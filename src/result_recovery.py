"""Explicit operator recovery of authenticated saved API review content."""
from copy import deepcopy

from result_outbox import ResultOutbox
from turn_events import IDENTITY_FIELDS, EventConflict, EventValidationError, event_id


def _session(engine, session_id):
    if type(session_id) is not int or session_id <= 0:
        raise EventValidationError('A saved result requires a valid session.')
    session = engine._store.get(session_id)
    if not session or session.get('completion_protocol') != 1:
        raise EventConflict('This session has no saved API result authority.')
    return session


def _records(engine, session_id, result_id=None):
    root = engine._store._path.parent / 'api_seat_runtime'
    pattern = '*/outbox/' + (result_id + '.json' if result_id is not None else '*.json')
    values = []
    try:
        for path in sorted(root.glob(pattern)):
            box = ResultOutbox(path.parent.parent)
            record = box.get(path.stem)
            payload = engine._store.briefs.verify_saved_result(record)
            if payload['session_id'] == session_id:
                values.append((box, payload))
    except (OSError, ValueError, KeyError, TypeError):
        raise EventValidationError('Saved result evidence is unavailable or failed verification.') from None
    if len({payload['result_id'] for _, payload in values}) != len(values):
        raise EventConflict('Saved result identity is ambiguous; no delivery was attempted.')
    return sorted(values, key=lambda item: (item[1]['created_at'], item[1]['result_id']))


def _disposition(session, payload):
    prior = next((event for event in session.get('admitted_events', [])
                  if event['event_id'] == payload['event_id']), None)
    if prior is not None:
        exact = (all(prior.get(key) == payload[key] for key in (*IDENTITY_FIELDS, 'session_id', 'kind', 'content'))
                 and prior.get('expected_identity_id') == payload['seat_identity_id'])
        return ('admitted', None) if exact else ('blocked', 'accepted_event_conflict')
    if session.get('stop_id'):
        return 'blocked', 'stopped_run'
    if any(item['attempt_id'] == payload['attempt_id'] for item in session.get('superseded_attempts', [])):
        return 'blocked', 'attempt_superseded'
    invocation = session.get('active_invocation') or {}
    binding = session.get('participant_bindings', {}).get(invocation.get('role'), {})
    provenance = binding.get('launch_provenance') or {}
    if (session['state'] not in ('active', 'waiting', 'stalled', 'interrupted') or invocation.get('consumed')
            or any(invocation.get(key) != payload[key] for key in IDENTITY_FIELDS)
            or session.get('input_revision') != payload['input_revision']
            or invocation.get('dispatch_id') != payload['dispatch_id']
            or invocation.get('expected_identity_id') != payload['seat_identity_id']
            or invocation.get('human') or binding.get('kind') != 'agent'
            or provenance.get('launch_attempt') != payload['launch_attempt']
            or provenance.get('effective', {}).get('seat', {}).get('adapter') != 'openai-compatible'):
        return 'blocked', 'not_current_attempt'
    return 'saved', None


def saved_results(engine, session_id):
    with engine._lock:
        session = _session(engine, session_id)
        previews = []
        for _, payload in _records(engine, session_id):
            state, reason = _disposition(session, payload)
            preview = {key: payload[key] for key in
                       ('result_id', 'brief_id', 'kind', 'content', 'created_at', 'seat_identity_id')}
            previews.append(dict(preview, state=state, reason=reason, can_deliver=state != 'blocked'))
        return previews


def _proof(engine, payload):
    if engine._seat_manager is not None:
        try:
            proof = engine._seat_manager.saved_result_exit_proof(deepcopy(payload))
            if isinstance(proof, dict) and proof.get('local_ended') is True:
                return proof
        except (OSError, ValueError):
            pass
    return {'local_ended': False}


def _settle(engine, payload, proof):
    if proof.get('local_ended') is not True:
        return False
    try:
        record = engine._trigger.queue.settle_recovered(payload['dispatch_id'], payload['seat_identity_id'], evidence=proof)
        return (record['state'] == 'settled_recovered'
                or record.get('recovery_hold', {}).get('cleared') is True)
    except (OSError, ValueError, PermissionError):
        # Content already committed. A queue persistence failure is not an ACK
        # failure and cannot be reported as a successful transport settlement.
        return False


def deliver_saved_result(engine, session_id, result_id, *, submitted_by='operator'):
    event_id(result_id)
    if not isinstance(submitted_by, str) or not submitted_by.strip() or len(submitted_by) > 80:
        raise EventValidationError('Operator display name must contain 1-80 characters.')
    with engine._lock:
        session = _session(engine, session_id)
        found = _records(engine, session_id, result_id)
        if len(found) != 1:
            raise EventConflict('No verified saved result matches this session and result.')
        box, payload = found[0]
        state, reason = _disposition(session, payload)
        if state == 'blocked':
            raise EventConflict('Saved answer cannot be delivered: ' + reason + '.')
        if state == 'admitted':
            # Resolve lost acknowledgements before considering later fences.
            # Projection repair cannot dispatch a successor a second time.
            engine._project_session(session_id, dispatch=False)
            box.acknowledge(result_id, result_id)
            settled = _settle(engine, payload, _proof(engine, payload))
        else:
            proof = _proof(engine, payload)
            if proof['local_ended'] is not True:
                engine._trigger.queue.hold_recovered(payload['dispatch_id'], payload['seat_identity_id'], result_id)
            engine._store.admit_verified_saved_event(session_id, payload, submitted_by=submitted_by)
            settled = _settle(engine, payload, proof)
            engine._project_session(session_id)
            box.acknowledge(result_id, result_id)
        return {'status': 'admitted', 'event_id': result_id, 'accepted_event_id': result_id,
                'session_id': session_id, 'kind': payload['kind'], 'transport_settled': settled}
