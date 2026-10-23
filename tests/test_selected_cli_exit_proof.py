"""Native owned worker handles plus explicit CLI child-receipt protocol fixtures."""
from copy import deepcopy
import sys
import unittest
from unittest.mock import Mock, patch
import uuid

from api_seats import atomic_json
from tests import test_cold_retry_context as fixture


@unittest.skipUnless(sys.platform == 'win32', 'native retained Windows worker proof')
class SelectedCLIExitProofTests(unittest.TestCase):
    def setUp(self):
        # Run after fixture shutdown, including tests that replace/pop its
        # attempt entry so that the fixture no longer owns this handle.
        self.addCleanup(lambda: getattr(self, 'native', None) and self.native.close())
        fixture.ColdRetryContextTests.setUp(self)
        self.cli = self.make_record(key='team/selected-cli', alive=True)
        self.manager.reconcile_runtime()
        ownership, birth = self.cli['snapshot']['ownership'], self.cli['birth']
        self.assertTrue(self.manager.observe_runtime_heartbeat(self.cli['principal'], {
            'attempt': self.cli['attempt'], 'launch_nonce': ownership['launch_nonce'],
            'server_identity': ownership['server_identity'], 'boot_id': self.manager.boot_id,
            'worker_pid': birth['pid'], 'creation_filetime': birth['creation_filetime'],
            'worker_root': birth['worker_root']})['verified'])
        self.attempt = self.manager.attempts[self.cli['key']]
        self.native = self.attempt['process']
        self.proof_source = fixture.ColdRetryContextTests.provenance(self, self.cli)
        self.dispatch = uuid.uuid4().hex

    make_record = fixture.ColdRetryContextTests.make_record

    def end_worker(self):
        self.cli['child'].stdin.write(b'x')
        self.cli['child'].stdin.flush()
        self.assertEqual(self.cli['child'].wait(timeout=5), 7)
        self.assertEqual(self.native.wait(timeout=5), 7)

    def test_live_owned_cli_cannot_claim_end(self):
        result = self.manager.selected_cli_exit_proof(self.proof_source, self.dispatch)
        self.assertFalse(result['local_ended'])
        self.assertIsNone(self.cli['child'].poll())
        self.spawn.assert_not_called()

    def test_retained_worker_exit_and_matching_child_receipt_prove_end_without_control(self):
        self.end_worker()
        # The native handle above proves the toy supervisor's exit7. This
        # separate child code is a protocol fixture, not a native CLI run.
        receipt = dict(self.cli['receipt'], state='failed', child_exit_code=23)
        atomic_json(self.cli['path'].with_name('receipt.json'), receipt)
        before = fixture.ColdRetryContextTests.files(self)
        lease = self.attempt['authenticated_at']
        with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('fresh probe')), \
                patch.object(self.native, 'close', side_effect=AssertionError('closed handle')), \
                patch.object(self.native, 'terminate', side_effect=AssertionError('terminated worker')):
            result = self.manager.selected_cli_exit_proof(deepcopy(self.proof_source), self.dispatch)
            self.assertTrue(result['local_ended'])
            self.assertEqual(result['dispatch_id'], self.dispatch)
            self.assertEqual(result['launch_attempt'], self.cli['attempt'])
            self.assertEqual(result['seat_identity_id'], self.cli['principal']['identity_id'])
            self.assertEqual(result['child_exit_code'], 23)
            self.assertEqual(result['verification_basis'], 'retained_native_handle_observed_end')
        self.assertEqual(fixture.ColdRetryContextTests.files(self), before)
        self.assertEqual(self.attempt['authenticated_at'], lease)
        self.spawn.assert_not_called()

    def test_missing_or_noninteger_child_receipt_never_proves_both_lifetimes(self):
        self.end_worker()
        for value in (None, True, '23'):
            receipt = dict(self.cli['receipt'], state='failed', child_exit_code=value)
            atomic_json(self.cli['path'].with_name('receipt.json'), receipt)
            with self.subTest(value=value):
                self.assertFalse(self.manager.selected_cli_exit_proof(self.proof_source, self.dispatch)['local_ended'])

    def test_live_true_worker_wins_over_exited_launcher_shim_and_child_receipt(self):
        atomic_json(self.cli['path'].with_name('receipt.json'),
                    dict(self.cli['receipt'], state='failed', child_exit_code=23))
        shim = Mock(pid=self.native.pid + 1)
        shim.poll.return_value = 0
        self.attempt.update(process=shim, worker_process=self.native)
        with patch('runtime_adoption.open_verified_process', side_effect=AssertionError('fresh probe')):
            self.assertFalse(self.manager.selected_cli_exit_proof(self.proof_source, self.dispatch)['local_ended'])
        self.assertIsNone(self.cli['child'].poll())
        shim.wait.assert_not_called()
        shim.terminate.assert_not_called()
        shim.kill.assert_not_called()
        self.end_worker()

    def test_wrong_frozen_scope_or_changed_birth_cannot_inherit_handle_proof(self):
        self.end_worker()
        atomic_json(self.cli['path'].with_name('receipt.json'),
                    dict(self.cli['receipt'], state='failed', child_exit_code=23))
        for field in ('launch_attempt', 'identity_id', 'fingerprint', 'key'):
            changed = dict(self.proof_source, **{field: '0' * 32})
            with self.subTest(field=field):
                self.assertFalse(self.manager.selected_cli_exit_proof(changed, self.dispatch)['local_ended'])
        path = self.cli['path'].with_name('birth.json')
        original = path.read_bytes()
        birth = deepcopy(self.cli['birth'])
        birth['creation_filetime'] = str(int(birth['creation_filetime']) + 1)
        try:
            atomic_json(path, birth)
            self.assertFalse(self.manager.selected_cli_exit_proof(self.proof_source, self.dispatch)['local_ended'])
        finally:
            path.write_bytes(original)

    def test_cold_absence_uses_existing_receipt_basis_not_a_synthetic_process(self):
        self.end_worker()
        atomic_json(self.cli['path'].with_name('receipt.json'),
                    dict(self.cli['receipt'], state='failed', child_exit_code=23))
        self.manager.attempts.pop(self.cli['key'])
        self.manager.runtime_history.pop(self.cli['attempt'], None)
        before = fixture.ColdRetryContextTests.files(self)
        # Explicit cold-probe algorithm seam, not a native absence claim.
        with patch('runtime_adoption.open_verified_process', return_value={
                'status': 'absent', 'process': None, 'error_code': 87}):
            result = self.manager.selected_cli_exit_proof(self.proof_source, self.dispatch)
        self.assertTrue(result['local_ended'])
        self.assertEqual(result['verification_basis'], 'durable_receipt_and_observed_absent')
        self.assertEqual(result['child_exit_code'], 23)
        self.assertNotIn(self.cli['key'], self.manager.attempts)
        self.assertEqual(fixture.ColdRetryContextTests.files(self), before)
        self.native.close()

    def test_api_adapter_and_malformed_dispatch_never_gain_cli_proof(self):
        api = self.make_record(key='team/api-proof', adapter='openai-compatible', alive=True, invocation_protocol=1)
        provenance = fixture.ColdRetryContextTests.provenance(self, api)
        self.assertFalse(self.manager.selected_cli_exit_proof(provenance, self.dispatch)['local_ended'])
        for dispatch in (None, True, 'not-a-dispatch', 'a' * 31):
            with self.subTest(dispatch=dispatch):
                self.assertFalse(self.manager.selected_cli_exit_proof(self.proof_source, dispatch)['local_ended'])
