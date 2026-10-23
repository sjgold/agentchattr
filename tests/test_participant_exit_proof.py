"""Actual retained Windows supervisors; supplied CLI receipts/cold probes are labelled."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
import uuid

from tests import test_saved_result_exit_proof as fixture


@unittest.skipUnless(sys.platform == 'win32', 'actual retained Windows worker lifetime')
class ParticipantExitProofTests(unittest.TestCase):
    def setUp(self):
        fixture.SavedResultExitProofTests.setUp(self)
        self.provenance = self.manager.launch_provenance(self.api['principal'])

    make_record = fixture.SavedResultExitProofTests.make_record
    end_worker = fixture.SavedResultExitProofTests.end_worker
    files = fixture.SavedResultExitProofTests.files

    def test_actual_retained_api_exit_needs_no_outbox_or_seal_and_preserves_resources(self):
        self.end_worker()
        before, lease = self.files(), self.attempt['authenticated_at']
        with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('reopened worker')), \
                patch.object(self.native, 'close', side_effect=AssertionError('closed query handle')), \
                patch.object(self.native, 'terminate', side_effect=AssertionError('query terminated worker')):
            for _ in range(2):
                proof = self.manager.participant_exit_proof(deepcopy(self.provenance), self.dispatch)
                self.assertIs(proof['local_ended'], True)
                self.assertEqual(proof['wrapper_status'], 'observed_exited')
                self.assertEqual(proof['verification_basis'], 'protocol_one_no_invocations')
                self.assertEqual(proof['model_status'], 'never_spawned')
                self.assertEqual(proof['dispatch_id'], self.dispatch)
                self.assertEqual(proof['seat_identity_id'], self.api['principal']['identity_id'])
                self.assertEqual(proof['launch_attempt'], self.api['attempt'])
        self.assertEqual(self.files(), before)
        self.assertEqual(self.attempt['authenticated_at'], lease)
        self.spawn.assert_not_called()

    def test_live_true_worker_cannot_borrow_dead_launcher_shim_exit(self):
        shim = Mock(pid=self.native.pid + 1)
        shim.poll.return_value = 0
        self.attempt.update(process=shim, worker_process=self.native)
        try:
            with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('fresh probe')):
                self.assertFalse(self.manager.participant_exit_proof(self.provenance, self.dispatch)['local_ended'])
            self.assertIsNone(self.api['child'].poll())
            self.end_worker()
            self.assertTrue(self.manager.participant_exit_proof(self.provenance, self.dispatch)['local_ended'])
            shim.wait.assert_not_called()
            shim.terminate.assert_not_called()
        finally:
            self.native.close()

    def test_pending_model_intent_is_not_ended_when_its_supervisor_exits(self):
        from invocation_evidence import begin
        begin({'runtime_path': str(self.api['path'].parent), 'dispatch_id': self.dispatch,
            'launch_attempt': self.api['attempt'], 'launch_nonce': self.payload['launch_nonce']})
        self.end_worker()
        before = self.files()
        self.assertFalse(self.manager.participant_exit_proof(self.provenance, self.dispatch)['local_ended'])
        self.assertEqual(self.files(), before)

    def test_actual_model_exit_journal_proves_only_its_exact_dispatch(self):
        from invocation_evidence import begin, spawn_outcome, record_exit
        scope = begin({'runtime_path': str(self.api['path'].parent), 'dispatch_id': self.dispatch,
            'launch_attempt': self.api['attempt'], 'launch_nonce': self.payload['launch_nonce']})
        root = Path(__file__).resolve().parents[1]
        code = ('import sys,json;sys.path.insert(0,' + repr(str(root)) + ');'
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
        record_exit(scope, child.returncode)
        self.end_worker()
        proof = self.manager.participant_exit_proof(self.provenance, self.dispatch)
        self.assertTrue(proof['local_ended'])
        self.assertEqual(proof['verification_basis'], 'all_bound_invocations_ended')
        self.assertEqual(proof['invocations'][0]['child_exit_code'], 9)
        self.assertFalse(self.manager.participant_exit_proof(self.provenance, uuid.uuid4().hex)['local_ended'])

    def test_wrong_or_malformed_provenance_and_changed_birth_never_borrow_native_authority(self):
        self.end_worker()
        for value in (None, [], {}, {'effective': None}, {'effective': []}, self.payload):
            with self.subTest(value=value):
                self.assertFalse(self.manager.participant_exit_proof(value, self.dispatch)['local_ended'])
        for field in ('identity_id', 'launch_attempt', 'fingerprint', 'key'):
            invalid = deepcopy(self.provenance)
            invalid[field] = uuid.uuid4().hex
            self.assertFalse(self.manager.participant_exit_proof(invalid, self.dispatch)['local_ended'])
        path = self.api['path'].with_name('birth.json')
        original = path.read_bytes()
        birth = json.loads(original)
        birth['creation_filetime'] = str(int(birth['creation_filetime']) + 1)
        try:
            path.write_text(json.dumps(birth), encoding='utf-8')
            self.assertFalse(self.manager.participant_exit_proof(self.provenance, self.dispatch)['local_ended'])
        finally:
            path.write_bytes(original)

    def test_cold_probe_matrix_is_an_explicit_algorithm_seam_not_native_absence_acceptance(self):
        self.end_worker()
        self.manager.attempts.pop(self.api['key'])
        try:
            for observed, ended in (
                    ({'status': 'absent', 'process': None, 'error_code': 87}, True),
                    ({'status': 'mismatch', 'process': None, 'reason': 'creation_time_mismatch'}, True),
                    ({'status': 'uncertain', 'process': None, 'error_code': 5}, False),
                    ({'status': 'uncertain', 'process': None, 'error_code': 31}, False)):
                self.manager.runtime_history.clear()
                with self.subTest(observed=observed), patch('runtime_adoption.open_verified_process', return_value=observed):
                    proof = self.manager.participant_exit_proof(self.provenance, self.dispatch)
                    self.assertIs(proof['local_ended'], ended)
            self.assertNotIn(self.api['key'], self.manager.attempts)
        finally:
            self.native.close()

    def test_cli_uses_actual_retained_worker_and_explicitly_supplied_child_receipt(self):
        cli = self.make_record(key='team/retired-cli', adapter='cli', alive=True)
        identity, birth = cli['snapshot']['ownership'], cli['birth']
        self.manager.reconcile_runtime()
        report = {'attempt': cli['attempt'], 'launch_nonce': identity['launch_nonce'],
            'server_identity': identity['server_identity'], 'boot_id': self.manager.boot_id,
            'worker_pid': birth['pid'], 'creation_filetime': birth['creation_filetime'], 'worker_root': birth['worker_root']}
        self.assertTrue(self.manager.observe_runtime_heartbeat(cli['principal'], report)['verified'])
        attempt = self.manager.attempts[cli['key']]
        provenance = self.manager.launch_provenance(cli['principal'])
        native = attempt['process']
        cli['child'].stdin.write(b'x')
        cli['child'].stdin.flush()
        self.assertEqual(cli['child'].wait(timeout=5), 7)
        self.assertEqual(native.wait(timeout=5), 7)
        path = cli['path'].with_name('receipt.json')
        receipt = json.loads(path.read_text(encoding='utf-8'))
        # This toy is a real supervisor, not a real CLI product/client. Its
        # child exit receipt is a protocol fixture, never native child proof.
        receipt.update(state='stopped', child_exit_code=True)
        path.write_text(json.dumps(receipt), encoding='utf-8')
        self.assertFalse(self.manager.participant_exit_proof(provenance, self.dispatch)['local_ended'])
        receipt['child_exit_code'] = 23
        path.write_text(json.dumps(receipt), encoding='utf-8')
        proof = self.manager.participant_exit_proof(provenance, self.dispatch)
        self.assertTrue(proof['local_ended'])
        self.assertEqual(proof['child_exit_code'], 23)
        self.assertEqual(proof['verification_basis'], 'retained_native_handle_observed_end')
