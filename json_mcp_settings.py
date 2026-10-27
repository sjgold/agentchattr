"""Add or remove one MCP server entry in a JSON client config (Antigravity agy mcp_config.json).

The user's file is edited at the text level: exactly one member of the top-level
``mcpServers`` object is inserted, replaced in place or deleted, and every other byte
(key order, unknown keys, indentation, separators, line endings, trailing newline) is
left as it was. The json module is used only to validate and to verify the result
structurally, including key order; the file is never re-serialised through it.
Anything unexpected is refused before any write. Messages and exceptions carry paths,
key names and SHA-256 digests only, never file contents or the bearer token.

Formatting of what we add: the new member copies the separator and indentation of the
member before it (or, in an empty object, the file's indent unit on new lines when the
file spans several lines, else one line). Two documented exceptions to byte
preservation, both undone by remove_exact when the file is unchanged since our write:
an empty ``mcpServers`` object written with inner whitespace (``{ }``) loses that
whitespace, and a missing ``mcpServers`` is appended as the last root member.

Ownership and integrity guards:
- An existing member under our name is refreshed or removed only if it has exactly the shape
  we write (the url key holding a loopback http URL, plus optionally headers with exactly one
  "Authorization: Bearer ..." value). Anything else is the user's and is refused, untouched.
- Every planned write is checked three ways: the bytes before and after the spliced region
  are identical to the original, only mcpServers.<entry> differs structurally (key order
  included), and the parsed result equals the expected value.
- If the write fails for any reason after a backup was made, that backup is deleted.

Strict parsing, by design: duplicate keys, a UTF-8 BOM, JSONC comments or trailing commas,
NaN/Infinity, non-finite numbers, mixed or bare-CR line endings and an existing empty file
are all refused rather than repaired.

Operational notes:
- The wrapper's lifetime lock file (<config>.agentchattr.lock, next to the config) is never
  deleted; it is empty and harmless.
- mcp_settings_path is not constrained beyond $VAR/~ expansion (relative paths resolve against
  the project directory). Requiring an absolute path is a possible later tightening.
- agy_running duplicates yaml_mcp_settings' process check; once the path-aware
  client_running lands there (branch hermes-running-path), reuse it instead.
- os.replace writes a new file: Windows gives it the directory's inherited ACL,
  POSIX mode bits are not copied, and a symlinked config becomes a regular file.
- Backups (mcp_config.json.<entry>-<UTC>-<hex>.bak) are never deleted automatically.
  They hold the user's own file, including any secrets of theirs, but never our token.
- A hard kill skips the stop hook: the entry and its token stay, and an orphaned
  mcp_config.json.*.tmp may remain. The next launch refreshes the entry (no new backup)
  and its normal stop removes it; remove_exact(path) also works without a receipt.
- agy reads this file when it starts; an agy that is already running keeps the servers it
  loaded. agy_running() is a read-only check for that.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_ENTRY = 'agentchattr-fork'
DEFAULT_URL_KEY = 'serverURL'
SECTION = 'mcpServers'
RESERVED_ENTRIES = ('agentchattr',)
_WS = ' \t\r\n'


class JsonSettingsError(ValueError):
    """The file was left unchanged because its shape or content was unexpected."""


@dataclass
class ApplyReceipt:
    path: Path
    entry: str
    backup_path: Path | None      # pre-write copy without our entry; None if the file was new or already held it
    backup_sha256: str | None
    written_sha256: str
    created_file: bool
    created_section: bool
    prior_sha256: str | None = None   # sha256 of the bytes this write replaced; None if the file was new
    url_key: str = DEFAULT_URL_KEY


@dataclass
class RemovalResult:
    path: Path
    status: str                   # 'absent', 'restored-exact', 'deleted-created-file' or 'removed-entry'
    matches_backup: bool | None   # structural equality with the backup; None when there is no backup
    differing_keys: list


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entry_name(raw=None) -> str:
    """Validated entry name; never the user's own ``agentchattr`` entry."""
    name = DEFAULT_ENTRY if raw is None else raw
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', name):
        raise JsonSettingsError('mcp_entry_name must be 1-64 letters, digits, ".", "_" or "-".')
    if name.lower() in RESERVED_ENTRIES:
        raise JsonSettingsError(f'mcp_entry_name must not be {name!r}; that entry belongs to the user.')
    return name


