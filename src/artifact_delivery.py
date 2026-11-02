"""Owned artifact result files and delivery only, never model generation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import urllib.error

from api_seats import atomic_json
from artifact_protocol import (MAX_RESULT_RECORD_BYTES, MAX_ACK_BYTES, seal_result, validate_payload,
                               _owned_path, _size)
from artifact_store import (ArtifactConflict, ArtifactUnavailable, ArtifactValidationError,
    QUARANTINE_REASONS, request_ids, _fields, _hex, _integer, _number, _observation)
from launcher import LaunchError, startup_lock
from runtime_ownership import _validate
from sealed_result_io import deliver_saved, put_immutable_json, read_bounded_json


class ArtifactRejected(ArtifactValidationError):
    def __init__(self, diagnostic_id, reason):
        super().__init__('Artifact result was quarantined; operator action is required.')
        self.diagnostic_id, self.reason = diagnostic_id, reason


def _read(path, maximum):
    try:
        return read_bounded_json(path, maximum)
    except (OSError, ValueError, TypeError, RecursionError):
        raise ArtifactUnavailable('Saved artifact delivery storage is unavailable; files were preserved.') from None


class ArtifactOutbox:
    def __init__(self, runtime_path):
        self.runtime_path = Path(runtime_path).absolute()
        _owned_path(self.runtime_path, self.runtime_path)
        self.identity, self.adapter = self._identity()

    def _identity(self):
        path = _owned_path(self.runtime_path, self.runtime_path / 'config.json')
        snapshot = _read(path, MAX_RESULT_RECORD_BYTES)
        try:
            validated = _validate(path, snapshot)
            if validated is None:
                raise ValueError('No managed launch')
            identity = validated[0]
            adapter = snapshot['seat']['adapter']
            if hasattr(self, 'identity') and (self.identity != identity or self.adapter != adapter):
                raise ArtifactConflict('Immutable artifact launch ownership changed.')
            return identity, adapter
        except ArtifactConflict:
            raise
        except (ValueError, TypeError, KeyError):
            raise ArtifactUnavailable('Managed artifact result ownership is unavailable.') from None

    def _path(self, dispatch_id, kind='result'):
        folders = {'result': 'artifact_results', 'ack': 'artifact_acks', 'disposition': 'artifact_dispositions',
                   'lock': 'artifact_result_locks'}
        return _owned_path(self.runtime_path, self.runtime_path / folders[kind] / (_hex(dispatch_id) + '.json'))

    def _bound(self, record, dispatch_id):
        _fields(record, ('payload', 'seal'))
        payload = validate_payload(record['payload'])
        _hex(record['seal'], 64)
        identity, adapter = self._identity()
        if (payload['dispatch_id'] != dispatch_id or payload['launch_attempt'] != identity['attempt']
                or payload['launch_nonce'] != identity['launch_nonce'] or payload['fingerprint'] != identity['fingerprint']):
            raise ArtifactConflict('Saved artifact result belongs to a different immutable launch.')
        _observation(payload['observation'], adapter)
        return {'payload': payload, 'seal': record['seal']}

    def save(self, payload, seal_secret):
        record = seal_result(payload, seal_secret)
        dispatch = record['payload']['dispatch_id']
        self._bound(record, dispatch)
        _size(record, MAX_RESULT_RECORD_BYTES)
        try:
            return put_immutable_json(self._path(dispatch), record,
                lock=startup_lock(self._path(dispatch, 'lock'), time.monotonic() + 10),
                load_existing=lambda: self.get(dispatch), write=atomic_json, conflict_error=ArtifactConflict)
        except (OSError, LaunchError):
            raise ArtifactUnavailable('Artifact result write did not complete.') from None

    def get(self, dispatch_id):
        path = self._path(dispatch_id)
        try:
            return self._bound(_read(path, MAX_RESULT_RECORD_BYTES), dispatch_id)
        except ArtifactConflict:
            raise
        except (ValueError, TypeError, KeyError):
            raise ArtifactUnavailable('Saved artifact result is malformed; it was preserved.') from None

    def find(self, dispatch_id):
        self._identity()
        path = self._path(dispatch_id)
        try:
            path.stat()
        except FileNotFoundError:
            return None
        except OSError:
            raise ArtifactUnavailable('Saved artifact availability cannot be checked safely.') from None
        return self.get(dispatch_id)

    def list_records(self, *, limit=100):
        _integer(limit, 1, 100)
        self._identity()
        folder = _owned_path(self.runtime_path, self.runtime_path / 'artifact_results')
        try:
            paths = sorted(folder.glob('*.json'))
            rows = [self.get(path.stem) for path in paths[:limit]]
            return {'rows': rows, 'count': len(paths), 'truncated': len(rows) < len(paths)}
        except (OSError, ValueError):
            raise ArtifactUnavailable('Artifact result inventory is unavailable.') from None

    def _aux(self, dispatch, kind):
        self._identity()
        path = self._path(dispatch, kind)
        try:
            path.stat()
        except FileNotFoundError:
            return None
        except OSError:
            raise ArtifactUnavailable('Artifact delivery receipt cannot be read.') from None
        record = self.get(dispatch)
        value = _read(path, MAX_ACK_BYTES)
        try:
            fields = ('version', 'purpose', 'result_id', 'accepted_event_id', 'request_id', 'acknowledged_at') if kind == 'ack' else (
                'version', 'purpose', 'result_id', 'diagnostic_id', 'reason', 'recorded_at')
            _fields(value, fields)
            if type(value['version']) is not int or value['version'] != 1 or value['purpose'] != 'artifact-v1' or value['result_id'] != dispatch:
                raise ValueError('Different receipt scope')
            if kind == 'ack':
                if value['accepted_event_id'] != dispatch or value['request_id'] != record['payload']['request_id']:
                    raise ValueError('Different admission')
                _number(value['acknowledged_at'])
            else:
                _hex(value['diagnostic_id'])
                if not isinstance(value['reason'], str) or value['reason'] not in QUARANTINE_REASONS:
                    raise ValueError('Unknown diagnostic')
                _number(value['recorded_at'])
            return deepcopy(value)
        except (ValueError, TypeError, KeyError):
            raise ArtifactUnavailable('Artifact delivery receipt is malformed; it was preserved.') from None

    def get_ack(self, dispatch_id):
        return self._aux(dispatch_id, 'ack')

    def get_disposition(self, dispatch_id):
        return self._aux(dispatch_id, 'disposition')

    def acknowledge(self, dispatch_id, accepted_event_id):
        _hex(dispatch_id)
        if _hex(accepted_event_id) != dispatch_id:
            raise ArtifactConflict('Artifact acknowledgement identifies another dispatch.')
        try:
            with startup_lock(self._path(dispatch_id, 'lock'), time.monotonic() + 10):
                record = self.get(dispatch_id)
                prior = self.get_ack(dispatch_id)
                if prior is not None:
                    return prior
                if self.get_disposition(dispatch_id) is not None:
                    raise ArtifactConflict('Quarantined artifact delivery cannot be acknowledged.')
                value = {'version': 1, 'purpose': 'artifact-v1', 'result_id': dispatch_id,
                    'accepted_event_id': dispatch_id, 'request_id': record['payload']['request_id'],
                    'acknowledged_at': time.time()}
                atomic_json(self._path(dispatch_id, 'ack'), value)
                return deepcopy(value)
        except (OSError, LaunchError):
            raise ArtifactUnavailable('Artifact acknowledgement write did not complete.') from None

    def quarantine(self, dispatch_id, diagnostic_id, reason):
        _hex(dispatch_id); _hex(diagnostic_id)
        if not isinstance(reason, str) or reason not in QUARANTINE_REASONS:
            raise ArtifactValidationError('Unknown artifact quarantine reason.')
        try:
            with startup_lock(self._path(dispatch_id, 'lock'), time.monotonic() + 10):
                self.get(dispatch_id)
                if self.get_ack(dispatch_id) is not None:
                    raise ArtifactConflict('An admitted artifact acknowledgement cannot be poisoned.')
                prior = self.get_disposition(dispatch_id)
                if prior is not None:
                    if prior['diagnostic_id'] != diagnostic_id or prior['reason'] != reason:
                        raise ArtifactConflict('Artifact disposition is immutable.')
                    return prior
                value = {'version': 1, 'purpose': 'artifact-v1', 'result_id': dispatch_id,
                    'diagnostic_id': diagnostic_id, 'reason': reason, 'recorded_at': time.time()}
                atomic_json(self._path(dispatch_id, 'disposition'), value)
                return deepcopy(value)
        except (OSError, LaunchError):
            raise ArtifactUnavailable('Artifact disposition write did not complete.') from None


def deliver_saved_artifact(box, record, submit):
    _fields(record, ('payload', 'seal'))
    payload = validate_payload(record['payload'])
    dispatch = payload['dispatch_id']
    if box.get(dispatch) != record:
        raise ArtifactConflict('Artifact delivery must use its exact saved record.')
    received = []
    def send(saved):
        try:
            response = submit(saved)
        except urllib.error.HTTPError as exc:
            if exc.code != 409:
                raise
            try:
                raw = exc.read(MAX_ACK_BYTES + 1)
                if len(raw) > MAX_ACK_BYTES:
                    raise ValueError('Oversized ACK')
                def unique(pairs):
                    value = {}
                    for key, item in pairs:
                        if key in value:
                            raise ValueError('Duplicate ACK field')
                        value[key] = item
                    return value
                response = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
            except (ValueError, UnicodeError, RecursionError):
                raise ArtifactValidationError('Artifact ACK is unavailable or malformed.') from None
            finally:
                exc.close()
        if isinstance(response, dict) and response.get('status') == 'quarantined':
            _fields(response, ('status', 'diagnostic_id', 'reason', 'request_terminal', 'received_truncated', 'notice'))
            _hex(response['diagnostic_id'])
            if (type(response['request_terminal']) is not bool or type(response['received_truncated']) is not bool
                    or not isinstance(response['reason'], str) or response['reason'] not in QUARANTINE_REASONS
                    or response['notice'] not in (None, 'response_body_not_retained')):
                raise ArtifactValidationError('Artifact quarantine response is invalid.')
            if response['request_terminal']:
                box.quarantine(dispatch, response['diagnostic_id'], response['reason'])
            raise ArtifactRejected(response['diagnostic_id'], response['reason'])
        _fields(response, ('status', 'event_id', 'request_id', 'version_id', 'sha256'))
        if (response['status'] != 'admitted' or response['event_id'] != dispatch
                or response['request_id'] != payload['request_id']
                or response['version_id'] != request_ids(payload['request_id'])['version_id']
                or response['sha256'] != hashlib.sha256(payload['markdown'].encode('utf-8')).hexdigest()):
            raise ArtifactValidationError('Artifact ACK does not identify the saved result.')
        received.append(deepcopy(response))
        return response
    deliver_saved(record, send, expected_id=dispatch, acknowledge=box.acknowledge,
                  error_factory=ArtifactValidationError)
    return received[-1]
