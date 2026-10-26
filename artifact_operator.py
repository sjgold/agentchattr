"""Reduced operator document operations; one captured source and explicit author."""
from copy import deepcopy
import time

import artifact_store as storage
from artifact_service import active_artifact_instance, ArtifactAccessError
from artifact_sources import capture_artifact_session_source, ArtifactSourceError
import runtime_protocol


MESSAGES = {
    'invalid_request': 'Invalid document request.', 'request_conflict': 'Document request conflicts with saved state.',
    'operator_forbidden': 'Operator authentication is required.', 'not_found': 'Document record was not found.',
    'method_not_allowed': 'Method is not supported.', 'unexpected_failure': 'Document operation failed.',
    'session_unknown': 'Session was not found.', 'run_unknown': 'Session run was not found.',
    'channel_mismatch': 'Session and channel do not match.', 'channel_inactive': 'Channel is not active.',
    'no_author_available': 'No supported live author is available for this session.',
    'source_unavailable': 'Session source could not be captured.',
    'source_too_large': 'Session source exceeds the supported size; nothing was truncated.',
    'request_too_large': 'Document request exceeds the supported size.',
    'storage_unavailable': 'Document storage is unavailable. Saved data is retained.',
    'boundary_held': 'Document operation requires an independent authority boundary.',
    'not_ready': 'Document is not ready yet.'}
STATUS = {'invalid_request': 400, 'request_too_large': 413, 'source_too_large': 413,
          'operator_forbidden': 403, 'method_not_allowed': 405, 'unexpected_failure': 500,
          'session_unknown': 404, 'run_unknown': 404, 'not_found': 404,
          'storage_unavailable': 503, 'boundary_held': 503}


class ArtifactOperatorError(ValueError):
    def __init__(self, code, *, cause=None, author_name=None, examined_roles=None,
                 request_id=None, durability=None, request=None):
        self.code, self.http_status = code, STATUS.get(code, 409)
        self.cause, self.author_name, self.examined_roles = cause, author_name, examined_roles
        self.request_id, self.durability, self.request = request_id, durability, request
        text = 'Artifact authoring is not enabled.' if cause == 'capability_off' else MESSAGES[code]
        super().__init__(text)

    def body(self):
        return {'code': self.code, 'error': str(self), 'cause': self.cause,
                'author_name': self.author_name, 'examined_roles': self.examined_roles,
                'request_id': self.request_id, 'durability': self.durability, 'request': self.request}


def resolve_default_artifact_author(session, authority):
    if 'artifact-v1' not in runtime_protocol.SUPPORTED_CAPABILITIES:
        raise ArtifactOperatorError('no_author_available', cause='capability_off', examined_roles=0)
    reasons = {'artifact_capability_missing': 'not_supported', 'unmanaged_producer': 'unmanaged',
               'producer_unavailable': 'no_live_instance', 'capability_binding_changed': 'binding_changed',
               'runtime_unverified': 'runtime_unverified'}
    examined, first = 0, None
    for role in session['design_snapshot']['roles']:
        binding = session.get('participant_bindings', {}).get(role, {})
        if binding.get('kind') != 'agent' or not binding.get('identity_id'):
            continue
        examined += 1
        identity, name = binding['identity_id'], None
        try:
            instance = active_artifact_instance(authority.registry, identity)
            name = instance['name']
        except ArtifactAccessError:
            matches = [row for row in authority.registry.get_all().values()
                       if row.get('identity_id') == identity and row.get('state') == 'active']
            cause = 'ambiguous' if len(matches) > 1 else 'no_live_instance'
        else:
            current = authority.seats.artifact_producer(instance)
            if current['available'] is True:
                return identity
            cause = reasons.get(current['reason'], 'not_supported')
        if first is None:
            first = cause, name
    cause, name = first or ('no_agent_role', None)
    raise ArtifactOperatorError('no_author_available', cause=cause, author_name=name, examined_roles=examined)


def summary(row, *, needs_resume=False, warning=None):
    audit, state = row['audit'], row['state']
    label = {'prepared': 'queued', 'queued': 'queued', 'active': 'working',
             'fulfilled': 'ready', 'imported': 'ready' if row['version_id'] else 'failed'}.get(state, 'failed')
    if needs_resume:
        label = 'unavailable'
    source = audit['source_run']
    return {'request_id': audit['request_id'], 'channel': row['channel'], 'state': state,
        'reason': row['reason'], 'label': label, 'author_name': audit['producer']['name'],
        'created_at': audit['created_at'], 'updated_at': row['updated_at'], 'version_id': row['version_id'],
        'source': {'session_id': source['session_id'] if source else None,
            'run_id': source['run_id'] if source else None, 'message_count': len(audit['scope']['message_refs']),
            'packet_bytes': audit['scope']['byte_length'], 'scope_sha256': audit['scope']['sha256'],
            'input_revision': audit['scope']['input_revision'],
            'source_so_far': source is not None and source['state_at_request'] != 'complete'},
        'needs_resume': needs_resume, 'warning': warning}


