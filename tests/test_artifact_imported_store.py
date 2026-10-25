"""Whole-lineage imported storage with real files/catalog and metadata producers.

No producer is managed or live here; no dispatch, worker, provider or app factory.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import artifact_store
from tests import test_artifact_store as fixture


class ArtifactImportedStoreTests(unittest.TestCase):
    def setUp(self):
        fixture.ArtifactStoreTests.setUp(self)
        self.source = artifact_store.ArtifactStore(self.root / 'source')
        self.target = artifact_store.ArtifactStore(self.root / 'target')
        for owner in (self.source, self.target):
            owner.bind_channel_policy(lambda: self.service)

    packet = fixture.ArtifactStoreTests.packet
    audit = fixture.ArtifactStoreTests.audit

    @staticmethod
    def files(owner):
        root = owner.path.parent.parent
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def source_graph(self, text='\ufeff# Café 日本語 e\u0301\r\n\r\nExact bytes.\r\n', *, attempts=True):
        audit = self.audit(artifact_store, self.source)
        self.source.reserve_request(audit, audit['request_id'])
        self.source.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                                     {'state': 'queued', 'reason': 'queued'}, now=20)
        version = self.source.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
            text, {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'}, now=30)
        if attempts:
            parent = {'version_id': version['id'], 'sequence': 1, 'sha256': version['sha256']}
            failed = self.audit(artifact_store, self.source, lineage_id=audit['lineage_id'], parent=parent)
            self.source.reserve_request(failed, failed['request_id'])
            self.source.set_attempt_state(failed['request_id'], failed['attempt_id'], 'prepared',
                                         {'state': 'failed', 'reason': 'generation_failed'}, now=40)
            pending = self.audit(artifact_store, self.source, lineage_id=audit['lineage_id'], parent=parent)
            self.source.reserve_request(pending, pending['request_id'])
        return self.portable(self.source, audit['lineage_id']), audit, version

    def portable(self, owner, lineage_id, archive_id='archive-fixture'):
        snapshot = owner.export_metadata(lineage_id)
        lineage = snapshot['lineage']
        requests, versions, objects = [], [], {}
        for row in snapshot['requests']:
            audit = row['audit']
            producer = audit['producer']
            requests.append({'request_id': audit['request_id'], 'original_channel': audit['original_channel'],
                'requester': audit['requester'], 'producer': {key: deepcopy(producer[key]) for key in
                    ('name', 'identity_id', 'adapter', 'requested_model', 'requested_model_reason')},
                'source_run': deepcopy(audit['source_run']), 'scope': deepcopy(audit['scope']),
                'instruction': audit['instruction'], 'format': audit['format'],
                'expected_parent': deepcopy(audit['expected_parent']), 'created_at': audit['created_at'],
                'updated_at': row['updated_at'], 'import_source': deepcopy(row.get('import_source',
                    {'archive_id': archive_id, 'original_state': row['state'], 'original_reason': row['reason']}))})
            scope = audit['scope']
            objects[('packet', scope['packet_id'])] = owner.read_archive_object('packet', scope['packet_id'],
                sha256=scope['sha256'], byte_length=scope['byte_length'])
        for version in snapshot['versions']:
            versions.append({'version_id': version['id'], 'request_id': version['request_id'],
                'sequence': version['sequence'], 'parent_version_id': version['parent_version_id'],
                'sha256': version['sha256'], 'byte_length': version['byte_length'],
                'created_at': version['created_at'], 'observation': deepcopy(version['provenance']['observation'])})
            objects[('version', version['id'])] = owner.read_archive_object('version', version['id'],
                sha256=version['sha256'], byte_length=version['byte_length'])
        portable = {'lineage_id': lineage['id'], 'channel': lineage['channel'],
            'updated_at': lineage['updated_at'], 'head_version_id': lineage['head_version_id'],
            'requests': sorted(requests, key=lambda row: row['request_id']),
            'versions': sorted(versions, key=lambda row: row['sequence'])}
        return portable, objects

    def import_graph(self, graph, *, owner=None, channel='review', archive_id='archive-fixture'):
        owner = owner or self.target
        portable, objects = graph
        prepared = owner.prepare_import_lineage(portable, objects, archive_id=archive_id)
        with self.service._boundary():
            result = owner.import_lineage(prepared, channel=channel)
        return result

    def test_whole_lineage_import_preserves_raw_history_and_unversioned_attempts_without_authority(self):
        graph, audit, version = self.source_graph()
        original_files = self.files(self.source)
        result = self.import_graph(graph)
        self.assertEqual(result, {'status': 'created', 'reason': None, 'collision_kinds': [],
                                  'created_versions': 1, 'created_requests': 3})
        saved = self.target.get_version(version['id'])
        self.assertEqual(saved['markdown'].encode('utf-8'), graph[1][('version', version['id'])])
        self.assertEqual(saved['metadata']['provenance']['observation'], version['provenance']['observation'])
        for request in graph[0]['requests']:
            row = self.target.get_request(request['request_id'])
            self.assertEqual((row['state'], row['reason']), ('imported', 'imported'))
            self.assertEqual(row['import_source'], request['import_source'])
            self.assertEqual(row['audit']['scope'], request['scope'])
            self.assertEqual(row['audit']['producer']['capabilities'], [])
            for field in ('launch_attempt', 'launch_nonce', 'fingerprint'):
                self.assertIsNone(row['audit']['producer'][field])
            self.assertEqual(row['audit']['producer']['requested_model_reason'], 'CLI model unverified')
            self.assertEqual(row['version_id'], version['id'] if request['request_id'] == audit['request_id'] else None)
        self.assertEqual(self.target.pending('review'), [])
        lineage = self.target.list_lineages()['rows'][0]
        self.assertIsNone(lineage['pending_request_id'])
        self.assertEqual(lineage['head_version_id'], version['id'])
        self.assertFalse((self.root / 'target' / 'artifact_briefs' / 'requests').exists())
        self.assertFalse((self.root / 'target' / 'queue').exists())
        self.assertEqual(self.files(self.source), original_files)

    def test_index_failure_after_staging_preserves_head_metadata_and_orphan_retry_never_overwrites(self):
        graph, audit, version = self.source_graph(attempts=False)
        prepared = self.target.prepare_import_lineage(*graph, archive_id='archive-fixture')
        old_index = self.target.path.read_bytes() if self.target.path.exists() else None
        old_metadata = self.target.list_lineages()
        with patch('artifact_store.atomic_json', side_effect=OSError('Controlled final index failure')):
            with self.service._boundary(), self.assertRaises(artifact_store.ArtifactUnavailable):
                self.target.import_lineage(prepared, channel='review')
        self.assertEqual(self.target.path.read_bytes() if self.target.path.exists() else None, old_index)
        self.assertEqual(self.target.list_lineages(), old_metadata)
        self.assertIsNone(self.target.get_request(audit['request_id']))
        self.assertIn(version['id'], json.dumps(self.target.diagnostics()))
        self.assertFalse(list((self.root / 'target').rglob('*.tmp')))
        changed, objects = deepcopy(graph[0]), dict(graph[1])
        different = b'# Different immutable bytes\r\n'
        changed['versions'][0].update(sha256=hashlib.sha256(different).hexdigest(), byte_length=len(different))
        objects[('version', version['id'])] = different
        with self.assertRaises(artifact_store.ArtifactConflict):
            self.target.prepare_import_lineage(changed, objects, archive_id='archive-fixture')
        self.assertEqual((self.root / 'target' / 'artifacts' / 'objects' / (version['id'] + '.md')).read_bytes(),
                         graph[1][('version', version['id'])])
        fresh = artifact_store.ArtifactStore(self.root / 'target')
        fresh.bind_channel_policy(lambda: self.service)
        self.assertEqual(self.import_graph(graph, owner=fresh)['status'], 'created')
        self.assertEqual(fresh.get_version(version['id'])['markdown'].encode('utf-8'), graph[1][('version', version['id'])])
        self.assertFalse(list((self.root / 'target').rglob('*.tmp')))


if __name__ == '__main__':
    unittest.main()
