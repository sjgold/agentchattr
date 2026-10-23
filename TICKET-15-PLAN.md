# Ticket15: replace or skip a missing participant

State: same-AGY contract and five precision amendments RATIFIED. Skip storage8834a8d, clone/replay964d3af and unified transport/native proofb9cd507 independently bounded-PASS. Tranche4 replacement-store/repair architecture ratified; store interfaces below freeze before observed-red tests. Replacement state/repair, engine/routes, projection/export and UI remain unimplemented. Finish Ticket15 through reviewed publication/closure, then stop; no next ticket.

Base: published main `55bd7cbea6367b299fc4c927f71cf4736480bd40`. Branch: `codex/ticket-15-participant-replacement`. Owner: Codex, claim `a99548d9-49eb-4f70-9cf1-d185414cbad5`. Independent reviewer: same AGY. Scope: issue15, specification v1.7 SC-5 and AT-21d/22. Ticket12 blocker and Tickets13/14 recovery are delivered.

## Outcome

An operator can replace the participant assigned to a failed current turn, preserving its role, approved source/rules/design and earlier accepted results. The new instance receives an immutable review brief and fresh attempt/brief/dispatch IDs. The run stays the same; only the affected current and unstarted future role assignments change. A missing coordinator uses this same path.

An operator can instead skip the current contribution. It stays explicitly missing in the transcript, downstream context and final output/export, never counted as agreement or an authentic reviewer answer. Skip does not erase the role's later assignments or silently skip the rest of the run.

Both operations fence old attempts durably before queue/process effects. They preserve permanent Stop/corrected-run fences and reject stale decisions. They make no claim that an old worker ended merely because its contribution was replaced or skipped.

## Source-grounded starting points

| Existing source | Reusable boundary |
| --- | --- |
| SessionEngine._current_checkpoint / retry_turn | Exact checkpoint_id+attempt_id, stalled/waiting/interrupted eligibility, durable intent/fence before side effects |
| SessionStore._event_update | Atomic JSON mutation under store lock, memory rollback on write failure, no nested cross-store transactions |
| SessionEngine._trigger_current / BriefStore.put | Approved immutable source/rules/design/prior context, API owner seal after binding, fresh typed attempt IDs |
| SeatManager.prepare_retry_context / prepare_clean_context | Frozen effective-profile fingerprinting, idempotent prepared keys, context metadata, fresh CLI contract, native readiness; existing methods do not implement the proposed replacement clone |
| runtime_adoption + manager proof helpers | True worker versus launcher, exact birth/receipt/native proof; live or uncertain processes never treated as ended |
| CoordinatedQueue._reconcile / QueueStore.claim | Permanent attempt fence and cancellation polling; same physical identity cannot take successor work while its lifecycle is unproven |
| cli_result_recovery and result_recovery | Content/transport separation, read-only inspection, exact replay before later fences, stable projection repair |
| SessionEngine._project_session / archive.build_export | Stable add_once projection, routing suppression, transcript JSONL export containing copied message metadata |

There is no existing graphify graph for this repository or registry entry; source/call-site reads supply the dependency map. No graph tool installation, provider call or graph rebuild is proposed.

## Approaches considered

| Approach | Assessment |
| --- | --- |
| Recommended: clone a selected managed seat's frozen profile into a fresh run-bound instance | Reuses owned launch/readiness and scoped brief delivery; selected source seat and unrelated jobs remain intact. Requires a small dedicated replacement-preparation path. |
| Rebind the role directly to an already-running selected seat | Smaller, but cannot honestly guarantee fresh native conversation or independent context. Reject as default. |
| Add replacement-specific provider/model editing and an independent launcher | Duplicates pre-flight settings and ownership mechanisms. Outside this ticket. |

The proposed picker selects a currently authenticated, app-owned API/CLI identity as a profile source. Preview shows sanitized adapter/provider/model/reasoning, fresh-context capability and exact affected future positions. It never accepts browser-supplied effective settings. Commit freezes server-derived provenance/fingerprint; replay cannot pick up later saved/template edits.

## Proposed operation contracts

