from pathlib import Path
import re
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
import app

ROOT = Path(__file__).resolve().parents[1]

class AssetCacheIsolationTests(unittest.TestCase):
    def test_core_url_does_not_reuse_the_desktop_generation(self):
        html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
        self.assertNotIn('/static/core.js?v=223', html)

    def test_static_assets_cannot_be_reused_across_installations(self):
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('test', {'server': {'host':'127.0.0.1','port':8300}})
        api.mount('/static', StaticFiles(directory=str(ROOT / 'static')))
        with TestClient(api) as client:
            response = client.get('/static/core.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertIn('function agentDisplayName', response.text)
