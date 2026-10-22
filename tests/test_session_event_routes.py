import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from agents import AgentTrigger
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore


class SessionEventRoutes(unittest.TestCase):
    def test_bearer_events_and_operator_continuation_have_distinct_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            sessions = SessionStore(directory + '/runs.json')
            sessions.save_custom_template({'id': 'test', 'name': 'Test', 'roles': ['reviewer'],
                'phases': [{'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Read.', 'is_output': True}]})
            registry = RuntimeRegistry(directory)
            registry.seed({'one': {}, 'two': {}})
            one, two = registry.register('one'), registry.register('two')
            messages = MessageStore(directory + '/messages.jsonl')
            engine = SessionEngine(sessions, messages, AgentTrigger(registry, directory), registry)
            run = engine.start_session('test', 'general', {'reviewer': 'one'}, 'user', input_text='source')
            brief = run['active_invocation']['brief_id']
            api = FastAPI()
            with patch.object(app, 'app', api):
                app._install_security_middleware('operator-test', {'server': {'port': 18300}})
            api.add_api_route('/api/sessions/{session_id}/event', app.session_event, methods=['POST'])
            api.add_api_route('/api/sessions/{session_id}/continue', app.continue_session_event, methods=['POST'])
            api.add_api_route('/api/sessions/{session_id}/human-result', app.human_session_result, methods=['POST'])
            client = TestClient(api, client=('127.0.0.1', 40000))
            owner = {'Authorization': 'Bearer ' + one['token']}
            peer = {'Authorization': 'Bearer ' + two['token']}
            operator = {'x-session-token': 'operator-test'}
            event = {'brief_id': brief, 'kind': 'question', 'content': 'Which source?'}
            with patch.object(app, 'registry', registry), patch.object(app, 'session_store', sessions), patch.object(app, 'session_engine', engine):
                self.assertEqual(client.post('/api/sessions/1/event', json=event, headers=operator).status_code, 403)
                self.assertEqual(client.post('/api/sessions/1/event', json=event, headers=peer).status_code, 403)
                self.assertEqual(client.post('/api/sessions/99/event', json=event, headers=owner).status_code, 409)
                result = client.post('/api/sessions/1/event', json=event, headers=owner)
                self.assertEqual(result.status_code, 200)
                question = result.json()['event_id']
                answer = {'question_event_id': question, 'answer': 'Use the supplied source.'}
                self.assertEqual(client.post('/api/sessions/1/continue', json=answer, headers=owner).status_code, 403)
                self.assertEqual(client.post('/api/sessions/1/continue', json=answer, headers=operator).status_code, 200)
                self.assertEqual(client.post('/api/sessions/1/event', json={**event, 'kind': 'final'}, headers=owner).status_code, 409)
                self.assertEqual(client.post('/api/sessions/1/human-result', json={'brief_id': brief, 'content': 'Forged'}, headers=owner).status_code, 403)

    def test_strict_api_response_parser_has_no_status_or_text_fallback(self):
        from turn_events import parse_session_response, EventValidationError
        self.assertEqual(parse_session_response('```json\n{"kind":"question","content":"Which source?"}\n```')['kind'], 'question')
        for text in ('Still working', '{"kind":"status","content":"working"}',
                     '{"kind":"final","content":""}', 'prefix {"kind":"final","content":"result"}',
                     '{"kind":"final","content":"result","extra":true}'):
            with self.subTest(text=text), self.assertRaises(EventValidationError):
                parse_session_response(text)
