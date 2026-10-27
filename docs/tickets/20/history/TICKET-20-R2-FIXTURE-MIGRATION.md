# Ticket 20: R2 fixture migration before N additions and D4 reds

Status: builder mechanical test migration VERIFIED on codex/ticket-20-r2-on-a1. Production/tool bytes unchanged from accepted merge/design pin8580c34. Reviewer confirmed D4 direction and authorized this migration FIRST; no N additions or D4 reds/source are in this commit.

## Assertion ownership and preserved intent

|File / old site|Before|After and invariant|
|---|---|---|
|record_bounds322-337|Diagnostic detail seeds copied from authoring _data and passed to _validate_index; summary validator on authoring owner|Copy diagnostic_store._data; use diagnostic _validate_diagnostics/_validate_summary. Preserve >2**63-1 refusal, rederived id, identical scalar values and exception class. Authoring integer/sequence checks unchanged.|
|record_bounds691-706|One combined authoring frame validates max numeric fields including diagnostics|Keep authoring max-row validator AND validate detached diagnostic frame on its owner. Preserve all2**63-1 positives, real ids/summary and991296B golden unchanged.|
|store403/410/505|Request debug quarantine_ids read through get_request|Same membership/list equality and real id through request_diagnostics. State/audit comparisons remain authoring reads.|
|store444|Request debug overflow_count3 for a dispatch with ONLY unattached details|Preserve dispatch summary counter3 through combined diagnostics report. Explicitly assert request_diagnostics overflow_count0 because no detail attaches; this intentional R2 attribution change was frozen in the contract. No expected3 assertion deleted.|
|parent67; export_store142|Empty attached-id list on request row|Same empty list through request_diagnostics. No parent/read-only behavior weakened.|
|export_store40|Construct imported row with quarantine_ids=[]|Real v2 rows omit the field; assert absence before import-source conversion, remove extra obsolete key only. No state/reason semantics tightened.|
|export_store149-152; store_review hash-only dedupe|Authoring bytes unchanged after diagnostic replay, now trivially true alone|Keep authoring-byte assertion and ALSO assert diagnostic-owner bytes unchanged, so diagnostic dedupe is still tested.|
|store_integrity133|All diagnostics refuse with held authoring, including request_id=None|Non-null request attachment still refuses; standalone None now succeeds with no attachment. Preserve held index bytes and all other held-authoring read/mutation refusals. This independent-owner exception was frozen.|
|oversize35/38/56-66; store_review81-93; saturation33-57|Diagnostic-only fixture read/write/snapshot uses index.json|Same generated payload/counters/ids/budgets/replay comparisons on diagnostic_store.path. Fresh ArtifactStore loads its diagnostic owner and validates same seed. No limit patch or expected counter changed.|

## Complete move-list audit

The all-artifact module selection covers every named site, including unchanged assertions. These sites remain unchanged by design: store_integrity53 object-corruption observation; admission277 diagnostic report; recovery169/266; workers336; staging_receipt77; import_stage_review219; imported_store168; export_store remaining report counts/body/orphan checks. They already read combined reports or immutable receipts, not removed request fields. The table above records every edited assertion/access.

Portable source fixtures artifact_portable_projection.json78 and artifact_portable_revision_projection.json80/149/214 deliberately retain quarantine_ids as ignored unknown source keys, as explicitly frozen in the R2 contract. Their literal expected portable output/goldens stay unchanged; export_store.imported_index now asserts actual v2 source rows omit the key. Authoring-only fixtures in record_bounds501/631 and store513 derive current saved index bytes, so they already build schema2 without editing literal versions. Empty/mixed-v1 tests intentionally exercise legacy input and remain version1.

## Exact before/after test diff

All changed assertions and fixture seed accesses follow. No production/tool or literal golden file changed.