The following names describe NEW interfaces, not existing implementations. Freeze exact schemas after critique and before helper test authoring.

- Read-only `SessionEngine.participant_recovery_options(session_id)` returns current checkpoint, missing role/current seat, sanitized managed replacement choices and skip impact. It performs no launch, adoption, cancellation or generation.
- Operator replacement decision binds request_id, checkpoint_id, old attempt_id, selected target_identity_id and target profile fingerprint from preview. Optional reason is bounded plain text. No model/source/role override.
- Operator skip decision binds request_id, checkpoint_id and old attempt_id, with an explicit bounded reason. Literal consent in UI makes missing contribution semantics visible.
- Tentative routes: GET `/api/sessions/{session_id}/participant-recovery`, POST `/api/sessions/{session_id}/replace-participant`, POST `/api/sessions/{session_id}/skip-participant`. Operator middleware only, strict unique-key bounded JSON, sanitized errors, no-store responses. Seat bearer alone insufficient.
- Exact request replay returns its persisted outcome/status before checking a later checkpoint, with safe projection/preparation inspection. Conflicting reuse of request_id rejects. Replays never silently allocate another generation, new IDs or another worker.

Eligibility starts with existing nonhuman current checkpoint rules: unconsumed invocation, current failed/waiting/interrupted checkpoint, no Stop, no corrected/superseded run and no pending Retry/replacement. Ordinary live/slow status alone never authorizes an inferred crash. Explicit operator choice may supersede live-but-stalled work without killing it.

## Replacement transaction and fresh context

1. Under coordinator RLock, revalidate checkpoint, target identity/profile and fresh-context capability. Compute affected unstarted positions for this role in the frozen design. Retain original cast_snapshot and completed event bytes.
2. One store transaction records request intent, exact old attempt fence, old transport audit and pending replacement with reserved new attempt/brief/dispatch IDs, frozen target provenance and same-boot explicit intent marker. No worker launch before this commit.
3. Reconcile cancellation/hold for only the old dispatch and identity. Do not globally revoke its bearer or terminate unrelated work. A different fresh physical seat can continue even when old exit is unproven.
4. Proposed `SeatManager.prepare_replacement_context` clones the frozen target profile into a distinct run/role/request-bound attempt. It does not call prepare_retry_context on the target source, because that method can terminate its original context. Pending intent before Popen and spawned outcome before model input remain mandatory.
5. API clone receives an isolated immutable request packet. CLI clone requires the existing verified fresh-context argument contract and configuration resource isolation. Unsupported freshness/shared locked settings block preparation rather than reusing history or ending the selected source seat. No overwrite of active native settings.
6. Wait for real ready/current-boot native identity proof and fresh context capability. Then atomically update this role's cast/participant binding and assignment audit; earlier results remain unchanged. Reuse normal brief construction/typed dispatch with the reserved new IDs and the same source/input revision.
7. Record sanitized effective old/new seat/model/reasoning and the exact current/future role positions. Completed assignments remain attributed to their original worker. Other roles, runs and background jobs remain untouched.

Cold restart must not create a worker or rerun pending replacement automatically. It inventories and leaves interrupted intent visible. Explicit repeat/repair can resume the exact reserved intent after fresh readiness. Before immutable brief authority exists, a failed preparation may be explicitly repaired using exact launch proof/consent like delivered Retry. After binding a brief or API seal, owner changes require a fresh explicit operation with new IDs; never rewrite the old brief/key.

## Skip and missing-work visibility

Ratified representation: a dedicated immutable `skipped_turns` audit, not a fake final/question in admitted_events. It records request/operator/reason, current role/phase/turn/input revision, old identity/attempt and a stable projection ID. The same atomic mutation fences the old attempt and advances the logical cursor once through a dedicated _advance_skipped_turn helper; ordinary _append_admission final/question validation stays unchanged.

Project a distinct routing-suppressed session notice: missing contribution, role/phase and operator reason. Include structured missing-contribution context in subsequent frozen briefs without substituting it for approved source or accepted results. Coordinator loss is not special: replacement retains the coordinator role; an explicitly skipped output/synthesis turn must finish as missing output, not a successful synthesis.

