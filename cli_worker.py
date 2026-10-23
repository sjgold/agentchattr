"""App-owned interactive CLI wrapper using existing platform injection runners."""
from contextlib import ExitStack
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.request

from api_seats import Receipt, SeatError, validate_seat
from cli_seats import build_cli_args, config_resource, probe_version
from launcher import LaunchError, startup_lock
from wrapper import (_auth_headers, _build_provider_launch, _get_server_url, _queue_watcher,
                     _register_instance, _resolve_mcp_inject, ROOT)


def run(snapshot_path):
    snapshot_path = Path(snapshot_path)
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    seat, client = snapshot['seat'], snapshot['provider']
    validate_seat(seat, {seat['provider']: client})
    from runtime_ownership import record_worker_birth, heartbeat_payload
    birth = record_worker_birth(snapshot_path, snapshot)
    observed_boot = [None]
    receipt = Receipt(snapshot_path.with_name('receipt.json'), snapshot['attempt'])
    receipt.update(startup_checked=False, version=None, child_exit_code=None)
    stop = threading.Event()
    stop_reason = {'requested': False}
    connected = threading.Event()
    identity = {'name': None, 'token': None}
    base, server = snapshot['base'], snapshot['server']
    port = server.get('port', 8300)
    data = Path(server['data_dir'])
    proxy = None
    outcome = 1

    def request(path):
        body = {'runtime_ownership': heartbeat_payload(birth, observed_boot[0])} if path.startswith('/api/heartbeat/') else {}
        req = urllib.request.Request(f'http://127.0.0.1:{port}' + path, data=json.dumps(body).encode(), method='POST',
                                     headers=_auth_headers(identity['token'], include_json=True))
        with urllib.request.urlopen(req, timeout=2) as response:
            return json.loads(response.read())

    def heartbeat():
        last_success = time.monotonic()
        while not stop.wait(0.5):
            try:
                control = json.loads(snapshot_path.with_name('stop.json').read_text(encoding='utf-8'))
                if control.get('attempt') == snapshot['attempt']:
                    stop_reason['requested'] = True
                    stop.set()
                    break
            except (OSError, ValueError, AttributeError):
                pass
            try:
                response = request('/api/heartbeat/' + identity['name'])
                proof = response.get('runtime_ownership', {})
                observed_boot[0] = proof.get('boot_id')
                identity['name'] = response.get('name', identity['name'])
                last_success = time.monotonic()
                if not stop.is_set():
                    receipt.update(state='ready' if connected.is_set() else 'starting', name=identity['name'],
                                   adapter_connected=connected.is_set())
            except (OSError, ValueError):
                if time.monotonic() - last_success > 15:
                    receipt.update(state='failed', adapter_connected=False,
                                   error='Local server heartbeat deadline reached. Retry this seat.')
                    stop.set()

    def start_watcher(inject):
        # Platform runner calls this only after its owned child/session exists.
        connected.set()
        receipt.update(startup_checked=True, state='ready', adapter_connected=True, name=identity['name'])
        def get_identity():
            name = identity['name']
            return name, data / (name + '_queue.jsonl')
        threading.Thread(target=_queue_watcher, args=(get_identity, inject),
                         kwargs={'is_multi_instance': True, 'server_port': port, 'agent_name': base,
                                 'get_token_fn': lambda: identity['token'], 'stop_event': stop},
                         daemon=True).start()

    try:
        with ExitStack() as stack:
            resource = config_resource(client, client['cwd'])
            if resource:
                target = Path(resource)
                # Shared across server/data directories and checkouts for this path.
                stack.enter_context(startup_lock(target.with_name(target.name + '.agentchattr.lock'),
                                                time.monotonic() + 0.2))
            mode = _resolve_mcp_inject('', client)
            if not mode:
                raise SeatError('This client has no declared MCP identity injection contract. Configure a supported adapter before launch.')
            identity.update(_register_instance(port, base, seat['name']))
            receipt.update(identity_id=identity.get('identity_id'))
            if not identity.get('name') or not identity.get('token'):
                raise SeatError('The local server did not supply a CLI identity.')
            proxy_url = None
            if mode.get('mcp_inject') == 'proxy_flag':
                from mcp_proxy import McpIdentityProxy
                transport = mode.get('mcp_transport', 'http')
                url = _get_server_url(snapshot.get('mcp', {}), transport)
                from urllib.parse import urlsplit
                parsed = urlsplit(url)
                proxy = McpIdentityProxy(upstream_base=f'{parsed.scheme}://{parsed.netloc}',
                                         upstream_path=parsed.path, agent_name=identity['name'],
                                         instance_token=identity['token'])
                if proxy.start() is False:
                    raise SeatError('The owned MCP identity proxy could not start.')
                proxy_url = proxy.url + parsed.path
            strip = {'CLAUDECODE'} | set(client.get('strip_env', []))
            environment = {k: v for k, v in os.environ.items() if k not in strip}
            arguments, environment, inject_env, _ = _build_provider_launch(
                seat['provider'], client, identity['name'], data, proxy_url,
                build_cli_args(seat, client), environment, token=identity['token'],
                mcp_cfg=snapshot.get('mcp', {}), project_dir=Path(client['cwd']))
            version = probe_version(client['command'], client.get('cli_version_args'))
            receipt.update(name=identity['name'], version=version)
            threading.Thread(target=heartbeat, daemon=True).start()
            kwargs = dict(command=client['command'], extra_args=arguments, cwd=client['cwd'],
                          env=environment, queue_file=data / (identity['name'] + '_queue.jsonl'),
                          agent=seat['provider'], no_restart=True, start_watcher=start_watcher,
                          strip_env=list(strip), inject_env=inject_env, stop_event=stop,
                          inject_delay=client.get('inject_delay', 0.3))
            if sys.platform == 'win32':
                from wrapper_windows import run_agent
                kwargs['enter_backend'] = client.get('enter_backend', 'console_input')
            else:
                from wrapper_unix import run_agent
                kwargs.update(session_name='agentchattr-' + base, managed=True)
            outcome = run_agent(**kwargs)
            requested_stop = stop_reason['requested']
            stop.set()
            receipt.update(state='stopped' if requested_stop or outcome == 0 else 'failed',
                           adapter_connected=False, child_exit_code=outcome,
                           error=None if requested_stop or outcome == 0 else f'CLI exited with code {outcome}. Retry this seat.')
    except (ValueError, OSError, SeatError, LaunchError):
        receipt.update(state='action_required', adapter_connected=False,
                       error='CLI launch could not complete. Check executable, client settings, shared-file ownership and local server, then retry.')
    finally:
        stop.set()
        if identity.get('token'):
            try:
                request('/api/deregister/' + identity['name'])
            except (OSError, ValueError):
                pass
        if proxy is not None:
            proxy.stop()
    return outcome


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base')
    parser.add_argument('--seat-file', required=True)
    args = parser.parse_args()
    sys.exit(run(args.seat_file))
