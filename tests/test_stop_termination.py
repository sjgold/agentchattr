"""Explicit CLI termination must bind the current app-owned launch."""
import json
import time
import unittest
from api_seats import SeatError, atomic_json


class StopTerminationTests(unittest.TestCase):
    def setUp(self):
        from tests.test_api_seat_runtime import APISeatRuntimeTests
        self.fixture = APISeatRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.manager.launch('team', 'writer')
        self.attempt = f.manager.attempts['team/writer']
        self.attempt['seat']['adapter'] = 'cli'
        self.instance = f.registry.register(self.attempt['base'])

    def test_stale_launch_confirmation_cannot_stop_replacement_or_write_control(self):
        f = self.fixture
        with self.assertRaises(SeatError):
            f.manager.terminate_owned(self.instance['identity_id'], 'stale-launch')
        f.process.terminate.assert_not_called()
        self.assertFalse(self.attempt['snapshot'].with_name('stop.json').exists())

    def test_missing_child_exit_evidence_remains_unresolved_even_when_worker_exits(self):
        f = self.fixture
        def exit_without_receipt(timeout):
            f.process.poll.return_value = 0
            return 0
        f.process.wait.side_effect = exit_without_receipt
        result = f.manager.terminate_owned(self.instance['identity_id'], self.attempt['id'])
        self.assertFalse(result['local_ended'])

    def test_child_exit_receipt_and_worker_exit_prove_owned_local_end(self):
        f = self.fixture
        def child_and_worker_exit(timeout):
            atomic_json(self.attempt['receipt'], {'attempt': self.attempt['id'], 'state': 'stopped',
                'child_exit_code': -15, 'updated_at': time.time()})
            f.process.poll.return_value = 0
            return 0
        f.process.wait.side_effect = child_and_worker_exit
        offer = f.manager.termination_offer(self.instance['identity_id'])
        self.assertEqual(offer['launch_attempt'], self.attempt['id'])
        result = f.manager.terminate_owned(self.instance['identity_id'], offer['launch_attempt'])
        self.assertTrue(result['local_ended'])
        self.assertEqual(result['remote_compute'], 'unverified')
        control = json.loads(self.attempt['snapshot'].with_name('stop.json').read_text(encoding='utf-8'))
        self.assertEqual(control['attempt'], self.attempt['id'])


if __name__ == '__main__':
    unittest.main()