Final UI/output metadata and the existing archive JSONL must retain the missing list. Recommended final display adds a deterministic missing-contribution notice alongside an unchanged synthesis text; do not rely solely on a model obeying a prompt. If the output turn itself is skipped, expose a stable missing-output notice as the final output anchor. A new general Markdown/artifact exporter belongs to later tickets; verify existing export contains the notice and provenance now.

## Settled architecture and remaining precision

1. **Old physical-seat lifecycle hold:** Ratified old_transport audit on participant_replacement/participant_skipped fences, identity-scoped new-claim blocking for every unresolved old identity (published or missing dispatch), and preserved existing cancellation polling. No fake selected_cli/API seal. Ratified precision: a bare child/worker cancellation receipt cannot clear this physical hold; require strict true worker plus exact child/model lifecycle proof before audit resolution.
2. **Preparation and restart representation:** Ratified dedicated pending_replacement/replacement_requests and small `participant_recovery.py`, dedicated manager clone leaving profile-source seat intact, explicit repair_replacement and cold interrupted_pending_recovery with no auto-spawn. Ratified precision: durable fence/pending intent must precede any clone Popen; ownership is immutable after ANY persisted brief, including unsealed CLI, not only an API result seal. Seal is HMAC authentication, not encryption.
3. **Skip projection/output persistence:** Ratified skipped_turns outside admitted_events, dedicated _advance_skipped_turn, routing-suppressed missing notice, missing_contributions context and exact current-turn-only scope. Ratified precision: existing archive messages.jsonl retains skip audit via notice metadata, avoiding a new session backup format; missing_output denotes actual absent final output, not an earlier skipped contributor before another synthesis turn. Stable notice and first-dispatch IO-gap behavior will be frozen in their engine tranche.

## Frozen tranche1: skip store transaction

NEW `SessionStore.skip_participant(session_id, *, checkpoint_id, attempt_id, request_id, reason, confirm_skip, submitted_by='operator', now=None) -> copied session`. IDs are existing positive literal session ID and32hex request/checkpoint/attempt identifiers. confirm_skip must be literalTrue; reason nonempty valid UTF-8 text at most256 characters with no NUL; actor1..80 characters. Exact replay excludes now from intent and returns unchanged persisted session before later checkpoint/Stop tests; changed intent under the same request ID conflicts.

Under store._lock through _event_update, require an unconsumed nonhuman current invocation and exact persisted stalled/waiting/interrupted checkpoint, no Stop/replaced_by_run_id/pending_retry/pending_replacement or existing current attempt fence. One mutation records a participant_skipped fence with old_transport {dispatch_id, seat_identity_id, copied launch_provenance, resolvedFalse, resolved_atNone}, immutable skipped_turns record including original role/phase/turn/run/input/identity/attempt/reason/operator/time/projection_id, clears active_invocation and advances the cursor once. It never appends an admitted final/question or calls queue/messages/registry/manager.

NEW `_advance_skipped_turn(session, skip_record)` is an internal lock-held helper, not an external route. It performs the atomic fence/audit/cursor step without modifying _append_admission. Final output turn skip sets complete/missing_outputTrue. An earlier skipped participant in a multi-person output phase advances to the later participant without declaring its still-possible output missing. Preserve completed event bytes, original cast/design/source/rules and future role assignments. All write failures roll back memory and disk. Exact replay is byte/time/callback stable across reload, Stop and advanced cursor.

Helper owns only new tests/test_participant_skip_storage.py, bounded12 cases with explicit process doubles/no native proof. Initial2 actual missing-method errors0.119s precede implementation. Existing tests remain unchanged. Runtime/HTTP/UI/export claims are outside this tranche.

Tranche1 evidence: root independently reproduced initial2 missing-method errors0.108s. First expanded12 run had9 pass/3 fixture setup errors0.708s because its unique channel exceeded the existing20-character limit; helper shortened only that channel. An unreached projection_idNone assertion was corrected to stable32hex projection_id plus projected_message_idNone, matching the contract. Helper12 pass0.768s. Root unchanged12 plus selected/saved admission and Stop/events58 pass2.889s. Full818 total tests OK/four expected platform skips73.010s; Python syntax and diff whitespace pass. Store only, no queue/projection/process control. Same AGY bounded source/execution review is next.

