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
import artifact_protocol as protocol
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
    sealed_fixture_record = worker_fixture.ArtifactWorkerTests.sealed_fixture_record
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

    def test_codec_source_labels_and_session_skip_only_bad_lineage_after_structure(self):
        _, bad_audit, _ = self.graph_for_packet(self.run_packet())
        _, healthy_audit, _ = self.source_graph(attempts=False)
        data = self.export()
        fields = ('source_run.state_at_request', 'source_run.session_id', 'requester',
                  'producer.name', 'producer.requested_model_reason', 'scope.uid', 'scope.message_id')
        for number, field in enumerate(fields):
            def corrupt_semantic_field(members):
                index = json.loads(members[codec.INDEX_MEMBER])
                lineage = next(x for x in index['lineages'] if x['lineage_id'] == bad_audit['lineage_id'])
                request = lineage['requests'][0]
                name = codec.member_name('packet', request['scope']['packet_id'])
                value = json.loads(members[name])
                if field.startswith('source_run.'):
                    key = field.split('.')[1]
                    value['source_run'][key] = 2**63 if key == 'session_id' else 'x' * 257
                    request['source_run'] = deepcopy(value['source_run'])
                elif field == 'scope.uid':
                    value['messages'][0]['uid'] = 'x' * 257
                elif field == 'scope.message_id':
                    value['messages'][0]['id'] = 2**63
                elif field == 'requester':
                    request['requester'] = 'x' * 257
                else:
                    request['producer'][field.split('.')[1]] = 'x' * 257
                raw = codec.canonical_utf8(value)
                request['scope'].update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw),
                    message_refs=[{'id': row['id'], 'uid': row['uid'],
                        'sha256': hashlib.sha256(codec.canonical_utf8(row)).hexdigest()}
                        for row in value['messages']])
                members[name] = raw
                members[codec.INDEX_MEMBER] = codec.canonical_utf8(index)
                manifest = json.loads(members['manifest.json'])
                manifest['artifacts'] = codec.artifact_counts(index)
                members['manifest.json'] = codec.canonical_utf8(manifest)

            incoming = self.repack(data, corrupt_semantic_field)
            owner = store.ArtifactStore(self.root / ('semantic-import-' + str(number)))
            owner.bind_channel_policy(lambda: self.service)
            with self.subTest(field=field):
                with zipfile.ZipFile(io.BytesIO(incoming)) as zf:
                    self.assertEqual(len(codec.preflight(zf, zip_size=len(incoming))['index']['lineages']), 2)
                report = self.restore(incoming, owner=owner)
                self.assertTrue(report['ok'])
                self.assertFalse(report['partial'])
                result = report['sections']['artifacts']
                self.assertIsNone(result['section_error'])
                self.assertEqual((result['invalid_lineages'], result['created_lineages']), (1, 1))
                # Unobserved-red postconditions, required to execute once green.
                self.assertEqual(result['details'][0]['reason'], 'invalid_lineage')
                self.assertEqual(owner.export_lineage_ids(), (healthy_audit['lineage_id'],))
                self.assertIsNone(owner.get_request(bad_audit['request_id']))

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
        # Unobserved-red postconditions: reached only after the new outcome passes.
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

    def test_label_control_and_byte_matrix_refuses_every_index_label(self):
        audit = self.audit(store, self.source, packet=self.run_packet())
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

    @staticmethod
    def changed_label(audit, field, value):
        changed = deepcopy(audit)
        if field == 'scope.uid':
            changed['scope']['message_refs'][0]['uid'] = value
        elif field == 'requester':
            changed['requester'] = value
        else:
            parent, key = field.split('.')
            changed[parent][key] = value
            if key == 'requested_model':
                changed['producer']['requested_model_reason'] = None
        return changed

    def test_all_audit_label_unicode_and_blankness_compatibility(self):
        audit = self.audit(store, self.source, packet=self.run_packet())
        values = ('A\u0080\u0085\u009fB', 'A\u2028\u2029B', '\ufeff', '\u202e',
                  '\u00e9' * 128, '\u754c' * 85 + 'x', 'caf\u00e9', 'cafe\u0301')
        for field in ('requester', 'producer.name', 'producer.requested_model',
                      'producer.requested_model_reason', 'source_run.state_at_request', 'scope.uid'):
            for value in values:
                changed = self.changed_label(audit, field, value)
                with self.subTest(field=field, positive=ascii(value[:8])):
                    self.assertEqual(store._audit(changed), changed)
            for blank in ('\u0085', '\u2028', '\u2029'):
                with self.subTest(field=field, blank=ascii(blank)):
                    with self.assertRaises(store.ArtifactValidationError):
                        store._audit(self.changed_label(audit, field, blank))

    def test_audit_free_text_rejects_other_controls_and_preserves_ht_lf_cr(self):
        audit = self.audit(store, self.source)
        for field in ('instruction', 'format'):
            changed = deepcopy(audit)
            changed[field] = 'Start\t\r\nEnd'
            self.assertEqual(store._audit(changed)[field].encode('utf-8'), b'Start\t\r\nEnd')
            cap = 32768 if field == 'instruction' else 512
            changed[field] = '\U0001f600' * (cap // 4)
            self.assertEqual(len(store._audit(changed)[field].encode('utf-8')), cap)
            changed[field] += 'x'
            with self.assertRaises(store.ArtifactValidationError):
                store._audit(changed)
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
        for value in (0, -stamp, float('nan'), float('inf'), True):
            with self.subTest(existing_number_guard=repr(value)):
                with self.assertRaises(store.ArtifactValidationError):
                    store._number(value)
        with self.assertRaises(store.ArtifactValidationError):
            store._integer(True)
        _, audit, _ = self.graph_for_packet(self.run_packet())
        run_audit = deepcopy(audit)
        # Exact boundary positives go through _audit, not only the generic helper.
        largest = deepcopy(run_audit)
        largest.update(created_at=2**63-1,
            expected_parent={'version_id': 'd' * 32, 'sequence': 2**63-1, 'sha256': 'e' * 64})
        largest['source_run']['session_id'] = 2**63-1
        largest['scope']['message_refs'][0]['id'] = 2**63-1
        self.assertEqual(store._audit(largest), largest)
        self.assertEqual(store._integer(2**63-1), 2**63-1)
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
        for field in ('request.updated_at', 'lineage.updated_at', 'version.created_at'):
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
        # Avoid the outer chain validator, which already rejects a large sequence
        # for a one-version chain. This direct row validator has no such mask.
        metadata = deepcopy(original['versions'][version_id])
        metadata['sequence'] = 2**63-1
        self.source._validate_version(metadata, original['requests'])
        metadata['sequence'] = 2**63
        with self.subTest(record_field='version.sequence_direct_row'):
            with self.assertRaises(store.ArtifactValidationError):
                self.source._validate_version(metadata, original['requests'])
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
        summary.update(latest_byte_count=0, updated_at=2**63)
        with self.subTest(index_field='overflow.updated_at'):
            with self.assertRaises(store.ArtifactValidationError):
                self.source._validate_summary(summary, None)
        with self.subTest(record_field='timestamp_helper'):
            with self.assertRaises(store.ArtifactValidationError):
                store._number(2**63)

    def test_packet_semantic_fields_refuse_before_any_object_or_index_write(self):
        for number, timestamp in enumerate((None, 1.2345678901234567e-100)):
            owner = store.ArtifactStore(self.root / ('packet-positive-' + str(number)))
            owner.bind_channel_policy(lambda: self.service)
            packet = self.run_packet()
            packet['source_run']['session_id'] = 2**63-1
            packet['messages'][0].update(uid='\U0001f600' * 64, id=2**63-1, timestamp=timestamp)
            scope = owner.put_packet('f' * 32, packet)
            self.assertEqual(owner.get_packet(scope['packet_id']), packet)
        for number, field in enumerate(('uid_length', 'uid_control', 'message_id',
                                       'message_timestamp', 'source_run_session_id',
                                       'uid_del', 'uid_ht', 'uid_cr', 'uid_lf', 'id_bool', 'id_negative',
                                       'source_state_length', 'source_state_control')):
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
            elif field in ('uid_del', 'uid_ht', 'uid_cr', 'uid_lf'):
                control = {'uid_del': '\x7f', 'uid_ht': '\t', 'uid_cr': '\r', 'uid_lf': '\n'}[field]
                packet['messages'][0]['uid'] = 'bad' + control + 'uid'
            elif field in ('id_bool', 'id_negative'):
                packet['messages'][0]['id'] = True if field == 'id_bool' else -1
            elif field.startswith('source_state_'):
                packet['source_run']['state_at_request'] = ('x' * 257 if field.endswith('length')
                                                            else 'bad\x01state')
            else:
                packet['source_run']['session_id'] = 2**63
            before = self.stored_files(owner)
            before_index = owner.path.read_bytes() if owner.path.exists() else None
            with self.subTest(field=field):
                with self.assertRaises(store.ArtifactValidationError):
                    owner.put_packet('c' * 32, packet)
                # Unobserved-red for newly invalid values; required green invariants.
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
        with self.assertRaises(self.module._ArtifactProducerUnavailable) as caught:
            self.authority.prepare_request(audit, packet, audit['request_id'])
        # Distinguish the label refusal from a lost or changed runtime binding.
        self.assertEqual(str(caught.exception), 'Artifact producer labels exceed the supported grammar.')
        self.assertNotIn(model, str(caught.exception))
        self.assertNotIn('binding', str(caught.exception))
        self.assertNotIn('immutable producer launch', str(caught.exception))
        # Unobserved-red: reached when the typed refusal exists, checked once green.
        self.assertEqual(self.stored_files(self.artifacts), before)
        self.assertEqual(self.artifacts.export_lineage_ids(), ())
        self.assertIsNone(self.artifacts.get_request(audit['request_id']))

    def test_storage_boundary_name_and_reason_refuse_before_reservation(self):
        for number, (field, value) in enumerate((
                (field, value) for field in ('producer.name', 'producer.requested_model_reason',
                    'producer.requested_model', 'source_run.state_at_request', 'requester', 'scope.uid')
                for value in ('x' * 257, 'bad\x01label'))):
            owner = store.ArtifactStore(self.root / ('storage-defense-' + str(number)))
            owner.bind_channel_policy(lambda: self.service)
            packet = self.run_packet()
            audit = self.audit(store, owner, packet=packet)
            changed = self.changed_label(audit, field, value)
            if field in ('source_run.state_at_request', 'scope.uid'):
                # Hostile persisted input fixture: keep audit/body/hash consistent
                # without invoking the new packet validator to build invalid data.
                if field == 'scope.uid':
                    packet['messages'][0]['uid'] = value
                else:
                    packet['source_run']['state_at_request'] = value
                raw = codec.canonical_utf8(packet)
                changed['scope'].update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw),
                    message_refs=[{'id': row['id'], 'uid': row['uid'],
                        'sha256': hashlib.sha256(codec.canonical_utf8(row)).hexdigest()}
                        for row in packet['messages']])
                owner._object_path('packet', changed['scope']['packet_id']).write_bytes(raw)
            before = self.stored_files(owner)
            with self.subTest(field=field, kind='byte_cap' if len(value) == 257 else 'control'):
                with self.assertRaises(store.ArtifactValidationError):
                    owner.reserve_request(changed, changed['request_id'])
                # Unobserved-red invariants; unlike the old pure _audit check,
                # this real call would create rows/index bytes if it accepted.
                self.assertEqual(self.stored_files(owner), before)
                self.assertEqual(owner.export_lineage_ids(), ())
                self.assertIsNone(owner.get_request(audit['request_id']))

    def test_storage_boundary_out_of_bound_index_holds_on_fresh_load(self):
        _, audit, _ = self.graph_for_packet(self.run_packet())
        base = json.loads(self.source.path.read_bytes())
        control = self.root / 'healthy-load-control'
        atomic_json(control / 'artifacts' / 'index.json', base)
        self.assertEqual(store.ArtifactStore(control).export_lineage_ids(), (audit['lineage_id'],))
        number = 0
        for field in ('requester', 'producer.name', 'producer.requested_model_reason',
                      'producer.requested_model', 'source_run.state_at_request', 'scope.uid'):
            for value in ('x' * 257, 'bad\x01label'):
                changed = deepcopy(base)
                row = changed['requests'][audit['request_id']]
                row['audit'] = self.changed_label(row['audit'], field, value)
                # Keep provenance equality valid, so only the new grammar can
                # refuse: no unrelated existing cross-reference refusal mask.
                metadata = changed['versions'][row['version_id']]
                for key in ('requester', 'producer', 'scope', 'source_run'):
                    metadata['provenance'][key] = deepcopy(row['audit'][key])
                root = self.root / ('load-defense-' + str(number))
                number += 1
                path = root / 'artifacts' / 'index.json'
                atomic_json(path, changed)
                before = path.read_bytes()
                with self.subTest(field=field, kind='byte_cap' if len(value) == 257 else 'control'):
                    with self.assertRaises(store.ArtifactUnavailable) as caught:
                        store.ArtifactStore(root)
                    # Unobserved-red invariants: no rewrite/reset, typed hold.
                    self.assertEqual(str(caught.exception),
                        'Saved artifact index is unavailable or malformed; nothing was reset.')
                    held = store.ArtifactStore(root, hold_unreadable=True)
                    with self.assertRaises(store.ArtifactUnavailable):
                        held.export_lineage_ids()
                    self.assertEqual(path.read_bytes(), before)

    def test_protocol_caps_controls_parent_and_result_number_parity(self):
        self.setup_authority()
        audit, consumer = self.claimed()
        brief = self.authority._brief(audit)
        payload = self.sealed_fixture_record(audit, consumer)['payload']
        for field, cap in (('instruction', 32768), ('format', 512)):
            for value in ('Start\t\r\nEnd', '\U0001f600' * (cap // 4)):
                changed = deepcopy(brief)
                changed[field] = value
                with self.subTest(brief_field=field, guard='accepted'):
                    self.assertEqual(protocol.validate_brief(changed), changed)
            changed[field] += 'x'
            with self.subTest(brief_field=field, guard='byte_cap'):
                with self.assertRaises(store.ArtifactValidationError):
                    protocol.validate_brief(changed)
            for code in (*range(32), 127):
                if code in (9, 10, 13):
                    continue
                changed = deepcopy(brief)
                changed[field] = 'bad' + chr(code) + 'text'
                with self.subTest(brief_field=field, control=hex(code)):
                    with self.assertRaises(store.ArtifactValidationError):
                        protocol.validate_brief(changed)
            for value in ('\u0085', '\u2028', '\u2029', 'bad\ud800text'):
                changed = deepcopy(brief)
                changed[field] = value
                with self.subTest(brief_field=field, existing_blank_surrogate_guard=ascii(value)):
                    with self.assertRaises(store.ArtifactValidationError):
                        protocol.validate_brief(changed)
                changed_audit = deepcopy(audit)
                changed_audit[field] = value
                with self.subTest(audit_field=field, existing_blank_surrogate_guard=ascii(value)):
                    with self.assertRaises(store.ArtifactValidationError):
                        store._audit(changed_audit)
        for field, value in (('state_at_request', 'x' * 257),
                             ('state_at_request', 'bad\x01state'), ('session_id', 2**63)):
            changed = deepcopy(brief)
            changed['input_revision'] = 'a' * 64
            changed['source_run'] = {'session_id': 1, 'run_id': 'b' * 32,
                'input_revision': 'a' * 64, 'state_at_request': 'active'}
            changed['source_run'][field] = value
            with self.subTest(protocol='brief', source_run_field=field, value_type=type(value).__name__):
                with self.assertRaises(store.ArtifactValidationError):
                    protocol.validate_brief(changed)
        changed = deepcopy(payload)
        changed['observation'] = {'confirmed_model': 'x' * 257, 'confirmation_reason': 'api_response'}
        with self.subTest(protocol='payload', field='observation.confirmed_model'):
            with self.assertRaises(store.ArtifactValidationError):
                protocol.validate_payload(changed)
        for validator, original in ((protocol.validate_brief, brief),
                                    (protocol.validate_payload, payload)):
            changed = deepcopy(original)
            changed['expected_parent'] = {'version_id': 'd' * 32, 'sequence': 2**63-1, 'sha256': 'e' * 64}
            self.assertEqual(validator(changed), changed)
            changed['expected_parent']['sequence'] = 2**63
            with self.subTest(protocol=validator.__name__, field='parent.sequence'):
                with self.assertRaises(store.ArtifactValidationError):
                    validator(changed)
        for stamp in (2**63-1, 1.2345678901234567e-100):
            changed = deepcopy(payload)
            changed['created_at'] = stamp
            self.assertEqual(protocol.validate_payload(changed), changed)
        changed['created_at'] = 2**63
        with self.subTest(protocol='payload', field='created_at'):
            with self.assertRaises(store.ArtifactValidationError):
                protocol.validate_payload(changed)

    def test_generated_name_and_default_reason_service_compatibility_guards(self):
        # Configure actual seats BEFORE the existing fixture launches them.
        # This wraps only fixture setup, not manager/provenance observations.
        launch = self.launch_binding

        def launch_default(seat_id):
            next(seat for seat in self.package['seats'] if seat['id'] == seat_id)['model'] = None
            self.manager.store.save(self.package)
            return launch(seat_id)

        self.launch_binding = launch_default
        self.setup_authority()
        for instance, reason in ((self.instance, 'cli_model_unverified'),
                                 (self.launch_binding('api')[0], 'provider_default')):
            with self.subTest(adapter=reason):
                self.assertRegex(instance['name'], r'^(cli|api)-[0-9a-f]{8}-[0-9a-f]{12}(?:-[0-9]+)?$')
                self.assertIsNone(self.manager.launch_provenance(instance)['effective']['seat']['model'])
                audit, packet = self.new_request(instance=instance)
                self.assertEqual(audit['producer']['name'], instance['name'])
                # Internal audit supplies the fixed server reason, which the
                # real _producer binding re-derives and verifies (not config).
                audit['producer']['requested_model_reason'] = reason
                result = self.authority.prepare_request(audit, packet, audit['request_id'])
                self.assertEqual(result['request']['state'], 'queued')
                stored = self.artifacts.get_request(audit['request_id'])['audit']['producer']
                self.assertEqual((stored['requested_model'], stored['requested_model_reason']), (None, reason))

    def test_observation_load_and_import_bounds_with_healthy_control(self):
        _, bad, _ = self.graph_for_packet(self.packet(), api=True)
        _, healthy, _ = self.source_graph(attempts=True)
        data = self.export()
        base = json.loads(self.source.path.read_bytes())
        control = self.root / 'observation-load-control'
        atomic_json(control / 'artifacts' / 'index.json', base)
        self.assertEqual(len(store.ArtifactStore(control).export_lineage_ids()), 2)
        for number, value in enumerate(('x' * 257, 'bad\x01model')):
            changed = deepcopy(base)
            changed['versions'][store.request_ids(bad['request_id'])['version_id']]['provenance']['observation'][
                'confirmed_model'] = value
            root = self.root / ('observation-load-' + str(number))
            path = root / 'artifacts' / 'index.json'
            atomic_json(path, changed)
            before = path.read_bytes()
            with self.subTest(boundary='load', kind='cap' if number == 0 else 'control'):
                with self.assertRaises(store.ArtifactUnavailable):
                    store.ArtifactStore(root)
                self.assertEqual(path.read_bytes(), before)  # Unobserved-red, required green.
            def mutate(members):
                index = json.loads(members[codec.INDEX_MEMBER])
                lineage = next(x for x in index['lineages'] if x['lineage_id'] == bad['lineage_id'])
                lineage['versions'][0]['observation']['confirmed_model'] = value
                members[codec.INDEX_MEMBER] = codec.canonical_utf8(index)
            incoming = self.repack(data, mutate)
            owner = store.ArtifactStore(self.root / ('observation-import-' + str(number)))
            owner.bind_channel_policy(lambda: self.service)
            with self.subTest(boundary='import', kind='cap' if number == 0 else 'control'):
                with zipfile.ZipFile(io.BytesIO(incoming)) as zf:
                    self.assertEqual(len(codec.preflight(zf, zip_size=len(incoming))['index']['lineages']), 2)
                result = self.restore(incoming, owner=owner)
                self.assertTrue(result['ok'])
                self.assertIsNone(result['sections']['artifacts']['section_error'])
                self.assertEqual((result['sections']['artifacts']['invalid_lineages'],
                                  result['sections']['artifacts']['created_lineages']), (1, 1))
                self.assertEqual(owner.export_lineage_ids(), (healthy['lineage_id'],))
        # Existing chain guards, NOT new width reds or isolated mutation proof.
        for number, field in enumerate(('version.sequence', 'expected_parent.sequence')):
            target_id = bad['lineage_id'] if field == 'version.sequence' else healthy['lineage_id']
            def mutate_chain(members):
                index = json.loads(members[codec.INDEX_MEMBER])
                lineage = next(x for x in index['lineages'] if x['lineage_id'] == target_id)
                if field == 'version.sequence':
                    lineage['versions'][0]['sequence'] = 2**63
                else:
                    request = next(x for x in lineage['requests'] if x['expected_parent'] is not None)
                    request['expected_parent']['sequence'] = 2**63
                members[codec.INDEX_MEMBER] = codec.canonical_utf8(index)
            incoming = self.repack(data, mutate_chain)
            owner = store.ArtifactStore(self.root / ('chain-guard-' + str(number)))
            owner.bind_channel_policy(lambda: self.service)
            with self.subTest(existing_chain_guard=field):
                with zipfile.ZipFile(io.BytesIO(incoming)) as zf:
                    codec.preflight(zf, zip_size=len(incoming))
                result = self.restore(incoming, owner=owner)
                self.assertTrue(result['ok'])
                self.assertEqual((result['sections']['artifacts']['invalid_lineages'],
                                  result['sections']['artifacts']['created_lineages']), (1, 1))

    def test_maximum_record_numbers_load_through_whole_index_compatibility(self):
        _, audit, _ = self.source_graph(attempts=False)
        self.source.quarantine_submission(None, 'a' * 32, 'b' * 32,
            reason='invalid_response', content=None, now=10)
        value = deepcopy(self.source._data)
        value['requests'][audit['request_id']]['updated_at'] = 2**63-1
        value['lineages'][audit['lineage_id']]['updated_at'] = 2**63-1
        version_id = store.request_ids(audit['request_id'])['version_id']
        value['versions'][version_id]['created_at'] = 2**63-1
        diagnostic = next(iter(value['diagnostics'].values()))
        diagnostic.update(byte_count=2**63-1, received_at=2**63-1, updated_at=2**63-1)
        key = {name: diagnostic[name] for name in ('request_id', 'attempt_id', 'dispatch_id',
            'reason', 'sha256', 'byte_count', 'actor_identity_id')}
        diagnostic['id'] = self.source._diagnostic_id(key)
        value['diagnostics'] = {diagnostic['id']: diagnostic}
        value['store_overflow'] = {'id': self.source._summary_id(None), 'kind': 'store_overflow',
            'dispatch_id': None, 'counter': 1, 'latest_diagnostic_id': diagnostic['id'],
            'latest_sha256': diagnostic['sha256'], 'latest_byte_count': 2**63-1,
            'latest_reason': 'invalid_response', 'updated_at': 2**63-1}
        self.source._validate_index(value)

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
