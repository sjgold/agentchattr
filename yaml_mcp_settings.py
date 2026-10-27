"""Add or remove one MCP server entry in a YAML client config (Hermes config.yaml).

The user's file is edited at the text level: exactly one entry under the
top-level ``mcp_servers`` block mapping is inserted or deleted, and every other
byte (comments, ordering, quoting, line endings, BOM) is left as it was.
PyYAML is used only to locate nodes and to verify the result structurally; the
file is never re-serialised through it. Anything unexpected is refused before
any write. Messages and exceptions carry paths, key names and SHA-256 digests
only, never file contents or the bearer token.

Operational notes:
- os.replace writes a new file: Windows gives it the directory's inherited ACL,
  POSIX mode bits are not copied, and a symlinked config.yaml becomes a regular file.
- Backups (config.yaml.agentchattr-uat-<UTC>-<hex>.bak) are never deleted
  automatically. They hold the user's own file, including any secrets of theirs, but
  never our token; prune old ones by hand.
- A hard kill skips the stop hook: the entry and its token stay, and an orphaned
  config.yaml.*.tmp may remain. The next launch refreshes the entry (no new backup) and
  its normal stop removes it; remove_exact(path) also works without a receipt.
- The wrapper's lifetime lock file sits next to config.yaml, so taking it can create a
  missing HERMES_HOME directory before apply() checks that the directory exists.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_ENTRY = 'agentchattr-uat'
SECTION = 'mcp_servers'
_BOM = '﻿'


class YamlSettingsError(ValueError):
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


@dataclass
class RemovalResult:
    path: Path
    status: str                   # 'absent', 'restored-exact', 'deleted-created-file' or 'removed-entry'
    matches_backup: bool | None   # structural equality with the backup; None when there is no backup
    differing_keys: list


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _yaml():
    try:
        import yaml
    except ImportError:
        raise YamlSettingsError('PyYAML is required to verify YAML settings; nothing was changed.') from None
    return yaml


# --- Reading and locating ----------------------------------------------------

def _decode(raw: bytes, path: Path):
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        raise YamlSettingsError(f'{path.name} is not UTF-8 text; nothing was changed.') from None
    bom = text.startswith(_BOM)
    if bom:
        text = text[1:]
    if '\r\n' in text and re.search(r'(?<!\r)\n', text):
        raise YamlSettingsError(f'{path.name} mixes line endings; nothing was changed.')
    if re.search(r'\r(?!\n)', text):
        raise YamlSettingsError(f'{path.name} uses bare carriage returns; nothing was changed.')
    if re.search('[\u0085  ]', text):
        raise YamlSettingsError(f'{path.name} uses Unicode line separators; nothing was changed.')
    newline = '\r\n' if '\r\n' in text else '\n'
    return text, bom, newline


def _encode(text: str, bom: bool) -> bytes:
    return ((_BOM if bom else '') + text).encode('utf-8')


def _load(text: str, path: Path):
    """Structural value (safe_load); YAML error details are dropped because they quote file text."""
    yaml = _yaml()
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as error:
        mark = getattr(error, 'problem_mark', None)
        where = f' near line {mark.line + 1}' if mark else ''
        raise YamlSettingsError(f'{path.name} is not valid YAML{where}; nothing was changed.') from None


def _compose(text: str, path: Path):
    yaml = _yaml()
    try:
        documents = list(yaml.compose_all(text))
    except yaml.YAMLError as error:
        mark = getattr(error, 'problem_mark', None)
        where = f' near line {mark.line + 1}' if mark else ''
        raise YamlSettingsError(f'{path.name} is not valid YAML{where}; nothing was changed.') from None
    if len(documents) > 1:
        raise YamlSettingsError(f'{path.name} holds several YAML documents; nothing was changed.')
    return documents[0] if documents else None


def _scalar_key(node):
    yaml = _yaml()
    return node.value if isinstance(node, yaml.ScalarNode) else None


def _line_start(text: str, index: int) -> int:
    return text.rfind('\n', 0, index) + 1


def _after_line(text: str, index: int) -> int:
    """Index of the start of the line following the one that holds ``index``.

    A node's end mark often sits at column 0 of the next line already."""
    if index > 0 and text[index - 1] == '\n':
        return index
    newline = text.find('\n', index)
    return len(text) if newline < 0 else newline + 1


