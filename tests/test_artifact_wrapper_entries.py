"""Actual wrapper entry routing and pre-change goldens, controlled IO only."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from dispatch_queue import QueueStore
from artifact_store import request_ids
import wrapper


ROOT = Path(__file__).resolve().parents[1]


class ArtifactWrapperEntryTests(unittest.TestCase):
    @staticmethod
    def artifact_record():
        request = '1' * 32
        ids = request_ids(request)
        return {'state': 'dispatched', 'consumer_id': 'fixture-consumer', 'events': [],
            'envelope': {'dispatch_id': ids['dispatch_id'], 'purpose': 'artifact-v1', 'channel': 'peer',
                'artifact_request_id': request, 'artifact_attempt_id': ids['attempt_id'],
                'artifact_brief_id': ids['brief_id'], 'artifact_scope_sha256': 'b' * 64,
                'target_identity_id': 'a' * 32, 'target_agent_name': 'fixture-author'}}

    def test_actual_unconfigured_cli_watcher_refuses_artifact_before_chat_prompt_or_injection(self):
        record = self.artifact_record()
        stop = threading.Event()
        client = Mock()
        client.consumer_id = record['consumer_id']
        client.claim.return_value = deepcopy(record)
        client.inspect.return_value = deepcopy(record)
        def done(*args, **kwargs):
            stop.set()
            return record
        client.acknowledge.side_effect = done
        client.release.side_effect = done
        inject = Mock(return_value=True)
        # A bounded stop also protects the test if neither ACK nor release happens.
        original_wait = stop.wait
        def bounded_wait(timeout=None):
            stop.set()
            return original_wait(0)
        with patch('queue_client.QueueClient', return_value=client), patch.object(wrapper, '_fetch_role',
                return_value='Mutable role') as role, patch.object(wrapper, '_fetch_active_rules',
                return_value={'rules': ['Mutable rules']}) as rules, patch.object(stop, 'wait', bounded_wait), redirect_stdout(io.StringIO()):
            wrapper._queue_watcher(lambda: ('fixture-author', ROOT / '.audit-tmp' / 'unused-queue.jsonl'), inject,
                server_port=12345, get_token_fn=lambda: 'CONTROLLED_TEST_BEARER', stop_event=stop)
        inject.assert_not_called()
        role.assert_not_called()
        rules.assert_not_called()
        client.acknowledge.assert_not_called()
        client.release.assert_called_once_with(record['envelope']['dispatch_id'], failed=True,
                                               error_category='local_delivery_failure')

    def test_actual_api_dispatch_loop_forwards_artifact_record_before_legacy_handle_trigger(self):
        tree = ast.parse((ROOT / 'src' / 'wrapper_api.py').read_text(encoding='utf-8'))
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        loops = [node for node in ast.walk(main) if isinstance(node, ast.While)
            and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == 'handle_trigger' for call in ast.walk(node))]
        self.assertEqual(len(loops), 1, 'Use the actual main dispatch loop, not a copied formatter.')
        stop, record = threading.Event(), self.artifact_record()
        client = Mock()
        client.claim.return_value = record
        legacy = Mock(return_value=True)
        artifact = Mock(return_value=True)
        namespace = {'shutdown': stop, 'queue': client, 'processed_dispatch': None, 'processed_ok': False,
            'unresolved_dispatches': set(), 'last_cancelled': [False], 'last_failure_category': [''],
            'last_failure_http_status': [None], 'handle_trigger': legacy, 'handle_artifact_trigger': artifact,
            'time': SimpleNamespace(sleep=lambda _: stop.set()), 'print': lambda *args, **kwargs: None}
        module = ast.fix_missing_locations(ast.Module(body=[loops[0]], type_ignores=[]))
        exec(compile(module, 'wrapper_api.py:actual-main-dispatch-loop', 'exec'), namespace)
        legacy.assert_not_called()
        artifact.assert_called_once_with(record)

    def test_legacy_chat_and_review_prompt_bytes_and_queue_calls_match_prechange_capture(self):
        golden = json.loads((ROOT / 'tests' / 'fixtures' / 'artifact_legacy_prompts.json').read_text(encoding='utf-8'))
        for kind, expected in golden['observations'].items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp') as directory:
                queue = QueueStore(directory)
                instance = {'name': 'fixture-author', 'identity_id': 'a' * 32}
                stop, calls, prompts = threading.Event(), [], []
                class Client:
                    consumer_id = 'legacy-consumer'
                    def claim(self):
                        calls.append(['claim'])
                        return queue.claim(instance, self.consumer_id)
                    def acknowledge(self, dispatch):
                        calls.append(['ack', dispatch])
                        value = queue.acknowledge(instance, dispatch, self.consumer_id)
                        self.release(dispatch)
                        stop.set()
                        return value
                    def release(self, dispatch):
                        calls.append(['release', dispatch])
                        return queue.release(instance, dispatch, self.consumer_id)
                    def uncertain(self, dispatch):
                        calls.append(['uncertain', dispatch])
                        return queue.uncertain(instance, dispatch, self.consumer_id)
                def inject(text):
                    prompts.append(text)
                    return True
                with patch('dispatch_queue.time.time', return_value=123.5):
                    queue.enqueue(instance, expected['envelope'])
                    with patch('queue_client.QueueClient', return_value=Client()), patch.object(wrapper, '_fetch_role',
                            return_value='Keep original role.'), patch.object(wrapper, '_fetch_active_rules',
                            return_value={'rules': ['Use exact evidence.', 'Keep source literal.']}), redirect_stdout(io.StringIO()):
                        wrapper._queue_watcher(lambda: (instance['name'], Path(directory) / 'unused_queue.jsonl'), inject,
                            is_multi_instance=True, server_port=12345, agent_name='fixture',
                            get_token_fn=lambda: 'TEST_BEARER_NEVER_CAPTURED', stop_event=stop)
                self.assertEqual([text.encode('utf-8') for text in prompts], [expected['prompt'].encode('utf-8')])
                self.assertEqual(calls, expected['calls'])
                self.assertEqual(queue.owned(instance, expected['envelope']['dispatch_id']), expected['record'])


if __name__ == '__main__':
    unittest.main()
