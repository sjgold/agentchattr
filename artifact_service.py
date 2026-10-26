"""Artifact authority component under construction; no runtime/public binding."""
from copy import deepcopy
from functools import wraps
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


def _packet_service_entry(method):
    @wraps(method)
    def invoke(self, *args, **kwargs):
        return self._packet_invocation(lambda: method(self, *args, **kwargs))
    return invoke


class ArtifactService:
    def _packet_invocation(self, step):
        with _packet_validation_invocation(self.store):
            return step()

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
        values = [row for row in self.registry.get_all().values()
                  if row['identity_id'] == identity and row.get('state') == 'active']
        if len(values) != 1:
            raise ArtifactAccessError('Artifact producer identity is unavailable.')
        return values[0]

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

    def _diagnostic(self, row, instance, reason, content, *, terminal=False, payload=None):
        bounded, truncated = (None, False) if content is None else self._bounded(content)
        if truncated:
            reason = 'response_too_large'
        audit = row['audit']
        claim = payload or audit
        diagnostic = self.store.quarantine_submission(claim.get('request_id'), claim.get('attempt_id'),
            claim.get('dispatch_id'), reason=reason, content=bounded, actor_identity_id=instance['identity_id'])
        return {'status': 'quarantined', 'diagnostic_id': diagnostic.get('id') or diagnostic['latest_diagnostic_id'],
                'reason': reason, 'request_terminal': terminal, 'received_truncated': truncated,
                'notice': 'response_body_not_retained' if truncated else None}

    def _fence(self, row):
        request = row['audit']['request_id']
        cancellation = uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:artifact-v1:cancel:' + request).hex
        return self.agents.queue.cancel_dispatch(row['audit']['dispatch_id'], cancellation)

    def _packet(self, row, instance):
        try:
            return self.store.get_packet(row['audit']['scope']['packet_id'])
        except ArtifactUnavailable:
            self._diagnostic(row, instance, 'source_packet_unavailable', None, terminal=True)
            self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                {'state': 'failed', 'reason': 'source_packet_unavailable'})
            self._fence(row)
            raise

    def _activate(self, row):
        return self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                                             {'state': 'active', 'reason': None})

    @_packet_service_entry
    def get_brief(self, brief_id, instance):
        with self.channels._boundary():
            return self._get_brief_locked(brief_id, instance)

    def _get_brief_locked(self, brief_id, instance):
        private, row, live, _ = self._context(brief_id, instance)
        packet = self._packet(row, live)
        self._activate(row)
        public = {key: deepcopy(value) for key, value in private.items() if key != '_artifact_seal'}
        public['producer'].pop('launch_nonce')
        return {'brief': public, 'packet': packet}

    @_packet_service_entry
    def get_delivery(self, brief_id, instance):
        with self.channels._boundary():
            private, row, live, record = self._context(brief_id, instance)
            if row['audit']['producer']['adapter'] != 'openai-compatible':
                raise ArtifactAccessError('Private artifact delivery is limited to its managed API worker.')
            packet = self._packet(row, live)
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
        with self.channels._boundary():
            parent = self._get_parent_locked(brief_id, instance)
            return {**self._get_brief_locked(brief_id, instance), **parent}

    @staticmethod
    def _ack(metadata):
        return {'status': 'admitted', 'event_id': metadata['dispatch_id'], 'request_id': metadata['request_id'],
                'version_id': metadata['id'], 'sha256': metadata['sha256']}

    @_packet_service_entry
    def submit_cli(self, brief_id, markdown, instance):
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
                error = self._diagnostic(row, live, 'invalid_content', markdown)
                raise ArtifactInputError(error['diagnostic_id'], received_truncated=error['received_truncated']) from None
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
                content, truncated = self._bounded(payload['markdown'])
                reason = 'response_too_large' if truncated else 'unmatched_saved_result'
                diagnostic = self.store.quarantine_submission(None, payload['attempt_id'], payload['dispatch_id'],
                    reason=reason, content=content, actor_identity_id=live['identity_id'])
                return {'status': 'quarantined', 'diagnostic_id': diagnostic['id'], 'reason': reason,
                    'request_terminal': False, 'received_truncated': truncated,
                    'notice': 'response_body_not_retained' if truncated else None}
            private, row, live, owned = self._context(row['audit']['brief_id'], instance, replay=True)
            payload = verify_result(record, private['_artifact_seal']['seal_secret'])
            reason = self._payload_reason(payload, row, owned)
            if reason:
                return self._diagnostic(row, live, reason, payload['markdown'], payload=payload)
            try:
                _observation(payload['observation'], row['audit']['producer']['adapter'])
            except ArtifactValidationError:
                return self._diagnostic(row, live, 'invalid_response', payload['markdown'], payload=payload)
            audit = row['audit']
            box = ArtifactOutbox(self.store.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
            if row['state'] == 'fulfilled':
                saved = self.store.get_version(row['version_id'])
                if saved is None:
                    raise ArtifactUnavailable('Artifact version is unavailable.')
                if saved['markdown'] != payload['markdown']:
                    return self._diagnostic(row, live, 'conflicting_duplicate', payload['markdown'], payload=payload)
                prior = box.find(audit['dispatch_id'])
                if prior is None:
                    raise ArtifactUnavailable('Artifact result authority is missing.')
                verify_result(prior, private['_artifact_seal']['seal_secret'])
                box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
                return self._ack(saved['metadata'])
            self._packet(row, live)
            self._activate(row)
            prior = box.find(audit['dispatch_id'])
            if prior is not None:
                verified = verify_result(prior, private['_artifact_seal']['seal_secret'])
                if self._payload_reason(verified, row, owned):
                    raise ArtifactUnavailable('Stored artifact result scope differs from its request.')
                if verified['markdown'] != payload['markdown']:
                    return self._diagnostic(row, live, 'conflicting_duplicate', payload['markdown'], payload=payload)
                payload = verified  # First trusted observation/time remains immutable.
            else:
                box.save(payload, private['_artifact_seal']['seal_secret'])
            metadata = self.store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
                payload['markdown'], payload['observation'])
            box.acknowledge(audit['dispatch_id'], audit['dispatch_id'])
            return self._ack(metadata)

    @_packet_service_entry
    def reject_response(self, brief_id, content, instance, *, received_truncated=False):
        if (type(received_truncated) is not bool or
                not ((isinstance(content, str) and not received_truncated) or
                     (content is None and received_truncated))):
            raise ArtifactValidationError('Artifact rejection requires text or an explicit omitted body.')
        with self.channels._boundary():
            _, row, live, _ = self._context(brief_id, instance)
            if row['audit']['producer']['adapter'] != 'openai-compatible':
                raise ArtifactAccessError('API response rejection requires its managed API producer.')
            self._packet(row, live)
            row = self._activate(row)
            result = self._diagnostic(row, live, 'response_too_large' if received_truncated else 'invalid_response',
                                      content, terminal=True)
            if received_truncated:
                result.update(received_truncated=True, notice='response_body_not_retained')
            self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], 'active',
                {'state': 'quarantined', 'reason': 'invalid_response'})
            self._fence(row)
            return result

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
                    if (row['audit']['source_run'] or {}).get('run_id') != run_id:
                        continue
                    self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                        {'state': 'cancelled', 'reason': 'source_stopped'})
                    requests.append(row['audit']['request_id'])
                    dispatches.append(row['audit']['dispatch_id'])
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

    def _resume_recovered(self, row, transport):
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
        self._packet(row, instance)
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
                                    'conflicting_duplicate', payload['markdown'])
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
        with self.channels._boundary():
            row = self.store.get_request(request_id)
            if row is None:
                raise ArtifactConflict('Artifact request is unknown.')
            record = self._queue_record(row)
            audit = row['audit']
            if row['state'] not in LIVE:
                if recover_saved and row['state'] == 'fulfilled':
                    ack = self._repair_fulfilled_ack(row)
                    return self._mutation(row, record, admission=ack if ack['status'] == 'admitted' else None,
                        warning=None if ack['status'] == 'admitted' else 'operator_recovery_required',
                        transport_settled=record is not None and record['state'] == 'settled_recovered')
                return self._mutation(row, record)
            settled = self._settle_empty_transport(row, record)
            if settled is not None:
                return self._mutation(settled, record, warning='operator_recovery_required')
            if recover_saved and record is not None and record['state'] in ('released', 'failed', 'settled_recovered'):
                return self._resume_recovered(row, record)
            self.channels.require_active(row['channel'])
            live = self._producer(audit, self._instance(audit['producer']['identity_id']))
            self._packet(row, live)
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

    def recover_startup(self, *, limit=100):
        """One bounded pass over owned work, without spawning or adopting a seat."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ArtifactValidationError('Artifact recovery limit must be between 1 and 100.')
        result = {'scanned': 0, 'enqueue_repaired': [], 'admitted': [], 'cancel_fence_repaired': [],
                  'recovery_available': [], 'quarantined': [], 'held': [], 'remaining': 0}
        with self.channels._boundary():
            tasks, saved = {}, {}
            def held(request, dispatch, reason):
                result['held'].append({'request_id': request, 'dispatch_id': dispatch, 'reason': reason})
            try:
                for channel in self.store.channel_names():
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
            # Inventory only retained managed launches belonging to this server.
            # No registry registration, heartbeat, process lookup or adoption here.
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
                        saved[dispatch] = (box, record)
                        if dispatch not in tasks:
                            tasks[dispatch] = self.store.get_request_by_dispatch(dispatch)
                except (OSError, ValueError, RuntimeError):
                    held(None, None, 'storage_unavailable')
            selected = list(tasks)[:limit]
            result['remaining'] += max(0, len(tasks) - limit)
            for dispatch in selected:
                result['scanned'] += 1
                row = tasks[dispatch]
                request = row['audit']['request_id'] if row is not None else None
                try:
                    if row is not None and row['state'] in ('prepared', 'queued'):
                        # This dispatch is assigned ONLY queue-state repair this pass.
                        repaired = self.resume_request(request)
                        if repaired['request']['state'] == 'failed':
                            held(request, dispatch, 'delivery_unconfirmed')
                        else:
                            result['enqueue_repaired'].append(request)
                        continue
                    if row is not None and row['state'] == 'cancelled':
                        repair = self.repair_cancel_fences([request])
                        result['cancel_fence_repaired'].extend(repair['repaired'])
                        if repair['unconfirmed']:
                            held(request, dispatch, 'operator_recovery_required')
                    if dispatch not in saved:
                        if row is not None and row['state'] == 'active':
                            transport = self._queue_record(row)
                            if transport is None:
                                held(request, dispatch, 'operator_recovery_required')
                            elif self._settle_empty_transport(row, transport) is not None:
                                held(request, dispatch, 'delivery_unconfirmed')
                        continue
                    box, record = saved[dispatch]
                    payload = record['payload']
                    if row is not None and row['state'] == 'fulfilled':
                        try:
                            acknowledgement = self._repair_fulfilled_ack(row)
                            if acknowledgement['status'] == 'quarantined':
                                result['quarantined'].append(acknowledgement['diagnostic_id'])
                        except (OSError, ValueError, RuntimeError):
                            held(request, dispatch, 'operator_recovery_required')
                        continue  # ACK repair is neither admission nor terminal quarantine.
                    if row is not None and row['state'] == 'imported':
                        held(request, dispatch, 'operator_recovery_required')
                        continue
                    if row is None or row['state'] not in LIVE:
                        reason = ('unmatched_saved_result' if row is None else
                                  'cancelled' if row['state'] == 'cancelled' else 'superseded')
                        diagnostic = self.store.quarantine_submission(payload['request_id'] if row else None,
                            payload['attempt_id'], dispatch, reason=reason, content=payload['markdown'],
                            actor_identity_id=payload['seat_identity_id'])
                        identifier = diagnostic.get('id') or diagnostic['latest_diagnostic_id']
                        box.quarantine(dispatch, identifier, reason)
                        result['quarantined'].append(identifier)
                        continue
                    transport = self._queue_record(row)
                    if transport is None:
                        held(request, dispatch, 'operator_recovery_required')
                    elif transport['state'] in ('released', 'failed', 'settled_recovered'):
                        result['recovery_available'].append(request)
                    elif transport['state'] in ('dispatched', 'acknowledged', 'uncertain'):
                        admission = self.admit_saved(record, self._instance(row['audit']['producer']['identity_id']))
                        if admission['status'] == 'admitted':
                            result['admitted'].append(admission)
                        else:
                            result['quarantined'].append(admission['diagnostic_id'])
                    else:
                        held(request, dispatch, 'operator_recovery_required')
                except (ArtifactAccessError, _ArtifactProducerUnavailable):
                    held(request, dispatch, 'producer_unavailable')
                except ArtifactConflict:
                    held(request, dispatch, 'operator_recovery_required')
                except (OSError, ValueError, RuntimeError):
                    held(request, dispatch, 'storage_unavailable')
            for dispatch in list(tasks)[limit:]:
                row = tasks[dispatch]
                if row is not None and row['state'] in ('prepared', 'queued'):
                    try:
                        self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                                                     {'state': row['state'], 'reason': 'resume_pending'})
                    except (OSError, ValueError, RuntimeError):
                        held(row['audit']['request_id'], dispatch, 'storage_unavailable')
        return result
