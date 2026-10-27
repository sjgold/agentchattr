"""Real pre-flight provider descriptions, no process or global file writes."""
import os,sys,tempfile,unittest
from unittest.mock import patch
from api_seats import SeatStore
PRIVATE='Launch writes a private MCP identity configuration for this seat. Native login is reused; no authentication home is copied.'
class ConfigurationEffectsTests(unittest.TestCase):
 def describe(self,mode,**settings):
  with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'HERMES_HOME':directory,'HOME':directory,'USERPROFILE':directory},clear=True):
   template={'command':sys.executable,'cwd':directory,'mcp_inject':mode,**settings}
   rows=SeatStore(directory,{'fixture':template}).describe_providers()
   self.assertEqual(len(rows),1)
   return rows[0]['configuration_effects']
 def assert_entry(self,text,path,entry):
  for expected in (path,entry,'Launch','only','backup','Stop','removes','restores'):self.assertIn(expected,text)
  self.assertFalse('private MCP identity' in text)
  self.assertFalse('http://' in text or 'Bearer' in text)
 def test_json_custom_entry_discloses_global_file(self):
  self.assert_entry(self.describe('json_entry_file',mcp_settings_path='~/.gemini/config/mcp_config.json',mcp_entry_name='agentchattr-check',mcp_http_key='serverURL'),'~/.gemini/config/mcp_config.json','agentchattr-check')
 def test_json_default_entry_discloses_global_file(self):
  self.assert_entry(self.describe('json_entry_file',mcp_settings_path='~/.gemini/config/mcp_config.json',mcp_http_key='serverURL'),'~/.gemini/config/mcp_config.json','agentchattr-fork')
 def test_yaml_discloses_actual_constant_entry_and_file(self):
  self.assert_entry(self.describe('yaml_settings_file',mcp_settings_path='$HERMES_HOME/config.yaml'),'$HERMES_HOME/config.yaml','agentchattr-uat')
 def test_legacy_file_and_private_modes_are_byte_unchanged(self):
  path='settings.json'
  expected='Launch merges MCP identity into '+path+' and creates a backup. Only one seat may own this fixed settings path.'
  self.assertEqual(self.describe('settings_file',mcp_settings_path=path),expected)
  for mode in ('env','env_content','flag','proxy_flag'):
   with self.subTest(mode=mode):
    self.assertEqual(self.describe(mode,mcp_env_var='FAKE_SETTINGS',mcp_flag='--mcp-config',mcp_proxy_flag_template='--mcp={url}'),PRIVATE)
