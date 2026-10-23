"""Explicit replacement-preparation repair; process/readiness/end-proof doubles are nonnative."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import uuid

from api_seats import SeatError, atomic_json
from api_seat_runtime import SeatManager
from dispatch_queue import QueueStore
from review_brief import BriefStore, build_brief, freeze_inputs
from tests import test_prepare_replacement_context as fixture


class ReplacementPreparationRepairTests(unittest.TestCase):
    def setUp(self):
        fixture.PrepareReplacementContextTests.setUp(self)
        spawn=self.spawn.side_effect
        self.spawn.side_effect=OSError('Synchronous preparation fixture failure')
        self.failed=self.manager.prepare_replacement_context(self.provenance,self.context_key,binding=self.binding)
        self.spawn.side_effect=spawn
        self.dispatch_id=uuid.uuid4().hex  # Reserved server-dispatch boundary, no generation implied.

    def ready(self,seat_id):
        return fixture.PrepareReplacementContextTests.ready(self,seat_id)

    def repair(self,**changes):
        values={'binding':self.binding,'preparation_attempt':self.failed['launch_attempt'],'dispatch_id':self.dispatch_id}
        values.update(changes)
        return self.manager.repair_replacement_context(self.provenance,self.context_key,**values)

    def context(self,view):
        return fixture.PrepareReplacementContextTests.context(self,view)

    def register_ready(self,view):
        return fixture.PrepareReplacementContextTests.register_ready(self,view)

    def live_preparation(self,cli=False,failed=True):
        if cli:
            fixture.PrepareReplacementContextTests.cli_source(self,verified=True)
        self.context_key='live-'+uuid.uuid4().hex
        view=self.manager.prepare_replacement_context(self.provenance,self.context_key,binding=self.binding)
        self.prepared_owner=self.register_ready(view)
        self.manager.prepare_replacement_context(self.provenance,self.context_key,binding=self.binding)
        attempt=self.context(view)
        if failed:
            receipt=json.loads(attempt['receipt'].read_text('utf-8'))
            receipt.update(state='failed',adapter_connected=False,error='Fixture preparation failure')
            atomic_json(attempt['receipt'],receipt)
            attempt['state']='failed'
        self.failed=view
        return attempt

    def assert_no_spawn(self,callback):
        calls=self.spawn.call_count
        try:result=callback()
        except SeatError:result=None
        else:self.assertIn(result['state'],('failed','blocked','action_required'))
        self.assertEqual(self.spawn.call_count,calls)
        return result

    def test_exact_sync_failed_repair_creates_one_new_attempt_and_replay_reuses_it(self):
        before=self.spawn.call_count
        result=self.repair()
        self.assertEqual(result['state'],'starting')
        self.assertNotEqual(result['launch_attempt'],self.failed['launch_attempt'])
        self.assertEqual(self.spawn.call_count,before+1)
        repeated=self.repair()
        self.assertEqual(repeated['launch_attempt'],result['launch_attempt'])
        self.assertEqual(self.spawn.call_count,before+1)
        self.processes[0].wait.assert_not_called()
        self.processes[0].terminate.assert_not_called()

    def test_missing_preparation_or_stale_attempt_refuses_without_initial_launch(self):
        before=self.spawn.call_count
        with self.assertRaises(SeatError):
            self.manager.repair_replacement_context(self.provenance,'missing-'+uuid.uuid4().hex,
                binding=self.binding,preparation_attempt=self.failed['launch_attempt'],dispatch_id=self.dispatch_id)
        with self.assertRaises(SeatError):self.repair(preparation_attempt=uuid.uuid4().hex)
        for changes in ({'binding':dict(self.binding,role='other')},{'binding':dict(self.binding,child_run_id=uuid.uuid4().hex)},
                        {'dispatch_id':True},{'dispatch_id':'bad'}):
            with self.subTest(changes=changes),self.assertRaises(SeatError):self.repair(**changes)
        forged=dict(self.provenance,identity_id=uuid.uuid4().hex)
        with self.assertRaises(SeatError):
            self.manager.repair_replacement_context(forged,self.context_key,binding=self.binding,
                preparation_attempt=self.failed['launch_attempt'],dispatch_id=self.dispatch_id)
        self.assertEqual(self.spawn.call_count,before)

    def test_cold_synchronous_failed_repair_and_replay_preserve_scope_without_blind_spawn(self):
        cold=SeatManager(self.manager.root,self.manager.config,self.store,self.registry,monitor=False)
        self.addCleanup(cold.shutdown)
        before=self.spawn.call_count
        result=cold.repair_replacement_context(self.provenance,self.context_key,binding=self.binding,
            preparation_attempt=self.failed['launch_attempt'],dispatch_id=self.dispatch_id)
        self.assertNotEqual(result['launch_attempt'],self.failed['launch_attempt'])
        self.assertEqual(self.spawn.call_count,before+1)
        replay=cold.repair_replacement_context(self.provenance,self.context_key,binding=self.binding,
            preparation_attempt=self.failed['launch_attempt'],dispatch_id=self.dispatch_id)
        self.assertEqual(replay['launch_attempt'],result['launch_attempt'])
        self.assertEqual(self.spawn.call_count,before+1)
        attempt=next(value for value in cold.attempts.values() if value['id']==result['launch_attempt'])
        self.assertEqual(attempt['retried_from'],self.failed['launch_attempt'])
        self.assertEqual(attempt['context_key'],self.context_key)
        self.assertEqual(attempt['child_run_id'],self.binding['child_run_id'])

    def test_any_prepared_queue_history_immutable_brief_or_model_intent_blocks_repair(self):
        for boundary in ('queue','brief','model'):
            attempt=self.live_preparation()
            if boundary=='queue':
                QueueStore(self.root).enqueue(self.prepared_owner,{'dispatch_id':uuid.uuid4().hex,
                    'channel':'background','prompt':'Unrelated prepared-seat history'})
            elif boundary=='brief':
                design={'id':'bound','name':'Bound','roles':['reviewer'],'phases':[
                    {'name':'Review','participants':['reviewer'],'prompt':'Read source.','is_output':True}]}
                session={**freeze_inputs(design,input_text='Exact bound source'),'id':1,'channel':'review',
                         'cast':{'reviewer':self.prepared_owner['name']},'goal':''}
                envelope=build_brief(session,0,0,self.prepared_owner['name'],self.prepared_owner['identity_id'])
                BriefStore(self.root).put(envelope)
            else:
                # A persisted model intent blocks control even without a birth;
                # this is not a claim that a model child was spawned or ended.
                atomic_json(attempt['snapshot'].parent/'invocations'/self.dispatch_id/'invocation.json',
                    {'dispatch_id':self.dispatch_id,'launch_attempt':attempt['id']})
            calls=self.spawn.call_count
            confirmation={'confirm':True,'launch_attempt':attempt['id']}
            with self.subTest(boundary=boundary), \
                 patch.object(self.manager,'_end_api_preparation',side_effect=AssertionError('bound work controlled')), \
                 patch.object(self.manager,'terminate_owned',side_effect=AssertionError('bound work controlled')):
                self.assert_no_spawn(lambda:self.repair(confirmation=confirmation))
            self.assertEqual(self.spawn.call_count,calls)

    def test_live_failed_confirmation_and_unknown_end_proof_cannot_spawn_or_force(self):
        healthy=self.live_preparation(failed=False)
        with patch.object(self.manager,'_end_api_preparation',side_effect=AssertionError('healthy preparation controlled')), \
             patch.object(self.manager,'terminate_owned',side_effect=AssertionError('healthy preparation controlled')):
            self.assert_no_spawn(lambda:self.repair(confirmation={'confirm':True,'launch_attempt':healthy['id']}))
        attempt=self.live_preparation()
        process=attempt['process']
        with patch.object(self.manager,'_end_api_preparation',return_value=False) as end, \
             patch.object(self.manager,'terminate_owned',side_effect=AssertionError('API used CLI termination')):
            self.assert_no_spawn(self.repair)
            end.assert_not_called()
            for confirmation in ({'confirm':1,'launch_attempt':attempt['id']},
                                 {'confirm':True,'launch_attempt':uuid.uuid4().hex}):
                with self.subTest(confirmation=confirmation),self.assertRaises(SeatError):self.repair(confirmation=confirmation)
            end.assert_not_called()
            result=self.assert_no_spawn(lambda:self.repair(confirmation={'confirm':True,'launch_attempt':attempt['id']}))
            self.assertEqual(result['state'],'blocked')
            end.assert_called_once()
        process.terminate.assert_not_called()
        process.wait.assert_not_called()
        # Even an ended launcher double plus a bare failed receipt is unknown.
        process.poll.return_value=7
        with patch.object(self.manager,'participant_exit_proof',return_value={'local_ended':False}):
            self.assert_no_spawn(lambda:self.repair(confirmation={'confirm':True,'launch_attempt':attempt['id']}))

    def test_api_cooperative_end_witness_launches_frozen_repair_without_touching_source(self):
        attempt=self.live_preparation()
        source=self.manager.attempts['team/api']
        source_files={path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()}
        frozen=deepcopy(attempt['effective'])
        self.package['seats'][0]['model']='WRONG_SAVED_MODEL'
        self.store.save(self.package)
        self.store.providers['fake-api']['system_prompt']='WRONG_SAVED_SYSTEM'
        def ended(selected,confirmation):
            self.assertIs(selected,attempt)
            self.assertEqual(confirmation,{'confirm':True,'launch_attempt':attempt['id']})
            selected['process'].poll.return_value=7
            selected['verified_api_exit']={'local_ended':True,'launch_attempt':selected['id'],
                                           'model_status':'never_spawned','verification_basis':'protocol_one_no_invocations'}
            return True  # Explicit nonnative API end-witness seam.
        with patch.object(self.manager,'_end_api_preparation',side_effect=ended) as end, \
             patch.object(self.manager,'terminate_owned',side_effect=AssertionError('API used CLI delegate')):
            result=self.repair(confirmation={'confirm':True,'launch_attempt':attempt['id']})
        end.assert_called_once()
        self.assertNotEqual(result['launch_attempt'],attempt['id'])
        repaired=self.context(result)
        self.assertEqual(repaired['effective'],frozen)
        self.assertEqual(repaired['replacement_source'],attempt['replacement_source'])
        source['process'].terminate.assert_not_called()
        source['process'].wait.assert_not_called()
        self.assertEqual(source_files,{path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()})

    def test_cli_exact_owned_delegate_and_separate_end_proof_preserve_profile_source(self):
        attempt=self.live_preparation(cli=True)
        source=self.manager.attempts['team/cli']
        before=self.spawn.call_count
        def ended(identity,launch):
            self.assertEqual(identity,self.prepared_owner['identity_id'])
            self.assertEqual(launch,attempt['id'])
            attempt['process'].poll.return_value=0
            receipt=json.loads(attempt['receipt'].read_text('utf-8'))
            receipt.update(state='stopped',adapter_connected=False,child_exit_code=0)
            atomic_json(attempt['receipt'],receipt)
            return {'local_ended':True,'remote_compute':'unverified'}
        proof={'local_ended':True,'dispatch_id':self.dispatch_id,'seat_identity_id':self.prepared_owner['identity_id'],
               'launch_attempt':attempt['id'],'wrapper_status':'observed_exited','child_exit_code':0,
               'verification_basis':'retained_native_handle_observed_end'}
        with patch.object(self.manager,'terminate_owned',side_effect=ended) as terminate, \
             patch.object(self.manager,'participant_exit_proof',return_value=proof) as observed, \
             patch.object(self.manager,'_end_api_preparation',side_effect=AssertionError('CLI used API delegate')):
            repaired=self.repair(confirmation={'confirm':True,'launch_attempt':attempt['id']})
        terminate.assert_called_once()
        observed.assert_called_once()
        self.assertEqual(observed.call_args.args[1],self.dispatch_id)
        self.assertEqual(self.spawn.call_count,before+1)
        new=self.context(repaired)
        self.assertEqual(new['effective']['provider']['cli_args'],
                         ['fixture-original','--context-id',repaired['context_id']])
        source['process'].terminate.assert_not_called()
        source['process'].wait.assert_not_called()

    def test_fixed_settings_source_cannot_use_missing_record_repair_to_bypass_resource_guard(self):
        fixture.PrepareReplacementContextTests.cli_source(self,verified=True,fixed_settings=True)
        source=self.manager.attempts['team/cli']
        files={path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()}
        before=self.spawn.call_count
        # Initial clone correctly cannot share this resource; a repair with no
        # matching preparation must not become an alternate initial-launch path.
        self.assert_no_spawn(lambda:self.manager.prepare_replacement_context(self.provenance,
            'fixed-'+uuid.uuid4().hex,binding=self.binding))
        with self.assertRaises(SeatError):
            self.manager.repair_replacement_context(self.provenance,'fixed-'+uuid.uuid4().hex,
                binding=self.binding,preparation_attempt=uuid.uuid4().hex,dispatch_id=self.dispatch_id,
                confirmation={'confirm':True,'launch_attempt':self.source_launch['attempt']})
        self.assertEqual(self.spawn.call_count,before)
        self.assertEqual(files,{path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()})
        source['process'].terminate.assert_not_called()
        source['process'].wait.assert_not_called()
