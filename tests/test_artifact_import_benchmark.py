"""Measured whole-boundary import gate; default writer and real temporary files."""
import hashlib
import json
from pathlib import Path
import threading
import time
import unittest
import uuid

import artifact_store as module
from sealed_result_io import canonical_utf8
from tests import test_artifact_store as fixture


def graph(count, *, exact_bytes=None):
    requests,versions,objects=[],[],{}
    lineage=uuid.uuid4().hex
    parent=None
    packet={'version':1,'channel':'review','scope_kind':'selected_channel_messages',
            'source_run':None,'input':None,'messages':[]}
    packet_raw=canonical_utf8(packet)
    for sequence in range(1,count+1):
        request=uuid.uuid4().hex;ids=module.request_ids(request)
        raw=('# '+str(sequence)+'\r\n').encode('utf-8')
        digest=hashlib.sha256(raw).hexdigest()
        scope=module._packet_scope(ids['packet_id'],packet)
        requests.append({'request_id':request,'original_channel':'review','requester':'operator',
            'producer':{'name':'archive-author','identity_id':'a'*32,'adapter':'cli',
                        'requested_model':None,'requested_model_reason':'cli_model_unverified'},
            'source_run':None,'scope':scope,'instruction':'x','format':'Markdown','expected_parent':parent,
            'created_at':10,'updated_at':20,'import_source':{'archive_id':'benchmark',
                'original_state':'fulfilled','original_reason':None}})
        versions.append({'version_id':ids['version_id'],'request_id':request,'sequence':sequence,
            'parent_version_id':parent['version_id'] if parent else None,'sha256':digest,'byte_length':len(raw),
            'created_at':20,'observation':{'confirmed_model':None,'confirmation_reason':'cli_model_unverified'}})
        objects[('packet',ids['packet_id'])]=packet_raw
        objects[('version',ids['version_id'])]=raw
        parent={'version_id':ids['version_id'],'sequence':sequence,'sha256':digest}
    portable={'lineage_id':lineage,'channel':'review','updated_at':20,'head_version_id':parent['version_id'],
              'requests':requests,'versions':versions}
    envelope={'version':1,'lineages':[portable]}
    if exact_bytes is not None:
        remaining=exact_bytes-len(canonical_utf8(envelope))
        for request in requests:
            add=min(32768-len(request['instruction'].encode('utf-8')),remaining)
            request['instruction']+='x'*add;remaining-=add
        if remaining or len(canonical_utf8(envelope))!=exact_bytes:raise AssertionError('Exact envelope not built')
    return portable,objects


class ArtifactImportBenchmarkTests(unittest.TestCase):
    setUp=fixture.ArtifactStoreTests.setUp

    def test_ten_four_mib_imports_with_one_hundred_existing_lineages_meet_basic_responsiveness(self):
        existing=[graph(1) for _ in range(100)]
        large=graph(128,exact_bytes=4194304)
        self.assertEqual(len(canonical_utf8({'version':1,'lineages':[large[0]]})),4194304)
        self.assertEqual(len(large[1])+6,262)  # Five history members plus the artifact index.
        samples=[];baselines=[];stop=threading.Event();progress=threading.Event();errors=[]
        def peer():
            try:
                while not stop.is_set():
                    self.service.require_active('peer');progress.set()
                    stop.wait(.001)
            except BaseException as error:errors.append(type(error).__name__)
        worker=threading.Thread(target=peer,name='artifact-import-benchmark-peer')
        worker.start()
        try:
            for number in range(10):
                owner=module.ArtifactStore(self.root/('bench-'+str(number)))
                owner.bind_channel_policy(lambda:self.service)
                for portable,objects in existing:
                    plan=owner.prepare_import_lineage(portable,objects)
                    with self.service._boundary():owner.import_lineage(plan,channel='review')
                self.assertEqual(len(owner.export_lineage_ids()),100)
                self.assertEqual(sum(len(owner.export_metadata(key)['lineage']['version_ids'])
                                     for key in owner.export_lineage_ids()),100)
                prepared=owner.prepare_import_lineage(*large)
                progress.clear()
                self.assertTrue(progress.wait(2))
                baseline=time.perf_counter()
                with self.service._boundary():self.service.require_active('peer')
                baselines.append(time.perf_counter()-baseline)
                started=time.perf_counter()
                # Includes engine/catalog acquisition, metadata JSON parse,
                # collision recheck, full _persist validation and default fsync.
                with self.service._boundary():result=owner.import_lineage(prepared,channel='review')
                samples.append(time.perf_counter()-started)
                self.assertEqual((result['created_requests'],result['created_versions']),(128,128))
                progress.clear();self.assertTrue(progress.wait(2))
        finally:
            stop.set();worker.join(timeout=5)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        receipt={'method':'store/catalog real-files Windows default atomic_json',
            'portable_envelope_bytes':4194304,'existing_lineages':100,'existing_versions':100,
            'requests':128,'versions':128,'packet_objects':128,'zip_member_count':262,
            'baseline_seconds':baselines,'samples_seconds':samples,'maximum_seconds':max(samples),'target_seconds':.300,'target_met':max(samples)<=.300,
            'limit_seconds':1.0,'limit_policy':'reduced first-release basic responsiveness',
            'includes_metadata_parse':True,'includes_whole_index_validation':True,'fsync_mocked':False}
        destination=Path(__file__).resolve().parents[1]/'.audit-tmp'/'ticket20-import-benchmark.json'
        destination.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print(json.dumps(receipt))
        # Reviewed2026-10-26: always report300ms target, enforce1s basic release ceiling.
        self.assertLessEqual(max(samples),1.0)


if __name__=='__main__':unittest.main()
