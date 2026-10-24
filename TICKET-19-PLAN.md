# Ticket 19 channel lifecycle interface freeze candidate

**Status: interface candidate e492b78 confirmed with P1-P5; precisions below await short diff confirmation before pure-catalog TDD. No implementation yet.**

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

The reviewer selected option 1 and reserved names, with the settlements below. No stable-ID migration or general transaction framework is planned.

## Proposed lifecycle and work boundary

- General is permanently active and protected at every server mutation path, including imports/settings shims; the client is no authority.
- Active channels appear in ordinary tabs/sidebar. Archive hides normal navigation, preserves all message bytes and retained records, blocks writes/Start/automatic dispatch, and provides readable history plus an explicit Reopen action in management.
- Reopen restores active access with no new capacity cap. Existing create has no cap; the backup import-only limit remains separate. No truncation or implicit source rewrite.
- Busy checking includes nonterminal/prepared/interrupted/unresolved reviews, queued/active/uncertain/cancelling transport, and unresolved retired-participant transport audits. A completed logical run with unfinished transport still blocks removal. Report exact blocking scope, never infer model end from status. Open jobs/schedules as saved records are retained; determine actual runtime activity from authoritative records, not a freeform board label.
- Proposed shared lock order starts at SessionEngine's existing RLock. Channel action previews, final busy rechecks, dispatch ingress/claim and lifecycle mutations must serialize through that boundary. Preserve authentic cancellation delivery and unrelated-channel work. No check-then-enqueue gap.
- Operator post/recipient preview, session Start/restart/activation, job/suggestion/workflow/schedule dispatch, agent REST/MCP fallback and raw queue claim must consult the same lifecycle policy. An archived/deleted target is refused or held explicitly; never widened to general. Raw unconfigured store algorithms remain separate test seams, not evidence of configured runtime enforcement.
- Schedules in inactive channels are skipped per record without firing/deleting/mark_run; unrelated due schedules still progress. Proposed reopening may permit one overdue firing through normal scheduling, which must be disclosed. Confirm this policy in critique.
- Renaming also requires a safe quiescent boundary as the conservative proposal, even though RC-2 explicitly requires it only for archive/delete. Move the intended current channel references and preserve historical immutable source/event/brief authority. Jobs' old receipted message bodies must not be silently re-authored. Exact cross-store migration list/IO recovery is C2 below.

## Proposed mutation/effect contract

Use read-only action preview plus explicit operator request_id/version. Delete preview names the channel and counts messages/status marks to remove; it also lists material retained (session sources/results, jobs, summaries, uploads/saved artifacts). Confirmation must describe consequences and match the exact current channel/plan; new content/work or lifecycle change requires refreshed confirmation before any destructive effect.

Rename/delete use a durable intent/fence before store mutations. Perform each existing-store effect atomically where possible; on IO failure leave the channel held with actionable recovery rather than broadcasting success or permitting dispatch into a partly migrated/deleted state. Exact same-intent retry repairs remaining work without changing the intended target or duplicating effects. Cold startup must see the fence before publication/claim loops; no blind destructive cleanup of arbitrary old reviews. Keep interrupted intent and original source metadata available for explicit recovery.

Archive/reopen must not touch message history or artifact/source content. Delete retains current sources/results/jobs/summaries/uploads and rejects artifact-purge flags. There is no standalone artifact store in this baseline. No new backup format; existing messages.jsonl export remains intact. Explicit backup import retains its existing reported remap-to-general behavior, adding reason `channel_retired` for inactive/reserved names. This operator-requested history import strips routing authority and does not dispatch. Runtime publication and remembered agent replies never redirect to general. This distinction supersedes the proposal's broader import-remap prohibition.

Generic settings_update must not overwrite lifecycle-owned state. Legacy WS actions either call the guarded service or return a safe explicit error; an old cached client must not bypass delete confirmation. Final UI changes selection/navigation only after an acknowledged successful action and keeps drafts/context on refusal.

## Discoverable management UI proposal

One labelled Manage channels action accessible in both tab and sidebar layouts. List Active, Archived and read-only Retired groups, state, retained-record counts and blocking explanation. Retired entries link existing Jobs and summary views filtered to their source channel. Archive/Reopen are explicit actions; Rename requires an active channel; Delete opens a consequence panel with counts/retention text and typed channel confirmation, plus cancel. A separate confirmed queued-only cancellation action never doubles as Archive/Delete. General's protected status is visible. Show busy/IO-recovery errors inline, preserve selection/drafts on failure, and offer readable archived history without composer/session controls. Native app styling,14px body/44px new action targets/390px fit; no unrelated overflow repair.

