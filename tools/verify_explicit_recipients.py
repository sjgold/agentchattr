"""DRAFT: isolated Windows explicit-recipient acceptance, local fake providers only.

Select --case audience|order|family. --compile-only starts no processes.
The optional audience --serve pause is for separately authorized root browser QA.
No run is accepted until actual result/cleanup evidence exists. Registry-only
family/offline rows provide no native readiness evidence. No live AI/Omarchy or
remote cancellation guarantee. Existing verifier files are used read-only.
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
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from invocation_evidence import classify
from tools import verify_participant_recovery as lifecycle
from tools import verify_runtime_crash_matrix as resources

ONE = {'id': 'recipient-order', 'name': 'One actual CLI result', 'roles': ['worker'],
       'phases': [{'name': 'Review', 'participants': ['worker'], 'prompt': 'Give one typed final.', 'is_output': True}]}
SOURCE = 'Exact recipient-order café\r\nsource @all remains data.'


def server_code(root, provider_port, case):
    return f'''import sys,json,config_loader
from pathlib import Path
from process_identity import capture_birth
from api_seats import atomic_json
root=Path({str(root)!r})
atomic_json(root/'server-birth.json',capture_birth())
load=config_loader.load_config
def isolated(path=None):
    cfg=load(path)
    cfg['agents']={{'fixture-api':{{'type':'api','base_url':'http://127.0.0.1:{provider_port}/v1',
        'system_prompt':'Local recipient acceptance. Reply without mentions.'}},
        'fixture-cli':{{'command':{sys.executable!r},'cwd':{str(root)!r},
        'cli_args':[{str(ROOT/'tools/fake_recipient_client.py')!r}],
        'mcp_inject':'env','mcp_env_var':'RECIPIENT_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
fixture_rows={{}}
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','audience-run','order-run','order-run-b','family-run']
    app.session_store.save_custom_template({ONE!r})
app.configure=configured
@app.app.get('/api/fixture/state')
def state():
    manager=app.api_seat_manager
    with manager.lock:
        workers={{}}
        for key,attempt in manager.attempts.items():
            owner=next((v for v in app.registry.get_all().values() if v['base']==attempt.get('base')),None)
            workers[key]={{'attempt':attempt['id'],'name':owner['name'] if owner else None,
                'identity_id':owner['identity_id'] if owner else None,
                'readiness':manager.restart_readiness(owner['identity_id'],manager.boot_id) if owner else None}}
        return {{'workers':workers,'registry_fixture':fixture_rows,'router':app.router._channels}}
@app.app.post('/api/fixture/registry')
async def registry_fixture(request:app.Request):
    body=await request.json()
    action=body['action']
    if action=='offline':
        app.registry.seed({{'offline-fixture':{{'label':'NONNATIVE offline registry fixture'}}}})
        value=app.registry.register('offline-fixture')
        fixture_rows['offline']={{k:value[k] for k in ('name','identity_id','base','state')}}
    elif action=='family':
        app.registry.seed({{'familyfixture':{{'label':'NONNATIVE family fixture'}},
                           'pendingfixture':{{'label':'NONNATIVE pending fixture'}}}})
        first=app.registry.register('familyfixture')
        first=app.registry.rename(first['name'],'familyfixture-one')
        second=app.registry.register('familyfixture')
        second=app.registry.rename(second['name'],'familyfixture-two')
        fixture_rows['family']=[{{k:v[k] for k in ('name','identity_id','base','state')}} for v in (first,second)]
        pending=app.registry.register('pendingfixture')
        # Explicit registry-only pending fixture, no worker/readiness assertion.
        with app.registry._lock:app.registry._instances[pending['name']].state='pending'
        app.registry._save_instances()
    elif action=='unique':
        app.registry.deregister('familyfixture-two')
    elif action=='hops':
        app.router._channels[body['channel']]={{'hop_count':3,'paused':True,'guard_emitted':True}}
    else:raise ValueError('Unknown fixture action')
    return {{'registry_fixture':fixture_rows}}
import run
run.main()
'''


class Fixture:
    # Read-only utility reuse only; no inherited scenario constructor or exercise.
    wait = resources.Case.wait
    retain = staticmethod(resources.Case.retain)
    keep_worker = lifecycle.Fixture.keep_worker
    keep_model = lifecycle.Fixture.keep_model
    keep_client = lifecycle.Fixture.keep_client
    clients_read = lifecycle.Fixture.clients_read
    session = resources.Case.session

    def __init__(self, case):
        self.case = case
        scratch = ROOT / '.audit-tmp'
        scratch.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='explicit recipients ' + case + ' ', dir=scratch))
        self.data, self.records = self.root / 'data', self.root / 'records'
        self.records.mkdir()
        self.captures, self.capture_lock = [], threading.Lock()
        self.gates, self.servers, self.workers, self.models, self.clients = {}, [], {}, {}, {}
        self.runs, self.observations, self.api, self.run_id = [], [], None, None
        self.cleanup = None
        parent = self
        class Provider(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with parent.capture_lock:
                    index = len(parent.captures) + 1
                    parent.captures.append(payload)
                    gate = threading.Event()
                    parent.gates[index] = gate
                    atomic_json(parent.root / 'provider-requests.json', parent.captures)
                body = json.dumps({'choices': [{'message': {'content': 'LOCAL_REPLY_' + str(index)}}]}).encode()
                try:
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body[:1]); self.wfile.flush()
                    if gate.wait(110):
                        self.wfile.write(body[1:]); self.wfile.flush()
                except OSError:
                    pass
            def log_message(self, *args):
                pass
        self.provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        self.provider.daemon_threads = True
        threading.Thread(target=self.provider.serve_forever, daemon=True).start()
        sockets = [socket.socket() for _ in range(3)]
        for item in sockets:
            item.bind(('127.0.0.1', 0))
        ports = [item.getsockname()[1] for item in sockets]
        for item in sockets:
            item.close()
        self.base = 'http://127.0.0.1:' + str(ports[0])
        self.env = dict(os.environ, AGENTCHATTR_DATA_DIR=str(self.data),
            AGENTCHATTR_UPLOAD_DIR=str(self.root / 'uploads'), RECIPIENT_RECORDS=str(self.records),
            RECIPIENT_PEER_NAME_FILE=str(self.root / 'peer-name.txt'),
            RECIPIENT_CLI_NAME_FILE=str(self.root / 'cli-name.txt'))
        self.env.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))

    def start(self):
        code = server_code(self.root, self.provider.server_port, self.case)
        compile(code, '<recipient-server>', 'exec')
        with (self.root / 'server.log').open('wb') as log:
            launcher = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=self.env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        self.servers.append({'launcher': launcher, 'handle': None, 'exit_observed': None})
        birth = self.wait(lambda: json.loads((self.root / 'server-birth.json').read_text(encoding='utf-8')), 'true server birth', 10)
        self.servers[0]['handle'] = self.retain(birth)
        def page():
            assert launcher.poll() is None, 'Isolated server exited'
            with urllib.request.urlopen(self.base + '/preflight', timeout=2) as reply:
                return reply.read().decode('utf-8-sig')
        self.token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', self.wait(page, 'HTTP ready')).group(1)
        def api(path, body=None, headers=None):
            request = urllib.request.Request(self.base + path,
                data=json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None,
                headers={'x-session-token': self.token, 'Content-Type': 'application/json'} if headers is None else headers)
            with urllib.request.urlopen(request, timeout=15) as reply:
                return json.load(reply)
        self.api = api

    def state(self):
        return self.api('/api/fixture/state')

    def ledger_records(self):
        path = self.data / 'queue/ledger.json'
        return json.loads(path.read_text(encoding='utf-8'))['records'] if path.exists() else []

    def messages(self):
        path = self.data / 'agentchattr_log.jsonl'
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line] if path.exists() else []

    def reject(self, path, body, headers, status=403):
        try:
            self.api(path, body, headers)
        except urllib.error.HTTPError as exc:
            assert exc.code == status, (exc.code, status)
            return
        raise AssertionError('Expected scoped refusal: ' + path)

    def setup(self):
        self.start()
        if self.case == 'family':
            return
        common = {'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        seats = [dict(common, id='a', name='API A', adapter='openai-compatible', provider='fixture-api', model='recipient-model-a')]
        if self.case == 'audience':
            seats.append(dict(common, id='b', name='API B', adapter='openai-compatible', provider='fixture-api', model='recipient-model-b'))
        else:
            seats.append(dict(common, id='cli', name='Order CLI', adapter='cli', provider='fixture-cli'))
        self.api('/api/preflight/packages', {'id': 'recipients', 'name': 'Isolated recipients', 'seats': seats})
        revision = self.api('/api/preflight/seats')['package_revisions']['recipients']
        self.api('/api/preflight/packages/recipients/launch', {'revision': revision})
        def ready():
            state = self.state()
            return state if len(state['workers']) == len(seats) and all(
                value['readiness'] and value['readiness']['state'] == 'ready' and
                value['readiness']['process_verified'] is True for value in state['workers'].values()) else None
        self.initial = self.wait(ready, 'genuine worker HTTP/native proof')
        assert not self.captures
        for value in self.initial['workers'].values():
            self.keep_worker(value['attempt'])
        if self.case == 'order':
            record = self.wait(lambda: values[0] if len(values := self.clients_read()) == 1 else None, 'hidden client self birth')
            owner = self.initial['workers']['recipients/cli']
            self.client_pid = self.keep_client(record, owner['attempt'])
            (self.root / 'peer-name.txt').write_text(self.initial['workers']['recipients/a']['name'], encoding='utf-8')
            (self.root / 'cli-name.txt').write_text(owner['name'], encoding='utf-8')

    def finish_api(self, target_count):
        self.wait(lambda: len(self.captures) == target_count, 'exact held provider count')
        # All current exact journals are retained before any response body gate opens.
        def retain_intents():
            for worker in self.workers.values():
                for directory in (worker['path'] / 'invocations').glob('*'):
                    if directory.name not in self.models:
                        self.keep_model(worker['path'], directory.name)
            return len(self.models) == target_count
        self.wait(retain_intents, 'exact model birth handles')
        for index in range(1, target_count + 1):
            self.gates[index].set()
        for dispatch, model in self.models.items():
            if model.get('exit_observed') is None:
                model['exit_observed'] = model['handle'].wait(timeout=15)
            snapshot = json.loads((model['runtime'] / 'config.json').read_text(encoding='utf-8'))
            scope = {'runtime_path': str(model['runtime']), 'launch_attempt': snapshot['attempt'],
                     'launch_nonce': snapshot['ownership']['launch_nonce'], 'dispatch_id': dispatch}
            self.wait(lambda scope=scope: classify(scope).get('local_ended') is True, 'genuine parent IPC/end')
        self.wait(lambda: all(value['state'] in ('released', 'cancelled') for value in self.ledger_records()
            if value['envelope']['dispatch_id'] in self.models), 'API transport release')

    def quiet(self, ledger_count, provider_count, seconds=3, queued_dispatch=None, cli_injections=None, other_queued_dispatch=None):
        # More than two normal 1s worker polls, not an instantaneous absence check.
        started_at = time.time()
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            assert len(self.captures) == provider_count
            records = self.ledger_records()
            assert len(records) == ledger_count
            if queued_dispatch:
                assert next(r for r in records if r['envelope']['dispatch_id'] == queued_dispatch)['state'] == 'queued'
            if other_queued_dispatch:
                assert next(r for r in records if r['envelope']['dispatch_id'] == other_queued_dispatch)['state'] == 'queued'
            if cli_injections is not None:
                assert sum(len(v['turns']) for v in self.clients_read()) == cli_injections
            time.sleep(.1)
        self.observations.append({'kind': 'bounded_poll_interval', 'started_at': started_at,
            'ended_at': time.time(), 'minimum_seconds': seconds, 'provider_count': provider_count,
            'ledger_count': ledger_count, 'queued_dispatch': queued_dispatch,
            'other_queued_dispatch': other_queued_dispatch, 'cli_injections': cli_injections})

    def receipt(self, message, identities, ack=None):
        receipt = message['metadata']['recipient_routing']
        assert message['uid'] == receipt['message_uid']
        if ack is not None:
            assert ack == {'type': 'message_accepted', 'uid': message['uid'], 'channel': message['channel']}
        assert [item['identity_id'] for item in receipt['recipients']] == identities
        expected = {uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:recipient:' + message['uid'] + ':' + identity).hex: identity for identity in identities}
        def dispatched():
            records = self.ledger_records()
            return records if all(any(r['envelope']['dispatch_id'] == dispatch for r in records) for dispatch in expected) else None
        records = self.wait(dispatched, 'each frozen recipient identity dispatch') if expected else self.ledger_records()
        assert {r['envelope']['dispatch_id'] for r in records} - self.before_dispatches == set(expected), 'Unexpected per-message dispatch'
        for dispatch, identity in expected.items():
            record = next(r for r in records if r['envelope']['dispatch_id'] == dispatch)
            assert record['envelope']['target_identity_id'] == identity
        # No nonrecipient identity may acquire this message's deterministic dispatch.
        state = self.state()
        nonrecipients = list(state['workers'].values())
        for instance in state['registry_fixture'].values():
            nonrecipients.extend(instance if isinstance(instance, list) else [instance])
        for value in nonrecipients:
            identity = value['identity_id']
            if identity not in identities:
                forbidden = uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:recipient:' + message['uid'] + ':' + identity).hex
                assert not any(r['envelope']['dispatch_id'] == forbidden for r in records)
        self.observations.append({'uid': message['uid'], 'receipt': receipt, 'dispatches': expected, 'ack': ack})
        return receipt

    def ws(self):
        from websockets.sync.client import connect
        return connect(self.base.replace('http:', 'ws:') + '/ws?token=' + self.token, open_timeout=10)

    def post(self, socket, text, selected, channel='audience-run', **extra):
        self.before_dispatches = {r['envelope']['dispatch_id'] for r in self.ledger_records()}
        preview = self.api('/api/recipients/preview', {'text': text, 'selected_recipients': selected, 'channel': channel})
        assert set(preview) == {'mode', 'tokens', 'ignored', 'recipients', 'warnings', 'waiting'}
        socket.send(json.dumps({'type': 'message', 'text': text, 'selected_recipients': selected,
            'sender': 'fixture-operator', 'channel': channel, 'attachments': [], **extra}, ensure_ascii=False))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            event = json.loads(socket.recv(timeout=5))
            if event.get('type') == 'message_error':
                raise AssertionError('Operator message unexpectedly refused')
            if event.get('type') == 'message_accepted':
                message = self.wait(lambda: next((m for m in self.messages() if m.get('uid') == event['uid']), None), 'durable ACK UID')
                assert message['text'] == text
                receipt = message['metadata']['recipient_routing']
                assert {key: receipt[key] for key in preview} == preview
                return message, event
        raise AssertionError('Content ACK deadline')

    def close(self):
        # Adapter around the reviewed cleanup, not inherited scenario execution.
        # Stop EVERY actual run before its complete inventory/native waits.
        if self.api:
            for session_id in self.runs:
                try:
                    self.api(f'/api/sessions/{session_id}/stop', {})
                except Exception:
                    pass
        lifecycle.Fixture.close(self)


def audience(f, serve=False):
    a, b = (f.initial['workers']['recipients/' + name] for name in ('a', 'b'))
    f.api('/api/fixture/registry', {'action': 'offline'})
    offline = f.state()['registry_fixture']['offline']
    selected = [a['name'], b['name']]
    count = 0
    with f.ws() as socket:
        explicit = '@' + a['name'] + ' Exact café\r\nreview this'
        if serve:
            f.before_dispatches = {r['envelope']['dispatch_id'] for r in f.ledger_records()}
            marker = ROOT / '.audit-tmp/ticket17-recipient-browser-url.txt'
            sentinel = ROOT / '.audit-tmp/ticket17-recipient-browser-stop.txt'
            ready = {'url': f.base + '/?channel=audience-run', 'channel': 'audience-run',
                     'text': explicit, 'selected_names': selected, 'scratch': str(f.root),
                     'stop_sentinel': str(sentinel), 'post_click_pulse_seconds': 30}
            atomic_json(marker, ready)
            print(json.dumps(ready, ensure_ascii=True), flush=True)
            try:
                f.wait(sentinel.exists, 'bounded root browser post', 600)
                message = next(m for m in reversed(f.messages()) if m.get('text') == explicit and m.get('metadata', {}).get('recipient_routing'))
                ack = None  # Browser owns its actual ACK; script never invents one.
            finally:
                marker.unlink(missing_ok=True); sentinel.unlink(missing_ok=True)
        else:
            message, ack = f.post(socket, explicit, selected)
        f.receipt(message, [a['identity_id']], ack)
        f.finish_api(1); count = 1
        message, ack = f.post(socket, 'Selections only café\r\nraw', selected)
        f.receipt(message, [a['identity_id'], b['identity_id']], ack)
        f.finish_api(3); count = 3
        quoted = '"@' + b['name'] + '" `@' + b['name'] + '`\n\n```\n@' + b['name'] + '\n```'
        zero_cases = [('Shared note café\r\nraw', []), (quoted, []), ('@definitely-unknown', selected),
                      ('Stale selected', ['nonexistent-selection'])]
        for text, names in zero_cases:
            before = len(f.ledger_records())
            message, ack = f.post(socket, text, names)
            receipt = f.receipt(message, [], ack)
            if text.startswith('@definitely'):
                assert receipt['mode'] == 'explicit' and receipt['warnings'][0]['kind'] == 'unknown'
            if text == quoted:
                assert {entry['reason'] for entry in receipt['ignored']} == {'quote', 'code', 'fence'}
            if text == 'Stale selected':
                assert receipt['warnings'][0]['kind'] == 'unavailable'
            f.quiet(before, count)
        message, ack = f.post(socket, quoted, [a['name']])
        f.receipt(message, [a['identity_id']], ack); f.finish_api(4); count = 4
        message, ack = f.post(socket, '@all Online audience only', selected)
        f.receipt(message, [value['identity_id'] for value in sorted((a, b), key=lambda v: v['name'])], ack)
        f.finish_api(6); count = 6
        before = len(f.ledger_records())
        message, ack = f.post(socket, '@offline-fixture Exact offline identity', selected)
        receipt = f.receipt(message, [offline['identity_id']], ack)
        assert receipt['warnings'] == [{'kind': 'offline', 'token': 'offline-fixture', 'candidates': []}]
        f.quiet(before + 1, count)
        job = f.api('/api/jobs', {'title': 'Recipient operator job', 'channel': 'audience-run'})
        path = f'/api/jobs/{job["id"]}/messages'
        f.before_dispatches = {r['envelope']['dispatch_id'] for r in f.ledger_records()}
        job_preview = f.api('/api/recipients/preview', {'text': '@' + b['name'] + ' Job raw café\r\ntext',
            'selected_recipients': [a['name']], 'channel': 'audience-run', 'job_id': job['id']})
        job_message = f.api(path, {'text': '@' + b['name'] + ' Job raw café\r\ntext',
            'selected_recipients': [a['name']], 'sender': 'fixture-operator'})
        f.receipt(job_message, [b['identity_id']]); f.finish_api(7); count = 7
        assert job_preview['recipients'] == job_message['metadata']['recipient_routing']['recipients']
        identities = json.loads((f.data / 'registry.json').read_text(encoding='utf-8'))['instances']
        bearer = {'Authorization': 'Bearer ' + identities[a['name']]['token'], 'Content-Type': 'application/json'}
        preview_body = {'text': '@all', 'selected_recipients': [], 'channel': 'audience-run'}
        before = len(f.ledger_records())
        for headers in ({'Content-Type': 'application/json'}, bearer):
            f.reject('/api/recipients/preview', preview_body, headers)
            f.reject(path, {'text': '@all'}, headers)
        forged = f.api('/api/send', {'text': 'Bearer shared status, no addressed agent.', 'channel': 'audience-run',
            'metadata': {'recipient_routing': message['metadata']['recipient_routing']}}, bearer)
        assert 'recipient_routing' not in forged.get('metadata', {})
        assert 'recipient_routing' not in next(m for m in f.messages() if m['id'] == forged['id']).get('metadata', {})
        for field in ('metadata', 'origin', 'msg_type'):
            socket.send(json.dumps({'type': 'message', 'text': '@all forged', 'channel': 'audience-run',
                                   'selected_recipients': selected, field: {} if field == 'metadata' else 'operator'}))
            deadline = time.monotonic() + 15
            refused = False
            while time.monotonic() < deadline:
                event = json.loads(socket.recv(timeout=min(5, max(.01, deadline - time.monotonic()))))
                if event.get('type') == 'message_error':
                    refused = True
                    break
                assert event.get('type') != 'message_accepted'
            assert refused, 'Invalid-field WebSocket message_error deadline'
        f.quiet(before, count)
    assert len(f.captures) == 7
    assert sum(v['model'] == 'recipient-model-a' for v in f.captures) == 4
    assert sum(v['model'] == 'recipient-model-b' for v in f.captures) == 3
    return {'case': 'audience', 'provider_calls': 7, 'cli_injections': 0,
            'offline_fixture_native_claim': False, 'serve': serve,
            'ignored_only_no_selection_provider_calls': 0,
            'ignored_only_selected_a_provider_calls': 1,
            'ignored_only_behavior': 'settled_selected_fallback_not_address_leak'}


def order(f):
    owner, peer = f.initial['workers']['recipients/cli'], f.initial['workers']['recipients/a']
    def start(channel='order-run'):
        run = f.api('/api/sessions/start', {'template_id': ONE['id'], 'channel': channel,
            'cast': {'worker': owner['name']}, 'input_text': SOURCE, 'goal': 'Keep exact logical order.'})
        f.runs.append(run['id'])
        return run
    def client_turn(index, key='dispatch_id'):
        values = f.clients_read()
        if len(values) == 1 and len(values[0]['turns']) > index and values[0]['turns'][index].get(key):
            return values[0]['turns'][index]
    def record(dispatch):
        return next(v for v in f.ledger_records() if v['envelope']['dispatch_id'] == dispatch)
    def submit(index):
        (f.records / ('submit-' + str(f.client_pid) + '-' + str(index))).touch()
        return f.wait(lambda: client_turn(index, 'final_reply'), 'actual gated MCP typed result')
    first = start()
    early = f.wait(lambda: client_turn(0, 'agent_chat_reply'), 'actual MCP chat plus early release')
    assert early['release_reply']['status'] == 'released'
    assert record(early['dispatch_id'])['state'] == 'released'
    second = start('order-run-b')
    original = [deepcopy(f.session(run['id'])) for run in (first, second)]
    f.api('/api/fixture/registry', {'action': 'hops', 'channel': 'order-run'})
    with f.ws() as socket:
        manual, ack = f.post(socket, '@' + owner['name'] + ' MANUAL_AFTER_B', [], 'order-run')
        f.receipt(manual, [owner['identity_id']], ack)
        manual_id = uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:recipient:' + manual['uid'] + ':' + owner['identity_id']).hex
        queued_count = len(f.ledger_records())
        f.quiet(queued_count, 0, queued_dispatch=manual_id, cli_injections=1,
            other_queued_dispatch=second['active_invocation']['dispatch_id'])
        assert record(manual_id)['state'] == 'queued' and len(f.clients_read()[0]['turns']) == 1
        assert f.state()['router']['order-run'] == {'hop_count': 0, 'paused': False, 'guard_emitted': False}
        for run, before in zip((first, second), original):
            current = f.session(run['id'])
            assert current['state'] == before['state'] and current['active_invocation'] == before['active_invocation']
        peer_message, ack = f.post(socket, '@' + peer['name'] + ' PEER_USABLE', [], 'order-run')
        f.receipt(peer_message, [peer['identity_id']], ack); f.finish_api(1)
        assert len(f.clients_read()[0]['turns']) == 1
        assert submit(0)['final_reply']['status'] == 'admitted'
        second_turn = f.wait(lambda: client_turn(1, 'release_reply'), 'B injection after actual A final')
        assert second_turn['dispatch_id'] == second['active_invocation']['dispatch_id']
        assert record(manual_id)['state'] == 'queued'
        assert submit(1)['final_reply']['status'] == 'admitted'
        third = f.wait(lambda: client_turn(2, 'release_reply'), 'normal manual injection and release')
        assert third['kind'] == 'manual' and third['dispatch_id'] == manual_id
        assert third['release_reply']['status'] == 'released'
        injection_order = [{'kind': turn['kind'], 'dispatch_id': turn['dispatch_id']}
                           for turn in f.clients_read()[0]['turns']]
        assert injection_order == [
            {'kind': 'review', 'dispatch_id': first['active_invocation']['dispatch_id']},
            {'kind': 'review', 'dispatch_id': second['active_invocation']['dispatch_id']},
            {'kind': 'manual', 'dispatch_id': manual_id}]
        b_claim = next(e['at'] for e in record(second_turn['dispatch_id'])['events'] if e['state'] == 'dispatched')
        manual_claim = next(e['at'] for e in record(manual_id)['events'] if e['state'] == 'dispatched')
        a_accepted = f.session(first['id'])['admitted_events'][0]['accepted_at']
        b_accepted = f.session(second['id'])['admitted_events'][0]['accepted_at']
        assert a_accepted <= b_claim and b_accepted <= manual_claim
        assert b_claim <= manual_claim
        for dispatch in (early['dispatch_id'], second_turn['dispatch_id'], manual_id):
            assert sum(e['state'] == 'dispatched' for e in record(dispatch)['events']) == 1
        # Client turn records are the fixture's transport journal, not queue_client storage.
        f.observations.append({'kind': 'actual_order_evidence', 'a_accepted_at': a_accepted,
            'b_claimed_at': b_claim, 'b_accepted_at': b_accepted, 'manual_claimed_at': manual_claim,
            'client_injection_order': injection_order,
            'journal_path': str(f.records / ('client-' + str(f.client_pid) + '.json'))})
        stopped = start()
        f.wait(lambda: client_turn(3, 'release_reply'), 'Stop review genuine injected/early released')
        f.api(f'/api/sessions/{stopped["id"]}/stop', {})
        late = submit(3)
        assert late['final_reply']['status'] == 'rejected'
        current = f.session(stopped['id'])
        assert current['stop_id'] and not current['admitted_events']
        assert any(m.get('metadata', {}).get('quarantine_session_id') == stopped['id'] for m in f.messages())
    assert len(f.captures) == 1 and len(f.clients_read()[0]['turns']) == 4
    assert f.session(first['id'])['admitted_events'][0]['content'] == 'ACTUAL_RECIPIENT_FINAL_0'
    assert f.session(second['id'])['admitted_events'][0]['content'] == 'ACTUAL_RECIPIENT_FINAL_1'
    return {'case': 'order', 'provider_calls': 1, 'cli_injections': 4,
            'actual_mcp_early_release': True, 'actual_late_stop_quarantine': True}


def family(f):
    f.api('/api/fixture/registry', {'action': 'family'})
    members = f.state()['registry_fixture']['family']
    with f.ws() as socket:
        body = {'text': '@familyfixture', 'selected_recipients': [], 'channel': 'family-run'}
        preview = f.api('/api/recipients/preview', body)
        assert preview['recipients'] == []
        assert preview['warnings'] == [{'kind': 'ambiguous', 'token': 'familyfixture',
                                       'candidates': sorted(v['name'] for v in members)}]
        message, ack = f.post(socket, body['text'], [], 'family-run')
        f.receipt(message, [], ack); f.quiet(0, 0)
        f.api('/api/fixture/registry', {'action': 'unique'})
        message, ack = f.post(socket, '@familyfixture unique now', [], 'family-run')
        f.receipt(message, [members[0]['identity_id']], ack)
        message, ack = f.post(socket, '@pendingfixture remains unavailable', [], 'family-run')
        assert f.receipt(message, [], ack)['warnings'][0]['kind'] == 'unavailable'
        f.quiet(1, 0)
    return {'case': 'family', 'provider_calls': 0, 'cli_injections': 0,
            'scope': 'real_server_registry_and_authenticated_ws_only_no_native_family_claim'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True, choices=('audience', 'order', 'family'))
    parser.add_argument('--compile-only', action='store_true')
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    assert not args.serve or args.case == 'audience'
    for case in ('audience', 'order', 'family'):
        compile(server_code(ROOT / '.audit-tmp/compile-recipient', 19000, case), '<generated-recipient-server>', 'exec')
    compile((ROOT / 'tools/fake_recipient_client.py').read_text(encoding='utf-8'), '<fake-recipient-client>', 'exec')
    if args.compile_only:
        print(json.dumps({'result': 'COMPILE_ONLY', 'generated_servers': 3, 'fake_clients': 1}))
        return
    if sys.platform != 'win32':
        raise SystemExit('Actual retained native Windows fixture required')
    f, result = Fixture(args.case), None
    try:
        f.setup()
        result = audience(f, args.serve) if args.case == 'audience' else order(f) if args.case == 'order' else family(f)
    except BaseException as exc:
        atomic_json(f.root / 'failure.json', {'case': args.case, 'error_type': type(exc).__name__,
            'provider_calls_observed': len(f.captures), 'scope': 'failed_run_not_acceptance'})
        raise
    finally:
        try:
            atomic_json(f.root / 'observations.json', f.observations)
        finally:
            f.close()
        if result is not None:
            result.update(result='PASS', scratch=str(f.root), cleanup=f.cleanup)
            atomic_json(f.root / 'result.json', result)
            print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
