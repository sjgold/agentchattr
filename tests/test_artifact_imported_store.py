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
from channel_lifecycle import ChannelInactive, DELETE_STEPS
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
        prepared = owner.prepare_import_lineage(portable, objects)
        with self.service._boundary():
            result = owner.import_lineage(prepared, channel=channel)
        return result

    @staticmethod
    def canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                          allow_nan=False).encode('utf-8')

    def graph_for_packet(self, packet, *, text='# Packet-bound version\r\n', api=False):
        audit = self.audit(artifact_store, self.source, packet=packet)
        if api:
            audit['producer'].update(adapter='openai-compatible', launch_attempt=uuid.uuid4().hex,
                launch_nonce=uuid.uuid4().hex, fingerprint='1' * 64,
                requested_model='REQUESTED_ARCHIVE_MODEL', requested_model_reason=None)
        self.source.reserve_request(audit, audit['request_id'])
        self.source.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                                     {'state': 'queued', 'reason': 'queued'}, now=20)
        observation = ({'confirmed_model': 'RECORDED_ARCHIVE_MODEL', 'confirmation_reason': 'api_response'}
                       if api else {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'})
        version = self.source.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
                                             text, observation, now=30)
        return self.portable(self.source, audit['lineage_id']), audit, version

    def assert_no_metadata(self, owner, before):
        self.assertEqual(owner.export_lineage_ids(), before[0])
        self.assertEqual(owner.path.read_bytes() if owner.path.exists() else None, before[1])

    @staticmethod
    def metadata_baseline(owner):
        return owner.export_lineage_ids(), owner.path.read_bytes() if owner.path.exists() else None

    def replace_packet(self, graph, packet):
        portable, objects = deepcopy(graph[0]), dict(graph[1])
        request = portable['requests'][0]
        raw = self.canonical(packet)
        scope = request['scope']
        scope.update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw),
            message_refs=[{'id': row['id'], 'uid': row['uid'],
                           'sha256': hashlib.sha256(self.canonical(row)).hexdigest()}
                          for row in packet['messages']])
        objects[('packet', scope['packet_id'])] = raw
        return portable, objects

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
        prepared = self.target.prepare_import_lineage(*graph)
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
            self.target.prepare_import_lineage(changed, objects)
        self.assertEqual((self.root / 'target' / 'artifacts' / 'objects' / (version['id'] + '.md')).read_bytes(),
                         graph[1][('version', version['id'])])
        fresh = artifact_store.ArtifactStore(self.root / 'target')
        fresh.bind_channel_policy(lambda: self.service)
        self.assertEqual(self.import_graph(graph, owner=fresh)['status'], 'created')
        self.assertEqual(fresh.get_version(version['id'])['markdown'].encode('utf-8'), graph[1][('version', version['id'])])
        self.assertFalse(list((self.root / 'target').rglob('*.tmp')))

    def test_imported_version_reuses_current_provenance_validator(self):
        packet = self.packet()
        input_text = '\ufeffSource café\r\nexact input.'
        revision = hashlib.sha256(input_text.encode('utf-8')).hexdigest()
        packet.update(scope_kind='run_accepted_messages',
            source_run={'session_id': 7, 'run_id': uuid.uuid4().hex,
                        'input_revision': revision, 'state_at_request': 'stopped'},
            input={'text': input_text, 'input_revision': revision,
                   'source_document': {'name': 'literal.json', '_artifact_seal': 'USER DATA, not authority'}})
        graph, audit, version = self.graph_for_packet(packet, api=True)
        original_validator = artifact_store.ArtifactStore._validate_version
        validated = []
        def unchanged_validator(owner, metadata, requests):
            validated.append((metadata['id'], requests[metadata['request_id']]['state']))
            return original_validator(owner, metadata, requests)
        with patch.object(artifact_store.ArtifactStore, '_validate_version', unchanged_validator):
            self.assertEqual(self.import_graph(graph)['status'], 'created')
            fresh = artifact_store.ArtifactStore(self.root / 'target')
            result = fresh.get_version(version['id'])
        self.assertIn((version['id'], 'imported'), validated)
        request = fresh.get_request(audit['request_id'])
        self.assertEqual(request['audit']['source_run'], audit['source_run'])
        self.assertEqual(request['audit']['scope'], audit['scope'])
        self.assertEqual(request['audit']['producer']['requested_model'], 'REQUESTED_ARCHIVE_MODEL')
        self.assertEqual(result['metadata']['provenance']['observation'],
                         {'confirmed_model': 'RECORDED_ARCHIVE_MODEL', 'confirmation_reason': 'api_response'})
        raw_index = json.loads(fresh.path.read_text(encoding='utf-8'))
        self.assertNotIn('import_source', raw_index['versions'][version['id']])
        self.assertEqual(fresh.get_packet(audit['scope']['packet_id']), packet)

    def test_imported_version_provenance_tamper_holds(self):
        graph, _, version = self.source_graph(attempts=False)
        self.import_graph(graph)
        index = json.loads(self.target.path.read_text(encoding='utf-8'))
        index['versions'][version['id']]['provenance']['instruction'] = 'TAMPERED_IMPORT_PROVENANCE'
        self.target.path.write_text(json.dumps(index), encoding='utf-8')
        before = self.files(self.target)
        with self.assertRaises(artifact_store.ArtifactUnavailable):
            artifact_store.ArtifactStore(self.root / 'target')
        held = artifact_store.ArtifactStore(self.root / 'target', hold_unreadable=True)
        with self.assertRaises(artifact_store.ArtifactUnavailable):
            held.get_version(version['id'])
        self.assertEqual(self.files(self.target), before)

    def test_imported_and_local_audit_grammars_cannot_be_substituted_or_null_forged(self):
        graph, audit, _ = self.source_graph(attempts=False)
        self.import_graph(graph)
        original = json.loads(self.target.path.read_text(encoding='utf-8'))
        request_id = audit['request_id']
        for change in ('missing_origin', 'null_origin', 'bad_origin', 'extra_origin',
                       'live_with_origin', 'launch_authority', 'capability_authority', 'extra_audit'):
            with self.subTest(change=change):
                value = deepcopy(original)
                row = value['requests'][request_id]
                if change == 'missing_origin':
                    row.pop('import_source')
                elif change == 'null_origin':
                    row['import_source'] = None
                elif change == 'bad_origin':
                    row['import_source']['original_state'] = 'bogus'
                elif change == 'extra_origin':
                    row['import_source']['secret'] = 'NOT_ALLOWED'
                elif change == 'live_with_origin':
                    row['state'] = 'queued'
                elif change == 'launch_authority':
                    row['audit']['producer']['launch_nonce'] = uuid.uuid4().hex
                elif change == 'capability_authority':
                    row['audit']['producer']['capabilities'] = ['artifact-v1']
                else:
                    row['audit']['extra'] = True
                self.target.path.write_text(json.dumps(value), encoding='utf-8')
                before = self.target.path.read_bytes()
                with self.assertRaises(artifact_store.ArtifactUnavailable):
                    artifact_store.ArtifactStore(self.root / 'target')
                self.assertEqual(self.target.path.read_bytes(), before)
        self.target.path.write_text(json.dumps(original), encoding='utf-8')
        for mutation in ('null_producer', 'extra_producer', 'extra_request', 'null_scope'):
            with self.subTest(portable=mutation):
                portable = deepcopy(graph[0])
                request = portable['requests'][0]
                if mutation == 'null_producer':
                    request['producer'] = None
                elif mutation == 'extra_producer':
                    request['producer']['launch_nonce'] = uuid.uuid4().hex
                elif mutation == 'extra_request':
                    request['extra'] = True
                else:
                    request['scope'] = None
                before = self.metadata_baseline(self.target)
                with self.assertRaises(artifact_store.ArtifactValidationError):
                    self.target.prepare_import_lineage(portable, graph[1])
                self.assert_no_metadata(self.target, before)
        legacy = self.audit(artifact_store, self.source)
        local = self.source.reserve_request(legacy, legacy['request_id'])
        self.assertEqual(local['audit']['producer']['capabilities'], ['artifact-v1'])
        self.assertIsNone(local['audit']['producer']['launch_nonce'])
        for change in ({'adapter': 'openai-compatible'}, {'capabilities': []}):
            invalid = self.audit(artifact_store, self.source)
            invalid['producer'].update(change)
            before = self.metadata_baseline(self.source)
            with self.assertRaises(artifact_store.ArtifactValidationError):
                self.source.reserve_request(invalid, invalid['request_id'])
            self.assert_no_metadata(self.source, before)

    def test_duplicate_whole_graph_local_or_imported_and_partial_uid_collisions_skip_without_merge(self):
        graph, audit, version = self.source_graph()
        before = self.files(self.source)
        prepared = self.source.prepare_import_lineage(*graph)
        expected = {'status': 'skipped', 'reason': 'duplicate', 'collision_kinds': [],
                    'created_versions': 0, 'created_requests': 0}
        with self.service._boundary():
            self.assertEqual(self.source.classify_import_lineage(prepared), expected)
            self.assertEqual(self.source.import_lineage(prepared, channel='review'), expected)
        self.assertEqual(self.files(self.source), before)
        self.import_graph(graph)
        imported_before = self.files(self.target)
        self.assertEqual(self.import_graph(graph), expected)
        self.assertEqual(self.files(self.target), imported_before)
        changed = deepcopy(graph[0])
        changed['lineage_id'] = uuid.uuid4().hex
        prepared = self.target.prepare_import_lineage(changed, graph[1])
        with self.service._boundary():
            result = self.target.classify_import_lineage(prepared)
            self.assertEqual(result, self.target.import_lineage(prepared, channel='review'))
        self.assertEqual(result['reason'], 'uid_collision')
        self.assertEqual(set(result['collision_kinds']), {'request', 'version', 'packet', 'dispatch'})
        self.assertEqual(result['created_versions'], 0)
        self.assertEqual(result['created_requests'], 0)
        self.assertEqual(self.files(self.target), imported_before)
        divergent, objects = deepcopy(graph[0]), dict(graph[1])
        changed_bytes = b'# Divergent indexed Markdown'
        divergent['versions'][0].update(sha256=hashlib.sha256(changed_bytes).hexdigest(), byte_length=len(changed_bytes))
        for row in divergent['requests']:
            if row['expected_parent']:
                row['expected_parent']['sha256'] = hashlib.sha256(changed_bytes).hexdigest()
        objects[('version', version['id'])] = changed_bytes
        with self.assertRaises(artifact_store.ArtifactImportCollision) as caught:
            self.target.prepare_import_lineage(divergent, objects)
        self.assertEqual(caught.exception.reason, 'uid_collision')
        self.assertIn('version', caught.exception.collision_kinds)
        self.assertEqual(self.files(self.target), imported_before)

    def test_imported_terminal_guards_pending_and_dispatch_getters_never_reactivate_history(self):
        graph, audit, version = self.source_graph()
        self.import_graph(graph)
        before = self.files(self.target)
        for request in graph[0]['requests']:
            request_id = request['request_id']
            ids = artifact_store.request_ids(request_id)
            row = self.target.get_request(request_id)
            self.assertEqual(self.target.get_request_by_dispatch(ids['dispatch_id']), row)
            with self.assertRaises(artifact_store.ArtifactConflict):
                self.target.set_attempt_state(request_id, ids['attempt_id'], 'imported',
                    {'state': 'queued', 'reason': 'queued'})
            with self.assertRaises(artifact_store.ArtifactConflict):
                self.target.commit_version(request_id, ids['attempt_id'], ids['dispatch_id'], '# No admission',
                    {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'})
            with self.assertRaises(artifact_store.ArtifactValidationError):
                self.target.reserve_request(row['audit'], request_id)
        self.assertEqual(self.target.pending('review'), [])
        self.assertEqual(self.target.list_versions(audit['lineage_id'])['rows'][0]['id'], version['id'])
        self.assertEqual(self.files(self.target), before)
        self.assertFalse((self.root / 'target' / 'queue').exists())

    def test_real_markdown_packet_message_limits_and_hash_binding_reject_without_partial_index(self):
        graph, _, version = self.source_graph(text='x' * 524288, attempts=False)
        self.assertEqual(len(graph[1][('version', version['id'])]), 524288)
        self.assertEqual(self.import_graph(graph)['status'], 'created')
        packet = self.packet()
        packet['messages'][0]['text'] = 'x'
        packet['messages'][0]['text'] += 'x' * (2097152 - len(self.canonical(packet)))
        self.assertEqual(len(self.canonical(packet)), 2097152)
        packet_graph, _, _ = self.graph_for_packet(packet)
        self.assertEqual(self.import_graph(packet_graph)['status'], 'created')
        messages = self.packet()
        messages['messages'] = [{**messages['messages'][0], 'id': i, 'uid': 'source-' + str(i), 'text': 'x'} for i in range(1000)]
        message_graph, _, _ = self.graph_for_packet(messages)
        self.assertEqual(self.import_graph(message_graph)['status'], 'created')
        # New IDs avoid collision-based refusal masking byte/content validation.
        valid, _, _ = self.source_graph(attempts=False)
        invalid = []
        oversized, bodies = deepcopy(valid[0]), dict(valid[1])
        raw = b'x' * 524289
        vid = oversized['versions'][0]['version_id']
        oversized['versions'][0].update(byte_length=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        bodies[('version', vid)] = raw
        invalid.append((oversized, bodies))
        too_big = deepcopy(packet)
        too_big['messages'][0]['text'] += 'x'
        invalid.append(self.replace_packet(valid, too_big))
        too_many = deepcopy(messages)
        too_many['messages'].append({**too_many['messages'][0], 'id': 1000, 'uid': 'source-1000'})
        invalid.append(self.replace_packet(valid, too_many))
        bad_hash = deepcopy(valid[0])
        bad_hash['requests'][0]['scope']['message_refs'][0]['sha256'] = '0' * 64
        invalid.append((bad_hash, valid[1]))
        bad_body = dict(valid[1])
        bad_body[('version', vid)] = b'WRONG_HASH_BODY'
        invalid.append((valid[0], bad_body))
        for raw in (b'NUL\x00text', b'bad\xffUTF8'):
            portable, objects = deepcopy(valid[0]), dict(valid[1])
            portable['versions'][0].update(byte_length=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            objects[('version', vid)] = raw
            invalid.append((portable, objects))
        for index, (portable, objects) in enumerate(invalid):
            with self.subTest(index=index):
                before = self.metadata_baseline(self.target)
                with self.assertRaises(artifact_store.ArtifactValidationError):
                    self.target.prepare_import_lineage(portable, objects)
                self.assert_no_metadata(self.target, before)

    def test_prepared_plan_detaches_inputs_is_root_bound_and_detects_staged_file_change(self):
        graph, _, version = self.source_graph(attempts=False)
        portable, objects = deepcopy(graph[0]), dict(graph[1])
        prepared = self.target.prepare_import_lineage(portable, objects)
        portable['requests'][0]['instruction'] = 'EXTERNAL_MUTATION'
        objects.clear()
        foreign = artifact_store.ArtifactStore(self.root / 'foreign')
        foreign.bind_channel_policy(lambda: self.service)
        with self.service._boundary(), self.assertRaises(artifact_store.ArtifactValidationError):
            foreign.import_lineage(prepared, channel='review')
        with self.service._boundary():
            self.assertEqual(self.target.import_lineage(prepared, channel='review')['status'], 'created')
        self.assertEqual(self.target.get_version(version['id'])['metadata']['provenance']['instruction'],
                         graph[0]['requests'][0]['instruction'])
        other, _, other_version = self.source_graph(attempts=False)
        prepared = self.target.prepare_import_lineage(*other)
        staged = self.root / 'target' / 'artifacts' / 'objects' / (other_version['id'] + '.md')
        staged.write_bytes(b'CHANGED_AFTER_VALIDATION')
        before = self.metadata_baseline(self.target)
        with self.service._boundary(), self.assertRaises(artifact_store.ArtifactUnavailable):
            self.target.import_lineage(prepared, channel='review')
        self.assert_no_metadata(self.target, before)

    def test_object_stage_fault_leaves_no_partial_metadata_or_temp_and_reports_orphans(self):
        graph, _, version = self.source_graph(attempts=False)
        replace = Path.replace
        destination = self.root / 'target' / 'artifacts' / 'objects' / (version['id'] + '.md')
        def fail_exact_object(path, target):
            if Path(target) == destination:
                raise OSError('Controlled immutable object replace failure')
            return replace(path, target)
        before = self.metadata_baseline(self.target)
        with patch.object(Path, 'replace', fail_exact_object), self.assertRaises(artifact_store.ArtifactUnavailable):
            self.target.prepare_import_lineage(*graph)
        self.assert_no_metadata(self.target, before)
        self.assertFalse(destination.exists())
        self.assertFalse(list((self.root / 'target').rglob('*.tmp')))
        self.assertEqual(self.import_graph(graph)['status'], 'created')
        self.assertEqual(destination.read_bytes(), graph[1][('version', version['id'])])

    def test_export_metadata_snapshot_ids_and_referenced_reads_are_detached_strict_and_bounded(self):
        self.assertEqual(self.target.export_lineage_ids(), ())
        graph, audit, version = self.source_graph()
        before = self.files(self.source)
        open_file = Path.open
        def forbid_bodies(path, *args, **kwargs):
            if path.suffix == '.md' or path.parent.name == 'packets':
                raise AssertionError('Metadata read attempted immutable body IO')
            return open_file(path, *args, **kwargs)
        with patch.object(Path, 'open', forbid_bodies):
            selected = self.source.export_lineage_ids()
            snapshot = self.source.export_metadata(audit['lineage_id'])
        self.assertEqual(selected, (audit['lineage_id'],))
        snapshot['requests'][0]['audit']['instruction'] = 'DETACHED_MUTATION'
        self.assertNotEqual(self.source.export_metadata(audit['lineage_id']), snapshot)
        self.assertEqual(self.files(self.source), before)
        self.source_graph(attempts=False)
        self.assertEqual(selected, (audit['lineage_id'],))
        self.assertEqual(len(self.source.export_lineage_ids()), 2)
        raw = self.source.read_archive_object('version', version['id'], sha256=version['sha256'], byte_length=version['byte_length'])
        self.assertEqual(raw, graph[1][('version', version['id'])])
        for kind, identifier, digest, length in (('version', uuid.uuid4().hex, version['sha256'], version['byte_length']),
                ('version', version['id'], '0' * 64, version['byte_length']),
                ('version', version['id'], version['sha256'], version['byte_length'] + 1)):
            with self.assertRaises(artifact_store.ArtifactUnavailable):
                self.source.read_archive_object(kind, identifier, sha256=digest, byte_length=length)
        orphan_id = uuid.uuid4().hex
        orphan = self.root / 'source' / 'artifacts' / 'objects' / (orphan_id + '.md')
        orphan.write_bytes(b'# Orphan is not an export reference')
        with self.assertRaises(artifact_store.ArtifactUnavailable):
            self.source.read_archive_object('version', orphan_id,
                sha256=hashlib.sha256(orphan.read_bytes()).hexdigest(), byte_length=orphan.stat().st_size)
        self.source.path.write_bytes(b'{broken index')
        broken = self.files(self.source)
        held = artifact_store.ArtifactStore(self.root / 'source', hold_unreadable=True)
        with self.assertRaises(artifact_store.ArtifactUnavailable):
            held.export_lineage_ids()
        self.assertEqual(self.files(self.source), broken)

    def test_imported_history_rename_moves_only_outer_channel_and_stays_readable_after_retirement(self):
        graph, audit, version = self.source_graph()
        self.import_graph(graph)
        frozen = self.target.export_metadata(audit['lineage_id'])
        immutable = {key: value for key, value in self.files(self.target).items()
                     if key.startswith('artifacts/objects/') or key.startswith('artifact_briefs/packets/')}
        staged_graph, _, _ = self.source_graph(attempts=False)
        self.catalog.set_state('review', 'archived', expected_revision=self.catalog.snapshot()['revision'])
        prepared = self.target.prepare_import_lineage(*staged_graph)
        before = self.metadata_baseline(self.target)
        with self.service._boundary(), self.assertRaises(ChannelInactive):
            self.target.import_lineage(prepared, channel='review')
        self.assert_no_metadata(self.target, before)
        self.target.rename_channel('review', 'peer')  # Internal held-intent machinery bypasses ordinary writes.
        moved = self.target.export_metadata(audit['lineage_id'])
        self.assertEqual(moved['lineage']['channel'], 'peer')
        for old, new in zip(frozen['requests'], moved['requests']):
            self.assertEqual(new['channel'], 'peer')
            self.assertEqual(new['audit'], old['audit'])
            self.assertEqual(new['import_source'], old['import_source'])
            self.assertEqual(new['updated_at'], old['updated_at'])
        self.assertEqual(moved['versions'][0]['channel'], 'peer')
        self.assertEqual(moved['versions'][0]['provenance'], frozen['versions'][0]['provenance'])
        for key, value in immutable.items():
            self.assertEqual(self.files(self.target)[key], value)
        operation = uuid.uuid4().hex
        self.catalog.begin('delete', 'peer', None, request_id=operation, expected_revision=self.catalog.snapshot()['revision'])
        for step in DELETE_STEPS:
            self.catalog.complete_step(operation, step)
        self.catalog.finish(operation)
        self.assertEqual(self.target.get_version(version['id'])['markdown'].encode('utf-8'), graph[1][('version', version['id'])])
        self.assertEqual(self.target.pending('peer'), [])
        before = self.files(self.target)
        self.target.rename_channel('review', 'peer')
        self.assertEqual(self.files(self.target), before)


if __name__ == '__main__':
    unittest.main()
