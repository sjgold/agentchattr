# Ticket17: explicit recipients are authoritative

State: source-grounded proposal, pending Sonnet contract critique. No Ticket17 production or test edits yet. Routine per-ticket human gates remain removed under Seth's renewed October23 evening authorization.

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

## OPEN1: address grammar and unknown/offline policy

Proposed lexical contract (bounded linear scan, no new dependency):

- Fenced backtick/tilde blocks, including an unclosed fence, are data. Markdown quote paragraphs (including lazy continuation until a blank line) are data. Inline code spans are data.
- Balanced prose quotes (ASCII single/double and typographic pairs) are data; apostrophes inside words are not quote openers. Settle exact unclosed-quote behavior before tests.
- Address token boundary prevents email/local-word substrings. Exact case-insensitive full names; underscores/hyphens within identifiers; never accept a known prefix of an unknown longer name.
- Preserve first textual occurrence order and deduplicate by immutable target identity. Exact registered name wins over family expansion. @both remains a documented compatibility alias of @all.
- An unknown token counts as explicit addressing. Known+unknown sends only the known subset with a visible warning; unknown-only sends shared chat to no agents, despite selected buttons or routing.default.
- @all uses registered, non-pending, currently online seats. Explicit registered-but-offline recipients may remain queued with an offline warning; nonexistent/unregistered names are unavailable and cannot reserve a future identity.
- Only authored text enters the lexer; attachment names, paths, extracted bodies and review packet source are never scanned. Plain pasted prose without a quote/code boundary is authored text; do not invent document-detection heuristics.

Candidate component interface: recipient_routing.scan_addresses(text) -> {tokens, explicit}; resolve_recipients(text, selected_names, instances, online_names) -> {mode, tokens, recipients:[{name,identity_id,online}], unknown, warnings}. Pure copied output, no registry/store/queue/process effects. Exact signatures/schema freeze after critique, before observed-red helper tests.

## OPEN2: authoritative ingress and preview

Candidate POST /api/recipients/preview, operator-only/no-store, takes authored text and selected names, returns sanitized current audience/warnings/wait status. It never pauses, enqueues, spawns or mutates hop counters. Bound text and metadata consistently with existing message limits; settle exact bounds before tests.

WebSocket operator message carries raw text and selected_recipients separately. Server recomputes resolution, classifies origin from authentication rather than the display sender, and writes internal recipient_routing metadata with exact identity set and warnings. Clients cannot submit that internal receipt. Callback wakes only those frozen identities (same-identity rename allowed, no successor identity guessed); derive stable per-message/per-identity dispatch IDs for repeated callbacks, using existing queue idempotency. Add a small identity-based AgentTrigger helper rather than looking up a mutable name again.

Preview is informational and refreshed before Send. No new fingerprint ticket/secret/store: the accepted message receipt displays the actual server-resolved audience if membership changed. Client does not rewrite authored text. It retains the draft while final preview/connection validation fails and prevents double submission during that check. Broader exactly-once human send/ACK recovery is outside this ticket.

New authority metadata is removed on archive import; imported/history messages broadcast without triggering. Existing typed projections and quarantined/stopped scope remain routing-suppressed. API/MCP agent paths retain bearer-derived identities and cannot forge operator selections.

## OPEN3: busy seats and review order

Recommend default Wait, shown explicitly in recipient preview, with no new interrupt choice or implicit pause. Operator-routed wait messages do not auto-pause the review in _on_message. Stop remains the deliberate way to cancel it.

Queue new-claim guard must check typed logical occupancy, not just physical ACTIVE records. Under the existing coordinator lock, collect each identity's earliest unconsumed non-human review invocation (stable created time/session-ID ordering). Allow only that exact review dispatch as a new claim until a typed final/question resolves it; manual and later-review dispatches stay queued. Existing matching active/cancelling consumer polling remains first, including cold cancellation delivery. Existing physical ACTIVE, recovery_hold and retired old_transport gates still apply.

Candidate raw claim keyword allowed_dispatch_ids=None applies only to NEW queued claims. A missing set preserves existing direct raw queue callers; coordinator supplies the precise set for occupied identities. No synthetic ACK, lease extension, cancellation ID or process control.

Agent chat bound to a frozen review must never create extra work beyond the engine's typed scheduling. OPEN: suppress all mention wakes from review-scoped ordinary agent chat (recommended), or keep a narrower expected-agent filter. Out-of-run authenticated agent discussion retains ordinary explicit addressing and loop guard, while stopped/superseded scope remains suppressed. Test paused/stalled/interrupted as well as active, and fresh independent discussion after Stop.

## OPEN4: human ingress and slash/scheduling scope

Recommend one resolver for channel WebSocket and operator job-thread posts, and the same lexical rules for agent Router addresses. Job reply defaults are selected recipients, so any explicit token overrides them. All paths retain shared visibility.

Address-dependent built-in slash expansions must use the resolved audience rather than secretly broadcasting to every agent. Non-routing local commands remain local; quoted commands stay display data. OPEN: reconcile existing /roastreview, /artchallenge, /hatmaking and /poetry broadcast defaults with RC-1's no-explicit/no-selection rule. Recommend no hidden default audience, with a visible no-recipient hint.

New scheduling choices should use explicit-over-selected resolution too; persist existing approved target semantics and preserve literal prompt/source text. OPEN: adjust only the current scheduling composer/server creation boundary, or explicitly defer scheduling UX to its own ticket. Never rewrite stored historical schedules or add a new scheduler in17.

## Implementation/verification tranches after settlement

1. Pure lexer/resolver plus Router compatibility: helper owns a new bounded test module, captures initial missing-interface/quote/unknown errors before production. Cover multiline/fences/prose quotes/apostrophes/email, aliases/case/full tokens, all/none/mixedunknown/offline, stable identity dedup and no mutation.
2. Server preview/operator ingress/callback/identity routing and logical queue guard: observed-red tests with real stores/registry/ledger and real middleware, explicit scheduling fixtures. Prove no wider fallback, immutable audience, no implicit pause, released-but-unconsumed hold, consumer cancellation polling, Stop/old identity protections, import/projection safety and queue failure behavior.
3. Composer/job/scheduling boundary agreed above: actual UI preview and raw-text preservation, unknown warning, checkbox precedence/none/all, draft retention on preview failure, desktop/mobile/keyboard checks. New UI inherits existing14px/44px panel tokens; no full-page redesign.
4. Isolated Windows/local-fake acceptance: actual per-seat invocation counts for explicit subset versus buttons, no mention wakes from quoted data, busy manual work waits for typed event plus release, peer remains available and Stop fences remain effective. Retain exact native handles/complete cleanup; root reviews draft before execution. No live provider/native AI or Omarchy.
5. Full918 baseline plus meaningful new tests, prior routing/session/Stop/Retry/outbox/recovery integrations, Sonnet source/reproduction review and substantive recheck, post-merge verification and standing-authorized publication/closure. Continue dependency order.

Review focus: no accidental audience expansion, no interpretation of source as addresses/commands, no name-to-new-identity race, no bypass via job or MCP ingress, no duplicate mention successor, and no logical-review overlap after early transport release. Keep the implementation smaller than a new scheduling/delivery framework.
