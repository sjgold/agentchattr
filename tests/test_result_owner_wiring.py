"""Engine-issued sealed briefs use the actual managed API runtime scope."""
import json
import unittest
from unittest.mock import patch

from agents import AgentTrigger
from api_seats import SeatError
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from tests import test_restart_launch as launch_fixture


class ResultOwnerWiringTests(unittest.TestCase):
    def setUp(self):
        fixture = launch_fixture.RestartLaunchTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.sessions = SessionStore(str(fixture.root / 'session_runs.json'))
        self.sessions.save_custom_template({'id': 'seal-test', 'name': 'Result authority', 'roles': ['reader'],
            'phases': [{'name': 'Review', 'participants': ['reader'], 'prompt': 'Review source.', 'is_output': True}]})
        self.messages = MessageStore(str(fixture.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(fixture.registry, str(fixture.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, fixture.registry,
                                    seat_manager=fixture.manager)

    def start(self, participant, channel='general'):
        return self.engine.start_session('seal-test', channel, {'reader': participant}, 'operator',
                                         input_text='Exact café\r\nsource')

    def test_managed_api_brief_matches_exact_bound_invocation_and_runtime_owner(self):
        owner, _ = self.fixture.ready('api')
        run = self.start(owner['name'])
        invocation = run['active_invocation']
        delivery = self.sessions.briefs.get_delivery(invocation['brief_id'], owner)
        self.assertIn('seal_secret', delivery)
        self.assertEqual(delivery['result_owner'], self.fixture.manager.result_owner(owner, invocation['dispatch_id']))
        public = self.sessions.briefs.get(invocation['brief_id'], owner)
        record = self.trigger.queue.claim(owner, 'test-consumer')
        secret = delivery['seal_secret']
        self.assertNotIn(secret, json.dumps(run))
        self.assertNotIn(secret, json.dumps(record))
        self.assertNotIn(secret, json.dumps(public))
        self.assertEqual(record['envelope']['dispatch_id'], invocation['dispatch_id'])

    def test_cli_manual_and_human_turns_have_no_sealing_key(self):
        cli, _ = self.fixture.ready('cli')
        self.fixture.registry.seed({'manual-api': {'type': 'api'}})
        manual = self.fixture.registry.register('manual-api')
        for index, participant in enumerate((cli, manual, {'name': 'human-reader'})):
            run = self.start(participant['name'], 'unsealed-' + str(index))
            invocation = run['active_invocation']
            public = self.sessions.briefs.get(invocation['brief_id'], operator=True)
            self.assertNotIn('seal_secret', public)
            self.assertNotIn('_result_seal', public)
            if index < 2:
                self.assertNotIn('seal_secret', self.sessions.briefs.get_delivery(invocation['brief_id'], participant))

    def test_failed_managed_owner_lookup_cannot_fall_back_to_an_unsealed_turn(self):
        owner, _ = self.fixture.ready('api')
        for index, outcome in enumerate((None, SeatError('Changed owned metadata'))):
            options = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
            with self.subTest(outcome=type(outcome).__name__), patch.object(self.fixture.manager, 'result_owner', **options):
                run = self.start(owner['name'], 'failed-' + str(index))
                self.assertIsNone(run)
                run = self.sessions.list_all('failed-' + str(index))[0]
                self.assertEqual(run['state'], 'interrupted')
                self.assertIsNone(run.get('active_invocation'))
        self.assertEqual(self.trigger.queue.for_identity(owner), [])
