"""Real operator middleware around participant decisions, with process doubles."""
from contextlib import ExitStack
import json
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from tests import test_participant_recovery_engine as fixture


class ParticipantRecoveryRoutesTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.ParticipantRecoveryEngineTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('participant-operator-test', {'server': {'port': 18300}})
        api.add_api_route('/api/sessions/{session_id}/participant-recovery', app.get_participant_recovery, methods=['GET'])
        for path, function in (('replace-participant', app.replace_session_participant),
                               ('repair-replacement', app.repair_session_replacement),
                               ('skip-participant', app.skip_session_participant)):
            api.add_api_route('/api/sessions/{session_id}/' + path, function, methods=['POST'])
        self.client = TestClient(api, client=('127.0.0.1', 40000))
        self.path = '/api/sessions/' + str(self.f.f.run['id'])
        self.headers = {'X-Session-Token': 'participant-operator-test'}
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(app, 'registry', self.f.f.fixture.registry))
        stack.enter_context(patch.object(app, 'session_engine', self.f.engine))
        stack.enter_context(patch.object(self.f.f.fixture.manager, 'participant_exit_proof', return_value={'local_ended': False}))

    def test_worker_bearer_and_missing_operator_token_cannot_preview_or_mutate(self):
        for headers in ({}, {'Authorization': 'Bearer ' + self.f.f.source['token']}):
            self.assertEqual(self.client.get(self.path + '/participant-recovery', headers=headers).status_code, 403)
            for action in ('replace-participant', 'skip-participant', 'repair-replacement'):
                self.assertEqual(self.client.post(self.path + '/' + action, json={}, headers=headers).status_code, 403)

    def test_operator_options_and_exact_replacement_replay_are_no_store_and_source_is_private(self):
        options = self.client.get(self.path + '/participant-recovery', headers=self.headers)
        self.assertEqual(options.status_code, 200)
        self.assertEqual(options.headers['cache-control'], 'no-store')
        for _ in range(2):
            result = self.client.post(self.path + '/replace-participant', json=self.f.decision, headers=self.headers)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.headers['cache-control'], 'no-store')
            self.assertEqual(result.json()['status'], 'preparing_contexts')
            self.assertNotIn('target_provenance', result.text)
        self.assertEqual(len(self.f.sessions.get(self.f.f.run['id'])['replacement_requests']), 1)

    def test_strict_bounded_unique_json_is_rejected_before_engine_action(self):
        decision = json.dumps(self.f.decision)
        duplicate = '{"request_id":"' + self.f.decision['request_id'] + '",' + decision[1:]
        for action, method, valid in (
            ('replace-participant', 'replace_participant', self.f.decision),
            ('repair-replacement', 'repair_replacement', {'request_id': uuid.uuid4().hex, 'preparation_attempt': uuid.uuid4().hex}),
            ('skip-participant', 'skip_participant', {key: self.f.decision[key] for key in ('request_id', 'checkpoint_id', 'attempt_id')} |
                {'reason': 'Missing work.', 'confirm_skip': True})):
            with patch.object(self.f.engine, method) as execute:
                payload = json.dumps(valid)
                for content in ('[]', '{', json.dumps(dict(valid, content='override')), payload[:-1] + ',"unknown":true}',
                                duplicate, json.dumps(dict(valid, reason='x' * 9000)), b'\xff'):
                    response = self.client.post(self.path + '/' + action, content=content, headers=self.headers)
                    self.assertEqual(response.status_code, 400)
                execute.assert_not_called()

    def test_pending_stop_conflict_and_storage_errors_are_sanitized(self):
        with patch.object(self.f.engine, 'participant_recovery_options', side_effect=OSError('PRIVATE_RUNTIME_PATH')):
            response = self.client.get(self.path + '/participant-recovery', headers=self.headers)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('PRIVATE_RUNTIME_PATH', response.text)
        self.f.engine.stop_session(self.f.f.run['id'])
        response = self.client.post(self.path + '/replace-participant', json=self.f.decision, headers=self.headers)
        self.assertEqual(response.status_code, 409)
