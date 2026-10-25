"""Final slice4 edge regressions; owned temp owners and controlled failures."""
import json
import unittest
from unittest.mock import patch
import uuid

from artifact_store import ArtifactUnavailable
from channel_lifecycle import ChannelConflict, ChannelUnavailable
from launcher import LaunchError
from tests import test_artifact_lifecycle_review as review
from tests import test_artifact_lifecycle_metadata as metadata


class ArtifactLifecycleEdgeTests(unittest.TestCase):
    context=review.ArtifactLifecycleReviewTests.context
    apply_cancel=review.ArtifactLifecycleReviewTests.apply_cancel

    def test_ordinary_cancel_lock_timeout_has_typed_http_503_including_backstop(self):
        for target in ('queue','backstop'):
            with self.subTest(target=target):
                case=self.context();case.trigger.queue.enqueue(case.instance,{'channel':'review','text':'ordinary'})
                preview=case.service.preview('cancel_queued','review')
                body={'op':'cancel_queued','channel':'review','request_id':uuid.uuid4().hex,
                      'confirmation':'review','preview_token':preview['preview_token']}
                owner,method=(case.trigger.queue,'cancel_queued_channel') if target=='queue' else (case.service,'apply')
                before=case.files()
                with patch.object(owner,method,side_effect=LaunchError('PRIVATE_LOCK')):
                    response,broadcasts=metadata.ArtifactLifecycleMetadataTests.http(case,'apply',body)
                self.assertEqual(response.status_code,503)
                self.assertEqual(json.loads(response.body),{'code':'artifact_cancellation_unavailable',
                    'error':'Artifact cancellation is unavailable. No queued work was changed.'})
                self.assertEqual(broadcasts,0);self.assertEqual(case.files(),before)

    def test_unreadable_handler_lookup_preserves_prior_effects_and_marks_unknown_rows(self):
        for error in (ChannelConflict,OSError):
            with self.subTest(error=error.__name__):
                case=self.context();case.prepare();case.prepare();case.prepare()
                preview=case.service.preview('cancel_queued','review')
                selected=[row for row in preview['blockers'] if row['kind']=='artifact']
                second=selected[1]['request_id'];failed=[False]
                get=case.artifacts.get_request;cancel=case.authority.cancel_request
                def unknown(identifier):
                    if failed[0]:raise ArtifactUnavailable('PRIVATE_INDEX')
                    return get(identifier)
                def fail_second(identifier):
                    if identifier==second:
                        failed[0]=True;raise error('PRIVATE_CANCEL')
                    return cancel(identifier)
                with patch.object(case.artifacts,'get_request',side_effect=unknown), \
                        patch.object(case.authority,'cancel_request',side_effect=fail_second):
                    with self.assertRaises(ChannelUnavailable) as caught:self.apply_cancel(case,preview)
                self.assertEqual(caught.exception.code,'artifact_cancellation_partial')
                payload=caught.exception.payload
                self.assertEqual(payload['unverified_request_ids'],[row['request_id'] for row in selected[1:]])
                self.assertEqual(payload['artifact_cancellation'],{
                    'cancelled_request_ids':[selected[0]['request_id']],
                    'fenced_dispatch_ids':[selected[0]['dispatch_id']],'unconfirmed_dispatch_ids':[]})
                self.assertNotIn('PRIVATE',str(payload))
                self.assertEqual(get(selected[0]['request_id'])['state'],'cancelled')
                self.assertEqual(get(second)['state'],'queued')

    def test_omitted_owner_keeps_legacy_nonhex_artifact_queue_ids_and_cancellation(self):
        case=self.context();case.prepare();raw=case.trigger.queue._queue
        value=json.loads(raw.path.read_text(encoding='utf-8'))
        value['records'][0]['envelope']['dispatch_id']='legacy-artifact-id'
        raw.path.write_text(json.dumps(value),encoding='utf-8')
        case.service.authored_artifacts=None
        preview=case.service.preview('cancel_queued','review')
        self.assertEqual(preview['queued_dispatch_ids'],['legacy-artifact-id'])
        self.assertTrue(self.apply_cancel(case,preview)['ok'])
        self.assertEqual(case.trigger.queue.owned(case.instance,'legacy-artifact-id')['state'],'cancelled')

    def test_queued_predicate_is_reasserted_at_each_mutation(self):
        case=self.context();case.prepare();case.prepare()
        preview=case.service.preview('cancel_queued','review')
        selected=[row for row in preview['blockers'] if row['kind']=='artifact'];first=selected[0]['request_id']
        validate=case.authority.validate_queued_cancellation;calls=[]
        def activated_after_prevalidation(identifier):
            result=validate(identifier);calls.append(identifier)
            if len(calls)==len(selected):
                row=case.artifacts.get_request(first)
                case.artifacts.set_attempt_state(first,row['audit']['attempt_id'],'queued',{'state':'active','reason':None})
            return result
        with patch.object(case.authority,'validate_queued_cancellation',side_effect=activated_after_prevalidation):
            with self.assertRaises(ChannelConflict) as caught:self.apply_cancel(case,preview)
        self.assertEqual(caught.exception.code,'artifact_cancellation_refused')
        self.assertEqual(caught.exception.payload['artifact_cancellation'],{
            'cancelled_request_ids':[],'fenced_dispatch_ids':[],'unconfirmed_dispatch_ids':[]})
        self.assertEqual(case.trigger.queue.owned(case.instance,selected[0]['dispatch_id'])['state'],'queued')
        self.assertEqual(case.artifacts.get_request(first)['state'],'active')
        self.assertEqual(case.artifacts.get_request(selected[1]['request_id'])['state'],'queued')


    def test_saved_fenced_and_saved_unconfirmed_rows_survive_a_later_refusal(self):
        for fenced in (True,False):
            with self.subTest(fenced=fenced):
                case=self.context();case.prepare();case.prepare()
                preview=case.service.preview('cancel_queued','review')
                rows=[row for row in preview['blockers'] if row['kind']=='artifact']
                first,second=rows;cancel=case.authority.cancel_request;fence=case.authority._fence
                def refuse(identifier):
                    if identifier==second['request_id']:raise ChannelConflict('PRIVATE_REFUSAL')
                    return cancel(identifier)
                def maybe_fence(row):
                    if not fenced and row['audit']['request_id']==first['request_id']:raise OSError('PRIVATE_FENCE')
                    return fence(row)
                with patch.object(case.authority,'cancel_request',side_effect=refuse), \
                        patch.object(case.authority,'_fence',side_effect=maybe_fence):
                    with self.assertRaises(ChannelConflict) as caught:self.apply_cancel(case,preview)
                payload=caught.exception.payload
                self.assertEqual(caught.exception.code,'artifact_cancellation_refused')
                self.assertEqual(payload['artifact_cancellation'],{
                    'cancelled_request_ids':[first['request_id']],
                    'fenced_dispatch_ids':[first['dispatch_id']] if fenced else [],
                    'unconfirmed_dispatch_ids':[] if fenced else [first['dispatch_id']]})
                self.assertEqual(payload['refused_request_ids'],[second['request_id']])
                self.assertEqual(case.artifacts.get_request(second['request_id'])['state'],'queued')

    def test_unknown_effect_wire_and_launch_backstop_are_safe_over_legacy_ws(self):
        import asyncio
        import app
        from channel_service import ArtifactCancellationPartial
        from unittest.mock import AsyncMock
        case=self.context()
        summary={'cancelled_request_ids':['a'*32],'fenced_dispatch_ids':['b'*32],'unconfirmed_dispatch_ids':[]}
        error=ArtifactCancellationPartial({'op':'cancel_queued','channel':'review','state':'active','revision':0,
            'artifact_cancellation':summary,'unverified_request_ids':['c'*32,'d'*32]})
        body={'op':'cancel_queued','channel':'review','request_id':uuid.uuid4().hex,'confirmation':'review','preview_token':'unused'}
        with patch.object(case.service,'apply',side_effect=error):
            response,broadcasts=metadata.ArtifactLifecycleMetadataTests.http(case,'apply',body)
        self.assertEqual(response.status_code,503);self.assertEqual(broadcasts,0)
        self.assertEqual(json.loads(response.body)['unverified_request_ids'],['c'*32,'d'*32])
        for failure,code in ((error,'artifact_cancellation_partial'),(LaunchError('PRIVATE_LOCK'),'artifact_cancellation_unavailable')):
            ws=AsyncMock();event={'type':'channel_cancel_queued','name':'review',**{key:body[key] for key in ('request_id','confirmation','preview_token')}}
            with patch.object(app,'_channels',return_value=case.service),patch.object(case.service,'apply',side_effect=failure), \
                    patch.object(app,'_broadcast_channel_projection',AsyncMock()) as broadcast:
                asyncio.run(app._legacy_channel_action(ws,event))
            payload=json.loads(ws.send_text.call_args.args[0])
            self.assertEqual((payload['code'],payload['error_code']),(503,code));broadcast.assert_not_called()
            self.assertNotIn('PRIVATE',str(payload))
            if code=='artifact_cancellation_partial':self.assertEqual(payload['unverified_request_ids'],['c'*32,'d'*32])


    def test_exact_neutral_and_delete_held_disclosures(self):
        neutral='Authored artifact contents cannot be confirmed; repair saved artifact metadata before changing channels.'
        deletion='Authored artifact contents cannot be confirmed; repair saved artifact metadata before deleting.'
        for op in ('create','reopen','archive','rename','delete'):
            with self.subTest(op=op):
                case=self.context()
                if op=='reopen':case.catalog.set_state('review','archived',expected_revision=case.catalog.snapshot()['revision'])
                case.artifacts.path.parent.mkdir(parents=True,exist_ok=True);case.artifacts.path.write_bytes(b'HELD')
                self.assertEqual(case.service.retained_view('review')['artifact_source_disclosure'],neutral)
                for row in case.service.catalog_view()['channels']:
                    if row['state']!='unregistered':self.assertEqual(row['artifact_source_disclosure'],neutral)
                options={'new_name':'renamed'} if op=='rename' else {}
                with self.assertRaises(ChannelUnavailable) as caught:
                    case.service.preview(op,'new-channel' if op=='create' else 'review',**options)
                self.assertEqual(caught.exception.payload['artifact_source_disclosure'],deletion if op=='delete' else neutral)

    def test_later_row_activation_refuses_after_only_the_earlier_row_is_saved(self):
        case=self.context();case.prepare();case.prepare()
        preview=case.service.preview('cancel_queued','review')
        rows=[row for row in preview['blockers'] if row['kind']=='artifact'];first,later=rows
        validate=case.authority.validate_queued_cancellation;calls=[]
        def activated_after_prevalidation(identifier):
            result=validate(identifier);calls.append(identifier)
            if len(calls)==len(rows):
                row=case.artifacts.get_request(later['request_id'])
                case.artifacts.set_attempt_state(later['request_id'],row['audit']['attempt_id'],'queued',{'state':'active','reason':None})
            return result
        with patch.object(case.authority,'validate_queued_cancellation',side_effect=activated_after_prevalidation):
            with self.assertRaises(ChannelConflict) as caught:self.apply_cancel(case,preview)
        self.assertEqual(caught.exception.code,'artifact_cancellation_refused')
        self.assertEqual(caught.exception.payload['artifact_cancellation'],{
            'cancelled_request_ids':[first['request_id']],'fenced_dispatch_ids':[first['dispatch_id']],
            'unconfirmed_dispatch_ids':[]})
        self.assertEqual(caught.exception.payload['refused_request_ids'],[later['request_id']])
        self.assertEqual(case.trigger.queue.owned(case.instance,first['dispatch_id'])['state'],'cancelled')
        self.assertEqual(case.trigger.queue.owned(case.instance,later['dispatch_id'])['state'],'queued')
        self.assertEqual(case.artifacts.get_request(later['request_id'])['state'],'active')

    def test_real_handler_lookup_failure_reaches_http_body_and_ws_frame(self):
        import asyncio
        import app
        from unittest.mock import AsyncMock
        for transport in ('http','ws'):
            with self.subTest(transport=transport):
                case=self.context();case.prepare();case.prepare();case.prepare()
                preview=case.service.preview('cancel_queued','review')
                rows=[row for row in preview['blockers'] if row['kind']=='artifact'];first=rows[0];second=rows[1]
                failed=[False];get=case.artifacts.get_request;cancel=case.authority.cancel_request
                def unreadable(identifier):
                    if failed[0]:raise ArtifactUnavailable('PRIVATE_INDEX')
                    return get(identifier)
                def fail_second(identifier):
                    if identifier==second['request_id']:
                        failed[0]=True;raise OSError('PRIVATE_CANCEL')
                    return cancel(identifier)
                body={'op':'cancel_queued','channel':'review','request_id':uuid.uuid4().hex,
                    'confirmation':'review','preview_token':preview['preview_token']}
                with patch.object(case.artifacts,'get_request',side_effect=unreadable), \
                        patch.object(case.authority,'cancel_request',side_effect=fail_second):
                    if transport=='http':
                        response,broadcasts=metadata.ArtifactLifecycleMetadataTests.http(case,'apply',body)
                        self.assertEqual(response.status_code,503);self.assertEqual(broadcasts,0)
                        payload=json.loads(response.body)
                    else:
                        ws=AsyncMock();event={'type':'channel_cancel_queued','name':'review',
                            **{key:body[key] for key in ('request_id','confirmation','preview_token')}}
                        with patch.object(app,'_channels',return_value=case.service), \
                                patch.object(app,'_broadcast_channel_projection',AsyncMock()) as broadcast:
                            asyncio.run(app._legacy_channel_action(ws,event))
                        payload=json.loads(ws.send_text.call_args.args[0]);broadcast.assert_not_called()
                        self.assertEqual(payload['code'],503)
                self.assertEqual(payload['code' if transport=='http' else 'error_code'],'artifact_cancellation_partial')
                self.assertEqual(payload['unverified_request_ids'],[row['request_id'] for row in rows[1:]])
                self.assertEqual(payload['artifact_cancellation'],{
                    'cancelled_request_ids':[first['request_id']],'fenced_dispatch_ids':[first['dispatch_id']],
                    'unconfirmed_dispatch_ids':[]})
                self.assertNotIn('PRIVATE',str(payload))
                self.assertEqual(get(first['request_id'])['state'],'cancelled')
                self.assertEqual(get(second['request_id'])['state'],'queued')

    def test_first_row_unknown_is_partial_even_with_no_known_effects(self):
        case=self.context();case.prepare();case.prepare()
        preview=case.service.preview('cancel_queued','review');rows=[row for row in preview['blockers'] if row['kind']=='artifact']
        failed=[False];get=case.artifacts.get_request;cancel=case.authority.cancel_request
        def unknown(identifier):
            if failed[0]:raise ArtifactUnavailable('PRIVATE_INDEX')
            return get(identifier)
        def save_then_lose_return(identifier):
            cancel(identifier);failed[0]=True;raise OSError('PRIVATE_RETURN')
        with patch.object(case.artifacts,'get_request',side_effect=unknown), \
                patch.object(case.authority,'cancel_request',side_effect=save_then_lose_return):
            with self.assertRaises(ChannelUnavailable) as caught:self.apply_cancel(case,preview)
        self.assertEqual(caught.exception.code,'artifact_cancellation_partial')
        self.assertEqual(caught.exception.payload['artifact_cancellation'],{
            'cancelled_request_ids':[],'fenced_dispatch_ids':[],'unconfirmed_dispatch_ids':[]})
        self.assertEqual(caught.exception.payload['unverified_request_ids'],[row['request_id'] for row in rows])
        self.assertEqual(get(rows[0]['request_id'])['state'],'cancelled')
        self.assertEqual(get(rows[1]['request_id'])['state'],'queued')


if __name__=='__main__':unittest.main()
