"""Operator-selected content must not suppress late authenticated output audit."""
import unittest
import uuid

from tests import test_cli_message_attachment as fixture
from turn_events import EventConflict


class SelectedReplacementQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CliMessageAttachmentTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_selected_copy_does_not_count_as_the_fenced_workers_typed_result(self):
        ack = self.f.attach()
        before = self.f.sessions.get(self.f.run['id'])
        self.assertEqual(before['admitted_events'][0]['provenance'], 'operator_selected_cli_result')
        with self.assertRaises(EventConflict):
            self.f.engine.admit_event(self.f.run['active_invocation']['brief_id'], 'final',
                'LATE_ACTUAL_TYPED_OUTPUT', self.f.cli, event_id=uuid.uuid4().hex)
        current = self.f.sessions.get(self.f.run['id'])
        self.assertEqual(len(current['admitted_events']), 1)
        self.assertEqual(current['admitted_events'][0]['event_id'], ack['accepted_event_id'])
        quarantined = current.get('quarantined_events', [])
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0]['content'], 'LATE_ACTUAL_TYPED_OUTPUT')
        self.assertEqual(quarantined[0]['reason'], 'attempt_superseded')
        self.assertEqual(quarantined[0]['expected_identity_id'], self.f.cli['identity_id'])

    def test_true_typed_duplicate_after_stop_is_still_not_quarantined_again(self):
        event_id = uuid.uuid4().hex
        brief = self.f.run['active_invocation']['brief_id']
        self.f.engine.admit_event(brief, 'final', 'Already accepted typed output', self.f.cli, event_id=event_id)
        self.f.engine.stop_session(self.f.run['id'])
        with self.assertRaises(EventConflict):
            self.f.engine.admit_event(brief, 'final', 'Already accepted typed output', self.f.cli, event_id=event_id)
        current = self.f.sessions.get(self.f.run['id'])
        self.assertEqual(len(current['admitted_events']), 1)
        self.assertEqual(current.get('quarantined_events', []), [])