```diff
diff --git a/tests/test_artifact_diagnostic_oversize.py b/tests/test_artifact_diagnostic_oversize.py
index 6265c00..35b0807 100644
--- a/tests/test_artifact_diagnostic_oversize.py
+++ b/tests/test_artifact_diagnostic_oversize.py
@@ -32,10 +32,10 @@ class ArtifactOversizeDiagnosticTests(unittest.TestCase):
         self.assertIsNone(second['body_object_id'])
         self.assertEqual(second['byte_count'], 0)
         self.assertEqual(second['sha256'], hashlib.sha256(b'').hexdigest())
-        before = store.path.read_bytes()
+        before = store.diagnostic_store.path.read_bytes()
         self.assertEqual(store.quarantine_submission(*args, reason='invalid_content', content='',
             actor_identity_id='4' * 32, now=999), first)
-        self.assertEqual(store.path.read_bytes(), before)
+        self.assertEqual(store.diagnostic_store.path.read_bytes(), before)
         self.assertEqual(body.read_bytes(), b'')
 
     def test_oversize_reason_uses_existing_group_and_global_overflow_bounds(self):
@@ -52,7 +52,7 @@ class ArtifactOversizeDiagnosticTests(unittest.TestCase):
                     expected_kind, expected_count, expected_groups = 'dispatch_overflow', 8, 1
                 else:
                     # Strict-loadable metadata-only fixture at REAL limits, no cap patches.
-                    value = json.loads(store.path.read_text(encoding='utf-8'))
+                    value = json.loads(store.diagnostic_store.path.read_text(encoding='utf-8'))
                     value['diagnostics'] = {}
                     for _ in range(256):
                         group = uuid.uuid4().hex
@@ -63,7 +63,7 @@ class ArtifactOversizeDiagnosticTests(unittest.TestCase):
                                 'reason', 'sha256', 'byte_count', 'actor_identity_id')}
                             detail['id'] = uuid.uuid5(uuid.NAMESPACE_URL, canonical_utf8(key).decode('utf-8')).hex
                             value['diagnostics'][detail['id']] = detail
-                    store.path.write_text(json.dumps(value), encoding='utf-8')
+                    store.diagnostic_store.path.write_text(json.dumps(value), encoding='utf-8')
                     store = ArtifactStore(store.root)
                     dispatch = uuid.uuid4().hex
                     expected_kind = 'store_overflow'
diff --git a/tests/test_artifact_export_store.py b/tests/test_artifact_export_store.py
index 9729d23..6e5d79c 100644
--- a/tests/test_artifact_export_store.py
+++ b/tests/test_artifact_export_store.py
@@ -37,7 +37,8 @@ class ArtifactExportStoreTests(unittest.TestCase):
         for row in index['requests'].values():
             row['import_source'] = {'archive_id': 'archive-fixture',
                 'original_state': row['state'], 'original_reason': row['reason']}
-            row.update(state='imported', reason='imported', quarantine_ids=[])
+            self.assertNotIn('quarantine_ids', row)  # Real v2 source row, not portable allowlist input.
+            row.update(state='imported', reason='imported')
             producer = row['audit']['producer']
             producer.update(adapter='openai-compatible', launch_attempt=None,
                 launch_nonce=None, fingerprint=None, capabilities=[])
@@ -139,7 +140,7 @@ class ArtifactExportStoreTests(unittest.TestCase):
                 reason='superseded', content='late-' + str(position), actor_identity_id='a'*32)
         self.assertEqual(target.export_metadata(audit['lineage_id']), before)
         self.assertEqual(target.get_request(audit['request_id']), public_before)
-        self.assertEqual(target.get_request(audit['request_id'])['quarantine_ids'], [])
+        self.assertEqual(target.request_diagnostics(audit['request_id'])['quarantine_ids'], [])
         diagnostics = target.diagnostics()
         self.assertEqual(diagnostics['detailed_count'], 8)
         self.assertEqual(diagnostics['retained_body_bytes'], 8 * len(b'late-0'))
@@ -147,9 +148,11 @@ class ArtifactExportStoreTests(unittest.TestCase):
         summary = next(row for row in diagnostics['rows'] if row['kind'] == 'dispatch_overflow')
         self.assertEqual(summary['counter'], 2)
         before_bytes = target.path.read_bytes()
+        diagnostic_bytes = target.diagnostic_store.path.read_bytes()
         target.quarantine_submission(audit['request_id'], audit['attempt_id'], audit['dispatch_id'],
             reason='superseded', content='late-0', actor_identity_id='a'*32)
         self.assertEqual(target.path.read_bytes(), before_bytes)
+        self.assertEqual(target.diagnostic_store.path.read_bytes(), diagnostic_bytes)
         for item in (audit, second):
             with self.assertRaises(module.ArtifactConflict):
                 target.commit_version(item['request_id'], item['attempt_id'], item['dispatch_id'], '# Refused',
diff --git a/tests/test_artifact_parent.py b/tests/test_artifact_parent.py
index 0f2ae22..957d392 100644
--- a/tests/test_artifact_parent.py
+++ b/tests/test_artifact_parent.py
@@ -64,7 +64,7 @@ class ArtifactParentTests(unittest.TestCase):
             case.authority.get_parent(revision['brief_id'], case.instance)
         self.assertEqual(case.files(), before)
         self.assertEqual(case.artifacts.get_request(revision['request_id'])['state'], 'queued')
-        self.assertEqual(case.artifacts.get_request(revision['request_id'])['quarantine_ids'], [])
+        self.assertEqual(case.artifacts.request_diagnostics(revision['request_id'])['quarantine_ids'], [])
 
     def test_api_no_body_rejection_and_strict_report_shapes_never_grant_cli_authority(self):
         case = self.context()
diff --git a/tests/test_artifact_record_bounds.py b/tests/test_artifact_record_bounds.py
index de66467..75ecf79 100644
--- a/tests/test_artifact_record_bounds.py
+++ b/tests/test_artifact_record_bounds.py
@@ -318,7 +318,7 @@ class ArtifactRecordBoundsTests(unittest.TestCase):
         with self.subTest(record_field='version.sequence_direct_row'):
             with self.assertRaises(store.ArtifactValidationError):
                 self.source._validate_version(metadata, original['requests'])
-        changed = deepcopy(original)
+        changed = deepcopy(self.source.diagnostic_store._data)
         diagnostic = next(iter(changed['diagnostics'].values()))
         diagnostic['byte_count'] = 2**63
         key = {name: diagnostic[name] for name in ('request_id', 'attempt_id', 'dispatch_id',
@@ -327,24 +327,24 @@ class ArtifactRecordBoundsTests(unittest.TestCase):
         changed['diagnostics'] = {diagnostic['id']: diagnostic}
         with self.subTest(index_field='diagnostic.byte_count'):
             with self.assertRaises(store.ArtifactValidationError):
-                self.source._validate_index(changed)
-        changed = deepcopy(original)
+                self.source.diagnostic_store._validate_diagnostics(changed)
+        changed = deepcopy(self.source.diagnostic_store._data)
         diagnostic = next(iter(changed['diagnostics'].values()))
         diagnostic.update(received_at=2**63, updated_at=2**63)
         with self.subTest(index_field='diagnostic.received_at/updated_at'):
             with self.assertRaises(store.ArtifactValidationError):
-                self.source._validate_index(changed)
+                self.source.diagnostic_store._validate_diagnostics(changed)
         summary = {'id': self.source._summary_id(None), 'kind': 'store_overflow',
             'dispatch_id': None, 'counter': 1, 'latest_diagnostic_id': 'd' * 32,
             'latest_sha256': 'e' * 64, 'latest_byte_count': 2**63,
             'latest_reason': 'invalid_response', 'updated_at': 10}
         with self.subTest(index_field='overflow.latest_byte_count'):
             with self.assertRaises(store.ArtifactValidationError):
-                self.source._validate_summary(summary, None)
+                self.source.diagnostic_store._validate_summary(summary, None)
         summary.update(latest_byte_count=0, updated_at=2**63)
         with self.subTest(index_field='overflow.updated_at'):
             with self.assertRaises(store.ArtifactValidationError):
-                self.source._validate_summary(summary, None)
+                self.source.diagnostic_store._validate_summary(summary, None)
         with self.subTest(record_field='timestamp_helper'):
             with self.assertRaises(store.ArtifactValidationError):
                 store._number(2**63)
@@ -693,17 +693,19 @@ class ArtifactRecordBoundsTests(unittest.TestCase):
         value['lineages'][audit['lineage_id']]['updated_at'] = 2**63-1
         version_id = store.request_ids(audit['request_id'])['version_id']
         value['versions'][version_id]['created_at'] = 2**63-1
-        diagnostic = next(iter(value['diagnostics'].values()))
+        diagnostic_value = deepcopy(self.source.diagnostic_store._data)
+        diagnostic = next(iter(diagnostic_value['diagnostics'].values()))
         diagnostic.update(byte_count=2**63-1, received_at=2**63-1, updated_at=2**63-1)
         key = {name: diagnostic[name] for name in ('request_id', 'attempt_id', 'dispatch_id',
             'reason', 'sha256', 'byte_count', 'actor_identity_id')}
         diagnostic['id'] = self.source._diagnostic_id(key)
-        value['diagnostics'] = {diagnostic['id']: diagnostic}
-        value['store_overflow'] = {'id': self.source._summary_id(None), 'kind': 'store_overflow',
+        diagnostic_value['diagnostics'] = {diagnostic['id']: diagnostic}
+        diagnostic_value['store_overflow'] = {'id': self.source._summary_id(None), 'kind': 'store_overflow',
             'dispatch_id': None, 'counter': 1, 'latest_diagnostic_id': diagnostic['id'],
             'latest_sha256': diagnostic['sha256'], 'latest_byte_count': 2**63-1,
             'latest_reason': 'invalid_response', 'updated_at': 2**63-1}
         self.source._validate_index(value)
+        self.source.diagnostic_store._validate_diagnostics(diagnostic_value)
 
     def maximum_row(self):
         """Build real persisted data, then validate a detached widest row.
diff --git a/tests/test_artifact_store.py b/tests/test_artifact_store.py
index ffcc440..c20d50e 100644
--- a/tests/test_artifact_store.py
+++ b/tests/test_artifact_store.py
@@ -400,14 +400,14 @@ class ArtifactStoreTests(unittest.TestCase):
         self.assertEqual(store.get_request(audit['request_id']), before)
         mismatch = store.quarantine_submission(audit['request_id'], audit['attempt_id'], uuid.uuid4().hex,
             reason='wrong_dispatch', content='Wrong dispatch', now=101)
-        self.assertNotIn(mismatch['id'], store.get_request(audit['request_id'])['quarantine_ids'])
+        self.assertNotIn(mismatch['id'], store.request_diagnostics(audit['request_id'])['quarantine_ids'])
         wrong_attempt = uuid.uuid4().hex
         detailed = store.quarantine_submission(audit['request_id'], wrong_attempt, audit['dispatch_id'],
             reason='wrong_attempt', content='Exact cafÃ©\r\nbody', actor_identity_id='b' * 32, now=102)
         row = store.get_request(audit['request_id'])
         self.assertEqual(row['state'], before['state'])
         self.assertEqual(row['audit'], before['audit'])
-        self.assertEqual(row['quarantine_ids'], [detailed['id']])
+        self.assertEqual(store.request_diagnostics(audit['request_id'])['quarantine_ids'], [detailed['id']])
         key = {'request_id': audit['request_id'], 'attempt_id': wrong_attempt, 'dispatch_id': audit['dispatch_id'],
             'reason': 'wrong_attempt', 'sha256': hashlib.sha256('Exact cafÃ©\r\nbody'.encode()).hexdigest(),
             'byte_count': len('Exact cafÃ©\r\nbody'.encode()), 'actor_identity_id': 'b' * 32}
@@ -441,7 +441,10 @@ class ArtifactStoreTests(unittest.TestCase):
         self.assertEqual(self.files(store), before)
         self.assertEqual(diagnostic(store, audit['dispatch_id'], 'overflow-B', 201)['counter'], 2)
         self.assertEqual(diagnostic(store, audit['dispatch_id'], 'overflow-A', 202)['counter'], 3)
-        self.assertEqual(store.get_request(audit['request_id'])['overflow_count'], 3)
+        self.assertEqual(next(row for row in store.diagnostics()['rows']
+            if row['kind'] == 'dispatch_overflow' and row['dispatch_id'] == audit['dispatch_id'])['counter'], 3)
+        # These details were deliberately unattached (request_id=None).
+        self.assertEqual(store.request_diagnostics(audit['request_id'])['overflow_count'], 0)
         self.assertEqual(store.get_request(audit['request_id'])['state'], 'queued')
         _, oversized_body = self.owner('oversized-body')
         too_large = 'x' * (512 * 1024 + 1)
@@ -502,7 +505,7 @@ class ArtifactStoreTests(unittest.TestCase):
             store.set_attempt_state(peer['request_id'], peer['attempt_id'], 'queued', {'state': 'active', 'reason': None})
         diagnostic = store.quarantine_submission(peer['request_id'], peer['attempt_id'], peer['dispatch_id'],
             reason='source_packet_unavailable', now=100)
-        self.assertIn(diagnostic['id'], store.get_request(peer['request_id'])['quarantine_ids'])
+        self.assertIn(diagnostic['id'], store.request_diagnostics(peer['request_id'])['quarantine_ids'])
         self.assertEqual(store.set_attempt_state(peer['request_id'], peer['attempt_id'], 'queued',
             {'state': 'failed', 'reason': 'source_packet_unavailable'}, now=101)['state'], 'failed')
         healthy_index = store.path.read_bytes()
diff --git a/tests/test_artifact_store_integrity.py b/tests/test_artifact_store_integrity.py
index 91e43c0..9f53597 100644
--- a/tests/test_artifact_store_integrity.py
+++ b/tests/test_artifact_store_integrity.py
@@ -130,10 +130,14 @@ class ArtifactIndexIntegrityTests(unittest.TestCase):
                 for operation in (held.list_lineages, lambda: held.get_request(r1), lambda: held.get_version(first['id']),
                         lambda: held.set_attempt_state(rp, pending['attempt_id'], 'queued',
                             {'state': 'cancelled', 'reason': 'operator_cancelled'}, now=50),
-                        lambda: held.quarantine_submission(None, uuid.uuid4().hex, uuid.uuid4().hex,
+                        lambda: held.quarantine_submission(r1, uuid.uuid4().hex, uuid.uuid4().hex,
                             reason='unmatched_saved_result', content=None)):
                     with self.assertRaises(module.ArtifactUnavailable):
                         operation()
+                standalone = held.quarantine_submission(None, uuid.uuid4().hex, uuid.uuid4().hex,
+                    reason='unmatched_saved_result', content=None)
+                self.assertEqual(standalone['kind'], 'quarantine')
+                self.assertIsNone(standalone['attached_request_id'])
                 self.assertEqual(store.path.read_bytes(), bad)
 
     def test_valid_index_load_does_not_scan_immutable_bodies(self):
diff --git a/tests/test_artifact_store_review.py b/tests/test_artifact_store_review.py
index f60577a..f20ab1d 100644
--- a/tests/test_artifact_store_review.py
+++ b/tests/test_artifact_store_review.py
@@ -51,9 +51,11 @@ class ArtifactStoreReviewTests(unittest.TestCase):
                 self.assertTrue(row['not_retained'])
                 self.assertIsNone(row['body_object_id'])
                 before = self.store.path.read_bytes()
+                diagnostic_before = self.store.diagnostic_store.path.read_bytes()
                 self.assertEqual(self.store.quarantine_submission(audit['request_id'], audit['attempt_id'],
                     audit['dispatch_id'], reason='invalid_content', content=text, now=999), row)
                 self.assertEqual(self.store.path.read_bytes(), before)
+                self.assertEqual(self.store.diagnostic_store.path.read_bytes(), diagnostic_before)
         self.assertEqual(self.store.get_request(audit['request_id'])['state'], 'queued')
 
     def test_unknown_packets_and_unreserved_missing_packet_are_not_corruption(self):
@@ -78,9 +80,9 @@ class ArtifactStoreReviewTests(unittest.TestCase):
     def test_full_dispatch_group_uses_its_summary_even_when_global_details_full(self):
         row = self.store.quarantine_submission(None, uuid.uuid4().hex, uuid.uuid4().hex,
             reason='unmatched_saved_result', content=None, now=100)
-        value = json.loads(self.store.path.read_text(encoding='utf-8'))
+        value = json.loads(self.store.diagnostic_store.path.read_text(encoding='utf-8'))
         value['diagnostics'] = {}
-        # Root-owned valid full-index fixture, no patched limits or public setup claim.
+        # Root-owned valid full-diagnostic fixture, no patched limits or public setup claim.
         dispatches = [uuid.uuid4().hex for _ in range(128)]
         for dispatch in dispatches:
             for number in range(8):
@@ -90,7 +92,7 @@ class ArtifactStoreReviewTests(unittest.TestCase):
                     'reason', 'sha256', 'byte_count', 'actor_identity_id')}
                 detail['id'] = self.store._diagnostic_id(key)
                 value['diagnostics'][detail['id']] = detail
-        self.store.path.write_text(json.dumps(value), encoding='utf-8')
+        self.store.diagnostic_store.path.write_text(json.dumps(value), encoding='utf-8')
         restored = artifact_store.ArtifactStore(self.case.root)
         summary = restored.quarantine_submission(None, uuid.uuid4().hex, dispatches[0],
             reason='unmatched_saved_result', content=None, now=200)
diff --git a/tests/test_artifact_store_saturation.py b/tests/test_artifact_store_saturation.py
index ccb55da..ff169f9 100644
--- a/tests/test_artifact_store_saturation.py
+++ b/tests/test_artifact_store_saturation.py
@@ -30,9 +30,9 @@ class ArtifactDiagnosticSaturationTests(unittest.TestCase):
         self.assertEqual(second['counter'], 2**31 - 1)
         self.assertNotEqual(second['latest_diagnostic_id'], first['latest_diagnostic_id'])
         self.assertEqual(second['latest_byte_count'], len(b'another overflow key'))
-        before = store.path.read_bytes()
+        before = store.diagnostic_store.path.read_bytes()
         self.assertEqual(self.submit(store, dispatch, 'another overflow key', now=999), second)
-        self.assertEqual(store.path.read_bytes(), before)
+        self.assertEqual(store.diagnostic_store.path.read_bytes(), before)
         self.assertEqual(store.list_lineages()['count'], 0)
 
     def test_dispatch_counter_saturates_with_public_calls_after_valid_near_limit_seed(self):
@@ -41,9 +41,9 @@ class ArtifactDiagnosticSaturationTests(unittest.TestCase):
             self.submit(self.store, dispatch, f'detail {number}')
         self.assertEqual(self.submit(self.store, dispatch, 'first overflow')['kind'], 'dispatch_overflow')
         # Explicit white-box storage fixture, built from a real generated index.
-        value = json.loads(self.store.path.read_text(encoding='utf-8'))
+        value = json.loads(self.store.diagnostic_store.path.read_text(encoding='utf-8'))
         value['dispatch_overflow'][dispatch]['counter'] = 2**31 - 2
-        self.store.path.write_text(json.dumps(value), encoding='utf-8')
+        self.store.diagnostic_store.path.write_text(json.dumps(value), encoding='utf-8')
         restored = ArtifactStore(self.root)  # Strict load validates the seeded data.
         self.verify_near_limit(restored, dispatch)
 
@@ -52,9 +52,9 @@ class ArtifactDiagnosticSaturationTests(unittest.TestCase):
             self.submit(self.store, uuid.uuid4().hex, None)
         dispatch = uuid.uuid4().hex
         self.assertEqual(self.submit(self.store, dispatch, 'first overflow')['kind'], 'store_overflow')
-        value = json.loads(self.store.path.read_text(encoding='utf-8'))
+        value = json.loads(self.store.diagnostic_store.path.read_text(encoding='utf-8'))
         value['store_overflow']['counter'] = 2**31 - 2
-        self.store.path.write_text(json.dumps(value), encoding='utf-8')
+        self.store.diagnostic_store.path.write_text(json.dumps(value), encoding='utf-8')
         restored = ArtifactStore(self.root)
         self.verify_near_limit(restored, dispatch)
 
```

