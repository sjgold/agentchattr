"""A failed queue publication must not strand unrelated seats after selection."""
import unittest
from unittest.mock import patch
import uuid

from tests import test_dispatch_queue as queue_fixture
from tests import test_result_owner_wiring as fixture


class CLIMissingDispatchTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)

    def test_selected_unpublished_dispatch_does_not_block_a_peer_claim(self):
        owner, _ = self.fixture.ready('cli')
        peer, _ = self.fixture.ready('api')
        with patch.object(self.trigger.queue, 'enqueue', side_effect=OSError('queue publication failed')):
            self.assertIsNone(fixture.ResultOwnerWiringTests.start(self, owner['name']))
        run = self.sessions.list_all()[0]
        self.assertEqual(run['state'], 'interrupted')
        self.assertTrue(run['active_invocation'])
        message = self.engine.send_chat(owner, 'Explicitly selected legacy answer', channel=run['channel'])
        candidate = self.engine.cli_message_candidate(run['id'], message['id'])
        self.sessions.admit_selected_cli_event(run['id'], self.messages.get_snapshot(message['id']),
            request_id=uuid.uuid4().hex, confirm_operator_attribution=True,
            **{key: candidate[key] for key in ('message_uid', 'snapshot_hash', 'checkpoint')})
        expected = self.trigger.queue._queue.enqueue(peer, queue_fixture.envelope(job_id=73))
        claimed = self.trigger.queue.claim(peer, 'peer-consumer')
        self.assertEqual(claimed['envelope'], expected['envelope'])
