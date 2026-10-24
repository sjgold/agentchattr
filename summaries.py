"""Per-channel summary store — agents write, everyone reads."""

import json
import math
import time
import threading
import uuid
from pathlib import Path
from copy import deepcopy

from api_seats import atomic_json
from channel_guards import channel_write
from channel_lifecycle import ChannelConflict, ChannelUnavailable, _name

MAX_CHARS = 1000


class SummaryStore:
    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._summaries: dict[str, dict] = {}  # channel → summary dict
        self._lock = threading.Lock()
        self._channel_policy_getter = None
        self._configured = False
        self._load_error = None
        self._fingerprint = None
        self._had_file = self._path.exists()
        self._load()
        self._durable = deepcopy(self._summaries)

    def _load(self):
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text("utf-8"))
            if isinstance(raw, dict):
                self._summaries = raw
        except (json.JSONDecodeError, KeyError):
            self._summaries = {}

    def _save(self):
        try:
            self._check_readable(force=True)
            atomic_json(self._path, self._summaries)
        except Exception:
            self._summaries = deepcopy(self._durable)
            raise
        self._durable = deepcopy(self._summaries)
        self._had_file = True
        self._fingerprint = None

    def _check_readable(self, *, force=False, strict=False):
        if self._load_error:
            raise ChannelUnavailable(self._load_error)
        if not (self._configured or strict):
            return
        try:
            try:
                info = self._path.stat()
            except FileNotFoundError:
                if self._had_file:
                    raise ValueError('Saved summaries disappeared.')
                return
            stamp = info.st_mtime_ns, info.st_size
            if not force and stamp == self._fingerprint:
                return
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('Duplicate summary field.')
                    result[key] = value
                return result
            def invalid(value):
                raise ValueError('Invalid JSON number.')
            saved = json.loads(self._path.read_text(encoding='utf-8'),
                               object_pairs_hook=unique, parse_constant=invalid)
            if type(saved) is not dict:
                raise ValueError('Summaries must be an object.')
            for channel, entry in saved.items():
                _name(channel)
                if (type(entry) is not dict or type(entry.get('text')) is not str
                        or type(entry.get('author')) is not str
                        or type(entry.get('message_id')) is not int
                        or type(entry.get('updated_at')) not in (int, float)
                        or not math.isfinite(entry['updated_at'])):
                    raise ValueError('Invalid summary.')
            after = self._path.stat()
            if (after.st_mtime_ns, after.st_size) != stamp or saved != self._durable:
                raise ValueError('Saved summaries changed.')
            self._fingerprint = stamp
        except (ValueError, TypeError, KeyError, OverflowError, OSError):
            raise ChannelUnavailable('Saved summaries are unreadable or changed. Repair the file and restart; no reset was performed.') from None

    def get(self, channel: str) -> dict | None:
        with self._lock:
            self._check_readable()
            entry = self._summaries.get(channel)
            return deepcopy(entry) if entry else None

    def get_all(self) -> dict:
        with self._lock:
            self._check_readable()
            return deepcopy(self._summaries)

    def bind_channel_policy(self, getter):
        if not callable(getter):
            raise ValueError('An explicit channel policy getter is required.')
        self._channel_policy_getter = getter
        self._configured = True
        with self._lock:
            try:
                self._check_readable(force=True)
            except ChannelUnavailable as error:
                self._load_error = str(error)  # Bind held, so the rest of startup can continue.

    def rename_channel(self, old_name, new_name):
        """Staged lifecycle phase, without active-channel checks or callbacks."""
        _name(old_name)
        _name(new_name)
        with self._lock:
            self._check_readable(force=True, strict=True)
            if old_name == new_name or old_name not in self._summaries:
                return
            if new_name in self._summaries:
                raise ChannelConflict('Destination already contains a summary.')
            staged = deepcopy(self._summaries)
            staged[new_name] = staged.pop(old_name)
            atomic_json(self._path, staged)
            self._summaries = staged
            self._durable = deepcopy(staged)
            self._had_file = True
            self._fingerprint = None

    @channel_write(lambda store, args: [args['channel']])
    def write(self, channel: str, text: str, author: str, message_id: int = 0,
              uid: str | None = None, updated_at: float | None = None) -> dict | None:
        text = text.strip()
        if not text:
            return None
        if len(text) > MAX_CHARS:
            return None  # Caller should inform the agent
        with self._lock:
            self._check_readable()
            entry = {
                "uid": uid or str(uuid.uuid4()),
                "text": text,
                "author": author,
                "updated_at": updated_at if updated_at is not None else time.time(),
                "message_id": message_id,
            }
            self._summaries[channel] = entry
            self._save()
            return dict(entry)

    @channel_write(lambda store, args: [args['channel']])
    def delete(self, channel: str) -> bool:
        with self._lock:
            self._check_readable()
            if channel in self._summaries:
                del self._summaries[channel]
                self._save()
                return True
            return False
