"""Configured channel policy. Serialize lifecycle decisions with publication."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import time

from channel_lifecycle import (ChannelConflict, ChannelInactive, ChannelUnavailable,
                               _name, _request_id)
from dispatch_queue import ACTIVE
from session_engine import PROJECTION_REPAIR_STATES


_LIVE_REVIEW = {'active', 'waiting', 'paused', 'awaiting_input', 'stalled', 'retrying',
                'interrupted', 'prepared'}
_OPS = {'create', 'archive', 'reopen', 'delete', 'rename', 'cancel_queued', 'recover_projections'}


class ChannelService:
    def __init__(self, catalog, *, engine, messages, jobs, schedules, summaries,
                 queue, settings, save_settings, migrate_cursors, router,
                 migrate_last_active):
        self.catalog, self.engine, self.messages = catalog, engine, messages
        self.jobs, self.schedules, self.summaries = jobs, schedules, summaries
        self.queue, self.settings = queue, settings
        self._save_settings, self._migrate_cursors = save_settings, migrate_cursors
        self.router, self._migrate_last_active = router, migrate_last_active
        self._callbacks = []
        self._unregistered = set(settings.get('unregistered_channels', []))
        with self._boundary():
            value = catalog.snapshot()
            self._unregistered.update(name for name in settings.get('channels', [])
                                      if name not in value['channels'] and name not in value['retired'])
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
        messages = deepcopy(self.messages.get_recent(count=2**63, channel=channel))
        ids = {item['id'] for item in messages}
        todos = {key: value for key, value in self.messages.get_todos().items() if key in ids}
        jobs = self.jobs.lifecycle_scope(channel)
        schedules = deepcopy([item for item in self.schedules.list_all() if item.get('channel') == channel])
        runs = self.engine._store.list_all(channel=channel)
        summary = deepcopy(self.summaries.get(channel))
        transport = self.queue.records(channel)
        counts = dict(messages=len(messages), todos=len(todos), jobs=len(jobs),
                      schedules=len(schedules), sessions=len(runs), summaries=int(summary is not None))
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
                  'max_id': max(ids, default=-1), 'todos': sorted(todos),
                  'jobs': sorted((item['id'], item.get('updated_at')) for item in jobs),
                  'schedules': sorted((item['id'], item.get('next_run'), item.get('active')) for item in schedules),
                  'summary': [summary.get('uid'), summary.get('updated_at')] if summary else None,
                  'sessions': [(item['id'], item.get('state'), item.get('channel_updated_at', item.get('updated_at')))
                               for item in sorted(runs, key=lambda item: item['id'])],
                  'transport': sorted((item['envelope']['dispatch_id'], item['state']) for item in transport),
                  'blockers': blockers}
        queued = sorted(item['envelope']['dispatch_id'] for item in transport if item['state'] == 'queued')
        return counts, blockers, queued, overdue, stable

    def catalog_view(self):
        with self._boundary():
            value = self.catalog.snapshot()
            rows = []
            for name, state in value['channels'].items():
                counts, _, _, overdue, _ = self._scope(name)
                rows.append({'name': name, 'state': state, 'counts': counts, 'overdue_schedules': overdue})
            rows.extend({'name': name, 'state': 'unregistered', 'counts': None, 'overdue_schedules': 0}
                        for name in sorted(self._unregistered))
            return {'revision': value['revision'], 'channels': rows, 'intent': value['intent']}

    @staticmethod
    def _action(value, op, channel, new_name):
        _name(channel)
        if type(op) is not str or op not in _OPS:
            raise ValueError('Choose a supported channel action.')
        if op == 'rename':
            _name(new_name)
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
            self._action(value, op, channel, new_name)
            counts, blockers, queued, overdue, stable = self._scope(channel)
            token = hashlib.sha256(json.dumps([op, channel, new_name, value['revision'], stable],
                sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
            return {'op': op, 'channel': channel, 'new_name': new_name, 'revision': value['revision'],
                    'state': value['channels'].get(channel), 'counts': counts, 'blockers': blockers,
                    'queued_dispatch_ids': queued, 'overdue_schedules': overdue, 'preview_token': token}

    def apply(self, op, channel, *, new_name=None, request_id, confirmation, preview_token):
        _request_id(request_id)
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

    def retry(self, request_id):
        _request_id(request_id)
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
