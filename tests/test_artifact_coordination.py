"""Root-owned queue-boundary tests, fixture-controlled managed process evidence."""
from contextlib import contextmanager
from copy import deepcopy
import json
import threading
import unittest
from unittest.mock import patch

from dispatch_queue import QueueConflict
from tests import test_artifact_admission as fixture
from tests import test_artifact_queue as queue_fixture


class ArtifactCoordinationTests(unittest.TestCase):
    def context(self):
        case = fixture.ArtifactAdmissionTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        case.setup_authority()
        return case

    def test_eligibility_is_metadata_only_but_brief_checks_packet_before_work(self):
        case = self.context()
        audit = case.prepare()
        with patch.object(case.artifacts, 'get_packet', side_effect=AssertionError('Body read during claim')):
            self.assertEqual(case.authority.eligible_dispatch_ids(case.instance), {audit['dispatch_id']})
            consumer = case.claim(audit)
        packet_path = case.root / 'artifact_briefs' / 'packets' / (audit['scope']['packet_id'] + '.json')
        packet_path.write_bytes(b'broken packet')
        with self.assertRaises(case.storage.ArtifactUnavailable):
            case.authority.get_brief(audit['brief_id'], case.instance)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'failed')
        self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id'])['consumer_id'], consumer)
        self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 0)

    def test_lookup_failure_skips_new_artifact_without_starving_chat(self):
        case = self.context()
        audit = case.prepare()
        peer_id = 'c' * 32
        case.trigger.queue.enqueue(case.instance, {'dispatch_id': peer_id, 'channel': 'peer', 'prompt': 'peer'})
        with patch.object(case.artifacts, 'channel_names', side_effect=case.storage.ArtifactUnavailable('held')):
            record = case.trigger.queue.claim(case.instance, 'peer-consumer')
        self.assertEqual(record['envelope']['dispatch_id'], peer_id)
        self.assertEqual(case.trigger.queue.owned(case.instance, audit['dispatch_id'])['state'], 'queued')
        case.trigger.queue.release(case.instance, peer_id, 'peer-consumer')
        # A malformed hook result is also a lookup failure, never a raw-ledger error.
        for value in ({'not-an-id'}, ['bad'], None):
            with self.subTest(value=value), patch.object(case.authority, 'eligible_dispatch_ids', return_value=value):
                self.assertIsNone(case.trigger.queue.claim(case.instance, 'closed-consumer'))

    def test_hooks_are_inside_outer_boundary_before_ledger_and_serialize_cancel_prepare(self):
        for operation in ('cancel', 'prepare'):
            with self.subTest(operation=operation):
                case = self.context()
                audit = case.prepare()
                extra, packet = case.new_request(channel='peer')
                raw = case.trigger.queue._queue
                original_transaction = raw._transaction
                local = threading.local()
                observations = []
                @contextmanager
                def transaction():
                    local.depth = getattr(local, 'depth', 0) + 1
                    try:
                        with original_transaction() as value:
                            yield value
                    finally:
                        local.depth -= 1
                rendezvous = threading.Barrier(2)
                release = threading.Event()
                mutation_started, mutation_done = threading.Event(), threading.Event()
                failures, results = [], []
                original_eligible = case.authority.eligible_dispatch_ids
                original_validate = case.authority.validate_enqueue
                def observe():
                    observations.append((case.engine._lock._is_owned(), getattr(local, 'depth', 0)))
                def eligible(instance):
                    observe()
                    rendezvous.wait(5)
                    if not release.wait(5):
                        raise AssertionError('Test did not release claim hook')
                    return original_eligible(instance)
                def validate(instance, envelope):
                    observe()
                    return original_validate(instance, envelope)
                def claim():
                    try:
                        results.append(case.trigger.queue.claim(case.instance, 'barrier-consumer'))
                    except BaseException as error:
                        failures.append(error)
                def mutate():
                    mutation_started.set()
                    try:
                        if operation == 'cancel':
                            case.authority.cancel_request(audit['request_id'])
                        else:
                            case.authority.prepare_request(extra, packet, extra['request_id'])
                    except BaseException as error:
                        failures.append(error)
                    finally:
                        mutation_done.set()
                with patch.object(raw, '_transaction', transaction), patch.object(case.authority,
                        'eligible_dispatch_ids', eligible), patch.object(case.authority, 'validate_enqueue', validate):
                    first = threading.Thread(target=claim)
                    second = threading.Thread(target=mutate)
                    first.start()
                    try:
                        rendezvous.wait(5)
                        second.start()
                        self.assertTrue(mutation_started.wait(5))
                        self.assertFalse(mutation_done.is_set())
                    finally:
                        release.set()
                        first.join(10)
                        if second.ident is not None:
                            second.join(10)
                self.assertFalse(first.is_alive())
                self.assertFalse(second.is_alive())
                self.assertEqual(failures, [])
                self.assertTrue(observations)
                self.assertTrue(all(value == (True, 0) for value in observations), observations)
                self.assertEqual(results[0]['envelope']['dispatch_id'], audit['dispatch_id'])
                state = case.artifacts.get_request(audit['request_id'])['state']
                self.assertEqual(state, 'cancelled' if operation == 'cancel' else 'queued')
                if operation == 'prepare':
                    self.assertEqual(case.artifacts.get_request(extra['request_id'])['state'], 'queued')

    def test_nonartifact_claim_events_and_review_restrictions_keep_exact_golden_bytes(self):
        case = queue_fixture.ArtifactQueueTests()
        self.addCleanup(case.doCleanups)
        case.setUp()
        queue, instance = case.queue, case.instance
        with patch('dispatch_queue.time.time', return_value=123.5):
            queue.enqueue(instance, {'dispatch_id': 'first', 'channel': 'general', 'prompt': 'one'})
            queue.enqueue(instance, {'dispatch_id': 'second', 'channel': 'general', 'review_brief_id': 'brief'})
        original = queue.path.read_bytes()
        for with_artifact in (False, True):
            for allowed in (None, {'second'}):
                with self.subTest(artifact=with_artifact, allowed=allowed):
                    queue.path.write_bytes(original)
                    if with_artifact:
                        value = json.loads(original)
                        opaque = deepcopy(value['records'][0])
                        opaque['envelope'].update(case.envelope)
                        value['records'].insert(0, opaque)
                        queue.path.write_text(json.dumps(value), encoding='utf-8')
                    expected_id = 'first' if allowed is None else 'second'
                    expected = deepcopy(next(row for row in json.loads(original)['records']
                                             if row['envelope']['dispatch_id'] == expected_id))
                    expected.update(state='dispatched', consumer_id='golden-consumer')
                    expected['events'].append({'state': 'dispatched', 'at': 123.5, 'error': ''})
                    with patch('dispatch_queue.time.time', return_value=123.5):
                        actual = queue.claim(instance, 'golden-consumer', allowed_dispatch_ids=allowed)
                    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
                    self.assertEqual(canonical(actual), canonical(expected))
                    self.assertEqual(actual['events'][-1], {'state': 'dispatched', 'at': 123.5, 'error': ''})

    def test_real_review_occupancy_queues_artifact_until_review_stops_without_namespace_adoption(self):
        case = self.context()
        case.sessions.save_custom_template({'id': 'artifact-occupancy', 'name': 'Review', 'roles': ['reviewer'],
            'phases': [{'name': 'Review', 'participants': ['reviewer'], 'prompt': 'Review source.', 'is_output': True}]})
        run = case.engine.start_session('artifact-occupancy', 'review',
            {'reviewer': case.instance['name']}, 'operator', input_text='Frozen review source.')
        audit = case.prepare(channel='peer')
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'], 'queued_behind_review')
        consumer = 'review-occupancy-consumer'
        record = case.trigger.queue.claim(case.instance, consumer)
        self.assertEqual(record['envelope']['dispatch_id'], run['active_invocation']['dispatch_id'])
        case.trigger.queue.release(case.instance, record['envelope']['dispatch_id'], consumer)
        self.assertIsNone(case.trigger.queue.claim(case.instance, consumer))
        case.engine.stop_session(run['id'])
        claimed = case.trigger.queue.claim(case.instance, 'artifact-after-review')
        self.assertEqual(claimed['envelope']['dispatch_id'], audit['dispatch_id'])
        self.assertNotIn('run_id', claimed['envelope'])
        self.assertNotIn('review_brief_id', claimed['envelope'])
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'queued')


if __name__ == '__main__':
    unittest.main()
