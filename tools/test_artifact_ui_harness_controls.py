"""Synthetic harness controls only. No acceptance listeners/profiles/processes."""
import ast
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

from tools import verify_artifact_ui as harness
from tools import fake_artifact_client as client


class ArtifactHarnessControls(unittest.TestCase):
    def test_actual_shim_supports_every_marked_method_used_by_product(self):
        required=sorted(set(re.findall(r'\bmarked\.([a-zA-Z]+)',(harness.ROOT/'static/chat.js').read_text(encoding='utf-8'))))
        code="global.window=global;\n"+harness.marked_shim()+"\nconst assert=require('assert');\n"
        code+='for(const name of '+json.dumps(required)+')assert.equal(typeof marked[name],"function",name);\n'
        code+='marked.setOptions({breaks:true,gfm:true});assert.equal(marked.parse("<script>&"),"&lt;script&gt;&amp;");\n'
        env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH')}
        result=harness.subprocess.run(['node','-'],input=code,text=True,encoding='utf-8',capture_output=True,env=env,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_full_fixture_startup_dry_stops_before_any_listener(self):
        result=harness.run_bootstrap_control(guard_ok=True,dry_startup=True)
        self.assertEqual(result['returncode'],0,result)
        self.assertTrue(result['observed']['dry_pre_listener'])
        self.assertTrue(result['observed']['no_listener_bind'])

    def test_actual_package_validator_accepts_dummy_api_secret_reference(self):
        from api_seats import provider_templates,validate_package
        from cli_seats import cli_templates
        cfg=harness.literal_config(harness.ROOT/'.audit-tmp/synthetic',[54321,54322,54323,54324])
        package=validate_package(harness.fixture_package(),{**provider_templates(cfg),**cli_templates(cfg)})
        api=next(seat for seat in package['seats'] if seat['id']=='api')
        self.assertEqual(api['secret_ref'],'ARTIFACT_FIXTURE_DUMMY_KEY')
        self.assertEqual(harness.safe_env({},harness.ROOT,[54321]*4,'nonce',{})[api['secret_ref']],'fixture-only-no-provider')

    def test_watchdog_exits_even_when_record_and_callback_fail(self):
        with patch.object(harness,'write_json',side_effect=OSError('held evidence')), \
             patch.object(sys,'_artifact_fixture_shutdown',Mock(side_effect=RuntimeError('callback')),create=True), \
             patch('threading.Thread.start',side_effect=RuntimeError('cannot start')), \
             patch('os._exit',side_effect=SystemExit(92)):
            with self.assertRaises(SystemExit) as caught: harness.watchdog_shutdown(harness.ROOT)
        self.assertEqual(caught.exception.code,92)

    def test_non_ascii_control_auth_refuses_without_typeerror(self):
        from starlette.datastructures import Headers
        for field in (b'x-session-token',b'x-fixture-nonce'):
            raw=[(b'x-session-token',b'token'),(b'x-fixture-nonce',b'nonce')]
            raw=[(key,b'caf\xe9' if key==field else value) for key,value in raw]
            self.assertFalse(harness.authorized(Headers(raw=raw),'token','nonce'))

    def test_real_guard_child_allows_only_internal_socketpair_and_patches_after_guard(self):
        result=harness.run_bootstrap_control(guard_ok=True)
        self.assertEqual(result['returncode'],0,result)
        self.assertEqual(result['observed']['capabilities'],['artifact-v1'])
        self.assertTrue(result['observed']['asyncio_run'])
        self.assertTrue(result['observed']['plain_unowned_refused'])
        self.assertTrue(result['observed']['guard_ready'])

    def test_real_guard_child_failure_exits_91_before_protocol_patch(self):
        result=harness.run_bootstrap_control(guard_ok=False)
        self.assertEqual(result['returncode'],91,result)
        self.assertFalse(result['bootstrap_record'])
        self.assertIsNone(result['observed'])

    def test_real_guard_child_exits_on_expired_lease(self):
        result=harness.run_bootstrap_control(guard_ok=True,lease_seconds=-1)
        self.assertEqual(result['returncode'],92,result)
        self.assertTrue(result['bootstrap_record'])

    def test_watchdog_checks_parent_birth_and_closes_handle(self):
        handle=Mock();handle.poll.return_value=None
        with patch('process_identity.open_verified_process',return_value={'status':'live','process':handle}):
            self.assertFalse(harness.watchdog_expired({'pid':123},float('inf')))
        handle.close.assert_called_once()
        with patch('process_identity.open_verified_process',return_value={'status':'mismatch','process':None}):
            self.assertTrue(harness.watchdog_expired({'pid':123},float('inf')))
        with patch('process_identity.open_verified_process',side_effect=AssertionError('deadline first')):
            self.assertTrue(harness.watchdog_expired({'pid':123},0))

    def test_trusted_interpreter_is_original_checkout_without_junction(self):
        result=harness.trusted_manifest()
        original=harness.original_checkout()
        self.assertEqual(Path(result['interpreter']).resolve(),(original/'.venv-windows/Scripts/python.exe').resolve())
        self.assertEqual(Path(result['source_worktree']),harness.ROOT)
        self.assertEqual(Path(result['original_checkout']),original)
        with self.assertRaises(ValueError): harness.trusted_manifest(executable=harness.ROOT/'foreign/python.exe')

    def test_private_replace_retries_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'private.json';real=os.replace;calls=[]
            def replace(source,target):
                calls.append(1)
                if len(calls)<3: raise PermissionError('reader race')
                return real(source,target)
            with patch('os.replace',side_effect=replace): harness.write_json(path,{'ok':True})
            self.assertEqual(len(calls),3);self.assertEqual(harness.read_json(path),{'ok':True})

    def test_private_reader_tolerates_bounded_windows_permission_race(self):
        with patch.object(Path,'read_text',side_effect=[PermissionError('replace race'),'{"ready":true}']) as read:
            self.assertEqual(harness.read_json(Path('synthetic-private.json')),{'ready':True})
        self.assertEqual(read.call_count,2)

    def test_finish_refuses_missing_and_not_observed_cases(self):
        self.assertEqual(set(harness.missing_cases([])),harness.EVIDENCE_CASES)
        rows=[{'case':case,'observations':{'status':'observed'}} for case in harness.EVIDENCE_CASES]
        self.assertEqual(harness.missing_cases(rows),[])
        rows[0]['observations']['status']='not_observed'
        self.assertEqual(harness.missing_cases(rows),[rows[0]['case']])

    def test_import_constructs_no_fixture_listener_process_or_profile(self):
        for name in ('verify_artifact_ui', 'fake_artifact_client'):
            source = harness.ROOT / 'tools' / (name + '.py')
            spec = importlib.util.spec_from_file_location('fresh_' + name, source)
            module = importlib.util.module_from_spec(spec)
            with patch('socket.socket', side_effect=AssertionError('listener')), \
                 patch('subprocess.Popen', side_effect=AssertionError('process')), \
                 patch('tempfile.mkdtemp', side_effect=AssertionError('fixture')):
                spec.loader.exec_module(module)

    def test_compile_only_has_no_runtime_construction(self):
        with patch.object(sys, 'argv', ['tool', '--compile-only']), \
             patch.object(harness, 'Fixture', side_effect=AssertionError('fixture')), \
             patch.object(harness, 'runtime_server', side_effect=AssertionError('server')):
            harness.main()

    def test_bootstrap_catches_failure_and_exits_91(self):
        fake_os = types.ModuleType('os'); fake_os._exit = Mock(side_effect=SystemExit(91))
        importer = __import__
        def imports(name, *args, **kwargs):
            return fake_os if name == 'os' else importer(name, *args, **kwargs)
        with patch.object(harness, 'install_fixture_guard', side_effect=RuntimeError('guard')), \
             patch('builtins.__import__', side_effect=imports):
            with self.assertRaises(SystemExit) as caught: exec(harness.bootstrap_source(), {})
        self.assertEqual(caught.exception.code, 91)

    def test_missing_child_guard_refuses_before_any_product_work(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, '_artifact_fixture_guard', None, create=True):
            with self.assertRaises(RuntimeError): harness.require_guard()
        with patch.dict(os.environ, {'CHANNEL_FIXTURE_ROOT': str(harness.ROOT)}, clear=True), \
             patch.object(sys, '_artifact_fixture_guard', str(harness.ROOT), create=True), \
             patch.object(sys, '_channel_fixture_guard', False, create=True):
            with self.assertRaises(RuntimeError): harness.require_guard()

    def test_late_bootstrap_cannot_patch_capability(self):
        import runtime_protocol
        before = runtime_protocol.SUPPORTED_CAPABILITIES
        with patch.dict(os.environ, {'ARTIFACT_FIXTURE_REQUIRED': '1'}):
            with self.assertRaises(RuntimeError): harness.install_fixture_guard()
        self.assertEqual(runtime_protocol.SUPPORTED_CAPABILITIES, before)

    def test_guard_failure_never_enables_capability(self):
        # Synthetic import boundary: fail install_guard before runtime import.
        fake_guard = types.ModuleType('tools.channel_guard')
        fake_guard.install_guard = Mock(side_effect=PermissionError('refused'))
        fake_runtime = types.ModuleType('runtime_protocol'); fake_runtime.SUPPORTED_CAPABILITIES = ()
        with patch.dict(sys.modules, {'tools.channel_guard': fake_guard}), \
             patch.dict(os.environ, {'ARTIFACT_FIXTURE_REQUIRED': '1'}):
            runtime = sys.modules.pop('runtime_protocol', None)
            try:
                with self.assertRaises(PermissionError): harness.install_fixture_guard()
                self.assertNotIn('runtime_protocol', sys.modules)
                self.assertEqual(fake_runtime.SUPPORTED_CAPABILITIES, ())
            finally:
                if runtime is not None: sys.modules['runtime_protocol'] = runtime

    def test_unowned_loopback_port_and_external_address_refused(self):
        for address in [('127.0.0.1', 9999), ('8.8.8.8', 12345), ('0.0.0.0', 12345), '/tmp/socket']:
            with self.subTest(address=address), self.assertRaises(PermissionError):
                harness.check_address(address, [12345])
        harness.check_address(('127.0.0.1', 12345), [12345])

    def test_origin_csp_input_is_owned_and_without_credentials(self):
        for value in ('http://127.0.0.1:9999', 'https://example.com', 'http://x@127.0.0.1:12345',
                      'http://127.0.0.1:12345?token=x'):
            with self.assertRaises(ValueError): harness.owned_origin(value, [12345])
        self.assertEqual(harness.owned_origin('http://127.0.0.1:12345', [12345]), 'http://127.0.0.1:12345')

    def test_environment_strips_secrets_proxies_and_keeps_explicit_bootstrap(self):
        env = harness.safe_env({'PATH': 'trusted-path', 'OPENAI_API_KEY': 'secret', 'PYTHONPATH': 'foreign',
            'PYTHONHOME': 'foreign', 'HTTPS_PROXY': 'foreign', 'ANTHROPIC_API_KEY': 'secret',
            'CHANNEL_FIXTURE_NONCE': 'old'}, harness.ROOT / '.audit-tmp/synthetic', [12345]*4, 'new', {})
        self.assertNotIn('OPENAI_API_KEY', env); self.assertNotIn('HTTPS_PROXY', env)
        self.assertNotIn('PYTHONHOME', env); self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertEqual(env['CHANNEL_FIXTURE_NONCE'], 'new')
        self.assertIn(str(harness.ROOT), env['PYTHONPATH'])
        self.assertTrue(env['PYTHONPATH'].split(os.pathsep)[0].endswith('bootstrap'))
        self.assertEqual(env['ARTIFACT_FIXTURE_REQUIRED'], '1')
        self.assertEqual(env['PYTHONNOUSERSITE'], '1')
        for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP'):
            self.assertTrue(Path(env[key]).is_relative_to(harness.ROOT / '.audit-tmp/synthetic'))

    def test_parent_http_ignores_ambient_proxy_without_changing_host_environment(self):
        opener=Mock()
        with patch.dict(os.environ,{'HTTP_PROXY':'http://foreign:9999'}), \
             patch('urllib.request.ProxyHandler') as proxy, \
             patch('urllib.request.build_opener',return_value=opener):
            harness.local_request('http://127.0.0.1:12345',2)
            proxy.assert_called_once_with({})
            opener.open.assert_called_once_with('http://127.0.0.1:12345',timeout=2)
            self.assertEqual(os.environ['HTTP_PROXY'],'http://foreign:9999')

    def test_literal_config_has_only_local_fake_provider_and_no_strip(self):
        cfg = harness.literal_config(harness.ROOT / '.audit-tmp/synthetic', [11000, 11001, 11002, 11003])
        self.assertEqual(set(cfg['agents']), {'artifact-api', 'artifact-cli'})
        self.assertEqual(cfg['agents']['artifact-cli']['strip_env'], [])
        self.assertEqual(cfg['agents']['artifact-api']['base_url'], 'http://127.0.0.1:11003/v1')
        self.assertEqual(cfg['agents']['artifact-api']['api_key_env'], 'ARTIFACT_FIXTURE_DUMMY_KEY')

    def test_evidence_refuses_token_or_nonce_without_echoing_them(self):
        for secret in ('TOKEN_SECRET', 'NONCE_SECRET'):
            with self.assertRaises(ValueError) as caught:
                harness.public_evidence({'nested': [secret]}, ('TOKEN_SECRET', 'NONCE_SECRET'))
            self.assertNotIn(secret, str(caught.exception))
        self.assertEqual(harness.public_evidence({'status': 'ready'}, ('TOKEN_SECRET',)), {'status': 'ready'})

    def test_duplicate_or_wrong_control_headers_refused(self):
        from starlette.datastructures import Headers
        good = [(b'x-session-token', b'token'), (b'x-fixture-nonce', b'nonce')]
        self.assertTrue(harness.authorized(Headers(raw=good), 'token', 'nonce'))
        for raw in (good + [good[0]], good + [good[1]], good[:1], [(b'x-session-token', b'wrong'), good[1]]):
            self.assertFalse(harness.authorized(Headers(raw=raw), 'token', 'nonce'))

    def test_blob_browser_and_server_hash_match_exact_bom_crlf(self):
        raw = harness.CANNED.encode('utf-8')
        proof = {'base64': base64.b64encode(raw).decode(), 'browser_sha256': hashlib.sha256(raw).hexdigest(), 'filename': 'document.md'}
        self.assertEqual(harness.verify_blob(proof), raw)
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf')); self.assertIn(b'\r\n', raw)
        for key, value in [('filename', '../Downloads/document.md'), ('browser_sha256', '0'*64), ('base64', 'not-base64')]:
            broken = dict(proof); broken[key] = value
            with self.assertRaises(ValueError): harness.verify_blob(broken)

    def test_blob_wrong_bytes_even_with_correct_own_hash_refused(self):
        raw = b'wrong bytes'
        with self.assertRaises(ValueError): harness.verify_blob({'base64': base64.b64encode(raw).decode(),
            'browser_sha256': harness.hash_bytes(raw), 'filename': 'document.md'})

    def test_observer_logs_native_default_override_and_hashes_before_transfer(self):
        code = harness.browser_observer('synthetic-not-a-real-nonce')
        self.assertIn('event.preventDefault()', code)
        self.assertIn('native_default_intercepted:true', code)
        self.assertLess(code.index("crypto.subtle.digest('SHA-256'"), code.index("fetch('/__artifact_fixture/blob'"))
        self.assertIn('filename:a.download', code)
        self.assertNotIn('console.', code)

    def test_fake_cli_binding_refuses_foreign_url_and_missing_headers(self):
        good = {'mcpServers': {'agentchattr': {'url': 'http://127.0.0.1:11001/mcp', 'headers': {'Authorization': 'Bearer fixture'}}}}
        self.assertEqual(client.binding(good, [11001])[0], 'http://127.0.0.1:11001/mcp')
        for url in ('https://provider.test/mcp', 'http://127.0.0.1:9999/mcp', 'http://127.0.0.1:11001/mcp?token=x'):
            bad = deepcopy(good); bad['mcpServers']['agentchattr']['url'] = url
            with self.assertRaises(ValueError): client.binding(bad, [11001])
        good['mcpServers']['agentchattr']['headers'] = {}
        with self.assertRaises(ValueError): client.binding(good, [11001])

    def test_fake_cli_requires_both_assigned_ids(self):
        brief, dispatch = 'a'*32, 'b'*32
        self.assertEqual(client.prompt_ids("chat_artifact_brief(brief_id='"+brief+"') chat_queue_release(dispatch_id='"+dispatch+"')"), (brief, dispatch))
        with self.assertRaises(ValueError): client.prompt_ids('ordinary chat prompt')

    def test_fake_cli_calls_real_mcp_in_order_and_stops_on_refusal(self):
        # This structural order control is paired with actual reply validation.
        source = (harness.ROOT / 'tools/fake_artifact_client.py').read_text(encoding='utf-8')
        self.assertIn("session.call_tool(tool, arguments)", source)
        self.assertLess(source.index("('chat_artifact_brief', {'brief_id'"), source.index("('chat_artifact_submit', {'brief_id'"))
        self.assertLess(source.index("('chat_artifact_submit', {'brief_id'"), source.index("('chat_queue_release', {'dispatch_id'"))
        self.assertIn("if result.isError:", source)
        self.assertNotIn("'chat_send'", source)

    def test_ack_required_before_release_even_when_mcp_iserror_false(self):
        from tools.verify_artifact_ui import CANNED
        brief, dispatch = 'a'*32, 'b'*32
        good = {'status': 'admitted', 'event_id': dispatch, 'request_id': 'c'*32,
            'version_id': 'd'*32, 'sha256': hashlib.sha256(CANNED.encode()).hexdigest()}
        self.assertEqual(len(client.validate_reply('chat_artifact_submit', json.dumps(good), brief, dispatch, CANNED)), 64)
        for key, value in [('status', 'quarantined'), ('event_id', 'f'*32), ('sha256', '0'*64), ('version_id', 'not-hex')]:
            bad = dict(good); bad[key] = value
            with self.assertRaises(ValueError): client.validate_reply('chat_artifact_submit', json.dumps(bad), brief, dispatch, CANNED)
        with self.assertRaises(ValueError): client.validate_reply('chat_artifact_submit', '{"error":"refused"}', brief, dispatch, CANNED)

    def test_brief_and_release_reply_bound_to_assigned_dispatch(self):
        brief, dispatch = 'a'*32, 'b'*32
        value = {'brief': {'brief_id': brief, 'dispatch_id': dispatch}, 'packet': {}, 'parent': None}
        client.validate_reply('chat_artifact_brief', json.dumps(value), brief, dispatch, '')
        value['brief']['dispatch_id'] = 'f'*32
        with self.assertRaises(ValueError): client.validate_reply('chat_artifact_brief', json.dumps(value), brief, dispatch, '')
        client.validate_reply('chat_queue_release', json.dumps({'dispatch_id': dispatch, 'status': 'released'}), brief, dispatch, '')
        with self.assertRaises(ValueError): client.validate_reply('chat_queue_release', json.dumps({'dispatch_id': dispatch, 'status': 'cancelling'}), brief, dispatch, '')

    def test_browser_observation_bounded_and_secret_scanned(self):
        payload = {'case': 'cli', 'observations': {'literal_reader': True}}
        self.assertEqual(harness.validate_observation(payload, ('SECRET',)), payload)
        for bad in ({'case': 'unknown', 'observations': {}}, {'case': 'cli', 'observations': {'text': 'SECRET'}},
                    {'case': 'cli', 'observations': {'text': 'x'*131073}}):
            with self.assertRaises(ValueError): harness.validate_observation(bad, ('SECRET',))

    def test_external_control_refuses_foreign_root_before_read_or_network(self):
        with patch.object(harness, 'read_json', side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError): harness.external_control(harness.ROOT, 'state')

    def test_cleanup_visits_other_births_after_identity_failure(self):
        from process_identity import open_verified_process
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'audit').mkdir()
            for pid in (111,222):
                harness.write_json(root/'audit'/('artifact-bootstrap-'+str(pid)+'.json'), {'birth': {'pid': pid}})
            harness.write_json(root/'audit/guard-test.json', {'pid':111,'real_attempts':[]})
            fixture = harness.Fixture.__new__(harness.Fixture)
            fixture.root=root; fixture.token=''; fixture.nonce='nonce'; fixture.birth={'pid':111}
            fixture.handle=None; fixture.process=None; fixture.hashes={}; fixture.trusted={}; fixture.config_hashes={}
            visited=[]; handle=Mock();handle.poll.return_value=0
            def probe(birth):
                visited.append(birth['pid'])
                return {'status':'mismatch','process':None} if birth['pid']==111 else {'status':'exited','process':handle}
            with patch('process_identity.open_verified_process',side_effect=probe), \
                 patch.object(harness,'PIN_FILES',()), \
                 patch.object(harness,'trusted_manifest',return_value={}), \
                 patch.object(harness,'read_signed',side_effect=lambda root,path:harness.read_json(path)):
                self.assertFalse(fixture.close())
            self.assertEqual(set(visited),{111,222});handle.close.assert_called_once()
            self.assertTrue(any(row.get('pid')==111 for row in fixture.cleanup['unresolved']))

    def test_preplanted_root_without_creator_registration_refused(self):
        with patch.object(harness,'read_json',side_effect=FileNotFoundError()):
            with self.assertRaises(ValueError): harness.owned_manifest(harness.ROOT/'.audit-tmp/artifact-ui-preplanted')

    def test_creator_manifest_still_refuses_forbidden_ports(self):
        scratch=harness.ROOT/'.audit-tmp';scratch.mkdir(exist_ok=True)
        root=Path(tempfile.mkdtemp(prefix='artifact-ui-port-control-',dir=scratch))
        harness.register_manifest(root,{'ports':[8300,54322,54323,54324]})
        with self.assertRaises(ValueError): harness.owned_manifest(root)

    def test_signed_birth_tampering_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'audit').mkdir()
            with patch.object(harness,'owned_manifest',return_value=({},'outside-root-key')):
                harness.signed_record(root,'spawn-1.json',{'birth':{'pid':1}})
                path=root/'audit/spawn-1.json'
                self.assertEqual(harness.read_signed(root,path)['birth']['pid'],1)
                value=harness.read_json(path);value['value']['birth']['pid']=999;harness.write_json(path,value)
                with self.assertRaises(ValueError): harness.read_signed(root,path)

    def test_spawn_record_is_written_even_without_child_bootstrap(self):
        process=Mock(pid=123)
        with patch('process_identity.capture_birth',return_value={'pid':123,'creation_filetime':'1'}) as capture, \
             patch.object(harness,'signed_record') as record:
            harness.capture_spawn(harness.ROOT,process)
        capture.assert_called_once_with(123)
        self.assertEqual(record.call_args.args[1],'spawn-123.json')

    def test_failed_spawn_journal_terminates_only_just_created_handle(self):
        process=Mock(pid=123);process.poll.return_value=None
        with patch('process_identity.capture_birth',return_value={'pid':123}), \
             patch.object(harness,'signed_record',side_effect=OSError('held journal')):
            with self.assertRaises(OSError): harness.capture_spawn(harness.ROOT,process)
        process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=10)

    def test_standalone_cleanup_continues_after_mismatch_and_never_kills_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'audit').mkdir()
            handle=Mock();handle.poll.return_value=None
            with patch.object(harness,'owned_manifest',return_value=({},'outside-root-key')):
                for pid in (1,2):
                    harness.signed_record(root,'spawn-'+str(pid)+'.json',{'birth':{'pid':pid,'creation_filetime':'1'}})
                visited=[]
                def probe(birth):
                    visited.append(birth['pid'])
                    return {'status':'mismatch','process':None} if birth['pid']==1 else {'status':'live','process':handle}
                with patch('process_identity.open_verified_process',side_effect=probe):
                    result=harness.standalone_cleanup(root)
            self.assertEqual(set(visited),{1,2});self.assertEqual(result['visited'],2)
            self.assertTrue(result['unresolved']);handle.terminate.assert_called_once();handle.close.assert_called_once()

    def test_cli_entry_without_guard_exits_91_before_birth_or_settings(self):
        with patch.object(harness,'require_guard',side_effect=RuntimeError('absent')), \
             patch('process_identity.capture_birth',side_effect=AssertionError('too early')):
            with self.assertRaises(SystemExit) as caught: client.main()
        self.assertEqual(caught.exception.code,91)

    def test_delayed_create_gate_is_outside_real_source_capture(self):
        # Compile-time ordering control, not a simulated concurrency acceptance.
        tree=ast.parse((harness.ROOT/'tools/verify_artifact_ui.py').read_text(encoding='utf-8'))
        server=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='runtime_server')
        capture=next(n for n in server.body if isinstance(n,ast.FunctionDef) and n.name=='capture')
        code=ast.unparse(capture)
        self.assertLess(code.index('original_capture('),code.index("gates['create'].wait(40)"))
        self.assertNotIn('_boundary',code)

    def test_all_scripts_parse_and_source_capability_unchanged(self):
        for name in harness.PIN_FILES:
            if name.endswith('.py'): ast.parse((harness.ROOT / name).read_text(encoding='utf-8'))
        self.assertIn('SUPPORTED_CAPABILITIES = ()', (harness.ROOT / 'runtime_protocol.py').read_text(encoding='utf-8'))

    def test_no_acceptance_claim_from_finish_marker(self):
        source = (harness.ROOT / 'tools/verify_artifact_ui.py').read_text(encoding='utf-8')
        self.assertIn("'acceptance_claim': False", source)
        self.assertIn("'controller_finished': success", source)


if __name__ == '__main__':
    unittest.main()
