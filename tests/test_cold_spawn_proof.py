"""Lost RAM handles and dead supervisors cannot authorize duplicate children."""
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import Mock, patch
import uuid

from api_seats import SeatError, SeatStore
from api_seat_runtime import SeatManager
from invocation_evidence import begin
from registry import RuntimeRegistry

ROOT = Path(__file__).resolve().parents[1]


class ColdSpawnProofTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name)
        self.store = SeatStore(self.data, {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1'}})
        self.store.save({'id': 'team', 'name': 'Team', 'seats': [{'id': 'api', 'name': 'API',
            'adapter': 'openai-compatible', 'provider': 'fake', 'model': 'frozen-model', 'reasoning': None,
            'launch_profile': 'standard', 'secret_ref': ''}]})
        self.manager = SeatManager(ROOT, {'server': {'port': 18300}}, self.store,
                                   RuntimeRegistry(str(self.data)), monitor=False)
        self.addCleanup(self.manager.shutdown)

    def launch_double(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.return_value = 1
        with patch('api_seat_runtime.subprocess.Popen', return_value=process):
            self.manager.launch('team', 'api')
        return self.manager.attempts['team/api']

    def test_lost_handle_with_spawned_intent_and_failed_label_is_not_never_spawned(self):
        attempt = self.launch_double()
        attempt.update(process=None, state='failed')  # Explicit cold-RAM algorithm fixture.
        self.assertFalse(self.manager._retry_preparation_exit_proven(attempt))

    def test_missing_disk_intent_cannot_be_replaced_by_failed_ram_label(self):
        attempt = self.launch_double()
        attempt['snapshot'].with_name('launch.json').unlink()
        attempt.update(process=None, state='failed', spawn_outcome='failed')
        self.assertFalse(self.manager._retry_preparation_exit_proven(attempt))

    def test_genuine_sync_popen_failure_has_validated_disk_proof(self):
        with patch('api_seat_runtime.subprocess.Popen', side_effect=OSError('fixture spawn failure')):
            self.manager.launch('team', 'api')
        attempt = self.manager.attempts['team/api']
        self.assertIsNone(attempt['process'])
        self.assertTrue(self.manager._retry_preparation_exit_proven(attempt))

    def test_dead_supervisor_with_pending_model_intent_blocks_explicit_seat_restart(self):
        attempt = self.launch_double()
        begin({'runtime_path': str(attempt['snapshot'].parent), 'launch_attempt': attempt['id'],
               'launch_nonce': attempt['ownership']['launch_nonce'], 'dispatch_id': uuid.uuid4().hex})
        attempt['process'].poll.return_value = 1
        attempt['process'].returncode = 1
        with patch('api_seat_runtime.subprocess.Popen', side_effect=AssertionError('duplicate model owner')) as spawn:
            with self.assertRaises(SeatError):
                self.manager.launch('team', 'api', restart=True)
        spawn.assert_not_called()

    def test_dead_cli_wrapper_without_client_exit_receipt_cannot_restart(self):
        self.store.providers['cli'] = {'command': sys.executable, 'cwd': str(self.data),
                                       'cli_args': ['-c', 'pass'], 'mcp_inject': 'env',
                                       'mcp_env_var': 'COLD_PROOF_MCP_SETTINGS'}
        seat = {'id': 'cli', 'name': 'CLI', 'adapter': 'cli', 'provider': 'cli', 'model': None,
                'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        self.store.save({'id': 'team', 'name': 'Team', 'seats': [seat]})
        process = Mock()
        process.poll.return_value = None
        process.wait.return_value = 1
        with patch('api_seat_runtime.subprocess.Popen', return_value=process):
            self.manager.launch('team', 'cli')
        process.poll.return_value = 1
        process.returncode = 1
        with patch('api_seat_runtime.subprocess.Popen', side_effect=AssertionError('orphan CLI replacement')) as spawn:
            with self.assertRaises(SeatError):
                self.manager.launch('team', 'cli', restart=True)
        spawn.assert_not_called()

    def test_cached_preparation_failure_cannot_override_new_conflicting_birth(self):
        from tests import test_cold_preparation_repair as fixture
        from api_seats import atomic_json
        f = fixture.ColdPreparationRepairTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            provenance, key, binding, failed, path, snapshot = f.failed_preparation()
            cold = f.new_manager()
            cold.reconcile_runtime()
            atomic_json(path.with_name('birth.json'), {'conflicting_birth': True})
            with self.assertRaises(SeatError):
                cold.prepare_retry_context(provenance, key, binding=binding, retry_attempt=failed['launch_attempt'])
        f.spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
