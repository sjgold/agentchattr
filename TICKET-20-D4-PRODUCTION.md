# Ticket 20 D4 production ledger

Status: implementation authorized after945ea482 reds; builder regression green at4968e47, but the first D4 production timing gate MISSED. Return to DESIGN, acceptance held. No R3/operator/capacity/activation/push. Capability stays empty.

## Ordered work and verification

1. Correct P1 deterministic startup/no-spurious-held/queued-positive test, P2 masked hooks, P3 genuine fence evolution, P4 weak peers/ownership variants; retain observed-red baseline. Freeze all private seams in one PHASES table (P6).
2. Implement shared legacy Event before authoring load, capture/snapshot pure predicate and outside-authoring observational scan. Run owner/integration + phase tests for actual store behavior.
3. Implement frozen diagnostic intents/guards/receipts and a per-invocation A/B/C driver with no owner transaction state. Explicit per-caller locked cores preserve ordinary behavior; every B failure propagates before C, private signal caught only by driver.
4. Refactor startup into outside-boundary inventory and fresh per-item operations/counts/marks; adapt MCP to combined service without caller boundary. Run D4 and A1/R1/R2 support green.
5. Add all P5 missing contract coverage (red-before-source where possible, else mutation-checked green), ownership/receipt/guard mutations, artifact affected selection and ONE full discovery on frozen source. Do not run suites in a timing window.
6. Add explicit production gate mode on same tools:10+ fresh samples per caller A/C/peer during heavy B, structural reads outside boundary, full/held4MiB import gates. Retain every sample/retry, no threshold changes. Miss returns to review. Independent reviewer runs/static audit required before acceptance.

## Mechanism decisions

- Ruling: diagnostic context is passed explicitly through private locked cores (origin/mode), never placed on an owner or in a new ContextVar. The existing A1 packet invocation scope may span A/B/C.
- Ruling: guards store immutable canonical request/audit, normalized queue claim and retained result/ACK/disposition snapshots. C rereads fresh authority and compares; it never rereads or writes diagnostics. Result-based seal checks stay for admission/recovery/ACK, while terminal/unmatched startup retains existing launch-bound/no-added-seal behavior.
- Ruling: _DiagnosticRequired inherits directly from Exception and is never intercepted by existing ValueError/RuntimeError storage catches. Only the driver catches it after releasing A; B errors propagate with no fabricated receipt.
- Ruling: startup selection is deterministic by sorted channels and original per-channel request order. Tests explicitly seed selection order; a fresh row check before omitted marks prevents spurious storage-unavailable warnings as well as stale writes.

Each step's actual edits/checks and any changed decision will be recorded below. Existing failed gates and raw DESIGN receipts retain their original attribution.

## Step1/2 checkpoint

P1-P4 test corrections observed red before source:30methods45FAIL/28ERROR27.851s, tracked14dc5da0. Hooks now collect writer/marker observations and assert after production returns; deterministic same-channel task selection tests both still-queued positive and changed-active/no-spurious-held negative. Ownership unsupported cases cover all3locks and noncallable/raising/None/nonbool results. Startup terminal peer actually cancels another request; structural reads progress while a separate thread holds the boundary. Real fence evolution precedes release. No unused pause argument remains.

Store implementation adds one shared Event before authoring load and uses it for sticky legacy refusal in both owners. Capture/snapshot share a memory-only predicate, including imported/no-attachment and non-null authoring errors. Diagnostic transactions check the marker before and after metadata replacement; landed bytes are retained and C never gets a successful receipt after legacy discovery. Filesystem orphan scans now execute outside the authoring lock. A1 packet helpers unchanged.

Executed56tests8.663s PASS (owner/integration plus marker-before-load/capture-no-diagnostic-lock/orphan-scan release). This is partial implementation evidence, NOT complete D4 green or a timing gate. Service driver/startup/MCP and P5 coverage remain.

## Service and P5 implementation checkpoint

The invocation-local driver now runs capture under A, catches only the private diagnostic signal after releasing that boundary, persists B without engine/catalog/authoring ownership, and checks the exact receipt/intent/token under C. Selected service entries use private capture cores; MCP calls the combined entry without a caller-held boundary. Startup inventories outside the boundary and runs fresh per-item capture/settlement. No owner holds invocation authority or a new ContextVar.

P5 added fourteen methods to the same root file. They cover typed B failure/no C, continuation/origin and guard proof capture, pre-B ownership, five reservation queue cases, newly inactive reservation/retained recovery, terminal winner warning, changed reason/channel/audit and unreadable C, changed saved digest/ACK/disposition/consumer, startup admission/inventory ownership, stale startup disposition and source-failure counts, imported/held capture and sticky constructor marker, mid-scan OSError projection, overflow summary receipt id, and corrupted guard proof pairs. Existing failing MCP capture now records one parent-first A token, as does the healthy control.

Two added checks were observed red before the corresponding source fixes: external Event clear forgot an already observed legacy hold; an audit mismatch on an already-fulfilled ACK-repair row returned the terminal-winner projection. Two tests/two failures0.722s. Recognition now latches the marker on its owner, and a terminal winner requires an actual state change from captured authority; existing fences likewise cannot mask an unrelated authority mismatch. Phase44 PASS27.767s after these fixes. Additional sticky request_diagnostics and failing combined-A assertions pass in phase/recovery49 PASS28.848s.

Broader artifact selection434 in231.692s:433 pass, one failure in the pre-approved adaptation at test_artifact_authority_review. Its public resume_request fault patch no longer reached the origin-aware startup core. Changed only that patch target to _resume_request_locked, preserving the exact operator_recovery_required assertion; the49 focused run exercises it. Full project builder run1814/221modules is in progress; no full-pass claim yet. Earlier144 support tests passed33.523s before the fourteen P5 additions.

### P5 evidence map

All added methods are in tests/test_artifact_diagnostic_phases.py. Names begin test_:

|Requirement|Method suffix|
|---|---|
|B failure, no fabricated receipt|b_failure_has_no_c_effect_or_fabricated_receipt_per_entry|
|Signal/continuation/origin and proof fields|continuation_origins_and_all_guard_proofs_are_captured|
|Second ownership query|pre_b_guard_rechecks_current_thread_ownership|
|M6 queue predicates|reservation_resume_queue_changes_and_existing_fence_precedence|
|C409 modes|resume_inactive_at_c_is_409_for_reservation_and_retained_modes|
|Operator terminal winner|resume_terminal_winner_has_no_invented_admission_and_warns|
|Current row fields and C503|changed_authoring_fields_and_unreadable_authoring_at_c|
|Saved result/ACK/disposition/claim|saved_proof_ack_and_disposition_changes_refuse_c|
|Startup admission and inventory|startup_saved_admission_b_and_outbox_inventory_are_outside_boundary|
|Startup counts/stale disposition|startup_stale_disposition_and_unraced_source_failure_counts|
|Legacy/imported/held|capture_imported_held_and_sticky_constructor_marker|
|Orphan scan failure isolation|orphan_scan_oserror_drops_observations_without_latching_authoring|
|Summary own id|overflow_summary_id_is_the_receipt_id|
|Proof-pair rejection|corrupt_guard_proof_pairs_cannot_become_terminal_winner_results|

Other existing phase methods cover the nine races, ownership failures, receipt replay, event-before-load and durable-before-transition ordering. P6 interfaces are consolidated in PHASES, with DIAGNOSTICS F-4 reduced to a cross-reference. These are implementation checks, not performance acceptance.

## Frozen production measurement protocol

The existing authority and facade tools gain an explicit --production-gate mode. Historical DESIGN and failed-gate receipts keep their original attribution. Service mode runs ten fresh fixtures for each of nine diagnostic callers plus healthy combined brief and delivery. A/C are measured from real outermost acquired main-thread engine/catalog boundary entries; B/C are identified by wrapping the real private production writer/settler, without replacing their work. No guard-copy cost or hypothetical C probe is used. Response encoding for healthy combined context is outside the boundary under D4 and reported separately.

Each fixture retains the max-source shape:129 authoring requests (128 imported priors and one2MiB/1000-ref candidate),512KiB parent and Markdown. The diagnostic seed has1023 matching bodies/7.5MiB, with seven candidate-dispatch details so a512KiB result can fill the8MiB/1024-object quota. Source-failure callers pay a real successful bounded read/content validation before the injected late-read failure; their content-free diagnostic cannot fill a body slot. This distinction is reported, not disguised as a body write. A peer repeatedly calls require_active on the same engine/catalog locks during B. B latency is report-only; actual A/C holds and peer maximum require<=0.270 hard and<=0.216 margin, with ownership/retry failures retained.

Facade mode runs ten fresh max-authoring fixtures with heavy/summary/request_diagnostics/structural observations outside the authority boundary, then ten full and ten held diagnostic4MiB import cases. Structural read rewrites the maximum810186-byte metadata to force a strict reread. Peer waits and boundary ownership are measured, diagnostic latency remains report-only. Import gates retain<=0.300. Owner caches are warm after setup; cold restart tails are not measured. No warm-up discard, sample replacement or threshold change. Path.replace PermissionErrors are counted for every phase, including body replacement. Source/tool/fixture hashes and detected real fsync/D1/D2 provenance are written before sampling; receipts are incremental. Timing begins only after suites and mutation checks finish, on a clean frozen pin.

## Frozen regression and mutation receipts

Builder full root test-module discovery (namespace-safe explicit module loader):221 modules,1814 tests, OK with four skips342.250s, tracked shell5fdf71c7-0157-48d5-8147-fd5eb2ce6e38. This includes all434 artifact tests, with the one stale public-resume patch adapted before the run. Product bytes remained unchanged during and after the full run. Afterward, the foreign-receipt test also gained an exact-intent-identity refusal check; that one test passes0.316s. No product change required another full run.

Runnable tools/check_artifact_d4_mutations.py:15 in-memory mutants, all killed by assertion failures, zero error-only kills, product source hashes unchanged. The first run retained13 valid kills plus one invalid harness anchor (no mutant was installed for that entry); corrected the dedented pre-B anchor and added the exact-intent mutant, then reran the complete15. The original failed harness receipt is preserved. Controls tools/test_artifact_checkpoint_controls.py:4 OK0.758s after incremental A/B/C receipt hooks were added. Hooks write after releasing the measured boundary; persistence of timing evidence is never hidden inside an authority hold.

Current mode intentionally measures nine diagnostic callers and two healthy added-entry holds (110 service rows), plus40 facade/read observations and20 import rows. At least ten samples per group; no timing run has begun at this freeze. --production-gate is explicit on each existing tool. Capability remains empty; no activation or push.

### Full-run summary

```text
Ran 1814 tests in 342.250s
OK (skipped=4)
```

### Mutation receipt

