"""Operator-only HTTP recovery routes, actual middleware and signed stores."""
from contextlib import ExitStack
import json
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from tests import test_saved_result_recovery as fixture


class SavedResultRoutesTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.SavedResultRecoveryTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('saved-operator-test', {'server': {'port': 18300}})
        api.add_api_route('/api/sessions/{session_id}/saved-results', app.get_saved_session_results, methods=['GET'])
        api.add_api_route('/api/sessions/{session_id}/deliver-saved-result', app.deliver_saved_session_result, methods=['POST'])
        self.client = TestClient(api, client=('127.0.0.1', 40000))
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(app, 'registry', self.f.fixture.registry))
        stack.enter_context(patch.object(app, 'session_engine', self.f.engine))
        self.headers = {'X-Session-Token': 'saved-operator-test'}
        self.path = '/api/sessions/' + str(self.f.session_id)
        self.body = {'result_id': self.f.payload['result_id']}

    def test_registered_worker_and_missing_token_cannot_preview_or_deliver(self):
        for headers in ({}, {'Authorization': 'Bearer ' + self.f.owner['token']}):
            self.assertEqual(self.client.get(self.path + '/saved-results', headers=headers).status_code, 403)
            self.assertEqual(self.client.post(self.path + '/deliver-saved-result', json=self.body, headers=headers).status_code, 403)
        self.assertEqual(self.f.current()['admitted_events'], [])

    def test_preview_and_delivery_are_scoped_no_store_and_never_accept_raw_content(self):
        preview = self.client.get(self.path + '/saved-results', headers=self.headers)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.headers['cache-control'], 'no-store')
        self.assertEqual(preview.json()['saved_results'][0]['content'], self.f.payload['content'])
        for private in (self.f.secret, self.f.record['seal'], str(self.f.runtime), self.f.owner_scope['launch_nonce']):
            self.assertNotIn(private, preview.text)
        for body in ({}, [], {**self.body, 'content': 'not caller-owned'}, {'result_id': True},
                     {**self.body, 'seal_secret': self.f.secret}, {'result_id': '../escape'}):
            response = self.client.post(self.path + '/deliver-saved-result', json=body, headers=self.headers)
            self.assertEqual(response.status_code, 400)
        missing = self.client.post(self.path + '/deliver-saved-result', json={'result_id': uuid.uuid4().hex}, headers=self.headers)
        self.assertEqual(missing.status_code, 409)
        response = self.client.post(self.path + '/deliver-saved-result', json=self.body, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertFalse(response.json()['transport_settled'])
        self.assertEqual(response.json()['accepted_event_id'], self.f.payload['result_id'])
        self.assertEqual(self.f.current()['admitted_events'][0]['submitted_by'], 'operator')
        again = self.client.post(self.path + '/deliver-saved-result', json=self.body, headers=self.headers)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(len(self.f.current()['admitted_events']), 1)

    def test_bad_json_and_oversized_metadata_do_not_reach_the_engine(self):
        with patch.object(self.f.engine, 'deliver_saved_result') as deliver:
            for text in ('not JSON', json.dumps({'result_id': 'a' * 9000}),
                         '{"result_id":"' + self.f.payload['result_id'] + '","result_id":"' + self.f.payload['result_id'] + '"}'):
                response = self.client.post(self.path + '/deliver-saved-result', content=text, headers=self.headers)
                self.assertEqual(response.status_code, 400)
            deliver.assert_not_called()

    def test_storage_errors_are_sanitized_and_do_not_leak_internal_paths(self):
        for method, suffix in (('saved_results', 'saved-results'), ('deliver_saved_result', 'deliver-saved-result')):
            with patch.object(self.f.engine, method, side_effect=OSError(str(self.f.runtime) + self.f.secret)):
                response = (self.client.get(self.path + '/' + suffix, headers=self.headers) if method == 'saved_results'
                            else self.client.post(self.path + '/' + suffix, json=self.body, headers=self.headers))
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(str(self.f.runtime), response.text)
                self.assertNotIn(self.f.secret, response.text)
