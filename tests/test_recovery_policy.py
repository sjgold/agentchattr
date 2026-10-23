"""Validate operator recovery limits without silently normalizing bad values."""
import unittest


class RecoveryPolicyTests(unittest.TestCase):
    def test_managed_adapter_limits_are_frozen_and_run_override_wins(self):
        from tests.test_managed_turn_retry import ManagedTurnRetryTests
        from agents import AgentTrigger
        from session_engine import SessionEngine
        fixture = ManagedTurnRetryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        adapters = {'cli': {'response_timeout': 75, 'monitor_interval': .25},
                    'openai-compatible': {'ack_timeout': 3, 'response_timeout': 40}}
        engine = SessionEngine(fixture.sessions, fixture.messages,
            AgentTrigger(fixture.registry, str(fixture.root)), fixture.registry,
            seat_manager=fixture.manager, recovery_policy={'ack_timeout': 9},
            adapter_recovery_policy=adapters)
        run = engine.start_session('review', 'adapter-policy',
            {'reviewer': fixture.api['name'], 'editor': fixture.cli['name']}, 'operator',
            input_text='Frozen adapter limits', recovery_policy={'response_timeout': 12})
        expected = {'ack_timeout': 3, 'response_timeout': 12, 'monitor_interval': 1}
        self.assertEqual(run['active_invocation']['monitoring']['policy'], expected)
        self.assertEqual(run['participant_bindings']['editor']['recovery_policy'],
                         {'ack_timeout': 9, 'response_timeout': 12, 'monitor_interval': .25})
        adapters['openai-compatible']['ack_timeout'] = 999
        engine._adapter_recovery_policy['openai-compatible']['ack_timeout'] = 999
        invocation = run['active_invocation']
        engine.monitor_turns(now=invocation['monitoring']['created_at'] + 3.01)
        self.assertEqual(fixture.sessions.get(run['id'])['turn_recovery']['reason'], 'missing_ack')
        self.assertEqual(fixture.sessions.get(run['id'])['active_invocation']['monitoring']['policy'], expected)

    def test_invalid_adapter_configuration_fails_before_engine_hooks(self):
        from session_engine import SessionEngine
        from unittest.mock import Mock
        for invalid in ([], {'unknown': {}}, {'cli': None}, {'cli': {'response_timeout': True}}):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                SessionEngine(Mock(), Mock(), None, adapter_recovery_policy=invalid)

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
