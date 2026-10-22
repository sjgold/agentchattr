import unittest
from unittest.mock import Mock


class CliDispatchConsumerTests(unittest.TestCase):
    def test_fast_cooperative_release_before_injection_returns_retains_ack_history(self):
        import tempfile
        from dispatch_queue import QueueStore
        from queue_client import CliConsumer
        with tempfile.TemporaryDirectory() as directory:
            queue = QueueStore(directory)
            seat = {'name': 'seat', 'identity_id': 'a' * 32}
            queue.enqueue(seat, {'dispatch_id': 'b' * 32})
            queue.enqueue(seat, {'dispatch_id': 'c' * 32})
            client = Mock()
            client.claim.side_effect = lambda: queue.claim(seat, 'worker')
            client.acknowledge.side_effect = lambda dispatch: queue.acknowledge(seat, dispatch, 'worker')
            client.uncertain.side_effect = lambda dispatch: queue.uncertain(seat, dispatch, 'worker')
            def inject(dispatch):
                queue.release(seat, dispatch, 'worker')
            consumer = CliConsumer(client, inject, lambda envelope: envelope['dispatch_id'])
            consumer.poll()
            first = queue.owned(seat, 'b' * 32)
            self.assertEqual(first['state'], 'released')
            self.assertEqual([e['state'] for e in first['events']],
                             ['queued', 'dispatched', 'acknowledged', 'released'])
            consumer.poll()
            self.assertEqual(queue.owned(seat, 'c' * 32)['state'], 'released')
            client.uncertain.assert_not_called()

    def test_repeated_claim_does_not_reinject_and_release_allows_next(self):
        from queue_client import CliConsumer
        client = Mock()
        one = {'envelope': {'dispatch_id': 'a' * 32, 'channel': 'alpha'}}
        two = {'envelope': {'dispatch_id': 'b' * 32, 'channel': 'beta'}}
        client.claim.side_effect = [one, one, two]
        inject = Mock()
        consumer = CliConsumer(client, inject, lambda e: e['channel'])
        consumer.poll()
        consumer.poll()
        self.assertEqual(inject.call_count, 1)
        consumer.poll()
        self.assertEqual([c.args[0] for c in inject.call_args_list], ['alpha', 'beta'])
        self.assertEqual(client.acknowledge.call_count, 2)
        client.release.assert_not_called()

    def test_injection_failure_retains_uncertainty_without_retry(self):
        from queue_client import CliConsumer
        client = Mock()
        client.claim.return_value = {'envelope': {'dispatch_id': 'a' * 32}}
        inject = Mock(return_value=False)
        consumer = CliConsumer(client, inject, lambda e: 'prompt')
        with self.assertRaises(RuntimeError):
            consumer.poll()
        consumer.poll()
        self.assertEqual(inject.call_count, 1)
        client.uncertain.assert_called_once_with('a' * 32)
        client.acknowledge.assert_not_called()
