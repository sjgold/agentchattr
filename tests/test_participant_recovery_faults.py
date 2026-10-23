"""Participant controller fault boundaries; real stores, nonnative manager readiness/process doubles."""
from copy import deepcopy
import json
import time
import unittest
from unittest.mock import patch
import uuid

from agents import AgentTrigger
from api_seats import atomic_json
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict, EventValidationError
from tests import test_participant_recovery_engine as fixture


class ParticipantRecoveryFaultTests(unittest.TestCase):
    def setUp(self):
        fixture.ParticipantRecoveryEngineTests.setUp(self)

    def current(self):
        return self.sessions.get(self.f.run['id'])

    def replace(self,decision=None):
        return self.engine.replace_participant(self.f.run['id'],self.decision if decision is None else decision)

    def prepare_ready(self):
        self.replace()
        pending=deepcopy(self.current()['pending_replacement'])
        context,provenance=self.f.clone(pending)
        return pending,context,provenance

    def mark_ready(self,pending):
        manager=self.f.fixture.manager
        source=pending['target_provenance']
        binding={'child_run_id':self.f.run['run_id'],'role':pending['role']}
        view=manager.prepare_replacement_context(source,pending['context_key'],binding=binding)
        attempt=next(value for value in manager.attempts.values() if value['id']==view['launch_attempt'])
        owner=self.f.fixture.registry.register(attempt['base'])
        atomic_json(attempt['receipt'],{'attempt':attempt['id'],'name':owner['name'],'identity_id':owner['identity_id'],
            'state':'ready','adapter_connected':True,'authentication':'unknown','confirmed_model':None,'updated_at':time.time()})
        context=manager.prepare_replacement_context(source,pending['context_key'],binding=binding)
        return context,manager.launch_provenance(owner)

    def repair_decision(self,pending,context):
        return {'request_id':pending['request_id'],'preparation_attempt':context['launch_attempt']}

    def tolerate_io(self,callback):
        try:return callback()
        except OSError:return None

    def test_bind_io_gap_preserves_reserved_intent_without_queue_and_replay_uses_same_clone(self):
        pending,context,_=self.prepare_ready()
        before=self.f.fixture.spawn.call_count
        with patch.object(self.sessions,'bind_replacement',side_effect=OSError('Injected bind gap')):
            self.tolerate_io(self.replace)
        current=self.current()
        for key in ('request_id','new_attempt_id','new_brief_id','new_dispatch_id','context_key'):
            self.assertEqual(current['pending_replacement'][key],pending[key])
        records=self.f.trigger.queue.for_identity({'name':context['name'],'identity_id':context['identity_id']})
        self.assertFalse(any(value['envelope']['dispatch_id']==pending['new_dispatch_id'] for value in records))
        self.replace()
        self.assertEqual(self.current()['active_invocation']['attempt_id'],pending['new_attempt_id'])
        self.assertEqual(self.f.fixture.spawn.call_count,before)

    def test_committed_enqueue_lost_reply_replay_does_not_prepare_or_dispatch_again(self):
        pending,context,_=self.prepare_ready()
        queue=self.f.trigger.queue
        enqueue=queue.enqueue
        def committed_then_lost(instance,envelope):
            result=enqueue(instance,envelope)
            if envelope['dispatch_id']==pending['new_dispatch_id']:
                raise OSError('Injected lost enqueue reply after durable commit')
            return result
        with patch.object(queue,'enqueue',side_effect=committed_then_lost):
            self.tolerate_io(self.replace)
        records=queue.for_identity({'name':context['name'],'identity_id':context['identity_id']})
        self.assertEqual(sum(value['envelope']['dispatch_id']==pending['new_dispatch_id'] for value in records),1)
        with patch.object(self.f.fixture.manager,'prepare_replacement_context',side_effect=AssertionError('committed context prepared again')), \
             patch.object(self.f.trigger,'trigger_sync',side_effect=AssertionError('committed envelope dispatched again')):
            self.replace()
        self.assertEqual(self.current()['active_invocation']['dispatch_id'],pending['new_dispatch_id'])

    def test_brief_put_gap_retries_same_reserved_owner_and_keeps_immutable_prior_text(self):
        pending,context,_=self.prepare_ready()
        prior=deepcopy(self.current()['admitted_events'][0])
        self.f.messages.get_by_id(prior['projected_message_id'])['text']='WRONG_LIVE_PROJECTION'
        self.f.messages.delete([prior['projected_message_id']])
        with patch.object(self.sessions.briefs,'put',side_effect=OSError('Injected immutable brief write gap')):
            self.tolerate_io(self.replace)
        self.replace()
        invocation=self.current()['active_invocation']
        self.assertEqual(invocation['brief_id'],pending['new_brief_id'])
        self.assertEqual(invocation['attempt_id'],pending['new_attempt_id'])
        self.assertEqual(invocation['dispatch_id'],pending['new_dispatch_id'])
        self.assertEqual(invocation['expected_identity_id'],context['identity_id'])
        brief=self.sessions.briefs.get(invocation['brief_id'],operator=True)
        self.assertEqual(brief['prior_results'],pending['approved_prior_results'])
        self.assertIn('IMMUTABLE_PRIOR café',json.dumps(brief['prior_results'],ensure_ascii=False))
        self.assertNotIn('WRONG_LIVE_PROJECTION',json.dumps(brief))

    def test_api_brief_enqueue_failure_blocks_repair_control_and_fresh_request_reserves_new_generation(self):
        pending,context,_=self.prepare_ready()
        with patch.object(self.f.trigger.queue,'enqueue',side_effect=OSError('Injected unpublished API dispatch')):
            self.tolerate_io(self.replace)
        current=self.current()
        brief=self.sessions.briefs.get(pending['new_brief_id'],operator=True)
        self.assertEqual(brief['expected_identity_id'],context['identity_id'])
        before=deepcopy(brief)
        with patch.object(self.f.fixture.manager,'repair_replacement_context',side_effect=AssertionError('immutable owner repaired')):
            with self.assertRaises(EventConflict):
                self.engine.repair_replacement(self.f.run['id'],self.repair_decision(pending,context))
        current=self.current()
        decision=dict(self.decision,request_id=uuid.uuid4().hex,
            checkpoint_id=current['turn_recovery']['checkpoint_id'],attempt_id=current['active_invocation']['attempt_id'])
        self.replace(decision)
        fresh=self.current()['pending_replacement']
        for field in ('new_attempt_id','new_brief_id','new_dispatch_id'):
            self.assertNotEqual(fresh[field],pending[field])
        self.assertEqual(self.sessions.briefs.get(pending['new_brief_id'],operator=True),before)
        self.assertEqual(self.current()['input_snapshot'],self.f.run['input_snapshot'])

    def test_unsealed_cli_brief_is_also_immutable_before_any_manager_repair_control(self):
        manager=self.f.fixture.manager
        self.f.fixture.store.providers['fake-cli'].update(cli_fresh_context_args=['--context-id','{context_id}'],
                                                          cli_fresh_context_verified=True)
        package=self.f.fixture.store.package('team')
        new_seat=deepcopy(next(value for value in package['seats'] if value['id']=='cli'))
        new_seat.update(id='fresh-cli',name='Fresh profile source')
        package['seats'].append(new_seat)
        self.f.fixture.store.save(package)
        source,_=self.f.fixture.ready('fresh-cli')
        provenance=manager.launch_provenance(source)
        self.decision.update(target_identity_id=source['identity_id'],target_fingerprint=provenance['fingerprint'])
        self.replace()
        pending=deepcopy(self.current()['pending_replacement'])
        context,_=self.mark_ready(pending)
        with patch.object(self.f.trigger.queue,'enqueue',side_effect=OSError('Injected unpublished CLI dispatch')):
            self.tolerate_io(self.replace)
        brief=self.sessions.briefs.get(pending['new_brief_id'],operator=True)
        self.assertEqual(brief['expected_identity_id'],context['identity_id'])
        self.assertNotIn('seal_secret',brief)
        with patch.object(manager,'repair_replacement_context',side_effect=AssertionError('unsealed brief owner repaired')):
            with self.assertRaises(EventConflict):
                self.engine.repair_replacement(self.f.run['id'],self.repair_decision(pending,context))

    def test_explicit_sync_failed_preparation_repair_keeps_reserved_turn_ids_and_source(self):
        manager=self.f.fixture.manager
        spawn=self.f.fixture.spawn.side_effect
        self.f.fixture.spawn.side_effect=OSError('Injected synchronous clone launch failure')
        self.replace()
        self.f.fixture.spawn.side_effect=spawn
        pending=deepcopy(self.current()['pending_replacement'])
        context=pending['context']
        calls=self.f.fixture.spawn.call_count
        self.replace()
        self.assertEqual(self.f.fixture.spawn.call_count,calls)
        self.engine.repair_replacement(self.f.run['id'],self.repair_decision(pending,context))
        repaired=self.current()['pending_replacement']
        for key in ('request_id','new_attempt_id','new_brief_id','new_dispatch_id','context_key','approved_prior_results'):
            self.assertEqual(repaired[key],pending[key])
        self.assertNotEqual(repaired['context']['launch_attempt'],context['launch_attempt'])
        self.assertEqual(self.f.fixture.spawn.call_count,calls+1)
        self.assertEqual(self.current()['admitted_events'],self.f.run['admitted_events'])

    def test_new_boot_pending_intent_never_prepares_until_explicit_same_request_repeat(self):
        self.replace()
        pending=deepcopy(self.current()['pending_replacement'])
        manager=self.f.fixture.manager
        manager.boot_id=uuid.uuid4().hex
        sessions=SessionStore(str(self.sessions._path))
        messages=MessageStore(str(self.f.messages._path))
        trigger=AgentTrigger(self.f.fixture.registry,str(self.f.fixture.root))
        engine=SessionEngine(sessions,messages,trigger,self.f.fixture.registry,seat_manager=manager)
        with patch.object(manager,'prepare_replacement_context',side_effect=AssertionError('cold automatic prepare')):
            engine.reconcile_restart(boot_id=manager.boot_id)
            engine.monitor_turns()
        cold=sessions.get(self.f.run['id'])
        self.assertEqual(cold['state'],'interrupted')
        for key in ('new_attempt_id','new_brief_id','new_dispatch_id','context_key'):
            self.assertEqual(cold['pending_replacement'][key],pending[key])
        engine.replace_participant(self.f.run['id'],self.decision)
        resumed=sessions.get(self.f.run['id'])
        self.assertEqual(resumed['pending_replacement']['recovery_boot_id'],manager.boot_id)
        self.assertEqual(resumed['pending_replacement']['new_attempt_id'],pending['new_attempt_id'])

    def test_options_and_strict_target_decisions_do_not_change_ownership_or_storage(self):
        manager=self.f.fixture.manager
        files={path:path.read_bytes() for path in self.f.fixture.root.rglob('*') if path.is_file()}
        calls=self.f.fixture.spawn.call_count
        with patch.object(manager,'prepare_replacement_context',side_effect=AssertionError('options prepared')), \
             patch.object(manager,'terminate_owned',side_effect=AssertionError('options controlled')):
            options=self.engine.participant_recovery_options(self.f.run['id'])
        text=json.dumps(options)
        self.assertNotIn('credential-value-test-only',text)
        self.assertNotIn(self.f.source['token'],text)
        self.assertEqual(files,{path:path.read_bytes() for path in self.f.fixture.root.rglob('*') if path.is_file()})
        for changes in ({'source_text':'override'},{'request_id':True},{'target_fingerprint':'0'*64},
                        {'target_identity_id':uuid.uuid4().hex},{'attempt_id':uuid.uuid4().hex}):
            with self.subTest(changes=changes),self.assertRaises((EventConflict,EventValidationError)):
                self.replace(dict(self.decision,**changes))
        self.f.fixture.registry.deregister(self.f.source['name'])
        with self.assertRaises(EventConflict):self.replace()
        self.assertNotIn('pending_replacement',self.current())
        self.assertEqual(self.f.fixture.spawn.call_count,calls)

    def test_stop_or_corrected_fence_during_preparation_prevents_binding_or_new_dispatch(self):
        pending,context,_=self.prepare_ready()
        baseline=deepcopy(self.current())
        for changes in ({'stop_id':uuid.uuid4().hex,'state':'stopping','dispatch_eligible':False},
                        {'replaced_by_run_id':uuid.uuid4().hex}):
            def update(value):
                value.clear()
                value.update(deepcopy(dict(baseline,**changes)))
            self.sessions._event_update(self.f.run['id'],update)
            try:self.replace()
            except EventConflict:pass
            current=self.current()
            self.assertEqual(current['cast'],self.f.run['cast'])
            records=self.f.trigger.queue.for_identity({'name':context['name'],'identity_id':context['identity_id']})
            self.assertFalse(any(record['envelope']['dispatch_id']==pending['new_dispatch_id'] for record in records))

    def test_replacement_completion_schedules_one_unaffected_successor_and_old_output_quarantines(self):
        pending,context,_=self.prepare_ready()
        self.replace()
        invocation=deepcopy(self.current()['active_invocation'])
        owner=self.f.fixture.registry.get_instance(context['name'])
        source_records=len(self.f.trigger.queue.for_identity(self.f.source))
        self.engine.admit_event(invocation['brief_id'],'final','Accepted replacement review',owner)
        advanced=self.current()
        self.assertEqual(advanced['active_invocation']['role'],'reader')
        self.assertEqual(advanced['active_invocation']['expected_identity_id'],self.f.source['identity_id'])
        self.assertEqual(len(self.f.trigger.queue.for_identity(self.f.source)),source_records+1)
        self.replace()
        self.assertEqual(len(self.f.trigger.queue.for_identity(self.f.source)),source_records+1)
        with self.assertRaises(EventConflict):
            self.engine.admit_event(self.f.run['active_invocation']['brief_id'],'final','LATE_RETIRED_EDITOR',self.f.old)
        self.assertTrue(any(event['content']=='LATE_RETIRED_EDITOR' for event in self.current()['quarantined_events']))
        self.assertEqual(len(self.current()['admitted_events']),2)
