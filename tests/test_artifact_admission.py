"""Real artifact admission components, synthetic supported managed bindings only.

Shared temp root/catalog/registry/queue; process and native observations are doubles.
No app factory, worker, provider, native process or network acceptance is claimed.
"""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
import uuid

from api_seat_runtime import SeatManager
from api_seats import SeatStore
from tests import test_artifact_capability as capability_fixture
from tests import test_artifact_store as store_fixture
from tests import test_channel_import as channel_fixture


class ArtifactAdmissionTests(unittest.TestCase):
    def setUp(self):
        channel_fixture.ChannelImportTests.setUp(self)

    def files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def setup_authority(self):
        self.module = importlib.import_module('artifact_service')
        self.storage = importlib.import_module('artifact_store')
        self.protocol = importlib.import_module('artifact_protocol')
        self.briefs = importlib.import_module('artifact_brief').ArtifactBriefStore(self.root)
        self.artifacts = self.storage.ArtifactStore(self.root)
        self.artifacts.bind_channel_policy(lambda: self.service)
        enabled = patch('runtime_protocol.SUPPORTED_CAPABILITIES', ('artifact-v1',))
        enabled.start()  # Explicit fixture-controlled support, not production runtime support.
        self.addCleanup(enabled.stop)
        providers = {'fake-cli': {'command': sys.executable, 'cwd': str(self.root),
            'cli_args': [], 'mcp_inject': 'env', 'mcp_env_var': 'ARTIFACT_TEST_MCP'},
            'fake-api': {'type': 'api', 'base_url': 'http://127.0.0.1:19999/v1'}}
        common = {'reasoning': None, 'launch_profile': 'standard', 'secret_ref': ''}
        self.package = {'id': 'team', 'name': 'Fixture', 'seats': [
            dict(common, id='cli', name='CLI', adapter='cli', provider='fake-cli', model='fixture-cli'),
            dict(common, id='api', name='API', adapter='openai-compatible', provider='fake-api', model='fixture-api')]}
        seat_store = SeatStore(self.root, providers)
        seat_store.save(self.package)
        self.manager = SeatManager(Path(__file__).resolve().parents[1],
            {'server': {'port': 18300}}, seat_store, self.registry, monitor=False)
        self.processes = []
        def spawn(*args, **kwargs):
            process = Mock()
            process.poll.return_value = None
            process.returncode = None
            def ended(*args, **kwargs):
                process.poll.return_value = 0
                process.returncode = 0
                return 0
            process.wait.side_effect = ended
            process.terminate.side_effect = ended
            self.processes.append(process)
            return process
        seam = patch('api_seat_runtime.subprocess.Popen', side_effect=spawn)
        self.spawn = seam.start()
        self.addCleanup(seam.stop)
        self.addCleanup(self.manager.shutdown)
        self.instance, self.attempt, _ = self.launch_binding('cli')
        self.authority = self.module.ArtifactService(store=self.artifacts, briefs=self.briefs,
            agents=self.trigger, seats=self.manager, channels=self.service, registry=self.registry)
        self.trigger.bind_artifact_policy(lambda: self.authority)
        self.trigger.queue.bind_artifact_policy(lambda: self.authority)

    def launch_binding(self, seat):
        return capability_fixture.ArtifactCapabilityTests.launch_binding(self, seat, supported=True)

    def new_request(self, *, instance=None, channel='review', lineage_id=None, parent=None):
        instance = instance or self.instance
        request_id = uuid.uuid4().hex
        packet = store_fixture.ArtifactStoreTests.packet(self, channel)
        scope = self.artifacts.put_packet(request_id, packet)
        ids = self.storage.request_ids(request_id)
        owner = self.manager.artifact_producer(instance)
        provenance = self.manager.launch_provenance(instance)
        requested = provenance['effective']['seat']['model']
        audit = {'version': 1, 'purpose': 'artifact-v1', 'request_id': request_id,
            'lineage_id': lineage_id or ids['lineage_id'], 'attempt_id': ids['attempt_id'],
            'dispatch_id': ids['dispatch_id'], 'brief_id': ids['brief_id'],
            'original_channel': channel, 'requester': 'operator',
            'producer': {'name': instance['name'], 'identity_id': instance['identity_id'],
                'adapter': owner['adapter'], 'launch_attempt': owner['launch_attempt'],
                'launch_nonce': owner['launch_nonce'], 'fingerprint': owner['fingerprint'],
                'requested_model': requested, 'requested_model_reason': None,
                'capabilities': ['artifact-v1']},
            'source_run': None, 'scope': scope, 'instruction': 'Write an exact evidence artifact.',
            'format': 'Markdown', 'expected_parent': deepcopy(parent), 'created_at': 100.0}
        return audit, packet

    def prepare(self, **options):
        audit, packet = self.new_request(**options)
        result = self.authority.prepare_request(audit, packet, audit['request_id'])
        self.assertEqual(result['request']['state'], 'queued')
        return audit

    def claim(self, audit, instance=None):
        instance = instance or self.instance
        consumer = 'fixture-consumer-' + uuid.uuid4().hex
        record = self.trigger.queue.claim(instance, consumer)
        self.assertEqual(record['envelope']['dispatch_id'], audit['dispatch_id'])
        return consumer

    def test_own_unclaimed_cli_submit_refuses_without_file_version_or_state_effects(self):
        self.setup_authority()
        audit = self.prepare()
        before = self.files()
        row = self.artifacts.get_request(audit['request_id'])
        with self.assertRaises((self.module.ArtifactAccessError, self.storage.ArtifactConflict)):
            self.authority.submit_cli(audit['brief_id'], '# Unclaimed café\r\nnot admitted', self.instance)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.artifacts.get_request(audit['request_id']), row)
        self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 0)

    def test_exact_claimed_cli_admits_once_raw_unicode_crlf_and_replays_original_ack(self):
        self.setup_authority()
        audit = self.prepare()
        consumer = self.claim(audit)
        public = self.authority.get_brief(audit['brief_id'], self.instance)
        self.assertEqual(public['packet'], store_fixture.ArtifactStoreTests.packet(self))
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'active')
        text = '\ufeff# Café 日本語 e\u0301\r\n\r\nExact evidence.\r\n'
        ack = self.authority.submit_cli(audit['brief_id'], text, self.instance)
        self.assertEqual(ack, {'status': 'admitted', 'event_id': audit['dispatch_id'],
            'request_id': audit['request_id'], 'version_id': self.storage.request_ids(audit['request_id'])['version_id'],
            'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()})
        saved = self.artifacts.get_version(ack['version_id'])
        self.assertEqual(saved['markdown'].encode('utf-8'), text.encode('utf-8'))
        before = self.files()
        self.assertEqual(self.authority.submit_cli(audit['brief_id'], text, self.instance), ack)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 1)
        owned = self.trigger.queue.owned(self.instance, audit['dispatch_id'])
        self.assertEqual(owned['consumer_id'], consumer)
        self.assertEqual(owned['state'], 'dispatched')  # Admission is not transport settlement.


if __name__ == '__main__':
    unittest.main()
