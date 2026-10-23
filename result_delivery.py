"""One generation, durable sealed result, then bounded delivery of that result.

The caller owns a queue claim. Existing saved results require operator recovery;
this component never reclaims transport, admits on startup or invokes a model
to replace a saved answer.
"""
from copy import deepcopy
import json
import time
import urllib.error

from result_outbox import ResultOutbox, OutboxError, _hex, _scope, verify_result
from review_brief import BriefStore, BriefError
from turn_events import parse_session_response


def complete_review_turn(runtime_path, envelope, dispatch_id, generate, submit, *, on_saved=None):
    _hex(dispatch_id)
    box = ResultOutbox(runtime_path)
    try:
        owner = BriefStore._result_owner(envelope['result_owner'], envelope)
        secret = _hex(envelope['seal_secret'], 64)
        if (owner['dispatch_id'] != dispatch_id or owner['launch_attempt'] != box.identity['attempt']
                or owner['launch_nonce'] != box.identity['launch_nonce']
                or owner['fingerprint'] != box.identity['fingerprint']):
            raise OutboxError('Review result scope does not match its immutable runtime.')
        header = {'version': 1, 'result_id': dispatch_id, 'dispatch_id': dispatch_id, 'event_id': dispatch_id,
                  **{field: envelope[field] for field in (
                      'session_id', 'brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')},
                  **{field: owner[field] for field in (
                      'seat_identity_id', 'launch_attempt', 'launch_nonce', 'fingerprint')}}
        _scope(header)
    except (KeyError, TypeError, BriefError):
        raise OutboxError('A managed review result requires its private brief authority.') from None

    prior = box.find(dispatch_id)
    if prior is not None:
        payload = verify_result(prior, secret)
        if any(payload[field] != value for field, value in header.items()):
            raise OutboxError('Existing saved result belongs to a different immutable review scope.')
        if on_saved is not None:
            on_saved(dispatch_id)
        return {'status': 'saved', 'result_id': dispatch_id}

    response = parse_session_response(generate())
    record = box.save({**header, **response, 'created_at': time.time()}, secret)
    if on_saved is not None:
        on_saved(dispatch_id)
    event = {field: record['payload'][field] for field in (
        'brief_id', 'kind', 'content', 'event_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')}
    for attempt in range(3):
        try:
            accepted = submit(deepcopy(event))
        except urllib.error.HTTPError as exc:
            duplicate = False
            try:
                if exc.code == 409:
                    duplicate = json.load(exc).get('accepted_event_id') == dispatch_id
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
                    or accepted.get('event_id') != dispatch_id):
                raise OutboxError('Server acknowledgement does not identify this saved result.')
            break
        time.sleep(.2)
    # A failed local ACK write must not repeat generation or claim success.
    box.acknowledge(dispatch_id, dispatch_id)
    return {'status': 'admitted', 'result_id': dispatch_id}
