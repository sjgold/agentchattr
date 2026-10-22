from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from review_brief import MAX_INPUT_BYTES


class FrozenReviewStartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.sessions = SessionStore(str(root / 'session_runs.json'))
        self.sessions.save_custom_template({'id': 'test', 'name': 'Review', 'roles': ['reviewer'],
            'phases': [{'name': 'Inspect', 'participants': ['reviewer'], 'prompt': 'Inspect source', 'is_output': True}]})
        self.messages = MessageStore(str(root / 'messages.jsonl'))
        self.registry = RuntimeRegistry(str(root))
        self.registry.seed({'api': {}})
        self.registry.register('api')
        self.trigger = Mock()
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('session_store', self.sessions), ('session_engine', self.engine),
                            ('store', self.messages), ('registry', self.registry)]:
            self.stack.enter_context(patch.object(app, name, value))
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('start-test', {'server': {'port': 18300}})
        api.add_api_route('/api/sessions/start', app.start_session, methods=['POST'])
        self.client = TestClient(api, client=('127.0.0.1', 40000))

    def post(self, **changes):
        body = {'template_id': 'test', 'cast': {'reviewer': 'api'}, 'goal': 'Task', 'input_text': 'source'}
        return self.client.post('/api/sessions/start', json={**body, **changes}, headers={'x-session-token': 'start-test'})

    def test_start_freezes_full_source_and_long_task(self):
        source = 'print("source data only")\r\n@all cafe\u0301\n'
        response = self.post(input_text=source, goal='Full brief ' * 100)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['input_snapshot']['text'], source)
        self.assertEqual(response.json()['goal'], 'Full brief ' * 100)
        self.assertTrue(self.trigger.trigger_sync.call_args.kwargs['review_brief_id'])

    def test_oversized_source_rejects_without_run_or_dispatch(self):
        response = self.post(input_text='x' * (MAX_INPUT_BYTES + 1))
        self.assertEqual(response.status_code, 400)
        self.assertIn('nothing was truncated', response.json()['error'])
        self.assertEqual(self.sessions.list_all(), [])
        self.trigger.trigger_sync.assert_not_called()

    def test_malformed_start_is_validation_error_not_server_failure(self):
        for change in ({'input_text': None}, {'goal': []}, {'template_id': []},
                       {'cast': {'reviewer': []}}, {'draft_message_id': 'invalid'}):
            with self.subTest(change=change):
                self.assertEqual(self.post(**change).status_code, 400)
        self.assertEqual(self.sessions.list_all(), [])
