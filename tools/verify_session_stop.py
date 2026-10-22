"""Actual scoped Stop: blocked API child, unsupported CLI, quarantine and peers.

Uses isolated data/ports and local fake clients only. Never discovers/kills PIDs;
termination is through the manager's positively owned launch confirmation.
--serve pauses at unresolved/quarantined CLI evidence until the browser-stop
sentinel appears, then runs the original stale/valid termination assertions.
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
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dispatch_queue import QueueStore
from launcher import stop_owned_child
from session_store import SessionStore

API_TEMPLATE = {'id': 'api-stop', 'name': 'Accepted work then delayed invocation',
    'roles': ['reviewer'], 'phases': [
        {'name': 'Accepted first pass', 'participants': ['reviewer'], 'prompt': 'Give the first result.'},
        {'name': 'Delayed final', 'participants': ['reviewer'], 'prompt': 'Give the final result.', 'is_output': True}]}
SINGLE_TEMPLATE = {'id': 'single-stop', 'name': 'Single owned turn', 'roles': ['worker'],
    'phases': [{'name': 'Work', 'participants': ['worker'], 'prompt': 'Do the assigned work.', 'is_output': True}]}


def main():
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Actual Windows CLI console required.'}))
        return
    captures = []
    slow_started, slow_release, slow_handler_ended = threading.Event(), threading.Event(), threading.Event()
    slow_calls = []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            captures.append(payload)
            fresh = 'FRESH-INDEPENDENT' in json.dumps(payload)
            if fresh:
                text = 'Fresh independent discussion survived Stop.'
            elif payload['model'] == 'peer-model':
                text = json.dumps({'kind': 'final', 'content': 'Peer run completed independently.'})
            else:
                slow_calls.append(payload)
                text = json.dumps({'kind': 'final', 'content': 'Accepted before Stop.' if len(slow_calls) == 1 else 'Late API callback must not be accepted.'})
            body = json.dumps({'model': 'fake-local-confirmed', 'choices': [{'message': {'content': text}}]}).encode()
            delayed = not fresh and payload['model'] == 'slow-model' and len(slow_calls) == 2
            try:
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                if delayed:
                    self.wfile.write(body[:1])
                    self.wfile.flush()
                    slow_started.set()
                    slow_release.wait(90)
                    self.wfile.write(body[1:])
                else:
                    self.wfile.write(body)
                self.wfile.flush()
            except OSError:
                pass
            finally:
                if delayed:
                    slow_handler_ended.set()

        def log_message(self, *args):
            pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='session stop integration ', dir=scratch))
    data, records = temporary / 'data', temporary / 'records'
    records.mkdir()
    source_sentinel = temporary / 'SOURCE_NOT_EXECUTED.txt'
    source = f'Exact café source\r\n@all is data.\nfrom pathlib import Path\nPath({str(source_sentinel)!r}).write_text("executed")'
    sockets = [socket.socket() for _ in range(3)]
    for handle in sockets:
        handle.bind(('127.0.0.1', 0))
    ports = [handle.getsockname()[1] for handle in sockets]
    for handle in sockets:
        handle.close()
    base = f'http://127.0.0.1:{ports[0]}'
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(data), AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'), TICKET10_RECORDS=str(records))
    fixture = str((ROOT / 'tools/fake_session_stop_cli.py').resolve())
    code = f'''import config_loader
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['agents']={{'fake-api':{{'type':'api','base_url':'http://127.0.0.1:{provider.server_port}/v1'}},
        'fake-cli':{{'command':{sys.executable!r},'cwd':'.','cli_args':[{fixture!r}],
        'mcp_inject':'env','mcp_env_var':'TICKET10_FAKE_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.session_store.save_custom_template({API_TEMPLATE!r})
    app.session_store.save_custom_template({SINGLE_TEMPLATE!r})
    app.room_settings['channels']=['general','api-review','cli-run','peer-review','fresh']
app.configure=configured
import run
run.main()
'''
    child, api = None, None
    url_marker = scratch / 'ticket10-browser-url.txt'
    stop_marker = scratch / 'ticket10-browser-stop.txt'
    try:
        with (temporary / 'server.log').open('wb') as output:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)

        def wait_for(check, label, timeout=30):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise AssertionError('server exited; scratch: ' + str(temporary))
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

        def api(path, body=None, headers=None):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                headers=headers if headers is not None else {'x-session-token': token, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)

        def reject(path, body, expected, headers=None):
            try:
                api(path, body, headers)
            except urllib.error.HTTPError as exc:
                assert exc.code == expected, f'expected HTTP{expected}, received {exc.code}'
            else:
                raise AssertionError('Expected rejection: ' + path)

        def saved(session_id):
            return next(value for value in json.loads((data / 'session_runs.json').read_text('utf-8')) if value['id'] == session_id)

        def stop_status(session_id):
            return api(f'/api/sessions/{session_id}/stop-status')

        def receipt_statuses(state):
            return [value['evidence']['status'] for value in state.get('cancellation_receipts', [])]

        seat = {'id': 'slow', 'name': 'Slow API', 'adapter': 'openai-compatible', 'provider': 'fake-api',
                'model': 'slow-model', 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        api('/api/preflight/packages', {'id': 'stop-team', 'name': 'Stop team', 'seats': [seat,
            {**seat, 'id': 'peer', 'name': 'Independent peer', 'model': 'peer-model'},
            {**seat, 'id': 'cli', 'name': 'Unsupported CLI', 'adapter': 'cli', 'provider': 'fake-cli', 'model': None}]})
        revision = api('/api/preflight/seats')['package_revisions']['stop-team']
        api('/api/preflight/packages/stop-team/launch', {'revision': revision})
        ready = wait_for(lambda: state if (state := api('/api/preflight/packages/stop-team/status'))['ready'] else None, 'three seats ready')
        names = {key: ready['seats'][key]['name'] for key in ('slow', 'peer', 'cli')}
        instances = json.loads((data / 'registry.json').read_text('utf-8'))['instances']
        owner = {key: instances[names[key]] for key in names}
        headers = {key: {'Authorization': 'Bearer ' + owner[key]['token'], 'Content-Type': 'application/json'} for key in names}
        (records / 'control.json').write_text(json.dumps({'peer_name': names['peer']}), encoding='utf-8')
        queue = QueueStore(data)
        api_run = api('/api/sessions/start', {'template_id': 'api-stop', 'channel': 'api-review',
            'cast': {'reviewer': names['slow']}, 'goal': 'Retain prior accepted result.', 'input_text': source})
        assert slow_started.wait(30), 'fake provider never reached actual delayed response body'
        active_api = saved(api_run['id'])
        assert len(active_api['admitted_events']) == 1
        accepted = active_api['admitted_events'][0]
        assert accepted['content'] == 'Accepted before Stop.'
        api_invocation = active_api['active_invocation']
        cli_run = api('/api/sessions/start', {'template_id': 'single-stop', 'channel': 'cli-run',
            'cast': {'worker': names['cli']}, 'input_text': source})

        def cli_record():
            value = json.loads((records / 'cli-stop.json').read_text('utf-8'))
            if value.get('error'):
                raise AssertionError('CLI fixture: ' + value['error'])
            return value

        wait_for(lambda: 'envelope' in cli_record(), 'real CLI console and scoped brief')
        cli_invocation = cli_run['active_invocation']
        descendants = []
        for key, run, invocation in (('slow', api_run, api_invocation), ('cli', cli_run, cli_invocation)):
            descendants.append((key, queue.enqueue(owner[key], {'dispatch_id': uuid.uuid4().hex,
                'channel': run['channel'], 'prompt': 'STOPPED-DESCENDANT must never run',
                'run_id': run['run_id'], 'attempt_id': invocation['attempt_id']})))
        started_stop = time.monotonic()
        first_stop = api(f'/api/sessions/{api_run["id"]}/stop', {})
        cli_stop = api(f'/api/sessions/{cli_run["id"]}/stop', {})
        assert first_stop['dispatch_eligible'] is False and cli_stop['dispatch_eligible'] is False
        assert api(f'/api/sessions/{api_run["id"]}/stop', {})['stop_id'] == first_stop['stop_id']
        ended = wait_for(lambda: state if (state := stop_status(api_run['id']))['state'] == 'stopped' and
                         'local_ended' in receipt_statuses(state) else None, 'actual API invocation child local_ended', timeout=10)
        local_end_ms = (time.monotonic() - started_stop) * 1000
        assert not slow_release.is_set(), 'fixture provider progressed before local cancellation evidence'
        assert ended['admitted_events'] == active_api['admitted_events']
        assert ended['input_snapshot']['text'] == source
        assert all(value['evidence']['remote_compute'] == 'unverified' for value in ended['cancellation_receipts'])
        wait_for(lambda: 'unsupported' in receipt_statuses(stop_status(cli_run['id'])), 'honest unsupported CLI receipt')
        runtime = api('/api/preflight/seats')['runtime']
        for key in ('slow', 'peer', 'cli'):
            assert runtime['stop-team/' + key]['attempt'] == ready['seats'][key]['attempt']
            assert runtime['stop-team/' + key]['state'] == 'ready', 'Stop implicitly terminated a seat'
        for key, record in descendants:
            assert queue.owned(owner[key], record['envelope']['dispatch_id'])['state'] == 'cancelled'
        assert len(cli_record()['prompts']) == 1

        # A genuine peer run still executes after Stop of both affected runs.
        peer_run = api('/api/sessions/start', {'template_id': 'single-stop', 'channel': 'peer-review',
            'cast': {'worker': names['peer']}, 'input_text': 'Independent source'})
        wait_for(lambda: saved(peer_run['id'])['state'] == 'complete', 'unaffected peer run completes')
        ledger = lambda: json.loads((data / 'queue/ledger.json').read_text('utf-8'))['records']
        peer_count = lambda: sum(record['envelope']['target_identity_id'] == owner['peer']['identity_id'] for record in ledger())
        before_peer = peer_count()
        api_late = 'API-LATE-TYPED café @' + names['peer']
        reject(f'/api/sessions/{api_run["id"]}/event', {'brief_id': api_invocation['brief_id'],
            'kind': 'final', 'content': api_late}, 409, headers['slow'])
        api('/api/send', {'text': 'API-LATE-TAGGED @' + names['peer'], 'channel': 'api-review',
                         'dispatch_id': api_invocation['dispatch_id']}, headers['slow'])
        (records / 'emit-late').touch()
        late_cli = wait_for(lambda: value if 'responses' in (value := cli_record()) else None, 'late typed/tagged/untagged MCP output')
        assert json.loads(late_cli['responses']['typed'])['status'] == 'rejected'
        for key in ('typed', 'tagged', 'untagged'):
            assert any(event['content'] == late_cli['late_content'][key] for event in stop_status(cli_run['id'])['quarantined_events'])
        assert any(event['content'] == api_late for event in stop_status(api_run['id'])['quarantined_events'])
        slow_release.set()
        wait_for(slow_handler_ended.is_set, 'fake provider late callback cleanup')
        time.sleep(1.5)
        assert peer_count() == before_peer, 'quarantined mentions cascaded into peer work'
        assert len(saved(api_run['id'])['admitted_events']) == 1
        assert saved(cli_run['id']).get('admitted_events', []) == []

        # Explicit new ordinary dispatch scope restores legitimate discussion on
        # the surviving API seat; the stopped source run remains fenced.
        fresh = queue.enqueue(owner['slow'], {'channel': 'fresh', 'prompt': 'FRESH-INDEPENDENT discussion'})
        wait_for(lambda: queue.owned(owner['slow'], fresh['envelope']['dispatch_id'])['state'] == 'released', 'fresh tagged API discussion')
        messages = [json.loads(line) for line in (data / 'agentchattr_log.jsonl').read_text('utf-8').splitlines()]
        discussion = next(message for message in messages if message['text'] == 'Fresh independent discussion survived Stop.')
        assert not (discussion.get('metadata') or {}).get('routing_suppressed')
        assert discussion['metadata']['dispatch_id'] == fresh['envelope']['dispatch_id']
        assert SessionStore(str(data / 'session_runs.json')).get(api_run['id'])['dispatch_eligible'] is False
        assert SessionStore(str(data / 'session_runs.json')).get(cli_run['id'])['dispatch_eligible'] is False
        unresolved = wait_for(lambda: state if (state := stop_status(cli_run['id']))['state'] == 'unresolved' else None,
                              'actual ten-second CLI unresolved deadline', timeout=13)
        assert unresolved['dispatch_eligible'] is False
        assert queue.owned(owner['cli'], cli_invocation['dispatch_id'])['state'] == 'cancelling'
        assert len(cli_record()['prompts']) == 1
        if '--serve' in sys.argv:
            browser_url = base + '/?channel=cli-run'
            url_marker.write_text(browser_url, encoding='utf-8')
            print(json.dumps({'stage': 'stop_browser_qa_ready', 'url': browser_url,
                'channel': cli_run['channel'], 'cli_session_id': cli_run['id'],
                'api_session_id': api_run['id'], 'cli_state': unresolved['state'],
                'quarantined_events': len(unresolved.get('quarantined_events', [])),
                'stop_sentinel': str(stop_marker), 'scratch': str(temporary)}), flush=True)
            while child.poll() is None and not stop_marker.exists():
                time.sleep(.5)
        terminate_path = f'/api/sessions/{cli_run["id"]}/terminate-seat'
        reject(terminate_path, {'dispatch_id': cli_invocation['dispatch_id'], 'launch_attempt': '0' * 32, 'confirm': True}, 409)
        assert api('/api/preflight/seats')['runtime']['stop-team/cli']['state'] == 'ready'
        api(terminate_path, {'dispatch_id': cli_invocation['dispatch_id'],
                            'launch_attempt': ready['seats']['cli']['attempt'], 'confirm': True})
        wait_for(lambda: api('/api/preflight/seats')['runtime']['stop-team/cli']['state'] == 'stopped', 'confirmed exact owned CLI termination')
        settled = wait_for(lambda: state if (state := stop_status(cli_run['id']))['state'] == 'stopped' else None, 'terminated CLI settled local_ended')
        assert 'local_ended' in receipt_statuses(settled)
        assert queue.owned(owner['cli'], cli_invocation['dispatch_id'])['state'] == 'cancelled'
        assert api('/api/preflight/seats')['runtime']['stop-team/peer']['state'] == 'ready'
        assert not source_sentinel.exists()
        print(json.dumps({'result': 'PASS', 'api_local_ended_ms': round(local_end_ms, 3),
            'api_prior_results_retained': 1, 'provider_remote_compute': 'unverified',
            'cli_unsupported_then_unresolved': True, 'cli_injections': len(cli_record()['prompts']),
            'quarantine_no_mention_cascade': True, 'fresh_tagged_discussion': True,
            'stale_termination_http': 409, 'confirmed_owned_termination': True,
            'peer_run_completed': True, 'reloaded_fences': True, 'scratch': str(temporary)}), flush=True)
    finally:
        slow_release.set()
        if api is not None and child is not None and child.poll() is None:
            for key in ('slow', 'peer', 'cli'):
                try:
                    api('/api/preflight/seats/stop-team/' + key + '/stop', {})
                except OSError:
                    pass
        if child is not None:
            stop_owned_child(child)
        provider.shutdown()
        provider.server_close()
        if '--serve' in sys.argv:
            for marker in (url_marker, stop_marker):
                if marker.exists():
                    marker.unlink()


if __name__ == '__main__':
    main()
