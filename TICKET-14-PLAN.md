# Ticket14: recover an operator-selected CLI message

State: COMPLETE. Same-AGY source-grounded final FULL PASS; published origin/main4999c39342b85cfafc44bb373ad39cb6e0b57377 and issue14 confirmed closed. Post-merge806 total tests OK/four expected skips71.794s and syntax/diff pass. Final pack: TICKET-14-REVIEW.md; receipt: REVIEW-GEMINI-TICKET-14.md; usage: RECOVER-CLI-MESSAGES.md.

Base: published main `9de60a2e9c413dad789a3f06e91682684d74e46f`. Branch: `codex/ticket-14-selected-cli-result`. Scope: issue14, specification v1.7 SC-5 and CLI AT-21c, standing autonomous policy in STATUS.md. Ticket12 blocker and Ticket13 are closed. Independent review: [contract settlement](epics/6e815a47-c25b-4900-9e83-1be98cead36f/artifacts/ticket-14-contract-review/index.md). Same AGY remains final reviewer.

## Required outcome

An operator selects an existing channel message ID, inspects exact text and attribution, then explicitly attaches it as a final answer or question to the failed CLI logical turn. Ordinary chat cannot complete turns automatically. No model invocation, process launch/termination, participant replacement or source rewrite occurs during recovery.

Authenticated immutable seat identity is mandatory. Missing legacy turn association requires explicit operator attribution; known conflicting scope or unknown authorship rejects. After Retry, the original source and current replacement can have different identities. Preserve source provenance while atomically fencing the unconsumed replacement and admitting once under the current logical turn. Stop and corrected/superseded runs remain protected.

## Settled source and attribution boundaries

- Only ordinary chat in the session channel qualifies. Reject imported messages, routing-suppressed/quarantined entries, unverified_scope, typed session projections, system/leave and non-CLI sources. Name equality alone never proves authorship.
- Source metadata.seat_identity_id must match the current expected CLI identity OR an immutable superseded source attempt within the SAME run, logical turn and input revision. Use retained brief/queue/attempt lineage, never current name or template alone.
- All present run/turn/attempt/dispatch/input tags must match that specific source lineage. Complete authenticated dispatch association is machine_verified. Missing association requires literal confirm_operator_attribution=True and operator_attributed. Partial metadata cannot erase a known conflict.
- Imported history is display data. Strip identity/execution claims during import and always stamp imported=True. Harmless metadata, literal content, UID, timestamps, channel and reply links remain intact.
- Snapshot digest is full SHA256 of canonical JSON (UTF-8, sorted keys, compact separators, ensure_ascii=False, allow_nan=False). Native nonempty string UID is the global source identity; absent/null/empty legacy UID uses legacy-{message_id}-{snapshot_sha256[:16]} without rewriting history. Present non-string UIDs reject as malformed. This synthetic identifier supports deduplication, not authentication.
- Numeric message IDs start at0 and can be reused after clear/reload. Audit numeric IDs, but prevent global reuse by source_message_uid, not numeric ID alone. A UID under a different numeric ID is still the same source.
- Store the copied exact selected content and source hash/UID/identity/available attempt scope in the accepted event. Later source edits cannot change admitted content.

## Operator intent and first-writer rules

Inspect returns exact source snapshot/hash/UID and checkpoint {session_id, run_id, turn_id, attempt_id, input_revision}. Actual ID and SHA256 revision formats follow existing session schema.

Attach supplies request_id, message_id, message_uid, snapshot_hash, kind, checkpoint and confirm_operator_attribution. Content is always loaded server-side. Validate literal nonnegative message ID, strict allowlists, existing request-ID format, exact checkpoint and final/question content limits. No content override.

An exact already-admitted intent returns accepted_event_id before current Stop/Retry fences or source lookup; repair projection with dispatch=False and never trigger another successor. Changed intent under the same request ID conflicts. A new pending decision requires current unconsumed invocation, permitted state active/waiting/stalled/interrupted, no stop_id, no pending_retry and no corrected/superseded run. dispatch_eligible=False alone does not forbid content recovery.

Normal authenticated final and operator attachment race under the same engine RLock: the first durable admission wins. Completed replacement turns reject a new selection. Questions enter awaiting_input through the existing continuation contract. Independent first-pass input restrictions remain applicable.

## Transaction and transport boundary

