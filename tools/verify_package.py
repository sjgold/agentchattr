"""Ticket #5 real-server mixed-package check with local fake API and CLI clients.

Run with the project Windows venv. --serve retains the isolated server after
PASS until .audit-tmp/ticket5-browser-stop.txt is created, for browser QA.
No provider or model service is called.
"""
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
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Real managed CLI console requires Windows.'}))
        return

    provider_calls = []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            provider_calls.append(self.rfile.read(int(self.headers['Content-Length'])))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"model":"fake-only","choices":[{"message":{"content":"fake"}}]}')

        def log_message(self, *args):
            pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='package integration ', dir=scratch))
    records = temporary / 'records'
    records.mkdir()
    fixture = str((ROOT / 'tools/fake_cli_seat.py').resolve())
    sockets = [socket.socket() for _ in range(3)]
    for handle in sockets:
        handle.bind(('127.0.0.1', 0))
    ports = [handle.getsockname()[1] for handle in sockets]
    for handle in sockets:
        handle.close()
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT',
                                 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(temporary / 'data'),
                       AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'),
                       TICKET4_SCRATCH_DIR=str(records),
                       TICKET5_FAKE_URL=f'http://127.0.0.1:{provider.server_port}/v1')
    environment.pop('TICKET5_MISSING_CREDENTIAL', None)
    code = f'''import config_loader,os
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['agents']={{'fake-api':{{'type':'api','base_url':os.environ['TICKET5_FAKE_URL'],
        'label':'Local fake API'}},
        'fake-cli':{{'command':{json.dumps(sys.executable)},'cwd':'.',
        'cli_args':[{json.dumps(fixture)}],
        'cli_model_args':['--model','{{model}}'],
        'cli_reasoning_args':['--reasoning','{{reasoning}}'],
        'reasoning_efforts':['high'],'mcp_inject':'env',
        'mcp_env_var':'TICKET4_FAKE_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import run
run.main()
'''
    child = None
    api = None
    base = f'http://127.0.0.1:{ports[0]}'
    package_id = 'mixed-team'
    package_path = f'/api/preflight/packages/{package_id}'
    stop_marker = scratch / 'ticket5-browser-stop.txt'
    url_marker = scratch / 'ticket5-browser-url.txt'

    try:
        with (temporary / 'server.log').open('wb') as output:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT,
                                     env=environment, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=subprocess.STDOUT)

        def wait_for(check, label, timeout=30):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise AssertionError('isolated server exited; inspect ' + str(temporary / 'server.log'))
                try:
                    value = check()
                    if value:
                        return value
                except (OSError, KeyError, ValueError):
                    pass
                time.sleep(0.1)
            raise AssertionError('deadline waiting for ' + label + '; inspect ' + str(temporary / 'server.log'))

        def page():
            with urllib.request.urlopen(base + '/preflight', timeout=2) as response:
                return response.read().decode('utf-8-sig')

        html = wait_for(page, 'preflight')
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', html).group(1)

        def api(path, body=None):
            request = urllib.request.Request(base + path,
                headers={'x-session-token': token, 'Content-Type': 'application/json'},
                data=json.dumps(body).encode() if body is not None else None)
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)

        def conflict(path, body):
            try:
                api(path, body)
            except urllib.error.HTTPError as exc:
                assert exc.code == 409, f'expected 409, received {exc.code}'
            else:
                raise AssertionError('expected 409 from ' + path)

        def status():
            return api(package_path + '/status')

        def launch(revision, **choices):
            return api(package_path + '/launch', {'revision': revision, **choices})

        def record(model):
            return json.loads((records / f'record-{model}.json').read_text('utf-8'))

        api_seat = {'id': 'api', 'name': 'API fake', 'adapter': 'openai-compatible',
                    'provider': 'fake-api', 'model': 'api-one', 'reasoning': None,
                    'launch_profile': 'standard', 'secret_ref': ''}
        cli_seat = {'id': 'cli', 'name': 'CLI fake', 'adapter': 'cli',
                    'provider': 'fake-cli', 'model': 'cli-one', 'reasoning': 'high',
                    'launch_profile': 'standard', 'secret_ref': ''}
        missing_seat = {**api_seat, 'id': 'missing', 'name': 'Credential needed',
                        'secret_ref': 'TICKET5_MISSING_CREDENTIAL'}
        package = {'id': package_id, 'name': 'Mixed fake team',
                   'seats': [api_seat, cli_seat, missing_seat]}
        assert api('/api/preflight/packages', package) == package
        listed = api('/api/preflight/seats')
        assert listed['packages'] == [package], 'saved mixed package failed to roundtrip'
        revision = listed['package_revisions'][package_id]
        assert re.fullmatch('[0-9a-f]{64}', revision)
        assert not listed['package_launches'][package_id]['ready']

        first = launch(revision)
        assert set(first['seats']) == {'api', 'cli', 'missing'}
        assert first['seats']['missing']['state'] == 'action_required'
        healthy = wait_for(lambda: (s if s['seats']['api']['state'] == 'ready' and
                              s['seats']['cli']['state'] == 'ready' else None)
                           if (s := status()) else None, 'healthy mixed peers ready')
        assert healthy['seats']['missing']['state'] == 'action_required'
        assert not healthy['ready']
        assert not provider_calls, 'launch called the fake API provider'
        attempts = {seat: healthy['seats'][seat]['attempt'] for seat in ('api', 'cli')}
        wait_for(lambda: (records / 'record-cli-one.json').exists(), 'CLI fixture argv')
        assert record('cli-one')['model'] == 'cli-one'
        assert record('cli-one')['reasoning'] == 'high'
        assert record('cli-one')['mcp_settings_path']
        assert record('cli-one')['mcp_settings']['mcpServers']['agentchattr']['headers']['Authorization']

        reused = launch(revision)
        assert {seat: reused['seats'][seat]['attempt'] for seat in attempts} == attempts
        assert reused['seats']['missing']['state'] == 'action_required'
        omitted = launch(revision, omitted_seats=['missing'])
        assert omitted['ready'] and set(omitted['seats']) == {'api', 'cli'}
        assert {seat: omitted['seats'][seat]['attempt'] for seat in attempts} == attempts
        assert len(api('/api/preflight/seats')['packages'][0]['seats']) == 3
        conflict(package_path + '/chat', {'selection_id': reused['selection_id']})

        sessions_before = api('/api/sessions/active-all')
        session_file = temporary / 'data/session_runs.json'
        sessions_bytes_before = session_file.read_bytes() if session_file.exists() else None
        message_file = temporary / 'data/agentchattr_log.jsonl'
        message_bytes_before = message_file.read_bytes() if message_file.exists() else None
        handoff = api(package_path + '/chat', {'selection_id': omitted['selection_id']})
        assert handoff == {'selection_id': omitted['selection_id'],
                           'url': '/?package_launch=' + omitted['selection_id']}
        assert api('/api/sessions/active-all') == sessions_before
        assert (session_file.read_bytes() if session_file.exists() else None) == sessions_bytes_before
        assert (message_file.read_bytes() if message_file.exists() else None) == message_bytes_before
        assert not provider_calls, 'chat handoff called the fake API provider'
        assert not record('cli-one')['prompts'], 'chat handoff dispatched a CLI prompt'

        package['seats'][1]['model'] = 'cli-two'
        api('/api/preflight/packages', package)
        assert not status()['ready'], 'saved edit left old selection ready'
        conflict(package_path + '/chat', {'selection_id': omitted['selection_id']})
        conflict(package_path + '/launch', {'revision': revision, 'omitted_seats': ['missing']})
        new_revision = api('/api/preflight/seats')['package_revisions'][package_id]
        assert new_revision != revision
        mismatch = launch(new_revision, omitted_seats=['missing'])
        assert mismatch['seats']['cli']['state'] == 'action_required'
        assert 'restart' in mismatch['seats']['cli']['error'].lower()
        assert mismatch['seats']['api']['attempt'] == attempts['api']
        assert mismatch['seats']['cli']['attempt'] == attempts['cli']
        assert not (records / 'record-cli-two.json').exists()
        restarted = launch(new_revision, omitted_seats=['missing'], restart_seats=['cli'])
        assert restarted['seats']['api']['attempt'] == attempts['api']
        assert restarted['seats']['cli']['attempt'] != attempts['cli']
        ready = wait_for(lambda: s if (s := status())['ready'] else None,
                         'targeted restarted team ready')
        assert ready['seats']['cli']['requested_model'] == 'cli-two'
        wait_for(lambda: (records / 'record-cli-two.json').exists(), 'restarted CLI argv')
        assert record('cli-two')['model'] == 'cli-two'
        assert not provider_calls

        api(f'/api/preflight/seats/{package_id}/api/stop', {})
        assert not status()['ready'], 'stopping a member left the selection ready'
        conflict(package_path + '/chat', {'selection_id': restarted['selection_id']})

        if '--serve' in sys.argv:
            serving = launch(new_revision, omitted_seats=['missing'], restart_seats=['api'])
            wait_for(lambda: status()['ready'], 'browser QA team ready')
            assert serving['selection_id'] == status()['selection_id']

        print(json.dumps({'result': 'PASS', 'url': base + '/preflight',
                          'saved_seats': 3, 'healthy_peers_reused': True,
                          'partial_failure_isolated': True, 'omitted_selection_ready': True,
                          'stale_handoff_rejected': True, 'revision_and_restart_checked': True,
                          'provider_calls': len(provider_calls), 'sessions_created': 0,
                          'scratch': str(temporary)}), flush=True)
        if '--serve' in sys.argv:
            url_marker.write_text(base + '/preflight', encoding='utf-8')
            print('Browser QA server ready; create ' + str(stop_marker) + ' to stop it.', flush=True)
            while child.poll() is None and not stop_marker.exists():
                time.sleep(0.5)
    finally:
        if api is not None and child is not None and child.poll() is None:
            for seat_id in ('api', 'cli', 'missing'):
                try:
                    api(f'/api/preflight/seats/{package_id}/{seat_id}/stop', {})
                except (OSError, urllib.error.HTTPError):
                    pass
        if child is not None:
            stop_owned_child(child)
        provider.shutdown()
        provider.server_close()
        if url_marker.exists():
            url_marker.unlink()
        if stop_marker.exists():
            stop_marker.unlink()


if __name__ == '__main__':
    main()
