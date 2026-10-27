"""Ticket23 root reds. Missing document_packets/route seams are infrastructure;
existing validator/brief rejections are behavioral. No provider/native calls.
"""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import document_inputs as inputs
import review_brief
from sealed_result_io import canonical_utf8
from tests.test_review_brief import design


def packet_fixture(files=None):
    files=files or [inputs.preview_document('same.py','\ufeffshared café\r\nonly first'.encode('utf-8')),
                    inputs.preview_document('same.py',b'shared\nonly second')]
    members=[{'file_id':'f'+str(i+1),**deepcopy(row)} for i,row in enumerate(files)]
    text=canonical_utf8({'version':2,'kind':'file_packet','files':members}).decode('utf-8')
    digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
    return {'version':2,'kind':'file_packet','encoding':'utf-8','source_id':'packet:'+digest,
            'byte_length':sum(row['byte_length'] for row in files),'content_sha256':digest,
            'files':[{key:value for key,value in row.items() if key!='text'} for row in members],'text':text}


class DocumentPacketTests(unittest.TestCase):
    def module(self):return importlib.import_module('document_packets')

    def test_exact_schema_preview_and_detachment(self):
        module=self.module()
        files=[inputs.preview_document('dup.txt',b'exact\r\n'),inputs.preview_document('dup.txt',b'exact\r\n')]
        packet=module.preview_packet(files)
        self.assertEqual(packet,packet_fixture(files))
        self.assertEqual([row['file_id'] for row in packet['files']],['f1','f2'])
        detached=module.validate_packet(packet)
        detached['files'][0]['name']='changed'
        self.assertEqual(packet['files'][0]['name'],'dup.txt')
        self.assertEqual(files[0]['name'],'dup.txt')

    def test_existing_snapshot_seam_accepts_v2_without_altering_v1(self):
        v1=inputs.preview_document('one.py',b'literal\r\n')
        self.assertEqual(inputs.validate_document_snapshot(v1),v1)
        packet=packet_fixture()
        self.assertEqual(inputs.validate_document_snapshot(packet),packet)

    def test_raw_aggregate_boundary_is_independent_of_json_escape_growth(self):
        module=self.module()
        files=[inputs.preview_document('a.txt',b'\\'*262144),inputs.preview_document('b.txt',b'"'*262144)]
        packet=module.preview_packet(files)
        self.assertEqual(packet['byte_length'],524288)
        self.assertGreater(len(packet['text'].encode('utf-8')),524288)
        self.assertEqual(module.validate_packet(packet),packet)
        frozen=review_brief.freeze_inputs(design(),source_file=packet)
        self.assertEqual(frozen['input_snapshot']['text'],packet['text'])
        encoded=json.dumps({'template_id':'custom-review','source_file':packet}).encode('utf-8')
        self.assertLessEqual(len(encoded),4*1024*1024)
        files[1]=inputs.preview_document('b.txt',b'"'*262145)
        with self.assertRaises(inputs.DocumentTooLarge):module.preview_packet(files)

    def test_non_ascii_raw_bytes_and_metadata_allowance(self):
        module=self.module()
        files=[inputs.preview_document('one.txt',('é'*262144).encode('utf-8'))]
        self.assertEqual(module.preview_packet(files)['byte_length'],524288)
        files=[inputs.preview_document('n'+str(i)+'x'*240,b'') for i in range(300)]
        with self.assertRaises(inputs.DocumentTooLarge):module.preview_packet(files)
        self.assertEqual(module.MAX_METADATA_BYTES,65536)
        sample=[inputs.preview_document('x.txt',b'x')]
        manifest=json.loads(packet_fixture(sample)['text'])
        for row in manifest['files']:row['text']=''
        overhead=len(canonical_utf8(manifest))
        with patch.object(module,'MAX_METADATA_BYTES',overhead):module.preview_packet(sample)
        with patch.object(module,'MAX_METADATA_BYTES',overhead-1),self.assertRaises(inputs.DocumentTooLarge):
            module.preview_packet(sample)

    def test_change_rename_and_reorder_each_change_revision(self):
        module=self.module()
        a=inputs.preview_document('a.txt',b'a\r\n');b=inputs.preview_document('b.txt',b'b')
        original=module.preview_packet([a,b])
        variants=([b,a],[inputs.preview_document('renamed.txt',b'a\r\n'),b],
                  [inputs.preview_document('a.txt',b'a\n'),b])
        for files in variants:
            self.assertNotEqual(module.preview_packet(files)['content_sha256'],original['content_sha256'])

    def test_packet_tamper_unknown_fields_and_noncanonical_text_refuse(self):
        module=self.module();good=packet_fixture();self.assertEqual(module.validate_packet(good),good)
        for key,value in [('version',True),('byte_length',0),('source_id','packet:'+'0'*64),
                          ('content_sha256','0'*64),('path','PRIVATE_PATH')]:
            bad=deepcopy(good);bad[key]=value
            with self.subTest(field=key),self.assertRaises(inputs.DocumentInputError):module.validate_packet(bad)
        bad=deepcopy(good);bad['files'][0]['file_id']='f2'
        with self.assertRaises(inputs.DocumentInputError):module.validate_packet(bad)
        bad=deepcopy(good);bad['text']=json.dumps(json.loads(good['text']),indent=2)
        bad['content_sha256']=hashlib.sha256(bad['text'].encode()).hexdigest();bad['source_id']='packet:'+bad['content_sha256']
        with self.assertRaises(inputs.DocumentInputError):module.validate_packet(bad)
        with self.assertRaises(inputs.DocumentInputError):module.preview_packet([])
        bad_file=inputs.preview_document('a',b'a');bad_file['text']='tampered'
        with self.assertRaises(inputs.DocumentInputError):module.preview_packet([bad_file])

    def test_file_bound_quote_membership_has_no_cross_file_fallback(self):
        module=self.module();packet=packet_fixture();revision=packet['content_sha256']
        def quote(file_id,text,rev=revision):
            return module.check_quote(packet,{'packet_revision':rev,'file_id':file_id,'quote':text})
        self.assertEqual(quote('f1','shared'),{'verified':True,'reason':None})
        self.assertEqual(quote('f2','shared'),{'verified':True,'reason':None})
        self.assertEqual(quote('f2','only first'),{'verified':False,'reason':'quote_not_found'})
        self.assertEqual(quote('f3','shared'),{'verified':False,'reason':'unknown_file'})
        self.assertEqual(quote('f1','shared','0'*64),{'verified':False,'reason':'packet_revision_mismatch'})
        self.assertEqual(quote('f1',''),{'verified':False,'reason':'invalid_citation'})
        self.assertEqual(module.check_quote(packet,{'packet_revision':revision,'file_id':'f1','quote':'shared','extra':1}),
                         {'verified':False,'reason':'invalid_citation'})

    def test_same_packet_reaches_cli_brief_api_message_and_persistent_store(self):
        packet=packet_fixture();frozen=review_brief.freeze_inputs(design(),source_file=packet)
        run={**frozen,'id':4,'channel':'review'}
        before=deepcopy(run)
        cli=review_brief.build_brief(run,0,0,'cli-seat','cli-id')
        api=review_brief.build_brief(run,1,0,'api-seat','api-id')
        metadata={key:value for key,value in packet.items() if key!='text'}
        self.assertEqual((cli['source'],cli['source_document']),(packet['text'],metadata))
        self.assertEqual(api['input_revision'],cli['input_revision'])
        messages=review_brief.brief_messages(api,[],'api-seat')
        source=json.loads(messages[1]['content'])
        self.assertEqual(source['text'],cli['source']);self.assertEqual(source['source_document'],metadata)
        with tempfile.TemporaryDirectory() as tmp:
            store=review_brief.BriefStore(tmp);store.put(cli)
            self.assertEqual(review_brief.BriefStore(tmp).get(cli['brief_id'],operator=True),cli)
        self.assertEqual(run,before)
        self.assertNotIn('source_document',messages[0]['content'])

    def test_session_reload_and_legacy_paste_stay_compatible(self):
        from session_store import SessionStore
        packet=packet_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store=SessionStore(str(Path(tmp)/'sessions.json'));store.save_custom_template(design())
            run=store.create('custom-review','review',{'reviewer':'cli','editor':'api'},'operator',source_file=packet)
            saved=SessionStore(str(store._path)).get(run['id'])
            self.assertEqual(saved['input_snapshot']['document'],{k:v for k,v in packet.items() if k!='text'})
            self.assertEqual(saved['input_revision'],packet['content_sha256'])
            old=store.create('custom-review','old',{'reviewer':'cli','editor':'api'},'operator',input_text='old\r\n')
            self.assertEqual(set(old['input_snapshot']),{'text','encoding','revision'})

    def test_accepted_session_source_keeps_valid_packet_metadata(self):
        from tests.test_artifact_admission import ArtifactAdmissionTests
        from tests.test_artifact_operator_core import accepted_source
        from artifact_sources import capture_artifact_session_source
        case=ArtifactAdmissionTests();case.setUp();case.setup_authority();self.addCleanup(case.doCleanups)
        packet=packet_fixture();create=case.sessions.create
        def file_create(*args,**kwargs):
            kwargs.pop('input_text',None)
            return create(*args,**kwargs,source_file=packet)
        with patch.object(case.sessions,'create',side_effect=file_create):run,_,_=accepted_source(case)
        _,source=capture_artifact_session_source(run['id'],run['run_id'],'review',sessions=case.sessions,messages=case.messages)
        self.assertEqual(source['input']['text'],packet['text'])
        self.assertEqual(source['input']['source_document'],{k:v for k,v in packet.items() if k!='text'})

    def test_existing_artifact_import_export_roundtrips_packet_bytes(self):
        from tests.test_artifact_imported_store import ArtifactImportedStoreTests
        case=ArtifactImportedStoreTests();case.setUp();self.addCleanup(case.doCleanups)
        source=case.packet();packet=packet_fixture()
        source['input']={'text':packet['text'],'input_revision':packet['content_sha256'],
                         'source_document':{k:v for k,v in packet.items() if k!='text'}}
        graph,audit,_=case.graph_for_packet(source)
        case.import_graph(graph)
        self.assertEqual(case.target.get_packet(audit['scope']['packet_id']),source)


if __name__=='__main__':unittest.main()
