"""ROOT A1 reds: invocation-only reuse, unchanged real store/service paths.

Behavioral reds count existing semantic validation, not a missing helper.
Infrastructure reds name the frozen private API that does not exist yet.
Assertions after those first failures are unobserved-red invariants, required
in green. All roots are disposable; no process/provider/network acceptance.
"""
from contextlib import contextmanager
from contextvars import copy_context
from copy import deepcopy
from dataclasses import replace
import gc
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid
import weakref
import zipfile

import artifact_archive as codec
import artifact_store as storage
import artifact_worker as worker
from artifact_delivery import ArtifactOutbox
import mcp_bridge
from sealed_result_io import canonical_utf8
from tests import test_artifact_admission as admission_fixture
from tests.test_artifact_import_benchmark import graph
from tests import test_artifact_store as store_fixture


class ArtifactPacketReuseTests(unittest.TestCase):
    def fixture(self, *, managed=False):
        case = admission_fixture.ArtifactAdmissionTests() if managed else store_fixture.ArtifactStoreTests()
        case.setUp()
        root = case.root
        self.addCleanup(lambda: self.assertFalse(root.exists(), 'Temporary root survived cleanup'))
        self.addCleanup(case.doCleanups)
        if managed:
            case.setup_authority()
        return case

    def stored(self, *, source_run=False):
        case = self.fixture()
        _, owner = case.owner()
        packet = case.packet()
        if source_run:
            revision = hashlib.sha256(b'Input').hexdigest()
            packet['input'] = {'text': 'Input', 'input_revision': revision, 'source_document': None}
            packet['source_run'] = {'session_id': 1, 'run_id': 'a' * 32,
                'input_revision': revision, 'state_at_request': 'active'}
        audit = case.queued(storage, owner, packet=packet)
        return case, owner, audit, packet

    @staticmethod
    def scope(owner):
        # INFRASTRUCTURE red until the reviewed private adapter exists.
        return storage._packet_validation_invocation(owner)

    @staticmethod
    def state():
        return storage._PACKET_VALIDATION_INVOCATION.get()

    @staticmethod
    def observations(owner):
        return [{key: value for key, value in row.items() if key != 'updated_at'}
                for row in owner._object_errors.values()]

    def outcome(self, owner, packet_id, *, need_packet=True):
        try:
            if need_packet:
                return ('ok', owner.get_packet(packet_id), self.observations(owner))
            with owner._lock:
                owner._check_index()
                value = owner._packet(packet_id, _need_packet=False)
            return ('ok', value, self.observations(owner))
        except Exception as error:
            return (type(error), str(error), self.observations(owner))

    def mcp_context(self, case, audit):
        with patch.object(mcp_bridge, 'artifact_authority', case.authority), \
                patch.object(mcp_bridge, '_authenticated_instance', return_value=case.instance):
            return json.loads(mcp_bridge.chat_artifact_brief(audit['brief_id']))

    def test_combined_brief_reads_three_times_but_validates_content_once(self):
        """BEHAVIORAL: existing real MCP chain performs three content walks."""
        case = self.fixture(managed=True)
        audit = case.prepare()
        case.claim(audit)
        with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content, \
                patch.object(case.artifacts, '_read_object', wraps=case.artifacts._read_object) as reads:
            result = self.mcp_context(case, audit)
        self.assertEqual(set(result), {'brief', 'packet', 'parent'})
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'active')
        self.assertEqual(reads.call_count, 3)
        self.assertEqual(content.call_count, 1)  # Observed behavioral red.
        # Unobserved-red invariant after the count: existing public method stays.
        self.assertEqual(case.authority.get_parent(audit['brief_id'], case.instance), {'parent': None})

    def test_repeat_public_invocations_are_fresh_and_results_detached(self):
        """BEHAVIORAL: repeat fetch skips activation read but has a fresh scope."""
        case = self.fixture(managed=True)
        audit = case.prepare()
        case.claim(audit)
        with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content, \
                patch.object(case.artifacts, '_read_object', wraps=case.artifacts._read_object) as reads:
            first = self.mcp_context(case, audit)
            original = deepcopy(first['packet'])
            first['packet']['messages'][0]['text'] = 'external mutation'
            second = self.mcp_context(case, audit)
        self.assertEqual(second['packet'], original)
        # STORE-level detachment, independent of MCP's JSON decoding.
        direct = case.artifacts.get_packet(audit['scope']['packet_id'])
        direct['messages'][0]['text'] = 'mutated store return'
        self.assertEqual(case.artifacts.get_packet(audit['scope']['packet_id']), original)
        self.assertEqual(reads.call_count, 5)  # Three initial, two idempotent repeat.
        self.assertEqual(content.call_count, 2)

    def test_separate_api_parent_and_delivery_fetches_have_distinct_invocations(self):
        """BEHAVIORAL: HTTP/API fetches are separate scopes, unlike combined MCP."""
        case = self.fixture(managed=True)
        instance, _, _ = case.launch_binding('api')
        audit = case.prepare(instance=instance)
        case.claim(audit, instance)
        with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content, \
                patch.object(case.artifacts, '_read_object', wraps=case.artifacts._read_object) as reads:
            self.assertEqual(case.authority.get_parent(audit['brief_id'], instance), {'parent': None})
            delivery = case.authority.get_delivery(audit['brief_id'], instance)
        self.assertEqual(delivery['brief']['request_id'], audit['request_id'])
        self.assertEqual(reads.call_count, 3)
        self.assertEqual(content.call_count, 2)

    def test_public_parent_entry_remains_read_only_and_available(self):
        """EXISTING GUARD: combined MCP entry cannot remove the public parent API."""
        case = self.fixture(managed=True)
        audit = case.prepare()
        case.claim(audit)
        before = case.files()
        self.assertEqual(case.authority.get_parent(audit['brief_id'], case.instance), {'parent': None})
        self.assertEqual(case.files(), before)
        self.assertEqual(case.artifacts.get_request(audit['request_id'])['state'], 'queued')

    def test_prepare_reuses_reserve_enqueue_and_queued_validation(self):
        """BEHAVIORAL: put_packet build stays full; three read validations reuse."""
        case = self.fixture(managed=True)
        audit, packet = case.new_request()
        with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content, \
                patch.object(case.artifacts, '_read_object', wraps=case.artifacts._read_object) as reads:
            result = case.authority.prepare_request(audit, packet, audit['request_id'])
        self.assertEqual(result['request']['state'], 'queued')
        self.assertEqual(reads.call_count, 3)
        self.assertEqual(content.call_count, 2)  # One build, one successful read.

    def test_commit_new_reuses_the_same_successful_source_validation(self):
        """BEHAVIORAL: service _packet and _commit_new both read, validate once."""
        case = self.fixture(managed=True)
        audit, _ = case.claimed()
        text = '# Exact result\r\ncafe'
        with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content, \
                patch.object(case.artifacts, '_read_object', wraps=case.artifacts._read_object) as reads:
            result = case.authority.submit_cli(audit['brief_id'], text, case.instance)
        self.assertEqual(result['status'], 'admitted')
        self.assertEqual(case.artifacts.get_version(result['version_id'])['markdown'], text)
        self.assertEqual(reads.call_count, 2)
        self.assertEqual(content.call_count, 1)

    def test_resume_pending_queued_target_preserves_read_but_reuses_walk(self):
        """BEHAVIORAL: resume's queued target reads at the store discard site."""
        case = self.fixture(managed=True)
        audit = case.prepare()
        case.artifacts.set_attempt_state(audit['request_id'], audit['attempt_id'], 'queued',
            {'state': 'queued', 'reason': 'resume_pending'})
        with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content, \
                patch.object(case.artifacts, '_read_object', wraps=case.artifacts._read_object) as reads:
            result = case.authority.resume_request(audit['request_id'])
        self.assertEqual((result['request']['state'], result['request']['reason']), ('queued', 'queued'))
        self.assertEqual(reads.call_count, 2)
        self.assertEqual(content.call_count, 1)

    def test_hit_has_no_new_content_work_and_returns_fresh_packet_and_scope(self):
        """INFRASTRUCTURE first; semantic counts/detachment unobserved-red."""
        case, owner, audit, packet = self.stored()
        key = audit['scope']['packet_id']
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            with case.service._boundary():
                first = owner.get_packet(key)
            # Same invocation survives a genuine authority-boundary release.
            with case.service._boundary(), owner._lock:
                second, scope = owner._packet(key)
            first['messages'][0]['text'] = 'changed first return'
            second['messages'][0]['uid'] = 'changed second return'
            scope['message_refs'][0]['sha256'] = 'f' * 64
            self.assertEqual(owner.get_packet(key), packet)
            with owner._lock:
                _, fresh_scope = owner._packet(key)
            self.assertEqual(fresh_scope, audit['scope'])
            self.assertEqual(content.call_count, 1)

    def test_need_packet_false_still_compares_channel_and_source_run(self):
        """INFRASTRUCTURE first; cached audit-view mismatches must still refuse."""
        for field in ('original_channel', 'source_run'):
            with self.subTest(field=field):
                _, owner, audit, _ = self.stored(source_run=True)
                key = audit['scope']['packet_id']
                with self.scope(owner):
                    owner.get_packet(key)
                    value = deepcopy(owner._data)
                    target = value['requests'][audit['request_id']]['audit']
                    if field == 'original_channel':
                        target[field] = 'peer'
                    else:
                        target[field]['session_id'] = 2
                    owner._persist(value)
                    before = owner.path.read_bytes()
                    self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)
                    self.assertEqual(owner.path.read_bytes(), before)

    def test_need_packet_false_does_not_parse_full_packet_on_a_hit(self):
        """INFRASTRUCTURE first; only small scope/audit-view JSON may parse."""
        _, owner, audit, _ = self.stored(source_run=True)
        key = audit['scope']['packet_id']
        with self.scope(owner):
            owner.get_packet(key)
            raw = owner._object_path('packet', key).read_bytes()
            original = storage.json.loads
            def parse(value, *args, **kwargs):
                compared = value.encode('utf-8') if isinstance(value, str) else value
                self.assertNotEqual(compared, raw, 'Discard hit parsed the packet instead of audit-view bytes')
                return original(value, *args, **kwargs)
            with patch.object(storage.json, 'loads', side_effect=parse), \
                    patch.object(storage.hashlib, 'sha256', side_effect=AssertionError('Hit rehashed packet')), \
                    patch.object(storage, '_packet_scope', side_effect=AssertionError('Content walk on hit')):
                with owner._lock:
                    packet, scope = owner._packet(key, _need_packet=False)
            self.assertIsNone(packet)
            self.assertEqual(scope, audit['scope'])

    def test_nested_public_and_private_scopes_restore_after_exception(self):
        """INFRASTRUCTURE first; nested public entry is a fresh invocation."""
        case = self.fixture(managed=True)
        audit, _ = case.claimed()
        owner = case.artifacts
        key = audit['scope']['packet_id']
        self.assertIsNone(self.state())
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            outer = self.state()
            owner.get_packet(key)
            case.authority.get_parent(audit['brief_id'], case.instance)  # Fresh public scope.
            self.assertIs(self.state(), outer)
            with self.assertRaisesRegex(RuntimeError, 'nested exception'):
                with self.scope(owner):
                    self.assertIsNot(self.state(), outer)
                    owner.get_packet(key)
                    raise RuntimeError('nested exception')
            self.assertIs(self.state(), outer)
            owner.get_packet(key)
            self.assertEqual(content.call_count, 3)
        self.assertIsNone(self.state())

    def test_copied_context_and_second_thread_cannot_consume_or_mutate_evidence(self):
        """INFRASTRUCTURE first; copied ContextVar does not copy thread authority."""
        _, owner, audit, packet = self.stored()
        key = audit['scope']['packet_id']
        errors, results = [], []
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            owner.get_packet(key)
            before_entries = dict(self.state().entries)
            copied = copy_context()
            def read():
                try:
                    results.append(copied.run(owner.get_packet, key))
                except BaseException as error:
                    errors.append(type(error).__name__)
            thread = threading.Thread(target=read)
            thread.start()
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(results, [packet])
            self.assertEqual(self.state().entries, before_entries)
            self.assertTrue(all(self.state().entries[k] is value for k, value in before_entries.items()))
            self.assertEqual(owner.get_packet(key), packet)
            self.assertEqual(content.call_count, 2)
        with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            owner.get_packet(key)
            self.assertEqual(content.call_count, 1)

    def test_second_owner_same_root_cannot_reuse_first_owner_evidence(self):
        _, owner, audit, packet = self.stored()
        other = storage.ArtifactStore(owner.root)
        key = audit['scope']['packet_id']
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            owner.get_packet(key)
            self.assertEqual(other.get_packet(key), packet)
            self.assertEqual(owner.get_packet(key), packet)
            self.assertEqual(content.call_count, 2)

    def test_forged_raw_scope_or_audit_view_pair_falls_back_to_full_validation(self):
        """INFRASTRUCTURE first; no externally registered evidence is trusted."""
        for field, forged in (('raw', b'forged raw'), ('scope_bytes', b'{}'),
                              ('audit_view_bytes', b'{"channel":"peer","source_run":null}')):
            with self.subTest(field=field):
                _, owner, audit, packet = self.stored()
                key = audit['scope']['packet_id']
                with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
                    owner.get_packet(key)
                    state = self.state()
                    evidence = state.entries[key]
                    state.entries[key] = replace(evidence, **{field: forged})
                    self.assertEqual(owner.get_packet(key), packet)
                    self.assertEqual(content.call_count, 2)

    def test_no_evidence_reference_survives_scope_exit(self):
        _, owner, audit, _ = self.stored()
        key = audit['scope']['packet_id']
        owner_keys = set(vars(owner))
        with self.scope(owner):
            owner.get_packet(key)
            state = self.state()
            evidence = state.entries[key]
            state_ref, evidence_ref = weakref.ref(state), weakref.ref(evidence)
            self.assertFalse(any(value is state or value is evidence for value in vars(owner).values()))
        del state, evidence
        gc.collect()
        self.assertIsNone(self.state())
        self.assertIsNone(state_ref())
        self.assertIsNone(evidence_ref())
        self.assertEqual(set(vars(owner)), owner_keys)

    def test_foreign_invocation_evidence_is_not_reissued_by_assigning_an_entry(self):
        _, owner, audit, packet = self.stored()
        key = audit['scope']['packet_id']
        with self.scope(owner):
            owner.get_packet(key)
            retained_for_attack = self.state().entries[key]
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            self.state().entries[key] = retained_for_attack
            self.assertEqual(owner.get_packet(key), packet)
            self.assertEqual(content.call_count, 1)

    def test_third_distinct_packet_validates_without_growing_the_evidence_map(self):
        _, owner, audit, packet = self.stored()
        keys = [audit['scope']['packet_id']]
        for _ in range(2):
            scope = owner.put_packet(uuid.uuid4().hex, deepcopy(packet))
            keys.append(scope['packet_id'])
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            for key in keys + keys:
                self.assertEqual(owner.get_packet(key), packet)
            self.assertEqual(len(self.state().entries), 2)
            self.assertEqual(content.call_count, 4)  # First two once, uncached third twice.

    @contextmanager
    def damage(self, path, variant, raw):
        original_stat = path.stat()
        original_open = Path.open
        try:
            if variant == 'permission':
                def opened(candidate, *args, **kwargs):
                    if candidate == path:
                        raise PermissionError('controlled packet read denial')
                    return original_open(candidate, *args, **kwargs)
                with patch.object(Path, 'open', opened):
                    yield
                return
            if variant == 'decoder_recursion':
                # CPython's C decoder accepts our deep list on this host.
                # This explicit fault seam pins the uncaught parser exception.
                with patch.object(storage.json, 'loads', side_effect=RecursionError('controlled decoder recursion')):
                    yield
                return
            if variant == 'delete':
                path.unlink()
            elif variant == 'symlink':
                target = path.with_name('symlink-target.json')
                target.write_bytes(raw)
                path.unlink()
                try:
                    path.symlink_to(target)
                except OSError as error:
                    self.skipTest('OS refused temp symlink creation: ' + type(error).__name__)
            elif variant == 'truncate':
                path.write_bytes(raw[:10])
            elif variant == 'oversize':
                path.write_bytes(raw + b' ' * (storage.MAX_PACKET_BYTES + 1 - len(raw)))
            elif variant == 'noncanonical':
                path.write_bytes(raw + b' ')
            elif variant == 'deep_nest':
                path.write_bytes(b'[' * 2000 + b'0' + b']' * 2000)
            elif variant == 'same_size_mtime':
                packet = json.loads(raw)
                text = packet['messages'][0]['text']
                packet['messages'][0]['text'] = ('Z' if text[0] != 'Z' else 'Y') + text[1:]
                changed = canonical_utf8(packet)
                self.assertEqual(len(changed), len(raw))
                path.write_bytes(changed)
                os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            else:
                raise AssertionError(variant)
            yield
        finally:
            if path.is_symlink():
                path.unlink()
            path.write_bytes(raw)

    def test_between_read_corruption_matches_uncached_errors_and_observations(self):
        """Baseline runs now; reused half is INFRA, then unobserved-red invariant."""
        for variant in ('truncate', 'oversize', 'delete', 'permission', 'noncanonical', 'same_size_mtime', 'deep_nest', 'decoder_recursion', 'symlink'):
            with self.subTest(variant=variant):
                _, owner, audit, _ = self.stored()
                key = audit['scope']['packet_id']
                path = owner._object_path('packet', key)
                raw, index = path.read_bytes(), owner.path.read_bytes()
                with self.damage(path, variant, raw):
                    baseline = self.outcome(owner, key)
                if variant == 'deep_nest':
                    # C decoder behavior differs by interpreter version.
                    self.assertIn(baseline[0], (RecursionError, storage.ArtifactUnavailable))
                else:
                    self.assertEqual(baseline[0], RecursionError if variant == 'decoder_recursion' else storage.ArtifactUnavailable)
                if baseline[0] is RecursionError:
                    self.assertEqual(baseline[2], [])
                else:
                    self.assertEqual(len(baseline[2]), 1)
                owner._object_errors.clear()
                with self.scope(owner):
                    owner.get_packet(key)
                    with self.damage(path, variant, raw):
                        reused = self.outcome(owner, key)
                    self.assertEqual(reused, baseline)
                self.assertEqual(owner.path.read_bytes(), index)

    def test_failed_first_read_registers_no_evidence_and_recursion_behavior_is_unchanged(self):
        _, owner, audit, packet = self.stored()
        key = audit['scope']['packet_id']
        path = owner._object_path('packet', key)
        raw = path.read_bytes()
        with self.scope(owner):
            with self.damage(path, 'decoder_recursion', raw):
                self.assertEqual(self.outcome(owner, key)[0], RecursionError)
            self.assertEqual(self.state().entries, {})
            self.assertEqual(self.observations(owner), [])
            with self.damage(path, 'truncate', raw):
                self.assertEqual(self.outcome(owner, key)[0], storage.ArtifactUnavailable)
            self.assertEqual(self.state().entries, {})
            self.assertEqual(owner.get_packet(key), packet)
            self.assertEqual(set(self.state().entries), {key})

    def test_current_audit_scope_mismatches_refuse_identically_after_hit(self):
        for field in ('uid', 'sha256', 'id', 'input_revision', 'ref_count'):
            with self.subTest(field=field):
                _, owner, audit, _ = self.stored()
                key = audit['scope']['packet_id']
                def changed_value():
                    value = deepcopy(owner._data)
                    scope = value['requests'][audit['request_id']]['audit']['scope']
                    if field == 'input_revision':
                        scope[field] = 'f' * 64
                    elif field == 'ref_count':
                        scope['message_refs'] = []
                    else:
                        scope['message_refs'][0][field] = {'uid': 'different-uid', 'sha256': 'f' * 64, 'id': 2}[field]
                    return value
                original = deepcopy(owner._data)
                bad = changed_value()
                owner._persist(bad)
                baseline = self.outcome(owner, key)
                self.assertEqual(baseline[0], storage.ArtifactUnavailable)
                owner._persist(original)
                owner._object_errors.clear()
                with self.scope(owner):
                    owner.get_packet(key)
                    owner._persist(bad)
                    before = owner.path.read_bytes()
                    self.assertEqual(self.outcome(owner, key), baseline)
                    self.assertEqual(owner.path.read_bytes(), before)

    def test_scope_is_pure_in_packet_id_and_bytes_not_current_audit(self):
        """EXISTING GUARD: pure computation does not use audit state."""
        _, owner, audit, packet = self.stored()
        key = audit['scope']['packet_id']
        first = storage._packet_scope(key, deepcopy(packet))
        value = deepcopy(owner._data)
        value['requests'][audit['request_id']]['audit']['requester'] = 'another requester'
        value['requests'][audit['request_id']]['audit']['instruction'] = 'Another valid instruction'
        owner._persist(value)
        second = storage._packet_scope(key, deepcopy(packet))
        self.assertEqual(first, second)
        different = storage._packet_scope('f' * 32, deepcopy(packet))
        self.assertNotEqual(different['packet_id'], first['packet_id'])
        self.assertEqual({k: v for k, v in different.items() if k != 'packet_id'},
                         {k: v for k, v in first.items() if k != 'packet_id'})

    def test_direct_worker_import_archive_validation_does_not_consume_store_evidence(self):
        """INFRA first; real direct callers still walk/refuse, not just aliases."""
        case = self.fixture(managed=True)
        audit, consumer = case.claimed()
        private = case.briefs.get_private(audit['brief_id'])
        box = ArtifactOutbox(case.root / 'api_seat_runtime' / audit['producer']['launch_attempt'])
        entry = case.trigger.queue.owned(case.instance, audit['dispatch_id'])['envelope']
        response = case.authority.get_brief(audit['brief_id'], case.instance)
        delivery = {**response, 'brief': {k: deepcopy(v) for k, v in private.items() if k != '_artifact_seal'},
            'seal_secret': private['_artifact_seal']['seal_secret'],
            'result_owner': private['_artifact_seal']['owner'], 'consumer_id': consumer}
        with self.scope(case.artifacts):
            case.artifacts.get_packet(audit['scope']['packet_id'])
            for module, action in ((worker, lambda: worker._check_brief(response, box, entry)),
                           (worker, lambda: worker.artifact_messages(delivery, {'parent': None})),
                           (storage, lambda: case.artifacts.put_packet(audit['request_id'], response['packet']))):
                with patch.object(module, '_packet_scope', wraps=module._packet_scope) as walked:
                    action()
                self.assertEqual(walked.call_count, 1)
            invalid = deepcopy(response)
            invalid['packet']['messages'][0]['uid'] = '\0'
            with self.assertRaises(storage.ArtifactValidationError):
                worker._check_brief(invalid, box, entry)
            invalid_delivery = deepcopy(delivery)
            invalid_delivery['packet']['messages'][0]['uid'] = '\0'
            with self.assertRaises(worker.ArtifactWorkerError):
                worker.artifact_messages(invalid_delivery, {'parent': None})
        portable, objects = graph(1)
        imported_request = portable['requests'][0]
        packet_id = imported_request['scope']['packet_id']
        case.artifacts.put_packet(imported_request['request_id'], json.loads(objects[('packet', packet_id)]))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as zf:
            for (kind, identifier), raw in objects.items():
                zf.writestr(codec.member_name(kind, identifier), raw)
        with self.scope(case.artifacts):
            case.artifacts.get_packet(packet_id)
            with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as import_walked:
                case.artifacts.prepare_import_lineage(portable, objects)
            self.assertEqual(import_walked.call_count, 1)
            with patch.object(codec, '_packet_scope', wraps=codec._packet_scope) as archive_walked:
                with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as zf:
                    self.assertEqual(codec.read_lineage_objects(zf, portable), objects)
            self.assertEqual(archive_walked.call_count, 1)
            bad_portable, bad_objects = deepcopy(portable), deepcopy(objects)
            bad_packet = json.loads(bad_objects[('packet', packet_id)])
            bad_packet['unexpected'] = 'Unknown schema key'
            bad_raw = canonical_utf8(bad_packet)
            bad_objects[('packet', packet_id)] = bad_raw
            bad_portable['requests'][0]['scope'].update(
                sha256=hashlib.sha256(bad_raw).hexdigest(), byte_length=len(bad_raw))
            with self.assertRaises(storage.ArtifactValidationError):
                case.artifacts.prepare_import_lineage(bad_portable, bad_objects)
            bad_stream = io.BytesIO()
            with zipfile.ZipFile(bad_stream, 'w') as zf:
                for (kind, identifier), raw in bad_objects.items():
                    zf.writestr(codec.member_name(kind, identifier), raw)
            with zipfile.ZipFile(io.BytesIO(bad_stream.getvalue())) as zf:
                with self.assertRaises(codec.ArtifactLineageError):
                    codec.read_lineage_objects(zf, bad_portable)

    def test_validate_enqueue_and_export_reuse_only_inside_selected_scope(self):
        """INFRA first; ordinary calls stay full; export bytes stay exact."""
        case = self.fixture(managed=True)
        audit = case.prepare()
        owner = case.artifacts
        key = audit['scope']['packet_id']
        envelope = case.trigger.queue.records()[0]['envelope']
        reference = audit['scope']
        for selected in (False, True):
            with self.subTest(selected=selected):
                @contextmanager
                def chosen():
                    if selected:
                        with self.scope(owner):
                            yield
                    else:
                        yield
                with chosen(), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
                    owner.get_packet(key)
                    case.authority.validate_enqueue(case.instance, envelope)
                    raw = owner.read_archive_object('packet', key,
                        sha256=reference['sha256'], byte_length=reference['byte_length'])
                    self.assertEqual(raw, canonical_utf8(owner.get_packet(key)))
                self.assertEqual(content.call_count, 1 if selected else 4)

    def test_audit_failure_after_valid_content_registers_no_evidence(self):
        _, owner, audit, _ = self.stored()
        key = audit['scope']['packet_id']
        bad = deepcopy(owner._data)
        bad['requests'][audit['request_id']]['audit']['scope']['message_refs'][0]['sha256'] = 'f' * 64
        owner._persist(bad)
        with self.scope(owner):
            self.assertEqual(self.outcome(owner, key)[0], storage.ArtifactUnavailable)
            self.assertEqual(self.state().entries, {})

    def test_need_packet_false_miss_and_scope_mismatch_hit(self):
        _, owner, audit, _ = self.stored()
        key = audit['scope']['packet_id']
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            with owner._lock:
                packet, scope = owner._packet(key, _need_packet=False)
            self.assertIsNone(packet)
            self.assertEqual(scope, audit['scope'])
            bad = deepcopy(owner._data)
            bad['requests'][audit['request_id']]['audit']['scope']['message_refs'][0]['uid'] = 'another-uid'
            owner._persist(bad)
            self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)
            self.assertEqual(content.call_count, 1)

    def test_successful_hit_clears_real_prior_object_observation(self):
        _, owner, audit, packet = self.stored()
        key = audit['scope']['packet_id']
        path = owner._object_path('packet', key)
        raw = path.read_bytes()
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            owner.get_packet(key)
            with self.damage(path, 'truncate', raw):
                self.assertEqual(self.outcome(owner, key)[0], storage.ArtifactUnavailable)
            self.assertEqual(len(self.observations(owner)), 1)
            self.assertEqual(owner.get_packet(key), packet)
            self.assertEqual(self.observations(owner), [])
            self.assertEqual(content.call_count, 1)

    def test_differential_healthy_empty_unicode_crlf_and_max_packets(self):
        for shape in ('empty', 'unicode_crlf', 'max'):
            with self.subTest(shape=shape):
                case = self.fixture()
                _, owner = case.owner()
                packet = case.packet()
                if shape == 'empty':
                    packet['messages'] = []
                elif shape == 'max':
                    base = packet['messages'][0]
                    packet['messages'] = [{**deepcopy(base), 'id': i, 'uid': 'max-' + str(i), 'text': 'x' * 1000}
                                          for i in range(1000)]
                    remaining = storage.MAX_PACKET_BYTES - len(canonical_utf8(packet))
                    self.assertGreater(remaining, 0)
                    packet['messages'][-1]['text'] += 'x' * remaining
                    self.assertEqual(len(canonical_utf8(packet)), storage.MAX_PACKET_BYTES)
                audit = case.queued(storage, owner, packet=packet)
                key = audit['scope']['packet_id']
                baseline = self.outcome(owner, key)
                before = owner.path.read_bytes()
                with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
                    self.assertEqual(self.outcome(owner, key), baseline)
                    self.assertEqual(self.outcome(owner, key), baseline)
                    self.assertEqual(content.call_count, 1)
                self.assertEqual(owner.path.read_bytes(), before)

    def test_differential_bad_message_source_run_and_scope(self):
        for field in ('message', 'source_run', 'scope'):
            with self.subTest(field=field):
                _, owner, audit, packet = self.stored(source_run=True)
                key = audit['scope']['packet_id']
                path = owner._object_path('packet', key)
                raw = path.read_bytes()
                bad = deepcopy(packet)
                if field == 'message':
                    bad['messages'][0]['id'] = -1
                elif field == 'source_run':
                    bad['source_run']['session_id'] = 2 ** 63
                else:
                    bad['scope_kind'] = 'unrecognized'
                damaged = canonical_utf8(bad)
                path.write_bytes(damaged)
                baseline = self.outcome(owner, key)
                self.assertEqual(baseline[0], storage.ArtifactUnavailable)
                path.write_bytes(raw)
                owner._object_errors.clear()
                with self.scope(owner):
                    owner.get_packet(key)
                    path.write_bytes(damaged)
                    self.assertEqual(self.outcome(owner, key), baseline)

    def test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count(self):
        case = self.fixture()
        _, owner = case.owner()
        large, small = case.packet(), case.packet()
        large['messages'][0]['text'] = 'L' * 3000
        small['messages'][0]['text'] = 's'
        a = owner.put_packet(uuid.uuid4().hex, large)
        b = owner.put_packet(uuid.uuid4().hex, small)
        # Test-only change AFTER first valid capture isolates the otherwise
        # redundant aggregate bound: two legal packets at fixed MAX cannot
        # exceed2*MAX. No production budget/timing fixture is changed.
        reduced = a['byte_length'] // 3
        self.assertLess(b['byte_length'], reduced)
        self.assertGreater(a['byte_length'] + b['byte_length'], 2 * reduced)
        with self.scope(owner):
            owner.get_packet(a['packet_id'])
            with patch.object(storage, 'MAX_PACKET_BYTES', reduced), \
                    patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
                owner.get_packet(b['packet_id'])
                owner.get_packet(b['packet_id'])
                self.assertEqual(content.call_count, 2)
                self.assertNotIn(b['packet_id'], self.state().entries)
                self.assertEqual(len(self.state().entries), 1)

    def test_different_root_does_not_share_evidence(self):
        case, owner, audit, packet = self.stored()
        _, other = case.owner('other-root')
        other.put_packet(audit['request_id'], packet)
        key = audit['scope']['packet_id']
        with self.scope(owner), patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            owner.get_packet(key)
            other.get_packet(key)
            owner.get_packet(key)
            self.assertEqual(content.call_count, 2)

    def test_admit_reject_and_standalone_brief_selected_entries(self):
        for entry in ('admit', 'reject', 'brief'):
            with self.subTest(entry=entry):
                case = self.fixture(managed=True)
                instance = case.instance
                if entry == 'reject':
                    instance, _, _ = case.launch_binding('api')
                audit = case.prepare(instance=instance)
                consumer = case.claim(audit, instance)
                if entry == 'admit':
                    case.authority.get_brief(audit['brief_id'], instance)
                sealed = case.sealed_fixture_record(audit, consumer)
                with patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
                    if entry == 'admit':
                        self.assertEqual(case.authority.admit_saved(sealed, instance)['status'], 'admitted')
                    elif entry == 'reject':
                        self.assertTrue(case.authority.reject_response(audit['brief_id'], 'invalid response', instance)['request_terminal'])
                    else:
                        self.assertEqual(case.authority.get_brief(audit['brief_id'], instance)['brief']['request_id'], audit['request_id'])
                    self.assertEqual(content.call_count, 1)
                self.assertIsNone(self.state())

    def test_recovery_public_items_have_fresh_invocation_scopes(self):
        case = self.fixture(managed=True)
        audits = [case.prepare(), case.prepare(channel='peer')]
        for audit in audits:
            case.artifacts.set_attempt_state(audit['request_id'], audit['attempt_id'], 'queued',
                {'state': 'queued', 'reason': 'resume_pending'})
        seen = {}
        original = case.artifacts._read_validated_packet_content
        def observe(packet_id, *args, **kwargs):
            self.assertIsNotNone(self.state())
            seen.setdefault(packet_id, set()).add(self.state().token)
            return original(packet_id, *args, **kwargs)
        with patch.object(case.artifacts, '_read_validated_packet_content', side_effect=observe), \
                patch.object(storage, '_packet_scope', wraps=storage._packet_scope) as content:
            result = case.authority.recover_startup()
            self.assertEqual(set(result['enqueue_repaired']), {a['request_id'] for a in audits})
            self.assertEqual(content.call_count, 2)
        tokens = [next(iter(values)) for values in seen.values()]
        self.assertEqual(len(tokens), 2)
        self.assertIsNot(tokens[0], tokens[1])
        self.assertIsNone(self.state())

    def test_parent_refusal_and_between_read_packet_damage_keep_service_semantics(self):
        for damaged_read in (1, 2):
            with self.subTest(damaged_read=damaged_read):
                case = self.fixture(managed=True)
                audit = case.prepare()
                case.claim(audit)
                key = audit['scope']['packet_id']
                path = case.artifacts._object_path('packet', key)
                original = case.artifacts._read_object
                reads = []
                def read(kind, identifier, maximum):
                    if kind == 'packet' and identifier == key:
                        reads.append(identifier)
                        if len(reads) == damaged_read:
                            packet = json.loads(path.read_bytes())
                            before = path.stat()
                            text = packet['messages'][0]['text']
                            packet['messages'][0]['text'] = 'Z' + text[1:]
                            raw = canonical_utf8(packet)
                            self.assertEqual(len(raw), before.st_size)
                            path.write_bytes(raw)
                            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                    return original(kind, identifier, maximum)
                with patch.object(case.artifacts, '_read_object', side_effect=read):
                    result = self.mcp_context(case, audit)
                self.assertEqual(result['code'], 'artifact_storage_unavailable')
                row = case.artifacts.get_request(audit['request_id'])
                self.assertEqual(row['state'], 'queued' if damaged_read == 1 else 'failed')
                self.assertEqual(row['reason'], 'queued' if damaged_read == 1 else 'source_packet_unavailable')
                self.assertEqual(len(reads), damaged_read)
                self.assertEqual(case.artifacts.list_versions(audit['lineage_id'])['count'], 0)
                self.assertIsNone(self.state())


if __name__ == '__main__':
    unittest.main()
