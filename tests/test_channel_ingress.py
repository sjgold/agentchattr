"""Configured publication/coordinator seams, without HTTP or worker claims."""
import asyncio
import json
import threading
import unittest
from unittest.mock import AsyncMock, Mock, patch

import app
from channel_lifecycle import ChannelStore, ChannelInactive, ChannelUnavailable
from channel_service import ChannelService
from dispatch_queue import QueueStore
from schedules import ScheduleStore
from summaries import SummaryStore
from tests import test_operator_ingress as fixture


class ChannelIngressTests(unittest.TestCase):
    def setUp(self):
        fixture.OperatorIngressTests.setUp(self)
        catalog = ChannelStore(self.root / 'channels.json')
        catalog.initialize(['general', 'review', 'peer'])
        self.channel_service = ChannelService(catalog, engine=self.engine, messages=self.messages,
            jobs=self.jobs, schedules=ScheduleStore(str(self.root / 'schedules.json')),
            summaries=SummaryStore(str(self.root / 'summaries.json')), queue=self.trigger.queue,
            settings={'channels': ['general', 'review', 'peer']}, save_settings=Mock(),
            migrate_cursors=Mock(), router=self.router, migrate_last_active=Mock())
        self.patches.enter_context(patch.object(app, 'channel_service', self.channel_service, create=True))
        for name, value in {'schedules': self.channel_service.schedules, 'summaries': self.channel_service.summaries,
                            'room_settings': self.channel_service.settings,
                            'config': {'server': {'data_dir': str(self.root)}}}.items():
            self.patches.enter_context(patch.object(app, name, value))

    def test_archived_operator_publication_is_refused_before_history_or_queue_changes(self):
        self.channel_service.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.trigger.queue.path.read_bytes()
        with self.assertRaises(ChannelInactive):
            app._publish_operator_message(sender='operator', text='@claude exact',
                                          selected_recipients=[], channel='review')
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)

    def test_configured_claim_holds_archived_and_unknown_targets_but_claims_peer(self):
        # Pre-existing ledger from before lifecycle enforcement was configured.
        legacy = QueueStore(self.root)
        legacy.enqueue(self.peer, {'channel': 'review', 'text': 'hold'})
        legacy.enqueue(self.peer, {'channel': 'unregistered', 'text': 'hold too'})
        peer = legacy.enqueue(self.peer, {'channel': 'peer', 'text': 'claim'})
        self.channel_service.catalog.set_state('review', 'archived', expected_revision=0)
        self.trigger.queue.bind_channel_policy(lambda: self.channel_service)
        claimed = self.trigger.queue.claim(self.peer, 'worker')
        self.assertEqual(claimed['envelope']['dispatch_id'], peer['envelope']['dispatch_id'])
        self.assertEqual([item['state'] for item in self.trigger.queue.records() if
                         item['envelope']['target_identity_id'] == self.peer['identity_id']],
                         ['queued', 'queued', 'dispatched'])
        with self.assertRaises(ChannelInactive):
            self.trigger.queue.enqueue(self.peer, {'channel': 'unregistered', 'text': 'new refusal'})

    def test_resolved_audience_is_enqueued_before_publish_returns_and_callback_deduplicates(self):
        before = len(self.trigger.queue.records('review'))
        message = app._publish_operator_message(sender='operator', text='@claude exact',
                                              selected_recipients=[], channel='review')
        queued = self.trigger.queue.records('review')
        self.assertEqual(len(queued), before + 1)
        receipt = message['metadata']['recipient_routing']
        self.assertEqual(queued[-1]['envelope']['target_identity_id'], receipt['recipients'][0]['identity_id'])
        asyncio.run(app._dispatch_operator_audience(message))
        self.assertEqual(len(self.trigger.queue.records('review')), before + 1)

    def test_explicit_runtime_initializer_projects_and_binds_claim_policy(self):
        app._initialize_channel_lifecycle(self.root)
        app.channel_service.catalog.set_state('review', 'archived', expected_revision=0)
        held = self.trigger.queue.enqueue  # configured enqueue must refuse before a write
        before = self.trigger.queue.path.read_bytes()
        with self.assertRaises(ChannelInactive):
            held(self.peer, {'channel': 'review', 'text': 'must not enqueue'})
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)

    def test_invalid_catalog_initializer_leaves_queue_closed_without_settings_reseed(self):
        active = self.trigger.queue.claim(self.owner, 'worker')
        path = self.root / 'channel_lifecycle.json'
        path.write_text('{invalid', encoding='utf-8')
        with self.assertRaises(ChannelUnavailable):
            app._initialize_channel_lifecycle(self.root)
        before = self.trigger.queue.path.read_bytes()
        with self.assertRaises(ChannelUnavailable):
            self.trigger.queue.claim(self.owner, 'worker')
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        self.assertEqual(path.read_text(encoding='utf-8'), '{invalid')
        # Fail-closed claim includes owner polls, but settlement still works.
        released = self.trigger.queue.release(self.owner, active['envelope']['dispatch_id'], 'worker')
        self.assertEqual(released['state'], 'released')

    def test_actual_preview_handler_maps_inactive_and_unreadable_catalog_cleanly(self):
        request = Mock()
        request.state.auth_origin = 'operator'
        request.body = AsyncMock(return_value=json.dumps({'text': 'shared', 'selected_recipients': [],
                                                         'channel': 'review'}).encode('utf-8'))
        self.channel_service.catalog.set_state('review', 'archived', expected_revision=0)
        self.assertEqual(asyncio.run(app.preview_recipients(request)).status_code, 409)
        self.channel_service.catalog.path.write_text('{invalid', encoding='utf-8')
        self.assertEqual(asyncio.run(app.preview_recipients(request)).status_code, 503)

    def test_one_target_policy_failure_keeps_saved_content_emit_and_other_target(self):
        real = self.trigger.trigger_identity_sync
        emitted = []
        self.messages.on_message(emitted.append)
        def fail_one(identity, **kwargs):
            if identity == self.owner['identity_id']:
                raise ChannelUnavailable('injected target policy failure')
            return real(identity, **kwargs)
        with patch.object(self.trigger, 'trigger_identity_sync', side_effect=fail_one):
            message = app._publish_operator_message(sender='operator', text='@codex @claude exact',
                                                  selected_recipients=[], channel='review')
        self.assertEqual(len(emitted), 1)
        self.assertEqual(self.messages.get_snapshot(message['id']), message)
        self.assertEqual([record['envelope']['target_identity_id'] for record in self.trigger.queue.records('review')],
                         [self.peer['identity_id']])

    def test_async_publication_keeps_loop_responsive_and_emits_on_caller_thread(self):
        entered, release = threading.Event(), threading.Event()
        real = app._dispatch_operator_audience_sync
        emitted_threads = []
        self.messages.on_message(lambda message: emitted_threads.append(threading.get_ident()))
        def slow_queue(*args, **kwargs):
            entered.set()
            if not release.wait(2):
                raise AssertionError('Queue test gate timed out')
            return real(*args, **kwargs)
        async def exercise():
            caller = threading.get_ident()
            with patch.object(app, '_dispatch_operator_audience_sync', side_effect=slow_queue):
                task = asyncio.create_task(app._publish_operator_message_async(sender='operator',
                    text='@claude exact', selected_recipients=[], channel='review'))
                try:
                    for _ in range(100):
                        if entered.is_set():
                            break
                        await asyncio.sleep(.005)
                    self.assertTrue(entered.is_set())
                    self.assertFalse(task.done())
                    self.assertEqual(emitted_threads, [])
                finally:
                    release.set()
                await asyncio.wait_for(task, 2)
            self.assertEqual(emitted_threads, [caller])
        asyncio.run(exercise())


if __name__ == '__main__':
    unittest.main()
