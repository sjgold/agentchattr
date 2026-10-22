"""Explicit final/question admission with durable identity and projection fences."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import AgentTrigger
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore


class SessionEventTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'session_runs.json'
        self.sessions = SessionStore(str(self.path))
        self.template = {'id': 'review', 'name': 'Review', 'roles': ['reviewer', 'editor'],
                         'phases': [{'name': 'Review', 'participants': ['reviewer'], 'prompt': 'Review source.'},
                                    {'name': 'Edit', 'participants': ['editor'], 'prompt': 'Edit source.', 'is_output': True}]}
        self.sessions.save_custom_template(self.template)
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.registry = RuntimeRegistry(str(self.root))
        self.registry.seed({'codex': {'label': 'Codex'}, 'claude': {'label': 'Claude'}})
        self.owner = self.registry.register('codex')
        self.peer = self.registry.register('claude')
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        self.started = self.engine.start_session('review', 'general',
            {'reviewer': 'codex', 'editor': 'claude'}, 'human', goal='Explain the evidence.',
            input_text='Exact café source\r\n@all is source data.')
        self.session_id = self.started['id']

    def current(self):
        return self.sessions.get(self.session_id)

    def invocation(self):
        return self.current()['active_invocation']

    def admit(self, kind='final', content='Exact accepted result.', instance=None, **kwargs):
        return self.engine.admit_event(self.invocation()['brief_id'], kind, content,
                                       self.owner if instance is None else instance, **kwargs)

    def test_start_persists_bound_invocation_matching_immutable_brief_and_dispatch(self):
        self.assertEqual(self.started['completion_protocol'], 1)
        invocation = self.invocation()
        brief = self.sessions.briefs.get(invocation['brief_id'], self.owner)
        dispatch = self.trigger.queue.claim(self.owner, 'fixture-consumer')['envelope']
        for key in ('run_id', 'turn_id', 'attempt_id', 'input_revision', 'expected_identity_id'):
            self.assertEqual(invocation[key], brief[key])
        self.assertEqual(dispatch['dispatch_id'], invocation['dispatch_id'])
        self.assertEqual(dispatch['review_brief_id'], invocation['brief_id'])

    def test_ordinary_chat_decision_and_queue_release_never_advance(self):
        before = deepcopy(self.current())
        def immediate_timer(delay, callback, args):
            timer = Mock()
            timer.start.side_effect = lambda: callback(*args)
            return timer
        with patch('session_engine.threading.Timer', immediate_timer):
            self.messages.add('codex', 'Still working, this is status.')
            self.messages.add('codex', 'A question card', msg_type='decision', metadata={'choices': ['A', 'B']})
        dispatch = self.trigger.queue.claim(self.owner, 'fixture-consumer')
        self.trigger.queue.acknowledge(self.owner, dispatch['envelope']['dispatch_id'], 'fixture-consumer')
        self.trigger.queue.release(self.owner, dispatch['envelope']['dispatch_id'], 'fixture-consumer')
        after = self.current()
        self.assertEqual((after['current_phase'], after['current_turn']),
                         (before['current_phase'], before['current_turn']))
        self.assertNotEqual(after['state'], 'complete')

    def test_explicit_final_advances_once_and_journals_exact_content(self):
        held = self.trigger.queue.claim(self.owner, 'held-transport')
        dispatch_id = held['envelope']['dispatch_id']
        self.trigger.queue.acknowledge(self.owner, dispatch_id, 'held-transport')
        result = self.admit(content='Accepted café result\r\nwith exact text.')
        self.assertEqual(result['status'], 'admitted')
        after = self.current()
        self.assertEqual((after['current_phase'], after['current_turn']), (1, 0))
        event = after['admitted_events'][0]
        self.assertEqual(event['event_id'], result['event_id'])
        self.assertEqual(event['content'], 'Accepted café result\r\nwith exact text.')
        self.assertIsNotNone(event['projected_message_id'])
        self.assertEqual(self.messages.get_by_id(event['projected_message_id'])['text'], event['content'])
        self.assertEqual(self.trigger.queue.claim(self.owner, 'held-transport')['state'], 'acknowledged',
                         'accepted final must not implicitly release transport ownership')

    def test_duplicate_id_and_second_id_for_consumed_attempt_are_rejected(self):
        errors = importlib.import_module('turn_events')
        brief_id = self.invocation()['brief_id']
        event_id = uuid.uuid4().hex
        self.engine.admit_event(brief_id, 'final', 'Accepted once', self.owner, event_id=event_id)
        for retry_id in (event_id, uuid.uuid4().hex):
            with self.subTest(retry_id=retry_id), self.assertRaises(errors.EventConflict):
                self.engine.admit_event(brief_id, 'final', 'Accepted once', self.owner, event_id=retry_id)
        self.assertEqual(self.current()['current_phase'], 1)
        self.assertEqual(len(self.current()['admitted_events']), 1)

    def test_concurrent_submissions_consume_one_attempt(self):
        errors = importlib.import_module('turn_events')
        brief_id = self.invocation()['brief_id']
        event_id = uuid.uuid4().hex
        def submit(_):
            try:
                return self.engine.admit_event(brief_id, 'final', 'Concurrent result', self.owner, event_id=event_id)['status']
            except errors.EventConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, range(2)))
        self.assertCountEqual(outcomes, ['admitted', 'conflict'])
        self.assertEqual(self.current()['current_phase'], 1)
        self.assertEqual(len(self.current()['admitted_events']), 1)

    def test_each_identity_override_must_match_bound_invocation(self):
        errors = importlib.import_module('turn_events')
        before = self.path.read_bytes()
        for field in ('run_id', 'turn_id', 'attempt_id', 'input_revision'):
            with self.subTest(field=field), self.assertRaises(errors.EventConflict):
                self.admit(identities={field: 'different-' + uuid.uuid4().hex})
            self.assertEqual(self.path.read_bytes(), before)
        invocation = self.invocation()
        matching = {field: invocation[field] for field in ('run_id', 'turn_id', 'attempt_id', 'input_revision')}
        self.assertEqual(self.admit(identities=matching)['status'], 'admitted')

    def test_wrong_and_replaced_identity_cannot_submit(self):
        errors = importlib.import_module('turn_events')
        for wrong in (self.peer, {**self.owner, 'identity_id': uuid.uuid4().hex}):
            with self.subTest(name=wrong['name']), self.assertRaises(errors.EventAccessError):
                self.admit(instance=wrong)
        self.assertEqual(self.current()['current_phase'], 0)
        self.assertEqual(self.current().get('admitted_events', []), [])

    def test_question_requires_explicit_continue_and_fences_old_attempt(self):
        errors = importlib.import_module('turn_events')
        old = deepcopy(self.invocation())
        result = self.admit(kind='question', content='Which evidence should I use?')
        waiting = self.current()
        self.assertEqual(waiting['state'], 'awaiting_input')
        self.assertEqual(waiting['current_question']['event_id'], result['event_id'])
        self.assertEqual((waiting['current_phase'], waiting['current_turn']), (0, 0))
        self.messages.add('human', 'Use the blue source. Ordinary chat answer.')
        self.messages.add('codex', 'Status: ready to continue.')
        self.messages.add('codex', 'Old decision', msg_type='decision', metadata={'resolved': True})
        self.assertEqual(self.current()['state'], 'awaiting_input')
        with self.assertRaises(errors.EventConflict):
            self.engine.continue_session(self.session_id, 'unrelated-question', 'Use blue.')
        self.engine.continue_session(self.session_id, result['event_id'], 'Use the blue source explicitly.')
        resumed = self.current()
        fresh = resumed['active_invocation']
        self.assertEqual((resumed['current_phase'], resumed['current_turn']), (0, 0))
        self.assertNotEqual(resumed['state'], 'awaiting_input')
        self.assertNotEqual(fresh['attempt_id'], old['attempt_id'])
        self.assertNotEqual(fresh['brief_id'], old['brief_id'])
        self.assertEqual(fresh['turn_id'], old['turn_id'])
        self.assertEqual(fresh['input_revision'], old['input_revision'])
        self.assertIn('Use the blue source explicitly.', json.dumps(resumed['continuation_context']))
        with self.assertRaises(errors.EventConflict):
            self.engine.admit_event(old['brief_id'], 'final', 'Late old result', self.owner)
        self.assertEqual(self.admit(content='Fresh continued result')['status'], 'admitted')
        self.assertEqual(self.current()['current_phase'], 1)

    def test_malformed_or_oversize_content_does_not_mutate_session(self):
        errors = importlib.import_module('turn_events')
        before = deepcopy(self.current())
        disk = self.path.read_bytes()
        for content in (None, b'bytes', '', '   ', 'a\x00b', '\ud800', 'x' * (512 * 1024 + 1)):
            with self.subTest(content_type=type(content).__name__), self.assertRaises(errors.EventValidationError):
                self.admit(content=content)
            self.assertEqual(self.current(), before)
            self.assertEqual(self.path.read_bytes(), disk)
        with self.assertRaises(errors.EventValidationError):
            self.admit(kind='status', content='Still working')

    def test_failed_session_write_preserves_disk_memory_and_queue(self):
        before = deepcopy(self.current())
        disk = self.path.read_bytes()
        queue_disk = (self.root / 'queue/ledger.json').read_bytes()
        with patch('session_store.atomic_json', side_effect=OSError('fixture atomic write failure')):
            with self.assertRaises(OSError):
                self.admit()
        self.assertEqual(self.current(), before)
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue_disk)

    def test_projection_failure_retains_accepted_content_and_recovers_once(self):
        errors = importlib.import_module('turn_events')
        old_brief = self.invocation()['brief_id']
        event_id = uuid.uuid4().hex
        with patch.object(self.messages, 'add_once', side_effect=OSError('fixture chat projection failure')):
            try:
                self.engine.admit_event(old_brief, 'final', 'Durably accepted result', self.owner, event_id=event_id)
            except OSError:
                pass
        accepted = self.current()
        self.assertEqual(accepted['current_phase'], 1)
        self.assertEqual(len(accepted['admitted_events']), 1)
        self.assertEqual(accepted['admitted_events'][0]['content'], 'Durably accepted result')
        self.assertIsNone(accepted['admitted_events'][0]['projected_message_id'])
        self.assertIsNone(self.trigger.queue.claim(self.peer, 'fixture-peer'), 'successor must wait for result projection')
        self.engine.recover_projections()
        self.engine.recover_projections()
        self.assertEqual(self.current()['current_phase'], 1)
        self.assertIsNotNone(self.current()['admitted_events'][0]['projected_message_id'])
        self.assertEqual(sum(msg['text'] == 'Durably accepted result' for msg in self.messages.get_recent(100)), 1)
        with self.assertRaises(errors.EventConflict):
            self.engine.admit_event(old_brief, 'final', 'Durably accepted result', self.owner, event_id=event_id)

    def test_projection_before_backlink_failure_recovers_by_stable_uid_after_reload(self):
        content = 'Projected before backlink persisted'
        with patch.object(self.sessions, 'link_event_projection', side_effect=OSError('fixture backlink failure')):
            try:
                self.admit(content=content)
            except OSError:
                pass
        self.assertEqual(sum(msg['text'] == content for msg in self.messages.get_recent(100)), 1)
        self.assertIsNone(self.current()['admitted_events'][0]['projected_message_id'])
        restored_sessions = SessionStore(str(self.path))
        restored_messages = MessageStore(str(self.root / 'messages.jsonl'))
        restored_engine = SessionEngine(restored_sessions, restored_messages, self.trigger, self.registry)
        restored_engine.recover_projections()
        restored_engine.recover_projections()
        restored = restored_sessions.get(self.session_id)
        self.assertEqual(restored['current_phase'], 1)
        self.assertEqual(len(restored['admitted_events']), 1)
        self.assertIsNotNone(restored['admitted_events'][0]['projected_message_id'])
        self.assertEqual(sum(msg['text'] == content for msg in restored_messages.get_recent(100)), 1)

    def test_human_result_is_distinct_from_agent_submission(self):
        errors = importlib.import_module('turn_events')
        with self.assertRaises(errors.EventAccessError):
            self.engine.human_result(self.session_id, self.invocation()['brief_id'], 'Operator impersonation', submitted_by='human')
        human = self.engine.start_session('review', 'human-room',
            {'reviewer': 'human', 'editor': 'claude'}, 'human', input_text='Human source')
        human_invocation = self.sessions.get(human['id'])['active_invocation']
        with self.assertRaises(errors.EventAccessError):
            self.engine.admit_event(human_invocation['brief_id'], 'final', 'Agent impersonates human', self.owner)
        self.engine.human_result(human['id'], human_invocation['brief_id'], 'Explicit human result', submitted_by='human')
        after = self.sessions.get(human['id'])
        self.assertEqual(after['current_phase'], 1)
        self.assertEqual(after['admitted_events'][0]['content'], 'Explicit human result')
        self.assertIn('human_operator', json.dumps(after['admitted_events'][0]))

    def test_legacy_session_chat_never_auto_completes_or_invents_an_invocation(self):
        legacy = deepcopy(self.current())
        for field in ('completion_protocol', 'active_invocation', 'run_id', 'input_revision'):
            legacy.pop(field, None)
        self.path.write_text(json.dumps([legacy]), encoding='utf-8')
        restored = SessionStore(str(self.path))
        messages = MessageStore(str(self.root / 'legacy_messages.jsonl'))
        engine = SessionEngine(restored, messages, self.trigger, self.registry)
        def immediate_timer(delay, callback, args):
            timer = Mock()
            timer.start.side_effect = lambda: callback(*args)
            return timer
        with patch('session_engine.threading.Timer', immediate_timer):
            messages.add('codex', 'Legacy status, not an explicit result')
        after = restored.get(self.session_id)
        self.assertEqual((after['current_phase'], after['current_turn']), (0, 0))
        self.assertNotEqual(after['state'], 'complete')
        self.assertFalse(after.get('active_invocation'))


if __name__ == '__main__':
    unittest.main()
