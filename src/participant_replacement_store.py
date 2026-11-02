"""Atomic replacement intent and assignment binding, without runtime effects."""
from copy import deepcopy
import hashlib
import json
import math
import re
import time
import uuid

from review_brief import MAX_PRIOR_BYTES, _revision, _text
from turn_events import EventConflict, EventValidationError, event_id


def _profile(value):
    required = {'key', 'launch_attempt', 'identity_id', 'effective', 'fingerprint'}
    if not isinstance(value, dict) or set(value) not in (required, required | {'fresh_base_effective'}):
        raise EventValidationError('An immutable managed source profile is required.')
    try:
        from runtime_ownership import _key
        _key(value['key'])
        event_id(value['launch_attempt'])
        event_id(value['identity_id'])
        effective = value['effective']
        base = value.get('fresh_base_effective', effective)
        if (not isinstance(effective, dict) or not isinstance(base, dict)
                or any(not isinstance(base.get(field), dict) for field in ('seat', 'provider', 'server'))
                or base['seat'].get('adapter') not in ('cli', 'openai-compatible')):
            raise ValueError('Malformed effective profile')
        payload = {'effective': effective, 'fresh_base_effective': base} if 'fresh_base_effective' in value else effective
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode('utf-8')).hexdigest()
        if not isinstance(value['fingerprint'], str) or not re.fullmatch('[0-9a-f]{64}', value['fingerprint']) or digest != value['fingerprint']:
            raise ValueError('Changed profile fingerprint')
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise EventValidationError('Managed replacement profile is malformed or changed.') from None
    return deepcopy(value), deepcopy(base)


def _session_id(value):
    if type(value) is not int or value <= 0:
        raise EventValidationError('Session ID must be a positive integer.')


def _staging_invocation(store, session, checkpoint_id, attempt_id):
    pending = session.get('pending_replacement')
    if not pending or pending.get('status') not in ('preparation_failed', 'blocked'):
        return store._participant_checkpoint(session, checkpoint_id, attempt_id), None
    # Presence includes malformed/unknown authority. Only proven absence can
    # permit a fresh choice, and it never un-fences the original worker.
    try:
        store.briefs._path(pending['new_brief_id']).stat()
    except FileNotFoundError:
        pass
    except (OSError, KeyError, ValueError):
        raise EventConflict('Replacement brief authority is unavailable; no owner was changed.') from None
    else:
        raise EventConflict('This replacement already has immutable brief authority. Use a new turn recovery.')
    view = deepcopy(session)
    view.pop('pending_replacement')
    view['state'] = 'stalled'
    if not view.get('turn_recovery'):
        raise EventConflict('The original logical checkpoint is unavailable.')
    view['turn_recovery']['status'] = 'stalled'
    old_requests = {key for key, value in session.get('replacement_requests', {}).items()
                    if value.get('status') == 'superseded_preparation'} | {pending['request_id']}
    view['superseded_attempts'] = [item for item in view.get('superseded_attempts', [])
        if not (item.get('attempt_id') == attempt_id and item.get('reason') == 'participant_replacement'
                and item.get('request_id') in old_requests and item.get('run_id') == session['run_id']
                and item.get('turn_id') == pending['old_invocation']['turn_id']
                and item.get('input_revision') == session['input_revision'])]
    return store._participant_checkpoint(view, checkpoint_id, attempt_id), pending


