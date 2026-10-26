"""ROOT D4 observed reds, real owned authority/store/queue/outbox fixtures.

B tests fail behaviorally on current in-boundary diagnostic I/O. Tests looking
up the frozen driver/intent/marker seam are INFRASTRUCTURE reds until it exists.
Assertions past the first red are explicitly unobserved until green; per-test
conditions are in TICKET-20-D4-REDS.md. No timing gate/provider/native claims.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError, is_dataclass
import hashlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

import artifact_service as authority
import artifact_store as storage
from artifact_delivery import ArtifactOutbox
from artifact_transport import failure
from channel_lifecycle import ChannelInactive
from tests import test_artifact_admission as admission_fixture


class CrashAfterDiagnostic(BaseException):
    pass


class ArtifactDiagnosticPhaseTests(unittest.TestCase):
    def fixture(self, kind='cli', *, source=False):
        case=admission_fixture.ArtifactAdmissionTests();case.setUp();case.setup_authority()
        self.addCleanup(lambda:self.assertFalse(case.root.exists()))
        self.addCleanup(case.doCleanups)
        instance=case.instance
        if kind in ('reject','delivery'):
            instance,_,_=case.launch_binding('api')
        audit,packet=case.new_request(instance=instance)
        session=None
        if source:
            case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
            session=case.sessions.create('planning','review',
                {'planner':'planner','challenger':'challenger','synthesiser':'synthesiser'},
                'operator',goal='Diagnostic phase source',input_text='Frozen source')
            request=uuid.uuid4().hex;ids=storage.request_ids(request)
            audit.update(request_id=request,**{key:ids[key] for key in ('lineage_id','attempt_id','dispatch_id','brief_id')})
            revision=hashlib.sha256(b'Frozen source').hexdigest()
            run={'session_id':session['id'],'run_id':session['run_id'],'input_revision':revision,'state_at_request':session['state']}
            packet.update(scope_kind='run_accepted_messages',source_run=run,
                input={'text':'Frozen source','input_revision':revision,'source_document':None})
            audit.update(source_run=deepcopy(run),scope=case.artifacts.put_packet(request,packet))
        case.authority.prepare_request(audit,packet,audit['request_id'])
        consumer=case.claim(audit,instance)
        record=case.sealed_fixture_record(audit,consumer,
            observation=({'confirmed_model':None,'confirmation_reason':'provider_did_not_report_model'}
                if kind in ('reject','delivery') else None))
        box=ArtifactOutbox(case.root/'api_seat_runtime'/audit['producer']['launch_attempt'])
        return case,audit,instance,consumer,record,box,session

    def action(self, kind):
        if kind=='startup_unmatched':
            case=admission_fixture.ArtifactAdmissionTests();case.setUp();case.setup_authority()
            self.addCleanup(lambda:self.assertFalse(case.root.exists()));self.addCleanup(case.doCleanups)
            audit,_=case.new_request();instance=case.instance;consumer='retained-unmatched-consumer'
            case.briefs.put(case.authority._brief(audit),owner=case.authority._owner(audit))
            record=case.sealed_fixture_record(audit,consumer)
            box=ArtifactOutbox(case.attempt['snapshot'].parent)
            box.save(record['payload'],case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
            return (case,audit,instance,consumer,record,box,None),lambda:case.authority.recover_startup()
        values=self.fixture(kind)
        case,audit,instance,consumer,record,box,_=values
        if kind in ('brief','delivery','resume','retained'):
            if kind=='retained':
                case.authority.get_brief(audit['brief_id'],instance)
                box.save(record['payload'],case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
                case.trigger.queue.release(instance,audit['dispatch_id'],consumer)
            case.artifacts._object_path('packet',audit['scope']['packet_id']).write_bytes(b'BROKEN_PACKET')
        if kind in ('saved','fulfilled','ack','startup'):
            case.authority.get_brief(audit['brief_id'],instance)
            if kind=='saved':
                record=deepcopy(record);record['payload']['expected_parent']={'version_id':'e'*32,'sequence':1,'sha256':'f'*64}
                record=case.protocol.seal_result(record['payload'],case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
            if kind in ('fulfilled','ack'):
                case.artifacts.commit_version(audit['request_id'],audit['attempt_id'],audit['dispatch_id'],
                    '# Previously committed',record['payload']['observation'])
            if kind in ('ack','startup'):
                box.save(record['payload'],case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
            if kind=='startup':case.authority.cancel_request(audit['request_id'])
        if kind=='unmatched':
            record=deepcopy(record);record['payload'].update(request_id='a'*32,dispatch_id='b'*32,result_id='b'*32)
        calls={
            'cli':lambda:case.authority.submit_cli(audit['brief_id'],'',instance),
            'reject':lambda:case.authority.reject_response(audit['brief_id'],'invalid structured response',instance),
            'brief':lambda:case.authority.get_brief(audit['brief_id'],instance),
            'delivery':lambda:case.authority.get_delivery(audit['brief_id'],instance),
            'resume':lambda:case.authority.resume_request(audit['request_id']),
            'retained':lambda:case.authority.resume_request(audit['request_id'],recover_saved=True),
            'saved':lambda:case.authority.admit_saved(record,instance),
            'fulfilled':lambda:case.authority.admit_saved(record,instance),
            'ack':lambda:case.authority.resume_request(audit['request_id'],recover_saved=True),
            'startup':lambda:case.authority.recover_startup(),
            'unmatched':lambda:case.authority.admit_saved(record,instance)}
        return values,calls[kind]

    @staticmethod
    def outcome(action):
        try:return ('ok',action())
        except Exception as error:return ('error',error)

    def pause(self,case,action,peer,*,after_durable=False):
        """Event proof, no sleeps/latency claim. Always release/join on red."""
        entered,proceed,peer_done=threading.Event(),threading.Event(),threading.Event()
        original=case.artifacts.diagnostic_store.record
        def blocked(*args,**kwargs):
            value=original(*args,**kwargs) if after_durable else None
            entered.set()
            if not proceed.wait(5):raise AssertionError('test failed to release diagnostic I/O')
            return value if after_durable else original(*args,**kwargs)
        def competing():
            try:return self.outcome(peer)
            finally:peer_done.set()
        with ThreadPoolExecutor(max_workers=2) as pool,patch.object(case.artifacts.diagnostic_store,'record',blocked):
            operation=pool.submit(self.outcome,action)
            contender=None
            try:
                self.assertTrue(entered.wait(2),'fixture never reached the real diagnostic writer')
                contender=pool.submit(competing)
                progressed=peer_done.wait(.75)
            finally:proceed.set()
            original_result=operation.result(timeout=3)
            competing_result=contender.result(timeout=3) if contender is not None else None
        self.assertTrue(progressed,'peer cannot progress until diagnostic I/O releases authority boundary')
        # Unobserved on current product: C/race assertions in each caller.
        return original_result,competing_result

    def test_diagnostic_io_is_outside_all_three_authority_locks_per_caller(self):
        for kind in ('cli','reject','brief','delivery','resume','retained','saved','fulfilled','ack','startup','unmatched','startup_unmatched'):
            with self.subTest(caller=kind):
                (case,*_),action=self.action(kind);seen=[]
                original=case.artifacts.diagnostic_store.record
                def observed(*args,**kwargs):
                    seen.append(True)
                    self.assertFalse(case.engine._lock._is_owned(),'B owns engine lock')
                    self.assertFalse(case.catalog._lock._is_owned(),'B owns catalog lock')
                    self.assertFalse(case.artifacts._lock._is_owned(),'B owns authoring lock')
                    return original(*args,**kwargs)
                with patch.object(case.artifacts.diagnostic_store,'record',observed):
                    try:action()
                    except (authority.ArtifactInputError,storage.ArtifactUnavailable):pass
                self.assertEqual(seen,[True])

    def test_diagnostic_io_releases_authority_boundary_for_cancel(self):
        for kind in ('cli','reject','brief','delivery','resume','retained','saved'):
            with self.subTest(caller=kind):
                values,action=self.action(kind);case,audit,_,_,_,box,_=values
                outcome,other=self.pause(case,action,lambda:case.authority.cancel_request(audit['request_id']))
                self.assertEqual(other[0],'ok')
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')
                self.assertIsNone(box.get_ack(audit['dispatch_id']));self.assertIsNone(box.get_disposition(audit['dispatch_id']))
                self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'],0)
                if kind in ('resume','retained'):
                    self.assertEqual(outcome[0],'ok');self.assertIsNone(outcome[1]['admission'])
                else:
                    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)

    def test_diagnostic_io_releases_authority_boundary_for_stop(self):
        for kind in ('cli','reject'):
            with self.subTest(caller=kind):
                case,audit,instance,_,_,box,session=self.fixture(kind,source=True)
                action=(lambda:case.authority.reject_response(audit['brief_id'],'bad',instance)) if kind=='reject' else (lambda:case.authority.submit_cli(audit['brief_id'],'',instance))
                def stop():
                    # Real service/engine Stop ordering, no HTTP/native claim.
                    with case.service._boundary():
                        fenced=case.authority.fence_source_requests(session['run_id'])
                        stopped=case.engine.stop_session(session['id'])
                    case.authority.repair_cancel_fences(fenced['request_ids'])
                    return stopped
                outcome,other=self.pause(case,action,stop)
                self.assertEqual(other[0],'ok');self.assertEqual(other[1]['state'],'stopped')
                row=case.artifacts.get_request(audit['request_id'])
                self.assertEqual((row['state'],row['reason']),('cancelled','source_stopped'))
                self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)
                self.assertIsNone(box.get_ack(audit['dispatch_id']));self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'],0)

    def test_second_writer_during_diagnostic_io_refuses_stale_settlement(self):
        for kind in ('cli','reject'):
            with self.subTest(caller=kind):
                values,action=self.action(kind);case,audit,instance,_,record,box,_=values
                outcome,other=self.pause(case,action,lambda:case.authority.admit_saved(record,instance))
                self.assertEqual(other[0],'ok');self.assertEqual(other[1]['status'],'admitted')
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'fulfilled')
                self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'],1)
                self.assertIsNotNone(box.get_ack(audit['dispatch_id']))
                self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)

    def test_crash_after_durable_diagnostic_before_settlement_replays_safely(self):
        for kind in ('reject','startup'):
            with self.subTest(caller=kind):
                values,action=self.action(kind);case,audit,_,_,_,box,_=values
                settle=case.authority._settle_diagnostic_intent  # INFRASTRUCTURE until D4.
                with patch.object(case.authority,'_settle_diagnostic_intent',side_effect=CrashAfterDiagnostic):
                    with self.assertRaises(CrashAfterDiagnostic):action()
                data=case.artifacts.diagnostic_store._data
                self.assertEqual(len(data['diagnostics']),1);identifier=next(iter(data['diagnostics']))
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active' if kind=='reject' else 'cancelled')
                self.assertIsNone(box.get_disposition(audit['dispatch_id']));self.assertIsNone(box.get_ack(audit['dispatch_id']))
                if kind=='reject':
                    replay=case.authority.recover_startup()
                    self.assertEqual(replay['quarantined'],[])
                    self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')
                result=action()
                self.assertEqual(result['diagnostic_id'] if kind=='reject' else result['quarantined'][0],identifier)
                self.assertEqual(len(case.artifacts.diagnostic_store._data['diagnostics']),1)
                self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'],0)

    def test_mcp_parent_first_context_has_no_outer_diagnostic_boundary(self):
        import mcp_bridge
        case,audit,instance,_,_,_,_=self.fixture()
        original=case.authority._get_parent_locked;parents=[]
        def parent(*args):
            result=original(*args);parents.append(result)
            case.artifacts._object_path('packet',audit['scope']['packet_id']).write_bytes(b'DAMAGE_AFTER_PARENT')
            return result
        with patch.object(case.authority,'_get_parent_locked',parent),patch.object(mcp_bridge,'artifact_authority',case.authority),patch.object(mcp_bridge,'_authenticated_instance',return_value=instance):
            outcome,other=self.pause(case,lambda:json.loads(mcp_bridge.chat_artifact_brief(audit['brief_id'])),lambda:case.service.require_active('peer'))
        self.assertEqual(len(parents),1);self.assertEqual(other[0],'ok')
        self.assertEqual(outcome[0],'ok');self.assertEqual(outcome[1]['code'],'artifact_storage_unavailable')
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'failed')

    def test_healthy_mcp_parent_and_brief_share_one_capture_boundary(self):
        import mcp_bridge
        case,audit,instance,_,_,_,_=self.fixture()
        original_boundary=case.service._boundary;state={'depth':0,'token':None};calls=[]
        @contextmanager
        def boundary():
            if state['depth']==0:state['token']=object()
            state['depth']+=1
            try:
                with original_boundary():yield
            finally:state['depth']-=1
        parent=case.authority._get_parent_locked;brief=case.authority._get_brief_locked
        def observed(name,method,*args):
            self.assertGreater(state['depth'],0)
            self.assertTrue(case.engine._lock._is_owned());self.assertTrue(case.catalog._lock._is_owned())
            calls.append((name,state['token']))
            return method(*args)
        with patch.object(case.service,'_boundary',boundary),patch.object(case.authority,'_get_parent_locked',lambda *args:observed('parent',parent,*args)),patch.object(case.authority,'_get_brief_locked',lambda *args:observed('brief',brief,*args)),patch.object(mcp_bridge,'artifact_authority',case.authority),patch.object(mcp_bridge,'_authenticated_instance',return_value=instance):
            result=json.loads(mcp_bridge.chat_artifact_brief(audit['brief_id']))
        self.assertEqual(set(result),{'brief','packet','parent'})
        self.assertEqual([name for name,_ in calls],['parent','brief'])
        self.assertIs(calls[0][1],calls[1][1])  # Existing A1 guard, preserved by D4.

    def test_startup_diagnostic_io_has_per_item_boundaries_and_fresh_cancel_count(self):
        values,action=self.action('resume');case,audit,_,_,_,_,_=values
        outcome,other=self.pause(case,case.authority.recover_startup,lambda:case.authority.cancel_request(audit['request_id']))
        self.assertEqual(other[0],'ok');self.assertEqual(outcome[0],'ok')
        self.assertNotIn(audit['request_id'],outcome[1]['enqueue_repaired'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')

    def test_startup_terminal_diagnostic_allows_independent_peer(self):
        (case,*_),action=self.action('startup')
        outcome,other=self.pause(case,action,lambda:case.service.require_active('peer'))
        self.assertEqual(other[0],'ok');self.assertEqual(outcome[0],'ok')
        self.assertEqual(len(outcome[1]['quarantined']),1)

    def test_startup_snapshot_is_outside_boundary_and_resume_marks_are_fresh(self):
        (case,*_),_=self.action('cli');seen=[]
        original=case.artifacts.channel_names
        def names():
            seen.append(True)
            self.assertFalse(case.engine._lock._is_owned())
            self.assertFalse(case.catalog._lock._is_owned())
            return original()
        with patch.object(case.artifacts,'channel_names',names):case.authority.recover_startup()
        self.assertTrue(seen)

    def test_diagnostic_reads_do_not_hold_authoring_lock_during_orphan_scan(self):
        case,audit,_,_,_,_,_=self.fixture()
        orphan=case.artifacts._object_path('packet','d'*32);orphan.write_bytes(b'{}')
        entered,proceed=threading.Event(),threading.Event();original=Path.stat
        def paused(path,*args,**kwargs):
            if path==orphan and threading.current_thread().name.startswith('diagnostic-read'):
                entered.set()
                if not proceed.wait(5):raise AssertionError('orphan stat not released')
            return original(path,*args,**kwargs)
        with ThreadPoolExecutor(max_workers=2,thread_name_prefix='diagnostic-read') as pool,patch.object(Path,'stat',paused):
            reading=pool.submit(case.artifacts.diagnostics)
            try:
                self.assertTrue(entered.wait(2))
                other=pool.submit(case.authority.cancel_request,audit['request_id'])
                from concurrent.futures import wait
                finished=bool(wait([other],timeout=.75).done)
            finally:proceed.set()
            report=reading.result(timeout=3);other.result(timeout=3)
        self.assertTrue(finished,'authoring lock blocks cancellation during observational stat')
        self.assertTrue(report['owners']['authoring']['available'])

    def test_request_diagnostic_reads_run_without_authority_or_authoring_locks(self):
        case,audit,_,_,_,_,_=self.fixture();seen=[]
        case.artifacts.quarantine_submission(audit['request_id'],audit['attempt_id'],audit['dispatch_id'],reason='invalid_content',content='known')
        original=case.artifacts.diagnostic_store._check_diagnostics
        def observed():
            seen.append(True)
            self.assertFalse(case.engine._lock._is_owned());self.assertFalse(case.catalog._lock._is_owned())
            self.assertFalse(case.artifacts._lock._is_owned())
            return original()
        with patch.object(case.artifacts.diagnostic_store,'_check_diagnostics',observed):
            self.assertEqual(len(case.artifacts.request_diagnostics(audit['request_id'])['quarantine_ids']),1)
        self.assertTrue(seen)  # Existing outside-boundary read guard, not a new red.

    def test_diagnostic_driver_refuses_caller_held_boundary(self):
        for name in ('engine','catalog','authoring'):
            with self.subTest(lock=name):
                case,audit,instance,_,_,_,_=self.fixture()
                lock={'engine':case.engine._lock,'catalog':case.catalog._lock,'authoring':case.artifacts._lock}[name]
                before=case.files()
                with lock,self.assertRaises(storage.ArtifactUnavailable) as caught:
                    case.authority.get_brief(audit['brief_id'],instance)
                self.assertEqual(type(caught.exception).__name__,'_ArtifactBoundaryHeld')
                self.assertEqual(caught.exception.code,'artifact_boundary_held')
                self.assertEqual(failure(caught.exception)[0],'artifact_storage_unavailable')
                self.assertEqual(case.files(),before)

    def test_diagnostic_driver_refuses_unsupported_ownership_query(self):
        case,audit,instance,_,_,_,_=self.fixture();original=case.engine._lock
        class Unsupported:
            _is_owned=None
            def __enter__(self):return original.__enter__()
            def __exit__(self,*args):return original.__exit__(*args)
        before=case.files()
        with patch.object(case.engine,'_lock',Unsupported()),self.assertRaises(storage.ArtifactUnavailable) as caught:
            case.authority.get_brief(audit['brief_id'],instance)
        self.assertEqual(caught.exception.code,'artifact_boundary_held');self.assertEqual(case.files(),before)

    def test_guard_modes_capture_current_state_and_immutable_intent(self):
        modes={'cli':'live_claim','reject':'live_claim','brief':'live_claim','delivery':'live_claim',
            'resume':'reservation_resume','retained':'retained_recovery','saved':'live_claim',
            'fulfilled':'fulfilled_replay','ack':'fulfilled_ack','startup':'terminal_saved','unmatched':'unmatched_saved_live','startup_unmatched':'unmatched_saved_retained'}
        for kind,mode in modes.items():
            with self.subTest(caller=kind):
                values,action=self.action(kind);case,audit,*_=values
                original=case.authority._persist_diagnostic_intent  # INFRASTRUCTURE.
                seen=[]
                def persist(intent):
                    self.assertTrue(is_dataclass(intent));self.assertTrue(is_dataclass(intent.guard))
                    self.assertEqual(intent.guard.mode,mode)
                    self.assertEqual(intent.guard.state,case.artifacts.get_request(audit['request_id'])['state'] if kind not in ('unmatched','startup_unmatched') else None)
                    with self.assertRaises(FrozenInstanceError):intent.reason='changed'
                    seen.append(intent)
                    return original(intent)
                with patch.object(case.authority,'_persist_diagnostic_intent',persist):
                    try:action()
                    except (authority.ArtifactInputError,storage.ArtifactUnavailable):pass
                self.assertEqual(len(seen),1)

    def test_c_live_claim_allows_acknowledged_transition(self):
        values,action=self.action('reject');case,audit,instance,consumer,*_=values
        original=case.authority._persist_diagnostic_intent  # INFRASTRUCTURE.
        def persist(intent):
            result=original(intent)
            case.trigger.queue.acknowledge(instance,audit['dispatch_id'],consumer)
            return result
        with patch.object(case.authority,'_persist_diagnostic_intent',persist):result=action()
        self.assertEqual(result['status'],'quarantined');self.assertTrue(result['request_terminal'])

    def test_c_fulfilled_replay_ignores_queue_release_and_fences(self):
        values,action=self.action('fulfilled');case,audit,instance,consumer,*_=values
        original=case.authority._persist_diagnostic_intent
        def persist(intent):
            result=original(intent)
            case.trigger.queue.release(instance,audit['dispatch_id'],consumer)
            case.trigger.queue.cancel_dispatch(audit['dispatch_id'],'f'*32)
            return result
        with patch.object(case.authority,'_persist_diagnostic_intent',persist):result=action()
        self.assertEqual(result['status'],'quarantined');self.assertFalse(result['request_terminal'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'fulfilled')

    def test_inactive_channel_a_maps_400_but_new_inactive_c_maps_409(self):
        case,audit,instance,_,_,_,_=self.fixture('reject')
        with patch.object(case.service,'require_active',side_effect=ChannelInactive('fixture inactive')):
            result=self.outcome(lambda:case.authority.reject_response(audit['brief_id'],'bad',instance))
        self.assertEqual(failure(result[1])[0],'artifact_invalid_request')  # Existing A guard reached first.
        original=case.authority._persist_diagnostic_intent  # INFRASTRUCTURE until D4.
        with ExitStack() as stack:
            def persist(intent):
                value=original(intent)
                stack.enter_context(patch.object(case.service,'require_active',side_effect=ChannelInactive('inactive after B')))
                return value
            stack.enter_context(patch.object(case.authority,'_persist_diagnostic_intent',persist))
            result=self.outcome(lambda:case.authority.reject_response(audit['brief_id'],'bad',instance))
        self.assertEqual(result[0],'error');self.assertIsInstance(result[1],storage.ArtifactConflict)
        self.assertEqual(failure(result[1])[0],'artifact_conflict')
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')

    def test_fulfilled_ack_and_replay_do_not_gain_active_channel_requirement(self):
        for kind in ('ack','fulfilled','startup'):
            with self.subTest(caller=kind):
                (case,*_),action=self.action(kind)
                original=case.authority._persist_diagnostic_intent
                with ExitStack() as stack:
                    def persist(intent):
                        value=original(intent)
                        stack.enter_context(patch.object(case.service,'require_active',side_effect=AssertionError('new active-channel requirement')))
                        return value
                    stack.enter_context(patch.object(case.authority,'_persist_diagnostic_intent',persist))
                    result=action()
                self.assertIsInstance(result,dict)

    def test_foreign_receipt_and_second_settlement_are_refused_without_effect(self):
        values,action=self.action('reject');case,audit,*_=values
        original=case.authority._settle_diagnostic_intent;captured=[]
        def settle(intent,receipt,*,invocation_key):
            captured.append((intent,receipt,invocation_key))
            with self.assertRaises(storage.ArtifactConflict):
                original(intent,receipt,invocation_key=object())
            return original(intent,receipt,invocation_key=invocation_key)
        with patch.object(case.authority,'_settle_diagnostic_intent',settle):action()
        before=case.files();self.assertEqual(len(captured),1)
        with case.service._boundary(),self.assertRaises(storage.ArtifactConflict):
            original(captured[0][0],captured[0][1],invocation_key=captured[0][2])
        self.assertEqual(case.files(),before)

    def test_c_settlement_never_reads_or_writes_diagnostic_owner(self):
        (case,*_),action=self.action('reject')
        original=case.authority._settle_diagnostic_intent
        def settle(*args,**kwargs):
            with ExitStack() as stack:
                for name in ('record','report','request_diagnostics','_check_diagnostics'):
                    stack.enter_context(patch.object(case.artifacts.diagnostic_store,name,side_effect=AssertionError('C touched diagnostic owner')))
                return original(*args,**kwargs)
        with patch.object(case.authority,'_settle_diagnostic_intent',settle):result=action()
        self.assertTrue(result['request_terminal'])

    def test_legacy_marker_is_created_before_authoring_load(self):
        root=self.fixture()[0].root/'legacy-marker-construction';seen=[]
        original=storage.ArtifactStore._load_index
        def load(owner):
            marker=owner._diagnostic_legacy_marker  # INFRASTRUCTURE.
            self.assertIsInstance(marker,threading.Event)
            self.assertFalse(hasattr(owner,'diagnostic_store'))
            seen.append(marker)
            return original(owner)
        with patch.object(storage.ArtifactStore,'_load_index',load):owner=storage.ArtifactStore(root)
        self.assertEqual(seen,[owner._diagnostic_legacy_marker])

    def test_legacy_marker_capture_never_waits_for_diagnostic_lock(self):
        case,audit,_,_,_,_,_=self.fixture()
        capture=case.artifacts._capture_diagnostic_attachment  # INFRASTRUCTURE.
        entered,proceed=threading.Event(),threading.Event()
        def hold():
            with case.artifacts.diagnostic_store._lock:
                entered.set();proceed.wait(3)
        with ThreadPoolExecutor(max_workers=2) as pool:
            held=pool.submit(hold)
            try:
                self.assertTrue(entered.wait(1))
                result=pool.submit(capture,audit['request_id'],audit['dispatch_id'])
                self.assertEqual(result.result(timeout=.75),audit['request_id'])
                case.artifacts._diagnostic_legacy_marker.set()
                with self.assertRaises(storage.ArtifactUnavailable):capture(audit['request_id'],audit['dispatch_id'])
            finally:proceed.set()
            held.result(timeout=2)
        with self.assertRaises(storage.ArtifactDiagnosticsUnavailable):
            case.artifacts.diagnostic_store.record(None,'a'*32,'b'*32,reason='invalid_content')
        self.assertFalse(case.artifacts.diagnostic_store.path.exists())

    def test_diagnostic_guard_uses_current_row_and_distinct_claim_key(self):
        case,audit,instance,consumer,record,_,_=self.fixture()
        record=deepcopy(record);record['payload']['request_id']='c'*32
        record=case.protocol.seal_result(record['payload'],case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
        original=case.authority._persist_diagnostic_intent;seen=[]
        def immutable(value):
            self.assertNotIsInstance(value,(dict,list))
            if is_dataclass(value):
                for field in value.__dataclass_fields__:immutable(getattr(value,field))
            elif isinstance(value,tuple):
                for item in value:immutable(item)
        def persist(intent):
            seen.append(intent);immutable(intent)
            self.assertEqual(intent.request_id,'c'*32)
            self.assertEqual(intent.guard.request_id,audit['request_id'])
            self.assertIsNone(intent.attached_request_id)
            # Source object mutation cannot rewrite captured immutable diagnostic input.
            record['payload']['markdown']='# Changed after capture'
            return original(intent)
        with patch.object(case.authority,'_persist_diagnostic_intent',persist):
            result=case.authority.admit_saved(record,instance)
        self.assertEqual(len(seen),1);self.assertFalse(result['request_terminal'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'queued')
        row=case.artifacts.diagnostic_store._data['diagnostics'][result['diagnostic_id']]
        self.assertEqual(row['sha256'],hashlib.sha256('# Exact café\r\nresult'.encode()).hexdigest())

    def test_unmatched_lookup_becoming_present_refuses_stale_receipt(self):
        (case,*_),action=self.action('unmatched')
        original=case.authority._persist_diagnostic_intent
        created=[]
        def persist(intent):
            result=original(intent)
            audit,packet=case.new_request();ids=storage.request_ids('a'*32)
            audit.update(request_id='a'*32,**{key:ids[key] for key in ('lineage_id','attempt_id','dispatch_id','brief_id')})
            audit['scope']=case.artifacts.put_packet('a'*32,packet)
            case.authority.prepare_request(audit,packet,'a'*32);created.append(audit)
            return result
        with patch.object(case.authority,'_persist_diagnostic_intent',persist),self.assertRaises(storage.ArtifactConflict):action()
        self.assertEqual(len(created),1)
        self.assertEqual(case.artifacts.get_request('a'*32)['state'],'queued')
        self.assertEqual(case.artifacts.request_diagnostics('a'*32)['quarantine_ids'],[])
        self.assertEqual(case.artifacts.diagnostics()['detailed_count'],1)

    def test_producer_disappearing_after_diagnostic_refuses_c_without_transition(self):
        values,action=self.action('reject');case,audit,*_=values
        original=case.authority._persist_diagnostic_intent
        def persist(intent):
            result=original(intent);case.manager.stop('team','api');return result
        with patch.object(case.authority,'_persist_diagnostic_intent',persist):result=self.outcome(action)
        self.assertEqual(result[0],'error')
        self.assertIn(failure(result[1])[0],('artifact_conflict','artifact_access_denied'))
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')
        self.assertEqual(case.artifacts.diagnostics()['detailed_count'],1)
        self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'],0)

    def test_diagnostic_durable_precedes_terminal_state_and_saved_disposition(self):
        for kind in ('reject','startup'):
            with self.subTest(caller=kind):
                values,action=self.action(kind);case,audit,*_=values;seen=[]
                def durable():
                    cold=storage.ArtifactDiagnosticStore(case.root)
                    self.assertEqual(cold.report()['detailed_count'],1)
                    seen.append(True)
                original_state=case.artifacts.set_attempt_state
                original_disposition=ArtifactOutbox.quarantine
                def state(*args,**kwargs):
                    if args[3]['state'] in ('failed','quarantined'):durable()
                    return original_state(*args,**kwargs)
                def disposition(box,*args,**kwargs):
                    durable();return original_disposition(box,*args,**kwargs)
                with patch.object(case.artifacts,'set_attempt_state',state),patch.object(ArtifactOutbox,'quarantine',disposition):action()
                self.assertEqual(seen,[True])  # Existing ordering guard, not a new red.

    def test_existing_quarantined_before_fence_crash_is_not_falsely_repaired(self):
        values,action=self.action('reject');case,audit,_,_,_,box,_=values
        with patch.object(case.authority,'_fence',side_effect=OSError('fence crash')):
            with self.assertRaises(OSError):action()
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'quarantined')
        with patch.object(case.authority,'_fence',side_effect=AssertionError('new terminal repair policy')):
            resumed=case.authority.resume_request(audit['request_id'])
            recovered=case.authority.recover_startup()
        self.assertEqual(resumed['request']['state'],'quarantined')
        self.assertNotIn(audit['request_id'],recovered['cancel_fence_repaired'])
        self.assertEqual(recovered['admitted'],[]);self.assertIsNone(box.get_ack(audit['dispatch_id']))

    def test_legacy_discovered_during_metadata_replace_keeps_landed_bytes_and_refuses_c(self):
        values,action=self.action('reject');case,audit,*_=values
        marker=case.artifacts._diagnostic_legacy_marker  # INFRASTRUCTURE.
        original=storage.atomic_json
        def replaced(path,value):
            original(path,value)
            if Path(path)==case.artifacts.diagnostic_store.path:
                legacy=json.loads(case.artifacts.path.read_bytes())
                legacy.update(version=1,diagnostics={},dispatch_overflow={},store_overflow=None)
                for row in legacy['requests'].values():row['quarantine_ids']=[]
                case.artifacts.path.write_text(json.dumps(legacy),encoding='utf-8')
                with self.assertRaises(storage.ArtifactUnavailable):case.artifacts._check_index()
                self.assertTrue(marker.is_set())
        with patch.object(storage,'atomic_json',replaced),self.assertRaises(storage.ArtifactUnavailable):action()
        self.assertTrue(case.artifacts.diagnostic_store.path.exists())
        landed=json.loads(case.artifacts.diagnostic_store.path.read_bytes())
        self.assertEqual(len(landed['diagnostics']),1)
        self.assertEqual(case.artifacts._data['requests'][audit['request_id']]['state'],'active')
        with self.assertRaises(storage.ArtifactDiagnosticsUnavailable):case.artifacts.diagnostic_store.report()

    def test_omitted_startup_request_is_reread_before_resume_pending_mark(self):
        values,_=self.action('resume');case,audit,*_=values
        extra=case.prepare(channel='peer')
        def changed():
            with case.service._boundary():
                return case.artifacts.set_attempt_state(extra['request_id'],extra['attempt_id'],'queued',{'state':'active','reason':None})
        result,other=self.pause(case,lambda:case.authority.recover_startup(limit=1),changed)
        self.assertEqual(other[0],'ok');self.assertEqual(result[0],'ok')
        row=case.artifacts.get_request(extra['request_id'])
        self.assertEqual((row['state'],row['reason']),('active',None))
        self.assertNotIn(extra['request_id'],result[1]['enqueue_repaired'])


if __name__=='__main__':
    unittest.main()
