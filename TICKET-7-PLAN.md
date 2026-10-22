# Ticket #7: preserve every queued turn

**State:** Proposed implementation contract, awaiting independent AGY pressure-test. No #7 production changes yet.

**Authority:** Approved issue #7, specification v1.7 SD-3 / SC-5 / AT-21b and the October 22 autonomous execution amendment. #6 is published and closed. Codex implements; the same Antigravity agent reviews the frozen implementation and substantive fixes. Routine plan and completion decisions are delegated under standing authorization.

## Verified baseline

`AgentTrigger.trigger` and `trigger_sync` append name-based JSONL files. Both wrappers clear them before processing; they also clear pending files at startup. Ordinary CLI entries collapse into the last channel plus independently selected prompt/job fields. API entries collapse by channel. Frozen-brief entries remain separate, but CLI injects several without owning a turn through its execution. These paths can lose work even when the process heartbeat remains healthy.

## Proposed contract

1. Persist one immutable envelope per dispatch before returning from enqueue. Preserve dispatch ID, intended stable seat identity, channel, prompt, job, review-brief reference and supplied run/turn/attempt/input metadata together. Generate an ID when absent; deduplicate only an identical ID with identical contents and recipient. Reject conflicting reuse explicitly. Two identical texts with different IDs are distinct work.
2. Use the standard-library SQLite store under the configured data directory. Transactions and a unique live-ownership constraint serialize competing consumers across threads/processes. Store no bearer tokens or provider credentials. Resolve stable identity at enqueue; unregistered legacy names require an explicit compatibility policy rather than silently granting work to a future replacement seat.
3. Wrappers use bearer-authenticated queue endpoints. Claim atomically records dispatch ownership with an opaque per-wrapper consumer ID before returning an envelope. A lost claim response leaves durable uncertainty, and never silently replays a model call. Claiming a second turn for an occupied seat returns contention rather than another envelope. Enqueue remains available while a seat is busy.
4. Keep separate durable `queued`, `dispatched` and `acknowledged` receipts. Injection/provider acceptance acknowledgement refers to exactly that dispatch and owner. Finish/failure records retain the envelope and receipt history. Heartbeat, typing/idle status, ordinary chat and channel name do not release ownership. A wrapper restart with a new consumer ID must not inherit or replay an uncertain in-flight dispatch automatically. Full server-restart reconciliation and retry controls remain #9/#11.
5. API executes each claimed envelope separately and serially, including two turns in the same channel. Forward its own prompt and job context, not another entry's fields. Acknowledge after accepting the durable envelope, mark transport work finished only after successful response delivery, and preserve failure diagnostics. A failed generation/delivery is not successful completion. API result-outbox/idempotent answer recovery remains the later recovery ticket.
6. CLI injects one envelope at a time with that envelope's channel/prompt/job or frozen-brief instructions. The injection explicitly names its dispatch ID and requests an authenticated queue-release tool after the agent finishes that work. Release is scoped to the same seat and dispatch. This tool releases transport ownership only; it must not admit session results or advance the engine. #8 will add the explicit run-result contract. If injection or its acknowledgement fails, retain uncertain ownership and block another injection rather than guessing the client did no work.
7. Surface per-seat queued count, current dispatch state/ID and contention in authenticated status and a small operator-visible queue view. Never label an uncertain dispatch completed. Avoid exposing source text or bearer tokens in summaries. Empty queue polling is normal; storage/validation failures are visible failures, not swallowed exceptions.
8. Existing JSONL files must not be erased on startup. Compatibility is an open implementation question below. Updated wrappers must not continue running the lossy read-clear path alongside the durable consumer. Existing Desktop installation and its data stay untouched.

## Questions for AGY pressure-test

- Is the CLI transport-release tool sufficient to enforce one owned turn without incorrectly pulling #8 completion admission into #7? Check noncompliant clients: queued work should remain visible and blocked, never overlap or advance itself.
- Should legacy pending JSONL be imported once through a read-only ledger (file identity plus byte position/content fingerprint), or explicitly surfaced as legacy work requiring operator resolution? Either preserves originals. Silent dropping and auto-replaying uncertain pre-existing work are prohibited. Inspect actual current producer/consumer and registration contracts before recommending.
- Test the claim-response-loss, injection-before-ack crash, duplicate acknowledgement, replacement seat, rename, concurrent consumer and failed storage windows. Identify anything the proposed receipt states cannot represent before implementation.
- Check whether SQLite adds avoidable complexity compared with existing atomic JSON and startup locks. The requirement is durable cross-process ownership, not a preferred database.

## Planned verification

- Failing tests first, real temporary durable store and registry. Two distinct CLI envelopes with different channels/prompts/jobs, two API turns in one channel, duplicate ID versus identical text, immutable fields and FIFO under contention.
- Competing processes/consumers never own two turns for one seat; separate seats can progress. Failed enqueue/claim/ack leaves durable recoverable state. Reopen store after wrapper failure and inspect pending/in-flight receipts without automatic replay.
- Authenticated HTTP/MCP tests reject wrong seat, wrong consumer, stale/replaced identity and invalid payload; rename keeps identity-bound ownership. Ordinary status/chat cannot release a dispatch.
- Real isolated app with fake API provider and real fake CLI console/MCP transport. Verify both distinct turns arrive separately with exact fields and receipts, one owned turn per seat, visible contention and retained work after an owned wrapper failure. No live providers or installed client changes.
- Run full suite and existing frozen-brief/package integrations, JavaScript syntax and whitespace checks. Preserve platform limitations. Same AGY independently tests the frozen implementation and rechecks substantive fixes before merge/push/closure.

## Tasks

- [ ] Same AGY pressure-tests and resolves the proposed transport ownership/compatibility contract.
- [ ] Test-only helper writes meaningful red regressions against agreed interfaces.
- [ ] Implement durable store, scoped endpoints/tools, trigger producer and serial wrappers.
- [ ] Show queue state/uncertainty and exercise real fake-client failure windows.
- [ ] Freeze, independent same-AGY review/recheck, reviewed publication and closure.

Next owner: same AGY reviewer returns a contract critique; Codex then settles the bounded implementation choices and begins tests/production work. This is an asynchronous agent handoff, with no human approval requested.
