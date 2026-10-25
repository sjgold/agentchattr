"""Root-owned private brief/outbox persistence; no generation or admission."""
from copy import deepcopy
import importlib
import io
import json
import unittest
from unittest.mock import patch
import urllib.error

from artifact_store import ArtifactConflict, ArtifactUnavailable, request_ids
from tests import test_artifact_protocol as protocol_fixture
from tests import test_result_outbox as runtime_fixture


class ArtifactDeliveryTests(unittest.TestCase):
    def context(self):
        case = runtime_fixture.ResultOutboxTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        return case

    def brief(self):
        payload = protocol_fixture.ArtifactProtocolTests().payload()
        ids = request_ids(payload['request_id'])
        return {**{key: payload[key] for key in ('version', 'purpose', 'brief_id', 'request_id',
            'lineage_id', 'attempt_id', 'dispatch_id', 'scope_sha256', 'expected_parent')},
            'packet_id': ids['packet_id'], 'producer': {'identity_id': payload['seat_identity_id'],
                'adapter': 'cli', **{key: payload[key] for key in ('launch_attempt', 'launch_nonce', 'fingerprint')}},
            'instruction': 'Write café\r\nexactly.', 'format': 'Markdown', 'input_revision': None, 'source_run': None}

    def test_private_brief_put_once_preserves_first_secret_and_conflicts_before_write(self):
        module = importlib.import_module('artifact_brief')
        case = self.context()
        store = module.ArtifactBriefStore(case.root)
        body = self.brief()
        owner = {'adapter': 'cli', 'dispatch_id': body['dispatch_id'],
            'seat_identity_id': body['producer']['identity_id'],
            **{key: body['producer'][key] for key in ('launch_attempt', 'launch_nonce', 'fingerprint')}}
        self.assertEqual(store.put(body, owner=owner), body['brief_id'])
        saved = store.get_private(body['brief_id'])
        self.assertEqual(set(saved), set(body) | {'_artifact_seal'})
        self.assertRegex(saved['_artifact_seal']['seal_secret'], '^[0-9a-f]{64}$')
        path = case.root / 'artifact_briefs' / 'requests' / (body['brief_id'] + '.json')
        before = path.read_bytes()
        store.put(deepcopy(body), owner=deepcopy(owner))
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ArtifactConflict):
            store.put({**body, 'instruction': 'Changed intent'}, owner=owner)
        self.assertEqual(path.read_bytes(), before)
        saved['_artifact_seal']['owner'].clear()
        self.assertEqual(store.get_private(body['brief_id'])['_artifact_seal']['owner'], owner)

    def test_owned_outbox_exact_bytes_repeat_ack_and_no_poison_after_admission(self):
        module = importlib.import_module('artifact_delivery')
        case = self.context()
        payload = protocol_fixture.ArtifactProtocolTests().payload()
        payload.update(launch_attempt=case.snapshot['attempt'],
            launch_nonce=case.snapshot['ownership']['launch_nonce'],
            fingerprint=case.snapshot['ownership']['fingerprint'],
            observation={'confirmed_model': 'fixture-model', 'confirmation_reason': 'api_response'})
        box = module.ArtifactOutbox(case.runtime)
        self.assertIsNone(box.find(payload['dispatch_id']))
        record = box.save(payload, case.secret)
        path = case.runtime / 'artifact_results' / (payload['dispatch_id'] + '.json')
        before = path.read_bytes()
        self.assertEqual(module.ArtifactOutbox(case.runtime).save(deepcopy(payload), case.secret), record)
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ArtifactConflict):
            box.save({**payload, 'markdown': 'A different version'}, case.secret)
        self.assertEqual(path.read_bytes(), before)
        first = box.acknowledge(payload['dispatch_id'], payload['dispatch_id'])
        self.assertEqual(first['accepted_event_id'], payload['dispatch_id'])
        self.assertEqual(box.get_ack(payload['dispatch_id']), first)
        self.assertEqual(box.acknowledge(payload['dispatch_id'], payload['dispatch_id']), first)
        with self.assertRaises(ArtifactConflict):
            box.quarantine(payload['dispatch_id'], 'f' * 32, 'invalid_response')
        self.assertIsNone(box.get_disposition(payload['dispatch_id']))
        self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['payload']['markdown'], payload['markdown'])

    def saved(self):
        module = importlib.import_module('artifact_delivery')
        case = self.context()
        payload = protocol_fixture.ArtifactProtocolTests().payload()
        payload.update(launch_attempt=case.snapshot['attempt'], launch_nonce=case.snapshot['ownership']['launch_nonce'],
            fingerprint=case.snapshot['ownership']['fingerprint'],
            observation={'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'})
        box = module.ArtifactOutbox(case.runtime)
        return module, case, box, box.save(payload, case.secret)

    def test_http_duplicate_ack_is_bounded_validated_and_acknowledged_without_generation(self):
        module, _, box, record = self.saved()
        payload = record['payload']
        import hashlib
        ack = {'status': 'admitted', 'event_id': payload['dispatch_id'], 'request_id': payload['request_id'],
            'version_id': request_ids(payload['request_id'])['version_id'],
            'sha256': hashlib.sha256(payload['markdown'].encode('utf-8')).hexdigest()}
        sent = []
        def submit(saved):
            sent.append(saved)
            raise urllib.error.HTTPError('http://127.0.0.1/fixture-only', 409, 'duplicate', {},
                                         io.BytesIO(json.dumps(ack).encode('utf-8')))
        self.assertEqual(module.deliver_saved_artifact(box, record, submit), ack)
        self.assertEqual(sent, [record])
        self.assertEqual(box.get_ack(payload['dispatch_id'])['accepted_event_id'], payload['dispatch_id'])

    def test_terminal_quarantine_is_not_ack_and_index_write_fault_preserves_result(self):
        module, _, box, record = self.saved()
        dispatch = record['payload']['dispatch_id']
        before = box.get(dispatch)
        with patch.object(module, 'atomic_json', side_effect=OSError('PRIVATE_PATH')):
            with self.assertRaises(ArtifactUnavailable):
                box.acknowledge(dispatch, dispatch)
        self.assertEqual(box.get(dispatch), before)
        self.assertIsNone(box.get_ack(dispatch))
        response = {'status': 'quarantined', 'diagnostic_id': 'f' * 32, 'reason': 'cancelled',
                    'request_terminal': True, 'received_truncated': False, 'notice': None}
        with self.assertRaises(module.ArtifactRejected):
            module.deliver_saved_artifact(box, record, lambda value: response)
        self.assertIsNone(box.get_ack(dispatch))
        self.assertEqual(box.get_disposition(dispatch)['reason'], 'cancelled')
        self.assertEqual(box.get(dispatch), before)


if __name__ == '__main__':
    unittest.main()
