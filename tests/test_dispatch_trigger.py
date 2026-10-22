"""Producer persistence, identity and envelope boundaries, without wrappers."""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agents import AgentTrigger
from registry import RuntimeRegistry


class DispatchTriggerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.registry = RuntimeRegistry(str(self.root))
        self.registry.seed({'codex': {'label': 'Codex'}})
        self.seat = self.registry.register('codex')
        self.trigger = AgentTrigger(self.registry, str(self.root))

    def test_sync_and_async_producers_preserve_distinct_complete_envelopes(self):
        self.trigger.trigger_sync('codex', message='user: first', channel='first',
                                  job_id=7, prompt='first prompt', dispatch_id='a' * 32,
                                  run_id='run-a', turn_id='turn-a', attempt_id='attempt-a',
                                  input_revision='source-a')
        asyncio.run(self.trigger.trigger('codex', message='user: second', channel='second',
                                         prompt='second prompt', dispatch_id='b' * 32,
                                         review_brief_id='c' * 32))
        first = self.trigger.queue.claim(self.seat, 'd' * 32)
        self.assertEqual(first['envelope']['target_identity_id'], self.seat['identity_id'])
        for key, value in {'channel': 'first', 'job_id': 7, 'prompt': 'first prompt',
                           'run_id': 'run-a', 'turn_id': 'turn-a', 'attempt_id': 'attempt-a',
                           'input_revision': 'source-a'}.items():
            self.assertEqual(first['envelope'][key], value)
        self.trigger.queue.acknowledge(self.seat, 'a' * 32, 'd' * 32)
        self.trigger.queue.release(self.seat, 'a' * 32, 'd' * 32)
        second = self.trigger.queue.claim(self.seat, 'd' * 32)
        self.assertEqual(second['envelope']['channel'], 'second')
        self.assertEqual(second['envelope']['review_brief_id'], 'c' * 32)
        self.assertNotIn('job_id', second['envelope'])
        self.assertFalse(list(self.root.glob('*_queue.jsonl')))

    def test_missing_instance_fails_without_binding_a_future_replacement(self):
        with self.assertRaises(ValueError):
            self.trigger.trigger_sync('missing', message='do not send to a future seat')
        self.assertFalse(list(self.root.glob('*_queue.jsonl')))

    def test_failed_transport_is_visible_without_showing_envelope_text(self):
        self.trigger.trigger_sync('codex', message='private source', dispatch_id='a' * 32)
        self.trigger.queue.claim(self.seat, 'worker')
        self.trigger.queue.release(self.seat, 'a' * 32, 'worker', failed=True)
        summary = self.trigger.queue.status()
        self.assertEqual(summary['seats'][self.seat['identity_id']]['failed'], 1)
        self.assertNotIn('private source', str(summary))

    def test_duplicate_dispatch_survives_identity_preserving_rename(self):
        queue = self.trigger.queue
        first = queue.enqueue(self.seat, {'dispatch_id': 'a' * 32, 'channel': 'general'})
        renamed = {**self.seat, 'name': 'renamed-seat'}
        retried = queue.enqueue(renamed, {'dispatch_id': 'a' * 32, 'channel': 'general'})
        self.assertEqual(retried['envelope'], first['envelope'])

    def test_invalid_routing_fields_fail_before_storage(self):
        queue = self.trigger.queue
        for fields in ({'channel': ['alpha']}, {'channel': 'general', 'job_id': True},
                       {'channel': 'general', 'prompt': {'wrong': 'type'}}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                queue.enqueue(self.seat, fields)
        self.assertFalse(queue.path.exists())

    def test_failed_enqueue_interrupts_session_visibly_instead_of_waiting_forever(self):
        from session_engine import SessionEngine
        from session_store import SessionStore
        from store import MessageStore
        sessions = SessionStore(str(self.root / 'sessions.json'))
        sessions.save_custom_template({'id': 'test', 'name': 'Test', 'roles': ['reviewer'],
            'phases': [{'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Inspect', 'is_output': True}]})
        messages = MessageStore(str(self.root / 'messages.jsonl'))
        engine = SessionEngine(sessions, messages, self.trigger, self.registry)
        with patch('dispatch_queue.atomic_json', side_effect=OSError('write failed')):
            result = engine.start_session('test', 'general', {'reviewer': 'codex'}, 'human', input_text='source')
        self.assertIsNone(result)
        self.assertEqual(sessions.get(1)['state'], 'interrupted')
        self.assertTrue(any(m.get('type') == 'session_error' for m in messages.get_recent(50)))
        self.assertFalse(self.trigger.queue.path.exists())
