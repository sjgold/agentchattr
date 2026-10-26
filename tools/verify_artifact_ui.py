"""Review-gated reduced20 browser fixture. Import/--compile-only starts nothing.

--run owns a bounded server/managed fake CLI/API fixture; a separate isolated
browser controller performs actual UI actions. No provider, activation or save
dialog claim. All files/attempts are retained. Never run before pin clearance.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import hmac
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
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
CANNED = '\ufeff# Fixture document\r\nExact café 日本語\r\n<script>window.BAD=1</script>\r\n![x](javascript:bad)\r\n'
FORBIDDEN_PORTS = frozenset((8300, 8200, 8201, 8301, 8302))
CONTROL_PREFIX = '/__artifact_fixture'
CONTROL_ACTIONS = frozenset(('seed', 'release_cli', 'hold_api', 'release_api', 'hold_create',
    'release_create', 'capability_off', 'capability_on', 'hold_authoring', 'restore_authoring',
    'fail_read', 'proxy_download', 'poll_failure', 'restore_faults', 'finish', 'shutdown'))
EVIDENCE_CASES = frozenset(('cli', 'api', 'lost-create', 'refusal', 'cancel-stop', 'lifecycle',
    'read-download', 'viewport-keyboard', 'polling', 'reload', 'stale-response', 'cleanup'))
PIN_FILES = ('runtime_protocol.py', 'api_seat_runtime.py', 'cli_worker.py', 'wrapper.py',
    'wrapper_windows.py', 'wrapper_api.py', 'artifact_worker.py', 'artifact_operator.py',
    'artifact_routes.py', 'artifact_sources.py', 'artifact_service.py', 'artifact_store.py',
    'static/index.html', 'static/artifacts.js', 'static/artifacts.css', 'static/sessions.js',
    'tools/channel_guard.py', 'tools/verify_artifact_ui.py', 'tools/fake_artifact_client.py',
    'tools/test_artifact_ui_harness_controls.py')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=True, allow_nan=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def local_request(request, timeout):
    """Parent/control requests must not inherit the host's ambient proxies."""
    from urllib.request import build_opener, ProxyHandler
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)


def public_evidence(value, secrets):
    """Refuse rather than silently losing evidence. Never print a leaked string."""
    raw = json.dumps(value, ensure_ascii=True, allow_nan=False)
    if any(secret and secret in raw for secret in secrets):
        raise ValueError('Secret-bearing evidence refused')
    return value


def owned_origin(address, ports):
    parsed = urlsplit(address)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1'
            or parsed.port not in ports or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError('Unowned fixture origin')
    return 'http://127.0.0.1:' + str(parsed.port)


def check_address(address, ports):
    if (not isinstance(address, tuple) or len(address) < 2
            or address[0] not in ('127.0.0.1', 'localhost', '::1') or address[1] not in ports):
        raise PermissionError('Fixture owned-port allowlist refused connection')


def authorized(headers, token, nonce):
    return (len(headers.getlist('x-session-token')) == 1
            and len(headers.getlist('x-fixture-nonce')) == 1
            and hmac.compare_digest(headers.get('x-session-token', ''), token)
            and hmac.compare_digest(headers.get('x-fixture-nonce', ''), nonce))


def safe_env(original, root, ports, nonce, policy):
    root = Path(root)
    # Allowlist the OS execution essentials; no inherited secret/proxy/config vars.
    names = ('SystemRoot', 'WINDIR', 'COMSPEC', 'PATH', 'PATHEXT', 'SYSTEMDRIVE',
             'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS')
    result = {key: value for key, value in original.items() if key.upper() in {x.upper() for x in names}}
    for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP',
                'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME'):
        result[key] = str(root / 'profiles' / key.lower())
    result.update(HOMEDRIVE=root.drive, HOMEPATH=str(root / 'profiles/userprofile')[len(root.drive):],
        CHANNEL_FIXTURE_ROOT=str(root), CHANNEL_FIXTURE_NONCE=nonce,
        CHANNEL_GUARD_POLICY=json.dumps(policy), ARTIFACT_FIXTURE_PORTS=json.dumps(ports),
        ARTIFACT_FIXTURE_REQUIRED='1', PYTHONNOUSERSITE='1',
        PYTHONPATH=str(root / 'bootstrap') + os.pathsep + str(ROOT), NO_PROXY='127.0.0.1,localhost,::1',
        AGENTCHATTR_DATA_DIR=str(root / 'data'), AGENTCHATTR_UPLOAD_DIR=str(root / 'uploads'),
        AGENTCHATTR_PORT=str(ports[0]), AGENTCHATTR_MCP_HTTP_PORT=str(ports[1]),
        AGENTCHATTR_MCP_SSE_PORT=str(ports[2]), ARTIFACT_FIXTURE_DUMMY_KEY='fixture-only-no-provider')
    return result


