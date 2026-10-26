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

    def test_run_without_artifact_policy_keeps_ordinary_stop(self):
        from tests import test_channel_import as fixture
        from pathlib import Path
        case=fixture.ChannelImportTests();case.setUp();self.addCleanup(case.doCleanups)
        case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
        session=case.sessions.create('planning','review',{'planner':'p','challenger':'c','synthesiser':'s'},'operator')
        result=case.engine.stop_session(session['id'])
        self.assertTrue(result['stop_id']);self.assertEqual(case.trigger.queue.records(),[])
