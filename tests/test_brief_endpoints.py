from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
from registry import RuntimeRegistry
from review_brief import BriefStore, build_brief, freeze_inputs


class ScopedBriefEndpointTests(unittest.TestCase):
    def test_malformed_persisted_brief_is_rejected_cleanly(self):
        import json
        from review_brief import BriefError
        with tempfile.TemporaryDirectory() as directory:
            briefs = BriefStore(directory)
            brief_id = 'a' * 32
            briefs.path.mkdir(parents=True)
            for value in ([], {}, {'brief_id': brief_id, 'expected_agent': 'one', 'source': []}):
                (briefs.path / (brief_id + '.json')).write_text(json.dumps(value), encoding='utf-8')
                with self.subTest(value=value), self.assertRaises(BriefError):
                    briefs.get(brief_id, {'name': 'one'})

    def test_scoped_agent_read_and_operator_read_reject_other_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = RuntimeRegistry(directory)
            registry.seed({'one': {}, 'two': {}})
            one, two = registry.register('one'), registry.register('two')
            template = {'id': 'test', 'name': 'Test', 'roles': ['reviewer'], 'phases': [
                {'name': 'Inspect', 'participants': ['reviewer'], 'prompt': 'Inspect source', 'is_output': True}]}
            session = {'id': 1, 'cast': {'reviewer': one['name']}, **freeze_inputs(template, input_text='source beyond recent chat')}
            brief = build_brief(session, 0, 0, one['name'], registry.get_instance(one['name'])['identity_id'])
            briefs = BriefStore(directory)
            brief_id = briefs.put(brief)
            api = FastAPI()
            with patch.object(app, 'app', api):
                app._install_security_middleware('operator-test', {'server': {'port': 18300}})
            api.add_api_route('/api/review-briefs/{brief_id}', app.get_review_brief)
            client = TestClient(api, client=('127.0.0.1', 40000))
            with patch.object(app, 'registry', registry), patch.object(app, 'session_store', SimpleNamespace(briefs=briefs)):
                path = '/api/review-briefs/' + brief_id
                self.assertEqual(client.get(path).status_code, 403)
                result = client.get(path, headers={'Authorization': 'Bearer ' + one['token']})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['source'], 'source beyond recent chat')
                self.assertEqual(client.get(path, headers={'Authorization': 'Bearer ' + two['token']}).status_code, 403)
                self.assertEqual(client.get(path, headers={'x-session-token': 'operator-test'}).status_code, 200)
                self.assertEqual(client.get('/api/review-briefs/not-a-valid-id',
                    headers={'Authorization': 'Bearer ' + one['token']}).status_code, 404)
