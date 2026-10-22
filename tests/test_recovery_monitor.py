"""Server monitoring detects dropped events without a browser polling status."""
from contextlib import ExitStack
import time
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app


class RecoveryMonitorTests(unittest.TestCase):
    def test_new_session_event_wakes_monitor_before_long_poll_interval(self):
        from tests.test_turn_recovery import TurnRecoveryTests
        f = TurnRecoveryTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.engine._recovery_policy['monitor_interval'] = 1
        f.sessions.on_change(app._on_session_change)
        api = FastAPI()
        api.on_event('startup')(app.start_turn_monitor)
        api.on_event('shutdown')(app.stop_turn_monitor)
        with patch.object(app, 'session_engine', f.engine), patch.object(app, '_event_loop', None), TestClient(api):
            deadline = time.monotonic() + .5
            while f.current()['active_invocation']['monitoring']['last_event']['state'] == 'bound' and time.monotonic() < deadline:
                time.sleep(.005)
            f.sessions._event_update(f.session_id, lambda s: s['active_invocation']['monitoring'].update(ack_deadline=time.time() - 1))
            deadline = time.monotonic() + .3
            while f.current()['state'] != 'stalled' and time.monotonic() < deadline:
                time.sleep(.005)
            self.assertEqual(f.current()['state'], 'stalled')

    def test_startup_monitor_persists_stall_and_shutdown_joins_task(self):
        from tests.test_turn_recovery import TurnRecoveryTests
        f = TurnRecoveryTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.engine._recovery_policy['monitor_interval'] = .01
        f.sessions._event_update(f.session_id, lambda s: s['active_invocation']['monitoring'].update(ack_deadline=time.time() - 1))
        api = FastAPI()
        api.on_event('startup')(app.start_turn_monitor)
        api.on_event('shutdown')(app.stop_turn_monitor)
        with ExitStack() as stack:
            stack.enter_context(patch.object(app, 'session_engine', f.engine))
            with TestClient(api):
                deadline = time.monotonic() + 1
                while f.current()['state'] != 'stalled' and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(f.current()['turn_recovery']['reason'], 'missing_ack')
                self.assertIsNotNone(app._turn_monitor_task)
            self.assertIsNone(app._turn_monitor_task)
