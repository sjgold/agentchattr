"""Internal local-exit queue settlement and durable Retry ordering, no native claim."""
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
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore


class ColdRetrySettlementTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'session_runs.json'
        self.sessions = SessionStore(str(self.path))
        self.sessions.save_custom_template({'id': 'review', 'name': 'Review', 'roles': ['reviewer', 'editor'],
            'phases': [{'name': 'Evidence', 'participants': ['reviewer'], 'prompt': 'Read source.'},
                       {'name': 'Result', 'participants': ['editor'], 'prompt': 'Use prior result.', 'is_output': True}]})
        self.registry = RuntimeRegistry(str(self.root))
        self.registry.seed({'old': {'type': 'api'}, 'peer': {'type': 'api'}})
        self.owner, self.peer = self.registry.register('old'), self.registry.register('peer')
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        started = self.engine.start_session('review', 'general', {'reviewer': 'peer', 'editor': 'old'},
            'operator', input_text='Exact café\r\nsource')
        self.session_id = started['id']
        first = started['active_invocation']
        self.queue = self.trigger.queue
        self.queue.claim(self.peer, 'peer-consumer')
        self.queue.acknowledge(self.peer, first['dispatch_id'], 'peer-consumer')
        self.engine.admit_event(first['brief_id'], 'final', 'Prior accepted result', self.peer)
        self.queue.release(self.peer, first['dispatch_id'], 'peer-consumer')
        self.old = deepcopy(self.current()['active_invocation'])
        self.launch = uuid.uuid4().hex
        self.provenance = {'key': 'team/api', 'launch_attempt': self.launch,
            'identity_id': self.owner['identity_id'], 'fingerprint': 'a' * 64,
            'effective': {'seat': {'adapter': 'openai-compatible', 'model': 'frozen-model'}}}
        self.sessions._event_update(self.session_id, lambda value: value['participant_bindings']['editor'].update(
            launch_provenance=deepcopy(self.provenance)))
        self.queue.claim(self.owner, 'dead-worker-consumer')
        self.queue.acknowledge(self.owner, self.old['dispatch_id'], 'dead-worker-consumer')
        self.now = time.time() + 1000
        self.engine.monitor_turns(now=self.now)
        self.checkpoint = self.current()['turn_recovery']['checkpoint_id']
        self.request = uuid.uuid4().hex
        self.evidence = {'local_ended': True, 'wrapper_status': 'absent', 'model_status': 'never_spawned',
            'verification_basis': 'protocol_one_no_invocations', 'launch_attempt': self.launch}
        self.independent = self.queue.enqueue(self.peer, {'prompt': 'Independent work', 'channel': 'peer'})

    def current(self):
        return self.sessions.get(self.session_id)

    def peer_record(self):
        return self.queue.owned(self.peer, self.independent['envelope']['dispatch_id'])

    def test_internal_confirm_local_exit_settles_only_exact_cancellation_idempotently(self):
        self.queue.cancel_dispatch(self.old['dispatch_id'], self.request)
        peer = deepcopy(self.peer_record())
        settled = self.queue.confirm_local_exit(self.old['dispatch_id'], self.request, evidence=self.evidence)
        self.assertEqual(settled['state'], 'cancelled')
        self.assertEqual(settled['consumer_id'], 'dead-worker-consumer')
        self.assertEqual(settled['cancellation']['status'], 'local_ended')
        self.assertEqual(settled['cancellation']['source'], 'runtime_reconciliation')
        self.assertEqual(settled['cancellation']['verification_basis'], self.evidence['verification_basis'])
        self.assertEqual(settled['cancellation']['launch_attempt'], self.launch)
        before = (self.root / 'queue/ledger.json').read_bytes()
        self.assertEqual(self.queue.confirm_local_exit(self.old['dispatch_id'], self.request,
                         evidence=self.evidence), settled)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), before)
        self.assertEqual(self.peer_record(), peer)

    def test_invalid_internal_proof_or_atomic_failure_preserves_exact_ledger(self):
        self.queue.cancel_dispatch(self.old['dispatch_id'], self.request)
        before = (self.root / 'queue/ledger.json').read_bytes()
        for evidence, cancellation in ((self.evidence, uuid.uuid4().hex),
            ({**self.evidence, 'local_ended': False}, self.request),
            ({**self.evidence, 'local_ended': 1}, self.request),
            ({**self.evidence, 'launch_attempt': 'not-an-attempt'}, self.request),
            ({**self.evidence, 'verification_basis': 'provider_said_done'}, self.request)):
            with self.subTest(evidence=evidence, cancellation_id=cancellation), self.assertRaises(ValueError):
                self.queue.confirm_local_exit(self.old['dispatch_id'], cancellation, evidence=evidence)
            self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), before)
        with patch('dispatch_queue.atomic_json', side_effect=OSError('fixture settlement write failure')):
            with self.assertRaises(OSError):
                self.queue.confirm_local_exit(self.old['dispatch_id'], self.request, evidence=self.evidence)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), before)
        self.assertEqual(self.queue.owned(self.owner, self.old['dispatch_id'])['state'], 'cancelling')
        self.assertEqual(self.peer_record(), self.independent)

    def proof_manager(self, local_ended):
        manager = Mock(spec=['runtime_exit_proof', 'prepare_retry_context', 'context_status',
                             'launch_provenance', 'restart_readiness', 'boot_id'])
        manager.boot_id = uuid.uuid4().hex
        manager.restart_readiness.return_value = {'state': 'unverified', 'process_verified': False}
        def proof(provenance, dispatch_id=None):
            persisted = SessionStore(str(self.path)).get(self.session_id)
            self.assertTrue(any(item['attempt_id'] == self.old['attempt_id'] for item in persisted['superseded_attempts']))
            self.assertEqual(persisted['pending_retry']['request_id'], self.request)
            self.assertEqual(provenance, self.provenance)
            self.assertEqual(dispatch_id, self.old['dispatch_id'])
            record = self.queue.owned(self.owner, dispatch_id)
            self.assertEqual(record['state'], 'cancelling')
            self.assertEqual(record['cancellation_id'], self.request)
            return deepcopy(self.evidence if local_ended else {'local_ended': False, 'reason': 'unproven_worker_exit'})
        manager.runtime_exit_proof.side_effect = proof
        self.engine._seat_manager = manager
        return manager

    def test_cold_retry_settles_after_fence_and_progresses_same_boot_only_after_new_native_readiness(self):
        manager = self.proof_manager(True)
        self.engine.reconcile_restart(boot_id=manager.boot_id, now=self.now)
        self.assertEqual(self.current()['state'], 'interrupted')
        prior, source, peer = deepcopy(self.current()['admitted_events']), deepcopy(self.current()['input_snapshot']), deepcopy(self.peer_record())
        self.registry.seed({'fresh': {'type': 'api'}})
        fresh = self.registry.register('fresh')
        context = {'state': 'starting', 'key': 'retry-fixture/api', 'launch_attempt': uuid.uuid4().hex,
            'context_id': uuid.uuid4().hex, 'identity_id': None, 'name': None,
            'clean_context': False, 'old_local_ended': True, 'verification_basis': 'isolated_request_packet'}
        def prepare(*args, **kwargs):
            settled = self.queue.owned(self.owner, self.old['dispatch_id'])
            self.assertEqual(settled['state'], 'cancelled')
            self.assertEqual(settled['cancellation']['source'], 'runtime_reconciliation')
            return deepcopy(context)
        manager.prepare_retry_context.side_effect = prepare
        manager.context_status.side_effect = lambda old_context: deepcopy(context)
        manager.launch_provenance.return_value = {**self.provenance, 'key': context['key'],
            'launch_attempt': context['launch_attempt'], 'identity_id': fresh['identity_id']}
        self.engine.retry_turn(self.session_id, self.checkpoint, self.old['attempt_id'], self.request, now=self.now)
        manager.runtime_exit_proof.assert_called_once_with(self.provenance, self.old['dispatch_id'])
        self.assertEqual(self.current()['state'], 'retrying')
        reserved = self.current()['pending_retry']['new_attempt_id']
        self.assertEqual(self.current()['pending_retry']['context']['launch_attempt'], context['launch_attempt'])
        self.assertEqual(len(json.loads((self.root / 'queue/ledger.json').read_text('utf-8'))['records']), 3)
        self.engine.reconcile_restart(boot_id=manager.boot_id, now=self.now + .1)
        self.engine.monitor_turns(now=self.now + .1)
        self.assertEqual(self.current()['state'], 'retrying', 'same-boot operator intent cannot be reclassified cold forever')
        # Ready receipt/identity alone precedes current-boot native proof.
        context.update(state='ready', identity_id=fresh['identity_id'], name=fresh['name'], clean_context=True)
        self.engine.reconcile_restart(boot_id=manager.boot_id, now=self.now + .2)
        self.engine.monitor_turns(now=self.now + .2)
        self.assertEqual(self.current()['state'], 'retrying')
        self.assertEqual(self.current()['pending_retry']['status'], 'preparing_contexts')
        self.assertEqual(self.queue.for_identity(fresh), [])
        manager.restart_readiness.side_effect = lambda identity, boot: {
            'state': 'ready' if identity == fresh['identity_id'] else 'unverified',
            'process_verified': identity == fresh['identity_id']}
        self.engine.reconcile_restart(boot_id=manager.boot_id, now=self.now + .3)
        self.engine.monitor_turns(now=self.now + .3)
        current = self.current()
        self.assertEqual(current['active_invocation']['attempt_id'], reserved)
        self.assertEqual(current['active_invocation']['turn_id'], self.old['turn_id'])
        self.assertEqual(current['active_invocation']['expected_identity_id'], fresh['identity_id'])
        self.assertEqual(current['admitted_events'], prior)
        self.assertEqual(current['input_snapshot'], source)
        self.assertEqual(self.peer_record(), peer)
        self.assertEqual(len(self.queue.for_identity(fresh)), 1)
        self.engine.reconcile_restart(boot_id=manager.boot_id, now=self.now + .4)
        self.engine.monitor_turns(now=self.now + .4)
        self.assertEqual(len(self.queue.for_identity(fresh)), 1)

    def test_unproven_dead_worker_stays_retrying_with_exact_old_ownership_held(self):
        manager = self.proof_manager(False)
        peer = deepcopy(self.peer_record())
        self.engine.retry_turn(self.session_id, self.checkpoint, self.old['attempt_id'], self.request, now=self.now)
        manager.runtime_exit_proof.assert_called_once_with(self.provenance, self.old['dispatch_id'])
        self.assertEqual(self.current()['state'], 'retrying')
        old = self.queue.owned(self.owner, self.old['dispatch_id'])
        self.assertEqual(old['state'], 'cancelling')
        self.assertEqual(old['consumer_id'], 'dead-worker-consumer')
        self.assertEqual(old['cancellation_id'], self.request)
        self.assertEqual(self.peer_record(), peer)
        self.assertEqual(len(self.current()['admitted_events']), 1)
        manager.prepare_retry_context.assert_not_called()


if __name__ == '__main__':
    unittest.main()
