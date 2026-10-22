"""Durable run-scoped Stop fences, cancellation evidence, and late quarantine."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import AgentTrigger
from dispatch_queue import QueueAccessError, QueueBusy, QueueConflict
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventAccessError, EventConflict


class SessionStopTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'session_runs.json'
        self.sessions = SessionStore(str(self.path))
        self.sessions.save_custom_template({'id': 'review', 'name': 'Scoped review',
            'roles': ['reviewer', 'editor'], 'phases': [
                {'name': 'Review', 'participants': ['reviewer'], 'prompt': 'Review source.'},
                {'name': 'Edit', 'participants': ['editor'], 'prompt': 'Edit source.', 'is_output': True}]})
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.registry = RuntimeRegistry(str(self.root))
        self.registry.seed({'codex': {'label': 'Codex'}, 'claude': {'label': 'Claude'}})
        self.owner = self.registry.register('codex')
        self.peer = self.registry.register('claude')
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        self.started = self.engine.start_session('review', 'general',
            {'reviewer': 'codex', 'editor': 'claude'}, 'human', goal='Keep accepted work.',
            input_text='Exact café source\r\n@all is source data.')
        self.session_id = self.started['id']
        self.run_id = self.started['run_id']
        self.invocation = deepcopy(self.started['active_invocation'])
        self.queue = self.engine._trigger.queue

    def current(self):
        return self.sessions.get(self.session_id)

    def claim(self, consumer='worker'):
        return self.queue.claim(self.owner, consumer)

    def test_stop_persists_ineligibility_and_stable_id(self):
        stopped = self.engine.stop_session(self.session_id)
        self.assertFalse(stopped['dispatch_eligible'])
        self.assertEqual(stopped['state'], 'stopping')
        self.assertRegex(stopped['stop_id'], r'^[0-9a-f]{32}$')
        repeated = self.engine.stop_session(self.session_id)
        self.assertEqual(repeated['stop_id'], stopped['stop_id'])
        self.assertFalse(SessionStore(str(self.path)).get(self.session_id)['dispatch_eligible'])

    def test_end_session_delegates_to_stop_and_does_not_claim_termination(self):
        self.claim()
        result = self.engine.end_session(self.session_id)
        self.assertEqual(result['state'], 'stopping')
        self.assertFalse(result['dispatch_eligible'])
        self.assertEqual(self.queue.owned(self.owner, self.invocation['dispatch_id'])['state'], 'cancelling')

    def test_stopped_pending_dispatch_cannot_be_claimed(self):
        self.engine.stop_session(self.session_id)
        self.assertIsNone(self.claim())
        self.assertEqual(self.queue.owned(self.owner, self.invocation['dispatch_id'])['state'], 'cancelled')

    def test_fence_is_persisted_before_queue_cleanup(self):
        original_cancel = self.queue.cancel_run
        observed = []
        def checked_cancel(run_id, stop_id):
            durable = SessionStore(str(self.path)).get(self.session_id)
            observed.append(durable)
            self.assertFalse(durable['dispatch_eligible'])
            self.assertEqual(durable['stop_id'], stop_id)
            self.assertEqual(durable['run_id'], run_id)
            return original_cancel(run_id, stop_id)
        with patch.object(self.queue, 'cancel_run', side_effect=checked_cancel):
            self.engine.stop_session(self.session_id)
        self.assertTrue(observed)

    def test_failed_stop_persistence_preserves_disk_memory_and_queue(self):
        before = deepcopy(self.current())
        disk = self.path.read_bytes()
        queue_disk = (self.root / 'queue/ledger.json').read_bytes()
        with patch('session_store.atomic_json', side_effect=OSError('fixture Stop persistence failure')):
            with self.assertRaises(OSError):
                self.engine.stop_session(self.session_id)
        self.assertEqual(self.current(), before)
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue_disk)

    def test_cleanup_failure_reload_keeps_fence_and_cannot_claim_or_enqueue_stopped_run(self):
        with patch.object(self.queue, 'cancel_run', side_effect=OSError('fixture interrupted cleanup')):
            try:
                self.engine.stop_session(self.session_id)
            except OSError:
                pass
        durable = SessionStore(str(self.path)).get(self.session_id)
        self.assertFalse(durable['dispatch_eligible'])
        self.assertRegex(durable['stop_id'], r'^[0-9a-f]{32}$')
        restored_sessions = SessionStore(str(self.path))
        restored_trigger = AgentTrigger(self.registry, str(self.root))
        restored = SessionEngine(restored_sessions, self.messages, restored_trigger, self.registry)
        with self.assertRaises(QueueConflict):
            restored_trigger.trigger_sync('codex', prompt='Late stopped-run dispatch', run_id=self.run_id,
                                           attempt_id=self.invocation['attempt_id'])
        self.assertIsNone(restored_trigger.queue.claim(self.owner, 'new-worker'))
        restored.reconcile_stops()
        self.assertEqual(restored_trigger.queue.owned(self.owner, self.invocation['dispatch_id'])['state'], 'cancelled')
        self.assertFalse(restored_sessions.get(self.session_id)['dispatch_eligible'])

    def test_stop_cancels_run_descendants_but_preserves_other_run_and_ordinary_work(self):
        descendant = self.trigger.trigger_sync('codex', prompt='Run descendant', run_id=self.run_id,
                                               attempt_id=self.invocation['attempt_id'])
        ordinary = self.trigger.trigger_sync('codex', prompt='Unrelated ordinary work')
        peer_session = self.engine.start_session('review', 'peer-room',
            {'reviewer': 'claude', 'editor': 'codex'}, 'human', input_text='Peer source')
        self.engine.stop_session(self.session_id)
        for dispatch_id in (self.invocation['dispatch_id'], descendant['envelope']['dispatch_id']):
            self.assertEqual(self.queue.owned(self.owner, dispatch_id)['state'], 'cancelled')
        self.assertEqual(self.claim()['envelope']['dispatch_id'], ordinary['envelope']['dispatch_id'])
        peer_claim = self.queue.claim(self.peer, 'peer-worker')
        self.assertEqual(peer_claim['envelope']['run_id'], peer_session['run_id'])
        self.assertNotIn(self.sessions.get(peer_session['id'])['state'], ('stopping', 'stopped', 'unresolved'))

    def test_delivered_receipt_retains_ownership_local_ended_frees_only_owned_dispatch(self):
        self.claim()
        ordinary = self.trigger.trigger_sync('codex', prompt='Ordinary task after owned cancellation')
        stopped = self.engine.stop_session(self.session_id)
        dispatch_id = self.invocation['dispatch_id']
        self.assertEqual(self.queue.owned(self.owner, dispatch_id)['state'], 'cancelling')
        self.queue.cancellation_receipt(self.owner, dispatch_id, 'worker', 'delivered')
        with self.assertRaises(QueueBusy):
            self.claim('replacement-consumer')
        ended = self.queue.cancellation_receipt(self.owner, dispatch_id, 'worker', 'local_ended')
        self.assertEqual(ended['state'], 'cancelled')
        self.assertIn('unverified', json.dumps(ended))
        self.engine.reconcile_stops()
        self.assertEqual(self.current()['state'], 'stopped')
        self.assertEqual(self.current()['stop_id'], stopped['stop_id'])
        self.assertEqual(self.claim('replacement-consumer')['envelope']['dispatch_id'], ordinary['envelope']['dispatch_id'])

    def test_unsupported_then_deadline_is_unresolved_and_keeps_owned_work(self):
        self.claim()
        self.engine.stop_session(self.session_id)
        dispatch_id = self.invocation['dispatch_id']
        receipt = self.queue.cancellation_receipt(self.owner, dispatch_id, 'worker', 'unsupported')
        self.assertIn('unsupported', json.dumps(receipt))
        self.engine.reconcile_stops(now=time.time() + 11)
        self.assertEqual(self.current()['state'], 'unresolved')
        self.assertFalse(self.current()['dispatch_eligible'])
        self.assertNotEqual(self.queue.owned(self.owner, dispatch_id)['state'], 'cancelled')
        with self.assertRaises(QueueBusy):
            self.claim('replacement-consumer')

    def test_cancellation_receipts_reject_wrong_seat_consumer_and_invalid_status(self):
        self.claim()
        self.engine.stop_session(self.session_id)
        dispatch_id = self.invocation['dispatch_id']
        for instance, consumer in ((self.peer, 'worker'), (self.owner, 'stale-consumer')):
            with self.subTest(consumer=consumer), self.assertRaises(QueueAccessError):
                self.queue.cancellation_receipt(instance, dispatch_id, consumer, 'local_ended')
        with self.assertRaises(ValueError):
            self.queue.cancellation_receipt(self.owner, dispatch_id, 'worker', 'looks_idle')
        self.assertEqual(self.queue.owned(self.owner, dispatch_id)['state'], 'cancelling')

    def test_late_result_is_attributed_quarantine_without_projection_or_successor(self):
        self.claim()
        self.engine.stop_session(self.session_id)
        queue_before = (self.root / 'queue/ledger.json').read_bytes()
        content = 'Late café output\r\n@claude start another review.'
        with self.assertRaises(EventConflict):
            self.engine.admit_event(self.invocation['brief_id'], 'final', content, self.owner)
        after = self.current()
        self.assertEqual(len(after['quarantined_events']), 1)
        quarantined = after['quarantined_events'][0]
        self.assertEqual(quarantined['content'], content)
        for identity in (self.run_id, self.invocation['attempt_id'], self.invocation['brief_id'], self.owner['identity_id']):
            self.assertIn(identity, json.dumps(quarantined))
        self.assertEqual(after.get('admitted_events', []), [])
        self.assertEqual((after['current_phase'], after['current_turn']), (0, 0))
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue_before)
        self.assertFalse(any(message['text'] == content for message in self.messages.get_recent(100)))
        self.assertIsNone(self.queue.claim(self.peer, 'peer-worker'))

    def test_wrong_seat_is_denied_without_quarantine(self):
        self.engine.stop_session(self.session_id)
        with self.assertRaises(EventAccessError):
            self.engine.admit_event(self.invocation['brief_id'], 'final', 'Wrong provenance', self.peer)
        self.assertEqual(self.current().get('quarantined_events', []), [])

    def test_accepted_result_is_preserved_and_duplicate_retry_is_not_quarantined(self):
        self.claim()
        self.queue.acknowledge(self.owner, self.invocation['dispatch_id'], 'worker')
        event_id = uuid.uuid4().hex
        self.engine.admit_event(self.invocation['brief_id'], 'final', 'Accepted before Stop', self.owner, event_id=event_id)
        self.queue.release(self.owner, self.invocation['dispatch_id'], 'worker')
        accepted = deepcopy(self.current()['admitted_events'])
        source = deepcopy(self.current()['input_snapshot'])
        self.engine.stop_session(self.session_id)
        with self.assertRaises(EventConflict):
            self.engine.admit_event(self.invocation['brief_id'], 'final', 'Accepted before Stop', self.owner, event_id=event_id)
        self.assertEqual(self.current()['admitted_events'], accepted)
        self.assertEqual(self.current()['input_snapshot'], source)
        self.assertEqual(self.current().get('quarantined_events', []), [])

    def test_stop_and_final_serialize_to_one_explainable_outcome(self):
        self.claim()
        gate = threading.Barrier(2)
        def stop():
            gate.wait(timeout=3)
            self.engine.stop_session(self.session_id)
        def final():
            gate.wait(timeout=3)
            try:
                self.engine.admit_event(self.invocation['brief_id'], 'final', 'Racing final', self.owner)
                return 'admitted'
            except EventConflict:
                return 'fenced'
        with ThreadPoolExecutor(max_workers=2) as pool:
            stopping = pool.submit(stop)
            admitting = pool.submit(final)
            outcome = admitting.result(timeout=5)
            stopping.result(timeout=5)
        current = self.current()
        self.assertFalse(current['dispatch_eligible'])
        if outcome == 'admitted':
            self.assertEqual(len(current['admitted_events']), 1)
            self.assertEqual(current['current_phase'], 1)
            self.assertEqual(current.get('quarantined_events', []), [])
        else:
            self.assertEqual(current.get('admitted_events', []), [])
            self.assertEqual(current['current_phase'], 0)
            self.assertEqual(len(current['quarantined_events']), 1)
        self.assertIsNone(self.queue.claim(self.peer, 'peer-worker'), 'stopped successor must never be delivered')


if __name__ == '__main__':
    unittest.main()
