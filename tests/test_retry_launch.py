"""Owned same-turn retry relaunches, with receipt/process doubles only."""
import copy
import hashlib
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
from api_seats import SeatError, SeatStore, atomic_json
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry


class RetryLaunchTests(unittest.TestCase):
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

    def cli(self):
        instance, launch = self.ready('cli')
        return instance, launch, self.manager.launch_provenance(instance)

    def ended(self, attempt):
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'stopped',
            'child_exit_code': 0, 'adapter_connected': False, 'updated_at': time.time()})
        attempt['process'].poll.return_value = 0
        attempt['process'].returncode = 0

    def register_ready(self, prepared):
        attempt = self.manager.attempts[prepared['key']]
        instance = self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready',
            'name': instance['name'], 'adapter_connected': True, 'authentication': 'unknown',
            'confirmed_model': None, 'updated_at': time.time()})
        return instance

    def test_live_generic_offer_is_read_only_and_bound_to_owned_attempt(self):
        instance, launch, provenance = self.cli()
        offer = self.manager.retry_context_offer(provenance)
        self.assertEqual(offer['state'], 'confirmation_required')
        self.assertEqual(offer['launch_attempt'], launch['attempt'])
        self.assertEqual(len(self.processes), 1)
        self.processes[0].wait.assert_not_called()
        self.assertFalse(self.manager.attempts['team/cli']['snapshot'].with_name('stop.json').exists())

    def test_stale_or_nonliteral_confirmation_rejects_before_control_or_spawn(self):
        _, launch, provenance = self.cli()
        for confirmation in ({'launch_attempt': uuid.uuid4().hex, 'confirm': True},
                             {'launch_attempt': launch['attempt'], 'confirm': 1}):
            with self.subTest(confirmation=confirmation), self.assertRaises(SeatError):
                self.manager.prepare_retry_context(provenance, uuid.uuid4().hex,
                                                   confirmation=confirmation)
        old = self.manager.attempts['team/cli']
        self.assertFalse(old['snapshot'].with_name('stop.json').exists())
        self.assertEqual(len(self.processes), 1)
        old['process'].wait.assert_not_called()

    def test_offer_requires_matching_receipt_integer_child_exit_and_worker_exit(self):
        _, _, provenance = self.cli()
        old = self.manager.attempts['team/cli']
        for receipt, worker_exit in (
            ({'attempt': old['id'], 'state': 'stopped', 'child_exit_code': 0}, None),
            ({'attempt': old['id'], 'state': 'ready'}, 0),
            ({'attempt': uuid.uuid4().hex, 'state': 'stopped', 'child_exit_code': 0}, 0),
            ({'attempt': old['id'], 'state': 'stopped', 'child_exit_code': True}, 0)):
            with self.subTest(receipt=receipt, worker_exit=worker_exit):
                atomic_json(old['receipt'], receipt)
                old['process'].poll.return_value = worker_exit
                self.assertNotEqual(self.manager.retry_context_offer(provenance)['state'], 'ready')
                if worker_exit is not None:
                    prepared = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex)
                    self.assertEqual(prepared['state'], 'blocked')
        self.ended(old)
        self.assertEqual(self.manager.retry_context_offer(provenance)['state'], 'ready')
        self.assertEqual(len(self.processes), 1)

    def test_generic_relaunch_uses_frozen_profile_and_stays_nonclean_after_readiness(self):
        instance, launch, provenance = self.cli()
        self.ended(self.manager.attempts['team/cli'])
        self.package['seats'][1]['model'] = 'edited-model'
        self.store.providers['fake-cli'].update(cli_args=['edited-args'], cwd=str(ROOT),
                                               mcp_env_var='EDITED_SETTINGS')
        self.manager.save(self.package)
        binding = {'child_run_id': uuid.uuid4().hex, 'role': 'editor'}
        context_key = uuid.uuid4().hex
        # Inspect the actual file handed to Popen, before any readiness/backlink.
        spawn = self.spawn.side_effect
        snapshots = []
        def capture(argv, **kwargs):
            snapshots.append(json.loads(Path(argv[argv.index('--seat-file') + 1]).read_text('utf-8')))
            return spawn(argv, **kwargs)
        self.spawn.side_effect = capture
        prepared = self.manager.prepare_retry_context(provenance, context_key, binding=binding)
        self.assertEqual(prepared['state'], 'starting')
        self.assertTrue(prepared['old_local_ended'])
        self.assertFalse(prepared['clean_context'])
        self.assertEqual(prepared['verification_basis'], 'same_turn_retry_relaunch')
        self.assertNotEqual(prepared['launch_attempt'], launch['attempt'])
        snapshot = snapshots[0]
        self.assertEqual(snapshot['seat']['model'], 'cli-original')
        self.assertEqual(snapshot['seat']['reasoning'], 'high')
        self.assertEqual(snapshot['provider']['cwd'], str(self.root.resolve()))
        self.assertEqual(snapshot['provider']['mcp_inject'], 'env')
        self.assertEqual(snapshot['provider']['mcp_env_var'], 'RESTART_TEST_SETTINGS')
        self.assertEqual(snapshot['provider']['cli_args'], ['fixture-original'])
        for field, value in {**binding, 'context_key': context_key}.items():
            self.assertEqual(snapshot[field], value)
        fresh = self.manager.attempts[prepared['key']]
        self.assertNotEqual(fresh['base'], self.manager.attempts['team/cli']['base'])
        fresh_instance = self.registry.register(fresh['base'])
        self.assertEqual(self.manager.fresh_context_owner(fresh_instance),
                         {**binding, 'context_key': context_key})
        self.assertNotEqual(fresh_instance['identity_id'], instance['identity_id'])
        self.assertEqual(self.manager.prepare_retry_context(provenance, context_key,
                         binding=binding)['state'], 'starting', 'registration alone is not ready')
        atomic_json(fresh['receipt'], {'attempt': fresh['id'], 'state': 'ready',
            'name': fresh_instance['name'], 'adapter_connected': True,
            'authentication': 'unknown', 'updated_at': time.time()})
        ready = self.manager.prepare_retry_context(provenance, context_key, binding=binding)
        self.assertEqual(ready['state'], 'ready')
        self.assertEqual(ready['identity_id'], fresh_instance['identity_id'])
        self.assertFalse(ready['clean_context'])
        self.assertEqual(ready['verification_basis'], 'same_turn_retry_relaunch')
        self.assertEqual(ready['launch_attempt'], prepared['launch_attempt'])
        self.assertEqual(len(self.processes), 2)

    def test_confirmed_generic_cleanup_preserves_unrelated_api_peer(self):
        peer, peer_launch = self.ready('api')
        _, launch, provenance = self.cli()
        old = self.manager.attempts['team/cli']
        def child_exit(timeout=None):
            self.ended(old)
            return 0
        old['process'].wait.side_effect = child_exit
        result = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex,
            confirmation={'launch_attempt': launch['attempt'], 'confirm': True})
        self.assertEqual(result['state'], 'starting')
        self.assertTrue(result['old_local_ended'])
        self.assertFalse(result['clean_context'])
        self.assertEqual(json.loads(old['snapshot'].with_name('stop.json').read_text('utf-8')),
                         {'attempt': launch['attempt']})
        old['process'].terminate.assert_not_called()
        self.processes[0].wait.assert_not_called()
        self.processes[0].terminate.assert_not_called()
        self.assertEqual(self.manager.inspect('team', 'api')['attempt'], peer_launch['attempt'])
        self.assertEqual(self.manager.launch_provenance(peer)['identity_id'], peer['identity_id'])
        self.assertEqual(len(self.processes), 3)

    def test_confirmed_worker_exit_without_child_proof_cannot_spawn(self):
        _, launch, provenance = self.cli()
        result = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex,
            confirmation={'launch_attempt': launch['attempt'], 'confirm': True})
        self.assertEqual(result['state'], 'blocked')
        self.assertFalse(result['old_local_ended'])
        self.assertEqual(len(self.processes), 1)

    def test_same_context_key_conflicts_with_different_frozen_settings(self):
        _, _, provenance = self.cli()
        self.ended(self.manager.attempts['team/cli'])
        context_key = uuid.uuid4().hex
        self.manager.prepare_retry_context(provenance, context_key)
        changed = copy.deepcopy(provenance)
        changed['effective']['seat']['model'] = 'another-model'
        changed['fingerprint'] = hashlib.sha256(json.dumps(changed['effective'],
            sort_keys=True).encode()).hexdigest()
        with self.assertRaises(SeatError):
            self.manager.prepare_retry_context(changed, context_key)
        self.assertEqual(len(self.processes), 2)

    def test_verified_retries_replace_nonce_instead_of_accumulating_selectors(self):
        self.store.providers['fake-cli'].update(cli_fresh_context_args=['--context-id', '{context_id}'],
                                              cli_fresh_context_verified=True)
        _, _, provenance = self.cli()
        self.ended(self.manager.attempts['team/cli'])
        first = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex)
        new_instance = self.register_ready(first)
        self.manager.prepare_retry_context(provenance, self.manager.attempts[first['key']]['context_key'])
        fresh_provenance = self.manager.launch_provenance(new_instance)
        self.assertIsNotNone(fresh_provenance)
        self.ended(self.manager.attempts[first['key']])
        second = self.manager.prepare_retry_context(fresh_provenance, uuid.uuid4().hex)
        self.assertNotEqual(first['context_id'], second['context_id'])
        snapshot = json.loads(self.manager.attempts[second['key']]['snapshot'].read_text('utf-8'))
        self.assertEqual(snapshot['provider']['cli_args'],
                         ['fixture-original', '--context-id', second['context_id']])
        self.assertNotIn(first['context_id'], snapshot['provider']['cli_args'])
        self.assertEqual(len(self.processes), 3)

    def test_stale_owned_launch_offer_blocks_without_side_effects(self):
        _, _, provenance = self.cli()
        stale = copy.deepcopy(provenance)
        stale['launch_attempt'] = uuid.uuid4().hex
        self.assertEqual(self.manager.retry_context_offer(stale)['state'], 'blocked')
        self.assertEqual(self.manager.retry_context_offer(None)['state'], 'blocked')
        self.assertEqual(len(self.processes), 1)
        self.processes[0].wait.assert_not_called()

    def test_failed_provider_receipt_reuses_live_api_but_not_disconnected_identity(self):
        instance, launch = self.ready('api')
        provenance = self.manager.launch_provenance(instance)
        attempt = self.manager.attempts['team/api']
        for state in ('failed', 'action_required'):
            with self.subTest(state=state):
                atomic_json(attempt['receipt'], {'attempt': launch['attempt'], 'state': state,
                    'name': instance['name'], 'adapter_connected': True,
                    'authentication': 'rejected', 'error': 'provider_failure', 'updated_at': time.time()})
                result = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex)
                self.assertEqual(result['identity_id'], instance['identity_id'])
                self.assertEqual(result['launch_attempt'], launch['attempt'])
                self.assertNotEqual(result['state'], 'blocked')
                receipt = json.loads(attempt['receipt'].read_text('utf-8'))
                self.assertEqual(receipt['state'], state)
                self.assertEqual(receipt['authentication'], 'rejected')
        self.registry.deregister(instance['name'])
        result = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex)
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(len(self.processes), 1)
        self.processes[0].wait.assert_not_called()

    def test_live_generic_retry_requires_confirmation_before_any_control_or_spawn(self):
        _, _, provenance = self.cli()
        result = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex)
        self.assertIn('confirmation_required', (result['state'], result.get('reason')))
        self.assertFalse(result.get('clean_context', False))
        self.assertEqual(len(self.processes), 1)
        self.processes[0].wait.assert_not_called()
        self.assertFalse(self.manager.attempts['team/cli']['snapshot'].with_name('stop.json').exists())

    def test_matching_api_supervisor_reuses_actual_owned_identity(self):
        instance, launch = self.ready('api')
        provenance = self.manager.launch_provenance(instance)
        result = self.manager.prepare_retry_context(provenance, uuid.uuid4().hex)
        self.assertEqual(result['state'], 'ready')
        self.assertEqual(result['identity_id'], instance['identity_id'])
        self.assertEqual(result['launch_attempt'], launch['attempt'])
        self.assertEqual(len(self.processes), 1)
        self.processes[0].wait.assert_not_called()


if __name__ == '__main__':
    unittest.main()
