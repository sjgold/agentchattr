"""Assigned parent reads and bounded rejection reports, controlled process evidence."""
import hashlib
import unittest

from tests import test_artifact_admission as fixture


class ArtifactParentTests(unittest.TestCase):
    def context(self):
        case = fixture.ArtifactAdmissionTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        return case

    def test_assigned_parent_is_exact_readonly_and_new_lineage_has_no_parent(self):
        case = self.context()
        first = case.prepare()
        consumer = case.claim(first)
        before = case.files()
        self.assertEqual(case.authority.get_parent(first['brief_id'], case.instance), {'parent': None})
        self.assertEqual(case.files(), before)
        text = '# Exact café\r\nParent bytes.\r\n'
        ack = case.authority.submit_cli(first['brief_id'], text, case.instance)
        case.trigger.queue.release(case.instance, first['dispatch_id'], consumer)
        metadata = case.artifacts.get_version(ack['version_id'])['metadata']
        expected = {'version_id': metadata['id'], 'sequence': metadata['sequence'], 'sha256': metadata['sha256']}
        revision = case.prepare(lineage_id=first['lineage_id'], parent=expected)
        case.claim(revision)
        before = case.files()
        response = case.authority.get_parent(revision['brief_id'], case.instance)
        self.assertEqual(response, {'parent': {**expected, 'byte_length': len(text.encode('utf-8')), 'markdown': text}})
        self.assertEqual(response['parent']['sha256'], hashlib.sha256(text.encode('utf-8')).hexdigest())
        self.assertEqual(case.files(), before)
        self.assertEqual(case.artifacts.get_request(revision['request_id'])['state'], 'queued')

    def test_unclaimed_wrong_seat_terminal_or_corrupt_parent_refuses_without_settlement(self):
        case = self.context()
        audit = case.prepare()
        before = case.files()
        with self.assertRaises(case.storage.ArtifactConflict):
            case.authority.get_parent(audit['brief_id'], case.instance)
        self.assertEqual(case.files(), before)
        consumer = case.claim(audit)
        other, _, _ = case.launch_binding('api')
        before = case.files()
        with self.assertRaises(case.module.ArtifactAccessError):
            case.authority.get_parent(audit['brief_id'], other)
        self.assertEqual(case.files(), before)
        ack = case.authority.submit_cli(audit['brief_id'], '# Parent', case.instance)
        before = case.files()
        with self.assertRaises(case.storage.ArtifactConflict):
            case.authority.get_parent(audit['brief_id'], case.instance)
        self.assertEqual(case.files(), before)
        case.trigger.queue.release(case.instance, audit['dispatch_id'], consumer)
        metadata = case.artifacts.get_version(ack['version_id'])['metadata']
        parent = {'version_id': metadata['id'], 'sequence': metadata['sequence'], 'sha256': metadata['sha256']}
        revision = case.prepare(lineage_id=audit['lineage_id'], parent=parent)
        case.claim(revision)
        path = case.root / 'artifacts' / 'objects' / (metadata['id'] + '.md')
        path.write_bytes(b'corrupt immutable parent')
        before = case.files()
        with self.assertRaises(case.storage.ArtifactUnavailable):
            case.authority.get_parent(revision['brief_id'], case.instance)
        self.assertEqual(case.files(), before)
        self.assertEqual(case.artifacts.get_request(revision['request_id'])['state'], 'queued')
        self.assertEqual(case.artifacts.get_request(revision['request_id'])['quarantine_ids'], [])

    def test_api_no_body_rejection_and_strict_report_shapes_never_grant_cli_authority(self):
        case = self.context()
        instance, _, _ = case.launch_binding('api')
        audit, _ = case.claimed(instance=instance, channel='peer')
        for content, flag in (('text', True), (None, False), (None, 1)):
            with self.subTest(content=content, flag=flag):
                before = case.files()
                with self.assertRaises(case.storage.ArtifactValidationError):
                    case.authority.reject_response(audit['brief_id'], content, instance, received_truncated=flag)
                self.assertEqual(case.files(), before)
        cli, _ = case.claimed()
        before = case.files()
        with self.assertRaises(case.module.ArtifactAccessError):
            case.authority.reject_response(cli['brief_id'], None, case.instance, received_truncated=True)
        self.assertEqual(case.files(), before)
        result = case.authority.reject_response(audit['brief_id'], None, instance, received_truncated=True)
        self.assertEqual(result['reason'], 'response_too_large')
        self.assertTrue(result['received_truncated'])
        self.assertEqual(result['notice'], 'response_body_not_retained')
        self.assertTrue(result['request_terminal'])
        row = case.artifacts.get_request(audit['request_id'])
        self.assertEqual((row['state'], row['reason']), ('quarantined', 'invalid_response'))
        self.assertEqual(case.trigger.queue.owned(instance, audit['dispatch_id'])['state'], 'cancelling')


if __name__ == '__main__':
    unittest.main()
