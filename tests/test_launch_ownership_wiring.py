"""Owned same-turn retry relaunches, with receipt/process doubles only."""
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
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
from registry import RuntimeRegistry


class LaunchOwnershipWiringTests(unittest.TestCase):
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

    def ready(self, seat_id):
        launched = self.manager.launch('team', seat_id)
        attempt = self.manager.attempts['team/' + seat_id]
        instance = self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': launched['attempt'], 'state': 'ready',
            'name': instance['name'], 'adapter_connected': True, 'authentication': 'unknown',
            'confirmed_model': None, 'updated_at': time.time()})
        self.assertEqual(self.manager.inspect('team', seat_id)['state'], 'ready')
        return instance, launched

    def test_constructor_validates_boot_id_before_any_launch(self):
        for value in (True, 1, '', 'x' * 32, 'bad'):
            with self.subTest(boot_id=value), self.assertRaises(ValueError):
                SeatManager(ROOT, {'server': {'port': 18300}}, self.store, self.registry,
                            monitor=False, boot_id=value)
        self.assertEqual(self.processes, [])

    def test_pending_manifest_and_ownership_exist_before_popen(self):
        real_spawn = self.spawn.side_effect
        observed = []
        def inspect(argv, **kwargs):
            path = Path(argv[argv.index('--seat-file') + 1])
            snapshot = json.loads(path.read_text('utf-8'))
            ownership = snapshot['ownership']
            manifest = json.loads(path.with_name('launch.json').read_text('utf-8'))
            self.assertEqual(manifest, {**ownership, 'spawn_outcome': 'pending'})
            self.assertEqual(ownership['attempt'], snapshot['attempt'])
            self.assertEqual(ownership['launch_key'], 'team/api')
            self.assertEqual(ownership['boot_id'], self.manager.boot_id)
            observed.append(path)
            return real_spawn(argv, **kwargs)
        self.spawn.side_effect = inspect
        launched = self.manager.launch('team', 'api')
        self.assertEqual(len(observed), 1)
        manifest = json.loads(observed[0].with_name('launch.json').read_text('utf-8'))
        self.assertEqual(manifest['spawn_outcome'], 'spawned')
        self.assertEqual(manifest['attempt'], launched['attempt'])

    def test_fresh_default_boot_ids_and_explicit_boot_are_preserved(self):
        other = SeatManager(ROOT, {'server': {'port': 18300}}, self.store, self.registry, monitor=False)
        self.addCleanup(other.shutdown)
        self.assertRegex(self.manager.boot_id, r'^[0-9a-f]{32}$')
        self.assertRegex(other.boot_id, r'^[0-9a-f]{32}$')
        self.assertNotEqual(other.boot_id, self.manager.boot_id)
        boot = uuid.uuid4().hex
        chosen = SeatManager(ROOT, {'server': {'port': 18300}}, self.store, self.registry,
                             monitor=False, boot_id=boot)
        self.addCleanup(chosen.shutdown)
        chosen.launch('team', 'api')
        snapshot = json.loads(chosen.attempts['team/api']['snapshot'].read_text('utf-8'))
        self.assertEqual(snapshot['ownership']['boot_id'], boot)

    def test_synchronous_popen_oserror_records_failed_without_process_handle(self):
        seen = []
        def fail(argv, **kwargs):
            path = Path(argv[argv.index('--seat-file') + 1])
            pending = json.loads(path.with_name('launch.json').read_text('utf-8'))
            self.assertEqual(pending['spawn_outcome'], 'pending')
            seen.append(path)
            raise OSError('fixture synchronous Popen failure')
        self.spawn.side_effect = fail
        result = self.manager.launch('team', 'api')
        self.assertEqual(result['state'], 'failed')
        self.assertIsNone(self.manager.attempts['team/api']['process'])
        self.assertEqual(json.loads(seen[0].with_name('launch.json').read_text('utf-8'))['spawn_outcome'], 'failed')
        self.assertEqual(self.processes, [])

    def test_post_spawn_persistence_failure_retains_real_handle_and_pending_intent(self):
        import runtime_ownership
        actual_atomic = runtime_ownership.atomic_json
        outcomes = []
        def interrupted(path, value):
            if Path(path).name == 'launch.json':
                outcomes.append(value['spawn_outcome'])
                if value['spawn_outcome'] == 'spawned':
                    raise OSError('fixture post-Popen manifest failure')
            return actual_atomic(path, value)
        with patch('runtime_ownership.atomic_json', side_effect=interrupted):
            try:
                self.manager.launch('team', 'api')
            except OSError:
                pass
        attempt = self.manager.attempts['team/api']
        self.assertEqual(len(self.processes), 1)
        self.assertIs(attempt['process'], self.processes[0])
        self.assertIsNone(attempt['process'].poll())
        self.assertNotEqual(attempt['state'], 'failed', 'post-spawn bookkeeping cannot claim synchronous spawn failure')
        self.assertEqual(json.loads(attempt['snapshot'].with_name('launch.json').read_text('utf-8'))['spawn_outcome'], 'pending')
        self.assertEqual(outcomes, ['pending', 'spawned'])

    @unittest.skipUnless(sys.platform == 'win32', 'Windows hidden native console launch settings')
    def test_cli_ownership_wiring_preserves_hidden_native_console_and_secret_free_manifest(self):
        self.manager.launch('team', 'cli')
        argv, kwargs = self.spawn.call_args
        self.assertIn('cli_worker.py', argv[0][2])
        self.assertEqual(kwargs['creationflags'] & subprocess.CREATE_NEW_CONSOLE, subprocess.CREATE_NEW_CONSOLE)
        self.assertEqual(kwargs['startupinfo'].dwFlags & subprocess.STARTF_USESHOWWINDOW, subprocess.STARTF_USESHOWWINDOW)
        self.assertEqual(kwargs['startupinfo'].wShowWindow, subprocess.SW_HIDE)
        for stream in ('stdin', 'stdout', 'stderr'):
            self.assertNotIn(stream, kwargs)
        attempt = self.manager.attempts['team/cli']
        snapshot = json.loads(attempt['snapshot'].read_text('utf-8'))
        manifest = json.loads(attempt['snapshot'].with_name('launch.json').read_text('utf-8'))
        self.assertEqual(manifest['spawn_outcome'], 'spawned')
        self.assertEqual(manifest['launch_key'], 'team/cli')
        self.assertEqual(snapshot['provider']['cli_args'], ['fixture-original'])
        self.manager.launch('team', 'api')
        api_attempt = self.manager.attempts['team/api']
        serialized = api_attempt['snapshot'].with_name('launch.json').read_text('utf-8')
        self.assertNotIn('credential-value-test-only', serialized)
        self.assertNotIn('Original API instruction', serialized)
        self.assertNotIn('RESTART_TEST_KEY', serialized)
        self.assertNotIn('api-original', serialized)

    def test_explicit_restart_changes_attempt_and_nonce_but_not_effective_fingerprint(self):
        self.manager.launch('team', 'api')
        first = self.manager.attempts['team/api']
        snapshot = json.loads(first['snapshot'].read_text('utf-8'))
        self.manager.launch('team', 'api', restart=True)
        second = self.manager.attempts['team/api']
        next_snapshot = json.loads(second['snapshot'].read_text('utf-8'))
        self.assertNotEqual(first['id'], second['id'])
        self.assertNotEqual(snapshot['ownership']['launch_nonce'], next_snapshot['ownership']['launch_nonce'])
        self.assertEqual(snapshot['ownership']['fingerprint'], next_snapshot['ownership']['fingerprint'])
        self.assertEqual(first['fingerprint'], second['fingerprint'])
        before = len(self.processes)
        same = self.manager.launch('team', 'api')
        self.assertEqual(same['attempt'], second['id'])
        self.assertEqual(len(self.processes), before, 'nonce alone must not create settings drift')

    def test_same_turn_retry_and_corrected_context_share_manifest_launch_path(self):
        self.store.providers['fake-cli'].update(cli_fresh_context_args=['--context-id', '{context_id}'],
                                              cli_fresh_context_verified=True)
        instance, launched = self.ready('cli')
        provenance = self.manager.launch_provenance(instance)
        old = self.manager.attempts['team/cli']
        old['process'].poll.return_value = 0
        old['process'].returncode = 0
        atomic_json(old['receipt'], {'attempt': old['id'], 'state': 'stopped', 'child_exit_code': 0,
            'adapter_connected': False, 'authentication': 'unknown', 'updated_at': time.time()})
        prepared = [self.manager.prepare_retry_context(provenance, uuid.uuid4().hex),
                    self.manager.prepare_clean_context(provenance, uuid.uuid4().hex)]
        nonces = set()
        for context in prepared:
            self.assertEqual(context['state'], 'starting')
            attempt = self.manager.attempts[context['key']]
            snapshot = json.loads(attempt['snapshot'].read_text('utf-8'))
            manifest = json.loads(attempt['snapshot'].with_name('launch.json').read_text('utf-8'))
            self.assertEqual(manifest['spawn_outcome'], 'spawned')
            self.assertEqual(manifest['launch_key'], context['key'])
            self.assertEqual(manifest['attempt'], context['launch_attempt'])
            self.assertEqual(manifest['fingerprint'], hashlib.sha256(json.dumps(attempt['effective'], sort_keys=True).encode()).hexdigest())
            self.assertEqual(snapshot['ownership']['boot_id'], self.manager.boot_id)
            self.assertEqual(snapshot['seat']['model'], 'cli-original')
            nonces.add(manifest['launch_nonce'])
        self.assertEqual(len(nonces), 2)
        self.assertEqual(len(self.processes), 3)


if __name__ == '__main__':
    unittest.main()
