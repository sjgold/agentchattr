"""Catalog display authority survives an owner-local storage hold."""
import json
import unittest
import uuid

import app
from tests import test_channel_routes as fixture


class ChannelCatalogOwnerTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelRoutesTests.setUp(self)

    def hold(self, owner):
        if owner == 'jobs':
            self.service.jobs.bind_channel_policy(app._channels)
            path = self.service.jobs._path
        elif owner == 'schedules':
            self.service.schedules.bind_channel_policy(app._channels)
            path = self.service.schedules._path
        elif owner == 'summaries':
            self.service.summaries.bind_channel_policy(app._channels)
            path = self.service.summaries._path
        elif owner == 'sessions':
            path = self.service.engine._store._path
        elif owner == 'queue':
            path = self.service.queue.path
        else:
            path = self.service.artifacts._path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'{private unreadable owner')

    def row(self, packet, channel='discussion'):
        return next(row for row in packet['channels'] if row['name'] == channel)

    def test_held_jobs_catalog_is_200_with_active_authority_and_explicit_null(self):
        self.hold('jobs')
        response = self.client.get('/api/channels', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        row = self.row(response.json())
        self.assertEqual(row['state'], 'active')
        self.assertIsNone(row['counts']['jobs'])
        self.assertIn('jobs', row['errors'])

    def test_healthy_catalog_schema_has_queue_count_and_owner_errors(self):
        response = self.client.get('/api/channels', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        row = self.row(response.json())
        self.assertIn('errors', row)
        self.assertEqual(row['errors'], {})
        self.assertEqual(set(row['counts']), {'messages', 'todos', 'jobs', 'schedules', 'sessions', 'summaries', 'uploads', 'queue'})
        self.assertEqual(row['counts']['queue'], 0)

    def test_each_held_owner_stays_local_while_strict_actions_refuse_and_peer_posts(self):
        for owner in ('jobs', 'schedules', 'summaries', 'sessions', 'queue', 'uploads'):
            with self.subTest(owner=owner):
                case = ChannelCatalogOwnerTests()
                case.setUp()
                try:
                    previews = {op: case.client.post('/api/channels/preview', headers=case.headers,
                        json={'op': op, 'channel': 'discussion'}).json() for op in ('archive', 'delete')}
                    baseline = case.row(case.client.get('/api/channels', headers=case.headers).json())
                    case.hold(owner)
                    response = case.client.get('/api/channels', headers=case.headers)
                    self.assertEqual(response.status_code, 200, response.text)
                    row = case.row(response.json())
                    self.assertEqual(row['state'], 'active')
                    self.assertIsNone(row['counts'][owner])
                    self.assertEqual(set(row['errors']), {owner})
                    for key, value in baseline['counts'].items():
                        if key != owner:
                            self.assertEqual(row['counts'][key], value, (owner, key))
                    self.assertEqual(row['overdue_schedules'], None if owner == 'schedules' else baseline['overdue_schedules'])
                    before = {path.relative_to(case.f.root).as_posix(): path.read_bytes()
                              for path in case.f.root.rglob('*') if path.is_file()}
                    for op in ('archive', 'delete'):
                        checked = case.client.post('/api/channels/preview', headers=case.headers,
                            json={'op': op, 'channel': 'discussion'})
                        self.assertEqual(checked.status_code, 503, (owner, op, checked.text))
                        applied = case.client.post('/api/channels/apply', headers=case.headers,
                            json={'op': op, 'channel': 'discussion', 'confirmation': 'discussion',
                                  'request_id': uuid.uuid4().hex, 'preview_token': previews[op]['preview_token']})
                        self.assertEqual(applied.status_code, 503, (owner, op, applied.text))
                    after = {path.relative_to(case.f.root).as_posix(): path.read_bytes()
                             for path in case.f.root.rglob('*') if path.is_file()}
                    self.assertEqual(after, before)
                    app._publish_operator_message(sender='operator', text='Healthy peer chat',
                                                  selected_recipients=[], channel='elsewhere')
                    self.assertEqual(case.f.messages.get_recent(channel='elsewhere')[-1]['text'], 'Healthy peer chat')
                    self.assertNotIn('private unreadable', response.text)
                    self.assertNotIn(str(case.f.root), response.text)
                finally:
                    case.doCleanups()

    def test_unreadable_catalog_itself_still_returns_503(self):
        self.service.catalog.path.write_bytes(b'{broken catalog')
        response = self.client.get('/api/channels', headers=self.headers)
        self.assertEqual(response.status_code, 503)
