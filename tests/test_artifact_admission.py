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
            'cli_args': [], 'cli_model_args': ['--model', '{model}'],
            'mcp_inject': 'env', 'mcp_env_var': 'ARTIFACT_TEST_MCP'},
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

    def claimed(self, *, instance=None, **options):
        instance = instance or self.instance
        audit = self.prepare(instance=instance, **options)
        consumer = self.claim(audit, instance)
        self.authority.get_brief(audit['brief_id'], instance)
        return audit, consumer

    def sealed_fixture_record(self, audit, consumer, text='# Exact café\r\nresult', *, observation=None):
        """Trusted test signer, not model output or a live provider observation."""
        private = self.briefs.get_private(audit['brief_id'])
        producer = audit['producer']
        payload = {'version': 1, 'purpose': 'artifact-v1', 'result_id': audit['dispatch_id'],
            'dispatch_id': audit['dispatch_id'], 'request_id': audit['request_id'],
            'attempt_id': audit['attempt_id'], 'brief_id': audit['brief_id'],
            'lineage_id': audit['lineage_id'], 'scope_sha256': audit['scope']['sha256'],
            'expected_parent': deepcopy(audit['expected_parent']),
            'seat_identity_id': producer['identity_id'], 'launch_attempt': producer['launch_attempt'],
            'launch_nonce': producer['launch_nonce'], 'fingerprint': producer['fingerprint'],
            'consumer_id': consumer, 'kind': 'artifact', 'markdown': text,
            'observation': observation or {'confirmed_model': None, 'confirmation_reason': 'cli_model_unverified'},
            'created_at': 200.0}
        return self.protocol.seal_result(payload, private['_artifact_seal']['seal_secret'])

    def assert_refused(self, action):
        try:
            value = action()
        except (self.module.ArtifactAccessError, self.storage.ArtifactConflict,
                self.storage.ArtifactUnavailable):
            return None
        self.assertEqual(value['status'], 'quarantined')
        self.assertNotEqual(value.get('request_terminal'), True)
        return value

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

    def test_wrong_seat_unknown_brief_and_cancelling_claim_refuse_before_effects(self):
        self.setup_authority()
        audit, _ = self.claimed()
        self.registry.seed({'unmanaged': {'label': 'Unmanaged fixture'}})
        other = self.registry.register('unmanaged')
        for callback in (lambda: self.authority.get_brief(audit['brief_id'], other),
                         lambda: self.authority.submit_cli(audit['brief_id'], '# Wrong seat', other),
                         lambda: self.authority.get_brief(uuid.uuid4().hex, self.instance),
                         lambda: self.authority.get_delivery(audit['brief_id'], self.instance)):
            before = self.files()
            with self.assertRaises((self.module.ArtifactAccessError, self.storage.ArtifactConflict)):
                callback()
            self.assertEqual(self.files(), before)
        self.trigger.queue.cancel_dispatch(audit['dispatch_id'], uuid.uuid4().hex)
        before = self.files()
        for callback in (lambda: self.authority.get_brief(audit['brief_id'], self.instance),
                         lambda: self.authority.submit_cli(audit['brief_id'], '# Cancelling', self.instance)):
            with self.assertRaises((self.module.ArtifactAccessError, self.storage.ArtifactConflict)):
                callback()
            self.assertEqual(self.files(), before)
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'active')

    def test_scoped_wrong_attempt_scope_parent_consumer_diagnostics_do_not_poison_active_request(self):
        self.setup_authority()
        audit, consumer = self.claimed()
        original = self.sealed_fixture_record(audit, consumer)
        secret = self.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret']
        for field, value, reason in (
                ('attempt_id', uuid.uuid4().hex, 'wrong_attempt'),
                ('scope_sha256', '0' * 64, 'wrong_scope'),
                ('expected_parent', {'version_id': uuid.uuid4().hex, 'sequence': 1, 'sha256': '0' * 64}, 'wrong_parent'),
                ('consumer_id', uuid.uuid4().hex, 'wrong_identity')):
            with self.subTest(field=field):
                payload = deepcopy(original['payload'])
                payload[field] = value
                record = self.protocol.seal_result(payload, secret)
                result = self.authority.admit_saved(record, self.instance)
                self.assertEqual(result['status'], 'quarantined')
                self.assertEqual(result['reason'], reason)
                self.assertIs(result['request_terminal'], False)
                self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'active')
                self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 0)
        accepted = self.authority.admit_saved(original, self.instance)
        self.assertEqual(accepted['status'], 'admitted')
        self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 1)

    def test_current_identity_attempt_nonce_fingerprint_and_source_are_rechecked_at_submit(self):
        self.setup_authority()
        audit, _ = self.claimed()
        original = self.manager.artifact_producer(self.instance)
        # Read-only gate observation seams isolate every frozen-reference comparison.
        for field in ('identity_id', 'launch_attempt', 'launch_nonce', 'fingerprint'):
            changed = {**original, field: ('0' * 64 if field == 'fingerprint' else uuid.uuid4().hex)}
            with self.subTest(field=field), patch.object(self.manager, 'artifact_producer', return_value=changed):
                self.assert_refused(lambda: self.authority.submit_cli(audit['brief_id'], '# Stale binding', self.instance))
            self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'active')
            self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 0)
        with patch('runtime_protocol.sources_match', return_value=False):
            self.assert_refused(lambda: self.authority.submit_cli(audit['brief_id'], '# Changed source', self.instance))
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'active')
        self.assertEqual(self.authority.submit_cli(audit['brief_id'], '# Current binding', self.instance)['status'], 'admitted')

    def test_conflicting_duplicate_cannot_replace_head_or_original_ack_even_after_transport_release(self):
        self.setup_authority()
        audit, consumer = self.claimed()
        text = '# Original\r\nexact Unicode 日本語'
        ack = self.authority.submit_cli(audit['brief_id'], text, self.instance)
        original = self.artifacts.get_version(ack['version_id'])
        result = self.authority.submit_cli(audit['brief_id'], '# Conflicting duplicate', self.instance)
        self.assertEqual(result['status'], 'quarantined')
        self.assertEqual(result['reason'], 'conflicting_duplicate')
        self.assertIs(result['request_terminal'], False)
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'fulfilled')
        self.assertEqual(self.artifacts.get_version(ack['version_id']), original)
        self.trigger.queue.release(self.instance, audit['dispatch_id'], consumer)
        before = self.files()
        self.assertEqual(self.authority.submit_cli(audit['brief_id'], text, self.instance), ack)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 1)

    def test_cli_invalid_content_is_retryable_while_exact_api_invalid_response_is_terminal(self):
        self.setup_authority()
        audit, _ = self.claimed()
        for text, truncated in (('', False), (' \r\n\t', False), ('NUL\x00PRIVATE', False),
                                ('bad\ud800PRIVATE', False), ('x' * (self.protocol.MAX_RESULT_RECORD_BYTES + 1), True)):
            with self.subTest(truncated=truncated, size=len(text)):
                with self.assertRaises(self.module.ArtifactInputError) as caught:
                    self.authority.submit_cli(audit['brief_id'], text, self.instance)
                error = caught.exception
                self.assertEqual(error.code, 'invalid_content')
                self.assertRegex(error.diagnostic_id, r'^[0-9a-f]{32}$')
                self.assertIs(error.received_truncated, truncated)
                self.assertNotIn('PRIVATE', str(error))
                self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'active')
                self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 0)
                self.assertFalse(list(self.attempt['snapshot'].parent.glob('artifact_results/*.json')))
                if truncated:
                    row = next(row for row in self.artifacts.diagnostics()['rows'] if row['id'] == error.diagnostic_id)
                    self.assertEqual(row['byte_count'], 0)
                    self.assertEqual(row['sha256'], hashlib.sha256(b'').hexdigest())
                    self.assertIs(row['not_retained'], True)
                    self.assertIsNone(row['body_object_id'])
        self.assertEqual(self.authority.submit_cli(audit['brief_id'], '# Corrected first valid result', self.instance)['status'], 'admitted')
        api, _, _ = self.launch_binding('api')
        api_audit, _ = self.claimed(instance=api, channel='peer')
        delivery = self.authority.get_delivery(api_audit['brief_id'], api)
        self.assertEqual(delivery['consumer_id'], self.trigger.queue.owned(api, api_audit['dispatch_id'])['consumer_id'])
        result = self.authority.reject_response(api_audit['brief_id'], 'INVALID_PROVIDER_OUTPUT', api)
        self.assertEqual(set(result), {'status', 'diagnostic_id', 'reason', 'request_terminal', 'received_truncated', 'notice'})
        self.assertEqual(result['status'], 'quarantined')
        self.assertEqual(result['reason'], 'invalid_response')
        self.assertIs(result['request_terminal'], True)
        self.assertIs(result['received_truncated'], False)
        self.assertIsNone(result['notice'])
        self.assertEqual(self.artifacts.get_request(api_audit['request_id'])['state'], 'quarantined')
        self.assertEqual(self.artifacts.pending('peer'), [])

    def test_corrupt_packet_fails_only_exact_request_and_index_hold_never_admits_from_cache(self):
        self.setup_authority()
        audit, _ = self.claimed()
        packet_path = self.root / 'artifact_briefs' / 'packets' / (audit['scope']['packet_id'] + '.json')
        packet_path.write_bytes(b'{corrupt packet')
        with self.assertRaises(self.storage.ArtifactUnavailable):
            self.authority.submit_cli(audit['brief_id'], '# No source fallback', self.instance)
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'failed')
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['reason'], 'source_packet_unavailable')
        api, _, _ = self.launch_binding('api')
        peer, consumer = self.claimed(instance=api, channel='peer')
        record = self.sealed_fixture_record(peer, consumer,
            observation={'confirmed_model': 'fixture-confirmed', 'confirmation_reason': 'api_response'})
        self.assertEqual(self.authority.admit_saved(record, api)['status'], 'admitted')
        index = self.artifacts.path.read_bytes()
        self.artifacts.path.write_bytes(b'{corrupt index')
        before = self.files()
        with self.assertRaises(self.storage.ArtifactUnavailable):
            self.authority.submit_cli(audit['brief_id'], '# No cached fallback', self.instance)
        self.assertEqual(self.files(), before)
        self.artifacts.path.write_bytes(index)

    def test_archived_and_held_channels_fence_first_admission_but_cancel_and_ack_replay_remain(self):
        self.setup_authority()
        audit, _ = self.claimed()
        self.catalog.set_state('review', 'archived', expected_revision=self.catalog.snapshot()['revision'])
        before = self.files()
        with self.assertRaises(channel_fixture.ChannelConflict):
            self.authority.submit_cli(audit['brief_id'], '# Inactive', self.instance)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'active')
        cancelled = self.authority.cancel_request(audit['request_id'])
        self.assertEqual(cancelled['request']['state'], 'cancelled')
        try:
            late = self.authority.submit_cli(audit['brief_id'], '# Cancelled late output', self.instance)
        except (self.module.ArtifactAccessError, self.storage.ArtifactConflict):
            pass
        else:
            self.assertEqual(late['status'], 'quarantined')
            self.assertEqual(late['reason'], 'cancelled')
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'cancelled')
        api, _, _ = self.launch_binding('api')
        peer, consumer = self.claimed(instance=api, channel='peer')
        record = self.sealed_fixture_record(peer, consumer,
            observation={'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'})
        self.catalog.begin('rename', 'peer', 'peer-new', request_id=uuid.uuid4().hex,
                           expected_revision=self.catalog.snapshot()['revision'])
        before = self.files()
        with self.assertRaises(channel_fixture.ChannelConflict):
            self.authority.admit_saved(record, api)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.artifacts.get_request(peer['request_id'])['state'], 'active')

    def test_two_lineages_progress_independently_and_same_parent_cas_never_enqueues_rival(self):
        self.setup_authority()
        first = self.prepare()
        second = self.prepare(channel='peer')
        first_consumer = self.claim(first)
        self.authority.get_brief(first['brief_id'], self.instance)
        accepted = self.authority.submit_cli(first['brief_id'], '# First lineage', self.instance)
        self.trigger.queue.release(self.instance, first['dispatch_id'], first_consumer)
        second_consumer = self.claim(second)
        self.authority.get_brief(second['brief_id'], self.instance)
        self.assertEqual(self.authority.submit_cli(second['brief_id'], '# Independent lineage', self.instance)['status'], 'admitted')
        self.trigger.queue.release(self.instance, second['dispatch_id'], second_consumer)
        metadata = self.artifacts.get_version(accepted['version_id'])['metadata']
        parent = {'version_id': metadata['id'], 'sequence': metadata['sequence'], 'sha256': metadata['sha256']}
        revision = self.prepare(lineage_id=first['lineage_id'], parent=parent)
        rival, packet = self.new_request(lineage_id=first['lineage_id'], parent=parent)
        queue_before = self.trigger.queue.path.read_bytes()
        with self.assertRaises(self.storage.ArtifactConflict):
            self.authority.prepare_request(rival, packet, rival['request_id'])
        self.assertEqual(self.trigger.queue.path.read_bytes(), queue_before)
        self.assertIsNone(self.artifacts.get_request(rival['request_id']))
        self.assertEqual(self.artifacts.get_request(revision['request_id'])['state'], 'queued')
        self.assertEqual(self.artifacts.list_versions(first['lineage_id'])['count'], 1)
        self.assertEqual(self.artifacts.list_versions(second['lineage_id'])['count'], 1)

    def test_disabled_policy_and_legacy_wrapper_refuse_enqueue_without_effects(self):
        protocol = importlib.import_module('runtime_protocol')
        self.assertEqual(protocol.SUPPORTED_CAPABILITIES, ('artifact-v1',))  # Reviewed activation default.
        self.setup_authority()
        audit, packet = self.new_request()
        before = self.files()
        with patch.object(protocol, 'SUPPORTED_CAPABILITIES', ()):
            with self.assertRaises((self.module.ArtifactAccessError, self.storage.ArtifactConflict)):
                self.authority.prepare_request(audit, packet, audit['request_id'])
        self.assertEqual(self.files(), before)
        old, old_attempt, _ = capability_fixture.ArtifactCapabilityTests.launch_binding(self, 'api', supported=False)
        old_audit, old_packet = self.new_request()
        old_audit['producer'] = {**old_audit['producer'], 'name': old['name'], 'identity_id': old['identity_id'],
            'adapter': 'openai-compatible', 'launch_attempt': old_attempt['id'],
            'launch_nonce': old_attempt['ownership']['launch_nonce'], 'fingerprint': old_attempt['ownership']['fingerprint'],
            'requested_model': old_attempt['effective']['seat']['model']}
        before = self.files()
        with self.assertRaises((self.module.ArtifactAccessError, self.storage.ArtifactConflict)):
            self.authority.prepare_request(old_audit, old_packet, old_audit['request_id'])
        self.assertEqual(self.files(), before)
        self.assertFalse(list(self.root.glob('artifacts/objects/*.md')))

    def test_projections_are_detached_and_never_expose_private_seal_nonce_or_credentials(self):
        self.setup_authority()
        audit = self.prepare()
        projected = self.authority.resume_request(audit['request_id'])
        self.assertEqual(set(projected), {'request', 'dispatch', 'admission', 'transport_settled', 'notice', 'warning'})
        self.assertEqual(set(projected['dispatch']), {'dispatch_id', 'state'})
        private = self.briefs.get_private(audit['brief_id'])
        self.claim(audit)
        public = self.authority.get_brief(audit['brief_id'], self.instance)
        self.assertEqual(set(public), {'brief', 'packet'})
        for value in (projected, public):
            serialized = json.dumps(value, ensure_ascii=False)
            self.assertNotIn('seal_secret', serialized)
            self.assertNotIn('_artifact_seal', serialized)
            self.assertNotIn('launch_nonce', serialized)
            self.assertNotIn(private['_artifact_seal']['seal_secret'], serialized)
            self.assertNotIn(audit['producer']['launch_nonce'], serialized)
            self.assertNotIn(self.instance['token'], serialized)
        public['packet']['messages'][0]['text'] = 'external mutation'
        public['brief']['instruction'] = 'external mutation'
        projected['request']['audit']['instruction'] = 'external mutation'
        fresh = self.authority.get_brief(audit['brief_id'], self.instance)
        self.assertEqual(fresh['packet'], store_fixture.ArtifactStoreTests.packet(self))
        self.assertEqual(fresh['brief']['instruction'], audit['instruction'])
        self.assertEqual(self.artifacts.get_request(audit['request_id'])['audit']['instruction'], audit['instruction'])
        self.assertFalse((self.root / 'artifacts' / 'objects').exists())


if __name__ == '__main__':
    unittest.main()
