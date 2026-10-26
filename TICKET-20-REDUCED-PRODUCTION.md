# Reduced20 backend production ledger

Production CLEARED by reviewer at6788311, with F1-F8 green preconditions. R3/UI/transcript/screen/activation/push excluded. Capability stays empty.

Order: fix replay fixture and record ERR-F honestly; implement source snapshot/typed precheck + shared projector text; implement identity resolver/operator services/status; strict route/middleware/app wiring; source-Stop shared cancel wiring; run root reds and fix reachable fixtures; add F1-F8 discriminating cases and mutation checks; affected baseline and one full builder discovery; independent execution/static review before acceptance. No timing campaign here.

First red correction: one error was a fixture defect, not infrastructure: replay reused an immutable packet id with changed bytes. Existing receipt stays unchanged. Correct with a fresh request/derived ids and actually relaunch producer before asserting replay bypasses live resolution.

## Delivery requirement added by Seth

On2026-10-26 Seth requested: "Before delivery please clean up the file stucture its kinda  a mess". Before delivery, group accumulated ticket/review docs under docs/, separate historical measurement receipts from current guidance, and keep a clear root entry point. Preserve history and verification evidence; prepare a concrete move map from the actual tree and check links/imports/tests after the moves. Schedule this after functional changes settle, before delivery. No file deletion or cleanup move has happened yet.

## Implemented backend, functional checkpoint

- artifact_sources: typed bounded canonical byte/count precheck; exact structural allowlists; same-channel one-lock deep snapshot; accepted-event/continuation source validation, own-message footer and shared projector text; immutable packet staging outside authority.
- artifact_operator: current identity resolver/mapping/global capability, source/producer capture outside authority, common service producer derivation, stored and concurrent replay before prepare, bounded public status/cancel/version/download/session projections and honest durability.
- artifact_routes/app: strict prefix-only operator auth/Host/Origin, raw duplicate-header checks, bounded chunked body/strict JSON, method/media/DTO errors, off-thread work, fixed safe downloads and public-header normalization. App uses shared configured owners. Capability unchanged.
- service/coordinator: public status without repair; source Stop shared by Stop/status/reconciliation; durable cancellation precedes fences; actual affected records/partial failures preserved; post-run requests remain independent.

Original27 ROOT tests first reached25 PASS/one imported-status lockfile difference/one CLI-relaunch fixture error. Fixed status to avoid unnecessary queue I/O for terminal/imported rows; replay uses a genuine fake-API managed relaunch with changed identity, nonce AND fingerprint (model change). CLI restart refusal was valid existing safety behavior, not a product bug. Expanded root46 tests OK3.932s, no provider/native/listener claim.

Focused integration222 ran57.422s with TWO findings: a CHANNELS exact contract sentence had been paraphrased by the scope-doc edit, and newly repeated Stop cancellation affected an explicitly later/stopped-source request. Restored the accurate original disclosure sentence and preserved explicit post-run independence without changing the old test. Targeted8 including Stop/recovery/docs then OK1.207s. Full affected/final builder verification follows the frozen source; old222 run is not labeled green.

Mutation proof:25 in-process mutants killed, source files unchanged by harness;24 had assertion failures (two also had follow-on errors), one typed-refusal mutant was ERROR-only and is labeled weaker. It verifies required subclass semantics, not runtime infrastructure. First harness invocation had a SyntaxError before any mutant ran; corrected the harness anchor and retained that fact. Final receipt/hashes are refreshed with the frozen verification run.

F1-F8 coverage is in the same four root areas, including valid create202/replay200, actual API relaunch, deterministic resolver mappings/family/duplicate identity, readonly terminal unconfirmed fence, raw header/body/error matrices, exact DTO/download values, completed session paging/titles, source detach/identity/phase/footer/count/Unicode bounds, Stop partial/retry/no-policy/same-channel-other-run and reconciliation. Fresh fixture scratch directories self-create. Existing frontend and transcript work stays held for later. No responsiveness screening is claimed here.

## Frozen verification window

Product checkpointccf266223cb6d0581978ae647a07ea2a13d70e09. An initial serialized verification command stopped in the mutation step before any artifact/full suite ran: one mutation now matched the newly added404 guard rather than the intended503 guard, so the selected503-only test correctly did not kill it. The failed receipt is retained as reduced20-mutations-wrong-branch.json, shellb6c05ae0. Corrected to two explicit404/503 mutations with their respective existing tests. Final26 mutants all killed,25 assertion-based and one typed-refusal ERROR-only; two assertion-based checks also produce follow-on errors. Product hashes unchanged by these in-process checks. No product fix followed this harness-target correction.

The affected selection and pre-fix full discovery completed as recorded below. Final-source full discovery follows the later concurrent-replay fix. No backend acceptance claim yet.

## Verification and real import-target miss

Affected54 artifact modules/483 tests on frozen163b542:482 passed, ONE old import benchmark miss0.3100635 against0.300,252.643s, tracked8a9a1447. No functional failures. The miss remains a miss; no sentinel existed in that unit run and no cause is claimed. Standalone source import/_persist/atomic_json AST equality against220f340 verified. ONE full builder discovery on that source:225 modules,1863 tests OK348.456s,4 skips, tracked454326ff. Its own import max0.188733s is retained separately and does not erase the earlier miss.

Reviewer requested ONE standalone ten-sample diagnostic under the stall sentinel, then a dated basic release ceiling1.0s while retaining/reporting0.300s target. Diagnostic981953fb collected10 fresh fixtures, all below0.300; no performance source change. Detailed JSON below. The benchmark/test-policy edit follows that ruling and changes no import code. Full discovery's stricter old assertion already passed; the exact new assertion is checked independently at its1.0 boundary without repeating another ten imports.

A final deterministic concurrent-create test then exposed a genuine race before packet staging (observed1FAIL0.232s): when a second identical creator had already saved newer source bytes, immutable conflict returned409. Added shared stored-result validation at the exception path under the boundary; metadata lookup failure is contained and changed intent still409. Also verified a matching imported intent replays with no live session/capability and does not enqueue. Final root48 tests OK4.539s. Because actual source changed, one final full run will include all affected artifact tests; no redundant standalone affected rerun. Prior1863 full is labeled pre-fix, not final-source green.

```json
{
  "kind": "diagnostic analysis, prior0.3100635 retained, no attribution/exclusion",
  "git_head_at_analysis": "163b5424c7cd395cb72bd75187471970e2a178b5",
  "raw_receipt_sha256": "a03a04c4126edde470896ccdca9a24fd78152e45f480606a9bdb8082545d1463",
  "source_hashes_match_before_test_policy_edit": true,
  "samples": [
    0.1700319000519812,
    0.16082990006543696,
    0.16460530005861074,
    0.1762738999677822,
    0.16412109998054802,
    0.17300650000106543,
    0.16458909993525594,
    0.16419220005627722,
    0.1680347000947222,
    0.159989699954167
  ],
  "median": 0.16459719999693334,
  "max": 0.1762738999677822,
  "sentinel_max_gap": 0.1077206,
  "gaps_over_100ms": 4,
  "gaps_over_500ms": 0,
  "counted_replace_retries": {},
  "target_exceedances": 0
}
```


## Final backend candidate, 2026-10-26

Frozen candidate97c7196022f6f8a20be4a397ecbded38757ce66e, product0725f699a32e617f364e912f35d76f8d02d3b90c. Builder shella953e7b9 completed27 in-process mutation kills then ONE full root discovery:225 modules,1865 tests OK362.026s,4 skips. This includes all affected artifact modules and the accepted A1/D4/R1/R2 support tests. No redundant standalone affected suite was run after the final concurrent-replay fix.26 mutant kills include assertion failures (two also yield follow-on errors); one typed-contract kill is ERROR-only and remains weaker evidence. Source files were untouched by mutation execution.

The final full run's import samples are retained below: max0.2136556001s, target0.300 met, reduced release ceiling1.0s met. Earlier affected0.3100635 miss, pre-fix full1863 result and standalone sentinel diagnostic remain separate evidence above. No miss is erased, no environmental cause claimed. Import production code remains unchanged from accepted220f3400.

Behavior pinned for integration fixes: test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent preserves post-run independence; test_engine_stop_cancels_mid_run_artifact_and_fences_claim and test_reconcile_uses_shared_cancel_and_reports_affected_records preserve mid-run Stop/shared reconciliation. The original CHANNELS backup exclusion sentence was restored without changing its existing assertion.

Independent backend acceptance remains pending. Next owner: reviewer, rerun the four root modules and spot mutations/static production audit against this candidate. UI follows acceptance. Cleanup plan docs/plans/2026-10-26-delivery-file-cleanup.md is submitted for review;110 rename-only moves, no deletions or source-path restructuring, no moves executed. Activation and push remain held.

### Final mutation receipt

