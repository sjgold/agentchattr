"""Schedule public handler and write-ahead tick seams, without native claims."""
import asyncio
from copy import deepcopy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid
import unittest
from unittest.mock import AsyncMock, Mock, patch

import app
import schedules as schedule_module
from schedules import ScheduleStore
from tests import test_channel_message_mutations as fixture


class ChannelScheduleRouteTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelMessageMutationTests.setUp(self)
        self.schedules.bind_channel_policy(lambda: self.service)

    def request(self, **fields):
        body = dict(prompt='Read exact source', targets=['helper'], spec='every 1h', channel='review')
        body.update(fields)
        return Mock(json=AsyncMock(return_value=body))

    def effects(self):
        return (fixture.ChannelMessageMutationTests.effects(self), deepcopy(self.schedules._schedules))

    def test_archived_schedule_create_refuses_before_saved_row_or_callback(self):
        self.catalog.set_state('review', 'archived', expected_revision=0)
        changed = Mock()
        self.schedules.on_change(changed)
        before = self.effects()
        response = asyncio.run(app.create_schedule(self.request()))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.effects(), before)
        changed.assert_not_called()

    def test_archived_schedule_delete_refuses_actual_stored_channel_before_effects(self):
        row = self.schedules.create('Keep', ['helper'], channel='review', interval_seconds=3600)
        self.catalog.set_state('review', 'archived', expected_revision=0)
        before = self.effects()
        response = asyncio.run(app.delete_schedule(row['id']))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.effects(), before)

    def due(self, channel='review', one_shot=False):
        with patch('schedules.time.time', return_value=100):
            return self.schedules.create('Scheduled work', ['helper'], channel=channel,
                interval_seconds=60, send_at=101, one_shot=one_shot)

    def tick(self, publisher, now=200):
        with patch.object(app, '_publish_operator_message', publisher), patch('schedules.time.time', return_value=now):
            app._run_schedule_tick()

    def test_failed_first_persist_sends_nothing_and_leaves_due_row_while_peer_progresses(self):
        first, peer = self.due(), self.due('peer')
        writer = schedule_module.atomic_json
        writes = []
        def fail_first(path, rows):
            writes.append(1)
            if len(writes) == 1:
                raise OSError('PRIVATE initial write')
            return writer(path, rows)
        published = Mock()
        with patch('schedules.atomic_json', side_effect=fail_first):
            self.tick(published)
        self.assertEqual(published.call_count, 1)
        self.assertEqual(published.call_args.kwargs['channel'], 'peer')
        self.assertEqual(self.schedules.get(first['id'])['next_run'], 101)
        self.assertIsNone(self.schedules.get(first['id'])['last_run'])
        self.assertEqual(self.schedules.get(peer['id'])['next_run'], 260)
        self.tick(published, now=201)
        self.assertEqual(published.call_count, 2)
        self.assertEqual(self.schedules.get(first['id'])['last_run'], 201)

    def test_crash_after_write_ahead_before_publication_misses_one_shot_without_replay(self):
        row = self.due(one_shot=True)
        class SimulatedProcessCrash(BaseException):
            pass
        publisher = Mock(side_effect=SimulatedProcessCrash)
        with self.assertRaises(SimulatedProcessCrash):
            self.tick(publisher)
        persisted = json.loads(self.schedules._path.read_text(encoding='utf-8'))[0]
        self.assertFalse(persisted['active'])
        self.assertEqual(persisted['last_attempt_at'], 200)
        self.assertIsNone(persisted['last_run'])
        reloaded = ScheduleStore(str(self.schedules._path), configured=True)
        reloaded.bind_channel_policy(lambda: self.service)
        self.service.schedules = reloaded
        retry = Mock()
        with patch.object(app, 'schedules', reloaded):
            self.tick(retry, now=201)
        retry.assert_not_called()
        self.assertIsNone(reloaded.get(row['id'])['last_run'])

    def test_post_publication_save_failure_keeps_reservation_and_does_not_repeat(self):
        row = self.due()
        writer = schedule_module.atomic_json
        def fail_success(path, rows):
            if any(item.get('last_run') == 200 for item in rows):
                raise OSError('PRIVATE post-publication write')
            return writer(path, rows)
        publisher = Mock()
        with patch('schedules.atomic_json', side_effect=fail_success):
            self.tick(publisher)
        self.assertEqual(publisher.call_count, 1)
        saved = self.schedules.get(row['id'])
        self.assertEqual(saved['next_run'], 260)
        self.assertEqual(saved['last_attempt_at'], 200)
        self.assertIsNone(saved['last_run'])
        self.tick(publisher, now=201)
        self.assertEqual(publisher.call_count, 1)

    def test_successful_one_shot_delete_failure_leaves_inactive_completed_row(self):
        row = self.due(one_shot=True)
        writer = schedule_module.atomic_json
        def fail_delete(path, rows):
            if not rows:
                raise OSError('PRIVATE delete failure')
            return writer(path, rows)
        publisher = Mock()
        with patch('schedules.atomic_json', side_effect=fail_delete):
            self.tick(publisher)
        self.assertFalse(self.schedules.get(row['id'])['active'])
        self.assertEqual(self.schedules.get(row['id'])['last_run'], 200)
        self.tick(publisher, now=201)
        self.assertEqual(publisher.call_count, 1)

    def test_unexpected_first_publication_error_records_internal_and_peer_still_fires(self):
        first, peer = self.due(), self.due('peer')
        def publish(**fields):
            if fields['channel'] == 'review':
                raise RuntimeError('PRIVATE source should not echo')
        with patch.object(app, 'log') as log:
            self.tick(Mock(side_effect=publish))
        self.assertEqual(self.schedules.get(first['id'])['last_error'], 'internal')
        self.assertEqual(self.schedules.get(peer['id'])['last_run'], 200)
        self.assertNotIn('PRIVATE', str(log.mock_calls))
        self.assertNotIn('PRIVATE', self.schedules._path.read_text(encoding='utf-8'))

    def test_partial_target_enqueue_is_retained_without_same_interval_resend(self):
        self.registry.seed({'helper': {'label': 'Helper'}})
        owner = self.registry.register('helper')
        row = self.due()
        def partial_publish(**fields):
            self.trigger.trigger_sync(owner['name'], 'First target already admitted', channel='review')
            raise OSError('Later target failed')
        publisher = Mock(side_effect=partial_publish)
        self.tick(publisher)
        records = self.trigger.queue.records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['envelope']['target_identity_id'], owner['identity_id'])
        self.assertEqual(self.schedules.get(row['id'])['last_error'], 'delivery_unconfirmed')
        self.tick(publisher, now=201)
        self.assertEqual(publisher.call_count, 1)
        self.assertEqual(self.trigger.queue.records(), records)

    def test_active_crud_worker_and_inactive_reads_keep_existing_payloads(self):
        caller, calls = threading.get_ident(), []
        create = self.schedules.create
        def checked(*args, **kwargs):
            calls.append(threading.get_ident())
            self.assertTrue(self.engine._lock._is_owned())
            return create(*args, **kwargs)
        with patch.object(self.schedules, 'create', side_effect=checked):
            response = asyncio.run(app.create_schedule(self.request(channel='peer')))
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(calls, [caller])
        row = json.loads(response.body)
        toggled = asyncio.run(app.toggle_schedule(row['id']))
        self.assertFalse(json.loads(toggled.body)['active'])
        self.assertEqual(json.loads(asyncio.run(app.delete_schedule(row['id'])).body), {'ok': True})
        retained = self.due()
        self.catalog.set_state('review', 'archived', expected_revision=0)
        self.assertEqual(asyncio.run(app.toggle_schedule(retained['id'])).status_code, 409)
        self.assertEqual(asyncio.run(app.get_schedules())[0]['id'], retained['id'])
        self.catalog.path.write_text('{broken', encoding='utf-8')
        self.assertEqual(asyncio.run(app.create_schedule(self.request())).status_code, 503)
        self.assertEqual(asyncio.run(app.get_schedules())[0]['id'], retained['id'])

    def test_fire_holds_archive_until_publish_and_settlement_finish(self):
        row = self.due()
        entered, release, checking = threading.Event(), threading.Event(), threading.Event()
        def publisher(**fields):
            self.assertTrue(self.engine._lock._is_owned())
            self.assertTrue(self.catalog._lock._is_owned())
            entered.set()
            self.assertTrue(release.wait(2))
        def archive():
            checking.set()
            preview = self.service.preview('archive', 'review')
            return self.service.apply('archive', 'review', request_id=uuid.uuid4().hex,
                confirmation='review', preview_token=preview['preview_token'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.tick, Mock(side_effect=publisher))
            try:
                self.assertTrue(entered.wait(2))
                second = pool.submit(archive)
                self.assertTrue(checking.wait(2))
                self.assertFalse(second.done())
            finally:
                release.set()
            first.result(2)
            second.result(2)
        self.assertEqual(self.catalog.snapshot()['channels']['review'], 'archived')
        self.assertEqual(self.schedules.get(row['id'])['last_run'], 200)
        later = Mock()
        self.tick(later, now=400)
        later.assert_not_called()

    def test_configured_nonpositive_cadence_cannot_reserve_an_immediately_due_retry(self):
        before = self.effects()
        for interval in (-60, 0, True, float('inf')):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                self.schedules.create('Invalid repeat', ['helper'], channel='review', interval_seconds=interval)
            self.assertEqual(self.effects(), before)
        raw = [{'id': 'bad-cadence', 'channel': 'review', 'targets': ['helper'],
                'next_run': 101, 'active': True, 'one_shot': False, 'interval_seconds': -60}]
        path = self.root / 'invalid-cadence.json'
        path.write_text(json.dumps(raw), encoding='utf-8')
        closed = ScheduleStore(str(path), configured=True)
        from channel_lifecycle import ChannelUnavailable
        with self.assertRaises(ChannelUnavailable):
            closed.run_due()
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), raw)

    def test_cadence_computation_failure_leaves_memory_and_disk_unmodified(self):
        row = self.due()
        for call in (lambda: self.schedules.begin_attempt(row['id'], now=200),
                     lambda: self.schedules.mark_run(row['id'])):
            before = self.effects()
            with patch('schedules.compute_next_run', side_effect=ValueError('Invalid stored cadence')):
                with self.assertRaises(ValueError):
                    call()
            self.assertEqual(self.effects(), before)

    def test_configured_oversize_json_numbers_hold_without_constructor_overflow_or_reset(self):
        path = self.root / 'oversize-number.json'
        raw = [{'id': 'large-number', 'channel': 'review', 'targets': ['helper'],
                'next_run': 10 ** 400, 'active': True, 'one_shot': False}]
        path.write_text(json.dumps(raw), encoding='utf-8')
        before = path.read_bytes()
        closed, error = None, None
        try:
            closed = ScheduleStore(str(path), configured=True)
        except Exception as caught:
            error = caught
        self.assertIsNone(error, 'Unreadable schedule data must hold the store, not abort startup.')
        from channel_lifecycle import ChannelUnavailable
        with self.assertRaises(ChannelUnavailable):
            closed.list_all()
        self.assertEqual(path.read_bytes(), before)

    def test_nonfuture_reservation_logs_invalid_cadence_without_claiming_a_save_failure(self):
        self.due()
        before = self.effects()
        publisher = Mock()
        with patch.object(app, 'log') as log, patch('schedules.compute_next_run', return_value=200):
            self.tick(publisher, now=200)
        publisher.assert_not_called()
        self.assertIn('cadence', str(log.mock_calls).lower())
        self.assertNotIn('could not be saved', str(log.mock_calls))
        self.assertEqual(self.effects(), before)


if __name__ == '__main__':
    unittest.main()
