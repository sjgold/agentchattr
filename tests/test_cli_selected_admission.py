"""Selected CLI admission transactions; real stores, process doubles, no native proof."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

from session_store import SessionStore
from turn_events import EventConflict, EventValidationError
from tests import test_result_owner_wiring as fixture


class CliSelectedAdmissionTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.cli, _ = self.fixture.ready('cli')
        self.run = fixture.ResultOwnerWiringTests.start(self, self.cli['name'])
        self.message = self.engine.send_chat(self.cli, 'Selected café\r\n@all `literal code`',
            dispatch_id=self.run['active_invocation']['dispatch_id'], channel=self.run['channel'])
        self.snapshot = self.messages.get_snapshot(self.message['id'])
        candidate = self.engine.cli_message_candidate(self.run['id'], self.message['id'])
        self.intent = {key: deepcopy(candidate[key]) for key in ('message_uid', 'snapshot_hash', 'checkpoint')}
        self.intent['request_id'] = uuid.uuid4().hex

    def admit(self, **changes):
        return self.sessions.admit_selected_cli_event(self.run['id'], self.snapshot,
                                                      **dict(self.intent, **changes))

    def event(self, run):
        return next(event for event in run['admitted_events']
                    if event.get('selected_request', {}).get('request_id') == self.intent['request_id'])

    def rewrite_run(self, baseline, **changes):
        def update(value):
            value.clear()
            value.update(deepcopy(dict(baseline, **changes)))
        self.sessions._event_update(self.run['id'], update)

    def digest(self, snapshot):
        return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()

    def assert_refused_unchanged(self, callback):
        disk, memory = self.sessions._path.read_bytes(), self.sessions.list_all()
        with self.assertRaises((EventConflict, EventValidationError)):
            callback()
        self.assertEqual(self.sessions._path.read_bytes(), disk)
        self.assertEqual(self.sessions.list_all(), memory)

    def test_final_admits_exact_source_and_fences_current_attempt_atomically(self):
        updated = self.admit()
        event = self.event(updated)
        original = self.run['active_invocation']
        self.assertEqual(updated['state'], 'complete')
        self.assertEqual(event['content'], self.snapshot['text'])
        self.assertEqual(event['provenance'], 'operator_selected_cli_result')
        self.assertEqual(event['source_message_uid'], self.snapshot['uid'])
        self.assertEqual(event['source_identity_id'], self.cli['identity_id'])
        self.assertEqual(event['expected_identity_id'], original['expected_identity_id'])
        self.assertEqual(event['source_attempt_id'], original['attempt_id'])
        self.assertEqual(event['snapshot_hash'], self.intent['snapshot_hash'])
        fence = next(item for item in updated['superseded_attempts'] if item['attempt_id'] == original['attempt_id'])
        self.assertEqual(fence['reason'], 'superseded_by_operator_recovery')
        self.assertEqual(fence['dispatch_id'], original['dispatch_id'])
        self.assertEqual(fence['request_id'], self.intent['request_id'])
        self.assertEqual(event['sender'], self.snapshot['sender'])
        self.assertEqual(event['source_message_id'], self.snapshot['id'])
        self.assertEqual(event['attribution'], 'machine_verified')
        self.assertEqual(event['submitted_by'], 'operator')
        self.assertEqual(len(event['event_id']), 32)
        self.assertIsNone(event['projected_message_id'])
        self.assertIn('recovered_at', event)
        self.snapshot['text'] = 'Later caller mutation'
        self.assertEqual(self.event(self.sessions.get(self.run['id']))['content'], self.message['text'])

    def test_exact_replay_is_persistence_identical_and_does_not_touch_queue_or_messages(self):
        queue_before = self.trigger.queue.status()
        messages_before = self.messages._path.read_bytes()
        updated = self.admit()
        disk = self.sessions._path.read_bytes()
        replay = self.admit()
        self.assertEqual(updated, replay)
        self.assertEqual(self.sessions._path.read_bytes(), disk)
        self.assertEqual(self.trigger.queue.status(), queue_before)
        self.assertEqual(self.messages._path.read_bytes(), messages_before)
        self.assertEqual(len(replay['admitted_events']), 1)

    def test_question_uses_same_turn_and_existing_awaiting_input_contract(self):
        invocation = self.run['active_invocation']
        self.sessions._event_update(self.run['id'], lambda value: value.update(
            state='interrupted', dispatch_eligible=False,
            turn_recovery={'status': 'stalled', 'checkpoint_id': uuid.uuid4().hex}))
        updated = self.admit(kind='question')
        event = self.event(updated)
        self.assertEqual(updated['state'], 'awaiting_input')
        self.assertEqual(updated['current_question']['event_id'], event['event_id'])
        self.assertEqual(updated['current_question']['text'], self.snapshot['text'])
        self.assertEqual((updated['current_phase'], updated['current_turn']),
                         (self.run['current_phase'], self.run['current_turn']))
        self.assertEqual(event['attempt_id'], invocation['attempt_id'])
        self.assertEqual(updated['turn_recovery']['status'], 'resolved')
        self.assertEqual(len(updated['admitted_events']), 1)

    def test_replay_after_stop_reload_and_source_display_edit_has_no_callback_churn(self):
        first = self.admit()
        accepted = self.event(first)
        self.sessions.stop_run(self.run['id'], 'Stopped after admission')
        # Display storage changes do not replace the copied accepted source.
        self.message['text'] = 'Edited live display'
        self.sessions = SessionStore(str(self.sessions._path))
        calls = []
        self.sessions.on_change(lambda *args: calls.append(args))
        disk = self.sessions._path.read_bytes()
        replay = self.admit()
        self.assertEqual(self.event(replay), accepted)
        self.assertTrue(replay['stop_id'])
        self.assertEqual(self.sessions._path.read_bytes(), disk)
        self.assertEqual(calls, [])

    def test_same_request_changed_intent_conflicts_without_mutating_original(self):
        self.admit()
        for changes in ({'kind': 'question'}, {'message_uid': 'different-uid'},
                        {'snapshot_hash': 'a' * 64}, {'confirm_operator_attribution': True},
                        {'submitted_by': 'another operator'},
                        {'checkpoint': dict(self.intent['checkpoint'], attempt_id=uuid.uuid4().hex)}):
            with self.subTest(changes=changes):
                self.assert_refused_unchanged(lambda: self.admit(**changes))

    def test_strict_request_snapshot_checkpoint_confirmation_and_operator_validation(self):
        invalid = ({'request_id': True}, {'request_id': 'not-uuid'}, {'snapshot_hash': 'A' * 64},
                   {'snapshot_hash': '0' * 63}, {'message_uid': ''}, {'kind': 'chat'},
                   {'confirm_operator_attribution': 1}, {'confirm_operator_attribution': 'true'},
                   {'submitted_by': ''}, {'submitted_by': ' '}, {'submitted_by': 'x' * 81},
                   {'submitted_by': None}, {'checkpoint': {}},
                   {'checkpoint': dict(self.intent['checkpoint'], extra='untrusted')},
                   {'checkpoint': dict(self.intent['checkpoint'], session_id=True)},
                   {'checkpoint': dict(self.intent['checkpoint'], turn_id=uuid.uuid4().hex)})
        for changes in invalid:
            with self.subTest(changes=changes):
                self.assert_refused_unchanged(lambda: self.admit(**changes))
        for session_id in (0, True, '1', -1, 99999):
            with self.subTest(session_id=session_id):
                self.assert_refused_unchanged(lambda: self.sessions.admit_selected_cli_event(
                    session_id, self.snapshot, **self.intent))
        for source_id in (-1, True, '0'):
            snapshot = dict(self.snapshot, id=source_id)
            with self.subTest(source_id=source_id):
                self.assert_refused_unchanged(lambda: self.sessions.admit_selected_cli_event(
                    self.run['id'], snapshot, **dict(self.intent, snapshot_hash=self.digest(snapshot))))

    def test_store_revalidates_hash_uid_and_untrusted_scope_instead_of_trusting_preview(self):
        for change in ({'text': 'Replacement text'}, {'uid': 'new-uid'}, {'channel': 'other'}):
            snapshot = dict(self.snapshot, **change)
            with self.subTest(change=change):
                self.assert_refused_unchanged(lambda: self.sessions.admit_selected_cli_event(
                    self.run['id'], snapshot, **self.intent))
        for extra in ({'imported': True}, {'routing_suppressed': True}, {'quarantine_session_id': 1},
                      {'seat_identity_id': uuid.uuid4().hex}, {'run_id': uuid.uuid4().hex},
                      {'provenance': 'unverified_scope'}):
            snapshot = deepcopy(self.snapshot)
            snapshot['metadata'].update(extra)
            with self.subTest(extra=extra):
                self.assert_refused_unchanged(lambda: self.sessions.admit_selected_cli_event(
                    self.run['id'], snapshot, **dict(self.intent, snapshot_hash=self.digest(snapshot))))

    def test_legacy_attribution_needs_literal_confirmation_and_preserves_no_source_attempt(self):
        snapshot = deepcopy(self.snapshot)
        snapshot['metadata'] = {'seat_identity_id': self.cli['identity_id']}
        self.snapshot = snapshot
        self.intent['snapshot_hash'] = self.digest(snapshot)
        self.assert_refused_unchanged(lambda: self.admit())
        updated = self.admit(confirm_operator_attribution=True, submitted_by='Seth')
        event = self.event(updated)
        self.assertEqual(event['attribution'], 'operator_attributed')
        self.assertIsNone(event['source_attempt_id'])
        self.assertEqual(event['submitted_by'], 'Seth')
        self.assertEqual(event['selected_request']['confirm_operator_attribution'], True)

    def test_current_fences_and_adapter_are_revalidated_at_commit(self):
        baseline = self.sessions.get(self.run['id'])
        invocation = baseline['active_invocation']
        api_bindings = deepcopy(baseline['participant_bindings'])
        api_bindings['reader']['launch_provenance']['effective']['seat']['adapter'] = 'openai-compatible'
        for changes in ({'stop_id': uuid.uuid4().hex}, {'pending_retry': {'request_id': uuid.uuid4().hex}},
                        {'replaced_by_run_id': uuid.uuid4().hex},
                        {'participant_bindings': api_bindings},
                        {'active_invocation': dict(invocation, consumed=True)},
                        {'active_invocation': dict(invocation, attempt_id=uuid.uuid4().hex)},
                        {'completion_protocol': 0}):
            self.rewrite_run(baseline, **changes)
            with self.subTest(changes=list(changes)):
                self.assert_refused_unchanged(lambda: self.admit())

    def test_historical_source_a_targets_current_b_without_fabricating_principal(self):
        # Retained Retry history boundary, not a managed/native relaunch claim.
        original = self.run['active_invocation']
        current = dict(original, attempt_id=uuid.uuid4().hex, dispatch_id=uuid.uuid4().hex,
                       brief_id=uuid.uuid4().hex, expected_identity_id=uuid.uuid4().hex,
                       expected_agent='replacement-display')
        bindings = deepcopy(self.run['participant_bindings'])
        bindings['reader']['identity_id'] = current['expected_identity_id']
        bindings['reader']['launch_provenance']['identity_id'] = current['expected_identity_id']
        history = {key: original[key] for key in ('run_id', 'turn_id', 'attempt_id', 'dispatch_id',
                                                'input_revision', 'expected_identity_id')}
        self.rewrite_run(self.run, active_invocation=current, participant_bindings=bindings,
                         superseded_attempts=[history])
        self.intent['checkpoint']['attempt_id'] = current['attempt_id']
        updated = self.admit()
        event = self.event(updated)
        self.assertEqual(event['source_identity_id'], original['expected_identity_id'])
        self.assertEqual(event['expected_identity_id'], current['expected_identity_id'])
        self.assertEqual(event['source_attempt_id'], original['attempt_id'])
        self.assertEqual(event['attempt_id'], current['attempt_id'])
        self.assertEqual(event['sender'], self.snapshot['sender'])
        self.assertEqual(len(updated['superseded_attempts']), 2)

    def test_atomic_replace_failure_rolls_back_fence_and_admission_memory_disk_and_external_stores(self):
        memory, disk = self.sessions.list_all(), self.sessions._path.read_bytes()
        external = {path: path.read_bytes() for path in self.fixture.root.rglob('*') if path.is_file()}
        real_replace = Path.replace
        def fail_session_replace(path, target):
            if Path(target) == self.sessions._path:
                raise OSError('Injected selected transaction replacement failure')
            return real_replace(path, target)
        with patch.object(Path, 'replace', fail_session_replace), self.assertRaises(OSError):
            self.admit()
        self.assertEqual(self.sessions.list_all(), memory)
        self.assertEqual(self.sessions._path.read_bytes(), disk)
        for path, content in external.items():
            self.assertEqual(path.read_bytes(), content)
        reloaded = SessionStore(str(self.sessions._path))
        self.assertEqual(reloaded.list_all(), memory)
        self.assertEqual(self.admit()['state'], 'complete')

    def test_concurrent_same_request_and_competing_normal_result_have_one_durable_winner(self):
        barrier = threading.Barrier(4)
        def same_request():
            barrier.wait(timeout=5)
            return self.admit()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: same_request(), range(4)))
        self.assertEqual(len({self.event(run)['event_id'] for run in results}), 1)
        self.assertEqual(len(self.sessions.get(self.run['id'])['admitted_events']), 1)
        # Global UID reuse is denied across runs even with a different numeric ID.
        uid_run = fixture.ResultOwnerWiringTests.start(self, self.cli['name'], 'uid-review')
        uid_message = self.engine.send_chat(self.cli, 'Another run selected source',
            dispatch_id=uid_run['active_invocation']['dispatch_id'], channel=uid_run['channel'])
        uid_candidate = self.engine.cli_message_candidate(uid_run['id'], uid_message['id'])
        uid_snapshot = self.messages.get_snapshot(uid_message['id'])
        uid_snapshot['uid'] = self.snapshot['uid']
        uid_intent = {key: uid_candidate[key] for key in ('message_uid', 'snapshot_hash', 'checkpoint')}
        uid_intent.update(request_id=uuid.uuid4().hex, message_uid=uid_snapshot['uid'],
                          snapshot_hash=self.digest(uid_snapshot))
        self.assert_refused_unchanged(lambda: self.sessions.admit_selected_cli_event(
            uid_run['id'], uid_snapshot, **uid_intent))
        # Reusing a numeric display ID with a distinct UID is not global reuse.
        uid_snapshot.update(id=self.snapshot['id'], uid=uuid.uuid4().hex)
        uid_intent.update(message_uid=uid_snapshot['uid'], snapshot_hash=self.digest(uid_snapshot))
        accepted_uid_run = self.sessions.admit_selected_cli_event(uid_run['id'], uid_snapshot, **uid_intent)
        self.assertEqual(len(accepted_uid_run['admitted_events']), 1)
        # Fresh real run: normal authenticated result races selected-store admission.
        second = fixture.ResultOwnerWiringTests.start(self, self.cli['name'], 'racing-review')
        invocation = second['active_invocation']
        message = self.engine.send_chat(self.cli, 'Competing selected result',
            dispatch_id=invocation['dispatch_id'], channel=second['channel'])
        snapshot = self.messages.get_snapshot(message['id'])
        candidate = self.engine.cli_message_candidate(second['id'], message['id'])
        intent = {key: candidate[key] for key in ('message_uid', 'snapshot_hash', 'checkpoint')}
        intent['request_id'] = uuid.uuid4().hex
        brief = self.sessions.briefs.get(invocation['brief_id'], self.cli)
        event = {key: brief[key] for key in ('brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')}
        event.update(event_id=uuid.uuid4().hex, kind='final', content='Normal authenticated result')
        gate = threading.Barrier(2)
        def compete(selected):
            gate.wait(timeout=5)
            try:
                if selected:
                    self.sessions.admit_selected_cli_event(second['id'], snapshot, **intent)
                else:
                    self.sessions.admit_event(second['id'], event, self.cli)
                return 'accepted'
            except EventConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(compete, (True, False)))
        self.assertCountEqual(outcomes, ['accepted', 'conflict'])
        self.assertEqual(len(self.sessions.get(second['id'])['admitted_events']), 1)
