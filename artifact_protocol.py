"""Artifact-v1 grammar and domain-separated seals, with no dispatch authority."""
from copy import deepcopy
import hmac
import json
from pathlib import Path
import re

from artifact_store import (ArtifactValidationError, ArtifactUnavailable, MAX_ARTIFACT_BYTES, request_ids,
    _canonical, _fields, _hex, _integer, _number, _observation, _path_key, _source_run, _text)
from sealed_result_io import payload_mac


MAX_RESULT_RECORD_BYTES = 6 * MAX_ARTIFACT_BYTES + 32768
MAX_BRIEF_RECORD_BYTES = 6 * 32768 + 32768
MAX_ACK_BYTES = 16384
BRIEF_FIELDS = frozenset(('version', 'purpose', 'brief_id', 'request_id', 'lineage_id',
    'attempt_id', 'dispatch_id', 'packet_id', 'scope_sha256', 'expected_parent', 'producer',
    'instruction', 'format', 'input_revision', 'source_run'))
PAYLOAD_FIELDS = frozenset(('version', 'purpose', 'result_id', 'dispatch_id', 'request_id',
    'attempt_id', 'brief_id', 'lineage_id', 'scope_sha256', 'expected_parent', 'seat_identity_id',
    'launch_attempt', 'launch_nonce', 'fingerprint', 'consumer_id', 'kind', 'markdown',
    'observation', 'created_at'))
OWNER_FIELDS = frozenset(('adapter', 'dispatch_id', 'seat_identity_id', 'launch_attempt',
                          'launch_nonce', 'fingerprint'))


def _purpose(value):
    if type(value['version']) is not int or value['version'] != 1 or value['purpose'] != 'artifact-v1':
        raise ArtifactValidationError('Unsupported artifact protocol version or purpose.')


def _ids(value):
    derived = request_ids(value['request_id'])
    _hex(value['lineage_id'])
    for field in ('attempt_id', 'dispatch_id', 'brief_id'):
        if value[field] != derived[field]:
            raise ArtifactValidationError('Artifact protocol identifiers differ from the request.')
    _hex(value['scope_sha256'], 64)
    return derived


def _parent(value):
    if value is not None:
        _fields(value, ('version_id', 'sequence', 'sha256'))
        _hex(value['version_id']); _integer(value['sequence'], 1); _hex(value['sha256'], 64)


def _size(value, maximum):
    # Validate UTF-8/canonical values; storage uses atomic_json's ASCII escapes.
    if (len(_canonical(value)) > maximum
            or len(json.dumps(value, ensure_ascii=True, allow_nan=False).encode('utf-8')) > maximum):
        raise ArtifactValidationError('Artifact protocol record exceeds its byte limit.')


def _owned_path(root, path):
    base, path = Path(root).absolute(), Path(path).absolute()
    if (_path_key(base.resolve()) != _path_key(base)
            or _path_key(path.resolve()) != _path_key(path)
            or not path.resolve().is_relative_to(base)):
        raise ArtifactUnavailable('Artifact storage cannot follow redirected paths.')
    return path


def validate_owner(value):
    _fields(value, OWNER_FIELDS)
    if value['adapter'] not in ('cli', 'openai-compatible'):
        raise ArtifactValidationError('Artifact authority requires a managed adapter.')
    for field in OWNER_FIELDS - {'adapter'}:
        _hex(value[field], 64 if field == 'fingerprint' else 32)
    return deepcopy(value)


def validate_brief(body):
    _fields(body, BRIEF_FIELDS)
    _purpose(body)
    derived = _ids(body)
    if body['packet_id'] != derived['packet_id']:
        raise ArtifactValidationError('Artifact brief packet differs from its request.')
    _parent(body['expected_parent'])
    producer = body['producer']
    _fields(producer, ('identity_id', 'adapter', 'launch_attempt', 'launch_nonce', 'fingerprint'))
    validate_owner({'dispatch_id': body['dispatch_id'], 'seat_identity_id': producer['identity_id'],
        **{field: producer[field] for field in ('adapter', 'launch_attempt', 'launch_nonce', 'fingerprint')}})
    _text(body['instruction'], 32768); _text(body['format'], 512)
    if body['input_revision'] is not None:
        _hex(body['input_revision'], 64)
    _source_run(body['source_run'])
    if body['source_run'] is not None and body['input_revision'] != body['source_run']['input_revision']:
        raise ArtifactValidationError('Artifact brief input and source run differ.')
    _size(body, MAX_BRIEF_RECORD_BYTES)
    return deepcopy(body)


def validate_payload(payload):
    _fields(payload, PAYLOAD_FIELDS)
    _purpose(payload)
    _ids(payload)
    if payload['result_id'] != payload['dispatch_id'] or payload['kind'] != 'artifact':
        raise ArtifactValidationError('Artifact result identity or kind differs.')
    _parent(payload['expected_parent'])
    for field in ('seat_identity_id', 'launch_attempt', 'launch_nonce'):
        _hex(payload[field])
    _hex(payload['fingerprint'], 64)
    consumer = payload['consumer_id']
    if not isinstance(consumer, str) or not re.fullmatch('[a-zA-Z0-9_.-]{1,128}', consumer):
        raise ArtifactValidationError('Artifact result requires its exact consumer claim.')
    _text(payload['markdown'], MAX_ARTIFACT_BYTES)
    observation = payload['observation']
    _fields(observation, ('confirmed_model', 'confirmation_reason'))
    adapter = 'cli' if observation['confirmation_reason'] == 'cli_model_unverified' else 'openai-compatible'
    _observation(observation, adapter)  # Service also checks the actual frozen adapter.
    _number(payload['created_at'])
    _size(payload, MAX_RESULT_RECORD_BYTES)
    return deepcopy(payload)


def seal_result(payload, seal_secret):
    value = validate_payload(payload)
    key = bytes.fromhex(_hex(seal_secret, 64))
    return {'payload': value, 'seal': payload_mac(value, key)}


def verify_result(record, seal_secret):
    _fields(record, ('payload', 'seal'))
    value = validate_payload(record['payload'])
    digest = _hex(record['seal'], 64)
    expected = payload_mac(value, bytes.fromhex(_hex(seal_secret, 64)))
    if not hmac.compare_digest(digest, expected):
        raise ArtifactValidationError('Artifact result seal does not match its private brief.')
    return value


def parse_response(text):
    _text(text, MAX_RESULT_RECORD_BYTES)
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ArtifactValidationError('Artifact response has duplicate fields.')
            value[key] = item
        return value
    def invalid_constant(_value):
        raise ArtifactValidationError('Artifact response contains nonfinite data.')
    try:
        value = json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)
        _fields(value, ('kind', 'markdown'))
        if value['kind'] != 'artifact':
            raise ArtifactValidationError('Artifact response kind is invalid.')
        _text(value['markdown'], MAX_ARTIFACT_BYTES)
        return deepcopy(value)
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise ArtifactValidationError('Expected one bounded artifact JSON response; nothing was published.') from None
