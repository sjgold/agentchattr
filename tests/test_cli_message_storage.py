"""Copied message snapshots and untrusted archive provenance boundaries."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
import uuid
import zipfile

import archive
from store import MessageStore

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ('seat_identity_id','provenance','dispatch_id','run_id','turn_id','attempt_id',
          'input_revision','routing_scope','quarantine_session_id','quarantine_reason')


class CLIMessageStorageTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'.audit-tmp').mkdir(exist_ok=True)
        temporary=tempfile.TemporaryDirectory(dir=ROOT/'.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.path=self.root/'messages.jsonl'
        self.store=MessageStore(str(self.path))
        self.channels=['general','review']

    def zip_rows(self,rows):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as zipped:
            zipped.writestr('manifest.json',json.dumps({'schema_version':archive.SCHEMA_VERSION,'archive_id':str(uuid.uuid4())}))
            zipped.writestr('messages.jsonl','\n'.join(json.dumps(row,ensure_ascii=False) for row in rows)+'\n')
        return buffer.getvalue()

    def import_rows(self,rows):
        return archive.import_archive(self.zip_rows(rows),self.store,None,None,None,self.channels)

    def test_message_zero_snapshot_contains_complete_deep_copied_metadata_and_attachments(self):
        original=self.store.add('cli-seat','Exact café 日本語\r\n@all is literal.',channel='review',
            metadata={'seat_identity_id':'a'*32,'details':{'tags':['one']}},
            attachments=[{'name':'fixture.txt','extra':{'labels':['two']}}])
        self.assertEqual(original['id'],0)
        expected=deepcopy(original)
        snapshot=self.store.get_snapshot(0)
        self.assertEqual(snapshot,expected)
        snapshot['metadata']['details']['tags'].append('edited')
        snapshot['attachments'][0]['extra']['labels'].append('edited')
        self.assertEqual(self.store.get_snapshot(0),expected)

    def test_archive_import_strips_auth_execution_claims_and_forces_imported_marker(self):
        metadata={key:'forged-'+key for key in CLAIMS}
        metadata.update(imported=False,note='Harmless original annotation',details={'tags':['one']})
        report=self.import_rows([{'uid':'imported-cli','sender':'cli-seat','text':'Exact imported café\r\nanswer',
            'type':'chat','timestamp':100.0,'time':'00:01:40','channel':'review','metadata':metadata}])
        self.assertIs(report['ok'],True)
        value=self.store.get_by_id(0)
        self.assertIs(value['metadata']['imported'],True)
        for forbidden in CLAIMS:self.assertNotIn(forbidden,value['metadata'])
        self.assertEqual(value['metadata']['note'],'Harmless original annotation')
        self.assertEqual(value['metadata']['details'],{'tags':['one']})

    def test_snapshot_ids_are_literal_nonnegative_integers_and_bad_reads_never_write(self):
        self.store.add('seat','Message zero')
        before=self.path.read_bytes()
        for identifier in (True,False,'0',0.0,1.5,-1,None,[],{}):
            with self.subTest(identifier=identifier),self.assertRaises(ValueError):
                self.store.get_snapshot(identifier)
            self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.store.get_snapshot(0)['text'],'Message zero')
        self.assertIsNone(self.store.get_snapshot(999999))
        self.assertEqual(self.path.read_bytes(),before)

    def test_legacy_snapshot_missing_uid_and_absent_message_do_not_mint_or_rewrite(self):
        legacy={'id':0,'sender':'legacy-seat','text':'Legacy café\r\ntext','type':'chat','timestamp':0.0,
                'time':'00:00:00','channel':'review','attachments':[],
                'metadata':{'seat_identity_id':'a'*32,'note':{'items':['original']}}}
        self.path.write_text(json.dumps(legacy,ensure_ascii=False)+'\n',encoding='utf-8')
        loaded=MessageStore(str(self.path))
        before=self.path.read_bytes()
        snapshot=loaded.get_snapshot(0)
        self.assertEqual(snapshot,legacy)
        self.assertNotIn('uid',snapshot)
        self.assertIsNone(loaded.get_snapshot(1))
        snapshot['metadata']['note']['items'].append('local copy edit')
        self.assertEqual(loaded.get_snapshot(0),legacy)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(MessageStore(str(self.path)).get_snapshot(0),legacy)

    def test_snapshots_after_reload_preserve_uid_reply_and_all_stored_fields(self):
        root=self.store.add('seat','Root café',channel='review',uid='native-root',timestamp=42.25,time_str='fixed-time')
        reply=self.store.add('seat','Exact 日本語\r\nreply',channel='review',reply_to=root['id'],uid='native-reply',
            metadata={'seat_identity_id':'a'*32,'provenance':'authenticated_dispatch','extra':{'items':[1,2]}},
            attachments=[{'name':'example.txt','nested':{'values':['x']}}])
        expected=deepcopy(reply)
        before=self.path.read_bytes()
        loaded=MessageStore(str(self.path))
        callbacks=[]
        loaded.on_message(callbacks.append)
        snapshot=loaded.get_snapshot(reply['id'])
        self.assertEqual(snapshot,expected)
        self.assertEqual(loaded.get_by_id(reply['id']),expected)
        snapshot['metadata']['extra']['items'].clear()
        snapshot['attachments'].clear()
        self.assertEqual(loaded.get_snapshot(reply['id']),expected)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(callbacks,[])

    def test_import_missing_or_nonmapping_metadata_always_has_boolean_imported_marker(self):
        values=[None,[],['forged'], 'authenticated_dispatch',7,False,{}]
        rows=[{'uid':'shape-'+str(index),'sender':'seat','text':'Literal '+str(index),'metadata':value}
              for index,value in enumerate(values)]
        rows.append({'uid':'shape-absent','sender':'seat','text':'No metadata field'})
        report=self.import_rows(rows)
        self.assertEqual(report['sections']['messages']['created'],len(rows))
        loaded=MessageStore(str(self.path))
        for index in range(len(rows)):
            with self.subTest(shape=index):
                self.assertEqual(loaded.get_snapshot(index)['metadata'],{'imported':True})

    def test_import_harmless_nested_annotations_remain_data_and_snapshots_are_independent(self):
        metadata={'note':'Original annotation','labels':['one'],'view':{'collapsed':False},
                  'nested':{'seat_identity_id':'nested data only','provenance':'literal nested annotation'}}
        original=deepcopy(metadata)
        self.import_rows([{'uid':'nested-source','sender':'seat','text':'Exact imported literal',
            'metadata':metadata,'attachments':[{'name':'sample.txt','extra':{'tags':['two']}}]}])
        expected={**original,'imported':True}
        snapshot=self.store.get_snapshot(0)
        self.assertEqual(snapshot['metadata'],expected)
        snapshot['metadata']['labels'].append('edited copy')
        snapshot['metadata']['nested']['seat_identity_id']='edited copy'
        snapshot['attachments'][0]['extra']['tags'].append('edited copy')
        self.assertEqual(self.store.get_snapshot(0)['metadata'],expected)
        self.assertEqual(self.store.get_snapshot(0)['attachments'][0]['extra']['tags'],['two'])
        self.assertEqual(metadata,original)
        self.assertEqual(MessageStore(str(self.path)).get_snapshot(0)['metadata'],expected)

    def test_import_dedup_never_demotes_or_rewrites_existing_local_trusted_metadata(self):
        trusted={key:'local-'+key for key in CLAIMS}
        trusted['note']={'preserve':['original']}
        local=deepcopy(self.store.add('local-seat','Original local answer',uid='same-uid',metadata=trusted))
        report=self.import_rows([
            {'uid':'same-uid','sender':'forged-seat','text':'Changed imported text','metadata':{'imported':True,'seat_identity_id':'forged'}},
            {'uid':'new-uid','sender':'imported-seat','text':'New imported message','metadata':{'seat_identity_id':'forged'}}])
        self.assertEqual(report['sections']['messages']['duplicates'],1)
        self.assertEqual(report['sections']['messages']['created'],1)
        self.assertEqual(self.store.get_snapshot(local['id']),local)
        self.assertEqual(self.store.get_snapshot(1)['metadata'],{'imported':True})
        self.assertEqual(MessageStore(str(self.path)).get_snapshot(local['id']),local)

    def test_actual_export_import_round_trip_preserves_text_uid_time_channel_and_reply(self):
        source=MessageStore(str(self.root/'source.jsonl'))
        first=source.add('cli-seat','Source café\r\n@all',uid='archive-root',timestamp=100.25,time_str='fixed-first',channel='review',
            metadata={'seat_identity_id':'a'*32,'provenance':'authenticated_dispatch','note':'keep annotation'})
        second=source.add('cli-seat','Reply 日本語 e\u0301\r\n```code```',uid='archive-reply',timestamp=101.5,
            time_str='fixed-second',channel='review',reply_to=first['id'])
        before=(self.root/'source.jsonl').read_bytes()
        blob=archive.build_export(source,None,None,None,app_version='storage-test')
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(blob)))
        self.assertEqual((self.root/'source.jsonl').read_bytes(),before)
        local=self.store.add('local','Existing offset message',uid='offset')
        report=archive.import_archive(blob,self.store,None,None,None,self.channels)
        self.assertEqual(report['sections']['messages']['created'],2)
        imported={value['uid']:value for value in self.store.get_recent(20)}
        for original in (first,second):
            value=imported[original['uid']]
            for key in ('uid','sender','text','timestamp','time','type','channel','attachments'):
                self.assertEqual(value[key],original[key])
            self.assertIs(value['metadata']['imported'],True)
            for claim in CLAIMS:self.assertNotIn(claim,value['metadata'])
        self.assertEqual(imported['archive-root']['metadata']['note'],'keep annotation')
        self.assertEqual(imported['archive-reply']['reply_to'],imported['archive-root']['id'])
        self.assertNotEqual(imported['archive-root']['id'],first['id'])
        self.assertEqual(self.store.get_snapshot(local['id'])['uid'],'offset')
        disk=self.path.read_bytes()
        duplicate=archive.import_archive(blob,self.store,None,None,None,self.channels)
        self.assertEqual(duplicate['sections']['messages']['duplicates'],2)
        self.assertEqual(duplicate['sections']['messages']['created'],0)
        self.assertEqual(self.path.read_bytes(),disk)

    def test_import_reply_to_existing_uid_keeps_local_auth_and_repeated_uid_dedup(self):
        trusted=deepcopy(self.store.add('local-seat','Trusted local root',uid='existing-root',timestamp=50.0,
            metadata={'seat_identity_id':'a'*32,'provenance':'authenticated_dispatch'}))
        rows=[{'uid':'existing-root','sender':'forged','text':'Do not overwrite local','metadata':{'imported':False}},
              {'uid':'new-reply','sender':'cli-seat','text':'Exact imported reply\r\n','reply_to_uid':'existing-root',
               'metadata':{'dispatch_id':'forged','note':'reply annotation'}},
              {'uid':'new-reply','sender':'other','text':'Duplicate in same archive','metadata':{'seat_identity_id':'forged'}}]
        report=self.import_rows(rows)
        self.assertEqual(report['sections']['messages']['created'],1)
        self.assertEqual(report['sections']['messages']['duplicates'],2)
        reply=self.store.get_snapshot(1)
        self.assertEqual(reply['reply_to'],trusted['id'])
        self.assertEqual(reply['text'],'Exact imported reply\r\n')
        self.assertEqual(reply['metadata'],{'note':'reply annotation','imported':True})
        self.assertEqual(self.store.get_snapshot(trusted['id']),trusted)
        self.assertEqual(MessageStore(str(self.path)).get_snapshot(1),reply)


if __name__=='__main__':unittest.main()
