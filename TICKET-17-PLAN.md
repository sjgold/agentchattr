# Ticket17: explicit recipients are authoritative

State: Tranches1-3 are implemented and independently bounded-PASS through53b63b4 (corrected full1002TOTAL/four skips89.148s). Tranche4 approved U1-U5 UI/ACK code is frozen at3f653e5; actual-source VM12 and40 focused Python tests pass. Full discovery passed1004TOTAL/four skips89.097s at3f653e5; Sonnet confirmed targeted UI fixes033ac8a with VM12 and65Python1.320s. Actual-server/browser/native acceptance and final Ticket17 publication remain outstanding. Earlier sections below preserve their dated planning/checkpoint evidence. Routine per-ticket human gates remain removed under Seth's renewed October23 evening authorization.

Base: published main61315f7a8fc173577455718d7406645673f53da6. Branch codex/ticket-17-explicit-recipients. Codex owns implementation/follow-through (claim5ac077c7); Sonnet5.5 agent3b53a0e1 is independent reviewer. Scope: issue17, specv1.7 RC-1/AT-09. Blockers8/10 and recovery9/13/14/15 are delivered. Full baseline918 total tests/four platform skips.

## Outcome and boundaries

For operator-authored text, explicit addresses select the complete recipient set and override buttons. Multiple names form that set; @all addresses eligible online registered seats. With no explicit address use selections, and with neither post shared chat without waking agents. Unknown addresses warn and never activate selected/default wider recipients. Addressing controls triggers, not message visibility.

Exclude quoted data, code and attachment bodies from address parsing. Show the current resolved recipients before Send; the server recomputes against current identities when accepting the message. Default manual work waits behind an unfinished review turn, even if its transport was released early. Agent mentions do not bypass typed turn order, Stop or retired-identity holds.

No new interruption/termination workflow, native client adapter, attachment format, scheduler, provider request, external service or general Markdown renderer. Existing Stop/Retry remains explicit. Existing quote-preserving text and shared-channel history remain visible. No source of addressing authority is taken from model-written metadata or imported archives.

## Source observations

| Source/caller | Current behavior and consequence |
| --- | --- |
| static/chat.js sendMessage2514 | Prepends every missing activeMentions entry to raw text. Existing executable audit E10 reproduces @claude with all three buttons becoming @codex @glm @claude. |
| router.py parse_mentions/get_targets | Regex sees quoted/code mentions; only recognizes known tokens, so unknown tokens cannot be distinguished from no explicit address. Human default_mention can broaden an empty result. |
| app.websocket_endpoint message ingress | Receives operator WebSocket token, but only stores display sender/text/attachments. Selected buttons are currently encoded into text rather than server-validated metadata. |
| app._handle_new_message | Shared broadcast, slash expansion, legacy Router.get_targets and name-to-family expansion. Human mentions can auto-pause a session via SessionEngine._on_message; agent guard is permissive when get_allowed_agent returnsNone in non-active states. |
| app.post_job_message + static/jobs.js sendJobMessage | Separate human routing path; reply target prefixing and its own regex can miss quoted/unknown address intent. |
| static/chat.js scheduling helpers | Union explicit tokens with active buttons; strip addresses from prompt. New scheduling choices can repeat the same audience-broadening defect. |
| agents.trigger_sync/registry.resolve_to_instances | Trigger looks up a mutable name again. Exact names win, otherwise base-family names expand. Persisted dispatch already binds immutable target_identity_id. |
| CoordinatedQueue.claim/QueueStore.claim | Serializes active physical transport, but a released current review can remain logically unconsumed. New manual work may then claim before a genuine final/question resolves it. |
| archive.import_archive | Imported records stamp importedTrue and strip execution claims, but callbacks still receive them. New routing authority must be stripped and imports must not wake recipients. |

Open Brain query for project recipient precedence found no matching thought. Existing graph registry has no project graph; no graph build or tooling installation is needed. Root executed unchanged E10 audit and confirmed the original defect; this is baseline characterization, not a new regression suite.

## Approaches considered

1. Recommended: one server lexer/resolver and a read-only preview endpoint. Send raw text plus selected names, persist the server's exact audience receipt, then enqueue to those immutable identities. Reuse durable queue with a narrow logical-turn claim guard. Thin clients share server truth.
2. Separate JS/Python parsers with client prefixing: fewer initial endpoint changes, but drift and hidden text rewriting preserve the original failure mode. Reject.
3. Preview tickets, audience locks and a new manual-message outbox: stronger snapshot/delivery protocol, but introduces state and recovery beyond RC-1. Reject unless the reviewer identifies a necessary invariant absent from option1. Preview is current information; acceptance revalidates and records the actual audience.

## Settled lexer and recipient policy

- Backtick/tilde fences (including an unclosed fence) mask addresses. Inline code spans mask addresses. A blockquote begins with first nonspace `>` and includes lazy continuation through the next blank line.
- Balanced ASCII double quotes and typographic double pairs mask addresses within one paragraph. Blank lines reset pairing. An unmatched quote is ordinary authored text. Single quotes and apostrophes have no quote semantics. Preview lists ignored tokens and their quote/code/fence reason.
- A token starts at `@` outside an email/word identifier and consumes the complete ASCII identifier `[A-Za-z0-9_][A-Za-z0-9_-]*`, case-insensitively. Period/comma end tokens; trailing hyphens are never trimmed. A longer unknown token cannot route its known prefix.
- Exact registered names win. Otherwise a base-family alias resolves only when exactly one active member exists. Multiple active members produce an ambiguous warning listing candidates and wake nobody for that token. Pending exact seats are unavailable, never a reason to fall back to the family.
- Preserve address occurrence order and deduplicate recipient identities. `@all` and compatibility alias `@both` expand eligible active online seats in canonical-name sort order. Explicit registered active but offline seats remain eligible for queued work with an offline warning. Missing identities cannot reserve future registrations.
- Unknown/ambiguous tokens still count as explicit addressing: known subsets may route, unknown-only routes nobody, buttons and routing.default never widen the audience. With no authored tokens use selected names; neither means shared chat with zero wakes.
- Attachment names, paths and bodies never enter the lexer. Unfenced, unquoted pasted prose is authored text. No document detector or general Markdown renderer.

### Frozen pure interfaces for Tranche 1

New module `recipient_routing.py`, using only standard-library code and the existing `turn_events.MAX_EVENT_BYTES` (512 KiB) constant:

```python
scan_addresses(text: str) -> dict
# Exactly:
{
    'tokens': ['claude', 'unknown'],
    'ignored': [{'token': 'codex', 'reason': 'quote'}],
}

resolve_recipients(text: str, selected_names: list[str],
                   instances: dict[str, dict], online_names: set[str]) -> dict
# Exactly:
{
    'mode': 'explicit',  # explicit | selected | none
    'tokens': ['claude', 'unknown'],
    'ignored': [{'token': 'codex', 'reason': 'quote'}],
    'recipients': [{'name': 'claude', 'identity_id': 'immutable-id', 'online': True}],
    'warnings': [{'kind': 'unknown', 'token': 'unknown', 'candidates': []}],
}
```

Tokens are lowercase without `@`, first occurrence deduplicated within each output list; ignored entries deduplicate by (token, reason). Allowed reasons: `quote`, `code`, `fence`. Warning kinds: `unknown`, `ambiguous`, `offline`, `unavailable`; every warning has exactly kind/token/candidates, candidates is a sorted list of canonical names (empty except ambiguity). One warning per kind/token. In selected mode tokens are normalized selected names, with optional one leading `@` removed; first occurrence order retained. An empty selected list yields mode none. Explicit unknown-only remains mode explicit. Selections never participate when authored tokens exist.

