"""Reviewer fixes: actual callback, bounded parser and real queue, no provider."""
import ast
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import urllib.error

from api_seats import Receipt
import artifact_worker
from tests import test_artifact_workers as fixture
from tests import test_artifact_transport as transport_fixture

ROOT=Path(__file__).resolve().parents[1]
class ArtifactWrapperReviewTests(unittest.TestCase):
    def test_actual_cli_status_preserves_unrelated_receipt_error_and_clears_only_own_guidance(self):
        tree=ast.parse((ROOT/'cli_worker.py').read_text(encoding='utf-8'))
        run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        function=next(n for n in run.body if isinstance(n,ast.FunctionDef) and n.name=='artifact_status')
        with tempfile.TemporaryDirectory(dir=ROOT/'.audit-tmp') as directory:
            receipt=Receipt(Path(directory)/'receipt.json','a'*32)
            receipt.update(error='Local server heartbeat deadline reached. Retry this seat.',
                           state='failed',authentication='failed',adapter_connected=False)
            namespace={'receipt':receipt}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),'<actual CLI artifact_status>','exec'),namespace)
            callback=namespace['artifact_status']
            callback('b'*32,'complete',None)
            self.assertEqual(receipt.value['error'],'Local server heartbeat deadline reached. Retry this seat.')
            self.assertEqual(receipt.value['state'],'failed')
            self.assertEqual(receipt.value['authentication'],'failed')
            self.assertFalse(receipt.value['adapter_connected'])
            receipt.update(error=None)
            callback('b'*32,'hold','artifact_generation_uncertain')
            self.assertIn('Artifact work is held',receipt.value['error'])
            callback('b'*32,'inject',None)
            self.assertIsNone(receipt.value['error'])
            self.assertIsNone(receipt.value['held_artifact'])

    def context(self):
        case=fixture.ArtifactWorkerTests();self.addCleanup(case.doCleanups)
        case.setUp();case.setup_authority()
        return case

    def test_preflight_preserves_fixed_specific_codes_and_waits_for_retryable_http(self):
        case=self.context();audit,consumer=case.claimed();record,owned=case.owned(audit)
        before=case.files()
        for code in ('artifact_context_too_large','artifact_capability_missing'):
            with self.subTest(code=code):
                decision=artifact_worker.preflight_cli_artifact(record,**owned,
                    fetch_brief=Mock(side_effect=artifact_worker.ArtifactWorkerError(code)),submit_saved=case.forbidden)
                self.assertEqual((decision['action'],decision['reason']),('reject',code))
        for status in (408,429):
            with self.subTest(status=status):
                body=io.BytesIO(b'PRIVATE_BODY')
                error=urllib.error.HTTPError('http://127.0.0.1/fixture',status,'PRIVATE',{},body)
                decision=artifact_worker.preflight_cli_artifact(record,**owned,
                    fetch_brief=Mock(side_effect=error),submit_saved=case.forbidden)
                self.assertEqual(decision['action'],'wait')
                self.assertTrue(body.closed)
        self.assertEqual(case.files(),before)

    def test_only_literal_true_can_release_api_transport_as_success(self):
        for admitted in (1,'admitted',{'status':'admitted'}):
            with self.subTest(admitted=admitted):
                case=self.context()
                instance,attempt,audit,consumer,record,owned=case.api_scope()
                client=case.queue_client(instance,consumer=consumer)
                self.assertEqual(artifact_worker.settle_api_artifact(client,audit['dispatch_id'],
                    runtime_path=owned['runtime_path'],admitted=admitted,local_ended=True),'settled')
                self.assertEqual(client.inspect(audit['dispatch_id'])['state'],'failed')

    def test_nested_json_is_invalid_request_and_get_body_is_explicitly_oversize(self):
        case=transport_fixture.ArtifactTransportTests();self.addCleanup(case.doCleanups);case.setUp()
        before=case.case.files()
        response=case.client.post('/api/artifact-results',headers=case.headers,
            content=b'{"nested":'+b'['*1500+b'0'+b']'*1500+b'}')
        self.assertEqual(response.status_code,400)
        self.assertEqual(response.json()['code'],'artifact_invalid_request')
        response=case.client.request('GET',case.base,headers=case.headers,content=b'x')
        self.assertEqual(response.status_code,413)  # GET has an explicit zero-byte body cap.
        self.assertEqual(response.json()['code'],'artifact_request_too_large')
        self.assertEqual(case.case.files(),before)

if __name__=='__main__':unittest.main()
