"""Shared result IO mechanics; callers retain schemas and admission policy."""
from copy import deepcopy
import hashlib
import hmac
import json
import re
import time
import urllib.error


def canonical_utf8(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def payload_mac(payload, secret_bytes):
    return hmac.new(secret_bytes, canonical_utf8(payload), hashlib.sha256).hexdigest()


def read_bounded_json(path, maximum):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Saved JSON has duplicate fields.')
            value[key] = item
        return value

    with path.open('rb') as source:
        raw = source.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('Saved result file exceeds its storage limit.')
    return json.loads(raw, object_pairs_hook=unique)


def put_immutable_json(path, value, *, lock, load_existing, write, conflict_error):
    with lock:
        if path.exists():
            prior = load_existing()
            if prior != value:
                raise conflict_error('A different result already occupies this immutable result ID.')
            return prior
        write(path, value)
    return deepcopy(value)


def validate_api_result_owner(owner, envelope, error_factory):
    fields = {'adapter', 'dispatch_id', 'seat_identity_id', 'launch_attempt', 'launch_nonce', 'fingerprint'}
    if (not isinstance(owner, dict) or set(owner) != fields
            or owner['adapter'] != 'openai-compatible'
            or type(envelope.get('completion_protocol')) is not int or envelope['completion_protocol'] != 1
            or owner['seat_identity_id'] != envelope.get('expected_identity_id')):
        raise error_factory('Result authority requires the exact managed API participant.')
    for field in fields - {'adapter'}:
        size = 64 if field == 'fingerprint' else 32
        if not isinstance(owner[field], str) or not re.fullmatch('[0-9a-f]{' + str(size) + '}', owner[field]):
            raise error_factory('Result authority requires exact immutable launch references.')
    return deepcopy(owner)


def public_envelope(value):
    result = deepcopy(value)
    result.pop('_result_seal', None)
    return result


def deliver_saved(event, submit, *, expected_id, acknowledge, error_factory, sleep=None):
    pause = time.sleep if sleep is None else sleep
    for attempt in range(3):
        try:
            accepted = submit(deepcopy(event))
        except urllib.error.HTTPError as exc:
            duplicate = False
            try:
                if exc.code == 409:
                    duplicate = json.load(exc).get('accepted_event_id') == expected_id
            except (ValueError, AttributeError):
                pass
            finally:
                exc.close()
            if duplicate:
                break
            if exc.code < 500 or attempt == 2:
                raise
        except OSError:
            if attempt == 2:
                raise
        else:
            if (not isinstance(accepted, dict) or accepted.get('status') != 'admitted'
                    or accepted.get('event_id') != expected_id):
                raise error_factory('Server acknowledgement does not identify this saved result.')
            break
        pause(.2)
    # A failed local ACK must not repeat generation or claim success.
    acknowledge(expected_id, expected_id)
    return {'status': 'admitted', 'result_id': expected_id}
