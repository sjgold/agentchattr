"""Artifact worker components with fixture-controlled support and callbacks.

Real owned files, service, queue and current-boot bindings; process observations
and transport/provider callbacks are doubles. No native/network acceptance.
"""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock, patch
import urllib.error
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

    def api_scope(self):
        """Distinct real owned runtime for each simulated sequential API producer."""
        seats = [s for s in self.package['seats'] if s['adapter'] == 'openai-compatible']
        name = 'api' if not any(k == 'team/api' for k in self.manager.attempts) else 'api' + str(len(seats))
        if name != 'api':
            self.package['seats'].append({**seats[0], 'id': name, 'name': name})
            self.manager.store.save(self.package)
        instance, attempt, _ = self.launch_binding(name)
        audit, consumer = self.claimed(instance=instance)
        record, owned = self.owned(audit, instance, attempt)
        return instance, attempt, audit, consumer, record, owned

    def api_callbacks(self, instance, *, generate=None):
        return {'fetch_delivery': lambda brief: self.authority.get_delivery(brief, instance),
            'fetch_parent': lambda brief: self.authority.get_parent(brief, instance),
            'generate': generate or self.forbidden,
            'submit_saved': lambda value: self.authority.admit_saved(value, instance),
            'reject_response': lambda report: self.authority.reject_response(
                self.current_brief, report['content'], instance,
                received_truncated=report['received_truncated']),
            'cancel_requested': lambda dispatch: False}

    def queue_client(self, instance, *, consumer=None):
        """In-process transport adapter over the real coordinator, no HTTP client."""
        queue = self.trigger.queue
        class Client:
            def __init__(self):
                self.consumer_id = consumer or uuid.uuid4().hex
                self.calls = []
            def claim(inner):
                inner.calls.append(('claim',))
                return queue.claim(instance, inner.consumer_id)
            def inspect(inner, dispatch):
                inner.calls.append(('inspect', dispatch))
                value = queue.owned(instance, dispatch)
                if value['consumer_id'] != inner.consumer_id:
                    raise PermissionError('Wrong fixture consumer')
                return value
            def acknowledge(inner, dispatch):
                inner.calls.append(('ack', dispatch))
                return queue.acknowledge(instance, dispatch, inner.consumer_id)
            def uncertain(inner, dispatch):
                inner.calls.append(('uncertain', dispatch))
                return queue.uncertain(instance, dispatch, inner.consumer_id)
            def release(inner, dispatch, *, failed=False, error_category='', http_status=None):
                inner.calls.append(('release', dispatch, failed, error_category))
                return queue.release(instance, dispatch, inner.consumer_id, failed=failed,
                                     error=error_category, http_status=http_status)
            def cancellation_receipt(inner, dispatch, status):
                inner.calls.append(('cancel', dispatch, status))
                return queue.cancellation_receipt(instance, dispatch, inner.consumer_id, status)
        return Client()

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
            with self.subTest(change=change):
                with self.assertRaises(worker.ArtifactWorkerError) as caught:
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

    def test_fresh_cli_prompt_uses_assigned_tools_and_transient_first_fetch_can_retry_once(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        audit, _ = self.claimed()
        record, owned = self.owned(audit)
        fetch = Mock(side_effect=OSError('PRIVATE_URL_OR_TOKEN'))
        decision = worker.preflight_cli_artifact(record, **owned, fetch_brief=fetch, submit_saved=self.forbidden)
        self.assertEqual(decision, {'action': 'wait', 'prompt': None, 'admission': None,
                                    'reason': 'artifact_context_unavailable'})
        fetch.assert_called_once_with(audit['brief_id'])
        public = self.authority.get_brief(audit['brief_id'], self.instance)
        fetch = Mock(return_value=public)
        decision = worker.preflight_cli_artifact(record, **owned, fetch_brief=fetch, submit_saved=self.forbidden)
        self.assertEqual(decision['action'], 'inject')
        self.assertIsNone(decision['admission'])
        self.assertIsNone(decision['reason'])
        prompt = decision['prompt']
        self.assertNotIn('\n', prompt)
        for word in ('chat_artifact_brief', 'chat_artifact_submit', 'chat_queue_release',
                     audit['brief_id'], audit['dispatch_id'], '524288'):
            self.assertIn(word, prompt)
        for forbidden in ('chat_send', 'job_id', audit['producer']['launch_nonce'],
                          public['packet']['messages'][0]['text'], self.instance['token']):
            self.assertNotIn(forbidden, prompt)
        self.assertIn('untrusted', prompt.lower())
        entry = worker.validate_artifact_dispatch(record, **owned)
        entry['channel'] = 'external-mutation'
        self.assertEqual(record['envelope']['channel'], 'review')
        changed = deepcopy(public)
        changed['packet']['messages'][0]['text'] = 'TAMPERED_SOURCE'
        refused = worker.preflight_cli_artifact(record, **owned,
            fetch_brief=lambda brief: changed, submit_saved=self.forbidden)
        self.assertEqual(refused['action'], 'reject')
        self.assertIsNone(refused['prompt'])

    def test_actual_cli_consumer_never_reinjects_same_or_uncertain_work_and_new_consumer_is_busy(self):
        worker = importlib.import_module('artifact_worker')
        from queue_client import CliConsumer
        from dispatch_queue import QueueBusy
        self.setup_authority()
        audit = self.prepare()
        client = self.queue_client(self.instance)
        inject = Mock(return_value=True)
        manifest = self.attempt['effective']['wrapper_protocol']
        fetch_attempts = []
        def fetch(brief):
            fetch_attempts.append(brief)
            if len(fetch_attempts) == 1:
                raise OSError('Controlled transient pre-injection fetch failure')
            return self.authority.get_brief(brief, self.instance)
        def preflight(record, **state):
            return worker.preflight_cli_artifact(record, runtime_path=self.attempt['snapshot'].parent,
                manifest=manifest, consumer_id=client.consumer_id,
                fetch_brief=fetch,
                submit_saved=self.forbidden, **state)
        consumer = CliConsumer(client, inject, self.forbidden, artifact_preflight=preflight)
        consumer.poll()
        inject.assert_not_called()
        self.assertIsNone(consumer.held_artifact_dispatch_id)
        consumer.poll()
        consumer.poll()
        self.assertEqual(inject.call_count, 1)
        self.assertEqual(fetch_attempts, [audit['brief_id'], audit['brief_id']])
        self.assertEqual(self.trigger.queue.owned(self.instance, audit['dispatch_id'])['state'], 'acknowledged')
        restarted = self.queue_client(self.instance)
        restarted_inject = Mock(side_effect=self.forbidden)
        new = CliConsumer(restarted, restarted_inject, self.forbidden,
                          artifact_preflight=Mock(side_effect=self.forbidden))
        with self.assertRaises(QueueBusy):
            new.poll()
        restarted_inject.assert_not_called()
        client.release(audit['dispatch_id'])
        next_audit = self.prepare(channel='peer')
        failed_inject = Mock(return_value=True)
        failing = CliConsumer(client, failed_inject, self.forbidden, artifact_preflight=preflight)
        with patch.object(client, 'acknowledge', side_effect=OSError('PRIVATE_ACK_FAILURE')):
            try:
                failing.poll()
            except OSError:
                pass
        failing.poll()
        failing.poll()
        self.assertEqual(failed_inject.call_count, 1)
        self.assertEqual(self.trigger.queue.owned(self.instance, next_audit['dispatch_id'])['state'], 'uncertain')
        self.assertFalse(any(call[0] == 'release' and call[1] == next_audit['dispatch_id'] for call in client.calls))

    def test_api_saves_exact_unicode_crlf_and_trusted_per_call_model_before_real_submission(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        instance, attempt, audit, _, record, owned = self.api_scope()
        self.current_brief = audit['brief_id']
        text = '\ufeff# Café 日本語 e\u0301\r\n\r\nExact authored bytes.\r\n'
        generate = Mock(return_value={'content': json.dumps({'kind': 'artifact', 'markdown': text}, ensure_ascii=False),
                                      'confirmed_model': 'PER_RESULT_MODEL'})
        callbacks = self.api_callbacks(instance, generate=generate)
        order = []
        def submitted(value):
            path = owned['runtime_path'] / 'artifact_results' / (audit['dispatch_id'] + '.json')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), value)
            order.append('submit')
            return self.authority.admit_saved(value, instance)
        def saved(dispatch):
            self.assertEqual(dispatch, audit['dispatch_id'])
            self.assertTrue((owned['runtime_path'] / 'artifact_results' / (dispatch + '.json')).exists())
            order.append('saved')
        callbacks['submit_saved'] = submitted
        outcome = worker.complete_api_artifact(record, **owned, **callbacks, on_saved=saved)
        self.assertEqual(outcome['status'], 'admitted')
        self.assertIsNone(outcome['reason'])
        self.assertEqual(order, ['saved', 'submit'])
        generate.assert_called_once()
        args = generate.call_args.args
        self.assertEqual(args[1], audit['dispatch_id'])
        self.assertEqual([message['role'] for message in args[0]], ['system', 'user'])
        version = self.artifacts.get_version(outcome['admission']['version_id'])
        self.assertEqual(version['markdown'].encode('utf-8'), text.encode('utf-8'))
        self.assertEqual(version['metadata']['provenance']['observation'],
            {'confirmed_model': 'PER_RESULT_MODEL', 'confirmation_reason': 'api_response'})
        self.assertEqual(self.trigger.queue.owned(instance, audit['dispatch_id'])['state'], 'dispatched')
        attempt['process'].terminate.assert_not_called()

    def test_api_saved_redelivery_lost_ack_and_terminal_disposition_never_fetch_or_generate(self):
        worker = importlib.import_module('artifact_worker')
        delivery = importlib.import_module('artifact_delivery')
        self.setup_authority()
        instance, _, audit, consumer, record, owned = self.api_scope()
        private = self.briefs.get_private(audit['brief_id'])
        signed = self.sealed_fixture_record(audit, consumer,
            observation={'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'})
        box = delivery.ArtifactOutbox(owned['runtime_path'])
        box.save(signed['payload'], private['_artifact_seal']['seal_secret'])
        path = owned['runtime_path'] / 'artifact_results' / (audit['dispatch_id'] + '.json')
        original = path.read_bytes()
        callbacks = dict(fetch_delivery=self.forbidden, fetch_parent=self.forbidden,
            generate=self.forbidden, reject_response=self.forbidden, cancel_requested=lambda dispatch: False)
        def lost_ack(value):
            self.authority.admit_saved(value, instance)
            raise OSError('PRIVATE_LOST_ACK')
        outcome = worker.complete_api_artifact(record, **owned, **callbacks, submit_saved=lost_ack)
        self.assertEqual(outcome, {'status': 'held', 'admission': None, 'reason': 'artifact_delivery_unconfirmed'})
        self.assertEqual(path.read_bytes(), original)
        outcome = worker.complete_api_artifact(record, **owned, **callbacks,
            submit_saved=lambda value: self.authority.admit_saved(value, instance))
        self.assertEqual(outcome['status'], 'admitted')
        self.assertEqual(self.artifacts.list_versions(audit['lineage_id'])['count'], 1)
        other, _, late, late_consumer, late_record, late_owned = self.api_scope()
        signed = self.sealed_fixture_record(late, late_consumer,
            observation={'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'})
        late_box = delivery.ArtifactOutbox(late_owned['runtime_path'])
        late_box.save(signed['payload'], self.briefs.get_private(late['brief_id'])['_artifact_seal']['seal_secret'])
        self.authority.cancel_request(late['request_id'])
        late_record = self.trigger.queue.owned(other, late['dispatch_id'])
        outcome = worker.complete_api_artifact(late_record, **late_owned, **callbacks,
            submit_saved=lambda value: self.authority.admit_saved(value, other))
        self.assertEqual(outcome['status'], 'quarantined')
        self.assertIsNotNone(late_box.get_disposition(late['dispatch_id']))
        outcome = worker.complete_api_artifact(late_record, **late_owned, **callbacks, submit_saved=self.forbidden)
        self.assertEqual(outcome['status'], 'quarantined')

    def test_api_invalid_json_and_real_oversize_report_terminal_without_a_fabricated_prefix(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        malformed = ['```json\n{"kind":"artifact","markdown":"x"}\n```',
            '{"kind":"artifact","markdown":"x","confirmed_model":"FORGED"}',
            '{"kind":"artifact","markdown":"x","markdown":"duplicate"}',
            '{"kind":"artifact","markdown":"bad\\u0000text"}',
            'x' * (self.protocol.MAX_RESULT_RECORD_BYTES + 1)]
        for text in malformed:
            with self.subTest(size=len(text)):
                instance, _, audit, _, record, owned = self.api_scope()
                generate = Mock(return_value={'content': text, 'confirmed_model': 'trusted-callback-model'})
                callbacks = self.api_callbacks(instance, generate=generate)
                reports = []
                def rejected(report):
                    reports.append(deepcopy(report))
                    return self.authority.reject_response(audit['brief_id'], report['content'], instance,
                        received_truncated=report['received_truncated'])
                callbacks['reject_response'] = rejected
                callbacks['submit_saved'] = self.forbidden
                outcome = worker.complete_api_artifact(record, **owned, **callbacks)
                self.assertEqual(outcome['status'], 'quarantined')
                self.assertEqual(outcome['reason'], 'artifact_invalid_response')
                generate.assert_called_once()
                self.assertEqual(len(reports), 1)
                truncated = len(text.encode('utf-8')) > self.protocol.MAX_RESULT_RECORD_BYTES
                self.assertEqual(reports[0], {'content': None if truncated else text, 'received_truncated': truncated})
                self.assertEqual(self.artifacts.get_request(audit['request_id'])['state'], 'quarantined')
                self.assertFalse(list(owned['runtime_path'].glob('artifact_results/*.json')))
                if truncated:
                    rows = self.artifacts.diagnostics()['rows']
                    diagnostic = next(row for row in rows if row.get('dispatch_id') == audit['dispatch_id'])
                    self.assertEqual(diagnostic['byte_count'], 0)
                    self.assertEqual(diagnostic['sha256'], hashlib.sha256(b'').hexdigest())
                    self.assertIsNone(diagnostic['body_object_id'])

    def test_observations_are_isolated_across_sequential_calls_and_two_independent_runtimes(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        first = self.api_scope()
        instance, attempt, audit, consumer, record, owned = first
        callbacks = self.api_callbacks(instance, generate=lambda messages, dispatch: {
            'content': '{"kind":"artifact","markdown":"First"}', 'confirmed_model': 'MODEL_ONE'})
        result = worker.complete_api_artifact(record, **owned, **callbacks)
        self.trigger.queue.release(instance, audit['dispatch_id'], consumer)
        second_audit, _ = self.claimed(instance=instance, channel='peer')
        second_record, second_owned = self.owned(second_audit, instance, attempt)
        callbacks['generate'] = lambda messages, dispatch: {
            'content': '{"kind":"artifact","markdown":"Second"}', 'confirmed_model': None}
        second_result = worker.complete_api_artifact(second_record, **second_owned, **callbacks)
        self.assertEqual(self.artifacts.get_version(result['admission']['version_id'])['metadata']['provenance']['observation'],
            {'confirmed_model': 'MODEL_ONE', 'confirmation_reason': 'api_response'})
        self.assertEqual(self.artifacts.get_version(second_result['admission']['version_id'])['metadata']['provenance']['observation'],
            {'confirmed_model': None, 'confirmation_reason': 'provider_did_not_report_model'})
        contexts = [self.api_scope(), self.api_scope()]
        barrier = threading.Barrier(2)
        def run(item):
            index, context = item
            target, _, _, _, claimed, scope = context
            def generated(messages, dispatch):
                barrier.wait(timeout=5)
                return {'content': json.dumps({'kind': 'artifact', 'markdown': 'Independent ' + str(index)}),
                        'confirmed_model': 'SEAT_' + str(index)}
            return worker.complete_api_artifact(claimed, **scope,
                **self.api_callbacks(target, generate=generated))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, enumerate(contexts)))
        for index, value in enumerate(results):
            observation = self.artifacts.get_version(value['admission']['version_id'])['metadata']['provenance']['observation']
            self.assertEqual(observation, {'confirmed_model': 'SEAT_' + str(index), 'confirmation_reason': 'api_response'})

    def test_api_invocation_fence_inspection_and_cancellation_never_regenerate_existing_intent(self):
        worker = importlib.import_module('artifact_worker')
        evidence = importlib.import_module('invocation_evidence')
        cancelled = importlib.import_module('api_invocation').InvocationCancelled
        self.setup_authority()
        instance, attempt, audit, _, record, owned = self.api_scope()
        before = self.files()
        self.assertEqual(worker.inspect_api_artifact_invocation(owned['runtime_path'], audit['dispatch_id']),
                         {'state': 'not_started', 'local_ended': True})
        self.assertEqual(worker.artifact_api_cancellation_status(owned['runtime_path'], audit['dispatch_id']), 'local_ended')
        self.assertEqual(self.files(), before)
        callbacks = dict(fetch_delivery=self.forbidden, fetch_parent=self.forbidden, generate=self.forbidden,
            submit_saved=self.forbidden, reject_response=self.forbidden, cancel_requested=lambda dispatch: True)
        with self.assertRaises(cancelled) as caught:
            worker.complete_api_artifact(record, **owned, **callbacks)
        self.assertTrue(caught.exception.local_ended)
        scope = {'runtime_path': owned['runtime_path'], 'launch_attempt': attempt['id'],
                 'launch_nonce': attempt['ownership']['launch_nonce'], 'dispatch_id': audit['dispatch_id']}
        intent = evidence.begin(scope)
        before = self.files()
        callbacks['cancel_requested'] = lambda dispatch: False
        with self.assertRaises(cancelled) as caught:
            worker.complete_api_artifact(record, **owned, **callbacks)
        self.assertFalse(caught.exception.local_ended)
        self.assertEqual(worker.artifact_api_cancellation_status(owned['runtime_path'], audit['dispatch_id']), 'unresolved')
        self.assertEqual(self.files(), before)
        evidence.spawn_outcome(intent, 'failed')  # Controlled synchronous-failure journal, not native exit proof.
        before = self.files()
        self.assertEqual(worker.inspect_api_artifact_invocation(owned['runtime_path'], audit['dispatch_id']),
                         {'state': 'ended', 'local_ended': True})
        outcome = worker.complete_api_artifact(record, **owned, **callbacks)
        self.assertEqual(outcome, {'status': 'held', 'admission': None, 'reason': 'artifact_generation_uncertain'})
        self.assertEqual(self.files(), before)
        with self.assertRaises(FileExistsError):
            evidence.begin(scope)

    def test_safe_http_network_storage_and_malformed_ack_outcomes_keep_saved_work(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        audit, consumer = self.claimed()
        record, owned = self.owned(audit)
        for code, action in ((403, 'reject'), (409, 'reject'), (503, 'wait')):
            fetch = Mock(side_effect=urllib.error.HTTPError('http://PRIVATE_TOKEN', code, 'PRIVATE_BODY', {}, None))
            decision = worker.preflight_cli_artifact(record, **owned, fetch_brief=fetch, submit_saved=self.forbidden)
            self.assertEqual(decision['action'], action)
            self.assertNotIn('PRIVATE', json.dumps(decision))
            self.assertIsNone(decision['prompt'])
        signed = self.sealed_fixture_record(audit, consumer)
        box = importlib.import_module('artifact_delivery').ArtifactOutbox(owned['runtime_path'])
        box.save(signed['payload'], self.briefs.get_private(audit['brief_id'])['_artifact_seal']['seal_secret'])
        original = (owned['runtime_path'] / 'artifact_results' / (audit['dispatch_id'] + '.json')).read_bytes()
        for submit in (Mock(side_effect=OSError('PRIVATE_SEND_ERROR')),
                       Mock(return_value={'status': 'admitted', 'event_id': uuid.uuid4().hex})):
            decision = worker.preflight_cli_artifact(record, **owned, fetch_brief=self.forbidden, submit_saved=submit)
            self.assertEqual(decision['action'], 'hold')
            self.assertEqual(decision['reason'], 'artifact_delivery_unconfirmed')
            self.assertNotIn('PRIVATE', json.dumps(decision))
            self.assertEqual((owned['runtime_path'] / 'artifact_results' / (audit['dispatch_id'] + '.json')).read_bytes(), original)
        instance, _, api_audit, _, api_record, api_owned = self.api_scope()
        callbacks = self.api_callbacks(instance)
        callbacks['fetch_delivery'] = Mock(side_effect=OSError('PRIVATE_DELIVERY_ERROR'))
        outcome = worker.complete_api_artifact(api_record, **api_owned, **callbacks)
        self.assertEqual(outcome['status'], 'held')
        self.assertEqual(outcome['reason'], 'artifact_context_unavailable')
        self.assertNotIn('PRIVATE', json.dumps(outcome))
        callbacks = self.api_callbacks(instance, generate=lambda messages, dispatch: {
            'content': '{"kind":"artifact","markdown":"Saved before failure"}', 'confirmed_model': None})
        with patch('artifact_delivery.atomic_json', side_effect=OSError('PRIVATE_SAVE_FAILURE')):
            outcome = worker.complete_api_artifact(api_record, **api_owned, **callbacks)
        self.assertEqual(outcome['status'], 'held')
        self.assertEqual(outcome['reason'], 'artifact_delivery_unconfirmed')
        self.assertEqual(self.artifacts.list_versions(api_audit['lineage_id'])['count'], 0)

    def test_parent_packet_exact_bytes_hashes_caps_and_model_message_privacy(self):
        worker = importlib.import_module('artifact_worker')
        self.setup_authority()
        original, consumer = self.claimed()
        text = '\ufeff# Parent café\r\n' + 'x' * (self.protocol.MAX_ARTIFACT_BYTES - len('\ufeff# Parent café\r\n'.encode('utf-8')))
        ack = self.authority.submit_cli(original['brief_id'], text, self.instance)
        self.trigger.queue.release(self.instance, original['dispatch_id'], consumer)
        metadata = self.artifacts.get_version(ack['version_id'])['metadata']
        api, attempt, _ = self.launch_binding('api')
        parent = {'version_id': metadata['id'], 'sequence': 1, 'sha256': metadata['sha256']}
        audit, _ = self.claimed(instance=api, lineage_id=original['lineage_id'], parent=parent)
        delivery = self.authority.get_delivery(audit['brief_id'], api)
        before = self.files()
        response = self.authority.get_parent(audit['brief_id'], api)
        self.assertEqual(self.files(), before)
        self.assertEqual(response['parent']['markdown'].encode('utf-8'), text.encode('utf-8'))
        self.assertEqual(response['parent']['byte_length'], 524288)
        messages = worker.artifact_messages(delivery, response)
        self.assertEqual([message['role'] for message in messages], ['system', 'user'])
        user = json.loads(messages[1]['content'])
        self.assertEqual(set(user), {'instruction', 'format', 'source', 'parent'})
        self.assertEqual(user['source'], delivery['packet'])
        self.assertEqual(user['parent'], response['parent'])
        self.assertIn('untrusted', messages[0]['content'].lower())
        encoded = json.dumps(messages, ensure_ascii=False)
        for secret in (delivery['seal_secret'], delivery['consumer_id'],
                       delivery['result_owner']['launch_nonce'], api['token']):
            self.assertNotIn(secret, encoded)
        for change in ({'markdown': text + 'x'}, {'sha256': '0' * 64}, {'sequence': 2}):
            altered = {'parent': {**response['parent'], **change}}
            with self.assertRaises(worker.ArtifactWorkerError):
                worker.artifact_messages(delivery, altered)
        corrupted = deepcopy(delivery)
        corrupted['packet']['messages'][0]['text'] = 'HASH_DRIFT'
        with self.assertRaises(worker.ArtifactWorkerError):
            worker.artifact_messages(corrupted, response)
        self.assertEqual(self.files(), before)
        attempt['process'].terminate.assert_not_called()

    def test_binding_manifest_birth_source_drift_and_default_disabled_policy_remain_closed(self):
        worker = importlib.import_module('artifact_worker')
        protocol = importlib.import_module('runtime_protocol')
        self.assertEqual(protocol.SUPPORTED_CAPABILITIES, ())
        self.setup_authority()
        audit, _ = self.claimed()
        record, owned = self.owned(audit)
        for state in ('queued', 'released'):
            altered = {**record, 'state': state}
            with self.assertRaises(worker.ArtifactWorkerError):
                worker.validate_artifact_dispatch(altered, **owned)
        for change in ({'job_id': 0}, {'target_identity_id': uuid.uuid4().hex}):
            altered = deepcopy(record)
            altered['envelope'].update(change)
            with self.assertRaises(worker.ArtifactWorkerError):
                worker.validate_artifact_dispatch(altered, **owned)
        absent = deepcopy(owned['manifest'])
        absent['capabilities'] = []
        with self.assertRaises(worker.ArtifactWorkerError):
            worker.validate_artifact_dispatch(record, **{**owned, 'manifest': absent})
        birth_path = owned['runtime_path'] / 'birth.json'
        birth_bytes = birth_path.read_bytes()
        birth_path.unlink()
        try:
            with self.assertRaises(worker.ArtifactWorkerError):
                worker.validate_artifact_dispatch(record, **owned)
        finally:
            birth_path.write_bytes(birth_bytes)
        source = Path(self.manager.root) / next(iter(owned['manifest']['sources']))
        read_bytes = Path.read_bytes
        # Controlled source BYTE read drift exercises the actual source hasher, no repo edit.
        def changed_bytes(path):
            value = read_bytes(path)
            return value + b'\n# controlled source drift\n' if path == source else value
        with patch.object(Path, 'read_bytes', changed_bytes):
            with self.assertRaises(worker.ArtifactWorkerError):
                worker.validate_artifact_dispatch(record, **owned)
        # Child eligibility comes from its immutable server launch, not a local enable toggle.
        with patch.object(protocol, 'SUPPORTED_CAPABILITIES', ()):
            entry = worker.validate_artifact_dispatch(record, **owned)
            self.assertEqual(entry['dispatch_id'], audit['dispatch_id'])


if __name__ == '__main__':
    unittest.main()
