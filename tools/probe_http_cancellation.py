"""Measure actual blocked-worker exit on Windows, never equating close with exit.

Each network case runs in an owned subprocess with a hard deadline. Its local
server releases delayed responses after the cancellation observation window so
an unsuccessful interruption cannot leave the probe waiting indefinitely.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import ssl
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CANCEL_BUDGET = .75
CASES = ('urllib_body_response_close', 'http_headers_socket_close',
         'http_headers_shutdown_close', 'http_body_socket_close',
         'http_body_shutdown_close', 'cancel_before_connection_assignment',
         'completed_response_cancel_race', 'http_headers_blocking_shutdown_close',
         'http_body_blocking_shutdown_close', 'dns_stall_pre_socket', 'connect_stall_pre_socket',
         'urllib_https_body_response_close', 'https_headers_socket_close',
         'https_headers_shutdown_close', 'https_body_socket_close', 'https_body_shutdown_close',
         'https_headers_blocking_shutdown_close', 'https_body_blocking_shutdown_close')


def network_case(name, cert=None, key=None, observation=CANCEL_BUDGET, minimum_hold=0, request_timeout=5):
    release_server = threading.Event()
    server_waiting = threading.Event()
    worker_phase = threading.Event()
    worker_done = threading.Event()
    closer_done = threading.Event()
    cancelled = threading.Event()
    assignment_allowed = threading.Event()
    publication_allowed = threading.Event()
    network_completed = threading.Event()
    handles = {}
    outcomes = {}
    lock = threading.Lock()
    requests = []
    delay_started = []
    payload = b'owned-loopback-response-payload'
    stage = 'headers' if 'headers' in name else 'body'
    tls = 'https' in name
    pre_socket_stall = name in ('dns_stall_pre_socket', 'connect_stall_pre_socket')
    immediate = pre_socket_stall or name in ('cancel_before_connection_assignment', 'completed_response_cancel_race')

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def do_GET(self):
            requests.append(self.path)
            try:
                if stage == 'headers' and not immediate:
                    delay_started.append(time.monotonic())
                    server_waiting.set()
                    release_server.wait(max(request_timeout + 2, minimum_hold + 2))
                self.send_response(200)
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                if immediate:
                    self.wfile.write(payload)
                else:
                    self.wfile.write(payload[:1])
                    self.wfile.flush()
                    if stage == 'body':
                        delay_started.append(time.monotonic())
                        server_waiting.set()
                        release_server.wait(max(request_timeout + 2, minimum_hold + 2))
                    self.wfile.write(payload[1:])
                self.wfile.flush()
            except OSError:
                pass

        def log_message(self, *args):
            pass

        def log_error(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    def worker():
        response = None
        connection = None
        try:
            if name.startswith('urllib_'):
                handlers = [urllib.request.ProxyHandler({})]
                if tls:
                    handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
                opener = urllib.request.build_opener(*handlers)
                scheme = 'https' if tls else 'http'
                response = opener.open(f'{scheme}://127.0.0.1:{server.server_port}/probe', timeout=request_timeout)
                with lock:
                    handles['response'] = response
                worker_phase.set()
                body = response.read()
            else:
                connection = (http.client.HTTPSConnection('127.0.0.1', server.server_port, timeout=request_timeout,
                              context=ssl._create_unverified_context()) if tls else
                              http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=request_timeout))
                if name == 'cancel_before_connection_assignment':
                    worker_phase.set()
                    if not assignment_allowed.wait(3):
                        raise TimeoutError('assignment fixture gate')
                with lock:
                    # Explicit publication and cancellation check under the same
                    # lock, before connect. Closing None alone cannot do this.
                    handles['connection'] = connection
                    if cancelled.is_set():
                        outcomes.update(io_status='cancelled_before_connect', published=False)
                        return
                def stall():
                    worker_phase.set()
                    server_waiting.set()
                    if not release_server.wait(5):
                        raise TimeoutError('controlled pre-socket stall')
                if name == 'dns_stall_pre_socket':
                    resolve = socket.getaddrinfo
                    def delayed_dns(*args, **kwargs):
                        stall()
                        return resolve(*args, **kwargs)
                    with patch('socket.getaddrinfo', delayed_dns):
                        connection.connect()
                elif name == 'connect_stall_pre_socket':
                    connect = connection._create_connection
                    def delayed_connect(*args, **kwargs):
                        stall()
                        return connect(*args, **kwargs)
                    connection._create_connection = delayed_connect
                    connection.connect()
                else:
                    connection.connect()
                with lock:
                    handles['socket'] = connection.sock
                    if tls:
                        outcomes['tls_version'] = connection.sock.version()
                    if cancelled.is_set():
                        outcomes.update(io_status='cancelled_after_connect_before_request', published=False)
                        return
                if 'blocking' in name:
                    connection.sock.settimeout(None)
                connection.request('GET', '/probe')
                if stage == 'headers':
                    worker_phase.set()
                response = connection.getresponse()
                with lock:
                    handles['response'] = response
                if stage == 'body':
                    worker_phase.set()
                body = response.read()
            outcomes.update(io_status='success', response_bytes=len(body), exact_body=body == payload)
            if name == 'completed_response_cancel_race':
                network_completed.set()
                if not publication_allowed.wait(3):
                    raise TimeoutError('publication fixture gate')
            # Demonstrate the output fence separately from network interruption.
            outcomes['published'] = not cancelled.is_set()
        except Exception as exc:
            outcomes.update(io_status='error', exception=type(exc).__name__,
                            exception_detail=str(exc), published=False)
        finally:
            outcomes['io_finished_at'] = time.monotonic()
            outcomes['cancel_flag_at_finish'] = cancelled.is_set()
            try:
                if response is not None:
                    response.close()
                if connection is not None:
                    connection.close()
            except Exception as exc:
                outcomes['worker_cleanup_exception'] = type(exc).__name__
            finally:
                outcomes['worker_finished_at'] = time.monotonic()
                worker_done.set()

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    cleanup_release_at = None
    try:
        if name == 'completed_response_cancel_race':
            if not network_completed.wait(3):
                raise AssertionError('worker did not complete response before race gate')
        elif name == 'cancel_before_connection_assignment':
            if not worker_phase.wait(3):
                raise AssertionError('worker did not reach pre-assignment gate')
        else:
            if not server_waiting.wait(3) or not worker_phase.wait(3):
                raise AssertionError('worker/server did not reach intended blocked stage')
            time.sleep(.05)

        cancel_started = time.monotonic()
        cancelled.set()

        def close_owned_handle():
            try:
                with lock:
                    response = handles.get('response')
                    owned_socket = handles.get('socket')
                outcomes['socket_present_when_cancelled'] = owned_socket is not None
                if name.startswith('urllib_'):
                    response.close()
                elif name == 'cancel_before_connection_assignment':
                    outcomes['handle_present_when_cancelled'] = bool(handles)
                    assignment_allowed.set()
                elif name == 'completed_response_cancel_race':
                    publication_allowed.set()
                elif pre_socket_stall:
                    handles['connection'].close()
                elif name.endswith('shutdown_close'):
                    try:
                        owned_socket.shutdown(socket.SHUT_RDWR)
                    finally:
                        owned_socket.close()
                else:
                    owned_socket.close()
                outcomes['close_status'] = 'returned'
            except Exception as exc:
                outcomes['close_status'] = type(exc).__name__
            finally:
                outcomes['close_finished_at'] = time.monotonic()
                closer_done.set()

        closer = threading.Thread(target=close_owned_handle, daemon=True)
        closer.start()
        worker_thread.join(max(0, cancel_started + observation - time.monotonic()))
        worker_exited = not worker_thread.is_alive()
        close_returned = closer_done.is_set()
        observed_at = time.monotonic()
        # Only now unblock the server for bounded cleanup. Success after this
        # point is not credited as cancellation within the observation window.
        if delay_started and minimum_hold:
            threading.Event().wait(max(0, delay_started[0] + minimum_hold - time.monotonic()))
        cleanup_release_at = time.monotonic()
        release_server.set()
        assignment_allowed.set()
        publication_allowed.set()
        worker_thread.join(2)
        closer.join(2)
        result = {'case': name, 'observation_budget_ms': observation * 1000,
                  'tls': tls, 'socket_mode': 'blocking' if 'blocking' in name else f'timeout_{request_timeout}s',
                  'server_progress_withheld_ms': round((cleanup_release_at - delay_started[0]) * 1000, 3) if delay_started else None,
                  'worker_exited_before_cleanup': worker_exited,
                  'close_returned_at_observation': close_returned,
                  'observation_elapsed_ms': round((observed_at - cancel_started) * 1000, 3),
                  'worker_exit_after_cancel_ms': round((outcomes['worker_finished_at'] - cancel_started) * 1000, 3)
                      if 'worker_finished_at' in outcomes else None,
                  'close_return_after_cancel_ms': round((outcomes['close_finished_at'] - cancel_started) * 1000, 3)
                      if 'close_finished_at' in outcomes else None,
                  'cleanup_server_release_after_cancel_ms': round((cleanup_release_at - cancel_started) * 1000, 3),
                  'worker_thread_alive_after_cleanup': worker_thread.is_alive(),
                  'closer_thread_alive_after_cleanup': closer.is_alive(),
                  'server_requests': len(requests),
                  **{key: value for key, value in outcomes.items() if not key.endswith('_at')}}
        if not worker_exited:
            result['cancellation_verdict'] = 'unresolved_worker_blocked_until_cleanup'
        elif name in ('cancel_before_connection_assignment', 'completed_response_cancel_race'):
            result['cancellation_verdict'] = 'cooperative_guard_prevents_publication'
        else:
            result['cancellation_verdict'] = 'local_worker_exited_before_cleanup'
        return result
    finally:
        release_server.set()
        assignment_allowed.set()
        publication_allowed.set()
        shutdown_thread = threading.Thread(target=server.shutdown, daemon=True)
        shutdown_thread.start()
        shutdown_thread.join(1)
        server.server_close()


def ipc_probe():
    values = []
    payload = b'x' * (512 * 1024)
    code = 'import sys; data=sys.stdin.buffer.read(); sys.stdout.buffer.write(data); sys.stdout.buffer.flush()'
    for _ in range(3):
        started = time.monotonic()
        child = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        spawned = time.monotonic()
        try:
            stdout, stderr = child.communicate(input=payload, timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate(timeout=2)
            values.append({'timeout': True})
            continue
        values.append({'popen_return_ms': round((spawned - started) * 1000, 3),
                       'roundtrip_ms': round((time.monotonic() - started) * 1000, 3),
                       'input_bytes': len(payload), 'output_bytes': len(stdout),
                       'exact_echo': stdout == payload, 'exit_code': child.returncode,
                       'stderr_bytes': len(stderr)})
    return {'method': 'owned subprocess communicate, full 512KiB input and output', 'runs': values,
            'median_popen_return_ms': statistics.median(v['popen_return_ms'] for v in values if 'popen_return_ms' in v)
                if any('popen_return_ms' in v for v in values) else None}


def owned_child_network_probe():
    """Terminate only a child blocked in real HTTP; verify parent/server survive."""
    blocked = threading.Event()
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            if self.path == '/health':
                self.end_headers()
                self.wfile.write(b'owned-server-alive')
                return
            self.send_header('Content-Length', '32')
            self.end_headers()
            self.wfile.write(b'x')
            self.wfile.flush()
            blocked.set()
            release.wait(8)
            try:
                self.wfile.write(b'x' * 31)
            except OSError:
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    code = ('import urllib.request,sys; '
            'opener=urllib.request.build_opener(urllib.request.ProxyHandler({})); '
            'response=opener.open(sys.argv[1],timeout=20); '
            'sys.stdout.buffer.write(response.read())')
    child = subprocess.Popen([sys.executable, '-c', code, f'http://127.0.0.1:{server.server_port}/slow'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        if not blocked.wait(4):
            raise AssertionError('owned child did not reach actual delayed body read')
        time.sleep(.05)
        alive_before = child.poll() is None
        started = time.monotonic()
        child.terminate()
        try:
            stdout, stderr = child.communicate(timeout=3)
            exited = True
        except subprocess.TimeoutExpired:
            exited = False
            child.kill()
            stdout, stderr = child.communicate(timeout=2)
        elapsed = (time.monotonic() - started) * 1000
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/health', timeout=2) as response:
            server_ok = response.read() == b'owned-server-alive'
        return {'method': 'owned child blocked in urllib body read; terminate then communicate',
                'child_alive_before_cancel': alive_before, 'child_exited_within_3s': exited,
                'actual_exit_code': child.returncode, 'terminate_to_exit_ms': round(elapsed, 3),
                'server_progress_released_before_child_exit': release.is_set(),
                'parent_still_running': True, 'owned_server_health_after_cancel': server_ok,
                'output_bytes': len(stdout), 'stderr_bytes': len(stderr),
                'remote_compute_cancellation': 'unverified'}
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=2)
        release.set()
        closer = threading.Thread(target=server.shutdown, daemon=True)
        closer.start()
        closer.join(1)
        server.server_close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--skip-ipc', action='store_true')
    parser.add_argument('--tls-only', action='store_true')
    parser.add_argument('--long-bound', action='store_true', help='HTTP/TLS shutdown at10s, server held12s, plus owned-child abort')
    parser.add_argument('--observation-seconds', type=float, default=CANCEL_BUDGET)
    parser.add_argument('--minimum-server-hold', type=float, default=0)
    parser.add_argument('--request-timeout', type=float, default=5)
    parser.add_argument('--cert')
    parser.add_argument('--key')
    args = parser.parse_args()
    if args.case:
        print(json.dumps(network_case(args.case, args.cert, args.key, args.observation_seconds,
                                      args.minimum_server_hold, args.request_timeout)), flush=True)
        return
    directory = ROOT / '.audit-tmp'
    directory.mkdir(exist_ok=True)
    openssl = shutil.which('openssl')
    cert_args = []
    tls_evidence = 'unverified: no existing openssl executable'
    if openssl:
        certificates = directory / ('cancellation-tls-' + uuid.uuid4().hex[:8])
        certificates.mkdir()
        cert, key = certificates / 'cert.pem', certificates / 'key.pem'
        configuration = certificates / 'openssl.cnf'
        configuration.write_text('[req]\ndistinguished_name=dn\n[dn]\nCN=localhost\n', encoding='utf-8')
        generated = subprocess.run([openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
            '-config', str(configuration), '-keyout', str(key), '-out', str(cert),
            '-days', '1', '-subj', '/CN=localhost'],
            capture_output=True, timeout=10)
        if generated.returncode == 0:
            cert_args = ['--cert', str(cert), '--key', str(key)]
            tls_evidence = 'local self-signed certificate generated by existing ' + openssl
        else:
            tls_evidence = 'unverified: existing openssl certificate generation failed: ' + generated.stderr.decode('utf-8', errors='replace')[-1000:]
    results = []
    names = ('http_body_shutdown_close', 'https_body_shutdown_close') if args.long_bound else CASES
    def run_case(name):
        if args.tls_only and 'https' not in name:
            return None
        if 'https' in name and not cert_args:
            return {'case': name, 'tls': 'unverified'}
        timing_args = (['--observation-seconds', '10', '--minimum-server-hold', '12', '--request-timeout', '20']
                       if args.long_bound else [])
        try:
            process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--case', name, *cert_args, *timing_args],
                                     capture_output=True, text=True, timeout=22 if args.long_bound else 12)
            if process.returncode:
                result = {'case': name, 'probe_error': process.stderr[-2000:], 'exit_code': process.returncode}
            else:
                result = json.loads(process.stdout)
        except subprocess.TimeoutExpired:
            result = {'case': name, 'cancellation_verdict': 'unresolved_owned_probe_process_deadline'}
        print(json.dumps(result), flush=True)
        return result
    if args.long_bound:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [result for result in pool.map(run_case, names) if result is not None]
    else:
        results = [result for name in names if (result := run_case(name)) is not None]
    report = {'interpreter': sys.executable, 'python': sys.version, 'platform': sys.platform,
              'network_cases': results, 'tls_fixture': tls_evidence,
              'remote_compute_cancellation': 'not tested or established'}
    if not args.skip_ipc:
        report['ipc'] = ipc_probe()
    if args.long_bound:
        report['owned_child_network'] = owned_child_network_probe()
        print(json.dumps(report['owned_child_network']), flush=True)
    directory = ROOT / '.audit-tmp'
    directory.mkdir(exist_ok=True)
    path = directory / ('http-cancellation-probe-' + uuid.uuid4().hex[:8] + '.json')
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'evidence_file': str(path), 'interpreter': sys.executable,
                      'ipc': report.get('ipc')}), flush=True)


if __name__ == '__main__':
    main()
