"""Discovery contracts, stale-catalog handling and frozen per-model validation."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, MagicMock, patch

from api_seats import SeatError, SeatStore
from model_catalog import (CatalogError, ModelCatalog, model_entry, probe_antigravity,
                           probe_api, probe_claude, probe_codex, read_codex_cache)


PROVIDER = {'type': 'api', 'base_url': 'https://api.deepseek.com/v1',
            'reasoning_efforts': ['legacy-high', 'preserve-me', 'old-effort', 'saved-effort', 'new-effort']}


def seat(model='first', effort=None):
    return {'id': 'writer', 'name': 'Writer', 'adapter': 'openai-compatible',
            'provider': 'test', 'model': model, 'reasoning': effort,
            'secret_ref': '', 'launch_profile': 'standard'}


def package(value):
    return {'id': 'team', 'name': 'Team', 'seats': [value]}


def discovered(*entries, complete=True):
    return {'models': list(entries), 'source': 'test-native-metadata',
            'catalog_fetched_at': '2026-11-01T20:00:00+00:00', 'complete': complete,
            'retirement_authoritative': complete}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.store = SeatStore(self.tmp, {'test': PROVIDER})

    def refresh(self, result):
        catalog = self.store.catalog
        catalog.probe = Mock(side_effect=result) if isinstance(result, Exception) else Mock(return_value=result)
        catalog.refresh('test')
        deadline = time.monotonic() + 2
        while catalog.snapshot('test')['refreshing'] and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertFalse(catalog.snapshot('test')['refreshing'])
        return catalog.snapshot('test')

    def test_read_and_save_do_not_probe_or_substitute(self):
        self.store.catalog.probe = Mock(side_effect=AssertionError('must not probe'))
        value = package(seat('saved-retired', 'preserve-me'))
        self.store.save(value)
        self.assertEqual(self.store.list(), [value])
        described = self.store.describe_providers()[0]
        self.assertEqual(described['models'], [])
        self.assertEqual(described['reasoning_efforts'], [])
        self.assertTrue(described['model_catalog']['dynamic'])
        self.store.catalog.probe.assert_not_called()

    def test_new_model_and_model_specific_effort_are_discovered(self):
        self.refresh(discovered(model_entry('first', efforts=['low'], reasoning_known=True)))
        self.refresh(discovered(model_entry('first', efforts=['low'], reasoning_known=True),
                                model_entry('new-model', 'New model', ['high', 'ultra'], True)))
        self.assertEqual(self.store.describe_providers()[0]['models'], ['first', 'new-model'])
        self.store.save(package(seat('new-model', 'ultra')))
        with self.assertRaisesRegex(SeatError, 'does not support'):
            self.store.save(package(seat('first', 'ultra')))

    def test_complete_retirement_refuses_launch_but_saved_package_stays_readable(self):
        saved = package(seat('retired', 'old-effort'))
        self.store.save(saved)
        self.refresh(discovered(model_entry('current')))
        self.assertEqual(self.store.list(), [saved])
        with self.assertRaisesRegex(SeatError, 'unavailable'):
            self.store.catalog.provider_for_seat(saved['seats'][0])
        self.assertEqual(json.loads(self.store.path.read_text(encoding='utf-8'))['packages'], [saved])

    def test_failed_refresh_keeps_last_good_timestamp_and_does_not_retire_new_saved_id(self):
        before = self.refresh(discovered(model_entry('first')))
        after = self.refresh(CatalogError('Metadata login unavailable.'))
        self.assertEqual(after['models'], before['models'])
        self.assertEqual(after['catalog_fetched_at'], before['catalog_fetched_at'])
        self.assertFalse(after['complete'])
        self.assertTrue(after['authoritative'])
        self.assertIn('unavailable', after['error'])
        self.store.save(package(seat('new-saved-model', 'saved-effort')))
        self.store.catalog.provider_for_seat(seat('new-saved-model', 'saved-effort'))

    def test_partial_catalog_does_not_delete_or_retire_previous_models(self):
        before = self.refresh(discovered(model_entry('first'), model_entry('second')))
        after = self.refresh(discovered(model_entry('first'), complete=False))
        self.assertEqual(after['models'], before['models'])
        self.assertFalse(after['complete'])
        self.store.catalog.provider_for_seat(seat('second'))

    def test_private_cache_survives_recreation_and_is_bound_to_provider_identity(self):
        self.refresh(discovered(model_entry('first')))
        recreated = SeatStore(self.tmp, {'test': PROVIDER})
        self.assertEqual(recreated.catalog.snapshot('test')['models'][0]['id'], 'first')
        changed = {**PROVIDER, 'base_url': 'https://api.deepseek.com/other'}
        isolated = SeatStore(self.tmp, {'test': changed})
        self.assertEqual(isolated.catalog.snapshot('test')['models'], [])

    def test_credential_changes_invalidate_previous_account_catalog_without_persisting_secret(self):
        providers = {'test': {**PROVIDER, 'api_key_env': 'CATALOG_TEST_KEY'}}
        with patch.dict(os.environ, {'CATALOG_TEST_KEY': 'first-test-secret'}):
            catalog = ModelCatalog(self.tmp, providers, probe=Mock(return_value=discovered(model_entry('first'))))
            identity = catalog._identity('test')
            catalog._refresh('test', identity)
            contents = (catalog.directory / (identity + '.json')).read_text(encoding='utf-8')
            self.assertNotIn('first-test-secret', contents)
        with patch.dict(os.environ, {'CATALOG_TEST_KEY': 'second-test-secret'}):
            self.assertEqual(catalog.snapshot('test')['models'], [])

    def test_singleflight_refresh_and_no_generation_or_launch(self):
        entered, release = threading.Event(), threading.Event()
        def probe(provider):
            entered.set()
            release.wait(2)
            return discovered(model_entry('first'))
        self.store.catalog.probe = Mock(side_effect=probe)
        self.store.catalog.refresh()
        self.assertTrue(entered.wait(1))
        for _ in range(6):
            self.store.catalog.refresh()
        self.assertEqual(self.store.catalog.probe.call_count, 1)
        release.set()
        deadline = time.monotonic() + 2
        while self.store.catalog.snapshot('test')['refreshing'] and time.monotonic() < deadline:
            time.sleep(.005)

    def test_unknown_effort_metadata_preserves_saved_explicit_effort(self):
        self.refresh(discovered(model_entry('first')))
        self.store.save(package(seat('first', 'saved-effort')))
        effective = self.store.catalog.provider_for_seat(seat('first', 'saved-effort'))
        from api_seats import build_payload
        self.assertEqual(build_payload(seat('first', 'saved-effort'), effective, [])['reasoning_effort'], 'saved-effort')

    def test_frozen_worker_settings_preserve_per_model_validation_after_catalog_changes(self):
        from api_seat_runtime import SeatManager
        self.refresh(discovered(model_entry('first', efforts=['ultra'], reasoning_known=True)))
        self.store.save(package(seat('first', 'ultra')))
        manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, self.store, None, monitor=False)
        frozen = manager._effective(seat('first', 'ultra'))
        self.refresh(discovered(model_entry('first', efforts=['low'], reasoning_known=True)))
        from api_seats import build_payload
        self.assertEqual(build_payload(frozen['seat'], frozen['provider'], [])['reasoning_effort'], 'ultra')
        with self.assertRaisesRegex(SeatError, 'does not support'):
            manager._effective(seat('first', 'ultra'))

    def test_stale_effort_metadata_cannot_reject_saved_effort_at_launch(self):
        from api_seat_runtime import SeatManager
        self.store.save(package(seat('first', 'new-effort')))
        self.refresh(discovered(model_entry('first', efforts=['low'], reasoning_known=True)))
        self.refresh(CatalogError('offline'))
        manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, self.store, None, monitor=False)
        effective = manager._effective(seat('first', 'new-effort'))
        from api_seats import build_payload
        self.assertEqual(build_payload(effective['seat'], effective['provider'], [])['reasoning_effort'], 'new-effort')

    def test_unknown_metadata_enforces_configured_allowlist_for_new_choice(self):
        with self.assertRaisesRegex(SeatError, 'configured'):
            self.store.save(package(seat('first', 'arbitrary-new-effort')))

    def test_native_picker_absence_does_not_retire_unlisted_valid_model(self):
        result = discovered(model_entry('first'))
        result['retirement_authoritative'] = False
        self.refresh(result)
        self.store.catalog.provider_for_seat(seat('valid-hidden-model'))

    def test_unchanged_historical_selection_does_not_block_saving_other_changes(self):
        old = package(seat('retired', 'legacy-high'))
        self.store.save(old)
        self.refresh(discovered(model_entry('first')))
        changed = deepcopy(old)
        changed['seats'][0]['name'] = 'Renamed historical seat'
        self.store.save(changed)

    def test_partial_results_add_new_models_without_removing_old(self):
        self.refresh(discovered(model_entry('first')))
        result = self.refresh(discovered(model_entry('new-second'), complete=False))
        self.assertEqual({m['id'] for m in result['models']}, {'first', 'new-second'})

    def test_partial_and_persisted_efforts_remain_unknown_to_launch_validation(self):
        self.refresh(discovered(model_entry('first', efforts=['low'], reasoning_known=True)))
        self.refresh(discovered(model_entry('other'), complete=False))
        result = self.store.catalog.provider_for_seat(seat('first', 'new-effort'), preserve_unknown=True)
        self.assertFalse(result['_catalog_model']['reasoning_known'])
        recreated = SeatStore(self.tmp, {'test': PROVIDER})
        result = recreated.catalog.provider_for_seat(seat('first', 'new-effort'), preserve_unknown=True)
        self.assertFalse(result['_catalog_model']['reasoning_known'])

    def test_deadline_clears_spinner_retains_models_and_ignores_late_result(self):
        before = self.refresh(discovered(model_entry('first')))
        entered, release = threading.Event(), threading.Event()
        def blocked(provider):
            entered.set()
            release.wait(2)
            return discovered(model_entry('late'))
        catalog = self.store.catalog
        catalog.probe = blocked
        catalog.refresh('test')
        self.assertTrue(entered.wait(1))
        identity = catalog.states['test'][0]
        catalog._expire('test', identity, catalog.jobs['test'])
        expired = catalog.snapshot('test')
        self.assertFalse(expired['refreshing'])
        self.assertFalse(expired['complete'])
        self.assertEqual(expired['models'], before['models'])
        self.assertIn('deadline', expired['error'])
        release.set()
        deadline = time.monotonic() + 2
        while catalog.jobs and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertEqual(catalog.snapshot('test')['models'], before['models'])

    def test_another_api_credential_reference_cannot_inherit_catalog_rejection(self):
        self.refresh(discovered(model_entry('first', efforts=['low'], reasoning_known=True)))
        value = seat('first', 'new-effort')
        value['secret_ref'] = 'OTHER_ACCOUNT_KEY'
        effective = self.store.catalog.provider_for_seat(value, preserve_unknown=True)
        self.assertNotIn('_catalog_model', effective)

    def test_glm_unknown_new_effort_uses_configured_allowlist(self):
        provider = {'type': 'api', 'base_url': 'https://api.z.ai/api/coding/paas/v4',
                    'reasoning_efforts': ['high']}
        store = SeatStore(self.tmp, {'test': provider})
        store.save(package(seat('operator-model', 'high')))
        with self.assertRaisesRegex(SeatError, 'configured'):
            store.save(package(seat('operator-model', 'arbitrary-effort')))

    def test_catalog_refresh_keeps_running_team_ready_and_reuses_frozen_attempt(self):
        from tests.test_package_launch import PackageLaunchTests
        case = PackageLaunchTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        provider = case.store.providers['fake-api']
        provider.update(base_url='https://api.deepseek.com/v1', _catalog_dynamic=True, reasoning_efforts=['high'])
        case.launch_team()
        case.mark_ready('api')
        case.mark_ready('cli')
        self.assertTrue(case.manager.package_status('team')['ready'])
        attempt = case.manager.attempts['team/api']
        snapshot = attempt['snapshot'].read_bytes()
        ownership = deepcopy(attempt['ownership'])
        count = case.spawn.call_count
        catalog = case.store.catalog
        catalog.probe = Mock(return_value=discovered(model_entry('api-one', 'Fresh display name', ['high'], True)))
        catalog.refresh('fake-api')
        deadline = time.monotonic() + 2
        while catalog.snapshot('fake-api')['refreshing'] and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(case.manager.package_status('team')['ready'])
        case.manager.launch('team', 'api')
        self.assertEqual(case.spawn.call_count, count)
        self.assertEqual(attempt['snapshot'].read_bytes(), snapshot)
        self.assertEqual(attempt['ownership'], ownership)
        catalog.probe = Mock(side_effect=CatalogError('offline'))
        catalog.refresh('fake-api')
        deadline = time.monotonic() + 2
        while catalog.snapshot('fake-api')['refreshing'] and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertTrue(case.manager.package_status('team')['ready'])
        for change in ({'model': 'edited-model'}, {'reasoning': 'high'}):
            changed = deepcopy(case.package)
            changed['seats'][0].update(change)
            case.store.save(changed)
            with self.assertRaisesRegex(SeatError, 'explicit restart'):
                case.manager.launch('team', 'api')
            self.assertEqual(case.spawn.call_count, count)
            case.store.save(case.package)
        provider['temperature'] = .7
        state = case.manager.package_status('team')
        self.assertFalse(state['ready'])
        self.assertIn('settings changed', state['seats']['api']['error'])

    def test_fresh_frozen_capabilities_survive_failed_probe_for_operational_comparison(self):
        from api_seat_runtime import SeatManager
        self.refresh(discovered(model_entry('first', 'Original display', ['new-effort'], True)))
        value = seat('first', 'new-effort')
        manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, self.store, None, monitor=False)
        frozen = manager._effective(value)
        attempt = {'seat': deepcopy(value), 'effective': deepcopy(frozen)}
        self.refresh(CatalogError('offline'))
        self.assertEqual(manager._effective_for_running(value, attempt), frozen)
        edited = {**value, 'model': 'different-model'}
        current = manager._effective_for_running(edited, attempt)
        self.assertNotIn('_catalog_model', current['provider'])
        self.assertNotEqual(current, frozen)


class MetadataAdapterTests(unittest.TestCase):
    def test_claude_uses_control_initialize_only_and_resolves_aliases(self):
        models = [{'value': 'sonnet', 'resolvedModel': 'model-current', 'displayName': 'Current',
                   'supportsEffort': True, 'supportedEffortLevels': ['low', 'high']},
                  {'value': 'small', 'supportsEffort': False}]
        frame = {'type': 'control_response', 'response': {'request_id': 'catalog-init', 'subtype': 'success',
                                                        'response': {'models': models}}}
        run = Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps(frame), ''))
        result = probe_claude({'command': 'claude.exe'}, run)
        self.assertEqual([m['id'] for m in result['models']], ['sonnet', 'model-current', 'small'])
        self.assertEqual(result['models'][1]['reasoning_efforts'], ['low', 'high'])
        self.assertTrue(result['models'][2]['reasoning_known'])
        request = json.loads(run.call_args.kwargs['input'])
        self.assertEqual(request['request']['subtype'], 'initialize')
        self.assertNotIn('prompt', request)
        self.assertEqual(request['type'], 'control_request')
        self.assertIn('--no-session-persistence', run.call_args.args[0])

    def test_antigravity_empty_auth_failure_is_not_retirement(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, '', 'You are not logged into Antigravity.'))
        with self.assertRaises(CatalogError):
            probe_antigravity({'command': 'agy'}, run)
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        with self.assertRaisesRegex(CatalogError, 'no models'):
            probe_antigravity({'command': 'agy'}, run)

    def test_antigravity_parses_native_list_without_guessing_efforts(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0,
            'gemini-new-low Gemini New (Low)\nclaude-new Claude New\n', ''))
        result = probe_antigravity({'command': 'agy'}, run)
        self.assertEqual(len(result['models']), 2)
        self.assertFalse(result['models'][0]['reasoning_known'])
        self.assertEqual(run.call_args.args[0], ['agy', 'models'])

    def test_antigravity_format_change_fails_instead_of_dropping_model_rows(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0,
            'gemini-new Model New\nUPPERCASE Model Also New\n', ''))
        with self.assertRaisesRegex(CatalogError, 'format'):
            probe_antigravity({'command': 'agy'}, run)

    def test_codex_cache_is_explicitly_cached_and_filters_hidden_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'models.json'
            path.write_text(json.dumps({'fetched_at': 'last-fetch', 'models': [
                {'slug': 'first', 'visibility': 'list', 'supported_reasoning_levels': [{'effort': 'ultra'}]},
                {'slug': 'hidden', 'visibility': 'hide'}]}), encoding='utf-8')
            result = read_codex_cache(path)
        self.assertEqual(result['models'][0]['reasoning_efforts'], ['ultra'])
        self.assertEqual(len(result['models']), 1)
        self.assertFalse(result['complete'])
        self.assertEqual(result['catalog_fetched_at'], 'last-fetch')

    def test_codex_metadata_process_uses_no_threads_turns_mcp_servers_or_hooks(self):
        process = Mock()
        process.stdout = io.StringIO('{"id":1,"result":{}}\n{"id":2,"result":{"data":[]}}\n')
        before = discovered(model_entry('first'))
        refreshed = {**before, 'catalog_fetched_at': 'fresh-timestamp'}
        with patch('model_catalog.subprocess.Popen', return_value=process) as spawn, \
                patch('model_catalog.read_codex_cache', side_effect=[before, refreshed]):
            result = probe_codex({'command': 'codex.exe'})
        self.assertTrue(result['complete'])
        command = spawn.call_args.args[0]
        for setting in ('mcp_servers={}', 'features.codex_hooks=false', 'features.plugins=false'):
            self.assertIn(setting, command)
        frames = [json.loads(call.args[0]) for call in process.stdin.write.call_args_list]
        self.assertEqual([f['method'] for f in frames], ['initialize', 'initialized', 'model/list'])
        process.kill.assert_called_once()

    def test_codex_cleanup_failure_does_not_mask_success_or_skip_pipe_closes(self):
        process = Mock()
        process.stdout = Mock(wraps=io.StringIO('{"id":1,"result":{}}\n{"id":2,"result":{"data":[]}}\n'))
        # Iteration needs an actual stream, with close tracked independently.
        stream = io.StringIO('{"id":1,"result":{}}\n{"id":2,"result":{"data":[]}}\n')
        process.stdout = stream
        process.kill.side_effect = OSError('already exited')
        process.wait.side_effect = subprocess.TimeoutExpired('codex', 5)
        before = discovered(model_entry('first'))
        with patch('model_catalog.subprocess.Popen', return_value=process), \
                patch('model_catalog.read_codex_cache', side_effect=[before, {**before, 'catalog_fetched_at': 'new'}]):
            result = probe_codex({'command': 'codex.exe'})
        self.assertTrue(result['complete'])
        self.assertTrue(stream.closed)
        process.stdin.close.assert_called_once()

    def test_glm_before_first_probe_keeps_explicitly_configured_fallback_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SeatStore(directory, {'glm': {'type': 'api', 'base_url': 'https://api.z.ai/api/coding/paas/v4',
                                                  'models': ['operator-model']}})
            catalog = store.catalog.snapshot('glm')
            self.assertEqual(catalog['models'], [])
            self.assertEqual(catalog['configured_models'], ['operator-model'])
            self.assertFalse(catalog['authoritative'])

    def test_deepseek_metadata_is_get_only_with_model_specific_efforts(self):
        body = {'data': [{'id': 'first', 'name': 'First', 'effort': {'supported_levels': ['low', 'max']}}]}
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(body).encode()
        result = probe_api(PROVIDER, opener)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.method, 'GET')
        self.assertIsNone(request.data)
        self.assertEqual(request.full_url, 'https://api.deepseek.com/v1/models')
        self.assertEqual(result['models'][0]['reasoning_efforts'], ['low', 'max'])

    def test_muse_missing_effort_metadata_remains_unknown(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"data":[{"id":"new-model"}]}'
        result = probe_api({'type': 'api', 'base_url': 'https://api.meta.ai/v1'}, opener)
        self.assertFalse(result['models'][0]['reasoning_known'])
        self.assertEqual(result['models'][0]['reasoning_efforts'], [])
        self.assertIn('chat compatibility', result['capability_note'])

    def test_glm_verified_coding_models_endpoint_discovers_ids_without_inventing_efforts(self):
        opener = MagicMock()
        payload = {'data': [{'id': f'discovered-{index}', 'object': 'model', 'created': 1, 'owned_by': 'provider'}
                            for index in range(11)]}
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        result = probe_api({'type': 'api', 'base_url': 'https://api.z.ai/api/coding/paas/v4'}, opener)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.method, 'GET')
        self.assertIsNone(request.data)
        self.assertEqual(request.full_url, 'https://api.z.ai/api/coding/paas/v4/models')
        self.assertEqual(len(result['models']), 11)
        self.assertEqual(result['source'], 'glm-models-endpoint')
        self.assertTrue(all(not m['reasoning_known'] and m['reasoning_efforts'] == [] for m in result['models']))
        self.assertTrue(result['complete'])

    def test_partial_and_malformed_api_catalogs_cannot_establish_retirement(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"data":[{"id":"first"}],"has_more":true}'
        self.assertFalse(probe_api(PROVIDER, opener)['complete'])
        for raw in (b'{"data":[]}', b'{"data":[{"id":"first"},{}]}', b'{"data":[{"id":"bad\\nmodel"}]}'):
            opener.open.return_value.__enter__.return_value.read.return_value = raw
            with self.assertRaises(CatalogError):
                probe_api(PROVIDER, opener)

    def test_native_metadata_environment_strips_configured_api_keys_and_preserves_native_auth(self):
        from model_catalog import _probe_environment
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'secret', 'META_API_KEY': 'secret',
                                     'ANTHROPIC_API_KEY': 'native-login-key', 'CODEX_HOME': 'native-home'}):
            env = _probe_environment({'_catalog_strip_env': ['DEEPSEEK_API_KEY', 'META_API_KEY']})
        self.assertNotIn('DEEPSEEK_API_KEY', env)
        self.assertNotIn('META_API_KEY', env)
        self.assertEqual(env['ANTHROPIC_API_KEY'], 'native-login-key')
        self.assertEqual(env['CODEX_HOME'], 'native-home')


class CatalogRouteTests(unittest.TestCase):
    def test_refresh_requires_operator_token_and_same_origin_and_starts_no_team(self):
        import app
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        api = FastAPI()
        api.add_api_route('/api/preflight/models/refresh', app.refresh_seat_models, methods=['POST'])
        with patch.object(app, 'app', api):
            app._install_security_middleware('catalog-token', {'server': {'port': 18300}})
        store = Mock()
        store.describe_providers.return_value = [{'id': 'test'}]
        with TestClient(api) as client, patch.object(app, 'api_seat_store', store), patch.object(app, 'api_seat_manager') as manager:
            self.assertEqual(client.post('/api/preflight/models/refresh', json={}).status_code, 403)
            headers = {'x-session-token': 'catalog-token'}
            self.assertEqual(client.post('/api/preflight/models/refresh', json={},
                headers={**headers, 'origin': 'https://foreign.invalid'}).status_code, 403)
            result = client.post('/api/preflight/models/refresh', json={'provider': 'test'}, headers=headers)
            self.assertEqual(result.status_code, 202)
            self.assertEqual(result.json(), {'providers': [{'id': 'test'}]})
            self.assertEqual(result.headers['cache-control'], 'no-store')
            store.catalog.refresh.assert_called_once_with('test')
            manager.assert_not_called()


if __name__ == '__main__':
    unittest.main()
