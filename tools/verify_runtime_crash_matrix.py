"""Selectable real Windows restart cases with a local fake provider and CLI.

--compile-only checks both fixtures and generated server, starting no process.
--case held-stop|projection|long-down|all selects bounded isolated scenarios.
Example: .venv-windows/Scripts/python.exe tools/verify_runtime_crash_matrix.py --case held-stop
The three cases were verified individually; the combined all mode is unverified.
Scope: held-turn continuity, two crashes with permanent Stop, stable accepted
projection recovery, and one observed >15s outage. Reports native process exits
per resource. Local model/client fixtures establish no remote-compute or native
AI-client guarantee; Linux/Omarchy acceptance is outside this Windows tool.
"""
import argparse
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from invocation_evidence import classify_history, classify
from process_identity import open_verified_process
from runtime_ownership import _manifest, _validate

ONE = {'id': 'crash-one', 'name': 'One frozen turn', 'roles': ['worker'],
       'phases': [{'name': 'Final', 'participants': ['worker'], 'prompt': 'Review exact source.', 'is_output': True}]}
TWO = {'id': 'crash-two', 'name': 'Accepted evidence then held work', 'roles': ['worker'],
       'phases': [{'name': 'Evidence', 'participants': ['worker'], 'prompt': 'Give the first evidence.'},
                  {'name': 'Final', 'participants': ['worker'], 'prompt': 'Use the accepted evidence.', 'is_output': True}]}
SOURCE = 'Exact café 日本語 e\u0301\r\n@all is source data.\r\nprint("SOURCE_NOT_EXECUTED")'
RULE = 'Retain exact source and accepted evidence; identify uncertainty.'
POLICY = {'ack_timeout': 5, 'response_timeout': 120, 'monitor_interval': .2}


def server_code(scratch, provider_port, case):
    fixture = str(ROOT / 'tools' / 'fake_runtime_crash_cli.py')
    return f'''import sys,os,json,ctypes,config_loader
from pathlib import Path
from api_seats import atomic_json
from process_identity import capture_birth
scratch=Path({str(scratch)!r})
stage=int(os.environ['CRASH_MATRIX_STAGE'])
atomic_json(scratch/('server-'+str(stage)+'.json'),capture_birth())
audit_records=[]
parse=ctypes.WinDLL('shell32',use_last_error=True).CommandLineToArgvW
parse.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)]
parse.restype=ctypes.POINTER(ctypes.c_wchar_p)
free=ctypes.WinDLL('kernel32',use_last_error=True).LocalFree
free.argtypes=[ctypes.c_void_p]
free.restype=ctypes.c_void_p
scripts={{str((Path({str(ROOT)!r})/name).resolve()).casefold():name for name in ('wrapper_api.py','cli_worker.py')}}
def audit(event,args):
    if event!='subprocess.Popen':return
    argv=args[1]
    if isinstance(argv,str):
        count=ctypes.c_int()
        pointer=parse(argv,ctypes.byref(count))
        if not pointer:raise OSError('Fixture audit argv classification failed')
        try:argv=[pointer[i] for i in range(count.value)]
        finally:free(ctypes.cast(pointer,ctypes.c_void_p))
    script=None
    for value in argv:
        if Path(str(value)).name.casefold() in ('wrapper_api.py','cli_worker.py'):
            script=scripts.get(str(Path(value).resolve()).casefold())
            if script:break
    executable=Path(str(argv[0])).name.casefold() if argv else ''
    audit_records.append({{'managed':bool(script),'category':script or ('git' if executable in ('git','git.exe') else 'other'),
                          'has_seat_file':'--seat-file' in argv}})
    atomic_json(scratch/('spawns-'+str(stage)+'.json'),audit_records)
sys.addaudithook(audit)
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['session_recovery']={POLICY!r}
    cfg['agents']={{'fixture-api':{{'type':'api','base_url':'http://127.0.0.1:{provider_port}/v1',
        'system_prompt':'FROZEN_CRASH_SYSTEM'}},
        'fixture-cli':{{'command':{sys.executable!r},'cwd':{str(scratch)!r},'cli_args':[{fixture!r}],
        'mcp_inject':'env','mcp_env_var':'CRASH_MATRIX_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','api-run','cli-run','cli-stop','projection']
    app.session_store.save_custom_template({ONE!r})
    app.session_store.save_custom_template({TWO!r})
    if stage==0:
        rule=app.rules.propose({RULE!r},'fixture')
        app.rules.activate(rule['id'])
    if {case!r}=='projection' and stage==0:
        def fail_backlink(session_id,event_id,message_id):
            # _project_session already persisted add_once before this callback.
            run=app.session_store.get(session_id)
            event=next(e for e in run['admitted_events'] if e['event_id']==event_id)
            message=app.store.get_by_id(message_id)
            assert event['projected_message_id'] is None
            assert message['uid']=='session-event:'+event_id and message['text']==event['content']
            atomic_json(scratch/'projection-gap.json',{{'session_id':session_id,'event_id':event_id,'message_id':message_id}})
            raise OSError('Fixture-only first-boot projection backlink unavailable')
        app.session_store.link_event_projection=fail_backlink
app.configure=configured
@app.app.get('/api/fixture/state')
def fixture_state():
    m=app.api_seat_manager
    with m.lock:
        workers={{}}
        for key,a in m.attempts.items():
            owner=next((v for v in app.registry.get_all().values() if v['base']==a.get('base')),None)
            workers[key]={{'attempt':a['id'],'identity_id':owner['identity_id'] if owner else None,
                'name':owner['name'] if owner else None,'process_kind':type(a.get('process')).__name__,
                'process_pid':a['process'].pid if a.get('process') else None,
                'readiness':m.restart_readiness(owner['identity_id'],m.boot_id) if owner else None}}
        return {{'boot_id':m.boot_id,'workers':workers,'spawns':sum(v['managed'] for v in audit_records)}}
@app.app.post('/api/fixture/reconcile')
def fixture_reconcile():
    app.session_engine.reconcile_restart(boot_id=app.api_seat_manager.boot_id)
    app.session_engine.recover_projections()
    return {{'boot_id':app.api_seat_manager.boot_id}}
import run
run.main()
'''


