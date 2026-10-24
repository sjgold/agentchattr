# Ticket17: explicit recipients are authoritative

State: pure interface shapes approved by Sonnet at082307c; seven exact test-encoding clarifications incorporated below before helper TDD. Tranche1 pure module,18 helper tests and4 reviewer-edge regressions are implemented; no live routing, queue or UI changes yet. Routine per-ticket human gates remain removed under Seth's renewed October23 evening authorization.

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

Under the coordinator lock, collect nonterminal protocol-1 sessions with no stop_id and no superseded/corrected run, whose active_invocation is non-human and unconsumed. Include active/waiting/paused/awaiting_input/stalled/retrying/interrupted/prepared states. For the claimed identity, permit only the earliest invocation dispatch by (monitoring.created_at, session ID). Missing/malformed ordering evidence fails closed for new claims on that identity. No qualifying invocation means no restriction.

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

## Tranche2 exact runtime interfaces (proposed freeze, before tests)

Sonnet bounded-passed corrected Tranche1 at e9a6402: independent26 focused0.343s plus probe reruns (no native wiring). Builder corrected full940TOTAL tests,936passed/four expected skips89.561s, shell4686f27c/log.audit-tmp/ticket17-pure-resolver-corrected-full.log. These results do not certify the following unimplemented contracts.

### Router and registry compatibility

- Keep `Router.parse_mentions(self, text: str) -> list[str]`. Replace its regex interpretation with scan_addresses(text)['tokens']; retain only known agent names, expanding all/both at occurrence position to sorted online known names (all known names if no online_checker), stable dedup. Ignored/unknown tokens create no targets. Diagnostic warnings stay in operator resolver/preview, not Router output.
- Keep `Router.get_targets(self, sender, text, channel='general') -> list[str]`. Human branch resets the existing three hop/paused/notice fields and returns only parsed mentions; remove human routing.default fallback deliberately. Agent branch preserves pause/hop/self-filter behavior. Existing continue_routing is the reset primitive the later trusted operator ingress can reuse. No new reset API.
- Keep `RuntimeRegistry.resolve_to_instances(self, name: str) -> list[str]`. Exact registered name wins as today; otherwise a known base with exactly one active member returns that member; multiple active members returns []; zero active members and unknown non-agent names keep existing [name] compatibility. Pending exact instances are still skipped by the caller. This changes only the unsafe multiple-family expansion.
- Keep `SessionEngine._on_message(self, msg: dict) -> None` callback signature. Replace its human-chat pause side effect with a documented inert callback: shared chat/decision content is display data, never admission, pause or progression. Current implementation already ignores legacy runs; explicit session Pause/Resume/Stop operations remain unchanged. Deliberately amend/rename the Ticket8 pause-on-chat test. No new Pause control/API.

### Shared review predicate and precise whitelist derivation

Add pure functions in queue_coordinator.py (no new module/framework):

```python
is_nonterminal_review(run: dict) -> bool
allowed_review_dispatch_ids(runs: list[dict], identity_id: str) -> set[str] | None
```

`is_nonterminal_review` requires completion_protocol ==1, no stop_id, no replaced_by_run_id, and state in active/waiting/paused/awaiting_input/stalled/retrying/interrupted/prepared. It does not require dispatch_eligible True, an active invocation, or proven native readiness.

`allowed_review_dispatch_ids` reads copied SessionStore.list_all() data, never a queue ledger or clock. For qualifying runs whose active_invocation.expected_identity_id equals the claimed identity, a human=True or consumed=True invocation imposes no restriction. An otherwise eligible invocation requires human and consumed both literalFalse, a positive integer session id (bool rejected), a dispatch_id valid under the existing queue identifier format (1..128 ASCII alphanumeric/underscore/dot/hyphen), and monitoring.created_at a finite nonnegative int/float (bool rejected). Missing/malformed monitoring, created_at, session id, flags or dispatch id for that matching identity yields an empty allowset, even if another candidate has valid ordering. No matching invocation yields None. Otherwise sort candidates by (monitoring.created_at, session id) and return the singleton earliest dispatch ID. No timestamp synthesis or persistence.

Keep `CoordinatedQueue.claim(self, instance, consumer_id)`. Under its existing RLock, reconcile existing holds, read sessions once for blocked runs and this helper, then pass allowed_dispatch_ids to raw claim. Derive identity from the immutable authenticated instance identity, never name. Existing store/queue lock nesting is unchanged: list_all releases store lock before queue transaction.

Extend `QueueStore.claim(self, instance, consumer_id, *, blocked_run_ids=None, blocked_identity_ids=None, allowed_dispatch_ids=None)`. Validate None or a set of existing-format identifier strings; invalid shape raises ValueError before mutation. Existing active/cancelling exact-owner polling remains first and is unaffected by the whitelist. Preserve blocked-run cancellation exception, identity/recovery holds. For new queued claims iterate the full identity-specific FIFO, skip blocked run or unallowed dispatch, and claim the first allowed record. Empty allowset claims nothing; a publication gap or blocked allowed run cannot fall through to manual/later work. No queue rewrites on skipped claims.

### Channel predicate and agent-wake suppression placement

Add `SessionEngine.has_nonterminal_review(self, channel: str) -> bool`: under engine RLock read copied sessions for that channel and apply is_nonterminal_review. This differs from get_allowed_agent: prepared/paused/interrupted/awaiting_input also count, regardless of active invocation. Keep get_allowed_agent unchanged for other existing callers.

In app._handle_new_message, retain typed-projection and stopped/superseded-scope early display-only returns. Determine whether the current registered sender is an agent and channel has_nonterminal_review. Agent ordinary chat must broadcast without Router.get_targets, loop-hop mutation or trigger. This check must also stop built-in slash reposts from re-entering as human-looking routing input. Preserve existing agent session-draft validation/cards as display-only: compute the suppression boolean before slash branches, prevent all four broadcast slash branches when suppressed, then after draft extraction return before raw_targets. Suppressed non-draft ordinary chat broadcasts once; a suppressed agent slash remains literal shared text rather than expansion. Existing genuine typed scheduling is untouched.

Apply the same predicate before agent job mention loops in mcp_bridge.py (authenticated instance, job.channel) and the equivalent app job path, preserving existing chat_scope quarantine. This closes a job-thread bypass rather than waiting for operator-job ingress in Tranche3. Operator-origin classification and trusted receipts are still the next tranche; display sender alone will not become authority there.

### Bounded tests after reviewer freeze

Helper assignment proposed: only new tests/test_recipient_runtime_order.py, about12 cases. First actual red: released-but-unconsumed current review must deny a queued manual claim; pure allowed_review_dispatch_ids missing method; nonterminal agent chat must not trigger even its expected peer. Use real engine/store/registry/queue fixtures with explicitly nonnative process doubles. Extend to two runs/same seat ordering, raw queued scan past skipped record, malformed/NaN/bool timing, no occupancy default, Stop/superseded/human/consumed boundaries, owner/cancelling polling/recovery holds and byte-stable no-claim. Root owns separate Router/alias/agent-suppression tests and deliberate old Ticket8 test edit, with actual red first. No helper edits to old tests or production. Freeze approval is required before assigning this workorder.
