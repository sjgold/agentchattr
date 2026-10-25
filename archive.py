"""Export/import archive for project history (chat, jobs, rules, summaries)."""

import hashlib
import io
import json
import re
import threading
import time
import uuid
import zipfile
import zlib
from copy import deepcopy
from contextlib import contextmanager
from itertools import islice

from channel_lifecycle import ChannelConflict, ChannelInactive, ChannelUnavailable
import artifact_archive as artifact_codec
from artifact_store import ArtifactUnavailable, ArtifactValidationError, ArtifactImportCollision
from sealed_result_io import canonical_utf8

SCHEMA_VERSION = 1
MAX_SCHEMA_VERSION = 2
MAX_IMPORT_SIZE = 50 * 1024 * 1024  # 50MB uncompressed

_import_lock = threading.Lock()
_LEGACY_HISTORY_ONLY = object()


class ArtifactArchiveLimit(ValueError):
    """Measured owned export data only; no untrusted header values."""
    def __init__(self, bound, actual, *, history_bytes, artifact_bytes, container_overhead_bytes=0):
        limits = {'members': ('members', 4096), 'manifest': ('bytes', 65536),
            'index': ('bytes', 4194304), 'lineages': ('lineages', 1024), 'ratio': ('ratio', 1000),
            'uncompressed': ('bytes', 52428800), 'zip': ('bytes', 52428800)}
        self.code, self.bound, self.actual = 'artifact_archive_limit', bound, actual
        self.unit, self.limit = limits[bound]
        self.history_bytes, self.artifact_bytes = history_bytes, artifact_bytes
        self.container_overhead_bytes = container_overhead_bytes
        self.total_bytes = history_bytes + artifact_bytes + container_overhead_bytes
        self.dominant_section = 'history' if history_bytes >= artifact_bytes else 'artifacts'
        self.error = (f'Artifact backup exceeds the {bound} limit ({actual} {self.unit}; limit {self.limit}); '
            f'dominant section: {self.dominant_section}. History {history_bytes} bytes, artifacts {artifact_bytes} bytes, '
            f'container overhead {container_overhead_bytes} bytes.')
        super().__init__(self.error)

    def projection(self):
        return {key: getattr(self, key) for key in ('code', 'error', 'bound', 'unit', 'limit', 'actual',
            'total_bytes', 'history_bytes', 'artifact_bytes', 'container_overhead_bytes', 'dominant_section')}


def _fingerprint(record: dict) -> str:
    """Deterministic fingerprint for legacy records without uid."""
    # Use fields that exist on the record type (messages vs jobs vs rules)
    parts = [
        record.get("sender", "") or record.get("created_by", ""),
        record.get("text", "") or record.get("title", ""),
        str(record.get("timestamp", "") or record.get("created_at", "")),
        record.get("channel", ""),
        record.get("body", ""),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _ensure_uid(record: dict) -> str:
    """Return existing uid or generate a fingerprint-based one."""
    if record.get("uid"):
        return record["uid"]
    return "fp-" + _fingerprint(record)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def build_export(store, jobs_store, rules_store, summary_store,
                 app_version: str = "", *, artifact_store=_LEGACY_HISTORY_ONLY) -> bytes:
    """Build a zip archive from current stores. Returns zip bytes."""
    if artifact_store is not _LEGACY_HISTORY_ONLY:
        if artifact_store is None:
            raise artifact_codec.ArtifactSectionError('artifact_archive_owner_unavailable')
        try:
            identifiers = artifact_store.export_lineage_ids()
            if identifiers:
                return _build_artifact_export(store, jobs_store, rules_store, summary_store,
                    app_version, artifact_store, identifiers)
        except (ChannelUnavailable, OSError):
            raise artifact_codec.ArtifactSectionError('artifact_archive_storage_unavailable') from None
        # Healthy empty is the ONLY configured fallback. Reuse the exact legacy
        # writer, including its UUID/clock/compression call sequence.
        return build_export(store, jobs_store, rules_store, summary_store, app_version)
    buf = io.BytesIO()

    # Collect data
    messages = store.get_recent(count=999_999_999)
    jobs_list = jobs_store.list_all() if jobs_store else []
    rules_list = rules_store.list_all() if rules_store else []
    summaries = summary_store.get_all() if summary_store else {}

    # Build messages JSONL
    messages_lines = []
    for msg in messages:
        exported = dict(msg)
        exported["uid"] = _ensure_uid(msg)
        # Convert reply_to int to reply_to_uid if possible
        if "reply_to" in exported:
            reply_id = exported["reply_to"]
            for m in messages:
                if m["id"] == reply_id:
                    exported["reply_to_uid"] = _ensure_uid(m)
                    break
        messages_lines.append(json.dumps(exported, ensure_ascii=False))

    # Build jobs
    exported_jobs = []
    for job in jobs_list:
        ej = dict(job)
        ej["uid"] = _ensure_uid(job)
        # Ensure job messages have uids
        exported_msgs = []
        for jm in ej.get("messages", []):
            ejm = dict(jm)
            ejm["uid"] = jm.get("uid") or "fp-" + hashlib.sha256(
                f"{jm.get('sender', '')}|{jm.get('text', '')}|{jm.get('timestamp', '')}".encode()
            ).hexdigest()[:16]
            exported_msgs.append(ejm)
        ej["messages"] = exported_msgs
        # Convert anchor_msg_id to anchor_message_uid
        anchor_id = ej.get("anchor_msg_id")
        if anchor_id is not None:
            for m in messages:
                if m["id"] == anchor_id:
                    ej["anchor_message_uid"] = _ensure_uid(m)
                    break
        exported_jobs.append(ej)

    # Build rules
    exported_rules = []
    for rule in rules_list:
        er = dict(rule)
        er["uid"] = _ensure_uid(rule)
        exported_rules.append(er)

    # Build summaries
    exported_summaries = []
    for channel, summary in summaries.items():
        es = dict(summary)
        es["channel"] = channel
        es["uid"] = summary.get("uid", str(uuid.uuid4()))
        exported_summaries.append(es)

    # Build manifest
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "archive_id": str(uuid.uuid4()),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "product": "agentchattr",
        "app_version": app_version,
        "counts": {
            "messages": len(messages_lines),
            "jobs": len(exported_jobs),
            "rules": len(exported_rules),
            "summaries": len(exported_summaries),
        },
        "attachments_included": False,
    }

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.writestr("messages.jsonl", "\n".join(messages_lines) + "\n" if messages_lines else "")
        zf.writestr("jobs.json", json.dumps(exported_jobs, indent=2, ensure_ascii=False))
        zf.writestr("rules.json", json.dumps(exported_rules, indent=2, ensure_ascii=False))
        zf.writestr("summaries.json", json.dumps(exported_summaries, indent=2, ensure_ascii=False))

    return buf.getvalue()


