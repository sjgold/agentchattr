"""A new server boot cannot silently resume a previous boot's pending launch."""
from copy import deepcopy
import unittest
import uuid

from tests import test_cold_retry_settlement as fixture


class RetryBootProgressTests(unittest.TestCase):
    def test_new_boot_holds_pending_retry_until_explicit_same_request_is_repeated(self):
        f = fixture.ColdRetrySettlementTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        manager = f.proof_manager(True)
        first_boot = manager.boot_id
        f.engine.reconcile_restart(boot_id=first_boot, now=f.now)
        context = {'state': 'starting', 'key': 'retry-fixture/api', 'launch_attempt': uuid.uuid4().hex,
                   'identity_id': None, 'name': None, 'clean_context': False, 'old_local_ended': True}
        manager.prepare_retry_context.return_value = deepcopy(context)
        f.engine.retry_turn(f.session_id, f.checkpoint, f.old['attempt_id'], f.request, now=f.now)
        reserved = f.current()['pending_retry']['new_attempt_id']
        before_queue = (f.root / 'queue/ledger.json').read_bytes()
        manager.prepare_retry_context.reset_mock()
        second_boot = uuid.uuid4().hex
        manager.boot_id = second_boot
        f.engine.reconcile_restart(boot_id=second_boot, now=f.now + 1)
        f.engine.monitor_turns(now=f.now + 1)
        self.assertEqual(f.current()['state'], 'interrupted')
        self.assertFalse(f.current()['dispatch_eligible'])
        manager.prepare_retry_context.assert_not_called()
        self.assertEqual((f.root / 'queue/ledger.json').read_bytes(), before_queue)
        self.assertEqual(f.current()['pending_retry']['new_attempt_id'], reserved)
        f.engine.retry_turn(f.session_id, f.checkpoint, f.old['attempt_id'], f.request, now=f.now + 2)
        manager.prepare_retry_context.assert_called_once()
        self.assertEqual(f.current()['state'], 'retrying')
        self.assertEqual(f.current()['pending_retry']['recovery_boot_id'], second_boot)
        self.assertEqual(f.current()['pending_retry']['new_attempt_id'], reserved)
        self.assertEqual((f.root / 'queue/ledger.json').read_bytes(), before_queue)


if __name__ == '__main__':
    unittest.main()
