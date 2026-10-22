"""Recovery cannot leak authority through routing, pauses, or corrected lineage."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import uuid

from dispatch_queue import QueueConflict


class RecoveryBoundaryTests(unittest.TestCase):
    def fixture(self):
        from tests.test_turn_recovery import TurnRecoveryTests
        fixture = TurnRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_superseded_producer_and_scoped_chat_have_no_routing_authority(self):
        f = self.fixture()
        now, checkpoint = f.terminal_failure()
        old = deepcopy(f.record()['envelope'])
        f.engine.retry_turn(f.session_id, checkpoint['checkpoint_id'], f.original['attempt_id'], uuid.uuid4().hex, now=now)
        old['dispatch_id'] = uuid.uuid4().hex
        with self.assertRaises(QueueConflict):
            f.queue.enqueue(f.owner, old)
        metadata = f.engine.chat_scope(f.owner, f.original['dispatch_id'])
        self.assertTrue(metadata.get('routing_suppressed'))
        self.assertEqual(metadata['quarantine_session_id'], f.session_id)
        f.engine.send_chat(f.owner, 'Late @claude content stays intact.', dispatch_id=f.original['dispatch_id'])
        self.assertEqual(f.current()['quarantined_events'][-1]['reason'], 'attempt_superseded')
        fresh = f.current()['active_invocation']['dispatch_id']
        self.assertFalse(f.engine.chat_scope(f.owner, fresh).get('routing_suppressed'))

    def test_new_corrected_run_does_not_inherit_retry_fences_or_checkpoints(self):
        f = self.fixture()
        now, checkpoint = f.terminal_failure()
        f.engine.retry_turn(f.session_id, checkpoint['checkpoint_id'], f.original['attempt_id'], uuid.uuid4().hex, now=now)
        f.engine.stop_session(f.session_id)
        f.engine.reconcile_stops()
        parent = f.current()
        self.assertTrue(parent['superseded_attempts'])
        child = f.sessions.prepare_restart(f.session_id, 'Corrected source for a NEW run.', uuid.uuid4().hex)
        self.assertEqual(child['superseded_attempts'], [])
        self.assertEqual(child['retry_requests'], {})
        self.assertIsNone(child['turn_recovery'])
        self.assertNotIn('pending_retry', child)
        self.assertEqual(child['recovery_policy'], parent['recovery_policy'])

    def test_resume_preserves_remaining_response_allowance(self):
        f = self.fixture()
        f.queue.claim(f.owner, 'worker')
        f.queue.acknowledge(f.owner, f.original['dispatch_id'], 'worker')
        ack = f.record()['events'][-1]['at']
        f.engine.monitor_turns(now=ack + 1)
        deadline = f.current()['active_invocation']['monitoring']['response_deadline']
        with patch('session_store.time.time', return_value=ack + 10):
            f.sessions.pause(f.session_id)
        with patch('session_store.time.time', return_value=ack + 110):
            f.sessions.resume_explicit(f.session_id)
        f.engine.monitor_turns(now=deadline + 50)
        self.assertEqual(f.current()['state'], 'waiting')
        f.engine.monitor_turns(now=deadline + 101)
        self.assertEqual(f.current()['turn_recovery']['reason'], 'response_timeout')

    def test_corrected_review_read_scope_survives_stall_and_pending_retry(self):
        from tests.test_corrected_agents import CorrectedAgentTests
        f = CorrectedAgentTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        child = f.engine.correct_and_restart(f.parent['id'], 'Corrected packet only.', uuid.uuid4().hex)
        active = f.engine.activate_restart(child['id'])
        invocation = active['active_invocation']
        queue = f.engine._trigger.queue
        record = queue.claim(f.api, 'worker')
        queue.acknowledge(f.api, invocation['dispatch_id'], 'worker')
        f.messages.add('system', 'Abandoned source and unrelated shared history')
        now = record['events'][-1]['at'] + 1000
        f.engine.monitor_turns(now=now)
        stalled = f.sessions.get(child['id'])
        self.assertEqual(stalled['state'], 'stalled')
        self.assertEqual(f.engine.review_messages(f.api), [])
        checkpoint = stalled['turn_recovery']
        f.engine.retry_turn(child['id'], checkpoint['checkpoint_id'], invocation['attempt_id'], uuid.uuid4().hex, now=now)
        self.assertEqual(f.sessions.get(child['id'])['state'], 'retrying')
        self.assertEqual(f.engine.review_messages(f.api), [])

    def test_failed_queue_cleanup_keeps_fence_and_cold_claim_cannot_replay(self):
        from agents import AgentTrigger
        from session_engine import SessionEngine
        from session_store import SessionStore
        f = self.fixture()
        now, checkpoint = f.stall(acknowledged=False)
        raw_queue = f.queue._queue
        with patch.object(raw_queue, 'cancel_dispatch', side_effect=OSError('fixture cleanup failure')):
            with self.assertRaises(OSError):
                f.engine.retry_turn(f.session_id, checkpoint['checkpoint_id'], f.original['attempt_id'], uuid.uuid4().hex, now=now)
        self.assertTrue(any(a['attempt_id'] == f.original['attempt_id'] for a in f.current()['superseded_attempts']))
        restored = SessionStore(str(f.path))
        trigger = AgentTrigger(f.registry, str(f.root))
        engine = SessionEngine(restored, f.messages, trigger, f.registry)
        self.assertIsNone(engine._trigger.queue.claim(f.owner, 'cold-consumer'))
        self.assertEqual(raw_queue.owned(f.owner, f.original['dispatch_id'])['state'], 'cancelled')
