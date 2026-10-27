"""Named-key loading uses fake keys and a temporary user profile only."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import launcher


class LauncherNamedKeyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/'checkout'; self.root.mkdir()
        self.home=Path(tmp.name)/'profile'; self.home.mkdir()
        self.config={'server':{'data_dir':'data'},'agents':{
            'api':{'type':'api','api_key_env':'FAKE_KEY_A'},
            'cli':{'command':'fake','api_key_env':'UNREFERENCED'}}}
        home_patch=patch('launcher.Path.home',return_value=self.home)
        env_patch=patch.dict(os.environ,{'PATH':'fixture-path'},clear=True)
        home_patch.start(); self.addCleanup(home_patch.stop)
        env_patch.start(); self.addCleanup(env_patch.stop)

    def write(self,raw):
        (self.home/'.env').write_bytes(raw)

    def env(self):
        return launcher._server_environment(self.root,self.config)

    def test_only_strict_referenced_lines_first_match_quotes_and_crlf(self):
        self.write(b'UNREFERENCED=UNUSED_PRIVATE\r\nexport FAKE_KEY_A=bad\r\n FAKE_KEY_A=bad\r\n#FAKE_KEY_A=bad\r\nFAKE_KEY_A="FAKE_PRIVATE_A"\r\nFAKE_KEY_A=second\r\nBAD_UTF8=\xff\r\n')
        result=self.env()
        self.assertEqual(result['FAKE_KEY_A'],'FAKE_PRIVATE_A')
        self.assertNotIn('UNREFERENCED',result)
        self.assertNotIn('BAD_UTF8',result)
        self.assertFalse('FAKE_KEY_A' in os.environ, 'Parent environment was modified')
        self.assertEqual(result['PATH'],'fixture-path')

    def test_saved_api_seat_reference_is_included_but_cli_and_unknown_template_are_not(self):
        data=self.root/'data';data.mkdir()
        (data/'api_seats.json').write_text(json.dumps({'version':1,'packages':[{'seats':[
            {'adapter':'openai-compatible','provider':'api','secret_ref':'FAKE_KEY_B'},
            {'adapter':'cli','provider':'cli','secret_ref':'CLI_PRIVATE'},
            {'adapter':'openai-compatible','provider':'missing','secret_ref':'UNKNOWN_PRIVATE'}]}]}),encoding='utf-8')
        self.write(b"FAKE_KEY_B='FAKE_PRIVATE_B'\nCLI_PRIVATE=bad\nUNKNOWN_PRIVATE=bad\n")
        result=self.env()
        self.assertEqual(result['FAKE_KEY_B'],'FAKE_PRIVATE_B')
        self.assertNotIn('CLI_PRIVATE',result);self.assertNotIn('UNKNOWN_PRIVATE',result)

    def test_existing_environment_wins_including_empty_value(self):
        self.write(b'FAKE_KEY_A=file\n')
        for value in ('already-set',''):
            with self.subTest(value=value),patch.dict(os.environ,{'FAKE_KEY_A':value}):
                self.assertEqual(self.env()['FAKE_KEY_A'],value)

    def test_missing_file_missing_name_and_unreadable_file_are_harmless(self):
        self.assertNotIn('FAKE_KEY_A',self.env())
        self.write(b'NOT_REFERENCED=value\n')
        self.assertNotIn('FAKE_KEY_A',self.env())
        with patch('pathlib.Path.open',side_effect=PermissionError('PRIVATE_ERROR_SENTINEL')):
            self.assertNotIn('FAKE_KEY_A',self.env())

    def test_invalid_names_and_invalid_value_never_reach_child(self):
        self.config['agents']['api']['api_key_env']='BAD\nNAME'
        self.write(b'BAD\nNAME=private\n')
        self.assertTrue(self.env()==dict(os.environ), "Unexpected environment change")
        self.config['agents']['api']['api_key_env']='FAKE_KEY_A'
        for raw in (b'FAKE_KEY_A=bad\x00value\n',b'FAKE_KEY_A=\xff\n'):
            self.write(raw)
            self.assertNotIn('FAKE_KEY_A',self.env())

    def test_no_references_does_not_open_dotenv(self):
        self.config['agents']={}
        with patch('pathlib.Path.open',side_effect=AssertionError('No key-file read needed')):
            self.assertTrue(self.env()==dict(os.environ), "Unexpected environment change")

    def test_malformed_saved_reference_is_ignored_without_private_diagnostics(self):
        data=self.root/'data';data.mkdir()
        (data/'api_seats.json').write_text(json.dumps({'packages':[{'seats':[
            {'adapter':'openai-compatible','provider':[],'secret_ref':'FAKE_KEY_B'}]}]}),encoding='utf-8')
        self.write(b'FAKE_KEY_A=good\nFAKE_KEY_B=ignored\n')
        result=self.env()
        self.assertEqual(result['FAKE_KEY_A'],'good')
        self.assertNotIn('FAKE_KEY_B',result)

    def test_strip_environment_is_case_insensitive_on_windows(self):
        with patch('launcher.os.name','nt'):
            result=launcher.strip_environment({'fake_key_a':'private','UNRELATED':'keep'}, {'FAKE_KEY_A'})
        self.assertEqual(result, {'UNRELATED':'keep'})

    def test_spawn_enriches_only_server_child_without_logging_or_argv_leak(self):
        self.write(b'FAKE_KEY_A=FAKE_PRIVATE_SENTINEL\nUNREFERENCED=OTHER_PRIVATE\n')
        out=io.StringIO();err=io.StringIO()
        with patch('launcher.subprocess.Popen',return_value=Mock()) as spawn,redirect_stdout(out),redirect_stderr(err):
            launcher.spawn_server(self.root,Path('fixture-python'),self.config)
        args,kw=spawn.call_args
        self.assertEqual(kw.get('env',{}).get('FAKE_KEY_A'),'FAKE_PRIVATE_SENTINEL')
        self.assertNotIn('UNREFERENCED',kw['env'])
        self.assertFalse('FAKE_KEY_A' in os.environ, 'Parent environment was modified')
        self.assertNotIn('FAKE_PRIVATE_SENTINEL',str(args)+out.getvalue()+err.getvalue())
        self.assertNotIn(b'FAKE_PRIVATE_SENTINEL',(self.root/'.launcher/server.log').read_bytes())


if __name__=='__main__':unittest.main()
