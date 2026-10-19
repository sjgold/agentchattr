"""Validated API-seat packages and OpenAI-compatible request settings."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import shutil
import time
from urllib.parse import urlsplit
import uuid

from launcher import startup_lock


class SeatError(ValueError):
    pass


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', value):
        raise SeatError('IDs must start with a lowercase letter and contain at most 48 lowercase letters, digits or hyphens.')
    return value


def provider_templates(config):
    return {name: deepcopy(cfg) for name, cfg in config.get('agents', {}).items() if cfg.get('type') == 'api'}


def validate_provider(provider):
    url = provider.get('base_url', '')
    if not isinstance(url, str):
        raise SeatError('Provider endpoint must be a URL.')
    try:
        parsed = urlsplit(url)
        parsed.port  # Validate optional port syntax/range before spawning.
    except ValueError:
        raise SeatError('Provider endpoint has invalid URL/port syntax.') from None
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.scheme not in ('http', 'https')
            or (parsed.scheme == 'http' and parsed.hostname not in ('127.0.0.1', 'localhost', '::1'))):
        raise SeatError('Provider requires HTTPS (or loopback HTTP), without URL credentials, query or fragment.')
    reference = provider.get('api_key_env', '')
    if not isinstance(reference, str) or (reference and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', reference)):
        raise SeatError('Provider api_key_env must be an environment-variable reference, never a key value.')
    efforts = provider.get('reasoning_efforts', [])
    if not isinstance(efforts, list) or any(not isinstance(e, str) or not e or len(e) > 40 for e in efforts):
        raise SeatError('Provider reasoning_efforts must be a list of supported strings.')
    temperature = provider.get('temperature')
    if temperature is not None and (isinstance(temperature, bool) or not isinstance(temperature, (int, float))
                                    or not math.isfinite(temperature) or not 0 < temperature <= 2):
        raise SeatError('Provider temperature must be greater than zero and at most two.')


def validate_seat(seat, providers):
    required = {'id', 'name', 'adapter', 'provider', 'model', 'reasoning', 'launch_profile', 'secret_ref'}
    if not isinstance(seat, dict) or set(seat) != required:
        raise SeatError('Seat fields must match the supported schema. Store a secret_ref, never a secret value.')
    identifier(seat['id'])
    if not isinstance(seat['name'], str) or not 1 <= len(seat['name'].strip()) <= 100:
        raise SeatError('Seat name must contain 1–100 characters.')
    if seat['adapter'] not in ('openai-compatible', 'cli') or seat['launch_profile'] != 'standard':
        raise SeatError('Select an API or CLI adapter with the standard launch profile.')
    if not isinstance(seat['provider'], str) or seat['provider'] not in providers:
        raise SeatError('Select a configured API provider template.')
    provider = providers[seat['provider']]
    if seat['adapter'] == 'cli':
        from cli_seats import validate_cli_seat
        return validate_cli_seat(seat, provider)
    validate_provider(provider)
    model = seat['model']
    if model is not None and (not isinstance(model, str) or not model.strip() or len(model) > 256
                              or any(ord(c) < 32 for c in model)):
        raise SeatError('Model must be a nonempty model ID or null for Provider default.')
    reasoning = seat['reasoning']
    if reasoning is not None and (not isinstance(reasoning, str) or reasoning not in provider.get('reasoning_efforts', [])):
        raise SeatError('This provider template does not declare support for the selected reasoning effort.')
    ref = seat['secret_ref']
    if not isinstance(ref, str) or (ref and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', ref)):
        raise SeatError('Secret reference must be an environment-variable name or empty for no authentication.')
    required_ref = provider.get('api_key_env', '')
    if required_ref and not ref:
        raise SeatError('This provider requires a secret reference.')
    return deepcopy(seat)


def validate_package(package, providers):
    if not isinstance(package, dict) or set(package) != {'id', 'name', 'seats'}:
        raise SeatError('Package requires exactly id, name and seats.')
    identifier(package['id'])
    if not isinstance(package['name'], str) or not 1 <= len(package['name'].strip()) <= 100:
        raise SeatError('Package name must contain 1–100 characters.')
    if not isinstance(package['seats'], list) or not package['seats']:
        raise SeatError('A package must contain at least one seat.')
    seats = [validate_seat(seat, providers) for seat in package['seats']]
    if len({s['id'] for s in seats}) != len(seats):
        raise SeatError('Seat IDs must be unique within a package.')
    return {**deepcopy(package), 'seats': seats}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as output:
            json.dump(value, output, ensure_ascii=True, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        # Windows readers may briefly hold the destination without delete-share.
        # Retry only this transient access failure, retaining atomic replacement
        # and a bounded failure for genuinely unwritable paths.
        for attempt in range(8):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(min(0.005 * 2 ** attempt, 0.08))
    finally:
        if temporary.exists():
            temporary.unlink()


class SeatStore:
    def __init__(self, data_dir, providers):
        self.path = Path(data_dir) / 'api_seats.json'
        self.providers = deepcopy(providers)

    def list(self):
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text('utf-8'))
            if not isinstance(data, dict) or set(data) != {'version', 'packages'} or data['version'] != 1:
                raise SeatError('Unsupported package storage schema.')
            if not isinstance(data['packages'], list):
                raise SeatError('Stored packages must be a list.')
            packages = [validate_package(p, self.providers) for p in data['packages']]
            if len({p['id'] for p in packages}) != len(packages):
                raise SeatError('Duplicate stored package ID.')
            return packages
        except (OSError, ValueError, TypeError) as exc:
            raise SeatError('Saved packages are invalid or unreadable; preserved unchanged. Repair or restore the file before saving.') from exc

    def save(self, package):
        package = validate_package(package, self.providers)
        with startup_lock(self.path.with_suffix('.lock'), time.monotonic() + 10):
            packages = self.list()
            updated = [p for p in packages if p['id'] != package['id']] + [package]
            if self.path.exists():
                shutil.copy2(self.path, self.path.with_name('api_seats.' + uuid.uuid4().hex + '.bak'))
            atomic_json(self.path, {'version': 1, 'packages': updated})
        return package

    def seat(self, package_id, seat_id):
        for package in self.list():
            if package['id'] == package_id:
                for seat in package['seats']:
                    if seat['id'] == seat_id:
                        return seat
        raise SeatError('Saved seat not found.')

    def describe_providers(self):
        result = []
        for name, cfg in self.providers.items():
            try:
                if cfg.get('type') != 'api' and cfg.get('command'):
                    from cli_seats import validate_cli_seat
                    validate_cli_seat({'model': None, 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}, cfg)
                    result.append({'id': name, 'name': cfg.get('label', name), 'adapter': 'cli',
                                   'default_model': None, 'models': [m for m in cfg.get('models', []) if isinstance(m, str)] if isinstance(cfg.get('models', []), list) else [],
                                   'reasoning_efforts': cfg.get('reasoning_efforts', []) if cfg.get('cli_reasoning_args') else [],
                                   'supports_model': bool(cfg.get('cli_model_args')), 'secret_ref': '',
                                   'configuration_effects': ('Launch merges MCP identity into ' + str(cfg.get('mcp_settings_path')) +
                                       ' and creates a backup. Only one seat may own this fixed settings path.'
                                       if cfg.get('mcp_inject') == 'settings_file' else
                                       'Launch writes a private MCP identity configuration for this seat. Native login is reused; no authentication home is copied.')})
                    continue
                validate_provider(cfg)
                models = cfg.get('models', [])
                result.append({'id': name, 'name': cfg.get('label', name), 'adapter': 'openai-compatible',
                               'default_model': cfg.get('model') or None,
                               'models': [m for m in models if isinstance(m, str)] if isinstance(models, list) else [],
                               'reasoning_efforts': cfg.get('reasoning_efforts', []),
                               'secret_ref': cfg.get('api_key_env', '')})
            except (SeatError, ValueError):
                result.append({'id': name, 'name': name, 'error': 'Provider template requires configuration repair.'})
        return result


def build_payload(seat, provider, messages):
    validate_seat(seat, {seat['provider']: provider})
    payload = {'messages': messages}
    if seat['model'] is not None:
        payload['model'] = seat['model']
    if seat['reasoning'] is not None:
        payload['reasoning_effort'] = seat['reasoning']
    if provider.get('temperature') is not None:
        payload['temperature'] = provider['temperature']
    return payload


def request_completion(seat, provider, messages, timeout=120):
    import urllib.request
    from launcher import NoRedirect
    payload = build_payload(seat, provider, messages)
    headers = {'Content-Type': 'application/json'}
    reference = seat['secret_ref']
    if reference:
        secret = os.environ.get(reference)
        if not secret:
            raise SeatError('Required credential is unavailable in the server environment.')
        headers['Authorization'] = 'Bearer ' + secret
    request = urllib.request.Request(provider['base_url'].rstrip('/') + '/chat/completions',
                                     data=json.dumps(payload).encode(), headers=headers, method='POST')
    # Do not forward credentials across redirects or through inherited proxies.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise SeatError('Provider response exceeds the 16 MiB response limit.')
        data = json.loads(raw)
    content = data['choices'][0]['message']['content']
    if not isinstance(content, str) or not content.strip():
        raise SeatError('Provider returned no text content.')
    confirmed = data.get('model')
    return {'content': content, 'confirmed_model': confirmed if isinstance(confirmed, str) and confirmed else None}


class Receipt:
    """One atomic, secret-free status document per owned launch attempt."""
    def __init__(self, path, attempt):
        import threading
        self.path, self.attempt = Path(path), attempt
        self.lock = threading.Lock()
        self.value = {'attempt': attempt, 'state': 'starting', 'confirmed_model': None,
                      'authentication': 'unknown', 'adapter_connected': False}

    def update(self, **values):
        with self.lock:
            self.value.update(values)
            self.value['updated_at'] = time.time()
            atomic_json(self.path, self.value)

    def watch_for_stop(self):
        import threading
        def watch():
            while True:
                try:
                    control = json.loads(self.path.with_name('stop.json').read_text('utf-8'))
                    if control.get('attempt') == self.attempt:
                        try:
                            self.update(state='stopped', adapter_connected=False)
                        finally:
                            # Exits the actual worker even when Windows Popen
                            # owns a venv redirector, or its main thread is in I/O.
                            os._exit(0)
                except (OSError, ValueError, AttributeError):
                    pass
                time.sleep(0.1)
        threading.Thread(target=watch, daemon=True).start()
