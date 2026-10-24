"""DRAFT Windows/local-fake channel acceptance. No execution approval is implied.

--case native|browser; --compile-only compiles three server variants, guard
bootstrap and one client without constructing a fixture or opening resources.
Native is bounded to300s, browser1200s, cleanup90s. Browser actions belong to
the reviewer, never injected by this tool. No live AI/provider/Omarchy claims.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from process_identity import open_verified_process
from runtime_ownership import _manifest, _validate
from tools import verify_runtime_crash_matrix as resources

SOURCE = 'Exact channel café 日本語 e\u0301\r\n@all remains source data.'
TEMPLATE = {'id': 'channel-human', 'name': 'Retained human review', 'roles': ['reader'],
    'phases': [{'name': 'Read', 'participants': ['reader'], 'prompt': 'Read the frozen source.', 'is_output': True}]}
TRUSTED_BOOTSTRAP = {
    'pyvenv.cfg': '3f9424aac986e633206a9b93f480cd5ea22a0e4ab550a49c5494ea18e99bb45b',
    'Lib/site-packages/pywin32.pth': 'e7cd73df98b91c407dfd96d1f4dd18b7f9a60f29902b92cf5ece79b6eb637b81',
    'Lib/site-packages/win32/lib/pywin32_bootstrap.py': 'fd31f27bc85a6b9c974670838b6eefafb32991be4a9f840f96a4f5524df3b3c3'}


def trusted_bootstrap_manifest():
    """Fixed local bootstrap boundary, not a Python/stdlib integrity attestation."""
    venv = ROOT / '.venv-windows'
    assert Path(sys.executable).resolve() == (venv / 'Scripts/python.exe').resolve()
    assert sorted(path.name for path in (venv / 'Lib/site-packages').glob('*.pth')) == ['pywin32.pth']
    rows = {}
    for name, expected in TRUSTED_BOOTSTRAP.items():
        raw = (venv / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == expected, 'Trusted local bootstrap manifest changed: ' + name
        rows[name] = {'size': len(raw), 'sha256': digest}
    assert 'include-system-site-packages = false' in (venv / 'pyvenv.cfg').read_text(encoding='utf-8').lower()
    return {'files': rows, 'interpreter': sys.executable, 'venv': sys.prefix, 'stdlib_root': sys.base_prefix,
            'outside_guard': 'trusted interpreter/stdlib/native DLL/site initialization bounded by local manifest only',
            'not_claimed': 'no safety/integrity attestation of Python, stdlib or pre-hook global access'}


def repository_head():
    git = ROOT / '.git'
    if git.is_file():
        pointer = git.read_text(encoding='utf-8').strip()
        assert pointer.startswith('gitdir: ')
        git = (ROOT / pointer[8:]).resolve()
    head = (git / 'HEAD').read_text(encoding='ascii').strip()
    if re.fullmatch('[a-f0-9]{40}', head):
        return head
    assert head.startswith('ref: ')
    reference = head[5:]
    for directory in (git, (git / (git / 'commondir').read_text(encoding='utf-8').strip()).resolve()
                      if (git / 'commondir').exists() else git):
        path = directory / reference
        if path.exists():
            return path.read_text(encoding='ascii').strip()
        packed = directory / 'packed-refs'
        if packed.exists():
            for line in packed.read_text(encoding='ascii').splitlines():
                if line.endswith(' ' + reference):
                    return line.split()[0]
    raise ValueError('Owned repository HEAD could not be resolved')


def guard_bootstrap():
    return ("import os\nif os.environ.get('CHANNEL_FIXTURE_ROOT'):\n try:\n"
            "  from tools.channel_guard import install_guard\n  install_guard('python')\n"
            " except BaseException:\n  os._exit(91)\n")


def server_code(root, case, stage):
    return f'''import os,sys,json,time,asyncio,hashlib
from pathlib import Path
root=Path({str(root)!r})
from tools.channel_guard import install_guard
install_guard('server')
from api_seats import atomic_json
from process_identity import capture_birth
atomic_json(root/'server-{stage}-birth.json',capture_birth())
import config_loader
load=config_loader.load_config
def isolated(path=None):
    cfg=load(path)
    cfg['server']['host']='127.0.0.1'
    cfg['agents']={{}} if {case!r}=='browser' else {{'channel-cli':{{
        'command':{sys.executable!r},'cwd':str(root),'cli_args':[{str(ROOT/'tools/fake_channel_client.py')!r}],
        'mcp_inject':'env','mcp_env_var':'CHANNEL_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
from fastapi import HTTPException
from channel_lifecycle import ChannelUnavailable
from store import MessageStore
from jobs import JobStore
from schedules import ScheduleStore
from summaries import SummaryStore
from session_store import SessionStore
from session_engine import SessionEngine
from registry import RuntimeRegistry
from agents import AgentTrigger
data=root/'data'
channel='manage-run' if {case!r}=='browser' else 'lifecycle-run'
seeded={{}}
def seed(messages,jobs,schedules,summaries,sessions,registry):
    uploaded=root/'uploads'/'0123456789abcdef0123456789abcdef.txt'
    uploaded.parent.mkdir(parents=True,exist_ok=True)
    uploaded.write_bytes({b'OWNED_UPLOAD_BYTES\r\n'!r})
    row=messages.add('fixture',{'Exact history café\r\nsource'!r},channel=channel,
        attachments=[{{'name':'exact source.txt','url':'/uploads/'+uploaded.name}}])
    messages.add_todo(row['id'])
    peer=messages.add('fixture','PEER_HISTORY_UNCHANGED',channel='peer')
    job=jobs.create('Retained job','job',channel,'fixture',status='open')
    jobs.add_message(job['id'],'fixture',{'Retained conversation café\r\nline'!r})
    schedule=schedules.create('Inactive retained schedule',['missing-fixture'],channel=channel,interval_seconds=600)
    schedules.toggle(schedule['id'])
    summaries.write(channel,{'Exact retained summary\r\nsecond line'!r},'fixture',message_id=row['id'])
    sessions.save_custom_template({TEMPLATE!r})
    engine=SessionEngine(sessions,messages,AgentTrigger(registry,str(data)),registry)
    run=engine.start_session({TEMPLATE['id']!r},channel,{{'reader':'human-reader'}},'fixture',input_text={SOURCE!r})
    engine.human_result(run['id'],run['active_invocation']['brief_id'],'Genuine human fixture journal.',submitted_by='human-reader')
    engine.stop_session(run['id']);engine.reconcile_stops()
    return {{'message_id':row['id'],'peer_message_id':peer['id'],'job_id':job['id'],'schedule_id':schedule['id'],
        'session_id':run['id'],'upload':uploaded.name}}
if {case!r}=='browser' and {stage}==0:
    assert not (data/'channel_lifecycle.json').exists()
    data.mkdir(parents=True,exist_ok=True)
    atomic_json(data/'settings.json',{{'channels':['general','manage-run','peer','archived','retired','pending-run'],'username':'fixture-operator'}})
    seeded=seed(MessageStore(str(data/'agentchattr_log.jsonl')),JobStore(str(data/'jobs.json')),
        ScheduleStore(str(data/'schedules.json')),SummaryStore(str(data/'summaries.json')),
        SessionStore(str(data/'session_runs.json')),RuntimeRegistry(str(data)))
    extra=MessageStore(str(data/'agentchattr_log.jsonl'))
    extra.add('fixture','Literal data-only <script> + space',channel='odd <tag> + name')
    atomic_json(root/'seed.json',seeded)
    seed_files={{str(path.relative_to(data)):{{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size}}
        for path in data.rglob('*') if path.is_file() and (path.name in ('agentchattr_log.jsonl','jobs.json','schedules.json','summaries.json','session_runs.json','todos.json','custom_templates.json') or path.parent.name=='review_briefs')}}
    atomic_json(root/'pre-lifecycle-files.json',seed_files)
configure=app.configure
fault={{'mode':None,'consumed':False}}
audit=json.loads((root/'fixture-actions.json').read_text(encoding='utf-8')) if (root/'fixture-actions.json').exists() else []
owned_originals={{}}
def save_audit():atomic_json(root/'fixture-actions.json',audit)
actual_channel_observer=app._on_channel_change
def observed_channel_event(event):
    audit.append({{'kind':'actual_channel_observer','event':event,'at':time.time()}});save_audit()
    actual_channel_observer(event)
app._on_channel_change=observed_channel_event
def configured(*args,**kwargs):
    global seeded
    configure(*args,**kwargs)
    if {case!r}=='native':
        for name in ('lifecycle-run','peer'):
            revision=app.channel_service.catalog.snapshot()['revision']
            app.channel_service.catalog.create(name,expected_revision=revision)
        app.channel_service._project(app.channel_service.catalog.snapshot())
        seeded=seed(app.store,app.jobs,app.schedules,app.summaries,app.session_store,app.registry)
        atomic_json(root/'seed.json',seeded)
    elif {stage}==0:
        seeded=json.loads((root/'seed.json').read_text(encoding='utf-8'))
        original=json.loads((root/'pre-lifecycle-files.json').read_text(encoding='utf-8'))
        after={{name:{{'sha256':hashlib.sha256((data/name).read_bytes()).hexdigest(),'size':(data/name).stat().st_size}} for name in original}}
        atomic_json(root/'pre-lifecycle-after-configure.json',after)
        assert after==original,'Retained rows changed during initial lifecycle discovery'
        for name in ('archived',):
            value=app.channel_service.catalog.snapshot()
            app.channel_service.catalog.set_state(name,'archived',expected_revision=value['revision'])
        preview=app.channel_service.preview('delete','retired')
        app.channel_service.apply('delete','retired',request_id='1'*32,confirmation='retired',preview_token=preview['preview_token'])
        app.registry.seed({{'browser-registry-only':{{'label':'NONNATIVE queued fixture'}}}})
        registry_only=app.registry.register('browser-registry-only')
        queued=app.agents.queue.enqueue(registry_only,{{'channel':'manage-run','text':'QUEUED_ONLY_NONNATIVE'}})
        seeded['registry_only_dispatch']=queued['envelope']['dispatch_id']
        atomic_json(root/'seed.json',seeded)
    else:seeded=json.loads((root/'seed.json').read_text(encoding='utf-8'))
    app.channel_service.artifacts.probe()
app.configure=configured
def authorized(request):
    if (not request.client or request.client.host!='127.0.0.1'
            or request.headers.get('x-session-token')!=app.session_token
            or request.headers.get('x-fixture-nonce')!=os.environ['CHANNEL_FIXTURE_NONCE']
            or request.scope.get('query_string',b'')!=b''):
        raise HTTPException(403,'Fixture operator access required')
@app.app.get('/api/fixture/state')
def state(request:app.Request):
    authorized(request)
    workers={{}}
    with app.api_seat_manager.lock:
        for key,attempt in app.api_seat_manager.attempts.items():
            owner=next((v for v in app.registry.get_all().values() if v['base']==attempt.get('base')),None)
            workers[key]={{'attempt':attempt['id'],'name':owner['name'] if owner else None,
                'identity_id':owner['identity_id'] if owner else None,
                'readiness':app.api_seat_manager.restart_readiness(owner['identity_id'],app.api_seat_manager.boot_id) if owner else None}}
    return {{'workers':workers,'seed':seeded,'fault':fault,'audit':audit,'stage':{stage}}}
@app.app.post('/api/fixture/control')
async def control(request:app.Request):
    authorized(request)
    body=await request.json()
    allowed={{'hold_jobs','hold_schedules','hold_catalog','restore','refuse409','refuse503','timeout','pending_delete'}}
    if set(body)!={{'nonce','action'}} or body['nonce']!=os.environ['CHANNEL_FIXTURE_NONCE'] or body['action'] not in allowed:
        raise HTTPException(400,'Invalid fixed fixture action')
    action=body['action']
    audit.append({{'action':action,'at':time.time(),'fixture_controlled':True}})
    if action.startswith('hold_'):
        key=action[5:]
        path={{'jobs':data/'jobs.json','schedules':data/'schedules.json','catalog':data/'channel_lifecycle.json'}}[key]
        owned_originals.setdefault(key,path.read_bytes())
        path.write_text('{{broken fixture state',encoding='utf-8')
    elif action=='restore':
        for key,value in owned_originals.items():
            path={{'jobs':data/'jobs.json','schedules':data/'schedules.json','catalog':data/'channel_lifecycle.json'}}[key]
            path.write_bytes(value)
        if 'jobs' in owned_originals:
            app.jobs=JobStore(str(data/'jobs.json'),migrate_sort_orders=False,hold_unreadable=True)
            app.jobs.bind_channel_policy(app._channels);app.channel_service.jobs=app.jobs
            app.jobs.on_change(app._on_job_change)
        if 'schedules' in owned_originals:
            app.schedules=ScheduleStore(str(data/'schedules.json'),configured=True)
            app.schedules.bind_channel_policy(app._channels);app.channel_service.schedules=app.schedules
            app.schedules.on_change(app._on_schedule_change)
        owned_originals.clear()
    elif action=='pending_delete':
        service=app.channel_service
        preview=service.preview('delete','pending-run')
        original=service.catalog.complete_step
        def fail_mark(request_id,step):raise OSError('Fixture lost step acknowledgement')
        service.catalog.complete_step=fail_mark
        try:
            try:service.apply('delete','pending-run',request_id='2'*32,confirmation='pending-run',preview_token=preview['preview_token'])
            except ChannelUnavailable:pass
        finally:service.catalog.complete_step=original
        intent=service.catalog.snapshot()['intent']
        assert intent['request_id']=='2'*32 and intent['op']=='delete' and intent['old']=='pending-run'
        assert intent['completed_steps']==[]
    else:fault.update(mode=action,consumed=False)
    atomic_json(root/'fixture-actions.json',audit)
    return {{'ok':True,'fixture_controlled':True,'action':action}}
route=next(r for r in app.app.routes if getattr(r,'path',None)=='/api/channels/apply')
actual_apply=route.dependant.call
async def observed_apply(request:app.Request):
    mode=fault['mode']
    body=await request.json()
    if mode and not fault['consumed'] and body.get('op')=='rename' and body.get('channel')=='manage-run':
        fault['consumed']=True
        audit.append({{'action':'management-response-fault','mode':mode,'body':body,'at':time.time(),'fixture_controlled':True}})
        atomic_json(root/'fixture-actions.json',audit)
        if mode=='timeout':await asyncio.sleep(9)
        return app.JSONResponse({{'error':'Fixture controlled refusal'}},status_code=409 if mode=='refuse409' else 503)
    entry={{'kind':'actual_public_apply','body':body,'at':time.time()}}
    audit.append(entry);save_audit()
    result=await actual_apply(request)
    entry['status']=getattr(result,'status_code',200);save_audit()
    return result
route.dependant.call=observed_apply
retry_route=next(r for r in app.app.routes if getattr(r,'path',None)=='/api/channels/retry')
actual_retry=retry_route.dependant.call
async def observed_retry(request:app.Request):
    entry={{'kind':'actual_public_retry','body':await request.json(),'at':time.time()}}
    audit.append(entry);save_audit()
    result=await actual_retry(request)
    entry['status']=getattr(result,'status_code',200);save_audit()
    return result
retry_route.dependant.call=observed_retry
import uvicorn
actual_server_init=uvicorn.Server.__init__
server_instance=[]
def capture_server(self,*args,**kwargs):
    actual_server_init(self,*args,**kwargs);server_instance.append(self)
uvicorn.Server.__init__=capture_server
@app.app.post('/api/fixture/shutdown')
async def shutdown(request:app.Request):
    authorized(request)
    body=await request.json()
    if body!={{'nonce':os.environ['CHANNEL_FIXTURE_NONCE']}}:raise HTTPException(400,'Invalid shutdown nonce')
    web_port=int(os.environ['AGENTCHATTR_PORT'])
    web=[value for value in server_instance if value.config.app is app.app and value.config.port==web_port]
    assert len(web)==1,'Exact web Server selection was not unique'
    ports={{web_port,int(os.environ['AGENTCHATTR_MCP_HTTP_PORT']),int(os.environ['AGENTCHATTR_MCP_SSE_PORT'])}}
    listeners=[value for value in server_instance if value.config.host=='127.0.0.1' and value.config.port in ports]
    assert len(listeners)==3 and {{value.config.port for value in listeners}}==ports
    roles={{web_port:'web',int(os.environ['AGENTCHATTR_MCP_HTTP_PORT']):'mcp_http',int(os.environ['AGENTCHATTR_MCP_SSE_PORT']):'mcp_sse'}}
    recorded=[{{'role':roles[value.config.port],'host':value.config.host,'port':value.config.port}} for value in listeners]
    audit.append({{'kind':'exact_listener_shutdown','listeners':recorded,'at':time.time()}});save_audit()
    for value in listeners:value.should_exit=True
    return {{'ok':True,'listeners':recorded}}
import run
run.main()
'''


class Fixture:
    wait = resources.Case.wait
    retain = staticmethod(resources.Case.retain)

    def __init__(self, case):
        self.trusted_bootstrap = trusted_bootstrap_manifest()
        self.guard_source_hash = hashlib.sha256((ROOT / 'tools/channel_guard.py').read_bytes()).hexdigest()
        self.case = case
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='channel lifecycle ' + case + ' ', dir=ROOT / '.audit-tmp'))
        self.data, self.records = self.root / 'data', self.root / 'records'
        self.records.mkdir()
        (self.records / 'commands').mkdir()
        (self.root / 'audit').mkdir()
        atomic_json(self.root / 'bootstrap-before.json', self.trusted_bootstrap)
        self.nonce = uuid.uuid4().hex
        self.servers, self.workers, self.clients, self.observations, self.runs = [], {}, {}, [], set()
        self.api_ready, self.token, self.cleanup = False, None, None
        self.started_at = time.monotonic()
        self.deadline = self.started_at + (300 if case == 'native' else 1200)
        self.marker, self.sentinel = self.root / 'READY.json', self.root / 'browser-done.json'
        sockets = []
        try:
            for _ in range(3):
                handle = socket.socket()
                sockets.append(handle)
                handle.bind(('127.0.0.1', 0))
            self.ports = [value.getsockname()[1] for value in sockets]
            assert len(set(self.ports)) == 3 and not set(self.ports) & {8300, 8200, 8201, 8301, 8302}
            self.base = 'http://127.0.0.1:' + str(self.ports[0])
            self.env = dict(os.environ)
            original_home = Path.home()
            forbidden = [str(ROOT / 'data'), str(ROOT / '.agentchattr'),
                         *(str(original_home / name) for name in ('.agentchattr', '.claude', '.codex', '.gemini', '.config'))]
            for variable in ('APPDATA', 'LOCALAPPDATA'):
                if os.environ.get(variable):
                    forbidden.extend(str(Path(os.environ[variable]) / name) for name in ('Claude', 'Codex', 'Gemini', 'agentchattr'))
            # The owned repository config inputs alone may be read/hash-scoped.
            config_hashes = {}
            forbidden_ports = {8300, 8200, 8201, 8301, 8302}
            import tomllib
            for name in ('config.toml', 'config.local.toml'):
                path = ROOT / name
                config_hashes[name] = {'exists': False}
                if path.exists():
                    raw = path.read_bytes()
                    config_hashes[name] = {'exists': True, 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
                    parsed = tomllib.loads(raw.decode('utf-8'))
                    configured = parsed.get('server', {}).get('data_dir')
                    if configured:
                        forbidden.append(str((ROOT / configured).resolve()))
                    for group, field in (('server', 'port'), ('mcp', 'http_port'), ('mcp', 'sse_port')):
                        value = parsed.get(group, {}).get(field)
                        if type(value) is int:
                            forbidden_ports.add(value)
            assert not set(self.ports) & forbidden_ports
            atomic_json(self.root / 'repository-config-hashes.json', config_hashes)
            self.repository_configs = config_hashes
            home = self.root / 'profile'
            home.mkdir()
            for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME'):
                path = home / key.lower()
                path.mkdir()
                self.env[key] = str(path)
            self.env['HOMEDRIVE'] = home.drive
            self.env['HOMEPATH'] = str(home / 'userprofile')[len(home.drive):]
            for variable in ('PYTHONSTARTUP', 'PYTHONHOME', 'PYTHONUSERBASE', 'PYTHONINSPECT'):
                self.env.pop(variable, None)
            bootstrap = self.root / 'bootstrap'
            bootstrap.mkdir()
            (bootstrap / 'sitecustomize.py').write_text(guard_bootstrap(), encoding='utf-8')
            self.env.update(AGENTCHATTR_DATA_DIR=str(self.data), AGENTCHATTR_UPLOAD_DIR=str(self.root / 'uploads'),
                CHANNEL_FIXTURE_ROOT=str(self.root), CHANNEL_FIXTURE_NONCE=self.nonce,
                CHANNEL_GUARD_POLICY=json.dumps({'forbidden_roots': forbidden, 'forbidden_ports': sorted(forbidden_ports),
                    'allowed_python_roots': [str(ROOT), str(self.root), sys.prefix, sys.base_prefix],
                    'guard_sha256': self.guard_source_hash}),
                PYTHONPATH=str(bootstrap) + os.pathsep + str(ROOT), PYTHONNOUSERSITE='1')
            self.env.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, self.ports))))
        finally:
            close_errors = []
            for handle in sockets:
                try:
                    handle.close()
                except BaseException as error:
                    close_errors.append(error)
            if close_errors:
                raise RuntimeError('Fixture port reservation cleanup failed after visiting every socket') from close_errors[0]

    def remaining(self):
        value = self.deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError('Bounded fixture deadline')
        return value

    def until(self, check, label, seconds=30):
        end = min(self.deadline, time.monotonic() + seconds)
        while time.monotonic() < end:
            try:
                value = check()
                if value:
                    return value
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(.05)
        raise AssertionError('Deadline: ' + label)

    def api(self, path, body=None, *, expected=200):
        headers = {'X-Session-Token': self.token, 'Content-Type': 'application/json'}
        if path.startswith('/api/fixture/'):
            headers['X-Fixture-Nonce'] = self.nonce
        request = urllib.request.Request(self.base + path,
            data=json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None,
            headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=min(15, self.remaining())) as reply:
                status, value = reply.status, json.load(reply)
        except urllib.error.HTTPError as error:
            try:
                status, value = error.code, json.load(error)
            finally:
                error.close()
        self.observations.append({'path': path, 'request': deepcopy(body), 'status': status, 'response': deepcopy(value)})
        assert status == expected, (path, status, expected)
        return value

    def start(self):
        stage = len(self.servers)
        source = server_code(self.root, self.case, stage)
        (self.root / ('server-' + str(stage) + '.py')).write_text(source, encoding='utf-8')
        with (self.root / ('server-' + str(stage) + '.log')).open('wb') as log:
            launcher = subprocess.Popen([sys.executable, '-u', '-c', source], cwd=ROOT, env=self.env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        server = {'launcher': launcher, 'handle': None, 'exit_observed': None}
        self.servers.append(server)
        birth = self.until(lambda: json.loads((self.root / f'server-{stage}-birth.json').read_text(encoding='utf-8')), 'true server birth', 12)
        server['birth'], server['handle'] = birth, self.retain(birth)
        def ready():
            with urllib.request.urlopen(self.base + '/preflight', timeout=2) as reply:
                return reply.read().decode('utf-8-sig')
        page = self.until(ready, 'server HTTP readiness')
        self.token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', page).group(1)
        self.api_ready = True

    def records_read(self):
        rows = [json.loads(path.read_text(encoding='utf-8')) for path in self.records.glob('client-*.json')]
        assert not any(entry.get('error_type') for row in rows for entry in row['turns'] + row['commands'])
        return rows

    def ledger(self):
        path = self.data / 'queue' / 'ledger.json'
        return json.loads(path.read_text(encoding='utf-8'))['records'] if path.exists() else []

    def messages(self):
        path = self.data / 'agentchattr_log.jsonl'
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line] if path.exists() else []

    def effects(self):
        # Volatile cursor/runtime/instance state is deliberately outside this
        # AUTHORITATIVE allowlist; cursor lineage gets its own quiescent proof.
        names = {'agentchattr_log.jsonl', 'todos.json', 'jobs.json', 'schedules.json', 'summaries.json',
                 'session_runs.json', 'channel_lifecycle.json', 'retained_artifacts.json', 'queue/ledger.json'}
        paths = [self.data / name for name in sorted(names)] + list((self.data / 'review_briefs').rglob('*.json'))
        return {path.relative_to(self.data).as_posix(): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size': path.stat().st_size}
            for path in paths if path.is_file()}

    def cursors(self):
        path = self.data / 'mcp_cursors.json'
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}

    def command(self, op, channel='renamed-run'):
        identity = uuid.uuid4().hex
        atomic_json(self.records / 'commands' / (identity + '.json'),
                    {'id': identity, 'op': op, 'channel': channel, 'nonce': self.nonce})
        return self.until(lambda: next((entry for row in self.records_read() for entry in row['commands'] if entry['id'] == identity), None), 'real child MCP command', 15)

    def ws_post(self, connection, text, channel, *, selected=(), rejected=False):
        connection.send(json.dumps({'type': 'message', 'sender': 'fixture-operator', 'text': text,
            'channel': channel, 'attachments': [], 'selected_recipients': list(selected)}, ensure_ascii=False))
        end = min(self.deadline, time.monotonic() + 15)
        while time.monotonic() < end:
            event = json.loads(connection.recv(timeout=min(5, self.remaining())))
            if event['type'] in ('message_error', 'channel_error'):
                assert rejected, event
                self.observations.append({'kind': 'actual_ws_refusal', 'event': event})
                return event
            if event['type'] == 'message_accepted':
                assert not rejected
                saved = self.until(lambda: next((row for row in self.messages() if row.get('uid') == event['uid']), None), 'saved ACK UID')
                assert saved['text'] == text and saved['channel'] == channel
                assert saved['metadata']['recipient_routing']['message_uid'] == event['uid']
                self.observations.append({'kind': 'actual_ws_accept', 'event': event, 'message': saved})
                return saved
        raise TimeoutError('Content response deadline')

    def action(self, op, channel, *, new_name=None, expected=200):
        body = {'op': op, 'channel': channel}
        if new_name is not None:
            body['new_name'] = new_name
        preview = self.api('/api/channels/preview', body)
        return self.api('/api/channels/apply', dict(body, request_id=uuid.uuid4().hex,
            confirmation=channel, preview_token=preview['preview_token']), expected=expected)

    def shutdown_server(self, server):
        if server.get('exit_observed') is not None:
            return
        self.api('/api/fixture/shutdown', {'nonce': self.nonce})
        server['exit_observed'] = server['handle'].wait(timeout=min(12, self.remaining()))
        server['launcher'].wait(timeout=min(5, self.remaining()))
        self.api_ready = False

    def close(self):
        """Visit every isolated owner; only exact end-proven workers may be forced."""
        unresolved, inventory = [], []
        deadline = time.monotonic() + 90
        self.deadline = deadline
        def budget(seconds):
            return max(.05, min(seconds, deadline - time.monotonic()))
        def problem(label, error):
            unresolved.append({'resource': label, 'error_type': type(error).__name__})
        try:
            path = self.data / 'session_runs.json'
            if path.exists():
                self.runs.update(row['id'] for row in json.loads(path.read_text(encoding='utf-8')))
        except Exception as error:
            problem('all-session-inventory', error)
        for identity in sorted(self.runs):
            if self.api_ready:
                try:
                    self.api(f'/api/sessions/{identity}/stop', {})
                except Exception as error:
                    problem('session-' + str(identity), error)
        try:
            for row in self.ledger():
                dispatch = row['envelope']['dispatch_id']
                atomic_json(self.records / ('release-' + dispatch + '.json'), {'dispatch_id': dispatch, 'nonce': self.nonce})
        except Exception as error:
            problem('release-gate-inventory', error)
        configurations = []
        try:
            configurations = list((self.data / 'api_seat_runtime').glob('*/config.json'))
            directories = [path for path in (self.data / 'api_seat_runtime').glob('*') if path.is_dir()]
            assert all((path / 'config.json').is_file() and (path / 'launch.json').is_file() for path in directories)
        except Exception as error:
            problem('runtime-enumeration', error)
        for config in configurations:
            attempt = config.parent.name
            try:
                snapshot = json.loads(config.read_text(encoding='utf-8'))
                valid = _validate(config, snapshot)
                assert valid
                manifest = _manifest(config.with_name('launch.json'), valid[0])
                entry = {'attempt': attempt, 'spawn_outcome': manifest['spawn_outcome'], 'adapter': snapshot['seat']['adapter'],
                         'invocations': [path.name for path in (config.parent / 'invocations').glob('*')]}
                inventory.append(entry)
                assert not entry['invocations'] and entry['adapter'] == 'cli', 'Unexpected model/adapter intent'
                if manifest['spawn_outcome'] == 'failed' and not config.with_name('birth.json').exists():
                    continue
                if attempt not in self.workers:
                    worker = resources.Case.keep_worker(self, attempt)
                    worker['birth'] = json.loads(config.with_name('birth.json').read_text(encoding='utf-8'))
                    worker['ownership'] = deepcopy(valid[0])
                atomic_json(config.with_name('stop.json'), {'attempt': attempt})
            except Exception as error:
                problem('runtime-' + attempt, error)
        # Client exit is cooperative control, never native-parent termination.
        try:
            journals = list(self.records.glob('client-*.json'))
        except Exception as error:
            journals = []
            problem('client-enumeration', error)
        for path in journals:
            try:
                row = json.loads(path.read_text(encoding='utf-8'))
                pid = row['birth']['pid']
                if pid not in self.clients:
                    probe = open_verified_process(row['birth'])
                    if probe['status'] != 'live':
                        raise ValueError('Unretained client native end unknown')
                    binding = row.get('binding') or json.loads((self.records / 'binding.json').read_text(encoding='utf-8'))
                    assert binding['nonce'] == self.nonce and binding['attempt'] in self.workers
                    self.clients[pid] = {'handle': probe['process'], 'birth': row['birth'],
                                        'attempt': binding['attempt'], 'exit_observed': None}
            except Exception as error:
                problem(path.name, error)
        try:
            if journals:
                identity = uuid.uuid4().hex
                atomic_json(self.records / 'commands' / (identity + '.json'),
                    {'id': identity, 'op': 'exit', 'channel': 'peer', 'nonce': self.nonce})
        except Exception as error:
            problem('cooperative-client-exit', error)
        for pid, client in self.clients.items():
            try:
                client['exit_observed'] = client['handle'].wait(timeout=budget(24))
            except Exception as error:
                problem('client-' + str(pid), error)
        for attempt, worker in self.workers.items():
            try:
                try:
                    worker['exit_observed'] = worker['handle'].wait(timeout=budget(12))
                except subprocess.TimeoutExpired:
                    # Fresh complete inventory at the actual fallback action.
                    config = worker['path'] / 'config.json'
                    snapshot = json.loads(config.read_text(encoding='utf-8'))
                    valid = _validate(config, snapshot)
                    birth = json.loads(config.with_name('birth.json').read_text(encoding='utf-8'))
                    receipt = json.loads(config.with_name('receipt.json').read_text(encoding='utf-8'))
                    manifest = _manifest(config.with_name('launch.json'), valid[0])
                    fresh_configs = list((self.data / 'api_seat_runtime').glob('*/config.json'))
                    assert {path.parent.name for path in fresh_configs} == {path.parent.name for path in configurations}
                    assert all((path / 'config.json').is_file() and (path / 'launch.json').is_file()
                        for path in (self.data / 'api_seat_runtime').glob('*') if path.is_dir())
                    for fresh in fresh_configs:
                        fresh_snapshot = json.loads(fresh.read_text(encoding='utf-8'))
                        fresh_valid = _validate(fresh, fresh_snapshot)
                        assert fresh_valid and fresh_snapshot['seat']['adapter'] == 'cli'
                        assert not list((fresh.parent / 'invocations').glob('*'))
                        if fresh.parent.name != attempt:
                            assert _manifest(fresh.with_name('launch.json'), fresh_valid[0])['spawn_outcome'] == 'failed'
                            assert not fresh.with_name('birth.json').exists()
                    fresh_journals = [json.loads(path.read_text(encoding='utf-8')) for path in self.records.glob('client-*.json')]
                    assert {row['birth']['pid'] for row in fresh_journals} == set(self.clients)
                    clients = [value for value in self.clients.values() if value['attempt'] == attempt]
                    assert valid[0] == worker['ownership'] and birth == worker['birth']
                    assert birth['pid'] == worker['handle'].pid and manifest['spawn_outcome'] == 'spawned'
                    assert len(self.workers) == 1 and len(clients) == 1 and type(clients[0]['exit_observed']) is int
                    assert type(clients[0]['handle'].poll()) is int
                    client_journal = json.loads((self.records / ('client-' + str(clients[0]['birth']['pid']) + '.json')).read_text(encoding='utf-8'))
                    assert client_journal['birth'] == clients[0]['birth'] and client_journal['ended'] is True
                    assert client_journal['work_thread_ended'] is True and client_journal['binding']['attempt'] == attempt
                    assert receipt['attempt'] == attempt and type(receipt.get('child_exit_code')) is int
                    assert not list((config.parent / 'invocations').glob('*'))
                    assert snapshot['seat']['adapter'] == 'cli'
                    worker['handle'].terminate()
                    worker['exit_observed'] = worker['handle'].wait(timeout=budget(5))
            except Exception as error:
                problem('worker-' + attempt, error)
        try:
            final = list((self.data / 'api_seat_runtime').glob('*/config.json'))
            assert {path.parent.name for path in final} == {path.parent.name for path in configurations}
            assert all(not list((path.parent / 'invocations').glob('*')) for path in final)
        except Exception as error:
            problem('final-complete-runtime-inventory', error)
        for server in reversed(self.servers):
            try:
                if server.get('handle') is None:
                    raise ValueError('Server birth not retained; no launcher PID control')
                if server.get('exit_observed') is None:
                    try:
                        self.shutdown_server(server)
                    except Exception:
                        server['handle'].terminate()
                        server['exit_observed'] = server['handle'].wait(timeout=budget(5))
                        server['launcher'].wait(timeout=budget(5))
            except Exception as error:
                problem('server', error)
        for value in list(self.clients.values()) + list(self.workers.values()) + self.servers:
            try:
                if value.get('handle'):
                    value['handle'].close()
            except Exception as error:
                problem('handle-close', error)
        for marker in (self.marker, self.sentinel):
            try:
                if marker.exists() and json.loads(marker.read_text(encoding='utf-8')).get('nonce') == self.nonce:
                    marker.unlink()
            except Exception as error:
                problem('owned-marker', error)
        guards = []
        try:
            guards = [json.loads(path.read_text(encoding='utf-8')) for path in (self.root / 'audit').glob('guard-*.json')]
            assert guards and all(not row['real_attempts'] for row in guards)
            assert all(row['guard_sha256'] == self.guard_source_hash for row in guards)
            assert hashlib.sha256((ROOT / 'tools/channel_guard.py').read_bytes()).hexdigest() == self.guard_source_hash
            expected_pids = {row['birth']['pid'] for row in self.servers + list(self.workers.values()) + list(self.clients.values()) if row.get('birth')}
            assert expected_pids <= {row['pid'] for row in guards}
        except Exception as error:
            problem('isolation-guard-evidence', error)
        logs = []
        for path in self.root.glob('server-*.log'):
            try:
                raw = path.read_bytes()
                text = raw.decode('utf-8', errors='replace')
                logs.append({'name': path.name, 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                    'counts': {word: text.count(word) for word in ('Traceback', 'Selector', 'Warning', 'Error')}})
            except Exception as error:
                problem('server-log-evidence', error)
        try:
            after_bootstrap = trusted_bootstrap_manifest()
            assert after_bootstrap == self.trusted_bootstrap
            atomic_json(self.root / 'bootstrap-after.json', after_bootstrap)
        except Exception as error:
            problem('trusted-bootstrap-after', error)
        try:
            config_after = {}
            for name in ('config.toml', 'config.local.toml'):
                path = ROOT / name
                config_after[name] = {'exists': False}
                if path.exists():
                    raw = path.read_bytes()
                    config_after[name] = {'exists': True, 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
            atomic_json(self.root / 'repository-config-after.json', config_after)
            assert config_after == self.repository_configs
        except Exception as error:
            problem('owned-repository-config-after', error)
        self.cleanup = {'actual_workers_waited': sum(type(row.get('exit_observed')) is int for row in self.workers.values()),
            'actual_clients_waited': sum(type(row.get('exit_observed')) is int for row in self.clients.values()),
            'actual_servers_waited': sum(type(row.get('exit_observed')) is int for row in self.servers),
            'model_intents': sum(len(row['invocations']) for row in inventory),
            'configured_api_runtimes': sum(row['adapter'] != 'cli' for row in inventory),
            'provider_scope': 'no API provider configured; model/runtime inventory is measured, no provider listener',
            'external_connections': sum(len(row['real_attempts']) for row in guards), 'server_logs': logs,
            'inventory': inventory, 'guard_records': guards, 'redirected_profile_files': [path.relative_to(self.root).as_posix()
                for path in (self.root / 'profile').rglob('*') if path.is_file()], 'unresolved': unresolved}
        atomic_json(self.root / 'cleanup.json', self.cleanup)
        assert not unresolved, 'Cleanup unresolved; preserve scratch'


def native(fixture):
    from websockets.sync.client import connect
    fixture.start()
    common = {'id': 'cli', 'name': 'Lifecycle CLI', 'adapter': 'cli', 'provider': 'channel-cli',
              'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
    fixture.api('/api/preflight/packages', {'id': 'lifecycle', 'name': 'Local channel fixture', 'seats': [common]})
    revision = fixture.api('/api/preflight/seats')['package_revisions']['lifecycle']
    fixture.api('/api/preflight/packages/lifecycle/launch', {'revision': revision})
    def ready():
        state = fixture.api('/api/fixture/state')
        row = state['workers'].get('lifecycle/cli')
        return row if row and row['readiness'] and row['readiness'].get('process_verified') is True and row['readiness']['state'] == 'ready' else None
    owner = fixture.until(ready, 'actual CLI readiness', 30)
    worker = resources.Case.keep_worker(fixture, owner['attempt'])
    worker['birth'] = json.loads((worker['path'] / 'birth.json').read_text(encoding='utf-8'))
    worker['ownership'] = deepcopy(_validate(worker['path'] / 'config.json', json.loads((worker['path'] / 'config.json').read_text(encoding='utf-8')))[0])
    snapshot = json.loads((worker['path'] / 'config.json').read_text(encoding='utf-8'))
    assert snapshot['provider']['mcp_inject'] == 'env' and not snapshot['provider'].get('settings_file')
    assert not list((worker['path'] / 'invocations').glob('*'))
    row = fixture.until(lambda: records[0] if len(records := fixture.records_read()) == 1 else None, 'hidden client birth')
    assert row['console_present'] and not row['console_visible']
    fixture.clients[row['birth']['pid']] = {'handle': fixture.retain(row['birth']), 'birth': row['birth'],
        'attempt': owner['attempt'], 'exit_observed': None}
    # Exact fixed binding schema, no credential material.
    atomic_json(fixture.records / 'binding.json', {key: owner[key] for key in ('name', 'identity_id', 'attempt')} | {'nonce': fixture.nonce})
    with connect(fixture.base.replace('http:', 'ws:') + '/ws?token=' + fixture.token, open_timeout=10) as connection:
        posted = fixture.ws_post(connection, '@' + owner['name'] + ' FIRST_MANUAL', 'lifecycle-run', selected=[owner['name']])
        turn = fixture.until(lambda: next((turn for row in fixture.records_read() for turn in row['turns'] if turn.get('read_completed_at')), None), 'actual first injection MCP read')
        dispatch = turn['dispatch_id']
        before = fixture.effects()
        for op in ('archive', 'delete', 'rename'):
            body = {'op': op, 'channel': 'lifecycle-run'}
            if op == 'rename':
                body['new_name'] = 'renamed-run'
            preview = fixture.api('/api/channels/preview', body)
            assert any(item.get('dispatch_id') == dispatch for item in preview['blockers'])
            fixture.api('/api/channels/apply', dict(body, confirmation='lifecycle-run', request_id=uuid.uuid4().hex,
                preview_token=preview['preview_token']), expected=409)
            after = fixture.effects()
            fixture.observations.append({'kind': 'busy_refusal_effects', 'op': op, 'dispatch_id': dispatch,
                                         'before': before, 'after': after})
            assert after == before
        atomic_json(fixture.records / ('release-' + dispatch + '.json'), {'dispatch_id': dispatch, 'nonce': fixture.nonce})
        fixture.until(lambda: next((r for r in fixture.ledger() if r['envelope']['dispatch_id'] == dispatch and r['state'] == 'released'), None), 'genuine MCP terminal release')
        rename_preview = fixture.api('/api/channels/preview', {'op': 'rename', 'channel': 'lifecycle-run', 'new_name': 'renamed-run'})
        assert not rename_preview['blockers']
        messages, jobs = deepcopy(fixture.messages()), fixture.api('/api/jobs')
        sessions_path = fixture.data / 'session_runs.json'
        sessions = json.loads(sessions_path.read_text(encoding='utf-8'))
        schedules_path = fixture.data / 'schedules.json'
        schedules = json.loads(schedules_path.read_text(encoding='utf-8'))
        summaries_path = fixture.data / 'summaries.json'
        summaries = json.loads(summaries_path.read_text(encoding='utf-8'))
        todos_before = (fixture.data / 'todos.json').read_bytes()
        immutable = {path.relative_to(fixture.data).as_posix(): path.read_bytes() for path in fixture.data.rglob('*')
            if path.is_file() and (path.parent.name in ('queue', 'review_briefs') or path.name in ('config.json', 'birth.json', 'launch.json'))}
        upload = fixture.root / 'uploads' / '0123456789abcdef0123456789abcdef.txt'
        upload_bytes = upload.read_bytes()
        cursor_before, effects_before = fixture.cursors(), fixture.effects()
        assert 'lifecycle-run' in cursor_before[owner['name']]
        fixture.observations.append({'kind': 'rename_immediate_before_apply', 'effects': effects_before,
                                     'cursor': cursor_before})
        fixture.api('/api/channels/apply', {'op': 'rename', 'channel': 'lifecycle-run', 'new_name': 'renamed-run',
            'request_id': uuid.uuid4().hex, 'confirmation': 'lifecycle-run', 'preview_token': rename_preview['preview_token']})
        cursor_expected = deepcopy(cursor_before)
        for values in cursor_expected.values():
            if 'lifecycle-run' in values:
                values['renamed-run'] = values.pop('lifecycle-run')
        cursor_after = fixture.cursors()
        fixture.observations.append({'kind': 'quiescent_cursor_rename', 'before': cursor_before, 'after': cursor_after})
        assert cursor_after == cursor_expected
        for row in messages:
            if row.get('channel') == 'lifecycle-run':
                row['channel'] = 'renamed-run'
        assert fixture.messages() == messages
        for row in jobs:
            if row['channel'] == 'lifecycle-run':
                row['channel'] = 'renamed-run'
                for message in row['messages']:
                    if message.get('channel') == 'lifecycle-run':
                        message['channel'] = 'renamed-run'
        assert fixture.api('/api/jobs') == jobs
        for rows in (sessions, schedules):
            for row in rows:
                if row['channel'] == 'lifecycle-run':
                    row['channel'] = 'renamed-run'
        assert json.loads(sessions_path.read_text(encoding='utf-8')) == sessions
        assert json.loads(schedules_path.read_text(encoding='utf-8')) == schedules
        summaries['renamed-run'] = summaries.pop('lifecycle-run')
        assert json.loads(summaries_path.read_text(encoding='utf-8')) == summaries
        assert (fixture.data / 'todos.json').read_bytes() == todos_before
        for name, value in immutable.items():
            assert (fixture.data / name).read_bytes() == value
        assert upload.read_bytes() == upload_bytes
        omitted = fixture.command('send_omitted')
        assert omitted['reply'].startswith('Sent (id=')
        assert fixture.messages()[-1]['channel'] == 'renamed-run'
        fixture.action('archive', 'renamed-run')
        before, last_ids, cursor_archived = fixture.effects(), [r['id'] for r in fixture.messages()], fixture.cursors()
        for operation, channel in [('send_explicit', 'lifecycle-run'), ('send_explicit', 'renamed-run'), ('send_omitted', 'renamed-run')]:
            result = fixture.command(operation, channel)
            assert result['reply'].startswith('Error:')
        errors = [fixture.ws_post(connection, 'Archived refusal ' + str(index), 'renamed-run', rejected=True) for index in range(25)]
        assert len(errors) == 25 and all(row['type'] in ('message_error', 'channel_error') for row in errors)
        quiet_start = time.monotonic()
        while time.monotonic() - quiet_start < 3:
            fixture.remaining()
            assert fixture.effects() == before and len(fixture.ledger()) == 1
            assert sum(len(row['turns']) for row in fixture.records_read()) == 1
            time.sleep(.1)
        after = fixture.effects()
        fixture.observations.append({'kind': 'archived_25_ws_refusals', 'before': before, 'after': after,
            'error_count': len(errors), 'quiet_seconds': time.monotonic() - quiet_start})
        assert after == before and [row['id'] for row in fixture.messages()] == last_ids
        assert fixture.cursors() == cursor_archived
        fixture.ws_post(connection, 'UNADDRESSED_PEER_PROGRESS', 'peer')
        retained_peer = [deepcopy(row) for row in fixture.messages() if row['channel'] == 'peer']
        primary_before = fixture.effects()
        fixture.api('/api/jobs', {'title': 'Refused', 'channel': 'renamed-run'}, expected=409)
        fixture.api('/api/sessions/start', {'template_id': TEMPLATE['id'], 'channel': 'renamed-run', 'cast': {'reader': 'human-reader'}, 'input_text': 'No allocation'}, expected=409)
        fixture.api('/api/schedules', {'prompt': 'Refused', 'targets': [owner['name']], 'channel': 'renamed-run', 'spec': 'every 1m'}, expected=409)
        primary_after = fixture.effects()
        fixture.observations.append({'kind': 'archived_primary_refusals', 'before': primary_before, 'after': primary_after})
        assert primary_after == primary_before
        fixture.action('reopen', 'renamed-run')
        fixture.ws_post(connection, '@' + owner['name'] + ' SECOND_MANUAL', 'renamed-run', selected=[owner['name']])
        second = fixture.until(lambda: turns[1] if len(turns := [t for r in fixture.records_read() for t in r['turns'] if t.get('read_completed_at')]) == 2 else None, 'second actual injection')
        atomic_json(fixture.records / ('release-' + second['dispatch_id'] + '.json'), {'dispatch_id': second['dispatch_id'], 'nonce': fixture.nonce})
        fixture.until(lambda: next((r for r in fixture.ledger() if r['envelope']['dispatch_id'] == second['dispatch_id'] and r['state'] == 'released'), None), 'second actual release')
        preview = fixture.api('/api/channels/preview', {'op': 'delete', 'channel': 'renamed-run'})
        current_messages = [row for row in fixture.messages() if row['channel'] == 'renamed-run']
        assert preview['counts']['messages'] == len(current_messages)
        assert preview['counts']['uploads'] == sum(len(row.get('attachments', [])) for row in current_messages)
        fixture.api('/api/channels/apply', {'op': 'delete', 'channel': 'renamed-run', 'request_id': uuid.uuid4().hex,
            'confirmation': 'renamed-run', 'preview_token': preview['preview_token']})
        retained = fixture.api('/api/channels/retained?channel=renamed-run')
        assert retained['state'] == 'retired' and retained['jobs'] and retained['sessions'] and retained['schedules'] and retained['summary']
        assert retained['uploads'] and retained['uploads'][0]['safe_links'] and upload.read_bytes() == upload_bytes
        assert not [row for row in fixture.messages() if row['channel'] == 'renamed-run']
        assert [row for row in fixture.messages() if row['channel'] == 'peer'] == retained_peer
        for name in ('lifecycle-run', 'renamed-run'):
            fixture.api('/api/channels/preview', {'op': 'create', 'channel': name}, expected=409)
        assert sum(len(row['turns']) for row in fixture.records_read()) == 2
        assert len(fixture.ledger()) == 2
        assert not list((worker['path'] / 'invocations').glob('*'))
        assert posted['metadata']['recipient_routing']['recipients'][0]['identity_id'] == owner['identity_id']
    return {'case': 'native', 'cli_injections': sum(len(row['turns']) for row in fixture.records_read()),
            'dispatches': len(fixture.ledger()), 'archived_ws_refusals': len(errors), 'native_model_claim': False}


def browser(fixture):
    fixture.start()
    before = fixture.api('/api/channels')
    assert {'general', 'manage-run', 'peer'} <= {row['name'] for row in before['channels'] if row['state'] == 'active'}
    assert any(row['state'] == 'unregistered' and row['name'] == 'odd <tag> + name' for row in before['channels'])
    fixture.api('/api/fixture/control', {'nonce': fixture.nonce, 'action': 'pending_delete'})
    pending = json.loads((fixture.data / 'channel_lifecycle.json').read_text(encoding='utf-8'))['intent']
    assert pending and pending['old'] == 'pending-run'
    fixture.shutdown_server(fixture.servers[-1])
    fixture.start()
    current = fixture.api('/api/channels')
    assert current['intent'] == pending
    assert any(row['name'] == 'peer' and row['state'] == 'active' for row in current['channels'])
    ready = {'stage': 'channel_lifecycle_browser_ready', 'nonce': fixture.nonce, 'url': fixture.base,
        'channel': 'manage-run', 'scratch': str(fixture.root), 'sentinel': str(fixture.sentinel),
        'deadline_seconds': int(fixture.remaining()), 'observer': 'root browser operator',
        'pending_request_id': pending['request_id'], 'case': 'browser',
        'rename_destination': 'managed-new', 'ready_at': time.time(),
        'private_controls': '/api/fixture/control (X-Session-Token + X-Fixture-Nonce headers, empty query, loopback, fixed actions only)'}
    atomic_json(fixture.marker, ready)
    print(json.dumps(ready), flush=True)
    def finished():
        if not fixture.sentinel.exists():
            return None
        value = json.loads(fixture.sentinel.read_text(encoding='utf-8'))
        assert value.get('nonce') == fixture.nonce, 'Unknown sentinel preserved'
        return value
    completion = fixture.until(finished, 'actual browser observation sentinel', fixture.remaining())
    assert completion.get('actual_ui_completed') is True
    assert completion.get('profile') == 'isolated' and completion.get('browser_closed') is True
    screenshots = completion.get('screenshots', [])
    assert screenshots and {item['viewport']['width'] for item in screenshots} >= {390, 1280}
    for item in screenshots:
        path = Path(item['path']).resolve()
        assert path.is_relative_to(fixture.root.resolve()) and path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        assert item['observer'] in ('root', 'reviewer')
    current = fixture.api('/api/channels')
    assert current['intent'] is None
    assert any(row['name'] == 'managed-new' and row['state'] == 'retired' for row in current['channels'])
    actions = json.loads((fixture.root / 'fixture-actions.json').read_text(encoding='utf-8'))
    public = [row for row in actions if row.get('kind') == 'actual_public_apply' and row.get('status') == 200
              and row['at'] >= ready['ready_at']]
    assert {row['body']['op'] for row in public} >= {'rename', 'archive', 'reopen', 'delete', 'cancel_queued'}
    assert len([row for row in public if row['body']['op'] == 'rename']) == 1
    assert len([row for row in actions if row.get('kind') == 'actual_channel_observer'
                and row.get('event', {}).get('type') == 'channel_deleted'
                and row['event'].get('channel') == 'pending-run']) == 1
    assert not fixture.records_read() and not list((fixture.data / 'api_seat_runtime').glob('*/config.json'))
    fixture.observations.append({'kind': 'browser_observer_receipt', 'receipt': completion, 'catalog': current})
    return {'case': 'browser', 'browser_observer': completion['observer'], 'screenshots': len(screenshots),
            'cli_injections': 0, 'dispatches': len(fixture.ledger()), 'native_model_claim': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=('native', 'browser'), required=True)
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    if args.compile_only:
        for case, stage in (('native', 0), ('browser', 0), ('browser', 1)):
            source = server_code(Path('C:/owned-channel-fixture'), case, stage)
            compile(source, '<channel-server>', 'exec')
            constants = [node.value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Constant)]
            assert b'OWNED_UPLOAD_BYTES\r\n' in constants and 'Exact history café\r\nsource' in constants
            assert 'Retained conversation café\r\nline' in constants and 'Exact retained summary\r\nsecond line' in constants
        compile(guard_bootstrap(), '<guard-bootstrap>', 'exec')
        compile((ROOT / 'tools' / 'channel_guard.py').read_text(encoding='utf-8'), '<channel-guard>', 'exec')
        compile((ROOT / 'tools' / 'fake_channel_client.py').read_text(encoding='utf-8'), '<channel-client>', 'exec')
        print('Compiled 3 server variants, 1 guard bootstrap, 1 stdlib guard and 1 client; no fixture/resources constructed.')
        return
    fixture, result, failure = None, None, None
    def failure_evidence(error):
        return {'classification': 'pending_independent_product_fixture_environment_review',
            'error_type': type(error).__name__, 'case': args.case,
            'frames': [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                       for frame in traceback.extract_tb(error.__traceback__)]}
    try:
        if os.name != 'nt':
            raise RuntimeError('This acceptance draft requires Windows native birth APIs')
        fixture = Fixture(args.case)
        source_hashes = {name: hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest()
                         for name in ('verify_channel_lifecycle.py', 'fake_channel_client.py', 'channel_guard.py')}
        atomic_json(fixture.root / 'source-hashes.json', {'head': repository_head(), 'tools': source_hashes})
        result = native(fixture) if args.case == 'native' else browser(fixture)
    except BaseException as error:
        failure = error
        if fixture is not None:
            try:
                atomic_json(fixture.root / 'failure.json', failure_evidence(error))
            except OSError:
                pass  # Cleanup still runs, and the original failure remains a failure.
    finally:
        if fixture is not None:
            try:
                atomic_json(fixture.root / 'observations.json', fixture.observations)
            except BaseException as error:
                failure = failure or error
            finally:
                try:
                    fixture.close()
                except BaseException as error:
                    failure = failure or error
    if failure is not None:
        if fixture is not None:
            try:
                atomic_json(fixture.root / 'failure.json', failure_evidence(failure))
            except OSError:
                pass
        raise failure
    try:
        expected = (1, 1, 1) if args.case == 'native' else (0, 0, 2)
        actual = tuple(fixture.cleanup[key] for key in ('actual_workers_waited', 'actual_clients_waited', 'actual_servers_waited'))
        assert actual == expected and fixture.cleanup['model_intents'] == 0
        assert fixture.cleanup['configured_api_runtimes'] == 0 and fixture.cleanup['external_connections'] == 0
        assert not fixture.cleanup['unresolved']
        result.update(result='PASS', scratch=str(fixture.root), cleanup=fixture.cleanup,
                      elapsed_seconds=time.monotonic() - fixture.started_at)
        atomic_json(fixture.root / 'result.json', result)
    except BaseException as error:
        try:
            atomic_json(fixture.root / 'failure.json', failure_evidence(error))
        except OSError:
            pass
        raise
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
