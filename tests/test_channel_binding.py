"""Actual lifecycle initializer with real owners, no configure/native claims."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import uuid

import app
import mcp_bridge
from channel_lifecycle import ChannelStore, ChannelInactive, ChannelUnavailable
from jobs import JobStore
from schedules import ScheduleStore
from tests import test_channel_import as fixture


class ChannelBindingTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelImportTests.setUp(self)
        # Remove inherited opt-in bindings so the real factory must install them.
        for owner in (self.messages, self.summaries, self.engine, self.schedules, self.jobs,
                      self.trigger.queue):
            owner._channel_policy_getter = None
        self.trigger.queue._channel_policy = None
        self.sessions.save_custom_template({'id': 'human', 'name': 'Human', 'roles': ['reader'],
            'phases': [{'name': 'Read', 'participants': ['reader'], 'prompt': 'Read.', 'is_output': True}]})
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        for name, value in {'store': self.messages, 'jobs': self.jobs, 'schedules': self.schedules,
                'summaries': self.summaries, 'session_engine': self.engine, 'session_store': self.sessions,
                'agents': self.trigger, 'registry': self.registry, 'router': self.service.router,
                'room_settings': self.settings, 'channel_service': None,
                'config': {'server': {'data_dir': str(self.root)}}}.items():
            self.patches.enter_context(patch.object(app, name, value))
        self.patches.enter_context(patch.object(mcp_bridge, 'channel_policy_getter', None))

    def initialize(self):
        app._initialize_channel_lifecycle(self.root)
        return app.channel_service

    def effects(self):
        return ({p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()},
                deepcopy(self.messages._messages), self.messages._next_id,
                deepcopy(self.sessions._sessions), self.sessions._next_id,
                deepcopy(self.sessions._templates))

    def assert_refused_without_effects(self, call, expected=ChannelInactive):
        before, error = self.effects(), None
        try:
            call()
        except Exception as exc:
            error = exc
        self.assertEqual(self.effects(), before)
        self.assertIsInstance(error, expected)

    def test_initializer_binds_previously_unbound_messages_before_archived_write(self):
        service = self.initialize()
        service.catalog.set_state('review', 'archived', expected_revision=0)
        self.assert_refused_without_effects(lambda: self.messages.add('operator', 'Must not save', channel='review'))

    def test_initializer_binds_previously_unbound_engine_before_archived_start(self):
        service = self.initialize()
        service.catalog.set_state('review', 'archived', expected_revision=0)
        self.assert_refused_without_effects(lambda: self.engine.start_session('human', 'review',
            {'reader': 'alice'}, 'operator', input_text='Must not allocate a run'))

    def owners(self):
        return (self.messages, self.summaries, self.engine, app.jobs, app.schedules)

    def seed_catalog(self):
        catalog = ChannelStore(self.root / 'channel_lifecycle.json')
        catalog.initialize(['general', 'review', 'peer'])
        return catalog

    def test_every_owner_is_same_fail_closed_getter_before_catalog_initialization(self):
        original = ChannelStore.initialize
        observed = []
        def initialize(catalog, names):
            self.assertIsNone(app.channel_service)
            self.assertTrue(all(owner._channel_policy_getter is app._channels for owner in self.owners()))
            self.assertIs(self.trigger.queue._channel_policy, app._channels)
            self.assertIs(mcp_bridge.channel_policy_getter, app._channels)
            with self.assertRaises(ChannelUnavailable):
                app._channels()
            observed.append(True)
            return original(catalog, names)
        with patch.object(ChannelStore, 'initialize', initialize):
            service = self.initialize()
        self.assertEqual(observed, [True])
        self.assertIs(app._channels(), service)

    def test_existing_archived_catalog_is_authoritative_despite_stale_settings(self):
        catalog = self.seed_catalog()
        catalog.set_state('review', 'archived', expected_revision=0)
        before = catalog.path.read_bytes()
        self.assertIn('review', self.settings['channels'])
        service = self.initialize()
        self.assertEqual(service.catalog.path.read_bytes(), before)
        self.assertNotIn('review', self.settings['channels'])
        self.assert_refused_without_effects(lambda: self.messages.add('operator', 'No resurrection', channel='review'))

    def test_corrupt_catalog_leaves_all_writers_and_new_claims_closed(self):
        path = self.root / 'channel_lifecycle.json'
        path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ChannelUnavailable):
            self.initialize()
        calls = [lambda: self.messages.add('operator', 'No save', channel='peer'),
            lambda: self.summaries.write('peer', 'No summary', 'operator'),
            lambda: self.engine.start_session('human', 'peer', {'reader': 'alice'}, 'operator'),
            lambda: self.jobs.create('No job', 'job', 'peer', 'operator'),
            lambda: self.schedules.create('No schedule', ['codex'], channel='peer', interval_seconds=60)]
        for index, call in enumerate(calls):
            with self.subTest(writer=index):
                self.assert_refused_without_effects(call, ChannelUnavailable)
        self.registry.seed({'codex': {}})
        owner = self.registry.register('codex')
        before = self.effects()
        with self.assertRaises(ChannelUnavailable):
            self.trigger.queue.claim(owner, 'algorithm-consumer')
        self.assertEqual(self.effects(), before)
        self.assertEqual(path.read_text(encoding='utf-8'), '{broken')

    def test_bound_all_store_families_refuse_archived_and_active_peer_stays_usable(self):
        service = self.initialize()
        service.catalog.set_state('review', 'archived', expected_revision=0)
        for call in [lambda: self.messages.add('operator', 'No save', channel='review'),
                     lambda: self.summaries.write('review', 'No summary', 'operator'),
                     lambda: self.jobs.create('No job', 'job', 'review', 'operator'),
                     lambda: self.schedules.create('No schedule', ['codex'], channel='review', interval_seconds=60)]:
            self.assert_refused_without_effects(call)
        saved = self.messages.add('operator', 'Peer source', channel='peer')
        self.assertEqual(saved['channel'], 'peer')
        self.assertEqual(self.summaries.write('peer', 'Peer summary', 'operator')['text'], 'Peer summary')

    def test_held_unreadable_job_and_schedule_bind_without_reset_or_blocking_chat(self):
        job_path, schedule_path = self.root / 'held-jobs.json', self.root / 'held-schedules.json'
        job_path.write_text('{broken jobs', encoding='utf-8')
        schedule_path.write_text('{broken schedules', encoding='utf-8')
        jobs = JobStore(str(job_path), migrate_sort_orders=False, hold_unreadable=True)
        schedules = ScheduleStore(str(schedule_path), configured=True)
        before = job_path.read_bytes(), schedule_path.read_bytes()
        with patch.object(app, 'jobs', jobs), patch.object(app, 'schedules', schedules):
            self.initialize()
            self.assertIs(jobs._channel_policy_getter, app._channels)
            self.assertIs(schedules._channel_policy_getter, app._channels)
            for reader in (jobs.list_all, schedules.list_all):
                with self.assertRaises(ChannelUnavailable):
                    reader()
            self.assertEqual(self.messages.add('operator', 'Unrelated chat', channel='peer')['text'], 'Unrelated chat')
        self.assertEqual((job_path.read_bytes(), schedule_path.read_bytes()), before)

    def test_readable_history_stop_and_journal_survive_catalog_unavailability(self):
        saved = self.messages.add('operator', 'Retained history', channel='review')
        run = self.engine.start_session('human', 'review', {'reader': 'alice'}, 'operator', input_text='Source')
        service = self.initialize()
        service.catalog.path.write_text('{broken', encoding='utf-8')
        self.assertEqual(self.messages.get_snapshot(saved['id']), saved)
        self.assertEqual(self.sessions.get(run['id'])['input_snapshot']['text'], 'Source')
        self.engine.stop_session(run['id'])
        self.engine.reconcile_stops()
        self.assertEqual(self.sessions.get(run['id'])['state'], 'stopped')
        self.assertEqual(service.catalog.path.read_text(encoding='utf-8'), '{broken')

    def test_persisted_pending_intent_never_auto_retries_and_only_named_channels_held(self):
        self.messages.add('operator', 'Pending retained history', channel='review')
        catalog = self.seed_catalog()
        request = uuid.uuid4().hex
        catalog.begin('rename', 'review', 'next-name', request_id=request, expected_revision=0)
        before = catalog.path.read_bytes(), self.messages._path.read_bytes()
        self.initialize()
        self.assertEqual((catalog.path.read_bytes(), self.messages._path.read_bytes()), before)
        for channel in ('review', 'next-name'):
            self.assert_refused_without_effects(lambda: self.messages.add('operator', 'No write', channel=channel))
        self.assertEqual(self.messages.add('operator', 'Peer progress', channel='peer')['channel'], 'peer')

    def test_observer_is_registered_by_initializer_before_explicit_pending_retry(self):
        self.messages.add('operator', 'Delete after explicit retry', channel='review')
        catalog = self.seed_catalog()
        request = uuid.uuid4().hex
        catalog.begin('delete', 'review', None, request_id=request, expected_revision=0)
        observed = Mock()
        with patch.object(app, '_on_channel_change', observed):
            service = self.initialize()
            observed.assert_not_called()
            service.retry(request)
        observed.assert_called_once()
        self.assertEqual(observed.call_args.args[0]['type'], 'channel_deleted')
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_saved_data_names_are_unregistered_never_auto_created_or_rewritten(self):
        self.messages.add('operator', 'Retained orphan', channel='data-only')
        self.jobs.create('Retained job', 'job', 'job-only', 'operator')
        self.schedules.create('Retained schedule', ['codex'], channel='schedule-only', interval_seconds=60)
        paths = [self.messages._path, self.jobs._path, self.schedules._path]
        before = [path.read_bytes() for path in paths]
        service = self.initialize()
        self.assertEqual([path.read_bytes() for path in paths], before)
        value = service.catalog.snapshot()
        view = {row['name']: row for row in service.catalog_view()['channels']}
        for name in ('data-only', 'job-only', 'schedule-only'):
            self.assertNotIn(name, value['channels'])
            self.assertNotIn(name, self.settings['channels'])
            self.assertEqual(view[name]['state'], 'unregistered')
            self.assert_refused_without_effects(lambda: self.messages.add('operator', 'No route', channel=name))

    def test_bound_active_owner_operations_remain_durable_and_use_new_service(self):
        service = self.initialize()
        self.assertIsNot(service, self.service)
        self.assertEqual(self.jobs.create('Peer job', 'job', 'peer', 'operator')['channel'], 'peer')
        schedule = self.schedules.create('Peer schedule', ['codex'], channel='peer', interval_seconds=60)
        self.assertEqual(self.schedules.get(schedule['id']), schedule)
        run = self.engine.start_session('human', 'peer', {'reader': 'alice'}, 'operator', input_text='Exact source')
        self.assertEqual(run['channel'], 'peer')
        self.assertEqual(self.sessions.get(run['id'])['input_snapshot']['text'], 'Exact source')


if __name__ == '__main__':
    unittest.main()
