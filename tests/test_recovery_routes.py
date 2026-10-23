"""Operator recovery actions are scoped, explicit and strict about policy input."""
from contextlib import ExitStack
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app


class RecoveryRoutesTests(unittest.TestCase):
    def setUp(self):
        from tests.test_turn_recovery import TurnRecoveryTests
        self.f = TurnRecoveryTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        _, self.checkpoint = self.f.terminal_failure()
        self.api = FastAPI()
        with patch.object(app, 'app', self.api):
            app._install_security_middleware('operator-test', {'server': {'port': 18300}})
        self.api.add_api_route('/api/sessions/start', app.start_session, methods=['POST'])
        self.client = TestClient(self.api, client=('127.0.0.1', 40000))
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name, value in (('registry', self.f.registry), ('session_engine', self.f.engine),
                            ('session_store', self.f.sessions), ('store', self.f.messages)):
            stack.enter_context(patch.object(app, name, value))
        self.operator = {'X-Session-Token': 'operator-test'}
        self.agent = {'Authorization': 'Bearer ' + self.f.owner['token']}
        self.body = {'checkpoint_id': self.checkpoint['checkpoint_id'], 'attempt_id': self.f.original['attempt_id']}

    def test_start_rejects_bad_policy_and_freezes_valid_run_override(self):
        body = {'template_id': 'review', 'channel': 'override', 'cast': {'reviewer': 'codex', 'editor': 'claude'}}
        bad = self.client.post('/api/sessions/start', json={**body, 'recovery_policy': {'ack_timeout': True}}, headers=self.operator)
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(len(self.f.sessions.list_all()), 1)
        good = self.client.post('/api/sessions/start', json={**body, 'recovery_policy': {'ack_timeout': 2}}, headers=self.operator)
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.json()['recovery_policy']['ack_timeout'], 2)
        self.api.add_api_route('/api/sessions/{session_id}/recovery-status', app.session_recovery_status, methods=['GET'])
        status = self.client.get(f"/api/sessions/{good.json()['id']}/recovery-status", headers=self.operator)
        self.assertEqual(status.status_code, 200)
        self.assertIsNone(status.json()['turn_recovery'])

    def test_wait_and_retry_require_operator_and_exact_checkpoint(self):
        self.api.add_api_route('/api/sessions/{session_id}/wait', app.wait_session_turn, methods=['POST'])
        self.api.add_api_route('/api/sessions/{session_id}/retry', app.retry_session_turn, methods=['POST'])
        wait = {**self.body, 'extend_seconds': 20}
        for action, body in (('wait', wait), ('retry', {**self.body, 'request_id': uuid.uuid4().hex})):
            path = f'/api/sessions/{self.f.session_id}/{action}'
            self.assertEqual(self.client.post(path, json=body, headers=self.agent).status_code, 403)
            self.assertEqual(self.client.post(path, json={**body, 'content': 'not an answer recovery'}, headers=self.operator).status_code, 400)
            self.assertEqual(self.client.post(path, json={**body, 'checkpoint_id': uuid.uuid4().hex}, headers=self.operator).status_code, 409)
        response = self.client.post(f'/api/sessions/{self.f.session_id}/wait', json=wait, headers=self.operator)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['active_invocation']['attempt_id'], self.f.original['attempt_id'])
        retry = self.client.post(f'/api/sessions/{self.f.session_id}/retry',
            json={**self.body, 'request_id': uuid.uuid4().hex}, headers=self.operator)
        self.assertEqual(retry.status_code, 200, 'Waiting longer must not lock out a later explicit retry choice.')
        self.assertNotEqual(retry.json()['active_invocation']['attempt_id'], self.f.original['attempt_id'])

    def test_retry_is_idempotent_and_status_read_does_not_dispatch(self):
        self.api.add_api_route('/api/sessions/{session_id}/retry', app.retry_session_turn, methods=['POST'])
        self.api.add_api_route('/api/sessions/{session_id}/recovery-status', app.session_recovery_status, methods=['GET'])
        path = f'/api/sessions/{self.f.session_id}'
        ledger = self.f.root / 'queue/ledger.json'
        before = ledger.read_bytes()
        status = self.client.get(path + '/recovery-status', headers=self.operator)
        self.assertEqual(status.status_code, 200)
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(self.client.get(path + '/recovery-status', headers=self.agent).status_code, 403)
        body = {**self.body, 'request_id': uuid.uuid4().hex}
        first = self.client.post(path + '/retry', json=body, headers=self.operator)
        self.assertEqual(first.status_code, 200)
        second = self.client.post(path + '/retry', json=body, headers=self.operator)
        self.assertEqual(second.json()['active_invocation'], first.json()['active_invocation'])
