"""A missing server observation cannot terminate an owned in-flight model."""
import threading
import unittest
import urllib.error
from unittest.mock import Mock

import wrapper_api


class RestartCancellationPollTests(unittest.TestCase):
    def test_unavailable_poll_does_not_imply_cancellation(self):
        for failure in (urllib.error.URLError('offline'), TimeoutError(),
                        urllib.error.HTTPError('http://127.0.0.1', 409, 'boot fence', {}, None),
                        urllib.error.HTTPError('http://127.0.0.1', 503, 'starting', {}, None), ValueError('invalid JSON')):
            with self.subTest(failure=type(failure).__name__):
                queue = Mock()
                queue.claim.side_effect = failure
                self.assertFalse(wrapper_api._cancellation_requested(queue, 'dispatch', threading.Event()))

    def test_only_exact_positive_cancelling_receipt_ends_the_invocation(self):
        queue = Mock()
        for current, expected in ((None, False),
                ({'envelope': {'dispatch_id': 'other'}, 'state': 'cancelling'}, False),
                ({'envelope': {'dispatch_id': 'dispatch'}, 'state': 'acknowledged'}, False),
                ({'envelope': {'dispatch_id': 'dispatch'}, 'state': 'cancelling'}, True)):
            queue.claim.return_value = current
            self.assertEqual(wrapper_api._cancellation_requested(queue, 'dispatch', threading.Event()), expected)

    def test_local_shutdown_still_cancels_without_waiting_on_the_server(self):
        shutdown, queue = threading.Event(), Mock()
        shutdown.set()
        self.assertTrue(wrapper_api._cancellation_requested(queue, 'dispatch', shutdown))
        queue.claim.assert_not_called()

    def test_actual_held_model_survives_failed_polls_and_returns_one_response(self):
        from tests.test_api_invocation import APIInvocationTests
        fixture = APIInvocationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        outages = []
        queue = Mock()
        def claim():
            if fixture.entered.is_set() and len(outages) < 3:
                outages.append(True)
                raise urllib.error.URLError('temporary server outage')
            if len(outages) == 3:
                fixture.release.set()
            return {'envelope': {'dispatch_id': 'dispatch'}, 'state': 'acknowledged'}
        queue.claim.side_effect = claim
        shutdown = threading.Event()
        result = fixture.module.run_completion({**fixture.seat, 'model': 'blocked', 'secret_ref': ''},
            fixture.provider, [], lambda: wrapper_api._cancellation_requested(queue, 'dispatch', shutdown), timeout=5)
        self.assertEqual(len(outages), 3)
        self.assertEqual(len(fixture.requests), 1)
        self.assertTrue(result['content'].startswith('Exact café'))
