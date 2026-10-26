"""Artifact authority component under construction; no runtime/public binding."""
from copy import deepcopy
from functools import wraps
from dataclasses import dataclass, field
import hashlib
import json
import time
import uuid

from artifact_store import (ArtifactConflict, ArtifactUnavailable, ArtifactValidationError,
    LIVE, _audit, _hex, _path_key, _text, _observation, _label_text, _packet_validation_invocation)
from artifact_protocol import (validate_brief, validate_payload, MAX_RESULT_RECORD_BYTES,
                               MAX_ARTIFACT_BYTES, verify_result)
from artifact_delivery import ArtifactOutbox
from dispatch_queue import QueueAccessError
from launcher import LaunchError
from queue_coordinator import CoordinatedQueue, allowed_review_dispatch_ids
from channel_lifecycle import ChannelConflict
import runtime_protocol


class ArtifactAccessError(PermissionError):
    pass


class _ArtifactProducerUnavailable(ArtifactConflict):
    """Internal classification, with the same public conflict/error family."""


class ArtifactInputError(ArtifactValidationError):
    def __init__(self, diagnostic_id, *, received_truncated=False):
        super().__init__('Invalid Markdown. Correct the argument and submit again within the byte limit.')
        self.code = 'invalid_content'
        self.diagnostic_id = diagnostic_id
        self.received_truncated = received_truncated



class _ArtifactBoundaryHeld(ArtifactUnavailable):
    code = 'artifact_boundary_held'

    def __init__(self):
        super().__init__('Artifact diagnostic operation requires an independent authority boundary.')