def bootstrap_source():
    return '''import os
try:
 from tools.verify_artifact_ui import install_fixture_guard
 install_fixture_guard()
except BaseException:
 os._exit(91)
'''


def install_fixture_guard():
    """Only sitecustomize calls this, before any runtime_protocol import."""
    if os.environ.get('ARTIFACT_FIXTURE_REQUIRED') != '1' or 'runtime_protocol' in sys.modules:
        raise RuntimeError('Missing/late owned bootstrap')
    from tools.channel_guard import install_guard
    install_guard('artifact-python')
    root = Path(os.environ['CHANNEL_FIXTURE_ROOT']).resolve()
    ports = json.loads(os.environ['ARTIFACT_FIXTURE_PORTS'])
    private = read_json(root / 'private.json')
    if ports != private['ports'] or os.environ['CHANNEL_FIXTURE_NONCE'] != private['nonce']:
        raise ValueError('Guard fixture binding mismatch')
    # Pure negative test does not open a socket or leave a real guard violation.
    try:
        check_address(('127.0.0.1', 65500), ports)
    except PermissionError:
        pass
    else:
        raise RuntimeError('Owned-port negative control did not refuse')
    def audit(event, args):
        if event in ('socket.connect', 'socket.bind'):
            try:
                check_address(args[1], ports)
            except PermissionError:
                write_json(root / 'audit' / ('unowned-port-' + str(os.getpid()) + '.json'), {'event': event})
                raise
    sys.addaudithook(audit)
    import runtime_protocol
    if runtime_protocol.SUPPORTED_CAPABILITIES != ():
        raise ValueError('Production capability changed')
    runtime_protocol.SUPPORTED_CAPABILITIES = ('artifact-v1',)
    sys._artifact_fixture_guard = str(root)
    from process_identity import capture_birth
    write_json(root / 'audit' / ('artifact-bootstrap-' + str(os.getpid()) + '.json'),
        {'birth': capture_birth(), 'capabilities': ['artifact-v1'], 'owned_port_negative_test': True})
    # Wrapper imports config_loader before reading seat snapshots: do not allow a
    # fallback read of real provider config. The literal owned config is shared.
    import config_loader
    config_loader.load_config = lambda *args, **kwargs: deepcopy(private['config'])


def require_guard():
    expected = os.environ.get('CHANNEL_FIXTURE_ROOT')
    actual = getattr(sys, '_artifact_fixture_guard', None)
    if not expected or actual != str(Path(expected).resolve()) or not getattr(sys, '_channel_fixture_guard', False):
        raise RuntimeError('Fixture child refused before resource construction')
    return Path(actual)


def verify_blob(payload):
    if set(payload) != {'base64', 'browser_sha256', 'filename'} or payload['filename'] != 'document.md':
        raise ValueError('Invalid bounded Blob proof')
    raw = base64.b64decode(payload['base64'], validate=True)
    if len(raw) > 524288 or hash_bytes(raw) != payload['browser_sha256'] or raw != CANNED.encode('utf-8'):
        raise ValueError('Blob proof mismatch')
    return raw


def validate_observation(payload, secrets):
    if (not isinstance(payload, dict) or set(payload) != {'case', 'observations'}
            or payload['case'] not in EVIDENCE_CASES or not isinstance(payload['observations'], dict)
            or len(json.dumps(payload).encode('utf-8')) > 131072):
        raise ValueError('Invalid bounded browser observation')
    return public_evidence(payload, secrets)


def literal_config(root, ports):
    return {'server': {'host': '127.0.0.1', 'port': ports[0], 'data_dir': str(root / 'data')},
        'mcp': {'http_port': ports[1], 'sse_port': ports[2]},
        'images': {'upload_dir': str(root / 'uploads')}, 'routing': {'default': 'none'},
        'agents': {'artifact-cli': {'command': sys.executable, 'cwd': str(root),
            'cli_args': [str(ROOT / 'tools/fake_artifact_client.py')], 'strip_env': [],
            'mcp_inject': 'env', 'mcp_env_var': 'ARTIFACT_FIXTURE_MCP', 'inject_delay': .1},
            'artifact-api': {'type': 'api', 'base_url': 'http://127.0.0.1:' + str(ports[3]) + '/v1',
                'api_key_env': 'ARTIFACT_FIXTURE_DUMMY_KEY'}}}


