"""Import preparation faults/concurrency; real stores, no ZIP or worker claims."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import threading
import unittest

import artifact_store
from tests import test_artifact_imported_store as fixture


class ArtifactImportPlanTests(unittest.TestCase):
    setUp = fixture.ArtifactImportedStoreTests.setUp
    packet = fixture.ArtifactImportedStoreTests.packet
    audit = fixture.ArtifactImportedStoreTests.audit
    portable = fixture.ArtifactImportedStoreTests.portable
    source_graph = fixture.ArtifactImportedStoreTests.source_graph

    def test_malformed_packet_content_is_fixed_validation_without_any_staging(self):
        graph, audit, _ = self.source_graph(attempts=False)
        portable, objects = deepcopy(graph[0]), dict(graph[1])
        raw = b'not JSON'
        portable['requests'][0]['scope'].update(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
        objects[('packet', audit['scope']['packet_id'])] = raw
        with self.assertRaises(artifact_store.ArtifactValidationError):
            self.target.prepare_import_lineage(portable, objects)
        self.assertFalse(self.target.path.exists())
        self.assertFalse(list(self.target.root.rglob('*.md')))
        self.assertFalse(list(self.target.root.rglob('*.json')))

    def test_two_commits_of_same_prepared_lineage_create_once_without_merging(self):
        graph, audit, version = self.source_graph(attempts=False)
        first = self.target.prepare_import_lineage(*graph)
        second = self.target.prepare_import_lineage(*graph)
        barrier = threading.Barrier(2)
        def commit(plan):
            barrier.wait(timeout=5)
            with self.service._boundary():
                return self.target.import_lineage(plan, channel='review')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(commit, (first, second)))
        self.assertEqual(sorted(row['status'] for row in results), ['created', 'skipped'])
        self.assertEqual(next(row for row in results if row['status']=='skipped')['reason'], 'duplicate')
        self.assertEqual(self.target.export_lineage_ids(), (audit['lineage_id'],))
        self.assertEqual(self.target.list_versions(audit['lineage_id'])['count'], 1)
        self.assertEqual(self.target.get_version(version['id'])['markdown'].encode('utf-8'),
                         graph[1][('version', version['id'])])


if __name__ == '__main__': unittest.main()