def replace_participant(store, session_id, *, checkpoint_id, attempt_id, request_id,
                        target_provenance, boot_id, reason='', submitted_by='operator', now=None):
    _session_id(session_id)
    for identifier in (checkpoint_id, attempt_id, request_id, boot_id):
        event_id(identifier)
    profile, _ = _profile(target_provenance)
    if (not isinstance(reason, str) or len(reason) > 256 or '\0' in reason
            or not isinstance(submitted_by, str) or not submitted_by.strip()
            or len(submitted_by) > 80 or '\0' in submitted_by):
        raise EventValidationError('Replacement reason/operator label is invalid.')
    try:
        reason.encode('utf-8')
        submitted_by.encode('utf-8')
    except UnicodeError:
        raise EventValidationError('Replacement labels must be valid UTF-8.') from None
    at = time.time() if now is None else now
    if type(at) not in (int, float) or not math.isfinite(at) or at < 0:
        raise EventValidationError('Replacement time must be finite and nonnegative.')
    intent = {'request_id': request_id, 'checkpoint_id': checkpoint_id, 'attempt_id': attempt_id,
              'target_identity_id': profile['identity_id'], 'target_fingerprint': profile['fingerprint'],
              'reason': reason, 'submitted_by': submitted_by}

    def stage(session):
        previous = session.get('replacement_requests', {}).get(request_id)
        if previous:
            if previous['intent'] != intent or previous['target_provenance'] != profile:
                raise EventConflict('Replacement request ID belongs to different choices.')
            pending = session.get('pending_replacement')
            if (not session.get('stop_id') and not session.get('replaced_by_run_id') and pending
                    and pending['request_id'] == request_id and pending['recovery_boot_id'] != boot_id):
                pending.update(recovery_boot_id=boot_id, status='preparing_contexts')
            return
        invocation, abandoned = _staging_invocation(store, session, checkpoint_id, attempt_id)
        role = invocation['role']
        positions = [{'phase': phase_index, 'turn': turn_index}
                     for phase_index, phase in enumerate(session['design_snapshot']['phases'])
                     for turn_index, participant in enumerate(phase['participants'])
                     if participant == role and (phase_index, turn_index) >= (session['current_phase'], session['current_turn'])]
        prior = [{'id': event.get('projected_message_id'), 'sender': event['sender'],
                  'text': event['content'], 'channel': session['channel']}
                 for event in session.get('admitted_events', []) if event['kind'] == 'final']
        _text(json.dumps(prior, ensure_ascii=False, allow_nan=False), MAX_PRIOR_BYTES, 'Approved prior results')
        pending = {'request_id': request_id, 'checkpoint_id': checkpoint_id, 'old_invocation': deepcopy(invocation),
                   'target_provenance': deepcopy(profile), 'role': role, 'affected_positions': positions,
                   'new_attempt_id': uuid.uuid4().hex, 'new_brief_id': uuid.uuid4().hex,
                   'new_dispatch_id': uuid.uuid4().hex,
                   'context_key': _revision({'run_id': session['run_id'], 'role': role, 'request_id': request_id}),
                   'approved_prior_results': prior,
                   'approved_continuation_context': deepcopy(session.get('continuation_context', [])),
                   'requested_at': at, 'recovery_boot_id': boot_id, 'status': 'preparing_contexts'}
        session.setdefault('superseded_attempts', []).append({
            **{key: invocation[key] for key in ('attempt_id', 'turn_id', 'dispatch_id', 'expected_identity_id')},
            'run_id': session['run_id'], 'input_revision': session['input_revision'],
            'superseded_at': at, 'reason': 'participant_replacement', 'request_id': request_id,
            'old_transport': {'dispatch_id': invocation['dispatch_id'],
                'seat_identity_id': invocation['expected_identity_id'],
                'launch_provenance': deepcopy(session['participant_bindings'][role].get('launch_provenance')),
                'resolved': False, 'resolved_at': None}})
        session.setdefault('replacement_requests', {})[request_id] = {
            'intent': deepcopy(intent), 'target_provenance': deepcopy(profile), 'role': role,
            **{key: deepcopy(pending[key]) for key in ('new_attempt_id', 'new_brief_id', 'new_dispatch_id',
                                                      'context_key', 'affected_positions', 'requested_at')},
            'status': 'preparing_contexts'}
        if abandoned:
            entry = session['replacement_requests'][abandoned['request_id']]
            entry.update(status='superseded_preparation', superseded_by=request_id, superseded_at=at)
            if abandoned.get('context'):
                entry['abandoned_context'] = deepcopy(abandoned['context'])
        session['pending_replacement'] = pending
        session['turn_recovery'].update(status='replacing')
        session['turn_recovery'].setdefault('actions', []).append({'action': 'replace', 'at': at, 'request_id': request_id})
        session.update(state='retrying', dispatch_eligible=False)
    return store._event_update(session_id, stage, skip_if_unchanged=True)


