"""Schedule store — recurring prompts fired without human intervention."""

import json
import math
import re
import time
import threading
import uuid
from pathlib import Path
from copy import deepcopy

from api_seats import atomic_json
from channel_guards import channel_write
from channel_lifecycle import ChannelConflict, ChannelUnavailable, _name


# Interval parsing: "every 30m", "every 1h", "every 2h", "daily at 09:00"
_INTERVAL_RE = re.compile(
    r"every\s+(\d+)\s*(m|min|h|hr|d|day)s?\b",
    re.IGNORECASE
)
_DAILY_RE = re.compile(
    r"daily\s+at\s+(\d{1,2}):(\d{2})\b",
    re.IGNORECASE
)

# Upper bound for an explicit send time (2100-01-01). Anything beyond this is
# a mistake or an attack: it never fires, so the row sticks in the list forever.
MAX_SEND_AT = 4102444800.0


def parse_schedule_spec(spec: str) -> tuple[int | None, str | None]:
    """Parse natural-language schedule spec.
    Returns (interval_seconds, None) for intervals, or (None, cron_expr) for daily.
    Returns (None, None) if unparseable.
    """
    spec = spec.strip()
    m = _INTERVAL_RE.search(spec)
    if m:
        val = int(m.group(1))
        unit = m.group(2).lower()
        if unit in ("m", "min"):
            secs = val * 60
        elif unit in ("h", "hr"):
            secs = val * 3600
        elif unit in ("d", "day"):
            secs = val * 86400
        else:
            return (None, None)
        if secs < 60:
            secs = 60  # minimum 1 minute
        return (secs, None)

    dm = _DAILY_RE.search(spec)
    if dm:
        hour = int(dm.group(1)) % 24
        minute = int(dm.group(2)) % 60
        # Store as "HH:MM" for daily; we compute next_run from current time
        return (86400, f"{hour:02d}:{minute:02d}")  # interval=1 day, time hint

    return (None, None)


def compute_next_run(
    interval_seconds: int,
    last_run: float | None,
    daily_at: str | None = None,
) -> float:
    """Compute next run timestamp. daily_at is "HH:MM" for daily schedules."""
    now = time.time()
    if last_run is None:
        if daily_at:
            # First run: today at HH:MM, or tomorrow if already past
            parts = daily_at.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            from datetime import datetime
            today = datetime.fromtimestamp(now)
            target = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
            ts = target.timestamp()
            if ts <= now:
                from datetime import timedelta
                target = target + timedelta(days=1)
                ts = target.timestamp()
            return ts
        return now + interval_seconds
    if daily_at:
        from datetime import datetime, timedelta
        last_dt = datetime.fromtimestamp(last_run)
        parts = daily_at.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        next_dt = last_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_dt <= last_dt:
            next_dt = next_dt + timedelta(days=1)
        return next_dt.timestamp()
    return last_run + interval_seconds


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _unbound_schedule_policy():
    raise ChannelUnavailable('Schedule publication is held until channel policy is bound.')


