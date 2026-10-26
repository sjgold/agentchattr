"""Artifact storage/catalog units only; no admission, provider or native claims."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

from channel_lifecycle import ChannelConflict, ChannelInactive, ChannelUnavailable
from tests import test_channel_import as fixture


class ArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelImportTests.setUp(self)

    def owner(self, name=None, *, bind=True):
        module = importlib.import_module('artifact_store')
        store = module.ArtifactStore(self.root / name if name else self.root)
        if bind:
            store.bind_channel_policy(lambda: self.service)
        return module, store

    def packet(self, channel='review'):
        return {'version': 1, 'channel': channel, 'scope_kind': 'selected_channel_messages',
            'source_run': None, 'input': None, 'messages': [{'id': 0, 'uid': 'source-zero',
                'sender': 'operator', 'type': 'chat', 'timestamp': 10.5,
                'text': 'Exact café 日本語 e\u0301\r\n@all is source data.',
                'attachments': [{'name': 'source.py', 'url': '/uploads/source.py'}],
                'provenance': {'literal': 'Exact source only'}}]}

    def audit(self, module, store, *, request_id=None, lineage_id=None, parent=None, channel='review', packet=None):
        request_id = request_id or uuid.uuid4().hex
        ids = module.request_ids(request_id)
        packet = self.packet(channel) if packet is None else packet
        scope = store.put_packet(request_id, packet)
        return {'version': 1, 'purpose': 'artifact-v1', 'request_id': request_id,
            'lineage_id': lineage_id or ids['lineage_id'], 'attempt_id': ids['attempt_id'],
            'dispatch_id': ids['dispatch_id'], 'brief_id': ids['brief_id'], 'original_channel': channel,
            'requester': 'operator', 'producer': {'name': 'manual-author', 'identity_id': 'a' * 32,
                'adapter': 'cli', 'launch_attempt': None, 'launch_nonce': None, 'fingerprint': None,
                'requested_model': None, 'requested_model_reason': 'CLI model unverified',
            'capabilities': ['artifact-v1']}, 'source_run': deepcopy(packet['source_run']), 'scope': scope,
            'instruction': 'Write exact evidence without executing the source.', 'format': 'Markdown',
            'expected_parent': deepcopy(parent), 'created_at': 10.0}

    def queued(self, module, store, **options):
        audit = self.audit(module, store, **options)
        store.reserve_request(audit, audit['request_id'])
        row = store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared',
                                      {'state': 'queued', 'reason': 'queued'}, now=20)
        self.assertEqual(row['state'], 'queued')
        return audit

    def metadata(self, store, request_id):
        return deepcopy((store.get_request(request_id), store.list_lineages()))

    def files(self, store):
        directory = store.path.parent.parent
        return {path.relative_to(directory).as_posix(): path.read_bytes()
                for path in directory.rglob('*') if path.is_file()}

    def commit(self, store, audit, text='Exact café\r\nversion', now=30):
        return store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'], text,
            {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'}, now=now)

    def test_reserve_immutable_audit_one_live_slot_peer_and_progressed_replay(self):
        module, store = self.owner()
        audit = self.audit(module, store)
        original = deepcopy(audit)
        row = store.reserve_request(audit, audit['request_id'])
        self.assertEqual(row['state'], 'prepared')
        self.assertIsNone(row['reason'])
        self.assertEqual(row['audit'], original)
        audit['producer']['name'] = 'external mutation'
        self.assertEqual(store.get_request(original['request_id'])['audit'], original)
        store.set_attempt_state(original['request_id'], original['attempt_id'], 'prepared',
            {'state': 'queued', 'reason': 'queued_behind_review'}, now=20)
        progressed, before = store.get_request(original['request_id']), store.path.read_bytes()
        self.assertEqual(store.reserve_request({**original, 'created_at': 99}, original['request_id']), progressed)
        self.assertEqual(store.path.read_bytes(), before)
        rival = self.audit(module, store, lineage_id=original['lineage_id'])
        with self.assertRaises(module.ArtifactConflict):
            store.reserve_request(rival, rival['request_id'])
        self.assertEqual(store.path.read_bytes(), before)
        self.assertIn(rival['scope']['packet_id'], json.dumps(store.diagnostics()))
        peer = self.audit(module, store, channel='peer')
        self.assertEqual(store.reserve_request(peer, peer['request_id'])['state'], 'prepared')
        self.assertEqual({row['request_id'] for row in store.pending('review')}, {original['request_id']})
        self.assertEqual({row['request_id'] for row in store.pending('peer')}, {peer['request_id']})

    def test_object_and_index_commit_faults_preserve_metadata_and_report_orphan(self):
        module, store = self.owner()
        audit = self.queued(module, store)
        markdown = '\ufeff# Exact café\r\n\r\nJapanese 日本語 e\u0301.\r\n'
        observation = {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'}
        ids = module.request_ids(audit['request_id'])
        object_path = self.root / 'artifacts' / 'objects' / (ids['version_id'] + '.md')
        before, metadata = store.path.read_bytes(), self.metadata(store, audit['request_id'])
        original_replace = Path.replace
        def fail_object(source, target):
            if Path(target) == object_path:
                raise OSError('local object replacement failure')
            return original_replace(source, target)
        with patch.object(Path, 'replace', fail_object):
            with self.assertRaises(module.ArtifactUnavailable):
                store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'], markdown, observation, now=30)
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(self.metadata(store, audit['request_id']), metadata)
        self.assertFalse(object_path.exists())
        self.assertEqual(list(object_path.parent.rglob('*.tmp')), [])
        with patch('artifact_store.atomic_json', side_effect=OSError('local index failure')):
            with self.assertRaises(module.ArtifactUnavailable):
                store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'], markdown, observation, now=30)
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(self.metadata(store, audit['request_id']), metadata)
        self.assertEqual(object_path.read_bytes(), markdown.encode('utf-8'))
        self.assertIsNone(store.get_version(ids['version_id']))
        self.assertIn(ids['version_id'], json.dumps(store.diagnostics(), ensure_ascii=False))
        restored = module.ArtifactStore(self.root)
        self.assertEqual(self.metadata(restored, audit['request_id']), metadata)
        with self.assertRaises(module.ArtifactConflict):
            self.commit(store, audit, markdown + 'Conflicting orphan overwrite', now=31)
        self.assertEqual(object_path.read_bytes(), markdown.encode('utf-8'))
        result = self.commit(store, audit, markdown, now=32)
        self.assertEqual(result['id'], ids['version_id'])
        self.assertEqual(object_path.read_bytes(), markdown.encode('utf-8'))

    def test_markdown_exact_bytes_real_boundary_and_invalid_text_have_no_partial_commit(self):
        module, store = self.owner()
        texts = ['\ufeff# 日本語 😀 e\u0301\r\n\r\n  spaced\ttext\n',
                 'a' * (512 * 1024 - 2) + '\r\n']
        for text in texts:
            audit = self.queued(module, store)
            metadata = self.commit(store, audit, text)
            path = self.root / 'artifacts/objects' / (metadata['id'] + '.md')
            self.assertEqual(path.read_bytes(), text.encode('utf-8'))
            self.assertEqual(metadata['sha256'], hashlib.sha256(text.encode('utf-8')).hexdigest())
            self.assertEqual(metadata['byte_length'], len(text.encode('utf-8')))
            self.assertEqual(store.get_version(metadata['id'])['markdown'], text)
        audit = self.queued(module, store)
        for text in ('', ' \t\r\n', '\x00bad', '\ud800', b'not text', 'a' * (512 * 1024 + 1)):
            with self.subTest(text_type=type(text).__name__, length=len(text)):
                before = self.files(store)
                with self.assertRaises(module.ArtifactValidationError):
                    self.commit(store, audit, text)
                self.assertEqual(self.files(store), before)
        for field, cap in [('instruction', 32 * 1024), ('format', 512)]:
            valid = self.audit(module, store)
            valid[field] = 'x' * cap
            store.reserve_request(valid, valid['request_id'])
            invalid = self.audit(module, store)
            invalid[field] = 'x' * (cap + 1)
            before = self.files(store)
            with self.assertRaises(module.ArtifactValidationError):
                store.reserve_request(invalid, invalid['request_id'])
            self.assertEqual(self.files(store), before)
        for name, mutate in [('bool-version', lambda value: value.update(version=True)),
                ('bool-time', lambda value: value.update(created_at=True)),
                ('nan-time', lambda value: value.update(created_at=float('nan'))),
                ('nul-instruction', lambda value: value.update(instruction='bad\x00text')),
                ('extra-audit-field', lambda value: value.update(secret='not-a-schema-field')),
                ('api-missing-launch', lambda value: value['producer'].update(adapter='openai-compatible')),
                ('missing-model-reason', lambda value: value['producer'].update(requested_model_reason=None)),
                ('partial-launch', lambda value: value['producer'].update(launch_attempt='a' * 32))]:
            with self.subTest(invalid_audit=name):
                value = self.audit(module, store)
                mutate(value)
                before = self.files(store)
                with self.assertRaises(module.ArtifactValidationError):
                    store.reserve_request(value, value['request_id'])
                self.assertEqual(self.files(store), before)
        for request_id in (True, 0, '', 'A' * 32, '../unsafe'):
            with self.subTest(request_id=request_id), self.assertRaises(module.ArtifactValidationError):
                module.request_ids(request_id)

    def test_packets_have_independent_unicode_golden_hashes_replay_caps_and_uid_collision(self):
        module, store = self.owner()
        request = uuid.uuid4().hex
        packet = self.packet()
        packet['messages'][0]['text'] += '\nLiteral \\r\\n stays literal.'
        canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True,
                                             separators=(',', ':'), allow_nan=False).encode('utf-8')
        raw = canonical(packet)
        scope = store.put_packet(request, packet)
        expected = {'kind': packet['scope_kind'], 'packet_id': module.request_ids(request)['packet_id'],
            'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw),
            'message_refs': [{'id': 0, 'uid': 'source-zero',
                'sha256': hashlib.sha256(canonical(packet['messages'][0])).hexdigest()}], 'input_revision': None}
        self.assertEqual(scope, expected)
        self.assertNotEqual(scope['sha256'], hashlib.sha256(json.dumps(packet, ensure_ascii=True,
            sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest())
        before = self.files(store)
        self.assertEqual(store.put_packet(request, deepcopy(packet)), scope)
        self.assertEqual(self.files(store), before)
        loaded = store.get_packet(scope['packet_id'])
        loaded['messages'][0]['provenance']['literal'] = 'outside mutation'
        self.assertEqual(store.get_packet(scope['packet_id']), packet)
        changed = deepcopy(packet)
        changed['messages'][0]['text'] += ' changed'
        with self.assertRaises(module.ArtifactConflict):
            store.put_packet(request, changed)
        for collision in ('id', 'uid', 'legacy_uid'):
            invalid = self.packet()
            second = deepcopy(invalid['messages'][0])
            second.update(id=5, uid='different')
            if collision == 'id':
                second['id'] = 0
            elif collision == 'uid':
                second['uid'] = 'source-zero'
            else:
                invalid['messages'][0].update(id=0, uid='legacy:5')
                second.update(id=5, uid='legacy:5')
            invalid['messages'].append(second)
            with self.subTest(collision=collision), self.assertRaises(module.ArtifactValidationError):
                store.put_packet(uuid.uuid4().hex, invalid)
        for size in (1000, 1001):
            value = self.packet()
            value['messages'] = [{**value['messages'][0], 'id': n, 'uid': 'msg-' + str(n)} for n in range(size)]
            if size == 1000:
                self.assertEqual(len(store.put_packet(uuid.uuid4().hex, value)['message_refs']), 1000)
            else:
                with self.assertRaises(module.ArtifactValidationError):
                    store.put_packet(uuid.uuid4().hex, value)
        boundary = self.packet()
        boundary['messages'][0]['text'] = ''
        boundary['messages'][0]['text'] = 'x' * (2 * 1024 * 1024 - len(canonical(boundary)))
        self.assertEqual(len(canonical(boundary)), 2 * 1024 * 1024)
        self.assertEqual(store.put_packet(uuid.uuid4().hex, boundary)['byte_length'], 2 * 1024 * 1024)
        oversized = deepcopy(boundary)
        oversized['messages'][0]['text'] += 'x'
        with self.assertRaises(module.ArtifactValidationError):
            store.put_packet(uuid.uuid4().hex, oversized)
        run_packet = self.packet()
        revision = hashlib.sha256(b'Input\r\nexact').hexdigest()
        run_packet.update(scope_kind='run_accepted_messages',
            source_run={'session_id': 1, 'run_id': 'b' * 32, 'input_revision': revision, 'state_at_request': 'stopped'},
            input={'text': 'Input\r\nexact', 'input_revision': revision, 'source_document': None})
        self.assertEqual(store.put_packet(uuid.uuid4().hex, run_packet)['input_revision'], revision)
        run_packet['input']['input_revision'] = 'c' * 64
        with self.assertRaises(module.ArtifactValidationError):
            store.put_packet(uuid.uuid4().hex, run_packet)
        for label, mutate in [('bool-version', lambda value: value.update(version=True)),
                ('bool-message-id', lambda value: value['messages'][0].update(id=True)),
                ('bool-timestamp', lambda value: value['messages'][0].update(timestamp=True)),
                ('nested-nonfinite', lambda value: value['messages'][0]['provenance'].update(bad=float('inf'))),
                ('unsupported-metadata', lambda value: value['messages'][0]['provenance'].update(bad={'set'})),
                ('extra-packet-key', lambda value: value.update(secret='unsupported'))]:
            with self.subTest(invalid_packet=label):
                value = self.packet()
                mutate(value)
                before = self.files(store)
                with self.assertRaises(module.ArtifactValidationError):
                    store.put_packet(uuid.uuid4().hex, value)
                self.assertEqual(self.files(store), before)

    def test_state_transitions_preserve_audit_terminal_reasons_and_pending_ownership(self):
        module, store = self.owner()
        for start, destinations in [('prepared', ['queued', 'active', 'failed', 'cancelled', 'quarantined']),
                                    ('queued', ['active', 'failed', 'cancelled', 'quarantined']),
                                    ('active', ['failed', 'cancelled', 'quarantined'])]:
            for target in destinations:
                with self.subTest(start=start, target=target):
                    audit = self.audit(module, store)
                    store.reserve_request(audit, audit['request_id'])
                    if start != 'prepared':
                        store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'prepared', {'state': start, 'reason': None}, now=20)
                    changed = store.set_attempt_state(audit['request_id'], audit['attempt_id'], start,
                        {'state': target, 'reason': 'generation_failed' if target == 'failed' else None}, now=30)
                    self.assertEqual(changed['audit'], audit)
                    self.assertEqual(changed['state'], target)
                    before = store.path.read_bytes()
                    self.assertEqual(store.set_attempt_state(audit['request_id'], audit['attempt_id'], start,
                        {'state': target, 'reason': changed['reason']}, now=40), changed)
                    self.assertEqual(store.path.read_bytes(), before)
                    if target in ('failed', 'cancelled', 'quarantined'):
                        with self.assertRaises(module.ArtifactConflict):
                            store.set_attempt_state(audit['request_id'], audit['attempt_id'], target,
                                {'state': target, 'reason': 'operator_cancelled'}, now=41)
                        self.assertNotIn(audit['request_id'], {row['request_id'] for row in store.pending('review')})
        audit = self.queued(module, store)
        active = store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'queued',
                                         {'state': 'active', 'reason': 'resume_pending'}, now=50)
        changed = store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'active',
                                          {'state': 'active', 'reason': 'queued_behind_review'}, now=51)
        self.assertEqual(changed['audit'], active['audit'])
        for attempt, expected, change in [(uuid.uuid4().hex, 'active', {'state': 'failed', 'reason': None}),
                (audit['attempt_id'], 'prepared', {'state': 'failed', 'reason': None})]:
            with self.assertRaises(module.ArtifactConflict):
                store.set_attempt_state(audit['request_id'], attempt, expected, change, now=60)
        with self.assertRaises(module.ArtifactConflict):
            store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'active',
                                    {'state': 'fulfilled', 'reason': None}, now=60)
        for change in ({'state': 'bogus', 'reason': None}, {'state': 'failed', 'reason': 'PRIVATE_ERROR'},
                       {'state': 'failed', 'reason': None, 'audit': {}}):
            with self.assertRaises(module.ArtifactValidationError):
                store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'active', change, now=60)

    def test_commit_replay_parent_cas_and_observation_preserve_old_versions(self):
        module, store = self.owner()
        audit = self.queued(module, store)
        first = self.commit(store, audit, '# First\r\nexact', now=30)
        before = self.files(store)
        self.assertEqual(self.commit(store, audit, '# First\r\nexact', now=900), first)
        self.assertEqual(self.files(store), before)
        for attempt, text in [(audit['attempt_id'], 'Different content'), (uuid.uuid4().hex, '# First\r\nexact')]:
            with self.assertRaises(module.ArtifactConflict):
                store.commit_version(audit['request_id'], attempt, audit['dispatch_id'], text,
                    {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'})
        parent = {'version_id': first['id'], 'sequence': 1, 'sha256': first['sha256']}
        stale = self.audit(module, store, lineage_id=audit['lineage_id'], parent={**parent, 'sha256': '0' * 64})
        index = store.path.read_bytes()
        with self.assertRaises(module.ArtifactConflict):
            store.reserve_request(stale, stale['request_id'])
        self.assertEqual(store.path.read_bytes(), index)
        next_audit = self.queued(module, store, lineage_id=audit['lineage_id'], parent=parent)
        with self.assertRaises(module.ArtifactValidationError):
            store.commit_version(next_audit['request_id'], next_audit['attempt_id'], next_audit['dispatch_id'], 'No fake model',
                {'confirmed_model': 'claimed-by-cli', 'confirmation_reason': 'api_response'})
        second = self.commit(store, next_audit, '# Second\r\nexact', now=40)
        self.assertEqual((second['sequence'], second['parent_version_id']), (2, first['id']))
        self.assertEqual(store.get_version(first['id'])['markdown'], '# First\r\nexact')
        self.assertEqual([row['id'] for row in store.list_versions(audit['lineage_id'])['rows']], [second['id'], first['id']])
        # Structural trusted-observation dictionaries only, no actual API/model claim.
        for observation in ({'confirmed_model': 'fixture-confirmed-model', 'confirmation_reason': 'api_response'},
                            {'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'}):
            api_audit = self.audit(module, store)
            api_audit['producer'].update(adapter='openai-compatible', launch_attempt='c' * 32,
                launch_nonce='d' * 32, fingerprint='e' * 64, requested_model='fixture-requested-model', requested_model_reason=None)
            store.reserve_request(api_audit, api_audit['request_id'])
            store.set_attempt_state(api_audit['request_id'], api_audit['attempt_id'], 'prepared',
                                    {'state': 'queued', 'reason': 'queued'}, now=50)
            result = store.commit_version(api_audit['request_id'], api_audit['attempt_id'], api_audit['dispatch_id'],
                                           '# API-shaped dictionary\r\nexact', observation, now=60)
            self.assertEqual(result['sha256'], hashlib.sha256(b'# API-shaped dictionary\r\nexact').hexdigest())
            self.assertIn(observation['confirmation_reason'], json.dumps(result['provenance']))

    def test_deterministic_concurrent_parent_cas_has_one_winner_and_peer_progress(self):
        module, store = self.owner()
        audit = self.queued(module, store)
        head = self.commit(store, audit)
        parent = {'version_id': head['id'], 'sequence': head['sequence'], 'sha256': head['sha256']}
        choices = [self.audit(module, store, lineage_id=audit['lineage_id'], parent=parent) for _ in range(2)]
        peer = self.audit(module, store, channel='peer')
        barrier = threading.Barrier(3)
        def reserve(value):
            barrier.wait(timeout=3)
            try:
                return store.reserve_request(value, value['request_id'])
            except module.ArtifactConflict:
                return None
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(reserve, value) for value in choices + [peer]]
            results = [future.result(timeout=5) for future in futures]
        self.assertEqual(sum(row is not None for row in results[:2]), 1)
        self.assertEqual(results[2]['audit'], peer)
        self.assertEqual(len(store.pending('review')), 1)
        self.assertEqual(len(store.pending('peer')), 1)
        self.assertEqual(store.list_versions(audit['lineage_id'])['count'], 1)

    def test_policy_wait_never_holds_store_lock_or_blocks_low_level_cancellation(self):
        module, store = self.owner()
        audit = self.queued(module, store)
        entered, proceed, cancelled = threading.Event(), threading.Event(), threading.Event()
        def getter():
            entered.set()
            self.assertTrue(proceed.wait(3))
            return self.service
        store.bind_channel_policy(getter)
        def cancel():
            row = store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'queued',
                                          {'state': 'cancelled', 'reason': 'operator_cancelled'}, now=30)
            cancelled.set()
            return row
        with ThreadPoolExecutor(max_workers=2) as pool:
            ordinary = pool.submit(store.put_packet, uuid.uuid4().hex, self.packet('peer'))
            try:
                self.assertTrue(entered.wait(3))
                settlement = pool.submit(cancel)
                self.assertTrue(cancelled.wait(3), 'Cancellation must finish while ordinary write waits BEFORE policy')
            finally:
                proceed.set()
            self.assertEqual(settlement.result(timeout=3)['state'], 'cancelled')
            self.assertEqual(ordinary.result(timeout=3)['kind'], 'selected_channel_messages')

    def test_quarantine_requestless_matching_only_dedupe_and_no_state_poisoning(self):
        module, store = self.owner()
        audit = self.queued(module, store)
        before = store.get_request(audit['request_id'])
        unknown = store.quarantine_submission(None, uuid.uuid4().hex, uuid.uuid4().hex,
            reason='unmatched_saved_result', content='Exact café\r\ndiagnostic', now=100)
        self.assertEqual(unknown['kind'], 'quarantine')
        unknown_id = uuid.uuid4().hex
        self.assertEqual(store.quarantine_submission(unknown_id, uuid.uuid4().hex, uuid.uuid4().hex,
            reason='unmatched_saved_result', content=None, now=100.5)['request_id'], unknown_id)
        self.assertEqual(store.get_request(audit['request_id']), before)
        mismatch = store.quarantine_submission(audit['request_id'], audit['attempt_id'], uuid.uuid4().hex,
            reason='wrong_dispatch', content='Wrong dispatch', now=101)
        self.assertNotIn(mismatch['id'], store.request_diagnostics(audit['request_id'])['quarantine_ids'])
        wrong_attempt = uuid.uuid4().hex
        detailed = store.quarantine_submission(audit['request_id'], wrong_attempt, audit['dispatch_id'],
            reason='wrong_attempt', content='Exact café\r\nbody', actor_identity_id='b' * 32, now=102)
        row = store.get_request(audit['request_id'])
        self.assertEqual(row['state'], before['state'])
        self.assertEqual(row['audit'], before['audit'])
        self.assertEqual(store.request_diagnostics(audit['request_id'])['quarantine_ids'], [detailed['id']])
        key = {'request_id': audit['request_id'], 'attempt_id': wrong_attempt, 'dispatch_id': audit['dispatch_id'],
            'reason': 'wrong_attempt', 'sha256': hashlib.sha256('Exact café\r\nbody'.encode()).hexdigest(),
            'byte_count': len('Exact café\r\nbody'.encode()), 'actor_identity_id': 'b' * 32}
        canonical = json.dumps(key, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        self.assertEqual(detailed['id'], uuid.uuid5(uuid.NAMESPACE_URL, canonical).hex)
        snapshot = self.files(store)
        self.assertEqual(store.quarantine_submission(audit['request_id'], wrong_attempt, audit['dispatch_id'],
            reason='wrong_attempt', content='Exact café\r\nbody', actor_identity_id='b' * 32, now=999), detailed)
        self.assertEqual(self.files(store), snapshot)
        diagnostics = store.diagnostics()
        self.assertTrue(all('body' not in row and 'content' not in row for row in diagnostics['rows']))
        escaped_body = json.dumps('Exact café\r\nbody', ensure_ascii=False)[1:-1]
        self.assertNotIn(escaped_body, json.dumps(diagnostics, ensure_ascii=False))

    def test_real_default_diagnostic_caps_overflow_last_key_and_orphan_body_budgets(self):
        module, store = self.owner('per-dispatch')
        for name, expected in [('MAX_DIAGNOSTICS_PER_DISPATCH', 8), ('MAX_DIAGNOSTIC_DISPATCH_GROUPS', 256),
                ('MAX_DIAGNOSTIC_RECORDS', 1024), ('MAX_QUARANTINE_BODY_BYTES', 8 * 1024 * 1024),
                ('MAX_QUARANTINE_OBJECTS', 1024), ('MAX_DIAGNOSTIC_COUNTER', 2**31 - 1)]:
            self.assertEqual(getattr(module, name), expected)
        audit = self.queued(module, store)
        attempt = audit['attempt_id']
        def diagnostic(owner, dispatch, key, now):
            return owner.quarantine_submission(None, attempt, dispatch, reason='wrong_scope', content=key, now=now)
        for n in range(8):
            diagnostic(store, audit['dispatch_id'], 'retained-' + str(n), 100 + n)
        first = diagnostic(store, audit['dispatch_id'], 'overflow-A', 200)
        self.assertEqual((first['kind'], first['counter']), ('dispatch_overflow', 1))
        before = self.files(store)
        self.assertEqual(diagnostic(store, audit['dispatch_id'], 'overflow-A', 999), first)
        self.assertEqual(self.files(store), before)
        self.assertEqual(diagnostic(store, audit['dispatch_id'], 'overflow-B', 201)['counter'], 2)
        self.assertEqual(diagnostic(store, audit['dispatch_id'], 'overflow-A', 202)['counter'], 3)
        self.assertEqual(next(row for row in store.diagnostics()['rows']
            if row['kind'] == 'dispatch_overflow' and row['dispatch_id'] == audit['dispatch_id'])['counter'], 3)
        # These details were deliberately unattached (request_id=None).
        self.assertEqual(store.request_diagnostics(audit['request_id'])['overflow_count'], 0)
        self.assertEqual(store.get_request(audit['request_id'])['state'], 'queued')
        _, oversized_body = self.owner('oversized-body')
        too_large = 'x' * (512 * 1024 + 1)
        oversized_result = diagnostic(oversized_body, uuid.uuid4().hex, too_large, 200)
        self.assertTrue(oversized_result['not_retained'])
        self.assertEqual(oversized_result['byte_count'], len(too_large))
        self.assertEqual(oversized_result['sha256'], hashlib.sha256(too_large.encode()).hexdigest())
        self.assertEqual(list((oversized_body.path.parent / 'quarantine').glob('*.txt')), [])
        _, grouped = self.owner('group-limit')
        for n in range(256):
            diagnostic(grouped, uuid.uuid4().hex, None, 100 + n)
        overflow = diagnostic(grouped, uuid.uuid4().hex, None, 1000)
        self.assertEqual(overflow['kind'], 'store_overflow')
        self.assertEqual(grouped.diagnostics()['dispatch_group_count'], 256)
        _, total = self.owner('detail-limit')
        for group in range(128):
            dispatch = uuid.uuid4().hex
            for n in range(8):
                diagnostic(total, dispatch, str(n), 100 + group * 8 + n)
        self.assertEqual(diagnostic(total, uuid.uuid4().hex, None, 2000)['kind'], 'store_overflow')
        self.assertEqual(total.diagnostics()['detailed_count'], 1024)
        self.assertEqual(total.diagnostics()['dispatch_group_count'], 128)
        _, bodies = self.owner('body-limit')
        for n in range(16):
            row = diagnostic(bodies, uuid.uuid4().hex, chr(65 + n) * (512 * 1024), 100 + n)
            self.assertFalse(row['not_retained'])
        self.assertEqual(bodies.diagnostics()['retained_body_bytes'], 8 * 1024 * 1024)
        self.assertTrue(diagnostic(bodies, uuid.uuid4().hex, 'one more byte', 200)['not_retained'])
        _, orphans = self.owner('orphan-byte-budget')
        orphan_dir = orphans.path.parent / 'quarantine'
        orphan_dir.mkdir(parents=True)
        for _ in range(16):
            (orphan_dir / (uuid.uuid4().hex + '.txt')).write_bytes(b'x' * (512 * 1024))
        self.assertTrue(diagnostic(orphans, uuid.uuid4().hex, 'must not exceed orphan budget', 200)['not_retained'])
        _, objects = self.owner('orphan-object-budget')
        object_dir = objects.path.parent / 'quarantine'
        object_dir.mkdir(parents=True)
        for _ in range(1024):
            (object_dir / (uuid.uuid4().hex + '.txt')).write_bytes(b'x')
        self.assertTrue(diagnostic(objects, uuid.uuid4().hex, 'must not exceed orphan count', 200)['not_retained'])
        self.assertEqual(len(list(object_dir.glob('*.txt'))), 1024)

    def test_object_corruption_is_scoped_while_bad_index_holds_unknown_reads_without_reset(self):
        module, store = self.owner()
        audit = self.queued(module, store)
        version = self.commit(store, audit)
        path = self.root / 'artifacts/objects' / (version['id'] + '.md')
        path.write_bytes(b'corrupt object bytes')
        with self.assertRaises(module.ArtifactUnavailable):
            store.get_version(version['id'])
        peer = self.queued(module, store, channel='peer')
        self.assertEqual(store.get_request(peer['request_id'])['state'], 'queued')
        packet_path = self.root / 'artifact_briefs/packets' / (peer['scope']['packet_id'] + '.json')
        packet_path.write_bytes(b'{broken packet')
        with self.assertRaises(module.ArtifactUnavailable):
            store.get_packet(peer['scope']['packet_id'])
        with self.assertRaises(module.ArtifactUnavailable):
            store.set_attempt_state(peer['request_id'], peer['attempt_id'], 'queued', {'state': 'active', 'reason': None})
        diagnostic = store.quarantine_submission(peer['request_id'], peer['attempt_id'], peer['dispatch_id'],
            reason='source_packet_unavailable', now=100)
        self.assertIn(diagnostic['id'], store.request_diagnostics(peer['request_id'])['quarantine_ids'])
        self.assertEqual(store.set_attempt_state(peer['request_id'], peer['attempt_id'], 'queued',
            {'state': 'failed', 'reason': 'source_packet_unavailable'}, now=101)['state'], 'failed')
        healthy_index = store.path.read_bytes()
        formatted = json.dumps(json.loads(healthy_index), ensure_ascii=False, indent=4).encode('utf-8')
        store.path.write_bytes(formatted)
        self.assertEqual(store.get_request(audit['request_id'])['state'], 'fulfilled')
        self.assertEqual(store.path.read_bytes(), formatted)
        for broken in (b'{broken index', b'[]', b'{}', b'{"version":1,"version":1}', b'{"x":NaN}', b'\xff'):
            with self.subTest(broken=broken):
                store.path.write_bytes(broken)
                with self.assertRaises(module.ArtifactUnavailable):
                    module.ArtifactStore(self.root)
                held = module.ArtifactStore(self.root, hold_unreadable=True)
                with self.assertRaises(module.ArtifactUnavailable):
                    held.get_request(uuid.uuid4().hex)
                with self.assertRaises(module.ArtifactUnavailable):
                    held.list_lineages()
                self.assertEqual(store.path.read_bytes(), broken)
        store.path.write_bytes(healthy_index)
        original_open = Path.open
        def unavailable(path, *args, **kwargs):
            if path == store.path:
                raise OSError('private local index read failure')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', unavailable), self.assertRaises(module.ArtifactUnavailable):
            module.ArtifactStore(self.root)
        self.assertEqual(store.path.read_bytes(), healthy_index)

    def test_detached_metadata_reload_staged_rename_inactive_replay_and_low_level_settlement(self):
        module = importlib.import_module('artifact_store')
        self.assertTrue(issubclass(module.ArtifactValidationError, ValueError))
        self.assertTrue(issubclass(module.ArtifactConflict, ChannelConflict))
        self.assertTrue(issubclass(module.ArtifactUnavailable, ChannelUnavailable))
        before_constructor = {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        store = module.ArtifactStore(self.root)
        self.assertFalse(store.path.exists())
        self.assertEqual({path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}, before_constructor)
        with self.assertRaises(module.ArtifactUnavailable):
            store.put_packet(uuid.uuid4().hex, self.packet())
        store.bind_channel_policy(lambda: self.service)
        audit = self.queued(module, store)
        version = self.commit(store, audit, '# Exact\r\ncontent', now=30)
        pending = self.queued(module, store, parent={'version_id': version['id'], 'sequence': 1, 'sha256': version['sha256']}, lineage_id=audit['lineage_id'])
        unreserved = self.audit(module, store)
        before_audit = deepcopy(store.get_request(pending['request_id'])['audit'])
        immutable = {path: path.read_bytes() for path in (self.root / 'artifact_briefs').rglob('*.json')}
        immutable.update({path: path.read_bytes() for path in (self.root / 'artifacts/objects').glob('*.md')})
        request = store.get_request_by_dispatch(pending['dispatch_id'])
        request['audit']['producer']['name'] = 'outside'
        self.assertEqual(store.get_request(pending['request_id'])['audit'], before_audit)
        original_open = Path.open
        def no_bodies(path, *args, **kwargs):
            if path.suffix == '.md' or 'packets' in path.parts:
                raise AssertionError('Metadata read copied an immutable body')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', no_bodies):
            versions = store.list_versions(audit['lineage_id'], limit=1)
            self.assertEqual(versions['count'], 1)
            self.assertNotIn('markdown', versions['rows'][0])
            self.assertEqual(store.retained_metadata('review')['count'], 1)
            self.assertEqual(store.lifecycle_scope('review')['version_count'], 1)
            self.assertEqual(store.get_request_by_dispatch(pending['dispatch_id'])['state'], 'queued')
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.files(store)
        self.assertEqual(store.reserve_request({**before_audit, 'created_at': 999}, pending['request_id'])['state'], 'queued')
        self.assertEqual(self.commit(store, audit, '# Exact\r\ncontent', now=999), version)
        self.assertEqual(self.files(store), before)
        with self.assertRaises(ChannelInactive):
            store.reserve_request(unreserved, unreserved['request_id'])
        with self.assertRaises(ChannelInactive):
            self.commit(store, pending, 'Ordinary new commit stays blocked')
        self.assertEqual(self.files(store), before)
        new_request = uuid.uuid4().hex
        with self.assertRaises(ChannelInactive):
            store.put_packet(new_request, self.packet())
        store.set_attempt_state(pending['request_id'], pending['attempt_id'], 'queued',
            {'state': 'cancelled', 'reason': 'operator_cancelled'}, now=50)
        store.rename_channel('review', 'renamed')
        self.assertEqual(store.channel_names(), {'renamed'})
        self.assertEqual(store.get_request(pending['request_id'])['channel'], 'renamed')
        self.assertEqual(store.get_request(pending['request_id'])['audit'], before_audit)
        self.assertEqual(store.get_version(version['id'])['metadata']['channel'], 'renamed')
        for path, raw in immutable.items():
            self.assertEqual(path.read_bytes(), raw)
        restored = module.ArtifactStore(self.root)
        self.assertEqual(restored.list_lineages(), store.list_lineages())
        before = restored.path.read_bytes()
        restored.rename_channel('review', 'renamed')
        self.assertEqual(restored.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
