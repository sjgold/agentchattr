"""DRAFT selectable Windows/local-fake participant recovery; compile before review.

--case replace-api|replace-cli|skip|repair-cold selects one isolated scenario.
--serve is permitted only for replace-api/skip: root owns browser actions.
Before a decision the sentinel wait is bounded600s; after clicking Replace/Skip
the reviewer must pulse within30s, inside the normal120s provider deadline.
--compile-only starts no server, provider, model, worker or console.
No live AI/provider, remote-compute, Omarchy or native AI-client acceptance.
"""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
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
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from api_seats import atomic_json
from invocation_evidence import classify_history, classify
from runtime_ownership import _manifest, _validate
from tools import verify_runtime_crash_matrix as resource

POLICY={'ack_timeout':5,'response_timeout':3,'monitor_interval':.1}
GOAL='Preserve approved work while explicitly recovering the missing participant.'
RULE='Missing contributions are missing, never agreement. Keep literal source and authentic prior results.'
PRIOR='AUTHENTIC_PRIOR café\r\naccepted evidence'
SYNTHESIS='AUTHENTIC_SYNTHESIS café\r\naccepted content remains intact.'
REPLACEMENT={'id':'participant-replace','name':'Prior then current and future worker','roles':['reviewer','worker'],
    'phases':[{'name':'Evidence','participants':['reviewer'],'prompt':'Give exact evidence.'},
              {'name':'Review','participants':['worker'],'prompt':'Review accepted evidence.'},
              {'name':'Final','participants':['worker'],'prompt':'Give final synthesis.','is_output':True}]}
SKIP={'id':'participant-skip','name':'Prior then missing worker then genuine synthesis','roles':['reviewer','worker','synthesis'],
    'phases':[{'name':'Evidence','participants':['reviewer'],'prompt':'Give exact evidence.'},
              {'name':'Review','participants':['worker'],'prompt':'Review accepted evidence.'},
              {'name':'Final','participants':['synthesis'],'prompt':'Synthesize with missing-work context.','is_output':True}]}


def server_code(root,provider_port,case,stage):
    fake=str(ROOT/'tools/fake_participant_recovery.py')
    return f'''import os,sys,json,ctypes,config_loader
from copy import deepcopy
from pathlib import Path
from api_seats import atomic_json
from process_identity import capture_birth
root=Path({str(root)!r})
stage={stage!r}
atomic_json(root/('server-birth-'+str(stage)+'.json'),capture_birth())
managed=[]
parse=ctypes.WinDLL('shell32',use_last_error=True).CommandLineToArgvW
parse.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)]
parse.restype=ctypes.POINTER(ctypes.c_wchar_p)
free=ctypes.WinDLL('kernel32',use_last_error=True).LocalFree
free.argtypes=[ctypes.c_void_p]
free.restype=ctypes.c_void_p
scripts={{str((Path({str(ROOT)!r})/name).resolve()).casefold() for name in ('wrapper_api.py','cli_worker.py')}}
fault_fired=False
def audit(event,args):
    global fault_fired
    if event!='subprocess.Popen':return
    argv=args[1]
    if isinstance(argv,str):
        count=ctypes.c_int()
        pointer=parse(argv,ctypes.byref(count))
        if not pointer:raise OSError('Fixture argv classification unavailable')
        try:argv=[pointer[i] for i in range(count.value)]
        finally:free(ctypes.cast(pointer,ctypes.c_void_p))
    if not any(str(Path(str(v)).resolve()).casefold() in scripts for v in argv):return
    assert '--seat-file' in argv,'Managed fixture launch missing private config'
    path=Path(argv[argv.index('--seat-file')+1]).resolve()
    assert path.is_relative_to((root/'data/api_seat_runtime').resolve())
    snapshot=json.loads(path.read_text('utf-8'))
    identity=snapshot['ownership']
    entry={{'launch_attempt':snapshot['attempt'],'launch_key':identity['launch_key'],'failed_before_os_spawn':False}}
    if ({case!r}=='repair-cold' and stage==0 and (root/'arm-failure').exists()
            and snapshot.get('replacement_source') and not fault_fired):
        fault_fired=True
        entry['failed_before_os_spawn']=True
        managed.append(entry)
        atomic_json(root/('managed-'+str(stage)+'.json'),managed)
        atomic_json(root/'fault.json',entry)
        raise OSError('Fixture exact replacement Popen failure before child creation')
    managed.append(entry)
    atomic_json(root/('managed-'+str(stage)+'.json'),managed)
sys.addaudithook(audit)
load=config_loader.load_config
def isolated(path=None):
    cfg=load(path)
    cfg['session_recovery']={POLICY!r}
    cfg['agents']={{'fixture-api':{{'type':'api','base_url':'http://127.0.0.1:{provider_port}/v1',
        'system_prompt':'FROZEN_PARTICIPANT_SYSTEM'}},
        'fixture-cli':{{'command':{sys.executable!r},'cwd':{str(root)!r},'cli_args':[{fake!r}],
        'cli_model_args':['--model','{{model}}'],'cli_reasoning_args':['--reasoning','{{reasoning}}'],
        'reasoning_efforts':['high'],'cli_fresh_context_args':['--context-id','{{context_id}}'],
        'cli_fresh_context_verified':True,'mcp_inject':'env','mcp_env_var':'PARTICIPANT_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
controls=[]
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','participant-run']
    app.session_store.save_custom_template({REPLACEMENT!r})
    app.session_store.save_custom_template({SKIP!r})
    if stage==0:
        rule=app.rules.propose({RULE!r},'fixture')
        app.rules.activate(rule['id'])
    terminate=app.api_seat_manager.terminate_owned
    def measured(identity,attempt):
        controls.append({{'identity_id':identity,'launch_attempt':attempt}})
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
        return {{'boot_id':manager.boot_id,'workers':workers,'controls':deepcopy(controls),'managed':deepcopy(managed)}}
import run
run.main()
'''


