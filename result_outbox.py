"""Immutable, sealed API review results and separate delivery acknowledgements.

Storage validation is not runtime adoption. Authentication requires the trusted
brief key; neither a local file nor its claimed seat grants admission authority.
"""
from copy import deepcopy
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import time

from api_seats import atomic_json
from launcher import startup_lock
from runtime_ownership import _validate
from turn_events import MAX_EVENT_BYTES, validate_content


class OutboxError(ValueError):
    pass


class OutboxConflict(OutboxError):
    pass


PAYLOAD_FIELDS = frozenset(('version', 'result_id', 'dispatch_id', 'event_id', 'session_id',
    'brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision', 'seat_identity_id',
    'launch_attempt', 'launch_nonce', 'fingerprint', 'kind', 'content', 'created_at'))
MAX_RECORD_BYTES = 6 * MAX_EVENT_BYTES + 16384


def _hex(value, width=32):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{' + str(width) + '}', value):
        raise OutboxError('Result identifiers must use their exact lowercase hexadecimal format.')
    return value


def _timestamp(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise OutboxError('Result timestamps must be finite positive numbers.')


def _scope(value):
    if type(value['version']) is not int or value['version'] != 1:
        raise OutboxError('Unsupported saved result version.')
    for field in ('result_id', 'dispatch_id', 'event_id', 'brief_id', 'run_id', 'attempt_id',
                  'seat_identity_id', 'launch_attempt', 'launch_nonce'):
        _hex(value[field])
    for field in ('input_revision', 'fingerprint'):
        _hex(value[field], 64)
    if value['result_id'] != value['dispatch_id'] or value['result_id'] != value['event_id']:
        raise OutboxError('Result, dispatch and event identifiers must match.')
    if type(value['session_id']) is not int or value['session_id'] <= 0:
        raise OutboxError('A saved result requires a positive session identifier.')
    turn = value['turn_id']
    if (not isinstance(turn, str) or len(turn) > 128
            or not re.fullmatch(re.escape(value['run_id']) + r':[0-9]+:[0-9]+', turn)):
        raise OutboxError('Result turn does not match its run.')


def _payload(value):
    if not isinstance(value, dict) or set(value) != PAYLOAD_FIELDS:
        raise OutboxError('Saved result fields do not match the supported schema.')
    _scope(value)
    _timestamp(value['created_at'])
    try:
        validate_content(value['kind'], value['content'])
    except ValueError:
        raise OutboxError('Saved result must contain valid bounded final/question text.') from None
    return deepcopy(value)


def _record(value):
    if not isinstance(value, dict) or set(value) != {'payload', 'seal'}:
        raise OutboxError('Saved result requires exactly payload and seal.')
    return {'payload': _payload(value['payload']), 'seal': _hex(value['seal'], 64)}


def _mac(payload, secret):
    key = bytes.fromhex(_hex(secret, 64))
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def seal_result(payload, seal_secret):
    value = _payload(payload)
    return {'payload': value, 'seal': _mac(value, seal_secret)}


def verify_result(record, seal_secret):
    value = _record(record)
    if not hmac.compare_digest(value['seal'], _mac(value['payload'], seal_secret)):
        raise OutboxError('Saved result seal does not match its trusted brief.')
    return value['payload']


def _read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise OutboxError('Saved JSON has duplicate fields.')
            result[key] = value
        return result
    try:
        with path.open('rb') as source:
            raw = source.read(MAX_RECORD_BYTES + 1)
        if len(raw) > MAX_RECORD_BYTES:
            raise OutboxError('Saved result file exceeds its storage limit.')
        return json.loads(raw, object_pairs_hook=unique)
    except (OSError, ValueError):
        raise OutboxError('Saved result storage is unavailable or malformed; files were preserved.') from None


def _path_spelling(path):
    value = str(path)
    if os.name == 'nt':
        # A locked Win32 file can resolve with the equivalent extended prefix.
        if value.startswith('\\\\?\\UNC\\'):
            value = '\\\\' + value[8:]
        elif value.startswith('\\\\?\\'):
            value = value[4:]
    return os.path.normcase(os.path.normpath(value))


class ResultOutbox:
    def __init__(self, runtime_path):
        self.runtime_path = Path(runtime_path).resolve()
        self.identity = self._identity()

    def _identity(self):
        path = self.runtime_path / 'config.json'
        snapshot = _read(path)
        try:
            validated = _validate(path, snapshot)
            if validated is None or snapshot.get('seat', {}).get('adapter') != 'openai-compatible':
                raise OutboxError('Only managed API runtime snapshots can own result storage.')
            identity = validated[0]
        except (ValueError, KeyError, TypeError):
            raise OutboxError('Managed API runtime ownership is missing or invalid.') from None
        if hasattr(self, 'identity') and identity != self.identity:
            raise OutboxConflict('The immutable runtime ownership changed.')
        return identity

    def _path(self, result_id, *, ack=False, lock=False):
        _hex(result_id)
        folder = self.runtime_path / ('outbox_ack' if ack else 'outbox')
        path = folder / (result_id + ('.lock' if lock else '.json'))
        if (_path_spelling(folder.resolve()) != _path_spelling(folder)
                or _path_spelling(path.resolve()) != _path_spelling(path)):
            raise OutboxError('Result storage cannot follow redirected directories or files.')
        return path

    def _bound(self, record, result_id):
        value = _record(record)
        payload = value['payload']
        identity = self._identity()
        if (payload['result_id'] != result_id or payload['launch_attempt'] != identity['attempt']
                or payload['launch_nonce'] != identity['launch_nonce']
                or payload['fingerprint'] != identity['fingerprint']):
            raise OutboxError('Saved result does not match this immutable runtime launch.')
        return value

    def save(self, payload, seal_secret):
        record = seal_result(payload, seal_secret)
        result_id = record['payload']['result_id']
        self._bound(record, result_id)
        path = self._path(result_id)
        with startup_lock(self._path(result_id, lock=True), time.monotonic() + 10):
            if path.exists():
                prior = self.get(result_id)
                if prior != record:
                    raise OutboxConflict('A different result already occupies this immutable result ID.')
                return prior
            atomic_json(path, record)
        return deepcopy(record)

    def get(self, result_id):
        return self._bound(_read(self._path(result_id)), result_id)

    def find(self, result_id):
        self._identity()
        try:
            self._path(result_id).stat()
        except FileNotFoundError:
            return None
        except OSError:
            raise OutboxError('Saved result availability cannot be checked safely.') from None
        return self.get(result_id)

    def list_records(self):
        self._identity()
        folder = self._path('0' * 32).parent
        return [self.get(path.stem) for path in sorted(folder.glob('*.json'))]

    def get_ack(self, result_id):
        self._identity()
        path = self._path(result_id, ack=True)
        if not self._path(result_id).exists() and not path.exists():
            return None
        self.get(result_id)
        if not path.exists():
            return None
        value = _read(path)
        if (not isinstance(value, dict) or set(value) != {
                'version', 'result_id', 'accepted_event_id', 'acknowledged_at'}
                or type(value['version']) is not int or value['version'] != 1
                or value['result_id'] != result_id or value['accepted_event_id'] != result_id):
            raise OutboxError('Saved delivery acknowledgement does not match its result.')
        _timestamp(value['acknowledged_at'])
        return value

    def acknowledge(self, result_id, accepted_event_id):
        _hex(result_id)
        if _hex(accepted_event_id) != result_id:
            raise OutboxConflict('The accepted event does not match this saved result.')
        with startup_lock(self._path(result_id, lock=True), time.monotonic() + 10):
            self.get(result_id)
            prior = self.get_ack(result_id)
            if prior is not None:
                return prior
            value = {'version': 1, 'result_id': result_id, 'accepted_event_id': accepted_event_id,
                     'acknowledged_at': time.time()}
            atomic_json(self._path(result_id, ack=True), value)
        return value
