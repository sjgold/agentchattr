"""A failed queue publication must not strand unrelated seats after selection."""
import unittest
from unittest.mock import patch
import uuid
from pathlib import Path
import threading

from dispatch_queue import QueueBusy, QueueStore
from queue_coordinator import CoordinatedQueue
from session_store import SessionStore
from tests import test_dispatch_queue as queue_fixture
from tests import test_result_owner_wiring as fixture


class CLIMissingDispatchTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)

    def selected_missing(self, before_admit=None):
        owner, _ = self.fixture.ready('cli')
        peer, _ = self.fixture.ready('api')
        with patch.object(self.trigger.queue, 'enqueue', side_effect=OSError('queue publication failed')):
            self.assertIsNone(fixture.ResultOwnerWiringTests.start(self, owner['name']))
        run = self.sessions.list_all()[0]
        self.assertEqual(run['state'], 'interrupted')
        self.assertTrue(run['active_invocation'])
        message = self.engine.send_chat(owner, 'Explicitly selected legacy answer', channel=run['channel'])
        candidate = self.engine.cli_message_candidate(run['id'], message['id'])
        if before_admit:
            before_admit(owner)
        request = uuid.uuid4().hex
        self.sessions.admit_selected_cli_event(run['id'], self.messages.get_snapshot(message['id']),
            request_id=request, confirm_operator_attribution=True,
            **{key: candidate[key] for key in ('message_uid', 'snapshot_hash', 'checkpoint')})
        return owner, peer, run, request

    def test_selected_unpublished_dispatch_does_not_block_a_peer_claim(self):
        owner, peer, run, request = self.selected_missing()
        expected = self.trigger.queue._queue.enqueue(peer, queue_fixture.envelope(job_id=73))
        claimed = self.trigger.queue.claim(peer, 'peer-consumer')
        self.assertEqual(claimed['envelope'], expected['envelope'])

    def test_missing_transport_hold_survives_reload_and_only_exact_proof_can_resolve(self):
        owner, peer, run, request = self.selected_missing()
        fence = self.sessions.get(run['id'])['superseded_attempts'][-1]
        transport = fence['selected_transport']
        self.assertIs(transport['resolved'], False)
        self.assertIsNone(transport['resolved_at'])
        self.assertEqual(transport['dispatch_id'], run['active_invocation']['dispatch_id'])
        self.assertEqual(transport['seat_identity_id'], owner['identity_id'])
        raw = self.trigger.queue._queue
        pending = raw.enqueue(owner, queue_fixture.envelope(job_id=74))
        sessions = SessionStore(str(self.sessions._path))
        coordinated = CoordinatedQueue(QueueStore(self.fixture.root), sessions, threading.RLock())
        with self.assertRaises(QueueBusy):
            coordinated.claim(owner, 'new-consumer')
        # Internal algorithm evidence only, not native process proof.
        proof = {'local_ended': True, 'dispatch_id': transport['dispatch_id'],
                 'seat_identity_id': owner['identity_id'],
                 'launch_attempt': transport['launch_provenance']['launch_attempt'],
                 'verification_basis': 'retained_native_handle_observed_end'}
        disk = sessions._path.read_bytes()
        for invalid in (dict(proof, local_ended=1), dict(proof, dispatch_id=uuid.uuid4().hex),
                        dict(proof, launch_attempt=uuid.uuid4().hex)):
            with self.assertRaises(ValueError):
                sessions.resolve_selected_transport(run['id'], request, invalid)
            self.assertEqual(sessions._path.read_bytes(), disk)
        replace = Path.replace
        def fail(path, target):
            if Path(target) == sessions._path:
                raise OSError('resolution persistence failed')
            return replace(path, target)
        with patch.object(Path, 'replace', fail), self.assertRaises(OSError):
            sessions.resolve_selected_transport(run['id'], request, proof)
        self.assertEqual(sessions._path.read_bytes(), disk)
        with self.assertRaises(QueueBusy):
            coordinated.claim(owner, 'new-consumer')
        sessions.resolve_selected_transport(run['id'], request, proof)
        resolved = sessions._path.read_bytes()
        sessions.resolve_selected_transport(run['id'], request, proof)
        self.assertEqual(sessions._path.read_bytes(), resolved)
        self.assertEqual(coordinated.claim(owner, 'new-consumer')['envelope'], pending['envelope'])

    def test_existing_unrelated_consumer_can_still_poll_its_cancellation(self):
        work = {}
        def active_job(owner):
            raw = self.trigger.queue._queue
            work.update(raw.enqueue(owner, queue_fixture.envelope(job_id=75)))
            raw.claim(owner, 'original-consumer')
        owner, peer, run, request = self.selected_missing(active_job)
        raw = self.trigger.queue._queue
        dispatch = work['envelope']['dispatch_id']
        self.assertEqual(self.trigger.queue.claim(owner, 'original-consumer')['state'], 'dispatched')
        raw.cancel_dispatch(dispatch, uuid.uuid4().hex)
        self.assertEqual(self.trigger.queue.claim(owner, 'original-consumer')['state'], 'cancelling')
        with self.assertRaises(QueueBusy):
            self.trigger.queue.claim(owner, 'different-consumer')
