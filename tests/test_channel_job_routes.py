"""Configured job API handler boundaries, without native invocation claims."""
import asyncio
from copy import deepcopy
import json
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import app
from jobs import JobStore
from channel_lifecycle import ChannelUnavailable
from tests import test_channel_message_mutations as fixture


class ChannelJobRouteTests(unittest.TestCase):
    archive = fixture.ChannelMessageMutationTests.archive
    effects = fixture.ChannelMessageMutationTests.effects

    def setUp(self):
        fixture.ChannelMessageMutationTests.setUp(self)
        self.jobs = JobStore(str(self.root / 'jobs.json'), migrate_sort_orders=False)
        self.service.jobs = self.jobs
        self.jobs.bind_channel_policy(lambda: self.service)
        self.patches.enter_context(patch.object(app, 'jobs', self.jobs))
        self.registry.seed({'claude': {'label': 'Claude'}})
        self.peer = self.registry.register('claude')

    def request(self, body=None, query=None):
        return Mock(json=AsyncMock(return_value=deepcopy(body or {})),
            body=AsyncMock(return_value=json.dumps(body or {}).encode('utf-8')),
            state=SimpleNamespace(auth_origin='operator'), query_params=query or {})

    def state(self):
        return (self.effects(), deepcopy(self.jobs._jobs), self.jobs._next_id)

    def test_archived_update_returns409_before_any_field_or_file_changes(self):
        job = self.jobs.create('Original', 'job', 'review', 'operator', status='open')
        self.archive()
        before, error, result = self.state(), None, None
        try:
            result = asyncio.run(app.update_job(job['id'], self.request({'status': 'done', 'title': 'Changed', 'assignee': 'other'})))
        except Exception as caught:
            error = caught
        self.assertIsNone(error, 'Return a clean refusal rather than leaking a store guard.')
        self.assertEqual(getattr(result, 'status_code', 200), 409)
        self.assertEqual(self.state(), before)

    def test_archived_suggestion_acceptance_refuses_before_resolution_or_dispatch(self):
        job = self.jobs.create('Original', 'job', 'review', 'operator')
        self.jobs.add_message(job['id'], self.peer['name'], 'Suggested task', msg_type='suggestion')
        self.archive()
        before, error, result = self.state(), None, None
        try:
            result = asyncio.run(app.resolve_job_message(job['id'], 0, self.request({'resolution': 'accepted'})))
        except Exception as caught:
            error = caught
        self.assertIsNone(error, 'Channel validation must precede the suggestion write and trigger.')
        self.assertEqual(getattr(result, 'status_code', 200), 409)
        self.assertEqual(self.state(), before)

    def test_archived_delete_reorder_and_post_refuse_but_thread_stays_readable(self):
        job = self.jobs.create('Retained', 'job', 'review', 'operator', status='open')
        message = self.jobs.add_message(job['id'], 'operator', 'Keep this')
        self.archive()
        before = self.state()
        calls = [lambda: app.delete_job(job['id'], self.request(query={'permanent': 'true'})),
                 lambda: app.delete_job(job['id'], self.request()),
                 lambda: app.delete_job_message(job['id'], message['id']),
                 lambda: app.reorder_jobs(self.request({'ordered_ids': [job['id']]})),
                 lambda: app.post_job_message(job['id'], self.request({'text': 'Refused'}))]
        for call in calls:
            self.assertEqual(asyncio.run(call()).status_code, 409)
            self.assertEqual(self.state(), before)
        self.assertEqual(asyncio.run(app.get_job_messages(job['id']))[0]['text'], 'Keep this')
        self.assertEqual(asyncio.run(app.get_jobs(channel='review'))[0]['id'], job['id'])
        self.assertEqual(self.state(), before)

    def test_mixed_lane_reorder_changes_only_active_records_and_update_still_works(self):
        first = self.jobs.create('First', 'job', 'peer', 'operator', status='open')
        retained = self.jobs.create('Retained', 'job', 'review', 'operator', status='open')
        last = self.jobs.create('Last', 'job', 'peer', 'operator', status='open')
        self.archive()
        before = self.jobs.get(retained['id'])
        outcome = asyncio.run(app.reorder_jobs(self.request({'ordered_ids': [first['id'], last['id']]})))
        self.assertTrue(outcome['ok'])
        self.assertEqual(self.jobs.get(retained['id']), before)
        self.assertGreater(self.jobs.get(first['id'])['sort_order'], self.jobs.get(last['id'])['sort_order'])
        updated = asyncio.run(app.update_job(first['id'], self.request({'status': 'done', 'title': 'Saved', 'assignee': 'codex'})))
        self.assertEqual((updated['status'], updated['title'], updated['assignee']), ('done', 'Saved', 'codex'))

    def test_accepted_suggestion_is_saved_before_actual_scoped_queue_enqueue(self):
        job = self.jobs.create('Active', 'job', 'peer', 'operator')
        self.jobs.add_message(job['id'], self.peer['name'], 'Suggested task', msg_type='suggestion')
        observed = []
        real = self.trigger.trigger_sync
        def enqueue(*args, **kwargs):
            self.assertTrue(self.engine._lock._is_owned())
            disk = json.loads(self.jobs._path.read_text(encoding='utf-8'))
            self.assertEqual(disk[0]['messages'][0]['resolved'], 'accepted')
            observed.append(threading.get_ident())
            return real(*args, **kwargs)
        caller = threading.get_ident()
        with patch.object(self.trigger, 'trigger_sync', side_effect=enqueue):
            result = asyncio.run(app.resolve_job_message(job['id'], 0, self.request({'resolution': 'accepted'})))
        self.assertEqual(result, {'ok': True, 'resolution': 'accepted'})
        self.assertEqual(len(observed), 1)
        self.assertNotEqual(observed[0], caller)
        records = self.trigger.queue.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['envelope']['channel'], 'peer')
        self.assertEqual(records[0]['envelope']['job_id'], job['id'])
        self.assertEqual(records[0]['envelope']['target_identity_id'], self.peer['identity_id'])

    def test_bad_resolution_and_missing_jobs_are_clean_and_have_no_effects(self):
        job = self.jobs.create('Active', 'job', 'peer', 'operator')
        self.jobs.add_message(job['id'], 'operator', 'Suggestion', msg_type='suggestion')
        before = self.state()
        self.assertEqual(asyncio.run(app.resolve_job_message(job['id'], 0, self.request({'resolution': 'invalid'}))).status_code, 400)
        self.assertEqual(asyncio.run(app.resolve_job_message(job['id'], 99, self.request())).status_code, 400)
        self.assertEqual(asyncio.run(app.update_job(999, self.request({'title': 'Missing'}))).status_code, 404)
        self.assertEqual(self.state(), before)

    def test_unreadable_jobs_return503_without_overwrite_and_catalog_failure_keeps_reads(self):
        job = self.jobs.create('Retained', 'job', 'peer', 'operator')
        self.catalog.path.write_text('{broken', encoding='utf-8')
        self.assertEqual(asyncio.run(app.update_job(job['id'], self.request({'title': 'Never'}))).status_code, 503)
        self.assertEqual(len(asyncio.run(app.get_jobs())), 1)
        self.jobs._path.write_text('{broken jobs', encoding='utf-8')
        for operation in (lambda: app.get_jobs(), lambda: app.get_job_messages(job['id']),
                          lambda: app.update_job(job['id'], self.request({'title': 'Never'}))):
            self.assertEqual(asyncio.run(operation()).status_code, 503)
            self.assertEqual(self.jobs._path.read_text(encoding='utf-8'), '{broken jobs')

    def test_gated_job_update_runs_off_loop(self):
        job = self.jobs.create('Active', 'job', 'peer', 'operator')
        entered, release = threading.Event(), threading.Event()
        real = self.jobs.update_title
        def gated(*args, **kwargs):
            entered.set()
            if not release.wait(2):
                raise AssertionError('Gate timed out')
            return real(*args, **kwargs)
        async def exercise():
            task = asyncio.create_task(app.update_job(job['id'], self.request({'title': 'Worker saved'})))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 1))
                # This coroutine advances while the worker owns the engine boundary.
                await asyncio.sleep(0)
                release.set()
                self.assertEqual((await asyncio.wait_for(task, 2))['title'], 'Worker saved')
            finally:
                release.set()
        with patch.object(self.jobs, 'update_title', side_effect=gated):
            asyncio.run(exercise())

    def test_legacy_invalid_active_sort_can_reorder_without_rewriting_inactive_sort(self):
        raw = [{'id': 1, 'channel': 'peer', 'status': 'open', 'sort_order': 'old-invalid', 'messages': []},
               {'id': 2, 'channel': 'review', 'status': 'open', 'messages': []}]
        self.jobs._path.write_text(json.dumps(raw), encoding='utf-8')
        reloaded = JobStore(str(self.jobs._path), migrate_sort_orders=False)
        reloaded.bind_channel_policy(lambda: self.service)
        self.service.jobs = reloaded
        self.archive()
        with patch.object(app, 'jobs', reloaded):
            result = asyncio.run(app.reorder_jobs(self.request({'ordered_ids': [1]})))
        self.assertEqual(result, {'ok': True, 'updated': 1})
        persisted = json.loads(reloaded._path.read_text(encoding='utf-8'))
        self.assertEqual(persisted[0]['sort_order'], 1)
        self.assertEqual(persisted[1], raw[1])

    def test_initializer_binds_job_policy_before_catalog_failure(self):
        self.jobs.create('Original', 'job', 'review', 'operator')
        path = self.root / 'channel_lifecycle.json'
        path.write_text('{broken', encoding='utf-8')
        with patch('mcp_bridge.channel_policy_getter', None), patch.object(app, 'summaries', self.summaries):
            with self.assertRaises(ChannelUnavailable):
                app._initialize_channel_lifecycle(self.root)
        self.assertIsNone(app.channel_service)
        before = self.jobs._path.read_bytes()
        with self.assertRaises(ChannelUnavailable):
            self.jobs.update_title(1, 'Must stay closed')
        self.assertEqual(self.jobs._path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