```json
{
  "kind": "D4 in-process mutation proof, no product edits, not a timing gate",
  "mutations": [
    {
      "label": "receipt intent identity",
      "test": "test_foreign_receipt_and_second_settlement_are_refused_without_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_foreign_receipt_and_second_settlement_are_refused_without_effect (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_foreign_receipt_and_second_settlement_are_refused_without_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 458, in test_foreign_receipt_and_second_settlement_are_refused_without_effect\n    with patch.object(case.authority,'_settle_diagnostic_intent',settle):action()\n                                                                         ~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 95, in <lambda>\n    'reject':lambda:case.authority.reject_response(audit['brief_id'],'invalid structured response',instance),\n                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in invoke\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 137, in _packet_invocation\n    return step()\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in <lambda>\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n                                           ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 775, in reject_response\n    return self._run_diagnostic_operation(lambda: self._reject_response_locked(brief_id, content, instance, received_truncated=received_truncated), origin='worker')\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 167, in _run_diagnostic_operation\n    return self._settle_diagnostic_intent(intent, receipt, invocation_key=key)\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 455, in settle\n    with self.assertRaises(storage.ArtifactConflict):\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactConflict not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.279s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "receipt token",
      "test": "test_foreign_receipt_and_second_settlement_are_refused_without_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_foreign_receipt_and_second_settlement_are_refused_without_effect (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_foreign_receipt_and_second_settlement_are_refused_without_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 458, in test_foreign_receipt_and_second_settlement_are_refused_without_effect\n    with patch.object(case.authority,'_settle_diagnostic_intent',settle):action()\n                                                                         ~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 95, in <lambda>\n    'reject':lambda:case.authority.reject_response(audit['brief_id'],'invalid structured response',instance),\n                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in invoke\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 137, in _packet_invocation\n    return step()\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in <lambda>\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n                                           ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 775, in reject_response\n    return self._run_diagnostic_operation(lambda: self._reject_response_locked(brief_id, content, instance, received_truncated=received_truncated), origin='worker')\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 167, in _run_diagnostic_operation\n    return self._settle_diagnostic_intent(intent, receipt, invocation_key=key)\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 452, in settle\n    with self.assertRaises(storage.ArtifactConflict):\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactConflict not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.277s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "authority audit comparison",
      "test": "test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results) (field='audit_bytes')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 926, in test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.644s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "record digest pair",
      "test": "test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results) (field='record_digest')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 926, in test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.651s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "queue projection",
      "test": "test_reservation_resume_queue_changes_and_existing_fence_precedence",
      "killed": true,
      "failures": 3,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_reservation_resume_queue_changes_and_existing_fence_precedence (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_reservation_resume_queue_changes_and_existing_fence_precedence) (transition='absent_present')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 737, in test_reservation_resume_queue_changes_and_existing_fence_precedence\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n======================================================================\nFAIL: test_reservation_resume_queue_changes_and_existing_fence_precedence (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_reservation_resume_queue_changes_and_existing_fence_precedence) (transition='queued_claimed')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 737, in test_reservation_resume_queue_changes_and_existing_fence_precedence\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n======================================================================\nFAIL: test_reservation_resume_queue_changes_and_existing_fence_precedence (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_reservation_resume_queue_changes_and_existing_fence_precedence) (transition='new_fence')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 740, in test_reservation_resume_queue_changes_and_existing_fence_precedence\n    self.assertEqual(outcome[0],'ok');self.assertIsNone(outcome[1]['admission'])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 'error' != 'ok'\n- error\n+ ok\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.939s\n\nFAILED (failures=3)\n"
    },
    {
      "label": "saved result digest",
      "test": "test_saved_proof_ack_and_disposition_changes_refuse_c",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_saved_proof_ack_and_disposition_changes_refuse_c (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_saved_proof_ack_and_disposition_changes_refuse_c) (changed='record')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 824, in test_saved_proof_ack_and_disposition_changes_refuse_c\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.923s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "ACK observation",
      "test": "test_saved_proof_ack_and_disposition_changes_refuse_c",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_saved_proof_ack_and_disposition_changes_refuse_c (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_saved_proof_ack_and_disposition_changes_refuse_c) (changed='ack')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 824, in test_saved_proof_ack_and_disposition_changes_refuse_c\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.921s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "disposition observation",
      "test": "test_saved_proof_ack_and_disposition_changes_refuse_c",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_saved_proof_ack_and_disposition_changes_refuse_c (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_saved_proof_ack_and_disposition_changes_refuse_c) (changed='disposition')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 824, in test_saved_proof_ack_and_disposition_changes_refuse_c\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.953s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "C active channel",
      "test": "test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes) (mode='resume')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 757, in test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n======================================================================\nFAIL: test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes) (mode='retained')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 757, in test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n----------------------------------------------------------------------\nRan 1 test in 0.426s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "pre-B ownership check",
      "test": "test_pre_b_guard_rechecks_current_thread_ownership",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_pre_b_guard_rechecks_current_thread_ownership (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_pre_b_guard_rechecks_current_thread_ownership)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 710, in test_pre_b_guard_rechecks_current_thread_ownership\n    self.assertEqual(len(calls),2);self.assertEqual(writer.call_count,0)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^\nAssertionError: 1 != 2\n\n----------------------------------------------------------------------\nRan 1 test in 0.258s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "pre-A ownership check",
      "test": "test_diagnostic_driver_refuses_caller_held_boundary",
      "killed": true,
      "failures": 3,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_diagnostic_driver_refuses_caller_held_boundary (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary) (lock='engine')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 339, in test_diagnostic_driver_refuses_caller_held_boundary\n    with lock,self.assertRaises(storage.ArtifactUnavailable) as caught:\n              ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable not raised\n\n======================================================================\nFAIL: test_diagnostic_driver_refuses_caller_held_boundary (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary) (lock='catalog')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 339, in test_diagnostic_driver_refuses_caller_held_boundary\n    with lock,self.assertRaises(storage.ArtifactUnavailable) as caught:\n              ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable not raised\n\n======================================================================\nFAIL: test_diagnostic_driver_refuses_caller_held_boundary (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary) (lock='authoring')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 339, in test_diagnostic_driver_refuses_caller_held_boundary\n    with lock,self.assertRaises(storage.ArtifactUnavailable) as caught:\n              ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.499s\n\nFAILED (failures=3)\n"
    },
    {
      "label": "B failure must not fabricate receipt",
      "test": "test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry",
      "killed": true,
      "failures": 12,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='cli')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='reject')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='brief')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='delivery')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='resume')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='retained')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='saved')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='fulfilled')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='ack')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='startup')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='startup_unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 658, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n----------------------------------------------------------------------\nRan 1 test in 2.497s\n\nFAILED (failures=12)\n"
    },
    {
      "label": "summary receipt id",
      "test": "test_overflow_summary_id_is_the_receipt_id",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_overflow_summary_id_is_the_receipt_id (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_overflow_summary_id_is_the_receipt_id)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 909, in test_overflow_summary_id_is_the_receipt_id\n    self.assertEqual(result['diagnostic_id'],summary['id']);self.assertNotEqual(result['diagnostic_id'],summary['latest_diagnostic_id'])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: '8c22f0844dbd5ee6a0892bd7f821be09' != 'b500c07b3ad05c079023384e1610c25b'\n- 8c22f0844dbd5ee6a0892bd7f821be09\n+ b500c07b3ad05c079023384e1610c25b\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.314s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "pre-C guard",
      "test": "test_second_writer_during_diagnostic_io_refuses_stale_settlement",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_second_writer_during_diagnostic_io_refuses_stale_settlement (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_second_writer_during_diagnostic_io_refuses_stale_settlement) (caller='cli')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 193, in test_second_writer_during_diagnostic_io_refuses_stale_settlement\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactInputError('Invalid Markdown. Correct the argument and submit again within the byte limit.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n----------------------------------------------------------------------\nRan 1 test in 0.532s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "origin capture",
      "test": "test_continuation_origins_and_all_guard_proofs_are_captured",
      "killed": true,
      "failures": 10,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='reject')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='delivery')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='resume')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='retained')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='saved')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='fulfilled')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='ack')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='startup')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='startup_unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 687, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n----------------------------------------------------------------------\nRan 1 test in 2.274s\n\nFAILED (failures=10)\n"
    }
  ],
  "source_sha256": {
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py": "2a13f084071e6e12db61fcb6fdbeccfde030d5ffe1bd9add33422b297fd6e6d7",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_store.py": "6c92e79837400e79444353d1a10c6679ac6761db07bb8a2f48062fd75a212f1d",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\mcp_bridge.py": "265dd38d36be915b8df6040222cac4de878ef9f8d498127cf99c1b0c253141b8"
  },
  "source_unchanged": true,
  "pass": true
}
```

## First D4 production timing gate: MISS, return to design

Frozen clean pin4968e47059e2c744d0611f4d96293afe705fa9d7. Tracked run fbfa7d68-408a-41cb-bf4a-6a16237fa016 exited1. All110 original samples and290 incremental phase observations are retained below, no selective rerun or exclusion. Receipt SHA2569675460e34503ee2085a880b1ba3dcd4e75bc83806efcba6ca1efb1c23f23c38. Every PermissionError replacement counter is zero. No suite overlapped this timing window.

Exactly one hard/margin miss: admit_saved sample6, phase A1.1663549999939278s against0.270 hard/0.216 margin. Its C0.03550619992893189s, B0.2116205000784248s, peer maximum during B0.027092000003904104s. Other109 samples meet hard and margin comparisons. The outlier cause is UNKNOWN and stays NORMAL; a retry was not observed. Splitting diagnostic IO did not make every authority hold satisfy the cap. No clearance follows from the other109 samples.

All B ownership observations were false for engine/catalog/authoring. Healthy combined A maximum0.177735900s (peer0.181155900s), healthy delivery A maximum0.142430000s. This supports diagnostic B isolation for this run while leaving the failed A hold unresolved. It does not prove cancellation/Stop latency in the production gate.

|Caller|N|A median/max s|C median/max s|B max s, report only|Peer max s|Miss samples|
|---|---|---|---|---|---|---|
|brief_context|10|0.115464/0.159658|0.067548/0.117458|0.439972|0.048511||
|delivery|10|0.083143/0.092314|0.068983/0.075052|0.219249|0.037333||
|submit_cli|10|0.131967/0.151158|0.020702/0.027486|0.240213|0.032619||
|admit_saved|10|0.165453/1.166355|0.034055/0.038830|0.246939|0.027092|6|
|reject_response|10|0.134623/0.145825|0.074141/0.090781|0.227004|0.031533||
|resume|10|0.080887/0.093431|0.069068/0.087377|0.222162|0.042808||
|retained_recovery|10|0.124386/0.131760|0.079646/0.091791|0.204567|0.038181||
|ack_repair|10|0.075283/0.089260|0.027710/0.030491|0.223934|0.011669||
|startup_terminal|10|0.038717/0.046117|0.033733/0.037958|0.216932|0.020086||
|healthy_brief_context|10|0.152537/0.177736|none|none|0.181156||
|healthy_delivery|10|0.118482/0.142430|none|none|0.146286||

### Gate coverage limits found during the run

This first service run is valid evidence of the failed A hold, but is not the complete contracted acceptance harness. Repeated peers use require_active, not timed mutating cancel/Stop/independent-request actions; deterministic unit races already cover their functional progress, which is a separate claim. Service-level summary-only C settlement remains to be measured (facade summary is not enough). The peer starts for B, while healthy A has a contending peer; diagnostic A has no peer wait observation. Startup incidental direct engine-lock acquisitions, A+C sum and whole-call latency need explicit observations. These gaps must be corrected in the next frozen harness contract, not silently waived or presented as completed gates.

Per the MISS rule, the facade/read/import run and supplemental mutating-peer/summary measurements were NOT STARTED. No new product optimization, gate rerun or threshold/budget change follows this finding. Existing tests/full/mutation results retain their4968 attribution. The4MiB in-suite benchmark remains a regression result, not the missing D4 full/held gate.

Recommended next step for reviewer ruling: harness-only phase-A attribution on the same admit_saved/max-source shape, splitting validate_payload, context/producer checks, seal verification, packet read/content validation, activation authoring persist (validation/encode/fsync/replace), outbox read/verification and intent capture. The current source A includes authoring persistence and outbox IO; this is a static call-path fact, not an attribution of the1.166s tail. Any new design profile must retain every sample alongside this miss. Do not choose a remedy before the attribution/design review.

### Raw frozen receipt (all samples and phase observations)

