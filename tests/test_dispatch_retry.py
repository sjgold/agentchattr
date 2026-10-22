"""Retry cancellation changes one dispatch while retaining uncertain ownership."""
from pathlib import Path
import tempfile
import unittest

from dispatch_queue import QueueBusy, QueueStore
from tests.test_dispatch_queue import envelope


class DispatchRetryTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('.audit-tmp')
        scratch.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.queue = QueueStore(temporary.name)
        self.owner = {'name': 'one', 'identity_id': 'identity-one'}
        self.peer = {'name': 'two', 'identity_id': 'identity-two'}
        self.first = self.queue.enqueue(self.owner, envelope())
        self.following = self.queue.enqueue(self.owner, envelope())
        self.other = self.queue.enqueue(self.peer, envelope())

    def test_queued_retry_cancels_only_the_named_dispatch(self):
        dispatch = self.first['envelope']['dispatch_id']
        self.assertEqual(self.queue.cancel_dispatch(dispatch, 'retry-one')['state'], 'cancelled')
        self.assertEqual(self.queue.owned(self.owner, self.following['envelope']['dispatch_id']), self.following)
        self.assertEqual(self.queue.owned(self.peer, self.other['envelope']['dispatch_id']), self.other)

    def test_claimed_retry_holds_ownership_until_actual_local_end(self):
        self.queue.claim(self.owner, 'worker')
        dispatch = self.first['envelope']['dispatch_id']
        self.assertEqual(self.queue.cancel_dispatch(dispatch, 'retry-one')['state'], 'cancelling')
        with self.assertRaises(QueueBusy):
            self.queue.claim(self.owner, 'new-worker')
        self.assertEqual(self.queue.claim(self.owner, 'worker')['envelope']['dispatch_id'], dispatch)
        self.queue.cancellation_receipt(self.owner, dispatch, 'worker', 'local_ended')
        self.assertEqual(self.queue.claim(self.owner, 'new-worker')['envelope'], self.following['envelope'])
