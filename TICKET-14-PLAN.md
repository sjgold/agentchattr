# Ticket14: recover an operator-selected CLI message

State: contract settled by the same AGY reviewer, with source-grounded precision amendments. Storage checkpoint b9763b2 independently bounded-PASS (focused15 and full744 tests, four expected skips). Candidate inspection implemented and tested as a bounded checkpoint below. No admission/transport/UI implementation or final acceptance yet.

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

## Implementation and verification sequence

1. Observed-red copied snapshot/import tests, minimal storage hardening, focused existing archive/message verification.
2. Freeze candidate/admission component contracts; observed-red identity/lineage/checkpoint/dedup/concurrency/persistence tests; implement dedicated operator transaction and reconciliation.
3. Observed-red queue hold/CLI proof/HTTP authentication tests; implement transport integration without weakening API authority.
4. Existing review-panel UI: explicit message ID, readonly preview, attribution/legacy confirmation, final/question actions, idempotent feedback. No general editing, skip or participant replacement.
5. Actual isolated Windows fake CLI/MCP integration and browser selection/attachment. Verify exact generations/injections/dispatches, after-Retry fences, original provenance, no quoted-command routing, Stop/corrected rejection, peer preservation, projection/ACK recovery, true native lifecycle cleanup.
6. Full regression, same AGY final frozen review/reproduction, post-merge checks before standing-authorized publication and issue closure.

Limits: no live providers/native AI clients, Desktop/global settings, participant replacement (#15), new scheduler or Omarchy acceptance. Imported provenance is rejected; trusted historical storage is not a general signature system.
