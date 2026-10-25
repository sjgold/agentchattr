"""Capability binding components with fixture-controlled support and process proof.

No worker, native process, model, provider or network is started by these tests.
"""
from copy import deepcopy
import hashlib
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

    def launch_binding(self, seat='api', *, supported=False, omit_birth_protocol=False):
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
            if omit_birth_protocol:
                # Explicit source-match observation double, not an actual mismatching checkout.
                with patch('runtime_protocol.sources_match', return_value=False):
                    birth = runtime_ownership.record_worker_birth(attempt['snapshot'], snapshot)
            else:
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

    def birth_fixture(self, adapter, *, matching=True):
        """Real immutable launch/birth files, with only capture_birth controlled."""
        protocol = importlib.import_module('runtime_protocol')
        manifest = protocol.build_manifest(fixture.ROOT, adapter)
        self.assertIsNotNone(manifest)
        manifest['capabilities'] = ['artifact-v1']
        if not matching:
            manifest['sources'][next(iter(manifest['sources']))] = '0' * 64
        seat_id = 'cli' if adapter == 'cli' else 'api'
        seat = next(s for s in self.package['seats'] if s['id'] == seat_id)
        effective = self.manager._effective(seat)
        effective['wrapper_protocol'] = manifest
        attempt = uuid.uuid4().hex
        key = 'fixture/' + seat_id
        ownership = runtime_ownership.new_launch_identity(fixture.ROOT, effective, key,
                                                          attempt, self.manager.boot_id)
        base = ('cli-' if seat_id == 'cli' else 'api-') + hashlib.sha256(key.encode()).hexdigest()[:8] + '-' + attempt[:12]
        snapshot = {**effective, 'attempt': attempt, 'base': base, 'ownership': ownership}
        path = self.root / 'api_seat_runtime' / attempt / 'config.json'
        atomic_json(path, snapshot)
        runtime_ownership.record_spawn_outcome(path, snapshot, 'pending')
        runtime_ownership.record_spawn_outcome(path, snapshot, 'spawned')
        observed = {'platform': 'win32', 'pid': 43000, 'creation_filetime': '234567890',
                    'image_path': str(self.root / 'fixture-python.exe')}
        return path, snapshot, observed

    def test_manifests_both_adapters_are_disabled_detached_and_strictly_validated(self):
        protocol = importlib.import_module('runtime_protocol')
        self.assertEqual(protocol.SUPPORTED_CAPABILITIES, ())
        for adapter in ('cli', 'openai-compatible'):
            with self.subTest(adapter=adapter):
                manifest = protocol.build_manifest(fixture.ROOT, adapter)
                self.assertEqual(set(manifest), {'version', 'adapter', 'capabilities', 'sources'})
                self.assertEqual(manifest['version'], 1)
                self.assertEqual(manifest['adapter'], adapter)
                self.assertEqual(manifest['capabilities'], [])
                self.assertEqual(set(manifest['sources']), set(protocol.SOURCE_FILES[adapter]))
                self.assertIn('runtime_protocol.py', manifest['sources'])
                for name, digest in manifest['sources'].items():
                    self.assertEqual(Path(name).name, name)
                    self.assertEqual(digest, hashlib.sha256((fixture.ROOT / name).read_bytes()).hexdigest())
                synthetic = deepcopy(manifest)
                synthetic['capabilities'] = ['artifact-v1']
                validated = protocol.validate_manifest(synthetic, adapter)
                self.assertEqual(validated, synthetic)
                validated['sources'].clear()
                validated['capabilities'].clear()
                self.assertTrue(synthetic['sources'])
                self.assertEqual(synthetic['capabilities'], ['artifact-v1'])
                invalid = [None, [], {**manifest, 'version': True}, {**manifest, 'version': 2},
                    {**manifest, 'adapter': 'other'}, {**manifest, 'extra': 1},
                    {**manifest, 'capabilities': ['artifact-v1', 'artifact-v1']},
                    {**manifest, 'capabilities': ['unknown']}, {**manifest, 'sources': {}},
                    {**manifest, 'sources': {**manifest['sources'], '../outside.py': '0' * 64}}]
                for digest in ('A' * 64, 'g' * 64, '0' * 63, None, True):
                    sources = dict(manifest['sources'])
                    sources[next(iter(sources))] = digest
                    invalid.append({**manifest, 'sources': sources})
                for value in invalid:
                    with self.subTest(value=value), self.assertRaises(ValueError):
                        protocol.validate_manifest(value, adapter)

    def test_source_byte_drift_and_unreadable_closure_fail_closed_without_touching_sources(self):
        protocol = importlib.import_module('runtime_protocol')
        for adapter in ('cli', 'openai-compatible'):
            checkout = self.root / ('checkout-' + adapter)
            checkout.mkdir()
            for name in protocol.SOURCE_FILES[adapter]:
                (checkout / name).write_bytes((fixture.ROOT / name).read_bytes())
            manifest = protocol.build_manifest(checkout, adapter)
            self.assertTrue(protocol.sources_match(checkout, manifest))
            source = checkout / protocol.SOURCE_FILES[adapter][0]
            original = source.read_bytes()
            source.write_bytes(original + b'\n# fixture-controlled source drift\n')
            self.assertFalse(protocol.sources_match(checkout, manifest))
            source.write_bytes(original)
            self.assertTrue(protocol.sources_match(checkout, manifest))
            source.unlink()
            before = self.files()
            self.assertIsNone(protocol.build_manifest(checkout, adapter))
            self.assertFalse(protocol.sources_match(checkout, manifest))
            self.assertEqual(self.files(), before)
            source.write_bytes(original)
            read_bytes = Path.read_bytes
            def unreadable(path):
                if path == source:
                    raise OSError('PRIVATE_SOURCE_READ_FAILURE')
                return read_bytes(path)
            with patch.object(Path, 'read_bytes', unreadable):
                self.assertIsNone(protocol.build_manifest(checkout, adapter))
                self.assertFalse(protocol.sources_match(checkout, manifest))

    def test_birth_match_mismatch_and_both_repeat_directions_preserve_immutable_record(self):
        for adapter in ('cli', 'openai-compatible'):
            for matching in (True, False):
                with self.subTest(adapter=adapter, matching=matching):
                    path, snapshot, observed = self.birth_fixture(adapter, matching=matching)
                    with patch.object(runtime_ownership, 'capture_birth', return_value=observed):
                        birth = runtime_ownership.record_worker_birth(path, snapshot)
                        if matching:
                            self.assertEqual(birth['wrapper_protocol'], snapshot['wrapper_protocol'])
                        else:
                            self.assertNotIn('wrapper_protocol', birth)
                        before = self.files()
                        self.assertEqual(runtime_ownership.record_worker_birth(path, snapshot), birth)
                        self.assertEqual(self.files(), before)
                        # Opposite source comparison changes the proposed outcome for SAME attempt.
                        with patch('runtime_protocol.sources_match', return_value=not matching):
                            with self.assertRaises(ValueError):
                                runtime_ownership.record_worker_birth(path, snapshot)
                        self.assertEqual(self.files(), before)
                        self.assertEqual(birth['ownership'], snapshot['ownership'])
                        self.assertEqual(birth['pid'], observed['pid'])

    def test_snapshot_validation_rejects_malformed_manifest_before_launch_record_changes(self):
        protocol = importlib.import_module('runtime_protocol')
        path, snapshot, _ = self.birth_fixture('cli')
        manifest = snapshot['wrapper_protocol']
        for value in ({**manifest, 'version': 99}, {**manifest, 'version': True},
                      {**manifest, 'adapter': 'openai-compatible'},
                      {**manifest, 'sources': {}}, {**manifest, 'capabilities': ['unknown']},
                      {**manifest, 'sources': {**manifest['sources'], 'secret/path': '0' * 64}}):
            changed = deepcopy(snapshot)
            changed['wrapper_protocol'] = value
            before = self.files()
            with self.subTest(value=value), self.assertRaises(ValueError):
                runtime_ownership.record_spawn_outcome(path, changed, 'spawned')
            self.assertEqual(self.files(), before)
        self.assertEqual(protocol.validate_manifest(manifest, 'cli'), manifest)

    def test_fixture_supported_cli_and_api_project_manifest_and_ownership_fingerprint(self):
        for seat in ('api', 'cli'):
            with self.subTest(seat=seat):
                instance, attempt, birth = self.launch_binding(seat, supported=True)
                snapshot = json.loads(attempt['snapshot'].read_text(encoding='utf-8'))
                provenance = self.manager.launch_provenance(instance)
                self.assertEqual(provenance['effective']['wrapper_protocol'], snapshot['wrapper_protocol'])
                self.assertEqual(birth['wrapper_protocol'], snapshot['wrapper_protocol'])
                result = self.assert_gate(instance, available=True, reason=None)
                self.assertEqual(result['adapter'], 'cli' if seat == 'cli' else 'openai-compatible')
                self.assertEqual(result['fingerprint'], snapshot['ownership']['fingerprint'])
                self.assertEqual(result['launch_nonce'], snapshot['ownership']['launch_nonce'])
                projected = self.manager._provenance_effective(attempt['effective'])
                projected['wrapper_protocol']['capabilities'].clear()
                self.assertEqual(attempt['effective']['wrapper_protocol']['capabilities'], ['artifact-v1'])
                changed = deepcopy(attempt['effective'])
                changed['wrapper_protocol']['capabilities'] = []
                changed_identity = runtime_ownership.new_launch_identity(fixture.ROOT, changed,
                    'team/' + seat, attempt['id'], self.manager.boot_id)
                self.assertNotEqual(changed_identity['fingerprint'], result['fingerprint'])
                self.assertNotIn(instance['token'], json.dumps(result))
                self.assertNotIn('credential-value-test-only', json.dumps(result))

    def test_fixture_supported_gate_requires_current_boot_lease_receipt_and_live_owner(self):
        instance, attempt, _ = self.launch_binding(supported=True)
        self.assert_gate(instance, available=True, reason=None)
        for field, value in (('adopted_boot', uuid.uuid4().hex), ('authenticated_at', time.time() - 60)):
            original = attempt[field]
            attempt[field] = value
            try:
                self.assert_gate(instance, available=False, reason='runtime_unverified')
            finally:
                attempt[field] = original
        receipt = json.loads(attempt['receipt'].read_text(encoding='utf-8'))
        for change in ({'attempt': uuid.uuid4().hex}, {'identity_id': uuid.uuid4().hex},
                       {'state': 'starting'}, {'adapter_connected': False}):
            atomic_json(attempt['receipt'], {**receipt, **change})
            self.assert_gate(instance, available=False, reason='runtime_unverified')
        atomic_json(attempt['receipt'], receipt)
        attempt['released'] = True
        self.assert_gate(instance, available=False, reason='producer_unavailable')
        attempt['released'] = False
        self.manager.retired_attempts.add(attempt['id'])
        self.assert_gate(instance, available=False, reason='producer_unavailable')
        self.manager.retired_attempts.remove(attempt['id'])
        attempt['process'].poll.return_value = 7
        self.assert_gate(instance, available=False, reason='producer_unavailable')
        attempt['process'].poll.return_value = None
        self.assert_gate(instance, available=True, reason=None)

    def test_omitted_birth_declaration_is_missing_but_present_disagreement_is_changed(self):
        for seat in ('api', 'cli'):
            with self.subTest(seat=seat):
                instance, attempt, birth = self.launch_binding(seat, supported=True, omit_birth_protocol=True)
                self.assertNotIn('wrapper_protocol', birth)
                self.assert_gate(instance, available=False, reason='artifact_capability_missing')
                changed = deepcopy(birth)
                changed['wrapper_protocol'] = deepcopy(attempt['effective']['wrapper_protocol'])
                changed['wrapper_protocol']['capabilities'] = []
                atomic_json(attempt['snapshot'].with_name('birth.json'), changed)
                self.assert_gate(instance, available=False, reason='capability_binding_changed')

    def test_fixture_supported_gate_rechecks_source_hash_disk_identity_and_replaced_seat(self):
        instance, attempt, _ = self.launch_binding(supported=True)
        self.assert_gate(instance, available=True, reason=None)
        with patch('runtime_protocol.sources_match', return_value=False):
            self.assert_gate(instance, available=False, reason='capability_binding_changed')
        path = attempt['snapshot']
        snapshot = json.loads(path.read_text(encoding='utf-8'))
        changed = deepcopy(snapshot)
        changed['ownership']['launch_nonce'] = uuid.uuid4().hex
        atomic_json(path, changed)
        self.assert_gate(instance, available=False, reason='capability_binding_changed')
        atomic_json(path, snapshot)
        self.assert_gate(instance, available=True, reason=None)
        self.registry.deregister(instance['name'])
        replacement = self.registry.register(attempt['base'])
        self.assertNotEqual(replacement['identity_id'], instance['identity_id'])
        self.assertIs(self.manager.artifact_producer(instance)['available'], False)
        self.assertIs(self.manager.artifact_producer(replacement)['available'], False)

    def test_legacy_restart_adoption_never_upgrades_manifest_or_spawns_another_worker(self):
        instance, attempt, birth = self.launch_binding()
        before = self.files()
        calls = self.spawn.call_count
        manager = type(self.manager)(fixture.ROOT, self.manager.config, self.store,
                                    self.registry, monitor=False)
        self.addCleanup(manager.shutdown)
        self.assertIs(manager.artifact_producer(instance)['available'], False)
        with patch('runtime_adoption.open_verified_process',
                   return_value={'status': 'live', 'process': attempt['process']}):
            reply = manager.observe_runtime_heartbeat(instance,
                runtime_ownership.heartbeat_payload(birth, manager.boot_id))
        self.assertTrue(reply['verified'], reply)
        result = manager.artifact_producer(instance)
        self.assertIs(result['available'], False)
        self.assertEqual(result['reason'], 'artifact_capability_missing')
        self.assertEqual(result['capabilities'], [])
        self.assertNotIn('wrapper_protocol', json.loads(attempt['snapshot'].read_text(encoding='utf-8')))
        self.assertNotIn('wrapper_protocol', json.loads(attempt['snapshot'].with_name('birth.json').read_text(encoding='utf-8')))
        self.assertEqual(self.files(), before)
        self.assertEqual(self.spawn.call_count, calls)

    def test_fixture_supported_gate_is_detached_readonly_and_never_adopts_or_controls(self):
        instance, attempt, _ = self.launch_binding(supported=True)
        before = self.files()
        calls = self.spawn.call_count
        with (patch.object(self.manager, '_inspect', side_effect=AssertionError('no inspection/control')),
              patch.object(self.manager, 'reconcile_runtime', side_effect=AssertionError('no adoption'))):
            result = self.assert_gate(instance, available=True, reason=None)
            result['capabilities'].clear()
            result['identity_id'] = uuid.uuid4().hex
            self.assert_gate(instance, available=True, reason=None)
            for value in (None, {}, 'not-an-instance', {'identity_id': uuid.uuid4().hex}):
                denied = self.manager.artifact_producer(value)
                self.assertIs(denied['available'], False)
                self.assertEqual(denied['capabilities'], [])
        self.assertEqual(self.files(), before)
        self.assertEqual(self.spawn.call_count, calls)
        attempt['process'].terminate.assert_not_called()
        attempt['process'].wait.assert_not_called()
        self.assertFalse((self.root / 'artifacts').exists())
        self.assertFalse((self.root / 'artifact_briefs').exists())
        self.assertFalse((self.root / 'queue').exists())


if __name__ == '__main__':
    unittest.main()
