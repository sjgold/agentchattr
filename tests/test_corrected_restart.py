"""Corrected lineage is atomic, prepared is not stopped, and review context is clean."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import AgentTrigger
from registry import RuntimeRegistry
from review_brief import BriefError, brief_messages, build_brief, freeze_inputs
from rules import RuleStore
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventAccessError, EventConflict

OLD_SOURCE = 'OLD_SOURCE mistaken café text\r\n@all is source data.'
NEW_SOURCE = 'NEW_SOURCE corrected 日本語 e\u0301 🐙\r\nExact replacement source.'


class CorrectedRestartTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'session_runs.json'
        self.sessions = SessionStore(str(self.path))
        self.template = {'id': 'human-review', 'name': 'Human review', 'roles': ['reviewer', 'editor'],
            'phases': [{'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Inspect source.'},
                       {'name': 'Decide', 'participants': ['editor'], 'prompt': 'Explain decision.', 'is_output': True}]}
        self.sessions.save_custom_template(self.template)
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.registry = RuntimeRegistry(str(self.root))
        self.registry.seed({'helper': {'label': 'Unrelated helper'}})
        self.helper = self.registry.register('helper')
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.rules = RuleStore(str(self.root / 'rules.json'))
        rule = self.rules.propose('Keep exact source quotations.', 'operator')
        self.rules.activate(rule['id'])
        self.engine = SessionEngine(self.sessions, self.messages, self.trigger, self.registry, rules_store=self.rules)
        started = self.engine.start_session('human-review', 'general', {'reviewer': 'alice', 'editor': 'bob'},
            'operator', goal='Retained goal ' * 50, input_text=OLD_SOURCE)
        self.parent_id = started['id']
        self.old_brief = started['active_invocation']['brief_id']
        self.engine.human_result(self.parent_id, self.old_brief, 'OLD_RESULT accepted human finding.', submitted_by='alice')
        self.engine.stop_session(self.parent_id)
        self.engine.reconcile_stops()
        self.parent = deepcopy(self.sessions.get(self.parent_id))
        self.assertEqual(self.parent['state'], 'stopped')
        self.request_id = uuid.uuid4().hex

    def prepare(self, source=NEW_SOURCE, request_id=None, **kwargs):
        return self.sessions.prepare_restart(self.parent_id, source, request_id or self.request_id, **kwargs)

    def test_review_messages_omit_all_shared_chat_but_keep_new_source_and_own_results(self):
        session = {**freeze_inputs(self.template, goal='New review', input_text=NEW_SOURCE,
                                  rules={'epoch': 1, 'rules': ['Keep exact source quotations.']}),
                   'id': 99, 'channel': 'general', 'completion_protocol': 1}
        envelope = build_brief(session, 0, 0, 'alice', prior_results=[{'text': 'NEW_RUN_ONLY accepted result'}])
        envelope['completion_protocol'] = 1
        recent = [{'id': i, 'sender': 'human', 'text': 'OLD_SOURCE OLD_RESULT old summary'} for i in range(30)]
        messages = brief_messages(envelope, recent, 'alice')
        serialized = json.dumps(messages, ensure_ascii=False)
        self.assertNotIn('supplementary_chat', serialized)
        self.assertNotIn('OLD_SOURCE', serialized)
        self.assertNotIn('OLD_RESULT', serialized)
        self.assertIn('NEW_RUN_ONLY', serialized)
        source_message = next(json.loads(m['content']) for m in messages if m['role'] == 'user'
                              and json.loads(m['content']).get('kind') == 'untrusted_review_source')
        self.assertEqual(source_message['text'], NEW_SOURCE)

    def test_prepare_atomically_links_parent_to_new_frozen_prepared_child(self):
        child = self.prepare()
        parent = self.sessions.get(self.parent_id)
        self.assertEqual(parent['replaced_by_run_id'], child['run_id'])
        self.assertEqual(child['parent_run_id'], self.parent['run_id'])
        self.assertEqual(child['lineage_root_id'], self.parent['run_id'])
        self.assertEqual(child['request_id'], self.request_id)
        self.assertEqual(child['state'], 'prepared')
        self.assertTrue(child['prepared'])
        self.assertFalse(child['dispatch_eligible'])
        self.assertIsNone(child['stop_id'])
        self.assertNotEqual(child['run_id'], self.parent['run_id'])
        self.assertEqual(child['input_snapshot']['text'], NEW_SOURCE)
        self.assertEqual(child['input_revision'], hashlib.sha256(NEW_SOURCE.encode('utf-8')).hexdigest())
        for field in ('design_snapshot', 'design_revision', 'goal', 'rules_snapshot', 'rules_revision', 'cast', 'participant_bindings'):
            self.assertEqual(child[field], self.parent[field])
        for field in ('admitted_events', 'result_message_ids', 'quarantined_events', 'continuation_context'):
            self.assertEqual(child.get(field, []), [])
        self.assertFalse(child.get('active_invocation'))
        restored = SessionStore(str(self.path))
        self.assertEqual(restored.get(self.parent_id)['replaced_by_run_id'], restored.get(child['id'])['run_id'])

    def test_prepared_ineligibility_does_not_collide_with_permanent_stop_reconciliation(self):
        child = deepcopy(self.parent)
        child.update(id=self.parent_id + 1, run_id=uuid.uuid4().hex, state='prepared', prepared=True,
                     dispatch_eligible=False, stop_id=None, stopped_at=None, active_invocation=None,
                     admitted_events=[], result_message_ids=[], quarantined_events=[], continuation_context=[])
        child.pop('replaced_by_run_id', None)
        self.path.write_text(json.dumps([self.parent, child]), encoding='utf-8')
        restored = SessionStore(str(self.path))
        trigger = AgentTrigger(self.registry, str(self.root))
        engine = SessionEngine(restored, self.messages, trigger, self.registry)
        engine.reconcile_stops()
        self.assertIsNone(trigger.queue.claim(self.helper, 'unrelated-consumer'))
        self.assertEqual(restored.get(child['id'])['state'], 'prepared')
        self.assertIsNone(restored.get(child['id'])['stop_id'])

    def test_unchanged_invalid_or_oversize_source_preserves_parent_and_disk(self):
        before = self.path.read_bytes()
        snapshot = deepcopy(self.sessions.list_all())
        for source in (OLD_SOURCE, 'NUL\x00source', '\ud800', b'\xff', 'x' * (512 * 1024 + 1)):
            with self.subTest(source_type=type(source).__name__), self.assertRaises(BriefError):
                self.prepare(source=source)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(self.sessions.list_all(), snapshot)

    def test_same_request_is_idempotent_and_changed_payload_or_sibling_conflicts(self):
        child = self.prepare()
        repeated = self.prepare()
        self.assertEqual(repeated['id'], child['id'])
        self.assertEqual(repeated['run_id'], child['run_id'])
        self.assertEqual(len(self.sessions.list_all()), 2)
        before = self.path.read_bytes()
        with self.assertRaises(EventConflict):
            self.prepare(source=NEW_SOURCE + ' changed under same request')
        with self.assertRaises(EventConflict):
            self.prepare(request_id=uuid.uuid4().hex)
        self.assertEqual(self.path.read_bytes(), before)

    def test_concurrent_identical_requests_create_one_linked_child(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            children = list(pool.map(lambda _: self.prepare(), range(4)))
        self.assertEqual(len({child['id'] for child in children}), 1)
        self.assertEqual(len({child['run_id'] for child in children}), 1)
        self.assertEqual(len(self.sessions.list_all()), 2)
        self.assertEqual(self.sessions.get(self.parent_id)['replaced_by_run_id'], children[0]['run_id'])

    def test_failed_atomic_prepare_preserves_exact_disk_memory_and_next_id(self):
        disk, memory = self.path.read_bytes(), deepcopy(self.sessions.list_all())
        with patch('session_store.atomic_json', side_effect=OSError('fixture lineage write failure')):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual(self.sessions.list_all(), memory)
        child = self.prepare()
        self.assertEqual(child['id'], self.parent_id + 1)

    def test_frozen_snapshots_bindings_and_old_history_are_independent(self):
        self.sessions.get_template('human-review')['phases'][0]['prompt'] = 'Changed live design'
        self.rules.edit(self.rules.list_all()[0]['id'], text='Changed live rule')
        bindings = deepcopy(self.parent['participant_bindings'])
        child = self.prepare(participant_bindings=bindings)
        self.assertEqual(child['design_snapshot'], self.parent['design_snapshot'])
        self.assertEqual(child['rules_snapshot'], self.parent['rules_snapshot'])
        bindings['reviewer']['kind'] = 'mutated-input'
        child['design_snapshot']['phases'][0]['prompt'] = 'Mutated returned child'
        child['cast']['reviewer'] = 'changed-return'
        child['participant_bindings']['editor']['kind'] = 'mutated-return'
        persisted_child = next(value for value in self.sessions.list_all() if value['id'] != self.parent_id)
        self.assertEqual(persisted_child['design_snapshot'], self.parent['design_snapshot'])
        self.assertEqual(persisted_child['cast'], self.parent['cast'])
        self.assertEqual(persisted_child['participant_bindings'], self.parent['participant_bindings'])
        parent = self.sessions.get(self.parent_id)
        for field in ('input_snapshot', 'admitted_events', 'result_message_ids', 'quarantined_events', 'continuation_context'):
            self.assertEqual(parent[field], self.parent[field])
        self.assertTrue(any(message['text'] == 'OLD_RESULT accepted human finding.' for message in self.messages.get_recent(100)))

    def test_stopping_parent_rejects_while_unresolved_allows_only_preparation(self):
        active = self.engine.start_session('human-review', 'stopping-room',
            {'reviewer': 'alice', 'editor': 'bob'}, 'operator', input_text='Other original')
        self.engine.stop_session(active['id'])
        self.assertEqual(self.sessions.get(active['id'])['state'], 'stopping')
        with self.assertRaises(EventConflict):
            self.sessions.prepare_restart(active['id'], 'Other corrected', uuid.uuid4().hex)
        # A real persisted unresolved status can stage a child; execution remains
        # a separate context-validation action owned by engine.activate_restart.
        self.sessions.stop_outcome(active['id'], 'unresolved', [])
        child = self.sessions.prepare_restart(active['id'], 'Other corrected', uuid.uuid4().hex)
        self.assertEqual(child['state'], 'prepared')
        self.assertFalse(child['dispatch_eligible'])
        self.assertFalse(child.get('active_invocation'))

    def test_store_activation_is_atomic_and_rejects_reactivation(self):
        child = self.prepare()
        disk, memory = self.path.read_bytes(), deepcopy(self.sessions.list_all())
        with patch('session_store.atomic_json', side_effect=OSError('fixture activation write failure')):
            with self.assertRaises(OSError):
                self.sessions.activate_restart(child['id'])
        self.assertEqual(self.path.read_bytes(), disk)
        self.assertEqual(self.sessions.list_all(), memory)
        activated = self.sessions.activate_restart(child['id'])
        self.assertEqual(activated['state'], 'active')
        self.assertTrue(activated['dispatch_eligible'])
        with self.assertRaises(EventConflict):
            self.sessions.activate_restart(child['id'])

    def test_engine_prepares_only_then_explicit_activation_binds_fresh_human_turn(self):
        child = self.engine.correct_and_restart(self.parent_id, NEW_SOURCE, self.request_id)
        self.assertEqual(child['state'], 'prepared')
        self.assertFalse(child['dispatch_eligible'])
        self.assertFalse(child.get('active_invocation'))
        self.assertTrue(all(value['kind'] == 'human' for value in child['participant_bindings'].values()))
        self.engine.activate_restart(child['id'])
        current = self.sessions.get(child['id'])
        invocation = current['active_invocation']
        self.assertTrue(current['dispatch_eligible'])
        self.assertTrue(invocation['human'])
        self.assertNotEqual(invocation['brief_id'], self.parent['active_invocation']['brief_id'])
        self.assertNotEqual(invocation['attempt_id'], self.parent['active_invocation']['attempt_id'])
        self.assertNotEqual(invocation['turn_id'], self.parent['active_invocation']['turn_id'])
        brief = self.sessions.briefs.get(invocation['brief_id'], operator=True)
        self.assertEqual(brief['source'], NEW_SOURCE)
        self.assertEqual(brief['prior_results'], [])
        self.assertEqual(brief.get('continuation_context', []), [])
        self.assertIsNone(self.trigger.queue.claim(self.helper, 'no-human-dispatch'))

    def test_prepared_child_reserves_channel_and_remains_operator_visible(self):
        child = self.prepare()
        self.assertEqual(self.engine.get_active('general')['id'], child['id'])
        competing = self.engine.start_session('human-review', 'general',
            {'reviewer': 'alice', 'editor': 'bob'}, 'operator', input_text='Unrelated overlapping review')
        self.assertIsNone(competing)
        self.assertEqual(len(self.sessions.list_all()), 2)

    def test_stop_during_preparation_is_permanent_and_activation_never_revives_it(self):
        child = self.prepare()
        stopped = self.engine.stop_session(child['id'])
        self.assertRegex(stopped['stop_id'], r'^[0-9a-f]{32}$')
        self.engine.reconcile_stops()
        for activate in (self.sessions.activate_restart, self.engine.activate_restart):
            with self.subTest(activate=activate.__qualname__), self.assertRaises(EventConflict):
                activate(child['id'])
        permanent = self.sessions.get(child['id'])
        self.assertEqual(permanent['stop_id'], stopped['stop_id'])
        self.assertFalse(permanent['dispatch_eligible'])
        self.assertFalse(permanent.get('active_invocation'))

    def test_old_brief_cannot_submit_to_replacement_and_parent_never_creates_siblings(self):
        child = self.engine.correct_and_restart(self.parent_id, NEW_SOURCE, self.request_id)
        self.engine.activate_restart(child['id'])
        old_current = self.parent['active_invocation']['brief_id']
        with self.assertRaises(EventConflict):
            self.engine.human_result(self.parent_id, old_current, 'Late old human result', submitted_by='bob')
        with self.assertRaises(EventAccessError):
            self.engine.human_result(child['id'], old_current, 'Wrong lineage result', submitted_by='bob')
        self.assertEqual(self.sessions.get(child['id'])['admitted_events'], [])
        self.engine.stop_session(child['id'])
        self.engine.reconcile_stops()
        with self.assertRaises(EventConflict):
            self.sessions.prepare_restart(self.parent_id, NEW_SOURCE + ' sibling', uuid.uuid4().hex)
        grandchild = self.sessions.prepare_restart(child['id'], NEW_SOURCE + ' next correction', uuid.uuid4().hex)
        self.assertEqual(grandchild['parent_run_id'], child['run_id'])
        self.assertEqual(grandchild['lineage_root_id'], self.parent['run_id'])


if __name__ == '__main__':
    unittest.main()
