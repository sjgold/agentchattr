"""Actual lifecycle integration reds; owned fixture roots and controlled managed births."""
import json
import unittest
from unittest.mock import patch
import uuid
from channel_lifecycle import ChannelConflict, ChannelStore, ChannelUnavailable
from tests import test_artifact_admission as fixture

OLD_STEPS=('messages','jobs','schedules','summaries','sessions','cursors','settings')

class ArtifactLifecycleTests(unittest.TestCase):
    def context(self):
        case=fixture.ArtifactAdmissionTests()
        self.addCleanup(case.doCleanups)
        case.setUp();case.setup_authority()
        # Explicit test-owned future owner binding, not a configured factory claim.
        case.service.authored_artifacts=case.artifacts
        case.service.artifact_service_getter=lambda:case.authority
        return case

    def old_intent(self,case,*,finished=False):
        request=uuid.uuid4().hex
        # Real catalog writer under the OLD tuple; current loader must accept
        # exactly that prefix after the tuple grows. No product file changes.
        with patch('channel_lifecycle.RENAME_STEPS',OLD_STEPS):
            case.catalog.begin('rename','review','renamed',request_id=request,
                expected_revision=case.catalog.snapshot()['revision'])
            for step in OLD_STEPS:
                case.catalog.complete_step(request,step)
            if finished:
                case.catalog.finish(request)
        return request

    def test_prepared_and_queued_requests_block_lifecycle_with_exact_artifact_ids(self):
        for phase in ('prepared','queued'):
            for operation in ('archive','rename','delete'):
                with self.subTest(phase=phase,operation=operation):
                    case=self.context()
                    audit,packet=case.new_request()
                    if phase=='prepared':
                        case.artifacts.reserve_request(audit,audit['request_id'])
                    else:
                        case.authority.prepare_request(audit,packet,audit['request_id'])
                    options={'new_name':'renamed'} if operation=='rename' else {}
                    preview=case.service.preview(operation,'review',**options)
                    before=case.files()
                    with self.assertRaises(ChannelConflict):
                        case.service.apply(operation,'review',request_id=uuid.uuid4().hex,
                            confirmation='review',preview_token=preview['preview_token'],**options)
                    self.assertEqual(case.files(),before)
                    blockers=[row for row in preview['blockers'] if row['kind']=='artifact']
                    self.assertEqual(len(blockers),1)
                    self.assertEqual(blockers[0]['request_id'],audit['request_id'])
                    self.assertEqual(blockers[0]['dispatch_id'],audit['dispatch_id'])
                    self.assertEqual(blockers[0]['request_state'],phase)
                    self.assertFalse(blockers[0]['held'])

    def test_old_seven_name_marks_resume_only_artifacts(self):
        case=self.context();audit,packet=case.new_request()
        case.artifacts.reserve_request(audit,audit['request_id'])
        case.artifacts.set_attempt_state(audit['request_id'],audit['attempt_id'],'prepared',
            {'state':'failed','reason':'generation_failed'})
        before=case.artifacts.get_request(audit['request_id'])['audit']
        request=self.old_intent(case)
        # A fresh actual catalog owner reads what the old writer persisted.
        case.service.catalog=ChannelStore(case.catalog.path)
        with patch.object(case.artifacts,'rename_channel',wraps=case.artifacts.rename_channel) as move:
            result=case.service.retry(request)
        move.assert_called_once_with('review','renamed')
        self.assertTrue(result['ok'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['channel'],'renamed')
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['audit'],before)
        self.assertIsNone(case.service.catalog.snapshot()['intent'])

    def test_finished_operation_without_intent_never_runs_artifact_step(self):
        case=self.context();request=self.old_intent(case,finished=True)
        with patch.object(case.artifacts,'rename_channel',side_effect=AssertionError('Finished move repeated')):
            with self.assertRaises(ChannelConflict):
                case.service.retry(request)
        self.assertIsNone(case.catalog.snapshot()['intent'])

    def test_out_of_order_or_foreign_old_marks_refuse_fresh_load(self):
        for marks in (['jobs','messages'],['messages','foreign']):
            with self.subTest(marks=marks):
                case=self.context();self.old_intent(case)
                value=json.loads(case.catalog.path.read_text(encoding='utf-8'))
                value['intent']['completed_steps']=marks
                case.catalog.path.write_text(json.dumps(value),encoding='utf-8')
                with self.assertRaises(ChannelUnavailable):
                    ChannelStore(case.catalog.path).snapshot()

    def test_terminal_and_missing_transport_joins_are_metadata_only(self):
        for scenario in ('terminal_queued','active_missing','terminal_missing'):
            with self.subTest(scenario=scenario):
                case=self.context();audit,packet=case.new_request()
                if scenario=='terminal_missing':
                    case.artifacts.reserve_request(audit,audit['request_id'])
                    case.artifacts.set_attempt_state(audit['request_id'],audit['attempt_id'],'prepared',
                        {'state':'failed','reason':'generation_failed'})
                else:
                    case.authority.prepare_request(audit,packet,audit['request_id'])
                    if scenario=='terminal_queued':
                        with patch.object(case.authority,'_fence',side_effect=OSError('Controlled fence failure')):
                            case.authority.cancel_request(audit['request_id'])
                    else:
                        case.claim(audit)
                        case.authority.get_brief(audit['brief_id'],case.instance)
                        raw=case.trigger.queue._queue
                        ledger=json.loads(raw.path.read_text(encoding='utf-8'))
                        ledger['records']=[]  # Explicit retained-ledger loss fixture, no worker-exit claim.
                        raw.path.write_text(json.dumps(ledger),encoding='utf-8')
                with patch.object(case.artifacts,'get_packet',side_effect=AssertionError('Packet body read in scope')):
                    preview=case.service.preview('archive','review')
                rows=[row for row in preview['blockers'] if row['kind']=='artifact']
                if scenario=='terminal_missing':
                    self.assertEqual(rows,[])
                    continue
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['request_id'],audit['request_id'])
                self.assertEqual(rows[0]['transport_state'],'queued' if scenario=='terminal_queued' else None)
                self.assertEqual(rows[0]['request_state'],'cancelled' if scenario=='terminal_queued' else 'active')
                self.assertEqual(rows[0]['reason'],'transport_pending' if scenario=='terminal_queued' else 'transport_missing')
                self.assertEqual(rows[0]['held'],scenario=='active_missing')

    def test_unreadable_authored_index_refuses_mutation_preview(self):
        case=self.context();audit,packet=case.new_request()
        case.artifacts.reserve_request(audit,audit['request_id'])
        case.artifacts.path.write_bytes(b'BROKEN_INDEX')
        with self.assertRaises(ChannelUnavailable):
            case.service.preview('archive','review')
        self.assertEqual(case.artifacts.path.read_bytes(),b'BROKEN_INDEX')

    def test_unknown_rename_step_does_not_fall_through_to_settings(self):
        import channel_lifecycle
        import channel_service
        case=self.context();request=self.old_intent(case)
        extended=channel_lifecycle.RENAME_STEPS+('unsupported_future_step',)
        with patch.object(channel_lifecycle,'RENAME_STEPS',extended), \
                patch.object(channel_service,'RENAME_STEPS',extended):
            with self.assertRaises(ChannelConflict):
                case.service.retry(request)

if __name__=='__main__':unittest.main()
