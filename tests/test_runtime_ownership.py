"""Immutable launch manifests and truthful self-birth evidence, no adoption."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class RuntimeOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.ownership = importlib.import_module('runtime_ownership')
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.data = self.root / 'data'
        self.effective = {'seat': {'id': 'api', 'name': 'Fixture', 'adapter': 'openai-compatible',
            'provider': 'fake', 'model': 'SOURCE_MODEL_SENTINEL', 'reasoning': None,
            'secret_ref': 'CREDENTIAL_REFERENCE_SENTINEL'},
            'provider': {'base_url': 'http://127.0.0.1:19999/v1',
                         'system_prompt': 'PRIVATE_PROVIDER_SOURCE_SENTINEL'},
            'server': {'data_dir': str(self.data), 'host': '127.0.0.1', 'port': 19998},
            'mcp': {'http_port': 19997, 'sse_port': 19996}}
        self.key, self.attempt, self.boot = 'team/api', uuid.uuid4().hex, uuid.uuid4().hex

    def identity(self, **changes):
        return self.ownership.new_launch_identity(changes.get('root', self.root),
            changes.get('effective', self.effective), changes.get('key', self.key),
            changes.get('attempt', self.attempt), changes.get('boot_id', self.boot))

    def snapshot(self):
        identity = self.identity()
        base = 'api-' + hashlib.sha256(self.key.encode()).hexdigest()[:8] + '-' + self.attempt[:12]
        snapshot = {**deepcopy(self.effective), 'attempt': self.attempt, 'base': base, 'ownership': identity}
        path = self.data / 'api_seat_runtime' / self.attempt / 'config.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot), encoding='utf-8')
        return path, snapshot

    def files(self):
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}

    def birth_values(self, value):
        if isinstance(value, dict):
            if 'creation_filetime' in value:
                return value
            for child in value.values():
                found = self.birth_values(child)
                if found is not None:
                    return found
        return None

    def test_identity_excludes_raw_settings_and_matches_exact_fingerprint(self):
        identity = self.identity()
        self.assertEqual(identity['version'], 1)
        self.assertEqual(identity['root_path'], str(self.root.resolve()))
        self.assertEqual(identity['data_path'], str(self.data.resolve()))
        self.assertEqual(identity['launch_key'], self.key)
        self.assertEqual(identity['attempt'], self.attempt)
        self.assertEqual(identity['boot_id'], self.boot)
        self.assertEqual(identity['fingerprint'], hashlib.sha256(json.dumps(self.effective, sort_keys=True).encode()).hexdigest())
        self.assertRegex(identity['launch_nonce'], r'^[0-9a-f]{32}$')
        serialized = json.dumps(identity)
        for private in ('SOURCE_MODEL_SENTINEL', 'PRIVATE_PROVIDER_SOURCE_SENTINEL', 'CREDENTIAL_REFERENCE_SENTINEL'):
            self.assertNotIn(private, serialized)

    def test_new_nonce_and_boot_keep_static_server_identity(self):
        first = self.identity()
        second = self.identity(boot_id=uuid.uuid4().hex)
        self.assertNotEqual(first['launch_nonce'], second['launch_nonce'])
        self.assertNotEqual(first['boot_id'], second['boot_id'])
        self.assertEqual(first['server_identity'], second['server_identity'])
        equivalent = deepcopy(self.effective)
        equivalent['server']['data_dir'] = str(self.data / 'nested' / '..')
        self.assertEqual(self.identity(effective=equivalent)['server_identity'], first['server_identity'])
        edited = deepcopy(self.effective)
        edited['seat']['model'] = 'different-model'
        self.assertEqual(self.identity(effective=edited)['server_identity'], first['server_identity'])
        self.assertNotEqual(self.identity(effective=edited)['fingerprint'], first['fingerprint'])
        other_port = deepcopy(self.effective)
        other_port['server']['port'] += 1
        self.assertNotEqual(self.identity(effective=other_port)['server_identity'], first['server_identity'])

    def test_factory_rejects_malformed_attempt_boot_and_launch_key(self):
        for field in ('attempt', 'boot_id'):
            for value in (None, True, '', 'x' * 32, uuid.uuid4().hex[:-1]):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.identity(**{field: value})
        for value in (None, True, '', '../team/api', 'team/../api', 'team/api/extra'):
            with self.subTest(key=value), self.assertRaises(ValueError):
                self.identity(key=value)
        self.assertEqual(self.files(), {})

    def test_manifest_pending_spawned_failed_transitions_and_repeated_outcomes(self):
        path, snapshot = self.snapshot()
        identity = deepcopy(snapshot['ownership'])
        self.ownership.record_spawn_outcome(path, snapshot, 'pending')
        manifest_path = path.with_name('launch.json')
        pending = json.loads(manifest_path.read_text('utf-8'))
        self.assertEqual(pending, {**identity, 'spawn_outcome': 'pending'})
        pending_bytes = manifest_path.read_bytes()
        self.ownership.record_spawn_outcome(path, snapshot, 'pending')
        self.assertEqual(manifest_path.read_bytes(), pending_bytes)
        self.ownership.record_spawn_outcome(path, snapshot, 'spawned')
        spawned = manifest_path.read_bytes()
        self.ownership.record_spawn_outcome(path, snapshot, 'spawned')
        self.assertEqual(manifest_path.read_bytes(), spawned)
        for invalid in ('failed', 'pending', 'unknown', True):
            with self.subTest(outcome=invalid), self.assertRaises(ValueError):
                self.ownership.record_spawn_outcome(path, snapshot, invalid)
            self.assertEqual(manifest_path.read_bytes(), spawned)
        self.assertEqual(snapshot['ownership'], identity)
        # A separately reserved launch may truthfully fail before spawning.
        self.attempt = uuid.uuid4().hex
        failed_path, failed_snapshot = self.snapshot()
        self.ownership.record_spawn_outcome(failed_path, failed_snapshot, 'pending')
        self.ownership.record_spawn_outcome(failed_path, failed_snapshot, 'failed')
        failed = failed_path.with_name('launch.json').read_bytes()
        self.ownership.record_spawn_outcome(failed_path, failed_snapshot, 'failed')
        self.assertEqual(failed_path.with_name('launch.json').read_bytes(), failed)
        with self.assertRaises(ValueError):
            self.ownership.record_spawn_outcome(failed_path, failed_snapshot, 'spawned')

    def test_wrong_reference_or_runtime_path_rejects_before_any_write(self):
        path, snapshot = self.snapshot()
        before = self.files()
        mutations = []
        for field, value in (('attempt', uuid.uuid4().hex), ('base', 'api-wrong-base')):
            changed = deepcopy(snapshot)
            changed[field] = value
            mutations.append(changed)
        for field, value in (('version', True), ('launch_nonce', 'invalid'), ('launch_key', '../bad/api'),
                             ('attempt', uuid.uuid4().hex), ('boot_id', True), ('fingerprint', '0' * 64),
                             ('server_identity', '0' * 64), ('root_path', str(self.root / 'foreign-root')),
                             ('data_path', str(self.root / 'foreign-data')), ('created_at', float('nan'))):
            changed = deepcopy(snapshot)
            changed['ownership'][field] = value
            mutations.append(changed)
        changed = deepcopy(snapshot)
        changed['provider']['system_prompt'] = 'Changed frozen effective profile'
        mutations.append(changed)
        for changed in mutations:
            with self.subTest(ownership=changed['ownership']), self.assertRaises(ValueError):
                self.ownership.record_spawn_outcome(path, changed, 'pending')
            self.assertEqual(self.files(), before)
        for wrong in (self.root / 'escaped' / 'config.json', path.with_name('other.json'),
                      path.parent.parent / uuid.uuid4().hex / 'config.json'):
            with self.subTest(path=wrong), self.assertRaises(ValueError):
                self.ownership.record_spawn_outcome(wrong, snapshot, 'pending')
            self.assertEqual(self.files(), before)

    def test_failed_manifest_atomic_write_preserves_original_exact_bytes(self):
        path, snapshot = self.snapshot()
        self.ownership.record_spawn_outcome(path, snapshot, 'pending')
        before = self.files()
        with patch('runtime_ownership.atomic_json', side_effect=OSError('fixture manifest persistence failure')):
            with self.assertRaises(OSError):
                self.ownership.record_spawn_outcome(path, snapshot, 'spawned')
        self.assertEqual(self.files(), before)
        self.ownership.record_spawn_outcome(path, snapshot, 'spawned')
        self.assertEqual(json.loads(path.with_name('launch.json').read_text('utf-8'))['spawn_outcome'], 'spawned')

    def test_legacy_snapshot_is_readonly_without_manufactured_manifest_or_birth(self):
        path, snapshot = self.snapshot()
        snapshot.pop('ownership')
        path.write_text(json.dumps(snapshot), encoding='utf-8')
        before = self.files()
        self.assertIsNone(self.ownership.record_spawn_outcome(path, snapshot, 'pending'))
        self.assertIsNone(self.ownership.record_worker_birth(path, snapshot))
        self.assertEqual(self.files(), before)

    @unittest.skipUnless(sys.platform == 'win32', 'actual current Windows process birth')
    def test_worker_birth_is_actual_self_and_idempotent_before_ready(self):
        path, snapshot = self.snapshot()
        self.ownership.record_spawn_outcome(path, snapshot, 'pending')
        self.ownership.record_worker_birth(path, snapshot)
        record_path = path.with_name('birth.json')
        record = json.loads(record_path.read_text('utf-8'))
        birth = self.birth_values(record)
        expected = importlib.import_module('process_identity').capture_birth()
        self.assertIsNotNone(birth)
        for key, value in expected.items():
            self.assertEqual(birth[key], value)
        self.assertEqual(birth['pid'], os.getpid())
        self.assertEqual(record['attempt'], snapshot['attempt'])
        self.assertEqual(record['base'], snapshot['base'])
        self.assertEqual(record['ownership'], snapshot['ownership'])
        self.assertEqual(record['worker_root'], str(Path(self.ownership.__file__).resolve().parent))
        before = record_path.read_bytes()
        self.ownership.record_worker_birth(path, snapshot)
        self.assertEqual(record_path.read_bytes(), before)

    @unittest.skipUnless(sys.platform == 'win32', 'actual current Windows process birth')
    def test_conflicting_existing_birth_never_overwrites_evidence(self):
        path, snapshot = self.snapshot()
        self.ownership.record_spawn_outcome(path, snapshot, 'pending')
        self.ownership.record_worker_birth(path, snapshot)
        record_path = path.with_name('birth.json')
        record = json.loads(record_path.read_text('utf-8'))
        birth = self.birth_values(record)
        birth['creation_filetime'] = str(int(birth['creation_filetime']) + 1)
        record_path.write_text(json.dumps(record), encoding='utf-8')
        before = record_path.read_bytes()
        with self.assertRaises(ValueError):
            self.ownership.record_worker_birth(path, snapshot)
        self.assertEqual(record_path.read_bytes(), before)

    @unittest.skipUnless(sys.platform == 'win32', 'actual current Windows process birth')
    def test_failed_birth_atomic_write_preserves_manifest_and_snapshot(self):
        path, snapshot = self.snapshot()
        self.ownership.record_spawn_outcome(path, snapshot, 'pending')
        before = self.files()
        with patch('runtime_ownership.atomic_json', side_effect=OSError('fixture birth persistence failure')):
            with self.assertRaises(OSError):
                self.ownership.record_worker_birth(path, snapshot)
        self.assertEqual(self.files(), before)


if __name__ == '__main__':
    unittest.main()
