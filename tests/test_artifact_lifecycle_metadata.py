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


    def test_partial_fence_reports_then_fresh_retry_repairs_only_the_fence(self):
        case=self.context();audit=case.prepare()
        preview=case.service.preview('cancel_queued','review')
        with patch.object(case.authority,'_fence',side_effect=OSError('private fence fault')):
            with self.assertRaises(ChannelUnavailable) as caught:
                case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
                    confirmation='review',preview_token=preview['preview_token'])
        self.assertEqual(caught.exception.code,'artifact_cancellation_partial')
        self.assertEqual(caught.exception.payload['artifact_cancellation'],{
            'cancelled_request_ids':[audit['request_id']],'fenced_dispatch_ids':[],
            'unconfirmed_dispatch_ids':[audit['dispatch_id']]})
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')
        self.assertEqual(case.trigger.queue.owned(case.instance,audit['dispatch_id'])['state'],'queued')
        fresh=case.service.preview('cancel_queued','review')
        with patch.object(case.authority,'cancel_request',side_effect=AssertionError('request state repeated')), \
                patch.object(case.authority,'repair_cancel_fences',wraps=case.authority.repair_cancel_fences) as repair:
            result=case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
                confirmation='review',preview_token=fresh['preview_token'])
        repair.assert_called_once_with([audit['request_id']])
        self.assertEqual(result['artifact_cancellation']['fenced_dispatch_ids'],[audit['dispatch_id']])
        self.assertTrue(result['ok']);self.assertIsNone(case.catalog.snapshot()['intent'])
        self.assertEqual(list(case.root.rglob('*.tmp')),[])

    @staticmethod
    def http(case,action,body):
        import asyncio
        import json
        from unittest.mock import AsyncMock
        from starlette.requests import Request
        import app
        raw=json.dumps(body).encode()
        async def receive():return {'type':'http.request','body':raw,'more_body':False}
        request=Request({'type':'http','method':'POST','path':'/api/channels/'+action,
            'query_string':b'','headers':[],'server':('testserver',80),'scheme':'http',
            'state':{'auth_origin':'operator'}},receive)
        with patch.object(app,'_channels',return_value=case.service), \
                patch.object(app,'_broadcast_channel_projection',AsyncMock()) as broadcast:
            result=asyncio.run(app._channel_http(request,action))
        return result,broadcast.call_count

    def test_held_preview_and_mutations_have_fixed_http_and_ws_projection(self):
        import asyncio
        import json
        from unittest.mock import AsyncMock
        import app
        for op in ('create','reopen','archive','rename','delete'):
            with self.subTest(op=op):
                case=self.context();self.reserve(case)
                if op=='reopen':case.catalog.set_state('review','archived',expected_revision=case.catalog.snapshot()['revision'])
                case.artifacts.path.write_bytes(b'HELD_INDEX');before=case.files()
                body={'op':op,'channel':'new-channel' if op=='create' else 'review'}
                if op=='rename':body['new_name']='renamed'
                response,broadcasts=self.http(case,'preview',body)
                self.assertEqual(response.status_code,503)
                result=json.loads(response.body)
                self.assertEqual(result['code'],'artifact_owner_held')
                self.assertTrue(result['artifacts_held']);self.assertIsNone(result['artifact_source_retained'])
                self.assertEqual(set(result['artifact_counts']),{'artifacts','artifact_versions','artifact_requests','artifact_source_bytes'})
                self.assertTrue(all(value is None for value in result['artifact_counts'].values()))
                self.assertNotIn('preview_token',result);self.assertEqual(broadcasts,0)
                self.assertEqual(case.files(),before)
                applied={**body,'request_id':uuid.uuid4().hex,'confirmation':body['channel'],'preview_token':'invalid'}
                refused,broadcasts=self.http(case,'apply',applied)
                self.assertEqual(refused.status_code,503)
                self.assertEqual(json.loads(refused.body)['code'],'artifact_owner_held')
                self.assertEqual(refused.headers['cache-control'],'no-store')
                self.assertEqual(broadcasts,0);self.assertEqual(case.files(),before)
                event={'type':'channel_'+op,'request_id':uuid.uuid4().hex,'name':body['channel'],
                       'confirmation':body['channel'],'preview_token':'invalid'}
                if op=='rename':event.pop('name');event.update(old_name='review',new_name='renamed')
                websocket=AsyncMock()
                with patch.object(app,'_channels',return_value=case.service), \
                        patch.object(app,'_broadcast_channel_projection',AsyncMock()) as broadcast:
                    asyncio.run(app._legacy_channel_action(websocket,event))
                frame=json.loads(websocket.send_text.call_args.args[0])
                self.assertEqual((frame['type'],frame['code'],frame['error_code']),('channel_error',503,'artifact_owner_held'))
                self.assertTrue(frame['artifacts_held']);broadcast.assert_not_called()
                self.assertEqual(case.files(),before)

    def test_missing_and_partial_cancellation_wires_expose_no_success_event(self):
        import asyncio
        import json
        from unittest.mock import AsyncMock
        import app
        for fault in ('missing','partial'):
            with self.subTest(fault=fault):
                case=self.context();audit=case.prepare()
                if fault=='missing':case.service.artifact_service_getter=None
                preview=case.service.preview('cancel_queued','review')
                body={'op':'cancel_queued','channel':'review','request_id':uuid.uuid4().hex,
                      'confirmation':'review','preview_token':preview['preview_token']}
                with patch.object(case.authority,'_fence',side_effect=OSError('private')):
                    response,broadcasts=self.http(case,'apply',body)
                self.assertEqual(response.status_code,503)
                result=json.loads(response.body)
                self.assertEqual(result['code'],'artifact_cancellation_'+('unavailable' if fault=='missing' else 'partial'))
                self.assertEqual(broadcasts,0)
                if fault=='partial':
                    self.assertFalse(result['ok']);self.assertEqual(result['warning'],'transport_unconfirmed')
                    self.assertEqual(result['artifact_cancellation']['unconfirmed_dispatch_ids'],[audit['dispatch_id']])
                else:self.assertNotIn('artifact_cancellation',result)
                fresh=case.service.preview('cancel_queued','review')
                event={'type':'channel_cancel_queued','name':'review','request_id':uuid.uuid4().hex,
                       'confirmation':'review','preview_token':fresh['preview_token']}
                websocket=AsyncMock()
                with patch.object(case.authority,'_fence',side_effect=OSError('private')), \
                        patch.object(app,'_channels',return_value=case.service), \
                        patch.object(app,'_broadcast_channel_projection',AsyncMock()) as broadcast:
                    asyncio.run(app._legacy_channel_action(websocket,event))
                frame=json.loads(websocket.send_text.call_args.args[0])
                self.assertEqual(frame['error_code'],result['code']);self.assertEqual(frame['code'],503)
                self.assertNotIn('private',json.dumps(frame));broadcast.assert_not_called()
                self.assertEqual(case.trigger.queue.owned(case.instance,audit['dispatch_id'])['state'],'queued')

    def test_terminal_state_and_new_version_invalidate_existing_preview_without_body_reads(self):
        case=self.context();audit=self.reserve(case)
        first=case.service.preview('delete','review')
        case.artifacts.set_attempt_state(audit['request_id'],audit['attempt_id'],'prepared',
            {'state':'failed','reason':'generation_failed'})
        with self.assertRaises(ChannelConflict):case.service.apply('delete','review',request_id=uuid.uuid4().hex,
            confirmation='review',preview_token=first['preview_token'])
        second=case.service.preview('delete','review')
        self.assertNotEqual(second['preview_token'],first['preview_token'])
        next_audit,_=case.new_request(lineage_id=audit['lineage_id'])
        case.artifacts.reserve_request(next_audit,next_audit['request_id'])
        case.artifacts.set_attempt_state(next_audit['request_id'],next_audit['attempt_id'],'prepared',
            {'state':'queued','reason':'queued'})
        case.artifacts.commit_version(next_audit['request_id'],next_audit['attempt_id'],next_audit['dispatch_id'],
            '# retained',{'confirmed_model':None,'confirmation_reason':'cli_model_unverified'})
        with patch.object(case.artifacts,'_read_object',side_effect=AssertionError('body read')):
            third=case.service.preview('delete','review')
        self.assertNotEqual(third['preview_token'],second['preview_token'])
        self.assertEqual(third['counts']['artifact_versions'],1)
        self.assertEqual(third['counts']['artifact_requests'],2)
        self.assertIsNotNone(case.artifacts.lifecycle_scope('review')['lineages'][0]['head_sha256'])

    def test_corrupt_body_does_not_hold_metadata_and_windows_cleanup_leaves_no_files(self):
        case=self.context();audit=self.reserve(case)
        packet_path=case.artifacts._object_path('packet',audit['scope']['packet_id'])
        packet_path.write_bytes(b'BROKEN_PACKET')
        with patch.object(case.artifacts,'_read_object',side_effect=AssertionError('metadata opened object')):
            catalog=case.service.catalog_view();retained=case.service.retained_view('review')
            preview=case.service.preview('archive','review')
        self.assertFalse(next(row for row in catalog['channels'] if row['name']=='review')['artifacts_held'])
        self.assertFalse(retained['artifacts_held']);self.assertEqual(preview['counts']['artifacts'],1)
        self.assertEqual(packet_path.read_bytes(),b'BROKEN_PACKET')
        self.assertEqual(list(case.root.rglob('*.tmp')),[])
        root=case.root;case.doCleanups();self.assertFalse(root.exists())

    def test_retained_authored_rows_stop_at_100_without_reading_bodies(self):
        case=self.context()
        for _ in range(101):self.reserve(case,terminal=True)
        with patch.object(case.artifacts,'_read_object',side_effect=AssertionError('retained read body')):
            retained=case.service.retained_view('review')
        self.assertEqual(retained['counts']['artifacts'],101)
        self.assertEqual(retained['counts']['artifact_requests'],101)
        self.assertEqual(len(retained['artifacts']),100)
        self.assertTrue(retained['truncated']['artifacts'])
        self.assertNotIn('launch_nonce',str(retained))
        self.assertEqual(list(case.root.rglob('*.tmp')),[])


    def test_mixed_queue_failure_keeps_saved_artifact_cancellation_visible(self):
        case=self.context();audit=case.prepare()
        chat=case.trigger.queue.enqueue(case.instance,{'channel':'review','text':'ordinary queued chat'})
        preview=case.service.preview('cancel_queued','review')
        with patch.object(case.trigger.queue,'cancel_queued_channel',side_effect=OSError('private ledger fault')):
            with self.assertRaises(ChannelUnavailable) as caught:
                case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
                    confirmation='review',preview_token=preview['preview_token'])
        self.assertEqual(caught.exception.code,'artifact_cancellation_partial')
        summary=caught.exception.payload['artifact_cancellation']
        self.assertEqual(summary['cancelled_request_ids'],[audit['request_id']])
        self.assertEqual(summary['fenced_dispatch_ids'],[audit['dispatch_id']])
        self.assertEqual(summary['unconfirmed_dispatch_ids'],[chat['envelope']['dispatch_id']])
        self.assertEqual(case.trigger.queue.owned(case.instance,chat['envelope']['dispatch_id'])['state'],'queued')
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')

    def test_request_persist_failure_never_claims_a_saved_cancellation(self):
        from artifact_store import ArtifactUnavailable
        case=self.context();audit=case.prepare()
        preview=case.service.preview('cancel_queued','review');before=case.files()
        with patch.object(case.artifacts,'set_attempt_state',side_effect=ArtifactUnavailable('private')):
            with self.assertRaises(ChannelUnavailable) as caught:
                case.service.apply('cancel_queued','review',request_id=uuid.uuid4().hex,
                    confirmation='review',preview_token=preview['preview_token'])
        self.assertEqual(caught.exception.code,'artifact_cancellation_unavailable')
        self.assertEqual(case.files(),before)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'queued')


    def test_explicitly_omitted_owner_preserves_legacy_catalog_and_retained_shape(self):
        from copy import deepcopy
        case=self.context();configured=case.artifacts
        case.service.authored_artifacts=None
        legacy_catalog=case.service.catalog_view();legacy_retained=case.service.retained_view('review')
        expected={'messages','todos','jobs','schedules','sessions','summaries','uploads','queue'}
        self.assertEqual(set(legacy_catalog['channels'][0]['counts']),expected)
        self.assertNotIn('artifacts',legacy_retained)
        self.assertEqual(set(legacy_retained),{'channel','state','counts','truncated','errors',
            'jobs','sessions','schedules','uploads','summary'})
        case.service.authored_artifacts=configured
        newer=case.service.catalog_view();retained=case.service.retained_view('review')
        artifact_keys={'artifacts','artifact_versions','artifact_requests','artifact_source_bytes'}
        for row in newer['channels']:
            self.assertFalse(row['artifacts_held']);self.assertFalse(row['artifact_source_retained'])
            self.assertIsNone(row['artifact_source_disclosure'])
            self.assertTrue(all(row['counts'][key]==0 for key in artifact_keys))
        stripped=deepcopy(newer)
        for row in stripped['channels']:
            for key in artifact_keys:row['counts'].pop(key)
            for key in ('artifacts_held','artifact_source_retained','artifact_source_disclosure'):row.pop(key)
        self.assertEqual(stripped,legacy_catalog)
        for key in ('artifacts','artifacts_held','artifact_source_retained','artifact_source_disclosure'):retained.pop(key)
        for key in artifact_keys:retained['counts'].pop(key)
        retained['truncated'].pop('artifacts')
        self.assertEqual(retained,legacy_retained)
        self.assertFalse(configured.path.exists())


if __name__=='__main__':unittest.main()
