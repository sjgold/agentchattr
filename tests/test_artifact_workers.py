"""Artifact worker components with fixture-controlled support and callbacks.

Real owned files, service, queue and current-boot bindings; process observations
and transport/provider callbacks are doubles. No native/network acceptance.
"""
from copy import deepcopy
import importlib
import json
import unittest
from unittest.mock import Mock
import uuid

from tests import test_artifact_admission as fixture


class ArtifactWorkerTests(unittest.TestCase):
    def setUp(self):
        fixture.ArtifactAdmissionTests.setUp(self)

    setup_authority = fixture.ArtifactAdmissionTests.setup_authority
    launch_binding = fixture.ArtifactAdmissionTests.launch_binding
    new_request = fixture.ArtifactAdmissionTests.new_request
    prepare = fixture.ArtifactAdmissionTests.prepare
    claim = fixture.ArtifactAdmissionTests.claim
    claimed = fixture.ArtifactAdmissionTests.claimed
    files = fixture.ArtifactAdmissionTests.files
    sealed_fixture_record = fixture.ArtifactAdmissionTests.sealed_fixture_record

    def owned(self, audit, instance=None, attempt=None):
        instance = instance or self.instance
        attempt = attempt or self.attempt
        record = self.trigger.queue.owned(instance, audit['dispatch_id'])
        manifest = json.loads(attempt['snapshot'].read_text(encoding='utf-8'))['wrapper_protocol']
        return record, {'runtime_path': attempt['snapshot'].parent,
                        'manifest': manifest, 'consumer_id': record['consumer_id']}

    @staticmethod
    def forbidden(*args, **kwargs):
        raise AssertionError('Forbidden callback ran.')

    def test_managed_dispatch_validation_refuses_unknown_unbound_or_wrong_consumer_without_effects(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        audit, _ = self.claimed()
        record, owned = self.owned(audit)
        before = self.files()
        for change in ({'purpose': 'unknown'}, {'artifact_attempt_id': uuid.uuid4().hex},
                       {'review_brief_id': uuid.uuid4().hex}, {'text': 'MUST_NOT_INJECT'}):
            altered = deepcopy(record)
            altered['envelope'].update(change)
            with self.subTest(change=change), self.assertRaises(worker.ArtifactWorkerError) as caught:
                worker.validate_artifact_dispatch(altered, **owned)
            self.assertEqual(caught.exception.code, 'artifact_invalid_dispatch')
            self.assertEqual(self.files(), before)
        with self.assertRaises(worker.ArtifactWorkerError) as caught:
            worker.validate_artifact_dispatch(record, **{**owned, 'consumer_id': uuid.uuid4().hex})
        self.assertEqual(caught.exception.code, 'artifact_invalid_dispatch')
        with self.assertRaises(worker.ArtifactWorkerError):
            worker.validate_artifact_dispatch(record, **{**owned, 'runtime_path': None, 'manifest': None})
        self.assertEqual(self.files(), before)

    def test_exact_owned_cli_saved_result_redelivers_ack_before_any_brief_fetch_or_injection(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        audit, consumer = self.claimed()
        record, owned = self.owned(audit)
        signed = self.sealed_fixture_record(audit, consumer, '# Saved café\r\nexact')
        private = self.briefs.get_private(audit['brief_id'])
        box = importlib.import_module('artifact_delivery').ArtifactOutbox(owned['runtime_path'])
        saved = box.save(signed['payload'], private['_artifact_seal']['seal_secret'])
        saved_bytes = (owned['runtime_path'] / 'artifact_results' / (audit['dispatch_id'] + '.json')).read_bytes()
        submit = Mock(side_effect=lambda value: self.authority.admit_saved(value, self.instance))
        decision = worker.preflight_cli_artifact(record, **owned,
            fetch_brief=self.forbidden, submit_saved=submit)
        self.assertEqual(set(decision), {'action', 'prompt', 'admission', 'reason'})
        self.assertEqual(decision['action'], 'complete')
        self.assertIsNone(decision['prompt'])
        self.assertIsNone(decision['reason'])
        self.assertEqual(decision['admission']['status'], 'admitted')
        self.assertEqual(decision['admission']['event_id'], audit['dispatch_id'])
        submit.assert_called_once_with(saved)
        self.assertEqual((owned['runtime_path'] / 'artifact_results' / (audit['dispatch_id'] + '.json')).read_bytes(), saved_bytes)
        self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 1)
        self.assertEqual(self.trigger.queue.owned(self.instance, audit['dispatch_id'])['state'], 'dispatched')


if __name__ == '__main__':
    unittest.main()
