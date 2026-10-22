"""Validate operator recovery limits without silently normalizing bad values."""
import unittest


class RecoveryPolicyTests(unittest.TestCase):
    def test_defaults_and_partial_override_are_independent_snapshots(self):
        from turn_recovery import recovery_policy
        first = recovery_policy({'ack_timeout': 2})
        self.assertEqual(first, {'ack_timeout': 2, 'response_timeout': 900, 'monitor_interval': 1})
        first['response_timeout'] = 10
        self.assertEqual(recovery_policy()['response_timeout'], 900)

    def test_invalid_limits_fail_before_any_run_can_be_created(self):
        from turn_recovery import recovery_policy
        for invalid in (True, False, 0, -1, float('nan'), float('inf'), '30', None):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                recovery_policy({'ack_timeout': invalid})
        for invalid in ([], 'limits', {'unknown': 30}):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                recovery_policy(invalid)
