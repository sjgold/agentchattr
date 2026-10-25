"""Pure portable projections and in-memory ZIP metadata, no archive driver."""
from copy import deepcopy
import importlib
import io
import json
from pathlib import Path
import stat
import unittest
import zipfile

from tests import test_artifact_imported_store as fixture


class ArtifactArchiveCodecTests(unittest.TestCase):
    setUp=fixture.ArtifactImportedStoreTests.setUp
    packet=fixture.ArtifactImportedStoreTests.packet
    audit=fixture.ArtifactImportedStoreTests.audit
    portable=fixture.ArtifactImportedStoreTests.portable
    source_graph=fixture.ArtifactImportedStoreTests.source_graph
    graph_for_packet=fixture.ArtifactImportedStoreTests.graph_for_packet

    @staticmethod
    def headers():
        rows=[]
        for number,name in enumerate(('manifest.json','artifacts/index.json')):
            row=zipfile.ZipInfo(name);row.header_offset=number*100
            row.file_size=2;row.compress_size=2;row.compress_type=zipfile.ZIP_STORED
            rows.append(row)
        return rows

    @staticmethod
    def zip_bytes(manifest,index,objects):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
            zf.writestr('manifest.json',json.dumps(manifest))
            zf.writestr('artifacts/index.json',json.dumps(index))
            for name,raw in objects.items():zf.writestr(name,raw)
        return buffer.getvalue()

    def test_export_built_projection_drops_authority_at_every_nested_boundary(self):
        codec=importlib.import_module('artifact_archive')
        graph,audit,version=self.source_graph(attempts=False)
        snapshot=self.source.export_metadata(audit['lineage_id'])
        sentinel='APP_AUTHORITY_CANARY_81c9'
        request=snapshot['requests'][0];producer=request['audit']['producer']
        producer.update(launch_attempt=sentinel,launch_nonce=sentinel,fingerprint=sentinel,
                        capabilities=[sentinel],token=sentinel,path=sentinel)
        request['audit']['scope']['message_refs'][0]['owner']=sentinel
        request['audit']['scope']['seal']=sentinel
        request['audit']['brief_id']=sentinel
        request['import_source']={'archive_id':'first-origin','original_state':'fulfilled',
                                  'original_reason':None,'secret':sentinel}
        snapshot['versions'][0]['provenance']['observation']['token']=sentinel
        snapshot['lineage']['path']=sentinel
        result=codec.portable_lineage(snapshot,archive_id='current-export')
        self.assertEqual(result['requests'][0]['import_source']['archive_id'],'first-origin')
        encoded=json.dumps(result,ensure_ascii=False)
        self.assertNotIn(sentinel,encoded)
        self.assertEqual(result['requests'][0]['scope']['message_refs'],audit['scope']['message_refs'])
        self.assertEqual(set(result['requests'][0]['producer']),
            {'name','identity_id','adapter','requested_model','requested_model_reason'})
        self.assertNotIn('attempt_id',encoded);self.assertNotIn('dispatch_id',encoded)
        self.assertNotIn('brief_id',encoded);self.assertNotIn('launch_nonce',encoded)
        request['audit']['expected_parent']={'version_id':'f'*32,'sequence':7,'sha256':'e'*64,'owner':sentinel}
        parent=codec.portable_lineage(snapshot,archive_id='current-export')['requests'][0]['expected_parent']
        self.assertEqual(parent,{'version_id':'f'*32,'sequence':7,'sha256':'e'*64})

    def test_artifact_member_names_are_derived_from_exact_validated_ids(self):
        codec=importlib.import_module('artifact_archive')
        self.assertEqual(codec.member_name('version','a'*32),'artifacts/objects/'+('a'*32)+'.md')
        self.assertEqual(codec.member_name('packet','b'*32),'artifacts/packets/'+('b'*32)+'.json')
        for kind,identifier in (('other','a'*32),('version','../secret'),('packet','A'*32)):
            with self.subTest(kind=kind),self.assertRaises(ValueError):codec.member_name(kind,identifier)

    def test_manifest_allowlist_and_packet_user_data_are_preserved_separately(self):
        codec=importlib.import_module('artifact_archive')
        packet=self.packet();packet['messages'][0]['provenance']['launch_nonce']='USER_DATA_CANARY'
        graph,audit,version=self.graph_for_packet(packet)
        index=codec.portable_index([self.source.export_metadata(audit['lineage_id'])],archive_id='archive-fixture')
        base={'schema_version':1,'archive_id':'archive-fixture','created_at':'2026-10-25T00:00:00Z',
            'product':'agentchattr','app_version':'test','counts':{'messages':1,'jobs':0,'rules':0,'summaries':0,
            'token':'APP_AUTHORITY_CANARY'},'attachments_included':False,'seal':'APP_AUTHORITY_CANARY'}
        manifest=codec.artifact_manifest(base,index)
        self.assertEqual(set(manifest),{'schema_version','archive_id','created_at','product','app_version',
                                       'counts','attachments_included','artifacts'})
        self.assertNotIn('APP_AUTHORITY_CANARY',json.dumps(manifest))
        self.assertEqual(manifest['artifacts'],{'version':1,'lineages':1,'requests':1,'versions':1,'packets':1,
            'markdown_bytes':version['byte_length'],'source_bytes':audit['scope']['byte_length'],'copied_source_text':True})
        members={codec.member_name(kind,key):raw for (kind,key),raw in graph[1].items()}
        data=self.zip_bytes(manifest,index,members)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            section=codec.preflight(zf,zip_size=len(data))
            bodies=codec.read_lineage_objects(zf,section['index']['lineages'][0])
        self.assertEqual(bodies,graph[1])
        self.assertIn(b'USER_DATA_CANARY',bodies[('packet',audit['scope']['packet_id'])])

    def test_header_metadata_hazards_are_fixed_section_refusals(self):
        codec=importlib.import_module('artifact_archive')
        for bad in ('../x','/artifacts/index.json','C:/x','artifacts\\index.json','artifacts/index.json\0x',
                    'ARTIFACTS/index.json','\uff41rtifacts/index.json','artifacts/objects/no.md','unknown.txt'):
            with self.subTest(name=bad):
                rows=self.headers();rows[1].filename=bad;rows[1].orig_filename=bad
                with self.assertRaises(codec.ArtifactSectionError):codec.validate_headers(rows)
        for bad in ('encrypted','symlink','directory','other_type','compression','duplicate','normalized_duplicate','offset'):
            with self.subTest(kind=bad):
                rows=self.headers()
                if bad=='encrypted':rows[1].flag_bits=1
                elif bad=='symlink':rows[1].external_attr=(stat.S_IFLNK|0o777)<<16
                elif bad=='directory':rows[1].external_attr=0x10
                elif bad=='other_type':rows[1].external_attr=(stat.S_IFCHR|0o600)<<16
                elif bad=='compression':rows[1].compress_type=zipfile.ZIP_BZIP2
                elif bad=='offset':rows[1].header_offset=rows[0].header_offset
                else:
                    row=zipfile.ZipInfo('MANIFEST.JSON' if bad=='normalized_duplicate' else 'manifest.json')
                    row.header_offset=999;row.file_size=row.compress_size=0;rows.append(row)
                with self.assertRaises(codec.ArtifactSectionError) as caught:codec.validate_headers(rows)
                self.assertEqual(caught.exception.code,'artifact_archive_invalid_section')
        self.assertTrue(codec.has_artifact_members([zipfile.ZipInfo('ARTIFACTS/index.json')]))
        self.assertTrue(codec.has_artifact_members([zipfile.ZipInfo('\uff41rtifacts/index.json')]))

    def test_global_limit_precedence_uses_real_default_values(self):
        codec=importlib.import_module('artifact_archive')
        for bound in ('members','index','lineages','ratio','uncompressed','zip'):
            with self.subTest(bound=bound):
                rows=self.headers();options={'lineage_count':0,'zip_size':0}
                if bound=='members':
                    for number in range(4095):
                        row=zipfile.ZipInfo('artifacts/objects/'+format(number,'032x')+'.md')
                        row.header_offset=1000+number*100;row.file_size=row.compress_size=0;rows.append(row)
                elif bound=='index':rows[1].file_size=4194305
                elif bound=='lineages':options['lineage_count']=1025
                elif bound=='ratio':rows[0].file_size=1001;rows[0].compress_size=1
                elif bound=='uncompressed':
                    rows[0].filename=rows[0].orig_filename='messages.jsonl'
                    rows[0].file_size=rows[0].compress_size=50*1024*1024
                else:options['zip_size']=50*1024*1024+1
                with self.assertRaises(codec.ArtifactSectionError) as caught:codec.validate_headers(rows,**options)
                self.assertEqual((caught.exception.code,caught.exception.bound),('artifact_archive_limit',bound))

    def test_index_structure_cross_lineage_and_unknown_members_refuse_before_body_reads(self):
        codec=importlib.import_module('artifact_archive')
        graph,audit,_=self.source_graph(attempts=False)
        index={'version':1,'lineages':[graph[0]]}
        self.assertEqual(codec.validate_index(json.dumps(index).encode()),index)
        for mutation in ('extra','duplicate_keys','duplicate_lineage','duplicate_request','cross_parent','unsafe_ref','unknown_member'):
            with self.subTest(mutation=mutation):
                changed=deepcopy(index);names=None
                if mutation=='extra':changed['token']='EXTRA'
                elif mutation=='duplicate_keys':
                    with self.assertRaises(codec.ArtifactSectionError):codec.validate_index(b'{"version":1,"version":1,"lineages":[]}')
                    continue
                elif mutation=='duplicate_lineage':changed['lineages'].append(deepcopy(changed['lineages'][0]))
                elif mutation=='duplicate_request':changed['lineages'][0]['requests'].append(deepcopy(changed['lineages'][0]['requests'][0]))
                elif mutation=='cross_parent':
                    other,_,_=self.source_graph(attempts=False);changed['lineages'].append(other[0])
                    changed['lineages'][0]['requests'][0]['expected_parent']={
                        'version_id':other[0]['versions'][0]['version_id'],'sequence':1,'sha256':other[0]['versions'][0]['sha256']}
                elif mutation=='unsafe_ref':changed['lineages'][0]['requests'][0]['scope']['packet_id']='../bad'
                else:names={'manifest.json','artifacts/index.json','artifacts/objects/'+('f'*32)+'.md'}
                with self.assertRaises(codec.ArtifactSectionError):codec.validate_index(json.dumps(changed).encode(),member_names=names)

    def test_object_cap_and_hash_failures_are_lineage_local_after_structural_preflight(self):
        codec=importlib.import_module('artifact_archive')
        graph,_,_=self.source_graph(attempts=False)
        for problem in ('missing','hash','markdown_cap','packet_cap','message_cap'):
            with self.subTest(problem=problem):
                lineage=deepcopy(graph[0]);members={codec.member_name(*key):raw for key,raw in graph[1].items()}
                if problem=='missing':members.clear()
                elif problem=='hash':members[codec.member_name('version',lineage['versions'][0]['version_id'])]=b'WRONG'
                elif problem=='markdown_cap':lineage['versions'][0]['byte_length']=524289
                elif problem=='packet_cap':lineage['requests'][0]['scope']['byte_length']=2097153
                else:
                    refs=lineage['requests'][0]['scope']['message_refs']
                    refs[:]=[{'id':i,'uid':'m'+str(i),'sha256':'a'*64} for i in range(1001)]
                index={'version':1,'lineages':[lineage]}
                codec.validate_index(json.dumps(index).encode())
                data=self.zip_bytes({},index,members)
                with zipfile.ZipFile(io.BytesIO(data)) as zf,self.assertRaises(codec.ArtifactLineageError):
                    codec.read_lineage_objects(zf,lineage)

    def test_manifest_strict_types_dates_and_schema_ownership(self):
        codec=importlib.import_module('artifact_archive')
        graph,audit,_=self.source_graph(attempts=False)
        index={'version':1,'lineages':[graph[0]]}
        base={'schema_version':1,'archive_id':'archive-fixture','created_at':'2026-10-25T00:00:00Z',
            'product':'agentchattr','app_version':'test','counts':{'messages':0,'jobs':0,'rules':0,'summaries':0},
            'attachments_included':False}
        valid=codec.artifact_manifest(base,index)
        for field in ('bool_version','bool_count','bad_date','extra_artifact','bad_flag','wrong_hash_count'):
            with self.subTest(field=field):
                changed=deepcopy(valid)
                if field=='bool_version':changed['artifacts']['version']=True
                elif field=='bool_count':changed['artifacts']['versions']=True
                elif field=='bad_date':changed['created_at']='2026-99-99T99:99:99Z'
                elif field=='extra_artifact':changed['artifacts']['token']='EXTRA'
                elif field=='bad_flag':changed['artifacts']['copied_source_text']=1
                else:changed['artifacts']['source_bytes']+=1
                with self.assertRaises(codec.ArtifactSectionError):codec.validate_manifest(changed,index,artifact_present=True)
        with self.assertRaises(codec.ArtifactSectionError) as caught:
            codec.validate_manifest(base,index,artifact_present=True)
        self.assertEqual(caught.exception.code,'artifact_archive_schema_mismatch')
        history_only={**base,'schema_version':2}
        codec.validate_manifest(history_only,None,artifact_present=False)

    def test_real_zip_crc_body_failure_is_local_and_global_structure_is_not_ignored(self):
        codec=importlib.import_module('artifact_archive')
        graph,audit,_=self.source_graph(attempts=False)
        index={'version':1,'lineages':[graph[0]]}
        base={'schema_version':1,'archive_id':'archive-fixture','created_at':'2026-10-25T00:00:00Z',
            'product':'agentchattr','app_version':'test','counts':{'messages':0,'jobs':0,'rules':0,'summaries':0},
            'attachments_included':False}
        manifest=codec.artifact_manifest(base,index)
        members={codec.member_name(*key):raw for key,raw in graph[1].items()}
        data=self.zip_bytes(manifest,index,members)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            info=zf.getinfo(codec.member_name('version',graph[0]['versions'][0]['version_id']))
            offset=info.header_offset+30+len(info.filename.encode())+len(info.extra)
        corrupt=bytearray(data);corrupt[offset]^=1
        with zipfile.ZipFile(io.BytesIO(corrupt)) as zf:
            codec.preflight(zf,zip_size=len(corrupt))
            with self.assertRaises(codec.ArtifactLineageError):codec.read_lineage_objects(zf,graph[0])
        extra={**members,'artifacts/objects/'+('f'*32)+'.md':b'UNREFERENCED'}
        data=self.zip_bytes(manifest,index,extra)
        with zipfile.ZipFile(io.BytesIO(data)) as zf,self.assertRaises(codec.ArtifactSectionError):
            codec.preflight(zf,zip_size=len(data))
        # Missing referenced members are lineage-local after structural preflight.
        data=self.zip_bytes(manifest,index,{})
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            codec.preflight(zf,zip_size=len(data))
            with self.assertRaises(codec.ArtifactLineageError):codec.read_lineage_objects(zf,graph[0])

    def test_literal_contract_projection_golden_covers_all_built_metadata(self):
        codec=importlib.import_module('artifact_archive')
        fixture=json.loads((Path(__file__).parent/'fixtures'/'artifact_portable_projection.json').read_text(encoding='utf-8'))
        lineage=codec.portable_lineage(fixture['snapshot'],archive_id='literal-archive')
        self.assertEqual(lineage,fixture['expected_lineage'])
        index=codec.portable_index([fixture['snapshot']],archive_id='literal-archive')
        self.assertEqual(index,{'version':1,'lineages':[fixture['expected_lineage']]})
        manifest=codec.artifact_manifest(fixture['history'],index)
        self.assertEqual(manifest,fixture['expected_manifest'])
        self.assertNotIn(fixture['canary'],json.dumps({'index':index,'manifest':manifest}))

    def test_actual_deflate_ratio_guard_and_combined_limit_precedence(self):
        codec=importlib.import_module('artifact_archive')
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zf:
            zf.writestr('manifest.json','{}')
            zf.writestr('artifacts/index.json','{"version":1,"lineages":[]}')
            zf.writestr('messages.jsonl',b'x'*(2*1024*1024))
        data=buffer.getvalue()
        with zipfile.ZipFile(io.BytesIO(data)) as zf,self.assertRaises(codec.ArtifactSectionError) as caught:
            codec.preflight(zf,zip_size=len(data))
        self.assertEqual((caught.exception.code,caught.exception.bound),('artifact_archive_limit','ratio'))
        rows=self.headers();rows[0].file_size=50*1024*1024+1;rows[0].compress_size=1
        rows[0].filename=rows[0].orig_filename='messages.jsonl'
        with self.assertRaises(codec.ArtifactSectionError) as caught:
            codec.validate_headers(rows,lineage_count=1025,zip_size=50*1024*1024+1)
        self.assertEqual(caught.exception.bound,'ratio')
        rows[1].file_size=4194305
        with self.assertRaises(codec.ArtifactSectionError) as caught:
            codec.validate_headers(rows,lineage_count=1025,zip_size=50*1024*1024+1)
        self.assertEqual(caught.exception.bound,'index')

    def test_exact_global_and_object_boundaries_are_accepted_without_lowered_caps(self):
        codec=importlib.import_module('artifact_archive')
        raw=b'{"version":1,"lineages":[]}'
        self.assertEqual(codec.validate_index(raw+b' '*(4194304-len(raw))),{'version':1,'lineages':[]})
        with self.assertRaises(codec.ArtifactSectionError) as caught:codec.validate_index(b' '*(4194305))
        self.assertEqual(caught.exception.bound,'index')
        rows=self.headers()
        for number in range(4094):
            row=zipfile.ZipInfo('artifacts/objects/'+format(number,'032x')+'.md')
            row.header_offset=1000+number*100;row.file_size=row.compress_size=0;rows.append(row)
        self.assertEqual(len(codec.validate_headers(rows,lineage_count=1024,zip_size=50*1024*1024)),4096)
        rows=self.headers();rows[0].file_size=1000;rows[0].compress_size=1
        codec.validate_headers(rows)
        graph,_,_=self.source_graph(text='x'*524288,attempts=False)
        lineage=graph[0];members={codec.member_name(*key):raw for key,raw in graph[1].items()}
        data=self.zip_bytes({}, {'version':1,'lineages':[lineage]},members)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            self.assertEqual(codec.read_lineage_objects(zf,lineage),graph[1])


if __name__=='__main__':unittest.main()
