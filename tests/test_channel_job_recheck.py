"""Job review regressions, with real local stores and public handler seams."""
import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import app
import jobs as jobs_module
from jobs import JobStore
from channel_lifecycle import ChannelUnavailable
from dispatch_queue import QueueConflict
from tests import test_channel_job_routes as fixture
from tests import test_channel_message_mutations as history_fixture


class ChannelJobRecheckTests(unittest.TestCase):
    request = fixture.ChannelJobRouteTests.request

    def setUp(self):
        fixture.ChannelJobRouteTests.setUp(self)

    def test_unchanged_reads_do_not_reparse_and_changed_corruption_fails_closed(self):
        job = self.jobs.create('Saved', 'job', 'peer', 'operator')
        with patch.object(self.jobs, '_read_jobs', wraps=self.jobs._read_jobs) as reader:
            for _ in range(4):
                self.jobs.get(job['id'])
                self.jobs.get_messages(job['id'])
                self.jobs.list_all(channel='peer')
            self.assertEqual(reader.call_count, 0)
            self.jobs._path.write_text('{broken jobs', encoding='utf-8')
            for read in (lambda: self.jobs.get(job['id']), self.jobs.list_all):
                with self.assertRaises(ChannelUnavailable):
                    read()
            self.assertEqual(reader.call_count, 1, 'The same failed fingerprint must not be parsed repeatedly.')
        self.assertEqual(self.jobs._path.read_text(encoding='utf-8'), '{broken jobs')

    def test_filtered_read_copies_no_peer_conversations_and_keeps_virtual_orders(self):
        peer = self.jobs.create('Peer', 'job', 'peer', 'operator')
        selected = self.jobs.create('Selected', 'job', 'review', 'operator')
        def copy_selected(value):
            if type(value) is list:
                self.assertFalse(any(type(row) is dict and row.get('id') == peer['id']
                                     and row.get('title') == 'Peer' for row in value))
            return deepcopy(value)
        with patch.object(jobs_module, 'deepcopy', side_effect=copy_selected):
            rows = self.jobs.list_all(channel='review')
        self.assertEqual([row['id'] for row in rows], [selected['id']])

    def test_manage_scope_uses_metadata_without_copying_conversation_bodies(self):
        job = self.jobs.create('Saved', 'job', 'peer', 'operator')
        self.jobs.add_message(job['id'], 'operator', 'Private conversation')
        with patch.object(jobs_module, 'deepcopy', side_effect=AssertionError('No conversation copy in lifecycle scope')):
            scope = self.jobs.lifecycle_scope('peer')
            view = self.service.catalog_view()
        self.assertEqual(scope, [{'id': job['id'], 'updated_at': self.jobs.get(job['id'])['updated_at']}])
        self.assertEqual(next(row for row in view['channels'] if row['name'] == 'peer')['counts']['jobs'], 1)

    def test_explicit_startup_hold_keeps_every_job_operation_closed_without_reset(self):
        self.jobs._path.write_text('{unreadable startup', encoding='utf-8')
        held = JobStore(str(self.jobs._path), migrate_sort_orders=False, hold_unreadable=True)
        held.bind_channel_policy(lambda: self.service)
        self.assertTrue(held.load_error)
        for action in (held.list_all, lambda: held.get(1), lambda: held.get_messages(1),
                       lambda: held.create('Never', 'job', 'peer', 'operator')):
            with self.assertRaises(ChannelUnavailable):
                action()
        self.assertEqual(held._path.read_text(encoding='utf-8'), '{unreadable startup')

    def test_failed_accept_trigger_explains_saved_resolution_without_exception_echo(self):
        job = self.jobs.create('Saved', 'job', 'peer', 'operator')
        self.jobs.add_message(job['id'], self.peer['name'], 'Suggestion', msg_type='suggestion')
        with patch.object(self.trigger, 'trigger_sync', side_effect=QueueConflict('PRIVATE DETAILS')):
            response = asyncio.run(app.resolve_job_message(job['id'], 0, self.request({'resolution': 'accepted'})))
        self.assertEqual(response.status_code, 409)
        message = json.loads(response.body)['error']
        self.assertIn('saved', message.lower())
        self.assertIn('check', message.lower())
        self.assertNotIn('PRIVATE', message)
        self.assertEqual(self.jobs.get_messages(job['id'])[0]['resolved'], 'accepted')
        self.assertEqual(self.trigger.queue.records(), [])

    def test_read_failure_guidance_is_about_reading_jobs_not_changing_history(self):
        self.jobs.create('Saved', 'job', 'peer', 'operator')
        self.jobs._path.write_text('{broken jobs', encoding='utf-8')
        for call in (lambda: app.get_jobs(), lambda: app.get_job_messages(1)):
            response = asyncio.run(call())
            self.assertEqual(response.status_code, 503)
            message = json.loads(response.body)['error'].lower()
            self.assertIn('jobs', message)
            self.assertNotIn('change', message)

    def test_closed_jobs_bootstrap_reports_error_and_socket_still_accepts_chat(self):
        self.jobs._path.write_text('{unreadable startup', encoding='utf-8')
        held = JobStore(str(self.jobs._path), migrate_sort_orders=False, hold_unreadable=True)
        held.bind_channel_policy(lambda: self.service)
        with patch.object(app, 'jobs', held):
            frames = history_fixture.ChannelMessageMutationTests.socket(self, [
                {'type': 'message', 'channel': 'peer', 'text': 'Chat remains available', 'selected_recipients': []}])
        unavailable = next(frame for frame in frames if frame['type'] == 'jobs')
        self.assertIn('error', unavailable)
        self.assertNotIn('data', unavailable)
        self.assertTrue(any(frame['type'] == 'history_complete' for frame in frames))
        self.assertTrue(any(frame['type'] == 'message_accepted' for frame in frames))
        self.assertEqual(self.messages.get_recent(5, channel='peer')[-1]['text'], 'Chat remains available')
        self.assertEqual(held._path.read_text(encoding='utf-8'), '{unreadable startup')

    def test_external_content_change_is_not_served_stale_or_overwritten(self):
        job = self.jobs.create('Saved', 'job', 'peer', 'operator')
        original = json.loads(self.jobs._path.read_text(encoding='utf-8'))
        # Formatting-only edits revalidate to the same authoritative records.
        self.jobs._path.write_text(json.dumps(original, indent=7), encoding='utf-8')
        self.assertEqual(self.jobs.get(job['id'])['title'], 'Saved')
        changed = deepcopy(original)
        changed[0]['title'] = 'External edit'
        self.jobs._path.write_text(json.dumps(changed), encoding='utf-8')
        before = self.jobs._path.read_bytes()
        for action in (self.jobs.list_all, lambda: self.jobs.update_title(job['id'], 'Overwrite')):
            with self.assertRaises(ChannelUnavailable):
                action()
        self.assertEqual(self.jobs._path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
