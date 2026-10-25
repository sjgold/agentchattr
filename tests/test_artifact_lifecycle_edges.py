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
        self.assertEqual(case.artifacts.get_request(first)['state'],'active')
        self.assertEqual(case.artifacts.get_request(selected[1]['request_id'])['state'],'queued')


if __name__=='__main__':unittest.main()