## Verification

First attempted unittest discover with explicit top-level failed before collection: namespace tests directory has no package initializer, ImportError Start directory is not importable. Tracked50520fb6, zero tests, infrastructure only. No code change followed that failure. Corrected selection loads the same sorted test_artifact*.py module names through unittest.loadTestsFromNames, with main .venv-windows Python and PYTHONPATH=.;49modules/379tests, tracked a94d1fe1. This is artifact-only selection, not project full discovery. Final result:379 tests PASS in203.516s, zero failures/errors/skips,49modules, tracked a94d1fe1 exited0. Includes all A1/R1/R2 artifact modules and literal991296B golden. In-suite real4MiB import max0.188725000s (limit0.300), fsync not mocked; this is not the future full/held D4 gate or whole-project discovery. Starlette httpx deprecation warning retained. Product/tool/portable literal fixture bytes unchanged. Before/after diff reviewed; no assertion removed or lowered.

```text
2026-10-26T10:41:34.185Z === started (pid 63676, agent 6c2a7241-eb44-423f-8d53-eb4cc5425ad8, shell: C:\Program Files\PowerShell\7\pwsh.exe)
2026-10-26T10:41:35.617Z err| C:\Users\SJG\Documents\CodePlayground\agentchattr\.venv-windows\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
2026-10-26T10:41:35.617Z err|   from starlette.testclient import TestClient as TestClient  # noqa
2026-10-26T10:41:35.683Z | {'kind': 'builder artifact-module selection, NOT full discovery', 'interpreter': 'C:\\Users\\SJG\\Documents\\CodePlayground\\agentchattr\\.venv-windows\\Scripts\\python.exe', 'modules': 49, 'tests': 379}
2026-10-26T10:44:59.199Z err| ...........................................................................................................................................................................................................................................................................................................................................................................................
2026-10-26T10:44:59.199Z err| ----------------------------------------------------------------------
2026-10-26T10:44:59.199Z err| Ran 379 tests in 203.516s
2026-10-26T10:44:59.199Z err| 
2026-10-26T10:44:59.199Z | {"method": "store/catalog real-files Windows default atomic_json", "portable_envelope_bytes": 4194304, "existing_lineages": 100, "existing_versions": 100, "requests": 128, "versions": 128, "packet_objects": 128, "zip_member_count": 262, "baseline_seconds": [0.00043999997433274984, 0.0004715999821200967, 0.0004056999459862709, 0.0005663000047206879, 0.0004437000025063753, 0.00044219999108463526, 0.000422299955971539, 0.0003758000675588846, 0.0004154000198468566, 0.0003980000037699938], "samples_seconds": [0.16415470000356436, 0.1838131999829784, 0.18872500001452863, 0.18598930002190173, 0.1788111999630928, 0.16790670005138963, 0.17320780002046376, 0.17263140005525202, 0.16636269993614405, 0.16173440008424222], "maximum_seconds": 0.18872500001452863, "limit_seconds": 0.3, "includes_metadata_parse": true, "includes_whole_index_validation": true, "fsync_mocked": false}
2026-10-26T10:44:59.199Z err| OK
2026-10-26T10:44:59.788Z === exited (code 0)

```
