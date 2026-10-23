"""Managed API outbox storage and integrity, without native adoption claims."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import importlib
import json
import math
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from runtime_ownership import new_launch_identity, record_spawn_outcome


class ResultOutboxTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('result_outbox')
        (ROOT / '.audit-tmp').mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / '.audit-tmp')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime, self.snapshot = self.runtime_fixture()
        self.secret = bytes(range(32)).hex()
        run = '1' * 32
        self.payload = {'version': 1, 'result_id': '2' * 32, 'dispatch_id': '2' * 32, 'event_id': '2' * 32,
            'session_id': 7, 'brief_id': '3' * 32, 'run_id': run, 'turn_id': run + ':0:1',
            'attempt_id': '4' * 32, 'input_revision': '5' * 64, 'seat_identity_id': '6' * 32,
            'launch_attempt': self.snapshot['attempt'], 'launch_nonce': self.snapshot['ownership']['launch_nonce'],
            'fingerprint': self.snapshot['ownership']['fingerprint'], 'kind': 'final',
            'content': 'Exact café 日本語 e\u0301\r\n@all is quoted output.\n```python\nprint("data")\n```',
            'created_at': 1792730000.125}
        self.box = self.module.ResultOutbox(self.runtime)

    def runtime_fixture(self, adapter='openai-compatible'):
        attempt, key = uuid.uuid4().hex, 'fixture/api'
        effective = {'seat': {'id': 'api', 'name': 'Fixture API', 'adapter': adapter, 'provider': 'fake',
            'model': 'frozen-model', 'reasoning': None, 'launch_profile': 'standard', 'secret_ref': 'FIXTURE_KEY_REF'},
            'provider': {'base_url': 'http://127.0.0.1:19999/v1', 'system_prompt': 'PRIVATE_PROVIDER_SENTINEL'},
            'server': {'data_dir': str(self.root / 'data'), 'host': '127.0.0.1', 'port': 19998},
            'mcp': {'http_port': 19997, 'sse_port': 19996}}
        ownership = new_launch_identity(self.root, effective, key, attempt, uuid.uuid4().hex)
        prefix = 'api-' if adapter == 'openai-compatible' else 'cli-'
        snapshot = {**effective, 'attempt': attempt, 'ownership': ownership,
                    'base': prefix + hashlib.sha256(key.encode()).hexdigest()[:8] + '-' + attempt[:12]}
        runtime = self.root / 'data' / 'api_seat_runtime' / attempt
        atomic_json(runtime / 'config.json', snapshot)
        record_spawn_outcome(runtime / 'config.json', snapshot, 'pending')
        return runtime, snapshot

    def result_path(self, result_id=None):
        return self.runtime / 'outbox' / ((result_id or self.payload['result_id']) + '.json')

    def test_independent_canonical_hmac_preserves_exact_unicode_and_newlines(self):
        record = self.module.seal_result(self.payload, self.secret)
        canonical = json.dumps(self.payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        expected = hmac.new(bytes.fromhex(self.secret), canonical, hashlib.sha256).hexdigest()
        self.assertEqual(record, {'payload': self.payload, 'seal': expected})
        self.assertEqual(self.module.verify_result(record, self.secret), self.payload)
        record['payload']['content'] = 'edited local copy'
        self.assertNotEqual(record['payload']['content'], self.payload['content'])

    def test_same_id_immutable_replay_survives_reopen(self):
        first = self.box.save(self.payload, self.secret)
        original = self.result_path().read_bytes()
        reopened = self.module.ResultOutbox(self.runtime)
        self.assertEqual(reopened.save(deepcopy(self.payload), self.secret), first)
        self.assertEqual(self.result_path().read_bytes(), original)
        changed = {**self.payload, 'content': 'Different answer with the same stable ID'}
        with self.assertRaises(self.module.OutboxConflict):
            reopened.save(changed, self.secret)
        self.assertEqual(self.result_path().read_bytes(), original)

    def test_ack_is_separate_exact_and_retains_original_time(self):
        self.box.save(self.payload, self.secret)
        original = self.result_path().read_bytes()
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))
        ack = self.box.acknowledge(self.payload['result_id'], self.payload['event_id'])
        self.assertEqual(set(ack), {'version', 'result_id', 'accepted_event_id', 'acknowledged_at'})
        self.assertEqual(ack['result_id'], self.payload['result_id'])
        self.assertEqual(ack['accepted_event_id'], self.payload['event_id'])
        self.assertGreater(ack['acknowledged_at'], 0)
        self.assertEqual(self.module.ResultOutbox(self.runtime).acknowledge(self.payload['result_id'], self.payload['event_id']), ack)
        self.assertEqual(self.result_path().read_bytes(), original)

    def changed(self, **changes):
        return {**deepcopy(self.payload), **changes}

    def new_result(self, value='a'):
        return self.changed(result_id=value * 32, dispatch_id=value * 32, event_id=value * 32)

    def test_tampered_payload_seal_and_wrong_key_never_verify(self):
        record = self.module.seal_result(self.payload, self.secret)
        for field, value in (('content', 'Changed answer'), ('kind', 'question'), ('session_id', 8),
                             ('seat_identity_id', 'a' * 32), ('input_revision', 'b' * 64)):
            altered = deepcopy(record)
            altered['payload'][field] = value
            with self.subTest(field=field), self.assertRaises(self.module.OutboxError):
                self.module.verify_result(altered, self.secret)
        with self.assertRaises(self.module.OutboxError):
            self.module.verify_result(record, bytes(reversed(range(32))).hex())
        for seal in ('0' * 64, 'F' * 64, '', None, True):
            with self.subTest(seal_type=type(seal).__name__), self.assertRaises(self.module.OutboxError):
                self.module.verify_result({**record, 'seal': seal}, self.secret)
        for key in ('x' * 64, self.secret.upper(), '0' * 63, '0' * 65, b'0' * 64, None, True):
            with self.subTest(key_type=type(key).__name__), self.assertRaises(self.module.OutboxError):
                self.module.seal_result(self.payload, key)

    def test_identifiers_and_linked_turn_scope_are_strict(self):
        fields = ('result_id', 'dispatch_id', 'event_id', 'brief_id', 'run_id', 'attempt_id', 'seat_identity_id',
                  'launch_attempt', 'launch_nonce', 'input_revision', 'fingerprint')
        for field in fields:
            for value in (None, True, 7, '../escape', 'A' * len(self.payload[field]), '0' * (len(self.payload[field]) - 1)):
                with self.subTest(field=field, value_type=type(value).__name__), self.assertRaises(self.module.OutboxError):
                    self.module.seal_result(self.changed(**{field: value}), self.secret)
        for changes in ({'dispatch_id': 'a' * 32}, {'event_id': 'b' * 32},
                        {'turn_id': 'a' * 32 + ':0:1'}, {'turn_id': self.payload['run_id'] + ':-1:0'},
                        {'turn_id': self.payload['run_id'] + ':0:1:2'}, {'turn_id': None}):
            with self.subTest(changes=changes), self.assertRaises(self.module.OutboxError):
                self.module.seal_result(self.changed(**changes), self.secret)

    def test_exact_schema_numeric_types_and_private_field_refusal(self):
        for field in self.payload:
            value = deepcopy(self.payload)
            del value[field]
            with self.subTest(missing=field), self.assertRaises(self.module.OutboxError):
                self.module.seal_result(value, self.secret)
        for field in ('seal_secret', 'token', 'provider_credential', 'source', 'unknown'):
            with self.subTest(extra=field), self.assertRaises(self.module.OutboxError):
                self.module.seal_result(self.changed(**{field: 'PRIVATE_CREDENTIAL_SENTINEL'}), self.secret)
        for field, values in (('version', (True, '1', 1.0, 0, 2)), ('session_id', (True, '7', 7.0, 0, -1)),
                              ('created_at', (True, '1', 0, -1, math.nan, math.inf, -math.inf))):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(self.module.OutboxError):
                    self.module.seal_result(self.changed(**{field: value}), self.secret)
        valid = self.module.seal_result(self.payload, self.secret)
        for value in ([], None, {**valid, 'key': self.secret}, {'payload': self.payload}, {'seal': valid['seal']}):
            with self.subTest(record_type=type(value).__name__), self.assertRaises(self.module.OutboxError):
                self.module.verify_result(value, self.secret)

    def test_question_and_exact_utf8_byte_boundary_without_clipping(self):
        limit = 512 * 1024
        text = 'é' * (limit // 2)
        payload = self.changed(kind='question', content=text)
        self.assertEqual(self.module.verify_result(self.box.save(payload, self.secret), self.secret)['content'], text)
        for kind, content in (('final', text + 'a'), ('question', '\ud800'), ('final', '\0bad'),
                              ('final', ' \r\n'), ('final', None), ('decision', 'plain text'), (True, 'text')):
            with self.subTest(kind=kind, content_type=type(content).__name__), self.assertRaises(self.module.OutboxError):
                self.module.seal_result(self.changed(kind=kind, content=content), self.secret)

    def test_reads_are_deep_copies_sorted_read_only_and_private_keys_are_absent(self):
        before = {str(p.relative_to(self.runtime)): p.read_bytes() for p in self.runtime.rglob('*') if p.is_file()}
        self.assertEqual(self.box.list_records(), [])
        self.assertIsNone(self.box.get_ack(self.payload['result_id']))
        self.assertEqual({str(p.relative_to(self.runtime)): p.read_bytes() for p in self.runtime.rglob('*') if p.is_file()}, before)
        first = self.box.save(self.new_result('b'), self.secret)
        second = self.box.save(self.new_result('a'), self.secret)
        values = self.box.list_records()
        self.assertEqual([v['payload']['result_id'] for v in values], ['a' * 32, 'b' * 32])
        values[0]['payload']['content'] = 'mutated list copy'
        second['payload']['content'] = 'mutated save copy'
        retrieved = self.box.get('a' * 32)
        self.assertEqual(retrieved['payload']['content'], self.payload['content'])
        retrieved['payload']['content'] = 'mutated get copy'
        self.assertEqual(self.box.get('a' * 32)['payload']['content'], self.payload['content'])
        self.box.acknowledge('a' * 32, 'a' * 32)
        for path in (*self.runtime.glob('outbox/*.json'), *self.runtime.glob('outbox_ack/*.json')):
            text = path.read_text('utf-8')
            for excluded in (self.secret, 'PRIVATE_PROVIDER_SENTINEL', 'PRIVATE_CREDENTIAL_SENTINEL', 'FIXTURE_KEY_REF'):
                self.assertNotIn(excluded, text)
        self.assertEqual(first['payload']['content'], self.payload['content'])

    def test_payload_and_existing_results_stay_bound_to_exact_frozen_launch(self):
        self.box.save(self.payload, self.secret)
        original = self.result_path().read_bytes()
        for field, value in (('launch_attempt', 'a' * 32), ('launch_nonce', 'b' * 32), ('fingerprint', 'c' * 64)):
            with self.subTest(field=field), self.assertRaises(self.module.OutboxError):
                self.box.save(self.changed(**{field: value}), self.secret)
            self.assertEqual(self.result_path().read_bytes(), original)
        path = self.runtime / 'config.json'
        config = path.read_bytes()
        for mutate in (lambda s: s['seat'].update(model='changed-model'),
                       lambda s: s['ownership'].update(launch_nonce='e' * 32),
                       lambda s: s['ownership'].update(fingerprint='f' * 64),
                       lambda s: s.update(attempt='d' * 32)):
            value = deepcopy(self.snapshot)
            mutate(value)
            atomic_json(path, value)
            try:
                with self.assertRaises(self.module.OutboxError):
                    self.module.ResultOutbox(self.runtime).get(self.payload['result_id'])
            finally:
                path.write_bytes(config)
        self.assertEqual(self.result_path().read_bytes(), original)

    def test_cli_legacy_and_arbitrary_runtime_directories_are_refused_without_writes(self):
        cli, snapshot = self.runtime_fixture(adapter='cli')
        legacy, old = self.runtime_fixture()
        del old['ownership']
        atomic_json(legacy / 'config.json', old)
        unrelated = self.root / 'unrelated'
        unrelated.mkdir()
        atomic_json(unrelated / 'config.json', self.snapshot)
        for path in (cli, legacy, unrelated, self.root / 'missing', self.runtime / '..'):
            before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
            with self.subTest(path=path.name), self.assertRaises(self.module.OutboxError):
                self.module.ResultOutbox(path).save(self.payload, self.secret)
            self.assertEqual({str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, before)

    def test_atomic_save_failure_keeps_prior_bytes_and_cannot_resurrect_failed_record(self):
        self.box.save(self.payload, self.secret)
        original = self.result_path().read_bytes()
        candidate = self.new_result('a')
        target = self.result_path(candidate['result_id'])
        replace = Path.replace
        def fault(path, destination):
            if Path(destination) == target:
                raise OSError('bounded atomic replace fixture')
            return replace(path, destination)
        with patch.object(Path, 'replace', new=fault):
            with self.assertRaises((OSError, self.module.OutboxError)):
                self.box.save(candidate, self.secret)
        self.assertEqual(self.result_path().read_bytes(), original)
        self.assertFalse(target.exists())
        self.box.save(self.new_result('b'), self.secret)
        self.assertEqual([r['payload']['result_id'] for r in self.module.ResultOutbox(self.runtime).list_records()],
                         [self.payload['result_id'], 'b' * 32])

    def test_atomic_ack_failure_preserves_result_and_previous_ack_bytes(self):
        self.box.save(self.payload, self.secret)
        original = self.result_path().read_bytes()
        first = self.box.acknowledge(self.payload['result_id'], self.payload['result_id'])
        previous = self.runtime / 'outbox_ack' / (self.payload['result_id'] + '.json')
        previous_bytes = previous.read_bytes()
        candidate = self.new_result('a')
        self.box.save(candidate, self.secret)
        target = self.runtime / 'outbox_ack' / ('a' * 32 + '.json')
        replace = Path.replace
        def fault(path, destination):
            if Path(destination) == target:
                raise OSError('bounded ack replace fixture')
            return replace(path, destination)
        with patch.object(Path, 'replace', new=fault):
            with self.assertRaises((OSError, self.module.OutboxError)):
                self.box.acknowledge('a' * 32, 'a' * 32)
        self.assertFalse(target.exists())
        self.assertIsNone(self.box.get_ack('a' * 32))
        self.assertEqual(self.result_path().read_bytes(), original)
        self.assertEqual(previous.read_bytes(), previous_bytes)
        self.assertEqual(self.box.get_ack(self.payload['result_id']), first)
        self.assertEqual(self.module.ResultOutbox(self.runtime).acknowledge('a' * 32, 'a' * 32)['accepted_event_id'], 'a' * 32)

    def test_ack_requires_existing_exact_result_and_rejects_malformed_ack(self):
        with self.assertRaises(self.module.OutboxError):
            self.box.acknowledge(self.payload['result_id'], self.payload['event_id'])
        self.box.save(self.payload, self.secret)
        with self.assertRaises(self.module.OutboxError):
            self.box.acknowledge(self.payload['result_id'], 'a' * 32)
        ack = self.box.acknowledge(self.payload['result_id'], self.payload['event_id'])
        path = self.runtime / 'outbox_ack' / (self.payload['result_id'] + '.json')
        for changes in ({'version': True}, {'result_id': 'a' * 32}, {'accepted_event_id': 'b' * 32},
                        {'acknowledged_at': True}, {'acknowledged_at': 0}, {'acknowledged_at': math.nan}, {'extra': 'field'}):
            malformed = {**ack, **changes}
            path.write_text(json.dumps(malformed), encoding='utf-8')
            disk = path.read_bytes()
            with self.subTest(changes=changes), self.assertRaises(self.module.OutboxError):
                self.module.ResultOutbox(self.runtime).get_ack(self.payload['result_id'])
            self.assertEqual(path.read_bytes(), disk)

    def test_malformed_final_records_fail_closed_without_rewrite_and_temps_are_ignored(self):
        record = self.box.save(self.payload, self.secret)
        for filename in ('partial.tmp', 'x.lock', self.payload['result_id'] + '.json.tmp'):
            (self.runtime / 'outbox' / filename).write_bytes(b'not a record')
        self.assertEqual(self.box.list_records(), [record])
        for value in (b'{', b'[]', b'null', b'\xff', json.dumps({**record, 'unknown': True}).encode(),
                      json.dumps({'payload': self.changed(launch_nonce='a' * 32), 'seal': record['seal']}).encode()):
            self.result_path().write_bytes(value)
            for read in (lambda: self.box.get(self.payload['result_id']), self.box.list_records):
                with self.subTest(prefix=value[:10]), self.assertRaises(self.module.OutboxError):
                    read()
                self.assertEqual(self.result_path().read_bytes(), value)

    def test_path_identifiers_cannot_escape_or_mutate_external_files(self):
        canary = self.root / 'outside.json'
        canary.write_bytes(b'outside preserved')
        for identifier in ('../outside', '..\\outside', str(canary.resolve()), 'a/b', '.', '', True, None):
            for operation in (lambda: self.box.get(identifier), lambda: self.box.get_ack(identifier),
                              lambda: self.box.acknowledge(identifier, identifier)):
                with self.subTest(identifier=identifier), self.assertRaises(self.module.OutboxError):
                    operation()
            self.assertEqual(canary.read_bytes(), b'outside preserved')
        self.assertFalse((self.root / 'outbox').exists())

    def test_symlink_outbox_directory_and_result_file_are_refused(self):
        outside = self.root / 'outside'
        outside.mkdir()
        runtime, snapshot = self.runtime_fixture()
        try:
            (runtime / 'outbox').symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest('Native symlink capability unavailable: ' + type(exc).__name__)
        payload = self.changed(launch_attempt=snapshot['attempt'], launch_nonce=snapshot['ownership']['launch_nonce'],
                               fingerprint=snapshot['ownership']['fingerprint'])
        with self.assertRaises(self.module.OutboxError):
            self.module.ResultOutbox(runtime).save(payload, self.secret)
        self.assertEqual(list(outside.iterdir()), [])
        self.result_path().parent.mkdir(exist_ok=True)
        canary = outside / 'record.json'
        canary.write_text(json.dumps(self.module.seal_result(self.payload, self.secret)), encoding='utf-8')
        disk = canary.read_bytes()
        self.result_path().symlink_to(canary)
        for operation in (lambda: self.box.get(self.payload['result_id']), lambda: self.box.save(self.payload, self.secret), self.box.list_records):
            with self.assertRaises(self.module.OutboxError):
                operation()
        self.assertEqual(canary.read_bytes(), disk)

    def test_concurrent_conflicting_thread_saves_choose_one_immutable_winner(self):
        candidates = [self.changed(content='Thread answer ' + str(number)) for number in range(6)]
        def save(payload):
            try:
                return self.module.ResultOutbox(self.runtime).save(payload, self.secret)
            except self.module.OutboxConflict:
                return None
        with ThreadPoolExecutor(max_workers=6) as pool:
            outcomes = list(pool.map(save, candidates))
        winners = [record for record in outcomes if record is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(self.box.list_records(), winners)
        self.assertIn(self.module.verify_result(winners[0], self.secret), candidates)

    def test_concurrent_process_save_and_ack_share_one_stable_acknowledgement(self):
        code = ('import json,sys;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                'from result_outbox import ResultOutbox;packet=json.load(sys.stdin);'
                'box=ResultOutbox(packet["runtime"]);box.save(packet["payload"],packet["secret"]);'
                'print(json.dumps(box.acknowledge(packet["payload"]["result_id"],packet["payload"]["event_id"])))')
        packet = json.dumps({'runtime': str(self.runtime), 'payload': self.payload, 'secret': self.secret}).encode()
        children = []
        try:
            for _ in range(3):
                children.append(subprocess.Popen([sys._base_executable, '-c', code], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)))
            def communicate(child):
                stdout, stderr = child.communicate(input=packet, timeout=15)
                self.assertEqual(child.returncode, 0, stderr.decode('utf-8', errors='replace'))
                return json.loads(stdout)
            with ThreadPoolExecutor(max_workers=3) as pool:
                acknowledgements = list(pool.map(communicate, children))
            self.assertEqual(acknowledgements, [acknowledgements[0]] * 3)
            self.assertEqual(self.box.get_ack(self.payload['result_id']), acknowledgements[0])
            self.assertEqual(len(self.box.list_records()), 1)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()  # Exact owned base-interpreter child, no grandchildren.
                child.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
