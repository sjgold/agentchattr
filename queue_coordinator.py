"""Serialize durable run eligibility with queue mutations, without store nesting."""
import math

from dispatch_queue import ACTIVE, QueueBusy, QueueConflict, _identifier


def is_nonterminal_review(run):
    return (run.get('completion_protocol') == 1 and not run.get('stop_id')
            and not run.get('replaced_by_run_id')
            and run.get('state') in ('active', 'waiting', 'paused', 'awaiting_input',
                                     'stalled', 'retrying', 'interrupted', 'prepared'))


def allowed_review_dispatch_ids(runs, identity_id):
    """Restrict a seat to its earliest outstanding logical review invocation."""
    ordered, malformed = [], []
    for run in runs:
        if not is_nonterminal_review(run):
            continue
        invocation = run.get('active_invocation') or {}
        if (invocation.get('expected_identity_id') != identity_id
                or invocation.get('human') is True or invocation.get('consumed') is True):
            continue
        if invocation.get('attempt_id') and any(
                attempt.get('attempt_id') == invocation['attempt_id']
                for attempt in run.get('superseded_attempts', [])):
            continue  # Retry's durable fence retires occupancy before rebinding.
        dispatch = invocation.get('dispatch_id')
        try:
            _identifier(dispatch, 'Dispatch ID')
            valid_dispatch = True
        except ValueError:
            valid_dispatch = False
        session_id = run.get('id')
        valid_session = type(session_id) is int and session_id > 0
        monitoring = invocation.get('monitoring')
        created = monitoring.get('created_at') if isinstance(monitoring, dict) else None
        valid_created = ((type(created) is int and created >= 0)
                         or (type(created) is float and created >= 0 and math.isfinite(created)))
        if (not valid_dispatch or not valid_session or not valid_created
                or invocation.get('human') is not False or invocation.get('consumed') is not False):
            malformed.append((session_id if valid_session else math.inf,
                              dispatch if isinstance(dispatch, str) else '', valid_dispatch))
        else:
            ordered.append((created, session_id, dispatch))
    if malformed:
        _, dispatch, valid = min(malformed)
        return {dispatch} if valid else set()
    return {min(ordered)[2]} if ordered else None


class CoordinatedQueue:
    def __init__(self, queue, sessions, lock):
        self._queue, self._sessions, self._lock = queue, sessions, lock

    def _reconcile(self):
        # list_all releases the SessionStore lock before the queue transaction.
        unpublished_holds = set()
        for run in self._sessions.list_all():
            if run.get('stop_id'):
                self._queue.cancel_run(run['run_id'], run['stop_id'])
            for attempt in run.get('superseded_attempts', []):
                if (attempt.get('reason') in ('participant_replacement', 'participant_skipped')
                        and (attempt.get('old_transport') or {}).get('resolved') is not True):
                    unpublished_holds.add(attempt['old_transport']['seat_identity_id'])
                if attempt.get('reason') == 'superseded_by_operator_recovery':
                    record = self._queue.hold_recovered(attempt['dispatch_id'], attempt['expected_identity_id'],
                                                        attempt['dispatch_id'], selected_cli=True)
                    if record is None and (attempt.get('selected_transport') or {}).get('resolved') is not True:
                        unpublished_holds.add(attempt['expected_identity_id'])
                self._queue.cancel_dispatch(attempt['dispatch_id'], attempt['request_id'])
        return unpublished_holds

    def enqueue(self, instance, envelope):
        with self._lock:
            runs = self._sessions.list_all()
            if any(run['run_id'] == envelope.get('run_id') and run.get('dispatch_eligible') is False for run in runs):
                raise QueueConflict('Stopped runs cannot enqueue further work.')
            if any(run['run_id'] == envelope.get('run_id') and
                   any(item['attempt_id'] == envelope.get('attempt_id') for item in run.get('superseded_attempts', []))
                   for run in runs):
                raise QueueConflict('Superseded attempts cannot enqueue further work.')
            return self._queue.enqueue(instance, envelope)

    def settle_old_transport(self, session_id, request_id, evidence):
        """Commit exact ledger completion before lifting a durable identity hold."""
        if type(session_id) is not int or session_id <= 0:
            raise QueueConflict('Session ID must be a positive integer.')
        with self._lock:
            session = self._sessions.get(session_id)
            transport, proof = self._sessions._old_transport_proof(session, request_id, evidence)
            if transport.get('resolved') is True:
                return session
            self._reconcile()
            owner = {'name': 'retired-participant', 'identity_id': proof['seat_identity_id']}
            records = self._queue.for_identity(owner)
            if any(record['state'] in ACTIVE and record['envelope']['dispatch_id'] != proof['dispatch_id']
                   for record in records):
                raise QueueBusy('Other work still owns this retired seat; it was not cancelled.')
            record = next((r for r in records if r['envelope']['dispatch_id'] == proof['dispatch_id']), None)
            if record and record['state'] == 'cancelling':
                self._queue.confirm_retired_exit(proof['dispatch_id'],
                    record.get('cancellation_id') or record.get('stop_id'), evidence=proof)
            return self._sessions.resolve_old_transport(session_id, request_id, proof)

    def claim(self, instance, consumer_id):
        with self._lock:
            unpublished_holds = self._reconcile()
            runs = self._sessions.list_all()
            blocked = {run['run_id'] for run in runs
                       if run.get('dispatch_eligible') is False and not run.get('stop_id')}
            identity = instance.get('identity_id') if isinstance(instance, dict) else None
            allowed = allowed_review_dispatch_ids(runs, identity)
            return self._queue.claim(instance, consumer_id, blocked_run_ids=blocked,
                                     blocked_identity_ids=unpublished_holds, allowed_dispatch_ids=allowed)

    def __getattr__(self, name):
        attribute = getattr(self._queue, name)
        if not callable(attribute):
            return attribute
        def coordinated(*args, **kwargs):
            with self._lock:
                return attribute(*args, **kwargs)
        return coordinated