def seed_session(app, owner, channel, state='complete'):
    """Actual stores/projection; synthetic accepted source, no review generation."""
    session = app.session_store.create('planning', channel,
        {'planner': owner['name'], 'challenger': 'human', 'synthesiser': 'human'}, 'fixture-operator',
        input_text='Frozen source café\r\n', participant_bindings={
            'planner': {'kind': 'agent', 'identity_id': owner['identity_id']},
            'challenger': {'kind': 'human', 'identity_id': None},
            'synthesiser': {'kind': 'agent', 'identity_id': None}})
    if session is None:
        raise ValueError('Fixture source session slot unavailable')
    event = {'brief_id': uuid.uuid4().hex, 'run_id': session['run_id'],
        'turn_id': session['run_id'] + ':0:0', 'attempt_id': uuid.uuid4().hex,
        'input_revision': session['input_revision'], 'event_id': uuid.uuid4().hex,
        'kind': 'final', 'sender': owner['name'], 'content': 'Accepted source café\r\n', 'is_output': False}
    metadata = {key: event[key] for key in ('brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision', 'event_id', 'kind')}
    metadata.update(session_id=session['id'], routing_suppressed=True, session_output=False)
    row = app.store.add_once('session-event:' + event['event_id'], event['sender'], event['content'],
        msg_type='session_result', channel=channel, metadata=metadata)
    event['projected_message_id'] = row['id']
    return app.session_store._event_update(session['id'], lambda value: value.update(admitted_events=[event], state=state))


def browser_observer(nonce):
    """Fixture-only observer. Secret stays inside closure; exported proof is scanned."""
    return r'''(() => {
const nonce=NONCE, blobs=new Map(), evidence={clicks:[],revoked:[],errors:[]};
const create=URL.createObjectURL.bind(URL), revoke=URL.revokeObjectURL.bind(URL);
URL.createObjectURL=b=>{const u=create(b);blobs.set(u,b);return u};
URL.revokeObjectURL=u=>{evidence.revoked.push({at:performance.now()});blobs.delete(u);revoke(u)};
document.addEventListener('click',event=>{const a=event.target.closest?.('a[download]');if(!a||a.download!=='document.md')return;
event.preventDefault();const b=blobs.get(a.href);const entry={filename:a.download,at:performance.now(),native_default_intercepted:true};evidence.clicks.push(entry);
(async()=>{if(!b)throw Error('Actual object URL Blob absent');const raw=await b.arrayBuffer();
const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),x=>x.toString(16).padStart(2,'0')).join('');
let binary='';for(const x of new Uint8Array(raw))binary+=String.fromCharCode(x);
const response=await fetch('/__artifact_fixture/blob',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','X-Session-Token':window.SESSION_TOKEN||window.__SESSION_TOKEN__,'X-Fixture-Nonce':nonce},body:JSON.stringify({base64:btoa(binary),browser_sha256:digest,filename:a.download})});
if(!response.ok)throw Error('Server Blob proof refused');Object.assign(entry,await response.json(),{browser_sha256:digest});})().catch(()=>evidence.errors.push('blob_proof_failed'));
},true);
window.__artifactFixtureEvidence=()=>JSON.parse(JSON.stringify(evidence));
window.__artifactFixtureReport=async payload=>{const r=await fetch('/__artifact_fixture/evidence',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','X-Session-Token':window.SESSION_TOKEN||window.__SESSION_TOKEN__,'X-Fixture-Nonce':nonce},body:JSON.stringify(payload)});if(!r.ok)throw Error('Observation refused');return {recorded:true}};
})();'''.replace('NONCE', json.dumps(nonce))


