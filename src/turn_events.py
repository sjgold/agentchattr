"""Explicit session-event validation shared by adapters and durable admission."""
import json
import re

MAX_EVENT_BYTES = 512 * 1024
IDENTITY_FIELDS = ('brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')


class EventConflict(ValueError):
    pass


class EventAccessError(PermissionError):
    pass


class EventValidationError(ValueError):
    pass


def event_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise EventValidationError('Event ID must be a UUID hex identifier.')
    return value


def validate_content(kind, content):
    if kind not in ('final', 'question') or not isinstance(content, str) or not content.strip() or '\0' in content:
        raise EventValidationError('An explicit final or question with nonempty plain text is required.')
    try:
        size = len(content.encode('utf-8'))
    except UnicodeError:
        raise EventValidationError('Event text must be valid UTF-8.') from None
    if size > MAX_EVENT_BYTES:
        raise EventValidationError('Event text exceeds 512 KiB; nothing was truncated.')
    return content


def parse_session_response(response):
    """Only a declared final/question is a session event; no text heuristics."""
    if not isinstance(response, str):
        raise EventValidationError('Session response must be JSON text.')
    text = response.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if len(lines) < 3 or lines[0] not in ('```', '```json') or lines[-1] != '```':
            raise EventValidationError('Malformed session response fence.')
        text = '\n'.join(lines[1:-1])
    def unique_keys(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise EventValidationError('Session response contains duplicate JSON keys.')
            value[key] = item
        return value
    try:
        result = json.loads(text, object_pairs_hook=unique_keys)
    except ValueError:
        raise EventValidationError('Session response must declare final or question in a JSON object.') from None
    if not isinstance(result, dict) or set(result) != {'kind', 'content'}:
        raise EventValidationError('Session response requires exactly kind and content.')
    validate_content(result['kind'], result['content'])
    return result
