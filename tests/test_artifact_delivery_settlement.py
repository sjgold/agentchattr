"""Root-owned A-1 terminal-delivery settlement, real stores and controlled processes."""
import json
import unittest
from unittest.mock import patch

from artifact_delivery import ArtifactOutbox
from tests import test_artifact_recovery as fixture


class ArtifactDeliverySettlementTests(unittest.TestCase):
    def context(self):
        owner = fixture.ArtifactRecoveryTests()
        self.addCleanup(owner.doCleanups)
        return owner, owner.context()

    def terminal_transport(self, case, request_state, transport_state):
        if request_state == 'prepared':
            audit, packet = case.new_request()
            original = case.artifacts.set_attempt_state
            def lost_mark(*args, **kwargs):
                if args[3]['state'] == 'queued':
                    raise OSError('controlled enqueue-before-mark crash')
                return original(*args, **kwargs)
            with patch.object(case.artifacts, 'set_attempt_state', side_effect=lost_mark):
                with self.assertRaises(OSError):
                    case.authority.prepare_request(audit, packet, audit['request_id'])
        else:
            audit = case.prepare()
        consumer = case.claim(audit)
        if request_state == 'active':
            case.authority.get_brief(audit['brief_id'], case.instance)
        case.trigger.queue.release(case.instance, audit['dispatch_id'], consumer,
                                   failed=transport_state != 'released')
        if transport_state == 'settled_recovered':
            # Valid retained ledger-state fixture; this does not claim native exit evidence.
            path = case.trigger.queue.path
            value = json.loads(path.read_text(encoding='utf-8'))
            value['records'][0]['state'] = 'settled_recovered'
            path.write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], request_state)
        return audit, consumer

    def test_terminal_transport_without_saved_result_settles_all_live_states_in_startup_and_resume(self):
        for operation in ('startup', 'resume'):
            for request_state in ('prepared', 'queued', 'active'):
                for transport_state in ('released', 'failed', 'settled_recovered'):
                    with self.subTest(operation=operation, request=request_state, transport=transport_state):
                        owner, case = self.context()
                        audit, _ = self.terminal_transport(case, request_state, transport_state)
                        transport = case.trigger.queue.owned(case.instance, audit['dispatch_id'])
                        owner.reload(case)
                        if operation == 'startup':
                            result = case.authority.recover_startup()
                            self.assertIn({'request_id': audit['request_id'], 'dispatch_id': audit['dispatch_id'],
                                           'reason': 'delivery_unconfirmed'}, result['held'])
                        else:
                            result = case.authority.resume_request(audit['request_id'])
                            self.assertEqual(result['request']['reason'], 'delivery_unconfirmed')
                        row = case.artifacts.get_request(audit['request_id'])
                        self.assertEqual((row['state'], row['reason']), ('failed', 'delivery_unconfirmed'))
                        self.assertEqual(case.artifacts.pending('review'), [])
                        self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 0)
                        self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id']), transport)
                        before = case.files()
                        case.authority.resume_request(audit['request_id'])
                        self.assertEqual(case.files(), before)

    def test_active_request_without_transport_is_reported_and_never_reenqueued(self):
        _, case = self.context()
        audit, _ = case.claimed()
        case.trigger.queue.path.write_text(json.dumps({'version': 1, 'records': []}), encoding='utf-8')
        before = case.files()
        result = case.authority.recover_startup()
        self.assertIn({'request_id': audit['request_id'], 'dispatch_id': audit['dispatch_id'],
                       'reason': 'operator_recovery_required'}, result['held'])
        self.assertEqual(case.files(), before)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'active')

    def test_late_result_after_delivery_failure_is_quarantined_and_cannot_revive_lineage(self):
        owner, case = self.context()
        audit, consumer = self.terminal_transport(case, 'active', 'failed')
        case.authority.resume_request(audit['request_id'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'failed')
        box, _ = owner.save(case, audit, consumer)  # Explicit late trusted-worker write fixture.
        owner.reload(case)
        result = case.authority.recover_startup()
        self.assertEqual(len(result['quarantined']), 1)
        self.assertEqual(box.get_disposition(audit['dispatch_id'])['reason'], 'superseded')
        self.assertIsNone(box.get_ack(audit['dispatch_id']))
        self.assertEqual(case.artifacts.pending('review'), [])

    def test_unreadable_outbox_and_cancel_fence_refuse_no_result_settlement(self):
        for fault in ('unreadable', 'cancel_fence'):
            with self.subTest(fault=fault):
                _, case = self.context()
                audit, _ = self.terminal_transport(case, 'active', 'failed')
                if fault == 'cancel_fence':
                    path = case.trigger.queue.path
                    value = json.loads(path.read_text(encoding='utf-8'))
                    value['records'][0]['cancellation_id'] = 'e' * 32
                    path.write_text(json.dumps(value), encoding='utf-8')
                from contextlib import nullcontext
                seam = (patch.object(ArtifactOutbox, 'find', side_effect=case.storage.ArtifactUnavailable('fixture held'))
                        if fault == 'unreadable' else nullcontext())
                before = case.files()
                with seam:
                    result = case.authority.recover_startup()
                self.assertTrue(result['held'])
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'active')
                self.assertEqual(case.files(), before)


if __name__ == '__main__':
    unittest.main()
