"""Slice4 root behavioral regressions on actual lifecycle/store/queue owners.

Managed producer support and process observations are fixture controlled by the
existing admission fixture. No native process, provider, HTTP or browser claim.
"""
import unittest
from unittest.mock import patch
import uuid

from channel_lifecycle import ChannelConflict, ChannelUnavailable
from tests import test_artifact_lifecycle as fixture


class ArtifactLifecycleMetadataTests(unittest.TestCase):
    context=fixture.ArtifactLifecycleTests.context

    def reserve(self,case,*,terminal=False):
        audit,packet=case.new_request()
        case.artifacts.reserve_request(audit,audit['request_id'])
        if terminal:
            case.artifacts.set_attempt_state(audit['request_id'],audit['attempt_id'],'prepared',
                {'state':'failed','reason':'generation_failed'})
        return audit

    def test_lifecycle_scope_includes_all_requests_heads_and_copied_source_bytes(self):
        case=self.context();audit=self.reserve(case,terminal=True)
        with patch.object(case.artifacts,'get_packet',side_effect=AssertionError('metadata body read')):
            scope=case.artifacts.lifecycle_scope('review')
        self.assertIn('requests',scope)
        self.assertEqual(scope['request_count'],1)
        self.assertEqual(scope['source_bytes'],audit['scope']['byte_length'])
        self.assertEqual(scope['requests'][0]['request_id'],audit['request_id'])
        self.assertEqual(scope['requests'][0]['state'],'failed')
        self.assertIsNone(scope['lineages'][0]['head_version_id'])
        self.assertIsNone(scope['lineages'][0]['head_sha256'])
        scope['requests'].clear()
        self.assertEqual(case.artifacts.lifecycle_scope('review')['request_count'],1)

    def test_catalog_and_retained_authored_counts_are_metadata_only_and_detached(self):
        case=self.context();audit=self.reserve(case)
        case.messages.add('operator','healthy peer',channel='peer')
        with patch.object(case.artifacts,'get_packet',side_effect=AssertionError('packet read')), \
                patch.object(case.artifacts,'get_version',side_effect=AssertionError('Markdown read')):
            view=case.service.catalog_view();retained=case.service.retained_view('review')
        row=next(row for row in view['channels'] if row['name']=='review')
        self.assertEqual(row['counts'].get('artifacts'),1)
        self.assertEqual(row['counts']['artifact_versions'],0)
        self.assertEqual(row['counts']['artifact_requests'],1)
        self.assertEqual(row['counts']['artifact_source_bytes'],audit['scope']['byte_length'])
        self.assertFalse(row['artifacts_held'])
        self.assertEqual(retained['counts']['artifacts'],1)
        self.assertFalse(retained['truncated']['artifacts'])
        self.assertEqual(retained['artifacts'][0]['pending_request']['request_id'],audit['request_id'])
        self.assertNotIn('launch_nonce',str(retained))
        retained['artifacts'].clear()
        self.assertEqual(case.service.retained_view('review')['counts']['artifacts'],1)
        self.assertEqual(next(row for row in view['channels'] if row['name']=='peer')['counts']['messages'],1)

    def test_delete_preview_discloses_retained_copied_source_for_terminal_attempt(self):
        case=self.context();audit=self.reserve(case,terminal=True)
        preview=case.service.preview('delete','review')
        self.assertEqual(preview['counts'].get('artifact_requests'),1)
        self.assertEqual(preview['counts']['artifact_source_bytes'],audit['scope']['byte_length'])
        self.assertTrue(preview['artifact_source_retained'])
        self.assertIn('copied source',preview['artifact_source_disclosure'])
        self.assertNotIn('launch_nonce',str(preview))
        result=case.service.apply('delete','review',request_id=uuid.uuid4().hex,confirmation='review',
                                  preview_token=preview['preview_token'])
        self.assertTrue(result['ok'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['audit'],audit)
        self.assertEqual(case.artifacts.get_packet(audit['scope']['packet_id'])['channel'],'review')

    def test_held_authored_index_isolated_from_healthy_catalog_and_retained_peers(self):
        case=self.context();self.reserve(case)
        case.jobs.create('healthy retained job','task','review','operator')
        case.artifacts.path.write_bytes(b'BROKEN_ARTIFACT_INDEX')
        view=case.service.catalog_view();retained=case.service.retained_view('review')
        row=next(row for row in view['channels'] if row['name']=='review')
        self.assertTrue(row.get('artifacts_held'))
        self.assertIsNone(row['counts']['artifacts'])
        self.assertEqual(row['errors']['artifacts'],'Saved authored artifacts are held; repair storage and reload.')
        self.assertEqual(row['counts']['jobs'],1)
        self.assertIsNone(retained['artifacts'])
        self.assertTrue(retained['artifacts_held'])
        self.assertIsNone(retained['artifact_source_retained'])
        self.assertEqual(retained['counts']['jobs'],1)
        self.assertEqual(case.artifacts.path.read_bytes(),b'BROKEN_ARTIFACT_INDEX')

    def test_orphan_artifact_queue_record_is_a_held_ownership_mismatch(self):
        case=self.context();audit=case.prepare()
        empty=case.storage.ArtifactStore(case.root/'empty-authored-owner')
        empty.bind_channel_policy(lambda:case.service)
        case.service.authored_artifacts=empty
        preview=case.service.preview('archive','review')
        rows=[row for row in preview['blockers'] if row['kind']=='artifact']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['dispatch_id'],audit['dispatch_id'])
        self.assertIsNone(rows[0]['request_state'])
        self.assertTrue(rows[0]['held'])
        self.assertEqual(rows[0]['reason'],'ownership_mismatch')

    def test_queued_cancel_persists_request_before_fencing_exact_dispatch(self):
        case=self.context();audit=case.prepare();events=[]
        persist=case.artifacts.set_attempt_state;fence=case.authority._fence
        def observed_state(*args,**kwargs):
            result=persist(*args,**kwargs);events.append(('request',result['state']));return result
        def observed_fence(row):
            self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')
            events.append(('fence',row['audit']['dispatch_id']));return fence(row)
        preview=case.service.preview('cancel_queued','review')
        with patch.object(case.artifacts,'set_attempt_state',side_effect=observed_state), \
                patch.object(case.authority,'_fence',side_effect=observed_fence):
            result=case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
                confirmation='review',preview_token=preview['preview_token'])
        self.assertTrue(result['ok'])
        self.assertEqual(events,[('request','cancelled'),('fence',audit['dispatch_id'])])
        self.assertEqual(result['artifact_cancellation'],{'cancelled_request_ids':[audit['request_id']],
            'fenced_dispatch_ids':[audit['dispatch_id']],'unconfirmed_dispatch_ids':[]})
        self.assertEqual(case.trigger.queue.owned(case.instance,audit['dispatch_id'])['state'],'cancelled')

    def test_missing_cancel_service_refuses_before_queue_or_request_changes(self):
        case=self.context();audit=case.prepare();case.service.artifact_service_getter=None
        preview=case.service.preview('cancel_queued','review');before=case.files()
        with self.assertRaises(ChannelUnavailable) as caught:
            case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
                confirmation='review',preview_token=preview['preview_token'])
        self.assertEqual(getattr(caught.exception,'code',None),'artifact_cancellation_unavailable')
        self.assertEqual(case.files(),before)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'queued')

    def test_claimed_artifact_is_not_eligible_for_queued_only_cancellation(self):
        case=self.context();audit=case.prepare();case.claim(audit)
        preview=case.service.preview('cancel_queued','review');before=case.files()
        with self.assertRaises(ChannelConflict):
            case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
                confirmation='review',preview_token=preview['preview_token'])
        self.assertEqual(case.files(),before)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'queued')


if __name__=='__main__':unittest.main()
