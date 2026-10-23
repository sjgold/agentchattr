"""Durable participant replacement intent/binding; process/readiness doubles, no native claim."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from api_seats import atomic_json
from session_store import SessionStore
from turn_events import EventConflict, EventValidationError
from tests import test_result_owner_wiring as fixture


class ParticipantReplacementStoreTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.old,_=self.fixture.ready('cli')
        self.source,_=self.fixture.ready('api')
        self.provenance=self.fixture.manager.launch_provenance(self.source)
        self.sessions.save_custom_template({'id':'replace-store','name':'Historical work then replacement',
            'roles':['reader','editor'],'phases':[
                {'name':'Evidence','participants':['reader'],'prompt':'Read source.'},
                {'name':'Review','participants':['editor','reader'],'prompt':'Review evidence.'},
                {'name':'Final','participants':['editor'],'prompt':'Synthesize.','is_output':True}]})
        self.run=self.engine.start_session('replace-store','replacement',
            {'reader':self.source['name'],'editor':self.old['name']},'operator',goal='Keep the approved evidence.',
            input_text='Exact café\r\nreplacement source')
        self.engine.admit_event(self.run['active_invocation']['brief_id'],'final','IMMUTABLE_PRIOR café\r\nresult',self.source)
        self.run=self.sessions.get(self.run['id'])
        record=self.trigger.queue.owned(self.old,self.run['active_invocation']['dispatch_id'])
        self.engine.monitor_turns(now=record['events'][0]['at']+self.run['recovery_policy']['ack_timeout']+.1)
        self.run=self.sessions.get(self.run['id'])
        self.assertEqual(self.run['state'],'stalled')
        self.intent={'checkpoint_id':self.run['turn_recovery']['checkpoint_id'],
            'attempt_id':self.run['active_invocation']['attempt_id'],'request_id':uuid.uuid4().hex,
            'target_provenance':deepcopy(self.provenance),'boot_id':self.fixture.manager.boot_id,
            'reason':'Replace only this current and future editor assignment.'}
        seam=patch.object(self.fixture.manager,'restart_readiness',return_value={'state':'ready','process_verified':True})
        self.readiness=seam.start()
        self.addCleanup(seam.stop)

    def stage(self,**changes):
        return self.sessions.replace_participant(self.run['id'],**dict(self.intent,**changes))

    def clone(self,pending):
        manager=self.fixture.manager
        binding={'child_run_id':self.run['run_id'],'role':'editor'}
        view=manager.prepare_replacement_context(self.provenance,pending['context_key'],binding=binding)
        attempt=next(value for value in manager.attempts.values() if value['id']==view['launch_attempt'])
        owner=self.fixture.registry.register(attempt['base'])
        atomic_json(attempt['receipt'],{'attempt':attempt['id'],'name':owner['name'],'identity_id':owner['identity_id'],
            'state':'ready','adapter_connected':True,'authentication':'unknown','updated_at':time.time(),'confirmed_model':None})
        ready=manager.prepare_replacement_context(self.provenance,pending['context_key'],binding=binding)
        self.assertEqual(ready.get('verified_boot_id'),manager.boot_id,'manager must supply actual boot witness after its readiness seam')
        return ready,manager.launch_provenance(owner)

    def bind(self,context,provenance,**changes):
        return self.sessions.bind_replacement(self.run['id'],self.intent['request_id'],context,provenance,
            **{'boot_id':self.fixture.manager.boot_id,**changes})

    def refused(self,callback):
        disk,memory=self.sessions._path.read_bytes(),self.sessions.list_all()
        with self.assertRaises((EventConflict,EventValidationError)):callback()
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(self.sessions.list_all(),memory)

    def restore(self,baseline,**changes):
        def replace(value):
            value.clear()
            value.update(deepcopy(dict(baseline,**changes)))
        self.sessions._event_update(self.run['id'],replace)

    def test_stage_fences_current_attempt_before_any_effect_and_keeps_cast_and_prior_work(self):
        files={path:path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file() and path!=self.sessions._path}
        spawns=self.fixture.spawn.call_count
        updated=self.stage()
        self.assertEqual(updated['state'],'retrying')
        self.assertIs(updated['dispatch_eligible'],False)
        self.assertEqual(updated['cast'],self.run['cast'])
        self.assertEqual(updated['active_invocation'],self.run['active_invocation'])
        self.assertEqual(updated['admitted_events'],self.run['admitted_events'])
        pending=updated['pending_replacement']
        self.assertEqual(pending['target_provenance'],self.provenance)
        for key in ('new_attempt_id','new_brief_id','new_dispatch_id'):
            self.assertEqual(uuid.UUID(hex=pending[key]).hex,pending[key])
        fence=updated['superseded_attempts'][-1]
        self.assertEqual(fence['reason'],'participant_replacement')
        self.assertEqual(fence['old_transport']['dispatch_id'],self.run['active_invocation']['dispatch_id'])
        self.assertFalse(fence['old_transport']['resolved'])
        self.assertEqual(self.fixture.spawn.call_count,spawns)
        self.assertEqual(files,{path:path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file() and path!=self.sessions._path})

    def test_fresh_binding_updates_only_current_future_role_preserving_historical_work(self):
        staged=self.stage()
        context,provenance=self.clone(staged['pending_replacement'])
        before_queue=self.trigger.queue.status()
        before_messages=self.messages._path.read_bytes()
        updated=self.sessions.bind_replacement(self.run['id'],self.intent['request_id'],context,provenance,
                                                boot_id=self.fixture.manager.boot_id)
        self.assertEqual(updated['state'],'active')
        self.assertTrue(updated['dispatch_eligible'])
        self.assertIsNone(updated['active_invocation'])
        self.assertEqual(updated['pending_replacement']['status'],'dispatching')
        self.assertEqual(updated['cast']['editor'],context['name'])
        self.assertEqual(updated['participant_bindings']['editor']['identity_id'],context['identity_id'])
        self.assertEqual(updated['cast']['reader'],self.run['cast']['reader'])
        for key in ('cast_snapshot','admitted_events','design_snapshot','input_snapshot','rules_snapshot'):
            self.assertEqual(updated[key],self.run[key])
        self.assertEqual(self.trigger.queue.status(),before_queue)
        self.assertEqual(self.messages._path.read_bytes(),before_messages)

    def test_stage_approved_prior_uses_immutable_event_not_edited_or_deleted_chat_and_copies_context(self):
        event=deepcopy(self.run['admitted_events'][0])
        self.messages.get_by_id(event['projected_message_id'])['text']='WRONG_MUTABLE_DISPLAY'
        self.messages.delete([event['projected_message_id']])
        # Existing stored continuation boundary; no human/provider call is inferred.
        continuation={'question_event_id':uuid.uuid4().hex,'question':'Approved question',
                      'answer':'Approved answer café\r\ntext','projected_message_id':None}
        self.sessions._event_update(self.run['id'],lambda value:value['continuation_context'].append(deepcopy(continuation)))
        result=self.stage()
        pending=result['pending_replacement']
        serialized=json.dumps(pending['approved_prior_results'],ensure_ascii=False)
        def strings(value):
            if isinstance(value,str):return [value]
            if isinstance(value,dict):return [text for item in value.values() for text in strings(item)]
            if isinstance(value,list):return [text for item in value for text in strings(item)]
            return []
        self.assertIn(event['content'],strings(pending['approved_prior_results']))
        self.assertNotIn('WRONG_MUTABLE_DISPLAY',serialized)
        self.assertEqual(pending['approved_continuation_context'],[continuation])
        self.assertEqual(result['admitted_events'][0],event)
        pending['target_provenance']['effective']['seat']['model']='CALLER_MUTATION'
        pending['approved_prior_results'].clear()
        pending['approved_continuation_context'][0]['answer']='CALLER_MUTATION'
        durable=self.sessions.get(self.run['id'])['pending_replacement']
        self.assertEqual(durable['target_provenance'],self.provenance)
        self.assertTrue(durable['approved_prior_results'])
        self.assertEqual(durable['approved_continuation_context'],[continuation])

    def test_same_boot_replay_and_explicit_new_boot_resume_keep_reserved_ids_and_frozen_intent(self):
        first=self.stage(now=123456.5)
        disk=self.sessions._path.read_bytes()
        calls=[]
        self.sessions.on_change(lambda *args:calls.append(args))
        self.assertEqual(self.stage(now=999999.5),first)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(calls,[])
        self.sessions=SessionStore(str(self.sessions._path))
        new_boot=uuid.uuid4().hex
        resumed=self.stage(boot_id=new_boot)
        pending=deepcopy(resumed['pending_replacement'])
        self.assertEqual(pending['recovery_boot_id'],new_boot)
        for key in ('new_attempt_id','new_brief_id','new_dispatch_id','context_key','target_provenance',
                    'approved_prior_results','approved_continuation_context','requested_at'):
            self.assertEqual(pending[key],first['pending_replacement'][key])
        self.sessions.stop_run(self.run['id'],'Stop pending replacement')
        stopped=self.sessions.get(self.run['id'])
        disk=self.sessions._path.read_bytes()
        replay=self.stage(boot_id=uuid.uuid4().hex)
        self.assertEqual(replay,stopped)
        self.assertEqual(self.sessions._path.read_bytes(),disk)

    def test_strict_ids_profile_fingerprint_reason_and_actor_refuse_atomically(self):
        for key in ('checkpoint_id','attempt_id','request_id','boot_id'):
            for value in (True,None,'bad','A'*32,'a'*31):
                with self.subTest(key=key,value=value):self.refused(lambda:self.stage(**{key:value}))
        for changes in ({'reason':'x'*257},{'reason':'bad\0text'},{'reason':'\ud800'},{'reason':None},
                        {'submitted_by':''},{'submitted_by':' '},{'submitted_by':'x'*81},
                        {'submitted_by':'actor\0name'},{'submitted_by':None}):
            with self.subTest(changes=repr(changes)):self.refused(lambda:self.stage(**changes))
        for key,value in (('fingerprint','a'*64),('identity_id',True),('launch_attempt','bad')):
            profile=deepcopy(self.provenance)
            profile[key]=value
            with self.subTest(profile=key):self.refused(lambda:self.stage(target_provenance=profile))
        for session_id in (0,True,'1',1.0,-1,999999):
            with self.subTest(session_id=session_id):
                self.refused(lambda:self.sessions.replace_participant(session_id,**self.intent))
        accepted=self.stage(reason='é'*256,submitted_by='S'*80)
        self.assertEqual(accepted['pending_replacement']['target_provenance'],self.provenance)

    def test_current_checkpoint_stop_pending_and_consumed_fences_refuse_before_effects(self):
        baseline=deepcopy(self.run)
        for changes in ({'stop_id':uuid.uuid4().hex},{'replaced_by_run_id':uuid.uuid4().hex},
                        {'pending_retry':{'request_id':uuid.uuid4().hex}},
                        {'pending_replacement':{'request_id':uuid.uuid4().hex}},
                        {'active_invocation':dict(baseline['active_invocation'],consumed=True)},
                        {'active_invocation':dict(baseline['active_invocation'],human=True)},
                        {'state':'awaiting_input'},{'state':'paused'}, {'turn_recovery':None}):
            self.restore(baseline,**changes)
            with self.subTest(changes=list(changes)):self.refused(self.stage)
        self.restore(baseline)
        self.refused(lambda:self.stage(checkpoint_id=uuid.uuid4().hex))
        self.refused(lambda:self.stage(attempt_id=uuid.uuid4().hex))

    def test_bind_requires_exact_context_boot_identity_and_frozen_profile(self):
        staged=self.stage()
        context,provenance=self.clone(staged['pending_replacement'])
        for changes in ({'state':'starting'},{'clean_context':False},{'verified_boot_id':uuid.uuid4().hex},
                        {'key':'wrong/context'},{'identity_id':self.source['identity_id']},
                        {'identity_id':self.old['identity_id']},{'launch_attempt':uuid.uuid4().hex}):
            with self.subTest(context=changes):self.refused(lambda:self.bind(dict(context,**changes),provenance))
        self.refused(lambda:self.bind(context,provenance,boot_id=uuid.uuid4().hex))
        for field,value in (('identity_id',self.source['identity_id']),('launch_attempt',uuid.uuid4().hex),
                            ('fingerprint','0'*64)):
            forged=dict(provenance,**{field:value})
            with self.subTest(provenance=field):self.refused(lambda:self.bind(context,forged))
        changed=deepcopy(provenance)
        changed['effective']['seat']['model']='OTHER_MODEL'
        self.refused(lambda:self.bind(context,changed))

    def test_atomic_stage_replace_failure_rolls_back_fence_pending_ids_and_all_external_state(self):
        memory,disk=self.sessions.list_all(),self.sessions._path.read_bytes()
        external={path:path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file() and path!=self.sessions._path}
        replace=Path.replace
        def fail(path,target):
            if Path(target)==self.sessions._path:raise OSError('Injected replacement stage failure')
            return replace(path,target)
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.stage()
        self.assertEqual(self.sessions.list_all(),memory)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        for path,data in external.items():self.assertEqual(path.read_bytes(),data)
        self.assertNotIn('pending_replacement',self.sessions.get(self.run['id']))

    def test_atomic_bind_replace_failure_preserves_staged_intent_and_no_queued_brief(self):
        staged=self.stage()
        context,provenance=self.clone(staged['pending_replacement'])
        memory,disk=self.sessions.list_all(),self.sessions._path.read_bytes()
        queue=self.trigger.queue.status()
        messages=self.messages._path.read_bytes()
        replace=Path.replace
        def fail(path,target):
            if Path(target)==self.sessions._path:raise OSError('Injected replacement bind failure')
            return replace(path,target)
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.bind(context,provenance)
        self.assertEqual(self.sessions.list_all(),memory)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(self.trigger.queue.status(),queue)
        self.assertEqual(self.messages._path.read_bytes(),messages)
        self.assertEqual(self.bind(context,provenance)['pending_replacement']['status'],'dispatching')

    def test_thread_idempotency_reserves_one_fence_and_one_set_of_generation_ids(self):
        barrier=threading.Barrier(4)
        def stage_once(_):
            barrier.wait(timeout=5)
            return self.stage()
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(stage_once,range(4)))
        self.assertTrue(all(result==results[0] for result in results))
        self.assertEqual(len(results[0]['superseded_attempts']),1)
        pending=results[0]['pending_replacement']
        self.assertEqual(len({pending[key] for key in ('new_attempt_id','new_brief_id','new_dispatch_id')}),3)
        self.assertEqual(pending['affected_positions'],[{'phase':1,'turn':0},{'phase':2,'turn':0}])
        context,provenance=self.clone(pending)
        first=self.bind(context,provenance)
        disk=self.sessions._path.read_bytes()
        self.assertEqual(self.bind(context,provenance),first)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        audit=first['participant_changes'][-1]
        self.assertEqual(audit['affected_positions'],[{'phase':1,'turn':0},{'phase':2,'turn':0}])
        serialized=json.dumps(audit)
        self.assertNotIn('credential-value-test-only',serialized)
        self.assertNotIn(self.source['token'],serialized)

    def test_normal_final_and_replacement_stage_have_one_durable_winner(self):
        invocation=self.run['active_invocation']
        brief=self.sessions.briefs.get(invocation['brief_id'],self.old)
        event={key:brief[key] for key in ('brief_id','run_id','turn_id','attempt_id','input_revision')}
        event.update(event_id=uuid.uuid4().hex,kind='final',content='Actual original contribution')
        barrier=threading.Barrier(2)
        def race(replace):
            barrier.wait(timeout=5)
            try:
                if replace:self.stage()
                else:self.sessions.admit_event(self.run['id'],event,self.old)
                return 'accepted'
            except EventConflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(race,(True,False)))
        self.assertCountEqual(outcomes,['accepted','conflict'])
        saved=self.sessions.get(self.run['id'])
        self.assertEqual(len(saved['admitted_events'])+int(bool(saved.get('pending_replacement'))),2)

    def test_changed_intent_conflicts_and_bound_replay_after_stop_cannot_resume(self):
        staged=self.stage()
        for changes in ({'reason':'Different reason'},{'submitted_by':'Other operator'},
                        {'request_id':uuid.uuid4().hex},{'checkpoint_id':uuid.uuid4().hex}):
            with self.subTest(changes=changes):self.refused(lambda:self.stage(**changes))
        context,provenance=self.clone(staged['pending_replacement'])
        bound=self.bind(context,provenance)
        self.sessions.stop_run(self.run['id'],'Stop after bound replacement')
        stopped=self.sessions.get(self.run['id'])
        disk=self.sessions._path.read_bytes()
        self.assertEqual(self.bind(context,provenance),stopped)
        self.assertEqual(self.stage(),stopped)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(stopped['cast_snapshot'],self.run['cast_snapshot'])
        self.assertEqual(bound['participant_bindings']['reader'],self.run['participant_bindings']['reader'])
