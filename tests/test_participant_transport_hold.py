"""Retired participant transport holds; all exit dictionaries are algorithm inputs only."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

from dispatch_queue import QueueConflict, QueueStore
from queue_coordinator import CoordinatedQueue
from session_store import SessionStore
from turn_events import EventConflict, EventValidationError
from tests import test_dispatch_queue as ledger_fixture
from tests import test_participant_skip_storage as skip_fixture
from tests import test_result_owner_wiring as managed_fixture


class ParticipantTransportHoldTests(unittest.TestCase):
    def setUp(self):
        skip_fixture.ParticipantSkipStorageTests.setUp(self)
        self.queue=self.trigger.queue
        self.raw=self.queue._queue
        self.path=self.fixture.root/'queue/ledger.json'
        self.dispatch=self.run['active_invocation']['dispatch_id']

    def skip(self):
        return self.sessions.skip_participant(self.run['id'],**self.intent)

    def proof(self):
        return {'local_ended':True,'dispatch_id':self.dispatch,'seat_identity_id':self.owner['identity_id'],
            'launch_attempt':self.run['participant_bindings']['reader']['launch_provenance']['launch_attempt'],
            'wrapper_status':'observed_exited','child_exit_code':0,
            'verification_basis':'retained_native_handle_observed_end'}

    def blocked(self,queue=None,owner=None,consumer='new-consumer'):
        try:record=(queue or self.queue).claim(owner or self.owner,consumer)
        except QueueConflict:return
        self.assertIsNone(record,'retired physical identity must not claim new work')

    def resolve(self, evidence=None):
        return self.sessions.resolve_old_transport(self.run['id'],self.intent['request_id'],
                                                   self.proof() if evidence is None else evidence)

    def new_run(self, owner=None):
        self.owner=owner or self.owner
        run=managed_fixture.ResultOwnerWiringTests.start(self,self.owner['name'],'held-'+uuid.uuid4().hex[:10])
        skip_fixture.ParticipantSkipStorageTests.stalled(self,run)
        self.dispatch=self.run['active_invocation']['dispatch_id']

    def transport(self):
        return self.sessions.get(self.run['id'])['superseded_attempts'][-1]['old_transport']

    def refused(self,evidence,request_id=None,session_id=None):
        disk,memory=self.sessions._path.read_bytes(),self.sessions.list_all()
        with self.assertRaises((EventConflict,EventValidationError)):
            self.sessions.resolve_old_transport(self.run['id'] if session_id is None else session_id,
                request_id or self.intent['request_id'],evidence)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(self.sessions.list_all(),memory)

    def test_published_skipped_identity_cannot_claim_unrelated_next_job_but_peer_can(self):
        self.skip()
        job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=100))
        self.blocked()
        self.assertEqual(self.raw.owned(self.owner,job['envelope']['dispatch_id']),job)
        peer={'name':'peer','identity_id':uuid.uuid4().hex}
        peer_job=self.raw.enqueue(peer,ledger_fixture.envelope(job_id=200))
        self.assertEqual(self.queue.claim(peer,'peer-consumer')['envelope'],peer_job['envelope'])

    def test_resolve_old_transport_requires_distinct_exact_internal_exit_proof(self):
        self.skip()
        result=self.sessions.resolve_old_transport(self.run['id'],self.intent['request_id'],self.proof())
        transport=result['superseded_attempts'][-1]['old_transport']
        self.assertIs(transport['resolved'],True)
        self.assertEqual(transport['exit_proof']['dispatch_id'],self.dispatch)
        self.assertEqual(transport['exit_proof']['seat_identity_id'],self.owner['identity_id'])

    def test_cold_ineligible_same_active_consumer_receives_cancellation_not_task(self):
        self.raw.claim(self.owner,'authentic-consumer')
        self.sessions._event_update(self.run['id'],lambda value:value.update(state='interrupted',dispatch_eligible=False))
        self.skip()
        record=self.queue.claim(self.owner,'authentic-consumer')
        self.assertEqual(record['state'],'cancelling')
        self.assertEqual(record['envelope']['dispatch_id'],self.dispatch)
        self.assertNotEqual(record['state'],'dispatched')

    def test_unpublished_dispatch_hold_survives_reload_without_fabricating_record(self):
        with patch.object(self.queue,'enqueue',side_effect=OSError('Unpublished dispatch fixture')):
            self.engine.start_session('seal-test','unpublished',{'reader':self.owner['name']},'operator',input_text='Exact source')
        run=self.sessions.list_all('unpublished')[0]
        self.assertIsNotNone(run['active_invocation'])
        # Storage fixture restores monitoring eligibility for the genuinely
        # unpublished invocation; monitor derives a real missing-ack checkpoint.
        self.sessions._event_update(run['id'],lambda value:value.update(state='waiting'))
        self.engine.monitor_turns(now=run['active_invocation']['monitoring']['ack_deadline']+.1)
        self.run=self.sessions.get(run['id'])
        self.dispatch=self.run['active_invocation']['dispatch_id']
        self.intent.update(checkpoint_id=self.run['turn_recovery']['checkpoint_id'],
            attempt_id=self.run['active_invocation']['attempt_id'],request_id=uuid.uuid4().hex)
        self.skip()
        ledger_before=self.path.read_bytes()
        self.sessions=SessionStore(str(self.sessions._path))
        queue=CoordinatedQueue(QueueStore(self.fixture.root),self.sessions,threading.RLock())
        self.blocked(queue)
        self.assertEqual(self.path.read_bytes(),ledger_before)
        self.assertFalse(any(value['envelope']['dispatch_id']==self.dispatch for value in self.raw.for_identity(self.owner)))
        self.resolve()
        job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=505))
        # The original fixture's earlier queued work still exists; it is now
        # eligible again, showing that no per-seat blanket cancellation occurred.
        claimed=queue.claim(self.owner,'after-proof')
        self.assertIsNotNone(claimed)
        self.assertNotEqual(claimed['envelope']['dispatch_id'],self.dispatch)
        self.assertEqual(self.raw.owned(self.owner,job['envelope']['dispatch_id']),job)

    def test_participant_replacement_algorithm_fence_blocks_only_retired_identity(self):
        skipped=self.skip()
        # Durable replacement fence boundary; engine replacement is outside3a.
        self.sessions._event_update(skipped['id'],lambda value:value['superseded_attempts'][-1].update(
            reason='participant_replacement'))
        job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=401))
        self.blocked()
        self.fixture.registry.seed({'new-independent':{'type':'api'}})
        new=self.fixture.registry.register('new-independent')
        new_job=self.raw.enqueue(new,ledger_fixture.envelope(job_id=402))
        self.assertEqual(self.queue.claim(new,'new-identity-consumer')['envelope'],new_job['envelope'])
        self.assertEqual(self.raw.owned(self.owner,job['envelope']['dispatch_id']),job)
        self.assertNotIn('recovery_hold',self.raw.owned(self.owner,self.dispatch))
        self.resolve()
        self.assertEqual(self.queue.claim(self.owner,'retired-now-proven')['envelope'],job['envelope'])

    def test_release_or_failed_worker_transport_alone_never_resolves_physical_audit(self):
        for failed in (False,True):
            if failed:self.new_run()
            self.raw.claim(self.owner,'actual-consumer')
            self.skip()
            released=self.raw.release(self.owner,self.dispatch,'actual-consumer',failed=failed)
            job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=601))
            self.blocked()
            self.assertIs(self.transport()['resolved'],False)
            self.assertEqual(self.raw.owned(self.owner,self.dispatch),released)
            self.assertEqual(self.raw.owned(self.owner,job['envelope']['dispatch_id']),job)
            # Finish this subcase before the next real invocation; queue release
            # is distinct from the internal, explicitly supplied proof.
            self.resolve()
            claimed=self.queue.claim(self.owner,'finished-job')
            self.assertEqual(claimed['envelope'],job['envelope'])
            self.raw.release(self.owner,job['envelope']['dispatch_id'],'finished-job')

    def test_stop_and_authentic_local_ended_receipt_keep_hold_until_distinct_proof(self):
        self.raw.claim(self.owner,'actual-consumer')
        self.skip()
        stopped=self.sessions.stop_run(self.run['id'],'Stop after participant skip')
        self.blocked(consumer='another-consumer')
        cancelling=self.raw.owned(self.owner,self.dispatch)
        self.assertEqual(cancelling['stop_id'],stopped['stop_id'])
        self.assertEqual(self.queue.claim(self.owner,'actual-consumer')['state'],'cancelling')
        receipt=self.raw.cancellation_receipt(self.owner,self.dispatch,'actual-consumer','local_ended')
        job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=702))
        self.blocked()
        self.assertIs(self.transport()['resolved'],False)
        self.resolve()
        self.assertEqual(self.raw.owned(self.owner,self.dispatch),receipt)
        self.assertEqual(self.queue.claim(self.owner,'proven-after-stop')['envelope'],job['envelope'])

    def test_cli_proof_scope_wrapper_child_and_basis_are_strict_and_allowlisted(self):
        self.skip()
        valid=self.proof()
        for changes in ({'local_ended':1},{'local_ended':False},{'dispatch_id':uuid.uuid4().hex},
                        {'seat_identity_id':uuid.uuid4().hex},{'launch_attempt':uuid.uuid4().hex},
                        {'child_exit_code':True},{'child_exit_code':None},{'child_exit_code':'0'},
                        {'wrapper_status':'live'},{'wrapper_status':'uncertain'},
                        {'verification_basis':'protocol_one_no_invocations','model_status':'never_spawned'},
                        {'verification_basis':'raw_worker_receipt'}):
            with self.subTest(changes=changes):self.refused(dict(valid,**changes))
        self.refused(valid,request_id=uuid.uuid4().hex)
        for session_id in (0,True,'1',-1):
            with self.subTest(session_id=session_id):self.refused(valid,session_id=session_id)
        supplied=dict(valid,internal_untrusted_note='must not persist')
        resolved=self.resolve(supplied)
        persisted=resolved['superseded_attempts'][-1]['old_transport']['exit_proof']
        self.assertNotIn('internal_untrusted_note',persisted)
        self.assertEqual(persisted['child_exit_code'],0)
        supplied['child_exit_code']=99
        self.assertEqual(self.transport()['exit_proof']['child_exit_code'],0)

    def test_api_proof_requires_both_supervisor_and_exact_model_history_category(self):
        api,_=self.fixture.ready('api')
        for index,(basis,status) in enumerate((('all_bound_invocations_ended','ended'),
                                               ('protocol_one_no_invocations','never_spawned'))):
            self.new_run(api)
            self.skip()
            evidence=dict(self.proof(),verification_basis=basis,model_status=status)
            evidence.pop('child_exit_code')
            for changes in ({'model_status':'unverified'},{'model_status':'ended' if status=='never_spawned' else 'never_spawned'},
                            {'verification_basis':'retained_native_handle_observed_end'},
                            {'wrapper_status':'live'}):
                with self.subTest(basis=basis,changes=changes):self.refused(dict(evidence,**changes))
            result=self.resolve(evidence)
            proof=result['superseded_attempts'][-1]['old_transport']['exit_proof']
            self.assertEqual(proof['model_status'],status)
            self.assertNotIn('child_exit_code',proof)

    def test_resolver_replay_concurrent_stop_reload_is_byte_and_time_stable(self):
        self.skip()
        proof=self.proof()
        barrier=threading.Barrier(4)
        def resolve_once(_):
            barrier.wait(timeout=5)
            return self.resolve(proof)
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(resolve_once,range(4)))
        self.assertTrue(all(value==results[0] for value in results))
        first=deepcopy(self.transport())
        self.sessions.stop_run(self.run['id'],'Stop after proven retired exit')
        self.sessions=SessionStore(str(self.sessions._path))
        disk=self.sessions._path.read_bytes()
        callbacks=[]
        self.sessions.on_change(lambda *args:callbacks.append(args))
        self.resolve(proof)
        self.assertEqual(self.transport(),first)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(callbacks,[])
        self.refused(dict(proof,child_exit_code=1))

    def test_resolver_atomic_replace_fault_rolls_back_and_does_not_unblock_claim(self):
        self.skip()
        job=self.raw.enqueue(self.owner,ledger_fixture.envelope(job_id=1001))
        self.blocked()
        session_bytes=self.sessions._path.read_bytes()
        memory=self.sessions.list_all()
        ledger_bytes=self.path.read_bytes()
        original=Path.replace
        def fail(path,target):
            if Path(target)==self.sessions._path:raise OSError('Injected old transport resolution fault')
            return original(path,target)
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.resolve()
        self.assertEqual(self.sessions.list_all(),memory)
        self.assertEqual(self.sessions._path.read_bytes(),session_bytes)
        self.assertEqual(self.path.read_bytes(),ledger_bytes)
        self.blocked()
        self.assertEqual(self.raw.owned(self.owner,job['envelope']['dispatch_id']),job)
        self.resolve()
        self.assertEqual(self.queue.claim(self.owner,'after-proof')['envelope'],job['envelope'])

    def test_cold_unverified_task_remains_denied_until_cancelled_even_for_original_consumer(self):
        self.raw.claim(self.owner,'actual-consumer')
        self.sessions._event_update(self.run['id'],lambda value:value.update(dispatch_eligible=False))
        for acknowledge in (False,True):
            if acknowledge:self.raw.acknowledge(self.owner,self.dispatch,'actual-consumer')
            before=self.raw.owned(self.owner,self.dispatch)
            self.blocked(consumer='actual-consumer')
            self.blocked(consumer='wrong-consumer')
            self.assertEqual(self.raw.owned(self.owner,self.dispatch),before)
        self.skip()
        self.assertEqual(self.queue.claim(self.owner,'actual-consumer')['state'],'cancelling')
        self.blocked(consumer='wrong-consumer')