1. Under coordinator RLock, validate copied source, current checkpoint, lineage, duplicate use and operator decision.
2. One SessionStore transaction commits the selected event and fences the current replacement attempt (reason superseded_by_operator_recovery), preserving true source identity/attempt separately. No fabricated live principal. Global source UID single-use is checked under the same SessionStore lock.
3. After releasing that store lock, hold the exact affected dispatch before cancelling it. No nested cross-store locks or cross-file atomicity claim. Queue IO failure cannot undo the durable admission/fence; reconciliation must complete hold/cancellation before any affected successor dispatch.
4. Project accepted content once with routing suppression. Preserve earlier results and unrelated jobs/peer seats.

Extend hold_recovered only for the settled queued/dispatched/acknowledged/uncertain/failed/cancelling replacement states, while preserving existing API behavior and exact result/dispatch binding. Same active/cancelling consumer still polls its cancellation; new claims on the held physical identity are blocked. Cancellation preserves cancellation IDs/receipts. Exit proof clears held cancelled records without rewriting cancellation history. Released/previously terminal cases must be handled explicitly against existing lifecycle rules, never inferred as process exit.

Dedicated SeatManager.selected_cli_exit_proof(instance_or_provenance, dispatch_id) keeps CLI ownership separate from API HMAC authority. Warm proof requires a retained verified TRUE-worker handle with actual integer exit and matching integer native-child exit receipt. Launcher shim exit is insufficient. Cold proof reuses Ticket9 exact provenance/receipt and observed-absence rules. Only genuine produced bases are allowed: observed_child_exit_and_ipc, durable_receipt_and_observed_absent, retained_native_handle_observed_end. No synthetic exit codes, force termination, lease extension, unsupported tmux proof or native POSIX acceptance.

## Frozen storage tranche

- MessageStore.get_snapshot(msg_id): literal int >=0 (bool/string/negative raise ValueError); returns deepcopy of the complete stored message or None if absent. Copies nested metadata/attachments under the store lock, performs no writes or UID migration. Existing get_by_id remains unchanged.
- archive.import_archive: every newly imported message receives copied dict metadata (non-dict becomes empty), stripping seat_identity_id, provenance, dispatch_id, run_id, turn_id, attempt_id, input_revision, routing_scope, quarantine_session_id and quarantine_reason; sets imported=True regardless of supplied value. Existing local messages and archive dedup/reply/content behavior remain intact.
- Later component signatures will be pinned in bounded tranches before their tests. Core public routes are operator-only GET /api/sessions/{session_id}/cli-message-candidate/{message_id} and POST /api/sessions/{session_id}/attach-cli-message. Strict bounded JSON, sanitized errors, no keys/internal paths. Admission ACK includes accepted_event_id, attribution and truthful transport_settled.

## Frozen candidate inspection tranche

SessionEngine.cli_message_candidate(session_id, message_id) serializes readonly inspection under the engine RLock. Session ID must be literal positive int and message ID literal nonnegative int; malformed input raises EventValidationError. Missing or ineligible source/session raises EventConflict with a sanitized explanation.

Response: session_id, message_id, message_uid, sender, channel, created_at (stored timestamp), text, snapshot_hash, eligible=True, attribution, requires_operator_confirmation, available_kinds=['final','question'], source_attempt_id and checkpoint. No raw metadata, runtime path, nonce, secret or process-control capability.

Checkpoint is exactly {session_id, run_id, turn_id, attempt_id, input_revision} for the CURRENT invocation. Source attempt is resolved separately: complete authenticated_dispatch tags match one current/historical source entry and return that source_attempt_id; incomplete legacy tags preserve conflicts but return source_attempt_id=None and operator_attributed. Historical candidates must match current run/turn/input and immutable expected identity. Mixed tags from different attempts reject. Unknown nonempty provenance rejects; absent provenance with known authenticated seat identity remains eligible legacy output.

Only managed CLI agent bindings, protocol1, unconsumed active/waiting/stalled/interrupted invocation, no Stop/pending retry qualify. A false dispatch_eligible flag does not reject content inspection. Text must satisfy existing final/question validation, without truncation. Previously consumed source UID is ineligible across all sessions; source numeric ID alone is not a global duplicate key.

This tranche adds inspection only. It does not admit content, mutate stores/queue, trigger dispatch, query exit proof, adopt workers or extend leases. It does not expose the HTTP endpoint yet.

## Frozen admission store tranche

SessionStore.admit_selected_cli_event(session_id, snapshot, *, request_id, message_uid, snapshot_hash, checkpoint, kind='final', confirm_operator_attribution=False, submitted_by='operator') returns the updated session. This internal method takes a copied full source snapshot; it recomputes reviewed source UID/hash and validates source lineage/current checkpoint inside the session transaction. Malformed inputs or conflicting intent fail closed without writes.

