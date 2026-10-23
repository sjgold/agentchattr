"""Isolated real HTTP/CLI/MCP stalled-turn acceptance, local fake models only.

--serve pauses at the original CLI stall. Browser QA may inspect/open/cancel
confirmation only; this script owns Retry. Write ticket12-browser-stop.txt.
Generic same-source relaunch is explicitly NOT a clean-context proof.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ctypes
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

POLICY = {'ack_timeout': 2, 'response_timeout': 3, 'monitor_interval': .1}
TWO = {'id': 'two-recovery', 'name': 'Accepted result then recovery', 'roles': ['reviewer', 'editor'],
       'phases': [{'name': 'Evidence', 'participants': ['reviewer'], 'prompt': 'Read exact source.'},
                  {'name': 'Result', 'participants': ['editor'], 'prompt': 'Use accepted evidence.', 'is_output': True}]}
ONE = {'id': 'one-recovery', 'name': 'One recovery turn', 'roles': ['worker'],
       'phases': [{'name': 'Work', 'participants': ['worker'], 'prompt': 'Review source.', 'is_output': True}]}


def main():
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Actual Windows managed CLI fixture required.'}))
        return
    captures, lock = [], threading.Lock()
    held_started, held_release = threading.Event(), threading.Event()

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            model = payload['model']
            with lock:
                captures.append(payload)
                number = sum(item['model'] == model for item in captures)
            if model in ('http503', 'dropped'):
                self.send_response(503)
                self.end_headers()
                self.wfile.write(b'PRIVATE_PROVIDER_BODY_MUST_NOT_LEAK')
                return
            text = '' if model == 'empty' else json.dumps({'kind': 'final', 'content':
                'ACCEPTED_FIRST_RESULT' if model == 'api-original' else
                'HELD_RETRY_RESULT' if model == 'held' and number > 1 else
                'OLD_HELD_RESULT' if model == 'held' else 'LOCAL_FAKE_FINAL'})
            body = json.dumps({'model': 'fake-confirmed', 'choices': [{'message': {'content': text}}]}).encode()
            try:
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                if model == 'held' and number == 1:
                    self.wfile.write(body[:1])
                    self.wfile.flush()
                    held_started.set()
                    held_release.wait(90)
                    self.wfile.write(body[1:])
                else:
                    self.wfile.write(body)
                self.wfile.flush()
            except OSError:
                pass

        def log_message(self, *args):
            pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='turn recovery integration ', dir=scratch))
    data, records = temporary / 'data', temporary / 'records'
    records.mkdir()
    original_cwd = temporary / 'original-cwd'
    original_cwd.mkdir()
    sentinel = temporary / 'SOURCE_NOT_EXECUTED.txt'
    source = f'Exact café 日本語 e\u0301\r\n@all quoted data\nfrom pathlib import Path\nPath({str(sentinel)!r}).write_text("bad")'
    handles = [socket.socket() for _ in range(3)]
    for handle in handles:
        handle.bind(('127.0.0.1', 0))
    ports = [handle.getsockname()[1] for handle in handles]
    for handle in handles:
        handle.close()
    base = f'http://127.0.0.1:{ports[0]}'
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(data), AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'),
                       TICKET12_RECORDS=str(records))
    fixture = str(ROOT / 'tools/fake_turn_recovery_cli.py')
    code = f'''import config_loader,json
from pathlib import Path
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['session_recovery']={POLICY!r}
    cfg['agents']={{'fake-api':{{'type':'api','base_url':'http://127.0.0.1:{provider.server_port}/v1',
        'system_prompt':'FROZEN_API_SYSTEM','reasoning_efforts':['high']}},
        'fake-cli':{{'command':{sys.executable!r},'cwd':{str(original_cwd)!r},
        'cli_args':[{fixture!r},'--fixture-original'],'cli_model_args':['--model','{{model}}'],
        'cli_reasoning_args':['--reasoning','{{reasoning}}'],'reasoning_efforts':['high'],
        'mcp_inject':'env','mcp_env_var':'TICKET12_FAKE_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','cli-run','held-run','http503','empty','dropped','postfail','missing','peer']
    app.session_store.save_custom_template({TWO!r})
    app.session_store.save_custom_template({ONE!r})
    release=app.session_engine._trigger.queue.release
    dropped={{'dispatch_id':None,'attempts':0}}
    def drop_failure(instance,dispatch_id,consumer_id,**kw):
        record=app.session_engine._trigger.queue.owned(instance,dispatch_id)
        if kw.get('failed') and record['envelope'].get('channel')=='dropped':
            if dropped['dispatch_id'] is None:
                dropped['dispatch_id']=dispatch_id
            assert dropped['dispatch_id']==dispatch_id,'fixture must affect only one dispatch receipt'
            dropped['attempts']+=1
            Path({str(records / 'dropped-report.json')!r}).write_text(json.dumps(dropped),encoding='utf-8')
            return record
        return release(instance,dispatch_id,consumer_id,**kw)
    app.session_engine._trigger.queue.release=drop_failure
    admit=app.session_engine.admit_event
    post_count={{'count':0}}
    def fail_post(brief_id,kind,content,instance,**kw):
        envelope=app.session_store.briefs.get(brief_id,instance)
        session=app.session_store.get(envelope['session_id'])
        if session['channel']=='postfail':
            post_count['count']+=1
            Path({str(records / 'postfail-count.json')!r}).write_text(json.dumps(post_count),encoding='utf-8')
            raise OSError('fixture result post unavailable')
        return admit(brief_id,kind,content,instance,**kw)
    app.session_engine.admit_event=fail_post
    prepare=app.api_seat_manager.prepare_retry_context
    def late_ingress(provenance,context_key,**kw):
        from turn_events import EventConflict
        if provenance['effective']['seat']['adapter']=='cli':
            instance=next((value for value in app.registry.get_all().values()
                           if value['identity_id']==provenance['identity_id']),None)
            run=next((value for value in app.session_store.list_all()
                      if value['run_id']==kw.get('binding',{{}}).get('child_run_id')),None)
            if instance and run:
                brief_id=run['active_invocation']['brief_id']
                try:
                    admit(brief_id,'final','CONTROLLED_OLD_CLI_INGRESS',instance)
                except EventConflict:
                    Path({str(records / 'controlled-late.json')!r}).write_text(json.dumps({{
                        'rejected':True,'identity_id':instance['identity_id'],'brief_id':brief_id}}),encoding='utf-8')
                else:
                    raise AssertionError('superseded old CLI event admitted')
        return prepare(provenance,context_key,**kw)
    app.api_seat_manager.prepare_retry_context=late_ingress
app.configure=configured
@app.app.post('/api/fixture/registry-seat')
async def fixture_registry(request:app.Request):
    body=await request.json()
    if body.get('remove'):
        app.registry.deregister(body['name'])
        return {{'removed':True}}
    app.registry.seed({{'fixture-no-worker':{{'type':'api','label':'No worker fixture'}}}})
    seat=app.registry.register('fixture-no-worker')
    return {{'name':seat['name'],'identity_id':seat['identity_id']}}
@app.app.post('/api/fixture/drift')
async def fixture_drift():
    app.api_seat_store.providers['fake-cli'].update(cli_args=[{fixture!r},'--edited'],cwd={str(ROOT)!r},mcp_env_var='EDITED_SETTINGS')
    return {{'edited':True}}
import run
run.main()
'''
    child, api, old_handle = None, None, None
    url_marker, stop_marker = scratch / 'ticket12-browser-url.txt', scratch / 'ticket12-browser-stop.txt'
    try:
        with (temporary / 'server.log').open('wb') as output:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)

        def wait_for(check, label, timeout=35):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                assert child.poll() is None, 'server exited; scratch: ' + str(temporary)
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
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)

        def reject(path, body, expected, headers=None):
            try:
                api(path, body, headers)
            except urllib.error.HTTPError as exc:
                assert exc.code == expected, f'expected HTTP{expected}, received {exc.code}'
            else:
                raise AssertionError('expected rejection: ' + path)

        def saved(session_id):
            return next(item for item in json.loads((data / 'session_runs.json').read_text('utf-8')) if item['id'] == session_id)

        def status(session_id):
            return api(f'/api/sessions/{session_id}/recovery-status')

        def count(model):
            with lock:
                return sum(item['model'] == model for item in captures)

        def clients():
            values = [json.loads(path.read_text('utf-8')) for path in records.glob('client-*.json')]
            for value in values:
                assert not value.get('error'), value.get('error')
            return values

        def stalled(session_id, reason):
            value = wait_for(lambda: item if (item := status(session_id))['state'] == 'stalled' else None, reason)
            assert value['turn_recovery']['reason'] == reason, value['turn_recovery']
            return value

        def start(channel, first, second=None, policy=None):
            return api('/api/sessions/start', {'template_id': TWO['id'] if second else ONE['id'], 'channel': channel,
                'cast': {'reviewer': first, 'editor': second} if second else {'worker': first},
                'goal': 'Retain accepted source and prior result.', 'input_text': source, 'recovery_policy': policy or POLICY})

        seat = {'reasoning': 'high', 'launch_profile': 'standard', 'secret_ref': '',
                'adapter': 'openai-compatible', 'provider': 'fake-api'}
        package = {'id': 'recovery-team', 'name': 'Recovery fixture', 'seats': [
            dict(seat, id='api', name='API evidence', model='api-original'),
            dict(seat, id='worker', name='API recovery', model='held'),
            dict(seat, id='cli', name='CLI recovery', adapter='cli', provider='fake-cli', model='cli-original')]}
        api('/api/preflight/packages', package)
        revision = api('/api/preflight/seats')['package_revisions']['recovery-team']
        api('/api/preflight/packages/recovery-team/launch', {'revision': revision})
        ready = wait_for(lambda: value if (value := api('/api/preflight/packages/recovery-team/status'))['ready'] else None, 'mixed seats ready')
        names = {key: ready['seats'][key]['name'] for key in ('api', 'worker', 'cli')}
        instances = json.loads((data / 'registry.json').read_text('utf-8'))['instances']
        owners = {key: instances[names[key]] for key in names}
        bearer = {key: {'Authorization': 'Bearer ' + owners[key]['token'], 'Content-Type': 'application/json'} for key in names}
        queue = QueueStore(data)
        old_client = wait_for(lambda: clients()[0] if len(clients()) == 1 else None, 'original fake console boot')
        (records / 'control.json').write_text(json.dumps({'old_pid': old_client['pid']}), encoding='utf-8')

        # A real blocked body and an authenticated old result, before provider progress.
        held = start('held-run', names['api'], names['worker'])
        assert held_started.wait(30), 'actual fake provider did not block in body read'
        stalled_held = stalled(held['id'], 'response_timeout')
        old_api = stalled_held['active_invocation']
        accepted = stalled_held['admitted_events']
        assert len(accepted) == 1 and accepted[0]['content'] == 'ACCEPTED_FIRST_RESULT'
        checkpoint = stalled_held['turn_recovery']['checkpoint_id']
        assert SessionStore(str(data / 'session_runs.json')).get(held['id'])['turn_recovery']['checkpoint_id'] == checkpoint
        before_calls = count('held')
        before_queue = (data / 'queue/ledger.json').read_bytes()
        waited = api(f'/api/sessions/{held["id"]}/wait', {'checkpoint_id': checkpoint, 'attempt_id': old_api['attempt_id'], 'extend_seconds': 10})
        for field in ('brief_id', 'attempt_id', 'dispatch_id'):
            assert waited['active_invocation'][field] == old_api[field]
        assert count('held') == before_calls == 1
        assert (data / 'queue/ledger.json').read_bytes() == before_queue
        request = {'checkpoint_id': checkpoint, 'attempt_id': old_api['attempt_id'], 'request_id': uuid.uuid4().hex}
        api(f'/api/sessions/{held["id"]}/retry', request)
        reject(f'/api/sessions/{held["id"]}/event', {'brief_id': old_api['brief_id'], 'kind': 'final',
               'content': 'OLD_HTTP_LATE_RESULT'}, 409, bearer['worker'])
        complete = wait_for(lambda: item if (item := saved(held['id']))['state'] == 'complete' else None, 'held API retry completion')
        assert not held_release.is_set(), 'local child cancellation was masked by provider progress'
        old_transport = queue.owned(owners['worker'], old_api['dispatch_id'])
        assert old_transport['state'] == 'cancelled'
        assert old_transport['cancellation']['status'] == 'local_ended'
        assert old_transport['cancellation']['remote_compute'] == 'unverified'
        assert any(event['state'] == 'cancelled' for event in old_transport['events'])
        assert complete['admitted_events'][0] == accepted[0] and len(complete['admitted_events']) == 2
        assert complete['admitted_events'][1]['content'] == 'HELD_RETRY_RESULT'
        assert complete['input_snapshot']['text'] == source and count('held') == 2
        held_payload = next(item for item in reversed(captures) if item['model'] == 'held')
        source_message = next(json.loads(item['content']) for item in held_payload['messages']
                              if 'untrusted_review_source' in item['content'])
        assert source_message['text'] == source
        assert 'ACCEPTED_FIRST_RESULT' in json.dumps(held_payload['messages'])
        api(f'/api/sessions/{held["id"]}/retry', request)
        assert count('held') == 2
        assert any(item['content'] == 'OLD_HTTP_LATE_RESULT' for item in saved(held['id'])['quarantined_events'])
        held_release.set()

        # Real provider/empty/post failures each generate once and admit nothing.
        failures = {}
        for model, reason in (('http503', 'http_error'), ('empty', 'empty_completion'),
                              ('postfail', 'local_delivery_failure'), ('dropped', 'response_timeout')):
            package['seats'][1]['model'] = model
            api('/api/preflight/packages', package)
            api('/api/preflight/seats/recovery-team/worker/launch', {'restart': True})
            current_worker = wait_for(lambda: item if (item := api('/api/preflight/seats')['runtime']['recovery-team/worker'])['state'] == 'ready' else None, 'API worker restart')
            failure_start = time.monotonic()
            run = start(model, current_worker['name'], policy=POLICY if model == 'dropped' else {**POLICY, 'response_timeout': 15})
            failed = stalled(run['id'], reason)
            assert count(model) == 1 and failed['admitted_events'] == []
            assert failed['turn_recovery']['recoverable_result'] is False
            assert 'PRIVATE_PROVIDER_BODY' not in json.dumps(failed['turn_recovery'])
            if model == 'http503':
                assert failed['turn_recovery']['reason'] == 'http_error'
                assert failed['turn_recovery']['http_status'] == 503
            if model != 'dropped':
                assert time.monotonic() - failure_start < 10, 'explicit failure waited for the response deadline'
            if model == 'postfail':
                assert json.loads((records / 'postfail-count.json').read_text('utf-8'))['count'] == 3
            if model == 'dropped':
                identity = json.loads((data / 'registry.json').read_text('utf-8'))['instances'][current_worker['name']]
                record = queue.owned(identity, failed['active_invocation']['dispatch_id'])
                assert record['state'] == 'acknowledged', 'dropped report must not manufacture a failure receipt'
                heartbeat = {'Authorization': 'Bearer ' + identity['token'], 'Content-Type': 'application/json'}
                for _ in range(3):
                    api('/api/heartbeat/' + identity['name'], {'active': True}, heartbeat)
                    assert status(run['id'])['turn_recovery']['reason'] == 'response_timeout'
            failures[model] = reason
            api(f'/api/sessions/{run["id"]}/stop', {})
            if model == 'empty':
                identity = json.loads((data / 'registry.json').read_text('utf-8'))['instances'][current_worker['name']]
                reject(f'/api/sessions/{run["id"]}/event', {'brief_id': failed['active_invocation']['brief_id'],
                    'kind': 'final', 'content': 'STOPPED_LATE_RESULT'}, 409,
                    {'Authorization': 'Bearer ' + identity['token'], 'Content-Type': 'application/json'})
                assert saved(run['id'])['quarantined_events'][-1]['content'] == 'STOPPED_LATE_RESULT'

        # Missing receipt and absent identity are separate registry-only fixtures.
        no_worker = api('/api/fixture/registry-seat', {})
        missing = start('missing', no_worker['name'])
        missing_state = stalled(missing['id'], 'missing_ack')
        api('/api/fixture/registry-seat', {'remove': True, 'name': no_worker['name']})
        wait_for(lambda: status(missing['id'])['turn_recovery']['reason'] == 'disconnected', 'disconnected checkpoint')
        api(f'/api/sessions/{missing["id"]}/stop', {})

        # Generic real console retries only after exact owned termination proof.
        cli_run = start('cli-run', names['api'], names['cli'])
        old_record = wait_for(lambda: item if 'envelope' in (item := clients()[0]) else None, 'old actual CLI injected brief')
        cli_stall = stalled(cli_run['id'], 'response_timeout')
        old_invocation = cli_stall['active_invocation']
        assert old_record['envelope']['source'] == source
        assert len(old_record['prompts']) == 1
        cli_body = {'checkpoint_id': cli_stall['turn_recovery']['checkpoint_id'],
                    'attempt_id': old_invocation['attempt_id'], 'request_id': uuid.uuid4().hex}
        retry_path = f'/api/sessions/{cli_run["id"]}/retry'
        reject(retry_path, cli_body, 409)
        reject(retry_path, {**cli_body, 'confirmation': {'confirm': True, 'launch_attempt': '0' * 32}}, 409)
        assert len(clients()) == 1 and len(clients()[0]['prompts']) == 1
        if '--serve' in sys.argv:
            url = base + '/?channel=cli-run'
            url_marker.write_text(url, encoding='utf-8')
            print(json.dumps({'stage': 'recovery_browser_qa_ready', 'url': url, 'cli_session_id': cli_run['id'],
                'channel': 'cli-run', 'inspection_only': True, 'stop_sentinel': str(stop_marker), 'scratch': str(temporary)}), flush=True)
            deadline = time.monotonic() + 600
            while child.poll() is None and not stop_marker.exists():
                assert time.monotonic() < deadline, 'browser QA sentinel deadline'
                time.sleep(.5)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        old_handle = kernel.OpenProcess(0x00100000, False, old_record['pid'])
        assert old_handle, 'could not retain owned fixture child handle'
        package['seats'][2]['model'] = 'edited-cli-model'
        api('/api/preflight/packages', package)
        reject('/api/fixture/drift', {}, 403, bearer['api'])
        api('/api/fixture/drift', {})
        confirmed = {**cli_body, 'confirmation': {'confirm': True, 'launch_attempt': ready['seats']['cli']['attempt']}}
        pending = api(retry_path, confirmed)
        assert pending['state'] == 'retrying'
        context = pending['pending_retry']['context']
        assert context['clean_context'] is False and context['verification_basis'] == 'same_turn_retry_relaunch'
        assert kernel.WaitForSingleObject(old_handle, 0) == 0, 'original actual CLI child still alive'
        controlled = json.loads((records / 'controlled-late.json').read_text('utf-8'))
        assert controlled == {'rejected': True, 'identity_id': old_invocation['expected_identity_id'],
                              'brief_id': old_invocation['brief_id']}
        assert any(item['content'] == 'CONTROLLED_OLD_CLI_INGRESS'
                   for item in saved(cli_run['id'])['quarantined_events'])
        fresh = wait_for(lambda: item if len(items := clients()) == 2 and 'envelope' in
                         (item := next(value for value in items if value['pid'] != old_record['pid'])) else None,
                         'one actual retry injection after ready')
        assert fresh['model'] == 'cli-original' and fresh['reasoning'] == 'high'
        assert fresh['cwd'] == str(original_cwd) and fresh['argv'] == old_record['argv']
        assert len(fresh['prompts']) == 1 and len(clients()[0]['prompts']) == 1
        new = fresh['envelope']
        for field in ('brief_id', 'attempt_id', 'dispatch_id'):
            if field in new:
                assert new[field] != old_invocation[field]
        for field in ('run_id', 'turn_id', 'input_revision'):
            assert new[field] == old_invocation[field]
        assert new['source'] == source and 'ACCEPTED_FIRST_RESULT' in json.dumps(new['prior_results'])
        assert new['expected_identity_id'] != old_invocation['expected_identity_id']
        api(retry_path, confirmed)
        assert len(clients()) == 2 and len(fresh['prompts']) == 1
        assert api('/api/preflight/seats')['runtime']['recovery-team/api']['attempt'] == ready['seats']['api']['attempt']
        (records / 'new-may-submit').touch()
        done = wait_for(lambda: item if (item := saved(cli_run['id']))['state'] == 'complete' else None, 'CLI typed final')
        assert len(done['admitted_events']) == 2
        assert done['admitted_events'][1]['content'].startswith('CLI_RETRY_FINAL')
        (records / 'new-may-release').touch()
        wait_for(lambda: any(item.get('release') for item in clients() if item['pid'] == fresh['pid']), 'separate MCP transport release')
        peer = start('peer', names['api'])
        wait_for(lambda: saved(peer['id'])['state'] == 'complete', 'unchanged API peer usable')
        assert not sentinel.exists(), 'source was executed'
        print(json.dumps({'result': 'PASS', 'failures': failures, 'held_provider_calls': count('held'),
            'postfail_provider_calls': count('postfail'), 'postfail_submission_attempts': 3,
            'missing_ack_and_disconnected_distinct': True, 'cli_processes': 2,
            'generic_clean_context': False, 'old_native_exit_observed': True,
            'same_source_prior_result_retained': True, 'scratch': str(temporary)}), flush=True)
    finally:
        held_release.set()
        if api is not None and child is not None and child.poll() is None:
            # Stop only managed workers in this fixture, including retry keys.
            try:
                runtime = api('/api/preflight/seats')['runtime']
                for key in runtime:
                    try:
                        api('/api/preflight/seats/' + key + '/stop', {})
                    except OSError:
                        pass
            except OSError:
                pass
        if old_handle:
            kernel.CloseHandle(old_handle)
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
