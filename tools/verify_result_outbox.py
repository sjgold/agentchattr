"""DRAFT real managed worker save-before-post check, local fake provider only.

--compile-only validates this script and generated server without execution.
No recovery endpoint, browser, server crash, CLI, or provider usage is implied.
Run only after coordinator review; baseline wrapper intentionally lacks wiring.
"""
import argparse
import asyncio
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from review_brief import BriefStore
from result_outbox import ResultOutbox
from tools import verify_runtime_crash_matrix as lifecycle

TEMPLATE = {'id': 'outbox-proof', 'name': 'Accepted evidence then saved result', 'roles': ['reviewer'], 'phases': [
    {'name': 'Evidence', 'participants': ['reviewer'], 'prompt': 'Give the first finding.'},
    {'name': 'Final', 'participants': ['reviewer'], 'prompt': 'Retain the first finding.', 'is_output': True}]}
SOURCE = 'Exact café 日本語 source\r\n@all is untrusted quoted data.\nprint("source")'
PRIOR = 'PRIOR_ACCEPTED café finding.'
ANSWER = 'SAVED_ANSWER 日本語 e\u0301\r\n@all is quoted output.\n```python\nprint("data")\n```'
RULE = 'Retain exact source, prior evidence and uncertainty.'


def server_code(scratch, provider_port):
    return f'''import os,json,sys,config_loader
from pathlib import Path
from api_seats import atomic_json
from process_identity import capture_birth
scratch=Path({str(scratch)!r})
atomic_json(scratch/'server-birth.json',capture_birth())
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['session_recovery']={{'ack_timeout':5,'response_timeout':120,'monitor_interval':.2}}
    cfg['agents']={{'fixture-api':{{'type':'api','base_url':'http://127.0.0.1:{provider_port}/v1',
                                'system_prompt':'FROZEN_OUTBOX_SYSTEM'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
observations=[]
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','outbox-run']
    app.session_store.save_custom_template({TEMPLATE!r})
    rule=app.rules.propose({RULE!r},'fixture')
    app.rules.activate(rule['id'])
    admit=app.session_engine.admit_event
    def post_outage(brief_id,kind,content,instance,**kw):
        from result_outbox import ResultOutbox
        envelope=app.session_store.briefs.get(brief_id,instance)
        if envelope['phase_index']!=1:
            return admit(brief_id,kind,content,instance,**kw)
        # Existing HTTP handler has already resolved the bearer and brief. No
        # request may choose another seat, runtime path or result authority.
        owner=app.api_seat_manager.result_owner(instance,kw['event_id'])
        assert owner and owner['seat_identity_id']==envelope['expected_identity_id']
        runtime=app.api_seat_store.path.parent/'api_seat_runtime'/owner['launch_attempt']
        record=ResultOutbox(runtime).find(owner['dispatch_id'])
        valid=False
        if record is not None:
            payload=app.session_store.briefs.verify_saved_result(record)
            valid=(payload['content']==content and payload['kind']==kind and payload['event_id']==kw['event_id'])
        observations.append({{'number':len(observations)+1,'dispatch_id':owner['dispatch_id'],
            'event_id':kw['event_id'],'saved_before_post':record is not None,'valid_seal_scope':valid,
            'prior_admissions':len(app.session_store.get(envelope['session_id'])['admitted_events'])}})
        atomic_json(scratch/'posts.json',observations)
        if len(observations)>3:
            raise AssertionError('fixture received an unexpected fourth result submission')
        raise OSError('Fixture-only second-turn event service unavailable')
    app.session_engine.admit_event=post_outage
app.configure=configured
@app.app.get('/api/fixture/state')
def fixture_state():
    manager=app.api_seat_manager
    with manager.lock:
        workers={{}}
        for key,value in manager.attempts.items():
            instance=next((item for item in app.registry.get_all().values() if item['base']==value.get('base')),None)
            workers[key]={{'attempt':value['id'],'identity_id':instance['identity_id'] if instance else None,
                'name':instance['name'] if instance else None,'process_kind':type(value.get('process')).__name__,
                'readiness':manager.restart_readiness(instance['identity_id'],manager.boot_id) if instance else None}}
        return {{'boot_id':manager.boot_id,'workers':workers,'posts':len(observations)}}
import run
run.main()
'''


