"""Operator participant recovery, serialized by the session coordinator lock."""
from copy import deepcopy
import re
import time

from api_seats import SeatError
from turn_events import EventConflict, EventValidationError, event_id


def _decision(value, required, optional=()):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - set(optional):
        raise EventValidationError('Participant recovery decision has invalid fields.')
    for key in required:
        if key != 'target_fingerprint':
            event_id(value[key])
    if 'target_fingerprint' in required and (not isinstance(value['target_fingerprint'], str)
            or not re.fullmatch('[0-9a-f]{64}', value['target_fingerprint'])):
        raise EventValidationError('Select the exact displayed source profile fingerprint.')


def _session(engine, session_id):
    if type(session_id) is not int or session_id <= 0:
        raise EventValidationError('Session ID must be a positive integer.')
    value = engine._store.get(session_id)
    if not value or value.get('completion_protocol') != 1:
        raise EventConflict('This review is unavailable for participant recovery.')
    return value


def _ack(session, request_id):
    request = session['replacement_requests'][request_id]
    pending = session.get('pending_replacement')
    return {'request_id': request_id, 'status': ('stopped' if session.get('stop_id') else
        pending['status'] if pending and pending['request_id'] == request_id else request['status']),
        'session_id': session['id'], 'role': request['role'],
        'attempt_id': request['new_attempt_id']}


def recovery_options(engine, session_id):
    from participant_replacement_store import _summary
    with engine._lock:
        session = _session(engine, session_id)
        invocation = session.get('active_invocation') or {}
        checkpoint = session.get('turn_recovery') or {}
        pending = session.get('pending_replacement')
        eligible = False
        if invocation and checkpoint:
            try:
                from participant_replacement_store import _staging_invocation
                _staging_invocation(engine._store, session, checkpoint['checkpoint_id'], invocation['attempt_id'])
                eligible = True
            except ValueError:
                pass
        choices = []
        if eligible and engine._seat_manager:
            for owner in engine._registry.get_all().values():
                provenance = engine._seat_manager.launch_provenance(owner)
                if not provenance:
                    continue
                seat = provenance['effective']['seat']
                if seat['adapter'] == 'cli' and provenance['effective']['provider'].get('cli_fresh_context_verified') is not True:
                    continue
                choices.append({**_summary(provenance, owner['identity_id'], owner['name']),
                                'fingerprint': provenance['fingerprint']})
        role = invocation.get('role') or (pending or {}).get('role')
        binding = session.get('participant_bindings', {}).get(role, {})
        request = session.get('replacement_requests', {}).get((pending or {}).get('request_id'), {})
        context = (pending or {}).get('context') or {}
        return {'session_id': session_id, 'eligible': eligible, 'role': role,
                'checkpoint_id': checkpoint.get('checkpoint_id'), 'attempt_id': invocation.get('attempt_id'),
                'current': _summary(binding.get('launch_provenance'), binding.get('identity_id'), session['cast'].get(role)),
                'choices': choices, 'pending': ({'request_id': pending['request_id'], 'status': pending['status'],
                    'preparation_attempt': context.get('launch_attempt'),
                    'can_repair': pending['status'] == 'preparation_failed' and not request.get('bound_context')
                                  and not _brief_exists(engine, pending['new_brief_id'])} if pending else None)}


def settle_retired(engine, session):
    """Observe genuine exit only; replacing content never terminates a worker."""
    if not engine._seat_manager:
        return
    for attempt in session.get('superseded_attempts', []):
        audit = attempt.get('old_transport')
        if not audit or audit.get('resolved') is True or not audit.get('launch_provenance'):
            continue
        try:
            proof = engine._seat_manager.participant_exit_proof(audit['launch_provenance'], audit['dispatch_id'])
            if proof.get('local_ended') is True:
                engine._trigger.queue.settle_old_transport(session['id'], attempt['request_id'], proof)
        except (OSError, ValueError):
            continue  # The durable physical-seat hold remains until proof/write succeeds.


def _brief_exists(engine, brief_id):
    try:
        engine._store.briefs._path(brief_id).stat()
    except FileNotFoundError:
        return False
    return True


