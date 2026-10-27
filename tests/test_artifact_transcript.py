"""Ticket21 ROOT reds: basic transcript, no synthesis or new timing gate."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import patch

from tests import test_artifact_operator_core as core
accepted_source=core.accepted_source


class ArtifactTranscriptTests(unittest.TestCase):
    # Use the existing actual-store fixture without inheriting unrelated tests.
    def context(self):
        return core.ArtifactOperatorCoreTests.context(self)

    def export(self,case,session,**kwargs):
        module=importlib.import_module('artifact_transcript')
        return module.export_session_transcript(session,session['run_id'],'review',messages=case.messages,**kwargs)

    def test_exact_unicode_crlf_and_incomplete_header_without_html_execution(self):
        case=self.context();session,_,_=accepted_source(case,text='café 日本語\r\n<script>literal</script>',state='active')
        raw=self.export(case,session)
        self.assertIsInstance(raw,bytes)
        self.assertIn('café 日本語\r\n<script>literal</script>'.encode(),raw)
        self.assertIn(b'Incomplete',raw);self.assertIn(session['run_id'].encode(),raw)

    def test_admission_order_wins_over_message_id(self):
        case=self.context();session,row,event=accepted_source(case,text='FIRST')
        second=deepcopy(event);second['event_id']='a'*32;second['content']='SECOND'
        metadata=deepcopy(row['metadata']);metadata['event_id']=second['event_id']
        added=case.messages.add_once('session-event:'+second['event_id'],event['sender'],'SECOND',
            msg_type='session_result',channel='review',metadata=metadata)
        second['projected_message_id']=added['id']
        session['admitted_events']=[second,event]
        raw=self.export(case,session)
        self.assertLess(raw.index(b'SECOND'),raw.index(b'FIRST'))

    def test_missing_or_edited_projection_refuses_without_reconstructing_content(self):
        case=self.context();session,_,_=accepted_source(case,text='stored')
        module=importlib.import_module('artifact_transcript')
        for changed in ('content','projected_message_id'):
            bad=deepcopy(session);bad['admitted_events'][0][changed]='different' if changed=='content' else 999999
            with self.subTest(changed=changed),self.assertRaises(module.ArtifactTranscriptError) as caught:self.export(case,bad)
            self.assertEqual(caught.exception.code,'source_unavailable')

    def test_export_cap_is_utf8_bytes_and_never_returns_truncated_output(self):
        case=self.context();session,_,_=accepted_source(case,text='日本語'*50)
        module=importlib.import_module('artifact_transcript');raw=self.export(case,session)
        self.assertEqual(self.export(case,session,max_bytes=len(raw)),raw)
        with self.assertRaises(module.ArtifactTranscriptError) as caught:self.export(case,session,max_bytes=len(raw)-1)
        self.assertEqual(caught.exception.code,'transcript_too_large')

    def test_wrong_channel_run_and_duplicate_projection_are_refused(self):
        case=self.context();session,_,_=accepted_source(case)
        module=importlib.import_module('artifact_transcript')
        for run,channel in ((session['run_id'],'peer'),('f'*32,'review')):
            with self.subTest(run=run,channel=channel),self.assertRaises(module.ArtifactTranscriptError):
                module.export_session_transcript(session,run,channel,messages=case.messages)
        bad=deepcopy(session);bad['admitted_events']*=2
        with self.assertRaises(module.ArtifactTranscriptError):self.export(case,bad)

    def test_snapshot_read_once_and_detached_source_is_not_mutated(self):
        case=self.context();session,_,_=accepted_source(case);before=deepcopy(session)
        with patch.object(case.messages,'snapshot_selected',wraps=case.messages.snapshot_selected) as snapshot:
            self.export(case,session)
        snapshot.assert_called_once();self.assertEqual(session,before)

    def test_continuation_follows_its_question_and_skip_is_explicit(self):
        case=self.context();session,row,event=accepted_source(case,text='first')
        question=deepcopy(event);question.update(event_id='b'*32,kind='question',content='ASK')
        meta=deepcopy(row['metadata']);meta.update(event_id=question['event_id'],kind='question')
        saved=case.messages.add_once('session-event:'+question['event_id'],event['sender'],'ASK',
            msg_type='session_result',channel='review',metadata=meta)
        question['projected_message_id']=saved['id']
        answer=case.messages.add_once('session-input:'+question['event_id'],'operator','ANSWER',
            channel='review',metadata={'session_id':session['id'],'question_event_id':question['event_id']})
        session['admitted_events']=[question,event]
        session['continuation_context']=[{'question_event_id':question['event_id'],'answer':'ANSWER',
            'projected_message_id':answer['id']}]
        raw=self.export(case,session)
        self.assertLess(raw.index(b'ASK'),raw.index(b'ANSWER'));self.assertLess(raw.index(b'ANSWER'),raw.index(b'first'))
        session['skipped_turns']=[{'turn_id':session['run_id']+':0:1','reason':'participant_skipped','sender':'human'}]
        self.assertIn(b'Skipped',self.export(case,session))

    def test_attachment_paths_omitted_and_packet_size_limit_not_applied(self):
        case=self.context();session,row,_=accepted_source(case,text='large')
        original=case.messages.snapshot_selected
        def attached(*args):
            rows=original(*args);rows[0]['attachments']=[{'name':'PRIVATE-NAME','url':'file:///PRIVATE-PATH'}];return rows
        with patch.object(case.messages,'snapshot_selected',side_effect=attached):raw=self.export(case,session)
        self.assertIn(b'Attachment present; content not exported',raw)
        self.assertNotIn(b'PRIVATE',raw)
        # The transcript cap, not a packet builder cap, governs this export.
        with patch('artifact_sources.check_packet_bounds',side_effect=AssertionError('packet cap must not run')):
            self.assertTrue(self.export(case,session))

    def test_download_route_is_present_and_fixed_to_markdown(self):
        import artifact_routes
        router=artifact_routes.create_router(lambda:None)
        routes={(row.path,frozenset(row.methods)) for row in router.routes}
        self.assertIn(('/api/artifacts/sessions/{session_id}/transcript',frozenset({'GET','HEAD'})),routes)
