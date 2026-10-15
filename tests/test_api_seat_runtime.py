import importlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import SeatStore, atomic_json
from registry import RuntimeRegistry


class APISeatRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'api_seat_runtime.py').exists(), 'API-seat process manager missing')
        self.module = importlib.import_module('api_seat_runtime')
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.providers = {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1'}}
        self.store = SeatStore(self.root, self.providers)
        self.package = {'id': 'team', 'name': 'Team', 'seats': [{'id': 'writer', 'name': 'Writer',
                        'adapter': 'openai-compatible', 'provider': 'fake', 'model': 'one',
                        'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}]}
        self.store.save(self.package)
        self.registry = RuntimeRegistry(str(self.root))
        self.manager = self.module.SeatManager(ROOT, {'server': {'port': 18300, 'data_dir': str(self.root)}},
                                               self.store, self.registry, startup_timeout=0.1, monitor=False)
        self.process = Mock()
        self.process.poll.return_value = None
        self.patch = patch.object(self.module.subprocess, 'Popen', return_value=self.process)
        self.spawn = self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.manager.shutdown)

    def mark_ready(self):
        attempt = self.manager.attempts['team/writer']
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready', 'name': 'example',
                    'adapter_connected': True, 'authentication': 'unknown', 'confirmed_model': None,
                    'updated_at': time.time()})

    def test_launch_snapshot_propagates_settings_and_reuses_owned_process(self):
        first = self.manager.launch('team', 'writer')
        self.mark_ready()
        second = self.manager.launch('team', 'writer')
        self.assertEqual(first['attempt'], second['attempt'])
        self.spawn.assert_called_once()
        self.assertEqual(second['state'], 'ready')
        attempt = self.manager.attempts['team/writer']
        snapshot = json.loads(attempt['snapshot'].read_text())
        self.assertEqual(snapshot['seat']['model'], 'one')
        self.assertEqual(snapshot['server']['port'], 18300)

    def test_edit_requires_explicit_restart_and_stops_only_owned_child(self):
        self.manager.launch('team', 'writer')
        self.mark_ready()
        self.package['seats'][0]['model'] = 'two'
        self.store.save(self.package)
        with self.assertRaisesRegex(self.module.SeatError, 'restart'):
            self.manager.launch('team', 'writer')
        self.process.terminate.assert_not_called()
        result = self.manager.launch('team', 'writer', restart=True)
        self.process.terminate.assert_called_once()
        self.assertEqual(result['requested_model'], 'two')

    def test_readiness_timeout_and_child_exit_are_explicit(self):
        self.manager.launch('team', 'writer')
        self.manager.attempts['team/writer']['started'] -= 1
        result = self.manager.inspect('team', 'writer')
        self.assertEqual(result['state'], 'failed')
        self.assertIn('deadline', result['error'])
        self.process.terminate.assert_called_once()

    def test_missing_secret_is_user_action_without_spawn(self):
        self.package['seats'][0]['secret_ref'] = 'TEST_ABSENT_API_SECRET'
        self.store.save(self.package)
        with patch.dict('os.environ', {}, clear=True):
            result = self.manager.launch('team', 'writer')
        self.assertEqual(result['state'], 'action_required')
        self.spawn.assert_not_called()

    def test_stale_attempt_receipt_cannot_confirm_model(self):
        self.manager.launch('team', 'writer')
        attempt = self.manager.attempts['team/writer']
        atomic_json(attempt['receipt'], {'attempt': 'old', 'state': 'ready', 'confirmed_model': 'wrong'})
        result = self.manager.inspect('team', 'writer')
        self.assertEqual(result['state'], 'starting')
        self.assertIsNone(result['confirmed_model'])

    def test_unknown_target_does_not_stop_any_child(self):
        with self.assertRaises(self.module.SeatError):
            self.manager.launch('other', 'writer', restart=True)
        self.process.terminate.assert_not_called()

    def test_stop_cleans_up_its_registration_even_without_a_receipt(self):
        self.manager.launch('team', 'writer')
        attempt = self.manager.attempts['team/writer']
        registration = self.registry.register(attempt['base'])
        self.manager.stop('team', 'writer')
        self.assertIsNone(self.registry.get_instance(registration['name']))

    def test_fresh_starting_receipts_do_not_extend_startup_deadline(self):
        self.manager.launch('team', 'writer')
        attempt = self.manager.attempts['team/writer']
        attempt['started'] -= 1
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'starting',
                    'adapter_connected': False, 'authentication': 'unknown', 'updated_at': time.time()})
        self.assertEqual(self.manager.inspect('team', 'writer')['state'], 'failed')

    def test_removing_a_live_seat_requires_targeted_stop_first(self):
        self.package['seats'].append({**self.package['seats'][0], 'id': 'second'})
        self.store.save(self.package)
        self.manager.launch('team', 'writer')
        changed = {**self.package, 'seats': self.package['seats'][1:]}
        self.assertTrue(hasattr(self.manager, 'save'), 'serialized package save missing')
        with self.assertRaisesRegex(self.module.SeatError, 'Stop'):
            self.manager.save(changed)
        self.manager.stop('team', 'writer')
        self.manager.save(changed)

    def test_concurrent_launch_requests_create_one_owned_child(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.manager.launch('team', 'writer'), range(2)))
        self.assertEqual(results[0]['attempt'], results[1]['attempt'])
        self.spawn.assert_called_once()

    def test_expired_heartbeat_fails_and_releases_only_owned_registration(self):
        self.manager.launch('team', 'writer')
        self.mark_ready()
        attempt = self.manager.attempts['team/writer']
        data = json.loads(attempt['receipt'].read_text())
        data['updated_at'] -= 60
        atomic_json(attempt['receipt'], data)
        result = self.manager.inspect('team', 'writer')
        self.assertEqual(result['state'], 'failed')
        self.assertIn('heartbeat', result['error'])
        self.process.terminate.assert_called_once()

    def test_real_child_exit_is_visible_and_removes_registration(self):
        self.manager.launch('team', 'writer')
        attempt = self.manager.attempts['team/writer']
        registration = self.registry.register(attempt['base'])
        self.process.poll.return_value = 9
        result = self.manager.inspect('team', 'writer')
        self.assertEqual(result['state'], 'failed')
        self.assertIn('exited', result['error'])
        self.assertIsNone(self.registry.get_instance(registration['name']))

    def test_lost_receipt_cannot_leave_a_seat_ready_forever(self):
        self.manager.launch('team', 'writer')
        self.mark_ready()
        self.manager.inspect('team', 'writer')
        attempt = self.manager.attempts['team/writer']
        attempt['last_receipt_at'] = time.time() - 60
        attempt['receipt'].unlink()
        self.assertEqual(self.manager.inspect('team', 'writer')['state'], 'failed')

    def test_stop_requests_the_actual_attempt_worker_to_exit(self):
        result = self.manager.launch('team', 'writer')
        attempt = self.manager.attempts['team/writer']
        self.manager.stop('team', 'writer')
        control = attempt['snapshot'].with_name('stop.json')
        self.assertTrue(control.exists(), 'worker stop control was not written')
        self.assertEqual(json.loads(control.read_text()), {'attempt': result['attempt']})


if __name__ == '__main__':
    unittest.main()
