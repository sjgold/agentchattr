"""Durable upload references retained before channel message deletion."""
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import threading

from api_seats import atomic_json
from channel_lifecycle import ChannelUnavailable, _name


_ENTRY = {'channel', 'message_id', 'message_uid', 'timestamp', 'attachments'}
_HELD = 'Retained upload metadata is unavailable; repair the file before deleting history.'


def safe_upload_url(value):
    if type(value) is not str or not re.fullmatch(r'/uploads/[A-Za-z0-9][A-Za-z0-9._-]{0,254}', value):
        return None
    name = value.removeprefix('/uploads/')
    stem = name.split('.')[0].upper()
    if name.endswith('.') or stem in {'CON', 'PRN', 'AUX', 'NUL'} or re.fullmatch(r'(COM|LPT)[1-9]', stem):
        return None
    return value


class RetainedArtifactStore:
    def __init__(self, path):
        self._path = Path(path)
        self._lock = threading.RLock()
        self._value = {'version': 1, 'channels': {}}
        self._had_file = False
        self._fingerprint = None
        self._load_error = False
        try:
            if self._path.exists():
                self._value = self._read()
                self._had_file = True
                self._fingerprint = self._stamp()
        except (ValueError, TypeError, OverflowError, OSError):
            self._load_error = True

    def _stamp(self):
        info = self._path.stat()
        return info.st_mtime_ns, info.st_size

    @staticmethod
    def _validate(value):
        if (type(value) is not dict or set(value) != {'version', 'channels'}
                or type(value['version']) is not int or value['version'] != 1
                or type(value['channels']) is not dict):
            raise ValueError('Invalid retained metadata schema.')
        for channel, entries in value['channels'].items():
            _name(channel)
            if type(entries) is not dict:
                raise ValueError('Invalid retained metadata rows.')
            for uid, entry in entries.items():
                if (type(uid) is not str or not uid or type(entry) is not dict or set(entry) != _ENTRY
                        or entry['channel'] != channel or type(entry['message_id']) is not int
                        or entry['message_id'] < 0 or entry['message_uid'] != uid
                        or type(entry['attachments']) is not list
                        or any(type(item) is not dict for item in entry['attachments'])):
                    raise ValueError('Invalid retained metadata entry.')
                timestamp = entry['timestamp']
                if timestamp is not None and (type(timestamp) not in (int, float) or not math.isfinite(timestamp)):
                    raise ValueError('Invalid retained metadata timestamp.')
        json.dumps(value, allow_nan=False)  # Reject non-finite attachment metadata too.
        return value

    def _read(self):
        before = self._stamp()
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate retained metadata field.')
                result[key] = value
            return result
        def invalid(value):
            raise ValueError('Invalid JSON number.')
        value = json.loads(self._path.read_text(encoding='utf-8'),
                           object_pairs_hook=unique, parse_constant=invalid)
        if self._stamp() != before:
            raise ValueError('Retained metadata changed while reading.')
        return self._validate(value)

    def check(self, *, force=False):
        with self._lock:
            if self._load_error:
                raise ChannelUnavailable(_HELD)
            try:
                try:
                    stamp = self._stamp()
                except FileNotFoundError:
                    if self._had_file:
                        raise ValueError('Saved metadata disappeared.')
                    return
                if force or stamp != self._fingerprint:
                    if self._read() != self._value:
                        raise ValueError('External metadata changes require reload.')
                    self._fingerprint = stamp
            except (ValueError, TypeError, OverflowError, OSError):
                raise ChannelUnavailable(_HELD) from None

    def _commit(self, value):
        atomic_json(self._path, value)
        self._value = deepcopy(value)
        self._had_file = True
        self._fingerprint = None

    def probe(self):
        """Atomic no-op write before a delete intent, never a future-IO promise."""
        with self._lock:
            self.check(force=True)
            self._commit(self._value)

    def retain(self, channel, messages):
        _name(channel)
        with self._lock:
            self.check(force=True)
            staged = deepcopy(self._value)
            for message in messages:
                if message.get('channel') != channel:
                    raise ValueError('Upload reference has a different source channel.')
                attachments = message.get('attachments') or []
                if not attachments:
                    continue
                identifier = message['id']
                uid = message.get('uid', f'legacy:{identifier}')
                entry = {'channel': channel, 'message_id': identifier, 'message_uid': uid,
                         'timestamp': message.get('timestamp'), 'attachments': deepcopy(attachments)}
                entries = staged['channels'].setdefault(channel, {})
                if uid in entries and entries[uid] != entry:
                    raise ValueError('Retained upload identity conflicts with saved metadata.')
                entries[uid] = entry
            self._validate(staged)
            if staged != self._value:
                self._commit(staged)

    def read(self, channel, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Use a retained metadata limit between 1 and 1000.')
        with self._lock:
            self.check()
            entries = self._value['channels'].get(channel, {})
            rows = []
            for entry in entries.values():
                if len(rows) == limit:
                    break
                rows.append(deepcopy(entry))
            return {'rows': rows, 'count': len(entries), 'truncated': len(entries) > len(rows)}

    def reference_count(self, channel, *, exclude_uids=()):
        with self._lock:
            self.check()
            return sum(len(entry['attachments']) for uid, entry in self._value['channels'].get(channel, {}).items()
                       if uid not in exclude_uids)

    def channel_names(self):
        with self._lock:
            self.check()
            return set(self._value['channels'])
