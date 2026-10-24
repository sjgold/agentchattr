"""Retained upload metadata only, without message deletion or HTTP claims."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from channel_lifecycle import ChannelUnavailable


class RetainedArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'retained_artifacts.json'

    def store(self):
        self.module = importlib.import_module('retained_artifacts')
        return self.module.RetainedArtifactStore(self.path)

    def message(self, **changes):
        return {'id': 0, 'uid': 'source-message', 'channel': 'review', 'timestamp': 123.5,
                'text': 'MESSAGE BODY MUST NEVER BE RETAINED',
                'attachments': [{'name': 'café source.png', 'url': '/uploads/abcd1234.png',
                                 'path': 'uploads/abcd1234.png'}], **changes}

    def test_retention_preserves_reference_metadata_and_never_message_text(self):
        store = self.store()
        message = self.message()
        store.retain('review', [message])
        expected = {'channel': 'review', 'message_id': 0, 'message_uid': 'source-message',
                    'timestamp': 123.5, 'attachments': message['attachments']}
        self.assertEqual(store.read('review'), {'rows': [expected], 'count': 1, 'truncated': False})
        self.assertNotIn(message['text'].encode(), self.path.read_bytes())
        self.assertEqual(self.store().read('review')['rows'], [expected])

    def test_atomic_probe_failure_leaves_existing_metadata_exact(self):
        store = self.store()
        store.retain('review', [self.message()])
        before = self.path.read_bytes(), store.read('review')
        with patch('retained_artifacts.atomic_json', side_effect=OSError('probe failure')):
            with self.assertRaises(OSError):
                store.probe()
        self.assertEqual((self.path.read_bytes(), store.read('review')), before)

    def test_empty_probe_creates_valid_file_and_reload_is_detached(self):
        store = self.store()
        self.assertFalse(self.path.exists())
        store.probe()
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')), {'version': 1, 'channels': {}})
        self.assertEqual(self.store().channel_names(), set())

    def test_same_identity_merge_is_no_write_and_conflicting_reference_refuses(self):
        store = self.store()
        message = self.message()
        store.retain('review', [message])
        before = self.path.read_bytes()
        with patch('retained_artifacts.atomic_json', side_effect=AssertionError('no-op merge wrote')):
            self.store().retain('review', [deepcopy(message)])
        with self.assertRaises(ValueError):
            store.retain('review', [self.message(attachments=[{'url': '/uploads/different.png'}])])
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_merge_preserves_prior_memory_disk_and_peer_references(self):
        store = self.store()
        store.retain('peer', [self.message(channel='peer')])
        before = self.path.read_bytes(), store.read('peer'), store.read('review')
        with patch('retained_artifacts.atomic_json', side_effect=OSError('write failure')):
            with self.assertRaises(OSError):
                store.retain('review', [self.message()])
        self.assertEqual((self.path.read_bytes(), store.read('peer'), store.read('review')), before)

    def test_wrong_schema_duplicates_bool_and_nonfinite_hold_without_reset(self):
        for raw in (b'{broken', b'\xff', b'[]', b'{"version":true,"channels":{}}',
                    b'{"version":1,"channels":{},"extra":0}',
                    b'{"version":1,"channels":{},"channels":{}}',
                    b'{"version":1,"channels":{"review":[]}}'):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                store = self.store()
                for call in (store.check, store.probe, lambda: store.retain('review', [self.message()])):
                    with self.assertRaises(ChannelUnavailable):
                        call()
                self.assertEqual(self.path.read_bytes(), raw)

    def test_invalid_entry_fields_hold_and_file_is_untouched(self):
        self.store().retain('review', [self.message()])
        good = json.loads(self.path.read_text(encoding='utf-8'))
        for field, value in (('message_id', True), ('message_uid', 4), ('timestamp', float('inf')),
                             ('timestamp', 10**1000),
                             ('attachments', ['wrong']), ('channel', 'peer')):
            with self.subTest(field=field):
                raw = deepcopy(good)
                raw['channels']['review']['source-message'][field] = value
                self.path.write_text(json.dumps(raw), encoding='utf-8')
                before = self.path.read_bytes()
                with self.assertRaises(ChannelUnavailable):
                    self.store().read('review')
                self.assertEqual(self.path.read_bytes(), before)

    def test_unreadable_directory_is_held_without_changing_any_bytes(self):
        self.path.mkdir()
        marker = self.path / 'retained'
        marker.write_bytes(b'kept')
        store = self.store()
        with self.assertRaises(ChannelUnavailable):
            store.check()
        self.assertEqual(marker.read_bytes(), b'kept')

    def test_caps_count_without_truncating_saved_rows_or_aliasing(self):
        store = self.store()
        store.retain('review', [self.message(id=i, uid=f'uid-{i}') for i in range(125)])
        result = store.read('review', limit=100)
        self.assertEqual((len(result['rows']), result['count'], result['truncated']), (100, 125, True))
        result['rows'][0]['attachments'][0]['name'] = 'changed'
        self.assertEqual(store.read('review', limit=200)['rows'][0]['attachments'][0]['name'], 'café source.png')
        for limit in (True, 0, -1, 1001):
            with self.assertRaises(ValueError):
                store.read('review', limit=limit)

    def test_legacy_id_zero_without_uid_uses_stable_reference_without_source_change(self):
        store = self.store()
        message = self.message()
        del message['uid']
        del message['timestamp']
        before = deepcopy(message)
        store.retain('review', [message])
        entry = store.read('review')['rows'][0]
        self.assertEqual((entry['message_uid'], entry['message_id'], entry['timestamp']), ('legacy:0', 0, None))
        self.assertEqual(message, before)
        self.store().retain('review', [message])
        self.assertEqual(store.read('review')['count'], 1)

    def test_safe_upload_links_reject_external_traversal_encoding_and_devices(self):
        self.store()
        safe = self.module.safe_upload_url
        self.assertEqual(safe('/uploads/abcd1234.png'), '/uploads/abcd1234.png')
        for value in ('https://example.com/x', '//example.com/x', '/uploads/../secret',
                      '/uploads/a/b', '/uploads/a\\b', '/uploads/%2e%2e', '/uploads/%252f',
                      '/uploads/file.png?x=1', '/uploads/file.png#x', '/uploads/.hidden',
                      '/uploads/file.', '/uploads/CON.txt', '/uploads/NUL', None, 1):
            with self.subTest(value=value):
                self.assertIsNone(safe(value))

    def test_external_corruption_never_overwrites_or_resets_loaded_memory(self):
        store = self.store()
        store.retain('review', [self.message()])
        self.path.write_bytes(b'corrupt externally')
        with self.assertRaises(ChannelUnavailable):
            store.retain('peer', [self.message(channel='peer')])
        self.assertEqual(self.path.read_bytes(), b'corrupt externally')
