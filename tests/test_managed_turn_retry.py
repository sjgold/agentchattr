"""Real coordinator/store/queue retry orchestration with owned process doubles."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import SeatStore, atomic_json
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry


from agents import AgentTrigger
from session_store import SessionStore
from session_engine import SessionEngine
from store import MessageStore
from turn_events import EventConflict

class ManagedTurnRetryTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.providers = {
            'fake-api': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1',
                         'system_prompt': 'Original API instruction', 'temperature': .7},
            'fake-cli': {'command': sys.executable, 'cwd': str(self.root),
                         'cli_args': ['fixture-original'], 'cli_model_args': ['--model', '{model}'],
                         'cli_reasoning_args': ['--effort', '{reasoning}'], 'reasoning_efforts': ['high'],
                         'mcp_inject': 'env', 'mcp_env_var': 'RESTART_TEST_SETTINGS'}}
        common = {'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        self.package = {'id': 'team', 'name': 'Team', 'seats': [
            dict(common, id='api', name='API', adapter='openai-compatible', provider='fake-api', model='api-original', secret_ref='RESTART_TEST_KEY'),
            dict(common, id='cli', name='CLI', adapter='cli', provider='fake-cli', model='cli-original', reasoning='high')]}
        self.store = SeatStore(self.root, self.providers)
        self.store.save(self.package)
        self.registry = RuntimeRegistry(str(self.root))
        self.manager = SeatManager(ROOT, {'server': {'port': 18300}}, self.store, self.registry,
                                   startup_timeout=5, monitor=False)
        self.processes = []
        def spawn(*args, **kwargs):
            process = Mock()
            process.poll.return_value = None
            process.returncode = None
            def ended(*args, **kwargs):
                process.poll.return_value = 0
                process.returncode = 0
                return 0
            process.wait.side_effect = ended
            process.terminate.side_effect = ended
            self.processes.append(process)
            return process
        self.environment = patch.dict(os.environ, {'RESTART_TEST_KEY': 'credential-value-test-only'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.patcher = patch('api_seat_runtime.subprocess.Popen', side_effect=spawn)
        self.spawn = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.manager.shutdown)

        self.sessions = SessionStore(str(self.root / 'session_runs.json'))
        self.sessions.save_custom_template({'id': 'review', 'name': 'Review', 'roles': ['reviewer', 'editor'],
            'phases': [{'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Read source.'},
                       {'name': 'Edit', 'participants': ['editor'], 'prompt': 'Edit source.', 'is_output': True}]})
        self.api, self.api_launch = self.ready('api')
        self.cli, self.cli_launch = self.ready('cli')
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry,
            seat_manager=self.manager, recovery_policy={'ack_timeout': 5, 'response_timeout': 10, 'monitor_interval': 1})
        self.queue = self.trigger.queue
        started = self.engine.start_session('review', 'general',
            {'reviewer': self.api['name'], 'editor': self.cli['name']}, 'operator',
            input_text='Exact café source\r\nkept across same-turn retry.')
        self.session_id = started['id']
        first = started['active_invocation']
        self.queue.claim(self.api, 'api-worker')
        self.queue.acknowledge(self.api, first['dispatch_id'], 'api-worker')
        self.engine.admit_event(first['brief_id'], 'final', 'Accepted API phase result', self.api)
        self.queue.release(self.api, first['dispatch_id'], 'api-worker')
        self.original = deepcopy(self.current()['active_invocation'])
        self.queue.claim(self.cli, 'cli-worker')
        self.queue.acknowledge(self.cli, self.original['dispatch_id'], 'cli-worker')
        self.now = time.time() + 11
        self.engine.monitor_turns(now=self.now)
        self.assertEqual(self.current()['state'], 'stalled')
        self.checkpoint = self.current()['turn_recovery']['checkpoint_id']
        self.request_id = uuid.uuid4().hex

    def ready(self, seat_id):
        launched = self.manager.launch('team', seat_id)
        attempt = self.manager.attempts['team/' + seat_id]
        instance = self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': launched['attempt'], 'state': 'ready',
            'name': instance['name'], 'adapter_connected': True, 'authentication': 'unknown',
            'confirmed_model': None, 'updated_at': time.time()})
        self.assertEqual(self.manager.inspect('team', seat_id)['state'], 'ready')
        return instance, launched

    def current(self):
        return self.sessions.get(self.session_id)

    def records(self):
        return json.loads((self.root / 'queue/ledger.json').read_text('utf-8'))['records']

    def retry(self, confirmation):
        return self.engine.retry_turn(self.session_id, self.checkpoint, self.original['attempt_id'],
            self.request_id, confirmation=confirmation, now=self.now)

    def confirm(self):
        return {'launch_attempt': self.cli_launch['attempt'], 'confirm': True}

    def prove_exit_on_wait(self):
        old = self.manager.attempts['team/cli']
        def ended(timeout=None):
            atomic_json(old['receipt'], {'attempt': old['id'], 'state': 'stopped',
                'authentication': 'unknown', 'adapter_connected': False,
                'child_exit_code': 0, 'updated_at': time.time()})
            old['process'].poll.return_value = 0
            old['process'].returncode = 0
            return 0
        old['process'].wait.side_effect = ended
        return old

    def fresh_ready(self):
        context = self.current()['pending_retry']['context']
        attempt = self.manager.attempts[context['key']]
        instance = self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready',
            'name': instance['name'], 'adapter_connected': True,
            'authentication': 'unknown', 'updated_at': time.time()})
        return instance, attempt

    def test_confirmed_cli_retry_fences_then_waits_for_new_actual_ready_identity(self):
        old = self.prove_exit_on_wait()
        prior = deepcopy(self.current()['admitted_events'])
        source = deepcopy(self.current()['input_snapshot'])
        self.package['seats'][1]['model'] = 'edited-model-not-authorized'
        self.store.providers['fake-cli'].update(cli_args=['edited-args'], cwd=str(ROOT),
                                               mcp_env_var='EDITED_SETTINGS')
        self.manager.save(self.package)
        self.retry(self.confirm())
        state = self.current()
        self.assertEqual(state['state'], 'retrying')
        self.assertEqual(state['pending_retry']['context']['state'], 'starting')
        self.assertEqual(len(self.processes), 3)
        self.assertEqual(len(self.records()), 2)
        self.assertEqual(self.queue.owned(self.cli, self.original['dispatch_id'])['state'], 'cancelled')
        self.assertTrue(any(x['attempt_id'] == self.original['attempt_id'] for x in state['superseded_attempts']))
        self.assertEqual(state['admitted_events'], prior)
        self.assertEqual(state['input_snapshot'], source)
        self.processes[0].wait.assert_not_called()
        self.assertEqual(self.manager.inspect('team', 'api')['attempt'], self.api_launch['attempt'])
        fresh_instance, fresh_launch = self.fresh_ready()
        self.engine.monitor_turns(now=self.now + .1)
        state = self.current()
        new = state['active_invocation']
        for field in ('brief_id', 'attempt_id', 'dispatch_id'):
            self.assertNotEqual(new[field], self.original[field])
        for field in ('run_id', 'turn_id', 'input_revision'):
            self.assertEqual(new[field], self.original[field])
        self.assertEqual(new['expected_identity_id'], fresh_instance['identity_id'])
        self.assertEqual(state['participant_bindings']['editor']['identity_id'], fresh_instance['identity_id'])
        provenance = state['participant_bindings']['editor']['launch_provenance']
        self.assertEqual(provenance['launch_attempt'], fresh_launch['id'])
        self.assertEqual(provenance['effective']['seat']['model'], 'cli-original')
        snapshot = json.loads(fresh_launch['snapshot'].read_text('utf-8'))
        self.assertEqual(snapshot['seat']['reasoning'], 'high')
        self.assertEqual(snapshot['provider']['cli_args'], ['fixture-original'])
        self.assertEqual(snapshot['provider']['cwd'], str(self.root.resolve()))
        self.assertEqual(snapshot['provider']['mcp_env_var'], 'RESTART_TEST_SETTINGS')
        self.assertEqual(state['admitted_events'], prior)
        self.assertEqual(state['input_snapshot'], source)
        self.assertEqual(len(self.records()), 3)
        delivered = self.queue.claim(fresh_instance, 'new-cli-worker')
        self.assertEqual(delivered['envelope']['dispatch_id'], new['dispatch_id'])

    def test_missing_stale_or_nonliteral_confirmation_preserves_fence_queue_and_processes(self):
        before = deepcopy(self.current())
        disk = (self.root / 'session_runs.json').read_bytes()
        queue_disk = (self.root / 'queue/ledger.json').read_bytes()
        for confirmation in (None, {'confirm': True, 'launch_attempt': uuid.uuid4().hex},
                             {'confirm': 1, 'launch_attempt': self.cli_launch['attempt']}):
            with self.subTest(confirmation=confirmation), self.assertRaises(EventConflict):
                self.retry(confirmation)
            self.assertEqual(self.current(), before)
            self.assertEqual((self.root / 'session_runs.json').read_bytes(), disk)
            self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue_disk)
            self.assertEqual(len(self.processes), 2)
            self.processes[1].wait.assert_not_called()
            self.assertFalse(self.manager.attempts['team/cli']['snapshot'].with_name('stop.json').exists())

    def test_unrelated_queued_work_on_same_seat_blocks_before_any_fence_or_control(self):
        extra = self.queue.enqueue(self.cli, {'dispatch_id': uuid.uuid4().hex,
            'channel': 'unrelated', 'prompt': 'Preserve this independent work', 'run_id': uuid.uuid4().hex})
        before = deepcopy(self.current())
        queue_disk = (self.root / 'queue/ledger.json').read_bytes()
        with self.assertRaises(EventConflict):
            self.retry(self.confirm())
        self.assertEqual(self.current(), before)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue_disk)
        self.assertEqual(self.queue.owned(self.cli, extra['envelope']['dispatch_id'])['state'], 'queued')
        self.assertFalse(self.manager.attempts['team/cli']['snapshot'].with_name('stop.json').exists())
        self.processes[1].wait.assert_not_called()
        self.assertEqual(len(self.processes), 2)

    def test_retry_request_is_durable_idempotent_and_fence_precedes_manager_control(self):
        old = self.prove_exit_on_wait()
        original_prepare = self.manager.prepare_retry_context
        observed = []
        def prepare(*args, **kwargs):
            persisted = SessionStore(str(self.root / 'session_runs.json')).get(self.session_id)
            self.assertEqual(persisted['state'], 'retrying')
            self.assertTrue(any(x['attempt_id'] == self.original['attempt_id']
                                for x in persisted['superseded_attempts']))
            self.assertEqual(self.queue.owned(self.cli, self.original['dispatch_id'])['state'], 'cancelling')
            observed.append(True)
            return original_prepare(*args, **kwargs)
        with patch.object(self.manager, 'prepare_retry_context', side_effect=prepare):
            self.retry(self.confirm())
        self.assertEqual(observed, [True])
        attempt = self.current()['pending_retry']['context']['launch_attempt']
        wait_count = old['process'].wait.call_count
        self.retry(self.confirm())
        self.assertEqual(self.current()['pending_retry']['context']['launch_attempt'], attempt)
        self.assertEqual(old['process'].wait.call_count, wait_count)
        self.assertEqual(len(self.processes), 3)
        self.fresh_ready()
        self.engine.monitor_turns(now=self.now + .1)
        new = deepcopy(self.current()['active_invocation'])
        self.retry(self.confirm())
        self.assertEqual(self.current()['active_invocation'], new)
        self.assertEqual(len(self.records()), 3)
        self.assertEqual(len(self.processes), 3)

    def test_permanent_stop_during_context_start_prevents_new_dispatch(self):
        self.prove_exit_on_wait()
        self.retry(self.confirm())
        self.engine.stop_session(self.session_id)
        fresh_instance, _ = self.fresh_ready()
        self.engine.monitor_turns(now=self.now + 1)
        self.engine.reconcile_stops(now=self.now + 1)
        state = self.current()
        self.assertTrue(state['stop_id'])
        self.assertFalse(state['dispatch_eligible'])
        self.assertEqual(len(self.records()), 2)
        self.assertIsNone(self.queue.claim(fresh_instance, 'new-cli-worker'))
        with self.assertRaises(EventConflict):
            self.retry(self.confirm())

    def test_worker_exit_without_child_receipt_holds_failed_preparation_and_quarantines_old_result(self):
        self.retry(self.confirm())
        state = self.current()
        self.assertEqual(state['state'], 'retrying')
        self.assertEqual(state['pending_retry']['status'], 'preparation_failed')
        self.assertEqual(state['pending_retry']['context']['state'], 'blocked')
        self.assertEqual(len(self.processes), 2)
        self.assertEqual(len(self.records()), 2)
        self.assertEqual(self.queue.owned(self.cli, self.original['dispatch_id'])['state'], 'cancelling')
        with self.assertRaises(EventConflict):
            self.engine.admit_event(self.original['brief_id'], 'final', 'Old late output', self.cli)
        self.assertEqual(self.current()['quarantined_events'][-1]['content'], 'Old late output')
        self.assertEqual(len(self.current()['admitted_events']), 1)

    def test_live_failed_api_supervisor_reuses_identity_only_after_signed_local_end(self):
        started = self.engine.start_session('review', 'api-retry',
            {'reviewer': self.api['name'], 'editor': self.cli['name']}, 'operator', input_text='API source')
        session_id = started['id']
        old = started['active_invocation']
        self.queue.claim(self.api, 'api-invocation')
        self.queue.acknowledge(self.api, old['dispatch_id'], 'api-invocation')
        attempt = self.manager.attempts['team/api']
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'failed',
            'name': self.api['name'], 'adapter_connected': True, 'authentication': 'failed',
            'error': 'provider_failure', 'updated_at': time.time()})
        self.engine.monitor_turns(now=self.now + 1)
        stalled = self.sessions.get(session_id)
        request_id = uuid.uuid4().hex
        self.engine.retry_turn(session_id, stalled['turn_recovery']['checkpoint_id'], old['attempt_id'],
                               request_id, now=self.now + 1)
        pending = self.sessions.get(session_id)
        self.assertEqual(pending['state'], 'retrying')
        self.assertEqual(pending['active_invocation']['attempt_id'], old['attempt_id'])
        self.assertEqual(self.queue.owned(self.api, old['dispatch_id'])['state'], 'cancelling')
        self.assertEqual(len(self.records()), 3)
        self.queue.cancellation_receipt(self.api, old['dispatch_id'], 'api-invocation', 'local_ended')
        self.engine.monitor_turns(now=self.now + 1.1)
        new = self.sessions.get(session_id)['active_invocation']
        self.assertNotEqual(new['attempt_id'], old['attempt_id'])
        self.assertEqual(new['expected_identity_id'], self.api['identity_id'])
        self.assertEqual(new['turn_id'], old['turn_id'])
        self.assertEqual(len(self.records()), 4)
        self.assertEqual(len(self.processes), 2)
        self.processes[0].wait.assert_not_called()
        self.assertEqual(json.loads(attempt['receipt'].read_text('utf-8'))['authentication'], 'failed')


if __name__ == '__main__':
    unittest.main()
