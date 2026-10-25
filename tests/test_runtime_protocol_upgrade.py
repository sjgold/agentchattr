"""Old managed metadata survives source-set growth; native observations are doubles."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import uuid

from api_seat_runtime import SeatManager
from api_seats import atomic_json
from dispatch_queue import QueueStore
import runtime_adoption
import runtime_ownership
import runtime_protocol as protocol
from tests import test_artifact_capability as fixture


ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / 'tests' / 'fixtures' / 'artifact_old_manifests.json').read_text(encoding='utf-8'))
OLD_SETS = {key: tuple(value) for key, value in VECTORS['source_names'].items()}


class RuntimeProtocolUpgradeTests(unittest.TestCase):
    def context(self):
        case = fixture.ArtifactCapabilityTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        return case

    def old_launch(self, case, seat, capabilities):
        original = case.manager._effective
        def effective(selected):
            value = original(selected)
            value['wrapper_protocol']['capabilities'] = deepcopy(capabilities)
            return value
        # Explicit old-schema observation: same real launch/birth functions,
        # but the old13/27 source sets before returning to current server code.
        with patch.object(protocol, 'SOURCE_FILES', OLD_SETS), patch.object(case.manager, '_effective', side_effect=effective):
            case.manager.launch('team', seat)
            attempt = case.manager.attempts['team/' + seat]
            snapshot = json.loads(attempt['snapshot'].read_text(encoding='utf-8'))
            before_provenance = case.manager._provenance_effective(attempt['effective'])
            process = attempt['process']
            process.pid = 47000 + len(case.processes)
            observed = {'platform': 'win32', 'pid': process.pid, 'creation_filetime': '990123456',
                        'image_path': str(case.root / 'fixture-python.exe')}
            with patch('runtime_ownership.capture_birth', return_value=observed):
                birth = runtime_ownership.record_worker_birth(attempt['snapshot'], snapshot)
        instance = case.registry.register(attempt['base'])
        receipt = {'attempt': attempt['id'], 'state': 'ready', 'name': instance['name'],
            'identity_id': instance['identity_id'], 'adapter_connected': True,
            'authentication': 'unknown', 'updated_at': time.time()}
        atomic_json(attempt['receipt'], receipt)
        return instance, attempt, snapshot, birth, receipt, before_provenance

    def test_old_manifest_ownership_and_provenance_match_prechange_literal_vectors(self):
        for row in VECTORS['rows']:
            with self.subTest(adapter=row['adapter'], capability=row['effective']['wrapper_protocol']['capabilities']):
                effective = deepcopy(row['effective'])
                self.assertEqual(protocol.validate_manifest(effective['wrapper_protocol'], row['adapter']), effective['wrapper_protocol'])
                identity = runtime_ownership.new_launch_identity(ROOT, effective, 'golden/author', '1' * 32, '2' * 32)
                self.assertEqual(identity['fingerprint'], row['ownership_fingerprint'])
                projected = SeatManager._provenance_effective(effective)
                self.assertEqual(hashlib.sha256(json.dumps(projected, sort_keys=True).encode('utf-8')).hexdigest(),
                                 row['provenance_fingerprint'])
                self.assertFalse(protocol.sources_match(ROOT, effective['wrapper_protocol']))

    def test_old_sets_preserve_ownership_candidate_cold_heartbeat_exit_and_release_without_capability(self):
        for seat, adapter in (('cli', 'cli'), ('api', 'openai-compatible')):
            for capabilities in ([], ['artifact-v1']):
                with self.subTest(adapter=adapter, capabilities=capabilities):
                    case = self.context()
                    instance, attempt, snapshot, birth, receipt, before_provenance = self.old_launch(case, seat, capabilities)
                    self.assertEqual(runtime_ownership._validate(attempt['snapshot'], snapshot)[0], snapshot['ownership'])
                    self.assertEqual(runtime_adoption._candidate(case.manager, attempt['snapshot'])['birth'], birth)
                    cold = SeatManager(ROOT, case.manager.config, case.store, case.registry, monitor=False)
                    self.addCleanup(cold.shutdown)
                    process = attempt['process']
                    with patch('runtime_adoption.open_verified_process', return_value={'status': 'live', 'process': process}):
                        reply = cold.observe_runtime_heartbeat(instance,
                            runtime_ownership.heartbeat_payload(birth, cold.boot_id))
                    self.assertTrue(reply['verified'], reply)
                    self.assertEqual(cold.artifact_producer(instance)['reason'], 'artifact_capability_missing')
                    provenance = cold.launch_provenance(instance)
                    self.assertEqual(provenance['effective'], before_provenance)
                    self.assertEqual(provenance['fingerprint'],
                        hashlib.sha256(json.dumps(before_provenance, sort_keys=True).encode('utf-8')).hexdigest())
                    self.assertEqual(json.loads(attempt['snapshot'].read_text(encoding='utf-8')), snapshot)
                    queue = QueueStore(case.root)
                    dispatch = uuid.uuid4().hex
                    queue.enqueue(instance, {'dispatch_id': dispatch})
                    queue.claim(instance, 'old-worker-consumer')
                    self.assertEqual(queue.release(instance, dispatch, 'old-worker-consumer')['state'], 'released')
                    process.poll.return_value = 0  # Explicit observed-exit double, not native evidence.
                    process.returncode = 0
                    if seat == 'cli':
                        receipt['child_exit_code'] = 23
                    receipt.update(state='failed', adapter_connected=False)
                    atomic_json(attempt['receipt'], receipt)
                    self.assertTrue(cold.participant_exit_proof(provenance, dispatch)['local_ended'])
                    process.terminate.assert_not_called()
                    process.kill.assert_not_called()
                    # A separate fresh seat really goes through manager.launch;
                    # it gets the current source set while capability stays off.
                    fresh = next(item for item in case.package['seats'] if item['id'] == seat)
                    case.package['seats'].append({**fresh, 'id': seat + 'fresh', 'name': 'Fresh ' + seat})
                    case.store.save(case.package)
                    case.manager.launch('team', seat + 'fresh')
                    current = case.manager.attempts['team/' + seat + 'fresh']['effective']['wrapper_protocol']
                    self.assertEqual(set(current['sources']), set(protocol.SOURCE_FILES[adapter]))
                    self.assertEqual(current['capabilities'], [])

    def test_structure_is_bounded_and_no_snapshot_filename_can_drive_source_reads(self):
        current = protocol.build_manifest(ROOT, 'cli')
        for key in ('../x.py', 'a/b.py', 'A.py', '.py', 'x..py'):
            with self.subTest(key=key), patch.object(Path, 'read_bytes', side_effect=AssertionError('Snapshot path read')) as read:
                value = {**current, 'sources': {key: '0' * 64}}
                with self.assertRaises(ValueError):
                    protocol.validate_manifest(value, 'cli')
                self.assertFalse(protocol.sources_match(ROOT, value))
                read.assert_not_called()
        maximum = {**current, 'sources': {'f' + str(i) + '.py': '0' * 64 for i in range(128)}}
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Metadata attempted IO')):
            self.assertEqual(protocol.validate_manifest(maximum, 'cli'), maximum)
        for change in ({'sources': {**maximum['sources'], 'overflow.py': '0' * 64}}, {'sources': {}},
                       {'version': True}, {'version': 2}, {'adapter': 'openai-compatible'},
                       {'sources': {'safe.py': 'A' * 64}}):
            with self.subTest(change=tuple(change)), self.assertRaises(ValueError):
                protocol.validate_manifest({**current, **change}, 'cli')
        original_read = Path.read_bytes
        read_names = []
        def read_current(path):
            read_names.append(path.name)
            self.assertIn(path.name, protocol.SOURCE_FILES['cli'])
            return original_read(path)
        extra = {**current, 'sources': {**current['sources'], 'safe_extra.py': '0' * 64}}
        protocol.validate_manifest(extra, 'cli')
        with patch.object(Path, 'read_bytes', read_current):
            self.assertFalse(protocol.sources_match(ROOT, extra))
        self.assertNotIn('safe_extra.py', read_names)

    def test_new_birth_does_not_copy_old_source_set_and_cannot_overwrite_its_first_outcome(self):
        for adapter in ('cli', 'openai-compatible'):
            with self.subTest(adapter=adapter):
                case = self.context()
                with patch.object(protocol, 'SOURCE_FILES', OLD_SETS):
                    path, snapshot, observed = case.birth_fixture(adapter)
                with patch('runtime_ownership.capture_birth', return_value=observed):
                    birth = runtime_ownership.record_worker_birth(path, snapshot)
                    self.assertNotIn('wrapper_protocol', birth)
                    before = path.with_name('birth.json').read_bytes()
                    self.assertEqual(runtime_ownership.record_worker_birth(path, snapshot), birth)
                    with patch('runtime_protocol.sources_match', return_value=True), self.assertRaises(ValueError):
                        runtime_ownership.record_worker_birth(path, snapshot)
                    self.assertEqual(path.with_name('birth.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
