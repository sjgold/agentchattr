"""Operator middleware and bounded retained-data responses, no native claims."""
import json
import unittest
from unittest.mock import patch
from urllib.parse import quote

import app
from tests import test_channel_routes as fixture
from jobs import JobStore
from session_store import SessionStore


class ChannelRetainedRoutesTests(unittest.TestCase):
    def setUp(self):
        fixture.ChannelRoutesTests.setUp(self)
        self.client.app.add_api_route('/api/channels/retained', app.get_retained_channel, methods=['GET'])

    def test_operator_read_is_no_store_and_anonymous_or_agent_are_refused(self):
        response = self.client.get('/api/channels/retained?channel=discussion', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.json()['channel'], 'discussion')
        self.assertEqual(self.client.get('/api/channels/retained?channel=discussion').status_code, 403)
        agent = {'Authorization': 'Bearer ' + self.f.owner['token']}
        self.assertEqual(self.client.get('/api/channels/retained?channel=discussion', headers=agent).status_code, 403)

    def test_legacy_plus_space_unicode_and_percent_names_round_trip_once(self):
        for name in ('a+b', 'a b', 'Old 資料%Name'):
            self.service.summaries.write(name, 'Exact ' + name, 'operator')
            self.service._unregistered.add(name)
        for query, name in (('a+b', 'a+b'), ('a%2Bb', 'a+b'), ('a%20b', 'a b'),
                            (quote('Old 資料%Name', safe=''), 'Old 資料%Name')):
            response = self.client.get('/api/channels/retained?channel=' + query, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['channel'], name)
            self.assertEqual(response.json()['summary']['text'], 'Exact ' + name)

    def test_raw_query_rejects_duplicates_unknown_malformed_and_oversized_values(self):
        cases = ('', '?channel=', '?channel=discussion&channel=discussion',
                 '?channel=discussion&unknown=1', '?other=discussion', '?channel=%',
                 '?channel=%2', '?channel=%ZZ', '?channel=%FF', '?channel=' + 'x' * 4100)
        before = self.service.catalog.path.read_bytes()
        for query in cases:
            with self.subTest(query=query[:70]):
                response = self.client.get('/api/channels/retained' + query, headers=self.headers)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.service.catalog.path.read_bytes(), before)

    def test_held_owners_have_null_fields_counts_and_explicit_generic_errors(self):
        jobs = JobStore(str(self.f.root / 'held_jobs.json'), migrate_sort_orders=False, hold_unreadable=True)
        jobs._path.write_bytes(b'{private broken jobs')
        self.service.jobs = jobs
        self.service.summaries.bind_channel_policy(app._channels)
        self.service.summaries._path.write_bytes(b'{private broken summaries')
        self.service.schedules.bind_channel_policy(app._channels)
        self.service.schedules._path.write_bytes(b'{private broken schedules')
        self.service.engine._store._path.write_bytes(b'{private broken sessions')
        self.service.artifacts._path.write_bytes(b'{private broken uploads')
        response = self.client.get('/api/channels/retained?channel=discussion', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        packet = response.json()
        for owner in ('jobs', 'sessions', 'schedules', 'uploads'):
            self.assertIsNone(packet[owner])
            self.assertIsNone(packet['counts'][owner])
            self.assertIsNone(packet['truncated'][owner])
            self.assertIn(owner, packet['errors'])
        self.assertIsNone(packet['summary'])
        self.assertIn('summary', packet['errors'])
        self.assertNotIn('private broken', response.text)
        self.assertNotIn(str(self.f.root), response.text)

    def test_array_caps_counts_and_metadata_do_not_include_conversation_or_input(self):
        path = self.f.root / 'bounded_jobs.json'
        path.write_text(json.dumps([{'id': i + 1, 'channel': 'discussion', 'title': f'Job {i}',
            'status': 'open', 'messages': [{'text': 'PRIVATE CONVERSATION BODY'}]}
            for i in range(125)]), encoding='utf-8')
        self.service.jobs = JobStore(str(path), migrate_sort_orders=False)
        sessions_path = self.f.root / 'bounded_sessions.json'
        sessions_path.write_text(json.dumps([{'id': i + 1, 'channel': 'discussion', 'state': 'stopped',
            'input_snapshot': {'text': 'PRIVATE FROZEN INPUT'}} for i in range(125)]), encoding='utf-8')
        self.service.engine._store = SessionStore(str(sessions_path))
        for i in range(125):
            self.service.schedules.create('PRIVATE SCHEDULE PROMPT', ['codex'],
                channel='discussion', interval_seconds=3600)
        self.service.artifacts.retain('discussion', [{'id': i, 'uid': f'uid-{i}', 'channel': 'discussion',
            'attachments': [{'name': 'kept.png', 'url': '/uploads/abcd1234.png'}]} for i in range(125)])
        response = self.client.get('/api/channels/retained?channel=discussion', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        packet = response.json()
        for owner in ('jobs', 'sessions', 'schedules', 'uploads'):
            self.assertEqual((len(packet[owner]), packet['counts'][owner], packet['truncated'][owner]), (100, 125, True))
        for body in ('PRIVATE CONVERSATION BODY', 'PRIVATE FROZEN INPUT', 'PRIVATE SCHEDULE PROMPT'):
            self.assertNotIn(body, response.text)

    def test_safe_links_only_while_original_attachment_fields_remain_inert_metadata(self):
        fields = [{'name': '<script>source</script>', 'url': '/uploads/abcd1234.png'},
                  {'name': 'external', 'url': 'https://example.com/x'},
                  {'name': 'traversal', 'url': '/uploads/../secret'},
                  {'name': 'encoded', 'url': '/uploads/%252e%252e'}]
        self.service.artifacts.retain('discussion', [{'id': 0, 'uid': 'retained-link',
            'channel': 'discussion', 'timestamp': 12, 'attachments': fields}])
        response = self.client.get('/api/channels/retained?channel=discussion', headers=self.headers)
        packet = response.json()
        self.assertEqual(packet['uploads'][0]['attachments'], fields)
        self.assertEqual(packet['uploads'][0]['safe_links'], [{'name': '<script>source</script>', 'url': '/uploads/abcd1234.png'}])

    def test_reads_have_no_file_effect_and_unknown_name_is_not_registered(self):
        before = {p.relative_to(self.f.root).as_posix(): p.read_bytes()
                  for p in self.f.root.rglob('*') if p.is_file()}
        self.assertEqual(self.client.get('/api/channels/retained?channel=discussion', headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get('/api/channels/retained?channel=never-registered', headers=self.headers).status_code, 404)
        after = {p.relative_to(self.f.root).as_posix(): p.read_bytes()
                 for p in self.f.root.rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_deleted_channel_retained_summary_is_readable_without_resurrection(self):
        self.f.messages.add('operator', 'removed chat', channel='discussion')
        self.service.summaries.write('discussion', 'Exact retained summary', 'operator')
        preview = self.service.preview('delete', 'discussion')
        self.service.apply('delete', 'discussion', request_id='a' * 32, confirmation='discussion',
                           preview_token=preview['preview_token'])
        response = self.client.get('/api/channels/retained?channel=discussion', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['state'], 'retired')
        self.assertEqual(response.json()['summary']['text'], 'Exact retained summary')
        self.assertEqual(self.f.messages.get_recent(channel='discussion'), [])

    def test_session_metadata_rejects_bool_ids_and_nonfinite_saved_input(self):
        path = self.f.root / 'bad_sessions.json'
        for raw in (b'[{"id":true,"channel":"discussion","state":"stopped"}]',
                    b'[{"id":1,"channel":"discussion","state":"stopped","audit":1e999}]'):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                self.service.engine._store = SessionStore(str(path))
                response = self.client.get('/api/channels/retained?channel=discussion', headers=self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.json()['sessions'])
                self.assertIn('sessions', response.json()['errors'])
                self.assertEqual(path.read_bytes(), raw)