def _finalize_dispatch(engine, session, pending, envelope, now):
    records = engine._trigger.queue.for_identity({'name': envelope['expected_agent'],
        'identity_id': envelope['expected_identity_id']})
    record = next((value for value in records if value['envelope']['dispatch_id'] == pending['new_dispatch_id']), None)
    if record and any(record['envelope'].get(key) != envelope[key]
                      for key in ('run_id', 'turn_id', 'attempt_id', 'input_revision')):
        raise EventConflict('Replacement dispatch differs from its immutable brief.')
    queued = record is not None and record['state'] not in ('cancelled', 'failed')
    def finish(value):
        if value.get('stop_id'):
            return
        active = value.get('active_invocation')
        if active is None:
            value['active_invocation'] = engine._store._invocation(value, envelope,
                pending['new_dispatch_id'], False, pending['requested_at'])
            if not _brief_exists(engine, envelope['brief_id']):
                value['active_invocation']['intent_only'] = True
        elif active['attempt_id'] != pending['new_attempt_id']:
            raise EventConflict('Another invocation occupies this replacement turn.')
        request = value['replacement_requests'][pending['request_id']]
        request['status'] = 'dispatched' if queued else 'local_delivery_failure'
        value['waiting_on'] = envelope['expected_agent']
        value['state'] = 'waiting' if queued else 'stalled'
        if not queued:
            import uuid
            value['turn_recovery'] = {'checkpoint_id': uuid.uuid4().hex, 'attempt_id': envelope['attempt_id'],
                'turn_id': envelope['turn_id'], 'dispatch_id': pending['new_dispatch_id'],
                'first_at': now, 'actions': [], 'recoverable_result': False,
                'reason': 'local_delivery_failure', 'status': 'stalled',
                'last_event': {'state': 'publication_failed', 'at': now}}
        value.pop('pending_replacement', None)
    return engine._store._event_update(session['id'], finish)


def finish_replacement(engine, session):
    pending = session.get('pending_replacement')
    if (not pending or session.get('stop_id') or session.get('replaced_by_run_id')
            or pending['recovery_boot_id'] != engine._seat_manager.boot_id):
        return session
    now = time.time()
    engine._trigger.queue._reconcile()
    settle_retired(engine, session)
    # Durable brief ownership wins before any clone/readiness call, including
    # a committed enqueue whose HTTP/storage reply was lost.
    if _brief_exists(engine, pending['new_brief_id']):
        envelope = engine._store.briefs.get(pending['new_brief_id'], operator=True)
        return _finalize_dispatch(engine, session, pending, envelope, now)
    try:
        context = engine._seat_manager.prepare_replacement_context(pending['target_provenance'],
            pending['context_key'], binding={'child_run_id': session['run_id'], 'role': pending['role']})
        def remember(value):
            current = value['pending_replacement']
            current['context'] = deepcopy(context)
            current['status'] = ('dispatching' if context['state'] == 'ready' else
                                 'preparing_contexts' if context['state'] == 'starting' else 'preparation_failed')
            value['replacement_requests'][pending['request_id']]['status'] = current['status']
        session = engine._store._event_update(session['id'], remember, skip_if_unchanged=True)
        pending = session['pending_replacement']
        if context['state'] != 'ready':
            return session
        owner = next((value for value in engine._registry.get_all().values()
                      if value['identity_id'] == context['identity_id']), None)
        provenance = engine._seat_manager.launch_provenance(owner)
        session = engine._store.bind_replacement(session['id'], pending['request_id'], context, provenance,
                                                boot_id=engine._seat_manager.boot_id)
        pending = session['pending_replacement']
        result = engine._trigger_current(session, retry=pending, now=now)
        if _brief_exists(engine, pending['new_brief_id']):
            envelope = engine._store.briefs.get(pending['new_brief_id'], operator=True)
            return _finalize_dispatch(engine, session, pending, envelope, now)
        if result is False:
            raise SeatError('Replacement context could not be delivered.')
        return session
    except (SeatError, OSError, ValueError):
        # A persisted brief can never be rebound or repaired as preparation.
        if _brief_exists(engine, pending['new_brief_id']):
            envelope = engine._store.briefs.get(pending['new_brief_id'], operator=True)
            return _finalize_dispatch(engine, engine._store.get(session['id']), pending, envelope, now)
        def failed(value):
            value['pending_replacement']['status'] = 'preparation_failed'
            value['replacement_requests'][pending['request_id']]['status'] = 'preparation_failed'
        return engine._store._event_update(session['id'], failed, skip_if_unchanged=True)


