"""Explicit missing-contribution store transactions; process doubles, no native proof."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

from session_store import SessionStore
from turn_events import EventConflict, EventValidationError
from tests import test_result_owner_wiring as fixture


class ParticipantSkipStorageTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.owner, _ = self.fixture.ready('cli')
        self.run = fixture.ResultOwnerWiringTests.start(self, self.owner['name'])
        record = self.trigger.queue.owned(self.owner, self.run['active_invocation']['dispatch_id'])
        self.engine.monitor_turns(now=record['events'][0]['at'] + self.run['recovery_policy']['ack_timeout'] + .1)
        self.run = self.sessions.get(self.run['id'])
        self.assertEqual(self.run['state'], 'stalled')
        self.intent = {'checkpoint_id':self.run['turn_recovery']['checkpoint_id'],
            'attempt_id':self.run['active_invocation']['attempt_id'], 'request_id':uuid.uuid4().hex,
            'reason':'Missing reviewer contribution, operator chose to proceed.', 'confirm_skip':True}

    def skip(self, **changes):
        return self.sessions.skip_participant(self.run['id'], **dict(self.intent, **changes))

    def stalled(self, run):
        invocation=run['active_invocation']
        record=self.trigger.queue.owned(self.owner,invocation['dispatch_id'])
        self.engine.monitor_turns(now=record['events'][0]['at']+run['recovery_policy']['ack_timeout']+.1)
        self.run=self.sessions.get(run['id'])
        self.assertEqual(self.run['state'],'stalled')
        self.intent.update(checkpoint_id=self.run['turn_recovery']['checkpoint_id'],
                           attempt_id=invocation['attempt_id'],request_id=uuid.uuid4().hex)

    def design(self, phases, roles):
        tid='skip-'+uuid.uuid4().hex
        self.sessions.save_custom_template({'id':tid,'name':'Skip transaction design','roles':roles,'phases':phases})
        return self.engine.start_session(tid,tid[:18],{role:self.owner['name'] for role in roles},'operator',
                                         goal='Preserve prior work.',input_text='Exact café\r\nsource')

    def replace_run(self, baseline, **changes):
        def replace(value):
            value.clear()
            value.update(deepcopy(dict(baseline,**changes)))
        self.sessions._event_update(self.run['id'],replace)

    def refused(self, callback):
        disk,memory=self.sessions._path.read_bytes(),self.sessions.list_all()
        with self.assertRaises((EventConflict,EventValidationError)):
            callback()
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(self.sessions.list_all(),memory)

    def test_final_output_skip_is_explicit_missing_work_and_not_an_admitted_answer(self):
        updated = self.skip()
        self.assertEqual(updated['state'], 'complete')
        self.assertIs(updated['missing_output'], True)
        self.assertIsNone(updated['active_invocation'])
        self.assertEqual(updated['admitted_events'], [])
        self.assertEqual(len(updated['skipped_turns']), 1)
        skipped = updated['skipped_turns'][0]
        self.assertEqual(skipped['request_id'], self.intent['request_id'])
        self.assertEqual(skipped['reason'], self.intent['reason'])
        fence = next(value for value in updated['superseded_attempts']
                     if value['attempt_id']==self.intent['attempt_id'])
        self.assertEqual(fence['reason'], 'participant_skipped')
        self.assertEqual(fence['old_transport']['dispatch_id'], self.run['active_invocation']['dispatch_id'])
        self.assertIs(fence['old_transport']['resolved'], False)

    def test_exact_skip_replay_has_identical_bytes_time_and_no_callback_churn(self):
        first = self.skip(now=123456.5)
        disk = self.sessions._path.read_bytes()
        callbacks=[]
        self.sessions.on_change(lambda *args:callbacks.append(args))
        replay=self.skip(now=999999.5)
        self.assertEqual(replay,first)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(callbacks,[])

    def test_skip_preserves_prior_accepted_work_and_all_frozen_future_assignments(self):
        run=self.design([
            {'name':'Evidence','participants':['reader'],'prompt':'Read source.'},
            {'name':'Critique','participants':['critic'],'prompt':'Critique evidence.'},
            {'name':'Synthesis','participants':['reader'],'prompt':'Synthesize.','is_output':True}],['reader','critic'])
        self.engine.admit_event(run['active_invocation']['brief_id'],'final','Genuine prior accepted evidence',self.owner)
        self.stalled(self.sessions.get(run['id']))
        before=deepcopy(self.run)
        messages=self.messages._path.read_bytes()
        queue=self.trigger.queue.status()
        spawns=self.fixture.spawn.call_count
        registry=self.fixture.registry.get_all()
        updated=self.skip()
        self.assertEqual((updated['current_phase'],updated['current_turn']),(2,0))
        self.assertEqual(updated['admitted_events'],before['admitted_events'])
        for key in ('design_snapshot','input_snapshot','rules_snapshot','cast','cast_snapshot',
                    'participant_bindings','goal','run_id','input_revision','capacity_policy','result_message_ids'):
            self.assertEqual(updated[key],before[key],key)
        self.assertEqual(self.messages._path.read_bytes(),messages)
        self.assertEqual(self.trigger.queue.status(),queue)
        self.assertEqual(self.fixture.spawn.call_count,spawns)
        self.assertEqual(self.fixture.registry.get_all(),registry)
        audit=updated['skipped_turns'][0]
        self.assertEqual(audit['role'],'critic')
        self.assertEqual(audit['run_id'],before['run_id'])
        self.assertEqual(audit['input_revision'],before['input_revision'])
        self.assertEqual(audit['attempt_id'],before['active_invocation']['attempt_id'])
        self.assertEqual(audit['submitted_by'],'operator')
        self.assertEqual(len(audit['projection_id']),32)
        self.assertEqual(uuid.UUID(hex=audit['projection_id']).hex,audit['projection_id'])
        self.assertIsNone(audit['projected_message_id'])
        transport=updated['superseded_attempts'][-1]['old_transport']
        self.assertEqual(transport['launch_provenance'],before['participant_bindings']['critic']['launch_provenance'])
        transport['launch_provenance']['effective']['seat']['model']='MUTATED_COPY'
        self.assertNotEqual(self.sessions.get(updated['id'])['superseded_attempts'][-1]['old_transport'],transport)

    def test_skip_advances_only_one_participant_and_does_not_remove_later_role_occurrence(self):
        run=self.design([
            {'name':'Discussion','participants':['reader','critic'],'prompt':'Discuss evidence.'},
            {'name':'Final','participants':['reader'],'prompt':'Final synthesis.','is_output':True}],['reader','critic'])
        self.stalled(run)
        updated=self.skip()
        self.assertEqual((updated['current_phase'],updated['current_turn']),(0,1))
        self.assertEqual(updated['state'],'active')
        self.assertIsNone(updated['active_invocation'])
        self.assertEqual(updated['design_snapshot']['phases'][1]['participants'],['reader'])
        self.assertEqual(updated['cast'],run['cast'])
        self.assertEqual(len(updated['skipped_turns']),1)
        self.assertFalse(updated.get('missing_output',False))

    def test_earlier_output_phase_skip_does_not_mark_later_real_synthesis_missing(self):
        run=self.design([{'name':'Joint output','participants':['reader','critic'],
            'prompt':'Contribute synthesis.','is_output':True}],['reader','critic'])
        self.stalled(run)
        updated=self.skip()
        self.assertEqual((updated['current_phase'],updated['current_turn']),(0,1))
        self.assertFalse(updated.get('missing_output',False))
        self.assertEqual(updated['admitted_events'],[])
        # Explicitly invoke the EXISTING engine dispatch path to bind the next
        # genuine contribution; skip_participant itself must not do this work.
        self.engine._trigger_current(updated)
        next_run=self.sessions.get(updated['id'])
        self.engine.admit_event(next_run['active_invocation']['brief_id'],'final','Genuine later synthesis',self.owner)
        completed=self.sessions.get(updated['id'])
        self.assertEqual(completed['state'],'complete')
        self.assertFalse(completed.get('missing_output',False))
        self.assertEqual(len(completed['admitted_events']),1)
        self.assertEqual(completed['admitted_events'][0]['content'],'Genuine later synthesis')
        self.assertEqual(len(completed['skipped_turns']),1)

    def test_strict_ids_consent_reason_and_actor_reject_without_any_mutation(self):
        for field in ('checkpoint_id','attempt_id','request_id'):
            for value in (None,True,12,'bad','A'*32,'a'*31):
                with self.subTest(field=field,value=value):
                    self.refused(lambda:self.skip(**{field:value}))
        for changes in ({'confirm_skip':False},{'confirm_skip':1},{'confirm_skip':'true'},{'confirm_skip':None},
                        {'reason':''},{'reason':' \r\n'},{'reason':'x'*257},{'reason':'bad\0text'},
                        {'reason':'\ud800'},{'reason':None},{'submitted_by':''},{'submitted_by':' '},
                        {'submitted_by':'x'*81},{'submitted_by':None}):
            with self.subTest(changes=repr(changes)):
                self.refused(lambda:self.skip(**changes))
        for session_id in (0,-1,True,'1',1.0,None,999999):
            with self.subTest(session_id=session_id):
                self.refused(lambda:self.sessions.skip_participant(session_id,**self.intent))
        updated=self.skip(reason='é'*256,submitted_by='S'*80)
        self.assertEqual(updated['skipped_turns'][0]['reason'],'é'*256)

    def test_stale_current_and_permanent_or_pending_fences_deny(self):
        baseline=deepcopy(self.run)
        invocation=baseline['active_invocation']
        for changes in ({'stop_id':uuid.uuid4().hex},{'replaced_by_run_id':uuid.uuid4().hex},
                        {'pending_retry':{'request_id':uuid.uuid4().hex}},
                        {'pending_replacement':{'request_id':uuid.uuid4().hex}},
                        {'active_invocation':dict(invocation,consumed=True)},
                        {'active_invocation':dict(invocation,human=True)}, {'active_invocation':None},
                        {'state':'active'},{'state':'paused'},{'state':'awaiting_input'},{'state':'complete'},
                        {'turn_recovery':None}, {'completion_protocol':0}):
            self.replace_run(baseline,**changes)
            with self.subTest(changes=list(changes)):
                self.refused(lambda:self.skip())
        # Protocol0 is intentionally last: legacy stores prohibit later mutation.

    def test_replay_survives_reload_and_stop_while_changed_intent_and_new_request_conflict(self):
        first=self.skip()
        self.sessions.stop_run(self.run['id'],'Stopped after explicit skip')
        self.sessions=SessionStore(str(self.sessions._path))
        disk=self.sessions._path.read_bytes()
        callbacks=[]
        self.sessions.on_change(lambda *args:callbacks.append(args))
        replay=self.skip()
        self.assertEqual(replay['skipped_turns'],first['skipped_turns'])
        self.assertTrue(replay['stop_id'])
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(callbacks,[])
        for changes in ({'reason':'Different decision'},{'submitted_by':'other'},
                        {'attempt_id':uuid.uuid4().hex},{'checkpoint_id':uuid.uuid4().hex},
                        {'request_id':uuid.uuid4().hex}):
            with self.subTest(changes=changes):self.refused(lambda:self.skip(**changes))

    def test_waiting_and_interrupted_current_checkpoints_allow_explicit_skip(self):
        baseline=deepcopy(self.run)
        for state in ('waiting','interrupted'):
            self.replace_run(baseline,state=state,dispatch_eligible=False)
            result=self.skip(request_id=uuid.uuid4().hex)
            self.assertEqual(len(result['skipped_turns']),1)
            self.assertEqual(result['state'],'complete')
            self.assertEqual(result['skipped_turns'][0]['reason'],self.intent['reason'])

    def test_real_atomic_replace_failure_preserves_memory_disk_and_external_files(self):
        memory,disk=self.sessions.list_all(),self.sessions._path.read_bytes()
        external={path:path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()}
        original=Path.replace
        def fail(path,target):
            if Path(target)==self.sessions._path:raise OSError('Injected atomic skip failure')
            return original(path,target)
        with patch.object(Path,'replace',fail),self.assertRaises(OSError):self.skip()
        self.assertEqual(self.sessions.list_all(),memory)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(SessionStore(str(self.sessions._path)).list_all(),memory)
        for path,data in external.items():self.assertEqual(path.read_bytes(),data)
        self.assertEqual(len(self.skip()['skipped_turns']),1)

    def test_four_thread_same_request_has_one_fence_skip_and_stable_projection_identity(self):
        barrier=threading.Barrier(4)
        def skip_once(_):
            barrier.wait(timeout=5)
            return self.skip()
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(skip_once,range(4)))
        self.assertTrue(all(result==results[0] for result in results))
        saved=self.sessions.get(self.run['id'])
        self.assertEqual(len(saved['skipped_turns']),1)
        self.assertEqual(len(saved['superseded_attempts']),1)
        self.assertEqual(saved['admitted_events'],[])
        disk=self.sessions._path.read_bytes()
        self.assertEqual(self.skip(),saved)
        self.assertEqual(self.sessions._path.read_bytes(),disk)

    def test_normal_final_and_skip_race_admits_exactly_one_kind_of_contribution(self):
        invocation=self.run['active_invocation']
        brief=self.sessions.briefs.get(invocation['brief_id'],self.owner)
        event={key:brief[key] for key in ('brief_id','run_id','turn_id','attempt_id','input_revision')}
        event.update(event_id=uuid.uuid4().hex,kind='final',content='Actual authenticated contribution')
        gate=threading.Barrier(2)
        def race(selected):
            gate.wait(timeout=5)
            try:
                if selected:self.skip()
                else:self.sessions.admit_event(self.run['id'],event,self.owner)
                return 'accepted'
            except EventConflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(race,(True,False)))
        self.assertCountEqual(outcomes,['accepted','conflict'])
        current=self.sessions.get(self.run['id'])
        self.assertEqual(len(current.get('skipped_turns',[]))+len(current['admitted_events']),1)
        self.assertEqual(current['state'],'complete')
