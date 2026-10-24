"""Pure channel catalog contracts; temporary JSON only, no configured runtime claims."""
import importlib
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid


RENAME_STEPS = ('messages', 'jobs', 'schedules', 'summaries', 'sessions', 'cursors', 'settings')
DELETE_STEPS = ('todos', 'messages', 'settings')


class ChannelLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.channels = importlib.import_module('channel_lifecycle')
        scratch = Path(__file__).resolve().parents[1] / '.audit-tmp'
        temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'channel_lifecycle.json'
        self.store = self.channels.ChannelStore(self.path)

    def rename(self, old, new):
        request = uuid.uuid4().hex
        self.store.begin('rename', old, new, request_id=request,
                         expected_revision=self.store.snapshot()['revision'])
        for step in RENAME_STEPS:
            self.store.complete_step(request, step)
        return self.store.finish(request)

    def test_explicit_initialization_archive_and_reload_preserve_catalog(self):
        self.assertFalse(self.path.exists())
        initial = self.store.initialize(['general', 'review'])
        self.assertEqual(initial, {'version': 1, 'revision': 0,
            'channels': {'general': 'active', 'review': 'active'}, 'retired': {}, 'intent': None})
        archived = self.store.set_state('review', 'archived', expected_revision=initial['revision'])
        self.assertEqual(archived['channels']['review'], 'archived')
        self.assertEqual(archived['revision'], initial['revision'] + 1)
        self.assertEqual(self.channels.ChannelStore(self.path).snapshot(), archived)

    def test_ordered_rename_can_consume_own_alias_but_never_other_owner_alias(self):
        self.store.initialize(['general', 'a', 'c'])
        first = self.rename('a', 'b')
        self.assertEqual(first['retired'], {'a': 'b'})
        restored = self.rename('b', 'a')
        self.assertEqual(restored['retired'], {'b': 'a'})
        self.assertEqual(restored['channels'], {'general': 'active', 'a': 'active', 'c': 'active'})
        before = self.path.read_bytes()
        with self.assertRaises(self.channels.ChannelConflict):
            self.store.begin('rename', 'c', 'b', request_id=uuid.uuid4().hex,
                             expected_revision=restored['revision'])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.snapshot(), restored)

    def test_missing_requires_explicit_initialize_and_existing_catalog_never_reseeds(self):
        for read in (self.store.snapshot, self.store.blocked_names, lambda: self.store.require_active('general')):
            with self.assertRaises(self.channels.ChannelUnavailable):
                read()
        self.assertFalse(self.path.exists())
        initial = self.store.initialize(['review'])
        self.assertEqual(initial['channels'], {'general': 'active', 'review': 'active'})
        before = self.path.read_bytes()
        self.assertEqual(self.store.initialize(['new-seed']), initial)
        self.assertEqual(self.path.read_bytes(), before)
        self.path.write_text('{corrupt', encoding='utf-8')
        before = self.path.read_bytes()
        for call in (lambda: self.channels.ChannelStore(self.path), lambda: self.store.initialize(['new-seed'])):
            with self.assertRaises(self.channels.ChannelUnavailable) as caught:
                call()
            self.assertNotIn(str(self.path), str(caught.exception))
            self.assertEqual(self.path.read_bytes(), before)

    def test_strict_catalog_schema_rejects_corruption_without_reset_or_rewrite(self):
        valid = self.store.initialize(['general', 'a'])
        invalid = [[], None, {}, {**valid, 'version': True}, {**valid, 'version': 2},
                   {**valid, 'revision': True}, {**valid, 'revision': -1}, {**valid, 'revision': 1.0},
                   {**valid, 'extra': True}, {**valid, 'channels': {'general': 'archived'}},
                   {**valid, 'channels': {'a': 'active'}}, {**valid, 'channels': {'general': 'active', 'Bad': 'active'}},
                   {**valid, 'channels': {'general': 'active', 'a': 'unknown'}},
                   {**valid, 'channels': {'general': 'active', 'a': True}},
                   {**valid, 'retired': {'old': 'missing'}}, {**valid, 'retired': {'a': 'a'}},
                   {**valid, 'retired': {'general': 'a'}}, {**valid, 'retired': {'old': 'other', 'other': 'old'}},
                   {**valid, 'retired': {'old': 1}}, {**valid, 'retired': {'Bad': 'a'}},
                   {**valid, 'intent': {}}, {**valid, 'intent': {'request_id': True, 'op': 'rename', 'old': 'a', 'new': 'b', 'completed_steps': []}},
                   {**valid, 'intent': {'request_id': 'a'*32, 'op': 'rename', 'old': 'a', 'new': 'b', 'completed_steps': ['jobs']}}]
        for field in valid:
            missing = deepcopy(valid); del missing[field]; invalid.append(missing)
        for value in invalid:
            self.path.write_text(json.dumps(value), encoding='utf-8')
            before = self.path.read_bytes()
            with self.subTest(value=value), self.assertRaises(self.channels.ChannelUnavailable):
                self.channels.ChannelStore(self.path)
            self.assertEqual(self.path.read_bytes(), before)

    def test_strict_names_revisions_transitions_and_general_protection(self):
        current = self.store.initialize(['a'])
        for name in ('', 'Upper', '../a', 'a b', 'a_b', 'x'*21, True, None, 7):
            before = self.path.read_bytes()
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.store.create(name, expected_revision=current['revision'])
            self.assertEqual(self.path.read_bytes(), before)
        for revision in (True, False, '0', 0.0, None, -1):
            before = self.path.read_bytes()
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                self.store.create('new', expected_revision=revision)
            self.assertEqual(self.path.read_bytes(), before)
        archived = self.store.set_state('a', 'archived', expected_revision=current['revision'])
        with self.assertRaises(self.channels.ChannelConflict):
            self.store.create('new', expected_revision=current['revision'])
        for name, state in (('a', 'archived'), ('a', 'retired'), ('a', 'unknown'), ('general', 'archived')):
            before = self.path.read_bytes()
            with self.subTest(name=name, state=state), self.assertRaises(ValueError):
                self.store.set_state(name, state, expected_revision=archived['revision'])
            self.assertEqual(self.path.read_bytes(), before)
        for op, new in (('rename', 'new-general'), ('delete', None)):
            with self.assertRaises(ValueError):
                self.store.begin(op, 'general', new, request_id=uuid.uuid4().hex, expected_revision=archived['revision'])
        restored = self.store.set_state('a', 'active', expected_revision=archived['revision'])
        self.assertEqual(restored['revision'], archived['revision'] + 1)

    def test_create_and_rename_reservations_preserve_direct_alias_ownership(self):
        self.store.initialize(['a', 'x'])
        self.rename('a', 'b'); self.rename('b', 'c')
        current = self.rename('c', 'b')
        self.assertEqual(current['retired'], {'a': 'b', 'c': 'b'})
        for name in ('a', 'b', 'c'):
            before = self.path.read_bytes()
            with self.subTest(name=name), self.assertRaises(self.channels.ChannelConflict):
                self.store.create(name, expected_revision=current['revision'])
            self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(self.channels.ChannelConflict):
            self.store.begin('rename', 'x', 'a', request_id=uuid.uuid4().hex, expected_revision=current['revision'])
        fresh = self.store.create('fresh', expected_revision=current['revision'])
        self.assertEqual(fresh['channels']['fresh'], 'active')
        self.assertEqual(fresh['revision'], current['revision'] + 1)

    def test_delete_retains_retired_row_and_aliases_without_reopen_or_rename(self):
        self.store.initialize(['a'])
        before = self.rename('a', 'b')
        request = uuid.uuid4().hex
        self.store.begin('delete', 'b', None, request_id=request, expected_revision=before['revision'])
        for step in DELETE_STEPS:
            self.store.complete_step(request, step)
        retired = self.store.finish(request)
        self.assertEqual(retired['channels']['b'], 'retired')
        self.assertEqual(retired['retired'], {'a': 'b'})
        self.assertEqual(self.channels.ChannelStore(self.path).snapshot(), retired)
        for call in (lambda: self.store.set_state('b', 'active', expected_revision=retired['revision']),
                     lambda: self.store.begin('rename', 'b', 'c', request_id=uuid.uuid4().hex, expected_revision=retired['revision']),
                     lambda: self.store.create('a', expected_revision=retired['revision'])):
            before_bytes = self.path.read_bytes()
            with self.assertRaises(ValueError):
                call()
            self.assertEqual(self.path.read_bytes(), before_bytes)

    def test_pending_intent_steps_are_ordered_replayable_and_single_intent(self):
        initial = self.store.initialize(['a', 'peer'])
        request = uuid.uuid4().hex
        pending = self.store.begin('rename', 'a', 'b', request_id=request, expected_revision=initial['revision'])
        self.assertEqual(pending['intent'], {'request_id': request, 'op': 'rename', 'old': 'a', 'new': 'b', 'completed_steps': []})
        before = self.path.read_bytes()
        self.assertEqual(self.store.begin('rename', 'a', 'b', request_id=request, expected_revision=initial['revision']), pending)
        self.assertEqual(self.path.read_bytes(), before)
        for call in (lambda: self.store.finish(request), lambda: self.store.complete_step(request, 'jobs'),
                     lambda: self.store.complete_step(request, 'unknown'),
                     lambda: self.store.begin('rename', 'a', 'c', request_id=request, expected_revision=pending['revision']),
                     lambda: self.store.begin('rename', 'a', 'b', request_id=uuid.uuid4().hex, expected_revision=pending['revision']),
                     lambda: self.store.create('unrelated', expected_revision=pending['revision'])):
            with self.assertRaises(ValueError):
                call()
            self.assertEqual(self.path.read_bytes(), before)
        first = self.store.complete_step(request, 'messages')
        self.assertEqual(first['revision'], pending['revision'] + 1)
        before = self.path.read_bytes()
        self.assertEqual(self.store.complete_step(request, 'messages'), first)
        self.assertEqual(self.path.read_bytes(), before)
        reloaded = self.channels.ChannelStore(self.path)
        self.assertEqual(reloaded.begin('rename', 'a', 'b', request_id=request, expected_revision=initial['revision']), first)
        for step in RENAME_STEPS[1:]:
            reloaded.complete_step(request, step)
        completed = reloaded.finish(request)
        self.assertIsNone(completed['intent'])
        self.assertEqual(completed['revision'], initial['revision'] + 1 + len(RENAME_STEPS) + 1)
        with self.assertRaises(self.channels.ChannelConflict):
            reloaded.finish(request)

    def test_blocked_names_include_inactive_alias_and_both_pending_names_only(self):
        self.store.initialize(['a', 'archived', 'x'])
        current = self.rename('x', 'peer')
        current = self.store.set_state('archived', 'archived', expected_revision=current['revision'])
        request = uuid.uuid4().hex
        self.store.begin('rename', 'a', 'b', request_id=request, expected_revision=current['revision'])
        self.assertEqual(self.store.blocked_names(), {'archived', 'x', 'a', 'b'})
        for name in ('archived', 'x', 'a', 'b', 'missing'):
            with self.subTest(name=name), self.assertRaises(self.channels.ChannelInactive):
                self.store.require_active(name)
        self.assertIsNone(self.store.require_active('general'))
        self.assertIsNone(self.store.require_active('peer'))
        before = self.path.read_bytes()
        blocked = self.store.blocked_names(); blocked.add('peer')
        self.assertEqual(self.store.blocked_names(), {'archived', 'x', 'a', 'b'})
        self.assertEqual(self.path.read_bytes(), before)

    def test_atomic_writer_failure_preserves_disk_memory_revision_and_missing_initial_state(self):
        initial = self.store.initialize(['a'])
        def refuses(call):
            before, snapshot = self.path.read_bytes(), self.store.snapshot()
            with patch('channel_lifecycle.atomic_json', side_effect=OSError('private raw path must not escape')):
                with self.assertRaises(self.channels.ChannelUnavailable) as caught:
                    call()
            self.assertNotIn('private raw path', str(caught.exception))
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(self.store.snapshot(), snapshot)
            self.assertEqual(self.channels.ChannelStore(self.path).snapshot(), snapshot)
        refuses(lambda: self.store.create('new', expected_revision=initial['revision']))
        refuses(lambda: self.store.set_state('a', 'archived', expected_revision=initial['revision']))
        request = uuid.uuid4().hex
        refuses(lambda: self.store.begin('rename', 'a', 'b', request_id=request, expected_revision=initial['revision']))
        self.store.begin('rename', 'a', 'b', request_id=request, expected_revision=initial['revision'])
        refuses(lambda: self.store.complete_step(request, 'messages'))
        for step in RENAME_STEPS:
            self.store.complete_step(request, step)
        refuses(lambda: self.store.finish(request))
        self.assertEqual(self.store.finish(request)['channels']['b'], 'active')
        missing_path = self.path.with_name('missing.json')
        missing = self.channels.ChannelStore(missing_path)
        with patch('channel_lifecycle.atomic_json', side_effect=OSError('bounded write fault')):
            with self.assertRaises(self.channels.ChannelUnavailable):
                missing.initialize(['a'])
        self.assertFalse(missing_path.exists())
        with self.assertRaises(self.channels.ChannelUnavailable):
            missing.snapshot()

    def test_cross_instance_competing_revision_has_exactly_one_durable_winner(self):
        initial = self.store.initialize(['a'])
        stores = [self.channels.ChannelStore(self.path) for _ in range(4)]
        def create(index):
            try:
                stores[index].create('new-' + str(index), expected_revision=initial['revision'])
                return 'created'
            except self.channels.ChannelConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(create, range(4)))
        self.assertEqual(outcomes.count('created'), 1)
        self.assertEqual(outcomes.count('conflict'), 3)
        final = self.channels.ChannelStore(self.path).snapshot()
        self.assertEqual(final['revision'], initial['revision'] + 1)
        self.assertEqual(len(final['channels']), len(initial['channels']) + 1)

    def test_detached_catalog_and_pending_results_never_alias_or_write_on_read(self):
        names = ['a']
        initial = self.store.initialize(names)
        names.append('caller-name')
        initial['channels']['a'] = 'retired'
        self.assertEqual(self.store.snapshot()['channels'], {'general': 'active', 'a': 'active'})
        request = uuid.uuid4().hex
        result = self.store.begin('rename', 'a', 'b', request_id=request, expected_revision=self.store.snapshot()['revision'])
        before = self.path.read_bytes()
        result['intent']['completed_steps'].append('settings')
        result['retired']['forged'] = 'a'
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['intent']['completed_steps'], [])
        self.assertEqual(snapshot['retired'], {})
        snapshot['intent']['new'] = 'caller-edit'
        self.assertEqual(self.store.snapshot()['intent']['new'], 'b')
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
