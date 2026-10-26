# Ticket 20: D4 ROOT observed reds and N follow-ups

Status: first ROOT red pin, production HELD for independent review. Product/tool bytes remain unchanged from a40af574; the previously accepted R2 N baseline is still green. One NEW root file tests/test_artifact_diagnostic_phases.py, plus five accepted test-only N follow-ups and explicit private test-interface documentation. No D4 implementation/gate, R3/operator/capacity/activation or push.

## Exact builder observation

Final ROOT module30methods in36.338s:33behavioral assertion FAIL records,28infrastructure AttributeError records,4existing guard methods PASS,0skips. Tracked1d8ef42b-976f-49b3-a487-2b032d1b1130 exited1. All28 errors name a genuinely absent frozen _persist_diagnostic_intent, _settle_diagnostic_intent, _capture_diagnostic_attachment or _diagnostic_legacy_marker; no fixture TypeError/KeyError or other unexpected error. The33failures are4entry guards +12writer ownership +7cancel progress +2Stop progress +2second writer progress +1MCP progress +1orphan scan +1startup snapshot +1startup cancel count +1startup terminal peer +1omitted-mark progress. These count subtests, not test methods. No timing acceptance is claimed from Event deadlines.

Earlier first-file run accidentally collected the imported ArtifactAdmissionTests class too (34tests,31FAIL/23ERROR plus fixture guards). Replaced the class import with a module alias, then expanded missing contract cases. The29-method expanded run33FAIL/28ERROR/3guards24.836s is retained in tracked6f943e43. Added one healthy combined-capture A1 guard, yielding the actual final30-method run above. No product edit between these observations; final counts are from execution, not inferred arithmetic.

## Per-method reachability inventory

B means observed behavioral failure, I means missing-API infrastructure error, G means existing guard. Every downstream invariant is required in green; an I error never proves the body below it.

