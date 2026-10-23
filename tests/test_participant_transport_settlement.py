"""Retired cancellation settlement; explicit algorithm evidence, no native exit claim."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

from dispatch_queue import QueueConflict, QueueStore
from queue_coordinator import CoordinatedQueue
from session_store import SessionStore
from tests import test_participant_transport_hold as fixture
from tests import test_dispatch_queue as ledger_fixture


class ParticipantTransportSettlementTests(unittest.TestCase):
    def setUp(self):
        fixture.ParticipantTransportHoldTests.setUp(self)
        self.raw.claim(self.owner,'actual-consumer')
        self.sessions.skip_participant(self.run['id'],**self.intent)
        self.queue._reconcile()
        self.record=self.raw.owned(self.owner,self.dispatch)
        self.assertEqual(self.record['state'],'cancelling')
        self.evidence=fixture.ParticipantTransportHoldTests.proof(self)

    def settle(self,evidence=None):
        return self.queue.settle_old_transport(self.run['id'],self.intent['request_id'],
                                               self.evidence if evidence is None else evidence)

    def audit(self):
        return self.sessions.get(self.run['id'])['superseded_attempts'][-1]['old_transport']

    def refused_unchanged(self,callback):
        disk,memory=self.sessions._path.read_bytes(),self.sessions.list_all()
        ledger=self.path.read_bytes()
        with self.assertRaises(ValueError):callback()
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(self.sessions.list_all(),memory)
        self.assertEqual(self.path.read_bytes(),ledger)

    def new_retired(self,state='dispatched',owner=None):
        fixture.ParticipantTransportHoldTests.new_run(self,owner)
        self.evidence=fixture.ParticipantTransportHoldTests.proof(self)
        if state!='queued':self.raw.claim(self.owner,'actual-consumer')
        if state in ('failed','released'):
            self.raw.release(self.owner,self.dispatch,'actual-consumer',failed=state=='failed')
        self.sessions.skip_participant(self.run['id'],**self.intent)
        self.queue._reconcile()
        if state=='cancelled':
            self.raw.cancellation_receipt(self.owner,self.dispatch,'actual-consumer','local_ended')
        self.record=self.raw.owned(self.owner,self.dispatch)

    def test_raw_completion_records_internal_proof_without_worker_bearer_or_selected_hold(self):
        result=self.raw.confirm_retired_exit(self.dispatch,self.record['cancellation_id'],evidence=self.evidence)
        self.assertEqual(result['state'],'cancelled')
        self.assertEqual(result['cancellation']['status'],'local_ended')
        self.assertEqual(result['cancellation']['source'],'runtime_reconciliation')
        self.assertNotIn('recovery_hold',result)
        self.assertFalse(self.sessions.get(self.run['id'])['superseded_attempts'][-1]['old_transport']['resolved'])

    def test_coordinator_commits_exact_queue_completion_before_resolving_old_transport(self):
        original=self.sessions.resolve_old_transport
        def queue_first(*args,**kwargs):
            record=self.raw.owned(self.owner,self.dispatch)
            self.assertEqual(record['state'],'cancelled')
            self.assertEqual(record['cancellation']['source'],'runtime_reconciliation')
            self.assertFalse(self.audit()['resolved'])
            return original(*args,**kwargs)
        with patch.object(self.sessions,'resolve_old_transport',side_effect=queue_first):
            result=self.settle()
        transport=result['superseded_attempts'][-1]['old_transport']
        self.assertTrue(transport['resolved'])
        cancelled=self.raw.owned(self.owner,self.dispatch)
        self.assertEqual(cancelled['state'],'cancelled')
        self.assertEqual(cancelled['consumer_id'],'actual-consumer')
        self.assertEqual(cancelled['envelope'],self.record['envelope'])
        self.assertEqual(cancelled['cancellation']['source'],'runtime_reconciliation')

    def test_raw_strict_proof_and_exact_cancellation_scope_do_not_mutate_on_refusal(self):
        for changes in ({'local_ended':False},{'local_ended':1},{'dispatch_id':uuid.uuid4().hex},
                        {'seat_identity_id':uuid.uuid4().hex},{'launch_attempt':'bad'},
                        {'wrapper_status':'live'},{'wrapper_status':'uncertain'},
                        {'child_exit_code':True},{'child_exit_code':None},
                        {'verification_basis':'bare_worker_receipt'}):
            with self.subTest(changes=changes):
                self.refused_unchanged(lambda:self.raw.confirm_retired_exit(self.dispatch,
                    self.record['cancellation_id'],evidence=dict(self.evidence,**changes)))
        for cancellation in (uuid.uuid4().hex,True,'../bad'):
            with self.subTest(cancellation=cancellation):
                self.refused_unchanged(lambda:self.raw.confirm_retired_exit(self.dispatch,cancellation,
                                                                          evidence=self.evidence))
        # Queue has no frozen launch reference on first completion; the
        # coordinator MUST reject a different well-formed launch before writes.
        wrong_launch=dict(self.evidence,launch_attempt=uuid.uuid4().hex)
        self.refused_unchanged(lambda:self.settle(wrong_launch))

    def test_stop_id_fallback_preserves_stop_state_and_default_api_confirmation_guard(self):
        self.settle()
        fixture.ParticipantTransportHoldTests.new_run(self)
        self.evidence=fixture.ParticipantTransportHoldTests.proof(self)
        self.raw.claim(self.owner,'actual-consumer')
        self.sessions.skip_participant(self.run['id'],**self.intent)
        stopped=self.sessions.stop_run(self.run['id'],'Stop before retired cancellation reconcile')
        self.queue._reconcile()
        self.record=self.raw.owned(self.owner,self.dispatch)
        self.assertEqual(self.record['stop_id'],stopped['stop_id'])
        self.assertNotIn('cancellation_id',self.record)
        with self.assertRaises(QueueConflict):
            self.raw.confirm_local_exit(self.dispatch,stopped['stop_id'],evidence=self.evidence)
        self.settle()
        result=self.raw.owned(self.owner,self.dispatch)
        self.assertEqual(result['state'],'cancelled')
        self.assertEqual(result['stop_id'],stopped['stop_id'])
        self.assertNotIn('cancellation_id',result)
        self.assertEqual(result['cancellation']['source'],'runtime_reconciliation')
        self.assertTrue(self.sessions.get(self.run['id'])['stop_id'])

    def test_queued_failed_released_and_auth_cancelled_records_keep_terminal_history(self):
        self.settle()
        for state in ('queued','failed','released','cancelled'):
            self.new_retired(state)
            before=self.raw.owned(self.owner,self.dispatch)
            self.settle()
            self.assertTrue(self.audit()['resolved'])
            self.assertEqual(self.raw.owned(self.owner,self.dispatch),before,state)
            self.assertNotIn('recovery_hold',before)

    def test_unrelated_active_same_identity_refuses_before_writes_and_preserves_work(self):
        self.raw.cancellation_receipt(self.owner,self.dispatch,'actual-consumer','local_ended')
        job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=811))
        active=self.raw.claim(self.owner,'unrelated-consumer')
        self.assertEqual(active['envelope'],job['envelope'])
        self.refused_unchanged(self.settle)
        self.assertEqual(self.raw.owned(self.owner,job['envelope']['dispatch_id']),active)
        self.assertFalse(self.audit()['resolved'])

    def test_missing_ledger_is_not_created_and_only_audit_is_resolved(self):
        self.settle()
        with patch.object(self.queue,'enqueue',side_effect=OSError('Unpublished retired intent')):
            self.engine.start_session('seal-test','unpublished',{'reader':self.owner['name']},'operator',input_text='Exact source')
        self.run=self.sessions.list_all('unpublished')[0]
        self.dispatch=self.run['active_invocation']['dispatch_id']
        self.sessions._event_update(self.run['id'],lambda value:value.update(state='waiting'))
        self.engine.monitor_turns(now=self.run['active_invocation']['monitoring']['ack_deadline']+.1)
        self.run=self.sessions.get(self.run['id'])
        self.intent.update(checkpoint_id=self.run['turn_recovery']['checkpoint_id'],
            attempt_id=self.run['active_invocation']['attempt_id'],request_id=uuid.uuid4().hex)
        self.sessions.skip_participant(self.run['id'],**self.intent)
        self.evidence=fixture.ParticipantTransportHoldTests.proof(self)
        before=self.path.read_bytes()
        self.settle()
        self.assertEqual(self.path.read_bytes(),before)
        self.assertTrue(self.audit()['resolved'])
        self.assertFalse(any(record['envelope']['dispatch_id']==self.dispatch for record in self.raw.for_identity(self.owner)))

    def test_four_thread_resolution_replay_reload_stop_and_copy_are_stable(self):
        gate=threading.Barrier(4)
        def settle_once(_):
            gate.wait(timeout=5)
            return self.settle()
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(settle_once,range(4)))
        self.assertTrue(all(result==results[0] for result in results))
        record=self.raw.owned(self.owner,self.dispatch)
        self.assertEqual(sum(event['state']=='cancelled' for event in record['events']),1)
        self.sessions.stop_run(self.run['id'],'Stop after retired completion')
        self.sessions=SessionStore(str(self.sessions._path))
        self.raw=QueueStore(self.fixture.root)
        self.queue=CoordinatedQueue(self.raw,self.sessions,threading.RLock())
        disk,ledger=self.sessions._path.read_bytes(),self.path.read_bytes()
        replay=self.settle()
        replay['superseded_attempts'][-1]['old_transport']['exit_proof']['child_exit_code']=99
        self.assertEqual(self.audit()['exit_proof']['child_exit_code'],0)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(self.path.read_bytes(),ledger)
        self.refused_unchanged(lambda:self.settle(dict(self.evidence,child_exit_code=1)))

    def test_queue_replace_failure_leaves_audit_false_and_same_consumer_can_poll(self):
        before=self.path.read_bytes()
        session_before=self.sessions._path.read_bytes()
        replace=Path.replace
        def fail(path,target):
            if Path(target)==self.path:raise OSError('Injected retired ledger write failure')
            return replace(path,target)
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.settle()
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.sessions._path.read_bytes(),session_before)
        self.assertFalse(self.audit()['resolved'])
        self.assertEqual(self.queue.claim(self.owner,'actual-consumer')['state'],'cancelling')
        self.settle()
        self.assertTrue(self.audit()['resolved'])

    def test_session_write_failure_after_queue_completion_keeps_hold_and_exact_retry_repairs(self):
        replace=Path.replace
        def fail(path,target):
            if Path(target)==self.sessions._path:raise OSError('Injected audit resolution write failure')
            return replace(path,target)
        session_before=self.sessions._path.read_bytes()
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.settle()
        self.assertEqual(self.sessions._path.read_bytes(),session_before)
        self.assertFalse(self.audit()['resolved'])
        record=self.raw.owned(self.owner,self.dispatch)
        self.assertEqual(record['state'],'cancelled')
        job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=901))
        fixture.ParticipantTransportHoldTests.blocked(self)
        ledger=self.path.read_bytes()
        self.settle()
        self.assertEqual(self.path.read_bytes(),ledger)
        self.assertTrue(self.audit()['resolved'])
        self.assertEqual(self.queue.claim(self.owner,'after-proof')['envelope'],job['envelope'])

    def test_api_end_and_no_invocation_proofs_use_adapter_schema_and_preserve_consumer(self):
        self.settle()
        api,_=self.fixture.ready('api')
        for basis,status in (('all_bound_invocations_ended','ended'),('protocol_one_no_invocations','never_spawned')):
            self.new_retired(owner=api)
            evidence=dict(self.evidence,verification_basis=basis,model_status=status)
            evidence.pop('child_exit_code')
            self.refused_unchanged(lambda:self.settle(dict(evidence,model_status='unverified')))
            result=self.settle(evidence)
            self.assertTrue(result['superseded_attempts'][-1]['old_transport']['resolved'])
            record=self.raw.owned(self.owner,self.dispatch)
            self.assertEqual(record['state'],'cancelled')
            self.assertEqual(record['consumer_id'],'actual-consumer')
            proof=result['superseded_attempts'][-1]['old_transport']['exit_proof']
            self.assertEqual(proof['model_status'],status)
            self.assertNotIn('child_exit_code',proof)

    def test_raw_exact_replay_rejects_changed_proof_and_never_returns_old_task_again(self):
        cancellation=self.record['cancellation_id']
        first=self.raw.confirm_retired_exit(self.dispatch,cancellation,evidence=self.evidence)
        ledger=self.path.read_bytes()
        self.assertEqual(self.raw.confirm_retired_exit(self.dispatch,cancellation,evidence=self.evidence),first)
        self.assertEqual(self.path.read_bytes(),ledger)
        for changes in ({'child_exit_code':23},{'launch_attempt':uuid.uuid4().hex},
                        {'verification_basis':'observed_child_exit_and_ipc'}):
            with self.subTest(changes=changes):
                self.refused_unchanged(lambda:self.raw.confirm_retired_exit(self.dispatch,cancellation,
                    evidence=dict(self.evidence,**changes)))
        self.assertIsNone(self.raw.claim(self.owner,'actual-consumer'))
        self.assertFalse(self.audit()['resolved'],'raw ledger completion alone cannot resolve the session')
