"""Actual queue middleware inspection, no server processes or provider calls."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from agents import AgentTrigger
from registry import RuntimeRegistry


class ArtifactInspectTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.audit-tmp'))
        self.registry = RuntimeRegistry(directory)
        self.registry.seed({'one': {}, 'two': {}})
        self.owner, self.peer = self.registry.register('one'), self.registry.register('two')
        self.agents = AgentTrigger(self.registry, directory)
        self.agents.trigger_sync('one', dispatch_id='a' * 32)
        self.agents.queue.claim(self.owner, 'original-consumer')
        self.agents.trigger_sync('one', dispatch_id='b' * 32)
        self.body = {'dispatch_id': 'a' * 32, 'consumer_id': 'original-consumer'}
        self.headers = {'authorization': 'Bearer ' + self.owner['token']}
        self.engine = Mock()
        self.enterContext(patch.object(app, 'registry', self.registry))
        self.enterContext(patch.object(app, 'agents', self.agents))
        self.enterContext(patch.object(app, 'session_engine', self.engine))
        self.enterContext(patch.object(app, 'session_token', 'operator-fixture'))
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-fixture', {'server': {'port': 18300}})
        api.add_api_route('/api/queue/{operation}', app.dispatch_operation, methods=['POST'])
        self.client = self.enterContext(TestClient(api, client=('127.0.0.1', 40000)))

    def test_inspect_own_active_and_released_records_is_no_store_and_never_claims_successor(self):
        for terminal in (False, True):
            with self.subTest(terminal=terminal):
                if terminal:
                    self.agents.queue.release(self.owner, 'a' * 32, 'original-consumer')
                before = self.agents.queue.path.read_bytes()
                response = self.client.post('/api/queue/inspect', headers=self.headers, json=self.body)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertEqual(response.json(), {'dispatch': self.agents.queue.owned(self.owner, 'a' * 32)})
                self.assertEqual(self.agents.queue.path.read_bytes(), before)
                self.assertEqual(self.agents.queue.owned(self.owner, 'b' * 32)['state'], 'queued')
                self.engine.monitor_turns.assert_not_called()

    def test_wrong_seat_consumer_unknown_dispatch_operator_and_cookie_refuse_without_effect(self):
        before = self.agents.queue.path.read_bytes()
        cases = (({'authorization': 'Bearer ' + self.peer['token']}, self.body),
                 (self.headers, {**self.body, 'consumer_id': 'wrong-consumer'}),
                 (self.headers, {**self.body, 'dispatch_id': 'c' * 32}),
                 ({'x-session-token': 'operator-fixture'}, self.body),
                 ({'cookie': 'session_token=operator-fixture'}, self.body))
        for headers, body in cases:
            with self.subTest(headers=tuple(headers), body=body):
                response = self.client.post('/api/queue/inspect', headers=headers, json=body)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertEqual(self.agents.queue.path.read_bytes(), before)
        self.engine.monitor_turns.assert_not_called()

    def test_inspect_rejects_extra_fields_empty_consumer_and_pruned_record_without_mutation(self):
        before = self.agents.queue.path.read_bytes()
        for body in ({**self.body, 'failed': False}, {**self.body, 'status': 'local_ended'},
                     {**self.body, 'consumer_id': ''}):
            with self.subTest(body=body):
                response = self.client.post('/api/queue/inspect', headers=self.headers, json=body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.agents.queue.path.read_bytes(), before)
        self.agents.queue.path.write_text('{"version":1,"records":[]}', encoding='utf-8')
        before = self.agents.queue.path.read_bytes()
        response = self.client.post('/api/queue/inspect', headers=self.headers, json=self.body)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {'error': 'Dispatch owner does not match this seat and consumer.'})
        self.assertEqual(self.agents.queue.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