|Method|Observed records|Reachability and unobserved follow-on|
|---|---|---|
|test_c_fulfilled_replay_ignores_queue_release_and_fences|1 I ERROR|Missing persist helper. Queue release/fence and replay result assertions require that hook and successful A/B; all currently unobserved.|
|test_c_live_claim_allows_acknowledged_transition|1 I ERROR|Missing persist helper. Live-set transition during B and terminal quarantine assertion unobserved until that helper exists.|
|test_c_settlement_never_reads_or_writes_diagnostic_owner|1 I ERROR|Missing settle helper. Diagnostic read/write traps are installed only after that lookup succeeds.|
|test_crash_after_durable_diagnostic_before_settlement_replays_safely|2 I ERROR|Missing settle helper in both callers. Durable file, no C/disposition, raw no-auto-recovery and retry-id equality require the real new C hook; all unobserved now.|
|test_diagnostic_driver_refuses_caller_held_boundary|3 B FAIL|Current healthy call succeeds under each engine/catalog/authoring lock; assertRaises fails3times. Exact private class/code/fixed503 and zero file effects follow only after refusal exists.|
|test_diagnostic_driver_refuses_unsupported_ownership_query|1 B FAIL|Current call succeeds with an enterable engine lock wrapper lacking callable ownership query. Typed internal refusal and no-write assertions remain unobserved.|
|test_diagnostic_durable_precedes_terminal_state_and_saved_disposition|1 G PASS|Existing guard PASS for reject and startup; cold diagnostic owner confirms row durability BEFORE effect. No new phase split proof inferred.|
|test_diagnostic_guard_uses_current_row_and_distinct_claim_key|1 I ERROR|Missing persist helper. Wrong diagnostic key vs actual authority target, frozen recursive fields, detached content and unchanged queued state require hook; unobserved.|
|test_diagnostic_io_is_outside_all_three_authority_locks_per_caller|12 B FAIL|12current real branches fail engine-lock ownership assertion inside writer. Catalog/authoring checks and successful result follow only after engine check passes; not claimed reached today.|
|test_diagnostic_io_releases_authority_boundary_for_cancel|7 B FAIL|7Event progress FAILs. Both futures are released/joined; C cancellation preservation, agent409/operator MutationResult and noACK/version checks occur only after peer progresses during B.|
|test_diagnostic_io_releases_authority_boundary_for_stop|2 B FAIL|2Event progress FAILs using actual source session/Stop sequence. Final cancelled/source_stopped/no version assertions currently unobserved.|
|test_diagnostic_reads_do_not_hold_authoring_lock_during_orphan_scan|1 B FAIL|Peer cancellation cannot finish while paused orphan stat owns authoring lock. Report/row postconditions require releasing that edge.|
|test_existing_quarantined_before_fence_crash_is_not_falsely_repaired|1 G PASS|Existing guard PASS. QUARANTINED-before-fence residual stays unrepaired, no fabricated repaired/admitted claim.|
|test_foreign_receipt_and_second_settlement_are_refused_without_effect|1 I ERROR|Missing settle helper. Forged key, valid original settlement and stale second attempt/no effects all currently unobserved.|
|test_fulfilled_ack_and_replay_do_not_gain_active_channel_requirement|3 I ERROR|3missing persist-helper errors. New inactive-channel traps after B are unobserved until hook exists.|
|test_guard_modes_capture_current_state_and_immutable_intent|12 I ERROR|12missing persist-helper errors. mode/state/frozen dataclass checks require actual captures, not proof from the AttributeError.|
|test_healthy_mcp_parent_and_brief_share_one_capture_boundary|1 G PASS|Existing A1 guard PASS: parent then brief observe same outer capture token and owned engine/catalog; must remain so after D4.|
|test_inactive_channel_a_maps_400_but_new_inactive_c_maps_409|1 I ERROR|Existing A400 half passes first. C half stops at absent persist helper; C409/type/state assertions unobserved.|
|test_legacy_discovered_during_metadata_replace_keeps_landed_bytes_and_refuses_c|1 I ERROR|Missing shared marker. Cross-file post-replace legacy change/landed-byte and held-no-C assertions unobserved.|
|test_legacy_marker_capture_never_waits_for_diagnostic_lock|1 I ERROR|Missing capture helper. Thread/marker/None-write refusal assertions start only after API exists; no current lock-isolation proof.|
|test_legacy_marker_is_created_before_authoring_load|1 I ERROR|AttributeError inside constructor load observer: marker absent. Event type/before-owner initialization assertion unobserved after lookup.|
|test_mcp_parent_first_context_has_no_outer_diagnostic_boundary|1 B FAIL|Real parent read then between-read packet damage reaches writer; peer Event progress FAIL. Fixed MCP error/state/one-parent assertions follow only after peer progress.|
|test_omitted_startup_request_is_reread_before_resume_pending_mark|1 B FAIL|Event peer update is blocked. After D4 progress, omitted item must stay active/None with no stale resume_pending overwrite or repair count.|
|test_producer_disappearing_after_diagnostic_refuses_c_without_transition|1 I ERROR|Missing persist helper. Actual managed-stop action and access/conflict/refusal state assertions unobserved.|
|test_request_diagnostic_reads_run_without_authority_or_authoring_locks|1 G PASS|Existing read guard PASS with observed callback. Caller executes outside boundary; this is not a new forced caller-held refusal.|
|test_second_writer_during_diagnostic_io_refuses_stale_settlement|2 B FAIL|2Event progress FAILs. Actual saved-result admission/version/ACK winner and stale-invalid-response/invalid-content conflict assertions unobserved until peer runs during B.|
|test_startup_diagnostic_io_has_per_item_boundaries_and_fresh_cancel_count|1 B FAIL|Event progress FAIL. Fresh cancellation/count outcome needs per-item C; no enqueue_repaired success inferred from current row.|
|test_startup_snapshot_is_outside_boundary_and_resume_marks_are_fresh|1 B FAIL|Current initial channel_names callback owns engine/catalog and fails. Task snapshot guard only; omitted-mark case tested separately above.|
|test_startup_terminal_diagnostic_allows_independent_peer|1 B FAIL|Event progress FAIL. Real retained terminal result disposition/actual count assertion requires peer completion in B.|
|test_unmatched_lookup_becoming_present_refuses_stale_receipt|1 I ERROR|Missing persist helper. New real reservation appearing during B, Cconflict and no retro-attachment assertions unobserved.|

