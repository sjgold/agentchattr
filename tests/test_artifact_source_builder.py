"""Reduced20 ROOT source/snapshot reds; missing helper seams are infrastructure.
No model calls, fixtures use the actual MessageStore and accepted packet grammar.
"""
from copy import deepcopy
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from store import MessageStore
import artifact_store


class ArtifactSourceBuilderTests(unittest.TestCase):
    def context(self):
        tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'.audit-tmp')
        self.addCleanup(tmp.cleanup)
        return MessageStore(str(Path(tmp.name)/'messages.jsonl'))

    def test_snapshot_selected_is_detached_and_channel_exact(self):
        messages=self.context();first=messages.add('operator','exact café\r\n',channel='review')
        foreign=messages.add('operator','foreign',channel='peer')
        saved=messages.snapshot_selected('review',[first['id']])
        self.assertEqual([row['id'] for row in saved],[first['id']])
        saved[0]['text']='changed'
        self.assertEqual(messages.get_snapshot(first['id'])['text'],'exact café\r\n')
        with self.assertRaises(ValueError):messages.snapshot_selected('review',[foreign['id']])

    def test_snapshot_selected_locks_once_without_recursive_lock_calls(self):
        messages=self.context();row=messages.add('operator','one',channel='review');original=messages._lock
        entered=[]
        class Counted:
            def __enter__(self):
                if not original.acquire(blocking=False):raise AssertionError('recursive message-lock acquisition')
                entered.append(True);return self
            def __exit__(self,*args):original.release()
        messages._lock=Counted()
        result=messages.snapshot_selected('review',[row['id']])
        self.assertEqual(len(result),1);self.assertEqual(len(entered),1)

    def test_snapshot_missing_and_duplicate_ids_never_return_partial(self):
        messages=self.context();row=messages.add('operator','one',channel='review')
        for ids in ([row['id'],999999],[row['id'],row['id']]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):messages.snapshot_selected('review',ids)

    def test_typed_packet_precheck_runs_before_full_content_walk(self):
        module=importlib.import_module('artifact_sources')
        packet={'version':1,'channel':'review','scope_kind':'selected_channel_messages',
            'source_run':None,'input':None,'messages':[]}
        with patch.object(artifact_store,'_packet_scope',side_effect=AssertionError('full walk must not run')):
            for body in ('x'*(2*1024*1024+1),):
                packet['messages']=[{'id':0,'uid':'zero','sender':'operator','type':'chat',
                    'timestamp':None,'text':body,'attachments':[],'provenance':{}}]
                with self.assertRaises(module.ArtifactSourceError) as caught:module.check_packet_bounds(packet)
                self.assertEqual(caught.exception.code,'source_too_large')

    def test_projection_allowlist_preserves_literal_text_not_server_metadata(self):
        module=importlib.import_module('artifact_sources')
        row={'id':7,'uid':'message-7','sender':'operator','type':'chat','timestamp':None,
            'text':'literal token/path/fingerprint café\r\n','channel':'review',
            'attachments':[{'name':'x','url':'/uploads/x','path':'PRIVATE_PATH','token':'PRIVATE_TOKEN'}],
            'metadata':{'session_id':1,'run_id':'a'*32,'token':'PRIVATE_TOKEN',
                'launch_nonce':'PRIVATE_NONCE','config':{'secret':'PRIVATE_CONFIG'}}}
        message=module.project_artifact_message(row)
        self.assertEqual(set(message),{'id','uid','sender','type','timestamp','text','attachments','provenance'})
        self.assertEqual(message['text'],row['text']);self.assertEqual(message['attachments'],[{'name':'x','url':'/uploads/x'}])
        self.assertEqual(message['provenance'],{'session_id':1,'run_id':'a'*32})
        self.assertNotIn('PRIVATE_',str(message))

    def test_legacy_uid_collision_is_refused_not_renamed(self):
        module=importlib.import_module('artifact_sources')
        base={'sender':'operator','type':'chat','timestamp':None,'text':'one','channel':'review','metadata':{}}
        one=module.project_artifact_message(dict(base,id=7))
        self.assertEqual(one['uid'],'legacy:7')
        two=module.project_artifact_message(dict(base,id=8,uid='legacy:7'))
        packet={'version':1,'channel':'review','scope_kind':'selected_channel_messages',
            'source_run':None,'input':None,'messages':[one,two]}
        with self.assertRaises(artifact_store.ArtifactValidationError):artifact_store._packet_scope('a'*32,packet)
