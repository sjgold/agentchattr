"""One owned, cancellable process per blocking provider request.

Only the persistent supervisor publishes replies. The child receives sensitive
request data through stdin and returns a bounded, structured response on stdout.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

MAX_PACKET = 32 * 1024 * 1024


class InvocationCancelled(Exception):
    def __init__(self, local_ended):
        super().__init__('Local invocation ended.' if local_ended else 'Local invocation termination unresolved.')
        self.local_ended = local_ended


class InvocationFailure(Exception):
    def __init__(self, http_status=None):
        super().__init__('Provider invocation failed' + (f' (HTTP {http_status}).' if http_status else '.'))
        self.http_status = http_status


def run_completion(seat, provider, messages, cancel_requested, timeout=120):
    """Return provider text/metadata, or observed cancellation, never stderr data."""
    if cancel_requested():
        raise InvocationCancelled(local_ended=True)
    reference = seat.get('secret_ref', '')
    secret = os.environ.get(reference) if reference else None
    packet = json.dumps({'seat': seat, 'provider': provider, 'messages': messages,
                         'secret': secret, 'timeout': timeout}, ensure_ascii=False).encode('utf-8')
    if len(packet) > MAX_PACKET:
        raise InvocationFailure()
    environment = os.environ.copy()
    if reference:
        environment.pop(reference, None)
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--child'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=environment, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    done = threading.Event()
    output = {}

    def communicate():
        try:
            output['raw'], _ = child.communicate(input=packet)
        except Exception:
            output['error'] = True
        finally:
            done.set()

    communication = threading.Thread(target=communicate, daemon=True)
    communication.start()
    deadline = time.monotonic() + timeout
    cleanup_attempted = False

    def end_child():
        nonlocal cleanup_attempted
        cleanup_attempted = True
        try:
            if child.poll() is None:
                child.terminate()
        except OSError:
            pass
        communication.join(2)
        try:
            if child.poll() is None:
                child.kill()
        except OSError:
            pass
        communication.join(2)
        return child.poll() is not None and done.is_set()

    try:
        while not done.wait(.05):
            if cancel_requested():
                raise InvocationCancelled(local_ended=end_child())
            if time.monotonic() >= deadline:
                if not end_child():
                    raise InvocationCancelled(local_ended=False)
                raise InvocationFailure()
        # A completed response may race Stop. Publication still belongs to the
        # server's durable run fence; this check avoids knowingly submitting it.
        if cancel_requested():
            raise InvocationCancelled(local_ended=child.poll() is not None)
        if child.returncode or output.get('error'):
            raise InvocationFailure()
        raw = output.get('raw', b'')
        if len(raw) > MAX_PACKET:
            raise InvocationFailure()
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise InvocationFailure() from None
        if result.get('status') != 'ok':
            status = result.get('http_status')
            raise InvocationFailure(status if type(status) is int else None)
        return result['result']
    finally:
        if not cleanup_attempted and (child.poll() is None or not done.is_set()):
            end_child()


def _child():
    # No raw exceptions, provider response bodies or credentials reach stderr.
    import urllib.error
    from api_seats import request_completion
    response = {'status': 'error'}
    try:
        raw = sys.stdin.buffer.read(MAX_PACKET + 1)
        if len(raw) > MAX_PACKET:
            raise ValueError('Oversized invocation packet')
        packet = json.loads(raw)
        reference = packet['seat'].get('secret_ref', '')
        if reference and isinstance(packet.get('secret'), str):
            os.environ[reference] = packet['secret']
        result = request_completion(packet['seat'], packet['provider'], packet['messages'],
                                    timeout=packet['timeout'])
        response = {'status': 'ok', 'result': result}
    except urllib.error.HTTPError as exc:
        response['http_status'] = exc.code
    except Exception:
        pass
    encoded = json.dumps(response, ensure_ascii=False).encode('utf-8')
    if len(encoded) > MAX_PACKET:
        encoded = b'{"status":"error"}'
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


if __name__ == '__main__':
    if sys.argv[1:] == ['--child']:
        _child()
