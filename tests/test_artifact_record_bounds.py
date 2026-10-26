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
        for path in saved_files:
            with self.subTest(privacy='outbox'):
                self.assertFalse('m' * 257 in path.read_text(encoding='utf-8'),
                    'Overlong observation reached the saved outbox.')
        with self.subTest(privacy='version_metadata'):
            self.assertFalse('m' * 257 in
                json.dumps(self.artifacts.export_metadata(audit['lineage_id'])['versions']),
                'Overlong observation reached version metadata.')
        self.assertEqual((outcome['status'], outcome['reason'], row['state'], row['reason'],
                          len(reports), len(saved_files), self.artifacts.list_versions(audit['lineage_id'])['count']),
            ('quarantined', 'artifact_invalid_response', 'quarantined', 'invalid_response', 1, 0, 0))
        self.assertEqual(reports, [{'content': content, 'received_truncated': False}])
        self.assertNotIn('m' * 257, json.dumps(self.artifacts.diagnostics()))
        # Real reject_response fences a claimed transport; settlement is separate.
        self.assertEqual(self.trigger.queue.owned(instance, audit['dispatch_id'])['state'], 'cancelling')

    @staticmethod
    def stored_files(owner):
        return {p.relative_to(owner.root).as_posix(): p.read_bytes()
                for p in owner.root.rglob('*') if p.is_file()}

    def run_packet(self):
        value = self.packet()
        revision = hashlib.sha256(b'').hexdigest()
        value.update(scope_kind='run_accepted_messages',
            input={'text': '', 'input_revision': revision, 'source_document': None},
            source_run={'session_id': 1, 'run_id': '4' * 32,
                        'input_revision': revision, 'state_at_request': 'active'})
        return value

    def test_label_control_matrix_refuses_every_index_label_without_effects(self):
        audit = self.audit(store, self.source, packet=self.run_packet())
        before = self.stored_files(self.source)
        fields = ('requester', 'producer.name', 'producer.requested_model',
                  'producer.requested_model_reason', 'source_run.state_at_request',
                  'scope.uid', 'observation.confirmed_model')
        for field in fields:
            for code in (*range(32), 127, 256, 257):
                value = ('\U0001f600' * 64 + ('x' if code == 257 else '')
                         if code in (256, 257) else 'prefix' + chr(code) + 'suffix')
                changed = deepcopy(audit)
                if field == 'observation.confirmed_model':
                    action = lambda: store._observation({'confirmed_model': value,
                        'confirmation_reason': 'api_response'}, 'openai-compatible')
                else:
                    if field == 'scope.uid':
                        changed['scope']['message_refs'][0]['uid'] = value
                    elif field == 'requester':
                        changed['requester'] = value
                    else:
                        parent, key = field.split('.')
                        changed[parent][key] = value
                        if key == 'requested_model':
                            changed['producer']['requested_model_reason'] = None
                    action = lambda: store._audit(changed)
                with self.subTest(field=field, case=('bytes' + str(code) if code in (256, 257) else hex(code))):
                    if code == 256:
                        expected = ({'confirmed_model': value, 'confirmation_reason': 'api_response'}
                                    if field == 'observation.confirmed_model' else changed)
                        self.assertEqual(action(), expected)
                    else:
                        with self.assertRaises(store.ArtifactValidationError):
                            action()
                    self.assertEqual(self.stored_files(self.source), before)

    def test_audit_free_text_rejects_other_controls_and_preserves_ht_lf_cr(self):
        audit = self.audit(store, self.source)
        for field in ('instruction', 'format'):
            changed = deepcopy(audit)
            changed[field] = 'Start\t\r\nEnd'
            self.assertEqual(store._audit(changed)[field].encode('utf-8'), b'Start\t\r\nEnd')
            for code in (*range(32), 127):
                if code in (9, 10, 13):
                    continue
                changed[field] = 'Start' + chr(code) + 'End'
                with self.subTest(field=field, control=hex(code)):
                    with self.assertRaises(store.ArtifactValidationError):
                        store._audit(changed)

    def test_index_text_helper_accept_refuse_set_is_shared_infrastructure(self):
        # Missing helper is explicitly an infrastructure RED, never behavior proof.
        helper = store._index_text
        for cap in (512, 32768):
            for text in ('A\t\r\nB', '\ufeff', '\u202e', '\U0001f600' * (cap // 4)):
                self.assertEqual(helper(text, cap), text.encode('utf-8'))
            for text in (' ', '\u0085', '\u2028', '\u2029', 'bad\x01text',
                         'bad\0text', 'bad\ud800text', 'x' * (cap + 1)):
                with self.subTest(cap=cap, value=ascii(text[:12])):
                    with self.assertRaises(store.ArtifactValidationError):
                        helper(text, cap)

    def test_record_integer_widths_with_float_and_bool_compatibility_guards(self):
        # Positive float width <=23 is a type consequence, not a new restriction.
        stamp = 1.2345678901234567e-100
        self.assertEqual(len(json.dumps(stamp)), 23)
        self.assertEqual(store._number(stamp), stamp)
        self.assertEqual(store._number(2**63-1), 2**63-1)
        self.assertEqual(len(json.dumps(-stamp)), 24)
        for value in (-stamp, float('nan'), float('inf'), True):
            with self.subTest(existing_number_guard=repr(value)):
                with self.assertRaises(store.ArtifactValidationError):
                    store._number(value)
        with self.assertRaises(store.ArtifactValidationError):
            store._integer(True)
        _, audit, _ = self.graph_for_packet(self.run_packet())
        run_audit = deepcopy(audit)
        for field in ('created_at', 'source_run.session_id', 'scope.message_id', 'parent.sequence'):
            changed = deepcopy(run_audit)
            if field == 'created_at':
                changed['created_at'] = 2**63
            elif field == 'source_run.session_id':
                changed['source_run']['session_id'] = 2**63
            elif field == 'scope.message_id':
                changed['scope']['message_refs'][0]['id'] = 2**63
            else:
                changed['expected_parent'] = {'version_id': 'd' * 32,
                    'sequence': 2**63, 'sha256': 'e' * 64}
            with self.subTest(record_field=field):
                with self.assertRaises(store.ArtifactValidationError):
                    store._audit(changed)
        self.source.quarantine_submission(None, 'a' * 32, 'b' * 32,
            reason='invalid_response', content=None, now=10)
        original = deepcopy(self.source._data)
        version_id = store.request_ids(audit['request_id'])['version_id']
        for field in ('request.updated_at', 'lineage.updated_at', 'version.created_at', 'version.sequence'):
            changed = deepcopy(original)
            if field == 'request.updated_at':
                changed['requests'][audit['request_id']]['updated_at'] = 2**63
            elif field == 'lineage.updated_at':
                changed['lineages'][audit['lineage_id']]['updated_at'] = 2**63
            else:
                changed['versions'][version_id][field.split('.')[1]] = 2**63
            with self.subTest(index_field=field):
                with self.assertRaises(store.ArtifactValidationError):
                    self.source._validate_index(changed)
        changed = deepcopy(original)
        diagnostic = next(iter(changed['diagnostics'].values()))
        diagnostic['byte_count'] = 2**63
        key = {name: diagnostic[name] for name in ('request_id', 'attempt_id', 'dispatch_id',
            'reason', 'sha256', 'byte_count', 'actor_identity_id')}
        diagnostic['id'] = self.source._diagnostic_id(key)
        changed['diagnostics'] = {diagnostic['id']: diagnostic}
        with self.subTest(index_field='diagnostic.byte_count'):
            with self.assertRaises(store.ArtifactValidationError):
                self.source._validate_index(changed)
        changed = deepcopy(original)
        diagnostic = next(iter(changed['diagnostics'].values()))
        diagnostic.update(received_at=2**63, updated_at=2**63)
        with self.subTest(index_field='diagnostic.received_at/updated_at'):
            with self.assertRaises(store.ArtifactValidationError):
                self.source._validate_index(changed)
        summary = {'id': self.source._summary_id(None), 'kind': 'store_overflow',
            'dispatch_id': None, 'counter': 1, 'latest_diagnostic_id': 'd' * 32,
            'latest_sha256': 'e' * 64, 'latest_byte_count': 2**63,
            'latest_reason': 'invalid_response', 'updated_at': 10}
        with self.subTest(index_field='overflow.latest_byte_count'):
            with self.assertRaises(store.ArtifactValidationError):
                self.source._validate_summary(summary, None)
        with self.subTest(record_field='timestamp_helper'):
            with self.assertRaises(store.ArtifactValidationError):
                store._number(2**63)

    def test_packet_semantic_fields_refuse_before_any_object_or_index_write(self):
        for number, field in enumerate(('uid_length', 'uid_control', 'message_id',
                                       'message_timestamp', 'source_run_session_id')):
            owner = store.ArtifactStore(self.root / ('packet-check-' + str(number)))
            owner.bind_channel_policy(lambda: self.service)
            packet = self.run_packet()
            if field == 'uid_length':
                packet['messages'][0]['uid'] = 'x' * 257
            elif field == 'uid_control':
                packet['messages'][0]['uid'] = 'bad\x01uid'
            elif field == 'message_id':
                packet['messages'][0]['id'] = 2**63
            elif field == 'message_timestamp':
                packet['messages'][0]['timestamp'] = 2**63
            else:
                packet['source_run']['session_id'] = 2**63
            before = self.stored_files(owner)
            before_index = owner.path.read_bytes() if owner.path.exists() else None
            with self.subTest(field=field):
                with self.assertRaises(store.ArtifactValidationError):
                    owner.put_packet('c' * 32, packet)
                self.assertEqual(self.stored_files(owner), before)
                self.assertEqual(owner.path.read_bytes() if owner.path.exists() else None, before_index)
                self.assertEqual(owner.export_lineage_ids(), ())

    def test_codec_wide_integer_timestamps_skip_only_bad_lineage(self):
        _, bad_audit, _ = self.source_graph(attempts=False)
        _, healthy_audit, _ = self.source_graph(attempts=False)
        data = self.export()
        # Existing structural finite-positive/type rules remain section errors.
        # New integer-width restrictions below are semantic lineage skips.
        for value in (float('nan'), float('inf'), -1.2345678901234567e-100, True):
            def invalid_shape(members):
                index = json.loads(members[codec.INDEX_MEMBER])
                lineage = next(x for x in index['lineages'] if x['lineage_id'] == bad_audit['lineage_id'])
                lineage['requests'][0]['created_at'] = value
                members[codec.INDEX_MEMBER] = json.dumps(index, allow_nan=True).encode('utf-8')
            incoming = self.repack(data, invalid_shape)
            with self.subTest(existing_codec_shape_guard=repr(value)):
                with zipfile.ZipFile(io.BytesIO(incoming)) as zf:
                    with self.assertRaises(codec.ArtifactSectionError) as caught:
                        codec.preflight(zf, zip_size=len(incoming))
                self.assertEqual(caught.exception.code, 'artifact_archive_invalid_section')
                self.assertEqual(caught.exception.http_status, 400)
                self.assertEqual(self.target.export_lineage_ids(), ())
        for number, field in enumerate(('request.created_at', 'request.updated_at',
                                       'version.created_at', 'lineage.updated_at')):
            def mutate(members):
                index = json.loads(members[codec.INDEX_MEMBER])
                lineage = next(x for x in index['lineages'] if x['lineage_id'] == bad_audit['lineage_id'])
                if field.startswith('request.'):
                    lineage['requests'][0][field.split('.')[1]] = 2**63
                elif field.startswith('version.'):
                    lineage['versions'][0]['created_at'] = 2**63
                else:
                    lineage['updated_at'] = 2**63
                members[codec.INDEX_MEMBER] = codec.canonical_utf8(index)
            incoming = self.repack(data, mutate)
            owner = store.ArtifactStore(self.root / ('number-import-' + str(number)))
            owner.bind_channel_policy(lambda: self.service)
            with self.subTest(field=field):
                with zipfile.ZipFile(io.BytesIO(incoming)) as zf:
                    self.assertEqual(len(codec.preflight(zf, zip_size=len(incoming))['index']['lineages']), 2)
                result = self.restore(incoming, owner=owner)
                self.assertTrue(result['ok'])
                self.assertIsNone(result['sections']['artifacts']['section_error'])
                self.assertEqual((result['sections']['artifacts']['invalid_lineages'],
                                  result['sections']['artifacts']['created_lineages']), (1, 1))
                self.assertEqual(owner.export_lineage_ids(), (healthy_audit['lineage_id'],))

    def test_seat_config_model_label_refuses_typed_before_any_reservation(self):
        self.setup_authority()
        # Existing seat config accepts <=256 characters. 86 three-byte chars
        # reach the actual immutable launch as 258 UTF8 bytes, without forgery.
        model = '\u754c' * 86
        selected = next(seat for seat in self.package['seats'] if seat['id'] == 'api')
        selected['model'] = model
        self.manager.store.save(self.package)
        instance, _, _ = self.launch_binding('api')
        self.assertEqual(self.manager.launch_provenance(instance)['effective']['seat']['model'], model)
        audit, packet = self.new_request(instance=instance)
        self.assertEqual(audit['producer']['requested_model'], model)
        before = self.stored_files(self.artifacts)
        with self.assertRaises(self.module._ArtifactProducerUnavailable):
            self.authority.prepare_request(audit, packet, audit['request_id'])
        self.assertEqual(self.stored_files(self.artifacts), before)
        self.assertEqual(self.artifacts.export_lineage_ids(), ())
        self.assertIsNone(self.artifacts.get_request(audit['request_id']))

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