def _summary(provenance, identity, name):
    seat = (provenance or {}).get('effective', {}).get('seat', {})
    return {'identity_id': identity, 'name': name, 'launch_attempt': (provenance or {}).get('launch_attempt'),
            **{key: seat.get(key) for key in ('adapter', 'provider', 'model', 'reasoning')}}


def bind_replacement(store, session_id, request_id, context, provenance, *, boot_id):
    _session_id(session_id)
    event_id(request_id)
    event_id(boot_id)
    profile, base = _profile(provenance)
    context = deepcopy(context)
    if not isinstance(context, dict):
        raise EventValidationError('A verified replacement context is required.')

    def bind(session):
        request = session.get('replacement_requests', {}).get(request_id)
        if not request:
            raise EventConflict('This replacement request is unavailable.')
        stable = {key: context.get(key) for key in ('key', 'launch_attempt', 'identity_id', 'context_id', 'name')}
        if request.get('bound_context'):
            if request['bound_context'] != stable or request['bound_provenance'] != profile:
                raise EventConflict('The bound replacement owner is immutable.')
            return
        pending = session.get('pending_replacement')
        if (session.get('stop_id') or session.get('replaced_by_run_id') or session.get('pending_retry')
                or not pending or pending['request_id'] != request_id
                or pending['recovery_boot_id'] != boot_id or context.get('verified_boot_id') != boot_id
                or context.get('state') != 'ready' or context.get('clean_context') is not True):
            raise EventConflict('This replacement needs its current verified ready context.')
        expected_key = 'replacement-' + hashlib.sha256(pending['context_key'].encode('utf-8')).hexdigest()[:24] + '/context'
        old = pending['old_invocation']
        _, selected_base = _profile(pending['target_provenance'])
        if (context.get('key') != expected_key or profile['key'] != expected_key
                or context.get('identity_id') != profile['identity_id']
                or profile['identity_id'] in (old['expected_identity_id'], pending['target_provenance']['identity_id'])
                or context.get('launch_attempt') != profile['launch_attempt']
                or profile.get('fresh_base_effective') != selected_base or base != selected_base
                or not isinstance(context.get('name'), str) or not context['name']):
            raise EventConflict('Replacement context does not match its frozen selected profile.')
        event_id(context.get('context_id'))
        expected_effective = deepcopy(selected_base)
        if selected_base['seat']['adapter'] == 'cli':
            from cli_seats import build_fresh_context_args
            expected_effective['provider']['cli_args'] = list(selected_base['provider'].get('cli_args', [])) + build_fresh_context_args(selected_base['provider'], context['context_id'])
        if profile['effective'] != expected_effective:
            raise EventConflict('Replacement effective settings drifted from the approved source.')
        remembered = pending.get('context')
        if remembered and remembered.get('launch_attempt') != context['launch_attempt']:
            raise EventConflict('Prepared replacement launch changed before binding.')
        role = pending['role']
        old_binding = session['participant_bindings'][role]
        change = {'request_id': request_id, 'role': role, 'at': time.time(),
                  'old': _summary(old_binding.get('launch_provenance'), old['expected_identity_id'], old['expected_agent']),
                  'new': _summary(profile, profile['identity_id'], context['name']),
                  'affected_positions': deepcopy(pending['affected_positions'])}
        session.setdefault('participant_changes', []).append(change)
        old_binding.update(identity_id=profile['identity_id'], launch_provenance=deepcopy(profile))
        session['cast'][role] = context['name']
        pending.update(context=deepcopy(context), status='dispatching')
        request.update(bound_context=stable, bound_provenance=deepcopy(profile), status='dispatching')
        session.update(active_invocation=None, state='active', dispatch_eligible=True)
        session['turn_recovery'].update(status='resolved', resolved_by=pending['new_attempt_id'])
    return store._event_update(session_id, bind, skip_if_unchanged=True)
