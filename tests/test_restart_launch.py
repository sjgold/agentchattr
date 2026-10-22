"""Declared clean CLI capability and immutable owned managed-launch provenance."""
import importlib
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


class RestartLaunchTests(unittest.TestCase):
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

    def test_verified_fresh_context_contract_builds_explicit_argv(self):
        build = importlib.import_module('cli_seats').build_fresh_context_args
        template = {'cli_fresh_context_args': ['--context-id', '{context_id}'], 'cli_fresh_context_verified': True}
        context_id = uuid.uuid4().hex
        self.assertEqual(build(template, context_id), ['--context-id', context_id])
        self.assertEqual(build(template, 'a' * 128), ['--context-id', 'a' * 128])

    def test_unverified_or_missing_cli_contract_is_unsupported(self):
        build = importlib.import_module('cli_seats').build_fresh_context_args
        for value in (None, False, 0, 1, 'true'):
            with self.subTest(verified=value), self.assertRaisesRegex(SeatError, 'unsupported_clean_context'):
                build({'cli_fresh_context_args': ['--context-id', '{context_id}'],
                       'cli_fresh_context_verified': value}, uuid.uuid4().hex)
        with self.assertRaisesRegex(SeatError, 'unsupported_clean_context'):
            build({}, uuid.uuid4().hex)

    def test_owned_api_provenance_is_json_safe_and_excludes_bearer_and_credential(self):
        instance, launch = self.ready('api')
        provenance = self.manager.launch_provenance(instance)
        self.assertEqual(provenance['key'], 'team/api')
        self.assertEqual(provenance['launch_attempt'], launch['attempt'])
        self.assertEqual(provenance['identity_id'], instance['identity_id'])
        self.assertEqual(provenance['effective']['seat']['model'], 'api-original')
        self.assertEqual(provenance['effective']['provider']['base_url'], self.providers['fake-api']['base_url'])
        self.assertEqual(provenance['effective']['provider']['system_prompt'], 'Original API instruction')
        serialized = json.dumps(provenance, allow_nan=False)
        self.assertIn('RESTART_TEST_KEY', serialized)
        self.assertNotIn('credential-value-test-only', serialized)
        self.assertNotIn(instance['token'], serialized)
        self.assertRegex(provenance['fingerprint'], r'^[0-9a-f]{64}$')

    def test_unsupported_cli_preparation_never_stops_or_spawns_even_with_confirmation(self):
        instance, launch = self.ready('cli')
        provenance = self.manager.launch_provenance(instance)
        result = self.manager.prepare_clean_context(provenance, uuid.uuid4().hex,
            confirmation={'launch_attempt': launch['attempt'], 'confirm': True})
        self.assertEqual(result['state'], 'blocked')
        self.assertIn('unsupported_clean_context', json.dumps(result))
        self.assertEqual(len(self.processes), 1)
        self.processes[0].terminate.assert_not_called()
        self.processes[0].wait.assert_not_called()
        self.assertEqual(self.manager.inspect('team', 'cli')['attempt'], launch['attempt'])

    def test_fresh_mapping_rejects_ambiguous_formatting_and_non_argument_shapes(self):
        build = importlib.import_module('cli_seats').build_fresh_context_args
        invalid = (None, '--context-id {context_id}', [], ['--context-id'],
                   ['{context_id}', '{context_id}'], ['{other}'], ['{context_id!r}'],
                   ['{context_id:>8}'], ['{context_id.member}'], ['{context_id'],
                   [42, '{context_id}'], ['\x00{context_id}'])
        for mapping in invalid:
            with self.subTest(mapping=mapping), self.assertRaises(SeatError):
                build({'cli_fresh_context_args': mapping, 'cli_fresh_context_verified': True}, uuid.uuid4().hex)

    def test_context_identifier_rejects_non_plain_or_oversize_values(self):
        build = importlib.import_module('cli_seats').build_fresh_context_args
        template = {'cli_fresh_context_args': ['--context-id', '{context_id}'], 'cli_fresh_context_verified': True}
        for invalid in (None, '', 'a' * 129, '../escape', 'two words', 'line\nbreak', '日本語', '{value}'):
            with self.subTest(context_id=invalid), self.assertRaises(SeatError):
                build(template, invalid)

    def test_api_provenance_and_clean_reuse_ignore_saved_and_template_drift(self):
        instance, launch = self.ready('api')
        original = self.manager.launch_provenance(instance)
        self.assertEqual(original['fingerprint'], self.manager.attempts['team/api']['fingerprint'])
        self.package['seats'][0]['model'] = 'edited-saved-model'
        self.store.providers['fake-api'].update(base_url='http://127.0.0.1:19998/v1',
            system_prompt='Edited live instruction', temperature=1.2)
        self.manager.save(self.package)
        self.assertEqual(self.manager.launch_provenance(instance), original)
        result = self.manager.prepare_clean_context(original, uuid.uuid4().hex)
        self.assertEqual(result['state'], 'ready')
        self.assertTrue(result['clean_context'])
        self.assertEqual(result['identity_id'], instance['identity_id'])
        self.assertEqual(result['launch_attempt'], launch['attempt'])
        self.assertEqual(len(self.processes), 1, 'API clean requests must reuse the original owned supervisor')
        self.processes[0].terminate.assert_not_called()
        self.processes[0].wait.assert_not_called()
        self.assertEqual(self.manager.launch_provenance(instance), original)

    def test_cli_provenance_preserves_actual_args_cwd_mcp_model_and_reasoning(self):
        instance, launch = self.ready('cli')
        original = self.manager.launch_provenance(instance)
        effective = original['effective']
        self.assertEqual(effective['seat']['model'], 'cli-original')
        self.assertEqual(effective['seat']['reasoning'], 'high')
        self.assertEqual(effective['provider']['cli_args'], ['fixture-original'])
        self.assertEqual(effective['provider']['cwd'], str(self.root.resolve()))
        self.assertEqual(effective['provider']['mcp_inject'], 'env')
        self.assertEqual(effective['provider']['mcp_env_var'], 'RESTART_TEST_SETTINGS')
        self.package['seats'][1]['model'] = 'edited-cli-model'
        self.store.providers['fake-cli'].update(cli_args=['edited-argument'], cwd=str(ROOT),
                                               mcp_env_var='EDITED_SETTINGS')
        self.manager.save(self.package)
        self.assertEqual(self.manager.launch_provenance(instance), original)
        original['effective']['provider']['cli_args'].append('caller-mutation')
        original['effective']['seat']['model'] = 'caller-model'
        saved = self.manager.launch_provenance(instance)
        self.assertEqual(saved['effective']['provider']['cli_args'], ['fixture-original'])
        self.assertEqual(saved['effective']['seat']['model'], 'cli-original')
        self.assertEqual(saved['launch_attempt'], launch['attempt'])
        self.assertNotIn(instance['token'], json.dumps(saved))

    def test_unowned_replaced_and_stale_identity_have_no_launch_provenance(self):
        instance, _ = self.ready('api')
        self.registry.seed({'unowned': {'label': 'External identity'}})
        external = self.registry.register('unowned')
        self.assertIsNone(self.manager.launch_provenance(external))
        self.assertIsNone(self.manager.launch_provenance({**instance, 'identity_id': uuid.uuid4().hex}))
        original_base = self.manager.attempts['team/api']['base']
        self.registry.deregister(instance['name'])
        replacement = self.registry.register(original_base)
        self.assertNotEqual(replacement['identity_id'], instance['identity_id'])
        self.assertIsNone(self.manager.launch_provenance(replacement))
        self.assertIsNone(self.manager.launch_provenance(instance))

    def test_declared_but_unverified_cli_remains_blocked_without_side_effects(self):
        self.store.providers['fake-cli'].update(cli_fresh_context_args=['--context-id', '{context_id}'],
                                              cli_fresh_context_verified=False)
        instance, launch = self.ready('cli')
        provenance = self.manager.launch_provenance(instance)
        for confirmation in (None, {'launch_attempt': launch['attempt'], 'confirm': True}):
            with self.subTest(confirmation=confirmation):
                result = self.manager.prepare_clean_context(provenance, uuid.uuid4().hex, confirmation=confirmation)
                self.assertEqual(result['state'], 'blocked')
                self.assertIn('unsupported_clean_context', json.dumps(result))
        self.assertEqual(len(self.processes), 1)
        self.processes[0].terminate.assert_not_called()
        self.processes[0].wait.assert_not_called()

    def verified_cli(self):
        self.store.providers['fake-cli'].update(cli_fresh_context_args=['--context-id', '{context_id}'],
                                              cli_fresh_context_verified=True)
        instance, launched = self.ready('cli')
        return instance, launched, self.manager.launch_provenance(instance)

    def test_live_verified_cli_requires_exact_confirmation_without_side_effects(self):
        instance, launch, provenance = self.verified_cli()
        result = self.manager.prepare_clean_context(provenance, uuid.uuid4().hex)
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(result['reason'], 'confirmation_required')
        self.assertFalse(result['clean_context'])
        attempt = self.manager.attempts['team/cli']
        self.assertFalse(attempt['snapshot'].with_name('stop.json').exists())
        self.assertEqual(len(self.processes), 1)
        self.processes[0].wait.assert_not_called()
        self.processes[0].terminate.assert_not_called()

    def test_stale_verified_cli_confirmation_is_rejected_before_control_or_spawn(self):
        instance, launch, provenance = self.verified_cli()
        with self.assertRaises(SeatError):
            self.manager.prepare_clean_context(provenance, uuid.uuid4().hex,
                confirmation={'launch_attempt': uuid.uuid4().hex, 'confirm': True})
        attempt = self.manager.attempts['team/cli']
        self.assertFalse(attempt['snapshot'].with_name('stop.json').exists())
        self.assertEqual(len(self.processes), 1)
        self.processes[0].wait.assert_not_called()
        self.processes[0].terminate.assert_not_called()

    def test_proven_ended_cli_launches_frozen_fresh_context_then_reuses_prepared_attempt(self):
        instance, launch, provenance = self.verified_cli()
        old = self.manager.attempts['team/cli']
        old['process'].poll.return_value = 0
        old['process'].returncode = 0
        atomic_json(old['receipt'], {'attempt': launch['attempt'], 'state': 'stopped',
                    'name': instance['name'], 'child_exit_code': 0, 'adapter_connected': False,
                    'authentication': 'unknown', 'updated_at': time.time()})
        self.manager.inspect('team', 'cli')
        self.package['seats'][1]['model'] = 'edited-model-must-not-launch'
        self.store.providers['fake-cli'].update(cli_args=['edited-args-must-not-launch'],
            mcp_env_var='EDITED_SETTINGS', cwd=str(ROOT), cli_fresh_context_verified=False)
        self.manager.save(self.package)
        context_key = uuid.uuid4().hex
        prepared = self.manager.prepare_clean_context(provenance, context_key)
        self.assertEqual(prepared['state'], 'starting')
        self.assertFalse(prepared['clean_context'], 'spawn alone does not establish a clean ready identity')
        self.assertNotEqual(prepared['launch_attempt'], launch['attempt'])
        self.assertEqual(len(self.processes), 2)
        fresh = self.manager.attempts[prepared['key']]
        snapshot = json.loads(fresh['snapshot'].read_text('utf-8'))
        self.assertEqual(snapshot['seat']['model'], 'cli-original')
        self.assertEqual(snapshot['seat']['reasoning'], 'high')
        self.assertEqual(snapshot['provider']['cwd'], str(self.root.resolve()))
        self.assertEqual(snapshot['provider']['mcp_env_var'], 'RESTART_TEST_SETTINGS')
        self.assertEqual(snapshot['provider']['cli_args'],
                         ['fixture-original', '--context-id', prepared['context_id']])
        self.assertRegex(prepared['context_id'], r'^[A-Za-z0-9_.-]{1,128}$')
        repeated = self.manager.prepare_clean_context(provenance, context_key)
        self.assertEqual(repeated['launch_attempt'], prepared['launch_attempt'])
        self.assertEqual(repeated['context_id'], prepared['context_id'])
        self.assertEqual(len(self.processes), 2)
        new_identity = self.registry.register(fresh['base'])
        atomic_json(fresh['receipt'], {'attempt': prepared['launch_attempt'], 'state': 'ready',
            'name': new_identity['name'], 'adapter_connected': True, 'authentication': 'unknown',
            'confirmed_model': None, 'updated_at': time.time()})
        ready = self.manager.prepare_clean_context(provenance, context_key)
        self.assertEqual(ready['state'], 'ready')
        self.assertTrue(ready['clean_context'])
        self.assertEqual(ready['identity_id'], new_identity['identity_id'])
        self.assertNotEqual(ready['identity_id'], instance['identity_id'])
        self.assertEqual(ready['launch_attempt'], prepared['launch_attempt'])
        self.assertEqual(len(self.processes), 2)

    def test_worker_exit_without_matching_stopped_child_receipt_is_not_clean(self):
        instance, launch, provenance = self.verified_cli()
        old = self.manager.attempts['team/cli']
        old['process'].poll.return_value = 0
        old['process'].returncode = 0
        # Existing receipt still says ready and contains no child-exit proof.
        result = self.manager.prepare_clean_context(provenance, uuid.uuid4().hex)
        self.assertEqual(result['state'], 'blocked')
        self.assertFalse(result['clean_context'])
        self.assertEqual(len(self.processes), 1)

    def test_confirmed_cleanup_targets_only_original_cli_and_preserves_api_peer(self):
        peer, peer_launch = self.ready('api')
        instance, launch, provenance = self.verified_cli()
        old = self.manager.attempts['team/cli']
        def actual_child_end(timeout=None):
            atomic_json(old['receipt'], {'attempt': launch['attempt'], 'state': 'stopped',
                'name': instance['name'], 'child_exit_code': 0, 'adapter_connected': False,
                'authentication': 'unknown', 'updated_at': time.time()})
            old['process'].poll.return_value = 0
            old['process'].returncode = 0
            return 0
        old['process'].wait.side_effect = actual_child_end
        prepared = self.manager.prepare_clean_context(provenance, uuid.uuid4().hex,
            confirmation={'launch_attempt': launch['attempt'], 'confirm': True})
        self.assertEqual(prepared['state'], 'starting')
        self.assertNotEqual(prepared['launch_attempt'], launch['attempt'])
        self.assertEqual(json.loads(old['snapshot'].with_name('stop.json').read_text('utf-8')),
                         {'attempt': launch['attempt']})
        old['process'].wait.assert_called()
        old['process'].terminate.assert_not_called()
        self.assertEqual(len(self.processes), 3)
        self.processes[0].wait.assert_not_called()
        self.processes[0].terminate.assert_not_called()
        self.assertEqual(self.manager.inspect('team', 'api')['attempt'], peer_launch['attempt'])
        self.assertEqual(self.manager.inspect('team', 'api')['state'], 'ready')
        self.assertEqual(self.manager.launch_provenance(peer)['identity_id'], peer['identity_id'])


if __name__ == '__main__':
    unittest.main()
