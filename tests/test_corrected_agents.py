"""Managed role snapshots and corrected-review preparation/activation gates."""
import json
from pathlib import Path
import time
import unittest
import uuid
from api_seats import atomic_json
from agents import AgentTrigger
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict


class CorrectedAgentTests(unittest.TestCase):
    def setUp(self):
        from tests.test_restart_launch import RestartLaunchTests
        self.fixture = RestartLaunchTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.api, self.launch = f.ready('api')
        self.sessions = SessionStore(str(f.root / 'runs.json'))
        self.sessions.save_custom_template({'id': 'one', 'name': 'One review', 'roles': ['reviewer'],
            'phases': [{'name': 'Review', 'participants': ['reviewer'], 'prompt': 'Review exactly.', 'is_output': True}]})
        self.messages = MessageStore(str(f.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(f.registry, str(f.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, f.registry, seat_manager=f.manager)
        self.parent = self.engine.start_session('one', 'general', {'reviewer': self.api['name']},
                                                 'operator', input_text='OLD-DOCUMENT')
        self.engine.stop_session(self.parent['id'])
        self.engine.reconcile_stops()

    def test_start_freezes_actual_launch_then_api_restarts_with_same_supervisor_despite_template_drift(self):
        f = self.fixture
        provenance = self.parent['participant_bindings']['reviewer']['launch_provenance']
        self.assertEqual(provenance['effective']['seat']['model'], 'api-original')
        f.store.providers['fake-api']['system_prompt'] = 'CHANGED template'
        child = self.engine.correct_and_restart(self.parent['id'], 'NEW-DOCUMENT café\r\n', uuid.uuid4().hex)
        self.assertEqual(child['state'], 'prepared')
        self.assertFalse(child['dispatch_eligible'])
        self.assertIsNone(self.trigger.queue.claim(self.api, 'no-prepared-dispatch'))
        activated = self.engine.activate_restart(child['id'])
        invocation = activated['active_invocation']
        self.assertEqual(invocation['expected_identity_id'], self.api['identity_id'])
        brief = self.sessions.briefs.get(invocation['brief_id'], self.api)
        self.assertEqual(brief['source'], 'NEW-DOCUMENT café\r\n')
        self.assertEqual(brief['prior_results'], [])
        self.assertEqual(len(f.processes), 1)
        self.assertNotIn(self.api['token'], json.dumps(activated))
        self.assertNotIn('credential-value-test-only', json.dumps(activated))
        self.assertEqual(self.engine.activate_restart(child['id'])['active_invocation']['dispatch_id'], invocation['dispatch_id'])

    def test_unrelated_pending_work_blocks_before_lineage_or_runtime_side_effects(self):
        self.trigger.trigger_sync(self.api['name'], message='user: unrelated', channel='other')
        with self.assertRaises(EventConflict):
            self.engine.correct_and_restart(self.parent['id'], 'NEW-DOCUMENT', uuid.uuid4().hex)
        self.assertNotIn('replaced_by_run_id', self.sessions.get(self.parent['id']))
        self.assertEqual(len(self.fixture.processes), 1)
        self.assertEqual(self.trigger.queue.claim(self.api, 'unrelated')['envelope']['channel'], 'other')

    def test_missing_old_provenance_requires_explicit_current_replacement_selection(self):
        self.sessions._event_update(self.parent['id'], lambda s: s['participant_bindings']['reviewer'].pop('launch_provenance'))
        with self.assertRaises(EventConflict):
            self.engine.correct_and_restart(self.parent['id'], 'NEW-DOCUMENT', uuid.uuid4().hex)
        child = self.engine.correct_and_restart(self.parent['id'], 'NEW-DOCUMENT', uuid.uuid4().hex,
                                                replacements={'reviewer': self.api['identity_id']})
        self.assertEqual(child['participant_bindings']['reviewer']['launch_provenance']['launch_attempt'], self.launch['attempt'])
        self.assertEqual(self.engine.activate_restart(child['id'])['state'], 'waiting')

    def test_unknown_replacement_role_is_rejected_without_creating_child(self):
        with self.assertRaises((EventConflict, ValueError)):
            self.engine.correct_and_restart(self.parent['id'], 'NEW-DOCUMENT', uuid.uuid4().hex,
                                             replacements={'unknown': self.api['identity_id']})
        self.assertEqual(len(self.sessions.list_all()), 1)

    def test_second_fresh_cli_generation_does_not_retain_previous_context_selector(self):
        f = self.fixture
        f.store.providers['fake-cli'].update(cli_fresh_context_args=['--context-id', '{context_id}'],
                                       cli_fresh_context_verified=True)
        instance, _ = f.ready('cli')
        provenance = f.manager.launch_provenance(instance)
        def ended(attempt):
            atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'stopped',
                'child_exit_code': 0, 'updated_at': time.time()})
            attempt['process'].poll.return_value = 0
            attempt['process'].returncode = 0
        ended(f.manager.attempts['team/cli'])
        first = f.manager.prepare_clean_context(provenance, uuid.uuid4().hex)
        attempt = f.manager.attempts[first['key']]
        fresh_instance = f.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'name': fresh_instance['name'],
            'state': 'ready', 'adapter_connected': True, 'authentication': 'unknown', 'updated_at': time.time()})
        f.manager.context_status(first)
        next_provenance = f.manager.launch_provenance(fresh_instance)
        ended(attempt)
        second = f.manager.prepare_clean_context(next_provenance, uuid.uuid4().hex)
        arguments = f.manager.attempts[second['key']]['effective']['provider']['cli_args']
        self.assertNotIn(first['context_id'], arguments)
        self.assertEqual(arguments.count('--context-id'), 1)
        self.assertIn(second['context_id'], arguments)


if __name__ == '__main__':
    unittest.main()