def _frozen(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode('utf-8')


def _digest(value):
    return None if value is None else hashlib.sha256(_frozen(value)).hexdigest()


@dataclass(frozen=True)
class _DiagnosticClaim:
    state: str
    raw_state: str
    consumer_id: str | None
    envelope: bytes = field(repr=False)
    cancellation_id: str | None
    stop_id: str | None


@dataclass(frozen=True)
class _DiagnosticGuard:
    request_id: str | None
    state: str | None
    reason: str | None
    version_id: str | None
    channel: str | None
    audit_bytes: bytes | None = field(repr=False)
    mode: str
    queue: _DiagnosticClaim | None
    actor_identity_id: str | None
    lookup_request_id: str | None
    dispatch_id: str
    launch_attempt: str
    producer_bytes: bytes | None = field(repr=False)
    record_bytes: bytes | None = field(repr=False)
    record_digest: str | None
    saved_digest: str | None
    ack: bytes | None = field(repr=False)
    disposition: bytes | None = field(repr=False)
    brief_bytes: bytes | None = field(repr=False)


@dataclass(frozen=True)
class _DiagnosticContinuation:
    kind: str
    origin: str
    error_text: str | None = field(repr=False)


@dataclass(frozen=True)
class _DiagnosticIntent:
    request_id: str | None
    attempt_id: str
    dispatch_id: str
    actor_identity_id: str | None
    reason: str
    content: str | None = field(repr=False)
    attached_request_id: str | None
    received_truncated: bool
    now: float
    guard: _DiagnosticGuard
    continuation: _DiagnosticContinuation


class _DiagnosticRequired(Exception):
    def __init__(self, intent):
        super().__init__('Artifact diagnostic persistence is required.')
        self.intent = intent


@dataclass(frozen=True)
class _DiagnosticReceipt:
    intent: _DiagnosticIntent = field(repr=False)
    token: object = field(repr=False)
    payload: bytes = field(repr=False)


class _DiagnosticAuthorityChanged(ArtifactConflict):
    def __init__(self, *, cancel_winner=False):
        super().__init__('Artifact diagnostic authority changed before settlement.')
        self.cancel_winner = cancel_winner

def _packet_service_entry(method):
    @wraps(method)
    def invoke(self, *args, **kwargs):
        return self._packet_invocation(lambda: method(self, *args, **kwargs))
    return invoke


def active_artifact_instance(registry, identity):
    values = [row for row in registry.get_all().values()
              if row['identity_id'] == identity and row.get('state') == 'active']
    if len(values) != 1:
        raise ArtifactAccessError('Artifact producer identity is unavailable.')
    return values[0]


class ArtifactService:
    def _packet_invocation(self, step):
        with _packet_validation_invocation(self.store):
            return step()

    def _assert_independent_boundary(self):
        for owner in (self.channels.engine, self.channels.catalog, self.store):
            try:
                query = getattr(owner._lock, '_is_owned', None)
                if not callable(query):
                    raise _ArtifactBoundaryHeld()
                owned = query()
                if type(owned) is not bool or owned:
                    raise _ArtifactBoundaryHeld()
            except Exception:
                raise _ArtifactBoundaryHeld() from None

    def _run_diagnostic_operation(self, step, *, origin):
        if origin not in ('agent', 'worker', 'resume', 'startup'):
            raise ArtifactValidationError('Unknown diagnostic caller.')
        self._assert_independent_boundary()
        try:
            with self.channels._boundary():
                return step()
        except _DiagnosticRequired as required:
            intent = required.intent
        if intent.continuation.origin != origin:
            raise ArtifactValidationError('Diagnostic caller differs from its capture.')
        self._assert_independent_boundary()
        payload = self._persist_diagnostic_intent(intent)
        key = object()
        receipt = _DiagnosticReceipt(intent, key, payload)
        with self.channels._boundary():
            return self._settle_diagnostic_intent(intent, receipt, invocation_key=key)

    @staticmethod
    def _diagnostic_claim(record):
        if record is None:
            return None
        state = record['state']
        return _DiagnosticClaim('claimed_live' if state in ('dispatched', 'acknowledged', 'uncertain')
            and record['consumer_id'] else state, state, record['consumer_id'], _frozen(record['envelope']),
            record.get('cancellation_id'), record.get('stop_id'))

    def _capture_diagnostic(self, row, instance, reason, content, *, mode, origin,
                            kind='return_quarantine', payload=None, incoming=None,
                            transport=None, launch_attempt=None, error_text=None,
                            received_truncated=False):
        if row is not None:
            row = self.store.get_request(row['audit']['request_id'])
            audit = row['audit']
            claim = payload or audit
            lookup, dispatch, launch = audit['request_id'], audit['dispatch_id'], audit['producer']['launch_attempt']
            target = lookup
            if mode != 'fulfilled_ack':
                transport = self._queue_record(row)
        else:
            claim = payload
            lookup, dispatch = payload['request_id'], payload['dispatch_id']
            launch = launch_attempt or payload['launch_attempt']
            target = None
        key_request = claim.get('request_id') if row is not None else None
        attached = self.store._capture_diagnostic_attachment(key_request, claim['dispatch_id'])
        bounded, truncated = (None, False) if content is None else self._bounded(content)
        truncated = truncated or received_truncated
        if truncated:
            reason = 'response_too_large'
        box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / launch)
        saved = box.find(dispatch)
        ack, disposition = box.get_ack(dispatch), box.get_disposition(dispatch)
        proof = incoming if incoming is not None else saved
        brief = (self.briefs.get_private(audit['brief_id']) if row is not None
            and mode in ('live_claim', 'fulfilled_replay', 'fulfilled_ack', 'retained_recovery') else None)
        producer = None
        if mode == 'unmatched_saved_live':
            producer = self.seats.artifact_producer(self._instance(instance['identity_id']))
        guard = _DiagnosticGuard(target, row['state'] if row else None, row['reason'] if row else None,
            row['version_id'] if row else None, row['channel'] if row else None,
            _frozen(audit) if row else None, mode, self._diagnostic_claim(transport),
            instance.get('identity_id'), lookup, dispatch, launch, _frozen(producer) if producer else None,
            _frozen(proof) if proof is not None else None, _digest(proof), _digest(saved),
            _frozen(ack) if ack is not None else None, _frozen(disposition) if disposition is not None else None,
            _frozen(brief) if brief is not None else None)
        raise _DiagnosticRequired(_DiagnosticIntent(key_request, claim['attempt_id'], claim['dispatch_id'],
            instance.get('identity_id'), reason, bounded, attached, truncated, time.time(), guard,
            _DiagnosticContinuation(kind, origin, error_text)))

    def _persist_diagnostic_intent(self, intent):
        if (type(intent) is not _DiagnosticIntent or intent.guard.mode not in (
                'live_claim', 'reservation_resume', 'fulfilled_replay', 'fulfilled_ack', 'retained_recovery',
                'terminal_saved', 'unmatched_saved_live', 'unmatched_saved_retained') or
                intent.continuation.kind not in ('return_quarantine', 'raise_invalid_content', 'fail_source_packet',
                    'quarantine_invalid_response', 'resume_ack_conflict', 'startup_saved_disposition')):
            raise ArtifactValidationError('Invalid diagnostic intent.')
        result = self.store.diagnostic_store.record(intent.request_id, intent.attempt_id, intent.dispatch_id,
            reason=intent.reason, content=intent.content, actor_identity_id=intent.actor_identity_id,
            attached_request_id=intent.attached_request_id, now=intent.now)
        return _frozen(result)

    def _interrupted_diagnostic(self, intent, row, record):
        if (intent.continuation.origin == 'resume' and row is not None and row['state'] not in LIVE
                and row['state'] != intent.guard.state):
            settled = record is not None and record['state'] in ('cancelled', 'released', 'failed', 'settled_recovered')
            warning = None if row['state'] == 'cancelled' and settled else 'operator_recovery_required'
            return self._mutation(row, record, transport_settled=settled, warning=warning)
        previous = intent.guard.queue
        new_fence = (record is not None and (record.get('stop_id') or record.get('cancellation_id')) and
            (previous is None or record.get('stop_id') != previous.stop_id or
             record.get('cancellation_id') != previous.cancellation_id or
             (record['state'] in ('cancelling', 'cancelled') and record['state'] != previous.raw_state)))
        if intent.continuation.origin == 'resume' and row is not None and new_fence:
            settled = record['state'] in ('cancelled', 'released', 'failed', 'settled_recovered')
            return self._mutation(row, record, transport_settled=settled,
                warning=None if settled else 'operator_recovery_required')
        raise _DiagnosticAuthorityChanged(cancel_winner=row is not None and row['state'] == 'cancelled')

    def _verify_diagnostic_guard(self, intent):
        guard = intent.guard
        if guard.record_bytes is not None and hashlib.sha256(guard.record_bytes).hexdigest() != guard.record_digest:
            raise ArtifactConflict('Artifact diagnostic record proof differs.')
        row = self.store.get_request(guard.request_id) if guard.request_id is not None else None
        record = (self._queue_record(row) if row is not None and guard.mode != 'fulfilled_ack' else None)
        if guard.request_id is not None:
            if row is None:
                raise ArtifactConflict('Artifact diagnostic request is unavailable.')
            if (row['state'], row['reason'], row['version_id'], row['channel'], _frozen(row['audit'])) != (
                    guard.state, guard.reason, guard.version_id, guard.channel, guard.audit_bytes):
                return row, record, False
            current = self._diagnostic_claim(record)
            if guard.mode not in ('fulfilled_ack', 'terminal_saved'):
                if guard.mode == 'fulfilled_replay':
                    if current is None or guard.queue is None or (current.consumer_id, current.envelope) != (
                            guard.queue.consumer_id, guard.queue.envelope):
                        return row, record, False
                elif current != guard.queue:
                    # raw_state is observational; moves within the claimed-live class are legal.
                    if current is None or guard.queue is None or (
                            current.state, current.consumer_id, current.envelope, current.cancellation_id, current.stop_id) != (
                            guard.queue.state, guard.queue.consumer_id, guard.queue.envelope,
                            guard.queue.cancellation_id, guard.queue.stop_id):
                        return row, record, False
            audit = row['audit']
            instance = {'name': audit['producer']['name'], 'identity_id': guard.actor_identity_id}
            if guard.mode in ('live_claim', 'fulfilled_replay', 'reservation_resume'):
                self._producer(audit, self._instance(guard.actor_identity_id))
            elif guard.mode == 'retained_recovery':
                try:
                    self._producer(audit, self._instance(guard.actor_identity_id))
                except (ArtifactAccessError, ArtifactConflict):
                    if self._recovery_proof(audit).get('local_ended') is not True:
                        raise ArtifactConflict('Artifact recovered authority changed.') from None
            if guard.mode in ('live_claim', 'fulfilled_replay', 'reservation_resume', 'retained_recovery') and record is not None:
                self._envelope(row, instance, record['envelope'])
            if guard.mode in ('live_claim', 'reservation_resume', 'retained_recovery'):
                try:
                    self.channels.require_active(row['channel'])
                except ChannelConflict:
                    raise ArtifactConflict('Artifact channel is no longer active.') from None
            if guard.brief_bytes is not None:
                private = self.briefs.get_private(audit['brief_id'])
                if _frozen(private) != guard.brief_bytes:
                    raise ArtifactConflict('Artifact diagnostic brief authority changed.')
                if guard.record_bytes is not None:
                    verify_result(json.loads(guard.record_bytes), private['_artifact_seal']['seal_secret'])
            if guard.mode == 'fulfilled_ack':
                if self.store.get_version(row['version_id']) is None:
                    raise ArtifactUnavailable('Artifact committed version is unavailable.')
                if guard.queue is not None:
                    record = {'envelope': {'dispatch_id': guard.dispatch_id}, 'state': guard.queue.raw_state}
        else:
            if self.store.get_request(guard.lookup_request_id) is not None or self.store.get_request_by_dispatch(guard.dispatch_id) is not None:
                raise ArtifactConflict('Previously unmatched artifact now has a request.')
            if guard.mode == 'unmatched_saved_live':
                self._enabled()
                producer = self.seats.artifact_producer(self._instance(guard.actor_identity_id))
                if producer['available'] is not True or _frozen(producer) != guard.producer_bytes:
                    raise _ArtifactProducerUnavailable('Artifact producer binding is unavailable or changed.')
        box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / guard.launch_attempt)
        if guard.mode in ('terminal_saved', 'unmatched_saved_retained'):
            from runtime_adoption import _launch_record
            _launch_record(self.seats, box.runtime_path / 'config.json')
        saved = box.find(guard.dispatch_id)
        ack, disposition = box.get_ack(guard.dispatch_id), box.get_disposition(guard.dispatch_id)
        if (_digest(saved) != guard.saved_digest or
                (_frozen(ack) if ack is not None else None) != guard.ack or
                (_frozen(disposition) if disposition is not None else None) != guard.disposition):
            raise ArtifactConflict('Artifact diagnostic result or receipt changed.')
        return row, record, True

    def _settle_diagnostic_intent(self, intent, receipt, *, invocation_key):
        if (type(intent) is not _DiagnosticIntent or type(receipt) is not _DiagnosticReceipt
                or receipt.intent is not intent or receipt.token is not invocation_key):
            raise ArtifactConflict('Artifact diagnostic receipt does not belong to this invocation.')
        row, record, unchanged = self._verify_diagnostic_guard(intent)
        if not unchanged:
            return self._interrupted_diagnostic(intent, row, record)
        diagnostic = json.loads(receipt.payload)
        identifier = diagnostic.get('id') or diagnostic['latest_diagnostic_id']
        continuation = intent.continuation
        result = {'status': 'quarantined', 'diagnostic_id': identifier, 'reason': intent.reason,
            'request_terminal': continuation.kind == 'quarantine_invalid_response',
            'received_truncated': intent.received_truncated,
            'notice': 'response_body_not_retained' if intent.received_truncated else None}
        if continuation.kind == 'raise_invalid_content':
            raise ArtifactInputError(identifier, received_truncated=intent.received_truncated)
        if continuation.kind == 'fail_source_packet':
            self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                {'state': 'failed', 'reason': 'source_packet_unavailable'})
            self._fence(row)
            raise ArtifactUnavailable(continuation.error_text) from None
        if continuation.kind == 'quarantine_invalid_response':
            self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                {'state': 'quarantined', 'reason': 'invalid_response'})
            self._fence(row)
        elif continuation.kind == 'resume_ack_conflict' and continuation.origin == 'resume':
            return self._mutation(row, record, warning='operator_recovery_required',
                transport_settled=record is not None and record['state'] == 'settled_recovered')
        elif continuation.kind == 'startup_saved_disposition':
            box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / intent.guard.launch_attempt)
            box.quarantine(intent.guard.dispatch_id, identifier, intent.reason)
        return result

    def __init__(self, *, store, briefs, agents, seats, channels, registry):
        if (not isinstance(agents.queue, CoordinatedQueue) or agents.queue._lock is not channels.engine._lock
                or agents._registry is not registry or seats.registry is not registry
                or _path_key(store.root) != _path_key(briefs.root)
                or _path_key(store.root) != _path_key(seats.store.path.parent)):
            raise ArtifactValidationError('Artifact owners must share one configured boundary and data root.')
        self.store, self.briefs, self.agents = store, briefs, agents
        self.seats, self.channels, self.registry = seats, channels, registry

    @staticmethod
    def _enabled():
        if 'artifact-v1' not in runtime_protocol.SUPPORTED_CAPABILITIES:
            raise ArtifactConflict('Artifact authoring is not enabled for this wrapper implementation.')

    def _instance(self, identity):
        return active_artifact_instance(self.registry, identity)

    def _producer(self, audit, instance, *, _binding=None):
        self._enabled()
        producer = audit['producer']
        if not isinstance(instance, dict) or instance.get('identity_id') != producer['identity_id']:
            raise ArtifactAccessError('Artifact request belongs to another seat.')
        if _binding is None:
            live = self._instance(producer['identity_id'])
            current = self.seats.artifact_producer(live)
            provenance = self.seats.launch_provenance(live)
        else:
            live, current, provenance = _binding
        if (current['available'] is not True or current['identity_id'] != producer['identity_id']
                or current['capabilities'] != ['artifact-v1'] or current['adapter'] != producer['adapter']
                or any(current[key] != producer[key] for key in ('launch_attempt', 'launch_nonce', 'fingerprint'))):
            raise _ArtifactProducerUnavailable('Artifact producer binding is unavailable or changed.')
        if provenance is None:
            raise _ArtifactProducerUnavailable('Artifact producer launch is unverified.')
        model = provenance['effective']['seat'].get('model') or None
        reason = None if model else ('cli_model_unverified' if producer['adapter'] == 'cli' else 'provider_default')
        try:
            _label_text(live['name'])
            if model is not None:
                _label_text(model)
        except ArtifactValidationError:
            raise _ArtifactProducerUnavailable('Artifact producer labels exceed the supported grammar.') from None
        if producer['requested_model'] != model or producer['requested_model_reason'] != reason:
            raise ArtifactConflict('Requested model differs from the immutable producer launch.')
        return live

    def request_producer(self, identity):
        """Build the operator audit through the same binding checks as prepare."""
        self._enabled()
        live = self._instance(identity)
        current = self.seats.artifact_producer(live)
        provenance = self.seats.launch_provenance(live)
        if current['available'] is not True or provenance is None:
            raise _ArtifactProducerUnavailable('Artifact producer binding is unavailable or changed.')
        model = provenance['effective']['seat'].get('model') or None
        producer = {'name': live['name'], 'identity_id': identity, 'adapter': current['adapter'],
            **{key: current[key] for key in ('launch_attempt', 'launch_nonce', 'fingerprint')},
            'requested_model': model, 'requested_model_reason': None if model else
                ('cli_model_unverified' if current['adapter'] == 'cli' else 'provider_default'),
            'capabilities': ['artifact-v1']}
        self._producer({'producer': producer}, live, _binding=(live, current, provenance))
        return producer

    @staticmethod
    def _brief(audit):
        return validate_brief({**{key: deepcopy(audit[key]) for key in
            ('version', 'purpose', 'brief_id', 'request_id', 'lineage_id', 'attempt_id', 'dispatch_id',
             'expected_parent', 'instruction', 'format', 'source_run')},
            'packet_id': audit['scope']['packet_id'], 'scope_sha256': audit['scope']['sha256'],
            'input_revision': audit['scope']['input_revision'],
            'producer': {key: deepcopy(audit['producer'][key]) for key in
                ('identity_id', 'adapter', 'launch_attempt', 'launch_nonce', 'fingerprint')}})

    @staticmethod
    def _owner(audit):
        return {'dispatch_id': audit['dispatch_id'], 'seat_identity_id': audit['producer']['identity_id'],
            **{key: audit['producer'][key] for key in ('adapter', 'launch_attempt', 'launch_nonce', 'fingerprint')}}

    @staticmethod
    def _projection(row):
        value = deepcopy(row)
        value['audit']['producer'].pop('launch_nonce', None)
        return value

    def _mutation(self, row, record=None, *, admission=None, transport_settled=None, notice=None, warning=None):
        dispatch = None if record is None else {'dispatch_id': record['envelope']['dispatch_id'], 'state': record['state']}
        return {'request': self._projection(row), 'dispatch': dispatch, 'admission': admission,
                'transport_settled': transport_settled, 'notice': notice, 'warning': warning}

    @_packet_service_entry
    def prepare_request(self, audit, packet, request_id):
        try:
            audit = _audit(audit)
        except ArtifactValidationError:
            # An invalid configured model must have the producer refusal, even
            # though the common audit validator runs before the live binding.
            producer = audit.get('producer') if isinstance(audit, dict) else None
            if isinstance(producer, dict):
                try:
                    for key in ('name', 'requested_model', 'requested_model_reason'):
                        if producer.get(key) is not None:
                            _label_text(producer[key])
                except ArtifactValidationError:
                    raise _ArtifactProducerUnavailable('Artifact producer labels exceed the supported grammar.') from None
            raise
        if request_id != audit['request_id']:
            raise ArtifactValidationError('Artifact request id differs from its frozen audit.')
        with self.channels._boundary():
            existing = self.store.get_request(request_id)
            if existing is not None:
                return self._mutation(self.store.reserve_request(audit, request_id))
            self.channels.require_active(audit['original_channel'])
            live = self._producer(audit, self._instance(audit['producer']['identity_id']))
            if self.store.put_packet(request_id, packet) != audit['scope']:
                raise ArtifactConflict('Artifact source packet differs from its frozen request.')
            self.store.reserve_request(audit, request_id)
            self.briefs.put(self._brief(audit), owner=self._owner(audit))
            record = self.agents.trigger_identity_sync(live['identity_id'], dispatch_id=audit['dispatch_id'],
                channel=audit['original_channel'], purpose='artifact-v1', artifact_request_id=request_id,
                artifact_attempt_id=audit['attempt_id'], artifact_brief_id=audit['brief_id'],
                artifact_scope_sha256=audit['scope']['sha256'])
            allowed = allowed_review_dispatch_ids(self.channels.engine._store.list_all(), live['identity_id'])
            reason = 'queued_behind_review' if allowed is not None and audit['dispatch_id'] not in allowed else 'queued'
            row = self.store.set_attempt_state(request_id, audit['attempt_id'], 'prepared',
                                               {'state': 'queued', 'reason': reason})
            return self._mutation(row, record)

    def _envelope(self, row, instance, envelope):
        audit = row['audit']
        expected = {'purpose': 'artifact-v1', 'dispatch_id': audit['dispatch_id'],
            'artifact_request_id': audit['request_id'], 'artifact_attempt_id': audit['attempt_id'],
            'artifact_brief_id': audit['brief_id'], 'artifact_scope_sha256': audit['scope']['sha256'],
            'channel': audit['original_channel']}
        if (instance.get('identity_id') != audit['producer']['identity_id']
                or any(envelope.get(key) != value for key, value in expected.items())
                or envelope.get('target_identity_id', audit['producer']['identity_id']) != audit['producer']['identity_id']):
            raise ArtifactConflict('Artifact queue envelope differs from its frozen authority.')

    def validate_enqueue(self, instance, envelope):
        # Called inside the coordinator boundary BEFORE its raw ledger call.
        self._enabled()
        row = self.store.get_request(envelope.get('artifact_request_id'))
        if row is None or row['state'] not in LIVE:
            raise ArtifactConflict('Artifact request is not live for enqueue.')
        self.channels.require_active(row['channel'])
        self._producer(row['audit'], instance)
        self._envelope(row, instance, envelope)
        private = self.briefs.get_private(row['audit']['brief_id'])
        if {key: value for key, value in private.items() if key != '_artifact_seal'} != self._brief(row['audit']):
            raise ArtifactUnavailable('Artifact private brief differs from its request.')
        self.store.get_packet(row['audit']['scope']['packet_id'])

    def eligible_dispatch_ids(self, instance):
        result = set()
        bindings = {}  # Per-call observations only; no eligibility survives this call.
        if not isinstance(instance, dict):
            return result
        try:
            self._enabled()
            for channel in self.store.channel_names():
                for pending in self.store.pending(channel):
                    row = self.store.get_request(pending['request_id'])
                    if row['audit']['producer']['identity_id'] != instance.get('identity_id'):
                        continue
                    try:
                        self.channels.require_active(row['channel'])
                        producer = row['audit']['producer']
                        key = tuple(producer[field] for field in ('identity_id', 'launch_attempt', 'launch_nonce', 'fingerprint'))
                        if key not in bindings:
                            live = self._instance(producer['identity_id'])
                            bindings[key] = (live, self.seats.artifact_producer(live), self.seats.launch_provenance(live))
                        self._producer(row['audit'], instance, _binding=bindings[key])
                        result.add(row['audit']['dispatch_id'])
                    except Exception:
                        continue  # Claim reads metadata; the brief gate checks its packet.
        except Exception:
            return set()
        return result

    def _context(self, brief_id, instance, *, replay=False):
        if not isinstance(instance, dict) or not instance.get('identity_id'):
            raise ArtifactAccessError('An authenticated artifact producer is required.')
        private = self.briefs.get_private(brief_id)
        row = self.store.get_request(private['request_id'])
        if row is None:
            raise ArtifactConflict('Artifact request is unknown.')
        live = self._producer(row['audit'], instance)
        if ({key: value for key, value in private.items() if key != '_artifact_seal'} != self._brief(row['audit'])
                or private['_artifact_seal']['owner'] != self._owner(row['audit'])):
            raise ArtifactUnavailable('Artifact brief no longer matches its immutable request.')
        try:
            record = self.agents.queue.owned(live, row['audit']['dispatch_id'])
        except QueueAccessError:
            raise ArtifactAccessError('Artifact dispatch belongs to another seat.') from None
        self._envelope(row, live, record['envelope'])
        if replay and row['state'] == 'fulfilled':
            if not record['consumer_id']:
                raise ArtifactConflict('Artifact ACK has no original dispatch claim.')
            return private, row, live, record
        if row['state'] not in LIVE:
            raise ArtifactConflict('Artifact request is terminal.')
        self.channels.require_active(row['channel'])
        if not record['consumer_id'] or record['state'] not in ('dispatched', 'acknowledged', 'uncertain'):
            raise ArtifactConflict('Artifact dispatch has not been claimed or is cancelling.')
        return private, row, live, record

    @staticmethod
    def _bounded(content):
        if not isinstance(content, str):
            raise ArtifactValidationError('Artifact diagnostic content must be text.')
        if len(content) > MAX_RESULT_RECORD_BYTES:
            return None, True
        total = 0
        for start in range(0, len(content), 16384):
            total += len(content[start:start + 16384].encode('utf-8', errors='surrogatepass'))
            if total > MAX_RESULT_RECORD_BYTES:
                return None, True
        return content, False

    def _diagnostic(self, row, instance, reason, content, *, terminal=False, payload=None,
                    mode=None, origin='agent', kind='return_quarantine', incoming=None,
                    transport=None, received_truncated=False, error_text=None):
        mode = mode or ('fulfilled_replay' if row['state'] == 'fulfilled' else 'live_claim')
        self._capture_diagnostic(row, instance, reason, content, mode=mode, origin=origin,
            kind=kind, payload=payload, incoming=incoming, transport=transport,
            error_text=error_text, received_truncated=received_truncated)

    def _fence(self, row):
        request = row['audit']['request_id']
        cancellation = uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:artifact-v1:cancel:' + request).hex
        return self.agents.queue.cancel_dispatch(row['audit']['dispatch_id'], cancellation)

    def _packet(self, row, instance, *, mode='live_claim', origin='agent'):
        try:
            return self.store.get_packet(row['audit']['scope']['packet_id'])
        except ArtifactUnavailable as error:
            self._diagnostic(row, instance, 'source_packet_unavailable', None, terminal=True,
                mode=mode, origin=origin, kind='fail_source_packet', error_text=str(error))

    def _activate(self, row):
        return self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                                             {'state': 'active', 'reason': None})

    @_packet_service_entry
    def get_brief(self, brief_id, instance):
        return self._run_diagnostic_operation(lambda: self._get_brief_locked(brief_id, instance), origin='agent')

    def _get_brief_locked(self, brief_id, instance):
        private, row, live, _ = self._context(brief_id, instance)
        packet = self._packet(row, live)
        self._activate(row)
        public = {key: deepcopy(value) for key, value in private.items() if key != '_artifact_seal'}
        public['producer'].pop('launch_nonce')
        return {'brief': public, 'packet': packet}

    @_packet_service_entry
    def get_delivery(self, brief_id, instance):
        return self._run_diagnostic_operation(lambda: self._get_delivery_locked(brief_id, instance), origin='worker')

    def _get_delivery_locked(self, brief_id, instance):
        with self.channels._boundary():
            private, row, live, record = self._context(brief_id, instance)
            if row['audit']['producer']['adapter'] != 'openai-compatible':
                raise ArtifactAccessError('Private artifact delivery is limited to its managed API worker.')
            packet = self._packet(row, live, origin='worker')
            self._activate(row)
            return {'brief': {key: deepcopy(value) for key, value in private.items() if key != '_artifact_seal'},
                'packet': packet, 'seal_secret': private['_artifact_seal']['seal_secret'],
                'result_owner': deepcopy(private['_artifact_seal']['owner']), 'consumer_id': record['consumer_id']}

    @_packet_service_entry
    def get_parent(self, brief_id, instance):
        """Read only this claimed request's immutable parent; never activate work."""
        with self.channels._boundary():
            return self._get_parent_locked(brief_id, instance)

    def _get_parent_locked(self, brief_id, instance):
        _, row, _, _ = self._context(brief_id, instance)
        self.store.get_packet(row['audit']['scope']['packet_id'])
        expected = row['audit']['expected_parent']
        if expected is None:
            return {'parent': None}
        saved = self.store.get_version(expected['version_id'])
        if saved is None:
            raise ArtifactUnavailable('Assigned artifact parent is unavailable.')
        metadata, text = saved['metadata'], saved['markdown']
        raw = text.encode('utf-8')
        if (metadata['id'] != expected['version_id'] or metadata['sequence'] != expected['sequence']
                or metadata['sha256'] != expected['sha256'] or len(raw) != metadata['byte_length']
                or len(raw) > MAX_ARTIFACT_BYTES or hashlib.sha256(raw).hexdigest() != metadata['sha256']):
            raise ArtifactUnavailable('Assigned artifact parent is unavailable.')
        return {'parent': {**deepcopy(expected), 'byte_length': len(raw), 'markdown': text}}

    @_packet_service_entry
    def get_brief_context(self, brief_id, instance):
        return self._run_diagnostic_operation(lambda: self._get_brief_context_locked(brief_id, instance), origin='agent')

    def _get_brief_context_locked(self, brief_id, instance):
        with self.channels._boundary():
            parent = self._get_parent_locked(brief_id, instance)
            return {**self._get_brief_locked(brief_id, instance), **parent}

    @staticmethod
    def _ack(metadata):
        return {'status': 'admitted', 'event_id': metadata['dispatch_id'], 'request_id': metadata['request_id'],
                'version_id': metadata['id'], 'sha256': metadata['sha256']}

    @_packet_service_entry
    def submit_cli(self, brief_id, markdown, instance):
        return self._run_diagnostic_operation(lambda: self._submit_cli_locked(brief_id, markdown, instance), origin='agent')

    def _submit_cli_locked(self, brief_id, markdown, instance):
        with self.channels._boundary():
            private, row, live, record = self._context(brief_id, instance, replay=True)
            audit = row['audit']
            if audit['producer']['adapter'] != 'cli':
                raise ArtifactAccessError('CLI submission cannot provide an API model observation.')
            box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
            if row['state'] == 'fulfilled':
                saved = self.store.get_version(row['version_id'])
                if saved is None:
                    raise ArtifactUnavailable('Artifact version is unavailable.')
                if markdown != saved['markdown']:
                    return self._diagnostic(row, live, 'conflicting_duplicate', markdown)
                prior = box.find(audit['dispatch_id'])
                if prior is None:
                    raise ArtifactUnavailable('Artifact result authority is missing.')
                verify_result(prior, private['_artifact_seal']['seal_secret'])
                box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
                return self._ack(saved['metadata'])
            self._packet(row, live)
            row = self._activate(row)
            try:
                _text(markdown, MAX_ARTIFACT_BYTES)
            except ArtifactValidationError:
                self._diagnostic(row, live, 'invalid_content', markdown, kind='raise_invalid_content')
            prior = box.find(audit['dispatch_id'])
            if prior is not None and prior['payload']['markdown'] != markdown:
                return self._diagnostic(row, live, 'conflicting_duplicate', markdown)
            if prior is None:
                payload = {**{key: deepcopy(audit[key]) for key in
                    ('version', 'purpose', 'request_id', 'attempt_id', 'brief_id', 'lineage_id', 'dispatch_id', 'expected_parent')},
                    'result_id': audit['dispatch_id'], 'scope_sha256': audit['scope']['sha256'],
                    **{key: value for key, value in self._owner(audit).items() if key not in ('adapter', 'dispatch_id')},
                    'consumer_id': record['consumer_id'], 'kind': 'artifact', 'markdown': markdown,
                    'observation': {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'},
                    'created_at': time.time()}
                prior = box.save(payload, private['_artifact_seal']['seal_secret'])
            verified = verify_result(prior, private['_artifact_seal']['seal_secret'])
            metadata = self.store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
                verified['markdown'], verified['observation'])
            box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
            return self._ack(metadata)

    @staticmethod
    def _payload_reason(payload, row, record):
        audit = row['audit']
        for field, expected, reason in (
            ('dispatch_id', audit['dispatch_id'], 'wrong_dispatch'),
            ('request_id', audit['request_id'], 'wrong_scope'),
            ('attempt_id', audit['attempt_id'], 'wrong_attempt'),
            ('brief_id', audit['brief_id'], 'wrong_brief'),
            ('lineage_id', audit['lineage_id'], 'wrong_scope'),
            ('scope_sha256', audit['scope']['sha256'], 'wrong_scope'),
            ('expected_parent', audit['expected_parent'], 'wrong_parent'),
            ('seat_identity_id', audit['producer']['identity_id'], 'wrong_identity'),
            ('consumer_id', record['consumer_id'], 'wrong_identity')):
            if payload[field] != expected:
                return reason
        if any(payload[field] != audit['producer'][field] for field in ('launch_attempt', 'launch_nonce', 'fingerprint')):
            return 'superseded'
        return None

    @_packet_service_entry
    def admit_saved(self, record, instance):
        return self._run_diagnostic_operation(lambda: self._admit_saved_locked(record, instance, origin='worker'), origin='worker')

    def _admit_saved_locked(self, record, instance, *, origin='worker'):
        payload = validate_payload(record.get('payload') if isinstance(record, dict) else None)
        with self.channels._boundary():
            self._enabled()
            if not isinstance(instance, dict) or not instance.get('identity_id'):
                raise ArtifactAccessError('An authenticated artifact producer is required.')
            row = self.store.get_request_by_dispatch(payload['dispatch_id']) or self.store.get_request(payload['request_id'])
            if row is None:
                live = self._instance(instance['identity_id'])
                if self.seats.artifact_producer(live)['available'] is not True:
                    raise ArtifactAccessError('Managed artifact producer binding is required.')
                self._capture_diagnostic(None, live, 'unmatched_saved_result', payload['markdown'],
                    mode='unmatched_saved_live', origin=origin, payload=payload, incoming=record)
            private, row, live, owned = self._context(row['audit']['brief_id'], instance, replay=True)
            payload = verify_result(record, private['_artifact_seal']['seal_secret'])
            reason = self._payload_reason(payload, row, owned)
            if reason:
                return self._diagnostic(row, live, reason, payload['markdown'], payload=payload, incoming=record, origin=origin)
            try:
                _observation(payload['observation'], row['audit']['producer']['adapter'])
            except ArtifactValidationError:
                return self._diagnostic(row, live, 'invalid_response', payload['markdown'], payload=payload, incoming=record, origin=origin)
            audit = row['audit']
            box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
            if row['state'] == 'fulfilled':
                saved = self.store.get_version(row['version_id'])
                if saved is None:
                    raise ArtifactUnavailable('Artifact version is unavailable.')
                if saved['markdown'] != payload['markdown']:
                    return self._diagnostic(row, live, 'conflicting_duplicate', payload['markdown'], payload=payload, incoming=record, origin=origin)
                prior = box.find(audit['dispatch_id'])
                if prior is None:
                    raise ArtifactUnavailable('Artifact result authority is missing.')
                verify_result(prior, private['_artifact_seal']['seal_secret'])
                box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
                return self._ack(saved['metadata'])
            self._packet(row, live, origin=origin)
            row = self._activate(row)
            prior = box.find(audit['dispatch_id'])
            if prior is not None:
                verified = verify_result(prior, private['_artifact_seal']['seal_secret'])
                if self._payload_reason(verified, row, owned):
                    raise ArtifactUnavailable('Stored artifact result scope differs from its request.')
                if verified['markdown'] != payload['markdown']:
                    return self._diagnostic(row, live, 'conflicting_duplicate', payload['markdown'], payload=payload, incoming=record, origin=origin)
                payload = verified  # First trusted observation/time remains immutable.
            else:
                box.save(payload, private['_artifact_seal']['seal_secret'])
            metadata = self.store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
                payload['markdown'], payload['observation'])
            box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
            return self._ack(metadata)

    @_packet_service_entry
    def reject_response(self, brief_id, content, instance, *, received_truncated=False):
        return self._run_diagnostic_operation(lambda: self._reject_response_locked(brief_id, content, instance, received_truncated=received_truncated), origin='worker')

    def _reject_response_locked(self, brief_id, content, instance, *, received_truncated=False):
        if (type(received_truncated) is not bool or
                not ((isinstance(content, str) and not received_truncated) or
                     (content is None and received_truncated))):
            raise ArtifactValidationError('Artifact rejection requires text or an explicit omitted body.')
        with self.channels._boundary():
            _, row, live, _ = self._context(brief_id, instance)
            if row['audit']['producer']['adapter'] != 'openai-compatible':
                raise ArtifactAccessError('API response rejection requires its managed API producer.')
            self._packet(row, live, origin='worker')
            row = self._activate(row)
            self._diagnostic(row, live, 'response_too_large' if received_truncated else 'invalid_response',
                content, terminal=True, origin='worker', kind='quarantine_invalid_response',
                received_truncated=received_truncated)

    def _queue_record(self, row):
        audit = row['audit']
        try:
            return self.agents.queue.owned({'name': audit['producer']['name'],
                'identity_id': audit['producer']['identity_id']}, audit['dispatch_id'])
        except QueueAccessError:
            return None

    def validate_queued_cancellation(self, request_id):
        """Pure queued-only operator predicate; never activates, fences or writes."""
        with self.channels._boundary():
            row = self.store.get_request(request_id)
            if row is None or row['state'] not in ('prepared', 'queued', 'cancelled'):
                raise ArtifactConflict('Artifact request is not eligible for queued cancellation.')
            record = self._queue_record(row)
            if record is None:
                if row['state'] != 'prepared':
                    raise ArtifactConflict('Artifact queued transport is unavailable.')
            else:
                if record['state'] != 'queued':
                    raise ArtifactConflict('Artifact transport is already claimed or settled.')
                self._envelope(row, {'identity_id': row['audit']['producer']['identity_id']}, record['envelope'])
            return self._projection(row)

    def request_status(self, request_id):
        _hex(request_id)
        with self.channels._boundary():
            row = self.store.get_request(request_id)
            if row is None:
                return None
            record = self._queue_record(row) if row['state'] in LIVE else None
            return {'request': self._projection(row),
                    'needs_resume': row['state'] in LIVE and record is None}

    def cancel_request(self, request_id):
        with self.channels._boundary():
            row = self.store.get_request(request_id)
            if row is None:
                raise ArtifactConflict('Artifact request is unknown.')
            previous = row['state']
            if row['state'] == 'cancelled':
                if row['reason'] != 'operator_cancelled':
                    raise ArtifactConflict('Artifact cancellation reason is already settled.')
            elif row['state'] not in LIVE:
                raise ArtifactConflict('A terminal artifact request cannot be cancelled again.')
            else:
                row = self.store.set_attempt_state(request_id, row['audit']['attempt_id'], row['state'],
                    {'state': 'cancelled', 'reason': 'operator_cancelled'})
            try:
                record = self._fence(row)
                settled = ((record is None and previous == 'prepared') or
                    (record is not None and record['state'] in ('cancelled', 'released', 'failed', 'settled_recovered')))
                return self._mutation(row, record, transport_settled=settled,
                    warning=None if settled else 'transport_unconfirmed')
            except (OSError, ValueError, LaunchError):
                return self._mutation(row, transport_settled=False, warning='transport_unconfirmed')

    def fence_source_requests(self, run_id):
        _hex(run_id)
        requests, dispatches = [], []
        with self.channels._boundary():
            for channel in self.store.channel_names():
                for pending in self.store.pending(channel):
                    row = self.store.get_request(pending['request_id'])
                    source = row['audit']['source_run'] or {}
                    if (source.get('run_id') != run_id or source.get('state_at_request') in
                            ('complete', 'stopping', 'stopped', 'unresolved')):
                        continue  # An explicitly post-run document is independent of that run's Stop.
                    self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                        {'state': 'cancelled', 'reason': 'source_stopped'})
                    requests.append(row['audit']['request_id'])
                    dispatches.append(row['audit']['dispatch_id'])
        # A prior Stop may have durably cancelled the row but failed its fence.
        # Retained transport records keep that exact source cancellation retryable.
        with self.channels._boundary():
            for record in self.agents.queue.records():
                envelope = record['envelope']
                if envelope.get('purpose') != 'artifact-v1':
                    continue
                row = self.store.get_request(envelope.get('artifact_request_id'))
                if (row is not None and row['state'] == 'cancelled' and row['reason'] == 'source_stopped'
                        and (row['audit']['source_run'] or {}).get('run_id') == run_id
                        and row['audit']['request_id'] not in requests):
                    requests.append(row['audit']['request_id']); dispatches.append(envelope['dispatch_id'])
        return {'request_ids': requests, 'dispatch_ids': dispatches}

    def repair_cancel_fences(self, request_ids=None, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ArtifactValidationError('Artifact repair limit must be between 1 and 100.')
        with self.channels._boundary():
            if request_ids is None:
                request_ids = []
                for record in self.agents.queue.records():
                    if record['envelope'].get('purpose') != 'artifact-v1':
                        continue
                    row = self.store.get_request_by_dispatch(record['envelope']['dispatch_id'])
                    if row is not None and row['state'] == 'cancelled':
                        request_ids.append(row['audit']['request_id'])
            rows = [self.store.get_request(_hex(identifier)) for identifier in request_ids]
            rows = [row for row in rows if row is not None and row['state'] == 'cancelled']
            repaired, unconfirmed = [], []
            for row in rows[:limit]:
                try:
                    record = self._fence(row)
                    if record is None or record['state'] in ('cancelled', 'released', 'failed', 'settled_recovered'):
                        repaired.append(row['audit']['request_id'])
                    else:
                        unconfirmed.append(row['audit']['dispatch_id'])
                except (OSError, ValueError, LaunchError):
                    unconfirmed.append(row['audit']['dispatch_id'])
            return {'repaired': repaired, 'unconfirmed': unconfirmed, 'remaining': max(0, len(rows) - limit)}

    def _recovery_proof(self, audit):
        """Use the existing exact-launch exit verifier, never infer exit from release."""
        from runtime_adoption import _candidate
        producer = audit['producer']
        try:
            with self.seats.lock:
                item = _candidate(self.seats, self.store.root / 'api_seat_runtime' /
                                  producer['launch_attempt'] / 'config.json')
                identity = item['identity']
                if (identity['attempt'] != producer['launch_attempt']
                        or identity['launch_nonce'] != producer['launch_nonce']
                        or identity['fingerprint'] != producer['fingerprint']
                        or item['effective']['seat']['adapter'] != producer['adapter']
                        or 'artifact-v1' not in item['snapshot'].get('wrapper_protocol', {}).get('capabilities', [])):
                    return {'local_ended': False}
                effective = self.seats._provenance_effective(item['effective'])
                model = effective['seat'].get('model') or None
                reason = None if model else ('cli_model_unverified' if producer['adapter'] == 'cli' else 'provider_default')
                if model != producer['requested_model'] or reason != producer['requested_model_reason']:
                    return {'local_ended': False}
                provenance = {'key': item['key'], 'launch_attempt': producer['launch_attempt'],
                              'identity_id': producer['identity_id'], 'effective': effective}
                hashed = effective
                base = item['snapshot'].get('context_base_effective')
                if base:
                    provenance['fresh_base_effective'] = self.seats._provenance_effective(base)
                    hashed = {'effective': effective, 'fresh_base_effective': provenance['fresh_base_effective']}
                provenance['fingerprint'] = hashlib.sha256(json.dumps(hashed, sort_keys=True).encode('utf-8')).hexdigest()
                return self.seats.participant_exit_proof(provenance, audit['dispatch_id'])
        except (OSError, ValueError, KeyError, TypeError):
            return {'local_ended': False}

    def _resume_recovered(self, row, transport, *, origin='resume'):
        self._enabled()
        audit, producer = row['audit'], row['audit']['producer']
        if (row['state'] != 'active' or transport is None or transport['state'] not in
                ('released', 'failed', 'settled_recovered') or not transport['consumer_id']
                or transport.get('cancellation_id') or transport.get('stop_id')):
            raise ArtifactConflict('Saved artifact recovery requires an active request and retained claim.')
        instance = {'name': producer['name'], 'identity_id': producer['identity_id']}
        self._envelope(row, instance, transport['envelope'])
        private = self.briefs.get_private(audit['brief_id'])
        if ({key: value for key, value in private.items() if key != '_artifact_seal'} != self._brief(audit)
                or private['_artifact_seal']['owner'] != self._owner(audit)):
            raise ArtifactUnavailable('Artifact recovered brief authority is unavailable.')
        box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / producer['launch_attempt'])
        if box.get_disposition(audit['dispatch_id']) is not None:
            raise ArtifactConflict('Saved artifact result has a terminal quarantine disposition.')
        saved = box.find(audit['dispatch_id'])
        if saved is None:
            raise ArtifactConflict('No saved artifact result is available for this dispatch.')
        payload = verify_result(saved, private['_artifact_seal']['seal_secret'])
        if self._payload_reason(payload, row, transport) is not None:
            raise ArtifactConflict('Saved artifact result differs from its retained claim.')
        _observation(payload['observation'], producer['adapter'])
        proof = self._recovery_proof(audit)
        try:
            self._producer(audit, self._instance(producer['identity_id']))
        except (ArtifactAccessError, ArtifactConflict):
            if proof.get('local_ended') is not True:
                raise ArtifactConflict('Saved artifact producer is neither verified live nor proven ended.') from None
        self.channels.require_active(row['channel'])
        self._packet(row, instance, mode='retained_recovery', origin=origin)
        metadata = self.store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
                                             payload['markdown'], payload['observation'])
        box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
        settled = transport['state'] == 'settled_recovered'
        if not settled and proof.get('local_ended') is True:
            try:
                if producer['adapter'] == 'cli':
                    self.agents.queue.hold_recovered(audit['dispatch_id'], producer['identity_id'],
                                                     audit['dispatch_id'], selected_cli=True)
                transport = self.agents.queue.settle_recovered(audit['dispatch_id'], producer['identity_id'], evidence=proof)
                settled = transport['state'] == 'settled_recovered' or transport.get('recovery_hold', {}).get('cleared') is True
            except (OSError, ValueError, PermissionError):
                settled = False  # Content committed; this separate transport effect is unconfirmed.
        return self._mutation(self.store.get_request(audit['request_id']), transport,
            admission=self._ack(metadata), transport_settled=settled,
            notice={'id': uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:artifact-v1:recovered:' + audit['dispatch_id']).hex,
                    'code': 'admitted_from_recovered_result'}, warning=None if settled else 'transport_unconfirmed')

    def _repair_fulfilled_ack(self, row):
        return self._packet_invocation(lambda: self._run_diagnostic_operation(
            lambda: self._repair_fulfilled_ack_locked(row, origin='worker'), origin='worker'))

    def _repair_fulfilled_ack_locked(self, row, *, origin, transport=None):
        """Bookkeeping only for content already committed, independent of worker life."""
        audit = row['audit']
        if row['state'] != 'fulfilled':
            raise ArtifactConflict('Only a fulfilled artifact has an admission ACK to repair.')
        private = self.briefs.get_private(audit['brief_id'])
        if ({key: value for key, value in private.items() if key != '_artifact_seal'} != self._brief(audit)
                or private['_artifact_seal']['owner'] != self._owner(audit)):
            raise ArtifactConflict('Artifact ACK brief authority differs from its request.')
        box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
        if box.get_disposition(audit['dispatch_id']) is not None:
            raise ArtifactConflict('Artifact result already has a quarantine disposition.')
        record = box.get(audit['dispatch_id'])
        payload = verify_result(record, private['_artifact_seal']['seal_secret'])
        if self._payload_reason(payload, row, {'consumer_id': payload['consumer_id']}) is not None:
            raise ArtifactConflict('Artifact ACK result differs from its frozen request.')
        saved = self.store.get_version(row['version_id'])
        if saved is None:
            raise ArtifactUnavailable('Artifact committed version is unavailable.')
        raw = payload['markdown'].encode('utf-8')
        metadata = saved['metadata']
        if (payload['markdown'] != saved['markdown'] or len(raw) != metadata['byte_length']
                or hashlib.sha256(raw).hexdigest() != metadata['sha256']):
            return self._diagnostic(row, {'identity_id': audit['producer']['identity_id']},
                                    'conflicting_duplicate', payload['markdown'], mode='fulfilled_ack', origin=origin,
                                    kind='resume_ack_conflict', incoming=record, transport=transport)
        if payload['observation'] != metadata['provenance']['observation']:
            raise ArtifactConflict('Artifact ACK model observation differs from its committed version.')
        box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
        return self._ack(metadata)

    def _settle_empty_transport(self, row, transport):
        """A finished delivery without saved content cannot retain a pending slot."""
        if transport is None or transport['state'] not in ('released', 'failed', 'settled_recovered'):
            return None
        audit = row['audit']
        self._envelope(row, {'identity_id': audit['producer']['identity_id']}, transport['envelope'])
        if not transport['consumer_id'] or transport.get('cancellation_id') or transport.get('stop_id'):
            raise ArtifactConflict('Terminal artifact delivery has an unresolved claim or cancellation fence.')
        box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
        if box.find(audit['dispatch_id']) is not None:
            return None  # Saved content retains the separate operator-recovery path.
        if box.get_disposition(audit['dispatch_id']) is not None:
            raise ArtifactConflict('Artifact delivery has a retained quarantine disposition.')
        return self.store.set_attempt_state(audit['request_id'], audit['attempt_id'], row['state'],
                                            {'state': 'failed', 'reason': 'delivery_unconfirmed'})

    @_packet_service_entry
    def resume_request(self, request_id, *, recover_saved=False):
        return self._run_diagnostic_operation(lambda: self._resume_request_locked(request_id, recover_saved=recover_saved, origin='resume'), origin='resume')

    def _resume_request_locked(self, request_id, *, recover_saved=False, origin='resume'):
        with self.channels._boundary():
            row = self.store.get_request(request_id)
            if row is None:
                raise ArtifactConflict('Artifact request is unknown.')
            record = self._queue_record(row)
            audit = row['audit']
            if row['state'] not in LIVE:
                if recover_saved and row['state'] == 'fulfilled':
                    ack = self._repair_fulfilled_ack_locked(row, origin=origin, transport=record)
                    return self._mutation(row, record, admission=ack if ack['status'] == 'admitted' else None,
                        warning=None if ack['status'] == 'admitted' else 'operator_recovery_required',
                        transport_settled=record is not None and record['state'] == 'settled_recovered')
                return self._mutation(row, record)
            settled = self._settle_empty_transport(row, record)
            if settled is not None:
                return self._mutation(settled, record, warning='operator_recovery_required')
            if recover_saved and record is not None and record['state'] in ('released', 'failed', 'settled_recovered'):
                return self._resume_recovered(row, record, origin=origin)
            self.channels.require_active(row['channel'])
            live = self._producer(audit, self._instance(audit['producer']['identity_id']))
            self._packet(row, live, mode='reservation_resume', origin=origin)
            if record is None:
                if row['state'] == 'active':
                    raise ArtifactUnavailable('Active artifact transport is missing; explicit repair is required.')
                self.briefs.put(self._brief(audit), owner=self._owner(audit))
                record = self.agents.trigger_identity_sync(live['identity_id'], dispatch_id=audit['dispatch_id'],
                    channel=audit['original_channel'], purpose='artifact-v1', artifact_request_id=request_id,
                    artifact_attempt_id=audit['attempt_id'], artifact_brief_id=audit['brief_id'],
                    artifact_scope_sha256=audit['scope']['sha256'])
            self._envelope(row, live, record['envelope'])
            if record['state'] == 'queued':
                allowed = allowed_review_dispatch_ids(self.channels.engine._store.list_all(), live['identity_id'])
                reason = 'queued_behind_review' if allowed is not None and audit['dispatch_id'] not in allowed else 'queued'
                row = self.store.set_attempt_state(request_id, audit['attempt_id'], row['state'], {'state': 'queued', 'reason': reason})
                return self._mutation(row, record)
            if record['state'] in ('dispatched', 'acknowledged', 'uncertain'):
                return self._mutation(self._activate(row), record)
            if record['state'] in ('cancelled', 'cancelling'):
                row = self.store.set_attempt_state(request_id, audit['attempt_id'], row['state'],
                    {'state': 'cancelled', 'reason': 'operator_cancelled'})
                return self._mutation(row, record, transport_settled=record['state'] == 'cancelled')
            # Terminal transport with saved content needs explicit operator recovery.
            return self._mutation(row, record, warning='operator_recovery_required')

    def _startup_cancel_repair(self, row, result):
        repair = self.repair_cancel_fences([row['audit']['request_id']])
        for request in repair['repaired']:
            if request not in result['cancel_fence_repaired']:
                result['cancel_fence_repaired'].append(request)
        if repair['unconfirmed']:
            entry = {'request_id': row['audit']['request_id'], 'dispatch_id': row['audit']['dispatch_id'],
                     'reason': 'operator_recovery_required'}
            if entry not in result['held']:
                result['held'].append(entry)

    def _startup_capture(self, dispatch, saved, result):
        row = self.store.get_request_by_dispatch(dispatch)
        request = row['audit']['request_id'] if row is not None else None
        def held(reason):
            result['held'].append({'request_id': request, 'dispatch_id': dispatch, 'reason': reason})
        if row is not None and row['state'] in ('prepared', 'queued'):
            repaired = self._resume_request_locked(request, origin='startup')
            state = repaired['request']['state']
            if state in LIVE:
                result['enqueue_repaired'].append(request)
            elif state == 'failed':
                held('delivery_unconfirmed')
            elif state == 'cancelled':
                self._startup_cancel_repair(self.store.get_request(request), result)
            else:
                held('operator_recovery_required')
            return
        if row is not None and row['state'] == 'cancelled':
            self._startup_cancel_repair(row, result)
        if saved is None:
            if row is not None and row['state'] == 'active':
                transport = self._queue_record(row)
                if transport is None:
                    held('operator_recovery_required')
                elif self._settle_empty_transport(row, transport) is not None:
                    held('delivery_unconfirmed')
            return
        launch, expected = saved
        box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / launch)
        record = box.get(dispatch)
        if _digest(record) != _digest(expected):
            raise ArtifactConflict('Retained artifact result changed after inventory.')
        if box.get_ack(dispatch) is not None or box.get_disposition(dispatch) is not None:
            raise ArtifactConflict('Retained artifact receipt changed after inventory.')
        payload = record['payload']
        if row is not None and row['state'] == 'fulfilled':
            try:
                acknowledgement = self._repair_fulfilled_ack_locked(row, origin='startup')
                if acknowledgement['status'] == 'quarantined':
                    result['quarantined'].append(acknowledgement['diagnostic_id'])
            except (OSError, ValueError, RuntimeError):
                held('operator_recovery_required')
            return
        if row is not None and row['state'] == 'imported':
            held('operator_recovery_required')
            return
        if row is None or row['state'] not in LIVE:
            reason = ('unmatched_saved_result' if row is None else
                      'cancelled' if row['state'] == 'cancelled' else 'superseded')
            self._capture_diagnostic(row, {'identity_id': payload['seat_identity_id']}, reason,
                payload['markdown'], mode='unmatched_saved_retained' if row is None else 'terminal_saved',
                origin='startup', kind='startup_saved_disposition', payload=payload,
                incoming=record, launch_attempt=launch)
        transport = self._queue_record(row)
        if transport is None:
            held('operator_recovery_required')
        elif transport['state'] in ('released', 'failed', 'settled_recovered'):
            result['recovery_available'].append(request)
        elif transport['state'] in ('dispatched', 'acknowledged', 'uncertain'):
            admission = self._admit_saved_locked(record, self._instance(row['audit']['producer']['identity_id']), origin='startup')
            if admission['status'] == 'admitted':
                result['admitted'].append(admission)
            else:
                result['quarantined'].append(admission['diagnostic_id'])
        else:
            held('operator_recovery_required')

    def recover_startup(self, *, limit=100):
        """Bounded outside-boundary inventory followed by fresh per-item authority."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ArtifactValidationError('Artifact recovery limit must be between 1 and 100.')
        self._assert_independent_boundary()
        result = {'scanned': 0, 'enqueue_repaired': [], 'admitted': [], 'cancel_fence_repaired': [],
                  'recovery_available': [], 'quarantined': [], 'held': [], 'remaining': 0}
        tasks, saved = {}, {}
        def held(request, dispatch, reason):
            result['held'].append({'request_id': request, 'dispatch_id': dispatch, 'reason': reason})
        try:
            for channel in sorted(self.store.channel_names()):
                for pending in self.store.pending(channel):
                    row = self.store.get_request(pending['request_id'])
                    tasks[row['audit']['dispatch_id']] = row
            for record in self.agents.queue.records():
                if record['envelope'].get('purpose') == 'artifact-v1':
                    dispatch = record['envelope']['dispatch_id']
                    row = self.store.get_request_by_dispatch(dispatch)
                    if row is not None and row['state'] == 'cancelled' and record['state'] in (
                            'queued', 'dispatched', 'acknowledged', 'uncertain', 'cancelling'):
                        tasks[dispatch] = row
        except (OSError, ValueError, RuntimeError):
            held(None, None, 'storage_unavailable')
            return result
        from runtime_adoption import _launch_record
        for config in sorted((self.store.root / 'api_seat_runtime').glob('*/config.json')):
            if not (config.parent / 'artifact_results').exists():
                continue
            try:
                _launch_record(self.seats, config)
                box = ArtifactOutbox(config.parent)
                inventory = box.list_records(limit=100)
                result['remaining'] += max(0, inventory['count'] - len(inventory['rows']))
                for record in inventory['rows']:
                    dispatch = record['payload']['dispatch_id']
                    if box.get_ack(dispatch) is not None or box.get_disposition(dispatch) is not None:
                        continue
                    if dispatch in saved:
                        raise ArtifactUnavailable('Conflicting retained artifact authority.')
                    saved[dispatch] = (config.parent.name, record)
                    if dispatch not in tasks:
                        tasks[dispatch] = self.store.get_request_by_dispatch(dispatch)
            except (OSError, ValueError, RuntimeError):
                held(None, None, 'storage_unavailable')
        selected = list(tasks)[:limit]
        result['remaining'] += max(0, len(tasks) - limit)
        for dispatch in selected:
            result['scanned'] += 1
            snapshot = tasks[dispatch]
            request = snapshot['audit']['request_id'] if snapshot is not None else None
            try:
                outcome = self._packet_invocation(lambda: self._run_diagnostic_operation(
                    lambda: self._startup_capture(dispatch, saved.get(dispatch), result), origin='startup'))
                if isinstance(outcome, dict) and outcome.get('status') == 'quarantined':
                    result['quarantined'].append(outcome['diagnostic_id'])
            except (ArtifactAccessError, _ArtifactProducerUnavailable):
                held(request, dispatch, 'producer_unavailable')
            except ArtifactConflict as error:
                if isinstance(error, _DiagnosticAuthorityChanged) and error.cancel_winner:
                    try:
                        with self.channels._boundary():
                            current = self.store.get_request_by_dispatch(dispatch)
                            if current is not None and current['state'] == 'cancelled':
                                self._startup_cancel_repair(current, result)
                            else:
                                held(request, dispatch, 'operator_recovery_required')
                    except (OSError, ValueError, RuntimeError):
                        held(request, dispatch, 'storage_unavailable')
                else:
                    held(request, dispatch, 'operator_recovery_required')
            except (OSError, ValueError, RuntimeError):
                # Warning projection uses fresh authority, not the inventory snapshot.
                # A failed refresh itself remains a per-item storage warning.
                try:
                    current = self.store.get_request_by_dispatch(dispatch)
                    mode = current['state'] if current is not None else None
                except (OSError, ValueError, RuntimeError):
                    mode = None
                held(request, dispatch, 'operator_recovery_required' if mode == 'fulfilled' else 'storage_unavailable')
        for dispatch in list(tasks)[limit:]:
            snapshot = tasks[dispatch]
            if snapshot is None:
                continue
            try:
                with self.channels._boundary():
                    row = self.store.get_request(snapshot['audit']['request_id'])
                    if (row is not None and row['audit']['attempt_id'] == snapshot['audit']['attempt_id']
                            and row['state'] in ('prepared', 'queued')):
                        self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                            {'state': row['state'], 'reason': 'resume_pending'})
            except (OSError, ValueError, RuntimeError):
                held(snapshot['audit']['request_id'], dispatch, 'storage_unavailable')
        return result