Inputs: text is a string, valid UTF-8, no NUL, at most MAX_EVENT_BYTES; empty text is permitted for attachment-only preview. Selected names are nonempty valid UTF-8 strings without NUL, with one optional leading `@` removed unless the literal name is itself registered. Selections are literal names, not authored tokens: punctuation/spaces are allowed, and stale names warn unavailable rather than rejecting the whole request. Invalid shapes raise ValueError. Instances is the copied `registry.get_all()` mapping, whose required per-seat fields are name/base/identity_id/state; online_names is a set of canonical names. Validate required nonempty UTF-8 string fields, no NUL, mapping-name agreement and active/pending state; snapshot names/base/online names may lie outside the authored-token grammar and still participate in selections and @all. Real registry.seed/register accepts such names. Validate case-insensitive collisions; malformed snapshots raise ValueError rather than guessing authority. Extra registry fields are ignored. Case-insensitive name collisions fail closed. Selected names are additionally bounded by aggregate UTF-8 bytes at MAX_EVENT_BYTES, preserving normalized deduplication and allowing stale selections even with an empty registry. Since each valid name is at least one byte, this also bounds element count. HTTP body bounds remain a later ingress concern. Invalid text/names (including non-string, NUL or surrogate) raise ValueError with a generic message that never echoes submitted content.

Both functions return fresh copied values and never mutate inputs, registry, message files, queue, processes, hop counters or session state. The pure resolver has no channel/session/busy dependency. Preview later enriches its output with wait information using current coordinator state. These are frozen pure interfaces approved for observed-red tests, not implemented APIs.

### Exact lexical and warning clarifications (Sonnet recheck)

1. `unknown`: an authored token matches no registered name/family/alias. `unavailable`: a pending exact seat, stale selected name, registered family without an active member, or all/both expanding to zero online seats. `ambiguous`: family has two or more active members. `offline`: individually addressed registered active seat is absent from online_names, including selected-mode addresses. Unavailable all/both warnings retain the literal token. Every failed expansion is visible.
2. Tokens retain literal `all`/`both`; expansion occurs at that token's textual position in sorted canonical-name order. Deduplicate immutable identities across the entire audience. Expanded recipients have online=True.
3. A leading @ counts at start of text or when its previous character is NOT in `[A-Za-z0-9_.+%-]`. Consume the whole ASCII identifier. If immediately followed by a non-ASCII alphanumeric character, retain the extended contiguous identifier as an unknown token (e.g. `claudeé`), never route the ASCII prefix.
4. Lines are separated only by LF, CRLF or CR. Fences open at a line start with zero to three spaces and a run of three or more backticks or tildes. Backtick opener info strings cannot contain a backtick, so same-line ```x``` is inline code, not a fence. Opening a fence resets lazy blockquote state. A closer uses the same character, length at least the opener, on its own line (surrounding whitespace allowed). Unclosed fences mask to end. Inline backtick runs close on equal-length runs in the same paragraph; unmatched runs are authored. Diagnostic priority is fence, then inline code (including code inside blockquotes), then blockquote/double quote. Masking precedes double-quote pairing; reasons respectively fence/code/quote.
5. ASCII double quotes pair sequentially, without nesting; typographic U+201C opens and U+201D closes. Mixed or unmatched pairs are authored; blank line resets. Single quote forms never mask. Test apostrophe-heavy authored text including agents' notes, @claude's draft and 'tis.
6. Ignored-only addresses mean no authored tokens, so selected or none mode applies. Selected names use the same exact-name, unique-family and unavailable rules; failed selections remain selected mode with zero recipients, never default fallback.
7. Text and aggregate selected-name bounds use UTF-8 bytes, not character count. Validation errors never echo submitted text. Outputs must be detached: mutate returned structures, resolve again, and assert snapshot plus new result are unchanged.

Diagnostic bound: exposed tokens longer than128 code points become their first127 code points plus U+2026 ellipsis (total128), including tokens/ignored/warnings output. The marker lies outside the identifier grammar: a truncated token is always unknown and must never resolve a registered prefix. Resolve that condition before exact/family lookup; raw message text stays intact. Cover a long known-name prefix and a pathological200KiB input with a generous linear-time bound. Sonnet confirmed17cdbdb clarifications by diff before this bounded diagnostic addition.

## Settled authoritative ingress and preview

Operator-only `POST /api/recipients/preview`, no-store: accept authored text and selected names, call the identical resolver, add current wait information. It never pauses, enqueues, spawns or resets hop counters. Acceptance recomputes current identities; preview is informational, not a ticket or audience lock.

WebSocket operator messages carry raw text and selected_recipients separately. Authentication determines origin, independently of display sender. The single trusted operator publication path writes internal `recipient_routing` metadata containing the immutable message UID, exact resolved audience and warnings. Generic MessageStore.add AND add_once strip the reserved key from caller metadata; archives/imports and agent MCP/API paths cannot acquire this authority. A dedicated internal publication method or private capability is required, never a caller metadata flag. Freeze that method's precise signature in its ingress tranche before tests.

The receipt says **resolved audience**, never delivered. A crash/QueueConflict after message persistence but before enqueue can leave a resolved recipient unwoken; no callback replay/manual-message outbox is added here. Per-recipient dispatch IDs use UUID5 derived from immutable message UID and immutable target identity. Assign/read UID before the first enqueue, persist it in the receipt, and test MessageStore.clear plus numeric-ID reuse cannot collide. Callback replay uses existing queue idempotency. Same-identity rename is safe; never guess a successor identity from the old name.

Use a small identity-based trigger helper. Preserve the human hop-counter/unpause reset in trusted ingress (preview stays pure). Human routing.default becomes unused. Client retains raw text and the draft on preview/connection failure, prevents double submit during the final check, and displays the accepted server audience if membership changed. Exactly-once human send/ACK recovery remains outside scope.

Imported/history messages, typed projections and quarantined/stopped scopes are display-only. All ingress spoof tests must cover add/add_once, MCP, REST bearer, operator job posts, archive import and slash re-posts. JobStore.add_message currently has no metadata parameter; any receipt persistence extension must be bounded and tested, not described as an existing metadata injection path.

## Settled Wait and logical review order

Deliberate Ticket8 behavior change: **human chat never changes protocol-1 run state**, with or without mentions. Amend/rename tests/test_session_choices.py's pause-on-human-chat regression to assert no pause. Existing explicit session actions remain authoritative; no new Pause/interrupt workflow is introduced. Persisted paused/resume behavior remains supported.

Under the coordinator lock, collect nonterminal protocol-1 sessions with no stop_id and no superseded/corrected run, whose active_invocation is non-human and unconsumed. Include active/waiting/paused/awaiting_input/stalled/retrying/interrupted/prepared states. For the claimed identity, permit only the earliest invocation dispatch by (monitoring.created_at, session ID). Malformed ordering falls back deterministically to one matching review dispatch as specified below, never manual work. No qualifying invocation means no restriction.

Raw `QueueStore.claim(..., allowed_dispatch_ids=None)` receives either None (unrestricted for this claimed identity) or a set of dispatch-ID strings (possibly empty). It applies only to NEW queued claims: preserve exact active/cancelling owner polling first, identity holds and recovery holds, then iterate ALL queued records, skipping those outside the set. Never stop at a skipped manual record. If the allowed dispatch is unpublished or belongs to blocked_run_ids, nothing is claimable. No synthetic ACK/lease/cancellation/process control.

