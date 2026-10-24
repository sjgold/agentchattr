# Ticket 19 channel lifecycle contract proposal

**Status: discovery/proposal only; not frozen for tests or implementation.**

Goal: discoverable rename, archive/reopen and deliberate deletion; preserve history/artifacts appropriately, block automatic routing into archived channels, protect general, and require finished/stopped work before removal. Scope authority specv1.7 RC-2/AT-11 and issue19. Blocker10 is verified closed. Base published main3845c5ef46ef7dbbc0453b5cf61dadc95a2c1491; baseline1040tests/four platform skips. Prior18 complete with independent acceptance/publication/closure.

Owner Codex implementation-owner77b543b7; existing Sonnet independent reviewer and existing bounded test helper remain the only delegated peers. No new agents, source edits, tests, process/provider/browser run yet. Latest autonomous authorization supersedes the issue's older human/model-pool gates; live AI/Omarchy/Desktop/global changes remain excluded.

## Source-grounded constraints

Existing app WebSocket channel_create/rename/delete mutate room_settings and MessageStore directly. General has local guards; there is no archive state or run/queue busy check in those branches. Settings and message-log rewrites write directly to their files. Existing delete confirmation asks only for a channel name, and switches UI before server success. Root has not executed those destructive paths against user data.

Channel names also appear in jobs, schedules, summaries, sessions, queue envelopes and MCP cursor/fallback state. Current MCP delete migrator redirects remembered channels to general; preserving that fallback during archival/deletion could silently move a stale reply into another conversation. The schedule loop publishes before mark_run and has one outer exception handler, so simply throwing on an archived channel can starve unrelated due schedules. Backup import can append channel names; it must not resurrect inactive namespace entries. No standalone saved-artifact store exists in this baseline; session source/results/jobs/summaries/uploads already carry retained material.

Message receipts and immutable brief/result identities must retain their Ticket17/18 guarantees. Existing turn-event identity excludes channel, but a rename still needs a deliberate history/reference policy. No automatic model/process Stop or termination is permitted from a channel action. Explicit existing Stop controls remain the route for busy reviews.

Open Brain search found no relevant stored thought; graph fast path has no local graph and no agentchattr registry entry. Source tracing used bounded rg/reads, no graph build/install.

## Alternatives and recommendation for critique

1. **Recommended small lifecycle store/coordinator, current name namespace.** One atomic versioned channel-state/operation record is authoritative; room_settings.channels becomes its active-navigation projection. Archive/reopen changes state without rewriting history. A coordinated mutation fence blocks target dispatch/publication while rename/delete effects complete. New operator APIs and existing WS shims delegate to the same service. Preserve existing store formats and avoid a new orchestration engine.
2. **Stable channel UUID throughout all records.** Allows safe name reuse but requires a migration/trust boundary across message receipts, jobs, schedules, session/queue references and MCP fallbacks. Prefer only if safe deleted-name reuse is required; avoid adding an identifier that only some ingress paths enforce.
3. **Only add archived flags to room_settings.** Small for navigation, insufficient alone for stale callbacks, due schedules, rename/delete write failures and namespace reuse. Rejected as the complete design.

The recommendation is a proposal, not a settled permission to reserve names permanently. C1 below must be resolved before TDD.

## Proposed lifecycle and work boundary

- General is permanently active and protected at every server mutation path, including imports/settings shims; the client is no authority.
- Active channels appear in ordinary tabs/sidebar. Archive hides normal navigation, preserves all message bytes and retained records, blocks writes/Start/automatic dispatch, and provides readable history plus an explicit Reopen action in management.
- Reopen restores active access subject to the existing configured active-channel capacity. No truncation, silent remapping to general or implicit source rewrite.
- Busy checking includes nonterminal/prepared/interrupted/unresolved reviews, queued/active/uncertain/cancelling transport, and unresolved retired-participant transport audits. A completed logical run with unfinished transport still blocks removal. Report exact blocking scope, never infer model end from status. Open jobs/schedules as saved records are retained; determine actual runtime activity from authoritative records, not a freeform board label.
- Proposed shared lock order starts at SessionEngine's existing RLock. Channel action previews, final busy rechecks, dispatch ingress/claim and lifecycle mutations must serialize through that boundary. Preserve authentic cancellation delivery and unrelated-channel work. No check-then-enqueue gap.
- Operator post/recipient preview, session Start/restart/activation, job/suggestion/workflow/schedule dispatch, agent REST/MCP fallback and raw queue claim must consult the same lifecycle policy. An archived/deleted target is refused or held explicitly; never widened to general. Raw unconfigured store algorithms remain separate test seams, not evidence of configured runtime enforcement.
- Schedules in inactive channels are skipped per record without firing/deleting/mark_run; unrelated due schedules still progress. Proposed reopening may permit one overdue firing through normal scheduling, which must be disclosed. Confirm this policy in critique.
- Renaming also requires a safe quiescent boundary as the conservative proposal, even though RC-2 explicitly requires it only for archive/delete. Move the intended current channel references and preserve historical immutable source/event/brief authority. Jobs' old receipted message bodies must not be silently re-authored. Exact cross-store migration list/IO recovery is C2 below.

