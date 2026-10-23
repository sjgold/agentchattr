"""Serialize durable run eligibility with queue mutations, without store nesting."""
from dispatch_queue import QueueConflict


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
