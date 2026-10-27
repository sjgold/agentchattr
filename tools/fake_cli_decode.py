"""Test-tool framing codec for frozen review brief responses, never authority."""
import json

BOUNDARY = '\n--- packet ---\n'
SOURCE_FOLLOWS = "after the line '--- packet ---'"


def decode_brief(text):
    if type(text) is not str:
        raise ValueError('Review brief response must be text.')
    try:
        context, end = json.JSONDecoder().raw_decode(text)
    except ValueError:
        # Preserve the old JSON decoder's whitespace handling for v1 only.
        value = json.loads(text)
        if isinstance(value, dict) and 'source_follows' in value:
            raise ValueError('Multi-file brief requires an exact boundary.') from None
        return value
    if isinstance(context, dict) and 'source_follows' in context:
        if (context['source_follows'] != SOURCE_FOLLOWS
                or not text[end:].startswith(BOUNDARY) or 'source' in context):
            raise ValueError('Multi-file brief boundary is missing or invalid.')
        return {**context, 'source': text[end+len(BOUNDARY):]}
    return json.loads(text)
