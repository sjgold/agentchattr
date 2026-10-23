"""The coordinator, operator policy and rejected drafts share server authority."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from agents import AgentTrigger
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore, validate_session_template
from store import MessageStore


class CapacityRoutesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir='.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.policy = dict(max_roles=7, max_participants_per_phase=6,
                           max_phases=2, max_prompt_chars=60, max_total_turns=12)
        self.sessions = SessionStore(str(self.root / 'sessions.json'), capacity_policy=self.policy)
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.registry = RuntimeRegistry(str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages,
                                   AgentTrigger(self.registry, str(self.root)), self.registry)
        self.api = FastAPI()
        self.api.add_api_route('/api/session-capacity', app.get_session_capacity, methods=['GET'])
        self.api.add_api_route('/api/sessions/request-draft', app.request_session_draft, methods=['POST'])
        self.api.add_api_route('/api/sessions/save-draft', app.save_draft, methods=['POST'])
        self.api.add_api_route('/api/sessions/start', app.start_session, methods=['POST'])
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name, value in (('session_store', self.sessions), ('session_engine', self.engine),
                            ('store', self.messages), ('registry', self.registry)):
            stack.enter_context(patch.object(app, name, value))
        self.client = TestClient(self.api)

    def test_public_policy_and_coordinator_request_are_identical(self):
        policy = self.client.get('/api/session-capacity').json()
        self.assertEqual(policy['policy'], self.policy)
        self.assertEqual(policy['execution'], {'mode': 'sequential', 'active_turns_per_session': 1})
        response = self.client.post('/api/sessions/request-draft', json={'agent': 'coordinator', 'description': 'Use all six'})
        self.assertEqual(response.status_code, 200)
        request = self.messages.get_recent(1)[0]
        self.assertIn(policy['limits_text'], request['text'])

    def test_stale_valid_flag_cannot_save_or_start_excess_draft(self):
        template = {'id': 'excess', 'name': 'Whole team', 'roles': [f'r{i}' for i in range(7)],
                    'phases': [{'name': 'Review', 'participants': [f'r{i}' for i in range(7)],
                                'prompt': 'Read', 'is_output': True}]}
        original = deepcopy(template)
        self.messages.add('system', 'Fixture room opened')
        message = self.messages.add('system', 'Intact stale proposal', msg_type='session_draft',
                                    metadata={'valid': True, 'template': template})
        errors = validate_session_template(template, self.policy)
        saved = self.client.post('/api/sessions/save-draft', json={'message_id': message['id']})
        started = self.client.post('/api/sessions/start', json={'template_id': 'excess', 'draft_message_id': message['id'],
            'cast': {role: 'user' for role in template['roles']}})
        for response in (saved, started):
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['errors'], errors)
        self.assertEqual(self.messages.get_by_id(message['id'])['metadata']['template'], original)
        self.assertEqual(self.sessions.list_all(), [])
        self.assertIsNone(self.sessions.get_template('excess'))
        self.assertFalse((self.root / 'custom_templates.json').exists())

    def test_old_invalid_flag_is_rechecked_without_rewriting_original_proposal(self):
        self.api.add_api_route('/api/sessions/validate-draft', app.validate_session_draft, methods=['POST'])
        template = {'id': 'now-valid', 'name': 'Six people', 'roles': [f'r{i}' for i in range(6)],
                    'phases': [{'name': 'All', 'participants': [f'r{i}' for i in range(6)], 'is_output': True}]}
        self.messages.add('system', 'Room opened')
        message = self.messages.add('system', 'Old four-seat rejection', msg_type='session_draft',
                                    metadata={'valid': False, 'errors': ['old max4'], 'template': template})
        checked = self.client.post('/api/sessions/validate-draft', json={'message_id': message['id']})
        self.assertEqual(checked.status_code, 200)
        self.assertTrue(checked.json()['valid'])
        self.assertEqual(checked.json()['template'], template)
        self.assertEqual(checked.json()['errors'], [])
        saved = self.client.post('/api/sessions/save-draft', json={'message_id': message['id']})
        self.assertEqual(saved.status_code, 200)
        started = self.client.post('/api/sessions/start', json={'draft_message_id': message['id'],
            'cast': {role: 'user' for role in template['roles']}})
        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.json()['capacity_policy'], self.policy)
        self.assertFalse(self.messages.get_by_id(message['id'])['metadata']['valid'])

    def test_non_object_draft_fails_before_start_cache_or_dispatch(self):
        self.messages.add('system', 'Room opened')
        message = self.messages.add('system', 'Malformed old proposal', msg_type='session_draft',
                                    metadata={'valid': False, 'template': ['not a design object']})
        result = self.client.post('/api/sessions/start', json={'draft_message_id': message['id']})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json()['errors'], ['Template must be a JSON object'])
        self.assertEqual(self.sessions.get_templates(), [])
        self.assertEqual(self.sessions.list_all(), [])
