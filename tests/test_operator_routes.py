"""Operator routing through real middleware; no native worker/provider claims."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import inspect
import io
import json
import unittest
import zipfile
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
import app
import archive
import mcp_bridge
from jobs import JobStore
from router import Router
from store import _OPERATOR_PUBLICATION
from tests import test_session_events as fixture


class OperatorRoutesTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.SessionEventTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.jobs = JobStore(str(self.f.root / 'jobs.json'))
        self.router = Router(['codex', 'claude'], default_mention='all')
        stack = ExitStack()
        self.addCleanup(stack.close)
        empty = Mock()
        empty.list_all.return_value = []
        for name, value in (('registry', self.f.registry), ('store', self.f.messages),
                            ('session_engine', self.f.engine), ('session_store', self.f.sessions),
                            ('agents', self.f.trigger), ('jobs', self.jobs), ('router', self.router),
                            ('config', {'agents': {}}), ('rules', empty), ('schedules', empty),
                            ('room_settings', {'username': 'operator', 'channels': ['general'], 'history_limit': 'all'}),
                            ('session_token', 'operator-routing-test'), ('ws_clients', set()), ('agent_hats', {})):
            stack.enter_context(patch.object(app, name, value))
        stack.enter_context(patch.object(app, 'broadcast_status', AsyncMock()))
        stack.enter_context(patch.object(mcp_bridge, 'is_online', return_value=True))
        def callback(message):
            try:
                asyncio.get_running_loop().create_task(app._handle_new_message(message))
            except RuntimeError:
                pass
        self.f.messages.on_message(callback)
        self.headers = {'X-Session-Token': 'operator-routing-test'}
        self.body = {'text': '@codex café\r\nraw', 'selected_recipients': ['claude'], 'channel': 'general'}

    def client(self):
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('operator-routing-test', {'server': {'port': 18300}})
        api.add_api_route('/api/recipients/preview', app.preview_recipients, methods=['POST'])
        api.add_api_route('/api/jobs/{job_id}/messages', app.post_job_message, methods=['POST'])
        api.add_api_route('/api/send', app.api_send, methods=['POST'])
        api.add_api_route('/api/messages', app.get_messages, methods=['GET'])
        api.add_api_route('/api/sessions/request-draft', app.request_session_draft, methods=['POST'])
        api.add_api_websocket_route('/ws', app.websocket_endpoint)
        client = TestClient(api, client=('127.0.0.1', 40000))
        self.addCleanup(client.close)
        return client

    def open_socket(self, client):
        socket = client.websocket_connect('/ws?token=operator-routing-test')
        connection = socket.__enter__()
        self.addCleanup(lambda: socket.__exit__(None, None, None))
        while connection.receive_json()['type'] != 'history_complete':
            pass
        return connection

    def test_preview_is_authoritative_readonly_and_has_no_delivery_promise(self):
        client = self.client()
        files = {str(p): p.read_bytes() for p in self.f.root.rglob('*') if p.is_file()}
        channels = deepcopy(self.router._channels)
        result = client.post('/api/recipients/preview', json=self.body, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers['cache-control'], 'no-store')
        value = result.json()
        self.assertEqual(set(value), {'mode', 'tokens', 'ignored', 'recipients', 'warnings', 'waiting'})
        self.assertEqual([r['name'] for r in value['recipients']], ['codex'])
        self.assertEqual(value['waiting'], [{'identity_id': self.f.owner['identity_id'], 'reason': 'earlier_review_turn'}])
        self.assertEqual(self.router._channels, channels)
        self.assertEqual({str(p): p.read_bytes() for p in self.f.root.rglob('*') if p.is_file()}, files)

    def test_preview_and_job_operator_auth_cannot_be_replaced_by_bearer_or_body(self):
        client = self.client()
        job = self.jobs.create('Task', 'job', 'general', 'operator')
        for headers in ({}, {'Authorization': 'Bearer ' + self.f.owner['token']}):
            self.assertEqual(client.post('/api/recipients/preview', json=self.body, headers=headers).status_code, 403)
            self.assertEqual(client.post('/api/jobs/' + str(job['id']) + '/messages',
                json={'text': '@all', 'sender': 'operator'}, headers=headers).status_code, 403)

    def test_trusted_message_identity_fields_cannot_be_changed_by_generic_update(self):
        message = self.f.messages._publish_operator('operator', 'immutable accepted text',
            authority=_OPERATOR_PUBLICATION, routing={'origin': 'operator', 'mode': 'none',
                'tokens': [], 'ignored': [], 'recipients': [], 'warnings': [], 'waiting': []})
        self.f.messages.update_message(message['id'], {'uid': 'forged', 'sender': 'codex',
            'channel': 'elsewhere', 'text': 'edited', 'timestamp': 0, 'metadata': {'reaction': 'read'}})
        saved = self.f.messages.get_snapshot(message['id'])
        for field in ('uid', 'sender', 'channel', 'text', 'timestamp'):
            self.assertEqual(saved[field], message[field])
        self.assertEqual(saved['metadata']['reaction'], 'read')

    def test_preview_rejects_duplicate_invalid_and_oversized_bodies_without_echo(self):
        client = self.client()
        before = self.f.trigger.queue.path.read_bytes()
        for raw in ('[]', '{"text":"secret","text":"@all"}',
                    json.dumps(dict(self.body, metadata={'recipient_routing': {}})),
                    json.dumps(dict(self.body, text='private\x00')),
                    json.dumps(dict(self.body, text='x' * (1024 * 1024)))):
            response = client.post('/api/recipients/preview', content=raw, headers=self.headers)
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('private', response.text)
        self.assertEqual(self.f.trigger.queue.path.read_bytes(), before)

    def test_job_channel_and_operator_display_collision_are_server_owned(self):
        client = self.client()
        job = self.jobs.create('Task', 'job', 'general', 'operator')
        wrong = client.post('/api/recipients/preview', headers=self.headers,
            json=dict(self.body, job_id=job['id'], channel='elsewhere'))
        self.assertEqual(wrong.status_code, 400)
        response = client.post('/api/jobs/' + str(job['id']) + '/messages', headers=self.headers,
            json={'text': '@codex café\r\nraw', 'sender': 'claude', 'selected_recipients': ['claude']})
        self.assertEqual(response.status_code, 200)
        message = response.json()
        self.assertEqual(message['text'], '@codex café\r\nraw')
        receipt = message['metadata']['recipient_routing']
        self.assertEqual(receipt['origin'], 'operator')
        self.assertEqual([r['identity_id'] for r in receipt['recipients']], [self.f.owner['identity_id']])
        queued = [r for r in self.f.trigger.queue.for_identity(self.f.owner)
                  if r['envelope'].get('job_id') == job['id']]
        self.assertEqual(len(queued), 1)

    def test_bearer_chat_ignores_human_sender_and_routing_metadata(self):
        client = self.client()
        before = self.f.trigger.queue.path.read_bytes()
        response = client.post('/api/send', headers={'Authorization': 'Bearer ' + self.f.owner['token']},
            json={'text': '@claude follow up', 'sender': 'operator', 'selected_recipients': ['claude'],
                  'metadata': {'recipient_routing': {'origin': 'operator'}}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['sender'], self.f.owner['name'])
        self.assertNotIn('recipient_routing', response.json()['metadata'])
        self.assertEqual(self.f.trigger.queue.path.read_bytes(), before)

    def test_websocket_posts_raw_text_with_operator_receipt_despite_name_collision(self):
        socket = self.open_socket(self.client())
        text = 'café\r\n@codex exact'
        socket.send_json({'type': 'message', 'text': text, 'sender': 'claude', 'channel': 'general',
                          'selected_recipients': ['claude']})
        event = socket.receive_json()
        self.assertEqual(event['type'], 'message')
        message = event['data']
        self.assertEqual(message['text'], text)
        self.assertEqual(message['metadata']['recipient_routing']['origin'], 'operator')
        self.assertEqual([r['name'] for r in message['metadata']['recipient_routing']['recipients']], ['codex'])

    def test_websocket_rejects_forged_authority_and_duplicate_keys(self):
        socket = self.open_socket(self.client())
        before = self.f.messages.get_recent(100)
        for raw in (json.dumps({'type': 'message', 'text': '@all', 'metadata': {'recipient_routing': {}}}),
                    '{"type":"message","text":"first","text":"@all"}'):
            socket.send_text(raw)
            self.assertEqual(socket.receive_json()['type'], 'message_error')
        self.assertEqual(self.f.messages.get_recent(100), before)

    def test_agent_paths_do_not_reference_private_publication_capability(self):
        self.assertNotIn('_OPERATOR_PUBLICATION', inspect.getsource(mcp_bridge))
        self.assertNotIn('_OPERATOR_PUBLICATION', inspect.getsource(app.api_send))

    def test_unauthenticated_mcp_human_label_is_display_only_in_job_thread(self):
        job = self.jobs.create('Task', 'job', 'discussion', 'operator')
        before = self.f.trigger.queue.path.read_bytes()
        channels = deepcopy(self.router._channels)
        with ExitStack() as stack:
            for name, value in (('jobs', self.jobs), ('store', self.f.messages), ('registry', self.f.registry),
                                ('router', self.router), ('agents', self.f.trigger), ('session_engine', self.f.engine)):
                stack.enter_context(patch.object(mcp_bridge, name, value))
            stack.enter_context(patch.dict(mcp_bridge._presence, {}, clear=True))
            result = mcp_bridge.chat_send('operator', '@all', job_id=job['id'], channel='discussion')
        self.assertIn('Sent', result)
        self.assertEqual(self.jobs.get_messages(job['id'])[-1]['text'], '@all')
        self.assertEqual(self.f.trigger.queue.path.read_bytes(), before)
        self.assertEqual(self.router._channels, channels)

    def test_preview_reports_missing_storage_and_job_without_private_details(self):
        client = self.client()
        response = client.post('/api/recipients/preview', json=dict(self.body, job_id=999), headers=self.headers)
        self.assertEqual(response.status_code, 404)
        for field in ('registry', 'store', 'jobs'):
            with patch.object(app, field, None):
                body = dict(self.body, job_id=999) if field == 'jobs' else self.body
                result = client.post('/api/recipients/preview', json=body, headers=self.headers)
                self.assertEqual(result.status_code, 503)
                self.assertNotIn(str(self.f.root), result.text)

    def test_enqueue_io_after_job_publication_keeps_content_ack_and_one_saved_message(self):
        client = self.client()
        job = self.jobs.create('Task', 'job', 'general', 'operator')
        with patch.object(self.f.trigger, 'trigger_identity_sync', side_effect=OSError('private queue path')):
            response = client.post('/api/jobs/' + str(job['id']) + '/messages', headers=self.headers,
                json={'text': '@claude accepted', 'selected_recipients': []})
        self.assertEqual(response.status_code, 200)
        messages = self.jobs.get_messages(job['id'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['uid'], response.json()['uid'])
        self.assertEqual(len(response.json()['metadata']['recipient_routing']['recipients']), 1)

    def test_hidden_coordinator_prompt_is_dispatched_then_absent_from_readers_and_zip(self):
        client = self.client()
        response = client.post('/api/sessions/request-draft', headers=self.headers,
            json={'agent': 'claude', 'description': 'Hidden planning description', 'channel': 'general'})
        self.assertEqual(response.status_code, 200)
        rows = self.f.messages.get_recent(100)
        self.assertFalse(any(row['type'] == 'session_request' for row in rows))
        self.assertNotIn('Hidden planning description', json.dumps(client.get('/api/messages', headers=self.headers).json()))
        with zipfile.ZipFile(io.BytesIO(archive.build_export(self.f.messages, None, None, None))) as exported:
            self.assertNotIn('Hidden planning description', exported.read('messages.jsonl').decode('utf-8'))
        records = self.f.trigger.queue.for_identity(self.f.peer)
        self.assertEqual(len(records), 1)
        self.assertIn('Hidden planning description', records[0]['envelope']['prompt'])

    def test_unexpected_websocket_error_is_generic_and_connection_remains_usable(self):
        # Bound this fault-injected handler test; a missing error frame must not hang discovery.
        frames = []
        inputs = iter([{'type': 'message', 'text': '@claude hello'},
                       {'type': 'message', 'text': 'shared after error'}])
        class Socket:
            query_params = {'token': 'operator-routing-test'}
            async def accept(self): pass
            async def send_text(self, value): frames.append(json.loads(value))
            async def receive_text(self):
                value = next(inputs, None)
                if value is None:
                    await asyncio.sleep(.01)
                    raise WebSocketDisconnect()
                return json.dumps(value)
        publish = app._publish_operator_message
        failed = False
        def fail_once(**kwargs):
            nonlocal failed
            if not failed:
                failed = True
                raise RuntimeError('private runtime location')
            return publish(**kwargs)
        async def exercise():
            await asyncio.wait_for(app.websocket_endpoint(Socket()), timeout=2)
        with patch.object(app, '_publish_operator_message', side_effect=fail_once):
            asyncio.run(exercise())
        errors = [frame for frame in frames if frame['type'] == 'message_error']
        self.assertEqual(len(errors), 1)
        self.assertNotIn('private', json.dumps(errors))
        self.assertTrue(any(frame['type'] == 'message' for frame in frames))
