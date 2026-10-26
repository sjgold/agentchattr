"""Serialize durable run eligibility with queue mutations, without store nesting."""
import math
import logging
import re
from contextlib import contextmanager, nullcontext

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


log = logging.getLogger(__name__)


class CoordinatedQueue:
    def __init__(self, queue, sessions, lock):
        self._queue, self._sessions, self._lock = queue, sessions, lock
        self._channel_policy = None
        self._artifact_policy = None
        self._artifact_stop_reports = {}
        self._artifact_repair_cursor = 0
        self._artifact_repair_warning = None
        self._artifact_report_overflow = False

    def bind_artifact_policy(self, getter):
        if not callable(getter):
            raise ValueError('Artifact policy requires an explicit getter.')
        with self._lock:
            self._artifact_policy = getter

    def bind_channel_policy(self, policy_getter):
        """Bind before runtime publication; a failed getter keeps work held."""
        if not callable(policy_getter):
            raise ValueError('An explicit channel policy getter is required.')
        with self._lock:
            self._channel_policy = policy_getter

    @contextmanager
    def _channel_boundary(self):
        with self._lock:
            policy = self._channel_policy() if self._channel_policy else None
            with policy._boundary() if policy else nullcontext():
                yield policy

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
        self._repair_retained_artifact_stops()
        return unpublished_holds

    def enqueue(self, instance, envelope):
        with self._channel_boundary() as policy:
            if policy:
                policy.require_active(envelope.get('channel', 'general'))
            runs = self._sessions.list_all()
            if any(run['run_id'] == envelope.get('run_id') and run.get('dispatch_eligible') is False for run in runs):
                raise QueueConflict('Stopped runs cannot enqueue further work.')
            if any(run['run_id'] == envelope.get('run_id') and
                   any(item['attempt_id'] == envelope.get('attempt_id') for item in run.get('superseded_attempts', []))
                   for run in runs):
                raise QueueConflict('Superseded attempts cannot enqueue further work.')
            if 'purpose' in envelope:
                if envelope['purpose'] != 'artifact-v1' or self._artifact_policy is None:
                    raise QueueConflict('Artifact dispatch authority is unavailable.')
                # Engine/catalog held; no ledger transaction has begun.
                authority = self._artifact_policy()
                if authority is None:
                    raise QueueConflict('Artifact dispatch authority is unavailable.')
                authority.validate_enqueue(instance, envelope)
                return self._queue._enqueue_artifact_validated(instance, envelope)
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
        with self._channel_boundary() as policy:
            blocked_channels, active_channels = None, None
            if policy:
                value = policy.catalog.snapshot()
                blocked_channels = policy.catalog.blocked_names()
                active_channels = {name for name, state in value['channels'].items() if state == 'active'}
            unpublished_holds = self._reconcile()
            runs = self._sessions.list_all()
            blocked = {run['run_id'] for run in runs
                       if run.get('dispatch_eligible') is False and not run.get('stop_id')}
            identity = instance.get('identity_id') if isinstance(instance, dict) else None
            allowed = allowed_review_dispatch_ids(runs, identity)
            artifact_eligible = set()
            if self._artifact_policy is not None:
                try:
                    artifact_eligible = self._artifact_policy().eligible_dispatch_ids(instance,
                        stopped_source_runs={run['run_id'] for run in runs if run.get('stop_id')})
                    if (not isinstance(artifact_eligible, set) or any(
                            not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value)
                            for value in artifact_eligible)):
                        artifact_eligible = set()
                except Exception:
                    artifact_eligible = set()  # Owner failure closes new artifact claims only.
            # Existing owners must still inspect/release/cancel retained transport.
            for record in self._queue.for_identity(instance):
                if (record['state'] in ACTIVE and record['consumer_id'] == consumer_id
                        and record['envelope'].get('purpose') == 'artifact-v1'):
                    artifact_eligible.add(record['envelope']['dispatch_id'])
            return self._queue.claim(instance, consumer_id, blocked_run_ids=blocked,
                                     blocked_identity_ids=unpublished_holds, allowed_dispatch_ids=allowed,
                                     blocked_channel_names=blocked_channels, active_channel_names=active_channels,
                                     artifact_eligible=artifact_eligible)

    def repair_artifact_stops(self):
        from channel_lifecycle import ChannelUnavailable
        try:
            with self._channel_boundary():
                self._repair_retained_artifact_stops()
        except ChannelUnavailable:
            pass  # Optional startup repair stays idle under the global channel hold.

    def _repair_retained_artifact_stops(self):
        # One bounded retained-record pass, independent of historical run count.
        if self._artifact_policy is None:
            return
        try:
            policy = self._artifact_policy()
            if policy is None:
                return
            ids = [row['envelope']['artifact_request_id'] for row in self._queue.records()
                   if row['envelope'].get('purpose') == 'artifact-v1'
                   and row['state'] in ACTIVE | {'queued'}
                   and not (row.get('cancellation_id') or row.get('stop_id'))]
            if ids:
                start = self._artifact_repair_cursor % len(ids)
                ordered = ids[start:] + ids[:start]
                self._artifact_repair_cursor = (start + min(100, len(ids))) % len(ids)
                ids = ordered[:100]
            if not ids:
                return
            for effect in policy.fence_retained_source_requests(ids):
                report = self._artifact_stop_reports.get(effect['run_id'], {'dispatch_ids': [], 'warning': None})
                if effect['dispatch_id'] not in report['dispatch_ids']:
                    report['dispatch_ids'].append(effect['dispatch_id'])
                    report['confirmed'] = False
                self._remember_artifact_stop(effect['run_id'], report)
            policy.repair_cancel_fences(ids)
            self._artifact_repair_warning = None
        except Exception as error:
            self._artifact_repair_warning = self._artifact_failure_warning(error)
            log.warning('Artifact retained Stop repair held (%s)', type(error).__name__)

    def cancel_run(self, run_id, stop_id, *, fence_artifacts=False):
        from artifact_store import ArtifactUnavailable
        with self._channel_boundary():
            records = self._queue.cancel_run(run_id, stop_id)
            if not fence_artifacts or self._artifact_policy is None:
                return records
            try:
                policy = self._artifact_policy()
                if policy is None:
                    return records
                affected = policy.fence_source_requests(run_id)
                previous = self._artifact_stop_reports.get(run_id, {'dispatch_ids': [], 'warning': None})
                retained = [] if previous.get('confirmed') else previous['dispatch_ids']
                self._remember_artifact_stop(run_id, {
                    'dispatch_ids': list(dict.fromkeys(retained + list(affected['dispatch_ids']))),
                    'warning': previous['warning'] if retained else None})
                ids = affected['request_ids']
                for start in range(0, len(ids), 100):
                    policy.repair_cancel_fences(ids[start:start+100])
            except Exception as error:
                previous = self._artifact_stop_reports.get(run_id, {'dispatch_ids': []})
                self._remember_artifact_stop(run_id, dict(previous, warning=self._artifact_failure_warning(error)))
                log.warning('Artifact source Stop fencing held (%s)', type(error).__name__)
            # Artifact transport has its own status, never review stop receipts.
            return records

    @staticmethod
    def _artifact_failure_warning(error):
        from artifact_store import ArtifactUnavailable
        return 'storage_unavailable' if isinstance(error, (ArtifactUnavailable, OSError)) else 'artifact_fence_failed'

    def _remember_artifact_stop(self, run_id, report):
        # Observation cache only; persisted requests/transport remain authoritative.
        self._artifact_stop_reports.pop(run_id, None)
        self._artifact_stop_reports[run_id] = report
        while len(self._artifact_stop_reports) > 128:
            clean = next((key for key, value in self._artifact_stop_reports.items()
                          if (value.get('confirmed') and not value['warning']) or (not value['dispatch_ids'] and not value['warning'])), None)
            if clean is None:
                self._artifact_report_overflow = True
                clean = next(iter(self._artifact_stop_reports))
            self._artifact_stop_reports.pop(clean)

    def artifact_stop_status(self, run_id):
        with self._lock:
            report = self._artifact_stop_reports.get(run_id, {'dispatch_ids': [], 'warning': None})
            wanted = set(report['dispatch_ids'])
            overflow = 'unconfirmed_overflow' if self._artifact_report_overflow else None
            if not wanted:
                return {'warning': overflow or report['warning'] or self._artifact_repair_warning,
                        'unconfirmed_dispatch_ids': []}
            try:
                terminal = {'cancelled', 'released', 'failed', 'settled_recovered'}
                rows = {row['envelope']['dispatch_id']: row for row in self._queue.records()
                        if row['envelope']['dispatch_id'] in wanted}
                unconfirmed = sorted(identifier for identifier in wanted
                                     if identifier not in rows or rows[identifier]['state'] not in terminal)
                report['confirmed'] = not unconfirmed
                if report['confirmed']:
                    report['warning'] = None
                warning = report['warning'] or self._artifact_repair_warning or ('transport_unconfirmed' if unconfirmed else None)
            except Exception as error:
                report['confirmed'] = False
                warning = self._artifact_failure_warning(error)
                unconfirmed = sorted(wanted)
                log.warning('Artifact Stop status inspection held (%s)', type(error).__name__)
            return {'warning': overflow or warning, 'unconfirmed_dispatch_ids': unconfirmed}

    def __getattr__(self, name):
        attribute = getattr(self._queue, name)
        if not callable(attribute):
            return attribute
        def coordinated(*args, **kwargs):
            with self._lock:
                return attribute(*args, **kwargs)
        return coordinated