class Fixture:
    # Readonly native helpers, no inherited scenario/setup/cleanup behavior.
    wait=resource.Case.wait
    retain=staticmethod(resource.Case.retain)
    session=resource.Case.session
    ledger=resource.Case.ledger

    def __init__(self,case):
        self.case=case
        scratch=ROOT/'.audit-tmp'
        scratch.mkdir(exist_ok=True)
        self.root=Path(tempfile.mkdtemp(prefix='participant '+case+' ',dir=scratch))
        self.data,self.records=self.root/'data',self.root/'records'
        self.records.mkdir()
        self.source='Exact café 日本語 e\u0301\r\n@all is untrusted source\nfrom pathlib import Path\nPath('+repr(str(self.root/'SOURCE_EXECUTED'))+').touch()'
        self.captures,self.capture_lock=[],threading.Lock()
        self.gates,self.servers,self.workers,self.models,self.clients={},[],{},{},{}
        self.run_id,self.api,self.cleanup=None,None,None
        parent=self
        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with parent.capture_lock:
                    index=len(parent.captures)+1
                    parent.captures.append(payload)
                    gate=threading.Event()
                    parent.gates[index]=gate
                content=PRIOR if index==1 else SYNTHESIS if case=='skip' else 'API_CLONE_TYPED_FINAL_'+str(index)
                body=json.dumps({'choices':[{'message':{'content':json.dumps({'kind':'final','content':content})}}]}).encode()
                try:
                    self.send_response(200)
                    self.send_header('Content-Length',str(len(body)))
                    self.end_headers()
                    self.wfile.write(body[:1])
                    self.wfile.flush()
                    if gate.wait(110):
                        self.wfile.write(body[1:])
                        self.wfile.flush()
                except OSError:pass
            def log_message(self,*args):pass
        self.provider=ThreadingHTTPServer(('127.0.0.1',0),Provider)
        self.provider.daemon_threads=True
        threading.Thread(target=self.provider.serve_forever,daemon=True).start()
        sockets=[socket.socket() for _ in range(3)]
        for item in sockets:item.bind(('127.0.0.1',0))
        ports=[item.getsockname()[1] for item in sockets]
        for item in sockets:item.close()
        self.base=f'http://127.0.0.1:{ports[0]}'
        self.env=dict(os.environ,AGENTCHATTR_DATA_DIR=str(self.data),AGENTCHATTR_UPLOAD_DIR=str(self.root/'uploads'),
                      PARTICIPANT_RECORDS=str(self.records))
        self.env.update(dict(zip(('AGENTCHATTR_PORT','AGENTCHATTR_MCP_HTTP_PORT','AGENTCHATTR_MCP_SSE_PORT'),map(str,ports))))

    def start(self):
        stage=len(self.servers)
        code=server_code(self.root,self.provider.server_port,self.case,stage)
        compile(code,'<participant-server>','exec')
        with (self.root/('server-'+str(stage)+'.log')).open('wb') as log:
            launcher=subprocess.Popen([sys.executable,'-u','-c',code],cwd=ROOT,env=self.env,
                                      stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        server={'launcher':launcher,'handle':None,'exit_observed':None}
        self.servers.append(server)
        birth=self.wait(lambda:json.loads((self.root/('server-birth-'+str(stage)+'.json')).read_text('utf-8')),'true server birth',10)
        server['handle']=self.retain(birth)
        def page():
            assert launcher.poll() is None,'Fixture server exited'
            with urllib.request.urlopen(self.base+'/preflight',timeout=2) as reply:return reply.read().decode('utf-8-sig')
        token=re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"',self.wait(page,'HTTP ready')).group(1)
        def api(path,body=None,headers=None):
            request=urllib.request.Request(self.base+path,data=json.dumps(body).encode('utf-8') if body is not None else None,
                headers=headers or {'x-session-token':token,'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=15) as reply:return json.load(reply)
        self.api=api
        def download(path):
            request=urllib.request.Request(self.base+path,headers={'x-session-token':token})
            with urllib.request.urlopen(request,timeout=15) as reply:return reply.read()
        self.download=download

    def state(self):return self.api('/api/fixture/state')
    def current(self):return self.session(self.run_id)

    def keep_worker(self,attempt):
        fresh=attempt not in self.workers
        worker=resource.Case.keep_worker(self,attempt)
        if fresh:
            snapshot=json.loads((worker['path']/'config.json').read_text('utf-8'))
            worker['retained_ownership']=deepcopy(_validate(worker['path']/'config.json',snapshot)[0])
            worker['retained_birth']=json.loads((worker['path']/'birth.json').read_text('utf-8'))
        return worker

    def keep_model(self,runtime,dispatch):
        fresh=dispatch not in self.models
        model=resource.Case.keep_model(self,runtime,dispatch)
        if fresh:
            model['retained_intent']=json.loads((runtime/'invocations'/dispatch/'invocation.json').read_text('utf-8'))
            model['retained_birth']=json.loads((runtime/'invocations'/dispatch/'birth.json').read_text('utf-8'))
        return model

    def ready_initial(self):
        state=self.state()
        keys=('team/api','team/cli','team/peer')
        return state if all(key in state['workers'] and state['workers'][key]['readiness']
            and state['workers'][key]['readiness']['state']=='ready'
            and state['workers'][key]['readiness']['process_verified'] is True for key in keys) else None

    def clients_read(self):
        values=[json.loads(path.read_text('utf-8')) for path in self.records.glob('client-*.json')]
        assert all(not turn.get('error_type') for value in values for turn in value['turns']),'Local fake MCP error'
        return values

    def keep_client(self,record,attempt):
        pid=record['birth']['pid']
        if pid not in self.clients:
            assert record['console_present'] and not record['console_visible']
            self.clients[pid]={'handle':self.retain(record['birth']),'attempt':attempt,'exit_observed':None}
        return pid

    def identity_worker(self,identity):
        matches=[value for value in self.state()['workers'].values() if value['identity_id']==identity]
        assert len(matches)==1,'Exact actual runtime identity required'
        return matches[0]

    def release_api(self,index):
        self.wait(lambda:len(self.captures)>=index,'held fake provider request '+str(index))
        run=self.current()
        invocation=deepcopy(run['active_invocation'])
        owner=self.identity_worker(invocation['expected_identity_id'])
        runtime=self.keep_worker(owner['attempt'])['path']
        self.wait(lambda:json.loads((runtime/'invocations'/invocation['dispatch_id']/'birth.json').read_text('utf-8')),'model self birth')
        model=self.keep_model(runtime,invocation['dispatch_id'])
        self.gates[index].set()
        self.wait(lambda:any(event['attempt_id']==invocation['attempt_id'] for event in self.current()['admitted_events']),'genuine API typed admission')
        model['exit_observed']=model['handle'].wait(timeout=10)
        snapshot=json.loads((runtime/'config.json').read_text('utf-8'))
        scope={'runtime_path':str(runtime),'launch_attempt':snapshot['attempt'],
               'launch_nonce':snapshot['ownership']['launch_nonce'],'dispatch_id':invocation['dispatch_id']}
        self.wait(lambda:classify(scope).get('local_ended') is True,'exact model parent IPC/end')
        return invocation

    def reject(self,path,body=None,headers=None,status=403):
        try:self.api(path,body,headers)
        except urllib.error.HTTPError as exc:
            assert exc.code==status,(exc.code,status)
            return
        raise AssertionError('Expected scoped refusal: '+path)

    def crash(self):
        assert len(self.workers)==3 and len(self.clients)==1 and self.models
        server=self.servers[-1]
        assert server['handle'] is not None
        stamp=time.monotonic()
        server['handle'].terminate()
        server['exit_observed']=server['handle'].wait(timeout=8)
        server['launcher'].wait(timeout=8)
        return stamp

    def close(self):
        """Account for all private intents; never force API model or native client."""
        unresolved,histories=[],{}
        for gate in self.gates.values():gate.set()
        if self.api and self.run_id:
            try:self.api(f'/api/sessions/{self.run_id}/stop',{})
            except Exception:pass
        for path in (self.data/'api_seat_runtime').glob('*/config.json'):
            attempt=path.parent.name
            if attempt in self.workers:continue
            try:
                validated=_validate(path,json.loads(path.read_text('utf-8')))
                assert validated
                manifest=_manifest(path.with_name('launch.json'),validated[0])
                if manifest['spawn_outcome']=='failed' and not path.with_name('birth.json').exists():continue
                self.keep_worker(attempt)
            except Exception:unresolved.append(attempt+': true worker birth/end unproven; preserved')
        for path in self.records.glob('client-*.json'):
            try:
                record=json.loads(path.read_text('utf-8'))
                if record['birth']['pid'] in self.clients:continue
                identity=next((v['envelope']['expected_identity_id'] for v in record['turns'] if v.get('envelope')),None)
                matches=[a for a,w in self.workers.items() if identity and
                    json.loads((w['path']/'config.json').read_text('utf-8'))['seat']['adapter']=='cli' and
                    json.loads((w['path']/'receipt.json').read_text('utf-8')).get('identity_id')==identity]
                if len(matches)!=1:raise ValueError('Client runtime scope unavailable')
                self.keep_client(record,matches[0])
            except Exception:unresolved.append('native client scope/birth unproven; no guessed actuation')
        for attempt,worker in self.workers.items():
            info={'complete':False,'models':{},'adapter':None}
            histories[attempt]=info
            try:
                snapshot=json.loads((worker['path']/'config.json').read_text('utf-8'))
                info['adapter']=snapshot['seat']['adapter']
                directories=list((worker['path']/'invocations').glob('*'))
                info['complete']=True
                if info['adapter']=='cli':continue
                if not directories:
                    proof=classify_history(worker['path'])
                    info['empty_basis']=proof.get('verification_basis') if proof.get('local_ended') is True else None
                    if not info['empty_basis']:unresolved.append(attempt+': empty API history unproven')
                for directory in directories:
                    dispatch=directory.name
                    info['models'][dispatch]='unproven'
                    if dispatch in self.models:continue
                    try:
                        proof=classify({'runtime_path':str(worker['path']),'launch_attempt':attempt,
                            'launch_nonce':snapshot['ownership']['launch_nonce'],'dispatch_id':dispatch})
                        if proof.get('local_ended') is True:
                            info['models'][dispatch]=proof['verification_basis']
                            continue
                    except (OSError,ValueError,KeyError):pass
                    try:self.keep_model(worker['path'],dispatch)
                    except Exception:unresolved.append(dispatch+': API model birth/end unproven; preserved')
            except Exception:unresolved.append(attempt+': incomplete private model inventory')
        def wait(value,label,force=False):
            try:
                if value.get('exit_observed') is None:
                    try:value['exit_observed']=value['handle'].wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        allowed=force() if callable(force) else force
                        if not allowed:
                            unresolved.append(label+': exit unproven; no force cleanup')
                            return
                        value['handle'].terminate()
                        value['exit_observed']=value['handle'].wait(timeout=8)
            except Exception:unresolved.append(label+': exact retained wait unresolved')
        for dispatch,model in self.models.items():
            wait(model,'API-model-'+dispatch,False)
            if model.get('exit_observed') is not None:
                try:
                    histories[model['runtime'].name]['models'][dispatch]='retained_native_model_handle_observed_end'
                except Exception:
                    unresolved.append(dispatch+': retained model end inventory attribution failed')
        # Request child-aware worker shutdown only after local HTTP bodies are
        # released. Parent never terminates a native client/model directly.
        for attempt,worker in self.workers.items():
            try:atomic_json(worker['path']/'stop.json',{'attempt':attempt})
            except Exception:unresolved.append(attempt+': cooperative stop write failed')
        for pid,client in self.clients.items():wait(client,'native-client-'+str(pid),False)
        def fresh_api_guard(attempt,worker):
            """Called only immediately before worker actuation, after wait timeout."""
            try:
                config=worker['path']/'config.json'
                snapshot=json.loads(config.read_text('utf-8'))
                validated=_validate(config,snapshot)
                if not validated or validated[0]!=worker['retained_ownership']:
                    raise ValueError('Retained runtime ownership changed')
                birth=json.loads(config.with_name('birth.json').read_text('utf-8'))
                if birth!=worker['retained_birth'] or birth['pid']!=worker['handle'].pid:
                    raise ValueError('Retained true-worker birth changed')
                manifest=_manifest(config.with_name('launch.json'),validated[0])
                if manifest['spawn_outcome']!='spawned':raise ValueError('Worker spawn not bound')
                # Enumerate again now, never rely on the earlier inventory.
                directories=list((worker['path']/'invocations').glob('*'))
                history=classify_history(worker['path'])
                if not directories:
                    allowed=(history.get('local_ended') is True
                        and history.get('verification_basis')=='protocol_one_no_invocations'
                        and type(snapshot.get('invocation_protocol')) is int and snapshot['invocation_protocol']==1
                        and type(birth.get('invocation_protocol')) is int and birth['invocation_protocol']==1)
                    if not allowed:raise ValueError('Dual-protocol empty history unproven')
                    return True
                if history.get('local_ended') is True:return True
                for directory in directories:
                    scope={'runtime_path':str(worker['path']),'launch_attempt':attempt,
                           'launch_nonce':validated[0]['launch_nonce'],'dispatch_id':directory.name}
                    if classify(scope).get('local_ended') is True:continue
                    model=self.models.get(directory.name)
                    intent=json.loads((directory/'invocation.json').read_text('utf-8'))
                    child_birth=json.loads((directory/'birth.json').read_text('utf-8'))
                    if (not model or model['runtime']!=worker['path']
                            or type(model.get('exit_observed')) is not int
                            or type(model['handle'].poll()) is not int
                            or intent!=model['retained_intent'] or child_birth!=model['retained_birth']
                            or child_birth['pid']!=model['handle'].pid
                            or intent['launch_attempt']!=attempt
                            or intent['launch_nonce']!=validated[0]['launch_nonce']
                            or intent['dispatch_id']!=directory.name):
                        raise ValueError('Fresh model intent has no exact observed-end witness')
                return True
            except Exception:
                unresolved.append(attempt+': fresh API child inventory unproven before fallback; worker preserved')
                return False
        for attempt,worker in self.workers.items():
            may_force=False
            try:
                info=histories[attempt]
                if info['adapter']=='cli':
                    clients=[v for v in self.clients.values() if v['attempt']==attempt]
                    may_force=bool(clients) and all(v.get('exit_observed') is not None for v in clients)
                else:
                    may_force=lambda attempt=attempt,worker=worker:fresh_api_guard(attempt,worker)
            except Exception:unresolved.append(attempt+': child inventory guard failed; worker force forbidden')
            wait(worker,'worker-'+attempt,may_force)
        # Reconcile a final inventory after Stop/waits so an intent appearing
        # during the first pass is accounted for without claiming another native wait.
        for config in (self.data/'api_seat_runtime').glob('*/config.json'):
            attempt=config.parent.name
            try:
                snapshot=json.loads(config.read_text('utf-8'))
                validated=_validate(config,snapshot)
                assert validated
                manifest=_manifest(config.with_name('launch.json'),validated[0])
                if attempt not in self.workers:
                    if manifest['spawn_outcome']=='failed' and not config.with_name('birth.json').exists():continue
                    unresolved.append(attempt+': runtime appeared after retention inventory; preserved')
                    continue
                info=histories[attempt]
                for directory in (config.parent/'invocations').glob('*'):
                    if directory.name in info['models']:continue
                    proof=classify({'runtime_path':str(config.parent),'launch_attempt':attempt,
                        'launch_nonce':snapshot['ownership']['launch_nonce'],'dispatch_id':directory.name})
                    if proof.get('local_ended') is not True:
                        unresolved.append(directory.name+': late model intent end unproven')
                    info['models'][directory.name]=proof.get('verification_basis') if proof.get('local_ended') is True else 'unproven'
            except Exception:unresolved.append(attempt+': final runtime/model inventory failed')
        for server in reversed(self.servers):
            wait(server,'true-server',True)
            try:server['launcher'].wait(timeout=8)
            except Exception:unresolved.append('server launcher exit unresolved; no PID fallback')
        for value in list(self.models.values())+list(self.clients.values())+list(self.workers.values())+self.servers:
            try:
                if value.get('handle'):value['handle'].close()
            except Exception:unresolved.append('retained handle close failed')
        self.provider.shutdown()
        self.provider.server_close()
        self.cleanup={'actual_workers_waited':sum(v.get('exit_observed') is not None for v in self.workers.values()),
            'actual_clients_waited':sum(v.get('exit_observed') is not None for v in self.clients.values()),
            'actual_models_waited':sum(v.get('exit_observed') is not None for v in self.models.values()),
            'actual_servers_waited':sum(v.get('exit_observed') is not None for v in self.servers),
            'provider_calls':len(self.captures),'model_end_basis':histories,'unresolved':unresolved}
        atomic_json(self.root/'cleanup.json',self.cleanup)
        assert not unresolved,'Owned resource cleanup unresolved; scratch: '+str(self.root)


def exercise(fixture,args):
    fixture.start()
    common={'model':None,'reasoning':None,'launch_profile':'standard','secret_ref':''}
    fixture.api('/api/preflight/packages',{'id':'team','name':'Participant fixture','seats':[
        dict(common,id='api',name='Original API profile',adapter='openai-compatible',provider='fixture-api',model='approved-api-model'),
        dict(common,id='cli',name='Original CLI profile',adapter='cli',provider='fixture-cli',model='approved-cli-model',reasoning='high'),
        dict(common,id='peer',name='Idle API peer',adapter='openai-compatible',provider='fixture-api',model='unused-peer-model')]})
    revision=fixture.api('/api/preflight/seats')['package_revisions']['team']
    fixture.api('/api/preflight/packages/team/launch',{'revision':revision})
    initial=fixture.wait(fixture.ready_initial,'three genuine worker HTTP/native proofs')
    assert len(initial['managed'])==3 and not fixture.captures
    for value in initial['workers'].values():fixture.keep_worker(value['attempt'])
    old=initial['workers']['team/cli']
    old_record=fixture.wait(lambda:values[0] if len(values:=fixture.clients_read())==1 else None,'old hidden client birth')
    old_pid=fixture.keep_client(old_record,old['attempt'])
    immutable={path:path.read_bytes() for worker in fixture.workers.values()
               for path in (worker['path']/'config.json',worker['path']/'launch.json',worker['path']/'birth.json')}
    template=SKIP if args.case=='skip' else REPLACEMENT
    cast={'reviewer':initial['workers']['team/api']['name'],'worker':old['name']}
    if args.case=='skip':cast['synthesis']=cast['reviewer']
    started=fixture.api('/api/sessions/start',{'template_id':template['id'],'channel':'participant-run',
        'cast':cast,'goal':GOAL,'input_text':fixture.source,'recovery_policy':POLICY})
    fixture.run_id=started['id']
    fixture.release_api(1)
    old_record=fixture.wait(lambda:next((v for v in fixture.clients_read() if v['birth']['pid']==old_pid
        and len(v['turns'])==1 and v['turns'][0].get('envelope')),None),'actual old CLI review brief')
    before=fixture.wait(lambda:v if (v:=fixture.current())['state']=='stalled' else None,'current CLI timeout checkpoint')
    assert len(before['admitted_events'])==1 and before['admitted_events'][0]['content']==PRIOR
    old_invocation=deepcopy(before['active_invocation'])
    assert old_record['turns'][0]['envelope']['source']==fixture.source
    options=fixture.api(f'/api/sessions/{fixture.run_id}/participant-recovery')
    source=old if args.case=='replace-cli' else initial['workers']['team/api']
    selected=next(value for value in options['choices'] if value['identity_id']==source['identity_id'])
    decision={'request_id':uuid.uuid4().hex,'checkpoint_id':options['checkpoint_id'],'attempt_id':options['attempt_id'],
              'target_identity_id':source['identity_id'],'target_fingerprint':selected['fingerprint'],
              'reason':'Explicit participant recovery, preserve the approved source.'}
    skip={'request_id':uuid.uuid4().hex,'checkpoint_id':options['checkpoint_id'],'attempt_id':options['attempt_id'],
          'reason':'Reviewer contribution is missing, never agreement.','confirm_skip':True}
    registry=json.loads((fixture.data/'registry.json').read_text('utf-8'))['instances']
    bearer={'Authorization':'Bearer '+registry[old['name']]['token'],'Content-Type':'application/json'}
    fixture.reject(f'/api/sessions/{fixture.run_id}/participant-recovery',headers=bearer)
    route=f'/api/sessions/{fixture.run_id}/'+('skip-participant' if args.case=='skip' else 'replace-participant')
    fixture.reject(route,skip if args.case=='skip' else decision,bearer)
    if args.serve:
        marker=ROOT/'.audit-tmp/ticket15-participant-browser-url.txt'
        sentinel=ROOT/'.audit-tmp/ticket15-participant-browser-stop.txt'
        sentinel.unlink(missing_ok=True)
        url=fixture.base+'/?channel=participant-run'
        marker.write_text(url,encoding='utf-8')
        print(json.dumps({'stage':'participant_recovery_ready','case':args.case,'url':url,'session_id':fixture.run_id,
            'channel':'participant-run','target_identity_id':source['identity_id'],'target_name':source['name'],
            'stop_sentinel':str(sentinel),'scratch':str(fixture.root),'post_click_pulse_seconds':30}),flush=True)
        try:
            fixture.wait(lambda:sentinel.exists(),'browser decision600s; pulse within30s after click',600)
            actual=fixture.current()
            if args.case=='skip' and actual.get('skipped_turns'):
                saved=actual['skipped_turns'][-1]['skip_request']
                skip={key:saved[key] for key in skip}
            elif args.case!='skip' and actual.get('replacement_requests'):
                requests=list(actual['replacement_requests'].values())
                assert len(requests)==1
                saved=requests[0]['intent']
                assert saved['target_identity_id']==source['identity_id'] and saved['target_fingerprint']==selected['fingerprint']
                decision={key:saved[key] for key in decision}
        finally:
            marker.unlink(missing_ok=True)
            sentinel.unlink(missing_ok=True)
    restart_ms=None
    if args.case=='repair-cold':
        (fixture.root/'arm-failure').touch()
        fixture.api(route,decision)
        failed=fixture.current()['pending_replacement']
        assert failed['status']=='preparation_failed'
        attempt=failed['context']['launch_attempt']
        directory=fixture.data/'api_seat_runtime'/attempt
        assert json.loads((directory/'launch.json').read_text('utf-8'))['spawn_outcome']=='failed'
        assert not (directory/'birth.json').exists()
        assert json.loads((fixture.root/'fault.json').read_text('utf-8'))['launch_attempt']==attempt
        saved_ids={key:failed[key] for key in ('new_attempt_id','new_brief_id','new_dispatch_id','context_key')}
        crash=fixture.crash()
        fixture.start()
        restart_ms=round((time.monotonic()-crash)*1000,3)
        assert restart_ms<15000
        restored=fixture.wait(fixture.ready_initial,'original workers fresh boot proof after fast restart',25)
        assert restored['boot_id']!=initial['boot_id'] and restored['managed']==[] and len(fixture.captures)==1
        assert fixture.current()['state']=='interrupted'
        fixture.api(route,decision)
        pending=fixture.current()['pending_replacement']
        assert all(pending[key]==value for key,value in saved_ids.items())
        assert pending['context']['launch_attempt']==attempt
        fixture.api(f'/api/sessions/{fixture.run_id}/repair-replacement',
                    {'request_id':decision['request_id'],'preparation_attempt':attempt})
        assert all(fixture.current()['pending_replacement'][key]==value for key,value in saved_ids.items())
    elif args.case=='skip':fixture.api(route,skip)
    else:fixture.api(route,decision)
    # Submit from the original live native client AFTER the durable fence.
    fence=next(value for value in fixture.current()['superseded_attempts'] if value['attempt_id']==old_invocation['attempt_id'])
    assert fence['reason']==('participant_skipped' if args.case=='skip' else 'participant_replacement')
    (fixture.records/('submit-'+str(old_pid)+'-0')).touch()
    old_reply=fixture.wait(lambda:next((v['turns'][0]['response'] for v in fixture.clients_read()
        if v['birth']['pid']==old_pid and v['turns'][0].get('response')),None),'real old typed result rejection')
    assert old_reply['status']=='rejected'
    assert any(v['content']=='OLD_RETIRED_ACTUAL_FINAL' for v in fixture.current()['quarantined_events'])
    assert len(fixture.current()['admitted_events'])==1
    if args.case!='skip':
        def dispatched():
            fixture.api(route,decision)
            run=fixture.current()
            invocation=run.get('active_invocation')
            return run if invocation and invocation['expected_identity_id']!=old['identity_id'] and not run.get('pending_replacement') else None
        bound=fixture.wait(dispatched,'real fresh clone proof and reserved dispatch',35)
        request=bound['replacement_requests'][decision['request_id']]
        actual=bound['active_invocation']
        for name,field in (('new_attempt_id','attempt_id'),('new_brief_id','brief_id'),('new_dispatch_id','dispatch_id')):
            assert request[name]==actual[field]
        assert bound['cast_snapshot']==before['cast_snapshot']
        assert bound['cast']['worker']!=before['cast']['worker']
        assert bound['participant_changes'][-1]['affected_positions']==[{'phase':1,'turn':0},{'phase':2,'turn':0}]
        new=fixture.identity_worker(actual['expected_identity_id'])
        fixture.keep_worker(new['attempt'])
        assert new['identity_id'] not in (old['identity_id'],source['identity_id'])
        if args.case=='replace-cli':
            client=fixture.wait(lambda:next((v for v in fixture.clients_read() if v['context_id'] is not None
                and v['turns'] and v['turns'][0].get('envelope')),None),'fresh hidden CLI context')
            pid=fixture.keep_client(client,new['attempt'])
            snapshot=json.loads((fixture.data/'api_seat_runtime'/new['attempt']/'config.json').read_text('utf-8'))
            assert client['context_id']==snapshot['context_id'] and client['argv'].count('--context-id')==1
            assert client['cwd']==old_record['cwd'] and client['model']==old_record['model'] and client['reasoning']==old_record['reasoning']
            for index in (0,1):
                frame=fixture.wait(lambda:next((v['turns'][index] for v in fixture.clients_read()
                    if v['birth']['pid']==pid and len(v['turns'])>index and v['turns'][index].get('envelope')),None),'clone CLI frame '+str(index))
                assert frame['envelope']['source']==fixture.source
                assert any(v.get('text')==PRIOR for v in frame['envelope']['prior_results'])
                (fixture.records/('submit-'+str(pid)+'-'+str(index))).touch()
                reply=fixture.wait(lambda:next((v['turns'][index].get('response') for v in fixture.clients_read()
                    if v['birth']['pid']==pid and len(v['turns'])>index and v['turns'][index].get('response')),None),'actual clone CLI typed final')
                assert reply['status']=='admitted'
                (fixture.records/('release-'+str(pid)+'-'+str(index))).touch()
                fixture.wait(lambda:any(v['birth']['pid']==pid and v['turns'][index].get('release_reply') for v in fixture.clients_read()),'separate MCP release')
        else:
            fixture.release_api(2)
            fixture.release_api(3)
        before_replay=len(fixture.captures)
        fixture.api(route,decision)
        assert len(fixture.captures)==before_replay
    else:
        fixture.release_api(2)
        payload=json.dumps(fixture.captures[1],ensure_ascii=False)
        assert 'missing_contributions' in payload and skip['reason'] in payload
    final=fixture.wait(lambda:v if (v:=fixture.current())['state']=='complete' else None,'complete accepted output')
    assert final['input_snapshot']==before['input_snapshot'] and final['rules_snapshot']==before['rules_snapshot']
    assert final['design_snapshot']==before['design_snapshot'] and final['capacity_policy']==before['capacity_policy']
    assert final['admitted_events'][0]==before['admitted_events'][0]
    assert final['goal']==GOAL and not (fixture.root/'SOURCE_EXECUTED').exists()
    assert all(path.read_bytes()==value for path,value in immutable.items()),'Source/peer immutable runtime files changed'
    assert fixture.state()['controls']==[],'Replacement/skip implicitly terminated a participant/profile source'
    assert all(worker['handle'].poll() is None for attempt,worker in fixture.workers.items()
               if attempt in {v['attempt'] for v in initial['workers'].values()}),'Original source/peer did not survive'
    messages=[json.loads(line) for line in (fixture.data/'agentchattr_log.jsonl').read_text('utf-8').splitlines() if line]
    if args.case=='skip':
        assert len(final['admitted_events'])==2 and len(final['skipped_turns'])==1
        event=final['admitted_events'][-1]
        assert event['content']==SYNTHESIS
        output=next(value for value in messages if value['id']==final['output_message_id'])
        assert output['text'].startswith(SYNTHESIS) and skip['reason'] in output['text']
        assert output['metadata']['missing_contributions'] and not final.get('missing_output',False)
        notices=[value for value in messages if value['type']=='session_skip']
        assert len(notices)==1 and notices[0]['metadata']['routing_suppressed'] is True
        exported=fixture.download('/api/export')
        with zipfile.ZipFile(io.BytesIO(exported)) as zipped:
            rows=[json.loads(line) for line in zipped.read('messages.jsonl').decode('utf-8').splitlines() if line]
        assert any(v['type']=='session_skip' and v['metadata']['skipped_turn']['reason']==skip['reason'] for v in rows)
    else:assert len(final['admitted_events'])==3 and not final.get('skipped_turns')
    for event in final['admitted_events']:
        assert sum(value.get('uid')=='session-event:'+event['event_id'] for value in messages)==1
    counts=3 if args.case in ('replace-api','repair-cold') else 2 if args.case=='skip' else 1
    assert len(fixture.captures)==counts
    assert not any(payload['model']=='unused-peer-model' for payload in fixture.captures)
    clients=fixture.clients_read()
    assert len(clients)==(2 if args.case=='replace-cli' else 1)
    injections=sum(len(value['turns']) for value in clients)
    assert injections==(3 if args.case=='replace-cli' else 1)
    peer=fixture.state()['workers']['team/peer']
    assert peer['identity_id']==initial['workers']['team/peer']['identity_id'] and peer['readiness']['state']=='ready'
    return {'case':args.case,'result':'PASS','provider_calls':len(fixture.captures),'cli_injections':injections,
        'accepted_results':len(final['admitted_events']),'old_actual_late_output_quarantined':True,
        'source_and_peer_preserved':True,'implicit_termination_calls':0,'http_restart_ms':restart_ms}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',required=True,choices=('replace-api','replace-cli','skip','repair-cold'))
    parser.add_argument('--compile-only',action='store_true')
    parser.add_argument('--serve',action='store_true')
    args=parser.parse_args()
    assert not args.serve or args.case in ('replace-api','skip')
    for case in ('replace-api','replace-cli','skip','repair-cold'):
        for stage in (0,1):compile(server_code(ROOT/'.audit-tmp/compile-participant',19000,case,stage),'<generated-server>','exec')
    compile((ROOT/'tools/fake_participant_recovery.py').read_text('utf-8'),'<fake-native-cli>','exec')
    if args.compile_only:
        print(json.dumps({'result':'COMPILE_ONLY','generated_servers':8,'fake_clients':1}))
        return
    if sys.platform!='win32':raise SystemExit('Actual Windows native fixture required')
    fixture=Fixture(args.case)
    result=None
    try:result=exercise(fixture,args)
    finally:
        fixture.close()
        if result is not None:
            result.update(scratch=str(fixture.root),cleanup=fixture.cleanup)
            atomic_json(fixture.root/'result.json',result)
            print(json.dumps(result),flush=True)


if __name__=='__main__':main()
