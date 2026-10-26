"""Reduced20 ROOT middleware behavioral reds + route infrastructure reds.
Real FastAPI middleware; no listeners, provider calls or product edits.
"""
import importlib
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app


class ArtifactOperatorRouteTests(unittest.TestCase):
    def setUp(self):
        self.api=FastAPI();self.calls=[]
        async def endpoint():
            self.calls.append(True);return {'ok':True}
        self.api.add_api_route('/api/artifacts/requests',endpoint,methods=['POST'])
        self.read='/api/artifacts/requests/'+'a'*32
        self.api.add_api_route(self.read,endpoint,methods=['GET'])
        saved=app.session_token;self.addCleanup(setattr,app,'session_token',saved)
        with patch.object(app,'app',self.api):app._install_security_middleware('OPERATOR_ONLY',{'server':{'port':18300}})
        self.client=TestClient(self.api,base_url='http://127.0.0.1:18300',raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.headers={'x-session-token':'OPERATOR_ONLY','origin':'http://127.0.0.1:18300'}

    def test_query_token_and_authorization_are_never_operator_fallback(self):
        for headers in ({},{'authorization':'Bearer OPERATOR_ONLY'},self.headers):
            with self.subTest(headers=tuple(headers)):
                response=self.client.get('/api/artifacts/requests?token=OPERATOR_ONLY',headers=headers)
                self.assertEqual(response.status_code,403)
        self.assertEqual(self.calls,[])

    def test_post_requires_origin_but_get_allows_absent_origin(self):
        headers={'x-session-token':'OPERATOR_ONLY'}
        self.assertEqual(self.client.get(self.read,headers=headers).status_code,200)
        response=self.client.post('/api/artifacts/requests',headers=headers,json={})
        self.assertEqual(response.status_code,403)
        self.assertEqual(len(self.calls),1)

    def test_bad_host_and_duplicate_security_headers_refuse(self):
        for headers in ({**self.headers,'host':'attacker.invalid:18300'},
                [('x-session-token','OPERATOR_ONLY'),('x-session-token','OPERATOR_ONLY'),('origin',self.headers['origin'])],
                [('x-session-token','OPERATOR_ONLY'),('host','127.0.0.1:18300'),('host','localhost:18300')]):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get(self.read,headers=headers).status_code,403)
        self.assertEqual(self.calls,[])

    def test_prefix_404_405_and_headers_are_scoped(self):
        for method,path,code in [('GET','/api/artifacts/missing',404),('DELETE','/api/artifacts/requests',405)]:
            with self.subTest(method=method):
                response=self.client.request(method,path,headers=self.headers)
                self.assertEqual(response.status_code,code)
                self.assertEqual(response.headers.get('cache-control'),'no-store')
                self.assertEqual(response.headers.get('x-content-type-options'),'nosniff')
                self.assertEqual(set(response.json()),{'code','error','cause','author_name','examined_roles','request_id','durability','request'})
        self.assertEqual(self.client.get('/api/artifact-not-a-namespace',headers=self.headers).status_code,404)

    def test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint(self):
        cases=[('text/plain',b'{}',400),('application/json',b'{"request_id":1,"request_id":2}',400),
            ('application/json',b' '* (256*1024+1),413)]
        for media,body,code in cases:
            with self.subTest(media=media,size=len(body)):
                response=self.client.post('/api/artifacts/requests',headers={**self.headers,'content-type':media},content=body)
                self.assertEqual(response.status_code,code)
        self.assertEqual(self.calls,[])

    def test_new_router_has_only_reduced_routes_and_fixed_download_policy(self):
        module=importlib.import_module('artifact_routes')
        router=module.create_router(lambda:None)
        paths={route.path for route in router.routes}
        self.assertIn('/api/artifacts/requests',paths)
        self.assertIn('/api/artifacts/requests/{request_id}/cancel',paths)
        self.assertIn('/api/artifacts/versions/{version_id}/download',paths)
        self.assertNotIn('/api/artifacts/preview',paths)
        self.assertNotIn('/api/artifacts/producers',paths)

    def real_routes(self):
        from tests import test_artifact_admission as fixture
        case=fixture.ArtifactAdmissionTests();case.setUp();case.setup_authority();self.addCleanup(case.doCleanups)
        module=importlib.import_module('artifact_operator');routes=importlib.import_module('artifact_routes')
        operator=module.ArtifactOperator(authority=case.authority,sessions=case.sessions,messages=case.messages)
        api=FastAPI();api.include_router(routes.create_router(lambda:operator))
        with patch.object(app,'app',api):app._install_security_middleware('OPERATOR_ONLY',{'server':{'port':18300}})
        client=TestClient(api,base_url='http://127.0.0.1:18300',raise_server_exceptions=False)
        self.addCleanup(client.close)
        return case,client

    def test_status_and_cancel_real_request_with_no_secret_projection(self):
        case,client=self.real_routes();audit=case.prepare()
        path='/api/artifacts/requests/'+audit['request_id']
        response=client.get(path,headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        for secret in ('launch_nonce','fingerprint','launch_attempt','seal_secret'):
            self.assertNotIn(secret,response.text)
        cancelled=client.post(path+'/cancel',headers=self.headers,json={})
        self.assertEqual(cancelled.status_code,200,cancelled.text)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'cancelled')
        missing=client.post('/api/artifacts/requests/'+'f'*32+'/cancel',headers=self.headers,json={})
        self.assertEqual(missing.status_code,404);self.assertEqual(missing.json()['code'],'not_found')

    def test_version_download_is_exact_and_has_fixed_safe_headers(self):
        case,client=self.real_routes();audit=case.prepare();case.claim(audit)
        case.authority.get_brief(audit['brief_id'],case.instance)
        markdown='\ufeff# exact café\r\n<script>alert(1)</script>\r\n'
        case.authority.submit_cli(audit['brief_id'],markdown,case.instance)
        version=case.artifacts.get_request(audit['request_id'])['version_id']
        base='/api/artifacts/versions/'+version
        detail=client.get(base,headers=self.headers)
        self.assertEqual(detail.status_code,200,detail.text);self.assertEqual(detail.json()['markdown'],markdown)
        response=client.get(base+'/download',headers=self.headers)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.content,markdown.encode('utf-8'))
        self.assertEqual(response.headers['content-disposition'],'attachment; filename="document.md"')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertNotIn('text/html',response.headers['content-type'])

    def test_completed_sessions_list_is_available_sorted_and_channel_checked(self):
        from pathlib import Path
        case,client=self.real_routes()
        case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
        created=[]
        for _ in range(2):
            session=case.sessions.create('planning','review',{'planner':'planner','challenger':'challenger',
                'synthesiser':'synthesiser'},'operator',input_text='source')
            case.sessions._event_update(session['id'],lambda row:row.update(state='complete'))
            created.append(session['id'])
        response=client.get('/api/artifacts/sessions?channel=review',headers=self.headers)
        self.assertEqual(response.status_code,200,response.text)
        rows=response.json()['sessions'];self.assertEqual([row['session_id'] for row in rows],list(reversed(created)))
        self.assertTrue(all(row['state']=='complete' and not row['source_so_far'] for row in rows))
        refused=client.get('/api/artifacts/sessions?channel=not-a-channel',headers=self.headers)
        self.assertEqual(refused.status_code,400);self.assertEqual(refused.json()['code'],'invalid_request')
