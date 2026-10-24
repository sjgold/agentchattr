"""Strict, atomic channel catalog. No application or dispatch side effects."""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import re
import threading
import time

from api_seats import atomic_json
from launcher import LaunchError, startup_lock


RENAME_STEPS = ('messages', 'jobs', 'schedules', 'summaries', 'sessions', 'cursors', 'settings')
DELETE_STEPS = ('todos', 'messages', 'settings')
_FIELDS = {'version', 'revision', 'channels', 'retired', 'intent'}
_INTENT_FIELDS = {'request_id', 'op', 'old', 'new', 'completed_steps'}


class ChannelConflict(ValueError):
    pass


class ChannelInactive(ChannelConflict):
    pass


class ChannelUnavailable(RuntimeError):
    pass


def _name(value):
    if type(value) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,19}', value):
        raise ValueError('Use a channel name of 1-20 lowercase letters, numbers or hyphens.')
    return value


def _revision(value):
    if type(value) is not int or value < 0:
        raise ValueError('Catalog revision must be a nonnegative integer.')


def _request_id(value):
    if type(value) is not str or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise ValueError('A 32-character lowercase hexadecimal request ID is required.')


def _destination(value, old, new):
    if (old == new or new in value['channels']
            or (new in value['retired'] and value['retired'][new] != old)):
        raise ChannelConflict('That channel name is already used or retired by another channel.')


def _validate(value):
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError('Invalid catalog fields.')
    if type(value['version']) is not int or value['version'] != 1:
        raise ValueError('Invalid catalog version.')
    _revision(value['revision'])
    channels, retired = value['channels'], value['retired']
    if type(channels) is not dict or type(retired) is not dict:
        raise ValueError('Invalid channel maps.')
    if channels.get('general') != 'active' or 'general' in retired:
        raise ValueError('General must remain active and protected.')
    for name, state in channels.items():
        _name(name)
        if type(state) is not str or state not in ('active', 'archived', 'retired'):
            raise ValueError('Invalid channel state.')
    for alias, owner in retired.items():
        _name(alias)
        _name(owner)
        if alias in channels or owner not in channels or owner == 'general':
            raise ValueError('Retired names must point directly to their current owner.')
    intent = value['intent']
    if intent is None:
        return
    if type(intent) is not dict or set(intent) != _INTENT_FIELDS:
        raise ValueError('Invalid channel intent fields.')
    _request_id(intent['request_id'])
    old, new, op = intent['old'], intent['new'], intent['op']
    _name(old)
    if old == 'general' or channels.get(old) not in ('active', 'archived'):
        raise ValueError('Invalid channel intent source.')
    if op == 'rename' and type(op) is str:
        _name(new)
        if channels[old] != 'active':
            raise ValueError('An archived channel must be reopened before rename.')
        _destination(value, old, new)
        steps = RENAME_STEPS
    elif op == 'delete' and type(op) is str and new is None:
        steps = DELETE_STEPS
    else:
        raise ValueError('Invalid channel operation.')
    completed = intent['completed_steps']
    if (type(completed) is not list or len(completed) > len(steps)
            or any(type(step) is not str for step in completed)
            or completed != list(steps[:len(completed)])):
        raise ValueError('Invalid channel operation steps.')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate catalog field.')
        result[key] = value
    return result


class ChannelStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._state = None
        # Atomic replacement makes a plain initial read safe. A missing file
        # remains uninitialized; only initialize() may create the catalog.
        self._read(missing_ok=True)

    def _read(self, *, missing_ok=False):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'),
                               object_pairs_hook=_unique_object)
            _validate(value)
        except FileNotFoundError:
            if missing_ok:
                return None
            raise ChannelUnavailable('Channel management is not initialized.') from None
        except (OSError, ValueError, UnicodeError, RecursionError):
            raise ChannelUnavailable('Channel state is unreadable; publication is held.') from None
        self._state = deepcopy(value)
        return value

    @contextmanager
    def _transaction(self, *, missing_ok=False):
        with self._lock:
            try:
                with startup_lock(self.path.with_suffix(self.path.suffix + '.lock'),
                                  time.monotonic() + 10):
                    yield self._read(missing_ok=missing_ok)
            except (OSError, LaunchError):
                raise ChannelUnavailable('Channel state could not be saved; retry management.') from None

    def _write(self, value):
        _validate(value)
        atomic_json(self.path, value)
        self._state = deepcopy(value)
        return deepcopy(value)

    @staticmethod
    def _editable(value, expected_revision):
        _revision(expected_revision)
        if value['intent'] is not None:
            raise ChannelConflict('A channel operation is pending; finish its repair first.')
        if value['revision'] != expected_revision:
            raise ChannelConflict('Channel state changed; refresh the preview.')

    @staticmethod
    def _intent(value, request_id):
        _request_id(request_id)
        intent = value['intent']
        if intent is None or intent['request_id'] != request_id:
            raise ChannelConflict('That channel operation is not pending; refresh management.')
        return intent

    def initialize(self, channel_names):
        with self._transaction(missing_ok=True) as value:
            if value is not None:
                return deepcopy(value)
            if type(channel_names) not in (list, tuple):
                raise ValueError('An explicit list of channel names is required.')
            names = [_name(name) for name in channel_names]
            if len(set(names)) != len(names):
                raise ValueError('Channel names must be unique.')
            return self._write({'version': 1, 'revision': 0,
                'channels': dict.fromkeys(['general', *names], 'active'),
                'retired': {}, 'intent': None})

    def snapshot(self):
        with self._transaction() as value:
            return deepcopy(value)

    def require_active(self, channel):
        _name(channel)
        with self._transaction() as value:
            intent = value['intent']
            if intent and channel in (intent['old'], intent['new']):
                raise ChannelInactive(f'Channel {channel} is held for repair.')
            if channel in value['retired']:
                raise ChannelInactive(f'Channel {channel} is retired; specify an active channel.')
            state = value['channels'].get(channel)
            if state != 'active':
                raise ChannelInactive(f'Channel {channel} is {state or "unregistered"}; specify an active channel.')

    def blocked_names(self):
        with self._transaction() as value:
            names = {name for name, state in value['channels'].items() if state != 'active'}
            names.update(value['retired'])
            if value['intent']:
                names.add(value['intent']['old'])
                if value['intent']['new'] is not None:
                    names.add(value['intent']['new'])
            return names

    def create(self, name, *, expected_revision):
        _name(name)
        with self._transaction() as value:
            self._editable(value, expected_revision)
            if name in value['channels'] or name in value['retired']:
                raise ChannelConflict('That channel name is already used or retired.')
            value['channels'][name] = 'active'
            value['revision'] += 1
            return self._write(value)

    def set_state(self, name, state, *, expected_revision):
        _name(name)
        with self._transaction() as value:
            self._editable(value, expected_revision)
            current = value['channels'].get(name)
            if (name == 'general' or type(state) is not str
                    or (current, state) not in (('active', 'archived'), ('archived', 'active'))):
                raise ChannelConflict('Only active and archived channels can change state; general is protected.')
            value['channels'][name] = state
            value['revision'] += 1
            return self._write(value)

    def begin(self, op, old, new, *, request_id, expected_revision):
        _request_id(request_id)
        _revision(expected_revision)
        _name(old)
        if type(op) is not str or op not in ('rename', 'delete'):
            raise ValueError('Choose rename or delete.')
        if op == 'rename':
            _name(new)
        elif new is not None:
            raise ValueError('Delete has no destination name.')
        with self._transaction() as value:
            requested = {'request_id': request_id, 'op': op, 'old': old, 'new': new, 'completed_steps': []}
            if value['intent']:
                if {**value['intent'], 'completed_steps': []} == requested:
                    return deepcopy(value)
                raise ChannelConflict('Another channel operation or different parameters are pending.')
            self._editable(value, expected_revision)
            if old == 'general' or value['channels'].get(old) not in ('active', 'archived'):
                raise ChannelConflict('Choose an existing non-retired channel; general is protected.')
            if op == 'rename':
                if value['channels'][old] != 'active':
                    raise ChannelConflict('Reopen the channel before renaming it.')
                _destination(value, old, new)
            value['intent'] = requested
            value['revision'] += 1
            return self._write(value)

    def complete_step(self, request_id, step):
        with self._transaction() as value:
            intent = self._intent(value, request_id)
            steps = RENAME_STEPS if intent['op'] == 'rename' else DELETE_STEPS
            if type(step) is not str or step not in steps:
                raise ChannelConflict('Unknown channel operation step.')
            if step in intent['completed_steps']:
                return deepcopy(value)
            if step != steps[len(intent['completed_steps'])]:
                raise ChannelConflict('Complete the channel operation steps in order.')
            intent['completed_steps'].append(step)
            value['revision'] += 1
            return self._write(value)

    def finish(self, request_id):
        with self._transaction() as value:
            intent = self._intent(value, request_id)
            steps = RENAME_STEPS if intent['op'] == 'rename' else DELETE_STEPS
            if intent['completed_steps'] != list(steps):
                raise ChannelConflict('Channel effects are incomplete; repair them before finishing.')
            old, new = intent['old'], intent['new']
            if intent['op'] == 'delete':
                value['channels'][old] = 'retired'
            else:
                value['retired'].pop(new, None)
                value['retired'] = {alias: new if owner == old else owner
                                    for alias, owner in value['retired'].items()}
                value['retired'][old] = new
                value['channels'][new] = value['channels'].pop(old)
            value['intent'] = None
            value['revision'] += 1
            return self._write(value)
