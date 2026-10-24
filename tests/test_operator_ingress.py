"""Private central-ingress and durable queue units, without HTTP or native claims."""

import asyncio
from copy import deepcopy
from contextlib import ExitStack
import unittest
from unittest.mock import Mock, patch
import uuid

import app
import mcp_bridge
from dispatch_queue import QueueConflict
from jobs import JobStore
from router import Router
from tests import test_session_events as fixture


class OperatorIngressTests(unittest.TestCase):
    def setUp(self):
        fixture.SessionEventTests.setUp(self)
        self.jobs = JobStore(str(self.root / 'jobs.json'))
        self.router = Router(['codex', 'claude'])
        self.patches = self.enterContext(ExitStack())
        for name, value in {'store': self.messages, 'jobs': self.jobs,
                            'registry': self.registry, 'agents': self.trigger,
                            'router': self.router, 'session_engine': self.engine,
                            'session_store': self.sessions}.items():
            self.patches.enter_context(patch.object(app, name, value, create=True))
        self.patches.enter_context(patch.object(mcp_bridge, 'is_online', return_value=True))

    def test_central_publication_keeps_raw_text_and_explicit_over_selection(self):
        message = app._publish_operator_message(sender='operator', text='@codex café\r\nraw',
            selected_recipients=['claude'], channel='general')
        self.assertEqual(message['text'], '@codex café\r\nraw')
        receipt = message['metadata']['recipient_routing']
        self.assertEqual(receipt['mode'], 'explicit')
        self.assertEqual(receipt['recipients'][0]['identity_id'], self.owner['identity_id'])
        self.assertEqual(len(receipt['recipients']), 1)
        self.assertEqual(receipt['message_uid'], message['uid'])

    def test_identity_trigger_targets_immutable_identity_with_exact_dispatch(self):
        dispatch = uuid.uuid4().hex
        record = self.trigger.trigger_identity_sync(self.peer['identity_id'], dispatch_id=dispatch,
            message='operator: Exact café\r\ntext', channel='general', job_id=7)
        self.assertEqual(record['envelope']['dispatch_id'], dispatch)
        self.assertEqual(record['envelope']['target_identity_id'], self.peer['identity_id'])
        self.assertEqual(record['envelope']['job_id'], 7)

    def publish(self, text='@claude raw', **changes):
        return app._publish_operator_message(**{
            'sender': 'operator', 'text': text, 'selected_recipients': [], 'channel': 'general', **changes})

    def dispatch(self, message, **kwargs):
        asyncio.run(app._dispatch_operator_audience(message, **kwargs))

    def dispatch_id(self, message, identity):
        return uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:recipient:' + message['uid'] + ':' + identity).hex

    def audience_records(self, identity):
        instance = self.registry.get_instance(identity) if isinstance(identity, str) else identity
        return self.trigger.queue.for_identity(instance)

    def test_unknown_none_ignored_addresses_and_attachment_names_never_broaden(self):
        for text, selected, mode in [('@unknown', ['codex'], 'explicit'), ('shared', [], 'none')]:
            with self.subTest(text=text):
                message = self.publish(text, selected_recipients=selected,
                    attachments=[{'name': '@all.txt', 'path': '@claude', 'text': '@codex'}])
                receipt = message['metadata']['recipient_routing']
                self.assertEqual(receipt['mode'], mode)
                self.assertEqual(receipt['recipients'], [])
                before = self.trigger.queue.path.read_bytes()
                self.dispatch(message)
                self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        message = self.publish('"@codex" `@all`', selected_recipients=['claude'])
        self.assertEqual([x['identity_id'] for x in message['metadata']['recipient_routing']['recipients']], [self.peer['identity_id']])

    def test_actual_central_order_is_persist_then_explicit_channel_reset_then_emit(self):
        order = []
        def reset(channel):
            self.assertEqual(channel, 'review')
            message = self.messages.get_recent(1)[0]
            self.assertIn('recipient_routing', message['metadata'])
            self.assertEqual(self.messages.get_snapshot(message['id']), message)
            order.append('reset')
        self.messages.on_message(lambda message: order.append('emit'))
        real_publish = self.messages._publish_operator
        def persisted(*args, **kwargs):
            result = real_publish(*args, **kwargs)
            order.append('persist')
            return result
        with patch.object(self.messages, '_publish_operator', side_effect=persisted), \
             patch.object(self.router, 'continue_routing', side_effect=reset):
            self.publish('@claude café\r\nraw', channel='review')
        self.assertEqual(order, ['persist', 'reset', 'emit'])

    def test_io_failure_has_no_reset_callback_or_queue_effect(self):
        before = self.messages._path.read_bytes() if self.messages._path.exists() else None
        ledger = self.trigger.queue.path.read_bytes()
        callback = Mock()
        self.messages.on_message(callback)
        with patch('store.os.fsync', side_effect=OSError('bounded publication fault')), \
             patch.object(self.router, 'continue_routing') as reset, self.assertRaises(OSError):
            self.publish()
        reset.assert_not_called()
        callback.assert_not_called()
        self.assertEqual(self.messages._path.read_bytes() if self.messages._path.exists() else None, before)
        self.assertEqual(self.trigger.queue.path.read_bytes(), ledger)

    def test_wait_annotation_is_identity_based_and_operator_name_collision_stays_operator(self):
        message = self.publish('@codex', sender=self.peer['name'])
        receipt = message['metadata']['recipient_routing']
        self.assertEqual(receipt['origin'], 'operator')
        self.assertEqual(receipt['waiting'], [{'identity_id': self.owner['identity_id'], 'reason': 'earlier_review_turn'}])
        self.dispatch(message)
        record = self.trigger.queue.owned(self.owner, self.dispatch_id(message, self.owner['identity_id']))
        self.assertEqual(record['state'], 'queued')
        self.assertEqual(self.trigger.queue.claim(self.owner, 'worker')['envelope']['dispatch_id'], self.started['active_invocation']['dispatch_id'])
        free = self.publish('@claude')
        self.assertEqual(free['metadata']['recipient_routing']['waiting'], [])

    def test_dispatch_reload_ignores_callback_forgery_and_repeated_callback_is_idempotent(self):
        message = self.publish('@claude Exact café\r\ntext')
        forged = deepcopy(message)
        forged['text'] = '@codex forged'
        forged['metadata']['recipient_routing']['recipients'] = [
            {'name': 'codex', 'identity_id': self.owner['identity_id'], 'online': True}]
        self.dispatch(forged)
        dispatch_id = self.dispatch_id(message, self.peer['identity_id'])
        record = self.trigger.queue.owned(self.peer, dispatch_id)
        self.assertIn(message['text'], record['envelope'].get('prompt', '') + record['envelope'].get('text', ''))
        before = self.trigger.queue.path.read_bytes()
        self.dispatch(message)
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        self.dispatch({**message, 'uid': 'wrong-uid'})
        generic = self.messages.add('operator', '@all generic')
        self.dispatch(generic)
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)

    def test_identity_rename_preserved_but_removed_identity_not_replaced_by_same_name(self):
        message = self.publish('@claude')
        renamed = self.registry.rename(self.peer['name'], 'claude-renamed')
        self.assertIsInstance(renamed, dict)
        self.dispatch(message)
        record = self.trigger.queue.owned(renamed, self.dispatch_id(message, self.peer['identity_id']))
        self.assertEqual(record['envelope']['target_agent_name'], renamed['name'])
        second = self.publish('@codex')
        self.registry.deregister(self.owner['name'])
        replacement = self.registry.register('codex')
        self.assertNotEqual(replacement['identity_id'], self.owner['identity_id'])
        before = self.trigger.queue.path.read_bytes()
        self.dispatch(second)
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        self.assertEqual(self.trigger.queue.for_identity(replacement), [])

    def test_clear_numeric_id_reuse_derives_distinct_uid_dispatches(self):
        from store import MessageStore
        self.messages.clear()
        initial = MessageStore(str(self.messages._path))
        with patch.object(app, 'store', initial):
            first = self.publish('@claude')
            self.dispatch(first)
        initial.clear()
        # A real reload restarts numeric ids from the empty history, without reusing UIDs.
        reloaded = MessageStore(str(self.messages._path))
        with patch.object(app, 'store', reloaded):
            second = self.publish('@claude')
            self.dispatch(second)
        self.assertEqual((first['id'], second['id']), (0, 0))
        self.assertNotEqual(first['uid'], second['uid'])
        ids = {r['envelope']['dispatch_id'] for r in self.trigger.queue.for_identity(self.peer)}
        self.assertIn(self.dispatch_id(first, self.peer['identity_id']), ids)
        self.assertIn(self.dispatch_id(second, self.peer['identity_id']), ids)

    def test_per_target_queue_conflict_does_not_abort_other_targets(self):
        message = self.publish('@codex @claude')
        real_trigger = self.trigger.trigger_identity_sync
        def targeted(identity, **kwargs):
            if identity == self.owner['identity_id']:
                raise QueueConflict('bounded first recipient failure')
            return real_trigger(identity, **kwargs)
        with patch.object(self.trigger, 'trigger_identity_sync', side_effect=targeted):
            self.dispatch(message)
        self.assertIsNotNone(self.trigger.queue.owned(self.peer, self.dispatch_id(message, self.peer['identity_id'])))
        self.assertEqual(len(message['metadata']['recipient_routing']['recipients']), 2)

    def test_operator_job_private_publication_uses_stored_channel_and_saved_snapshot(self):
        job = self.jobs.create('Review', 'task', 'review', 'operator')
        observed = []
        self.jobs.on_change(lambda action, value: observed.append(action))
        with patch.object(self.router, 'continue_routing', wraps=self.router.continue_routing) as reset:
            message = self.publish('@claude café\r\nraw', job_id=job['id'], channel='review', msg_type='suggestion')
        reset.assert_called_once_with('review')
        self.assertEqual(observed, ['message'])
        self.assertEqual(self.jobs.get_message_snapshot(job['id'], message['id']), message)
        self.dispatch(message, job_id=job['id'])
        record = self.trigger.queue.owned(self.peer, self.dispatch_id(message, self.peer['identity_id']))
        self.assertEqual(record['envelope']['channel'], 'review')
        self.assertEqual(record['envelope']['job_id'], job['id'])

    def test_internal_approved_targets_and_slash_original_audience_only(self):
        for origin in ('workflow', 'schedule'):
            message = self.publish('@codex source instruction', selected_recipients=['codex'],
                approved_targets=['claude'], origin=origin)
            receipt = message['metadata']['recipient_routing']
            self.assertEqual(receipt['origin'], origin)
            self.assertEqual([r['identity_id'] for r in receipt['recipients']], [self.peer['identity_id']])
        for command in ('/roastreview', '/artchallenge', '/hatmaking', '/poetry'):
            message = self.publish('@claude ' + command + ' source @unknown')
            self.assertNotEqual(message['text'], '@claude ' + command + ' source @unknown')
            self.assertEqual([r['identity_id'] for r in message['metadata']['recipient_routing']['recipients']], [self.peer['identity_id']])
            unaddressed = self.publish(command + ' source')
            self.assertEqual(unaddressed['metadata']['recipient_routing']['recipients'], [])
        for text in ('"/poetry @claude"', '`/poetry @claude`'):
            message = self.publish(text)
            self.assertEqual(message['text'], text)
            self.assertEqual(message['metadata']['recipient_routing']['recipients'], [])


if __name__ == '__main__':
    unittest.main()
