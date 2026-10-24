"""Real store/ledger ordering contracts, without workers or native readiness claims."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import unittest

import queue_coordinator
from dispatch_queue import QueueBusy, QueueStore
from session_store import SessionStore
from tests import test_turn_recovery as fixture


class RecipientRuntimeOrderTests(unittest.TestCase):
    def setUp(self):
        fixture.TurnRecoveryTests.setUp(self)

    def test_released_unconsumed_review_blocks_manual_same_identity(self):
        old = self.queue.claim(self.owner, 'worker')
        self.queue.release(self.owner, old['envelope']['dispatch_id'], 'worker')
        manual = self.queue.enqueue(self.owner, {'text': 'manual', 'channel': 'general'})
        before = self.queue.path.read_bytes()
        self.assertIsNone(self.queue.claim(self.owner, 'worker'))
        self.assertEqual(self.queue.path.read_bytes(), before)
        self.assertEqual(self.queue.owned(self.owner, manual['envelope']['dispatch_id'])['state'], 'queued')

    def test_allowed_review_dispatch_ids_names_current_immutable_identity(self):
        self.assertEqual(queue_coordinator.allowed_review_dispatch_ids(
            self.sessions.list_all(), self.owner['identity_id']), {self.original['dispatch_id']})
        self.assertIsNone(queue_coordinator.allowed_review_dispatch_ids(
            self.sessions.list_all(), self.peer['identity_id']))

    def candidate(self, dispatch='review-a', session_id=1, created=1):
        run = deepcopy(self.sessions.get(self.session_id))
        run['id'] = session_id
        run['active_invocation']['monitoring'] = {'created_at': created}
        run['active_invocation'].update(dispatch_id=dispatch, human=False, consumed=False)
        return run

    def test_shared_nonterminal_predicate_and_no_occupancy_boundaries(self):
        run = self.candidate()
        for state in ('active', 'waiting', 'paused', 'awaiting_input', 'stalled', 'retrying', 'interrupted', 'prepared'):
            with self.subTest(state=state):
                run.update(state=state, dispatch_eligible=False)
                self.assertTrue(queue_coordinator.is_nonterminal_review(run))
                self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([run], self.owner['identity_id']), {'review-a'})
        for changes in ({'state': 'complete'}, {'state': 'stopped'}, {'completion_protocol': 0},
                        {'stop_id': 'stop'}, {'replaced_by_run_id': 'replacement'}):
            candidate = {**self.candidate(), **changes}
            with self.subTest(changes=changes):
                self.assertFalse(queue_coordinator.is_nonterminal_review(candidate))
                self.assertIsNone(queue_coordinator.allowed_review_dispatch_ids([candidate], self.owner['identity_id']))
        for changes in ({'human': True}, {'consumed': True}, {'expected_identity_id': self.peer['identity_id']}):
            candidate = self.candidate()
            candidate['active_invocation'].update(changes)
            self.assertIsNone(queue_coordinator.allowed_review_dispatch_ids([candidate], self.owner['identity_id']))
        run = self.candidate()
        del run['active_invocation']
        self.assertTrue(queue_coordinator.is_nonterminal_review(run))
        self.assertIsNone(queue_coordinator.allowed_review_dispatch_ids([run], self.owner['identity_id']))

    def test_valid_order_is_created_time_then_session_id_without_mutation(self):
        runs = [self.candidate('later', 1, 3), self.candidate('same-time-b', 3, 2), self.candidate('first', 2, 2)]
        original = deepcopy(runs)
        allowed = queue_coordinator.allowed_review_dispatch_ids(runs, self.owner['identity_id'])
        self.assertEqual(allowed, {'first'})
        allowed.add('mutated')
        self.assertEqual(queue_coordinator.allowed_review_dispatch_ids(list(reversed(runs)), self.owner['identity_id']), {'first'})
        self.assertEqual(runs, original)

    def test_malformed_timing_and_flags_prioritize_own_task_over_valid(self):
        good = self.candidate('good', 1, 0)
        for value in (None, True, -1, float('nan'), float('inf'), '1'):
            bad = self.candidate('malformed', 9, value)
            with self.subTest(timing=repr(value)):
                self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([good, bad], self.owner['identity_id']), {'malformed'})
        for monitoring in (None, {}, 'bad'):
            bad = self.candidate('malformed', 9)
            bad['active_invocation']['monitoring'] = monitoring
            self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([good, bad], self.owner['identity_id']), {'malformed'})
        for flag in ('human', 'consumed'):
            for value in (None, 0, 'false'):
                bad = self.candidate('malformed', 9)
                bad['active_invocation'][flag] = value
                self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([good, bad], self.owner['identity_id']), {'malformed'})
            bad = self.candidate('malformed', 9)
            del bad['active_invocation'][flag]
            self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([good, bad], self.owner['identity_id']), {'malformed'})

    def test_malformed_candidate_ties_and_invalid_dispatch_fail_closed(self):
        identity = self.owner['identity_id']
        good = self.candidate('good', 1, 0)
        for invalid_id in (None, True, 0, -1, '2'):
            bad = self.candidate('z-task', invalid_id)
            lower = self.candidate('a-task', 8, None)
            self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([good, bad, lower], identity), {'a-task'})
        for dispatch in (None, True, '', 'invalid space', 'x' * 129):
            bad = self.candidate(dispatch, 2)
            self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([good, bad], identity), set())
        first = self.candidate('b', 4, None)
        second = self.candidate('a', 4, None)
        self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([first, second], identity), {'a'})
        invalid = self.candidate(None, 4)
        self.assertEqual(queue_coordinator.allowed_review_dispatch_ids([second, invalid], identity), set())

    def test_raw_claim_skips_manual_and_validates_allowset_before_writes(self):
        raw = QueueStore(self.root / 'raw')
        manual = raw.enqueue(self.owner, {'dispatch_id': 'manual', 'text': 'manual'})
        raw.enqueue(self.owner, {'dispatch_id': 'review', 'text': 'review'})
        before = raw.path.read_bytes()
        for invalid in ([], {}, 'review', {'bad space'}, {1}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                raw.claim(self.owner, 'worker', allowed_dispatch_ids=invalid)
            self.assertEqual(raw.path.read_bytes(), before)
        self.assertIsNone(raw.claim(self.owner, 'worker', allowed_dispatch_ids=set()))
        self.assertEqual(raw.path.read_bytes(), before)
        claimed = raw.claim(self.owner, 'worker', allowed_dispatch_ids={'review'})
        self.assertEqual(claimed['envelope']['dispatch_id'], 'review')
        self.assertEqual(raw.owned(self.owner, manual['envelope']['dispatch_id']), manual)

    def test_raw_unpublished_or_blocked_allowed_dispatch_never_falls_through(self):
        raw = QueueStore(self.root / 'gap')
        raw.enqueue(self.owner, {'dispatch_id': 'manual'})
        raw.enqueue(self.owner, {'dispatch_id': 'review', 'run_id': 'cold'})
        before = raw.path.read_bytes()
        self.assertIsNone(raw.claim(self.owner, 'worker', allowed_dispatch_ids={'unpublished'}))
        self.assertIsNone(raw.claim(self.owner, 'worker', allowed_dispatch_ids={'review'}, blocked_run_ids={'cold'}))
        self.assertEqual(raw.path.read_bytes(), before)
        self.assertEqual(raw.claim(self.owner, 'worker', allowed_dispatch_ids=None)['envelope']['dispatch_id'], 'manual')

    def test_exact_active_and_cancelling_owner_poll_precedes_empty_whitelist(self):
        raw = QueueStore(self.root / 'poll')
        dispatch = 'a' * 32
        raw.enqueue(self.owner, {'dispatch_id': dispatch, 'run_id': 'cold'})
        active = raw.claim(self.owner, 'worker')
        before = raw.path.read_bytes()
        self.assertEqual(raw.claim(self.owner, 'worker', allowed_dispatch_ids=set()), active)
        with self.assertRaises(QueueBusy):
            raw.claim(self.owner, 'other', allowed_dispatch_ids=set())
        self.assertEqual(raw.path.read_bytes(), before)
        raw.cancel_dispatch(dispatch, 'cancel')
        cancelling = raw.owned(self.owner, dispatch)
        self.assertEqual(raw.claim(self.owner, 'worker', blocked_run_ids={'cold'}, allowed_dispatch_ids=set()), cancelling)
        raw.cancellation_receipt(self.owner, dispatch, 'worker', 'local_ended')
        raw.enqueue(self.owner, {'dispatch_id': 'next'})
        raw.hold_recovered(dispatch, self.owner['identity_id'], dispatch, selected_cli=True)
        with self.assertRaises(QueueBusy):
            raw.claim(self.owner, 'worker', allowed_dispatch_ids={'next'})

    def test_two_real_reviews_early_release_final_then_review_before_manual(self):
        second = self.engine.start_session('review', 'second', {'reviewer': 'codex', 'editor': 'claude'}, 'operator')
        first = self.queue.claim(self.owner, 'worker')
        self.queue.release(self.owner, first['envelope']['dispatch_id'], 'worker')
        manual = self.queue.enqueue(self.owner, {'text': 'manual'})
        before = self.queue.path.read_bytes()
        self.assertIsNone(self.queue.claim(self.owner, 'worker'))
        self.assertEqual(self.queue.path.read_bytes(), before)
        self.engine.admit_event(self.original['brief_id'], 'final', 'First accepted result', self.owner)
        self.assertEqual(self.queue.claim(self.owner, 'worker')['envelope']['dispatch_id'], second['active_invocation']['dispatch_id'])
        self.queue.release(self.owner, second['active_invocation']['dispatch_id'], 'worker')
        self.assertIsNone(self.queue.claim(self.owner, 'worker'))
        self.engine.admit_event(second['active_invocation']['brief_id'], 'question', 'Please clarify?', self.owner)
        self.assertEqual(self.queue.claim(self.owner, 'worker')['envelope']['dispatch_id'], manual['envelope']['dispatch_id'])

    def test_real_stalled_and_cold_review_holds_manual_but_peer_remains_usable(self):
        active = self.queue.claim(self.owner, 'worker')
        self.queue.release(self.owner, active['envelope']['dispatch_id'], 'worker', failed=True, error='provider_failure')
        self.engine.monitor_turns()
        self.queue.enqueue(self.owner, {'dispatch_id': 'manual'})
        peer = self.queue.enqueue(self.peer, {'dispatch_id': 'peer-manual'})
        for state in ('stalled', 'paused', 'interrupted'):
            def update(run):
                run['state'] = state
                run['dispatch_eligible'] = False
            self.sessions._event_update(self.session_id, update)
            before = self.queue.path.read_bytes()
            self.assertIsNone(self.queue.claim(self.owner, 'worker'))
            self.assertEqual(self.queue.path.read_bytes(), before)
        self.assertEqual(self.queue.claim(self.peer, 'peer-worker')['envelope']['dispatch_id'], peer['envelope']['dispatch_id'])

    def test_reload_and_concurrent_denials_are_read_only_then_stop_releases_restriction(self):
        old = self.queue.claim(self.owner, 'worker')
        self.queue.release(self.owner, old['envelope']['dispatch_id'], 'worker')
        self.queue.enqueue(self.owner, {'dispatch_id': 'manual'})
        sessions = SessionStore(str(self.path))
        coordinated = queue_coordinator.CoordinatedQueue(self.queue._queue, sessions, self.queue._lock)
        before = self.queue.path.read_bytes()
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(lambda _: coordinated.claim(self.owner, 'worker'), range(4))), [None] * 4)
        self.assertEqual(self.queue.path.read_bytes(), before)
        sessions._event_update(self.session_id, lambda run: run.update(stop_id='explicit-stop', state='stopped', dispatch_eligible=False))
        self.assertEqual(coordinated.claim(self.owner, 'worker')['envelope']['dispatch_id'], 'manual')


if __name__ == '__main__':
    unittest.main()
