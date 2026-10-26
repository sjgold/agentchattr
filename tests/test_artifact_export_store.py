"""Export reads and imported-only index validation; storage fixtures, no import driver."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch
import uuid

import artifact_store as module
from tests import test_artifact_store as fixture


class ArtifactExportStoreTests(unittest.TestCase):
    setUp = fixture.ArtifactStoreTests.setUp
    packet = fixture.ArtifactStoreTests.packet
    audit = fixture.ArtifactStoreTests.audit
    owner = fixture.ArtifactStoreTests.owner

    def seed(self):
        _, store = self.owner('export-source')
        audit = self.audit(module, store)
        store.reserve_request(audit, audit['request_id'])
        store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                                {'state': 'queued', 'reason': 'queued'})
        text = '\ufeff# Caf\u00e9\r\nExact bytes.\r\n'
        version = store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
            text, {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'})
        parent = {key: version[key] for key in ('sequence', 'sha256')}
        parent['version_id'] = version['id']
        second = self.audit(module, store, lineage_id=audit['lineage_id'], parent=parent)
        store.reserve_request(second, second['request_id'])
        return store, audit, second, version, text.encode('utf-8')

    def imported_index(self):
        store, audit, second, version, raw = self.seed()
        index = json.loads(store.path.read_bytes())
        for row in index['requests'].values():
            row['import_source'] = {'archive_id': 'archive-fixture',
                'original_state': row['state'], 'original_reason': row['reason']}
            self.assertNotIn('quarantine_ids', row)  # Real v2 source row, not portable allowlist input.
            row.update(state='imported', reason='imported')
            producer = row['audit']['producer']
            producer.update(adapter='openai-compatible', launch_attempt=None,
                launch_nonce=None, fingerprint=None, capabilities=[])
        index['versions'][version['id']]['provenance']['producer'] = deepcopy(
            index['requests'][audit['request_id']]['audit']['producer'])
        index['versions'][version['id']]['provenance']['observation'] = {
            'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'}
        index['lineages'][audit['lineage_id']]['pending_request_id'] = None
        return index, audit, second, version

    def test_export_snapshot_is_detached_metadata_only_and_objects_are_bound(self):
        _, empty = self.owner('export-empty')
        self.assertEqual(empty.export_lineage_ids(), ())
        self.assertFalse(empty.path.exists())
        store, audit, second, version, raw = self.seed()
        with patch.object(store, '_read_object', side_effect=AssertionError('metadata read a body')):
            self.assertEqual(store.export_lineage_ids(), (audit['lineage_id'],))
            snapshot = store.export_metadata(audit['lineage_id'])
        self.assertEqual(len(snapshot['requests']), 2)
        self.assertEqual([row['id'] for row in snapshot['versions']], [version['id']])
        snapshot['requests'][0]['audit']['instruction'] = 'DETACHED'
        self.assertNotEqual(store.get_request(audit['request_id'])['audit']['instruction'], 'DETACHED')
        self.assertEqual(store.read_archive_object('version', version['id'],
            sha256=version['sha256'], byte_length=len(raw)), raw)
        scope = audit['scope']
        packet = store.read_archive_object('packet', scope['packet_id'],
            sha256=scope['sha256'], byte_length=scope['byte_length'])
        self.assertEqual(hashlib.sha256(packet).hexdigest(), scope['sha256'])
        for kind, identifier, digest, length in (
            ('version', version['id'], 'f'*64, len(raw)),
            ('packet', uuid.uuid4().hex, scope['sha256'], scope['byte_length'])):
            with self.subTest(kind=kind), self.assertRaises(module.ArtifactUnavailable):
                store.read_archive_object(kind, identifier, sha256=digest, byte_length=length)
        with self.assertRaises(module.ArtifactValidationError):
            store.read_archive_object('other', version['id'], sha256=version['sha256'], byte_length=len(raw))
        store.path.write_bytes(b'BROKEN')
        with self.assertRaises(module.ArtifactUnavailable):
            store.export_lineage_ids()
        self.assertEqual(store.path.read_bytes(), b'BROKEN')

    def test_imported_index_accepts_unversioned_attempts_and_reuses_version_validator(self):
        index, audit, second, version = self.imported_index()
        _, target = self.owner('imported-format')
        target.path.parent.mkdir(parents=True)
        target.path.write_text(json.dumps(index), encoding='utf-8')
        with patch.object(module.ArtifactStore, '_validate_version',
                autospec=True, side_effect=module.ArtifactStore._validate_version) as validate:
            fresh = module.ArtifactStore(target.root)
        self.assertEqual(validate.call_count, 1)
        self.assertEqual(fresh.pending('review'), [])
        self.assertIsNone(fresh.get_request(second['request_id'])['version_id'])
        self.assertEqual(fresh.get_request(audit['request_id'])['state'], 'imported')
        before = target.path.read_bytes()
        with self.assertRaises(module.ArtifactConflict):
            fresh.set_attempt_state(second['request_id'], second['attempt_id'], 'imported',
                {'state': 'queued', 'reason': 'queued'})
        self.assertEqual(target.path.read_bytes(), before)
        index['versions'][version['id']]['provenance']['producer']['name'] = 'TAMPER'
        target.path.write_text(json.dumps(index), encoding='utf-8')
        with self.assertRaises(module.ArtifactUnavailable):
            module.ArtifactStore(target.root)

    def test_imported_shape_never_weakens_local_audit_or_origin_validation(self):
        index, audit, second, version = self.imported_index()
        for mutation in ('missing_origin', 'bad_origin', 'local_empty_caps', 'local_api_null', 'extra_key'):
            with self.subTest(mutation=mutation):
                value = deepcopy(index)
                row = value['requests'][second['request_id']]
                if mutation == 'missing_origin':
                    del row['import_source']
                elif mutation == 'bad_origin':
                    row['import_source']['archive_id'] = '../unsafe/token'
                elif mutation == 'extra_key':
                    row['import_source']['token'] = 'EXTRA'
                else:
                    row.pop('import_source')
                    row.update(state='failed', reason='generation_failed')
                    if mutation == 'local_api_null':
                        row['audit']['producer']['capabilities'] = ['artifact-v1']
                _, target = self.owner('shape-' + mutation)
                target.path.parent.mkdir(parents=True)
                target.path.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaises(module.ArtifactUnavailable):
                    module.ArtifactStore(target.root)
        # The accepted CLI/null-ref local storage contract remains valid.
        self.assertEqual(module._audit(audit), audit)

    def test_imported_diagnostics_stand_alone_and_never_attach_or_reactivate(self):
        index, audit, second, version = self.imported_index()
        _, target = self.owner('imported-diagnostics')
        target.path.parent.mkdir(parents=True)
        target.path.write_text(json.dumps(index), encoding='utf-8')
        target = module.ArtifactStore(target.root)
        target.bind_channel_policy(lambda: self.service)
        before = target.export_metadata(audit['lineage_id'])
        public_before = target.get_request(audit['request_id'])
        for position in range(10):
            target.quarantine_submission(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
                reason='superseded', content='late-' + str(position), actor_identity_id='a'*32)
        self.assertEqual(target.export_metadata(audit['lineage_id']), before)
        self.assertEqual(target.get_request(audit['request_id']), public_before)
        self.assertEqual(target.request_diagnostics(audit['request_id'])['quarantine_ids'], [])
        diagnostics = target.diagnostics()
        self.assertEqual(diagnostics['detailed_count'], 8)
        self.assertEqual(diagnostics['retained_body_bytes'], 8 * len(b'late-0'))
        self.assertFalse(any(row['kind'] == 'orphan_quarantine' for row in diagnostics['rows']))
        summary = next(row for row in diagnostics['rows'] if row['kind'] == 'dispatch_overflow')
        self.assertEqual(summary['counter'], 2)
        before_bytes = target.path.read_bytes()
        diagnostic_bytes = target.diagnostic_store.path.read_bytes()
        target.quarantine_submission(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
            reason='superseded', content='late-0', actor_identity_id='a'*32)
        self.assertEqual(target.path.read_bytes(), before_bytes)
        self.assertEqual(target.diagnostic_store.path.read_bytes(), diagnostic_bytes)
        for item in (audit, second):
            with self.assertRaises(module.ArtifactConflict):
                target.commit_version(item['request_id'], item['attempt_id'], item['dispatch_id'], '# Refused',
                    {'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'})
        self.assertEqual(target.export_metadata(audit['lineage_id']), before)

    def test_imported_origin_version_relation_and_authority_negative_matrix(self):
        index, audit, second, version = self.imported_index()
        for mutation in ('unversioned_fulfilled', 'versioned_failed', 'origin_imported', 'bad_state',
                         'bad_reason', 'bad_archive', 'launch_ref', 'capability', 'version_origin',
                         'local_origin'):
            with self.subTest(mutation=mutation):
                value = deepcopy(index)
                row = value['requests'][audit['request_id']]
                if mutation == 'unversioned_fulfilled':
                    value['requests'][second['request_id']]['import_source']['original_state'] = 'fulfilled'
                elif mutation == 'versioned_failed':
                    row['import_source']['original_state'] = 'failed'
                elif mutation == 'origin_imported':
                    row['import_source']['original_state'] = 'imported'
                elif mutation == 'bad_state':
                    row['import_source']['original_state'] = 'bogus'
                elif mutation == 'bad_reason':
                    row['import_source']['original_reason'] = 'bogus'
                elif mutation == 'bad_archive':
                    row['import_source']['archive_id'] = '/private/path'
                elif mutation == 'launch_ref':
                    row['audit']['producer']['launch_attempt'] = 'a'*32
                elif mutation == 'capability':
                    row['audit']['producer']['capabilities'] = ['artifact-v1']
                elif mutation == 'version_origin':
                    value['versions'][version['id']]['provenance']['import_source'] = row['import_source']
                else:
                    # Otherwise-valid LOCAL original with an added imported origin.
                    source = module.ArtifactStore(self.root / 'export-source')
                    value = json.loads(source.path.read_bytes())
                    value['requests'][audit['request_id']]['import_source'] = row['import_source']
                _, target = self.owner('negative-' + mutation)
                target.path.parent.mkdir(parents=True)
                target.path.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaises(module.ArtifactUnavailable):
                    module.ArtifactStore(target.root)
        # Prove legacy CLI/null-ref compatibility through a real fresh index load.
        local = module.ArtifactStore(self.root / 'export-source')
        self.assertEqual(local.get_request(audit['request_id'])['audit'], audit)

    def test_export_metadata_detachment_held_reads_and_body_tamper_matrix(self):
        store, audit, second, version, raw = self.seed()
        snapshot = store.export_metadata(audit['lineage_id'])
        original = deepcopy(snapshot)
        snapshot['lineage']['channel'] = 'DETACHED'
        snapshot['versions'][0]['provenance']['instruction'] = 'DETACHED'
        self.assertEqual(store.export_metadata(audit['lineage_id']), original)
        with self.assertRaises(module.ArtifactConflict):
            store.export_metadata(uuid.uuid4().hex)
        with self.assertRaises(module.ArtifactUnavailable):
            store.read_archive_object('version', uuid.uuid4().hex,
                sha256=version['sha256'], byte_length=len(raw))
        body = store.root / 'artifacts' / 'objects' / (version['id'] + '.md')
        for mutation in ('hash', 'length', 'missing'):
            with self.subTest(mutation=mutation):
                if mutation == 'missing':
                    body.unlink()
                else:
                    body.write_bytes(b'x' * len(raw) if mutation == 'hash' else raw + b'x')
                with self.assertRaises(module.ArtifactUnavailable):
                    store.read_archive_object('version', version['id'],
                        sha256=version['sha256'], byte_length=len(raw))
                self.assertEqual(store.export_metadata(audit['lineage_id']), original)
                body.write_bytes(raw)
        # Correct expected hash with an incorrect expected length also refuses.
        with self.assertRaises(module.ArtifactUnavailable):
            store.read_archive_object('version', version['id'],
                sha256=version['sha256'], byte_length=len(raw) + 1)
        store.path.write_bytes(b'BROKEN_INDEX')
        for read in (lambda: store.export_metadata(audit['lineage_id']),
                     lambda: store.read_archive_object('version', version['id'],
                         sha256=version['sha256'], byte_length=len(raw))):
            with self.assertRaises(module.ArtifactUnavailable):
                read()
        self.assertEqual(store.path.read_bytes(), b'BROKEN_INDEX')


if __name__ == '__main__':
    unittest.main()
