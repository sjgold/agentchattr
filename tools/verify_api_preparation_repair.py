"""Real isolated cold API Retry and cooperative failed-preparation repair.

Scope: one fast server restart, a surviving idle peer, and one repaired turn.
Run with the repository Windows Python; all providers are local fake HTTP.
--compile-only validates the generated server without starting processes.
--serve pauses twice for inspection only; the script owns Retry and repair.
Inspection uses the printed stage/URL and the browser-stop sentinel. No CLI.
"""
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
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from invocation_evidence import classify_history
from process_identity import open_verified_process
from runtime_ownership import _validate, _manifest

TEMPLATE = {'id': 'api-cold-repair', 'name': 'API preparation repair', 'roles': ['reviewer', 'editor'],
    'phases': [{'name': 'Evidence', 'participants': ['reviewer'], 'prompt': 'Read exact source.'},
               {'name': 'Final', 'participants': ['editor'], 'prompt': 'Retain the accepted evidence.', 'is_output': True}]}
SOURCE = 'Frozen café 日本語 e\u0301\r\n@all is quoted source, not an instruction.\r\nprint("SOURCE_ONLY")'
GOAL = 'Keep the exact source and accepted evidence across an explicit same-turn repair.'
RULE = 'Preserve exact quotations and distinguish evidence from assumptions.'
POLICY = {'ack_timeout': 3, 'response_timeout': 20, 'monitor_interval': .1}