## Settled C1-C5 and exact interfaces for review

### Durable catalog, no channel UUIDs

New `channel_lifecycle.py` owns `ChannelStore` and the configured `ChannelService`. File `channel_lifecycle.json` has exactly these top-level fields:

```json
{"version":1,"revision":0,"channels":{"general":"active"},"retired":{},"intent":null}
```

`channels` maps current names to `active|archived|retired`; a deleted channel remains a `retired` row for discoverability. `retired` maps rename-from aliases to their owning CURRENT channel name. Channel names use the existing dispatch grammar `[a-z0-9][a-z0-9-]{0,19}`. No lowercasing/coercion in the pure API; UI may offer normalized input before submission. `general` must exist, active, never an alias or a mutation source. Bool-as-int version/revision, extra/missing keys, malformed states/names/owners/cycles, alias/current-name overlap and invalid intent fail validation. Aliases must point directly to a current row, including a retired deleted row. Outputs are detached copies.

Create refuses any current or alias name. Rename may consume an alias only when its owner is the source channel: remove that alias, retarget every other owned alias to the new current name, add old->new, move the current row. Example a->b->a succeeds; c->b and new create b fail. Delete keeps the current row and owned aliases permanently reserved. Archive retains its name without adding an alias. No automatic alias routing: explicit old names fail with an actionable retired-name error.

`revision` is a nonnegative monotonic catalog-write counter. All catalog writes use existing atomic-JSON machinery, leave disk/memory unchanged on failure, and increment revision exactly once after a successful write. Missing file is distinct from unreadable/invalid existing file: only an explicit initializer may create it. No load-error reset to empty/active.

```python
ChannelStore(path)  # loads strictly; missing is uninitialized, not implicitly active
ChannelStore.initialize(channel_names) -> dict  # only if missing; otherwise strict load/no overwrite
ChannelStore.snapshot() -> dict
ChannelStore.require_active(channel) -> None
ChannelStore.blocked_names() -> set[str]
ChannelStore.create(name, *, expected_revision) -> dict
ChannelStore.set_state(name, state, *, expected_revision) -> dict  # active<->archived only
ChannelStore.begin(op, old, new, *, request_id, expected_revision) -> dict
ChannelStore.complete_step(request_id, step) -> dict
ChannelStore.finish(request_id) -> dict
```

Pure methods validate exact string/int types, and stale revision or conflicting intent raises `ChannelConflict`. `begin` supports `rename|delete`; `new` is a name for rename and null for delete. Single intent, not an operation journal: `{request_id, op, old, new, completed_steps}`. Request ID is 32 lowercase hex. Allowed ordered step names below; unknown/out-of-order steps fail, repeated completed step is a no-op. `finish` requires all effects complete, applies the catalog change and clears the intent atomically. Repeating a completed HTTP request after a lost ACK returns conflict/refreshed catalog, never repeats destructive work; the client reloads. Same request ID while pending resumes exactly the recorded intent, never replaces parameters. No successful ACK before finish.

While intent is pending both old/new are blocked, other lifecycle mutations conflict, unrelated active channels remain usable. `blocked_names()` includes archived/retired rows, aliases and pending old/new. Unknown names also fail `require_active`, so the configured queue derives blocks for unknown ledger channels as well. `ChannelUnavailable` covers missing initialization, invalid/unreadable catalog and permanent IO; `ChannelInactive` covers missing/inactive/reserved/held targets. HTTP mapping is 503 and 409 respectively; validation 400; stale/busy/conflict 409. Error messages name channel/state or safe scope, never raw file paths/errors.

### Configured service and publication boundary

```python
ChannelService(catalog, *, engine, messages, jobs, schedules, summaries,
               queue, settings, save_settings, migrate_cursors, router,
               migrate_last_active)
ChannelService.catalog_view() -> dict
ChannelService.require_active(channel) -> None
ChannelService.publication(channel)  # context manager, holds boundary through persistence/enqueue
ChannelService.preview(op, channel, *, new_name=None) -> dict
ChannelService.apply(op, channel, *, new_name=None, request_id,
                     confirmation, preview_token) -> dict
ChannelService.retry(request_id) -> dict
```

`require_active` delegates to the single catalog policy. A bare check is insufficient for writers: `publication` takes engine RLock -> catalog RLock, checks, and holds both through final persistence/enqueue. Store locks follow: message/job/schedule/summary/session/queue locks are acquired one at a time after that boundary; no store callback while a store lock is held, no reverse acquisition. Low-level standalone store algorithms remain independently testable; configured public writers/claimers receive the service explicitly, without production fallback. Any store write guard is entered BEFORE the store lock. Typed Stop/cancellation receipts and historical result admission retain their existing authority gates and are not disabled by a channel hold; channel actions never invoke worker Stop themselves.

