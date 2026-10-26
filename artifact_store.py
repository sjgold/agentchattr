"""Owned artifact metadata and immutable bytes; no dispatch or admission policy."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import uuid

from api_seats import atomic_json
from channel_guards import channel_write
from channel_lifecycle import ChannelConflict, ChannelUnavailable
from sealed_result_io import canonical_utf8
from launcher import LaunchError, startup_lock


MAX_ARTIFACT_BYTES = 512 * 1024
MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_PACKET_MESSAGES = 1000
MAX_DIAGNOSTICS_PER_DISPATCH = 8
MAX_DIAGNOSTIC_DISPATCH_GROUPS = 256
MAX_DIAGNOSTIC_RECORDS = 1024
MAX_QUARANTINE_BODY_BYTES = 8 * 1024 * 1024
MAX_QUARANTINE_OBJECTS = 1024
MAX_DIAGNOSTIC_COUNTER = 2**31 - 1
MAX_DIAGNOSTIC_METADATA_BYTES = 1024 * 1024
MAX_OBJECT_ERRORS = 256
MAX_ARTIFACT_LABEL_BYTES = 256
MAX_ARTIFACT_RECORD_INTEGER = 2**63 - 1
MAX_ARTIFACT_NUMBER_TOKEN_BYTES = 23
_LABEL_CONTROLS = re.compile(r'[\x00-\x1f\x7f]')
_INDEX_CONTROLS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
LIVE = {'prepared', 'queued', 'active'}
TERMINAL = {'fulfilled', 'failed', 'cancelled', 'quarantined', 'imported'}
STATE_REASONS = {None, 'resume_pending', 'queued', 'queued_behind_review', 'source_stopped',
    'operator_cancelled', 'producer_unavailable', 'generation_failed', 'delivery_unconfirmed',
    'invalid_response', 'quarantined', 'imported', 'source_packet_unavailable'}
QUARANTINE_REASONS = {'wrong_identity', 'wrong_attempt', 'wrong_dispatch', 'wrong_brief',
    'wrong_scope', 'wrong_parent', 'cancelled', 'superseded', 'conflicting_duplicate',
    'invalid_content', 'invalid_response', 'unmatched_saved_result', 'source_packet_unavailable', 'response_too_large'}


class ArtifactValidationError(ValueError):
    pass


class ArtifactConflict(ChannelConflict):
    pass


class ArtifactUnavailable(ChannelUnavailable):
    pass


_LEGACY_GUIDANCE = 'Saved development artifacts use schema 1. Conversion is required; no files were reset.'
_AUTHORING_GUIDANCE = 'Saved artifact index is held; repair storage and restart.'
_DIAGNOSTIC_GUIDANCE = 'Artifact diagnostics are unavailable. Repair the diagnostic metadata before retrying.'


class ArtifactDiagnosticsUnavailable(ArtifactUnavailable):
    code = 'artifact_diagnostics_unavailable'

    def __init__(self):
        super().__init__(_DIAGNOSTIC_GUIDANCE)


def _owner_error(owner, legacy):
    if legacy:
        return {'code': 'artifact_legacy_schema_unavailable', 'error': _LEGACY_GUIDANCE}
    return {'code': 'artifact_diagnostics_unavailable' if owner == 'diagnostics' else 'artifact_storage_unavailable',
            'error': _DIAGNOSTIC_GUIDANCE if owner == 'diagnostics' else _AUTHORING_GUIDANCE}


class ArtifactImportCollision(ArtifactConflict):
    def __init__(self, reason, collision_kinds, *, created_objects=()):
        super().__init__('Artifact lineage conflicts with retained immutable storage.')
        self.reason = reason
        self.collision_kinds = tuple(sorted(collision_kinds))
        self._created_objects = created_objects


@dataclass(frozen=True)
class _PreparedLineage:
    root: str
    metadata: bytes
    objects: tuple
    skipped: bool = False
    created_objects: tuple = ()


def _hex(value, width=32):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{' + str(width) + '}', value):
        raise ArtifactValidationError('Invalid artifact identifier.')
    return value


def _fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ArtifactValidationError('Artifact fields do not match the supported schema.')


def _text(value, maximum=None, *, empty=False):
    if not isinstance(value, str) or '\0' in value or (not empty and not value.strip()):
        raise ArtifactValidationError('Artifact text must be valid nonempty UTF-8 without NUL.')
    try:
        raw = value.encode('utf-8')
    except UnicodeError:
        raise ArtifactValidationError('Artifact text must be valid UTF-8.') from None
    if maximum is not None and len(raw) > maximum:
        raise ArtifactValidationError('Artifact text exceeds its byte limit; nothing was truncated.')
    return raw


def _number(value):
    if type(value) not in (int, float):
        raise ArtifactValidationError('Artifact timestamps must be finite positive numbers.')
    try:
        valid = math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ArtifactValidationError('Artifact timestamps must be finite positive numbers.')
    if ((type(value) is int and value > MAX_ARTIFACT_RECORD_INTEGER)
            or (type(value) is float and len(json.dumps(value, allow_nan=False)) > MAX_ARTIFACT_NUMBER_TOKEN_BYTES)):
        raise ArtifactValidationError('Artifact timestamp exceeds its supported numeric width.')
    return value


def _integer(value, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ArtifactValidationError('Invalid artifact count.')
    return value


def _record_integer(value, minimum=0, maximum=None):
    limit = MAX_ARTIFACT_RECORD_INTEGER if maximum is None else min(maximum, MAX_ARTIFACT_RECORD_INTEGER)
    return _integer(value, minimum, limit)


def _label_text(value, maximum=MAX_ARTIFACT_LABEL_BYTES):
    raw = _text(value, maximum)
    if _LABEL_CONTROLS.search(value):
        raise ArtifactValidationError('Artifact labels cannot contain ASCII controls.')
    return raw


def _index_text(value, maximum):
    raw = _text(value, maximum)
    if _INDEX_CONTROLS.search(value):
        raise ArtifactValidationError('Artifact record text permits only HT, LF and CR controls.')
    return raw


def _channel(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,19}', value):
        raise ArtifactValidationError('Invalid artifact channel.')
    return value


def _json(value):
    if value is None or type(value) is bool:
        return
    if isinstance(value, str):
        _text(value, empty=True)
    elif type(value) in (int, float):
        try:
            if not math.isfinite(value):
                raise ArtifactValidationError('Artifact JSON numbers must be finite.')
        except OverflowError:
            raise ArtifactValidationError('Artifact JSON numbers must be finite.') from None
    elif isinstance(value, list):
        for item in value:
            _json(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _text(key, empty=True)
            _json(item)
    else:
        raise ArtifactValidationError('Artifact data must be JSON.')


def _canonical(value):
    try:
        _json(value)
        return canonical_utf8(value)
    except (RecursionError, UnicodeError, OverflowError):
        raise ArtifactValidationError('Artifact JSON is invalid or too deeply nested.') from None


def _uuid(label):
    return uuid.uuid5(uuid.NAMESPACE_URL, label).hex


def request_ids(request_id):
    _hex(request_id)
    return {field: _uuid(f'agentchattr:artifact-v1:{field}:{request_id}') for field in
        ('lineage_id', 'attempt_id', 'dispatch_id', 'brief_id', 'packet_id', 'version_id')}


def _source_run(value):
    if value is None:
        return
    _fields(value, ('session_id', 'run_id', 'input_revision', 'state_at_request'))
    _record_integer(value['session_id'], 1)
    _hex(value['run_id'])
    _hex(value['input_revision'], 64)
    _label_text(value['state_at_request'])


def _packet_scope(packet_id, packet):
    _fields(packet, ('version', 'channel', 'scope_kind', 'source_run', 'input', 'messages'))
    if type(packet['version']) is not int or packet['version'] != 1:
        raise ArtifactValidationError('Unsupported artifact packet version.')
    _channel(packet['channel'])
    if packet['scope_kind'] not in ('run_accepted_messages', 'selected_channel_messages'):
        raise ArtifactValidationError('Invalid artifact source scope.')
    _source_run(packet['source_run'])
    source = packet['input']
    revision = None
    if source is not None:
        _fields(source, ('text', 'input_revision', 'source_document'))
        revision = hashlib.sha256(_text(source['text'], empty=True)).hexdigest()
        if _hex(source['input_revision'], 64) != revision:
            raise ArtifactValidationError('Artifact input revision does not match its exact text.')
        if source['source_document'] is not None and not isinstance(source['source_document'], dict):
            raise ArtifactValidationError('Invalid artifact source document metadata.')
    if packet['source_run'] is not None and packet['source_run']['input_revision'] != revision:
        raise ArtifactValidationError('Artifact source run and input revision differ.')
    messages = packet['messages']
    if not isinstance(messages, list) or len(messages) > MAX_PACKET_MESSAGES:
        raise ArtifactValidationError('Artifact packet exceeds its message limit.')
    ids, uids, refs = set(), set(), []
    for msg in messages:
        _fields(msg, ('id', 'uid', 'sender', 'type', 'timestamp', 'text', 'attachments', 'provenance'))
        _record_integer(msg['id'])
        _label_text(msg['uid'])
        _text(msg['sender'])
        _text(msg['type'])
        _text(msg['text'], empty=True)
        if msg['timestamp'] is not None:
            _number(msg['timestamp'])
        if not isinstance(msg['attachments'], list) or not isinstance(msg['provenance'], dict):
            raise ArtifactValidationError('Invalid artifact source message metadata.')
        if msg['id'] in ids or msg['uid'] in uids:
            raise ArtifactValidationError('Artifact source message IDs and UIDs must be unique.')
        ids.add(msg['id']); uids.add(msg['uid'])
        refs.append({'id': msg['id'], 'uid': msg['uid'], 'sha256': hashlib.sha256(_canonical(msg)).hexdigest()})
    raw = _canonical(packet)
    if len(raw) > MAX_PACKET_BYTES:
        raise ArtifactValidationError('Artifact packet exceeds 2 MiB; nothing was truncated.')
    return {'kind': packet['scope_kind'], 'packet_id': _hex(packet_id),
        'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw),
        'message_refs': refs, 'input_revision': revision}


def _audit(value):
    _fields(value, ('version', 'purpose', 'request_id', 'lineage_id', 'attempt_id', 'dispatch_id',
        'brief_id', 'original_channel', 'requester', 'producer', 'source_run', 'scope',
        'instruction', 'format', 'expected_parent', 'created_at'))
    if type(value['version']) is not int or value['version'] != 1 or value['purpose'] != 'artifact-v1':
        raise ArtifactValidationError('Unsupported artifact request version or purpose.')
    derived = request_ids(value['request_id'])
    _hex(value['lineage_id'])
    for name in ('attempt_id', 'dispatch_id', 'brief_id'):
        if value[name] != derived[name]:
            raise ArtifactValidationError('Artifact request identifiers do not match.')
    _channel(value['original_channel']); _label_text(value['requester'])
    _index_text(value['instruction'], 32 * 1024); _index_text(value['format'], 512)
    _number(value['created_at']); _source_run(value['source_run'])
    producer = value['producer']
    _fields(producer, ('name', 'identity_id', 'adapter', 'launch_attempt', 'launch_nonce',
        'fingerprint', 'requested_model', 'requested_model_reason', 'capabilities'))
    _label_text(producer['name']); _hex(producer['identity_id'])
    if producer['adapter'] not in ('cli', 'openai-compatible') or producer['capabilities'] != ['artifact-v1']:
        raise ArtifactValidationError('Artifact producer capability is invalid.')
    present = [producer[key] is not None for key in ('launch_attempt', 'launch_nonce', 'fingerprint')]
    if any(present) != all(present) or (producer['adapter'] == 'openai-compatible' and not all(present)):
        raise ArtifactValidationError('Artifact launch ownership is incomplete.')
    if all(present):
        _hex(producer['launch_attempt']); _hex(producer['launch_nonce']); _hex(producer['fingerprint'], 64)
    if producer['requested_model'] is None:
        _label_text(producer['requested_model_reason'])
    else:
        _label_text(producer['requested_model'])
        if producer['requested_model_reason'] is not None:
            raise ArtifactValidationError('Known requested model cannot have an absent-model reason.')
    scope = value['scope']
    _fields(scope, ('kind', 'packet_id', 'sha256', 'byte_length', 'message_refs', 'input_revision'))
    if scope['kind'] not in ('run_accepted_messages', 'selected_channel_messages') or scope['packet_id'] != derived['packet_id']:
        raise ArtifactValidationError('Artifact request packet reference is invalid.')
    _hex(scope['sha256'], 64); _record_integer(scope['byte_length'], 1, MAX_PACKET_BYTES)
    if scope['input_revision'] is not None:
        _hex(scope['input_revision'], 64)
    if not isinstance(scope['message_refs'], list) or len(scope['message_refs']) > MAX_PACKET_MESSAGES:
        raise ArtifactValidationError('Artifact request source references are invalid.')
    seen_ids, seen_uids = set(), set()
    for ref in scope['message_refs']:
        _fields(ref, ('id', 'uid', 'sha256'))
        _record_integer(ref['id']); _label_text(ref['uid']); _hex(ref['sha256'], 64)
        if ref['id'] in seen_ids or ref['uid'] in seen_uids:
            raise ArtifactValidationError('Artifact source references are duplicated.')
        seen_ids.add(ref['id']); seen_uids.add(ref['uid'])
    parent = value['expected_parent']
    if parent is not None:
        _fields(parent, ('version_id', 'sequence', 'sha256'))
        _hex(parent['version_id']); _record_integer(parent['sequence'], 1); _hex(parent['sha256'], 64)
    _canonical(value)
    return deepcopy(value)


def _audit_imported(value):
    """Validate the closed imported exception without changing local _audit."""
    if not isinstance(value, dict) or not isinstance(value.get('producer'), dict):
        raise ArtifactValidationError('Invalid imported artifact audit.')
    producer = value['producer']
    if (producer.get('adapter') not in ('cli', 'openai-compatible')
            or producer.get('capabilities') != []
            or any(producer.get(key) is not None for key in
                   ('launch_attempt', 'launch_nonce', 'fingerprint'))):
        raise ArtifactValidationError('Imported artifact authority must be absent.')
    # Reuse the unchanged common grammar through its existing CLI/null-ref
    # storage exception. This validation-only view is never stored or returned.
    local_view = deepcopy(value)
    local_view['producer'].update(adapter='cli', capabilities=['artifact-v1'])
    _audit(local_view)
    return deepcopy(value)


def _validate_imported(row):
    _fields(row, ('audit', 'channel', 'state', 'reason', 'updated_at', 'version_id',
                  'import_source'))
    if row['state'] != 'imported' or row['reason'] != 'imported':
        raise ArtifactValidationError('Imported artifact requests are terminal and read-only.')
    origin = row['import_source']
    _fields(origin, ('archive_id', 'original_state', 'original_reason'))
    if (not isinstance(origin['archive_id'], str)
            or not re.fullmatch(r'[A-Za-z0-9._-]{1,64}', origin['archive_id'])
            or not isinstance(origin['original_state'], str)
            or origin['original_state'] not in (LIVE | TERMINAL) - {'imported'}
            or (origin['original_reason'] is not None and not isinstance(origin['original_reason'], str))
            or origin['original_reason'] not in STATE_REASONS):
        raise ArtifactValidationError('Invalid imported artifact origin.')
    if (row['version_id'] is not None) != (origin['original_state'] == 'fulfilled'):
        raise ArtifactValidationError('Imported artifact version differs from its original state.')
    return _audit_imported(row['audit'])


def _observation(value, adapter):
    _fields(value, ('confirmed_model', 'confirmation_reason'))
    model, reason = value['confirmed_model'], value['confirmation_reason']
    if adapter == 'cli':
        valid = model is None and reason == 'cli_model_unverified'
    elif model is None:
        valid = reason == 'provider_did_not_report_model'
    else:
        _label_text(model)
        valid = reason == 'api_response'
    if not valid:
        raise ArtifactValidationError('Artifact model observation is invalid.')
    return deepcopy(value)


def _empty():
    return {'version': 2, 'lineages': {}, 'requests': {}, 'versions': {}}


def _empty_legacy_v1():
    return {'version': 1, 'lineages': {}, 'requests': {}, 'versions': {}, 'diagnostics': {},
            'dispatch_overflow': {}, 'store_overflow': None}


def _empty_diagnostics():
    return {'version': 1, 'diagnostics': {}, 'dispatch_overflow': {}, 'store_overflow': None}


def _diagnostic_id(key):
    return _uuid(_canonical(key).decode('utf-8'))


def _summary_id(dispatch_id):
    return _uuid('agentchattr:artifact-v1:overflow:' + (dispatch_id or 'store'))


def _path_key(path):
    value = str(path)
    if os.name == 'nt':
        if value.startswith('\\\\?\\UNC\\'):
            value = '\\\\' + value[8:]
        elif value.startswith('\\\\?\\'):
            value = value[4:]
    return os.path.normcase(os.path.normpath(value))


@dataclass(frozen=True)
class _ValidatedPacketBytes:
    packet_id: str
    raw: bytes
    scope_bytes: bytes
    audit_view_bytes: bytes


@dataclass
class _PacketValidationInvocation:
    owner: object
    root_key: tuple
    thread_id: int
    active: bool = True
    token: object = field(default_factory=object)
    entries: dict = field(default_factory=dict)
    issued: dict = field(default_factory=dict)


_PACKET_VALIDATION_INVOCATION = ContextVar('artifact_packet_validation_invocation', default=None)


def _packet_owner_key(owner):
    try:
        return (_path_key(owner.root.resolve()), _path_key(owner.path.resolve()))
    except (OSError, RuntimeError, ValueError):
        return None  # Evidence eligibility must not change the caller's error precedence.


@contextmanager
def _packet_validation_invocation(owner):
    state = _PacketValidationInvocation(owner, _packet_owner_key(owner), threading.get_ident())
    token = _PACKET_VALIDATION_INVOCATION.set(state)
    try:
        yield
    finally:
        state.active = False
        state.entries.clear()
        state.issued.clear()
        _PACKET_VALIDATION_INVOCATION.reset(token)


def _packet_invocation_for(owner):
    state = _PACKET_VALIDATION_INVOCATION.get()
    if (isinstance(state, _PacketValidationInvocation) and state.active and state.owner is owner
            and state.thread_id == threading.get_ident() and state.root_key is not None
            and state.root_key == _packet_owner_key(owner)):
        return state
    return None


def _packet_evidence(state, packet_id, raw):
    if state is None or not state.active:
        return None
    entry = state.entries.get(packet_id)
    if not isinstance(entry, _ValidatedPacketBytes):
        return None
    issued = state.issued.get(id(entry))
    if (type(issued) is not tuple or len(issued) != 5 or issued[0] is not entry or issued[4] is not state.token
            or entry.packet_id != packet_id or type(entry.raw) is not bytes
            or type(entry.scope_bytes) is not bytes or type(entry.audit_view_bytes) is not bytes
            or issued[1] is not entry.raw or issued[2] is not entry.scope_bytes
            or issued[3] is not entry.audit_view_bytes
            or len(entry.raw) != len(raw) or entry.raw != raw):
        return None
    return entry


class _ArtifactOwnedFiles:
    """Owned filesystem primitives; no metadata or policy state."""
    def _safe(self, path):
        if _path_key(path.resolve()) != _path_key(path.absolute()):
            raise ArtifactUnavailable('Artifact storage path is unavailable.')
        return path


    def _fingerprint(self):
        self._safe(self.path)
        try:
            stamp = self.path.stat()
            return stamp.st_mtime_ns, stamp.st_size
        except FileNotFoundError:
            return None


    def _fingerprint_quiet(self):
        try:
            return self._fingerprint()
        except (OSError, ArtifactUnavailable):
            return ('unreadable',)


    def _object_path(self, kind, identifier):
        _hex(identifier)
        if kind == 'packet':
            path = self.root / 'artifact_briefs' / 'packets' / (identifier + '.json')
        elif kind == 'version':
            path = self.root / 'artifacts' / 'objects' / (identifier + '.md')
        else:
            path = self.root / 'artifacts' / 'quarantine' / (identifier + '.txt')
        return self._safe(path)


    def _put_bytes(self, path, raw):
        temporary = None
        try:
            self._safe(path)
            with startup_lock(self._safe(path.with_suffix(path.suffix + '.lock')), time.monotonic() + 10):
                if path.exists():
                    with path.open('rb') as stream:
                        prior = stream.read(len(raw) + 1)
                    if prior != raw:
                        raise ArtifactConflict('Different bytes already occupy this immutable artifact object.')
                    return False
                path.parent.mkdir(parents=True, exist_ok=True)
                self._safe(path)
                temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
                with temporary.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(path)
            return True
        except (OSError, LaunchError):
            raise ArtifactUnavailable('Artifact object write did not complete.') from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    raise ArtifactUnavailable('Artifact temporary cleanup did not complete.') from None



class ArtifactDiagnosticStore(_ArtifactOwnedFiles):
    """Independent diagnostic ledger; never reads authoring or channel policy."""
    _diagnostic_id = staticmethod(_diagnostic_id)
    _summary_id = staticmethod(_summary_id)

    def __init__(self, data_dir, *, hold_unreadable=False, legacy_held=False):
        if type(hold_unreadable) is not bool or type(legacy_held) is not bool:
            raise ArtifactValidationError('Invalid diagnostic startup mode.')
        self.root = Path(data_dir).absolute()
        self.path = self.root / 'artifacts' / 'diagnostics.json'
        self._lock = threading.RLock()
        self._data = _empty_diagnostics()
        self._stamp = None
        self._invalid_stamp = object()
        self._held = None
        self._known = False
        self._legacy_held = legacy_held
        self._transaction_active = False
        if legacy_held:
            self._held = _LEGACY_GUIDANCE
            return
        try:
            self._data = self._load_diagnostics()
            self._stamp = self._fingerprint()
            self._known = True
        except (OSError, ArtifactUnavailable):
            self._held = _DIAGNOSTIC_GUIDANCE
            self._invalid_stamp = self._fingerprint_quiet()
            if not hold_unreadable:
                raise ArtifactDiagnosticsUnavailable() from None

    def _set_legacy_hold(self):
        with self._lock:
            self._legacy_held = True
            self._held = _LEGACY_GUIDANCE

    def _load_diagnostics(self):
        try:
            self._safe(self.path)
            before = self._fingerprint()
            if before is None:
                return _empty_diagnostics()
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ArtifactValidationError('Duplicate diagnostic fields.')
                    value[key] = item
                return value
            def nonfinite(_):
                raise ArtifactValidationError('Nonfinite diagnostic value.')
            with self.path.open('rb') as stream:
                raw = stream.read(MAX_DIAGNOSTIC_METADATA_BYTES + 1)
            if len(raw) > MAX_DIAGNOSTIC_METADATA_BYTES or raw.startswith(b'\xef\xbb\xbf'):
                raise ArtifactValidationError('Unsupported diagnostic encoding or size.')
            value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=nonfinite)
            pending = [(value, 1)]
            while pending:
                item, depth = pending.pop()
                if isinstance(item, list) or (isinstance(item, dict) and depth > 3):
                    raise ArtifactValidationError('Diagnostic nesting exceeds its schema.')
                if isinstance(item, dict):
                    pending.extend((child, depth + 1) for child in item.values())
            self._validate_diagnostics(value)
            if before != self._fingerprint():
                raise ArtifactValidationError('Diagnostic metadata changed while reading.')
            return value
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, ArtifactUnavailable):
            raise ArtifactDiagnosticsUnavailable() from None

    def _check_diagnostics(self):
        if self._legacy_held:
            raise ArtifactDiagnosticsUnavailable()
        stamp = self._fingerprint_quiet()
        if self._held is None and stamp == self._stamp:
            return
        if self._held is not None and stamp == self._invalid_stamp:
            raise ArtifactDiagnosticsUnavailable()
        try:
            if stamp is None and self._stamp is not None:
                raise ArtifactDiagnosticsUnavailable()
            value = self._load_diagnostics()
            if not self._known or value != self._data:
                raise ArtifactDiagnosticsUnavailable()
        except (OSError, ArtifactUnavailable):
            self._held = _DIAGNOSTIC_GUIDANCE
            self._invalid_stamp = stamp
            raise ArtifactDiagnosticsUnavailable() from None
        self._stamp, self._held = stamp, None

    @contextmanager
    def _transaction(self):
        with self._lock:
            if self._legacy_held:
                raise ArtifactDiagnosticsUnavailable()
            if self._transaction_active:
                yield
                return
            try:
                with startup_lock(self._safe(self.path.with_suffix('.json.lock')), time.monotonic() + 10):
                    self._transaction_active = True
                    try:
                        yield
                    finally:
                        self._transaction_active = False
            except (OSError, LaunchError):
                raise ArtifactDiagnosticsUnavailable() from None

    @staticmethod
    def _encoded(value):
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False).encode('utf-8')
        if len(raw) > MAX_DIAGNOSTIC_METADATA_BYTES:
            raise ArtifactDiagnosticsUnavailable()
        return raw

    def _persist_diagnostics(self, value):
        with self._transaction():
            self._check_diagnostics()
            self._validate_diagnostics(value)
            self._encoded(value)
            self._safe(self.path)
            try:
                atomic_json(self.path, value)
                stamp = self._fingerprint()
            except Exception:
                # Replacement may have landed, even if its final stat failed.
                self._held = _DIAGNOSTIC_GUIDANCE
                self._invalid_stamp = object()
                raise ArtifactDiagnosticsUnavailable() from None
            self._data, self._stamp = value, stamp
            self._known = True

    def record(self, request_id, attempt_id, dispatch_id, *, reason, content=None,
               actor_identity_id=None, attached_request_id=None, now=None):
        if request_id is not None:
            _hex(request_id)
        _hex(attempt_id); _hex(dispatch_id)
        if actor_identity_id is not None:
            _hex(actor_identity_id)
        if attached_request_id is not None:
            if (_hex(attached_request_id) != request_id
                    or request_ids(attached_request_id)['dispatch_id'] != dispatch_id):
                raise ArtifactValidationError('Diagnostic attachment differs from its dispatch.')
        if not isinstance(reason, str) or reason not in QUARANTINE_REASONS:
            raise ArtifactValidationError('Invalid artifact diagnostic reason.')
        if content is not None and not isinstance(content, str):
            raise ArtifactValidationError('Artifact diagnostic content must be text or null.')
        raw = b'' if content is None else content.encode('utf-8', errors='surrogatepass')
        retainable = content is not None and '\0' not in content
        try:
            raw.decode('utf-8')
        except UnicodeError:
            retainable = False
        key = {'request_id': request_id, 'attempt_id': attempt_id, 'dispatch_id': dispatch_id,
               'reason': reason, 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw),
               'actor_identity_id': actor_identity_id}
        identifier = self._diagnostic_id(key)
        try:
            with self._transaction():
                self._check_diagnostics()
                prior = self._data['diagnostics'].get(identifier)
                if prior is not None:
                    return deepcopy(prior)
                rows = self._data['diagnostics'].values()
                groups = {row['dispatch_id'] for row in rows}
                group_count = sum(row['dispatch_id'] == dispatch_id for row in rows)
                global_overflow = (group_count < MAX_DIAGNOSTICS_PER_DISPATCH and
                    (len(self._data['diagnostics']) >= MAX_DIAGNOSTIC_RECORDS
                     or (dispatch_id not in groups and len(groups) >= MAX_DIAGNOSTIC_DISPATCH_GROUPS)))
                value = deepcopy(self._data)
                if global_overflow or group_count >= MAX_DIAGNOSTICS_PER_DISPATCH:
                    prior = value['store_overflow'] if global_overflow else value['dispatch_overflow'].get(dispatch_id)
                    if prior is not None and prior['latest_diagnostic_id'] == identifier:
                        return deepcopy(prior)
                    summary = deepcopy(prior) if prior is not None else {
                        'id': self._summary_id(None if global_overflow else dispatch_id),
                        'kind': 'store_overflow' if global_overflow else 'dispatch_overflow',
                        'dispatch_id': None if global_overflow else dispatch_id, 'counter': 0}
                    summary.update(counter=min(summary['counter'] + 1, MAX_DIAGNOSTIC_COUNTER),
                        latest_diagnostic_id=identifier, latest_sha256=key['sha256'], latest_byte_count=len(raw),
                        latest_reason=reason, updated_at=_number(time.time() if now is None else now))
                    if global_overflow:
                        value['store_overflow'] = summary
                    else:
                        value['dispatch_overflow'][dispatch_id] = summary
                    self._persist_diagnostics(value)
                    return deepcopy(summary)
                files, total = self._body_inventory()
                retained = (retainable and len(raw) <= MAX_ARTIFACT_BYTES
                    and len(files) < MAX_QUARANTINE_OBJECTS and total + len(raw) <= MAX_QUARANTINE_BODY_BYTES)
                stamp = _number(time.time() if now is None else now)
                row = {'id': identifier, 'kind': 'quarantine', **key,
                       'received_at': stamp, 'updated_at': stamp, 'not_retained': not retained,
                       'body_object_id': identifier if retained else None, 'attached_request_id': attached_request_id}
                value['diagnostics'][identifier] = row
                # A refused candidate must not create even an orphan body.
                self._validate_diagnostics(value)
                self._encoded(value)
                if retained:
                    self._put_bytes(self._object_path('quarantine', identifier), raw)
                self._persist_diagnostics(value)
                return deepcopy(row)
        except (OSError, LaunchError, ArtifactUnavailable):
            # Body/lock failures do not imply a metadata replacement happened.
            # Only _persist_diagnostics marks commit uncertainty.
            raise ArtifactDiagnosticsUnavailable() from None

    def _attached_rows(self, request_id):
        rows = [deepcopy(row) for row in self._data['diagnostics'].values()
                if row['attached_request_id'] == request_id]
        return sorted(rows, key=lambda row: (row['received_at'], row['id']))

    def request_diagnostics(self, request_id):
        _hex(request_id)
        with self._lock:
            self._check_diagnostics()
            rows = self._attached_rows(request_id)
            summary = self._data['dispatch_overflow'].get(request_ids(request_id)['dispatch_id']) if rows else None
            return {'available': True, 'quarantine_ids': [row['id'] for row in rows],
                    'overflow_count': summary['counter'] if summary else 0, 'error': None}

    def report(self):
        try:
            with self._lock:
                self._check_diagnostics()
                rows = deepcopy(list(self._data['diagnostics'].values()))
                rows.extend(deepcopy(list(self._data['dispatch_overflow'].values())))
                if self._data['store_overflow'] is not None:
                    rows.append(deepcopy(self._data['store_overflow']))
                files, total = self._body_inventory()
                referenced = {row['body_object_id'] for row in self._data['diagnostics'].values() if row['body_object_id']}
                for path in files:
                    if path.stem not in referenced:
                        rows.append({'id': path.stem, 'kind': 'orphan_quarantine', 'updated_at': path.stat().st_mtime})
                return {'rows': rows, 'dispatch_group_count': len({row['dispatch_id'] for row in self._data['diagnostics'].values()}),
                        'detailed_count': len(self._data['diagnostics']), 'retained_body_bytes': total}
        except (OSError, ArtifactUnavailable):
            raise ArtifactDiagnosticsUnavailable() from None

    def _body_inventory(self):
        folder = self.root / 'artifacts' / 'quarantine'
        self._safe(folder)
        if not folder.exists():
            return [], 0
        try:
            with os.scandir(folder) as directory:
                entries = list(directory)
        except OSError:
            # Match Path.glob's enumeration-error behavior. Entry stat errors
            # below still propagate, and every matching path keeps its guard.
            return [], 0
        files = []
        total = 0
        suffix = os.path.normcase('.txt')
        for entry in entries:
            if not os.path.normcase(entry.name).endswith(suffix):
                continue
            path = Path(entry.path)
            self._safe(path)
            # Do not filter is_file: the previous scan also counted matching
            # directories. DirEntry.stat reuses enumeration metadata on Windows.
            total += entry.stat().st_size
            files.append(path)
        return files, total


    def _validate_diagnostics(self, value):
        _fields(value, _empty_diagnostics())
        if type(value['version']) is not int or value['version'] != 1:
            raise ArtifactValidationError('Unsupported diagnostic version.')
        if not isinstance(value['diagnostics'], dict) or not isinstance(value['dispatch_overflow'], dict):
            raise ArtifactValidationError('Diagnostic containers must be objects.')
        if len(value['diagnostics']) > MAX_DIAGNOSTIC_RECORDS:
            raise ArtifactValidationError('Artifact diagnostic count exceeds its bound.')
        groups = {}
        for identifier, row in value['diagnostics'].items():
            _fields(row, ('id', 'kind', 'request_id', 'attempt_id', 'dispatch_id', 'reason', 'sha256',
                'byte_count', 'actor_identity_id', 'received_at', 'updated_at', 'not_retained', 'body_object_id', 'attached_request_id'))
            if row['kind'] != 'quarantine' or _hex(identifier) != row['id']:
                raise ArtifactValidationError('Invalid artifact diagnostic identity.')
            if row['request_id'] is not None:
                _hex(row['request_id'])
            _hex(row['attempt_id']); _hex(row['dispatch_id']); _hex(row['sha256'], 64)
            if row['actor_identity_id'] is not None:
                _hex(row['actor_identity_id'])
            _record_integer(row['byte_count']); _number(row['received_at'])
            if row['updated_at'] != row['received_at'] or row['reason'] not in QUARANTINE_REASONS:
                raise ArtifactValidationError('Invalid artifact diagnostic metadata.')
            key = {name: row[name] for name in ('request_id', 'attempt_id', 'dispatch_id', 'reason',
                                               'sha256', 'byte_count', 'actor_identity_id')}
            if self._diagnostic_id(key) != identifier or type(row['not_retained']) is not bool:
                raise ArtifactValidationError('Artifact diagnostic key differs.')
            if row['body_object_id'] != (None if row['not_retained'] else identifier):
                raise ArtifactValidationError('Artifact diagnostic body reference differs.')
            attached = row['attached_request_id']
            if attached is not None and (_hex(attached) != row['request_id']
                    or request_ids(attached)['dispatch_id'] != row['dispatch_id']):
                raise ArtifactValidationError('Invalid diagnostic attachment.')
            groups[row['dispatch_id']] = groups.get(row['dispatch_id'], 0) + 1
        if len(groups) > MAX_DIAGNOSTIC_DISPATCH_GROUPS or any(n > MAX_DIAGNOSTICS_PER_DISPATCH for n in groups.values()):
            raise ArtifactValidationError('Artifact diagnostic group bound exceeded.')
        for dispatch_id, summary in value['dispatch_overflow'].items():
            if dispatch_id not in groups:
                raise ArtifactValidationError('Artifact overflow group is unknown.')
            self._validate_summary(summary, _hex(dispatch_id))
        if value['store_overflow'] is not None:
            self._validate_summary(value['store_overflow'], None)


    def _validate_summary(self, summary, dispatch_id):
        _fields(summary, ('id', 'kind', 'dispatch_id', 'counter', 'latest_diagnostic_id', 'latest_sha256',
                         'latest_byte_count', 'latest_reason', 'updated_at'))
        if (summary['id'] != self._summary_id(dispatch_id) or summary['dispatch_id'] != dispatch_id
                or summary['kind'] != ('dispatch_overflow' if dispatch_id else 'store_overflow')):
            raise ArtifactValidationError('Artifact overflow scope differs.')
        _record_integer(summary['counter'], 1, MAX_DIAGNOSTIC_COUNTER)
        _hex(summary['latest_diagnostic_id']); _hex(summary['latest_sha256'], 64)
        _record_integer(summary['latest_byte_count']); _number(summary['updated_at'])
        if summary['latest_reason'] not in QUARANTINE_REASONS:
            raise ArtifactValidationError('Invalid artifact overflow reason.')




class ArtifactStore(_ArtifactOwnedFiles):
    def __init__(self, data_dir, *, hold_unreadable=False):
        if type(hold_unreadable) is not bool:
            raise ArtifactValidationError('Invalid artifact startup mode.')
        self.root = Path(data_dir).absolute()
        self.path = self.root / 'artifacts' / 'index.json'
        self._lock = threading.RLock()
        self._data = _empty()
        self._stamp = None
        self._invalid_stamp = object()
        self._held = None
        self._known = False
        self._legacy_held = False
        self._object_errors = {}
        self._channel_policy_getter = self._closed_policy
        try:
            self._data = self._load_index()
            self._stamp = self._fingerprint()
            self._known = True
        except ArtifactUnavailable:
            self._held = _LEGACY_GUIDANCE if self._legacy_held else _AUTHORING_GUIDANCE
            self._invalid_stamp = self._fingerprint_quiet()
            if not hold_unreadable:
                raise
        self.diagnostic_store = ArtifactDiagnosticStore(self.root, hold_unreadable=True, legacy_held=self._legacy_held)

    @staticmethod
    def _closed_policy():
        raise ArtifactUnavailable('Artifact publication policy is not bound.')

    def bind_channel_policy(self, getter):
        if not callable(getter):
            raise ArtifactValidationError('Artifact policy getter must be callable.')
        with self._lock:
            self._channel_policy_getter = getter




    def _load_index(self):
        try:
            self._safe(self.path)
            before = self._fingerprint()
            if before is None:
                return _empty()
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ArtifactValidationError('Duplicate artifact fields.')
                    value[key] = item
                return value
            with self.path.open('rb') as stream:
                value = json.loads(stream.read().decode('utf-8'), object_pairs_hook=unique)
            if before != self._fingerprint():
                raise ArtifactValidationError('Artifact index changed during its read.')
            if (isinstance(value, dict) and type(value.get('version')) is int and value['version'] == 1
                    and set(value) == set(_empty_legacy_v1())):
                if value == _empty_legacy_v1():
                    return _empty()
                self._legacy_held = True
                raise ArtifactUnavailable(_LEGACY_GUIDANCE)
            self._validate_index(value)
            return value
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            raise ArtifactUnavailable('Saved artifact index is unavailable or malformed; nothing was reset.') from None

    def _check_index(self):
        if self._legacy_held:
            raise ArtifactUnavailable(_LEGACY_GUIDANCE)
        stamp = self._fingerprint_quiet()
        if self._held is None and stamp == self._stamp:
            return
        if self._held is not None and stamp == self._invalid_stamp:
            raise ArtifactUnavailable(self._held)
        try:
            value = self._load_index()
            if not self._known or value != self._data:
                raise ArtifactUnavailable('Saved artifacts changed; repair storage and restart.')
        except ArtifactUnavailable:
            self._held = _LEGACY_GUIDANCE if self._legacy_held else _AUTHORING_GUIDANCE
            self._invalid_stamp = stamp
            raise ArtifactUnavailable(self._held) from None
        self._stamp, self._held = stamp, None

    def _persist(self, value):
        if self._legacy_held:
            raise ArtifactUnavailable(_LEGACY_GUIDANCE)
        self._validate_index(value)
        try:
            with startup_lock(self._safe(self.path.with_suffix('.json.lock')), time.monotonic() + 10):
                self._check_index()
                self._safe(self.path)
                atomic_json(self.path, value)
                stamp = self._fingerprint()
        except (OSError, LaunchError, ArtifactUnavailable):
            raise ArtifactUnavailable(_LEGACY_GUIDANCE if self._legacy_held else 'Artifact index write did not complete.') from None
        self._data, self._stamp = value, stamp



    def _record_object_error(self, kind, identifier):
        referenced = (identifier in self._data['versions'] if kind == 'version' else
            any(row['audit']['scope']['packet_id'] == identifier for row in self._data['requests'].values()))
        if not referenced:
            return
        key = (kind, identifier)
        self._object_errors.pop(key, None)
        self._object_errors[key] = {'id': identifier, 'kind': 'object_error',
            'object_kind': kind, 'code': 'object_unavailable', 'updated_at': time.time()}
        if len(self._object_errors) > MAX_OBJECT_ERRORS:
            self._object_errors.pop(next(iter(self._object_errors)))

    def _read_object(self, kind, identifier, maximum):
        try:
            path = self._object_path(kind, identifier)
            with path.open('rb') as stream:
                raw = stream.read(maximum + 1)
            if len(raw) > maximum:
                raise ValueError('Oversized object')
            return raw
        except (OSError, ValueError, ArtifactUnavailable):
            self._record_object_error(kind, identifier)
            raise ArtifactUnavailable('Artifact object is unavailable.') from None

    def _read_validated_packet_content(self, packet_id, raw, *, need_packet=True):
        evidence = _packet_evidence(_packet_invocation_for(self), packet_id, raw)
        if evidence is not None:
            return (json.loads(raw) if need_packet else None,
                    json.loads(evidence.scope_bytes), json.loads(evidence.audit_view_bytes))
        packet = json.loads(raw)
        scope = _packet_scope(packet_id, packet)
        if _canonical(packet) != raw:
            raise ArtifactValidationError('Packet bytes changed.')
        view = {'channel': packet['channel'], 'source_run': packet['source_run']}
        return packet if need_packet else None, scope, view

    def _remember_validated_packet(self, packet_id, raw, scope, view):
        state = _packet_invocation_for(self)
        if state is None or _packet_evidence(state, packet_id, raw) is not None:
            return
        # Bypass storage at the bound; never evict another packet's proof.
        if packet_id not in state.entries and len(state.entries) >= 2:
            return
        total = sum(len(entry.raw) for key, entry in state.entries.items()
                    if key != packet_id and isinstance(entry, _ValidatedPacketBytes))
        if total + len(raw) > 2 * MAX_PACKET_BYTES:
            return
        entry = _ValidatedPacketBytes(packet_id, raw, canonical_utf8(scope), canonical_utf8(view))
        prior = state.entries.get(packet_id)
        if prior is not None:
            state.issued.pop(id(prior), None)
        state.entries[packet_id] = entry
        live = {id(value) for value in state.entries.values()}
        state.issued = {key: value for key, value in state.issued.items() if key in live}
        state.issued[id(entry)] = (entry, entry.raw, entry.scope_bytes, entry.audit_view_bytes, state.token)

    def _packet(self, packet_id, *, _need_packet=True):
        try:
            raw = self._read_object('packet', packet_id, MAX_PACKET_BYTES)
            packet, scope, view = self._read_validated_packet_content(packet_id, raw, need_packet=_need_packet)
            for row in self._data['requests'].values():
                audit = row['audit']
                if audit['scope']['packet_id'] == packet_id and (
                        audit['scope'] != scope or view['channel'] != audit['original_channel']
                        or view['source_run'] != audit['source_run']):
                    raise ArtifactValidationError('Packet no longer matches its request.')
        except (ValueError, TypeError, KeyError, UnicodeError, ArtifactUnavailable):
            self._record_object_error('packet', packet_id)
            raise ArtifactUnavailable('Artifact source packet is unavailable.') from None
        self._object_errors.pop(('packet', packet_id), None)
        self._remember_validated_packet(packet_id, raw, scope, view)
        return packet, scope

    def _request(self, request_id):
        _hex(request_id)
        row = self._data['requests'].get(request_id)
        if row is None:
            raise ArtifactConflict('Artifact request is unknown.')
        return row

    def _row(self, row):
        return deepcopy(row)

    def _parent(self, lineage):
        head = lineage['head_version_id']
        if head is None:
            return None
        value = self._data['versions'][head]
        return {'version_id': head, 'sequence': value['sequence'], 'sha256': value['sha256']}

    def put_packet(self, request_id, packet):
        if not isinstance(packet, dict):
            raise ArtifactValidationError('Artifact packet must be an object.')
        _channel(packet.get('channel'))
        _hex(request_id)
        return self._put_packet(request_id, packet)

    @channel_write(lambda self, args: [args['packet']['channel']])
    def _put_packet(self, request_id, packet):
        with self._lock:
            self._check_index()
            ids = request_ids(request_id)
            scope = _packet_scope(ids['packet_id'], packet)
            self._put_bytes(self._object_path('packet', ids['packet_id']), _canonical(packet))
            return deepcopy(scope)

    def get_packet(self, packet_id):
        _hex(packet_id)
        with self._lock:
            self._check_index()
            return self._packet(packet_id)[0]  # A fresh parse, never an owner/evidence-owned object.

    def export_lineage_ids(self):
        with self._lock:
            self._check_index()
            return tuple(sorted(self._data['lineages']))

    def export_metadata(self, lineage_id):
        _hex(lineage_id)
        with self._lock:
            self._check_index()
            lineage = self._data['lineages'].get(lineage_id)
            if lineage is None:
                raise ArtifactConflict('Artifact lineage is unknown.')
            requests = [row for _, row in sorted(self._data['requests'].items())
                        if row['audit']['lineage_id'] == lineage_id]
            return deepcopy({'lineage': lineage, 'requests': requests,
                'versions': [self._data['versions'][identifier] for identifier in lineage['version_ids']]})

    def read_archive_object(self, kind, object_id, *, sha256, byte_length):
        if kind not in ('version', 'packet'):
            raise ArtifactValidationError('Invalid artifact archive object kind.')
        _hex(object_id); _hex(sha256, 64)
        _record_integer(byte_length, 1, MAX_ARTIFACT_BYTES if kind == 'version' else MAX_PACKET_BYTES)
        with self._lock:
            self._check_index()
            if kind == 'version':
                metadata = self._data['versions'].get(object_id)
                if metadata is None:
                    raise ArtifactUnavailable('Artifact archive object is unavailable.')
                reference = metadata
            else:
                reference = next((row['audit']['scope'] for row in self._data['requests'].values()
                    if row['audit']['scope']['packet_id'] == object_id), None)
                if reference is None:
                    raise ArtifactUnavailable('Artifact archive object is unavailable.')
            if reference['sha256'] != sha256 or reference['byte_length'] != byte_length:
                raise ArtifactUnavailable('Artifact archive object is unavailable.')
            if kind == 'packet':
                raw = _canonical(self._packet(object_id)[0])
            else:
                saved = self.get_version(object_id)
                raw = saved['markdown'].encode('utf-8')
            if len(raw) != byte_length or hashlib.sha256(raw).hexdigest() != sha256:
                self._record_object_error(kind, object_id)
                raise ArtifactUnavailable('Artifact archive object is unavailable.')
            return raw

    def _import_metadata(self, portable):
        """Pure portable-to-imported projection, with no disk or policy access."""
        _fields(portable, ('lineage_id', 'channel', 'updated_at', 'head_version_id', 'requests', 'versions'))
        lineage_id = _hex(portable['lineage_id'])
        channel = _channel(portable['channel'])
        _number(portable['updated_at'])
        if not isinstance(portable['requests'], list) or not portable['requests']:
            raise ArtifactValidationError('Artifact import lineage must contain requests.')
        if not isinstance(portable['versions'], list):
            raise ArtifactValidationError('Artifact import versions must be an array.')
        _canonical(portable)
        value = _empty()
        for row in portable['requests']:
            _fields(row, ('request_id', 'original_channel', 'requester', 'producer', 'source_run',
                'scope', 'instruction', 'format', 'expected_parent', 'created_at', 'updated_at', 'import_source'))
            producer = row['producer']
            _fields(producer, ('name', 'identity_id', 'adapter', 'requested_model', 'requested_model_reason'))
            request_id = _hex(row['request_id'])
            if request_id in value['requests']:
                raise ArtifactValidationError('Artifact imported request is duplicated.')
            ids = request_ids(request_id)
            audit = {'version': 1, 'purpose': 'artifact-v1', 'request_id': request_id,
                'lineage_id': lineage_id, 'attempt_id': ids['attempt_id'], 'dispatch_id': ids['dispatch_id'],
                'brief_id': ids['brief_id'], **{key: deepcopy(row[key]) for key in
                    ('original_channel', 'requester', 'source_run', 'scope', 'instruction', 'format',
                     'expected_parent', 'created_at')},
                'producer': {**deepcopy(producer), 'launch_attempt': None, 'launch_nonce': None,
                    'fingerprint': None, 'capabilities': []}}
            value['requests'][request_id] = {'audit': audit, 'channel': channel, 'state': 'imported',
                'reason': 'imported', 'updated_at': row['updated_at'], 'version_id': None,
                'import_source': deepcopy(row['import_source'])}
        version_ids = []
        for row in portable['versions']:
            _fields(row, ('version_id', 'request_id', 'sequence', 'parent_version_id', 'sha256',
                          'byte_length', 'created_at', 'observation'))
            version_id = _hex(row['version_id'])
            request = value['requests'].get(row['request_id'])
            if request is None or request['version_id'] is not None or version_id in value['versions']:
                raise ArtifactValidationError('Artifact imported version request is invalid or duplicated.')
            request['version_id'] = version_id
            audit = request['audit']
            provenance = {key: deepcopy(audit[key]) for key in
                ('requester', 'producer', 'source_run', 'scope', 'instruction', 'format')}
            provenance.update(input_revision=audit['scope']['input_revision'], observation=deepcopy(row['observation']))
            value['versions'][version_id] = {'id': version_id, 'lineage_id': lineage_id, 'channel': channel,
                'attempt_id': audit['attempt_id'], 'dispatch_id': audit['dispatch_id'], 'provenance': provenance,
                **{key: deepcopy(row[key]) for key in ('request_id', 'sequence', 'parent_version_id',
                    'sha256', 'byte_length', 'created_at')}}
            version_ids.append(version_id)
        value['lineages'][lineage_id] = {'id': lineage_id, 'channel': channel,
            'head_version_id': portable['head_version_id'], 'pending_request_id': None,
            'version_ids': version_ids, 'updated_at': portable['updated_at']}
        self._validate_index(value)
        return value

    @staticmethod
    def _import_references(value):
        references = {('version', key): row for key, row in value['versions'].items()}
        references.update({('packet', row['audit']['scope']['packet_id']): row['audit']['scope']
                           for row in value['requests'].values()})
        return references

    def prepare_import_lineage(self, portable_lineage, objects):
        try:
            value = self._import_metadata(portable_lineage)
            references = self._import_references(value)
            if not isinstance(objects, dict) or set(objects) != set(references):
                raise ArtifactValidationError('Artifact import object set differs from its lineage.')
            # Validate every object before staging any of them. All full-body
            # parsing/hashing and immutable writes happen outside the boundary.
            for (kind, identifier), reference in references.items():
                raw = objects[(kind, identifier)]
                if (type(raw) is not bytes or len(raw) != reference['byte_length']
                        or hashlib.sha256(raw).hexdigest() != reference['sha256']):
                    raise ArtifactValidationError('Artifact import object bytes differ from metadata.')
                if kind == 'version':
                    _text(raw.decode('utf-8'), MAX_ARTIFACT_BYTES)
                else:
                    packet = json.loads(raw)
                    scope = _packet_scope(identifier, packet)
                    if scope != reference or _canonical(packet) != raw:
                        raise ArtifactValidationError('Artifact import source packet differs.')
                    audit = next(row['audit'] for row in value['requests'].values()
                                 if row['audit']['scope']['packet_id'] == identifier)
                    if packet['channel'] != audit['original_channel'] or packet['source_run'] != audit['source_run']:
                        raise ArtifactValidationError('Artifact import packet authority differs.')
        except ArtifactValidationError:
            raise
        except (KeyError, TypeError, UnicodeError, RecursionError, ValueError):
            raise ArtifactValidationError('Artifact import lineage is malformed.') from None
        with self._lock:
            self._check_index()
            result = self._classify_import(value)
            if result is not None:
                local_refs = self._import_references(self._data)
                if result['reason'] == 'uid_collision' and any(
                        key in local_refs and (row['sha256'], row['byte_length']) !=
                        (local_refs[key]['sha256'], local_refs[key]['byte_length'])
                        for key, row in references.items()):
                    raise ArtifactImportCollision('uid_collision', result['collision_kinds'])
                return _PreparedLineage(_path_key(self.root), _canonical(value), (), skipped=True)
        stamps, created_objects = [], []
        for (kind, identifier), reference in sorted(references.items()):
            path = self._object_path(kind, identifier)
            try:
                if self._put_bytes(path, objects[(kind, identifier)]):
                    created_objects.append((kind, identifier, len(objects[(kind, identifier)])))
                stat = path.stat()
            except ArtifactConflict:
                # The object file lock has already been released. Never nest
                # a metadata owner lock inside the immutable-file lock.
                with self._lock:
                    self._check_index()
                    current = self._classify_import(value)
                raise ArtifactImportCollision('uid_collision' if current else 'object_conflict',
                    current['collision_kinds'] if current else [kind], created_objects=tuple(created_objects)) from None
            except (OSError, ArtifactUnavailable):
                error = ArtifactUnavailable('Artifact import staging is unavailable.')
                error._created_objects = None
                error._orphan_reason = 'staging_io_unconfirmed'
                raise error from None
            stamps.append((kind, identifier, stat.st_mtime_ns, stat.st_size))
        return _PreparedLineage(_path_key(self.root), _canonical(value), tuple(stamps),
                                created_objects=tuple(created_objects))

    def _import_orphans(self, created_objects):
        """Private observation: only objects this invocation actually created."""
        if created_objects is None:
            return None
        if not created_objects:
            return {'objects': 0, 'bytes': 0}
        with self._lock:
            try:
                self._check_index()
                references = self._import_references(self._data)
                count, size = 0, 0
                for kind, identifier, _ in set(created_objects):
                    if (kind, identifier) in references:
                        continue
                    try:
                        actual = self._object_path(kind, identifier).stat().st_size
                    except FileNotFoundError:
                        continue
                    count += 1
                    size += actual
                return {'objects': count, 'bytes': size}
            except (OSError, ArtifactUnavailable):
                return None

    def _prepared_import(self, prepared):
        if not isinstance(prepared, _PreparedLineage) or prepared.root != _path_key(self.root):
            raise ArtifactValidationError('Artifact import plan belongs to another store.')
        try:
            for kind, identifier, modified, size in prepared.objects:
                stat = self._object_path(kind, identifier).stat()
                if (stat.st_mtime_ns, stat.st_size) != (modified, size):
                    raise ArtifactUnavailable('Artifact import staged object changed.')
            return json.loads(prepared.metadata)
        except OSError:
            raise ArtifactUnavailable('Artifact import staged object is unavailable.') from None

    @staticmethod
    def _import_result(reason=None, *, versions=0, requests=0, collision_kinds=()):
        return {'status': 'created' if reason is None else 'skipped', 'reason': reason,
            'collision_kinds': sorted(collision_kinds), 'created_versions': versions, 'created_requests': requests}

    def _classify_import(self, value):
        incoming = {'lineage': set(value['lineages']), 'request': set(value['requests']),
            'version': set(value['versions']),
            'packet': {row['audit']['scope']['packet_id'] for row in value['requests'].values()},
            'dispatch': {row['audit']['dispatch_id'] for row in value['requests'].values()}}
        local = {'lineage': set(self._data['lineages']), 'request': set(self._data['requests']),
            'version': set(self._data['versions']),
            'packet': {row['audit']['scope']['packet_id'] for row in self._data['requests'].values()},
            'dispatch': {row['audit']['dispatch_id'] for row in self._data['requests'].values()}}
        collisions = [kind for kind in incoming if incoming[kind] & local[kind]]
        if not collisions:
            return None
        if (all(incoming[kind] <= local[kind] for kind in incoming)
                and all(self._data['requests'][key]['audit']['lineage_id'] == row['audit']['lineage_id']
                        for key, row in value['requests'].items())
                and all(self._data['versions'][key]['lineage_id'] == row['lineage_id']
                        for key, row in value['versions'].items())):
            local_refs = self._import_references(self._data)
            if all((row['sha256'], row['byte_length']) ==
                   (local_refs[key]['sha256'], local_refs[key]['byte_length'])
                   for key, row in self._import_references(value).items()):
                return self._import_result('duplicate')
        return self._import_result('uid_collision', collision_kinds=collisions)

    def classify_import_lineage(self, prepared):
        with self._lock:
            self._check_index()
            result = self._classify_import(self._prepared_import(prepared))
            if prepared.skipped and result is None:
                raise ArtifactConflict('Artifact import classification changed; prepare again.')
            return result

    @channel_write(lambda self, args: [_channel(args['channel'])])
    def import_lineage(self, prepared, *, channel):
        with self._lock:
            self._check_index()
            imported = self._prepared_import(prepared)
            result = self._classify_import(imported)
            if result is not None:
                return result
            if prepared.skipped:
                raise ArtifactConflict('Artifact import classification changed; prepare again.')
            value = deepcopy(self._data)
            for group in ('lineages', 'requests', 'versions'):
                for identifier, row in imported[group].items():
                    row['channel'] = channel
                    value[group][identifier] = row
            self._persist(value)
            return self._import_result(versions=len(imported['versions']), requests=len(imported['requests']))

    def reserve_request(self, audit, request_id):
        audit = _audit(audit)
        if audit['request_id'] != _hex(request_id):
            raise ArtifactValidationError('Artifact request identifier differs.')
        with self._lock:
            self._check_index()
            existing = self._data['requests'].get(request_id)
            if existing is not None:
                first = {k: v for k, v in existing['audit'].items() if k != 'created_at'}
                repeat = {k: v for k, v in audit.items() if k != 'created_at'}
                if first != repeat:
                    raise ArtifactConflict('This request ID already has a different immutable intent.')
                return self._row(existing)
        return self._reserve_new(audit, request_id)

    @channel_write(lambda self, args: [args['audit']['original_channel']])
    def _reserve_new(self, audit, request_id):
        with self._lock:
            self._check_index()
            if request_id in self._data['requests']:
                return self.reserve_request(audit, request_id)
            packet, scope = self._packet(audit['scope']['packet_id'])
            if (scope != audit['scope'] or packet['channel'] != audit['original_channel']
                    or packet['source_run'] != audit['source_run']):
                raise ArtifactConflict('Artifact request does not match its frozen packet.')
            lineage_id = audit['lineage_id']
            lineage = self._data['lineages'].get(lineage_id)
            if lineage and (lineage['pending_request_id'] is not None or self._parent(lineage) != audit['expected_parent']):
                raise ArtifactConflict('Artifact lineage changed or already has pending work.')
            if lineage is None and audit['expected_parent'] is not None:
                raise ArtifactConflict('Artifact parent version is unknown.')
            if lineage and lineage['channel'] != audit['original_channel']:
                raise ArtifactConflict('Artifact request channel differs from its lineage.')
            value = deepcopy(self._data)
            if lineage is None:
                value['lineages'][lineage_id] = {'id': lineage_id, 'channel': audit['original_channel'],
                    'head_version_id': None, 'pending_request_id': None, 'version_ids': [], 'updated_at': audit['created_at']}
            value['lineages'][lineage_id]['pending_request_id'] = request_id
            value['lineages'][lineage_id]['updated_at'] = audit['created_at']
            row = {'audit': deepcopy(audit), 'channel': audit['original_channel'], 'state': 'prepared',
                'reason': None, 'updated_at': audit['created_at'], 'version_id': None}
            value['requests'][request_id] = row
            self._persist(value)
            return self._row(row)

    def get_request(self, request_id):
        _hex(request_id)
        with self._lock:
            self._check_index()
            row = self._data['requests'].get(request_id)
            return self._row(row) if row is not None else None

    def get_request_by_dispatch(self, dispatch_id):
        _hex(dispatch_id)
        with self._lock:
            self._check_index()
            return next((self._row(row) for row in self._data['requests'].values()
                         if row['audit']['dispatch_id'] == dispatch_id), None)

    def set_attempt_state(self, request_id, attempt_id, expected_state, change, *, now=None):
        _hex(attempt_id)
        _fields(change, ('state', 'reason'))
        if (not isinstance(expected_state, str) or expected_state not in LIVE | TERMINAL
                or not isinstance(change['state'], str) or change['state'] not in LIVE | TERMINAL
                or (change['reason'] is not None and not isinstance(change['reason'], str))
                or change['reason'] not in STATE_REASONS):
            raise ArtifactValidationError('Invalid artifact state change.')
        with self._lock:
            self._check_index()
            row = self._request(request_id)
            if row['audit']['attempt_id'] != attempt_id:
                raise ArtifactConflict('Artifact attempt differs.')
            if row['state'] == change['state'] and row['reason'] == change['reason']:
                return self._row(row)
            if row['state'] != expected_state or row['state'] in TERMINAL:
                raise ArtifactConflict('Artifact request state changed or is terminal.')
            allowed = {'prepared': {'prepared', 'queued', 'active', 'failed', 'cancelled', 'quarantined'},
                'queued': {'queued', 'active', 'failed', 'cancelled', 'quarantined'},
                'active': {'active', 'failed', 'cancelled', 'quarantined'}}
            if change['state'] not in allowed[row['state']]:
                raise ArtifactConflict('Artifact state transition is not allowed.')
            if change['state'] in ('queued', 'active'):
                self._packet(row['audit']['scope']['packet_id'], _need_packet=False)
            stamp = _number(time.time() if now is None else now)
            value = deepcopy(self._data)
            target = value['requests'][request_id]
            target.update(change, updated_at=stamp)
            lineage = value['lineages'][row['audit']['lineage_id']]
            lineage['updated_at'] = stamp
            if change['state'] in TERMINAL:
                lineage['pending_request_id'] = None
            self._persist(value)
            return self._row(target)

    def commit_version(self, request_id, attempt_id, dispatch_id, markdown, observation, *, now=None):
        raw = _text(markdown, MAX_ARTIFACT_BYTES)
        _hex(attempt_id); _hex(dispatch_id)
        with self._lock:
            self._check_index()
            row = self._request(request_id)
            if row['audit']['attempt_id'] != attempt_id or row['audit']['dispatch_id'] != dispatch_id:
                raise ArtifactConflict('Artifact submission attempt or dispatch differs.')
            _observation(observation, row['audit']['producer']['adapter'])
            if row['state'] == 'fulfilled':
                old = self.get_version(row['version_id'])
                if old is None or old['metadata']['request_id'] != request_id:
                    raise ArtifactUnavailable('Artifact version reference is unavailable.')
                if old['markdown'] != markdown:
                    raise ArtifactConflict('Different content already occupies this artifact dispatch.')
                return old['metadata']
        return self._commit_new(request_id, attempt_id, dispatch_id, raw, observation, now)

    def _commit_channels(self, request_id):
        with self._lock:
            self._check_index()
            return [self._request(request_id)['channel']]

    @channel_write(lambda self, args: self._commit_channels(args['request_id']))
    def _commit_new(self, request_id, attempt_id, dispatch_id, raw, observation, now):
        with self._lock:
            self._check_index()
            row = self._request(request_id)
            if row['state'] == 'fulfilled':
                return self.commit_version(request_id, attempt_id, dispatch_id, raw.decode('utf-8'), observation, now=now)
            audit = row['audit']
            lineage = self._data['lineages'][audit['lineage_id']]
            if (row['state'] not in ('queued', 'active') or lineage['pending_request_id'] != request_id
                    or self._parent(lineage) != audit['expected_parent']):
                raise ArtifactConflict('Artifact request is not live or its parent changed.')
            self._packet(audit['scope']['packet_id'], _need_packet=False)
            stamp = _number(time.time() if now is None else now)
            version_id = request_ids(request_id)['version_id']
            metadata = {'id': version_id, 'lineage_id': audit['lineage_id'],
                'sequence': len(lineage['version_ids']) + 1, 'channel': row['channel'],
                'parent_version_id': lineage['head_version_id'], 'request_id': request_id,
                'attempt_id': attempt_id, 'dispatch_id': dispatch_id, 'sha256': hashlib.sha256(raw).hexdigest(),
                'byte_length': len(raw), 'created_at': stamp,
                'provenance': {'requester': audit['requester'], 'producer': deepcopy(audit['producer']),
                    'observation': deepcopy(observation), 'source_run': deepcopy(audit['source_run']),
                    'scope': deepcopy(audit['scope']), 'input_revision': audit['scope']['input_revision'],
                    'instruction': audit['instruction'], 'format': audit['format']}}
            self._put_bytes(self._object_path('version', version_id), raw)
            value = deepcopy(self._data)
            value['versions'][version_id] = metadata
            target = value['lineages'][audit['lineage_id']]
            target['version_ids'].append(version_id)
            target.update(head_version_id=version_id, pending_request_id=None, updated_at=stamp)
            value['requests'][request_id].update(state='fulfilled', reason=None, version_id=version_id, updated_at=stamp)
            self._persist(value)
            return deepcopy(metadata)

    def get_version(self, version_id):
        _hex(version_id)
        with self._lock:
            self._check_index()
            metadata = self._data['versions'].get(version_id)
            if metadata is None:
                return None
            raw = self._read_object('version', version_id, MAX_ARTIFACT_BYTES)
            try:
                text = raw.decode('utf-8')
                _text(text, MAX_ARTIFACT_BYTES)
                if len(raw) != metadata['byte_length'] or hashlib.sha256(raw).hexdigest() != metadata['sha256']:
                    raise ValueError('Artifact bytes changed.')
            except (ValueError, UnicodeError):
                self._record_object_error('version', version_id)
                raise ArtifactUnavailable('Artifact version object is unavailable.') from None
            self._object_errors.pop(('version', version_id), None)
            return {'metadata': deepcopy(metadata), 'markdown': text}

    @staticmethod
    def _page(rows, limit, offset=0):
        _integer(limit, 1, 100); _integer(offset)
        selected = rows[offset:offset + limit]
        return {'rows': deepcopy(selected), 'count': len(rows), 'truncated': offset + len(selected) < len(rows)}

    def _pending_row(self, row):
        audit = row['audit']
        return {**{key: audit[key] for key in ('request_id', 'lineage_id', 'attempt_id', 'dispatch_id')},
            'state': row['state'], 'reason': row['reason'],
            'source_run_id': audit['source_run']['run_id'] if audit['source_run'] else None}

    def _lineage_row(self, lineage):
        head = self._data['versions'].get(lineage['head_version_id'])
        summary = None if head is None else {key: head[key] for key in
            ('id', 'sequence', 'sha256', 'byte_length', 'created_at')}
        pending = self._data['requests'].get(lineage['pending_request_id'])
        return {'id': lineage['id'], 'channel': lineage['channel'], 'updated_at': lineage['updated_at'],
            'head_version_id': lineage['head_version_id'], 'head': summary,
            'version_count': len(lineage['version_ids']), 'pending_request_id': lineage['pending_request_id'],
            'pending_request': self._pending_row(pending) if pending else None}

    def list_lineages(self, channel=None, *, limit=100, offset=0):
        if channel is not None:
            _channel(channel)
        with self._lock:
            self._check_index()
            rows = [self._lineage_row(row) for row in self._data['lineages'].values()
                    if channel is None or row['channel'] == channel]
            rows.sort(key=lambda row: (-row['updated_at'], row['id']))
            return self._page(rows, limit, offset)

    def list_versions(self, lineage_id, *, limit=100, offset=0):
        _hex(lineage_id)
        with self._lock:
            self._check_index()
            lineage = self._data['lineages'].get(lineage_id)
            rows = [self._data['versions'][identifier] for identifier in reversed(lineage['version_ids'])] if lineage else []
            return self._page(rows, limit, offset)

    def pending(self, channel):
        _channel(channel)
        with self._lock:
            self._check_index()
            rows = [self._pending_row(row) for row in self._data['requests'].values()
                    if row['channel'] == channel and row['state'] in LIVE]
            return deepcopy(sorted(rows, key=lambda row: row['request_id']))

    def channel_names(self):
        with self._lock:
            self._check_index()
            return {row['channel'] for group in ('lineages', 'requests', 'versions')
                    for row in self._data[group].values()}

    def lifecycle_scope(self, channel):
        _channel(channel)
        with self._lock:
            self._check_index()
            lineages = [row for row in self._data['lineages'].values() if row['channel'] == channel]
            requests = sorted((row for row in self._data['requests'].values() if row['channel'] == channel),
                              key=lambda row: row['audit']['request_id'])
            return deepcopy({'lineages': [{'id': row['id'], 'updated_at': row['updated_at'],
                    'head_version_id': row['head_version_id'],
                    'head_sha256': self._data['versions'][row['head_version_id']]['sha256']
                        if row['head_version_id'] else None} for row in sorted(lineages, key=lambda row: row['id'])],
                'requests': [{'request_id': row['audit']['request_id'], 'dispatch_id': row['audit']['dispatch_id'],
                    'state': row['state'], 'reason': row['reason'], 'updated_at': row['updated_at'],
                    'version_id': row['version_id']} for row in requests],
                'pending': self.pending(channel), 'version_count': sum(len(row['version_ids']) for row in lineages),
                'request_count': len(requests),
                'source_bytes': sum(row['audit']['scope']['byte_length'] for row in requests)})

    def retained_metadata(self, channel, *, limit=100):
        return self.list_lineages(channel, limit=limit)

    def rename_channel(self, old_name, new_name):
        _channel(old_name); _channel(new_name)
        if old_name == new_name:
            raise ArtifactValidationError('Artifact rename names must differ.')
        with self._lock:
            self._check_index()
            names = self.channel_names()
            if old_name not in names:
                return []
            if new_name in names:
                raise ArtifactConflict('Artifact rename destination is occupied.')
            value = deepcopy(self._data)
            moved = []
            for group in ('lineages', 'requests', 'versions'):
                for row in value[group].values():
                    if row['channel'] == old_name:
                        row['channel'] = new_name
                        if group == 'lineages':
                            moved.append(row['id'])
            self._persist(value)
            return moved

    @staticmethod
    def _diagnostic_id(key):
        return _diagnostic_id(key)

    @staticmethod
    def _summary_id(dispatch_id):
        return _summary_id(dispatch_id)




    def _validate_index(self, value):
        _fields(value, _empty())
        if type(value['version']) is not int or value['version'] != 2:
            raise ArtifactValidationError('Unsupported artifact index version.')
        _canonical(value)
        for group in ('lineages', 'requests', 'versions'):
            if not isinstance(value[group], dict):
                raise ArtifactValidationError('Artifact index containers must be objects.')
        dispatches = set()
        live = {}
        for identifier, row in value['requests'].items():
            if isinstance(row, dict) and row.get('state') == 'imported':
                audit = _validate_imported(row)
            else:
                _fields(row, ('audit', 'channel', 'state', 'reason', 'updated_at', 'version_id'))
                audit = _audit(row['audit'])
            if _hex(identifier) != audit['request_id'] or audit['dispatch_id'] in dispatches:
                raise ArtifactValidationError('Artifact request identity is duplicated or inconsistent.')
            dispatches.add(audit['dispatch_id'])
            _channel(row['channel']); _number(row['updated_at'])
            if row['state'] not in LIVE | TERMINAL or row['reason'] not in STATE_REASONS:
                raise ArtifactValidationError('Invalid saved artifact state.')
            if row['version_id'] is not None:
                _hex(row['version_id'])
                metadata = value['versions'].get(row['version_id'])
                if metadata is None or metadata.get('request_id') != identifier:
                    raise ArtifactValidationError('Artifact request version reference differs.')
            if row['state'] == 'fulfilled' and row['version_id'] is None:
                raise ArtifactValidationError('Completed artifact has no version.')
            if row['state'] not in ('fulfilled', 'imported') and row['version_id'] is not None:
                raise ArtifactValidationError('Unfulfilled artifact names a version.')
            if row['state'] in LIVE:
                if audit['lineage_id'] in live:
                    raise ArtifactValidationError('Multiple live requests occupy an artifact lineage.')
                live[audit['lineage_id']] = identifier
            lineage = value['lineages'].get(audit['lineage_id'])
            if lineage is None or lineage.get('channel') != row['channel']:
                raise ArtifactValidationError('Artifact request lineage is unavailable.')
            parent = audit['expected_parent']
            if row['state'] == 'imported' and parent is not None:
                metadata = value['versions'].get(parent['version_id'])
                if (metadata is None or metadata['lineage_id'] != audit['lineage_id']
                        or metadata['sequence'] != parent['sequence'] or metadata['sha256'] != parent['sha256']):
                    raise ArtifactValidationError('Imported artifact request parent differs from its lineage.')
        used_versions = set()
        for identifier, lineage in value['lineages'].items():
            _fields(lineage, ('id', 'channel', 'head_version_id', 'pending_request_id', 'version_ids', 'updated_at'))
            if _hex(identifier) != lineage['id']:
                raise ArtifactValidationError('Artifact lineage identity differs.')
            _channel(lineage['channel']); _number(lineage['updated_at'])
            versions = lineage['version_ids']
            if not isinstance(versions, list) or len(set(versions)) != len(versions):
                raise ArtifactValidationError('Artifact versions must be unique and ordered.')
            if lineage['head_version_id'] != (versions[-1] if versions else None):
                raise ArtifactValidationError('Artifact head differs from its versions.')
            if lineage['pending_request_id'] != live.get(identifier):
                raise ArtifactValidationError('Artifact pending reservation differs.')
            parent = None
            expected_parent = None
            for sequence, version_id in enumerate(versions, 1):
                metadata = value['versions'].get(_hex(version_id))
                if metadata is None or version_id in used_versions:
                    raise ArtifactValidationError('Artifact version index is inconsistent.')
                used_versions.add(version_id)
                self._validate_version(metadata, value['requests'])
                if value['requests'][metadata['request_id']]['audit']['expected_parent'] != expected_parent:
                    raise ArtifactValidationError('Artifact request parent metadata differs.')
                if (metadata['id'] != version_id or metadata['lineage_id'] != identifier
                        or metadata['channel'] != lineage['channel'] or metadata['sequence'] != sequence
                        or metadata['parent_version_id'] != parent):
                    raise ArtifactValidationError('Artifact version chain is inconsistent.')
                parent = version_id
                expected_parent = {'version_id': version_id, 'sequence': metadata['sequence'],
                                   'sha256': metadata['sha256']}
            pending_id = lineage['pending_request_id']
            if pending_id is not None and value['requests'][pending_id]['audit']['expected_parent'] != expected_parent:
                raise ArtifactValidationError('Artifact pending parent differs from the current head.')
        if used_versions != set(value['versions']):
            raise ArtifactValidationError('Unindexed artifact version metadata exists.')

    def _validate_version(self, metadata, requests):
        _fields(metadata, ('id', 'lineage_id', 'sequence', 'channel', 'parent_version_id', 'request_id',
            'attempt_id', 'dispatch_id', 'sha256', 'byte_length', 'created_at', 'provenance'))
        _hex(metadata['id']); _hex(metadata['lineage_id']); _hex(metadata['sha256'], 64)
        _record_integer(metadata['sequence'], 1); _record_integer(metadata['byte_length'], 1, MAX_ARTIFACT_BYTES)
        _channel(metadata['channel']); _number(metadata['created_at'])
        request = requests.get(metadata['request_id'])
        if request is None or request['version_id'] != metadata['id'] or request['state'] not in ('fulfilled', 'imported'):
            raise ArtifactValidationError('Artifact version request is unavailable.')
        audit = request['audit']
        if (metadata['id'] != request_ids(audit['request_id'])['version_id']
                or metadata['lineage_id'] != audit['lineage_id']
                or metadata['attempt_id'] != audit['attempt_id'] or metadata['dispatch_id'] != audit['dispatch_id']):
            raise ArtifactValidationError('Artifact version authority differs.')
        parent = audit['expected_parent']
        if metadata['parent_version_id'] != (parent['version_id'] if parent else None):
            raise ArtifactValidationError('Artifact version parent differs from its request.')
        provenance = metadata['provenance']
        _fields(provenance, ('requester', 'producer', 'observation', 'source_run', 'scope',
                            'input_revision', 'instruction', 'format'))
        for key in ('requester', 'producer', 'source_run', 'scope', 'instruction', 'format'):
            if provenance[key] != audit[key]:
                raise ArtifactValidationError('Artifact provenance differs from its frozen audit.')
        if provenance['input_revision'] != audit['scope']['input_revision']:
            raise ArtifactValidationError('Artifact provenance input differs.')
        _observation(provenance['observation'], audit['producer']['adapter'])



    def _check_diagnostic_legacy(self):
        with self._lock:
            legacy = self._legacy_held
        if legacy:
            self.diagnostic_store._set_legacy_hold()

    def _snapshot_diagnostic_attachment(self, request_id, dispatch_id):
        _hex(request_id); _hex(dispatch_id)
        with self._lock:
            legacy = self._legacy_held
            held = self._held is not None or not self._known
            row = self._data['requests'].get(request_id)
            attached = (request_id if row is not None and row['state'] != 'imported'
                        and row['audit']['dispatch_id'] == dispatch_id else None)
        if legacy:
            self.diagnostic_store._set_legacy_hold()
            raise ArtifactUnavailable(_LEGACY_GUIDANCE)
        if held:
            raise ArtifactUnavailable(_AUTHORING_GUIDANCE)
        return attached

    def quarantine_submission(self, request_id, attempt_id, dispatch_id, *, reason, content=None,
                              actor_identity_id=None, now=None):
        if request_id is not None:
            _hex(request_id)
        _hex(attempt_id); _hex(dispatch_id)
        if actor_identity_id is not None:
            _hex(actor_identity_id)
        if not isinstance(reason, str) or reason not in QUARANTINE_REASONS:
            raise ArtifactValidationError('Invalid artifact diagnostic reason.')
        if content is not None and not isinstance(content, str):
            raise ArtifactValidationError('Artifact diagnostic content must be text or null.')
        attached = self._snapshot_diagnostic_attachment(request_id, dispatch_id) if request_id is not None else None
        self._check_diagnostic_legacy()
        return self.diagnostic_store.record(request_id, attempt_id, dispatch_id, reason=reason, content=content,
            actor_identity_id=actor_identity_id, attached_request_id=attached, now=now)

    def request_diagnostics(self, request_id):
        _hex(request_id)
        self._check_diagnostic_legacy()
        try:
            return self.diagnostic_store.request_diagnostics(request_id)
        except ArtifactDiagnosticsUnavailable:
            return {'available': False, 'quarantine_ids': None, 'overflow_count': None,
                    'error': _owner_error('diagnostics', self.diagnostic_store._legacy_held)}

    def diagnostics(self, *, limit=100):
        _integer(limit, 1, 100)
        rows = []
        owners = {'authoring': {'available': True, 'reason': None},
                  'diagnostics': {'available': True, 'reason': None}}
        errors = {'authoring': None, 'diagnostics': None}
        try:
            with self._lock:
                self._check_index()
                observations = deepcopy(list(self._object_errors.values()))
                referenced = {'packet': {row['audit']['scope']['packet_id'] for row in self._data['requests'].values()},
                              'version': set(self._data['versions'])}
                for kind, folder, suffix in (('packet', self.root / 'artifact_briefs' / 'packets', '.json'),
                                            ('version', self.root / 'artifacts' / 'objects', '.md')):
                    self._safe(folder)
                    for path in folder.glob('*' + suffix):
                        if path.stem not in referenced[kind]:
                            self._safe(path)
                            observations.append({'id': path.stem, 'kind': 'orphan_' + kind, 'updated_at': path.stat().st_mtime})
                rows.extend(observations)
        except (OSError, ArtifactUnavailable):
            owners['authoring'] = {'available': False, 'reason': 'legacy_schema' if self._legacy_held else 'authoring_unavailable'}
            errors['authoring'] = _owner_error('authoring', self._legacy_held)
        self._check_diagnostic_legacy()
        detail = {'dispatch_group_count': None, 'detailed_count': None, 'retained_body_bytes': None}
        try:
            report = self.diagnostic_store.report()
            rows.extend(report['rows'])
            detail = {key: report[key] for key in detail}
        except ArtifactDiagnosticsUnavailable:
            legacy = self.diagnostic_store._legacy_held
            owners['diagnostics'] = {'available': False, 'reason': 'legacy_schema' if legacy else 'diagnostics_unavailable'}
            errors['diagnostics'] = _owner_error('diagnostics', legacy)
        rows.sort(key=lambda row: (-row['updated_at'], row['id']))
        partial = not all(owner['available'] for owner in owners.values())
        return {'rows': deepcopy(rows[:limit]), 'count': None if partial else len(rows),
                'truncated': partial or len(rows) > limit, **detail,
                'owners': owners, 'partial': partial, 'errors': errors}
