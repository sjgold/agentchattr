"""Reduced20 ROOT behavioral reds for production source-Stop connection.
Uses real accepted service, queue, session and source packet fixtures.
"""
import unittest
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

    def test_stop_does_not_cancel_unrelated_artifact_source(self):
        case,audit,instance,consumer,record,box,session=self.fixture()
        other=case.prepare(channel='peer')
        case.engine.stop_session(session['id'])
        self.assertEqual(case.artifacts.get_request(other['request_id'])['state'],'queued')
        self.assertEqual(next(row for row in case.trigger.queue.records() if row['envelope']['dispatch_id']==other['dispatch_id'])['state'],'queued')
