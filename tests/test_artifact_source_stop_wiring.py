"""Reduced20 ROOT behavioral reds for production source-Stop connection.
Uses real accepted service, queue, session and source packet fixtures.
"""
import unittest
from copy import deepcopy
import uuid
from unittest.mock import patch
import artifact_store
from tests import test_artifact_diagnostic_phases as phase_fixture


class ArtifactSourceStopWiringTests(unittest.TestCase):
    def fixture(self):
        owner=phase_fixture.ArtifactDiagnosticPhaseTests();self.addCleanup(owner.doCleanups)
        return owner.fixture(source=True)

    def test_engine_stop_cancels_mid_run_artifact_and_fences_claim(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        result=case.engine.stop_session(session['id'])
        self.assertIsNotNone(result['stop_id'])
        row=case.artifacts.get_request(audit['request_id'])
        self.assertEqual((row['state'],row['reason']),('cancelled','source_stopped'))
        transport=next((row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id']),None)
        self.assertIn(transport['state'],('cancelling','cancelled'))
        self.assertTrue(transport.get('cancellation_id') or transport.get('stop_id'))

    def test_explicit_stop_path_fences_source_once(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        stopped=case.sessions.stop_run(session['id'],'fixture Stop')
        case.trigger.queue.cancel_run(session['run_id'],stopped['stop_id'],fence_artifacts=True)
        row=case.artifacts.get_request(audit['request_id'])
        self.assertEqual((row['state'],row['reason']),('cancelled','source_stopped'))
        self.assertIn(next((row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id']),None)['state'],('cancelling','cancelled'))

    def test_stop_does_not_cancel_different_run_artifact_in_same_channel(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        case.sessions._event_update(session['id'],lambda row:row.update(state='interrupted'))
        other_session=case.sessions.create('planning','review',{'planner':'planner','challenger':'challenger',
            'synthesiser':'synthesiser'},'operator',input_text='Other source')
        other,packet=case.new_request(channel='review');request=uuid.uuid4().hex;ids=case.storage.request_ids(request)
        other.update(request_id=request,**{key:ids[key] for key in ('lineage_id','attempt_id','dispatch_id','brief_id')})
        source={'session_id':other_session['id'],'run_id':other_session['run_id'],
            'input_revision':other_session['input_revision'],'state_at_request':other_session['state']}
        packet.update(scope_kind='run_accepted_messages',source_run=source,
            input={'text':'Other source','input_revision':source['input_revision'],'source_document':None})
        other.update(source_run=source,scope=case.artifacts.put_packet(request,packet))
        case.authority.prepare_request(other,packet,request)
        case.engine.stop_session(session['id'])
        self.assertEqual(case.artifacts.get_request(other['request_id'])['state'],'queued')
        self.assertEqual(next(row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==other['dispatch_id'])['state'],'queued')
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'],'source_stopped')

    def test_reconcile_repairs_retained_artifacts_without_review_receipts(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        stopped=case.sessions.stop_run(session['id'],'Stop before reconciliation')
        with case.service._boundary():case.trigger.queue._reconcile()
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'],'source_stopped')
        records=case.trigger.queue.cancel_run(session['run_id'],stopped['stop_id'])
        self.assertNotIn(audit['dispatch_id'],[row['envelope']['dispatch_id'] for row in records])
        self.assertIn(audit['dispatch_id'],case.trigger.queue.artifact_stop_status(session['run_id'])['unconfirmed_dispatch_ids'])
        case.engine.reconcile_stops()
        case.engine.stop_status(session['id'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')

    def test_durable_state_precedes_fence_and_partial_failure_is_retryable(self):
        case,audit,instance,consumer,record,box,session=self.fixture();seen=[]
        def broken(row):
            saved=case.artifacts.get_request(audit['request_id'])
            seen.append((saved['state'],saved['reason'],case.engine._lock._is_owned(),case.catalog._lock._is_owned()))
            raise OSError('controlled fence failure')
        with patch.object(case.authority,'_fence',broken):result=case.engine.stop_session(session['id'])
        self.assertEqual(result['artifact_cancellation']['warning'],'transport_unconfirmed')
        self.assertEqual(seen,[('cancelled','source_stopped',True,True)])
        self.assertTrue(case.sessions.get(session['id'])['stop_id'])
        case.engine.stop_status(session['id'])
        retained=next(row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id'])
        self.assertEqual(retained['state'],'cancelling');self.assertTrue(retained['cancellation_id'])

    def test_held_artifact_owner_does_not_abort_stop_or_other_sessions(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        case.sessions._event_update(session['id'],lambda row:row.update(state='interrupted'))
        other=case.sessions.create('planning','review',{'planner':'p','challenger':'c','synthesiser':'s'},'operator')
        case.sessions.stop_run(other['id'],'other stopped run')
        case.artifacts.path.write_bytes(b'corrupt authoring index')
        try:result=case.engine.stop_session(session['id'])
        except artifact_store.ArtifactUnavailable:self.fail('Held artifact owner must not abort durable session Stop')
        self.assertTrue(result['stop_id'])
        self.assertEqual(result['artifact_cancellation']['warning'],'storage_unavailable')
        case.engine.reconcile_stops()
        self.assertEqual(case.sessions.get(other['id'])['state'],'stopped')

    def test_held_owner_allows_ordinary_claim_after_historical_stop(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        case.sessions.stop_run(session['id'],'historical Stop')
        other,_,_=case.launch_binding('api')
        envelope=deepcopy(next(row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id'])['envelope'])
        for key in list(envelope):
            if key=='purpose' or key.startswith('artifact_'):envelope.pop(key)
        envelope.update(dispatch_id=uuid.uuid4().hex,run_id=uuid.uuid4().hex,
            target_identity_id=other['identity_id'],target_agent=other['name'])
        case.trigger.queue._queue.enqueue(other,envelope)
        case.artifacts.path.write_bytes(b'corrupt authoring index')
        try:claimed=case.trigger.queue.claim(other,'ordinary-consumer')
        except artifact_store.ArtifactUnavailable:self.fail('Held artifact owner must not abort ordinary claim')
        self.assertEqual(claimed['envelope']['dispatch_id'],envelope['dispatch_id'])

    def test_historical_stops_never_scan_artifact_index_per_claim(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        runs=[dict(session,run_id=uuid.uuid4().hex,stop_id=uuid.uuid4().hex) for _ in range(40)]
        with patch.object(case.sessions,'list_all',return_value=runs),patch.object(case.artifacts,'channel_names',wraps=case.artifacts.channel_names) as scan:
            case.trigger.queue._reconcile();case.trigger.queue._reconcile()
        scan.assert_not_called()

    def test_retained_repair_budget_rotates_without_starving_later_requests(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        rows=[]
        for _ in range(101):
            row=deepcopy(next(row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id']))
            row['envelope']['artifact_request_id']=uuid.uuid4().hex;rows.append(row)
        batches=[]
        with patch.object(case.trigger.queue._queue,'records',return_value=rows),patch.object(case.authority,'fence_retained_source_requests',return_value=[]),patch.object(case.authority,'repair_cancel_fences',side_effect=lambda ids:batches.append(list(ids))):
            case.trigger.queue.repair_artifact_stops();case.trigger.queue.repair_artifact_stops()
        self.assertEqual([len(batch) for batch in batches],[100,100])
        self.assertEqual(len(set(batches[0]+batches[1])),101)

    def test_artifact_fences_are_separate_from_review_stop_outcome(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        case.engine.stop_session(session['id']);case.engine.reconcile_stops()
        status=case.engine.stop_status(session['id'])
        self.assertEqual(status['state'],'stopped')
        self.assertNotIn(audit['dispatch_id'],[row['dispatch_id'] for row in status['cancellation_receipts']])
        self.assertEqual(status['termination_offers'],[])
        self.assertIn(audit['dispatch_id'],status['artifact_cancellation']['unconfirmed_dispatch_ids'])

    def test_optional_retained_repair_respects_held_channel_startup(self):
        from channel_lifecycle import ChannelUnavailable
        case,audit,instance,consumer,record,box,session=self.fixture()
        with patch.object(case.trigger.queue,'_channel_policy',side_effect=ChannelUnavailable('held channel')):
            try:case.trigger.queue.repair_artifact_stops()
            except ChannelUnavailable:self.fail('Optional artifact repair must not abort held-channel startup')
            with self.assertRaises(ChannelUnavailable):case.trigger.queue.claim(instance,'owner')

    def test_no_artifact_stop_report_does_not_read_transport(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        with patch.object(case.trigger.queue._queue,'records',side_effect=AssertionError('no transport read')):
            status=case.trigger.queue.artifact_stop_status(session['run_id'])
        self.assertEqual(status,{'warning':None,'unconfirmed_dispatch_ids':[]})

    def test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        case.trigger.queue.bind_artifact_policy(lambda:None)
        result=case.engine.stop_session(session['id'])
        self.assertTrue(result['stop_id']);self.assertIsNone(result['artifact_cancellation']['warning'])
        case.trigger.queue._reconcile()
        self.assertIsNone(case.engine.stop_status(session['id'])['artifact_cancellation']['warning'])
        from dispatch_queue import QueueBusy
        with self.assertRaises(QueueBusy):case.trigger.queue.claim(instance,'different-consumer')
        other,_,_=case.launch_binding('api')
        self.assertIsNone(case.trigger.queue.claim(other,'ordinary-consumer'))

    def test_all_artifact_policy_errors_are_contained_after_durable_stop(self):
        for error in (artifact_store.ArtifactConflict('conflict'),artifact_store.ArtifactValidationError('invalid'),
                      KeyError('session_id'),RuntimeError('owner read failure')):
            with self.subTest(error=type(error).__name__):
                case,audit,instance,consumer,record,box,session=self.fixture()
                with patch.object(case.authority,'fence_source_requests',side_effect=error):
                    try:result=case.engine.stop_session(session['id'])
                    except Exception as escaped:self.fail('Artifact fault escaped durable Stop: '+type(escaped).__name__)
                self.assertEqual(result['artifact_cancellation']['warning'],'artifact_fence_failed')
                with patch.object(case.authority,'fence_retained_source_requests',side_effect=error):
                    try:
                        case.trigger.queue._reconcile();case.engine.stop_status(session['id'])
                    except Exception as escaped:self.fail('Artifact fault escaped retained repair: '+type(escaped).__name__)
                self.assertTrue(case.sessions.get(session['id'])['stop_id'])

    def test_queued_stopped_source_never_claims_even_when_repair_fails(self):
        from tests.test_artifact_operator_core import ArtifactOperatorCoreTests,accepted_source
        from artifact_operator import ArtifactOperator
        owner=ArtifactOperatorCoreTests();self.addCleanup(owner.doCleanups);case=owner.context()
        session,_,_=accepted_source(case,state='active')
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'report'}
        ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages).create(intent)
        with patch.object(case.authority,'fence_source_requests',side_effect=artifact_store.ArtifactUnavailable('held')):
            case.engine.stop_session(session['id'])
        with patch.object(case.authority,'fence_retained_source_requests',side_effect=RuntimeError('repair failed')):
            self.assertIsNone(case.trigger.queue.claim(case.instance,'late-worker'))
        self.assertEqual(case.artifacts.get_request(intent['request_id'])['state'],'queued')
        self.assertIsNone(case.trigger.queue.claim(case.instance,'late-worker'))
        self.assertEqual(case.artifacts.get_request(intent['request_id'])['reason'],'source_stopped')

    def test_prepared_without_transport_is_ineligible_after_source_stop(self):
        from tests.test_artifact_operator_core import ArtifactOperatorCoreTests,accepted_source
        from artifact_operator import ArtifactOperator,ArtifactOperatorError
        owner=ArtifactOperatorCoreTests();self.addCleanup(owner.doCleanups);case=owner.context()
        session,_,_=accepted_source(case,state='active')
        intent={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'report'}
        def reserved(audit,packet,identifier):
            case.artifacts.reserve_request(audit,identifier);raise OSError('crash before enqueue')
        operator=ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        with patch.object(case.authority,'prepare_request',reserved),self.assertRaises(ArtifactOperatorError):operator.create(intent)
        with patch.object(case.authority,'fence_source_requests',side_effect=artifact_store.ArtifactUnavailable('held')):
            case.engine.stop_session(session['id'])
        self.assertEqual(case.artifacts.get_request(intent['request_id'])['state'],'prepared')
        self.assertEqual(case.authority.eligible_dispatch_ids(case.instance),set())
        self.assertIsNone(case.trigger.queue.claim(case.instance,'late-worker'))
        from queue_coordinator import CoordinatedQueue
        restored=CoordinatedQueue(case.trigger.queue._queue,case.sessions,case.engine._lock)
        restored.bind_channel_policy(lambda:case.service);restored.bind_artifact_policy(lambda:case.authority)
        case.trigger.queue=restored
        case.engine.stop_session(session['id'])
        self.assertEqual(case.artifacts.get_request(intent['request_id'])['reason'],'source_stopped')
        self.assertEqual(case.artifacts.get_request(intent['request_id'])['state'],'cancelled')

    def test_restart_retained_repair_uses_real_source_fences_and_shrinking_candidates(self):
        from queue_coordinator import CoordinatedQueue
        case,audit,instance,consumer,record,box,session=self.fixture()
        with patch.object(case.authority,'fence_source_requests',side_effect=artifact_store.ArtifactUnavailable('transient owner hold')):
            case.engine.stop_session(session['id'])
        restored=CoordinatedQueue(case.trigger.queue._queue,case.sessions,case.engine._lock)
        restored.bind_channel_policy(lambda:case.service);restored.bind_artifact_policy(lambda:case.authority)
        self.assertEqual(restored._artifact_repair_cursor,0)
        with patch.object(case.artifacts,'channel_names',side_effect=AssertionError('retained repair must not scan index channels')):
            restored.repair_artifact_stops();restored.repair_artifact_stops()
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'],'source_stopped')
        transport=case.trigger.queue.owned(instance,audit['dispatch_id'])
        self.assertEqual(transport['state'],'cancelling');self.assertTrue(transport['cancellation_id'])
        self.assertIn(audit['dispatch_id'],restored.artifact_stop_status(session['run_id'])['unconfirmed_dispatch_ids'])
        with patch.object(case.authority,'fence_retained_source_requests',side_effect=RuntimeError('unrelated artifact failure')):
            status=case.engine.stop_status(session['id'])
        self.assertEqual(status['state'],'stopped')
        from turn_events import EventConflict
        with self.assertRaises(EventConflict):case.engine.terminate_seat(session['id'],audit['dispatch_id'],'not-a-review-launch',case.manager)

    def test_none_policy_enqueue_uses_typed_conflict(self):
        from dispatch_queue import QueueConflict
        case,audit,instance,consumer,record,box,session=self.fixture()
        envelope=case.trigger.queue.owned(instance,audit['dispatch_id'])['envelope']
        case.trigger.queue.bind_artifact_policy(lambda:None)
        try:case.trigger.queue.enqueue(instance,envelope)
        except QueueConflict:pass
        except Exception as error:self.fail('Missing policy must refuse with QueueConflict: '+type(error).__name__)
        else:self.fail('Missing artifact policy must refuse enqueue')

    def test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow(self):
        for all_pending in (False,True):
            with self.subTest(all_pending=all_pending):
                case,audit,instance,consumer,record,box,session=self.fixture();queue=case.trigger.queue
                ids=[uuid.uuid4().hex for _ in range(129)]
                for index,run in enumerate(ids[:128]):
                    queue._remember_artifact_stop(run,{'dispatch_ids':[] if index==1 and not all_pending else [uuid.uuid4().hex],
                        'warning':None if index==1 and not all_pending else 'transport_unconfirmed', 'confirmed':index==0})
                queue._remember_artifact_stop(ids[-1],{'dispatch_ids':[uuid.uuid4().hex],'warning':'transport_unconfirmed'})
                self.assertEqual(len(queue._artifact_stop_reports),128)
                self.assertIn(ids[-1],queue._artifact_stop_reports)
                if all_pending:self.assertEqual(queue.artifact_stop_status(ids[0])['warning'],'unconfirmed_overflow')
                else:self.assertIn(ids[0],queue._artifact_stop_reports);self.assertNotIn(ids[1],queue._artifact_stop_reports)

    def test_optional_artifact_inspection_failure_does_not_abort_review_work(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        case.engine.stop_session(session['id']);other,_,_=case.launch_binding('api')
        with patch.object(case.trigger.queue._queue,'records',side_effect=OSError('inspection unavailable')):
            try:
                self.assertIsNone(case.trigger.queue.claim(other,'ordinary-worker'))
                status=case.engine.stop_status(session['id'])
            except OSError:self.fail('Optional artifact inspection must not abort review work')
        self.assertEqual(status['artifact_cancellation']['warning'],'storage_unavailable')
        self.assertEqual(status['state'],'stopped')

    def test_nested_artifact_fault_sites_are_contained(self):
        for site in ('getter','repair_cancel_fences','eligible_dispatch_ids','session_get'):
            with self.subTest(site=site):
                case,audit,instance,consumer,record,box,session=self.fixture();other,_,_=case.launch_binding('api')
                case.sessions.stop_run(session['id'],'durable source Stop')
                target,name=(case.sessions,'get') if site=='session_get' else (case.authority,site)
                if site=='getter':target,name=case.trigger.queue,'_artifact_policy'
                with patch.object(target,name,side_effect=RuntimeError('controlled '+site)) as fault:
                    try:self.assertIsNone(case.trigger.queue.claim(other,'ordinary-worker'))
                    except Exception as error:self.fail('Artifact fault escaped '+site+': '+type(error).__name__)
                fault.assert_called()

    def test_retained_real_rotation_over_one_hundred_rows_and_restart(self):
        from queue_coordinator import CoordinatedQueue
        case,audit,instance,consumer,record,box,session=self.fixture()
        packet=case.artifacts.get_packet(audit['scope']['packet_id'])
        requests=[audit['request_id']]
        for _ in range(101):
            request=uuid.uuid4().hex;ids=case.storage.request_ids(request);item=deepcopy(audit)
            item.update(request_id=request,**{key:ids[key] for key in ('lineage_id','attempt_id','dispatch_id','brief_id')})
            item['scope']=case.artifacts.put_packet(request,packet)
            case.authority.prepare_request(item,packet,request);requests.append(request)
        case.sessions.stop_run(session['id'],'durable Stop before artifact fence')
        def coordinator():
            value=CoordinatedQueue(case.trigger.queue._queue,case.sessions,case.engine._lock)
            value.bind_channel_policy(lambda:case.service);value.bind_artifact_policy(lambda:case.authority);return value
        restored=coordinator()
        with patch.object(case.authority,'fence_retained_source_requests',wraps=case.authority.fence_retained_source_requests) as real:
            restored.repair_artifact_stops()
            self.assertEqual(len(real.call_args.args[0]),100)
            self.assertEqual(sum(case.artifacts.get_request(r)['state']=='cancelled' for r in requests),100)
            restarted=coordinator();self.assertEqual(restarted._artifact_repair_cursor,0)
            restarted.repair_artifact_stops()
            self.assertEqual(len(real.call_args.args[0]),2)
        self.assertTrue(all(case.artifacts.get_request(r)['reason']=='source_stopped' for r in requests))

    def test_held_artifact_owner_does_not_block_owned_review_termination(self):
        from tests.test_session_stop import SessionStopTests
        from types import SimpleNamespace
        owner=SessionStopTests();owner.setUp();self.addCleanup(owner.doCleanups)
        owner.claim();owner.queue.bind_artifact_policy(lambda:None)
        owner.engine.stop_session(owner.session_id)
        with patch.object(owner.queue,'_artifact_policy',side_effect=artifact_store.ArtifactUnavailable('held owner')):
            result=owner.engine.terminate_seat(owner.session_id,owner.invocation['dispatch_id'],'fixture-launch',
                SimpleNamespace(terminate_owned=lambda identity,attempt:{'local_ended':True}))
        self.assertEqual(result['state'],'stopped')
        self.assertEqual(owner.queue.owned(owner.owner,owner.invocation['dispatch_id'])['state'],'cancelled')

    def test_repeated_stop_preserves_unconfirmed_ids_until_transport_terminal(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        with patch.object(case.authority,'_fence',side_effect=artifact_store.ArtifactUnavailable('held fence')):
            first=case.engine.stop_session(session['id'])
        self.assertEqual(first['artifact_cancellation']['warning'],'storage_unavailable')
        self.assertIn(audit['dispatch_id'],first['artifact_cancellation']['unconfirmed_dispatch_ids'])
        # A successful incremental fence response must not erase prior uncertainty.
        with patch.object(case.authority,'fence_source_requests',return_value={'request_ids':[],'dispatch_ids':[]}):
            second=case.engine.stop_session(session['id'])
        self.assertEqual(first['stop_id'],second['stop_id'])
        self.assertIn(audit['dispatch_id'],second['artifact_cancellation']['unconfirmed_dispatch_ids'])
        self.assertIsNotNone(second['artifact_cancellation']['warning'])
        case.trigger.queue.cancel_dispatch(audit['dispatch_id'],uuid.uuid4().hex)
        case.trigger.queue.cancellation_receipt(instance,audit['dispatch_id'],consumer,'local_ended')
        final=case.trigger.queue.artifact_stop_status(session['run_id'])
        self.assertEqual(final,{'warning':None,'unconfirmed_dispatch_ids':[]})

    def test_run_without_artifact_policy_keeps_ordinary_stop(self):
        from tests import test_channel_import as fixture
        from pathlib import Path
        case=fixture.ChannelImportTests();case.setUp();self.addCleanup(case.doCleanups)
        case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
        session=case.sessions.create('planning','review',{'planner':'p','challenger':'c','synthesiser':'s'},'operator')
        result=case.engine.stop_session(session['id'])
        self.assertTrue(result['stop_id']);self.assertEqual(case.trigger.queue.records(),[])
