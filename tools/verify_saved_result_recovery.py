"""DRAFT selectable real-worker saved-answer recovery, local fake provider only.

--compile-only starts no process. Select --case cold-final|cold-question|lost-ack.
Optional --stop-before-delivery checks pending Stop refusal in a cold case.
--serve is cold-final only: browser may Deliver, script then posts idempotently.
Requires coordinator review/readiness before execution. No live AI/Omarchy.
"""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from api_seats import atomic_json
from invocation_evidence import classify, classify_history
from result_outbox import ResultOutbox
from review_brief import BriefStore
from runtime_ownership import _manifest,_validate
from tools import verify_result_outbox as base


def server_code(scratch,provider_port,case):
    return f'''import os,sys,json,ctypes,config_loader
from pathlib import Path
from api_seats import atomic_json
from process_identity import capture_birth
from turn_events import EventConflict,event_id
scratch=Path({str(scratch)!r})
stage=int(os.environ['SAVED_RECOVERY_STAGE'])
atomic_json(scratch/('server-'+str(stage)+'.json'),capture_birth())
spawns=[]
parse=ctypes.WinDLL('shell32',use_last_error=True).CommandLineToArgvW
parse.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)]
parse.restype=ctypes.POINTER(ctypes.c_wchar_p)
free=ctypes.WinDLL('kernel32',use_last_error=True).LocalFree
free.argtypes=[ctypes.c_void_p]
scripts={{str((Path({str(ROOT)!r})/name).resolve()).casefold() for name in ('wrapper_api.py','cli_worker.py')}}
def audit(event,args):
    if event!='subprocess.Popen':return
    argv=args[1]
    if isinstance(argv,str):
        count=ctypes.c_int()
        pointer=parse(argv,ctypes.byref(count))
        if not pointer:raise OSError('Fixture spawn classification failed')
        try:argv=[pointer[i] for i in range(count.value)]
        finally:free(ctypes.cast(pointer,ctypes.c_void_p))
    managed=any(Path(str(v)).name.casefold() in ('wrapper_api.py','cli_worker.py') and
        str(Path(v).resolve()).casefold() in scripts for v in argv)
    spawns.append({{'managed':managed,'has_seat_file':'--seat-file' in argv}})
    atomic_json(scratch/('spawns-'+str(stage)+'.json'),spawns)
sys.addaudithook(audit)
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['session_recovery']={{'ack_timeout':5,'response_timeout':120,'monitor_interval':.2}}
    cfg['agents']={{'fixture-api':{{'type':'api','base_url':'http://127.0.0.1:{provider_port}/v1',
        'system_prompt':'FROZEN_SAVED_RECOVERY_SYSTEM'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
observations=[]
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','outbox-run']
    app.session_store.save_custom_template({base.TEMPLATE!r})
    if stage==0:
        rule=app.rules.propose({base.RULE!r},'fixture')
        app.rules.activate(rule['id'])
        admit=app.session_engine.admit_event
        def response_fault(brief_id,kind,content,instance,**kw):
            from result_outbox import ResultOutbox
            envelope=app.session_store.briefs.get(brief_id,instance)
            if envelope['phase_index']!=1:return admit(brief_id,kind,content,instance,**kw)
            owner=app.api_seat_manager.result_owner(instance,kw['event_id'])
            runtime=app.api_seat_store.path.parent/'api_seat_runtime'/owner['launch_attempt']
            record=ResultOutbox(runtime).get(owner['dispatch_id'])
            payload=app.session_store.briefs.verify_saved_result(record)
            assert payload['kind']==kind and payload['content']==content and payload['event_id']==kw['event_id']
            row={{'number':len(observations)+1,'dispatch_id':owner['dispatch_id'],
                'saved_before_post':True,'real_admit_completed':False,'duplicate_conflict':False}}
            observations.append(row)
            atomic_json(scratch/'posts.json',observations)
            if {case!r}!='lost-ack':
                if len(observations)>3:raise AssertionError('Unexpected fourth saved-result post')
                raise OSError('Fixture-only pending result post outage')
            try:
                result=admit(brief_id,kind,content,instance,**kw)
            except EventConflict:
                row['duplicate_conflict']=True
                atomic_json(scratch/'posts.json',observations)
                raise
            row['real_admit_completed']=True
            run=app.session_store.get(envelope['session_id'])
            accepted=next(e for e in run['admitted_events'] if e['event_id']==kw['event_id'])
            assert accepted['projected_message_id'] is not None
            row['projected_message_id']=accepted['projected_message_id']
            atomic_json(scratch/'posts.json',observations)
            if len(observations)==1:raise OSError('Fixture response lost AFTER real admission and projection')
            return result
        app.session_engine.admit_event=response_fault
app.configure=configured
@app.app.get('/api/fixture/state')
def fixture_state():
    m=app.api_seat_manager
    with m.lock:
        workers={{}}
        for key,a in m.attempts.items():
            i=next((v for v in app.registry.get_all().values() if v['base']==a.get('base')),None)
            workers[key]={{'attempt':a['id'],'identity_id':i['identity_id'] if i else None,
                'name':i['name'] if i else None,'process_kind':type(a.get('process')).__name__,
                'process_pid':a['process'].pid if a.get('process') else None,
                'readiness':m.restart_readiness(i['identity_id'],m.boot_id) if i else None}}
        return {{'boot_id':m.boot_id,'workers':workers,'managed_spawns':sum(v['managed'] for v in spawns)}}
@app.app.get('/api/fixture/exit-proof/{{result_id}}')
def fixture_proof(result_id:str):
    from result_outbox import ResultOutbox
    event_id(result_id)
    paths=list((app.api_seat_store.path.parent/'api_seat_runtime').glob('*/outbox/'+result_id+'.json'))
    assert len(paths)==1
    record=ResultOutbox(paths[0].parent.parent).get(result_id)
    payload=app.session_store.briefs.verify_saved_result(record)
    return app.api_seat_manager.saved_result_exit_proof(payload)
import run
run.main()
'''


