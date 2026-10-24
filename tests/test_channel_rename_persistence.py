"""Summary and cursor durability seams, without runtime migration claims."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mcp_bridge
from channel_lifecycle import ChannelUnavailable
from summaries import SummaryStore


class RenamePersistenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_summary_atomic_write_failure_retains_disk_and_memory(self):
        store = SummaryStore(str(self.root / 'summaries.json'))
        store.write('old', 'retained', 'operator')
        before = store._path.read_bytes(), deepcopy(store._summaries)
        with patch('summaries.atomic_json', create=True, side_effect=OSError('private path')):
            with self.assertRaises(OSError):
                store.write('old', 'replacement', 'operator')
        self.assertEqual((store._path.read_bytes(), store._summaries), before)

    def test_corrupt_summary_binding_holds_reads_without_reset(self):
        path = self.root / 'summaries.json'
        path.write_bytes(b'{broken')
        store = SummaryStore(str(path))
        store.bind_channel_policy(lambda: None)
        for reader in (store.get_all, lambda: store.get('old')):
            with self.assertRaises(ChannelUnavailable):
                reader()
        self.assertEqual(path.read_bytes(), b'{broken')

    def test_cursor_save_snapshots_nested_values_under_lock(self):
        path = self.root / 'cursors.json'
        cursors = {'reader': {'old': 4, 'job:7': 11}}
        serialize = json.dumps
        observed = []
        def inspect(value, *args, **kwargs):
            observed.append((value['reader'] is cursors['reader'], mcp_bridge._cursors_lock.locked()))
            return serialize(value, *args, **kwargs)
        with patch.object(mcp_bridge, '_CURSORS_FILE', path), patch.object(mcp_bridge, '_cursors', cursors):
            with patch.object(mcp_bridge.json, 'dumps', side_effect=inspect):
                mcp_bridge._save_cursors()
        self.assertEqual(observed, [(False, True)])
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), cursors)

    def test_summary_delete_fault_and_detached_nested_reads(self):
        store = SummaryStore(str(self.root / 'summaries.json'))
        store.write('old', 'retained', 'operator')
        before = store._path.read_bytes(), deepcopy(store._summaries)
        with patch('summaries.atomic_json', side_effect=OSError('failure')):
            with self.assertRaises(OSError):
                store.delete('old')
        self.assertEqual((store._path.read_bytes(), store._summaries), before)
        store.get_all()['old']['text'] = 'mutated copy'
        self.assertEqual(store.get('old')['text'], 'retained')

    def test_summary_external_corruption_and_format_only_changes(self):
        store = SummaryStore(str(self.root / 'summaries.json'))
        store.write('old', 'retained', 'operator')
        saved = store.get_all()
        store.bind_channel_policy(lambda: None)
        store._path.write_text(json.dumps(saved), encoding='utf-8')
        self.assertEqual(store.get_all(), saved)
        store._path.write_bytes(b'[]')
        with self.assertRaises(ChannelUnavailable):
            store.rename_channel('old', 'new')
        self.assertEqual(store._path.read_bytes(), b'[]')
        self.assertEqual(store._summaries, saved)

    def test_strict_cursor_move_max_merge_retry_and_owned_path(self):
        path = self.root / 'owned.json'
        before = {'reader': {'old': 9, 'new': 12, 'job:7': 99}, 'peer': {'old': 20, 'peer': 3}}
        path.write_text(json.dumps(before), encoding='utf-8')
        expected = {'reader': {'new': 12, 'job:7': 99}, 'peer': {'new': 20, 'peer': 3}}
        with patch.object(mcp_bridge, '_cursors', deepcopy(before)), patch.object(mcp_bridge, '_CURSORS_FILE', self.root / 'foreign.json'):
            mcp_bridge.migrate_cursors_rename('old', 'new', strict=True, path=path)
            self.assertEqual(mcp_bridge._cursors, expected)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), expected)
            saved = path.read_bytes()
            with patch('mcp_bridge.atomic_json', side_effect=AssertionError('retry must not write')):
                mcp_bridge.migrate_cursors_rename('old', 'new', strict=True, path=path)
            self.assertEqual(path.read_bytes(), saved)
        self.assertFalse((self.root / 'foreign.json').exists())

    def test_strict_cursor_failure_or_corruption_never_commits_memory(self):
        path = self.root / 'owned.json'
        before = {'reader': {'old': 9, 'job:7': 99}}
        path.write_text(json.dumps(before), encoding='utf-8')
        saved = path.read_bytes()
        with patch.object(mcp_bridge, '_cursors', deepcopy(before)):
            with patch('mcp_bridge.atomic_json', side_effect=OSError('private path')):
                with self.assertRaises(OSError):
                    mcp_bridge.migrate_cursors_rename('old', 'new', strict=True, path=path)
            self.assertEqual(path.read_bytes(), saved)
            self.assertEqual(mcp_bridge._cursors, before)
            for raw in (b'[]', b'{"reader":{"old":true}}', b'{"reader":{"old":1,"old":2}}', b'{bad'):
                path.write_bytes(raw)
                with self.assertRaises(ChannelUnavailable):
                    mcp_bridge.migrate_cursors_rename('old', 'new', strict=True, path=path)
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(mcp_bridge._cursors, before)

    def test_volatile_fallback_replay_preserves_peer_and_job_memory(self):
        with patch.object(mcp_bridge, '_last_read_channel', {'reader': 'old', 'peer': 'peer'}), patch.object(mcp_bridge, '_last_read_job_id', {'reader': 7}):
            mcp_bridge.migrate_fallbacks_rename('old', 'new')
            mcp_bridge.migrate_fallbacks_rename('old', 'new')
            self.assertEqual(mcp_bridge._last_read_channel, {'reader': 'new', 'peer': 'peer'})
            self.assertEqual(mcp_bridge._last_read_job_id, {'reader': 7})

    def test_bound_summary_rejects_nonfinite_saved_time_without_rewrite(self):
        path = self.root / 'summaries.json'
        raw = b'{"old":{"text":"retained","author":"operator","message_id":0,"updated_at":1e999}}'
        path.write_bytes(raw)
        store = SummaryStore(str(path))
        store.bind_channel_policy(lambda: None)
        with self.assertRaises(ChannelUnavailable):
            store.get_all()
        self.assertEqual(path.read_bytes(), raw)
