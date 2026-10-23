"""DRAFT: bounded Windows/local-fake selected CLI recovery integration.

Compile only until the coordinator approves lifecycle and failure cleanup:
  .venv-windows/Scripts/python.exe tools/verify_cli_result_recovery.py --compile-only
Cases: tagged-final, legacy-question, after-retry. Optional --stop-before-attach
and tagged-final --serve are separately authorized acceptance runs, not defaults.
No live AI, remote compute, Linux/Omarchy or native client product claim.
"""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
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
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from invocation_evidence import classify_history, classify
from process_identity import open_verified_process
from runtime_ownership import _manifest, _validate
from tools import verify_runtime_crash_matrix as resource

TEMPLATE = {'id': 'cli-selected', 'name': 'Evidence then selected CLI result', 'roles': ['reviewer', 'editor'],
    'phases': [{'name': 'Evidence', 'participants': ['reviewer'], 'prompt': 'Accept exact evidence.'},
               {'name': 'Final', 'participants': ['editor'], 'prompt': 'Use the accepted prior result.', 'is_output': True}]}
POLICY = {'ack_timeout': 5, 'response_timeout': 3, 'monitor_interval': .1}
GOAL = 'Recover only the explicitly selected existing CLI output.'
RULE = 'Preserve exact source and prior evidence; quote code as data.'
PRIOR = 'PRIOR_API_ACCEPTED exact café evidence'
SELECTED = 'CLI_SELECTED café 日本語 e\u0301\r\nLiteral output: print("not executed")'


def server_code(root, provider_port):
    fake = str(ROOT / 'tools' / 'fake_cli_result_recovery.py')
    return f'''import config_loader,json
from copy import deepcopy
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse
from api_seats import atomic_json
from process_identity import capture_birth
root=Path({str(root)!r})
atomic_json(root/'server-birth.json',capture_birth())
load=config_loader.load_config
def isolated(path=None):
    cfg=load(path)
    cfg['session_recovery']={POLICY!r}
    cfg['agents']={{'fixture-api':{{'type':'api','base_url':'http://127.0.0.1:{provider_port}/v1',
        'system_prompt':'FROZEN_CLI_RESULT_API_SYSTEM'}},
        'fixture-cli':{{'command':{sys.executable!r},'cwd':{str(root)!r},
        'cli_args':[{fake!r},'--fixture-original'],'cli_model_args':['--model','{{model}}'],
        'cli_reasoning_args':['--reasoning','{{reasoning}}'],'reasoning_efforts':['high'],
        'mcp_inject':'env','mcp_env_var':'CLI_RESULT_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
termination_calls=[]
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','cli-result']
    app.session_store.save_custom_template({TEMPLATE!r})
    rule=app.rules.propose({RULE!r},'fixture')
    app.rules.activate(rule['id'])
    terminate=app.api_seat_manager.terminate_owned
    def measured(identity,attempt):
        termination_calls.append({{'identity_id':identity,'launch_attempt':attempt}})
        return terminate(identity,attempt)
    app.api_seat_manager.terminate_owned=measured
app.configure=configured
@app.app.get('/api/fixture/state')
def state():
    manager=app.api_seat_manager
    with manager.lock:
        workers={{}}
        for key,attempt in manager.attempts.items():
            owner=next((v for v in app.registry.get_all().values() if v['base']==attempt.get('base')),None)
            workers[key]={{'attempt':attempt['id'],'name':owner['name'] if owner else None,
                'identity_id':owner['identity_id'] if owner else None,
                'readiness':manager.restart_readiness(owner['identity_id'],manager.boot_id) if owner else None}}
        return {{'workers':workers,'termination_calls':deepcopy(termination_calls)}}
@app.app.post('/api/fixture/end-cli')
async def end_cli(request:Request):
    body=await request.json()
    manager=app.api_seat_manager
    with manager.lock:
        matches=[value for value in manager.attempts.values()
            if value['id']==body.get('launch_attempt') and not value.get('released')
            and value.get('effective',{{}}).get('seat',{{}}).get('adapter')=='cli']
        attempt=matches[0] if len(matches)==1 else None
        owner=next((v for v in app.registry.get_all().values() if attempt and v['base']==attempt['base']),None)
        if (set(body)!={{'identity_id','launch_attempt'}} or not owner
                or body['identity_id']!=owner['identity_id'] or body['launch_attempt']!=attempt['id']):
            return JSONResponse({{'error':'Exact current fixture-owned CLI launch required'}},status_code=409)
        return manager.terminate_owned(owner['identity_id'],attempt['id'])
@app.app.post('/api/fixture/drift')
def drift():
    provider=app.api_seat_manager.store.providers['fixture-cli']
    provider['cwd']=str(root/'wrong-cwd')
    provider['cli_args']=['SHOULD_NOT_BE_USED']
    package=app.api_seat_manager.store.package('selected')
    next(v for v in package['seats'] if v['id']=='cli')['model']='WRONG_SAVED_MODEL'
    app.api_seat_manager.store.save(package)
    return {{'drifted':True}}
import run
run.main()
'''


