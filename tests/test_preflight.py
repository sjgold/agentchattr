import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from launcher import instance_identity


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {'server': {'port': 18300, 'data_dir': './data'},
                    'agents': {'api': {'type': 'api', 'api_key_env': 'EXAMPLE_SECRET'}}}
        self.assertTrue(hasattr(app, 'get_health'), 'app health endpoint missing')
        self.assertTrue(hasattr(app, 'get_preflight'), 'preflight endpoint missing')
        self.config_patch = patch.object(app, 'config', self.cfg)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.api = FastAPI()
        with patch.object(app, 'app', self.api):
            app._install_security_middleware('test-session-token', self.cfg)
        self.api.add_api_route('/api/health', app.get_health)
        self.api.add_api_route('/api/preflight', app.get_preflight)
        self.client = TestClient(self.api, client=('127.0.0.1', 40000))

    def test_health_is_public_loopback_and_identifies_instance(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['app'], 'agentchattr')
        self.assertEqual(data['identity'], instance_identity(Path(app.__file__).parent, self.cfg))
        self.assertNotIn('token', response.text)

    def test_preflight_requires_authentication_and_does_not_expose_secret_refs(self):
        self.assertEqual(self.client.get('/api/preflight').status_code, 403)
        response = self.client.get('/api/preflight', headers={'x-session-token': 'test-session-token'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('EXAMPLE_SECRET', response.text)
        self.assertEqual(response.json()['agents'][0]['authentication'], 'unknown')

    def test_health_rejects_remote_clients(self):
        client = TestClient(self.api, client=('192.0.2.3', 40000))
        self.assertEqual(client.get('/api/health').status_code, 403)

    def test_endpoints_registered_on_actual_app(self):
        paths = {route.path for route in app.app.routes}
        self.assertIn('/api/health', paths)
        self.assertIn('/api/preflight', paths)

    def test_managed_seat_endpoints_require_session_token(self):
        for function in ('get_api_seats', 'save_api_package', 'launch_api_seat', 'stop_api_seat'):
            self.assertTrue(hasattr(app, function), f'{function} endpoint missing')
        self.api.add_api_route('/api/preflight/seats', app.get_api_seats)
        self.api.add_api_route('/api/preflight/packages', app.save_api_package, methods=['POST'])
        self.assertEqual(self.client.get('/api/preflight/seats').status_code, 403)
        self.assertEqual(self.client.post('/api/preflight/packages', json={}).status_code, 403)

    def test_package_api_validation_roundtrip_and_missing_credential_state(self):
        import tempfile
        from api_seats import SeatStore
        from api_seat_runtime import SeatManager
        from registry import RuntimeRegistry
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root / '.audit-tmp') as temporary:
            store = SeatStore(temporary, {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1'}})
            manager = SeatManager(root, self.cfg, store, RuntimeRegistry(temporary), monitor=False)
            self.addCleanup(manager.shutdown)
            self.api.add_api_route('/api/preflight/seats', app.get_api_seats)
            self.api.add_api_route('/api/preflight/packages', app.save_api_package, methods=['POST'])
            self.api.add_api_route('/api/preflight/seats/{package_id}/{seat_id}/launch', app.launch_api_seat, methods=['POST'])
            headers = {'x-session-token': 'test-session-token'}
            package = {'id': 'team', 'name': 'Team', 'seats': [{'id': 'writer', 'name': 'Writer',
                       'adapter': 'openai-compatible', 'provider': 'fake', 'model': 'requested',
                       'reasoning': None, 'launch_profile': 'standard', 'secret_ref': 'MISSING_TEST_SECRET'}]}
            with patch.object(app, 'api_seat_store', store), patch.object(app, 'api_seat_manager', manager):
                self.assertEqual(self.client.post('/api/preflight/packages', json=[], headers=headers).status_code, 400)
                self.assertEqual(self.client.post('/api/preflight/packages', json={**package, 'api_key': 'never-save'}, headers=headers).status_code, 400)
                self.assertEqual(self.client.post('/api/preflight/packages', json=package, headers={**headers, 'Origin': 'https://example.invalid'}).status_code, 403)
                self.assertEqual(self.client.post('/api/preflight/packages', json=package, headers=headers).status_code, 200)
                result = self.client.get('/api/preflight/seats', headers=headers)
                self.assertEqual(result.json()['packages'], [package])
                path = '/api/preflight/seats/team/writer/launch'
                self.assertEqual(self.client.post(path, json={'restart': 'yes'}, headers=headers).status_code, 409)
                with patch.dict('os.environ', {}, clear=True):
                    result = self.client.post(path, json={}, headers=headers)
                self.assertEqual(result.json()['state'], 'action_required')
                self.assertIsNone(result.json()['confirmed_model'])


if __name__ == '__main__':
    unittest.main()
