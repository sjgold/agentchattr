"""App-owned API wrapper attempts. No provider requests happen at launch."""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

from api_seats import SeatError, atomic_json, validate_package
from launcher import stop_owned_child


class SeatManager:
    def __init__(self, root, config, store, registry, startup_timeout=15, monitor=True):
        self.root, self.config = Path(root), deepcopy(config)
        self.store, self.registry = store, registry
        self.timeout = startup_timeout
        self.attempts = {}
        self.lock = threading.RLock()
        self.closed = threading.Event()
        if monitor:
            self.thread = threading.Thread(target=self._monitor, daemon=True)
            self.thread.start()

    def _monitor(self):
        while not self.closed.wait(0.5):
            with self.lock:
                for key in list(self.attempts):
                    try:
                        self._inspect(key)
                    except (SeatError, OSError):
                        self.attempts[key].update(state='failed', error='Owned wrapper cleanup failed. Check data-directory permissions before retrying.')

    def _effective(self, seat):
        original = self.store.providers[seat['provider']]
        provider = {k: deepcopy(original[k]) for k in ('base_url', 'reasoning_efforts', 'temperature',
                    'api_key_env', 'system_prompt', 'context_messages') if k in original}
        server = deepcopy(self.config.get('server', {}))
        server['data_dir'] = str(self.store.path.parent.resolve())
        if server.get('host', '127.0.0.1') not in ('127.0.0.1', 'localhost'):
            raise SeatError('API wrapper currently requires a server listening on IPv4 loopback.')
        return {'seat': seat, 'provider': provider, 'server': server}

    def save(self, package):
        package = validate_package(package, self.store.providers)
        with self.lock:
            remaining = {s['id'] for s in package['seats']}
            for key, attempt in self.attempts.items():
                package_id, seat_id = key.split('/')
                if package_id == package['id'] and seat_id not in remaining:
                    self._inspect(key)
                    if not attempt.get('released') and attempt.get('process') and attempt['process'].poll() is None:
                        raise SeatError('Stop this owned seat before removing it from the package.')
            return self.store.save(package)

    def launch(self, package_id, seat_id, restart=False):
        with self.lock:
            if self.closed.is_set():
                raise SeatError('Server is shutting down; no new seats can launch.')
            seat = self.store.seat(package_id, seat_id)
            effective = self._effective(seat)
            fingerprint = hashlib.sha256(json.dumps(effective, sort_keys=True).encode()).hexdigest()
            key = package_id + '/' + seat_id
            previous = self.attempts.get(key)
            if previous:
                current = self._inspect(key)
                alive = previous.get('process') and previous['process'].poll() is None
                if alive and not restart:
                    if previous['fingerprint'] == fingerprint and current['state'] in ('starting', 'ready'):
                        return current
                    raise SeatError('This seat is already running with changed or failed settings; choose explicit restart.')
                self._release(previous)
            attempt_id = uuid.uuid4().hex
            directory = self.store.path.parent / 'api_seat_runtime' / attempt_id
            attempt = {'id': attempt_id, 'fingerprint': fingerprint, 'process': None,
                       'snapshot': directory / 'config.json', 'receipt': directory / 'receipt.json',
                       'started': time.monotonic(), 'seat': deepcopy(seat), 'effective': effective,
                       'last_receipt_at': None,
                       'state': 'starting', 'error': None, 'name': None,
                       'confirmed_model': None, 'authentication': 'unknown', 'adapter_connected': False}
            self.attempts[key] = attempt
            if seat['secret_ref'] and not os.environ.get(seat['secret_ref']):
                attempt.update(state='action_required', error='Required credential is unavailable in the server environment. Set its reference and restart the server.')
                return self._view(attempt)
            base = 'api-' + hashlib.sha256(key.encode()).hexdigest()[:8] + '-' + attempt_id[:12]
            self.registry.seed({base: {'type': 'api', 'label': seat['name'], 'color': '#60a5fa'}})
            attempt['base'] = base
            snapshot = {**effective, 'attempt': attempt_id, 'base': base}
            try:
                atomic_json(attempt['snapshot'], snapshot)
                # No secret values in arguments, snapshot or managed diagnostics.
                command = [sys.executable, '-u', str(self.root / 'wrapper_api.py'), base,
                           '--seat-file', str(attempt['snapshot'])]
                options = {'cwd': str(self.root), 'stdin': subprocess.DEVNULL,
                           'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL,
                           'close_fds': True}
                if sys.platform == 'win32':
                    options['creationflags'] = subprocess.CREATE_NO_WINDOW
                else:
                    options['start_new_session'] = True
                attempt['process'] = subprocess.Popen(command, **options)
            except OSError:
                attempt.update(state='failed', error='Could not start this API wrapper. Check the application Python environment and retry.')
            return self._view(attempt)

    def _view(self, attempt):
        return {'attempt': attempt['id'], 'state': attempt['state'], 'error': attempt['error'],
                'name': attempt['name'], 'requested_model': attempt['seat']['model'],
                'confirmed_model': attempt['confirmed_model'], 'authentication': attempt['authentication'],
                'adapter_connected': attempt['adapter_connected'],
                'ready_capability': 'chat_dispatch' if attempt['state'] == 'ready' else None,
                'provider_verified': attempt['authentication'] == 'verified',
                'last_adapter_check': attempt['last_receipt_at'],
                'startup_deadline_seconds': self.timeout}

    def _inspect(self, key):
        attempt = self.attempts[key]
        process = attempt['process']
        if process is None or attempt.get('released') or attempt['state'] == 'stopped':
            return self._view(attempt)
        if process.poll() is not None:
            self._release(attempt)
            attempt.update(state='failed', adapter_connected=False, error='API wrapper exited. Retry this seat; other seats were not stopped.')
            return self._view(attempt)
        receipt = None
        try:
            value = json.loads(attempt['receipt'].read_text('utf-8'))
            if (value.get('attempt') == attempt['id'] and isinstance(value.get('updated_at'), (int, float))
                    and math.isfinite(value['updated_at'])
                    and value.get('state') in ('starting', 'ready', 'failed', 'action_required', 'stopped')
                    and isinstance(value.get('adapter_connected'), bool)
                    and (value.get('state') != 'ready' or (value['adapter_connected'] and isinstance(value.get('name'), str)))
                    and value.get('authentication') in ('unknown', 'verified', 'failed')):
                receipt = value
        except (OSError, ValueError, AttributeError):
            pass
        if receipt:
            attempt['last_receipt_at'] = receipt['updated_at']
            for field in ('state', 'name', 'error', 'authentication', 'adapter_connected', 'confirmed_model'):
                if field in receipt:
                    attempt[field] = receipt[field]
            if receipt['updated_at'] > time.time() + 5 or time.time() - receipt['updated_at'] > self.timeout:
                self._release(attempt)
                attempt.update(state='failed', adapter_connected=False, error='Adapter heartbeat deadline reached. Retry this seat.')
        elif attempt['last_receipt_at'] is not None and time.time() - attempt['last_receipt_at'] > self.timeout:
            self._release(attempt)
            attempt.update(state='failed', adapter_connected=False, error='Adapter receipt unavailable past its deadline. Retry this seat.')
        if attempt['state'] == 'starting' and time.monotonic() - attempt['started'] > self.timeout:
            self._release(attempt)
            attempt.update(state='failed', adapter_connected=False, error='API-seat startup deadline reached. Check server connectivity and retry this seat.')
        return self._view(attempt)

    def inspect(self, package_id, seat_id):
        with self.lock:
            key = package_id + '/' + seat_id
            if key not in self.attempts:
                return {'state': 'not_started', 'requested_model': self.store.seat(package_id, seat_id)['model'],
                        'confirmed_model': None, 'authentication': 'unknown', 'adapter_connected': False}
            return self._inspect(key)

    def snapshot(self):
        with self.lock:
            return {key: self._inspect(key) for key in list(self.attempts)}

    def _release(self, attempt):
        if attempt.get('released'):
            return
        if attempt.get('process'):
            try:
                atomic_json(attempt['snapshot'].with_name('stop.json'), {'attempt': attempt['id']})
            except OSError:
                raise SeatError('Could not request this owned worker to stop. Check data-directory permissions; no replacement was started.') from None
            try:
                attempt['process'].wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            stop_owned_child(attempt['process'])
        # A launch-unique base identifies registrations even if the child died
        # between registering and writing its receipt. No external PID search.
        for name, instance in self.registry.get_all().items():
            if instance.get('base') == attempt.get('base'):
                self.registry.deregister(name)
        attempt['released'] = True

    def stop(self, package_id, seat_id):
        with self.lock:
            key = package_id + '/' + seat_id
            if key not in self.attempts:
                raise SeatError('No owned launch exists for this seat.')
            attempt = self.attempts[key]
            self._release(attempt)
            attempt.update(state='stopped', adapter_connected=False)
            return self._view(attempt)

    def shutdown(self):
        self.closed.set()
        with self.lock:
            for attempt in self.attempts.values():
                if attempt['state'] != 'stopped':
                    self._release(attempt)
                    attempt.update(state='stopped', adapter_connected=False)
