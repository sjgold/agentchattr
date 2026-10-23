"""Coordinator replacement orchestration with nonnative process/readiness seams."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tests import test_participant_replacement_store as fixture


class ParticipantRecoveryEngineTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.ParticipantReplacementStoreTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.engine, self.sessions = self.f.engine, self.f.sessions
        self.decision = {key: deepcopy(self.f.intent[key]) for key in ('request_id', 'checkpoint_id', 'attempt_id', 'reason')}
        self.decision.update(target_identity_id=self.f.source['identity_id'], target_fingerprint=self.f.provenance['fingerprint'])

    def test_replacement_intent_is_durable_before_clone_and_source_is_untouched(self):
        manager = self.f.fixture.manager
        prepare = manager.prepare_replacement_context
        def inspect_order(*args, **kwargs):
            persisted = self.sessions.get(self.f.run['id'])
            self.assertEqual(persisted['pending_replacement']['request_id'], self.decision['request_id'])
            self.assertEqual(persisted['superseded_attempts'][-1]['reason'], 'participant_replacement')
            self.assertEqual(self.f.trigger.queue.owned(self.f.old, self.f.run['active_invocation']['dispatch_id'])['state'], 'cancelled')
            return prepare(*args, **kwargs)
        with patch.object(manager, 'prepare_replacement_context', side_effect=inspect_order), \
             patch.object(manager, 'terminate_owned', side_effect=AssertionError('No old/source termination')):
            ack = self.engine.replace_participant(self.f.run['id'], self.decision)
        self.assertEqual(ack['status'], 'preparing_contexts')
        self.assertEqual(ack['request_id'], self.decision['request_id'])
        self.assertNotIn('target_provenance', ack)

    def test_ready_clone_uses_reserved_ids_and_immutable_prior_then_exact_replay_does_not_dispatch(self):
        self.engine.replace_participant(self.f.run['id'], self.decision)
        pending = self.sessions.get(self.f.run['id'])['pending_replacement']
        context, _ = self.f.clone(pending)
        result = self.engine.replace_participant(self.f.run['id'], self.decision)
        self.assertEqual(result['status'], 'dispatched')
        current = self.sessions.get(self.f.run['id'])
        invocation = current['active_invocation']
        self.assertEqual(invocation['attempt_id'], pending['new_attempt_id'])
        self.assertEqual(invocation['expected_identity_id'], context['identity_id'])
        brief = self.sessions.briefs.get(invocation['brief_id'], operator=True)
        self.assertEqual(brief['prior_results'], pending['approved_prior_results'])
        before = self.f.fixture.spawn.call_count
        with patch.object(self.f.trigger, 'trigger_sync', side_effect=AssertionError('No replay dispatch')):
            self.assertEqual(self.engine.replace_participant(self.f.run['id'], self.decision), result)
        self.assertEqual(self.f.fixture.spawn.call_count, before)
