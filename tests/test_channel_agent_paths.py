"""Agent-facing channel refusal units, no live MCP server or worker claims."""
import asyncio
import json
from copy import deepcopy
import unittest
import uuid
from unittest.mock import AsyncMock, Mock, patch

import app
import mcp_bridge
from channel_lifecycle import ChannelInactive, ChannelUnavailable
from tests import test_channel_ingress as fixture
from tests.test_identity_contract import auth_ctx


class ChannelAgentPathTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelIngressTests.setUp(self)
        self.trigger.queue.bind_channel_policy(app._channels)
        for name, value in {'store': self.messages, 'registry': self.registry, 'jobs': self.jobs,
                            'session_engine': self.engine, 'agents': self.trigger, 'router': self.router,
                            'room_settings': self.channel_service.settings, 'config': {
                                'images': {'upload_dir': str(self.root / 'uploads')}},
                            '_CURSORS_FILE': None, 'channel_policy_getter': app._channels}.items():
            self.patches.enter_context(patch.object(mcp_bridge, name, value, create=True))
        for name in ('_last_read_channel', '_last_read_job_id', '_cursors', '_presence'):
            self.patches.enter_context(patch.dict(getattr(mcp_bridge, name), {}, clear=True))

    def request(self, body):
        return Mock(headers={'authorization': 'Bearer ' + self.owner['token']},
                    json=AsyncMock(return_value=body), body=AsyncMock(return_value=json.dumps(body).encode('utf-8')))

    def archive(self):
        self.channel_service.catalog.set_state('review', 'archived', expected_revision=0)

    def test_agent_rest_send_refuses_archived_before_history_and_queue_changes(self):
        self.archive()
        before = self.trigger.queue.path.read_bytes()
        result = asyncio.run(app.api_send(self.request({'text': 'shared input', 'channel': 'review'})))
        self.assertEqual(result.status_code, 409)
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        accepted = asyncio.run(app.api_send(self.request({'text': '@claude delayed', 'channel': 'peer'})))
        message = json.loads(accepted.body)
        self.channel_service.catalog.set_state('peer', 'archived',
            expected_revision=self.channel_service.catalog.snapshot()['revision'])
        before, router = self.trigger.queue.path.read_bytes(), deepcopy(self.router._channels)
        asyncio.run(app._handle_new_message(message))
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        self.assertEqual(self.router._channels, router)

    def test_mcp_remembered_archived_channel_refuses_without_general_fallback_or_cursor_change(self):
        self.archive()
        mcp_bridge._last_read_channel['operator'] = 'review'
        before = deepcopy(mcp_bridge._cursors)
        result = mcp_bridge.chat_send('operator', 'shared input')
        self.assertIn('Error:', result)
        self.assertIn('archived', result.lower())
        self.assertEqual(self.messages.get_recent(), [])
        self.assertEqual(mcp_bridge._cursors, before)
        self.assertEqual(mcp_bridge._last_read_channel['operator'], 'review')

    def test_deleted_cursor_keeps_retired_target_and_never_redirects_to_general(self):
        mcp_bridge._last_read_channel.update(operator='review', other='peer')
        preview = self.channel_service.preview('delete', 'review')
        self.channel_service.apply('delete', 'review', request_id=uuid.uuid4().hex,
            confirmation='review', preview_token=preview['preview_token'])
        mcp_bridge.migrate_cursors_delete('review')
        self.assertEqual(mcp_bridge._last_read_channel, {'operator': 'review', 'other': 'peer'})
        self.assertIn('retired', mcp_bridge.chat_send('operator', 'must refuse').lower())
        self.assertEqual(self.messages.get_recent(), [])

    def test_unknown_and_invalid_targets_refuse_without_cursor_or_history_changes(self):
        self.assertIn('Error:', mcp_bridge.chat_send('operator', 'shared', channel='unregistered'))
        self.assertEqual(asyncio.run(app.api_send(self.request({'text': 'shared', 'channel': 'Bad Name'}))).status_code, 400)
        self.assertEqual(self.messages.get_recent(), [])
        self.assertEqual(mcp_bridge._cursors, {})

    def test_active_peer_send_preserves_token_identity_and_actual_channel(self):
        response = asyncio.run(app.api_send(self.request({'text': 'REST shared', 'channel': 'peer', 'sender': 'claude'})))
        self.assertEqual(response.status_code, 200)
        result = mcp_bridge.chat_send('claude', 'MCP shared', channel='peer', ctx=auth_ctx(self.owner['token']))
        self.assertIn('Sent', result)
        saved = self.messages.get_recent(channel='peer')
        self.assertEqual(len(saved), 2)
        self.assertTrue(all(item['sender'] == self.owner['name'] for item in saved))
        self.assertEqual(self.messages.get_recent(channel='general'), [])

    def test_archived_upload_is_refused_before_copying_or_creating_upload_directory(self):
        source = self.root / 'source.png'
        source.write_bytes(b'fixture image bytes')
        self.archive()
        result = mcp_bridge.chat_send('operator', 'shared', channel='review', image_path=str(source))
        self.assertIn('Error:', result)
        self.assertFalse((self.root / 'uploads').exists())
        self.assertEqual(self.messages.get_recent(), [])

    def test_job_scope_uses_stored_channel_before_rest_or_mcp_publication(self):
        job = self.jobs.create('Keep', 'task', 'review', 'operator')
        self.archive()
        response = asyncio.run(app.api_send(self.request({'text': 'shared', 'job_id': job['id']})))
        self.assertEqual(response.status_code, 409)
        self.assertIn('Error:', mcp_bridge.chat_send('operator', 'shared', job_id=job['id']))
        self.assertEqual(self.jobs.get_messages(job['id']), [])
        self.assertEqual(self.messages.get_recent(), [])

    def test_job_channel_mismatch_cannot_bypass_actual_channel_guard(self):
        job = self.jobs.create('Keep', 'task', 'review', 'operator')
        response = asyncio.run(app.api_send(self.request({'text': 'shared', 'job_id': job['id'], 'channel': 'peer'})))
        self.assertEqual(response.status_code, 400)
        self.assertIn('Error:', mcp_bridge.chat_send('operator', 'shared', job_id=job['id'], channel='peer'))
        self.assertEqual(self.jobs.get_messages(job['id']), [])
        with patch.object(self.jobs, 'add_message', return_value=None):
            response = asyncio.run(app.api_send(self.request({'text': 'shared', 'job_id': job['id']})))
        self.assertEqual(response.status_code, 404)

    def test_direct_agent_triggers_share_the_final_enqueue_guard(self):
        self.archive()
        before = self.trigger.queue.path.read_bytes()
        calls = (lambda: self.trigger.trigger_sync(self.peer['name'], 'operator: shared', channel='review'),
                 lambda: self.trigger.trigger_identity_sync(self.peer['identity_id'], dispatch_id=uuid.uuid4().hex,
                                                           message='operator: shared', channel='review'),
                 lambda: asyncio.run(self.trigger.trigger(self.peer['name'], 'operator: shared', channel='review')))
        for call in calls:
            with self.assertRaises(ChannelInactive):
                call()
            self.assertEqual(self.trigger.queue.path.read_bytes(), before)

    def test_conversion_trigger_maps_inactive_and_active_peer_queues_once(self):
        self.archive()
        before = self.trigger.queue.path.read_bytes()
        response = asyncio.run(app.trigger_agent_silent(self.request({'agent': 'claude', 'message': 'shared', 'channel': 'review'})))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.trigger.queue.path.read_bytes(), before)
        result = asyncio.run(app.trigger_agent_silent(self.request({'agent': 'claude', 'message': 'shared', 'channel': 'peer'})))
        self.assertEqual(result, {'ok': True, 'triggered': [self.peer['name']]})
        self.assertEqual(len(self.trigger.queue.records('peer')), 1)

    def test_unreadable_policy_maps_to_tool_error_and_rest_503_without_writes(self):
        self.channel_service.catalog.path.write_text('{broken', encoding='utf-8')
        response = asyncio.run(app.api_send(self.request({'text': 'shared', 'channel': 'peer'})))
        self.assertEqual(response.status_code, 503)
        self.assertIn('Error:', mcp_bridge.chat_send('operator', 'shared', channel='peer'))
        self.assertEqual(self.messages.get_recent(), [])

    def test_unreadable_policy_maps_claim_503_but_http_release_still_settles(self):
        active = self.trigger.queue.claim(self.owner, 'worker')
        self.channel_service.catalog.path.write_text('{broken', encoding='utf-8')
        response = asyncio.run(app.dispatch_operation('claim', self.request({'consumer_id': 'worker'})))
        self.assertEqual(response.status_code, 503)
        release = asyncio.run(app.dispatch_operation('release', self.request({'consumer_id': 'worker',
            'dispatch_id': active['envelope']['dispatch_id']})))
        self.assertEqual(release.status_code, 200)


if __name__ == '__main__':
    unittest.main()