```json
{
  "kind": "reduced20 in-process mutations, no source edits",
  "source_hashes": {
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_operator.py": "f1484d359ea11ebbcba8319c1e17a09411609c40f15605867cb141bb595ba01f",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_routes.py": "76f931c71148294250d3453e89c2fdb02df8769ec9a8b13d7924ef8a23ca7504",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_sources.py": "256b4e89cf3b439fb1950355fdcc8f21f27d4090b245a1ba48c1a01ae0b2cefc",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\store.py": "c295351faa7e2be022748ba57220df3db285718af176b8785e28e8a4883c18c0",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py": "def6af5caa5552989eda0aa1901ccd7564126815c72fe3aa92e629d23301d8b7",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py": "7f8a218c3ced6282bed8889078072b1f66495f98dccdef07fe3a34f9e3bdd840",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py": "b7e04c5197d6b8caf0db652befd6af3be957add665ca1b98fc02b0e46537e6ff",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\app.py": "381e62cf2ccd1bb2c50d6600af14ab6fe789bd2c3261c9f1141dbbea78d39d61"
  },
  "checks": [
    {
      "label": "author mappings",
      "test": "test_reason_mapping_order_family_skip_and_inactive_duplicate",
      "killed": true,
      "failures": 4,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='artifact_capability_missing')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'not_supported'\n- no_live_instance\n+ not_supported\n\n\n======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='unmanaged_producer')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'unmanaged'\n- no_live_instance\n+ unmanaged\n\n\n======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='capability_binding_changed')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'binding_changed'\n- no_live_instance\n+ binding_changed\n\n\n======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='runtime_unverified')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'runtime_unverified'\n- no_live_instance\n+ runtime_unverified\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.099s\n\nFAILED (failures=4)\n"
    },
    {
      "label": "global capability first",
      "test": "test_capability_off_refuses_before_any_manager_lookup",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_capability_off_refuses_before_any_manager_lookup (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_capability_off_refuses_before_any_manager_lookup)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 58, in test_capability_off_refuses_before_any_manager_lookup\n    self.assertEqual(caught.exception.cause,'capability_off')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_supported' != 'capability_off'\n- not_supported\n+ capability_off\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.068s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "concurrent packet winner replay",
      "test": "test_concurrent_saved_same_intent_wins_before_packet_staging",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_concurrent_saved_same_intent_wins_before_packet_staging (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_concurrent_saved_same_intent_wins_before_packet_staging)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 265, in test_concurrent_saved_same_intent_wins_before_packet_staging\n    try:result=operator.create(intent)\n               ~~~~~~~~~~~~~~~^^^^^^^^\n  File \"<reduced20-mutant>\", line 69, in create\nartifact_operator.ArtifactOperatorError: Document request conflicts with saved state.\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 266, in test_concurrent_saved_same_intent_wins_before_packet_staging\n    except module.ArtifactOperatorError as error:self.fail('Stored identical winner must replay: '+error.code)\n                                                 ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Stored identical winner must replay: request_conflict\n\n----------------------------------------------------------------------\nRan 1 test in 0.184s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "replay before relaunch lookup",
      "test": "test_replay_uses_stored_intent_before_prepare_or_resolver",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_replay_uses_stored_intent_before_prepare_or_resolver (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_replay_uses_stored_intent_before_prepare_or_resolver)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 150, in test_replay_uses_stored_intent_before_prepare_or_resolver\n    try:result=operator.create(intent)\n               ~~~~~~~~~~~~~~~^^^^^^^^\n  File \"<reduced20-mutant>\", line 20, in create\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_operator.py\", line 73, in resolve_default_artifact_author\n    raise ArtifactOperatorError('no_author_available', cause=cause, author_name=name, examined_roles=examined)\nartifact_operator.ArtifactOperatorError: No supported live author is available for this session.\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 151, in test_replay_uses_stored_intent_before_prepare_or_resolver\n    except module.ArtifactOperatorError as error:self.fail('Identical replay refused: '+error.code)\n                                                 ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Identical replay refused: no_author_available\n\n----------------------------------------------------------------------\nRan 1 test in 0.338s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "create caller boundary",
      "test": "test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 233, in test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect\n    with case.service._boundary(),self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(intent)\n                                  ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactOperatorError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.159s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "public status serialized",
      "test": "test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 241, in test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect\n    self.assertTrue(seen);self.assertTrue(all(pair==(True,True) for pair in seen))\n                          ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: False is not true\n\n----------------------------------------------------------------------\nRan 1 test in 0.147s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "create202",
      "test": "test_successful_create_replay_conflict_and_capture_stop_guard",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_successful_create_replay_conflict_and_capture_stop_guard (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_successful_create_replay_conflict_and_capture_stop_guard)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 190, in test_successful_create_replay_conflict_and_capture_stop_guard\n    first=operator.create(intent);self.assertTrue(first.created)\n                                  ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\nAssertionError: False is not true\n\n----------------------------------------------------------------------\nRan 1 test in 0.145s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "capture current Stop guard",
      "test": "test_successful_create_replay_conflict_and_capture_stop_guard",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_successful_create_replay_conflict_and_capture_stop_guard (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_successful_create_replay_conflict_and_capture_stop_guard)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 199, in test_successful_create_replay_conflict_and_capture_stop_guard\n    with patch.object(case.artifacts,'put_packet',stop_after_packet),self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(new_intent)\n                                                                     ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactOperatorError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.215s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "error durable state",
      "test": "test_summary_all_states_and_post_durable_cancel_failure",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_summary_all_states_and_post_durable_cancel_failure (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_summary_all_states_and_post_durable_cancel_failure)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 224, in test_summary_all_states_and_post_durable_cancel_failure\n    self.assertEqual(caught.exception.durability,'recorded');self.assertEqual(caught.exception.request['state'],'cancelled')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_recorded' != 'recorded'\n- not_recorded\n? ----\n+ recorded\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.130s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "Host guard",
      "test": "test_bad_host_and_duplicate_security_headers_refuse",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers={'x-session-token': 'OPERATOR_ONLY', 'origin': 'http://127.0.0.1:18300', 'host': 'attacker.invalid:18300'})\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 45, in test_bad_host_and_duplicate_security_headers_refuse\n    self.assertEqual(self.client.get(self.read,headers=headers).status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 200 != 403\n\n======================================================================\nFAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 46, in test_bad_host_and_duplicate_security_headers_refuse\n    self.assertEqual(self.calls,[])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\nAssertionError: Lists differ: [True] != []\n\nFirst list contains 1 additional elements.\nFirst extra element 0:\nTrue\n\n- [True]\n+ []\n\n----------------------------------------------------------------------\nRan 1 test in 0.025s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "bearer excluded",
      "test": "test_security_raw_header_matrix_envelopes_and_legacy_namespace",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_security_raw_header_matrix_envelopes_and_legacy_namespace (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_security_raw_header_matrix_envelopes_and_legacy_namespace) (headers={'x-session-token': 'OPERATOR_ONLY', 'origin': 'http://127.0.0.1:18300', 'authorization': 'Bearer seat'})\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 163, in test_security_raw_header_matrix_envelopes_and_legacy_namespace\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 404 != 403\n\n======================================================================\nFAIL: test_security_raw_header_matrix_envelopes_and_legacy_namespace (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_security_raw_header_matrix_envelopes_and_legacy_namespace) (headers=[('x-session-token', 'OPERATOR_ONLY'), ('authorization', 'Bearer x'), ('authorization', 'Bearer y')])\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 163, in test_security_raw_header_matrix_envelopes_and_legacy_namespace\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 404 != 403\n\n----------------------------------------------------------------------\nRan 1 test in 0.024s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "POST Origin",
      "test": "test_post_requires_origin_but_get_allows_absent_origin",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_post_requires_origin_but_get_allows_absent_origin (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_requires_origin_but_get_allows_absent_origin)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 37, in test_post_requires_origin_but_get_allows_absent_origin\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 200 != 403\n\n----------------------------------------------------------------------\nRan 1 test in 0.005s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "query token excluded",
      "test": "test_query_token_and_authorization_are_never_operator_fallback",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=('x-session-token', 'origin'))\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 30, in test_query_token_and_authorization_are_never_operator_fallback\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 405 != 403\n\n----------------------------------------------------------------------\nRan 1 test in 0.005s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "chunked cap",
      "test": "test_json_boundaries_chunked_body_and_scoped_errors",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_json_boundaries_chunked_body_and_scoped_errors (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_json_boundaries_chunked_body_and_scoped_errors)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 178, in test_json_boundaries_chunked_body_and_scoped_errors\n    self.assertEqual(response.status_code,413);self.assertEqual(response.json()['code'],'request_too_large')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 400 != 413\n\n----------------------------------------------------------------------\nRan 1 test in 0.008s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "duplicate JSON",
      "test": "test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='application/json', size=31)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 64, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint\n    self.assertEqual(response.status_code,code)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 200 != 400\n\n======================================================================\nFAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 65, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint\n    self.assertEqual(self.calls,[])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\nAssertionError: Lists differ: [True] != []\n\nFirst list contains 1 additional elements.\nFirst extra element 0:\nTrue\n\n- [True]\n+ []\n\n----------------------------------------------------------------------\nRan 1 test in 0.006s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "503 envelope preserved",
      "test": "test_fixed_error_codes_do_not_become_generic_500",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_fixed_error_codes_do_not_become_generic_500 (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_fixed_error_codes_do_not_become_generic_500) (code='storage_unavailable')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 226, in test_fixed_error_codes_do_not_become_generic_500\n    self.assertEqual(response.status_code,status,response.text);self.assertEqual(response.json()['code'],code)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 500 != 503 : {\"code\":\"unexpected_failure\",\"error\":\"Document operation failed.\",\"cause\":null,\"author_name\":null,\"examined_roles\":null,\"request_id\":null,\"durability\":null,\"request\":null}\n\n======================================================================\nFAIL: test_fixed_error_codes_do_not_become_generic_500 (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_fixed_error_codes_do_not_become_generic_500) (code='boundary_held')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 226, in test_fixed_error_codes_do_not_become_generic_500\n    self.assertEqual(response.status_code,status,response.text);self.assertEqual(response.json()['code'],code)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 500 != 503 : {\"code\":\"unexpected_failure\",\"error\":\"Document operation failed.\",\"cause\":null,\"author_name\":null,\"examined_roles\":null,\"request_id\":null,\"durability\":null,\"request\":null}\n\n----------------------------------------------------------------------\nRan 1 test in 0.164s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "404 domain code preserved",
      "test": "test_create_202_replay_200_validation_and_detail_errors",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_create_202_replay_200_validation_and_detail_errors (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_create_202_replay_200_validation_and_detail_errors) (changes=('session_id',))\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 206, in test_create_202_replay_200_validation_and_detail_errors\n    self.assertEqual(response.status_code,code,response.text);self.assertEqual(response.json()['code'],error_code)\n                                                              ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_found' != 'session_unknown'\n- not_found\n+ session_unknown\n\n\n======================================================================\nFAIL: test_create_202_replay_200_validation_and_detail_errors (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_create_202_replay_200_validation_and_detail_errors) (changes=('run_id',))\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 206, in test_create_202_replay_200_validation_and_detail_errors\n    self.assertEqual(response.status_code,code,response.text);self.assertEqual(response.json()['code'],error_code)\n                                                              ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_found' != 'run_unknown'\n- not_found\n+ run_unknown\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.185s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "source UID proof",
      "test": "test_capture_single_read_identity_attribution_and_deep_detachment",
      "killed": true,
      "failures": 1,
      "errors": 1,
      "evidence": "assertion",
      "output": "======================================================================\nERROR: test_capture_single_read_identity_attribution_and_deep_detachment (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_capture_single_read_identity_attribution_and_deep_detachment)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 105, in test_capture_single_read_identity_attribution_and_deep_detachment\n    self.assertEqual(caught.exception.code,'source_unavailable')\n                     ^^^^^^^^^^^^^^^^\nAttributeError: '_AssertRaisesContext' object has no attribute 'exception'\n\n======================================================================\nFAIL: test_capture_single_read_identity_attribution_and_deep_detachment (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_capture_single_read_identity_attribution_and_deep_detachment) (field='uid')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 103, in test_capture_single_read_identity_attribution_and_deep_detachment\n    with self.subTest(field=field),self.assertRaises(module.ArtifactSourceError) as caught:\n                                   ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactSourceError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.073s\n\nFAILED (failures=1, errors=1)\n"
    },
    {
      "label": "source caps",
      "test": "test_cap_precheck_exact_bytes_unicode_escaping_and_count",
      "killed": true,
      "failures": 1,
      "errors": 1,
      "evidence": "assertion",
      "output": "======================================================================\nERROR: test_cap_precheck_exact_bytes_unicode_escaping_and_count (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_cap_precheck_exact_bytes_unicode_escaping_and_count)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 143, in test_cap_precheck_exact_bytes_unicode_escaping_and_count\n    self.assertEqual(caught.exception.code,'source_too_large')\n                     ^^^^^^^^^^^^^^^^\nAttributeError: '_AssertRaisesContext' object has no attribute 'exception'\n\n======================================================================\nFAIL: test_cap_precheck_exact_bytes_unicode_escaping_and_count (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_cap_precheck_exact_bytes_unicode_escaping_and_count) (kind='x')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 142, in test_cap_precheck_exact_bytes_unicode_escaping_and_count\n    with self.subTest(kind=text[:1]),self.assertRaises(module.ArtifactSourceError) as caught:module.check_packet_bounds(packet)\n                                     ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactSourceError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.013s\n\nFAILED (failures=1, errors=1)\n"
    },
    {
      "label": "metadata allowlist",
      "test": "test_projection_allowlist_preserves_literal_text_not_server_metadata",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_projection_allowlist_preserves_literal_text_not_server_metadata (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_projection_allowlist_preserves_literal_text_not_server_metadata)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 70, in test_projection_allowlist_preserves_literal_text_not_server_metadata\n    self.assertEqual(message['provenance'],{'session_id':1,'run_id':'a'*32})\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: {'ses[52 chars]aaaa', 'token': 'PRIVATE_TOKEN', 'launch_nonce[14 chars]NCE'} != {'ses[52 chars]aaaa'}\n- {'launch_nonce': 'PRIVATE_NONCE',\n-  'run_id': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',\n? ^\n\n+ {'run_id': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'session_id': 1}\n? ^                                             +++++++++++++++++\n\n-  'session_id': 1,\n-  'token': 'PRIVATE_TOKEN'}\n\n----------------------------------------------------------------------\nRan 1 test in 0.001s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "source full walk seam",
      "test": "test_capture_single_read_identity_attribution_and_deep_detachment",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_capture_single_read_identity_attribution_and_deep_detachment (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_capture_single_read_identity_attribution_and_deep_detachment)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 96, in test_capture_single_read_identity_attribution_and_deep_detachment\n    snapshot.assert_called_once();walk.assert_called_once()\n                                  ~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 965, in assert_called_once\n    raise AssertionError(msg)\nAssertionError: Expected '_packet_scope' to have been called once. Called 0 times.\n\n----------------------------------------------------------------------\nRan 1 test in 0.073s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "snapshot deep detach",
      "test": "test_snapshot_selected_is_detached_and_channel_exact",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_snapshot_selected_is_detached_and_channel_exact (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_selected_is_detached_and_channel_exact)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 28, in test_snapshot_selected_is_detached_and_channel_exact\n    self.assertEqual(messages.get_snapshot(first['id'])['metadata']['nested']['values'],[1])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Lists differ: [1, 2] != [1]\n\nFirst list contains 1 additional elements.\nFirst extra element 1:\n2\n\n- [1, 2]\n+ [1]\n\n----------------------------------------------------------------------\nRan 1 test in 0.004s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "snapshot typed refusal",
      "test": "test_snapshot_missing_and_duplicate_ids_never_return_partial",
      "killed": true,
      "failures": 0,
      "errors": 1,
      "evidence": "ERROR-only, weaker typed-contract evidence",
      "output": "======================================================================\nERROR: test_snapshot_missing_and_duplicate_ids_never_return_partial (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_missing_and_duplicate_ids_never_return_partial) (ids=[0, 999999])\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 47, in test_snapshot_missing_and_duplicate_ids_never_return_partial\n    with self.subTest(ids=ids),self.assertRaises(MessageSnapshotUnavailable):messages.snapshot_selected('review',ids)\n                                                                             ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in snapshot_selected\nValueError: Selected messages are unavailable.\n\n----------------------------------------------------------------------\nRan 1 test in 0.002s\n\nFAILED (errors=1)\n"
    },
    {
      "label": "Stop policy wired",
      "test": "test_engine_stop_cancels_mid_run_artifact_and_fences_claim",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_engine_stop_cancels_mid_run_artifact_and_fences_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_engine_stop_cancels_mid_run_artifact_and_fences_claim)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 22, in test_engine_stop_cancels_mid_run_artifact_and_fences_claim\n    self.assertEqual((row['state'],row['reason']),('cancelled','source_stopped'))\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Tuples differ: ('queued', 'queued') != ('cancelled', 'source_stopped')\n\nFirst differing element 0:\n'queued'\n'cancelled'\n\n- ('queued', 'queued')\n+ ('cancelled', 'source_stopped')\n\n----------------------------------------------------------------------\nRan 1 test in 0.160s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "Stop fence effect",
      "test": "test_engine_stop_cancels_mid_run_artifact_and_fences_claim",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_engine_stop_cancels_mid_run_artifact_and_fences_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_engine_stop_cancels_mid_run_artifact_and_fences_claim)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 24, in test_engine_stop_cancels_mid_run_artifact_and_fences_claim\n    self.assertIn(transport['state'],('cancelling','cancelled'))\n    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'dispatched' not found in ('cancelling', 'cancelled')\n\n----------------------------------------------------------------------\nRan 1 test in 0.171s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "reconcile shares Stop",
      "test": "test_reconcile_uses_shared_cancel_and_reports_affected_records",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_reconcile_uses_shared_cancel_and_reports_affected_records (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_reconcile_uses_shared_cancel_and_reports_affected_records)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 57, in test_reconcile_uses_shared_cancel_and_reports_affected_records\n    self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'],'source_stopped')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'queued' != 'source_stopped'\n- queued\n+ source_stopped\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.159s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "postrun independent",
      "test": "test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent (tests.test_artifact_recovery.ArtifactRecoveryTests.test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent)\nService/engine sequencing fixture, not an app Stop-route integration claim.\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_recovery.py\", line 340, in test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent\n    self.assertEqual(case.artifacts.get_request(later['request_id'])['state'], 'queued')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'cancelled' != 'queued'\n- cancelled\n+ queued\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.295s\n\nFAILED (failures=1)\n"
    }
  ],
  "source_unchanged": true,
  "pass": true
}
```

