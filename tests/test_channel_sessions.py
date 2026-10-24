"""Real session/catalog boundaries with explicit doubles, no native/HTTP claims."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import Mock, patch
import uuid

from agents import AgentTrigger
from channel_lifecycle import ChannelInactive, ChannelUnavailable
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore
from turn_events import EventConflict
from tests import test_channel_import as fixture


class ChannelSessionTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelImportTests.setUp(self)
        self.sessions.save_custom_template({'id': 'human-test', 'name': 'Human review',
            'roles': ['reader'], 'phases': [{'name': 'Read', 'participants': ['reader'],
                                            'prompt': 'Read exact source.', 'is_output': True}]})
        self.engine.bind_channel_policy(lambda: self.service)

    def start(self, channel='review'):
        return self.engine.start_session('human-test', channel, {'reader': 'alice'},
                                         'operator', input_text='Exact source\r\nretained')

    def effects(self):
        return ({p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()},
                self.sessions._next_id, deepcopy(self.sessions._sessions),
                deepcopy(self.sessions._templates))

    def assert_refusal(self, call, expected=ChannelInactive):
        before, error = self.effects(), None
        try:
            call()
        except Exception as exc:
            error = exc
        self.assertEqual(self.effects(), before)
        self.assertIsInstance(error, expected)

    def test_archived_start_refuses_before_session_id_template_brief_or_queue_effects(self):
        self.catalog.set_state('review', 'archived', expected_revision=0)
        self.assert_refusal(self.start)

    def test_archived_stopped_parent_restart_refuses_before_child_or_context_calls(self):
        parent = self.start()
        self.engine.stop_session(parent['id'])
        self.engine.reconcile_stops()
        self.assertEqual(self.sessions.get(parent['id'])['state'], 'stopped')
        self.catalog.set_state('review', 'archived', expected_revision=0)
        manager = Mock()
        with patch.object(self.engine, '_seat_manager', manager):
            self.assert_refusal(lambda: self.engine.correct_and_restart(parent['id'],
                'Genuinely edited source', uuid.uuid4().hex))
            self.assertEqual(manager.mock_calls, [])

    def prepared(self):
        parent = self.start()
        self.engine.stop_session(parent['id'])
        self.engine.reconcile_stops()
        return self.engine.correct_and_restart(parent['id'], 'Edited exact source', uuid.uuid4().hex)

    def test_held_unregistered_and_malformed_start_destinations_have_no_effects(self):
        self.catalog.begin('rename', 'review', 'renamed', request_id=uuid.uuid4().hex, expected_revision=0)
        for channel, error in [('review', ChannelInactive), ('renamed', ChannelInactive),
                               ('missing', ChannelInactive), ('Bad/name', ValueError)]:
            with self.subTest(channel=channel):
                self.assert_refusal(lambda: self.start(channel), error)

    def test_corrupt_catalog_blocks_all_four_primaries_without_reset_or_context_calls(self):
        child = self.prepared()
        self.catalog.path.write_text('{broken', encoding='utf-8')
        manager = Mock()
        with patch.object(self.engine, '_seat_manager', manager):
            calls = [self.start,
                lambda: self.engine.correct_and_restart(1, 'Another edit', uuid.uuid4().hex),
                lambda: self.engine.prepare_contexts(child['id'], uuid.uuid4().hex),
                lambda: self.engine.activate_restart(child['id'])]
            for index, call in enumerate(calls):
                with self.subTest(operation=index):
                    self.assert_refusal(call, ChannelUnavailable)
            self.assertEqual(manager.mock_calls, [])

    def test_prepared_child_context_and_activation_use_stored_archived_channel(self):
        child = self.prepared()
        self.assertEqual(child['channel'], 'review')
        self.catalog.set_state('review', 'archived', expected_revision=0)
        manager = Mock()
        with patch.object(self.engine, '_seat_manager', manager):
            for call in [lambda: self.engine.prepare_contexts(child['id'], uuid.uuid4().hex),
                         lambda: self.engine.activate_restart(child['id'])]:
                self.assert_refusal(call)
            self.assertEqual(manager.mock_calls, [])

    def test_retired_stopped_parent_never_redirects_restart_to_general(self):
        parent = self.start()
        self.engine.stop_session(parent['id'])
        self.engine.reconcile_stops()
        # Explicit catalog-history boundary, not a claim of configured deletion migration.
        request = uuid.uuid4().hex
        self.catalog.begin('delete', 'review', None, request_id=request, expected_revision=0)
        for step in ('todos', 'messages', 'settings'):
            self.catalog.complete_step(request, step)
        self.catalog.finish(request)
        self.assert_refusal(lambda: self.engine.correct_and_restart(parent['id'],
            'Changed exact source', uuid.uuid4().hex))
        self.assertEqual(self.sessions.get(parent['id'])['channel'], 'review')
        self.assertIsNone(self.engine.get_active('general'))

    def test_inactive_typed_admission_receipts_stop_and_reads_remain_available(self):
        self.registry.seed({'codex': {'label': 'Codex'}})
        owner = self.registry.register('codex')
        run = self.engine.start_session('human-test', 'review', {'reader': 'codex'},
                                        'operator', input_text='Manual-client source')
        invocation = run['active_invocation']
        record = self.trigger.queue.claim(owner, 'explicit-algorithm-consumer')
        dispatch = record['envelope']['dispatch_id']
        self.catalog.set_state('review', 'archived', expected_revision=0)
        self.trigger.queue.acknowledge(owner, dispatch, 'explicit-algorithm-consumer')
        result = self.engine.admit_event(invocation['brief_id'], 'final', 'Exact retained\r\nfinal', owner)
        self.assertEqual(result['status'], 'admitted')
        saved = self.sessions.get(run['id'])
        self.assertEqual(saved['admitted_events'][0]['content'], 'Exact retained\r\nfinal')
        self.assertEqual(saved['state'], 'complete')
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        self.trigger.queue.release(owner, dispatch, 'explicit-algorithm-consumer')
        self.assertEqual(self.engine.restart_status(run['id'])['id'], run['id'])
        peer = self.start('peer')
        self.catalog.set_state('peer', 'archived', expected_revision=1)
        self.engine.stop_session(peer['id'])
        self.engine.reconcile_stops()
        self.assertEqual(self.sessions.get(peer['id'])['state'], 'stopped')

    def test_active_peer_and_unbound_standalone_preserve_start_restart_activation(self):
        self.catalog.set_state('review', 'archived', expected_revision=0)
        peer = self.start('peer')
        self.engine.stop_session(peer['id'])
        self.engine.reconcile_stops()
        child = self.engine.correct_and_restart(peer['id'], 'Corrected peer source', uuid.uuid4().hex)
        active = self.engine.activate_restart(child['id'])
        self.assertNotEqual(active['state'], 'prepared')
        self.assertEqual(self.sessions.get(child['id'])['channel'], 'peer')
        standalone_store = SessionStore(str(self.root / 'standalone' / 'runs.json'))
        standalone_store.save_custom_template(self.sessions.get_template('human-test'))
        standalone = SessionEngine(standalone_store, MessageStore(str(self.root / 'standalone' / 'messages.jsonl')),
            AgentTrigger(self.registry, str(self.root / 'standalone')), self.registry)
        old = standalone.start_session('human-test', 'review', {'reader': 'alice'}, 'operator', input_text='Legacy')
        self.assertIsNotNone(old)
        self.assertEqual(old['channel'], 'review')

    def test_startup_skips_archived_run_before_checkpoint_and_same_boot_reopen_is_idempotent(self):
        run = self.start()
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.effects()
        boot = uuid.uuid4().hex
        self.engine.reconcile_restart(boot_id=boot, now=100)
        self.assertEqual(self.effects(), before)
        self.assertNotIn('restart_recovery', self.sessions.get(run['id']))
        self.catalog.set_state('review', 'active', expected_revision=1)
        self.engine.reconcile_restart(boot_id=boot, now=100)
        current = self.sessions.get(run['id'])
        self.assertEqual(current['active_invocation'], run['active_invocation'])
        stable = self.effects()
        self.engine.reconcile_restart(boot_id=boot, now=100)
        self.assertEqual(self.effects(), stable)

    def test_startup_pending_intent_run_is_unchanged_while_peer_reconciles(self):
        held, peer = self.start(), self.start('peer')
        self.catalog.begin('rename', 'review', 'held-new', request_id=uuid.uuid4().hex, expected_revision=0)
        before = deepcopy(self.sessions.get(held['id']))
        brief_paths = {p.name: p.read_bytes() for p in self.root.rglob('*.json') if 'brief' in str(p)}
        self.engine.reconcile_restart(boot_id=uuid.uuid4().hex, now=100)
        self.assertEqual(self.sessions.get(held['id']), before)
        self.assertEqual(self.sessions.get(peer['id'])['restart_recovery']['status'], 'verified')
        self.assertEqual({p.name: p.read_bytes() for p in self.root.rglob('*.json') if 'brief' in str(p)}, brief_paths)

    def test_missing_run_keeps_existing_conflict_without_manager_or_file_changes(self):
        for call in [lambda: self.engine.correct_and_restart(999, 'Edited source', uuid.uuid4().hex),
                     lambda: self.engine.prepare_contexts(999, uuid.uuid4().hex),
                     lambda: self.engine.activate_restart(999)]:
            self.assert_refusal(call, EventConflict)

    def test_start_holds_engine_catalog_boundary_until_invocation_is_durable(self):
        entered, release, checking = threading.Event(), threading.Event(), threading.Event()
        original = self.sessions.create
        def gated(*args, **kwargs):
            entered.set()
            self.assertTrue(release.wait(2))
            return original(*args, **kwargs)
        def preview():
            checking.set()
            return self.service.preview('archive', 'review')
        with patch.object(self.sessions, 'create', side_effect=gated):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.start)
                try:
                    self.assertTrue(entered.wait(2))
                    second = pool.submit(preview)
                    self.assertTrue(checking.wait(2))
                    self.assertFalse(second.done())
                finally:
                    release.set()
                started, view = first.result(2), second.result(2)
        self.assertIsNotNone(self.sessions.get(started['id'])['active_invocation'])
        self.assertTrue(view['blockers'])


if __name__ == '__main__':
    unittest.main()
