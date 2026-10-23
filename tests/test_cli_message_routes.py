"""Operator-only CLI message inspection and attachment through real middleware."""
from contextlib import ExitStack
import json
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from tests import test_cli_message_candidate as fixture


class CLIMessageRoutesTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CliMessageCandidateTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        message = self.f.source()
        candidate = self.f.engine.cli_message_candidate(self.f.run['id'], message['id'])
        self.body = {key: candidate[key] for key in ('message_id', 'message_uid', 'snapshot_hash', 'checkpoint')}
        self.body.update(request_id=uuid.uuid4().hex, kind='final', confirm_operator_attribution=False)
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('cli-operator-test', {'server': {'port': 18300}})
        api.add_api_route('/api/sessions/{session_id}/cli-message-candidate/{message_id}',
                          app.get_cli_message_candidate, methods=['GET'])
        api.add_api_route('/api/sessions/{session_id}/attach-cli-message',
                          app.attach_selected_cli_message, methods=['POST'])
        self.client = TestClient(api, client=('127.0.0.1', 40000))
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(app, 'registry', self.f.fixture.registry))
        stack.enter_context(patch.object(app, 'session_engine', self.f.engine))
        stack.enter_context(patch.object(self.f.fixture.manager, 'selected_cli_exit_proof',
                                       return_value={'local_ended': False}))
        self.path = '/api/sessions/' + str(self.f.run['id'])
        self.preview = self.path + '/cli-message-candidate/' + str(message['id'])
        self.headers = {'X-Session-Token': 'cli-operator-test'}

    def test_agent_bearer_and_missing_operator_token_cannot_preview_or_attach(self):
        for headers in ({}, {'Authorization': 'Bearer ' + self.f.cli['token']}):
            self.assertEqual(self.client.get(self.preview, headers=headers).status_code, 403)
            self.assertEqual(self.client.post(self.path + '/attach-cli-message', json=self.body,
                                             headers=headers).status_code, 403)

    def test_operator_preview_and_attach_replay_have_no_store_cache_or_extra_admission(self):
        preview = self.client.get(self.preview, headers=self.headers)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.headers['cache-control'], 'no-store')
        for _ in range(2):
            response = self.client.post(self.path + '/attach-cli-message', json=self.body, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertFalse(response.json()['transport_settled'])
        self.assertEqual(len(self.f.sessions.get(self.f.run['id'])['admitted_events']), 1)

    def test_invalid_duplicate_or_unbounded_json_never_reaches_attachment_engine(self):
        duplicate = '{"request_id":"' + self.body['request_id'] + '",' + json.dumps(self.body)[1:]
        nested = json.dumps(self.body).replace('"session_id": 1', '"session_id": 1,"session_id": 1')
        with patch.object(self.f.engine, 'attach_cli_message') as attach:
            for text in ('not JSON', '[]', json.dumps(dict(self.body, content='override')),
                         json.dumps(dict(self.body, message_uid='x' * 9000)), duplicate, nested):
                with self.subTest(length=len(text)):
                    response = self.client.post(self.path + '/attach-cli-message', content=text, headers=self.headers)
                    self.assertEqual(response.status_code, 400)
            attach.assert_not_called()

    def test_stale_checkpoint_is_conflict_and_storage_failures_hide_private_paths(self):
        changed = dict(self.body, checkpoint=dict(self.body['checkpoint'], attempt_id=uuid.uuid4().hex))
        response = self.client.post(self.path + '/attach-cli-message', json=changed, headers=self.headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.f.sessions.get(self.f.run['id'])['admitted_events'], [])
        private = str(self.f.fixture.root / 'private-native-worker')
        for name in ('cli_message_candidate', 'attach_cli_message'):
            with patch.object(self.f.engine, name, side_effect=OSError(private)):
                response = (self.client.get(self.preview, headers=self.headers) if name == 'cli_message_candidate'
                            else self.client.post(self.path + '/attach-cli-message', json=self.body, headers=self.headers))
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(private, response.text)
