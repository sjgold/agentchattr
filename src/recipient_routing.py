"""Pure authored-address parsing and immutable recipient snapshot resolution."""

from collections import defaultdict, deque
import re

from turn_events import MAX_EVENT_BYTES


_NAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_-]*\Z')
_ADDRESS = re.compile(r'(?<![A-Za-z0-9_.+%\-])@([A-Za-z0-9_][A-Za-z0-9_-]*)')
_FENCE = re.compile(r' {0,3}(`{3,}|~{3,})(.*)\Z')
_ELLIPSIS = '\u2026'
_BACKTICKS = re.compile(r'`+')
_LINES = re.compile(r'[^\r\n]*(?:\r\n|\r|\n|$)')


def _text(value):
    if not isinstance(value, str) or '\0' in value:
        raise ValueError('Recipient text must be valid UTF-8 without NUL.')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError:
        raise ValueError('Recipient text must be valid UTF-8 without NUL.') from None
    if size > MAX_EVENT_BYTES:
        raise ValueError('Recipient text exceeds the supported byte limit.')
    return value


def _diagnostic(token):
    return token if len(token) <= 128 else token[:127] + _ELLIPSIS


def _paragraph_masks(text, mask, start, end):
    """Pair backtick runs with indexed lookahead, then pair visible quotes."""
    runs = [(m.start(), m.end()) for m in _BACKTICKS.finditer(text, start, end)]
    queues = defaultdict(deque)
    for left, right in runs:
        if mask[left] != 1:
            queues[right - left].append((left, right))
    covered_until = start
    for left, right in runs:
        if left < covered_until or mask[left] == 1:
            continue
        matching = queues[right - left]
        while matching and matching[0][0] <= left:
            matching.popleft()
        if matching:
            _, close_end = matching.popleft()
            for index in range(left, close_end):
                if mask[index] != 1:
                    mask[index] = 2
            covered_until = close_end

    opener = None
    for index in range(start, end):
        if mask[index]:
            continue
        char = text[index]
        if char not in ('"', '\u201c', '\u201d'):
            continue
        if opener is not None and char == opener[1]:
            for position in range(opener[0], index + 1):
                if not mask[position]:
                    mask[position] = 3
            opener = None
        else:
            opener = (index, '"' if char == '"' else '\u201d') if char != '\u201d' else None


