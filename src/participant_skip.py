"""Missing contribution projection and bounded post-skip dispatch repair."""
from copy import deepcopy
import uuid

from review_brief import missing_contributions
from turn_events import EventConflict, EventValidationError, event_id


def next_position(session, skipped):
    phase, turn = skipped['phase'], skipped['turn']
    phases = session['design_snapshot']['phases']
    if turn + 1 < len(phases[phase]['participants']):
        return phase, turn + 1
    return (phase + 1, 0) if phase + 1 < len(phases) else None


def successor(session):
    if not session.get('skipped_turns'):
        return None
    skipped = session['skipped_turns'][-1]
    if next_position(session, skipped) != (session['current_phase'], session['current_turn']):
        return None
    turn_id = f"{session['run_id']}:{session['current_phase']}:{session['current_turn']}"
    if any(event['turn_id'] == turn_id for event in session.get('admitted_events', [])):
        return None  # A question already consumed this generation; Continue is fresh work.
    namespace = uuid.UUID(hex=skipped['projection_id'])
    return {key: uuid.uuid5(namespace, key).hex for key in ('new_attempt_id', 'new_brief_id', 'new_dispatch_id')}


def footer(session):
    missing = missing_contributions(session)
    if not missing:
        return ''
    return '\n\nMissing contributions:\n' + '\n'.join(
        f"- {item['role']} ({session['design_snapshot']['phases'][item['phase']]['name']}): {item['reason']}"
        for item in missing)


def project_skips(engine, session):
    for skipped in session.get('skipped_turns', []):
        if skipped.get('projected_message_id') is not None:
            continue
        audit = deepcopy(skipped)
        audit['projected_message_id'] = None
        text = (f"Missing contribution: {skipped['role']} from {skipped['agent_name']}. "
                f"Operator skipped this turn: {skipped['reason']}")
        if session.get('missing_output') and skipped == session['skipped_turns'][-1]:
            text = 'Missing output. ' + text
        # This snapshot belongs to this skip, not later skips added to the run.
        index = session['skipped_turns'].index(skipped)
        missing = missing_contributions(dict(session, skipped_turns=session['skipped_turns'][:index + 1]))
        message = engine._messages.add_once('session-skip:' + skipped['projection_id'], 'system', text,
            msg_type='session_skip', channel=session['channel'], metadata={'session_id': session['id'],
                'is_notice': True, 'routing_suppressed': True, 'skipped_turn': audit,
                'missing_contributions': missing})
        engine._store.link_skip_projection(session['id'], skipped['projection_id'], message['id'])


def skip_participant(engine, session_id, decision, *, submitted_by='operator'):
    from participant_recovery import _session, settle_retired
    if not isinstance(decision, dict) or set(decision) != {'request_id', 'checkpoint_id', 'attempt_id', 'reason', 'confirm_skip'}:
        raise EventValidationError('Skip requires the exact checkpoint and explicit missing-work decision.')
    for key in ('request_id', 'checkpoint_id', 'attempt_id'):
        event_id(decision[key])
    with engine._lock:
        before = _session(engine, session_id)
        replay = any(item['request_id'] == decision['request_id'] for item in before.get('skipped_turns', []))
        session = engine._store.skip_participant(session_id, **decision, submitted_by=submitted_by)
        engine._trigger.queue._reconcile()
        settle_retired(engine, session)
        # Replay can repair only the exact immediate successor, never another
        # turn reached since this operator decision or a cold interrupted run.
        may_dispatch = (not replay or (successor(session) is not None and session['state'] == 'active'
            and not session.get('active_invocation') and not session.get('stop_id')
            and session.get('dispatch_eligible') is not False))
        engine._project_session(session_id, dispatch=may_dispatch)
        current = engine._store.get(session_id)
        reserved = successor(current)
        invocation = current.get('active_invocation')
        if (replay and reserved and invocation and not invocation.get('consumed')
                and invocation['attempt_id'] == reserved['new_attempt_id']
                and not current.get('stop_id') and current.get('dispatch_eligible') is not False
                and current['state'] in ('waiting', 'stalled')):
            records = engine._trigger.queue.for_identity({'name': invocation['expected_agent'],
                                                          'identity_id': invocation['expected_identity_id']})
            if not any(item['envelope']['dispatch_id'] == reserved['new_dispatch_id'] for item in records):
                engine._trigger_current(current, retry=reserved)
        skipped = next(item for item in session['skipped_turns'] if item['request_id'] == decision['request_id'])
        return {'status': 'skipped', 'request_id': decision['request_id'], 'session_id': session_id,
                'projection_id': skipped['projection_id']}
