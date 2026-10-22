from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from api_seats import SeatStore, atomic_json, package_revision
from api_seat_runtime import SeatManager
from registry import RuntimeRegistry


class PackageReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SeatStore(self.tmp.name, {'fake': {'type': 'api', 'base_url': 'http://127.0.0.1:1/v1'}})
        self.pkg = {'id': 'team', 'name': 'Team', 'seats': [{'id': 'one', 'name': 'One',
                    'adapter': 'openai-compatible', 'provider': 'fake', 'model': 'one',
                    'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}]}
        self.store.save(self.pkg)
        self.manager = SeatManager(Path(__file__).resolve().parents[1], {'server': {}}, self.store,
                                   RuntimeRegistry(self.tmp.name), monitor=False)
        self.process = Mock()
        self.process.poll.return_value = None
        self.spawn = patch('api_seat_runtime.subprocess.Popen', return_value=self.process)
        self.spawn.start()
        self.addCleanup(self.spawn.stop)
        cleanup = patch('api_seat_runtime.stop_owned_child')
        cleanup.start()
        self.addCleanup(cleanup.stop)
        self.addCleanup(self.manager.shutdown)

    def test_initial_receipt_failure_starts_nothing(self):
        with patch('package_launch.atomic_json', side_effect=OSError('read only')), \
                patch.object(self.manager, 'launch') as launch:
            with self.assertRaises(OSError):
                self.manager.launch_package('team', package_revision(self.pkg))
            launch.assert_not_called()
        self.assertFalse(self.manager.package_status('team')['ready'])

    def test_final_receipt_failure_does_not_claim_ready_or_stop_peer(self):
        writes = []
        def save(path, value):
            writes.append(path)
            if len(writes) == 2:
                raise OSError('read only')
            atomic_json(path, value)
        with patch('package_launch.atomic_json', side_effect=save):
            self.manager.launch_package('team', package_revision(self.pkg))
        attempt = self.manager.attempts['team/one']
        atomic_json(attempt['receipt'], {'attempt': attempt['id'], 'state': 'ready', 'name': 'one',
                    'adapter_connected': True, 'authentication': 'unknown', 'confirmed_model': None,
                    'updated_at': time.time()})
        result = self.manager.package_status('team')
        self.assertFalse(result['ready'])
        self.assertIn('receipt', result['error'])
        self.assertIsNone(self.process.poll())
        self.assertFalse(attempt.get('released', False))

    def test_selection_receipt_is_immutable_package_data_and_bound_attempt(self):
        selection = self.manager.launch_package('team', package_revision(self.pkg))
        path = Path(self.tmp.name) / 'package_selections' / (selection['selection_id'] + '.json')
        original = path.read_bytes()
        self.pkg['name'] = 'Changed'
        self.manager.save(self.pkg)
        self.assertEqual(path.read_bytes(), original)
        import json
        saved = json.loads(original)
        self.assertEqual(saved['package']['name'], 'Team')
        self.assertEqual(saved['attempts']['one'], selection['seats']['one']['attempt'])
