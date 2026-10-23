"""A disappeared managed coordinator gets a checkpoint without brief authority."""
import unittest
from unittest.mock import patch
import uuid

from tests import test_result_owner_wiring as fixture


class MissingParticipantCheckpointTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.reader, _ = self.fixture.ready('api')
        self.coordinator, _ = self.fixture.ready('cli')
        self.sessions.save_custom_template({'id': 'missing-coordinator', 'name': 'Missing coordinator',
            'roles': ['reader', 'coordinator'], 'phases': [
                {'name': 'Evidence', 'participants': ['reader'], 'prompt': 'Read source.'},
                {'name': 'Output', 'participants': ['coordinator'], 'prompt': 'Synthesize.', 'is_output': True}]})
        self.run = self.engine.start_session('missing-coordinator', 'missing-output',
            {'reader': self.reader['name'], 'coordinator': self.coordinator['name']}, 'operator', input_text='Frozen source')

    def disappear(self):
        self.fixture.registry.deregister(self.coordinator['name'])
        with patch.object(self.sessions.briefs, 'put', side_effect=AssertionError('No authority for an absent seat')):
            self.engine.admit_event(self.run['active_invocation']['brief_id'], 'final', 'APPROVED_PRIOR', self.reader)
        return self.sessions.get(self.run['id'])

    def test_disappearance_between_turns_creates_stalled_intent_without_brief_or_delivery(self):
        queued = len(self.trigger.queue.for_identity(self.coordinator))
        run = self.disappear()
        self.assertEqual(run['state'], 'stalled')
        invocation = run['active_invocation']
        self.assertEqual(invocation['expected_identity_id'], self.coordinator['identity_id'])
        self.assertIs(invocation['intent_only'], True)
        self.assertEqual(run['turn_recovery']['attempt_id'], invocation['attempt_id'])
        self.assertEqual(run['turn_recovery']['reason'], 'disconnected')
        self.assertFalse(self.sessions.briefs._path(invocation['brief_id']).exists())
        self.assertEqual(len(self.trigger.queue.for_identity(self.coordinator)), queued)
        self.assertEqual(run['admitted_events'][0]['content'], 'APPROVED_PRIOR')

    def test_intent_only_checkpoint_can_be_explicitly_skipped_without_inventing_answer(self):
        run = self.disappear()
        self.assertIsNotNone(run.get('active_invocation'))
        changed = self.sessions.skip_participant(run['id'], checkpoint_id=run['turn_recovery']['checkpoint_id'],
            attempt_id=run['active_invocation']['attempt_id'], request_id=uuid.uuid4().hex,
            reason='Coordinator disconnected.', confirm_skip=True)
        self.assertEqual(changed['state'], 'complete')
        self.assertIs(changed['missing_output'], True)
        self.assertEqual(len(changed['admitted_events']), 1)
        self.assertEqual(changed['skipped_turns'][0]['role'], 'coordinator')
