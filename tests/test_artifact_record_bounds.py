"""R1 behavior reds over real temp stores/codec/worker, no native/provider claims."""
from copy import deepcopy
import hashlib
import io
import json
import unittest
from unittest.mock import Mock
import zipfile

import artifact_archive as codec
import artifact_store as store
import artifact_worker as worker
from api_seats import atomic_json
from tests import test_artifact_imported_store as imported_fixture
from tests import test_artifact_workers as worker_fixture
from tests import test_artifact_archive_driver as archive_fixture


class ArtifactRecordBoundsTests(unittest.TestCase):
    # Explicit aliases avoid inheriting/collecting existing helper tests twice.
    def setUp(self):
        # Added first so fixture cleanup runs before the no-leftover assertion.
        self.addCleanup(lambda: self.assertFalse(self.root.exists()))
        imported_fixture.ArtifactImportedStoreTests.setUp(self)

    packet = imported_fixture.ArtifactImportedStoreTests.packet
    audit = imported_fixture.ArtifactImportedStoreTests.audit
    portable = imported_fixture.ArtifactImportedStoreTests.portable
    source_graph = imported_fixture.ArtifactImportedStoreTests.source_graph
    graph_for_packet = imported_fixture.ArtifactImportedStoreTests.graph_for_packet
    export = archive_fixture.ArtifactArchiveDriverTests.export
    restore = archive_fixture.ArtifactArchiveDriverTests.restore
    target_history = archive_fixture.ArtifactArchiveDriverTests.target_history
    repack = staticmethod(archive_fixture.ArtifactArchiveDriverTests.repack)
    setup_authority = worker_fixture.ArtifactWorkerTests.setup_authority
    launch_binding = worker_fixture.ArtifactWorkerTests.launch_binding
    new_request = worker_fixture.ArtifactWorkerTests.new_request
    prepare = worker_fixture.ArtifactWorkerTests.prepare
    claim = worker_fixture.ArtifactWorkerTests.claim
    claimed = worker_fixture.ArtifactWorkerTests.claimed
    owned = worker_fixture.ArtifactWorkerTests.owned
    api_scope = worker_fixture.ArtifactWorkerTests.api_scope
    api_callbacks = worker_fixture.ArtifactWorkerTests.api_callbacks
    forbidden = staticmethod(worker_fixture.ArtifactWorkerTests.forbidden)

    def test_api_observation_label_257_bytes_refuses_without_normalizing_256(self):
        for blank in ('\u0085', '\u2028', '\u2029'):
            with self.subTest(blank=ascii(blank)):
                with self.assertRaises(store.ArtifactValidationError):
                    store._observation({'confirmed_model': blank,
                        'confirmation_reason': 'api_response'}, 'openai-compatible')
        for value in ('\ufeff', '\u202e', '\U0001f600' * 64):
            observation = {'confirmed_model': value, 'confirmation_reason': 'api_response'}
            self.assertEqual(store._observation(observation, 'openai-compatible'), observation)
        too_long = '\U0001f600' * 64 + 'x'
        self.assertEqual(len(too_long.encode('utf-8')), 257)
        with self.assertRaises(store.ArtifactValidationError):
            store._observation({'confirmed_model': too_long,
                'confirmation_reason': 'api_response'}, 'openai-compatible')

    def test_codec_overlong_source_state_skips_only_bad_lineage_after_structure(self):
        packet = self.packet()
        revision = hashlib.sha256(b'').hexdigest()
        packet.update(scope_kind='run_accepted_messages',
            input={'text': '', 'input_revision': revision, 'source_document': None},
            source_run={'session_id': 1, 'run_id': '4' * 32,
                        'input_revision': revision, 'state_at_request': 'active'})
        _, bad_audit, _ = self.graph_for_packet(packet)
        _, healthy_audit, _ = self.source_graph(attempts=False)
        data = self.export()

        def corrupt_semantic_state(members):
            index = json.loads(members[codec.INDEX_MEMBER])
            lineage = next(x for x in index['lineages'] if x['lineage_id'] == bad_audit['lineage_id'])
            request = lineage['requests'][0]
            name = codec.member_name('packet', request['scope']['packet_id'])
            value = json.loads(members[name])
            value['source_run']['state_at_request'] = 'x' * 257
            request['source_run'] = deepcopy(value['source_run'])
            raw = codec.canonical_utf8(value)
            request['scope'].update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
            members[name] = raw
            members[codec.INDEX_MEMBER] = codec.canonical_utf8(index)
            # Keep the real manifest accounting valid after changing packet bytes.
            manifest = json.loads(members['manifest.json'])
            manifest['artifacts'] = codec.artifact_counts(index)
            members['manifest.json'] = codec.canonical_utf8(manifest)

        incoming = self.repack(data, corrupt_semantic_state)
        with zipfile.ZipFile(io.BytesIO(incoming)) as zf:
            section = codec.preflight(zf, zip_size=len(incoming))
            self.assertEqual(len(section['index']['lineages']), 2)
        report = self.restore(incoming)
        self.assertTrue(report['ok'])
        self.assertFalse(report['partial'])
        result = report['sections']['artifacts']
        self.assertIsNone(result['section_error'])
        self.assertEqual((result['invalid_lineages'], result['created_lineages']), (1, 1))
        self.assertEqual(result['details'][0]['reason'], 'invalid_lineage')
        self.assertEqual(self.target.export_lineage_ids(), (healthy_audit['lineage_id'],))
        self.assertIsNone(self.target.get_request(bad_audit['request_id']))

    def test_api_overlong_observation_rejects_before_outbox_save_and_version(self):
        self.setup_authority()
        instance, _, audit, _, record, owned = self.api_scope()
        content = json.dumps({'kind': 'artifact', 'markdown': '# Valid content\r\n'})
        callbacks = self.api_callbacks(instance,
            generate=Mock(return_value={'content': content, 'confirmed_model': 'm' * 257}))
        reports = []

        def reject(report):
            reports.append(deepcopy(report))
            return self.authority.reject_response(audit['brief_id'], report['content'], instance,
                received_truncated=report['received_truncated'])

        callbacks['reject_response'] = reject
        # Observe real submission on old code, so the red exposes admission, not
        # an AssertionError from a forbidden transport callback.
        outcome = worker.complete_api_artifact(record, **owned, **callbacks)
        row = self.artifacts.get_request(audit['request_id'])
        saved_files = list(owned['runtime_path'].glob('artifact_results/*.json'))
        self.assertEqual((outcome['status'], outcome['reason'], row['state'], row['reason'],
                          len(reports), len(saved_files), self.artifacts.list_versions(audit['lineage_id'])['count']),
            ('quarantined', 'artifact_invalid_response', 'quarantined', 'invalid_response', 1, 0, 0))
        self.assertEqual(reports, [{'content': content, 'received_truncated': False}])
        self.assertNotIn('m' * 257, json.dumps(self.artifacts.diagnostics()))
        self.assertEqual(self.trigger.queue.owned(instance, audit['dispatch_id'])['state'], 'dispatched')

    def maximum_row(self):
        """Build real persisted data, then validate a detached widest row.

        The detached sequence/parent widths do not represent a physical chain
        with 2**63 rows. All scalar values and the serialized row are real.
        """
        label = '\U0001f600' * 64
        stamp = 1.2345678901234567e-100
        self.assertEqual(len(json.dumps(stamp)), 23)
        packet = self.packet()
        revision = hashlib.sha256(b'').hexdigest()
        packet.update(scope_kind='run_accepted_messages',
            input={'text': '', 'input_revision': revision, 'source_document': None},
            source_run={'session_id': 2**63-1, 'run_id': '4' * 32,
                        'input_revision': revision, 'state_at_request': label},
            messages=[{'id': 2**63-1-i, 'uid': chr(0x10000+i) * 64,
                'sender': 'operator', 'type': 'chat', 'timestamp': stamp,
                'text': '', 'attachments': [], 'provenance': {}} for i in range(1000)])
        audit = self.audit(store, self.source, request_id='1' * 32, packet=packet)
        audit.update(requester=label, instruction='\U0001f600' * 8192,
                     format='\U0001f600' * 128, created_at=stamp)
        audit['producer'].update(name=label, adapter='openai-compatible',
            launch_attempt='2' * 32, launch_nonce='3' * 32, fingerprint='4' * 64,
            requested_model=label, requested_model_reason=None)
        self.source.reserve_request(audit, audit['request_id'])
        self.source.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                                     {'state': 'queued', 'reason': 'queued'}, now=stamp)
        metadata = self.source.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
            'x' * 524288, {'confirmed_model': label, 'confirmation_reason': 'api_response'}, now=stamp)
        request = self.source.export_metadata(audit['lineage_id'])['requests'][0]
        request['audit']['expected_parent'] = {'version_id': 'e' * 32,
            'sequence': 2**63-1, 'sha256': 'f' * 64}
        metadata.update(sequence=2**63-1, parent_version_id='e' * 32)
        store._audit(request['audit'])
        self.source._validate_version(metadata, {audit['request_id']: request})
        path = self.root / 'maximum-row.json'
        atomic_json(path, metadata)
        return metadata, path.read_bytes()

    def test_built_maximum_version_row_matches_prechange_writer_golden(self):
        metadata, raw = self.maximum_row()
        self.assertEqual(json.loads(raw), metadata)
        self.assertEqual(len(metadata['provenance']['instruction'].encode('utf-8')), 32768)
        self.assertEqual(len(metadata['provenance']['scope']['message_refs']), 1000)
        for ref in metadata['provenance']['scope']['message_refs']:
            self.assertEqual(len(ref['uid'].encode('utf-8')), 256)
            self.assertEqual(len(json.dumps(ref['uid'])) - 2, 768)
        # Literal byte count/hash captured from the real pre-change atomic_json
        # writer after building this exact row, not a projected escrow formula.
        self.assertEqual(len(raw), 991296)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
            '8451bbe3371bd3f472e5531e78c2529b702bdf4759dd043c995f702b3aeeeef4')


if __name__ == '__main__':
    unittest.main()
