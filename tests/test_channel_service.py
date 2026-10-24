"""Direct lifecycle-service units with real stores, no HTTP or worker claims."""
import importlib
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import threading
from unittest.mock import Mock, patch
import unittest
import uuid

from channel_lifecycle import ChannelStore, ChannelConflict, ChannelInactive, ChannelUnavailable
from jobs import JobStore
from schedules import ScheduleStore
from summaries import SummaryStore
from router import Router
from tests import test_session_events as fixture


class ChannelServiceTests(unittest.TestCase):
    def setUp(self):
        fixture.SessionEventTests.setUp(self)
        self.module = importlib.import_module('channel_service')
        self.catalog = ChannelStore(self.root / 'channel_lifecycle.json')
        self.catalog.initialize(['general', 'review', 'peer'])
        self.jobs = JobStore(str(self.root / 'jobs.json'))
        self.schedules = ScheduleStore(str(self.root / 'schedules.json'))
        self.summaries = SummaryStore(str(self.root / 'summaries.json'))
        self.settings = {'channels': ['general', 'review', 'peer', 'unregistered']}
        self.save = Mock()
        self.cursors = Mock()
        self.service = self.module.ChannelService(self.catalog, engine=self.engine,
            messages=self.messages, jobs=self.jobs, schedules=self.schedules,
            summaries=self.summaries, queue=self.trigger.queue, settings=self.settings,
            save_settings=self.save, migrate_cursors=self.cursors,
            router=Router(['codex', 'claude']), migrate_last_active=Mock())

    def apply(self, op, channel, **kwargs):
        preview = self.service.preview(op, channel, **kwargs)
        return self.service.apply(op, channel, request_id=uuid.uuid4().hex,
            confirmation=channel, preview_token=preview['preview_token'], **kwargs)

    def test_archive_reopen_preserves_exact_history_and_blocks_publication(self):
        saved = self.messages.add('operator', 'Exact café\r\nsource', channel='review')
        before = self.messages._path.read_bytes()
        result = self.apply('archive', 'review')
        self.assertEqual(result['state'], 'archived')
        self.assertEqual(self.messages._path.read_bytes(), before)
        with self.assertRaises(ChannelInactive):
            with self.service.publication('review'):
                self.messages.add('operator', 'must not save', channel='review')
        self.assertEqual(self.messages._path.read_bytes(), before)
        self.assertEqual(self.apply('reopen', 'review')['state'], 'active')
        self.assertEqual(self.messages.get_snapshot(saved['id']), saved)
        self.assertEqual(self.messages._path.read_bytes(), before)

    def test_active_review_refusal_reports_exact_scope_without_effects(self):
        started = self.engine.start_session('review', 'review',
            {'reviewer': 'codex', 'editor': 'claude'}, 'operator',
            goal='Review source.', input_text='Frozen source')
        before = self.trigger.queue.path.read_bytes()
        for state in ('active', 'waiting', 'paused', 'awaiting_input', 'stalled', 'retrying', 'interrupted', 'prepared'):
            self.sessions._event_update(started['id'], lambda value: value.update(state=state))
            preview = self.service.preview('archive', 'review')
            self.assertTrue(any(item['kind'] == 'review' and item['session_id'] == started['id']
                                and item['run_id'] == started['run_id'] and item['state'] == state
                                for item in preview['blockers']))
            with self.subTest(state=state), self.assertRaises(ChannelConflict):
                self.service.apply('archive', 'review', request_id=uuid.uuid4().hex,
                    confirmation='review', preview_token=preview['preview_token'])
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        self.assertEqual(self.catalog.snapshot()['channels']['review'], 'active')

    def test_stale_confirmation_and_name_errors_have_no_effects(self):
        preview = self.service.preview('delete', 'review')
        self.messages.add('operator', 'new content', channel='review')
        before = self.catalog.path.read_bytes()
        with self.assertRaises(ChannelConflict):
            self.service.apply('delete', 'review', request_id=uuid.uuid4().hex,
                confirmation='review', preview_token=preview['preview_token'])
        self.assertEqual(self.catalog.path.read_bytes(), before)
        with self.assertRaises(ValueError):
            self.service.preview('archive', 'Bad Name')
        with self.assertRaises(ChannelConflict):
            self.apply('delete', 'general')

    def test_settings_projection_self_heals_and_unregistered_names_stay_unusable(self):
        self.assertEqual(self.settings['channels'], ['general', 'review', 'peer'])
        view = self.service.catalog_view()
        self.assertTrue(any(row['name'] == 'unregistered' and row['state'] == 'unregistered' for row in view['channels']))
        with self.assertRaises(ChannelInactive):
            self.service.require_active('unregistered')
        self.apply('archive', 'review')
        self.settings['channels'].append('review')  # stale settings after a catalog commit
        self.service._project(self.catalog.snapshot())
        self.assertNotIn('review', self.settings['channels'])
        self.apply('create', 'unregistered')
        self.service.require_active('unregistered')
        self.assertEqual(self.settings['unregistered_channels'], [])
        before = deepcopy(self.settings)
        self.save.side_effect = OSError('settings save failed')
        with self.assertRaises(OSError):
            self.apply('archive', 'peer')
        self.assertEqual(self.settings, before)
        self.save.side_effect = None
        self.service._project(self.catalog.snapshot())
        self.assertNotIn('peer', self.settings['channels'])

    def test_queued_only_cancel_is_separate_and_refreshes_preview(self):
        queued = self.trigger.queue.enqueue(self.peer, {'channel': 'review', 'text': 'waiting'})
        with self.assertRaises(ChannelConflict):
            self.apply('archive', 'review')
        self.apply('cancel_queued', 'review')
        self.assertEqual(self.trigger.queue.records('review')[0]['state'], 'cancelled')
        self.assertEqual(self.apply('archive', 'review')['state'], 'archived')
        self.assertEqual(self.trigger.queue.records('review')[0]['envelope'], queued['envelope'])

    def test_delete_retains_saved_records_and_emits_only_after_catalog_finish(self):
        target = self.messages.add('operator', 'delete', channel='review')
        self.messages.add_todo(target['id'])
        job = self.jobs.create('Saved job', 'task', 'review', 'operator')
        self.summaries.write('review', 'Retained summary', 'operator')
        schedule = self.schedules.create('later', ['codex'], channel='review', interval_seconds=3600)
        saved = (deepcopy(self.jobs.list_all()), deepcopy(self.schedules.list_all()), self.summaries.get('review'))
        notifications = []
        self.messages.on_delete(lambda ids: notifications.append((ids, self.catalog.snapshot()['channels']['review'])))
        result = self.apply('delete', 'review')
        self.assertEqual(result['state'], 'retired')
        self.assertEqual(notifications, [([target['id']], 'retired')])
        self.assertIsNone(self.messages.get_snapshot(target['id']))
        self.assertEqual(self.messages.get_todos(), {})
        self.assertEqual((self.jobs.list_all(), self.schedules.list_all(), self.summaries.get('review')), saved)
        row = next(row for row in self.service.catalog_view()['channels'] if row['name'] == 'review')
        self.assertEqual(row['counts']['jobs'], 1)
        self.assertEqual(row['counts']['summaries'], 1)
        self.assertEqual(row['counts']['schedules'], 1)

    def test_delete_io_failure_holds_intent_and_retry_converges_without_partial_callbacks(self):
        target = self.messages.add('operator', 'delete', channel='review')
        self.messages.add_todo(target['id'])
        preview = self.service.preview('delete', 'review')
        request = uuid.uuid4().hex
        notified = []
        self.messages.on_delete(notified.append)
        with patch.object(self.catalog, 'complete_step', side_effect=OSError('lost step mark')):
            with self.assertRaises(ChannelUnavailable):
                self.service.apply('delete', 'review', request_id=request, confirmation='review',
                                   preview_token=preview['preview_token'])
        self.assertEqual(self.messages.get_todos(), {})
        self.assertIsNotNone(self.messages.get_snapshot(target['id']))
        self.assertEqual(notified, [])
        self.assertIn('review', self.catalog.blocked_names())
        self.assertEqual(self.service.retry(request)['state'], 'retired')
        self.assertEqual(notified, [[target['id']]])

    def test_finished_delete_notifies_channel_even_when_prior_retry_already_removed_messages(self):
        self.messages.add('operator', 'delete', channel='review')
        preview = self.service.preview('delete', 'review')
        request = uuid.uuid4().hex
        events = []
        self.service.on_change(events.append)
        complete = self.catalog.complete_step
        def fail_settings_mark(request_id, step):
            if step == 'settings':
                raise OSError('lost settings step mark')
            return complete(request_id, step)
        with patch.object(self.catalog, 'complete_step', side_effect=fail_settings_mark):
            with self.assertRaises(ChannelUnavailable):
                self.service.apply('delete', 'review', request_id=request, confirmation='review',
                                   preview_token=preview['preview_token'])
        self.assertEqual(self.catalog.snapshot()['intent']['completed_steps'], ['todos', 'messages'])
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        self.assertEqual(events, [])
        result = self.service.retry(request)
        self.assertEqual(events, [{'type': 'channel_deleted', 'channel': 'review', 'revision': result['revision']}])
        with self.assertRaises(ChannelConflict):
            self.service.retry(request)
        self.assertEqual(len(events), 1)

    def test_stopped_review_does_not_hide_unresolved_retired_transport(self):
        run = self.sessions.create('review', 'review', {'reviewer': 'human', 'editor': 'human'}, 'operator')
        def change(value):
            value['state'] = 'stopped'
            value['stop_id'] = 'stopped-proof'
            value['superseded_attempts'] = [{'old_transport': {'dispatch_id': 'missing-ledger',
                'seat_identity_id': 'retired-seat', 'resolved': False}}]
        self.sessions._event_update(run['id'], change)
        preview = self.service.preview('archive', 'review')
        self.assertTrue(any(item['kind'] == 'retired_transport' and item['dispatch_id'] == 'missing-ledger'
                            for item in preview['blockers']))
        with self.assertRaises(ChannelConflict):
            self.apply('archive', 'review')

    def test_publication_vs_archive_has_one_winner_and_no_silent_message_loss(self):
        preview = self.service.preview('archive', 'review')
        barrier = threading.Barrier(2)
        def publish():
            barrier.wait()
            try:
                with self.service.publication('review'):
                    self.messages.add('operator', 'racing input', channel='review')
                return 'published'
            except ChannelInactive:
                return 'refused'
        def archive():
            barrier.wait()
            try:
                self.service.apply('archive', 'review', request_id=uuid.uuid4().hex,
                    confirmation='review', preview_token=preview['preview_token'])
                return 'archived'
            except ChannelConflict:
                return 'stale'
        with ThreadPoolExecutor(2) as pool:
            a = pool.submit(publish); b = pool.submit(archive)
            outcomes = a.result(), b.result()
        self.assertIn(outcomes, (('published', 'stale'), ('refused', 'archived')))
        self.assertEqual(len(self.messages.get_recent(channel='review')), int(outcomes[0] == 'published'))

    def test_monitor_only_updates_do_not_change_preview_token(self):
        run = self.sessions.create('review', 'review', {'reviewer': 'human', 'editor': 'human'}, 'operator')
        self.sessions._event_update(run['id'], lambda value: value.update(active_invocation={'monitoring': {}}))
        before = self.service.preview('archive', 'review')['preview_token']
        self.sessions._event_update(run['id'], lambda value: value['active_invocation']['monitoring'].update(
            last_event={'state': 'queued', 'at': 123}))
        self.assertEqual(self.service.preview('archive', 'review')['preview_token'], before)

    def test_unreadable_catalog_fails_closed_without_reseed_or_publication(self):
        self.catalog.path.write_text('{invalid', encoding='utf-8')
        before = self.messages._path.read_bytes() if self.messages._path.exists() else None
        with self.assertRaises(ChannelUnavailable):
            self.service.catalog_view()
        with self.assertRaises(ChannelUnavailable):
            with self.service.publication('peer'):
                self.messages.add('operator', 'must not save', channel='peer')
        self.assertEqual(self.messages._path.read_bytes() if self.messages._path.exists() else None, before)

    def test_reopen_discloses_overdue_enabled_schedules_and_does_not_fire_them(self):
        self.schedules.create('later', ['codex'], channel='review', interval_seconds=3600)
        with self.schedules._lock:
            self.schedules._schedules[0]['next_run'] = 1
            self.schedules._save()
        self.apply('archive', 'review')
        before = self.schedules._path.read_bytes()
        preview = self.service.preview('reopen', 'review')
        self.assertEqual(preview['overdue_schedules'], 1)
        self.apply('reopen', 'review')
        self.assertEqual(self.schedules._path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
