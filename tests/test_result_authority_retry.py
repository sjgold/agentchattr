"""Sealed API authority survives delivery faults; process doubles, no model calls."""
from copy import deepcopy
import json
import time
import unittest
from unittest.mock import patch
import uuid

from tests import test_result_owner_wiring as fixture
from turn_events import EventConflict


class ResultAuthorityRetryTests(unittest.TestCase):
    def setUp(self):
        fixture.ResultOwnerWiringTests.setUp(self)
        self.owner, self.launch = self.fixture.ready('api')
        started = fixture.ResultOwnerWiringTests.start(self, self.owner['name'])
        self.session_id = started['id']
        self.queue = self.trigger.queue
        self.old = deepcopy(started['active_invocation'])
        self.queue.claim(self.owner, 'original-consumer')
        self.queue.acknowledge(self.owner, self.old['dispatch_id'], 'original-consumer')
        self.queue.release(self.owner, self.old['dispatch_id'], 'original-consumer', failed=True, error='local_delivery_failure')
        self.engine.monitor_turns(now=time.time())
        self.assertEqual(self.current()['state'], 'stalled')
        self.checkpoint = self.current()['turn_recovery']['checkpoint_id']
        self.request = uuid.uuid4().hex
        self.persisted = []

    def current(self):
        return self.sessions.get(self.session_id)

    def retry(self):
        return self.engine.retry_turn(self.session_id, self.checkpoint, self.old['attempt_id'], self.request)

    def persist_brief(self, envelope, **kwargs):
        result = self.original_put(envelope, **kwargs)
        path = self.sessions.briefs.path / (result + '.json')
        self.persisted.append({'envelope': deepcopy(envelope), 'path': path, 'bytes': path.read_bytes()})
        return result

    def delivery_gap(self, operation):
        self.original_put = self.sessions.briefs.put
        with patch.object(self.sessions.briefs, 'put', side_effect=self.persist_brief), \
                patch.object(self.sessions if operation == 'bind' else self.queue,
                             'bind_invocation' if operation == 'bind' else 'enqueue',
                             side_effect=OSError('fixture post-authority delivery failure')):
            try:
                self.retry()
            except OSError:
                pass  # API error reporting is separate from persisted recovery semantics.
        self.assertEqual(len(self.persisted), 1)
        raw = json.loads(self.persisted[0]['bytes'])
        self.assertIn('_result_seal', raw)
        return self.persisted[0]

    def assert_stalled_reserved(self, sealed):
        current = self.current()
        self.assertEqual(current['state'], 'stalled')
        self.assertEqual(current['turn_recovery']['reason'], 'local_delivery_failure')
        invocation = current['active_invocation']
        for field in ('attempt_id', 'brief_id', 'turn_id'):
            self.assertEqual(invocation[field], sealed['envelope'][field])
        self.assertEqual(invocation['dispatch_id'], json.loads(sealed['bytes'])['_result_seal']['owner']['dispatch_id'])
        self.assertEqual(sealed['path'].read_bytes(), sealed['bytes'])
        self.assertFalse(current.get('pending_retry'), 'sealed authority is no longer replaceable preparation')
        self.assertEqual(current['input_snapshot']['text'], 'Exact café\r\nsource')
        secret = json.loads(sealed['bytes'])['_result_seal']['seal_secret']
        self.assertNotIn(secret, json.dumps(current))
        self.assertNotIn(secret, json.dumps(self.records()))
        self.assertNotIn(secret, json.dumps(self.sessions.briefs.get(sealed['envelope']['brief_id'], operator=True)))
        return current

    def records(self):
        return json.loads((self.fixture.root / 'queue/ledger.json').read_text('utf-8'))['records']

    def assert_no_process_control(self):
        self.assertEqual(self.fixture.spawn.call_count, 1)
        for process in self.fixture.processes:
            process.wait.assert_not_called()
            process.terminate.assert_not_called()
            process.kill.assert_not_called()

    def test_sealed_put_then_bind_failure_becomes_current_turn_delivery_failure(self):
        self.assert_stalled_reserved(self.delivery_gap('bind'))

    def test_sealed_bound_then_enqueue_failure_becomes_current_turn_delivery_failure(self):
        self.assert_stalled_reserved(self.delivery_gap('enqueue'))

    def test_postsealed_repair_rejects_before_context_or_process_control(self):
        sealed = self.delivery_gap('enqueue')
        self.assert_stalled_reserved(sealed)
        before, records = deepcopy(self.current()), deepcopy(self.records())
        with patch.object(self.fixture.manager, 'prepare_retry_context', side_effect=AssertionError('postsealed preparation must not run')) as prepare:
            with self.assertRaises(EventConflict):
                self.engine.repair_retry(self.session_id, self.request, self.launch['attempt'],
                    confirmation={'confirm': True, 'launch_attempt': self.launch['attempt']})
            prepare.assert_not_called()
        self.assertEqual(self.current(), before)
        self.assertEqual(self.records(), records)
        self.assertEqual(sealed['path'].read_bytes(), sealed['bytes'])
        self.assert_no_process_control()

    def test_explicit_retry_mints_new_ids_preserving_old_seal_and_exact_source(self):
        sealed = self.delivery_gap('bind')
        current = self.assert_stalled_reserved(sealed)
        old_invocation = deepcopy(current['active_invocation'])
        newer = self.engine.retry_turn(self.session_id, current['turn_recovery']['checkpoint_id'],
            old_invocation['attempt_id'], uuid.uuid4().hex)
        invocation = newer['active_invocation']
        for field in ('attempt_id', 'brief_id', 'dispatch_id'):
            self.assertNotEqual(invocation[field], old_invocation[field])
        self.assertEqual(invocation['turn_id'], old_invocation['turn_id'])
        for field in ('run_id', 'input_revision', 'input_snapshot', 'design_revision', 'rules_snapshot'):
            self.assertEqual(newer[field], current[field])
        self.assertEqual(sealed['path'].read_bytes(), sealed['bytes'])
        delivery = self.sessions.briefs.get_delivery(invocation['brief_id'], self.owner)
        self.assertNotEqual(delivery['seal_secret'], json.loads(sealed['bytes'])['_result_seal']['seal_secret'])
        self.assertEqual(delivery['source'], 'Exact café\r\nsource')
        self.assertTrue(any(value['attempt_id'] == old_invocation['attempt_id'] for value in newer['superseded_attempts']))
        active = [record for record in self.records() if record['state'] == 'queued']
        self.assertEqual([record['envelope']['dispatch_id'] for record in active], [invocation['dispatch_id']])
        self.assertFalse(any(record['envelope']['dispatch_id'] == old_invocation['dispatch_id'] for record in self.records()))
        self.assertNotIn(delivery['seal_secret'], json.dumps(newer))
        self.assertNotIn(delivery['seal_secret'], json.dumps(self.records()))
        self.assert_no_process_control()

    def test_committed_enqueue_lost_reply_replay_finalizes_same_turn_once(self):
        self.original_put = self.sessions.briefs.put
        enqueue = self.queue.enqueue
        committed = []
        def lost_reply(*args, **kwargs):
            record = enqueue(*args, **kwargs)
            committed.append(deepcopy(record))
            raise OSError('fixture reply lost after durable queue commit')
        with patch.object(self.sessions.briefs, 'put', side_effect=self.persist_brief), patch.object(self.queue, 'enqueue', side_effect=lost_reply):
            try:
                self.retry()
            except OSError:
                pass
        self.assertEqual(len(committed), 1)
        self.assertEqual(len(self.persisted), 1)
        invocation = deepcopy(self.current()['active_invocation'])
        record = next(value for value in self.records() if value['envelope']['dispatch_id'] == invocation['dispatch_id'])
        self.assertEqual(record, committed[0])
        before_queue = (self.fixture.root / 'queue/ledger.json').read_bytes()
        with patch.object(self.fixture.manager, 'prepare_retry_context', side_effect=AssertionError('committed replay must not prepare context')) as prepare:
            for _ in range(3):
                self.retry()
            prepare.assert_not_called()
        current = self.current()
        self.assertEqual(current['active_invocation'], invocation, 'committed timing/identity must not reset')
        self.assertFalse(current.get('pending_retry'))
        self.assertIn(current['state'], ('waiting', 'active'))
        self.assertEqual((self.fixture.root / 'queue/ledger.json').read_bytes(), before_queue)
        self.assertEqual(self.persisted[0]['path'].read_bytes(), self.persisted[0]['bytes'])
        self.assert_no_process_control()

    def test_stop_wins_across_sealed_bind_gap_without_delivery_or_new_authority(self):
        sealed = self.delivery_gap('bind')
        current = self.assert_stalled_reserved(sealed)
        stop = self.engine.stop_session(self.session_id)
        stop_id = stop['stop_id']
        records = deepcopy(self.records())
        with patch.object(self.fixture.manager, 'prepare_retry_context', side_effect=AssertionError('Stop forbids preparation')):
            for action in (self.retry, lambda: self.engine.repair_retry(self.session_id, self.request, self.launch['attempt'])):
                with self.assertRaises(EventConflict):
                    action()
            with self.assertRaises(EventConflict):
                self.engine.admit_event(current['active_invocation']['brief_id'], 'final', 'Late stopped output', self.owner)
            self.engine.monitor_turns()
            self.engine.reconcile_stops()
        latest = self.current()
        self.assertEqual(latest['stop_id'], stop_id)
        self.assertFalse(latest['dispatch_eligible'])
        self.assertEqual(latest['admitted_events'], [])
        self.assertTrue(any(event['content'] == 'Late stopped output' for event in latest['quarantined_events']))
        self.assertEqual(self.records(), records)
        self.assertEqual(sealed['path'].read_bytes(), sealed['bytes'])
        self.assert_no_process_control()

    def test_missing_or_malformed_private_authority_never_enables_preparation_repair(self):
        sealed = self.delivery_gap('enqueue')
        self.assert_stalled_reserved(sealed)
        malformed = json.loads(sealed['bytes'])
        malformed['_result_seal']['seal_secret'] = 'not-a-key'
        for content in (None, json.dumps(malformed).encode()):
            if content is None:
                sealed['path'].unlink()
            else:
                sealed['path'].write_bytes(content)
            before, records = deepcopy(self.current()), deepcopy(self.records())
            with patch.object(self.fixture.manager, 'prepare_retry_context', side_effect=AssertionError('invalid authority forbids process preparation')) as prepare:
                with self.assertRaises(ValueError):
                    self.engine.repair_retry(self.session_id, self.request, self.launch['attempt'],
                        confirmation={'confirm': True, 'launch_attempt': self.launch['attempt']})
                prepare.assert_not_called()
            self.assertEqual(self.current(), before)
            self.assertEqual(self.records(), records)
            if content is None:
                self.assertFalse(sealed['path'].exists())
            else:
                self.assertEqual(sealed['path'].read_bytes(), content)
        self.assert_no_process_control()


if __name__ == '__main__':
    unittest.main()
