"""Private staging observations only; no persisted/public authority fields."""
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import artifact_store as module
from tests import test_artifact_imported_store as fixture


class ArtifactStagingReceiptTests(unittest.TestCase):
    setUp=fixture.ArtifactImportedStoreTests.setUp
    packet=fixture.ArtifactImportedStoreTests.packet
    audit=fixture.ArtifactImportedStoreTests.audit
    portable=fixture.ArtifactImportedStoreTests.portable
    source_graph=fixture.ArtifactImportedStoreTests.source_graph

    def test_immutable_put_returns_created_true_only_for_its_own_write(self):
        identifier=uuid.uuid4().hex
        path=self.target._object_path('version',identifier)
        self.assertIs(self.target._put_bytes(path,b'# immutable\r\n'),True)
        self.assertIs(self.target._put_bytes(path,b'# immutable\r\n'),False)
        self.assertEqual(path.read_bytes(),b'# immutable\r\n')

    def test_created_reused_failed_index_and_duplicate_receipts_count_only_unreferenced(self):
        graph,audit,version=self.source_graph(attempts=False)
        first=self.target.prepare_import_lineage(*graph)
        reused=self.target.prepare_import_lineage(*graph)
        self.assertEqual(len(first.created_objects),2)
        self.assertEqual(reused.created_objects,())
        expected={'objects':2,'bytes':sum(len(raw) for raw in graph[1].values())}
        with patch.object(Path,'open',side_effect=AssertionError('orphan report read a body')):
            self.assertEqual(self.target._import_orphans(first.created_objects),expected)
        with patch('artifact_store.atomic_json',side_effect=OSError('controlled index write')):
            with self.service._boundary(),self.assertRaises(module.ArtifactUnavailable):
                self.target.import_lineage(first,channel='review')
        self.assertEqual(self.target._import_orphans(first.created_objects),expected)
        self.assertEqual(self.target._import_orphans(reused.created_objects),{'objects':0,'bytes':0})
        self.assertEqual(self.target.export_lineage_ids(),())
        with self.service._boundary():self.target.import_lineage(reused,channel='review')
        self.assertEqual(self.target._import_orphans(first.created_objects),{'objects':0,'bytes':0})
        duplicate=self.target.prepare_import_lineage(*graph)
        self.assertEqual(duplicate.created_objects,())
        self.assertEqual(self.target._import_orphans(duplicate.created_objects),{'objects':0,'bytes':0})
        self.assertNotIn('created_objects',self.target.path.read_text(encoding='utf-8'))
        self.assertNotIn('created_objects',self.target.get_request(audit['request_id']))

    def test_concurrent_import_receipts_never_count_reused_or_winner_referenced_files(self):
        graph,_,_=self.source_graph(attempts=False);barrier=threading.Barrier(2)
        def run(_):
            plan=self.target.prepare_import_lineage(*graph)
            barrier.wait(timeout=5)
            with self.service._boundary():result=self.target.import_lineage(plan,channel='review')
            return plan,result
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,range(2)))
        self.assertEqual(sorted(result['status'] for _,result in results),['created','skipped'])
        self.assertEqual(sum(len(plan.created_objects) for plan,_ in results),2)
        for plan,result in results:
            self.assertEqual(self.target._import_orphans(plan.created_objects),{'objects':0,'bytes':0})

    def test_mid_staging_io_is_unknown_with_fixed_reason_and_preserves_leftovers(self):
        graph,audit,_=self.source_graph(attempts=False)
        original=self.target._put_bytes
        def fail(path,raw):
            if path.suffix=='.md':raise OSError('PRIVATE_IO_ERROR')
            return original(path,raw)
        with patch.object(self.target,'_put_bytes',side_effect=fail),self.assertRaises(module.ArtifactUnavailable) as caught:
            self.target.prepare_import_lineage(*graph)
        self.assertIsNone(caught.exception._created_objects)
        self.assertEqual(caught.exception._orphan_reason,'staging_io_unconfirmed')
        self.assertIsNone(self.target._import_orphans(caught.exception._created_objects))
        self.assertNotIn('PRIVATE_IO_ERROR',str(caught.exception))
        self.assertEqual(self.target.export_lineage_ids(),())
        self.assertTrue(any(row['kind']=='orphan_packet' and row['id']==audit['scope']['packet_id']
                            for row in self.target.diagnostics()['rows']))


if __name__=='__main__':unittest.main()
