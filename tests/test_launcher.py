"""Bootstrap checks use temporary homes and fake processes, never agents."""
import concurrent.futures
import contextlib
import importlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'launcher.py').exists(), 'shared bootstrap is missing')
        self.launcher = importlib.import_module('launcher')
        scratch = ROOT / '.audit-tmp'
        scratch.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'checkout with spaces'
        self.root.mkdir()
        self.cfg = {'server': {'port': 18300, 'host': '127.0.0.1', 'data_dir': './data'}}

    def test_identity_binds_checkout_port_and_data(self):
        identity = self.launcher.instance_identity(self.root, self.cfg)
        other = {'server': {**self.cfg['server'], 'data_dir': './other'}}
        self.assertNotEqual(identity, self.launcher.instance_identity(self.root, other))
        self.assertNotEqual(identity, self.launcher.instance_identity(self.root / 'other', self.cfg))
        self.assertEqual(identity, self.launcher.instance_identity(self.root, self.cfg))

    def test_reuses_matching_service_without_dependency_setup(self):
        with patch.object(self.launcher, 'probe_health', return_value='matching'), \
             patch.object(self.launcher, 'ensure_environment') as setup, \
             patch.object(self.launcher, 'spawn_server') as spawn:
            url = self.launcher.ensure_server(self.root, self.cfg, timeout=1)
        self.assertEqual(url, 'http://127.0.0.1:18300/preflight')
        setup.assert_not_called()
        spawn.assert_not_called()

    def test_foreign_listener_is_never_terminated_or_replaced(self):
        with patch.object(self.launcher, 'probe_health', return_value='foreign'), \
             patch.object(self.launcher, 'spawn_server') as spawn:
            with self.assertRaisesRegex(self.launcher.LaunchError, '18300.*occupied'):
                self.launcher.ensure_server(self.root, self.cfg, timeout=1)
        spawn.assert_not_called()

    def test_failed_startup_reports_exit_and_log_location(self):
        process = Mock()
        process.poll.return_value = 17
        with patch.object(self.launcher, 'probe_health', return_value='absent'), \
             patch.object(self.launcher, 'ensure_environment', return_value=Path(sys.executable)), \
             patch.object(self.launcher, 'spawn_server', return_value=process):
            with self.assertRaisesRegex(self.launcher.LaunchError, '17.*server.log'):
                self.launcher.ensure_server(self.root, self.cfg, timeout=1)

    def test_timeout_stops_only_owned_child(self):
        process = Mock()
        process.poll.return_value = None
        with patch.object(self.launcher, 'probe_health', return_value='absent'), \
             patch.object(self.launcher, 'ensure_environment', return_value=Path(sys.executable)), \
             patch.object(self.launcher, 'spawn_server', return_value=process):
            started = time.monotonic()
            with self.assertRaisesRegex(self.launcher.LaunchError, 'deadline'):
                self.launcher.ensure_server(self.root, self.cfg, timeout=0.05)
        self.assertLess(time.monotonic() - started, 1)
        process.terminate.assert_called_once()

    def test_concurrent_launches_spawn_once(self):
        ready = threading.Event()
        process = Mock()
        process.poll.return_value = None
        def spawn(*args):
            ready.set()
            return process
        def probe(*args, **kwargs):
            return 'matching' if ready.is_set() else 'absent'
        with patch.object(self.launcher, 'probe_health', side_effect=probe), \
             patch.object(self.launcher, 'ensure_environment', return_value=Path(sys.executable)), \
             patch.object(self.launcher, 'spawn_server', side_effect=spawn) as create:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.launcher.ensure_server(self.root, self.cfg, timeout=2), range(2)))
        self.assertEqual(create.call_count, 1)
        self.assertEqual(results[0], results[1])

    def test_setup_requires_explicit_choice(self):
        with patch.object(self.launcher, 'environment_ready', return_value=False), \
             patch.object(self.launcher.subprocess, 'run') as run:
            with self.assertRaisesRegex(self.launcher.LaunchError, '--setup'):
                self.launcher.ensure_environment(self.root, setup=False)
        run.assert_not_called()

    def test_linux_and_windows_environments_are_separate(self):
        windows = self.launcher.environment_python(self.root, platform='win32')
        linux = self.launcher.environment_python(self.root, platform='linux')
        self.assertNotEqual(windows.parent.parent, linux.parent.parent)
        self.assertIn('.venv-windows', str(windows))
        self.assertIn('.venv-linux', str(linux))

    def test_passive_discovery_does_not_launch_commands(self):
        cfg = {**self.cfg, 'agents': {'missing': {'command': 'nonexistent-example-cli'}, 'api': {'type': 'api'}}}
        with patch.object(self.launcher.subprocess, 'run') as run, \
             patch.object(self.launcher.subprocess, 'Popen') as popen:
            result = self.launcher.preflight_snapshot(cfg)
        self.assertEqual(result['agents'][0]['authentication'], 'unknown')
        self.assertFalse(result['agents'][0]['ready'])
        self.assertIsNone(result['agents'][1]['executable'])
        run.assert_not_called()
        popen.assert_not_called()

    def test_health_contract_rejects_wrong_instance(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        identity = self.launcher.instance_identity(self.root, self.cfg)
        class Handler(BaseHTTPRequestHandler):
            def do_GET(inner):
                inner.send_response(200)
                inner.end_headers()
                inner.wfile.write(json.dumps({'app': 'agentchattr', 'protocol': 1, 'identity': identity, 'state': 'ready'}).encode())
            def log_message(*args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f'http://127.0.0.1:{server.server_port}'
        self.assertEqual(self.launcher.probe_health(url, identity, timeout=1), 'matching')
        self.assertEqual(self.launcher.probe_health(url, 'other', timeout=1), 'foreign')

    def test_lock_is_bounded_and_releases_after_exception(self):
        path = self.root / 'lock'
        with self.launcher.startup_lock(path, time.monotonic() + 1):
            with self.assertRaisesRegex(self.launcher.LaunchError, 'startup.*busy'):
                with self.launcher.startup_lock(path, time.monotonic() + 0.03):
                    self.fail('lock should be exclusive')
        with self.assertRaises(ValueError):
            with self.launcher.startup_lock(path, time.monotonic() + 1):
                raise ValueError('test')
        with self.launcher.startup_lock(path, time.monotonic() + 1):
            pass

    def test_check_mode_does_not_create_files_or_start_server(self):
        (self.root / 'config.toml').write_text('[server]\nport = 18300\n')
        with patch.object(self.launcher, 'probe_health', return_value='absent'), \
             patch.object(self.launcher, 'environment_ready', return_value=False), \
             patch.object(self.launcher, 'spawn_server') as spawn:
            self.assertEqual(self.launcher.main(['--check'], root=self.root), 0)
        self.assertEqual([p.name for p in self.root.iterdir()], ['config.toml'])
        spawn.assert_not_called()

    def test_kernel_lock_excludes_a_separate_process(self):
        import subprocess
        path = self.root / 'cross-process.lock'
        code = ('import sys,time; from pathlib import Path; from launcher import startup_lock; '
                'lock=startup_lock(Path(sys.argv[1]),time.monotonic()+2); '
                'lock.__enter__(); print("locked",flush=True); sys.stdin.readline(); lock.__exit__(None,None,None)')
        process = subprocess.Popen([sys.executable, '-c', code, str(path)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'locked')
            with self.assertRaises(self.launcher.LaunchError):
                with self.launcher.startup_lock(path, time.monotonic() + 0.05):
                    self.fail('separate process lock was ignored')
        finally:
            process.communicate('\n', timeout=5)
        self.assertEqual(process.returncode, 0)
        with self.launcher.startup_lock(path, time.monotonic() + 1):
            pass

    def test_instance_identity_includes_upload_directory_and_host(self):
        original = self.launcher.instance_identity(self.root, self.cfg)
        changed_upload = {**self.cfg, 'images': {'upload_dir': './other-uploads'}}
        changed_host = {**self.cfg, 'server': {**self.cfg['server'], 'host': '::1'}}
        self.assertNotEqual(original, self.launcher.instance_identity(self.root, changed_upload))
        self.assertNotEqual(original, self.launcher.instance_identity(self.root, changed_host))

    def test_non_http_listener_is_a_conflict(self):
        from http.client import BadStatusLine
        opener = unittest.mock.Mock()
        opener.open.side_effect = BadStatusLine('not HTTP')
        with patch.object(self.launcher.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual(self.launcher.probe_health('http://127.0.0.1:18300', 'id'), 'foreign')


if __name__ == '__main__':
    unittest.main()
