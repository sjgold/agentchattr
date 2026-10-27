"""Reviewer findings M1/M3/M4/M6 and the stop-hook KeyboardInterrupt case, for both settings helpers.

Temporary directories only; no real client configuration or process list is touched.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json_mcp_settings as jm  # noqa: E402
import yaml_mcp_settings as ym  # noqa: E402

TOKEN = 'tok_SECRET_guard_0123456789abcdef'
URL = 'http://127.0.0.1:49961/mcp'
JSON_BASE = '{\n  "mcpServers": {\n    "agentchattr": {\n      "serverURL": "http://127.0.0.1:8200/mcp"\n    }%s\n  },\n  "other": 1\n}\n'
YAML_BASE = '# keep me\nmodel: x\nmcp_servers:\n  agentchattr:\n    url: "http://127.0.0.1:8200/mcp"\n%sterminal:\n  backend: local\n'


def quiet(*_args):
    pass


class Dir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)


class NotOursIsRefused(Dir):
    """M1: an entry under our name that does not look like ours is never refreshed or removed."""

    JSON_FOREIGN = [
        '{"command": "npx", "args": ["open-brain"]}',
        '{"serverURL": "https://example.com/mcp"}',
        '{"serverURL": "http://127.0.0.1:8200/mcp", "trust": true}',
        '{"serverURL": "http://127.0.0.1:8200/mcp", "headers": {"Authorization": "Bearer x", "X-Other": "y"}}',
        '{"serverURL": "http://127.0.0.1:8200/mcp", "headers": {"Authorization": "Basic abc"}}',
        '{"serverURL": "http://127.0.0.1.evil.com:80/mcp"}',
        '{"url": "http://127.0.0.1:8200/mcp"}',
        '{}',
    ]
    YAML_FOREIGN = [
        '    command: npx\n',
        '    url: "https://example.com/mcp"\n',
        '    url: "http://localhost:8200/mcp"\n    timeout: 5\n',
        '    url: "http://127.0.0.1:8200/mcp"\n    headers:\n      Authorization: "Bearer x"\n      X-Other: y\n',
        '    url: "http://127.0.0.1:8200/mcp"\n    headers:\n      Authorization: "Basic abc"\n',
    ]

    def test_json_foreign_entry(self):
        path = self.dir / 'mcp_config.json'
        for value in self.JSON_FOREIGN:
            with self.subTest(value=value):
                original = (JSON_BASE % (',\n    "agentchattr-fork": ' + value)).encode()
                path.write_bytes(original)
                with self.assertRaises(jm.JsonSettingsError) as caught:
                    jm.apply(path, URL, TOKEN, log=quiet)
                self.assertIn('agentchattr-fork', str(caught.exception))
                self.assertNotIn('open-brain', str(caught.exception))
                with self.assertRaises(jm.JsonSettingsError):
                    jm.remove_exact(path, log=quiet)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(self.dir.glob('*.bak')), [])

    def test_json_configured_name_never_overwrites_a_users_server(self):
        path = self.dir / 'mcp_config.json'
        original = (JSON_BASE % ',\n    "open-brain": {"serverURL": "https://brain.example/mcp"}').encode()
        path.write_bytes(original)
        with self.assertRaises(jm.JsonSettingsError):
            jm.apply(path, URL, TOKEN, entry='open-brain', log=quiet)
        self.assertEqual(path.read_bytes(), original)

    def test_json_ours_shaped_entry_is_accepted(self):
        path = self.dir / 'mcp_config.json'
        for value in ('{"serverURL": "http://127.0.0.1:1/mcp"}',
                      '{"serverURL": "http://localhost:8200/sse", "headers": {"Authorization": "Bearer old"}}'):
            with self.subTest(value=value):
                path.write_bytes((JSON_BASE % (',\n    "agentchattr-fork": ' + value)).encode())
                jm.apply(path, URL, TOKEN, log=quiet)
                self.assertEqual(jm.remove_exact(path, log=quiet).status, 'removed-entry')

    def test_yaml_foreign_entry(self):
        path = self.dir / 'config.yaml'
        for value in self.YAML_FOREIGN:
            with self.subTest(value=value):
                original = (YAML_BASE % ('  agentchattr-uat:\n' + value)).encode()
                path.write_bytes(original)
                with self.assertRaises(ym.YamlSettingsError) as caught:
                    ym.apply(path, URL, TOKEN, log=quiet)
                self.assertIn('agentchattr-uat', str(caught.exception))
                with self.assertRaises(ym.YamlSettingsError):
                    ym.remove_exact(path, log=quiet)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(self.dir.glob('*.bak')), [])

    def test_yaml_ours_shaped_entry_is_accepted(self):
        path = self.dir / 'config.yaml'
        path.write_bytes((YAML_BASE % '  agentchattr-uat:\n    url: "http://127.0.0.1:1/mcp"\n').encode())
        ym.apply(path, URL, TOKEN, log=quiet)
        self.assertEqual(ym.remove_exact(path, log=quiet).status, 'removed-entry')


class BytesOutsideTheSpliceAreChecked(Dir):
    """M3: a splice that also changes bytes elsewhere (structure intact) is refused."""

    def test_json_apply(self):
        path = self.dir / 'mcp_config.json'
        original = (JSON_BASE % '').encode()
        path.write_bytes(original)
        real = jm._append_member

        def sloppy(*args, **kwargs):
            text, region = real(*args, **kwargs)
            return text.replace('{\n', '{ \n', 1), region
        with patch.object(jm, '_append_member', sloppy), self.assertRaises(jm.JsonSettingsError):
            jm.apply(path, URL, TOKEN, log=quiet)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.dir.glob('*.bak')), [])

    def test_json_refresh_and_remove(self):
        path = self.dir / 'mcp_config.json'
        path.write_bytes((JSON_BASE % '').encode())
        receipt = jm.apply(path, URL, TOKEN, log=quiet)
        written = path.read_bytes()
        for name in ('_replace_value', '_remove_member'):
            real = getattr(jm, name)

            def sloppy(*args, real=real, **kwargs):
                text, region = real(*args, **kwargs)
                return text.replace('"other":', '"other" :'), region     # same structure, other bytes
            with self.subTest(name=name), patch.object(jm, name, sloppy), self.assertRaises(jm.JsonSettingsError):
                if name == '_replace_value':
                    jm.apply(path, URL, TOKEN + 'x', log=quiet)
                else:
                    path.write_bytes(written.replace(b'"other": 1', b'"other": 2'))
                    jm.remove_exact(path, receipt=receipt, log=quiet)

    def test_yaml_apply_and_remove(self):
        path = self.dir / 'config.yaml'
        original = (YAML_BASE % '').encode()
        path.write_bytes(original)
        real = ym._with_entry

        def sloppy(*args, **kwargs):
            text, created, region = real(*args, **kwargs)
            return text.replace('# keep me', '# KEEP me'), created, region
        with patch.object(ym, '_with_entry', sloppy), self.assertRaises(ym.YamlSettingsError):
            ym.apply(path, URL, TOKEN, log=quiet)
        self.assertEqual(path.read_bytes(), original)
        receipt = ym.apply(path, URL, TOKEN, log=quiet)
        path.write_bytes(path.read_bytes().replace(b'backend: local', b'backend: docker'))
        real_remove = ym._without_entry

        def sloppy_remove(*args, **kwargs):
            text, region = real_remove(*args, **kwargs)
            return text.replace('# keep me', '# KEEP me'), region
        with patch.object(ym, '_without_entry', sloppy_remove), self.assertRaises(ym.YamlSettingsError):
            ym.remove_exact(path, receipt=receipt, log=quiet)
        self.assertIn(b'agentchattr-uat', path.read_bytes())


class BackupIsRemovedOnAnyWriteFailure(Dir):
    """M4."""

    def test_json(self):
        path = self.dir / 'mcp_config.json'
        original = (JSON_BASE % '').encode()
        path.write_bytes(original)
        with patch.object(jm, '_atomic_write', side_effect=PermissionError('locked')), self.assertRaises(PermissionError):
            jm.apply(path, URL, TOKEN, log=quiet)
        self.assertEqual(list(self.dir.glob('*.bak')), [])
        self.assertEqual(path.read_bytes(), original)

    def test_yaml(self):
        path = self.dir / 'config.yaml'
        original = (YAML_BASE % '').encode()
        path.write_bytes(original)
        with patch.object(ym, '_atomic_write', side_effect=OSError('disk full')), self.assertRaises(OSError):
            ym.apply(path, URL, TOKEN, log=quiet)
        self.assertEqual(list(self.dir.glob('*.bak')), [])
        self.assertEqual(path.read_bytes(), original)


class ReceiptRecordsThePriorBytes(Dir):
    """B2 support: the receipt says which bytes the write replaced."""

    def test_json_and_yaml(self):
        import hashlib
        for module, name, base in ((jm, 'mcp_config.json', JSON_BASE % ''), (ym, 'config.yaml', YAML_BASE % '')):
            with self.subTest(module=module.__name__):
                path = self.dir / name
                path.write_bytes(base.encode())
                first = module.apply(path, URL, TOKEN, log=quiet)
                self.assertEqual(first.prior_sha256, hashlib.sha256(base.encode()).hexdigest())
                second = module.apply(path, URL, TOKEN + 'x', log=quiet)
                self.assertEqual(second.prior_sha256, first.written_sha256)
        missing = jm.apply(self.dir / 'new.json', URL, TOKEN, log=quiet)
        self.assertIsNone(missing.prior_sha256)


class AgyRunningWithoutPaths(unittest.TestCase):
    """M6: no executable path obtained means the path check did not run."""

    def test_names_only_listing_is_none(self):
        self.assertIsNone(jm.agy_running(lister=lambda: [('svchost.exe', None), ('node.exe', None)],
                                         install_root=os.path.join(os.sep, 'fake', 'agy', 'bin')))

    def test_name_match_is_still_true(self):
        self.assertIs(jm.agy_running(lister=lambda: [('agy.exe', None)],
                                     install_root=os.path.join(os.sep, 'fake', 'agy', 'bin')), True)

    def test_every_open_process_failing_is_none(self):
        from types import SimpleNamespace
        with patch.object(jm.sys, 'platform', 'win32'), \
                patch.object(jm.subprocess, 'run', return_value=SimpleNamespace(stdout='"System","4"\n')), \
                patch.object(jm, '_windows_executable_paths', return_value=[]):
            self.assertIsNone(jm.agy_running(install_root=os.path.join(os.sep, 'fake', 'agy', 'bin')))


class StopCleanupsSurviveKeyboardInterrupt(unittest.TestCase):
    def test_json_cleanup_and_close_still_run(self):
        import wrapper
        resources = MagicMock()
        with patch.object(wrapper, '_remove_yaml_mcp_entries', side_effect=KeyboardInterrupt), \
                patch.object(wrapper, '_remove_json_mcp_entries') as json_cleanup, \
                self.assertRaises(KeyboardInterrupt):
            wrapper._stop_settings_cleanups(resources)
        json_cleanup.assert_called_once_with()
        resources.close.assert_called_once_with()

    def test_close_runs_when_json_cleanup_is_interrupted(self):
        import wrapper
        resources = MagicMock()
        with patch.object(wrapper, '_remove_yaml_mcp_entries', return_value=[]), \
                patch.object(wrapper, '_remove_json_mcp_entries', side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            wrapper._stop_settings_cleanups(resources)
        resources.close.assert_called_once_with()

    def test_ordinary_errors_are_reported_without_detail(self):
        import io
        import wrapper
        resources = MagicMock()
        out = io.StringIO()
        with patch.object(wrapper, '_remove_yaml_mcp_entries', side_effect=RuntimeError(TOKEN)), \
                patch.object(wrapper, '_remove_json_mcp_entries', side_effect=RuntimeError(TOKEN)), \
                patch('sys.stdout', out):
            wrapper._stop_settings_cleanups(resources)
        self.assertNotIn(TOKEN, out.getvalue())
        resources.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
