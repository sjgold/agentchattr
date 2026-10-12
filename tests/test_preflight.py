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


if __name__ == '__main__':
    unittest.main()
