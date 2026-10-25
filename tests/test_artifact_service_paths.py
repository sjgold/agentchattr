"""Root-owned API/cancel service paths, fixture-controlled process/model evidence."""
import unittest

from tests import test_artifact_admission as fixture


class ArtifactServicePathTests(unittest.TestCase):
    def context(self):
        case = fixture.ArtifactAdmissionTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        return case

    def test_exact_sealed_api_result_admits_once_and_preserves_first_observation(self):
        case = self.context()
        instance, _, _ = case.launch_binding('api')
        audit, consumer = case.claimed(instance=instance, channel='peer')
        observation = {'confirmed_model': 'fixture-confirmed-model', 'confirmation_reason': 'api_response'}
        record = case.sealed_fixture_record(audit, consumer, observation=observation)
        ack = case.authority.admit_saved(record, instance)
        self.assertEqual(ack['status'], 'admitted')
        metadata = case.artifacts.get_version(ack['version_id'])['metadata']
        self.assertEqual(metadata['provenance']['observation'], observation)
        before = case.files()
        self.assertEqual(case.authority.admit_saved(record, instance), ack)
        self.assertEqual(case.files(), before)
        self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 1)
        self.assertEqual(case.trigger.queue.owned(instance, audit['dispatch_id'])['state'], 'dispatched')

    def test_inactive_channel_cancel_fences_claimed_transport_without_admitting_late_result(self):
        case = self.context()
        audit, _ = case.claimed()
        case.catalog.set_state('review', 'archived', expected_revision=case.catalog.snapshot()['revision'])
        result = case.authority.cancel_request(audit['request_id'])
        self.assertEqual(result['request']['state'], 'cancelled')
        self.assertEqual(result['dispatch']['state'], 'cancelling')
        self.assertFalse(result['transport_settled'])
        with self.assertRaises((case.module.ArtifactAccessError, case.storage.ArtifactConflict)):
            case.authority.submit_cli(audit['brief_id'], '# Late answer', case.instance)
        self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 0)


if __name__ == '__main__':
    unittest.main()
