import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

@unittest.skipUnless(sys.platform == 'win32', 'Windows managed CLI')
class ManagedCliActivityTests(unittest.TestCase):
    def test_codex_approves_only_its_injected_chat_server(self):
        from wrapper import _build_provider_launch
        args, _, _, _ = _build_provider_launch('codex_release',
            {'command': 'C:/clients/codex.exe', 'mcp_inject': 'proxy_flag',
             'mcp_proxy_flag_template': '-c mcp_servers={{{server}={{url="{url}"}}}}'},
            'codex-seat', Path('.'), 'http://127.0.0.1:18000/mcp',
            ['--sandbox', 'read-only', '--ask-for-approval', 'never'], {})
        self.assertIn('mcp_servers.agentchattr.default_tools_approval_mode="approve"', args)
        self.assertEqual(args[-4:], ['--sandbox', 'read-only', '--ask-for-approval', 'never'])

    def test_heartbeat_includes_observed_activity(self):
        import cli_worker
        import wrapper_windows
        seen = threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            seat = dict(id='one',name='Fake',adapter='cli',provider='fake',model=None,
                        reasoning=None,launch_profile='standard',secret_ref='')
            snapshot = dict(seat=seat,attempt='attempt',base='cli-fake',mcp={},
                server={'port':18999,'data_dir':directory},
                provider={'command':sys.executable,'cwd':directory,'mcp_inject':'env','mcp_env_var':'FAKE_SETTINGS'})
            path.write_text(json.dumps(snapshot), encoding='utf-8')
            def request(req, **kwargs):
                if '/heartbeat/' in req.full_url and json.loads(req.data).get('active') is True:
                    seen.set()
                response=MagicMock();response.__enter__.return_value.read.return_value=b'{}'
                return response
            def run(**kwargs):
                self.assertEqual(kwargs['env'].get('TERM'), 'xterm-256color')
                kwargs['start_watcher'](lambda text: True)
                self.assertTrue(seen.wait(2), 'Managed heartbeat omitted observed CLI activity')
                return 0
            with patch.dict(os.environ, {'TERM': 'dumb'}), \
                 patch('runtime_ownership.record_worker_birth',return_value={}), \
                 patch('runtime_ownership.heartbeat_payload',return_value={}), \
                 patch.object(cli_worker,'_register_instance',return_value={'name':'cli-fake','token':'fake'}), \
                 patch.object(cli_worker.urllib.request,'urlopen',side_effect=request), \
                 patch.object(cli_worker,'_queue_watcher'), \
                 patch.object(wrapper_windows,'get_activity_checker',return_value=lambda: True), \
                 patch.object(wrapper_windows,'run_agent',side_effect=run):
                cli_worker.run(path)

    def test_local_stop_does_not_wait_for_blocked_heartbeat(self):
        import cli_worker
        import wrapper_windows
        entered, release = threading.Event(), threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps(dict(attempt='attempt',base='cli-fake',mcp={},
                seat=dict(id='one',name='Fake',adapter='cli',provider='fake',model=None,
                          reasoning=None,launch_profile='standard',secret_ref=''),
                server={'port':18999,'data_dir':directory},
                provider={'command':sys.executable,'cwd':directory,'mcp_inject':'env',
                          'mcp_env_var':'FAKE_SETTINGS'})), encoding='utf-8')
            def request(req, **kwargs):
                if '/heartbeat/' in req.full_url:
                    entered.set()
                    release.wait(3)
                response=MagicMock();response.__enter__.return_value.read.return_value=b'{}'
                return response
            def run(**kwargs):
                self.assertTrue(entered.wait(2))
                path.with_name('stop.json').write_text(json.dumps({'attempt':'attempt'}),encoding='utf-8')
                try:
                    self.assertTrue(kwargs['stop_event'].wait(.8), 'Network heartbeat blocked local Stop')
                finally:
                    release.set()
                return 0
            with patch('runtime_ownership.record_worker_birth',return_value={}), \
                 patch('runtime_ownership.heartbeat_payload',return_value={}), \
                 patch.object(cli_worker,'_register_instance',return_value={'name':'cli-fake','token':'fake'}), \
                 patch.object(cli_worker.urllib.request,'urlopen',side_effect=request), \
                 patch.object(wrapper_windows,'run_agent',side_effect=run):
                cli_worker.run(path)
