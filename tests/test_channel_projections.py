"""Journal/projection lifecycle boundaries, real stores without native transport."""
from copy import deepcopy
import unittest
import uuid
from unittest.mock import patch

from channel_lifecycle import ChannelConflict, ChannelUnavailable
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict
from tests import test_channel_service as fixture


class ChannelProjectionTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelServiceTests.setUp(self)
        self.sessions.save_custom_template({'id': 'single', 'name': 'Single', 'roles': ['reviewer'],
            'phases': [{'name': 'Review', 'participants': ['reviewer'], 'prompt': 'Review.', 'is_output': True}]})

    def start(self):
        run = self.engine.start_session('single', 'review', {'reviewer': 'claude'}, 'operator', input_text='Exact source')
        invocation = run['active_invocation']
        record = self.trigger.queue.claim(self.peer, 'fixture-consumer')
        self.assertEqual(record['envelope']['dispatch_id'], invocation['dispatch_id'])
        self.trigger.queue.acknowledge(self.peer, invocation['dispatch_id'], 'fixture-consumer')
        self.trigger.queue.release(self.peer, invocation['dispatch_id'], 'fixture-consumer')
        return run, invocation

    def bind(self):
        self.engine.bind_channel_policy(lambda: self.service)
        self.messages.bind_channel_policy(lambda: self.service)

    def pending_final(self):
        run, invocation = self.start()
        with patch.object(self.engine, '_project_session'):
            self.engine.admit_event(invocation['brief_id'], 'final', 'Pending exact result', self.peer)
        return run, invocation

    def test_late_archived_final_is_admitted_but_projects_only_after_reopen(self):
        run, invocation = self.start()
        self.bind()
        # Simulate a state change predating the late typed event. Normal archive
        # refuses a live run; this is an admission/projection recovery seam.
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.messages._path.read_bytes() if self.messages._path.exists() else None
        result = self.engine.admit_event(invocation['brief_id'], 'final', 'Retained exact\r\nresult', self.peer)
        self.assertEqual(result['status'], 'admitted')
        saved = self.sessions.get(run['id'])
        self.assertEqual(saved['state'], 'complete')
        self.assertEqual(saved['admitted_events'][0]['content'], 'Retained exact\r\nresult')
        self.assertIsNone(saved['admitted_events'][0]['projected_message_id'])
        self.assertEqual(self.messages._path.read_bytes() if self.messages._path.exists() else None, before)
        self.engine.recover_projections()
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        self.catalog.set_state('review', 'active', expected_revision=1)
        self.engine.recover_projections()
        self.engine.recover_projections()
        projected = self.messages.get_recent(channel='review')
        self.assertEqual([row['type'] for row in projected], ['session_result', 'session_end'])
        self.assertEqual(projected[0]['text'], 'Retained exact\r\nresult')

    def test_deleted_complete_history_does_not_resurrect_after_reload(self):
        run, invocation = self.start()
        self.engine.admit_event(invocation['brief_id'], 'final', 'Already projected', self.peer)
        self.assertEqual(self.sessions.get(run['id'])['state'], 'complete')
        self.bind()
        preview = self.service.preview('delete', 'review')
        self.service.apply('delete', 'review', request_id=uuid.uuid4().hex,
            confirmation='review', preview_token=preview['preview_token'])
        before = self.messages._path.read_bytes()
        sessions = SessionStore(str(self.path))
        messages = MessageStore(str(self.messages._path))
        engine = SessionEngine(sessions, messages, self.trigger, self.registry)
        engine.bind_channel_policy(lambda: self.service)
        messages.bind_channel_policy(lambda: self.service)
        journal = deepcopy(sessions.get(run['id']))
        engine.recover_projections()
        engine.recover_projections()
        self.assertEqual(messages.get_recent(channel='review'), [])
        self.assertEqual(messages._path.read_bytes(), before)
        self.assertEqual(sessions.get(run['id']), journal)
        self.assertEqual(journal['admitted_events'][0]['content'], 'Already projected')

    def test_completed_pending_result_blocks_lifecycle_with_exact_transport_scope(self):
        run, invocation = self.pending_final()
        for operation in ('archive', 'delete', 'rename'):
            extra = {'new_name': 'renamed'} if operation == 'rename' else {}
            preview = self.service.preview(operation, 'review', **extra)
            pending = [item for item in preview['blockers'] if item['kind'] == 'projection_pending']
            self.assertEqual(len(pending), 1)
            self.assertEqual((pending[0]['session_id'], pending[0]['run_id'], pending[0]['dispatch_id']),
                             (run['id'], run['run_id'], invocation['dispatch_id']))
            with self.assertRaises(ChannelConflict):
                self.service.apply(operation, 'review', request_id=uuid.uuid4().hex,
                    confirmation='review', preview_token=preview['preview_token'], **extra)
        preview = self.service.preview('archive', 'review')
        self.engine.recover_projections()
        changed = self.service.preview('archive', 'review')
        self.assertNotEqual(preview['preview_token'], changed['preview_token'])
        self.assertFalse(any(item['kind'] == 'projection_pending' for item in changed['blockers']))
        with self.assertRaises(ChannelConflict):
            self.service.apply('archive', 'review', request_id=uuid.uuid4().hex,
                confirmation='review', preview_token=preview['preview_token'])

    def test_continuation_projection_remains_pending_in_archived_history(self):
        run, invocation = self.start()
        question = self.engine.admit_event(invocation['brief_id'], 'question', 'Which source?', self.peer)
        self.bind()
        self.catalog.set_state('review', 'archived', expected_revision=0)
        self.sessions.continue_question(run['id'], question['event_id'], 'Exact answer\r\nretained')
        before = self.messages._path.read_bytes()
        self.engine.recover_projections()
        self.assertEqual(self.messages._path.read_bytes(), before)
        preview = self.service.preview('delete', 'review')
        pending = [row for row in preview['blockers'] if row['kind'] == 'projection_pending']
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['dispatch_id'], invocation['dispatch_id'])
        self.catalog.set_state('review', 'active', expected_revision=1)
        self.engine.recover_projections()
        self.engine.recover_projections()
        answers = [row for row in self.messages.get_recent(channel='review') if row['type'] == 'session_input']
        self.assertEqual([row['text'] for row in answers], ['Exact answer\r\nretained'])

    def test_pending_intent_suppresses_projection_without_changing_journal(self):
        run, _ = self.pending_final()
        self.bind()
        self.catalog.begin('delete', 'review', None, request_id=uuid.uuid4().hex, expected_revision=0)
        before, ledger = self.path.read_bytes(), self.trigger.queue.path.read_bytes()
        with patch.object(self.messages, 'add_once') as add:
            self.engine.recover_projections()
        add.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.trigger.queue.path.read_bytes(), ledger)
        self.assertIsNone(self.sessions.get(run['id'])['admitted_events'][0]['projected_message_id'])

    def test_unavailable_policy_keeps_admission_and_recovery_quiet(self):
        run, invocation = self.start()
        self.bind()
        self.catalog.path.write_text('corrupt', encoding='utf-8')
        result = self.engine.admit_event(invocation['brief_id'], 'final', 'Retained during hold', self.peer)
        self.assertEqual(result['status'], 'admitted')
        self.assertIsNone(self.sessions.get(run['id'])['admitted_events'][0]['projected_message_id'])
        with patch.object(self.messages, 'add_once') as add, patch('session_engine.log') as log:
            self.engine.recover_projections()
        add.assert_not_called()
        log.error.assert_not_called()
        log.warning.assert_not_called()
        self.engine.bind_channel_policy(lambda: (_ for _ in ()).throw(ChannelUnavailable('held')))
        self.engine.recover_projections()

    def test_active_projection_storage_error_is_not_swallowed_as_policy_refusal(self):
        run, _ = self.pending_final()
        self.bind()
        before = deepcopy(self.sessions.get(run['id']))
        for failure in (OSError('write failed'), ValueError('conflicting event')):
            with patch.object(self.messages, 'add_once', side_effect=failure), self.assertRaises(type(failure)):
                self.engine._project_session(run['id'], dispatch=False)
            self.assertEqual(self.sessions.get(run['id']), before)

    def test_archived_multiphase_final_does_not_dispatch_the_next_turn(self):
        run = self.engine.start_session('review', 'review', {'reviewer': 'claude', 'editor': 'codex'}, 'operator')
        invocation = run['active_invocation']
        self.bind()
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.trigger.queue.path.read_bytes()
        result = self.engine.admit_event(invocation['brief_id'], 'final', 'First phase retained', self.peer)
        self.assertEqual(result['status'], 'admitted')
        current = self.sessions.get(run['id'])
        self.assertEqual(current['current_phase'], 1)
        self.assertIsNone(current['active_invocation'])
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_stopped_late_final_quarantine_remains_available_while_archived(self):
        run, invocation = self.start()
        self.bind()
        self.engine.stop_session(run['id'], 'operator stopped')
        self.catalog.set_state('review', 'archived', expected_revision=0)
        with self.assertRaises(EventConflict):
            self.engine.admit_event(invocation['brief_id'], 'final', 'Late retained audit', self.peer)
        saved = self.sessions.get(run['id'])
        self.assertEqual(saved['admitted_events'], [])
        self.assertEqual(len(saved['quarantined_events']), 1)
        self.assertEqual(saved['quarantined_events'][0]['content'], 'Late retained audit')
        self.assertEqual(saved['quarantined_events'][0]['reason'], 'stopped_run')
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_held_review_projection_does_not_block_active_peer_recovery(self):
        run, _ = self.pending_final()
        general = self.sessions.get(self.session_id)
        with patch.object(self.engine, '_project_session'):
            self.engine.admit_event(general['active_invocation']['brief_id'], 'question', 'Active peer question', self.owner)
        self.bind()
        self.catalog.begin('delete', 'review', None, request_id=uuid.uuid4().hex, expected_revision=0)
        self.engine.recover_projections()
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        self.assertIsNone(self.sessions.get(run['id'])['admitted_events'][0]['projected_message_id'])
        self.assertTrue(any(row['text'] == 'Active peer question' for row in self.messages.get_recent(channel='general')))

    def test_projection_storage_runs_under_engine_and_active_catalog_boundary(self):
        run, _ = self.pending_final()
        self.bind()
        original, observed = self.messages.add_once, []
        def checked(*args, **kwargs):
            self.assertTrue(self.engine._lock._is_owned())
            self.assertTrue(self.catalog._lock._is_owned())
            self.assertFalse(self.messages._lock.locked())
            observed.append(kwargs['channel'])
            return original(*args, **kwargs)
        with patch.object(self.messages, 'add_once', side_effect=checked):
            self.engine._project_session(run['id'], dispatch=False)
        self.assertEqual(observed, ['review', 'review'])


if __name__ == '__main__':
    unittest.main()
