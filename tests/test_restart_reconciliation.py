"""Cold reconciliation preserves authority, queue ownership, and frozen work."""
from copy import deepcopy
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
from dispatch_queue import QueueConflict
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict


class RestartReconciliationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'session_runs.json'
        self.sessions = SessionStore(str(self.path))
        self.sessions.save_custom_template({'id': 'review', 'name': 'Review', 'roles': ['reviewer', 'editor'],
            'phases': [{'name': 'Evidence', 'participants': ['reviewer'], 'prompt': 'Read exact source.'},
                       {'name': 'Decision', 'participants': ['editor'], 'prompt': 'Use prior result.', 'is_output': True}]})
        self.registry = RuntimeRegistry(str(self.root))
        self.registry.seed({'seat0': {'type': 'api', 'label': 'API reviewer'},
                            'seat1': {'type': 'api', 'label': 'API editor'}})
        self.owner = self.registry.register('seat0')
        self.peer = self.registry.register('seat1')
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        run = self.engine.start_session('review', 'general', {'reviewer': 'seat0', 'editor': 'seat1'},
            'operator', input_text='Exact café\r\nsource', goal='Preserve accepted evidence.')
        self.session_id = run['id']
        self.original = deepcopy(run['active_invocation'])

    def current(self):
        return self.sessions.get(self.session_id)

    def records(self):
        return json.loads((self.root / 'queue/ledger.json').read_text('utf-8'))['records']

    def projection_gap(self):
        with patch.object(self.engine, '_project_session', return_value=False):
            self.engine.admit_event(self.original['brief_id'], 'final', 'Accepted before crash', self.owner)
        self.assertIsNone(self.current()['active_invocation'])
        self.assertEqual(self.current()['current_phase'], 1)

    def managed(self, states=None):
        self.readiness = states or {}
        self.manager = Mock(spec=['restart_readiness', 'launch_provenance', 'prepare_retry_context'])
        self.manager.restart_readiness.side_effect = lambda identity_id, boot_id: deepcopy(self.readiness.get(identity_id,
            {'state': 'unverified', 'process_verified': False}))
        def bind(value):
            for role, instance in (('reviewer', self.owner), ('editor', self.peer)):
                value['participant_bindings'][role]['launch_provenance'] = {
                    'key': 'team/' + role, 'identity_id': instance['identity_id'],
                    'launch_attempt': uuid.uuid4().hex, 'fingerprint': 'a' * 64,
                    'effective': {'seat': {'id': role, 'adapter': 'openai-compatible', 'model': 'frozen-model'}}}
        self.sessions._event_update(self.session_id, bind)
        self.engine._seat_manager = self.manager
        return self.manager

    def cold(self, manager=None):
        self.sessions = SessionStore(str(self.path))
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry, seat_manager=manager)

    def ack(self):
        record = self.trigger.queue.claim(self.owner, 'original-worker')
        self.trigger.queue.acknowledge(self.owner, record['envelope']['dispatch_id'], 'original-worker')
        return record

    def assert_unclaimable(self, instance, consumer):
        try:
            result = self.trigger.queue.claim(instance, consumer)
        except QueueConflict:
            return
        self.assertIsNone(result, 'an unverified owner must never receive the held envelope')

    def test_recover_projections_never_blindly_enqueues_successor(self):
        self.projection_gap()
        before = deepcopy(self.records())
        self.engine.recover_projections()
        self.assertEqual(self.records(), before)
        self.assertIsNone(self.current()['active_invocation'])
        self.assertIsNotNone(self.current()['admitted_events'][0]['projected_message_id'])

    def test_restart_reconciliation_exposes_unknown_owner_without_new_attempt(self):
        self.registry.deregister(self.owner['name'])
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        current = self.current()
        self.assertEqual(current['state'], 'interrupted')
        self.assertFalse(current['dispatch_eligible'])
        self.assertEqual(current['active_invocation'], self.original)

    def test_projection_dispatch_false_is_publicly_available(self):
        self.projection_gap()
        self.engine._project_session(self.session_id, dispatch=False)
        self.assertEqual(len(self.records()), 1)

    def test_repeated_projection_repairs_chat_once_without_second_admission(self):
        self.projection_gap()
        self.cold()
        self.engine.recover_projections()
        self.engine.recover_projections()
        results = [value for value in self.messages.get_recent(100) if value['type'] == 'session_result']
        self.assertEqual([value['text'] for value in results], ['Accepted before crash'])
        self.assertEqual(len(self.current()['admitted_events']), 1)
        self.assertEqual(self.current()['admitted_events'][0]['projected_message_id'], results[0]['id'])
        self.assertEqual(len(self.records()), 1)

    def test_registered_manual_agent_remains_eligible_without_managed_process_claim(self):
        original, records = deepcopy(self.current()), deepcopy(self.records())
        self.cold()
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        current = self.current()
        self.assertEqual(current['state'], original['state'])
        self.assertTrue(current['dispatch_eligible'])
        self.assertEqual(current['active_invocation'], original['active_invocation'])
        self.assertEqual(self.records(), records)

    def test_verified_managed_owner_keeps_original_held_invocation_without_replay(self):
        self.ack()
        manager = self.managed({self.owner['identity_id']: {'state': 'ready', 'process_verified': True}})
        before, queue = deepcopy(self.current()), deepcopy(self.records())
        self.cold(manager)
        boot = uuid.uuid4().hex
        self.engine.reconcile_restart(boot_id=boot)
        current = self.current()
        self.assertTrue(current['dispatch_eligible'])
        self.assertEqual(current['active_invocation'], before['active_invocation'])
        self.assertEqual(self.records(), queue)
        manager.restart_readiness.assert_any_call(self.owner['identity_id'], boot)
        manager.prepare_retry_context.assert_not_called()

    def test_ready_label_without_process_verification_cannot_restore_managed_owner(self):
        manager = self.managed({self.owner['identity_id']: {'state': 'ready', 'process_verified': False}})
        self.cold(manager)
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        current = self.current()
        self.assertEqual(current['state'], 'interrupted')
        self.assertFalse(current['dispatch_eligible'])
        self.assertFalse(current.get('stop_id'))
        self.assertEqual(current['turn_recovery']['reason'], 'restart_unverified')
        self.assertFalse(current['turn_recovery']['recoverable_result'])

    def test_same_boot_preserves_wait_checkpoint_deadlines_and_frozen_snapshots(self):
        self.ack()
        self.engine.monitor_turns(now=time.time() + 1000)
        checkpoint = self.current()['turn_recovery']['checkpoint_id']
        self.engine.wait_turn(self.session_id, checkpoint, self.original['attempt_id'], 2000)
        manager = self.managed()
        before = deepcopy(self.current())
        self.cold(manager)
        boot = uuid.uuid4().hex
        self.engine.reconcile_restart(boot_id=boot, now=time.time())
        reconciled = deepcopy(self.current())
        for field in ('input_snapshot', 'design_snapshot', 'rules_snapshot', 'capacity_policy', 'recovery_policy', 'active_invocation'):
            self.assertEqual(reconciled[field], before[field])
        self.assertEqual(reconciled['turn_recovery']['checkpoint_id'], checkpoint)
        self.assertEqual(reconciled['turn_recovery']['actions'], before['turn_recovery']['actions'])
        self.assertEqual(reconciled['turn_recovery']['deferred_until'], before['turn_recovery']['deferred_until'])
        self.assertEqual(reconciled['restart_recovery']['boot_id'], boot)
        self.assertEqual(reconciled['restart_recovery']['previous_state'], before['state'])
        disk, queue = self.path.read_bytes(), (self.root / 'queue/ledger.json').read_bytes()
        self.engine.reconcile_restart(boot_id=boot, now=time.time() + 10)
        self.assertEqual(self.current(), reconciled)
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue)

    def test_unknown_held_owner_keeps_consumer_and_envelope_but_cannot_claim(self):
        self.ack()
        manager = self.managed()
        held = deepcopy(self.records()[0])
        self.cold(manager)
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        self.assert_unclaimable(self.owner, 'original-worker')
        self.assert_unclaimable(self.owner, 'replacement-worker')
        self.assertEqual(self.records()[0], held)
        self.assertEqual(len(self.records()), 1)

    def test_replaced_identity_is_interrupted_visible_and_reserves_channel(self):
        self.registry.deregister(self.owner['name'])
        replacement = self.registry.register('seat0')
        self.assertNotEqual(replacement['identity_id'], self.owner['identity_id'])
        self.cold()
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        active = self.engine.get_active('general')
        self.assertEqual(active['id'], self.session_id)
        self.assertEqual(active['state'], 'interrupted')
        self.assertIsNone(self.engine.start_session('review', 'general', {'reviewer': replacement['name'], 'editor': self.peer['name']}, 'operator'))
        self.assert_unclaimable(replacement, 'replacement-worker')
        self.assertEqual(len(self.sessions.list_all()), 1)

    def test_interrupted_run_does_not_globally_block_peer_or_ordinary_work(self):
        manager = self.managed()
        self.cold(manager)
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        record = self.trigger.queue.enqueue(self.peer, {'prompt': 'Ordinary independent work', 'channel': 'peer'})
        claimed = self.trigger.queue.claim(self.peer, 'peer-worker')
        self.assertEqual(claimed['envelope']['dispatch_id'], record['envelope']['dispatch_id'])
        self.assertEqual(self.registry.resolve_token(self.owner['token'])['identity_id'], self.owner['identity_id'])
        self.assertFalse(self.current().get('stop_id'))

    def test_late_unfenced_final_admitted_but_successor_waits_for_its_own_readiness(self):
        manager = self.managed()
        self.cold(manager)
        boot = uuid.uuid4().hex
        self.engine.reconcile_restart(boot_id=boot)
        result = self.engine.admit_event(self.original['brief_id'], 'final', 'Late authorized result', self.owner)
        self.assertEqual(result['status'], 'admitted')
        self.assertEqual(self.current()['admitted_events'][0]['content'], 'Late authorized result')
        self.assertEqual(self.current()['current_phase'], 1)
        self.assertIsNone(self.current()['active_invocation'])
        self.assertEqual(len(self.records()), 1)
        self.readiness[self.peer['identity_id']] = {'state': 'ready', 'process_verified': True}
        self.engine.reconcile_restart(boot_id=boot)
        fresh = deepcopy(self.current()['active_invocation'])
        self.assertEqual(fresh['expected_identity_id'], self.peer['identity_id'])
        self.assertEqual(len(self.records()), 2)
        self.engine.reconcile_restart(boot_id=boot)
        self.assertEqual(self.current()['active_invocation'], fresh)
        self.assertEqual(len(self.records()), 2)

    def test_human_question_pause_prepared_and_completed_semantics_survive(self):
        human = self.engine.start_session('review', 'human', {'reviewer': 'Alice', 'editor': 'Bob'}, 'operator')
        paused = self.engine.start_session('review', 'paused', {'reviewer': 'seat1', 'editor': 'seat0'}, 'operator')
        self.sessions.pause(paused['id'])
        self.engine.admit_event(self.original['brief_id'], 'question', 'Question before restart?', self.owner)
        parent = self.engine.start_session('review', 'prepared', {'reviewer': 'Alice', 'editor': 'Bob'}, 'operator', input_text='old')
        self.engine.stop_session(parent['id'])
        self.engine.reconcile_stops()
        child = self.sessions.prepare_restart(parent['id'], 'corrected', uuid.uuid4().hex)
        self.sessions.save_custom_template({'id': 'single', 'name': 'One', 'roles': ['r'],
            'phases': [{'name': 'Output', 'participants': ['r'], 'prompt': 'x', 'is_output': True}]})
        complete = self.engine.start_session('single', 'completed', {'r': 'seat1'}, 'operator')
        self.engine.admit_event(complete['active_invocation']['brief_id'], 'final', 'Complete before restart', self.peer)
        ids = [human['id'], paused['id'], self.session_id, child['id'], complete['id']]
        before = {identifier: self.sessions.get(identifier) for identifier in ids}
        records = deepcopy(self.records())
        self.cold()
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        for identifier, old in before.items():
            with self.subTest(session_id=identifier):
                current = self.sessions.get(identifier)
                self.assertEqual(current['state'], old['state'])
                self.assertEqual(current['active_invocation'], old['active_invocation'])
        self.assertEqual(self.records(), records)

    def test_atomic_reconciliation_failure_preserves_disk_memory_and_queue(self):
        manager = self.managed()
        self.cold(manager)
        before, disk = deepcopy(self.current()), self.path.read_bytes()
        queue = (self.root / 'queue/ledger.json').read_bytes()
        with patch('session_store.atomic_json', side_effect=OSError('fixture reconcile persistence failure')):
            with self.assertRaises(OSError):
                self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        self.assertEqual(self.current(), before)
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue)

    def test_explicit_retry_terminal_interrupted_turn_creates_new_attempt_without_losing_source(self):
        self.ack()
        self.trigger.queue.release(self.owner, self.original['dispatch_id'], 'original-worker', failed=True, error='provider_failure')
        self.registry.deregister(self.owner['name'], reclaimable=True)
        self.cold()
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        interrupted = deepcopy(self.current())
        self.assertEqual(interrupted['state'], 'interrupted')
        self.assertEqual(self.registry.resolve_token(self.owner['token'])['identity_id'], self.owner['identity_id'])
        checkpoint = interrupted['turn_recovery']['checkpoint_id']
        self.engine.retry_turn(self.session_id, checkpoint, self.original['attempt_id'], uuid.uuid4().hex)
        new = self.current()['active_invocation']
        self.assertNotEqual(new['attempt_id'], self.original['attempt_id'])
        self.assertEqual(new['turn_id'], self.original['turn_id'])
        self.assertEqual(self.current()['input_snapshot'], interrupted['input_snapshot'])
        self.assertTrue(any(item['attempt_id'] == self.original['attempt_id'] for item in self.current()['superseded_attempts']))
        with self.assertRaises(EventConflict):
            self.engine.admit_event(self.original['brief_id'], 'final', 'Superseded old result', self.owner)

    def test_stop_fence_survives_boot_and_leaves_same_seat_usable_for_independent_work(self):
        self.engine.stop_session(self.session_id)
        self.engine.reconcile_stops()
        stop_id = self.current()['stop_id']
        self.cold()
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        self.assertEqual(self.current()['stop_id'], stop_id)
        self.assertFalse(self.current()['dispatch_eligible'])
        with self.assertRaises(EventConflict):
            self.engine.admit_event(self.original['brief_id'], 'final', 'Stopped old result', self.owner)
        record = self.trigger.queue.enqueue(self.owner, {'prompt': 'Fresh independent discussion', 'channel': 'other'})
        claimed = self.trigger.queue.claim(self.owner, 'ordinary-worker')
        self.assertEqual(claimed['envelope']['dispatch_id'], record['envelope']['dispatch_id'])

    def test_crashed_pending_context_preparation_never_automatically_launches(self):
        manager = self.managed()
        def pending(value):
            value['state'] = 'retrying'
            value['pending_retry'] = {'request_id': uuid.uuid4().hex, 'old_invocation': deepcopy(value['active_invocation']),
                'status': 'preparing_contexts', 'context': {'key': 'retry-fixture/editor',
                'launch_attempt': uuid.uuid4().hex, 'state': 'starting', 'clean_context': False}}
        self.sessions._event_update(self.session_id, pending)
        intent, records = deepcopy(self.current()['pending_retry']), deepcopy(self.records())
        self.cold(manager)
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex)
        self.assertEqual(self.current()['pending_retry']['request_id'], intent['request_id'])
        self.assertEqual(self.current()['pending_retry']['context']['launch_attempt'], intent['context']['launch_attempt'])
        self.assertEqual(self.records(), records)
        manager.prepare_retry_context.assert_not_called()


if __name__ == '__main__':
    unittest.main()
