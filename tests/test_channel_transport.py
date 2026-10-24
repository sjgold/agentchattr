"""Channel queue and persistence units, without configured application claims."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from dispatch_queue import QueueStore, QueueConflict
from channel_lifecycle import ChannelStore, ChannelUnavailable
from store import MessageStore


class ChannelTransportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.queue = QueueStore(self.root)
        self.owner = {'name': 'seat', 'identity_id': uuid.uuid4().hex}
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))

    def enqueue(self, channel):
        return self.queue.enqueue(self.owner, {'channel': channel, 'text': 'exact input'})

    def test_blocked_queued_channel_never_claims_and_peer_channel_progresses(self):
        held = self.enqueue('archived')
        peer = self.enqueue('active')
        claimed = self.queue.claim(self.owner, 'worker', blocked_channel_names={'archived'})
        self.assertEqual(claimed['envelope']['dispatch_id'], peer['envelope']['dispatch_id'])
        self.assertEqual(self.queue.for_identity(self.owner)[0], held)
        self.queue.release(self.owner, peer['envelope']['dispatch_id'], 'worker')
        before = self.queue.path.read_bytes()
        self.assertIsNone(self.queue.claim(self.owner, 'worker', blocked_channel_names={'archived'}))
        self.assertEqual(self.queue.path.read_bytes(), before)

    def test_active_catalog_filter_holds_unknown_without_a_ledger_prepass(self):
        unknown = self.enqueue('unregistered')
        peer = self.enqueue('peer')
        claimed = self.queue.claim(self.owner, 'worker', active_channel_names={'peer'})
        self.assertEqual(claimed['envelope']['dispatch_id'], peer['envelope']['dispatch_id'])
        self.assertEqual(self.queue.for_identity(self.owner)[0], unknown)
        before = self.queue.path.read_bytes()
        for invalid in ('peer', [], frozenset(), {'Bad'}, {True}):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                self.queue.claim(self.owner, 'worker', active_channel_names=invalid)
            self.assertEqual(self.queue.path.read_bytes(), before)
        self.assertEqual(self.queue.claim(self.owner, 'worker', active_channel_names=set())['state'], 'dispatched')

    def test_failed_channel_rewrite_keeps_exact_disk_and_memory(self):
        self.messages.add('operator', 'Exact café\r\nsource', channel='old')
        self.messages.add('operator', 'peer', channel='peer')
        before = self.messages._path.read_bytes()
        memory = deepcopy(self.messages.get_recent())
        with patch('store.os.fsync', side_effect=OSError('injected sync failure')):
            with self.assertRaises(OSError):
                self.messages.rename_channel('old', 'new')
        self.assertEqual(self.messages._path.read_bytes(), before)
        self.assertEqual(self.messages.get_recent(), memory)
        self.assertEqual(MessageStore(str(self.messages._path)).get_recent(), memory)

    def test_cancel_queued_is_exact_scoped_and_never_moves_active_work(self):
        active = self.enqueue('busy')
        self.queue.claim(self.owner, 'worker')
        held = self.enqueue('archived')
        peer = self.enqueue('peer')
        before = self.queue.path.read_bytes()
        with self.assertRaises(QueueConflict):
            self.queue.cancel_queued_channel('busy', [active['envelope']['dispatch_id']], 'cancel-one')
        self.assertEqual(self.queue.path.read_bytes(), before)
        with self.assertRaises(QueueConflict):
            self.queue.cancel_queued_channel('archived', [], 'cancel-two')
        self.assertEqual(self.queue.path.read_bytes(), before)
        records = self.queue.cancel_queued_channel('archived', [held['envelope']['dispatch_id']], 'cancel-three')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['state'], 'cancelled')
        current = self.queue.for_identity(self.owner)
        self.assertEqual(current[0]['state'], 'dispatched')
        self.assertEqual(current[2], peer)
        records[0]['state'] = 'caller mutation'
        self.assertEqual(self.queue.for_identity(self.owner)[1]['state'], 'cancelled')

    def test_existing_owner_poll_and_cancel_delivery_precede_channel_hold(self):
        first = self.enqueue('archived')
        dispatch = first['envelope']['dispatch_id']
        self.queue.claim(self.owner, 'worker')
        self.assertEqual(self.queue.claim(self.owner, 'worker', blocked_channel_names={'archived'})['state'], 'dispatched')
        self.queue.cancel_dispatch(dispatch, 'existing-stop')
        self.assertEqual(self.queue.claim(self.owner, 'worker', blocked_channel_names={'archived'})['state'], 'cancelling')

    def test_replace_failure_preserves_original_and_success_preserves_message_identity(self):
        saved = self.messages.add('operator', 'Exact café\r\nsource', channel='old',
                                  attachments=[{'url': '/uploads/retained.png'}])
        before = self.messages._path.read_bytes()
        with patch('store.os.replace', side_effect=OSError('injected replace failure')):
            with self.assertRaises(OSError):
                self.messages.rename_channel('old', 'new')
        self.assertEqual(self.messages._path.read_bytes(), before)
        self.assertEqual(self.messages.get_snapshot(saved['id']), saved)
        self.assertEqual(list(self.root.glob('messages.jsonl.*.tmp')), [])
        self.messages.rename_channel('old', 'new')
        self.assertEqual(self.messages.get_snapshot(saved['id']), {**saved, 'channel': 'new'})
        after = self.messages._path.read_bytes()
        self.messages.rename_channel('old', 'new')
        self.assertEqual(self.messages._path.read_bytes(), after)

    def test_delete_phases_are_atomic_scoped_and_do_not_notify_or_remove_uploads(self):
        target = self.messages.add('operator', 'remove', channel='old', attachments=[{'url': '/uploads/keep.txt'}])
        peer = self.messages.add('operator', 'keep', channel='peer', reply_to=target['id'])
        self.messages.add_todo(target['id'])
        self.messages.add_todo(peer['id'])
        notifications = []
        self.messages.on_delete(notifications.append)
        self.messages.upload_dir = self.root / 'uploads'
        self.messages.upload_dir.mkdir()
        upload = self.messages.upload_dir / 'keep.txt'
        upload.write_text('retained', encoding='utf-8')
        before = self.messages._todos_path.read_bytes()
        with patch('store.atomic_json', side_effect=OSError('todo write failed'), create=True):
            with self.assertRaises(OSError):
                self.messages.remove_channel_todos('old')
        self.assertEqual(self.messages._todos_path.read_bytes(), before)
        self.assertEqual(self.messages.get_todos(), {target['id']: 'todo', peer['id']: 'todo'})
        self.messages.remove_channel_todos('old')
        after = self.messages._todos_path.read_bytes()
        self.messages.remove_channel_todos('old')
        self.assertEqual(self.messages._todos_path.read_bytes(), after)
        before = self.messages._path.read_bytes()
        with patch('store.os.replace', side_effect=OSError('message replacement failed')):
            with self.assertRaises(OSError):
                self.messages.remove_channel_messages('old')
        self.assertEqual(self.messages._path.read_bytes(), before)
        self.assertIsNotNone(self.messages.get_snapshot(target['id']))
        removed = self.messages.remove_channel_messages('old')
        self.assertEqual(removed, [target['id']])
        self.assertEqual(self.messages.get_todos(), {peer['id']: 'todo'})
        self.assertEqual(self.messages.get_snapshot(peer['id']), peer)
        self.assertTrue(upload.exists())
        self.assertEqual(notifications, [])
        self.messages.notify_deleted(removed)
        self.assertEqual(notifications, [[target['id']]])

    def test_delete_crash_seams_reload_and_replay_without_other_todo_changes(self):
        target = self.messages.add('operator', 'remove', channel='old')
        peer = self.messages.add('operator', 'keep', channel='peer')
        self.messages.add_todo(target['id'])
        self.messages.add_todo(peer['id'])
        catalog = ChannelStore(self.root / 'channels.json')
        catalog.initialize(['old', 'peer'])
        request = uuid.uuid4().hex
        catalog.begin('delete', 'old', None, request_id=request, expected_revision=0)
        self.messages.remove_channel_todos('old')
        with patch('channel_lifecycle.atomic_json', side_effect=OSError('lost step mark')):
            with self.assertRaises(ChannelUnavailable):
                catalog.complete_step(request, 'todos')
        catalog = ChannelStore(catalog.path)
        messages = MessageStore(str(self.messages._path))
        self.assertIn('old', catalog.blocked_names())
        self.assertEqual(catalog.snapshot()['intent']['completed_steps'], [])
        messages.remove_channel_todos('old')
        catalog.complete_step(request, 'todos')
        messages.remove_channel_messages('old')
        with patch('channel_lifecycle.atomic_json', side_effect=OSError('lost second step mark')):
            with self.assertRaises(ChannelUnavailable):
                catalog.complete_step(request, 'messages')
        catalog = ChannelStore(catalog.path)
        messages = MessageStore(str(messages._path))
        before = messages._path.read_bytes()
        self.assertEqual(messages.remove_channel_messages('old'), [])
        self.assertEqual(messages._path.read_bytes(), before)
        catalog.complete_step(request, 'messages')
        catalog.complete_step(request, 'settings')
        self.assertEqual(catalog.finish(request)['channels']['old'], 'retired')
        self.assertEqual(messages.get_todos(), {peer['id']: 'todo'})


if __name__ == '__main__':
    unittest.main()
