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
