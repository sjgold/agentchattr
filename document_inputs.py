"""Pure validation of operator-supplied UTF-8 file snapshots, without file IO."""
import hashlib
import json
import unicodedata

from review_brief import MAX_INPUT_BYTES


MAX_DOCUMENT_BYTES = MAX_INPUT_BYTES
_FIELDS = {'version', 'kind', 'source_id', 'name', 'encoding',
           'byte_length', 'content_sha256', 'text'}


class DocumentInputError(ValueError):
    pass


class DocumentTooLarge(DocumentInputError):
    pass


def _name(value):
    if (type(value) is not str or not value.strip() or len(value) > 255
            or value in ('.', '..') or value.endswith(('.', ' '))
            or any(char in value for char in ('/', '\\', ':'))
            or any(unicodedata.category(char) in ('Cc', 'Cf')
                   or char in ('\u2028', '\u2029') for char in value)):
        raise DocumentInputError('Choose a valid file basename without paths or control characters.')
    try:
        encoded = value.encode('utf-8')
    except UnicodeError:
        raise DocumentInputError('The file name must be valid UTF-8.') from None
    if len(encoded) > 1024:
        raise DocumentInputError('The UTF-8 file name exceeds 1024 bytes.')
    return value


def preview_document(filename, content: bytes):
    """Return exact text and recomputed identity; the name asserts no provenance."""
    name = _name(filename)
    if type(content) is not bytes:
        raise DocumentInputError('File content must be bytes, without conversion.')
    if len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentTooLarge(
            f'File exceeds the {MAX_DOCUMENT_BYTES} byte limit. Reduce it explicitly; nothing was truncated.')
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError as failure:
        raise DocumentInputError(
            f'Invalid UTF-8 at byte offset {failure.start}. Save as UTF-8 and select the file again.') from None
    for offset, value in enumerate(content):
        if (value < 32 and value not in (9, 10, 13)) or value == 127:
            raise DocumentInputError(
                f'Control character U+{value:04X} at byte offset {offset}. Select plain UTF-8 text.')
    digest = hashlib.sha256(content).hexdigest()
    identity = json.dumps({'name': name, 'content_sha256': digest}, sort_keys=True,
                          ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return {'version': 1, 'kind': 'file', 'source_id': 'file:' + hashlib.sha256(identity).hexdigest(),
            'name': name, 'encoding': 'utf-8', 'byte_length': len(content),
            'content_sha256': digest, 'text': text}


def validate_document_snapshot(snapshot):
    """Recompute every field, accepting self-consistent snapshots without a ticket."""
    if (type(snapshot) is not dict or snapshot.keys() != _FIELDS
            or type(snapshot.get('version')) is not int or snapshot['version'] != 1
            or type(snapshot.get('byte_length')) is not int
            or any(type(snapshot.get(field)) is not str for field in
                   ('kind', 'source_id', 'name', 'encoding', 'content_sha256', 'text'))):
        raise DocumentInputError('Invalid file snapshot fields; preview the file again.')
    try:
        content = snapshot['text'].encode('utf-8')
    except UnicodeEncodeError as failure:
        offset = len(snapshot['text'][:failure.start].encode('utf-8'))
        raise DocumentInputError(f'Invalid UTF-8 snapshot text at byte offset {offset}.') from None
    canonical = preview_document(snapshot['name'], content)
    if snapshot != canonical:
        raise DocumentInputError('File snapshot does not match its text; preview the file again.')
    return canonical
