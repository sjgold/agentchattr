"""Authenticated heartbeat ownership forwarding through real security middleware."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
import mcp_bridge
from registry import RuntimeRegistry


class RuntimeHeartbeatTests(unittest.TestCase):
    def setUp(self):
        Path('.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir='.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.registry = RuntimeRegistry(temporary.name)
        self.registry.seed({'seat0': {'type': 'api'}, 'seat1': {'type': 'api'}})
        self.owner = self.registry.register('seat0')
        self.peer = self.registry.register('seat1')
        self.headers = {'Authorization': 'Bearer ' + self.owner['token']}
        self.boot = uuid.uuid4().hex
        self.manager = Mock(spec=['observe_runtime_heartbeat'])
        self.manager.observe_runtime_heartbeat.return_value = {'boot_id': self.boot, 'verified': True, 'reason': 'verified'}
        self.payload = {'attempt': uuid.uuid4().hex, 'launch_nonce': uuid.uuid4().hex,
            'server_identity': 'a' * 64, 'boot_id': self.boot, 'worker_pid': 123,
            'creation_filetime': '133748291234567890', 'worker_root': 'fixture-only-payload'}
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-fixture-token', {'server': {'port': 18300}})
        api.add_api_route('/api/heartbeat/{agent_name}', app.heartbeat, methods=['POST'])
        self.client = TestClient(api, client=('127.0.0.1', 40000))
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(app, 'registry', self.registry))
        stack.enter_context(patch.object(app, 'api_seat_manager', self.manager))
        self.broadcast = stack.enter_context(patch.object(app, 'broadcast_status', new_callable=AsyncMock))
        stack.enter_context(patch.object(mcp_bridge, '_presence', {}))
        stack.enter_context(patch.object(mcp_bridge, '_activity', {}))
        stack.enter_context(patch.object(mcp_bridge, '_activity_ts', {}))

    def test_real_bearer_forwards_only_authenticated_principal_and_runtime_payload(self):
        response = self.client.post('/api/heartbeat/' + self.peer['name'], headers=self.headers,
            json={'runtime_ownership': self.payload, 'name': self.peer['name'],
                  'principal': self.peer, 'identity_id': self.peer['identity_id']})
        self.assertEqual(response.status_code, 200)
        self.manager.observe_runtime_heartbeat.assert_called_once_with(self.registry.resolve_token(self.owner['token']), self.payload)
        self.assertEqual(response.json()['name'], self.owner['name'])
        self.assertEqual(response.json()['runtime_ownership'], self.manager.observe_runtime_heartbeat.return_value)

    def test_boot_challenge_is_returned_without_claiming_verification(self):
        self.manager.observe_runtime_heartbeat.return_value = {'boot_id': self.boot, 'verified': False, 'reason': 'boot_challenge'}
        payload = {**self.payload, 'boot_id': None}
        response = self.client.post('/api/heartbeat/' + self.owner['name'], headers=self.headers,
                                    json={'runtime_ownership': payload})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['runtime_ownership'], {'boot_id': self.boot, 'verified': False, 'reason': 'boot_challenge'})
        self.manager.observe_runtime_heartbeat.assert_called_once_with(self.registry.resolve_token(self.owner['token']), payload)

    def test_unauthed_manual_or_agent_heartbeat_never_invokes_adoption(self):
        agent = self.client.post('/api/heartbeat/' + self.owner['name'], json={'runtime_ownership': self.payload})
        self.assertEqual(agent.status_code, 403)
        manual = self.client.post('/api/heartbeat/manual-visitor', json={'runtime_ownership': self.payload})
        self.assertEqual(manual.status_code, 200)
        self.assertEqual(manual.json()['name'], 'manual-visitor')
        self.assertNotIn('runtime_ownership', manual.json())
        self.manager.observe_runtime_heartbeat.assert_not_called()

    def test_invalid_and_revoked_bearers_remain_stale_409_without_adoption(self):
        invalid = self.client.post('/api/heartbeat/' + self.owner['name'],
            headers={'Authorization': 'Bearer invalid-fixture-token'}, json={'runtime_ownership': self.payload})
        self.assertEqual(invalid.status_code, 409)
        self.registry.deregister(self.owner['name'])
        revoked = self.client.post('/api/heartbeat/' + self.owner['name'], headers=self.headers,
                                    json={'runtime_ownership': self.payload})
        self.assertEqual(revoked.status_code, 409)
        self.manager.observe_runtime_heartbeat.assert_not_called()

    def test_ordinary_bearer_heartbeat_preserves_presence_activity_without_adoption(self):
        response = self.client.post('/api/heartbeat/' + self.owner['name'], headers=self.headers, json={'active': True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(response.json()['name'], self.owner['name'])
        self.assertIn(self.owner['name'], mcp_bridge._presence)
        self.assertTrue(mcp_bridge._activity[self.owner['name']])
        self.broadcast.assert_awaited_once()
        self.manager.observe_runtime_heartbeat.assert_not_called()


if __name__ == '__main__':
    unittest.main()
