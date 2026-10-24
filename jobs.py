"""Job store — bounded work conversations with threaded messages."""

import json
import time
import threading
import uuid
from copy import deepcopy
from pathlib import Path

import api_seats
from channel_lifecycle import ChannelConflict, ChannelUnavailable, _name
from channel_guards import channel_write
from store import _operator_authority, _operator_receipt


def _unbound_job_policy():
    raise ChannelUnavailable('Job publication is held until channel policy is bound.')


class JobStore:
    def __init__(self, path: str, *, migrate_sort_orders=True, hold_unreadable=False):
        if type(hold_unreadable) is not bool or (hold_unreadable and migrate_sort_orders):
            raise ValueError('Startup hold is available only for configured jobs.')
        if type(migrate_sort_orders) is not bool:
            raise ValueError('Sort migration mode must be boolean.')
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._jobs: list[dict] = []
        self._next_id = 1
        self._lock = threading.Lock()
        self._configured = not migrate_sort_orders
        self._channel_policy_getter = _unbound_job_policy if self._configured else None
        self._had_file = False
        self._fingerprint = None
        self._invalid_fingerprint = None
        self._load_error = None
        self._durable_jobs = []
        self._durable_next_id = 1
        self._callbacks: list = []  # (action, job) on any change
        try:
            self._load()
        except ChannelUnavailable:
            if not hold_unreadable:
                raise
            self._load_error = "Saved jobs are unreadable. Jobs are held; repair the file and restart. Chat remains available."

    def _load(self):
        if not self._path.exists():
            return
        try:
            raw = self._read_jobs()
            self._fingerprint = self._read_fingerprint
            if isinstance(raw, list):
                self._jobs = raw
                self._had_file = True
                if self._jobs:
                    self._next_id = max(a["id"] for a in self._jobs) + 1
                    self._durable_jobs = deepcopy(raw)
                    self._durable_next_id = self._next_id
                    if not self._configured and self._ensure_sort_orders_locked():
                        self._save()
        except (ValueError, KeyError, TypeError, OSError) as error:
            if self._configured:
                raise ChannelUnavailable('Saved jobs are unreadable; no reset was performed.') from None
            if not isinstance(error, (json.JSONDecodeError, KeyError)):
                raise
            self._jobs = []

    @property
    def load_error(self):
        return self._load_error

    def _stamp(self):
        stat = self._path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _read_jobs(self):
        before = self._stamp()
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError('Duplicate job field.')
                value[key] = item
            return value
        def invalid(value):
            raise ValueError('Invalid JSON constant.')
        options = {'object_pairs_hook': unique, 'parse_constant': invalid} if self._configured else {}
        value = json.loads(self._path.read_text(encoding='utf-8'), **options)
        if self._configured:
            if type(value) is not list:
                raise ValueError('Jobs must be a list.')
            seen = set()
            for job in value:
                if (type(job) is not dict or type(job.get('id')) is not int or job['id'] <= 0
                        or job['id'] in seen or type(job.get('channel')) is not str
                        or not job['channel'] or type(job.get('messages')) is not list
                        or any(type(message) is not dict for message in job['messages'])):
                    raise ValueError('Invalid saved job.')
                seen.add(job['id'])
        after = self._stamp()
        if after != before:
            raise ValueError('Jobs changed while being read.')
        self._read_fingerprint = after
        return value

    def _check_readable(self, *, force=False):
        if self._load_error:
            raise ChannelUnavailable(self._load_error)
        if self._configured:
            try:
                try:
                    stamp = self._stamp()
                except FileNotFoundError:
                    if self._had_file:
                        raise OSError('Saved jobs disappeared.')
                    return
                if stamp == self._invalid_fingerprint:
                    raise ChannelUnavailable('Saved jobs changed or are unreadable. Repair the file and restart; no reset was performed.')
                if force or stamp != self._fingerprint:
                    try:
                        value = self._read_jobs()
                        if value != self._durable_jobs:
                            raise ValueError('External job edits require a restart.')
                    except (ValueError, KeyError, TypeError, OSError):
                        self._invalid_fingerprint = stamp
                        raise
                    self._fingerprint = self._read_fingerprint
                    self._invalid_fingerprint = None
            except (ValueError, KeyError, TypeError, OSError):
                raise ChannelUnavailable('Saved jobs changed or are unreadable. Repair the file and restart; no reset was performed.') from None

    def bind_channel_policy(self, getter):
        if not callable(getter):
            raise ValueError('An explicit channel policy getter is required.')
        self._configured = True
        self._channel_policy_getter = getter
        with self._lock:
            if not self._load_error:
                self._check_readable(force=True)

    def _job_channels(self, job_id):
        with self._lock:
            self._check_readable()
            return [job.get('channel', 'general') for job in self._jobs if job['id'] == job_id]

    def _reorder_channels(self, status, ids):
        if type(ids) is not list or any(type(value) is not int or value <= 0 for value in ids):
            raise ValueError('Ordered job IDs must be positive integers.')
        with self._lock:
            self._check_readable()
            selected = {job['id']: job for job in self._jobs}
            if any(value not in selected or selected[value].get('status') != status for value in ids):
                raise ChannelConflict('Refresh jobs; a selected job is no longer in this lane.')
            return [selected[value].get('channel', 'general') for value in ids]

    def _save(self):
        try:
            self._check_readable(force=True)
            api_seats.atomic_json(self._path, self._jobs)
        except Exception:
            self._jobs = deepcopy(self._durable_jobs)
            self._next_id = self._durable_next_id
            raise
        self._durable_jobs = deepcopy(self._jobs)
        self._durable_next_id = self._next_id
        self._had_file = True
        # The atomic writer just committed these known bytes. A later changed
        # fingerprint must revalidate, never overwrite an external edit.
        try:
            self._fingerprint = self._stamp()
        except OSError:
            self._fingerprint = None

    def rename_channel(self, old_name, new_name):
        """Durable lifecycle phase; caller holds the engine/catalog boundary."""
        _name(old_name)
        _name(new_name)
        with self._lock:
            self._check_readable(force=True)
            if old_name == new_name or not any(row.get('channel') == old_name for row in self._jobs):
                return
            if any(row.get('channel') == new_name for row in self._jobs):
                raise ChannelConflict('Destination already contains jobs.')
            staged = deepcopy(self._jobs)
            for row in staged:
                if row.get('channel') == old_name:
                    row['channel'] = new_name
                    for message in row['messages']:
                        if message.get('channel') == old_name:
                            message['channel'] = new_name
            api_seats.atomic_json(self._path, staged)
            self._jobs = staged
            self._durable_jobs = deepcopy(staged)
            self._durable_next_id = self._next_id
            self._had_file = True
            self._fingerprint = None

    def _next_sort_order_locked(self, status: str) -> int:
        max_order = 0
        projected = [{'id': job['id'], 'status': job.get('status', 'open'),
                      'sort_order': job.get('sort_order', 0)} for job in self._jobs]
        self._ensure_sort_orders_locked(status, jobs=projected)
        for a in projected:
            if a.get("status") != status:
                continue
            try:
                max_order = max(max_order, int(a.get("sort_order", 0)))
            except (TypeError, ValueError):
                continue
        return max_order + 1

    def _ensure_sort_orders_locked(self, status=None, *, jobs=None):
        rows = self._jobs if jobs is None else jobs
        rows = [job for job in rows if status is None or job.get('status', 'open') == status]
        max_by_group: dict[str, int] = {}
        changed = False
        for a in rows:
            key = a.get("status", "open")
            try:
                cur = int(a.get("sort_order", 0))
            except (TypeError, ValueError):
                cur = 0
            if cur > 0:
                max_by_group[key] = max(max_by_group.get(key, 0), cur)

        for a in rows:
            key = a.get("status", "open")
            try:
                cur = int(a.get("sort_order", 0))
            except (TypeError, ValueError):
                cur = 0
            if cur <= 0:
                next_order = max_by_group.get(key, 0) + 1
                a["sort_order"] = next_order
                max_by_group[key] = next_order
                changed = True
        return changed

    def on_change(self, callback):
        """Register a callback(action, job) on any change.
        action: 'create', 'update', 'message', 'message_delete'."""
        self._callbacks.append(callback)

    def _fire(self, action: str, job: dict):
        for cb in self._callbacks:
            try:
                cb(action, job)
            except Exception:
                pass

    def list_all(self, channel: str | None = None,
                 status: str | None = None) -> list[dict]:
        """List jobs, optionally filtered by channel and/or status."""
        with self._lock:
            self._check_readable()
            if self._configured:
                # Normalize only cheap lane/order projections across all records.
                # Conversation bodies are copied only for requested rows.
                orders = [{'id': job['id'], 'status': job.get('status', 'open'),
                           'sort_order': job.get('sort_order', 0)} for job in self._jobs]
                self._ensure_sort_orders_locked(jobs=orders)
                by_id = {job['id']: job['sort_order'] for job in orders}
                selected = [job for job in self._jobs
                            if (not channel or job.get('channel') == channel)
                            and (not status or job.get('status') == status)]
                result = deepcopy(selected)
                for job in result:
                    job['sort_order'] = by_id[job['id']]
            else:
                changed = self._ensure_sort_orders_locked()
                if changed:
                    self._save()
                result = list(self._jobs)
        if channel:
            result = [a for a in result if a.get("channel") == channel]
        if status:
            result = [a for a in result if a.get("status") == status]
        return result

    def channel_names(self):
        with self._lock:
            self._check_readable()
            return {job.get('channel', 'general') for job in self._jobs}

    def lifecycle_scope(self, channel):
        """Return only the stable job identifiers needed for lifecycle confirmation."""
        with self._lock:
            self._check_readable()
            return [{'id': job['id'], 'updated_at': job.get('updated_at')}
                    for job in self._jobs if job.get('channel') == channel]

    def get(self, job_id: int) -> dict | None:
        with self._lock:
            self._check_readable()
            for a in self._jobs:
                if a["id"] == job_id:
                    return deepcopy(a) if self._configured else dict(a)
            return None

    @channel_write(lambda jobs, args: [args['channel']])
    def create(self, title: str, job_type: str, channel: str,
               created_by: str, anchor_msg_id: int | None = None,
               assignee: str | None = None,
               body: str | None = None,
               uid: str | None = None,
               status: str | None = None,
               created_at: float | None = None,
               updated_at: float | None = None) -> dict:
        """Create a new job. Returns the job dict."""
        with self._lock:
            st = status or "done"
            now = time.time()
            a = {
                "id": self._next_id,
                "uid": uid or str(uuid.uuid4()),
                "type": job_type,
                "title": title.strip()[:120],
                "body": (body or "").strip()[:1000],
                "status": st,
                "channel": channel,
                "created_by": created_by,
                "assignee": assignee or "",
                "anchor_msg_id": anchor_msg_id,
                "messages": [],
                "created_at": created_at or now,
                "updated_at": updated_at or now,
                "sort_order": self._next_sort_order_locked(st),
            }
            self._next_id += 1
            self._jobs.append(a)
            self._save()
        self._fire("create", a)
        return a

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def update_status(self, job_id: int, status: str) -> dict | None:
        """Update job status. Valid: open, done, archived."""
        if status not in ("open", "done", "archived"):
            return None
        with self._lock:
            for a in self._jobs:
                if a["id"] == job_id:
                    old_status = a.get("status")
                    next_order = None
                    if old_status != status:
                        # Compute destination order before moving this job so
                        # the job doesn't count itself in the target lane.
                        next_order = self._next_sort_order_locked(status)
                    a["status"] = status
                    a["updated_at"] = time.time()
                    if next_order is not None:
                        a["sort_order"] = next_order
                    self._save()
                    result = dict(a)
                    break
            else:
                return None
        self._fire("update", result)
        return result

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def update_title(self, job_id: int, title: str) -> dict | None:
        with self._lock:
            for a in self._jobs:
                if a["id"] == job_id:
                    a["title"] = title.strip()[:120]
                    a["updated_at"] = time.time()
                    self._save()
                    result = dict(a)
                    break
            else:
                return None
        self._fire("update", result)
        return result

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def update_assignee(self, job_id: int, assignee: str) -> dict | None:
        with self._lock:
            for a in self._jobs:
                if a["id"] == job_id:
                    a["assignee"] = assignee.strip()
                    a["updated_at"] = time.time()
                    self._save()
                    result = dict(a)
                    break
            else:
                return None
        self._fire("update", result)
        return result

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def add_message(self, job_id: int, sender: str, text: str,
                    attachments: list | None = None,
                    msg_type: str = "chat",
                    uid: str | None = None,
                    timestamp: float | None = None,
                    time_str: str | None = None) -> dict | None:
        """Add a message to a job's conversation. Returns the message."""
        with self._lock:
            for a in self._jobs:
                if a["id"] == job_id:
                    msg_id = len(a["messages"])
                    ts = timestamp if timestamp is not None else time.time()
                    msg = {
                        "id": msg_id,
                        "uid": uid or str(uuid.uuid4()),
                        "sender": sender,
                        "text": text.strip(),
                        "time": time_str or time.strftime("%H:%M:%S"),
                        "timestamp": ts,
                        "attachments": attachments or [],
                    }
                    if msg_type != "chat":
                        msg["type"] = msg_type
                    a["messages"].append(msg)
                    a["updated_at"] = time.time()
                    self._save()
                    result_msg = dict(msg)
                    result_msg["job_id"] = job_id
                    break
            else:
                return None
        self._fire("message", {"job_id": job_id, "message": result_msg})
        return result_msg

    def get_messages(self, job_id: int) -> list[dict] | None:
        """Get all messages for a job."""
        with self._lock:
            self._check_readable()
            for a in self._jobs:
                if a["id"] == job_id:
                    return deepcopy(a['messages']) if self._configured else list(a['messages'])
            return None

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def _publish_operator(self, job_id, sender, text, *, routing, authority,
                          attachments=None, msg_type='chat'):
        """Save an operator job message without emitting or routing it."""
        _operator_authority(authority)
        uid = str(uuid.uuid4())
        receipt = _operator_receipt(routing, uid)
        with self._lock:
            job = next((value for value in self._jobs if value['id'] == job_id), None)
            if job is None:
                return None
            stamp = time.time()
            message = {'id': len(job['messages']), 'uid': uid, 'sender': sender, 'text': text,
                       'channel': job['channel'],
                       'time': time.strftime('%H:%M:%S'), 'timestamp': stamp,
                       'attachments': deepcopy(attachments or []),
                       'metadata': {'recipient_routing': receipt}}
            if msg_type != 'chat':
                message['type'] = msg_type
            before = deepcopy(self._jobs)
            job['messages'].append(message)
            job['updated_at'] = stamp
            try:
                self._save()
            except Exception:
                self._jobs = before
                raise
        return dict(deepcopy(message), job_id=job_id)

    def get_message_snapshot(self, job_id, message_id):
        if type(job_id) is not int or job_id <= 0 or type(message_id) is not int or message_id < 0:
            raise ValueError('Job and message IDs must be valid integers.')
        with self._lock:
            self._check_readable()
            job = next((value for value in self._jobs if value['id'] == job_id), None)
            if job:
                for message in job['messages']:
                    if message['id'] == message_id:
                        return dict(deepcopy(message), job_id=job_id)
        return None

    def _emit_operator(self, message, *, authority):
        _operator_authority(authority)
        saved = self.get_message_snapshot(message['job_id'], message['id'])
        if not saved or saved.get('uid') != message.get('uid'):
            return
        receipt = (saved.get('metadata') or {}).get('recipient_routing') or {}
        if receipt.get('version') != 1 or receipt.get('message_uid') != saved['uid']:
            return
        for callback in list(self._callbacks):
            try:
                callback('message', deepcopy({'job_id': saved['job_id'], 'message': saved}))
            except Exception:
                pass

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def delete_message(self, job_id: int, msg_id: int) -> dict | None:
        """Soft-delete a message from a job conversation by message id."""
        with self._lock:
            for a in self._jobs:
                if a["id"] != job_id:
                    continue
                msgs = a.get("messages", [])
                hit = None
                for i, m in enumerate(msgs):
                    try:
                        mid = int(m.get("id", -1))
                    except (TypeError, ValueError):
                        mid = -1
                    if mid == msg_id:
                        hit = (i, m)
                        break
                if hit is None:
                    return None
                _, msg = hit
                if msg.get("deleted"):
                    return {"job_id": job_id, "message_id": msg_id}
                msg["deleted"] = True
                msg["text"] = ""
                msg["attachments"] = []
                msg["updated_at"] = time.time()
                a["updated_at"] = time.time()
                self._save()
                payload = {"job_id": job_id, "message_id": msg_id}
                break
            else:
                return None
        self._fire("message_delete", payload)
        return payload

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def resolve_message(self, job_id, index, resolution):
        if type(index) is not int or index < 0 or resolution not in ('accepted', 'dismissed'):
            raise ValueError('Use a valid suggestion index and resolution.')
        with self._lock:
            job = next((job for job in self._jobs if job['id'] == job_id), None)
            if job is None:
                return None
            if index >= len(job['messages']):
                raise ValueError('Invalid message index.')
            message = job['messages'][index]
            message['resolved'] = resolution
            self._save()
            saved = dict(deepcopy(message), job_id=job_id, channel=job['channel'])
            updated = deepcopy(job)
        self._fire('update', updated)
        return saved

    @channel_write(lambda jobs, args: jobs._job_channels(args['job_id']))
    def delete(self, job_id: int) -> dict | None:
        """Permanently delete a job."""
        with self._lock:
            for i, a in enumerate(self._jobs):
                if a["id"] == job_id:
                    removed = self._jobs.pop(i)
                    self._save()
                    result = dict(removed)
                    break
            else:
                return None
        self._fire("delete", result)
        return result

    @channel_write(lambda jobs, args: jobs._reorder_channels(args['status'], args['ordered_ids']))
    def reorder(self, status: str, ordered_ids: list[int]) -> list[dict]:
        """Reorder jobs within a status group by explicit id order (top to bottom)."""
        if status not in ("open", "done", "archived"):
            return []
        active_channels = None
        if self._channel_policy_getter is not None:
            policy = self._channel_policy_getter()
            value = policy.catalog.snapshot()
            active_channels = {name for name, state in value['channels'].items() if state == 'active'} - policy.catalog.blocked_names()
        with self._lock:
            if active_channels is None:
                self._ensure_sort_orders_locked()
            group = [
                a for a in self._jobs
                if a.get("status") == status and (active_channels is None or a.get('channel', 'general') in active_channels)
            ]
            if not group:
                return []

            by_id = {int(a["id"]): a for a in group}
            ordered: list[int] = []
            seen = set()
            for raw in ordered_ids:
                try:
                    aid = int(raw)
                except (TypeError, ValueError):
                    continue
                if aid in by_id and aid not in seen:
                    ordered.append(aid)
                    seen.add(aid)

            if not ordered:
                return []

            projected = deepcopy(group)
            self._ensure_sort_orders_locked(status, jobs=projected)
            existing_sorted = sorted(
                projected,
                key=lambda x: (int(x.get("sort_order", 0) or 0), float(x.get("updated_at", 0) or 0)),
                reverse=True,
            )
            for a in existing_sorted:
                aid = int(a["id"])
                if aid not in seen:
                    ordered.append(aid)

            changed: list[dict] = []
            n = len(ordered)
            for idx, aid in enumerate(ordered):
                item = by_id.get(aid)
                if not item:
                    continue
                new_order = n - idx
                try:
                    old_order = int(item.get("sort_order", 0) or 0)
                except (TypeError, ValueError):
                    old_order = 0
                if old_order != new_order:
                    item["sort_order"] = new_order
                    changed.append(dict(item))

            if changed:
                self._save()

        for item in changed:
            self._fire("update", item)
        return changed
