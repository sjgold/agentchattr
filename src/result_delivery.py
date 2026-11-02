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
from sealed_result_io import deliver_saved


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
    return deliver_saved(event, submit, expected_id=dispatch_id, acknowledge=box.acknowledge,
                         error_factory=OutboxError, sleep=time.sleep)
