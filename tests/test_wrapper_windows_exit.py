"""Ticket #4 (AT-02/03): Windows runner must surface real child exit status.

Baseline bug: run_agent() on Windows swallows the child's actual exit code
(never returns it), starts the queue watcher unconditionally before the
process is even spawned (so a failed spawn still "arms" injection), and does
not guarantee pid_holder is cleared when wait() itself fails. These tests
pin the ticket #4 contract: real exit code returned, watcher started only
after a successful spawn, and pid_holder cleared on both normal exit and a
failed wait.

Native console init and the real subprocess are mocked throughout — no real
agent or console is touched.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform != "win32":
    raise unittest.SkipTest("wrapper_windows only importable on win32")

import wrapper_windows  # noqa: E402


def _noop_start_watcher(inject_fn):
    pass


class RunAgentExitStatusTests(unittest.TestCase):
    def setUp(self):
        patcher_vt = patch.object(wrapper_windows, "enable_vt_mode")
        patcher_keepalive = patch.object(wrapper_windows, "_vt_keepalive_thread")
        patcher_sleep = patch.object(wrapper_windows.time, "sleep")
        self.addCleanup(patcher_vt.stop)
        self.addCleanup(patcher_keepalive.stop)
        self.addCleanup(patcher_sleep.stop)
        patcher_vt.start()
        patcher_keepalive.start()
        patcher_sleep.start()

    def _run_kwargs(self, **overrides):
        kwargs = dict(
            command="fake-cli",
            extra_args=[],
            cwd=".",
            env={},
            queue_file=Path(".audit-tmp") / "queue.jsonl",
            agent="claude",
            no_restart=True,
            start_watcher=_noop_start_watcher,
            pid_holder=[None],
        )
        kwargs.update(overrides)
        return kwargs

    def test_returns_actual_child_exit_code(self):
        proc = MagicMock()
        proc.pid = 4321
        proc.returncode = 23
        proc.wait.return_value = None
        with patch.object(wrapper_windows.subprocess, "Popen", return_value=proc):
            result = wrapper_windows.run_agent(**self._run_kwargs())
        self.assertEqual(result, 23)

    def test_batch_model_delimiters_fail_before_spawning_client(self):
        for value in ('alpha,beta', 'alpha;beta', 'alpha=beta'):
            kwargs = self._run_kwargs()
            kwargs.update(command='fake.cmd', extra_args=['--model', value])
            with self.subTest(value=value), patch.object(wrapper_windows.subprocess, 'Popen') as spawn:
                with self.assertRaises(ValueError):
                    wrapper_windows.run_agent(**kwargs)
                spawn.assert_not_called()

    def test_pid_holder_cleared_after_successful_exit(self):
        proc = MagicMock()
        proc.pid = 555
        proc.returncode = 0
        proc.wait.return_value = None
        pid_holder = [None]
        with patch.object(wrapper_windows.subprocess, "Popen", return_value=proc):
            wrapper_windows.run_agent(**self._run_kwargs(pid_holder=pid_holder))
        self.assertIsNone(pid_holder[0])

    def test_pid_holder_cleared_even_when_wait_raises(self):
        proc = MagicMock()
        proc.pid = 777
        proc.wait.side_effect = OSError("wait failed")
        pid_holder = [None]
        with patch.object(wrapper_windows.subprocess, "Popen", return_value=proc):
            with self.assertRaises(OSError):
                wrapper_windows.run_agent(**self._run_kwargs(pid_holder=pid_holder))
        self.assertIsNone(pid_holder[0])

    def test_watcher_starts_only_after_successful_spawn(self):
        order = []
        proc = MagicMock()
        proc.pid = 11
        proc.returncode = 0
        proc.wait.return_value = None

        def spawn(*args, **kwargs):
            order.append("spawn")
            return proc

        def start_watcher(inject_fn):
            order.append("watcher")

        with patch.object(wrapper_windows.subprocess, "Popen", side_effect=spawn):
            wrapper_windows.run_agent(**self._run_kwargs(start_watcher=start_watcher))

        self.assertEqual(order, ["spawn", "watcher"])

    def test_watcher_never_starts_if_spawn_fails(self):
        start_watcher = MagicMock()
        with patch.object(wrapper_windows.subprocess, "Popen", side_effect=OSError("spawn failed")):
            with self.assertRaises(OSError):
                wrapper_windows.run_agent(**self._run_kwargs(start_watcher=start_watcher))
        start_watcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
