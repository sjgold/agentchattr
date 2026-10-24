"""Retained data and delete fault boundaries with real local stores."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import uuid

from channel_lifecycle import ChannelUnavailable
from retained_artifacts import RetainedArtifactStore
from tests import test_channel_service as fixture


class ChannelRetainedTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelServiceTests.setUp(self)
        self.artifact_path = self.root / 'retained_artifacts.json'
        self.uploads = self.root / 'uploads'
        self.uploads.mkdir()
        self.messages.upload_dir = self.uploads
        self.upload = self.uploads / 'abcd1234.png'
        self.upload.write_bytes(b'exact upload bytes')

    def saved(self):
        message = self.messages.add('operator', 'Private source body', channel='review',
            attachments=[{'name': 'Original name.png', 'url': '/uploads/abcd1234.png', 'path': str(self.upload)}])
        self.messages.add_todo(message['id'])
        return message

    def delete(self, request_id=None):
        preview = self.service.preview('delete', 'review')
        return self.service.apply('delete', 'review', request_id=request_id or uuid.uuid4().hex,
            confirmation='review', preview_token=preview['preview_token'])

    def test_delete_retains_upload_source_reference_before_history_disappears(self):
        message = self.saved()
        result = self.delete()
        self.assertEqual(result['state'], 'retired')
        self.assertTrue(self.artifact_path.exists(), 'The channel backlink must outlive message deletion.')
        self.assertEqual(self.upload.read_bytes(), b'exact upload bytes')
        self.assertIsNone(self.messages.get_snapshot(message['id']))
        retained = self.service.retained_view('review')
        self.assertEqual(retained['uploads'][0]['message_uid'], message['uid'])
        self.assertEqual(retained['uploads'][0]['attachments'], message['attachments'])
        self.assertNotIn(message['text'], json.dumps(retained))

    def test_retained_view_exposes_summary_and_only_metadata_for_saved_owners(self):
        self.summaries.write('review', 'Exact retained summary', 'operator')
        job = self.jobs.create('Saved job', 'task', 'review', 'operator')
        self.jobs.add_message(job['id'], 'operator', 'CONVERSATION BODY MUST NOT APPEAR')
        self.schedules.create('PROMPT MUST NOT APPEAR', ['codex'], channel='review', interval_seconds=3600)
        run = self.sessions.create('review', 'review', {'reviewer': 'human', 'editor': 'human'},
                                   'operator', input_text='FROZEN INPUT MUST NOT APPEAR')
        packet = self.service.retained_view('review')
        self.assertEqual(packet['summary']['text'], 'Exact retained summary')
        self.assertEqual(packet['jobs'][0]['id'], job['id'])
        self.assertEqual(packet['sessions'][0]['id'], run['id'])
        encoded = json.dumps(packet)
        for forbidden in ('CONVERSATION BODY MUST NOT APPEAR', 'PROMPT MUST NOT APPEAR', 'FROZEN INPUT MUST NOT APPEAR'):
            self.assertNotIn(forbidden, encoded)

    def test_pre_begin_probe_failure_preserves_catalog_todos_and_messages(self):
        self.saved()
        before = (self.catalog.path.read_bytes(), self.messages._path.read_bytes(),
                  self.messages._todos_path.read_bytes())
        with patch('retained_artifacts.atomic_json', side_effect=OSError('probe failure')):
            with self.assertRaises(ChannelUnavailable):
                self.delete()
        self.assertEqual((self.catalog.path.read_bytes(), self.messages._path.read_bytes(),
                          self.messages._todos_path.read_bytes()), before)
        self.assertFalse(self.artifact_path.exists())

    def test_known_corrupt_metadata_refuses_before_any_delete_effect(self):
        self.saved()
        self.artifact_path.write_bytes(b'{corrupt metadata')
        before = (self.catalog.path.read_bytes(), self.messages._path.read_bytes(),
                  self.messages._todos_path.read_bytes())
        with self.assertRaises(ChannelUnavailable):
            self.delete()
        self.assertEqual((self.catalog.path.read_bytes(), self.messages._path.read_bytes(),
                          self.messages._todos_path.read_bytes()), before)
        self.assertEqual(self.artifact_path.read_bytes(), b'{corrupt metadata')

    def test_late_metadata_write_fault_holds_messages_and_uploads_then_retry_converges(self):
        import retained_artifacts
        message = self.saved()
        before = self.messages._path.read_bytes()
        request = uuid.uuid4().hex
        writer = retained_artifacts.atomic_json
        def fail_references(path, value):
            if value['channels']:
                raise OSError('late metadata failure')
            return writer(path, value)
        with patch('retained_artifacts.atomic_json', side_effect=fail_references):
            with self.assertRaises(ChannelUnavailable):
                self.delete(request)
        self.assertEqual(self.catalog.snapshot()['intent']['completed_steps'], ['todos'])
        self.assertEqual(self.messages.get_todos(), {})
        self.assertEqual(self.messages._path.read_bytes(), before)
        self.assertEqual(self.upload.read_bytes(), b'exact upload bytes')
        self.service.retry(request)
        self.assertEqual(self.service.retained_view('review')['uploads'][0]['message_uid'], message['uid'])

    def test_rewrite_failure_keeps_durable_metadata_and_originals_without_duplicate_merge(self):
        message = self.saved()
        request = uuid.uuid4().hex
        before = self.messages._path.read_bytes()
        with patch.object(self.messages, '_rewrite_jsonl', side_effect=OSError('rewrite failure')):
            with self.assertRaises(ChannelUnavailable):
                self.delete(request)
        metadata = self.artifact_path.read_bytes()
        self.assertEqual(RetainedArtifactStore(self.artifact_path).read('review')['count'], 1)
        self.assertEqual(self.messages._path.read_bytes(), before)
        self.assertEqual(self.messages.get_snapshot(message['id']), message)
        with patch('retained_artifacts.atomic_json', side_effect=AssertionError('retry merge must not write')):
            self.service.retry(request)
        self.assertEqual(self.artifact_path.read_bytes(), metadata)
        self.assertEqual(self.upload.read_bytes(), b'exact upload bytes')

    def test_lost_message_mark_resumes_after_reload_and_retained_reference_stays_exact(self):
        message = self.saved()
        request = uuid.uuid4().hex
        complete = self.catalog.complete_step
        def fail_message_mark(identifier, step):
            if step == 'messages':
                raise OSError('lost mark after both durable writes')
            return complete(identifier, step)
        with patch.object(self.catalog, 'complete_step', side_effect=fail_message_mark):
            with self.assertRaises(ChannelUnavailable):
                self.delete(request)
        self.assertIsNone(self.messages.get_snapshot(message['id']))
        before = self.artifact_path.read_bytes()
        self.service.artifacts = RetainedArtifactStore(self.artifact_path)
        with patch('retained_artifacts.atomic_json', side_effect=AssertionError('lost mark merge wrote')):
            self.service.retry(request)
        self.assertEqual(self.artifact_path.read_bytes(), before)
        self.assertEqual(self.service.retained_view('review')['uploads'][0]['message_uid'], message['uid'])

    def test_delete_preview_discloses_upload_reference_count(self):
        self.saved()
        self.assertEqual(self.service.preview('delete', 'review')['counts']['uploads'], 1)

    def test_attachment_count_change_invalidates_delete_confirmation(self):
        from channel_lifecycle import ChannelConflict
        message = self.saved()
        preview = self.service.preview('delete', 'review')
        self.messages.update_message(message['id'], {'attachments': []})
        with self.assertRaises(ChannelConflict):
            self.service.apply('delete', 'review', request_id=uuid.uuid4().hex, confirmation='review',
                               preview_token=preview['preview_token'])
        self.assertIsNone(self.catalog.snapshot()['intent'])