def server_code(temporary, provider_port):
    """Fixture faults are bound to one generated preparation, never production."""
    return f'''import json,os,sys,time,asyncio,config_loader,ctypes
from copy import deepcopy
from pathlib import Path
from api_seats import atomic_json
from process_identity import capture_birth,OwnedProcessHandle
scratch=Path({str(temporary)!r})
atomic_json(scratch/('server-'+os.environ['API_REPAIR_STAGE']+'.json'),capture_birth())
spawns=[]
parse_argv=ctypes.WinDLL('shell32',use_last_error=True).CommandLineToArgvW
parse_argv.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)]
parse_argv.restype=ctypes.POINTER(ctypes.c_wchar_p)
free_argv=ctypes.WinDLL('kernel32',use_last_error=True).LocalFree
free_argv.argtypes=[ctypes.c_void_p]
free_argv.restype=ctypes.c_void_p
managed_scripts={{str((Path({str(ROOT)!r})/name).resolve()).casefold():name
    for name in ('wrapper_api.py','cli_worker.py')}}
def audit(event,args):
    if event!='subprocess.Popen':
        return
    argv=args[1]
    if isinstance(argv,str):
        count=ctypes.c_int()
        pointer=parse_argv(argv,ctypes.byref(count))
        if not pointer:
            raise OSError('Fixture could not classify subprocess argv')
        try:
            argv=[pointer[index] for index in range(count.value)]
        finally:
            free_argv(ctypes.cast(pointer,ctypes.c_void_p))
    script=None
    for value in argv:
        if Path(str(value)).name.casefold() in ('wrapper_api.py','cli_worker.py'):
            script=managed_scripts.get(str(Path(value).resolve()).casefold())
            if script:
                break
    executable=Path(str(argv[0])).name.casefold() if argv else ''
    category=script or ('git' if executable in ('git','git.exe') else
                       'python' if executable in ('python','python.exe','pythonw.exe') else 'other')
    # No raw argv, working directory, environment or token in diagnostics.
    spawns.append({{'managed':bool(script),'category':category,'has_seat_file':'--seat-file' in argv}})
    atomic_json(scratch/('spawns-'+os.environ['API_REPAIR_STAGE']+'.json'),spawns)
sys.addaudithook(audit)
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['session_recovery']={POLICY!r}
    cfg['agents']={{'fixture-api':{{'type':'api','base_url':'http://127.0.0.1:{provider_port}/v1',
        'system_prompt':'FROZEN_REPAIR_SYSTEM','reasoning_efforts':['high'],'temperature':0.2}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
fault={{'attempt':None,'view':None,'proof':None,'writes':0}}
control={{'cli_termination_calls':0,'native_force_calls':0}}
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','repair-run']
    app.session_store.save_custom_template({TEMPLATE!r})
    if os.environ['API_REPAIR_STAGE']=='first':
        rule=app.rules.propose({RULE!r},'fixture')
        app.rules.activate(rule['id'])
    manager=app.api_seat_manager
    def forbidden_cli(*args,**kwargs):
        control['cli_termination_calls']+=1
        raise AssertionError('API preparation repair must not enter CLI termination')
    manager.terminate_owned=forbidden_cli
    native_terminate=OwnedProcessHandle.terminate
    def traced_terminate(handle):
        control['native_force_calls']+=1
        return native_terminate(handle)
    OwnedProcessHandle.terminate=traced_terminate
    prepare=manager.prepare_retry_context
    def gated(provenance,context_key,**kw):
        view=prepare(provenance,context_key,**kw)
        if fault['attempt'] or kw.get('retry_attempt') is not None:
            return view
        if view.get('launch_attempt')==provenance['launch_attempt']:
            raise AssertionError('fixture requires the original cold worker to be proven ended')
        if view.get('state')!='ready' or not view.get('identity_id'):
            return dict(view,state='starting') if view.get('state')=='ready' else view
        proof=manager.restart_readiness(view['identity_id'],manager.boot_id)
        if proof['state']!='ready' or proof['process_verified'] is not True:
            return dict(view,state='starting')
        with manager.lock:
            attempt=manager.attempts[view['key']]
            runtime=attempt['snapshot'].parent
            assert not list((runtime/'invocations').glob('*')),'first prepared worker must have no model child'
            receipt=json.loads(attempt['receipt'].read_text(encoding='utf-8'))
            assert receipt['identity_id']==view['identity_id']
            receipt.update(state='failed',error='Fixture-only preparation failure before turn binding.',updated_at=time.time())
            atomic_json(attempt['receipt'],receipt)
            attempt.update(state='failed',error=receipt['error'])
            fault.update(attempt=view['launch_attempt'],view=manager._context_view(view['key']),
                         proof=proof,writes=1)
            atomic_json(scratch/'fault.json',fault)
            return deepcopy(fault['view'])
    manager.prepare_retry_context=gated
app.configure=configured
@app.app.get('/api/fixture/state')
def fixture_state():
    manager=app.api_seat_manager
    with manager.lock:
        workers={{}}
        for key,value in manager.attempts.items():
            instance=next((i for i in app.registry.get_all().values() if i['base']==value['base']),None)
            workers[key]={{'attempt':value['id'],'identity_id':instance['identity_id'] if instance else None,
                'name':instance['name'] if instance else None,'process_kind':type(value.get('process')).__name__,
                'process_pid':value['process'].pid if value.get('process') else None,
                'readiness':manager.restart_readiness(instance['identity_id'],manager.boot_id) if instance else None,
                'verified_api_exit':deepcopy(value.get('verified_api_exit'))}}
        return {{'boot_id':manager.boot_id,'server_birth':capture_birth(),
                'spawns':sum(value['managed'] for value in spawns),'workers':workers,
                'auxiliary_spawns':{{category:sum(not v['managed'] and v['category']==category for v in spawns)
                    for category in ('git','python','other')}},'control':deepcopy(control)}}
@app.app.post('/api/fixture/drift')
def fixture_drift():
    app.api_seat_store.providers['fixture-api'].update(system_prompt='EDITED_SYSTEM_MUST_NOT_ENTER',temperature=0.9)
    return {{'edited':True}}
@app.app.post('/api/fixture/capture-old')
async def fixture_capture(request:app.Request):
    body=await request.json()
    run=app.session_store.get(body['session_id'])
    invocation=run['active_invocation']
    principal=next(i for i in app.registry.get_all().values() if i['identity_id']==invocation['expected_identity_id'])
    public=app.registry.resolve_token(principal['token']) if 'token' in principal else principal
    # get_all public records omit tokens; reconstruct public identity only.
    public={{k:deepcopy(v) for k,v in public.items() if k!='token'}}
    envelope=app.session_store.briefs.get(invocation['brief_id'],public)
    assert envelope['expected_identity_id']==public['identity_id']
    atomic_json(scratch/'old-callback.json',{{'principal':public,'envelope':envelope}})
    return {{'captured':True}}
@app.app.post('/api/fixture/late-old')
def fixture_late():
    from turn_events import EventConflict
    old=json.loads((scratch/'old-callback.json').read_text(encoding='utf-8'))
    assert old['envelope']['expected_identity_id']==old['principal']['identity_id']
    try:
        app.session_engine._admit_envelope(old['envelope'],'final','CONTROLLED_OLD_CALLBACK',old['principal'])
    except EventConflict:
        return app.JSONResponse({{'status':'rejected','ingress':'controlled_callback'}},status_code=409)
    raise AssertionError('superseded immutable brief admitted')
import run
run.main()
'''


