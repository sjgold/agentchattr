"""yaml_settings_file MCP injection (Hermes): seat contract, wrapper apply and removal on stop.

Every test uses a temporary HERMES_HOME; no real Hermes configuration is read or written.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_seats import SeatError, validate_seat  # noqa: E402

TOKEN = 'tok_SECRET_feedfacecafebeef0123456789'
ORIGINAL = ('# Hermes settings\r\nmodel: hermes-3  # chosen\r\n\r\nmcp_servers:\r\n'
            '  agentchattr:\r\n    url: "http://127.0.0.1:8200/mcp"  # the real one\r\n'
            '\r\n# terminal next\r\nterminal:\r\n  backend: local\r\n')


def seat(**changes):
    return dict(id='hermes', name='Hermes', adapter='cli', provider='hermes', model=None,
                reasoning=None, secret_ref='', launch_profile='standard', **changes)


class HermesHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'hermes home'
        self.home.mkdir()
        self.config = self.home / 'config.yaml'
        patcher = patch.dict(os.environ, {'HERMES_HOME': str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.template = {'command': sys.executable, 'cwd': '.', 'mcp_inject': 'yaml_settings_file',
                         'mcp_settings_path': '$HERMES_HOME/config.yaml', 'mcp_transport': 'http'}


class SeatContractTests(HermesHome):
    def test_yaml_settings_file_is_a_supported_mode(self):
        from wrapper import _VALID_INJECT_MODES
        self.assertIn('yaml_settings_file', _VALID_INJECT_MODES)
        validate_seat(seat(), {'hermes': self.template})

    def test_missing_settings_path_is_rejected(self):
        with self.assertRaises(SeatError):
            validate_seat(seat(), {'hermes': {**self.template, 'mcp_settings_path': ''}})

    def test_config_resource_expands_hermes_home_like_the_writer(self):
        from cli_seats import config_resource
        self.assertEqual(config_resource(self.template, ROOT),
                         os.path.normcase(str(self.config.resolve())))

    def test_unset_home_variable_is_refused_not_guessed(self):
        from cli_seats import config_resource
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('HERMES_HOME', None)
            with self.assertRaises(SeatError):
                config_resource(self.template, ROOT)


class WrapperLifecycleTests(HermesHome):
    def setUp(self):
        super().setUp()
        import wrapper
        wrapper._reset_yaml_state()
        self.addCleanup(wrapper._reset_yaml_state)

    def apply(self, token=TOKEN):
        import wrapper
        return wrapper._apply_mcp_inject(self.template, 'hermes', Path(self.tmp.name) / 'data', None,
                                         token=token, mcp_cfg={'http_port': 49961}, project_dir=ROOT)

    def test_apply_adds_only_the_uat_entry_and_keeps_the_existing_one(self):
        import yaml
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        args, env, path = self.apply()
        self.assertEqual((args, env), ([], {}))
        self.assertEqual(Path(path), self.config)
        data = yaml.safe_load(self.config.read_text('utf-8'))
        self.assertEqual(data['mcp_servers']['agentchattr'], {'url': 'http://127.0.0.1:8200/mcp'})
        self.assertEqual(data['mcp_servers']['agentchattr-uat'],
                         {'url': 'http://127.0.0.1:49961/mcp', 'headers': {'Authorization': 'Bearer ' + TOKEN}})
        text = self.config.read_text('utf-8')
        self.assertIn('# the real one', text)
        self.assertIn('# terminal next', text)

    def test_stop_restores_exact_original_bytes_after_a_token_refresh(self):
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        self.apply(token=TOKEN + 'refreshed')           # re-registration rewrites the entry
        results = wrapper._remove_yaml_mcp_entries()
        self.assertEqual([r.status for r in results], ['restored-exact'])
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode('utf-8'))
        backups = list(self.home.glob('config.yaml.agentchattr-uat-*.bak'))
        self.assertEqual(len(backups), 1)                # the refresh made no second backup
        self.assertNotIn(TOKEN.encode(), backups[0].read_bytes())

    def test_user_edit_before_a_refresh_survives_stop(self):
        # Reviewer B2: the first backup must not be paired with a later write when the user
        # edited the file in between, or stop would restore the stale backup over the edit.
        import wrapper
        import yaml
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        edited = self.config.read_bytes().replace(b'backend: local', b'backend: docker')
        self.config.write_bytes(edited)
        self.apply(token=TOKEN + 'refreshed')
        results = wrapper._remove_yaml_mcp_entries()
        self.assertEqual([r.status for r in results], ['removed-entry'])
        data = yaml.safe_load(self.config.read_text('utf-8'))
        self.assertEqual(data['terminal'], {'backend': 'docker'})
        self.assertNotIn('agentchattr-uat', data['mcp_servers'])
        self.assertEqual(self.config.read_bytes(), ORIGINAL.replace('backend: local', 'backend: docker').encode('utf-8'))

    def test_user_edit_to_a_created_file_before_a_refresh_keeps_the_file(self):
        import wrapper
        import yaml
        self.apply()
        self.config.write_bytes(self.config.read_bytes() + b'model: mine\n')
        self.apply(token=TOKEN + 'refreshed')
        wrapper._remove_yaml_mcp_entries()
        self.assertTrue(self.config.exists())
        self.assertEqual(yaml.safe_load(self.config.read_text('utf-8')).get('model'), 'mine')
        self.assertNotIn(TOKEN.encode(), self.config.read_bytes())

    def test_refresh_that_recreates_a_user_deleted_file_deletes_it_at_stop(self):
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        self.config.unlink()
        self.apply(token=TOKEN + 'refreshed')
        self.assertEqual([r.status for r in wrapper._remove_yaml_mcp_entries()], ['deleted-created-file'])
        self.assertFalse(self.config.exists())

    def test_a_print_that_raises_cannot_lose_the_receipt(self):
        import io
        import wrapper

        class Unprintable(io.StringIO):
            def write(self, _text):
                raise UnicodeEncodeError('cp1252', 'x', 0, 1, 'unmappable')
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        with patch('sys.stdout', Unprintable()):
            self.apply()
        self.assertEqual(len(wrapper._YAML_RECEIPTS), 1)
        wrapper._remove_yaml_mcp_entries()
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode('utf-8'))

    def test_late_reregistration_after_removal_cannot_write_the_entry_back(self):
        # Reviewer must-fix 1: the heartbeat thread may re-register (409) after the stop
        # hook removed our entry; that rewrite must not put the entry and token back.
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        wrapper._remove_yaml_mcp_entries()
        with self.assertRaises(ValueError):
            self.apply(token=TOKEN + 'late')
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode('utf-8'))

    def test_stop_hook_does_not_import_the_yaml_module_for_other_modes(self):
        # Reviewer must-fix 3: non-YAML modes are byte-for-byte unaffected.
        import wrapper
        sys.modules.pop('yaml_mcp_settings', None)
        with patch.dict(sys.modules, {'yaml_mcp_settings': None}):   # any import would now fail
            self.assertEqual(wrapper._remove_yaml_mcp_entries(), [])

    def test_stop_hook_survives_unexpected_errors(self):
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        with patch('yaml_mcp_settings.remove_exact', side_effect=RuntimeError('boom ' + TOKEN)):
            out = __import__('io').StringIO()
            with patch('sys.stdout', out):
                self.assertEqual(wrapper._remove_yaml_mcp_entries(), [])
        self.assertNotIn(TOKEN, out.getvalue())

    def test_stop_with_nothing_applied_is_a_no_op(self):
        import wrapper
        wrapper._YAML_RECEIPTS.clear()
        self.assertEqual(wrapper._remove_yaml_mcp_entries(), [])

    def test_unset_hermes_home_fails_before_any_write(self):
        import wrapper
        os.environ.pop('HERMES_HOME', None)
        with self.assertRaises(ValueError):
            self.apply()
        self.assertFalse(self.config.exists())


if __name__ == '__main__':
    unittest.main()