The Event helper always releases/joins operation and peer before reporting its progress red. Fixture root cleanup is asserted afterward. Stop is real temporary service/engine sequencing, not HTTP/native acceptance. No live runtime/provider is used. Missing helper bodies remain unobserved explicitly as listed; no assertion below a red is counted as reached.

## F-1..F-5 follow-ups

* F-1: retained factory ledger is now NONEMPTY, so resetting it differs from preserving it. Added in-memory reset mutant1FAIL; cold cap+1 removal1FAIL; encoded cap removal1FAIL; depth and nonfinite guard removal each3FAIL/0ERROR, with explicit stale-mode failures checked. Stale parser tests seed the malformed known RAM value and call _check_diagnostics with schema validation bypassed ONLY for depth/nonfinite, so neither changed-value inequality nor record's later schema assumptions can mask the parsing check. This is an isolated white-box parser test, not a naturally valid saved history. Full raw5-check receipt below.
* F-2: both cold legacy authoring refusal and live check/persist legacy tests assert exact type ArtifactUnavailable, not a subclass or text alone.
* F-3: startup warnings compare multiplicity/order-independently; contract freezes no incidental list ordering. Healthy-diagnostics ACK conflict control creates the real conflicting_duplicate receipt with no held entry before corruption yields operator_recovery_required; no new ACK/disposition is manufactured.
* F-4: frozen private test-interface table in DIAGNOSTICS now names _encoded static seam/injection, _data fixture seeds, diagnostic RLock ownership observation, fingerprint Path.stat and snapshot Hex32-orNone return. PHASES clarifies guard.state/request_id/mode and intent diagnostic key/attachment attribute names for red review. Receipt/guard mismatch maps ArtifactConflict before effects. Startup-mapping mutation is integration, so earlier31breakdown corrected to23owner/core+6integration+1ZIP+1deterministic-order. ERROR-based earlier kills (cold-held parser follow-ons, lifecycle, get_brief/resume) are weaker evidence and remain labeled, not relabeled assertion kills; new parser follow-ups are direct failures in every mode.
* F-5: ZIP no-mutation snapshot narrowed to target owner, restored history and catalog, excluding unrelated source root. CHANNELS test pins the substantive backup-exclusion/delete-retention sentence together, rather than three fragments. No CHANNELS behavior/source change.

Green support baseline AFTER these follow-ups:114tests PASS17.395s,0failure/error/skip, trackedc9d5b20e-50cd-42be-9cd6-646d74a71764. Includes A1/MCP/R1golden, both R2 files and oversize/saturation. Separate from intentionally red D4 module. Earlier53R2support tests also passed8.586s. No full project discovery or gate. Deprecation warnings retained. Current product/tool/portable golden diff against a40af574 is empty.

## Structured final red records

