"""AT-21b real isolated API/CLI queue delivery and explicit MCP release check."""
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
from dispatch_queue import QueueBusy, QueueStore
from launcher import stop_owned_child


def main():
    if sys.platform != 'win32':
        print(json.dumps({'result': 'SKIP', 'reason': 'Actual console injection requires Windows.'}))
        return
    captures = []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            captures.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"model":"fake-confirmed","choices":[{"message":{"content":"Local fake reply."}}]}')

        def log_message(self, *args):
            pass

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    threading.Thread(target=provider.serve_forever, daemon=True).start()
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='dispatch integration ', dir=scratch))
    data = temporary / 'data'
    data.mkdir()
    records = temporary / 'records'
    records.mkdir()
    legacy = data / 'legacy_queue.jsonl'
    original_legacy = b'{"prompt":"uncertain legacy work"}\r\nmalformed\r\n'
    legacy.write_bytes(original_legacy)
    sockets = [socket.socket() for _ in range(3)]
    for handle in sockets:
        handle.bind(('127.0.0.1', 0))
    ports = [handle.getsockname()[1] for handle in sockets]
    for handle in sockets:
        handle.close()
    base = f'http://127.0.0.1:{ports[0]}'
    environment = os.environ.copy()
    environment.update(dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT',
                                 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports))))
    environment.update(AGENTCHATTR_DATA_DIR=str(data), AGENTCHATTR_UPLOAD_DIR=str(temporary / 'uploads'),
                       TICKET7_RECORDS=str(records))
    fixture = str((ROOT / 'tools/fake_dispatch_cli.py').resolve())
    code = f'''import config_loader
load=config_loader.load_config
def isolated(root=None):
    cfg=load(root)
    cfg['agents']={{'fake-api':{{'type':'api','base_url':'http://127.0.0.1:{provider.server_port}/v1'}},
        'fake-cli':{{'command':{sys.executable!r},'cwd':'.','cli_args':[{fixture!r}],
        'mcp_inject':'env','mcp_env_var':'TICKET7_FAKE_SETTINGS'}}}}
    return cfg
config_loader.load_config=isolated
import run
run.main()
'''
    child = None
    api = None
    url_marker = scratch / 'ticket7-browser-url.txt'
    stop_marker = scratch / 'ticket7-browser-stop.txt'
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
                    result = check()
                    if result:
                        return result
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

        seat = {'id': 'api', 'name': 'Fake API', 'adapter': 'openai-compatible', 'provider': 'fake-api',
                'model': 'fake-api-model', 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        api('/api/preflight/packages', {'id': 'queue-team', 'name': 'Queue team', 'seats': [seat,
            {**seat, 'id': 'cli', 'name': 'Fake CLI', 'adapter': 'cli', 'provider': 'fake-cli', 'model': None}]})
        revision = api('/api/preflight/seats')['package_revisions']['queue-team']
        api('/api/preflight/packages/queue-team/launch', {'revision': revision})
        ready = wait_for(lambda: state if (state := api('/api/preflight/packages/queue-team/status'))['ready'] else None,
                         'managed mixed seats ready')
        assert not captures
        names = {seat_id: ready['seats'][seat_id]['name'] for seat_id in ('api', 'cli')}
        registered = json.loads((data / 'registry.json').read_text('utf-8'))['instances']
        instances = {seat_id: registered[names[seat_id]] for seat_id in names}
        queue = QueueStore(data)
        cli_entries = [dict(dispatch_id=uuid.uuid4().hex, channel='alpha', prompt='CLI-FIRST exact instruction', job_id=11),
                       dict(dispatch_id=uuid.uuid4().hex, channel='beta', prompt='CLI-SECOND separate instruction', job_id=22)]
        for entry in cli_entries:
            queue.enqueue(instances['cli'], entry)
        queue.enqueue(instances['cli'], dict(cli_entries[0]))

        def cli_record():
            result = json.loads((records / 'cli-record.json').read_text('utf-8'))
            if result.get('error'):
                raise AssertionError('fake CLI failed: ' + result['error'])
            return result

        first = wait_for(lambda: r if len((r := cli_record())['prompts']) >= 1 else None, 'first CLI injection')
        assert 'CLI-FIRST exact instruction' in first['prompts'][0]
        assert 'CLI-SECOND' not in first['prompts'][0]
        assert 'alpha' in first['prompts'][0] and '11' in first['prompts'][0]
        settings = json.loads(Path(first['settings_path']).read_text('utf-8'))
        cli_headers = {**settings['mcpServers']['agentchattr']['headers'], 'Content-Type': 'application/json'}
        try:
            api('/api/queue/claim', {'consumer_id': 'replacement-wrapper'}, cli_headers)
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        else:
            raise AssertionError('replacement consumer acquired an already owned seat')
        time.sleep(2.5)
        assert len(cli_record()['prompts']) == 1, 'a second CLI dispatch was injected before explicit release'
        visible = api('/api/queue/status')['seats'][instances['cli']['identity_id']]
        assert visible['queued'] == 1 and visible['contention']
        assert visible['active']['dispatch_id'] == cli_entries[0]['dispatch_id']
        assert visible['active']['awaiting_release']
        (records / 'release-first').touch()
        delivered = wait_for(lambda: r if len((r := cli_record())['released']) == 2 else None, 'both MCP releases')
        assert len(delivered['prompts']) == 2, 'duplicate enqueue injected another turn'
        assert 'CLI-SECOND separate instruction' in delivered['prompts'][1]
        assert 'CLI-FIRST' not in delivered['prompts'][1]
        assert 'beta' in delivered['prompts'][1] and '22' in delivered['prompts'][1]
        assert [item['dispatch_id'] for item in delivered['released']] == [item['dispatch_id'] for item in cli_entries]

        api_entries = [dict(dispatch_id=uuid.uuid4().hex, channel='general', prompt='API-FIRST only instruction'),
                       dict(dispatch_id=uuid.uuid4().hex, channel='general', prompt='API-SECOND own instruction')]
        for entry in api_entries:
            queue.enqueue(instances['api'], entry)
        wait_for(lambda: len(captures) == 2, 'two distinct same-channel API calls')
        for i, (payload, own, other) in enumerate(zip(captures, api_entries, reversed(api_entries))):
            assert payload['model'] == 'fake-api-model'
            system = '\n'.join(message['content'] for message in payload['messages'] if message['role'] == 'system')
            assert own['prompt'] in system, f'API call {i} lost its own instruction'
            assert other['prompt'] not in system, f'API call {i} mixed another dispatch instruction'

        def all_released():
            ledger = json.loads((data / 'queue/ledger.json').read_text('utf-8'))
            return ledger if len(ledger['records']) == 4 and all(r['state'] == 'released' for r in ledger['records']) else None

        ledger = wait_for(all_released, 'four durable release receipts')
        assert {r['envelope']['dispatch_id'] for r in ledger['records']} == {
            entry['dispatch_id'] for entry in cli_entries + api_entries}
        for record in ledger['records']:
            states = [event['state'] for event in record['events']]
            assert 'dispatched' in states and 'acknowledged' in states and states[-1] == 'released'
        assert legacy.read_bytes() == original_legacy
        assert legacy.name in json.dumps(api('/api/queue/status'))
        assert api('/api/sessions/active-all') == [], 'transport release created a session'

        failure_entries = [dict(dispatch_id=uuid.uuid4().hex, channel='gamma',
                                prompt='CLI-HOLD-UNTIL-FAILURE retain this owned work', job_id=33),
                           dict(dispatch_id=uuid.uuid4().hex, channel='delta',
                                prompt='CLI-PENDING-AFTER-FAILURE must remain queued', job_id=44)]
        for entry in failure_entries:
            queue.enqueue(instances['cli'], entry)
        held = wait_for(lambda: r if len((r := cli_record())['prompts']) == 3 else None,
                        'failure scenario first real CLI injection')
        assert 'CLI-HOLD-UNTIL-FAILURE' in held['prompts'][2]
        assert len(held['released']) == 2

        def retained_records():
            value = json.loads((data / 'queue/ledger.json').read_text('utf-8'))
            return {record['envelope']['dispatch_id']: record for record in value['records']}

        wait_for(lambda: retained_records()[failure_entries[0]['dispatch_id']]['state'] == 'acknowledged',
                 'held dispatch acknowledgement')
        if '--serve' in sys.argv:
            url_marker.write_text(base + '/preflight', encoding='utf-8')
            print(json.dumps({'stage': 'browser_qa_ready', 'url': base + '/preflight',
                              'release_withheld': True, 'stop_sentinel': str(stop_marker)}), flush=True)
            while child.poll() is None and not stop_marker.exists():
                time.sleep(.5)

        # Stop only this test's manager-owned runtime. No PID discovery or
        # unrelated cleanup, and no dispatch release sent by the fixture.
        stopped = api('/api/preflight/seats/queue-team/cli/stop', {})
        assert stopped['state'] == 'stopped'
        stopped_receipt = data / 'api_seat_runtime' / ready['seats']['cli']['attempt'] / 'receipt.json'
        wait_for(lambda: json.loads(stopped_receipt.read_text('utf-8'))['state'] == 'stopped',
                 'actual owned CLI worker stop acknowledgement')
        retained = retained_records()
        first_retained = retained[failure_entries[0]['dispatch_id']]
        self_held_states = ('dispatched', 'acknowledged', 'uncertain')
        assert first_retained['state'] in self_held_states, 'worker exit released uncertain active work'
        assert retained[failure_entries[1]['dispatch_id']]['state'] == 'queued'
        for entry in failure_entries:
            for field, value in entry.items():
                assert retained[entry['dispatch_id']]['envelope'][field] == value
        try:
            QueueStore(data).claim(instances['cli'], 'fresh-consumer-after-worker-failure')
        except QueueBusy:
            pass
        else:
            raise AssertionError('fresh consumer replayed retained work after worker failure')
        visible = api('/api/queue/status')['seats'][instances['cli']['identity_id']]
        assert visible['queued'] == 1 and visible['contention']
        assert visible['active']['dispatch_id'] == failure_entries[0]['dispatch_id']
        assert visible['active']['awaiting_release']
        assert len(cli_record()['prompts']) == 3, 'pending turn was injected before worker exit'
        assert len(cli_record()['released']) == 2
        assert api('/api/preflight/seats')['runtime']['queue-team/api']['state'] == 'ready'
        assert len(captures) == 2 and legacy.read_bytes() == original_legacy
        print(json.dumps({'result': 'PASS', 'successful_cli_injections': len(delivered['prompts']),
                          'cli_mcp_releases': len(delivered['released']), 'api_calls': len(captures),
                          'release_withheld_blocks_next': True, 'replacement_consumer_http': 409,
                          'same_id_deduplicated': True, 'legacy_bytes_preserved': True,
                          'owned_worker_stopped': True, 'retained_active_state': first_retained['state'],
                          'retained_queued': 1, 'fresh_consumer_blocked_after_failure': True,
                          'scratch': str(temporary)}), flush=True)
    finally:
        if api is not None and child is not None and child.poll() is None:
            for seat_id in ('api', 'cli'):
                try:
                    api('/api/preflight/seats/queue-team/' + seat_id + '/stop', {})
                except OSError:
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
