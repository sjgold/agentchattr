"""One bounded capacity policy for design ingress and public instructions."""
import unittest


class CapacityConfigTests(unittest.TestCase):
    def test_defaults_partial_override_and_independent_snapshots(self):
        from session_capacity import capacity_policy, policy_description
        defaults = capacity_policy()
        self.assertEqual(defaults, dict(max_roles=16, max_participants_per_phase=16,
            max_phases=12, max_prompt_chars=1000, max_total_turns=128))
        reduced = capacity_policy({'max_participants_per_phase': 3, 'max_total_turns': 8})
        self.assertEqual(reduced['max_roles'], 16)
        text = policy_description(reduced)
        for value in ('16 roles', '3 participants', '12 phases', '1000', '8 total'):
            self.assertIn(value, text)
        reduced['max_roles'] = 1
        self.assertEqual(capacity_policy()['max_roles'], 16)

    def test_invalid_policies_and_sanity_bounds_are_rejected(self):
        from session_capacity import capacity_policy
        for bad in ([], 'limits', {'unknown': 1}, {'max_roles': 257},
                    {'max_total_turns': 1025}, {'max_total_turns': 15}):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                capacity_policy(bad)
        for key in capacity_policy():
            for value in (0, -1, True, False, 1.5, '6', None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    capacity_policy({key: value})
        one = {key: 1 for key in capacity_policy()}
        self.assertEqual(capacity_policy(one), one)
