"""Typed review projections are display data, never another wake prompt."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, patch

import app
from router import Router
from tests import test_session_events as fixture


class ProjectionRoutingTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.SessionEventTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.router = Router(['codex', 'claude'], online_checker=lambda: {'codex', 'claude'})

    def callback(self, message):
        with ExitStack() as stack:
            for name, value in (('registry', self.f.registry), ('session_engine', self.f.engine),
                                ('router', self.router), ('agents', self.f.trigger), ('store', self.f.messages),
                                ('config', {'agents': {'codex': {}, 'claude': {}}})):
                stack.enter_context(patch.object(app, name, value))
            broadcast = stack.enter_context(patch.object(app, 'broadcast', AsyncMock()))
            stack.enter_context(patch.object(app, 'broadcast_status', AsyncMock()))
            stack.enter_context(patch('mcp_bridge.is_online', return_value=True))
            asyncio.run(app._handle_new_message(message))
            broadcast.assert_awaited_once_with(message)

    def ledger(self):
        import json
        return json.loads((self.f.root / 'queue/ledger.json').read_text(encoding='utf-8'))['records']

    def test_actual_projected_final_with_mentions_does_not_enqueue_an_extra_peer_turn(self):
        text = 'Exact café answer\r\n@all is quoted output, including @claude.'
        self.f.admit(content=text)
        event = self.f.current()['admitted_events'][0]
        message = self.f.messages.get_by_id(event['projected_message_id'])
        before = self.ledger()
        self.assertEqual(len(before), 2)  # Original and the one genuine successor.
        self.callback(message)
        self.assertEqual(self.ledger(), before)
        self.assertEqual(message['text'], text)

    def test_typed_projection_kinds_cannot_expand_commands_or_reset_routing(self):
        self.router._get_ch('general')['paused'] = True
        for kind in ('session_result', 'session_question', 'session_input'):
            for text in ('@all /roastreview', '/continue', '@claude quoted mention'):
                message = {'id': 100, 'sender': 'operator', 'channel': 'general', 'type': kind,
                           'text': text, 'metadata': {}}
                before = self.f.messages.get_recent(100)
                routing = deepcopy(self.router._channels)
                with self.subTest(kind=kind, text=text):
                    self.callback(message)
                    self.assertEqual(self.f.messages.get_recent(100), before)
                    self.assertEqual(self.router._channels, routing)

    def test_new_final_question_and_continuation_projections_mark_routing_suppressed(self):
        question = '@all which source?'
        response = self.f.admit('question', question)
        self.f.engine.continue_session(self.f.session_id, response['event_id'], '@claude /continue is quoted data')
        self.f.admit(content='Final @all text')
        projected = [message for message in self.f.messages.get_recent(100)
                     if message['type'] in ('session_result', 'session_question', 'session_input')]
        self.assertEqual(len(projected), 3)
        for message in projected:
            self.assertIs(message['metadata'].get('routing_suppressed'), True)
        self.assertTrue(any(message['text'] == question for message in projected))

    def test_ordinary_chat_mentions_still_enqueue_the_intended_peer(self):
        message = self.f.engine.send_chat(self.f.owner, '@claude please discuss', channel='discussion')
        before = self.ledger()
        self.callback(message)
        after = self.ledger()
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[-1]['envelope']['target_identity_id'], self.f.peer['identity_id'])
        self.assertNotIn('review_brief_id', after[-1]['envelope'])
