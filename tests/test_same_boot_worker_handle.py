"""Actual Windows venv launcher/worker PID distinction at heartbeat admission."""
import sys
import unittest
from unittest.mock import patch
import uuid

from api_seats import atomic_json
from tests import test_cold_retry_context as fixture


@unittest.skipUnless(sys.platform == 'win32', 'actual Windows venv shim and retained handles')
class SameBootWorkerHandleTests(unittest.TestCase):
    def setUp(self):
        fixture.ColdRetryContextTests.setUp(self)

    make_record = fixture.ColdRetryContextTests.make_record

    def check_adapter(self, adapter):
        # The existing birth fixture normally uses the base interpreter. Use
        # this test process's actual venv launcher to exercise its real shim.
        with patch.object(sys, '_base_executable', sys.executable):
            record = self.make_record(key='same-boot/' + adapter, adapter=adapter, alive=True,
                                      invocation_protocol=1 if adapter != 'cli' else None)
        shim, birth = record['child'], record['birth']
        self.assertNotEqual(shim.pid, birth['pid'], 'This regression must exercise a genuine venv shim.')
        def cooperate():
            if shim.poll() is None:
                shim.stdin.write(b'x')
                shim.stdin.flush()
            shim.wait(timeout=5)
        self.addCleanup(cooperate)
        self.manager.reconcile_runtime()
        identity = record['snapshot']['ownership']
        report = {'attempt': record['attempt'], 'launch_nonce': identity['launch_nonce'],
                  'server_identity': identity['server_identity'], 'boot_id': self.manager.boot_id,
                  'worker_pid': birth['pid'], 'creation_filetime': birth['creation_filetime'],
                  'worker_root': birth['worker_root']}
        self.assertTrue(self.manager.observe_runtime_heartbeat(record['principal'], report)['verified'])
        attempt = self.manager.attempts[record['key']]
        # Recreate the same-boot Popen slot using the REAL original shim;
        # cold adoption above supplies the otherwise identical owned record.
        attempt['process'].close()
        attempt['process'] = shim
        attempt.pop('adopted_boot')
        attempt.pop('worker_birth')
        self.assertTrue(self.manager.observe_runtime_heartbeat(record['principal'], report)['verified'])
        worker = attempt.get('worker_process')
        self.assertIsNotNone(worker, 'Authenticated true-worker handle must survive the same-boot heartbeat.')
        self.assertIs(attempt['process'], shim)
        self.assertEqual(worker.pid, birth['pid'])
        self.assertTrue(self.manager.observe_runtime_heartbeat(record['principal'], report)['verified'])
        self.assertIs(attempt['worker_process'], worker)
        lease = attempt['authenticated_at']
        cooperate()
        self.assertEqual(worker.wait(timeout=5), 7)
        dispatch = uuid.uuid4().hex
        if adapter == 'cli':
            # Native supervisor exit is observed above; child23 is a separate
            # explicit CLI receipt protocol fixture, not an actual CLI run.
            atomic_json(record['path'].with_name('receipt.json'), dict(record['receipt'],
                        state='stopped', child_exit_code=23))
            provenance = fixture.ColdRetryContextTests.provenance(self, record)
            result = self.manager.selected_cli_exit_proof(provenance, dispatch)
        else:
            payload = {'launch_attempt': record['attempt'], 'launch_nonce': identity['launch_nonce'],
                       'fingerprint': identity['fingerprint'], 'seat_identity_id': record['principal']['identity_id'],
                       'dispatch_id': dispatch}
            result = self.manager.saved_result_exit_proof(payload)
        self.assertTrue(result['local_ended'])
        self.assertEqual(attempt['authenticated_at'], lease)
        self.spawn.assert_not_called()

    def test_cli_same_boot_preserves_true_worker_handle_beside_original_shim(self):
        self.check_adapter('cli')

    def test_api_same_boot_preserves_true_worker_handle_beside_original_shim(self):
        self.check_adapter('openai-compatible')