def url_key(raw=None) -> str:
    key = DEFAULT_URL_KEY if raw is None else raw
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', key) or key == 'headers':
        raise JsonSettingsError('mcp_http_key must be a plain JSON key name other than "headers".')
    return key


# --- Reading and locating ----------------------------------------------------

def _decode(raw: bytes, path: Path):
    if raw.startswith(b'\xef\xbb\xbf'):
        raise JsonSettingsError(f'{path.name} starts with a byte-order mark; nothing was changed.')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        raise JsonSettingsError(f'{path.name} is not UTF-8 text; nothing was changed.') from None
    if '\r\n' in text and re.search(r'(?<!\r)\n', text):
        raise JsonSettingsError(f'{path.name} mixes line endings; nothing was changed.')
    if re.search(r'\r(?!\n)', text):
        raise JsonSettingsError(f'{path.name} uses bare carriage returns; nothing was changed.')
    newline = '\r\n' if '\r\n' in text else '\n'
    return text, newline


def _pairs(path):
    def hook(pairs):
        seen = {}
        for key, value in pairs:
            if key in seen:
                raise JsonSettingsError(f'{path.name} declares a key more than once; nothing was changed.')
            seen[key] = value
        return seen
    return hook


def _load(text: str, path: Path):
    """Parsed value. Duplicate keys, NaN/Infinity and overflowing numbers are refused;
    decoder details are reduced to a line number because they can quote file text."""
    def finite(literal):
        value = float(literal)
        if not math.isfinite(value):
            raise JsonSettingsError(f'{path.name} holds a number that is not finite; nothing was changed.')
        return value

    def constant(_name):
        raise JsonSettingsError(f'{path.name} holds NaN or Infinity; nothing was changed.')
    try:
        return json.loads(text, object_pairs_hook=_pairs(path), parse_float=finite, parse_constant=constant)
    except json.JSONDecodeError as error:
        raise JsonSettingsError(f'{path.name} is not valid JSON near line {error.lineno}; nothing was changed.') from None
    except RecursionError:
        raise JsonSettingsError(f'{path.name} is nested too deeply; nothing was changed.') from None


def _skip_ws(text: str, index: int) -> int:
    while index < len(text) and text[index] in _WS:
        index += 1
    return index


def _string_end(text: str, index: int) -> int:
    index += 1
    while text[index] != '"':
        index += 2 if text[index] == '\\' else 1
    return index + 1


def _value_end(text: str, index: int) -> int:
    """End of the value starting at ``index``. The text has already passed json.loads."""
    if text[index] == '"':
        return _string_end(text, index)
    if text[index] in '{[':
        depth = 0
        while True:
            char = text[index]
            if char == '"':
                index = _string_end(text, index)
                continue
            if char in '{[':
                depth += 1
            elif char in '}]':
                depth -= 1
                if depth == 0:
                    return index + 1
            index += 1
    while index < len(text) and text[index] not in ',}]' + _WS:
        index += 1
    return index


@dataclass
class _Member:
    key: str
    key_start: int
    key_end: int
    value_start: int
    value_end: int


@dataclass
class _Object:
    open: int
    close: int
    members: list

    def find(self, key):
        return next((m for m in self.members if m.key == key), None)