@dataclass
class _Layout:
    root_kind: str            # 'empty' or 'mapping'
    section_key: object       # key node of mcp_servers, or None
    section_value: object     # value node, or None
    entry_key: object         # key node of our entry inside mcp_servers, or None
    entry_value: object


def _layout(text: str, path: Path, entry: str) -> _Layout:
    yaml = _yaml()
    root = _compose(text, path)
    if root is None or (isinstance(root, yaml.ScalarNode) and root.tag.endswith(':null')):
        return _Layout('empty', None, None, None, None)
    if not isinstance(root, yaml.MappingNode) or root.flow_style:
        raise YamlSettingsError(f'{path.name} root is not a block mapping; nothing was changed.')
    keys = [_scalar_key(k) for k, _ in root.value]
    if '<<' in keys:
        raise YamlSettingsError(f'{path.name} uses a top-level merge key; nothing was changed.')
    matches = [(k, v) for k, v in root.value if _scalar_key(k) == SECTION]
    if len(matches) > 1:
        raise YamlSettingsError(f'{path.name} declares {SECTION} more than once; nothing was changed.')
    if not matches:
        return _Layout('mapping', None, None, None, None)
    key, value = matches[0]
    # PyYAML nodes do not carry their anchor; an anchored or aliased value's text starts with & or *.
    value_text = text[value.start_mark.index:value.end_mark.index]
    if value_text.startswith(('*', '&')):
        raise YamlSettingsError(f'{path.name} {SECTION} uses an anchor or alias; nothing was changed.')
    if isinstance(value, yaml.ScalarNode):
        if not value.tag.endswith(':null') or value_text.strip():
            raise YamlSettingsError(f'{path.name} {SECTION} is not a mapping; nothing was changed.')
        return _Layout('mapping', key, value, None, None)
    if not isinstance(value, yaml.MappingNode):
        raise YamlSettingsError(f'{path.name} {SECTION} is not a mapping; nothing was changed.')
    if value.flow_style:
        if value.value:
            raise YamlSettingsError(f'{path.name} {SECTION} is a non-empty flow mapping; nothing was changed.')
        return _Layout('mapping', key, value, None, None)
    child_keys = [_scalar_key(k) for k, _ in value.value]
    if '<<' in child_keys:
        raise YamlSettingsError(f'{path.name} {SECTION} uses a merge key; nothing was changed.')
    if child_keys.count(entry) > 1:
        raise YamlSettingsError(f'{path.name} declares {entry} more than once; nothing was changed.')
    for k, v in value.value:
        if _scalar_key(k) == entry:
            return _Layout('mapping', key, value, k, v)
    return _Layout('mapping', key, value, None, None)


# --- Text edits ------------------------------------------------------------

def _entry_lines(entry: str, url: str, token: str, indent: str, newline: str) -> str:
    def quoted(value):
        if not isinstance(value, str) or re.search(r'[\x00-\x1f"\\\x7f]', value):
            raise YamlSettingsError('Server URL or token contains characters that cannot be written safely; nothing was changed.')
        return '"' + value + '"'
    lines = [f'{indent}{entry}:', f'{indent}  url: {quoted(url)}']
    if token:
        lines += [f'{indent}  headers:', f'{indent}    Authorization: {quoted("Bearer " + token)}']
    return newline.join(lines) + newline


def _content_end(node) -> int:
    """End of a node's own text. A block collection's end mark points at the next token, which can
    sit past blank lines and comments that belong to the following key, so descend to the last value."""
    yaml = _yaml()
    if isinstance(node, yaml.MappingNode) and node.value and not node.flow_style:
        return _content_end(node.value[-1][1])
    if isinstance(node, yaml.SequenceNode) and node.value and not node.flow_style:
        return _content_end(node.value[-1])
    return node.end_mark.index


def _without_entry(text: str, layout: _Layout) -> str:
    start = _line_start(text, layout.entry_key.start_mark.index)
    end = _after_line(text, _content_end(layout.entry_value))
    return text[:start] + text[end:]