```json
{
  "kind": "D4 ROOT observed reds; product unchanged from a40af574; not acceptance",
  "tests": 30,
  "failures": 33,
  "errors": 28,
  "skips": 0,
  "rows": [
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_c_fulfilled_replay_ignores_queue_release_and_fences",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_c_live_claim_allows_acknowledged_transition",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_c_settlement_never_reads_or_writes_diagnostic_owner",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_settle_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_crash_after_durable_diagnostic_before_settlement_replays_safely (caller='reject')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_settle_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_crash_after_durable_diagnostic_before_settlement_replays_safely (caller='startup')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_settle_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary (lock='engine')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "ArtifactUnavailable not raised"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary (lock='catalog')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "ArtifactUnavailable not raised"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary (lock='authoring')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "ArtifactUnavailable not raised"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_unsupported_ownership_query",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "ArtifactUnavailable not raised"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_durable_precedes_terminal_state_and_saved_disposition",
      "kind": "existing_guard"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_guard_uses_current_row_and_distinct_claim_key",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='cli')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='reject')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='brief')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='delivery')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='resume')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='retained')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='saved')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='fulfilled')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='ack')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='startup')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='unmatched')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_is_outside_all_three_authority_locks_per_caller (caller='startup_unmatched')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false : B owns engine lock"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_cancel (caller='cli')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_cancel (caller='reject')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_cancel (caller='brief')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_cancel (caller='delivery')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_cancel (caller='resume')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_cancel (caller='retained')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_cancel (caller='saved')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_stop (caller='cli')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_io_releases_authority_boundary_for_stop (caller='reject')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_reads_do_not_hold_authoring_lock_during_orphan_scan",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : authoring lock blocks cancellation during observational stat"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_existing_quarantined_before_fence_crash_is_not_falsely_repaired",
      "kind": "existing_guard"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_foreign_receipt_and_second_settlement_are_refused_without_effect",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_settle_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_fulfilled_ack_and_replay_do_not_gain_active_channel_requirement (caller='ack')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_fulfilled_ack_and_replay_do_not_gain_active_channel_requirement (caller='fulfilled')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_fulfilled_ack_and_replay_do_not_gain_active_channel_requirement (caller='startup')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='cli')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='reject')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='brief')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='delivery')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='resume')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='retained')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='saved')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='fulfilled')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='ack')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='startup')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='unmatched')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_guard_modes_capture_current_state_and_immutable_intent (caller='startup_unmatched')",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_healthy_mcp_parent_and_brief_share_one_capture_boundary",
      "kind": "existing_guard"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_inactive_channel_a_maps_400_but_new_inactive_c_maps_409",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_legacy_discovered_during_metadata_replace_keeps_landed_bytes_and_refuses_c",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactStore' object has no attribute '_diagnostic_legacy_marker'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_legacy_marker_capture_never_waits_for_diagnostic_lock",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactStore' object has no attribute '_capture_diagnostic_attachment'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_legacy_marker_is_created_before_authoring_load",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactStore' object has no attribute '_diagnostic_legacy_marker'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_mcp_parent_first_context_has_no_outer_diagnostic_boundary",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_omitted_startup_request_is_reread_before_resume_pending_mark",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_producer_disappearing_after_diagnostic_refuses_c_without_transition",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_request_diagnostic_reads_run_without_authority_or_authoring_locks",
      "kind": "existing_guard"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_second_writer_during_diagnostic_io_refuses_stale_settlement (caller='cli')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_second_writer_during_diagnostic_io_refuses_stale_settlement (caller='reject')",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_diagnostic_io_has_per_item_boundaries_and_fresh_cancel_count",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_snapshot_is_outside_boundary_and_resume_marks_are_fresh",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "True is not false"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_terminal_diagnostic_allows_independent_peer",
      "kind": "behavioral_failure",
      "exception": "AssertionError",
      "message": "False is not true : peer cannot progress until diagnostic I/O releases authority boundary"
    },
    {
      "test": "tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_unmatched_lookup_becoming_present_refuses_stale_receipt",
      "kind": "error",
      "exception": "AttributeError",
      "message": "'ArtifactService' object has no attribute '_persist_diagnostic_intent'"
    }
  ]
}
```

## Raw F-1 mutation follow-up receipt

