"""Historical exit ALGORITHM tests; patched probe statuses are not native absence proof."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import SeatError, SeatStore, atomic_json
from api_seat_runtime import SeatManager
from process_identity import open_verified_process
from registry import RuntimeRegistry
from runtime_ownership import new_launch_identity, record_spawn_outcome


@unittest.skipUnless(sys.platform == 'win32', 'owned birth plus explicit cold algorithm probes')
class ColdRetryContextTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.data = Path(temporary.name)
        self.providers = {'fake-cli': {'command': sys._base_executable, 'cwd': str(self.data),
            'cli_args': ['-c', 'pass'], 'cli_model_args': ['--model', '{model}'], 'mcp_inject': 'env', 'mcp_env_var': 'HISTORY_FAKE_SETTINGS'},
            'fake-api': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1',
                         'system_prompt': 'PRIVATE_PROVIDER_HISTORY_SENTINEL'}}
        self.store = SeatStore(self.data, self.providers)
        self.seat = {'id': 'cli', 'name': 'CLI', 'adapter': 'cli', 'provider': 'fake-cli',
            'model': 'original-cli-model', 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        self.store.save({'id': 'team', 'name': 'Team', 'seats': [self.seat]})
        self.registry = RuntimeRegistry(str(self.data))
        self.manager = SeatManager(ROOT, {'server': {'port': 18300, 'host': '127.0.0.1'},
            'mcp': {'http_port': 18301, 'sse_port': 18302}}, self.store, self.registry,
            monitor=False, boot_id=uuid.uuid4().hex)
        def close_handles():
            for attempt in self.manager.attempts.values():
                process = attempt.get('process')
                if process is not None and hasattr(process, 'close'):
                    process.close()
        self.addCleanup(close_handles)
        self.addCleanup(self.manager.shutdown)
        self.actual_popen = subprocess.Popen
        self.old = self.make_record()
        self.patcher = patch('api_seat_runtime.subprocess.Popen', side_effect=AssertionError('cold inventory spawned'))
        self.spawn = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def make_record(self, key='team/cli', adapter='cli', alive=False, invocation_protocol=None):
        attempt = uuid.uuid4().hex
        seat = deepcopy(self.seat) if adapter == 'cli' else {**self.seat, 'id': 'api',
            'adapter': 'openai-compatible', 'provider': 'fake-api', 'model': 'frozen-model'}
        effective = self.manager._effective(seat)
        identity = new_launch_identity(ROOT, effective, key, attempt, uuid.uuid4().hex)
        base = ('cli-' if adapter == 'cli' else 'api-') + hashlib.sha256(key.encode()).hexdigest()[:8] + '-' + attempt[:12]
        path = self.data / 'api_seat_runtime' / attempt / 'config.json'
        snapshot = {**effective, 'attempt': attempt, 'base': base, 'ownership': identity}
        if invocation_protocol is not None:
            snapshot['invocation_protocol'] = invocation_protocol
        atomic_json(path, snapshot)
        record_spawn_outcome(path, snapshot, 'pending')
        code = ('import sys,json;sys.path.insert(0,' + repr(str(ROOT)) + ');'
            'from pathlib import Path;from runtime_ownership import record_worker_birth;'
            'p=Path(' + repr(str(path)) + ');record_worker_birth(p,json.loads(p.read_text(encoding="utf-8")));'
            'sys.stdin.buffer.read(1);sys.exit(7)')
        child = self.actual_popen([sys._base_executable, '-u', '-c', code], stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        def cleanup():
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
            child.stdin.close()
        self.addCleanup(cleanup)
        record_spawn_outcome(path, snapshot, 'spawned')
        deadline = time.monotonic() + 10
        while not path.with_name('birth.json').exists():
            self.assertIsNone(child.poll())
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.02)
        birth = json.loads(path.with_name('birth.json').read_text('utf-8'))
        self.registry.seed({base: {'type': adapter, 'label': 'Fixture worker'}})
        principal = self.registry.register(base)
        receipt = {'attempt': attempt, 'state': 'ready' if alive else 'stopped', 'name': principal['name'],
            'identity_id': principal['identity_id'], 'adapter_connected': alive,
            'authentication': 'unknown', 'updated_at': time.time()}
        if not alive:
            child.stdin.write(b'x')
            child.stdin.flush()
            self.assertEqual(child.wait(timeout=5), 7)
            # Supplied protocol receipt, separate from the explicitly patched
            # wrapper probe. This does not claim a real CLI child was exercised.
            receipt['child_exit_code'] = 7
        atomic_json(path.with_name('receipt.json'), receipt)
        return dict(path=path, snapshot=snapshot, birth=birth, principal=principal, child=child,
                    attempt=attempt, key=key, receipt=receipt)

    def files(self):
        return {str(path.relative_to(self.data)): path.read_bytes()
                for path in (self.data / 'api_seat_runtime').rglob('*') if path.is_file()}

    def record(self, entry=None):
        entry = self.old if entry is None else entry
        return next(value for value in self.manager.reconcile_runtime() if value['attempt'] == entry['attempt'])

    def provenance(self, entry=None):
        entry = self.old if entry is None else entry
        snapshot = entry['snapshot']
        effective = {key: deepcopy(snapshot[key]) for key in ('seat', 'provider', 'server', 'mcp', 'config_resource') if key in snapshot}
        return {'key': entry['key'], 'launch_attempt': entry['attempt'],
                'identity_id': entry['principal']['identity_id'], 'effective': effective,
                'fingerprint': snapshot['ownership']['fingerprint']}

    def test_exact_cold_cli_provenance_resolves_exit_without_synthetic_popen(self):
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            self.manager.reconcile_runtime()
            proof = self.manager.runtime_exit_proof(self.provenance())
        self.assertTrue(proof['local_ended'])
        self.assertNotIn(self.old['key'], self.manager.attempts)
        self.spawn.assert_not_called()

    def test_cold_proven_ended_cli_offer_is_ready_without_adopting_dead_process(self):
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            self.manager.reconcile_runtime()
            offer = self.manager.retry_context_offer(self.provenance())
        self.assertEqual(offer['state'], 'ready')
        self.assertTrue(offer['old_local_ended'])
        self.assertNotIn(self.old['key'], self.manager.attempts)
        self.spawn.assert_not_called()

    def allow_explicit_launch(self):
        processes = []
        def spawn(*args, **kwargs):
            process = Mock()
            process.poll.return_value = None
            def ended(*args, **kwargs):
                process.poll.return_value = 1
                process.returncode = 1
                return 1
            process.wait.side_effect = ended
            process.terminate.side_effect = ended
            processes.append(process)
            return process
        self.spawn.side_effect = spawn
        return processes

    def mark_ready(self, context):
        attempt = self.manager.attempts[context['key']]
        instance = self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready',
            'name': instance['name'], 'identity_id': instance['identity_id'], 'adapter_connected': True,
            'authentication': 'unknown', 'confirmed_model': None, 'updated_at': time.time()})
        return instance

    def test_unknown_probe_or_wrong_exact_provenance_never_claims_local_end(self):
        provenance = self.provenance()
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'uncertain', 'process': None, 'error_code': 31}):
            self.assertFalse(self.manager.runtime_exit_proof(provenance)['local_ended'])
        mutations = []
        for key, value in (('identity_id', uuid.uuid4().hex), ('launch_attempt', uuid.uuid4().hex), ('key', 'team/other')):
            mutations.append({**provenance, key: value})
        changed = deepcopy(provenance)
        changed['effective']['seat']['model'] = 'different-frozen-model'
        changed['fingerprint'] = hashlib.sha256(json.dumps(changed['effective'], sort_keys=True).encode()).hexdigest()
        mutations.append(changed)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            for invalid in mutations:
                with self.subTest(provenance=invalid):
                    self.assertFalse(self.manager.runtime_exit_proof(invalid)['local_ended'])
        self.spawn.assert_not_called()

    def test_explicit_cold_cli_retry_launches_frozen_profile_once_then_new_ready_identity(self):
        provenance = self.provenance()
        self.providers['fake-cli'].update(cli_args=['edited-argument'], cwd=str(ROOT), mcp_env_var='EDITED_SETTINGS')
        self.store.save({'id': 'team', 'name': 'Edited saved team', 'seats': [{**self.seat, 'model': 'edited-model'}]})
        processes = self.allow_explicit_launch()
        context_key = uuid.uuid4().hex
        binding = {'child_run_id': uuid.uuid4().hex, 'role': 'editor'}
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            self.manager.reconcile_runtime()
            self.assertEqual(processes, [])
            context = self.manager.prepare_retry_context(provenance, context_key, binding=binding)
            self.assertEqual(context['state'], 'starting')
            self.assertTrue(context['old_local_ended'])
            self.assertFalse(context['clean_context'])
            self.assertNotEqual(context['launch_attempt'], self.old['attempt'])
            self.assertEqual(len(processes), 1)
            fresh = self.manager.attempts[context['key']]
            snapshot = json.loads(fresh['snapshot'].read_text('utf-8'))
            self.assertEqual(snapshot['seat']['model'], 'original-cli-model')
            self.assertEqual(snapshot['provider']['cli_args'], ['-c', 'pass'])
            self.assertEqual(snapshot['provider']['cwd'], str(self.data.resolve()))
            self.assertEqual(snapshot['provider']['mcp_env_var'], 'HISTORY_FAKE_SETTINGS')
            for field, value in binding.items():
                self.assertEqual(snapshot[field], value)
            repeated = self.manager.prepare_retry_context(provenance, context_key, binding=binding)
            self.assertEqual(repeated['launch_attempt'], context['launch_attempt'])
            self.assertEqual(len(processes), 1)
            identity = self.mark_ready(context)
            ready = self.manager.prepare_retry_context(provenance, context_key, binding=binding)
        self.assertEqual(ready['state'], 'ready')
        self.assertFalse(ready['clean_context'])
        self.assertEqual(ready['identity_id'], identity['identity_id'])
        self.assertNotEqual(identity['identity_id'], self.old['principal']['identity_id'])
        self.assertEqual(len(processes), 1)

    def test_dual_protocol_one_empty_api_history_allows_one_new_frozen_supervisor(self):
        api = self.make_record(key='team/api', adapter='openai-compatible', invocation_protocol=1)
        provenance = self.provenance(api)
        self.store.providers['fake-api'].update(base_url='http://127.0.0.1:19998/edited',
                                                system_prompt='Edited source must not enter')
        processes = self.allow_explicit_launch()
        context_key = uuid.uuid4().hex
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            proof = self.manager.runtime_exit_proof(provenance)
            self.assertTrue(proof['local_ended'])
            self.assertEqual(processes, [])
            context = self.manager.prepare_retry_context(provenance, context_key,
                binding={'child_run_id': uuid.uuid4().hex, 'role': 'reviewer'})
            self.assertEqual(context['state'], 'starting')
            self.assertTrue(context['old_local_ended'])
            fresh = self.manager.attempts[context['key']]
            self.assertEqual(fresh['effective'], provenance['effective'])
            self.assertNotEqual(context['launch_attempt'], api['attempt'])
            self.assertEqual(len(processes), 1)
            instance = self.mark_ready(context)
            ready = self.manager.prepare_retry_context(provenance, context_key,
                binding={'child_run_id': json.loads(fresh['snapshot'].read_text('utf-8'))['child_run_id'], 'role': 'reviewer'})
        self.assertEqual(ready['state'], 'ready')
        self.assertEqual(ready['identity_id'], instance['identity_id'])
        self.assertNotEqual(instance['identity_id'], api['principal']['identity_id'])
        self.assertEqual(len(processes), 1)

    def test_empty_legacy_api_history_never_invents_invocation_exit_or_launch(self):
        api = self.make_record(key='team/api', adapter='openai-compatible')
        provenance = self.provenance(api)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            self.assertFalse(self.manager.runtime_exit_proof(provenance)['local_ended'])
            context = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex)
        self.assertEqual(context['state'], 'blocked')
        self.spawn.assert_not_called()

    def test_api_exit_requires_exact_dispatch_bound_actual_fixture_child_journal(self):
        import invocation_evidence
        api = self.make_record(key='team/api', adapter='openai-compatible', invocation_protocol=1)
        dispatch = uuid.uuid4().hex
        scope = {'runtime_path': str(api['path'].parent), 'launch_attempt': api['attempt'],
                 'launch_nonce': api['snapshot']['ownership']['launch_nonce'], 'dispatch_id': dispatch}
        evidence = invocation_evidence.begin(scope)
        code = ('import sys,json;sys.path.insert(0,' + repr(str(ROOT)) + ');'
            'from invocation_evidence import record_birth;record_birth(json.loads(' + repr(json.dumps(evidence)) + '));'
            'sys.exit(9)')
        model_child = self.actual_popen([sys._base_executable, '-u', '-c', code],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        def cleanup():
            if model_child.poll() is None:
                model_child.terminate()
            model_child.wait(timeout=5)
        self.addCleanup(cleanup)
        invocation_evidence.spawn_outcome(evidence, 'spawned')
        self.assertEqual(model_child.wait(timeout=5), 9)
        invocation_evidence.record_exit(evidence, model_child.returncode)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            self.assertTrue(self.manager.runtime_exit_proof(self.provenance(api), dispatch)['local_ended'])
            self.assertFalse(self.manager.runtime_exit_proof(self.provenance(api), uuid.uuid4().hex)['local_ended'])
        self.spawn.assert_not_called()

    def test_retained_live_api_retry_reuses_verified_original_supervisor_without_spawn(self):
        api = self.make_record(key='team/api', adapter='openai-compatible', alive=True, invocation_protocol=1)
        identity = api['snapshot']['ownership']
        def probe(birth):
            if birth['pid'] == self.old['birth']['pid']:
                return {'status': 'absent', 'process': None, 'error_code': 87}
            return open_verified_process(birth)
        with patch('runtime_adoption.open_verified_process', side_effect=probe):
            self.manager.reconcile_runtime()
            payload = {'attempt': api['attempt'], 'launch_nonce': identity['launch_nonce'],
                'server_identity': identity['server_identity'], 'boot_id': self.manager.boot_id,
                'worker_pid': api['birth']['pid'], 'creation_filetime': api['birth']['creation_filetime'],
                'worker_root': api['birth']['worker_root']}
            self.assertTrue(self.manager.observe_runtime_heartbeat(api['principal'], payload)['verified'])
            process = self.manager.attempts[api['key']]['process']
            context = self.manager.prepare_retry_context(self.provenance(api), uuid.uuid4().hex)
        self.assertEqual(context['state'], 'ready')
        self.assertEqual(context['identity_id'], api['principal']['identity_id'])
        self.assertEqual(context['launch_attempt'], api['attempt'])
        self.assertIs(self.manager.attempts[api['key']]['process'], process)
        self.assertIsNone(api['child'].poll())
        self.spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
