"""Draft fast cold HTTP reconnection, zero turns/models, exact retained handles only.

The parent fake provider survives two isolated server incarnations. No process
tree operations or PID-name search. Execution requires coordinator readiness.
"""
import ctypes
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
from process_identity import open_verified_process


def main():
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Actual Windows fast reconnect fixture required.'}))
        return
    calls = []
    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(True)
            self.send_response(500)
            self.end_headers()
        def log_message(self, *args):
            pass
    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='runtime reconnect integration ', dir=scratch))
    data, console_path = temporary / 'data', temporary / 'console.json'
    secret, private_source = 'PRIVATE_RECONNECT_CREDENTIAL', 'PRIVATE_RECONNECT_PROVIDER_SOURCE'
    fake_cli = f'''import ctypes,json,os,sys
from pathlib import Path
sys.path.insert(0,{str(ROOT)!r})
from process_identity import capture_birth
from api_seats import atomic_json
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetConsoleWindow.restype=ctypes.c_void_p
w=k.GetConsoleWindow()
u=ctypes.WinDLL('user32',use_last_error=True)
u.IsWindowVisible.argtypes=[ctypes.c_void_p]
atomic_json(Path({str(console_path)!r}),{{'birth':capture_birth(),'console_present':bool(w),'console_window':int(w or 0),
    'console_visible':bool(u.IsWindowVisible(w)) if w else False}})
sys.stdin.read()
'''
    cli_argument = 'exec(' + repr(fake_cli) + ')'
    sockets = [socket.socket() for _ in range(3)]
    for handle in sockets:
        handle.bind(('127.0.0.1', 0))
    ports = [handle.getsockname()[1] for handle in sockets]
    for handle in sockets:
        handle.close()
    base = f'http://127.0.0.1:{ports[0]}'
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(data), AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'),
                       RECONNECT_FIXTURE_KEY=secret)
    code = f'''import config_loader,sys,os
from pathlib import Path
from api_seats import atomic_json
from process_identity import capture_birth
# This self-birth is available even if later configure/startup fails.
atomic_json(Path({str(temporary)!r})/('server-'+os.environ['RECONNECT_STAGE']+'.json'),capture_birth())
spawn_events=[]
def audit(event,args):
    if event=='subprocess.Popen':
        spawn_events.append(True)
sys.addaudithook(audit)
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['agents']={{'fake-api':{{'type':'api','base_url':'http://127.0.0.1:{provider.server_port}/v1',
        'system_prompt':{private_source!r},'api_key_env':'RECONNECT_FIXTURE_KEY'}},
        'fake-cli':{{'command':{sys.executable!r},'cwd':{str(temporary)!r},'cli_args':['-u','-c',{cli_argument!r}],
        'mcp_inject':'env','mcp_env_var':'RECONNECT_FAKE_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
@app.app.get('/api/fixture/reconnect-state')
async def fixture_state():
    manager=app.api_seat_manager
    with manager.lock:
        workers={{}}
        for key,value in manager.attempts.items():
            instance=next((item for item in app.registry.get_all().values()
                if item.get('base')==value.get('base')),None)
            if instance:
                workers[key]={{'attempt':value['id'],'identity_id':instance['identity_id'],
                    'process_kind':type(value['process']).__name__,'process_pid':value['process'].pid,
                    'readiness':manager.restart_readiness(instance['identity_id'],manager.boot_id)}}
        return {{'boot_id':manager.boot_id,'server_birth':capture_birth(),
                'spawn_count':len(spawn_events),'workers':workers}}
import run
run.main()
'''
    servers, worker_handles, client_handle = [], {}, None
    current_api, result, initial, runtime_paths = None, None, None, {}

    def retain(birth):
        probe = open_verified_process(birth)
        assert probe['status'] == 'live' and probe['process'] is not None, probe
        return probe['process']

    def wait_for(check, label, timeout=35):
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

    def start_server(stage):
        env = dict(environment, RECONNECT_STAGE=stage)
        with (temporary / ('server-' + stage + '.log')).open('wb') as output:
            launcher = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=env,
                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        item = {'stage': stage, 'launcher': launcher, 'handle': None}
        servers.append(item)
        birth = wait_for(lambda: json.loads((temporary / ('server-' + stage + '.json')).read_text('utf-8')),
                         'actual server self-birth ' + stage, timeout=10)
        item['birth'], item['handle'] = birth, retain(birth)
        def page():
            assert launcher.poll() is None, 'server launcher exited during startup'
            with urllib.request.urlopen(base + '/preflight', timeout=1) as response:
                return response.read().decode('utf-8-sig')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', wait_for(page, 'HTTP ready ' + stage)).group(1)
        def api(path, body=None):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                headers={'x-session-token': token, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)
        return item, api

    def both_ready(api):
        value = api('/api/fixture/reconnect-state')
        keys = {'reconnect-team/api', 'reconnect-team/cli'}
        return value if keys <= value['workers'].keys() and all(
            value['workers'][key]['readiness']['state'] == 'ready' and
            value['workers'][key]['readiness']['process_verified'] is True for key in keys) else None

    try:
        first, current_api = start_server('first')
        common = {'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        package = {'id': 'reconnect-team', 'name': 'Fast reconnect fixture', 'seats': [
            dict(common, id='api', name='API', adapter='openai-compatible', provider='fake-api', secret_ref='RECONNECT_FIXTURE_KEY'),
            dict(common, id='cli', name='CLI', adapter='cli', provider='fake-cli')]}
        current_api('/api/preflight/packages', package)
        revision = current_api('/api/preflight/seats')['package_revisions']['reconnect-team']
        current_api('/api/preflight/packages/reconnect-team/launch', {'revision': revision})
        initial = wait_for(lambda: both_ready(current_api), 'initial actual HTTP boot proofs')
        assert initial['server_birth'] == first['birth']
        assert initial['spawn_count'] == 2 and calls == []
        for seat in ('api', 'cli'):
            key = 'reconnect-team/' + seat
            view = initial['workers'][key]
            assert view['process_kind'] == 'Popen'
            directory = data / 'api_seat_runtime' / view['attempt']
            birth = json.loads((directory / 'birth.json').read_text('utf-8'))
            worker_handles[seat] = retain(birth)
            runtime_paths[seat] = directory
            assert worker_handles[seat].pid == birth['pid']
        console = wait_for(lambda: json.loads(console_path.read_text('utf-8')), 'owned native CLI self-birth')
        assert console['console_present'] and not console['console_visible']
        client_handle = retain(console['birth'])
        immutable = {path: path.read_bytes() for directory in runtime_paths.values()
                     for path in (directory / 'config.json', directory / 'launch.json', directory / 'birth.json')}
        directories = {path.name for path in (data / 'api_seat_runtime').iterdir() if path.is_dir()}
        assert len(directories) == 2

        # Only the positively verified REAL server handle is terminated. Its
        # venv launcher PID is neither assumed to be the server nor tree-killed.
        crash_at = time.monotonic()
        first['handle'].terminate()
        first['handle'].wait(timeout=8)
        first['launcher'].wait(timeout=8)
        assert all(handle.poll() is None for handle in worker_handles.values())
        assert client_handle.poll() is None and calls == []
        second, current_api = start_server('second')
        http_ready_ms = (time.monotonic() - crash_at) * 1000
        assert http_ready_ms < 15000, 'did not exercise the required fast downtime window'
        restored = wait_for(lambda: both_ready(current_api), 'cold fresh-boot worker proofs', timeout=25)
        proof_ms = (time.monotonic() - crash_at) * 1000
        assert restored['server_birth'] == second['birth']
        assert restored['boot_id'] != initial['boot_id']
        assert restored['spawn_count'] == 0, 'cold manager spawned instead of reconciling original owners'
        for seat in ('api', 'cli'):
            key = 'reconnect-team/' + seat
            old, new = initial['workers'][key], restored['workers'][key]
            assert new['attempt'] == old['attempt'] and new['identity_id'] == old['identity_id']
            assert new['process_kind'] == 'OwnedProcessHandle'
            assert new['process_pid'] == worker_handles[seat].pid
            assert worker_handles[seat].poll() is None
        assert {path.name for path in (data / 'api_seat_runtime').iterdir() if path.is_dir()} == directories
        assert all(path.read_bytes() == original for path, original in immutable.items())
        assert json.loads(console_path.read_text('utf-8')) == console
        assert client_handle.poll() is None and calls == []
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.IsWindow.argtypes = [ctypes.c_void_p]
        user.IsWindowVisible.argtypes = [ctypes.c_void_p]
        assert user.IsWindow(console['console_window'])
        assert not user.IsWindowVisible(console['console_window']), 'original surviving console became visible'
        assert not (data / 'session_runs.json').exists()
        public = json.dumps(restored)
        assert secret not in public and private_source not in public
        result = {'result': 'PASS', 'http_restart_window_ms': round(http_ready_ms, 3),
                  'fresh_boot_proofs_ms': round(proof_ms, 3), 'same_original_workers': 2,
                  'cold_spawn_count': 0, 'provider_calls': 0, 'immutable_attempts': True,
                  'hidden_original_cli_survived': True, 'scope': 'fast_idle_runtime_reconnection_only',
                  'scratch': str(temporary)}
    finally:
        unresolved = []
        # Endpoints have first opportunity to stop the exact adopted attempts.
        if current_api is not None:
            for seat in ('api', 'cli'):
                try:
                    current_api('/api/preflight/seats/reconnect-team/' + seat + '/stop', {})
                except OSError:
                    pass
        # Failure cleanup uses ONLY handles retained before the deliberate crash.
        # Request worker-owned child cleanup before any fallback worker ending.
        if 'cli' in runtime_paths:
            atomic_json(runtime_paths['cli'] / 'stop.json', {'attempt': runtime_paths['cli'].name})
        cli_child_ended = False
        if client_handle is not None:
            try:
                client_handle.wait(timeout=8)
            except subprocess.TimeoutExpired:
                client_handle.terminate()
                client_handle.wait(timeout=8)
            cli_child_ended = True
        for seat, handle in worker_handles.items():
            try:
                handle.wait(timeout=8)
            except subprocess.TimeoutExpired:
                if seat == 'cli' and not cli_child_ended:
                    unresolved.append('CLI worker retained: native client exit was not proven')
                    continue
                # CLI fallback requires the retained native child's observed
                # exit. API has no queued turn/model child in this fixture.
                handle.terminate()
                handle.wait(timeout=8)
        for server in reversed(servers):
            if server['handle'] is not None:
                if server['handle'].poll() is None:
                    server['handle'].terminate()
                server['handle'].wait(timeout=8)
            server['launcher'].wait(timeout=8)
        for handle in [client_handle, *worker_handles.values(), *(value['handle'] for value in servers)]:
            if handle is not None:
                handle.close()
        provider.shutdown()
        provider.server_close()
        assert not unresolved, 'Unresolved owned cleanup; no unverified child actuation: ' + '; '.join(unresolved)
        if result:
            for seat, directory in runtime_paths.items():
                receipt = json.loads((directory / 'receipt.json').read_text('utf-8'))
                assert receipt['state'] == 'stopped'
                if seat == 'cli':
                    assert type(receipt['child_exit_code']) is int
            result['actual_worker_exits_observed'] = len(worker_handles)
            result['actual_server_exits_observed'] = len(servers)
    if result:
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
