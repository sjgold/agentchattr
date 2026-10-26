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
