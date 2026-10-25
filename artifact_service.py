"""Artifact authority component under construction; no runtime/public binding."""
from copy import deepcopy
import hashlib
import time

from artifact_store import (ArtifactConflict, ArtifactUnavailable, ArtifactValidationError,
    LIVE, _audit, _path_key)
from artifact_protocol import validate_brief
from queue_coordinator import CoordinatedQueue, allowed_review_dispatch_ids
import runtime_protocol


class ArtifactAccessError(PermissionError):
    pass


class ArtifactInputError(ArtifactValidationError):
    def __init__(self, diagnostic_id, *, received_truncated=False):
        super().__init__('Invalid Markdown. Correct the argument and submit again within the byte limit.')
        self.code = 'invalid_content'
        self.diagnostic_id = diagnostic_id
        self.received_truncated = received_truncated


class ArtifactService:
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

    def _producer(self, audit, instance):
        self._enabled()
        producer = audit['producer']
        if not isinstance(instance, dict) or instance.get('identity_id') != producer['identity_id']:
            raise ArtifactAccessError('Artifact request belongs to another seat.')
        live = self._instance(producer['identity_id'])
        current = self.seats.artifact_producer(live)
        if (current['available'] is not True or current['adapter'] != producer['adapter']
                or any(current[key] != producer[key] for key in ('launch_attempt', 'launch_nonce', 'fingerprint'))):
            raise ArtifactConflict('Artifact producer binding is unavailable or changed.')
        provenance = self.seats.launch_provenance(live)
        if provenance is None:
            raise ArtifactConflict('Artifact producer launch is unverified.')
        model = provenance['effective']['seat'].get('model') or None
        reason = None if model else ('cli_model_unverified' if producer['adapter'] == 'cli' else 'provider_default')
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

    def prepare_request(self, audit, packet, request_id):
        audit = _audit(audit)
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
        try:
            self._enabled()
            for channel in self.store.channel_names():
                for pending in self.store.pending(channel):
                    row = self.store.get_request(pending['request_id'])
                    if row['audit']['producer']['identity_id'] != instance.get('identity_id'):
                        continue
                    self.channels.require_active(row['channel'])
                    self._producer(row['audit'], instance)
                    self.store.get_packet(row['audit']['scope']['packet_id'])
                    result.add(row['audit']['dispatch_id'])
        except (OSError, ValueError, RuntimeError, PermissionError):
            return set()
        return result

    def get_brief(self, brief_id, instance):
        with self.channels._boundary():
            private = self.briefs.get_private(brief_id)
            row = self.store.get_request(private['request_id'])
            if row is None or row['state'] not in LIVE:
                raise ArtifactConflict('Artifact request is not live.')
            self.channels.require_active(row['channel'])
            live = self._producer(row['audit'], instance)
            record = self.agents.queue.owned(live, row['audit']['dispatch_id'])
            self._envelope(row, live, record['envelope'])
            if not record['consumer_id'] or record['state'] not in ('dispatched', 'acknowledged', 'uncertain'):
                raise ArtifactConflict('Artifact dispatch has not been claimed or is cancelling.')
            packet = self.store.get_packet(row['audit']['scope']['packet_id'])
            self.store.set_attempt_state(row['audit']['request_id'], row['audit']['attempt_id'], row['state'],
                                         {'state': 'active', 'reason': None})
            public = {key: deepcopy(value) for key, value in private.items() if key != '_artifact_seal'}
            public['producer'].pop('launch_nonce')
            return {'brief': public, 'packet': packet}

    @staticmethod
    def _ack(metadata):
        return {'status': 'admitted', 'event_id': metadata['dispatch_id'], 'request_id': metadata['request_id'],
                'version_id': metadata['id'], 'sha256': metadata['sha256']}

    def submit_cli(self, brief_id, markdown, instance):
        """TEMPORARY unguarded TDD scaffold, private/unpublished and not routed."""
        private = self.briefs.get_private(brief_id)
        audit = self.store.get_request(private['request_id'])['audit']
        return self._ack(self.store.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
            markdown, {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'}))