def replace_participant(engine, session_id, decision, *, submitted_by='operator'):
    _decision(decision, {'request_id', 'checkpoint_id', 'attempt_id', 'target_identity_id', 'target_fingerprint'}, {'reason'})
    with engine._lock:
        session = _session(engine, session_id)
        manager = engine._seat_manager
        if not manager:
            raise EventConflict('Managed replacement contexts are unavailable.')
        previous = session.get('replacement_requests', {}).get(decision['request_id'])
        if previous:
            provenance = previous['target_provenance']
            if (provenance['identity_id'] != decision['target_identity_id']
                    or provenance['fingerprint'] != decision['target_fingerprint']):
                raise EventConflict('Replacement request ID belongs to different choices.')
        else:
            owner = next((value for value in engine._registry.get_all().values()
                          if value['identity_id'] == decision['target_identity_id']), None)
            provenance = manager.launch_provenance(owner)
            if not provenance or provenance['fingerprint'] != decision['target_fingerprint']:
                raise EventConflict('The selected owned profile changed. Inspect choices again.')
        session = engine._store.replace_participant(session_id, **{key: decision[key] for key in
            ('request_id', 'checkpoint_id', 'attempt_id')}, target_provenance=provenance,
            boot_id=manager.boot_id, reason=decision.get('reason', ''), submitted_by=submitted_by)
        if not session.get('stop_id'):
            session = finish_replacement(engine, session)
        return _ack(session, decision['request_id'])


def repair_replacement(engine, session_id, decision):
    _decision(decision, {'request_id', 'preparation_attempt'}, {'confirmation'})
    confirmation = decision.get('confirmation')
    if confirmation is not None and (not isinstance(confirmation, dict)
            or set(confirmation) != {'confirm', 'launch_attempt'} or confirmation['confirm'] is not True
            or confirmation['launch_attempt'] != decision['preparation_attempt']):
        raise EventValidationError('Confirm the exact prepared launch before requesting its exit.')
    with engine._lock:
        session = _session(engine, session_id)
        request = session.get('replacement_requests', {}).get(decision['request_id']) or {}
        previous = request.get('preparation_repairs', {}).get(decision['preparation_attempt'])
        if previous:
            if previous['confirmation'] != confirmation:
                raise EventConflict('This repair attempt belongs to different confirmation.')
            if previous.get('launch_attempt'):
                return _ack(session, decision['request_id'])
        pending = session.get('pending_replacement')
        if (not pending or pending['request_id'] != decision['request_id'] or session.get('stop_id')
                or session.get('replaced_by_run_id') or pending.get('status') != 'preparation_failed'
                or session['replacement_requests'][decision['request_id']].get('bound_context')
                or _brief_exists(engine, pending['new_brief_id'])):
            raise EventConflict('Only the exact failed pre-brief preparation can be repaired.')
        if (pending.get('context') or {}).get('launch_attempt') != decision['preparation_attempt']:
            raise EventConflict('The exact current failed preparation is required.')
        def journal(value):
            value['replacement_requests'][decision['request_id']].setdefault('preparation_repairs', {}).setdefault(
                decision['preparation_attempt'], {'confirmation': deepcopy(confirmation), 'launch_attempt': None})
        engine._store._event_update(session_id, journal, skip_if_unchanged=True)
        context = engine._seat_manager.repair_replacement_context(pending['target_provenance'], pending['context_key'],
            binding={'child_run_id': session['run_id'], 'role': pending['role']},
            preparation_attempt=decision['preparation_attempt'], dispatch_id=pending['new_dispatch_id'],
            confirmation=decision.get('confirmation'))
        def remember(value):
            value['pending_replacement'].update(context=deepcopy(context),
                recovery_boot_id=engine._seat_manager.boot_id,
                status='preparing_contexts' if context['state'] in ('ready', 'starting') else 'preparation_failed')
            if context.get('launch_attempt') and context['launch_attempt'] != decision['preparation_attempt']:
                value['replacement_requests'][decision['request_id']]['preparation_repairs'][
                    decision['preparation_attempt']]['launch_attempt'] = context['launch_attempt']
        session = engine._store._event_update(session_id, remember)
        return _ack(finish_replacement(engine, session), decision['request_id'])
