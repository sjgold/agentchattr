"""Configured channel policy. Serialize lifecycle decisions with publication."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import time

from channel_lifecycle import (ChannelConflict, ChannelInactive, ChannelUnavailable,
                               _destination, _name, _request_id, RENAME_STEPS)
from dispatch_queue import ACTIVE
from session_engine import PROJECTION_REPAIR_STATES
from retained_artifacts import RetainedArtifactStore, safe_upload_url
from launcher import LaunchError


_LIVE_REVIEW = {'active', 'waiting', 'paused', 'awaiting_input', 'stalled', 'retrying',
                'interrupted', 'prepared'}
_OPS = {'create', 'archive', 'reopen', 'delete', 'rename', 'cancel_queued', 'recover_projections'}


class ChannelService:
    def __init__(self, catalog, *, engine, messages, jobs, schedules, summaries,
                 queue, settings, save_settings, migrate_cursors, router,
                 migrate_last_active, unregistered_channels=(), migrate_fallbacks=None):
        self.catalog, self.engine, self.messages = catalog, engine, messages
        self.jobs, self.schedules, self.summaries = jobs, schedules, summaries
        self.queue, self.settings = queue, settings
        self._save_settings, self._migrate_cursors = save_settings, migrate_cursors
        self.router, self._migrate_last_active = router, migrate_last_active
        self._migrate_fallbacks = migrate_fallbacks
        self._callbacks = []
        self.artifacts = RetainedArtifactStore(catalog.path.with_name('retained_artifacts.json'))
        self._unregistered = set(settings.get('unregistered_channels', []))
        with self._boundary():
            value = catalog.snapshot()
            self._unregistered.update(name for name in unregistered_channels
                                      if name not in value['channels'] and name not in value['retired'])
            self._unregistered.update(name for name in settings.get('channels', [])
                                      if name not in value['channels'] and name not in value['retired'])
            try:
                self._unregistered.update(name for name in self.artifacts.channel_names()
                    if name not in value['channels'] and name not in value['retired'])
            except ChannelUnavailable:
                pass  # Hold retained metadata operations, not chat startup.
            self._project(value)

    @contextmanager
    def _boundary(self):
        # No store lock may be held on entry. Each store read releases its lock
        # before the next store is read; callbacks run after those locks release.
        with self.engine._lock:
            with self.catalog._lock:
                yield

    def _project(self, value):
        previous, unregistered = deepcopy(self.settings), set(self._unregistered)
        try:
            self._unregistered.difference_update(value['channels'])
            self._unregistered.difference_update(value['retired'])
            self.settings['channels'] = [name for name, state in value['channels'].items() if state == 'active']
            self.settings['unregistered_channels'] = sorted(self._unregistered)
            self._save_settings()
        except OSError:
            self.settings.clear()
            self.settings.update(previous)
            self._unregistered = unregistered
            raise

    def on_change(self, callback):
        """Register a channel-level invalidation observer before publication starts."""
        self._callbacks.append(callback)

    def _heal_projection(self, value):
        projected = value
        intent = value['intent']
        # Delete deliberately projects removal before finish. Preserve that
        # accepted ordering when a retry starts after its settings mark.
        if intent and intent['op'] == 'delete' and 'settings' in intent['completed_steps']:
            projected = deepcopy(value)
            projected['channels'][intent['old']] = 'retired'
        active = [name for name, state in projected['channels'].items() if state == 'active']
        if self.settings.get('channels') != active:
            self._project(projected)

    def _emit(self, event):
        for callback in list(self._callbacks):
            try:
                callback(deepcopy(event))
            except Exception:
                pass

    def require_active(self, channel):
        with self._boundary():
            self.catalog.require_active(channel)

    @contextmanager
    def publication(self, channel):
        with self._boundary():
            self.catalog.require_active(channel)
            yield

    def resolve_import_channel(self, name, *, max_channels):
        if type(max_channels) is not int or max_channels < 1:
            raise ValueError('Import channel capacity must be a positive integer.')
        with self._boundary():
            value = self.catalog.snapshot()
            name = 'general' if name is None or name == '' else name
            try:
                _name(name)
            except ValueError:
                return {'channel': 'general', 'created': False, 'reason': 'invalid_or_full'}
            if name in self.catalog.blocked_names():
                return {'channel': 'general', 'created': False, 'reason': 'channel_retired'}
            if value['channels'].get(name) == 'active':
                return {'channel': name, 'created': False, 'reason': None}
            if value['intent']:
                return {'channel': 'general', 'created': False, 'reason': 'channel_repair_pending'}
            if sum(state == 'active' for state in value['channels'].values()) >= max_channels:
                return {'channel': 'general', 'created': False, 'reason': 'invalid_or_full'}
            value = self.catalog.create(name, expected_revision=value['revision'])
            self._project(value)
            return {'channel': name, 'created': True, 'reason': None}

    def _scope(self, channel):
        self.artifacts.check()
        self.engine._store.retained_metadata(channel, limit=1)  # Validate retained authority before a mutation preview.
        messages = deepcopy(self.messages.get_recent(count=2**63, channel=channel))
        ids = {item['id'] for item in messages}
        todos = {key: value for key, value in self.messages.get_todos().items() if key in ids}
        jobs = self.jobs.lifecycle_scope(channel)
        schedules = deepcopy([item for item in self.schedules.list_all() if item.get('channel') == channel])
        runs = self.engine._store.list_all(channel=channel)
        summary = deepcopy(self.summaries.get(channel))
        try:
            transport = self.queue.records(channel)
        except (ValueError, OSError, LaunchError):
            raise ChannelUnavailable('Saved queue records are unavailable; repair storage before changing channels.') from None
        counts = dict(messages=len(messages), todos=len(todos), jobs=len(jobs),
                      schedules=len(schedules), sessions=len(runs), summaries=int(summary is not None),
                      uploads=sum(len(item.get('attachments') or []) for item in messages))
        blockers = []
        def block(kind, run=None, record=None, audit=None, reason=None):
            run, record, audit = run or {}, record or {}, audit or {}
            envelope = record.get('envelope', {})
            blockers.append({'kind': kind, 'session_id': run.get('id'), 'run_id': run.get('run_id') or envelope.get('run_id'),
                'dispatch_id': envelope.get('dispatch_id') or audit.get('dispatch_id'),
                'identity_id': envelope.get('target_identity_id') or audit.get('seat_identity_id'),
                'state': record.get('state') or run.get('state')})
            if reason:
                blockers[-1]['reason'] = reason
        for run in runs:
            if run.get('state') in _LIVE_REVIEW and not run.get('stop_id') and not run.get('replaced_by_run_id'):
                block('review', run=run)
            events = {event['event_id']: event for event in run.get('admitted_events', [])
                      if run.get('completion_protocol') == 1}
            pending = [event for event in events.values() if event.get('projected_message_id') is None]
            pending.extend(events.get(context['question_event_id'], {'reason': 'missing_question_event'})
                           for context in run.get('continuation_context', [])
                           if run.get('completion_protocol') == 1 and context.get('projected_message_id') is None)
            pending.extend({'dispatch_id': skipped['dispatch_id'],
                            'expected_identity_id': skipped.get('seat_identity_id')}
                           for skipped in run.get('skipped_turns', [])
                           if run.get('completion_protocol') == 1 and skipped.get('projected_message_id') is None)
            for event in pending:
                envelope = next((record['envelope'] for record in transport
                    if record['envelope'].get('run_id') == run.get('run_id')
                    and record['envelope'].get('attempt_id') == event.get('attempt_id')), {})
                invocation = run.get('active_invocation') or {}
                if not envelope and invocation.get('attempt_id') == event.get('attempt_id'):
                    envelope = invocation
                block('projection_pending', run=run, audit={
                    'dispatch_id': event.get('dispatch_id') or envelope.get('dispatch_id'),
                    'seat_identity_id': event.get('expected_identity_id')},
                    reason=event.get('reason') or ('live_projection_requires_restart'
                        if run.get('state') not in PROJECTION_REPAIR_STATES else None))
            for attempt in run.get('superseded_attempts', []):
                audit = attempt.get('old_transport') or attempt.get('selected_transport')
                if audit and audit.get('resolved') is not True:
                    block('retired_transport', run=run, audit=audit)
            if run.get('turn_recovery') and run['turn_recovery'].get('status') not in ('complete', 'resolved'):
                block('recovery', run=run)
        for record in transport:
            if record['state'] in ACTIVE | {'queued'}:
                block('transport', record=record)
            if record.get('recovery_hold') and record['recovery_hold'].get('cleared') is not True:
                block('recovery', record=record)
        blockers.sort(key=lambda item: json.dumps(item, sort_keys=True))
        overdue = sum(bool(item.get('active')) and item.get('next_run', 0) <= time.time() for item in schedules)
        stable = {'messages': sorted((item['id'], item.get('uid')) for item in messages),
                  'max_id': max(ids, default=-1), 'todos': sorted(todos), 'uploads': counts['uploads'],
                  'jobs': sorted((item['id'], item.get('updated_at')) for item in jobs),
                  'schedules': sorted((item['id'], item.get('next_run'), item.get('active')) for item in schedules),
                  'summary': [summary.get('uid'), summary.get('updated_at')] if summary else None,
                  'sessions': [(item['id'], item.get('state'), item.get('channel_updated_at', item.get('updated_at')))
                               for item in sorted(runs, key=lambda item: item['id'])],
                  'transport': sorted((item['envelope']['dispatch_id'], item['state']) for item in transport),
                  'blockers': blockers}
        queued = sorted(item['envelope']['dispatch_id'] for item in transport if item['state'] == 'queued')
        return counts, blockers, queued, overdue, stable

    def retained_view(self, channel):
        with self._boundary():
            value = self.catalog.snapshot()
            if type(channel) is not str:
                raise ValueError('Choose a retained channel name.')
            if channel not in value['channels'] and channel not in self._unregistered:
                raise LookupError('Retained channel not found.')
            state = value['channels'].get(channel, 'unregistered')
            if value['intent'] and channel in (value['intent']['old'], value['intent']['new']):
                state = 'held'
            packet = {'channel': channel, 'state': state, 'counts': {}, 'truncated': {}, 'errors': {}}
            for owner, reader in (('jobs', self.jobs.retained_metadata),
                    ('sessions', self.engine._store.retained_metadata),
                    ('schedules', self.schedules.retained_metadata), ('uploads', self.artifacts.read)):
                try:
                    result = reader(channel, limit=100)
                    packet[owner], packet['counts'][owner], packet['truncated'][owner] = (
                        result['rows'], result['count'], result['truncated'])
                except (ChannelUnavailable, OSError):
                    packet[owner] = packet['counts'][owner] = packet['truncated'][owner] = None
                    packet['errors'][owner] = 'Saved records are held; repair storage and reload.'
            for entry in packet['uploads'] or []:
                entry['safe_links'] = [{'url': url, 'name': item.get('name') if type(item.get('name')) is str
                                       else url.removeprefix('/uploads/')}
                    for item in entry['attachments'] if (url := safe_upload_url(item.get('url')))]
            try:
                packet['summary'] = self.summaries.get(channel)
            except (ChannelUnavailable, OSError):
                packet['summary'] = None
                packet['errors']['summary'] = 'Saved summary is held; repair storage and reload.'
            return packet

    def _display_scope(self, channel, queue_counts):
        counts = {key: None for key in ('messages', 'todos', 'jobs', 'schedules', 'sessions', 'summaries', 'uploads', 'queue')}
        errors, messages, overdue = {}, [], None
        def held(owner):
            errors[owner] = f'Saved {owner} are held; repair storage and reload.'
        try:
            messages = self.messages.get_recent(count=2**63, channel=channel)
            counts['messages'] = len(messages)
        except (ChannelUnavailable, OSError):
            held('messages')
        if counts['messages'] is not None:
            try:
                ids = {item['id'] for item in messages}
                counts['todos'] = sum(key in ids for key in self.messages.get_todos())
            except (ChannelUnavailable, OSError):
                held('todos')
            try:
                uids = {item.get('uid') or f'legacy:{item["id"]}' for item in messages}
                counts['uploads'] = sum(len(item.get('attachments') or []) for item in messages) + self.artifacts.reference_count(channel, exclude_uids=uids)
            except (ChannelUnavailable, OSError):
                held('uploads')
        else:
            held('todos'); held('uploads')
        for owner, reader in (('jobs', lambda: len(self.jobs.lifecycle_scope(channel))),
                              ('sessions', lambda: self.engine._store.retained_metadata(channel, limit=1)['count']),
                              ('summaries', lambda: int(self.summaries.contains(channel)))):
            try:
                counts[owner] = reader()
            except (ChannelUnavailable, OSError):
                held(owner)
        try:
            counts['schedules'], overdue = self.schedules.display_counts(channel)
        except (ChannelUnavailable, OSError):
            held('schedules')
        if queue_counts is None:
            held('queue')
        else:
            counts['queue'] = queue_counts.get(channel, 0)
        return counts, errors, overdue

    def catalog_view(self):
        with self._boundary():
            value = self.catalog.snapshot()
            self._heal_projection(value)
            try:
                queue_counts = self.queue.channel_counts()
            except (ChannelUnavailable, ValueError, OSError, LaunchError):
                queue_counts = None
            rows = []
            for name, state in value['channels'].items():
                counts, errors, overdue = self._display_scope(name, queue_counts)
                rows.append({'name': name, 'state': state, 'counts': counts, 'overdue_schedules': overdue, 'errors': errors})
            rows.extend({'name': name, 'state': 'unregistered', 'counts': None, 'overdue_schedules': 0, 'errors': {}}
                        for name in sorted(self._unregistered))
            return {'revision': value['revision'], 'channels': rows, 'intent': value['intent']}

    @staticmethod
    def _action(value, op, channel, new_name):
        _name(channel)
        if type(op) is not str or op not in _OPS:
            raise ValueError('Choose a supported channel action.')
        if op == 'rename':
            _name(new_name)
            _destination(value, channel, new_name)
        elif new_name is not None:
            raise ValueError('Only rename accepts a destination name.')
        state = value['channels'].get(channel)
        if channel == 'general':
            raise ChannelConflict('General is protected.')
        if value['intent']:
            raise ChannelConflict('A channel operation is pending; use its repair action.')
        if op == 'create':
            if state is not None or channel in value['retired']:
                raise ChannelConflict('That channel name is already used or retired.')
        elif state not in ('active', 'archived'):
            raise ChannelInactive('Choose an existing active or archived channel.')
        elif op in ('archive', 'rename') and state != 'active':
            raise ChannelConflict('Reopen this channel first.')
        elif op == 'reopen' and state != 'archived':
            raise ChannelConflict('Only archived channels can be reopened.')
        elif op == 'recover_projections' and state != 'active':
            raise ChannelConflict('Reopen this channel before repairing its history.')

    def preview(self, op, channel, *, new_name=None):
        with self._boundary():
            value = self.catalog.snapshot()
            self._heal_projection(value)
            self._action(value, op, channel, new_name)
            if op == 'delete':
                self.artifacts.check()
            counts, blockers, queued, overdue, stable = self._scope(channel)
            destination = None
            if op == 'rename':
                destination_counts, destination_blockers, _, _, destination = self._scope(new_name)
                if any(destination_counts.values()) or destination_blockers:
                    raise ChannelConflict('Destination contains saved data or unresolved work; choose an unused name.')
                # Terminal queue history is immutable audit, not destination occupancy.
                destination['transport'] = []
            token = hashlib.sha256(json.dumps([op, channel, new_name, value['revision'], stable],
                # Destination preflight is repeated at apply, before begin.
                sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
            if destination is not None:
                token = hashlib.sha256((token + json.dumps(destination, sort_keys=True,
                    separators=(',', ':'), allow_nan=False)).encode('utf-8')).hexdigest()
            return {'op': op, 'channel': channel, 'new_name': new_name, 'revision': value['revision'],
                    'state': value['channels'].get(channel), 'counts': counts, 'blockers': blockers,
                    'queued_dispatch_ids': queued, 'overdue_schedules': overdue, 'preview_token': token}

    def apply(self, op, channel, *, new_name=None, request_id, confirmation, preview_token):
        _request_id(request_id)
        if op == 'rename':
            return self._apply_rename(channel, new_name, request_id, confirmation, preview_token)
        with self._boundary():
            pending = self.catalog.snapshot()['intent']
            if pending and (pending['request_id'], pending['op'], pending['old'], pending['new']) == (
                    request_id, op, channel, new_name) and confirmation == channel:
                return self.retry(request_id)
            preview = self.preview(op, channel, new_name=new_name)
            if type(confirmation) is not str or confirmation != channel:
                raise ChannelConflict('Type the exact channel name to confirm.')
            if type(preview_token) is not str or preview_token != preview['preview_token']:
                raise ChannelConflict('Channel contents or work changed; refresh the preview.')
            blockers = preview['blockers']
            if op == 'recover_projections':
                if not any(item['kind'] == 'projection_pending' and not item.get('reason') for item in blockers):
                    raise ChannelConflict('No repairable history is pending; live work must wait or restart.')
                repair = self._repair_projections(channel)
                return {'ok': True, 'revision': preview['revision'], 'channel': channel,
                        'state': 'active', 'op': op, 'projection_repair': repair}
            if op == 'cancel_queued':
                blockers = [item for item in blockers if not (item['kind'] == 'transport' and item['state'] == 'queued')]
            if blockers and op not in ('reopen', 'create'):
                raise ChannelConflict('Channel work is still pending; inspect its blocking scope first.')
            if op == 'create':
                value = self.catalog.create(channel, expected_revision=preview['revision'])
            elif op in ('archive', 'reopen'):
                value = self.catalog.set_state(channel, 'archived' if op == 'archive' else 'active',
                                               expected_revision=preview['revision'])
            elif op == 'cancel_queued':
                if not preview['queued_dispatch_ids']:
                    raise ChannelConflict('There are no queued messages to cancel.')
                self.queue.cancel_queued_channel(channel, preview['queued_dispatch_ids'], request_id)
                value = self.catalog.snapshot()
            elif op == 'delete':
                try:
                    self.artifacts.probe()
                except OSError:
                    raise ChannelUnavailable('Retained upload storage is unavailable; no delete intent was started.') from None
                self.catalog.begin('delete', channel, None, request_id=request_id,
                                   expected_revision=preview['revision'])
                return self.retry(request_id)
            else:
                raise ChannelConflict('Rename requires the separately reviewed migration step.')
            self._project(value)
            result = {'ok': True, 'revision': value['revision'], 'channel': channel,
                      'state': value['channels'].get(channel), 'op': op}
            if op == 'reopen':
                try:
                    result['projection_repair'] = self._repair_projections(channel)
                except ChannelUnavailable:
                    result['projection_repair_error'] = 'History repair did not finish. Inspect pending work and try repair again.'
            return result

    def _repair_projections(self, channel):
        try:
            return self.engine.recover_projections(channel=channel, terminal_only=True)
        except Exception:
            raise ChannelUnavailable('History repair did not finish; reload management and retry.') from None

    def _apply_rename(self, channel, new_name, request_id, confirmation, preview_token):
        with self._boundary():
            value = self.catalog.snapshot()
            self._heal_projection(value)
            pending = value['intent']
            if type(confirmation) is not str or confirmation != channel:
                raise ChannelConflict('Type the exact channel name to confirm.')
            if not (pending and (pending['request_id'], pending['op'], pending['old'], pending['new']) ==
                    (request_id, 'rename', channel, new_name)):
                preview = self.preview('rename', channel, new_name=new_name)
                if type(preview_token) is not str or preview_token != preview['preview_token']:
                    raise ChannelConflict('Channel contents or work changed; refresh the preview.')
                if preview['blockers']:
                    raise ChannelConflict('Channel work is still pending; inspect its blocking scope first.')
                self.catalog.begin('rename', channel, new_name, request_id=request_id,
                                   expected_revision=preview['revision'])
        # Never retain an outer apply boundary across the seven step boundaries.
        return self.retry(request_id)

    def _retry_rename(self, request_id):
        try:
            for step in RENAME_STEPS:
                with self._boundary():
                    value = self.catalog.snapshot()
                    intent = value['intent']
                    if not intent or intent['request_id'] != request_id or intent['op'] != 'rename':
                        raise ChannelConflict('That operation is no longer pending; reload the catalog.')
                    if step in intent['completed_steps']:
                        continue
                    old, new = intent['old'], intent['new']
                    if step == 'messages':
                        self.messages.rename_channel(old, new)
                    elif step == 'jobs':
                        self.jobs.rename_channel(old, new)
                    elif step == 'schedules':
                        self.schedules.rename_channel(old, new)
                    elif step == 'summaries':
                        self.summaries.rename_channel(old, new)
                    elif step == 'sessions':
                        self.engine._store.rename_channel(old, new)
                    elif step == 'cursors':
                        if self._migrate_cursors:
                            self._migrate_cursors(old, new)
                    else:
                        self._project(value)  # Flush OLD names before the catalog commit.
                    self.catalog.complete_step(request_id, step)
            with self._boundary():
                value = self.catalog.snapshot()
                intent = value['intent']
                if not intent or intent['request_id'] != request_id or intent['op'] != 'rename':
                    raise ChannelConflict('That operation is no longer pending; reload the catalog.')
                old, new = intent['old'], intent['new']
                if self.router:
                    self.router.rename_channel(old, new)
                if self._migrate_last_active:
                    self._migrate_last_active(old, new)
                if self._migrate_fallbacks:
                    self._migrate_fallbacks(old, new)
                value = self.catalog.finish(request_id)
                result = {'ok': True, 'op': 'rename', 'channel': new, 'old_name': old,
                          'new_name': new, 'state': value['channels'][new], 'revision': value['revision']}
                try:
                    self._project(value)
                except OSError:
                    result['projection_warning'] = 'Rename committed. Reload channel management to refresh navigation.'
                self._emit({'type': 'channel_renamed', 'old_name': old, 'new_name': new,
                            'revision': value['revision']})
                return result
        except OSError:
            raise ChannelUnavailable('Channel rename could not finish; reload management and retry its pending intent.') from None

    def retry(self, request_id):
        _request_id(request_id)
        with self._boundary():
            value = self.catalog.snapshot()
            self._heal_projection(value)
            intent = value['intent']
            rename = bool(intent and intent['request_id'] == request_id and intent['op'] == 'rename')
        if rename:
            return self._retry_rename(request_id)
        with self._boundary():
            value = self.catalog.snapshot()
            intent = value['intent']
            if intent is None or intent['request_id'] != request_id:
                raise ChannelConflict('That operation is no longer pending; reload the catalog.')
            if intent['op'] != 'delete':
                raise ChannelConflict('Rename repair requires the separately reviewed migration step.')
            channel, removed = intent['old'], []
            try:
                for step in ('todos', 'messages', 'settings'):
                    if step in intent['completed_steps']:
                        continue
                    if step == 'todos':
                        self.messages.remove_channel_todos(channel)
                    elif step == 'messages':
                        self.artifacts.retain(channel, self.messages.get_recent(count=2**63, channel=channel))
                        removed = self.messages.remove_channel_messages(channel)
                    else:
                        projected = self.catalog.snapshot()
                        projected['channels'][channel] = 'retired'
                        self._project(projected)
                    self.catalog.complete_step(request_id, step)
                value = self.catalog.finish(request_id)
            except OSError:
                raise ChannelUnavailable('Channel operation could not finish; reload management and retry its pending intent.') from None
            self.messages.notify_deleted(removed)
            self._emit({'type': 'channel_deleted', 'channel': channel, 'revision': value['revision']})
            return {'ok': True, 'revision': value['revision'], 'channel': channel,
                    'state': value['channels'][channel], 'op': 'delete'}
