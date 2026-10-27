"""Root-owned real manager flow and legacy consumer guards.

Launch-path test controls process observations. Legacy guards reuse bounded
Windows fixture children; none is a client, model or provider acceptance case.
"""
from copy import deepcopy
import json
import sys
import time
import unittest
from unittest.mock import patch
import uuid

from api_seats import atomic_json
from api_seat_runtime import SeatManager
import runtime_ownership
from tests import test_artifact_capability as fixture
from tests import test_cold_spawn_proof, test_selected_cli_exit_proof, test_same_boot_worker_handle


class ArtifactCapabilityRecoveryTests(unittest.TestCase):
    def test_real_launch_snapshot_and_provenance_reach_retained_and_cold_exit_proof(self):
        case = fixture.ArtifactCapabilityTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        # No effective-field construction or override: use the real manager path.
        case.manager.launch('team', 'cli')
        attempt = case.manager.attempts['team/cli']
        snapshot = json.loads(attempt['snapshot'].read_text(encoding='utf-8'))
        self.assertIn('wrapper_protocol', snapshot)
        self.assertEqual(snapshot['wrapper_protocol']['capabilities'], ['artifact-v1'])
        process = attempt['process']
        process.pid = 45000
        observed = {'platform': 'win32', 'pid': process.pid, 'creation_filetime': '456789012',
                    'image_path': str(case.root / 'fixture-python.exe')}
        with patch.object(runtime_ownership, 'capture_birth', return_value=observed):
            birth = runtime_ownership.record_worker_birth(attempt['snapshot'], snapshot)
        instance = case.registry.register(attempt['base'])
        receipt = {'attempt': attempt['id'], 'state': 'ready', 'name': instance['name'],
            'identity_id': instance['identity_id'], 'adapter_connected': True,
            'authentication': 'unknown', 'updated_at': time.time()}
        atomic_json(attempt['receipt'], receipt)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'live', 'process': process}):
            self.assertTrue(case.manager.observe_runtime_heartbeat(instance,
                runtime_ownership.heartbeat_payload(birth, case.manager.boot_id))['verified'])
        provenance = case.manager.launch_provenance(instance)
        self.assertEqual(provenance['effective']['wrapper_protocol'], snapshot['wrapper_protocol'])
        process.poll.return_value = 7  # Explicit controlled process-end observation.
        atomic_json(attempt['receipt'], {**receipt, 'state': 'failed', 'adapter_connected': False,
                                       'child_exit_code': 23})
        dispatch = uuid.uuid4().hex
        self.assertTrue(case.manager.selected_cli_exit_proof(provenance, dispatch)['local_ended'])
        cold = SeatManager(fixture.fixture.ROOT, case.manager.config, case.store, case.registry, monitor=False)
        self.addCleanup(cold.shutdown)
        with patch('runtime_adoption.open_verified_process',
                   return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            self.assertTrue(cold.runtime_exit_proof(provenance, dispatch)['local_ended'])
            self.assertEqual(cold.retry_context_offer(provenance)['state'], 'ready')

    @unittest.skipUnless(sys.platform == 'win32', 'Existing bounded Windows fixture child consumers')
    def test_legacy_manifest_absent_artifacts_pass_three_existing_recovery_consumers(self):
        original = SeatManager._effective
        captured = []
        def legacy(manager, seat):
            effective = original(manager, seat)
            effective.pop('wrapper_protocol', None)  # Explicit pre-upgrade storage fixture.
            captured.append(deepcopy(effective))
            return effective
        consumers = (
            (test_cold_spawn_proof.ColdSpawnProofTests,
             'test_cached_preparation_failure_cannot_override_new_conflicting_birth'),
            (test_selected_cli_exit_proof.SelectedCLIExitProofTests,
             'test_retained_worker_exit_and_matching_child_receipt_prove_end_without_control'),
            (test_same_boot_worker_handle.SameBootWorkerHandleTests,
             'test_cli_same_boot_preserves_true_worker_handle_beside_original_shim'),
        )
        with patch.object(SeatManager, '_effective', legacy):
            for cls, method in consumers:
                with self.subTest(consumer=method):
                    case = cls(method)
                    try:
                        case.setUp()
                        getattr(case, method)()  # Original consumer assertions, unchanged.
                    finally:
                        case.doCleanups()
        self.assertTrue(captured)
        self.assertTrue(all('wrapper_protocol' not in effective for effective in captured))


if __name__ == '__main__':
    unittest.main()
