"""Ticket23 HTTP reds use the existing operator/seat middleware fixture."""
from copy import deepcopy
from unittest.mock import patch
import unittest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import app
from tests import test_document_routes as route_fixture
from tests.test_document_packets import packet_fixture


class DocumentPacketRouteTests(unittest.TestCase):
    def setUp(self):
        self.case=route_fixture.DocumentRoutesTests();self.case.setUp();self.addCleanup(self.case.doCleanups)

    def client(self):
        api=FastAPI()
        with patch.object(app,'app',api):app._install_security_middleware('operator-routing-test',{'server':{'port':18300}})
        api.add_api_route('/api/documents/packet-preview',app.preview_document_packet,methods=['POST'])
        client=TestClient(api,client=('127.0.0.1',40000));self.addCleanup(client.close);return client

    def files(self):
        import json
        return [{k:v for k,v in row.items() if k!='file_id'} for row in json.loads(packet_fixture()['text'])['files']]

    def test_route_is_wired_post_only(self):
        methods=[set(route.methods) for route in app.app.routes if getattr(route,'path',None)=='/api/documents/packet-preview']
        self.assertEqual(methods,[{'POST'}])

    def test_preview_operator_exact_snapshot_and_no_storage(self):
        client=self.client();before=self.case.files()
        response=client.post('/api/documents/packet-preview',json={'files':self.files()},headers=self.case.fixture.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),packet_fixture())
        self.assertEqual(self.case.files(),before)

    def test_preview_auth_body_query_and_byte_refusals(self):
        client=self.client();before=self.case.files();headers=self.case.fixture.headers
        for auth in ({},{'Authorization':'Bearer '+self.case.fixture.f.owner['token']}):
            self.assertEqual(client.post('/api/documents/packet-preview',json={'files':self.files()},headers=auth).status_code,403)
        for body in ({},{'files':[]},{'files':self.files(),'unknown':1}):
            self.assertEqual(client.post('/api/documents/packet-preview',json=body,headers=headers).status_code,400)
        self.assertEqual(client.post('/api/documents/packet-preview?extra=1',json={'files':self.files()},headers=headers).status_code,400)
        self.assertEqual(client.post('/api/documents/packet-preview',content=b' '*(4*1024*1024+1),headers=headers).status_code,413)
        from document_inputs import preview_document
        files=[preview_document('a',b'a'*262144),preview_document('b',b'b'*262145)]
        self.assertEqual(client.post('/api/documents/packet-preview',json={'files':files},headers=headers).status_code,413)
        self.assertEqual(self.case.files(),before)

    def test_session_start_real_serializer_worst_case_and_operator_only(self):
        from document_inputs import preview_document
        client=self.case.client()
        files=[preview_document('a',b'\\'*262144),preview_document('b',b'"'*262144)]
        packet=packet_fixture(files)
        with patch.object(app,'_start_session_sync',return_value=JSONResponse({'ok':True})) as start:
            response=client.post('/api/sessions/start',json={'source_file':packet},headers=self.case.fixture.headers)
            self.assertEqual(response.status_code,200)
            self.assertLessEqual(len(response.request.content),4*1024*1024)
            self.assertEqual(start.call_args.args[1],packet)
        for headers in ({},{'Authorization':'Bearer '+self.case.fixture.f.owner['token']}):
            with patch.object(app,'_start_session_sync',side_effect=AssertionError('Seat must not start packet review')):
                self.assertEqual(client.post('/api/sessions/start',json={'source_file':packet},headers=headers).status_code,403)
        self.assertEqual(client.post('/api/sessions/start',content=b' '*(4*1024*1024+1),headers=self.case.fixture.headers).status_code,413)

    def test_existing_session_start_threads_validated_packet_before_engine(self):
        client=self.case.client();packet=packet_fixture()
        with patch.object(app,'_start_session_sync',return_value=JSONResponse({'ok':True})) as start:
            response=client.post('/api/sessions/start',json={'source_file':packet},headers=self.case.fixture.headers)
            self.assertEqual(response.status_code,200)
            self.assertEqual(start.call_args.args[1],packet)
        corrupt=deepcopy(packet);corrupt['byte_length']=0
        with patch.object(app,'_start_session_sync',side_effect=AssertionError('Invalid packet reached engine')):
            self.assertEqual(client.post('/api/sessions/start',json={'source_file':corrupt},headers=self.case.fixture.headers).status_code,400)


if __name__=='__main__':unittest.main()
