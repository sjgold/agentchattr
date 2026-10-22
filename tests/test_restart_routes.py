"""Operator-only corrected source preparation, repair and activation routes."""
import unittest
from unittest.mock import patch
from contextlib import ExitStack
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app


class RestartRoutesTests(unittest.TestCase):
    def setUp(self):
        from tests.test_corrected_restart import CorrectedRestartTests
        self.fixture = CorrectedRestartTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        f = self.fixture
        self.api = FastAPI()
        with patch.object(app, 'app', self.api):
            app._install_security_middleware('operator-test', {'server': {'port': 18300}})
        for path, method, handler in (
            ('correct-and-restart', 'POST', app.correct_and_restart_session),
            ('prepare-contexts', 'POST', app.prepare_restart_contexts),
            ('activate-restart', 'POST', app.activate_corrected_session),
            ('restart-status', 'GET', app.corrected_session_status)):
            self.api.add_api_route('/api/sessions/{session_id}/' + path, handler, methods=[method])
        self.client = TestClient(self.api, client=('127.0.0.1', 40000))
        for name, value in (('registry', f.registry), ('session_engine', f.engine), ('session_store', f.sessions)):
            self.stack.enter_context(patch.object(app, name, value))
        self.operator = {'X-Session-Token': 'operator-test'}
        self.agent = {'Authorization': 'Bearer ' + f.helper['token']}
        self.path = f'/api/sessions/{f.parent_id}/correct-and-restart'
        self.body = {'input_text': 'Corrected café\r\nsource', 'request_id': 'a' * 32}

    def test_operator_two_step_human_flow_is_idempotent_and_old_brief_stays_fenced(self):
        self.assertEqual(self.client.post(self.path, json=self.body, headers=self.agent).status_code, 403)
        prepared = self.client.post(self.path, json=self.body, headers=self.operator)
        self.assertEqual(prepared.status_code, 200)
        child = prepared.json()
        self.assertEqual(child['state'], 'prepared')
        self.assertFalse(child['dispatch_eligible'])
        base = f"/api/sessions/{child['id']}"
        self.assertEqual(self.client.post(base + '/prepare-contexts', json={'context_request_id': 'b' * 32}, headers=self.agent).status_code, 403)
        self.assertEqual(self.client.post(base + '/prepare-contexts', json={'context_request_id': 'b' * 32}, headers=self.operator).status_code, 200)
        self.assertEqual(self.client.post(base + '/activate-restart', json={}, headers=self.agent).status_code, 403)
        activated = self.client.post(base + '/activate-restart', json={}, headers=self.operator)
        self.assertEqual(activated.status_code, 200)
        self.assertEqual(activated.json()['state'], 'waiting')
        repeated = self.client.post(self.path, json=self.body, headers=self.operator)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json()['active_invocation']['brief_id'], activated.json()['active_invocation']['brief_id'])
        self.assertEqual(len(self.fixture.sessions.list_all()), 2)
        self.assertEqual(self.client.get(base + '/restart-status', headers=self.operator).json()['id'], child['id'])
        self.assertEqual(self.client.post(base + '/prepare-contexts', json={'context_request_id': 'c' * 32}, headers=self.operator).status_code, 409)

    def test_same_source_and_unknown_or_oversize_fields_have_no_lineage_side_effects(self):
        f = self.fixture
        for body in ({**self.body, 'input_text': f.parent['input_snapshot']['text']},
                     {**self.body, 'api_key': 'must-not-store'},
                     {**self.body, 'input_text': 'z' * (512 * 1024 + 1)}):
            with self.subTest(fields=list(body)):
                response = self.client.post(self.path, json=body, headers=self.operator)
                self.assertEqual(response.status_code, 400)
        self.assertEqual(len(f.sessions.list_all()), 1)
        self.assertNotIn('replaced_by_run_id', f.sessions.get(f.parent_id))

    def test_restart_options_are_operator_only_safe_and_read_only(self):
        self.api.add_api_route('/api/sessions/{session_id}/restart-options', app.corrected_session_options, methods=['GET'])
        path = f'/api/sessions/{self.fixture.parent_id}/restart-options'
        self.assertEqual(self.client.get(path, headers=self.agent).status_code, 403)
        response = self.client.get(path, headers=self.operator)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['roles'][0]['kind'], 'human')
        self.assertEqual(response.json()['candidates'], [])
        self.assertNotIn(self.fixture.helper['token'], response.text)
        self.assertEqual(len(self.fixture.sessions.list_all()), 1)


if __name__ == '__main__':
    unittest.main()
