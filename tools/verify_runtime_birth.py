"""Real isolated worker self-birth/manifest evidence, without model calls or adoption."""
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
from launcher import stop_owned_child
from process_identity import open_verified_process


def main():
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Actual Windows worker/hidden console proof required.'}))
        return
    captures = []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            captures.append(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            self.send_response(500)
            self.end_headers()

        def log_message(self, *args):
            pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='runtime birth integration ', dir=scratch))
    data = temporary / 'data'
    console_record = temporary / 'console.json'
    secret = 'PRIVATE_CREDENTIAL_VALUE_BIRTH_FIXTURE'
    source = 'PRIVATE_PROVIDER_SOURCE_BIRTH_FIXTURE'
    # Inline local fake client: record its inherited console visibility and wait
    # for the manager-owned worker to stop it. No MCP/tool/provider invocation.
    fake_cli = f'''import ctypes,json,os,sys
from pathlib import Path
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetConsoleWindow.restype=ctypes.c_void_p
window=kernel.GetConsoleWindow()
user=ctypes.WinDLL('user32',use_last_error=True)
user.IsWindowVisible.argtypes=[ctypes.c_void_p]
Path({str(console_record)!r}).write_text(json.dumps({{'pid':os.getpid(),'console_present':bool(window),
    'console_visible':bool(user.IsWindowVisible(window)) if window else False}}),encoding='utf-8')
sys.stdin.read()
'''
    fake_cli_argument = 'exec(' + repr(fake_cli) + ')'
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
                       BIRTH_FIXTURE_KEY=secret)
    code = f'''import config_loader,subprocess
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['agents']={{'fake-api':{{'type':'api','base_url':'http://127.0.0.1:{provider.server_port}/v1',
        'system_prompt':{source!r},'api_key_env':'BIRTH_FIXTURE_KEY'}},
        'fake-cli':{{'command':{sys.executable!r},'cwd':{str(temporary)!r},'cli_args':['-u','-c',{fake_cli_argument!r}],
        'mcp_inject':'env','mcp_env_var':'BIRTH_FAKE_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
@app.app.get('/api/fixture/birth-launchers')
async def fixture_launchers():
    with app.api_seat_manager.lock:
        return {{key:{{'launch_attempt':value['id'],'launcher_pid':value['process'].pid,
                      'process_object':id(value['process']),'original_popen':isinstance(value['process'],subprocess.Popen)}}
                for key,value in app.api_seat_manager.attempts.items() if value.get('process')}}
@app.app.get('/api/fixture/birth-readiness')
async def fixture_readiness():
    manager=app.api_seat_manager
    with manager.lock:
        statuses={{}}
        for key,value in manager.attempts.items():
            instance=next((item for item in app.registry.get_all().values()
                if item.get('base')==value.get('base')),None)
            if instance:
                statuses[key]={{'identity_id':instance['identity_id'],'launch_attempt':value['id'],
                    'readiness':manager.restart_readiness(instance['identity_id'],manager.boot_id)}}
        return {{'boot_id':manager.boot_id,'workers':statuses}}
import run
run.main()
'''
    child, api = None, None
    handles, evidence, result = [], {}, None
    try:
        with (temporary / 'server.log').open('wb') as output:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)

        def wait_for(check, label, timeout=35):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                assert child.poll() is None, 'isolated server exited; scratch: ' + str(temporary)
                try:
                    value = check()
                    if value:
                        return value
                except (OSError, KeyError, ValueError):
                    pass
                time.sleep(.1)
            raise AssertionError('deadline waiting for ' + label + '; scratch: ' + str(temporary))

        def page():
            with urllib.request.urlopen(base + '/preflight', timeout=2) as response:
                return response.read().decode('utf-8-sig')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', wait_for(page, 'preflight')).group(1)

        def api(path, body=None):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                headers={'x-session-token': token, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)

        common = {'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        package = {'id': 'birth-team', 'name': 'Birth evidence fixture', 'seats': [
            dict(common, id='api', name='API birth', adapter='openai-compatible', provider='fake-api', secret_ref='BIRTH_FIXTURE_KEY'),
            dict(common, id='cli', name='CLI birth', adapter='cli', provider='fake-cli')]}
        api('/api/preflight/packages', package)
        revision = api('/api/preflight/seats')['package_revisions']['birth-team']
        api('/api/preflight/packages/birth-team/launch', {'revision': revision})

        def ready_with_birth():
            status = api('/api/preflight/packages/birth-team/status')
            for seat, view in status['seats'].items():
                if view['state'] == 'ready':
                    path = data / 'api_seat_runtime' / view['attempt']
                    assert (path / 'birth.json').exists(), 'ready observed before durable self-birth: ' + seat
            return status if status['ready'] else None
        ready = wait_for(ready_with_birth, 'both actual workers ready with prior birth evidence')
        launchers = api('/api/fixture/birth-launchers')
        registry = json.loads((data / 'registry.json').read_text('utf-8'))['instances']
        immutable_files = {}
        for seat in ('api', 'cli'):
            attempt = ready['seats'][seat]['attempt']
            directory = data / 'api_seat_runtime' / attempt
            for filename in ('config.json', 'launch.json', 'birth.json'):
                immutable_files[directory / filename] = (directory / filename).read_bytes()
            snapshot = json.loads((directory / 'config.json').read_text('utf-8'))
            manifest = json.loads((directory / 'launch.json').read_text('utf-8'))
            birth = json.loads((directory / 'birth.json').read_text('utf-8'))
            identity = snapshot['ownership']
            assert manifest == {**identity, 'spawn_outcome': 'spawned'}
            assert identity['attempt'] == snapshot['attempt'] == birth['attempt'] == attempt
            assert identity['launch_key'] == 'birth-team/' + seat
            assert birth['base'] == snapshot['base'] == registry[ready['seats'][seat]['name']]['base']
            assert birth['ownership'] == identity
            assert identity['root_path'] == birth['worker_root'] == str(ROOT.resolve())
            assert identity['data_path'] == str(data.resolve())
            assert birth['platform'] == 'win32' and type(birth['pid']) is int
            assert type(birth['creation_filetime']) is str and int(birth['creation_filetime']) > 2 ** 53
            receipt = json.loads((directory / 'receipt.json').read_text('utf-8'))
            assert receipt['attempt'] == attempt and receipt['state'] == 'ready'
            assert (directory / 'birth.json').stat().st_mtime <= receipt['updated_at']
            probe = open_verified_process(birth)
            assert probe['status'] == 'live', probe
            handle = probe['process']
            handles.append((seat, handle))
            assert handle.pid == birth['pid'] and handle.poll() is None
            launcher = launchers['birth-team/' + seat]
            assert launcher['launch_attempt'] == attempt
            assert launcher['original_popen'] is True
            evidence[seat] = {'worker_pid': birth['pid'], 'launcher_pid': launcher['launcher_pid'],
                              'shim_differs': birth['pid'] != launcher['launcher_pid'], 'attempt': attempt}
            serialized = json.dumps([manifest, birth])
            for private in (secret, source, registry[ready['seats'][seat]['name']]['token']):
                assert private not in serialized, 'sensitive value leaked into ownership evidence'
        console = wait_for(lambda: json.loads(console_record.read_text('utf-8')), 'actual local fake client console record')
        assert console['console_present'] is True, 'fake native client lacks its intended console input contract'
        assert console['console_visible'] is False, 'managed native CLI console became visible'
        def actual_http_echo_ready():
            value = api('/api/fixture/birth-readiness')
            keys = {'birth-team/api', 'birth-team/cli'}
            return value if keys <= value['workers'].keys() and all(
                value['workers'][key]['readiness']['state'] == 'ready' and
                value['workers'][key]['readiness']['process_verified'] is True for key in keys) else None
        handshake = wait_for(actual_http_echo_ready, 'both actual workers echo current boot over HTTP and verify native birth')
        current_launchers = api('/api/fixture/birth-launchers')
        assert current_launchers == launchers, 'same-boot verification replaced the original Popen authority'
        for seat in ('api', 'cli'):
            status = handshake['workers']['birth-team/' + seat]
            assert status['identity_id'] == registry[ready['seats'][seat]['name']]['identity_id']
            assert status['launch_attempt'] == evidence[seat]['attempt']
            snapshot = json.loads((data / 'api_seat_runtime' / evidence[seat]['attempt'] / 'config.json').read_text('utf-8'))
            assert handshake['boot_id'] == snapshot['ownership']['boot_id']
        for path, original in immutable_files.items():
            assert path.read_bytes() == original, 'heartbeat rewrote immutable launch evidence: ' + path.name
        for private in (secret, source, *(value['token'] for value in registry.values())):
            assert private not in json.dumps(handshake), 'readiness endpoint exposed secret heartbeat data'
        assert captures == [], 'birth/readiness verification invoked local provider generation'
        assert not (data / 'session_runs.json').exists(), 'launch created a review run'
        result = {'result': 'PASS', 'worker_births_verified': 2, 'local_provider_calls': 0,
                  'hidden_cli_console': True, 'launcher_pid_not_assumed': evidence,
                  'actual_http_boot_echoes_verified': 2, 'same_boot_original_popen_retained': True,
                  'immutable_launch_evidence_unchanged': True,
                  'no_restart_or_adoption_claim': True, 'scratch': str(temporary)}
    finally:
        if api is not None and child is not None and child.poll() is None:
            for seat in ('api', 'cli'):
                try:
                    api('/api/preflight/seats/birth-team/' + seat + '/stop', {})
                except OSError:
                    pass
        if child is not None:
            stop_owned_child(child)
        exited = []
        for seat, handle in handles:
            try:
                handle.wait(timeout=8)
                exited.append(seat)
            finally:
                handle.close()
        provider.shutdown()
        provider.server_close()
        if result:
            assert set(exited) == {'api', 'cli'}
            for seat, info in evidence.items():
                receipt = json.loads((data / 'api_seat_runtime' / info['attempt'] / 'receipt.json').read_text('utf-8'))
                assert receipt['state'] == 'stopped' and receipt['adapter_connected'] is False
                if seat == 'cli':
                    assert type(receipt['child_exit_code']) is int
            result['actual_worker_exits_observed'] = len(exited)
            assert captures == []
    if result:
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