### Final builder log (includes all import samples)

```text
2026-10-26T20:07:43.696Z === started (pid 37280, agent 6c2a7241-eb44-423f-8d53-eb4cc5425ad8, shell: C:\Program Files\PowerShell\7\pwsh.exe)
2026-10-26T20:07:44.185Z err| C:\Users\SJG\Documents\CodePlayground\agentchattr\.venv-windows\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
2026-10-26T20:07:44.185Z err|   from starlette.testclient import TestClient as TestClient  # noqa
2026-10-26T20:07:44.367Z | {"label": "author mappings", "test": "test_reason_mapping_order_family_skip_and_inactive_duplicate", "killed": true, "failures": 4, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:44.436Z | {"label": "global capability first", "test": "test_capability_off_refuses_before_any_manager_lookup", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:44.622Z | {"label": "concurrent packet winner replay", "test": "test_concurrent_saved_same_intent_wins_before_packet_staging", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:44.962Z | {"label": "replay before relaunch lookup", "test": "test_replay_uses_stored_intent_before_prepare_or_resolver", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.123Z | {"label": "create caller boundary", "test": "test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.272Z | {"label": "public status serialized", "test": "test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.419Z | {"label": "create202", "test": "test_successful_create_replay_conflict_and_capture_stop_guard", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.636Z | {"label": "capture current Stop guard", "test": "test_successful_create_replay_conflict_and_capture_stop_guard", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.767Z | {"label": "error durable state", "test": "test_summary_all_states_and_post_durable_cancel_failure", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.794Z | {"label": "Host guard", "test": "test_bad_host_and_duplicate_security_headers_refuse", "killed": true, "failures": 2, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.820Z | {"label": "bearer excluded", "test": "test_security_raw_header_matrix_envelopes_and_legacy_namespace", "killed": true, "failures": 2, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.828Z | {"label": "POST Origin", "test": "test_post_requires_origin_but_get_allows_absent_origin", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.834Z | {"label": "query token excluded", "test": "test_query_token_and_authorization_are_never_operator_fallback", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.844Z | {"label": "chunked cap", "test": "test_json_boundaries_chunked_body_and_scoped_errors", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:45.851Z | {"label": "duplicate JSON", "test": "test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint", "killed": true, "failures": 2, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.017Z | {"label": "503 envelope preserved", "test": "test_fixed_error_codes_do_not_become_generic_500", "killed": true, "failures": 2, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.205Z | {"label": "404 domain code preserved", "test": "test_create_202_replay_200_validation_and_detail_errors", "killed": true, "failures": 2, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.280Z | {"label": "source UID proof", "test": "test_capture_single_read_identity_attribution_and_deep_detachment", "killed": true, "failures": 1, "errors": 1, "evidence": "assertion"}
2026-10-26T20:07:46.295Z | {"label": "source caps", "test": "test_cap_precheck_exact_bytes_unicode_escaping_and_count", "killed": true, "failures": 1, "errors": 1, "evidence": "assertion"}
2026-10-26T20:07:46.297Z | {"label": "metadata allowlist", "test": "test_projection_allowlist_preserves_literal_text_not_server_metadata", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.372Z | {"label": "source full walk seam", "test": "test_capture_single_read_identity_attribution_and_deep_detachment", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.377Z | {"label": "snapshot deep detach", "test": "test_snapshot_selected_is_detached_and_channel_exact", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.380Z | {"label": "snapshot typed refusal", "test": "test_snapshot_missing_and_duplicate_ids_never_return_partial", "killed": true, "failures": 0, "errors": 1, "evidence": "ERROR-only, weaker typed-contract evidence"}
2026-10-26T20:07:46.542Z | {"label": "Stop policy wired", "test": "test_engine_stop_cancels_mid_run_artifact_and_fences_claim", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.714Z | {"label": "Stop fence effect", "test": "test_engine_stop_cancels_mid_run_artifact_and_fences_claim", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:46.874Z | {"label": "reconcile shares Stop", "test": "test_reconcile_uses_shared_cancel_and_reports_affected_records", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:47.170Z | {"label": "postrun independent", "test": "test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T20:07:47.172Z | {"receipt": "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\.audit-tmp\\reduced20-mutations.json", "pass": true}
2026-10-26T20:07:48.620Z err| C:\Users\SJG\Documents\CodePlayground\agentchattr\.venv-windows\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
2026-10-26T20:07:48.621Z err|   from starlette.testclient import TestClient as TestClient  # noqa
2026-10-26T20:07:48.922Z | {'kind': 'D4 builder full root test-module discovery, namespace-safe', 'interpreter': 'C:\\Users\\SJG\\Documents\\CodePlayground\\agentchattr\\.venv-windows\\Scripts\\python.exe', 'modules': 225, 'tests': 1865}
2026-10-26T20:11:58.486Z err| .........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................Channel state is unavailable; publication and new claims are held.
2026-10-26T20:12:02.232Z err| .............................................................................................................Session 2: failed to persist dispatch for claude (OSError)
2026-10-26T20:12:10.658Z err| ................................................................................................................................Scheduled attempt could not be saved; nothing was published.
2026-10-26T20:12:10.748Z err| ...Scheduled publication was not confirmed (OSError).
2026-10-26T20:12:10.782Z err| .Scheduled delivery bookkeeping could not be saved; the attempt remains reserved.
2026-10-26T20:12:10.810Z err| .Scheduled delivery bookkeeping could not be saved; the attempt remains reserved.
2026-10-26T20:12:11.082Z err| ..........Scheduled publication was not confirmed (OSError).
2026-10-26T20:12:11.140Z err| .Scheduled publication was not confirmed (OSError).
2026-10-26T20:12:13.589Z err| .............................................................Session 2: failed to persist dispatch for cli-4d8efa15-ed564a040417 (OSError)
2026-10-26T20:12:15.437Z err| ..................................Session 1: failed to persist dispatch for cli-4d8efa15-c4ffb4bb7970 (OSError)
2026-10-26T20:12:15.547Z err| .Session 1: failed to persist dispatch for cli-4d8efa15-78c7a415391f (OSError)
2026-10-26T20:12:15.661Z err| .Session 1: failed to persist dispatch for cli-4d8efa15-51b2eef6c5c0 (OSError)
2026-10-26T20:12:26.538Z err| ........................................................................................................................Session 1: failed to persist dispatch for codex (OSError)
2026-10-26T20:12:30.538Z | {"method": "store/catalog real-files Windows default atomic_json", "portable_envelope_bytes": 4194304, "existing_lineages": 100, "existing_versions": 100, "requests": 128, "versions": 128, "packet_objects": 128, "zip_member_count": 262, "baseline_seconds": [0.00039820000529289246, 0.0005501999985426664, 0.0004097999772056937, 0.000390700064599514, 0.00039980001747608185, 0.00040280004031956196, 0.00038579991087317467, 0.0005828000139445066, 0.0004018000327050686, 0.000394499977119267], "samples_seconds": [0.17380089999642223, 0.21365560009144247, 0.16129720001481473, 0.17502719990443438, 0.1636166999815032, 0.16477689996827394, 0.16356560005806386, 0.16696439997758716, 0.17076210002414882, 0.16346800001338124], "maximum_seconds": 0.21365560009144247, "target_seconds": 0.3, "target_met": true, "limit_seconds": 1.0, "limit_policy": "reduced first-release basic responsiveness", "includes_metadata_parse": true, "includes_whole_index_validation": true, "fsync_mocked": false}
2026-10-26T20:12:30.538Z |   Using tmux session: owned
2026-10-26T20:12:30.538Z |   Reattach: tmux attach -t owned
2026-10-26T20:12:30.538Z |   Session already exists; preserved. Choose another seat or stop its owner first.
2026-10-26T20:12:30.538Z |   Warning: AGENTCHATTR_PORT='not-a-number' is not a valid integer, ignoring
2026-10-26T20:12:30.538Z |   MCP proxy: port 59249
2026-10-26T20:12:30.538Z |   MCP proxy: port 50157
2026-10-26T20:12:30.538Z |   Using tmux session: agentchattr-claude-1
2026-10-26T20:12:30.538Z |   Reattach: tmux attach -t agentchattr-claude-1
2026-10-26T20:12:30.539Z |   Child exit receipt unavailable; attach success does not prove child success.
2026-10-26T20:12:30.539Z |   [wrapper] VT enable (stdout): 0x0003 -> 0x0007 [ok]
2026-10-26T20:12:37.399Z err| .........................................................................sss.................Launch could not complete: Agent template is not configured. Add it to config.local.toml before launching.
2026-10-26T20:13:00.806Z err| .........................................................................................................................................................................Session 2: failed to persist dispatch for cli-4d8efa15-e02f359fcd0e (OSError)
2026-10-26T20:13:01.344Z err| ....Session 2: failed to persist dispatch for cli-4d8efa15-d802c439d1be (OSError)
2026-10-26T20:13:13.726Z err| ...................................................................................................................................................................................Artifact ownership binding is unavailable; artifact work is held.
2026-10-26T20:13:13.749Z err| .Artifact ownership binding is unavailable; artifact work is held.
2026-10-26T20:13:50.948Z err| .....................................................................................................................................................................................................................................................................................................................................................................................s......
2026-10-26T20:13:50.948Z | {
2026-10-26T20:13:50.948Z |   "server": "absent",
2026-10-26T20:13:50.948Z |   "environment_ready": false,
2026-10-26T20:13:50.948Z |   "checked_at": "2026-10-26T20:12:37.722345+00:00",
2026-10-26T20:13:50.948Z |   "agents": []
2026-10-26T20:13:50.948Z | }
2026-10-26T20:13:50.948Z |   MCP proxy: port 64951
2026-10-26T20:13:50.948Z |   MCP proxy: port 64960
2026-10-26T20:13:50.948Z |   MCP proxy: port 62745
2026-10-26T20:13:50.948Z |   MCP proxy: port 54463
2026-10-26T20:13:50.948Z |   MCP proxy: port 55482
2026-10-26T20:13:50.948Z err| ----------------------------------------------------------------------
2026-10-26T20:13:50.948Z err| Ran 1865 tests in 362.026s
2026-10-26T20:13:50.948Z err|
2026-10-26T20:13:50.948Z err| OK (skipped=4)
2026-10-26T20:13:51.577Z === exited (code 0)

```


## Independent review correction in progress

Reviewer92d4df60 reran48 root tests,170 support tests and27 mutants successfully, then identified G1 held-owner Stop/claim regression. Backend NOT accepted. Eight new review tests first ran1.272s:6 failures plus2 genuine held-owner propagation errors, and1 subtest fixture error (HTTPX string header could not encode superscript Content-Length). Corrected that fixture to raw latin1 bytes; ASCII refusal is separately mutation-checked. Prior full1865 remains pre-review-fix evidence.

G1/G2: explicit engine Stop fences artifact sources, while historical reconciliation has one bounded retained-record pass instead of per-run full-index scans. Artifact owner failure is contained and separate artifact_cancellation warning/status does not affect review stopping/unresolved receipts or termination offers. Runtime repair rotates100 retained requests to avoid starvation, and skips already fenced transport. Existing partial-fence tests now assert warning and successful later repair rather than propagated session failure. G3/G4/R1-R3: ASCII Content-Length, duplicate query refusal, empty HEAD errors, typed orphan packet conflict and producer drift mapping. R4/R5 contract records actual screen hold path and snapshot/paging behavior. Root56 initially passed5.529s before final bounded rotation and expanded mutations; final verification follows.


Correction verification checkpoint:37 mutants killed (36 assertion kills, one snapshot typed-contract ERROR-only), source hashes unchanged. Earlier correction harness attempts retained: ASCII-header test initially exercised HTTPX validation rather than raw ASGI; added direct latin1 scope and killed the ASCII mutant. Separate-report mutant initially only changed an unused return path; moved it to the actual returned record assignment and killed it. Post-run independence test now explicitly requests source fencing, preserving its original safety intent under the new ordinary cancel_run default.

Trackedee9df094 ran224 real root/support tests successfully in54.862s, plus ONE loader error from my wrong module name tests.test_artifact_mcp_reuse. This is not labeled a green suite. Correct module tests.test_artifact_mcp runs next, then ONE full builder discovery covers the frozen delta. No need to repeat the224 successful cases separately. Root review areas now57 tests (nine added methods); prior56 green before rotation is historical.


### Correction full run and additional review

Frozen6e428a4: full1874 ran362.956s,4 skips,3 errors, retained shell6cfe3c19. Actual findings: optional artifact repair acquired the held channel boundary during configured startup; an empty Stop report unnecessarily read a mock/non-artifact transport; the old durable-Stop test hook lacked the new fence_artifacts keyword. Fixed the optional held-channel no-op and empty-report no-read; adjusted only that test hook signature/forwarding, preserving every durability assertion. Two new root reproductions observed1FAIL/1ERROR0.309s before those product fixes; targeted46 then passed3.126s. This full run is NOT labeled green.

