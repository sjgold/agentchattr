"""Root-owned artifact purpose/seal tests; no provider or admission claim."""
from copy import deepcopy
import importlib
import unittest

from artifact_store import ArtifactValidationError, request_ids
from tests import test_result_outbox as review_fixture


class ArtifactProtocolTests(unittest.TestCase):
    def payload(self):
        ids = request_ids('1' * 32)
        return {'version': 1, 'purpose': 'artifact-v1', 'result_id': ids['dispatch_id'],
            'dispatch_id': ids['dispatch_id'], 'request_id': '1' * 32, 'attempt_id': ids['attempt_id'],
            'brief_id': ids['brief_id'], 'lineage_id': ids['lineage_id'], 'scope_sha256': 'a' * 64,
            'expected_parent': None, 'seat_identity_id': 'b' * 32, 'launch_attempt': 'c' * 32,
            'launch_nonce': 'd' * 32, 'fingerprint': 'e' * 64, 'consumer_id': 'fixture-consumer',
            'kind': 'artifact', 'markdown': '# Exact café 日本語\r\n\r\nKeep e\u0301 and \\literal.\r\n',
            'observation': {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'},
            'created_at': 1792730000.125}

    def test_purpose_seal_matches_independent_preimplementation_vector(self):
        protocol = importlib.import_module('artifact_protocol')
        payload = self.payload()
        record = protocol.seal_result(payload, bytes(range(32)).hex())
        # Independent stdlib vector captured before artifact protocol source existed.
        self.assertEqual(record['seal'], 'e72a03b128c0734a6ad96a79396821e74602850048812410f406bd1df5152c9d')
        self.assertEqual(protocol.verify_result(record, bytes(range(32)).hex()), payload)
        self.assertEqual(record['payload']['markdown'].encode('utf-8'), payload['markdown'].encode('utf-8'))
        edited = deepcopy(record)
        edited['payload']['markdown'] += 'tampered'
        with self.assertRaises(ArtifactValidationError):
            protocol.verify_result(edited, bytes(range(32)).hex())

    def test_review_and_artifact_records_refuse_in_both_directions_with_same_key(self):
        protocol = importlib.import_module('artifact_protocol')
        case = review_fixture.ResultOutboxTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        review = case.module.seal_result(case.payload, case.secret)
        artifact = protocol.seal_result(self.payload(), case.secret)
        with self.assertRaises(ArtifactValidationError):
            protocol.verify_result(review, case.secret)
        with self.assertRaises(case.module.OutboxError):
            case.module.verify_result(artifact, case.secret)


if __name__ == '__main__':
    unittest.main()
