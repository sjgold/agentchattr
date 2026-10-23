"""Skip notices, missing context and export; real stores with nonnative proof/process seams."""
import io
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid
import zipfile

import archive
from agents import AgentTrigger
from dispatch_queue import QueueConflict
from review_brief import brief_messages, missing_contributions
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict, EventValidationError
from tests import test_participant_skip_storage as fixture


class ParticipantSkipProjectionTests(unittest.TestCase):
    def setUp(self):
        fixture.ParticipantSkipStorageTests.setUp(self)
        self.decision={key:self.intent[key] for key in ('request_id','checkpoint_id','attempt_id','reason','confirm_skip')}
        seam=patch.object(self.fixture.manager,'participant_exit_proof',return_value={'local_ended':False,'reason':'unit_unproven'})
        self.proof=seam.start()
        self.addCleanup(seam.stop)

    def skip(self,decision=None):
        return self.engine.skip_participant(self.run['id'],self.decision if decision is None else decision)

    def current(self):
        return self.sessions.get(self.run['id'])

    def synth_run(self):
        self.peer,_=self.fixture.ready('api')
        self.sessions.save_custom_template({'id':'skip-synthesis','name':'Missing reviewer and genuine synthesis',
            'roles':['missing','synthesis'],'phases':[
                {'name':'Review','participants':['missing'],'prompt':'Read source.'},
                {'name':'Final','participants':['synthesis'],'prompt':'Synthesize evidence.','is_output':True}]})
        run=self.engine.start_session('skip-synthesis','skip-synthesis',
            {'missing':self.owner['name'],'synthesis':self.peer['name']},'operator',
            goal='Preserve honest missing work.',input_text='Frozen café\r\n@all source code')
        fixture.ParticipantSkipStorageTests.stalled(self,run)
        self.decision={key:self.intent[key] for key in ('request_id','checkpoint_id','attempt_id','reason','confirm_skip')}
        self.decision['reason']='Explicitly missing @all /command contribution.'

    def tolerate_io(self,callback):
        try:return callback()
        except OSError:return None

    def notice_records(self):
        return [value for value in self.messages.get_recent(500) if value['type']=='session_skip']

    def reload_engine(self):
        self.sessions=SessionStore(str(self.sessions._path))
        self.messages=MessageStore(str(self.messages._path))
        self.trigger=AgentTrigger(self.fixture.registry,str(self.fixture.root))
        self.engine=SessionEngine(self.sessions,self.messages,self.trigger,self.fixture.registry,seat_manager=self.fixture.manager)

    def test_terminal_skip_projects_explicit_missing_output_notice_as_output_anchor(self):
        ack=self.skip()
        self.assertEqual(set(ack),{'status','request_id','session_id','projection_id'})
        self.assertEqual(ack['status'],'skipped')
        run=self.current()
        audit=run['skipped_turns'][0]
        self.assertEqual(ack['projection_id'],audit['projection_id'])
        notice=self.messages.get_snapshot(audit['projected_message_id'])
        self.assertEqual(notice['type'],'session_skip')
        self.assertTrue(notice['metadata']['routing_suppressed'])
        self.assertIs(notice['metadata']['is_notice'],True)
        immutable=deepcopy(audit)
        immutable['projected_message_id']=None
        self.assertEqual(notice['metadata']['skipped_turn'],immutable)
        self.assertEqual(notice['metadata']['missing_contributions'],missing_contributions(run))
        self.assertIn(self.decision['reason'],notice['text'])
        self.assertEqual(run['output_message_id'],notice['id'])
        self.assertTrue(run['missing_output'])
        self.assertEqual(run['admitted_events'],[])

    def test_actual_archive_jsonl_preserves_missing_audit_and_never_fake_answer(self):
        self.skip()
        data=archive.build_export(self.messages,None,None,None)
        with zipfile.ZipFile(io.BytesIO(data)) as exported:
            messages=[json.loads(line) for line in exported.read('messages.jsonl').decode('utf-8').splitlines() if line]
        notice=next(value for value in messages if value['type']=='session_skip')
        self.assertTrue(notice['metadata']['routing_suppressed'])
        self.assertIn(self.decision['reason'],json.dumps(notice,ensure_ascii=False))
        self.assertFalse(any(value['type']=='session_result' for value in messages))

    def test_synthesis_brief_system_footer_and_real_zip_keep_missing_beside_authentic_result(self):
        self.synth_run()
        before=deepcopy(self.run)
        self.skip()
        current=self.current()
        self.assertFalse(current.get('missing_output',False))
        invocation=current['active_invocation']
        self.assertEqual(invocation['expected_identity_id'],self.peer['identity_id'])
        brief=self.sessions.briefs.get(invocation['brief_id'],operator=True)
        missing=missing_contributions(current)
        self.assertEqual(brief['missing_contributions'],missing)
        self.assertTrue(missing)
        self.assertEqual(brief['source'],before['input_snapshot']['text'])
        self.assertEqual(brief['prior_results'],[],'skip cannot masquerade as an accepted prior result')
        model=brief_messages(brief,[],self.peer['name'])
        self.assertIn(self.decision['reason'],json.dumps(model,ensure_ascii=False))
        missing[0]['reason']='CALLER_MUTATION'
        self.assertEqual(missing_contributions(current)[0]['reason'],self.decision['reason'])
        content='Genuine synthesis café\r\nunchanged accepted content.'
        self.engine.admit_event(invocation['brief_id'],'final',content,self.peer)
        done=self.current()
        self.assertEqual(done['admitted_events'][0]['content'],content)
        output=self.messages.get_snapshot(done['output_message_id'])
        self.assertTrue(output['text'].startswith(content))
        self.assertIn(self.decision['reason'],output['text'])
        self.assertEqual(output['metadata']['missing_contributions'],missing_contributions(done))
        self.assertFalse(done.get('missing_output',False))
        with zipfile.ZipFile(io.BytesIO(archive.build_export(self.messages,None,None,None))) as exported:
            rows=[json.loads(line) for line in exported.read('messages.jsonl').decode('utf-8').splitlines() if line]
        saved=next(value for value in rows if value['id']==output['id'])
        self.assertEqual(saved['text'],output['text'])
        self.assertEqual(saved['metadata']['missing_contributions'],output['metadata']['missing_contributions'])

    def test_message_id_zero_is_a_valid_skip_projection_and_missing_output_anchor(self):
        self.messages=MessageStore(str(self.fixture.root/'zero-messages.jsonl'))
        self.engine._messages=self.messages
        self.messages.on_message(self.engine._on_message)
        self.skip()
        audit=self.current()['skipped_turns'][0]
        self.assertEqual(audit['projected_message_id'],0)
        self.assertEqual(self.current()['output_message_id'],0)
        self.assertEqual(self.messages.get_snapshot(0)['type'],'session_skip')
        self.sessions.link_skip_projection(self.run['id'],audit['projection_id'],0)
        self.assertEqual(self.current()['output_message_id'],0)

    def test_concurrent_replay_reload_and_advanced_question_continue_never_dispatch_old_successor(self):
        self.synth_run()
        gate=threading.Barrier(4)
        def skip_once(_):
            gate.wait(timeout=5)
            return self.skip()
        with ThreadPoolExecutor(max_workers=4) as pool:acks=list(pool.map(skip_once,range(4)))
        self.assertTrue(all(value==acks[0] for value in acks))
        self.assertEqual(len(self.current()['skipped_turns']),1)
        self.assertEqual(len(self.notice_records()),1)
        self.assertEqual(len(self.trigger.queue.for_identity(self.peer)),1)
        original=deepcopy(self.current()['active_invocation'])
        question=self.engine.admit_event(original['brief_id'],'question','Actual synthesis clarification?',self.peer)
        self.engine.continue_session(self.run['id'],question['event_id'],'Explicit continuation answer')
        advanced=deepcopy(self.current()['active_invocation'])
        self.assertNotEqual(advanced['attempt_id'],original['attempt_id'])
        records=self.trigger.queue.for_identity(self.peer)
        self.reload_engine()
        with patch.object(self.trigger,'trigger_sync',side_effect=AssertionError('old skip replay dispatched work')):
            self.assertEqual(self.skip(),acks[0])
        self.assertEqual(self.current()['active_invocation'],advanced)
        self.assertEqual(self.trigger.queue.for_identity(self.peer),records)

    def test_projection_before_backlink_gap_repairs_one_notice_and_one_immediate_successor(self):
        self.synth_run()
        with patch.object(self.sessions,'link_skip_projection',side_effect=OSError('Skip backlink gap')):
            self.tolerate_io(self.skip)
        self.assertEqual(len(self.current()['skipped_turns']),1)
        self.assertIsNone(self.current()['skipped_turns'][0]['projected_message_id'])
        self.assertEqual(len(self.notice_records()),1)
        uid=self.notice_records()[0]['uid']
        self.skip()
        self.assertEqual(len(self.notice_records()),1)
        self.assertEqual(self.notice_records()[0]['uid'],uid)
        self.assertIsNotNone(self.current()['skipped_turns'][0]['projected_message_id'])
        self.assertEqual(len(self.trigger.queue.for_identity(self.peer)),1)

    def test_brief_write_gap_reuses_deterministic_successor_generation_ids(self):
        self.synth_run()
        captured=[]
        def fail(envelope,*args,**kwargs):
            captured.append(deepcopy(envelope))
            raise OSError('Immediate successor brief gap')
        with patch.object(self.sessions.briefs,'put',side_effect=fail):
            self.tolerate_io(self.skip)
        self.assertTrue(captured)
        self.skip()
        invocation=self.current()['active_invocation']
        for field in ('attempt_id','brief_id'):
            self.assertEqual(invocation[field],captured[0][field])
        self.assertEqual(len(self.trigger.queue.for_identity(self.peer)),1)
        self.assertEqual(len(self.current()['skipped_turns']),1)

    def test_enqueue_write_gap_retains_bound_immediate_ids_and_one_repaired_envelope(self):
        self.synth_run()
        with patch.object(self.trigger.queue,'enqueue',side_effect=OSError('Immediate successor queue gap')):
            self.tolerate_io(self.skip)
        invocation=deepcopy(self.current()['active_invocation'])
        self.assertIsNotNone(invocation)
        self.assertEqual(self.trigger.queue.for_identity(self.peer),[])
        self.skip()
        repaired=self.current()['active_invocation']
        for field in ('attempt_id','brief_id','dispatch_id'):
            self.assertEqual(repaired[field],invocation[field])
        records=self.trigger.queue.for_identity(self.peer)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]['envelope']['dispatch_id'],invocation['dispatch_id'])

    def test_committed_enqueue_lost_reply_exact_skip_replay_never_sends_another_envelope(self):
        self.synth_run()
        queue=self.trigger.queue
        enqueue=queue.enqueue
        def commit_then_lose(instance,envelope):
            result=enqueue(instance,envelope)
            if instance['identity_id']==self.peer['identity_id']:raise OSError('Lost successor enqueue reply')
            return result
        with patch.object(queue,'enqueue',side_effect=commit_then_lose):self.tolerate_io(self.skip)
        records=queue.for_identity(self.peer)
        self.assertEqual(len(records),1)
        with patch.object(self.trigger,'trigger_sync',side_effect=AssertionError('committed successor dispatched again')):
            self.skip()
        self.assertEqual(queue.for_identity(self.peer),records)

    def test_old_identity_hold_peer_progress_stop_and_late_output_remain_fenced(self):
        self.synth_run()
        original=deepcopy(self.run['active_invocation'])
        ack=self.skip()
        current=self.current()
        self.assertEqual(current['active_invocation']['expected_identity_id'],self.peer['identity_id'])
        with self.assertRaises(QueueConflict):self.trigger.queue.claim(self.owner,'new-old-consumer')
        claimed=self.trigger.queue.claim(self.peer,'real-peer-consumer')
        self.assertEqual(claimed['envelope']['dispatch_id'],current['active_invocation']['dispatch_id'])
        self.sessions.stop_run(self.run['id'],'Stop after skipped contribution')
        with patch.object(self.trigger,'trigger_sync',side_effect=AssertionError('stopped skip replay dispatched')):
            self.assertEqual(self.skip(),ack)
        with self.assertRaises(EventConflict):
            self.engine.admit_event(original['brief_id'],'final','LATE_SKIPPED_CONTRIBUTION',self.owner)
        self.assertTrue(any(value['content']=='LATE_SKIPPED_CONTRIBUTION' for value in self.current()['quarantined_events']))
        self.assertEqual(self.current()['admitted_events'],[])

    def test_strict_decision_and_normal_final_first_writer_have_one_durable_outcome(self):
        before=self.sessions._path.read_bytes()
        for changes in ({'text':'override'},{'request_id':True},{'confirm_skip':1},{'reason':''},
                        {'checkpoint_id':uuid.uuid4().hex},{'attempt_id':uuid.uuid4().hex}):
            with self.subTest(changes=changes),self.assertRaises((EventValidationError,EventConflict)):
                self.skip(dict(self.decision,**changes))
            self.assertEqual(self.sessions._path.read_bytes(),before)
        barrier=threading.Barrier(2)
        def race(skip):
            barrier.wait(timeout=5)
            try:
                if skip:self.skip()
                else:self.engine.admit_event(self.run['active_invocation']['brief_id'],'final','Actual completed answer',self.owner)
                return 'accepted'
            except EventConflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(race,(True,False)))
        self.assertCountEqual(results,['accepted','conflict'])
        self.assertEqual(len(self.current()['admitted_events'])+len(self.current().get('skipped_turns',[])),1)

    def test_atomic_skip_store_failure_precedes_any_queue_notice_or_exit_proof_effect(self):
        memory,disk=self.sessions.list_all(),self.sessions._path.read_bytes()
        queue=self.trigger.queue.status()
        messages=self.messages._path.read_bytes() if self.messages._path.exists() else None
        replace=Path.replace
        def fail(path,target):
            if Path(target)==self.sessions._path:raise OSError('Injected skip commit failure')
            return replace(path,target)
        with patch.object(Path,'replace',fail):self.tolerate_io(self.skip)
        self.assertEqual(self.sessions.list_all(),memory)
        self.assertEqual(self.sessions._path.read_bytes(),disk)
        self.assertEqual(self.trigger.queue.status(),queue)
        self.assertEqual(self.messages._path.read_bytes() if self.messages._path.exists() else None,messages)
        self.proof.assert_not_called()
