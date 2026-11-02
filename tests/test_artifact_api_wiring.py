"""Actual nested call_model and API release races; controlled provider/process observations."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch

import artifact_worker
from tests import test_artifact_workers as fixture

ROOT = Path(__file__).resolve().parents[1]

class ArtifactApiWiringTests(unittest.TestCase):
    def test_actual_call_model_default_and_per_result_observation(self):
        tree = ast.parse((ROOT / 'src' / 'wrapper_api.py').read_text(encoding='utf-8'))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        function = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == 'call_model')
        managed = {'seat': {'model':'requested'}, 'provider': {}}
        receipt = Mock()
        receipt.value = {'confirmed_model':'WRONG_SHARED_MODEL', 'authentication':'unknown'}
        namespace = {'managed':managed, 'receipt':receipt, 'queue':Mock(), 'shutdown':threading.Event(),
            '_cancellation_requested':lambda *args: False, 'Path':Path}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), '<actual call_model>', 'exec'), namespace)
        values = [{'content':'exact\r\n', 'confirmed_model':'first'},
                  {'content':'next', 'confirmed_model':'second'}, {'content':'legacy', 'confirmed_model':None}]
        with patch('api_invocation.run_completion', side_effect=deepcopy(values)):
            self.assertEqual(namespace['call_model']([], 'one', include_observation=True), values[0])
            self.assertEqual(namespace['call_model']([], 'two', include_observation=True), values[1])
            self.assertEqual(namespace['call_model']([], 'three'), 'legacy')

    def context(self):
        case = fixture.ArtifactWorkerTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        return case

    def test_actual_nested_artifact_handler_admits_exact_bytes_and_replays_without_chat(self):
        case = self.context()
        instance, attempt, audit, consumer, record, owned = case.api_scope()
        client = case.queue_client(instance, consumer=consumer)
        tree = ast.parse((ROOT / 'src' / 'wrapper_api.py').read_text(encoding='utf-8'))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        functions = [n for n in main.body if isinstance(n, ast.FunctionDef)
                     and n.name in ('call_model', 'handle_artifact_trigger')]
        self.assertEqual(len(functions), 2)
        receipt = Mock()
        receipt.value = {'authentication':'unknown', 'confirmed_model':'UNTRUSTED_SHARED'}
        snapshot = __import__('json').loads(attempt['snapshot'].read_text(encoding='utf-8'))
        namespace = {'managed':snapshot, 'managed_args':SimpleNamespace(seat_file=str(attempt['snapshot'])),
            'birth':{'wrapper_protocol':owned['manifest']}, 'queue':client, 'shutdown':threading.Event(),
            'receipt':receipt, 'set_working':Mock(), 'Path':Path, 'server_port':18300,
            'get_token':lambda:'TEST_ONLY', 'artifact_attempt':{'dispatch_id':None}, 'unresolved_dispatches':set(),
            '_ManagedProviderFailure':__import__('wrapper_api')._ManagedProviderFailure,
            'urllib':__import__('urllib'),
            'read_messages':Mock(side_effect=AssertionError('Mutable chat was read')),
            'send_message':Mock(side_effect=AssertionError('Artifact leaked to chat'))}
        exec(compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])), '<actual nested API functions>', 'exec'), namespace)
        transport = SimpleNamespace(fetch_delivery=lambda brief:case.authority.get_delivery(brief, instance),
            fetch_parent=lambda brief:case.authority.get_parent(brief, instance),
            submit_saved=lambda saved:case.authority.admit_saved(saved, instance),
            reject_response=lambda *args: self.fail('Unexpected rejection'))
        markdown = '# Exact café\r\nnew line'
        with patch('artifact_worker.ArtifactHTTP', return_value=transport), patch('api_invocation.run_completion',
                return_value={'content':__import__('json').dumps({'kind':'artifact','markdown':markdown}),
                              'confirmed_model':'same-call-model'}) as model:
            self.assertTrue(namespace['handle_artifact_trigger'](record))
            self.assertTrue(namespace['handle_artifact_trigger'](record))
        self.assertEqual(model.call_count, 1)
        namespace['read_messages'].assert_not_called()
        namespace['send_message'].assert_not_called()
        version = case.artifacts.get_version(case.artifacts.get_request(audit['request_id'])['version_id'])
        self.assertEqual(version['markdown'], markdown)
        self.assertEqual(version['metadata']['provenance']['observation']['confirmed_model'], 'same-call-model')
        self.assertEqual(client.inspect(audit['dispatch_id'])['state'], 'released')

    def test_cancel_between_result_and_release_and_after_inspect_uses_exact_receipt(self):
        for timing in ('before_settle', 'after_inspect'):
            with self.subTest(timing=timing):
                case = self.context()
                instance, attempt, audit, consumer, record, owned = case.api_scope()
                client = case.queue_client(instance, consumer=consumer)
                barrier = threading.Event()
                cancelled = threading.Event()
                failures = []
                original = client.inspect
                def inspect(dispatch):
                    value = original(dispatch)
                    if timing == 'after_inspect' and not cancelled.is_set():
                        barrier.set()
                        if not cancelled.wait(5):
                            raise AssertionError('Cancel did not complete')
                    return value
                client.inspect = inspect
                def cancel():
                    try:
                        if not barrier.wait(5):
                            raise AssertionError('No result/inspect rendezvous')
                        case.authority.cancel_request(audit['request_id'])
                    except BaseException as exc:
                        failures.append(exc)
                    finally:
                        cancelled.set()
                thread = threading.Thread(target=cancel)
                thread.start()
                try:
                    if timing == 'before_settle':
                        barrier.set()
                        self.assertTrue(cancelled.wait(5))
                    result = artifact_worker.settle_api_artifact(client, audit['dispatch_id'],
                        runtime_path=owned['runtime_path'], admitted=False, local_ended=True)
                finally:
                    barrier.set()
                    thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertFalse(failures, failures)
                self.assertEqual(result, 'settled')
                final = case.trigger.queue.owned(instance, audit['dispatch_id'])
                self.assertEqual(final['state'], 'cancelled')
                self.assertEqual(final['cancellation']['status'], 'local_ended')
                self.assertFalse(any(call[0] == 'claim' for call in client.calls))

    def test_cancel_after_admitted_ack_refuses_and_transport_releases_once(self):
        case = self.context()
        instance, attempt, audit, consumer, record, owned = case.api_scope()
        saved = case.sealed_fixture_record(audit, consumer, observation={'confirmed_model': 'fixture-model', 'confirmation_reason': 'api_response'})
        ack = case.authority.admit_saved(saved, instance)
        with self.assertRaises(case.storage.ArtifactConflict):
            case.authority.cancel_request(audit['request_id'])
        client = case.queue_client(instance, consumer=consumer)
        for _ in range(2):
            self.assertEqual(artifact_worker.settle_api_artifact(client, audit['dispatch_id'],
                runtime_path=owned['runtime_path'], admitted=True, local_ended=True), 'settled')
        self.assertEqual(sum(call[0] == 'release' for call in client.calls), 1)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['version_id'], ack['version_id'])

    def test_unresolved_invocation_never_releases_or_invents_local_end(self):
        case = self.context()
        instance, attempt, audit, consumer, record, owned = case.api_scope()
        client = case.queue_client(instance, consumer=consumer)
        with patch('artifact_worker.artifact_api_cancellation_status', return_value='unresolved'):
            self.assertEqual(artifact_worker.settle_api_artifact(client, audit['dispatch_id'],
                runtime_path=owned['runtime_path'], admitted=False), 'held')
            self.assertEqual(case.trigger.queue.owned(instance, audit['dispatch_id'])['state'], 'uncertain')
            case.authority.cancel_request(audit['request_id'])
            self.assertEqual(artifact_worker.settle_api_artifact(client, audit['dispatch_id'],
                runtime_path=owned['runtime_path'], admitted=False), 'held')
        self.assertFalse(any(call[0] == 'release' for call in client.calls))
        final = case.trigger.queue.owned(instance, audit['dispatch_id'])
        self.assertEqual(final['state'], 'cancelling')
        self.assertEqual(final['cancellation']['status'], 'unresolved')

if __name__ == '__main__':
    unittest.main()
