"""Configured rename wiring and delayed callback seams, no native claims."""
import asyncio
import json
import uuid
from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import patch

import app
from tests import test_channel_rename_service as fixture
from tests import test_channel_routes as route_fixture


class ChannelRenameRuntimeTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelRenameServiceTests.setUp(self)

    def test_callback_delayed_by_broadcast_does_not_resurrect_retired_router_state(self):
        self.service.router._get_ch('review')['hop_count'] = 2
        message = self.messages.add(self.owner['name'], 'Ordinary @claude', channel='review',
                                    metadata={'seat_identity_id': self.owner['identity_id']})
        async def exercise():
            entered, release = asyncio.Event(), asyncio.Event()
            async def broadcast(value):
                entered.set()
                await release.wait()
            with ExitStack() as seams:
                values = {'channel_service': self.service, 'session_engine': self.engine,
                          'store': self.messages, 'router': self.service.router, 'registry': self.registry,
                          'agents': self.trigger, 'room_settings': self.settings, 'config': {'agents': {}},
                          '_last_active_channel': 'review', '_agent_last_channel': {'codex': 'review'}}
                for key, value in values.items():
                    seams.enter_context(patch.object(app, key, value))
                seams.enter_context(patch.object(app, 'broadcast', side_effect=broadcast))
                self.service._migrate_last_active = app._migrate_channel_last_active
                task = asyncio.create_task(app._handle_new_message(message))
                await asyncio.wait_for(entered.wait(), 1)
                result = await asyncio.to_thread(fixture.ChannelRenameServiceTests.rename, self)
                self.assertEqual(result['channel'], 'renamed')
                before = self.trigger.queue.path.read_bytes()
                release.set()
                await task
                self.assertNotIn('review', self.service.router._channels)
                self.assertEqual(app._last_active_channel, 'renamed')
                self.assertEqual(app._agent_last_channel['codex'], 'renamed')
                self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        asyncio.run(exercise())


class ChannelRenameRouteTests(unittest.TestCase):
    def setUp(self):
        route_fixture.ChannelRoutesTests.setUp(self)

    def payload(self):
        response = self.client.post('/api/channels/preview', headers=self.headers,
            json={'op': 'rename', 'channel': 'discussion', 'new_name': 'renamed'})
        self.assertEqual(response.status_code, 200, response.text)
        return {'op': 'rename', 'channel': 'discussion', 'new_name': 'renamed',
                'request_id': uuid.uuid4().hex, 'confirmation': 'discussion',
                'preview_token': response.json()['preview_token']}

    def test_operator_http_rename_and_completed_replay_emit_single_final_event(self):
        message = self.f.messages.add('operator', 'Exact retained source', channel='discussion')
        events = []
        self.service.on_change(events.append)
        body = self.payload()
        accepted = self.client.post('/api/channels/apply', headers=self.headers, json=body)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()['channel'], 'renamed')
        self.assertEqual(self.f.messages.get_snapshot(message['id']), {**message, 'channel': 'renamed'})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['type'], 'channel_renamed')
        replay = self.client.post('/api/channels/apply', headers=self.headers, json=body)
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(len(events), 1)

    def test_post_commit_projection_failure_stays_http_success_and_get_self_heals(self):
        body = self.payload()
        save = self.service._save_settings
        def fail_new():
            if 'renamed' in self.service.settings['channels']:
                raise OSError('projection failure')
            return save()
        with patch.object(self.service, '_save_settings', side_effect=fail_new):
            accepted = self.client.post('/api/channels/apply', headers=self.headers, json=body)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertIn('projection_warning', accepted.json())
        self.assertIsNone(self.service.catalog.snapshot()['intent'])
        response = self.client.get('/api/channels', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn('renamed', self.service.settings['channels'])