Wiring checklist: operator post and recipient preview; generic configured channel-message publication; session Start/corrected restart/prepared activation before effects; job create/update/message; schedule create/update/fire; `/api/trigger`; AgentTrigger trigger/identity-trigger final enqueue; authenticated agent REST and MCP chat_send (including job and remembered-channel branches); summary writes; rule/draft cards that publish into channels; coordinator enqueue/claim. Read endpoints remain available for archived history/retained records. A stale job target or omitted-channel agent send with inactive remembered context returns an error requesting an explicit active channel. Delete does not replace remembered context with general. An actually absent remembered context may still use the existing initial general default.

Configure loads room settings before initializing the catalog, then wires service/queue/trigger guards BEFORE seat reconcile, engine resume, HTTP/MCP publication or background threads. First initialization atomically seeds settings channel names as active (ensuring general); existing valid catalog wins over stale settings. Settings active navigation is rebuilt from catalog active rows on EVERY configure and after EVERY successful mutation, self-healing a crash between catalog commit and settings save. Capture settings-only names before rebuilding and expose them in Manage as `unregistered`; they remain unusable until explicit create/import registers them, never silently promoted. Existing invalid catalog holds publication/claims and exposes 503 Manage state, never reconstructs from settings. Test fixtures explicitly initialize the service/catalog; generated acceptance fixtures must seed their named channels explicitly, not mutate settings to bypass policy.

`update_settings` containing `channels` is rejected before any setting mutation with `channel_error`; other unrelated settings stay as before. Legacy WS channel actions delegate when their full confirmation data is present; old clients missing it receive an explicit refresh/Manage error. All channel-validation silent continues become error replies, not broad rewrites of unrelated WS branches.

### Preview, busy scope, mutation HTTP

Operator-only routes use Ticket17 `request.state.auth_origin == 'operator'`:

| Route | Exact request | Response |
| --- | --- | --- |
| GET /api/channels | no query fields | catalog view with active/archived/retired rows, revision, pending intent, retained counts |
| POST /api/channels/preview | `{op, channel, new_name?}` | action preview below |
| POST /api/channels/apply | `{op, channel, new_name?, request_id, confirmation, preview_token}` | `{ok:true, revision, channel, state, op}` after complete success |
| POST /api/channels/retry | `{request_id}` | same success schema after exact pending repair |

Ops: create/archive/reopen/delete/rename/cancel_queued. New name exists only for rename; create uses channel as proposed name. Reject duplicate/unknown fields, invalid UTF-8/NUL, bool IDs, extra query keys and bodies >16KiB before effects. `confirmation` must equal the exact source channel name for archive/delete/rename/cancel_queued; create/reopen use the same explicit field for a uniform client. General cannot be archived, renamed, deleted or queued-cancelled through this UI. Preview for reopen discloses `N overdue schedules will run once`; no capacity check.

Preview exact top-level shape: `{op, channel, new_name, revision, state, counts, blockers, queued_dispatch_ids, overdue_schedules, preview_token}`. `new_name` null unless rename, state null for new create. Counts have messages, todos, jobs, schedules, sessions, summaries; uploads are shared retained storage, NOT falsely attributed per-channel. Blockers are `{kind, session_id, run_id, dispatch_id, identity_id, state}` with inapplicable values null, deterministically sorted. Kinds `review|transport|retired_transport|recovery`; expose exact scope and no source content. Preview is read-only.

Busy: all nonterminal/prepared/interrupted/retrying/stalled/waiting/paused/awaiting-input reviews, unresolved recovery/retired participant transport audits even without a ledger row, and queued/dispatched/acknowledged/uncertain/cancelling transport in this channel. Stopped/completed logical rows alone do not block; unfinished transport still does. Reuse authoritative state predicates and exact transport proofs, not freeform job status or online status. Rename active-only and quiescent; archive/delete quiescent; reopening archived-only. Cancel_queued refuses any non-queued live transport or unresolved audit and never changes review state.

`preview_token` is SHA256 of canonical JSON describing the action, catalog revision and stable scoped identifiers/counters: message ids/uids plus max id, todo ids, job ids+updated_at, schedule ids+next_run+enabled state, summary UID+updated_at revision, session ids+state+logical updated_at, and transport dispatch ids+state. Exclude raw bodies, monitoring, last_event and monitor-only timestamp churn. Server recomputes under the same boundary on apply before intent/effects; changed scoped identifiers/counters or work/state =>409 stale preview. Logical session updated_at excludes writes that change only monitoring; do not let monitor ticks invalidate confirmation. It is a self-consistency token, not authorization. No token store or durable preview. Counts/ids returned are detached; stored source content is not returned by the token endpoint. Repair uses the persisted pending intent after an initially valid confirmation, not a new token, and requires the channel remain held.

