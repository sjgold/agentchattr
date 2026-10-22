"""Accepted-event chat projection must survive a missing session backlink."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from store import MessageStore


class EventProjectionTests(unittest.TestCase):
    def test_uid_projects_once_across_concurrent_calls_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'messages.jsonl'
            messages = MessageStore(str(path))
            def project(_):
                return messages.add_once('session-event:a', 'seat', 'Exact accepted result',
                                         metadata={'event_id': 'a'})
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(project, range(8)))
            self.assertEqual(len({m['id'] for m in results}), 1)
            reloaded = MessageStore(str(path))
            result = reloaded.add_once('session-event:a', 'seat', 'Exact accepted result',
                                       metadata={'event_id': 'a'})
            self.assertEqual(result['id'], results[0]['id'])
            self.assertEqual(len(reloaded.get_recent(50)), 1)
            with self.assertRaises(ValueError):
                reloaded.add_once('session-event:a', 'impostor', 'Changed result')

    def test_failed_projection_keeps_original_disk_and_memory_then_retries_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'messages.jsonl'
            messages = MessageStore(str(path))
            messages.add('user', 'Existing history')
            original = path.read_bytes()
            with patch('store.os.replace', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    messages.add_once('session-event:a', 'seat', 'Accepted but not projected')
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len(messages.get_recent(50)), 1)
            projected = messages.add_once('session-event:a', 'seat', 'Accepted but not projected')
            self.assertEqual(projected['id'], 1)
            self.assertEqual(len(messages.get_recent(50)), 2)
