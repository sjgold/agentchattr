"""Private result authority stays out of ordinary frozen context."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from review_brief import BriefAccessError, BriefError, BriefStore, brief_messages, build_brief, freeze_inputs


class ResultBriefSealTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        temporary = tempfile.TemporaryDirectory(dir=root / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.store = BriefStore(temporary.name)
        self.principal = {'identity_id': uuid.uuid4().hex, 'name': 'managed-api'}
        template = {'id': 'sealed', 'name': 'Sealed review', 'roles': ['reader'], 'phases': [
            {'name': 'Review', 'participants': ['reader'], 'prompt': 'Read source.', 'is_output': True}]}
        session = {'id': 1, **freeze_inputs(template, input_text='Exact café\r\nsource')}
        self.envelope = build_brief(session, 0, 0, self.principal['name'], self.principal['identity_id'])
        self.envelope['completion_protocol'] = 1
        self.owner = {'adapter': 'openai-compatible', 'dispatch_id': uuid.uuid4().hex,
            'seat_identity_id': self.principal['identity_id'], 'launch_attempt': uuid.uuid4().hex,
            'launch_nonce': uuid.uuid4().hex, 'fingerprint': 'a' * 64}

    def test_private_key_is_stable_and_default_reads_never_expose_it(self):
        brief_id = self.store.put(self.envelope, result_owner=self.owner)
        path = self.store.path / (brief_id + '.json')
        original = path.read_bytes()
        delivered = self.store.get_delivery(brief_id, self.principal)
        secret = delivered['seal_secret']
        self.assertRegex(secret, '^[0-9a-f]{64}$')
        self.assertEqual(delivered['result_owner'], self.owner)
        for public in (self.store.get(brief_id, self.principal), self.store.get(brief_id, operator=True)):
            self.assertEqual(public, self.envelope)
            self.assertNotIn(secret, json.dumps(public))
        self.assertNotIn(secret, json.dumps(brief_messages(delivered, [], 'managed-api')))
        self.store.put(deepcopy(self.envelope), result_owner=deepcopy(self.owner))
        self.store.put(deepcopy(self.envelope))
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.store.get_delivery(brief_id, self.principal)['seal_secret'], secret)

    def test_other_identity_cannot_fetch_private_delivery(self):
        brief_id = self.store.put(self.envelope, result_owner=self.owner)
        with self.assertRaises(BriefAccessError):
            self.store.get_delivery(brief_id, {'identity_id': uuid.uuid4().hex, 'name': 'managed-api'})
        with self.assertRaises(BriefAccessError):
            self.store.get_delivery(brief_id, None)

    def test_legacy_replay_cannot_silently_add_a_result_key(self):
        brief_id = self.store.put(self.envelope)
        path = self.store.path / (brief_id + '.json')
        original = path.read_bytes()
        self.assertNotIn('seal_secret', self.store.get_delivery(brief_id, self.principal))
        with self.assertRaises(BriefError):
            self.store.put(self.envelope, result_owner=self.owner)
        self.assertEqual(path.read_bytes(), original)

    def test_saved_result_verifies_original_scope_without_a_live_principal(self):
        from result_outbox import seal_result
        brief_id = self.store.put(self.envelope, result_owner=self.owner)
        secret = self.store.get_delivery(brief_id, self.principal)['seal_secret']
        dispatch = self.owner['dispatch_id']
        payload = {'version': 1, 'result_id': dispatch, 'dispatch_id': dispatch, 'event_id': dispatch,
            **{field: self.envelope[field] for field in (
                'session_id', 'brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')},
            **{field: self.owner[field] for field in (
                'seat_identity_id', 'launch_attempt', 'launch_nonce', 'fingerprint')},
            'kind': 'final', 'content': 'Exact saved café\r\nanswer', 'created_at': 1234.5}
        record = seal_result(payload, secret)
        self.assertEqual(self.store.verify_saved_result(record), payload)
        for field in ('seat_identity_id', 'launch_attempt', 'launch_nonce', 'brief_id', 'run_id',
                      'attempt_id', 'input_revision', 'fingerprint', 'dispatch_id'):
            changed = deepcopy(payload)
            if field == 'run_id':
                changed['turn_id'] = 'b' * 32 + ':0:0'
            if field == 'dispatch_id':
                changed.update(result_id='b' * 32, event_id='b' * 32)
            changed[field] = 'b' * (64 if field in ('input_revision', 'fingerprint') else 32)
            with self.subTest(field=field), self.assertRaises(BriefError):
                self.store.verify_saved_result(seal_result(changed, secret))

    def test_http_delivery_exposes_key_only_to_exact_authenticated_api_owner(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import app
        from registry import RuntimeRegistry
        registry = RuntimeRegistry(str(self.store.path.parent))
        registry.seed({'managed-api': {'type': 'api'}, 'peer': {'type': 'api'}})
        owner, peer = registry.register('managed-api'), registry.register('peer')
        self.envelope.update(expected_agent=owner['name'], expected_identity_id=owner['identity_id'])
        self.owner['seat_identity_id'] = owner['identity_id']
        brief_id = self.store.put(self.envelope, result_owner=self.owner)
        api = FastAPI()
        with patch.object(app, 'app', api):
            app._install_security_middleware('seal-operator', {'server': {'port': 18300}})
        api.add_api_route('/api/review-briefs/{brief_id}', app.get_review_brief)
        with patch.object(app, 'registry', registry), patch.object(app, 'session_token', 'seal-operator'), \
                patch.object(app, 'session_store', SimpleNamespace(briefs=self.store)), \
                TestClient(api, client=('127.0.0.1', 40000)) as client:
            route = '/api/review-briefs/' + brief_id
            delivered = client.get(route, headers={'Authorization': 'Bearer ' + owner['token']})
            self.assertEqual(delivered.status_code, 200)
            self.assertIn('seal_secret', delivered.json())
            self.assertEqual(client.get(route, headers={'x-session-token': 'seal-operator'}).json(), self.envelope)
            self.assertEqual(client.get(route, headers={'Authorization': 'Bearer ' + peer['token']}).status_code, 403)
            self.assertEqual(client.get(route).status_code, 403)

    def test_mcp_context_for_same_owner_is_redacted(self):
        import mcp_bridge
        brief_id = self.store.put(self.envelope, result_owner=self.owner)
        with patch.object(mcp_bridge, 'review_briefs', self.store), \
                patch.object(mcp_bridge, '_authenticated_instance', return_value=self.principal):
            value = json.loads(mcp_bridge.chat_review_brief(brief_id))
        self.assertEqual(value, self.envelope)