def _object_at(text: str, open_index: int) -> _Object:
    members = []
    index = _skip_ws(text, open_index + 1)
    while text[index] != '}':
        key_end = _string_end(text, index)
        colon = _skip_ws(text, key_end)
        value_start = _skip_ws(text, colon + 1)
        value_end = _value_end(text, value_start)
        members.append(_Member(json.loads(text[index:key_end]), index, key_end, value_start, value_end))
        index = _skip_ws(text, value_end)
        if text[index] == ',':
            index = _skip_ws(text, index + 1)
    return _Object(open_index, index, members)


@dataclass
class _Layout:
    root: _Object
    section: _Object | None       # the mcpServers object, or None when absent
    entry: _Member | None         # our member inside mcpServers, or None


def _layout(text: str, path: Path, entry: str):
    """(parsed value, _Layout). Refuses every shape we will not edit."""
    value = _load(text, path)
    if not isinstance(value, dict):
        raise JsonSettingsError(f'{path.name} root is not a JSON object; nothing was changed.')
    root = _object_at(text, _skip_ws(text, 0))
    if SECTION not in value:
        return value, _Layout(root, None, None)
    if not isinstance(value[SECTION], dict):
        raise JsonSettingsError(f'{path.name} {SECTION} is not an object; nothing was changed.')
    section = _object_at(text, root.find(SECTION).value_start)
    member = section.find(entry)
    if member is not None and not isinstance(value[SECTION][entry], dict):
        raise JsonSettingsError(f'{path.name} {SECTION}.{entry} is not an object; nothing was changed.')
    return value, _Layout(root, section, member)


# --- Text edits ------------------------------------------------------------

def _line_indent(text: str, index: int) -> str:
    start = text.rfind('\n', 0, index) + 1
    return re.match(r'[ \t]*', text[start:]).group(0)


def _file_unit(text: str) -> str:
    match = re.search(r'\n([ \t]+)\S', text)
    return match.group(1) if match else '  '


@dataclass
class _Style:
    multiline: bool
    indent: str                   # indentation of the line that holds the new member
    unit: str
    newline: str
    colon: str
    item_sep: str                 # whitespace after a comma when on one line
    sep: str = ''                 # whitespace between the comma and a new last member


def _format(value, style: _Style, indent: str) -> str:
    if not isinstance(value, dict):
        return json.dumps(value)
    if style.multiline:
        inner = indent + style.unit
        items = [inner + json.dumps(k) + style.colon + _format(v, style, inner) for k, v in value.items()]
        return '{' + style.newline + (',' + style.newline).join(items) + style.newline + indent + '}'
    items = [json.dumps(k) + style.colon + _format(v, style, indent) for k, v in value.items()]
    return '{' + (',' + style.item_sep).join(items) + '}'


def _style_in(text: str, obj: _Object, newline: str) -> _Style:
    """How a new last member of ``obj`` should look, copied from its current last member."""
    parent = _line_indent(text, obj.open)
    if obj.members:
        last = obj.members[-1]
        gap_from = obj.open + 1 if len(obj.members) == 1 else text.rindex(',', 0, last.key_start) + 1
        gap = text[gap_from:last.key_start]
        colon = text[last.key_end:last.value_start]
        if '\n' in colon:
            colon = ': '
        multiline = '\n' in gap
        if not multiline and len(obj.members) == 1 and not gap:
            gap = ' ' if colon.endswith(' ') else ''     # `{"a": 1}` says nothing about `, `; follow the colon
        indent = gap.rsplit('\n', 1)[-1] if multiline else parent
        unit = indent[len(parent):] if multiline and indent.startswith(parent) and len(indent) > len(parent) else _file_unit(text)
        return _Style(multiline, indent, unit, newline, colon, ' ' if multiline else gap, gap)
    multiline = '\n' in text.strip(_WS)
    unit = _file_unit(text)
    return _Style(multiline, parent + unit if multiline else parent, unit, newline, ': ', ' ')


def _splice(text: str, start: int, end: int, insert: str):
    """(new text, (start, end, len(insert))): text[start:end] replaced by insert."""
    return text[:start] + insert + text[end:], (start, end, len(insert))