class ScheduleStore:
    def __init__(self, path: str, *, configured=False):
        if type(configured) is not bool:
            raise ValueError('Configured mode must be boolean.')
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._schedules: list[dict] = []
        self._lock = threading.Lock()
        self._callbacks: list = []
        self._configured = configured
        self._channel_policy_getter = _unbound_schedule_policy if configured else None
        self._durable = []
        self._fingerprint = self._invalid_fingerprint = None
        self._had_file = False
        self._load_error = None
        self._load()

    @property
    def load_error(self):
        return self._load_error

    def _stamp(self):
        info = self._path.stat()
        return info.st_mtime_ns, info.st_size

    def _read(self):
        before = self._stamp()
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate schedule field.')
                result[key] = value
            return result
        def invalid(value):
            raise ValueError('Invalid JSON number.')
        options = {'object_pairs_hook': unique, 'parse_constant': invalid} if self._configured else {}
        rows = json.loads(self._path.read_text(encoding='utf-8'), **options)
        if self._configured:
            if type(rows) is not list:
                raise ValueError('Saved schedules must be a list.')
            ids = set()
            for row in rows:
                if (type(row) is not dict or type(row.get('id')) is not str or not row['id']
                        or row['id'] in ids or type(row.get('channel')) is not str
                        or type(row.get('targets')) is not list
                        or any(type(target) is not str for target in row['targets'])
                        or not _finite_number(row.get('next_run'))
                        or any(key in row and type(row[key]) is not bool for key in ('active', 'one_shot'))
                        or any(row.get(key) is not None and not _finite_number(row[key]) for key in ('last_run', 'last_attempt_at'))
                        or ('failure_count' in row and (type(row['failure_count']) is not int or row['failure_count'] < 0))
                        or row.get('last_error') not in (None, 'invalid_schedule', 'delivery_unconfirmed', 'internal')
                        or ('interval_seconds' in row and (not _finite_number(row['interval_seconds']) or row['interval_seconds'] <= 0))):
                    raise ValueError('Invalid saved schedule.')
                ids.add(row['id'])
        after = self._stamp()
        if before != after:
            raise ValueError('Schedules changed while being read.')
        self._read_fingerprint = after
        return rows

    def _load(self):
        if not self._path.exists():
            return
        try:
            rows = self._read()
            if isinstance(rows, list):
                self._schedules = rows
                self._durable = deepcopy(rows)
                self._had_file = True
                self._fingerprint = self._read_fingerprint
        except (ValueError, TypeError, KeyError, OSError) as error:
            if self._configured:
                self._load_error = 'Saved schedules are unreadable. Scheduling is held; repair the file and restart.'
            elif not isinstance(error, (json.JSONDecodeError, TypeError)):
                raise

    def _check_readable(self, *, force=False):
        if self._load_error:
            raise ChannelUnavailable(self._load_error)
        if not self._configured:
            return
        try:
            try:
                stamp = self._stamp()
            except FileNotFoundError:
                if self._had_file:
                    raise OSError('Saved schedules disappeared.')
                return
            if stamp == self._invalid_fingerprint:
                raise ChannelUnavailable('Saved schedules changed or are unreadable. Repair the file and restart.')
            if force or stamp != self._fingerprint:
                try:
                    if self._read() != self._durable:
                        raise ValueError('External edits require a restart.')
                except (ValueError, KeyError, TypeError, OSError):
                    self._invalid_fingerprint = stamp
                    raise
                self._fingerprint = self._read_fingerprint
                self._invalid_fingerprint = None
        except (ValueError, TypeError, KeyError, OSError):
            raise ChannelUnavailable('Saved schedules changed or are unreadable. Repair the file and restart.') from None

    def bind_channel_policy(self, getter):
        if not callable(getter):
            raise ValueError('An explicit channel policy getter is required.')
        self._configured = True
        self._channel_policy_getter = getter
        with self._lock:
            if not self._load_error:
                self._check_readable(force=True)

    def _schedule_channels(self, schedule_id):
        with self._lock:
            self._check_readable()
            return [row.get('channel', 'general') for row in self._schedules if row.get('id') == schedule_id]

    def _save(self):
        try:
            self._check_readable(force=True)
            atomic_json(self._path, self._schedules)
        except Exception:
            self._schedules = deepcopy(self._durable)
            raise
        self._durable = deepcopy(self._schedules)
        self._had_file = True
        try:
            self._fingerprint = self._stamp()
        except OSError:
            self._fingerprint = None

    def rename_channel(self, old_name, new_name):
        """Durable lifecycle phase; no schedule execution or observer effect."""
        _name(old_name)
        _name(new_name)
        with self._lock:
            self._check_readable(force=True)
            if old_name == new_name or not any(row.get('channel') == old_name for row in self._schedules):
                return
            if any(row.get('channel') == new_name for row in self._schedules):
                raise ChannelConflict('Destination already contains schedules.')
            staged = deepcopy(self._schedules)
            for row in staged:
                if row.get('channel') == old_name:
                    row['channel'] = new_name
            atomic_json(self._path, staged)
            self._schedules = staged
            self._durable = deepcopy(staged)
            self._had_file = True
            self._fingerprint = None

    def on_change(self, callback):
        """Register callback(action, schedule) on any change."""
        self._callbacks.append(callback)

    def _fire(self, action: str, schedule: dict):
        for cb in self._callbacks:
            try:
                cb(action, schedule)
            except Exception:
                pass

    def retained_metadata(self, channel, *, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('Invalid retained row limit.')
        with self._lock:
            self._check_readable()
            rows, count = [], 0
            for schedule in self._schedules:
                if schedule.get('channel') == channel:
                    count += 1
                    if len(rows) < limit:
                        rows.append({key: deepcopy(schedule.get(key)) for key in ('id', 'channel', 'active', 'next_run')})
            return {'rows': rows, 'count': count, 'truncated': count > len(rows)}

    def channel_names(self):
        with self._lock:
            self._check_readable()
            return {row.get('channel', 'general') for row in self._schedules}

    def list_all(self, active_only: bool = False) -> list[dict]:
        with self._lock:
            self._check_readable()
            result = deepcopy(self._schedules)
        if active_only:
            result = [s for s in result if s.get("active", True)]
        return result

    def get(self, schedule_id: str) -> dict | None:
        with self._lock:
            self._check_readable()
            for s in self._schedules:
                if s.get("id") == schedule_id:
                    return deepcopy(s)
            return None

    @channel_write(lambda schedules, args: [args['channel']])
    def create(
        self,
        prompt: str,
        targets: list[str],
        channel: str = "general",
        interval_seconds: int | None = None,
        daily_at: str | None = None,
        one_shot: bool = False,
        send_at: float | None = None,
        created_by: str = "user",
    ) -> dict:
        """Create a schedule. Either interval_seconds or daily_at must be set.
        If one_shot=True, the schedule auto-deletes after firing once.
        If send_at is provided (epoch), use it as next_run directly.
        """
        schedule_id = str(uuid.uuid4())[:8]
        now = time.time()
        last_run = None
        if daily_at:
            interval_seconds = 86400
        if self._configured and interval_seconds is not None and (
                not _finite_number(interval_seconds) or interval_seconds <= 0):
            raise ValueError('Use a positive finite recurrence interval.')
        if send_at is not None:
            try:
                send_at = float(send_at)
            except (TypeError, ValueError, OverflowError):
                # OverflowError: JSON ints are arbitrary precision, so a
                # 400-digit literal reaches float() and blows up there.
                raise ValueError("That time is not a real moment")
            # NaN loses every comparison, so an unchecked NaN would slip past
            # the past-time guard below and then be written to the JSON store
            # as a bare NaN, which no later read of that file can parse.
            if not math.isfinite(send_at) or send_at > MAX_SEND_AT:
                raise ValueError("That time is not a real moment")
            if send_at <= now:
                raise ValueError("That time has already passed - pick a later one")
            next_run = send_at
            if one_shot:
                # A one-shot is defined solely by next_run. Keeping daily_at
                # would claim a daily recurrence the schedule does not have,
                # and the schedules bar renders that field verbatim.
                daily_at = None
        else:
            next_run = compute_next_run(
                interval_seconds or 86400,
                last_run,
                daily_at=daily_at,
            )
        with self._lock:
            s = {
                "id": schedule_id,
                "prompt": prompt.strip()[:500],
                "targets": [t.strip().lstrip("@") for t in targets if t.strip()],
                "channel": channel or "general",
                "interval_seconds": interval_seconds or 86400,
                "daily_at": daily_at,
                "next_run": next_run,
                "created_at": now,
                "last_run": None,
                "active": True,
                "one_shot": one_shot,
                "created_by": created_by,
            }
            self._schedules.append(s)
            self._save()
        self._fire("create", s)
        return deepcopy(s)

    def run_due(self) -> list[dict]:
        """Return list of schedules that are due (next_run <= now). Does not update."""
        now = time.time()
        with self._lock:
            self._check_readable()
            due = [s for s in self._schedules if s.get("active") and s.get("next_run", 0) <= now]
        return deepcopy(due)

    @channel_write(lambda schedules, args: schedules._schedule_channels(args['schedule_id']))
    def mark_run(self, schedule_id: str) -> dict | None:
        """Mark schedule as run, advance next_run. Returns updated schedule."""
        with self._lock:
            for s in self._schedules:
                if s.get("id") != schedule_id:
                    continue
                now = time.time()
                next_run = compute_next_run(s.get("interval_seconds", 3600), now, daily_at=s.get("daily_at"))
                s["last_run"] = now
                s["next_run"] = next_run
                self._save()
                result = dict(s)
                break
            else:
                return None
        self._fire("update", result)
        return result

    @channel_write(lambda schedules, args: schedules._schedule_channels(args['schedule_id']))
    def delete(self, schedule_id: str) -> dict | None:
        with self._lock:
            for i, s in enumerate(self._schedules):
                if s.get("id") == schedule_id:
                    removed = self._schedules.pop(i)
                    self._save()
                    result = dict(removed)
                    break
            else:
                return None
        self._fire("delete", result)
        return result

    @channel_write(lambda schedules, args: schedules._schedule_channels(args['schedule_id']))
    def toggle(self, schedule_id: str) -> dict | None:
        with self._lock:
            for s in self._schedules:
                if s.get("id") == schedule_id:
                    s["active"] = not s.get("active", True)
                    self._save()
                    result = dict(s)
                    break
            else:
                return None
        self._fire("update", result)
        return result


    @channel_write(lambda schedules, args: schedules._schedule_channels(args['schedule_id']))
    def begin_attempt(self, schedule_id, *, now=None):
        now = time.time() if now is None else now
        if not _finite_number(now):
            raise ValueError('Use a finite attempt time.')
        with self._lock:
            row = next((item for item in self._schedules if item.get('id') == schedule_id), None)
            if not row or not row.get('active') or row.get('next_run', 0) > now:
                return None
            if not row.get('one_shot'):
                next_run = compute_next_run(row.get('interval_seconds', 3600), now, daily_at=row.get('daily_at'))
                if not _finite_number(next_run) or next_run <= now:
                    raise ValueError('The reserved recurrence must be in the future.')
            row['last_attempt_at'] = now
            if row.get('one_shot'):
                row['active'] = False
            else:
                row['next_run'] = next_run
            self._save()
            result = deepcopy(row)
        self._fire('update', result)
        return result

    @channel_write(lambda schedules, args: schedules._schedule_channels(args['schedule_id']))
    def finish_attempt(self, schedule_id, *, success, error_code=None, now=None):
        now = time.time() if now is None else now
        if (type(success) is not bool or not _finite_number(now)
                or (success and error_code is not None)
                or (not success and error_code not in ('invalid_schedule', 'delivery_unconfirmed', 'internal'))):
            raise ValueError('Use a declared safe schedule outcome.')
        with self._lock:
            row = next((item for item in self._schedules if item.get('id') == schedule_id), None)
            if row is None:
                return None
            if success:
                row['last_run'] = now
                row['last_error'] = None
            else:
                row['failure_count'] = row.get('failure_count', 0) + 1
                row['last_error'] = error_code
            self._save()
            result = deepcopy(row)
        self._fire('update', result)
        return result
