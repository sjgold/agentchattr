"""Readonly selected CLI message inspection with real stores and process doubles."""
import hashlib
import json
from copy import deepcopy
import unittest
import uuid

from store import MessageStore
from turn_events import EventConflict, EventValidationError
from tests import test_result_owner_wiring as fixture


class CliMessageCandidateTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.cli, self.launch = self.fixture.ready('cli')
        self.run = fixture.ResultOwnerWiringTests.start(self, self.cli['name'])

    def source(self, text='Exact café\r\n@all `code`', **kwargs):
        invocation = self.run['active_invocation']
        return self.engine.send_chat(self.cli, text, dispatch_id=invocation['dispatch_id'],
                                     channel=self.run['channel'], **kwargs)

    def inspect(self, message):
        return self.engine.cli_message_candidate(self.run['id'], message['id'])

    def raw_source(self, metadata=None, **fields):
        values = dict(sender=self.cli['name'], text='Exact selected output', channel=self.run['channel'],
                      metadata={'seat_identity_id': self.cli['identity_id']} if metadata is None else metadata)
        values.update(fields)
        return self.messages.add(**values)

    def update_run(self, **fields):
        self.sessions._event_update(self.run['id'], lambda value: value.update(deepcopy(fields)))

    def restore_run(self, baseline):
        def replace(value):
            value.clear()
            value.update(deepcopy(baseline))
        self.sessions._event_update(self.run['id'], replace)

    def test_authenticated_source_returns_exact_text_hash_and_current_checkpoint(self):
        message = self.source()
        snapshot = self.messages.get_snapshot(message['id'])
        expected_hash = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
        result = self.engine.cli_message_candidate(self.run['id'], message['id'])
        self.assertEqual(result['snapshot_hash'], expected_hash)
        self.assertEqual(result['text'], snapshot['text'])
        self.assertEqual(result['message_uid'], snapshot['uid'])
        self.assertEqual(result['created_at'], snapshot['timestamp'])
        self.assertEqual(result['attribution'], 'machine_verified')
        self.assertFalse(result['requires_operator_confirmation'])
        self.assertEqual(result['source_attempt_id'], self.run['active_invocation']['attempt_id'])
        self.assertEqual(result['checkpoint'], dict(session_id=self.run['id'], run_id=self.run['run_id'],
            **{key: self.run['active_invocation'][key] for key in ('turn_id', 'attempt_id', 'input_revision')}))

    def test_inspection_has_no_store_queue_process_or_source_side_effects(self):
        message = self.source()
        files = {path: path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()}
        spawns = self.fixture.spawn.call_count
        first = self.engine.cli_message_candidate(self.run['id'], message['id'])
        first['checkpoint']['attempt_id'] = 'mutated-copy'
        second = self.engine.cli_message_candidate(self.run['id'], message['id'])
        self.assertEqual(second['checkpoint']['attempt_id'], self.run['active_invocation']['attempt_id'])
        self.assertEqual(self.fixture.spawn.call_count, spawns)
        self.assertEqual(files, {path: path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()})
        self.assertEqual(second['available_kinds'], ['final', 'question'])
        self.assertTrue(second['eligible'])
        self.assertEqual(set(second), {'session_id', 'message_id', 'message_uid', 'sender', 'channel',
            'created_at', 'text', 'snapshot_hash', 'eligible', 'attribution',
            'requires_operator_confirmation', 'available_kinds', 'source_attempt_id', 'checkpoint'})

    def test_legacy_id_zero_without_uid_uses_deterministic_full_snapshot_hash_readonly(self):
        path = self.fixture.root / 'legacy.jsonl'
        legacy = dict(id=0, sender=self.cli['name'], text='Legacy café\r\nsource', type='chat',
                      channel=self.run['channel'], timestamp=123.5,
                      metadata={'seat_identity_id': self.cli['identity_id']}, attachments=[{'nested': ['x']}])
        path.write_text(json.dumps(legacy, ensure_ascii=False) + '\n', encoding='utf-8')
        self.engine._messages = MessageStore(str(path))
        before = path.read_bytes()
        digest = hashlib.sha256(json.dumps(legacy, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
        result = self.engine.cli_message_candidate(self.run['id'], 0)
        self.assertEqual(result['message_uid'], 'legacy-0-' + digest[:16])
        self.assertEqual(result['snapshot_hash'], digest)
        self.assertEqual(result['attribution'], 'operator_attributed')
        self.assertTrue(result['requires_operator_confirmation'])
        self.assertIsNone(result['source_attempt_id'])
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn('uid', self.engine._messages.get_snapshot(0))
        for uid in (None, '', 0, True, ['malformed'], {'malformed': 'uid'}):
            with self.subTest(uid=uid):
                stored = dict(legacy, uid=uid)
                path.write_text(json.dumps(stored, ensure_ascii=False) + '\n', encoding='utf-8')
                before = path.read_bytes()
                self.engine._messages = MessageStore(str(path))
                if uid is None or uid == '':
                    digest = hashlib.sha256(json.dumps(stored, ensure_ascii=False, sort_keys=True,
                        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
                    result = self.engine.cli_message_candidate(self.run['id'], 0)
                    self.assertEqual(result['message_uid'], 'legacy-0-' + digest[:16])
                    self.assertEqual(result['snapshot_hash'], digest)
                else:
                    with self.assertRaises(EventConflict):
                        self.engine.cli_message_candidate(self.run['id'], 0)
                self.assertEqual(path.read_bytes(), before)

    def test_literal_id_validation_and_missing_records(self):
        message = self.source()
        for bad in (True, False, '1', 1.0, None, -1, [], {}):
            with self.subTest(session=bad), self.assertRaises(EventValidationError):
                self.engine.cli_message_candidate(bad, message['id'])
            with self.subTest(message=bad), self.assertRaises(EventValidationError):
                self.engine.cli_message_candidate(self.run['id'], bad)
        with self.assertRaises(EventValidationError):
            self.engine.cli_message_candidate(0, message['id'])
        for session_id, message_id in ((99999, message['id']), (self.run['id'], 99999)):
            with self.assertRaises(EventConflict):
                self.engine.cli_message_candidate(session_id, message_id)

    def test_same_name_wrong_or_missing_identity_and_wrong_channel_never_authorize(self):
        for metadata in ({}, {'seat_identity_id': uuid.uuid4().hex}, {'seat_identity_id': ''}):
            with self.subTest(metadata=metadata), self.assertRaises(EventConflict):
                self.inspect(self.raw_source(metadata=metadata))
        with self.assertRaises(EventConflict):
            self.inspect(self.raw_source(channel='other-channel'))
        # Renamed display text does not erase authenticated stable identity.
        historical = self.raw_source(sender='historical-display-name')
        # The live human-interruption callback pauses an unknown display name.
        # Restore the inspection-eligible run to model a stored historical name.
        self.update_run(state='waiting')
        result = self.inspect(historical)
        self.assertEqual(result['attribution'], 'operator_attributed')

    def test_each_present_scope_tag_must_match_and_partial_tags_require_confirmation(self):
        full = self.messages.get_snapshot(self.source()['id'])['metadata']
        for key in ('run_id', 'turn_id', 'attempt_id', 'dispatch_id', 'input_revision'):
            bad = dict(full, **{key: uuid.uuid4().hex})
            with self.subTest(key=key), self.assertRaises(EventConflict):
                self.inspect(self.raw_source(metadata=bad))
            partial = dict(full)
            del partial[key]
            result = self.inspect(self.raw_source(metadata=partial))
            self.assertEqual(result['attribution'], 'operator_attributed')
            self.assertTrue(result['requires_operator_confirmation'])
            self.assertIsNone(result['source_attempt_id'])

    def test_import_quarantine_unknown_provenance_and_nonchat_rejected(self):
        identity = {'seat_identity_id': self.cli['identity_id']}
        for extra in ({'imported': True}, {'routing_suppressed': True}, {'quarantine_session_id': 1},
                      {'provenance': 'unverified_scope'}, {'provenance': 'invented-authentication'}):
            with self.subTest(extra=extra), self.assertRaises(EventConflict):
                self.inspect(self.raw_source(metadata=dict(identity, **extra)))
        for kind in ('session_result', 'session_question', 'system', 'quarantine', 'decision'):
            with self.subTest(kind=kind), self.assertRaises(EventConflict):
                self.inspect(self.raw_source(msg_type=kind))

    def test_text_limits_are_utf8_bytes_and_invalid_text_is_not_clipped(self):
        for text in ('', '  \r\n', 'embedded\0nul', 'é' * (256 * 1024 + 1)):
            with self.subTest(length=len(text)), self.assertRaises((EventValidationError, EventConflict)):
                self.inspect(self.raw_source(text=text))
        exact = 'é' * (256 * 1024)
        self.assertEqual(self.inspect(self.raw_source(text=exact))['text'], exact)
        path = self.fixture.root / 'invalid-unicode.jsonl'
        message = self.messages.get_snapshot(self.raw_source()['id'])
        message['text'] = '\ud800'
        path.write_text(json.dumps(message) + '\n', encoding='utf-8')
        self.engine._messages = MessageStore(str(path))
        with self.assertRaises((EventValidationError, EventConflict)):
            self.inspect(message)

    def test_interrupted_stalled_and_dispatch_ineligible_remain_inspectable_but_fences_deny(self):
        message = self.source()
        for state in ('active', 'waiting', 'stalled', 'interrupted'):
            self.update_run(state=state, dispatch_eligible=False)
            self.assertTrue(self.inspect(message)['eligible'])
        baseline = self.sessions.get(self.run['id'])
        for fields in ({'stop_id': uuid.uuid4().hex}, {'pending_retry': {'request_id': uuid.uuid4().hex}},
                       {'replaced_by_run_id': uuid.uuid4().hex}, {'state': 'completed'},
                       {'state': 'awaiting_input'}, {'state': 'prepared'},
                       {'active_invocation': dict(baseline['active_invocation'], consumed=True)}):
            self.restore_run(baseline)
            self.update_run(**fields)
            with self.subTest(fields=list(fields)), self.assertRaises(EventConflict):
                self.inspect(message)

    def test_only_frozen_managed_cli_binding_and_protocol_one_qualify(self):
        message = self.source()
        baseline = self.sessions.get(self.run['id'])
        for change in ('api', 'unmanaged', 'human', 'legacy'):
            modified = deepcopy(baseline)
            binding = modified['participant_bindings']['reader']
            if change == 'api':
                binding['launch_provenance']['effective']['seat']['adapter'] = 'openai-compatible'
            elif change == 'unmanaged':
                binding.pop('launch_provenance')
            elif change == 'human':
                binding['kind'] = 'human'
            else:
                modified['completion_protocol'] = 0
            self.update_run(**modified)
            with self.subTest(change=change), self.assertRaises(EventConflict):
                self.inspect(message)

    def test_retained_same_turn_history_can_attribute_old_identity_without_mixing_lineages(self):
        # Boundary fixture: retained Retry history, not a native relaunch/proof claim.
        old = self.run['active_invocation']
        message = self.source()
        newer = dict(old, attempt_id=uuid.uuid4().hex, dispatch_id=uuid.uuid4().hex,
                     brief_id=uuid.uuid4().hex, expected_identity_id=uuid.uuid4().hex)
        historical = {key: old[key] for key in ('attempt_id', 'dispatch_id', 'turn_id', 'run_id',
                                               'input_revision', 'expected_identity_id')}
        binding = deepcopy(self.run['participant_bindings'])
        binding['reader']['identity_id'] = newer['expected_identity_id']
        binding['reader']['launch_provenance']['identity_id'] = newer['expected_identity_id']
        self.update_run(active_invocation=newer, participant_bindings=binding, superseded_attempts=[historical])
        self.fixture.registry.deregister(self.cli['name'])
        result = self.inspect(message)
        self.assertEqual(result['source_attempt_id'], old['attempt_id'])
        self.assertEqual(result['checkpoint']['attempt_id'], newer['attempt_id'])
        tags = self.messages.get_snapshot(message['id'])['metadata']
        for patch in ({'dispatch_id': newer['dispatch_id']}, {'input_revision': uuid.uuid4().hex},
                      {'run_id': uuid.uuid4().hex}):
            with self.subTest(patch=patch), self.assertRaises(EventConflict):
                self.inspect(self.raw_source(metadata=dict(tags, **patch)))

    def test_consumed_uid_is_global_even_when_numeric_id_changes_but_other_uid_is_not_consumed(self):
        message = self.source()
        other = fixture.ResultOwnerWiringTests.start(self, self.cli['name'], 'other-review')
        # Retained accepted-history boundary; no selected-event admission API in this tranche.
        self.sessions._event_update(other['id'], lambda value: value['admitted_events'].append({
            'event_id': uuid.uuid4().hex, 'source_message_uid': message['uid'],
            'source_message_id': 99999, 'kind': 'final', 'content': 'Already copied result'}))
        duplicate = self.raw_source(uid=message['uid'])
        self.assertNotEqual(duplicate['id'], message['id'])
        for source in (message, duplicate):
            with self.subTest(id=source['id']), self.assertRaises(EventConflict):
                self.inspect(source)
        self.assertTrue(self.inspect(self.raw_source(uid='independent-source-uid'))['eligible'])
