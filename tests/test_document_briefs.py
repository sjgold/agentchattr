"""Document snapshot threading with real stores, without native/provider claims."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

from agents import AgentTrigger
from document_inputs import preview_document
from registry import RuntimeRegistry
import review_brief
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from tests import test_review_brief as brief_fixture
from tests import test_result_owner_wiring as managed_fixture
from tests import test_participant_replacement_store as replacement_fixture


class DocumentBriefTests(unittest.TestCase):
    def setUp(self):
        self.document = preview_document('source.py', '\ufeffExact café 日本語 😀 e\u0301\r\n@all\nprint("literal")'.encode('utf-8'))
        self.metadata = {key: value for key, value in self.document.items() if key != 'text'}
        scratch = Path(__file__).resolve().parents[1] / '.audit-tmp'
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.sessions = SessionStore(str(self.root / 'session_runs.json'))
        self.sessions.save_custom_template(brief_fixture.design())

    def test_freeze_inputs_threads_exact_document_metadata_and_revision(self):
        frozen = review_brief.freeze_inputs(brief_fixture.design(), source_file=self.document)
        self.assertEqual(frozen['input_snapshot'], {'text': self.document['text'],
            'revision': self.document['content_sha256'], 'encoding': 'utf-8', 'document': self.metadata})
        self.assertEqual(frozen['input_revision'], self.document['content_sha256'])

    def test_real_session_create_persists_file_source_without_paste_fallback(self):
        run = self.sessions.create('custom-review', 'general', {'reviewer': 'codex', 'editor': 'claude'},
                                   'operator', source_file=self.document)
        self.assertEqual(run['input_snapshot']['document'], self.metadata)
        self.assertEqual(run['input_snapshot']['text'], self.document['text'])
        self.assertEqual(SessionStore(str(self.sessions._path)).get(run['id']), run)

    def frozen(self):
        return {**review_brief.freeze_inputs(brief_fixture.design(), rules=brief_fixture.RULES,
                    source_file=self.document), 'id': 7, 'channel': 'review',
                'cast': {'reviewer': 'codex', 'editor': 'claude'}}

    def envelope(self):
        return review_brief.build_brief(self.frozen(), 0, 0, 'codex', identity_id='identity-one')

    def runtime(self):
        registry = RuntimeRegistry(str(self.root))
        registry.seed({'codex': {'type': 'cli'}, 'claude': {'type': 'api'}})
        owner, peer = registry.register('codex'), registry.register('claude')
        messages = MessageStore(str(self.root / 'messages.jsonl'))
        trigger = AgentTrigger(registry, str(self.root))
        engine = SessionEngine(self.sessions, messages, trigger, registry)
        return engine, messages, trigger, owner, peer

    def files(self):
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}

    def test_legacy_pasted_snapshot_and_old_brief_stay_document_free(self):
        frozen = review_brief.freeze_inputs(brief_fixture.design(), input_text='Pasted café\r\nsource')
        self.assertEqual(set(frozen['input_snapshot']), {'text', 'revision', 'encoding'})
        self.assertEqual(frozen['input_revision'], hashlib.sha256(b'Pasted caf\xc3\xa9\r\nsource').hexdigest())
        session = {**frozen, 'id': 8, 'channel': 'general'}
        envelope = review_brief.build_brief(session, 0, 0, 'codex', identity_id='identity-one')
        self.assertNotIn('source_document', envelope)
        pasted = self.sessions.create('custom-review', 'legacy-paste',
            {'reviewer': 'codex', 'editor': 'claude'}, 'operator', input_text='Pasted café\r\nsource')
        reloaded = SessionStore(str(self.sessions._path)).get(pasted['id'])
        self.assertEqual(reloaded['input_snapshot'], frozen['input_snapshot'])
        self.assertEqual(set(reloaded['input_snapshot']), {'text', 'revision', 'encoding'})
        self.assertEqual(reloaded['input_snapshot']['text'], 'Pasted café\r\nsource')
        reloaded_brief = review_brief.build_brief(reloaded, 0, 0, 'codex', identity_id='identity-one')
        self.assertNotIn('source_document', reloaded_brief)
        self.sessions.briefs.put(envelope)
        before = self.files()
        self.assertEqual(self.sessions.briefs.get(envelope['brief_id'], operator=True), envelope)
        self.assertEqual(self.files(), before)

    def test_untrusted_packet_retains_selected_snapshot_after_local_file_edit_delete_and_chat_growth(self):
        path = self.root / 'source.py'
        original = self.document['text'].encode('utf-8')
        path.write_bytes(original)
        selected = preview_document(path.name, path.read_bytes())
        path.write_text('Different source, not the selection', encoding='utf-8')
        path.unlink()
        frozen = review_brief.freeze_inputs(brief_fixture.design(), source_file=selected)
        envelope = review_brief.build_brief({**frozen, 'id': 4, 'channel': 'review'}, 0, 0, 'codex', 'identity-one')
        recent = [{'id': i, 'sender': 'human', 'text': 'Unrelated chat ' + str(i)} for i in range(30)]
        messages = review_brief.brief_messages(envelope, recent[-20:], 'codex', 'System instruction')
        packet = next(json.loads(m['content']) for m in messages if m['role'] == 'user'
            and json.loads(m['content']).get('kind') == 'untrusted_review_source')
        self.assertEqual(packet['text'].encode('utf-8'), original)
        self.assertEqual(packet['source_document'], self.metadata)
        self.assertEqual(packet['input_revision'], self.document['content_sha256'])
        self.assertNotIn('source_document', messages[0]['content'])
        self.assertNotIn(self.document['name'], messages[0]['content'])

    def test_metadata_key_presence_tamper_and_extra_fields_fail_closed_before_brief_build(self):
        invalid = [None, [], {}, {**self.metadata, 'text': self.document['text']},
                   {**self.metadata, 'path': 'forged'}, {**self.metadata, 'byte_length': 0},
                   {**self.metadata, 'content_sha256': '0' * 64}]
        for metadata in invalid:
            session = self.frozen()
            session['input_snapshot']['document'] = metadata
            before = deepcopy(session)
            with self.subTest(metadata=metadata), self.assertRaises(review_brief.BriefError):
                review_brief.build_brief(session, 0, 0, 'codex', 'identity-one')
            self.assertEqual(session, before)

    def test_brief_store_revalidates_document_on_put_and_read_without_repair(self):
        envelope = self.envelope()
        self.sessions.briefs.put(envelope)
        path = self.sessions.briefs.path / (envelope['brief_id'] + '.json')
        original = path.read_bytes()
        for metadata in (None, {**self.metadata, 'text': self.document['text']},
                         {**self.metadata, 'content_sha256': '0' * 64}):
            changed = {**envelope, 'source_document': metadata}
            path.write_text(json.dumps(changed, ensure_ascii=False), encoding='utf-8')
            before = path.read_bytes()
            with self.subTest(metadata=metadata), self.assertRaises(review_brief.BriefError):
                self.sessions.briefs.get(envelope['brief_id'], operator=True)
            self.assertEqual(path.read_bytes(), before)
            invalid_new = {**changed, 'brief_id': uuid.uuid4().hex}
            with self.assertRaises(review_brief.BriefError):
                self.sessions.briefs.put(invalid_new)
            self.assertFalse((self.sessions.briefs.path / (invalid_new['brief_id'] + '.json')).exists())
        path.write_bytes(original)
        restored = self.sessions.briefs.get(envelope['brief_id'], operator=True)
        restored['source_document']['name'] = 'local copy edit'
        self.assertEqual(self.sessions.briefs.get(envelope['brief_id'], operator=True)['source_document'], self.metadata)

    def test_invalid_create_consumes_no_id_and_engine_has_no_binding_or_dispatch_effect(self):
        engine, messages, trigger, owner, peer = self.runtime()
        before, next_id = self.files(), self.sessions._next_id
        callbacks = Mock()
        self.sessions.on_change(callbacks)
        invalid = {**self.document, 'content_sha256': '0' * 64}
        with self.assertRaises(review_brief.BriefError):
            self.sessions.create('custom-review', 'invalid', {'reviewer': owner['name'], 'editor': peer['name']},
                'operator', source_file=invalid)
        self.assertEqual(self.sessions._next_id, next_id)
        self.assertEqual(self.files(), before)
        with patch.object(engine._registry, 'get_instance', side_effect=AssertionError('No binding inspection')):
            try:
                result = engine.start_session('custom-review', 'invalid',
                    {'reviewer': owner['name'], 'editor': peer['name']}, 'operator', source_file=invalid)
            except review_brief.BriefError:
                result = None
        self.assertIsNone(result)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.sessions._next_id, next_id)
        callbacks.assert_not_called()
        valid = self.sessions.create('custom-review', 'valid', {'reviewer': 'codex', 'editor': 'claude'},
            'operator', source_file=self.document)
        self.assertEqual(valid['id'], next_id)

    def test_internal_file_and_nonempty_or_nonstring_paste_reject_without_effects(self):
        before = self.files()
        for pasted in ('Nonempty pasted source', None, 0, False, b'bytes'):
            for call in (
                lambda: review_brief.freeze_inputs(brief_fixture.design(), input_text=pasted, source_file=self.document),
                lambda: self.sessions.create('custom-review', 'conflict', {'reviewer': 'codex', 'editor': 'claude'},
                    'operator', input_text=pasted, source_file=self.document),
            ):
                with self.subTest(pasted=repr(pasted)), self.assertRaises(review_brief.BriefError):
                    call()
                self.assertEqual(self.files(), before)

    def test_real_cli_scoped_brief_and_typed_final_preserve_file_revision_after_thirty_messages(self):
        case = managed_fixture.ResultOwnerWiringTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        owner, _ = case.fixture.ready('cli')  # Process double only, no native worker proof.
        run = case.engine.start_session('seal-test', 'file-cli', {'reader': owner['name']}, 'operator', source_file=self.document)
        original = deepcopy(run['input_snapshot'])
        for i in range(30):
            case.messages.add('human', 'Later unrelated message ' + str(i))
        invocation = run['active_invocation']
        brief = case.sessions.briefs.get(invocation['brief_id'], owner)
        api_packet = review_brief.brief_messages(brief, case.messages.get_recent(20), owner['name'])
        packet = next(json.loads(m['content']) for m in api_packet if m['role'] == 'user'
            and json.loads(m['content']).get('kind') == 'untrusted_review_source')
        self.assertEqual((brief['source'], brief['source_document']), (packet['text'], packet['source_document']))
        self.assertEqual(brief['source'], self.document['text'])
        self.assertEqual(brief['source_document'], self.metadata)
        self.assertNotIn('seal_secret', case.sessions.briefs.get_delivery(invocation['brief_id'], owner))
        case.engine.admit_event(invocation['brief_id'], 'final', 'Authentic file review', owner)
        current = case.sessions.get(run['id'])
        self.assertEqual(current['state'], 'complete')
        self.assertEqual(current['input_snapshot'], original)
        self.assertEqual(current['admitted_events'][0]['input_revision'], self.document['content_sha256'])

    def test_retry_brief_reuses_exact_document_source_with_new_attempt_and_same_turn(self):
        engine, messages, trigger, owner, peer = self.runtime()
        run = engine.start_session('custom-review', 'file-retry',
            {'reviewer': owner['name'], 'editor': peer['name']}, 'operator', source_file=self.document)
        invocation = deepcopy(run['active_invocation'])
        queue = engine._trigger.queue
        queue.claim(owner, 'worker')
        queue.acknowledge(owner, invocation['dispatch_id'], 'worker')
        queue.release(owner, invocation['dispatch_id'], 'worker', failed=True, error='provider_failure')
        engine.monitor_turns()
        current = self.sessions.get(run['id'])
        self.assertEqual(current['state'], 'stalled')
        engine.retry_turn(run['id'], current['turn_recovery']['checkpoint_id'], invocation['attempt_id'], uuid.uuid4().hex)
        retried = self.sessions.get(run['id'])
        fresh = retried['active_invocation']
        self.assertNotEqual(fresh['attempt_id'], invocation['attempt_id'])
        self.assertEqual(fresh['turn_id'], invocation['turn_id'])
        brief = self.sessions.briefs.get(fresh['brief_id'], owner)
        self.assertEqual((brief['source'], brief['source_document'], brief['input_revision']),
                         (self.document['text'], self.metadata, self.document['content_sha256']))
        self.assertEqual(retried['input_snapshot'], run['input_snapshot'])

    def test_managed_api_private_seal_and_identity_gates_remain_bound_to_file_brief(self):
        from result_outbox import seal_result
        case = managed_fixture.ResultOwnerWiringTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        owner, _ = case.fixture.ready('api')  # Nonnative managed process double.
        run = case.engine.start_session('seal-test', 'file-api', {'reader': owner['name']}, 'operator', source_file=self.document)
        invocation = run['active_invocation']
        delivery = case.sessions.briefs.get_delivery(invocation['brief_id'], owner)
        public = case.sessions.briefs.get(invocation['brief_id'], owner)
        self.assertEqual(delivery['source_document'], self.metadata)
        self.assertEqual(delivery['result_owner'], case.fixture.manager.result_owner(owner, invocation['dispatch_id']))
        self.assertNotIn(delivery['seal_secret'], json.dumps(run))
        self.assertNotIn('seal_secret', public)
        with self.assertRaises(review_brief.BriefAccessError):
            case.sessions.briefs.get_delivery(invocation['brief_id'], {'name': owner['name'], 'identity_id': uuid.uuid4().hex})
        payload = {'version': 1, 'result_id': invocation['dispatch_id'], 'dispatch_id': invocation['dispatch_id'],
            'event_id': invocation['dispatch_id'], **{key: delivery[key] for key in
                ('session_id', 'brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')},
            **{key: delivery['result_owner'][key] for key in ('seat_identity_id', 'launch_attempt', 'launch_nonce', 'fingerprint')},
            'kind': 'final', 'content': 'Saved file review', 'created_at': time.time()}
        self.assertEqual(case.sessions.briefs.verify_saved_result(seal_result(payload, delivery['seal_secret'])), payload)
        wrong_owner = {**payload, 'seat_identity_id': uuid.uuid4().hex}
        with self.assertRaises(review_brief.BriefError):
            case.sessions.briefs.verify_saved_result(seal_result(wrong_owner, delivery['seal_secret']))
        case.engine.admit_event(invocation['brief_id'], 'final', 'File API typed final', owner)
        self.assertEqual(case.sessions.get(run['id'])['input_snapshot']['document'], self.metadata)

    def test_participant_replacement_brief_reuses_file_snapshot_and_immutable_prior(self):
        case = replacement_fixture.ParticipantReplacementStoreTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.engine.stop_session(case.run['id'])  # Retire unrelated setup occupancy explicitly.
        run = case.engine.start_session('replace-store', 'file-replace',
            {'reader': case.source['name'], 'editor': case.old['name']}, 'operator', source_file=self.document)
        case.engine.admit_event(run['active_invocation']['brief_id'], 'final', 'FILE_IMMUTABLE_PRIOR', case.source)
        run = case.sessions.get(run['id'])
        dispatch = case.trigger.queue.owned(case.old, run['active_invocation']['dispatch_id'])
        case.engine.monitor_turns(now=dispatch['events'][0]['at'] + run['recovery_policy']['ack_timeout'] + .1)
        case.run = case.sessions.get(run['id'])
        decision = {'request_id': uuid.uuid4().hex, 'checkpoint_id': case.run['turn_recovery']['checkpoint_id'],
            'attempt_id': case.run['active_invocation']['attempt_id'], 'target_identity_id': case.source['identity_id'],
            'target_fingerprint': case.provenance['fingerprint'], 'reason': 'Preserve exact file source.'}
        case.engine.replace_participant(run['id'], decision)
        pending = case.sessions.get(run['id'])['pending_replacement']
        context, _ = case.clone(pending)  # Existing explicitly nonnative readiness/process seams.
        case.engine.replace_participant(run['id'], decision)
        current = case.sessions.get(run['id'])
        self.assertEqual(current['active_invocation']['expected_identity_id'], context['identity_id'])
        brief = case.sessions.briefs.get(current['active_invocation']['brief_id'], operator=True)
        self.assertEqual((brief['source'], brief['source_document'], brief['input_revision']),
                         (self.document['text'], self.metadata, self.document['content_sha256']))
        self.assertEqual(current['input_snapshot'], run['input_snapshot'])
        self.assertIn('FILE_IMMUTABLE_PRIOR', json.dumps(brief['prior_results']))


if __name__ == '__main__':
    unittest.main()