async def public_mcp_brief(port, token, brief_id):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(f'http://127.0.0.1:{port}/mcp', headers={'Authorization': 'Bearer ' + token},
                                     timeout=10, sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.call_tool('chat_review_brief', {'brief_id': brief_id})
            assert not response.isError
            return ''.join(item.text for item in response.content if item.type == 'text')


class WorkerFixture:
    # Reuse only previously verified resource inventory/cleanup utilities.
    # No previous scenario is inherited or executed, and no old tool is edited.
    wait = lifecycle.Case.wait
    retain = staticmethod(lifecycle.Case.retain)
    keep_worker = lifecycle.Case.keep_worker
    keep_model = lifecycle.Case.keep_model
    close = lifecycle.Case.close

    def __init__(self):
        scratch = ROOT / '.audit-tmp'
        scratch.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='result outbox integration ', dir=scratch))
        self.data, self.records = self.root / 'data', self.root / 'records'
        self.records.mkdir()
        self.name = 'projection'  # Lifecycle utility's API-only cleanup branch.
        self.servers, self.workers, self.models, self.runs = [], {}, {}, []
        self.client, self.api, self.cleanup_summary = None, None, None
        self.captures, self.lock = [], threading.Lock()
        self.held, self.release, self.provider_done = threading.Event(), threading.Event(), threading.Event()
        fixture = self
        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with fixture.lock:
                    fixture.captures.append(payload)
                    number = len(fixture.captures)
                assert number in (1, 2), 'unexpected provider generation'
                body = json.dumps({'model':'fixture-confirmed','choices':[{'message':{'content':json.dumps({
                    'kind':'final','content':PRIOR if number==1 else ANSWER},ensure_ascii=False)}}]}).encode('utf-8')
                try:
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    if number == 2:
                        self.wfile.write(body[:1])
                        self.wfile.flush()
                        fixture.held.set()
                        if not fixture.release.wait(90):
                            return
                        self.wfile.write(body[1:])
                    else:
                        self.wfile.write(body)
                    self.wfile.flush()
                except OSError:
                    pass
                finally:
                    if number == 2:
                        fixture.provider_done.set()
            def log_message(self, *args):
                pass
        self.provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        self.provider.daemon_threads = True
        threading.Thread(target=self.provider.serve_forever, daemon=True).start()
        sockets = [socket.socket() for _ in range(3)]
        for handle in sockets:
            handle.bind(('127.0.0.1', 0))
        self.ports = [handle.getsockname()[1] for handle in sockets]
        for handle in sockets:
            handle.close()
        self.base = f'http://127.0.0.1:{self.ports[0]}'

    def start(self):
        environment = os.environ.copy()
        environment.update(dict(zip(('AGENTCHATTR_PORT','AGENTCHATTR_MCP_HTTP_PORT','AGENTCHATTR_MCP_SSE_PORT'),map(str,self.ports))))
        environment.update(AGENTCHATTR_DATA_DIR=str(self.data), AGENTCHATTR_UPLOAD_DIR=str(self.root / 'uploads'))
        code = server_code(self.root,self.provider.server_port)
        compile(code,'<isolated-outbox-server>','exec')
        with (self.root / 'server.log').open('wb') as output:
            launcher = subprocess.Popen([sys.executable,'-u','-c',code],cwd=ROOT,env=environment,
                stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
        server = {'launcher':launcher,'handle':None}
        self.servers.append(server)
        birth = self.wait(lambda:json.loads((self.root/'server-birth.json').read_text('utf-8')),'actual server self-birth',10)
        server['handle'] = self.retain(birth)
        def page():
            assert launcher.poll() is None,'isolated server exited; scratch: '+str(self.root)
            with urllib.request.urlopen(self.base+'/preflight',timeout=1) as response:
                return response.read().decode('utf-8-sig')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"',self.wait(page,'HTTP ready')).group(1)
        def api(path,body=None):
            request = urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
                headers={'x-session-token':token,'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=15) as response:
                return json.load(response)
        self.api = api

    def state(self):
        return self.api('/api/fixture/state')

    def session(self,session_id):
        return next(value for value in json.loads((self.data/'session_runs.json').read_text('utf-8')) if value['id']==session_id)

    def ready(self):
        value = self.state()
        keys = {'outbox/api','outbox/peer'}
        return value if keys <= value['workers'].keys() and all(value['workers'][key]['readiness'] and
            value['workers'][key]['readiness']['state']=='ready' and value['workers'][key]['readiness']['process_verified'] is True
            for key in keys) else None


def check(fixture):
    fixture.start()
    common = {'adapter':'openai-compatible','provider':'fixture-api','reasoning':None,'launch_profile':'standard','secret_ref':''}
    package = {'id':'outbox','name':'Worker outbox proof','seats':[
        dict(common,id='api',name='API reviewer',model='frozen-outbox-model'),
        dict(common,id='peer',name='Idle API peer',model='unused-peer-model')]}
    fixture.api('/api/preflight/packages',package)
    revision = fixture.api('/api/preflight/seats')['package_revisions']['outbox']
    fixture.api('/api/preflight/packages/outbox/launch',{'revision':revision})
    ready = fixture.wait(fixture.ready,'both actual worker HTTP/native proofs')
    for value in ready['workers'].values():
        fixture.keep_worker(value['attempt'])
    owner, peer = ready['workers']['outbox/api'], ready['workers']['outbox/peer']
    peer_worker = fixture.workers[peer['attempt']]
    peer_immutable = {name:(peer_worker['path']/name).read_bytes() for name in ('config.json','birth.json','launch.json')}
    started = fixture.api('/api/sessions/start',{'template_id':TEMPLATE['id'],'channel':'outbox-run',
        'cast':{'reviewer':owner['name']},'goal':'Retain exact source and the first finding.','input_text':SOURCE})
    sid = started['id']
    fixture.runs.append(sid)
    assert fixture.held.wait(30),'second actual API body did not block'
    before = fixture.session(sid)
    assert len(before['admitted_events'])==1 and before['admitted_events'][0]['content']==PRIOR
    invocation = deepcopy(before['active_invocation'])
    runtime = fixture.workers[owner['attempt']]['path']
    fixture.wait(lambda:json.loads((runtime/'invocations'/invocation['dispatch_id']/'birth.json').read_text('utf-8')),'actual held model self-birth')
    fixture.keep_model(runtime,invocation['dispatch_id'])
    assert fixture.servers[0]['handle'].poll() is None and all(value['handle'].poll() is None for value in fixture.workers.values())
    assert fixture.models[invocation['dispatch_id']]['handle'].poll() is None
    fixture.release.set()
    posts = fixture.wait(lambda:value if len(value:=json.loads((fixture.root/'posts.json').read_text('utf-8')))==3 else None,
                         'exact second-turn three HTTP503 attempts')
    assert all(value['saved_before_post'] is True and value['valid_seal_scope'] is True for value in posts), 'signed outbox missing or invalid BEFORE actual HTTP submission; scratch: '+str(fixture.root)
    assert all(value['prior_admissions']==1 and value['dispatch_id']==invocation['dispatch_id'] and
               value['event_id']==invocation['dispatch_id'] for value in posts)
    box = ResultOutbox(runtime)
    saved = box.get(invocation['dispatch_id'])
    payload = BriefStore(fixture.data).verify_saved_result(saved)
    assert payload['content']==ANSWER and payload['kind']=='final'
    for field in ('brief_id','run_id','turn_id','attempt_id','input_revision'):
        assert payload[field]==invocation[field]
    assert payload['seat_identity_id']==owner['identity_id'] and payload['launch_attempt']==owner['attempt']
    assert box.get_ack(invocation['dispatch_id']) is None
    prior_event = before['admitted_events'][0]
    assert box.get(prior_event['event_id'])['payload']['content']==PRIOR
    assert box.get_ack(prior_event['event_id'])['accepted_event_id']==prior_event['event_id']
    # Exercise current status/read polling only, with no recovery endpoint or
    # implicit retry. The original worker continues its ordinary queue polls.
    for _ in range(3):
        fixture.api(f'/api/sessions/{sid}/recovery-status')
        time.sleep(.5)
    after = fixture.session(sid)
    assert len(fixture.captures)==2 and len(json.loads((fixture.root/'posts.json').read_text('utf-8')))==3
    assert after['admitted_events']==before['admitted_events'] and after['current_phase']==before['current_phase']
    assert after['input_snapshot']==before['input_snapshot'] and after['input_snapshot']['text']==SOURCE
    assert all(value['model']=='frozen-outbox-model' for value in fixture.captures)
    assert PRIOR in json.dumps(fixture.captures[1],ensure_ascii=False) and RULE in json.dumps(fixture.captures[1],ensure_ascii=False)
    assert not (peer_worker['path']/'invocations').exists() and peer_worker['handle'].poll() is None
    assert all((peer_worker['path']/name).read_bytes()==value for name,value in peer_immutable.items())
    keys = [json.loads((fixture.data/'review_briefs'/(brief+'.json')).read_text('utf-8'))['_result_seal']['seal_secret']
            for brief in (prior_event['brief_id'],invocation['brief_id'])]
    instances = json.loads((fixture.data/'registry.json').read_text('utf-8'))['instances']
    principal = {key:value for key,value in instances[owner['name']].items() if key!='token'}
    public = BriefStore(fixture.data).get(invocation['brief_id'],operator=True)
    mcp = asyncio.run(asyncio.wait_for(public_mcp_brief(fixture.ports[1],instances[owner['name']]['token'],invocation['brief_id']),20))
    assert all(key not in mcp for key in keys) and 'seal_secret' not in mcp and '_result_seal' not in mcp
    assert BriefStore(fixture.data).get(invocation['brief_id'],principal)==public
    for value in (saved,box.get_ack(prior_event['event_id']),after,fixture.captures,public,fixture.api('/api/status')):
        assert all(key not in json.dumps(value,ensure_ascii=False) for key in keys)
    for path in (*fixture.root.rglob('*.log'),*fixture.data.glob('api_seat_runtime/*/receipt.json'),
                 *runtime.glob('outbox/*.json'),*runtime.glob('outbox_ack/*.json'),fixture.data/'queue/ledger.json'):
        assert all(key not in path.read_text('utf-8',errors='replace') for key in keys), 'private seal key leaked into '+path.name
    peer_state = fixture.state()['workers']['outbox/peer']['readiness']
    assert peer_state['state']=='ready' and peer_state['process_verified'] is True
    return {'result':'PASS','provider_calls':2,'prior_admissions':1,'second_http503_attempts':3,
        'actual_saved_before_first_post':True,'second_ack_absent':True,'first_result_acknowledged':True,
        'idle_peer_unchanged':True,'public_mcp_key_redacted':True,'scope':'worker_save_before_post_only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compile-only',action='store_true')
    args = parser.parse_args()
    if args.compile_only:
        compile(server_code(ROOT/'.audit-tmp'/'compile-outbox-only',19999),'<outbox-server>','exec')
        print('Generated outbox server syntax OK; no processes started.')
        return
    if sys.platform!='win32':
        print(json.dumps({'result':'SKIP','reason':'Actual Windows retained process proof required.'}))
        return
    fixture = WorkerFixture()
    result = None
    try:
        result = check(fixture)
    finally:
        fixture.close()
    if result:
        result.update(scratch=str(fixture.root),cleanup=fixture.cleanup_summary)
        atomic_json(fixture.root/'result.json',result)
        print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