class _Creation(dict):
    def __init__(self, value, *, created):
        super().__init__(value)
        self.created = created  # HTTP status only, never an extra serialized DTO field.


class ArtifactOperator:
    def __init__(self, *, authority, sessions, messages):
        self.authority, self.sessions, self.messages = authority, sessions, messages

    def _intent(self, intent):
        try:
            storage._fields(intent, ('request_id', 'channel', 'session_id', 'run_id', 'instruction'))
            storage._hex(intent['request_id']); storage._hex(intent['run_id'])
            storage._channel(intent['channel']); storage._record_integer(intent['session_id'], 1)
            if isinstance(intent['instruction'], str) and len(intent['instruction'].encode('utf-8')) > 32768:
                raise ArtifactOperatorError('request_too_large')
            storage._index_text(intent['instruction'], 32768)
        except ArtifactOperatorError:
            raise
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise ArtifactOperatorError('invalid_request') from None

    @staticmethod
    def _stored_intent(row):
        audit, source = row['audit'], row['audit']['source_run'] or {}
        return {'request_id': audit['request_id'], 'channel': audit['original_channel'],
                'session_id': source.get('session_id'), 'run_id': source.get('run_id'),
                'instruction': audit['instruction']}

    def create(self, intent):
        self._intent(intent)
        authority, identifier = self.authority, intent['request_id']
        try:
            authority._assert_independent_boundary()
            with authority.channels._boundary():
                saved = authority.store.get_request(identifier)
                if saved is not None:
                    if (self._stored_intent(saved) != intent or saved['audit']['format'] != 'Markdown'
                            or saved['audit']['requester'] != 'operator'):
                        raise ArtifactOperatorError('request_conflict', request_id=identifier,
                                                    durability='recorded', request=summary(saved))
                    status = authority.request_status(identifier)
                    return _Creation({'request': summary(saved, needs_resume=status['needs_resume']),
                            'durability': 'recorded', 'transport_settled': None}, created=False)
            if 'artifact-v1' not in runtime_protocol.SUPPORTED_CAPABILITIES:
                raise ArtifactOperatorError('no_author_available', cause='capability_off', examined_roles=0)
            session = self.sessions.get(intent['session_id'])
            if session is None:
                raise ArtifactOperatorError('session_unknown')
            if session['channel'] != intent['channel']:
                raise ArtifactOperatorError('channel_mismatch')
            if session['run_id'] != intent['run_id']:
                raise ArtifactOperatorError('run_unknown')
            authority.channels.require_active(intent['channel'])
            identity = resolve_default_artifact_author(session, authority)
            captured, packet = capture_artifact_session_source(intent['session_id'], intent['run_id'],
                intent['channel'], sessions=self.sessions, messages=self.messages)
            if captured.get('participant_bindings') != session.get('participant_bindings'):
                raise ArtifactOperatorError('source_unavailable')
            producer_audit = authority.request_producer(identity)
            scope = authority.store.put_packet(identifier, packet)
            ids = storage.request_ids(identifier)
            audit = {'version': 1, 'purpose': 'artifact-v1', 'request_id': identifier,
                **{key: ids[key] for key in ('lineage_id', 'attempt_id', 'dispatch_id', 'brief_id')},
                'original_channel': intent['channel'], 'requester': 'operator',
                'producer': producer_audit,
                'source_run': packet['source_run'], 'scope': scope, 'instruction': intent['instruction'],
                'format': 'Markdown', 'expected_parent': None, 'created_at': time.time()}
            with authority.channels._boundary():
                winner = authority.store.get_request(identifier)
                if winner is not None:
                    if (self._stored_intent(winner) != intent or winner['audit']['format'] != 'Markdown'
                            or winner['audit']['requester'] != 'operator'):
                        raise ArtifactOperatorError('request_conflict', request_id=identifier,
                                                    durability='recorded', request=summary(winner))
                    state = authority.request_status(identifier)
                    return _Creation({'request': summary(winner, needs_resume=state['needs_resume']),
                        'durability': 'recorded', 'transport_settled': None}, created=False)
                current = self.sessions.get(intent['session_id'])
                if (current is None or current['run_id'] != captured['run_id'] or current.get('stop_id')
                        or current.get('replaced_by_run_id') or current['channel'] != captured['channel']
                        or current.get('participant_bindings') != captured.get('participant_bindings')
                        or current.get('input_revision') != captured.get('input_revision')):
                    raise ArtifactOperatorError('source_unavailable')
                result = authority.prepare_request(audit, packet, identifier)
                status = authority.request_status(identifier)
            return _Creation({'request': summary(result['request'], needs_resume=status['needs_resume']),
                    'durability': 'recorded', 'transport_settled': result['transport_settled']}, created=True)
        except ArtifactOperatorError as error:
            if error.durability is None:
                self._describe_effects(error, identifier)
            raise
        except ArtifactSourceError as error:
            refusal = ArtifactOperatorError(error.code)
            self._describe_effects(refusal, identifier)
            raise refusal from None
        except Exception as error:
            raise self._failure(error, identifier) from None

    def _describe_effects(self, error, request_id):
        error.request_id = request_id
        try:
            with self.authority.channels._boundary():
                row = self.authority.store.get_request(request_id)
            error.durability = 'recorded' if row is not None else 'not_recorded'
            error.request = summary(row) if row else None
        except (OSError, ValueError, RuntimeError):
            error.durability, error.request = 'unknown', None

    def _failure(self, error, request_id=None):
        if getattr(error, 'code', None) == 'artifact_boundary_held':
            return ArtifactOperatorError('boundary_held', request_id=request_id,
                                         durability='unknown' if request_id is not None else None)
        elif isinstance(error, storage.ArtifactUnavailable) or isinstance(error, OSError):
            code = 'storage_unavailable'
        elif isinstance(error, storage.ArtifactValidationError):
            code = 'invalid_request'
        elif isinstance(error, storage.ArtifactConflict):
            code = 'request_conflict'
        else:
            from channel_lifecycle import ChannelConflict, ChannelUnavailable, ChannelInactive
            code = ('storage_unavailable' if isinstance(error, ChannelUnavailable) else
                    'channel_inactive' if isinstance(error, (ChannelConflict, ChannelInactive)) else 'unexpected_failure')
        durability, row = None, None
        if request_id is not None:
            try:
                with self.authority.channels._boundary():
                    row = self.authority.store.get_request(request_id)
                durability = 'recorded' if row is not None else 'not_recorded'
            except (OSError, ValueError, RuntimeError):
                durability = 'unknown'
        return ArtifactOperatorError(code, request_id=request_id, durability=durability,
                                     request=summary(row) if row else None)

    def request_status(self, request_id):
        try:
            storage._hex(request_id)
            value = self.authority.request_status(request_id)
            if value is None:
                raise ArtifactOperatorError('not_found')
            return summary(value['request'], needs_resume=value['needs_resume'])
        except ArtifactOperatorError:
            raise
        except (ValueError, TypeError):
            raise ArtifactOperatorError('invalid_request') from None
        except Exception as error:
            raise self._failure(error, request_id) from None

    def cancel(self, request_id):
        try:
            storage._hex(request_id)
            with self.authority.channels._boundary():
                row = self.authority.store.get_request(request_id)
                if row is None:
                    raise ArtifactOperatorError('not_found')
                result = self.authority.cancel_request(request_id)
            return {'request': summary(result['request'], warning=result['warning']),
                    'durability': 'recorded', 'transport_settled': result['transport_settled']}
        except ArtifactOperatorError:
            raise
        except Exception as error:
            raise self._failure(error, request_id) from None

    def version(self, version_id):
        try:
            storage._hex(version_id)
            saved = self.authority.store.get_version(version_id)
            if saved is None:
                raise ArtifactOperatorError('not_found')
            metadata = saved['metadata']; provenance = metadata['provenance']
            view = {key: metadata[key] for key in
                    ('id', 'lineage_id', 'sequence', 'channel', 'request_id', 'sha256', 'byte_length', 'created_at')}
            view.update(author_name=provenance['producer']['name'],
                requested_model=provenance['producer']['requested_model'],
                confirmed_model=provenance['observation']['confirmed_model'],
                confirmation_reason=provenance['observation']['confirmation_reason'],
                source_run=deepcopy(provenance['source_run']))
            return {'version': view, 'markdown': saved['markdown']}
        except ArtifactOperatorError:
            raise
        except storage.ArtifactValidationError:
            raise ArtifactOperatorError('invalid_request') from None
        except Exception as error:
            raise self._failure(error) from None

    def document(self, request_id):
        status = self.request_status(request_id)
        if status['version_id'] is None:
            raise ArtifactOperatorError('not_ready', request_id=request_id, request=status)
        return self.version(status['version_id'])

    def download(self, version_id):
        return self.version(version_id)['markdown'].encode('utf-8')

    def list_sessions(self, channel, offset=0):
        try:
            storage._channel(channel); storage._record_integer(offset)
            if channel not in self.authority.channels.catalog.snapshot()['channels']:
                raise ArtifactOperatorError('invalid_request')
            rows = sorted(self.sessions.list_all(channel), key=lambda row: (row['started_at'], row['id']), reverse=True)
            values = []
            for row in rows[offset:offset+20]:
                raw = (row.get('template_name') or row.get('goal') or '').encode('utf-8')
                title = raw[:256].decode('utf-8', errors='ignore')
                values.append({'session_id': row['id'], 'run_id': row['run_id'], 'title': title,
                    'state': row['state'], 'started_at': row['started_at'], 'source_so_far': row['state'] != 'complete',
                    'title_truncated': len(raw) > 256})
            return {'sessions': values, 'offset': offset, 'has_more': offset+20 < len(rows)}
        except ArtifactOperatorError:
            raise
        except (ValueError, TypeError):
            raise ArtifactOperatorError('invalid_request') from None
        except Exception as error:
            raise self._failure(error) from None
