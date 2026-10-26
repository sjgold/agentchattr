"""Second ROOT R2 red file: real service/worker/transport/factory/temp owners.

Only process observations and provider/HTTP callbacks use the existing controlled
fixtures. No native process, listener, provider call or production capability.
"""
from copy import deepcopy
import hashlib
import io
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
        before=case.artifacts.path.read_bytes();calls=[];refusals=[]
        def submit(saved):
            calls.append(saved)
            try:return case.authority.admit_saved(saved,case.instance)
            except storage.ArtifactDiagnosticsUnavailable as error:
                refusals.append(error.code)
                raise
        outcome=worker.preflight_cli_artifact(record,**owned,
            fetch_brief=lambda brief:case.authority.get_brief(brief,case.instance),
            submit_saved=submit)
        self.assertEqual(len(calls),1)
        self.assertEqual(refusals,['artifact_diagnostics_unavailable'])
        self.assertEqual((case.artifacts.path.parent/'diagnostics.json').read_bytes(),b'BROKEN_DIAGNOSTICS')
        self.assertEqual((outcome['action'],outcome['reason']),('hold','artifact_delivery_unconfirmed'))
        self.assertEqual(case.artifacts.path.read_bytes(),before)
        self.assert_no_terminal_receipt(case,box,audit)

    def test_worker_api_saved_redelivery_diag_failure_holds(self):
        case=self.managed();instance,attempt,audit,consumer,record,owned=case.api_scope()
        box=self.invalid_saved(case,audit,consumer,attempt,api=True)
        self.corrupt_diagnostics(case.artifacts);case.current_brief=audit['brief_id']
        before=case.artifacts.path.read_bytes();calls=[];refusals=[]
        callbacks=case.api_callbacks(instance)
        def submit(saved):
            calls.append(saved)
            try:return case.authority.admit_saved(saved,instance)
            except storage.ArtifactDiagnosticsUnavailable as error:
                refusals.append(error.code)
                raise
        callbacks['submit_saved']=submit
        outcome=worker.complete_api_artifact(record,**owned,**callbacks)
        self.assertEqual(len(calls),1)
        self.assertEqual(refusals,['artifact_diagnostics_unavailable'])
        self.assertEqual((case.artifacts.path.parent/'diagnostics.json').read_bytes(),b'BROKEN_DIAGNOSTICS')
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
        for retained in (False,True):
            def checked(owner,data_dir,**kwargs):
                root=Path(data_dir);path=root/'artifacts'/'diagnostics.json'
                broken=(root/'artifacts'/'index.json').exists()
                preserved=None
                if broken and retained:
                    preserved=b'{"version":1,"diagnostics":{},"dispatch_overflow":{},"store_overflow":null}'
                    path.write_bytes(preserved)
                original(owner,data_dir,**kwargs)
                self.assertEqual(owner.diagnostic_store.root,owner.root)
                self.assertEqual(path.read_bytes() if path.exists() else None,preserved)
                seen.append((path,preserved,broken,retained))
            with patch.object(storage.ArtifactStore,'__init__',checked):
                ArtifactFactoryTests().test_real_factory_binds_before_catalog_recovers_before_threads_and_holds_corruption()
        self.assertTrue(any(broken and not retained and data is None for _,data,broken,retained in seen))
        self.assertTrue(any(broken and retained and data is not None for _,data,broken,retained in seen))
        self.assertTrue(all(not path.parent.parent.exists() for path,_,_,_ in seen))

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

    def test_service_unmatched_conflict_packet_failure_and_ack_repair_with_held_diagnostics(self):
        for caller in ('unmatched','get_brief','resume','conflicting_duplicate','ack_repair'):
            with self.subTest(caller=caller):
                case=self.managed();audit,consumer=case.claimed()
                record=case.sealed_fixture_record(audit,consumer)
                box=ArtifactOutbox(case.attempt['snapshot'].parent)
                if caller in ('conflicting_duplicate','ack_repair'):
                    case.artifacts.commit_version(audit['request_id'],audit['attempt_id'],audit['dispatch_id'],
                        '# Committed different',record['payload']['observation'])
                    box.save(record['payload'],case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
                if caller in ('get_brief','resume'):
                    case.artifacts._object_path('packet',audit['scope']['packet_id']).write_bytes(b'BAD_PACKET')
                if caller=='unmatched':
                    record=deepcopy(record);record['payload'].update(request_id='a'*32,dispatch_id='b'*32,result_id='b'*32)
                path=self.corrupt_diagnostics(case.artifacts)
                before=case.artifacts.path.read_bytes()
                row=case.artifacts.get_request(audit['request_id'])
                with self.assertRaises(storage.ArtifactDiagnosticsUnavailable) as caught:
                    if caller=='get_brief':case.authority.get_brief(audit['brief_id'],case.instance)
                    elif caller=='resume':case.authority.resume_request(audit['request_id'])
                    elif caller=='ack_repair':case.authority._repair_fulfilled_ack(row)
                    else:case.authority.admit_saved(record,case.instance)
                self.assertEqual(caught.exception.code,'artifact_diagnostics_unavailable')
                self.assertEqual(path.read_bytes(),b'BROKEN_DIAGNOSTICS')
                self.assertEqual(case.artifacts.path.read_bytes(),before)
                self.assertIsNone(box.get_ack(audit['dispatch_id']))
                self.assertIsNone(box.get_disposition(audit['dispatch_id']))

    def test_startup_held_diagnostic_reason_distinguishes_terminal_record_and_ack_repair(self):
        for mode in ('terminal','ack_repair'):
            with self.subTest(mode=mode):
                case=self.managed();audit,consumer=case.claimed()
                record=case.sealed_fixture_record(audit,consumer)
                box=ArtifactOutbox(case.attempt['snapshot'].parent)
                box.save(record['payload'],case.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
                if mode=='terminal':case.authority.cancel_request(audit['request_id'])
                else:case.artifacts.commit_version(audit['request_id'],audit['attempt_id'],audit['dispatch_id'],
                    '# Different committed bytes',record['payload']['observation'])
                path=self.corrupt_diagnostics(case.artifacts);before=case.artifacts.path.read_bytes()
                result=case.authority.recover_startup()
                expected = (['operator_recovery_required','storage_unavailable'] if mode=='terminal'
                            else ['operator_recovery_required'])
                # Claimed cancellation fence remains unconfirmed before the diagnostic refusal.
                self.assertEqual(result['held'],[{'request_id':audit['request_id'], 'dispatch_id':audit['dispatch_id'],
                    'reason':reason} for reason in expected])
                self.assertEqual(result['quarantined'],[]);self.assertEqual(result['admitted'],[])
                self.assertEqual(path.read_bytes(),b'BROKEN_DIAGNOSTICS');self.assertEqual(case.artifacts.path.read_bytes(),before)
                self.assertIsNone(box.get_ack(audit['dispatch_id']));self.assertIsNone(box.get_disposition(audit['dispatch_id']))

    def test_lifecycle_preview_rename_delete_ignore_held_diagnostics(self):
        from tests.test_artifact_lifecycle import ArtifactLifecycleTests
        for operation in ('rename','delete'):
            with self.subTest(operation=operation):
                fixture=ArtifactLifecycleTests();self.addCleanup(fixture.doCleanups)
                case=fixture.context();audit,_=case.new_request()
                case.artifacts.reserve_request(audit,audit['request_id'])
                case.artifacts.set_attempt_state(audit['request_id'],audit['attempt_id'],'prepared',
                    {'state':'failed','reason':'generation_failed'})
                path=self.corrupt_diagnostics(case.artifacts)
                options={'new_name':'renamed'} if operation=='rename' else {}
                with patch.object(case.artifacts.diagnostic_store,'report',side_effect=AssertionError('lifecycle read diagnostics')),                        patch.object(case.artifacts.diagnostic_store,'record',side_effect=AssertionError('lifecycle wrote diagnostics')):
                    preview=case.service.preview(operation,'review',**options)
                    result=case.service.apply(operation,'review',request_id=__import__('uuid').uuid4().hex,
                        confirmation='review',preview_token=preview['preview_token'],**options)
                self.assertTrue(result['ok']);self.assertEqual(path.read_bytes(),b'BROKEN_DIAGNOSTICS')
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['channel'],'renamed' if operation=='rename' else 'review')

    def test_archive_diagnostic_member_is_refused_before_mutation(self):
        from tests.test_artifact_archive_driver import ArtifactArchiveDriverTests
        fixture=ArtifactArchiveDriverTests();self.addCleanup(fixture.doCleanups);fixture.setUp()
        fixture.source_graph(attempts=False);data=fixture.export()
        corrupted=fixture.repack(data,lambda members:members.update({'artifacts/diagnostics.json':b'{}'}))
        before={p.relative_to(fixture.root).as_posix():p.read_bytes() for p in fixture.root.rglob('*') if p.is_file()}
        result=fixture.restore(corrupted)
        self.assertFalse(result['ok']);self.assertFalse(result['partial'])
        self.assertEqual(result['sections']['artifacts']['section_error']['code'],'artifact_archive_invalid_section')
        # restore creates empty target-history owners, which do not write files.
        self.assertEqual({p.relative_to(fixture.root).as_posix():p.read_bytes() for p in fixture.root.rglob('*') if p.is_file()},before)

    def test_channels_documents_diagnostic_backup_exclusion_and_delete_retention(self):
        text=(Path(__file__).resolve().parents[1]/'CHANNELS.md').read_text(encoding='utf-8')
        self.assertIn('Diagnostic logs and retained diagnostic bodies are excluded from channel backups.',text)
        self.assertIn('Deleting a channel retains those diagnostic files.',text)
        self.assertIn('The candidate remains under review and artifact authoring stays disabled.',text)

    def test_shared_atomic_json_single_write_is_byte_identical_for_real_payloads_and_r1_golden(self):
        import api_seats
        from tests.test_artifact_record_bounds import ArtifactRecordBoundsTests
        case=self.managed();audit=case.prepare()
        case.sessions._load_templates(Path(__file__).resolve().parents[1]/'session_templates')
        session=case.sessions.create('planning','peer',
            {'planner':'planner','challenger':'challenger','synthesiser':'synthesiser'},
            'operator',goal='Exact caf\u00e9\r\nplan',input_text='\u65e5\u672c\u8a9e source')
        self.assertIsNotNone(session)
        case.artifacts.quarantine_submission(None,'a'*32,'b'*32,reason='invalid_content',content='diagnostic')
        maximum=ArtifactRecordBoundsTests();self.addCleanup(maximum.doCleanups);maximum.setUp()
        metadata,golden=maximum.maximum_row()
        self.assertEqual(len(golden),991296)
        self.assertEqual(hashlib.sha256(golden).hexdigest(),'8451bbe3371bd3f472e5531e78c2529b702bdf4759dd043c995f702b3aeeeef4')
        payloads={
            'artifact_index':json.loads(case.artifacts.path.read_text(encoding='utf-8')),
            'diagnostic':json.loads(case.artifacts.diagnostic_store.path.read_text(encoding='utf-8')),
            'dispatch':json.loads(case.trigger.queue.path.read_text(encoding='utf-8')),
            'session':json.loads(case.sessions._path.read_text(encoding='utf-8')),
            'seats':json.loads(case.manager.store.path.read_text(encoding='utf-8')),
            'launch':json.loads(case.attempt['snapshot'].read_text(encoding='utf-8')),
            'brief':case.briefs.get_private(audit['brief_id']),
            'r1_maximum_version':metadata,
            'encoding_edges':{'z':'\x00\n\t\r\u00e9\u754c\U0001f600\ud800',
                'a':[0,-0.0,1.2345678901234567e-100,2**63-1,1e308,True,None]}}
        counts={};original_open=Path.open
        class Stream:
            def __init__(self,stream,label):self.stream,self.label=stream,label
            def __getattr__(self,key):return getattr(self.stream,key)
            def __enter__(self):self.stream.__enter__();return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def write(self,value):
                counts[self.label]+=1
                return self.stream.write(value)
        for label,value in payloads.items():
            reference=io.StringIO()
            json.dump(value,reference,ensure_ascii=True,allow_nan=False)  # Prior algorithm, not dumps-derived.
            expected=reference.getvalue().encode('utf-8');counts[label]=0
            target=case.root/(label+'.json')
            def opened(path,*args,**kwargs):
                stream=original_open(path,*args,**kwargs)
                return Stream(stream,label) if path.name.startswith(target.name+'.') and args and args[0]=='x' else stream
            with patch.object(Path,'open',opened):api_seats.atomic_json(target,value)
            self.assertEqual(target.read_bytes(),expected,label)
            self.assertEqual(json.loads(expected),json.loads(target.read_bytes()))
        # Byte comparisons above all run before the optimization-specific red.
        for label,count in counts.items():
            with self.subTest(one_write=label):self.assertEqual(count,1)
        target=case.root/'error-preserves.json';target.write_bytes(b'previous')
        cyclic=[];cyclic.append(cyclic)
        for value,error in ((float('nan'),ValueError),(float('inf'),ValueError),({'set':{1}},TypeError),(cyclic,ValueError)):
            with self.subTest(refusal=error.__name__):
                with self.assertRaises(error):api_seats.atomic_json(target,value)
                self.assertEqual(target.read_bytes(),b'previous')
                self.assertEqual(list(case.root.glob('error-preserves.json.*.tmp')),[])
