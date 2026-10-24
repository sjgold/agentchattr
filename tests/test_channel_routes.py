"""Channel management through real in-process middleware; no native claims."""
import asyncio
from copy import deepcopy
from contextlib import asynccontextmanager
import json
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
import app
from channel_lifecycle import ChannelStore
from tests import test_operator_routes as fixture


class ChannelRoutesTests(unittest.TestCase):
    def setUp(self):
        fixture.OperatorRoutesTests.setUp(self)
        self.service = app.channel_service
        self.service.on_change(app._on_channel_change)
        self.enterContext(patch.object(app, '_event_loop', None))
        @asynccontextmanager
        async def lifespan(api):
            app.set_event_loop(asyncio.get_running_loop())
            yield
            app.set_event_loop(None)
        api = FastAPI(lifespan=lifespan)
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-routing-test', {'server': {'port': 18300}})
        for path, handler, method in (
                ('/api/channels', app.get_channels, 'GET'),
                ('/api/channels/preview', app.preview_channel_action, 'POST'),
                ('/api/channels/apply', app.apply_channel_action, 'POST'),
                ('/api/channels/retry', app.retry_channel_action, 'POST')):
            api.add_api_route(path, handler, methods=[method])
        api.add_api_websocket_route('/ws', app.websocket_endpoint)
        self.client = self.enterContext(TestClient(api, client=('127.0.0.1', 40000)))

    def preview(self, op, channel='discussion'):
        response = self.client.post('/api/channels/preview', headers=self.headers,
                                    json={'op': op, 'channel': channel})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def apply(self, preview, **changes):
        body = {'op': preview['op'], 'channel': preview['channel'], 'request_id': uuid.uuid4().hex,
                'confirmation': preview['channel'], 'preview_token': preview['preview_token'], **changes}
        return self.client.post('/api/channels/apply', headers=self.headers, json=body)

    def test_operator_management_auth_and_archive_preserves_history(self):
        self.f.messages.add('operator', 'Exact café\r\nsource', channel='discussion')
        before = self.f.messages._path.read_bytes()
        self.assertEqual(self.client.get('/api/channels').status_code, 403)
        self.assertEqual(self.client.get('/api/channels', headers={'Authorization': 'Bearer ' + self.f.owner['token']}).status_code, 403)
        preview = self.preview('archive')
        self.assertEqual(preview['counts']['messages'], 1)
        self.assertEqual(self.apply(preview).status_code, 200)
        view = self.client.get('/api/channels', headers=self.headers)
        self.assertEqual(view.status_code, 200)
        self.assertTrue(any(row['name'] == 'discussion' and row['state'] == 'archived' for row in view.json()['channels']))
        self.assertEqual(self.f.messages._path.read_bytes(), before)

    def test_delete_requires_fresh_typed_confirmation_and_retains_job(self):
        saved = self.f.messages.add('operator', 'delete', channel='discussion')
        job = self.jobs.create('Retained', 'task', 'discussion', 'operator')
        preview = self.preview('delete')
        self.assertEqual(self.apply(preview, confirmation='wrong').status_code, 409)
        self.f.messages.add('operator', 'new content', channel='discussion')
        self.assertEqual(self.apply(preview).status_code, 409)
        self.assertIsNotNone(self.f.messages.get_snapshot(saved['id']))
        result = self.apply(self.preview('delete'))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.jobs.get(job['id']), job)
        self.assertEqual(self.f.messages.get_recent(channel='discussion'), [])

    def test_malformed_duplicate_unknown_large_and_query_requests_have_no_effects(self):
        before = self.service.catalog.path.read_bytes()
        for raw in ('[]', '{"op":"archive","op":"delete","channel":"discussion"}',
                    json.dumps({'op': 'delete', 'channel': 'discussion', 'purge_artifacts': True}),
                    json.dumps({'op': True, 'channel': 'discussion'}),
                    json.dumps({'op': 'archive', 'channel': 'x'*17000})):
            response = self.client.post('/api/channels/preview', headers=self.headers, content=raw)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.service.catalog.path.read_bytes(), before)
        self.assertEqual(self.client.get('/api/channels?unknown=1', headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post('/api/channels/retry', headers=self.headers,
            json={'request_id': True}).status_code, 400)

    def test_busy_scope_is_visible_and_apply_never_changes_active_run(self):
        started = self.f.engine.start_session('review', 'discussion', {'reviewer': 'codex', 'editor': 'claude'},
                                              'operator', input_text='Frozen source', goal='Review.')
        preview = self.preview('archive')
        self.assertTrue(any(row['session_id'] == started['id'] for row in preview['blockers']))
        before = self.f.trigger.queue.path.read_bytes()
        self.assertEqual(self.apply(preview).status_code, 409)
        self.assertEqual(self.f.trigger.queue.path.read_bytes(), before)
        self.assertEqual(self.f.sessions.get(started['id'])['state'], started['state'])

    def test_general_is_protected_on_every_management_operation(self):
        before = self.service.catalog.path.read_bytes()
        for op in ('create', 'archive', 'reopen', 'delete', 'cancel_queued', 'rename'):
            body = {'op': op, 'channel': 'general'}
            if op == 'rename':
                body['new_name'] = 'other'
            self.assertEqual(self.client.post('/api/channels/preview', headers=self.headers, json=body).status_code, 409)
        self.assertEqual(self.service.catalog.path.read_bytes(), before)

    def test_corrupt_catalog_is_visible_503_and_never_reseeded(self):
        self.service.catalog.path.write_text('{broken', encoding='utf-8')
        response = self.client.get('/api/channels', headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(str(self.f.root), response.text)
        self.assertEqual(self.service.catalog.path.read_text(encoding='utf-8'), '{broken')

    def test_separate_queued_cancel_then_archive_keeps_peer_work(self):
        queued = self.f.trigger.queue.enqueue(self.f.peer, {'channel': 'discussion', 'text': 'cancel exactly'})
        peer = self.f.trigger.queue.enqueue(self.f.peer, {'channel': 'elsewhere', 'text': 'keep'})
        self.assertEqual(self.apply(self.preview('archive')).status_code, 409)
        self.assertEqual(self.apply(self.preview('cancel_queued')).status_code, 200)
        self.assertEqual(self.apply(self.preview('archive')).status_code, 200)
        self.assertEqual(self.f.trigger.queue.owned(self.f.peer, queued['envelope']['dispatch_id'])['state'], 'cancelled')
        self.assertEqual(self.f.trigger.queue.owned(self.f.peer, peer['envelope']['dispatch_id']), peer)

    def test_restart_resumed_delete_reaches_typed_channel_broadcast(self):
        self.f.messages.add('operator', 'delete', channel='discussion')
        preview = self.preview('delete')
        request_id = uuid.uuid4().hex
        complete = self.service.catalog.complete_step
        def fail_settings(request, step):
            if step == 'settings':
                raise OSError('settings mark fault')
            return complete(request, step)
        with patch.object(app, '_broadcast', AsyncMock()) as broadcast:
            with patch.object(self.service.catalog, 'complete_step', side_effect=fail_settings):
                self.assertEqual(self.apply(preview, request_id=request_id).status_code, 503)
            self.assertEqual(broadcast.call_count, 0)
            # Fresh catalog/service reload persisted intent; bind before HTTP retry.
            from channel_service import ChannelService
            resumed = ChannelService(ChannelStore(self.service.catalog.path), engine=self.f.engine, messages=self.f.messages,
                jobs=self.jobs, schedules=self.service.schedules, summaries=self.service.summaries,
                queue=self.f.trigger.queue, settings=self.service.settings, save_settings=lambda: None,
                migrate_cursors=None, router=self.router, migrate_last_active=None)
            resumed.on_change(app._on_channel_change)
            with patch.object(app, 'channel_service', resumed):
                result = self.client.post('/api/channels/retry', headers=self.headers, json={'request_id': request_id})
            self.assertEqual(result.status_code, 200)
            events = [json.loads(call.args[0]) for call in broadcast.call_args_list]
            self.assertEqual(len([event for event in events if event['type'] == 'channel_deleted']), 1)
            self.assertTrue(any(event['type'] == 'channel_state' for event in events))

    def socket_events(self, inputs):
        frames, incoming = [], iter(inputs)
        class Socket:
            query_params = {'token': 'operator-routing-test'}
            async def accept(self): pass
            async def send_text(self, value): frames.append(json.loads(value))
            async def receive_text(self):
                event = next(incoming, None)
                if event is None:
                    await asyncio.sleep(.01)
                    raise WebSocketDisconnect()
                return json.dumps(event)
        asyncio.run(asyncio.wait_for(app.websocket_endpoint(Socket()), 2))
        return frames

    def test_settings_channel_override_is_rejected_before_any_setting_change(self):
        before = deepcopy(app.room_settings)
        frames = self.socket_events([{'type': 'update_settings', 'data': {
            'channels': ['general', 'forged'], 'username': 'must not change'}}])
        self.assertTrue(any(frame['type'] == 'channel_error' for frame in frames))
        self.assertEqual(app.room_settings, before)

    def test_legacy_mutations_without_confirmation_return_errors_and_keep_history(self):
        self.f.messages.add('operator', 'keep', channel='discussion')
        before = self.f.messages._path.read_bytes()
        frames = self.socket_events([
            {'type': 'channel_delete', 'name': 'discussion'},
            {'type': 'channel_rename', 'old_name': 'discussion', 'new_name': 'renamed'},
            {'type': 'channel_create', 'name': 'fresh'},
            {'type': 'channel_archive', 'name': 'discussion'},
            {'type': 'channel_reopen', 'name': 'discussion'}])
        self.assertEqual(len([frame for frame in frames if frame['type'] == 'channel_error']), 5)
        self.assertEqual(self.f.messages._path.read_bytes(), before)

    def test_confirmed_legacy_archive_uses_service_and_broadcasts_projection(self):
        preview = self.preview('archive')
        frames = self.socket_events([{'type': 'channel_archive', 'name': 'discussion',
            'request_id': uuid.uuid4().hex, 'confirmation': 'discussion', 'preview_token': preview['preview_token']}])
        self.assertTrue(any(frame['type'] == 'channel_state' for frame in frames))
        self.assertEqual(self.service.catalog.snapshot()['channels']['discussion'], 'archived')

    def test_reopen_preview_discloses_overdue_once_without_firing(self):
        self.service.schedules.create('later', ['claude'], channel='discussion', interval_seconds=3600)
        with self.service.schedules._lock:
            self.service.schedules._schedules[0]['next_run'] = 1
            self.service.schedules._save()
        self.assertEqual(self.apply(self.preview('archive')).status_code, 200)
        before = self.service.schedules._path.read_bytes()
        preview = self.preview('reopen')
        self.assertEqual(preview['overdue_schedules'], 1)
        self.assertEqual(self.apply(preview).status_code, 200)
        self.assertEqual(self.service.schedules._path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