```json
{
  "kind": "F1 follow-up mutations, in-memory only",
  "mutations": [
    {
      "label": "cold cap+1 check removed",
      "failures": 1,
      "errors": 0,
      "killed": true,
      "output": "F\n======================================================================\nFAIL: test_exact_metadata_cap_accepts_and_write_cap_refusal_precedes_body_put (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_exact_metadata_cap_accepts_and_write_cap_refusal_precedes_body_put)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 743, in test_exact_metadata_cap_accepts_and_write_cap_refusal_precedes_body_put\n    self.expect_diagnostic_unavailable(lambda:module.ArtifactDiagnosticStore(root))\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.029s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "encoded limit removed",
      "failures": 1,
      "errors": 0,
      "killed": true,
      "output": "F\n======================================================================\nFAIL: test_exact_metadata_cap_accepts_and_write_cap_refusal_precedes_body_put (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_exact_metadata_cap_accepts_and_write_cap_refusal_precedes_body_put)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 749, in test_exact_metadata_cap_accepts_and_write_cap_refusal_precedes_body_put\n    self.expect_diagnostic_unavailable(lambda:owner._encoded(frame))\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.027s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "depth guard removed: stale specifically fails",
      "failures": 3,
      "errors": 0,
      "killed": true,
      "output": "FFF\n======================================================================\nFAIL: test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate) (label='depth', mode='cold_raise')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 362, in test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate\n    self.expect_diagnostic_unavailable(lambda: diagnostic_class(root, hold_unreadable=False))\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n======================================================================\nFAIL: test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate) (label='depth', mode='cold_held')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 369, in test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate\n    self.expect_diagnostic_unavailable(owner._check_diagnostics)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n======================================================================\nFAIL: test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate) (label='depth', mode='stale')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 369, in test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate\n    self.expect_diagnostic_unavailable(owner._check_diagnostics)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.079s\n\nFAILED (failures=3)\n"
    },
    {
      "label": "finite guard removed: stale specifically fails",
      "failures": 3,
      "errors": 0,
      "killed": true,
      "output": "FFF\n======================================================================\nFAIL: test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate) (label='nonfinite', mode='cold_raise')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 362, in test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate\n    self.expect_diagnostic_unavailable(lambda: diagnostic_class(root, hold_unreadable=False))\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n======================================================================\nFAIL: test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate) (label='nonfinite', mode='cold_held')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 369, in test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate\n    self.expect_diagnostic_unavailable(owner._check_diagnostics)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n======================================================================\nFAIL: test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate (tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests.test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate) (label='nonfinite', mode='stale')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 369, in test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate\n    self.expect_diagnostic_unavailable(owner._check_diagnostics)\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_owner.py\", line 332, in expect_diagnostic_unavailable\n    with self.assertRaises(module.ArtifactDiagnosticsUnavailable) as caught:\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactDiagnosticsUnavailable not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.067s\n\nFAILED (failures=3)\n"
    },
    {
      "label": "factory resets retained NONEMPTY diagnostic ledger",
      "failures": 1,
      "errors": 0,
      "killed": true,
      "output": "F\n======================================================================\nFAIL: test_real_factory_does_not_create_or_reset_diagnostics_when_authoring_is_broken (tests.test_artifact_diagnostic_integration.ArtifactDiagnosticIntegrationTests.test_real_factory_does_not_create_or_reset_diagnostics_when_authoring_is_broken)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_integration.py\", line 176, in test_real_factory_does_not_create_or_reset_diagnostics_when_authoring_is_broken\n    ArtifactFactoryTests().test_real_factory_binds_before_catalog_recovers_before_threads_and_holds_corruption()\n    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_factory.py\", line 54, in test_real_factory_binds_before_catalog_recovers_before_threads_and_holds_corruption\n    app.configure({'server':{'data_dir':directory,'port':18300},'images':{'upload_dir':str(root/'uploads')},'agents':{}},session_token='FIXTURE')\n    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\app.py\", line 561, in configure\n    artifacts = ArtifactStore(data_dir, hold_unreadable=True)\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_integration.py\", line 173, in checked\n    self.assertEqual(path.read_bytes() if path.exists() else None,preserved)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: b'{\"v[23 chars]s\": {}, \"dispatch_overflow\": {}, \"store_overflow\": null}' != b'{\"v[23 chars]s\": {\"c33cca1a48cc58c596280328f0639100\": {\"id\"[488 chars]ull}'\n\n----------------------------------------------------------------------\nRan 1 test in 0.804s\n\nFAILED (failures=1)\n"
    }
  ]
}
```

## Green support log

```text
2026-10-26T11:32:37.763Z === started (pid 49252, agent 6c2a7241-eb44-423f-8d53-eb4cc5425ad8, shell: C:\Program Files\PowerShell\7\pwsh.exe)
2026-10-26T11:32:42.125Z err| .....................................C:\Users\SJG\Documents\CodePlayground\agentchattr\.venv-windows\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
2026-10-26T11:32:42.125Z err|   from starlette.testclient import TestClient as TestClient  # noqa
2026-10-26T11:32:55.931Z err| .............................................................................
2026-10-26T11:32:55.931Z err| ----------------------------------------------------------------------
2026-10-26T11:32:55.931Z err| Ran 114 tests in 17.395s
2026-10-26T11:32:55.931Z err| 
2026-10-26T11:32:55.931Z err| OK
2026-10-26T11:32:56.500Z === exited (code 0)

```