The accepted event retains current brief/run/turn/attempt/input IDs, source_identity_id/source_attempt_id and original snapshot sender separately, source_message_id/source_message_uid/snapshot_hash, exact copied content, attribution, provenance='operator_selected_cli_result', submitted_by and recovered_at. It stores selected_request binding request_id, checkpoint, source ID/UID/hash, kind, literal confirmation and operator label. A generated UUID-hex event_id remains stable across replay.

One transaction fences current target attempt with reason='superseded_by_operator_recovery' and the same request_id, then records content/progression. No live principal is fabricated. Global UID single-use and first-writer checks execute under SessionStore lock. Final/question follow existing progression and recovery resolution; pending retry, Stop, replaced run, consumed turn or stale checkpoint reject.

An exact admitted request replay precedes current fences and returns the stored decision without writing, timestamp changes, callbacks or progression. Changed reuse of request_id conflicts. Later MessageStore edits cannot alter accepted text. Failed persistence rolls back both in-memory fence and admission, preserving disk bytes.

Implemented and component-tested: helper12 PASS0.754s; root combined56 PASS4.653s and full768/four expected skips65.477s. Initial missing-method red preceded implementation. Shared final/question progression retains existing admission behavior; exact selected replay uses an explicit unchanged-transaction path without callbacks or writes. This tranche has no queue writes, projection, process proof or HTTP handler. Coordinator hold/cancel/reconciliation follows separately, preserving durable fence ordering.

## CLI transport and exit-proof tranche

Same AGY ratified keyword-only hold_recovered(..., selected_cli=False), with literal bool validation. Default False preserves Ticket13 states/refusals. True permits queued/dispatched/acknowledged/uncertain/failed/cancelling/released/cancelled and records recovery_hold.selected_cli=True. Hold installation preserves all existing record state, consumer, envelope, cancellation IDs/receipts and history. Cleared holds remain cleared.

CoordinatedQueue reconciles each durable superseded_by_operator_recovery fence by installing its exact hold before cancel_dispatch. Existing universal Stop precedence remains; selected mode can install the hold even if Stop already cancelled the record. Ordinary Retry fences do not acquire selected holds. No unrelated dispatch is cancelled. New claims remain blocked while the hold is uncleared; the existing owner still polls its cancelling dispatch.

settle_recovered accepts new CLI-only durable_receipt_and_observed_absent and retained_native_handle_observed_end bases ONLY for exact holds marked selected_cli=True. This preserves old API rejection of CLI-only proof. Existing observed_child_exit_and_ipc remains an allowlisted shared basis. Held cancelled transports clear via audit without rewriting cancellation history; held released transports settle under genuine proof.

SeatManager.selected_cli_exit_proof(frozen_provenance_or_instance, dispatch_id) validates exact managed CLI launch, approved server/root/effective settings, fingerprint, stored authenticated birth and receipt identity. Warm true-worker retained handle must match actual birth PID and have genuine integer exit; matching receipt must contain integer native-child exit. It never uses a launcher shim's exit as worker proof. Cold fallback reuses Ticket9 runtime_exit_proof. No handle close/control, worker adoption from this query or auth lease extension.

Root proof tests exercise real owned toy supervisor self-birth/retained native handles; child-exit receipts are explicitly supplied protocol fixtures and cold absence uses an algorithm seam. They do not claim a real CLI child ran or native cold absence acceptance. Actual CLI/MCP end-to-end verification remains required later.

## Engine attachment and operator HTTP tranche

SessionEngine.attach_cli_message(session_id, decision, *, submitted_by='operator') accepts exactly seven decision keys: request_id, message_id, message_uid, snapshot_hash, kind, checkpoint, confirm_operator_attribution. Actor label is a separate operator parameter. Content is loaded from MessageStore; no text override or worker principal is accepted.

Under coordinator RLock, validate decision and find exact prior selected_request before source lookup/current fences. Changed reuse conflicts. For a new decision, revalidate candidate/source copy/checkpoint and commit store admission/fence first. Reconcile holds/cancellation next, query exact frozen selected_transport provenance/dispatch with selected_cli_exit_proof, and clear ledger/session audit only after genuine proof and successful writes. Missing dispatch resolves via session audit without a fabricated queue record.

