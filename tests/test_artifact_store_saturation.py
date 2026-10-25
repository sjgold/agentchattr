"""Root-owned near-limit storage fixtures, not public setup or native evidence."""
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from artifact_store import ArtifactStore, MAX_DIAGNOSTIC_COUNTER


class ArtifactDiagnosticSaturationTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.audit-tmp'
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = ArtifactStore(self.root)
        self.attempt = uuid.uuid4().hex

    def submit(self, store, dispatch, content, now=100):
        return store.quarantine_submission(None, self.attempt, dispatch,
            reason='unmatched_saved_result', content=content, now=now)

    def verify_near_limit(self, store, dispatch):
        self.assertEqual(MAX_DIAGNOSTIC_COUNTER, 2**31 - 1)
        first = self.submit(store, dispatch, 'new overflow key', now=200)
        self.assertEqual(first['counter'], 2**31 - 1)
        self.assertIs(type(first['counter']), int)
        second = self.submit(store, dispatch, 'another overflow key', now=201)
        self.assertEqual(second['counter'], 2**31 - 1)
        self.assertNotEqual(second['latest_diagnostic_id'], first['latest_diagnostic_id'])
        self.assertEqual(second['latest_byte_count'], len(b'another overflow key'))
        before = store.path.read_bytes()
        self.assertEqual(self.submit(store, dispatch, 'another overflow key', now=999), second)
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(store.list_lineages()['count'], 0)

    def test_dispatch_counter_saturates_with_public_calls_after_valid_near_limit_seed(self):
        dispatch = uuid.uuid4().hex
        for number in range(8):
            self.submit(self.store, dispatch, f'detail {number}')
        self.assertEqual(self.submit(self.store, dispatch, 'first overflow')['kind'], 'dispatch_overflow')
        # Explicit white-box storage fixture, built from a real generated index.
        value = json.loads(self.store.path.read_text(encoding='utf-8'))
        value['dispatch_overflow'][dispatch]['counter'] = 2**31 - 2
        self.store.path.write_text(json.dumps(value), encoding='utf-8')
        restored = ArtifactStore(self.root)  # Strict load validates the seeded data.
        self.verify_near_limit(restored, dispatch)

    def test_store_counter_saturates_with_public_calls_after_valid_near_limit_seed(self):
        for _ in range(256):
            self.submit(self.store, uuid.uuid4().hex, None)
        dispatch = uuid.uuid4().hex
        self.assertEqual(self.submit(self.store, dispatch, 'first overflow')['kind'], 'store_overflow')
        value = json.loads(self.store.path.read_text(encoding='utf-8'))
        value['store_overflow']['counter'] = 2**31 - 2
        self.store.path.write_text(json.dumps(value), encoding='utf-8')
        restored = ArtifactStore(self.root)
        self.verify_near_limit(restored, dispatch)


if __name__ == '__main__':
    unittest.main()
