"""Engine selected-message attachment with real stores and explicit nonnative exit-proof seam."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import patch
import uuid

from agents import AgentTrigger
from dispatch_queue import QueueConflict
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict, EventValidationError
from tests import test_dispatch_queue as ledger_fixture
from tests import test_result_owner_wiring as fixture


class CliMessageAttachmentTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.cli, _ = self.fixture.ready('cli')
        self.run = fixture.ResultOwnerWiringTests.start(self, self.cli['name'])
        self.dispatch = self.run['active_invocation']['dispatch_id']
        self.message = self.engine.send_chat(self.cli, 'Selected café\r\n@all `/literal command`',
            dispatch_id=self.dispatch, channel=self.run['channel'])
        self.candidate = self.engine.cli_message_candidate(self.run['id'], self.message['id'])
        self.decision = {key: deepcopy(self.candidate[key]) for key in
                         ('message_id', 'message_uid', 'snapshot_hash', 'checkpoint')}
        self.decision.update(request_id=uuid.uuid4().hex, kind='final', confirm_operator_attribution=False)
        patcher = patch.object(self.fixture.manager, 'selected_cli_exit_proof',
                               return_value={'local_ended': False, 'reason': 'unit_unproven'})
        self.proof = patcher.start()
        self.addCleanup(patcher.stop)

    def attach(self, decision=None):
        return self.engine.attach_cli_message(self.run['id'], self.decision if decision is None else decision)

    def positive_proof(self):
        provenance = self.run['participant_bindings']['reader']['launch_provenance']
        return dict(local_ended=True, dispatch_id=self.dispatch, seat_identity_id=self.cli['identity_id'],
                    launch_attempt=provenance['launch_attempt'],
                    verification_basis='retained_native_handle_observed_end')

    def reload_engine(self):
        self.sessions = SessionStore(str(self.sessions._path))
        self.messages = MessageStore(str(self.messages._path))
        self.trigger = AgentTrigger(self.fixture.registry, str(self.fixture.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.fixture.registry,
                                    seat_manager=self.fixture.manager)

    def accepted(self):
        return self.sessions.get(self.run['id'])['admitted_events']

    def test_attach_loads_exact_source_and_returns_only_safe_ack_with_conservative_queued_hold(self):
        ack = self.attach()
        self.assertEqual(set(ack), {'status', 'session_id', 'accepted_event_id', 'kind',
            'source_message_id', 'source_message_uid', 'attribution', 'transport_settled'})
        self.assertEqual(ack['status'], 'admitted')
        self.assertFalse(ack['transport_settled'])
        run = self.sessions.get(self.run['id'])
        self.assertEqual(len(run['admitted_events']), 1)
        event = run['admitted_events'][0]
        self.assertEqual(event['event_id'], ack['accepted_event_id'])
        self.assertEqual(event['content'], self.message['text'])
        projected = self.messages.get_snapshot(event['projected_message_id'])
        self.assertEqual(projected['text'], self.message['text'])
        self.assertTrue(projected['metadata']['routing_suppressed'])
        held = self.trigger.queue.owned(self.cli, self.dispatch)
        self.assertEqual(held['state'], 'cancelled')
        self.assertIs(held['recovery_hold']['cleared'], False)

    def test_active_owner_is_cancelled_only_after_durable_admission_and_fence(self):
        raw = self.trigger.queue._queue
        raw.claim(self.cli, 'authentic-consumer')
        original = raw.hold_recovered
        def persisted_before_hold(*args, **kwargs):
            run = self.sessions.get(self.run['id'])
            self.assertEqual(len(run['admitted_events']), 1)
            self.assertEqual(run['superseded_attempts'][-1]['reason'], 'superseded_by_operator_recovery')
            return original(*args, **kwargs)
        with patch.object(raw, 'hold_recovered', side_effect=persisted_before_hold):
            ack = self.attach()
        self.assertFalse(ack['transport_settled'])
        held = raw.claim(self.cli, 'authentic-consumer')
        self.assertEqual(held['state'], 'cancelling')
        self.assertIs(held['recovery_hold']['cleared'], False)

    def test_strict_decision_and_changed_or_deleted_source_fail_before_admission(self):
        disk = self.sessions._path.read_bytes()
        for changes in ({'text': 'operator override'}, {'request_id': True}, {'message_id': True},
                        {'message_id': -1}, {'kind': 'chat'}, {'confirm_operator_attribution': 1},
                        {'checkpoint': {}}, {'snapshot_hash': 'A' * 64}, {'message_uid': 'wrong'}):
            with self.subTest(changes=changes), self.assertRaises((EventValidationError, EventConflict)):
                self.attach(dict(self.decision, **changes))
            self.assertEqual(self.sessions._path.read_bytes(), disk)
        for key in self.decision:
            missing = deepcopy(self.decision)
            del missing[key]
            with self.subTest(missing=key), self.assertRaises((EventValidationError, EventConflict)):
                self.attach(missing)
        self.message['text'] = 'Changed after preview'
        with self.assertRaises(EventConflict):
            self.attach()
        self.messages.delete([self.message['id']])
        with self.assertRaises(EventConflict):
            self.attach()
        self.assertEqual(self.sessions._path.read_bytes(), disk)
        self.proof.assert_not_called()

    def test_concurrent_replay_reload_stop_and_deleted_source_keep_one_event_projection_and_no_dispatch(self):
        barrier = threading.Barrier(4)
        def attach_once(_):
            barrier.wait(timeout=5)
            return self.attach()
        with ThreadPoolExecutor(max_workers=4) as pool:
            acks = list(pool.map(attach_once, range(4)))
        self.assertEqual(len({ack['accepted_event_id'] for ack in acks}), 1)
        event = deepcopy(self.accepted()[0])
        self.assertEqual(len(self.accepted()), 1)
        self.messages.delete([self.message['id']])
        self.sessions.stop_run(self.run['id'], 'Stop after accepted selection')
        self.reload_engine()
        with patch.object(self.trigger, 'trigger_sync', side_effect=AssertionError('replay dispatched work')):
            replay = self.attach()
        self.assertEqual(replay['accepted_event_id'], event['event_id'])
        self.assertEqual(self.accepted()[0], event)
        self.assertEqual(len([msg for msg in self.messages.get_recent(100)
                              if msg.get('uid') == 'session-event:' + event['event_id']]), 1)
        with self.assertRaises(EventConflict):
            self.attach(dict(self.decision, kind='question'))

    def test_queue_hold_io_failure_preserves_accepted_content_and_false_ack_until_repair(self):
        raw = self.trigger.queue._queue
        self.proof.return_value = self.positive_proof()
        with patch.object(raw, 'hold_recovered', side_effect=OSError('Injected hold write outage')):
            ack = self.attach()
        self.assertEqual(ack['status'], 'admitted')
        self.assertFalse(ack['transport_settled'])
        self.assertEqual(self.accepted()[0]['content'], self.message['text'])
        self.assertFalse(self.sessions.get(self.run['id'])['superseded_attempts'][-1]['selected_transport']['resolved'])
        repaired = self.attach()
        self.assertTrue(repaired['transport_settled'])
        self.assertEqual(repaired['accepted_event_id'], ack['accepted_event_id'])

    def test_positive_exact_proof_confirms_owned_cancellation_without_forging_receipt_and_resolves_audit(self):
        for stop_before_hold in (False, True):
            with self.subTest(stop_before_hold=stop_before_hold):
                if stop_before_hold:
                    self.run = fixture.ResultOwnerWiringTests.start(self, self.cli['name'], 'stop-proof')
                    self.dispatch = self.run['active_invocation']['dispatch_id']
                    message = self.engine.send_chat(self.cli, 'Selected before Stop',
                        dispatch_id=self.dispatch, channel='stop-proof')
                    candidate = self.engine.cli_message_candidate(self.run['id'], message['id'])
                    self.decision = {key: deepcopy(candidate[key]) for key in
                                     ('message_id', 'message_uid', 'snapshot_hash', 'checkpoint')}
                    self.decision.update(request_id=uuid.uuid4().hex, kind='final', confirm_operator_attribution=False)
                raw = self.trigger.queue._queue
                raw.claim(self.cli, 'authentic-consumer')
                provenance = deepcopy(self.run['participant_bindings']['reader']['launch_provenance'])
                self.proof.return_value = self.positive_proof()
                real_admit = self.sessions.admit_selected_cli_event
                def admitted_then_stop(*args, **kwargs):
                    updated = real_admit(*args, **kwargs)
                    if stop_before_hold:
                        self.sessions.stop_run(self.run['id'], 'Stop in accepted-content/queue gap')
                    return updated
                with patch.object(self.sessions, 'admit_selected_cli_event', side_effect=admitted_then_stop):
                    ack = self.attach()
                self.assertTrue(ack['transport_settled'])
                self.proof.assert_called_with(provenance, self.dispatch)
                settled = raw.owned(self.cli, self.dispatch)
                self.assertEqual(settled['state'], 'cancelled')
                self.assertEqual(settled['cancellation']['status'], 'local_ended')
                self.assertEqual(settled['cancellation']['source'], 'runtime_reconciliation')
                self.assertIs(settled['recovery_hold']['cleared'], True)
                run = self.sessions.get(self.run['id'])
                if stop_before_hold:
                    self.assertEqual(settled['stop_id'], run['stop_id'])
                    self.assertNotIn('cancellation_id', settled)
                transport = run['superseded_attempts'][-1]['selected_transport']
                self.assertIs(transport['resolved'], True)
                self.assertEqual(transport['launch_provenance'], provenance)
                self.assertEqual(transport['exit_proof']['dispatch_id'], self.dispatch)

    def test_ledger_settlement_failure_never_reports_transport_settled_from_proof_alone(self):
        raw = self.trigger.queue._queue
        self.proof.return_value = self.positive_proof()
        with patch.object(raw, 'settle_recovered', side_effect=OSError('Injected settlement failure')):
            ack = self.attach()
        self.assertFalse(ack['transport_settled'])
        self.assertEqual(len(self.accepted()), 1)
        self.assertIs(raw.owned(self.cli, self.dispatch)['recovery_hold']['cleared'], False)
        self.assertTrue(self.attach()['transport_settled'])
        self.assertEqual(len(self.accepted()), 1)

    def test_projection_before_backlink_gap_repairs_stable_uid_without_successor(self):
        try:
            with patch.object(self.sessions, 'link_event_projection', side_effect=OSError('Backlink gap')):
                self.attach()
        except OSError:
            pass  # Accepted content is authoritative even if its projection backlink fails.
        event = self.accepted()[0]
        self.assertIsNone(event['projected_message_id'])
        uid = 'session-event:' + event['event_id']
        self.assertEqual(len([msg for msg in self.messages.get_recent(100) if msg.get('uid') == uid]), 1)
        with patch.object(self.trigger, 'trigger_sync', side_effect=AssertionError('repair dispatched work')):
            ack = self.attach()
        self.assertEqual(ack['accepted_event_id'], event['event_id'])
        self.assertIsNotNone(self.accepted()[0]['projected_message_id'])
        self.assertEqual(len([msg for msg in self.messages.get_recent(100) if msg.get('uid') == uid]), 1)

    def test_question_awaits_input_and_explicit_continuation_keeps_original_content(self):
        ack = self.attach(dict(self.decision, kind='question'))
        run = self.sessions.get(self.run['id'])
        self.assertEqual(run['state'], 'awaiting_input')
        self.assertEqual(run['current_question']['event_id'], ack['accepted_event_id'])
        self.engine.continue_session(self.run['id'], ack['accepted_event_id'], 'Explicit operator continuation')
        continued = self.sessions.get(self.run['id'])
        self.assertEqual(continued['continuation_context'][0]['question'], self.message['text'])
        self.assertEqual(continued['continuation_context'][0]['answer'], 'Explicit operator continuation')
        self.assertNotEqual(continued['active_invocation']['attempt_id'], self.run['active_invocation']['attempt_id'])
        self.assertEqual(self.attach(dict(self.decision, kind='question'))['accepted_event_id'], ack['accepted_event_id'])

    def test_verified_peer_successor_is_enqueued_once_and_existing_jobs_remain_untouched(self):
        peer, _ = self.fixture.ready('api')
        self.sessions.save_custom_template({'id': 'two-phase-cli', 'name': 'Two phases', 'roles': ['reader', 'editor'],
            'phases': [{'name': 'Read', 'participants': ['reader'], 'prompt': 'Read source.'},
                       {'name': 'Edit', 'participants': ['editor'], 'prompt': 'Edit result.', 'is_output': True}]})
        self.run = self.engine.start_session('two-phase-cli', 'peer-review',
            {'reader': self.cli['name'], 'editor': peer['name']}, 'operator', input_text='Frozen source')
        self.dispatch = self.run['active_invocation']['dispatch_id']
        message = self.engine.send_chat(self.cli, 'Selected phase one', dispatch_id=self.dispatch, channel='peer-review')
        candidate = self.engine.cli_message_candidate(self.run['id'], message['id'])
        self.decision = {key: deepcopy(candidate[key]) for key in ('message_id', 'message_uid', 'snapshot_hash', 'checkpoint')}
        self.decision.update(request_id=uuid.uuid4().hex, kind='final', confirm_operator_attribution=False)
        raw = self.trigger.queue._queue
        job = raw.enqueue(self.cli, ledger_fixture.envelope(job_id=77))
        ack = self.attach()
        current = self.sessions.get(self.run['id'])
        self.assertEqual(current['active_invocation']['expected_identity_id'], peer['identity_id'])
        peer_dispatch = current['active_invocation']['dispatch_id']
        self.assertEqual(len(raw.for_identity(peer)), 1)
        self.assertEqual(raw.owned(self.cli, job['envelope']['dispatch_id']), job)
        with patch.object(self.trigger, 'trigger_sync', side_effect=AssertionError('replay dispatched successor')):
            self.assertEqual(self.attach()['accepted_event_id'], ack['accepted_event_id'])
        self.assertEqual(self.sessions.get(self.run['id'])['active_invocation']['dispatch_id'], peer_dispatch)
        self.assertEqual(len(raw.for_identity(peer)), 1)

    def test_pending_stop_retry_corrected_fences_and_normal_event_first_writer(self):
        baseline = self.sessions.get(self.run['id'])
        def restore(changes):
            def update(value):
                value.clear()
                value.update(deepcopy(dict(baseline, **changes)))
            self.sessions._event_update(self.run['id'], update)
        for changes in ({'stop_id': uuid.uuid4().hex}, {'pending_retry': {'request_id': uuid.uuid4().hex}},
                        {'replaced_by_run_id': uuid.uuid4().hex}):
            restore(changes)
            disk = self.sessions._path.read_bytes()
            with self.subTest(changes=changes), self.assertRaises(EventConflict):
                self.attach()
            self.assertEqual(self.sessions._path.read_bytes(), disk)
        restore({})
        barrier = threading.Barrier(2)
        def compete(selected):
            barrier.wait(timeout=5)
            try:
                if selected:
                    self.attach()
                else:
                    self.engine.admit_event(self.run['active_invocation']['brief_id'], 'final',
                                            'Normal final winner', self.cli)
                return 'admitted'
            except EventConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(compete, (True, False)))
        self.assertCountEqual(results, ['admitted', 'conflict'])
        self.assertEqual(len(self.accepted()), 1)

    def test_missing_unpublished_dispatch_holds_only_affected_identity_without_fake_record(self):
        with patch.object(self.trigger.queue, 'enqueue', side_effect=OSError('Unpublished dispatch')):
            self.engine.start_session('seal-test', 'unpublished', {'reader': self.cli['name']},
                                      'operator', input_text='Unpublished source')
        self.run = self.sessions.list_all('unpublished')[0]
        self.dispatch = self.run['active_invocation']['dispatch_id']
        message = self.engine.send_chat(self.cli, 'Legacy scoped unpublished result', channel='unpublished')
        candidate = self.engine.cli_message_candidate(self.run['id'], message['id'])
        self.decision = {key: deepcopy(candidate[key]) for key in ('message_id', 'message_uid', 'snapshot_hash', 'checkpoint')}
        self.decision.update(request_id=uuid.uuid4().hex, kind='final', confirm_operator_attribution=True)
        ack = self.attach()
        self.assertFalse(ack['transport_settled'])
        raw = self.trigger.queue._queue
        self.assertFalse(any(record['envelope']['dispatch_id'] == self.dispatch for record in raw.for_identity(self.cli)))
        with self.assertRaises(QueueConflict):
            # The original session's still-queued work is held by the unpublished identity audit.
            self.trigger.queue.claim(self.cli, 'new-consumer')
        self.proof.return_value = self.positive_proof()
        self.assertTrue(self.attach()['transport_settled'])
