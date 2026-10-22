"""Real isolated corrected lineage, frozen launch settings and fresh CLI/MCP reads.

--serve pauses after clean contexts are ready and before activation. Write
.audit-tmp/ticket11-browser-stop.txt to resume idempotent activation/assertions.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ctypes
import hashlib
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

OLD_SOURCE = 'OLD_SOURCE mistaken café\r\n@all quoted as data.'
OLD_ANSWER = 'OLD_CONTINUATION use the full mistaken source.'
NEW_SOURCE = 'NEW_SOURCE corrected 日本語 e\u0301 🐙\r\nExact new quoted source. @all is data.'
GOAL = 'Explain the source evidence and editorial decision. ' * 20
RULE = 'Quote exact source text and label unsupported claims.'
TEMPLATE = {'id': 'restart-fixture', 'name': 'Corrected mixed review', 'roles': ['reviewer', 'editor'],
    'phases': [{'name': 'Evidence', 'participants': ['reviewer'], 'prompt': 'Review exact source evidence.'},
               {'name': 'Editorial result', 'participants': ['editor'], 'prompt': 'Explain the editorial result.', 'is_output': True}]}
PEER = {'id': 'peer-fixture', 'name': 'Independent peer', 'roles': ['reviewer'],
    'phases': [{'name': 'Peer work', 'participants': ['reviewer'], 'prompt': 'Review independently.', 'is_output': True}]}


def main():
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Actual Windows managed CLI required.'}))
        return
    captures, old_calls = [], []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            captures.append({'path': self.path, 'payload': payload})
            parsed = []
            for message in payload['messages']:
                try:
                    parsed.append(json.loads(message['content']))
                except ValueError:
                    pass
            source = next(item['text'] for item in parsed if isinstance(item, dict) and item.get('kind') == 'untrusted_review_source')
            if payload['model'] == 'peer-original':
                event = {'kind': 'final', 'content': 'PEER_RESULT independently complete.'}
            elif source == OLD_SOURCE:
                old_calls.append(payload)
                event = ({'kind': 'question', 'content': 'Which source should I inspect?'} if len(old_calls) == 1 else
                         {'kind': 'final', 'content': 'OLD_RESULT accepted mistaken-source finding.'})
            else:
                event = {'kind': 'final', 'content': 'NEW_API_RESULT corrected source finding.'}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'model': 'fake-confirmed', 'choices': [{'message': {'content': json.dumps(event)}}]}).encode())

        def log_message(self, *args):
            pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='corrected restart integration ', dir=scratch))
    data, records = temporary / 'data', temporary / 'records'
    records.mkdir()
    original_cwd, edited_cwd = temporary / 'original-cwd', temporary / 'edited-cwd'
    original_cwd.mkdir()
    edited_cwd.mkdir()
    sockets = [socket.socket() for _ in range(3)]
    for handle in sockets:
        handle.bind(('127.0.0.1', 0))
    ports = [handle.getsockname()[1] for handle in sockets]
    for handle in sockets:
        handle.close()
    base = f'http://127.0.0.1:{ports[0]}'
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(data), AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'), TICKET11_RECORDS=str(records))
    fixture = str((ROOT / 'tools/fake_corrected_restart_cli.py').resolve())
    code = f'''import config_loader,json,uuid
from copy import deepcopy
from pathlib import Path
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['agents']={{'fake-api':{{'type':'api','base_url':'http://127.0.0.1:{provider.server_port}/v1',
        'system_prompt':'FROZEN_API_SYSTEM','reasoning_efforts':['high']}},
        'fake-cli':{{'command':{sys.executable!r},'cwd':{str(original_cwd)!r},
        'cli_args':[{fixture!r},'--fixture-original'],'cli_model_args':['--model','{{model}}'],
        'cli_reasoning_args':['--reasoning','{{reasoning}}'],'reasoning_efforts':['high'],
        'mcp_inject':'env','mcp_env_var':'TICKET11_FAKE_SETTINGS',
        'cli_fresh_context_args':['--context-id','{{context_id}}'],'cli_fresh_context_verified':True}}}}
    return cfg
config_loader.load_config=isolated
import app
configure=app.configure
def configured(*args,**kwargs):
    configure(*args,**kwargs)
    app.room_settings['channels']=['general','restart-run','peer-run']
    app.session_store.save_custom_template({TEMPLATE!r})
    app.session_store.save_custom_template({PEER!r})
    rule=app.rules.propose({RULE!r},'fixture')
    app.rules.activate(rule['id'])
    app.store.add('system','OLD_HISTORY '+{OLD_SOURCE!r}+' OLD_RESULT old answer OLD_CONTINUATION old answer',channel='restart-run')
    app.summaries.write('restart-run','OLD_SUMMARY '+{OLD_SOURCE!r},'fixture')
    job=app.jobs.create('OLD_JOB','question','restart-run','fixture',body={OLD_SOURCE!r})
    Path({str(records / 'control.json')!r}).write_text(json.dumps({{'channel':'restart-run','job_id':job['id']}}),encoding='utf-8')
    update=app.session_store._event_update
    fault={{'done':False}}
    def interrupted_backlink(session_id,change,action='update'):
        current=app.session_store.get(session_id)
        if not fault['done'] and current and current.get('parent_run_id') and current['state']=='prepared':
            candidate=deepcopy(current)
            change(candidate)
            editor=candidate.get('preparation_contexts',{{}}).get('editor',{{}})
            if editor.get('context_id'):
                fault['done']=True
                Path({str(records / 'backlink-fault.json')!r}).write_text(json.dumps({{'child_id':session_id,
                    'context_id':editor['context_id'],'launch_attempt':editor['launch_attempt'],'key':editor['key']}}),encoding='utf-8')
                raise OSError('Fixture interrupted fresh context backlink')
        return update(session_id,change,action)
    app.session_store._event_update=interrupted_backlink
app.configure=configured
@app.app.post('/api/fixture/restart-drift')
async def fixture_drift():
    app.api_seat_store.providers['fake-api'].update(base_url='http://127.0.0.1:{provider.server_port}/edited/v1',system_prompt='EDITED_SYSTEM_MUST_NOT_ENTER')
    app.api_seat_store.providers['fake-cli'].update(cli_args=[{fixture!r},'--edited-resume'],cwd={str(edited_cwd)!r},mcp_env_var='EDITED_MCP_SETTINGS',cli_fresh_context_verified=False)
    app.session_store.get_template('restart-fixture')['phases']=[{{'name':'EDITED_DESIGN','participants':['reviewer'],'is_output':True}}]
    return {{'drifted':True}}
import run
run.main()
'''
    child, api, old_handle = None, None, None
    url_marker, stop_marker = scratch / 'ticket11-browser-url.txt', scratch / 'ticket11-browser-stop.txt'
    try:
        with (temporary / 'server.log').open('wb') as output:
            child = subprocess.Popen([sys.executable, '-u', '-c', code], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)

        def wait_for(check, label, timeout=35):
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
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)

        def rejected(path, body, code, headers=None):
            try:
                api(path, body, headers)
            except urllib.error.HTTPError as exc:
                assert exc.code == code, f'expected HTTP{code}, received {exc.code}'
            else:
                raise AssertionError('Expected rejection from ' + path)

        def saved(session_id):
            return next(value for value in json.loads((data / 'session_runs.json').read_text('utf-8')) if value['id'] == session_id)

        def client(context_id=None):
            value = json.loads((records / ('client-' + (context_id or 'original') + '.json')).read_text('utf-8'))
            if value.get('error'):
                raise AssertionError('fake CLI failed: ' + value['error'])
            return value

        common = {'reasoning': 'high', 'launch_profile': 'standard', 'secret_ref': ''}
        api_seat = dict(common, id='api', name='API reviewer', adapter='openai-compatible', provider='fake-api', model='api-original')
        package = {'id': 'restart-team', 'name': 'Restart team', 'seats': [api_seat,
            dict(common, id='cli', name='CLI editor', adapter='cli', provider='fake-cli', model='cli-original'),
            dict(common, id='peer', name='Unrelated peer', adapter='openai-compatible', provider='fake-api', model='peer-original')]}
        api('/api/preflight/packages', package)
        revision = api('/api/preflight/seats')['package_revisions']['restart-team']
        api('/api/preflight/packages/restart-team/launch', {'revision': revision})
        ready = wait_for(lambda: value if (value := api('/api/preflight/packages/restart-team/status'))['ready'] else None, 'mixed seats ready')
        names = {key: ready['seats'][key]['name'] for key in ('api', 'cli', 'peer')}
        instances = json.loads((data / 'registry.json').read_text('utf-8'))['instances']
        api_headers = {'Authorization': 'Bearer ' + instances[names['api']]['token'], 'Content-Type': 'application/json'}
        parent = api('/api/sessions/start', {'template_id': 'restart-fixture', 'channel': 'restart-run',
            'cast': {'reviewer': names['api'], 'editor': names['cli']}, 'goal': GOAL, 'input_text': OLD_SOURCE})
        question = wait_for(lambda: value if (value := saved(parent['id']))['state'] == 'awaiting_input' else None, 'old API question')
        api(f'/api/sessions/{parent["id"]}/continue', {'question_event_id': question['current_question']['event_id'], 'answer': OLD_ANSWER})
        old = wait_for(lambda: value if 'envelope' in (value := client()) else None, 'old CLI exact wrong-source context')
        assert old['envelope']['source'] == OLD_SOURCE
        assert old['context_id'] is None and '--context-id' not in old['argv']
        assert old['model'] == 'cli-original' and old['reasoning'] == 'high'
        assert len(old_calls) == 2
        api(f'/api/sessions/{parent["id"]}/stop', {})
        wait_for(lambda: api(f'/api/sessions/{parent["id"]}/stop-status')['state'] == 'unresolved', 'old actual10s unresolved', timeout=14)
        (records / 'emit-old-late').touch()
        wait_for(lambda: value if 'late_response' in (value := client()) else None, 'old CLI late result rejection')
        assert client()['late_response']['status'] == 'rejected'
        old_parent = saved(parent['id'])
        old_final = next(event for event in old_parent['admitted_events'] if event['kind'] == 'final')
        assert old_final['content'].startswith('OLD_RESULT') and old_parent['continuation_context']
        package['seats'][0]['model'] = 'api-edited'
        package['seats'][1]['model'] = 'cli-edited'
        api('/api/preflight/packages', package)
        # This fixture route remains operator-protected by the actual middleware.
        rejected('/api/fixture/restart-drift', {}, 403, api_headers)
        api('/api/fixture/restart-drift', {})
        request_id = uuid.uuid4().hex
        restart_body = {'input_text': NEW_SOURCE, 'request_id': request_id}
        restart_path = f'/api/sessions/{parent["id"]}/correct-and-restart'
        prepared = api(restart_path, restart_body)
        child_id = prepared['id']
        status_path = f'/api/sessions/{child_id}/restart-status'
        assert prepared['state'] == 'prepared' and prepared['dispatch_eligible'] is False
        assert prepared['preparation_contexts']['reviewer']['state'] == 'ready'
        assert prepared['preparation_contexts']['editor']['reason'] == 'confirmation_required'
        assert prepared['preparation_contexts']['reviewer']['identity_id'] == instances[names['api']]['identity_id']
        assert api(restart_path, restart_body)['id'] == child_id
        assert len(list(records.glob('client-*.json'))) == 1 and len(captures) == 2
        assert len(client()['prompts']) == 1, 'stopped old context received additional work'
        # Retain an actual handle to this test's recorded native child before
        # requesting its confirmed manager-owned replacement (no PID scan/kill).
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        old_handle = kernel.OpenProcess(0x00100000, False, old['pid'])
        assert old_handle and kernel.WaitForSingleObject(old_handle, 0) == 258
        context_request_id = uuid.uuid4().hex
        context_body = {'context_request_id': context_request_id,
            'confirmations': {'editor': {'launch_attempt': ready['seats']['cli']['attempt'], 'confirm': True}}}
        context_path = f'/api/sessions/{child_id}/prepare-contexts'
        rejected(context_path, context_body, 503)
        fault = json.loads((records / 'backlink-fault.json').read_text('utf-8'))
        assert fault['child_id'] == child_id
        assert not saved(child_id).get('preparation_contexts'), 'fixture did not interrupt backlink before commit'
        nonce = fault['context_id']
        boot = wait_for(lambda: value if 'first_reads' in (value := client(nonce)) else None, 'fresh first MCP reads before backlink')
        assert all(value == [] for value in boot['first_reads'].values())
        assert kernel.WaitForSingleObject(old_handle, 0) == 0, 'old recorded client has not actually exited'
        assert boot['pid'] != old['pid'] and boot['context_id']
        assert boot['model'] == 'cli-original' and boot['reasoning'] == 'high'
        assert Path(boot['cwd']) == original_cwd
        assert '--fixture-original' in boot['argv'] and '--edited-resume' not in boot['argv']
        assert boot['settings_path'] != old['settings_path']
        api(context_path, context_body)
        def contexts_ready():
            value = api(status_path)
            contexts = value['preparation_contexts']
            return value if len(contexts) == 2 and all(c['state'] == 'ready' and c['clean_context'] for c in contexts.values()) else None
        contexts = wait_for(contexts_ready, 'both fresh contexts ready')
        assert len(list(records.glob('client-*.json'))) == 2
        assert len(list((data / 'api_seat_runtime').glob('*/config.json'))) == 4
        assert contexts['preparation_contexts']['editor']['launch_attempt'] == fault['launch_attempt']
        assert contexts['preparation_contexts']['editor']['identity_id'] != instances[names['cli']]['identity_id']
        assert contexts['preparation_contexts']['reviewer']['launch_attempt'] == ready['seats']['api']['attempt']
        assert api(context_path, context_body)['id'] == child_id
        assert api(restart_path, restart_body)['id'] == child_id
        assert len(list(records.glob('client-*.json'))) == 2 and len(captures) == 2
        assert contexts['parent_run_id'] == parent['run_id'] and contexts['lineage_root_id'] == parent['run_id']
        assert contexts['input_snapshot']['text'] == NEW_SOURCE
        assert contexts['input_revision'] == hashlib.sha256(NEW_SOURCE.encode('utf-8')).hexdigest()
        assert contexts['input_revision'] != parent['input_revision']
        assert contexts['design_snapshot'] == old_parent['design_snapshot'] and contexts['rules_snapshot'] == old_parent['rules_snapshot']
        assert contexts['goal'] == GOAL and contexts['admitted_events'] == []
        if '--serve' in sys.argv:
            browser_url = base + '/?channel=restart-run'
            url_marker.write_text(browser_url, encoding='utf-8')
            print(json.dumps({'stage': 'restart_browser_qa_ready', 'url': browser_url, 'channel': 'restart-run',
                'parent_session_id': parent['id'], 'child_session_id': child_id, 'stop_sentinel': str(stop_marker),
                'scratch': str(temporary)}), flush=True)
            while child.poll() is None and not stop_marker.exists():
                time.sleep(.5)
        activate_path = f'/api/sessions/{child_id}/activate-restart'
        api(activate_path, {})  # Idempotent if browser already activated.
        api(activate_path, {})
        new = wait_for(lambda: value if 'envelope' in (value := client(nonce)) and 'turn_reads' in value else None,
                       'new exact scoped CLI brief')
        envelope = new['envelope']
        assert envelope['source'] == NEW_SOURCE and envelope['run_id'] == contexts['run_id']
        assert envelope['input_revision'] == contexts['input_revision']
        assert envelope['rules']['rules'] == [RULE]
        assert [value['text'] for value in envelope['prior_results']] == ['NEW_API_RESULT corrected source finding.']
        assert envelope.get('continuation_context', []) == []
        new_payloads = [record for record in captures if 'NEW_SOURCE' in json.dumps(record['payload'], ensure_ascii=False)]
        assert len(new_payloads) == 1, 'activation or request retry regenerated the API review'
        payload = new_payloads[0]['payload']
        assert payload['model'] == 'api-original' and payload['reasoning_effort'] == 'high'
        assert new_payloads[0]['path'] == '/v1/chat/completions'
        assert 'FROZEN_API_SYSTEM' in payload['messages'][0]['content']
        clean_serialized = json.dumps({'payload': payload, 'brief': envelope, 'reads': new['turn_reads']}, ensure_ascii=False)
        for forbidden in ('OLD_SOURCE', 'OLD_RESULT', 'OLD_CONTINUATION', 'OLD_SUMMARY', 'OLD_JOB', 'EDITED_SYSTEM_MUST_NOT_ENTER', 'supplementary_chat'):
            assert forbidden not in clean_serialized, 'old/live context leaked: ' + forbidden
        assert all('NEW_API_RESULT' in json.dumps(value) for value in new['turn_reads'].values())
        assert envelope['brief_id'] != old['envelope']['brief_id'] and envelope['attempt_id'] != old['envelope']['attempt_id']
        (records / 'submit-new').touch()
        completed = wait_for(lambda: value if (value := saved(child_id))['state'] == 'complete' else None, 'corrected typed final')
        assert [event['content'] for event in completed['admitted_events']] == [
            'NEW_API_RESULT corrected source finding.', 'NEW_CLI_RESULT corrected café evidence.']
        (records / 'release-new').touch()
        queue = QueueStore(data)
        new_identity = next(value for value in json.loads((data / 'registry.json').read_text('utf-8'))['instances'].values()
                            if value['identity_id'] == completed['participant_bindings']['editor']['identity_id'])
        wait_for(lambda: queue.owned(new_identity, new['dispatch_id'])['state'] == 'released', 'separate new CLI release')
        rejected(f'/api/sessions/{parent["id"]}/event', {'brief_id': old_final['brief_id'], 'kind': 'final',
            'content': old_final['content'], 'event_id': old_final['event_id']}, 409, api_headers)
        parent_after = saved(parent['id'])
        for field in ('input_snapshot', 'admitted_events', 'result_message_ids', 'continuation_context', 'quarantined_events'):
            assert parent_after[field] == old_parent[field], 'old audit history was altered: ' + field
        assert parent_after['dispatch_eligible'] is False and parent_after['replaced_by_run_id'] == contexts['run_id']
        assert api(restart_path, restart_body)['id'] == child_id
        assert api(activate_path, {})['state'] == 'complete'
        assert len(list(records.glob('client-*.json'))) == 2
        peer = api('/api/sessions/start', {'template_id': 'peer-fixture', 'channel': 'peer-run',
            'cast': {'reviewer': names['peer']}, 'input_text': 'Independent peer source'})
        wait_for(lambda: saved(peer['id'])['state'] == 'complete', 'unrelated peer review')
        assert len(json.loads((data / 'session_runs.json').read_text('utf-8'))) == 3
        assert len(captures) == 4 and len(old_calls) == 2, 'idempotent restart/activation made extra provider calls'
        assert len([value for value in captures if 'NEW_SOURCE' in json.dumps(value['payload'], ensure_ascii=False)]) == 1
        assert len(list((data / 'api_seat_runtime').glob('*/config.json'))) == 4
        print(json.dumps({'result': 'PASS', 'parent_session_id': parent['id'], 'child_session_id': child_id,
            'fresh_pid_and_identity': True, 'old_client_exit_observed': True, 'first_boot_reads_empty': True,
            'backlink_failure_http': 503, 'same_request_repaired_without_duplicate_launch': True,
            'frozen_original_settings': True, 'new_source_only': True, 'old_audit_history_retained': True,
            'new_admitted_results': 2, 'peer_complete': True, 'scratch': str(temporary)}), flush=True)
    finally:
        if old_handle:
            ctypes.WinDLL('kernel32').CloseHandle(ctypes.c_void_p(old_handle))
        if api is not None and child is not None and child.poll() is None:
            try:
                # This dedicated isolated manager owns every listed attempt,
                # including fresh contexts whose backlink save was interrupted.
                runtime = api('/api/preflight/seats')['runtime']
                for key in runtime:
                    try:
                        api('/api/preflight/seats/' + key + '/stop', {})
                    except OSError:
                        pass
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
