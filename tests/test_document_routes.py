"""Document HTTP and corrected-restart component checks, without native workers."""
import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
import app
from document_inputs import preview_document, MAX_DOCUMENT_BYTES
from review_brief import BriefError
from tests import test_operator_routes as operator_fixture
from tests import test_corrected_restart as restart_fixture


class DocumentRoutesTests(unittest.TestCase):
    def setUp(self):
        self.fixture = operator_fixture.OperatorRoutesTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.headers = {**self.fixture.headers, 'Content-Type': 'application/octet-stream'}

    def client(self):
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-routing-test', {'server': {'port': 18300}})
        api.add_api_route('/api/documents/preview', app.preview_document_input, methods=['POST'])
        api.add_api_route('/api/sessions/start', app.start_session, methods=['POST'])
        api.add_api_route('/api/sessions/active', app.get_active_session, methods=['GET'])
        client = TestClient(api, client=('127.0.0.1', 40000))
        self.addCleanup(client.close)
        return client

    def files(self):
        return {str(p): p.read_bytes() for p in self.fixture.f.root.rglob('*') if p.is_file()}

    def test_preview_preserves_bytes_and_has_no_storage_effects(self):
        client = self.client()
        before = self.files()
        raw = '\ufeffcafé\r\n@all\rplain'.encode('utf-8')
        response = client.post('/api/documents/preview?filename=c%2B%2B.md', content=raw, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), preview_document('c++.md', raw))
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.files(), before)

    def test_stream_early_length_refusal_does_not_read(self):
        async def receive():
            raise AssertionError('must not read refused request')
        for value, status in ((str(MAX_DOCUMENT_BYTES + 1), 413), ('-1', 400), ('x', 400)):
            request = Request({'type': 'http', 'method': 'POST', 'path': '/',
                'headers': [(b'content-length', value.encode())]}, receive)
            with self.subTest(value=value), self.assertRaises(Exception) as raised:
                asyncio.run(app._document_bytes(request))
            self.assertEqual(raised.exception.status_code, status)

    def test_query_and_media_and_auth_fail_before_effects(self):
        client = self.client()
        before = self.files()
        for query in ('', '?filename=x&filename=y', '?filename=x&other=y', '?filename=%',
                      '?filename=%FF', '?filename=c++.md', '?filename=%00', '?filename='):
            self.assertEqual(client.post('/api/documents/preview'+query, content=b'x', headers=self.headers).status_code, 400)
        self.assertEqual(client.post('/api/documents/preview?filename=x', content=b'x',
            headers={**self.headers, 'Content-Type': 'text/plain'}).status_code, 415)
        for headers in ({}, {'Authorization': 'Bearer '+self.fixture.f.owner['token']}):
            self.assertEqual(client.post('/api/documents/preview?filename=x', content=b'x', headers=headers).status_code, 403)
        self.assertEqual(client.post('/api/documents/preview?filename='+('a'*4097), content=b'x', headers=self.headers).status_code, 400)
        self.assertEqual(self.files(), before)

    def test_stream_bounds_stop_at_first_overflow_and_accept_empty(self):
        for chunks, expected in (([b''], b''), ([b'a' * MAX_DOCUMENT_BYTES], b'a' * MAX_DOCUMENT_BYTES),
                                  ([b'a' * MAX_DOCUMENT_BYTES, b'b', b'never'], None),
                                  ([b'a' * (MAX_DOCUMENT_BYTES + 100), b'never'], None)):
            seen = []
            async def receive():
                i = len(seen)
                seen.append(i)
                return {'type': 'http.request', 'body': chunks[i], 'more_body': i+1 < len(chunks)}
            req = Request({'type': 'http', 'method': 'POST', 'path': '/', 'headers': []}, receive)
            if expected is None:
                with self.assertRaises(Exception) as raised:
                    asyncio.run(app._document_bytes(req))
                self.assertEqual(raised.exception.status_code, 413)
                self.assertLess(len(seen), len(chunks))
            else:
                self.assertEqual(asyncio.run(app._document_bytes(req)), expected)

    def test_preview_binary_invalid_utf8_and_size_rejected(self):
        client = self.client()
        for raw, status in ((b'\x00',400),(b'\xff',400),(b'a'*MAX_DOCUMENT_BYTES,200),
                            (b'a'*(MAX_DOCUMENT_BYTES+1),413)):
            response = client.post('/api/documents/preview?filename=source.py', content=raw, headers=self.headers)
            self.assertEqual(response.status_code, status)

    def test_start_presence_and_invalid_file_refuse_before_template_or_engine(self):
        client = self.client()
        document = preview_document('x.py', b'exact\r\ntext')
        before = self.files()
        with patch.object(app.session_engine, 'start_session', side_effect=AssertionError('no start')):
            for body in ({'source_file':document, 'input_text':''}, {'source_file':None},
                         {'source_file':{**document, 'content_sha256':'0'*64}}):
                self.assertEqual(client.post('/api/sessions/start', json=body,
                    headers=self.fixture.headers).status_code, 400)
        self.assertEqual(client.post('/api/sessions/start', content=b' '*(4*1024*1024+1), headers=self.fixture.headers).status_code, 413)
        self.assertEqual(client.post('/api/sessions/start', json={'source_file':document},
            headers={'Authorization':'Bearer '+self.fixture.f.owner['token']}).status_code, 403)
        self.assertEqual(self.files(), before)

    def test_start_file_and_pasted_both_use_existing_route(self):
        client = self.client()
        document = preview_document('source.mjs', b'exact\r\n@all')
        for channel, source in (('file-room', {'source_file':document}), ('paste-room', {'input_text':'paste'})):
            response = client.post('/api/sessions/start', json={'template_id':'review',
                'channel':channel,'cast':{'reviewer':'alice','editor':'bob'}, **source}, headers=self.fixture.headers)
            self.assertEqual(response.status_code, 200, response.text)
            snap = response.json()['input_snapshot']
            self.assertEqual(snap['text'], document['text'] if 'source_file' in source else 'paste')
            self.assertEqual('document' in snap, 'source_file' in source)
            app.session_engine.stop_session(response.json()['id'])
            stopped = client.get('/api/sessions/active?channel='+channel, headers=self.fixture.headers)
            self.assertEqual(stopped.status_code, 200)
            self.assertEqual(stopped.json()['input_snapshot'], snap)
            self.assertIn(stopped.json()['state'], ('stopping', 'stopped'))


    def test_draft_start_threads_file_snapshot_through_same_route(self):
        client = self.client()
        document = preview_document('draft.py', b'exact draft\r\nsource')
        template = deepcopy(self.fixture.f.template)
        template['id'] = 'file-draft'
        message = self.fixture.f.messages.add('operator', 'draft', metadata={'template':template})
        if message['id'] == 0:
            message = self.fixture.f.messages.add('operator', 'draft', metadata={'template':template})
        response = client.post('/api/sessions/start', json={'draft_message_id':message['id'],
            'channel':'draft-room', 'cast':{'reviewer':'alice','editor':'bob'}, 'source_file':document},
            headers=self.fixture.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['input_snapshot']['document']['source_id'], document['source_id'])
        self.assertEqual(response.json()['input_snapshot']['text'], document['text'])

    def test_crlf_heavy_maximum_file_start_json_remains_under_request_cap(self):
        client = self.client()
        document = preview_document('source.txt', b'\r\n'*(MAX_DOCUMENT_BYTES//2))
        body = {'template_id':'review', 'channel':'large-room', 'cast':{'reviewer':'alice','editor':'bob'}, 'source_file':document}
        wire = json.dumps(body).encode('utf-8')
        self.assertLess(len(wire), 4*1024*1024)
        response = client.post('/api/sessions/start', content=wire, headers=self.fixture.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['input_snapshot']['text'], document['text'])


class DocumentRestartTests(unittest.TestCase):
    def setUp(self):
        self.fixture = restart_fixture.CorrectedRestartTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.store = self.fixture.sessions
        self.parent_id = self.fixture.parent_id
        parent = self.store.get(self.parent_id)
        self.document = preview_document('original.py', parent['input_snapshot']['text'].encode('utf-8'))
        metadata = {k:v for k,v in self.document.items() if k != 'text'}
        self.store._event_update(self.parent_id, lambda run: run['input_snapshot'].update(document=metadata))

    def test_line_ending_only_restart_rejected_without_any_effect(self):
        before = self.store._path.read_bytes()
        callbacks = []
        self.store.on_change(lambda *args: callbacks.append(args))
        for text in (self.document['text'].replace('\r\n','\n'),
                     self.document['text'].replace('\r\n','\r')):
            with self.subTest(text=text), patch.object(self.fixture.engine, 'prepare_contexts') as contexts, \
                    patch('subprocess.Popen') as spawn:
                with self.assertRaises(BriefError):
                    self.fixture.engine.correct_and_restart(self.parent_id, text, 'same-source')
                contexts.assert_not_called()
                spawn.assert_not_called()
            self.assertEqual(self.store._path.read_bytes(), before)
        self.assertEqual(callbacks, [])

    def test_corrupt_parent_metadata_fails_closed_even_with_actual_edit(self):
        self.store._event_update(self.parent_id, lambda run: run['input_snapshot'].update(document=None))
        before = self.store._path.read_bytes()
        with self.assertRaises(BriefError):
            self.store.prepare_restart(self.parent_id, 'genuine edit', 'bad-parent')
        self.assertEqual(self.store._path.read_bytes(), before)

    def test_edited_child_is_exact_paste_and_parent_bytes_unchanged(self):
        parent = self.store.get(self.parent_id)
        text = 'actual edit\r\nwith bare\rline'
        child = self.store.prepare_restart(self.parent_id, text, 'edited')
        self.assertEqual(child['input_snapshot']['text'], text)
        self.assertNotIn('document', child['input_snapshot'])
        self.assertEqual(self.store.get(self.parent_id)['input_snapshot'], parent['input_snapshot'])
