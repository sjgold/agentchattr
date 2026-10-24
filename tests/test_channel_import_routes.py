"""Configured import HTTP, worker and append-fault evidence; no native agents."""
import asyncio
import io
import json
import threading
import time
import unittest
import uuid
from unittest.mock import patch

from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
import app
import archive
from rules import RuleStore
from tests import test_channel_import as fixture


class ChannelImportRouteTests(unittest.TestCase):
    zip_data = fixture.ChannelImportTests.zip_data
    row = fixture.ChannelImportTests.row
    effects = fixture.ChannelImportTests.effects

    def setUp(self):
        fixture.ChannelImportTests.setUp(self)
        self.rules = RuleStore(str(self.root / 'rules.json'))
        for name, value in dict(store=self.messages, jobs=self.jobs, rules=self.rules,
                summaries=self.summaries, schedules=self.schedules, registry=self.registry,
                agents=self.trigger, session_engine=self.engine, channel_service=self.service,
                room_settings=self.settings, ws_clients=set(),
                config={'server': {'data_dir': str(self.root), 'port': 18300}}).items():
            self.enterContext(patch.object(app, name, value))
        self.service._save_settings = app._save_settings
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('import-test-token', {'server': {'port': 18300}})
        api.add_api_route('/api/import', app.import_history, methods=['POST'])
        self.client = self.enterContext(TestClient(api, client=('127.0.0.1', 40000)))
        self.headers = {'X-Session-Token': 'import-test-token'}

    def test_upload_middleware_rejects_anonymous_and_agent_before_file_effects(self):
        self.registry.seed({'codex': {'label': 'Codex'}})
        seat = self.registry.register('codex')
        before = self.effects()
        for headers in ({}, {'Authorization': 'Bearer ' + seat['token']}):
            result = self.client.post('/api/import', headers=headers,
                files={'file': ('history.zip', self.zip_data([self.row('blocked')]), 'application/zip')})
            self.assertEqual(result.status_code, 403)
            self.assertEqual(self.effects(), before)

    def test_real_handler_passes_catalog_to_worker_instead_of_running_on_loop(self):
        original = archive.import_archive
        async def run():
            caller = threading.get_ident()
            def checked(*args, **kwargs):
                self.assertNotEqual(threading.get_ident(), caller)
                self.assertIs(kwargs['channel_policy'], self.service)
                return original(*args, **kwargs)
            with patch('archive.import_archive', side_effect=checked):
                result = await app.import_history(UploadFile(filename='history.zip',
                    file=io.BytesIO(self.zip_data([self.row('new-row', 'new-channel')]))))
            self.assertEqual(result.status_code, 200)
        asyncio.run(run())

    def test_loop_thread_can_check_channel_while_import_pauses_between_durable_batches(self):
        reached, release = threading.Event(), threading.Event()
        async def run():
            def between_batches(_):
                if not reached.is_set():
                    self.assertFalse(self.engine._lock._is_owned())
                    self.assertFalse(self.catalog._lock._is_owned())
                    self.assertEqual(len(self.messages._path.read_text(encoding='utf-8').splitlines()), 64)
                    reached.set()
                    self.assertTrue(release.wait(3))
            with patch('archive.time.sleep', side_effect=between_batches):
                task = asyncio.create_task(app.import_history(UploadFile(filename='history.zip',
                    file=io.BytesIO(self.zip_data([self.row('row-' + str(index)) for index in range(130)])))))
                try:
                    self.assertTrue(await asyncio.to_thread(reached.wait, 3))
                    started = time.perf_counter()
                    self.service.require_active('peer')  # Actual synchronous loop-thread handler boundary.
                    elapsed = time.perf_counter() - started
                    self.assertLess(elapsed, 1.0)
                    self.assertFalse(task.done())
                finally:
                    release.set()
                self.assertEqual((await asyncio.wait_for(task, 3)).status_code, 200)
        asyncio.run(run())
        self.assertEqual(len(self.messages.get_recent(1000)), 130)

    def test_new_imported_channel_survives_actual_settings_and_catalog_reload(self):
        result = self.client.post('/api/import', headers=self.headers,
            files={'file': ('history.zip', self.zip_data([self.row('new', 'registered')]), 'application/zip')})
        self.assertEqual(result.status_code, 200, result.text)
        from channel_lifecycle import ChannelStore
        self.assertEqual(ChannelStore(self.catalog.path).snapshot()['channels']['registered'], 'active')
        self.assertIn('registered', json.loads(app._settings_path().read_text(encoding='utf-8'))['channels'])

    def test_pending_intent_is_409_before_even_general_import_changes(self):
        self.catalog.begin('delete', 'review', None, request_id=uuid.uuid4().hex, expected_revision=0)
        before = self.effects()
        result = self.client.post('/api/import', headers=self.headers,
            files={'file': ('history.zip', self.zip_data([self.row('pending', 'general')]), 'application/zip')})
        self.assertEqual(result.status_code, 409)
        self.assertEqual(self.effects(), before)

    def test_corrupt_catalog_is_503_without_file_effects_or_path_echo(self):
        self.catalog.path.write_text('{broken', encoding='utf-8')
        before = self.effects()
        result = self.client.post('/api/import', headers=self.headers,
            files={'file': ('history.zip', self.zip_data([self.row('corrupt')]), 'application/zip')})
        self.assertEqual(result.status_code, 503)
        self.assertNotIn(str(self.root), result.text)
        self.assertEqual(self.effects(), before)

    def test_failed_batch_append_preserves_absence_or_exact_bytes_memory_and_next_id(self):
        for existing in (False, True):
            if existing:
                self.messages.add('operator', 'Existing peer', channel='peer')
            before = (self.messages._path.read_bytes() if self.messages._path.exists() else None,
                      self.messages.get_recent(), self.messages._next_id)
            with patch('store.os.fsync', side_effect=OSError('injected fsync')):
                with self.assertRaises(OSError):
                    self.messages._append_imported_batch([{'uid': 'failed', 'channel': 'peer', 'text': 'Not committed'}])
            self.assertEqual((self.messages._path.read_bytes() if self.messages._path.exists() else None,
                              self.messages.get_recent(), self.messages._next_id), before)

    def test_invalid_import_cap_maps_400_before_namespace_or_history_changes(self):
        self.settings['max_channels'] = True
        before = self.effects()
        result = self.client.post('/api/import', headers=self.headers,
            files={'file': ('history.zip', self.zip_data([self.row('bad-cap', 'new')]), 'application/zip')})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.effects(), before)

    def test_uid_committed_between_batches_is_not_imported_twice(self):
        inserted = []
        def between_batches(_):
            if not inserted and len(self.messages.get_recent(1000)) == 64:
                inserted.append(self.messages.add('operator', 'Concurrent source wins',
                    uid='row-64', channel='peer'))
        with patch('archive.time.sleep', side_effect=between_batches):
            report = archive.import_archive(self.zip_data([self.row('row-' + str(index), 'peer') for index in range(130)]),
                self.messages, self.jobs, self.rules, self.summaries, list(self.settings['channels']), channel_policy=self.service)
        saved = [row for row in self.messages.get_recent(1000) if row['uid'] == 'row-64']
        self.assertEqual(saved, inserted)
        self.assertEqual(report['sections']['messages']['duplicates'], 1)
        self.assertEqual(report['sections']['messages']['created'], 129)


if __name__ == '__main__':
    unittest.main()
