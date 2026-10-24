"""Job persistence and opt-in catalog units; no app, workers or HTTP claims."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from channel_lifecycle import ChannelConflict, ChannelInactive, ChannelUnavailable
from jobs import JobStore
from store import _OPERATOR_PUBLICATION
from tests import test_channel_import as fixture


class ChannelJobTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'jobs.json'

    def configured(self, *, bind=True):
        # Explicit real service construction through a module fixture, never app startup.
        context = SimpleNamespace(addCleanup=self.addCleanup)
        fixture.ChannelImportTests.setUp(context)
        jobs = JobStore(str(self.path), migrate_sort_orders=False)
        context.service.jobs = jobs
        if bind:
            jobs.bind_channel_policy(lambda: context.service)
        return jobs, context

    def snapshot(self, jobs):
        return (self.path.read_bytes() if self.path.exists() else None,
                deepcopy(jobs._jobs), jobs._next_id)

    def seed(self, jobs, channel='review', title='Original', status='open'):
        return jobs.create(title, 'job', channel, 'operator', status=status)

    def routing(self):
        return {'origin': 'operator', 'mode': 'none', 'tokens': [], 'ignored': [],
                'recipients': [], 'warnings': [], 'waiting': []}

    def test_atomic_update_failure_preserves_exact_disk_memory_ids_and_callbacks(self):
        jobs = JobStore(str(self.path))
        job = jobs.create('Original', 'job', 'review', 'operator')
        before = self.path.read_bytes(), deepcopy(jobs._jobs), jobs._next_id
        callback = Mock()
        jobs.on_change(callback)
        with patch('jobs.api_seats.atomic_json', side_effect=OSError('local write failure')) as writer:
            with self.assertRaises(OSError):
                jobs.update_title(job['id'], 'Must not persist')
            writer.assert_called_once()
        self.assertEqual((self.path.read_bytes(), jobs._jobs, jobs._next_id), before)
        callback.assert_not_called()

    def test_configured_legacy_missing_sort_is_virtual_deterministic_and_readonly(self):
        raw = [{'id': 1, 'uid': 'archived', 'title': 'Retained', 'type': 'job',
                'status': 'open', 'channel': 'review', 'messages': []},
               {'id': 2, 'uid': 'peer', 'title': 'Peer', 'type': 'job',
                'status': 'open', 'channel': 'peer', 'messages': []}]
        self.path.write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')
        before = self.path.read_bytes()
        with patch('jobs.api_seats.atomic_json') as writer:
            jobs = JobStore(str(self.path), migrate_sort_orders=False)
            first, second = jobs.list_all(), jobs.list_all()
            writer.assert_not_called()
        self.assertEqual(first, second)
        self.assertEqual([job['sort_order'] for job in first], [1, 2])
        self.assertEqual(jobs._jobs, raw)
        self.assertEqual(self.path.read_bytes(), before)

    def test_configured_bad_json_schema_and_read_io_fail_closed_without_reset(self):
        for content in ('{broken', '{}', '[null]', '[{"id":true,"messages":[]}]'):
            with self.subTest(content=content):
                self.path.write_text(content, encoding='utf-8')
                before = self.path.read_bytes()
                with self.assertRaises(ChannelUnavailable):
                    JobStore(str(self.path), migrate_sort_orders=False)
                self.assertEqual(self.path.read_bytes(), before)
        self.path.write_text('[]', encoding='utf-8')
        original_read = Path.read_text
        def unreadable(path, *args, **kwargs):
            if path == self.path:
                raise PermissionError('local read denied')
            return original_read(path, *args, **kwargs)
        with patch.object(Path, 'read_text', unreadable):
            with self.assertRaises(ChannelUnavailable):
                JobStore(str(self.path), migrate_sort_orders=False)
        self.assertEqual(self.path.read_text(encoding='utf-8'), '[]')

    def test_configured_writes_are_closed_until_explicit_policy_binding(self):
        jobs, context = self.configured(bind=False)
        before = self.snapshot(jobs)
        with self.assertRaises(ChannelUnavailable):
            self.seed(jobs)
        self.assertEqual(self.snapshot(jobs), before)
        self.assertEqual(jobs.list_all(), [])
        jobs.bind_channel_policy(lambda: context.service)
        self.assertEqual(self.seed(jobs)['id'], 1)

    def test_archived_actual_job_channel_guards_every_mutator_before_effects(self):
        jobs, context = self.configured()
        job = self.seed(jobs)
        message = jobs.add_message(job['id'], 'codex', 'Suggestion', msg_type='suggestion')
        context.catalog.set_state('review', 'archived', expected_revision=0)
        callback = Mock()
        jobs.on_change(callback)
        calls = [lambda: self.seed(jobs), lambda: jobs.update_status(job['id'], 'done'),
            lambda: jobs.update_title(job['id'], 'Changed'),
            lambda: jobs.update_assignee(job['id'], 'peer'),
            lambda: jobs.add_message(job['id'], 'operator', 'Changed'),
            lambda: jobs._publish_operator(job['id'], 'operator', 'Raw',
                routing=self.routing(), authority=_OPERATOR_PUBLICATION),
            lambda: jobs.delete_message(job['id'], message['id']),
            lambda: jobs.resolve_message(job['id'], 0, 'accepted'),
            lambda: jobs.delete(job['id']), lambda: jobs.reorder('open', [job['id']])]
        for index, call in enumerate(calls):
            with self.subTest(operation=index):
                before = self.snapshot(jobs)
                with self.assertRaises(ChannelInactive):
                    call()
                self.assertEqual(self.snapshot(jobs), before)
        callback.assert_not_called()

    def test_peer_mutations_and_locked_suggestion_resolution_remain_functional(self):
        jobs, context = self.configured()
        archived = self.seed(jobs)
        context.catalog.set_state('review', 'archived', expected_revision=0)
        job = self.seed(jobs, 'peer')
        self.assertEqual(jobs.update_title(job['id'], 'Peer title')['title'], 'Peer title')
        self.assertEqual(jobs.update_assignee(job['id'], 'codex')['assignee'], 'codex')
        self.assertEqual(jobs.update_status(job['id'], 'done')['status'], 'done')
        message = jobs.add_message(job['id'], 'codex', 'Suggestion', msg_type='suggestion')
        resolved = jobs.resolve_message(job['id'], 0, 'accepted')
        self.assertIsNotNone(resolved)
        self.assertEqual(jobs.get_messages(job['id'])[0]['resolved'], 'accepted')
        self.assertIsNotNone(jobs.delete_message(job['id'], message['id']))
        self.assertIsNotNone(jobs.delete(job['id']))
        self.assertEqual(jobs.get(archived['id']), archived)

    def test_active_only_reorder_preserves_unrequested_inactive_and_other_groups(self):
        jobs, context = self.configured()
        first = self.seed(jobs, 'peer', 'First')
        inactive = self.seed(jobs, 'review', 'Retained')
        last = self.seed(jobs, 'peer', 'Last')
        other = self.seed(jobs, 'peer', 'Other lane', status='done')
        context.catalog.set_state('review', 'archived', expected_revision=0)
        retained = deepcopy(next(row for row in jobs._jobs if row['id'] == inactive['id']))
        other_before = deepcopy(next(row for row in jobs._jobs if row['id'] == other['id']))
        jobs.reorder('open', [first['id']])
        rows = {row['id']: row for row in jobs._jobs}
        self.assertGreater(rows[first['id']]['sort_order'], rows[last['id']]['sort_order'])
        self.assertEqual(rows[inactive['id']], retained)
        self.assertEqual(rows[other['id']], other_before)

    def test_requested_inactive_or_unknown_reorder_refuses_whole_group(self):
        jobs, context = self.configured()
        active = self.seed(jobs, 'peer')
        inactive = self.seed(jobs)
        context.catalog.set_state('review', 'archived', expected_revision=0)
        for ids in ([active['id'], inactive['id']], [active['id'], 999]):
            with self.subTest(ids=ids):
                before = self.snapshot(jobs)
                with self.assertRaises((ChannelInactive, ChannelConflict)):
                    jobs.reorder('open', ids)
                self.assertEqual(self.snapshot(jobs), before)

    def test_atomic_failure_rolls_back_each_mutator_and_private_publication(self):
        jobs, _ = self.configured()
        job = self.seed(jobs)
        peer = self.seed(jobs, 'peer')
        message = jobs.add_message(job['id'], 'codex', 'Suggestion', msg_type='suggestion')
        callback = Mock()
        jobs.on_change(callback)
        calls = [lambda: self.seed(jobs, title='Never allocated'),
            lambda: jobs.update_status(job['id'], 'done'),
            lambda: jobs.update_title(job['id'], 'Never written'),
            lambda: jobs.update_assignee(job['id'], 'Never assigned'),
            lambda: jobs.add_message(job['id'], 'operator', 'Never appended'),
            lambda: jobs._publish_operator(job['id'], 'operator', 'Exact\r\nraw',
                routing=self.routing(), authority=_OPERATOR_PUBLICATION),
            lambda: jobs.delete_message(job['id'], message['id']),
            lambda: jobs.resolve_message(job['id'], 0, 'accepted'),
            lambda: jobs.delete(job['id']), lambda: jobs.reorder('open', [job['id'], peer['id']])]
        for index, call in enumerate(calls):
            with self.subTest(operation=index):
                before = self.snapshot(jobs)
                with patch('jobs.api_seats.atomic_json', side_effect=OSError('local write failure')) as writer:
                    with self.assertRaises(OSError):
                        call()
                    writer.assert_called_once()
                self.assertEqual(self.snapshot(jobs), before)
        callback.assert_not_called()

    def test_reads_are_detached_and_virtual_sort_never_leaks_into_archived_raw_rows(self):
        raw = [{'id': 1, 'uid': 'old', 'channel': 'review', 'status': 'open',
                'messages': [{'id': 0, 'uid': 'msg', 'text': 'Keep', 'attachments': [{'name': 'safe'}]}]},
               {'id': 2, 'uid': 'active', 'channel': 'peer', 'status': 'open', 'sort_order': 'bad', 'messages': []}]
        self.path.write_text(json.dumps(raw), encoding='utf-8')
        jobs, context = self.configured()
        context.catalog.set_state('review', 'archived', expected_revision=0)
        outputs = [jobs.list_all()[0], jobs.get(1)]
        for output in outputs:
            output['messages'][0]['attachments'][0]['name'] = 'Changed outside'
        messages = jobs.get_messages(1)
        messages[0]['text'] = 'Changed outside'
        snapshot = jobs.get_message_snapshot(1, 0)
        snapshot['attachments'].append({'name': 'Changed outside'})
        self.assertEqual(jobs._jobs, raw)
        jobs.update_title(2, 'Active edit')
        persisted = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(persisted[0], raw[0])
        self.assertNotIn('sort_order', persisted[0])

    def test_corrupt_catalog_refuses_writes_but_retained_job_reads_and_emit_stay_available(self):
        jobs, context = self.configured()
        job = self.seed(jobs)
        saved = jobs._publish_operator(job['id'], 'operator', 'Exact\r\nraw',
            routing=self.routing(), authority=_OPERATOR_PUBLICATION)
        context.catalog.path.write_text('{broken', encoding='utf-8')
        before = self.snapshot(jobs)
        with self.assertRaises(ChannelUnavailable):
            jobs.update_title(job['id'], 'Must not persist')
        self.assertEqual(self.snapshot(jobs), before)
        self.assertEqual(jobs.get_message_snapshot(job['id'], saved['id']), saved)
        callback = Mock()
        jobs.on_change(callback)
        jobs._emit_operator(saved, authority=_OPERATOR_PUBLICATION)
        callback.assert_called_once()

    def test_callbacks_follow_durable_commit_and_released_store_lock(self):
        jobs, _ = self.configured()
        observations = []
        def changed(action, value):
            self.assertFalse(jobs._lock.locked())
            observations.append((action, json.loads(self.path.read_text(encoding='utf-8'))))
        jobs.on_change(changed)
        job = self.seed(jobs)
        jobs.update_title(job['id'], 'Saved before callback')
        self.assertEqual([action for action, _ in observations], ['create', 'update'])
        self.assertEqual(observations[-1][1][0]['title'], 'Saved before callback')


if __name__ == '__main__':
    unittest.main()
