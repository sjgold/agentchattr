"""Portable artifact allowlists and bounded in-memory ZIP validation; no writes."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
import stat
import unicodedata
import zipfile

from artifact_store import (MAX_ARTIFACT_BYTES, MAX_PACKET_BYTES, MAX_PACKET_MESSAGES,
    LIVE, TERMINAL, STATE_REASONS, ArtifactValidationError, request_ids,
    _fields, _hex, _integer, _number, _channel, _text, _source_run, _packet_scope)
from sealed_result_io import canonical_utf8

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_INDEX_BYTES = 4 * 1024 * 1024
MAX_MEMBERS = 4096
MAX_LINEAGES = 1024
MAX_RATIO = 1000
HISTORY_MEMBERS = frozenset(('manifest.json', 'messages.jsonl', 'jobs.json', 'rules.json', 'summaries.json'))
INDEX_MEMBER = 'artifacts/index.json'
ERRORS = {
    'artifact_archive_owner_unavailable': (503, 'Artifact backup storage is not configured. No artifact data was omitted.'),
    'artifact_archive_storage_unavailable': (503, 'Artifact backup storage is unavailable. Saved data is retained.'),
    'artifact_archive_schema_mismatch': (400, 'Artifact members require archive schema 2.'),
    'artifact_archive_invalid_section': (400, 'Artifact backup section is invalid.'),
    'artifact_archive_limit': (413, 'Artifact backup exceeds a supported limit.'),
    'artifact_archive_repair_pending': (409, 'Finish channel repair before importing.'),
}


class ArtifactSectionError(ValueError):
    def __init__(self, code='artifact_archive_invalid_section', *, bound=None):
        self.code = code
        self.http_status, self.error = ERRORS[code]
        self.bound = bound
        super().__init__(self.error)


class ArtifactLineageError(ValueError):
    def __init__(self):
        super().__init__('Artifact lineage is invalid.')


def member_name(kind, identifier):
    _hex(identifier)
    if kind == 'version':
        return 'artifacts/objects/' + identifier + '.md'
    if kind == 'packet':
        return 'artifacts/packets/' + identifier + '.json'
    raise ArtifactValidationError('Invalid artifact archive object kind.')


def _pick(value, keys):
    return {key: deepcopy(value[key]) for key in keys}


def _scope(value):
    result = _pick(value, ('kind', 'packet_id', 'sha256', 'byte_length', 'input_revision'))
    result['message_refs'] = [_pick(row, ('id', 'uid', 'sha256')) for row in value['message_refs']]
    return result


def _source(value):
    return None if value is None else _pick(value, ('session_id', 'run_id', 'input_revision', 'state_at_request'))


def _parent(value):
    return None if value is None else _pick(value, ('version_id', 'sequence', 'sha256'))


def portable_lineage(snapshot, *, archive_id):
    """Build every metadata field explicitly; source packets are separate bytes."""
    _token(archive_id)
    lineage = snapshot['lineage']
    requests = []
    for row in snapshot['requests']:
        audit = row['audit']
        origin = row.get('import_source', {'archive_id': archive_id,
            'original_state': row['state'], 'original_reason': row['reason']})
        requests.append({'request_id': audit['request_id'], 'original_channel': audit['original_channel'],
            'requester': audit['requester'], 'producer': _pick(audit['producer'],
                ('name', 'identity_id', 'adapter', 'requested_model', 'requested_model_reason')),
            'source_run': _source(audit['source_run']), 'scope': _scope(audit['scope']),
            'instruction': audit['instruction'], 'format': audit['format'],
            'expected_parent': _parent(audit['expected_parent']), 'created_at': audit['created_at'],
            'updated_at': row['updated_at'], 'import_source': _pick(origin,
                ('archive_id', 'original_state', 'original_reason'))})
    versions = [{'version_id': row['id'], 'request_id': row['request_id'], 'sequence': row['sequence'],
        'parent_version_id': row['parent_version_id'], 'sha256': row['sha256'], 'byte_length': row['byte_length'],
        'created_at': row['created_at'], 'observation': _pick(row['provenance']['observation'],
            ('confirmed_model', 'confirmation_reason'))} for row in snapshot['versions']]
    return {'lineage_id': lineage['id'], 'channel': lineage['channel'], 'updated_at': lineage['updated_at'],
        'head_version_id': lineage['head_version_id'], 'requests': sorted(requests, key=lambda row: row['request_id']),
        'versions': sorted(versions, key=lambda row: row['sequence'])}


def portable_index(snapshots, *, archive_id):
    index = {'version': 1, 'lineages': sorted((portable_lineage(row, archive_id=archive_id)
             for row in snapshots), key=lambda row: row['lineage_id'])}
    return validate_index(canonical_utf8(index))


def artifact_counts(index):
    lineages = index['lineages']
    requests = [row for lineage in lineages for row in lineage['requests']]
    versions = [row for lineage in lineages for row in lineage['versions']]
    return {'version': 1, 'lineages': len(lineages), 'requests': len(requests), 'versions': len(versions),
        'packets': len(requests), 'markdown_bytes': sum(row['byte_length'] for row in versions),
        'source_bytes': sum(row['scope']['byte_length'] for row in requests), 'copied_source_text': True}


def artifact_manifest(history, index):
    result = {'schema_version': 2, 'archive_id': history['archive_id'], 'created_at': history['created_at'],
        'product': 'agentchattr', 'app_version': history['app_version'],
        'counts': {key: history['counts'][key] for key in ('messages', 'jobs', 'rules', 'summaries')},
        'attachments_included': False, 'artifacts': artifact_counts(index)}
    result['counts']['artifacts'] = result['artifacts']['lineages']
    validate_manifest(result, index, artifact_present=True)
    return result


def _token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,64}', value):
        raise ArtifactValidationError('Invalid artifact archive token.')


def _nullable_hex(value, width=32):
    if value is not None:
        _hex(value, width)


def _scope_shape(scope, request_id):
    _fields(scope, ('kind', 'packet_id', 'sha256', 'byte_length', 'message_refs', 'input_revision'))
    if scope['kind'] not in ('run_accepted_messages', 'selected_channel_messages'):
        raise ArtifactValidationError('Invalid artifact scope kind.')
    if _hex(scope['packet_id']) != request_ids(request_id)['packet_id']:
        raise ArtifactValidationError('Artifact packet ownership differs.')
    _hex(scope['sha256'], 64); _integer(scope['byte_length'], 1)
    _nullable_hex(scope['input_revision'], 64)
    if not isinstance(scope['message_refs'], list):
        raise ArtifactValidationError('Invalid artifact message references.')
    ids, uids = set(), set()
    for row in scope['message_refs']:
        _fields(row, ('id', 'uid', 'sha256'))
        _integer(row['id']); _text(row['uid']); _hex(row['sha256'], 64)
        if row['id'] in ids or row['uid'] in uids:
            raise ArtifactValidationError('Duplicate source references.')
        ids.add(row['id']); uids.add(row['uid'])


def _parent_shape(parent):
    if parent is not None:
        _fields(parent, ('version_id', 'sequence', 'sha256'))
        _hex(parent['version_id']); _integer(parent['sequence'], 1); _hex(parent['sha256'], 64)


def _request_shape(row):
    _fields(row, ('request_id', 'original_channel', 'requester', 'producer', 'source_run', 'scope',
        'instruction', 'format', 'expected_parent', 'created_at', 'updated_at', 'import_source'))
    _hex(row['request_id']); _channel(row['original_channel']); _text(row['requester'])
    _source_run(row['source_run']); _scope_shape(row['scope'], row['request_id'])
    _text(row['instruction'], 32768); _text(row['format'], 512); _parent_shape(row['expected_parent'])
    _number(row['created_at']); _number(row['updated_at'])
    producer = row['producer']
    _fields(producer, ('name', 'identity_id', 'adapter', 'requested_model', 'requested_model_reason'))
    _text(producer['name']); _hex(producer['identity_id'])
    if producer['adapter'] not in ('cli', 'openai-compatible'):
        raise ArtifactValidationError('Invalid artifact adapter.')
    if producer['requested_model'] is None:
        _text(producer['requested_model_reason'])
    else:
        _text(producer['requested_model'])
        if producer['requested_model_reason'] is not None:
            raise ArtifactValidationError('Invalid requested-model reason.')
    origin = row['import_source']
    _fields(origin, ('archive_id', 'original_state', 'original_reason'))
    _token(origin['archive_id'])
    if (not isinstance(origin['original_state'], str)
            or origin['original_state'] not in (LIVE | TERMINAL) - {'imported'}
            or (origin['original_reason'] is not None and not isinstance(origin['original_reason'], str))
            or origin['original_reason'] not in STATE_REASONS):
        raise ArtifactValidationError('Invalid artifact import origin.')


def _version_shape(row):
    _fields(row, ('version_id', 'request_id', 'sequence', 'parent_version_id', 'sha256',
                  'byte_length', 'created_at', 'observation'))
    _hex(row['version_id']); _hex(row['request_id']); _integer(row['sequence'], 1)
    _nullable_hex(row['parent_version_id']); _hex(row['sha256'], 64)
    _integer(row['byte_length'], 1); _number(row['created_at'])
    _fields(row['observation'], ('confirmed_model', 'confirmation_reason'))
    if row['observation']['confirmed_model'] is not None:
        _text(row['observation']['confirmed_model'])
    if row['observation']['confirmation_reason'] not in (
            'cli_model_unverified', 'provider_did_not_report_model', 'api_response'):
        raise ArtifactValidationError('Invalid artifact observation.')


def _unique_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ArtifactSectionError()
            value[key] = item
        return value
    def constant(value):
        raise ArtifactSectionError()
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=constant)


def validate_index(raw, *, member_names=None):
    if type(raw) is not bytes:
        raise ArtifactSectionError()
    if len(raw) > MAX_INDEX_BYTES:
        raise ArtifactSectionError('artifact_archive_limit', bound='index')
    try:
        index = _unique_json(raw)
        _fields(index, ('version', 'lineages'))
        if type(index['version']) is not int or index['version'] != 1 or not isinstance(index['lineages'], list):
            raise ArtifactValidationError('Invalid artifact index schema.')
        if len(index['lineages']) > MAX_LINEAGES:
            raise ArtifactSectionError('artifact_archive_limit', bound='lineages')
        owners = {kind: {} for kind in ('lineage', 'request', 'version', 'packet', 'dispatch')}
        references = set()
        def own(kind, identifier, ordinal):
            if identifier in owners[kind]:
                raise ArtifactValidationError('Ambiguous artifact archive identity.')
            owners[kind][identifier] = ordinal
        for ordinal, lineage in enumerate(index['lineages']):
            _fields(lineage, ('lineage_id', 'channel', 'updated_at', 'head_version_id', 'requests', 'versions'))
            own('lineage', _hex(lineage['lineage_id']), ordinal)
            _channel(lineage['channel']); _number(lineage['updated_at']); _nullable_hex(lineage['head_version_id'])
            if not isinstance(lineage['requests'], list) or not lineage['requests'] or not isinstance(lineage['versions'], list):
                raise ArtifactValidationError('Invalid artifact lineage containers.')
            for request in lineage['requests']:
                _request_shape(request)
                own('request', request['request_id'], ordinal)
                own('dispatch', request_ids(request['request_id'])['dispatch_id'], ordinal)
                own('packet', request['scope']['packet_id'], ordinal)
                references.add(member_name('packet', request['scope']['packet_id']))
            for version in lineage['versions']:
                _version_shape(version)
                own('version', version['version_id'], ordinal)
                references.add(member_name('version', version['version_id']))
        for ordinal, lineage in enumerate(index['lineages']):
            for request in lineage['requests']:
                parent = request['expected_parent']
                if parent is not None and owners['version'].get(parent['version_id'], ordinal) != ordinal:
                    raise ArtifactValidationError('Artifact parent escapes its lineage.')
            for version in lineage['versions']:
                if owners['request'].get(version['request_id'], ordinal) != ordinal:
                    raise ArtifactValidationError('Artifact request escapes its lineage.')
                parent = version['parent_version_id']
                if parent is not None and owners['version'].get(parent, ordinal) != ordinal:
                    raise ArtifactValidationError('Artifact version parent escapes its lineage.')
            if lineage['head_version_id'] is not None and owners['version'].get(lineage['head_version_id'], ordinal) != ordinal:
                raise ArtifactValidationError('Artifact head escapes its lineage.')
        if member_names is not None and any(name not in HISTORY_MEMBERS | {INDEX_MEMBER} | references for name in member_names):
            raise ArtifactValidationError('Artifact archive contains undeclared members.')
        return index
    except ArtifactSectionError:
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise ArtifactSectionError() from None


def has_artifact_members(infos):
    return any('artifacts' in unicodedata.normalize('NFKC', getattr(info, 'orig_filename', info.filename))
               .casefold().replace('\\', '/').split('/') for info in infos)


def validate_headers(infos, *, lineage_count=0, zip_size=0):
    if len(infos) > MAX_MEMBERS:
        raise ArtifactSectionError('artifact_archive_limit', bound='members')
    names, normalized, offsets = {}, set(), set()
    try:
        for info in infos:
            for name in (info.filename, info.orig_filename):
                if (not isinstance(name, str) or not name or any(unicodedata.category(ch) == 'Cc' for ch in name)
                        or '\\' in name or name.startswith('/') or ':' in name
                        or any(part in ('', '.', '..') for part in name.split('/'))):
                    raise ArtifactValidationError('Unsafe archive member name.')
            folded = unicodedata.normalize('NFKC', info.orig_filename).casefold()
            if folded in normalized or info.filename in names or info.orig_filename != info.filename:
                raise ArtifactValidationError('Duplicate or ambiguous archive member.')
            normalized.add(folded)
            if info.filename not in HISTORY_MEMBERS | {INDEX_MEMBER} and not re.fullmatch(
                    r'artifacts/(objects/[0-9a-f]{32}\.md|packets/[0-9a-f]{32}\.json)', info.filename):
                raise ArtifactValidationError('Unknown archive member.')
            _integer(info.header_offset); _integer(info.file_size); _integer(info.compress_size)
            if info.header_offset in offsets:
                raise ArtifactValidationError('Archive local headers overlap.')
            offsets.add(info.header_offset)
            mode = (info.external_attr >> 16) & 0o170000
            if (info.flag_bits & 0x41 or mode not in (0, stat.S_IFREG)
                    or info.external_attr & 0x10 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ArtifactValidationError('Unsupported archive member type.')
            names[info.filename] = info
        if INDEX_MEMBER in names and names[INDEX_MEMBER].file_size > MAX_INDEX_BYTES:
            raise ArtifactSectionError('artifact_archive_limit', bound='index')
        _integer(lineage_count); _integer(zip_size)
        if lineage_count > MAX_LINEAGES:
            raise ArtifactSectionError('artifact_archive_limit', bound='lineages')
        if any(info.file_size > MAX_RATIO * max(1, info.compress_size) for info in infos):
            raise ArtifactSectionError('artifact_archive_limit', bound='ratio')
        if sum(info.file_size for info in infos) > MAX_ARCHIVE_BYTES:
            raise ArtifactSectionError('artifact_archive_limit', bound='uncompressed')
        if zip_size > MAX_ARCHIVE_BYTES:
            raise ArtifactSectionError('artifact_archive_limit', bound='zip')
        return names
    except ArtifactSectionError:
        raise
    except (ValueError, TypeError, AttributeError):
        raise ArtifactSectionError() from None


def validate_manifest(manifest, index, *, artifact_present):
    try:
        if not isinstance(manifest, dict):
            raise ArtifactValidationError('Invalid archive manifest.')
        schema = manifest.get('schema_version')
        if schema == 1 and type(schema) is int and artifact_present:
            raise ArtifactSectionError('artifact_archive_schema_mismatch')
        if type(schema) is not int or schema != 2:
            raise ArtifactValidationError('Invalid artifact archive schema.')
        expected = {'schema_version', 'archive_id', 'created_at', 'product', 'app_version', 'counts', 'attachments_included'}
        if 'artifacts' in manifest:
            expected.add('artifacts')
        _fields(manifest, expected)
        _token(manifest['archive_id']); _text(manifest['app_version'], 128, empty=True)
        if (not isinstance(manifest['created_at'], str) or not re.fullmatch(
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', manifest['created_at'])
                or manifest['product'] != 'agentchattr' or manifest['attachments_included'] is not False):
            raise ArtifactValidationError('Invalid archive manifest metadata.')
        datetime.strptime(manifest['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        count_keys = {'messages', 'jobs', 'rules', 'summaries'}
        if 'artifacts' in manifest['counts']:
            count_keys.add('artifacts')
        _fields(manifest['counts'], count_keys)
        for value in manifest['counts'].values():
            _integer(value)
        if artifact_present:
            artifact = manifest.get('artifacts')
            _fields(artifact, ('version', 'lineages', 'requests', 'versions', 'packets',
                               'markdown_bytes', 'source_bytes', 'copied_source_text'))
            if type(artifact['version']) is not int or artifact['version'] != 1 or artifact['copied_source_text'] is not True:
                raise ArtifactValidationError('Invalid artifact manifest version or source disclosure.')
            for key in ('lineages', 'requests', 'versions', 'packets', 'markdown_bytes', 'source_bytes'):
                _integer(artifact[key])
            if index is None or manifest.get('artifacts') != artifact_counts(index) or manifest['counts'].get('artifacts') != len(index['lineages']):
                raise ArtifactValidationError('Artifact manifest counts differ.')
        elif 'artifacts' in manifest or manifest['counts'].get('artifacts', 0) != 0:
            raise ArtifactValidationError('Artifact manifest names an absent section.')
    except ArtifactSectionError:
        raise
    except (ValueError, TypeError, KeyError):
        raise ArtifactSectionError() from None


def _bounded_read(zf, info, maximum):
    with zf.open(info, 'r') as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum or len(raw) != info.file_size:
        raise ValueError('Archive member length differs.')
    return raw


def preflight(zf, *, zip_size):
    """Pure structural validation before a driver may mutate ANY owner."""
    infos = zf.infolist()
    # Read the capped index before ratio/total checks so fixed precedence holds.
    # The preliminary header pass uses only index/member limits and structure.
    if len(infos) > MAX_MEMBERS:
        raise ArtifactSectionError('artifact_archive_limit', bound='members')
    index_info = next((row for row in infos if row.filename == INDEX_MEMBER), None)
    if index_info is not None and index_info.file_size > MAX_INDEX_BYTES:
        raise ArtifactSectionError('artifact_archive_limit', bound='index')
    try:
        index = validate_index(_bounded_read(zf, index_info, MAX_INDEX_BYTES)) if index_info else None
        names = validate_headers(infos, lineage_count=len(index['lineages']) if index else 0, zip_size=zip_size)
        if index is not None:
            validate_index(canonical_utf8(index), member_names=set(names))
        # Opening checks local-name agreement and stdlib overlap bounds without
        # inflating untrusted bodies. CRC/body failures are checked on reads.
        for info in infos:
            with zf.open(info, 'r'):
                pass
        if 'manifest.json' not in names:
            raise ArtifactSectionError()
        manifest = _unique_json(_bounded_read(zf, names['manifest.json'], MAX_ARCHIVE_BYTES))
        validate_manifest(manifest, index, artifact_present=index is not None or has_artifact_members(infos))
        return {'manifest': manifest, 'index': index}
    except ArtifactSectionError:
        raise
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, zipfile.BadZipFile, UnicodeError, RecursionError):
        raise ArtifactSectionError() from None


def read_lineage_objects(zf, lineage):
    """One bounded member at a time, outside engine/catalog boundaries."""
    objects = {}
    try:
        for version in lineage['versions']:
            limit = MAX_ARTIFACT_BYTES
            _integer(version['byte_length'], 1, limit)
            raw = _bounded_read(zf, zf.getinfo(member_name('version', version['version_id'])), limit)
            _text(raw.decode('utf-8'), limit)
            if len(raw) != version['byte_length'] or hashlib.sha256(raw).hexdigest() != version['sha256']:
                raise ValueError('Artifact bytes differ.')
            objects[('version', version['version_id'])] = raw
        for request in lineage['requests']:
            scope = request['scope']
            _integer(scope['byte_length'], 1, MAX_PACKET_BYTES)
            if len(scope['message_refs']) > MAX_PACKET_MESSAGES:
                raise ValueError('Too many source messages.')
            raw = _bounded_read(zf, zf.getinfo(member_name('packet', scope['packet_id'])), MAX_PACKET_BYTES)
            packet = json.loads(raw)
            if (_packet_scope(scope['packet_id'], packet) != scope or canonical_utf8(packet) != raw
                    or packet['channel'] != request['original_channel'] or packet['source_run'] != request['source_run']):
                raise ValueError('Artifact source differs.')
            objects[('packet', scope['packet_id'])] = raw
        return objects
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, UnicodeError, RecursionError, zipfile.BadZipFile):
        raise ArtifactLineageError() from None
