"""Durable individual dispatches and explicit stable-seat transport ownership."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def envelope(**changes):
    return {'dispatch_id': uuid.uuid4().hex, 'channel': 'review',
            'prompt': 'Exact café 日本語\r\nprompt @all', 'job_id': 17,
            'review_brief_id': uuid.uuid4().hex, 'run_id': uuid.uuid4().hex,
            'turn_id': 'run:0:1', 'attempt_id': uuid.uuid4().hex,
            'input_revision': 'a' * 64, **changes}


class DispatchQueueTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('dispatch_queue')
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.instance = {'name': 'seat', 'identity_id': uuid.uuid4().hex}
        self.peer = {'name': 'peer', 'identity_id': uuid.uuid4().hex}
        self.store = self.module.QueueStore(self.root)
        self.ledger = self.root / 'queue/ledger.json'

    def test_distinct_envelopes_are_fifo_and_fields_never_mix(self):
        first = envelope(channel='alpha', prompt='First exact prompt', job_id=11)
        second = envelope(channel='beta', prompt='Second exact prompt', job_id=22)
        for supplied in (first, second):
            saved = self.store.enqueue(self.instance, supplied)
            for key, value in supplied.items():
                self.assertEqual(saved['envelope'][key], value)
            self.assertEqual(saved['state'], 'queued')
            self.assertEqual(saved['envelope']['target_identity_id'], self.instance['identity_id'])
        claimed = self.store.claim(self.instance, 'worker-one')
        self.assertEqual(claimed['envelope']['dispatch_id'], first['dispatch_id'])
        self.store.acknowledge(self.instance, first['dispatch_id'], 'worker-one')
        self.store.release(self.instance, first['dispatch_id'], 'worker-one')
        claimed = self.store.claim(self.instance, 'worker-one')
        for key, value in second.items():
            self.assertEqual(claimed['envelope'][key], value)

    def test_idempotent_id_and_conflicting_reuse_preserve_original(self):
        supplied = envelope()
        first = self.store.enqueue(self.instance, supplied)
        second = self.store.enqueue(self.instance, deepcopy(supplied))
        self.assertEqual(first['envelope'], second['envelope'])
        for changed, instance in (({**supplied, 'prompt': 'Conflicting content'}, self.instance),
                                  (supplied, self.peer)):
            with self.subTest(instance=instance['name']), self.assertRaises(self.module.QueueConflict):
                self.store.enqueue(instance, changed)
        self.assertEqual(self.store.claim(self.instance, 'worker')['envelope'], first['envelope'])

    def test_identical_text_with_distinct_ids_is_two_dispatches(self):
        first = envelope()
        second = {**first, 'dispatch_id': uuid.uuid4().hex}
        self.store.enqueue(self.instance, first)
        self.store.enqueue(self.instance, second)
        self.store.claim(self.instance, 'worker')
        self.store.release(self.instance, first['dispatch_id'], 'worker')
        self.assertEqual(self.store.claim(self.instance, 'worker')['envelope']['dispatch_id'], second['dispatch_id'])

    def test_generated_id_and_returned_records_are_independent_copies(self):
        supplied = envelope()
        supplied.pop('dispatch_id')
        saved = self.store.enqueue(self.instance, supplied)
        self.assertRegex(saved['envelope']['dispatch_id'], r'^[0-9a-f]{32}$')
        original_prompt = supplied['prompt']
        supplied['prompt'] = 'Mutated input'
        saved['envelope']['prompt'] = 'Mutated return'
        saved['events'].clear()
        claimed = self.store.claim(self.instance, 'worker')
        self.assertEqual(claimed['envelope']['prompt'], original_prompt)
        claimed['envelope']['channel'] = 'Mutated claim'
        self.assertEqual(self.store.claim(self.instance, 'worker')['envelope']['channel'], 'review')

    def test_claim_response_loss_recovers_same_owner_after_store_reopen(self):
        supplied = envelope()
        self.store.enqueue(self.instance, supplied)
        self.store.enqueue(self.instance, envelope())
        first = self.store.claim(self.instance, 'worker-one')
        self.assertEqual(first['state'], 'dispatched')
        reopened = self.module.QueueStore(self.root)
        recovered = reopened.claim(self.instance, 'worker-one')
        self.assertEqual(recovered['envelope']['dispatch_id'], supplied['dispatch_id'])
        self.assertEqual(recovered['consumer_id'], 'worker-one')
        with self.assertRaises(self.module.QueueBusy):
            reopened.claim(self.instance, 'replacement-worker')

    def test_acknowledgement_does_not_release_for_next_dispatch(self):
        supplied = envelope()
        self.store.enqueue(self.instance, supplied)
        self.store.enqueue(self.instance, envelope())
        self.store.claim(self.instance, 'worker')
        ack = self.store.acknowledge(self.instance, supplied['dispatch_id'], 'worker')
        self.assertEqual(ack['state'], 'acknowledged')
        self.assertEqual(self.store.claim(self.instance, 'worker')['envelope']['dispatch_id'], supplied['dispatch_id'])
        self.module.QueueStore(self.root).status()
        with self.assertRaises(self.module.QueueBusy):
            self.store.claim(self.instance, 'other-worker')
        self.assertEqual(self.store.release(self.instance, supplied['dispatch_id'], 'worker')['state'], 'released')
        self.assertNotEqual(self.store.claim(self.instance, 'other-worker')['envelope']['dispatch_id'], supplied['dispatch_id'])

    def test_wrong_seat_or_consumer_cannot_acknowledge_or_release(self):
        supplied = envelope()
        self.store.enqueue(self.instance, supplied)
        self.store.claim(self.instance, 'worker')
        for operation in ('acknowledge', 'release'):
            for identity, consumer in ((self.peer, 'worker'), (self.instance, 'wrong-worker')):
                with self.subTest(operation=operation, consumer=consumer), self.assertRaises(self.module.QueueAccessError):
                    getattr(self.store, operation)(identity, supplied['dispatch_id'], consumer)
        self.assertEqual(self.store.claim(self.instance, 'worker')['state'], 'dispatched')

    def test_rename_keeps_identity_ownership_and_replacement_gets_no_old_work(self):
        supplied = envelope()
        self.store.enqueue(self.instance, supplied)
        renamed = {**self.instance, 'name': 'renamed-seat'}
        claimed = self.store.claim(renamed, 'worker')
        self.assertEqual(claimed['envelope']['dispatch_id'], supplied['dispatch_id'])
        replacement = {'name': self.instance['name'], 'identity_id': uuid.uuid4().hex}
        try:
            other = self.store.claim(replacement, 'new-worker')
        except self.module.QueueAccessError:
            other = None
        self.assertIsNone(other)
        self.store.acknowledge(renamed, supplied['dispatch_id'], 'worker')
        self.assertEqual(self.store.release(renamed, supplied['dispatch_id'], 'worker')['state'], 'released')

    def test_failure_retains_envelope_and_events_then_allows_next_explicit_claim(self):
        supplied = envelope()
        self.store.enqueue(self.instance, supplied)
        following = self.store.enqueue(self.instance, envelope())
        claimed = self.store.claim(self.instance, 'worker')
        failed = self.store.release(self.instance, supplied['dispatch_id'], 'worker',
                                    failed=True, error='Local fixture transport failed')
        self.assertEqual(failed['state'], 'failed')
        self.assertEqual(failed['envelope'], claimed['envelope'])
        self.assertGreater(len(failed['events']), len(claimed['events']))
        self.assertIn('Local fixture transport failed', json.dumps(failed))
        self.assertEqual(self.store.claim(self.instance, 'worker')['envelope'], following['envelope'])

    def test_separate_seats_progress_while_one_seat_is_owned(self):
        self.store.enqueue(self.instance, envelope())
        peer_record = self.store.enqueue(self.peer, envelope())
        self.store.claim(self.instance, 'worker')
        self.assertEqual(self.store.claim(self.peer, 'peer-worker')['envelope'], peer_record['envelope'])

    def test_failed_atomic_enqueue_claim_or_ack_preserves_previous_ledger(self):
        supplied = envelope()
        self.store.enqueue(self.instance, supplied)
        for operation in ('enqueue', 'claim', 'acknowledge'):
            if operation == 'acknowledge':
                self.store.claim(self.instance, 'worker')
            original = self.ledger.read_bytes()
            with self.subTest(operation=operation), patch('os.replace', side_effect=OSError('fixture write failure')):
                with self.assertRaises(OSError):
                    if operation == 'enqueue':
                        self.store.enqueue(self.instance, envelope())
                    elif operation == 'claim':
                        self.store.claim(self.instance, 'worker')
                    else:
                        self.store.acknowledge(self.instance, supplied['dispatch_id'], 'worker')
            self.assertEqual(self.ledger.read_bytes(), original)
        recovered = self.module.QueueStore(self.root).claim(self.instance, 'worker')
        self.assertEqual(recovered['state'], 'dispatched')
        self.assertEqual(recovered['envelope']['dispatch_id'], supplied['dispatch_id'])
        self.store.release(self.instance, supplied['dispatch_id'], 'worker')
        self.assertIsNone(self.store.claim(self.instance, 'worker'),
                          'a failed enqueue must not leak into a later transaction')

    def test_malformed_ledger_fails_closed_without_replacing_bytes(self):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        original = b'{"truncated":'
        self.ledger.write_bytes(original)
        with self.assertRaises(ValueError):
            self.module.QueueStore(self.root).enqueue(self.instance, envelope())
        self.assertEqual(self.ledger.read_bytes(), original)

    def test_legacy_files_are_preserved_and_reported_without_replay(self):
        legacy = self.root / 'seat_queue.jsonl'
        original = b'{"prompt":"old uncertain work"}\r\nnot-json\r\n'
        legacy.write_bytes(original)
        self.assertIsNone(self.store.claim(self.instance, 'worker'))
        supplied = envelope(prompt='PRIVATE PROMPT MUST NOT APPEAR IN STATUS')
        self.store.enqueue(self.instance, supplied)
        self.store.claim(self.instance, 'worker')
        summary = json.dumps(self.module.QueueStore(self.root).status())
        self.assertIn(legacy.name, summary)
        self.assertNotIn(supplied['prompt'], summary)
        self.assertEqual(legacy.read_bytes(), original)

    def test_concurrent_threads_enqueue_without_losing_distinct_dispatches(self):
        entries = [envelope(job_id=i) for i in range(12)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            saved = list(pool.map(lambda item: self.module.QueueStore(self.root).enqueue(self.instance, item), entries))
        expected = {record['envelope']['dispatch_id'] for record in saved}
        actual = set()
        while (record := self.store.claim(self.instance, 'worker')) is not None:
            dispatch_id = record['envelope']['dispatch_id']
            self.assertNotIn(dispatch_id, actual)
            actual.add(dispatch_id)
            self.store.release(self.instance, dispatch_id, 'worker')
        self.assertEqual(actual, expected)

    def test_competing_processes_cannot_both_claim_one_seat(self):
        self.store.enqueue(self.instance, envelope())
        self.store.enqueue(self.instance, envelope())
        gate = self.root / 'start-workers'
        code = '''import json,sys,time
from pathlib import Path
from dispatch_queue import QueueStore,QueueBusy
root,instance,consumer,out=sys.argv[1:]
deadline=time.monotonic()+10
while not (Path(root)/'start-workers').exists():
    if time.monotonic()>deadline: raise TimeoutError('fixture gate')
    time.sleep(.01)
try:
    record=QueueStore(root).claim(json.loads(instance),consumer)
    result={'owner':record['consumer_id'],'dispatch_id':record['envelope']['dispatch_id']}
except QueueBusy:
    result={'busy':True}
Path(out).write_text(json.dumps(result),encoding='utf-8')
'''
        children = []
        try:
            for i in range(2):
                children.append(subprocess.Popen([sys.executable, '-c', code, str(self.root),
                    json.dumps(self.instance), f'worker-{i}', str(self.root / f'result-{i}.json')],
                    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            gate.touch()
            for child in children:
                stdout, stderr = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0, stderr.decode('utf-8', errors='replace'))
            results = [json.loads((self.root / f'result-{i}.json').read_text('utf-8')) for i in range(2)]
            self.assertEqual(sum('owner' in result for result in results), 1)
            self.assertEqual(sum(result.get('busy', False) for result in results), 1)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
