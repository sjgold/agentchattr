import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class APISeatConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'api_seats.py').exists(), 'API-seat configuration module missing')
        self.module = importlib.import_module('api_seats')
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(self.tmp.cleanup)
        self.providers = {'local': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1',
                                    'model': 'default-model', 'reasoning_efforts': ['high']}}
        self.store = self.module.SeatStore(Path(self.tmp.name), self.providers)
        self.package = {'id': 'team', 'name': 'Team', 'seats': [
            {'id': 'analyst', 'name': 'Analyst', 'adapter': 'openai-compatible',
             'provider': 'local', 'model': 'manual-model', 'reasoning': 'high',
             'launch_profile': 'standard', 'secret_ref': 'LOCAL_KEY'}]}

    def test_roundtrip_and_two_seats_using_one_provider(self):
        self.package['seats'].append({**self.package['seats'][0], 'id': 'writer', 'model': None})
        self.store.save(self.package)
        self.assertEqual(self.module.SeatStore(Path(self.tmp.name), self.providers).list(), [self.package])

    def test_unsupported_settings_and_literal_secrets_rejected(self):
        for change in ({'reasoning': 'maximum'}, {'api_key': 'do-not-save'},
                       {'adapter': 'shell'}, {'launch_profile': 'sudo'}, {'model': 42},
                       {'secret_ref': 'not a variable'}, {'provider': 'unknown'}):
            with self.subTest(change=change), self.assertRaises(self.module.SeatError):
                self.store.save({**self.package, 'seats': [{**self.package['seats'][0], **change}]})
        self.assertFalse((Path(self.tmp.name) / 'api_seats.json').exists())

    def test_malformed_storage_is_not_replaced(self):
        path = Path(self.tmp.name) / 'api_seats.json'
        path.write_text('{broken')
        with self.assertRaises(self.module.SeatError):
            self.store.save(self.package)
        self.assertEqual(path.read_text(), '{broken')

    def test_replacement_backs_up_valid_previous_package(self):
        self.store.save(self.package)
        changed = {**self.package, 'name': 'Changed'}
        self.store.save(changed)
        backups = list(Path(self.tmp.name).glob('api_seats.*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text())['packages'], [self.package])

    def test_payload_settings_and_confirmation_are_independent(self):
        seat = self.package['seats'][0]
        payload = self.module.build_payload(seat, self.providers['local'], [{'role': 'user', 'content': 'hello'}])
        self.assertEqual(payload['model'], 'manual-model')
        self.assertEqual(payload['reasoning_effort'], 'high')
        payload = self.module.build_payload({**seat, 'model': None, 'reasoning': None}, self.providers['local'], [])
        self.assertNotIn('model', payload)
        self.assertNotIn('reasoning_effort', payload)

    def test_real_http_payload_and_provider_receipt(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(inner):
                captured.append(json.loads(inner.rfile.read(int(inner.headers['Content-Length']))))
                inner.send_response(200)
                inner.end_headers()
                inner.wfile.write(json.dumps({'model': 'provider-reported-model', 'choices': [
                    {'message': {'content': 'test reply'}}]}).encode())
            def log_message(*args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        provider = {**self.providers['local'], 'base_url': f'http://127.0.0.1:{server.server_port}/v1'}
        seat = {**self.package['seats'][0], 'secret_ref': ''}
        self.assertTrue(hasattr(self.module, 'request_completion'), 'shared API request path missing')
        result = self.module.request_completion(seat, provider, [{'role': 'user', 'content': 'hello'}], timeout=2)
        self.assertEqual(captured[0]['model'], seat['model'])
        self.assertEqual(captured[0]['reasoning_effort'], 'high')
        self.assertEqual(result, {'content': 'test reply', 'confirmed_model': 'provider-reported-model'})

    def test_atomic_replacement_tolerates_transient_windows_reader_lock(self):
        path = Path(self.tmp.name) / 'receipt.json'
        self.module.atomic_json(path, {'state': 'starting'})
        original = Path.replace
        calls = []
        def locked_once(source, target):
            calls.append(1)
            if len(calls) == 1:
                raise PermissionError('simulated Windows reader sharing lock')
            return original(source, target)
        with patch.object(Path, 'replace', autospec=True, side_effect=locked_once):
            self.module.atomic_json(path, {'state': 'ready'})
        self.assertEqual(json.loads(path.read_text()), {'state': 'ready'})

    def test_permanent_replacement_failure_preserves_previous_file_and_is_bounded(self):
        import time
        path = Path(self.tmp.name) / 'receipt.json'
        self.module.atomic_json(path, {'state': 'starting'})
        started = time.monotonic()
        with patch.object(Path, 'replace', side_effect=PermissionError('persistent permission failure')):
            with self.assertRaises(PermissionError):
                self.module.atomic_json(path, {'state': 'ready'})
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(json.loads(path.read_text()), {'state': 'starting'})

    def test_malformed_provider_urls_and_secret_reference_are_rejected_safely(self):
        for url in ('https://[broken/v1', 'https://example.invalid:bad/v1',
                    'https://user:secret@example.invalid/v1', 'https://example.invalid/v1?key=secret'):
            with self.subTest(url=url), self.assertRaises(self.module.SeatError):
                self.module.validate_provider({'base_url': url})
        with self.assertRaises(self.module.SeatError):
            self.module.validate_provider({'base_url': 'https://example.invalid/v1', 'api_key_env': 'not-an-env-reference'})


if __name__ == '__main__':
    unittest.main()
