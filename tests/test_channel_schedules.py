"""Real schedule/catalog and synchronous tick units, without native/HTTP claims."""
from contextlib import ExitStack
from copy import deepcopy
import json
import unittest
from unittest.mock import Mock, patch

import app
from channel_lifecycle import ChannelInactive, ChannelUnavailable
from schedules import ScheduleStore
from tests import test_channel_import as fixture


class ChannelScheduleTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelImportTests.setUp(self)
        self.schedules.bind_channel_policy(lambda: self.service)
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        for name, value in {'schedules': self.schedules, 'channel_service': self.service,
                            'session_engine': self.engine, 'room_settings': self.settings}.items():
            self.patches.enter_context(patch.object(app, name, value))

    def effects(self, store):
        return (store._path.read_bytes() if store._path.exists() else None,
                deepcopy(store._schedules))

    def due(self, channel='review', *, one_shot=False, prompt='Exact scheduled prompt', targets=None):
        with patch('schedules.time.time', return_value=100):
            return self.schedules.create(prompt, ['codex'] if targets is None else targets,
                channel=channel, interval_seconds=60, one_shot=one_shot, send_at=101)

    def tick(self, now=200, publish=None):
        with patch.object(app, '_publish_operator_message', publish or Mock(return_value={'uid': 'saved'})), \
                patch('schedules.time.time', return_value=now):
            app._run_schedule_tick()

    def configured(self, name='configured.json', *, bind=True):
        store = ScheduleStore(str(self.root / name), configured=True)
        if bind:
            store.bind_channel_policy(lambda: self.service)
        return store

    def test_bound_configured_archived_create_refuses_before_disk_memory_or_callbacks(self):
        configured = ScheduleStore(str(self.root / 'configured-schedules.json'), configured=True)
        configured.bind_channel_policy(lambda: self.service)
        self.catalog.set_state('review', 'archived', expected_revision=0)
        callback = Mock()
        configured.on_change(callback)
        before = self.effects(configured)
        with self.assertRaises(ChannelInactive):
            configured.create('Do not save', ['codex'], channel='review', interval_seconds=60)
        self.assertEqual(self.effects(configured), before)
        callback.assert_not_called()

    def test_actual_tick_prefilters_archived_due_row_and_fires_active_peer(self):
        archived, peer = self.due(), self.due('peer')
        self.catalog.set_state('review', 'archived', expected_revision=0)
        publish = Mock(return_value={'id': 0, 'uid': 'saved-operator-message'})
        with patch.object(app, '_publish_operator_message', publish), patch('schedules.time.time', return_value=200):
            app._run_schedule_tick()
        self.assertEqual(self.schedules.get(archived['id']), archived)
        publish.assert_called_once()
        self.assertEqual(publish.call_args.kwargs['channel'], 'peer')
        self.assertEqual(self.schedules.get(peer['id'])['last_run'], 200)
        self.assertEqual(self.schedules.get(peer['id'])['next_run'], 260)

    def test_configured_unreadable_schema_is_held_not_empty_and_never_rewritten(self):
        valid = {'id': 'row', 'channel': 'review', 'targets': ['codex'], 'next_run': 101,
                 'active': True, 'one_shot': False, 'unknown_metadata': {'keep': True}}
        malformed = ['{broken', '{}', '[null]', json.dumps([valid, valid]),
            json.dumps([{**valid, 'next_run': True}]), json.dumps([{**valid, 'next_run': float('nan')}]),
            json.dumps([{**valid, 'active': 1}]), json.dumps([{**valid, 'targets': [1]}])]
        path = self.root / 'configured.json'
        for content in malformed:
            with self.subTest(content=content):
                path.write_text(content, encoding='utf-8')
                before = path.read_bytes()
                store = self.configured()
                for read in (store.list_all, store.run_due, lambda: store.get('row')):
                    with self.assertRaises(ChannelUnavailable):
                        read()
                self.assertEqual(path.read_bytes(), before)
        path.write_text(json.dumps([valid]), encoding='utf-8')
        store = self.configured()
        self.assertEqual(store.get('row')['unknown_metadata'], {'keep': True})

    def test_closed_then_bound_writes_and_actual_archived_row_guards(self):
        store = self.configured(bind=False)
        before = self.effects(store)
        with self.assertRaises(ChannelUnavailable):
            store.create('Closed', ['codex'], channel='peer', interval_seconds=60)
        self.assertEqual(self.effects(store), before)
        store.bind_channel_policy(lambda: self.service)
        with patch('schedules.time.time', return_value=100):
            row = store.create('Keep', ['codex'], channel='review', interval_seconds=60, send_at=101)
        self.catalog.set_state('review', 'archived', expected_revision=0)
        callback = Mock()
        store.on_change(callback)
        for call in (lambda: store.toggle(row['id']), lambda: store.delete(row['id']),
                     lambda: store.mark_run(row['id']), lambda: store.begin_attempt(row['id'], now=200),
                     lambda: store.finish_attempt(row['id'], success=False, error_code='internal', now=200)):
            with self.subTest(call=call):
                before = self.effects(store)
                with self.assertRaises(ChannelInactive):
                    call()
                self.assertEqual(self.effects(store), before)
        callback.assert_not_called()
        self.assertEqual(store.get(row['id']), row)

    def test_atomic_faults_restore_exact_disk_memory_and_suppress_callbacks(self):
        row = self.due()
        observed = Mock()
        self.schedules.on_change(observed)
        calls = [lambda: self.due('peer'), lambda: self.schedules.toggle(row['id']),
            lambda: self.schedules.delete(row['id']), lambda: self.schedules.mark_run(row['id']),
            lambda: self.schedules.begin_attempt(row['id'], now=200),
            lambda: self.schedules.finish_attempt(row['id'], success=False, error_code='internal', now=200)]
        for index, call in enumerate(calls):
            with self.subTest(operation=index):
                before = self.effects(self.schedules)
                with patch('schedules.atomic_json', side_effect=OSError('local atomic failure')) as writer:
                    with self.assertRaises(OSError):
                        call()
                    writer.assert_called_once()
                self.assertEqual(self.effects(self.schedules), before)
        observed.assert_not_called()

    def test_begin_reserves_once_and_finish_never_readvances_reserved_time(self):
        row = self.due()
        self.assertIsNone(self.schedules.begin_attempt(row['id'], now=100))
        attempt = self.schedules.begin_attempt(row['id'], now=200)
        self.assertEqual((attempt['last_attempt_at'], attempt['next_run']), (200, 260))
        self.assertIsNone(self.schedules.begin_attempt(row['id'], now=200))
        attempt['targets'].append('outside')
        self.schedules.finish_attempt(row['id'], success=False, error_code='delivery_unconfirmed', now=205)
        failed = self.schedules.get(row['id'])
        self.assertEqual(failed['next_run'], 260)
        self.assertIsNone(failed['last_run'])
        self.assertEqual(failed['failure_count'], 1)
        self.assertEqual(failed['last_error'], 'delivery_unconfirmed')
        self.assertEqual(failed['targets'], ['codex'])
        self.schedules.finish_attempt(row['id'], success=True, now=210)
        finished = self.schedules.get(row['id'])
        self.assertEqual((finished['last_run'], finished['next_run']), (210, 260))
        self.assertFalse(finished.get('last_error'))

    def test_recurring_publication_failure_is_safe_and_does_not_starve_peer(self):
        failed, peer = self.due(), self.due('peer')
        def publish(**fields):
            if fields['channel'] == 'review':
                raise OSError('PRIVATE path/source must not persist')
            return {'uid': 'peer-saved'}
        publisher = Mock(side_effect=publish)
        self.tick(publish=publisher)
        self.assertEqual(publisher.call_count, 2)
        row = self.schedules.get(failed['id'])
        self.assertEqual((row['next_run'], row['last_run']), (260, None))
        self.assertEqual(row['last_error'], 'delivery_unconfirmed')
        self.assertNotIn('PRIVATE', self.schedules._path.read_text(encoding='utf-8'))
        self.assertEqual(self.schedules.get(peer['id'])['last_run'], 200)
        publisher.reset_mock()
        self.tick(now=230, publish=publisher)
        publisher.assert_not_called()

    def test_one_shot_failure_stays_inactive_until_explicit_toggle_then_success_deletes(self):
        row = self.due(one_shot=True)
        self.tick(publish=Mock(side_effect=OSError('unconfirmed')))
        failed = self.schedules.get(row['id'])
        self.assertFalse(failed['active'])
        self.assertIsNone(failed['last_run'])
        self.assertEqual(failed['last_error'], 'delivery_unconfirmed')
        publisher = Mock()
        self.tick(now=201, publish=publisher)
        publisher.assert_not_called()
        self.schedules.toggle(row['id'])
        self.tick(now=202, publish=publisher)
        publisher.assert_called_once()
        self.assertIsNone(self.schedules.get(row['id']))

    def test_empty_prompt_or_targets_records_invalid_without_fake_success(self):
        rows = [self.due(prompt=''), self.due(targets=[])]
        publisher = Mock()
        self.tick(publish=publisher)
        publisher.assert_not_called()
        for original in rows:
            row = self.schedules.get(original['id'])
            self.assertEqual(row['last_error'], 'invalid_schedule')
            self.assertEqual((row['next_run'], row['last_run']), (260, None))

    def test_whole_tick_unavailable_or_unbound_policy_changes_no_markers_and_logs_once(self):
        self.due()
        before = self.effects(self.schedules)
        original_getter = self.schedules._channel_policy_getter
        for getter in (None, lambda: (_ for _ in ()).throw(ChannelUnavailable('private unavailable'))):
            with self.subTest(getter=getter):
                # Deliberate unbound/outage algorithm seam, no permissive factory fallback.
                self.schedules._channel_policy_getter = getter
                with patch.object(app, 'log') as log, patch.object(app, '_publish_operator_message') as publish:
                    self.tick(publish=publish)
                    self.tick(publish=publish)
                    publish.assert_not_called()
                    entries = [call for call in log.mock_calls if call[0] in ('warning', 'error', 'exception')]
                    self.assertEqual(len(entries), 1)
                    self.assertNotIn('private unavailable', str(entries))
                self.assertEqual(self.effects(self.schedules), before)
                self.schedules._channel_policy_getter = original_getter
                # Healthy non-due tick resets the continuous-outage latch.
                self.tick(now=100)

    def test_reopen_overdue_fires_once_from_current_time_without_missed_interval_replay(self):
        row = self.due()
        self.catalog.set_state('review', 'archived', expected_revision=0)
        publisher = Mock()
        self.tick(now=1000, publish=publisher)
        self.assertEqual(self.schedules.get(row['id']), row)
        self.catalog.set_state('review', 'active', expected_revision=1)
        self.tick(now=1000, publish=publisher)
        publisher.assert_called_once()
        self.assertEqual(self.schedules.get(row['id'])['next_run'], 1060)
        self.tick(now=1001, publish=publisher)
        publisher.assert_called_once()

    def test_configured_read_copies_fingerprint_and_callbacks_after_durable_unlock(self):
        store = self.configured()
        seen = []
        def callback(action, row):
            seen.append((action, store._lock.locked(), json.loads(store._path.read_text(encoding='utf-8'))))
        store.on_change(callback)
        row = store.create('Retain', ['codex'], channel='peer', interval_seconds=60)
        for result in (store.get(row['id']), store.list_all()[0]):
            result['targets'].append('outside')
        self.assertEqual(store.get(row['id'])['targets'], ['codex'])
        with patch('schedules.json.loads', wraps=json.loads) as loads:
            for _ in range(5):
                store.list_all()
                store.get(row['id'])
            loads.assert_not_called()
        self.assertEqual(seen[0][0:2], ('create', False))
        self.assertEqual(seen[0][2][0]['id'], row['id'])
        old_bytes = store._path.read_bytes()
        store._path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ChannelUnavailable):
            store.list_all()
        self.assertEqual(store._path.read_text(encoding='utf-8'), '{broken')
        self.assertTrue(old_bytes)


if __name__ == '__main__':
    unittest.main()
