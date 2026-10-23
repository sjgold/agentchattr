"""A retained handle cannot authorize interpreting changed birth metadata."""
import json
import unittest

from api_seats import atomic_json
from tests import test_api_preparation_repair as fixture


@unittest.skipUnless(fixture.sys.platform == 'win32', 'actual retained Windows worker handle')
class PreparationBirthGuardTests(unittest.TestCase):
    def test_changed_birth_after_authentication_blocks_control_before_stop(self):
        f = fixture.APIPreparationRepairTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        native = f.native_preparation()
        manager, prepared = native['manager'], native['prepared']
        path = native['attempt']['snapshot'].with_name('birth.json')
        receipt_path = path.with_name('receipt.json')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        atomic_json(receipt_path, {**receipt, 'state': 'ready'})
        identity = receipt['identity_id']
        self.assertTrue(manager.restart_readiness(identity, manager.boot_id)['process_verified'])
        birth = json.loads(path.read_text(encoding='utf-8'))
        changed = {**birth, 'creation_filetime': str(int(birth['creation_filetime']) + 1)}
        atomic_json(path, changed)
        self.assertFalse(manager.restart_readiness(identity, manager.boot_id)['process_verified'])
        principal = manager.registry.get_instance(receipt['name'])
        scope = changed['ownership']
        forged = {'attempt': scope['attempt'], 'launch_nonce': scope['launch_nonce'],
                  'server_identity': scope['server_identity'], 'boot_id': manager.boot_id,
                  'worker_pid': changed['pid'], 'creation_filetime': changed['creation_filetime'],
                  'worker_root': changed['worker_root']}
        self.assertFalse(manager.observe_runtime_heartbeat(principal, forged)['verified'])
        self.assertNotIn(prepared['launch_attempt'], manager.retired_attempts)
        self.assertNotIn(prepared['launch_attempt'], manager.runtime_history)
        result = manager.prepare_retry_context(native['provenance'], native['context_key'], binding=native['binding'],
            retry_attempt=prepared['launch_attempt'], confirmation={'confirm': True, 'launch_attempt': prepared['launch_attempt']})
        self.assertEqual(result['state'], 'blocked')
        self.assertFalse(path.with_name('stop.json').exists())
        self.assertIsNone(native['attempt']['process'].poll())
        native['spawn'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
