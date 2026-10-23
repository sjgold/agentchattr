"""Secret-free launch intent and worker self-birth, without adoption authority.

The runtime manager must additionally match its own approved server identity,
verify native birth, and receive fresh authenticated adapter evidence.
"""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

from api_seats import atomic_json
from process_identity import capture_birth

_EFFECTIVE_FIELDS = ('seat', 'provider', 'server', 'mcp', 'config_resource')


def _identifier(value, name):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise ValueError(f'{name} must be an exact launch identifier.')


def _key(value):
    if (not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}/[A-Za-z0-9_.-]{1,128}', value)
            or any(part in ('.', '..') for part in value.split('/'))):
        raise ValueError('Launch key must name one package/context and seat.')


def _path(value):
    try:
        return str(Path(value).resolve())
    except (TypeError, OSError, ValueError):
        raise ValueError('Ownership requires a valid local path.') from None


def _fingerprint(effective):
    try:
        return hashlib.sha256(json.dumps(effective, sort_keys=True, allow_nan=False).encode('utf-8')).hexdigest()
    except (TypeError, ValueError):
        raise ValueError('Launch settings must be finite JSON values.') from None


def _server_identity(root, effective):
    if not isinstance(effective, dict) or not isinstance(effective.get('server'), dict):
        raise ValueError('Launch settings require a server mapping.')
    server = effective['server']
    port = server.get('port', 8300)
    if type(port) is not int or not 1 <= port <= 65535 or server.get('host', '127.0.0.1') not in ('127.0.0.1', 'localhost'):
        raise ValueError('Ownership requires the configured IPv4 loopback server.')
    root = _path(root)
    data = _path(Path(root) / server.get('data_dir', './data'))
    identity = {'root': os.path.normcase(root), 'data': os.path.normcase(data),
                'host': server.get('host', '127.0.0.1'), 'port': port, 'mcp': effective.get('mcp', {})}
    return root, data, _fingerprint(identity)


def new_launch_identity(root, effective, key, attempt, boot_id):
    _key(key)
    _identifier(attempt, 'Attempt')
    _identifier(boot_id, 'Boot ID')
    root, data, server = _server_identity(root, effective)
    return {'version': 1, 'root_path': root, 'data_path': data, 'server_identity': server,
            'launch_key': key, 'attempt': attempt, 'launch_nonce': uuid.uuid4().hex,
            'fingerprint': _fingerprint(effective), 'boot_id': boot_id, 'created_at': time.time()}


def _validate(snapshot_path, snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError('Launch snapshot must be a mapping.')
    identity = snapshot.get('ownership')
    if identity is None:
        return None  # Legacy files stay read-only, never manufactured as owned.
    fields = {'version', 'root_path', 'data_path', 'server_identity', 'launch_key',
              'attempt', 'launch_nonce', 'fingerprint', 'boot_id', 'created_at'}
    if (not isinstance(identity, dict) or set(identity) != fields
            or type(identity['version']) is not int or identity['version'] != 1):
        raise ValueError('Unsupported ownership metadata.')
    for key in ('attempt', 'launch_nonce', 'boot_id'):
        _identifier(identity[key], key)
    _key(identity['launch_key'])
    if (type(identity['created_at']) not in (int, float) or not math.isfinite(identity['created_at'])
            or identity['created_at'] <= 0):
        raise ValueError('Launch creation time must be finite and positive.')
    effective = {key: snapshot[key] for key in _EFFECTIVE_FIELDS if key in snapshot}
    root, data, server = _server_identity(identity['root_path'], effective)
    if (root != identity['root_path'] or data != identity['data_path']
            or server != identity['server_identity'] or _fingerprint(effective) != identity['fingerprint']
            or snapshot.get('attempt') != identity['attempt']):
        raise ValueError('Launch ownership does not match its frozen settings.')
    adapter = effective.get('seat', {}).get('adapter')
    if adapter not in ('cli', 'openai-compatible'):
        raise ValueError('Unknown launch adapter.')
    base = ('cli-' if adapter == 'cli' else 'api-') + hashlib.sha256(identity['launch_key'].encode()).hexdigest()[:8] + '-' + identity['attempt'][:12]
    if snapshot.get('base') != base:
        raise ValueError('Launch base does not match its exact attempt.')
    path = Path(snapshot_path).resolve()
    expected = (Path(data) / 'api_seat_runtime' / identity['attempt'] / 'config.json').resolve()
    if path != expected or not path.is_relative_to(Path(data)):
        raise ValueError('Ownership path escapes or does not match its runtime attempt.')
    return deepcopy(identity), path


def _manifest(path, identity):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ValueError('Durable launch intent is unavailable or malformed.') from None
    if (not isinstance(value, dict) or set(value) != set(identity) | {'spawn_outcome'}
            or any(value.get(key) != item for key, item in identity.items())
            or value['spawn_outcome'] not in ('pending', 'spawned', 'failed')):
        raise ValueError('Launch intent belongs to a different attempt or settings.')
    return value


def record_spawn_outcome(snapshot_path, snapshot, outcome):
    validated = _validate(snapshot_path, snapshot)
    if validated is None:
        return None
    identity, path = validated
    if not isinstance(outcome, str) or outcome not in ('pending', 'spawned', 'failed'):
        raise ValueError('Spawn outcome must be pending, spawned or failed.')
    target = path.with_name('launch.json')
    if target.exists():
        previous = _manifest(target, identity)
        if previous['spawn_outcome'] == outcome:
            return previous
        if previous['spawn_outcome'] != 'pending' or outcome == 'pending':
            raise ValueError('A completed spawn decision cannot be rewritten.')
    elif outcome != 'pending':
        raise ValueError('Record launch intent before a spawn outcome.')
    result = {**identity, 'spawn_outcome': outcome}
    atomic_json(target, result)
    return result


def record_worker_birth(snapshot_path, snapshot):
    validated = _validate(snapshot_path, snapshot)
    if validated is None:
        return None
    identity, path = validated
    manifest = _manifest(path.with_name('launch.json'), identity)
    if manifest['spawn_outcome'] == 'failed':
        raise ValueError('A failed spawn cannot claim a worker birth.')
    result = {**capture_birth(), 'attempt': snapshot['attempt'], 'base': snapshot['base'],
              'ownership': identity, 'worker_root': str(Path(__file__).resolve().parent)}
    target = path.with_name('birth.json')
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise ValueError('Existing worker birth is unreadable; it was preserved.') from None
        if existing != result:
            raise ValueError('Worker birth conflicts with existing evidence; it was preserved.')
        return existing
    atomic_json(target, result)
    return result


def heartbeat_payload(birth, boot_id):
    if not birth or 'ownership' not in birth:
        return None
    identity = birth['ownership']
    return {'attempt': identity['attempt'], 'launch_nonce': identity['launch_nonce'],
            'server_identity': identity['server_identity'], 'boot_id': boot_id,
            'worker_pid': birth.get('pid'), 'creation_filetime': birth.get('creation_filetime'),
            'worker_root': birth.get('worker_root')}