Reviewer then found A1 getter-None, A2 wider policy exception propagation, A3 queued source-Stop claim window. Observed3 new test methods with5FAIL/1ERROR0.967s before source fixes; queued source actually claimed, so this is a real safety finding. Getter-None is no effect; all artifact-policy exceptions contained/logged/separately warned; stopped-source set lookup blocks queued and prepared claim eligibility independently of repair. Retained repair includes queued, remains rotating/bounded, handles restart and changing candidates. B1 test-hook signature fixed; B2 bounded128 observation cache/UI warning requirement documented; B3 None/fault matrix/queued/prepared/restart/identical orphan retry/capability drift/HEAD200 covered; B4 poll cost added to later screen scope. An initial None-policy test wrongly expected a new consumer to take an already-owned artifact seat; corrected to preserve QueueBusy and check an unrelated free seat.

Targeted93 tests OK9.122s (root changes, coordination, configured held startup, session Stop/choices). Final45 mutants all killed,44 assertion kills and one snapshot typed-contract ERROR-only. The earlier None guard mutant initially only created a warning, so its test now asserts no spurious warning and kills both explicit/retained None mutants. Final source/full verification follows; no source edits during that window.


### Passing full baseline and final D follow-ups

Frozen264b6c3 full1882 OK368.095s,4 skips, shellb42282d3, with no source edits during that run. Reviewer statically confirmed A1/A2/A3/B1 and requested D1-D5 closure details. Three fresh reproductions of D1/D3/D4 observed3FAIL/1ERROR0.716s. Implemented typed enqueue refusal for None policy; clean-first warning eviction/global unconfirmed_overflow; contained ledger inspection failure. Prepared/no-record test now retries explicit Stop after recreating the coordinator and requires cancelled/source_stopped, choosing the reviewer's explicit retry alternative without per-claim full-index prepared scans.

D5 extends exact nested fault sites (getter, repair_cancel_fences, eligible_dispatch_ids, real SessionStore.get), real102-request retained rotation100 then2 across coordinator recreation and shrinking candidates, successful owned review termination under held artifact owner, HEAD200 body suppression/header preservation. Targeted109 tests OK20.467s.51 mutations initially all killed; final cache hardening additionally invalidates old confirmation before a new dispatch is remembered, and treats any warning as unconfirmed even if a stale confirmed bit exists. Final mutation/full run follows. UI textContent/cache-key warning and report-only100+ poll-cost screen stay later deliverables; no cleanup moves, activation or push.


## Final corrected backend verification, 2026-10-26

Frozen source146b00a4ba17e191a96a8d662f32dd4ba5eb728f: ONE builder full discovery225 modules,1888 tests OK370.823s,4 skips, shell6514215a, exit0. It covers all reduced backend root areas, coordination/Stop/configuration and accepted A1/D4/MCP/R1/R2 support.51 in-process mutants killed:50 assertion kills, one snapshot typed-contract ERROR-only (weaker). Source hashes in the receipt match the frozen final files and stayed unchanged through mutation execution. The latest cache invalidation/eviction code is included in this full green result. Targeted109 OK20.467s is earlier focused evidence; final full is authoritative for this pin.

Final closure changes: typed enqueue refusal when a bound policy getter returns None; prepared/no-record requests remain ineligible and cancel on explicit repeated Stop after owner recovery/recreated coordinator; clean-first cache eviction plus global unconfirmed_overflow; new dispatch/failure invalidates prior confirmation; optional ledger inspection failure cannot abort review transport/status; nested getter/repair/eligibility/session-read errors contained. Real102-request repair handles100 then2 with restart/reset and shrinking candidates. Owned review termination succeeds despite a held artifact policy. HEAD200 and every refusal stay bodyless. No provider calls, browser/UI acceptance, activation, push or file moves are claimed.

All prior unsuccessful runs remain above, including the real safety findings and1874 three-error full run.1882 green was the preceding corrected baseline, not silently reused for the final delta. R2/D4 earlier timing history and the retained0.3100635 import-target miss remain unchanged. Next owner: reviewer reruns reduced modules/earlier support/Stop coordination and51 mutation checks, statically audits D1-D5, then closes backend. UI begins only after that review; its artifact warning text/render-cache-key and responsiveness screen remain explicit. Cleanup approved but still last, no moves/deletions yet.

### Final mutation receipt

