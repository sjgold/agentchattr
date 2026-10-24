"""Remaining primary writer fences, with real stores and handler seams only."""
import json
import unittest
from unittest.mock import Mock, patch

import app
import mcp_bridge
from rules import RuleStore
from channel_lifecycle import ChannelInactive
from tests import test_channel_agent_paths as fixture
from tests import test_channel_routes as route_fixture
from tests.test_identity_contract import auth_ctx


class ChannelPrimaryWriterTests(unittest.TestCase):
    archive = fixture.ChannelAgentPathTests.archive
    socket_events = route_fixture.ChannelRoutesTests.socket_events

    def setUp(self):
        fixture.ChannelAgentPathTests.setUp(self)
        self.rules = RuleStore(str(self.root / 'rules.json'))
        self.patches.enter_context(patch.object(mcp_bridge, 'rules', self.rules))
        self.patches.enter_context(patch.object(mcp_bridge, 'summaries', self.channel_service.summaries))
        self.patches.enter_context(patch.object(app, 'rules', self.rules))
        self.patches.enter_context(patch.object(app, 'session_token', 'operator-routing-test'))

    def test_mcp_job_proposal_refuses_before_card_or_cursor_changes(self):
        self.archive()
        result = mcp_bridge.chat_propose_job(self.peer['name'], 'Proposed work',
            channel='review', ctx=auth_ctx(self.peer['token']))
        self.assertTrue(result.startswith('Error:'), result)
        self.assertEqual(self.messages.get_recent(), [])
        self.assertEqual(mcp_bridge._cursors, {})

    def test_mcp_rule_proposal_refuses_before_rule_id_or_card_changes(self):
        self.archive()
        before = self.rules._next_id
        result = mcp_bridge.chat_rules('propose', self.peer['name'], 'Use exact sources',
            channel='review', ctx=auth_ctx(self.peer['token']))
        self.assertTrue(result.startswith('Error:'), result)
        self.assertEqual(self.rules._next_id, before)
        self.assertEqual(self.rules.list_all(), [])
        self.assertEqual(self.messages.get_recent(), [])

    def test_summary_refuses_before_saved_summary_or_timeline_changes(self):
        saved = self.channel_service.summaries.write('review', 'Retained summary', 'operator')
        before = self.channel_service.summaries._path.read_bytes()
        self.archive()
        result = mcp_bridge.chat_summary('write', self.peer['name'], 'Must not replace',
            channel='review', ctx=auth_ctx(self.peer['token']))
        self.assertTrue(result.startswith('Error:'), result)
        self.assertEqual(self.channel_service.summaries._path.read_bytes(), before)
        self.assertEqual(self.channel_service.summaries.get('review'), saved)
        self.assertEqual(self.messages.get_recent(), [])

    def test_summary_history_and_rule_list_remain_readable_during_policy_hold(self):
        saved = self.channel_service.summaries.write('review', 'Retained summary', 'operator')
        with patch.object(app, 'channel_service', None):
            result = mcp_bridge.chat_summary('read', self.peer['name'], channel='review', ctx=auth_ctx(self.peer['token']))
            listed = mcp_bridge.chat_rules('list', self.peer['name'], ctx=auth_ctx(self.peer['token']))
        self.assertEqual(json.loads(result), saved)
        self.assertEqual(listed, 'No active rules.')

    def writes(self, channel):
        context = auth_ctx(self.peer['token'])
        return (lambda: mcp_bridge.chat_propose_job(self.peer['name'], 'Task', channel=channel, ctx=context),
                lambda: mcp_bridge.chat_rules('propose', self.peer['name'], 'Rule', channel=channel, ctx=context),
                lambda: mcp_bridge.chat_summary('write', self.peer['name'], 'Summary', channel=channel, ctx=context))

    def test_unavailable_mcp_writers_fail_cleanly_without_rule_summary_or_message(self):
        with patch.object(app, 'channel_service', None):
            for call in self.writes('review'):
                self.assertTrue(call().startswith('Error:'))
        self.assertEqual(self.rules.list_all(), [])
        self.assertEqual(self.channel_service.summaries.get_all(), {})
        self.assertEqual(self.messages.get_recent(), [])

    def test_bad_channel_grammar_is_a_clean_tool_refusal(self):
        for call in self.writes('Bad/channel'):
            self.assertTrue(call().startswith('Error:'))
        self.assertEqual(self.rules.list_all(), [])
        self.assertEqual(self.channel_service.summaries.get_all(), {})
        self.assertEqual(self.messages.get_recent(), [])

    def test_direct_engine_callback_cannot_bypass_channel_policy(self):
        self.engine.bind_channel_policy(app._channels)
        self.archive()
        callback = Mock(return_value={'id': 4})
        before = self.sessions._path.read_bytes(), self.trigger.queue.path.read_bytes()
        with self.assertRaises(ChannelInactive):
            self.engine.send_chat(self.peer, 'Must not publish', channel='review', publish=callback)
        callback.assert_not_called()
        self.assertEqual((self.sessions._path.read_bytes(), self.trigger.queue.path.read_bytes()), before)

    def test_ws_agent_proposal_refusal_keeps_socket_usable_for_active_peer(self):
        self.archive()
        frames = self.socket_events([
            {'type': 'rule_propose', 'author': self.peer['name'], 'text': 'Refused', 'channel': 'review'},
            {'type': 'rule_propose', 'author': self.peer['name'], 'text': 'Accepted peer', 'channel': 'peer'}])
        self.assertTrue(any(frame['type'] == 'channel_error' and frame['code'] == 409 for frame in frames))
        self.assertEqual([rule['text'] for rule in self.rules.list_all()], ['Accepted peer'])
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        self.assertEqual(len(self.messages.get_recent(channel='peer')), 1)

    def test_ws_human_proposal_refuses_before_draft_creation(self):
        self.archive()
        frames = self.socket_events([{'type': 'rule_propose', 'author': 'user', 'text': 'Refused', 'channel': 'review'}])
        self.assertTrue(any(frame['type'] == 'channel_error' for frame in frames))
        self.assertEqual(self.rules.list_all(), [])

    def test_active_mcp_proposals_keep_bearer_identity_and_one_card_each(self):
        context = auth_ctx(self.peer['token'])
        self.assertIn('Proposed job', mcp_bridge.chat_propose_job('spoofed', 'Task', channel='peer', ctx=context))
        self.assertIn('Proposed rule', mcp_bridge.chat_rules('propose', 'spoofed', 'Rule', channel='peer', ctx=context))
        self.assertEqual([message['sender'] for message in self.messages.get_recent()], [self.peer['name']] * 2)
        self.assertEqual(self.rules.list_all()[0]['author'], self.peer['name'])

    def test_rule_and_summary_effects_run_under_engine_then_catalog(self):
        original_rule = self.rules.propose
        original_summary = self.channel_service.summaries.write
        observed = []
        def checked(callback, *args, **kwargs):
            observed.append((self.engine._lock._is_owned(), self.channel_service.catalog._lock._is_owned()))
            return callback(*args, **kwargs)
        with patch.object(self.rules, 'propose', side_effect=lambda *a, **k: checked(original_rule, *a, **k)), \
             patch.object(self.channel_service.summaries, 'write', side_effect=lambda *a, **k: checked(original_summary, *a, **k)):
            self.writes('peer')[1]()
            self.writes('peer')[2]()
        self.assertEqual(observed, [(True, True), (True, True)])

    def test_direct_engine_active_callback_keeps_authenticated_metadata(self):
        self.engine.bind_channel_policy(app._channels)
        callback = Mock(return_value={'id': 4})
        self.assertEqual(self.engine.send_chat(self.peer, 'Exact\r\nsource', channel='peer', publish=callback), {'id': 4})
        self.assertEqual(callback.call_args.args[0], 'Exact\r\nsource')
        self.assertEqual(callback.call_args.args[1]['seat_identity_id'], self.peer['identity_id'])


if __name__ == '__main__':
    unittest.main()
