"""Runtime routing fences, with real stores and no native workers/providers."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

import app
import mcp_bridge
from queue_coordinator import allowed_review_dispatch_ids
from jobs import JobStore
from router import Router
from tests import test_session_events as fixture


class RecipientRuntimeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.SessionEventTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.router = Router(['codex', 'claude'], default_mention='all',
                             online_checker=lambda: {'codex', 'claude'})
        self.jobs = JobStore(str(self.f.root / 'jobs.json'))

    def patched(self, agents=None):
        stack = ExitStack()
        for name, value in (('registry', self.f.registry), ('session_engine', self.f.engine),
                            ('session_store', self.f.sessions), ('router', self.router),
                            ('agents', agents or self.f.trigger), ('store', self.f.messages),
                            ('jobs', self.jobs), ('config', {'agents': {}})):
            stack.enter_context(patch.object(app, name, value))
        stack.enter_context(patch.object(app, 'broadcast', AsyncMock()))
        stack.enter_context(patch.object(app, 'broadcast_status', AsyncMock()))
        stack.enter_context(patch.object(mcp_bridge, 'is_online', return_value=True))
        return stack

    def request(self, body):
        return Mock(json=AsyncMock(return_value=body))

    def test_router_uses_authored_addresses_and_never_human_default(self):
        self.assertEqual(self.router.parse_mentions('"@codex" `@claude` @unknown'), [])
        self.router._get_ch('general').update(paused=True, hop_count=9, guard_emitted=True)
        self.assertEqual(self.router.get_targets('operator', '@unknown'), [])
        self.assertEqual(self.router._get_ch('general'),
                         {'paused': False, 'hop_count': 0, 'guard_emitted': False})
        self.assertEqual(self.router.get_targets('operator', 'plain shared note'), [])
        self.assertEqual(self.router.parse_mentions('@claude @all @codex'), ['claude', 'codex'])

    def test_registry_alias_only_resolves_a_unique_active_member(self):
        self.f.registry.rename('claude', 'claude-prime')
        self.assertEqual(self.f.registry.resolve_to_instances('claude'), ['claude-prime'])
        second = self.f.registry.register('claude')
        self.assertEqual(self.f.registry.resolve_to_instances('claude'), [])
        self.assertEqual(self.f.registry.resolve_to_instances(second['name']), [second['name']])
        self.assertEqual(self.f.registry.resolve_to_instances('operator'), ['operator'])

    def test_finite_large_integer_timestamp_does_not_crash_queue_ordering(self):
        run = self.f.current()
        run['active_invocation']['monitoring']['created_at'] = 10 ** 1000
        self.assertEqual(allowed_review_dispatch_ids([run], self.f.owner['identity_id']),
                         {run['active_invocation']['dispatch_id']})

    def test_channel_predicate_covers_nonterminal_states_without_invocation(self):
        for state in ('active', 'waiting', 'paused', 'awaiting_input', 'stalled', 'retrying', 'interrupted', 'prepared'):
            self.f.sessions._event_update(self.f.session_id,
                lambda run: run.update(state=state, active_invocation=None, dispatch_eligible=False))
            with self.subTest(state=state):
                self.assertTrue(self.f.engine.has_nonterminal_review('general'))
                self.assertFalse(self.f.engine.has_nonterminal_review('elsewhere'))
        self.f.sessions._event_update(self.f.session_id, lambda run: run.update(stop_id='a' * 32))
        self.assertFalse(self.f.engine.has_nonterminal_review('general'))

    def test_agent_mentions_in_every_nonterminal_state_never_create_dispatches(self):
        for state in ('active', 'waiting', 'paused', 'awaiting_input', 'stalled', 'retrying', 'interrupted', 'prepared'):
            self.f.sessions._event_update(self.f.session_id, lambda run: run.update(state=state))
            before = self.f.trigger.queue.path.read_bytes()
            channels = deepcopy(self.router._channels)
            with self.subTest(state=state), self.patched():
                asyncio.run(app._handle_new_message({'sender': 'claude', 'text': '@codex follow up',
                    'channel': 'general', 'type': 'chat'}))
                self.assertEqual(self.f.trigger.queue.path.read_bytes(), before)
                self.assertEqual(self.router._channels, channels)

    def test_agent_slash_is_literal_and_draft_card_stays_display_only(self):
        with self.patched():
            before = self.f.messages.get_recent(100)
            asyncio.run(app._handle_new_message({'sender': 'claude', 'text': '/roastreview',
                'channel': 'general', 'type': 'chat'}))
            self.assertEqual(self.f.messages.get_recent(100), before)
            template = dict(self.f.template, name='New proposal')
            before_ledger = self.f.trigger.queue.path.read_bytes()
            asyncio.run(app._handle_new_message({'sender': 'claude',
                'text': '```session\n' + json.dumps(template) + '\n```', 'channel': 'general', 'type': 'chat'}))
            self.assertEqual(self.f.trigger.queue.path.read_bytes(), before_ledger)
            self.assertTrue(any(m['type'] == 'session_draft' for m in self.f.messages.get_recent(100)))

    def test_ambiguous_conversion_returns_conflict_with_candidates(self):
        self.f.registry.register('claude')
        candidates = sorted(r['name'] for r in self.f.registry.get_all().values() if r['base'] == 'claude')
        agents = Mock(is_available=Mock(return_value=True), trigger=AsyncMock())
        with self.patched(agents):
            result = asyncio.run(app.trigger_agent_silent(self.request({'agent': 'claude', 'message': 'convert'})))
        self.assertEqual(getattr(result, 'status_code', None), 409)
        self.assertEqual(json.loads(result.body)['candidates'], candidates)
        agents.trigger.assert_not_awaited()

    def test_ambiguous_channel_family_wakes_nobody(self):
        self.f.registry.register('claude')
        agents = Mock(is_available=Mock(return_value=True), trigger=AsyncMock())
        with self.patched(agents):
            asyncio.run(app._handle_new_message({'sender': 'operator', 'text': '@claude hello',
                'channel': 'discussion', 'type': 'chat'}))
        agents.trigger.assert_not_awaited()

    def test_app_job_agent_guard_and_ambiguous_family_do_not_wake(self):
        job = self.jobs.create('Review task', 'job', 'general', 'operator')
        agents = Mock(is_available=Mock(return_value=True), trigger=AsyncMock())
        with self.patched(agents):
            asyncio.run(app.post_job_message(job['id'], self.request({'sender': 'claude', 'text': '@codex hello'})))
        agents.trigger.assert_not_awaited()
        self.f.registry.register('claude')
        with self.patched(agents):
            asyncio.run(app.post_job_message(job['id'], self.request({'sender': 'operator', 'text': '@claude hello'})))
        agents.trigger.assert_not_awaited()

    def test_mcp_job_agent_guard_and_ambiguous_family_do_not_wake(self):
        agents = Mock(is_available=Mock(return_value=True))
        job = self.jobs.create('Review task', 'job', 'general', 'operator')
        def send(channel, text):
            with ExitStack() as stack:
                for name, value in (('registry', self.f.registry), ('session_engine', self.f.engine),
                                    ('jobs', self.jobs), ('router', self.router), ('agents', agents)):
                    stack.enter_context(patch.object(mcp_bridge, name, value))
                stack.enter_context(patch.object(mcp_bridge, '_authenticated_instance', return_value=self.f.owner))
                stack.enter_context(patch.object(mcp_bridge, '_resolve_tool_identity', return_value=('codex', None)))
                return mcp_bridge.chat_send('codex', text, job_id=job['id'], channel=channel)
        self.assertIn('Sent', send('general', '@claude follow up'))
        agents.trigger_sync.assert_not_called()
        self.f.registry.register('claude')
        self.jobs._jobs[0]['channel'] = 'discussion'
        self.assertIn('Sent', send('discussion', '@claude follow up'))
        agents.trigger_sync.assert_not_called()
