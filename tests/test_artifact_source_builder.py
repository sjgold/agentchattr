"""Reduced20 ROOT source/snapshot reds; missing helper seams are infrastructure.
No model calls, fixtures use the actual MessageStore and accepted packet grammar.
"""
from copy import deepcopy
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from store import MessageStore, MessageSnapshotUnavailable
import artifact_store


class ArtifactSourceBuilderTests(unittest.TestCase):
    def context(self):
        scratch=Path(__file__).resolve().parents[1]/'.audit-tmp';scratch.mkdir(exist_ok=True)
        tmp=tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(tmp.cleanup)
        return MessageStore(str(Path(tmp.name)/'messages.jsonl'))

    def test_snapshot_selected_is_detached_and_channel_exact(self):
        messages=self.context();first=messages.add('operator','exact café\r\n',channel='review',metadata={'nested':{'values':[1]}})
        foreign=messages.add('operator','foreign',channel='peer')
        saved=messages.snapshot_selected('review',[first['id']])
        self.assertEqual([row['id'] for row in saved],[first['id']])
        saved[0]['text']='changed'
        saved[0]['metadata']['nested']['values'].append(2)
        self.assertEqual(messages.get_snapshot(first['id'])['metadata']['nested']['values'],[1])
        self.assertEqual(messages.get_snapshot(first['id'])['text'],'exact café\r\n')
        with self.assertRaises(MessageSnapshotUnavailable):messages.snapshot_selected('review',[foreign['id']])

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
            with self.subTest(ids=ids),self.assertRaises(MessageSnapshotUnavailable):messages.snapshot_selected('review',ids)

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

    def source_fixture(self):
        from tests import test_artifact_admission as fixture
        from tests.test_artifact_operator_core import accepted_source
        case=fixture.ArtifactAdmissionTests();case.setUp();case.setup_authority();self.addCleanup(case.doCleanups)
        session,row,event=accepted_source(case)
        return case,session,row,event

    def test_capture_single_read_identity_attribution_and_deep_detachment(self):
        module=importlib.import_module('artifact_sources');case,session,row,event=self.source_fixture()
        with patch.object(case.messages,'snapshot_selected',wraps=case.messages.snapshot_selected) as snapshot,patch.object(
                case.messages,'get_snapshot',side_effect=AssertionError('must not reread')),patch.object(
                artifact_store,'_packet_scope',wraps=artifact_store._packet_scope) as walk:
            captured,packet=module.capture_artifact_session_source(session['id'],session['run_id'],'review',sessions=case.sessions,messages=case.messages)
        snapshot.assert_called_once();walk.assert_called_once()
        self.assertEqual(packet['messages'][0]['text'],event['content'])
        packet['messages'][0]['provenance']['event_id']='CHANGED';captured['admitted_events'][0]['content']='changed'
        self.assertEqual(case.messages.get_snapshot(row['id'])['metadata']['event_id'],event['event_id'])
        self.assertEqual(case.sessions.get(session['id'])['admitted_events'][0]['content'],event['content'])
        for field,value in [('uid','wrong'),('sender','wrong'),('text','edited')]:
            with case.messages._lock:case.messages._messages[0][field]=value
            with self.subTest(field=field),self.assertRaises(module.ArtifactSourceError) as caught:
                module.capture_artifact_session_source(session['id'],session['run_id'],'review',sessions=case.sessions,messages=case.messages)
            self.assertEqual(caught.exception.code,'source_unavailable')
            with case.messages._lock:case.messages._messages[0]=deepcopy(row)

    def test_footer_uses_message_marker_not_current_session_state(self):
        module=importlib.import_module('artifact_sources');case,session,row,event=self.source_fixture()
        with patch('participant_skip.footer',return_value='\nFOOTER') as footer:
            module.capture_artifact_session_source(session['id'],session['run_id'],'review',sessions=case.sessions,messages=case.messages)
            footer.assert_not_called()
            with case.messages._lock:
                case.messages._messages[0]['metadata']['session_output']=True
                case.messages._messages[0]['text']=event['content']+'\nFOOTER'
            case.sessions._event_update(session['id'],lambda value:value.update(state='active'))
            _,packet=module.capture_artifact_session_source(session['id'],session['run_id'],'review',sessions=case.sessions,messages=case.messages)
            footer.assert_called_once();self.assertEqual(packet['messages'][0]['text'],event['content']+'\nFOOTER')

    def test_missing_duplicate_links_and_negative_phase_are_typed_refusals(self):
        module=importlib.import_module('artifact_sources');case,session,row,event=self.source_fixture()
        for variant in ('missing','duplicate','negative'):
            altered=deepcopy(event)
            if variant=='missing':altered['projected_message_id']=None
            if variant=='negative':altered['turn_id']=session['run_id']+':-1:0'
            case.sessions._event_update(session['id'],lambda value:value.update(admitted_events=[altered,deepcopy(altered)] if variant=='duplicate' else [altered]))
            if variant=='negative':
                with case.messages._lock:case.messages._messages[0]['metadata']['turn_id']=altered['turn_id']
            with self.subTest(variant=variant),self.assertRaises(module.ArtifactSourceError) as caught:
                module.capture_artifact_session_source(session['id'],session['run_id'],'review',sessions=case.sessions,messages=case.messages)
            self.assertEqual(caught.exception.code,'source_unavailable')

    def test_cap_precheck_exact_bytes_unicode_escaping_and_count(self):
        module=importlib.import_module('artifact_sources')
        from sealed_result_io import canonical_utf8
        message={'id':0,'uid':'zero','sender':'operator','type':'chat','timestamp':None,'text':'','attachments':[],'provenance':{}}
        packet={'version':1,'channel':'review','scope_kind':'selected_channel_messages','source_run':None,'input':None,'messages':[message]}
        room=artifact_store.MAX_PACKET_BYTES-len(canonical_utf8(packet));message['text']='x'*room
        self.assertEqual(module.check_packet_bounds(packet),artifact_store.MAX_PACKET_BYTES)
        for text in ('x'*(room+1),'é'*room,'"'*room):
            message['text']=text
            with self.subTest(kind=text[:1]),self.assertRaises(module.ArtifactSourceError) as caught:module.check_packet_bounds(packet)
            self.assertEqual(caught.exception.code,'source_too_large')
        packet['messages']=[{}]*1001
        with self.assertRaises(module.ArtifactSourceError) as caught:module.check_packet_bounds(packet)
        self.assertEqual(caught.exception.code,'source_too_large')
        with self.assertRaises(module.ArtifactSourceError) as caught:module.check_packet_bounds({'messages':'wrong'})
        self.assertEqual(caught.exception.code,'source_unavailable')
