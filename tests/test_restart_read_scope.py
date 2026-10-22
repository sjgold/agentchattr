"""A corrected review's default read paths cannot reimport abandoned history."""
import json
import unittest
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app
import mcp_bridge


class RestartReadScopeTests(unittest.TestCase):
    def setUp(self):
        from tests.test_session_events import SessionEventTests
        self.fixture = SessionEventTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.sessions._event_update(f.session_id, lambda s: s.update(parent_run_id='abandoned-run'))
        f.messages.add('system', 'OLD-SOURCE and rejected OLD-ANSWER @all')
        f.admit(content='NEW-RUN accepted phase result')
        self.api = FastAPI()
        self.api.add_api_route('/api/messages', app.get_messages, methods=['GET'])
        self.client = TestClient(self.api)

    def test_bearer_default_channel_and_job_reads_exclude_old_history_operator_read_preserved(self):
        f = self.fixture
        jobs = Mock()
        jobs.get_messages.return_value = [{'text': 'OLD-SOURCE job text'}]
        with patch.object(app, 'registry', f.registry), patch.object(app, 'session_engine', f.engine), \
             patch.object(app, 'store', f.messages), patch.object(app, 'jobs', jobs):
            for query in ('', '?channel=general', '?job_id=12'):
                with self.subTest(query=query):
                    result = self.client.get('/api/messages' + query, headers={'Authorization': 'Bearer ' + f.owner['token']})
                    self.assertEqual(result.status_code, 200)
                    self.assertNotIn('OLD-SOURCE', result.text)
                    self.assertIn('NEW-RUN accepted phase result', result.text)
            operator = self.client.get('/api/messages', headers={'X-Session-Token': 'operator'})
            self.assertIn('OLD-SOURCE', operator.text)
        jobs.get_messages.assert_not_called()

    def test_mcp_read_resync_job_and_summary_cannot_import_old_source(self):
        f = self.fixture
        jobs, summaries = Mock(), Mock()
        jobs.get.return_value = {'title': 'OLD-SOURCE', 'body': 'OLD-SOURCE job packet'}
        jobs.get_messages.return_value = []
        summaries.get.return_value = {'text': 'OLD-SOURCE persisted summary'}
        with patch.object(mcp_bridge, 'registry', f.registry), patch.object(mcp_bridge, 'session_engine', f.engine), \
             patch.object(mcp_bridge, 'store', f.messages), patch.object(mcp_bridge, 'jobs', jobs), \
             patch.object(mcp_bridge, 'summaries', summaries), \
             patch.object(mcp_bridge, '_resolve_tool_identity', return_value=(f.owner['name'], None)), \
             patch.object(mcp_bridge, '_authenticated_instance', return_value=f.owner):
            for read in (lambda: mcp_bridge.chat_read(f.owner['name']),
                         lambda: mcp_bridge.chat_read(f.owner['name'], job_id=12),
                         lambda: mcp_bridge.chat_resync(f.owner['name']),
                         lambda: mcp_bridge.chat_summary('read', f.owner['name'])):
                result = read()
                self.assertNotIn('OLD-SOURCE', result)
                self.assertIn('NEW-RUN accepted phase result', result)
        jobs.get.assert_not_called()
        summaries.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
