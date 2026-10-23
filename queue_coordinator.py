"""Serialize durable run eligibility with queue mutations, without store nesting."""
from dispatch_queue import ACTIVE, QueueBusy, QueueConflict


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
            blocked = {run['run_id'] for run in self._sessions.list_all()
                       if run.get('dispatch_eligible') is False and not run.get('stop_id')}
            return self._queue.claim(instance, consumer_id, blocked_run_ids=blocked,
                                     blocked_identity_ids=unpublished_holds)

    def __getattr__(self, name):
        attribute = getattr(self._queue, name)
        if not callable(attribute):
            return attribute
        def coordinated(*args, **kwargs):
            with self._lock:
                return attribute(*args, **kwargs)
        return coordinated
