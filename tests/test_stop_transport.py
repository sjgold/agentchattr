"""Cancellation receipts reach owners without injecting another CLI prompt."""
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from queue_client import CliConsumer


class StopTransportTests(unittest.TestCase):
    def test_legacy_record_returns_explicit_conflict_without_inventing_cancellation(self):
        from tests.test_session_stop import SessionStopTests
        fixture = SessionStopTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.sessions._sessions[0].pop('completion_protocol')
        api = FastAPI()
        api.add_api_route('/api/sessions/{session_id}/stop', app.end_session, methods=['POST'])
        with patch.object(app, 'session_engine', fixture.engine):
            response = TestClient(api).post('/api/sessions/1/stop')
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('stop_id', fixture.current())

    def test_stop_cannot_interleave_start_between_run_creation_and_first_dispatch(self):
        from tests.test_session_stop import SessionStopTests
        fixture = SessionStopTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        reached, release = threading.Event(), threading.Event()
        original = fixture.engine._trigger_current
        def gated(session):
            reached.set()
            if not release.wait(2):
                raise AssertionError('Start fixture gate timed out')
            return original(session)
        with patch.object(fixture.engine, '_trigger_current', side_effect=gated), ThreadPoolExecutor(max_workers=2) as pool:
            starting = pool.submit(fixture.engine.start_session, 'review', 'start-race',
                                   {'reviewer': 'codex', 'editor': 'claude'}, 'human')
            self.assertTrue(reached.wait(1))
            session_id = fixture.sessions.list_all()[-1]['id']
            stopping = pool.submit(fixture.engine.stop_session, session_id)
            try:
                with self.assertRaises(TimeoutError):
                    stopping.result(timeout=.05)
            finally:
                release.set()
            self.assertIsNotNone(starting.result(timeout=2))
            self.assertFalse(stopping.result(timeout=2)['dispatch_eligible'])

    def test_stopped_review_evidence_remains_visible_after_channel_refresh(self):
        from tests.test_session_stop import SessionStopTests
        fixture = SessionStopTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.engine.stop_session(fixture.session_id)
        self.assertEqual(fixture.engine.get_active('general')['state'], 'stopping')
        fixture.engine.reconcile_stops()
        self.assertEqual(fixture.engine.get_active('general')['state'], 'stopped')

    def test_cancelling_cli_reports_unsupported_without_injecting_even_on_first_poll(self):
        client, inject = Mock(), Mock()
        client.claim.return_value = {'state': 'cancelling', 'envelope': {'dispatch_id': 'a' * 32}}
        watcher = CliConsumer(client, inject, lambda envelope: 'must not inject')
        watcher.poll()
        watcher.poll()
        inject.assert_not_called()
        client.cancellation_receipt.assert_called_with('a' * 32, 'unsupported')
        client.release.assert_not_called()

    def test_http_receipt_is_bound_to_live_bearer_and_consumer(self):
        from tests.test_session_stop import SessionStopTests
        fixture = SessionStopTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.claim('worker')
        fixture.engine.stop_session(fixture.session_id)
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-test', {'server': {'port': 18300}})
        api.add_api_route('/api/queue/{operation}', app.dispatch_operation, methods=['POST'])
        client = TestClient(api, client=('127.0.0.1', 40000))
        body = {'consumer_id': 'worker', 'dispatch_id': fixture.invocation['dispatch_id'], 'status': 'local_ended'}
        with patch.object(app, 'registry', fixture.registry), patch.object(app, 'agents', fixture.trigger):
            peer = {'Authorization': 'Bearer ' + fixture.peer['token']}
            owner = {'Authorization': 'Bearer ' + fixture.owner['token']}
            self.assertEqual(client.post('/api/queue/cancel', json=body, headers=peer).status_code, 403)
            self.assertEqual(client.post('/api/queue/cancel', json={**body, 'consumer_id': 'stale'}, headers=owner).status_code, 403)
            result = client.post('/api/queue/cancel', json=body, headers=owner)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['dispatch']['state'], 'cancelled')

    def test_operator_stop_status_and_confirmed_termination_have_distinct_authority(self):
        from tests.test_session_stop import SessionStopTests
        fixture = SessionStopTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.claim('worker')
        manager = Mock()
        manager.termination_offer.return_value = {'launch_attempt': 'launch-one', 'seat_name': 'CLI', 'impact': 'Persistent context ends.'}
        manager.terminate_owned.return_value = {'local_ended': True, 'remote_compute': 'unverified'}
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-test', {'server': {'port': 18300}})
        api.add_api_route('/api/sessions/{session_id}/stop', app.end_session, methods=['POST'])
        api.add_api_route('/api/sessions/{session_id}/stop-status', app.session_stop_status, methods=['GET'])
        api.add_api_route('/api/sessions/{session_id}/terminate-seat', app.terminate_session_seat, methods=['POST'])
        client = TestClient(api, client=('127.0.0.1', 40000))
        owner = {'Authorization': 'Bearer ' + fixture.owner['token']}
        operator = {'x-session-token': 'operator-test'}
        with patch.object(app, 'registry', fixture.registry), patch.object(app, 'session_store', fixture.sessions), \
             patch.object(app, 'session_engine', fixture.engine), patch.object(app, 'agents', fixture.trigger), \
             patch.object(app, 'api_seat_manager', manager):
            self.assertEqual(client.post('/api/sessions/1/stop', headers=owner).status_code, 403)
            self.assertEqual(client.post('/api/sessions/1/stop', headers=operator).status_code, 200)
            status = client.get('/api/sessions/1/stop-status', headers=operator)
            self.assertEqual(status.status_code, 200)
            self.assertFalse(status.json()['dispatch_eligible'])
            body = {'dispatch_id': fixture.invocation['dispatch_id'], 'launch_attempt': 'launch-one'}
            self.assertEqual(client.post('/api/sessions/1/terminate-seat', json=body, headers=operator).status_code, 400)
            manager.terminate_owned.assert_not_called()
            self.assertEqual(client.post('/api/sessions/1/terminate-seat', json={**body, 'confirm': True}, headers=owner).status_code, 403)
            done = client.post('/api/sessions/1/terminate-seat', json={**body, 'confirm': True}, headers=operator)
            self.assertEqual(done.status_code, 200)
            self.assertEqual(done.json()['state'], 'stopped')
            manager.terminate_owned.assert_called_once_with(fixture.owner['identity_id'], 'launch-one')


if __name__ == '__main__':
    unittest.main()
