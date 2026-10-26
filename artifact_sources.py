"""Detached current-run source capture. No dispatch, authority or network I/O."""
from copy import deepcopy
import json

import artifact_store as storage
from review_brief import _validated_document
from store import MessageSnapshotUnavailable


class ArtifactSourceError(ValueError):
    def __init__(self, code='source_unavailable'):
        self.code = code
        super().__init__('Session source exceeds the supported size.' if code == 'source_too_large'
                         else 'Session source could not be captured.')


PROVENANCE = frozenset(('session_id', 'run_id', 'event_id', 'question_event_id', 'kind',
    'provenance', 'submitted_by', 'seat_identity_id', 'input_revision', 'session_output'))
ATTACHMENT = frozenset(('name', 'url', 'type', 'content_type', 'mime_type', 'size',
    'byte_length', 'sha256', 'content_sha256', 'encoding'))
SOURCE_STATES = frozenset(('active', 'waiting', 'paused', 'awaiting_input', 'stalled',
                         'retrying', 'interrupted', 'complete'))


def _primitive(value):
    return value is None or type(value) in (str, int, float, bool)


def project_artifact_message(row):
    try:
        storage._record_integer(row['id'])
        uid = 'legacy:' + str(row['id']) if row.get('uid') is None else row['uid']
        storage._label_text(uid)
        stamp = row.get('timestamp')
        if stamp is not None:
            storage._number(stamp)
        metadata = row.get('metadata') or {}
        attachments = row.get('attachments') or []
        if not isinstance(metadata, dict) or not isinstance(attachments, list):
            raise ValueError()
        projected = []
        for item in attachments:
            if not isinstance(item, dict):
                raise ValueError()
            descriptor = {}
            for key, value in item.items():
                if key not in ATTACHMENT:
                    continue
                if value is not None:
                    if key in ('size', 'byte_length'):
                        storage._record_integer(value)
                    elif key in ('sha256', 'content_sha256'):
                        storage._hex(value, 64)
                    else:
                        storage._text(value, empty=True)
                descriptor[key] = value
            projected.append(descriptor)
        return {'id': row['id'], 'uid': uid, 'sender': row['sender'], 'type': row['type'],
                'timestamp': stamp, 'text': row['text'], 'attachments': projected,
                'provenance': {key: value for key, value in metadata.items()
                               if key in PROVENANCE and _primitive(value)}}
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise ArtifactSourceError() from None


def check_packet_bounds(packet):
    """Count canonical bytes without allocating a potentially oversized JSON string."""
    total = 0

    def add(count):
        nonlocal total
        total += count
        if total > storage.MAX_PACKET_BYTES:
            raise ArtifactSourceError('source_too_large')

    def count(value, depth=0):
        if depth > 32:
            raise ArtifactSourceError()
        if isinstance(value, str):
            add(2)
            for start in range(0, len(value), 1024):
                add(len(json.dumps(value[start:start+1024], ensure_ascii=False,
                                   allow_nan=False).encode('utf-8')) - 2)
        elif isinstance(value, dict):
            add(2)
            for index, key in enumerate(sorted(value)):
                if index:
                    add(1)
                if not isinstance(key, str):
                    raise ArtifactSourceError()
                count(key, depth+1); add(1); count(value[key], depth+1)
        elif isinstance(value, list):
            add(2)
            for index, item in enumerate(value):
                if index:
                    add(1)
                count(item, depth+1)
        elif _primitive(value):
            add(len(json.dumps(value, allow_nan=False).encode('utf-8')))
        else:
            raise ArtifactSourceError()

    try:
        if not isinstance(packet, dict) or not isinstance(packet.get('messages'), list):
            raise ArtifactSourceError()
        if len(packet['messages']) > storage.MAX_PACKET_MESSAGES:
            raise ArtifactSourceError('source_too_large')
        count(packet)
    except ArtifactSourceError:
        raise
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        raise ArtifactSourceError() from None
    return total


from session_engine import event_projection_text as expected_event_projection_text


def capture_artifact_session_source(session_id, run_id, channel, *, sessions, messages):
    session = sessions.get(session_id)
    if (session is None or session.get('run_id') != run_id or session.get('channel') != channel
            or session.get('state') not in SOURCE_STATES or session.get('stop_id')
            or session.get('replaced_by_run_id')):
        raise ArtifactSourceError()
    entries = [(event, False) for event in session.get('admitted_events', [])]
    entries += [(entry, True) for entry in session.get('continuation_context', [])]
    if not entries:
        raise ArtifactSourceError()
    if len(entries) > storage.MAX_PACKET_MESSAGES:
        raise ArtifactSourceError('source_too_large')
    try:
        ids = [entry['projected_message_id'] for entry, _ in entries]
        if any(type(identifier) is not int for identifier in ids) or len(set(ids)) != len(ids):
            raise ArtifactSourceError()
        rows = messages.snapshot_selected(channel, ids)
        saved = {row['id']: row for row in rows}
        for entry, continuation in entries:
            row = saved[entry['projected_message_id']]
            meta = row.get('metadata') or {}
            if continuation:
                valid = (row['uid'] == 'session-input:' + entry['question_event_id']
                         and row['sender'] == 'operator' and row['text'] == entry['answer']
                         and meta.get('session_id') == session_id
                         and meta.get('question_event_id') == entry['question_event_id'])
            else:
                from turn_events import IDENTITY_FIELDS
                # Validate phase/turn grammar against the frozen design as well as attribution.
                run, phase, turn = entry['turn_id'].split(':')
                phase, turn = int(phase), int(turn)
                if phase < 0 or turn < 0:
                    raise ArtifactSourceError()
                session['design_snapshot']['phases'][phase]['participants'][turn]
                valid = (run == run_id and row['uid'] == 'session-event:' + entry['event_id']
                         and row['sender'] == entry['sender']
                         and row['text'] == expected_event_projection_text(session, entry, meta)
                         and meta.get('session_id') == session_id
                         and all(meta.get(key) == entry[key] for key in (*IDENTITY_FIELDS, 'event_id', 'kind')))
            if not valid:
                raise ArtifactSourceError()
        source = session['input_snapshot']
        document = (_validated_document(source['document'], source['text'])
                    if source.get('document') is not None else None)
        packet = {'version': 1, 'channel': channel, 'scope_kind': 'run_accepted_messages',
            'source_run': {'session_id': session_id, 'run_id': run_id,
                'input_revision': session['input_revision'], 'state_at_request': session['state']},
            'input': {'text': source['text'], 'input_revision': session['input_revision'],
                      'source_document': document},
            'messages': [project_artifact_message(row) for row in sorted(rows, key=lambda row: row['id'])]}
        check_packet_bounds(packet)
        storage._packet_scope('0'*32, packet)
        return deepcopy(session), packet
    except ArtifactSourceError:
        raise
    except (MessageSnapshotUnavailable, KeyError, IndexError, TypeError, ValueError, UnicodeError):
        raise ArtifactSourceError() from None
