"""Result-seal metadata from real managed stores and process doubles only."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import SeatError
from tests import test_restart_launch as fixture


class ResultOwnerTests(unittest.TestCase):
    def setUp(self):
        # Explicit setup reuse, not inherited duplicate test execution. Real
        # SeatManager/SeatStore/Registry, distinct Popen doubles, no native birth.
        fixture.RestartLaunchTests.setUp(self)
        # Included by the actual immutable effective launch, intentionally
        # excluded from sanitized launch_provenance. Distinguish hash sources
        # without assuming their values universally differ for simple settings.
        self.manager.config['server']['fixture_marker'] = 'original'
        self.dispatch = uuid.uuid4().hex

    def ready(self, seat='api'):
        return fixture.RestartLaunchTests.ready(self, seat)

    def test_ready_owned_api_returns_exact_runtime_ownership_scope(self):
        instance, launched = self.ready()
        attempt = self.manager.attempts['team/api']
        snapshot = json.loads(attempt['snapshot'].read_text('utf-8'))
        expected = {'adapter': 'openai-compatible', 'dispatch_id': self.dispatch,
                    'seat_identity_id': instance['identity_id'], 'launch_attempt': launched['attempt'],
                    'launch_nonce': snapshot['ownership']['launch_nonce'], 'fingerprint': snapshot['ownership']['fingerprint']}
        self.assertEqual(self.manager.result_owner(instance, self.dispatch), expected)
        self.assertEqual(expected['fingerprint'], attempt['ownership']['fingerprint'])
        self.assertNotEqual(expected['fingerprint'], self.manager.launch_provenance(instance)['fingerprint'])

    def test_invalid_dispatch_is_rejected_before_any_owner_lookup_or_mutation(self):
        for identifier in (None, True, 7, '', 'a' * 31, 'A' * 32, '../escape'):
            with self.subTest(identifier=identifier), self.assertRaises(SeatError):
                self.manager.result_owner(None, identifier)
        self.spawn.assert_not_called()
        self.assertEqual(self.manager.attempts, {})

    def files(self):
        return {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}

    def assert_no_control(self):
        for process in self.processes:
            process.terminate.assert_not_called()
            process.kill.assert_not_called()
            process.wait.assert_not_called()

    def test_public_scope_is_copy_only_secret_free_and_queries_never_spawn_or_control(self):
        instance, launched = self.ready()
        public = self.registry.resolve_token(instance['token'])
        before, identities = self.files(), deepcopy(self.registry.get_all())
        calls = self.spawn.call_count
        first = self.manager.result_owner(public, self.dispatch)
        serialized = json.dumps(first, allow_nan=False)
        for excluded in (instance['token'], 'credential-value-test-only', 'RESTART_TEST_KEY', 'Original API instruction',
                         self.providers['fake-api']['base_url']):
            self.assertNotIn(excluded, serialized)
        first['launch_nonce'] = '0' * 32
        first['seat_identity_id'] = '0' * 32
        current = self.manager.result_owner(public, self.dispatch)
        self.assertEqual(current['seat_identity_id'], instance['identity_id'])
        self.assertNotEqual(current['launch_nonce'], first['launch_nonce'])
        self.assertEqual(current['launch_attempt'], launched['attempt'])
        self.assertEqual(self.files(), before)
        self.assertEqual(self.registry.get_all(), identities)
        self.assertEqual(self.spawn.call_count, calls)
        self.assert_no_control()
        self.assertFalse(self.manager.attempts['team/api']['snapshot'].with_name('birth.json').exists())

    def test_cli_manual_unowned_released_and_dead_instances_have_no_result_owner(self):
        cli, _ = self.ready('cli')
        self.registry.seed({'manual-api': {'type': 'api'}})
        manual = self.registry.register('manual-api')
        owner, _ = self.ready()
        attempt = self.manager.attempts['team/api']
        before, identities = self.files(), deepcopy(self.registry.get_all())
        for instance in (None, {}, cli, manual, {**owner, 'identity_id': uuid.uuid4().hex}):
            with self.subTest(instance_type=type(instance).__name__):
                self.assertIsNone(self.manager.result_owner(instance, self.dispatch))
        attempt['released'] = True
        try:
            self.assertIsNone(self.manager.result_owner(owner, self.dispatch))
        finally:
            attempt['released'] = False
        attempt['process'].poll.return_value = 7
        try:
            self.assertIsNone(self.manager.result_owner(owner, self.dispatch))
        finally:
            attempt['process'].poll.return_value = None
        self.assertEqual(self.files(), before)
        self.assertEqual(self.registry.get_all(), identities)
        self.assertEqual(self.spawn.call_count, 2)
        self.assert_no_control()

    def test_replacement_at_same_owned_base_cannot_inherit_original_result_authority(self):
        original, _ = self.ready()
        self.registry.deregister(original['name'])
        replacement = self.registry.register(original['base'])
        self.assertNotEqual(replacement['identity_id'], original['identity_id'])
        before, identities = self.files(), deepcopy(self.registry.get_all())
        for instance in (original, replacement):
            self.assertIsNone(self.manager.result_owner(instance, self.dispatch))
        self.assertEqual(self.files(), before)
        self.assertEqual(self.registry.get_all(), identities)
        self.assertEqual(self.spawn.call_count, 1)
        self.assert_no_control()

    def test_saved_and_provider_edits_do_not_rebind_original_runtime_owner(self):
        instance, _ = self.ready()
        owner = self.manager.result_owner(instance, self.dispatch)
        self.package['seats'][0]['model'] = 'edited-saved-model'
        self.store.save(self.package)
        self.store.providers['fake-api'].update(system_prompt='Edited provider instruction', base_url='http://127.0.0.1:19990/v1')
        before = self.files()
        self.assertEqual(self.manager.result_owner(instance, self.dispatch), owner)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.spawn.call_count, 1)
        self.assert_no_control()

    def test_changed_snapshot_intent_or_approved_configuration_is_refused_read_only(self):
        instance, _ = self.ready()
        attempt = self.manager.attempts['team/api']
        snapshot_path, intent_path = attempt['snapshot'], attempt['snapshot'].with_name('launch.json')
        for path, mutations in ((snapshot_path, (
                lambda value: value['ownership'].update(launch_nonce='a' * 32),
                lambda value: value['ownership'].update(root_path=str(self.root)),
                lambda value: value['provider'].update(system_prompt='Changed disk prompt'),
                lambda value: value['seat'].update(model='changed-disk-model'))),
                (intent_path, (lambda value: value.update(launch_nonce='b' * 32),
                               lambda value: value.update(fingerprint='c' * 64)))):
            original = path.read_bytes()
            for mutate in mutations:
                value = json.loads(original)
                mutate(value)
                path.write_text(json.dumps(value), encoding='utf-8')
                before, identities = self.files(), deepcopy(self.registry.get_all())
                try:
                    with self.subTest(file=path.name, value=value), self.assertRaises(SeatError):
                        self.manager.result_owner(instance, self.dispatch)
                    self.assertEqual(self.files(), before)
                    self.assertEqual(self.registry.get_all(), identities)
                finally:
                    path.write_bytes(original)
        original_config = deepcopy(self.manager.config)
        original_root = self.manager.root
        for mutate in (lambda: self.manager.config['server'].update(port=18399),
                       lambda: self.manager.config.update(mcp={'http_port': 18391, 'sse_port': 18392}),
                       lambda: setattr(self.manager, 'root', self.root)):
            try:
                mutate()
                before = self.files()
                with self.assertRaises(SeatError):
                    self.manager.result_owner(instance, self.dispatch)
                self.assertEqual(self.files(), before)
            finally:
                self.manager.config = deepcopy(original_config)
                self.manager.root = original_root
        self.assertEqual(self.spawn.call_count, 1)
        self.assert_no_control()


if __name__ == '__main__':
    unittest.main()
