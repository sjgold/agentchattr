"""Operator projection repair through the real service, no UI/native claims."""
from copy import deepcopy
import json
import unittest
import uuid
from unittest.mock import patch

from channel_lifecycle import ChannelConflict, ChannelUnavailable
from tests import test_channel_projections as fixture


class ChannelProjectionRepairTests(unittest.TestCase):
    start = fixture.ChannelProjectionTests.start
    pending_final = fixture.ChannelProjectionTests.pending_final
    bind = fixture.ChannelProjectionTests.bind

    def setUp(self):
        fixture.ChannelProjectionTests.setUp(self)
        self.bind()

    def apply(self, op):
        preview = self.service.preview(op, 'review')
        return self.service.apply(op, 'review', request_id=uuid.uuid4().hex,
            confirmation='review', preview_token=preview['preview_token'])

    def test_active_operator_repair_projects_exact_scope_without_dispatch(self):
        run, _ = self.pending_final()
        before = self.trigger.queue.path.read_bytes()
        result = self.apply('recover_projections')
        self.assertTrue(result['ok'])
        report = result['projection_repair']
        self.assertEqual(report['messages_projected'], 1)
        self.assertEqual(report['skips_projected'], 0)
        self.assertEqual(report['continuations_projected'], 0)
        self.assertEqual(report['sessions'], [{'session_id': run['id'], 'run_id': run['run_id']}])
        self.assertNotIn('Pending exact result', json.dumps(report))
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        self.assertIsNotNone(self.sessions.get(run['id'])['admitted_events'][0]['projected_message_id'])

    def test_reopen_repairs_completed_pending_history_through_service(self):
        run, _ = self.pending_final()
        self.catalog.set_state('review', 'archived', expected_revision=0)
        result = self.apply('reopen')
        self.assertEqual(result['state'], 'active')
        self.assertEqual(result['projection_repair']['messages_projected'], 1)
        self.assertIsNotNone(self.sessions.get(run['id'])['admitted_events'][0]['projected_message_id'])

    def test_reopen_projection_error_keeps_committed_active_state_and_offers_repair(self):
        run, _ = self.pending_final()
        self.catalog.set_state('review', 'archived', expected_revision=0)
        with patch.object(self.messages, 'add_once', side_effect=OSError('private storage details')):
            result = self.apply('reopen')
        self.assertTrue(result['ok'])
        self.assertEqual(result['state'], 'active')
        self.assertIn('projection_repair_error', result)
        self.assertNotIn('private', json.dumps(result))
        self.assertEqual(self.catalog.snapshot()['channels']['review'], 'active')
        self.assertIn('review', self.settings['channels'])
        self.assertIsNone(self.sessions.get(run['id'])['admitted_events'][0]['projected_message_id'])
        self.assertEqual(self.apply('recover_projections')['projection_repair']['messages_projected'], 1)

    def test_active_repair_io_failure_is_generic_and_retry_keeps_journal_identity(self):
        run, _ = self.pending_final()
        journal = deepcopy(self.sessions.get(run['id']))
        with patch.object(self.messages, 'add_once', side_effect=OSError('private details')):
            with self.assertRaises(ChannelUnavailable) as failure:
                self.apply('recover_projections')
        self.assertNotIn('private', str(failure.exception))
        self.assertEqual(self.sessions.get(run['id']), journal)
        self.assertEqual(self.apply('recover_projections')['projection_repair']['messages_projected'], 1)

    def test_scoped_recovery_validates_names_and_is_noop_when_nothing_pending(self):
        before = self.path.read_bytes()
        with patch.object(self.engine, '_project_session') as project:
            result = self.engine.recover_projections(channel='peer')
            self.assertEqual(result, {'messages_projected': 0, 'skips_projected': 0,
                'continuations_projected': 0, 'sessions': []})
            with self.assertRaises(ValueError):
                self.engine.recover_projections(channel='Bad/name')
        project.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)

    def test_scoped_repair_leaves_other_channels_pending_and_never_dispatches(self):
        run, _ = self.pending_final()
        general = self.sessions.get(self.session_id)
        with patch.object(self.engine, '_project_session'):
            self.engine.admit_event(general['active_invocation']['brief_id'], 'question', 'Peer pending', self.owner)
        peer = deepcopy(self.sessions.get(self.session_id))
        with patch.object(self.engine, '_trigger_current') as trigger:
            self.apply('recover_projections')
        trigger.assert_not_called()
        self.assertEqual(self.sessions.get(self.session_id), peer)
        self.assertIsNotNone(self.sessions.get(run['id'])['admitted_events'][0]['projected_message_id'])

    def test_live_pending_projection_is_explicitly_nonrepairable(self):
        run = self.engine.start_session('review', 'review', {'reviewer': 'claude', 'editor': 'codex'}, 'operator')
        with patch.object(self.engine, '_project_session'):
            self.engine.admit_event(run['active_invocation']['brief_id'], 'final', 'Live pending', self.peer)
        before = self.path.read_bytes()
        pending = [item for item in self.service.preview('delete', 'review')['blockers']
                   if item['kind'] == 'projection_pending']
        self.assertEqual(pending[0]['reason'], 'live_projection_requires_restart')
        with self.assertRaises(ChannelConflict):
            self.apply('recover_projections')
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_projection_like_fields_never_create_unrepairable_blocker(self):
        run, _ = self.pending_final()
        self.sessions._event_update(run['id'], lambda value: value.update(completion_protocol=0))
        self.assertFalse(self.engine._enrich(self.sessions.get(run['id']))['projection_pending'])
        self.assertFalse(any(item['kind'] == 'projection_pending'
            for item in self.service.preview('archive', 'review')['blockers']))

    def test_persisted_pending_skip_counts_as_blocker_and_repairs_once(self):
        run, invocation = self.pending_final()
        # Persisted crash-state fixture, not a claim of skip authorization.
        skipped = dict(projection_id=uuid.uuid4().hex, projected_message_id=None,
            request_id=uuid.uuid4().hex, submitted_by='operator',
            **{key: invocation[key] for key in ('turn_id', 'run_id', 'input_revision', 'attempt_id')},
            dispatch_id=invocation['dispatch_id'], seat_identity_id=self.peer['identity_id'],
            role='reviewer', agent_name='claude', reason='Missing work', phase=0, turn=0,
            is_output=True, skipped_at=1)
        self.sessions._event_update(run['id'], lambda value: value.update(admitted_events=[],
            skipped_turns=[skipped], missing_output=True))
        self.assertTrue(self.engine._enrich(self.sessions.get(run['id']))['projection_pending'])
        pending = [item for item in self.service.preview('archive', 'review')['blockers']
                   if item['kind'] == 'projection_pending']
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['dispatch_id'], invocation['dispatch_id'])
        report = self.apply('recover_projections')['projection_repair']
        self.assertEqual((report['messages_projected'], report['skips_projected']), (0, 1))
        self.assertEqual(len([row for row in self.messages.get_recent(channel='review') if row['type'] == 'session_skip']), 1)

    def test_missing_question_reference_stays_visible_and_cannot_be_silently_repaired(self):
        run, _ = self.pending_final()
        self.sessions._event_update(run['id'], lambda value: value.update(admitted_events=[],
            continuation_context=[{'question_event_id': uuid.uuid4().hex, 'answer': 'Orphaned answer',
                                   'projected_message_id': None}]))
        pending = [item for item in self.service.preview('delete', 'review')['blockers']
                   if item['kind'] == 'projection_pending']
        self.assertEqual(pending[0]['reason'], 'missing_question_event')
        with self.assertRaises(ChannelConflict):
            self.apply('recover_projections')
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_repair_requires_current_token_and_typed_confirmation(self):
        self.pending_final()
        preview = self.service.preview('recover_projections', 'review')
        before = self.path.read_bytes()
        for confirmation, token in (('wrong', preview['preview_token']), ('review', 'stale')):
            with self.assertRaises(ChannelConflict):
                self.service.apply('recover_projections', 'review', request_id=uuid.uuid4().hex,
                    confirmation=confirmation, preview_token=token)
            self.assertEqual(self.path.read_bytes(), before)

    def test_interrupted_continuation_repairs_as_chat_without_next_turn(self):
        run, invocation = self.start()
        question = self.engine.admit_event(invocation['brief_id'], 'question', 'Which source?', self.peer)
        self.sessions.continue_question(run['id'], question['event_id'], 'Preserved answer')
        self.sessions._event_update(run['id'], lambda value: value.update(state='interrupted'))
        with patch.object(self.engine, '_trigger_current') as trigger:
            report = self.apply('recover_projections')['projection_repair']
        trigger.assert_not_called()
        self.assertEqual((report['messages_projected'], report['continuations_projected']), (0, 1))


if __name__ == '__main__':
    unittest.main()