def _append_member(text: str, obj: _Object, key: str, value, newline: str):
    style = _style_in(text, obj, newline)
    member = json.dumps(key) + style.colon + _format(value, style, style.indent)
    if obj.members:
        last = obj.members[-1]
        return _splice(text, last.value_end, last.value_end, ',' + style.sep + member)
    if style.multiline:
        parent = _line_indent(text, obj.open)
        inner = newline + style.indent + member + newline + parent
    else:
        inner = member
    return _splice(text, obj.open + 1, obj.close, inner)


def _replace_value(text: str, obj: _Object, member: _Member, value, newline: str):
    """Refresh our entry in place, keeping whether its value spans lines."""
    old = text[member.value_start:member.value_end]
    multiline = '\n' in old
    indent = _line_indent(text, member.key_start)
    parent = _line_indent(text, obj.open)
    unit = indent[len(parent):] if indent.startswith(parent) and len(indent) > len(parent) else _file_unit(text)
    colon = text[member.key_end:member.value_start]
    item_sep = ' ' if multiline or re.search(r',\s', old) or ': ' in old else ''
    style = _Style(multiline, indent, unit, newline, ': ' if '\n' in colon else colon, item_sep)
    return _splice(text, member.value_start, member.value_end, _format(value, style, indent))


def _remove_member(text: str, obj: _Object, member: _Member):
    index = obj.members.index(member)
    if len(obj.members) == 1:
        return _splice(text, obj.open + 1, obj.close, '')
    if index > 0:
        return _splice(text, obj.members[index - 1].value_end, member.value_end, '')
    return _splice(text, member.key_start, obj.members[1].key_start, '')


def _then(first, second):
    """Old-text span (start, end) covering two successive splices; ``second`` is in the
    coordinates of the text the first splice produced."""
    start, end, inserted = first
    a, b, _ = second

    def back(x, low):
        if x <= start:
            return x
        if x >= start + inserted:
            return x - inserted + end
        return start if low else end
    return min(start, back(a, True)), max(end, back(b, False)), None


def _check_outside(old: str, new: str, region, path: Path) -> None:
    """Every byte before and after the spliced span is unchanged (M3), independent of the
    structural checks: a splice cannot silently touch whitespace elsewhere."""
    start, end = region[0], region[1]
    tail = len(old) - end
    if len(new) < start + tail or new[:start] != old[:start] or new[len(new) - tail:] != old[end:]:
        raise JsonSettingsError(f'{path.name}: the planned edit would change bytes outside the spliced region; '
                                'nothing was changed.')


_OUR_URL = re.compile(r'http://(?:127\.0\.0\.1|localhost):\d{1,5}/')


def _looks_ours(value, key: str) -> bool:
    """The shape this module writes: the url key (a loopback http URL) plus, optionally,
    headers with exactly one Authorization: Bearer value. Anything else is the user's."""
    if not isinstance(value, dict) or set(value) not in ({key}, {key, 'headers'}):
        return False
    if not isinstance(value[key], str) or not _OUR_URL.match(value[key]):
        return False
    headers = value.get('headers', {'Authorization': 'Bearer '})
    return (isinstance(headers, dict) and set(headers) == {'Authorization'}
            and isinstance(headers['Authorization'], str) and headers['Authorization'].startswith('Bearer '))


def _refuse_unless_ours(parsed: dict, entry: str, key: str, path: Path) -> None:
    if not _looks_ours(parsed[SECTION][entry], key):
        raise JsonSettingsError(f'{path.name} {SECTION}.{entry} was not written by agentchattr (unexpected keys or '
                                f'URL); it is left untouched. Pick another mcp_entry_name or remove it by hand.')


# --- Verification ----------------------------------------------------------