```json
{
  "kind": "reduced20 in-process mutations, no source edits",
  "source_hashes": {
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_operator.py": "ae3a3a0e29d90d4a14c935cc5fa2acd6b20a459614d045e06c11bea01e0a1e6b",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_routes.py": "4d7c0ef58fcc9cb283f653256633708edc2e8625e88df609c098659948dfdde6",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_sources.py": "256b4e89cf3b439fb1950355fdcc8f21f27d4090b245a1ba48c1a01ae0b2cefc",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\store.py": "c295351faa7e2be022748ba57220df3db285718af176b8785e28e8a4883c18c0",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py": "ade861d579c68b7c901adeb17288108704f0bbe5c66ed3af47053f08dc4ff14f",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py": "f31df44c6f74341fdc20904460c9d6c4f850e23e309ed04657ea0bdd1244f972",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py": "bedec56aaf16845f923ade8734dca51334c08210194b563362bfabd887557099",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\app.py": "381e62cf2ccd1bb2c50d6600af14ab6fe789bd2c3261c9f1141dbbea78d39d61"
  },
  "checks": [
    {
      "label": "author mappings",
      "test": "test_reason_mapping_order_family_skip_and_inactive_duplicate",
      "killed": true,
      "failures": 4,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='artifact_capability_missing')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'not_supported'\n- no_live_instance\n+ not_supported\n\n\n======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='unmanaged_producer')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'unmanaged'\n- no_live_instance\n+ unmanaged\n\n\n======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='capability_binding_changed')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'binding_changed'\n- no_live_instance\n+ binding_changed\n\n\n======================================================================\nFAIL: test_reason_mapping_order_family_skip_and_inactive_duplicate (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_reason_mapping_order_family_skip_and_inactive_duplicate) (reason='runtime_unverified')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 166, in test_reason_mapping_order_family_skip_and_inactive_duplicate\n    self.assertEqual(caught.exception.cause,cause);self.assertEqual(caught.exception.examined_roles,2)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'no_live_instance' != 'runtime_unverified'\n- no_live_instance\n+ runtime_unverified\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.094s\n\nFAILED (failures=4)\n"
    },
    {
      "label": "global capability first",
      "test": "test_capability_off_refuses_before_any_manager_lookup",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_capability_off_refuses_before_any_manager_lookup (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_capability_off_refuses_before_any_manager_lookup)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 58, in test_capability_off_refuses_before_any_manager_lookup\n    self.assertEqual(caught.exception.cause,'capability_off')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_supported' != 'capability_off'\n- not_supported\n+ capability_off\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.074s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "concurrent packet winner replay",
      "test": "test_concurrent_saved_same_intent_wins_before_packet_staging",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_concurrent_saved_same_intent_wins_before_packet_staging (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_concurrent_saved_same_intent_wins_before_packet_staging)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 265, in test_concurrent_saved_same_intent_wins_before_packet_staging\n    try:result=operator.create(intent)\n               ~~~~~~~~~~~~~~~^^^^^^^^\n  File \"<reduced20-mutant>\", line 73, in create\nartifact_operator.ArtifactOperatorError: Document request conflicts with saved state.\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 266, in test_concurrent_saved_same_intent_wins_before_packet_staging\n    except module.ArtifactOperatorError as error:self.fail('Stored identical winner must replay: '+error.code)\n                                                 ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Stored identical winner must replay: request_conflict\n\n----------------------------------------------------------------------\nRan 1 test in 0.184s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "replay before relaunch lookup",
      "test": "test_replay_uses_stored_intent_before_prepare_or_resolver",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_replay_uses_stored_intent_before_prepare_or_resolver (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_replay_uses_stored_intent_before_prepare_or_resolver)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 150, in test_replay_uses_stored_intent_before_prepare_or_resolver\n    try:result=operator.create(intent)\n               ~~~~~~~~~~~~~~~^^^^^^^^\n  File \"<reduced20-mutant>\", line 20, in create\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_operator.py\", line 75, in resolve_default_artifact_author\n    raise ArtifactOperatorError('no_author_available', cause=cause, author_name=name, examined_roles=examined)\nartifact_operator.ArtifactOperatorError: No supported live author is available for this session.\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 151, in test_replay_uses_stored_intent_before_prepare_or_resolver\n    except module.ArtifactOperatorError as error:self.fail('Identical replay refused: '+error.code)\n                                                 ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Identical replay refused: no_author_available\n\n----------------------------------------------------------------------\nRan 1 test in 0.314s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "create caller boundary",
      "test": "test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 233, in test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect\n    with case.service._boundary(),self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(intent)\n                                  ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactOperatorError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.164s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "public status serialized",
      "test": "test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 241, in test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect\n    self.assertTrue(seen);self.assertTrue(all(pair==(True,True) for pair in seen))\n                          ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: False is not true\n\n----------------------------------------------------------------------\nRan 1 test in 0.151s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "create202",
      "test": "test_successful_create_replay_conflict_and_capture_stop_guard",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_successful_create_replay_conflict_and_capture_stop_guard (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_successful_create_replay_conflict_and_capture_stop_guard)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 190, in test_successful_create_replay_conflict_and_capture_stop_guard\n    first=operator.create(intent);self.assertTrue(first.created)\n                                  ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\nAssertionError: False is not true\n\n----------------------------------------------------------------------\nRan 1 test in 0.150s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "capture current Stop guard",
      "test": "test_successful_create_replay_conflict_and_capture_stop_guard",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_successful_create_replay_conflict_and_capture_stop_guard (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_successful_create_replay_conflict_and_capture_stop_guard)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 199, in test_successful_create_replay_conflict_and_capture_stop_guard\n    with patch.object(case.artifacts,'put_packet',stop_after_packet),self.assertRaises(module.ArtifactOperatorError) as caught:operator.create(new_intent)\n                                                                     ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactOperatorError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.237s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "error durable state",
      "test": "test_summary_all_states_and_post_durable_cancel_failure",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_summary_all_states_and_post_durable_cancel_failure (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_summary_all_states_and_post_durable_cancel_failure)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 224, in test_summary_all_states_and_post_durable_cancel_failure\n    self.assertEqual(caught.exception.durability,'recorded');self.assertEqual(caught.exception.request['state'],'cancelled')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_recorded' != 'recorded'\n- not_recorded\n? ----\n+ recorded\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.135s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "Host guard",
      "test": "test_bad_host_and_duplicate_security_headers_refuse",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers={'x-session-token': 'OPERATOR_ONLY', 'origin': 'http://127.0.0.1:18300', 'host': 'attacker.invalid:18300'})\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 45, in test_bad_host_and_duplicate_security_headers_refuse\n    self.assertEqual(self.client.get(self.read,headers=headers).status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 200 != 403\n\n======================================================================\nFAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 46, in test_bad_host_and_duplicate_security_headers_refuse\n    self.assertEqual(self.calls,[])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\nAssertionError: Lists differ: [True] != []\n\nFirst list contains 1 additional elements.\nFirst extra element 0:\nTrue\n\n- [True]\n+ []\n\n----------------------------------------------------------------------\nRan 1 test in 0.022s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "bearer excluded",
      "test": "test_security_raw_header_matrix_envelopes_and_legacy_namespace",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_security_raw_header_matrix_envelopes_and_legacy_namespace (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_security_raw_header_matrix_envelopes_and_legacy_namespace) (headers={'x-session-token': 'OPERATOR_ONLY', 'origin': 'http://127.0.0.1:18300', 'authorization': 'Bearer seat'})\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 196, in test_security_raw_header_matrix_envelopes_and_legacy_namespace\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 404 != 403\n\n======================================================================\nFAIL: test_security_raw_header_matrix_envelopes_and_legacy_namespace (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_security_raw_header_matrix_envelopes_and_legacy_namespace) (headers=[('x-session-token', 'OPERATOR_ONLY'), ('authorization', 'Bearer x'), ('authorization', 'Bearer y')])\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 196, in test_security_raw_header_matrix_envelopes_and_legacy_namespace\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 404 != 403\n\n----------------------------------------------------------------------\nRan 1 test in 0.023s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "POST Origin",
      "test": "test_post_requires_origin_but_get_allows_absent_origin",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_post_requires_origin_but_get_allows_absent_origin (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_requires_origin_but_get_allows_absent_origin)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 37, in test_post_requires_origin_but_get_allows_absent_origin\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 200 != 403\n\n----------------------------------------------------------------------\nRan 1 test in 0.005s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "query token excluded",
      "test": "test_query_token_and_authorization_are_never_operator_fallback",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=('x-session-token', 'origin'))\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 30, in test_query_token_and_authorization_are_never_operator_fallback\n    self.assertEqual(response.status_code,403)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 405 != 403\n\n----------------------------------------------------------------------\nRan 1 test in 0.005s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "chunked cap",
      "test": "test_json_boundaries_chunked_body_and_scoped_errors",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_json_boundaries_chunked_body_and_scoped_errors (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_json_boundaries_chunked_body_and_scoped_errors)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 211, in test_json_boundaries_chunked_body_and_scoped_errors\n    self.assertEqual(response.status_code,413);self.assertEqual(response.json()['code'],'request_too_large')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 400 != 413\n\n----------------------------------------------------------------------\nRan 1 test in 0.007s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "duplicate JSON",
      "test": "test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='application/json', size=31)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 64, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint\n    self.assertEqual(response.status_code,code)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 200 != 400\n\n======================================================================\nFAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 65, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint\n    self.assertEqual(self.calls,[])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\nAssertionError: Lists differ: [True] != []\n\nFirst list contains 1 additional elements.\nFirst extra element 0:\nTrue\n\n- [True]\n+ []\n\n----------------------------------------------------------------------\nRan 1 test in 0.006s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "503 envelope preserved",
      "test": "test_fixed_error_codes_do_not_become_generic_500",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_fixed_error_codes_do_not_become_generic_500 (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_fixed_error_codes_do_not_become_generic_500) (code='storage_unavailable')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 259, in test_fixed_error_codes_do_not_become_generic_500\n    self.assertEqual(response.status_code,status,response.text);self.assertEqual(response.json()['code'],code)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 500 != 503 : {\"code\":\"unexpected_failure\",\"error\":\"Document operation failed.\",\"cause\":null,\"author_name\":null,\"examined_roles\":null,\"request_id\":null,\"durability\":null,\"request\":null}\n\n======================================================================\nFAIL: test_fixed_error_codes_do_not_become_generic_500 (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_fixed_error_codes_do_not_become_generic_500) (code='boundary_held')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 259, in test_fixed_error_codes_do_not_become_generic_500\n    self.assertEqual(response.status_code,status,response.text);self.assertEqual(response.json()['code'],code)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 500 != 503 : {\"code\":\"unexpected_failure\",\"error\":\"Document operation failed.\",\"cause\":null,\"author_name\":null,\"examined_roles\":null,\"request_id\":null,\"durability\":null,\"request\":null}\n\n----------------------------------------------------------------------\nRan 1 test in 0.166s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "404 domain code preserved",
      "test": "test_create_202_replay_200_validation_and_detail_errors",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_create_202_replay_200_validation_and_detail_errors (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_create_202_replay_200_validation_and_detail_errors) (changes=('session_id',))\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 239, in test_create_202_replay_200_validation_and_detail_errors\n    self.assertEqual(response.status_code,code,response.text);self.assertEqual(response.json()['code'],error_code)\n                                                              ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_found' != 'session_unknown'\n- not_found\n+ session_unknown\n\n\n======================================================================\nFAIL: test_create_202_replay_200_validation_and_detail_errors (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_create_202_replay_200_validation_and_detail_errors) (changes=('run_id',))\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 239, in test_create_202_replay_200_validation_and_detail_errors\n    self.assertEqual(response.status_code,code,response.text);self.assertEqual(response.json()['code'],error_code)\n                                                              ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'not_found' != 'run_unknown'\n- not_found\n+ run_unknown\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.186s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "source UID proof",
      "test": "test_capture_single_read_identity_attribution_and_deep_detachment",
      "killed": true,
      "failures": 1,
      "errors": 1,
      "evidence": "assertion",
      "output": "======================================================================\nERROR: test_capture_single_read_identity_attribution_and_deep_detachment (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_capture_single_read_identity_attribution_and_deep_detachment)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 105, in test_capture_single_read_identity_attribution_and_deep_detachment\n    self.assertEqual(caught.exception.code,'source_unavailable')\n                     ^^^^^^^^^^^^^^^^\nAttributeError: '_AssertRaisesContext' object has no attribute 'exception'\n\n======================================================================\nFAIL: test_capture_single_read_identity_attribution_and_deep_detachment (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_capture_single_read_identity_attribution_and_deep_detachment) (field='uid')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 103, in test_capture_single_read_identity_attribution_and_deep_detachment\n    with self.subTest(field=field),self.assertRaises(module.ArtifactSourceError) as caught:\n                                   ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactSourceError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.072s\n\nFAILED (failures=1, errors=1)\n"
    },
    {
      "label": "source caps",
      "test": "test_cap_precheck_exact_bytes_unicode_escaping_and_count",
      "killed": true,
      "failures": 1,
      "errors": 1,
      "evidence": "assertion",
      "output": "======================================================================\nERROR: test_cap_precheck_exact_bytes_unicode_escaping_and_count (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_cap_precheck_exact_bytes_unicode_escaping_and_count)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 143, in test_cap_precheck_exact_bytes_unicode_escaping_and_count\n    self.assertEqual(caught.exception.code,'source_too_large')\n                     ^^^^^^^^^^^^^^^^\nAttributeError: '_AssertRaisesContext' object has no attribute 'exception'\n\n======================================================================\nFAIL: test_cap_precheck_exact_bytes_unicode_escaping_and_count (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_cap_precheck_exact_bytes_unicode_escaping_and_count) (kind='x')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 142, in test_cap_precheck_exact_bytes_unicode_escaping_and_count\n    with self.subTest(kind=text[:1]),self.assertRaises(module.ArtifactSourceError) as caught:module.check_packet_bounds(packet)\n                                     ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactSourceError not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.012s\n\nFAILED (failures=1, errors=1)\n"
    },
    {
      "label": "metadata allowlist",
      "test": "test_projection_allowlist_preserves_literal_text_not_server_metadata",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_projection_allowlist_preserves_literal_text_not_server_metadata (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_projection_allowlist_preserves_literal_text_not_server_metadata)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 70, in test_projection_allowlist_preserves_literal_text_not_server_metadata\n    self.assertEqual(message['provenance'],{'session_id':1,'run_id':'a'*32})\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: {'ses[52 chars]aaaa', 'token': 'PRIVATE_TOKEN', 'launch_nonce[14 chars]NCE'} != {'ses[52 chars]aaaa'}\n- {'launch_nonce': 'PRIVATE_NONCE',\n-  'run_id': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',\n? ^\n\n+ {'run_id': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'session_id': 1}\n? ^                                             +++++++++++++++++\n\n-  'session_id': 1,\n-  'token': 'PRIVATE_TOKEN'}\n\n----------------------------------------------------------------------\nRan 1 test in 0.001s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "source full walk seam",
      "test": "test_capture_single_read_identity_attribution_and_deep_detachment",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_capture_single_read_identity_attribution_and_deep_detachment (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_capture_single_read_identity_attribution_and_deep_detachment)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 96, in test_capture_single_read_identity_attribution_and_deep_detachment\n    snapshot.assert_called_once();walk.assert_called_once()\n                                  ~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 965, in assert_called_once\n    raise AssertionError(msg)\nAssertionError: Expected '_packet_scope' to have been called once. Called 0 times.\n\n----------------------------------------------------------------------\nRan 1 test in 0.073s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "snapshot deep detach",
      "test": "test_snapshot_selected_is_detached_and_channel_exact",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_snapshot_selected_is_detached_and_channel_exact (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_selected_is_detached_and_channel_exact)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 28, in test_snapshot_selected_is_detached_and_channel_exact\n    self.assertEqual(messages.get_snapshot(first['id'])['metadata']['nested']['values'],[1])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Lists differ: [1, 2] != [1]\n\nFirst list contains 1 additional elements.\nFirst extra element 1:\n2\n\n- [1, 2]\n+ [1]\n\n----------------------------------------------------------------------\nRan 1 test in 0.003s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "snapshot typed refusal",
      "test": "test_snapshot_missing_and_duplicate_ids_never_return_partial",
      "killed": true,
      "failures": 0,
      "errors": 1,
      "evidence": "ERROR-only, weaker typed-contract evidence",
      "output": "======================================================================\nERROR: test_snapshot_missing_and_duplicate_ids_never_return_partial (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_missing_and_duplicate_ids_never_return_partial) (ids=[0, 999999])\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_builder.py\", line 47, in test_snapshot_missing_and_duplicate_ids_never_return_partial\n    with self.subTest(ids=ids),self.assertRaises(MessageSnapshotUnavailable):messages.snapshot_selected('review',ids)\n                                                                             ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in snapshot_selected\nValueError: Selected messages are unavailable.\n\n----------------------------------------------------------------------\nRan 1 test in 0.002s\n\nFAILED (errors=1)\n"
    },
    {
      "label": "Stop policy wired",
      "test": "test_engine_stop_cancels_mid_run_artifact_and_fences_claim",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_engine_stop_cancels_mid_run_artifact_and_fences_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_engine_stop_cancels_mid_run_artifact_and_fences_claim)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 22, in test_engine_stop_cancels_mid_run_artifact_and_fences_claim\n    self.assertEqual((row['state'],row['reason']),('cancelled','source_stopped'))\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Tuples differ: ('queued', 'queued') != ('cancelled', 'source_stopped')\n\nFirst differing element 0:\n'queued'\n'cancelled'\n\n- ('queued', 'queued')\n+ ('cancelled', 'source_stopped')\n\n----------------------------------------------------------------------\nRan 1 test in 0.154s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "Stop fence effect",
      "test": "test_engine_stop_cancels_mid_run_artifact_and_fences_claim",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_engine_stop_cancels_mid_run_artifact_and_fences_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_engine_stop_cancels_mid_run_artifact_and_fences_claim)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 24, in test_engine_stop_cancels_mid_run_artifact_and_fences_claim\n    self.assertIn(transport['state'],('cancelling','cancelled'))\n    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'dispatched' not found in ('cancelling', 'cancelled')\n\n----------------------------------------------------------------------\nRan 1 test in 0.159s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "retained Stop repair",
      "test": "test_reconcile_repairs_retained_artifacts_without_review_receipts",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_reconcile_repairs_retained_artifacts_without_review_receipts (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_reconcile_repairs_retained_artifacts_without_review_receipts)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 57, in test_reconcile_repairs_retained_artifacts_without_review_receipts\n    self.assertEqual(case.artifacts.get_request(audit['request_id'])['reason'],'source_stopped')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'queued' != 'source_stopped'\n- queued\n+ source_stopped\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.161s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "historical index scans",
      "test": "test_historical_stops_never_scan_artifact_index_per_claim",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_historical_stops_never_scan_artifact_index_per_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_historical_stops_never_scan_artifact_index_per_claim)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 112, in test_historical_stops_never_scan_artifact_index_per_claim\n    scan.assert_not_called()\n    ~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 947, in assert_not_called\n    raise AssertionError(msg)\nAssertionError: Expected 'channel_names' to not have been called. Called 80 times.\nCalls: [call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call(),\n call()].\n\n----------------------------------------------------------------------\nRan 1 test in 0.278s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "held owner Stop containment",
      "test": "test_held_artifact_owner_does_not_abort_stop_or_other_sessions",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_held_artifact_owner_does_not_abort_stop_or_other_sessions (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_held_artifact_owner_does_not_abort_stop_or_other_sessions)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 85, in test_held_artifact_owner_does_not_abort_stop_or_other_sessions\n    try:result=case.engine.stop_session(session['id'])\n               ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py\", line 165, in stop_session\n    self._trigger.queue.cancel_run(session['run_id'], session['stop_id'], fence_artifacts=True)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in cancel_run\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 884, in fence_source_requests\n    for channel in self.store.channel_names():\n                   ~~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_store.py\", line 1579, in channel_names\n    self._check_index()\n    ~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_store.py\", line 966, in _check_index\n    raise ArtifactUnavailable(self._held) from None\nartifact_store.ArtifactUnavailable: Saved artifact index is held; repair storage and restart.\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 86, in test_held_artifact_owner_does_not_abort_stop_or_other_sessions\n    except artifact_store.ArtifactUnavailable:self.fail('Held artifact owner must not abort durable session Stop')\n                                              ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Held artifact owner must not abort durable session Stop\n\n----------------------------------------------------------------------\nRan 1 test in 0.164s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "retained held owner containment",
      "test": "test_held_owner_allows_ordinary_claim_after_historical_stop",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_held_owner_allows_ordinary_claim_after_historical_stop (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_held_owner_allows_ordinary_claim_after_historical_stop)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 103, in test_held_owner_allows_ordinary_claim_after_historical_stop\n    try:claimed=case.trigger.queue.claim(other,'ordinary-consumer')\n                ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py\", line 157, in claim\n    unpublished_holds = self._reconcile()\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py\", line 104, in _reconcile\n    self._repair_retained_artifact_stops()\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"<reduced20-mutant>\", line 20, in _repair_retained_artifact_stops\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 916, in fence_retained_source_requests\n    row = self.store.get_request(_hex(identifier))\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_store.py\", line 1407, in get_request\n    self._check_index()\n    ~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_store.py\", line 966, in _check_index\n    raise ArtifactUnavailable(self._held) from None\nartifact_store.ArtifactUnavailable: Saved artifact index is held; repair storage and restart.\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 104, in test_held_owner_allows_ordinary_claim_after_historical_stop\n    except artifact_store.ArtifactUnavailable:self.fail('Held artifact owner must not abort ordinary claim')\n                                              ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Held artifact owner must not abort ordinary claim\n\n----------------------------------------------------------------------\nRan 1 test in 0.231s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "Stop reports separate",
      "test": "test_artifact_fences_are_separate_from_review_stop_outcome",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_artifact_fences_are_separate_from_review_stop_outcome (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_artifact_fences_are_separate_from_review_stop_outcome)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 130, in test_artifact_fences_are_separate_from_review_stop_outcome\n    self.assertEqual(status['state'],'stopped')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'stopping' != 'stopped'\n- stopping\n+ stopped\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.183s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "retained repair bounded rotation",
      "test": "test_retained_repair_budget_rotates_without_starving_later_requests",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_retained_repair_budget_rotates_without_starving_later_requests (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_retained_repair_budget_rotates_without_starving_later_requests)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 124, in test_retained_repair_budget_rotates_without_starving_later_requests\n    self.assertEqual(len(set(batches[0]+batches[1])),101)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 100 != 101\n\n----------------------------------------------------------------------\nRan 1 test in 0.201s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "optional repair held catalog",
      "test": "test_optional_retained_repair_respects_held_channel_startup",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_optional_retained_repair_respects_held_channel_startup (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_optional_retained_repair_respects_held_channel_startup)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 139, in test_optional_retained_repair_respects_held_channel_startup\n    try:case.trigger.queue.repair_artifact_stops()\n        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"<reduced20-mutant>\", line 4, in repair_artifact_stops\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\contextlib.py\", line 141, in __enter__\n    return next(self.gen)\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py\", line 84, in _channel_boundary\n    policy = self._channel_policy() if self._channel_policy else None\n             ~~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\nchannel_lifecycle.ChannelUnavailable: held channel\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 140, in test_optional_retained_repair_respects_held_channel_startup\n    except ChannelUnavailable:self.fail('Optional artifact repair must not abort held-channel startup')\n                              ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Optional artifact repair must not abort held-channel startup\n\n----------------------------------------------------------------------\nRan 1 test in 0.158s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "empty artifact report no reads",
      "test": "test_no_artifact_stop_report_does_not_read_transport",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_no_artifact_stop_report_does_not_read_transport (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_no_artifact_stop_report_does_not_read_transport)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 147, in test_no_artifact_stop_report_does_not_read_transport\n    self.assertEqual(status,{'warning':None,'unconfirmed_dispatch_ids':[]})\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: {'warning': 'artifact_fence_failed', 'unconfirmed_dispatch_ids': []} != {'warning': None, 'unconfirmed_dispatch_ids': []}\n- {'unconfirmed_dispatch_ids': [], 'warning': 'artifact_fence_failed'}\n?                                             ^^^^^^^^^^^ -----------\n\n+ {'unconfirmed_dispatch_ids': [], 'warning': None}\n?                                             ^^^\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.158s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "None artifact owner",
      "test": "test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 153, in test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim\n    self.assertTrue(result['stop_id']);self.assertIsNone(result['artifact_cancellation']['warning'])\n                                       ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'artifact_fence_failed' is not None\n\n----------------------------------------------------------------------\nRan 1 test in 0.168s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "all artifact Stop faults contained",
      "test": "test_all_artifact_policy_errors_are_contained_after_durable_stop",
      "killed": true,
      "failures": 4,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_all_artifact_policy_errors_are_contained_after_durable_stop (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_all_artifact_policy_errors_are_contained_after_durable_stop) (error='ArtifactConflict')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 167, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    try:result=case.engine.stop_session(session['id'])\n               ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py\", line 165, in stop_session\n    self._trigger.queue.cancel_run(session['run_id'], session['stop_id'], fence_artifacts=True)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in cancel_run\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\nartifact_store.ArtifactConflict: conflict\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 168, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    except Exception as escaped:self.fail('Artifact fault escaped durable Stop: '+type(escaped).__name__)\n                                ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Artifact fault escaped durable Stop: ArtifactConflict\n\n======================================================================\nFAIL: test_all_artifact_policy_errors_are_contained_after_durable_stop (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_all_artifact_policy_errors_are_contained_after_durable_stop) (error='ArtifactValidationError')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 167, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    try:result=case.engine.stop_session(session['id'])\n               ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py\", line 165, in stop_session\n    self._trigger.queue.cancel_run(session['run_id'], session['stop_id'], fence_artifacts=True)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in cancel_run\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\nartifact_store.ArtifactValidationError: invalid\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 168, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    except Exception as escaped:self.fail('Artifact fault escaped durable Stop: '+type(escaped).__name__)\n                                ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Artifact fault escaped durable Stop: ArtifactValidationError\n\n======================================================================\nFAIL: test_all_artifact_policy_errors_are_contained_after_durable_stop (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_all_artifact_policy_errors_are_contained_after_durable_stop) (error='KeyError')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 167, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    try:result=case.engine.stop_session(session['id'])\n               ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py\", line 165, in stop_session\n    self._trigger.queue.cancel_run(session['run_id'], session['stop_id'], fence_artifacts=True)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in cancel_run\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\nKeyError: 'session_id'\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 168, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    except Exception as escaped:self.fail('Artifact fault escaped durable Stop: '+type(escaped).__name__)\n                                ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Artifact fault escaped durable Stop: KeyError\n\n======================================================================\nFAIL: test_all_artifact_policy_errors_are_contained_after_durable_stop (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_all_artifact_policy_errors_are_contained_after_durable_stop) (error='RuntimeError')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 167, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    try:result=case.engine.stop_session(session['id'])\n               ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py\", line 165, in stop_session\n    self._trigger.queue.cancel_run(session['run_id'], session['stop_id'], fence_artifacts=True)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in cancel_run\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\nRuntimeError: owner read failure\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 168, in test_all_artifact_policy_errors_are_contained_after_durable_stop\n    except Exception as escaped:self.fail('Artifact fault escaped durable Stop: '+type(escaped).__name__)\n                                ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Artifact fault escaped durable Stop: RuntimeError\n\n----------------------------------------------------------------------\nRan 1 test in 0.659s\n\nFAILED (failures=4)\n"
    },
    {
      "label": "source Stop eligibility",
      "test": "test_queued_stopped_source_never_claims_even_when_repair_fails",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_queued_stopped_source_never_claims_even_when_repair_fails (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_queued_stopped_source_never_claims_even_when_repair_fails)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 187, in test_queued_stopped_source_never_claims_even_when_repair_fails\n    self.assertIsNone(case.trigger.queue.claim(case.instance,'late-worker'))\n    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: {'envelope': {'sender': '?', 'text': '', 'channel': 'review', 'dispatch_id': '06c8c75e43875a13b474bc5744f9065e', 'purpose': 'artifact-v1', 'artifact_request_id': '74183615ec514b2a89131973bc1d20ea', 'artifact_attempt_id': 'ac7bf8fdd81c51c38d3d405c77968b3c', 'artifact_brief_id': 'e9b6a851aa2e5ff1ad7e69532101e24c', 'artifact_scope_sha256': '63419490b880539fc770f89b3ec2fc20172e4786c680f8a48e0f9f5e8643a65e', 'target_identity_id': '39cb8195bd374663a8ea95f666d3f890', 'target_agent_name': 'cli-4d8efa15-02d4a00bce13', 'created_at': 1793048257.5637732}, 'state': 'dispatched', 'consumer_id': 'late-worker', 'events': [{'state': 'queued', 'at': 1793048257.5637755, 'error': ''}, {'state': 'dispatched', 'at': 1793048257.5900586, 'error': ''}]} is not None\n\n----------------------------------------------------------------------\nRan 1 test in 0.179s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "queued retained repair",
      "test": "test_queued_stopped_source_never_claims_even_when_repair_fails",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_queued_stopped_source_never_claims_even_when_repair_fails (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_queued_stopped_source_never_claims_even_when_repair_fails)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 190, in test_queued_stopped_source_never_claims_even_when_repair_fails\n    self.assertEqual(case.artifacts.get_request(intent['request_id'])['reason'],'source_stopped')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'queued' != 'source_stopped'\n- queued\n+ source_stopped\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.163s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "capability drift at prepare",
      "test": "test_identical_orphan_retry_succeeds_and_prepare_capability_off_is_typed",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_identical_orphan_retry_succeeds_and_prepare_capability_off_is_typed (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_identical_orphan_retry_succeeds_and_prepare_capability_off_is_typed)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 309, in test_identical_orphan_retry_succeeds_and_prepare_capability_off_is_typed\n    self.assertEqual((caught.exception.code,caught.exception.cause),('no_author_available','capability_off'))\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Tuples differ: ('request_conflict', None) != ('no_author_available', 'capability_off')\n\nFirst differing element 0:\n'request_conflict'\n'no_author_available'\n\n- ('request_conflict', None)\n+ ('no_author_available', 'capability_off')\n\n----------------------------------------------------------------------\nRan 1 test in 0.096s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "None retained artifact owner",
      "test": "test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 155, in test_bound_none_artifact_policy_is_no_effect_on_stop_and_claim\n    self.assertIsNone(case.engine.stop_status(session['id'])['artifact_cancellation']['warning'])\n    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'artifact_fence_failed' is not None\n\n----------------------------------------------------------------------\nRan 1 test in 0.162s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "typed None enqueue",
      "test": "test_none_policy_enqueue_uses_typed_conflict",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_none_policy_enqueue_uses_typed_conflict (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_none_policy_enqueue_uses_typed_conflict)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 241, in test_none_policy_enqueue_uses_typed_conflict\n    try:case.trigger.queue.enqueue(instance,envelope)\n        ~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 19, in enqueue\nAttributeError: 'NoneType' object has no attribute 'validate_enqueue'\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 243, in test_none_policy_enqueue_uses_typed_conflict\n    except Exception as error:self.fail('Missing policy must refuse with QueueConflict: '+type(error).__name__)\n                              ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Missing policy must refuse with QueueConflict: AttributeError\n\n----------------------------------------------------------------------\nRan 1 test in 0.157s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "prepared Stop retry",
      "test": "test_prepared_without_transport_is_ineligible_after_source_stop",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_prepared_without_transport_is_ineligible_after_source_stop (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_prepared_without_transport_is_ineligible_after_source_stop)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 213, in test_prepared_without_transport_is_ineligible_after_source_stop\n    self.assertEqual(case.artifacts.get_request(intent['request_id'])['reason'],'source_stopped')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: None != 'source_stopped'\n\n----------------------------------------------------------------------\nRan 1 test in 0.109s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "clean first warning eviction",
      "test": "test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow) (all_pending=False)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 258, in test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow\n    else:self.assertIn(ids[0],queue._artifact_stop_reports);self.assertNotIn(ids[1],queue._artifact_stop_reports)\n         ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'cd11fb1a52e345d3ad0d78988b11c1ea' not found in {'1931bb30d121477ca2eb05bba26b5834': {'dispatch_ids': [], 'warning': None, 'confirmed': False}, '1143771d75b64040bf34b99b15187b8e': {'dispatch_ids': ['4fa1950fd72d41ec97b2b1d40551248c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '765cea9cdca0409cb0fba13caf20d80d': {'dispatch_ids': ['88eaed05c17d4d45885e74f252ac207c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '47db5380b7134242b36d7d88dbc9f3dd': {'dispatch_ids': ['b2889c2a9904423c9a44e8172eb46568'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '1ba85230308242e78300feeca91464bd': {'dispatch_ids': ['9dd75e691c10426689895b0aca005cda'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e6d12619edff4241b36bf33ceadb3fad': {'dispatch_ids': ['175898f18d3a44bcb21eae96196b4480'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '752d63887fee4d509534b597d1b9e9b7': {'dispatch_ids': ['8cc0834050184c329ce3766b4aaea82b'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'cb3cea2f61f246ecb6afbd00dc867cc0': {'dispatch_ids': ['c30e263c742a4345af930fdee633beb7'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '49e3e44cea8042a2adba42e35588438f': {'dispatch_ids': ['17e5fd9aaa0a4bf3954d0f9680f6a161'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '4bdf0cdd98de4cd78fbd36be4f0f2513': {'dispatch_ids': ['a44aad62d56d4869a335e6705d1cc315'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'c2f8bfb43a4744309ed9e9a3e762c1cc': {'dispatch_ids': ['67dbc7aa8f6a47fcb85043ae9e2a3113'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '76fc3676d3714844877e010ced31b266': {'dispatch_ids': ['ac929ff9788d4508af965977164b8abc'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '17996704b9e64716be6fda7d74eee315': {'dispatch_ids': ['fe760b82d0d64d82869ef8f0115382e3'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'b5da17baf875461599b573833a7215a7': {'dispatch_ids': ['ba9a4bed744a4173ae23474ae03671a1'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '6590e354e3314d11ad358f5aad1b752b': {'dispatch_ids': ['1b36e0cc3e9b46fe801f651ee29219c5'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '07d9f51a13b74a3a8dbfb87d42784060': {'dispatch_ids': ['f80ea66f3d9645409e860759cdf06d2a'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '41c4cca219f344c298b179201f903d21': {'dispatch_ids': ['817a071e88dd4221bb79547b45760340'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e87247a2af684c1080393481882569d1': {'dispatch_ids': ['fcbe85f0def4494ca13bbd264c89016e'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '9c7dd8c422f344318aa45ebbd6274e20': {'dispatch_ids': ['7b61eabcbd304e82899b1ac5bfeacbe7'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'b762141eaf5b49e694127f2939b24092': {'dispatch_ids': ['9e335903dd20460b880fb4ebe4d16c60'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'a401e88df7bb4b708fc706aaf8d26b96': {'dispatch_ids': ['d22ffe015318420a88238d4c911f5366'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'b9c285382c374d458359a8b6131bd615': {'dispatch_ids': ['bf66b1fdc7d444278136bdf6a407ff79'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e6a25febd77e4cb985685581105005be': {'dispatch_ids': ['9f3b2591f1c8477e8d49cb743e7d2625'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '028bd299c471495eaf4e3be6f6e5ec24': {'dispatch_ids': ['951b8afdc9c6497a86ed9c2dc533378e'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'a58a529b9b924dd286668040e56fad83': {'dispatch_ids': ['1a891d2c97ab47349380cb785783f19a'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '08a4796b9eeb471db01bae7e5b17bfce': {'dispatch_ids': ['ec536e09d39e4e199125495578777ad5'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'cc2127a04fb94d58a7f3277d8fc46539': {'dispatch_ids': ['a014228e43374db1978fd7186aa9e6f8'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '0ad5441c1847406994d8ae4d7738ddb3': {'dispatch_ids': ['45f4e1142028430b8fed333895cc65ba'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '2e10dd88034345b0842e440b900fc86b': {'dispatch_ids': ['662b18df376347baa31eb0ca9ad5bd79'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '2cbf0df5a06a42238174548f498b548f': {'dispatch_ids': ['efef0dfc8eb64e0cb204d4e7068117e5'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '29cad94203264fc5ae8c8a6f8adf05fc': {'dispatch_ids': ['a636fb3beee646e58a4737e367f08e80'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'b5b3bca3cbac47e0abe5bafc850167b1': {'dispatch_ids': ['60c6224e65f6409e868b4b7ac30ce6c4'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e9289472cddd48a7a87abe3ea2c5f698': {'dispatch_ids': ['1bf253e70fc54daabe076ffa3c688d26'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '6d62648b7808438eb8fbb2be5bb25f97': {'dispatch_ids': ['916930abff7e416fad0ff78074bf2314'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '6fa3a0fe191047d280214a04bc808c09': {'dispatch_ids': ['a07a203648e2416883f3aa2cd24b08e9'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'f726f77f9d5a498598fd0ff82dd7f60d': {'dispatch_ids': ['98320bc591b54a32ba31d7935f59276b'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '51ad09a1b05f4859a6ba6752eb8e71cf': {'dispatch_ids': ['c7e9697a9922444b87391b813afcfd26'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '278ee5e2c22a4199ad8087d7140726ce': {'dispatch_ids': ['cc1c7075c68e4a38abf943d4394ecce6'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '8ecc958fb0d444d5a09a9baad0e47025': {'dispatch_ids': ['53198bedde9645818dd5a122f3a9ce1b'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '2e6098d402aa407f84ec437c239e1e94': {'dispatch_ids': ['e4b5dbed8d2545d887a9566f26d1cbf5'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'fd6e14d394b442e3b6128b48bf53a7a0': {'dispatch_ids': ['94361db81b1247e59b646c8f7bea39f5'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '846d604c30134d01a798870082148057': {'dispatch_ids': ['06d2a262d5764fcdb1d683e5a968a159'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '61a4df2864ef486ab9c5682a53627a23': {'dispatch_ids': ['ec3f50a059cb47ad841e8f1a47ea6c4c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'c7f1ff2ac7dd4479a4bd21f2115b4d73': {'dispatch_ids': ['288d2fb369d946f2afc876668c9a5008'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'c9efd5c908df4573ad76dd8c8f74a347': {'dispatch_ids': ['9b7ded77c8ec46038b71745bf57c20a9'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e9a857899d6c4483a6246a902eb28f4d': {'dispatch_ids': ['bba252ecc4a84f9abee002c039671490'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '8149ef2de4ad40458f69eaa50196feb5': {'dispatch_ids': ['76081c7ced97447eb4f1aa057b825962'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'ffd6f9b64a72422ca746df6ee963ff24': {'dispatch_ids': ['a1becee6049f4f27a0902d1362932151'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '9c45131dcabd4b828dc675a9a8b7c3ae': {'dispatch_ids': ['179d32e68e054729bd8c86d37a0fa076'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '1f217895a40142dfb2180e3b582eae1b': {'dispatch_ids': ['13f927ae186b4b0194e7a5d68f760938'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '63a8617b9a3d4093ac11a1f25df001be': {'dispatch_ids': ['93a5705f250548a895c3c272c56f11b8'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'bba2e6482253470585ad356f95a08a6e': {'dispatch_ids': ['34e245861db3407ea1c64af947910572'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '56ee1e4d67de4cff99cd781d5debc9bf': {'dispatch_ids': ['2a93a08051024e1b92d3f8f1addfd956'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '6f9bdc499a0740c8aaf24182775c9adb': {'dispatch_ids': ['79ab76d952e64707b51a943542b1cfda'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '12309e1718ce45d3b2643142cc267dfd': {'dispatch_ids': ['c7c61384a65f42e1bb32f54c94bb647b'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'ce9d12a686e34bbdb5ff80bfd693ff92': {'dispatch_ids': ['049703b3439a4fe88c4c4c0c6490eeb1'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '91b585cef5754bdbb4397344b2d77e98': {'dispatch_ids': ['0014ce86448545aeba84c106597c3068'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '0b15f9dec7c9472aa1e701de6032dc9d': {'dispatch_ids': ['56d8c5da6ccb4551ba7f565b72b2073d'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'abf84584f4fa45668aa67f19c3002931': {'dispatch_ids': ['339fee7fd5cd4c02804bff8df41e0ea4'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'b0bf2b8006a643c8843228c370fdad98': {'dispatch_ids': ['730afa08edc749719db1be99f7b7fd97'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '3dd067c4efda4a71bf72ad160f34b484': {'dispatch_ids': ['d48e701602eb42d6a66a1eea06445581'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '0aeb124e9692495c84248e70a6b1f9d6': {'dispatch_ids': ['3f3571d5a71f4c8ca71d1763fd8c1dba'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'd671de8fc03f492ca437b0e121551243': {'dispatch_ids': ['6219f417453a4072913068dfa0228b03'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e71b7f5c78a1449dbcb02dee7843d85b': {'dispatch_ids': ['478fd56ab2c049f9a2f06062a7597a2c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '8e5607f22e2b44809d08e6331b381bb9': {'dispatch_ids': ['0ebf7440bc7f4db1a1024cac03724495'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'd6f4e6b2f8d1414897c89d6c7797e30a': {'dispatch_ids': ['172367e624604e068a9abfc2150aad37'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '5d070d64e5254330b142e67bbda1b051': {'dispatch_ids': ['e68a04fe99724c3cbe35cee174595abd'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '0ae60ed277b9417cb15d9c3b512eb20b': {'dispatch_ids': ['6a9c0ecfde3046ddbd3a90191120fff6'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '004bd9a1124642b79d51ea2ed9f568d3': {'dispatch_ids': ['81877d035b8a4d98971b0390f40d3cb0'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'cf15bc89f17747738a5bc3d721803cc1': {'dispatch_ids': ['f21ec6efd6ef450f954d3a8f69c0635c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '1ae07ca9510e4893bb90e12e772510a1': {'dispatch_ids': ['bcf17132f2ef4d52ac5a9af85cff639f'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'fd349622d9754d77beadc3e136c4f322': {'dispatch_ids': ['d5c06f70b4494c5981c608e416884e9c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e15b6988bb8a4c00bee501c182ad9d02': {'dispatch_ids': ['36c91d102f8a47e390911a8234646bb4'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '25d865903f44482a88fec02892859e0a': {'dispatch_ids': ['c12a34af0c2f4bdb8d32013f6dfa0edf'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '867a0b759a0640f69dd46fb5ba411970': {'dispatch_ids': ['e7e7c45a5dee4edca42288406fb452a7'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'e22fe31ca32541618cc9c02d7be64cec': {'dispatch_ids': ['49836051ddb64464a71324e4602088f6'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'd4265332c05c413889c88ba08a8b0552': {'dispatch_ids': ['a5bf6757740d4c828bb6f2eafa1f86f1'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'b53cfe2387574e1c949b4029ae407a55': {'dispatch_ids': ['093b8329b21142f7b24ae5b6fae800d8'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '7f9a24c9cf7647bea4764a89ff572986': {'dispatch_ids': ['23faef20cd9a47be8cef78c83b3b7861'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '891dff3cb5644f52aed7381cf63dcd29': {'dispatch_ids': ['48d60c5ede9c478abf1872f1b2be452a'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '8e84c4d2ef644eb0a97fb5a311a57e35': {'dispatch_ids': ['7188433e6722459298cdd36440bd05fd'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '409aaa019f6e406c9a38f988a380f322': {'dispatch_ids': ['2346afe749254d5c8cf4875222453228'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '8a9e7c0aca374d04973fccb49ba85203': {'dispatch_ids': ['4c820cca69b2459aaa561f203e33546e'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '46788382e9724a45a33e539373542e05': {'dispatch_ids': ['15f8c41bf6804f059e5127e405f38602'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'a8e10f188a194ba29239dfd53106cf9b': {'dispatch_ids': ['4bca081863ed49b0a630df661bab74a9'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '7fe11ba76e294498b3f85b655a3ff1b6': {'dispatch_ids': ['190ed5050c7d4762bfbe34427cbbd2ce'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '28890db2b24646af98d35fc0d6a2b7b1': {'dispatch_ids': ['2354ff9016dd4e739aa8117cb8bcc377'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '06aa363261a646cb9397c29f082b1725': {'dispatch_ids': ['4961a1b2ebd745b2aafd8d21b7a14026'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '7690531be8894866a5ebc55a306d2914': {'dispatch_ids': ['82c23634b8b34a75865faea483704c22'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '54a8400ad1eb448b8b4d45f022ca0b6f': {'dispatch_ids': ['8a007be2046b465091660003295d702b'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'ae34b7549278447c8398a9c16f925bc6': {'dispatch_ids': ['cea74b6535064608a87c33d887fe2455'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '41acfa6047074dabb1cdf771eb651e43': {'dispatch_ids': ['67c43cdd7f244fd092f695b47627e4ff'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'db22ee33684b430888972aed581938bf': {'dispatch_ids': ['ccb8900ceba44133b55ca16f799466ed'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '200bedfd84474246ab2169478dc361f0': {'dispatch_ids': ['28222c5f27094c70878576ee069fd2b2'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '4d852c4351bb4c6791ab4d42f09ba67b': {'dispatch_ids': ['a146db370b3544ff8ba06e0423e74429'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '2b07401358864325a11f60223952024a': {'dispatch_ids': ['70eb9a0b0a63434fad0318828faa237d'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'a030e6f4927a4bc8a5d37b7d68969e7c': {'dispatch_ids': ['6b5c2fc978f34c9da492b7e85b4a22b9'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '7b0a9c7abf0343349c60b5d9871d6fbd': {'dispatch_ids': ['b93a4f1e978041598aef5ad1bb909f16'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '7d90141193594a86ae62ada2ee9f7de2': {'dispatch_ids': ['22acca8b40e04f3f97511585f473070a'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '9a1a6a84ad2445e8be85472dd0658017': {'dispatch_ids': ['67d0e33b543e4d26ba5289c6b0b79444'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'c771dded31974b6abbe1763a5966edcc': {'dispatch_ids': ['c6084fa6ff5948c39ea4f0593d20414a'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '676325f0eef54a789a07af6833089243': {'dispatch_ids': ['e82d692c78ea4cd08fb17c38d3536f9a'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '2d3ecd3e0ea44797a5c582f9f28d3fa1': {'dispatch_ids': ['969e49f1d1644c8199f6eae9a3883f4d'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '54ac8f801b7d467a803c90f5ffc4a0e5': {'dispatch_ids': ['a224cea42ba24e96b3b5ceb7866866d7'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '889b76f4200e4b27a6ab6c41e88a1d85': {'dispatch_ids': ['64e369a2ca854d0da710e9fc768cc23f'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'f7f323551f4941ecb155776134b885d5': {'dispatch_ids': ['46eac6188b3b440180a70094ea9e342a'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '2dc92cc361764c7ca0c901a019ab0f93': {'dispatch_ids': ['9c81c72fcf464f0ba4078aa7a2e7f9a7'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '0eeb6136e8764808bfb0313a7878a683': {'dispatch_ids': ['4b6e29e3faeb457aaa46081f7e25ba02'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '3631e5926d7a496dbe798ec78c059b84': {'dispatch_ids': ['98f39e89ce62494e8e65d364001f546c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'cb9766308ce446b79da91e303a97a6ea': {'dispatch_ids': ['88aebcad343e43c1a054e3f346a2a1ff'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'cac7febfacdd44ac88247c9c9729e717': {'dispatch_ids': ['4c7192dacc4f4876bfe7705d7d089789'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '3c1bc19b65434c59a3947eee244444d4': {'dispatch_ids': ['46e07f1893ae4219808fb11086c07ada'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '50d4fc20dfe241b295a7dfac753eae9f': {'dispatch_ids': ['833d2903e35b42beb17486391f9eb842'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '6d263d22f4a847909bc0a873f626825c': {'dispatch_ids': ['b0ce0bd46ace4e048f4cccd1a0842383'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'eab82c09a99f48d6a83083ab20b16243': {'dispatch_ids': ['a615d3d655a9499fa739f701f9b74e10'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'dd2f8867f4994178864629dcca25ba86': {'dispatch_ids': ['15b62f6a31a4452880024a9dcb4fd4ab'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '20c477dd96df4d9ab03e4b46277ec4e3': {'dispatch_ids': ['046f0d863e9241a5a88907b52d486b90'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '780d26c9db4c43dfb0b2661902e14237': {'dispatch_ids': ['21090b631361487d8601147378cb1394'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'af6fcead7129467c9a77549fcc0a56b7': {'dispatch_ids': ['1690c6db83074a9da562d458d5d7df44'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '2e022fa667174eedb01c6177568f18bc': {'dispatch_ids': ['25e422ee60524a26a912f93f0f42a25d'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '9901de9d5049437bbbb7eb309a47ede8': {'dispatch_ids': ['f3822430eaaa4ad8b063de120872cfb3'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '1dd4efc8c27a44e08da46b48b6bcf45a': {'dispatch_ids': ['6083416e23de4877a827e3d8f54b247e'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '266200f78dc84a8d94ed88b955e3002e': {'dispatch_ids': ['6acc949b1874450db1023b23773fdfa3'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'eb051c082523417e89129ccba5d6d877': {'dispatch_ids': ['3e0cc849f41f4c54b744771e04716d75'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'f3f3e155c7d94179b02174f371a72f6d': {'dispatch_ids': ['aaccd3e1b43d46ee9f4e62d299f1c13c'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '83d5a4095fa94d00855088f587f5e2d6': {'dispatch_ids': ['99a42fc08af6446ba2c89c9885c0e220'], 'warning': 'transport_unconfirmed', 'confirmed': False}, 'f757bdb60ac243f9a8e705f70bd3c615': {'dispatch_ids': ['d96d470e68704918a7d5b702c576409e'], 'warning': 'transport_unconfirmed', 'confirmed': False}, '684a64a5aa684a499d131e4bff7ec81f': {'dispatch_ids': ['a2c68f4a339145968e1f97d1a488d486'], 'warning': 'transport_unconfirmed'}}\n\n----------------------------------------------------------------------\nRan 1 test in 0.333s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "warning overflow disclosure",
      "test": "test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow) (all_pending=True)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 257, in test_stop_report_eviction_keeps_pending_warnings_or_reports_overflow\n    if all_pending:self.assertEqual(queue.artifact_stop_status(ids[0])['warning'],'unconfirmed_overflow')\n                   ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: None != 'unconfirmed_overflow'\n\n----------------------------------------------------------------------\nRan 1 test in 0.296s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "retained inspection containment",
      "test": "test_optional_artifact_inspection_failure_does_not_abort_review_work",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_optional_artifact_inspection_failure_does_not_abort_review_work (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_optional_artifact_inspection_failure_does_not_abort_review_work)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 265, in test_optional_artifact_inspection_failure_does_not_abort_review_work\n    self.assertIsNone(case.trigger.queue.claim(other,'ordinary-worker'))\n                      ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py\", line 157, in claim\n    unpublished_holds = self._reconcile()\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py\", line 104, in _reconcile\n    self._repair_retained_artifact_stops()\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"<reduced20-mutant>\", line 9, in _repair_retained_artifact_stops\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\nOSError: inspection unavailable\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 267, in test_optional_artifact_inspection_failure_does_not_abort_review_work\n    except OSError:self.fail('Optional artifact inspection must not abort review work')\n                   ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Optional artifact inspection must not abort review work\n\n----------------------------------------------------------------------\nRan 1 test in 0.224s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "status inspection containment",
      "test": "test_optional_artifact_inspection_failure_does_not_abort_review_work",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_optional_artifact_inspection_failure_does_not_abort_review_work (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_optional_artifact_inspection_failure_does_not_abort_review_work)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 266, in test_optional_artifact_inspection_failure_does_not_abort_review_work\n    status=case.engine.stop_status(session['id'])\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\session_engine.py\", line 819, in stop_status\n    session['artifact_cancellation'] = self._trigger.queue.artifact_stop_status(session['run_id'])\n                                       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^\n  File \"<reduced20-mutant>\", line 11, in artifact_stop_status\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py\", line 200, in _repair_retained_artifact_stops\n    ids = [row['envelope']['artifact_request_id'] for row in self._queue.records()\n                                                             ~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\queue_coordinator.py\", line 200, in _repair_retained_artifact_stops\n    ids = [row['envelope']['artifact_request_id'] for row in self._queue.records()\n                                                             ~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1176, in __call__\n    return self._mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1180, in _mock_call\n    return self._execute_mock_call(*args, **kwargs)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\miniconda3\\Lib\\unittest\\mock.py\", line 1241, in _execute_mock_call\n    raise effect\nOSError: inspection unavailable\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_source_stop_wiring.py\", line 267, in test_optional_artifact_inspection_failure_does_not_abort_review_work\n    except OSError:self.fail('Optional artifact inspection must not abort review work')\n                   ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Optional artifact inspection must not abort review work\n\n----------------------------------------------------------------------\nRan 1 test in 0.230s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "ASCII content length",
      "test": "test_content_length_requires_ascii_decimal_and_head_errors_are_empty",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_content_length_requires_ascii_decimal_and_head_errors_are_empty (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_content_length_requires_ascii_decimal_and_head_errors_are_empty)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 81, in test_content_length_requires_ascii_decimal_and_head_errors_are_empty\n    self.assertEqual(response.status_code,400)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 500 != 400\n\n----------------------------------------------------------------------\nRan 1 test in 0.007s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "HEAD refusal body",
      "test": "test_content_length_requires_ascii_decimal_and_head_errors_are_empty",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_content_length_requires_ascii_decimal_and_head_errors_are_empty (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_content_length_requires_ascii_decimal_and_head_errors_are_empty)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 86, in test_content_length_requires_ascii_decimal_and_head_errors_are_empty\n    self.assertEqual(response.status_code,403);self.assertEqual(response.body,b'')\n                                               ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^\nAssertionError: b'{\"code\":\"operator_forbidden\",\"error\":\"Ope[136 chars]ull}' != b''\n\n----------------------------------------------------------------------\nRan 1 test in 0.007s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "duplicate query",
      "test": "test_duplicate_session_query_fields_refuse_before_listing",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_duplicate_session_query_fields_refuse_before_listing (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_duplicate_session_query_fields_refuse_before_listing)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_routes.py\", line 97, in test_duplicate_session_query_fields_refuse_before_listing\n    self.assertEqual(response.status_code,400)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 200 != 400\n\n----------------------------------------------------------------------\nRan 1 test in 0.073s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "orphan conflict cause",
      "test": "test_orphan_packet_conflict_has_distinct_recoverable_cause",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_orphan_packet_conflict_has_distinct_recoverable_cause (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_orphan_packet_conflict_has_distinct_recoverable_cause)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 284, in test_orphan_packet_conflict_has_distinct_recoverable_cause\n    self.assertEqual((caught.exception.code,caught.exception.cause),('request_conflict','packet_exists'))\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Tuples differ: ('request_conflict', None) != ('request_conflict', 'packet_exists')\n\nFirst differing element 1:\nNone\n'packet_exists'\n\n- ('request_conflict', None)\n+ ('request_conflict', 'packet_exists')\n\n----------------------------------------------------------------------\nRan 1 test in 0.120s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "producer drift cause",
      "test": "test_producer_drift_and_access_loss_are_author_refusals",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_producer_drift_and_access_loss_are_author_refusals (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_producer_drift_and_access_loss_are_author_refusals)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_operator_core.py\", line 297, in test_producer_drift_and_access_loss_are_author_refusals\n    self.assertEqual((caught.exception.code,caught.exception.cause),('no_author_available','producer_unavailable'))\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Tuples differ: ('request_conflict', None) != ('no_author_available', 'producer_unavailable')\n\nFirst differing element 0:\n'request_conflict'\n'no_author_available'\n\n- ('request_conflict', None)\n+ ('no_author_available', 'producer_unavailable')\n\n----------------------------------------------------------------------\nRan 1 test in 0.077s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "postrun independent",
      "test": "test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent (tests.test_artifact_recovery.ArtifactRecoveryTests.test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent)\nService/engine sequencing fixture, not an app Stop-route integration claim.\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_recovery.py\", line 340, in test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent\n    self.assertEqual(case.artifacts.get_request(later['request_id'])['state'], 'queued')\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'cancelled' != 'queued'\n- cancelled\n+ queued\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.271s\n\nFAILED (failures=1)\n"
    }
  ],
  "source_unchanged": true,
  "pass": true
}
```

