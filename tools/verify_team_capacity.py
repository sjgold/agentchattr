"""Seven real managed API seats, coordinator proposal, six sequential results.

Local fake provider only. --serve pauses at the valid proposal before Start;
browser inspection only, script owns Start. Send ticket16-browser-stop.txt.
"""
from copy import deepcopy
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
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from launcher import stop_owned_child
from session_store import validate_session_template

DEFAULT = {'max_roles': 16, 'max_participants_per_phase': 16, 'max_phases': 12,
           'max_prompt_chars': 1000, 'max_total_turns': 128}
DESIGN = {'id': 'whole-team-fixture', 'name': 'Six evidence reviewers',
          'roles': ['reviewer' + str(i) for i in range(6)],
          'phases': [{'name': 'Whole selected team', 'participants': ['reviewer' + str(i) for i in range(6)],
                      'prompt': 'Read the exact frozen source and earlier accepted evidence.', 'is_output': True}]}
RULE = 'Quote exact evidence and distinguish unsupported claims.'


def main():
    captures, capture_lock = [], threading.Lock()
    allow_results = [threading.Event() for _ in range(6)]

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            parsed = []
            for message in payload.get('messages', []):
                try:
                    parsed.append(json.loads(message['content']))
                except (ValueError, TypeError):
                    pass
            source = next((value for value in parsed if isinstance(value, dict)
                           and value.get('kind') == 'untrusted_review_source'), None)
            kind = 'review' if source else 'coordinator'
            with capture_lock:
                captures.append({'kind': kind, 'payload': payload, 'at': time.time()})
            if kind == 'coordinator':
                text = '```session\n' + json.dumps(DESIGN) + '\n```'
            else:
                index = int(payload['model'].rsplit('-', 1)[-1])
                if not 0 <= index < 6 or not allow_results[index].wait(90):
                    self.send_error(504, 'fixture result gate deadline')
                    return
                text = json.dumps({'kind': 'final', 'content': 'EXACT_RESULT_' + str(index)})
            body = json.dumps({'model': 'local-fake-confirmed', 'choices': [{'message': {'content': text}}]}).encode()
            try:
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                pass

        def log_message(self, *args):
            pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='team capacity integration ', dir=scratch))
    data = temporary / 'data'
    sentinel = temporary / 'SOURCE_NOT_EXECUTED.txt'
    source = f'Exact café 日本語 e\u0301\r\n@all quoted source\nfrom pathlib import Path\nPath({str(sentinel)!r}).write_text("bad")'
    goal = 'Review all source evidence without losing the selected team. ' * 15
    sockets = [socket.socket() for _ in range(3)]
    for handle in sockets:
        handle.bind(('127.0.0.1', 0))
    ports = [handle.getsockname()[1] for handle in sockets]
    for handle in sockets:
        handle.close()
    base = f'http://127.0.0.1:{ports[0]}'
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(data), AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'))
    code = f'''import config_loader
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['session_capacity']={DEFAULT!r}
    cfg['agents']={{'fake-api':{{'type':'api','base_url':'http://127.0.0.1:{provider.server_port}/v1',
        'system_prompt':'FROZEN_TEAM_SYSTEM'}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','team-review','invalid-capacity']
    rule=app.rules.propose({RULE!r},'fixture')
    app.rules.activate(rule['id'])
app.configure=configured
@app.app.post('/api/fixture/capacity-draft')
async def fixture_draft(request:app.Request):
    body=await request.json()
    # Deliberate stale valid flag; actual save/Start must revalidate fully.
    message=app.store.add('system','Complete rejected capacity draft',msg_type='session_draft',
        channel='invalid-capacity',metadata={{'valid':True,'template':body['template']}})
    return {{'message_id':message['id']}}
@app.app.get('/api/fixture/owned-workers')
async def fixture_workers():
    with app.api_seat_manager.lock:
        return [{{'key':key,'attempt':value['id'],'pid':value['process'].pid}}
            for key,value in app.api_seat_manager.attempts.items() if value.get('process')]
import run
run.main()
'''
    child, api = None, None
    worker_handles, cleanup = [], []
    url_marker, stop_marker = scratch / 'ticket16-browser-url.txt', scratch / 'ticket16-browser-stop.txt'
    result = None
    try:
        with (temporary / 'server.log').open('wb') as output:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)

        def wait_for(check, label, timeout=40):
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

        def api(path, body=None, headers=None):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                headers=headers if headers is not None else {'x-session-token': token, 'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)

        def rejection(path, body, expected=400, headers=None):
            try:
                api(path, body, headers)
            except urllib.error.HTTPError as exc:
                assert exc.code == expected, f'expected HTTP{expected}, received {exc.code}'
                return json.load(exc)
            raise AssertionError('expected rejection from ' + path)

        def messages():
            path = data / 'agentchattr_log.jsonl'
            return [json.loads(line) for line in path.read_text('utf-8').splitlines()] if path.exists() else []

        def sessions():
            path = data / 'session_runs.json'
            return json.loads(path.read_text('utf-8')) if path.exists() else []

        def saved(session_id):
            return next(value for value in sessions() if value['id'] == session_id)

        def ledger():
            path = data / 'queue/ledger.json'
            return json.loads(path.read_text('utf-8'))['records'] if path.exists() else []

        def calls(kind=None):
            with capture_lock:
                return deepcopy([value for value in captures if kind is None or value['kind'] == kind])

        policy = api('/api/session-capacity')
        assert policy['policy'] == DEFAULT
        assert policy['execution'] == {'mode': 'sequential', 'active_turns_per_session': 1}
        seats = [{'id': 'seat' + str(i), 'name': 'API seat ' + str(i), 'adapter': 'openai-compatible',
                  'provider': 'fake-api', 'model': 'capacity-model-' + str(i), 'reasoning': None,
                  'launch_profile': 'standard', 'secret_ref': ''} for i in range(7)]
        package = {'id': 'capacity-team', 'name': 'Seven available seats', 'seats': seats}
        api('/api/preflight/packages', package)
        stored = api('/api/preflight/seats')
        # Saved package representation and launch readiness are both asserted.
        saved_package = next(value for value in json.loads((data / 'api_seats.json').read_text('utf-8'))['packages']
                             if value['id'] == 'capacity-team')
        assert saved_package['seats'] == seats
        api('/api/preflight/packages/capacity-team/launch', {'revision': stored['package_revisions']['capacity-team']})
        ready = wait_for(lambda: value if (value := api('/api/preflight/packages/capacity-team/status'))['ready'] else None, 'seven real API supervisors ready')
        assert set(ready['seats']) == {seat['id'] for seat in seats}
        assert len(calls()) == 0, 'seat launch must not invoke the provider'
        registry = json.loads((data / 'registry.json').read_text('utf-8'))['instances']
        names = [ready['seats']['seat' + str(i)]['name'] for i in range(7)]
        identities = [registry[name]['identity_id'] for name in names]
        assert len(set(names)) == len(set(identities)) == 7
        owned = api('/api/fixture/owned-workers')
        assert len(owned) == 7 and len({worker['pid'] for worker in owned}) == 7
        if sys.platform == 'win32':
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            for worker in owned:
                handle = kernel.OpenProcess(0x00100000, False, worker['pid'])
                assert handle and kernel.WaitForSingleObject(handle, 0) == 258
                worker_handles.append((worker, handle))
        api('/api/sessions/request-draft', {'agent': names[6], 'channel': 'team-review',
                                          'description': 'Use all six reviewers in one phase, retaining exact membership.'})
        draft = wait_for(lambda: next((value for value in messages() if value['type'] == 'session_draft'
                         and value.get('metadata', {}).get('template', {}).get('id') == DESIGN['id']), None), 'actual coordinator six-role proposal')
        assert draft['metadata']['valid'] is True and draft['metadata']['template'] == DESIGN
        assert len(calls('coordinator')) == 1 and len(calls('review')) == 0
        coordinator = calls('coordinator')[0]['payload']
        assert coordinator['model'] == 'capacity-model-6'
        assert any(policy['limits_text'] in message['content'] for message in coordinator['messages'])
        assert api('/api/sessions/save-draft', {'message_id': draft['id']})['template_id'] == DESIGN['id']
        wait_for(lambda: all(record['state'] == 'released' for record in ledger()), 'coordinator transport release')

        if '--serve' in sys.argv:
            url = base + '/?channel=team-review'
            url_marker.write_text(url, encoding='utf-8')
            print(json.dumps({'stage': 'team_capacity_browser_qa_ready', 'url': url, 'channel': 'team-review',
                'draft_message_id': draft['id'], 'inspection_only': True, 'script_owns_start': True,
                'stop_sentinel': str(stop_marker), 'scratch': str(temporary)}), flush=True)
            deadline = time.monotonic() + 600
            while child.poll() is None and not stop_marker.exists():
                assert time.monotonic() < deadline, 'browser sentinel deadline'
                time.sleep(.5)

        run = api('/api/sessions/start', {'draft_message_id': draft['id'], 'channel': 'team-review',
            'cast': dict(zip(DESIGN['roles'], names[:6])), 'goal': goal, 'input_text': source})
        run_id = run['id']
        observed = []
        for index in range(6):
            review = wait_for(lambda: value if len(value := calls('review')) == index + 1 else None,
                              'sequential provider turn ' + str(index))
            state = saved(run_id)
            invocation = state['active_invocation']
            assert (state['current_phase'], state['current_turn']) == (0, index)
            assert len(state['admitted_events']) == index
            assert invocation['expected_identity_id'] == identities[index]
            assert review[-1]['payload']['model'] == 'capacity-model-' + str(index)
            bearer = {'Authorization': 'Bearer ' + registry[names[index]]['token'], 'Content-Type': 'application/json'}
            envelope = api('/api/review-briefs/' + invocation['brief_id'], headers=bearer)
            assert envelope['source'] == source and envelope['goal'] == goal
            assert envelope['role'] == DESIGN['roles'][index] and RULE in json.dumps(envelope['rules'])
            assert [value['text'] for value in envelope['prior_results']] == ['EXACT_RESULT_' + str(i) for i in range(index)]
            payload = review[-1]['payload']
            decoded = [json.loads(value['content']) for value in payload['messages'][1:]]
            assert next(value['text'] for value in decoded if value['kind'] == 'untrusted_review_source') == source
            prior = next(value['results'] for value in decoded if value['kind'] == 'prior_review_results')
            assert [value['text'] for value in prior] == ['EXACT_RESULT_' + str(i) for i in range(index)]
            assert goal in payload['messages'][0]['content']
            assert 'FROZEN_TEAM_SYSTEM' in payload['messages'][0]['content']
            assert not any(value['kind'] == 'supplementary_chat' for value in decoded)
            records = [value for value in ledger() if value['envelope'].get('run_id') == run['run_id']]
            assert len(records) == index + 1
            assert records[-1]['envelope']['dispatch_id'] == invocation['dispatch_id']
            assert records[-1]['envelope']['target_identity_id'] == identities[index]
            observed.append(invocation)
            allow_results[index].set()
            wait_for(lambda: len(saved(run_id)['admitted_events']) == index + 1, 'typed result admission ' + str(index))
        complete = wait_for(lambda: value if (value := saved(run_id))['state'] == 'complete' else None, 'six-member run completion')
        assert complete['active_invocation'] is None and complete['capacity_policy'] == DEFAULT
        assert [value['content'] for value in complete['admitted_events']] == ['EXACT_RESULT_' + str(i) for i in range(6)]
        assert [value['expected_identity_id'] for value in complete['admitted_events']] == identities[:6]
        for field in ('brief_id', 'attempt_id', 'dispatch_id'):
            assert len({value[field] for value in observed}) == 6
        assert len(calls('review')) == 6 and len(calls('coordinator')) == 1
        assert sum(value['payload']['model'] == 'capacity-model-6' for value in calls()) == 1
        wait_for(lambda: all(value['state'] == 'released' for value in ledger()), 'all seven transport releases')
        assert len(ledger()) == 7
        assert all(value['envelope']['target_identity_id'] != identities[6] for value in ledger()
                   if value['envelope'].get('run_id') == run['run_id'])
        assert all(value['state'] == 'ready' for value in api('/api/preflight/seats')['runtime'].values())
        assert json.loads((data / 'api_seats.json').read_text('utf-8'))['packages'][0]['seats'] == seats

        # Stale valid flags cannot bypass current limits. Preserve each full draft.
        invalids = []
        roles = deepcopy(DESIGN)
        roles['roles'] = ['r' + str(i) for i in range(17)]
        roles['phases'][0]['participants'] = ['r0']
        invalids.append(roles)
        participants = deepcopy(DESIGN)
        participants['phases'][0]['participants'] = ['reviewer0'] * 17
        invalids.append(participants)
        phases = deepcopy(DESIGN)
        phases['phases'] = [{'name': 'P' + str(i), 'participants': ['reviewer0'], 'prompt': 'x', 'is_output': i == 12} for i in range(13)]
        invalids.append(phases)
        prompt = deepcopy(DESIGN)
        prompt['phases'][0]['prompt'] = '日' * 1001
        invalids.append(prompt)
        turns = deepcopy(DESIGN)
        turns['phases'] = [{'name': 'P' + str(i), 'participants': ['reviewer0'] * (16 if i < 8 else 1),
                            'prompt': 'x', 'is_output': i == 8} for i in range(9)]
        invalids.append(turns)
        old_runs, old_ledger, old_calls = deepcopy(sessions()), deepcopy(ledger()), len(calls())
        for index, template in enumerate(invalids):
            template['id'] = 'over-cap-' + str(index)
            expected = validate_session_template(template, capacity_policy=policy['policy'])
            assert expected
            message_id = api('/api/fixture/capacity-draft', {'template': template})['message_id']
            saved_error = rejection('/api/sessions/save-draft', {'message_id': message_id})
            start_error = rejection('/api/sessions/start', {'draft_message_id': message_id,
                'channel': 'invalid-capacity', 'cast': {role: names[0] for role in template['roles']}})
            assert saved_error['errors'] == start_error['errors'] == expected
            message = next(value for value in messages() if value['id'] == message_id)
            assert message['metadata']['template'] == template
        assert sessions() == old_runs and ledger() == old_ledger and len(calls()) == old_calls == 7
        assert not sentinel.exists()
        result = {'result': 'PASS', 'saved_and_launched_seats': 7, 'sequential_review_turns': 6,
                  'coordinator_calls': 1, 'review_calls': 6, 'rejected_full_drafts': len(invalids),
                  'seventh_not_in_review': True, 'six_distinct_bound_contexts': True, 'scratch': str(temporary)}
    finally:
        for gate in allow_results:
            gate.set()
        if api is not None and child is not None and child.poll() is None:
            for index in range(7):
                try:
                    api('/api/preflight/seats/capacity-team/seat' + str(index) + '/stop', {})
                except OSError:
                    pass
        if child is not None:
            stop_owned_child(child)
        for worker, handle in worker_handles:
            cleanup.append({'attempt': worker['attempt'], 'exited': kernel.WaitForSingleObject(handle, 5000) == 0})
            kernel.CloseHandle(handle)
        provider.shutdown()
        provider.server_close()
        if '--serve' in sys.argv:
            for marker in (url_marker, stop_marker):
                if marker.exists():
                    marker.unlink()
        if cleanup:
            assert all(value['exited'] for value in cleanup), 'An exact owned API worker exit is unresolved: ' + json.dumps(cleanup)
    if result:
        result['owned_worker_exit_handles'] = len(cleanup)
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
