"""Startup uses one stable boot fence before publication and monitoring."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
from agents import AgentTrigger
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore


class RestartStartupTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = SessionStore(str(self.root / 'session_runs.json'))
        self.registry = RuntimeRegistry(str(self.root))
        self.messages = MessageStore(str(self.root / 'messages.jsonl'))
        self.trigger = AgentTrigger(self.registry, str(self.root))
        self.boot = uuid.uuid4().hex
        self.manager = SimpleNamespace(boot_id=self.boot, launch_provenance=lambda instance: None)
        self.engine = SessionEngine(self.store, self.messages, self.trigger, self.registry, seat_manager=self.manager)

    def test_resume_delegates_reconciliation_using_shared_manager_boot_every_time(self):
        with patch.object(self.engine, 'reconcile_restart') as reconcile:
            self.engine.resume_active_sessions()
            self.engine.resume_active_sessions()
        self.assertEqual(reconcile.call_count, 2)
        for call in reconcile.call_args_list:
            self.assertEqual(call.kwargs['boot_id'], self.boot)

    def test_resume_accepts_explicit_boot_instead_of_stop_projection_only_fallback(self):
        boot = uuid.uuid4().hex
        with patch.object(self.engine, 'reconcile_restart') as reconcile:
            self.engine.resume_active_sessions(boot_id=boot)
        reconcile.assert_called_once_with(boot_id=boot)

    def test_configure_inventories_and_reconciles_before_any_background_publication(self):
        events = []
        manager = Mock()
        manager.boot_id = self.boot
        manager.reconcile_runtime.side_effect = lambda: events.append('inventory')
        engine = Mock()
        engine.resume_active_sessions.side_effect = lambda **kw: events.append('resume')
        thread = Mock()
        thread.start.side_effect = lambda: events.append('background_start')
        cfg = {'server': {'data_dir': str(self.root / 'configured'), 'host': '127.0.0.1', 'port': 18300},
               'images': {'upload_dir': str(self.root / 'uploads')}, 'agents': {}}
        globals_to_restore = ('store', 'rules', 'summaries', 'jobs', 'schedules', 'router', 'agents',
                             'registry', 'session_store', 'session_engine', 'config', 'api_seat_store', 'api_seat_manager')
        with ExitStack() as stack:
            for name in globals_to_restore:
                stack.enter_context(patch.object(app, name, None))
            stack.enter_context(patch.object(app, 'room_settings', {}))
            stack.enter_context(patch.object(app, '_install_security_middleware'))
            stack.enter_context(patch.object(app, '_load_settings'))
            stack.enter_context(patch.object(app, '_load_hats'))
            stack.enter_context(patch('api_seat_runtime.SeatManager', return_value=manager))
            stack.enter_context(patch.object(app, 'SessionEngine', return_value=engine))
            stack.enter_context(patch.object(app.threading, 'Thread', return_value=thread))
            app.configure(cfg, session_token='isolated-operator-token')
        self.assertIn('inventory', events)
        self.assertIn('resume', events)
        self.assertIn('background_start', events)
        self.assertLess(events.index('inventory'), events.index('resume'))
        self.assertLess(events.index('resume'), events.index('background_start'))
        engine.resume_active_sessions.assert_called_once_with(boot_id=self.boot)

    def test_bootstrapped_monitor_reconciles_same_boot_before_observing_turns(self):
        events = []
        engine = Mock()
        engine._restart_boot_id = self.boot
        engine._recovery_policy = {'monitor_interval': .01}
        engine.reconcile_restart.side_effect = lambda **kw: events.append(('reconcile', kw['boot_id']))
        async def exercise():
            observed = asyncio.Event()
            loop = asyncio.get_running_loop()
            def monitor():
                events.append(('monitor', None))
                loop.call_soon_threadsafe(observed.set)
                return []
            engine.monitor_turns.side_effect = monitor
            try:
                await app.start_turn_monitor()
                await asyncio.wait_for(observed.wait(), timeout=2)
            finally:
                await app.stop_turn_monitor()
        with ExitStack() as stack:
            stack.enter_context(patch.object(app, 'session_engine', engine))
            stack.enter_context(patch.object(app, 'api_seat_manager', self.manager))
            for name in ('_turn_monitor_task', '_turn_monitor_stop', '_turn_monitor_wake', '_turn_monitor_loop'):
                stack.enter_context(patch.object(app, name, None))
            asyncio.run(exercise())
        self.assertTrue(events)
        for index, event in enumerate(events):
            if event[0] == 'monitor':
                self.assertGreater(index, 0)
                self.assertEqual(events[index - 1], ('reconcile', self.boot))

    def test_repeated_startup_preserves_held_timing_stop_and_new_runtime_sessions(self):
        self.store.save_custom_template({'id': 'one', 'name': 'One', 'roles': ['r'],
            'phases': [{'name': 'Work', 'participants': ['r'], 'prompt': 'Read exact source.', 'is_output': True}]})
        self.registry.seed({'seat': {'type': 'api'}})
        owner = self.registry.register('seat')
        started = self.engine.start_session('one', 'held', {'r': owner['name']}, 'operator', input_text='Exact café\r\nsource')
        old = started['active_invocation']
        self.trigger.queue.claim(owner, 'original-worker')
        self.trigger.queue.acknowledge(owner, old['dispatch_id'], 'original-worker')
        self.engine.monitor_turns(now=time.time() + 1000)
        checkpoint = self.store.get(started['id'])['turn_recovery']['checkpoint_id']
        self.engine.wait_turn(started['id'], checkpoint, old['attempt_id'], 2000)
        stopped = self.engine.start_session('one', 'stopped', {'r': 'Human'}, 'operator')
        self.engine.stop_session(stopped['id'])
        self.engine.reconcile_stops()
        before = deepcopy(self.store.get(started['id']))
        stop_id = self.store.get(stopped['id'])['stop_id']
        queue = (self.root / 'queue/ledger.json').read_bytes()
        self.engine.resume_active_sessions(boot_id=self.boot)
        self.engine.resume_active_sessions()
        current = self.store.get(started['id'])
        self.assertEqual(current['active_invocation'], before['active_invocation'])
        self.assertEqual(current['turn_recovery']['checkpoint_id'], checkpoint)
        self.assertEqual(current['turn_recovery']['actions'], before['turn_recovery']['actions'])
        self.assertEqual(current['turn_recovery']['deferred_until'], before['turn_recovery']['deferred_until'])
        self.assertEqual(current['input_snapshot'], before['input_snapshot'])
        self.assertEqual((self.root / 'queue/ledger.json').read_bytes(), queue)
        self.assertEqual(self.store.get(stopped['id'])['stop_id'], stop_id)
        self.assertFalse(self.store.get(stopped['id'])['dispatch_eligible'])
        # A new explicit run belongs to this already-bootstrapped coordinator,
        # even before its newly launched managed worker finishes boot echo.
        self.manager.launch_provenance = lambda instance: {'key': 'team/api', 'identity_id': instance['identity_id'],
            'launch_attempt': uuid.uuid4().hex, 'effective': {'seat': {'adapter': 'openai-compatible'}}}
        self.manager.restart_readiness = lambda *args, **kw: {'state': 'unverified', 'process_verified': False}
        fresh = self.engine.start_session('one', 'new-runtime', {'r': owner['name']}, 'operator')
        self.assertIsNotNone(fresh['active_invocation'])
        self.engine.resume_active_sessions()
        current = self.store.get(fresh['id'])
        self.assertEqual(current['state'], 'waiting')
        self.assertTrue(current['dispatch_eligible'])
        self.assertEqual(current['active_invocation']['attempt_id'], fresh['active_invocation']['attempt_id'])


if __name__ == '__main__':
    unittest.main()
