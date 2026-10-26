"""Root-owned crash/restart tests with controlled managed-process observations."""
from unittest.mock import patch
import json
import hashlib
import uuid
import unittest

from artifact_brief import ArtifactBriefStore
from artifact_delivery import ArtifactOutbox
from artifact_service import ArtifactService
from artifact_store import ArtifactStore
from tests import test_artifact_admission as fixture


class ArtifactRecoveryTests(unittest.TestCase):
    def context(self):
        case = fixture.ArtifactAdmissionTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        return case

    def reload(self, case):
        case.artifacts = ArtifactStore(case.root)
        case.artifacts.bind_channel_policy(lambda: case.service)
        case.briefs = ArtifactBriefStore(case.root)
        case.authority = ArtifactService(store=case.artifacts, briefs=case.briefs,
            agents=case.trigger, seats=case.manager, channels=case.service, registry=case.registry)

    def save(self, case, audit, consumer):
        record = case.sealed_fixture_record(audit, consumer)
        box = ArtifactOutbox(case.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
        private = case.briefs.get_private(audit['brief_id'])
        box.save(record['payload'], private['_artifact_seal']['seal_secret'])
        return box, record

    def test_three_after_write_crashes_reload_and_repair_without_duplicate_dispatch_or_seal(self):
        for seam in ('reserve', 'brief', 'enqueue'):
            with self.subTest(seam=seam):
                case = self.context()
                audit, packet = case.new_request()
                target, name = {'reserve': (case.artifacts, 'reserve_request'),
                    'brief': (case.briefs, 'put'), 'enqueue': (case.trigger, 'trigger_identity_sync')}[seam]
                original = getattr(target, name)
                def after_write(*args, **kwargs):
                    original(*args, **kwargs)
                    raise OSError('controlled lost mark')
                with patch.object(target, name, side_effect=after_write):
                    with self.assertRaises(OSError):
                        case.authority.prepare_request(audit, packet, audit['request_id'])
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'prepared')
                self.reload(case)
                result = case.authority.recover_startup()
                self.assertEqual(result['enqueue_repaired'], [audit['request_id']])
                row = case.artifacts.get_request(audit['request_id'])
                self.assertEqual(row['state'], 'queued')
                self.assertEqual(case.artifacts.get_packet(audit['scope']['packet_id']), packet)
                records = case.trigger.queue.for_identity(case.instance)
                self.assertEqual([row['envelope']['dispatch_id'] for row in records], [audit['dispatch_id']])
                private = case.briefs.get_private(audit['brief_id'])
                before = case.files()
                case.authority.resume_request(audit['request_id'])
                self.assertEqual(case.files(), before)
                self.assertEqual(case.briefs.get_private(audit['brief_id']), private)

    def test_claimed_before_queued_mark_is_repaired_without_admitting_same_pass(self):
        case = self.context()
        audit = case.prepare()
        consumer = case.claim(audit)  # No brief read: durable request is still queued.
        box, _ = self.save(case, audit, consumer)
        self.reload(case)
        first = case.authority.recover_startup()
        self.assertEqual(first['enqueue_repaired'], [audit['request_id']])
        self.assertEqual(first['admitted'], [])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'active')
        self.assertIsNone(box.get_ack(audit['dispatch_id']))
        second = case.authority.recover_startup()
        self.assertEqual(len(second['admitted']), 1)

    def test_current_saved_result_redelivery_and_worker_delivery_are_idempotent_in_both_orders(self):
        for startup_first in (False, True):
            with self.subTest(startup_first=startup_first):
                case = self.context()
                audit, consumer = case.claimed()
                box, saved = self.save(case, audit, consumer)
                before_queue = case.trigger.queue.owned(case.instance, audit['dispatch_id'])
                self.reload(case)
                if startup_first:
                    result = case.authority.recover_startup()
                    self.assertEqual(len(result['admitted']), 1)
                    ack = result['admitted'][0]
                    self.assertEqual(case.authority.admit_saved(saved, case.instance), ack)
                else:
                    ack = case.authority.admit_saved(saved, case.instance)
                    self.assertEqual(case.authority.recover_startup()['admitted'], [])
                self.assertEqual(ack['event_id'], audit['dispatch_id'])
                self.assertIsNotNone(box.get_ack(audit['dispatch_id']))
                self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 1)
                self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id']), before_queue)

    def test_failed_transport_never_automatically_admits_saved_result(self):
        case = self.context()
        audit, consumer = case.claimed()
        box, _ = self.save(case, audit, consumer)
        case.trigger.queue.release(case.instance, audit['dispatch_id'], consumer, failed=True)
        self.reload(case)
        before = case.files()
        result = case.authority.recover_startup()
        self.assertEqual(result['admitted'], [])
        self.assertEqual(result['recovery_available'], [audit['request_id']])
        self.assertEqual(case.files(), before)
        self.assertIsNone(box.get_ack(audit['dispatch_id']))

    def test_cancel_after_reserve_never_enqueues_and_lost_cancel_fence_repairs_only_transport(self):
        case = self.context()
        audit, packet = case.new_request()
        case.artifacts.reserve_request(audit, audit['request_id'])
        case.authority.cancel_request(audit['request_id'])
        self.reload(case)
        case.authority.recover_startup()
        self.assertEqual(case.trigger.queue.for_identity(case.instance), [])
        audit = case.prepare(channel='peer')
        with patch.object(case.authority, '_fence', side_effect=OSError('controlled fence write fault')):
            result = case.authority.cancel_request(audit['request_id'])
        self.assertFalse(result['transport_settled'])
        self.reload(case)
        result = case.authority.recover_startup()
        self.assertIn(audit['request_id'], result['cancel_fence_repaired'])
        self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id'])['state'], 'cancelled')
        self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 0)

    def test_operator_recovered_result_admits_once_without_claiming_transport_exit(self):
        case = self.context()
        audit, consumer = case.claimed()
        box, _ = self.save(case, audit, consumer)
        case.trigger.queue.release(case.instance, audit['dispatch_id'], consumer, failed=True)
        before = case.trigger.queue.owned(case.instance, audit['dispatch_id'])
        result = case.authority.resume_request(audit['request_id'], recover_saved=True)
        self.assertIsNotNone(result['admission'])
        self.assertEqual(result['admission']['status'], 'admitted')
        self.assertEqual(result['notice']['code'], 'admitted_from_recovered_result')
        self.assertFalse(result['transport_settled'])
        self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id']), before)
        self.assertIsNotNone(box.get_ack(audit['dispatch_id']))
        files = case.files()
        repeat = case.authority.resume_request(audit['request_id'], recover_saved=True)
        self.assertEqual(repeat['admission'], result['admission'])
        self.assertEqual(case.files(), files)

    def test_operator_recovery_refuses_claim_mismatch_disposition_cancel_and_unproven_owner(self):
        for fault in ('consumer', 'empty_consumer', 'seat', 'cancel_fence', 'disposition', 'cancelled', 'unverified'):
            with self.subTest(fault=fault):
                case = self.context()
                audit, consumer = case.claimed()
                box, _ = self.save(case, audit, consumer)
                case.trigger.queue.release(case.instance, audit['dispatch_id'], consumer, failed=True)
                if fault in ('consumer', 'empty_consumer', 'seat', 'cancel_fence'):
                    path = case.trigger.queue.path
                    value = json.loads(path.read_text(encoding='utf-8'))
                    row = value['records'][0]
                    if fault == 'seat':
                        row['envelope']['target_identity_id'] = 'f' * 32
                    elif fault == 'cancel_fence':
                        row['cancellation_id'] = 'e' * 32
                    else:
                        row['consumer_id'] = 'different-consumer' if fault == 'consumer' else ''
                    path.write_text(json.dumps(value), encoding='utf-8')
                elif fault == 'disposition':
                    diagnostic = case.artifacts.quarantine_submission(audit['request_id'], audit['attempt_id'],
                        audit['dispatch_id'], reason='invalid_response', content=None,
                        actor_identity_id=case.instance['identity_id'])
                    box.quarantine(audit['dispatch_id'], diagnostic['id'], 'invalid_response')
                elif fault == 'cancelled':
                    case.authority.cancel_request(audit['request_id'])
                if fault == 'unverified':
                    gate = patch.object(case.manager, 'artifact_producer', return_value={'available': False})
                else:
                    from contextlib import nullcontext
                    gate = nullcontext()
                before = case.files()
                with gate:
                    try:
                        result = case.authority.resume_request(audit['request_id'], recover_saved=True)
                    except (case.storage.ArtifactConflict, case.storage.ArtifactUnavailable, case.module.ArtifactAccessError):
                        pass
                    else:
                        self.assertIsNone(result['admission'])
                        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'cancelled')
                self.assertEqual(case.files(), before)
                self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 0)

    def test_operator_recovery_uses_real_retained_cli_exit_proof_with_controlled_process_end(self):
        case = self.context()
        audit, consumer = case.claimed()
        self.save(case, audit, consumer)
        case.trigger.queue.release(case.instance, audit['dispatch_id'], consumer, failed=True)
        attempt = case.manager.attempts['team/cli']
        worker = attempt.get('worker_process') or attempt['process']
        worker.poll.return_value = 0  # Explicit fixture observation, no real worker.
        receipt = json.loads(attempt['receipt'].read_text(encoding='utf-8'))
        receipt.update(state='failed', adapter_connected=False, child_exit_code=0)
        attempt['receipt'].write_text(json.dumps(receipt), encoding='utf-8')
        result = case.authority.resume_request(audit['request_id'], recover_saved=True)
        self.assertIsNotNone(result['admission'])
        self.assertTrue(result['transport_settled'])
        self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id'])['state'], 'settled_recovered')

    def test_commit_then_ack_fault_reload_repairs_ack_only_even_when_worker_has_exited(self):
        case = self.context()
        audit, _ = case.claimed()
        from artifact_delivery import atomic_json
        def ack_fault(path, value):
            if path.parent.name == 'artifact_acks':
                raise OSError('controlled ACK fault')
            return atomic_json(path, value)
        with patch('artifact_delivery.atomic_json', side_effect=ack_fault):
            with self.assertRaises(case.storage.ArtifactUnavailable):
                case.authority.submit_cli(audit['brief_id'], '# Durable answer\r\n', case.instance)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'fulfilled')
        box = ArtifactOutbox(case.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
        self.assertIsNone(box.get_ack(audit['dispatch_id']))
        self.reload(case)
        before_queue = case.trigger.queue.owned(case.instance, audit['dispatch_id'])
        index = case.artifacts.path.read_bytes()
        with patch.object(case.manager, 'artifact_producer', side_effect=AssertionError('ACK repair checked liveness')):
            case.authority.recover_startup()
        self.assertIsNotNone(box.get_ack(audit['dispatch_id']))
        self.assertIsNone(box.get_disposition(audit['dispatch_id']))
        self.assertEqual(case.artifacts.path.read_bytes(), index)
        self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id']), before_queue)
        files = case.files()
        case.authority.recover_startup()
        self.assertEqual(case.files(), files)

    def test_fulfilled_ack_repair_refuses_bad_seal_scope_and_records_conflict_without_disposition(self):
        for fault in ('seal', 'scope', 'markdown'):
            with self.subTest(fault=fault):
                case = self.context()
                audit, consumer = case.claimed()
                # Real commit with an intentionally missing local ACK.
                saved = case.sealed_fixture_record(audit, consumer)
                case.artifacts.commit_version(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
                    saved['payload']['markdown'], saved['payload']['observation'])
                payload = saved['payload']
                if fault == 'scope':
                    payload['scope_sha256'] = 'f' * 64
                elif fault == 'markdown':
                    payload['markdown'] = '# Different sealed bytes'
                box = ArtifactOutbox(case.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
                private = case.briefs.get_private(audit['brief_id'])
                box.save(payload, private['_artifact_seal']['seal_secret'])
                if fault == 'seal':
                    path = box.runtime_path / 'artifact_results' / (audit['dispatch_id'] + '.json')
                    value = json.loads(path.read_text(encoding='utf-8'))
                    value['seal'] = 'f' * 64
                    path.write_text(json.dumps(value), encoding='utf-8')
                committed = case.artifacts.get_version(case.artifacts.get_request(audit['request_id'])['version_id'])
                self.reload(case)
                result = case.authority.recover_startup()
                self.assertIsNone(box.get_ack(audit['dispatch_id']))
                self.assertIsNone(box.get_disposition(audit['dispatch_id']))
                self.assertEqual(case.artifacts.get_version(committed['metadata']['id']), committed)
                self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'fulfilled')
                if fault == 'markdown':
                    self.assertTrue(result['quarantined'])
                    self.assertEqual(case.artifacts.diagnostics()['rows'][0]['reason'], 'conflicting_duplicate')
                else:
                    self.assertTrue(result['held'])

    def test_unmatched_and_cancelled_saved_results_are_reported_without_admission_or_rewrite(self):
        for known in (False, True):
            with self.subTest(known=known):
                case = self.context()
                if known:
                    audit, consumer = case.claimed()
                else:
                    audit, _ = case.new_request()
                    case.briefs.put(case.authority._brief(audit), owner=case.authority._owner(audit))
                    consumer = 'unmatched-retained-consumer'
                box, _ = self.save(case, audit, consumer)
                if known:
                    case.authority.cancel_request(audit['request_id'])
                original = (box.runtime_path / 'artifact_results' / (audit['dispatch_id'] + '.json')).read_bytes()
                self.reload(case)
                result = case.authority.recover_startup()
                self.assertEqual(len(result['quarantined']), 1)
                self.assertEqual(result['admitted'], [])
                self.assertIsNone(box.get_ack(audit['dispatch_id']))
                disposition = box.get_disposition(audit['dispatch_id'])
                self.assertEqual(disposition['reason'], 'cancelled' if known else 'unmatched_saved_result')
                self.assertEqual((box.runtime_path / 'artifact_results' / (audit['dispatch_id'] + '.json')).read_bytes(), original)
                row = case.artifacts.get_request(audit['request_id'])
                self.assertEqual(row['state'] if row else None, 'cancelled' if known else None)

    def test_bounded_startup_reports_remaining_prepared_work_without_duplicate_enqueue(self):
        case = self.context()
        first, second = case.prepare(), case.prepare(channel='peer')
        result = case.authority.recover_startup(limit=1)
        self.assertEqual(result['scanned'], 1)
        self.assertEqual(result['remaining'], 1)
        self.assertEqual(len(result['enqueue_repaired']), 1)
        deferred = ({first['request_id'], second['request_id']} - set(result['enqueue_repaired'])).pop()
        self.assertEqual(case.artifacts.get_request(deferred)['reason'], 'resume_pending')
        self.assertEqual(len(case.trigger.queue.for_identity(case.instance)), 2)
        before = case.files()
        for invalid in (0, 101, True, '1'):
            with self.subTest(invalid=invalid), self.assertRaises(case.storage.ArtifactValidationError):
                case.authority.recover_startup(limit=invalid)
        self.assertEqual(case.files(), before)

    def test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent(self):
        """Service/engine sequencing fixture, not an app Stop-route integration claim."""
        case = self.context()
        source_id = uuid.uuid4().hex
        def source_request(state):
            audit, packet = case.new_request()
            request_id = uuid.uuid4().hex
            ids = case.storage.request_ids(request_id)
            audit.update(request_id=request_id, **{key: ids[key] for key in
                         ('lineage_id', 'attempt_id', 'dispatch_id', 'brief_id')})
            revision = hashlib.sha256(b'Source input').hexdigest()
            source = {'session_id': 1, 'run_id': source_id, 'input_revision': revision, 'state_at_request': state}
            packet.update(scope_kind='run_accepted_messages', source_run=source,
                input={'text': 'Source input', 'input_revision': revision, 'source_document': None})
            audit.update(source_run=source, scope=case.artifacts.put_packet(request_id, packet))
            case.authority.prepare_request(audit, packet, request_id)
            return audit
        audit = source_request('active')
        peer = case.prepare(channel='peer')
        with patch.object(case.engine, 'stop_session', side_effect=OSError('controlled Stop storage fault')):
            with self.assertRaises(OSError), case.service._boundary():
                fenced = case.authority.fence_source_requests(source_id)
                case.engine.stop_session(1)
        self.assertEqual(fenced['request_ids'], [audit['request_id']])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'], 'source_stopped')
        self.assertEqual(case.artifacts.get_request(peer['request_id'])['state'], 'queued')
        case.authority.repair_cancel_fences(fenced['request_ids'])
        later = source_request('stopped')
        case.trigger.queue.cancel_run(source_id, uuid.uuid4().hex, fence_artifacts=True)
        self.assertEqual(case.artifacts.get_request(later['request_id'])['state'], 'queued')
        self.assertEqual(case.trigger.queue.owned(case.instance, later['dispatch_id'])['state'], 'queued')


if __name__ == '__main__':
    unittest.main()
