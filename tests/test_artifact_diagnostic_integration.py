"""Second ROOT R2 red file: real service/worker/transport/factory/temp owners.

Only process observations and provider/HTTP callbacks use the existing controlled
fixtures. No native process, listener, provider call or production capability.
"""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import artifact_store as storage
import artifact_worker as worker
from artifact_delivery import ArtifactOutbox
from tests import test_artifact_workers as fixture


class ArtifactDiagnosticIntegrationTests(unittest.TestCase):
    def managed(self):
        case=fixture.ArtifactWorkerTests()
        self.addCleanup(lambda:self.assertFalse(case.root.exists()))
        self.addCleanup(case.doCleanups)
        case.setUp();case.setup_authority()
        return case

    @staticmethod
    def corrupt_diagnostics(owner):
        path=owner.root/'artifacts'/'diagnostics.json'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'BROKEN_DIAGNOSTICS')
        return path

    def invalid_saved(self,case,audit,consumer,attempt,*,api=False):
        observation={'confirmed_model':None,'confirmation_reason':'provider_did_not_report_model' if api else 'cli_model_unverified'}
        signed=case.sealed_fixture_record(audit,consumer,observation=observation)
        payload=deepcopy(signed['payload'])
        payload['expected_parent']={'version_id':'e'*32,'sequence':1,'sha256':'f'*64}
        secret=case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret']
        box=ArtifactOutbox(attempt['snapshot'].parent)
        box.save(payload,secret)  # Trusted fixture signer; no seal bypass in product.
        return box

    def assert_no_terminal_receipt(self,case,box,audit):
        self.assertIsNone(box.get_ack(audit['dispatch_id']))
        self.assertIsNone(box.get_disposition(audit['dispatch_id']))
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')
        self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'],0)

    def test_worker_cli_saved_redelivery_diag_failure_holds(self):
        case=self.managed();audit,consumer=case.claimed()
        record,owned=case.owned(audit)
        box=self.invalid_saved(case,audit,consumer,case.attempt)
        self.corrupt_diagnostics(case.artifacts)
        before=case.artifacts.path.read_bytes();calls=[]
        def submit(saved):
            calls.append(saved)
            return case.authority.admit_saved(saved,case.instance)
        outcome=worker.preflight_cli_artifact(record,**owned,
            fetch_brief=lambda brief:case.authority.get_brief(brief,case.instance),
            submit_saved=submit)
        self.assertEqual(len(calls),1)
        self.assertEqual((outcome['action'],outcome['reason']),('hold','artifact_delivery_unconfirmed'))
        self.assertEqual(case.artifacts.path.read_bytes(),before)
        self.assert_no_terminal_receipt(case,box,audit)

    def test_worker_api_saved_redelivery_diag_failure_holds(self):
        case=self.managed();instance,attempt,audit,consumer,record,owned=case.api_scope()
        box=self.invalid_saved(case,audit,consumer,attempt,api=True)
        self.corrupt_diagnostics(case.artifacts);case.current_brief=audit['brief_id']
        before=case.artifacts.path.read_bytes();calls=[]
        callbacks=case.api_callbacks(instance)
        def submit(saved):
            calls.append(saved)
            return case.authority.admit_saved(saved,instance)
        callbacks['submit_saved']=submit
        outcome=worker.complete_api_artifact(record,**owned,**callbacks)
        self.assertEqual(len(calls),1)
        self.assertEqual((outcome['status'],outcome['reason']),('held','artifact_delivery_unconfirmed'))
        self.assertEqual(case.artifacts.path.read_bytes(),before)
        self.assert_no_terminal_receipt(case,box,audit)

    def test_worker_delivery_with_held_diagnostics_is_context_unavailable(self):
        case=self.managed();instance,_,audit,_,record,owned=case.api_scope()
        self.corrupt_diagnostics(case.artifacts)
        packet=case.artifacts.root/'artifact_briefs'/'packets'/(audit['scope']['packet_id']+'.json')
        packet.write_bytes(b'BAD_PACKET')
        case.current_brief=audit['brief_id']
        outcome=worker.complete_api_artifact(record,**owned,**case.api_callbacks(instance))
        self.assertEqual((outcome['status'],outcome['reason']),('held','artifact_context_unavailable'))
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')
        self.assertFalse(list(owned['runtime_path'].glob('artifact_results/*.json')))

    def test_worker_invalid_response_with_held_diagnostics_returns_hold_without_fake_receipt(self):
        case=self.managed();instance,_,audit,_,record,owned=case.api_scope()
        self.corrupt_diagnostics(case.artifacts);case.current_brief=audit['brief_id']
        generated=Mock(return_value={'content':'not structured JSON','confirmed_model':None})
        outcome=worker.complete_api_artifact(record,**owned,**case.api_callbacks(instance,generate=generated))
        self.assertEqual((outcome['status'],outcome['reason']),('held','artifact_delivery_unconfirmed'))
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')
        self.assertFalse(list(owned['runtime_path'].glob('artifact_results/*.json')))
        self.assertFalse(list(owned['runtime_path'].glob('artifact_dispositions/*.json')))
        self.assertNotIn('diagnostic_id',outcome)

    def test_worker_postsave_redelivery_diag_failure_holds_without_disposition(self):
        case=self.managed();instance,_,audit,_,record,owned=case.api_scope()
        self.corrupt_diagnostics(case.artifacts);case.current_brief=audit['brief_id']
        generated=Mock(return_value={'content':json.dumps({'kind':'artifact','markdown':'# Valid'}),'confirmed_model':None})
        def saved(dispatch):
            self.assertEqual(dispatch,audit['dispatch_id'])
            packet=case.artifacts.root/'artifact_briefs'/'packets'/(audit['scope']['packet_id']+'.json')
            packet.write_bytes(b'CHANGED_AFTER_SAVE')
        outcome=worker.complete_api_artifact(record,**owned,**case.api_callbacks(instance,generate=generated),on_saved=saved)
        self.assertEqual((outcome['status'],outcome['reason']),('held','artifact_delivery_unconfirmed'))
        box=ArtifactOutbox(owned['runtime_path'])
        self.assertIsNotNone(box.find(audit['dispatch_id']))
        self.assert_no_terminal_receipt(case,box,audit)

    def test_actual_agent_transport_projects_held_diagnostic_503_without_receipt(self):
        from tests.test_artifact_transport import ArtifactTransportTests
        transport=ArtifactTransportTests()
        self.addCleanup(lambda:self.assertFalse(transport.case.root.exists()))
        self.addCleanup(transport.doCleanups);transport.setUp()
        self.corrupt_diagnostics(transport.case.artifacts)
        response=transport.client.post(transport.base+'/reject',headers=transport.headers,
            json={'content':'bad structured response','received_truncated':False})
        self.assertEqual(response.status_code,503,response.text)
        self.assertEqual(response.json(),{'status':'error','code':'artifact_storage_unavailable',
            'error':'Artifact storage is unavailable. Work is retained.',
            'diagnostic_id':None,'received_truncated':False})
        self.assertEqual(response.headers.get('cache-control'),'no-store')
        self.assertEqual(transport.case.artifacts.get_request(transport.audit['request_id'])['state'],'active')

    def test_actual_mcp_submit_projects_held_diagnostic_503_without_receipt(self):
        import mcp_bridge
        case=self.managed();audit,_=case.claimed()
        self.corrupt_diagnostics(case.artifacts)
        with patch.object(mcp_bridge,'artifact_authority',case.authority),\
                patch.object(mcp_bridge,'_authenticated_instance',return_value=case.instance):
            response=json.loads(mcp_bridge.chat_artifact_submit(audit['brief_id'],''))
        self.assertEqual(response['code'],'artifact_storage_unavailable')
        self.assertEqual(response['status'],'error');self.assertIsNone(response['diagnostic_id'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'],'active')

    def test_real_factory_does_not_create_or_reset_diagnostics_when_authoring_is_broken(self):
        from tests.test_artifact_factory import ArtifactFactoryTests
        original=storage.ArtifactStore.__init__
        seen=[]
        def checked(owner,data_dir,**kwargs):
            root=Path(data_dir);path=root/'artifacts'/'diagnostics.json'
            broken=(root/'artifacts'/'index.json').exists()
            preserved=None
            if broken:
                preserved=b'{"version":1,"diagnostics":{},"dispatch_overflow":{},"store_overflow":null}'
                path.write_bytes(preserved)
            original(owner,data_dir,**kwargs)
            self.assertEqual(owner.diagnostic_store.root,owner.root)
            self.assertEqual(path.read_bytes() if path.exists() else None,preserved)
            seen.append((path,preserved))
        with patch.object(storage.ArtifactStore,'__init__',checked):
            ArtifactFactoryTests().test_real_factory_binds_before_catalog_recovers_before_threads_and_holds_corruption()
        self.assertEqual(len(seen),2)
        self.assertTrue(all(not path.parent.parent.exists() for path,_ in seen))

    def test_export_and_import_ignore_corrupt_diagnostics_without_resetting_them(self):
        from tests.test_artifact_archive_driver import ArtifactArchiveDriverTests
        case=ArtifactArchiveDriverTests();self.addCleanup(lambda:self.assertFalse(case.root.exists()))
        self.addCleanup(case.doCleanups);case.setUp()
        _,audit,version=case.source_graph(attempts=False)
        source=self.corrupt_diagnostics(case.source);target=self.corrupt_diagnostics(case.target)
        data=case.export();report=case.restore(data)
        self.assertTrue(report['ok']);self.assertEqual(report['sections']['artifacts']['created_lineages'],1)
        self.assertEqual(case.target.get_version(version['id'])['markdown'],case.source.get_version(version['id'])['markdown'])
        self.assertEqual(source.read_bytes(),b'BROKEN_DIAGNOSTICS');self.assertEqual(target.read_bytes(),b'BROKEN_DIAGNOSTICS')
        self.assertFalse(case.source.diagnostics()['owners']['diagnostics']['available'])
        self.assertTrue(case.target.diagnostics()['owners']['authoring']['available'])

    def test_imported_standalone_diagnostic_changes_no_authoring_bytes_or_imported_rows(self):
        from tests.test_artifact_imported_store import ArtifactImportedStoreTests
        case=ArtifactImportedStoreTests();self.addCleanup(lambda:self.assertFalse(case.root.exists()))
        self.addCleanup(case.doCleanups);case.setUp()
        graph,audit,_=case.source_graph(attempts=False)
        plan=case.target.prepare_import_lineage(*graph)
        with case.service._boundary():case.target.import_lineage(plan,channel='review')
        before=case.target.path.read_bytes();row=case.target.get_request(audit['request_id'])
        result=case.target.quarantine_submission(audit['request_id'],audit['attempt_id'],audit['dispatch_id'],
            reason='superseded',content='late imported attempt')
        self.assertEqual(case.target.path.read_bytes(),before)
        self.assertEqual(case.target.get_request(audit['request_id']),row)
        self.assertEqual(case.target.request_diagnostics(audit['request_id'])['quarantine_ids'],[])
        self.assertIsNone(result['attached_request_id'])