def _with_entry(text: str, path: Path, entry: str, url: str, token: str, newline: str):
    """Return (new_text, created_section). ``text`` must not already hold the entry."""
    layout = _layout(text, path, entry)
    if layout.entry_key is not None:
        raise AssertionError('caller removes an existing entry first')
    if layout.section_key is None:
        prefix = text
        if prefix and not prefix.endswith('\n'):
            prefix += newline
        return prefix + SECTION + ':' + newline + _entry_lines(entry, url, token, '  ', newline), True
    key, value = layout.section_key, layout.section_value
    yaml = _yaml()
    if isinstance(value, yaml.MappingNode) and not value.flow_style:
        indent = ' ' * value.value[0][0].start_mark.column
        at = _after_line(text, _content_end(value))
        body = text[:at]
        if body and not body.endswith('\n'):
            body += newline
        return body + _entry_lines(entry, url, token, indent, newline) + text[at:], False
    # `mcp_servers:` with nothing after it, or `mcp_servers: {}` on one line: keep the key line
    # (and any trailing comment), drop an empty `{}`, and add the entry as a block under it.
    line_start = _line_start(text, key.start_mark.index)
    line_end = _after_line(text, key.end_mark.index)
    shape = re.fullmatch(r'(\s*:)\s*(?:\{\s*\})?\s*(#[^\r\n]*)?\r?\n?', text[key.end_mark.index:line_end])
    if not shape:
        raise YamlSettingsError(f'{path.name} has an empty {SECTION} in an unexpected form; nothing was changed.')
    comment = shape.group(2)
    line = text[line_start:key.end_mark.index] + shape.group(1) + ((' ' + comment) if comment else '') + newline
    indent = ' ' * (key.start_mark.column + 2)
    return text[:line_start] + line + _entry_lines(entry, url, token, indent, newline) + text[line_end:], False


# --- Verification ----------------------------------------------------------