### Client events and authoritative reload

After successful finish (or the atomic create/archive/reopen change), broadcast `channel_state` with `{type, revision, channels}` where channels is the same active/archived/retired/unregistered projection returned by catalog_view. Rename additionally emits `{type:"channel_renamed", old_name, new_name, revision}` and delete `{type:"channel_deleted", channel, revision}` only after completion. Refusals emit `{type:"channel_error", request_id, channel, error, code}` to the requesting socket, with request_id null if malformed/missing, safe error text and the matching HTTP status code. Pending IO is an error plus a reloadable held intent, never success. GET /api/channels is the authority after reconnect, lost ACK, conflicting revision or any ambiguous operation outcome; a broadcast/optimistic local switch cannot override it. Drafts remain until acknowledged completion and an intentional navigation change.

### Queued-only cancellation and claim

`DispatchQueue.cancel_queued_channel(channel, dispatch_ids, cancellation_id) -> list[dict]` acquires one queue transaction, validates the EXACT current queued ID set for that channel equals the confirmed list, and verifies every selected row is still queued BEFORE changing any. Mark those cancelled with the given id in one write. A single nonqueued/raced ID => conflict and no write. Do not loop over `cancel_dispatch`: its existing active->cancelling behavior violates this action. Service additionally rechecks all busy/audit scope under engine lock. Cancellation is a separate action; operator must refresh preview and invoke archive/delete afterwards.

`DispatchQueue.claim(..., blocked_channel_names=None)` adds a validated set of channel names alongside existing blocked_run_ids/identities/allowed_dispatch_ids. Skip blocked queued rows and scan later eligible rows without rewriting skipped records. Preserve existing exact-owner active/cancelling poll before the queued filter (needed for cancellation delivery); an active record should not become archived through the guarded lifecycle service. Do not turn the blocked-channel set into proof that active work ended. CoordinatedQueue derives blocks from the catalog plus unknown ledger channels while holding engine lock; unreadable catalog denies new claims. Existing receipts/settlement remain available. No worker/model/client termination.

### IO, rename repair and delete retention

All MessageStore `_rewrite_jsonl` callers gain temp-write + flush/fsync + os.replace, cleanup only own temp on failure, old file intact. Rename/delete stage memory/todo changes and commit memory only after durable corresponding writes; if a multi-file deletion fails, its intent remains held for idempotent retry. Preserve byte content/UID/text/attachments/recipient receipt dictionaries; archive/reopen does not call rewrite at all. Failure tests check old file and memory, not merely exceptions.

Rename ordered durable steps: `messages`, `jobs`, `schedules`, `summaries`, `sessions`, `cursors`, `settings`. Each store gets `rename_channel(old,new)` that changes only mutable channel location fields, writes atomically, is idempotent, and rejects a conflicting destination rather than merging unrelated records. Jobs include embedded job-message channel fields. Sessions include ALL run channel view fields, including stopped parents, with frozen input/brief/event identity untouched. Summary moves its key without rewriting author/UID/text. Cursors/fallbacks migrate through MCP's existing explicit methods. Settings save becomes atomic for this effect. After each successful effect mark its step durably; failure before step marking replays that idempotent effect safely.

In-memory router channel state and last-active maps are replayed on EVERY retry immediately before finish, not trusted as durable completed steps. Persisted MCP cursor changes belong to `cursors`; its volatile fallback maps also replay. Cold startup sees an intent and HOLDS old/new before loops; it does not automatically execute a destructive repair. Operator Retry replays remaining steps and volatile migrations then commits the catalog. Before catalog commit, room settings is not public authority. Client receives channel_renamed only after finish, with catalog projection; unrelated channels work while source/target are held.

Never rewrite queue envelopes, typed events, admitted result receipts or immutable historical review briefs. They retain the old channel as audit. Root source-read confirmed CLI recovery compares message.channel to session.channel: both mutable fields migrate; its unconsumed invocation would have blocked rename. Historical source snapshot hashes stay historical. Own alias rename-back works without turning aliases into runtime redirects.

