"""Explicit operator inspection of existing authenticated CLI chat messages."""
import hashlib
import json
import re
from copy import deepcopy

from turn_events import EventConflict, EventValidationError, event_id, validate_content


_SOURCE_FIELDS = ('run_id', 'turn_id', 'attempt_id', 'dispatch_id', 'input_revision')


def _current(engine, session_id):
    if type(session_id) is not int or session_id <= 0:
        raise EventValidationError('Session ID must be a positive integer.')
    return _current_session(engine._store.get(session_id), session_id)


def _current_session(session, session_id):
    if not session or session.get('completion_protocol') != 1:
        raise EventConflict('No explicit review turn is available for recovery.')
    invocation = session.get('active_invocation') or {}
    binding = session.get('participant_bindings', {}).get(invocation.get('role'), {})
    provenance = binding.get('launch_provenance') or {}
    if (session.get('state') not in ('active', 'waiting', 'stalled', 'interrupted')
            or session.get('stop_id') or session.get('pending_retry') or session.get('replaced_by_run_id')
            or not invocation or invocation.get('consumed') is not False
            or invocation.get('human') or binding.get('kind') != 'agent'
            or provenance.get('effective', {}).get('seat', {}).get('adapter') != 'cli'
            or invocation.get('run_id') != session.get('run_id')
            or invocation.get('input_revision') != session.get('input_revision')
            or any(item.get('attempt_id') == invocation.get('attempt_id')
                   for item in session.get('superseded_attempts', []))):
        raise EventConflict('This CLI turn cannot accept a selected message.')
    return session, invocation


def _source(session, invocation, snapshot):
    metadata = snapshot.get('metadata')
    if (snapshot.get('type') != 'chat' or snapshot.get('channel') != session.get('channel')
            or not isinstance(metadata, dict) or not metadata.get('seat_identity_id')
            or metadata.get('imported') is True or metadata.get('routing_suppressed') is True
            or metadata.get('quarantine_session_id') is not None
            or metadata.get('provenance') not in (None, '', 'authenticated_dispatch')):
        raise EventConflict('Message lacks eligible authenticated CLI provenance.')
    lineage = [invocation, *session.get('superseded_attempts', [])]
    matches = [item for item in lineage
               if item.get('expected_identity_id') == metadata['seat_identity_id']
               and item.get('run_id') == session['run_id']
               and item.get('turn_id') == invocation['turn_id']
               and item.get('input_revision') == session['input_revision']
               and all(metadata[key] == item.get(key) for key in _SOURCE_FIELDS if key in metadata)]
    if not matches:
        raise EventConflict('Message identity or turn scope conflicts with this review turn.')
    machine = (metadata.get('provenance') == 'authenticated_dispatch'
               and all(key in metadata for key in _SOURCE_FIELDS))
    attempts = {item['attempt_id'] for item in matches}
    if machine and len(attempts) != 1:
        raise EventConflict('Message source attempt is ambiguous.')
    return ('machine_verified' if machine else 'operator_attributed',
            next(iter(attempts)) if machine else None)


def _snapshot_identity(snapshot):
    if not isinstance(snapshot, dict) or type(snapshot.get('id')) is not int or snapshot['id'] < 0:
        raise EventValidationError('A complete source message snapshot is required.')
    try:
        digest = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    except (TypeError, ValueError, UnicodeError):
        raise EventValidationError('Message snapshot cannot be verified.') from None
    uid = snapshot.get('uid')
    if uid is None or uid == '':
        uid = f"legacy-{snapshot['id']}-{digest[:16]}"
    if not isinstance(uid, str) or not uid:
        raise EventConflict('Message source identity is invalid.')
    return uid, digest


def cli_message_candidate(engine, session_id, message_id):
    if type(message_id) is not int or message_id < 0:
        raise EventValidationError('Message ID must be a nonnegative integer.')
    with engine._lock:
        session, invocation = _current(engine, session_id)
        snapshot = engine._messages.get_snapshot(message_id)
        if snapshot is None:
            raise EventConflict('The selected message is no longer available.')
        attribution, source_attempt = _source(session, invocation, snapshot)
        validate_content('final', snapshot.get('text'))
        uid, digest = _snapshot_identity(snapshot)
        if any(event.get('source_message_uid') == uid for run in engine._store.list_all()
               for event in run.get('admitted_events', [])):
            raise EventConflict('Message has already been used to complete a review turn.')
        return {'session_id': session_id, 'message_id': message_id, 'message_uid': uid,
                'sender': snapshot.get('sender'), 'channel': snapshot['channel'],
                'created_at': snapshot.get('timestamp'), 'text': snapshot['text'],
                'snapshot_hash': digest, 'eligible': True, 'attribution': attribution,
                'requires_operator_confirmation': attribution == 'operator_attributed',
                'available_kinds': ['final', 'question'], 'source_attempt_id': source_attempt,
                'checkpoint': {'session_id': session_id, 'run_id': session['run_id'],
                    **{key: invocation[key] for key in ('turn_id', 'attempt_id', 'input_revision')}}}


