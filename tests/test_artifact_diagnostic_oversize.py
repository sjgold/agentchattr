"""Root-owned missing-body diagnostic namespace and real-limit metadata fixtures."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from artifact_store import ArtifactStore
from sealed_result_io import canonical_utf8


class ArtifactOversizeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_retained_empty_then_oversize_none_has_distinct_immutable_diagnostics(self):
        store = ArtifactStore(self.root)
        args = ('1' * 32, '2' * 32, '3' * 32)
        first = store.quarantine_submission(*args, reason='invalid_content', content='',
                                            actor_identity_id='4' * 32, now=100)
        self.assertFalse(first['not_retained'])
        body = self.root / 'artifacts' / 'quarantine' / (first['id'] + '.txt')
        self.assertEqual(body.read_bytes(), b'')
        second = store.quarantine_submission(*args, reason='response_too_large', content=None,
                                             actor_identity_id='4' * 32, now=101)
        self.assertNotEqual(first['id'], second['id'])
        self.assertTrue(second['not_retained'])
        self.assertIsNone(second['body_object_id'])
        self.assertEqual(second['byte_count'], 0)
        self.assertEqual(second['sha256'], hashlib.sha256(b'').hexdigest())
        before = store.diagnostic_store.path.read_bytes()
        self.assertEqual(store.quarantine_submission(*args, reason='invalid_content', content='',
            actor_identity_id='4' * 32, now=999), first)
        self.assertEqual(store.diagnostic_store.path.read_bytes(), before)
        self.assertEqual(body.read_bytes(), b'')

    def test_oversize_reason_uses_existing_group_and_global_overflow_bounds(self):
        for mode in ('per_dispatch', 'dispatch_groups', 'global_records'):
            with self.subTest(mode=mode):
                store = ArtifactStore(self.root / mode)
                dispatch, attempt = uuid.uuid4().hex, uuid.uuid4().hex
                row = store.quarantine_submission(None, attempt, dispatch,
                    reason='response_too_large', content=None, now=100)
                if mode == 'per_dispatch':
                    for _ in range(7):
                        store.quarantine_submission(None, uuid.uuid4().hex, dispatch,
                            reason='response_too_large', content=None, now=100)
                    expected_kind, expected_count, expected_groups = 'dispatch_overflow', 8, 1
                else:
                    # Strict-loadable metadata-only fixture at REAL limits, no cap patches.
                    value = json.loads(store.diagnostic_store.path.read_text(encoding='utf-8'))
                    value['diagnostics'] = {}
                    for _ in range(256):
                        group = uuid.uuid4().hex
                        for _ in range(4 if mode == 'global_records' else 1):
                            detail = deepcopy(row)
                            detail.update(dispatch_id=group, attempt_id=uuid.uuid4().hex)
                            key = {name: detail[name] for name in ('request_id', 'attempt_id', 'dispatch_id',
                                'reason', 'sha256', 'byte_count', 'actor_identity_id')}
                            detail['id'] = uuid.uuid5(uuid.NAMESPACE_URL, canonical_utf8(key).decode('utf-8')).hex
                            value['diagnostics'][detail['id']] = detail
                    store.diagnostic_store.path.write_text(json.dumps(value), encoding='utf-8')
                    store = ArtifactStore(store.root)
                    dispatch = uuid.uuid4().hex
                    expected_kind = 'store_overflow'
                    expected_count, expected_groups = (1024 if mode == 'global_records' else 256), 256
                summary = store.quarantine_submission(None, uuid.uuid4().hex, dispatch,
                    reason='response_too_large', content=None, now=101)
                self.assertEqual(summary['kind'], expected_kind)
                self.assertEqual(summary['latest_reason'], 'response_too_large')
                report = ArtifactStore(store.root).diagnostics()
                self.assertEqual(report['detailed_count'], expected_count)
                self.assertEqual(report['dispatch_group_count'], expected_groups)


if __name__ == '__main__':
    unittest.main()