Delete ordered steps: `messages`, `todos`, `settings`; retain jobs/schedules/summaries/sessions/uploads and aliases under the retired current row. Capture exact deleted IDs/UIDs before removal for the existing on_delete notification; emit after store locks release and final successful finish, plus `channel_deleted` to clear client caches. Idempotent repair may resend cache invalidation but cannot delete other channels. No artifact-purge field is accepted. Cross-channel reply_to may dangle safely; no cascade. Retired Manage counts/links keep saved sources/results/jobs/summary discoverable. Existing message export works before deletion; do not claim deleted messages remain exportable. Existing numeric ID reuse after reload is unchanged, Ticket17 UID-based dispatch stays intact.

Schedules are not deleted by archive/delete. Runner first skips inactive/held names without marking/deleting/firing, then handles each eligible due record in its own try/except. A firing failure is recorded on that schedule as a safe error and advances its next attempt through normal mark_run cadence, so a one-shot remains stored for retry and an unrelated due peer still progresses; only a successful one-shot is removed. No hot retry-every-tick loop. Reopen runs each overdue enabled schedule once at the next normal scheduler tick, not a historical catch-up burst. Disabled schedules remain disabled. Import checks reserved/inactive names before active list/autocreate, reports `channel_retired` remaps and uses service creation for truly new channels; authority-stripped imported history never routes.

## Bounded work orders (not assigned until this diff is confirmed)

After contract/precise interfaces are settled, existing helper gets ONLY one new bounded state/store test module with first2 actual RED; root owns route/routing/concurrency/IO tests. Then source implementation, focused/full regression, independent frozen source review. UI uses an actual-source VM verifier with observed RED and independent review. Live Windows/local-fake and rendered acceptance need a separate script/cleanup review and one-case authorization; no real channel deletion/user data or live providers. Test archive/reopen byte preservation/reload, general protection, busy/queued/old-transport refusal, stale confirmation, atomic write failure/replay, operator auth, all automatic ingress/claim paths, peer progress, and artifact retention honestly at the available integration boundary.

1. **A1 pure catalog, helper ONLY new tests/test_channel_lifecycle.py, 12 methods maximum.** First two actual missing-interface RED: explicit initialize/archive/reload and own-alias rename-back/other-owner refusal. Bounded matrix: initialize only when missing (never overwrite; invalid existing file raises ChannelUnavailable); strict bool/extra/missing/name/state/owner/cycle/alias-current-overlap/general validation; create refuses current/alias; rename consumes own alias and retargets lineage (a->b->a allowed, c->b/other-owner refused); delete retains row+aliases and forbids reopening/renaming; set_state only active<->archived/general protected; revision +1 per successful write, repeated step no-op, injected IO leaves exact disk+memory+revision; begin/step/finish order and all-step requirement, same request resumes, different request or changed parameters conflict; blocked_names includes archived/retired/aliases/pending old+new; require_active distinguishes Inactive from Unavailable; detached outputs. No app/native/process claims. Root implements ChannelStore only after two RED; Sonnet focused pure review before runtime wiring.
2. **A2 configured policy and archive/reopen/delete.** Root owns new route/policy/queue/IO/concurrency regressions, observed RED before service wiring. Include every listed ingress, all busy states and missing-ledger audit, queued-only cancellation race, exact owner poll, blocked FIFO/no-write, settings/import/auth, schedule peer failure/overdue disclosure, archived byte-preservation, retired discoverability, delete callback/retention/dangling reply, permanent IO hold, post-vs-archive lock race (exactly one wins: publication completes while active or is explicitly refused, no lost/unacknowledged silent send); queued dispatch for a just-archived channel is never claimed while an unrelated channel still claims. Explicit fixture initializer changes keep prior behavioral assertions. Freeze source + full suite for independent review before B.
3. **B rename.** Root writes bounded new tests/test_channel_rename.py, real stores and per-step failure injection with fresh reload/held startup, own alias round-trip, stopped parent corrected restart channel, unchanged immutable brief/receipt/queue bytes. Existing helper may receive a separate NEW-file work order after exact cases agreed. No generic transaction abstraction. Independent source/test review and full regression.
4. **C UI.** Separate behavior freeze and actual-source VM RED/green before wiring; both layouts, archived/Retired navigation, typed confirmation, stale refresh, offline/IO inline failure, ACK-before-selection/draft retention, 14/44/390. Independent review.
5. **D acceptance.** Separate exact-count Windows/local-fake script and cleanup review, then one-case runs + independent reproduction; real server ingress/claim suppression/queue-cancel/busy/refusal/rename-repair and rendered desktop/390. No process or provider starts in planning; no real-user channel deletion. Linux/live providers/accessibility limits explicitly retained.

Current checkpoint: docs/source-read only. Next owner Sonnet confirms the P1-P5 short diff, then Codex assigns A1 only; helper remains idle until confirmation. No Ticket19 implementation/testing accepted yet.
