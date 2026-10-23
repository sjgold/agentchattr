# Ticket15: replace or skip a missing participant

State: same-AGY contract and all five precision amendments RATIFIED. Tranche1 skip storage independently bounded-PASS8834a8d. Tranche2 initial clone/replay interface below frozen before observed-red tests; explicit failed-preparation repair receives its own later contract. No replacement manager, transport, HTTP, projection/export or UI behavior is implemented yet. Standing autonomous policy replaces routine human gates; material scope changes and live usage still require Seth.

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

## Proposed verification tranches

## Frozen tranche2: initial managed replacement clone and replay

NEW `SeatManager.prepare_replacement_context(source_provenance, context_key, *, binding) -> context view`. binding is exactly {child_run_id, role}, using current run UUID and nonempty role. context_key is a bounded1..128 plain identifier. No retry_attempt/confirmation in this tranche: failed/live/uncertain preparation replay never replaces a worker. Explicit repair receives a later observed-red contract.

New preparation validates server-derived provenance fingerprint against the current owned source and real immutable config/launch records, current approved root/data/web/MCP and current registry identity. Require source native current-boot readiness. Source queries must never use cleanup/termination paths or extend its lease. Component tests may mock only that readiness boundary and label it nonnative; no invented birth metadata.

Use a stable replacement key independent of selected seat ID so a repeated context_key cannot silently switch sources. Persist source reference {key, launch_attempt, identity_id, fingerprint} as replacement_source with existing context_id/context_key/context_source_fingerprint/context_base_effective/child_run_id/role fields. Validate exact source/binding/metadata on warm/cold replay, returning the same attempt or failed/blocked view. Corrupt/pending/ambiguous disk evidence never permits blind Popen. Reuse recover_prepared_context for disk lineage without repair; adoption retains replacement_source metadata without broadening process authority.

Clone frozen base effective settings rather than edited saved/provider/template values. API gets a distinct worker. CLI requires verified fresh context args/new nonce and existing config_resource guard. Env/flag-generated MCP configuration remains attempt-scoped; active fixed settings-file ownership blocks before spawn instead of overwriting it or stopping its owner. Use existing _launch_effective pending/spawned journaling and hidden console behavior.

Source process/handle/files/registry/context and unrelated jobs remain intact. Clone is starting/unverified until its OWN genuine current-boot native proof plus ready receipt; receipt alone cannot report clean_contextTrue. Context view exposes only existing safe fields. No review brief, dispatch or model call in this component. Engine intent-before-clone ordering belongs to the later engine tests.

Helper owns only tests/test_prepare_replacement_context.py, bounded10-12 real manager/store/registry cases with explicit Popen/readiness doubles. Capture initial API clone/source-preservation plus invalid binding/key red before implementation. Cover drift, fresh CLI/resource refusal, exact replay/conflicting source, separate source/clone readiness, ownership/journal IO, strict source/root guards and cold failed/pending replay without respawn. No native lifecycle/engine/provider/UI acceptance claim.

Tranche1 independent review: same AGY bounded-PASS8834a8d, dedicated12/0.805s, focused80/4.018s, full818 total/four expected skips73.115s. Later wiring explicitly excluded.

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
