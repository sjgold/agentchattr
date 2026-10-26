"""R2 root reds. Real owned temp storage; no provider/native/activation claims.

Missing independent-owner APIs are infrastructure reds, not isolation proof.
Assertions after a new expected refusal are unobserved-red postconditions until
the green run reaches them. Existing fixture tests are aliased, not inherited.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

import artifact_store as module
from tests import test_artifact_store as fixture


class ArtifactDiagnosticOwnerTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(lambda: self.assertFalse(self.root.exists()))
        fixture.ArtifactStoreTests.setUp(self)

    owner = fixture.ArtifactStoreTests.owner
    packet = fixture.ArtifactStoreTests.packet
    audit = fixture.ArtifactStoreTests.audit
    queued = fixture.ArtifactStoreTests.queued
    commit = fixture.ArtifactStoreTests.commit

    @staticmethod
    def empty_ledger():
        return {'version': 1, 'diagnostics': {}, 'dispatch_overflow': {}, 'store_overflow': None}

    @staticmethod
    def detail(dispatch, ordinal, *, attached=None):
        key = {'request_id': attached, 'attempt_id': f'{ordinal + 1:032x}',
               'dispatch_id': dispatch, 'reason': 'invalid_content',
               'sha256': hashlib.sha256(b'').hexdigest(), 'byte_count': 0,
               'actor_identity_id': None}
        canonical = json.dumps(key, ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False)
        identifier = uuid.uuid5(uuid.NAMESPACE_URL, canonical).hex
        return {'id': identifier, 'kind': 'quarantine', **key, 'received_at': 1,
                'updated_at': 1, 'not_retained': True, 'body_object_id': None,
                'attached_request_id': attached}

    def record(self, store, text='diagnostic', *, request=None, attempt=None, dispatch=None, now=10):
        return store.quarantine_submission(request, attempt or uuid.uuid4().hex,
            dispatch or uuid.uuid4().hex, reason='invalid_content', content=text, now=now)

    def test_diagnostic_only_write_does_not_create_authoring_index(self):
        _, store = self.owner('diagnostic-only')
        self.assertFalse(store.path.exists())
        result = self.record(store, 'Exact caf\u00e9\r\nbody')
        self.assertFalse(store.path.exists(), 'A diagnostic must not create an authoring index.')
        # Not reached on the old writer; required green postconditions.
        path = store.root / 'artifacts' / 'diagnostics.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(set(data), set(self.empty_ledger()))
        self.assertIn(result['id'], data['diagnostics'])
        self.assertEqual(data['diagnostics'][result['id']]['attached_request_id'], None)
        self.assertEqual((store.root / 'artifacts' / 'quarantine' /
                          (result['id'] + '.txt')).read_bytes(), 'Exact caf\u00e9\r\nbody'.encode('utf-8'))

    def test_diagnostic_detail_and_overflow_do_not_change_authoring_index_bytes(self):
        _, store = self.owner()
        audit = self.queued(module, store)
        before = store.path.read_bytes()
        before_request = store.get_request(audit['request_id'])
        for ordinal in range(9):
            result = self.record(store, f'unique-{ordinal}', request=audit['request_id'],
                                 attempt=audit['attempt_id'], dispatch=audit['dispatch_id'], now=20 + ordinal)
            with self.subTest(record=ordinal, kind=result['kind']):
                self.assertEqual(store.path.read_bytes(), before)
                self.assertEqual(store.get_request(audit['request_id']), before_request)
        # Unobserved-red postconditions: eight details and one summary persist
        # independently; no weakening of the existing budgets.
        path = store.root / 'artifacts' / 'diagnostics.json'
        self.assertTrue(path.exists(), 'Independent diagnostic metadata must be persisted.')
        data = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(len(data['diagnostics']), 8)
        self.assertEqual(data['dispatch_overflow'][audit['dispatch_id']]['counter'], 1)

    def test_diagnostic_corruption_does_not_block_authoring_or_version_admission(self):
        _, store = self.owner()
        audit = self.queued(module, store)
        before = store.path.read_bytes()
        path = store.root / 'artifacts' / 'diagnostics.json'
        path.write_bytes(b'BROKEN_DIAGNOSTIC_JSON')
        with self.assertRaises(module.ArtifactUnavailable):
            self.record(store, request=audit['request_id'], attempt=audit['attempt_id'],
                        dispatch=audit['dispatch_id'])
        # Unobserved-red on the old writer: verify once green.
        self.assertEqual(store.path.read_bytes(), before)
        version = self.commit(store, audit, '# valid despite held diagnostics')
        self.assertEqual(store.get_version(version['id'])['markdown'], '# valid despite held diagnostics')
        self.assertEqual(path.read_bytes(), b'BROKEN_DIAGNOSTIC_JSON')
        self.assertFalse(store.diagnostics()['owners']['diagnostics']['available'])
        self.assertTrue(store.diagnostics()['owners']['authoring']['available'])

    def test_cap_depth_bom_duplicate_and_invalid_ledgers_refuse_before_body_put(self):
        empty = json.dumps(self.empty_ledger()).encode('utf-8')
        invalid = {
            'cap': b' ' * (1048577 - len(empty)) + empty,
            'bom': b'\xef\xbb\xbf' + empty,
            'duplicate': b'{"version":1,"version":1,"diagnostics":{},"dispatch_overflow":{},"store_overflow":null}',
            'depth': b'{"version":1,"diagnostics":{"x":{"x":{"x":1}}},"dispatch_overflow":{},"store_overflow":null}',
            'nonfinite': b'{"version":NaN,"diagnostics":{},"dispatch_overflow":{},"store_overflow":null}',
            'version': json.dumps({**self.empty_ledger(), 'version': True}).encode('utf-8'),
            'extra_key': json.dumps({**self.empty_ledger(), 'unknown': 1}).encode('utf-8'),
        }
        for name, raw in invalid.items():
            with self.subTest(case=name):
                _, store = self.owner('invalid-' + name)
                path = store.root / 'artifacts' / 'diagnostics.json'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                with self.assertRaises(module.ArtifactUnavailable):
                    self.record(store, 'must not be stored')
                # Unobserved-red invariants: malformed metadata untouched and
                # no body or authoring index created on refusal.
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(list(path.parent.glob('quarantine/*.txt')), [])
                self.assertFalse(store.path.exists())

    def test_request_diagnostics_is_detached_ordered_and_independent_of_authoring_health(self):
        _, store = self.owner()
        audit = self.queued(module, store)
        later = self.record(store, 'later', request=audit['request_id'], attempt=audit['attempt_id'],
                            dispatch=audit['dispatch_id'], now=30)
        earlier = self.record(store, 'earlier', request=audit['request_id'], attempt=audit['attempt_id'],
                              dispatch=audit['dispatch_id'], now=20)
        store.path.write_bytes(b'BROKEN_AUTHORING_INDEX')
        with self.assertRaises(module.ArtifactUnavailable):
            store.get_request(audit['request_id'])
        projection = store.request_diagnostics(audit['request_id'])  # Infrastructure red until API exists.
        self.assertEqual(projection, {'available': True, 'quarantine_ids': [earlier['id'], later['id']],
                                     'overflow_count': 0, 'error': None})
        projection['quarantine_ids'].clear()
        self.assertEqual(len(store.request_diagnostics(audit['request_id'])['quarantine_ids']), 2)
        self.assertEqual(store.path.read_bytes(), b'BROKEN_AUTHORING_INDEX')

    def test_standalone_diagnostic_bypasses_ordinary_held_authoring(self):
        _, initial = self.owner('held-authoring')
        initial.path.parent.mkdir(parents=True, exist_ok=True)
        initial.path.write_bytes(b'BROKEN_AUTHORING_INDEX')
        held = module.ArtifactStore(initial.root, hold_unreadable=True)
        result = self.record(held, 'independent standalone')
        self.assertEqual(result['kind'], 'quarantine')
        self.assertEqual(initial.path.read_bytes(), b'BROKEN_AUTHORING_INDEX')
        self.assertTrue((held.root / 'artifacts' / 'diagnostics.json').exists())

    def test_legacy_nonempty_holds_both_owners_without_creating_diagnostics(self):
        _, initial = self.owner('legacy-nonempty')
        audit = self.queued(module, initial)
        legacy = json.loads(initial.path.read_text(encoding='utf-8'))
        legacy.update(version=1, diagnostics={}, dispatch_overflow={}, store_overflow=None)
        for row in legacy['requests'].values():
            row['quarantine_ids'] = []
        initial.path.write_text(json.dumps(legacy), encoding='utf-8')
        before = initial.path.read_bytes()
        held = module.ArtifactStore(initial.root, hold_unreadable=True)
        with self.subTest(owner='authoring'):
            with self.assertRaises(module.ArtifactUnavailable) as caught:
                held.get_request(audit['request_id'])
            self.assertEqual(str(caught.exception), 'Saved development artifacts use schema 1. Conversion is required; no files were reset.')
        with self.subTest(owner='diagnostics'):
            with self.assertRaises(module.ArtifactUnavailable):
                self.record(held)
        self.assertEqual(initial.path.read_bytes(), before)
        self.assertFalse((initial.root / 'artifacts' / 'diagnostics.json').exists())

    def test_body_put_error_does_not_hold_diagnostic_owner_or_invent_commit_uncertainty(self):
        _, store = self.owner()
        diagnostics = store.diagnostic_store  # Infrastructure red.
        def failed_body(path, raw):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)  # Completed body may survive a reported put failure.
            raise OSError('PRIVATE_BODY_FAULT')
        with patch.object(diagnostics, '_put_bytes', side_effect=failed_body):
            with self.assertRaises(module.ArtifactUnavailable) as caught:
                self.record(store, 'surviving orphan')
        self.assertEqual(caught.exception.code, 'artifact_diagnostics_unavailable')
        self.assertNotIn('PRIVATE_BODY_FAULT', str(caught.exception))
        self.assertIsNone(diagnostics._held)
        result = self.record(store, 'next write succeeds')
        self.assertEqual(result['kind'], 'quarantine')
        self.assertTrue(any(row['kind'] == 'orphan_quarantine' for row in store.diagnostics()['rows']))
        self.assertFalse(store.path.exists())

    def test_uncertain_metadata_commit_holds_stale_instance_and_restart_recognizes_landed_row(self):
        _, store = self.owner()
        diagnostics = store.diagnostic_store  # Infrastructure red.
        self.record(store, 'baseline')
        stamp = diagnostics._stamp
        original = module.atomic_json
        attempt, dispatch = uuid.uuid4().hex, uuid.uuid4().hex
        def fail_after_replace(path, value):
            original(path, value)
            if Path(path) == diagnostics.path:
                raise OSError('PRIVATE_UNCERTAIN_REPLACE')
        with patch.object(module, 'atomic_json', side_effect=fail_after_replace):
            with self.assertRaises(module.ArtifactUnavailable):
                self.record(store, 'landed despite exception', attempt=attempt, dispatch=dispatch)
        self.assertIsNotNone(diagnostics._held)
        self.assertNotEqual(diagnostics._invalid_stamp, stamp)
        with self.assertRaises(module.ArtifactUnavailable):
            self.record(store, 'stale owner must not overwrite')
        restored = module.ArtifactStore(store.root)
        before = restored.diagnostic_store.path.read_bytes()
        result = self.record(restored, 'landed despite exception', attempt=attempt, dispatch=dispatch)
        self.assertEqual(result['sha256'], hashlib.sha256(b'landed despite exception').hexdigest())
        self.assertEqual(restored.diagnostic_store.path.read_bytes(), before)

    def test_stale_diagnostic_owner_cannot_overwrite_another_owner(self):
        _, store = self.owner()
        diagnostics = store.diagnostic_store  # Infrastructure red.
        self.record(store, 'baseline')
        stale = module.ArtifactStore(store.root)
        self.record(store, 'newer saved record')
        before = diagnostics.path.read_bytes()
        with self.assertRaises(module.ArtifactUnavailable):
            self.record(stale, 'must not overwrite')
        self.assertEqual(diagnostics.path.read_bytes(), before)
        self.assertFalse(store.path.exists())

    def test_existing_8_256_1024_budgets_move_without_lowering_or_widening(self):
        _, store = self.owner()
        diagnostics = store.diagnostic_store  # Infrastructure red, no budget proof yet.
        for groups, per_group, expected in ((1, 8, 'dispatch_overflow'),
                                          (256, 1, 'store_overflow'),
                                          (256, 4, 'store_overflow')):
            with self.subTest(groups=groups, records=groups * per_group):
                _, local = self.owner(f'budget-{groups}-{per_group}')
                ledger = self.empty_ledger()
                for group in range(groups):
                    dispatch = f'{group + 1:032x}'
                    for ordinal in range(per_group):
                        row = self.detail(dispatch, ordinal)
                        ledger['diagnostics'][row['id']] = row
                local.diagnostic_store._persist_diagnostics(ledger)
                selected = '0' * 31 + '1' if groups == 1 else 'f' * 32
                result = self.record(local, 'overflow key', dispatch=selected)
                self.assertEqual(result['kind'], expected)
                report = local.diagnostics()
                self.assertEqual(report['detailed_count'], groups * per_group)
                self.assertEqual(report['dispatch_group_count'], groups)
                self.assertFalse(local.path.exists())

    def test_event_blocked_diagnostic_io_does_not_block_low_level_authoring_settlement(self):
        _, store = self.owner()
        audit = self.queued(module, store)
        diagnostics = store.diagnostic_store  # Infrastructure red, no Event claim yet.
        entered, proceed = threading.Event(), threading.Event()
        original = diagnostics._persist_diagnostics
        def blocked(value):
            entered.set()
            if not proceed.wait(5):
                raise AssertionError('Test did not release diagnostic writer')
            return original(value)
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(diagnostics, '_persist_diagnostics', side_effect=blocked):
            pending = pool.submit(self.record, store, 'blocked diagnostic')
            try:
                self.assertTrue(entered.wait(3))
                settlement = pool.submit(store.set_attempt_state, audit['request_id'], audit['attempt_id'],
                                         'queued', {'state': 'cancelled', 'reason': 'operator_cancelled'})
                self.assertEqual(settlement.result(timeout=2)['state'], 'cancelled')
                self.assertFalse(pending.done())
            finally:
                proceed.set()
            self.assertEqual(pending.result(timeout=3)['kind'], 'quarantine')
        self.assertEqual(store.get_request(audit['request_id'])['state'], 'cancelled')

    def test_request_diagnostics_invalid_id_is_validation_error_not_unknown_request(self):
        _, store = self.owner()
        # Missing method is infrastructure; invalid-id cases must run green.
        request_read = store.request_diagnostics
        for identifier in (None, '', 'g' * 32, 'A' * 32, 'a' * 31):
            with self.subTest(identifier=identifier):
                with self.assertRaises(module.ArtifactValidationError):
                    request_read(identifier)

    def test_authoring_validation_and_persistence_never_read_diagnostics(self):
        _, store = self.owner()
        audit = self.queued(module, store)
        value = json.loads(store.path.read_text(encoding='utf-8'))
        self.assertEqual(set(value), {'version', 'lineages', 'requests', 'versions'})
        # Unobserved-red on old schema: guards apply once the independent frame exists.
        diagnostic_path = store.root / 'artifacts' / 'diagnostics.json'
        original = Path.open
        def no_diagnostics(path, *args, **kwargs):
            if path == diagnostic_path:
                raise AssertionError('Authoring path read diagnostics')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', no_diagnostics):
            store._validate_index(deepcopy(value))
            store.set_attempt_state(audit['request_id'], audit['attempt_id'], 'queued',
                                    {'state': 'cancelled', 'reason': 'operator_cancelled'})
        self.assertEqual(store.get_request(audit['request_id'])['state'], 'cancelled')

    def test_r1_numeric_token_guard_and_atomic_json_encoding_match(self):
        # Existing compatibility guard, not counted as a new behavioral red.
        stamp = 1.2345678901234567e-100
        self.assertEqual(len(json.dumps(stamp, allow_nan=False)), 23)
        self.assertEqual(module._number(stamp), stamp)
        path = self.root / 'encoding-guard.json'
        module.atomic_json(path, {'b': 'caf\u00e9', 'a': stamp})
        self.assertEqual(path.read_bytes(), b'{"b": "caf\\u00e9", "a": 1.2345678901234567e-100}')


if __name__ == '__main__':
    unittest.main()
