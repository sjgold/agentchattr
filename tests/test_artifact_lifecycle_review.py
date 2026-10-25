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
        self.assertIn('Authored artifact metadata is held. Repair saved artifact metadata before changing channels.',report['warnings'])


    def test_terminal_requests_keep_every_active_transport_state_as_blocker(self):
        for transport in ('dispatched','acknowledged','uncertain','cancelling'):
            with self.subTest(transport=transport):
                case=self.context();audit=case.prepare();consumer=case.claim(audit)
                queue=case.trigger.queue
                if transport=='acknowledged':queue.acknowledge(case.instance,audit['dispatch_id'],consumer)
                elif transport=='uncertain':queue.uncertain(case.instance,audit['dispatch_id'],consumer)
                elif transport=='cancelling':queue.cancel_dispatch(audit['dispatch_id'],uuid.uuid4().hex)
                case.artifacts.set_attempt_state(audit['request_id'],audit['attempt_id'],'queued',
                    {'state':'failed','reason':'generation_failed'})
                preview=case.service.preview('archive','review')
                row=next(row for row in preview['blockers'] if row['kind']=='artifact')
                self.assertEqual((row['request_state'],row['transport_state']),('failed',transport))
                self.assertFalse(row['held']);self.assertEqual(row['reason'],'transport_pending')

    def test_catalog_preview_and_token_inputs_never_include_launch_or_seal_authority(self):
        import channel_service
        case=self.context();audit=case.prepare()
        private=case.briefs.get_private(audit['brief_id'])['_artifact_seal']
        token_bytes=[];sha=channel_service.hashlib.sha256
        def observed(raw=b''):
            token_bytes.append(raw);return sha(raw)
        with patch.object(channel_service.hashlib,'sha256',side_effect=observed):
            preview=case.service.preview('delete','review')
        encoded=json.dumps([case.service.catalog_view(),preview]).encode()+b''.join(token_bytes)
        for value in (audit['producer']['launch_nonce'],audit['producer']['fingerprint'],private['seal_secret']):
            self.assertNotIn(value.encode(),encoded)
        for key in (b'launch_nonce',b'fingerprint',b'seal_secret',b'_artifact_seal'):
            self.assertNotIn(key,encoded)

    def test_refusal_http_and_ws_report_saved_effects_at_409(self):
        import asyncio
        import app
        from unittest.mock import AsyncMock
        case=self.context();case.prepare();case.prepare()
        preview=case.service.preview('cancel_queued','review')
        selected=[row for row in preview['blockers'] if row['kind']=='artifact']
        refused=selected[-1]['request_id'];real=case.authority.cancel_request
        def deny(identifier):
            if identifier==refused:raise ChannelConflict('private refusal')
            return real(identifier)
        body={'op':'cancel_queued','channel':'review','request_id':uuid.uuid4().hex,
              'confirmation':'review','preview_token':preview['preview_token']}
        with patch.object(case.authority,'cancel_request',side_effect=deny):
            response,broadcasts=fixture.ArtifactLifecycleMetadataTests.http(case,'apply',body)
        self.assertEqual(response.status_code,409);self.assertEqual(broadcasts,0)
        payload=json.loads(response.body)
        self.assertEqual(payload['refused_request_ids'],[refused])
        self.assertEqual(payload['artifact_cancellation']['cancelled_request_ids'],[selected[0]['request_id']])
        self.assertEqual(payload['artifact_cancellation']['unconfirmed_dispatch_ids'],[])
        fresh=case.service.preview('cancel_queued','review')
        event={'type':'channel_cancel_queued','name':'review','request_id':uuid.uuid4().hex,
            'confirmation':'review','preview_token':fresh['preview_token']}
        ws=AsyncMock()
        with patch.object(case.authority,'cancel_request',side_effect=deny),patch.object(app,'_channels',return_value=case.service), \
                patch.object(app,'_broadcast_channel_projection',AsyncMock()) as broadcast:
            asyncio.run(app._legacy_channel_action(ws,event))
        frame=json.loads(ws.send_text.call_args.args[0])
        self.assertEqual((frame['code'],frame['error_code']),(409,'artifact_cancellation_refused'))
        self.assertEqual(frame['refused_request_ids'],[refused]);broadcast.assert_not_called()
        self.assertNotIn('private',str(frame))

    def test_malformed_orphan_token_changes_without_exposing_raw_id(self):
        case=self.context();case.prepare();raw=case.trigger.queue._queue
        value=json.loads(raw.path.read_text(encoding='utf-8'))
        empty=case.storage.ArtifactStore(case.root/'empty-for-token');empty.bind_channel_policy(lambda:case.service)
        case.service.authored_artifacts=empty;tokens=[]
        for identifier in ('bad-artifact-one','bad-artifact-two'):
            value['records'][0]['envelope']['dispatch_id']=identifier
            raw.path.write_text(json.dumps(value),encoding='utf-8')
            with patch.object(empty,'get_request_by_dispatch',side_effect=AssertionError('invalid lookup')):
                preview=case.service.preview('archive','review')
            self.assertNotIn(identifier,str(preview));tokens.append(preview['preview_token'])
        self.assertNotEqual(*tokens)


    def test_later_persistence_failure_never_labels_uncancelled_request_as_failed_fence(self):
        from artifact_store import ArtifactUnavailable
        case=self.context();case.prepare();case.prepare()
        preview=case.service.preview('cancel_queued','review')
        selected=[row for row in preview['blockers'] if row['kind']=='artifact'];second=selected[1]['request_id']
        real=case.artifacts.set_attempt_state
        def fail_later(identifier,*args,**kwargs):
            if identifier==second:raise ArtifactUnavailable('private persist failure')
            return real(identifier,*args,**kwargs)
        with patch.object(case.artifacts,'set_attempt_state',side_effect=fail_later):
            with self.assertRaises(ChannelUnavailable) as caught:self.apply_cancel(case,preview)
        self.assertEqual(caught.exception.code,'artifact_cancellation_partial')
        summary=caught.exception.payload['artifact_cancellation']
        self.assertEqual(summary['cancelled_request_ids'],[selected[0]['request_id']])
        self.assertEqual(summary['unconfirmed_dispatch_ids'],[])
        self.assertEqual(case.artifacts.get_request(second)['state'],'queued')

    def test_artifact_import_policy_hold_skips_lineage_without_creating_channel(self):
        import archive
        from tests import test_artifact_archive_driver as driver
        case=driver.ArtifactArchiveDriverTests();self.addCleanup(case.doCleanups);case.setUp()
        case.source_graph(attempts=False);case.source.rename_channel('review','new-import')
        data=case.export()
        # Explicit policy-owner observation: the import target is healthy while
        # the lifecycle's authored metadata owner is held at channel resolution.
        case.service.authored_artifacts=case.source
        case.source.path.write_bytes(b'HELD_POLICY_OWNER')
        result=case.restore(data)
        self.assertTrue(result['ok']);self.assertFalse(result['partial'])
        section=result['sections']['artifacts']
        self.assertEqual(section['channel_unavailable_lineages'],1)
        self.assertEqual(section['details'][0]['channel_reason'],'artifact_owner_held')
        self.assertEqual(case.target.export_lineage_ids(),())
        self.assertNotIn('new-import',case.catalog.snapshot()['channels'])
        self.assertIn('Authored artifact metadata is held. Repair saved artifact metadata before changing channels.',result['warnings'])

    def test_deletion_disclosure_is_specific_to_delete_preview(self):
        case=self.context();self.reserve(case,terminal=True)
        archived=case.service.preview('archive','review');deleted=case.service.preview('delete','review')
        self.assertNotIn('Deleting',archived['artifact_source_disclosure'])
        self.assertTrue(deleted['artifact_source_disclosure'].startswith('Deleting chat and todos keeps'))


    def test_held_authored_owner_does_not_block_actual_review_projection_repair(self):
        from artifact_store import ArtifactStore
        from tests import test_channel_projections as projections
        case=projections.ChannelProjectionTests();self.addCleanup(case.doCleanups);case.setUp()
        case.pending_final();case.bind()
        owner=ArtifactStore(case.root/'held-authored');owner.path.parent.mkdir(parents=True)
        owner.path.write_bytes(b'HELD_INDEX');case.service.authored_artifacts=owner
        preview=case.service.preview('recover_projections','review')
        result=case.service.apply('recover_projections','review',request_id=uuid.uuid4().hex,
            confirmation='review',preview_token=preview['preview_token'])
        self.assertTrue(result['ok'])
        self.assertIn('Pending exact result',[row['text'] for row in case.messages.get_recent(100)])
        self.assertEqual(owner.path.read_bytes(),b'HELD_INDEX')

    def test_launch_timeout_in_remaining_queue_and_repair_fence_keeps_saved_ids(self):
        case=self.context();audit=case.prepare()
        chat=case.trigger.queue.enqueue(case.instance,{'channel':'review','text':'ordinary'})
        preview=case.service.preview('cancel_queued','review')
        with patch.object(case.trigger.queue,'cancel_queued_channel',side_effect=LaunchError('private timeout')):
            with self.assertRaises(ChannelUnavailable) as caught:self.apply_cancel(case,preview)
        self.assertEqual(caught.exception.code,'artifact_cancellation_partial')
        self.assertEqual(caught.exception.payload['artifact_cancellation']['cancelled_request_ids'],[audit['request_id']])
        self.assertEqual(caught.exception.payload['artifact_cancellation']['unconfirmed_dispatch_ids'],[chat['envelope']['dispatch_id']])
        # Fresh case, cancelled request whose earlier fence has not landed.
        other=self.context();pending=other.prepare()
        with patch.object(other.authority,'_fence',side_effect=OSError('first fence')):
            other.authority.cancel_request(pending['request_id'])
        with patch.object(other.authority,'_fence',side_effect=LaunchError('repair timeout')):
            with self.assertRaises(ChannelUnavailable) as repaired:self.apply_cancel(other)
        self.assertEqual(repaired.exception.code,'artifact_cancellation_partial')
        self.assertEqual(repaired.exception.payload['artifact_cancellation']['unconfirmed_dispatch_ids'],[pending['dispatch_id']])


if __name__=='__main__':unittest.main()
