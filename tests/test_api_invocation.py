"""Real owned HTTP children, cancellation and secret-safe failure boundaries."""
import importlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class APIInvocationTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('api_invocation')
        self.entered = threading.Event()
        self.release = threading.Event()
        self.requests = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'alive')

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.requests.append((payload, self.headers.get('Authorization')))
                fixture.entered.set()
                if payload.get('model') == 'reject':
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'credential-sensitive-provider-body')
                    return
                data = json.dumps({'model': 'confirmed', 'choices': [
                    {'message': {'content': '' if payload.get('model') == 'empty' else 'Exact café\r\n' + 'x' * (512 * 1024)}}]}, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data[:1])
                    self.wfile.flush()
                    if payload.get('model') == 'blocked':
                        fixture.release.wait(8)
                    self.wfile.write(data[1:])
                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.release.set)
        self.provider = {'type': 'api', 'base_url': f'http://127.0.0.1:{self.server.server_port}/v1'}
        self.seat = {'id': 'api', 'name': 'API', 'adapter': 'openai-compatible',
                     'provider': 'local', 'model': 'requested', 'reasoning': None,
                     'launch_profile': 'standard', 'secret_ref': 'INVOCATION_TEST_KEY'}

    def test_real_child_preserves_large_source_payload_result_and_credential_header(self):
        messages = [{'role': 'user', 'content': 'café\r\n' + 'z' * (512 * 1024)}]
        with patch.dict(os.environ, INVOCATION_TEST_KEY='stdin-only-secret'):
            result = self.module.run_completion(self.seat, self.provider, messages, lambda: False, timeout=5)
        self.assertEqual(result, {'content': 'Exact café\r\n' + 'x' * (512 * 1024), 'confirmed_model': 'confirmed'})
        self.assertEqual(self.requests[0][0]['messages'], messages)
        self.assertEqual(self.requests[0][0]['model'], 'requested')
        self.assertEqual(self.requests[0][1], 'Bearer stdin-only-secret')

    def test_cancel_ends_blocked_owned_child_before_provider_progress_and_peer_health_survives(self):
        import urllib.request
        seat = {**self.seat, 'model': 'blocked', 'secret_ref': ''}
        started = []
        def cancellation():
            if self.entered.is_set():
                if not started:
                    started.append(time.monotonic())
                return True
            return False
        with self.assertRaises(self.module.InvocationCancelled) as caught:
            self.module.run_completion(seat, self.provider, [], cancellation, timeout=5)
        self.assertTrue(caught.exception.local_ended)
        self.assertLess(time.monotonic() - started[0], 3)
        self.assertFalse(self.release.is_set())
        with urllib.request.urlopen(f'http://127.0.0.1:{self.server.server_port}/health', timeout=2) as response:
            self.assertEqual(response.read(), b'alive')

    def test_pre_cancel_does_not_spawn_or_send(self):
        with patch('api_invocation.subprocess.Popen') as spawn:
            with self.assertRaises(self.module.InvocationCancelled):
                self.module.run_completion(self.seat, self.provider, [], lambda: True)
        spawn.assert_not_called()
        self.assertEqual(self.requests, [])

    def test_provider_error_reports_status_without_body_or_secret(self):
        with patch.dict(os.environ, INVOCATION_TEST_KEY='stdin-only-secret'):
            with self.assertRaises(self.module.InvocationFailure) as caught:
                self.module.run_completion({**self.seat, 'model': 'reject'}, self.provider, [], lambda: False)
        self.assertEqual(caught.exception.http_status, 401)
        self.assertNotIn('stdin-only-secret', str(caught.exception))
        self.assertNotIn('credential-sensitive-provider-body', str(caught.exception))

    def test_empty_completion_keeps_its_sanitized_category_across_real_child_ipc(self):
        with self.assertRaises(self.module.InvocationFailure) as caught:
            self.module.run_completion({**self.seat, 'model': 'empty', 'secret_ref': ''}, self.provider, [], lambda: False)
        self.assertEqual(caught.exception.category, 'empty_completion')
        self.assertIsNone(caught.exception.http_status)
        self.assertEqual(len(self.requests), 1)

    def test_whole_seat_stop_signals_supervisor_without_premature_exit_receipt(self):
        from api_seats import Receipt, atomic_json
        with tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp') as directory:
            receipt = Receipt(Path(directory) / 'receipt.json', 'owned-launch')
            receipt.update(state='ready')
            requested = threading.Event()
            receipt.watch_for_stop(on_stop=requested.set)
            atomic_json(Path(directory) / 'stop.json', {'attempt': 'owned-launch'})
            self.assertTrue(requested.wait(2))
            self.assertEqual(receipt.value['state'], 'ready', 'Only supervisor cleanup may claim ended.')

    def test_unproven_child_exit_remains_unresolved_without_repeating_cleanup_budget(self):
        process = Mock()
        process.poll.return_value = None
        checks = iter((False, True))
        with patch('api_invocation.subprocess.Popen', return_value=process), patch('api_invocation.threading.Thread'):
            with self.assertRaises(self.module.InvocationCancelled) as caught:
                self.module.run_completion({**self.seat, 'secret_ref': ''}, self.provider, [], lambda: next(checks))
        self.assertFalse(caught.exception.local_ended)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()

    def test_timeout_does_not_report_ordinary_failure_when_owned_process_is_still_alive(self):
        process = Mock()
        process.poll.return_value = None
        with patch('api_invocation.subprocess.Popen', return_value=process), patch('api_invocation.threading.Thread'):
            with self.assertRaises(self.module.InvocationCancelled) as caught:
                self.module.run_completion({**self.seat, 'secret_ref': ''}, self.provider, [], lambda: False, timeout=0)
        self.assertFalse(caught.exception.local_ended)


if __name__ == '__main__':
    unittest.main()
