"""Save-before-post delivery component, real outbox and callback-only transport."""
from copy import deepcopy
import importlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import urllib.error
import uuid

from review_brief import BriefStore, build_brief, freeze_inputs
from tests import test_result_outbox as fixture


class ResultDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.delivery = importlib.import_module('result_delivery')
        storage = fixture.ResultOutboxTests()
        storage.setUp()
        self.addCleanup(storage.doCleanups)
        self.storage = storage
        self.runtime, self.box = storage.runtime, storage.box
        template = {'id': 'delivery', 'name': 'Delivery component', 'roles': ['reader'], 'phases': [
            {'name': 'Review', 'participants': ['reader'], 'prompt': 'Read source.', 'is_output': True}]}
        self.principal = {'name': 'fixture-api', 'identity_id': storage.payload['seat_identity_id']}
        public = build_brief({'id': 7, **freeze_inputs(template, input_text='Exact source café\r\n')},
                             0, 0, self.principal['name'], self.principal['identity_id'])
        public['completion_protocol'] = 1
        self.dispatch = storage.payload['dispatch_id']
        owner = {'adapter': 'openai-compatible', 'dispatch_id': self.dispatch,
            'seat_identity_id': self.principal['identity_id'], 'launch_attempt': storage.snapshot['attempt'],
            'launch_nonce': storage.snapshot['ownership']['launch_nonce'], 'fingerprint': storage.snapshot['ownership']['fingerprint']}
        self.briefs = BriefStore(storage.root)
        brief_id = self.briefs.put(public, result_owner=owner)
        self.envelope = self.briefs.get_delivery(brief_id, self.principal)
        self.secret = self.envelope['seal_secret']
        self.content = storage.payload['content']
        self.payload = {**deepcopy(storage.payload), **{key: self.envelope[key] for key in
            ('session_id', 'brief_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')},
            **{key: owner[key] for key in ('seat_identity_id', 'launch_attempt', 'launch_nonce', 'fingerprint')}}

    def run_turn(self, generate, submit, **kwargs):
        return self.delivery.complete_review_turn(self.runtime, self.envelope, self.dispatch, generate, submit, **kwargs)

    def event(self, kind='final'):
        return {key: self.payload[key] for key in ('brief_id', 'event_id', 'run_id', 'turn_id', 'attempt_id', 'input_revision')} | {
            'kind': kind, 'content': self.content}

    def test_atomic_save_and_callback_precede_exact_submit_and_ack(self):
        order = []
        def generate():
            order.append('generate')
            self.assertIsNone(self.box.find(self.dispatch))
            return json.dumps({'kind': 'final', 'content': self.content})
        def on_saved(result_id):
            order.append('saved')
            self.assertEqual(result_id, self.dispatch)
            self.assertEqual(self.storage.module.verify_result(self.box.get(result_id), self.secret)['content'], self.content)
            self.assertIsNone(self.box.get_ack(result_id))
        def submit(event):
            order.append('submit')
            self.assertEqual(event, self.event())
            self.assertNotIn(self.secret, json.dumps(event))
            self.assertEqual(self.box.get(self.dispatch)['payload']['content'], self.content)
            return {'status': 'admitted', 'event_id': self.dispatch}
        result = self.run_turn(generate, submit, on_saved=on_saved)
        self.assertEqual(result, {'status': 'admitted', 'result_id': self.dispatch})
        self.assertEqual(order, ['generate', 'saved', 'submit'])
        self.assertEqual(self.box.get_ack(self.dispatch)['accepted_event_id'], self.dispatch)

    def test_existing_saved_record_never_regenerates_or_auto_submits(self):
        self.box.save(self.payload, self.secret)
        path = self.storage.result_path()
        original = path.read_bytes()
        generate, submit, saved = Mock(side_effect=AssertionError('must not generate')), Mock(side_effect=AssertionError('must not submit')), Mock()
        result = self.run_turn(generate, submit, on_saved=saved)
        self.assertEqual(result, {'status': 'saved', 'result_id': self.dispatch})
        generate.assert_not_called()
        submit.assert_not_called()
        saved.assert_called_once_with(self.dispatch)
        self.assertIsNone(self.box.get_ack(self.dispatch))
        self.assertEqual(path.read_bytes(), original)

    def test_find_absence_is_read_only_but_malformed_record_is_not_absence(self):
        before = {str(path): path.read_bytes() for path in self.runtime.rglob('*') if path.is_file()}
        self.assertIsNone(self.box.find(self.dispatch))
        self.assertEqual({str(path): path.read_bytes() for path in self.runtime.rglob('*') if path.is_file()}, before)
        path = self.storage.result_path()
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b'{')
        with self.assertRaises(self.storage.module.OutboxError):
            self.box.find(self.dispatch)
        self.assertEqual(path.read_bytes(), b'{')
        path.unlink()
        outside = self.storage.root / 'outside-result.json'
        outside.write_text(json.dumps(self.storage.module.seal_result(self.payload, self.secret)), encoding='utf-8')
        original = outside.read_bytes()
        try:
            path.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest('Native symlink capability unavailable: ' + type(exc).__name__)
        with self.assertRaises(self.storage.module.OutboxError):
            self.box.find(self.dispatch)
        self.assertEqual(outside.read_bytes(), original)

    def raw(self, kind='final'):
        return json.dumps({'kind': kind, 'content': self.content}, ensure_ascii=False)

    def http_error(self, status, body=None):
        return urllib.error.HTTPError('http://127.0.0.1/fixture', status, 'local callback fixture', {},
            io.BytesIO(json.dumps(body or {}).encode()))

    def fresh_dispatch(self):
        public = self.briefs.get(self.envelope['brief_id'], operator=True)
        public.update(brief_id=uuid.uuid4().hex, attempt_id=uuid.uuid4().hex)
        self.dispatch = uuid.uuid4().hex
        owner = {**self.envelope['result_owner'], 'dispatch_id': self.dispatch}
        brief = self.briefs.put(public, result_owner=owner)
        self.envelope = self.briefs.get_delivery(brief, self.principal)
        self.secret = self.envelope['seal_secret']

    def test_invalid_scope_key_or_snapshot_cannot_generate_or_submit(self):
        original = deepcopy(self.envelope)
        mutations = [lambda value: value.pop('seal_secret'), lambda value: value.update(seal_secret='bad'),
            lambda value: value.update(completion_protocol=True),
            lambda value: value['result_owner'].update(adapter='cli'),
            lambda value: value['result_owner'].update(dispatch_id='a' * 32),
            lambda value: value['result_owner'].update(seat_identity_id='b' * 32),
            lambda value: value['result_owner'].update(launch_attempt='c' * 32),
            lambda value: value['result_owner'].update(launch_nonce='d' * 32),
            lambda value: value['result_owner'].update(fingerprint='e' * 64),
            lambda value: value.update(brief_id='../escape')]
        generate, submit = Mock(), Mock()
        try:
            for mutate in mutations:
                self.envelope = deepcopy(original)
                mutate(self.envelope)
                with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                    self.run_turn(generate, submit)
            self.envelope = deepcopy(original)
            path = self.runtime / 'config.json'
            snapshot = json.loads(path.read_text('utf-8'))
            snapshot['seat']['model'] = 'changed-disk-model'
            path.write_text(json.dumps(snapshot), encoding='utf-8')
            with self.assertRaises(ValueError):
                self.run_turn(generate, submit)
        finally:
            self.envelope = original
        generate.assert_not_called()
        submit.assert_not_called()
        self.assertFalse(self.storage.result_path().exists())

    def test_generation_and_strict_response_failures_leave_no_saved_answer_or_post(self):
        submit, saved = Mock(), Mock()
        error = OSError('local generation fixture failure')
        with self.assertRaises(OSError):
            self.run_turn(Mock(side_effect=error), submit, on_saved=saved)
        for text in ('', 'ordinary untyped answer', '{', '{"kind":"final","content":""}',
                     '{"kind":"decision","content":"text"}', '{"kind":"final","content":"x","extra":true}'):
            with self.subTest(response=text), self.assertRaises(ValueError):
                self.run_turn(Mock(return_value=text), submit, on_saved=saved)
            self.assertIsNone(self.box.find(self.dispatch))
        submit.assert_not_called()
        saved.assert_not_called()

    def test_actual_save_replace_failure_prevents_first_submit_and_saved_callback(self):
        generate, submit, saved = Mock(return_value=self.raw()), Mock(), Mock()
        target = self.storage.result_path()
        replace = Path.replace
        def fail_replace(path, destination):
            if Path(destination) == target:
                raise OSError('fixture outbox replace failure')
            return replace(path, destination)
        with patch.object(Path, 'replace', new=fail_replace):
            with self.assertRaises((ValueError, OSError)):
                self.run_turn(generate, submit, on_saved=saved)
        generate.assert_called_once_with()
        submit.assert_not_called()
        saved.assert_not_called()
        self.assertIsNone(self.box.find(self.dispatch))
        self.assertEqual(self.box.list_records(), [])

    def test_post_outage_has_three_attempts_one_generation_and_one_saved_record(self):
        attempts, saved = [], Mock()
        generate = Mock(return_value=self.raw())
        def submit(event):
            attempts.append(deepcopy(event))
            self.assertEqual(self.box.get(self.dispatch)['payload']['content'], self.content)
            raise urllib.error.URLError('local callback unavailable')
        with self.assertRaises((OSError, ValueError)):
            self.run_turn(generate, submit, on_saved=saved)
        self.assertEqual(attempts, [self.event()] * 3)
        generate.assert_called_once_with()
        saved.assert_called_once_with(self.dispatch)
        self.assertEqual(len(self.box.list_records()), 1)
        self.assertIsNone(self.box.get_ack(self.dispatch))
        self.assertEqual(self.storage.module.verify_result(self.box.get(self.dispatch), self.secret)['content'], self.content)

    def test_network_then_http503_retries_exact_same_event_without_new_save_or_generate(self):
        attempts = []
        def submit(event):
            attempts.append(deepcopy(event))
            if len(attempts) == 1:
                raise urllib.error.URLError('local callback unavailable')
            if len(attempts) == 2:
                raise self.http_error(503)
            return {'status': 'admitted', 'event_id': self.dispatch}
        generate, saved = Mock(return_value=self.raw()), Mock()
        self.assertEqual(self.run_turn(generate, submit, on_saved=saved), {'status': 'admitted', 'result_id': self.dispatch})
        self.assertEqual(attempts, [self.event()] * 3)
        generate.assert_called_once_with()
        saved.assert_called_once_with(self.dispatch)
        self.assertEqual(self.box.get_ack(self.dispatch)['accepted_event_id'], self.dispatch)

    def test_lost_callback_ack_then_exact_http409_is_idempotent_success(self):
        # A callback set models the transport response only. This test does not
        # establish real HTTP authentication, session admission or projection.
        observed_ids, attempts = set(), []
        def submit(event):
            attempts.append(deepcopy(event))
            observed_ids.add(event['event_id'])
            if len(attempts) == 1:
                raise urllib.error.URLError('fixture successful callback response lost')
            raise self.http_error(409, {'accepted_event_id': self.dispatch})
        generate = Mock(return_value=self.raw('question'))
        self.assertEqual(self.run_turn(generate, submit), {'status': 'admitted', 'result_id': self.dispatch})
        self.assertEqual(attempts, [self.event('question')] * 2)
        self.assertEqual(observed_ids, {self.dispatch})
        generate.assert_called_once_with()
        self.assertEqual(self.box.get(self.dispatch)['payload']['kind'], 'question')
        self.assertEqual(self.box.get_ack(self.dispatch)['accepted_event_id'], self.dispatch)

    def test_wrong_ack_malformed_success_and_nonretryable_http_fail_once(self):
        outcomes = [self.http_error(status) for status in (400, 401, 403, 404)] + [
            self.http_error(409, {'accepted_event_id': 'a' * 32}),
            {'status': 'admitted', 'event_id': 'b' * 32}, {'status': 'admitted'},
            {'status': 'saved', 'event_id': 'a' * 32}, [], None]
        for outcome in outcomes:
            self.fresh_dispatch()
            submit = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
            generate = Mock(return_value=self.raw())
            with self.subTest(outcome_type=type(outcome).__name__), self.assertRaises((ValueError, OSError)):
                self.run_turn(generate, submit)
            submit.assert_called_once()
            generate.assert_called_once_with()
            self.assertIsNotNone(self.box.find(self.dispatch))
            self.assertIsNone(self.box.get_ack(self.dispatch))

    def test_ack_write_failure_retains_saved_record_then_replay_is_explicit_saved_only(self):
        target = self.runtime / 'outbox_ack' / (self.dispatch + '.json')
        replace = Path.replace
        def fail_replace(path, destination):
            if Path(destination) == target:
                raise OSError('fixture local acknowledgement write failure')
            return replace(path, destination)
        generate = Mock(return_value=self.raw())
        submit = Mock(return_value={'status': 'admitted', 'event_id': self.dispatch})
        with patch.object(Path, 'replace', new=fail_replace):
            with self.assertRaises((ValueError, OSError)):
                self.run_turn(generate, submit)
        generate.assert_called_once_with()
        submit.assert_called_once()
        disk = self.storage.result_path().read_bytes()
        self.assertIsNone(self.box.get_ack(self.dispatch))
        generate.reset_mock()
        submit.reset_mock()
        self.assertEqual(self.run_turn(generate, submit), {'status': 'saved', 'result_id': self.dispatch})
        generate.assert_not_called()
        submit.assert_not_called()
        self.assertEqual(self.storage.result_path().read_bytes(), disk)
        self.assertIsNone(self.box.get_ack(self.dispatch))

    def test_existing_record_wrong_key_scope_or_unreadable_storage_never_regenerates(self):
        self.box.save(self.payload, self.secret)
        generate, submit, saved = Mock(), Mock(), Mock()
        original = deepcopy(self.envelope)
        self.envelope['seal_secret'] = 'f' * 64
        with self.assertRaises(ValueError):
            self.run_turn(generate, submit, on_saved=saved)
        self.envelope = deepcopy(original)
        self.envelope['attempt_id'] = 'e' * 32
        with self.assertRaises(ValueError):
            self.run_turn(generate, submit, on_saved=saved)
        self.envelope = original
        path, open_file = self.storage.result_path(), Path.open
        def unreadable(candidate, *args, **kwargs):
            if candidate == path:
                raise PermissionError('fixture existing result unreadable')
            return open_file(candidate, *args, **kwargs)
        with patch.object(Path, 'open', new=unreadable):
            with self.assertRaises(ValueError):
                self.box.find(self.dispatch)
            with self.assertRaises(ValueError):
                self.run_turn(generate, submit, on_saved=saved)
        generate.assert_not_called()
        submit.assert_not_called()
        saved.assert_not_called()


if __name__ == '__main__':
    unittest.main()
