"""R2 root reds. Real owned temp storage; no provider/native/activation claims.

Missing independent-owner APIs are infrastructure reds, not isolation proof.
Assertions after a new expected refusal are unobserved-red postconditions until
the green run reaches them. Existing fixture tests are aliased, not inherited.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
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
        self.expect_diagnostic_unavailable(lambda: self.record(store, request=audit['request_id'],
            attempt=audit['attempt_id'], dispatch=audit['dispatch_id']))
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
        tied = self.record(store, 'same timestamp', request=audit['request_id'], attempt=audit['attempt_id'],
                           dispatch=audit['dispatch_id'], now=20)
        store.path.write_bytes(b'BROKEN_AUTHORING_INDEX')
        with self.assertRaises(module.ArtifactUnavailable):
            store.get_request(audit['request_id'])
        projection = store.request_diagnostics(audit['request_id'])  # Infrastructure red until API exists.
        expected_ids = sorted([earlier['id'], tied['id']]) + [later['id']]
        self.assertEqual(projection, {'available': True, 'quarantine_ids': expected_ids,
                                     'overflow_count': 0, 'error': None})
        projection['quarantine_ids'].clear()
        self.assertEqual(store.request_diagnostics(audit['request_id'])['quarantine_ids'], expected_ids)
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
            self.expect_diagnostic_unavailable(lambda: self.record(held))
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
        self.expect_diagnostic_unavailable(lambda: self.record(stale, 'must not overwrite'))
        self.assertEqual(diagnostics.path.read_bytes(), before)
        self.assertFalse(store.path.exists())

    def test_existing_8_256_1024_budgets_move_without_lowering_or_widening(self):
        _, store = self.owner()
        diagnostics = store.diagnostic_store  # Infrastructure red, no budget proof yet.
        for groups, per_group, expected in ((1, 8, 'dispatch_overflow'),
                                          (256, 1, 'store_overflow'),
                                          (128, 8, 'store_overflow')):
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
        self.record(store, 'valid diagnostic file must already exist')
        value = json.loads(store.path.read_text(encoding='utf-8'))
        self.assertEqual(set(value), {'version', 'lineages', 'requests', 'versions'})
        # Unobserved-red on old schema: guards apply once the independent frame exists.
        diagnostic_path = store.root / 'artifacts' / 'diagnostics.json'
        self.assertTrue(diagnostic_path.exists())
        original = Path.open
        def no_diagnostics(path, *args, **kwargs):
            if path == diagnostic_path:
                raise AssertionError('Authoring path read diagnostics')
            return original(path, *args, **kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'open', no_diagnostics))
            for name in ('_load_diagnostics', '_check_diagnostics', '_validate_diagnostics',
                         'request_diagnostics', 'report', 'record', '_persist_diagnostics'):
                stack.enter_context(patch.object(module.ArtifactDiagnosticStore, name,
                    side_effect=AssertionError('Authoring entered diagnostic ' + name)))
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

    def expect_diagnostic_unavailable(self, function):
        with self.assertRaises(module.ArtifactUnavailable) as caught:
            function()
        self.assertIsInstance(caught.exception, module.ArtifactDiagnosticsUnavailable)
        self.assertEqual(caught.exception.code, 'artifact_diagnostics_unavailable')
        self.assertEqual(str(caught.exception), 'Artifact diagnostics are unavailable. Repair the diagnostic metadata before retrying.')

    def test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate(self):
        empty = json.dumps(self.empty_ledger()).encode('utf-8')
        malformed = {
            'cap': b' ' * (1048577 - len(empty)) + empty,
            'bom': b'\xef\xbb\xbf' + empty,
            'duplicate': b'{"version":1,"version":1,"diagnostics":{},"dispatch_overflow":{},"store_overflow":null}',
            'depth': b'{"version":1,"diagnostics":{"x":{"x":{"x":1}}},"dispatch_overflow":{},"store_overflow":null}',
            'nonfinite': b'{"version":Infinity,"diagnostics":{},"dispatch_overflow":{},"store_overflow":null}',
            'extra': json.dumps({**self.empty_ledger(), 'unknown': 1}).encode('utf-8'),
        }
        diagnostic_class = module.ArtifactDiagnosticStore  # Infrastructure until class exists.
        for label, raw in malformed.items():
            for mode in ('cold_raise', 'cold_held', 'stale'):
                with self.subTest(label=label, mode=mode):
                    root = self.root / ('parser-' + label + '-' + mode)
                    path = root / 'artifacts' / 'diagnostics.json'
                    path.parent.mkdir(parents=True)
                    prior = diagnostic_class(root) if mode == 'stale' else None
                    path.write_bytes(raw)
                    if mode == 'cold_raise':
                        self.expect_diagnostic_unavailable(lambda: diagnostic_class(root, hold_unreadable=False))
                    else:
                        owner = prior if prior is not None else diagnostic_class(root, hold_unreadable=True)
                        self.expect_diagnostic_unavailable(lambda: owner.record(None, 'a'*32, 'b'*32,
                            reason='invalid_content', content='no body'))
                    self.assertEqual(path.read_bytes(), raw)
                    self.assertEqual(list(path.parent.glob('quarantine/*.txt')), [])

    def test_record_group_and_global_limits_are_individually_validated_on_cold_load(self):
        diagnostic_class = module.ArtifactDiagnosticStore
        for label, groups, width, extra in (('group_9', 1, 9, False),
                                           ('groups_257', 257, 1, False),
                                           ('records_1025', 128, 8, True)):
            with self.subTest(limit=label):
                root = self.root / label
                ledger = self.empty_ledger()
                for group in range(groups):
                    for ordinal in range(width):
                        row = self.detail(f'{group+1:032x}', ordinal)
                        ledger['diagnostics'][row['id']] = row
                if extra:
                    row = self.detail('f'*32, 0)
                    ledger['diagnostics'][row['id']] = row
                    self.assertEqual(len(ledger['diagnostics']), 1025)
                    self.assertEqual(len({r['dispatch_id'] for r in ledger['diagnostics'].values()}), 129)
                path = root / 'artifacts' / 'diagnostics.json'
                path.parent.mkdir(parents=True)
                raw = json.dumps(ledger).encode('utf-8'); path.write_bytes(raw)
                self.expect_diagnostic_unavailable(lambda: diagnostic_class(root))
                self.assertEqual(path.read_bytes(), raw)

    def test_body_object_total_bytes_and_object_count_limits_are_isolated(self):
        diagnostic_class = module.ArtifactDiagnosticStore
        for label in ('single_object', 'total_bytes', 'object_count'):
            with self.subTest(limit=label):
                root = self.root / ('body-limit-' + label)
                diagnostic_class(root)  # Real owner validation, no fake inventory.
                store = module.ArtifactStore(root)
                folder = root / 'artifacts' / 'quarantine'
                folder.mkdir(parents=True, exist_ok=True)
                if label == 'single_object':
                    retained = self.record(store, 'x' * 524288)
                    self.assertFalse(retained['not_retained'])
                    rejected = self.record(store, 'x' * 524289)
                    self.assertTrue(rejected['not_retained'])
                    self.assertEqual(len(list(folder.glob('*.txt'))), 1)
                elif label == 'total_bytes':
                    #15 objects, well under1024, leave room for exactly512KiB.
                    for index in range(15):
                        (folder / (f'{index+1:032x}' + '.txt')).write_bytes(b'x' * 524288)
                    self.assertFalse(self.record(store, 'y' * 524288)['not_retained'])
                    self.assertTrue(self.record(store, 'one byte too many')['not_retained'])
                    self.assertEqual(sum(p.stat().st_size for p in folder.glob('*.txt')), 8388608)
                else:
                    # Zero-byte orphans isolate count from bytes/per-object caps.
                    for index in range(1023):
                        (folder / (f'{index+1:032x}' + '.txt')).write_bytes(b'')
                    self.assertFalse(self.record(store, '')['not_retained'])
                    self.assertTrue(self.record(store, 'count only')['not_retained'])
                    self.assertEqual(len(list(folder.glob('*.txt'))), 1024)

    def test_authoring_put_bytes_override_still_controls_import_staging(self):
        from tests.test_artifact_imported_store import ArtifactImportedStoreTests
        case = ArtifactImportedStoreTests(); self.addCleanup(case.doCleanups); case.setUp()
        graph, _, _ = case.source_graph(attempts=False)
        before = case.target.path.read_bytes() if case.target.path.exists() else None
        with patch.object(case.target, '_put_bytes', side_effect=OSError('controlled staging fault')) as put:
            with self.assertRaises(module.ArtifactUnavailable):
                case.target.prepare_import_lineage(*graph)
        self.assertGreater(put.call_count, 0)
        self.assertEqual(case.target.path.read_bytes() if case.target.path.exists() else None, before)

    def test_owner_fingerprints_use_separate_paths(self):
        _, store = self.owner()
        self.queued(module, store)
        diagnostics = store.diagnostic_store
        self.record(store)
        seen = []; original = Path.stat
        def observed(path, *args, **kwargs):
            if path in (store.path, diagnostics.path): seen.append(path)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'stat', observed):
            store._fingerprint()
            self.assertEqual(seen, [store.path]); seen.clear()
            diagnostics._fingerprint()
            self.assertEqual(seen, [diagnostics.path])

    def test_unattached_details_and_summary_are_not_retroactively_attributed(self):
        _, store = self.owner(); request = uuid.uuid4().hex; ids = module.request_ids(request)
        for index in range(9):
            self.record(store, f'unmatched-{index}', request=request,
                        attempt=ids['attempt_id'], dispatch=ids['dispatch_id'])
        audit = self.audit(module, store, request_id=request)
        store.reserve_request(audit, request)
        self.assertEqual(store.request_diagnostics(request), {'available': True,
            'quarantine_ids': [], 'overflow_count': 0, 'error': None})
        self.assertEqual(next(r for r in store.diagnostics()['rows'] if r['kind']=='dispatch_overflow')['counter'], 1)

    def test_global_overflow_is_never_attributed_to_a_request(self):
        _, store = self.owner(); owner = store.diagnostic_store
        audit = self.queued(module, store)
        ledger = self.empty_ledger()
        for group in range(128):
            for ordinal in range(8):
                row = self.detail(f'{group+1:032x}', ordinal)
                ledger['diagnostics'][row['id']] = row
        owner._persist_diagnostics(ledger)
        self.assertEqual(self.record(store, request=audit['request_id'], attempt=audit['attempt_id'],
            dispatch=audit['dispatch_id'])['kind'], 'store_overflow')
        self.assertEqual(store.request_diagnostics(audit['request_id'])['overflow_count'], 0)

    def test_legacy_markers_preserve_guidance_across_constructor_check_and_persist(self):
        _, store = self.owner(); audit = self.queued(module, store)
        current = store.path.read_bytes()
        legacy = json.loads(current); legacy.update(version=1, diagnostics={}, dispatch_overflow={}, store_overflow=None)
        for row in legacy['requests'].values(): row['quarantine_ids']=[]
        store.path.write_text(json.dumps(legacy), encoding='utf-8')
        held = module.ArtifactStore(store.root, hold_unreadable=True)
        guidance='Saved development artifacts use schema 1. Conversion is required; no files were reset.'
        for action in (lambda: held.get_request(audit['request_id']),
                       lambda: held.set_attempt_state(audit['request_id'], audit['attempt_id'], 'queued',
                           {'state':'cancelled','reason':'operator_cancelled'})):
            with self.subTest(action=action):
                with self.assertRaises(module.ArtifactUnavailable) as caught: action()
                self.assertIs(type(caught.exception), module.ArtifactUnavailable)
                self.assertEqual(str(caught.exception), guidance)
        store.path.write_bytes(current)
        with self.assertRaises(module.ArtifactUnavailable) as caught: held.get_request(audit['request_id'])
        self.assertEqual(str(caught.exception), guidance)
        self.expect_diagnostic_unavailable(lambda: self.record(held))
        self.assertFalse((store.path.parent/'diagnostics.json').exists())

    def test_empty_v1_normalizes_in_memory_but_mixed_v2_is_held_without_reset(self):
        old={'version':1,'lineages':{},'requests':{},'versions':{},'diagnostics':{},'dispatch_overflow':{},'store_overflow':None}
        for mode in ('empty_v1','mixed_v2'):
            with self.subTest(mode=mode):
                root=self.root/mode; path=root/'artifacts'/'index.json';path.parent.mkdir(parents=True)
                value=old if mode=='empty_v1' else {**old,'version':2}
                raw=json.dumps(value).encode('utf-8');path.write_bytes(raw)
                owner=module.ArtifactStore(root,hold_unreadable=True)
                if mode=='mixed_v2':
                    with self.assertRaises(module.ArtifactUnavailable): owner.list_lineages()
                else:
                    self.assertEqual(owner.list_lineages()['count'],0)
                    self.assertEqual(owner._data,{'version':2,'lineages':{},'requests':{},'versions':{}})
                self.assertEqual(path.read_bytes(),raw)
                self.assertFalse((path.parent/'diagnostics.json').exists())

    def test_same_instance_uncertainty_recovers_only_the_previous_known_snapshot(self):
        _, store=self.owner();owner=store.diagnostic_store;self.record(store,'known')
        before=owner.path.read_bytes()
        with patch.object(module,'atomic_json',side_effect=OSError('before metadata replace')):
            self.expect_diagnostic_unavailable(lambda:self.record(store,'not landed'))
        self.assertEqual(owner.path.read_bytes(),before)
        self.assertIsNotNone(owner._held)
        self.assertEqual(self.record(store,'later valid')['kind'],'quarantine')
        self.assertIsNone(owner._held)

    def test_combined_report_partial_rows_limits_and_owner_errors_are_exact(self):
        _, store=self.owner();audit=self.queued(module,store)
        result=self.record(store,'known attached',request=audit['request_id'],attempt=audit['attempt_id'],dispatch=audit['dispatch_id'])
        store.path.write_bytes(b'bad authoring')
        with self.assertRaises(module.ArtifactUnavailable):store.get_request(audit['request_id'])
        report=store.diagnostics(limit=1)
        self.assertEqual(report['owners'],{'authoring':{'available':False,'reason':'authoring_unavailable'},
            'diagnostics':{'available':True,'reason':None}})
        self.assertIsNone(report['count']);self.assertTrue(report['partial']);self.assertTrue(report['truncated'])
        self.assertEqual(len(report['rows']),1);self.assertEqual(report['rows'][0]['id'],result['id'])
        self.assertEqual(report['retained_body_bytes'],len(b'known attached'))
        self.assertEqual(report['errors']['authoring'],{'code':'artifact_storage_unavailable',
            'error':'Saved artifact index is held; repair storage and restart.'})
        self.assertIsNone(report['errors']['diagnostics'])
        for limit in (0,101,True):
            with self.assertRaises(module.ArtifactValidationError):store.diagnostics(limit=limit)
        (store.path.parent/'diagnostics.json').write_bytes(b'bad diagnostic')
        report=store.diagnostics(limit=1)
        self.assertEqual(report['rows'],[]);self.assertIsNone(report['retained_body_bytes'])
        self.assertIsNone(report['count']);self.assertFalse(report['owners']['diagnostics']['available'])

    def test_snapshot_and_none_marker_read_do_no_authoring_io_or_nested_owner_lock(self):
        _, store=self.owner();audit=self.queued(module,store);owner=store.diagnostic_store
        original=owner.record
        def observed(*args,**kwargs):
            self.assertFalse(store._lock._is_owned())
            return original(*args,**kwargs)
        def no_open(*args,**kwargs):raise AssertionError('snapshot did IO')
        with patch.object(Path,'open',no_open),patch.object(Path,'stat',no_open):
            self.assertEqual(store._snapshot_diagnostic_attachment(audit['request_id'],audit['dispatch_id']),audit['request_id'])
            store._check_diagnostic_legacy()
        with patch.object(owner,'record',side_effect=observed):self.record(store)

    def test_concurrent_same_diagnostic_id_has_one_body_row_and_stable_receipt(self):
        _,store=self.owner();owner=store.diagnostic_store;attempt=uuid.uuid4().hex;dispatch=uuid.uuid4().hex
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.record(store,'same',attempt=attempt,dispatch=dispatch),range(2)))
        self.assertEqual(results[0],results[1]);self.assertEqual(store.diagnostics()['detailed_count'],1)
        self.assertEqual(len(list((store.path.parent/'quarantine').glob('*.txt'))),1)
        self.assertFalse(store.path.exists());self.assertTrue(owner.path.exists())

    @staticmethod
    def maximum_ledger():
        stamp=1.2345678901234567e-100
        value={'version':1,'diagnostics':{},'dispatch_overflow':{},'store_overflow':None}
        for group in range(256):
            request=f'{group+1:032x}';dispatch=module.request_ids(request)['dispatch_id']
            for ordinal in range(4):
                key={'request_id':request,'attempt_id':f'{group*4+ordinal+1:032x}',
                    'dispatch_id':dispatch,'reason':'source_packet_unavailable','sha256':'c'*64,
                    'byte_count':2**63-1,'actor_identity_id':'a'*32}
                text=json.dumps(key,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
                identifier=uuid.uuid5(uuid.NAMESPACE_URL,text).hex
                value['diagnostics'][identifier]={'id':identifier,'kind':'quarantine',**key,
                    'received_at':stamp,'updated_at':stamp,'not_retained':False,'body_object_id':identifier,
                    'attached_request_id':request}
            identifier=uuid.uuid5(uuid.NAMESPACE_URL,'agentchattr:artifact-v1:overflow:'+dispatch).hex
            value['dispatch_overflow'][dispatch]={'id':identifier,'kind':'dispatch_overflow','dispatch_id':dispatch,
                'counter':2**31-1,'latest_diagnostic_id':'b'*32,'latest_sha256':'c'*64,'latest_byte_count':2**63-1,
                'latest_reason':'source_packet_unavailable','updated_at':stamp}
        value['store_overflow']={'id':uuid.uuid5(uuid.NAMESPACE_URL,'agentchattr:artifact-v1:overflow:store').hex,
            'kind':'store_overflow','dispatch_id':None,'counter':2**31-1,'latest_diagnostic_id':'b'*32,
            'latest_sha256':'c'*64,'latest_byte_count':2**63-1,'latest_reason':'source_packet_unavailable','updated_at':stamp}
        return value

    def test_structural_maximum_frame_golden_validates_attached_derivation_and_encoding(self):
        value=self.maximum_ledger();raw=json.dumps(value,ensure_ascii=True,allow_nan=False).encode('utf-8')
        self.assertEqual(len(raw),810186)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'ca2cead533284a9c9165be1f5912e57f994a1a6cec9d4645e21beed290db34c1')
        self.assertEqual(len(value['diagnostics']),1024)
        self.assertEqual(len(value['dispatch_overflow']),256)
        self.assertTrue(all(len(reason)<=len('source_packet_unavailable') for reason in module.QUARANTINE_REASONS))
        self.assertEqual(len(json.dumps(1.2345678901234567e-100)),23)
        # Profile size guard above runs pre-change; independent R2 validation
        # below is infrastructure-red, not a claimed all-encoding maximum proof.
        owner=module.ArtifactDiagnosticStore(self.root/'max-profile')
        owner._validate_diagnostics(value)
        owner._persist_diagnostics(value)
        self.assertEqual(owner.path.read_bytes(),raw)
        for row in value['diagnostics'].values():
            self.assertEqual(module.request_ids(row['attached_request_id'])['dispatch_id'],row['dispatch_id'])

    def test_nonnull_request_held_authoring_is_authoring_error_without_diagnostic_write(self):
        _,store=self.owner();audit=self.queued(module,store)
        store.path.write_bytes(b'BROKEN_AUTHORING')
        with self.assertRaises(module.ArtifactUnavailable):store.get_request(audit['request_id'])
        with self.assertRaises(module.ArtifactUnavailable) as caught:
            self.record(store,request=audit['request_id'],attempt=audit['attempt_id'],dispatch=audit['dispatch_id'])
        self.assertIs(type(caught.exception),module.ArtifactUnavailable)
        self.assertEqual(str(caught.exception),'Saved artifact index is held; repair storage and restart.')
        self.assertEqual(store.path.read_bytes(),b'BROKEN_AUTHORING')
        self.assertFalse((store.path.parent/'diagnostics.json').exists())
        self.assertEqual(list(store.path.parent.glob('quarantine/*.txt')),[])


if __name__ == '__main__':
    unittest.main()
