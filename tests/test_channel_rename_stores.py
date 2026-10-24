"""Low-level rename phase persistence only, without service/native claims."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from jobs import JobStore
from schedules import ScheduleStore
from session_store import SessionStore
from summaries import SummaryStore
from store import _OPERATOR_PUBLICATION
from tests import test_session_events as session_fixture


class ChannelRenameStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.jobs = JobStore(str(self.root / 'jobs.json'))
        self.schedules = ScheduleStore(str(self.root / 'schedules.json'))
        self.summaries = SummaryStore(str(self.root / 'summaries.json'))

    def job_rows(self):
        job = self.jobs.create('Exact source', 'job', 'old', 'operator', status='open')
        routing = {'origin': 'operator', 'mode': 'none', 'tokens': [], 'ignored': [],
                   'recipients': [], 'warnings': [], 'waiting': []}
        self.jobs._publish_operator(job['id'], 'operator', 'Exact café\r\n@all',
            routing=routing, authority=_OPERATOR_PUBLICATION, attachments=[{'name': 'source.py'}])
        self.jobs.add_message(job['id'], 'codex', 'Ordinary message without channel')
        self.jobs.create('Peer retained', 'job', 'peer', 'operator', status='done')
        return deepcopy(self.jobs._jobs)

    def schedule_rows(self):
        with patch('schedules.time.time', return_value=100):
            row = self.schedules.create('Exact prompt', ['codex'], channel='old',
                interval_seconds=60, send_at=101)
            self.schedules.create('Peer retained', ['claude'], channel='peer', interval_seconds=90)
        self.schedules.begin_attempt(row['id'], now=200)
        self.schedules.finish_attempt(row['id'], success=False, error_code='delivery_unconfirmed', now=205)
        return deepcopy(self.schedules._schedules)

    def test_jobs_rename_only_matching_parent_and_embedded_channel_preserving_receipt(self):
        before = self.job_rows()
        expected = deepcopy(before)
        expected[0]['channel'] = 'new'
        expected[0]['messages'][0]['channel'] = 'new'
        observed = Mock()
        self.jobs.on_change(observed)
        self.jobs.rename_channel('old', 'new')
        self.assertEqual(self.jobs._jobs, expected)
        self.assertEqual(JobStore(str(self.jobs._path)).list_all(), expected)
        self.assertEqual(self.jobs._next_id, 3)
        observed.assert_not_called()

    def test_schedules_rename_only_channel_preserving_reserved_attempt_and_cadence(self):
        before = self.schedule_rows()
        expected = deepcopy(before)
        expected[0]['channel'] = 'new'
        observed = Mock()
        self.schedules.on_change(observed)
        self.schedules.rename_channel('old', 'new')
        self.assertEqual(self.schedules._schedules, expected)
        self.assertEqual(ScheduleStore(str(self.schedules._path)).list_all(), expected)
        observed.assert_not_called()

    def session_rows(self):
        # Actual immutable brief/ledger fixtures with manual registry identities, no native proof.
        context = SimpleNamespace(addCleanup=self.addCleanup)
        session_fixture.SessionEventTests.setUp(context)
        old = context.engine.start_session('review', 'old', {'reviewer': 'codex', 'editor': 'claude'},
                                           'operator', input_text='Frozen café\r\nsource')
        context.engine.stop_session(old['id'])
        context.engine.reconcile_stops()
        child = context.sessions.prepare_restart(old['id'], 'Corrected source', 'rename-request')
        self.assertEqual(child['channel'], 'old')
        return context

    def summary_rows(self):
        self.summaries.write('old', 'Exact café\r\nsummary', 'codex', message_id=0,
                             uid='retained-summary', updated_at=123.5)
        self.summaries.write('peer', 'Peer untouched', 'operator', message_id=42,
                             uid='peer-summary', updated_at=456.5)
        return deepcopy(self.summaries._summaries)

    def test_summary_moves_key_only_with_exact_uid_text_author_time_and_backlink(self):
        before = self.summary_rows()
        expected = deepcopy(before)
        expected['new'] = expected.pop('old')
        self.summaries.rename_channel('old', 'new')
        self.assertEqual(self.summaries._summaries, expected)
        self.assertEqual(SummaryStore(str(self.summaries._path)).get_all(), expected)

    def test_sessions_move_all_matching_top_levels_not_frozen_journal_or_brief_queue_bytes(self):
        context = self.session_rows()
        store = context.sessions
        before = deepcopy(store._sessions)
        expected = deepcopy(before)
        for row in expected:
            if row['channel'] == 'old':
                row['channel'] = 'new'
        external = {p.relative_to(context.root).as_posix(): p.read_bytes()
                    for p in context.root.rglob('*') if p.is_file() and p != store._path}
        callback = Mock()
        store.on_change(callback)
        old_next = store._next_id
        store.rename_channel('old', 'new')
        self.assertEqual(store._sessions, expected)
        self.assertEqual(SessionStore(str(store._path)).list_all(), expected)
        self.assertEqual(store._next_id, old_next)
        self.assertEqual({p.relative_to(context.root).as_posix(): p.read_bytes()
            for p in context.root.rglob('*') if p.is_file() and p != store._path}, external)
        callback.assert_not_called()

    def test_job_fresh_reload_retry_is_no_write_and_no_callback(self):
        self.job_rows()
        self.jobs.rename_channel('old', 'new')
        store = JobStore(str(self.jobs._path), migrate_sort_orders=False)
        callback = Mock()
        store.on_change(callback)
        before = store._path.read_bytes(), deepcopy(store._jobs), store._next_id
        with patch('jobs.api_seats.atomic_json', side_effect=AssertionError('retry must not write')):
            store.rename_channel('old', 'new')
        self.assertEqual((store._path.read_bytes(), store._jobs, store._next_id), before)
        callback.assert_not_called()

    def test_schedule_fresh_reload_retry_is_no_write_and_no_callback(self):
        self.schedule_rows()
        self.schedules.rename_channel('old', 'new')
        store = ScheduleStore(str(self.schedules._path))
        callback = Mock()
        store.on_change(callback)
        before = store._path.read_bytes(), deepcopy(store._schedules)
        with patch('schedules.atomic_json', side_effect=AssertionError('retry must not write')):
            store.rename_channel('old', 'new')
        self.assertEqual((store._path.read_bytes(), store._schedules), before)
        callback.assert_not_called()

    def test_summary_fresh_reload_retry_is_no_write(self):
        self.summary_rows()
        self.summaries.rename_channel('old', 'new')
        store = SummaryStore(str(self.summaries._path))
        before = store._path.read_bytes(), deepcopy(store._summaries)
        with patch('summaries.atomic_json', side_effect=AssertionError('retry must not write')):
            store.rename_channel('old', 'new')
        self.assertEqual((store._path.read_bytes(), store._summaries), before)

    def test_session_fresh_reload_retry_is_no_write_and_no_callback(self):
        context = self.session_rows()
        context.sessions.rename_channel('old', 'new')
        store = SessionStore(str(context.sessions._path))
        before = store._path.read_bytes(), deepcopy(store._sessions), store._next_id
        callback = Mock()
        store.on_change(callback)
        with patch('session_store.atomic_json', side_effect=AssertionError('retry must not write')):
            store.rename_channel('old', 'new')
        self.assertEqual((store._path.read_bytes(), store._sessions, store._next_id), before)
        callback.assert_not_called()

    def cases(self):
        self.job_rows()
        self.schedule_rows()
        self.summary_rows()
        context = self.session_rows()
        return [(self.jobs, '_jobs', 'jobs.api_seats.atomic_json'),
                (self.schedules, '_schedules', 'schedules.atomic_json'),
                (self.summaries, '_summaries', 'summaries.atomic_json'),
                (context.sessions, '_sessions', 'session_store.atomic_json')]

    def test_occupied_destination_refuses_all_stores_without_merge_or_any_write(self):
        for store, attribute, alias in self.cases():
            with self.subTest(store=type(store).__name__):
                # Every seeded store already has a distinct occupied peer channel.
                destination = 'general' if isinstance(store, SessionStore) else 'peer'
                before = store._path.read_bytes(), deepcopy(getattr(store, attribute))
                with patch(alias, side_effect=AssertionError('collision must not write')):
                    with self.assertRaises(ValueError):
                        store.rename_channel('old', destination)
                self.assertEqual((store._path.read_bytes(), getattr(store, attribute)), before)

    def test_atomic_rename_fault_keeps_all_store_memory_disk_ids_and_callbacks_exact(self):
        for store, attribute, alias in self.cases():
            with self.subTest(store=type(store).__name__):
                callback = Mock()
                if hasattr(store, 'on_change'):
                    store.on_change(callback)
                before = store._path.read_bytes(), deepcopy(getattr(store, attribute)), getattr(store, '_next_id', None)
                with patch(alias, side_effect=OSError('local rename write failure')) as writer:
                    with self.assertRaises(OSError):
                        store.rename_channel('old', 'new')
                    writer.assert_called_once()
                self.assertEqual((store._path.read_bytes(), getattr(store, attribute), getattr(store, '_next_id', None)), before)
                callback.assert_not_called()

    def test_phase_methods_bypass_policy_getter_and_allow_held_names_but_validate_grammar(self):
        for store, attribute, _ in self.cases():
            with self.subTest(store=type(store).__name__):
                getter = Mock(side_effect=AssertionError('phase must not query active policy'))
                if hasattr(store, 'bind_channel_policy'):
                    store.bind_channel_policy(getter)
                before = store._path.read_bytes(), deepcopy(getattr(store, attribute))
                with self.assertRaises(ValueError):
                    store.rename_channel('old', 'Bad/name')
                self.assertEqual((store._path.read_bytes(), getattr(store, attribute)), before)
                store.rename_channel('old', 'new')
                getter.assert_not_called()

    def test_job_embedded_foreign_scope_and_legacy_session_records_are_preserved(self):
        before = self.job_rows()
        before[0]['messages'][0]['channel'] = 'foreign-scope'
        self.jobs._path.write_text(json.dumps(before, ensure_ascii=False), encoding='utf-8')
        store = JobStore(str(self.jobs._path), migrate_sort_orders=False)
        expected = deepcopy(before)
        expected[0]['channel'] = 'new'
        store.rename_channel('old', 'new')
        self.assertEqual(store._jobs, expected)
        context = self.session_rows()
        # Retained legacy journal boundary: no typed authority or model claim is inferred.
        records = deepcopy(context.sessions._sessions)
        legacy = {'id': 99, 'channel': 'old', 'state': 'ended', 'cast': {'reader': 'manual'},
                  'custom_legacy_metadata': {'channel': 'old', 'literal': '@all'}}
        records.append(legacy)
        context.sessions._path.write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
        restored = SessionStore(str(context.sessions._path))
        before_next = restored._next_id
        restored.rename_channel('old', 'new')
        moved = next(row for row in restored._sessions if row['id'] == 99)
        self.assertEqual(moved, {**legacy, 'channel': 'new'})
        self.assertEqual(restored._next_id, before_next)


if __name__ == '__main__':
    unittest.main()
