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


@unittest.skipUnless(sys.platform == 'win32', 'actual owned birth, explicit cold algorithm probes')
class ColdPreparationRepairTests(unittest.TestCase):
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

    def new_manager(self):
        manager = SeatManager(ROOT, self.manager.config, self.store, self.registry,
                              monitor=False, boot_id=uuid.uuid4().hex)
        self.addCleanup(manager.shutdown)
        return manager

    def failed_preparation(self, entry=None):
        entry = self.old if entry is None else entry
        provenance = self.provenance(entry)
        context_key = uuid.uuid4().hex
        binding = {'child_run_id': uuid.uuid4().hex, 'role': 'editor'}
        self.spawn.side_effect = OSError('fixture synchronous prepared Popen failure')
        failed = self.manager.prepare_retry_context(provenance, context_key, binding=binding)
        self.assertEqual(failed['state'], 'failed')
        path = self.manager.attempts[failed['key']]['snapshot']
        snapshot = json.loads(path.read_text('utf-8'))
        self.assertEqual(json.loads(path.with_name('launch.json').read_text('utf-8'))['spawn_outcome'], 'failed')
        self.assertFalse(path.with_name('birth.json').exists())
        self.spawn.reset_mock()
        self.spawn.side_effect = AssertionError('cold replay silently replaced prepared context')
        return provenance, context_key, binding, failed, path, snapshot

    def test_cold_cli_original_request_replays_same_failed_preparation_without_spawn(self):
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            provenance, context_key, binding, failed, path, snapshot = self.failed_preparation()
            cold = self.new_manager()
            replay = cold.prepare_retry_context(provenance, context_key, binding=binding)
        self.assertEqual(replay['launch_attempt'], failed['launch_attempt'])
        self.assertEqual(replay['state'], 'failed')
        self.spawn.assert_not_called()

    def test_cold_api_original_request_replays_same_failed_preparation_without_spawn(self):
        api = self.make_record(key='team/api', adapter='openai-compatible', invocation_protocol=1)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            provenance, context_key, binding, failed, path, snapshot = self.failed_preparation(api)
            before = self.files()
            cold = self.new_manager()
            replay = cold.prepare_retry_context(provenance, context_key, binding=binding)
        self.assertEqual(replay['launch_attempt'], failed['launch_attempt'])
        self.assertEqual(replay['state'], 'failed')
        self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()

    def test_explicit_exact_failed_attempt_repairs_cli_and_api_once_from_frozen_profile(self):
        api = self.make_record(key='team/api', adapter='openai-compatible', invocation_protocol=1)
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            for entry in (self.old, api):
                with self.subTest(adapter=entry['snapshot']['seat']['adapter']):
                    provenance, context_key, binding, failed, path, snapshot = self.failed_preparation(entry)
                    before = path.with_name('launch.json').read_bytes()
                    self.store.providers['fake-cli'].update(cli_args=['edited-argument'], cwd=str(ROOT),
                                                           mcp_env_var='EDITED_SETTINGS')
                    self.store.providers['fake-api'].update(base_url='http://127.0.0.1:19998/edited',
                                                           system_prompt='Edited live provider prompt')
                    cold = self.new_manager()
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
                    repaired = cold.prepare_retry_context(provenance, context_key, binding=binding,
                                                          retry_attempt=failed['launch_attempt'])
                    self.assertEqual(repaired['state'], 'starting')
                    self.assertNotEqual(repaired['launch_attempt'], failed['launch_attempt'])
                    self.assertEqual(len(processes), 1)
                    fresh = json.loads(cold.attempts[repaired['key']]['snapshot'].read_text('utf-8'))
                    self.assertNotEqual(fresh['ownership']['launch_nonce'], snapshot['ownership']['launch_nonce'])
                    for field in ('seat', 'provider', 'server', 'mcp', 'config_resource',
                                  'context_key', 'context_source_fingerprint', 'context_base_effective',
                                  'child_run_id', 'role'):
                        self.assertEqual(fresh.get(field), snapshot.get(field), field)
                    repeat = cold.prepare_retry_context(provenance, context_key, binding=binding,
                                                         retry_attempt=failed['launch_attempt'])
                    self.assertEqual(repeat['launch_attempt'], repaired['launch_attempt'])
                    current = cold.prepare_retry_context(provenance, context_key, binding=binding)
                    self.assertEqual(current['launch_attempt'], repaired['launch_attempt'])
                    self.assertEqual(len(processes), 1)
                    self.assertEqual(path.with_name('launch.json').read_bytes(), before)

    def test_pending_or_spawned_unproven_and_ambiguous_contexts_never_respawn_even_confirmed(self):
        with patch('runtime_adoption.open_verified_process', return_value={'status': 'absent', 'process': None, 'error_code': 87}):
            provenance, context_key, binding, failed, path, snapshot = self.failed_preparation()
            manifest = json.loads(path.with_name('launch.json').read_text('utf-8'))
            for outcome in ('spawned', 'pending'):
                with self.subTest(spawn_outcome=outcome):
                    atomic_json(path.with_name('launch.json'), {**manifest, 'spawn_outcome': outcome})
                    before = self.files()
                    cold = self.new_manager()
                    try:
                        blocked = cold.prepare_retry_context(provenance, context_key, binding=binding,
                            retry_attempt=failed['launch_attempt'],
                            confirmation={'launch_attempt': failed['launch_attempt'], 'confirm': True})
                    except SeatError:
                        pass
                    else:
                        self.assertEqual(blocked['state'], 'blocked')
                    self.assertEqual(self.files(), before)
            atomic_json(path.with_name('launch.json'), manifest)
            # Two independently failed, unlinked physical attempts with exactly
            # the same source/binding cannot be resolved by newest mtime.
            attempt = uuid.uuid4().hex
            effective = {key: deepcopy(snapshot[key]) for key in ('seat', 'provider', 'server', 'mcp', 'config_resource') if key in snapshot}
            ownership = new_launch_identity(ROOT, effective, failed['key'], attempt, snapshot['ownership']['boot_id'])
            extra = deepcopy(snapshot)
            extra.update(attempt=attempt, base='cli-' + hashlib.sha256(failed['key'].encode()).hexdigest()[:8] + '-' + attempt[:12],
                         ownership=ownership)
            extra_path = path.parent.parent / attempt / 'config.json'
            atomic_json(extra_path, extra)
            record_spawn_outcome(extra_path, extra, 'pending')
            record_spawn_outcome(extra_path, extra, 'failed')
            os.utime(extra_path, (time.time() + 600, time.time() + 600))
            before = self.files()
            cold = self.new_manager()
            try:
                blocked = cold.prepare_retry_context(provenance, context_key, binding=binding)
            except SeatError:
                pass
            else:
                self.assertEqual(blocked['state'], 'blocked')
            self.assertEqual(self.files(), before)
        self.spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