def _build_artifact_export(store, jobs_store, rules_store, summary_store, app_version, owner, identifiers):
    legacy = build_export(store, jobs_store, rules_store, summary_store, app_version)
    with zipfile.ZipFile(io.BytesIO(legacy)) as zf:
        history = {name: zf.read(name) for name in artifact_codec.HISTORY_MEMBERS}
    original = json.loads(history['manifest.json'])
    lineages, references = [], {}
    for identifier in identifiers:
        snapshot = owner.export_metadata(identifier)
        lineages.append(artifact_codec.portable_lineage(snapshot, archive_id=original['archive_id']))
        for row in snapshot['requests']:
            scope = row['audit']['scope']
            references[('packet', scope['packet_id'])] = scope
        for row in snapshot['versions']:
            references[('version', row['id'])] = row
    index = {'version': 1, 'lineages': sorted(lineages, key=lambda row: row['lineage_id'])}
    index_raw = canonical_utf8(index)
    manifest = artifact_codec.artifact_manifest(original, index)
    history['manifest.json'] = json.dumps(manifest, indent=2, ensure_ascii=False).encode('utf-8')
    members = {artifact_codec.INDEX_MEMBER: index_raw}
    artifact_bytes = len(index_raw)
    for (kind, identifier), reference in sorted(references.items()):
        # No engine/catalog boundary here; one bounded immutable object at a time.
        raw = owner.read_archive_object(kind, identifier, sha256=reference['sha256'], byte_length=reference['byte_length'])
        artifact_bytes += len(raw)
        # Continue measuring/validating owned data after an overage, without
        # retaining arbitrarily many payloads. No successful truncated archive.
        if artifact_bytes <= artifact_codec.MAX_ARCHIVE_BYTES:
            members[artifact_codec.member_name(kind, identifier)] = raw
    history_bytes = sum(map(len, history.values()))
    def limit(bound, actual):
        raise ArtifactArchiveLimit(bound, actual, history_bytes=history_bytes, artifact_bytes=artifact_bytes)
    member_count = len(history) + 1 + len(references)
    if member_count > artifact_codec.MAX_MEMBERS:
        limit('members', member_count)
    if len(history['manifest.json']) > artifact_codec.MAX_MANIFEST_BYTES:
        limit('manifest', len(history['manifest.json']))
    if len(index_raw) > artifact_codec.MAX_INDEX_BYTES:
        limit('index', len(index_raw))
    if history_bytes + artifact_bytes > artifact_codec.MAX_ARCHIVE_BYTES:
        limit('uncompressed', history_bytes + artifact_bytes)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        for name, raw in sorted({**history, **members}.items()):
            compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
            compressed = len(compressor.compress(raw)) + len(compressor.flush())
            method = zipfile.ZIP_STORED if len(raw) > 1000 * max(1, compressed) else zipfile.ZIP_DEFLATED
            zf.writestr(name, raw, compress_type=method, compresslevel=6 if method == zipfile.ZIP_DEFLATED else None)
    data = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        if len(data) > artifact_codec.MAX_ARCHIVE_BYTES:
            compressed_history = sum(row.compress_size for row in zf.infolist() if row.filename in history)
            compressed_artifacts = sum(row.compress_size for row in zf.infolist() if row.filename not in history)
            raise ArtifactArchiveLimit('zip', len(data), history_bytes=compressed_history,
                artifact_bytes=compressed_artifacts,
                container_overhead_bytes=len(data) - compressed_history - compressed_artifacts)
        if len(lineages) > artifact_codec.MAX_LINEAGES:
            limit('lineages', len(lineages))
        artifact_codec.preflight(zf, zip_size=len(data))
    return data


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def _uses_artifact_format(zf):
    if artifact_codec.has_artifact_members(zf.infolist()):
        return True
    try:
        info = zf.getinfo('manifest.json')
        if info.file_size > artifact_codec.MAX_MANIFEST_BYTES:
            return False
        with zf.open(info) as stream:
            raw = stream.read(artifact_codec.MAX_MANIFEST_BYTES + 1)
        if len(raw) > artifact_codec.MAX_MANIFEST_BYTES:
            return False
        manifest = artifact_codec._unique_json(raw)
        schema = manifest.get('schema_version') if isinstance(manifest, dict) else None
        return type(schema) is int and schema == MAX_SCHEMA_VERSION
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, EOFError, zlib.error, zipfile.BadZipFile):
        return False


