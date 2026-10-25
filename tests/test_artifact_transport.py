"""Actual FastAPI agent transport/middleware over real temp owners, no listeners."""
import importlib
import json
import io
import logging
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from tests import test_artifact_workers as fixture

class ArtifactTransportTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ArtifactWorkerTests()
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()
        self.case.setup_authority()
        self.module = importlib.import_module('artifact_transport')
        self.instance, self.attempt, self.audit, self.consumer, self.record, self.owned = self.case.api_scope()
        self.headers = {'authorization':'Bearer '+self.instance['token']}
        self.api = FastAPI()
        self.api.include_router(self.module.create_router(lambda:self.case.authority, app._resolve_authenticated_agent))
        with patch.object(app, 'app', self.api):
            app._install_security_middleware('OPERATOR_ONLY', {'server':{'port':18300}})
        patched = patch.object(app, 'registry', self.case.registry)
        patched.start(); self.addCleanup(patched.stop)
        self.client = TestClient(self.api, client=('127.0.0.1',40000))
        self.addCleanup(self.client.close)
        self.base = '/api/artifact-briefs/'+self.audit['brief_id']

    def test_all_agent_routes_reject_operator_cookie_or_missing_auth_without_effects(self):
        before = self.case.files()
        for path, method, body in ((self.base,'GET',None),(self.base+'/delivery','GET',None),
                (self.base+'/parent','GET',None),('/api/artifact-results','POST',{}),
                (self.base+'/reject','POST',{'content':'bad','received_truncated':False})):
            for headers in ({},{'x-session-token':'OPERATOR_ONLY'}, {'cookie':'session_token=OPERATOR_ONLY'},
                            {'authorization':'Bearer OPERATOR_ONLY'},
                            {**self.headers,'origin':'https://untrusted.invalid'}):
                with self.subTest(path=path, headers=tuple(headers)):
                    response=self.client.request(method,path,headers=headers,json=body)
                    self.assertEqual(response.status_code,403)
                    self.assertEqual(response.headers.get('cache-control'),'no-store')
                    self.assertEqual(response.json(), {'status':'rejected','code':'artifact_access_denied',
                        'error':'Authenticated managed seat and assigned dispatch required.',
                        'diagnostic_id':None,'received_truncated':False})
        self.assertEqual(self.case.files(),before)

    def test_exact_context_result_and_cli_private_delivery_refusal(self):
        for path in (self.base,self.base+'/parent',self.base+'/delivery'):
            response=self.client.get(path,headers=self.headers)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.headers['cache-control'],'no-store')
        public=self.client.get(self.base,headers=self.headers).text
        private=self.client.get(self.base+'/delivery',headers=self.headers).json()
        self.assertNotIn(private['seal_secret'],public)
        self.assertNotIn(self.audit['producer']['launch_nonce'],public)
        signed=self.case.sealed_fixture_record(self.audit,self.consumer,
            observation={'confirmed_model':'observed','confirmation_reason':'api_response'})
        response=self.client.post('/api/artifact-results',headers=self.headers,json=signed)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'admitted')
        self.assertEqual(self.client.post('/api/artifact-results',headers=self.headers,json=signed).json(),response.json())
        cli=self.case.prepare()
        self.case.claim(cli)
        path='/api/artifact-briefs/'+cli['brief_id']
        before=self.case.files()
        for suffix,method,body in (('/delivery','GET',None),('/reject','POST',{'content':'bad','received_truncated':False})):
            refusal=self.client.request(method,path+suffix,headers={'authorization':'Bearer '+self.case.instance['token']},json=body)
            self.assertEqual(refusal.status_code,403)
        self.assertEqual(self.case.files(),before)

    def test_strict_bytes_shapes_and_error_mapping_are_fixed_and_no_store(self):
        before=self.case.files()
        cases=((self.base+'?extra=1','GET',None,400),('/api/artifact-results','POST',b'{"payload":{},"payload":{}}',400),
               ('/api/artifact-results','POST',b'\xff',400),('/api/artifact-results','POST',b'{"x":NaN}',400),
               (self.base+'/reject','POST',b'{"content":null,"received_truncated":false}',400))
        for path,method,body,status in cases:
            with self.subTest(path=path,body=body):
                response=self.client.request(method,path,headers=self.headers,content=body)
                self.assertEqual(response.status_code,status,response.text)
                self.assertEqual(response.headers.get('cache-control'),'no-store')
        self.assertEqual(self.case.files(),before)
        for exception,status,code in ((self.case.storage.ArtifactConflict('PRIVATE'),409,'artifact_conflict'),
                (self.case.storage.ArtifactValidationError('PRIVATE'),400,'artifact_invalid_request'),
                (self.case.storage.ArtifactUnavailable('PRIVATE'),503,'artifact_storage_unavailable'),
                (RuntimeError('PRIVATE'),503,'artifact_unavailable')):
            with patch.object(self.case.authority,'get_parent',side_effect=exception):
                response=self.client.get(self.base+'/parent',headers=self.headers)
            self.assertEqual(response.status_code,status)
            self.assertEqual(response.json()['code'],code)
            self.assertNotIn('PRIVATE',response.text)

    def test_oversize_and_secret_errors_are_bounded_redacted_and_do_not_mutate(self):
        maximum=self.module.MAX_RESULT_RECORD_BYTES
        before=self.case.files()
        response=self.client.post('/api/artifact-results',headers=self.headers,content=b'x'*(maximum+1))
        self.assertEqual(response.status_code,413)
        self.assertEqual(response.json()['code'],'artifact_request_too_large')
        self.assertEqual(self.case.files(),before)
        private=self.case.briefs.get_private(self.audit['brief_id'])['_artifact_seal']['seal_secret']
        secrets=(private,self.instance['token'],self.audit['producer']['launch_nonce'],'HOSTILE_MARKDOWN')
        output=io.StringIO();handler=logging.StreamHandler(output)
        logger=logging.getLogger();logger.addHandler(handler)
        try:
            with patch.object(self.case.authority,'get_delivery',side_effect=RuntimeError(' '.join(secrets))):
                response=self.client.get(self.base+'/delivery',headers=self.headers)
        finally:
            logger.removeHandler(handler)
        for secret in secrets:
            self.assertNotIn(secret,response.text)
            self.assertNotIn(secret,output.getvalue())
        self.assertEqual(self.case.files(),before)

if __name__=='__main__':
    unittest.main()
