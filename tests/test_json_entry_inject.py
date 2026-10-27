"""json_entry_file MCP injection (Antigravity agy): seat contract, wrapper apply and removal on stop.

Every test uses a temporary HOME/USERPROFILE; no real ~/.gemini configuration is read or written.
"""
import io
import json
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
ORIGINAL = ('{\r\n    "mcpServers": {\r\n        "agentchattr": {\r\n'
            '            "serverURL": "http://127.0.0.1:8200/mcp"\r\n        }\r\n    },\r\n'
            '    "zeta": [1, 2.5, true, null],\r\n    "alpha": {"nested": "keep"}\r\n}\r\n')


def seat(**changes):
    return dict(id='agy', name='Antigravity', adapter='cli', provider='agy', model=None,
                reasoning=None, secret_ref='', launch_profile='standard', **changes)


class AgyHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'user home'
        self.dir = self.home / '.gemini' / 'config'
        self.dir.mkdir(parents=True)
        self.config = self.dir / 'mcp_config.json'
        patcher = patch.dict(os.environ, {'HOME': str(self.home), 'USERPROFILE': str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.template = {'command': sys.executable, 'cwd': '.', 'mcp_inject': 'json_entry_file',
                         'mcp_settings_path': '~/.gemini/config/mcp_config.json', 'mcp_transport': 'http',
                         'mcp_http_key': 'serverURL'}


class SeatContractTests(AgyHome):
    def test_json_entry_file_is_a_supported_mode(self):
        from wrapper import _VALID_INJECT_MODES
        self.assertIn('json_entry_file', _VALID_INJECT_MODES)
        validate_seat(seat(), {'agy': self.template})

    def test_missing_settings_path_is_rejected(self):
        with self.assertRaises(SeatError):
            validate_seat(seat(), {'agy': {**self.template, 'mcp_settings_path': ''}})

    def test_the_users_own_entry_name_is_refused(self):
        for name in ('agentchattr', 'AgentChattr', ''):
            with self.subTest(name=name), self.assertRaises(SeatError):
                validate_seat(seat(), {'agy': {**self.template, 'mcp_entry_name': name}})

    def test_config_resource_expands_home_like_the_writer(self):
        from cli_seats import config_resource
        self.assertEqual(config_resource(self.template, ROOT),
                         os.path.normcase(str(self.config.resolve())))


class WrapperLifecycleTests(AgyHome):
    def setUp(self):
        super().setUp()
        import wrapper
        wrapper._reset_json_state()
        self.addCleanup(wrapper._reset_json_state)
        self.addCleanup(wrapper._reset_yaml_state)

    def apply(self, token=TOKEN, template=None):
        import wrapper
        return wrapper._apply_mcp_inject(template or self.template, 'agy', Path(self.tmp.name) / 'data', None,
                                         token=token, mcp_cfg={'http_port': 49961}, project_dir=ROOT)

    def test_apply_adds_only_the_fork_entry_and_keeps_everything_else(self):
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        args, env, path = self.apply()
        self.assertEqual((args, env), ([], {}))
        self.assertEqual(Path(path), self.config)
        data = json.loads(self.config.read_text('utf-8'))
        self.assertEqual(list(data), ['mcpServers', 'zeta', 'alpha'])
        self.assertEqual(list(data['mcpServers']), ['agentchattr', 'agentchattr-fork'])
        self.assertEqual(data['mcpServers']['agentchattr'], {'serverURL': 'http://127.0.0.1:8200/mcp'})
        self.assertEqual(data['mcpServers']['agentchattr-fork'],
                         {'serverURL': 'http://127.0.0.1:49961/mcp', 'headers': {'Authorization': 'Bearer ' + TOKEN}})
        raw = self.config.read_bytes()
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))        # CRLF kept throughout
        self.assertIn(b'\r\n        "agentchattr-fork": {\r\n            "serverURL"', raw)   # 4-space indent kept

    def test_configured_entry_name_is_used(self):
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply(template={**self.template, 'mcp_entry_name': 'fork-two'})
        self.assertIn('fork-two', json.loads(self.config.read_text('utf-8'))['mcpServers'])

    def test_stop_restores_exact_original_bytes_after_a_token_refresh(self):
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        self.apply(token=TOKEN + 'refreshed')
        results = wrapper._remove_json_mcp_entries()
        self.assertEqual([r.status for r in results], ['restored-exact'])
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode('utf-8'))
        backups = list(self.dir.glob('mcp_config.json.agentchattr-fork-*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertNotIn(TOKEN.encode(), backups[0].read_bytes())

    def test_user_edit_before_a_refresh_survives_stop(self):
        # Reviewer B2: never restore the first backup over an edit made between our writes.
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        self.config.write_bytes(self.config.read_bytes().replace(b'"keep"', b'"edited"'))
        self.apply(token=TOKEN + 'refreshed')
        results = wrapper._remove_json_mcp_entries()
        self.assertEqual([r.status for r in results], ['removed-entry'])
        self.assertEqual(self.config.read_bytes(), ORIGINAL.replace('"keep"', '"edited"').encode('utf-8'))

    def test_user_edit_to_a_created_file_before_a_refresh_keeps_the_file(self):
        import wrapper
        self.apply()
        self.config.write_bytes(self.config.read_bytes().replace(b'{\n', b'{\n  "mine": 1,\n', 1))
        self.apply(token=TOKEN + 'refreshed')
        wrapper._remove_json_mcp_entries()
        self.assertTrue(self.config.exists())
        self.assertEqual(json.loads(self.config.read_text('utf-8')).get('mine'), 1)
        self.assertNotIn(TOKEN.encode(), self.config.read_bytes())

    def test_refresh_that_recreates_a_user_deleted_file_deletes_it_at_stop(self):
        # Re-audit (4): the recreated file is ours alone; stop deletes it rather than leaving a stub.
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        self.config.unlink()
        self.apply(token=TOKEN + 'refreshed')
        self.assertEqual([r.status for r in wrapper._remove_json_mcp_entries()], ['deleted-created-file'])
        self.assertFalse(self.config.exists())

    def test_a_print_that_raises_cannot_lose_the_receipt(self):
        # Re-audit (5): the file is written, so the wrapper must still hold a receipt and clean up.
        import wrapper

        class Unprintable(io.StringIO):
            def write(self, _text):
                raise UnicodeEncodeError('cp1252', 'x', 0, 1, 'unmappable')
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        with patch('sys.stdout', Unprintable()):
            self.apply()
        self.assertEqual(len(wrapper._JSON_RECEIPTS), 1)
        wrapper._remove_json_mcp_entries()
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode('utf-8'))

    def test_missing_file_is_created_then_deleted(self):
        import wrapper
        self.apply()
        self.assertIn('agentchattr-fork', json.loads(self.config.read_text('utf-8'))['mcpServers'])
        self.assertEqual([r.status for r in wrapper._remove_json_mcp_entries()], ['deleted-created-file'])
        self.assertFalse(self.config.exists())

    def test_missing_directory_is_refused(self):
        self.dir.rmdir()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertFalse(self.config.exists())

    def test_late_reregistration_after_removal_cannot_write_the_entry_back(self):
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        wrapper._remove_json_mcp_entries()
        with self.assertRaises(ValueError):
            self.apply(token=TOKEN + 'late')
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode('utf-8'))

    def test_stop_hook_does_not_import_the_json_module_for_other_modes(self):
        import wrapper
        sys.modules.pop('json_mcp_settings', None)
        with patch.dict(sys.modules, {'json_mcp_settings': None}):
            self.assertEqual(wrapper._remove_json_mcp_entries(), [])

    def test_stop_hook_survives_unexpected_errors_without_printing_the_token(self):
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        out = io.StringIO()
        with patch('json_mcp_settings.remove_exact', side_effect=RuntimeError('boom ' + TOKEN)), \
                patch('sys.stdout', out):
            self.assertEqual(wrapper._remove_json_mcp_entries(), [])
        self.assertNotIn(TOKEN, out.getvalue())

    def test_unexpected_structure_is_refused_before_any_write(self):
        bad = b'{"mcpServers": []}\n'
        self.config.write_bytes(bad)
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(self.config.read_bytes(), bad)
        self.assertEqual(list(self.dir.glob('*.bak')), [])

    def test_yaml_and_json_cleanups_are_independent(self):
        import wrapper
        self.config.write_bytes(ORIGINAL.encode('utf-8'))
        self.apply()
        wrapper._remove_yaml_mcp_entries()                 # the YAML hook must not touch this file
        self.assertIn(b'agentchattr-fork', self.config.read_bytes())
        wrapper._remove_json_mcp_entries()
        self.assertEqual(self.config.read_bytes(), ORIGINAL.encode('utf-8'))


if __name__ == '__main__':
    unittest.main()
