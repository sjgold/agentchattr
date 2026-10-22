"""Ticket #5 package-launch contracts with owned-process doubles and real receipts."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api_seats
from api_seats import SeatError, SeatStore, atomic_json
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry


def api_seat(seat_id='api', model='api-one', secret_ref=''):
    return {'id': seat_id, 'name': seat_id.upper(), 'adapter': 'openai-compatible',
            'provider': 'fake-api', 'model': model, 'reasoning': None,
            'launch_profile': 'standard', 'secret_ref': secret_ref}


def cli_seat(seat_id='cli', model='cli-one'):
    return {'id': seat_id, 'name': seat_id.upper(), 'adapter': 'cli',
            'provider': 'fake-cli', 'model': model, 'reasoning': 'high',
            'launch_profile': 'standard', 'secret_ref': ''}


class PackageLaunchTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.providers = {
            'fake-api': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1'},
            'fake-cli': {'command': sys.executable, 'cwd': '.',
                         'cli_model_args': ['--model', '{model}'],
                         'cli_reasoning_args': ['--reasoning', '{reasoning}'],
                         'reasoning_efforts': ['high'], 'mcp_inject': 'env',
                         'mcp_env_var': 'TICKET5_FAKE_SETTINGS'},
        }
        self.store = SeatStore(self.root, self.providers)
        self.package = {'id': 'team', 'name': 'Team', 'seats': [api_seat(), cli_seat()]}
        self.store.save(self.package)
        self.manager = SeatManager(ROOT, {'server': {'port': 18300, 'data_dir': str(self.root)}},
                                   self.store, RuntimeRegistry(str(self.root)),
                                   startup_timeout=5, monitor=False)
        self.processes = []

        def fake_popen(*args, **kwargs):
            process = Mock()
            process.poll.return_value = None
            self.processes.append(process)
            return process

        self.patcher = patch('api_seat_runtime.subprocess.Popen', side_effect=fake_popen)
        self.spawn = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.manager.shutdown)

    def revision(self):
        return api_seats.package_revision(self.store.package('team'))

    def launch_team(self, **choices):
        return self.manager.launch_package('team', self.revision(), **choices)

    def mark_ready(self, seat_id):
        attempt = self.manager.attempts['team/' + seat_id]
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready',
                    'name': 'test-' + seat_id, 'adapter_connected': True,
                    'authentication': 'unknown', 'confirmed_model': None,
                    'updated_at': time.time()})

    def test_mixed_package_roundtrip_and_revision_are_canonical(self):
        saved = self.store.package('team')
        self.assertEqual(saved, self.package)
        saved['seats'][0]['model'] = 'mutated-copy'
        self.assertEqual(self.store.package('team'), self.package)
        self.assertEqual(api_seats.package_revision(self.package),
                         api_seats.package_revision(json.loads(json.dumps(self.package, sort_keys=True))))
        self.assertRegex(self.revision(), r'^[0-9a-f]{64}$')
        with self.assertRaises(SeatError):
            self.store.package('missing')

    def test_launch_reuses_two_healthy_matching_attempts_and_binds_selection(self):
        first = self.launch_team()
        self.assertEqual(set(first['seats']), {'api', 'cli'})
        self.assertEqual(first['revision'], self.revision())
        self.assertEqual(len(self.processes), 2)
        bound = {seat_id: first['seats'][seat_id]['attempt'] for seat_id in ('api', 'cli')}
        self.mark_ready('api')
        self.mark_ready('cli')
        second = self.launch_team()
        self.assertEqual(len(self.processes), 2, 'matching healthy seats should be reused')
        self.assertEqual({seat_id: second['seats'][seat_id]['attempt'] for seat_id in bound}, bound)
        self.assertTrue(self.manager.package_status('team')['ready'])

    def test_wrong_revision_rejects_before_any_spawn(self):
        with self.assertRaises(SeatError):
            self.manager.launch_package('team', '0' * 64)
        self.spawn.assert_not_called()
        self.assertFalse(self.manager.package_status('team')['ready'])

    def test_changed_model_requires_targeted_restart_and_preserves_peer(self):
        first = self.launch_team()
        self.mark_ready('api')
        self.mark_ready('cli')
        original_api = first['seats']['api']['attempt']
        original_cli = first['seats']['cli']['attempt']
        self.package['seats'][1]['model'] = 'cli-two'
        self.manager.save(self.package)
        changed = self.launch_team()
        self.assertEqual(changed['seats']['cli']['state'], 'action_required')
        self.assertIn('restart', changed['seats']['cli']['error'].lower())
        self.assertEqual(changed['seats']['api']['attempt'], original_api)
        self.assertEqual(changed['seats']['cli']['attempt'], original_cli)
        self.assertEqual(len(self.processes), 2)
        restarted = self.launch_team(restart_seats=['cli'])
        self.assertEqual(restarted['seats']['api']['attempt'], original_api)
        self.assertNotEqual(restarted['seats']['cli']['attempt'], original_cli)
        self.assertEqual(restarted['seats']['cli']['requested_model'], 'cli-two')
        self.assertEqual(len(self.processes), 3)

    def test_missing_credential_is_per_seat_and_peer_launches(self):
        self.package['seats'][0]['secret_ref'] = 'TICKET5_ABSENT_SECRET'
        self.manager.save(self.package)
        with patch.dict('os.environ', {}, clear=True):
            result = self.launch_team()
        self.assertEqual(result['seats']['api']['state'], 'action_required')
        self.assertEqual(result['seats']['cli']['state'], 'starting')
        self.assertEqual(len(self.processes), 1)
        self.mark_ready('cli')
        self.assertFalse(self.manager.package_status('team')['ready'])

    def test_omission_only_changes_this_selection(self):
        result = self.launch_team(omitted_seats=['cli'])
        self.assertEqual(set(result['seats']), {'api'})
        self.assertEqual(result['omitted_seats'], ['cli'])
        self.assertEqual(len(self.processes), 1)
        self.assertEqual({seat['id'] for seat in self.store.package('team')['seats']}, {'api', 'cli'})
        self.mark_ready('api')
        self.assertTrue(self.manager.package_status('team')['ready'])
        next_selection = self.launch_team()
        self.assertEqual(set(next_selection['seats']), {'api', 'cli'})
        self.assertEqual(len(self.processes), 2)

    def test_invalid_restart_and_omission_choices_do_not_spawn(self):
        cases = [dict(omitted_seats=['api', 'cli']), dict(omitted_seats=['missing']),
                 dict(restart_seats=['missing']), dict(omitted_seats=['api', 'api']),
                 dict(restart_seats=['cli', 'cli']),
                 dict(omitted_seats=['api'], restart_seats=['api'])]
        for choices in cases:
            with self.subTest(choices=choices), self.assertRaises(SeatError):
                self.launch_team(**choices)
        self.spawn.assert_not_called()

    def test_chat_handoff_requires_current_ready_selection(self):
        first = self.launch_team()
        with self.assertRaises(SeatError):
            self.manager.continue_package('team', first['selection_id'])
        self.mark_ready('api')
        self.mark_ready('cli')
        with self.assertRaises(SeatError):
            self.manager.continue_package('team', 'old-selection')
        result = self.manager.continue_package('team', first['selection_id'])
        self.assertEqual(result['selection_id'], first['selection_id'])
        self.assertTrue(result['url'].startswith('/?package_launch='))
        self.assertEqual(len(self.processes), 2, 'entering chat must not launch a session or worker')
        second = self.launch_team(omitted_seats=['cli'])
        with self.assertRaises(SeatError):
            self.manager.continue_package('team', first['selection_id'])
        self.assertEqual(self.manager.continue_package('team', second['selection_id'])['selection_id'],
                         second['selection_id'])

    def test_saved_edit_or_template_drift_revokes_ready_handoff(self):
        first = self.launch_team()
        self.mark_ready('api')
        self.mark_ready('cli')
        self.assertTrue(self.manager.package_status('team')['ready'])
        self.package['name'] = 'Updated Team'
        self.manager.save(self.package)
        self.assertFalse(self.manager.package_status('team')['ready'])
        with self.assertRaises(SeatError):
            self.manager.continue_package('team', first['selection_id'])
        second = self.launch_team()
        self.assertTrue(self.manager.package_status('team')['ready'])
        self.store.providers['fake-cli']['cli_args'] = ['--new-template']
        self.assertFalse(self.manager.package_status('team')['ready'])
        with self.assertRaises(SeatError):
            self.manager.continue_package('team', second['selection_id'])

    def assert_handoff_revoked_by(self, invalidation):
        selection = self.launch_team()
        self.mark_ready('api')
        self.mark_ready('cli')
        self.assertTrue(self.manager.package_status('team')['ready'])
        if invalidation == 'stop':
            self.manager.stop('team', 'cli')
        elif invalidation == 'stale':
            attempt = self.manager.attempts['team/cli']
            receipt = json.loads(attempt['receipt'].read_text('utf-8'))
            receipt['updated_at'] = time.time() - 60
            atomic_json(attempt['receipt'], receipt)
        elif invalidation == 'exit':
            self.manager.attempts['team/cli']['process'].poll.return_value = 23
            self.manager.attempts['team/cli']['process'].returncode = 23
        elif invalidation == 'restart':
            self.manager.launch('team', 'cli', restart=True)
        self.assertFalse(self.manager.package_status('team')['ready'])
        with self.assertRaises(SeatError):
            self.manager.continue_package('team', selection['selection_id'])

    def test_stopped_attempt_revokes_ready_handoff(self):
        self.assert_handoff_revoked_by('stop')

    def test_stale_attempt_revokes_ready_handoff(self):
        self.assert_handoff_revoked_by('stale')

    def test_dead_attempt_revokes_ready_handoff(self):
        self.assert_handoff_revoked_by('exit')

    def test_restarted_attempt_revokes_ready_handoff(self):
        self.assert_handoff_revoked_by('restart')


if __name__ == '__main__':
    unittest.main()
