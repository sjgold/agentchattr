import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


@unittest.skipUnless(sys.platform == 'win32', 'Windows CLI worker lifecycle')
class CliWorkerTests(unittest.TestCase):
    def test_failed_child_is_not_a_successful_stop(self):
        import cli_worker
        import wrapper_windows
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            seat = {'id': 'one', 'name': 'Fake', 'adapter': 'cli', 'provider': 'fake',
                    'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
            snapshot = {'seat': seat, 'attempt': 'attempt', 'base': 'cli-fake',
                        'server': {'port': 18999, 'data_dir': directory}, 'mcp': {},
                        'provider': {'command': sys.executable, 'cwd': directory,
                                     'mcp_inject': 'env', 'mcp_env_var': 'TICKET4_TEST_SETTINGS'}}
            path.write_text(json.dumps(snapshot), encoding='utf-8')
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'{}'
            with patch.object(cli_worker, '_register_instance', return_value={'name': 'cli-fake', 'token': 'fake-token'}), \
                    patch.object(cli_worker.urllib.request, 'urlopen', return_value=response), \
                    patch.object(wrapper_windows, 'run_agent', return_value=23):
                self.assertEqual(cli_worker.run(path), 23)
            receipt = json.loads(path.with_name('receipt.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['state'], 'failed')
            self.assertEqual(receipt['child_exit_code'], 23)
            self.assertEqual(receipt['authentication'], 'unknown')

    def test_cli_client_does_not_inherit_configured_api_keys(self):
        import os
        import cli_worker
        import wrapper_windows
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config.json'
            seat={'id':'one','name':'Fake','adapter':'cli','provider':'fake',
                  'model':None,'reasoning':None,'launch_profile':'standard','secret_ref':''}
            snapshot={'seat':seat,'attempt':'attempt','base':'cli-fake',
                      'server':{'port':18999,'data_dir':directory},'mcp':{},
                      'provider':{'command':sys.executable,'cwd':directory,'mcp_inject':'env',
                                  'mcp_env_var':'TICKET4_TEST_SETTINGS','strip_env':['fake_api_key']}}
            path.write_text(json.dumps(snapshot),encoding='utf-8')
            response=MagicMock();response.__enter__.return_value.read.return_value=b'{}'
            called=[]
            def run_client(**kwargs):
                self.assertFalse('FAKE_API_KEY' in kwargs['env'], 'API key reached native client')
                self.assertEqual(kwargs['env']['UNREFERENCED_ENV'],'keep')
                called.append(True)
                return 0
            with patch.dict(os.environ,{'FAKE_API_KEY':'fake-private','UNREFERENCED_ENV':'keep'},clear=True), \
                    patch.object(cli_worker,'_register_instance',return_value={'name':'cli-fake','token':'fake-token'}), \
                    patch.object(cli_worker.urllib.request,'urlopen',return_value=response), \
                    patch.object(wrapper_windows,'run_agent',side_effect=run_client):
                self.assertEqual(cli_worker.run(path),0)
            self.assertEqual(called,[True])

    def yaml_worker(self, startup_failure=False):
        import os
        import wrapper
        import cli_worker
        import wrapper_windows
        import yaml
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)/'home';home.mkdir()
            target=home/'config.yaml'
            original=b'# keep comments\r\nmodel: existing\r\nmcp_servers:\r\n  agentchattr:\r\n    url: "http://127.0.0.1:9999/mcp"\r\n'
            target.write_bytes(original)
            seat={'id':'one','name':'Hermes','adapter':'cli','provider':'fake','model':None,
                  'reasoning':None,'launch_profile':'standard','secret_ref':''}
            path=Path(directory)/'config.json'
            snapshot={'seat':seat,'attempt':'attempt','base':'cli-fake',
                      'server':{'port':18999,'data_dir':directory},'mcp':{},
                      'provider':{'command':sys.executable,'cwd':directory,'mcp_inject':'yaml_settings_file',
                                  'mcp_settings_path':'$HERMES_HOME/config.yaml'}}
            path.write_text(json.dumps(snapshot),encoding='utf-8')
            response=MagicMock();response.__enter__.return_value.read.return_value=b'{}'
            wrapper._reset_yaml_state();self.addCleanup(wrapper._reset_yaml_state)
            from contextlib import contextmanager
            real_lock=cli_worker.startup_lock
            active=[False]
            @contextmanager
            def locked(*args,**kwargs):
                with real_lock(*args,**kwargs):
                    active[0]=True
                    try:yield
                    finally:active[0]=False
            def remove_checked():
                self.assertTrue(active[0], 'Cleanup ran after the lifetime lock was released')
                return wrapper._remove_yaml_mcp_entries()

            def client(**kwargs):
                self.assertTrue('agentchattr-uat' in yaml.safe_load(target.read_text(encoding='utf-8'))['mcp_servers'])
                path.with_name('stop.json').write_text(json.dumps({'attempt':'attempt'}),encoding='utf-8')
                self.assertTrue(kwargs['stop_event'].wait(2),'Managed Stop was not observed')
                return 0
            with patch.dict(os.environ,{'HERMES_HOME':str(home)},clear=True), \
                    patch('yaml_mcp_settings.hermes_running',return_value=False), \
                    patch.object(cli_worker,'startup_lock',side_effect=locked), \
                    patch.object(cli_worker,'_remove_yaml_mcp_entries',side_effect=remove_checked), \
                    patch.object(cli_worker,'_register_instance',return_value={'name':'cli-fake','token':'FAKE_UAT_TOKEN'}), \
                    patch.object(cli_worker.urllib.request,'urlopen',return_value=response), \
                    patch.object(wrapper_windows,'run_agent',side_effect=client), \
                    patch.object(cli_worker,'probe_version',side_effect=OSError('fixture failure') if startup_failure else None,return_value=None):
                outcome=cli_worker.run(path)
            self.assertEqual(outcome,1 if startup_failure else 0)
            self.assertTrue(target.read_bytes()==original,'Managed YAML cleanup did not restore original bytes')
            self.assertFalse(any(home.glob('*.tmp')),'YAML cleanup left a temporary file')

    def test_managed_yaml_stop_removes_entry_before_releasing_settings_lock(self):
        self.yaml_worker()

    def test_managed_yaml_startup_failure_after_apply_also_removes_entry(self):
        self.yaml_worker(startup_failure=True)

    def json_worker(self, startup_failure=False):
        import os
        import wrapper
        import cli_worker
        import wrapper_windows
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)/'home';home.mkdir()
            target=home/'mcp_config.json'
            original=b'{\r\n  "mcpServers": {"agentchattr": {"serverURL": "http://127.0.0.1:9999/mcp"}}, "other": {"keep": true}\r\n}\r\n'
            target.write_bytes(original)
            seat={'id':'one','name':'Antigravity','adapter':'cli','provider':'fake','model':None,
                  'reasoning':None,'launch_profile':'standard','secret_ref':''}
            path=Path(directory)/'config.json'
            snapshot={'seat':seat,'attempt':'attempt','base':'cli-fake',
                      'server':{'port':18999,'data_dir':directory},'mcp':{},
                      'provider':{'command':sys.executable,'cwd':directory,'mcp_inject':'json_entry_file',
                                  'mcp_settings_path':str(target),'mcp_http_key':'serverURL','mcp_entry_name':'agentchattr-uat'}}
            path.write_text(json.dumps(snapshot),encoding='utf-8')
            response=MagicMock();response.__enter__.return_value.read.return_value=b'{}'
            wrapper._reset_json_state();self.addCleanup(wrapper._reset_json_state)
            from contextlib import contextmanager
            real_lock=cli_worker.startup_lock
            active=[False]
            @contextmanager
            def locked(*args,**kwargs):
                with real_lock(*args,**kwargs):
                    active[0]=True
                    try:yield
                    finally:active[0]=False
            def remove_checked():
                self.assertTrue(active[0], 'Cleanup ran after the lifetime lock was released')
                return wrapper._remove_json_mcp_entries()

            def client(**kwargs):
                self.assertTrue('agentchattr-uat' in json.loads(target.read_text(encoding='utf-8'))['mcpServers'])
                path.with_name('stop.json').write_text(json.dumps({'attempt':'attempt'}),encoding='utf-8')
                self.assertTrue(kwargs['stop_event'].wait(2),'Managed Stop was not observed')
                return 0
            with patch.dict(os.environ,{'HERMES_HOME':str(home)},clear=True), \
                                        patch.object(cli_worker,'startup_lock',side_effect=locked), \
                    patch.object(cli_worker,'_remove_json_mcp_entries',side_effect=remove_checked), \
                    patch.object(cli_worker,'_register_instance',return_value={'name':'cli-fake','token':'FAKE_UAT_TOKEN'}), \
                    patch.object(cli_worker.urllib.request,'urlopen',return_value=response), \
                    patch.object(wrapper_windows,'run_agent',side_effect=client), \
                    patch.object(cli_worker,'probe_version',side_effect=OSError('fixture failure') if startup_failure else None,return_value=None):
                outcome=cli_worker.run(path)
            self.assertEqual(outcome,1 if startup_failure else 0)
            self.assertTrue(target.read_bytes()==original,'Managed JSON cleanup did not restore original bytes')
            self.assertFalse(any(home.glob('*.tmp')),'JSON cleanup left a temporary file')

    def test_managed_json_stop_removes_entry_before_releasing_settings_lock(self):
        self.json_worker()

    def test_managed_json_startup_failure_after_apply_also_removes_entry(self):
        self.json_worker(startup_failure=True)
