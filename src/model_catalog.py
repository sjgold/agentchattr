"""Metadata-only model discovery. Importing or reading a catalog never probes a client."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from urllib.parse import urlsplit
import urllib.request


class CatalogError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def discovery_kind(provider):
    if provider.get('type') == 'api':
        host = urlsplit(provider.get('base_url', '')).hostname
        return {'api.deepseek.com': 'deepseek', 'api.meta.ai': 'muse',
                'api.z.ai': 'glm'}.get(host)
    command = re.split(r'[/\\]', provider.get('command', ''))[-1].lower()
    return {'claude': 'claude', 'claude.exe': 'claude', 'codex': 'codex',
            'codex.exe': 'codex', 'agy': 'antigravity', 'agy.exe': 'antigravity'}.get(command)


def _text(value):
    return isinstance(value, str) and 0 < len(value) <= 256 and not any(ord(c) < 32 for c in value)


def model_entry(model_id, name=None, efforts=None, reasoning_known=False):
    if not _text(model_id) or model_id.startswith('-'):
        raise CatalogError('The model catalog contains an invalid model ID.')
    if efforts is None:
        efforts = []
    if not isinstance(efforts, list) or any(not _text(e) for e in efforts):
        raise CatalogError('The model catalog contains invalid effort metadata.')
    return {'id': model_id, 'name': name if _text(name) else model_id,
            'reasoning_efforts': list(dict.fromkeys(efforts)),
            'reasoning_known': bool(reasoning_known), 'available': True}


def _nonempty(entries):
    if not entries:
        raise CatalogError('The metadata probe returned no models; availability is unverified.')
    if len({m['id'] for m in entries}) != len(entries):
        raise CatalogError('The metadata probe returned duplicate model IDs.')
    return entries


def _probe_environment(provider):
    env = dict(os.environ)
    env.pop('CLAUDECODE', None)
    for name in set(provider.get('_catalog_strip_env', [])) | set(provider.get('strip_env', [])):
        env.pop(name, None)
    return env


def _run(command, *, input=None, timeout=25, env=None):
    options = {'input': input, 'capture_output': True, 'text': True, 'encoding': 'utf-8',
               'errors': 'replace', 'timeout': timeout, 'env': env or _probe_environment({})}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(command, **options)


def probe_claude(provider, run=_run):
    command = [provider['command'], '--print', '--input-format', 'stream-json',
               '--output-format', 'stream-json', '--verbose', '--no-session-persistence',
               '--setting-sources', '', '--strict-mcp-config', '--mcp-config',
               '{"mcpServers":{}}', '--settings', '{"disableAllHooks":true}']
    control = {'type': 'control_request', 'request_id': 'catalog-init',
               'request': {'subtype': 'initialize', 'hooks': None}}
    result = run(command, input=json.dumps(control) + '\n', timeout=25, env=_probe_environment(provider))
    if result.returncode:
        raise CatalogError('Claude metadata initialization failed. Check native login and client availability.')
    for line in result.stdout.splitlines():
        try:
            frame = json.loads(line)
        except ValueError:
            continue
        if not isinstance(frame, dict):
            continue
        response = frame.get('response', {})
        if not isinstance(response, dict):
            continue
        if (frame.get('type') != 'control_response' or response.get('request_id') != 'catalog-init'
                or response.get('subtype') != 'success'):
            continue
        entries = {}
        body = response.get('response', {})
        if not isinstance(body, dict):
            continue
        models = body.get('models')
        if not isinstance(models, list):
            raise CatalogError('Claude did not return model metadata.')
        for item in models:
            if not isinstance(item, dict):
                raise CatalogError('Claude returned invalid model metadata.')
            efforts = item.get('supportedEffortLevels')
            known = isinstance(efforts, list) or item.get('supportsEffort') is False
            entry = model_entry(item.get('value'), item.get('displayName'), efforts, known)
            entries[entry['id']] = entry
            resolved = item.get('resolvedModel')
            if resolved and resolved not in entries:
                entries[resolved] = model_entry(resolved, item.get('displayName'), efforts, known)
        return {'models': _nonempty(list(entries.values())), 'source': 'claude-native-initialize',
                'complete': True, 'retirement_authoritative': False, 'catalog_fetched_at': utc_now()}
    raise CatalogError('Claude metadata initialization produced no catalog response.')


def read_codex_cache(path=None):
    path = path or Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'models_cache.json'
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict) or not isinstance(value.get('models'), list):
        raise CatalogError('Codex native cache contains invalid model metadata.')
    entries = []
    for model in value['models']:
        if not isinstance(model, dict):
            raise CatalogError('Codex native cache contains invalid model metadata.')
        if model.get('visibility') != 'list':
            continue
        efforts = model.get('supported_reasoning_levels')
        entries.append(model_entry(model['slug'], model.get('display_name'),
                                   [e['effort'] for e in efforts] if isinstance(efforts, list) else None,
                                   isinstance(efforts, list)))
    return {'models': _nonempty(entries), 'source': 'codex-native-cache', 'complete': False,
            'catalog_fetched_at': value.get('fetched_at')}


def probe_codex(provider):
    """A dedicated catalog process creates no thread/turn and owns no seat process."""
    try:
        before = read_codex_cache()
    except (OSError, ValueError, KeyError, TypeError):
        before = None
    options = {'stdin': subprocess.PIPE, 'stdout': subprocess.PIPE, 'stderr': subprocess.DEVNULL,
               'text': True, 'encoding': 'utf-8', 'errors': 'replace', 'env': _probe_environment(provider)}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW
    process = subprocess.Popen([provider['command'], 'app-server', '--stdio',
                                '-c', 'mcp_servers={}', '-c', 'features.codex_hooks=false',
                                '-c', 'features.plugins=false'], **options)
    lines = queue.Queue()
    def read():
        for line in process.stdout:
            lines.put(line)
        lines.put(None)
    threading.Thread(target=read, daemon=True).start()
    def send(frame):
        process.stdin.write(json.dumps(frame) + '\n')
        process.stdin.flush()
    def response(request_id, deadline):
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=max(.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if line is None:
                break
            try:
                frame = json.loads(line)
            except ValueError:
                continue
            if isinstance(frame, dict) and 'method' not in frame and frame.get('id') == request_id:
                if 'error' in frame:
                    raise CatalogError('Codex model metadata request failed.')
                result = frame.get('result', {})
                if not isinstance(result, dict):
                    raise CatalogError('Codex returned invalid metadata response.')
                return result
        raise CatalogError('Codex metadata initialization timed out.')
    try:
        deadline = time.monotonic() + 18
        send({'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'agentchattr-catalog', 'version': '1.0'}}})
        response(1, deadline)
        send({'method': 'initialized', 'params': {}})
        send({'id': 2, 'method': 'model/list', 'params': {'includeHidden': False}})
        listing = response(2, deadline)
        # Native startup refresh runs independently; only an advanced cache timestamp
        # proves this process obtained current remote metadata. RPC success alone does not.
        while time.monotonic() < deadline:
            try:
                current = read_codex_cache()
                if current['catalog_fetched_at'] and (not before or
                        current['catalog_fetched_at'] != before['catalog_fetched_at']):
                    return {**current, 'source': 'codex-native-refreshed-cache', 'complete': True,
                            'retirement_authoritative': False}
            except (OSError, ValueError, KeyError, TypeError):
                pass
            if time.monotonic() + .2 >= deadline:
                break
            time.sleep(.2)
        if before:
            return {**before, 'error': 'Codex returned its native cache; a fresh remote refresh could not be verified.'}
        entries = [model_entry(item.get('model') or item.get('id'), item.get('displayName'),
                   [e['reasoningEffort'] for e in item.get('supportedReasoningEfforts', [])],
                   'supportedReasoningEfforts' in item) for item in listing.get('data', [])
                   if not item.get('hidden')]
        return {'models': _nonempty(entries), 'source': 'codex-native-catalog', 'complete': False,
                'catalog_fetched_at': None, 'error': 'Native catalog freshness is unverified.'}
    finally:
        for cleanup in (process.kill, lambda: process.wait(timeout=5), process.stdin.close, process.stdout.close):
            try:
                cleanup()
            except (OSError, subprocess.TimeoutExpired):
                pass


def probe_antigravity(provider, run=_run):
    result = run([provider['command'], 'models'], timeout=25, env=_probe_environment(provider))
    if result.returncode or any(term in result.stderr.lower() for term in
            ('not logged', 'auth mode is unspecified', 'error getting token', 'access is denied')):
        raise CatalogError('Antigravity model discovery failed. Native authentication or credential storage is unavailable.')
    entries = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'\s*(?:[-*]\s+)?([a-z0-9][a-z0-9._/-]*-[a-z0-9._/-]+)\s+(.+?)\s*', line)
        if not match:
            raise CatalogError('Antigravity model-list format changed; availability is unverified.')
        entries.append(model_entry(match[1], match[2]))
    return {'models': _nonempty(entries), 'source': 'antigravity-native-models',
            'complete': True, 'retirement_authoritative': False, 'catalog_fetched_at': utc_now()}


def probe_api(provider, opener=None):
    kind = discovery_kind(provider)
    from launcher import NoRedirect
    opener = opener or urllib.request.build_opener(NoRedirect)
    headers = {'Accept': 'application/json'}
    reference = provider.get('api_key_env')
    if reference:
        secret = os.environ.get(reference)
        if not secret:
            raise CatalogError('Model discovery requires the configured credential in the server environment.')
        headers['Authorization'] = 'Bearer ' + secret
    request = urllib.request.Request(provider['base_url'].rstrip('/') + '/models', headers=headers, method='GET')
    with opener.open(request, timeout=12) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise CatalogError('Model metadata exceeds the 2 MiB limit.')
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise CatalogError('The provider did not return a model-list response.')
    entries = []
    for item in payload['data']:
        if not isinstance(item, dict):
            raise CatalogError('The provider returned invalid model metadata.')
        effort = item.get('effort', {}) if kind == 'deepseek' else {}
        levels = effort.get('supported_levels') if isinstance(effort, dict) else None
        entries.append(model_entry(item.get('id'), item.get('name'), levels, isinstance(levels, list)))
    complete = not any(payload.get(k) for k in ('has_more', 'next', 'next_cursor', 'nextCursor'))
    return {'models': _nonempty(entries), 'source': kind + '-models-endpoint', 'complete': complete,
            'retirement_authoritative': complete,
            'capability_note': ('This provider catalog does not declare chat compatibility for every model. '
                                'Verify the selected model supports chat completions.') if kind in ('muse', 'glm') else None,
            'catalog_fetched_at': utc_now(),
            'error': None if complete else 'The provider returned a partial model catalog.'}


def probe_provider(provider):
    kind = discovery_kind(provider)
    if kind == 'claude':
        return probe_claude(provider)
    if kind == 'codex':
        return probe_codex(provider)
    if kind == 'antigravity':
        return probe_antigravity(provider)
    if kind in ('deepseek', 'muse', 'glm'):
        return probe_api(provider)
    raise CatalogError('This client has no verified model metadata adapter.')


class ModelCatalog:
    def __init__(self, data_dir, providers, probe=probe_provider):
        self.directory = Path(data_dir) / 'model_catalogs'
        self.providers = providers
        self.probe = probe
        self.lock = threading.RLock()
        self.states = {}
        self.jobs = {}
        self.timers = {}
        self.api_key_names = [p['api_key_env'] for p in providers.values() if p.get('api_key_env')]

    def _identity(self, name):
        provider = self.providers[name]
        identity = {k: provider.get(k) for k in ('command', 'cwd', 'base_url', 'api_key_env')}
        # Credential values never leave the process or enter persisted model metadata.
        reference = provider.get('api_key_env')
        identity['credential_digest'] = hashlib.sha256(os.environ.get(reference, '').encode()).hexdigest() if reference else None
        identity['native_home'] = os.environ.get('CODEX_HOME') if discovery_kind(provider) == 'codex' else None
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    def _state(self, name):
        identity = self._identity(name)
        if name not in self.states or self.states[name][0] != identity:
            state = {'dynamic': bool(discovery_kind(self.providers[name])), 'models': [], 'source': None,
                     'checked_at': None, 'catalog_fetched_at': None, 'complete': False,
                     'authoritative': False, 'retirement_authoritative': False, 'refreshing': False, 'error': None,
                     'capability_note': None}
            configured = self.providers[name].get('models', [])
            state['configured_models'] = [m for m in configured if _text(m)] if isinstance(configured, list) else []
            default_model = self.providers[name].get('default_model') or self.providers[name].get('model')
            if _text(default_model) and default_model not in state['configured_models']:
                state['configured_models'].append(default_model)
            try:
                saved = json.loads((self.directory / (identity + '.json')).read_text(encoding='utf-8'))
                if saved.get('version') == 1 and saved.get('identity') == identity:
                    retained = saved['catalog']
                    entries = _nonempty([model_entry(m['id'], m.get('name'), m.get('reasoning_efforts'),
                                                      m.get('reasoning_known')) for m in retained['models']])
                    state.update({k: retained[k] for k in ('source', 'checked_at', 'catalog_fetched_at',
                                  'authoritative', 'error', 'capability_note') if k in retained})
                    state.update(models=entries, refreshing=False, complete=False)
            except (OSError, ValueError, KeyError, TypeError):
                pass
            self.states[name] = (identity, state)
        return self.states[name][1]

    def snapshot(self, name):
        with self.lock:
            state = deepcopy(self._state(name))
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(state['checked_at'])).total_seconds()
                if age > 300:
                    state.update(complete=False, retirement_authoritative=False)
            except (TypeError, ValueError):
                state.update(complete=False, retirement_authoritative=False)
            return state

    def refresh(self, name=None):
        names = [name] if name else list(self.providers)
        if any(n not in self.providers for n in names):
            raise CatalogError('Select a configured provider to refresh.')
        with self.lock:
            for current in names:
                state = self._state(current)
                if not state['dynamic'] or current in self.jobs:
                    continue
                state['refreshing'] = True
                identity = self.states[current][0]
                token = object()
                self.jobs[current] = token
                timer = threading.Timer(30, self._expire, args=(current, identity, token))
                self.timers[current] = timer
                timer.daemon = True
                timer.start()
                threading.Thread(target=self._refresh, args=(current, identity), daemon=True).start()

    def _expire(self, name, identity, token):
        with self.lock:
            if self.jobs.get(name) is token and self.states.get(name, (None,))[0] == identity:
                self.states[name][1].update(refreshing=False, complete=False, retirement_authoritative=False,
                    error='Model metadata probe exceeded its deadline. The previous catalog is retained.')

    def _refresh(self, name, identity):
        try:
            provider = deepcopy(self.providers[name])
            provider['_catalog_strip_env'] = self.api_key_names
            result = self.probe(provider)
            result['models'] = _nonempty(result['models'])
            failure = result.get('error')
            if not result.get('complete') and not failure:
                failure = 'The metadata catalog is partial or its freshness is unverified.'
        except Exception as exc:
            # Never expose provider bodies, subprocess stderr, request URLs or credentials.
            result = None
            failure = str(exc) if isinstance(exc, CatalogError) else 'Model metadata probe failed. Check native login, endpoint and connection.'
        with self.lock:
            self.jobs.pop(name, None)
            timer = self.timers.pop(name, None)
            if timer:
                timer.cancel()
            if self._identity(name) != identity:
                return
            state = self._state(name)
            expired = not state['refreshing'] and state.get('error', '').startswith('Model metadata probe exceeded') if state.get('error') else False
            if expired:
                return
            state.update(checked_at=utc_now(), refreshing=False, error=failure, complete=False, retirement_authoritative=False)
            if result:
                if result.get('complete'):
                    state.update(result, authoritative=True)
                else:
                    # Partial discovery adds models; it never removes or overrides known rows.
                    retained = {m['id']: m for m in state['models']}
                    for model in result['models']:
                        retained.setdefault(model['id'], model)
                    if not state['models']:
                        state.update(source=result.get('source'), catalog_fetched_at=result.get('catalog_fetched_at'),
                                     capability_note=result.get('capability_note'))
                    state['models'] = list(retained.values())
            try:
                from api_seats import atomic_json
                atomic_json(self.directory / (identity + '.json'),
                            {'version': 1, 'identity': identity, 'catalog': state})
            except OSError:
                state['error'] = 'Catalog checked, but its private cache could not be saved.'

    def provider_for_seat(self, seat, preserve_unknown=False):
        provider = deepcopy(self.providers[seat['provider']])
        state = self.snapshot(seat['provider'])
        if not state['dynamic']:
            return provider
        provider['_catalog_dynamic'] = True
        selected = seat['model'] or (provider.get('default_model') if seat['adapter'] == 'cli' else None)
        model = next((m for m in state['models'] if m['id'] == selected), None)
        from api_seats import SeatError
        account_matches = seat['adapter'] == 'cli' or seat.get('secret_ref', '') == provider.get('api_key_env', '')
        if not account_matches:
            model = None
        fresh = state['complete'] and account_matches
        if selected and fresh and state['retirement_authoritative'] and model is None:
            raise SeatError('The selected model is unavailable in the last complete catalog. Choose an available model or refresh models.')
        known = bool(fresh and model and model['reasoning_known'])
        if known and seat['reasoning'] is not None and seat['reasoning'] not in model['reasoning_efforts']:
            raise SeatError('The selected model does not support this reasoning effort. Choose a supported effort or Provider default.')
        if not known and not preserve_unknown and seat['reasoning'] is not None and seat['reasoning'] not in provider.get('reasoning_efforts', []):
            raise SeatError('Model effort metadata is unavailable; select a configured effort or Provider default.')
        if model:
            provider['_catalog_model'] = deepcopy(model)
            provider['_catalog_model']['reasoning_known'] = known
        return provider


def validate_frozen_effort(seat, provider):
    from api_seats import SeatError
    model = provider.get('_catalog_model')
    if model and model.get('reasoning_known') and seat.get('reasoning') is not None:
        if seat['reasoning'] not in model.get('reasoning_efforts', []):
            raise SeatError('The selected model does not support this reasoning effort.')