def is_artifact_archive(data):
    """Bounded discriminator only; never a substitute for strict preflight."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return _uses_artifact_format(zf)
    except (ValueError, TypeError, OSError, RuntimeError, EOFError, zipfile.BadZipFile):
        return False


def _artifact_report():
    return {'ok': True, 'mode': 'merge', 'partial': False,
        'archive': {'archive_id': '', 'schema_version': None, 'created_at': ''},
        'sections': {'artifacts': {'status': 'complete', 'created_lineages': 0, 'created_versions': 0,
            'created_requests': 0, 'duplicate_lineages': 0, 'conflict_lineages': 0, 'invalid_lineages': 0,
            'object_conflict_lineages': 0, 'channel_unavailable_lineages': 0, 'skipped_lineages': 0,
            'orphans': {'objects': 0, 'bytes': 0}, 'details': [], 'section_error': None}},
        'channels': {'created': [], 'remapped': [], 'skipped': []}, 'warnings': []}


def _artifact_failure(report, error, *, storage=False):
    report['ok'], report['error'] = False, error.error
    section = report['sections']['artifacts']
    section['status'] = 'failed' if storage else 'rejected'
    section['section_error'] = {'code': error.code, 'error': error.error}
    report['partial'] = bool(report['channels']['created'] or any(
        row.get(key, 0) for row in report['sections'].values()
        for key in ('created', 'updated', 'messages_created', 'created_lineages')))
    return report


class _HistorySnapshot:
    def __init__(self, members):
        self.members = members

    def namelist(self):
        return list(self.members)

    def read(self, name):
        return self.members[name]


def _strict_import(zf, zip_size, store, jobs_store, rules_store, summary_store,
                   channel_list, max_channels, policy, owner):
    report = _artifact_report()
    checking_owner = False
    try:
        section = artifact_codec.preflight(zf, zip_size=zip_size)
        manifest, index = section['manifest'], section['index']
        report['archive'] = {key: manifest[key] for key in ('archive_id', 'schema_version', 'created_at')}
        if index is not None:
            if owner is None:
                raise artifact_codec.ArtifactSectionError('artifact_archive_owner_unavailable')
            checking_owner = True
            owner.export_lineage_ids()
            checking_owner = False
            if policy is None:
                raise artifact_codec.ArtifactSectionError('artifact_archive_storage_unavailable')
        if policy is not None:
            with _import_boundary(policy):
                if policy.catalog.snapshot()['intent']:
                    raise artifact_codec.ArtifactSectionError('artifact_archive_repair_pending')
        # CRC/body verification precedes all mutations. The historical merge
        # algorithms then read these immutable, already-bounded history bytes.
        history = {}
        for info in zf.infolist():
            if info.filename in artifact_codec.HISTORY_MEMBERS:
                history[info.filename] = artifact_codec._bounded_read(zf, info, artifact_codec.MAX_ARCHIVE_BYTES)
        frozen = _HistorySnapshot(history)
        if policy is not None:
            return _configured_import(frozen, store, jobs_store, rules_store, summary_store,
                channel_list, max_channels, policy, report, artifact_store=owner,
                artifact_section=(zf, index) if index is not None else None)
        return _legacy_import(frozen, store, jobs_store, rules_store, summary_store, channel_list, max_channels, report)
    except artifact_codec.ArtifactSectionError as error:
        return _artifact_failure(report, error, storage=error.code == 'artifact_archive_storage_unavailable')
    except (ChannelUnavailable, OSError):
        return _artifact_failure(report,
            artifact_codec.ArtifactSectionError('artifact_archive_storage_unavailable'), storage=not checking_owner)
    except (ValueError, TypeError, KeyError, RuntimeError, EOFError, zlib.error, zipfile.BadZipFile):
        return _artifact_failure(report, artifact_codec.ArtifactSectionError())


def _artifact_skip(section, ordinal, reason, *, collision_kinds=(), channel_reason=None):
    counter = {'duplicate': 'duplicate_lineages', 'uid_collision': 'conflict_lineages',
        'invalid_lineage': 'invalid_lineages', 'object_conflict': 'object_conflict_lineages',
        'channel_unavailable': 'channel_unavailable_lineages'}[reason]
    section[counter] += 1
    section['skipped_lineages'] += 1
    section['details'].append({'ordinal': ordinal, 'reason': reason,
        'collision_kinds': list(collision_kinds) if reason == 'uid_collision' else [], 'channel_reason': channel_reason})
    if reason != 'duplicate':
        section['status'] = 'partial'


def _artifact_channel(report, resolved, raw, channel_list):
    if resolved['created']:
        report['channels']['created'].append(resolved['channel'])
        if resolved['channel'] not in channel_list:
            channel_list.append(resolved['channel'])
    if resolved['reason']:
        entry = {'from': raw, 'to': resolved['channel'], 'reason': resolved['reason']}
        report['channels']['remapped'].append(entry)
        counts = report['channels'].setdefault('remap_counts', [])
        prior = next((row for row in counts if all(row.get(key) == value for key, value in entry.items())), None)
        if prior is None:
            counts.append({**entry, 'count': 1})
        else:
            prior['count'] += 1


def _import_artifact_lineages(zf, index, owner, policy, channel_list, max_channels, report):
    section, receipts = report['sections']['artifacts'], []
    uncertain = False
    try:
        for ordinal, lineage in enumerate(index['lineages']):
            try:
                objects = artifact_codec.read_lineage_objects(zf, lineage)
                prepared = owner.prepare_import_lineage(lineage, objects)
                receipts.extend(prepared.created_objects)
                with _import_boundary(policy):
                    result = owner.classify_import_lineage(prepared)
                    if result is None:
                        catalog = policy.catalog.snapshot()
                        raw = lineage['channel']
                        if (raw not in catalog['channels'] and raw not in catalog['retired'] and not catalog['intent']
                                and sum(state == 'active' for state in catalog['channels'].values()) >= max_channels):
                            _artifact_skip(section, ordinal, 'channel_unavailable', channel_reason='invalid_or_full')
                            continue
                        resolved = policy.resolve_import_channel(raw, max_channels=max_channels)
                        _artifact_channel(report, resolved, raw, channel_list)
                        result = owner.import_lineage(prepared, channel=resolved['channel'])
                if result['status'] == 'created':
                    section['created_lineages'] += 1
                    section['created_versions'] += result['created_versions']
                    section['created_requests'] += result['created_requests']
                else:
                    _artifact_skip(section, ordinal, result['reason'], collision_kinds=result['collision_kinds'])
            except ArtifactImportCollision as error:
                receipts.extend(error._created_objects or ())
                _artifact_skip(section, ordinal, error.reason, collision_kinds=error.collision_kinds)
            except (artifact_codec.ArtifactLineageError, ArtifactValidationError):
                _artifact_skip(section, ordinal, 'invalid_lineage')
            except ArtifactUnavailable as error:
                if hasattr(error, '_created_objects') and error._created_objects is None:
                    uncertain = True
                raise
            time.sleep(0)
    finally:
        section['orphans'] = owner._import_orphans(None if uncertain else tuple(receipts))


def import_archive(zip_bytes: bytes, store, jobs_store, rules_store,
                   summary_store, channel_list: list[str],
                   max_channels: int = 8, *, channel_policy=None, artifact_store=None) -> dict:
    """Import a zip archive, merging into current stores.

    Returns a report dict with counts and warnings.
    """
    # Issue #5: import lock prevents concurrent imports
    if not _import_lock.acquire(blocking=False):
        return {"ok": False, "error": "import already running"}

    try:
        strict = is_artifact_archive(zip_bytes)
        if channel_policy is not None:
            if type(max_channels) is not int or max_channels < 1:
                raise ValueError('Import channel capacity must be a positive integer.')
            if not strict:
                with _import_boundary(channel_policy):
                    if channel_policy.catalog.snapshot()['intent']:
                        raise ChannelConflict('Finish channel repair before importing.')
        return _do_import(zip_bytes, store, jobs_store, rules_store,
                          summary_store, channel_list, max_channels, channel_policy=channel_policy, artifact_store=artifact_store)
    finally:
        _import_lock.release()


def _do_import(zip_bytes, store, jobs_store, rules_store,
               summary_store, channel_list, max_channels, *, channel_policy=None, artifact_store=None):
    warnings = []

    # Validate zip
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        return {"ok": False, "error": "invalid zip archive"}

    if _uses_artifact_format(zf):
        with zf:
            return _strict_import(zf, len(zip_bytes), store, jobs_store, rules_store, summary_store,
                channel_list, max_channels, channel_policy, artifact_store)

    # Check total uncompressed size
    total_size = sum(info.file_size for info in zf.infolist())
    if total_size > MAX_IMPORT_SIZE:
        return {"ok": False, "error": f"archive too large ({total_size // 1024 // 1024}MB, limit {MAX_IMPORT_SIZE // 1024 // 1024}MB)"}

    # Read manifest
    if "manifest.json" not in zf.namelist():
        return {"ok": False, "error": "missing manifest.json"}

    try:
        manifest = json.loads(zf.read("manifest.json"))
    except (json.JSONDecodeError, KeyError):
        return {"ok": False, "error": "corrupt manifest.json"}

    if manifest.get("schema_version", 0) > SCHEMA_VERSION:
        return {"ok": False, "error": f"unsupported archive schema_version: {manifest.get('schema_version')}. Update agentchattr to import this archive."}

    archive_info = {
        "archive_id": manifest.get("archive_id", ""),
        "schema_version": manifest.get("schema_version"),
        "created_at": manifest.get("created_at", ""),
    }

    report = {
        "ok": True,
        "mode": "merge",
        "archive": archive_info,
        "sections": {},
        "channels": {"created": [], "remapped": [], "skipped": []},
        "warnings": warnings,
    }

    if channel_policy is not None:
        return _configured_import(zf, store, jobs_store, rules_store, summary_store,
                                  channel_list, max_channels, channel_policy, report, artifact_store=artifact_store)

    return _legacy_import(zf, store, jobs_store, rules_store, summary_store, channel_list, max_channels, report)


def _legacy_import(zf, store, jobs_store, rules_store, summary_store, channel_list, max_channels, report):
    warnings = report['warnings']
    # Collect existing UIDs for dedup
    existing_msg_uids = set()
    for m in store.get_recent(count=999_999_999):
        existing_msg_uids.add(_ensure_uid(m))

    existing_job_uids = set()
    if jobs_store:
        for j in jobs_store.list_all():
            existing_job_uids.add(_ensure_uid(j))

    existing_rule_uids = set()
    if rules_store:
        for r in rules_store.list_all():
            existing_rule_uids.add(_ensure_uid(r))

    # Helper: resolve channel
    def resolve_channel(ch: str) -> str:
        if not ch:
            return "general"
        if ch in channel_list:
            return ch
        # Try to auto-create
        if len(channel_list) < max_channels:
            if re.match(r'^[a-z0-9][a-z0-9-]{0,29}$', ch):
                channel_list.append(ch)
                report["channels"]["created"].append(ch)
                return ch
        # Remap to general
        report["channels"]["remapped"].append({"from": ch, "to": "general", "reason": "invalid_or_full"})
        return "general"

    # --- Import messages (preserve archive uid, timestamp, time, reply links) ---
    msg_report = {"created": 0, "duplicates": 0, "conflicts": 0, "skipped": 0}
    # Two-pass: first import all messages, then rebuild reply_to links
    imported_uid_to_local_id = {}  # archive uid → new local id
    pending_replies = []  # (new_local_id, reply_to_uid)
    if "messages.jsonl" in zf.namelist():
        raw = zf.read("messages.jsonl").decode("utf-8", errors="replace")
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                msg_report["skipped"] += 1
                continue
            msg_uid = msg.get("uid") or "fp-" + _fingerprint(msg)
            if msg_uid in existing_msg_uids:
                msg_report["duplicates"] += 1
                continue
            channel = resolve_channel(msg.get("channel", "general"))
            metadata = deepcopy(msg.get("metadata")) if isinstance(msg.get("metadata"), dict) else {}
            for field in ('seat_identity_id', 'provenance', 'dispatch_id', 'run_id',
                          'turn_id', 'attempt_id', 'input_revision', 'routing_scope',
                          'quarantine_session_id', 'quarantine_reason', 'recipient_routing'):
                metadata.pop(field, None)
            metadata['imported'] = True
            new_msg = store.add(
                sender=msg.get("sender", "unknown"),
                text=msg.get("text", ""),
                msg_type=msg.get("type", "chat"),
                attachments=msg.get("attachments"),
                channel=channel,
                metadata=metadata,
                uid=msg_uid,
                timestamp=msg.get("timestamp"),
                time_str=msg.get("time"),
                _bulk=True,
            )
            imported_uid_to_local_id[msg_uid] = new_msg["id"]
            # Track reply links for second pass
            reply_to_uid = msg.get("reply_to_uid")
            if reply_to_uid:
                pending_replies.append((new_msg["id"], reply_to_uid))
            existing_msg_uids.add(msg_uid)
            msg_report["created"] += 1
        # Flush bulk-added messages and rebuild reply links (single rewrite)
        if msg_report["created"] > 0:
            if pending_replies:
                uid_to_id = dict(imported_uid_to_local_id)
                for m in store.get_recent(count=999_999_999):
                    uid = m.get("uid")
                    if uid:
                        uid_to_id[uid] = m["id"]
                with store._lock:
                    for local_id, reply_uid in pending_replies:
                        target_id = uid_to_id.get(reply_uid)
                        if target_id is not None:
                            for m in store._messages:
                                if m["id"] == local_id:
                                    m["reply_to"] = target_id
                                    break
            # Single rewrite covers both bulk messages and reply patches
            store.flush_bulk()
    report["sections"]["messages"] = msg_report

    # --- Import jobs (Issue #3: preserve status, timestamps, job message identity) ---
    job_report = {"created": 0, "updated": 0, "messages_created": 0, "duplicates": 0, "conflicts": 0}
    _job_id_remap = {}  # old numeric job_id → new local job_id
    if "jobs.json" in zf.namelist() and jobs_store:
        try:
            imported_jobs = json.loads(zf.read("jobs.json"))
        except json.JSONDecodeError:
            imported_jobs = []
            warnings.append("jobs.json was malformed; skipped")
        for job in imported_jobs:
            job_uid = job.get("uid") or "fp-" + _fingerprint(job)
            if job_uid in existing_job_uids:
                job_report["duplicates"] += 1
                continue
            channel = resolve_channel(job.get("channel", "general"))
            new_job = jobs_store.create(
                title=job.get("title", "Imported job"),
                job_type=job.get("type", "job"),
                channel=channel,
                created_by=job.get("created_by", "import"),
                body=job.get("body"),
                assignee=job.get("assignee"),
                uid=job_uid,
                status=job.get("status"),
                created_at=job.get("created_at"),
                updated_at=job.get("updated_at"),
            )
            # Import job messages with preserved identity
            for jm in job.get("messages", []):
                jm_uid = jm.get("uid") or "fp-" + hashlib.sha256(
                    f"{jm.get('sender', '')}|{jm.get('text', '')}|{jm.get('timestamp', '')}".encode()
                ).hexdigest()[:16]
                jobs_store.add_message(
                    job_id=new_job["id"],
                    sender=jm.get("sender", "unknown"),
                    text=jm.get("text", ""),
                    attachments=jm.get("attachments"),
                    msg_type=jm.get("type", "chat"),
                    uid=jm_uid,
                    timestamp=jm.get("timestamp"),
                    time_str=jm.get("time"),
                )
                job_report["messages_created"] += 1
            # Restore original updated_at (add_message bumps it to now)
            if job.get("updated_at") is not None:
                with jobs_store._lock:
                    for j in jobs_store._jobs:
                        if j["id"] == new_job["id"]:
                            j["updated_at"] = job["updated_at"]
                            jobs_store._save()
                            break
            # Track old→new ID mapping for breadcrumb remap
            old_id = job.get("id")
            if old_id is not None:
                _job_id_remap[old_id] = new_job["id"]
            existing_job_uids.add(job_uid)
            job_report["created"] += 1
        # Remap job_created breadcrumb messages to point at new job IDs
        # Only touch imported messages (by uid), not pre-existing local ones
        if _job_id_remap and imported_uid_to_local_id:
            imported_local_ids = set(imported_uid_to_local_id.values())
            with store._lock:
                for m in store._messages:
                    if (m.get("type") == "job_created"
                            and m["id"] in imported_local_ids
                            and isinstance(m.get("metadata"), dict)):
                        old_jid = m["metadata"].get("job_id")
                        if old_jid in _job_id_remap:
                            m["metadata"]["job_id"] = _job_id_remap[old_jid]
                store._rewrite()
    report["sections"]["jobs"] = job_report

    # --- Import rules ---
    rule_report = {"created": 0, "duplicates": 0, "conflicts": 0}
    if "rules.json" in zf.namelist() and rules_store:
        try:
            imported_rules = json.loads(zf.read("rules.json"))
        except json.JSONDecodeError:
            imported_rules = []
            warnings.append("rules.json was malformed; skipped")
        for rule in imported_rules:
            rule_uid = rule.get("uid") or "fp-" + _fingerprint(rule)
            if rule_uid in existing_rule_uids:
                rule_report["duplicates"] += 1
                continue
            new_rule = rules_store.propose(
                text=rule.get("text", ""),
                author=rule.get("author", "import"),
                reason=rule.get("reason", ""),
            )
            if new_rule:
                # Patch uid onto the rule record and save
                new_rule["uid"] = rule_uid
                rules_store._save()
                # Restore status if not pending — patch directly to avoid
                # state machine transition guards (e.g. deactivate only works
                # from active/proposed/draft, not pending)
                status = rule.get("status", "pending")
                if status != "pending":
                    with rules_store._lock:
                        for r in rules_store._rules:
                            if r["id"] == new_rule["id"]:
                                r["status"] = status
                                if status == "archived":
                                    r["archived_at"] = rule.get("archived_at", time.time())
                                if status == "active":
                                    rules_store._bump_epoch()
                                break
                        rules_store._save()
            existing_rule_uids.add(rule_uid)
            rule_report["created"] += 1
    report["sections"]["rules"] = rule_report

    # --- Import summaries (Issue #4: resolve channels properly) ---
    summary_report = {"created": 0, "updated": 0, "skipped": 0}
    if "summaries.json" in zf.namelist() and summary_store:
        try:
            imported_summaries = json.loads(zf.read("summaries.json"))
        except json.JSONDecodeError:
            imported_summaries = []
            warnings.append("summaries.json was malformed; skipped")
        for summary in imported_summaries:
            raw_channel = summary.get("channel", "")
            if not raw_channel:
                summary_report["skipped"] += 1
                continue
            # Resolve through channel resolver (creates if valid and capacity allows)
            channel = resolve_channel(raw_channel)
            # Skip summaries for remapped channels (don't overwrite general with wrong summary)
            if channel != raw_channel and raw_channel not in channel_list:
                summary_report["skipped"] += 1
                warnings.append(f"summary for '{raw_channel}' skipped (channel unavailable)")
                continue
            existing = summary_store.get(channel)
            s_uid = summary.get("uid")
            s_updated = summary.get("updated_at")
            if existing:
                if (s_updated or 0) > existing.get("updated_at", 0):
                    summary_store.write(
                        channel=channel,
                        text=summary.get("text", ""),
                        author=summary.get("author", "import"),
                        uid=s_uid,
                        updated_at=s_updated,
                    )
                    summary_report["updated"] += 1
                else:
                    summary_report["skipped"] += 1
            else:
                summary_store.write(
                    channel=channel,
                    text=summary.get("text", ""),
                    author=summary.get("author", "import"),
                    uid=s_uid,
                    updated_at=s_updated,
                )
                summary_report["created"] += 1
    report["sections"]["summaries"] = summary_report

    return report


@contextmanager
def _import_boundary(policy):
    with policy._boundary():
        policy.catalog.snapshot()
        yield


def _chunks(rows):
    iterator = iter(rows)
    while batch := list(islice(iterator, 64)):
        yield batch


def _array_rows(zf, name, warnings):
    if name not in zf.namelist():
        return []
    try:
        rows = json.loads(zf.read(name))
        if not isinstance(rows, list):
            raise ValueError()
        return [row for row in rows if isinstance(row, dict)]
    except (ValueError, UnicodeError):
        warnings.append(name + ' was malformed; skipped')
        return []


def _patch_import_messages(store, patches, policy, *, field):
    skipped = 0
    for batch in _chunks(patches):
        with _import_boundary(policy):
            active = {}
            for message_id, value in batch:
                saved = store.get_snapshot(message_id)
                if saved is None:
                    skipped += 1
                    continue
                try:
                    policy.require_active(saved.get('channel', 'general'))
                except ChannelInactive:
                    skipped += 1
                    continue
                active[message_id] = value
            if active:
                with store._lock:
                    staged = []
                    for message in store._messages:
                        if message['id'] in active:
                            message = deepcopy(message)
                            if field == 'reply_to':
                                message[field] = active[message['id']]
                            else:
                                message.setdefault('metadata', {})[field] = active[message['id']]
                        staged.append(message)
                    store._rewrite_jsonl(staged)
                    store._messages = staged
        time.sleep(0)  # Yield only after durable commit and boundary release.
    return skipped


def _configured_import(zf, store, jobs_store, rules_store, summary_store,
                       channel_list, max_channels, policy, report, *, artifact_store=None, artifact_section=None):
    """Catalog-aware import; each bounded mutation releases the engine lock."""
    warnings, remap_counts = report['warnings'], {}
    report['channels']['remap_counts'] = []

    def resolve(raw, *, redirected=True):
        result = policy.resolve_import_channel(raw, max_channels=max_channels)
        if result['created']:
            report['channels']['created'].append(result['channel'])
            if result['channel'] not in channel_list:
                channel_list.append(result['channel'])
        if result['reason'] and redirected:
            entry = {'from': raw, 'to': 'general', 'reason': result['reason']}
            report['channels']['remapped'].append(entry)
            key = (json.dumps(raw, sort_keys=True), result['reason'])
            counted = remap_counts.setdefault(key, {**entry, 'count': 0})
            counted['count'] += 1
        return result

    # Copies avoid assigning missing legacy UIDs into read-only stored history.
    message_uids = {m.get('uid') or _ensure_uid(dict(m)) for m in store.get_recent(999_999_999)}
    job_uids = {j.get('uid') or _ensure_uid(dict(j)) for j in jobs_store.list_all()} if jobs_store else set()
    rule_uids = {r.get('uid') or _ensure_uid(dict(r)) for r in rules_store.list_all()} if rules_store else set()
    msg_report = dict(created=0, duplicates=0, conflicts=0, skipped=0, reply_links_skipped=0)
    report['sections']['messages'] = msg_report
    imported_ids, replies = {}, []

    def message_rows():
        if 'messages.jsonl' not in zf.namelist():
            return
        raw = zf.read('messages.jsonl').decode('utf-8', errors='replace')
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError()
                yield message
            except ValueError:
                msg_report['skipped'] += 1

    for batch in _chunks(message_rows()):  # Decode/parse before taking policy.
        with _import_boundary(policy):
            staged, reply_uids, seen = [], {}, set()
            for message in batch:
                uid = message.get('uid') or 'fp-' + _fingerprint(message)
                if uid in message_uids or uid in seen:
                    msg_report['duplicates'] += 1
                    continue
                channel = resolve(message.get('channel', 'general'))['channel']
                metadata = deepcopy(message.get('metadata')) if isinstance(message.get('metadata'), dict) else {}
                for key in ('seat_identity_id', 'provenance', 'dispatch_id', 'run_id', 'turn_id', 'attempt_id',
                            'input_revision', 'routing_scope', 'quarantine_session_id', 'quarantine_reason', 'recipient_routing'):
                    metadata.pop(key, None)
                staged.append({**message, 'uid': uid, 'channel': channel, 'metadata': metadata})
                seen.add(uid)
                if message.get('reply_to_uid'):
                    reply_uids[uid] = message['reply_to_uid']
            saved = store._append_imported_batch(staged)
            msg_report['duplicates'] += len(staged) - len(saved)
            for message in saved:
                imported_ids[message['uid']] = message['id']
                if message['uid'] in reply_uids:
                    replies.append((message['id'], reply_uids[message['uid']]))
            message_uids.update(seen)
            msg_report['created'] += len(saved)
        time.sleep(0)

    uid_to_id = {m.get('uid'): m['id'] for m in store.get_recent(999_999_999) if m.get('uid')}
    msg_report['reply_links_skipped'] = _patch_import_messages(store,
        ((mid, uid_to_id[uid]) for mid, uid in replies if uid in uid_to_id), policy, field='reply_to')

    job_report = dict(created=0, updated=0, messages_created=0, duplicates=0, conflicts=0,
                      messages_skipped=0, partial=[], breadcrumbs_skipped=0)
    report['sections']['jobs'] = job_report
    job_ids = {}
    for job in _array_rows(zf, 'jobs.json', warnings) if jobs_store else []:
        with _import_boundary(policy):
            uid = job.get('uid') or 'fp-' + _fingerprint(job)
            if uid in job_uids:
                job_report['duplicates'] += 1
                continue
            channel = resolve(job.get('channel', 'general'))['channel']
            saved = jobs_store.create(title=job.get('title', 'Imported job'), job_type=job.get('type', 'job'),
                channel=channel, created_by=job.get('created_by', 'import'), body=job.get('body'),
                assignee=job.get('assignee'), uid=uid, status=job.get('status'),
                created_at=job.get('created_at'), updated_at=job.get('updated_at'))
            job_uids.add(uid)
            job_report['created'] += 1
            if job.get('id') is not None:
                job_ids[job['id']] = saved['id']
        time.sleep(0)
        conversation = job.get('messages', [])
        landed, skipped = 0, 0
        for index, message in enumerate(conversation):
            with _import_boundary(policy):
                try:
                    policy.require_active(channel)
                except ChannelInactive:
                    skipped = len(conversation) - index
                    break
                uid = message.get('uid') or 'fp-' + hashlib.sha256(
                    f"{message.get('sender', '')}|{message.get('text', '')}|{message.get('timestamp', '')}".encode()).hexdigest()[:16]
                jobs_store.add_message(saved['id'], message.get('sender', 'unknown'), message.get('text', ''),
                    attachments=message.get('attachments'), msg_type=message.get('type', 'chat'), uid=uid,
                    timestamp=message.get('timestamp'), time_str=message.get('time'))
                landed += 1
                job_report['messages_created'] += 1
            time.sleep(0)
        with _import_boundary(policy):
            try:
                policy.require_active(channel)
            except ChannelInactive:
                pass  # An archived job freezes its latest persisted timestamp too.
            else:
                if job.get('updated_at') is not None:
                    with jobs_store._lock:
                        for current in jobs_store._jobs:
                            if current['id'] == saved['id']:
                                current['updated_at'] = job['updated_at']
                                jobs_store._save()
                                break
        if skipped:
            job_report['messages_skipped'] += skipped
            job_report['partial'].append({'job_id': saved['id'], 'messages_imported': landed,
                'messages_skipped': skipped, 'reason': 'channel_retired', 'reimport': 'existing_job_uid_skipped'})
            warnings.append(f"Job #{saved['id']} imported partially: {landed} conversation rows saved, {skipped} skipped (channel_retired). "
                            'Re-import skips this existing job UID and will not fill its missing rows.')
        time.sleep(0)
    imported_set = set(imported_ids.values())
    breadcrumbs = [(m['id'], job_ids[m['metadata']['job_id']]) for m in store.get_recent(999_999_999)
        if m['id'] in imported_set and m.get('type') == 'job_created'
        and isinstance(m.get('metadata'), dict) and m['metadata'].get('job_id') in job_ids]
    job_report['breadcrumbs_skipped'] = _patch_import_messages(store, breadcrumbs, policy, field='job_id')

    rule_report = dict(created=0, duplicates=0, conflicts=0)
    report['sections']['rules'] = rule_report
    for rule in _array_rows(zf, 'rules.json', warnings) if rules_store else []:
        with _import_boundary(policy):
            uid = rule.get('uid') or 'fp-' + _fingerprint(rule)
            if uid in rule_uids:
                rule_report['duplicates'] += 1
                continue
            saved = rules_store.propose(rule.get('text', ''), rule.get('author', 'import'), rule.get('reason', ''))
            if saved:
                with rules_store._lock:
                    saved['uid'] = uid
                    status = rule.get('status', 'pending')
                    if status != 'pending':
                        saved['status'] = status
                        if status == 'archived':
                            saved['archived_at'] = rule.get('archived_at', time.time())
                        if status == 'active':
                            rules_store._bump_epoch()
                    rules_store._save()
            rule_uids.add(uid)
            rule_report['created'] += 1
        time.sleep(0)

    summary_report = dict(created=0, updated=0, skipped=0)
    report['sections']['summaries'] = summary_report
    for summary in _array_rows(zf, 'summaries.json', warnings) if summary_store else []:
        with _import_boundary(policy):
            raw = summary.get('channel', '')
            if not raw:
                summary_report['skipped'] += 1
                continue
            resolved = resolve(raw, redirected=False)
            if resolved['channel'] != raw:
                summary_report['skipped'] += 1
                warnings.append(f"Summary for {raw!r} skipped ({resolved['reason']}).")
                continue
            existing = summary_store.get(raw)
            if existing and (summary.get('updated_at') or 0) <= existing.get('updated_at', 0):
                summary_report['skipped'] += 1
                continue
            summary_store.write(raw, summary.get('text', ''), summary.get('author', 'import'),
                uid=summary.get('uid'), updated_at=summary.get('updated_at'))
            summary_report['updated' if existing else 'created'] += 1
        time.sleep(0)
    report['channels']['remap_counts'] = list(remap_counts.values())
    if artifact_section is not None:
        _import_artifact_lineages(artifact_section[0], artifact_section[1], artifact_store, policy,
            channel_list, max_channels, report)
    return report