class RecoveryFixture(base.WorkerFixture):
    def __init__(self,case):
        # Resource-only constructor: no inherited scenario/check is executed.
        super().__init__()
        self.case=case
        fixture=self
        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with fixture.lock:
                    fixture.captures.append(payload)
                    number=len(fixture.captures)
                assert number in (1,2),'unexpected extra provider generation'
                answer={'kind':'question' if case=='cold-question' and number==2 else 'final',
                        'content':base.PRIOR if number==1 else base.ANSWER}
                body=json.dumps({'model':'fixture-confirmed','choices':[{'message':{'content':json.dumps(answer,ensure_ascii=False)}}]}).encode('utf-8')
                try:
                    self.send_response(200)
                    self.send_header('Content-Length',str(len(body)))
                    self.end_headers()
                    if number==2:
                        self.wfile.write(body[:1]);self.wfile.flush()
                        fixture.held.set()
                        if not fixture.release.wait(120):return
                        self.wfile.write(body[1:])
                    else:self.wfile.write(body)
                    self.wfile.flush()
                except OSError:pass
                finally:
                    if number==2:fixture.provider_done.set()
            def log_message(self,*args):pass
        # Replace only this owned local server's handler before any worker starts.
        self.provider.RequestHandlerClass=Provider

    def start(self):
        stage=len(self.servers)
        env=os.environ.copy()
        env.update(dict(zip(('AGENTCHATTR_PORT','AGENTCHATTR_MCP_HTTP_PORT','AGENTCHATTR_MCP_SSE_PORT'),map(str,self.ports))))
        env.update(AGENTCHATTR_DATA_DIR=str(self.data),AGENTCHATTR_UPLOAD_DIR=str(self.root/'uploads'),SAVED_RECOVERY_STAGE=str(stage))
        code=server_code(self.root,self.provider.server_port,self.case)
        compile(code,'<saved-recovery-server>','exec')
        with (self.root/('server-'+str(stage)+'.log')).open('wb') as output:
            launcher=subprocess.Popen([sys.executable,'-u','-c',code],cwd=ROOT,env=env,
                stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
        item={'launcher':launcher,'handle':None,'exit_observed':False}
        self.servers.append(item)
        birth=self.wait(lambda:json.loads((self.root/('server-'+str(stage)+'.json')).read_text('utf-8')),'actual server birth',10)
        item['handle']=self.retain(birth)
        def page():
            assert launcher.poll() is None,'isolated server exited; scratch: '+str(self.root)
            with urllib.request.urlopen(self.base+'/preflight',timeout=1) as response:return response.read().decode('utf-8-sig')
        token=re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"',self.wait(page,'HTTP ready')).group(1)
        def api(path,body=None,headers=None):
            request=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
                headers=headers or {'x-session-token':token,'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)
        self.api=api
        return self.state()

    def reject(self,path,body,status,headers=None):
        try:self.api(path,body,headers)
        except urllib.error.HTTPError as exc:
            assert exc.code==status,(path,exc.code)
        else:raise AssertionError('Expected HTTP'+str(status)+': '+path)

    def close(self):
        """All exact private spawn intents, including previously waited/closed worker."""
        unresolved=[]
        bases={}
        self.release.set()
        if self.api:
            for sid in self.runs:
                try:self.api(f'/api/sessions/{sid}/stop',{})
                except Exception:pass
        for path in (self.data/'api_seat_runtime').glob('*/config.json'):
            try:
                snapshot=json.loads(path.read_text('utf-8'))
                checked=_validate(path,snapshot)
                assert checked is not None
                if path.parent.name not in self.workers:
                    outcome=_manifest(path.with_name('launch.json'),checked[0])['spawn_outcome']
                    if outcome=='failed' and not path.with_name('birth.json').exists():continue
                    self.keep_worker(path.parent.name)
            except Exception:unresolved.append(path.parent.name+': unretained worker birth/end')
        for attempt,worker in self.workers.items():
            inventory={'complete':False,'models':{}}
            bases[attempt]=inventory
            try:directories=list((worker['path']/'invocations').glob('*'))
            except Exception:
                unresolved.append(attempt+': unreadable invocation inventory');continue
            inventory['complete']=True
            if not directories:
                try:
                    proof=classify_history(worker['path'])
                    if proof.get('local_ended') is True:inventory['empty_basis']=proof['verification_basis']
                except Exception:unresolved.append(attempt+': empty-history proof unreadable')
            for directory in directories:
                dispatch=directory.name
                inventory['models'][dispatch]={'basis':'unproven'}
                if dispatch in self.models:continue
                try:
                    snapshot=json.loads((worker['path']/'config.json').read_text('utf-8'))
                    proof=classify({'runtime_path':str(worker['path']),'launch_attempt':attempt,
                        'launch_nonce':snapshot['ownership']['launch_nonce'],'dispatch_id':dispatch})
                    if proof['local_ended'] is True:
                        inventory['models'][dispatch]['basis']=proof['verification_basis'];continue
                    self.keep_model(worker['path'],dispatch)
                except Exception:unresolved.append(dispatch+': model intent/end unproven')
        if self.api:
            try:
                for key,row in self.state()['workers'].items():
                    if row['attempt'] in self.workers and classify_history(self.workers[row['attempt']]['path']).get('local_ended') is True:
                        try:self.api('/api/preflight/seats/'+key+'/stop',{})
                        except Exception:pass
            except Exception:pass
        for attempt,worker in self.workers.items():
            if worker['handle'] is None and worker.get('exit_observed') is not None:continue
            try:atomic_json(worker['path']/'stop.json',{'attempt':attempt})
            except Exception:unresolved.append(attempt+': cooperative stop write failed')
        def end(value,label,may_force):
            if value['handle'] is None:
                if value.get('exit_observed') is None:unresolved.append(label+': no retained end witness')
                return
            try:
                try:value['exit_observed']=value['handle'].wait(timeout=8)
                except subprocess.TimeoutExpired:
                    if not may_force():
                        unresolved.append(label+': child end unproven; preserved');return
                    value['handle'].terminate();value['exit_observed']=value['handle'].wait(timeout=8)
            except Exception:unresolved.append(label+': actual exit unresolved')
            finally:
                try:value['handle'].close()
                except Exception:unresolved.append(label+': handle close failed')
                value['handle']=None
        for dispatch,model in self.models.items():
            end(model,'model-'+dispatch,lambda:True)
            if model['exit_observed'] is not None and dispatch in bases.get(model['runtime'].name,{}).get('models',{}):
                bases[model['runtime'].name]['models'][dispatch]['basis']='retained_native_model_handle_observed_end'
        for attempt,worker in self.workers.items():
            def may_end():
                proof=bases[attempt]
                return proof['complete'] and (all(v['basis']!='unproven' for v in proof['models'].values())
                    if proof['models'] else bool(proof.get('empty_basis')))
            end(worker,'worker-'+attempt,may_end)
        for server in reversed(self.servers):
            try:
                if server['handle'] is None:
                    if not server.get('exit_observed'):unresolved.append('server birth/end unproven')
                else:
                    if server['handle'].poll() is None:server['handle'].terminate()
                    server['handle'].wait(timeout=8);server['exit_observed']=True
            except Exception:unresolved.append('true server exit unresolved')
            finally:
                if server['handle']:
                    server['handle'].close();server['handle']=None
            try:server['launcher'].wait(timeout=8)
            except Exception:unresolved.append('launcher exit unresolved; no PID/tree fallback')
        self.provider.shutdown();self.provider.server_close()
        self.cleanup_summary={'actual_servers_waited':sum(v['exit_observed'] is True for v in self.servers),
            'actual_workers_waited':sum(v.get('exit_observed') is not None for v in self.workers.values()),
            'retained_models_waited':sum(v.get('exit_observed') is not None for v in self.models.values()),
            'provider_calls':len(self.captures),'model_end_basis':bases,'unresolved':unresolved}
        atomic_json(self.root/'cleanup.json',self.cleanup_summary)
        assert not unresolved,'Unresolved exact-owned cleanup: '+'; '.join(unresolved)


def exercise(f,serve=False,stop_before=False):
    f.start()
    common={'adapter':'openai-compatible','provider':'fixture-api','reasoning':None,'launch_profile':'standard','secret_ref':''}
    f.api('/api/preflight/packages',{'id':'outbox','name':'Saved answer recovery','seats':[
        dict(common,id='api',name='API reviewer',model='frozen-recovery-model'),
        dict(common,id='peer',name='Idle peer',model='unused-peer-model')]})
    revision=f.api('/api/preflight/seats')['package_revisions']['outbox']
    f.api('/api/preflight/packages/outbox/launch',{'revision':revision})
    initial=f.wait(f.ready,'initial actual native/HTTP worker proof')
    for row in initial['workers'].values():f.keep_worker(row['attempt'])
    owner,peer=initial['workers']['outbox/api'],initial['workers']['outbox/peer']
    original=f.workers[owner['attempt']]
    peer_worker=f.workers[peer['attempt']]
    identities=json.loads((f.data/'registry.json').read_text('utf-8'))['instances']
    old_headers={'Authorization':'Bearer '+identities[owner['name']]['token'],'Content-Type':'application/json'}
    peer_headers={'Authorization':'Bearer '+identities[peer['name']]['token'],'Content-Type':'application/json'}
    run=f.api('/api/sessions/start',{'template_id':base.TEMPLATE['id'],'channel':'outbox-run',
        'cast':{'reviewer':owner['name']},'goal':'Recover this exact saved answer without another generation.','input_text':base.SOURCE})
    sid=run['id'];f.runs.append(sid)
    assert f.held.wait(30)
    before=f.session(sid)
    assert [e['content'] for e in before['admitted_events']]==[base.PRIOR]
    invocation=deepcopy(before['active_invocation']);rid=invocation['dispatch_id']
    f.wait(lambda:json.loads((original['path']/'invocations'/rid/'birth.json').read_text('utf-8')),'actual held model birth')
    model=f.keep_model(original['path'],rid)
    assert model['handle'].poll() is None and all(v['handle'].poll() is None for v in f.workers.values())
    f.release.set()
    wanted=2 if f.case=='lost-ack' else 3
    posts=f.wait(lambda:v if len(v:=json.loads((f.root/'posts.json').read_text('utf-8')))==wanted else None,'bounded actual post attempts')
    box=ResultOutbox(original['path'])
    saved=box.get(rid);saved_bytes=(original['path']/'outbox'/(rid+'.json')).read_bytes()
    payload=BriefStore(f.data).verify_saved_result(saved)
    assert payload['content']==base.ANSWER and all(row['dispatch_id']==rid and row['saved_before_post'] is True for row in posts)
    assert payload['kind']==('question' if f.case=='cold-question' else 'final')
    assert len(f.captures)==2
    if f.case=='lost-ack':
        ack=f.wait(lambda:box.get_ack(rid),'actual worker duplicate409 local ACK')
        current=f.session(sid)
        assert posts[0]['real_admit_completed'] is True and posts[1]['duplicate_conflict'] is True
        assert [e['content'] for e in current['admitted_events']]==[base.PRIOR,base.ANSWER]
        assert ack['accepted_event_id']==rid
        messages=[json.loads(line) for line in (f.data/'agentchattr_log.jsonl').read_text('utf-8').splitlines() if line.strip()]
        assert len([v for v in messages if v.get('uid')=='session-event:'+rid])==1
        assert f.state()['managed_spawns']==2
        return {'case':f.case,'provider_calls':2,'second_posts':2,'second_admissions':1,'second_projections':1,'acknowledged':True}
    assert box.get_ack(rid) is None and len(f.session(sid)['admitted_events'])==1
    model['exit_observed']=model['handle'].wait(timeout=8)
    assert classify_history(original['path'])['local_ended'] is True
    f.api('/api/preflight/seats/outbox/api/stop',{})
    original['exit_observed']=original['handle'].wait(timeout=8)
    atomic_json(f.root/'observed-original-exit.json',{'attempt':owner['attempt'],'actual_worker_exit':original['exit_observed'],
        'actual_model_exit':model['exit_observed'],'basis':'retained_native_handles_waited'})
    original['handle'].close();original['handle']=None
    assert peer_worker['handle'].poll() is None
    immutable={p:p.read_bytes() for worker in f.workers.values() for p in
        (worker['path']/'config.json',worker['path']/'birth.json',worker['path']/'launch.json')}
    directories={p.name for p in (f.data/'api_seat_runtime').iterdir() if p.is_dir()}
    crash=time.monotonic()
    server=f.servers[-1]
    server['handle'].terminate();server['handle'].wait(timeout=8);server['exit_observed']=True
    server['launcher'].wait(timeout=8)
    f.start()
    http_ms=(time.monotonic()-crash)*1000
    assert http_ms<15000
    def peer_ready():
        state=f.state();row=state['workers'].get('outbox/peer')
        return state if row and row['readiness'] and row['readiness']['state']=='ready' and row['readiness']['process_verified'] is True else None
    cold=f.wait(peer_ready,'original surviving peer fresh boot proof',25)
    assert cold['boot_id']!=initial['boot_id'] and cold['managed_spawns']==0
    assert cold['workers']['outbox/peer']['identity_id']==peer['identity_id']
    assert cold['workers']['outbox/peer']['process_kind']=='OwnedProcessHandle'
    assert cold['workers']['outbox/peer']['process_pid']==peer_worker['handle'].pid
    assert all(p.read_bytes()==value for p,value in immutable.items())
    assert {p.name for p in (f.data/'api_seat_runtime').iterdir() if p.is_dir()}==directories
    previews=f.api(f'/api/sessions/{sid}/saved-results')['saved_results']
    preview=next(v for v in previews if v['result_id']==rid)
    assert preview['state']=='saved' and preview['can_deliver'] is True and preview['content']==base.ANSWER
    assert f.session(sid)['admitted_events']==before['admitted_events'] and box.get_ack(rid) is None
    for key in ('active_invocation','input_snapshot','input_revision','design_revision','rules_snapshot','rules_revision','goal'):
        assert f.session(sid)[key]==before[key]
    assert len(f.captures)==2
    private=json.loads((f.data/'review_briefs'/(invocation['brief_id']+'.json')).read_text('utf-8'))['_result_seal']
    for forbidden in (private['seal_secret'],saved['seal'],payload['launch_nonce'],payload['fingerprint'],str(original['path'])):
        assert forbidden not in json.dumps(previews,ensure_ascii=False)
    for headers in (old_headers,peer_headers):
        f.reject(f'/api/sessions/{sid}/saved-results',None,403,headers)
        f.reject(f'/api/sessions/{sid}/deliver-saved-result',{'result_id':rid},403,headers)
    proof=f.api('/api/fixture/exit-proof/'+rid)
    assert proof['local_ended'] is True and proof['dispatch_id']==rid and proof['seat_identity_id']==owner['identity_id']
    if stop_before:
        stopped=f.api(f'/api/sessions/{sid}/stop',{})
        assert stopped['stop_id'] and stopped['dispatch_eligible'] is False
        f.reject(f'/api/sessions/{sid}/deliver-saved-result',{'result_id':rid},409)
        assert len(f.session(sid)['admitted_events'])==1 and box.get_ack(rid) is None
        assert (original['path']/'outbox'/(rid+'.json')).read_bytes()==saved_bytes
        return {'case':f.case,'pending_stopped_result_rejected':True,'provider_calls':2,'second_posts':3,'second_admissions':0}
    if serve:
        marker=ROOT/'.audit-tmp/ticket13-saved-result-browser-url.txt'
        sentinel=ROOT/'.audit-tmp/ticket13-saved-result-browser-stop.txt'
        sentinel.unlink(missing_ok=True)
        ready={'stage':'cold_saved_answer_ready','url':f.base+'/?channel=outbox-run','session_id':sid,'channel':'outbox-run',
            'result_id':rid,'browser_may_deliver':True,'stop_sentinel':str(sentinel),'scratch':str(f.root)}
        atomic_json(marker,ready);atomic_json(f.root/'browser-ready.json',ready);print(json.dumps(ready),flush=True)
        deadline=time.monotonic()+600
        try:
            while not sentinel.exists():
                assert time.monotonic()<deadline,'600s saved-answer browser deadline'
                assert f.servers[-1]['handle'].poll() is None and peer_worker['handle'].poll() is None
                time.sleep(.2)
        finally:marker.unlink(missing_ok=True);sentinel.unlink(missing_ok=True)
    response=f.api(f'/api/sessions/{sid}/deliver-saved-result',{'result_id':rid})
    assert response['accepted_event_id']==rid and response['transport_settled'] is True
    current=f.session(sid)
    assert [e['content'] for e in current['admitted_events']]==[base.PRIOR,base.ANSWER]
    event=current['admitted_events'][-1]
    assert event['provenance']=='verified_saved_api_result' and event['submitted_by']=='operator'
    assert event['expected_identity_id']==owner['identity_id'] and event['result_launch_attempt']==owner['attempt']
    assert current['state']==('awaiting_input' if f.case=='cold-question' else 'complete')
    if f.case=='cold-question':assert current['current_question']['event_id']==rid
    record=next(v for v in json.loads((f.data/'queue/ledger.json').read_text('utf-8'))['records'] if v['envelope']['dispatch_id']==rid)
    assert record['state']=='settled_recovered' and record['recovery']['source']=='result_recovery'
    assert record['recovery']['verification_basis']==proof['verification_basis']
    ack_bytes=(original['path']/'outbox_ack'/(rid+'.json')).read_bytes()
    for _ in range(2):
        assert f.api(f'/api/sessions/{sid}/deliver-saved-result',{'result_id':rid})['accepted_event_id']==rid
    assert (original['path']/'outbox_ack'/(rid+'.json')).read_bytes()==ack_bytes
    assert len(f.session(sid)['admitted_events'])==2 and len(f.captures)==2
    messages=[json.loads(line) for line in (f.data/'agentchattr_log.jsonl').read_text('utf-8').splitlines() if line.strip()]
    assert len([v for v in messages if v.get('uid')=='session-event:'+rid])==1
    assert (original['path']/'outbox'/(rid+'.json')).read_bytes()==saved_bytes
    assert f.state()['managed_spawns']==0 and peer_worker['handle'].poll() is None
    return {'case':f.case,'http_restart_ms':round(http_ms,3),'provider_calls':2,'second_posts':3,
        'second_admissions':1,'second_projections':1,'original_identity_attributed':True,'transport_settled':True,
        'actual_worker_exit':original['exit_observed'],'actual_model_exit':model['exit_observed'],'peer_survived':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=('cold-final','cold-question','lost-ack'))
    parser.add_argument('--compile-only',action='store_true')
    parser.add_argument('--stop-before-delivery',action='store_true')
    parser.add_argument('--serve',action='store_true')
    args=parser.parse_args()
    if args.compile_only:
        for case in ('cold-final','cold-question','lost-ack'):
            compile(server_code(ROOT/'.audit-tmp/compile-saved-only',19999,case),'<'+case+'-server>','exec')
        print('Three saved-recovery server variants syntax OK; no processes started.');return
    if not args.case:parser.error('Select one bounded case after coordinator readiness')
    if args.serve and (args.case!='cold-final' or args.stop_before_delivery):parser.error('--serve requires cold-final without Stop')
    if args.stop_before_delivery and args.case=='lost-ack':parser.error('Stop variant requires a pending cold result')
    if sys.platform!='win32':print(json.dumps({'result':'SKIP','reason':'Native Windows retained handle proof required.'}));return
    fixture=RecoveryFixture(args.case)
    result=None
    try:result=exercise(fixture,args.serve,args.stop_before_delivery)
    finally:fixture.close()
    if result:
        result.update(result='PASS',scratch=str(fixture.root),cleanup=fixture.cleanup_summary)
        atomic_json(fixture.root/'result.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
