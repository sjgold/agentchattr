"""Real configured factory with explicit manager/thread/security test seams."""
import json
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import uuid

import app
import mcp_bridge
from channel_lifecycle import ChannelStore, ChannelInactive, ChannelUnavailable


class ChannelConfigureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.data = self.root / 'data'
        self.data.mkdir()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name in ('store', 'rules', 'summaries', 'jobs', 'schedules', 'router', 'agents', 'registry',
                     'session_store', 'session_engine', 'channel_service', 'config', 'api_seat_store', 'api_seat_manager', '_event_loop',
                     'artifacts', 'artifact_briefs', 'artifact_authority', 'artifact_recovery'):
            self.stack.enter_context(patch.object(app, name, None))
        self.stack.enter_context(patch.object(app, 'room_settings', {'channels': ['general'], 'username': 'operator', 'history_limit': 'all'}))
        self.stack.enter_context(patch.object(app, 'ws_clients', set()))
        self.stack.enter_context(patch.object(mcp_bridge, 'channel_policy_getter', None))
        self.manager = SimpleNamespace(boot_id=uuid.uuid4().hex, reconcile_runtime=Mock(),
            shutdown=Mock(), start_monitor=Mock(), launch_provenance=lambda instance: None)
        self.thread_starts = []
        self.events = []
        self.manager.reconcile_runtime.side_effect = lambda: self.events.append('inventory')
        self.stack.enter_context(patch.object(app, 'session_token', 'isolated-configure-token'))
        self.stack.enter_context(patch.object(app, 'agent_hats', {}))
        self.cfg = {'server': {'data_dir': str(self.data), 'host': '127.0.0.1', 'port': 18300},
                    'images': {'upload_dir': str(self.root / 'uploads')},
                    'agents': {'helper': {'label': 'Helper'}}}

    def getters(self):
        return {'messages': app.store._channel_policy_getter,
                'summaries': app.summaries._channel_policy_getter,
                'jobs': app.jobs._channel_policy_getter,
                'schedules': app.schedules._channel_policy_getter,
                'engine': app.session_engine._channel_policy_getter,
                'coordinator': app.agents.queue._channel_policy,
                'mcp': mcp_bridge.channel_policy_getter}

    def configure(self, *, trace=False):
        def thread(*args, **kwargs):
            result = Mock()
            def start():
                self.events.append('background')
                self.thread_starts.append((kwargs['target'].__name__, dict(self.getters())))
            result.start.side_effect = start
            return result
        with ExitStack() as seams:
            seams.enter_context(patch.object(app, '_install_security_middleware'))
            def manager(root, cfg, store, registry, **kwargs):
                self.manager.store, self.manager.registry = store, registry
                return self.manager
            seams.enter_context(patch('api_seat_runtime.SeatManager', side_effect=manager))
            seams.enter_context(patch.object(app.threading, 'Thread', side_effect=thread))
            if trace:
                from queue_coordinator import CoordinatedQueue
                for name, owner in (('messages', app.MessageStore), ('summaries', app.SummaryStore),
                                    ('jobs', app.JobStore), ('schedules', app.ScheduleStore),
                                    ('engine', app.SessionEngine), ('coordinator', CoordinatedQueue)):
                    original = owner.bind_channel_policy
                    def bind(instance, getter, original=original, name=name):
                        self.events.append('bind:' + name)
                        return original(instance, getter)
                    seams.enter_context(patch.object(owner, 'bind_channel_policy', bind))
                for method in ('add', 'add_once', 'add_notice'):
                    original = getattr(app.MessageStore, method)
                    def message_write(instance, *args, original=original, method=method, **kwargs):
                        self.events.append('message:' + method)
                        return original(instance, *args, **kwargs)
                    seams.enter_context(patch.object(app.MessageStore, method, message_write))
                initialize = ChannelStore.initialize
                def init(catalog, names):
                    self.events.append('catalog')
                    self.assertTrue(all(getter is app._channels for getter in self.getters().values()))
                    return initialize(catalog, names)
                seams.enter_context(patch.object(ChannelStore, 'initialize', init))
                service_type = app.ChannelService
                def service(*args, **kwargs):
                    result = service_type(*args, **kwargs)
                    self.events.append('service')
                    return result
                seams.enter_context(patch.object(app, 'ChannelService', side_effect=service))
                change = service_type.on_change
                def observer(instance, callback):
                    result = change(instance, callback)
                    self.events.append('observer')
                    return result
                seams.enter_context(patch.object(service_type, 'on_change', observer))
                resume = app.SessionEngine.resume_active_sessions
                def reconcile(instance, **kwargs):
                    self.events.append('resume')
                    return resume(instance, **kwargs)
                seams.enter_context(patch.object(app.SessionEngine, 'resume_active_sessions', reconcile))
            app.configure(self.cfg, session_token='isolated-configure-token')

    def test_actual_factory_binds_every_policy_owner_to_the_same_closed_getter(self):
        self.configure()
        for name, getter in self.getters().items():
            with self.subTest(owner=name):
                self.assertIs(getter, app._channels)
                self.assertIs(getter(), app.channel_service)

    def test_actual_configured_tick_fires_once_with_receipt_queue_and_reserved_cadence(self):
        self.configure()
        owner = app.registry.register('helper')
        with patch('schedules.time.time', return_value=100):
            row = app.schedules.create('Configured fire', [owner['name']], channel='general',
                                       interval_seconds=60, send_at=101)
        with patch('schedules.time.time', return_value=200), patch('mcp_bridge.is_online', return_value=True):
            app._run_schedule_tick()
        messages = app.store.get_recent(10, channel='general')
        self.assertEqual(len(messages), 1)
        receipt = messages[0]['metadata']['recipient_routing']
        self.assertEqual(receipt['origin'], 'schedule')
        self.assertEqual([target['identity_id'] for target in receipt['recipients']], [owner['identity_id']])
        records = app.agents.queue.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['envelope']['target_identity_id'], owner['identity_id'])
        saved = app.schedules.get(row['id'])
        self.assertEqual((saved['last_run'], saved['next_run']), (200, 260))
        scheduler = [getters for name, getters in self.thread_starts if name == '_schedule_runner']
        self.assertEqual(len(scheduler), 1)
        self.assertIs(scheduler[0]['schedules'], app._channels)

    def test_pre_lifecycle_settings_upgrade_preserves_rows_and_exposes_data_only_name(self):
        settings = {'channels': ['general', 'dev'], 'username': 'operator'}
        (self.data / 'settings.json').write_text(json.dumps(settings), encoding='utf-8')
        messages = [{'id': 0, 'uid': 'retained-dev', 'sender': 'operator', 'text': 'Keep exact source', 'channel': 'dev'},
                    {'id': 1, 'uid': 'retained-orphan', 'sender': 'operator', 'text': 'Orphan history', 'channel': 'data-only'}]
        (self.data / 'agentchattr_log.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in messages), encoding='utf-8')
        (self.data / 'jobs.json').write_text(json.dumps([{'id': 1, 'uid': 'job-dev', 'channel': 'dev',
            'title': 'Retained', 'status': 'open', 'sort_order': 1, 'messages': []}]), encoding='utf-8')
        (self.data / 'schedules.json').write_text(json.dumps([{'id': 'due-dev', 'channel': 'dev', 'prompt': 'Retained prompt',
            'targets': ['helper'], 'next_run': 1, 'active': True, 'one_shot': False, 'interval_seconds': 60, 'last_run': None}]), encoding='utf-8')
        paths = [self.data / name for name in ('agentchattr_log.jsonl', 'jobs.json', 'schedules.json')]
        before = [path.read_bytes() for path in paths]
        self.assertFalse((self.data / 'channel_lifecycle.json').exists())
        self.configure()
        self.assertEqual([path.read_bytes() for path in paths], before)
        self.assertEqual(app.channel_service.catalog.snapshot()['channels'], {'general': 'active', 'dev': 'active'})
        app.store.add('operator', 'Dev remains publishable', channel='dev')
        from channel_lifecycle import ChannelInactive
        with self.assertRaises(ChannelInactive):
            app.store.add('operator', 'Must not auto-register', channel='data-only')
        view = {row['name']: row for row in app.channel_service.catalog_view()['channels']}
        self.assertIn('data-only', view)
        self.assertEqual(view['data-only']['state'], 'unregistered')

    def test_actual_startup_binding_catalog_observer_and_thread_order(self):
        self.configure(trace=True)
        for name in ('messages', 'summaries', 'jobs', 'schedules', 'engine', 'coordinator'):
            self.assertLess(self.events.index('bind:' + name), self.events.index('catalog'))
        for before, after in zip(('catalog', 'service', 'observer', 'inventory', 'resume'),
                                 ('service', 'observer', 'inventory', 'resume', 'background')):
            self.assertLess(self.events.index(before), self.events.index(after))
        first_bind = min(index for index, event in enumerate(self.events) if event.startswith('bind:'))
        before_service = self.events[first_bind:self.events.index('service')]
        self.assertFalse(any(event.startswith('message:') for event in before_service),
                         'No startup MessageStore.add* may run before the channel service exists.')
        self.assertTrue(self.thread_starts)
        for _, getters in self.thread_starts:
            self.assertTrue(all(getter is app._channels for getter in getters.values()))

    def test_corrupt_catalog_binds_every_owner_but_all_representative_writes_refuse(self):
        path = self.data / 'channel_lifecycle.json'
        path.write_text('{broken catalog', encoding='utf-8')
        self.configure()
        owner = app.registry.register('helper')
        before = {p.relative_to(self.data).as_posix(): p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
        calls = {'messages': lambda: app.store.add('operator', 'No write', channel='general'),
                 'summaries': lambda: app.summaries.write('general', 'No summary', 'operator'),
                 'jobs': lambda: app.jobs.create('No job', 'job', 'general', 'operator'),
                 'schedules': lambda: app.schedules.create('No prompt', [owner['name']], interval_seconds=60),
                 'engine': lambda: app.session_engine.start_session('missing', 'general', {'r': 'Human'}, 'operator'),
                 'coordinator': lambda: app.agents.queue.claim(owner, 'algorithm-consumer')}
        for name, getter in self.getters().items():
            with self.subTest(owner=name):
                self.assertIs(getter, app._channels)
                if name == 'mcp':
                    self.assertIn('unavailable', mcp_bridge.chat_send('operator', 'No write', channel='general'))
                else:
                    with self.assertRaises(ChannelUnavailable):
                        calls[name]()
                after = {p.relative_to(self.data).as_posix(): p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
                self.assertEqual(after, before)
        self.assertEqual(path.read_text(encoding='utf-8'), '{broken catalog')

    def test_pending_delete_holds_only_its_channel_then_operator_retry_broadcasts_deletion(self):
        catalog = ChannelStore(self.data / 'channel_lifecycle.json')
        catalog.initialize(['general', 'review', 'peer'])
        request_id = uuid.uuid4().hex
        catalog.begin('delete', 'review', None, request_id=request_id, expected_revision=0)
        rows = [{'id': 0, 'uid': 'held', 'sender': 'operator', 'text': 'Held history', 'channel': 'review'},
                {'id': 1, 'uid': 'peer', 'sender': 'operator', 'text': 'Peer history', 'channel': 'peer'}]
        history = self.data / 'agentchattr_log.jsonl'
        history.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        before = history.read_bytes()
        self.configure()
        self.assertEqual(history.read_bytes(), before)
        self.assertIsNotNone(app.channel_service.catalog.snapshot()['intent'])
        with self.assertRaises(ChannelInactive):
            app.store.add('operator', 'Held write', channel='review')
        app.store.add('operator', 'Peer works', channel='peer')
        frames = []
        class Client:
            async def send_text(inner, raw):
                frames.append(json.loads(raw))
        async def exercise():
            from starlette.requests import Request
            app._event_loop = asyncio.get_running_loop()
            app.ws_clients.add(Client())
            async def receive():
                return {'type': 'http.request', 'body': json.dumps({'request_id': request_id}).encode(), 'more_body': False}
            request = Request({'type': 'http', 'method': 'POST', 'path': '/api/channels/retry',
                'query_string': b'', 'headers': [], 'state': {'auth_origin': 'operator'}}, receive)
            response = await app.retry_channel_action(request)
            self.assertEqual(response.status_code, 200)
            for _ in range(5):
                await asyncio.sleep(0)
        asyncio.run(exercise())
        deleted = [frame for frame in frames if frame.get('type') == 'channel_deleted']
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]['channel'], 'review')
        self.assertEqual(app.channel_service.catalog.snapshot()['channels']['review'], 'retired')
        self.assertEqual(app.store.get_recent(channel='review'), [])
        self.assertEqual(len(app.store.get_recent(channel='peer')), 2)

    def test_configured_unreadable_summary_path_holds_owner_and_chat_still_works(self):
        path = self.data / 'summaries.json'
        path.mkdir()
        marker = path / 'retained.txt'
        marker.write_bytes(b'do not replace this directory')
        self.configure()
        self.assertIsNotNone(app.channel_service)
        with self.assertRaises(ChannelUnavailable):
            app.summaries.get_all()
        with patch.object(mcp_bridge, 'summaries', app.summaries), patch.object(mcp_bridge, 'session_engine', None):
            answer = mcp_bridge.chat_summary(action='read', sender='', channel='general')
        self.assertIn('summaries are held', answer)
        self.assertNotIn(str(path), answer)
        frames = []
        class Socket:
            query_params = {'token': 'isolated-configure-token'}
            reads = 0
            async def accept(inner): pass
            async def send_text(inner, raw): frames.append(json.loads(raw))
            async def receive_text(inner):
                from fastapi import WebSocketDisconnect
                inner.reads += 1
                if inner.reads > 1:
                    raise WebSocketDisconnect()
                return json.dumps({'type': 'message', 'text': 'Chat works with held summaries',
                                   'channel': 'general', 'selected_recipients': []})
        asyncio.run(app.websocket_endpoint(Socket()))
        self.assertTrue(any(frame.get('type') == 'history_complete' for frame in frames))
        self.assertTrue(any(frame.get('type') == 'message_accepted' for frame in frames))
        self.assertEqual(marker.read_bytes(), b'do not replace this directory')
        self.assertTrue(path.is_dir())

    def test_configured_rename_uses_owned_cursor_file_and_migrates_runtime_maps(self):
        (self.data / 'settings.json').write_text(json.dumps({'channels': ['general', 'dev', 'peer']}), encoding='utf-8')
        cursor_path = self.data / 'mcp_cursors.json'
        cursor_path.write_text(json.dumps({'reader': {'dev': 8, 'peer': 4, 'job:7': 99}}), encoding='utf-8')
        foreign = self.root / 'foreign-cursors.json'
        with patch.object(mcp_bridge, '_cursors', {}), patch.object(mcp_bridge, '_CURSORS_FILE', foreign), patch.object(mcp_bridge, '_last_read_channel', {'reader': 'dev', 'peer': 'peer'}), patch.object(app, '_last_active_channel', 'dev'), patch.object(app, '_agent_last_channel', {'reader': 'dev', 'peer': 'peer'}):
            self.configure()
            message = app.store.add('operator', 'Retained source', channel='dev')
            app.router._get_ch('dev')['hop_count'] = 2
            preview = app.channel_service.preview('rename', 'dev', new_name='qa')
            result = app.channel_service.apply('rename', 'dev', new_name='qa', request_id=uuid.uuid4().hex,
                confirmation='dev', preview_token=preview['preview_token'])
            self.assertEqual(result['channel'], 'qa')
            self.assertEqual(app.store.get_snapshot(message['id']), {**message, 'channel': 'qa'})
            self.assertEqual(json.loads(cursor_path.read_text(encoding='utf-8')),
                             {'reader': {'qa': 8, 'peer': 4, 'job:7': 99}})
            self.assertFalse(foreign.exists())
            self.assertEqual(mcp_bridge._last_read_channel, {'reader': 'qa', 'peer': 'peer'})
            self.assertEqual(app._last_active_channel, 'qa')
            self.assertEqual(app._agent_last_channel, {'reader': 'qa', 'peer': 'peer'})
            self.assertNotIn('dev', app.router._channels)
            self.assertEqual(app.router._channels['qa']['hop_count'], 2)

    def test_summary_upgrade_preserves_odd_names_and_optional_legacy_fields(self):
        (self.data / 'settings.json').write_text(json.dumps({'channels': ['general', 'dev']}), encoding='utf-8')
        saved = {'general': {'text': 'Valid general summary', 'author': 'operator',
                             'message_id': 0, 'updated_at': 123.5},
                 'Old Name': {'text': 'Read-only legacy data'},
                 'dev': {'text': 'Legacy without message_id', 'author': 'helper', 'updated_at': 124}}
        path = self.data / 'summaries.json'
        path.write_text(json.dumps(saved), encoding='utf-8')
        before = path.read_bytes()
        self.configure()
        self.assertEqual(app.summaries.get_all(), saved)
        self.assertEqual(app.summaries.get('general'), saved['general'])
        self.assertEqual(app.summaries.get('dev'), saved['dev'])
        view = {row['name']: row for row in app.channel_service.catalog_view()['channels']}
        self.assertEqual(view['Old Name']['state'], 'unregistered')
        with self.assertRaises(ValueError):
            app.summaries.write('Old Name', 'Must stay read-only', 'operator')
        self.assertEqual(path.read_bytes(), before)

    def test_configured_held_schedules_bootstrap_reports_error_but_chat_stays_available(self):
        path = self.data / 'schedules.json'
        path.write_text('{broken schedules', encoding='utf-8')
        self.configure()
        self.assertIsNotNone(app.channel_service)
        self.assertTrue(app.schedules.load_error)
        frames, error = [], None
        class Socket:
            query_params = {'token': 'isolated-configure-token'}
            reads = 0
            async def accept(inner): pass
            async def send_text(inner, raw): frames.append(json.loads(raw))
            async def receive_text(inner):
                from fastapi import WebSocketDisconnect
                inner.reads += 1
                if inner.reads > 1:
                    raise WebSocketDisconnect()
                return json.dumps({'type': 'message', 'text': 'Chat remains available',
                                   'channel': 'general', 'selected_recipients': []})
        try:
            asyncio.run(app.websocket_endpoint(Socket()))
        except Exception as caught:
            error = caught
        self.assertIsNone(error, 'A held schedule store must not disconnect the chat socket.')
        payload = next(frame for frame in frames if frame.get('type') == 'schedules')
        self.assertIn('error', payload)
        self.assertNotIn('data', payload)
        self.assertTrue(any(frame.get('type') == 'history_complete' for frame in frames))
        self.assertTrue(any(frame.get('type') == 'message_accepted' for frame in frames))
        self.assertEqual(path.read_text(encoding='utf-8'), '{broken schedules')


if __name__ == '__main__':
    unittest.main()
