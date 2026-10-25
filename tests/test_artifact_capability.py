"""Capability binding components with fixture-controlled support and process proof.

No worker, native process, model, provider or network is started by these tests.
"""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import uuid

from api_seats import atomic_json
import runtime_ownership
from tests import test_restart_launch as fixture


class ArtifactCapabilityTests(unittest.TestCase):
    def setUp(self):
        fixture.RestartLaunchTests.setUp(self)

    def files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def launch_binding(self, seat='api', *, supported=False):
        manifest = None
        if supported:
            protocol = importlib.import_module('runtime_protocol')
            manifest = protocol.build_manifest(fixture.ROOT,
                'cli' if seat == 'cli' else 'openai-compatible')
            self.assertIsNotNone(manifest)
            manifest['capabilities'] = ['artifact-v1']  # Synthetic supported wrapper fixture.
        effective = self.manager._effective
        def frozen(selected):
            value = effective(selected)
            if manifest is not None:
                value['wrapper_protocol'] = deepcopy(manifest)
            else:
                value.pop('wrapper_protocol', None)  # Explicit legacy snapshot.
            return value
        with patch.object(self.manager, '_effective', side_effect=frozen):
            self.manager.launch('team', seat)
        attempt = self.manager.attempts['team/' + seat]
        process = attempt['process']
        process.pid = 42000 + len(self.processes)
        snapshot = json.loads(attempt['snapshot'].read_text(encoding='utf-8'))
        # These values and the verified-open observation are doubles, never native proof.
        observed = {'platform': 'win32', 'pid': process.pid,
                    'creation_filetime': '123456789', 'image_path': str(self.root / 'fixture-python.exe')}
        with patch.object(runtime_ownership, 'capture_birth', return_value=observed):
            birth = runtime_ownership.record_worker_birth(attempt['snapshot'], snapshot)
        instance = self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready',
            'name': instance['name'], 'identity_id': instance['identity_id'],
            'adapter_connected': True, 'authentication': 'unknown', 'updated_at': time.time()})
        payload = runtime_ownership.heartbeat_payload(birth, self.manager.boot_id)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'live', 'process': process}):
            reply = self.manager.observe_runtime_heartbeat(instance, payload)
        self.assertTrue(reply['verified'], reply)
        return instance, attempt, birth

    def assert_gate(self, instance, *, available, reason):
        value = self.manager.artifact_producer(instance)
        self.assertEqual(set(value), {'available', 'reason', 'identity_id', 'adapter',
            'launch_attempt', 'launch_nonce', 'fingerprint', 'capabilities'})
        self.assertIs(value['available'], available)
        self.assertEqual(value['reason'], reason)
        self.assertEqual(value['capabilities'], ['artifact-v1'] if available else [])
        return value

    def test_legacy_or_forged_registration_cannot_grant_artifact_capability(self):
        self.registry.seed({'unmanaged': {'label': 'Unmanaged fixture'}})
        unmanaged = self.registry.register('unmanaged')
        forged = {**unmanaged, 'capabilities': ['artifact-v1'],
                  'wrapper_protocol': {'version': 1, 'capabilities': ['artifact-v1']}}
        before = self.files()
        self.assert_gate(forged, available=False, reason='unmanaged_producer')
        self.assertEqual(self.files(), before)
        instance, _, _ = self.launch_binding()
        self.assert_gate({**instance, 'capabilities': ['artifact-v1']},
                         available=False, reason='artifact_capability_missing')

    def test_fixture_supported_managed_binding_grants_then_identity_or_birth_change_refuses(self):
        instance, attempt, birth = self.launch_binding(supported=True)
        before = self.files()
        granted = self.assert_gate(instance, available=True, reason=None)
        self.assertEqual(granted['identity_id'], instance['identity_id'])
        self.assertEqual(granted['launch_attempt'], attempt['id'])
        self.assertEqual(granted['launch_nonce'], attempt['ownership']['launch_nonce'])
        self.assertEqual(granted['fingerprint'], attempt['ownership']['fingerprint'])
        self.assertEqual(self.files(), before)
        denied = self.manager.artifact_producer({**instance, 'identity_id': uuid.uuid4().hex})
        self.assertIs(denied['available'], False)
        self.assertEqual(denied['capabilities'], [])
        changed = deepcopy(birth)
        changed['creation_filetime'] = '123456790'
        atomic_json(attempt['snapshot'].with_name('birth.json'), changed)
        self.assert_gate(instance, available=False, reason='capability_binding_changed')


if __name__ == '__main__':
    unittest.main()
