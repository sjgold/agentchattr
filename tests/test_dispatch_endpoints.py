import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from agents import AgentTrigger
from registry import RuntimeRegistry


class DispatchEndpointTests(unittest.TestCase):
    def test_api_job_context_and_reply_stay_in_the_envelopes_job(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = RuntimeRegistry(directory)
            registry.seed({'one': {}})
            one = registry.register('one')
            jobs, messages = Mock(), Mock()
            messages.get_recent.return_value = [{'sender': 'user', 'text': 'unrelated channel source'}]
            jobs.get_messages.return_value = [{'sender': 'user', 'text': 'job eleven source'}]
            jobs.add_message.return_value = {'id': 1, 'text': 'job eleven answer'}
            api = FastAPI()
            api.add_api_route('/api/messages', app.get_messages, methods=['GET'])
            api.add_api_route('/api/send', app.api_send, methods=['POST'])
            client = TestClient(api)
            with patch.object(app, 'registry', registry), patch.object(app, 'jobs', jobs), patch.object(app, 'store', messages):
                history = client.get('/api/messages?channel=alpha&job_id=11')
                self.assertEqual(history.json()[0]['text'], 'job eleven source')
                reply = client.post('/api/send', headers={'Authorization': 'Bearer ' + one['token']},
                                    json={'text': 'answer', 'channel': 'alpha', 'job_id': 11})
                self.assertEqual(reply.status_code, 200)
                jobs.add_message.assert_called_once_with(11, one['name'], 'answer')
                messages.add.assert_not_called()

    def test_cooperative_release_is_scoped_and_only_changes_transport(self):
        import mcp_bridge
        with tempfile.TemporaryDirectory() as directory:
            registry = RuntimeRegistry(directory)
            registry.seed({'one': {}, 'two': {}})
            one, two = registry.register('one'), registry.register('two')
            agents = AgentTrigger(registry, directory)
            agents.trigger_sync('one', dispatch_id='a' * 32)
            agents.queue.claim(one, 'worker')
            with patch.object(mcp_bridge, 'agents', agents), patch.object(mcp_bridge, '_authenticated_instance', return_value=two):
                self.assertIn('Error:', mcp_bridge.chat_queue_release('a' * 32))
            with patch.object(mcp_bridge, 'agents', agents), patch.object(mcp_bridge, '_authenticated_instance', return_value=one):
                self.assertIn('released', mcp_bridge.chat_queue_release('a' * 32))
            self.assertEqual(agents.queue.owned(one, 'a' * 32)['state'], 'released')

    def test_scoped_claim_ack_release_and_strict_transport_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = RuntimeRegistry(directory)
            registry.seed({'one': {}, 'two': {}})
            one, two = registry.register('one'), registry.register('two')
            agents = AgentTrigger(registry, directory)
            agents.trigger_sync('one', channel='general', dispatch_id='a' * 32)
            api = FastAPI()
            with patch.object(app, 'app', api):
                app._install_security_middleware('operator-test', {'server': {'port': 18300}})
            api.add_api_route('/api/queue/{operation}', app.dispatch_operation, methods=['POST'])
            api.add_api_route('/api/queue/status', app.dispatch_status, methods=['GET'])
            client = TestClient(api, client=('127.0.0.1', 40000))
            owner = {'Authorization': 'Bearer ' + one['token']}
            peer = {'Authorization': 'Bearer ' + two['token']}
            with patch.object(app, 'registry', registry), patch.object(app, 'agents', agents):
                self.assertEqual(client.post('/api/queue/claim', json={'consumer_id': 'worker'}).status_code, 403)
                claimed = client.post('/api/queue/claim', json={'consumer_id': 'worker'}, headers=owner)
                self.assertEqual(claimed.status_code, 200)
                self.assertEqual(claimed.json()['dispatch']['envelope']['dispatch_id'], 'a' * 32)
                self.assertEqual(client.post('/api/queue/claim', json={'consumer_id': 'other'}, headers=owner).status_code, 409)
                body = {'dispatch_id': 'a' * 32, 'consumer_id': 'worker'}
                self.assertEqual(client.post('/api/queue/ack', json=body, headers=peer).status_code, 403)
                self.assertEqual(client.post('/api/queue/ack', json=body, headers=owner).status_code, 200)
                self.assertEqual(client.post('/api/queue/release', json={**body, 'result': 'must not admit output'}, headers=owner).status_code, 400)
                self.assertEqual(client.post('/api/queue/release', json=body, headers=owner).status_code, 200)
                self.assertIsNone(client.post('/api/queue/claim', json={'consumer_id': 'worker'}, headers=owner).json()['dispatch'])
                self.assertEqual(client.get('/api/queue/status', headers=peer).status_code, 403)
                status = client.get('/api/queue/status', headers={'x-session-token': 'operator-test'})
                self.assertEqual(status.status_code, 200)
                self.assertNotIn(one['token'], status.text)
