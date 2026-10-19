from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class CompatibilityLaunchTests(unittest.TestCase):
    def test_child_exit_23_propagates_and_uses_shared_bootstrap(self):
        import launch_agent
        root = Path(__file__).resolve().parents[1]
        cfg = {'agents': {'fake': {'command': 'fake'}}}
        with patch.object(launch_agent, 'load_config', return_value=cfg), \
                patch.object(launch_agent, 'ensure_server') as server, \
                patch.object(launch_agent, 'ensure_environment', return_value=Path('python.exe')), \
                patch.object(launch_agent.shutil, 'which', return_value='fake.exe'), \
                patch.object(launch_agent.subprocess, 'run', return_value=SimpleNamespace(returncode=23)) as run:
            self.assertEqual(launch_agent.main(['fake', '--', '--chosen-model', 'example'], root=root), 23)
            server.assert_called_once_with(root, cfg, setup=False)
            self.assertIn('--no-restart', run.call_args.args[0])
            self.assertEqual(run.call_args.args[0][-3:], ['--', '--chosen-model', 'example'])

    def test_missing_template_never_starts_a_server_or_agent(self):
        import launch_agent
        with patch.object(launch_agent, 'load_config', return_value={'agents': {}}), \
                patch.object(launch_agent, 'ensure_server') as server, \
                patch.object(launch_agent.subprocess, 'run') as run:
            self.assertEqual(launch_agent.main(['not-configured']), 1)
            server.assert_not_called()
            run.assert_not_called()
