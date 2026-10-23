"""An explicit preparation repair survives a lost operator response."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tests import test_participant_recovery_faults as fixture


class ReplacementRepairReplayTests(unittest.TestCase):
    def test_exact_repair_replay_does_not_launch_or_control_again_after_recording_success(self):
        f = fixture.ParticipantRecoveryFaultTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        spawn = f.f.fixture.spawn.side_effect
        f.f.fixture.spawn.side_effect = OSError('Synchronous preparation failure')
        f.replace()
        f.f.fixture.spawn.side_effect = spawn
        pending = deepcopy(f.current()['pending_replacement'])
        decision = f.repair_decision(pending, pending['context'])
        first = f.engine.repair_replacement(f.f.run['id'], decision)
        before = f.f.fixture.spawn.call_count
        with patch.object(f.f.fixture.manager, 'repair_replacement_context', side_effect=AssertionError('Repair replay actuated')):
            self.assertEqual(f.engine.repair_replacement(f.f.run['id'], decision), first)
        self.assertEqual(f.f.fixture.spawn.call_count, before)