Root executed a bounded existing-fixture characterization proving one seat can be bound to two waiting reviews. Required regression: release A early, keep B and manual work queued until A's typed final/question; then B before manual. A stalled earlier run holds later work: preview/docs say it waits for the earlier review turn on this seat until recovered or Stopped. Preserve unrelated peers, retired-identity holds, and cold-owner cancellation delivery.

Suppress ALL agent-chat mention wakes in a channel with any nonterminal protocol-1 run, including awaiting_input, paused, stalled and interrupted. Typed engine scheduling supplies review turns. Outside such a run, ordinary authenticated agent discussion keeps the shared lexer and loop guard. Old stopped/superseded scope remains suppressed; fresh independent discussion after Stop is allowed when no other nonterminal run occupies the channel.

## Settled ingress coverage and deferred scheduling

Channel operator WebSocket and job-thread operator posts use the resolver. A job reply default is a selection, overridden by any authored token. Four built-in slash expansions (/roastreview, /artchallenge, /hatmaking, /poetry) inherit the original command's resolved audience through trusted publication; no explicit/selected recipients means zero hidden broadcasts plus a visible hint. Non-routing local commands stay local. Agent Router lexer integration is a separate tested tranche.

Scheduling composer changes are **deferred** to schedule-specific work. Existing server /api/schedules already accepts explicit targets; preserve historical approvals. Known chat.js scheduling union/mention-stripping behavior remains a recorded gap, so closing17 cannot claim scheduling UX is fixed.

