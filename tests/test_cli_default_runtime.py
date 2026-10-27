"""Managed CLI defaults survive freezing and status reporting; no client is spawned."""
import json
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import Mock,patch
from api_seats import SeatStore
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry
from cli_seats import build_cli_args

class CliDefaultRuntimeTests(unittest.TestCase):
 def check_model(self,explicit):
  with tempfile.TemporaryDirectory() as directory:
   provider={'command':sys.executable,'cwd':directory,'cli_model_args':['--model','{model}'],
             'default_model':'gemini-3.8-flash-medium','mcp_inject':'env','mcp_env_var':'FAKE_SETTINGS'}
   seat={'id':'writer','name':'Writer','adapter':'cli','provider':'fake','model':explicit,
         'reasoning':None,'secret_ref':'','launch_profile':'standard'}
   store=SeatStore(directory,{'fake':provider});store.save({'id':'team','name':'Team','seats':[seat]})
   manager=SeatManager(Path(__file__).resolve().parents[1],{'server':{}},store,RuntimeRegistry(directory),monitor=False)
   expected=explicit or provider['default_model']
   self.assertEqual(manager.inspect('team','writer')['requested_model'],expected)
   effective=manager._effective(seat)
   self.assertEqual(effective['provider'].get('default_model'),provider['default_model'])
   self.assertEqual(manager._provenance_effective(effective)['provider'].get('default_model'),provider['default_model'])
   process=Mock();process.poll.return_value=None
   with patch('api_seat_runtime.subprocess.Popen',return_value=process):
    result=manager.launch('team','writer')
   frozen=json.loads(manager.attempts['team/writer']['snapshot'].read_text(encoding='utf-8'))
   self.assertEqual(build_cli_args(frozen['seat'],frozen['provider']),['--model',expected])
   self.assertEqual(result['requested_model'],expected)
   store.providers['fake']['default_model']='changed-default'
   changed=manager._effective(seat)
   self.assertFalse(manager._provenance_effective(effective)==manager._provenance_effective(changed))
 def test_blank_model_uses_frozen_template_default(self):self.check_model(None)
 def test_explicit_model_wins_and_default_still_fingerprints(self):self.check_model('explicit-model')
