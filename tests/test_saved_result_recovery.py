"""Operator recovery with real signed stores and explicit non-native proof seams."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import uuid

from dispatch_queue import QueueBusy
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from agents import AgentTrigger
from result_outbox import ResultOutbox
from tests import test_result_owner_wiring as fixture


class SavedResultRecoveryTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.owner, self.launch = self.fixture.ready('api')
        run = fixture.ResultOwnerWiringTests.start(self,self.owner['name'])
        self.session_id = run['id']
        self.old = deepcopy(run['active_invocation'])
        self.queue = self.trigger.queue
        self.queue.claim(self.owner,'original-consumer')
        self.queue.acknowledge(self.owner,self.old['dispatch_id'],'original-consumer')
        self.queue.release(self.owner,self.old['dispatch_id'],'original-consumer',failed=True,error='local_delivery_failure')
        self.engine.monitor_turns()
        delivery = self.sessions.briefs.get_delivery(self.old['brief_id'],self.owner)
        self.secret = delivery['seal_secret']
        self.owner_scope = delivery['result_owner']
        self.runtime = self.fixture.manager.attempts['team/api']['snapshot'].parent
        self.box = ResultOutbox(self.runtime)
        self.payload = {'version':1,'result_id':self.old['dispatch_id'],'dispatch_id':self.old['dispatch_id'],
            'event_id':self.old['dispatch_id'],**{key:delivery[key] for key in
                ('session_id','brief_id','run_id','turn_id','attempt_id','input_revision')},
            **{key:self.owner_scope[key] for key in ('seat_identity_id','launch_attempt','launch_nonce','fingerprint')},
            'kind':'final','content':'Recovered café 日本語 result\r\n@all is quoted data.','created_at':time.time()}
        self.record = self.box.save(self.payload,self.secret)
        self.proof = {'local_ended':True,'dispatch_id':self.old['dispatch_id'],'seat_identity_id':self.owner['identity_id'],
            'launch_attempt':self.launch['attempt'],'verification_basis':'all_bound_invocations_ended'}
        self.proof_patch = patch.object(self.fixture.manager,'saved_result_exit_proof',return_value={'local_ended':False})
        self.proof_query = self.proof_patch.start()
        self.addCleanup(self.proof_patch.stop)

    def current(self):
        return self.sessions.get(self.session_id)

    def deliver(self):
        return self.engine.deliver_saved_result(self.session_id,self.payload['result_id'],submitted_by='operator-fixture')

    def test_verified_preview_is_read_only_and_excludes_private_runtime_material(self):
        before = {str(path):path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()}
        values = self.engine.saved_results(self.session_id)
        self.assertEqual(len(values),1)
        preview = values[0]
        for key in ('result_id','brief_id','kind','content','created_at','seat_identity_id'):
            self.assertEqual(preview[key],self.payload[key])
        self.assertEqual(preview['state'],'saved')
        self.assertIs(preview['can_deliver'],True)
        self.assertIn('reason',preview)
        serialized = json.dumps(values)
        for private in (self.secret,self.record['seal'],self.owner_scope['launch_nonce'],self.owner_scope['fingerprint'],str(self.runtime)):
            self.assertNotIn(private,serialized)
        self.assertEqual({str(path):path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()},before)
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))

    def test_verified_pending_final_admits_once_and_settles_only_with_positive_proof(self):
        self.proof_query.return_value = self.proof
        result = self.deliver()
        self.assertEqual(result['status'],'admitted')
        self.assertEqual(result['event_id'],self.payload['result_id'])
        self.assertEqual(result['accepted_event_id'],self.payload['result_id'])
        self.assertEqual(result['session_id'],self.session_id)
        self.assertEqual(result['kind'],'final')
        self.assertIs(result['transport_settled'],True)
        event = self.current()['admitted_events'][0]
        self.assertEqual(event['content'],self.payload['content'])
        self.assertEqual(event['provenance'],'verified_saved_api_result')
        self.assertEqual(event['submitted_by'],'operator-fixture')
        self.assertEqual(self.queue.owned(self.owner,self.old['dispatch_id'])['state'],'settled_recovered')
        self.assertEqual(self.box.get_ack(self.payload['result_id'])['accepted_event_id'],self.payload['result_id'])

    def isolated(self):
        case = type(self)()
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def save_run(self,run,kind='final',created_at=None):
        invocation = run['active_invocation']
        owner = next(value for value in self.fixture.registry.get_all().values()
                     if value['identity_id']==invocation['expected_identity_id'])
        envelope = self.sessions.briefs.get_delivery(invocation['brief_id'],owner)
        scope = envelope['result_owner']
        payload = {**deepcopy(self.payload), **{key:envelope[key] for key in
            ('session_id','brief_id','run_id','turn_id','attempt_id','input_revision')},
            **{key:scope[key] for key in ('seat_identity_id','launch_attempt','launch_nonce','fingerprint')},
            'result_id':invocation['dispatch_id'],'dispatch_id':invocation['dispatch_id'],'event_id':invocation['dispatch_id'],
            'kind':kind,'created_at':time.time() if created_at is None else created_at}
        box = ResultOutbox(self.fixture.root/'api_seat_runtime'/scope['launch_attempt'])
        box.save(payload,envelope['seal_secret'])
        return payload,box

    def two_phase(self,same_seat=False):
        # This scenario owns a new run, rather than bypassing the setup run's turn.
        self.engine.stop_session(self.session_id, 'isolate successor recovery scenario')
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))
        if same_seat:
            peer = self.owner
        else:
            package = deepcopy(self.fixture.package)
            package['seats'].append({**package['seats'][0],'id':'peer','name':'Peer API'})
            self.fixture.store.save(package)
            peer,_ = self.fixture.ready('peer')
        self.sessions.save_custom_template({'id':'two-saved','name':'Recovered result then successor',
            'roles':['reader','editor'],'phases':[
                {'name':'Evidence','participants':['reader'],'prompt':'Read source.'},
                {'name':'Final','participants':['editor'],'prompt':'Use accepted evidence.','is_output':True}]})
        run = self.engine.start_session('two-saved','successor',{'reader':self.owner['name'],'editor':peer['name']},
            'operator',input_text='Frozen successor source café\r\n')
        invocation = run['active_invocation']
        claimed = self.queue.claim(self.owner,'second-run-consumer')
        self.assertEqual(claimed['envelope']['dispatch_id'],invocation['dispatch_id'])
        self.queue.acknowledge(self.owner,invocation['dispatch_id'],'second-run-consumer')
        self.queue.release(self.owner,invocation['dispatch_id'],'second-run-consumer',failed=True,error='local_delivery_failure')
        self.engine.monitor_turns()
        payload,box = self.save_run(run)
        return run,payload,box,peer

    def test_revoked_original_identity_is_not_revived_and_hold_commits_before_admission(self):
        self.fixture.registry.deregister(self.owner['name'])
        identities = deepcopy(self.fixture.registry.get_all())
        admit = self.sessions.admit_verified_saved_event
        def guarded(session_id,payload,**kwargs):
            held = self.queue.owned(self.owner,self.old['dispatch_id'])
            self.assertIs(held['recovery_hold']['cleared'],False)
            self.assertEqual(held['recovery_hold']['result_id'],self.payload['result_id'])
            return admit(session_id,payload,**kwargs)
        with patch.object(self.sessions,'admit_verified_saved_event',side_effect=guarded):
            result = self.deliver()
        self.assertIs(result['transport_settled'],False)
        self.assertEqual(self.fixture.registry.get_all(),identities)
        event = self.current()['admitted_events'][0]
        self.assertEqual(event['expected_identity_id'],self.owner['identity_id'])
        self.assertEqual(event['sender'],self.owner['name'])
        self.assertEqual(event['result_launch_attempt'],self.launch['attempt'])
        self.assertEqual(event['result_id'],self.payload['result_id'])
        self.assertEqual(self.fixture.spawn.call_count,1)
        for forbidden in ('seal_secret','launch_nonce','fingerprint'):
            self.assertNotIn(forbidden,event)

    def test_unproven_hold_blocks_only_same_seat_and_allows_verified_peer_successor(self):
        for same in (True,False):
            case = self.isolated()
            run,payload,box,peer = case.two_phase(same_seat=same)
            result = case.engine.deliver_saved_result(run['id'],payload['result_id'])
            self.assertIs(result['transport_settled'],False)
            current = case.sessions.get(run['id'])
            self.assertEqual(current['current_phase'],1)
            self.assertEqual(len(current['admitted_events']),1)
            expected = current['active_invocation']['dispatch_id']
            try:
                claimed = case.queue.claim(peer,'successor-consumer')
            except QueueBusy:
                claimed = None
            if same:
                self.assertIsNone(claimed)
            else:
                self.assertEqual(claimed['envelope']['dispatch_id'],expected)
                envelope = case.sessions.briefs.get(current['active_invocation']['brief_id'],peer)
                self.assertEqual([value['text'] for value in envelope['prior_results']],[payload['content']])
            self.assertEqual(box.get_ack(payload['result_id'])['accepted_event_id'],payload['result_id'])
            self.assertEqual(case.fixture.spawn.call_count,1 if same else 2)

    def test_verified_question_uses_original_kind_and_waits_for_operator_input(self):
        # A separate valid pending brief avoids mutating an immutable outbox.
        self.engine.stop_session(self.session_id, 'isolate question recovery scenario')
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))
        run = fixture.ResultOwnerWiringTests.start(self,self.owner['name'],'question')
        claimed = self.queue.claim(self.owner,'question-consumer')
        self.queue.release(self.owner,claimed['envelope']['dispatch_id'],'question-consumer',failed=True,error='local_delivery_failure')
        payload,box = self.save_run(run,kind='question')
        result = self.engine.deliver_saved_result(run['id'],payload['result_id'])
        current = self.sessions.get(run['id'])
        self.assertEqual(result['kind'],'question')
        self.assertEqual(current['state'],'awaiting_input')
        self.assertEqual(current['current_question']['event_id'],payload['result_id'])
        self.assertEqual(len(current['admitted_events']),1)
        self.assertEqual(box.get_ack(payload['result_id'])['accepted_event_id'],payload['result_id'])

    def test_tamper_wrong_session_or_invalid_result_never_previews_or_admits(self):
        before = deepcopy(self.current())
        queue = (self.fixture.root/'queue/ledger.json').read_bytes()
        for result_id in ('../escape',True,None,'a'*31):
            with self.subTest(result_id=result_id),self.assertRaises(ValueError):
                self.engine.deliver_saved_result(self.session_id,result_id)
        with self.assertRaises(ValueError):
            self.engine.deliver_saved_result(self.session_id+999,self.payload['result_id'])
        path = self.runtime/'outbox'/(self.payload['result_id']+'.json')
        altered = deepcopy(self.record)
        altered['payload']['content']='Tampered text must never preview'
        path.write_text(json.dumps(altered),encoding='utf-8')
        disk = path.read_bytes()
        for operation in (lambda:self.engine.saved_results(self.session_id),self.deliver):
            with self.assertRaises(ValueError):
                operation()
        self.assertEqual(path.read_bytes(),disk)
        self.assertEqual(self.current(),before)
        self.assertEqual((self.fixture.root/'queue/ledger.json').read_bytes(),queue)
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))

    def test_pending_stop_retry_or_corrected_source_blocks_old_result_without_ack(self):
        for action in ('stop','retry','corrected'):
            case = self.isolated()
            original = (case.runtime/'outbox'/(case.payload['result_id']+'.json')).read_bytes()
            current = case.current()
            if action=='retry':
                newer = case.engine.retry_turn(case.session_id,current['turn_recovery']['checkpoint_id'],
                    case.old['attempt_id'],uuid.uuid4().hex)
                case.save_run(newer,created_at=case.payload['created_at']-1)
            else:
                case.engine.stop_session(case.session_id)
                if action=='corrected':
                    case.engine.reconcile_stops()
                    self.assertEqual(case.current()['state'],'stopped')
                    child = case.engine.correct_and_restart(case.session_id,'Changed Unicode source 日本語\r\n',uuid.uuid4().hex)
                    with self.assertRaises(ValueError):
                        case.engine.deliver_saved_result(child['id'],case.payload['result_id'])
            previews = case.engine.saved_results(case.session_id)
            preview = next(value for value in previews if value['result_id']==case.payload['result_id'])
            self.assertEqual(preview['state'],'blocked')
            self.assertIs(preview['can_deliver'],False)
            self.assertTrue(preview['reason'])
            self.assertEqual(previews,sorted(previews,key=lambda value:(value['created_at'],value['result_id'])))
            with self.assertRaises(ValueError):
                case.deliver()
            self.assertEqual((case.runtime/'outbox'/(case.payload['result_id']+'.json')).read_bytes(),original)
            self.assertIsNone(case.box.get_ack(case.payload['result_id']))

    def test_exact_admitted_replay_precedes_later_stop_and_retry_fences(self):
        for action in ('stop','retry'):
            case = self.isolated()
            run,payload,box,_ = case.two_phase(same_seat=True)
            case.engine.deliver_saved_result(run['id'],payload['result_id'])
            if action=='stop':
                case.engine.stop_session(run['id'])
            else:
                case.engine.monitor_turns(now=time.time()+1000)
                current = case.sessions.get(run['id'])
                case.engine.retry_turn(run['id'],current['turn_recovery']['checkpoint_id'],
                    current['active_invocation']['attempt_id'],uuid.uuid4().hex)
            before = deepcopy(case.sessions.get(run['id']))
            ack = box.get_ack(payload['result_id'])
            with patch.object(case.sessions,'admit_verified_saved_event',side_effect=AssertionError('must not admit twice')):
                result = case.engine.deliver_saved_result(run['id'],payload['result_id'])
            self.assertEqual(result['accepted_event_id'],payload['result_id'])
            self.assertEqual(case.sessions.get(run['id'])['admitted_events'],before['admitted_events'])
            self.assertEqual(case.sessions.get(run['id'])['active_invocation'],before['active_invocation'])
            self.assertEqual(box.get_ack(payload['result_id']),ack)
            preview = next(value for value in case.engine.saved_results(run['id']) if value['result_id']==payload['result_id'])
            self.assertEqual(preview['state'],'admitted')
            self.assertIs(preview['can_deliver'],True)

    def test_ack_write_failure_after_admission_repairs_without_second_progression(self):
        target = self.runtime/'outbox_ack'/(self.payload['result_id']+'.json')
        replace = Path.replace
        def fault(path,destination):
            if Path(destination)==target:
                raise OSError('fixture saved-result acknowledgement write failure')
            return replace(path,destination)
        with patch.object(Path,'replace',new=fault):
            with self.assertRaises(OSError):
                self.deliver()
        accepted = deepcopy(self.current())
        self.assertEqual(len(accepted['admitted_events']),1)
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))
        with patch.object(self.sessions,'admit_verified_saved_event',side_effect=AssertionError('must not readmit')):
            result = self.deliver()
        self.assertEqual(result['accepted_event_id'],self.payload['result_id'])
        self.assertEqual(self.current()['admitted_events'],accepted['admitted_events'])
        self.assertEqual(len([value for value in self.messages.get_recent(100) if value.get('type')=='session_result']),1)

    def test_projection_before_backlink_gap_repairs_uid_without_dispatching_successor(self):
        run,payload,box,_ = self.two_phase(same_seat=False)
        self.proof_query.side_effect = lambda value:{**self.proof,'dispatch_id':value['dispatch_id'],
            'seat_identity_id':value['seat_identity_id'],'launch_attempt':value['launch_attempt']}
        with patch.object(self.sessions,'link_event_projection',side_effect=OSError('fixture backlink gap')):
            with self.assertRaises(OSError):
                self.engine.deliver_saved_result(run['id'],payload['result_id'])
        current = self.sessions.get(run['id'])
        self.assertEqual(len(current['admitted_events']),1)
        self.assertIsNone(current['admitted_events'][0]['projected_message_id'])
        self.assertIsNone(current['active_invocation'])
        queue = (self.fixture.root/'queue/ledger.json').read_bytes()
        original = next(value for value in self.messages.get_recent(100) if value.get('uid')=='session-event:'+payload['result_id'])
        with patch.object(self.trigger,'trigger_sync',side_effect=AssertionError('replay projection must not dispatch')):
            self.engine.deliver_saved_result(run['id'],payload['result_id'])
        repaired = self.sessions.get(run['id'])
        self.assertEqual(repaired['admitted_events'][0]['projected_message_id'],original['id'])
        self.assertIsNone(repaired['active_invocation'])
        self.assertEqual([value for value in self.messages.get_recent(100) if value.get('uid')==original['uid']],[original])
        self.assertEqual((self.fixture.root/'queue/ledger.json').read_bytes(),queue)
        self.assertIsNotNone(box.get_ack(payload['result_id']))

    def test_hold_io_prevents_admission_and_settlement_io_cannot_claim_transport_success(self):
        before = deepcopy(self.current())
        with patch.object(self.queue,'hold_recovered',side_effect=OSError('fixture hold write failure')):
            with self.assertRaises(OSError):
                self.deliver()
        self.assertEqual(self.current(),before)
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))
        self.proof_query.return_value = self.proof
        with patch.object(self.queue,'settle_recovered',side_effect=OSError('fixture terminal write failure')):
            result = self.deliver()
        self.assertEqual(result['status'],'admitted')
        self.assertIs(result['transport_settled'],False)
        self.assertEqual(len(self.current()['admitted_events']),1)
        self.assertIsNotNone(self.box.get_ack(self.payload['result_id']))
        self.assertNotEqual(self.queue.owned(self.owner,self.old['dispatch_id'])['state'],'settled_recovered')
        self.proof_query.side_effect = OSError('fixture proof unavailable after accepted result')
        again = self.deliver()
        self.assertEqual(again['accepted_event_id'],self.payload['result_id'])
        self.assertIs(again['transport_settled'],False)

    def test_concurrent_delivery_then_store_reload_retains_one_event_message_and_stable_ack(self):
        self.proof_query.return_value = self.proof
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _:self.deliver(),range(5)))
        self.assertTrue(all(value['accepted_event_id']==self.payload['result_id'] for value in results))
        self.assertEqual(len(self.current()['admitted_events']),1)
        self.assertEqual(len([value for value in self.messages.get_recent(100) if value.get('type')=='session_result']),1)
        ack = (self.runtime/'outbox_ack'/(self.payload['result_id']+'.json')).read_bytes()
        sessions = SessionStore(str(self.fixture.root/'session_runs.json'))
        messages = MessageStore(str(self.fixture.root/'messages.jsonl'))
        engine = SessionEngine(sessions,messages,AgentTrigger(self.fixture.registry,str(self.fixture.root)),
            self.fixture.registry,seat_manager=self.fixture.manager)
        result = engine.deliver_saved_result(self.session_id,self.payload['result_id'])
        self.assertEqual(result['accepted_event_id'],self.payload['result_id'])
        self.assertEqual((self.runtime/'outbox_ack'/(self.payload['result_id']+'.json')).read_bytes(),ack)
        self.assertEqual(len(sessions.get(self.session_id)['admitted_events']),1)
        self.assertEqual(self.fixture.spawn.call_count,1)


if __name__=='__main__':
    unittest.main()
