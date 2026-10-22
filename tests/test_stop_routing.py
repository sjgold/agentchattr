"""Stopped scope cannot escape through ordinary chat or mention descendants."""
import unittest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
import mcp_bridge
from dispatch_queue import QueueAccessError, QueueConflict


class StopRoutingTests(unittest.TestCase):
    def setUp(self):
        from tests.test_session_stop import SessionStopTests
        self.fixture = SessionStopTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_tagged_late_chat_is_quarantined_and_wrong_seat_cannot_tag_it(self):
        f = self.fixture
        f.engine.stop_session(f.session_id)
        text = 'Late café\r\n@claude do more work'
        msg = f.engine.send_chat(f.owner, text, dispatch_id=f.invocation['dispatch_id'])
        self.assertTrue(msg['metadata']['routing_suppressed'])
        self.assertEqual(msg['type'], 'quarantine')
        self.assertEqual(f.current()['quarantined_events'][0]['content'], text)
        with self.assertRaises(QueueAccessError):
            f.engine.send_chat(f.peer, text, dispatch_id=f.invocation['dispatch_id'])
        self.assertEqual(len(f.current()['quarantined_events']), 1)

    def test_untagged_stopped_seat_warns_but_fresh_tagged_discussion_and_peers_work(self):
        f = self.fixture
        f.engine.stop_session(f.session_id)
        untagged = f.engine.send_chat(f.owner, '@claude late unscoped')
        self.assertIn('[quarantine-warning]', untagged['text'])
        self.assertEqual(untagged['metadata']['provenance'], 'unverified_scope')
        f.trigger.trigger_sync(f.owner['name'], message='human: new independent discussion', dispatch_id='d' * 32)
        fresh = f.engine.send_chat(f.owner, '@claude fresh discussion', dispatch_id='d' * 32)
        self.assertFalse(fresh['metadata'].get('routing_suppressed', False))
        peer = f.engine.send_chat(f.peer, 'Unrelated peer discussion')
        self.assertFalse(peer['metadata'].get('routing_suppressed', False))
        self.assertEqual(len(f.current()['quarantined_events']), 1)

    def test_live_tagged_chat_preserves_run_scope_and_descendant_enqueue_obeys_stop(self):
        f = self.fixture
        msg = f.engine.send_chat(f.owner, '@claude continue', dispatch_id=f.invocation['dispatch_id'])
        meta = msg['metadata']
        self.assertEqual(meta['run_id'], f.run_id)
        self.assertEqual(meta['attempt_id'], f.invocation['attempt_id'])
        f.engine.stop_session(f.session_id)
        with self.assertRaises(QueueConflict):
            f.trigger.trigger_sync(f.peer['name'], message='late callback', run_id=meta['run_id'])

    def test_api_and_mcp_chat_ingress_keep_stopped_scope(self):
        f = self.fixture
        f.engine.stop_session(f.session_id)
        api = FastAPI()
        api.add_api_route('/api/send', app.api_send, methods=['POST'])
        client = TestClient(api)
        with patch.object(app, 'registry', f.registry), patch.object(app, 'session_engine', f.engine), patch.object(app, 'store', f.messages):
            response = client.post('/api/send', json={'text': '@claude late', 'dispatch_id': f.invocation['dispatch_id']},
                                   headers={'Authorization': 'Bearer ' + f.owner['token']})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['metadata']['routing_suppressed'])
        with patch.object(mcp_bridge, 'registry', f.registry), patch.object(mcp_bridge, 'store', f.messages), \
             patch.object(mcp_bridge, 'session_engine', f.engine), patch.object(mcp_bridge, '_authenticated_instance', return_value=f.owner), \
             patch.object(mcp_bridge, '_resolve_tool_identity', return_value=(f.owner['name'], None)):
            result = mcp_bridge.chat_send(f.owner['name'], '@claude late MCP', dispatch_id=f.invocation['dispatch_id'])
            self.assertIn('Sent', result)
        self.assertTrue(f.messages.get_recent(1)[0]['metadata']['routing_suppressed'])
        self.assertEqual(len(f.current()['quarantined_events']), 2)

    def test_delayed_callback_after_stop_does_not_route_or_execute_slash_commands(self):
        f = self.fixture
        msg = f.engine.send_chat(f.owner, '@claude /continue', dispatch_id=f.invocation['dispatch_id'])
        f.engine.stop_session(f.session_id)
        router = Mock()
        with patch.object(app, 'session_engine', f.engine), patch.object(app, 'registry', f.registry), \
             patch.object(app, 'router', router), patch.object(app, 'broadcast', AsyncMock()), \
             patch.object(app, 'config', {'agents': {}}):
            asyncio.run(app._handle_new_message(msg))
        router.get_targets.assert_not_called()
        router.continue_routing.assert_not_called()


if __name__ == '__main__':
    unittest.main()
