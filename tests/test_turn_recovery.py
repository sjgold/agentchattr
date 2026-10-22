"""Durable stalled-turn checkpoints, explicit wait, and same-turn retry fences."""
from copy import deepcopy
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import AgentTrigger
from dispatch_queue import QueueBusy
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventAccessError, EventConflict

POLICY = {'ack_timeout': 5, 'response_timeout': 10, 'monitor_interval': 1}


class TurnRecoveryTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'session_runs.json'
        self.sessions = SessionStore(str(self.path))
        self.sessions.save_custom_template({'id': 'review', 'name': 'Review', 'roles': ['reviewer', 'editor'],
            'phases': [{'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Inspect source.'},
                       {'name': 'Edit', 'participants': ['editor'], 'prompt': 'Explain result.', 'is_output': True}]})
        self.registry = RuntimeRegistry(str(self.root))
        self.registry.seed({'codex': {'type': 'api', 'label': 'API one'}, 'claude': {'type': 'api', 'label': 'API two'}})
        self.owner = self.registry.register('codex')
        self.peer = self.registry.register('claude')
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry, recovery_policy=POLICY)
        started = self.engine.start_session('review', 'general', {'reviewer': 'codex', 'editor': 'claude'},
            'operator', input_text='Exact café source\r\nunchanged across retry.')
        self.session_id = started['id']
        self.original = deepcopy(started['active_invocation'])
        self.queue = self.engine._trigger.queue

    def current(self):
        return self.sessions.get(self.session_id)

    def record(self):
        return self.queue.owned(self.owner, self.original['dispatch_id'])

    def ack(self):
        record = self.queue.claim(self.owner, 'worker')
        self.queue.acknowledge(self.owner, record['envelope']['dispatch_id'], 'worker')
        return next(event['at'] for event in reversed(self.record()['events']) if event['state'] == 'acknowledged')

    def stall(self, *, acknowledged=False):
        if acknowledged:
            now = self.ack() + self.current()['recovery_policy']['response_timeout'] + .1
        else:
            now = self.record()['events'][0]['at'] + self.current()['recovery_policy']['ack_timeout'] + .1
        self.engine.monitor_turns(now=now)
        self.assertEqual(self.current()['state'], 'stalled')
        return now, deepcopy(self.current()['turn_recovery'])

    def terminal_failure(self, category='provider_failure'):
        now = self.ack() + .01
        self.queue.release(self.owner, self.original['dispatch_id'], 'worker', failed=True, error=category)
        self.engine.monitor_turns(now=now)
        self.assertEqual(self.current()['state'], 'stalled')
        return now, deepcopy(self.current()['turn_recovery'])

    def test_policy_defaults_constructor_and_persisted_run_override(self):
        self.assertEqual(self.current()['recovery_policy'], POLICY)
        trigger = AgentTrigger(self.registry, str(self.root))
        default = SessionEngine(self.sessions, self.messages, trigger, self.registry)
        run = default.start_session('review', 'defaults', {'reviewer': 'codex', 'editor': 'claude'}, 'operator')
        self.assertEqual(run['recovery_policy'], {'ack_timeout': 30, 'response_timeout': 900, 'monitor_interval': 1})
        override = {'ack_timeout': 7, 'response_timeout': 15, 'monitor_interval': .5}
        run = self.engine.start_session('review', 'override', {'reviewer': 'codex', 'editor': 'claude'},
                                        'operator', recovery_policy=override)
        self.assertEqual(SessionStore(str(self.path)).get(run['id'])['recovery_policy'], override)

    def test_missing_ack_becomes_visible_stall_without_phase_advance(self):
        self.stall()
        state = self.current()
        self.assertEqual(state['state'], 'stalled')
        self.assertEqual(state['turn_recovery']['reason'], 'missing_ack')
        self.assertEqual(state['turn_recovery']['attempt_id'], self.original['attempt_id'])
        self.assertEqual((state['current_phase'], state['current_turn']), (0, 0))
        for key in ('checkpoint_id', 'last_event', 'status'):
            self.assertIn(key, state['turn_recovery'])

    def test_nonfinite_nonpositive_boolean_and_unknown_policy_values_rejected(self):
        for field in POLICY:
            for invalid in (True, False, 0, -1, float('inf'), float('nan'), '5', None):
                policy = {**POLICY, field: invalid}
                with self.subTest(field=field, invalid=repr(invalid)), self.assertRaises(ValueError):
                    SessionEngine(self.sessions, self.messages, AgentTrigger(self.registry, str(self.root)),
                                  self.registry, recovery_policy=policy)
                with self.assertRaises(ValueError):
                    self.engine.start_session('review', 'invalid', {'reviewer': 'codex', 'editor': 'claude'},
                                              'operator', recovery_policy=policy)
        with self.assertRaises(ValueError):
            self.engine.start_session('review', 'invalid', {'reviewer': 'codex', 'editor': 'claude'},
                                      'operator', recovery_policy={**POLICY, 'hidden_retry_budget': 99})
        self.assertEqual(len(self.sessions.list_all()), 1)

    def test_live_heartbeats_and_dropped_failure_do_not_extend_response_deadline(self):
        import app
        import mcp_bridge
        acknowledged_at = self.ack()
        deadline = acknowledged_at + POLICY['response_timeout']
        request = Mock()
        request.headers = {'Authorization': 'Bearer ' + self.owner['token']}
        async def body():
            return {'active': True}
        request.json = body
        with patch.object(app, 'registry', self.registry), patch.object(mcp_bridge, '_presence', {}), \
             patch.object(mcp_bridge, '_activity', {}):
            for now in (acknowledged_at + 1, deadline - .1, deadline + .1):
                with patch('time.time', return_value=now):
                    asyncio.run(app.heartbeat(self.owner['name'], request))
                    self.engine.monitor_turns(now=now)
                if now < deadline:
                    self.assertNotEqual(self.current()['state'], 'stalled')
        self.assertEqual(self.current()['state'], 'stalled')
        self.assertEqual(self.current()['turn_recovery']['reason'], 'response_timeout')
        self.assertEqual(self.record()['state'], 'acknowledged', 'no reported failure receipt was supplied')

    def assert_failure_visible(self, category):
        self.terminal_failure(category)
        state = self.current()
        self.assertEqual(state['turn_recovery']['reason'], category)
        self.assertEqual(state.get('admitted_events', []), [])
        self.assertEqual((state['current_phase'], state['current_turn']), (0, 0))
        self.assertFalse(any(message['type'] == 'session_result' for message in self.messages.get_recent(100)))

    def test_provider_failed_release_is_visible_without_advancement(self):
        self.assert_failure_visible('provider_failure')

    def test_malformed_completion_failed_release_is_visible_without_advancement(self):
        self.assert_failure_visible('malformed_session_response')

    def test_local_delivery_failed_release_is_visible_without_advancement(self):
        self.assert_failure_visible('local_delivery_failure')

    def test_empty_completion_failed_release_is_visible_without_advancement(self):
        self.assert_failure_visible('empty_completion')

    def test_absent_and_replaced_identity_are_disconnected_before_timeout(self):
        other = self.engine.start_session('review', 'other', {'reviewer': 'claude', 'editor': 'codex'}, 'operator')
        self.registry.deregister(self.owner['name'])
        replacement = self.registry.register('codex')
        self.assertNotEqual(replacement['identity_id'], self.owner['identity_id'])
        self.registry.deregister(self.peer['name'])
        self.engine.monitor_turns(now=time.time() + .1)
        for session_id in (self.session_id, other['id']):
            with self.subTest(session_id=session_id):
                state = self.sessions.get(session_id)
                self.assertEqual(state['state'], 'stalled')
                self.assertEqual(state['turn_recovery']['reason'], 'disconnected')
                self.assertEqual(state['current_phase'], 0)

    def test_human_question_and_explicit_pause_have_no_machine_deadline(self):
        self.sessions.pause(self.session_id)
        human = self.engine.start_session('review', 'human', {'reviewer': 'alice', 'editor': 'bob'}, 'operator')
        question = self.engine.start_session('review', 'question', {'reviewer': 'claude', 'editor': 'codex'}, 'operator')
        self.engine.admit_event(question['active_invocation']['brief_id'], 'question', 'Which source?', self.peer)
        self.engine.monitor_turns(now=time.time() + 10000)
        self.assertEqual(self.current()['state'], 'paused')
        self.assertEqual(self.sessions.get(human['id'])['state'], 'waiting')
        self.assertEqual(self.sessions.get(question['id'])['state'], 'awaiting_input')
        for session_id in (self.session_id, human['id'], question['id']):
            self.assertFalse(self.sessions.get(session_id).get('turn_recovery'))

    def test_unfenced_late_final_resolves_stall_and_stale_retry_conflicts(self):
        now, checkpoint = self.stall()
        result = self.engine.admit_event(self.original['brief_id'], 'final', 'Late but current final', self.owner)
        self.assertEqual(result['status'], 'admitted')
        self.assertEqual(self.current()['current_phase'], 1)
        self.assertNotEqual(self.current()['state'], 'stalled')
        with self.assertRaises(EventConflict):
            self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], uuid.uuid4().hex, now=now)

    def test_unfenced_late_question_resolves_stall_into_awaiting_input(self):
        now, checkpoint = self.stall()
        self.engine.admit_event(self.original['brief_id'], 'question', 'Late current question?', self.owner)
        self.assertEqual(self.current()['state'], 'awaiting_input')
        self.assertEqual(self.current()['current_phase'], 0)
        with self.assertRaises(EventConflict):
            self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], uuid.uuid4().hex, now=now)

    def test_wait_extends_same_checkpoint_without_new_identity_or_dispatch(self):
        now, checkpoint = self.stall(acknowledged=True)
        original = deepcopy(self.current()['active_invocation'])
        queue_before = (self.root / 'queue/ledger.json').read_bytes()
        self.engine.wait_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], 20, now=now)
        for key in ('run_id', 'turn_id', 'attempt_id', 'brief_id', 'dispatch_id', 'input_revision'):
            self.assertEqual(self.current()['active_invocation'][key], original[key])
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue_before)
        self.engine.monitor_turns(now=now + 19.9)
        self.assertNotEqual(self.current()['state'], 'stalled')
        self.engine.monitor_turns(now=now + 20.1)
        self.assertEqual(self.current()['state'], 'stalled')
        self.assertEqual(self.current()['turn_recovery']['checkpoint_id'], checkpoint['checkpoint_id'])

    def test_terminal_retry_is_idempotent_fresh_same_turn_and_fences_old_output(self):
        now, checkpoint = self.terminal_failure()
        request_id = uuid.uuid4().hex
        source = deepcopy(self.current()['input_snapshot'])
        self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], request_id, now=now)
        current = self.current()
        fresh = deepcopy(current['active_invocation'])
        for key in ('brief_id', 'attempt_id', 'dispatch_id'):
            self.assertNotEqual(fresh[key], self.original[key])
        for key in ('run_id', 'turn_id', 'input_revision'):
            self.assertEqual(fresh[key], self.original[key])
        self.assertEqual(current['input_snapshot'], source)
        self.assertTrue(any(item['attempt_id'] == self.original['attempt_id'] for item in current['superseded_attempts']))
        self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], request_id, now=now)
        self.assertEqual(self.current()['active_invocation']['attempt_id'], fresh['attempt_id'])
        # Request idempotency and the superseded fence must come from durable
        # state, not only the original coordinator's in-memory objects.
        self.sessions = SessionStore(str(self.path))
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        self.queue = self.engine._trigger.queue
        self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], request_id, now=now)
        self.assertEqual(self.current()['active_invocation']['attempt_id'], fresh['attempt_id'])
        with self.assertRaises(EventConflict):
            self.engine.admit_event(self.original['brief_id'], 'final', 'Late superseded result @claude', self.owner)
        quarantined = deepcopy(self.current()['quarantined_events'])
        self.assertEqual(quarantined[-1]['content'], 'Late superseded result @claude')
        with self.assertRaises(EventAccessError):
            self.engine.admit_event(self.original['brief_id'], 'final', 'Wrong seat', self.peer)
        self.assertEqual(self.current()['quarantined_events'], quarantined)
        records = json.loads((self.root / 'queue/ledger.json').read_text('utf-8'))['records']
        self.assertEqual(len(records), 2)

    def test_held_retry_waits_for_signed_local_end_before_new_dispatch(self):
        now, checkpoint = self.stall(acknowledged=True)
        request_id = uuid.uuid4().hex
        self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], request_id, now=now)
        self.assertEqual(self.current()['state'], 'retrying')
        self.assertEqual(self.record()['state'], 'cancelling')
        self.assertEqual(len(json.loads((self.root / 'queue/ledger.json').read_text('utf-8'))['records']), 1)
        with self.assertRaises(QueueBusy):
            self.queue.claim(self.owner, 'replacement-worker')
        self.queue.cancellation_receipt(self.owner, self.original['dispatch_id'], 'worker', 'local_ended')
        self.engine.monitor_turns(now=now + .1)
        fresh = self.current()['active_invocation']
        self.assertNotEqual(fresh['attempt_id'], self.original['attempt_id'])
        self.assertEqual(fresh['turn_id'], self.original['turn_id'])
        self.assertNotEqual(self.current()['state'], 'retrying')
        self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], request_id, now=now + .2)
        self.assertEqual(len(json.loads((self.root / 'queue/ledger.json').read_text('utf-8'))['records']), 2)

    def test_stale_wait_retry_and_stopped_or_prepared_runs_are_denied(self):
        now, checkpoint = self.stall()
        for stale_checkpoint, attempt in (('wrong-checkpoint', self.original['attempt_id']),
                                           (checkpoint['checkpoint_id'], uuid.uuid4().hex)):
            with self.subTest(checkpoint=stale_checkpoint), self.assertRaises(EventConflict):
                self.engine.wait_turn(self.session_id, stale_checkpoint, attempt, 20, now=now)
            with self.assertRaises(EventConflict):
                self.engine.retry_turn(self.session_id, stale_checkpoint, attempt, uuid.uuid4().hex, now=now)
        self.engine.stop_session(self.session_id)
        self.engine.reconcile_stops()
        prepared = self.sessions.prepare_restart(self.session_id, 'Different corrected source', uuid.uuid4().hex)
        for session_id in (self.session_id, prepared['id']):
            with self.subTest(session_id=session_id), self.assertRaises(EventConflict):
                self.engine.wait_turn(session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], 20, now=now)
            with self.assertRaises(EventConflict):
                self.engine.retry_turn(session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], uuid.uuid4().hex, now=now)

    def test_failed_wait_or_retry_persistence_preserves_disk_memory_and_queue(self):
        now, checkpoint = self.stall()
        before, disk = deepcopy(self.current()), self.path.read_bytes()
        queue_disk = (self.root / 'queue/ledger.json').read_bytes()
        for action in ('wait', 'retry'):
            with self.subTest(action=action), patch('session_store.atomic_json', side_effect=OSError('fixture recovery write failure')):
                with self.assertRaises(OSError):
                    if action == 'wait':
                        self.engine.wait_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], 20, now=now)
                    else:
                        self.engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], uuid.uuid4().hex, now=now)
            self.assertEqual(self.current(), before)
            self.assertEqual(self.path.read_bytes(), disk)
            self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue_disk)

    def test_checkpoint_policy_prior_results_and_source_survive_reload_and_retry(self):
        self.ack()
        self.engine.admit_event(self.original['brief_id'], 'final', 'Accepted earlier phase', self.owner)
        self.queue.release(self.owner, self.original['dispatch_id'], 'worker')
        accepted = deepcopy(self.current()['admitted_events'])
        source = deepcopy(self.current()['input_snapshot'])
        self.owner = self.peer
        self.original = deepcopy(self.current()['active_invocation'])
        now, checkpoint = self.terminal_failure('empty_completion')
        restored = SessionStore(str(self.path))
        restored_messages = MessageStore(str(self.root / 'messages.jsonl'))
        trigger = AgentTrigger(self.registry, str(self.root))
        engine = SessionEngine(restored, restored_messages, trigger, self.registry,
            recovery_policy={'ack_timeout': 100, 'response_timeout': 100, 'monitor_interval': 2})
        self.assertEqual(restored.get(self.session_id)['turn_recovery'], checkpoint)
        self.assertEqual(restored.get(self.session_id)['recovery_policy'], POLICY)
        engine.retry_turn(self.session_id, checkpoint['checkpoint_id'], self.original['attempt_id'], uuid.uuid4().hex, now=now)
        current = restored.get(self.session_id)
        self.assertEqual(current['admitted_events'], accepted)
        self.assertEqual(current['input_snapshot'], source)
        self.assertEqual(current['current_phase'], 1)
        brief = restored.briefs.get(current['active_invocation']['brief_id'], self.owner)
        self.assertEqual(brief['source'], source['text'])
        self.assertEqual([result['text'] for result in brief['prior_results']], ['Accepted earlier phase'])


if __name__ == '__main__':
    unittest.main()
