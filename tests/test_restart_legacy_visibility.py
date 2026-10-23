"""A cold-interruption marker must not resurrect abandoned legacy history."""
from copy import deepcopy
import unittest


class LegacyInterruptionVisibilityTests(unittest.TestCase):
    def test_legacy_record_cannot_admit_machine_provenance_from_an_old_brief(self):
        from tests.test_restart_reconciliation import RestartReconciliationTests
        from turn_events import EventConflict
        fixture = RestartReconciliationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.sessions._event_update(fixture.session_id, lambda value: value.pop('completion_protocol'))
        original, queue = deepcopy(fixture.current()), deepcopy(fixture.records())
        with self.assertRaises(EventConflict):
            fixture.engine.admit_event(fixture.original['brief_id'], 'final', 'Unverified legacy result', fixture.owner)
        self.assertEqual(fixture.current(), original)
        self.assertEqual(fixture.records(), queue)

    def test_legacy_abandoned_interruption_does_not_occupy_a_new_review_channel(self):
        from tests.test_restart_reconciliation import RestartReconciliationTests
        fixture = RestartReconciliationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        def legacy(value):
            value['state'] = 'interrupted'
            value.pop('completion_protocol', None)
            value.pop('restart_recovery', None)
        fixture.sessions._event_update(fixture.session_id, legacy)
        original = deepcopy(fixture.current())
        started = fixture.engine.start_session('review', 'general',
            {'reviewer': 'human-one', 'editor': 'human-two'}, 'operator')
        self.assertIsNotNone(started)
        self.assertEqual(fixture.engine.get_active('general')['id'], started['id'])
        self.assertEqual(fixture.sessions.get(fixture.session_id), original)
