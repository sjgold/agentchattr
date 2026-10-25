"""Codec review fault cases on real in-memory ZIP streams; no app mutations."""
from copy import deepcopy
import io
import json
from pathlib import Path
import stat
import struct
import unittest
from unittest.mock import patch
import warnings
import zipfile

import artifact_archive as codec
from tests import test_artifact_archive_codec as fixture


class ArtifactArchiveCodecReviewTests(unittest.TestCase):
    setUp=fixture.ArtifactArchiveCodecTests.setUp
    packet=fixture.ArtifactArchiveCodecTests.packet
    audit=fixture.ArtifactArchiveCodecTests.audit
    portable=fixture.ArtifactArchiveCodecTests.portable
    source_graph=fixture.ArtifactArchiveCodecTests.source_graph

    def archive(self):
        graph,_,_=self.source_graph(attempts=False)
        index={'version':1,'lineages':[graph[0]]}
        base={'schema_version':1,'archive_id':'fault-fixture','created_at':'2026-10-25T00:00:00Z',
            'product':'agentchattr','app_version':'test','counts':{'messages':0,'jobs':0,'rules':0,'summaries':0},
            'attachments_included':False}
        manifest=codec.artifact_manifest(base,index)
        import json
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zf:
            zf.writestr('manifest.json',json.dumps(manifest))
            zf.writestr('artifacts/index.json',json.dumps(index))
            for key,raw in graph[1].items():zf.writestr(codec.member_name(*key),raw)
        return buffer.getvalue(),graph,index,manifest

    def test_real_deflate_corruption_and_truncation_are_fixed_at_both_read_boundaries(self):
        data,graph,index,manifest=self.archive()
        for where in ('index','object'):
            for fault in ('deflate','truncated'):
                with self.subTest(where=where,fault=fault):
                    name=codec.INDEX_MEMBER if where=='index' else codec.member_name('version',graph[0]['versions'][0]['version_id'])
                    buffer=io.BytesIO(data);zf=zipfile.ZipFile(buffer)
                    self.addCleanup(zf.close)
                    info=zf.getinfo(name)
                    offset=info.header_offset+30+len(info.filename.encode('utf-8'))+len(info.extra)
                    if fault=='deflate':
                        buffer.seek(offset);buffer.write(b'\x07')  # Reserved raw-DEFLATE block type.
                    else:buffer.truncate(offset+1)  # Real backing stream truncated after metadata was read.
                    with self.assertRaises(codec.ArtifactSectionError if where=='index' else codec.ArtifactLineageError) as caught:
                        if where=='index':codec.preflight(zf,zip_size=len(data))
                        else:codec.read_lineage_objects(zf,graph[0])
                    if where=='index':self.assertEqual(caught.exception.code,'artifact_archive_invalid_section')

    def test_backing_stream_io_failure_is_fatal_storage_at_both_read_boundaries(self):
        data,graph,_,_=self.archive()
        class Fault(io.BytesIO):
            armed=False
            def read(self,*args,**kwargs):
                if self.armed:raise OSError('PRIVATE_IO_ERROR')
                return super().read(*args,**kwargs)
        for where in ('index','object'):
            with self.subTest(where=where):
                buffer=Fault(data)
                with zipfile.ZipFile(buffer) as zf:
                    buffer.armed=True
                    with self.assertRaises(codec.ArtifactSectionError) as caught:
                        if where=='index':codec.preflight(zf,zip_size=len(data))
                        else:codec.read_lineage_objects(zf,graph[0])
                self.assertEqual((caught.exception.code,caught.exception.http_status),
                                 ('artifact_archive_storage_unavailable',503))
                self.assertNotIn('PRIVATE_IO_ERROR',str(caught.exception))

    def test_manifest_date_requires_ascii_digits(self):
        _,_,index,manifest=self.archive()
        manifest['created_at']='\u0662\u0660\u0662\u0666-10-25T00:00:00Z'
        with self.assertRaises(codec.ArtifactSectionError):codec.validate_manifest(manifest,index,artifact_present=True)

    def test_header_hazards_and_manifest_cap_precede_any_decompression(self):
        for problem in ('unsafe_and_oversized_index','manifest_cap','unsupported_index_compression'):
            with self.subTest(problem=problem):
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
                    zf.writestr('manifest.json',b' '*(65537 if problem=='manifest_cap' else 2))
                    zf.writestr('artifacts/index.json',b' '*(4194305 if problem=='unsafe_and_oversized_index' else 2))
                    if problem=='unsafe_and_oversized_index':zf.writestr('../unsafe',b'x')
                with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as zf:
                    if problem=='unsupported_index_compression':zf.getinfo(codec.INDEX_MEMBER).compress_type=99
                    from unittest.mock import patch
                    with patch.object(codec,'_bounded_read',side_effect=AssertionError('decompressed before headers')):
                        with self.assertRaises(codec.ArtifactSectionError) as caught:
                            codec.preflight(zf,zip_size=len(buffer.getvalue()))
                self.assertEqual(caught.exception.code,'artifact_archive_limit' if problem=='manifest_cap'
                                 else 'artifact_archive_invalid_section')
                if problem=='manifest_cap':self.assertEqual(caught.exception.bound,'manifest')

    @staticmethod
    def central_offsets(data):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:position=zf.start_dir
        result={}
        while data[position:position+4]==b'PK\x01\x02':
            name,extra,comment=struct.unpack_from('<HHH',data,position+28)
            result[data[position+46:position+46+name].decode('utf-8')]=position
            position+=46+name+extra+comment
        return result

    def test_real_duplicate_encrypted_symlink_directory_offset_and_zip64_headers(self):
        data,graph,index,manifest=self.archive()
        for hazard in ('duplicate','encrypted','symlink','directory','duplicate_offset','normalized_duplicate'):
            with self.subTest(hazard=hazard):
                if hazard in ('encrypted','duplicate_offset'):
                    raw=bytearray(data);central=self.central_offsets(data)[codec.INDEX_MEMBER]
                    with zipfile.ZipFile(io.BytesIO(data)) as zf:local=zf.getinfo(codec.INDEX_MEMBER).header_offset
                    if hazard=='encrypted':
                        struct.pack_into('<H',raw,local+6,1);struct.pack_into('<H',raw,central+8,1)
                    else:struct.pack_into('<I',raw,central+42,0)
                    bad=bytes(raw)
                else:
                    buffer=io.BytesIO()
                    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
                        zf.writestr('manifest.json',json.dumps(manifest))
                        info=zipfile.ZipInfo(codec.INDEX_MEMBER)
                        if hazard=='symlink':info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
                        zf.writestr(info,json.dumps(index))
                        if hazard=='directory':zf.writestr('artifacts/',b'')
                        if hazard=='normalized_duplicate':zf.writestr('MANIFEST.JSON',b'{}')
                        if hazard=='duplicate':
                            with warnings.catch_warnings(record=True) as seen:
                                warnings.simplefilter('always');zf.writestr('manifest.json',b'{}')
                            self.assertTrue(any('Duplicate name' in str(row.message) for row in seen))
                    bad=buffer.getvalue()
                with zipfile.ZipFile(io.BytesIO(bad)) as zf,self.assertRaises(codec.ArtifactSectionError) as caught:
                    codec.preflight(zf,zip_size=len(bad))
                self.assertEqual(caught.exception.code,'artifact_archive_invalid_section')
        buffer=io.BytesIO()
        # Writer-only fixture switch forces actual ZIP64 records at small sizes;
        # parsing/limits run with the normal stdlib constant restored.
        with patch('zipfile.ZIP64_LIMIT',0),zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED,allowZip64=True) as zf:
            zf.writestr('manifest.json',json.dumps(manifest));zf.writestr(codec.INDEX_MEMBER,json.dumps(index))
            for key,raw in graph[1].items():zf.writestr(codec.member_name(*key),raw)
        valid=buffer.getvalue();self.assertIn(b'PK\x06\x06',valid)
        with zipfile.ZipFile(io.BytesIO(valid)) as zf:
            codec.preflight(zf,zip_size=len(valid))
            self.assertEqual(codec.read_lineage_objects(zf,graph[0]),graph[1])

    def test_preflight_level_bound_order_and_exact_zip_and_manifest_boundaries(self):
        data,graph,index,manifest=self.archive()
        prefix=b'\0'*(50*1024*1024-len(data));exact=prefix+data
        with zipfile.ZipFile(io.BytesIO(exact)) as zf:
            codec.preflight(zf,zip_size=len(exact))
        # Prefix/trailing bytes are deliberately within the documented stdlib
        # acceptance scope; only their contribution to total ZIP bytes is used.
        with zipfile.ZipFile(io.BytesIO(exact)) as zf,self.assertRaises(codec.ArtifactSectionError) as caught:
            codec.preflight(zf,zip_size=len(exact)+1)
        self.assertEqual(caught.exception.bound,'zip')
        for kind in ('members','ratio','uncompressed'):
            with self.subTest(bound=kind):
                buffer=io.BytesIO()
                compression=zipfile.ZIP_DEFLATED if kind=='ratio' else zipfile.ZIP_STORED
                with zipfile.ZipFile(buffer,'w',compression,compresslevel=6 if compression else None) as zf:
                    zf.writestr('manifest.json',json.dumps(manifest))
                    zf.writestr(codec.INDEX_MEMBER,b' '*(4194305 if kind=='members' else 2))
                    if kind=='members':
                        for number in range(4095):zf.writestr('artifacts/objects/'+format(number,'032x')+'.md',b'')
                    else:zf.writestr('messages.jsonl',b'x'*(50*1024*1024))
                content=buffer.getvalue()
                with zipfile.ZipFile(io.BytesIO(content)) as zf,patch.object(codec,'_bounded_read',
                        side_effect=AssertionError('inflation before header bounds')):
                    with self.assertRaises(codec.ArtifactSectionError) as caught:codec.preflight(zf,zip_size=len(content))
                self.assertEqual(caught.exception.bound,kind)
        buffer=io.BytesIO();raw=json.dumps(manifest).encode('utf-8')
        raw+=b' '*(65536-len(raw))
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
            zf.writestr('manifest.json',raw);zf.writestr(codec.INDEX_MEMBER,json.dumps(index))
        with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as zf:codec.preflight(zf,zip_size=len(buffer.getvalue()))

    def test_index_negative_matrix_and_actual_1024_lineage_index(self):
        _,graph,index,_=self.archive()
        other,_,_=self.source_graph(attempts=False)
        for kind in ('nan','infinity','float_int','bool_timestamp','nested_duplicate','empty_requests',
            'foreign_request','foreign_head','foreign_parent','duplicate_request_dispatch','reused_packet',
            'non_derived_packet','adapter','model_reason','origin_imported','duplicate_ref_id','duplicate_ref_uid','instruction'):
            with self.subTest(kind=kind):
                value=deepcopy(index);lineage=value['lineages'][0];request=lineage['requests'][0]
                if kind=='nan':lineage['updated_at']=float('nan')
                elif kind=='infinity':lineage['updated_at']=float('inf')
                elif kind=='float_int':lineage['versions'][0]['sequence']=1.0
                elif kind=='bool_timestamp':request['created_at']=True
                elif kind=='nested_duplicate':
                    raw=json.dumps(value).replace('"scope": {','"scope": {"kind":"selected_channel_messages",',1).encode()
                    with self.assertRaises(codec.ArtifactSectionError):codec.validate_index(raw)
                    continue
                elif kind=='empty_requests':lineage['requests']=[]
                elif kind.startswith('foreign_') or kind in ('duplicate_request_dispatch','reused_packet'):
                    value['lineages'].append(deepcopy(other[0]));foreign=value['lineages'][1]
                    if kind=='foreign_request':lineage['versions'][0]['request_id']=foreign['requests'][0]['request_id']
                    elif kind=='foreign_head':lineage['head_version_id']=foreign['head_version_id']
                    elif kind=='foreign_parent':lineage['versions'][0]['parent_version_id']=foreign['head_version_id']
                    elif kind=='duplicate_request_dispatch':foreign['requests'][0]=deepcopy(request)
                    else:foreign['requests'][0]['scope']['packet_id']=request['scope']['packet_id']
                elif kind=='non_derived_packet':request['scope']['packet_id']='f'*32
                elif kind=='adapter':request['producer']['adapter']='bogus'
                elif kind=='model_reason':request['producer'].update(requested_model='named',requested_model_reason='also-missing')
                elif kind=='origin_imported':request['import_source']['original_state']='imported'
                elif kind=='instruction':request['instruction']='x'*32769
                else:
                    ref=deepcopy(request['scope']['message_refs'][0])
                    if kind=='duplicate_ref_id':ref['uid']='new-uid'
                    else:ref['id']+=1
                    request['scope']['message_refs'].append(ref)
                with self.assertRaises(codec.ArtifactSectionError):codec.validate_index(json.dumps(value).encode())
        from tests.test_artifact_import_benchmark import graph as create_graph
        value={'version':1,'lineages':[create_graph(1)[0] for _ in range(1024)]}
        raw=json.dumps(value,separators=(',',':')).encode('utf-8')
        self.assertLessEqual(len(raw),4194304)
        self.assertEqual(len(codec.validate_index(raw)['lineages']),1024)
        value['lineages'].append(create_graph(1)[0])
        with self.assertRaises(codec.ArtifactSectionError) as caught:codec.validate_index(json.dumps(value).encode())
        self.assertEqual(caught.exception.bound,'lineages')

    def test_manifest_and_lineage_body_negative_matrices(self):
        data,graph,index,manifest=self.archive()
        for bad in ('archive_id','product','app_version','attachment','artifact_count','schema3','schema_bool',
                    'schema_text','duplicate','missing','no_artifact_key'):
            with self.subTest(manifest=bad):
                value=deepcopy(manifest)
                if bad=='archive_id':value['archive_id']='../invalid'
                elif bad=='product':value['product']='other'
                elif bad=='app_version':value['app_version']='x'*129
                elif bad=='attachment':value['attachments_included']=True
                elif bad=='artifact_count':value['counts']['artifacts']+=1
                elif bad=='schema3':value['schema_version']=3
                elif bad=='schema_bool':value['schema_version']=True
                elif bad=='schema_text':value['schema_version']='2'
                elif bad=='no_artifact_key':value.pop('artifacts')
                raw=json.dumps(value)
                if bad=='duplicate':raw=raw.replace('"archive_id":','"archive_id":"duplicated", "archive_id":',1)
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
                    if bad!='missing':zf.writestr('manifest.json',raw)
                    zf.writestr(codec.INDEX_MEMBER,json.dumps(index))
                    for key,body in graph[1].items():zf.writestr(codec.member_name(*key),body)
                with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as zf,self.assertRaises(codec.ArtifactSectionError):
                    codec.preflight(zf,zip_size=len(buffer.getvalue()))
        for bad in ('packet_noncanonical','packet_hash','source_run','channel','utf8','blank','length'):
            with self.subTest(body=bad):
                lineage=deepcopy(graph[0]);objects=dict(graph[1]);request=lineage['requests'][0];version=lineage['versions'][0]
                if bad in ('packet_noncanonical','packet_hash'):
                    key=('packet',request['scope']['packet_id']);packet=json.loads(objects[key])
                    if bad=='packet_noncanonical':objects[key]=json.dumps(packet,indent=2,ensure_ascii=False).encode()
                    else:packet['messages'][0]['text']='changed';objects[key]=json.dumps(packet,ensure_ascii=False).encode()
                elif bad=='source_run':request['source_run']={'session_id':1,'run_id':'a'*32,'input_revision':'b'*64,'state_at_request':'stopped'}
                elif bad=='channel':request['original_channel']='peer'
                else:
                    key=('version',version['version_id'])
                    if bad=='utf8':objects[key]=b'\xff'
                    elif bad=='blank':objects[key]=b' \r\n '
                    import hashlib
                    version.update(sha256=hashlib.sha256(objects[key]).hexdigest(),
                                   byte_length=len(objects[key])+(1 if bad=='length' else 0))
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
                    for key,body in objects.items():zf.writestr(codec.member_name(*key),body)
                with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as zf,self.assertRaises(codec.ArtifactLineageError):
                    codec.read_lineage_objects(zf,lineage)

    def test_literal_revision_api_unversioned_and_first_origin_projection_golden(self):
        value=json.loads((Path(__file__).parent/'fixtures'/'artifact_portable_revision_projection.json').read_text(encoding='utf-8'))
        lineage=codec.portable_lineage(value['snapshot'],archive_id='second-export')
        self.assertEqual(lineage,value['expected_lineage'])
        index=codec.portable_index([value['snapshot']],archive_id='second-export')
        self.assertEqual(index,{'version':1,'lineages':[value['expected_lineage']]})
        self.assertEqual(codec.artifact_manifest(value['history'],index),value['expected_manifest'])
        self.assertNotIn(value['canary'],json.dumps(index))
        self.assertEqual([row['request_id'] for row in lineage['requests']],['0'*32,'1'*32,'6'*32])
        self.assertEqual(lineage['requests'][0]['import_source']['archive_id'],'first-failure')
        self.assertEqual(lineage['requests'][2]['producer']['requested_model'],'Model-Requested')
        self.assertEqual(lineage['versions'][1]['observation']['confirmed_model'],'Model-Observed')


if __name__=='__main__':unittest.main()