For a selected cancelling transport, confirm_local_exit permits retained_native_handle_observed_end only on its exact selected_cli hold with dispatch/identity binding. If Stop created the cancellation without cancellation_id, use exact persisted stop_id. Its internal source remains runtime_reconciliation; this is not a worker ACK. Then clear the held cancelled record and resolve session audit. Default API/ordinary Retry behavior remains unchanged.

ACK fields: status='admitted', session_id, accepted_event_id, kind, source_message_id, source_message_uid, attribution, transport_settled. Queue/proof settlement IO after content acceptance yields transport_settled=False, never a false success or lost content. First normally coordinated attachment projects once and permits eligible peer successor work. Exact replay/IO projection repair uses dispatch=False and never triggers another successor. Source deletion/edit or Stop after acceptance cannot invalidate exact ACK. Projection-before-backlink failure repairs by stable UID.

Operator-only GET /api/sessions/{session_id}/cli-message-candidate/{message_id} and POST /api/sessions/{session_id}/attach-cli-message use real existing security middleware. Successful responses are no-store. POST accepts at most8192 bytes, strict decision fields, unique JSON keys including nested checkpoint, and no content/authority overrides. Worker bearer alone is insufficient. Errors use existing sanitized event error mapping.

Evidence before full regression: helper engine initial2 missing-method RED0.108s; expanded12 had11PASS/1 active warm-proof failure0.856s (root0.864s), then scoped confirmation fix and final12PASS0.914s including Stop-ID fallback. Root HTTP initial2 missing-handler RED0.090s; expanded4 routes plus engine12/API routes4/cold settlement4 PASS24/1.897s. Root full802 tests OK/four expected skips70.279s, Python syntax/diff clean. That802-test checkpoint preceded the actual integration and browser checks recorded below.

## Implementation and verification sequence

1. Observed-red copied snapshot/import tests, minimal storage hardening, focused existing archive/message verification.
2. Freeze candidate/admission component contracts; observed-red identity/lineage/checkpoint/dedup/concurrency/persistence tests; implement dedicated operator transaction and reconciliation.
3. Observed-red queue hold/CLI proof/HTTP authentication tests; implement transport integration without weakening API authority.
4. Existing review-panel UI: explicit message ID, readonly preview, attribution/legacy confirmation, final/question actions, idempotent feedback. No general editing, skip or participant replacement.
5. Actual isolated Windows fake CLI/MCP integration and browser selection/attachment. Verify exact generations/injections/dispatches, after-Retry fences, original provenance, no quoted-command routing, Stop/corrected rejection, peer preservation, projection/ACK recovery, true native lifecycle cleanup.
6. Full regression, same AGY final frozen review/reproduction, post-merge checks before standing-authorized publication and issue closure.