## Frozen tranche2: initial managed replacement clone and replay

NEW `SeatManager.prepare_replacement_context(source_provenance, context_key, *, binding) -> context view`. binding is exactly {child_run_id, role}, using current run UUID and nonempty role. context_key is a bounded1..128 plain identifier. No retry_attempt/confirmation in this tranche: failed/live/uncertain preparation replay never replaces a worker. Explicit repair receives a later observed-red contract.

New preparation validates server-derived provenance fingerprint against the current owned source and real immutable config/launch records, current approved root/data/web/MCP and current registry identity. Require source native current-boot readiness. Source queries must never use cleanup/termination paths or extend its lease. Component tests may mock only that readiness boundary and label it nonnative; no invented birth metadata.

Use a stable replacement key independent of selected seat ID so a repeated context_key cannot silently switch sources. Persist source reference {key, launch_attempt, identity_id, fingerprint} as replacement_source with existing context_id/context_key/context_source_fingerprint/context_base_effective/child_run_id/role fields. Validate exact source/binding/metadata on warm/cold replay, returning the same attempt or failed/blocked view. Corrupt/pending/ambiguous disk evidence never permits blind Popen. Reuse recover_prepared_context for disk lineage without repair; adoption retains replacement_source metadata without broadening process authority.

Clone frozen base effective settings rather than edited saved/provider/template values. API gets a distinct worker. CLI requires verified fresh context args/new nonce and existing config_resource guard. Env/flag-generated MCP configuration remains attempt-scoped; active fixed settings-file ownership blocks before spawn instead of overwriting it or stopping its owner. Use existing _launch_effective pending/spawned journaling and hidden console behavior.

Source process/handle/files/registry/context and unrelated jobs remain intact. Clone is starting/unverified until its OWN genuine current-boot native proof plus ready receipt; receipt alone cannot report clean_contextTrue. Context view exposes only existing safe fields. No review brief, dispatch or model call in this component. Engine intent-before-clone ordering belongs to the later engine tests.

Helper owns only tests/test_prepare_replacement_context.py, bounded10-12 real manager/store/registry cases with explicit Popen/readiness doubles. Capture initial API clone/source-preservation plus invalid binding/key red before implementation. Cover drift, fresh CLI/resource refusal, exact replay/conflicting source, separate source/clone readiness, ownership/journal IO, strict source/root guards and cold failed/pending replay without respawn. No native lifecycle/engine/provider/UI acceptance claim.

Tranche1 independent review: same AGY bounded-PASS8834a8d, dedicated12/0.805s, focused80/4.018s, full818 total/four expected skips73.115s. Later wiring explicitly excluded.

Tranche2 evidence: helper2 tests/10 missing-method AttributeError observations0.083s; root independently reproduced2/10 observations0.363s before implementation. Initial unchanged2 pass0.109s after manager clone/replay plus replacement_source adoption whitelist. Existing47 regressions pass5.266s. Helper12 final pass0.799s; its first expanded run had10 pass and2 fixture assumptions, corrected to accept the existing safe failed view on pre-spawn write failure and use the public context key rather than an absent internal key field. No production assertion weakened. Root unchanged12 plus launch/owner/native/adoption/ownership/cold replay63 pass7.640s; full830 total tests OK/four expected skips72.847s. Python syntax/diff clean. Cold incomplete pending/birth or ambiguous records use existing safe SeatError refusal, never Popen; synchronous failed preparation returns the same failed attempt. New clone tests use explicit process/readiness doubles, no native replacement acceptance. Same AGY bounded source/execution review next.

## Ratified tranche3a: old identity hold and strict audit resolution

Same AGY independently bounded-PASS964d3af: dedicated12/0.780s, focused68/7.586s and full830 total/four expected skips73.581s. Initial cloning only; explicit repair remains unwritten.