def scan_addresses(text: str) -> dict:
    """Return ordered authored tokens and bounded ignored-address diagnostics."""
    _text(text)
    mask = bytearray(len(text))  # 1=fence, 2=code, 3=quote
    fence = None
    quoted = False
    offset = 0
    paragraph_start = 0
    paragraphs = []
    for line_match in _LINES.finditer(text):
        line = line_match[0]
        if not line:
            continue
        body = line.rstrip('\r\n')
        end = offset + len(line)
        marker = _FENCE.fullmatch(body)
        if fence is not None:
            mask[offset:end] = b'\1' * len(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
        elif marker:
            # Backtick info strings cannot contain backticks: ```x``` is inline.
            if marker[1][0] != '`' or '`' not in marker[2]:
                fence = (marker[1][0], len(marker[1]))
                quoted = False
                mask[offset:end] = b'\1' * len(line)
            elif quoted:
                mask[offset:end] = b'\3' * len(line)
        elif not body.strip():
            quoted = False
        elif quoted or body.lstrip(' \t').startswith('>'):
            quoted = True
            mask[offset:end] = b'\3' * len(line)
        if not body.strip():
            paragraphs.append((paragraph_start, offset))
            paragraph_start = end
        offset = end
    paragraphs.append((paragraph_start, len(text)))
    for start, end in paragraphs:
        _paragraph_masks(text, mask, start, end)

    tokens, ignored = [], []
    seen, ignored_seen = set(), set()
    consumed_until = 0
    for match in _ADDRESS.finditer(text):
        if match.start() < consumed_until:
            continue
        end = match.end()
        # Unicode suffixes make the whole address unknown, never a known prefix.
        while end < len(text) and (text[end].isalnum() or text[end] in '_-'):
            end += 1
        consumed_until = end
        token = _diagnostic(text[match.start() + 1:end].lower())
        reason = mask[match.start()]
        if reason:
            label = {1: 'fence', 2: 'code', 3: 'quote'}[reason]
            if (token, label) not in ignored_seen:
                ignored_seen.add((token, label))
                ignored.append({'token': token, 'reason': label})
        elif token not in seen:
            seen.add(token)
            tokens.append(token)
    return {'tokens': tokens, 'ignored': ignored}


def _snapshot(instances, online_names):
    if not isinstance(instances, dict) or not isinstance(online_names, set):
        raise ValueError('Invalid recipient snapshot.')
    for name in online_names:
        _snapshot_string(name)
    names, families = {}, defaultdict(list)
    for name, record in instances.items():
        _snapshot_string(name)
        if (not isinstance(record, dict)
                or record.get('name') != name
                or record.get('state') not in ('active', 'pending')
                or name.lower() in names):
            raise ValueError('Invalid recipient snapshot.')
        _snapshot_string(record.get('base'))
        _snapshot_string(record.get('identity_id'))
        names[name.lower()] = record
        families[record['base'].lower()].append(record)
    return names, families


def _snapshot_string(value):
    _text(value)
    if not value:
        raise ValueError('Invalid empty recipient snapshot field.')


def resolve_recipients(text: str, selected_names: list[str],
                       instances: dict[str, dict], online_names: set[str]) -> dict:
    """Resolve current identities; output describes audience, never delivery."""
    scanned = scan_addresses(text)
    names, families = _snapshot(instances, online_names)
    if not isinstance(selected_names, list):
        raise ValueError('Selected recipients must be a list of names.')
    selected, selected_seen, size = [], set(), 0
    for raw in selected_names:
        _text(raw)
        size += len(raw.encode('utf-8'))
        token = raw if raw.lower() in names else raw.removeprefix('@')
        if size > MAX_EVENT_BYTES or not token:
            raise ValueError('Invalid selected recipients or byte limit exceeded.')
        token = _diagnostic(token.lower())
        if token not in selected_seen:
            selected_seen.add(token)
            selected.append(token)
    tokens = scanned['tokens'] or selected
    result = {'mode': 'explicit' if scanned['tokens'] else 'selected' if selected else 'none',
              'tokens': tokens, 'ignored': scanned['ignored'], 'recipients': [], 'warnings': []}
    identities, warnings = set(), set()

    def warn(kind, token, candidates=()):
        if (kind, token) not in warnings:
            warnings.add((kind, token))
            result['warnings'].append({'kind': kind, 'token': token,
                                       'candidates': sorted(candidates)})

    def include(record, token):
        online = record['name'] in online_names
        if not online:
            warn('offline', token)
        if record['identity_id'] not in identities:
            identities.add(record['identity_id'])
            result['recipients'].append({'name': record['name'],
                                         'identity_id': record['identity_id'], 'online': online})

    for token in tokens:
        if token.endswith(_ELLIPSIS) or (result['mode'] == 'explicit' and not _NAME.fullmatch(token)):
            warn('unknown', token)
        elif token in ('all', 'both'):
            eligible = sorted((r for r in names.values() if r['state'] == 'active'
                               and r['name'] in online_names), key=lambda r: r['name'])
            if not eligible:
                warn('unavailable', token)
            for record in eligible:
                include(record, token)
        elif token in names:
            record = names[token]
            if record['state'] != 'active':
                warn('unavailable', token)
            else:
                include(record, token)
        else:
            family = [r for r in families.get(token, []) if r['state'] == 'active']
            if len(family) == 1:
                include(family[0], token)
            elif len(family) > 1:
                warn('ambiguous', token, [r['name'] for r in family])
            else:
                warn('unavailable' if token in families or result['mode'] == 'selected' else 'unknown', token)
    return result