Limits: no live providers/native AI clients, Desktop/global settings, participant replacement (#15), new scheduler or Omarchy acceptance. Imported provenance is rejected; trusted historical storage is not a general signature system.

## Settled precision: selected dispatch never published

A real queue.enqueue OSError leaves an interrupted run with a valid bound CLI invocation but no ledger record. Initial test_cli_missing_dispatch failed because reconciliation tried holding that nonexistent record and blocked an unrelated peer. This red was added AFTER full783/four skips passed; expanded3 tests also failed before the ratified fix.

Same AGY Section6 ratifies selected_transport audit on the superseded attempt: exact dispatch_id, seat_identity_id, copied frozen launch_provenance, resolved=False and resolved_at=None. A selected_cli=True hold lookup on an absent ledger record returns None; default API behavior still rejects absence. The coordinator derives only the affected unresolved identity hold from the durable session audit, while peers remain claimable.

QueueStore.claim accepts internal blocked_identity_ids and checks it AFTER existing active/cancelling-consumer polling, before a NEW claim. Published transports use their ordinary exact ledger holds; unresolved unpublished ones use this identity-scoped session hold. No fictitious queue entry or consumer ACK is created.

SessionStore.resolve_selected_transport(session_id, request_id, evidence) is internal only, invoked after genuine selected_cli_exit_proof. It requires literal local_ended=True, exact dispatch/seat/launch and allowed CLI basis against the frozen audit, marks resolved with immutable proof/time, and preserves byte-identical exact replay. Persistence failure rolls memory/disk back. It can resolve transport after Stop without bypassing content fences.

Root missing-dispatch3 plus queue/admission/API hold/settlement regression39 PASS3.180s. Full786 tests OK/four expected skips70.610s (shell4688a3af exit0). Earlier missing-dispatch red and broad CLI-basis API regression remain recorded. This786-test checkpoint preceded the later engine/HTTP and actual CLI checks.

## UI and actual integration verification

The existing-theme inline panel provides an explicit message number, exact readonly preview, machine or legacy operator attribution, required legacy checkbox and separate final/question actions. Request IDs survive uncertain acknowledgement; history supports exact release rechecks after reload. Close/Escape and channel changes invalidate stale previews. After question attachment, Close focuses the visible empty answer field. Index CSS226/JS228 versions load the new behavior.

Root actual UI finalza6r12aj and legacy-question6eb9bnjj passed with the original stored seven-field decisions. Desktop1280x900/mobile390x844 inspection verified consent gating, exact Unicode/CRLF preview, attachment, acknowledgement, history/reload, keyboard actions and channel hiding. No Continue submitted. New panel14px text/44px controls, contrast9.332:1, internal390px containment. Inherited whole-page header overflow717px and mechanical index warnings remain outside scope. Screenshots were inspected in tool output without portable file paths. Browser Harness had no daemon; existing Chrome extension supplied task-only QA without installs/settings changes. Full builder evidence is in ticket-14-browser-qa.

Actual Windows/local-fake cases passed individually: tagged-final7bfj2rgf, legacy-question4pe29lrq, after-retryajo5d4hu, tagged Stop50l46tq4 and both serves above. Exactly1 prior API generation per case; CLI injection1 or2 afterRetry. Original source identity, prior/source/rules/frozen profile preserved; actual replacement B late output rejected and quarantined. Inspect/attach/replay performed no lifecycle actuation. A separate exact-owned fixture termination then genuine retained worker/client waits and matching child receipt made same-intent transport settlement true. Healthy API peer stayed ready/unused. Every pass cleanup unresolved[].

First tagged-final2ua_bi5_ failed before chat/attach because a Unicode string was searched in escaped JSON. Root re-derived exact parsed equality and strengthened both assertions to compare parsed text. That original failure remains intact. Lifecycle draft lookups were corrected before execution to exact identity/launch rather than a hardcoded pre-Retry key.

## Native settlement failure and same-boot worker-handle correction

Second actual tagged-final7sop0n1_ preserved one real selected admission/projection and observed CLI client+worker end, but exact replay reported unsettled. Root native regression rebuilt actual Windows venv shim versus self-born worker PID at heartbeat admission: CLI and API each failed because the true-worker handle was discarded. Both failures0.878s preceded the source change.

Heartbeat now retains the verified true-worker handle separately as worker_process when original Popen PID differs from birth PID, preserving original Popen authority. Duplicate handles/true-PID launches keep existing behavior. No identity/exit/lease guard is relaxed. Native/proof/adoption32 pass11.137s; stronger native2 check exact unchanged lease during proof passes0.927s.

Unchanged tagged-final7bfj2rgf then passed. Same AGY independently bounded-passed2887184: native2/0.896s, focused75/7.538s and frozen804/four expected skips72.599s. That review excluded UI/tools and subsequent quarantine edits.

## Replacement quarantine correction and final builder checks

After-Retryio6ppxny actually rejected B's late MCP typed final but recorded no quarantine: a selected copy carried B's current attempt ID, so existing duplicate suppression mistook it for B's own admitted generation. Root's focused regression failed before the narrow guard correction. Operator-selected provenance now cannot suppress audit of actual late typed output; true typed duplicates retain their existing behavior. Focused58 pass5.552s. Unchanged after-Retryajo5d4hu then passed, including exact late-output quarantine and native lifecycle settlement. Original failure remains intact.

Final root full806 tests OK/four expected skips73.299s; base734 plus72 across10 dedicated modules. Existing turn recovery44.799s, corrected restart30.112s and session Stop21.930s integrations pass. Existing API lost-ACKisfhwjra passes with2 calls/2 posts/one event/projection/ACK and no peer invocation; cleanup unresolved[]. Node syntax and diff checks pass. No Python production changes followed these checks; the final question-Close JS focus refinement was separately exercised after reload.

Same AGY whole-ticket source/reproduction review FULL PASS for fc921ca:806 total tests/four expected skips80.458s and four independent actual CLI cases. Builder held publication over incorrect source descriptions in the initial report; reviewer reread source/callers, reran72 focused tests7.721s, verified raw logs/scratch and rewrote/re-evaluated the report. No implementation changed. Post-merge806 total tests/four skips71.794s and syntax/diff pass. Published source4999c39342b85cfafc44bb373ad39cb6e0b57377 and issue14 closure verified. See TICKET-14-REVIEW.md and REVIEW-GEMINI-TICKET-14.md for exact evidence and limits.
