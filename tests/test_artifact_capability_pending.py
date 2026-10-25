"""Root-owned fixture-controlled pending launch progression, no native process."""
from copy import deepcopy
import json
import time
import unittest
from unittest.mock import patch

from api_seats import atomic_json
import runtime_ownership
import runtime_protocol
from tests import test_artifact_capability as fixture


class ArtifactCapabilityPendingTests(unittest.TestCase):
    def test_pending_birth_then_pending_heartbeat_then_verified_binding(self):
        case = fixture.ArtifactCapabilityTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        manifest = runtime_protocol.build_manifest(fixture.fixture.ROOT, 'openai-compatible')
        manifest['capabilities'] = ['artifact-v1']  # Fixture-controlled supported declaration.
        original = case.manager._effective
        def supported(seat):
            return {**original(seat), 'wrapper_protocol': deepcopy(manifest)}
        with patch.object(case.manager, '_effective', side_effect=supported):
            case.manager.launch('team', 'api')
        attempt = case.manager.attempts['team/api']
        instance = case.registry.register(attempt['base'])
        before = case.files()
        initial = case.manager.artifact_producer(instance)
        self.assertFalse(initial['available'])
        self.assertEqual(initial['reason'], 'runtime_unverified')
        self.assertEqual(case.files(), before)
        process = attempt['process']
        process.pid = 44000
        observed = {'platform': 'win32', 'pid': process.pid, 'creation_filetime': '345678901',
                    'image_path': str(case.root / 'fixture-python.exe')}
        snapshot = json.loads(attempt['snapshot'].read_text(encoding='utf-8'))
        with patch.object(runtime_ownership, 'capture_birth', return_value=observed):
            birth = runtime_ownership.record_worker_birth(attempt['snapshot'], snapshot)
        pending = case.manager.artifact_producer(instance)
        self.assertFalse(pending['available'])
        self.assertEqual(pending['reason'], 'runtime_unverified')
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready',
            'name': instance['name'], 'identity_id': instance['identity_id'],
            'adapter_connected': True, 'authentication': 'unknown', 'updated_at': time.time()})
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'live', 'process': process}):
            reply = case.manager.observe_runtime_heartbeat(instance,
                runtime_ownership.heartbeat_payload(birth, case.manager.boot_id))
        self.assertTrue(reply['verified'])
        ready = case.manager.artifact_producer(instance)
        self.assertTrue(ready['available'])
        self.assertIsNone(ready['reason'])


if __name__ == '__main__':
    unittest.main()
