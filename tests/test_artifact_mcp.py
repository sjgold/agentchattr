"""In-process real MCP tool registration and scoped service calls, no listeners."""
import asyncio
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import mcp_bridge
from tests import test_artifact_workers as fixture

ROOT=Path(__file__).resolve().parents[1]
class ArtifactMcpTests(unittest.TestCase):
    def test_artifact_tools_are_registered_and_all_legacy_tools_remain(self):
        golden=json.loads((ROOT/'tests/fixtures/artifact_legacy_tools.json').read_text(encoding='utf-8'))
        tools=asyncio.run(mcp_bridge._create_server(19999).list_tools())
        rows=[tool.model_dump() for tool in tools]
        self.assertEqual(rows[:15],golden['tools'])
        self.assertEqual([row['name'] for row in rows[15:]],['chat_artifact_brief','chat_artifact_submit'])
        self.assertEqual([f.__name__ for f in mcp_bridge._ALL_TOOLS[:15]],golden['function_order'])
        self.assertEqual({f.__name__:inspect.getdoc(f) for f in mcp_bridge._ALL_TOOLS[:15]},golden['function_docs'])

    def test_assigned_cli_brief_and_submit_are_scoped_and_validation_is_retryable(self):
        case=fixture.ArtifactWorkerTests();self.addCleanup(case.doCleanups)
        case.setUp();case.setup_authority()
        audit,consumer=case.claimed()
        with patch.object(mcp_bridge,'artifact_authority',case.authority),patch.object(mcp_bridge,'_authenticated_instance',return_value=case.instance):
            context=json.loads(mcp_bridge.chat_artifact_brief(audit['brief_id']))
            self.assertEqual(set(context),{'brief','packet','parent'})
            self.assertIsNone(context['parent'])
            private=case.briefs.get_private(audit['brief_id'])
            text=json.dumps(context)
            self.assertNotIn(private['_artifact_seal']['seal_secret'],text)
            self.assertNotIn(audit['producer']['launch_nonce'],text)
            invalid=json.loads(mcp_bridge.chat_artifact_submit(audit['brief_id'],''))
            self.assertEqual(invalid['code'],'invalid_content')
            self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')
            ack=json.loads(mcp_bridge.chat_artifact_submit(audit['brief_id'],'# Exact café\r\ntext'))
            self.assertEqual(ack['status'],'admitted')
            self.assertEqual(case.trigger.queue.owned(case.instance,audit['dispatch_id'])['state'],'dispatched')
        before=case.files()
        with patch.object(mcp_bridge,'artifact_authority',case.authority),patch.object(mcp_bridge,'_authenticated_instance',return_value=None):
            self.assertEqual(json.loads(mcp_bridge.chat_artifact_brief(audit['brief_id']))['code'],'artifact_access_denied')
        self.assertEqual(case.files(),before)

    def test_parent_refusal_precedes_activation_and_returns_only_fixed_error(self):
        case=fixture.ArtifactWorkerTests();self.addCleanup(case.doCleanups)
        case.setUp();case.setup_authority()
        audit=case.prepare();case.claim(audit)
        before=case.files()
        with patch.object(mcp_bridge,'artifact_authority',case.authority),patch.object(mcp_bridge,'_authenticated_instance',return_value=case.instance), \
                patch.object(case.authority,'_get_parent_locked',side_effect=case.storage.ArtifactUnavailable('PRIVATE_SEAL')), \
                patch.object(case.authority,'_get_brief_locked',side_effect=AssertionError('Activated after parent failure')):
            response=mcp_bridge.chat_artifact_brief(audit['brief_id'])
        self.assertNotIn('PRIVATE_SEAL',response)
        self.assertEqual(json.loads(response)['code'],'artifact_storage_unavailable')
        self.assertEqual(case.files(),before)

if __name__=='__main__':unittest.main()
