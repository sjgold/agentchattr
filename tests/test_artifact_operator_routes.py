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
        self.api.add_api_route(self.read,endpoint,methods=['GET','HEAD'])
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
        expected={('/api/artifacts/requests',frozenset({'POST'})),
            ('/api/artifacts/requests/{request_id}',frozenset({'GET','HEAD'})),
            ('/api/artifacts/requests/{request_id}/cancel',frozenset({'POST'})),
            ('/api/artifacts/requests/{request_id}/document',frozenset({'GET','HEAD'})),
            ('/api/artifacts/versions/{version_id}',frozenset({'GET','HEAD'})),
            ('/api/artifacts/versions/{version_id}/download',frozenset({'GET','HEAD'})),
            ('/api/artifacts/sessions',frozenset({'GET','HEAD'}))}
        self.assertEqual({(route.path,frozenset(route.methods)) for route in router.routes},expected)
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
        conflict=client.post('/api/artifacts/requests/'+audit['request_id']+'/cancel',headers=self.headers,json={})
        self.assertEqual(conflict.status_code,409);self.assertEqual(conflict.json()['request']['state'],'fulfilled')
        self.assertEqual(conflict.json()['durability'],'recorded')
        base='/api/artifacts/versions/'+version
        detail=client.get(base,headers=self.headers)
        self.assertEqual(detail.status_code,200,detail.text);self.assertEqual(detail.json()['markdown'],markdown)
        response=client.get(base+'/download',headers=self.headers)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.content,markdown.encode('utf-8'))
        self.assertEqual(response.headers['content-disposition'],'attachment; filename="document.md"')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(response.headers['content-type'],'text/markdown; charset=utf-8')
        self.assertEqual(set(detail.json()),{'version','markdown'})
        self.assertEqual(set(detail.json()['version']),{'id','lineage_id','sequence','channel','request_id','sha256',
            'byte_length','created_at','author_name','requested_model','confirmed_model','confirmation_reason','source_run'})
        for field in ('launch_nonce','fingerprint','launch_attempt'):
            self.assertNotIn(audit['producer'][field],detail.text)
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

    def test_security_raw_header_matrix_envelopes_and_legacy_namespace(self):
        async def legacy():return {'legacy':True}
        self.api.add_api_route('/api/artifact-not-a-namespace',legacy,methods=['GET'])
        legacy=self.client.get('/api/artifact-not-a-namespace?token=OPERATOR_ONLY')
        self.assertEqual(legacy.status_code,200)
        errors=[{}, {'x-session-token':''},{'x-session-token':'wrong'},
            {**self.headers,'authorization':'Bearer seat'},
            [('x-session-token','OPERATOR_ONLY'),('origin',self.headers['origin']),('origin',self.headers['origin'])],
            [('x-session-token','OPERATOR_ONLY'),('authorization','Bearer x'),('authorization','Bearer y')]]
        for headers in errors:
            with self.subTest(headers=headers):
                response=self.client.get('/api/artifacts/unknown',headers=headers)
                self.assertEqual(response.status_code,403)
                self.assertEqual(response.json()['code'],'operator_forbidden')
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertEqual(response.headers['x-content-type-options'],'nosniff')
                self.assertEqual(set(response.json()),{'code','error','cause','author_name','examined_roles','request_id','durability','request'})
        self.assertEqual(self.client.post('/api/artifacts/requests',headers={**self.headers,'origin':''},json={}).status_code,403)
        self.assertEqual(self.client.head(self.read,headers={'x-session-token':'OPERATOR_ONLY'}).status_code,200)
        for host,code in [('LOCALHOST:18300',200),('[::1]:18300',200),('user@localhost:18300',403),('localhost',403),('localhost:1',403)]:
            self.assertEqual(self.client.get(self.read,headers={**self.headers,'host':host}).status_code,code)

    def test_json_boundaries_chunked_body_and_scoped_errors(self):
        valid=b'{}'+b' '*(256*1024-2)
        response=self.client.post('/api/artifacts/requests',headers={**self.headers,'content-type':'application/json; charset=utf-8'},content=valid)
        self.assertEqual(response.status_code,200)
        response=self.client.post('/api/artifacts/requests',headers={**self.headers,'content-type':'application/json'},content=iter([b' '* (128*1024)]*3))
        self.assertEqual(response.status_code,413);self.assertEqual(response.json()['code'],'request_too_large')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        for raw in (b'{"a":NaN}',b'{"a":1,"a":2}',b'[]'):
            response=self.client.post('/api/artifacts/requests',headers={**self.headers,'content-type':'application/json'},content=raw)
            self.assertEqual(response.status_code,400);self.assertEqual(response.headers['cache-control'],'no-store')
        # Existing endpoint responses are wrapped only within the new prefix.
        async def fails():raise RuntimeError('PRIVATE_SERVER_ERROR')
        self.api.routes[:]=[route for route in self.api.routes if route.path!=self.read]
        self.api.add_api_route(self.read,fails,methods=['GET'])
        response=self.client.get(self.read,headers=self.headers)
        self.assertEqual(response.status_code,500);self.assertEqual(response.json()['code'],'unexpected_failure')
        self.assertNotIn('PRIVATE_SERVER_ERROR',response.text)

    def test_create_202_replay_200_validation_and_detail_errors(self):
        from tests.test_artifact_operator_core import accepted_source
        import uuid
        case,client=self.real_routes();session,_,_=accepted_source(case)
        body={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],
            'run_id':session['run_id'],'instruction':'x'*32768}
        result=client.post('/api/artifacts/requests',headers=self.headers,json=body)
        self.assertEqual(result.status_code,202,result.text)
        self.assertEqual(client.post('/api/artifacts/requests',headers=self.headers,json=body).status_code,200)
        self.assertEqual(client.get('/api/artifacts/requests/'+body['request_id']+'/document',headers=self.headers).status_code,409)
        self.assertEqual(client.get('/api/artifacts/requests/'+'f'*32,headers=self.headers).status_code,404)
        for changes,code,error_code in [({'instruction':'x'*32769},413,'request_too_large'),({'instruction':'bad\x01'},400,'invalid_request'),({'unknown':True},400,'invalid_request'),
                ({'session_id':999999},404,'session_unknown'),({'run_id':'f'*32},404,'run_unknown'),({'channel':'peer'},409,'channel_mismatch')]:
            with self.subTest(changes=tuple(changes)):
                response=client.post('/api/artifacts/requests',headers=self.headers,json={**body,'request_id':uuid.uuid4().hex,**changes})
                self.assertEqual(response.status_code,code,response.text);self.assertEqual(response.json()['code'],error_code)
        self.assertEqual(client.get('/api/artifacts/versions/'+'e'*32,headers=self.headers).status_code,404)

    def test_fixed_error_codes_do_not_become_generic_500(self):
        from tests.test_artifact_operator_core import accepted_source
        import uuid
        import artifact_operator,artifact_service
        from channel_lifecycle import ChannelInactive
        case,client=self.real_routes();session,_,_=accepted_source(case)
        body={'request_id':uuid.uuid4().hex,'channel':'review','session_id':session['id'],'run_id':session['run_id'],'instruction':'report'}
        from artifact_sources import ArtifactSourceError
        cases=[(case.service,'require_active',ChannelInactive('PRIVATE'),409,'channel_inactive'),
            (case.artifacts,'put_packet',OSError('PRIVATE'),503,'storage_unavailable'),
            (case.authority,'prepare_request',artifact_service._ArtifactBoundaryHeld(),503,'boundary_held'),
            (artifact_operator,'capture_artifact_session_source',RuntimeError('PRIVATE'),500,'unexpected_failure'),
            (artifact_operator,'capture_artifact_session_source',ArtifactSourceError(),409,'source_unavailable'),
            (artifact_operator,'capture_artifact_session_source',ArtifactSourceError('source_too_large'),413,'source_too_large')]
        for owner,name,error,status,code in cases:
            with self.subTest(code=code),patch.object(owner,name,side_effect=error):
                response=client.post('/api/artifacts/requests',headers=self.headers,json={**body,'request_id':uuid.uuid4().hex})
                self.assertEqual(response.status_code,status,response.text);self.assertEqual(response.json()['code'],code)
                self.assertIsNone(response.json()['cause']);self.assertNotIn('PRIVATE',response.text)
                self.assertEqual(response.headers['cache-control'],'no-store');self.assertEqual(response.headers['x-content-type-options'],'nosniff')

    def test_sessions_page_truncation_ties_offsets_and_exact_keys(self):
        from pathlib import Path
        case,client=self.real_routes();case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
        ids=[]
        for _ in range(23):
            session=case.sessions.create('planning','review',{'planner':'planner','challenger':'challenger','synthesiser':'synthesiser'},'operator')
            case.sessions._event_update(session['id'],lambda row:row.update(state='complete',started_at=100,template_name='',goal='é'*200))
            ids.append(session['id'])
        first=client.get('/api/artifacts/sessions?channel=review',headers=self.headers).json()
        second=client.get('/api/artifacts/sessions?channel=review&offset=20',headers=self.headers).json()
        self.assertEqual(set(first),{'sessions','offset','has_more'});self.assertTrue(first['has_more']);self.assertFalse(second['has_more'])
        self.assertEqual([row['session_id'] for row in first['sessions']+second['sessions']],list(reversed(ids)))
        for row in first['sessions']:
            self.assertEqual(set(row),{'session_id','run_id','title','state','started_at','source_so_far','title_truncated'})
            self.assertTrue(row['title_truncated']);self.assertEqual(len(row['title'].encode('utf-8')),256)
        for offset in ('-1','true','9'*20):
            self.assertEqual(client.get('/api/artifacts/sessions?channel=review&offset='+offset,headers=self.headers).status_code,400)

    def test_scoped_422_normalization_does_not_change_legacy_endpoint(self):
        from fastapi.responses import JSONResponse
        async def unprocessable():return JSONResponse({'private':'INTERNAL_VALIDATION'},status_code=422)
        self.api.routes[:]=[route for route in self.api.routes if route.path!=self.read]
        self.api.add_api_route(self.read,unprocessable,methods=['GET'])
        self.api.add_api_route('/api/legacy-validation',unprocessable,methods=['GET'])
        response=self.client.get(self.read,headers=self.headers)
        self.assertEqual(response.status_code,400);self.assertEqual(response.json()['code'],'invalid_request')
        self.assertNotIn('INTERNAL_VALIDATION',response.text)
        self.assertEqual(self.client.get('/api/legacy-validation?token=OPERATOR_ONLY').status_code,422)

    def test_capability_off_new_create_is_typed_and_has_no_reservation(self):
        from tests.test_artifact_operator_core import accepted_source
        import uuid
        case,client=self.real_routes();session,_,_=accepted_source(case)
        identifier=uuid.uuid4().hex
        body={'request_id':identifier,'channel':'review','session_id':session['id'],'run_id':session['run_id'],'instruction':'report'}
        before=case.artifacts.path.read_bytes() if case.artifacts.path.exists() else None
        with patch('runtime_protocol.SUPPORTED_CAPABILITIES',()):
            response=client.post('/api/artifacts/requests',headers=self.headers,json=body)
        self.assertEqual(response.status_code,409);self.assertEqual(response.json()['code'],'no_author_available')
        self.assertEqual(response.json()['cause'],'capability_off');self.assertEqual(response.json()['error'],'Artifact authoring is not enabled.')
        self.assertIsNone(case.artifacts.get_request(identifier))
        self.assertEqual(case.artifacts.path.read_bytes() if case.artifacts.path.exists() else None,before)
