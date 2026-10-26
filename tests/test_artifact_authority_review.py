"""Root-owned reviewer regressions; all process observations are fixture-controlled."""
import unittest
from unittest.mock import patch

from tests import test_artifact_recovery as fixture


class ArtifactAuthorityReviewTests(unittest.TestCase):
    def context(self):
        owner = fixture.ArtifactRecoveryTests()
        self.addCleanup(owner.doCleanups)
        return owner, owner.context()

    def test_unexpected_eligibility_errors_close_artifacts_but_preserve_peer_claims(self):
        _, case = self.context()
        audit = case.prepare()
        for number, error in enumerate((KeyError, IndexError)):
            with self.subTest(error=error.__name__):
                peer = 'peer-' + str(number)
                case.trigger.queue.enqueue(case.instance, {'dispatch_id': peer, 'channel': 'peer'})
                with patch.object(case.authority, 'eligible_dispatch_ids', side_effect=error('fixture lookup')):
                    claimed = case.trigger.queue.claim(case.instance, 'peer-consumer')
                self.assertEqual(claimed['envelope']['dispatch_id'], peer)
                case.trigger.queue.release(case.instance, peer, 'peer-consumer')
                self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id'])['state'], 'queued')
        second = case.prepare(channel='peer')
        original = case.authority._producer
        def one_bad_row(audit_value, instance, **kwargs):
            if audit_value['request_id'] == audit['request_id']:
                raise KeyError('fixture malformed owner')
            return original(audit_value, instance, **kwargs)
        with patch.object(case.authority, '_producer', side_effect=one_bad_row):
            self.assertEqual(case.authority.eligible_dispatch_ids(case.instance), {second['dispatch_id']})

    def test_producer_checks_are_reused_only_within_one_eligibility_call(self):
        _, case = self.context()
        audits = [case.prepare(), case.prepare(channel='peer'), case.prepare(channel='general')]
        original = case.manager.artifact_producer
        with patch.object(case.manager, 'artifact_producer', wraps=original) as gate:
            self.assertEqual(case.authority.eligible_dispatch_ids(case.instance), {a['dispatch_id'] for a in audits})
            self.assertEqual(gate.call_count, 1)
        with patch.object(case.manager, 'artifact_producer', return_value={'available': False}) as gate:
            self.assertEqual(case.authority.eligible_dispatch_ids(case.instance), set())
            self.assertEqual(gate.call_count, 1)
        self.assertEqual(case.authority.eligible_dispatch_ids(case.instance), {a['dispatch_id'] for a in audits})

    def test_terminal_known_saved_results_use_superseded_instead_of_unmatched_reason(self):
        for state, reason in (('failed', 'generation_failed'), ('quarantined', 'invalid_response')):
            with self.subTest(state=state):
                owner, case = self.context()
                audit, consumer = case.claimed()
                box, _ = owner.save(case, audit, consumer)
                case.artifacts.set_attempt_state(audit['request_id'], audit['attempt_id'], 'active',
                                                {'state': state, 'reason': reason})
                case.authority.recover_startup()
                self.assertEqual(box.get_disposition(audit['dispatch_id'])['reason'], 'superseded')
                self.assertIsNone(box.get_ack(audit['dispatch_id']))
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], state)

    def test_recovery_conflict_reports_operator_action_instead_of_producer_unavailable(self):
        _, case = self.context()
        audit = case.prepare()
        with patch.object(case.authority, '_resume_request_locked', side_effect=case.storage.ArtifactConflict('fixture mismatch')):
            result = case.authority.recover_startup()
        self.assertEqual(result['held'], [{'request_id': audit['request_id'], 'dispatch_id': audit['dispatch_id'],
                                          'reason': 'operator_recovery_required'}])

    def test_cancelled_prepared_request_with_no_transport_has_no_fence_to_repair(self):
        _, case = self.context()
        audit, _ = case.new_request()
        case.artifacts.reserve_request(audit, audit['request_id'])
        self.assertTrue(case.authority.cancel_request(audit['request_id'])['transport_settled'])
        before = case.files()
        result = case.authority.repair_cancel_fences([audit['request_id']])
        self.assertEqual(result, {'repaired': [audit['request_id']], 'unconfirmed': [], 'remaining': 0})
        self.assertEqual(case.files(), before)


if __name__ == '__main__':
    unittest.main()
