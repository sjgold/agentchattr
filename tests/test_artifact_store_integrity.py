"""Root-owned hand-edited index/object fixtures; not public or native setup."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import artifact_store
from tests import test_artifact_store as fixture


class ArtifactIndexIntegrityTests(unittest.TestCase):
    def context(self):
        case = fixture.ArtifactStoreTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        module, store = case.owner()
        return case, module, store

    def test_lazy_packet_binding_fails_only_that_object_and_allows_unrelated_work(self):
        for mutation in ('channel', 'source_run', 'input_revision', 'message_order'):
            with self.subTest(mutation=mutation):
                case, module, store = self.context()
                packet = case.packet()
                if mutation == 'source_run':
                    source = 'Frozen café\r\nsource'
                    revision = hashlib.sha256(source.encode('utf-8')).hexdigest()
                    packet['input'] = {'text': source, 'input_revision': revision, 'source_document': None}
                    packet['source_run'] = {'session_id': 7, 'run_id': 'c' * 32,
                        'input_revision': revision, 'state_at_request': 'active'}
                if mutation == 'message_order':
                    packet['messages'].append({**deepcopy(packet['messages'][0]), 'id': 1, 'uid': 'source-one'})
                audit = case.audit(module, store, packet=packet)
                audit['source_run'] = deepcopy(packet['source_run'])
                store.reserve_request(audit, audit['request_id'])
                value = json.loads(store.path.read_text(encoding='utf-8'))
                changed = value['requests'][audit['request_id']]['audit']
                if mutation == 'channel':
                    changed['original_channel'] = 'peer'
                elif mutation == 'source_run':
                    changed['source_run']['state_at_request'] = 'stopped'
                elif mutation == 'input_revision':
                    changed['scope']['input_revision'] = 'f' * 64
                else:
                    changed['scope']['message_refs'].reverse()
                store.path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
                restored = module.ArtifactStore(case.root)  # Metadata remains well-formed.
                restored.bind_channel_policy(lambda: case.service)
                with self.assertRaises(module.ArtifactUnavailable):
                    restored.get_packet(audit['scope']['packet_id'])
                self.assertIn(audit['scope']['packet_id'], json.dumps(restored.diagnostics()))
                with self.assertRaises(module.ArtifactUnavailable):
                    restored.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                        {'state': 'queued', 'reason': 'queued'}, now=20)
                self.assertEqual(restored.get_request(audit['request_id'])['state'], 'prepared')
                self.assertEqual(restored.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                    {'state': 'cancelled', 'reason': 'source_packet_unavailable'}, now=21)['state'], 'cancelled')
                peer = case.queued(module, restored, channel='peer')
                self.assertEqual(case.commit(restored, peer, '# Healthy peer\r\n')['sequence'], 1)
                other = case.queued(module, restored, channel='peer')
                self.assertEqual(restored.set_attempt_state(other['request_id'], other['attempt_id'], 'queued',
                    {'state': 'cancelled', 'reason': 'operator_cancelled'}, now=40)['state'], 'cancelled')

    def test_index_cross_reference_corruption_holds_fresh_owners_without_repair(self):
        case, module, store = self.context()
        first_request = case.queued(module, store)
        first = case.commit(store, first_request, '# One\r\n')
        parent = {'version_id': first['id'], 'sequence': 1, 'sha256': first['sha256']}
        second_request = case.queued(module, store, lineage_id=first['lineage_id'], parent=parent)
        second = case.commit(store, second_request, '# Two\r\n')
        pending = case.queued(module, store, lineage_id=first['lineage_id'], parent={
            'version_id': second['id'], 'sequence': 2, 'sha256': second['sha256']})
        original = json.loads(store.path.read_text(encoding='utf-8'))
        r1, r2, rp, lineage = first_request['request_id'], second_request['request_id'], pending['request_id'], first['lineage_id']
        def request_change(value, request_id, change):
            value['requests'][request_id].update(change)
        def parent_change(value, request_id, change):
            value['requests'][request_id]['audit']['expected_parent'].update(change)
        def version_change(value, change):
            value['versions'][second['id']].update(change)
        def audit_change(value, change):
            value['requests'][rp]['audit'].update(change)
        def dangling_request(value, version_id):
            request_change(value, rp, {'state': 'fulfilled', 'version_id': version_id})
            value['lineages'][lineage]['pending_request_id'] = None
        def imported_without_version(value):
            dangling_request(value, None)
            value['requests'][rp]['state'] = 'imported'
        cases = [
            ('imported-unversioned-row', imported_without_version),
            ('dangling-request-version', lambda v: dangling_request(v, 'f' * 32)),
            ('another-request-version', lambda v: dangling_request(v, first['id'])),
            ('accepted-parent-hash', lambda v: parent_change(v, r2, {'sha256': '0' * 64})),
            ('accepted-parent-sequence', lambda v: parent_change(v, r2, {'sequence': 9})),
            ('pending-parent-hash', lambda v: parent_change(v, rp, {'sha256': '0' * 64})),
            ('pending-parent-sequence', lambda v: parent_change(v, rp, {'sequence': 9})),
            ('pending-stale-head', lambda v: parent_change(v, rp, parent)),
            ('noncontiguous-sequence', lambda v: version_change(v, {'sequence': 3})),
            ('wrong-head', lambda v: v['lineages'][lineage].update(head_version_id=first['id'])),
            ('wrong-version-parent', lambda v: version_change(v, {'parent_version_id': None})),
            ('nonlive-pending-slot', lambda v: v['lineages'][lineage].update(pending_request_id=r1)),
            ('missing-pending-slot', lambda v: v['lineages'][lineage].update(pending_request_id=None)),
            ('two-live-requests', lambda v: request_change(v, r1, {'state': 'queued', 'version_id': None})),
            ('wrong-request-version', lambda v: request_change(v, r2, {'version_id': first['id']})),
            ('wrong-version-request', lambda v: version_change(v, {'request_id': r1})),
            ('wrong-version-attempt', lambda v: version_change(v, {'attempt_id': 'e' * 32})),
            ('wrong-version-dispatch', lambda v: version_change(v, {'dispatch_id': 'e' * 32})),
            ('wrong-version-lineage', lambda v: version_change(v, {'lineage_id': 'e' * 32})),
            ('fulfilled-without-version', lambda v: request_change(v, r1, {'version_id': None})),
            ('imported-without-version', lambda v: request_change(v, r1, {'state': 'imported', 'version_id': None})),
            ('version-request-not-fulfilled', lambda v: request_change(v, r1, {'state': 'failed'})),
            ('bad-original-channel', lambda v: audit_change(v, {'original_channel': 'NOT VALID'})),
            ('bad-derived-attempt', lambda v: audit_change(v, {'attempt_id': 'e' * 32})),
            ('bad-request-key', lambda v: audit_change(v, {'request_id': 'e' * 32})),
            ('bad-packet-reference', lambda v: v['requests'][rp]['audit']['scope'].update(packet_id='e' * 32)),
            ('malformed-scope-hash', lambda v: v['requests'][rp]['audit']['scope'].update(sha256='not-a-hash')),
        ]
        for label, mutate in cases:
            with self.subTest(mutation=label):
                value = deepcopy(original)
                mutate(value)
                bad = json.dumps(value, ensure_ascii=False).encode('utf-8')
                store.path.write_bytes(bad)
                with self.assertRaises(module.ArtifactUnavailable):
                    module.ArtifactStore(case.root)
                held = module.ArtifactStore(case.root, hold_unreadable=True)
                held.bind_channel_policy(lambda: case.service)
                for operation in (held.list_lineages, lambda: held.get_request(r1), lambda: held.get_version(first['id']),
                        lambda: held.set_attempt_state(rp, pending['attempt_id'], 'queued',
                            {'state': 'cancelled', 'reason': 'operator_cancelled'}, now=50),
                        lambda: held.quarantine_submission(None, uuid.uuid4().hex, uuid.uuid4().hex,
                            reason='unmatched_saved_result', content=None)):
                    with self.assertRaises(module.ArtifactUnavailable):
                        operation()
                self.assertEqual(store.path.read_bytes(), bad)

    def test_valid_index_load_does_not_scan_immutable_bodies(self):
        case, module, store = self.context()
        audit = case.queued(module, store)
        case.commit(store, audit)
        original = Path.open
        def no_bodies(path, *args, **kwargs):
            if path.suffix == '.md' or 'packets' in path.parts:
                raise AssertionError('Index load scanned an immutable body')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', no_bodies):
            restored = module.ArtifactStore(case.root)
            self.assertEqual(restored.list_lineages()['count'], 1)


if __name__ == '__main__':
    unittest.main()