def _diff_keys(before, after, prefix=''):
    """Key paths (no values) that differ between two mappings, one level into mcp_servers."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return [prefix or '<root>'] if before != after else []
    paths = []
    for key in sorted(set(before) | set(after), key=str):
        where = f'{prefix}.{key}' if prefix else str(key)
        if key not in before or key not in after:
            paths.append(where)
        elif key == SECTION and not prefix and all(isinstance(v, (dict, type(None))) for v in (before[key], after[key])):
            paths += _diff_keys(before[key] or {}, after[key] or {}, where)
        elif before[key] != after[key]:
            paths.append(where)
    return paths


def _normalised(value):
    """`mcp_servers:` with no entries reads as null; treat it the same as an empty mapping."""
    value = dict(value or {})
    if SECTION in value and value[SECTION] is None:
        value[SECTION] = {}
    return value


def verify_only_one_key_changed(before_text: str, after_text: str, *, entry: str = DEFAULT_ENTRY,
                                path: Path = Path('config.yaml')) -> list:
    """Raise unless the only structural change is mcp_servers.<entry>. Returns the changed key paths."""
    before = _load(before_text, path) or {}
    after = _load(after_text, path) or {}
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise YamlSettingsError(f'{path.name} root is not a mapping.')
    changed = _diff_keys(before, after)
    allowed = {f'{SECTION}.{entry}'}
    if SECTION not in before or before.get(SECTION) is None or SECTION not in after or after.get(SECTION) is None:
        allowed.add(SECTION)   # the section itself was created, emptied or removed along with our entry
    unexpected = [p for p in changed if p not in allowed]
    if unexpected:
        raise YamlSettingsError(f'{path.name}: unexpected structural change at {", ".join(unexpected)}.')
    return changed


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


def _backup(path: Path, raw: bytes) -> Path:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = path.with_name(f'{path.name}.{DEFAULT_ENTRY}-{stamp}-{secrets.token_hex(3)}.bak')
    with backup.open('xb') as handle:      # reserve the name; never overwrite an earlier backup
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    shutil.copystat(path, backup)
    if backup.read_bytes() != raw:
        raise YamlSettingsError(f'Backup of {path.name} could not be verified; nothing was changed.')
    return backup


def resolve_settings_path(raw, project_dir=None) -> Path:
    """Expand $VARS and ~ exactly once; refuse an unset variable rather than guessing a home."""
    if not isinstance(raw, str) or not raw.strip():
        raise YamlSettingsError("mcp_inject = 'yaml_settings_file' requires mcp_settings_path.")
    for groups in re.findall(r'\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)|%([A-Za-z_]\w*)%', raw):
        name = next(g for g in groups if g)
        if not os.environ.get(name, '').strip():
            raise YamlSettingsError(f'mcp_settings_path uses {name}, which is not set or is empty.')
    expanded = os.path.expanduser(os.path.expandvars(raw))
    if re.search(r'\$\{?[A-Za-z_]|%[A-Za-z_][A-Za-z0-9_]*%', expanded):
        raise YamlSettingsError('mcp_settings_path names an environment variable that is not set (for example HERMES_HOME).')
    target = Path(expanded)
    if not target.is_absolute():
        target = Path(project_dir or Path.cwd()) / target
    return target


def apply(path, url: str, token: str, *, entry: str = DEFAULT_ENTRY, log=print) -> ApplyReceipt:
    """Insert or refresh mcp_servers.<entry>. Caller holds the per-file write lock.

    Backup: a timestamped sibling with the exact prior bytes, made only when the file exists and
    does not already hold the entry (so a backup never contains our bearer token).

    Existing lines are kept byte for byte, with two documented exceptions: a file without a
    final newline gets one before the appended block, and an empty `mcp_servers:` or
    `mcp_servers: {}` key line is rewritten as `mcp_servers:` (keeping a trailing comment) so
    the entry can sit under it. Both are covered by the structural check, and remove_exact
    restores the original bytes when the file is unchanged since this write.
    If the file changes between reading and replacing it, the plan is redone once, then refused."""
    path = Path(path)
    if not path.parent.is_dir():
        raise YamlSettingsError(f'{path.parent} does not exist; nothing was changed.')
    for attempt in range(2):
        raw = _current_bytes(path)
        plan = _plan_apply(path, raw, entry, url, token)
        backup = backup_sha = None
        if raw is not None and not plan['had_entry']:
            backup, backup_sha = _backup(path, raw), _sha256(raw)
        try:
            _atomic_write(path, plan['data'], raw)
        except _ChangedUnderUs:
            if backup is not None:
                backup.unlink(missing_ok=True)       # our own backup of a version we did not edit
            continue
        if backup is not None:
            log(f'  Backed up {path.name} -> {backup} (sha256 {backup_sha})')
        log(f'  {"Refreshed" if plan["had_entry"] else "Added"} {SECTION}.{entry} in {path} (sha256 {_sha256(plan["data"])})')
        return ApplyReceipt(path, entry, backup, backup_sha, _sha256(plan['data']), raw is None, plan['created_section'])
    raise YamlSettingsError(f'{path.name} kept changing while it was being updated (is the client writing it?); '
                            'nothing of ours was written.')


def _plan_apply(path: Path, raw, entry: str, url: str, token: str) -> dict:
    """Validate and build the new bytes from ``raw`` (None for a missing file). No side effects."""
    text, bom, newline = _decode(raw or b'', path)
    layout = _layout(text, path, entry)
    had_entry = layout.entry_key is not None
    base = text
    if had_entry:
        base = _without_entry(text, layout)
        # Check the deletion on its own, so a hand-edited entry cannot hide a wider change.
        verify_only_one_key_changed(text, base, entry=entry, path=path)
        expected_base = _normalised(_load(text, path))
        expected_base[SECTION].pop(entry, None)
        if _normalised(_load(base, path)) != expected_base:
            raise YamlSettingsError(f'Could not refresh {SECTION}.{entry} in {path.name} safely; nothing was changed.')
    new_text, created_section = _with_entry(base, path, entry, url, token, newline)
    verify_only_one_key_changed(base, new_text, entry=entry, path=path)
    expected = _load(base, path) or {}
    if not isinstance(expected.get(SECTION), dict):
        expected[SECTION] = {}
    expected[SECTION][entry] = {'url': url, **({'headers': {'Authorization': 'Bearer ' + token}} if token else {})}
    if _load(new_text, path) != expected:
        raise YamlSettingsError(f'Could not update {path.name} safely; nothing was changed.')
    return {'data': _encode(new_text, bom), 'had_entry': had_entry, 'created_section': created_section}


def remove_exact(path, *, entry: str = DEFAULT_ENTRY, receipt: ApplyReceipt | None = None, log=print) -> RemovalResult:
    """Remove exactly mcp_servers.<entry>; caller holds the per-file write lock.

    If the file is still byte-identical to what apply() wrote, the backup bytes are restored
    (or the file we created is deleted). Otherwise only our entry's lines are deleted and the
    result is checked to differ from the current file by that entry alone. Either way the result
    is compared structurally with the backup and reported."""
    path = Path(path)
    for attempt in range(2):
        try:
            return _remove_once(path, entry, receipt, log)
        except _ChangedUnderUs:
            continue
    raise YamlSettingsError(f'{path.name} kept changing while {SECTION}.{entry} was being removed; '
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


def _remove_once(path: Path, entry: str, receipt, log) -> RemovalResult:
    raw = _current_bytes(path)
    if raw is None:
        return RemovalResult(path, 'absent', None, [])
    text, bom, newline = _decode(raw, path)
    layout = _layout(text, path, entry)
    if layout.entry_key is None:
        return RemovalResult(path, 'absent', None, [])
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
    # Edited since our write, or the backup is missing/tampered: delete only our entry (checked).
    new_text = _without_entry(text, layout)
    if receipt and receipt.created_section:
        after = _layout(new_text, path, entry)
        if after.section_key is not None and not getattr(after.section_value, 'value', None):
            start = _line_start(new_text, after.section_key.start_mark.index)
            new_text = new_text[:start] + new_text[_after_line(new_text, after.section_key.end_mark.index):]
    verify_only_one_key_changed(text, new_text, entry=entry, path=path)
    expected = _load(text, path)
    expected[SECTION].pop(entry)
    if receipt and receipt.created_section and not expected[SECTION]:
        expected.pop(SECTION)
    if _normalised(_load(new_text, path)) != _normalised(expected):
        raise YamlSettingsError(f'Could not remove {SECTION}.{entry} from {path.name} safely; file left unchanged.')
    data = _encode(new_text, bom)
    _atomic_write(path, data, raw)
    matches, differing = None, []
    if original is not None:
        differing = _diff_keys(_load(_decode(original, path)[0], path) or {}, _load(new_text, path) or {})
        matches = not differing
    elif receipt and receipt.backup_path:
        matches, differing = False, ['<backup missing or changed>']
    log(f'  Removed {SECTION}.{entry} from {path.name} (sha256 {_sha256(data)})'
        + ('' if matches is None else ('; matches backup' if matches else f'; differs from backup at {", ".join(differing)}')))
    return RemovalResult(path, 'removed-entry', matches, differing)


def _text(output) -> str:
    return output.decode('utf-8', errors='replace') if isinstance(output, bytes) else (output or '')


def hermes_running(image_names=('hermes.exe', 'hermes')) -> bool | None:
    """Read-only check by process image name only (never command lines).

    Returns True/False, or None when the process list could not be read. A Hermes started
    through an interpreter (python.exe) is not visible by image name; pass its launcher image."""
    wanted = {name.lower() for name in image_names}
    try:
        if sys.platform == 'win32':
            tasklist = os.path.join(os.environ.get('SystemRoot') or r'C:\Windows', 'System32', 'tasklist.exe')
            output = _text(subprocess.run([tasklist, '/FO', 'CSV', '/NH'], capture_output=True, timeout=15,
                                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout)
            images = {line.split('","', 1)[0].strip('"').lower() for line in output.splitlines() if line.startswith('"')}
        else:
            output = _text(subprocess.run(['ps', '-A', '-o', 'comm='], capture_output=True, timeout=15).stdout)
            images = {Path(line.strip()).name.lower() for line in output.splitlines() if line.strip()}
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return bool(images & wanted) if images else None
