"""Whole-team capacity and frozen sequential design bounds, without providers."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import AgentTrigger
from api_seats import SeatStore
from registry import RuntimeRegistry
from review_brief import BriefError, freeze_inputs
from session_engine import SessionEngine
from session_store import SessionStore, validate_session_template
from store import MessageStore

DEFAULT = {'max_roles': 16, 'max_participants_per_phase': 16, 'max_phases': 12,
           'max_prompt_chars': 1000, 'max_total_turns': 128}
LEGACY = {'max_roles': 6, 'max_participants_per_phase': 4, 'max_phases': 6,
          'max_prompt_chars': 200, 'max_total_turns': 24}


def design(roles=6, participants=None, phases=1, prompt='Read the exact source.'):
    names = ['role' + str(i) for i in range(roles)]
    return {'id': 'capacity-review', 'name': 'Whole team review', 'roles': names,
            'phases': [{'name': 'Phase ' + str(i), 'participants': list(names if participants is None else participants),
                        'prompt': prompt, 'is_output': i == phases - 1} for i in range(phases)]}


class SessionCapacityTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'session_runs.json'

    def test_default_policy_is_explicit_and_independent(self):
        policy = importlib.import_module('session_capacity').capacity_policy
        self.assertEqual(policy(), DEFAULT)
        first = policy()
        first['max_roles'] = 1
        self.assertEqual(policy(), DEFAULT)

    def test_six_member_phase_validates_without_rewriting_members(self):
        template = design()
        before = deepcopy(template)
        self.assertEqual(validate_session_template(template), [])
        self.assertEqual(template, before)

    def test_direct_invalid_save_refuses_before_memory_or_file_changes(self):
        store = SessionStore(str(self.path))
        store.save_custom_template(design(roles=1))
        before = store.get_template('capacity-review')
        files = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        invalid = design(roles=17)
        with self.assertRaises(ValueError):
            store.save_custom_template(invalid)
        self.assertEqual(store.get_template('capacity-review'), before)
        self.assertEqual({str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, files)

    def engine_fixture(self, template, capacity=None):
        store = SessionStore(str(self.path), capacity_policy=capacity)
        store.save_custom_template(template)
        registry = RuntimeRegistry(str(self.root))
        registry.seed({'seat' + str(i): {'type': 'api', 'label': 'Fixture ' + str(i)}
                       for i in range(len(template['roles']))})
        instances = [registry.register('seat' + str(i)) for i in range(len(template['roles']))]
        cast = {role: instance['name'] for role, instance in zip(template['roles'], instances)}
        messages = MessageStore(str(self.root / 'messages.jsonl'))
        trigger = AgentTrigger(registry, str(self.root))
        engine = SessionEngine(store, messages, trigger, registry)
        run = engine.start_session(template['id'], 'capacity', cast, 'operator', input_text='Exact café\r\nsource')
        return store, engine, trigger, registry, instances, messages, run

    def assert_limit(self, valid, invalid, fragment, policy=None):
        self.assertEqual(validate_session_template(valid, capacity_policy=policy), [])
        before = deepcopy(invalid)
        errors = validate_session_template(invalid, capacity_policy=policy)
        self.assertTrue(any(fragment in error.lower() for error in errors), errors)
        self.assertEqual(invalid, before, 'validation must retain the complete rejected design')

    def test_policy_rejects_boolean_noninteger_nonpositive_unknown_and_nonmapping(self):
        policy = importlib.import_module('session_capacity').capacity_policy
        for key in DEFAULT:
            for value in (True, False, 0, -1, 1.5, '6', None, float('inf')):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    policy({key: value})
        for value in ({'unknown': 1}, [], 'six', 6):
            with self.subTest(value=value), self.assertRaises(ValueError):
                policy(value)
        with self.assertRaises(ValueError):
            policy({'max_total_turns': 15, 'max_participants_per_phase': 16})

    def test_all_five_sanity_ceilings_are_enforced(self):
        policy = importlib.import_module('session_capacity').capacity_policy
        ceilings = {'max_roles': 256, 'max_participants_per_phase': 256,
                    'max_phases': 64, 'max_prompt_chars': 10000, 'max_total_turns': 1024}
        self.assertEqual(policy(ceilings), ceilings)
        for key, limit in ceilings.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy({**ceilings, key: limit + 1})

    def test_low_explicit_policy_is_allowed_and_caller_overrides_are_copied(self):
        policy = importlib.import_module('session_capacity').capacity_policy
        low = {key: 1 for key in DEFAULT}
        self.assertEqual(policy(low), low)
        original = deepcopy(low)
        self.assertEqual(validate_session_template(design(1, prompt='x'), capacity_policy=low), [])
        frozen = freeze_inputs(design(1, prompt='x'), capacity_policy=low)
        low['max_roles'] = 2
        self.assertEqual(frozen['capacity_policy'], original)
        self.assertTrue(validate_session_template(design(2, prompt='x'), capacity_policy=original))

    def test_role_boundary_sixteen_and_seventeen(self):
        self.assert_limit(design(16, participants=['role0']), design(17, participants=['role0']), 'roles')

    def test_phase_participant_boundary_counts_occurrences(self):
        self.assert_limit(design(1, participants=['role0'] * 16),
                          design(1, participants=['role0'] * 17), 'participants')

    def test_phase_boundary_twelve_and_thirteen(self):
        self.assert_limit(design(1, phases=12), design(1, phases=13), 'phases')

    def test_prompt_boundary_counts_unicode_characters_without_clipping(self):
        self.assert_limit(design(1, prompt='日' * 1000), design(1, prompt='日' * 1001), 'prompt')
        self.assertEqual(freeze_inputs(design(1, prompt='日' * 1000))['design_snapshot']['phases'][0]['prompt'], '日' * 1000)

    def test_total_turn_boundary_includes_output_phase_and_repeated_roles(self):
        valid = design(1, participants=['role0'] * 16, phases=8)
        invalid = deepcopy(valid)
        invalid['phases'].append({'name': 'One extra output', 'participants': ['role0'], 'prompt': 'Output.', 'is_output': True})
        self.assert_limit(valid, invalid, 'total turns')

    def test_total_turn_count_is_sum_of_participants_not_roles_times_phases(self):
        policy = {**DEFAULT, 'max_participants_per_phase': 2, 'max_total_turns': 3}
        valid = design(3, participants=['role0'], phases=2)
        valid['phases'][1]['participants'] = ['role1', 'role2']
        invalid = deepcopy(valid)
        invalid['phases'][0]['participants'].append('role0')
        self.assert_limit(valid, invalid, 'total turns', policy)

    def test_freeze_snapshots_exact_policy_and_design_independently(self):
        template, policy = design(), deepcopy(DEFAULT)
        frozen = freeze_inputs(template, input_text='Exact café\r\nsource', capacity_policy=policy)
        policy['max_roles'] = 1
        template['phases'][0]['participants'].pop()
        self.assertEqual(frozen['capacity_policy'], DEFAULT)
        self.assertEqual(len(frozen['design_snapshot']['phases'][0]['participants']), 6)
        self.assertEqual(frozen['input_snapshot']['text'], 'Exact café\r\nsource')

    def test_six_identity_bound_turns_execute_sequentially_without_skipping_any_member(self):
        store, engine, trigger, registry, instances, messages, run = self.engine_fixture(design())
        briefs, dispatches, attempts = [], [], []
        for index, instance in enumerate(instances):
            current = store.get(run['id'])
            invocation = current['active_invocation']
            self.assertEqual((current['current_phase'], current['current_turn']), (0, index))
            self.assertEqual(invocation['expected_identity_id'], instance['identity_id'])
            envelope = store.briefs.get(invocation['brief_id'], instance)
            self.assertEqual(envelope['role'], 'role' + str(index))
            self.assertEqual(envelope['source'], 'Exact café\r\nsource')
            self.assertEqual(len(envelope['prior_results']), index)
            records = json.loads((self.root / 'queue/ledger.json').read_text('utf-8'))['records']
            self.assertEqual(len(records), index + 1)
            self.assertEqual(sum(record['state'] not in ('released', 'failed', 'cancelled') for record in records), 1)
            for later in instances[index + 1:]:
                self.assertIsNone(trigger.queue.claim(later, 'not-yet-scheduled'))
            record = trigger.queue.claim(instance, 'consumer-' + str(index))
            self.assertEqual(record['envelope']['dispatch_id'], invocation['dispatch_id'])
            trigger.queue.acknowledge(instance, invocation['dispatch_id'], 'consumer-' + str(index))
            engine.admit_event(invocation['brief_id'], 'final', 'Result ' + str(index), instance)
            trigger.queue.release(instance, invocation['dispatch_id'], 'consumer-' + str(index))
            briefs.append(invocation['brief_id'])
            dispatches.append(invocation['dispatch_id'])
            attempts.append(invocation['attempt_id'])
        complete = store.get(run['id'])
        self.assertEqual(complete['state'], 'complete')
        self.assertIsNone(complete['active_invocation'])
        self.assertEqual([event['content'] for event in complete['admitted_events']], ['Result ' + str(i) for i in range(6)])
        self.assertEqual([event['expected_identity_id'] for event in complete['admitted_events']], [item['identity_id'] for item in instances])
        for identities in (briefs, dispatches, attempts):
            self.assertEqual(len(set(identities)), 6)

    def test_seven_seat_saved_package_preserves_full_membership_independent_of_design(self):
        seats = [{'id': 'seat' + str(i), 'name': 'Seat ' + str(i), 'adapter': 'openai-compatible',
                  'provider': 'fake', 'model': 'fake-model', 'reasoning': None,
                  'launch_profile': 'standard', 'secret_ref': ''} for i in range(7)]
        package = {'id': 'team', 'name': 'Seven seat team', 'seats': seats}
        store = SeatStore(self.root, {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1'}})
        store.save(package)
        reloaded = SeatStore(self.root, store.providers)
        self.assertEqual(reloaded.package('team')['seats'], seats)
        self.assertEqual(validate_session_template(design(7)), [])

    def test_corrected_child_inherits_parent_policy_after_server_policy_is_lowered(self):
        store = SessionStore(str(self.path), capacity_policy=DEFAULT)
        store.save_custom_template(design())
        parent = store.create('capacity-review', 'source', {role: 'Human ' + role for role in design()['roles']},
                              'operator', input_text='Original source', participant_bindings={
                                  role: {'kind': 'human', 'identity_id': None} for role in design()['roles']})
        store._event_update(parent['id'], lambda value: value.update(state='stopped', dispatch_eligible=False, stop_id=uuid.uuid4().hex))
        lower = SessionStore(str(self.path), capacity_policy={key: 1 for key in DEFAULT})
        child = lower.prepare_restart(parent['id'], 'Corrected source', uuid.uuid4().hex)
        self.assertEqual(child['capacity_policy'], DEFAULT)
        self.assertEqual(child['design_snapshot'], parent['design_snapshot'])
        child['capacity_policy']['max_roles'] = 1
        self.assertEqual(lower.get(parent['id'])['capacity_policy'], DEFAULT)
        self.assertEqual(lower.get(child['id'])['capacity_policy'], DEFAULT)

    def test_legacy_missing_policy_stays_readonly_and_child_uses_legacy_limits(self):
        store = SessionStore(str(self.path))
        store.save_custom_template(design(1))
        parent = store.create('capacity-review', 'legacy', {'role0': 'Human'}, 'operator', input_text='Old',
                              participant_bindings={'role0': {'kind': 'human', 'identity_id': None}})
        def legacy(value):
            value.pop('capacity_policy', None)
            value.update(state='stopped', dispatch_eligible=False, stop_id=uuid.uuid4().hex)
        store._event_update(parent['id'], legacy)
        before = self.path.read_bytes()
        loaded = SessionStore(str(self.path), capacity_policy={**DEFAULT, 'max_prompt_chars': 3000})
        self.assertNotIn('capacity_policy', loaded.get(parent['id']))
        self.assertEqual(self.path.read_bytes(), before)
        child = loaded.prepare_restart(parent['id'], 'New source', uuid.uuid4().hex)
        self.assertEqual(child['capacity_policy'], LEGACY)
        self.assertNotIn('capacity_policy', loaded.get(parent['id']))

    def test_stale_saved_design_rejected_at_start_without_run_or_dispatch_or_draft_mutation(self):
        store = SessionStore(str(self.path))
        store.save_custom_template(design())
        custom = (self.root / 'custom_templates.json').read_bytes()
        low = SessionStore(str(self.path), capacity_policy={key: 1 for key in DEFAULT})
        registry = RuntimeRegistry(str(self.root))
        trigger = AgentTrigger(registry, str(self.root))
        engine = SessionEngine(low, MessageStore(str(self.root / 'messages.jsonl')), trigger, registry)
        with self.assertRaises(BriefError):
            engine.start_session('capacity-review', 'invalid', {role: 'Human ' + role for role in design()['roles']}, 'operator')
        self.assertEqual(low.list_all(), [])
        self.assertFalse(self.path.exists())
        self.assertFalse((self.root / 'queue/ledger.json').exists())
        self.assertEqual((self.root / 'custom_templates.json').read_bytes(), custom)
        self.assertEqual(len(low.get_template('capacity-review')['roles']), 6)

    def test_continue_inherits_frozen_capacity_despite_lower_active_store_policy(self):
        store, engine, trigger, registry, instances, messages, run = self.engine_fixture(design())
        owner, old = instances[0], run['active_invocation']
        trigger.queue.claim(owner, 'worker')
        trigger.queue.acknowledge(owner, old['dispatch_id'], 'worker')
        event = engine.admit_event(old['brief_id'], 'question', 'Clarify?', owner)
        trigger.queue.release(owner, old['dispatch_id'], 'worker')
        loaded = SessionStore(str(self.path), capacity_policy={key: 1 for key in DEFAULT})
        resumed = SessionEngine(loaded, messages, AgentTrigger(registry, str(self.root)), registry)
        resumed.continue_session(run['id'], event['event_id'], 'Exact answer')
        current = loaded.get(run['id'])
        self.assertEqual(current['capacity_policy'], DEFAULT)
        self.assertNotEqual(current['active_invocation']['attempt_id'], old['attempt_id'])
        self.assertEqual(current['active_invocation']['turn_id'], old['turn_id'])
        self.assertEqual(current['design_snapshot'], run['design_snapshot'])

    def test_retry_does_not_consume_logical_design_turn_capacity(self):
        policy = {key: 1 for key in DEFAULT}
        store, engine, trigger, registry, instances, messages, run = self.engine_fixture(design(1, prompt='x'), policy)
        owner, old = instances[0], run['active_invocation']
        trigger.queue.claim(owner, 'worker')
        trigger.queue.acknowledge(owner, old['dispatch_id'], 'worker')
        trigger.queue.release(owner, old['dispatch_id'], 'worker', failed=True, error='provider_failure')
        engine.monitor_turns(now=time.time())
        checkpoint = store.get(run['id'])['turn_recovery']
        engine.retry_turn(run['id'], checkpoint['checkpoint_id'], old['attempt_id'], uuid.uuid4().hex)
        current = store.get(run['id'])
        self.assertEqual(current['capacity_policy'], policy)
        self.assertEqual((current['current_phase'], current['current_turn']), (0, 0))
        self.assertEqual(current['active_invocation']['turn_id'], old['turn_id'])
        self.assertNotEqual(current['active_invocation']['attempt_id'], old['attempt_id'])


if __name__ == '__main__':
    unittest.main()
