"""Real retained Windows worker handles; cold probe seams are algorithm tests."""
from copy import deepcopy
import json
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
import uuid

from tests import test_cold_retry_context as fixture


@unittest.skipUnless(sys.platform == 'win32', 'retained native Windows worker handle')
class SavedResultExitProofTests(unittest.TestCase):
    def setUp(self):
        fixture.ColdRetryContextTests.setUp(self)
        self.api = self.make_record(key='team/api', adapter='openai-compatible',
                                    alive=True, invocation_protocol=1)
        identity, birth = self.api['snapshot']['ownership'], self.api['birth']
        self.manager.reconcile_runtime()
        report = {'attempt': self.api['attempt'], 'launch_nonce': identity['launch_nonce'],
            'server_identity': identity['server_identity'], 'boot_id': self.manager.boot_id,
            'worker_pid': birth['pid'], 'creation_filetime': birth['creation_filetime'],
            'worker_root': birth['worker_root']}
        self.assertTrue(self.manager.observe_runtime_heartbeat(self.api['principal'], report)['verified'])
        self.attempt = self.manager.attempts[self.api['key']]
        self.native = self.attempt['process']
        self.dispatch = uuid.uuid4().hex
        self.payload = {'launch_attempt': self.api['attempt'], 'launch_nonce': identity['launch_nonce'],
            'fingerprint': identity['fingerprint'], 'seat_identity_id': self.api['principal']['identity_id'],
            'dispatch_id': self.dispatch}

    make_record = fixture.ColdRetryContextTests.make_record

    def end_worker(self):
        self.api['child'].stdin.write(b'x')
        self.api['child'].stdin.flush()
        self.assertEqual(self.api['child'].wait(timeout=5), 7)
        self.assertEqual(self.native.wait(timeout=5), 7)

    def files(self):
        return fixture.ColdRetryContextTests.files(self)

    def test_retained_true_worker_exit_avoids_postmortem_probe_and_changes_nothing(self):
        self.end_worker()
        before, lease = self.files(), self.attempt['authenticated_at']
        with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('reopened worker')), \
                patch.object(self.native, 'close', side_effect=AssertionError('closed query handle')), \
                patch.object(self.native, 'terminate', side_effect=AssertionError('query terminated worker')):
            for _ in range(2):
                proof = self.manager.saved_result_exit_proof(deepcopy(self.payload))
                self.assertTrue(proof['local_ended'])
                for field in ('launch_attempt', 'dispatch_id', 'seat_identity_id'):
                    self.assertEqual(proof[field], self.payload[field])
                self.assertEqual(proof['verification_basis'], 'protocol_one_no_invocations')
        self.assertEqual(self.files(), before)
        self.assertEqual(self.attempt['authenticated_at'], lease)
        self.spawn.assert_not_called()

    def test_live_true_worker_is_not_end_proof_even_if_launcher_shim_exited(self):
        shim = Mock(pid=self.native.pid + 1)
        shim.poll.return_value = 0
        self.attempt.update(process=shim, worker_process=self.native)
        with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('fresh probe')):
            self.assertFalse(self.manager.saved_result_exit_proof(self.payload)['local_ended'])
        self.assertIsNone(self.api['child'].poll())
        self.end_worker()
        with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('fresh probe')):
            self.assertTrue(self.manager.saved_result_exit_proof(self.payload)['local_ended'])
        shim.wait.assert_not_called()
        shim.terminate.assert_not_called()
        shim.kill.assert_not_called()
        self.native.close()

    def test_changed_owner_or_birth_metadata_never_inherits_retained_handle_proof(self):
        self.end_worker()
        for field in ('launch_attempt', 'launch_nonce', 'fingerprint', 'seat_identity_id'):
            invalid = dict(self.payload, **{field: '0' * len(self.payload[field])})
            with self.subTest(field=field):
                self.assertFalse(self.manager.saved_result_exit_proof(invalid)['local_ended'])
        path = self.api['path'].with_name('birth.json')
        original = path.read_bytes()
        changed = deepcopy(self.api['birth'])
        changed['creation_filetime'] = str(int(changed['creation_filetime']) + 1)
        try:
            path.write_text(json.dumps(changed), encoding='utf-8')
            self.assertFalse(self.manager.saved_result_exit_proof(self.payload)['local_ended'])
        finally:
            path.write_bytes(original)

    def test_pending_exact_model_intent_blocks_even_after_true_worker_exit(self):
        from invocation_evidence import begin
        begin({'runtime_path': str(self.api['path'].parent), 'dispatch_id': self.dispatch,
            'launch_attempt': self.api['attempt'], 'launch_nonce': self.payload['launch_nonce']})
        self.end_worker()
        before = self.files()
        self.assertFalse(self.manager.saved_result_exit_proof(self.payload)['local_ended'])
        self.assertEqual(self.files(), before)

    def test_wrong_dispatch_cannot_borrow_another_completed_model_invocation(self):
        from invocation_evidence import begin, spawn_outcome
        other = begin({'runtime_path': str(self.api['path'].parent), 'dispatch_id': uuid.uuid4().hex,
            'launch_attempt': self.api['attempt'], 'launch_nonce': self.payload['launch_nonce']})
        # Synchronous no-child spawn failure is valid history proof, but does
        # not prove anything about this different requested dispatch.
        spawn_outcome(other, 'failed')
        self.end_worker()
        self.assertFalse(self.manager.saved_result_exit_proof(self.payload)['local_ended'])

    def test_exact_model_exit_journal_and_retained_worker_exit_prove_both_lifetimes(self):
        from invocation_evidence import begin, spawn_outcome, record_exit
        from pathlib import Path
        scope = begin({'runtime_path': str(self.api['path'].parent), 'dispatch_id': self.dispatch,
            'launch_attempt': self.api['attempt'], 'launch_nonce': self.payload['launch_nonce']})
        code = ('import sys,json;sys.path.insert(0,' + repr(str(fixture.ROOT)) + ');'
            'from invocation_evidence import record_birth;record_birth(json.loads(' + repr(json.dumps(scope)) + '));'
            'sys.exit(9)')
        child = self.actual_popen([sys._base_executable, '-c', code], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        def cleanup():
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
        self.addCleanup(cleanup)
        spawn_outcome(scope, 'spawned')
        self.assertEqual(child.wait(timeout=5), 9)
        self.assertTrue((Path(scope['scope']['runtime_path']) / 'invocations' / self.dispatch / 'birth.json').exists())
        record_exit(scope, child.returncode)
        self.end_worker()
        with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('reopened worker')):
            proof = self.manager.saved_result_exit_proof(self.payload)
        self.assertTrue(proof['local_ended'])
        self.assertEqual(proof['verification_basis'], 'all_bound_invocations_ended')
        self.assertEqual(proof['invocations'][0]['child_exit_code'], 9)

    def test_cold_fallback_uses_exact_original_launch_and_dispatch_without_synthetic_worker(self):
        self.end_worker()
        self.manager.attempts.pop(self.api['key'])
        try:
            # Cold absence classification is explicitly a probe seam, not a
            # claim that this test reproduced native WinError87 after exit.
            with patch('runtime_adoption.open_verified_process',
                       return_value={'status': 'absent', 'process': None, 'error_code': 87}):
                proof = self.manager.saved_result_exit_proof(self.payload)
            self.assertTrue(proof['local_ended'])
            self.assertEqual(proof['dispatch_id'], self.dispatch)
            self.assertEqual(proof['verification_basis'], 'protocol_one_no_invocations')
            self.assertNotIn(self.api['key'], self.manager.attempts)
        finally:
            self.native.close()

    def test_only_a_retained_shim_requires_cold_native_proof_instead_of_its_exit_code(self):
        self.end_worker()
        shim = Mock(pid=self.native.pid + 1)
        shim.poll.return_value = 0
        self.attempt['process'] = shim
        try:
            with patch('runtime_adoption.open_verified_process',
                       return_value={'status': 'absent', 'process': None, 'error_code': 87}):
                self.assertTrue(self.manager.saved_result_exit_proof(self.payload)['local_ended'])
            self.manager.runtime_history.clear()
            with patch('runtime_adoption.open_verified_process',
                       return_value={'status': 'uncertain', 'process': None, 'error_code': 5}):
                self.assertFalse(self.manager.saved_result_exit_proof(self.payload)['local_ended'])
            shim.wait.assert_not_called()
            shim.terminate.assert_not_called()
        finally:
            self.native.close()
