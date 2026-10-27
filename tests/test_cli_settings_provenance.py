"""Entry-file settings stay bound to the managed launch, fake processes/temp homes only."""
import ast,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from api_seats import SeatStore,SeatError
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry
ROOT=Path(__file__).resolve().parents[1]

class CliSettingsProvenanceTests(unittest.TestCase):
 def test_all_worker_consumed_mcp_keys_are_provenance_bound(self):
  consumed=set()
  for name in ('cli_worker.py','wrapper.py','cli_seats.py'):
   for node in ast.walk(ast.parse((ROOT/name).read_text(encoding='utf-8'))):
    if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='get'
      and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str)
      and node.args[0].value.startswith('mcp_')):consumed.add(node.args[0].value)
  actual=SeatManager._provenance_effective({'seat':{},'provider':{key:'fixture' for key in consumed},'server':{}})['provider']
  self.assertFalse(bool(consumed-set(actual)),'Missing consumed keys: '+','.join(sorted(consumed-set(actual))))

 def fixture(self,directory):
  template={'command':sys.executable,'cwd':directory,'mcp_inject':'json_entry_file',
    'mcp_settings_path':str(Path(directory)/'mcp_config.json'),'mcp_http_key':'serverURL','mcp_transport':'http','mcp_entry_name':'agentchattr-fork-a'}
  seat={'id':'writer','name':'Writer','adapter':'cli','provider':'fake','model':None,'reasoning':None,'secret_ref':'','launch_profile':'standard'}
  store=SeatStore(directory,{'fake':template});store.save({'id':'team','name':'Team','seats':[seat]})
  manager=SeatManager(ROOT,{'server':{}},store,RuntimeRegistry(directory),monitor=False)
  return store,manager,seat

 def test_entry_edit_changes_provenance_and_requires_deliberate_restart(self):
  with tempfile.TemporaryDirectory() as directory:
   store,manager,seat=self.fixture(directory);before=manager._provenance_effective(manager._effective(seat))
   process=Mock();process.poll.return_value=None
   with patch('api_seat_runtime.subprocess.Popen',return_value=process):manager.launch('team','writer')
   store.providers['fake']['mcp_entry_name']='agentchattr-fork-b'
   after=manager._provenance_effective(manager._effective(seat))
   digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
   self.assertFalse(digest(before)==digest(after),'Entry name vanished from provenance fingerprint')
   with self.assertRaisesRegex(SeatError,'restart'):manager.launch('team','writer')
   process.terminate.assert_not_called()

 def test_tampered_entry_snapshot_refuses_before_apply(self):
  import cli_worker,runtime_ownership
  with tempfile.TemporaryDirectory() as directory:
   store,manager,seat=self.fixture(directory);process=Mock();process.poll.return_value=None
   with patch('api_seat_runtime.subprocess.Popen',return_value=process):manager.launch('team','writer')
   path=manager.attempts['team/writer']['snapshot'];original=json.loads(path.read_text(encoding='utf-8'))
   self.assertIsNotNone(runtime_ownership._validate(path,original))
   original['provider']['mcp_entry_name']='agentchattr-fork-b';path.write_text(json.dumps(original),encoding='utf-8')
   with patch.object(cli_worker,'_build_provider_launch') as apply:
    with self.assertRaisesRegex(ValueError,'frozen settings'):cli_worker.run(path)
    apply.assert_not_called()
   self.assertFalse(path.with_name('birth.json').exists())
