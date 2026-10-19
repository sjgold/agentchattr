from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

import wrapper_unix


class UnixOwnershipTests(unittest.TestCase):
    def test_unknown_existing_session_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(wrapper_unix, '_check_tmux'), \
                patch.object(wrapper_unix, '_session_exists', return_value=True), \
                patch.object(wrapper_unix.subprocess, 'run') as run:
            code = wrapper_unix.run_agent('fake', [], directory, {}, Path(directory) / 'queue',
                                          'fake', True, lambda fn: None, session_name='external')
            self.assertNotEqual(code, 0)
            self.assertFalse(any('kill-session' in call.args[0] for call in run.call_args_list))

    def test_child_exit_receipt_is_used_instead_of_attach_status(self):
        with tempfile.TemporaryDirectory() as directory:
            def run(command, **kwargs):
                if 'new-session' in command:
                    # The launch command points to an owned result receipt, even
                    # though no tmux process is created by this unit test.
                    import re
                    text = command[-1]
                    match = re.search(r'> (.+?); exit', text)
                    self.assertIsNotNone(match)
                    import shlex
                    path = Path(shlex.split(match.group(1))[0])
                    path.write_text('23', encoding='utf-8')
                return SimpleNamespace(returncode=0)
            with patch.object(wrapper_unix, '_check_tmux'), \
                    patch.object(wrapper_unix, '_session_exists', side_effect=[False, False, False]), \
                    patch.object(wrapper_unix.subprocess, 'run', side_effect=run):
                code = wrapper_unix.run_agent('fake', [], directory, {}, Path(directory) / 'queue',
                                              'fake', True, lambda fn: None, session_name='owned')
            self.assertEqual(code, 23)
