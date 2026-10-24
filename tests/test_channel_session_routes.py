"""Session-primary public handler seams with real catalog/store effects."""
import asyncio
from copy import deepcopy
import json
import threading
import uuid
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import app
from store import MessageStore
from tests import test_channel_message_mutations as fixture


class ChannelSessionRouteTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelMessageMutationTests.setUp(self)
        self.template = {'id': 'channel-review', 'name': 'Channel review', 'roles': ['reader'],
            'phases': [{'name': 'Read', 'participants': ['reader'], 'prompt': 'Inspect source.', 'is_output': True}]}
        self.sessions.save_custom_template(self.template)

    def request(self, body):
        return Mock(body=AsyncMock(return_value=json.dumps(body).encode('utf-8')),
            state=SimpleNamespace(auth_origin='operator'))

    def start_body(self, channel='review', **fields):
        return dict(template_id='channel-review', channel=channel, cast={'reader': 'Human'},
                    started_by='operator', input_text='Exact source', **fields)

    def effects(self):
        return (fixture.ChannelMessageMutationTests.effects(self), self.sessions._next_id,
                deepcopy(self.sessions._templates), self.sessions.list_all())

    def test_archived_destination_start_refuses_before_any_session_template_brief_or_queue_effect(self):
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.effects()
        response = asyncio.run(app.start_session(self.request(self.start_body())))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.body)['reason'], 'channel_inactive')
        self.assertEqual(self.effects(), before)

    def test_active_destination_cannot_register_template_from_archived_source_draft(self):
        self.messages.add('operator', 'Peer history', channel='peer')
        template = dict(deepcopy(self.template), id='from-archived-draft')
        card = self.messages.add('operator', 'Draft', msg_type='session_draft', channel='review',
                                 metadata={'template': template})
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.effects()
        response = asyncio.run(app.start_session(self.request(self.start_body('peer', draft_message_id=card['id']))))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.body)['reason'], 'channel_inactive')
        self.assertEqual(self.effects(), before)
        self.assertNotIn(template['id'], self.sessions._templates)

    def stopped_parent(self):
        parent = self.engine.start_session('channel-review', 'review', {'reader': 'Human'},
                                          'operator', input_text='Original source')
        self.engine.stop_session(parent['id'])
        self.engine.reconcile_stops()
        return self.sessions.get(parent['id'])

    def test_draft_zero_registers_template_without_changing_card_and_checks_source_when_archived(self):
        template = dict(deepcopy(self.template), id='draft-zero')
        card = self.messages.add('operator', 'Draft zero', msg_type='session_draft', channel='review',
                                 metadata={'template': template})
        self.assertEqual(card['id'], 0)
        snapshot = self.messages.get_snapshot(0)
        response = asyncio.run(app.start_session(self.request(self.start_body(draft_message_id=0))))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body)['template_id'], 'draft-zero')
        self.assertEqual(self.messages.get_snapshot(0), snapshot)
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.effects()
        response = asyncio.run(app.start_session(self.request(self.start_body('peer', draft_message_id=0))))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.effects(), before)

    def test_lifecycle_reason_is_distinct_from_unchanged_existing_session_conflict(self):
        response = asyncio.run(app.start_session(self.request(self.start_body())))
        self.assertEqual(response.status_code, 200)
        conflict = asyncio.run(app.start_session(self.request(self.start_body())))
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(json.loads(conflict.body), {'error': 'could not start session (one may already be active)'})
        self.catalog.set_state('review', 'archived', expected_revision=0)
        inactive = asyncio.run(app.start_session(self.request(self.start_body())))
        self.assertEqual(inactive.status_code, 409)
        self.assertEqual(json.loads(inactive.body)['reason'], 'channel_inactive')

    def test_retired_stopped_parent_refuses_restart_with_no_child_or_general_redirect(self):
        parent = self.stopped_parent()
        preview = self.service.preview('delete', 'review')
        self.service.apply('delete', 'review', request_id=uuid.uuid4().hex,
            confirmation='review', preview_token=preview['preview_token'])
        self.assertEqual(self.catalog.snapshot()['channels']['review'], 'retired')
        before = self.effects()
        response = asyncio.run(app.correct_and_restart_session(parent['id'], self.request(
            {'input_text': 'Actual correction', 'request_id': uuid.uuid4().hex})))
        self.assertEqual(response.status_code, 409)
        self.assertIn('retired', json.loads(response.body)['error'])
        self.assertEqual(json.loads(response.body)['reason'], 'channel_inactive')
        self.assertEqual(self.effects(), before)
        self.assertEqual(self.sessions.get(parent['id'])['channel'], 'review')

    def test_archived_parent_and_prepared_child_routes_fence_even_unbound_engine(self):
        parent = self.stopped_parent()
        child = self.engine.correct_and_restart(parent['id'], 'Actual correction', 'prepare-child')
        self.engine.bind_channel_policy(lambda: self.service)
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.effects()
        operations = [lambda: app.correct_and_restart_session(parent['id'], self.request(
                          {'input_text': 'Actual correction', 'request_id': 'prepare-child'})),
                      lambda: app.prepare_restart_contexts(child['id'], self.request({'context_request_id': 'repair'})),
                      lambda: app.activate_corrected_session(child['id'], self.request({}))]
        # App ingress cannot rely on the later engine-factory binding tranche.
        with patch.object(self.engine, '_channel_policy_getter', None):
            for call in operations:
                response = asyncio.run(call())
                self.assertEqual(response.status_code, 409)
                self.assertEqual(json.loads(response.body)['reason'], 'channel_inactive')
                self.assertIn('Reopen', json.loads(response.body)['error'])
                self.assertEqual(self.effects(), before)

    def test_unavailable_catalog_and_bad_draft_inputs_have_clean_no_effect_errors(self):
        for value, expected in ((False, 400), (-1, 400), ('0', 400), (999, 404)):
            before = self.effects()
            response = asyncio.run(app.start_session(self.request(self.start_body(draft_message_id=value))))
            self.assertEqual(response.status_code, expected)
            self.assertEqual(self.effects(), before)
        self.catalog.path.write_text('{broken', encoding='utf-8')
        before = self.effects()
        response = asyncio.run(app.start_session(self.request(self.start_body())))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.body)['reason'], 'channel_unavailable')
        self.assertEqual(self.effects(), before)

    def test_start_worker_owns_boundary_and_keeps_event_loop_responsive(self):
        entered, release = threading.Event(), threading.Event()
        start = self.engine.start_session
        caller = threading.get_ident()
        def gated(*args, **kwargs):
            self.assertNotEqual(threading.get_ident(), caller)
            self.assertTrue(self.engine._lock._is_owned())
            self.assertTrue(self.catalog._lock._is_owned())
            entered.set()
            self.assertTrue(release.wait(2))
            return start(*args, **kwargs)
        async def exercise():
            task = asyncio.create_task(app.start_session(self.request(self.start_body())))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 1))
                await asyncio.sleep(0)
                release.set()
                self.assertEqual((await asyncio.wait_for(task, 2)).status_code, 200)
            finally:
                release.set()
        with patch.object(self.engine, 'start_session', side_effect=gated):
            asyncio.run(exercise())

    def test_legacy_draft_invalid_channel_name_returns400_without_registering_template(self):
        legacy = MessageStore(str(self.root / 'legacy-messages.jsonl'))
        template = dict(deepcopy(self.template), id='bad-channel-draft')
        card = legacy.add('operator', 'Legacy draft', channel='Bad/old', metadata={'template': template})
        before, error, response = self.effects(), None, None
        with patch.object(app, 'store', legacy):
            try:
                response = asyncio.run(app.start_session(self.request(self.start_body('peer', draft_message_id=card['id']))))
            except Exception as caught:
                error = caught
        self.assertIsNone(error, 'Map invalid legacy channel grammar to a clean validation response.')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('reason', json.loads(response.body))
        self.assertEqual(self.effects(), before)


if __name__ == '__main__':
    unittest.main()
