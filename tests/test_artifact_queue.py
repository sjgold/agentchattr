"""Root-owned raw queue guards and historical-row fixtures, no runtime claims."""
import json
from pathlib import Path
import tempfile
import unittest

from artifact_store import request_ids
from dispatch_queue import QueueConflict, QueueStore


class ArtifactQueueTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.audit-tmp'
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.queue = QueueStore(temporary.name)
        self.instance = {'name': 'fixture', 'identity_id': 'a' * 32}
        ids = request_ids('1' * 32)
        self.envelope = {'dispatch_id': ids['dispatch_id'], 'channel': 'general', 'purpose': 'artifact-v1',
            'artifact_request_id': '1' * 32, 'artifact_attempt_id': ids['attempt_id'],
            'artifact_brief_id': ids['brief_id'], 'artifact_scope_sha256': 'b' * 64}

    def test_public_raw_enqueue_refuses_artifact_without_coordinator_authority(self):
        with self.assertRaises(QueueConflict):
            self.queue.enqueue(self.instance, self.envelope)
        self.assertFalse(self.queue.path.exists())

    def test_raw_claim_does_not_claim_artifact_without_explicit_eligibility(self):
        # Create an ordinary row through the real writer, then represent a retained
        # artifact row in a root-owned storage fixture. No enqueue authority claim.
        self.queue.enqueue(self.instance, {'dispatch_id': self.envelope['dispatch_id'], 'channel': 'general'})
        value = json.loads(self.queue.path.read_text(encoding='utf-8'))
        value['records'][0]['envelope'].update(self.envelope)
        self.queue.path.write_text(json.dumps(value), encoding='utf-8')
        before = self.queue.path.read_bytes()
        self.assertIsNone(self.queue.claim(self.instance, 'fixture-consumer'))
        self.assertEqual(self.queue.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
