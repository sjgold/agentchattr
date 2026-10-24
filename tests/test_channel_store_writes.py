"""Configured direct-store channel guards, without transport/native claims."""
import unittest
import uuid
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import threading
from unittest.mock import patch

import app
from channel_lifecycle import ChannelInactive, ChannelUnavailable
from store import _OPERATOR_PUBLICATION
from tests import test_channel_agent_paths as fixture


class ChannelStoreWriteTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelAgentPathTests.setUp(self)

    def archive(self):
        self.channel_service.catalog.set_state('review', 'archived', expected_revision=0)

    def saved(self):
        message = self.messages.add('codex', 'Exact source\r\nretained', channel='review')
        self.messages.add_todo(message['id'])
        self.messages.bind_channel_policy(app._channels)
        return message

    def evidence(self):
        return (self.messages._path.read_bytes(), self.messages._todos_path.read_bytes(),
                self.messages.get_recent(), self.messages.get_todos(), self.messages._next_id)

    def test_direct_system_message_is_refused_before_file_memory_or_id_changes(self):
        self.messages.bind_channel_policy(app._channels)
        self.archive()
        before = self.messages._path.read_bytes() if self.messages._path.exists() else None
        next_id = self.messages._next_id
        with self.assertRaises(ChannelInactive):
            self.messages.add('system', 'must not save', channel='review')
        self.assertEqual(self.messages._path.read_bytes() if self.messages._path.exists() else None, before)
        self.assertEqual(self.messages.get_recent(), [])
        self.assertEqual(self.messages._next_id, next_id)

    def test_summary_writes_and_deletes_are_refused_with_saved_source_retained(self):
        summary = self.channel_service.summaries
        summary.bind_channel_policy(app._channels)
        saved = summary.write('review', 'retained source', 'operator')
        before = summary._path.read_bytes()
        self.archive()
        for mutation in (lambda: summary.write('review', 'must not save', 'operator'),
                         lambda: summary.delete('review')):
            with self.assertRaises(ChannelInactive):
                mutation()
            self.assertEqual(summary._path.read_bytes(), before)
            self.assertEqual(summary.get('review'), saved)

    def test_edits_and_reply_links_refuse_before_any_saved_change(self):
        message = self.saved()
        self.archive()
        before = self.evidence()
        for mutation in (lambda: self.messages.update_message(message['id'], {'text': 'changed'}),
                         lambda: self.messages.update_reply_to(message['id'], 999)):
            with self.assertRaises(ChannelInactive):
                mutation()
            self.assertEqual(self.evidence(), before)

    def test_delete_and_global_clear_cannot_partially_mutate_active_peer(self):
        message = self.saved()
        peer = self.messages.add('operator', 'peer retained', channel='peer')
        self.archive()
        before = self.evidence()
        for mutation in (lambda: self.messages.delete([peer['id'], message['id']]),
                         lambda: self.messages.clear(), lambda: self.messages.clear('review')):
            with self.assertRaises(ChannelInactive):
                mutation()
            self.assertEqual(self.evidence(), before)
        self.messages.clear('peer')
        self.assertEqual(self.messages.get_recent(channel='review'), [message])

    def test_all_todo_mutations_refuse_without_callbacks_or_disk_changes(self):
        message = self.saved()
        self.archive()
        before, calls = self.evidence(), []
        self.messages.on_todo(lambda *args: calls.append(args))
        for name in ('add_todo', 'complete_todo', 'reopen_todo', 'remove_todo'):
            with self.assertRaises(ChannelInactive):
                getattr(self.messages, name)(message['id'])
            self.assertEqual(self.evidence(), before)
        self.assertEqual(calls, [])

    def test_projection_and_private_publication_cannot_bypass_archived_guard(self):
        self.saved()
        self.archive()
        before = self.evidence()
        routing = dict(origin='operator', mode='none', tokens=[], ignored=[], recipients=[], warnings=[], waiting=[])
        for mutation in (lambda: self.messages.add_once('late-event', 'codex', 'late', channel='review'),
                         lambda: self.messages._publish_operator('operator', 'late', channel='review',
                            authority=_OPERATOR_PUBLICATION, routing=routing)):
            with self.assertRaises(ChannelInactive):
                mutation()
            self.assertEqual(self.evidence(), before)

    def test_edit_moving_active_history_into_archived_channel_is_refused(self):
        self.saved()
        peer = self.messages.add('operator', 'peer', channel='peer')
        self.archive()
        before = self.evidence()
        with self.assertRaises(ChannelInactive):
            self.messages.update_message(peer['id'], {'channel': 'review'})
        self.assertEqual(self.evidence(), before)

    def test_trusted_sender_rename_preserves_archived_history_and_ids(self):
        message = self.saved()
        self.archive()
        next_id = self.messages._next_id
        self.assertEqual(self.messages.rename_sender('codex', 'renamed'), 1)
        saved = self.messages.get_snapshot(message['id'])
        self.assertEqual(saved, {**message, 'sender': 'renamed'})
        self.assertEqual(self.messages._next_id, next_id)

    def test_pending_delete_holds_normal_writes_but_raw_repair_phases_work(self):
        message = self.saved()
        catalog = self.channel_service.catalog
        catalog.begin('delete', 'review', None, request_id=uuid.uuid4().hex, expected_revision=0)
        with self.assertRaises(ChannelInactive):
            self.messages.remove_todo(message['id'])
        self.assertEqual(self.messages.remove_channel_todos('review'), [message['id']])
        self.assertEqual(self.messages.remove_channel_todos('review'), [])
        self.assertEqual(self.messages.remove_channel_messages('review'), [message['id']])
        self.assertEqual(self.messages.remove_channel_messages('review'), [])

    def test_corrupt_catalog_blocks_even_missing_target_without_touching_store(self):
        self.saved()
        before = self.evidence()
        self.channel_service.catalog.path.write_text('invalid', encoding='utf-8')
        for mutation in (lambda: self.messages.delete([999]),
                         lambda: self.messages.update_message(999, {}),
                         lambda: self.messages.add_todo(999)):
            with self.assertRaises(ChannelUnavailable):
                mutation()
            self.assertEqual(self.evidence(), before)

    def test_policy_boundary_precedes_store_lock_and_callback_can_read(self):
        self.messages.bind_channel_policy(app._channels)
        boundary, observed = self.channel_service._boundary, []
        @contextmanager
        def checked():
            self.assertFalse(self.messages._lock.locked())
            with boundary():
                self.assertTrue(self.engine._lock._is_owned())
                yield
        self.messages.on_message(lambda msg: observed.append(self.messages.get_snapshot(msg['id'])))
        with patch.object(self.channel_service, '_boundary', checked):
            saved = self.messages.add('operator', 'peer', channel='peer')
        self.assertEqual(observed, [saved])

    def test_direct_append_holds_archive_until_the_file_write_finishes(self):
        self.messages.bind_channel_policy(app._channels)
        entered, release, attempted = threading.Event(), threading.Event(), threading.Event()
        def gated_sync(_):
            entered.set()
            self.assertTrue(release.wait(3))
        def archive():
            attempted.set()
            with self.channel_service._boundary():
                self.archive()
        with ThreadPoolExecutor(max_workers=2) as pool, patch('store.os.fsync', gated_sync):
            write = pool.submit(self.messages.add, 'operator', 'saved before archive', channel='review')
            try:
                self.assertTrue(entered.wait(3))
                mutation = pool.submit(archive)
                self.assertTrue(attempted.wait(3))
                self.assertFalse(mutation.done())
            finally:
                release.set()
            saved = write.result(timeout=3)
            mutation.result(timeout=3)
        self.assertEqual(self.messages.get_snapshot(saved['id']), saved)
        before = self.messages._path.read_bytes()
        with self.assertRaises(ChannelInactive):
            self.messages.add('operator', 'too late', channel='review')
        self.assertEqual(self.messages._path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