class Case:
    """One parent-owned fake provider and its exact native child resources."""
    def __init__(self, name):
        self.name = name
        scratch = ROOT / '.audit-tmp'
        scratch.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='runtime crash ' + name + ' ', dir=scratch))
        self.data, self.records = self.root / 'data', self.root / 'records'
        self.records.mkdir()
        self.captures, self.capture_lock = [], threading.Lock()
        self.held, self.release, self.handler_ended = threading.Event(), threading.Event(), threading.Event()
        self.servers, self.workers, self.models = [], {}, {}
        self.client = None
        self.api = None
        self.runs = []
        self.initial = None
        self.cleanup_summary = None
        fixture = self

        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with fixture.capture_lock:
                    fixture.captures.append(payload)
                    number = len(fixture.captures)
                delayed = name == 'projection' or number == 2
                content = 'PROJECTED_ACCEPTED' if name == 'projection' else 'PRIOR_ACCEPTED' if number == 1 else 'OLD_UNFENCED_FINAL'
                body = json.dumps({'choices': [{'message': {'content': json.dumps({'kind': 'final', 'content': content})}}]}).encode()
                try:
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    if delayed:
                        self.wfile.write(body[:1])
                        self.wfile.flush()
                        fixture.held.set()
                        if not fixture.release.wait(150):
                            return
                        self.wfile.write(body[1:])
                    else:
                        self.wfile.write(body)
                    self.wfile.flush()
                except OSError:
                    pass
                finally:
                    if delayed:
                        fixture.handler_ended.set()
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
        self.env = os.environ.copy()
        self.env.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, self.ports))))
        self.env.update(AGENTCHATTR_DATA_DIR=str(self.data), AGENTCHATTR_UPLOAD_DIR=str(self.root / 'uploads'),
                        CRASH_MATRIX_RECORDS=str(self.records))

    def wait(self, check, label, timeout=40):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                value = check()
                if value:
                    return value
            except (OSError, KeyError, ValueError):
                pass
            time.sleep(.05)
        raise AssertionError('deadline: ' + label + '; scratch: ' + str(self.root))

    @staticmethod
    def retain(birth):
        probe = open_verified_process(birth)
        assert probe['status'] == 'live' and probe['process'] is not None, probe
        return probe['process']

    def start(self):
        stage = len(self.servers)
        code = server_code(self.root, self.provider.server_port, self.name)
        compile(code, '<isolated-server>', 'exec')
        with (self.root / ('server-' + str(stage) + '.log')).open('wb') as log:
            launcher = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT,
                env=dict(self.env, CRASH_MATRIX_STAGE=str(stage)), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        item = {'launcher': launcher, 'handle': None}
        self.servers.append(item)
        birth = self.wait(lambda: json.loads((self.root / ('server-' + str(stage) + '.json')).read_text('utf-8')), 'actual server birth', 10)
        item['handle'] = self.retain(birth)
        def page():
            assert launcher.poll() is None, 'isolated server exited; scratch: ' + str(self.root)
            with urllib.request.urlopen(self.base + '/preflight', timeout=1) as response:
                return response.read().decode('utf-8-sig')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', self.wait(page, 'HTTP ready')).group(1)
        def api(path, body=None):
            request = urllib.request.Request(self.base + path,
                data=json.dumps(body).encode() if body is not None else None,
                headers={'x-session-token': token, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        self.api = api
        return api('/api/fixture/state')

    def state(self):
        return self.api('/api/fixture/state')

    def boot_ready(self):
        value = self.state()
        expected = {'matrix/api'} if self.name == 'projection' else {'matrix/api', 'matrix/cli'}
        return value if expected <= value['workers'].keys() and all(value['workers'][key]['readiness'] and
            value['workers'][key]['readiness']['state'] == 'ready' and
            value['workers'][key]['readiness']['process_verified'] is True for key in expected) else None

    def keep_worker(self, attempt):
        if attempt not in self.workers:
            directory = self.data / 'api_seat_runtime' / attempt
            snapshot = json.loads((directory / 'config.json').read_text('utf-8'))
            validated = _validate(directory / 'config.json', snapshot)
            assert validated is not None
            birth = json.loads((directory / 'birth.json').read_text('utf-8'))
            assert birth['ownership'] == validated[0] and birth['attempt'] == attempt
            assert Path(birth['worker_root']).resolve() == ROOT.resolve()
            self.workers[attempt] = {'path': directory, 'handle': self.retain(birth),
                                     'exit_observed': None}
        return self.workers[attempt]

    def keep_model(self, runtime, dispatch):
        if dispatch not in self.models:
            snapshot = json.loads((runtime / 'config.json').read_text('utf-8'))
            validated = _validate(runtime / 'config.json', snapshot)
            assert validated is not None
            directory = runtime / 'invocations' / dispatch
            intent = json.loads((directory / 'invocation.json').read_text('utf-8'))
            birth = json.loads((directory / 'birth.json').read_text('utf-8'))
            assert intent['launch_attempt'] == snapshot['attempt'] and intent['dispatch_id'] == dispatch
            assert intent['launch_nonce'] == validated[0]['launch_nonce'] and intent['fingerprint'] == validated[0]['fingerprint']
            assert all(birth[field] == intent[field] for field in
                       ('version', 'launch_attempt', 'launch_nonce', 'dispatch_id', 'invocation_id', 'fingerprint'))
            self.models[dispatch] = {'handle': self.retain(birth), 'runtime': runtime, 'exit_observed': None}
        return self.models[dispatch]

    def client_record(self):
        record = json.loads((self.records / 'client.json').read_text('utf-8'))
        assert all(not turn.get('error_type') for turn in record['turns']), record
        return record

    def setup(self):
        self.start()
        common = {'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        seats = [dict(common, id='api', name='API matrix', adapter='openai-compatible', provider='fixture-api', model='frozen-matrix-model')]
        if self.name != 'projection':
            seats.append(dict(common, id='cli', name='CLI matrix', adapter='cli', provider='fixture-cli'))
        self.api('/api/preflight/packages', {'id': 'matrix', 'name': 'Crash matrix fixture', 'seats': seats})
        revision = self.api('/api/preflight/seats')['package_revisions']['matrix']
        self.api('/api/preflight/packages/matrix/launch', {'revision': revision})
        self.initial = self.wait(self.boot_ready, 'initial fresh HTTP/native proofs')
        assert self.initial['spawns'] == len(seats) and self.captures == []
        for worker in self.initial['workers'].values():
            self.keep_worker(worker['attempt'])
        if self.name != 'projection':
            record = self.wait(self.client_record, 'actual native hidden console self-birth')
            assert record['console_present'] and not record['console_visible']
            self.client = {'handle': self.retain(record['birth']), 'exit_observed': None}
        self.immutable = {path: path.read_bytes() for worker in self.workers.values()
                          for path in (worker['path'] / 'config.json', worker['path'] / 'birth.json', worker['path'] / 'launch.json')}
        self.attempt_dirs = {path.name for path in (self.data / 'api_seat_runtime').iterdir() if path.is_dir()}

    def session(self, session_id):
        return next(value for value in json.loads((self.data / 'session_runs.json').read_text('utf-8')) if value['id'] == session_id)

    def run(self, channel, seat, two=False):
        result = self.api('/api/sessions/start', {'template_id': TWO['id'] if two else ONE['id'], 'channel': channel,
            'cast': {'worker': self.initial['workers']['matrix/' + seat]['name']},
            'goal': 'Keep exact source, accepted results, and original attempt.', 'input_text': SOURCE, 'recovery_policy': POLICY})
        self.runs.append(result['id'])
        return result['id']

    def ledger(self, invocation):
        values = json.loads((self.data / 'queue' / 'ledger.json').read_text('utf-8'))['records']
        return next(value for value in values if value['envelope']['dispatch_id'] == invocation['dispatch_id'])

    def held_turns(self):
        api_id = self.run('api-run', 'api', two=True)
        assert self.held.wait(30), 'API body did not block'
        api_run = self.wait(lambda: value if len((value := self.session(api_id))['admitted_events']) == 1 and
                            value.get('active_invocation') else None, 'accepted prior result and held API invocation')
        assert api_run['admitted_events'][0]['content'] == 'PRIOR_ACCEPTED'
        invocation = api_run['active_invocation']
        runtime = self.workers[self.initial['workers']['matrix/api']['attempt']]['path']
        birth_path = runtime / 'invocations' / invocation['dispatch_id'] / 'birth.json'
        self.wait(lambda: json.loads(birth_path.read_text('utf-8')), 'actual held model self-birth')
        self.keep_model(runtime, invocation['dispatch_id'])
        cli_id = self.run('cli-run', 'cli')
        self.wait(lambda: record if len((record := self.client_record())['turns']) == 1 and record['turns'][0].get('envelope') else None,
                  'actual first CLI injected brief')
        cli_run = self.session(cli_id)
        for value in (api_run, cli_run):
            self.wait(lambda: item if (item := self.ledger(value['active_invocation']))['state'] == 'acknowledged' else None,
                      'actual transport acknowledgement')
        assert len(self.captures) == 2
        serialized = json.dumps(self.captures[1], ensure_ascii=False)
        assert 'PRIOR_ACCEPTED' in serialized and RULE in serialized
        return api_id, cli_id

    def crash(self):
        assert all(value['handle'] is not None for value in self.workers.values())
        if self.name != 'projection':
            assert self.client and self.client['handle'] and self.models
        item = self.servers[-1]
        assert item['handle'] is not None
        stamp = time.monotonic()
        item['handle'].terminate()
        item['handle'].wait(timeout=8)
        item['launcher'].wait(timeout=8)
        return stamp

    def assert_same_inventory(self):
        assert {path.name for path in (self.data / 'api_seat_runtime').iterdir() if path.is_dir()} == self.attempt_dirs
        assert all(path.read_bytes() == content for path, content in self.immutable.items())
        assert self.state()['spawns'] == 0

    def close(self):
        """Account for ALL private spawn intents, then exact retained handles."""
        unresolved = []
        model_inventory = {}
        self.release.set()  # Local provider cleanup only, never cancellation evidence.
        if self.api:
            for session_id in self.runs:
                try:
                    self.api(f'/api/sessions/{session_id}/stop', {})
                except Exception:
                    pass
        for path in (self.data / 'api_seat_runtime').glob('*/config.json'):
            attempt = path.parent.name
            if attempt in self.workers:
                continue
            try:
                validated = _validate(path, json.loads(path.read_text('utf-8')))
                assert validated is not None
                outcome = _manifest(path.with_name('launch.json'), validated[0])['spawn_outcome']
                if outcome == 'failed' and not path.with_name('birth.json').exists():
                    continue
                self.keep_worker(attempt)
            except Exception:
                unresolved.append(attempt + ': worker birth/end unproven; preserved')
        if self.client is None and self.name != 'projection':
            try:
                self.client = {'handle': self.retain(self.client_record()['birth']), 'exit_observed': None}
            except Exception:
                if self.workers:
                    unresolved.append('native CLI client birth/end unproven; no worker force cleanup')
        # Inventory every model journal, not just the one expected held child.
        for worker in self.workers.values():
            inventory = {'complete': False, 'models': {}}
            model_inventory[worker['path'].name] = inventory
            try:
                directories = list((worker['path'] / 'invocations').glob('*'))
            except Exception:
                unresolved.append(worker['path'].name + ': model inventory unreadable')
                continue
            inventory['complete'] = True
            if not directories:
                try:
                    proof = classify_history(worker['path'])
                    if proof.get('local_ended') is True:
                        inventory['empty_basis'] = proof['verification_basis']
                except Exception:
                    unresolved.append(worker['path'].name + ': empty-history proof unreadable')
            for directory in directories:
                dispatch = directory.name
                inventory['models'][dispatch] = {'basis': 'unproven'}
                if dispatch in self.models:
                    continue
                try:
                    snapshot = json.loads((worker['path'] / 'config.json').read_text('utf-8'))
                    proof = classify({'runtime_path': str(worker['path']), 'launch_attempt': snapshot['attempt'],
                                      'launch_nonce': snapshot['ownership']['launch_nonce'], 'dispatch_id': dispatch})
                    if proof['local_ended'] is True:
                        inventory['models'][dispatch]['basis'] = proof['verification_basis']
                        continue
                except Exception:
                    pass
                try:
                    self.keep_model(worker['path'], dispatch)
                except Exception:
                    unresolved.append(dispatch + ': model spawn/end unproven; no force cleanup')
        # Stop through owned endpoints before any fallback. These paths can
        # escalate worker stop, so API model lifecycle must be settled first.
        if self.api:
            try:
                state = self.state()
                for key, item in state['workers'].items():
                    if item['attempt'] not in self.workers:
                        continue
                    directory = self.workers[item['attempt']]['path']
                    if (key.endswith('/cli') and self.client) or (not key.endswith('/cli') and
                            classify_history(directory).get('local_ended') is True):
                        try:
                            self.api('/api/preflight/seats/' + key + '/stop', {})
                        except OSError:
                            pass
            except Exception:
                pass
        for attempt, worker in self.workers.items():
            try:
                atomic_json(worker['path'] / 'stop.json', {'attempt': attempt})
            except OSError:
                unresolved.append(attempt + ': cooperative stop write failed')
        def end_retained(value, label, may_force):
            try:
                try:
                    value['exit_observed'] = value['handle'].wait(timeout=8)
                except subprocess.TimeoutExpired:
                    if not may_force():
                        unresolved.append(label + ': child ownership unresolved; preserved')
                        return
                    value['handle'].terminate()
                    value['exit_observed'] = value['handle'].wait(timeout=8)
            except Exception:
                unresolved.append(label + ': exact retained exit unresolved')
            finally:
                try:
                    value['handle'].close()
                except Exception:
                    unresolved.append(label + ': retained handle close failed')
        for dispatch, model in self.models.items():
            # Exact self-born local fake HTTP child only. No process tree,
            # parent/shim guess, remote-compute claim or unrelated PID.
            end_retained(model, 'model-' + dispatch, lambda: True)
            if model['exit_observed'] is not None:
                inventory = model_inventory.get(model['runtime'].name)
                if inventory and dispatch in inventory['models']:
                    # This is a real native wait witness, not a fabricated
                    # parent exit.json, IPC proof, or remote-compute receipt.
                    inventory['models'][dispatch]['basis'] = 'retained_native_model_handle_observed_end'
        if self.client:
            end_retained(self.client, 'native-client', lambda: True)
        for worker in self.workers.values():
            def may_end_worker():
                snapshot = json.loads((worker['path'] / 'config.json').read_text('utf-8'))
                if snapshot['seat']['adapter'] == 'cli':
                    return self.client and self.client['exit_observed'] is not None
                inventory = model_inventory[worker['path'].name]
                return inventory['complete'] and (all(value['basis'] != 'unproven' for value in inventory['models'].values())
                    if inventory['models'] else bool(inventory.get('empty_basis')))
            end_retained(worker, 'worker-' + worker['path'].name, may_end_worker)
        for server in reversed(self.servers):
            try:
                if server['handle']:
                    if server['handle'].poll() is None:
                        server['handle'].terminate()
                    server['handle'].wait(timeout=8)
                    server['exit_observed'] = True
                else:
                    unresolved.append('true server birth never retained; no shim/PID fallback')
            except Exception:
                unresolved.append('true retained server exit unresolved')
            finally:
                if server['handle']:
                    try:
                        server['handle'].close()
                    except Exception:
                        unresolved.append('retained server handle close failed')
            try:
                server['launcher'].wait(timeout=8)
            except Exception:
                unresolved.append('unverified server launcher preserved')
        self.provider.shutdown()
        self.provider.server_close()
        self.cleanup_summary = {'actual_servers_waited': sum(v.get('exit_observed') is True for v in self.servers),
            'actual_workers_waited': sum(v['exit_observed'] is not None for v in self.workers.values()),
            'retained_models_waited': sum(v['exit_observed'] is not None for v in self.models.values()),
            'provider_calls': len(self.captures), 'api_model_end_basis': model_inventory, 'unresolved': unresolved}
        atomic_json(self.root / 'cleanup.json', self.cleanup_summary)
        assert not unresolved, 'Unresolved owned cleanup: ' + '; '.join(unresolved)


def held_stop(case):
    case.setup()
    api_id, cli_id = case.held_turns()
    before = {sid: deepcopy(case.session(sid)) for sid in (api_id, cli_id)}
    records = {sid: deepcopy(case.ledger(value['active_invocation'])) for sid, value in before.items()}
    crash_at = case.crash()
    case.start()
    http_ms = (time.monotonic() - crash_at) * 1000
    assert http_ms < 15000
    restored = case.wait(case.boot_ready, 'original API+CLI current boot adoption', 25)
    assert restored['boot_id'] != case.initial['boot_id']
    for key, worker in case.initial['workers'].items():
        actual = restored['workers'][key]
        assert (actual['attempt'], actual['identity_id']) == (worker['attempt'], worker['identity_id'])
        assert actual['process_kind'] == 'OwnedProcessHandle'
        assert actual['process_pid'] == case.workers[worker['attempt']]['handle'].pid
    for sid, value in before.items():
        current = case.session(sid)
        assert current['active_invocation'] == value['active_invocation'], 'attempt/timing must not reset'
        assert current['input_snapshot'] == value['input_snapshot'] and current['admitted_events'] == value['admitted_events']
        assert current['recovery_policy'] == value['recovery_policy']
        assert case.ledger(value['active_invocation']) == records[sid], 'envelope/consumer/receipts changed'
    assert all(model['handle'].poll() is None for model in case.models.values())
    assert case.client['handle'].poll() is None and len(case.client_record()['turns']) == 1
    assert len(case.captures) == 2
    case.assert_same_inventory()
    case.release.set()
    (case.records / 'submit-0').touch()
    for sid in (api_id, cli_id):
        case.wait(lambda: value if (value := case.session(sid))['state'] == 'complete' else None, 'old unfenced typed final admitted')
    (case.records / 'release-0').touch()
    case.wait(lambda: case.client_record()['turns'][0].get('release'), 'original CLI separate MCP release')
    assert [event['content'] for event in case.session(api_id)['admitted_events']] == ['PRIOR_ACCEPTED', 'OLD_UNFENCED_FINAL']
    assert case.session(cli_id)['admitted_events'][0]['content'] == 'CLI_CRASH_FINAL_0'
    assert len(case.captures) == 2
    # A new held CLI turn is permanently stopped, then the server crashes again.
    stopped_id = case.run('cli-stop', 'cli')
    case.wait(lambda: record if len((record := case.client_record())['turns']) == 2 and record['turns'][1].get('envelope') else None,
              'second actual CLI injection')
    invocation = deepcopy(case.session(stopped_id)['active_invocation'])
    stopped = case.api(f'/api/sessions/{stopped_id}/stop', {})
    stop_id = stopped['stop_id']
    assert stop_id and stopped['dispatch_eligible'] is False
    case.wait(lambda: value if (value := case.api(f'/api/sessions/{stopped_id}/stop-status'))['state'] == 'unresolved' else None,
              'actual 10s stopped CLI uncertainty', 18)
    case.crash()
    case.start()
    case.wait(case.boot_ready, 'same original workers after second crash', 25)
    permanent = case.session(stopped_id)
    assert permanent['stop_id'] == stop_id and permanent['dispatch_eligible'] is False and permanent['admitted_events'] == []
    (case.records / 'submit-1').touch()
    reply = case.wait(lambda: case.client_record()['turns'][1].get('admission'), 'real old CLI post-Stop MCP rejection')
    assert reply['status'] == 'rejected'
    late = case.session(stopped_id)
    assert any(event['content'] == 'CLI_CRASH_FINAL_1' for event in late['quarantined_events'])
    assert late['admitted_events'] == [] and late['stop_id'] == stop_id
    assert len(case.captures) == 2 and len(case.client_record()['turns']) == 2
    case.assert_same_inventory()
    launch = case.initial['workers']['matrix/cli']['attempt']
    case.api(f'/api/sessions/{stopped_id}/terminate-seat', {'dispatch_id': invocation['dispatch_id'], 'launch_attempt': launch, 'confirm': True})
    case.client['exit_observed'] = case.client['handle'].wait(timeout=8)
    case.workers[launch]['exit_observed'] = case.workers[launch]['handle'].wait(timeout=8)
    case.wait(lambda: value if (value := case.session(stopped_id))['state'] == 'stopped' else None, 'owned termination settled Stop')
    return {'case': 'held-stop', 'fast_http_ms': round(http_ms, 3), 'provider_calls': 2,
            'original_unfenced_admissions': 2, 'cli_injections': 2, 'server_crashes': 2, 'permanent_stop': True}


def projection(case):
    case.setup()
    sid = case.run('projection', 'api')
    assert case.held.wait(30)
    invocation = case.session(sid)['active_invocation']
    runtime = case.workers[case.initial['workers']['matrix/api']['attempt']]['path']
    case.wait(lambda: json.loads((runtime / 'invocations' / invocation['dispatch_id'] / 'birth.json').read_text('utf-8')), 'projection model birth')
    case.keep_model(runtime, invocation['dispatch_id'])
    case.release.set()
    gap = case.wait(lambda: json.loads((case.root / 'projection-gap.json').read_text('utf-8')), 'durable add_once before failed backlink')
    before = case.session(sid)
    assert len(before['admitted_events']) == 1 and before['admitted_events'][0]['projected_message_id'] is None
    assert before['admitted_events'][0]['event_id'] == gap['event_id']
    uid = 'session-event:' + gap['event_id']
    def messages():
        return [json.loads(line) for line in (case.data / 'agentchattr_log.jsonl').read_text('utf-8').splitlines() if line.strip()]
    original = next(value for value in messages() if value.get('uid') == uid)
    assert original['text'] == 'PROJECTED_ACCEPTED' and original['id'] == gap['message_id']
    case.crash()
    case.start()
    case.wait(case.boot_ready, 'projection worker current boot proof', 25)
    repaired = case.wait(lambda: value if (value := case.session(sid))['admitted_events'][0]['projected_message_id'] is not None else None,
                         'accepted projection recovery')
    for _ in range(3):
        case.api('/api/fixture/reconcile', {})
    assert len(repaired['admitted_events']) == 1
    assert repaired['admitted_events'][0]['event_id'] == gap['event_id']
    assert repaired['admitted_events'][0]['projected_message_id'] == original['id']
    assert [value for value in messages() if value.get('uid') == uid] == [original]
    assert len(case.captures) == 1
    case.assert_same_inventory()
    return {'case': 'projection', 'provider_calls': 1, 'accepted_events': 1, 'stable_projected_messages': 1}


def long_down(case):
    case.setup()
    api_id, cli_id = case.held_turns()
    before = {sid: deepcopy(case.session(sid)) for sid in (api_id, cli_id)}
    records = {sid: deepcopy(case.ledger(value['active_invocation'])) for sid, value in before.items()}
    stamp = case.crash()
    # No restart until a genuine >15s downtime, independent of exit outcomes.
    while time.monotonic() - stamp < 18:
        time.sleep(.2)
    deadline = time.monotonic() + 22
    outcomes = {}
    resources = [('worker-' + attempt, value) for attempt, value in case.workers.items()]
    resources += [('model-' + dispatch, value) for dispatch, value in case.models.items()]
    resources += [('native-client', case.client)]
    for label, value in resources:
        try:
            code = value['handle'].wait(timeout=max(.01, deadline - time.monotonic()))
            value['exit_observed'] = code
            outcomes[label] = 'observed_exited'
        except subprocess.TimeoutExpired:
            outcomes[label] = 'still_live_unresolved'
    assert not case.release.is_set(), 'fake provider progress must not stand in for local cancellation'
    downtime = time.monotonic() - stamp
    case.start()
    cold = case.state()
    assert cold['boot_id'] != case.initial['boot_id'] and cold['spawns'] == 0
    for _ in range(3):
        case.api('/api/fixture/reconcile', {})
    for sid, old in before.items():
        current = case.session(sid)
        assert current['active_invocation'] == old['active_invocation']
        assert current['input_snapshot'] == old['input_snapshot'] and current['admitted_events'] == old['admitted_events']
        assert not current.get('stop_id')
        record = case.ledger(old['active_invocation'])
        assert record['envelope'] == records[sid]['envelope'] and record['consumer_id'] == records[sid]['consumer_id']
        assert current['state'] == 'interrupted' and current['dispatch_eligible'] is False
    assert len(case.captures) == 2 and len(case.client_record()['turns']) == 1
    case.assert_same_inventory()
    return {'case': 'long-down', 'downtime_ms': round(downtime * 1000, 3), 'provider_calls': 2,
            'automatic_worker_spawns': 0, 'observations': outcomes,
            'end_proof_scope': 'actual_exits_reported_individually_live_resources_remain_unresolved'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('held-stop', 'projection', 'long-down', 'all'))
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    if args.compile_only:
        for name in ('held-stop', 'projection', 'long-down'):
            compile(server_code(ROOT / '.audit-tmp' / 'compile-crash-only', 19999, name), '<server-' + name + '>', 'exec')
        compile((ROOT / 'tools/fake_runtime_crash_cli.py').read_text('utf-8'), '<fake-cli>', 'exec')
        print('Three generated servers and dedicated fake CLI syntax OK; no processes started.')
        return
    if not args.case:
        parser.error('select --case; execution requires coordinator readiness')
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Actual Windows native process and console proof required.'}))
        return
    names = ('held-stop', 'projection', 'long-down') if args.case == 'all' else (args.case,)
    functions = {'held-stop': held_stop, 'projection': projection, 'long-down': long_down}
    for name in names:
        case = Case(name)
        result = None
        try:
            result = functions[name](case)
        finally:
            case.close()
        if result:
            result.update(result='PASS', scratch=str(case.root), cleanup=case.cleanup_summary)
            atomic_json(case.root / 'result.json', result)
            print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
