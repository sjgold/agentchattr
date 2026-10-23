"""Deterministic skip repair IDs cannot consume a later human continuation."""
import unittest
from unittest.mock import patch
import uuid

from tests import test_participant_replacement_store as fixture


class SkipSuccessorQuestionTests(unittest.TestCase):
    def test_next_participant_question_then_continue_allocates_a_new_attempt(self):
        f = fixture.ParticipantReplacementStoreTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        decision = {key: f.intent[key] for key in ('checkpoint_id', 'attempt_id', 'request_id')}
        decision.update(reason='Skip missing editor contribution.', confirm_skip=True)
        with patch.object(f.fixture.manager, 'participant_exit_proof', return_value={'local_ended': False}):
            f.engine.skip_participant(f.run['id'], decision)
        before = f.sessions.get(f.run['id'])['active_invocation']
        f.engine.admit_event(before['brief_id'], 'question', 'Which evidence should lead?', f.source)
        current = f.sessions.get(f.run['id'])
        result = f.engine.continue_session(f.run['id'], current['current_question']['event_id'], 'Lead with the original source.')
        self.assertNotEqual(result['active_invocation']['attempt_id'], before['attempt_id'])
        self.assertNotEqual(result['active_invocation']['brief_id'], before['brief_id'])
        brief = f.sessions.briefs.get(result['active_invocation']['brief_id'], operator=True)
        self.assertEqual(brief['continuation_context'][-1]['answer'], 'Lead with the original source.')
        self.assertEqual(len(brief['missing_contributions']), 1)
