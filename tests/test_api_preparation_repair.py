"""Adapter-neutral repair plus cooperative owned API toy-worker boundaries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import test_cold_retry_settlement as engine_fixture
from api_seats import SeatError, SeatStore, atomic_json
from api_seat_runtime import SeatManager
from process_identity import open_verified_process
from registry import RuntimeRegistry


class APIPreparationRepairTests(unittest.TestCase):
    def current(self):
        return self.sessions.get(self.session_id)

    def peer_record(self):
        return self.queue.owned(self.peer, self.independent['envelope']['dispatch_id'])

    def setUp(self):
        engine_fixture.ColdRetrySettlementTests.setUp(self)
        self.manager = engine_fixture.ColdRetrySettlementTests.proof_manager(self, True)
        self.failed_context = {'state': 'failed', 'key': 'retry-api-fixture/api',
            'launch_attempt': uuid.uuid4().hex, 'context_id': uuid.uuid4().hex,
            'identity_id': None, 'name': None, 'clean_context': False,
            'old_local_ended': True, 'verification_basis': 'isolated_request_packet'}
        self.manager.prepare_retry_context.return_value = deepcopy(self.failed_context)
        self.manager.context_status.return_value = deepcopy(self.failed_context)
        self.engine.retry_turn(self.session_id, self.checkpoint, self.old['attempt_id'], self.request, now=self.now)
        self.assertEqual(self.current()['pending_retry']['status'], 'preparation_failed')

    def test_engine_explicit_failed_api_repair_preserves_reserved_request_and_turn(self):
        before = deepcopy(self.current())
        self.engine.retry_turn(self.session_id, self.checkpoint, self.old['attempt_id'], self.request, now=self.now)
        self.assertEqual(self.current()['pending_retry']['context']['launch_attempt'], self.failed_context['launch_attempt'])
        self.assertTrue(all(call.kwargs['retry_attempt'] is None for call in self.manager.prepare_retry_context.call_args_list))
        self.manager.prepare_retry_context.reset_mock()
        replacement = {**self.failed_context, 'state': 'starting', 'launch_attempt': uuid.uuid4().hex}
        self.manager.prepare_retry_context.return_value = replacement
        self.manager.context_status.return_value = replacement
        self.engine.repair_retry(self.session_id, self.request, self.failed_context['launch_attempt'], now=self.now + .1)
        current = self.current()
        for field in ('request_id', 'new_attempt_id', 'new_brief_id', 'new_dispatch_id'):
            self.assertEqual(current['pending_retry'][field], before['pending_retry'][field])
        self.assertEqual(current['pending_retry']['old_invocation']['turn_id'], self.old['turn_id'])
        self.assertEqual(current['input_snapshot'], before['input_snapshot'])
        self.assertEqual(current['admitted_events'], before['admitted_events'])
        self.assertEqual(current['pending_retry']['context']['launch_attempt'], replacement['launch_attempt'])
        self.assertEqual(self.manager.prepare_retry_context.call_args.kwargs['retry_attempt'], self.failed_context['launch_attempt'])

    def test_engine_stale_controls_or_unrelated_prepared_work_preserve_session_and_queue(self):
        self.manager.prepare_retry_context.reset_mock()
        before, disk = deepcopy(self.current()), self.path.read_bytes()
        queue = (self.root / 'queue/ledger.json').read_bytes()
        for request, attempt, confirmation in ((uuid.uuid4().hex, self.failed_context['launch_attempt'], None),
            (self.request, uuid.uuid4().hex, None),
            (self.request, self.failed_context['launch_attempt'], {'confirm': 1, 'launch_attempt': self.failed_context['launch_attempt']})):
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.engine.repair_retry(self.session_id, request, attempt, confirmation=confirmation, now=self.now)
            self.assertEqual(self.current(), before)
            self.assertEqual(self.path.read_bytes(), disk)
            self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue)
        self.registry.seed({'prepared': {'type': 'api'}})
        prepared = self.registry.register('prepared')
        self.sessions._event_update(self.session_id, lambda value: value['pending_retry']['context'].update(
            identity_id=prepared['identity_id'], name=prepared['name']))
        self.queue.enqueue(prepared, {'prompt': 'Unrelated work must survive repair', 'channel': 'unrelated'})
        before, disk = deepcopy(self.current()), self.path.read_bytes()
        queue = (self.root / 'queue/ledger.json').read_bytes()
        with self.assertRaises(ValueError):
            self.engine.repair_retry(self.session_id, self.request, self.failed_context['launch_attempt'], now=self.now)
        self.assertEqual(self.current(), before)
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue)
        self.manager.prepare_retry_context.assert_not_called()

    def native_preparation(self):
        """Real owned toy supervisors; HTTP callback and old absence are explicit seams."""
        data = self.root / 'native'
        providers = {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1',
                              'system_prompt': 'Frozen API repair instruction'}}
        store = SeatStore(data, providers)
        seat = {'id': 'api', 'name': 'API', 'adapter': 'openai-compatible', 'provider': 'fake',
                'model': 'original-model', 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        store.save({'id': 'team', 'name': 'Native toy fixture', 'seats': [seat, {**seat, 'id': 'peer', 'name': 'Peer'}]})
        registry = RuntimeRegistry(str(data))
        config = {'server': {'port': 18300, 'host': '127.0.0.1'}, 'mcp': {'http_port': 18301, 'sse_port': 18302}}
        producer = SeatManager(ROOT, config, store, registry, monitor=False, boot_id=uuid.uuid4().hex)
        self.addCleanup(producer.shutdown)
        actual_popen = subprocess.Popen
        owned = []
        def start_toy(argv, **kwargs):
            path = Path(argv[argv.index('--seat-file') + 1])
            code = ('import sys,json,time;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                'from pathlib import Path;from runtime_ownership import record_worker_birth;from api_seats import atomic_json;'
                'p=Path(' + repr(str(path)) + ');s=json.loads(p.read_text(encoding="utf-8"));'
                'record_worker_birth(p,s)\n'
                'while True:\n'
                ' q=p.with_name("stop.json")\n'
                ' if q.exists() and json.loads(q.read_text(encoding="utf-8")).get("attempt")==s["attempt"]: break\n'
                ' time.sleep(.02)\n'
                'r=p.with_name("receipt.json");v=json.loads(r.read_text(encoding="utf-8")) if r.exists() else {}\n'
                'v.update(attempt=s["attempt"],state="stopped",adapter_connected=False,updated_at=time.time())\n'
                'atomic_json(r,v);sys.exit(7)')
            process = actual_popen([sys._base_executable, '-u', '-c', code], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            owned.append((process, path))
            return process
        spawn = self.enterContext(patch('api_seat_runtime.subprocess.Popen', side_effect=start_toy))
        def cleanup_owned():
            for process, path in owned:
                if process.poll() is None:
                    atomic_json(path.with_name('stop.json'), {'attempt': path.parent.name})
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()  # Exact fixture Popen; toy never spawns model children.
                    process.wait(timeout=5)
        self.addCleanup(cleanup_owned)
        def register_ready(manager, key):
            attempt = manager.attempts[key]
            deadline = time.monotonic() + 10
            while not attempt['snapshot'].with_name('birth.json').exists():
                self.assertIsNone(attempt['process'].poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.02)
            instance = registry.register(attempt['base'])
            atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready', 'name': instance['name'],
                'identity_id': instance['identity_id'], 'adapter_connected': True, 'authentication': 'unknown', 'updated_at': time.time()})
            manager.snapshot()
            return instance
        producer.launch('team', 'api')
        original = producer.attempts['team/api']
        original_instance = register_ready(producer, 'team/api')
        provenance = producer.launch_provenance(original_instance)
        self.assertIsNotNone(provenance)
        atomic_json(original['snapshot'].with_name('stop.json'), {'attempt': original['id']})
        self.assertEqual(original['process'].wait(timeout=5), 7)
        old_pid = json.loads(original['snapshot'].with_name('birth.json').read_text('utf-8'))['pid']
        # The source supervisor is now a cold historical owner, rather than an
        # unavailable live in-memory API supervisor that should be reused.
        producer = SeatManager(ROOT, config, store, registry, monitor=False, boot_id=uuid.uuid4().hex)
        self.addCleanup(producer.shutdown)
        self.addCleanup(cleanup_owned)
        def native_or_old_absence(birth):
            if birth['pid'] == old_pid:
                return {'status': 'absent', 'process': None, 'error_code': 87}
            return open_verified_process(birth)
        self.enterContext(patch('runtime_adoption.open_verified_process', side_effect=native_or_old_absence))
        context_key, binding = uuid.uuid4().hex, {'child_run_id': uuid.uuid4().hex, 'role': 'reviewer'}
        prepared = producer.prepare_retry_context(provenance, context_key, binding=binding)
        self.assertEqual(prepared['state'], 'starting', prepared)
        prepared_instance = register_ready(producer, prepared['key'])
        prepared_attempt = producer.attempts[prepared['key']]
        producer.launch('team', 'peer')
        peer_instance = register_ready(producer, 'team/peer')
        peer_attempt = producer.attempts['team/peer']
        cold = SeatManager(ROOT, config, store, registry, monitor=False, boot_id=uuid.uuid4().hex)
        def close_handles():
            for attempt in cold.attempts.values():
                if hasattr(attempt.get('process'), 'close'):
                    attempt['process'].close()
        self.addCleanup(close_handles)
        self.addCleanup(cold.shutdown)
        # Ensure toy workers end cooperatively before either manager's cleanup.
        self.addCleanup(cleanup_owned)
        cold.reconcile_runtime()
        for instance, attempt in ((prepared_instance, prepared_attempt), (peer_instance, peer_attempt)):
            birth = json.loads(attempt['snapshot'].with_name('birth.json').read_text('utf-8'))
            snapshot = json.loads(attempt['snapshot'].read_text('utf-8'))
            identity = snapshot['ownership']
            payload = {'attempt': attempt['id'], 'launch_nonce': identity['launch_nonce'], 'server_identity': identity['server_identity'],
                'boot_id': cold.boot_id, 'worker_pid': birth['pid'], 'creation_filetime': birth['creation_filetime'], 'worker_root': birth['worker_root']}
            self.assertTrue(cold.observe_runtime_heartbeat(instance, payload)['verified'])
            self.assertEqual(type(cold.attempts[snapshot['ownership']['launch_key']]['process']).__name__, 'OwnedProcessHandle')
        receipt = json.loads(prepared_attempt['receipt'].read_text('utf-8'))
        atomic_json(prepared_attempt['receipt'], {**receipt, 'state': 'failed', 'adapter_connected': True})
        spawn.reset_mock()
        spawn.side_effect = AssertionError('API repair unexpectedly spawned')
        return dict(manager=cold, producer=producer, provenance=provenance, context_key=context_key, binding=binding,
            prepared=prepared, attempt=prepared_attempt, peer=peer_attempt, spawn=spawn, store=store)

    @unittest.skipUnless(sys.platform == 'win32', 'actual owned API toy-worker handle')
    def test_live_prepared_api_requires_exact_literal_confirmation_without_actuation(self):
        native = self.native_preparation()
        before = native['attempt']['receipt'].read_bytes()
        manager, prepared = native['manager'], native['prepared']
        blocked = manager.prepare_retry_context(native['provenance'], native['context_key'], binding=native['binding'],
                                                 retry_attempt=prepared['launch_attempt'])
        self.assertEqual(blocked['state'], 'blocked')
        for confirmation in ({'confirm': True, 'launch_attempt': uuid.uuid4().hex},
                             {'confirm': 1, 'launch_attempt': prepared['launch_attempt']}):
            with self.subTest(confirmation=confirmation), self.assertRaises(SeatError):
                manager.prepare_retry_context(native['provenance'], native['context_key'], binding=native['binding'],
                    retry_attempt=prepared['launch_attempt'], confirmation=confirmation)
        self.assertIsNone(native['attempt']['process'].poll())
        self.assertIsNone(native['peer']['process'].poll())
        self.assertFalse(native['attempt']['snapshot'].with_name('stop.json').exists())
        self.assertEqual(native['attempt']['receipt'].read_bytes(), before)
        native['spawn'].assert_not_called()

    @unittest.skipUnless(sys.platform == 'win32', 'actual owned API toy-worker cooperative exit')
    def test_confirmed_live_api_repair_cooperatively_ends_worker_without_cli_or_forcekill(self):
        native = self.native_preparation()
        manager, prepared = native['manager'], native['prepared']
        replacements = []
        def replacement(*args, **kwargs):
            process = Mock()
            process.poll.return_value = None
            def ended(*args, **kwargs):
                process.poll.return_value = 1
                process.returncode = 1
                return 1
            process.wait.side_effect = ended
            process.terminate.side_effect = ended
            replacements.append(process)
            return process
        native['spawn'].side_effect = replacement
        with patch.object(manager, 'terminate_owned', side_effect=AssertionError('API used CLI termination path')), \
             patch('process_identity.OwnedProcessHandle.terminate', side_effect=AssertionError('API repair force-killed retained worker')):
            result = manager.prepare_retry_context(native['provenance'], native['context_key'], binding=native['binding'],
                retry_attempt=prepared['launch_attempt'], confirmation={'confirm': True, 'launch_attempt': prepared['launch_attempt']})
        self.assertEqual(result['state'], 'starting')
        self.assertNotEqual(result['launch_attempt'], prepared['launch_attempt'])
        self.assertEqual(native['attempt']['process'].wait(timeout=5), 7)
        receipt = json.loads(native['attempt']['receipt'].read_text('utf-8'))
        self.assertEqual(receipt['state'], 'stopped')
        self.assertNotIn('child_exit_code', receipt, 'API supervisor exit is not a model-child exit code')
        self.assertEqual(len(replacements), 1)
        self.assertIsNone(native['peer']['process'].poll())
        self.assertFalse(native['peer']['snapshot'].with_name('stop.json').exists())
        repeat = manager.prepare_retry_context(native['provenance'], native['context_key'], binding=native['binding'],
            retry_attempt=prepared['launch_attempt'], confirmation={'confirm': True, 'launch_attempt': prepared['launch_attempt']})
        self.assertEqual(repeat['launch_attempt'], result['launch_attempt'])
        self.assertEqual(len(replacements), 1)

    @unittest.skipUnless(sys.platform == 'win32', 'actual owned API toy-worker with pending journal')
    def test_pending_model_intent_blocks_replacement_even_after_supervisor_cooperative_exit(self):
        import invocation_evidence
        native = self.native_preparation()
        attempt, manager = native['attempt'], native['manager']
        snapshot = json.loads(attempt['snapshot'].read_text('utf-8'))
        invocation_evidence.begin({'runtime_path': str(attempt['snapshot'].parent), 'launch_attempt': attempt['id'],
            'launch_nonce': snapshot['ownership']['launch_nonce'], 'dispatch_id': uuid.uuid4().hex})
        atomic_json(attempt['snapshot'].with_name('stop.json'), {'attempt': attempt['id']})
        self.assertEqual(attempt['process'].wait(timeout=5), 7)
        result = manager.prepare_retry_context(native['provenance'], native['context_key'], binding=native['binding'],
            retry_attempt=attempt['id'], confirmation={'confirm': True, 'launch_attempt': attempt['id']})
        self.assertEqual(result['state'], 'blocked')
        native['spawn'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
