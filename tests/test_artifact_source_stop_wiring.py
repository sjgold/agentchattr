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

    def test_shared_cancel_run_path_also_covers_reconciliation(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        stopped=case.sessions.stop_run(session['id'],'fixture Stop')
        case.trigger.queue.cancel_run(session['run_id'],stopped['stop_id'])
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

    def test_reconcile_uses_shared_cancel_and_reports_affected_records(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        stopped=case.sessions.stop_run(session['id'],'Stop before reconciliation')
        with case.service._boundary():case.trigger.queue._reconcile()
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'],'source_stopped')
        records=case.trigger.queue.cancel_run(session['run_id'],stopped['stop_id'])
        self.assertIn(audit['dispatch_id'],[row['envelope']['dispatch_id'] for row in records])
        case.engine.reconcile_stops()
        case.engine.stop_status(session['id'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')

    def test_durable_state_precedes_fence_and_partial_failure_is_retryable(self):
        case,audit,instance,consumer,record,box,session=self.fixture();seen=[]
        def broken(row):
            saved=case.artifacts.get_request(audit['request_id'])
            seen.append((saved['state'],saved['reason'],case.engine._lock._is_owned(),case.catalog._lock._is_owned()))
            raise OSError('controlled fence failure')
        with patch.object(case.authority,'_fence',broken),self.assertRaises(artifact_store.ArtifactUnavailable):case.engine.stop_session(session['id'])
        self.assertEqual(seen,[('cancelled','source_stopped',True,True)])
        self.assertTrue(case.sessions.get(session['id'])['stop_id'])
        case.engine.stop_status(session['id'])
        retained=next(row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==audit['dispatch_id'])
        self.assertEqual(retained['state'],'cancelling');self.assertTrue(retained['cancellation_id'])

    def test_run_without_artifact_policy_keeps_ordinary_stop(self):
        from tests import test_channel_import as fixture
        from pathlib import Path
        case=fixture.ChannelImportTests();case.setUp();self.addCleanup(case.doCleanups)
        case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
        session=case.sessions.create('planning','review',{'planner':'p','challenger':'c','synthesiser':'s'},'operator')
        result=case.engine.stop_session(session['id'])
        self.assertTrue(result['stop_id']);self.assertEqual(case.trigger.queue.records(),[])
