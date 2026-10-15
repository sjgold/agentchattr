"""End-to-end ticket #3 check using an isolated app and a loopback fake provider."""
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
from launcher import stop_owned_child


def main():
    captures = []
    behavior = {'auth_error': False}
    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            captures.append(request)
            if self.headers.get('Authorization') != 'Bearer fake-test-only-value':
                self.send_response(403)
                self.end_headers()
                return
            if behavior['auth_error']:
                self.send_response(401)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'model': 'fake-provider-confirmed',
                'choices': [{'message': {'content': 'Fake provider reply.'}}]}).encode())
        def log_message(*args):
            pass
    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    child = None
    api = None
    try:
        temporary = tempfile.mkdtemp(prefix="api seat integration ", dir=scratch)
        sockets = [socket.socket() for _ in range(3)]
        for handle in sockets:
            handle.bind(('127.0.0.1', 0))
        ports = [handle.getsockname()[1] for handle in sockets]
        for handle in sockets:
            handle.close()
        environment = os.environ.copy()
        environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
        environment.update(AGENTCHATTR_DATA_DIR=str(Path(temporary) / 'data'),
                           AGENTCHATTR_UPLOAD_DIR=str(Path(temporary) / 'uploads'),
                           TICKET3_FAKE_URL=f'http://127.0.0.1:{provider.server_port}/v1',
                           TICKET3_FAKE_SECRET='fake-test-only-value')
        code = '''import os,config_loader
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['agents']={'fake': {'type':'api','base_url':os.environ['TICKET3_FAKE_URL'],
        'label':'Fake provider','model':'fake-default','api_key_env':'TICKET3_FAKE_SECRET',
        'reasoning_efforts':['high']}}
    return cfg
config_loader.load_config=isolated
import asyncio,api_seat_runtime
original_spawn=api_seat_runtime.subprocess.Popen
def debug_spawn(command, **options):
    if '--seat-file' in command:
        snapshot=command[command.index('--seat-file')+1]
        from pathlib import Path
        with Path(snapshot).with_name('fake-wrapper-debug.log').open('ab') as output:
            options.update(stdout=output, stderr=-2)
            return original_spawn(command, **options)
    return original_spawn(command, **options)
api_seat_runtime.subprocess.Popen=debug_spawn
import run
run.main()
'''
        with (Path(temporary) / 'server.log').open('wb') as output:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        base = f'http://127.0.0.1:{ports[0]}'
        def wait_for(function, label, timeout=20):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise AssertionError('isolated server exited; inspect its temporary server log')
                try:
                    value = function()
                    if value:
                        return value
                except (OSError, KeyError):
                    pass
                time.sleep(0.1)
            raise AssertionError('deadline waiting for ' + label)
        def page():
            with urllib.request.urlopen(base + '/preflight', timeout=2) as response:
                return response.read().decode('utf-8-sig')
        html = wait_for(page, 'preflight')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', html).group(1)
        def api(path, body=None):
            request = urllib.request.Request(base + path, headers={'x-session-token': token, 'Content-Type': 'application/json'},
                data=json.dumps(body).encode() if body is not None else None)
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)
        def send_human(text):
            from websockets.sync.client import connect
            with connect(base.replace('http://', 'ws://') + '/ws?token=' + token, proxy=None) as connection:
                connection.send(json.dumps({'type': 'message', 'sender': 'test-human', 'text': text, 'channel': 'general'}))
                connection.recv(timeout=5)
        seat = {'id': 'one', 'name': 'First fake seat', 'adapter': 'openai-compatible', 'provider': 'fake',
                'model': 'requested-one', 'reasoning': 'high', 'launch_profile': 'standard', 'secret_ref': 'TICKET3_FAKE_SECRET'}
        package = {'id': 'fake-team', 'name': 'Fake test team', 'seats': [seat, {**seat, 'id': 'two', 'name': 'Second fake seat', 'model': 'requested-two'}]}
        api('/api/preflight/packages', package)
        def state(which):
            result = api('/api/preflight/seats')['runtime'].get('fake-team/' + which, {})
            if result.get('state') == 'failed':
                raise AssertionError('Fake-seat runtime failed: ' + str(result.get('error')) + '; scratch: ' + temporary)
            return result
        launch_path = '/api/preflight/seats/fake-team/'
        first_attempt = api(launch_path + 'one/launch', {})['attempt']
        api(launch_path + 'two/launch', {})
        wait_for(lambda: state('one').get('state') == 'ready' and state('two').get('state') == 'ready', 'both wrappers ready')
        assert not captures, 'launch called the provider'
        assert state('one')['confirmed_model'] is None
        assert api(launch_path + 'one/launch', {})['attempt'] == first_attempt
        first_name = state('one')['name']
        second_name = state('two')['name']
        assert first_name != second_name
        send_human('@' + first_name + ' reply with test text')
        wait_for(lambda: state('one').get('confirmed_model') == 'fake-provider-confirmed', 'provider receipt')
        assert captures[0]['model'] == 'requested-one'
        assert captures[0]['reasoning_effort'] == 'high'
        assert state('one')['requested_model'] == 'requested-one'
        assert state('one')['authentication'] == 'verified'
        api(launch_path + 'one/stop', {})
        stopped_receipt = Path(temporary) / 'data/api_seat_runtime' / first_attempt / 'receipt.json'
        assert json.loads(stopped_receipt.read_text())['state'] == 'stopped', 'actual wrapper did not acknowledge stop'
        assert state('two')['state'] == 'ready'
        package['seats'][1]['model'] = 'changed-two'
        api('/api/preflight/packages', package)
        try:
            api(launch_path + 'two/launch', {})
            raise AssertionError('mismatched active seat reused')
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        api(launch_path + 'two/launch', {'restart': True})
        wait_for(lambda: state('two').get('state') == 'ready', 'targeted restart')
        assert state('two')['requested_model'] == 'changed-two'
        assert state('two')['confirmed_model'] is None
        behavior['auth_error'] = True
        send_human('@' + state('two')['name'] + ' test failure')
        wait_for(lambda: state('two').get('state') == 'action_required', 'authentication failure')
        assert state('two')['authentication'] == 'failed'
        behavior['auth_error'] = False
        api(launch_path + 'two/launch', {'restart': True})
        wait_for(lambda: state('two').get('state') == 'ready', 'targeted retry')
        assert state('one')['state'] == 'stopped'
        text = (Path(temporary) / 'data/api_seats.json').read_text()
        for path in (Path(temporary) / 'data/api_seat_runtime').rglob('*.json'):
            text += path.read_text()
        assert 'fake-test-only-value' not in text
        assert token not in text
        print(json.dumps({'result': 'PASS', 'url': base + '/preflight', 'seats': 2,
            'provider_calls_before_dispatch': 0, 'payload_model': captures[0]['model'],
            'confirmed_model': 'fake-provider-confirmed', 'targeted_restart_retry_stop': True,
            'worker_stop_acknowledged': True,
            'secret_values_persisted': False}), flush=True)
        if '--serve' in sys.argv:
            input('Press Enter to stop the isolated API-seat test server: ')
        for which in ('one', 'two'):
            api(launch_path + which + '/stop', {})
    finally:
        if api is not None and child is not None and child.poll() is None:
            for which in ('one', 'two'):
                try:
                    api('/api/preflight/seats/fake-team/' + which + '/stop', {})
                except OSError:
                    pass
        if child is not None:
            stop_owned_child(child)
        provider.shutdown()
        provider.server_close()


if __name__ == '__main__':
    main()
