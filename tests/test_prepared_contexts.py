"""Child-only preparation repair and pre-activation fresh-CLI read isolation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import AgentTrigger
from api_seat_runtime import SeatManager
from api_seats import SeatStore, atomic_json
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict


class PreparedContextTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.providers = {'api': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1'},
            'cli': {'command': sys.executable, 'cwd': str(self.root), 'mcp_inject': 'env',
                    'mcp_env_var': 'PREPARED_TEST_SETTINGS', 'cli_fresh_context_verified': True,
                    'cli_fresh_context_args': ['--context-id', '{context_id}']}}
        common = {'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        self.seats = SeatStore(self.root, self.providers)
        self.seats.save({'id': 'team', 'name': 'Team', 'seats': [
            dict(common, id='one', name='First API', adapter='openai-compatible', provider='api', model='one'),
            dict(common, id='two', name='Replacement API', adapter='openai-compatible', provider='api', model='two'),
            dict(common, id='cli', name='Fresh CLI', adapter='cli', provider='cli', model=None)]})
        self.registry = RuntimeRegistry(str(self.root))
        self.manager = SeatManager(ROOT, {'server': {'port': 18300}}, self.seats, self.registry,
                                   startup_timeout=5, monitor=False)
        self.processes, self.spawn_snapshots = [], []
        def spawn(command, **options):
            snapshot = Path(command[command.index('--seat-file') + 1])
            self.spawn_snapshots.append(json.loads(snapshot.read_text('utf-8')))
            process = Mock()
            process.poll.return_value = None
            process.returncode = None
            def ended(*args, **kwargs):
                process.poll.return_value = 0
                process.returncode = 0
                return 0
            process.wait.side_effect = ended
            process.terminate.side_effect = ended
            self.processes.append(process)
            return process
        self.patcher = patch('api_seat_runtime.subprocess.Popen', side_effect=spawn)
        self.spawn = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.manager.shutdown)
        self.one = self.ready('one')
        self.two = self.ready('two')
        self.sessions = SessionStore(str(self.root / 'session_runs.json'))
        self.sessions.save_custom_template({'id': 'review', 'name': 'Review', 'roles': ['reviewer'],
            'phases': [{'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Read source.', 'is_output': True}]})
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry, seat_manager=self.manager)
        parent = self.engine.start_session('review', 'general', {'reviewer': self.one['name']}, 'operator',
            goal='Keep the goal.', input_text='OLD_SOURCE and OLD_RESULTS remain historical.')
        self.engine.stop_session(parent['id'])
        self.engine.reconcile_stops()
        self.parent_id = parent['id']
        self.parent_request_id = uuid.uuid4().hex
        self.child = self.sessions.prepare_restart(self.parent_id, 'NEW_SOURCE corrected café\r\n日本語', self.parent_request_id)
        self.child_id = self.child['id']

    def ready(self, seat_id):
        launched = self.manager.launch('team', seat_id)
        attempt = self.manager.attempts['team/' + seat_id]
        instance = self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'], {'attempt': launched['attempt'], 'state': 'ready', 'name': instance['name'],
            'adapter_connected': True, 'authentication': 'unknown', 'confirmed_model': None, 'updated_at': time.time()})
        self.assertEqual(self.manager.inspect('team', seat_id)['state'], 'ready')
        return instance

    def current(self):
        return self.sessions.get(self.child_id)

    def immutable(self, child=None):
        child = child or self.current()
        return {key: deepcopy(child[key]) for key in ('run_id', 'input_snapshot', 'input_revision', 'design_snapshot',
            'design_revision', 'goal', 'rules_snapshot', 'rules_revision', 'parent_run_id', 'lineage_root_id')}

    def prepare(self, request_id=None, **kwargs):
        return self.engine.prepare_contexts(self.child_id, request_id or uuid.uuid4().hex, **kwargs)

    def test_api_context_preparation_is_child_only_and_does_not_dispatch(self):
        original = self.immutable()
        result = self.prepare()
        self.assertEqual(result['id'], self.child_id)
        self.assertEqual(result['state'], 'prepared')
        self.assertEqual(result['preparation_contexts']['reviewer']['state'], 'ready')
        self.assertFalse(result['dispatch_eligible'])
        self.assertFalse(result.get('active_invocation'))
        self.assertEqual(self.immutable(), original)
        self.assertEqual(len(self.processes), 2)

    def test_fresh_cli_scope_exists_before_child_backlink_and_denies_shared_reads(self):
        cli = self.ready('cli')
        provenance = self.manager.launch_provenance(cli)
        old = self.manager.attempts['team/cli']
        old['process'].poll.return_value = 0
        old['process'].returncode = 0
        atomic_json(old['receipt'], {'attempt': old['id'], 'state': 'stopped', 'child_exit_code': 0,
                                    'name': cli['name'], 'adapter_connected': False})
        self.manager.inspect('team', 'cli')
        context_key = self.child['run_id'] + '.reviewer'
        prepared = self.manager.prepare_clean_context(provenance, context_key,
            binding={'child_run_id': self.child['run_id'], 'role': 'reviewer'})
        serialized = json.dumps(self.spawn_snapshots[-1])
        self.assertIn(self.child['run_id'], serialized)
        self.assertIn(context_key, serialized)
        self.assertIn('reviewer', serialized)
        fresh = self.manager.attempts[prepared['key']]
        instance = self.registry.register(fresh['base'])
        scope = self.manager.fresh_context_owner(instance)
        self.assertEqual(scope['child_run_id'], self.child['run_id'])
        self.assertEqual(scope['role'], 'reviewer')
        self.assertEqual(scope['context_key'], context_key)
        self.assertFalse(self.current().get('preparation_contexts'))
        self.messages.add('system', 'OLD_SOURCE OLD_RESULTS old job/summary context')
        self.assertEqual(self.engine.review_messages(instance), [], 'prepared CLI must never fall back to shared history')
        self.assertIsNone(self.engine.review_messages(self.one), 'a retained API supervisor keeps ordinary reads during a draft')

    def test_role_edit_records_history_and_old_request_retries_never_revert_it(self):
        original_packet = self.immutable()
        initial_request = uuid.uuid4().hex
        first = self.prepare(initial_request)
        old_context = deepcopy(first['preparation_contexts']['reviewer'])
        edit_request = uuid.uuid4().hex
        edited = self.prepare(edit_request, replacements={'reviewer': self.two['identity_id']})
        self.assertEqual(edited['participant_bindings']['reviewer']['identity_id'], self.two['identity_id'])
        self.assertEqual(edited['preparation_contexts']['reviewer']['identity_id'], self.two['identity_id'])
        history = deepcopy(edited['reassigned_contexts_history'])
        self.assertIn(self.one['identity_id'], json.dumps(history))
        self.assertIn(old_context['launch_attempt'], json.dumps(history))
        # The first request's raw intent was no edits. It must not restore the
        # older role after a later independently identified edit succeeds.
        retried = self.prepare(initial_request)
        self.assertEqual(retried['participant_bindings'], edited['participant_bindings'])
        self.assertEqual(retried['preparation_contexts'], edited['preparation_contexts'])
        self.assertEqual(retried['reassigned_contexts_history'], history)
        parent_retry = self.engine.correct_and_restart(self.parent_id,
            self.child['input_snapshot']['text'], self.parent_request_id)
        self.assertEqual(parent_retry['id'], self.child_id)
        self.assertEqual(parent_retry['participant_bindings'], edited['participant_bindings'])
        self.assertEqual(self.immutable(), original_packet)
        self.assertEqual(len(self.processes), 2)

    def test_changed_same_context_request_intent_conflicts_without_reassignment(self):
        request_id = uuid.uuid4().hex
        first = self.prepare(request_id, replacements={'reviewer': self.two['identity_id']})
        with self.assertRaises(EventConflict):
            self.prepare(request_id, replacements={'reviewer': self.one['identity_id']})
        self.assertEqual(self.current()['participant_bindings'], first['participant_bindings'])
        self.assertEqual(self.current()['reassigned_contexts_history'], first['reassigned_contexts_history'])
        self.assertEqual(len(self.processes), 2)

    def test_failed_original_context_can_be_repaired_by_secondary_api_without_new_source(self):
        original_packet = self.immutable()
        process = self.manager.attempts['team/one']['process']
        process.poll.return_value = 23
        process.returncode = 23
        failed = self.prepare()
        self.assertEqual(failed['state'], 'prepared')
        self.assertEqual(failed['preparation_contexts']['reviewer']['state'], 'blocked')
        self.assertFalse(failed['dispatch_eligible'])
        repaired = self.prepare(replacements={'reviewer': self.two['identity_id']})
        self.assertEqual(repaired['id'], self.child_id)
        self.assertEqual(repaired['preparation_contexts']['reviewer']['state'], 'ready')
        self.assertEqual(repaired['participant_bindings']['reviewer']['identity_id'], self.two['identity_id'])
        self.assertEqual(self.immutable(), original_packet)
        self.assertEqual(len(self.sessions.list_all()), 2)
        self.assertEqual(len(self.processes), 2, 'API context repair must not spawn another supervisor')

    def test_unrelated_queued_work_blocks_reassignment_without_stopping_peer(self):
        before = deepcopy(self.current()['participant_bindings'])
        busy = self.trigger.trigger_sync(self.two['name'], prompt='Unrelated queued work', channel='elsewhere')
        with self.assertRaises(EventConflict):
            self.prepare(replacements={'reviewer': self.two['identity_id']})
        self.assertEqual(self.current()['participant_bindings'], before)
        self.assertEqual(self.trigger.queue.owned(self.two, busy['envelope']['dispatch_id'])['state'], 'queued')
        self.assertEqual(len(self.processes), 2)
        self.processes[1].wait.assert_not_called()
        self.processes[1].terminate.assert_not_called()

    def test_activation_and_permanent_stop_freeze_role_edits(self):
        prepared = self.prepare()
        self.engine.activate_restart(self.child_id)
        active = deepcopy(self.current())
        self.assertTrue(active['dispatch_eligible'])
        with self.assertRaises(EventConflict):
            self.prepare(replacements={'reviewer': self.two['identity_id']})
        self.assertEqual(self.current()['participant_bindings'], active['participant_bindings'])
        self.engine.stop_session(self.child_id)
        with self.assertRaises(EventConflict):
            self.prepare(replacements={'reviewer': self.two['identity_id']})
        self.assertTrue(self.current()['stop_id'])
        self.assertFalse(self.current()['dispatch_eligible'])
        self.assertEqual(self.current()['participant_bindings'], active['participant_bindings'])

    def test_failed_atomic_context_bookkeeping_preserves_disk_and_memory(self):
        path = self.root / 'session_runs.json'
        before, disk = deepcopy(self.current()), path.read_bytes()
        with patch('session_store.atomic_json', side_effect=OSError('fixture context bookkeeping failure')):
            with self.assertRaises(OSError):
                self.prepare(replacements={'reviewer': self.two['identity_id']})
        self.assertEqual(self.current(), before)
        self.assertEqual(path.read_bytes(), disk)
        self.assertEqual(len(self.processes), 2)

    def test_invalid_role_or_raw_settings_cannot_inject_source_or_credentials(self):
        original_packet = self.immutable()
        invalid = ({'unknown-role': self.two['identity_id']},
                   {'reviewer': {'identity_id': self.two['identity_id'], 'input_text': 'INJECTED SOURCE',
                                 'api_key': 'INJECTED CREDENTIAL', 'effective': {'provider': 'untrusted'}}})
        for replacements in invalid:
            with self.subTest(replacements=replacements), self.assertRaises(EventConflict):
                self.prepare(replacements=replacements)
        self.assertEqual(self.immutable(), original_packet)
        text = (self.root / 'session_runs.json').read_text('utf-8')
        self.assertNotIn('INJECTED SOURCE', text)
        self.assertNotIn('INJECTED CREDENTIAL', text)
        self.assertEqual(len(self.processes), 2)


if __name__ == '__main__':
    unittest.main()
