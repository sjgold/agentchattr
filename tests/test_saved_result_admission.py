"""Internal verified-content ingress, real stores and managed process doubles."""
from copy import deepcopy
import json
import time
import unittest
from unittest.mock import patch
import uuid

from result_outbox import seal_result
from tests import test_result_owner_wiring as fixture
from turn_events import EventConflict


class SavedResultAdmissionTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.owner, self.launch = self.fixture.ready('api')
        session = fixture.ResultOwnerWiringTests.start(self, self.owner['name'])
        self.session_id = session['id']
        invocation = session['active_invocation']
        delivery = self.sessions.briefs.get_delivery(invocation['brief_id'], self.owner)
        scope = delivery['result_owner']
        payload = {key: invocation[key] for key in ('brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')}
        payload.update(version=1, session_id=self.session_id, result_id=scope['dispatch_id'],
            event_id=scope['dispatch_id'], created_at=time.time(), kind='final', content='Exact café\r\nsaved answer')
        payload.update({key: value for key, value in scope.items() if key != 'adapter'})
        self.payload = self.sessions.briefs.verify_saved_result(seal_result(payload, delivery['seal_secret']))

    def current(self):
        return self.sessions.get(self.session_id)

    def admit(self, payload=None):
        return self.sessions.admit_verified_saved_event(self.session_id, self.payload if payload is None else payload)

    def test_original_verified_identity_admits_without_any_live_principal(self):
        before = self.current()
        self.fixture.registry.deregister(self.owner['name'])
        result = self.admit()
        self.assertEqual(result['state'], 'complete')
        event = result['admitted_events'][0]
        self.assertEqual(event['provenance'], 'verified_saved_api_result')
        self.assertEqual(event['submitted_by'], 'operator')
        self.assertEqual(event['expected_identity_id'], self.owner['identity_id'])
        self.assertEqual(event['sender'], self.owner['name'])
        self.assertEqual(event['result_id'], self.payload['result_id'])
        self.assertEqual(event['result_launch_attempt'], self.launch['attempt'])
        self.assertEqual(event['content'], self.payload['content'])
        self.assertIsNone(event['projected_message_id'])
        for field in ('input_snapshot', 'rules_snapshot', 'design_snapshot', 'input_revision'):
            self.assertEqual(result[field], before[field])
        for excluded in ('launch_nonce', 'fingerprint', 'seal_secret', '_result_seal'):
            self.assertNotIn(excluded, event)

    def test_saved_question_consumes_once_and_awaits_operator_input(self):
        payload = dict(self.payload, kind='question', content='Which exact revision?')
        result = self.admit(payload)
        self.assertEqual(result['state'], 'awaiting_input')
        self.assertTrue(result['active_invocation']['consumed'])
        self.assertEqual(result['current_question']['event_id'], payload['event_id'])
        before = self.sessions._path.read_bytes()
        with self.assertRaises(EventConflict):
            self.admit(payload)
        self.assertEqual(self.sessions._path.read_bytes(), before)

    def test_wrong_current_identity_and_immutable_scope_leave_store_unchanged(self):
        before = self.sessions._path.read_bytes()
        for field in ('brief_id', 'attempt_id', 'seat_identity_id', 'launch_attempt', 'input_revision'):
            changed = dict(self.payload, **{field: '0' * len(self.payload[field])})
            with self.subTest(field=field), self.assertRaises((ValueError, PermissionError)):
                self.admit(changed)
            self.assertEqual(self.sessions._path.read_bytes(), before)
        changed = dict(self.payload, result_id=uuid.uuid4().hex)
        with self.assertRaises(ValueError):
            self.admit(changed)
        self.assertEqual(self.sessions._path.read_bytes(), before)

    def test_permanent_stop_and_superseded_attempt_cannot_be_admitted(self):
        for field in ('stop_id', 'superseded_attempts'):
            def fence(session):
                session[field] = uuid.uuid4().hex if field == 'stop_id' else [{'attempt_id': self.payload['attempt_id']}]
            self.sessions._event_update(self.session_id, fence)
            before = self.sessions._path.read_bytes()
            with self.assertRaises(EventConflict):
                self.admit()
            self.assertEqual(self.sessions._path.read_bytes(), before)
            self.sessions._event_update(self.session_id, lambda run: run.update(**{field: None if field == 'stop_id' else []}))

    def test_non_api_or_human_bindings_do_not_gain_saved_api_authority(self):
        original = self.current()['participant_bindings']
        for mode in ('cli', 'manual', 'human'):
            def change(run):
                binding = run['participant_bindings']['reader']
                if mode == 'human':
                    binding['kind'] = 'human'
                elif mode == 'manual':
                    binding.pop('launch_provenance')
                else:
                    binding['launch_provenance']['effective']['seat']['adapter'] = 'cli'
            self.sessions._event_update(self.session_id, change)
            before = self.sessions._path.read_bytes()
            with self.subTest(mode=mode), self.assertRaises((ValueError, PermissionError)):
                self.admit()
            self.assertEqual(self.sessions._path.read_bytes(), before)
            self.sessions._event_update(self.session_id, lambda run: run.update(participant_bindings=deepcopy(original)))

    def test_persistence_failure_rolls_back_content_consumption_and_progression(self):
        before, memory = self.sessions._path.read_bytes(), self.current()
        with patch.object(self.sessions, '_save', side_effect=OSError('fixture admission write failed')):
            with self.assertRaises(OSError):
                self.admit()
        self.assertEqual(self.sessions._path.read_bytes(), before)
        self.assertEqual(self.current(), memory)
        self.assertEqual(self.admit()['state'], 'complete')