### Final full discovery log

```text
2026-10-26T20:58:11.840Z === started (pid 38628, agent 6c2a7241-eb44-423f-8d53-eb4cc5425ad8, shell: C:\Program Files\PowerShell\7\pwsh.exe)
2026-10-26T20:58:12.791Z err| C:\Users\SJG\Documents\CodePlayground\agentchattr\.venv-windows\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
2026-10-26T20:58:12.792Z err|   from starlette.testclient import TestClient as TestClient  # noqa
2026-10-26T20:58:13.041Z | {'kind': 'D4 builder full root test-module discovery, namespace-safe', 'interpreter': 'C:\\Users\\SJG\\Documents\\CodePlayground\\agentchattr\\.venv-windows\\Scripts\\python.exe', 'modules': 225, 'tests': 1888}
2026-10-26T21:02:39.794Z err| ................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................Channel state is unavailable; publication and new claims are held.
2026-10-26T21:02:43.511Z err| .............................................................................................................Session 2: failed to persist dispatch for claude (OSError)
2026-10-26T21:02:51.280Z err| ................................................................................................................................Scheduled attempt could not be saved; nothing was published.
2026-10-26T21:02:51.368Z err| ...Scheduled publication was not confirmed (OSError).
2026-10-26T21:02:51.402Z err| .Scheduled delivery bookkeeping could not be saved; the attempt remains reserved.
2026-10-26T21:02:51.433Z err| .Scheduled delivery bookkeeping could not be saved; the attempt remains reserved.
2026-10-26T21:02:51.693Z err| ..........Scheduled publication was not confirmed (OSError).
2026-10-26T21:02:51.755Z err| .Scheduled publication was not confirmed (OSError).
2026-10-26T21:02:54.068Z err| .............................................................Session 2: failed to persist dispatch for cli-4d8efa15-555ba7915a6c (OSError)
2026-10-26T21:02:55.901Z err| ..................................Session 1: failed to persist dispatch for cli-4d8efa15-47bd142bec1c (OSError)
2026-10-26T21:02:55.997Z err| .Session 1: failed to persist dispatch for cli-4d8efa15-d57f324b96ba (OSError)
2026-10-26T21:02:56.100Z err| .Session 1: failed to persist dispatch for cli-4d8efa15-1aef8f21eb7c (OSError)
2026-10-26T21:03:05.801Z err| ........................................................................................................................Session 1: failed to persist dispatch for codex (OSError)
2026-10-26T21:03:09.224Z | {"method": "store/catalog real-files Windows default atomic_json", "portable_envelope_bytes": 4194304, "existing_lineages": 100, "existing_versions": 100, "requests": 128, "versions": 128, "packet_objects": 128, "zip_member_count": 262, "baseline_seconds": [0.0004900998901575804, 0.0005624999757856131, 0.0003912999527528882, 0.0006882000016048551, 0.0004640000406652689, 0.00040570006240159273, 0.0004078000783920288, 0.00042290007695555687, 0.00040009990334510803, 0.00046829995699226856], "samples_seconds": [0.16738700005225837, 0.16650259995367378, 0.16431020002346486, 0.17060589999891818, 0.16631040000356734, 0.16357600002083927, 0.1718180999159813, 0.17823560000397265, 0.1855892000021413, 0.1665756000438705], "maximum_seconds": 0.1855892000021413, "target_seconds": 0.3, "target_met": true, "limit_seconds": 1.0, "limit_policy": "reduced first-release basic responsiveness", "includes_metadata_parse": true, "includes_whole_index_validation": true, "fsync_mocked": false}
2026-10-26T21:03:09.224Z |   Using tmux session: owned
2026-10-26T21:03:09.224Z |   Reattach: tmux attach -t owned
2026-10-26T21:03:09.224Z |   Session already exists; preserved. Choose another seat or stop its owner first.
2026-10-26T21:03:09.224Z |   Warning: AGENTCHATTR_PORT='not-a-number' is not a valid integer, ignoring
2026-10-26T21:03:09.224Z |   MCP proxy: port 51917
2026-10-26T21:03:09.224Z |   MCP proxy: port 63633
2026-10-26T21:03:09.224Z |   Using tmux session: agentchattr-claude-1
2026-10-26T21:03:09.224Z |   Reattach: tmux attach -t agentchattr-claude-1
2026-10-26T21:03:09.224Z |   Child exit receipt unavailable; attach success does not prove child success.
2026-10-26T21:03:09.224Z |   [wrapper] VT enable (stdout): 0x0003 -> 0x0007 [ok]
2026-10-26T21:03:16.114Z err| .........................................................................sss.................Launch could not complete: Agent template is not configured. Add it to config.local.toml before launching.
2026-10-26T21:03:38.394Z err| .........................................................................................................................................................................Session 2: failed to persist dispatch for cli-4d8efa15-13bf506c1c1e (OSError)
2026-10-26T21:03:38.856Z err| ....Session 2: failed to persist dispatch for cli-4d8efa15-f6db83c13e63 (OSError)
2026-10-26T21:03:49.211Z err| ...................................................................................................................................................................................Artifact ownership binding is unavailable; artifact work is held.
2026-10-26T21:03:49.227Z err| .Artifact ownership binding is unavailable; artifact work is held.
2026-10-26T21:04:23.864Z err| .....................................................................................................................................................................................................................................................................................................................................................................................s......
2026-10-26T21:04:23.865Z | {
2026-10-26T21:04:23.865Z |   "server": "absent",
2026-10-26T21:04:23.865Z |   "environment_ready": false,
2026-10-26T21:04:23.865Z |   "checked_at": "2026-10-26T21:03:16.415717+00:00",
2026-10-26T21:04:23.865Z |   "agents": []
2026-10-26T21:04:23.865Z | }
2026-10-26T21:04:23.865Z |   MCP proxy: port 52198
2026-10-26T21:04:23.865Z |   MCP proxy: port 52843
2026-10-26T21:04:23.865Z |   MCP proxy: port 63371
2026-10-26T21:04:23.865Z |   MCP proxy: port 58985
2026-10-26T21:04:23.865Z |   MCP proxy: port 52290
2026-10-26T21:04:23.865Z err| ----------------------------------------------------------------------
2026-10-26T21:04:23.865Z err| Ran 1888 tests in 370.823s
2026-10-26T21:04:23.865Z err|
2026-10-26T21:04:23.865Z err| OK (skipped=4)
2026-10-26T21:04:24.489Z === exited (code 0)

```
