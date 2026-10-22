"""Authenticated failure receipts expose sanitized turn failures immediately."""
from contextlib import ExitStack
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app


class RecoveryTransportTests(unittest.TestCase):
    def setUp(self):
        from tests.test_turn_recovery import TurnRecoveryTests
        self.f = TurnRecoveryTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-test', {'server': {'port': 18300}})
        api.add_api_route('/api/queue/{operation}', app.dispatch_operation, methods=['POST'])
        self.client = TestClient(api, client=('127.0.0.1', 40000))
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in (('registry', self.f.registry), ('agents', self.f.trigger), ('session_engine', self.f.engine)):
            self.stack.enter_context(patch.object(app, name, value))
        self.headers = {'Authorization': 'Bearer ' + self.f.owner['token']}
        self.f.queue.claim(self.f.owner, 'worker')
        self.body = {'dispatch_id': self.f.original['dispatch_id'], 'consumer_id': 'worker', 'failed': True}

    def test_http_failure_is_a_durable_checkpoint_before_deadline(self):
        response = self.client.post('/api/queue/release', json={**self.body,
            'error_category': 'http_error', 'http_status': 503}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        current = self.f.current()
        self.assertEqual(current['state'], 'stalled')
        self.assertEqual(current['turn_recovery']['reason'], 'http_error')
        self.assertEqual(current['turn_recovery']['http_status'], 503)
        self.assertEqual(current['admitted_events'], [])
        self.assertEqual((current['current_phase'], current['current_turn']), (0, 0))

    def test_empty_completion_reports_failure_without_a_fabricated_answer(self):
        response = self.client.post('/api/queue/release', json={**self.body,
            'error_category': 'empty_completion'}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.f.current()['turn_recovery']['reason'], 'empty_completion')
        self.assertFalse(self.f.current()['turn_recovery']['recoverable_result'])
        self.assertEqual(self.f.current()['admitted_events'], [])

    def test_bad_status_or_raw_error_never_mutates_or_leaks_the_receipt(self):
        ledger = self.f.root / 'queue/ledger.json'
        before = ledger.read_bytes()
        for status in (None, True, '503', 99, 600, {'secret': self.f.owner['token']}):
            with self.subTest(status=status):
                response = self.client.post('/api/queue/release', json={**self.body,
                    'error_category': 'http_error', 'http_status': status}, headers=self.headers)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn(self.f.owner['token'], response.text)
                self.assertEqual(ledger.read_bytes(), before)
        response = self.client.post('/api/queue/release', json={**self.body,
            'error_category': self.f.owner['token']}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(self.f.owner['token'], response.text)
        self.assertEqual(ledger.read_bytes(), before)

    def test_failure_categories_are_text_and_only_valid_for_failed_release(self):
        ledger = self.f.root / 'queue/ledger.json'
        before = ledger.read_bytes()
        for category in (None, False, 0, [], {}):
            with self.subTest(category=category):
                response = self.client.post('/api/queue/release', json={**self.body,
                    'error_category': category}, headers=self.headers)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(ledger.read_bytes(), before)
        response = self.client.post('/api/queue/release', json={**self.body, 'failed': False,
            'error_category': 'http_error'}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ledger.read_bytes(), before)
