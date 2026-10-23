"""Real model-child lifecycle evidence, separate from generated answer storage."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from tests import test_api_invocation as fixture
from api_seats import atomic_json
from runtime_ownership import new_launch_identity, record_spawn_outcome


class InvocationEvidenceTests(unittest.TestCase):
    def setUp(self):
        fixture.APIInvocationTests.setUp(self)
        temporary = tempfile.TemporaryDirectory(dir=fixture.ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name)
        self.attempt, self.dispatch = uuid.uuid4().hex, uuid.uuid4().hex
        effective = {'seat': self.seat, 'provider': self.provider,
                     'server': {'host': '127.0.0.1', 'port': 18300, 'data_dir': str(self.data)}, 'mcp': {}}
        identity = new_launch_identity(fixture.ROOT, effective, 'team/api', self.attempt, uuid.uuid4().hex)
        import hashlib
        base = 'api-' + hashlib.sha256(b'team/api').hexdigest()[:8] + '-' + self.attempt[:12]
        self.runtime = self.data / 'api_seat_runtime' / self.attempt
        snapshot = {**effective, 'attempt': self.attempt, 'base': base, 'ownership': identity}
        atomic_json(self.runtime / 'config.json', snapshot)
        record_spawn_outcome(self.runtime / 'config.json', snapshot, 'pending')
        record_spawn_outcome(self.runtime / 'config.json', snapshot, 'spawned')
        self.scope = {'runtime_path': str(self.runtime), 'launch_attempt': self.attempt,
                      'launch_nonce': identity['launch_nonce'], 'dispatch_id': self.dispatch}
        self.directory = self.runtime / 'invocations' / self.dispatch

    def record(self, name):
        return json.loads((self.directory / name).read_text(encoding='utf-8'))

    def test_success_records_real_birth_and_observed_exit_without_payload_or_secret(self):
        with patch.dict(os.environ, INVOCATION_TEST_KEY='EVIDENCE_SECRET_SENTINEL'):
            result = self.module.run_completion(self.seat, self.provider,
                [{'role': 'user', 'content': 'EVIDENCE_SOURCE_SENTINEL'}], lambda: False,
                timeout=5, evidence=self.scope)
        self.assertEqual(result['confirmed_model'], 'confirmed')
        intent, birth, ended = (self.record(name) for name in ('invocation.json', 'birth.json', 'exit.json'))
        self.assertEqual(intent['spawn_outcome'], 'spawned')
        for value in (intent, birth, ended):
            self.assertEqual(value['dispatch_id'], self.dispatch)
            self.assertEqual(value['launch_attempt'], self.attempt)
            self.assertEqual(value['launch_nonce'], self.scope['launch_nonce'])
            self.assertEqual(value['invocation_id'], intent['invocation_id'])
        self.assertNotEqual(birth['pid'], os.getpid())
        if os.name == 'nt':
            self.assertGreater(int(birth['creation_filetime']), 2 ** 53)
            self.assertTrue(Path(birth['image_path']).is_absolute())
        self.assertEqual(ended['child_exit_code'], 0)
        self.assertIs(type(ended['child_exit_code']), int)
        self.assertTrue(ended['ipc_cleaned'])
        persisted = ''.join(path.read_text(encoding='utf-8') for path in self.directory.glob('*.json'))
        for forbidden in ('EVIDENCE_SECRET_SENTINEL', 'EVIDENCE_SOURCE_SENTINEL', 'Exact café', 'messages', 'secret_ref'):
            self.assertNotIn(forbidden, persisted)

    def test_cancel_records_actual_child_exit_before_provider_progress(self):
        with self.assertRaises(self.module.InvocationCancelled) as caught:
            self.module.run_completion({**self.seat, 'model': 'blocked', 'secret_ref': ''}, self.provider,
                [], self.entered.is_set, timeout=5, evidence=self.scope)
        self.assertTrue(caught.exception.local_ended)
        self.assertFalse(self.release.is_set())
        ended = self.record('exit.json')
        self.assertIs(type(ended['child_exit_code']), int)
        self.assertTrue(ended['ipc_cleaned'])
        self.assertEqual(ended['invocation_id'], self.record('birth.json')['invocation_id'])

    def test_pending_intent_precedes_popen_and_sync_failure_has_no_invented_birth_or_exit(self):
        def fail_spawn(*args, **kwargs):
            self.assertEqual(self.record('invocation.json')['spawn_outcome'], 'pending')
            raise OSError('fixture spawn unavailable')
        with patch('api_invocation.subprocess.Popen', side_effect=fail_spawn):
            with self.assertRaises(OSError):
                self.module.run_completion(self.seat, self.provider, [], lambda: False,
                    timeout=5, evidence=self.scope)
        self.assertEqual(self.record('invocation.json')['spawn_outcome'], 'failed')
        self.assertFalse((self.directory / 'birth.json').exists())
        self.assertFalse((self.directory / 'exit.json').exists())
        self.assertEqual(self.requests, [])

    def test_wrong_launch_scope_fails_before_spawn_without_evidence_writes(self):
        with patch('api_invocation.subprocess.Popen') as spawn:
            for field in ('launch_attempt', 'launch_nonce', 'dispatch_id'):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.module.run_completion(self.seat, self.provider, [], lambda: False,
                        evidence={**self.scope, field: '../invalid'})
        spawn.assert_not_called()
        self.assertFalse(self.directory.exists())

    def test_failed_post_spawn_journal_write_ends_child_without_provider_request(self):
        from invocation_evidence import spawn_outcome
        actual_spawn = self.module.subprocess.Popen
        children = []
        def spawn(*args, **kwargs):
            child = actual_spawn(*args, **kwargs)
            children.append(child)
            self.addCleanup(lambda: child.kill() if child.poll() is None else None)
            return child
        def journal(evidence, outcome):
            if outcome == 'spawned':
                # Give an incorrectly released stdin packet time to reach the
                # actual provider; no provider call is allowed before commit.
                self.entered.wait(.5)
                raise OSError('fixture ownership bookkeeping failure')
            return spawn_outcome(evidence, outcome)
        with patch.dict(os.environ, INVOCATION_TEST_KEY='fixture-only'), patch('api_invocation.subprocess.Popen', side_effect=spawn), patch('invocation_evidence.spawn_outcome', side_effect=journal):
            with self.assertRaises(OSError):
                self.module.run_completion(self.seat, self.provider, [], lambda: False,
                    timeout=5, evidence=self.scope)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assertEqual(self.requests, [])

    def unresolved_birth(self):
        from invocation_evidence import begin, spawn_outcome, record_birth
        journal = begin(self.scope)
        spawn_outcome(journal, 'spawned')
        # This is a binding/probe ALGORITHM fixture, not native child absence.
        birth = record_birth(journal)
        return journal, birth

    def test_bound_birth_absence_proves_ended_without_invented_exit_code(self):
        import invocation_evidence
        self.unresolved_birth()
        for probe in ({'status': 'absent', 'process': None, 'error_code': 87},
                      {'status': 'mismatch', 'process': None, 'reason': 'creation_time_mismatch'}):
            with self.subTest(probe=probe), patch('invocation_evidence.open_verified_process', return_value=probe):
                proof = invocation_evidence.classify(self.scope)
                self.assertTrue(proof['local_ended'])
                self.assertEqual(proof['model_status'], 'absent')
                self.assertEqual(proof['verification_basis'], 'bound_invocation_birth_and_observed_absent')
                self.assertIsNone(proof.get('child_exit_code'))

    def test_live_or_uncertain_child_never_claims_ended_or_terminates(self):
        import invocation_evidence
        from unittest.mock import Mock
        self.unresolved_birth()
        process = Mock()
        probes = ({'status': 'live', 'process': process},
                  {'status': 'uncertain', 'process': None, 'error_code': 5},
                  {'status': 'uncertain', 'process': None, 'error_code': 31},
                  {'status': 'mismatch', 'process': None, 'reason': 'image_mismatch'})
        for probe in probes:
            with self.subTest(probe=probe), patch('invocation_evidence.open_verified_process', return_value=probe):
                self.assertFalse(invocation_evidence.classify(self.scope)['local_ended'])
        process.terminate.assert_not_called()
        process.kill.assert_not_called()
        process.close.assert_called_once()

    def test_wrong_birth_binding_and_pending_gap_fail_closed_before_native_probe(self):
        import invocation_evidence
        from invocation_evidence import begin
        journal = begin(self.scope)
        with patch('invocation_evidence.open_verified_process') as probe:
            self.assertFalse(invocation_evidence.classify(self.scope)['local_ended'])
            forged = {key: value for key, value in journal['intent'].items() if key != 'spawn_outcome'}
            forged.update(launch_nonce=uuid.uuid4().hex, pid=os.getpid(), platform='win32',
                          creation_filetime='133748291234567890', image_path=str(Path(os.__file__).resolve()))
            atomic_json(self.directory / 'birth.json', forged)
            self.assertFalse(invocation_evidence.classify(self.scope)['local_ended'])
        probe.assert_not_called()

    def test_genuine_parent_exit_receipt_is_bound_and_ipc_cleanup_required(self):
        import invocation_evidence
        with patch.dict(os.environ, INVOCATION_TEST_KEY='fixture-only'):
            self.module.run_completion(self.seat, self.provider, [], lambda: False, evidence=self.scope)
        proof = invocation_evidence.classify(self.scope)
        self.assertTrue(proof['local_ended'])
        self.assertEqual(proof['child_exit_code'], 0)
        ended = self.record('exit.json')
        # Without native absence proof, an incomplete/wrong receipt cannot
        # manufacture local end from the supervisor's last known state.
        with patch('invocation_evidence.open_verified_process', return_value={'status': 'uncertain', 'process': None, 'error_code': 31}):
            for change in ({'ipc_cleaned': False}, {'child_exit_code': True}, {'launch_attempt': uuid.uuid4().hex}):
                with self.subTest(change=change):
                    atomic_json(self.directory / 'exit.json', {**ended, **change})
                    self.assertFalse(invocation_evidence.classify(self.scope)['local_ended'])

    def declare_protocol(self):
        from runtime_ownership import record_worker_birth
        path = self.runtime / 'config.json'
        snapshot = json.loads(path.read_text(encoding='utf-8'))
        snapshot['invocation_protocol'] = 1
        atomic_json(path, snapshot)
        return record_worker_birth(path, snapshot)

    def test_empty_history_requires_dual_literal_protocol_declaration(self):
        import invocation_evidence
        self.assertFalse(invocation_evidence.classify_history(self.runtime)['local_ended'])
        birth = self.declare_protocol()
        self.assertEqual(birth.get('invocation_protocol'), 1)
        self.assertTrue(invocation_evidence.classify_history(self.runtime)['local_ended'])
        for protocol in (None, True, '1', 2):
            with self.subTest(protocol=protocol):
                atomic_json(self.runtime / 'birth.json', {**birth, 'invocation_protocol': protocol})
                self.assertFalse(invocation_evidence.classify_history(self.runtime)['local_ended'])
        atomic_json(self.runtime / 'birth.json', birth)
        path = self.runtime / 'config.json'
        snapshot = json.loads(path.read_text(encoding='utf-8'))
        snapshot.pop('invocation_protocol')
        atomic_json(path, snapshot)
        self.assertFalse(invocation_evidence.classify_history(self.runtime)['local_ended'])

    def test_protocol_one_with_pending_or_malformed_child_is_not_empty_history(self):
        import invocation_evidence
        self.declare_protocol()
        invocation_evidence.begin(self.scope)
        self.assertFalse(invocation_evidence.classify_history(self.runtime)['local_ended'])
        atomic_json(self.directory / 'invocation.json', {'unrelated': True})
        self.assertFalse(invocation_evidence.classify_history(self.runtime)['local_ended'])


if __name__ == '__main__':
    unittest.main()