def main():
    if '--compile-only' in sys.argv:
        compile(server_code(ROOT / '.audit-tmp' / 'compile-only', 19999), '<isolated-server>', 'exec')
        print('Generated isolated server syntax OK; no processes started.')
        return
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Native Windows process proof fixture required.'}))
        return
    captures, guard = [], threading.Lock()
    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            with guard:
                captures.append({'path': self.path, 'payload': payload})
                number = len(captures)
            if number == 2:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b'PRIVATE_FAKE_503_BODY')
                return
            assert number in (1, 3), 'unexpected provider generation'
            content = 'ACCEPTED_EVIDENCE' if number == 1 else 'REPAIRED_FINAL'
            body = json.dumps({'choices': [{'message': {'content': json.dumps({'kind': 'final', 'content': content})}}]}).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='api preparation repair integration ', dir=scratch))
    data = temporary / 'data'
    sockets = [socket.socket() for _ in range(3)]
    for item in sockets:
        item.bind(('127.0.0.1', 0))
    ports = [item.getsockname()[1] for item in sockets]
    for item in sockets:
        item.close()
    base = f'http://127.0.0.1:{ports[0]}'
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(data), AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'))
    code = server_code(temporary, provider.server_port)
    compile(code, '<isolated-server>', 'exec')
    servers, workers = [], {}
    api, result, session_id = None, None, None
    serve = '--serve' in sys.argv
    url_marker = scratch / 'ticket9-api-repair-browser-url.txt'
    stop_marker = scratch / 'ticket9-api-repair-browser-stop.txt'

    def wait_for(check, label, timeout=40):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                value = check()
                if value:
                    return value
            except (OSError, KeyError, ValueError):
                pass
            time.sleep(.05)
        raise AssertionError('deadline waiting for ' + label + '; scratch: ' + str(temporary))

    def retain(birth):
        probe = open_verified_process(birth)
        assert probe['status'] == 'live' and probe['process'] is not None, probe
        return probe['process']

    def retain_worker(attempt):
        if attempt not in workers:
            directory = data / 'api_seat_runtime' / attempt
            birth = json.loads((directory / 'birth.json').read_text('utf-8'))
            workers[attempt] = {'path': directory, 'handle': retain(birth), 'birth': birth, 'observed_exit': None}
        return workers[attempt]

    def start_server(stage):
        with (temporary / ('server-' + stage + '.log')).open('wb') as output:
            launcher = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT,
                env=dict(environment, API_REPAIR_STAGE=stage), stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        item = {'launcher': launcher, 'handle': None}
        servers.append(item)
        birth = wait_for(lambda: json.loads((temporary / ('server-' + stage + '.json')).read_text('utf-8')),
                         'actual server birth', 10)
        item['handle'] = retain(birth)
        def page():
            assert launcher.poll() is None, 'isolated server exited; scratch: ' + str(temporary)
            with urllib.request.urlopen(base + '/preflight', timeout=1) as response:
                return response.read().decode('utf-8-sig')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', wait_for(page, 'HTTP ready')).group(1)
        def request(path, body=None, headers=None):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                headers=headers or {'x-session-token': token, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        return item, request

    def saved(session_id):
        return next(value for value in json.loads((data / 'session_runs.json').read_text('utf-8')) if value['id'] == session_id)

    def reject(path, body, expected=409, headers=None):
        try:
            api(path, body, headers)
        except urllib.error.HTTPError as exc:
            assert exc.code == expected, (path, exc.code)
        else:
            raise AssertionError('expected HTTP rejection: ' + path)

    def ready(key):
        state = api('/api/fixture/state')
        view = state['workers'].get(key)
        return state if view and view['readiness'] and view['readiness']['state'] == 'ready' and view['readiness']['process_verified'] is True else None

    def inspect_pause(stage):
        if not serve:
            return
        stop_marker.unlink(missing_ok=True)
        details = {'stage': stage, 'url': base + '/?channel=repair-run', 'session_id': session_id,
                   'channel': 'repair-run', 'inspection_only': True, 'stop_sentinel': str(stop_marker),
                   'scratch': str(temporary)}
        atomic_json(temporary / ('browser-' + stage + '.json'), details)
        atomic_json(url_marker, details)
        print(json.dumps(details), flush=True)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            assert servers[-1]['handle'].poll() is None, 'server exited during inspection'
            assert all(value['handle'] is None or value['handle'].poll() is None for value in workers.values()), 'live fixture worker exited during inspection'
            if stop_marker.exists():
                stop_marker.unlink()
                url_marker.unlink(missing_ok=True)
                return
            time.sleep(.2)
        raise AssertionError('600s inspection deadline: ' + stage + '; scratch: ' + str(temporary))

    try:
        first, api = start_server('first')
        common = {'adapter': 'openai-compatible', 'provider': 'fixture-api', 'reasoning': 'high',
                  'launch_profile': 'standard', 'secret_ref': ''}
        package = {'id': 'repair-team', 'name': 'Cold API repair fixture', 'seats': [
            dict(common, id='worker', name='Review worker', model='frozen-review-model'),
            dict(common, id='peer', name='Healthy peer', model='unused-peer-model')]}
        api('/api/preflight/packages', package)
        revision = api('/api/preflight/seats')['package_revisions']['repair-team']
        api('/api/preflight/packages/repair-team/launch', {'revision': revision})
        wait_for(lambda: ready('repair-team/worker'), 'original worker actual HTTP proof')
        initial = wait_for(lambda: ready('repair-team/peer'), 'peer actual HTTP proof')
        owner, peer = initial['workers']['repair-team/worker'], initial['workers']['repair-team/peer']
        original = retain_worker(owner['attempt'])
        peer_process = retain_worker(peer['attempt'])
        assert initial['spawns'] == 2 and captures == []
        old_identity = json.loads((data / 'registry.json').read_text('utf-8'))['instances'][owner['name']]
        old_bearer = {'Authorization': 'Bearer ' + old_identity['token'], 'Content-Type': 'application/json'}
        started = api('/api/sessions/start', {'template_id': TEMPLATE['id'], 'channel': 'repair-run',
            'cast': {'reviewer': owner['name'], 'editor': owner['name']}, 'goal': GOAL, 'input_text': SOURCE,
            'recovery_policy': POLICY})
        session_id = started['id']
        stalled = wait_for(lambda: value if (value := saved(session_id))['state'] == 'stalled' else None, 'phase two HTTP503 stall')
        assert stalled['turn_recovery']['reason'] == 'http_error'
        assert [event['content'] for event in stalled['admitted_events']] == ['ACCEPTED_EVIDENCE']
        assert len(captures) == 2
        old = deepcopy(stalled['active_invocation'])
        provenance = stalled['participant_bindings']['editor']['launch_provenance']
        api('/api/fixture/capture-old', {'session_id': session_id})
        assert classify_history(original['path'])['local_ended'] is True
        api('/api/preflight/seats/repair-team/worker/stop', {})
        original['observed_exit'] = original['handle'].wait(timeout=8)
        original['handle'].close()
        original['handle'] = None  # Permit genuine OS absence, never fabricate it.
        assert peer_process['handle'].poll() is None
        immutable_peer = {name: (peer_process['path'] / name).read_bytes() for name in ('config.json', 'birth.json', 'launch.json')}
        before_dirs = {path.name for path in (data / 'api_seat_runtime').iterdir() if path.is_dir()}
        # Every deliberately crashed process is positively retained beforehand.
        crash_at = time.monotonic()
        first['handle'].terminate()
        first['handle'].wait(timeout=8)
        first['launcher'].wait(timeout=8)
        assert peer_process['handle'].poll() is None
        second, api = start_server('second')
        http_ms = (time.monotonic() - crash_at) * 1000
        assert http_ms < 15000, 'fixture exceeded the fast restart window'
        restored = wait_for(lambda: ready('repair-team/peer'), 'original peer adopted with fresh boot proof', 25)
        assert restored['boot_id'] != initial['boot_id'] and restored['spawns'] == 0
        assert restored['workers']['repair-team/peer']['identity_id'] == peer['identity_id']
        assert restored['workers']['repair-team/peer']['process_kind'] == 'OwnedProcessHandle'
        assert restored['workers']['repair-team/peer']['process_pid'] == peer_process['handle'].pid
        interrupted = wait_for(lambda: value if (value := saved(session_id))['state'] == 'interrupted' else None, 'cold run interruption')
        assert interrupted['active_invocation'] == old
        assert interrupted.get('stop_id') is None
        inspect_pause('cold_interrupted_before_retry')
        api('/api/fixture/drift', {})
        edited = deepcopy(package)
        edited['seats'][0].update(model='EDITED_MODEL', reasoning=None)
        api('/api/preflight/packages', edited)
        request = {'checkpoint_id': interrupted['turn_recovery']['checkpoint_id'], 'attempt_id': old['attempt_id'],
                   'request_id': uuid.uuid4().hex}
        api(f'/api/sessions/{session_id}/retry', request)
        failed = wait_for(lambda: value if (value := saved(session_id)).get('pending_retry', {}).get('status') == 'preparation_failed' else None,
                          'actual live prepared API fault before dispatch')
        pending = deepcopy(failed['pending_retry'])
        context = pending['context']
        prepared = retain_worker(context['launch_attempt'])
        assert prepared['handle'].poll() is None
        assert context['identity_id'] != owner['identity_id']
        assert context['state'] == 'failed' and len(captures) == 2
        assert not list((prepared['path'] / 'invocations').glob('*'))
        fault = json.loads((temporary / 'fault.json').read_text('utf-8'))
        assert fault['writes'] == 1 and fault['proof']['process_verified'] is True and fault['proof']['state'] == 'ready'
        api(f'/api/sessions/{session_id}/retry', request)
        replay = saved(session_id)
        assert replay['pending_retry'] == pending
        assert len({path.name for path in (data / 'api_seat_runtime').iterdir() if path.is_dir()} - before_dirs) == 1
        assert api('/api/fixture/state')['spawns'] == 1 and len(captures) == 2
        reject(f'/api/sessions/{session_id}/event', {'brief_id': old['brief_id'], 'kind': 'final', 'content': 'REVOKED_OLD_BEARER'}, expected=403, headers=old_bearer)
        reject('/api/fixture/late-old', {})
        quarantined = saved(session_id)
        assert any(event['content'] == 'CONTROLLED_OLD_CALLBACK' and event['attempt_id'] == old['attempt_id']
                   for event in quarantined['quarantined_events'])
        assert quarantined['admitted_events'] == stalled['admitted_events'] and len(captures) == 2
        inspect_pause('failed_preparation_before_repair')
        repair = {'request_id': request['request_id'], 'preparation_attempt': context['launch_attempt'],
                  'confirmation': {'confirm': True, 'launch_attempt': context['launch_attempt']}}
        api(f'/api/sessions/{session_id}/repair-retry', repair)
        prepared['observed_exit'] = prepared['handle'].wait(timeout=8)
        # A native wait, the exact stop request and zero model history prove
        # actual cooperative exit; no process .terminate() is used for repair.
        assert json.loads((prepared['path'] / 'stop.json').read_text('utf-8'))['attempt'] == context['launch_attempt']
        assert classify_history(prepared['path'])['local_ended'] is True
        complete = wait_for(lambda: value if (value := saved(session_id))['state'] == 'complete' else None, 'repaired typed completion', 45)
        assert [event['content'] for event in complete['admitted_events']] == ['ACCEPTED_EVIDENCE', 'REPAIRED_FINAL']
        final = complete['admitted_events'][-1]
        assert final['attempt_id'] == pending['new_attempt_id'] and final['turn_id'] == old['turn_id']
        assert final['brief_id'] == pending['new_brief_id']
        assert final['attempt_id'] != old['attempt_id']
        assert len(captures) == 3
        binding = complete['participant_bindings']['editor']
        fresh_provenance = binding['launch_provenance']
        assert fresh_provenance['identity_id'] not in (owner['identity_id'], context['identity_id'])
        assert fresh_provenance['effective'] == provenance['effective']
        fresh = retain_worker(fresh_provenance['launch_attempt'])
        wait_for(lambda: ready(fresh_provenance['key']), 'replacement current boot native proof')
        for field in ('input_snapshot', 'input_revision', 'design_snapshot', 'design_revision', 'rules_snapshot', 'rules_revision', 'goal', 'run_id'):
            assert complete[field] == stalled[field], field
        payload = captures[2]['payload']
        assert payload['model'] == 'frozen-review-model' and payload['reasoning_effort'] == 'high'
        assert captures[2]['path'] == '/v1/chat/completions'
        assert 'FROZEN_REPAIR_SYSTEM' in payload['messages'][0]['content']
        data_messages = [json.loads(message['content']) for message in payload['messages'] if message['role'] == 'user']
        source = next(value for value in data_messages if value.get('kind') == 'untrusted_review_source')
        prior = next(value for value in data_messages if value.get('kind') == 'prior_review_results')
        assert source['text'] == SOURCE and source['input_revision'] == complete['input_revision']
        assert [value['text'] for value in prior['results']] == ['ACCEPTED_EVIDENCE']
        assert RULE in json.dumps(payload, ensure_ascii=False) and GOAL in json.dumps(payload, ensure_ascii=False)
        assert 'EDITED_' not in json.dumps(payload) and 'CONTROLLED_OLD_CALLBACK' not in json.dumps(payload)
        api(f'/api/sessions/{session_id}/repair-retry', repair)
        api(f'/api/sessions/{session_id}/retry', request)
        final_state = api('/api/fixture/state')
        assert len(captures) == 3 and final_state['spawns'] == 2
        assert final_state['control'] == {'cli_termination_calls': 0, 'native_force_calls': 0}
        assert len({path.name for path in (data / 'api_seat_runtime').iterdir() if path.is_dir()} - before_dirs) == 2
        assert all((peer_process['path'] / name).read_bytes() == content for name, content in immutable_peer.items())
        assert peer_process['handle'].poll() is None and ready('repair-team/peer')
        assert not (peer_process['path'] / 'invocations').exists()
        result = {'result': 'PASS', 'provider_calls': 3, 'prepared_worker_provider_calls': 0,
            'http_restart_window_ms': round(http_ms, 3), 'cooperative_prepared_exit': prepared['observed_exit'],
            'reserved_generation_preserved': True, 'frozen_original_profile': True, 'peer_survived': True,
            'old_bearer_revoked': True, 'controlled_superseded_callback_rejected': True,
            'scope': 'fast_cold_api_preparation_repair_only', 'scratch': str(temporary)}
    finally:
        if serve:
            url_marker.unlink(missing_ok=True)
            stop_marker.unlink(missing_ok=True)
        unresolved = []
        known_attempts = set(workers)
        excluded_failed = set()
        # Reconcile every private fixture runtime, including overwritten manager
        # history and an attempt that failed before we retained its birth.
        for path in (data / 'api_seat_runtime').glob('*/config.json'):
            attempt = path.parent.name
            known_attempts.add(attempt)
            if attempt in workers:
                continue
            try:
                snapshot = json.loads(path.read_text('utf-8'))
                validated = _validate(path, snapshot)
                assert validated is not None
                manifest = _manifest(path.with_name('launch.json'), validated[0])
                if manifest['spawn_outcome'] == 'failed' and not path.with_name('birth.json').exists():
                    excluded_failed.add(attempt)
                    continue  # Validated synchronous Popen refusal, no worker.
                retain_worker(attempt)
            except (OSError, ValueError, KeyError, AssertionError):
                unresolved.append(attempt + ': worker birth/exit unproven; no process actuation')
        # Endpoints first; dynamically prepared keys are launch keys, not new
        # saved packages. Every fallback is bound to our exact retained birth.
        if api is not None:
            try:
                if session_id is not None:
                    api(f'/api/sessions/{session_id}/stop', {})
                state = api('/api/fixture/state')
                for key, value in state['workers'].items():
                    try:
                        if value['attempt'] not in workers:
                            if value['attempt'] not in excluded_failed and value['attempt'] not in known_attempts:
                                unresolved.append(value['attempt'] + ': unretained manager attempt; preserved')
                            continue
                        directory = data / 'api_seat_runtime' / value['attempt']
                        # Manager stop can escalate after its bounded grace.
                        # Gate it on genuine per-model exit evidence first.
                        atomic_json(directory / 'stop.json', {'attempt': value['attempt']})
                        proof = wait_for(lambda: item if (item := classify_history(directory)).get('local_ended') is True else None,
                                         'cleanup model lifecycle proof', 8)
                        if proof['local_ended'] is True:
                            api('/api/preflight/seats/' + key + '/stop', {})
                    except (OSError, AssertionError):
                        pass
            except OSError:
                pass
        for attempt, value in workers.items():
            handle = value['handle']
            if handle is None:
                continue
            try:
                atomic_json(value['path'] / 'stop.json', {'attempt': attempt})
                value['observed_exit'] = handle.wait(timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                if classify_history(value['path']).get('local_ended') is True:
                    # Only a retained true supervisor, with every model child
                    # proven ended (or protocol1 never-spawned), may be cleaned.
                    handle.terminate()
                    value['observed_exit'] = handle.wait(timeout=8)
                else:
                    unresolved.append(attempt + ': model lifecycle unproven; worker preserved')
            finally:
                handle.close()
        for server in reversed(servers):
            if server['handle'] is not None:
                if server['handle'].poll() is None:
                    server['handle'].terminate()
                server['handle'].wait(timeout=8)
                server['handle'].close()
            try:
                server['launcher'].wait(timeout=8)
            except subprocess.TimeoutExpired:
                unresolved.append('server launcher not observed ended; no PID/tree fallback')
        provider.shutdown()
        provider.server_close()
        assert not unresolved, 'Unresolved exact owned cleanup: ' + '; '.join(unresolved)
        if result:
            assert len(workers) == 4 and known_attempts == set(workers)
            assert all(value['observed_exit'] is not None for value in workers.values())
            assert all(classify_history(value['path'])['local_ended'] is True for value in workers.values())
            result['actual_worker_exits_observed'] = len(workers)
            result['actual_server_exits_observed'] = len(servers)
    if result:
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
