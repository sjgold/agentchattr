"""Recovered transport settlement, real ledger and explicitly supplied proof data."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from tests import test_dispatch_queue as fixture


class ResultSettlementTests(unittest.TestCase):
    def setUp(self):
        base = fixture.DispatchQueueTests()
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.root, self.store, self.owner, self.peer = base.root, base.store, base.instance, base.peer
        self.path = base.ledger
        self.first = self.store.enqueue(self.owner, fixture.envelope())
        self.dispatch = self.first['envelope']['dispatch_id']
        self.store.claim(self.owner, 'original-consumer')
        self.store.acknowledge(self.owner, self.dispatch, 'original-consumer')
        self.before = self.store.owned(self.owner, self.dispatch)
        self.peer_record = self.store.enqueue(self.peer, fixture.envelope(channel='peer'))
        self.evidence = {'local_ended': True, 'dispatch_id': self.dispatch,
            'seat_identity_id': self.owner['identity_id'], 'launch_attempt': uuid.uuid4().hex,
            'verification_basis': 'observed_child_exit_and_ipc'}

    def settle(self, **changes):
        return self.store.settle_recovered(self.dispatch, self.owner['identity_id'], evidence={**self.evidence, **changes})

    def test_exact_recovery_preserves_transport_and_records_only_internal_settlement(self):
        settled = self.settle()
        self.assertEqual(settled['state'], 'settled_recovered')
        self.assertEqual(settled['envelope'], self.before['envelope'])
        self.assertEqual(settled['consumer_id'], 'original-consumer')
        self.assertEqual(settled['events'][:-1], self.before['events'])
        self.assertEqual(settled['events'][-1]['state'], 'settled_recovered')
        self.assertEqual(settled['recovery']['source'], 'result_recovery')
        self.assertEqual(settled['recovery']['launch_attempt'], self.evidence['launch_attempt'])
        self.assertEqual(settled['recovery']['verification_basis'], self.evidence['verification_basis'])
        self.assertGreater(settled['recovery']['at'], 0)
        self.assertEqual(self.store.owned(self.peer, self.peer_record['envelope']['dispatch_id']), self.peer_record)

    def test_unproven_local_end_refusal_preserves_exact_ledger(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.settle(local_ended=False)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.owned(self.owner, self.dispatch), self.before)

    def test_exact_replay_after_reopen_is_byte_identical_and_changed_proof_conflicts(self):
        def settle(_):
            return type(self.store)(self.root).settle_recovered(self.dispatch, self.owner['identity_id'], evidence=deepcopy(self.evidence))
        with ThreadPoolExecutor(max_workers=5) as pool:
            outcomes = list(pool.map(settle, range(5)))
        self.assertEqual(outcomes, [outcomes[0]] * 5)
        first = outcomes[0]
        self.assertEqual(len(first['events']), len(self.before['events']) + 1)
        before = self.path.read_bytes()
        reopened = type(self.store)(self.root)
        self.assertEqual(reopened.settle_recovered(self.dispatch, self.owner['identity_id'], evidence=deepcopy(self.evidence)), first)
        self.assertEqual(self.path.read_bytes(), before)
        for changes in ({'launch_attempt': uuid.uuid4().hex}, {'verification_basis': 'protocol_one_no_invocations'},
                        {'dispatch_id': uuid.uuid4().hex}, {'seat_identity_id': self.peer['identity_id']}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.settle(**changes)
            self.assertEqual(self.path.read_bytes(), before)
        first['events'].clear()
        first['recovery']['source'] = 'mutated return'
        self.assertEqual(self.store.owned(self.owner, self.dispatch)['recovery']['source'], 'result_recovery')
        self.assertGreater(len(self.store.owned(self.owner, self.dispatch)['events']), 0)

    def test_all_allowed_held_states_and_api_proof_bases_preserve_history(self):
        bases = ('all_bound_invocations_ended', 'protocol_one_no_invocations',
                 'bound_invocation_birth_and_observed_absent', 'observed_child_exit_and_ipc')
        for state in ('dispatched', 'acknowledged', 'uncertain', 'failed'):
            for basis in bases:
                instance = {'name': 'fixture-' + state, 'identity_id': uuid.uuid4().hex}
                record = self.store.enqueue(instance, fixture.envelope())
                dispatch = record['envelope']['dispatch_id']
                self.store.claim(instance, 'retained-consumer')
                if state == 'acknowledged':
                    self.store.acknowledge(instance, dispatch, 'retained-consumer')
                elif state == 'uncertain':
                    self.store.uncertain(instance, dispatch, 'retained-consumer')
                elif state == 'failed':
                    self.store.release(instance, dispatch, 'retained-consumer', failed=True, error='local_delivery_failure')
                original = self.store.owned(instance, dispatch)
                proof = {**self.evidence, 'dispatch_id': dispatch, 'seat_identity_id': instance['identity_id'], 'verification_basis': basis}
                with self.subTest(state=state, basis=basis):
                    settled = self.store.settle_recovered(dispatch, instance['identity_id'], evidence=proof)
                    self.assertEqual(settled['state'], 'settled_recovered')
                    self.assertEqual(settled['envelope'], original['envelope'])
                    self.assertEqual(settled['consumer_id'], 'retained-consumer')
                    self.assertEqual(settled['events'][:-1], original['events'])
                    self.assertEqual(settled['recovery']['verification_basis'], basis)
                    for forbidden in ('cancellation', 'cancellation_receipts', 'cancellation_id', 'stop_id', 'child_exit_code', 'acknowledged_at'):
                        self.assertEqual(settled.get(forbidden), original.get(forbidden))
        self.assertEqual(self.store.owned(self.peer, self.peer_record['envelope']['dispatch_id']), self.peer_record)

    def test_invalid_or_wrong_target_proof_is_refused_without_any_ledger_change(self):
        before = self.path.read_bytes()
        invalid = [None, {}] + [{**self.evidence, 'local_ended': value} for value in (False, 1, 'true', None)]
        invalid += [{**self.evidence, key: value} for key, value in (
            ('dispatch_id', uuid.uuid4().hex), ('seat_identity_id', self.peer['identity_id']),
            ('launch_attempt', 'A' * 32), ('launch_attempt', '../escape'), ('launch_attempt', True),
            ('verification_basis', 'wrapper_age'), ('verification_basis', 'durable_receipt_and_observed_absent'))]
        invalid += [{key: value for key, value in self.evidence.items() if key != missing} for missing in self.evidence]
        for evidence in invalid:
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                self.store.settle_recovered(self.dispatch, self.owner['identity_id'], evidence=evidence)
            self.assertEqual(self.path.read_bytes(), before)
        for dispatch, identity in ((uuid.uuid4().hex, self.owner['identity_id']), (self.dispatch, self.peer['identity_id'])):
            with self.subTest(target=(dispatch, identity)), self.assertRaises(ValueError):
                self.store.settle_recovered(dispatch, identity, evidence=self.evidence)
            self.assertEqual(self.path.read_bytes(), before)

    def test_queued_cancelling_cancelled_and_released_transports_never_rewrite(self):
        for state in ('queued', 'cancelling', 'cancelled', 'released'):
            instance = {'name': 'fixture-' + state, 'identity_id': uuid.uuid4().hex}
            record = self.store.enqueue(instance, fixture.envelope())
            dispatch = record['envelope']['dispatch_id']
            if state == 'cancelled':
                self.store.cancel_dispatch(dispatch, uuid.uuid4().hex)
            elif state != 'queued':
                self.store.claim(instance, 'worker')
                if state == 'released':
                    self.store.release(instance, dispatch, 'worker')
                else:
                    self.store.cancel_dispatch(dispatch, uuid.uuid4().hex)
            self.assertEqual(self.store.owned(instance, dispatch)['state'], state)
            before = self.path.read_bytes()
            proof = {**self.evidence, 'dispatch_id': dispatch, 'seat_identity_id': instance['identity_id']}
            with self.subTest(state=state), self.assertRaises(ValueError):
                self.store.settle_recovered(dispatch, instance['identity_id'], evidence=proof)
            self.assertEqual(self.path.read_bytes(), before)

    def test_failed_atomic_settlement_preserves_bytes_and_no_memory_leaks_later(self):
        before = self.path.read_bytes()
        replace = Path.replace
        def fault(source, destination):
            if Path(destination) == self.path:
                raise OSError('fixture recovered settlement replace failure')
            return replace(source, destination)
        with patch.object(Path, 'replace', new=fault):
            with self.assertRaises(OSError):
                self.settle()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(type(self.store)(self.root).owned(self.owner, self.dispatch), self.before)
        self.store.enqueue(self.peer, fixture.envelope(channel='peer'))
        self.assertEqual(self.store.owned(self.owner, self.dispatch), self.before)
        self.assertNotIn('recovery', self.store.owned(self.owner, self.dispatch))

    def test_terminal_settlement_is_not_claimable_or_releasable_and_peer_remains_usable(self):
        settled = self.settle()
        reopened = type(self.store)(self.root)
        self.assertEqual(reopened.owned(self.owner, self.dispatch), settled)
        self.assertIsNone(reopened.claim(self.owner, 'replacement-consumer'))
        before = self.path.read_bytes()
        with self.assertRaises((ValueError, PermissionError)):
            reopened.release(self.owner, self.dispatch, 'original-consumer')
        self.assertEqual(self.path.read_bytes(), before)
        peer = reopened.claim(self.peer, 'independent-consumer')
        self.assertEqual(peer['envelope'], self.peer_record['envelope'])
        reopened.release(self.peer, peer['envelope']['dispatch_id'], 'independent-consumer')
        self.assertEqual(reopened.owned(self.owner, self.dispatch), settled)
        self.assertIsInstance(reopened.status(), dict)

if __name__ == '__main__':
    unittest.main()