def _selection_intent(session_id, decision, submitted_by):
    required = {'request_id', 'message_id', 'message_uid', 'snapshot_hash', 'kind',
                'checkpoint', 'confirm_operator_attribution'}
    if (type(session_id) is not int or session_id <= 0 or not isinstance(decision, dict)
            or set(decision) != required or type(decision['message_id']) is not int or decision['message_id'] < 0
            or not isinstance(decision['message_uid'], str) or not decision['message_uid']
            or not isinstance(decision['snapshot_hash'], str) or not re.fullmatch('[0-9a-f]{64}', decision['snapshot_hash'])
            or decision['kind'] not in ('final', 'question')
            or type(decision['confirm_operator_attribution']) is not bool
            or not isinstance(submitted_by, str) or not submitted_by.strip() or len(submitted_by) > 80):
        raise EventValidationError('Use only the reviewed message identity and explicit recovery decision.')
    event_id(decision['request_id'])
    checkpoint = decision['checkpoint']
    if (not isinstance(checkpoint, dict)
            or set(checkpoint) != {'session_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision'}
            or type(checkpoint['session_id']) is not int or checkpoint['session_id'] != session_id
            or not isinstance(checkpoint['turn_id'], str)
            or not isinstance(checkpoint['input_revision'], str)
            or not re.fullmatch('[0-9a-f]{64}', checkpoint['input_revision'])):
        raise EventValidationError('The exact preview checkpoint is required.')
    event_id(checkpoint['run_id'])
    event_id(checkpoint['attempt_id'])
    return dict(deepcopy(decision), submitted_by=submitted_by)


def _repair_transport(engine, session_id, request_id):
    """Return settlement and queue readiness without reviving any process."""
    try:
        engine._trigger.queue._reconcile()
        session = engine._store.get(session_id)
        fence = next(item for item in session['superseded_attempts']
                     if item.get('request_id') == request_id and item.get('reason') == 'superseded_by_operator_recovery')
        transport = fence['selected_transport']
        if transport.get('resolved') is True:
            return True, True
        if engine._seat_manager is None:
            return False, True
        try:
            proof = engine._seat_manager.selected_cli_exit_proof(
                deepcopy(transport['launch_provenance']), transport['dispatch_id'])
        except (OSError, ValueError):
            return False, True
        if not isinstance(proof, dict) or proof.get('local_ended') is not True:
            return False, True
        dispatch, identity = transport['dispatch_id'], transport['seat_identity_id']
        record = engine._trigger.queue.hold_recovered(dispatch, identity, dispatch, selected_cli=True)
        if record is not None:
            if record['state'] == 'cancelling':
                engine._trigger.queue.confirm_local_exit(dispatch,
                    record.get('cancellation_id') or record.get('stop_id'), evidence=proof)
            record = engine._trigger.queue.settle_recovered(dispatch, identity, evidence=proof)
            if record.get('recovery_hold', {}).get('cleared') is not True and record['state'] != 'settled_recovered':
                return False, False
        engine._store.resolve_selected_transport(session_id, request_id, proof)
        return True, True
    except (OSError, ValueError, KeyError, StopIteration):
        # Admission is already durable. Failed transport bookkeeping cannot
        # become a successful settlement or erase the copied answer.
        return False, False


def attach_cli_message(engine, session_id, decision, *, submitted_by='operator'):
    intent = _selection_intent(session_id, decision, submitted_by)
    with engine._lock:
        session = engine._store.get(session_id)
        if not session or session.get('completion_protocol') != 1:
            raise EventConflict('No explicit review turn is available for recovery.')
        previous = next((event for event in session.get('admitted_events', [])
                         if event.get('selected_request', {}).get('request_id') == intent['request_id']), None)
        replay = previous is not None
        if replay:
            if previous['selected_request'] != intent:
                raise EventConflict('Recovery request ID was already used for a different decision.')
        else:
            candidate = cli_message_candidate(engine, session_id, intent['message_id'])
            if any(candidate[key] != intent[key] for key in ('message_uid', 'snapshot_hash', 'checkpoint')):
                raise EventConflict('Selected message or session checkpoint changed since preview.')
            snapshot = engine._messages.get_snapshot(intent['message_id'])
            if snapshot is None:
                raise EventConflict('The selected message is no longer available.')
            engine._store.admit_selected_cli_event(session_id, snapshot,
                **{key: value for key, value in intent.items() if key != 'message_id'})
        settled, coordinated = _repair_transport(engine, session_id, intent['request_id'])
        engine._project_session(session_id, dispatch=not replay and coordinated)
        accepted = next(event for event in engine._store.get(session_id)['admitted_events']
                        if event.get('selected_request', {}).get('request_id') == intent['request_id'])
        return {'status': 'admitted', 'session_id': session_id, 'accepted_event_id': accepted['event_id'],
                'kind': accepted['kind'], 'source_message_id': accepted['source_message_id'],
                'source_message_uid': accepted['source_message_uid'], 'attribution': accepted['attribution'],
                'transport_settled': settled}
