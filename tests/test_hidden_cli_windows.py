"""Managed Windows CLI launches keep an input console without showing a window."""
import subprocess
import sys
import unittest


@unittest.skipUnless(sys.platform == 'win32', 'Windows console startup contract')
class HiddenCLIWindowTests(unittest.TestCase):
    def test_managed_cli_hides_its_console_and_preserves_console_input(self):
        from tests.test_managed_turn_retry import ManagedTurnRetryTests
        fixture = ManagedTurnRetryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        api, cli = [call.kwargs for call in fixture.spawn.call_args_list]
        self.assertEqual(api['creationflags'], subprocess.CREATE_NO_WINDOW)
        self.assertEqual(cli['creationflags'], subprocess.CREATE_NEW_CONSOLE)
        self.assertTrue(cli['startupinfo'].dwFlags & subprocess.STARTF_USESHOWWINDOW)
        self.assertEqual(cli['startupinfo'].wShowWindow, subprocess.SW_HIDE)
        for stream in ('stdin', 'stdout', 'stderr'):
            self.assertNotIn(stream, cli)
