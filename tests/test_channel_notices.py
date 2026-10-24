"""Best-effort notice call sites; no background-thread/native acceptance claim."""
import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import app
import mcp_bridge
from channel_lifecycle import ChannelInactive, ChannelUnavailable
from review_brief import BriefError
from tests import test_channel_agent_paths as fixture
from tests.test_identity_contract import auth_ctx


class ChannelNoticeTests(unittest.TestCase):
    archive = fixture.ChannelAgentPathTests.archive

    def setUp(self):
        fixture.ChannelAgentPathTests.setUp(self)
        self.messages.bind_channel_policy(app._channels)

    def calls(self, fragments, expected):
        source = Path(app.__file__).read_text(encoding='utf-8')
        calls = [node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == 'store'
            and node.func.attr in ('add', 'add_notice')
            and any(fragment in ast.get_source_segment(source, node) for fragment in fragments)]
        self.assertEqual(len(calls), expected)
        return calls

    def evaluate_calls(self, calls):
        # Exact production call expressions, with local-value fixtures. This
        # exercises their bound-store behavior, not the surrounding thread/UI.
        values = dict(store=self.messages, name='claude', agent_name='claude', sender='operator',
            channel='review', _agent_last_channel={'claude': 'review'}, _last_active_channel='review',
            router=self.router, target='claude', mentions='@claude', routing_scope={}, theme='source',
            color_parts='claude=gray', prompts={'haiku': 'literal prompt'}, form='haiku',
            created_by='operator', title='Retained job', result={'id': 8},
            tmpl={'name': 'Review'}, template_id='review', goal='Preserve source',
            session={'id': self.session_id}, mention_str='@claude')
        for node in calls:
            eval(compile(ast.Expression(node), app.__file__, 'eval'), values)

    def test_best_effort_notice_drops_inactive_without_ids_or_callbacks(self):
        self.archive()
        before = self.messages._next_id
        with self.assertLogs('store', level='INFO'):
            self.assertIsNone(self.messages.add_notice('system', 'Do not save', channel='review'))
        self.assertEqual(self.messages._next_id, before)
        self.assertEqual(self.messages.get_recent(channel='review'), [])
        with self.assertRaises(ChannelInactive):
            self.messages.add('operator', 'Ordinary input is still refused', channel='review')

    def test_phase_banner_after_archive_drops_without_raising(self):
        run = self.engine.start_session('review', 'review',
            {'reviewer': 'human', 'editor': 'human'}, 'operator')
        self.archive()
        self.engine.emit_current_phase_banner(run)
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_three_background_leave_call_sites_drop_archived_notice(self):
        calls = self.calls(['disconnected'], 3)
        self.archive()
        self.evaluate_calls(calls)
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_background_recovery_call_drops_when_catalog_is_unavailable(self):
        calls = self.calls(['auto-recovered.'], 1)
        with patch.object(app, 'channel_service', None):
            self.evaluate_calls(calls)
        self.assertEqual(self.messages.get_recent(), [])

    def test_router_resume_guard_and_offline_notice_call_sites_drop(self):
        calls = self.calls(['only humans can /continue', 'Routing resumed by',
                            'agent-to-agent hops reached', 'appears offline'], 4)
        self.archive()
        self.evaluate_calls(calls)
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_derived_slash_prompts_drop_when_callback_loses_active_channel(self):
        calls = self.calls(['Time for a roast review', 'Art challenge!',
                            'Hat making time!', '{prompts[form]}'], 4)
        self.archive()
        self.evaluate_calls(calls)
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_job_and_session_breadcrumb_call_sites_drop_without_side_effects(self):
        calls = self.calls(['Job created:', 'Session started:', 'Requested session draft from'], 3)
        self.archive()
        self.evaluate_calls(calls)
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_mcp_join_keeps_presence_reply_when_notice_policy_is_unavailable(self):
        with patch.object(app, 'channel_service', None):
            result = mcp_bridge.chat_join(self.peer['name'], ctx=auth_ctx(self.peer['token']))
        self.assertIn('Joined.', result)
        self.assertEqual(self.messages.get_recent(), [])

    def test_complete_and_interrupt_callbacks_still_broadcast_without_history_edits(self):
        self.messages.add('system', 'Peer history', channel='peer')  # Exercise truthy output_message_id.
        message = self.messages.add('claude', 'Retained result', channel='review',
                                    metadata={'existing': 'retained'})
        before = deepcopy(message)
        self.archive()
        async def observe():
            callback = AsyncMock()
            with patch.object(app, '_event_loop', asyncio.get_running_loop()), \
                 patch.object(app, 'broadcast_session', callback), \
                 patch.object(app, '_turn_monitor_loop', None):
                for action in ('complete', 'interrupt'):
                    run = self.sessions.get(self.session_id)
                    run.update(channel='review', output_message_id=message['id'], state='complete')
                    app._on_session_change(action, run)
                await asyncio.sleep(0)
                self.assertEqual(callback.await_count, 2)
        asyncio.run(observe())
        self.assertEqual(self.messages.get_snapshot(message['id']), before)
        self.assertEqual(self.messages.get_recent(channel='review'), [before])

    def test_context_preparation_error_stays_interrupted_after_notice_is_refused(self):
        def failure(*args, **kwargs):
            self.archive()
            raise BriefError('fixture context error')
        with patch('review_brief.build_brief', side_effect=failure):
            result = self.engine.start_session('review', 'review',
                {'reviewer': 'human', 'editor': 'human'}, 'operator')
        self.assertIsNone(result)
        self.assertEqual(self.sessions.list_all(channel='review')[0]['state'], 'interrupted')
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_dispatch_error_stays_interrupted_after_notice_is_refused(self):
        def failure(*args, **kwargs):
            self.archive()
            raise OSError('fixture queue error')
        with patch.object(self.trigger, 'trigger_sync', side_effect=failure):
            result = self.engine.start_session('review', 'review',
                {'reviewer': 'claude', 'editor': 'human'}, 'operator')
        self.assertIsNone(result)
        self.assertEqual(self.sessions.list_all(channel='review')[0]['state'], 'interrupted')
        self.assertEqual(self.messages.get_recent(channel='review'), [])

    def test_active_notice_still_publishes_and_storage_errors_remain_visible(self):
        observed = []
        self.messages.on_message(lambda msg: observed.append(msg['id']))
        saved = self.messages.add_notice('system', 'Visible notice', channel='peer')
        self.assertEqual(observed, [saved['id']])
        self.assertEqual(self.messages.get_snapshot(saved['id']), saved)
        with patch.object(self.messages, 'add', side_effect=OSError('real storage failure')):
            with self.assertRaises(OSError):
                self.messages.add_notice('system', 'must fail', channel='peer')


if __name__ == '__main__':
    unittest.main()
