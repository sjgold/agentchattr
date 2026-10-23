"""Conservative saved-result seat holds; real ledger, no native exit claims."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from dispatch_queue import QueueBusy
from tests import test_dispatch_queue as fixture


class ResultHoldTests(unittest.TestCase):
    def setUp(self):
        base = fixture.DispatchQueueTests()
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.store, self.root, self.path = base.store, base.root, base.ledger
        self.owner, self.peer = base.instance, base.peer
        record = self.store.enqueue(self.owner, fixture.envelope())
        self.dispatch = record['envelope']['dispatch_id']
        self.store.claim(self.owner, 'authentic-consumer')
        self.store.acknowledge(self.owner, self.dispatch, 'authentic-consumer')
        self.before = self.store.owned(self.owner, self.dispatch)
        self.next = self.store.enqueue(self.owner, fixture.envelope(channel='next'))
        self.peer_record = self.store.enqueue(self.peer, fixture.envelope(channel='peer'))
        self.proof = {'local_ended': True, 'dispatch_id': self.dispatch, 'seat_identity_id': self.owner['identity_id'],
                      'launch_attempt': uuid.uuid4().hex, 'verification_basis': 'all_bound_invocations_ended'}

    def hold(self):
        return self.store.hold_recovered(self.dispatch, self.owner['identity_id'], self.dispatch)

    def assert_blocked(self, store, consumer='new-consumer'):
        try:
            record = store.claim(self.owner, consumer)
        except QueueBusy:
            return
        self.assertIsNone(record, 'saved-result hold must not permit another dispatch')

    def test_failed_transport_hold_blocks_next_claim_across_reload_but_not_peer(self):
        self.store.release(self.owner, self.dispatch, 'authentic-consumer', failed=True, error='local_delivery_failure')
        held = self.hold()
        self.assertEqual(held['state'], 'failed')
        self.assertEqual(held['recovery_hold']['result_id'], self.dispatch)
        self.assertEqual(held['recovery_hold']['seat_identity_id'], self.owner['identity_id'])
        self.assertIs(held['recovery_hold']['cleared'], False)
        self.assertGreater(held['recovery_hold']['held_at'], 0)
        self.assert_blocked(type(self.store)(self.root))
        peer = self.store.claim(self.peer, 'peer-consumer')
        self.assertEqual(peer['envelope'], self.peer_record['envelope'])
        self.assertEqual(self.store.owned(self.owner, self.next['envelope']['dispatch_id']), self.next)

    def test_existing_owner_can_repoll_and_observe_cancellation_without_clearing_hold(self):
        held = self.hold()
        self.assertEqual(self.store.claim(self.owner, 'authentic-consumer'), held)
        cancellation_id = uuid.uuid4().hex
        self.store.cancel_dispatch(self.dispatch, cancellation_id)
        poll = type(self.store)(self.root).claim(self.owner, 'authentic-consumer')
        self.assertEqual(poll['state'], 'cancelling')
        self.assertIs(poll['recovery_hold']['cleared'], False)
        self.assert_blocked(self.store)

    def test_hold_is_immutable_replay_and_wrong_ids_or_metadata_cannot_rewrite_it(self):
        first = self.hold()
        disk = self.path.read_bytes()
        self.assertEqual(type(self.store)(self.root).hold_recovered(self.dispatch, self.owner['identity_id'], self.dispatch), first)
        self.assertEqual(self.path.read_bytes(), disk)
        for dispatch, identity, result in ((self.dispatch, self.peer['identity_id'], self.dispatch),
            (self.dispatch, self.owner['identity_id'], uuid.uuid4().hex),
            (uuid.uuid4().hex, self.owner['identity_id'], self.dispatch),
            (self.dispatch, self.owner['identity_id'], True),
            ('../escape', self.owner['identity_id'], '../escape')):
            with self.subTest(target=(dispatch,identity,result)), self.assertRaises(ValueError):
                self.store.hold_recovered(dispatch,identity,result)
            self.assertEqual(self.path.read_bytes(),disk)
        malformed = json.loads(disk)
        target = next(value for value in malformed['records'] if value['envelope']['dispatch_id']==self.dispatch)
        target['recovery_hold']['result_id']=uuid.uuid4().hex
        self.path.write_text(json.dumps(malformed),encoding='utf-8')
        changed = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.hold()
        self.assertEqual(self.path.read_bytes(),changed)

    def test_allowed_states_and_authentic_release_retain_uncleared_hold(self):
        for state in ('dispatched','acknowledged','uncertain','failed'):
            instance = {'name':'held-'+state,'identity_id':uuid.uuid4().hex}
            first = self.store.enqueue(instance,fixture.envelope())
            dispatch = first['envelope']['dispatch_id']
            self.store.claim(instance,'same-consumer')
            if state=='acknowledged':
                self.store.acknowledge(instance,dispatch,'same-consumer')
            elif state=='uncertain':
                self.store.uncertain(instance,dispatch,'same-consumer')
            elif state=='failed':
                self.store.release(instance,dispatch,'same-consumer',failed=True,error='local_delivery_failure')
            before = self.store.owned(instance,dispatch)
            held = self.store.hold_recovered(dispatch,instance['identity_id'],dispatch)
            self.assertEqual(held['state'],state)
            self.assertEqual(held['envelope'],before['envelope'])
            self.assertEqual(held['consumer_id'],before['consumer_id'])
            self.assertEqual(held['events'],before['events'])
            if state!='failed':
                held = self.store.release(instance,dispatch,'same-consumer',failed=(state=='uncertain'))
            self.assertIs(held['recovery_hold']['cleared'],False)
            successor = self.store.enqueue(instance,fixture.envelope(channel='later'))
            try:
                actual = type(self.store)(self.root).claim(instance,'replacement-consumer')
            except QueueBusy:
                actual = None
            self.assertIsNone(actual)
            self.assertEqual(self.store.owned(instance,successor['envelope']['dispatch_id']),successor)
        self.assertEqual(self.store.owned(self.peer,self.peer_record['envelope']['dispatch_id']),self.peer_record)

    def test_only_exact_positive_settlement_clears_failed_or_released_hold_and_unblocks(self):
        for failed in (False,True):
            instance = {'name':'proof-fixture','identity_id':uuid.uuid4().hex}
            first = self.store.enqueue(instance,fixture.envelope())
            dispatch = first['envelope']['dispatch_id']
            self.store.claim(instance,'authentic-worker')
            self.store.hold_recovered(dispatch,instance['identity_id'],dispatch)
            released = self.store.release(instance,dispatch,'authentic-worker',failed=failed)
            successor = self.store.enqueue(instance,fixture.envelope(channel='later'))
            evidence = {**self.proof,'dispatch_id':dispatch,'seat_identity_id':instance['identity_id']}
            disk = self.path.read_bytes()
            with self.assertRaises(ValueError):
                self.store.settle_recovered(dispatch,instance['identity_id'],evidence={**evidence,'local_ended':False})
            self.assertEqual(self.path.read_bytes(),disk)
            settled = self.store.settle_recovered(dispatch,instance['identity_id'],evidence=evidence)
            self.assertEqual(settled['state'],'settled_recovered')
            self.assertIs(settled['recovery_hold']['cleared'],True)
            self.assertGreater(settled['recovery_hold']['cleared_at'],0)
            self.assertEqual(settled['recovery_hold']['cleared_basis'],evidence['verification_basis'])
            self.assertEqual(settled['envelope'],released['envelope'])
            self.assertEqual(settled['consumer_id'],released['consumer_id'])
            disk = self.path.read_bytes()
            self.assertEqual(self.store.settle_recovered(dispatch,instance['identity_id'],evidence=evidence),settled)
            self.assertEqual(self.path.read_bytes(),disk)
            claimed = type(self.store)(self.root).claim(instance,'next-worker')
            self.assertEqual(claimed['envelope'],successor['envelope'])

    def test_cancelled_hold_clear_preserves_stop_receipts_and_cancelled_record_state(self):
        self.hold()
        run_id = self.before['envelope']['run_id']
        stop_id = uuid.uuid4().hex
        self.store.cancel_run(run_id,stop_id)
        disk = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.settle_recovered(self.dispatch,self.owner['identity_id'],evidence=self.proof)
        self.assertEqual(self.path.read_bytes(),disk)
        # Simulated authenticated consumer receipt is a queue input, not native
        # child-exit proof. Positive internal proof is separately supplied below.
        cancelled = self.store.cancellation_receipt(self.owner,self.dispatch,'authentic-consumer','local_ended')
        self.assertEqual(cancelled['state'],'cancelled')
        self.assert_blocked(type(self.store)(self.root))
        cleared = self.store.settle_recovered(self.dispatch,self.owner['identity_id'],evidence=self.proof)
        self.assertEqual(cleared['state'],'cancelled')
        for key in ('stop_id','cancellation','cancellation_receipts','consumer_id','envelope'):
            self.assertEqual(cleared[key],cancelled[key])
        self.assertEqual(cleared['events'][:-1],cancelled['events'])
        self.assertEqual(cleared['events'][-1]['state'],'recovery_hold_cleared')
        self.assertIs(cleared['recovery_hold']['cleared'],True)
        self.assertEqual(cleared['recovery']['source'],'result_recovery')
        self.assertEqual(cleared['recovery']['launch_attempt'],self.proof['launch_attempt'])
        disk = self.path.read_bytes()
        self.assertEqual(type(self.store)(self.root).settle_recovered(self.dispatch,self.owner['identity_id'],evidence=self.proof),cleared)
        self.assertEqual(self.path.read_bytes(),disk)
        self.assertEqual(self.store.claim(self.owner,'next-worker')['envelope'],self.next['envelope'])

    def test_atomic_hold_failure_preserves_bytes_without_leaking_a_claim_guard(self):
        self.store.release(self.owner,self.dispatch,'authentic-consumer',failed=True)
        disk = self.path.read_bytes()
        replace = Path.replace
        def fault(path,destination):
            if Path(destination)==self.path:
                raise OSError('fixture hold replace failure')
            return replace(path,destination)
        with patch.object(Path,'replace',new=fault):
            with self.assertRaises(OSError):
                self.hold()
        self.assertEqual(self.path.read_bytes(),disk)
        claimed = type(self.store)(self.root).claim(self.owner,'new-worker')
        self.assertEqual(claimed['envelope'],self.next['envelope'])
        self.assertNotIn('recovery_hold',self.store.owned(self.owner,self.dispatch))

    def test_unheld_terminal_or_queued_states_refuse_hold_but_settled_target_is_noop(self):
        for state in ('queued','released','cancelled','cancelling'):
            instance = {'name':'fixture-'+state,'identity_id':uuid.uuid4().hex}
            record = self.store.enqueue(instance,fixture.envelope())
            dispatch = record['envelope']['dispatch_id']
            if state=='cancelled':
                self.store.cancel_dispatch(dispatch,uuid.uuid4().hex)
            elif state!='queued':
                self.store.claim(instance,'worker')
                if state=='released':
                    self.store.release(instance,dispatch,'worker')
                else:
                    self.store.cancel_dispatch(dispatch,uuid.uuid4().hex)
            disk = self.path.read_bytes()
            with self.subTest(state=state),self.assertRaises(ValueError):
                self.store.hold_recovered(dispatch,instance['identity_id'],dispatch)
            self.assertEqual(self.path.read_bytes(),disk)
        settled = self.store.settle_recovered(self.dispatch,self.owner['identity_id'],evidence=self.proof)
        disk = self.path.read_bytes()
        self.assertEqual(self.hold(),settled)
        self.assertEqual(self.path.read_bytes(),disk)
        self.assertNotIn('recovery_hold',settled)


if __name__ == '__main__':
    unittest.main()