This split implements durable old-identity holds and a trusted internal audit resolver before native proof collection/cancellation completion (tranche3b). No API seals or selected_cli flags are manufactured. For participant_replacement/participant_skipped fences, CoordinatedQueue._reconcile cancels only that dispatch and adds every unresolved old_transport identity to blocked_identity_ids, whether a ledger record exists or not. New identity/peers remain claimable, unrelated work is retained rather than cancelled.

NEW `SessionStore.resolve_old_transport(session_id, request_id, evidence) -> copied session`, internal only. Require literal local_endedTrue and exact dispatch_id/seat_identity_id/launch_attempt matching the frozen old_transport and its launch_provenance. Require wrapper_status observed_exited or absent. CLI requires one of observed_child_exit_and_ipc/durable_receipt_and_observed_absent/retained_native_handle_observed_end plus genuine integer child_exit_code (notbool). API accepts actual history outputs: all_bound_invocations_ended with model_statusended, or protocol_one_no_invocations with model_statusnever_spawned. No fake wrapper exit code. Bare worker/cancellation receipt, live/uncertain/malformed proof, wrong adapter basis or wrong scope cannot resolve.

Under the store lock persist resolvedTrue/resolved_at(first only) and an allowlisted deepcopy exit_proof excluding variable probe timestamps. Exact same proof replay is byte/time/callback stable; changed evidence conflicts. Resolution after Stop is permitted because it changes no content/fences/cursor or cancellation history. Atomic write failure keeps the identity held. Missing/manual launch provenance cannot grant process-exit authority. Manager native proof production and calling this resolver only after necessary queue completion remain tranche3b/engine work.

Same AGY ratified the source-grounded cold edge: QueueStore.claim checks blocked_run_ids before returning an existing consumer record. A newly cancelling old dispatch must still reach its exact owner despite dispatch_eligibleFalse. Narrow exception only for statecancelling and the existing exact consumer/seat. Existing dispatched/acknowledged/uncertain tasks in blocked runs remain unavailable; different consumers and all new claims remain blocked. The genuine failure was observed before the guard changed.

Helper owns only new tests/test_participant_transport_hold.py, bounded12. Evidence dictionaries/consumer receipts are explicit algorithm inputs, not native exit proof. Capture early published-oldidentity-block/missing resolver errors plus cold-owner cancellation failure before production. Cover missing ledger, same seat unrelated job retention versus peers/new identity, restart/reload, Stop and release/cancellation receipts preserving unresolved hold, strict adapter/scope/bool/code proof, exact/changed replay and atomic resolver rollback. In3a, an active cancelling ledger still blocks after a synthetic internal audit resolution until existing cancellation completes; native internal completion is deliberately not claimed.

Actual3a evidence: initial helper3RED0.193s and root3RED0.183s each had1FAIL/2ERROR (old identity claimed another job, missing resolver, cold cancellation poll denied). Initial unchanged3 pass0.186s after the minimal source changes. Final helper12 pass0.935s; first expanded11PASS/1 fixture error used different reloaded store instances for resolver and coordinator, corrected to one shared reloaded store. Root unchanged12 plus queue/API/CLI/restart/skip75 pass5.219s, full842 total tests OK/four expected platform skips80.047s. Compile/diff clean. New exit dictionaries are algorithm inputs only; native collection/internal completion/engine calls remain3b and later work. Same AGY bounded source/execution review next.

## Verification work list

## Ratified tranche3b: native proof and ordered internal completion

NEW `SeatManager.participant_exit_proof(provenance, dispatch_id)` validates actual frozen launch/profile, identity/birth/receipt and current approved root. CLI delegates existing lifecycle proof without selected_cli flags. API shares private `_api_launch_exit_proof` with saved_result_exit_proof: all original sealed payload/nonce/fingerprint guards remain in the saved caller; retirement uses no invented outbox/HMAC payload. Retained true-worker PID/birth plus integer poll or exact cold Ticket9 absence, all model history ended and exact dispatch/protocol-one empty history are required. Warm queries never close/control retained handles or extend leases. Cold fallback retains existing inventory behavior, including temporary query-handle cleanup, without synthetic adoption or process control.

