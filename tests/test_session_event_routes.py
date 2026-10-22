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
    def test_identity_preserving_rename_can_continue_the_frozen_seat(self):
        from tests.test_session_events import SessionEventTests
        fixture = SessionEventTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        question = fixture.admit(kind='question', content='Which source?')
        renamed = fixture.registry.rename(fixture.owner['name'], 'renamed-reviewer')
        self.assertIsInstance(renamed, dict)
        resumed = fixture.engine.continue_session(fixture.session_id, question['event_id'], 'Use the original source.')
        self.assertEqual(resumed['state'], 'waiting')
        self.assertEqual(resumed['active_invocation']['expected_identity_id'], fixture.owner['identity_id'])
        self.assertEqual(resumed['active_invocation']['expected_agent'], 'renamed-reviewer')
        self.assertEqual(fixture.engine.get_active('general')['current_agent'], 'renamed-reviewer')

    def test_disconnected_agent_cannot_silently_become_a_human_on_continue(self):
        from tests.test_session_events import SessionEventTests
        from turn_events import EventConflict
        fixture = SessionEventTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        question = fixture.admit(kind='question', content='Which source?')
        fixture.registry.deregister(fixture.owner['name'])
        with self.assertRaises(EventConflict):
            fixture.engine.continue_session(fixture.session_id, question['event_id'], 'Use the original source.')
        self.assertFalse((fixture.current().get('active_invocation') or {}).get('human'))

    def test_human_brief_cannot_be_read_by_a_later_agent_with_the_same_name(self):
        from review_brief import BriefAccessError
        with tempfile.TemporaryDirectory() as directory:
            sessions = SessionStore(directory + '/runs.json')
            sessions.save_custom_template({'id': 'human', 'name': 'Human', 'roles': ['reviewer'],
                'phases': [{'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Read.'},
                           {'name': 'Decide', 'participants': ['reviewer'], 'prompt': 'Decide.', 'is_output': True}]})
            registry = RuntimeRegistry(directory)
            engine = SessionEngine(sessions, MessageStore(directory + '/messages.jsonl'),
                                   AgentTrigger(registry, directory), registry)
            run = engine.start_session('human', 'general', {'reviewer': 'alice'}, 'operator', input_text='Private human source')
            registry.seed({'alice': {}})
            replacement = registry.register('alice')
            with self.assertRaises(BriefAccessError):
                sessions.briefs.get(run['active_invocation']['brief_id'], replacement)
            self.assertEqual(sessions.briefs.get(run['active_invocation']['brief_id'], operator=True)['source'], 'Private human source')
            engine.human_result(run['id'], run['active_invocation']['brief_id'], 'First human result')
            next_brief = sessions.get(run['id'])['active_invocation']['brief_id']
            with self.assertRaises(BriefAccessError):
                sessions.briefs.get(next_brief, replacement)

    def test_mcp_compact_reference_keeps_actual_bearer_identity(self):
        import json
        import mcp_bridge
        from unittest.mock import Mock
        engine = Mock()
        engine.admit_event.return_value = {'status': 'admitted', 'event_id': 'a' * 32}
        seat = {'name': 'one', 'identity_id': 'b' * 32}
        with patch.object(mcp_bridge, 'session_engine', engine), patch.object(mcp_bridge, '_authenticated_instance', return_value=seat):
            result = json.loads(mcp_bridge.chat_session_event('c' * 32, 'final', 'Accepted result'))
            self.assertEqual(result['status'], 'admitted')
            engine.admit_event.assert_called_once_with('c' * 32, 'final', 'Accepted result', seat)
        with patch.object(mcp_bridge, '_authenticated_instance', return_value=None):
            result = json.loads(mcp_bridge.chat_session_event('c' * 32, 'final', 'No spoofing'))
            self.assertNotEqual(result['status'], 'admitted')

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
                self.assertEqual(client.post('/api/sessions/1/event', json={**event, 'event_id': ''}, headers=owner).status_code, 400)
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
                human = engine.start_session('test', 'human-room', {'reviewer': 'user'}, 'user', input_text='Human source')
                submitted = client.post(f"/api/sessions/{human['id']}/human-result", headers=operator,
                    json={'brief_id': human['active_invocation']['brief_id'], 'content': 'Explicit human final', 'submitted_by': 'user'})
                self.assertEqual(submitted.status_code, 200)
                complete = sessions.get(human['id'])
                self.assertEqual(complete['state'], 'complete')
                output = messages.get_by_id(complete['output_message_id'])
                self.assertTrue(output['metadata'].get('session_output'))

    def test_strict_api_response_parser_has_no_status_or_text_fallback(self):
        from turn_events import parse_session_response, EventValidationError
        self.assertEqual(parse_session_response('```json\n{"kind":"question","content":"Which source?"}\n```')['kind'], 'question')
        for text in ('Still working', '{"kind":"status","content":"working"}',
                     '{"kind":"final","content":""}', 'prefix {"kind":"final","content":"result"}',
                     '{"kind":"status","kind":"final","content":"result"}',
                     '{"kind":"final","content":"result","extra":true}'):
            with self.subTest(text=text), self.assertRaises(EventValidationError):
                parse_session_response(text)
