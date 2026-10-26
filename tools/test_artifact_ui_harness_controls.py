"""Synthetic harness controls only. No acceptance listeners/profiles/processes."""
import ast
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

from tools import verify_artifact_ui as harness
from tools import fake_artifact_client as client


class ArtifactHarnessControls(unittest.TestCase):
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
                 patch('tools.verify_channel_lifecycle.trusted_bootstrap_manifest',return_value={}):
                self.assertFalse(fixture.close())
            self.assertEqual(set(visited),{111,222});handle.close.assert_called_once()
            self.assertTrue(any(row.get('pid')==111 for row in fixture.cleanup['unresolved']))

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