NEW `QueueStore.confirm_retired_exit(dispatch_id, cancellation_id, *, evidence)` completes only an exact retired cancelling ledger. Validate scope, genuine wrapper end, typed adapter evidence and exact persisted cancellation ID or Stop ID. Store internal runtime_reconciliation cancellation plus immutable allowlisted exit_proof; no forged worker bearer, exit code, selected_cli hold or replacement cancellation ID. Exact replay preserves the record, changed proof conflicts. Existing authenticated cancelled records stay unchanged.

NEW `CoordinatedQueue.settle_old_transport(session_id, request_id, evidence)` holds the coordinator lock, validates a copied frozen audit via pure `SessionStore._old_transport_proof`, reconciles only persisted cancellation intents and rejects unrelated ACTIVE same-seat work without cancelling it. Complete old cancelling ledger before resolving the session audit; missing record creates none. Queue success/store failure leaves audit held; exact repeat repairs without another cancellation event. Automatic engine proof/settlement calls remain unwired until the engine tranche.

Native tests: new tests/test_participant_exit_proof.py7, actual Windows supervisor self-birth/retained handles and actual model child exit9. CLI child receipt23 is explicitly a protocol fixture, not an actual CLI product child. Cold87/creation mismatch/5/31 are explicit algorithm probe seams. No birth fabricated, native handles remain bounded-cleaned. Helper owns only new tests/test_participant_transport_settlement.py12; ledger evidence dictionaries explicitly algorithm-only.

Observed failures: root native initial2 missing-method errors0.991s; helper settlement initial2 missing methods0.506s. First settlement24 run23PASS/1 genuine changed-child-code replay failure2.250s, fixed by storing/comparing full stable cancellation.exit_proof; unchanged24PASS2.080s. Root malformed-provenance subcases raised AttributeError before explicit type guard (1test/2errors0.619s). Expanded39 run had1 fixture error: creation mismatch incorrectly labelled absent rather than actual mismatch status, corrected only the fixture enum. Final native/saved/transport39PASS9.357s; full861 total tests OK/four expected skips79.601s. Python syntax/diff review required before freeze. These are component lifetimes and internal ledger checks, not final native participant replacement acceptance. Unified Tranche3 same-AGY bounded source/execution review is next.

## Remaining verification work

## Frozen tranche4a: durable replacement intent and fresh binding

Same AGY bounded-PASSb9cd507 (doc pin454b001):31 dedicated/5.507s,104 focused/13.419s, full861 total/four expected skips79.196s. The following NEW store signatures were ratified before implementation:

`SessionStore.replace_participant(session_id, *, checkpoint_id, attempt_id, request_id, target_provenance, boot_id, reason='', submitted_by='operator', now=None) -> copied session`.

Validate literal positive session ID,32hex checkpoint/attempt/request/boot/source-identity/source-launch IDs, unchanged64hex target provenance fingerprint under the existing manager hash convention, nonempty managed target profile, reason<=256 valid UTF-8 characters/noNUL and actor1..80/noNUL. target_provenance is server-derived internal input, never a public settings override. Same existing current-checkpoint and Stop/corrected/pending guards apply. Exact prior request/intent ACK precedes current checkpoint guards. Same-boot exact replay is byte/time/callback stable; explicit repeat on a new server boot may update only pending recovery_boot_id/status (plus ordinary updated_at), preserving all reserved IDs/settings. Stop prevents resumption even on exact replay.

Atomically record participant_replacement fence and old_transport, reserve new_attempt_id/new_brief_id/new_dispatch_id once, store replacement_requests and pending_replacement before any clone. Pending stores old_invocation, frozen target_provenance, deterministic context_key from run/role/request, role/affected_positions, approved_prior_results from immutable admitted FINAL event content (not mutable chat), approved_continuation_context, requested_at/recovery_boot_id and statuspreparing_contexts. Stage sets retrying/dispatch_eligibleFalse while retaining old invocation for audit; cast/bindings/completed events/design/input/rules/cast_snapshot remain unchanged. Enumerate only current and unstarted same-role positions. No queue, manager, messages or process action in the store.

