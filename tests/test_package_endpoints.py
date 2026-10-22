from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app
from api_seats import SeatStore, package_revision
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry


class PackageEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {'server': {'port': 18300, 'data_dir': self.tmp.name}}
        self.store = SeatStore(self.tmp.name, {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:1/v1'}})
        self.pkg = {'id': 'team', 'name': 'Team', 'seats': [{'id': 'one', 'name': 'One',
                    'adapter': 'openai-compatible', 'provider': 'fake', 'model': 'one',
                    'reasoning': None, 'launch_profile': 'standard', 'secret_ref': 'MISSING_PACKAGE_TEST_SECRET'}]}
        self.store.save(self.pkg)
        self.manager = SeatManager(Path(app.__file__).parent, self.cfg, self.store,
                                   RuntimeRegistry(self.tmp.name), monitor=False)
        self.addCleanup(self.manager.shutdown)
        self.api = FastAPI()
        with patch.object(app, 'app', self.api):
            app._install_security_middleware('package-test-token', self.cfg)
        self.api.add_api_route('/api/preflight/packages/{package_id}/launch', app.launch_saved_package, methods=['POST'])
        self.api.add_api_route('/api/preflight/packages/{package_id}/status', app.get_package_status)
        self.api.add_api_route('/api/preflight/packages/{package_id}/chat', app.continue_saved_package, methods=['POST'])
        self.client = TestClient(self.api, client=('127.0.0.1', 40000))
        self.headers = {'x-session-token': 'package-test-token'}

    def test_authentication_origin_and_strict_launch_body(self):
        with patch.object(app, 'api_seat_manager', self.manager):
            route = '/api/preflight/packages/team/launch'
            self.assertEqual(self.client.post(route, json={}).status_code, 403)
            self.assertEqual(self.client.post(route, json={'revision': package_revision(self.pkg)},
                headers={**self.headers, 'Origin': 'https://example.invalid'}).status_code, 403)
            for body in ({}, {'revision': []}, {'revision': package_revision(self.pkg), 'unknown': True}):
                self.assertEqual(self.client.post(route, json=body, headers=self.headers).status_code, 400)

    def test_missing_credential_team_cannot_handoff_to_chat(self):
        with patch.object(app, 'api_seat_manager', self.manager), patch.dict('os.environ', {}, clear=True):
            route = '/api/preflight/packages/team'
            result = self.client.post(route + '/launch', json={'revision': package_revision(self.pkg)}, headers=self.headers)
            self.assertEqual(result.status_code, 200)
            self.assertFalse(result.json()['ready'])
            self.assertEqual(result.json()['seats']['one']['state'], 'action_required')
            self.assertEqual(self.client.get(route + '/status', headers=self.headers).status_code, 200)
            self.assertEqual(self.client.post(route + '/chat', json={'selection_id': result.json()['selection_id']},
                headers=self.headers).status_code, 409)

    def test_routes_registered_on_actual_app(self):
        paths = {route.path for route in app.app.routes}
        for suffix in ('launch', 'status', 'chat'):
            self.assertIn('/api/preflight/packages/{package_id}/' + suffix, paths)