def runtime_server():
    root = require_guard()
    private = read_json(root / 'private.json')
    ports, nonce = private['ports'], private['nonce']
    import config_loader
    config_loader.load_config = lambda *args, **kwargs: deepcopy(private['config'])
    import app
    import runtime_protocol
    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse, Response
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    gates = {key: threading.Event() for key in ('api', 'create')}
    gates['api'].set(); gates['create'].set()
    counts = {'fake_api': 0, 'capture': 0}
    fault = {'read': False, 'proxy': False, 'poll': False}
    state = {'sessions': {}, 'actions': [], 'finished': False}
    state_lock = threading.RLock()
    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            if self.path != '/v1/chat/completions': self.send_error(404); return
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 3*1024*1024: self.send_error(413); return
            json.loads(self.rfile.read(length))
            with state_lock: counts['fake_api'] += 1
            if not gates['api'].wait(100): self.send_error(503); return
            raw = json.dumps({'id': 'fixture', 'model': 'fixture-api',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': CANNED}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode('utf-8')
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
    provider = ThreadingHTTPServer(('127.0.0.1', ports[3]), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    app._fetch_latest_release = lambda: None  # disclosed fixture-only upstream lookup suppression
    original_configure = app.configure
    def configure(*args, **kwargs):
        original_configure(*args, **kwargs)
        private['token'] = app.session_token
        write_json(root / 'private.json', private)
        for channel in ('document-cli', 'document-api', 'peer', 'absent-author', 'active-source'):
            catalog = app.channel_service.catalog.snapshot()
            app.channel_service.catalog.create(channel, expected_revision=catalog['revision'])
        app.channel_service._project(app.channel_service.catalog.snapshot())
        common = {'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        package = {'id': 'artifact-fixture', 'name': 'Local fake document authors', 'seats': [
            dict(common, id='cli', name='Fixture CLI', adapter='cli', provider='artifact-cli', model=None),
            dict(common, id='api', name='Fixture API', adapter='openai-compatible', provider='artifact-api', model='fixture-api')]}
        app.api_seat_store.save(package)
        # Launch stays explicit via the nonce control after listeners are ready.
    app.configure = configure
    import artifact_operator
    original_capture = artifact_operator.capture_artifact_session_source
    def capture(*args, **kwargs):
        result = original_capture(*args, **kwargs)
        with state_lock: counts['capture'] += 1
        if not gates['create'].wait(40): raise TimeoutError('Fixture create gate expired')
        return result
    artifact_operator.capture_artifact_session_source = capture
    def auth(request):
        if (request.client.host != '127.0.0.1' or request.scope.get('query_string')
                or not authorized(request.headers, app.session_token, nonce)):
            raise HTTPException(403, 'Fixture authorization required')
    @app.app.get(CONTROL_PREFIX + '/state')
    def fixture_state(request: app.Request):
        auth(request)
        with app.api_seat_manager.lock:
            workers = {key: {'attempt': item['id'], 'state': app.api_seat_manager._inspect(key)['state'],
                'base': item['base']} for key, item in app.api_seat_manager.attempts.items()}
        value = {'sessions': state['sessions'], 'counts': counts, 'workers': workers,
            'actions': state['actions'], 'finished': state['finished']}
        return public_evidence(value, (nonce, app.session_token))
    @app.app.post(CONTROL_PREFIX + '/blob')
    async def blob(request: app.Request):
        auth(request)
        raw = await request.body()
        if len(raw) > 750000: raise HTTPException(413)
        payload = json.loads(raw); content = verify_blob(payload)
        target = root / 'downloads' / (hash_bytes(content) + '.md')
        target.write_bytes(content)
        result = {'server_sha256': hash_bytes(target.read_bytes()), 'bytes': len(content),
            'filename_intent': payload['filename'], 'native_save_claim': False}
        write_json(root / 'records' / 'blob-proof.json', result)
        return result
    @app.app.post(CONTROL_PREFIX + '/evidence')
    async def evidence(request: app.Request):
        auth(request)
        raw = await request.body()
        if len(raw) > 131072: raise HTTPException(413)
        try:
            value = validate_observation(json.loads(raw), (nonce, app.session_token))
        except ValueError:
            raise HTTPException(400, 'Bounded observation refused') from None
        write_json(root / 'records' / ('observation-' + uuid.uuid4().hex + '.json'), value)
        return {'recorded': True}
    @app.app.post(CONTROL_PREFIX + '/control')
    async def control(request: app.Request):
        auth(request)
        raw = await request.body()
        if len(raw) > 2048: raise HTTPException(413)
        body = json.loads(raw)
        if set(body) != {'action'} or body['action'] not in CONTROL_ACTIONS: raise HTTPException(400)
        action = body['action']; state['actions'].append({'action': action, 'at': time.time()})
        if action == 'seed':
            if not app.api_seat_manager.attempts:
                app.api_seat_manager.launch('artifact-fixture', 'cli')
                app.api_seat_manager.launch('artifact-fixture', 'api')
            owners = {}
            for seat in ('cli', 'api'):
                item = app.api_seat_manager.attempts['artifact-fixture/' + seat]
                matches = [row for row in app.registry.get_all().values() if row['base'] == item['base'] and row['state'] == 'active']
                if len(matches) != 1 or not app.api_seat_manager.artifact_producer(matches[0])['available']:
                    return {'ready': False}
                owners[seat] = matches[0]
            if not state['sessions']:
                for seat in ('cli', 'api'):
                    row = seed_session(app, owners[seat], 'document-' + seat)
                    state['sessions'][seat] = {'id': row['id'], 'run_id': row['run_id'], 'channel': row['channel']}
                for label, owner, state_name in [('absent', {'name': 'Absent author', 'identity_id': 'f'*32}, 'complete'),
                                                  ('active', owners['api'], 'active')]:
                    row = seed_session(app, owner, 'absent-author' if label == 'absent' else 'active-source', state_name)
                    state['sessions'][label] = {'id': row['id'], 'run_id': row['run_id'], 'channel': row['channel']}
            return {'ready': True, 'sessions': state['sessions']}
        if action == 'release_cli': (root / 'records/cli-release').write_text('release', encoding='utf-8')
        elif action.startswith('hold_') and action[5:] in gates: gates[action[5:]].clear()
        elif action.startswith('release_') and action[8:] in gates: gates[action[8:]].set()
        elif action == 'capability_off': runtime_protocol.SUPPORTED_CAPABILITIES = ()
        elif action == 'capability_on': runtime_protocol.SUPPORTED_CAPABILITIES = ('artifact-v1',)
        elif action == 'hold_authoring':
            state.setdefault('authoring_bytes', app.artifacts.path.read_bytes())
            app.artifacts.path.write_text('{broken owned fixture', encoding='utf-8')
        elif action == 'restore_authoring':
            if 'authoring_bytes' not in state: raise HTTPException(409)
            app.artifacts.path.write_bytes(state.pop('authoring_bytes'))
        elif action == 'restore_faults': fault.update(read=False, proxy=False, poll=False)
        elif action == 'fail_read': fault['read'] = True
        elif action == 'proxy_download': fault['proxy'] = True
        elif action == 'poll_failure': fault['poll'] = True
        elif action == 'finish':
            # An operator completion marker is never evidence of all cases passing.
            state['finished'] = True
            write_json(root / 'browser-done.json', {'finished': True})
        elif action == 'shutdown':
            gates['api'].set(); gates['create'].set()
            (root / 'records/cli-release').write_text('release', encoding='utf-8')
            app.api_seat_manager.shutdown()
            for item in servers: item.should_exit = True
        return {'ok': True}
    # Middleware is fixture-only and explicitly recorded. Real artifact routing
    # executes unchanged for all healthy operations.
    @app.app.middleware('http')
    async def fixture_page(request, call_next):
        path = request.url.path
        if path == '/':
            html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
            html, replacements = re.subn(r'<script[^>]+src="https://[^\"]+marked[^\"]*"[^>]*></script>',
                '<script>window.marked={parse:s=>String(s).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")};</script>', html)
            if replacements != 1: raise RuntimeError('CDN shim anchor changed')
            script = '<script>window.__SESSION_TOKEN__=' + json.dumps(app.session_token) + ';</script>'
            html = html.replace('</head>', script + '<script>' + browser_observer(nonce) + '</script></head>')
            origin = owned_origin('http://127.0.0.1:' + str(ports[0]), ports)
            return HTMLResponse(html, headers={'Cache-Control': 'no-store',
                'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src " + origin + ' ws://127.0.0.1:' + str(ports[0]) + "; object-src 'none'; base-uri 'none'"})
        if path.startswith('/api/artifacts/'):
            if fault['proxy'] and path.endswith('/download'):
                fault['proxy'] = False; return HTMLResponse('<html>Fixture proxy failure</html>')
            if fault['read'] and path.endswith('/document'):
                fault['read'] = False; return Response(status_code=503)
            if fault['poll'] and '/requests/' in path and not path.endswith(('/document', '/cancel')):
                return Response(status_code=503)
        return await call_next(request)
    import uvicorn
    servers = []
    original_init = uvicorn.Server.__init__
    def remember(self, *args, **kwargs):
        original_init(self, *args, **kwargs); servers.append(self)
    uvicorn.Server.__init__ = remember
    original_run = uvicorn.run
    def quiet_run(*args, **kwargs):
        # Product WebSocket URL contains an operator token. Never log that URL.
        kwargs.update(access_log=False, log_level='warning')
        return original_run(*args, **kwargs)
    uvicorn.run = quiet_run
    try:
        import run
        sys.argv = ['run.py']
        run.main()
    finally:
        gates['api'].set(); gates['create'].set()
        if app.api_seat_manager: app.api_seat_manager.shutdown()
        provider.shutdown(); provider.server_close()


class Fixture:
    """Explicit construction only after executable review; import has no effects."""
    def __init__(self):
        from tools.verify_channel_lifecycle import trusted_bootstrap_manifest, repository_head
        self.trusted = trusted_bootstrap_manifest()
        self.pin = repository_head()
        self.hashes = {name: hash_bytes((ROOT / name).read_bytes()) for name in PIN_FILES}
        if 'SUPPORTED_CAPABILITIES = ()' not in (ROOT / 'runtime_protocol.py').read_text(encoding='utf-8'):
            raise ValueError('Source capability must stay empty')
        scratch = ROOT / '.audit-tmp'; scratch.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='artifact-ui-', dir=scratch))
        self.process = None; self.handle = None; self.birth = None
        self.started = time.monotonic(); self.deadline = self.started + 1200
        self.observations = []; self.cleanup = None
        self.nonce = uuid.uuid4().hex; self.token = ''
        for directory in ('data', 'uploads', 'profiles', 'records', 'audit', 'downloads', 'bootstrap'):
            (self.root / directory).mkdir()
        handles = []
        try:
            for _ in range(4):
                handle = socket.socket(); handles.append(handle); handle.bind(('127.0.0.1', 0))
            self.ports = [handle.getsockname()[1] for handle in handles]
            forbidden_ports = set(FORBIDDEN_PORTS)
            forbidden = [str(ROOT / 'data'), str(ROOT / '.agentchattr')]
            # The interpreter lives in the original checkout, outside this worktree.
            original_checkout = Path(sys.prefix).parent
            forbidden += [str(original_checkout / item) for item in ('data', 'uploads', '.agentchattr')]
            original_home = Path.home()
            forbidden += [str(original_home / item) for item in ('.claude', '.codex', '.gemini', '.config', '.agentchattr')]
            import tomllib
            self.config_hashes = {}
            for name in ('config.toml', 'config.local.toml'):
                path = ROOT / name
                if path.exists():
                    raw = path.read_bytes(); self.config_hashes[name] = hash_bytes(raw)
                    value = tomllib.loads(raw.decode('utf-8'))
                    if value.get('server', {}).get('data_dir'): forbidden.append(str((ROOT / value['server']['data_dir']).resolve()))
                    for group, key in (('server', 'port'), ('mcp', 'http_port'), ('mcp', 'sse_port')):
                        if type(value.get(group, {}).get(key)) is int: forbidden_ports.add(value[group][key])
            if len(set(self.ports)) != 4 or set(self.ports) & forbidden_ports:
                raise ValueError('Port freeze collides with configured/live ports')
            for key in ('APPDATA', 'LOCALAPPDATA'):
                if os.environ.get(key):
                    forbidden += [str(Path(os.environ[key]) / x) for x in ('Claude', 'Codex', 'Gemini', 'agentchattr')]
            policy = {'forbidden_roots': forbidden, 'forbidden_ports': sorted(forbidden_ports),
                'allowed_python_roots': [str(ROOT), str(self.root), sys.prefix, sys.base_prefix],
                'guard_sha256': self.hashes['tools/channel_guard.py']}
            self.env = safe_env(os.environ, self.root, self.ports, self.nonce, policy)
            for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME'):
                Path(self.env[key]).mkdir()
            write_json(self.root / 'private.json', {'nonce': self.nonce, 'ports': self.ports,
                'config': literal_config(self.root, self.ports)})
            (self.root / 'bootstrap/sitecustomize.py').write_text(bootstrap_source(), encoding='utf-8')
            write_json(self.root / 'manifest.json', {'pin': self.pin, 'hashes': self.hashes,
                'ports': self.ports, 'trusted_bootstrap': self.trusted, 'lease_seconds': 1200,
                'native_download_default_intercepted': True})
        finally:
            for handle in handles: handle.close()
        self.base = 'http://127.0.0.1:' + str(self.ports[0])

    def api(self, action=None):
        import urllib.request
        path = CONTROL_PREFIX + ('/control' if action else '/state')
        request = urllib.request.Request(self.base + path,
            data=json.dumps({'action': action}).encode() if action else None,
            headers={'X-Session-Token': self.token, 'X-Fixture-Nonce': self.nonce, 'Content-Type': 'application/json'})
        with local_request(request, timeout=30) as response:
            value = json.load(response)
        self.observations.append(public_evidence({'action': action, 'value': value}, (self.nonce, self.token)))
        return value

    def start(self):
        with (self.root / 'server.log').open('wb') as log:
            self.process = subprocess.Popen([sys.executable, '-u', str(Path(__file__)), '--serve'],
                cwd=ROOT, env=self.env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        end = time.monotonic() + 90
        import urllib.request
        while time.monotonic() < end:
            if self.process.poll() is not None: raise RuntimeError('Guarded fixture server exited; retained log')
            try:
                private = read_json(self.root / 'private.json'); self.token = private['token']
                with local_request(self.base + '/preflight', timeout=2) as response:
                    if response.status == 200: break
            except (OSError, ValueError, KeyError): time.sleep(.1)
        else: raise TimeoutError('Guarded startup deadline')
        rows = [read_json(path) for path in (self.root / 'audit').glob('artifact-bootstrap-*.json')]
        candidates = [row['birth'] for row in rows if row['birth']['pid'] != os.getpid()]
        if len(candidates) != 1: raise ValueError('Initial server birth not unique')
        from process_identity import open_verified_process
        self.birth = candidates[0]
        result = open_verified_process(self.birth)
        if result['status'] != 'live' or result['process'] is None: raise ValueError('Server birth unverified')
        self.handle = result['process']
        end = min(self.deadline, time.monotonic() + 90)
        while time.monotonic() < end:
            if self.api('seed')['ready']: break
            time.sleep(.25)
        else: raise TimeoutError('Real managed CLI/API readiness deadline')
        write_json(self.root / 'lease.json', {'expires_at': time.time() + max(0, self.deadline-time.monotonic())})
        write_json(self.root / 'READY.json', {'url': self.base, 'root': str(self.root), 'pin': self.pin,
            'lease_seconds': 1200, 'status': 'fixture-ready-browser-not-yet-driven'})
        print(json.dumps(read_json(self.root / 'READY.json')), flush=True)

    def close(self):
        unresolved = []
        cleanup_deadline = time.monotonic() + 90
        try:
            if self.token: self.api('shutdown')
        except Exception as error: unresolved.append({'stage': 'cooperative-shutdown', 'error': type(error).__name__})
        from process_identity import open_verified_process
        births = []
        for path in (self.root / 'audit').glob('artifact-bootstrap-*.json'):
            births.append(read_json(path)['birth'])
        # Child first, server last. Each fresh open compares PID+creation+image.
        for birth in sorted(births, key=lambda row: row == self.birth):
            try:
                value = open_verified_process(birth)
                handle = value['process']
                if value['status'] == 'absent': continue
                if handle is None: raise ValueError('Owned process identity unresolved')
                try:
                    if handle.poll() is None:
                        try: handle.wait(timeout=min(3, max(0, cleanup_deadline-time.monotonic())))
                        except subprocess.TimeoutExpired:
                            handle.terminate(); handle.wait(timeout=min(10, max(0, cleanup_deadline-time.monotonic())))
                finally: handle.close()
            except Exception as error: unresolved.append({'pid': birth['pid'], 'error': type(error).__name__})
        if self.handle: self.handle.close()
        if self.process:
            try: self.process.wait(timeout=10)
            except subprocess.TimeoutExpired: unresolved.append({'stage': 'launcher-wait'})
        try:
            guards = [read_json(path) for path in (self.root / 'audit').glob('guard-*.json')]
            if not guards or any(row['real_attempts'] for row in guards): raise ValueError('Guard violations/missing evidence')
            if not {row['pid'] for row in guards}.issuperset(row['pid'] for row in births):
                raise ValueError('A child has no corresponding guard evidence')
            if list((self.root / 'audit').glob('unowned-port-*.json')): raise ValueError('Owned-port guard violation')
            if self.hashes != {name: hash_bytes((ROOT / name).read_bytes()) for name in PIN_FILES}: raise ValueError('Frozen source changed')
            from tools.verify_channel_lifecycle import trusted_bootstrap_manifest
            if self.trusted != trusted_bootstrap_manifest(): raise ValueError('Trusted bootstrap changed')
            for name, digest in self.config_hashes.items():
                if hash_bytes((ROOT / name).read_bytes()) != digest: raise ValueError('Repository config changed')
        except Exception as error: unresolved.append({'stage': 'evidence', 'error': type(error).__name__})
        self.cleanup = {'unresolved': unresolved, 'births_visited': len(births), 'retained_root': str(self.root),
            'browser_and_forwards': 'controller must separately record closed owned browser and forward ids'}
        write_json(self.root / 'cleanup.json', public_evidence(self.cleanup, (self.token, self.nonce)))
        return not unresolved


def external_control(root, action):
    """Owned gate operation without putting token/nonce into tool args/output."""
    root = Path(root).resolve()
    if not root.is_relative_to((ROOT / '.audit-tmp').resolve()) or not root.name.startswith('artifact-ui-'):
        raise ValueError('Foreign fixture root refused')
    if action not in CONTROL_ACTIONS | {'state'}:
        raise ValueError('Fixed fixture action required')
    manifest = read_json(root / 'manifest.json')
    if any(hash_bytes((ROOT / name).read_bytes()) != value for name, value in manifest['hashes'].items()):
        raise ValueError('Source/tool freeze changed')
    if time.time() > read_json(root / 'lease.json')['expires_at']:
        raise ValueError('Fixture lease expired')
    private = read_json(root / 'private.json')
    origin = owned_origin('http://127.0.0.1:' + str(private['ports'][0]), manifest['ports'])
    from urllib.request import Request
    request = Request(origin + CONTROL_PREFIX + ('/state' if action == 'state' else '/control'),
        data=None if action == 'state' else json.dumps({'action': action}).encode(),
        headers={'X-Session-Token': private['token'], 'X-Fixture-Nonce': private['nonce'], 'Content-Type': 'application/json'})
    with local_request(request, timeout=30) as response: value = json.load(response)
    return public_evidence(value, (private['token'], private['nonce']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--compile-only', action='store_true')
    modes.add_argument('--run', action='store_true')
    modes.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    modes.add_argument('--control', choices=sorted(CONTROL_ACTIONS | {'state'}))
    parser.add_argument('--fixture-root', type=Path)
    args = parser.parse_args()
    if args.compile_only:
        compile(bootstrap_source(), '<owned-sitecustomize>', 'exec')
        for name in ('tools/verify_artifact_ui.py', 'tools/fake_artifact_client.py', 'tools/test_artifact_ui_harness_controls.py'):
            compile((ROOT / name).read_text(encoding='utf-8'), name, 'exec')
        print('Compile only: no fixture/listener/process/profile constructed')
        return
    if args.serve:
        try: require_guard()
        except RuntimeError: raise SystemExit(91) from None
        runtime_server(); return
    if args.control:
        if args.fixture_root is None: parser.error('--control requires --fixture-root')
        print(json.dumps(external_control(args.fixture_root, args.control))); return
    fixture = Fixture()
    success = False
    try:
        fixture.start()
        while time.monotonic() < fixture.deadline:
            if (fixture.root / 'browser-done.json').exists():
                success = True; break
            if fixture.process.poll() is not None: raise RuntimeError('Server exited before controller completion')
            time.sleep(.25)
    finally:
        clean = fixture.close()
        receipt = {'pin': fixture.pin, 'hashes': fixture.hashes, 'observations': fixture.observations,
            'browser_observations': [read_json(path) for path in (fixture.root / 'records').glob('observation-*.json')],
            'controller_finished': success, 'cleanup': fixture.cleanup, 'acceptance_claim': False,
            'reason': 'reviewer must assess controller evidence and every required case; finish is not a pass'}
        write_json(fixture.root / 'receipt.json', public_evidence(receipt, (fixture.token, fixture.nonce)))
        print(json.dumps({'receipt': str(fixture.root / 'receipt.json'), 'cleanup_ok': clean}), flush=True)


if __name__ == '__main__':
    main()