`SessionStore.bind_replacement(session_id, request_id, context, provenance, *, boot_id) -> copied session` is internal only. Require exact pending request/current boot and ready/clean context with verified_boot_id equal to boot_id. The manager's replacement view supplies this witness only after native readiness; a synthetic unit proof remains explicitly nonnative. Require context key matches pending deterministic key, identity/launch match the new actual provenance, new identity differs from both retired and profile-source identities, and fresh_base_effective equals the frozen selected base. The new effective settings must equal that base (API) or base plus exactly its declared fresh CLI selector/context nonce. Valid immutable new provenance fingerprint is mandatory.

Binding updates only current/future same-role cast and identity/provenance, preserving role recovery policy and original cast_snapshot. Append sanitized participant_changes audit (old/new identity/name/adapter/provider/model/reasoning and affected positions), store bound context/provenance for exact replay, clear old active_invocation, and set active/dispatch_eligibleTrue with pending statusdispatching. It creates no brief/dispatch/provider call; reserved IDs and approved prior snapshots survive until later engine dispatch. Changed replay or unverified/mismatched context refuses atomically. Already-bound identical replay is byte stable, including after later Stop. Later engine handles cold fencing, repair and post-brief failure; not claimed here.

Helper owns only new tests/test_participant_replacement_store.py, bounded12. Capture first2 missing methods before production. Real stores/manager/registry with Popen/native-readiness seams labelled nonnative; no fabricated birth. Verify staged fence-before-effects, unchanged prior/source/design/cast, exact future positions, stable IDs/replay/cold explicit resume/Stop, strict scope/first-writer races and real Path.replace rollback. Use actual initial manager clone/ready view for bind success; manager must expose verified_boot_id (current view does not yet supply it), so preserve any genuine missing-witness failure before its refinement. No HTTP/engine/native replacement acceptance.

## Remaining acceptance work

- [x] Settle the three architecture choices and five precision amendments with same AGY source/caller critique; freeze each component signature before its observed-red tests.
- [ ] Store tests observed red before implementation: exact checkpoint/intent, current/future assignment audit, original completed bytes, atomic fence/skip cursor, global first-writer races, Stop/corrected/pending guard, persistence rollback and exact replay/reload.
- [ ] Manager preparation tests observed red: frozen chosen profile, new API/CLI identity, target source untouched, verified CLI freshness/resource lock refusal, pending/spawned journal, no duplicate Popen, real readiness versus sham shim, cold failed-preparation replay/repair and post-brief immutable owner.
- [ ] Transport/engine tests observed red: absent dispatch, live/uncertain/end proofs, same-owner cancellation poll, identity hold versus peers, old late result quarantine, current/future role mapping, coordinator replacement, skip followed by synthesis, no auto generation on cold restart and durable IO-gap repair.
- [ ] Strict HTTP/operator tests and existing review-panel controls. Preview confirms role/model changes or missing-work consequence; no arbitrary source editing or implicit choice. Desktop/mobile/keyboard QA with actual actions.
- [ ] Isolated Windows local fake API/CLI integration: real prior accepted result, dropped acknowledgement/disconnection/live-stalled as distinct cases, replacement and coordinator replacement, late old event, explicit skip + output/export missing marker, reboot/replay during pending recovery, peer preservation and bounded native cleanup. Root reviews draft fault/cleanup before each actual tranche.
- [ ] Full regression plus affected Retry/Stop/restart/API outbox/selected CLI suites, same-AGY frozen final source and execution review, post-merge checks, standing-authorized publication/closure.

Review focus: no hidden old-context reuse, no inferred exit or blanket termination, no owner/key mutation after brief binding, no loss of completed work, no missing input presented as agreement, no cold auto-respawn, no repeated downstream dispatch after reply loss. Keep new interfaces bounded to this operation rather than introducing a scheduler or generalized workflow engine.

## Limits

Managed API/CLI targets and existing approved review input. No live provider/native AI usage, native Omarchy, Desktop/global settings, arbitrary participant impersonation, automatic replacement/skip, model-equivalence claim or remote compute cancellation proof. The current source packet is pasted text; later shared document packets plug into the same frozen input boundary. Human-participant replacement and broad future-role deletion are not silently added.