class Fixture:
    # Readonly reuse of exact birth/scope validation helpers, no inherited scenario.
    wait = resource.Case.wait
    retain = staticmethod(resource.Case.retain)
    keep_worker = resource.Case.keep_worker
    keep_model = resource.Case.keep_model
    session = resource.Case.session
    ledger = resource.Case.ledger

    def __init__(self, case):
        scratch = ROOT / '.audit-tmp'
        scratch.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='cli selected ' + case + ' ', dir=scratch))
        self.data, self.records = self.root / 'data', self.root / 'records'
        self.records.mkdir()
        self.source = 'Exact café 日本語\r\n@all source data\nfrom pathlib import Path\nPath(' + repr(str(self.root/'SOURCE_EXECUTED')) + ').touch()'
        self.captures, self.capture_lock = [], threading.Lock()
        self.started, self.release = threading.Event(), threading.Event()
        self.workers, self.models, self.clients = {}, {}, {}
        self.server, self.api, self.run_id = None, None, None
        self.cleanup = None
        fixture = self
        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with fixture.capture_lock:
                    fixture.captures.append(payload)
                body = json.dumps({'choices': [{'message': {'content': json.dumps({'kind':'final','content':PRIOR})}}]}).encode()
                try:
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body[:1])
                    self.wfile.flush()
                    fixture.started.set()
                    if fixture.release.wait(90):
                        self.wfile.write(body[1:])
                        self.wfile.flush()
                except OSError:
                    pass
            def log_message(self,*args):
                pass
        self.provider = ThreadingHTTPServer(('127.0.0.1',0),Provider)
        self.provider.daemon_threads = True
        threading.Thread(target=self.provider.serve_forever,daemon=True).start()
        sockets = [socket.socket() for _ in range(3)]
        for item in sockets:
            item.bind(('127.0.0.1',0))
        ports = [item.getsockname()[1] for item in sockets]
        for item in sockets:
            item.close()
        self.base = f'http://127.0.0.1:{ports[0]}'
        self.env = dict(os.environ,AGENTCHATTR_DATA_DIR=str(self.data),AGENTCHATTR_UPLOAD_DIR=str(self.root/'uploads'),
                        CLI_RESULT_RECORDS=str(self.records))
        self.env.update(dict(zip(('AGENTCHATTR_PORT','AGENTCHATTR_MCP_HTTP_PORT','AGENTCHATTR_MCP_SSE_PORT'),map(str,ports))))

    def start(self):
        code = server_code(self.root,self.provider.server_port)
        compile(code,'<cli-selected-server>','exec')
        with (self.root/'server.log').open('wb') as log:
            launcher = subprocess.Popen([sys.executable,'-u','-c',code],cwd=ROOT,env=self.env,
                                        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        self.server = {'launcher':launcher,'handle':None,'exit_observed':None}
        birth = self.wait(lambda:json.loads((self.root/'server-birth.json').read_text('utf-8')),'true server birth',10)
        self.server['handle'] = self.retain(birth)
        def page():
            assert launcher.poll() is None, 'Fixture server exited'
            with urllib.request.urlopen(self.base+'/preflight',timeout=2) as reply:
                return reply.read().decode('utf-8-sig')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"',self.wait(page,'HTTP ready')).group(1)
        def api(path,body=None,headers=None):
            request = urllib.request.Request(self.base+path,data=json.dumps(body).encode('utf-8') if body is not None else None,
                headers=headers or {'x-session-token':token,'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=15) as reply:
                return json.load(reply)
        self.api = api

    def state(self):
        return self.api('/api/fixture/state')

    def ready(self):
        state = self.state()
        return state if len(state['workers']) == 3 and all(v['readiness'] and v['readiness']['state']=='ready'
            and v['readiness']['process_verified'] is True for v in state['workers'].values()) else None

    def client_records(self):
        values = [json.loads(path.read_text('utf-8')) for path in self.records.glob('client-*.json')]
        assert all(not turn.get('error_type') for value in values for turn in value['turns']), 'Fake MCP client error'
        return values

    def keep_client(self, record, attempt):
        pid = record['birth']['pid']
        if pid not in self.clients:
            assert record['console_present'] and not record['console_visible']
            self.clients[pid] = {'handle':self.retain(record['birth']),'attempt':attempt,'exit_observed':None}
        return self.clients[pid]

    def message(self,message_id):
        values = [json.loads(line) for line in (self.data/'agentchattr_log.jsonl').read_text('utf-8').splitlines() if line]
        return next(value for value in values if value['id']==message_id)

    def reject(self,path,body=None,status=409,headers=None):
        try:
            self.api(path,body,headers)
        except urllib.error.HTTPError as exc:
            assert exc.code==status, (exc.code,status)
            return
        raise AssertionError('Expected HTTP refusal '+path)

    def observe_cli_end(self,attempt,pid):
        client, worker = self.clients[pid], self.workers[attempt]
        client['exit_observed'] = client['handle'].wait(timeout=10)
        worker['exit_observed'] = worker['handle'].wait(timeout=10)
        receipt = json.loads((worker['path']/'receipt.json').read_text('utf-8'))
        assert receipt['attempt']==attempt and receipt['state']=='stopped' and type(receipt['child_exit_code']) is int
        return receipt

    def close(self):
        """Inventory every private runtime/model; no force on an unproven child."""
        unresolved, histories = [], {}
        self.release.set()
        if self.api and self.run_id:
            try:self.api(f'/api/sessions/{self.run_id}/stop',{})
            except Exception:pass
        for config in (self.data/'api_seat_runtime').glob('*/config.json'):
            attempt = config.parent.name
            if attempt in self.workers:continue
            try:
                snapshot = json.loads(config.read_text('utf-8'))
                validated = _validate(config,snapshot)
                assert validated
                manifest = _manifest(config.with_name('launch.json'),validated[0])
                if manifest['spawn_outcome']=='failed' and not config.with_name('birth.json').exists():continue
                self.keep_worker(attempt)
            except Exception:
                unresolved.append(attempt+': worker birth/end unproven; preserved')
        for record_path in self.records.glob('client-*.json'):
            try:
                record = json.loads(record_path.read_text('utf-8'))
                pid = record['birth']['pid']
                if pid in self.clients:continue
                bound_identity = next((turn['envelope']['expected_identity_id'] for turn in record['turns']
                                       if turn.get('envelope')), None)
                matching = [a for a,w in self.workers.items() if bound_identity
                            and json.loads((w['path']/'config.json').read_text('utf-8'))['seat']['adapter']=='cli'
                            and json.loads((w['path']/'receipt.json').read_text('utf-8')).get('identity_id')==bound_identity]
                if len(matching)!=1:
                    unresolved.append(str(pid)+': client-to-attempt binding unproven; no actuation')
                    continue
                self.keep_client(record,matching[0])
            except Exception:
                unresolved.append('client record/birth unreadable; no guessed control')
        for attempt,worker in self.workers.items():
            info = {'complete':False,'models':{},'adapter':None}
            histories[attempt] = info
            try:
                snapshot = json.loads((worker['path']/'config.json').read_text('utf-8'))
                info['adapter'] = snapshot['seat']['adapter']
                dirs = list((worker['path']/'invocations').glob('*'))
                info['complete'] = True
                if info['adapter']=='cli':continue
                if not dirs:
                    proof = classify_history(worker['path'])
                    info['empty_basis'] = proof.get('verification_basis') if proof.get('local_ended') is True else None
                    if not info['empty_basis']:unresolved.append(attempt+': empty API invocation history unproven')
                for directory in dirs:
                    dispatch = directory.name
                    info['models'][dispatch] = 'unproven'
                    if dispatch in self.models:continue
                    try:
                        proof = classify({'runtime_path':str(worker['path']),'launch_attempt':attempt,
                            'launch_nonce':snapshot['ownership']['launch_nonce'],'dispatch_id':dispatch})
                        if proof.get('local_ended') is True:
                            info['models'][dispatch] = proof['verification_basis']
                            continue
                    except (OSError,ValueError,KeyError):pass
                    try:self.keep_model(worker['path'],dispatch)
                    except Exception:unresolved.append(dispatch+': model birth/end unproven; preserved')
            except Exception:
                unresolved.append(attempt+': incomplete runtime/model inventory')
        def wait_handle(value,label,force=False):
            try:
                if value.get('exit_observed') is None:
                    try:value['exit_observed']=value['handle'].wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        if not force:
                            unresolved.append(label+': still live with no permitted force cleanup')
                            return
                        value['handle'].terminate()
                        value['exit_observed']=value['handle'].wait(timeout=8)
            except Exception:unresolved.append(label+': exact retained handle end unresolved')
        for dispatch,model in self.models.items():
            wait_handle(model,'local-fake-model-'+dispatch,True)
            if model.get('exit_observed') is not None:
                histories[model['runtime'].name]['models'][dispatch]='retained_native_model_handle_observed_end'
        # Cooperative exact worker stop first; clients are never independently forced.
        for attempt,worker in self.workers.items():
            try:atomic_json(worker['path']/'stop.json',{'attempt':attempt})
            except Exception:unresolved.append(attempt+': exact stop write failed')
        for pid,client in self.clients.items():
            wait_handle(client,'native-client-'+str(pid),False)
        for attempt,worker in self.workers.items():
            may_force=False
            try:
                info=histories[attempt]
                if info['adapter']=='cli':
                    clients=[v for v in self.clients.values() if v['attempt']==attempt]
                    may_force=bool(clients) and all(v.get('exit_observed') is not None for v in clients)
                    if not may_force and worker.get('exit_observed') is None:
                        unresolved.append(attempt+': native client end not proven; worker force forbidden')
                else:
                    may_force=info['complete'] and (all(v!='unproven' for v in info['models'].values())
                        if info['models'] else bool(info.get('empty_basis')))
            except Exception:unresolved.append(attempt+': worker child-accounting error; force forbidden')
            wait_handle(worker,'worker-'+attempt,may_force)
        if self.server:
            wait_handle(self.server,'true-server',True)
            try:self.server['launcher'].wait(timeout=8)
            except Exception:unresolved.append('server launcher exit unresolved; no PID fallback')
        for value in list(self.models.values())+list(self.clients.values())+list(self.workers.values())+([self.server] if self.server else []):
            try:
                if value.get('handle'):value['handle'].close()
            except Exception:unresolved.append('retained handle close failed')
        self.provider.shutdown()
        self.provider.server_close()
        self.cleanup={'actual_workers_waited':sum(v.get('exit_observed') is not None for v in self.workers.values()),
            'actual_clients_waited':sum(v.get('exit_observed') is not None for v in self.clients.values()),
            'actual_servers_waited':int(bool(self.server and self.server.get('exit_observed') is not None)),
            'actual_models_waited':sum(v.get('exit_observed') is not None for v in self.models.values()),
            'model_end_basis':histories,'provider_calls':len(self.captures),'unresolved':unresolved}
        atomic_json(self.root/'cleanup.json',self.cleanup)
        assert not unresolved, 'Owned cleanup unresolved; scratch: '+str(self.root)


def exercise(fixture,args):
    fixture.start()
    common={'model':None,'reasoning':None,'launch_profile':'standard','secret_ref':''}
    package={'id':'selected','name':'Selected CLI fixture','seats':[
        dict(common,id='api',name='Prior API',adapter='openai-compatible',provider='fixture-api',model='prior-model'),
        dict(common,id='cli',name='Selected CLI',adapter='cli',provider='fixture-cli',model='original-cli',reasoning='high'),
        dict(common,id='peer',name='Idle API peer',adapter='openai-compatible',provider='fixture-api',model='unused-peer-model')]}
    fixture.api('/api/preflight/packages',package)
    revision=fixture.api('/api/preflight/seats')['package_revisions']['selected']
    fixture.api('/api/preflight/packages/selected/launch',{'revision':revision})
    initial=fixture.wait(fixture.ready,'all three real worker HTTP/native proofs')
    assert not fixture.captures
    for worker in initial['workers'].values():fixture.keep_worker(worker['attempt'])
    old=initial['workers']['selected/cli']
    record=fixture.wait(lambda:values[0] if len(values:=fixture.client_records())==1 else None,'hidden client self birth')
    pid=record['birth']['pid']
    fixture.keep_client(record,old['attempt'])
    old_bearer=json.loads((fixture.data/'registry.json').read_text('utf-8'))['instances'][old['name']]['token']
    run=fixture.api('/api/sessions/start',{'template_id':TEMPLATE['id'],'channel':'cli-result',
        'cast':{'reviewer':initial['workers']['selected/api']['name'],'editor':old['name']},
        'goal':GOAL,'input_text':fixture.source,'recovery_policy':POLICY})
    fixture.run_id=run['id']
    assert fixture.started.wait(20),'Local prior API body not held'
    prior_run=fixture.session(run['id'])
    invocation=prior_run['active_invocation']
    runtime=fixture.workers[initial['workers']['selected/api']['attempt']]['path']
    fixture.wait(lambda:json.loads((runtime/'invocations'/invocation['dispatch_id']/'birth.json').read_text('utf-8')),'held model self birth')
    fixture.keep_model(runtime,invocation['dispatch_id'])
    fixture.release.set()
    run=fixture.wait(lambda:v if len((v:=fixture.session(fixture.run_id))['admitted_events'])==1
        and v.get('active_invocation') and v['active_invocation']['expected_identity_id']==old['identity_id'] else None,'prior result then CLI')
    fixture.models[invocation['dispatch_id']]['exit_observed']=fixture.models[invocation['dispatch_id']]['handle'].wait(timeout=10)
    fixture.wait(lambda:classify_history(runtime).get('local_ended') is True,'genuine API parent IPC end')
    assert run['admitted_events'][0]['content']==PRIOR and len(fixture.captures)==1
    record=fixture.wait(lambda:v if len((v:=fixture.client_records()[0])['turns'])==1
        and v['turns'][0].get('envelope') else None,'actual CLI brief')
    envelope=record['turns'][0]['envelope']
    assert envelope['source']==fixture.source and any(item.get('text')==PRIOR for item in envelope['prior_results'])
    assert RULE in json.dumps(envelope['rules'])
    atomic_json(fixture.records/'control.json',{'text':SELECTED,'channel':'cli-result','tagged':args.case!='legacy-question'})
    (fixture.records/('post-'+str(pid))).touch()
    record=fixture.wait(lambda:v if (v:=fixture.client_records()[0])['turns'][0].get('message_id') is not None else None,'actual MCP chat_send response')
    message_id=record['turns'][0]['message_id']
    source=fixture.message(message_id)
    assert source['text']==SELECTED and source['type']=='chat'
    original_source=deepcopy(source)
    before=fixture.wait(lambda:v if (v:=fixture.session(fixture.run_id))['state']=='stalled' else None,'live CLI response timeout')
    assert len(before['admitted_events'])==1 and len(record['turns'])==1 and len(fixture.captures)==1
    original_cli=deepcopy(before['active_invocation'])
    current, current_pid=old,pid
    if args.case=='after-retry':
        fixture.api('/api/fixture/drift',{})
        retry={'checkpoint_id':before['turn_recovery']['checkpoint_id'],'attempt_id':original_cli['attempt_id'],
            'request_id':uuid.uuid4().hex,'confirmation':{'confirm':True,'launch_attempt':old['attempt']}}
        fixture.api(f'/api/sessions/{fixture.run_id}/retry',retry)
        fixture.observe_cli_end(old['attempt'],pid)
        new_record=fixture.wait(lambda:next((v for v in fixture.client_records() if v['birth']['pid']!=pid
            and len(v['turns'])==1 and v['turns'][0].get('envelope')),None),'actual new Retry client injection')
        current_pid=new_record['birth']['pid']
        matching=[value for value in fixture.state()['workers'].values()
                  if value['identity_id']==new_record['turns'][0]['envelope']['expected_identity_id']]
        assert len(matching)==1,'Actual new Retry identity must bind exactly one managed attempt'
        current=matching[0]
        fixture.keep_worker(current['attempt'])
        fixture.keep_client(new_record,current['attempt'])
        new_env=new_record['turns'][0]['envelope']
        assert current['identity_id']!=old['identity_id'] and current['attempt']!=old['attempt']
        assert new_env['source']==fixture.source and any(item.get('text')==PRIOR for item in new_env['prior_results'])
        for key in ('run_id','turn_id','input_revision'):assert new_env[key]==envelope[key]
        assert new_record['argv']==record['argv'] and new_record['cwd']==record['cwd']
        atomic_json(fixture.records/'control.json',{'text':SELECTED,'channel':'cli-result','tagged':True,'emit_chat':False})
        (fixture.records/('post-'+str(current_pid))).touch()
        fixture.wait(lambda:any(v['birth']['pid']==current_pid and v['turns'][0].get('chat_skipped') for v in fixture.client_records()),'replacement sends no extra ordinary output')
        fixture.reject(f'/api/sessions/{fixture.run_id}/event',{'brief_id':original_cli['brief_id'],'kind':'final','content':'REVOKED_OLD_OUTPUT'},403,
            {'Authorization':'Bearer '+old_bearer,'Content-Type':'application/json'})
    content_control_baseline=len(fixture.state()['termination_calls'])
    candidate=fixture.api(f'/api/sessions/{fixture.run_id}/cli-message-candidate/{message_id}')
    digest=hashlib.sha256(json.dumps(original_source,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
    assert candidate['snapshot_hash']==digest and candidate['text']==SELECTED and candidate['message_uid']==source['uid']
    assert candidate['attribution']==('operator_attributed' if args.case=='legacy-question' else 'machine_verified')
    decision={key:deepcopy(candidate[key]) for key in ('message_id','message_uid','snapshot_hash','checkpoint')}
    decision.update(request_id=uuid.uuid4().hex,kind='question' if args.case=='legacy-question' else 'final',
                    confirm_operator_attribution=args.case=='legacy-question')
    path=f'/api/sessions/{fixture.run_id}/attach-cli-message'
    if args.case=='legacy-question':fixture.reject(path,dict(decision,confirm_operator_attribution=False))
    if args.stop_before_attach:
        fixture.api(f'/api/sessions/{fixture.run_id}/stop',{})
        fixture.reject(path,decision)
        assert len(fixture.session(fixture.run_id)['admitted_events'])==1 and fixture.message(message_id)==original_source
        return {'case':args.case,'stop_before_attach':True,'provider_calls':len(fixture.captures),'result':'PASS'}
    if args.serve:
        marker=ROOT/'.audit-tmp/ticket14-cli-result-browser-url.txt'
        sentinel=ROOT/'.audit-tmp/ticket14-cli-result-browser-stop.txt'
        sentinel.unlink(missing_ok=True)
        url=fixture.base+'/?channel=cli-result'
        marker.write_text(url,encoding='utf-8')
        print(json.dumps({'stage':'cli_selected_candidate_ready','url':url,'session_id':fixture.run_id,'channel':'cli-result',
            'message_id':message_id,'browser_may_attach':True,'scratch':str(fixture.root),'stop_sentinel':str(sentinel)}),flush=True)
        try:
            fixture.wait(lambda:sentinel.exists(),'bounded browser attachment',600)
            admitted=[v for v in fixture.session(fixture.run_id)['admitted_events'] if v.get('source_message_uid')==source['uid']]
            if admitted:
                intent=deepcopy(admitted[0]['selected_request'])
                assert intent['message_id']==message_id and intent['message_uid']==source['uid'] and intent['snapshot_hash']==digest and intent['kind']=='final'
                decision={key:intent[key] for key in decision}
        finally:
            marker.unlink(missing_ok=True)
            sentinel.unlink(missing_ok=True)
    calls_before=len(fixture.state()['termination_calls'])
    assert calls_before==content_control_baseline,'Candidate/preview/UI attach must not actuate a CLI'
    ack=fixture.api(path,decision)
    assert ack['status']=='admitted' and ack['transport_settled'] is False
    assert len(fixture.state()['termination_calls'])==calls_before,'Attach must never control a CLI process'
    accepted=fixture.session(fixture.run_id)
    event=next(v for v in accepted['admitted_events'] if v['event_id']==ack['accepted_event_id'])
    assert len(accepted['admitted_events'])==2 and event['content']==SELECTED and event['source_identity_id']==old['identity_id']
    assert event['source_attempt_id']==(None if args.case=='legacy-question' else original_cli['attempt_id'])
    assert event['expected_identity_id']==current['identity_id'] and event['provenance']=='operator_selected_cli_result'
    assert event['source_message_uid']==source['uid'] and event['snapshot_hash']==digest
    assert accepted['input_snapshot']==before['input_snapshot'] and accepted['rules_snapshot']==before['rules_snapshot']
    assert accepted['design_snapshot']==before['design_snapshot'] and accepted['capacity_policy']==before['capacity_policy']
    assert fixture.message(message_id)==original_source and len(fixture.captures)==1
    if args.case=='legacy-question':assert accepted['state']=='awaiting_input' and accepted['current_question']['event_id']==event['event_id']
    else:assert accepted['state']=='complete'
    if args.case=='after-retry':
        (fixture.records/('late-'+str(current_pid))).touch()
        late=fixture.wait(lambda:next((v['turns'][0]['late_result'] for v in fixture.client_records()
            if v['birth']['pid']==current_pid and v['turns'][0].get('late_result')),None),'actual current replacement typed rejection')
        assert late['status']=='rejected'
        assert any(v['content']=='ACTUAL_REPLACEMENT_LATE_FINAL' for v in fixture.session(fixture.run_id)['quarantined_events'])
        assert len(fixture.session(fixture.run_id)['admitted_events'])==2
    projected=fixture.message(event['projected_message_id'])
    assert projected['text']==SELECTED and projected['metadata']['routing_suppressed'] is True
    assert fixture.api(path,decision)['accepted_event_id']==event['event_id']
    # Explicit fixture actuation is separate from content recovery and is audited.
    current_bearer=json.loads((fixture.data/'registry.json').read_text('utf-8'))['instances'][current['name']]['token']
    ended=fixture.api('/api/fixture/end-cli',{'identity_id':current['identity_id'],'launch_attempt':current['attempt']})
    assert ended['local_ended'] is True and ended['remote_compute']=='unverified'
    fixture.observe_cli_end(current['attempt'],current_pid)
    settled=fixture.api(path,decision)
    assert settled['transport_settled'] is True and settled['accepted_event_id']==event['event_id']
    assert len(fixture.state()['termination_calls'])==calls_before+1,'Replay must not repeat explicit termination'
    fixture.reject(f'/api/sessions/{fixture.run_id}/event',{'brief_id':event['brief_id'],'kind':'final','content':'REVOKED_CLI_OUTPUT'},403,
        {'Authorization':'Bearer '+current_bearer,'Content-Type':'application/json'})
    final=fixture.session(fixture.run_id)
    assert len(final['admitted_events'])==2 and final['admitted_events'][1]['content']==SELECTED
    peer=fixture.state()['workers']['selected/peer']
    assert peer['identity_id']==initial['workers']['selected/peer']['identity_id'] and peer['readiness']['state']=='ready'
    assert fixture.workers[peer['attempt']]['handle'].poll() is None
    peer_bearer=json.loads((fixture.data/'registry.json').read_text('utf-8'))['instances'][peer['name']]['token']
    fixture.reject(path,decision,403,{'Authorization':'Bearer '+peer_bearer,'Content-Type':'application/json'})
    assert not (fixture.root/'SOURCE_EXECUTED').exists()
    messages=[json.loads(line) for line in (fixture.data/'agentchattr_log.jsonl').read_text('utf-8').splitlines() if line]
    assert sum(value.get('uid')=='session-event:'+event['event_id'] for value in messages)==1
    records=fixture.client_records()
    assert len(records)==(2 if args.case=='after-retry' else 1) and all(len(v['turns'])==1 for v in records)
    return {'case':args.case,'result':'PASS','provider_calls':len(fixture.captures),'cli_injections':sum(len(v['turns']) for v in records),
        'recovered_admissions':1,'attribution':candidate['attribution'],'original_source_identity':True,
        'transport_settled':True,'no_attach_actuation':True,'peer_survived':True}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',choices=('tagged-final','legacy-question','after-retry'),default='tagged-final')
    parser.add_argument('--compile-only',action='store_true')
    parser.add_argument('--stop-before-attach',action='store_true')
    parser.add_argument('--serve',action='store_true')
    args=parser.parse_args()
    assert not args.serve or (args.case=='tagged-final' and not args.stop_before_attach),'Serve scope is tagged-final only'
    assert not args.stop_before_attach or args.case=='tagged-final','Stop scope is tagged-final only'
    compile(server_code(ROOT/'.audit-tmp/compile-cli-selected',19000),'<generated-server>','exec')
    compile((ROOT/'tools/fake_cli_result_recovery.py').read_text('utf-8'),'<dedicated-fake-cli>','exec')
    if args.compile_only:
        print(json.dumps({'result':'COMPILE_ONLY','generated_servers':1,'fake_clients':1}))
        return
    if sys.platform!='win32':raise SystemExit('Actual Windows hidden console required')
    fixture=Fixture(args.case)
    result=None
    try:
        result=exercise(fixture,args)
    finally:
        fixture.close()
        if result is not None:
            result.update(scratch=str(fixture.root),cleanup=fixture.cleanup)
            atomic_json(fixture.root/'result.json',result)
            print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
