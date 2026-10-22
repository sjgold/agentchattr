"""A choice is a question within a turn, not a completed turn or interruption."""
import asyncio
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from registry import RuntimeRegistry
from turn_events import EventConflict


def setup_session(tmp_path, stack):
    sessions = SessionStore(str(tmp_path / 'session_runs.json'))
    sessions.save_custom_template({'id': 'test', 'name': 'Test', 'roles': ['asker', 'finisher'],
        'phases': [{'name': 'Work', 'participants': ['asker', 'finisher'], 'prompt': 'Test', 'is_output': True}]})
    messages = MessageStore(str(tmp_path / 'messages.jsonl'))
    registry = RuntimeRegistry(str(tmp_path))
    registry.seed({'claude': {}, 'codex': {}})
    registry.register('claude')
    registry.register('codex')
    trigger = Mock()
    engine = SessionEngine(sessions, messages, trigger, registry)
    timers = []
    def timer(delay, callback, args):
        result = Mock()
        result.start.side_effect = lambda: timers.append(lambda: callback(*args))
        return result
    stack.enter_context(patch('session_engine.threading.Timer', timer))
    stack.enter_context(patch.object(app, 'store', messages))
    stack.enter_context(patch.object(app, 'room_settings', {'username': 'Ben'}))
    stack.enter_context(patch.object(app, 'ws_clients', set()))
    engine.start_session('test', 'general', {'asker': 'claude', 'finisher': 'codex'}, 'Ben')
    return sessions, messages, engine, trigger, timers


def ask(messages, sender='claude', channel='general'):
    return messages.add(sender, 'Which?', msg_type='decision', channel=channel,
                        metadata={'choices': ['Blue', 'Green'], 'resolved': False})


def answer(question):
    request = Mock()
    async def body(): return {'choice': 'Blue'}
    request.json = body
    return asyncio.run(app.resolve_decision(question['id'], request))


class SessionChoiceTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.tmp_path = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.fixture = setup_session(self.tmp_path, self.stack)

    def submit(self, kind='final', content='Explicit final result'):
        sessions, messages, engine, trigger, timers = self.fixture
        invocation = sessions.get(1)['active_invocation']
        owner = engine._registry.get_instance(invocation['expected_agent'])
        return engine.admit_event(invocation['brief_id'], kind, content, owner)

    def test_choice_and_chat_require_explicit_final_to_advance_once(self):
        sessions, messages, engine, trigger, timers = self.fixture
        question = ask(messages)
        messages.add('claude', 'Please pick one.')
        assert answer(question)['ok']
        assert timers == []
        assert sessions.get(1)['current_turn'] == 0
        messages.add('claude', 'I will use Blue.')
        assert sessions.get(1)['current_turn'] == 0
        engine.resume_session(1)  # ordinary human answer interrupted the run
        self.submit()
        assert sessions.get(1)['current_turn'] == 1
        assert trigger.trigger_sync.call_count == 2
        self.submit(content='Explicit final output')
        assert sessions.get(1)['state'] == 'complete'

    def test_typed_question_holds_turn_and_schedules_no_chat_timer(self):
        sessions, messages, engine, trigger, timers = self.fixture
        self.submit('question', 'Which source?')
        messages.add('claude', 'I need a choice.')
        ask(messages)
        assert timers == []
        assert sessions.get(1)['state'] == 'awaiting_input'
        assert sessions.get(1)['current_turn'] == 0
        assert trigger.trigger_sync.call_count == 1

    def test_human_interruption_requires_explicit_resume_and_final(self):
        sessions, messages, engine, trigger, timers = self.fixture
        ask(messages)
        messages.add('Ben', '@claude Use red instead.')
        assert sessions.get(1)['state'] == 'paused'
        messages.add('claude', 'Using red.')
        with self.assertRaises(EventConflict):
            self.submit()
        assert sessions.get(1)['current_turn'] == 0
        engine.resume_session(1)
        assert trigger.trigger_sync.call_count == 1  # Resume never injects twice
        self.submit()
        assert sessions.get(1)['current_turn'] == 1

    def test_duplicate_choice_answer_is_rejected_without_second_reply(self):
        sessions, messages, engine, trigger, timers = self.fixture
        question = ask(messages)
        answer(question)
        result = answer(question)
        assert result.status_code == 400
        replies = [m for m in messages._messages if m.get('reply_to') == question['id']]
        assert len(replies) == 1
        assert sessions.get(1)['current_turn'] == 0
        assert sessions.get(1)['admitted_events'] == []

    def test_old_choice_cannot_answer_current_typed_question(self):
        sessions, messages, engine, trigger, timers = self.fixture
        old_question = ask(messages)
        current = self.submit('question', 'Current question')
        answer(old_question)
        assert sessions.get(1)['state'] == 'awaiting_input'
        assert sessions.get(1)['current_question']['event_id'] == current['event_id']
        messages.add('claude', 'Responding to the old answer.')
        assert timers == []
        assert sessions.get(1)['current_turn'] == 0
        assert trigger.trigger_sync.call_count == 1

    def test_question_card_in_other_channel_or_from_other_participant_is_ignored(self):
        sessions, messages, engine, trigger, timers = self.fixture
        ask(messages, channel='elsewhere')
        ask(messages, sender='codex')
        assert sessions.get(1).get('current_question') is None
        assert sessions.get(1)['admitted_events'] == []
        assert timers == []

    def test_typed_pending_question_survives_restart_without_retrigger(self):
        sessions, messages, engine, trigger, timers = self.fixture
        current = self.submit('question', 'Persist this question')
        restored = SessionStore(str(self.tmp_path / 'session_runs.json'))
        engine._store = restored
        engine.resume_active_sessions()
        assert restored.get(1)['current_question']['event_id'] == current['event_id']
        assert trigger.trigger_sync.call_count == 1
        messages.add('Ben', 'Ordinary chat is not continuation.')
        assert restored.get(1)['state'] == 'awaiting_input'
        engine.continue_session(1, current['event_id'], 'Explicit answer')
        assert restored.get(1)['state'] == 'waiting'
        assert trigger.trigger_sync.call_count == 2

    def test_end_session_rejects_late_typed_result(self):
        sessions, messages, engine, trigger, timers = self.fixture
        engine.end_session(1)
        with self.assertRaises(EventConflict):
            self.submit()
        assert sessions.get(1)['state'] == 'stopping'
        assert sessions.get(1)['dispatch_eligible'] is False
        assert trigger.trigger_sync.call_count == 1

    def test_fast_choice_answer_never_completes_a_pre_question_status(self):
        sessions, messages, engine, trigger, timers = self.fixture
        messages.add('claude', 'I need a choice.')
        question = ask(messages)
        answer(question)
        assert timers == []
        assert sessions.get(1)['current_turn'] == 0
        messages.add('claude', 'Using Blue.')
        assert sessions.get(1)['current_turn'] == 0
        engine.resume_session(1)
        self.submit()
        assert sessions.get(1)['current_turn'] == 1


if __name__ == '__main__':
    unittest.main()