## Proposed mutation/effect contract

Use read-only action preview plus explicit operator request_id/version. Delete preview names the channel and counts messages/status marks to remove; it also lists material retained (session sources/results, jobs, summaries, uploads/saved artifacts). Confirmation must describe consequences and match the exact current channel/plan; new content/work or lifecycle change requires refreshed confirmation before any destructive effect.

Rename/delete use a durable intent/fence before store mutations. Perform each existing-store effect atomically where possible; on IO failure leave the channel held with actionable recovery rather than broadcasting success or permitting dispatch into a partly migrated/deleted state. Exact same-intent retry repairs remaining work without changing the intended target or duplicating effects. Cold startup must see the fence before publication/claim loops; no blind destructive cleanup of arbitrary old reviews. Keep interrupted intent and original source metadata available for explicit recovery.

Archive/reopen must not touch message history or artifact/source content. Delete preserves all non-selected saved artifacts. Since a standalone artifact store is absent, do not invent or claim that integration: retain current sources/results/jobs/summaries/uploads, reject unsupported artifact-purge flags, and record the future integration seam honestly. No new backup format; existing messages.jsonl export remains intact. Import may add new valid channels but cannot automatically reopen archived/retired/deleted channels or remap their traffic into general.

Generic settings_update must not overwrite lifecycle-owned state. Legacy WS actions either call the guarded service or return a safe explicit error; an old cached client must not bypass delete confirmation. Final UI changes selection/navigation only after an acknowledged successful action and keeps drafts/context on refusal.

## Discoverable management UI proposal

One labelled Manage channels action accessible in both tab and sidebar layouts. List Active and Archived groups, state and blocking explanation. Archive/Reopen are explicit actions; Rename is available with current name/context; Delete opens a consequence panel with counts/retention text and typed channel confirmation, plus cancel. General's protected status is visible. Show busy/IO-recovery errors inline, preserve selection on failure, and offer readable archived history without enabling composer/session controls. Native app styling,14px body/44px new action targets/390px fit, keyboard labels/focus and reduced-motion; no decorative redesign or unrelated overflow repair.

## Decisions still open before interface freeze

- **C1 Namespace reuse/stale fallback.** Lean option reserves retired names (rename/delete) so delayed jobs, imports and MCP context cannot target a newly created conversation with the same name. This is a material UX restriction and must be explicit, not silently inferred. Alternative stable IDs requires full capture/validation at every ingress and migration. Critique the smallest safe choice for this ticket.
- **C2 Rename transaction scope and retention.** Which mutable channel references migrate (messages/current jobs/schedules/summary/session view fields/cursors) while old immutable receipt/brief/source/event data is retained? Specify exact IO-gap repair, startup behavior and final ACK; do not pretend multiple files are one atomic write.
- **C3 Queued manual work.** Strict refusal for every queued item is safe but may leave an offline manual queue difficult to clear using existing controls. Decide whether to expose existing scoped cancellation or permit an explicit separately confirmed queued-only cancellation step before archive/delete; never terminate a worker or cancel unrelated work implicitly.
- **C4 Archive read/reopen automation.** Proposed archived history is readable but read-only; schedules remain stored and blocked, and overdue active schedules may fire once after explicit Reopen. Confirm disclosure and import behavior without widening scope to scheduling-composer fixes deferred in17.
- **C5 Configured-service compatibility.** Production must fail closed if lifecycle state is unreadable. Decide migration of existing settings/channels and explicit test-fixture initialization; do not add a permissive production fallback solely to keep partial app fixtures green.

## Verification stages (not assigned yet)

After contract/precise interfaces are settled, existing helper gets ONLY one new bounded state/store test module with first2 actual RED; root owns route/routing/concurrency/IO tests. Then source implementation, focused/full regression, independent frozen source review. UI uses an actual-source VM verifier with observed RED and independent review. Live Windows/local-fake and rendered acceptance need a separate script/cleanup review and one-case authorization; no real channel deletion/user data or live providers. Test archive/reopen byte preservation/reload, general protection, busy/queued/old-transport refusal, stale confirmation, atomic write failure/replay, operator auth, all automatic ingress/claim paths, peer progress, and artifact retention honestly at the available integration boundary.

Next Sonnet critiques this proposal and resolves or returns C1-C5 before helper TDD. Root then freezes exact data/API signatures and bounded work orders. No Ticket19 implementation/testing accepted at this checkpoint.