```json
{
  "kind": "D4 PRODUCTION acceptance gate",
  "samples": [
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11196220002602786
        },
        {
          "phase": "C",
          "seconds": 0.06774960004258901
        }
      ],
      "B_seconds": [
        0.18849429988767952
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006201999494805932,
        0.00069650006480515,
        0.0006633999291807413,
        0.000873900018632412,
        0.0006660999497398734,
        0.0006264001131057739,
        0.0006391999777406454,
        0.0006513999542221427,
        0.0007551999296993017,
        0.03157989995088428,
        0.004800800001248717
      ],
      "peer_max_seconds": 0.03157989995088428,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 1,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.10952449997421354
        },
        {
          "phase": "C",
          "seconds": 0.06427570001687855
        }
      ],
      "B_seconds": [
        0.18984749994706362
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0008258000016212463,
        0.0008230999810621142,
        0.0009054000256583095,
        0.0006882000016048551,
        0.0006339000537991524,
        0.0007314999820664525,
        0.0007819999009370804,
        0.000753799919039011,
        0.0006235000910237432,
        0.027102299965918064,
        0.000632300041615963
      ],
      "peer_max_seconds": 0.027102299965918064,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 2,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11257809994276613
        },
        {
          "phase": "C",
          "seconds": 0.0651126999873668
        }
      ],
      "B_seconds": [
        0.18598990002647042
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006880000000819564,
        0.0005988000193610787,
        0.0006538000889122486,
        0.0007022999925538898,
        0.0007112999446690083,
        0.0007117000641301274,
        0.0007227000314742327,
        0.0007597000803798437,
        0.0006794999353587627,
        0.000654200091958046,
        0.026430799975059927
      ],
      "peer_max_seconds": 0.026430799975059927,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 3,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1596580999903381
        },
        {
          "phase": "C",
          "seconds": 0.11745770007837564
        }
      ],
      "B_seconds": [
        0.4399716999614611
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0010033000726252794,
        0.002643599989823997,
        0.0017192999366670847,
        0.0023947999579831958,
        0.0009034000104293227,
        0.0013016000157222152,
        0.0008323999354615808,
        0.0014229000080376863,
        0.0009346000151708722,
        0.001230900059454143,
        0.0008191000670194626,
        0.0011357000330463052,
        0.0018343999981880188,
        0.0011570999631658196,
        0.0008541999850422144,
        0.0006946000503376126,
        0.0011457999935373664,
        0.000979500007815659,
        0.0009718999499455094,
        0.001394700026139617,
        0.0015072000678628683,
        0.0461663999594748,
        0.014425900066271424
      ],
      "peer_max_seconds": 0.0461663999594748,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 4,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13170540006831288
        },
        {
          "phase": "C",
          "seconds": 0.0808802000246942
        }
      ],
      "B_seconds": [
        0.21898869995493442
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005794999888166785,
        0.0006787000456824899,
        0.0008687999797984958,
        0.0008060999680310488,
        0.0008657999569550157,
        0.0009935999987646937,
        0.0007143999682739377,
        0.0007550000445917249,
        0.0006455000257119536,
        0.0007141000824049115,
        0.04851090000011027
      ],
      "peer_max_seconds": 0.04851090000011027,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 5,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12498459999915212
        },
        {
          "phase": "C",
          "seconds": 0.07165429997257888
        }
      ],
      "B_seconds": [
        0.22402099997270852
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006449000211432576,
        0.0005442999536171556,
        0.0007054000161588192,
        0.0008199999574571848,
        0.0006556999869644642,
        0.0006871999939903617,
        0.0006010000361129642,
        0.0007066000252962112,
        0.0018362000118941069,
        0.0007809000089764595,
        0.00069650006480515,
        0.04422310006339103,
        0.0006399999838322401
      ],
      "peer_max_seconds": 0.04422310006339103,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 6,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11834919999819249
        },
        {
          "phase": "C",
          "seconds": 0.07716320001054555
        }
      ],
      "B_seconds": [
        0.19619099993724376
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006134000141173601,
        0.0004973000613972545,
        0.0007298999698832631,
        0.0006590000120922923,
        0.0007851000409573317,
        0.0007453999714925885,
        0.0006708999862894416,
        0.0006127000087872148,
        0.0006156000308692455,
        0.0007442000787705183,
        0.029405899927951396
      ],
      "peer_max_seconds": 0.029405899927951396,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 7,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11858529993332922
        },
        {
          "phase": "C",
          "seconds": 0.06734619999770075
        }
      ],
      "B_seconds": [
        0.1929907000157982
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005976000102236867,
        0.0005680000176653266,
        0.0008016000501811504,
        0.0008268000092357397,
        0.0007912999717518687,
        0.0008014999330043793,
        0.0006262999959290028,
        0.0007449000841006637,
        0.0007722999434918165,
        0.0005527999019250274,
        0.028035900089889765
      ],
      "peer_max_seconds": 0.028035900089889765,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 8,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.10937700001522899
        },
        {
          "phase": "C",
          "seconds": 0.0656723000574857
        }
      ],
      "B_seconds": [
        0.18737080006394535
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007833000272512436,
        0.0007372000254690647,
        0.0006227000849321485,
        0.0007114999461919069,
        0.0007234999211505055,
        0.0007270999485626817,
        0.0008888000156730413,
        0.000658300006762147,
        0.0007964000105857849,
        0.026259200065396726,
        0.00042639998719096184
      ],
      "peer_max_seconds": 0.026259200065396726,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 9,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11174910003319383
        },
        {
          "phase": "C",
          "seconds": 0.06599820009432733
        }
      ],
      "B_seconds": [
        0.19598079996649176
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005874999333173037,
        0.0004833999555557966,
        0.0007341000018641353,
        0.0006772000342607498,
        0.0007215000223368406,
        0.0005472999764606357,
        0.0007810000097379088,
        0.0007608000887557864,
        0.0008123998995870352,
        0.0008782000513747334,
        0.02726269990671426,
        0.0005402000388130546
      ],
      "peer_max_seconds": 0.02726269990671426,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "brief_context",
      "sample": 10,
      "source_fault_hook_calls": 2,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08094440004788339
        },
        {
          "phase": "C",
          "seconds": 0.07467550004366785
        }
      ],
      "B_seconds": [
        0.19325040001422167
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000647400040179491,
        0.0006630999268963933,
        0.0007902999641373754,
        0.0005386000266298652,
        0.0007517000194638968,
        0.0009124999633058906,
        0.0006016000406816602,
        0.0007097000489011407,
        0.0007615999784320593,
        0.03341479995287955
      ],
      "peer_max_seconds": 0.03341479995287955,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 1,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08444809995125979
        },
        {
          "phase": "C",
          "seconds": 0.06879010004922748
        }
      ],
      "B_seconds": [
        0.1838469000067562
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005691000260412693,
        0.0007203000131994486,
        0.0006621000356972218,
        0.0008740000193938613,
        0.0009175000013783574,
        0.0005151000805199146,
        0.0008581000147387385,
        0.0007436000742018223,
        0.0007339000003412366,
        0.02595339994877577,
        0.0006567999953404069
      ],
      "peer_max_seconds": 0.02595339994877577,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 2,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.09231370000634342
        },
        {
          "phase": "C",
          "seconds": 0.06714479997754097
        }
      ],
      "B_seconds": [
        0.1917191999964416
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005708999233320355,
        0.0009166999952867627,
        0.0007201000116765499,
        0.0006918999133631587,
        0.0006587000098079443,
        0.0007169999880716205,
        0.0007345000049099326,
        0.0006678999634459615,
        0.0009122000774368644,
        0.03222189994994551
      ],
      "peer_max_seconds": 0.03222189994994551,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 3,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.0870234000030905
        },
        {
          "phase": "C",
          "seconds": 0.07505200000014156
        }
      ],
      "B_seconds": [
        0.20926100003998727
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007984000258147717,
        0.0006809000624343753,
        0.0007252999348565936,
        0.0007084999233484268,
        0.0007988999132066965,
        0.0008200999582186341,
        0.0007353000110015273,
        0.0006431000074371696,
        0.0007562000537291169,
        0.0007449999684467912,
        0.03733339998871088
      ],
      "peer_max_seconds": 0.03733339998871088,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 4,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07990479993168265
        },
        {
          "phase": "C",
          "seconds": 0.06928549997974187
        }
      ],
      "B_seconds": [
        0.1791575999232009
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000914399977773428,
        0.0007086999248713255,
        0.0006646000547334552,
        0.0006806000601500273,
        0.0007381999166682363,
        0.0006033000536262989,
        0.0006676000775769353,
        0.0007567999418824911,
        0.0007226000307127833,
        0.025260099908336997,
        0.0006723999977111816
      ],
      "peer_max_seconds": 0.025260099908336997,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 5,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07952220004517585
        },
        {
          "phase": "C",
          "seconds": 0.06751490000169724
        }
      ],
      "B_seconds": [
        0.19109609990846366
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006076999707147479,
        0.000736100017093122,
        0.0008529999759048223,
        0.0007371000247076154,
        0.0008110000053420663,
        0.0006680999649688601,
        0.0007260000566020608,
        0.0006561999907717109,
        0.000547999981790781,
        0.03304010001011193
      ],
      "peer_max_seconds": 0.03304010001011193,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 6,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.09027599997352809
        },
        {
          "phase": "C",
          "seconds": 0.0691763999639079
        }
      ],
      "B_seconds": [
        0.18596839997917414
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005954999942332506,
        0.0007945999968796968,
        0.0007659000111743808,
        0.0007454000879079103,
        0.0006620000349357724,
        0.0007567000575363636,
        0.0007665999000892043,
        0.0006726999999955297,
        0.0007159999804571271,
        0.02629969990812242
      ],
      "peer_max_seconds": 0.02629969990812242,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 7,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08582220005337149
        },
        {
          "phase": "C",
          "seconds": 0.06832980003673583
        }
      ],
      "B_seconds": [
        0.21924869995564222
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005811000009998679,
        0.0008511999621987343,
        0.0006446000188589096,
        0.0006582000060006976,
        0.0007186000002548099,
        0.0009123000781983137,
        0.0008917000377550721,
        0.0007163000991567969,
        0.0006022000452503562,
        0.0008021999383345246,
        0.03333999996539205,
        0.0005378000205382705
      ],
      "peer_max_seconds": 0.03333999996539205,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 8,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07769830001052469
        },
        {
          "phase": "C",
          "seconds": 0.06763039994984865
        }
      ],
      "B_seconds": [
        0.19808969995938241
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006783000426366925,
        0.00046410004142671824,
        0.0008172999368980527,
        0.000812400016002357,
        0.0007064000237733126,
        0.0009135999716818333,
        0.00052429991774261,
        0.0009151999838650227,
        0.0006779000395908952,
        0.036628699977882206,
        0.0005072999047115445
      ],
      "peer_max_seconds": 0.036628699977882206,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 9,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08183809998445213
        },
        {
          "phase": "C",
          "seconds": 0.06986869999673218
        }
      ],
      "B_seconds": [
        0.19275170005857944
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005650999955832958,
        0.0005360000068321824,
        0.0007272000657394528,
        0.0008379999781027436,
        0.0006778000388294458,
        0.0007033000001683831,
        0.0007238999241963029,
        0.0006173999281600118,
        0.0006818000692874193,
        0.0006873999955132604,
        0.027121799997985363,
        0.0004681000718846917
      ],
      "peer_max_seconds": 0.027121799997985363,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "delivery",
      "sample": 10,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1315885999938473
        },
        {
          "phase": "C",
          "seconds": 0.020559199969284236
        }
      ],
      "B_seconds": [
        0.20731069997418672
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000672800000756979,
        0.0007625999860465527,
        0.0009044000180438161,
        0.0009342000121250749,
        0.0008796999463811517,
        0.0009282000828534365,
        0.0006895000115036964,
        0.0008904000278562307,
        0.0008583000162616372,
        0.0007082000374794006,
        0.007094500004313886,
        0.0007233000360429287
      ],
      "peer_max_seconds": 0.007094500004313886,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 1,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1253589999396354
        },
        {
          "phase": "C",
          "seconds": 0.021985100000165403
        }
      ],
      "B_seconds": [
        0.19251860002987087
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007588999578729272,
        0.0006260999944061041,
        0.0006383000873029232,
        0.0007146000862121582,
        0.0008304999209940434,
        0.0009703999385237694,
        0.0006884000031277537,
        0.0006843000883236527,
        0.0007844999199733138,
        0.004871200071647763,
        0.010432399925775826,
        0.001917600049637258
      ],
      "peer_max_seconds": 0.010432399925775826,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 2,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13568780000787228
        },
        {
          "phase": "C",
          "seconds": 0.022417100029997528
        }
      ],
      "B_seconds": [
        0.19781000004149973
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007189000025391579,
        0.0005948999896645546,
        0.0006158000323921442,
        0.000763299991376698,
        0.0006836999673396349,
        0.0008897999068722129,
        0.0007140999659895897,
        0.0007863000500947237,
        0.0008155000396072865,
        0.011450899997726083,
        0.01035800005774945,
        0.0006040999433025718
      ],
      "peer_max_seconds": 0.011450899997726083,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 3,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14770940004382282
        },
        {
          "phase": "C",
          "seconds": 0.01969520002603531
        }
      ],
      "B_seconds": [
        0.18398480000905693
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006899000145494938,
        0.0005993000231683254,
        0.0008058999665081501,
        0.0007131000747904181,
        0.0007178999949246645,
        0.0007977000204846263,
        0.0008279000176116824,
        0.0005409999284893274,
        0.000714199966751039,
        0.000682600075379014,
        0.0005773000884801149
      ],
      "peer_max_seconds": 0.0008279000176116824,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 4,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.15115760010667145
        },
        {
          "phase": "C",
          "seconds": 0.020355199929326773
        }
      ],
      "B_seconds": [
        0.1848189999582246
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006966999499127269,
        0.0006125000072643161,
        0.000660400022752583,
        0.000677799922414124,
        0.0006448000203818083,
        0.0007021999917924404,
        0.0006698999786749482,
        0.0007845000363886356,
        0.0006880000000819564,
        0.0005835999036207795,
        0.000826600007712841
      ],
      "peer_max_seconds": 0.000826600007712841,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 5,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13234610005747527
        },
        {
          "phase": "C",
          "seconds": 0.020562499994412065
        }
      ],
      "B_seconds": [
        0.19258180004544556
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007735999533906579,
        0.0007118000648915768,
        0.0007173999911174178,
        0.000615999917499721,
        0.0006994999712333083,
        0.0007389000384137034,
        0.00066509994212538,
        0.0007741999579593539,
        0.0006781999254599214,
        0.0010462000500410795,
        0.0007121000671759248
      ],
      "peer_max_seconds": 0.0010462000500410795,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 6,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13150679995305836
        },
        {
          "phase": "C",
          "seconds": 0.027485599974170327
        }
      ],
      "B_seconds": [
        0.2402132999850437
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000685799983330071,
        0.0007245000451803207,
        0.0011292999843135476,
        0.0007417999440804124,
        0.0008148000342771411,
        0.0007573999464511871,
        0.0007807000074535608,
        0.0008050999604165554,
        0.0010842999909073114,
        0.0009528000373393297,
        0.0006418999982997775,
        0.011421400005929172,
        0.014950999990105629
      ],
      "peer_max_seconds": 0.014950999990105629,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 7,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12677689990960062
        },
        {
          "phase": "C",
          "seconds": 0.020840600016526878
        }
      ],
      "B_seconds": [
        0.18634859996382147
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0008964999578893185,
        0.0008055000798776746,
        0.0008599000284448266,
        0.000640900107100606,
        0.000721900025382638,
        0.0006700999801978469,
        0.0005097000394016504,
        0.0007915999740362167,
        0.0006252001039683819,
        0.0006330000469461083,
        0.00046900007873773575,
        0.0042906999588012695,
        0.0005408000433817506
      ],
      "peer_max_seconds": 0.0042906999588012695,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 8,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12775159999728203
        },
        {
          "phase": "C",
          "seconds": 0.02052490005735308
        }
      ],
      "B_seconds": [
        0.19490180001594126
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005897999508306384,
        0.0007436999585479498,
        0.0006763000274077058,
        0.000824799994006753,
        0.0006989999674260616,
        0.0006059999577701092,
        0.0007718999404460192,
        0.0007548000430688262,
        0.0006249999860301614,
        0.012672899989411235,
        0.011703700060024858,
        0.0004965000553056598
      ],
      "peer_max_seconds": 0.012672899989411235,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 9,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14128149999305606
        },
        {
          "phase": "C",
          "seconds": 0.02111159998457879
        }
      ],
      "B_seconds": [
        0.21073130005970597
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0009125000797212124,
        0.0005556000396609306,
        0.0005590000655502081,
        0.0006337000522762537,
        0.0007214999059215188,
        0.0008098999969661236,
        0.0006492000538855791,
        0.0006984000792726874,
        0.0008352999575436115,
        0.03261879994533956,
        0.00555729994084686
      ],
      "peer_max_seconds": 0.03261879994533956,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactInputError",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "submit_cli",
      "sample": 10,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.177546999999322
        },
        {
          "phase": "C",
          "seconds": 0.032934000017121434
        }
      ],
      "B_seconds": [
        0.1877600000007078
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.00069169991184026,
        0.0005104999290779233,
        0.000687599997036159,
        0.0006794000510126352,
        0.0006430000066757202,
        0.0008223999757319689,
        0.0005739000625908375,
        0.0006548999808728695,
        0.0007245000451803207,
        0.006955699995160103,
        0.0007066000252962112
      ],
      "peer_max_seconds": 0.006955699995160103,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 1,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.16322569991461933
        },
        {
          "phase": "C",
          "seconds": 0.032762099988758564
        }
      ],
      "B_seconds": [
        0.19337560003623366
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005898999515920877,
        0.0006293000187724829,
        0.0007799000013619661,
        0.000717800110578537,
        0.0007261999417096376,
        0.0006540000904351473,
        0.0005981000140309334,
        0.000961200101301074,
        0.0006745000137016177,
        0.012407199945300817,
        0.010696300072595477,
        0.0005386000266298652
      ],
      "peer_max_seconds": 0.012407199945300817,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 2,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.16419740009587258
        },
        {
          "phase": "C",
          "seconds": 0.03289949998725206
        }
      ],
      "B_seconds": [
        0.18943280004896224
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007856000447645783,
        0.000785200041718781,
        0.0007103000534698367,
        0.0008184999460354447,
        0.0007555000483989716,
        0.0006821999559178948,
        0.0005790999857708812,
        0.0006905000191181898,
        0.0007418999448418617,
        0.0007418000604957342,
        0.004354400094598532
      ],
      "peer_max_seconds": 0.004354400094598532,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 3,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1594251999631524
        },
        {
          "phase": "C",
          "seconds": 0.034046599990688264
        }
      ],
      "B_seconds": [
        0.19321950001176447
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007357000140473247,
        0.0006161000346764922,
        0.0006297000218182802,
        0.0006782999262213707,
        0.0007339000003412366,
        0.0008026000577956438,
        0.0006141000194475055,
        0.0005848000291734934,
        0.0007405000505968928,
        0.00681379996240139,
        0.006295000086538494
      ],
      "peer_max_seconds": 0.00681379996240139,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 4,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.17983899998944253
        },
        {
          "phase": "C",
          "seconds": 0.03370929998345673
        }
      ],
      "B_seconds": [
        0.22841870004776865
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007564000552520156,
        0.000530000077560544,
        0.0006775000365450978,
        0.0007004999788478017,
        0.0007241000421345234,
        0.0006821999559178948,
        0.0008327000541612506,
        0.0007093999302014709,
        0.0009453999809920788,
        0.0007153000915423036,
        0.0007875999435782433,
        0.0008120998973026872,
        0.017274299985729158
      ],
      "peer_max_seconds": 0.017274299985729158,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 5,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 1.1663549999939278
        },
        {
          "phase": "C",
          "seconds": 0.03550619992893189
        }
      ],
      "B_seconds": [
        0.2116205000784248
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007311999797821045,
        0.0005856000352650881,
        0.0007763000903651118,
        0.0009068000363186002,
        0.0007057000184431672,
        0.0008008999284356833,
        0.0007914000889286399,
        0.0007427999516949058,
        0.0006441000150516629,
        0.0006373999640345573,
        0.009090200066566467,
        0.027092000003904104,
        0.0005749999545514584
      ],
      "peer_max_seconds": 0.027092000003904104,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": false,
      "margin_pass": false,
      "pass": false,
      "caller": "admit_saved",
      "sample": 6,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.16301659995224327
        },
        {
          "phase": "C",
          "seconds": 0.03883019997738302
        }
      ],
      "B_seconds": [
        0.24693900009151548
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007605999708175659,
        0.0007569000590592623,
        0.0009198000188916922,
        0.0005562999285757542,
        0.0008190000662580132,
        0.0008736000163480639,
        0.0008980000857263803,
        0.0008230000967159867,
        0.0007838000310584903,
        0.0007580999517813325,
        0.0010116000194102526,
        0.016764100058935583,
        0.008028400014154613
      ],
      "peer_max_seconds": 0.016764100058935583,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 7,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.16530280001461506
        },
        {
          "phase": "C",
          "seconds": 0.03406400000676513
        }
      ],
      "B_seconds": [
        0.20068169990554452
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005969000048935413,
        0.00048619997687637806,
        0.0006042999448254704,
        0.0007486999966204166,
        0.0004558000946417451,
        0.0006846999749541283,
        0.0007401000475510955,
        0.0006401999853551388,
        0.0007004999788478017,
        0.011031099944375455,
        0.00959469994995743,
        0.0004550999728962779
      ],
      "peer_max_seconds": 0.011031099944375455,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 8,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1656033000908792
        },
        {
          "phase": "C",
          "seconds": 0.03505879989825189
        }
      ],
      "B_seconds": [
        0.19140730006620288
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0013592999894171953,
        0.0007343000033870339,
        0.0007085000397637486,
        0.0007739000720903277,
        0.0006882000016048551,
        0.0006297000218182802,
        0.0006933999247848988,
        0.0006473999237641692,
        0.0006911999080330133,
        0.006411199923604727,
        0.005233400035649538
      ],
      "peer_max_seconds": 0.006411199923604727,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 9,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.16865949996281415
        },
        {
          "phase": "C",
          "seconds": 0.03456399997230619
        }
      ],
      "B_seconds": [
        0.19302590005099773
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006980999605730176,
        0.0005811000009998679,
        0.0006627999246120453,
        0.0005477999802678823,
        0.0007563000544905663,
        0.0007072000298649073,
        0.0006939000450074673,
        0.000826900009997189,
        0.0005452999612316489,
        0.0006844999734312296,
        0.0006392000941559672,
        0.000610699993558228,
        0.0004339999286457896
      ],
      "peer_max_seconds": 0.000826900009997189,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "admit_saved",
      "sample": 10,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13401849998626858
        },
        {
          "phase": "C",
          "seconds": 0.07154589996207505
        }
      ],
      "B_seconds": [
        0.19895650004036725
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0008549999911338091,
        0.0005250000394880772,
        0.0006644000532105565,
        0.0007718000560998917,
        0.0009685000404715538,
        0.0007679000264033675,
        0.0005299999611452222,
        0.0006364000728353858,
        0.000929499976336956,
        0.0008428000146523118,
        0.0007818000158295035,
        0.0007986000273376703
      ],
      "peer_max_seconds": 0.0009685000404715538,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 1,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13806299993302673
        },
        {
          "phase": "C",
          "seconds": 0.07932010001968592
        }
      ],
      "B_seconds": [
        0.20879529998637736
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006062000757083297,
        0.000516400090418756,
        0.0007845999207347631,
        0.0006776999216526747,
        0.0008103000000119209,
        0.0008153999224305153,
        0.0007193000055849552,
        0.0006651000585407019,
        0.0007133999606594443,
        0.000763599993661046,
        0.009638500050641596,
        0.00815190002322197
      ],
      "peer_max_seconds": 0.009638500050641596,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 2,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1333867999492213
        },
        {
          "phase": "C",
          "seconds": 0.07612300000619143
        }
      ],
      "B_seconds": [
        0.21768350002821535
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0008563000010326505,
        0.0007868999382480979,
        0.0005790999857708812,
        0.0007365000201389194,
        0.000785200041718781,
        0.0007913999725133181,
        0.0007370999082922935,
        0.0006158000323921442,
        0.0007924000965431333,
        0.0007820000173524022,
        0.013173700077459216,
        0.0008009999291971326,
        0.0006698000943288207
      ],
      "peer_max_seconds": 0.013173700077459216,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 3,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1310446000425145
        },
        {
          "phase": "C",
          "seconds": 0.07215889997314662
        }
      ],
      "B_seconds": [
        0.19507580006029457
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007692999206483364,
        0.0005836000200361013,
        0.0006303999107331038,
        0.0005855000345036387,
        0.0006852000951766968,
        0.00072160002309829,
        0.0005981000140309334,
        0.0008068999741226435,
        0.0006784000433981419,
        0.000717200106009841,
        0.0008104000007733703,
        0.0005006000865250826,
        0.0004091999726369977
      ],
      "peer_max_seconds": 0.0008104000007733703,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 4,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12720670003909618
        },
        {
          "phase": "C",
          "seconds": 0.06936039996799082
        }
      ],
      "B_seconds": [
        0.20274380000773817
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000631700037047267,
        0.0008660999592393637,
        0.0007375000277534127,
        0.0010843999916687608,
        0.0007353000110015273,
        0.0007218000246211886,
        0.0008031000616028905,
        0.0007383000338450074,
        0.0006537999724969268,
        0.010769199929200113,
        0.013699800008907914,
        0.00041799992322921753
      ],
      "peer_max_seconds": 0.013699800008907914,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 5,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13522749999538064
        },
        {
          "phase": "C",
          "seconds": 0.06925699999555945
        }
      ],
      "B_seconds": [
        0.19554880005307496
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0010912999277934432,
        0.0005465000867843628,
        0.0008045000722631812,
        0.0005644999910145998,
        0.0006347000598907471,
        0.0006600000197067857,
        0.0007133999606594443,
        0.0009062999160960317,
        0.0007564000552520156,
        0.01312120002694428,
        0.0005629000952467322,
        0.004241499933414161,
        0.0006221000803634524
      ],
      "peer_max_seconds": 0.01312120002694428,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 6,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14582470001187176
        },
        {
          "phase": "C",
          "seconds": 0.07658870005980134
        }
      ],
      "B_seconds": [
        0.22700409998651594
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006433998933061957,
        0.0007336999988183379,
        0.0007058000192046165,
        0.0009613999864086509,
        0.0009058000287041068,
        0.0007811998948454857,
        0.0005677000153809786,
        0.0007462999783456326,
        0.000906099914573133,
        0.000682000070810318,
        0.000681400066241622,
        0.008009699988178909,
        0.00836489989887923
      ],
      "peer_max_seconds": 0.00836489989887923,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 7,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13884700008202344
        },
        {
          "phase": "C",
          "seconds": 0.09078079997561872
        }
      ],
      "B_seconds": [
        0.22692050004843622
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0010103000095114112,
        0.0008590000215917826,
        0.0006938000442460179,
        0.0006895000115036964,
        0.0007003999780863523,
        0.0007647000020369887,
        0.0008796999463811517,
        0.0006151000270619988,
        0.0009318999946117401,
        0.0006376999663189054,
        0.013287400011904538,
        0.03153300005942583
      ],
      "peer_max_seconds": 0.03153300005942583,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 8,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14380550000350922
        },
        {
          "phase": "C",
          "seconds": 0.07673419988714159
        }
      ],
      "B_seconds": [
        0.2235398000339046
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006442000158131123,
        0.0007124999538064003,
        0.0007247000467032194,
        0.001196600031107664,
        0.0007940001087263227,
        0.0007429999532178044,
        0.0007642999989911914,
        0.0007746000774204731,
        0.0008243999909609556,
        0.0007164999842643738,
        0.0008720000041648746,
        0.009956999914720654,
        0.009942000033333898
      ],
      "peer_max_seconds": 0.009956999914720654,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 9,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1319620000431314
        },
        {
          "phase": "C",
          "seconds": 0.06884299998637289
        }
      ],
      "B_seconds": [
        0.1971315999981016
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0008564000017940998,
        0.0007930999854579568,
        0.0009308999869972467,
        0.0011178000131621957,
        0.00080289994366467,
        0.000637899967841804,
        0.0008807000704109669,
        0.0009527000365778804,
        0.0007076000329107046,
        0.0007633999921381474,
        0.0007022999925538898,
        0.01089590007904917,
        0.0005043999990448356
      ],
      "peer_max_seconds": 0.01089590007904917,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "reject_response",
      "sample": 10,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07812970003578812
        },
        {
          "phase": "C",
          "seconds": 0.06806980003602803
        }
      ],
      "B_seconds": [
        0.1949400999583304
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006344999419525266,
        0.0006295999046415091,
        0.0006706999847665429,
        0.0006985999643802643,
        0.0007729999488219619,
        0.0006928000366315246,
        0.000938400044105947,
        0.0006948999362066388,
        0.0005562000442296267,
        0.03964219999033958
      ],
      "peer_max_seconds": 0.03964219999033958,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 1,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08251089998520911
        },
        {
          "phase": "C",
          "seconds": 0.07518389995675534
        }
      ],
      "B_seconds": [
        0.19580610003322363
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006076999707147479,
        0.0005051000043749809,
        0.0007954000029712915,
        0.0009507000213488936,
        0.0006946000503376126,
        0.000709200045093894,
        0.0008679999737069011,
        0.0013226000592112541,
        0.0008580998983234167,
        0.0006579000037163496,
        0.026751800091005862,
        0.0004878999898210168
      ],
      "peer_max_seconds": 0.026751800091005862,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 2,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08131400006823242
        },
        {
          "phase": "C",
          "seconds": 0.06866600003559142
        }
      ],
      "B_seconds": [
        0.1937733000377193
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000588799943216145,
        0.000658900011330843,
        0.0007117999484762549,
        0.0006315999198704958,
        0.0007059000199660659,
        0.0005119000561535358,
        0.0006179000483825803,
        0.000658600009046495,
        0.0006555999862030149,
        0.03695089998655021
      ],
      "peer_max_seconds": 0.03695089998655021,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 3,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08046079997438937
        },
        {
          "phase": "C",
          "seconds": 0.06882150005549192
        }
      ],
      "B_seconds": [
        0.19259420002344996
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006195999449118972,
        0.0004482000367715955,
        0.0007370999082922935,
        0.0011211000382900238,
        0.0007384999189525843,
        0.0007117999484762549,
        0.000611299998126924,
        0.0007554000476375222,
        0.0007702999282628298,
        0.000610699993558228,
        0.0268748999806121,
        0.00046909996308386326
      ],
      "peer_max_seconds": 0.0268748999806121,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 4,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08184340002480894
        },
        {
          "phase": "C",
          "seconds": 0.07043119997251779
        }
      ],
      "B_seconds": [
        0.2020566000137478
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007282000733539462,
        0.0007974999025464058,
        0.0008860999951139092,
        0.0008134000236168504,
        0.000511899939738214,
        0.0007578999502584338,
        0.0008403999963775277,
        0.0007069999119266868,
        0.0006064999615773559,
        0.039995200000703335
      ],
      "peer_max_seconds": 0.039995200000703335,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 5,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07878099998924881
        },
        {
          "phase": "C",
          "seconds": 0.06931459996849298
        }
      ],
      "B_seconds": [
        0.19881540001370013
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006692999741062522,
        0.0005539000267162919,
        0.0006944999331608415,
        0.0008086999878287315,
        0.0008149000350385904,
        0.0005724999355152249,
        0.0008819999638944864,
        0.0011986999306827784,
        0.0008206999627873302,
        0.0008302000351250172,
        0.03464870003517717
      ],
      "peer_max_seconds": 0.03464870003517717,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 6,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07984170003328472
        },
        {
          "phase": "C",
          "seconds": 0.06594460003543645
        }
      ],
      "B_seconds": [
        0.18588440003804862
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007399999303743243,
        0.0007367999060079455,
        0.000629299902357161,
        0.0006265999982133508,
        0.0005789999850094318,
        0.0007353000110015273,
        0.0007954000029712915,
        0.0008242999901995063,
        0.0005817998899146914,
        0.02682119992095977
      ],
      "peer_max_seconds": 0.02682119992095977,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 7,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07999510003719479
        },
        {
          "phase": "C",
          "seconds": 0.06522049999330193
        }
      ],
      "B_seconds": [
        0.18720149993896484
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006970000686123967,
        0.0004760000156238675,
        0.0006355000659823418,
        0.0006037999410182238,
        0.0007535000331699848,
        0.0008267998928204179,
        0.0007306999759748578,
        0.0006484999321401119,
        0.0005516000092029572,
        0.0006826999597251415,
        0.026315299910493195
      ],
      "peer_max_seconds": 0.026315299910493195,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 8,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08632689993828535
        },
        {
          "phase": "C",
          "seconds": 0.0873767000157386
        }
      ],
      "B_seconds": [
        0.20235569996293634
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005454999627545476,
        0.0007317999843508005,
        0.0007556000491604209,
        0.0007292999653145671,
        0.000591500080190599,
        0.0007662000134587288,
        0.0006804000586271286,
        0.0006129000103101134,
        0.0006946000503376126,
        0.04280759999528527,
        0.00047500000800937414
      ],
      "peer_max_seconds": 0.04280759999528527,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 9,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.09343050001189113
        },
        {
          "phase": "C",
          "seconds": 0.07011630001943558
        }
      ],
      "B_seconds": [
        0.22216210002079606
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007575000636279583,
        0.0006654999451711774,
        0.0007314999820664525,
        0.0005877000512555242,
        0.0007217999082058668,
        0.0009047999046742916,
        0.0006838999688625336,
        0.0009833999210968614,
        0.000864999950863421,
        0.000869500101543963,
        0.0007520000217482448,
        0.04077500000130385
      ],
      "peer_max_seconds": 0.04077500000130385,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "resume",
      "sample": 10,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12144520005676895
        },
        {
          "phase": "C",
          "seconds": 0.08110110007692128
        }
      ],
      "B_seconds": [
        0.1898197999689728
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006536999717354774,
        0.0006771000334993005,
        0.0007282000733539462,
        0.0007197000086307526,
        0.0009405000600963831,
        0.0007413000566884875,
        0.0008340999484062195,
        0.0009036000119522214,
        0.0007334999972954392,
        0.02603480010293424,
        0.0005204000044614077
      ],
      "peer_max_seconds": 0.02603480010293424,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 1,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12806240003556013
        },
        {
          "phase": "C",
          "seconds": 0.07730000000447035
        }
      ],
      "B_seconds": [
        0.1951555999694392
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006789999315515161,
        0.0005957999965175986,
        0.0009055000264197588,
        0.0010160000529140234,
        0.0007455000886693597,
        0.0007627999875694513,
        0.0007531000301241875,
        0.0008007999276742339,
        0.000665399944409728,
        0.034178500063717365,
        0.0005686999065801501
      ],
      "peer_max_seconds": 0.034178500063717365,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 2,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12482919998001307
        },
        {
          "phase": "C",
          "seconds": 0.07652470003813505
        }
      ],
      "B_seconds": [
        0.18463369994424284
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000775999971665442,
        0.000695300055667758,
        0.0008103000000119209,
        0.0006926000351086259,
        0.000610099988989532,
        0.0005653999978676438,
        0.0006620000349357724,
        0.0007445000810548663,
        0.0007662000134587288,
        0.025774699985049665,
        0.002681800047867
      ],
      "peer_max_seconds": 0.025774699985049665,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 3,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1317597999004647
        },
        {
          "phase": "C",
          "seconds": 0.07850140007212758
        }
      ],
      "B_seconds": [
        0.1935793999582529
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006766000296920538,
        0.0006529999664053321,
        0.0008150000358000398,
        0.0008306000381708145,
        0.0006847999757155776,
        0.0005658000009134412,
        0.0006119000026956201,
        0.0008757999166846275,
        0.0007110999431461096,
        0.00079109997022897,
        0.027303299983032048
      ],
      "peer_max_seconds": 0.027303299983032048,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 4,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12394239997956902
        },
        {
          "phase": "C",
          "seconds": 0.08858970005530864
        }
      ],
      "B_seconds": [
        0.19376780011225492
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006474999245256186,
        0.0007898000767454505,
        0.0007621999830007553,
        0.0009977000299841166,
        0.0007577999494969845,
        0.0007458999752998352,
        0.0007649000035598874,
        0.0007012999849393964,
        0.0006811999483034015,
        0.000619300059042871,
        0.026006000000052154,
        0.0006692999741062522
      ],
      "peer_max_seconds": 0.026006000000052154,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 5,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12725820008199662
        },
        {
          "phase": "C",
          "seconds": 0.08566809992771596
        }
      ],
      "B_seconds": [
        0.1985285000409931
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006870999932289124,
        0.0007647000020369887,
        0.0008521999698132277,
        0.0007973000174388289,
        0.0007569000590592623,
        0.0007575000636279583,
        0.0007040000054985285,
        0.0007235999219119549,
        0.0008186000632122159,
        0.03464179998263717
      ],
      "peer_max_seconds": 0.03464179998263717,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 6,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12509139999747276
        },
        {
          "phase": "C",
          "seconds": 0.08078980003483593
        }
      ],
      "B_seconds": [
        0.20456670003477484
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000775699969381094,
        0.0007038000039756298,
        0.0007403999334201217,
        0.0012272000312805176,
        0.0007952000014483929,
        0.0007026999955996871,
        0.0006384999724105,
        0.0008451000321656466,
        0.0009547000518068671,
        0.0007159999804571271,
        0.031805000035092235
      ],
      "peer_max_seconds": 0.031805000035092235,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 7,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11704810010269284
        },
        {
          "phase": "C",
          "seconds": 0.07804000005126
        }
      ],
      "B_seconds": [
        0.18725720001384616
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007090999279171228,
        0.0008769000414758921,
        0.000973900081589818,
        0.0015776000218465924,
        0.000722200027666986,
        0.0007363999029621482,
        0.0007612999761477113,
        0.0006961999461054802,
        0.0006867999909445643,
        0.031979799969121814
      ],
      "peer_max_seconds": 0.031979799969121814,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 8,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12137669988442212
        },
        {
          "phase": "C",
          "seconds": 0.0917908000992611
        }
      ],
      "B_seconds": [
        0.19786310009658337
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007672999054193497,
        0.0007599999662488699,
        0.000510699930600822,
        0.0011228000512346625,
        0.0007524000247940421,
        0.0006405999884009361,
        0.0006002000300213695,
        0.0007165999850258231,
        0.0007062000222504139,
        0.03818110004067421
      ],
      "peer_max_seconds": 0.03818110004067421,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 9,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11911400000099093
        },
        {
          "phase": "C",
          "seconds": 0.07763569999951869
        }
      ],
      "B_seconds": [
        0.18938950006850064
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007692999206483364,
        0.0006344000576063991,
        0.0007937999907881021,
        0.0005304999649524689,
        0.0006787000456824899,
        0.0007730999495834112,
        0.0007406000513583422,
        0.0006476000417023897,
        0.0006700999801978469,
        0.027078700019046664,
        0.005953799933195114
      ],
      "peer_max_seconds": 0.027078700019046664,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": "ArtifactUnavailable",
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "retained_recovery",
      "sample": 10,
      "source_fault_hook_calls": 1,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": "after full successful bounded read/validation",
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07710570003837347
        },
        {
          "phase": "C",
          "seconds": 0.02908080001361668
        }
      ],
      "B_seconds": [
        0.20125459996052086
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007052000146359205,
        0.0007041998906061053,
        0.0007560000522062182,
        0.0007384000346064568,
        0.0008069999748840928,
        0.0006400001002475619,
        0.0007303999736905098,
        0.0007113000610843301,
        0.0008370999712496996,
        0.0007982999086380005,
        0.000646500033326447,
        0.0006826999597251415
      ],
      "peer_max_seconds": 0.0008370999712496996,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 1,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08926009992137551
        },
        {
          "phase": "C",
          "seconds": 0.030491000041365623
        }
      ],
      "B_seconds": [
        0.22393430001102388
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0009612999856472015,
        0.0008320000488311052,
        0.0009105000644922256,
        0.0007534000324085355,
        0.0008195999544113874,
        0.0009080000454559922,
        0.0008274000138044357,
        0.0008851999882608652,
        0.0006080999737605453,
        0.0006605000235140324,
        0.01166889991145581,
        0.010523200035095215,
        0.0008085999870672822
      ],
      "peer_max_seconds": 0.01166889991145581,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 2,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.08546339999884367
        },
        {
          "phase": "C",
          "seconds": 0.027097800048068166
        }
      ],
      "B_seconds": [
        0.19329339999239892
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007046000100672245,
        0.0006748000159859657,
        0.0005660000024363399,
        0.0007419999456033111,
        0.0005849000299349427,
        0.0008309000404551625,
        0.0007279000710695982,
        0.0007488999981433153,
        0.0007514000171795487,
        0.0006673999596387148,
        0.0006835999665781856
      ],
      "peer_max_seconds": 0.0008309000404551625,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 3,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07401110010687262
        },
        {
          "phase": "C",
          "seconds": 0.027518799994140863
        }
      ],
      "B_seconds": [
        0.1967826000181958
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005928999744355679,
        0.0054339999333024025,
        0.0007759000873193145,
        0.0007390000391751528,
        0.0008397999918088317,
        0.0008299999171867967,
        0.000883400090970099,
        0.000676599913276732,
        0.000745900091715157,
        0.0008657999569550157,
        0.004969600006006658,
        0.0006495000561699271
      ],
      "peer_max_seconds": 0.0054339999333024025,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 4,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07462420000229031
        },
        {
          "phase": "C",
          "seconds": 0.026854699943214655
        }
      ],
      "B_seconds": [
        0.19196329999249429
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0008642000611871481,
        0.0005237000295892358,
        0.0006739998934790492,
        0.0006764000281691551,
        0.0008013999322429299,
        0.0007184999994933605,
        0.000722800032235682,
        0.0006963000632822514,
        0.0007514000171795487,
        0.000685799983330071,
        0.0005967000033706427,
        0.011147800018079579,
        0.0031331999925896525
      ],
      "peer_max_seconds": 0.011147800018079579,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 5,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07456330000422895
        },
        {
          "phase": "C",
          "seconds": 0.028260399936698377
        }
      ],
      "B_seconds": [
        0.20095230010338128
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006874999962747097,
        0.0006163999205455184,
        0.0005721999332308769,
        0.0008953999495133758,
        0.0006164000369608402,
        0.0006862999871373177,
        0.0006568999961018562,
        0.0005657000001519918,
        0.0007430999539792538,
        0.0006418999982997775,
        0.0005879999371245503,
        0.0006346000591292977,
        0.0004344000481069088
      ],
      "peer_max_seconds": 0.0008953999495133758,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 6,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07419279997702688
        },
        {
          "phase": "C",
          "seconds": 0.029711499926634133
        }
      ],
      "B_seconds": [
        0.19563400000333786
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007504000095650554,
        0.0007814000127837062,
        0.0007380000315606594,
        0.0006067999638617039,
        0.0006678999634459615,
        0.0006134000141173601,
        0.0007328999927267432,
        0.0006738000083714724,
        0.0007108000572770834,
        0.005752600030973554,
        0.0006711999885737896
      ],
      "peer_max_seconds": 0.005752600030973554,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 7,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07502719992771745
        },
        {
          "phase": "C",
          "seconds": 0.02784700004849583
        }
      ],
      "B_seconds": [
        0.1917132999515161
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0009266999550163746,
        0.0006571999983862042,
        0.0007009000983089209,
        0.0007189000025391579,
        0.0008447000291198492,
        0.0007557000499218702,
        0.0007810000097379088,
        0.0006316999206319451,
        0.0007019999902695417,
        0.0007298999698832631,
        0.0006285000126808882
      ],
      "peer_max_seconds": 0.0009266999550163746,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 8,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07553820009343326
        },
        {
          "phase": "C",
          "seconds": 0.02757379994727671
        }
      ],
      "B_seconds": [
        0.19416149996686727
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006067999638617039,
        0.0004841000773012638,
        0.000609499984420836,
        0.0008933000499382615,
        0.0008093999931588769,
        0.0007386000361293554,
        0.0006611000280827284,
        0.0006958000594750047,
        0.000672800000756979,
        0.009434700012207031,
        0.00679320003837347
      ],
      "peer_max_seconds": 0.009434700012207031,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 9,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.07785860006697476
        },
        {
          "phase": "C",
          "seconds": 0.02713270008098334
        }
      ],
      "B_seconds": [
        0.19671759998891503
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006432000081986189,
        0.0007599999662488699,
        0.0006626000395044684,
        0.0007564999395981431,
        0.0006532000843435526,
        0.0006463000318035483,
        0.000645900028757751,
        0.0009353000205010176,
        0.0005499999970197678,
        0.008002899936400354,
        0.006969899986870587
      ],
      "peer_max_seconds": 0.008002899936400354,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "ack_repair",
      "sample": 10,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.038610100047662854
        },
        {
          "phase": "C",
          "seconds": 0.03307430003769696
        }
      ],
      "B_seconds": [
        0.1941552999196574
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006599000189453363,
        0.0007938999915495515,
        0.0006833999650552869,
        0.0005967000033706427,
        0.0008044999558478594,
        0.0006949000526219606,
        0.0006372000789269805,
        0.000677799922414124,
        0.0007677000248804688,
        0.0006368000758811831,
        0.0005747999530285597
      ],
      "peer_max_seconds": 0.0008044999558478594,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 1,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.038824399933218956
        },
        {
          "phase": "C",
          "seconds": 0.03443970007356256
        }
      ],
      "B_seconds": [
        0.19372440001461655
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006646000547334552,
        0.0005006999708712101,
        0.0006929000373929739,
        0.0005793999880552292,
        0.0007777999853715301,
        0.0007481001084670424,
        0.0005911999614909291,
        0.0005379000212997198,
        0.0006367999594658613,
        0.0005426000570878386,
        0.0005990999052301049,
        0.009023300022818148
      ],
      "peer_max_seconds": 0.009023300022818148,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 2,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.046116799931041896
        },
        {
          "phase": "C",
          "seconds": 0.03387069993186742
        }
      ],
      "B_seconds": [
        0.20684829994570464
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0007653000066056848,
        0.0009303999831900001,
        0.0006026000482961535,
        0.0007814000127837062,
        0.0007535000331699848,
        0.0007204000139608979,
        0.0006950999377295375,
        0.0005093000363558531,
        0.0007790999952703714,
        0.0007450999692082405,
        0.0006039000581949949,
        0.0005836000200361013
      ],
      "peer_max_seconds": 0.0009303999831900001,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 3,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.03844949998892844
        },
        {
          "phase": "C",
          "seconds": 0.033424100023694336
        }
      ],
      "B_seconds": [
        0.1859004000434652
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000593000091612339,
        0.0005364000098779798,
        0.0006013000383973122,
        0.0009021000005304813,
        0.0006824999582022429,
        0.0006648999406024814,
        0.0005769000854343176,
        0.0006705000996589661,
        0.0007967000128701329,
        0.0063596999971196055,
        0.0006315000355243683
      ],
      "peer_max_seconds": 0.0063596999971196055,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 4,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.039524200023151934
        },
        {
          "phase": "C",
          "seconds": 0.037957899970933795
        }
      ],
      "B_seconds": [
        0.20975279994308949
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000816499930806458,
        0.0004920999053865671,
        0.0006414999952539802,
        0.0008961999556049705,
        0.0007934999885037541,
        0.0008091999916359782,
        0.0013836000580340624,
        0.000619000056758523,
        0.0006147000240162015,
        0.0007418999448418617,
        0.0008226999780163169,
        0.0007647000020369887,
        0.0005867000436410308,
        0.0004428999964147806
      ],
      "peer_max_seconds": 0.0013836000580340624,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 5,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.03802530001848936
        },
        {
          "phase": "C",
          "seconds": 0.03517319995444268
        }
      ],
      "B_seconds": [
        0.21693200001027435
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.000559499952942133,
        0.0006204000674188137,
        0.0005750999553129077,
        0.0007945999968796968,
        0.001006699982099235,
        0.0008118998957797885,
        0.0006093999836593866,
        0.0007330999942496419,
        0.0005981000140309334,
        0.0007519000209867954,
        0.02008599997498095,
        0.0006302000256255269
      ],
      "peer_max_seconds": 0.02008599997498095,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 6,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.0383616000181064
        },
        {
          "phase": "C",
          "seconds": 0.03360730002168566
        }
      ],
      "B_seconds": [
        0.19259540003258735
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006178999319672585,
        0.0007269999478012323,
        0.0006989999674260616,
        0.0006702999817207456,
        0.0006968999514356256,
        0.0006884000031277537,
        0.0007655998924747109,
        0.0007236999226734042,
        0.0007175999926403165,
        0.0053143000695854425,
        0.0007109999423846602
      ],
      "peer_max_seconds": 0.0053143000695854425,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 7,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.039050100021995604
        },
        {
          "phase": "C",
          "seconds": 0.03385929996147752
        }
      ],
      "B_seconds": [
        0.18992599996272475
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006448000203818083,
        0.0006529000820592046,
        0.0006599999032914639,
        0.0007410000544041395,
        0.0008194999536499381,
        0.0005237000295892358,
        0.0006986000807955861,
        0.0009101999457925558,
        0.0008087999885901809,
        0.007985000032931566,
        0.005180899985134602
      ],
      "peer_max_seconds": 0.007985000032931566,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 8,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.038227500044740736
        },
        {
          "phase": "C",
          "seconds": 0.033286300022155046
        }
      ],
      "B_seconds": [
        0.18849070009309798
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0006017000414431095,
        0.005421199952252209,
        0.0008061999687924981,
        0.0007306999759748578,
        0.0008378999773412943,
        0.0006903999019414186,
        0.0007318999851122499,
        0.0005778999766334891,
        0.0006077999714761972,
        0.0008406999986618757,
        0.0005585999460890889,
        0.008955500088632107
      ],
      "peer_max_seconds": 0.008955500088632107,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 9,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.04132479999680072
        },
        {
          "phase": "C",
          "seconds": 0.03358940000180155
        }
      ],
      "B_seconds": [
        0.19105939997825772
      ],
      "B_authority_owned": [
        [
          false,
          false,
          false
        ]
      ],
      "peer_waits": [
        0.0005963000003248453,
        0.0006061999592930079,
        0.0008226999780163169,
        0.0006265999982133508,
        0.000822200090624392,
        0.0006048999493941665,
        0.0006594000151380897,
        0.0007051000138744712,
        0.0007686999160796404,
        0.0006402999861165881,
        0.0006700999801978469,
        0.0005590000655502081,
        0.0004061999497935176
      ],
      "peer_max_seconds": 0.0008226999780163169,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "caller": "startup_terminal",
      "sample": 10,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1024,
      "diagnostic_body_bytes": 8388608
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.15205639996565878
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.15440979995764792
      ],
      "peer_max_seconds": 0.15440979995764792,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.007552499999292195,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 1,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1777358999243006
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.18115590000525117
      ],
      "peer_max_seconds": 0.18115590000525117,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.00892550009302795,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 2,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14455970004200935
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.1469358999747783
      ],
      "peer_max_seconds": 0.1469358999747783,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.006621699896641076,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 3,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.15375820000190288
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.1561271999962628
      ],
      "peer_max_seconds": 0.1561271999962628,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.007379199960269034,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 4,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14586090005468577
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.14824170002248138
      ],
      "peer_max_seconds": 0.14824170002248138,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.006932200049050152,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 5,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.15382090001367033
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.15633910009637475
      ],
      "peer_max_seconds": 0.15633910009637475,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.0071084999945014715,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 6,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14312889997381717
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.14570550003554672
      ],
      "peer_max_seconds": 0.14570550003554672,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.0066383000230416656,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 7,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.15023169992491603
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.152738600037992
      ],
      "peer_max_seconds": 0.152738600037992,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.0067900000140070915,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 8,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.16035630006808788
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.16294770000968128
      ],
      "peer_max_seconds": 0.16294770000968128,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.007158400025218725,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 9,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.1530174999497831
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.15558030002284795
      ],
      "peer_max_seconds": 0.15558030002284795,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.008534599910490215,
      "response_bytes": 2638593,
      "caller": "healthy_brief_context",
      "sample": 10,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11747079994529486
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.12010319996625185
      ],
      "peer_max_seconds": 0.12010319996625185,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.0058981000911444426,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 1,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11558230000082403
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.1180558999767527
      ],
      "peer_max_seconds": 0.1180558999767527,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.005274800001643598,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 2,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11791089992038906
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.12041720002889633
      ],
      "peer_max_seconds": 0.12041720002889633,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.005699600093066692,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 3,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.12166179995983839
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.1252933000214398
      ],
      "peer_max_seconds": 0.1252933000214398,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.0057607999769970775,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 4,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11958699999377131
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.12200560001656413
      ],
      "peer_max_seconds": 0.12200560001656413,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.006306099938228726,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 5,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.14243000000715256
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.14628619991708547
      ],
      "peer_max_seconds": 0.14628619991708547,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.0067668999545276165,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 6,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11581530002877116
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.11863509996328503
      ],
      "peer_max_seconds": 0.11863509996328503,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.00560929998755455,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 7,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.13383219996467233
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.13700500002596527
      ],
      "peer_max_seconds": 0.13700500002596527,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.0061639000196009874,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 8,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11770010006148368
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.12023790006060153
      ],
      "peer_max_seconds": 0.12023790006060153,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.005668099969625473,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 9,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    },
    {
      "holds": [
        {
          "phase": "A",
          "seconds": 0.11905330000445247
        }
      ],
      "B_seconds": [],
      "B_authority_owned": [],
      "peer_waits": [
        0.1215892001055181
      ],
      "peer_max_seconds": 0.1215892001055181,
      "peer_errors": [],
      "replace_retries": {
        "A": 0,
        "B": 0,
        "C": 0
      },
      "exception_type": null,
      "hard_pass": true,
      "margin_pass": true,
      "pass": true,
      "outside_boundary_response_encode_seconds": 0.00596199999563396,
      "response_bytes": 2114672,
      "caller": "healthy_delivery",
      "sample": 10,
      "source_fault_hook_calls": 0,
      "authoring_requests": 129,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "source_fault": null,
      "diagnostic_body_objects": 1023,
      "diagnostic_body_bytes": 7864320
    }
  ],
  "phase_observations": [
    {
      "phase": "A",
      "seconds": 0.11196220002602786,
      "caller": "brief_context",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.18849429988767952,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "brief_context",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.06774960004258901,
      "caller": "brief_context",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.10952449997421354,
      "caller": "brief_context",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.18984749994706362,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "brief_context",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.06427570001687855,
      "caller": "brief_context",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.11257809994276613,
      "caller": "brief_context",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.18598990002647042,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "brief_context",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.0651126999873668,
      "caller": "brief_context",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.1596580999903381,
      "caller": "brief_context",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.4399716999614611,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 23,
      "caller": "brief_context",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.11745770007837564,
      "caller": "brief_context",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.13170540006831288,
      "caller": "brief_context",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.21898869995493442,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "brief_context",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.0808802000246942,
      "caller": "brief_context",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.12498459999915212,
      "caller": "brief_context",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.22402099997270852,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "brief_context",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.07165429997257888,
      "caller": "brief_context",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.11834919999819249,
      "caller": "brief_context",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.19619099993724376,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "brief_context",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.07716320001054555,
      "caller": "brief_context",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.11858529993332922,
      "caller": "brief_context",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.1929907000157982,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "brief_context",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.06734619999770075,
      "caller": "brief_context",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.10937700001522899,
      "caller": "brief_context",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.18737080006394535,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "brief_context",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.0656723000574857,
      "caller": "brief_context",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.11174910003319383,
      "caller": "brief_context",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.19598079996649176,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "brief_context",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.06599820009432733,
      "caller": "brief_context",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.08094440004788339,
      "caller": "delivery",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.19325040001422167,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "delivery",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.07467550004366785,
      "caller": "delivery",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.08444809995125979,
      "caller": "delivery",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.1838469000067562,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "delivery",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.06879010004922748,
      "caller": "delivery",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.09231370000634342,
      "caller": "delivery",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.1917191999964416,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "delivery",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.06714479997754097,
      "caller": "delivery",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.0870234000030905,
      "caller": "delivery",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.20926100003998727,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "delivery",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.07505200000014156,
      "caller": "delivery",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.07990479993168265,
      "caller": "delivery",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.1791575999232009,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "delivery",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.06928549997974187,
      "caller": "delivery",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.07952220004517585,
      "caller": "delivery",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.19109609990846366,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "delivery",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.06751490000169724,
      "caller": "delivery",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.09027599997352809,
      "caller": "delivery",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.18596839997917414,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "delivery",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.0691763999639079,
      "caller": "delivery",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.08582220005337149,
      "caller": "delivery",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.21924869995564222,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "delivery",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.06832980003673583,
      "caller": "delivery",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.07769830001052469,
      "caller": "delivery",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.19808969995938241,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "delivery",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.06763039994984865,
      "caller": "delivery",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.08183809998445213,
      "caller": "delivery",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.19275170005857944,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "delivery",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.06986869999673218,
      "caller": "delivery",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.1315885999938473,
      "caller": "submit_cli",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.20731069997418672,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "submit_cli",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.020559199969284236,
      "caller": "submit_cli",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.1253589999396354,
      "caller": "submit_cli",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.19251860002987087,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "submit_cli",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.021985100000165403,
      "caller": "submit_cli",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.13568780000787228,
      "caller": "submit_cli",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.19781000004149973,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "submit_cli",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.022417100029997528,
      "caller": "submit_cli",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.14770940004382282,
      "caller": "submit_cli",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.18398480000905693,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "submit_cli",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.01969520002603531,
      "caller": "submit_cli",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.15115760010667145,
      "caller": "submit_cli",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.1848189999582246,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "submit_cli",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.020355199929326773,
      "caller": "submit_cli",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.13234610005747527,
      "caller": "submit_cli",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.19258180004544556,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "submit_cli",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.020562499994412065,
      "caller": "submit_cli",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.13150679995305836,
      "caller": "submit_cli",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.2402132999850437,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "submit_cli",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.027485599974170327,
      "caller": "submit_cli",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.12677689990960062,
      "caller": "submit_cli",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.18634859996382147,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "submit_cli",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.020840600016526878,
      "caller": "submit_cli",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.12775159999728203,
      "caller": "submit_cli",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.19490180001594126,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "submit_cli",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.02052490005735308,
      "caller": "submit_cli",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.14128149999305606,
      "caller": "submit_cli",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.21073130005970597,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "submit_cli",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.02111159998457879,
      "caller": "submit_cli",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.177546999999322,
      "caller": "admit_saved",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.1877600000007078,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "admit_saved",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.032934000017121434,
      "caller": "admit_saved",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.16322569991461933,
      "caller": "admit_saved",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.19337560003623366,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "admit_saved",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.032762099988758564,
      "caller": "admit_saved",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.16419740009587258,
      "caller": "admit_saved",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.18943280004896224,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "admit_saved",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.03289949998725206,
      "caller": "admit_saved",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.1594251999631524,
      "caller": "admit_saved",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.19321950001176447,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "admit_saved",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.034046599990688264,
      "caller": "admit_saved",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.17983899998944253,
      "caller": "admit_saved",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.22841870004776865,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "admit_saved",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.03370929998345673,
      "caller": "admit_saved",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 1.1663549999939278,
      "caller": "admit_saved",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.2116205000784248,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "admit_saved",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.03550619992893189,
      "caller": "admit_saved",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.16301659995224327,
      "caller": "admit_saved",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.24693900009151548,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "admit_saved",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.03883019997738302,
      "caller": "admit_saved",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.16530280001461506,
      "caller": "admit_saved",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.20068169990554452,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "admit_saved",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.03406400000676513,
      "caller": "admit_saved",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.1656033000908792,
      "caller": "admit_saved",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.19140730006620288,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "admit_saved",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.03505879989825189,
      "caller": "admit_saved",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.16865949996281415,
      "caller": "admit_saved",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.19302590005099773,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "admit_saved",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.03456399997230619,
      "caller": "admit_saved",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.13401849998626858,
      "caller": "reject_response",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.19895650004036725,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "reject_response",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.07154589996207505,
      "caller": "reject_response",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.13806299993302673,
      "caller": "reject_response",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.20879529998637736,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "reject_response",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.07932010001968592,
      "caller": "reject_response",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.1333867999492213,
      "caller": "reject_response",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.21768350002821535,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "reject_response",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.07612300000619143,
      "caller": "reject_response",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.1310446000425145,
      "caller": "reject_response",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.19507580006029457,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "reject_response",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.07215889997314662,
      "caller": "reject_response",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.12720670003909618,
      "caller": "reject_response",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.20274380000773817,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "reject_response",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.06936039996799082,
      "caller": "reject_response",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.13522749999538064,
      "caller": "reject_response",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.19554880005307496,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "reject_response",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.06925699999555945,
      "caller": "reject_response",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.14582470001187176,
      "caller": "reject_response",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.22700409998651594,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "reject_response",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.07658870005980134,
      "caller": "reject_response",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.13884700008202344,
      "caller": "reject_response",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.22692050004843622,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "reject_response",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.09078079997561872,
      "caller": "reject_response",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.14380550000350922,
      "caller": "reject_response",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.2235398000339046,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "reject_response",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.07673419988714159,
      "caller": "reject_response",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.1319620000431314,
      "caller": "reject_response",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.1971315999981016,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "reject_response",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.06884299998637289,
      "caller": "reject_response",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.07812970003578812,
      "caller": "resume",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.1949400999583304,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "resume",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.06806980003602803,
      "caller": "resume",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.08251089998520911,
      "caller": "resume",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.19580610003322363,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "resume",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.07518389995675534,
      "caller": "resume",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.08131400006823242,
      "caller": "resume",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.1937733000377193,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "resume",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.06866600003559142,
      "caller": "resume",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.08046079997438937,
      "caller": "resume",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.19259420002344996,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "resume",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.06882150005549192,
      "caller": "resume",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.08184340002480894,
      "caller": "resume",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.2020566000137478,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "resume",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.07043119997251779,
      "caller": "resume",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.07878099998924881,
      "caller": "resume",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.19881540001370013,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "resume",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.06931459996849298,
      "caller": "resume",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.07984170003328472,
      "caller": "resume",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.18588440003804862,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "resume",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.06594460003543645,
      "caller": "resume",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.07999510003719479,
      "caller": "resume",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.18720149993896484,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "resume",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.06522049999330193,
      "caller": "resume",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.08632689993828535,
      "caller": "resume",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.20235569996293634,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "resume",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.0873767000157386,
      "caller": "resume",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.09343050001189113,
      "caller": "resume",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.22216210002079606,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "resume",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.07011630001943558,
      "caller": "resume",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.12144520005676895,
      "caller": "retained_recovery",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.1898197999689728,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "retained_recovery",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.08110110007692128,
      "caller": "retained_recovery",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.12806240003556013,
      "caller": "retained_recovery",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.1951555999694392,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "retained_recovery",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.07730000000447035,
      "caller": "retained_recovery",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.12482919998001307,
      "caller": "retained_recovery",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.18463369994424284,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "retained_recovery",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.07652470003813505,
      "caller": "retained_recovery",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.1317597999004647,
      "caller": "retained_recovery",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.1935793999582529,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "retained_recovery",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.07850140007212758,
      "caller": "retained_recovery",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.12394239997956902,
      "caller": "retained_recovery",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.19376780011225492,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "retained_recovery",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.08858970005530864,
      "caller": "retained_recovery",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.12725820008199662,
      "caller": "retained_recovery",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.1985285000409931,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "retained_recovery",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.08566809992771596,
      "caller": "retained_recovery",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.12509139999747276,
      "caller": "retained_recovery",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.20456670003477484,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "retained_recovery",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.08078980003483593,
      "caller": "retained_recovery",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.11704810010269284,
      "caller": "retained_recovery",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.18725720001384616,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "retained_recovery",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.07804000005126,
      "caller": "retained_recovery",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.12137669988442212,
      "caller": "retained_recovery",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.19786310009658337,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 10,
      "caller": "retained_recovery",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.0917908000992611,
      "caller": "retained_recovery",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.11911400000099093,
      "caller": "retained_recovery",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.18938950006850064,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "retained_recovery",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.07763569999951869,
      "caller": "retained_recovery",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.07710570003837347,
      "caller": "ack_repair",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.20125459996052086,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "ack_repair",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.02908080001361668,
      "caller": "ack_repair",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.08926009992137551,
      "caller": "ack_repair",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.22393430001102388,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "ack_repair",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.030491000041365623,
      "caller": "ack_repair",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.08546339999884367,
      "caller": "ack_repair",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.19329339999239892,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "ack_repair",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.027097800048068166,
      "caller": "ack_repair",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.07401110010687262,
      "caller": "ack_repair",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.1967826000181958,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "ack_repair",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.027518799994140863,
      "caller": "ack_repair",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.07462420000229031,
      "caller": "ack_repair",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.19196329999249429,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "ack_repair",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.026854699943214655,
      "caller": "ack_repair",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.07456330000422895,
      "caller": "ack_repair",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.20095230010338128,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "ack_repair",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.028260399936698377,
      "caller": "ack_repair",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.07419279997702688,
      "caller": "ack_repair",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.19563400000333786,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "ack_repair",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.029711499926634133,
      "caller": "ack_repair",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.07502719992771745,
      "caller": "ack_repair",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.1917132999515161,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "ack_repair",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.02784700004849583,
      "caller": "ack_repair",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.07553820009343326,
      "caller": "ack_repair",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.19416149996686727,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "ack_repair",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.02757379994727671,
      "caller": "ack_repair",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.07785860006697476,
      "caller": "ack_repair",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.19671759998891503,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "ack_repair",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.02713270008098334,
      "caller": "ack_repair",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.038610100047662854,
      "caller": "startup_terminal",
      "sample": 1
    },
    {
      "phase": "B",
      "seconds": 0.1941552999196574,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "startup_terminal",
      "sample": 1
    },
    {
      "phase": "C",
      "seconds": 0.03307430003769696,
      "caller": "startup_terminal",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.038824399933218956,
      "caller": "startup_terminal",
      "sample": 2
    },
    {
      "phase": "B",
      "seconds": 0.19372440001461655,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "startup_terminal",
      "sample": 2
    },
    {
      "phase": "C",
      "seconds": 0.03443970007356256,
      "caller": "startup_terminal",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.046116799931041896,
      "caller": "startup_terminal",
      "sample": 3
    },
    {
      "phase": "B",
      "seconds": 0.20684829994570464,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "startup_terminal",
      "sample": 3
    },
    {
      "phase": "C",
      "seconds": 0.03387069993186742,
      "caller": "startup_terminal",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.03844949998892844,
      "caller": "startup_terminal",
      "sample": 4
    },
    {
      "phase": "B",
      "seconds": 0.1859004000434652,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "startup_terminal",
      "sample": 4
    },
    {
      "phase": "C",
      "seconds": 0.033424100023694336,
      "caller": "startup_terminal",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.039524200023151934,
      "caller": "startup_terminal",
      "sample": 5
    },
    {
      "phase": "B",
      "seconds": 0.20975279994308949,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 14,
      "caller": "startup_terminal",
      "sample": 5
    },
    {
      "phase": "C",
      "seconds": 0.037957899970933795,
      "caller": "startup_terminal",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.03802530001848936,
      "caller": "startup_terminal",
      "sample": 6
    },
    {
      "phase": "B",
      "seconds": 0.21693200001027435,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "startup_terminal",
      "sample": 6
    },
    {
      "phase": "C",
      "seconds": 0.03517319995444268,
      "caller": "startup_terminal",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.0383616000181064,
      "caller": "startup_terminal",
      "sample": 7
    },
    {
      "phase": "B",
      "seconds": 0.19259540003258735,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "startup_terminal",
      "sample": 7
    },
    {
      "phase": "C",
      "seconds": 0.03360730002168566,
      "caller": "startup_terminal",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.039050100021995604,
      "caller": "startup_terminal",
      "sample": 8
    },
    {
      "phase": "B",
      "seconds": 0.18992599996272475,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 11,
      "caller": "startup_terminal",
      "sample": 8
    },
    {
      "phase": "C",
      "seconds": 0.03385929996147752,
      "caller": "startup_terminal",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.038227500044740736,
      "caller": "startup_terminal",
      "sample": 9
    },
    {
      "phase": "B",
      "seconds": 0.18849070009309798,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 12,
      "caller": "startup_terminal",
      "sample": 9
    },
    {
      "phase": "C",
      "seconds": 0.033286300022155046,
      "caller": "startup_terminal",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.04132479999680072,
      "caller": "startup_terminal",
      "sample": 10
    },
    {
      "phase": "B",
      "seconds": 0.19105939997825772,
      "authority_owned": [
        false,
        false,
        false
      ],
      "peer_samples_so_far": 13,
      "caller": "startup_terminal",
      "sample": 10
    },
    {
      "phase": "C",
      "seconds": 0.03358940000180155,
      "caller": "startup_terminal",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.15205639996565878,
      "caller": "healthy_brief_context",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.1777358999243006,
      "caller": "healthy_brief_context",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.14455970004200935,
      "caller": "healthy_brief_context",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.15375820000190288,
      "caller": "healthy_brief_context",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.14586090005468577,
      "caller": "healthy_brief_context",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.15382090001367033,
      "caller": "healthy_brief_context",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.14312889997381717,
      "caller": "healthy_brief_context",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.15023169992491603,
      "caller": "healthy_brief_context",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.16035630006808788,
      "caller": "healthy_brief_context",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.1530174999497831,
      "caller": "healthy_brief_context",
      "sample": 10
    },
    {
      "phase": "A",
      "seconds": 0.11747079994529486,
      "caller": "healthy_delivery",
      "sample": 1
    },
    {
      "phase": "A",
      "seconds": 0.11558230000082403,
      "caller": "healthy_delivery",
      "sample": 2
    },
    {
      "phase": "A",
      "seconds": 0.11791089992038906,
      "caller": "healthy_delivery",
      "sample": 3
    },
    {
      "phase": "A",
      "seconds": 0.12166179995983839,
      "caller": "healthy_delivery",
      "sample": 4
    },
    {
      "phase": "A",
      "seconds": 0.11958699999377131,
      "caller": "healthy_delivery",
      "sample": 5
    },
    {
      "phase": "A",
      "seconds": 0.14243000000715256,
      "caller": "healthy_delivery",
      "sample": 6
    },
    {
      "phase": "A",
      "seconds": 0.11581530002877116,
      "caller": "healthy_delivery",
      "sample": 7
    },
    {
      "phase": "A",
      "seconds": 0.13383219996467233,
      "caller": "healthy_delivery",
      "sample": 8
    },
    {
      "phase": "A",
      "seconds": 0.11770010006148368,
      "caller": "healthy_delivery",
      "sample": 9
    },
    {
      "phase": "A",
      "seconds": 0.11905330000445247,
      "caller": "healthy_delivery",
      "sample": 10
    }
  ],
  "product_pin": "4968e47059e2c744d0611f4d96293afe705fa9d7",
  "source_sha256": {
    "artifact_store.py": "6c92e79837400e79444353d1a10c6679ac6761db07bb8a2f48062fd75a212f1d",
    "artifact_service.py": "2a13f084071e6e12db61fcb6fdbeccfde030d5ffe1bd9add33422b297fd6e6d7",
    "mcp_bridge.py": "265dd38d36be915b8df6040222cac4de878ef9f8d498127cf99c1b0c253141b8",
    "api_seats.py": "a638aa9711b3b25e522654cee68fb91000e1349040cc2bd62fef034ed665c13d"
  },
  "fixed_order": [
    "brief_context",
    "delivery",
    "submit_cli",
    "admit_saved",
    "reject_response",
    "resume",
    "retained_recovery",
    "ack_repair",
    "startup_terminal",
    "healthy_brief_context",
    "healthy_delivery"
  ],
  "samples_per_caller": 10,
  "warmup_discarded": 0,
  "resampling": "None; every original miss, retry and error retained.",
  "cache_disclosure": "Warm after setup; structural report forces metadata reread. Cold restart tails unmeasured.",
  "phase_definition": "Outermost acquired main-thread boundary holds; B and C identified by private production hooks. No guard-copy or hypothetical C probe.",
  "peer_definition": "Repeated require_active on the same engine/catalog locks during real B. Waits include contention through completion; B has no wall clock gate.",
  "limits": {
    "hard": 0.27,
    "changed_hold_and_peer": 0.216,
    "import": 0.3
  },
  "fsync_mocked": false,
  "filesystem_primitives_verified_unpatched_before_counters": true,
  "detected_implementations": {
    "r2_diagnostic_owner": true,
    "d1_scandir": true,
    "d2_single_write_byte_identity": true
  },
  "r2_d1_d2_present": true,
  "authoring_schema": 2,
  "dirty_tree": false,
  "git_status_porcelain": "",
  "fixture_and_support_sha256": {
    "sealed_result_io.py": "9547ca48ba69383f6c93e2e31a4727588fa89212a87875c7ea1e1152580528df",
    "artifact_worker.py": "1e74591d026b283e2f037123b59c801a50030845872a8ae0f1b03a3f6d6ac73e",
    "tests/test_artifact_admission.py": "edd96860b9f115319f16bed4168e2ac78c84645261c47d62a036c5c96ca5ab3f",
    "tests/test_artifact_capability.py": "7d2ff157b9bf5250273ddad5c0c169aa551e349b38f3172af34fe5a92192d5f6",
    "tests/test_artifact_diagnostic_owner.py": "748a3aed6d85e7d72b7704f13ab46ae22938b6ee0a88b1c7f1efdd5a5fd8926c",
    "tests/test_artifact_import_benchmark.py": "83d5737c79cb5c7868b2980d1f8fcdbe8316a17d8301ec049569e28a71eb9c49",
    "tests/test_artifact_store.py": "094ba1791404a225a63b15606e12e2a608667ac305ae63e9d451be632dbd77f3",
    "tests/test_channel_import.py": "ae096f58491f8895e853bd39b0b94d6c3fa22ec0f5c7fdee61d774cdb57c87ec",
    "tests/test_restart_launch.py": "17f3893417eddee025ff43b6843eb5e5319e3f23198ea26cfad69c7da11e7843"
  },
  "tool_sha256": "e0eec5f34097eea9ae6f834ad4977476ce108fc74e6a7ea96ab70d8fa3b67af9",
  "closed_a1_base": "2c34bbfb159a3334ad4ba66eb7a8fbd4175594ca",
  "preserved_r2_parent": "be6fd6522474fe2fab0e6f0573ec6e9ccb9eab4a",
  "pass": false
}
```
