# Ticket #12: expose stalled turns and allow retry

**State:** Contract ratified by same AGY, including explicit preparation repair (Section7) and scoped Windows HTTP loop selection (Section8). Implemented and builder-tested; builder regressions complete with one recorded unexplained transient MCP return stall; frozen independent review pending. No publication or independent implementation PASS. TICKET-12-REVIEW.md records evidence and boundaries.

**Authority:** Approved issue #12, specification v1.7 SC-5 and AT-21a/d/22, with Seth's standing autonomous execution amendment. #8 and #11 are published/closed. Base main `0d247d5a19631dd2b70c20d2861d76af9144da8d`. Codex implements; the same AGY critiques the contract and independently reviews the frozen implementation.

## Scope

Make a missing acknowledgement, explicit failure, disconnected seat or overdue response visible without losing accepted work. Offer explicit wait/extend and retry of the current turn, with a fresh attempt and permanent fencing of the old attempt. Preserve source, role/design/rules, completed results and unrelated work.

Keep the existing stores, queue transaction ledger, coordinator lock, immutable briefs and owned invocation cancellation. No storage migration or new dependencies. API result outbox/delivery recovery remains #13; inspected CLI answer recovery #14; explicit participant replacement/skip #15; full process adoption after server restart #9; six-seat capacity #16. A post failure before #13 must not claim that an answer is durably recoverable.

## Source observations

- `SessionStore.bind_invocation` saves run/turn/attempt/brief/dispatch identity, but no acknowledgement or response deadlines. `build_brief` already creates a stable turn ID from run/phase/participant and a new attempt ID on each build.
- `wrapper_api.handle_trigger` distinguishes provider, malformed-session and local-delivery failures, and releases transport with an error category. An empty response currently returns false without a specific category. Session progress is not updated by this failure transport receipt.
- Queue records already persist timestamped queued/dispatched/acknowledged/released/failed events. Transport release does not admit a result or advance a phase. The ledger retains ownership for uncertainty/cancellation and permits only one active dispatch per seat.
- SessionEngine serializes admission, Stop and coordinated claim/enqueue with its RLock. Permanent Stop fences are run-scoped; no equivalent superseded-attempt recovery transaction exists yet.
- API request cancellation can end one owned invocation while retaining its seat supervisor. Generic CLI turns have no verified interrupt, so a live stalled CLI cannot safely receive another injected prompt merely because a timer expired.
- Startup projects accepted results and reconciles Stop without blindly redispatching. The browser currently shows waiting/paused/questions and Stop, with no turn failure checkpoint or wait/retry controls.

## Agreed shape

### Checkpoints and deadlines

Persist a per-invocation monitoring policy and current recovery checkpoint inside SessionStore. Record creation/enqueue time, acknowledgement deadline, response deadline after acknowledgement, last durable transport event, sanitized reason and the affected seat/role/phase/attempt. Record operator actions and superseded attempt identities separately from accepted results.

Use distinct configurable acknowledgement and response intervals, with adapter defaults and an explicit per-run override captured at Start. Ratified defaults: acknowledgement30s, response900s, monitoring1s. Precedence is global, managed-adapter, then explicit run overrides. Effective role/invocation policies are frozen; unmanaged identities use global/run settings. Expose active limits and remaining/due status to the operator. Human-result turns and awaiting-input questions have no machine response timeout. Explicit pause must not silently consume its suspended response allowance.

Run monitoring independently of an open browser. Queue failures surface immediately through server-side reconciliation of authenticated failed receipts; polling is the fallback when a failure report/ack is lost. A missing failure message must become visible within one configured monitoring interval after its deadline. A heartbeat is only connectivity evidence; it cannot renew an acknowledgement/response deadline or establish completion.

Reuse the authenticated queue failed-release event as the failure transport if it can carry the required bounded category/status without weakening admission separation. The server derives identities/seat/phase from immutable envelope and current invocation. Allowlisted categories and optional HTTP status contain no raw exception/body/source/credential data. If this path cannot provide truthful immediate failure, a separate compact authenticated failure endpoint is an alternative for critique.

### Wait and late results

Wait/extend names the current checkpoint and attempt, records an operator decision and extends its actual deadline without another model call or queue injection. It cannot clear a stopped/superseded fence. Paused runs resume explicitly; questions continue through their existing answer action.

An overdue checkpoint leaves the current unfenced attempt authoritative: a valid explicit final/question arriving before Retry or Stop resolves it normally. If admission wins the coordinator lock, stale Retry conflicts; if Retry wins, a durable superseded-attempt fence rejects/quarantines the old event. Timers, receipts and ordinary chat never advance a phase. No operator-held saved-answer recovery is added in #12.


### Retry and local ownership

An operator retry request binds checkpoint ID, old attempt ID and stable request ID. Validate current source/run/turn and eligibility, then durably record the superseded attempt fence before cancelling its exact dispatch. Keep the same logical turn, input/design/rules and prior accepted results; mint a new brief/attempt/dispatch. Do not rerun completed phases.

Maintain the existing coordinator order: engine RLock spans sequential SessionStore and QueueStore transactions; never hold one store lock while taking the other. Queue eligibility checks persisted superseded-attempt fences as well as Stop, without importing SessionStore into QueueStore. Fence only explicitly superseded attempts, since accepted finals can legitimately leave old transport held until cooperative release.

