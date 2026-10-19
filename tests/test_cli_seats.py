import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from api_seats import SeatError, SeatStore, validate_seat


def seat(**changes):
    return dict(id='writer', name='Writer', adapter='cli', provider='fake', model='chosen',
                reasoning='high', secret_ref='', launch_profile='standard', **changes)


class CliSeatTests(unittest.TestCase):
    def setUp(self):
        self.template = {'command': sys.executable, 'cwd': '.',
                         'cli_model_args': ['--model', '{model}'],
                         'cli_reasoning_args': ['--effort', '{reasoning}'],
                         'reasoning_efforts': ['high'], 'mcp_inject': 'env',
                         'mcp_env_var': 'FAKE_SETTINGS'}

    def test_mixed_package_roundtrip_preserves_api_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SeatStore(directory, {'fake': self.template})
            package = {'id': 'team', 'name': 'Team', 'seats': [seat()]}
            self.assertEqual(store.save(package), package)
            self.assertEqual(store.list(), [package])
            self.assertEqual(store.describe_providers()[0]['adapter'], 'cli')

    def test_declared_settings_reach_separate_argv(self):
        from cli_seats import build_cli_args
        self.assertEqual(build_cli_args(seat(), self.template), ['--model', 'chosen', '--effort', 'high'])
        value = seat()
        value.update(model=None, reasoning=None)
        self.assertEqual(build_cli_args(value, self.template), [])

    def test_unsupported_setting_fails_instead_of_being_ignored(self):
        for removed in ('cli_model_args', 'cli_reasoning_args', 'reasoning_efforts'):
            cfg = {k: v for k, v in self.template.items() if k != removed}
            with self.subTest(removed=removed), self.assertRaises(SeatError):
                validate_seat(seat(), {'fake': cfg})

    def test_unknown_identity_injection_contract_is_rejected(self):
        with self.assertRaises(SeatError):
            validate_seat(seat(), {'fake': {**self.template, 'mcp_inject': 'unknown'}})

    def test_all_nonmap_settings_shapes_remain_unchanged(self):
        from wrapper import _write_json_mcp_settings
        shapes = [None, [], False, 'text', {'mcpServers': []}, {'security': []},
                  {'security': {'folderTrust': []}}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            for value in shapes:
                original = json.dumps(value).encode('utf-8')
                path.write_bytes(original)
                with self.subTest(value=value), self.assertRaises(ValueError):
                    _write_json_mcp_settings(path, 'http://127.0.0.1:8200/mcp')
                self.assertEqual(path.read_bytes(), original)

    def test_native_login_seat_rejects_saved_secret_values(self):
        value = seat()
        value['secret_ref'] = 'a-literal-secret'
        with self.assertRaises(SeatError):
            validate_seat(value, {'fake': self.template})

    def test_unexpanded_or_ambiguous_argument_templates_rejected(self):
        from cli_seats import build_cli_args
        for mapping in (['--model'], ['{unknown}'], '--model {model}', ['{model}', '{model}']):
            with self.subTest(mapping=mapping), self.assertRaises(SeatError):
                build_cli_args(seat(), {**self.template, 'cli_model_args': mapping})

    def test_fixed_config_resource_is_canonical_and_env_mode_is_private(self):
        from cli_seats import config_resource
        with tempfile.TemporaryDirectory() as directory:
            cfg = {**self.template, 'mcp_inject': 'settings_file', 'mcp_settings_path': '.fake/settings.json'}
            self.assertEqual(config_resource(cfg, Path(directory)), os.path.normcase(str((Path(directory) / '.fake/settings.json').resolve())))
            self.assertIsNone(config_resource(self.template, Path(directory)))

    def test_owned_cli_launch_uses_cli_worker_and_keeps_snapshot_immutable(self):
        from api_seat_runtime import SeatManager
        from registry import RuntimeRegistry
        with tempfile.TemporaryDirectory() as directory:
            store = SeatStore(directory, {'fake': self.template})
            package = {'id': 'team', 'name': 'Team', 'seats': [seat()]}
            store.save(package)
            manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, store,
                                  RuntimeRegistry(directory), monitor=False)
            process = Mock()
            process.poll.return_value = None
            with patch('api_seat_runtime.subprocess.Popen', return_value=process) as spawn:
                manager.launch('team', 'writer')
                self.assertTrue(any(str(a).endswith('cli_worker.py') for a in spawn.call_args.args[0]))
                attempt = manager.attempts['team/writer']
                frozen = attempt['snapshot'].read_bytes()
                package['seats'][0]['model'] = 'edited'
                manager.save(package)
                self.assertEqual(attempt['snapshot'].read_bytes(), frozen)
                with self.assertRaises(SeatError):
                    manager.launch('team', 'writer')

    def test_fixed_config_conflict_is_rejected_before_second_spawn(self):
        from api_seat_runtime import SeatManager
        from registry import RuntimeRegistry
        with tempfile.TemporaryDirectory() as directory:
            template = {**self.template, 'cwd': directory, 'mcp_inject': 'settings_file',
                        'mcp_settings_path': 'shared.json'}
            store = SeatStore(directory, {'fake': template})
            first = seat()
            second = {**first, 'id': 'second'}
            store.save({'id': 'team', 'name': 'Team', 'seats': [first, second]})
            manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, store,
                                  RuntimeRegistry(directory), monitor=False)
            process = Mock()
            process.poll.return_value = None
            with patch('api_seat_runtime.subprocess.Popen', return_value=process) as spawn:
                manager.launch('team', 'writer')
                with self.assertRaises(SeatError):
                    manager.launch('team', 'second')
                self.assertEqual(spawn.call_count, 1)

    def test_missing_executable_is_action_needed_without_spawn(self):
        from api_seat_runtime import SeatManager
        from registry import RuntimeRegistry
        with tempfile.TemporaryDirectory() as directory:
            store = SeatStore(directory, {'fake': {**self.template, 'command': 'missing-ticket4-command'}})
            store.save({'id': 'team', 'name': 'Team', 'seats': [seat()]})
            manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, store,
                                  RuntimeRegistry(directory), monitor=False)
            with patch('api_seat_runtime.subprocess.Popen') as spawn:
                result = manager.launch('team', 'writer')
                self.assertEqual(result['state'], 'action_required')
                self.assertIsNone(result['executable'])
                self.assertFalse(result['startup_checked'])
                spawn.assert_not_called()

    def test_exact_cli_exit_and_unknown_auth_survive_worker_exit(self):
        from api_seat_runtime import SeatManager
        from api_seats import atomic_json
        from registry import RuntimeRegistry
        with tempfile.TemporaryDirectory() as directory:
            store = SeatStore(directory, {'fake': self.template})
            store.save({'id': 'team', 'name': 'Team', 'seats': [seat()]})
            manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, store,
                                  RuntimeRegistry(directory), monitor=False)
            process = Mock()
            process.poll.return_value = None
            with patch('api_seat_runtime.subprocess.Popen', return_value=process):
                manager.launch('team', 'writer')
            attempt = manager.attempts['team/writer']
            atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'failed',
                        'child_exit_code': 23, 'error': 'CLI exited with code 23.'})
            process.poll.return_value = 23
            process.returncode = 23
            result = manager.inspect('team', 'writer')
            self.assertEqual(result['child_exit_code'], 23)
            self.assertEqual(result['state'], 'failed')
            self.assertEqual(result['authentication'], 'unknown')
            self.assertIsNone(result['confirmed_model'])


if __name__ == '__main__':
    unittest.main()
