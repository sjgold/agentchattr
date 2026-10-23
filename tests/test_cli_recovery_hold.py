"""CLI recovery holds and coordinator repair; exit dictionaries are algorithm inputs only."""
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

from dispatch_queue import QueueConflict, QueueStore
from queue_coordinator import CoordinatedQueue
from session_store import SessionStore
from tests import test_dispatch_queue as ledger_fixture
from tests import test_result_owner_wiring as managed_fixture


class CliRecoveryHoldTests(unittest.TestCase):
    def setUp(self):
        managed_fixture.ResultOwnerWiringTests.setUp(self)
        self.owner, _ = self.fixture.ready('cli')
        self.run = managed_fixture.ResultOwnerWiringTests.start(self, self.owner['name'])
        self.coordinated = self.trigger.queue
        self.store = self.coordinated._queue
        self.path = self.fixture.root / 'queue' / 'ledger.json'
        self.dispatch = self.run['active_invocation']['dispatch_id']

    def admit_selected(self):
        message = self.engine.send_chat(self.owner, 'Selected café\r\n@all literal output',
            dispatch_id=self.dispatch, channel=self.run['channel'])
        candidate = self.engine.cli_message_candidate(self.run['id'], message['id'])
        intent = {key: candidate[key] for key in ('message_uid', 'snapshot_hash', 'checkpoint')}
        intent['request_id'] = uuid.uuid4().hex
        return self.sessions.admit_selected_cli_event(self.run['id'], self.messages.get_snapshot(message['id']),
                                                       **intent)

    def held(self, dispatch=None, owner=None):
        dispatch, owner = dispatch or self.dispatch, owner or self.owner
        return self.store.hold_recovered(dispatch, owner['identity_id'], dispatch, selected_cli=True)

    def blocked(self, queue, owner, consumer='new-consumer'):
        try:
            result = queue.claim(owner, consumer)
        except QueueConflict:
            return
        self.assertIsNone(result, 'held identity must not acquire new work')

    def state_record(self, state):
        owner = {'name': 'algorithm-' + state, 'identity_id': uuid.uuid4().hex}
        dispatch = self.store.enqueue(owner, ledger_fixture.envelope())['envelope']['dispatch_id']
        if state != 'queued':
            self.store.claim(owner, 'actual-consumer')
        if state == 'acknowledged':
            self.store.acknowledge(owner, dispatch, 'actual-consumer')
        elif state == 'uncertain':
            self.store.uncertain(owner, dispatch, 'actual-consumer')
        elif state in ('failed', 'released'):
            self.store.release(owner, dispatch, 'actual-consumer', failed=state == 'failed')
        elif state in ('cancelling', 'cancelled'):
            self.store.cancel_dispatch(dispatch, uuid.uuid4().hex)
            if state == 'cancelled':
                self.store.cancellation_receipt(owner, dispatch, 'actual-consumer', 'local_ended')
        return owner, dispatch

    def proof(self, dispatch, owner, basis='retained_native_handle_observed_end'):
        # Algorithm input only, not evidence that this fixture ran a native child.
        return dict(local_ended=True, dispatch_id=dispatch, seat_identity_id=owner['identity_id'],
                    launch_attempt=uuid.uuid4().hex, verification_basis=basis)

    def test_selected_cli_can_hold_a_queued_dispatch_without_rewriting_it(self):
        before = self.store.owned(self.owner, self.dispatch)
        held = self.store.hold_recovered(self.dispatch, self.owner['identity_id'], self.dispatch,
                                         selected_cli=True)
        self.assertEqual({key: value for key, value in held.items() if key != 'recovery_hold'}, before)
        self.assertIs(held['recovery_hold']['cleared'], False)
        self.assertEqual(held['recovery_hold']['result_id'], self.dispatch)

    def test_durable_selected_admission_installs_hold_before_cancel_and_blocks_next_claim(self):
        self.admit_selected()
        next_record = self.store.enqueue(self.owner, ledger_fixture.envelope(channel='unrelated-job'))
        original_cancel = self.store.cancel_dispatch
        def cancel_after_hold(dispatch_id, cancellation_id):
            record = self.store.owned(self.owner, dispatch_id)
            self.assertIn('recovery_hold', record, 'durable selected fence must install hold BEFORE cancelling')
            return original_cancel(dispatch_id, cancellation_id)
        with patch.object(self.store, 'cancel_dispatch', side_effect=cancel_after_hold):
            self.blocked(self.coordinated, self.owner)
        held = self.store.owned(self.owner, self.dispatch)
        self.assertEqual(held['state'], 'cancelled')
        self.assertIs(held['recovery_hold']['cleared'], False)
        self.assertEqual(self.store.owned(self.owner, next_record['envelope']['dispatch_id']), next_record)

    def test_eight_selected_states_preserve_record_and_default_api_contract_and_strict_bool(self):
        legacy_allowed = {'dispatched', 'acknowledged', 'uncertain', 'failed'}
        for state in ('queued', 'dispatched', 'acknowledged', 'uncertain', 'failed',
                      'cancelling', 'released', 'cancelled'):
            owner, dispatch = self.state_record(state)
            before = self.store.owned(owner, dispatch)
            disk = self.path.read_bytes()
            if state not in legacy_allowed:
                with self.subTest(default=state), self.assertRaises(QueueConflict):
                    self.store.hold_recovered(dispatch, owner['identity_id'], dispatch)
                self.assertEqual(self.path.read_bytes(), disk)
            for invalid in (None, 0, 1, 'true', [], {}):
                with self.subTest(state=state, selected_cli=invalid), self.assertRaises(QueueConflict):
                    self.store.hold_recovered(dispatch, owner['identity_id'], dispatch, selected_cli=invalid)
                self.assertEqual(self.path.read_bytes(), disk)
            held = self.held(dispatch, owner)
            self.assertEqual({key: value for key, value in held.items() if key != 'recovery_hold'}, before)
            self.assertIs(held['recovery_hold']['cleared'], False)
            self.assertIs(held['recovery_hold']['selected_cli'], True)
            self.assertGreater(held['recovery_hold']['held_at'], 0)
            if state in legacy_allowed:
                self.assertEqual(self.store.hold_recovered(dispatch, owner['identity_id'], dispatch), held)

    def test_exact_replay_identity_denial_owner_poll_release_and_peer_job_preservation(self):
        self.store.claim(self.owner, 'original-consumer')
        held = self.held()
        disk = self.path.read_bytes()
        self.assertEqual(self.held(), held)
        self.assertEqual(self.path.read_bytes(), disk)
        for dispatch, identity, result in ((self.dispatch, uuid.uuid4().hex, self.dispatch),
                                         (self.dispatch, self.owner['identity_id'], uuid.uuid4().hex)):
            with self.assertRaises(QueueConflict):
                self.store.hold_recovered(dispatch, identity, result, selected_cli=True)
            self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual(self.store.claim(self.owner, 'original-consumer'), held)
        cancellation_id = uuid.uuid4().hex
        self.store.cancel_dispatch(self.dispatch, cancellation_id)
        poll = self.store.claim(self.owner, 'original-consumer')
        self.assertEqual(poll['state'], 'cancelling')
        self.assertEqual(poll['cancellation_id'], cancellation_id)
        self.blocked(self.store, self.owner)
        self.store.cancellation_receipt(self.owner, self.dispatch, 'original-consumer', 'local_ended')
        successor = self.store.enqueue(self.owner, ledger_fixture.envelope(job_id=99))
        self.blocked(QueueStore(self.fixture.root), self.owner)
        peer = {'name': 'unrelated-peer', 'identity_id': uuid.uuid4().hex}
        job = self.store.enqueue(peer, ledger_fixture.envelope(job_id=88))
        self.assertEqual(self.store.claim(peer, 'peer-consumer')['envelope'], job['envelope'])
        self.assertEqual(self.store.owned(self.owner, successor['envelope']['dispatch_id']), successor)
        # Authentic release is separate from cancellation and must not erase a hold.
        released_owner, released_dispatch = self.state_record('dispatched')
        self.held(released_dispatch, released_owner)
        released = self.store.release(released_owner, released_dispatch, 'actual-consumer')
        self.assertEqual(released['state'], 'released')
        self.assertIs(released['recovery_hold']['cleared'], False)

    def test_real_hold_replace_failure_rolls_back_then_reload_reconciles_before_claim(self):
        self.admit_selected()
        next_record = self.store.enqueue(self.owner, ledger_fixture.envelope(job_id=101))
        disk, before = self.path.read_bytes(), self.store.owned(self.owner, self.dispatch)
        replace = Path.replace
        def fail_ledger(path, target):
            if Path(target) == self.path:
                raise OSError('Injected recovery hold persistence failure')
            return replace(path, target)
        with patch.object(Path, 'replace', fail_ledger), self.assertRaises(OSError):
            self.coordinated.claim(self.owner, 'new-consumer')
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual(self.store.owned(self.owner, self.dispatch), before)
        reloaded = CoordinatedQueue(QueueStore(self.fixture.root), SessionStore(str(self.sessions._path)),
                                    threading.RLock())
        self.blocked(reloaded, self.owner)
        target = self.store.owned(self.owner, self.dispatch)
        self.assertEqual(target['state'], 'cancelled')
        self.assertIs(target['recovery_hold']['cleared'], False)
        self.assertEqual(self.store.owned(self.owner, next_record['envelope']['dispatch_id']), next_record)

    def test_stop_before_hold_preserves_cancel_receipts_and_cleared_hold_is_not_recreated(self):
        self.store.claim(self.owner, 'original-consumer')
        self.admit_selected()
        stopped = self.sessions.stop_run(self.run['id'], 'Stop after durable selected event')
        self.store.cancel_run(self.run['run_id'], stopped['stop_id'])
        cancelled = self.store.cancellation_receipt(self.owner, self.dispatch, 'original-consumer', 'local_ended')
        self.blocked(self.coordinated, self.owner)
        held = self.store.owned(self.owner, self.dispatch)
        self.assertEqual(held['stop_id'], stopped['stop_id'])
        self.assertNotIn('cancellation_id', held)
        for key in ('state', 'stop_id', 'cancellation', 'cancellation_receipts'):
            self.assertEqual(held[key], cancelled[key])
        evidence = self.proof(self.dispatch, self.owner, 'durable_receipt_and_observed_absent')
        cleared = self.store.settle_recovered(self.dispatch, self.owner['identity_id'], evidence=evidence)
        self.assertEqual(cleared['state'], 'cancelled')
        self.assertIs(cleared['recovery_hold']['cleared'], True)
        for key in ('stop_id', 'cancellation', 'cancellation_receipts'):
            self.assertEqual(cleared[key], cancelled[key])
        self.assertEqual(cleared['events'][-1]['state'], 'recovery_hold_cleared')
        disk = self.path.read_bytes()
        self.coordinated.claim(self.owner, 'new-consumer')
        self.assertEqual(self.path.read_bytes(), disk)

    def test_cli_basis_settlement_exact_replay_released_clear_and_bad_proofs_do_not_mutate(self):
        for basis in ('durable_receipt_and_observed_absent', 'retained_native_handle_observed_end'):
            api_owner, api_dispatch = self.state_record('dispatched')
            default = self.store.hold_recovered(api_dispatch, api_owner['identity_id'], api_dispatch)
            self.assertNotIn('selected_cli', default['recovery_hold'])
            default_disk = self.path.read_bytes()
            with self.assertRaises(QueueConflict):
                self.store.settle_recovered(api_dispatch, api_owner['identity_id'],
                    evidence=self.proof(api_dispatch, api_owner, basis))
            self.assertEqual(self.path.read_bytes(), default_disk)
            owner, dispatch = self.state_record('released')
            self.held(dispatch, owner)
            evidence = self.proof(dispatch, owner, basis)
            disk = self.path.read_bytes()
            for changes in ({'local_ended': 1}, {'local_ended': False}, {'dispatch_id': uuid.uuid4().hex},
                            {'seat_identity_id': uuid.uuid4().hex}, {'launch_attempt': 'bad'},
                            {'verification_basis': 'invented-proof'}):
                with self.subTest(basis=basis, changes=changes), self.assertRaises(QueueConflict):
                    self.store.settle_recovered(dispatch, owner['identity_id'], evidence=dict(evidence, **changes))
                self.assertEqual(self.path.read_bytes(), disk)
            settled = self.store.settle_recovered(dispatch, owner['identity_id'], evidence=evidence)
            self.assertEqual(settled['state'], 'settled_recovered')
            self.assertIs(settled['recovery_hold']['cleared'], True)
            after = self.path.read_bytes()
            self.assertEqual(self.store.settle_recovered(dispatch, owner['identity_id'], evidence=evidence), settled)
            self.assertEqual(self.path.read_bytes(), after)
            next_record = self.store.enqueue(owner, ledger_fixture.envelope())
            self.assertEqual(self.store.claim(owner, 'replacement')['envelope'], next_record['envelope'])

    def test_ordinary_retry_fence_cancels_only_target_without_creating_selected_hold(self):
        invocation = self.run['active_invocation']
        history = {key: invocation[key] for key in ('dispatch_id', 'attempt_id', 'expected_identity_id',
                                                  'run_id', 'turn_id', 'input_revision')}
        history.update(reason='operator_retry', request_id=uuid.uuid4().hex)
        # Durable ordinary Retry boundary; no manager/process lifecycle claim.
        self.sessions._event_update(self.run['id'], lambda value: value['superseded_attempts'].append(history))
        job = self.store.enqueue(self.owner, ledger_fixture.envelope(job_id=303))
        claimed = self.coordinated.claim(self.owner, 'next-job-consumer')
        self.assertEqual(claimed['envelope'], job['envelope'])
        target = self.store.owned(self.owner, self.dispatch)
        self.assertEqual(target['state'], 'cancelled')
        self.assertNotIn('recovery_hold', target)