Cancel only the old dispatch, never all pending work for the run or peer seat. API cancellation uses actual observed local child exit and IPC cleanup, with remote compute unverified. Queue ownership remains held until its verified release/end; elapsed time cannot transfer it. New attempt preparation/dispatch must be idempotent across failed writes, enqueue failure and lost HTTP responses.

Generic live CLI retry requires explicit exact-launch termination and proven client/worker exit before an owned relaunch from the same frozen profile. The new process/identity is labeled same_turn_retry_relaunch. Generic native context is not claimed clean; verified fresh-context arguments are used only when that contract is present. Model/seat reconfiguration remains #15. Unrelated queued/active work on the old seat blocks termination before any retry fence or control write.


Old typed results, scoped chat and delayed routing from superseded attempts lose admission/routing authority permanently. A fresh correctly tagged attempt and unrelated human/peer discussion remain usable. Unknown untagged output cannot be treated as a verified retry result.

### Operator surface

Show the failed/stalled seat, phase, reason, last acknowledged event and active limits. Explain the distinction between missing ack, disconnected seat, live-but-overdue response and explicit generation/delivery failure. Show whether a saved answer is known; before #13, an unsaved/post-failed answer is not offered as recoverable.

Offer Wait/extend, Retry current turn and existing Stop. Preserve completed results and frozen source in the current run. Exact owned CLI termination remains a separate explicit confirmation with visible impact. Persist checkpoints/actions through refresh and store reload. Full runtime adoption is deferred, so restart cannot auto-reclaim or auto-replay an uncertain live invocation. Failed preparation remains visible with an explicit repair action, rather than an automatic retry loop.

## Alternatives considered

| Approach | Consequence |
| --- | --- |
| Per-turn durable checkpoint using existing session/queue stores (recommended) | Fits accepted architecture and preserves current work; requires explicit atomic recovery boundaries |
| Treat heartbeat/activity as completion or deadline extension | Cannot prove turn receipt/completion and masks live stalls; rejected |
| Automatically retry every overdue turn | Can duplicate model calls and collide with live CLI work; rejected |
| Stop/restart the whole run | Repeats accepted work and loses the required current-turn recovery semantics; rejected |

## Verification before publication

- Capture actual red regressions for missing ack, provider error, empty result, malformed result, failed post, dropped failure event, disconnected seat and live heartbeat with no result. Injected clocks test exact deadline boundaries independently of heartbeat.
- Real stores prove checkpoint persistence, wait without dispatch, fresh attempt identity, preserved prior results/source and failed-write rollback. Competing final/retry/Stop/claim operations admit only the winning authoritative attempt.
- Distinct same-turn retries remain idempotent under duplicate requests, post/enqueue acknowledgement loss and reload; stale retry controls cannot retry the next turn. A stopped/corrected run never recovers old-document work.
- Actual isolated API fixture uses sanitized HTTP/provider/empty/post failures and a delayed old result after explicit retry. Assert provider call counts and prior phase results, not only total test counts. No durable answer recovery is claimed without an outbox.
- Actual Windows fake CLI proves no second injection while old work is live; explicit supported end/owned termination and new identity precede any retry where required. Preserve peer seat/work, process ownership and remote-compute truthfulness.
- Desktop/mobile/keyboard UI checks, full discovery, all eight earlier integrations, static/diff checks and same-AGY frozen independent review/recheck. No live provider/native AI/global credential/Omarchy changes.

## Frozen interfaces and current checkpoint

Same AGY ratified engine policy/start overrides; monitor_turns(now=None); wait_turn(session_id,checkpoint_id,attempt_id,extend_seconds,now=...); retry_turn(session_id,checkpoint_id,attempt_id,request_id,confirmation=...,now=...). Positive finite policy values reject booleans. Defaults30/900/1 seconds are accepted builder defaults, not user-selected numbers. The coordinator RLock spans sequential store transactions, with each store lock fully released before acquiring the other.

Failure categories are provider_timeout, http_error, transport_closed, process_crash, malformed_session_response, provider_failure, local_delivery_failure and empty_completion. Optional HTTP status is an integer100-599; raw errors/payloads/credentials are excluded. Actual failure integration now passes, including empty content classification and one generation across failed result-post retries.

Manager retry_context_offer is read-only. prepare_retry_context preserves frozen settings, owns termination and waits for ready identity. Explicit engine repair_retry(session_id,request_id,preparation_attempt,confirmation=...,now=...) replaces failed preparation only if Popen never returned a handle or actual worker exit plus matching integer child receipt proves end. A live prepared context requires exact confirmation. Dead workers without client proof remain blocked. Repair retains reserved generation/turn/source/model and audits new preparation references; duplicate requests do not spawn again.

Windows main HTTP uses Uvicorn loop asyncio:SelectorEventLoop; other platforms retain auto. This is scoped to HTTP, with unchanged MCP thread loops/global policy. It avoids observed Proactor listener shutdown after WinError64. Windows select()512-socket limit is documented; capacity remains #16. Actual reset-connection regression and aligned --serve acceptance pass.

## Next owner

Same AGY independently reviews the frozen implementation and recorded transient MCP return stall. Codex fixes/rechecks substantive findings before publication. Bounded instrumented and unchanged queue reproductions passed; no production fix is inferred. No #12 publication or native AI/client acceptance claimed. See STATUS.md and TICKET-12-REVIEW.md.
