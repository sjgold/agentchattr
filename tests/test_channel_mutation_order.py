"""Worker/lock ordering and choice single-flight, without native delivery claims."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
import uuid
from unittest.mock import patch

import app
from channel_lifecycle import ChannelConflict
from tests import test_channel_message_mutations as fixture


class ChannelMutationOrderTests(unittest.TestCase):
    request = fixture.ChannelMessageMutationTests.request

    def setUp(self):
        fixture.ChannelMessageMutationTests.setUp(self)
        self.registry.seed({'claude': {'label': 'Claude'}})
        self.peer = self.registry.register('claude')

    def decision(self):
        return self.messages.add(self.peer['name'], 'Choose', msg_type='decision', channel='review',
            metadata={'choices': ['Blue', 'Green'], 'resolved': False})

    def test_choice_and_publication_hold_archive_while_worker_keeps_loop_responsive(self):
        card = self.decision()
        entered, release, archive_started = threading.Event(), threading.Event(), threading.Event()
        publish, emit = app._publish_operator_message, self.messages._emit_operator
        emitted = []
        async def run():
            loop_thread = threading.get_ident()
            def gated(**fields):
                self.assertNotEqual(threading.get_ident(), loop_thread)
                self.assertTrue(self.engine._lock._is_owned())
                self.assertTrue(self.catalog._lock._is_owned())
                entered.set()
                self.assertTrue(release.wait(3))
                return publish(**fields)
            def tracked(*args, **kwargs):
                emitted.append(threading.get_ident())
                return emit(*args, **kwargs)
            def archive():
                archive_started.set()
                preview = self.service.preview('archive', 'review')
                try:
                    self.service.apply('archive', 'review', request_id=uuid.uuid4().hex,
                        confirmation='review', preview_token=preview['preview_token'])
                except ChannelConflict:
                    return 'blocked_by_saved_dispatch'
                return 'archived'
            with patch.object(app, '_publish_operator_message', side_effect=gated), \
                 patch.object(self.messages, '_emit_operator', side_effect=tracked):
                response = asyncio.create_task(app.resolve_decision(card['id'], self.request({'choice': 'Blue'})))
                try:
                    self.assertTrue(await asyncio.to_thread(entered.wait, 3))
                    attempt = asyncio.create_task(asyncio.to_thread(archive))
                    self.assertTrue(await asyncio.to_thread(archive_started.wait, 3))
                    await asyncio.sleep(0)
                    self.assertFalse(response.done())
                    self.assertFalse(attempt.done())
                    self.broadcast.assert_not_awaited()
                finally:
                    release.set()
                self.assertEqual(await response, {'ok': True, 'chosen': 'Blue'})
                self.assertEqual(await attempt, 'blocked_by_saved_dispatch')
            self.assertEqual(emitted, [loop_thread])
        asyncio.run(run())
        self.assertEqual(self.catalog.snapshot()['channels']['review'], 'active')
        self.assertEqual(len(self.trigger.queue.records('review')), 1)

    def test_concurrent_choices_publish_exactly_one_reply_without_typed_progress(self):
        card = self.decision()
        before = self.sessions._path.read_bytes() if self.sessions._path.exists() else None
        def choose(choice):
            result = asyncio.run(app.resolve_decision(card['id'], self.request({'choice': choice})))
            return getattr(result, 'status_code', 200)
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(choose, ('Blue', 'Green')))
        self.assertCountEqual(statuses, [200, 400])
        replies = [message for message in self.messages.get_recent(channel='review')
                   if message.get('metadata', {}).get('recipient_routing')]
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]['text'], '@' + self.peer['name'] + ' ' +
                         self.messages.get_snapshot(card['id'])['metadata']['chosen'])
        self.assertEqual(len(self.trigger.queue.records('review')), 1)
        self.assertEqual(self.sessions._path.read_bytes() if self.sessions._path.exists() else None, before)

    def test_active_anchor_zero_is_accepted_and_card_is_updated_once(self):
        card = self.messages.add(self.peer['name'], 'Proposal', msg_type='job_proposal', channel='review',
                                 metadata={'title': 'Task', 'body': 'Source', 'status': 'pending'})
        self.assertEqual(card['id'], 0)
        result = asyncio.run(app.create_job(self.request({'title': 'Task', 'channel': 'review', 'anchor_msg_id': 0})))
        self.assertEqual(result['anchor_msg_id'], 0)
        self.assertEqual(len(self.jobs.list_all()), 1)
        self.assertEqual(self.messages.get_snapshot(0)['metadata']['status'], 'accepted')
        self.assertEqual(len([row for row in self.messages.get_recent() if row['type'] == 'job_created']), 1)

    def test_failed_reply_explains_resolved_card_and_manual_resend_without_retry_duplicate(self):
        card = self.decision()
        with patch.object(app, '_publish_operator_message', side_effect=OSError('private storage path')):
            response = asyncio.run(app.resolve_decision(card['id'], self.request({'choice': 'Blue'})))
        self.assertEqual(response.status_code, 503)
        error = json.loads(response.body)['error']
        self.assertIn('resolved', error)
        self.assertIn('resend', error)
        self.assertNotIn('private', error)
        self.assertTrue(self.messages.get_snapshot(card['id'])['metadata']['resolved'])
        retry = asyncio.run(app.resolve_decision(card['id'], self.request({'choice': 'Blue'})))
        self.assertEqual(retry.status_code, 400)
        self.assertEqual(len(self.trigger.queue.records('review')), 0)


if __name__ == '__main__':
    unittest.main()
