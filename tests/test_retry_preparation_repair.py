"""Explicit retry preparation repair preserves the reserved generation attempt."""
from copy import deepcopy
import time
import unittest
from unittest.mock import patch
import uuid

from api_seats import atomic_json
from turn_events import EventConflict


class RetryPreparationRepairTests(unittest.TestCase):
    def test_repair_route_is_operator_only_and_deduplicates_the_exact_context(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import app
        f, failed = self.fixture()
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-test', {'server': {'port': 18300}})
        api.add_api_route('/api/sessions/{session_id}/repair-retry', app.repair_session_retry, methods=['POST'])
        client = TestClient(api, client=('127.0.0.1', 40000))
        body = {'request_id': f.request_id, 'preparation_attempt': failed['id']}
        path = f'/api/sessions/{f.session_id}/repair-retry'
        operator = {'X-Session-Token': 'operator-test'}
        with patch.object(app, 'session_engine', f.engine), patch.object(app, 'registry', f.registry):
            self.assertEqual(client.post(path, json=body, headers={'Authorization': 'Bearer ' + f.api['token']}).status_code, 403)
            self.assertEqual(client.post(path, json={**body, 'content': 'not recovery'}, headers=operator).status_code, 400)
            first = client.post(path, json=body, headers=operator)
            self.assertEqual(first.status_code, 200)
            count = len(f.processes)
            second = client.post(path, json=body, headers=operator)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(len(f.processes), count)
            self.assertEqual(second.json()['pending_retry']['new_attempt_id'], first.json()['pending_retry']['new_attempt_id'])

    def test_unchanged_starting_context_does_not_rewrite_and_wake_monitor_forever(self):
        from tests.test_managed_turn_retry import ManagedTurnRetryTests
        f = ManagedTurnRetryTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.prove_exit_on_wait()
        f.retry(f.confirm())
        with patch.object(f.sessions, '_save', wraps=f.sessions._save) as save:
            f.engine.monitor_turns(now=f.now + .1)
            f.engine.monitor_turns(now=f.now + .2)
        self.assertEqual(save.call_count, 0)

    def fixture(self, *, child_proof=True, no_spawn=False):
        from tests.test_managed_turn_retry import ManagedTurnRetryTests
        f = ManagedTurnRetryTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.prove_exit_on_wait()
        if no_spawn:
            with patch('api_seat_runtime.subprocess.Popen', side_effect=OSError('fixture spawn failure')):
                f.retry(f.confirm())
        else:
            f.retry(f.confirm())
        pending = f.current()['pending_retry']
        attempt = f.manager.attempts[pending['context']['key']]
        if not no_spawn:
            attempt['process'].poll.return_value = 23
            attempt['process'].returncode = 23
            receipt = {'attempt': attempt['id'], 'state': 'failed', 'authentication': 'unknown',
                       'adapter_connected': False, 'updated_at': time.time()}
            if child_proof:
                receipt['child_exit_code'] = 23
            atomic_json(attempt['receipt'], receipt)
            f.engine.monitor_turns(now=f.now + .1)
        return f, attempt

    def test_explicit_repair_after_natural_exit_reuses_reserved_turn_attempt(self):
        f, failed = self.fixture()
        reserved = deepcopy(f.current()['pending_retry'])
        original_source = deepcopy(f.current()['input_snapshot'])
        count = len(f.processes)
        f.engine.repair_retry(f.session_id, f.request_id, failed['id'], now=f.now + .2)
        repaired = f.current()['pending_retry']
        self.assertEqual(repaired['new_attempt_id'], reserved['new_attempt_id'])
        self.assertNotEqual(repaired['context']['launch_attempt'], failed['id'])
        self.assertEqual(len(f.processes), count + 1)
        f.engine.repair_retry(f.session_id, f.request_id, failed['id'], now=f.now + .3)
        self.assertEqual(len(f.processes), count + 1)
        self.assertEqual(len(f.current()['preparation_history']), 1)
        f.fresh_ready()
        f.engine.monitor_turns(now=f.now + .4)
        current = f.current()
        self.assertEqual(current['state'], 'waiting')
        self.assertEqual(current['active_invocation']['attempt_id'], reserved['new_attempt_id'])
        self.assertEqual(current['input_snapshot'], original_source)
        self.assertEqual(len(current['admitted_events']), 1)
        self.assertEqual(current['participant_bindings']['editor']['launch_provenance']['effective']['seat']['model'], 'cli-original')

    def test_dead_worker_without_matching_child_proof_stays_blocked(self):
        f, failed = self.fixture(child_proof=False)
        count = len(f.processes)
        result = f.engine.repair_retry(f.session_id, f.request_id, failed['id'], now=f.now + .2)
        self.assertEqual(result['state'], 'retrying')
        self.assertEqual(result['pending_retry']['status'], 'preparation_failed')
        self.assertEqual(len(f.processes), count)
        self.assertEqual(result['active_invocation']['attempt_id'], f.original['attempt_id'])

    def test_popen_failure_can_be_repaired_without_a_fabricated_exit_receipt(self):
        f, failed = self.fixture(no_spawn=True)
        self.assertIsNone(failed['process'])
        count = len(f.processes)
        result = f.engine.repair_retry(f.session_id, f.request_id, failed['id'], now=f.now + .2)
        self.assertEqual(result['pending_retry']['context']['state'], 'starting')
        self.assertEqual(len(f.processes), count + 1)

    def test_wrong_pending_context_and_permanent_stop_cannot_repair(self):
        f, failed = self.fixture()
        before = f.current()
        for request, preparation in ((uuid.uuid4().hex, failed['id']), (f.request_id, uuid.uuid4().hex)):
            with self.subTest(request=request, preparation=preparation), self.assertRaises(EventConflict):
                f.engine.repair_retry(f.session_id, request, preparation)
        self.assertEqual(f.current(), before)
        f.engine.stop_session(f.session_id)
        with self.assertRaises(EventConflict):
            f.engine.repair_retry(f.session_id, f.request_id, failed['id'])
