"""App-owned API wrapper attempts. No provider requests happen at launch."""
from copy import deepcopy
import hashlib
import json
import math
import os
import re
import shutil
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
        self.package_selections = {}
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
        if seat['adapter'] == 'cli':
            from cli_seats import config_resource, validate_cli_seat
            validate_cli_seat(seat, original)
            client = {k: deepcopy(v) for k, v in original.items() if k in
                      ('command', 'cwd', 'cli_args', 'cli_model_args', 'cli_reasoning_args',
                       'cli_version_args', 'reasoning_efforts', 'strip_env', 'inject_delay', 'enter_backend',
                       'cli_fresh_context_args', 'cli_fresh_context_verified')
                      or k.startswith('mcp_')}
            client['cwd'] = str((self.root / client.get('cwd', '.')).resolve())
            if not Path(client['cwd']).is_dir():
                raise SeatError('The configured CLI working directory does not exist.')
            client['command'] = shutil.which(client['command']) or client['command']
            server = deepcopy(self.config.get('server', {}))
            server['data_dir'] = str(self.store.path.parent.resolve())
            if server.get('host', '127.0.0.1') not in ('127.0.0.1', 'localhost'):
                raise SeatError('Managed CLI seats require an IPv4 loopback server.')
            return {'seat': seat, 'provider': client, 'server': server,
                    'mcp': deepcopy(self.config.get('mcp', {})),
                    'config_resource': config_resource(client, client['cwd'])}
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

    def launch_package(self, package_id, revision, restart_seats=None, omitted_seats=None):
        from package_launch import launch_package
        return launch_package(self, package_id, revision, restart_seats, omitted_seats)

    def package_status(self, package_id):
        from package_launch import package_status
        return package_status(self, package_id)

    def continue_package(self, package_id, selection_id):
        from package_launch import continue_package
        return continue_package(self, package_id, selection_id)

    def launch(self, package_id, seat_id, restart=False):
        with self.lock:
            if self.closed.is_set():
                raise SeatError('Server is shutting down; no new seats can launch.')
            seat = self.store.seat(package_id, seat_id)
            effective = self._effective(seat)
            key = package_id + '/' + seat_id
            return self._launch_effective(key, effective, restart)

    def _launch_effective(self, key, effective, restart=False, launch_metadata=None):
        # Caller holds manager.lock. Both normal and corrected launches use the
        # same ownership, resource checks and immutable snapshot writer.
        seat = effective['seat']
        fingerprint = hashlib.sha256(json.dumps(effective, sort_keys=True).encode()).hexdigest()
        previous = self.attempts.get(key)
        if previous:
            current = self._inspect(key)
            alive = previous.get('process') and previous['process'].poll() is None
            if alive and not restart:
                if previous['fingerprint'] == fingerprint and current['state'] in ('starting', 'ready'):
                    return current
                raise SeatError('This seat is already running with changed or failed settings; choose explicit restart.')
            self._release(previous)
        resource = effective.get('config_resource')
        if resource:
            for other in self.attempts.values():
                if (not other.get('released') and other.get('process') and other['process'].poll() is None
                        and other['effective'].get('config_resource') == resource):
                    raise SeatError('This client uses a shared settings file already owned by another seat. Stop it first or configure an isolated client profile.')
        attempt_id = uuid.uuid4().hex
        directory = self.store.path.parent / 'api_seat_runtime' / attempt_id
        attempt = {'id': attempt_id, 'fingerprint': fingerprint, 'process': None,
                   'snapshot': directory / 'config.json', 'receipt': directory / 'receipt.json',
                   'started': time.monotonic(), 'seat': deepcopy(seat), 'effective': effective,
                   'last_receipt_at': None,
                   'state': 'starting', 'error': None, 'name': None,
                   'confirmed_model': None, 'authentication': 'unknown', 'adapter_connected': False}
        attempt.update(launch_metadata or {})
        self.attempts[key] = attempt
        if seat['secret_ref'] and not os.environ.get(seat['secret_ref']):
            attempt.update(state='action_required', error='Required credential is unavailable in the server environment. Set its reference and restart the server.')
            return self._view(attempt)
        cli = seat['adapter'] == 'cli'
        if cli and not shutil.which(effective['provider']['command']):
            attempt.update(state='action_required', error='CLI executable not found. Install or configure it, then retry.',
                           executable=None, startup_checked=False)
            return self._view(attempt)
        base = ('cli-' if cli else 'api-') + hashlib.sha256(key.encode()).hexdigest()[:8] + '-' + attempt_id[:12]
        self.registry.seed({base: {'type': 'cli' if cli else 'api', 'label': seat['name'], 'color': '#60a5fa'}})
        attempt['base'] = base
        snapshot = {**effective, 'attempt': attempt_id, 'base': base, **(launch_metadata or {})}
        try:
            atomic_json(attempt['snapshot'], snapshot)
            # No secret values in arguments, snapshot or managed diagnostics.
            command = [sys.executable, '-u', str(self.root / ('cli_worker.py' if cli else 'wrapper_api.py')), base,
                       '--seat-file', str(attempt['snapshot'])]
            options = {'cwd': str(self.root), 'stdin': subprocess.DEVNULL,
                       'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL,
                       'close_fds': True}
            if sys.platform == 'win32':
                options['creationflags'] = subprocess.CREATE_NEW_CONSOLE if cli else subprocess.CREATE_NO_WINDOW
                if cli:
                    for field in ('stdin', 'stdout', 'stderr'):
                        options.pop(field)
            else:
                options['start_new_session'] = True
            attempt['process'] = subprocess.Popen(command, **options)
        except OSError:
            attempt.update(state='failed', error='Could not start this owned wrapper. Check the application Python environment and retry.')
        return self._view(attempt)

    def _view(self, attempt):
        result = {'attempt': attempt['id'], 'state': attempt['state'], 'error': attempt['error'],
                'name': attempt['name'], 'requested_model': attempt['seat']['model'],
                'confirmed_model': attempt['confirmed_model'], 'authentication': attempt['authentication'],
                'adapter_connected': attempt['adapter_connected'],
                'ready_capability': 'chat_dispatch' if attempt['state'] == 'ready' else None,
                'provider_verified': attempt['authentication'] == 'verified',
                'last_adapter_check': attempt['last_receipt_at'],
                'startup_deadline_seconds': self.timeout}
        if attempt['seat']['adapter'] == 'cli':
            result.update(adapter='cli', executable=attempt.get('executable', attempt['effective']['provider']['command']),
                          startup_checked=attempt.get('startup_checked', False), version=attempt.get('version'),
                          child_exit_code=attempt.get('child_exit_code'),
                          ready_capability='mention_injection' if attempt['state'] == 'ready' else None,
                          provider_verified=False)
        return result

    def _inspect(self, key):
        attempt = self.attempts[key]
        process = attempt['process']
        if process is None or attempt.get('released') or attempt['state'] == 'stopped':
            return self._view(attempt)
        if process.poll() is not None:
            if attempt['seat']['adapter'] == 'cli':
                attempt['child_exit_code'] = process.returncode
                try:
                    final = json.loads(attempt['receipt'].read_text('utf-8'))
                    if (final.get('attempt') == attempt['id'] and
                            final.get('state') in ('stopped', 'failed', 'action_required')):
                        for field in ('state', 'error', 'child_exit_code', 'startup_checked', 'version'):
                            if field in final:
                                attempt[field] = final[field]
                        attempt['adapter_connected'] = False
                        self._release(attempt)
                        return self._view(attempt)
                except (OSError, ValueError, AttributeError):
                    pass
            self._release(attempt)
            attempt.update(state='failed', adapter_connected=False, error=f'Owned wrapper exited (code {process.returncode}). Retry this seat; other seats were not stopped.')
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
            if receipt.get('name'):
                instance = self.registry.get_instance(receipt['name'])
                if instance and instance.get('base') == attempt.get('base'):
                    attempt.setdefault('identity_id', instance['identity_id'])
            if attempt['seat']['adapter'] == 'cli':
                for field in ('startup_checked', 'version', 'child_exit_code'):
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

    def _owned_cli_identity(self, identity_id):
        instance = next((item for item in self.registry.get_all().values()
                         if item['identity_id'] == identity_id), None)
        if instance:
            for attempt in self.attempts.values():
                if (attempt.get('base') == instance.get('base') and not attempt.get('released')
                        and attempt['seat']['adapter'] == 'cli' and attempt.get('process')
                        and attempt['process'].poll() is None):
                    return attempt
        return None

    @staticmethod
    def _provenance_effective(effective):
        # Explicit launch fields only. Never snapshot registry tokens, resolved
        # credentials, arbitrary environment variables or unknown config keys.
        provider_fields = ('base_url', 'reasoning_efforts', 'temperature', 'api_key_env', 'system_prompt',
            'context_messages', 'command', 'cwd', 'cli_args', 'cli_model_args', 'cli_reasoning_args',
            'cli_version_args', 'strip_env', 'inject_delay', 'enter_backend', 'cli_fresh_context_args',
            'cli_fresh_context_verified', 'mcp_inject', 'mcp_flag', 'mcp_transport', 'mcp_merge_project',
            'mcp_env_var', 'mcp_proxy_flag_template', 'mcp_settings_path', 'mcp_http_key')
        result = {'seat': deepcopy(effective['seat']),
                  'provider': {key: deepcopy(value) for key, value in effective['provider'].items() if key in provider_fields},
                  'server': {key: deepcopy(value) for key, value in effective['server'].items() if key in ('host', 'port', 'data_dir')}}
        if 'mcp' in effective:
            result['mcp'] = {key: deepcopy(value) for key, value in effective['mcp'].items() if key in ('http_port', 'sse_port')}
        if 'config_resource' in effective:
            result['config_resource'] = effective['config_resource']
        return result

    def launch_provenance(self, instance):
        with self.lock:
            if not isinstance(instance, dict):
                return None
            live = next((item for item in self.registry.get_all().values()
                         if item['identity_id'] == instance.get('identity_id')), None)
            if not live:
                return None
            for key, attempt in self.attempts.items():
                if (attempt.get('base') == live.get('base') and not attempt.get('released')
                        and attempt.get('identity_id') == live['identity_id']
                        and attempt.get('process') and attempt['process'].poll() is None):
                    effective = self._provenance_effective(attempt['effective'])
                    result = {'key': key, 'launch_attempt': attempt['id'], 'identity_id': live['identity_id'],
                              'effective': effective}
                    payload = effective
                    if attempt.get('context_base_effective'):
                        result['fresh_base_effective'] = self._provenance_effective(attempt['context_base_effective'])
                        payload = {'effective': effective, 'fresh_base_effective': result['fresh_base_effective']}
                    result['fingerprint'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
                    return result
            return None

    def prepare_clean_context(self, provenance, context_key, *, confirmation=None, retry_attempt=None, binding=None):
        with self.lock:
            if self.closed.is_set():
                raise SeatError('Server is shutting down; no corrected context can launch.')
            effective = provenance['effective']
            payload = ({'effective': effective, 'fresh_base_effective': provenance['fresh_base_effective']}
                       if provenance.get('fresh_base_effective') else effective)
            fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
            if fingerprint != provenance.get('fingerprint'):
                raise SeatError('Retained launch provenance does not match its fingerprint.')
            if binding is not None and (not isinstance(binding, dict) or set(binding) != {'child_run_id', 'role'}
                    or not isinstance(binding['child_run_id'], str) or not re.fullmatch(r'[0-9a-f]{32}', binding['child_run_id'])
                    or not isinstance(binding['role'], str) or not binding['role']):
                raise SeatError('Fresh context binding requires its exact child run and role.')
            if effective['seat']['adapter'] == 'cli':
                from cli_seats import build_fresh_context_args
                try:
                    build_fresh_context_args(effective['provider'], context_key)
                except SeatError:
                    return {'state': 'blocked', 'reason': 'unsupported_clean_context', 'clean_context': False}
                key = 'review-' + hashlib.sha256(context_key.encode('utf-8')).hexdigest()[:24] + '/' + effective['seat']['id']
                existing = self.attempts.get(key)
                if existing:
                    if existing.get('context_source_fingerprint') != fingerprint:
                        raise SeatError('Prepared context key belongs to different frozen settings.')
                    if binding is not None and any(existing.get(k) != v for k, v in binding.items()):
                        raise SeatError('Prepared context was not bound to this child and role before launch.')
                    if retry_attempt is None or existing.get('retried_from') == retry_attempt:
                        return self._context_view(key)
                    if existing['id'] != retry_attempt:
                        raise SeatError('Context retry confirmation is stale; refresh its status.')
                    if existing.get('process') and existing['process'].poll() is None:
                        return {'state': 'blocked', 'reason': 'context_retry_needs_termination', 'clean_context': False}
                original = self.attempts.get(provenance['key'])
                if not original or original['id'] != provenance['launch_attempt']:
                    return {'state': 'blocked', 'reason': 'stale_launch_provenance', 'clean_context': False}
                process = original.get('process')
                if process and process.poll() is None:
                    if confirmation is None:
                        return {'state': 'blocked', 'reason': 'confirmation_required', 'clean_context': False,
                                'launch_attempt': original['id']}
                    if (not isinstance(confirmation, dict) or confirmation.get('confirm') is not True
                            or confirmation.get('launch_attempt') != original['id']):
                        raise SeatError('Owned launch confirmation is stale or incomplete.')
                    ended = self.terminate_owned(provenance['identity_id'], original['id'])
                    if not ended['local_ended']:
                        return {'state': 'blocked', 'reason': 'unresolved_child_exit', 'clean_context': False}
                elif not self._cli_exit_proven(original):
                    return {'state': 'blocked', 'reason': 'unresolved_child_exit', 'clean_context': False}
                self._release(original)
                # A distinct nonce is required for every actual fresh launch,
                # including an explicitly retried failed context preparation.
                context_id = uuid.uuid4().hex
                base = deepcopy(provenance.get('fresh_base_effective', effective))
                fresh = deepcopy(base)
                fresh['provider']['cli_args'] = list(fresh['provider'].get('cli_args', [])) + build_fresh_context_args(fresh['provider'], context_id)
                self._launch_effective(key, fresh, launch_metadata={
                    'context_id': context_id, 'context_source_fingerprint': fingerprint,
                    'context_base_effective': base,
                    'context_key': context_key, **(binding or {}),
                    'retried_from': retry_attempt})
                return self._context_view(key)
            attempt = self.attempts.get(provenance['key'])
            if attempt and attempt['id'] == provenance['launch_attempt']:
                view = self._inspect(provenance['key'])
                instance = next((item for item in self.registry.get_all().values()
                    if item['identity_id'] == provenance['identity_id'] and item.get('base') == attempt.get('base')), None)
                if instance and view['state'] == 'ready':
                    return {'state': 'ready', 'identity_id': instance['identity_id'],
                            'key': provenance['key'], 'launch_attempt': attempt['id'], 'name': instance['name'], 'clean_context': True,
                            'verification_basis': 'isolated_request_packet'}
            return {'state': 'blocked', 'reason': 'context_unavailable', 'clean_context': False}

    def retry_context_offer(self, provenance):
        """Describe exact owned retry capability without stopping any process."""
        with self.lock:
            result = {'state': 'blocked', 'clean_context': False, 'old_local_ended': False,
                      'verification_basis': 'same_turn_retry_relaunch'}
            if not isinstance(provenance, dict) or not isinstance(provenance.get('key'), str):
                return dict(result, reason='launch_provenance_unavailable')
            original = self.attempts.get(provenance['key'])
            if not original or original['id'] != provenance['launch_attempt']:
                return dict(result, reason='stale_launch_provenance')
            result['launch_attempt'] = original['id']
            if original['seat']['adapter'] == 'cli' and self._cli_exit_proven(original):
                return dict(result, state='ready', old_local_ended=True)
            live = next((item for item in self.registry.get_all().values()
                         if item['identity_id'] == provenance['identity_id'] and item.get('base') == original.get('base')), None)
            process = original.get('process')
            if not live or original.get('released') or not process or process.poll() is not None:
                return dict(result, reason='owned_context_unavailable')
            if original['seat']['adapter'] == 'cli':
                return dict(result, state='confirmation_required', reason='confirmation_required')
            view = self._inspect(provenance['key'])
            if view.get('adapter_connected'):
                # A failed provider call does not imply its supervisor died.
                return dict(result, state='ready', key=provenance['key'], identity_id=live['identity_id'],
                            name=live['name'], verification_basis='isolated_request_packet')
            return dict(result, reason='owned_context_unavailable')

    def prepare_retry_context(self, provenance, context_key, *, confirmation=None, binding=None):
        """Same-source retry preserves settings and never implies clean native context."""
        with self.lock:
            if self.closed.is_set():
                raise SeatError('Server is shutting down; retry context cannot launch.')
            effective = provenance['effective']
            payload = ({'effective': effective, 'fresh_base_effective': provenance['fresh_base_effective']}
                       if provenance.get('fresh_base_effective') else effective)
            fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
            if fingerprint != provenance.get('fingerprint'):
                raise SeatError('Retry launch provenance does not match its fingerprint.')
            if binding is not None and (not isinstance(binding, dict) or set(binding) != {'child_run_id', 'role'}
                    or not isinstance(binding['child_run_id'], str) or not re.fullmatch(r'[0-9a-f]{32}', binding['child_run_id'])
                    or not isinstance(binding['role'], str) or not binding['role']):
                raise SeatError('Retry context requires its exact run and role binding.')
            if not isinstance(context_key, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,128}', context_key):
                raise SeatError('Retry context key must be a bounded identifier.')
            if confirmation is not None:
                self.validate_context_confirmation(provenance, confirmation)
            if effective['seat']['adapter'] != 'cli':
                return self.retry_context_offer(provenance)
            key = 'retry-' + hashlib.sha256(context_key.encode('utf-8')).hexdigest()[:24] + '/' + effective['seat']['id']
            existing = self.attempts.get(key)
            if existing:
                if (existing.get('context_source_fingerprint') != fingerprint
                        or (binding is not None and any(existing.get(k) != v for k, v in binding.items()))):
                    raise SeatError('Retry context key belongs to different settings or run.')
                return self._context_view(key)
            offer = self.retry_context_offer(provenance)
            if offer['state'] == 'confirmation_required':
                if confirmation is None:
                    return offer
                ended = self.terminate_owned(provenance['identity_id'], provenance['launch_attempt'])
                if not ended['local_ended']:
                    return dict(offer, state='blocked', reason='unresolved_child_exit')
            elif offer['state'] != 'ready':
                return offer
            original = self.attempts[provenance['key']]
            if not self._cli_exit_proven(original):
                return dict(offer, state='blocked', reason='unresolved_child_exit', old_local_ended=False)
            self._release(original)
            context_id = uuid.uuid4().hex
            base = deepcopy(provenance.get('fresh_base_effective', effective))
            fresh = deepcopy(base)
            verified = fresh['provider'].get('cli_fresh_context_verified') is True
            if verified:
                from cli_seats import build_fresh_context_args
                fresh['provider']['cli_args'] = list(fresh['provider'].get('cli_args', [])) + build_fresh_context_args(fresh['provider'], context_id)
            self._launch_effective(key, fresh, launch_metadata={
                'context_id': context_id, 'context_source_fingerprint': fingerprint, 'context_base_effective': base,
                'context_key': context_key, **(binding or {}), 'retry_source_ended': True,
                'verification_basis': 'same_turn_retry_relaunch', 'context_clean_verified': verified})
            return self._context_view(key)

    def fresh_context_owner(self, instance):
        """Resolve read scope before readiness/backlink, without adopting work."""
        if not isinstance(instance, dict):
            return None
        with self.lock:
            live = next((item for item in self.registry.get_all().values()
                         if item['identity_id'] == instance.get('identity_id')), None)
            if not live:
                return None
            for attempt in self.attempts.values():
                if attempt.get('base') == live.get('base'):
                    if attempt.get('child_run_id'):
                        return {key: attempt.get(key) for key in ('child_run_id', 'role', 'context_key')}
                    return None
            # Read-only cold-start fencing is not runtime adoption: no process
            # handle, readiness, retry or dispatch is reconstructed here.
            suffix = live.get('base', '').rsplit('-', 1)[-1]
            if re.fullmatch(r'[0-9a-f]{12}', suffix):
                for path in (self.store.path.parent / 'api_seat_runtime').glob(suffix + '*/config.json'):
                    try:
                        snapshot = json.loads(path.read_text(encoding='utf-8'))
                    except (OSError, ValueError):
                        return {'child_run_id': None, 'role': None, 'context_key': None}
                    if snapshot.get('base') == live['base'] and snapshot.get('child_run_id'):
                        return {key: snapshot.get(key) for key in ('child_run_id', 'role', 'context_key')}
            return None

    def context_status(self, context):
        """Observe a prepared owned attempt; never launch or adopt a replacement."""
        with self.lock:
            key = context.get('key')
            attempt = self.attempts.get(key)
            if not attempt or attempt['id'] != context.get('launch_attempt'):
                return {'state': 'blocked', 'reason': 'prepared_context_changed', 'clean_context': False}
            result = self._context_view(key)
            if attempt['seat']['adapter'] != 'cli':
                result['verification_basis'] = 'isolated_request_packet'
            return result

    def validate_context_confirmation(self, provenance, confirmation):
        with self.lock:
            original = self.attempts.get(provenance['key'])
            if (not isinstance(confirmation, dict) or set(confirmation) != {'launch_attempt', 'confirm'}
                    or confirmation['confirm'] is not True
                    or confirmation['launch_attempt'] != provenance['launch_attempt']
                    or not original or original['id'] != provenance['launch_attempt']):
                raise SeatError('Owned launch confirmation is stale or incomplete; refresh before confirming.')

    @staticmethod
    def _cli_exit_proven(attempt):
        process = attempt.get('process')
        if not process or process.poll() is None:
            return False
        try:
            receipt = json.loads(attempt['receipt'].read_text(encoding='utf-8'))
            return (receipt.get('attempt') == attempt['id'] and receipt.get('state') == 'stopped'
                    and type(receipt.get('child_exit_code')) is int)
        except (OSError, ValueError):
            return False

    def _context_view(self, key):
        view = self._inspect(key)
        attempt = self.attempts[key]
        instance = next((item for item in self.registry.get_all().values()
                        if item['identity_id'] == attempt.get('identity_id') and item.get('base') == attempt.get('base')), None)
        basis = attempt.get('verification_basis', 'verified_fresh_launch_contract')
        clean = basis != 'same_turn_retry_relaunch' or attempt.get('context_clean_verified') is True
        return {'key': key, 'state': view['state'], 'reason': view['error'],
                'launch_attempt': attempt['id'], 'context_id': attempt.get('context_id'),
                'identity_id': instance['identity_id'] if instance else None,
                'name': instance['name'] if instance else None,
                'clean_context': clean and view['state'] == 'ready' and instance is not None,
                'verification_basis': basis, 'old_local_ended': attempt.get('retry_source_ended', False)}

    def termination_offer(self, identity_id):
        with self.lock:
            attempt = self._owned_cli_identity(identity_id)
            if not attempt:
                return None
            return {'launch_attempt': attempt['id'], 'seat_name': attempt['seat']['name'],
                    'impact': 'Terminates this persistent CLI context and disconnects its seat. Other queued work for this seat will need recovery.'}

    def terminate_owned(self, identity_id, launch_attempt):
        with self.lock:
            attempt = self._owned_cli_identity(identity_id)
            if not attempt or attempt['id'] != launch_attempt:
                raise SeatError('Owned CLI launch changed; refresh its termination offer before confirming.')
            # The worker owns the actual CLI process handle and must terminate
            # that child before writing its final receipt. Killing the worker
            # first could orphan that child, so it cannot prove local_ended.
            atomic_json(attempt['snapshot'].with_name('stop.json'), {'attempt': attempt['id']})
            try:
                attempt['process'].wait(timeout=8)
            except subprocess.TimeoutExpired:
                return {'local_ended': False, 'remote_compute': 'unverified'}
            ended = False
            try:
                receipt = json.loads(attempt['receipt'].read_text(encoding='utf-8'))
                ended = (attempt['process'].poll() is not None and receipt.get('attempt') == attempt['id']
                         and receipt.get('state') == 'stopped' and type(receipt.get('child_exit_code')) is int)
            except (OSError, ValueError):
                pass
            if ended:
                attempt.update(released=True, state='stopped', adapter_connected=False)
                for name, item in self.registry.get_all().items():
                    if item.get('base') == attempt.get('base'):
                        self.registry.deregister(name)
            return {'local_ended': ended, 'remote_compute': 'unverified'}

    def shutdown(self):
        self.closed.set()
        with self.lock:
            for attempt in self.attempts.values():
                if attempt['state'] != 'stopped':
                    self._release(attempt)
                    attempt.update(state='stopped', adapter_connected=False)
