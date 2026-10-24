"""Rename intent orchestration with real stores and explicit crash seams."""
from copy import deepcopy
from pathlib import Path
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import threading
import unittest
from unittest.mock import Mock, patch
import uuid

from api_seats import atomic_json
from channel_lifecycle import ChannelConflict, ChannelInactive, ChannelStore, ChannelUnavailable, RENAME_STEPS
from channel_service import ChannelService
from jobs import JobStore
from schedules import ScheduleStore
from session_store import SessionStore
from session_engine import SessionEngine
from summaries import SummaryStore
from store import MessageStore
import mcp_bridge
from tests import test_channel_service as fixture


class ChannelRenameServiceTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelServiceTests.setUp(self)
        self.settings_path = self.root / 'settings.json'
        self.service._save_settings = lambda: atomic_json(self.settings_path, self.settings)
        self.service._project(self.catalog.snapshot())
        self.events = []
        self.service.on_change(self.events.append)
        self.cursor_path = self.root / 'mcp_cursors.json'
        atomic_json(self.cursor_path, {'reader': {'review': 8, 'job:7': 10}, 'peer': {'peer': 4}})
        cursors = patch.object(mcp_bridge, '_cursors', {})
        cursors.start()
        self.addCleanup(cursors.stop)
        self.service._migrate_cursors = lambda old, new: mcp_bridge.migrate_cursors_rename(
            old, new, strict=True, path=self.cursor_path)

    def seed(self):
        message = self.messages.add('operator', 'Exact café\r\n@all source', channel='review')
        self.messages.add_todo(message['id'])
        self.jobs.create('Retained job', 'task', 'review', 'operator')
        self.schedules.create('Retained prompt', ['codex'], channel='review', interval_seconds=3600)
        self.summaries.write('review', 'Retained summary', 'operator')
        run = self.engine.start_session('review', 'review', {'reviewer': 'alice', 'editor': 'bob'},
                                       'operator', input_text='Original source')
        self.engine.stop_session(run['id'])
        self.engine.reconcile_stops()
        return message, run

    def immutable(self):
        mutable = {self.messages._path, self.messages._todos_path, self.jobs._path,
                   self.schedules._path, self.summaries._path, self.sessions._path,
                   self.catalog.path, self.settings_path, self.cursor_path}
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file() and p not in mutable}

    def reload(self):
        self.messages = MessageStore(str(self.messages._path))
        self.jobs = JobStore(str(self.jobs._path), migrate_sort_orders=False)
        self.schedules = ScheduleStore(str(self.schedules._path), configured=True)
        self.summaries = SummaryStore(str(self.summaries._path), hold_unreadable=True)
        self.sessions = SessionStore(str(self.sessions._path))
        self.trigger.queue = self.trigger.queue._queue
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry)
        self.catalog = ChannelStore(self.catalog.path)
        self.settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
        self.service = ChannelService(self.catalog, engine=self.engine, messages=self.messages,
            jobs=self.jobs, schedules=self.schedules, summaries=self.summaries, queue=self.trigger.queue,
            settings=self.settings, save_settings=lambda: atomic_json(self.settings_path, self.settings),
            migrate_cursors=lambda old, new: mcp_bridge.migrate_cursors_rename(old, new, strict=True, path=self.cursor_path),
            router=self.service.router, migrate_last_active=self.service._migrate_last_active,
            migrate_fallbacks=self.service._migrate_fallbacks)
        self.service.on_change(self.events.append)

    def rename(self, old='review', new='renamed', request_id=None):
        preview = self.service.preview('rename', old, new_name=new)
        return self.service.apply('rename', old, new_name=new,
            request_id=request_id or uuid.uuid4().hex, confirmation=old,
            preview_token=preview['preview_token'])

    def test_rename_commits_messages_and_reserved_alias_without_redirect(self):
        saved = self.messages.add('operator', 'Exact café\r\nsource', channel='review')
        events = []
        self.service.on_change(events.append)
        result = self.rename()
        self.assertEqual(result['channel'], 'renamed')
        self.assertEqual((result['old_name'], result['new_name']), ('review', 'renamed'))
        self.assertEqual(self.messages.get_snapshot(saved['id']), {**saved, 'channel': 'renamed'})
        self.assertEqual(self.catalog.snapshot()['retired'], {'review': 'renamed'})
        self.assertEqual(events, [{'type': 'channel_renamed', 'old_name': 'review',
                                  'new_name': 'renamed', 'revision': result['revision']}])
        with self.assertRaises(ChannelInactive):
            self.service.require_active('review')
        self.service.require_active('peer')

    def test_destination_summary_collision_refuses_preview_before_intent(self):
        self.summaries.write('unregistered', 'Retained destination summary', 'operator')
        before = self.catalog.path.read_bytes(), self.summaries._path.read_bytes()
        with self.assertRaises(ChannelConflict):
            self.service.preview('rename', 'review', new_name='unregistered')
        self.assertEqual((self.catalog.path.read_bytes(), self.summaries._path.read_bytes()), before)

    def test_every_step_write_before_mark_crash_reloads_and_converges_exactly(self):
        for step in RENAME_STEPS:
            with self.subTest(step=step):
                case = ChannelRenameServiceTests()
                case.setUp()
                try:
                    message, run = case.seed()
                    before = case.immutable()
                    expected_messages = deepcopy(case.messages.get_recent(count=2**31))
                    expected_jobs = deepcopy(case.jobs.list_all())
                    expected_schedules = deepcopy(case.schedules.list_all())
                    expected_summaries = case.summaries.get_all()
                    expected_summaries['renamed'] = expected_summaries.pop('review')
                    for collection in (expected_messages, expected_jobs, expected_schedules):
                        for row in collection:
                            if row.get('channel') == 'review':
                                row['channel'] = 'renamed'
                    todos_before = case.messages._todos_path.read_bytes()
                    expected = deepcopy(case.sessions.list_all())
                    for row in expected:
                        if row.get('channel') == 'review':
                            row['channel'] = 'renamed'
                    old_settings = list(case.settings['channels'])
                    request = uuid.uuid4().hex
                    complete = case.catalog.complete_step
                    def fail(request_id, current):
                        if current == step:
                            raise OSError('fault after phase write')
                        return complete(request_id, current)
                    with patch.object(case.catalog, 'complete_step', side_effect=fail):
                        with self.assertRaises(ChannelUnavailable):
                            case.rename(request_id=request)
                    self.assertEqual(case.events, [])
                    self.assertEqual(case.settings['channels'], old_settings)
                    self.assertEqual(json.loads(case.settings_path.read_text(encoding='utf-8'))['channels'], old_settings)
                    self.assertEqual(case.catalog.snapshot()['intent']['completed_steps'], list(RENAME_STEPS[:RENAME_STEPS.index(step)]))
                    case.reload()
                    for name in ('review', 'renamed'):
                        with self.assertRaises(ChannelInactive):
                            case.service.require_active(name)
                    result = case.service.retry(request)
                    self.assertEqual(result['channel'], 'renamed')
                    self.assertEqual(case.sessions.list_all(), expected)
                    self.assertEqual(case.immutable(), before)
                    self.assertEqual(case.messages.get_recent(count=2**31), expected_messages)
                    self.assertEqual(case.jobs.list_all(), expected_jobs)
                    self.assertEqual(case.schedules.list_all(), expected_schedules)
                    self.assertEqual(case.summaries.get_all(), expected_summaries)
                    self.assertEqual(case.messages._todos_path.read_bytes(), todos_before)
                    self.assertEqual(case.messages.get_snapshot(message['id']), {**message, 'channel': 'renamed'})
                    self.assertEqual(len(case.jobs.list_all(channel='renamed')), 1)
                    self.assertEqual(len([row for row in case.schedules.list_all() if row['channel'] == 'renamed']), 1)
                    self.assertIsNotNone(case.summaries.get('renamed'))
                    self.assertEqual(len(case.events), 1)
                    with self.assertRaises(ChannelConflict):
                        case.service.retry(request)
                    self.assertEqual(len(case.events), 1)
                finally:
                    case.doCleanups()

    def test_alias_roundtrip_preserves_summary_and_foreign_alias_stays_reserved(self):
        self.seed()
        summary = self.summaries.get('review')
        self.rename()
        with self.assertRaises(ChannelConflict):
            self.service.preview('rename', 'peer', new_name='review')
        self.rename('renamed', 'review')
        self.assertEqual(self.summaries.get('review'), summary)
        self.assertEqual(self.catalog.snapshot()['retired'], {'renamed': 'review'})
        with self.assertRaises(ChannelConflict):
            self.catalog.create('renamed', expected_revision=self.catalog.snapshot()['revision'])

    def test_destination_saved_rows_and_live_transport_are_never_merged(self):
        cases = (lambda name: self.messages.add('operator', 'old data', channel=name),
                 lambda name: self.jobs.create('saved', 'task', name, 'operator'),
                 lambda name: self.schedules.create('saved', ['codex'], channel=name, interval_seconds=3600),
                 lambda name: self.sessions.create('review', name, {'reviewer': 'human', 'editor': 'human'}, 'operator'),
                 lambda name: self.trigger.queue.enqueue(self.peer, {'channel': name, 'text': 'queued'}))
        for index, create in enumerate(cases):
            with self.subTest(create=create):
                name = f'unused-{index}'
                create(name)
                before = self.catalog.path.read_bytes()
                with self.assertRaises(ChannelConflict):
                    self.service.preview('rename', 'review', new_name=name)
                self.assertEqual(self.catalog.path.read_bytes(), before)

    def test_destination_arriving_after_preview_is_refused_without_begin(self):
        preview = self.service.preview('rename', 'review', new_name='renamed')
        self.summaries.write('renamed', 'Arrived later', 'operator')
        with self.assertRaises(ChannelConflict):
            self.service.apply('rename', 'review', new_name='renamed', request_id=uuid.uuid4().hex,
                confirmation='review', preview_token=preview['preview_token'])
        self.assertIsNone(self.catalog.snapshot()['intent'])

    def test_each_step_and_same_intent_apply_release_outer_lock_for_peer(self):
        self.seed()
        request = uuid.uuid4().hex
        with patch.object(self.catalog, 'complete_step', side_effect=OSError('before first mark')):
            with self.assertRaises(ChannelUnavailable):
                self.rename(request_id=request)
        original = self.service._boundary
        main = threading.get_ident()
        local = threading.local()
        boundaries = []
        @contextmanager
        def boundary():
            local.depth = getattr(local, 'depth', 0) + 1
            try:
                with original():
                    yield
            finally:
                local.depth -= 1
            if threading.get_ident() == main and not local.depth:
                pending = self.catalog.snapshot()['intent']
                if pending:
                    with ThreadPoolExecutor(1) as pool:
                        pool.submit(self.service.require_active, 'peer').result(timeout=1)
                    boundaries.append(tuple(pending['completed_steps']))
        with patch.object(self.service, '_boundary', boundary):
            result = self.service.apply('rename', 'review', new_name='renamed', request_id=request,
                confirmation='review', preview_token='lost-ack-old-token')
        self.assertEqual(result['channel'], 'renamed')
        self.assertTrue(all(tuple(RENAME_STEPS[:index]) in boundaries for index in range(1, 8)))

    def test_final_projection_fault_is_committed_success_then_live_self_heal(self):
        self.seed()
        save = self.service._save_settings
        def fail_new():
            if 'renamed' in self.settings['channels']:
                raise OSError('post-commit projection failure')
            save()
        with patch.object(self.service, '_save_settings', side_effect=fail_new):
            result = self.rename()
        self.assertTrue(result['ok'])
        self.assertIn('projection_warning', result)
        self.assertIsNone(self.catalog.snapshot()['intent'])
        self.assertEqual(len(self.events), 1)
        self.assertIn('review', self.settings['channels'])
        self.service.catalog_view()
        self.assertIn('renamed', self.settings['channels'])
        self.assertNotIn('review', self.settings['channels'])
        self.settings['channels'] = ['general']
        self.service.preview('archive', 'peer')
        self.assertIn('renamed', self.settings['channels'])
        self.settings['channels'] = ['general']
        with self.assertRaises(ChannelConflict):
            self.service.retry(uuid.uuid4().hex)
        self.assertIn('renamed', self.settings['channels'])
        import app
        frames = []
        class Socket:
            async def send_text(inner, raw): frames.append(json.loads(raw))
        with patch.object(app, 'room_settings', self.settings), patch.object(app, 'ws_clients', {Socket()}):
            asyncio.run(app.broadcast_settings())
        self.assertIn('renamed', frames[0]['data']['channels'])

    def test_finish_fault_replays_volatile_state_and_emits_once_without_row_work(self):
        self.seed()
        request = uuid.uuid4().hex
        with patch.object(self.catalog, 'finish', side_effect=OSError('before final commit')):
            with self.assertRaises(ChannelUnavailable):
                self.rename(request_id=request)
        self.assertEqual(self.catalog.snapshot()['intent']['completed_steps'], list(RENAME_STEPS))
        self.assertEqual(self.events, [])
        self.reload()
        with patch.object(self.messages, 'rename_channel', side_effect=AssertionError('marked phase')):
            result = self.service.retry(request)
        self.assertEqual(result['channel'], 'renamed')
        self.assertEqual(len(self.events), 1)

    def test_busy_source_and_archived_source_never_begin_rename(self):
        row = self.trigger.queue.enqueue(self.peer, {'channel': 'review', 'text': 'pending'})
        with self.assertRaises(ChannelConflict):
            self.rename()
        self.assertIsNone(self.catalog.snapshot()['intent'])
        self.trigger.queue.cancel_queued_channel('review', [row['envelope']['dispatch_id']], uuid.uuid4().hex)
        self.catalog.set_state('review', 'archived', expected_revision=self.catalog.snapshot()['revision'])
        with self.assertRaises(ChannelConflict):
            self.rename()

    def test_stopped_parent_restarts_in_new_channel_with_original_briefs_intact(self):
        _, parent = self.seed()
        before = self.immutable()
        self.rename()
        child = self.sessions.prepare_restart(parent['id'], 'Genuine edit', 'rename-child')
        self.assertEqual(child['channel'], 'renamed')
        self.assertEqual(self.immutable(), before)

    def test_volatile_router_and_app_maps_migrate_idempotently_preserving_peers(self):
        import app
        self.service.router._channels = {'review': {'hop_count': 3, 'paused': True, 'guard_emitted': True},
                                         'peer': {'hop_count': 1, 'paused': False, 'guard_emitted': False}}
        expected = deepcopy(self.service.router._channels)
        expected['renamed'] = expected.pop('review')
        with patch.object(app, '_last_active_channel', 'review'), patch.object(app, '_agent_last_channel', {'codex': 'review', 'claude': 'peer'}), patch.object(mcp_bridge, '_last_read_channel', {'codex': 'review', 'claude': 'peer'}):
            self.service._migrate_last_active = app._migrate_channel_last_active
            self.service._migrate_fallbacks = mcp_bridge.migrate_fallbacks_rename
            self.rename()
            app._migrate_channel_last_active('review', 'renamed')
            mcp_bridge.migrate_fallbacks_rename('review', 'renamed')
            self.assertEqual(app._last_active_channel, 'renamed')
            self.assertEqual(app._agent_last_channel, {'codex': 'renamed', 'claude': 'peer'})
            self.assertEqual(mcp_bridge._last_read_channel, {'codex': 'renamed', 'claude': 'peer'})
        self.assertEqual(self.service.router._channels, expected)
