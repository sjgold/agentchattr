"""Pre-flight observations never imply cold runtime adoption or control."""
import asyncio
import json
import sys
import unittest
from unittest.mock import patch

from api_seats import atomic_json


@unittest.skipUnless(sys.platform == 'win32', 'Reuses actual owned Windows birth fixtures')
class RuntimeVisibilityTests(unittest.TestCase):
    def adoption_fixture(self):
        from tests.test_runtime_adoption import RuntimeAdoptionTests
        fixture = RuntimeAdoptionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_unverified_inventory_is_visible_without_becoming_an_owned_attempt(self):
        fixture = self.adoption_fixture()
        before = fixture.files()
        fixture.manager.reconcile_runtime(now=fixture.now)
        view = fixture.manager.inspect('team', 'api')
        self.assertEqual(view['state'], 'unverified')
        self.assertFalse(view['process_verified'])
        self.assertEqual(view['reason'], 'awaiting_authenticated_boot_proof')
        self.assertEqual(fixture.manager.snapshot()['team/api'], view)
        import app
        with patch.object(app, 'api_seat_store', fixture.store), patch.object(app, 'api_seat_manager', fixture.manager):
            response = asyncio.run(app.get_api_seats())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body)['runtime']['team/api'], view)
        self.assertEqual(fixture.manager.attempts, {})
        self.assertEqual(fixture.files(), before)
        self.assertNotIn('PRIVATE_PROVIDER_SOURCE_SENTINEL', json.dumps(view))
        fixture.spawn.assert_not_called()
        self.assertTrue(fixture.heartbeat()['verified'])
        self.assertEqual(fixture.manager.inspect('team', 'api')['state'], 'ready')

    def test_recognized_legacy_runtime_is_visible_and_files_remain_unchanged(self):
        fixture = self.adoption_fixture()
        snapshot = dict(fixture.snapshot)
        snapshot.pop('ownership')
        atomic_json(fixture.path, snapshot)
        before = fixture.files()
        fixture.manager.reconcile_runtime(now=fixture.now)
        view = fixture.manager.snapshot()['team/api']
        self.assertEqual(view['state'], 'unverified')
        self.assertEqual(view['reason'], 'legacy_unverified')
        self.assertFalse(view['process_verified'])
        self.assertEqual(fixture.manager.attempts, {})
        self.assertEqual(fixture.files(), before)
        fixture.spawn.assert_not_called()

    def test_proven_historical_exit_is_displayed_without_fabricated_process(self):
        from tests.test_runtime_history import RuntimeHistoryTests
        fixture = RuntimeHistoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with patch('runtime_adoption.open_verified_process', return_value={
                'status': 'absent', 'error_code': 87, 'process': None}):
            fixture.manager.reconcile_runtime()
        view = fixture.manager.inspect('team', 'cli')
        self.assertEqual(view['state'], 'exited')
        self.assertEqual(view['reason'], 'local_exit_proven')
        self.assertFalse(view['process_verified'])
        self.assertEqual(fixture.manager.snapshot()['team/cli'], view)
        self.assertEqual(fixture.manager.attempts, {})
        fixture.spawn.assert_not_called()
