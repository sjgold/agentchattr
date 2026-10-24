"""Real store/catalog and public handler seams, with no native or HTTP claims."""
import asyncio
import json
from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, Mock, patch

import app
from fastapi import WebSocketDisconnect
from rules import RuleStore
from tests import test_channel_import as fixture


class ChannelMessageMutationTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelImportTests.setUp(self)
        self.rules = RuleStore(str(self.root / 'rules.json'))
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        for name, value in {'store': self.messages, 'jobs': self.jobs, 'rules': self.rules,
                'session_engine': self.engine, 'session_store': self.sessions,
                'agents': self.trigger, 'registry': self.registry,
                'channel_service': self.service, 'room_settings': self.settings,
                'router': self.service.router, 'ws_clients': set(), 'schedules': self.schedules,
                'session_token': 'mutation-test', 'config': {}, 'agent_hats': {}}.items():
            self.patches.enter_context(patch.object(app, name, value))
        self.broadcast = self.patches.enter_context(patch.object(app, '_broadcast', new=AsyncMock(wraps=app._broadcast)))
        self.patches.enter_context(patch.object(app, 'broadcast_status', new=AsyncMock()))

    def request(self, body):
        request = Mock()
        request.json = AsyncMock(return_value=deepcopy(body))
        return request

    def effects(self):
        return {'files': {p.relative_to(self.root).as_posix(): p.read_bytes()
                         for p in self.root.rglob('*') if p.is_file()},
                'messages': deepcopy(self.messages._messages),
                'rules': self.rules.list_all(), 'rule_next_id': self.rules._next_id,
                'rule_epoch': self.rules.epoch, 'message_next_id': self.messages._next_id,
                'settings': deepcopy(self.settings)}

    def archive(self):
        self.catalog.set_state('review', 'archived', expected_revision=self.catalog.snapshot()['revision'])

    def socket(self, events, after_first=None):
        frames = []
        inputs = iter(events)
        class Socket:
            query_params = {'token': 'mutation-test'}
            reads = 0
            async def accept(inner): pass
            async def send_text(inner, value): frames.append(json.loads(value))
            async def receive_text(inner):
                if inner.reads == 1 and after_first is not None:
                    after_first()
                inner.reads += 1
                event = next(inputs, None)
                if event is None:
                    raise WebSocketDisconnect()
                return json.dumps(event)
        asyncio.run(asyncio.wait_for(app.websocket_endpoint(Socket()), 2))
        return frames

    def assert_error_frame(self, frames, code=None):
        errors = [row for row in frames if row['type'] in ('channel_error', 'message_error')]
        self.assertTrue(errors, frames)
        if code is not None:
            self.assertTrue(any(row.get('code') == code for row in errors), errors)

    def test_archived_decision_refuses_cleanly_before_metadata_file_or_queue_changes(self):
        card = self.messages.add('codex', 'Choose a source', channel='review', msg_type='decision',
            metadata={'choices': ['Blue', 'Green'], 'resolved': False})
        self.archive()
        before = self.effects()
        result = asyncio.run(app.resolve_decision(card['id'], self.request({'choice': 'Blue'})))
        self.assertEqual(self.effects(), before)
        self.assertEqual(getattr(result, 'status_code', 200), 409, result)
        self.broadcast.assert_not_awaited()

    def test_inactive_job_and_session_proposal_demotions_have_no_effects(self):
        cards = [self.messages.add('codex', 'Keep proposal', channel='review', msg_type=kind,
                    metadata={'title': 'Original', 'body': 'Exact body', 'errors': ['Keep details']})
                 for kind in ('job_proposal', 'session_draft')]
        self.archive()
        for card in cards:
            with self.subTest(kind=card['type']):
                before = self.effects()
                result = asyncio.run(app.demote_proposal(card['id']))
                self.assertEqual(getattr(result, 'status_code', 200), 409)
                self.assertEqual(self.effects(), before)
        self.broadcast.assert_not_awaited()

    def test_inactive_rule_demotion_cannot_delete_rule_before_card_refusal(self):
        rule = self.rules.propose('Retain this rule', 'codex')
        card = self.messages.add('codex', 'Rule', channel='review', msg_type='rule_proposal',
                                 metadata={'rule_id': rule['id'], 'text': 'Retain this rule'})
        self.archive()
        before = self.effects()
        result = asyncio.run(app.demote_rule_proposal(card['id']))
        self.assertEqual(getattr(result, 'status_code', 200), 409)
        self.assertEqual(self.effects(), before)

    def test_mixed_delete_refuses_entire_set_and_socket_still_accepts_peer(self):
        archived = self.messages.add('operator', 'Keep archived', channel='review')
        peer = self.messages.add('operator', 'Keep peer', channel='peer')
        self.archive()
        before, checkpoint = self.effects(), []
        frames = self.socket([{'type': 'delete', 'ids': [peer['id'], archived['id']]},
            {'type': 'message', 'text': 'Peer still works', 'channel': 'peer', 'selected_recipients': []}],
            after_first=lambda: checkpoint.append(self.effects()))
        self.assertEqual(checkpoint, [before])
        self.assert_error_frame(frames)
        self.assertTrue(any(row['type'] == 'message_accepted' and row['channel'] == 'peer' for row in frames))
        self.assertEqual(self.messages.get_snapshot(peer['id']), peer)
        self.assertEqual(self.messages.get_snapshot(archived['id']), archived)

    def test_archived_todo_add_toggle_done_reopen_remove_are_clean_noops(self):
        empty = self.messages.add('operator', 'No todo', channel='review')
        todo = self.messages.add('operator', 'Todo', channel='review')
        done = self.messages.add('operator', 'Done', channel='review')
        self.messages.add_todo(todo['id'])
        self.messages.add_todo(done['id'])
        self.messages.complete_todo(done['id'])
        self.archive()
        for kind, card in [('todo_add', empty), ('todo_toggle', todo),
                           ('todo_toggle', done), ('todo_remove', todo)]:
            with self.subTest(kind=kind, id=card['id']):
                before = self.effects()
                with patch.object(app, 'broadcast_todo_update', new=AsyncMock()) as broadcast:
                    frames = self.socket([{'type': kind, 'id': card['id']}])
                    broadcast.assert_not_awaited()
                self.assert_error_frame(frames)
                self.assertEqual(self.effects(), before)

    def test_inactive_clear_and_continue_preserve_history_and_all_router_channels(self):
        self.messages.add('operator', 'Retained source', channel='review')
        self.service.router._channels = {
            name: {'hop_count': 9, 'paused': True, 'guard_emitted': True}
            for name in ('general', 'review', 'peer')}
        self.archive()
        for command in ('/clear', '/continue'):
            with self.subTest(command=command):
                before, routing = self.effects(), deepcopy(self.service.router._channels)
                frames = self.socket([{'type': 'message', 'text': command, 'channel': 'review'}])
                self.assert_error_frame(frames)
                self.assertEqual(self.effects(), before)
                self.assertEqual(self.service.router._channels, routing)

    def test_active_decision_and_rule_operations_keep_existing_choice_semantics(self):
        card = self.messages.add('operator', 'Pick', channel='peer', msg_type='decision',
                                 metadata={'choices': ['Blue'], 'resolved': False})
        result = asyncio.run(app.resolve_decision(card['id'], self.request({'choice': 'Blue'})))
        self.assertEqual(result, {'ok': True, 'chosen': 'Blue'})
        self.assertEqual(self.messages.get_snapshot(card['id'])['metadata'],
                         {'choices': ['Blue'], 'resolved': True, 'chosen': 'Blue'})
        self.assertEqual(self.messages.get_recent(channel='peer')[-1]['text'], '@operator Blue')
        for action, status in [('activate', 'activated'), ('draft', 'drafted'), ('dismiss', 'dismissed')]:
            rule = self.rules.propose('Rule ' + action, 'codex')
            proposal = self.messages.add('codex', 'Rule', channel='peer', msg_type='rule_proposal',
                                        metadata={'rule_id': rule['id']})
            result = asyncio.run(app.resolve_rule_proposal(proposal['id'], self.request({'action': action})))
            self.assertEqual(result['metadata']['status'], status)

    def test_active_peer_todos_delete_and_demotions_remain_functional(self):
        card = self.messages.add('operator', 'Todo', channel='peer')
        for event, expected in [('todo_add', 'todo'), ('todo_toggle', 'done'),
                                ('todo_toggle', 'todo'), ('todo_remove', None)]:
            frames = self.socket([{'type': event, 'id': card['id']}])
            self.assertFalse(any(row['type'] in ('channel_error', 'message_error') for row in frames))
            self.assertEqual(self.messages.get_todo_status(card['id']), expected)
        frames = self.socket([{'type': 'delete', 'ids': [card['id']]}])
        self.assertIsNone(self.messages.get_snapshot(card['id']))
        self.assertTrue(any(row['type'] == 'delete' for row in frames))
        for kind in ('job_proposal', 'session_draft'):
            proposal = self.messages.add('codex', 'Proposal', channel='peer', msg_type=kind,
                                        metadata={'title': 'Title', 'body': 'Body'})
            self.assertEqual(asyncio.run(app.demote_proposal(proposal['id']))['type'], 'chat')
        rule = self.rules.propose('Demote rule', 'codex')
        proposal = self.messages.add('codex', 'Rule', channel='peer', msg_type='rule_proposal',
                                    metadata={'rule_id': rule['id'], 'text': 'Demote rule'})
        self.assertEqual(asyncio.run(app.demote_rule_proposal(proposal['id']))['type'], 'chat')
        self.assertIsNone(self.rules.get(rule['id']))

    def test_corrupt_catalog_maps_http503_and_clean_socket_error_without_reseed(self):
        card = self.messages.add('codex', 'Choose', channel='review', msg_type='decision',
                                 metadata={'choices': ['Blue'], 'resolved': False})
        self.catalog.path.write_text('{broken', encoding='utf-8')
        before = self.effects()
        result = asyncio.run(app.resolve_decision(card['id'], self.request({'choice': 'Blue'})))
        self.assertEqual(getattr(result, 'status_code', 200), 503)
        self.assertEqual(self.effects(), before)
        frames = self.socket([{'type': 'delete', 'ids': [card['id']]}])
        self.assert_error_frame(frames, 503)
        self.assertEqual(self.effects(), before)

    def test_create_job_inactive_destination_refuses_before_id_card_or_breadcrumb(self):
        self.archive()
        before, next_id = self.effects(), self.jobs._next_id
        result = asyncio.run(app.create_job(self.request({'title': 'Unsaved job', 'channel': 'review'})))
        self.assertEqual(getattr(result, 'status_code', 200), 409)
        self.assertEqual(self.jobs._next_id, next_id)
        self.assertEqual(self.effects(), before)

    def test_create_job_active_destination_cannot_accept_archived_proposal_anchor(self):
        # ID zero is a real proposal anchor, not a missing-anchor sentinel.
        anchor = self.messages.add('codex', 'Proposal', channel='review', msg_type='job_proposal',
                                   metadata={'title': 'Original', 'status': 'pending'})
        self.assertEqual(anchor['id'], 0)
        self.archive()
        before, next_id = self.effects(), self.jobs._next_id
        result = asyncio.run(app.create_job(self.request({'title': 'Unsaved peer job', 'channel': 'peer',
                                                         'anchor_msg_id': anchor['id']})))
        self.assertEqual(getattr(result, 'status_code', 200), 409)
        self.assertEqual(self.jobs._next_id, next_id)
        self.assertEqual(self.effects(), before)

    def test_archived_rule_actions_refuse_cleanly_before_rule_or_card_mutation(self):
        cards = []
        for action in ('activate', 'draft', 'dismiss'):
            rule = self.rules.propose('Preserve exact sources ' + action, 'codex')
            cards.append((action, self.messages.add('codex', 'Proposed rule', channel='review',
                msg_type='rule_proposal', metadata={'rule_id': rule['id'], 'status': 'pending'})))
        self.archive()
        for action, card in cards:
            with self.subTest(action=action):
                before = self.effects()
                error = None
                try:
                    result = asyncio.run(app.resolve_rule_proposal(card['id'], self.request({'action': action})))
                except Exception as exc:
                    error = exc
                self.assertEqual(self.effects(), before)
                self.assertIsNone(error, 'A clean refusal must precede rule writes, not leak a store guard error.')
                self.assertEqual(getattr(result, 'status_code', 200), 409, result)
        self.broadcast.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
