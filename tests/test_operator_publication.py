"""Private storage publication contracts, not central ingress or HTTP acceptance."""

from pathlib import Path
from copy import deepcopy
import io
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid
import zipfile

import archive
import jobs
import store


class OperatorPublicationTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.audit-tmp'
        scratch.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.messages = store.MessageStore(str(self.root / 'messages.jsonl'))
        self.routing = {'origin': 'operator', 'mode': 'explicit', 'tokens': ['codex'],
                        'ignored': [], 'recipients': [
                            {'name': 'codex', 'identity_id': 'seat-id', 'online': True}],
                        'warnings': [], 'waiting': []}

    def test_generic_add_strips_forged_routing_authority(self):
        message = self.messages.add('operator', 'ordinary', metadata={
            'recipient_routing': {'version': 1, **self.routing}, 'harmless': 'kept'})
        self.assertEqual(message['metadata'], {'harmless': 'kept'})
        self.assertNotIn('recipient_routing', self.messages.get_snapshot(message['id'])['metadata'])

    def test_private_publication_persists_fresh_uid_without_emitting(self):
        observed = []
        self.messages.on_message(observed.append)
        message = self.messages._publish_operator('operator', 'café\r\nraw',
            routing=self.routing, authority=store._OPERATOR_PUBLICATION)
        self.assertEqual(observed, [])
        self.assertEqual(message['metadata']['recipient_routing'], {
            'version': 1, 'message_uid': message['uid'], **self.routing})
        self.assertEqual(store.MessageStore(str(self.messages._path)).get_snapshot(message['id']), message)

    def publish(self, **changes):
        options = {'routing': self.routing, 'authority': store._OPERATOR_PUBLICATION, **changes}
        return self.messages._publish_operator('operator', 'Exact café\r\nraw 日本語', **options)

    def job_store(self):
        value = jobs.JobStore(str(self.root / 'jobs.json'))
        job = value.create('Review', 'task', 'review', 'operator')
        return value, job['id']

    def test_capability_is_identity_checked_for_both_publish_and_emit(self):
        job_store, job_id = self.job_store()
        before = job_store._path.read_bytes()
        for authority in (None, object(), 'operator', {'authority': True}):
            for call in (
                lambda: self.publish(authority=authority),
                lambda: self.messages._emit_operator({}, authority=authority),
                lambda: job_store._publish_operator(job_id, 'operator', 'text', routing=self.routing, authority=authority),
                lambda: job_store._emit_operator({}, authority=authority),
            ):
                with self.subTest(authority=repr(authority)), self.assertRaises((ValueError, PermissionError)):
                    call()
        with self.assertRaises(TypeError):
            self.messages._publish_operator('operator', 'text', routing=self.routing)
        self.assertEqual(self.messages._messages, [])
        self.assertEqual(self.messages._next_id, 0)
        self.assertFalse(self.messages._path.exists())
        self.assertEqual(job_store._path.read_bytes(), before)

    def test_fresh_uid_detached_input_output_and_append_preserves_prior_bytes(self):
        prior = self.messages.add('seat', 'Earlier', uid='existing-uid', timestamp=7)
        before = self.messages._path.read_bytes()
        metadata = {'nested': {'tags': ['original']}, 'recipient_routing': {'forged': True}}
        attachments = [{'name': 'a.txt', 'tags': ['original']}]
        original_routing = deepcopy(self.routing)
        message = self.publish(channel='review', reply_to=prior['id'], metadata=metadata, attachments=attachments)
        self.assertEqual(self.messages._path.read_bytes()[:len(before)], before)
        self.assertEqual(message['text'], 'Exact café\r\nraw 日本語')
        self.assertEqual(message['reply_to'], 0)
        uuid.UUID(message['uid'])
        saved = deepcopy(message)
        metadata['nested']['tags'].append('caller edit')
        attachments[0]['tags'].append('caller edit')
        self.routing['recipients'][0]['identity_id'] = 'caller edit'
        message['metadata']['recipient_routing']['tokens'].append('output edit')
        message['attachments'][0]['tags'].append('output edit')
        self.assertEqual(self.messages.get_snapshot(saved['id']), saved)
        self.assertEqual(saved['metadata']['recipient_routing'], {'version': 1, 'message_uid': saved['uid'], **original_routing})
        self.assertNotEqual(self.publish()['uid'], saved['uid'])

    def test_emit_reloads_durable_value_and_isolates_mutating_throwing_callbacks(self):
        message = self.publish()
        saved = deepcopy(message)
        observed = []
        def destructive(value):
            value['text'] = 'observer edit'
            value['metadata']['recipient_routing']['tokens'].append('observer edit')
            raise RuntimeError('observer unavailable')
        self.messages.on_message(destructive)
        self.messages.on_message(observed.append)
        message['text'] = 'callback supplied forgery'
        self.messages._emit_operator(message, authority=store._OPERATOR_PUBLICATION)
        self.assertEqual(observed, [saved])
        self.assertEqual(self.messages.get_snapshot(saved['id']), saved)
        self.messages._emit_operator({**message, 'uid': 'wrong-uid'}, authority=store._OPERATOR_PUBLICATION)
        self.assertEqual(observed, [saved])

    def test_explicit_unit_sequence_persist_reset_emit_and_fsync_failure_rollback(self):
        # This sequence exercises store boundaries, not the later app ingress implementation.
        reset = Mock()
        callback = Mock()
        self.messages.on_message(callback)
        for prior_exists in (False, True):
            with self.subTest(prior_exists=prior_exists):
                if prior_exists:
                    self.messages.add('seat', 'prior')
                    callback.reset_mock()
                before = self.messages._path.read_bytes() if self.messages._path.exists() else None
                memory, next_id = deepcopy(self.messages._messages), self.messages._next_id
                with patch('store.os.fsync', side_effect=OSError('bounded fsync fault')):
                    with self.assertRaises(OSError):
                        self.publish()
                self.assertEqual(self.messages._path.read_bytes() if self.messages._path.exists() else None, before)
                self.assertEqual(self.messages._messages, memory)
                self.assertEqual(self.messages._next_id, next_id)
                callback.assert_not_called()
                reset.assert_not_called()
        sequence = []
        self.messages.on_message(lambda value: sequence.append('emit'))
        message = self.publish(channel='review')
        sequence.append('persist')
        self.assertEqual(self.messages.get_snapshot(message['id']), message)
        reset('review')
        sequence.append('reset')
        self.messages._emit_operator(message, authority=store._OPERATOR_PUBLICATION)
        self.assertEqual(sequence, ['persist', 'reset', 'emit'])
        reset.assert_called_once_with('review')

    def test_partial_append_failure_restores_exact_prior_bytes_and_id(self):
        self.messages.add('seat', 'prior')
        before = self.messages._path.read_bytes()
        memory, next_id = deepcopy(self.messages._messages), self.messages._next_id
        observed = Mock()
        self.messages.on_message(observed)
        real_open = open
        class PartialWriter:
            def __init__(self, file):
                self.file = file
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return self.file.__exit__(*args)
            def __getattr__(self, name):
                return getattr(self.file, name)
            def write(self, value):
                self.file.write(value[:max(1, len(value) // 2)])
                self.file.flush()
                raise OSError('bounded partial write fault')
        def opening(*args, **kwargs):
            file = real_open(*args, **kwargs)
            return PartialWriter(file) if 'a' in str(args[1] if len(args) > 1 else kwargs.get('mode', 'r')) else file
        with patch('store.open', side_effect=opening, create=True), self.assertRaises(OSError):
            self.publish()
        self.assertEqual(self.messages._path.read_bytes(), before)
        self.assertEqual(self.messages._messages, memory)
        self.assertEqual(self.messages._next_id, next_id)
        observed.assert_not_called()
        self.assertEqual(self.publish()['id'], next_id)

    def test_generic_add_once_metadata_copy_and_update_cannot_forge_receipt(self):
        metadata = {'recipient_routing': {'forged': True}, 'nested': {'items': ['original']}}
        first = self.messages.add('seat', 'plain', metadata=metadata, uid='caller-generic', timestamp=8)
        second = self.messages.add_once('projection-uid', 'session', 'projection', metadata=metadata)
        metadata['nested']['items'].append('caller edit')
        for message in (first, second):
            self.assertEqual(self.messages.get_snapshot(message['id'])['metadata'], {'nested': {'items': ['original']}})
            self.messages.update_message(message['id'], {'metadata': {'recipient_routing': self.routing, 'ui': True}})
            self.assertNotIn('recipient_routing', self.messages.get_snapshot(message['id'])['metadata'])
        trusted = self.publish()
        receipt = deepcopy(trusted['metadata']['recipient_routing'])
        self.messages.update_message(trusted['id'], {'metadata': {'recipient_routing': {'forged': True}, 'ui': {'expanded': True}}})
        updated = self.messages.get_snapshot(trusted['id'])
        self.assertEqual(updated['metadata']['recipient_routing'], receipt)
        self.assertEqual(updated['metadata']['ui'], {'expanded': True})
        self.assertEqual(self.messages.get_snapshot(first['id'])['uid'], 'caller-generic')
        self.assertEqual(self.messages.get_snapshot(first['id'])['timestamp'], 8)

    def test_job_publication_snapshot_and_observer_payload_are_detached(self):
        job_store, job_id = self.job_store()
        observed = []
        def destructive(action, value):
            value['message']['text'] = 'mutated'
            raise RuntimeError('observer unavailable')
        job_store.on_change(destructive)
        job_store.on_change(lambda action, value: observed.append((action, value)))
        message = job_store._publish_operator(job_id, 'operator', ' café\r\nraw ', routing=self.routing,
            authority=store._OPERATOR_PUBLICATION, attachments=[{'name': 'a.txt'}], msg_type='suggestion')
        self.assertEqual(observed, [])
        self.assertEqual(message['text'], ' café\r\nraw ')
        self.assertEqual(message['metadata']['recipient_routing'], {'version': 1, 'message_uid': message['uid'], **self.routing})
        saved = deepcopy(message)
        message['text'] = 'forged callback text'
        job_store._emit_operator(message, authority=store._OPERATOR_PUBLICATION)
        self.assertEqual(observed, [('message', {'job_id': job_id, 'message': saved})])
        snapshot = job_store.get_message_snapshot(job_id, saved['id'])
        snapshot['metadata']['recipient_routing']['tokens'].append('mutated')
        self.assertEqual(jobs.JobStore(str(job_store._path)).get_message_snapshot(job_id, saved['id']), saved)
        for bad in (True, False, '0', -1, None, 0.0):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                job_store.get_message_snapshot(job_id, bad)
        self.assertIsNone(job_store.get_message_snapshot(job_id, 999))

    def test_job_atomic_write_failure_preserves_disk_memory_and_callbacks(self):
        job_store, job_id = self.job_store()
        before, memory = job_store._path.read_bytes(), deepcopy(job_store._jobs)
        observed = Mock()
        job_store.on_change(observed)
        with patch('api_seats.atomic_json', side_effect=OSError('bounded job write fault')):
            with self.assertRaises(OSError):
                job_store._publish_operator(job_id, 'operator', 'text', routing=self.routing,
                    authority=store._OPERATOR_PUBLICATION)
        self.assertEqual(job_store._path.read_bytes(), before)
        self.assertEqual(job_store._jobs, memory)
        observed.assert_not_called()

    def test_archive_channel_and_job_imports_never_gain_routing_authority(self):
        job_store, _ = self.job_store()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zipped:
            zipped.writestr('manifest.json', json.dumps({'schema_version': archive.SCHEMA_VERSION}))
            zipped.writestr('messages.jsonl', json.dumps({'uid': 'imported', 'sender': 'operator', 'text': 'raw',
                'channel': 'general', 'metadata': {'recipient_routing': self.routing}}) + '\n')
            zipped.writestr('jobs.json', json.dumps([{'uid': 'import-job', 'title': 'Imported', 'channel': 'general',
                'messages': [{'uid': 'import-job-msg', 'sender': 'operator', 'text': 'raw',
                              'metadata': {'recipient_routing': self.routing}}]}]))
        report = archive.import_archive(buffer.getvalue(), self.messages, job_store, None, None, ['general'])
        self.assertTrue(report['ok'])
        message = self.messages.get_snapshot(0)
        self.assertTrue(message['metadata']['imported'])
        self.assertNotIn('recipient_routing', message['metadata'])
        imported = next(job for job in job_store.list_all() if job['uid'] == 'import-job')
        self.assertEqual(len(imported['messages']), 1)
        self.assertNotIn('recipient_routing', imported['messages'][0].get('metadata', {}))

    def test_clear_numeric_id_reuse_keeps_fresh_uid_and_receipt_binding(self):
        first = self.publish()
        self.messages.clear()
        loaded = store.MessageStore(str(self.messages._path))
        second = loaded._publish_operator('operator', 'next', routing=self.routing, authority=store._OPERATOR_PUBLICATION)
        self.assertEqual(first['id'], second['id'])
        self.assertNotEqual(first['uid'], second['uid'])
        self.assertEqual(second['metadata']['recipient_routing']['message_uid'], second['uid'])


if __name__ == '__main__':
    unittest.main()