Root AST enumeration found 27 MessageStore.add call sites in app.py (not the review's approximate28):

| Call sites at proposal82ac19f | Classification / treatment |
| --- | --- |
| websocket message1426 | Operator routed, raw text plus selections |
| post_job_message2323 (JobStore path) | Operator routed through the same resolver |
| slash reposts991/999/1018/1041 | Trusted inherited command audience, no name/default recomputation |
| api_send1867 and SessionEngine/MCP send_chat | Authenticated agent path, no operator receipt |
| schedule runner722 | Existing approved explicit targets; scheduling composer deferred |
| decisions2134, draft request3325 | Human-attributed internal workflows with explicit workflow targets, never generic sender-based operator authority |
| configure/background577/635/657/674, session change847/856 | System/lifecycle display, no human recipient fallback |
| handler981/984/1060/1070/1079/1103/1132, WS1412/1486, create_job2286, start_session2840, draft notice3320 | System/draft/rule/job/session display; preserve intended explicit workflow effects, no forged recipient receipt |

Before ingress edits, enumerate and test external MessageStore.add/add_once callers too (session projections, MCP and archive). The table classifies authentication and workflow authority, not display-name spelling.

## Implementation and verification tranches

1. Pure lexer/resolver only. After reviewer freeze recheck, helper owns new tests/test_recipient_resolution.py, bounded16-18 cases, first two actual missing-interface failures before implementation. Cover masking/ignored diagnostics, grammar/apostrophes, selection precedence, unknown/ambiguous/offline/all/none, deterministic identity dedup, malformed inputs and no mutation. No Router changes yet.
2. Agent Router lexer and safe registry alias compatibility; deliberate protocol-1 no-implicit-pause change; coordinator whitelist with actual stores/ledger. Observe red separately for changed behavior, preserve loop reset and owner polls.
3. Operator preview/trusted publication/identity trigger, channel WS, jobs, slash and reserved-key hardening. Freeze exact private ingress signatures before helper TDD. Middleware/auth, spoof, callback replay/UID reuse and enqueue-gap tests. No scheduling composer changes.
4. Composer/job UI uses server preview/raw text, warnings/ignored addresses and wait labels. Verify draft retention, no wider fallback, desktop/mobile/keyboard, existing14px/44px tokens. No full-page redesign.
5. Isolated Windows/local-fake acceptance with actual per-seat invocation counts, quoted addresses, busy manual ordering, peers and Stop. Review bounded native cleanup before execution; retain exact handles/journal proof and unresolved failures. No live provider/native AI/Omarchy.
6. Full918 baseline plus new regressions, affected prior integrations, independent Sonnet frozen-source/reproduction PASS and substantive recheck, post-merge verification, authorized publication/closure. Continue dependency order.

Review focus: no accidental expansion, source-data routing, name-to-new-identity race, job/MCP bypass, duplicate mention successor or overlap after early release. Tranche1 implementation is isolated in recipient_routing.py,18 helper pure tests and4 reviewer-edge regressions. Remaining tranches stay planned.

### Tranche1 review corrections

- Sonnet independently ran22 focused/old Router tests0.407s onf868445, but withheld bounded approval for two real fence/blockquote bugs. Root captured4 new tests before fixes:4tests0.010s with11 failing subtests/1error (fence cases, Unicode linebreak classification, real registry odd.name snapshot). No native processes were involved.
- Corrected backtick info strings, reset quote state at fence open, restricted line boundaries, tolerated valid out-of-grammar registry names, and followed Sonnet settlement allowing literal non-grammar selections (stale selections warn unavailable). The helper deliberately moved two grammar-only negatives to positive stale-selection diagnostics, preserving malformed-shape/UTF8/NUL/empty guards.
- Root corrected suite26PASS0.349s (22 new pure tests plus4 existing Router tests), syntax/diff checks pending final freeze. Earlier full936TOTAL tests/four skips92.293s was atf868445, before these fixes; do not attribute it to the corrected source. No runtime routing integration yet.

## Tranche2 exact runtime interfaces (approved freeze, implementation below)

Sonnet bounded-passed corrected Tranche1 at e9a6402: independent26 focused0.343s plus probe reruns (no native wiring). Builder corrected full940TOTAL tests,936passed/four expected skips89.561s, shell4686f27c/log.audit-tmp/ticket17-pure-resolver-corrected-full.log. These results do not certify the following unimplemented contracts.

### Router and registry compatibility

- Keep `Router.parse_mentions(self, text: str) -> list[str]`. Replace its regex interpretation with scan_addresses(text)['tokens']; retain only known agent names, expanding all/both at occurrence position to sorted online known names (all known names if no online_checker), stable dedup. Ignored/unknown tokens create no targets. Diagnostic warnings stay in operator resolver/preview, not Router output.
- Keep `Router.get_targets(self, sender, text, channel='general') -> list[str]`. Human branch resets the existing three hop/paused/notice fields and returns only parsed mentions; remove human routing.default fallback deliberately. Agent branch preserves pause/hop/self-filter behavior. Existing continue_routing is the reset primitive the later trusted operator ingress can reuse. No new reset API.
- Keep `RuntimeRegistry.resolve_to_instances(self, name: str) -> list[str]`. Exact registered name wins as today; otherwise a known base with exactly one active member returns that member; multiple active members returns []; zero active members and unknown non-agent names keep existing [name] compatibility. At the conversion /api/trigger-agent caller, an empty ambiguous-family result returns409 with sorted active family candidate names and no triggered list or trigger call. Mention/app job/MCP job paths interpret [] as no wake and each gets a regression. Scheduled-family targets are unchanged: schedules do not call resolve_to_instances. Pending exact instances are still skipped by the caller. This changes only the unsafe multiple-family expansion.
- Keep `SessionEngine._on_message(self, msg: dict) -> None` callback signature. Replace its human-chat pause side effect with a documented inert callback: shared chat/decision content is display data, never admission, pause or progression. Current implementation already ignores legacy runs; explicit session Pause/Resume/Stop operations remain unchanged. Deliberately amend/rename the Ticket8 pause-on-chat test. No new Pause control/API.

### Shared review predicate and precise whitelist derivation

Add pure functions in queue_coordinator.py (no new module/framework):

```python
is_nonterminal_review(run: dict) -> bool
allowed_review_dispatch_ids(runs: list[dict], identity_id: str) -> set[str] | None
```

`is_nonterminal_review` requires completion_protocol ==1, no stop_id, no replaced_by_run_id, and state in active/waiting/paused/awaiting_input/stalled/retrying/interrupted/prepared. It does not require dispatch_eligible True, an active invocation, or proven native readiness.

`allowed_review_dispatch_ids` reads copied SessionStore.list_all() data, never a queue ledger or clock. For qualifying runs whose active_invocation.expected_identity_id equals the claimed identity, a human=True or consumed=True invocation imposes no restriction. An invocation whose attempt_id appears in the same run superseded_attempts is also retired and imposes no logical restriction; existing queue cancellation/physical/old-transport holds still apply. This matters during the Retry fence-to-rebind window. An otherwise eligible invocation requires human and consumed both literalFalse, a positive integer session id (bool rejected), a dispatch_id valid under the existing queue identifier format (1..128 ASCII alphanumeric/underscore/dot/hyphen), and monitoring.created_at a finite nonnegative int/float (bool rejected). Missing/malformed monitoring, created_at, session id, flags or dispatch id marks that matching candidate malformed. If any malformed candidate exists, choose only the earliest malformed candidate by valid positive session id (invalid/bool/missing ids sort at positive infinity), then dispatch-ID spelling as a stable tie-break (invalid non-string id uses empty spelling). Return its singleton dispatch if that identifier is valid; otherwise empty. Malformed candidates take priority over normally ordered candidates, so legacy/corrupt ordering never strands its own valid task or admits manual/later work by default. No matching invocation yields None. Otherwise sort candidates by (monitoring.created_at, session id) and return the singleton earliest dispatch ID. No timestamp synthesis or persistence. A consumed N before publication of N+1 leaves a brief gap with no unconsumed invocation; manual work can claim during that gap. Existing physical ACTIVE still prevents concurrent transport, but strict adjacent-turn priority through that publication gap is outside this whitelist mechanism.

Keep `CoordinatedQueue.claim(self, instance, consumer_id)`. Under its existing RLock, reconcile existing holds, read sessions once for blocked runs and this helper, then pass allowed_dispatch_ids to raw claim. Derive identity from the immutable authenticated instance identity, never name. Existing store/queue lock nesting is unchanged: list_all releases store lock before queue transaction.

Extend `QueueStore.claim(self, instance, consumer_id, *, blocked_run_ids=None, blocked_identity_ids=None, allowed_dispatch_ids=None)`. Validate None or a set of existing-format identifier strings; invalid shape raises ValueError before mutation. Existing active/cancelling exact-owner polling remains first and is unaffected by the whitelist. Preserve blocked-run cancellation exception, identity/recovery holds. For new queued claims iterate the full identity-specific FIFO, skip blocked run or unallowed dispatch, and claim the first allowed record. Empty allowset claims nothing; a publication gap or blocked allowed run cannot fall through to manual/later work. No queue rewrites on skipped claims.

### Channel predicate and agent-wake suppression placement

Add `SessionEngine.has_nonterminal_review(self, channel: str) -> bool`: under engine RLock read copied sessions for that channel and apply is_nonterminal_review. This differs from get_allowed_agent: prepared/paused/interrupted/awaiting_input also count, regardless of active invocation. Keep get_allowed_agent unchanged for other existing callers.

In app._handle_new_message, retain typed-projection and stopped/superseded-scope early display-only returns. Determine whether the current registered sender is an agent and channel has_nonterminal_review. Agent ordinary chat must broadcast without Router.get_targets, loop-hop mutation or trigger. This check must also stop built-in slash reposts from re-entering as human-looking routing input. Preserve existing agent session-draft validation/cards as display-only: compute the suppression boolean before slash branches, prevent all four broadcast slash branches when suppressed, then after draft extraction return before raw_targets. Suppressed non-draft ordinary chat broadcasts once; a suppressed agent slash remains literal shared text rather than expansion. Existing genuine typed scheduling is untouched.

Apply the same predicate before agent job mention loops in mcp_bridge.py (authenticated instance, job.channel) and the equivalent app job path, preserving existing chat_scope quarantine. This closes a job-thread bypass rather than waiting for operator-job ingress in Tranche3. Operator-origin classification and trusted receipts are still the next tranche; display sender alone will not become authority there.

### Bounded tests after reviewer freeze

Helper assignment proposed: only new tests/test_recipient_runtime_order.py, about12 cases. First actual red: released-but-unconsumed current review must deny a queued manual claim; pure allowed_review_dispatch_ids missing method. Agent guard red is root-owned separately. Use real engine/store/registry/queue fixtures with explicitly nonnative process doubles. Extend to two runs/same seat ordering, raw queued scan past skipped record, malformed/NaN/bool timing, no occupancy default, Stop/superseded/human/consumed boundaries, owner/cancelling polling/recovery holds and byte-stable no-claim. Root owns separate Router/alias/agent-suppression tests and deliberate old Ticket8 test edit, with actual red first. No helper edits to old tests or production. Freeze approval is required before assigning this workorder.

Tranche2 freeze06bdc67 approved by Sonnet with C1 deterministic malformed-own-task fallback, C2 conversion ambiguity409/caller tests, and C3 documented adjacent-turn publication gap. These corrections above precede helper tests. Runtime code remains unchanged until observed red.

### Tranche2 implemented verification checkpoint (2026-10-24 Chicago)

- Queue-only helper initial2 actualred0.058s (manual wrongly claimed after early release plus missing helper). Final12PASS0.405s after disclosed fixture-only monitoring nesting and32hex hold-ID corrections. Actual stores/ledger/engine fixtures; no workers or native lifecycle claims.
- Root added10 runtime routing tests and deliberately revised the existing Ticket8 choice expectations. Initial9+one changed old test ran10/0.235s with13 failing observations/9 missing-method errors (.audit-tmp/ticket17-runtime-routing-red.log), before those source edits. Later focused34 exposed two other old choice-test resume assumptions; replaced those resumes with explicit waiting assertions for the approved behavior change. Existing explicit pause/restart tests remain unchanged.
- Root found one additional numeric-validation edge: math.isfinite on a very large finite integer raised OverflowError; actual1test ERROR0.017s preceded the integer-safe validation fix. This preserves the frozen finite-int contract without float coercion.
- Final focused62PASS1.742s (.audit-tmp/ticket17-runtime-focused.log): runtime routing10/order12, choices, old Router, typed projections, Stop routing and turn recovery. Python syntax/diff clean. Full regression and Sonnet bounded review follow on the frozen source; no final17 acceptance yet.
- Implemented Router shared lexer/no human default, unique-family compatibility/conversion409, inert human-chat callback, channel-level agent guards including job paths/draft display, and logical claim whitelist. Operator trusted receipts/server preview/UI remain unimplemented; no scheduling-composer change.

### Tranche2 review correction checkpoint

- Frozen33333da full962TOTAL tests ended FAILED(errors5, skipped4)85.432s, never acceptance. Sonnet independently reproduced the same5 in affected20 tests and passed frozen dispatch_queue/turn_recovery/corrected_restart/session_stop/session_events integrations. Original logs remain intact.
- R1: exclude Retry-fenced/superseded active attempts from logical occupancy before replacement binding. Root regression proves manual and reserved retry tasks wait before the fence, then can claim after it (physical holds remain authoritative). R2: four saved-result tests reused an older still-unconsumed setup run; their scenario helpers now explicitly Stop that older run before starting the target scenario and assert its saved result remains unacknowledged. All existing target recovery assertions retained. Ordinary Retry transport test passes unchanged after R1.
- Added agent /continue rejection regression, restored its existing human-only notice without router reset, and removed duplicate job lookup. Root first2 new regressions actually FAILED0.072s before fixes.
- Corrected focused84PASS5.019s (.audit-tmp/ticket17-runtime-corrected-focused.log), syntax/diff checks follow; corrected frozen full run and Sonnet substantive recheck required before bounded approval. No corrected full-suite result claimed yet. Preview/UI must explain that agent mentions during a review are display-only.

## Tranche3 trusted operator ingress (approved with corrections C1-C4, before tests)

Tranche2 c1bce3a is bounded-PASS: builder full964TOTAL/960passed/four skips85.646s; reviewer70focused4.376s and corrected-source turn_recovery/corrected_restart/session_stop integrations PASS. Earlier failed962 run remains historical. No final17 acceptance.

### Persistence authority and immutable UID

Use one process-private capability object `_OPERATOR_PUBLICATION` in store.py, shared with jobs.py/app.py; identity comparison only, never a serializable token or metadata flag. No HMAC, new database, ticket or outbox. Add private methods:

```python
MessageStore._publish_operator(self, sender, text, *, routing, authority,
                              channel='general', attachments=None,
                              reply_to=None, msg_type='chat', metadata=None) -> dict
JobStore._publish_operator(self, job_id, sender, text, *, routing, authority,
                          attachments=None, msg_type='chat') -> dict | None
MessageStore._emit_operator(self, message, *, authority) -> None
JobStore._emit_operator(self, message, *, authority) -> None
JobStore.get_message_snapshot(self, job_id, message_id) -> dict | None
```

Only the trusted central ingress calls private publication with the capability. A wrong/missing capability rejects. Each method assigns a fresh server UUID UID (no caller UID argument) before persistence, adds that same UID to the routing receipt, and returns a detached copy AFTER successful persistence. No enqueue occurs in either store. The private methods persist without firing callbacks; central ingress resets human routing and then emits the normal message callbacks/JobStore message change exactly once. Private operator JSONL writes append one encoded UTF-8 line under the store lock, recording the prior byte length first; write and fsync BEFORE committing _messages/_next_id. On any write/fsync exception truncate back to the prior length, leave memory/counter unchanged, emit nothing. If the file did not previously exist, remove only the empty file created by this failed operation. No full-history rewrite per human send. Ordinary agent chat keeps its existing append path; add_once retains its existing projection-only replacement behavior. Private job publication uses existing atomic_json and rolls memory back on write failure. Preserve UID/timestamp/import behavior on generic paths. Both _emit_operator methods capability-check, reload the saved matching id/UID, and call each registered observer with a detached deepcopy (swallow observer exceptions as on existing add). MessageStore emits its on_message callbacks; JobStore emits its normal message-change event with job_id and message. Central order is strictly persist -> router.continue_routing(message channel) -> emit. Private publication itself never emits.

Generic MessageStore.add and add_once always deepcopy metadata and remove recipient_routing before persistence/callbacks. Generic update_message cannot introduce or replace that key; preserve an existing receipt while allowing additive UI metadata. Ordinary caller metadata never receives the capability. JobStore.add_message keeps its current signature (no arbitrary metadata input); its import path already ignores incoming job-message metadata. The new private method is the only job receipt writer. Explicitly strip recipient_routing in archive message import too, and test forged job import metadata is ignored. Imported/history/projection records never route.

The private receipt is exactly:

```python
{'version': 1, 'origin': 'operator',  # operator | workflow | schedule, server chosen
 'message_uid': '<fresh server UUID>',
 'mode': 'explicit', 'tokens': [], 'ignored': [], 'recipients': [], 'warnings': [],
 'waiting': [{'identity_id': '<id>', 'reason': 'earlier_review_turn'}]}
```

Mode/tokens/ignored/recipients/warnings follow the frozen pure resolver. Waiting is an informational acceptance-time snapshot, not an assertion that delivery occurred. No keys, paths, process IDs or mutable name lookup tickets. For each recipient, waiting is present when allowed_review_dispatch_ids(current copied sessions, identity_id) is not None; ordinary physical queue serialization remains in force even without this annotation. No ready/free delivery promise.

### Central publication and authenticated origin

```python
app._publish_operator_message(*, sender, text, selected_recipients,
    channel='general', attachments=None, reply_to=None, job_id=None,
    msg_type='chat', metadata=None, approved_targets=None, origin='operator') -> dict
```

This synchronous private function is the ONLY caller of the two private store publication methods. Resolve current registry/online snapshots once, preserve raw ordinary text (including Unicode/CRLF), create the accepted receipt, persist, call existing router.continue_routing(channel) AFTER persistence, then emit callbacks. Preview never resets hops. Store IO failure emits no callback/enqueue or hop reset. Channel callbacks route asynchronously through _handle_new_message; operator job endpoint explicitly awaits the same audience dispatcher after the job is saved. No automatic replay after a crash between persistence and enqueue.

For authenticated human posts approved_targets is always None and origin is operator, regardless of display sender. The security middleware sets request.state.auth_origin='operator' ONLY after validating browser session header/query token. The allowed bearer branch returns without the operator marker; /api/send remains outside this new preview/publication marker flow. Preview and REST operator-job publication require the operator marker; agent bearers get403. WebSocket validates its session token before handling events and calls this ingress directly as operator. Client metadata/origin/capability/UID/routing/run fields are rejected or ignored, never authority. /api/send remains bearer-agent-only and cannot choose operator selections. An agent using a human-looking display label still follows its authenticated seat identity.

approved_targets is a private internal-workflow exception, forbidden in all client schemas: resolve_recipients('', approved_targets, snapshot, online), so instruction/source mentions cannot change an already-approved workflow audience. Migrate the existing schedule runner (origin schedule), decision-choice replies and request_session_draft (origin workflow) through this same ingress with their explicit server-selected targets. Preserve approved schedule targets and existing literal stored prompt/display conventions; scheduling composer union/stripping remains deferred. No new schedule mode or historic schedule rewrite. Other system/draft/rule/job-created/lifecycle adds stay display-only.

Unknown generic messages with no trusted receipt or authenticated seat_identity_id are display-only; they cannot gain human routing by spelling a human sender. Authenticated ordinary agent paths keep the shared Router lexer, loop guard and nonterminal-channel suppression. In _handle_new_message the durable trusted-receipt branch runs immediately after typed-projection/import suppression, BEFORE registry.get_instance(sender) or chat_scope. A real human whose display name matches an agent stays operator-origin; the same display name through /api/send bearer stays agent-origin. Test both. Preserve all stopped/superseded quarantine checks for actual agent chat.

### Frozen audience dispatch and identity helper

```python
app._dispatch_operator_audience(message: dict, *, job_id=None) -> None  # async
AgentTrigger.trigger_identity_sync(self, identity_id, *, dispatch_id,
    message='', channel='general', job_id=None, prompt='') -> dict
```

Dispatcher reloads the durable message snapshot by numeric id AND matching UID (MessageStore.get_snapshot or new JobStore.get_message_snapshot); only that saved receipt/text can authorize routing, never callback-supplied replacement metadata/text. Check receipt version/message_uid/origin; no recursive Router resolution. For each saved target identity, look up its CURRENT canonical instance by immutable identity, enqueue directly to that identity with the acceptance text/context. A rename keeps the identity and works; a removed identity warns/does not reserve work for a later same-named registration. Add a small common enqueue-instance helper in AgentTrigger if needed to reuse envelope construction; no native invocation or model generation here.

Dispatch ID is exactly uuid.uuid5(uuid.NAMESPACE_URL, 'agentchattr:recipient:' + message_uid + ':' + identity_id).hex. Assign/persist UID before the first enqueue; numeric IDs never participate. Same callback repeat is idempotent in the existing queue, and clear/id reuse yields distinct IDs. Catch per-target QueueConflict/unavailable identity and continue other resolved recipients; the receipt still means resolved audience, never delivered. No content regeneration, callback recovery ledger or blind retry. After message persistence a permanent enqueue failure can leave an unwoken recipient, explicitly disclosed.

Move built-in human slash expansion into central trusted publication: resolve the ORIGINAL command audience, expand /roastreview,/artchallenge,/hatmaking,/poetry once, then persist the expanded text with the unchanged resolved audience. No hidden all target, no raw-command recursion. Recognize a command only at authored start after optional plain leading address tokens; quoted/code command text stays literal. No recipients means posted with no agent wake and a UI-derived no-recipient hint. Ordinary message text is never rewritten.

### Operator preview and transport schemas

`POST /api/recipients/preview` is operator-only, no-store. Exact required JSON keys: text, selected_recipients, channel; optional job_id. job_id is a positive strict integer; if present its stored channel is authoritative and must match supplied channel. Text and aggregate selections retain MAX_EVENT_BYTES validation; entire JSON body <=2*MAX_EVENT_BYTES (1MiB), duplicate keys rejected at all nesting levels, generic400 errors without echoing source. Unknown/ambiguous recipients produce200 with warnings, not400. Invalid auth403, missing job404, unavailable registry/store503 with no private exception path. Response has exactly the five pure result fields plus waiting as above, without version/origin/UID. Pure resolution and wait annotation are reused at acceptance, but current identities are recomputed. No preview ticket/secret/fingerprint.

WebSocket message event: existing type/text/sender/channel/attachments/reply_to plus selected_recipients (default [] for old clients); no metadata/UID/authority. Bound the raw UTF8 event at1MiB, parse unique JSON keys, validate names/text/channel/attachment-list/strict nonnegative reply id (zero valid), then publish. Retain ordinary raw text. Client-facing error leaves its draft intact once the UI tranche handles it. Existing local /clear and human /continue remain explicit local controls and ignore selections. Selection defaults in the old client are already encoded into text until the UI tranche, not claimed fixed yet.

REST operator job POST preserves its existing path; accepted body text, selected_recipients(default[]), sender(display), attachments, type(chat|suggestion). Server job.channel supplies routing; arbitrary metadata/UID/origin/approved_targets/run IDs reject. Body/JSON bounds match preview. A job reply target is a client selection rather than prefixed text. Only session-authenticated operator origin uses trusted publication; agent API/MCP job posts retain their separate identity-derived paths and cannot call it.

### Tranche3 tests after freeze

First bounded helper workorder will own new tests/test_operator_publication.py only (~12 cases): actual missing private methods/metadata strip red before production, durable UID and exact receipt callback ordering, detached snapshots, unauthorized capability, add/add_once/update spoof, JSONL/job write failure no callback/enqueue/no memory leak, archive imports and immutable receipt updates. Root owns ingress/middleware/WebSocket/identity-dispatch tests in separate files. Split publication foundation from runtime ingress if needed, with precise scope and no duplicate assignments. No UI or native acceptance until these interfaces are implemented and independently reviewed.

### Tranche3 correction and migration boundaries

Sonnet source-read approved bb6f814 with C1-C4 now incorporated before helper tests. C1 append-before-memory with truncate-on-failure avoids O(history) work under the global message lock; C2 private emit signatures and persist/reset/emit ordering are explicit; C3 trusted receipt classification precedes all sender-name agent scope lookups.

C4 exclusions are deliberate: agent-origin slash expansion remains the generic authenticated-agent path (including the existing MCP raw-command store/delete behavior), never operator publication; preserve its identity-derived scope on any generic repost. WS /clear and human /continue remain local; existing WS /continue's default-general reset is outside17, while ALL new central resets pass the message channel explicitly. WS decision_propose/rule_* events never route. Client msg_type is never accepted: channel WS publishes chat only, REST jobs use chat or validated suggestion; session_request is reserved for internal request_session_draft with approved_targets. Add source-level checks that mcp_bridge.py and agent REST function bodies never reference the private capability, plus real middleware/body-spoof tests.

Helper publication tests must assert exact prior file bytes, _messages, _next_id, callback count and reset spy all unchanged on forced append/fsync failure; test callback deepcopies/throwing observer isolation and explicit persist/reset/emit order. No production tests may claim central-ingress ordering until that function exists and is exercised in root's later tests.

Sonnet confirmed C1-C4 by diff at1b4fb46. Helper is assigned ONLY new tests/test_operator_publication.py12 for private store foundations, actual initial red before production. App ingress/preview/identity dispatch remain a later subtranche; no T3 code implemented yet.

### Tranche3a publication foundations implemented

- Scope is store.py/jobs.py/archive.py and new tests/test_operator_publication.py12 only; app ingress/preview/identity-trigger wiring is still planned. Private publisher methods create a fresh UID/receipt before persistence and emit no callbacks; explicit emit reloads saved ID/UID with detached observers. Generic add/add_once/update/import protect the reserved receipt namespace.
- Helper initial2 actualred0.010s (forged key retained and missing private method) preceded production. Root unchanged expanded12PASS0.076s, including actual partial append and fsync faults/absent-file rollback, job atomic writer fault, real ZIP import and stable snapshots. No fixture corrections/assertion changes were needed. Explicit persist/reset/emit test is a unit sequence, not a claim about unimplemented app ingress.
- Affected56 tests PASS3.957s (.audit-tmp/ticket17-publication-focused.log), Python compile and diff clean. Frozen full regression and Sonnet bounded source review are next; no foundation acceptance/full-result claim yet.

### Tranche3a accepted and Tranche3b backend implemented

- Foundation6ca9289 full976TOTAL/972passed/four skips98.270s exit0; Sonnet independent72focused1.151s and own storage probes -> boundedPASS. Tranche3b source changes follow that acceptance and need their own recheck.
- Implemented approved central publication, authenticated middleware marker, strict operator preview/REST job/WebSocket message schemas, stored-ID/UID audience reload, immutable-identity trigger and UUID5 dispatches, slash audience capture, private approved workflow/schedule targeting and channel-specific hop reset after persistence. Private job messages now store their acceptance channel so later job moves cannot change an already-resolved callback context. Hidden session_request is transient: after dispatch attempt it is removed from chat storage; its prompt stays in the durable target envelope. Browser filtering also protects transient display.
- Applied reviewer n1 with actual red: generic updates preserve trusted message identity/content fields while accepting additive UI metadata. No supported ordinary edit flow was removed (current proposal-demotion callers do not target private published chat/session_request types).
- Generic unauthenticated human-looking messages are display-only, including MCP job posts without an authenticated instance; bearer paths retain agent identity and cannot access the capability. Agent slash reposts preserve their identity-derived scope. Old ordinary-agent tests now call actual engine.send_chat instead of fabricating a display sender; choice fixtures provide the registry/router/session context required by trusted internal reply publication. A direct job test deliberately changed from sender-label classification to operator-marker classification; real middleware coverage is separate.
- Helper initial2 actualred0.037s before methods; expanded root12 had11PASS/1absent-file fixture ERROR0.286s, corrected only optional-bytes/absence assertions. Root first3 preview/auth/immutability tests had2missing-endpoint ERROR/1mutationFAIL0.042s before source changes. Root later3 error-path tests had2FAIL/1PASS0.094s: unavailable storage must be503, and enqueue IO AFTER durable job publication must preserve content ACK200. Those are fixed; the receipt never promises delivery or auto-replay.
- First expanded21(helper12+root9)PASS0.538s. One affected invocation also named a nonexistent test_session_drafts module; corrected module selection, not product code. Four older assertions required genuine auth/context fixture updates as described above. Final affected126PASS3.000s (.audit-tmp/ticket17-ingress-affected.log), Python syntax/diff clean. New helper12 private units make no HTTP claims; root12 routes use real in-process FastAPI middleware/WebSocket fixtures, not native worker/provider/browser acceptance.
- Full frozen discovery and Sonnet bounded source/reproduction review next. UI still prepends selections and has no recipient preview until Tranche4; no claim of complete RC-1 behavior or final17 acceptance. Scheduling composer union/mention stripping remains explicitly deferred.

### Tranche3b review corrections F1 and fixture completion

- Frozen5ed4403 full1000TOTAL ended FAILED(one error, four skips)89.858s. Sole failure was the capacity fixture's missing router/registered coordinator; Sonnet independently reproduced it in103focused and alone. Reviewer native integrations at5ed4403 allPASS: session_events, dispatch_queue, turn_recovery, corrected_restart, session_stop, review_brief, team_capacity, api_seat, cli_seat, package. Those results precede this correction.
- F1 real visibility regression: the newly persisted hidden coordinator request leaked through readers/export. Restored removal from MessageStore after dispatch attempt, with saved id/UID guard; request-draft endpoint awaits that attempt before returning. The actual target queue envelope retains its full prompt. Private receipts still persist before enqueue; this internal hidden-workflow exception intentionally has no callback/outbox replay after removal, matching prior hidden behavior.
- Capacity fixture now supplies Router and a genuinely registered coordinator. Original policy/execution assertions remain; prompt-limit equality is checked against the actual queued prompt rather than a hidden stored message. Added explicit hidden-message absence assertion.
- Root F1 standalone actualFAIL0.046s before fix. An initial combined F1/unexpected-WS-error attempt had a missing error frame and was interrupted through its owned exec session (no native workers/providers); that partial log is not a completed suite result. Replaced only that fault test's transport fixture with a bounded scripted WebSocket handler, observed genuine missing-error-frame FAIL0.043s, then added generic per-message error handling. Fault details never reach the client; the next message remains usable. Other route tests use actual TestClient middleware/WebSocket flows.
- Corrected67focusedPASS1.376s (.audit-tmp/ticket17-ingress-corrected-focused.log). Syntax/diff and corrected full regression plus Sonnet substantive recheck are required before bounded backendPASS. Offline feedback remains in accepted warnings/preview for Tranche4 UI; no delivery promise or live-provider acceptance.

## Tranche4 composer/job UI (proposed behavior freeze, before tests/code)

Backend53b63b4 is bounded-PASS: builder full1002TOTAL/998passed/four expected skips89.148s; Sonnet105focused2.184s and corrected-source session_events/review_brief/dispatch_queue integrations PASS. Root hidden-workflow test already asserts exactly one coordinator dispatch. None of this fixes E10 until this UI tranche removes prefixing.

### Incumbent surface and direction

Scoped Operate extension, preserving static/style.css dark tokens, existing layout/type/buttons and channel/job navigation. New inline preview sits between target controls and the input in each composer; no modal, new design world, image assets or page redesign. Existing14px/44px recovery controls are the reference. Impeccable context ran via the already-installed local binary; it found no PRODUCT.md/DESIGN.md, so existing implementation is visual authority for this scoped change. No install or generated product narrative. Mechanical detector runs once after UI completion, then bounded desktop/mobile inspection plus at most one confirmation round.

Direction contract: THESIS, make the audience visible beside the act of sending. OWN-WORLD, incumbent dark surfaces/text/semantic warning colors, flat12px-inset status regions and wrapping @names. STORY, see who is addressed, understand overrides/waits, post shared text without accidental extra responses. FIRST VIEWPORT, selected controls above a compact preview, textarea and Send remain the primary action; extra ignored-address detail is collapsible. FORM, ordinary inline status section, no replacement-world seed needed. FINISH, unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance. For this incumbent extension, design documentation is this source-grounded component contract; no new raster or full-app DESIGN.md rewrite is needed.

### Shared server-only audience preview

Add static/recipients.js and static/recipients.css, loaded before jobs.js/chat.js. No JS address parser. Proposed shared API:

```javascript
const preview = RecipientPreview.attach(element);
preview.schedule(requestOrNull); // debounce250ms; dedup unchanged input
await preview.prepare(request);  // always a fresh immediate server preview before send
preview.invalidate();            // cancel stale request/context and clear old audience
preview.error(message);          // local generic status, never inject raw HTML
```

Request is exactly {text,selected_recipients,channel,job_id?}. Use the approved POST /api/recipients/preview and X-Session-Token. Abort superseded fetches; an incrementing generation discards late responses. Network/HTTP/invalid JSON error shows a generic error and leaves the draft intact. Bound preview fetch at8s. No background network poll: debounce on input/composition-end/target change, refresh on relevant membership/availability changes and channel/job switches. Existing voice-typing fallback calls updateSendButton; route that through a deduplicated preview schedule. Null request for a genuinely empty composer clears the preview to a static hint. Attachments affect whether the composer has content, never parser input.

One fresh prepare is required on Send even if the last preview matches. Snapshot text/selections/channel or job/attachments/reply before awaiting. If any draft/context field changes before prepare returns, cancel the send and schedule the new preview, rather than posting a stale snapshot. No automatic send/retry. While preparing, disable Send, label it Checking audience, and expose busy state. Multiple clicks/Enter cannot create multiple posts.

### Channel send and minimal content ACK refinement

Remove sendMessage's activeMentions prefix union. Send the original input.value (no trimming/rewrite) and separate selected_recipients array; attachments and reply id keep their current shape. Local /clear and /continue keep existing explicit local behavior and bypass audience preview; all other text/commands use the server resolver. Remove client needsMention regex rewriting for /summary: buttons are valid selections under RC-1. Update four broadcast-command descriptions from all agents to addressed agents. No scheduling composer code changes.

Proposed small backend transport refinement: after successful `_publish_operator_message`, the WS handler sends ONLY that socket `{'type':'message_accepted','uid':message['uid'],'channel':message['channel']}`. It confirms saved content/resolved audience, NEVER enqueue/delivery. This is not a client ticket, new outbox, idempotency key or automatic retry; no new request fields. Server message_error remains the rejection/unconfirmed path. Add focused backend tests for ACK-after-persistence/no ACK on failure and retain all receipt-first tests.

Keep at most ONE channel post awaiting ACK per WebSocket. Leave the draft visible until message_accepted, disable Send while waiting, and clear only if the current channel and full draft snapshot still match the submitted snapshot. If the operator edited or switched context, preserve the current draft. Bind handlers/pending state to the specific WS instance so a retired socket cannot clear a newer send. On error/close retain text/attachments/reply and show Draft kept; never resend. ACK timeout10s marks unconfirmed and closes that specific socket before allowing another post, so an old ACK cannot be mistaken for a new send on the same socket. Reconnect only reloads history, never resubmits. On token-restart4003, keep a nonempty draft visible with Copy your draft before refreshing; preserve existing automatic reload when no draft exists. No cross-reload draft persistence or exactly-once recovery is claimed.

### Job send and recipient controls

Remove sendJobMessage's regex extraction and recipient prefixing. Its current reply target becomes selected_recipients=[target] (or []); explicit raw text overrides it at the server. Preserve existing inferred reply-default/cycle/clear interactions, but do not reinterpret authored addresses in JS or silently select the first parsed name after send. Server preview/accepted receipt owns the current message audience.

Snapshot activeJobId, stored job channel, raw input.value and attachments before the final prepare. Disable job Send during prepare/POST; POST the raw text/selection to the existing operator job endpoint, wait for its content ACK200, then clear only the unchanged draft in the same job. HTTP/network/timeout errors preserve everything, show a visible error, and do not retry. A job change or edited text while awaiting never loses the new draft. The channel composer has its own pending state; the two UIs cannot clear one another.

Existing target buttons remain selected when explicit mentions override them; the preview explains the override for this message. aria-pressed must reflect channel button state. Job reply target is a selection, not private visibility; label/copy makes shared-thread visibility clear. Existing per-channel selection persistence and job reply-cycle behavior remain. No newly inferred default audience.

### Copy, rendering and accessibility

Preview heading: Addressed agents. Show canonical @names and one source label (Explicit addresses / Selected recipients / Shared note). No recipients: No agents addressed. This stays in the shared conversation. Explicit mode with selected buttons: Explicit @mentions replace the selected buttons for this message. Unknown/ambiguous/unavailable/offline warnings use server data; no wider fallback. Ambiguity lists candidate names. Offline: Work will queue for this identity. Waiting: Waits for the earlier review turn on this seat; recover or Stop that turn. Include Agent mentions during a review are display-only in the wait help. Accepted receipts say Resolved audience, not delivered/notified.

Ignored-address details list every token and reason (quoted text / inline code / fenced code), collapsed when long; no hidden swallowed address. Render names/warnings via textContent/DOM, never server strings into innerHTML. aria-live polite and atomic, no focus stealing or modal traps. Preview updates announce only meaningful changes. Error messages are generic and never echo transport paths/HTML exceptions.

All new content-bearing text >=14px, inset>=12px inside the preview, interactive targets>=44px, visible keyboard focus, natural wrapping/min-width0 at390px. Details use native keyboard semantics. Preserve Enter to Send/Shift+Enter newline and existing autocomplete shortcuts, but composing IME Enter must not send. Inputs remain editable while checking/waiting; successful Send refocuses only the unchanged current composer, never a different context. Do not fix inherited page/header overflow or unrelated design-hook findings without scope evidence.

### Tranche4 verification before acceptance

Freeze this behavior with Sonnet before frontend tests/code. Root owns UI implementation; helper may own one new Node VM regression script after the exact shared module API freezes, observed-red first. Cover raw text versus selections, unknown/quote/all responses, stale preview cancellation, final prepare/draft mutation, disconnect/ACK/error retention, duplicate Send, job context changes, safe rendering and IME Enter. Server tests cover the minimal ACK refinement separately. Node syntax plus existing composer audit must exercise actual sendMessage/sendJobMessage, not reimplement them.

Actual Windows/local-fake server acceptance still follows: native invocation counts for explicit subset/none/quotes/busy ordering plus actual /ws, preview and job routes; bounded tracked cleanup reviewed before execution. Root browser QA batches desktop/mobile/keyboard/error states on the actual server; no live AI/Omarchy/Desktop/global changes. Independent final review covers the whole ticket after UI/native evidence, then post-merge checks and publication. No UI or ACK refinement has been implemented at this freeze.

### Tranche4 clarifications U1-U5 (before tests/code)

Sonnet approved17fc398 with these precise additions. U1: correlate ACK only to the single pending post on that SAME socket instance; UID is unknown until the response. Timeout copy is: This message may have been saved. Check the conversation before sending again. Draft kept. Never resend or clear from a retired socket ACK. U2: normal broadcast and ACK can arrive in either order; only the ACK plus unchanged snapshot clears the draft. Node tests cover both orders.

U3: preview failure is fail-closed. Posting stays blocked until a preview succeeds; a visible Check again button (>=44px) retries the preview only. No send-anyway. A fresh final prepare still precedes every post. U4: local /clear and /continue use the server's first-whitespace-token/lowercase rule, including /clear x and /continue x; they bypass preview/ACK. Unselected /roastreview previews No agents addressed and still posts shared text. U5: single-flight covers button, Enter and voice/updateSendButton paths; composing IME Enter never sends. No second prepare while a send is already in flight.

Preview live announcements change only for meaningful audience/warning/ignored/waiting changes, not raw-text keystrokes with the same result. New preview script must precede jobs.js/chat.js (order regression). Scheduling composer tests/helpers remain unchanged and deferred.

Testing anchors: channel recipient state/send/event helpers will live between `// --- Recipient composer ---` and `// --- Image paste/drop ---`; job send helpers between `// --- Recipient job composer ---` and `async function uploadJobImage`. These are extraction seams for the actual source functions in a bounded Node VM test, not an alternate implementation. Backend ACK tests precede the small server change, then Node observed-red precedes UI files/wiring. No frontend or ACK code has changed yet.


### Tranche4 implementation evidence (bounded, before source review)

Shared preview and composer code now implement the approved interfaces and U1-U5. Backend saved-content ACK routes16PASS0.457s, actual-source VM12PASS and root combined publication/ingress/routes40PASS0.771s. Initial backend missing-ACK and helper missing-module/E10-prefix reds are retained separately from VM fixture adaptations. Exact native key handlers are invoked for IME, not source-regex proof. Existing historical baseline audit stays unchanged; the new tools/verify_recipient_ui.cjs executes the current extracted functions.

Preview refreshes on meaningful availability/membership and session events, with no network poll; final prepare always rechecks. Displayed stored receipts say Resolved audience. Engine lock still covers trusted append/fsync as accepted in backend review. New receipt/preview uses safe DOM text. UI source review, full regression, actual-server acceptance and browser measurements remain outstanding at this checkpoint.


### Tranche4 S1/S2 review corrections

Sonnet independently ran actual-source VM12 and65Python tests1.349s with source/syntax/diff review at3f653e5; builder frozen full1004TOTAL/four skips89.097s. Before acceptance, S1 now distinguishes definite server rejection from uncertain saves, preserving safe server message_error text; job4xx/503 says Not saved while500/network/timeout remains uncertain. S2 adds optional schedule(request,force=false) so availability/session refresh retains the visible audience during a debounced fresh request. It never replays a post. A positioned preview ancestor contains the clipped live region. Helper red9PASS/3FAIL preceded these changes inside the existing12 cases; unchanged12PASS and root65Python1.329s after. Await Sonnet targeted recheck; browser/native/live-server acceptance remains outstanding.


### Tranche5 acceptance draft scope (not execution authorization)

UI033ac8a is independently bounded-PASS. Existing helper first proposes exact case/count/cleanup design, then drafts new verify_explicit_recipients.py and optional dedicated fake client. No actual acceptance execution before root and Sonnet review full draft, native handle accounting and cleanup. Real run.main server uses private data/dynamic ports and session authentication, with actual WS preview/job ingress and UID content ACK. Required cases: subset while all selected, selections-only, neither/ignored/unknown zero dispatches, all online only, ambiguous/unique family, manual wait behind released-unconsumed typed review, agent display-only mention during review, bearer403 and Stop. Same-family registry/MCP fixtures must not be passed off as native managed seats with unique bases.

All API response-body gates release only after verified native worker/model handles are retained; CLI early release/late typed final must come from the actual fake client's authenticated MCP, not parent-forged machine ingress. Exact per-case provider/injection/admission/dispatch counts are frozen before runs. Cleanup inventories every private launch/config/manifest/model/client record, retains true server separately from launcher, never scans/guesses PID/tree or forces native client/model. Exact cooperative stop then native waits; any worker fallback requires fresh complete child-end evidence immediately before action. Unknown metadata remains unresolved/preserved and later resources still receive cleanup; unresolved fails. Root browser serve is separately authorized/bounded after normal-case evidence. No live AI, Omarchy or Desktop/global settings changes.