def _same(a, b) -> bool:
    """Deep equality that also requires identical key order and identical scalar types."""
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a) == list(b) and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _diff_keys(before, after, prefix=''):
    """Key paths (no values) that differ between two objects, one level into mcpServers."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return [prefix or '<root>'] if not _same(before, after) else []
    paths = []
    for key in sorted(set(before) | set(after)):
        where = f'{prefix}.{key}' if prefix else key
        if key not in before or key not in after:
            paths.append(where)
        elif key == SECTION and not prefix and isinstance(before[key], dict) and isinstance(after[key], dict):
            paths += _diff_keys(before[key], after[key], where)
        elif not _same(before[key], after[key]):
            paths.append(where)
    if not paths and list(before) != list(after):
        paths.append((prefix or '<root>') + ' (key order)')
    return paths


def _without(value: dict, entry: str) -> dict:
    """``value`` minus mcpServers.<entry>; an mcpServers left empty reads as absent."""
    value = dict(value)
    if isinstance(value.get(SECTION), dict):
        section = {k: v for k, v in value[SECTION].items() if k != entry}
        if section:
            value[SECTION] = section
        else:
            value.pop(SECTION)
    return value


def verify_only_one_key_changed(before_text: str, after_text: str, *, entry: str = DEFAULT_ENTRY,
                                path: Path = Path('mcp_config.json')) -> list:
    """Raise unless the only structural change is mcpServers.<entry> (and an mcpServers that
    holds nothing else being created or removed with it). Key order counts as structure.
    Returns the changed key paths."""
    before = _load(before_text, path)
    after = _load(after_text, path)
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise JsonSettingsError(f'{path.name} root is not a JSON object.')
    # _without drops an mcpServers left empty, so pin its position separately when both sides
    # have one. A created or removed mcpServers may sit anywhere (apply checks it is appended last).
    moved = SECTION in before and SECTION in after and list(before) != list(after)
    if moved or not _same(_without(before, entry), _without(after, entry)):
        unexpected = [p for p in _diff_keys(before, after) if p not in (SECTION, f'{SECTION}.{entry}')]
        raise JsonSettingsError(f'{path.name}: unexpected structural change at {", ".join(unexpected) or "<order>"}.')
    return _diff_keys(before, after)


# --- File I/O --------------------------------------------------------------

class _ChangedUnderUs(Exception):
    """The file no longer holds the bytes the plan was made from."""


def _current_bytes(path: Path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _atomic_write(path: Path, data: bytes, expect) -> None:
    """Replace path with data only if it still holds ``expect`` (None means: must not exist).

    The check runs immediately before os.replace, which narrows but cannot close the window
    against another writer; callers re-plan once on a mismatch and then refuse."""
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if _current_bytes(path) != expect:
            raise _ChangedUnderUs()
        for attempt in range(8):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(min(0.005 * 2 ** attempt, 0.08))
    finally:
        Path(temporary).unlink(missing_ok=True)


def _backup(path: Path, raw: bytes, entry: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = path.with_name(f'{path.name}.{entry}-{stamp}-{secrets.token_hex(3)}.bak')
    with backup.open('xb') as handle:      # reserve the name; never overwrite an earlier backup
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    shutil.copystat(path, backup)
    if backup.read_bytes() != raw:
        raise JsonSettingsError(f'Backup of {path.name} could not be verified; nothing was changed.')
    return backup


def resolve_settings_path(raw, project_dir=None) -> Path:
    """Expand $VARS and ~ exactly once; refuse an unset variable rather than guessing a home."""
    if not isinstance(raw, str) or not raw.strip():
        raise JsonSettingsError("mcp_inject = 'json_entry_file' requires mcp_settings_path.")
    for groups in re.findall(r'\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)|%([A-Za-z_]\w*)%', raw):
        name = next(g for g in groups if g)
        if not os.environ.get(name, '').strip():
            raise JsonSettingsError(f'mcp_settings_path uses {name}, which is not set or is empty.')
    expanded = os.path.expanduser(os.path.expandvars(raw))
    if re.search(r'\$\{?[A-Za-z_]|%[A-Za-z_][A-Za-z0-9_]*%', expanded):
        raise JsonSettingsError('mcp_settings_path names an environment variable that is not set.')
    if expanded.startswith('~'):
        raise JsonSettingsError('mcp_settings_path starts with ~ but no home directory could be found.')
    target = Path(expanded)
    if not target.is_absolute():
        target = Path(project_dir or Path.cwd()) / target
    return target


def _entry_value(url: str, token: str, key: str) -> dict:
    if not isinstance(url, str) or not isinstance(token, str):
        raise JsonSettingsError('Server URL and token must be text; nothing was changed.')
    return {key: url, **({'headers': {'Authorization': 'Bearer ' + token}} if token else {})}


def apply(path, url: str, token: str, *, entry: str = DEFAULT_ENTRY, key: str = DEFAULT_URL_KEY,
          log=print) -> ApplyReceipt:
    """Insert or refresh mcpServers.<entry>. Caller holds the per-file write lock.

    Backup: a timestamped sibling with the exact prior bytes, made only when the file exists and
    does not already hold the entry (so a backup never contains our bearer token). A missing file
    in an existing directory is created; a missing directory is refused.
    If the file changes between reading and replacing it, the plan is redone once, then refused."""
    path = Path(path)
    entry, key = entry_name(entry), url_key(key)
    if not path.parent.is_dir():
        raise JsonSettingsError(f'{path.parent} does not exist; nothing was changed.')
    for attempt in range(2):
        raw = _current_bytes(path)
        plan = _plan_apply(path, raw, entry, _entry_value(url, token, key), key)
        backup = backup_sha = None
        if raw is not None and not plan['had_entry']:
            backup, backup_sha = _backup(path, raw, entry), _sha256(raw)
        try:
            _atomic_write(path, plan['data'], raw)
        except _ChangedUnderUs:
            if backup is not None:
                backup.unlink(missing_ok=True)       # our own backup of a version we did not edit
            continue
        except BaseException:
            if backup is not None:
                backup.unlink(missing_ok=True)       # nothing was written, so the backup has no purpose
            raise
        if backup is not None:
            log(f'  Backed up {path.name} -> {backup} (sha256 {backup_sha})')
        log(f'  {"Refreshed" if plan["had_entry"] else "Added"} {SECTION}.{entry} in {path} (sha256 {_sha256(plan["data"])})')
        return ApplyReceipt(path, entry, backup, backup_sha, _sha256(plan['data']), raw is None, plan['created_section'],
                            None if raw is None else _sha256(raw), key)
    raise JsonSettingsError(f'{path.name} kept changing while it was being updated (is the client writing it?); '
                            'nothing of ours was written.')


def _plan_apply(path: Path, raw, entry: str, value: dict, key: str = DEFAULT_URL_KEY) -> dict:
    """Validate and build the new bytes from ``raw`` (None for a missing file). No side effects."""
    if raw is None:
        style = _Style(True, '', '  ', '\n', ': ', ' ')
        text = _format({SECTION: {entry: value}}, style, '') + '\n'
        if not _same(_load(text, path), {SECTION: {entry: value}}):
            raise JsonSettingsError(f'Could not create {path.name} safely; nothing was changed.')
        return {'data': text.encode('utf-8'), 'had_entry': False, 'created_section': True}
    text, newline = _decode(raw, path)
    parsed, layout = _layout(text, path, entry)
    created_section = False
    if layout.entry is not None:
        _refuse_unless_ours(parsed, entry, key, path)
        new_text, region = _replace_value(text, layout.section, layout.entry, value, newline)
    elif layout.section is not None:
        new_text, region = _append_member(text, layout.section, entry, value, newline)
    else:
        new_text, region = _append_member(text, layout.root, SECTION, {entry: value}, newline)
        created_section = True
    _check_outside(text, new_text, region, path)
    verify_only_one_key_changed(text, new_text, entry=entry, path=path)
    expected = dict(parsed)
    expected[SECTION] = {**expected.get(SECTION, {}), entry: value}
    if not _same(_load(new_text, path), expected):
        raise JsonSettingsError(f'Could not update {path.name} safely; nothing was changed.')
    return {'data': new_text.encode('utf-8'), 'had_entry': layout.entry is not None, 'created_section': created_section}


def remove_exact(path, *, entry: str = DEFAULT_ENTRY, receipt: ApplyReceipt | None = None, key: str | None = None,
                 log=print) -> RemovalResult:
    """Remove exactly mcpServers.<entry>; caller holds the per-file write lock.

    An entry that does not have the shape apply() writes (``key``, default the receipt's url key)
    is refused, never deleted. If the file is still byte-identical to what apply() wrote, the
    backup bytes are restored (or the file we created is deleted). Otherwise only our member is
    deleted and the result is checked to differ from the current file by that entry alone.
    Either way the result is compared structurally with the backup and reported."""
    path = Path(path)
    entry = entry_name(entry)
    key = url_key(key if key is not None else (receipt.url_key if receipt else None))
    for attempt in range(2):
        try:
            return _remove_once(path, entry, receipt, log, key)
        except _ChangedUnderUs:
            continue
    raise JsonSettingsError(f'{path.name} kept changing while {SECTION}.{entry} was being removed; '
                            'remove it by hand or stop the client and retry.')


def _verified_backup(receipt):
    """Backup bytes if present and still matching the recorded sha256, else None."""
    if not receipt or not receipt.backup_path:
        return None
    try:
        original = receipt.backup_path.read_bytes()
    except OSError:
        return None
    return original if _sha256(original) == receipt.backup_sha256 else None


def _remove_once(path: Path, entry: str, receipt, log, key: str = DEFAULT_URL_KEY) -> RemovalResult:
    raw = _current_bytes(path)
    if raw is None:
        return RemovalResult(path, 'absent', None, [])
    text, newline = _decode(raw, path)
    parsed, layout = _layout(text, path, entry)
    if layout.entry is None:
        return RemovalResult(path, 'absent', None, [])
    _refuse_unless_ours(parsed, entry, key, path)
    original = _verified_backup(receipt)
    unchanged_since_write = bool(receipt) and _sha256(raw) == receipt.written_sha256
    if unchanged_since_write and receipt.created_file:
        if _current_bytes(path) != raw:
            raise _ChangedUnderUs()
        path.unlink()
        log(f'  Removed {path} (created for this run; sha256 matched)')
        return RemovalResult(path, 'deleted-created-file', True, [])
    if unchanged_since_write and original is not None:
        _atomic_write(path, original, raw)
        log(f'  Restored {path.name} from backup (sha256 {receipt.backup_sha256})')
        return RemovalResult(path, 'restored-exact', True, [])
    # Edited since our write, or the backup is missing/tampered: delete only our member (checked).
    new_text, region = _remove_member(text, layout.section, layout.entry)
    expected = dict(parsed)
    expected[SECTION] = {k: v for k, v in parsed[SECTION].items() if k != entry}
    if receipt and receipt.created_section and len(layout.section.members) == 1:
        root = _object_at(new_text, _skip_ws(new_text, 0))
        new_text, second = _remove_member(new_text, root, root.find(SECTION))
        region = _then(region, second)
        expected.pop(SECTION)
    _check_outside(text, new_text, region, path)
    verify_only_one_key_changed(text, new_text, entry=entry, path=path)
    if not _same(_load(new_text, path), expected):
        raise JsonSettingsError(f'Could not remove {SECTION}.{entry} from {path.name} safely; file left unchanged.')
    data = new_text.encode('utf-8')
    _atomic_write(path, data, raw)
    matches, differing = None, []
    if original is not None:
        differing = _diff_keys(_load(_decode(original, path)[0], path), expected)
        matches = not differing
    elif receipt and receipt.backup_path:
        matches, differing = False, ['<backup missing or changed>']
    log(f'  Removed {SECTION}.{entry} from {path.name} (sha256 {_sha256(data)})'
        + ('' if matches is None else ('; matches backup' if matches else f'; differs from backup at {", ".join(differing)}')))
    return RemovalResult(path, 'removed-entry', matches, differing)


def _text(output) -> str:
    return output.decode('utf-8', errors='replace') if isinstance(output, bytes) else (output or '')


def _windows_executable_paths() -> list:
    """Full image paths of the processes this user may query (EnumProcesses +
    OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION) + QueryFullProcessImageNameW).
    Executable paths only: no command lines, arguments or environment are read."""
    import ctypes
    from ctypes import wintypes
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi.EnumProcesses.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    psapi.EnumProcesses.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                    ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    size = 1024
    while True:
        pids = (wintypes.DWORD * size)()
        needed = wintypes.DWORD()
        if not psapi.EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(needed)):
            raise OSError('EnumProcesses failed')
        if needed.value < ctypes.sizeof(pids):
            break
        size *= 2
    paths = []
    for pid in pids[:needed.value // ctypes.sizeof(wintypes.DWORD)]:
        handle = kernel32.OpenProcess(0x1000, False, pid) if pid else None   # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            continue                       # system or other users' processes; the image-name check still sees them
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                paths.append(buffer.value)
        finally:
            kernel32.CloseHandle(handle)
    return paths


def _list_processes() -> list:
    """(image name, executable path or None) per process. Raises when the list cannot be read."""
    if sys.platform == 'win32':
        tasklist = os.path.join(os.environ.get('SystemRoot') or r'C:\Windows', 'System32', 'tasklist.exe')
        output = _text(subprocess.run([tasklist, '/FO', 'CSV', '/NH'], capture_output=True, timeout=15,
                                      creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout)
        names = [line.split('","', 1)[0].strip('"') for line in output.splitlines() if line.startswith('"')]
        if not names:
            raise ValueError('tasklist listed no processes')
        return [(name, None) for name in names] + [(os.path.basename(p), p) for p in _windows_executable_paths()]
    output = _text(subprocess.run(['ps', '-A', '-o', 'comm='], capture_output=True, timeout=15).stdout)
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise ValueError('ps listed no processes')
    return [(Path(line).name, line if line.startswith('/') else None) for line in lines]


def _default_install_root():
    if sys.platform == 'win32' and os.environ.get('LOCALAPPDATA', '').strip():
        return os.path.join(os.environ['LOCALAPPDATA'], 'agy', 'bin')
    return None


def _normalised_path(raw: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.realpath(raw)))


def _is_under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip('\\/') + os.sep)


def agy_running(image_names=('agy.exe', 'agy'), install_root=None, lister=None) -> bool | None:
    """Read-only check: is agy running? Matches by image name OR by an executable path under
    agy's install root (default %LOCALAPPDATA%\\agy\\bin; resolved, normcase/normpath, prefix
    match on a separator boundary). Lists image names and executable paths only, never
    command lines, arguments or environment.

    True if either check matches; None when the process list could not be read, no executable
    path could be read, or no install root is known (POSIX without install_root, or
    LOCALAPPDATA unset); False only when both checks ran and found nothing. ``lister`` returns (image name, path or None) pairs; tests
    inject a fake one. Limitation: an agy copied or started from outside its install root
    under another image name (or through node.exe) is not detected."""
    wanted = {name.lower() for name in image_names}
    root = install_root if install_root is not None else _default_install_root()
    try:
        processes = list((lister or _list_processes)())
        root = _normalised_path(root) if root else None
        for name, path in processes:
            if name and name.lower() in wanted:
                return True
            if path and root and _is_under(_normalised_path(path), root):
                return True
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    # False needs both checks to have run: no executable path at all (every OpenProcess
    # refused, or a names-only lister) means the path check did not.
    return False if processes and root and any(path for _, path in processes) else None
