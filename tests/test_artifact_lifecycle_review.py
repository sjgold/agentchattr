"""Root-owned slice4 review regressions; real temp owners, controlled faults."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from channel_lifecycle import ChannelConflict, ChannelUnavailable
from launcher import LaunchError
from tests import test_artifact_lifecycle_metadata as fixture


class ArtifactLifecycleReviewTests(unittest.TestCase):
    context=fixture.ArtifactLifecycleMetadataTests.context
    reserve=fixture.ArtifactLifecycleMetadataTests.reserve

    def apply_cancel(self,case,preview=None):
        preview=preview or case.service.preview('cancel_queued','review')
        return case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
            confirmation='review',preview_token=preview['preview_token'])

    def test_queue_lock_timeout_after_persist_is_unconfirmed_not_unhandled(self):
        for direct in (False,True):
            with self.subTest(direct=direct):
                case=self.context();audit=case.prepare()
                with patch.object(case.authority,'_fence',side_effect=LaunchError('private queue timeout')):
                    if direct:
                        result=case.authority.cancel_request(audit['request_id'])
                        self.assertFalse(result['transport_settled'])
                        self.assertEqual(result['warning'],'transport_unconfirmed')
                    else:
                        with self.assertRaises(ChannelUnavailable) as caught:self.apply_cancel(case)
                        self.assertEqual(caught.exception.code,'artifact_cancellation_partial')
                        summary=caught.exception.payload['artifact_cancellation']
                        self.assertEqual(summary['cancelled_request_ids'],[audit['request_id']])
                        self.assertEqual(summary['unconfirmed_dispatch_ids'],[audit['dispatch_id']])
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')

    def test_active_request_never_uses_queued_only_bridge_even_with_queued_transport(self):
        case=self.context();audit=case.prepare()
        case.artifacts.set_attempt_state(audit['request_id'],audit['attempt_id'],'queued',{'state':'active','reason':None})
        preview=case.service.preview('cancel_queued','review');before=case.files()
        with self.assertRaises(ChannelConflict):self.apply_cancel(case,preview)
        self.assertEqual(case.files(),before)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')

    def test_unexpected_first_or_later_refusal_never_becomes_unconfirmed(self):
        for position in (0,1):
            with self.subTest(position=position):
                case=self.context();case.prepare();case.prepare()
                preview=case.service.preview('cancel_queued','review')
                selected=[row for row in preview['blockers'] if row['kind']=='artifact']
                refused=selected[position]['request_id'];cancel=case.authority.cancel_request
                def refuse(identifier):
                    if identifier==refused:raise ChannelConflict('private refusal')
                    return cancel(identifier)
                with patch.object(case.authority,'cancel_request',side_effect=refuse):
                    with self.assertRaises(ChannelConflict) as caught:self.apply_cancel(case,preview)
                payload=caught.exception.payload
                self.assertEqual(caught.exception.code,'artifact_cancellation_refused')
                self.assertEqual(payload['refused_request_ids'],[refused])
                self.assertEqual(payload['artifact_cancellation']['unconfirmed_dispatch_ids'],[])
                saved=[row['request_id'] for row in selected[:position]]
                self.assertEqual(payload['artifact_cancellation']['cancelled_request_ids'],saved)
                self.assertEqual(case.artifacts.get_request(refused)['state'],'queued')

    def test_prevalidation_refusal_checks_all_rows_before_any_mutation(self):
        case=self.context();case.prepare();case.prepare()
        preview=case.service.preview('cancel_queued','review');before=case.files()
        rows=[row for row in preview['blockers'] if row['kind']=='artifact'];refused=rows[-1]['request_id']
        def validation(identifier):
            if identifier==refused:raise ChannelConflict('private predicate refusal')
        # Explicit future pure-predicate seam; mutation still goes through the real bridge.
        with patch.object(case.authority,'validate_queued_cancellation',side_effect=validation,create=True):
            with self.assertRaises(ChannelConflict) as caught:self.apply_cancel(case,preview)
        self.assertEqual(caught.exception.code,'artifact_cancellation_refused')
        self.assertEqual(caught.exception.payload['refused_request_ids'],[refused])
        self.assertEqual(caught.exception.payload['artifact_cancellation'],{
            'cancelled_request_ids':[],'fenced_dispatch_ids':[],'unconfirmed_dispatch_ids':[]})
        self.assertEqual(case.files(),before)

    def test_unverifiable_orphan_ids_are_sanitized_held_rows_not_store_lookups(self):
        for fault in ('missing_request','malformed_dispatch'):
            with self.subTest(fault=fault):
                case=self.context();audit=case.prepare()
                raw=case.trigger.queue._queue
                value=json.loads(raw.path.read_text(encoding='utf-8'))
                envelope=value['records'][0]['envelope']
                if fault=='missing_request':envelope.pop('artifact_request_id')
                else:envelope['dispatch_id']='not-an-artifact-id'
                raw.path.write_text(json.dumps(value),encoding='utf-8')
                empty=case.storage.ArtifactStore(case.root/'empty-authored')
                empty.bind_channel_policy(lambda:case.service);case.service.authored_artifacts=empty
                preview=case.service.preview('archive','review')
                rows=[row for row in preview['blockers'] if row['kind']=='artifact']
                self.assertEqual(len(rows),1);self.assertTrue(rows[0]['held'])
                self.assertEqual(rows[0]['reason'],'ownership_mismatch')
                self.assertIsNone(rows[0]['request_state'])
                self.assertIsNone(rows[0]['request_id'] if fault=='missing_request' else rows[0]['dispatch_id'])
                self.assertNotIn('not-an-artifact-id',str(preview))

    def test_omitted_owner_keeps_legacy_preview_shape(self):
        case=self.context();case.service.authored_artifacts=None
        preview=case.service.preview('delete','review')
        for key in ('artifacts_held','artifact_source_retained','artifact_source_disclosure'):
            self.assertNotIn(key,preview)
        self.assertTrue({'artifacts','artifact_versions','artifact_requests','artifact_source_bytes'}.isdisjoint(preview['counts']))

    def test_held_owner_still_allows_ordinary_queued_cancel_and_repair_preview(self):
        case=self.context();self.reserve(case,terminal=True)
        queued=case.trigger.queue.enqueue(case.instance,{'channel':'review','text':'ordinary only'})
        case.artifacts.path.write_bytes(b'HELD_INDEX')
        preview=case.service.preview('cancel_queued','review')
        self.assertTrue(self.apply_cancel(case,preview)['ok'])
        self.assertEqual(case.trigger.queue.owned(case.instance,queued['envelope']['dispatch_id'])['state'],'cancelled')
        repair=case.service.preview('recover_projections','review')
        self.assertIn('preview_token',repair)
        self.assertEqual(case.artifacts.path.read_bytes(),b'HELD_INDEX')

    def test_import_cannot_create_channel_while_authored_owner_is_held(self):
        import archive
        case=self.context();self.reserve(case,terminal=True)
        case.artifacts.path.write_bytes(b'HELD_INDEX')
        resolved=case.service.resolve_import_channel('new-import',max_channels=8)
        self.assertEqual(resolved,{'channel':'general','created':False,'reason':'artifact_owner_held'})
        data=archive.build_export(SimpleNamespace(get_recent=lambda count:[
            {'id':0,'uid':'existing-channel','sender':'operator','text':'kept','channel':'peer'},
            {'id':1,'uid':'new-channel','sender':'operator','text':'redirected','channel':'new-import'}]),None,None,None)
        report=archive.import_archive(data,case.messages,None,None,None,list(case.settings['channels']),
            channel_policy=case.service,artifact_store=case.artifacts)
        self.assertTrue(report['ok'])
        self.assertNotIn('new-import',case.catalog.snapshot()['channels'])
        self.assertEqual(len(case.messages.get_recent(10,channel='peer')),1)
        self.assertEqual(len(case.messages.get_recent(10,channel='general')),1)
        self.assertEqual(report['channels']['remapped'][0]['reason'],'artifact_owner_held')
        self.assertEqual(report['channels']['remap_counts'][0]['count'],1)


if __name__=='__main__':unittest.main()
