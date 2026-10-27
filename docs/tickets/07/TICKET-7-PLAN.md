# Ticket #7: preserve every queued turn

**State:** Contract settled after same AGY critique and source-based follow-up. Test authoring and implementation in progress. AGY confirmed console quietness is not readiness; final frozen implementation review remains mandatory.

**Authority:** Approved issue #7, specification v1.7 SD-3 / SC-5 / AT-21b and the October 22 autonomous execution amendment. #6 is published and closed. Codex implements; the same Antigravity agent reviews the frozen implementation and substantive fixes. Routine plan and completion decisions are delegated under standing authorization.

## Verified baseline

`AgentTrigger.trigger` and `trigger_sync` append name-based JSONL files. Both wrappers clear them before processing; they also clear pending files at startup. Ordinary CLI entries collapse into the last channel plus independently selected prompt/job fields. API entries collapse by channel. Frozen-brief entries remain separate, but CLI injects several without owning a turn through its execution. These paths can lose work even when the process heartbeat remains healthy.

## Settled contract

1. Persist one immutable envelope per dispatch before returning from enqueue. Preserve dispatch ID, intended stable seat identity, channel, prompt, job, review-brief reference and supplied run/turn/attempt/input metadata together. Generate an ID when absent; deduplicate only an identical ID with identical contents and recipient. Reject conflicting reuse explicitly. Two identical texts with different IDs are distinct work.
2. Use a single atomic JSON transaction ledger at `data/queue/ledger.json`, protected by the existing kernel-held `startup_lock` and `atomic_json`. Each envelope, owner and receipt transition commits in one replacement, avoiding crash windows between separate claim/envelope files. Read the ledger again under lock for every operation; no stale in-memory writer snapshots. Store no bearer tokens or provider credentials. Resolve stable identity at enqueue; unregistered legacy names require an explicit compatibility policy rather than silently granting work to a future replacement seat.
3. Wrappers use bearer-authenticated queue endpoints. Claim atomically records dispatch ownership with an opaque per-wrapper consumer ID before returning an envelope. A lost claim response leaves durable uncertainty, and never silently replays a model call. Repeating claim with the same consumer returns the same current envelope, recovering a lost response. A different consumer receives contention. The wrapper guards already-injected IDs in memory, so repeated claim polls never repeat terminal injection. Enqueue remains available while a seat is busy.
4. Keep separate durable `queued`, `dispatched` and `acknowledged` receipts. Injection/provider acceptance acknowledgement refers to exactly that dispatch and owner. Finish/failure records retain the envelope and receipt history. Heartbeat, typing/idle status, ordinary chat and channel name do not release ownership. A wrapper restart with a new consumer ID must not inherit or replay an uncertain in-flight dispatch automatically. Full server-restart reconciliation and retry controls remain #9/#11.
5. API executes each claimed envelope separately and serially, including two turns in the same channel. Forward its own prompt and job context, not another entry's fields. Acknowledge after accepting the durable envelope, mark transport work finished only after successful response delivery, and preserve failure diagnostics. A failed generation/delivery is not successful completion. API result-outbox/idempotent answer recovery remains the later recovery ticket.
6. CLI injects one envelope at a time with that envelope's channel/prompt/job or frozen-brief instructions. The injection explicitly names its dispatch ID and requests an authenticated queue-release tool after the agent finishes that work. Release is scoped to the same seat and dispatch. This tool releases transport ownership only; it must not admit session results or advance the engine. #8 will add the explicit run-result contract. If injection or its acknowledgement fails, retain uncertain ownership and block another injection rather than guessing the client did no work.
7. Surface per-seat queued count, current dispatch state/ID and contention in authenticated status and a small operator-visible queue view. Never label an uncertain dispatch completed. Avoid exposing source text or bearer tokens in summaries. Empty queue polling is normal; storage/validation failures are visible failures, not swallowed exceptions.
8. Existing JSONL files remain untouched and are listed as legacy_unmigrated_files in operator status. They are not automatically imported or replayed. Updated wrappers must not continue running the lossy read-clear path alongside the durable consumer. Existing Desktop installation and its data stay untouched.

## Independent critique resolutions

- AGY initially suggested supervisor prompt-readiness detection. Source inspection showed only activity-delta/quietness heuristics and whole-process exit. AGY accepted holding ownership through silence, chat and heartbeat: explicit authenticated transport release is required, the watcher verifies it before injecting again, and clients that omit it remain visibly awaiting release. This safety limitation is documented rather than hidden by guessing readiness. Process exit/failure must retain uncertainty; never blindly replay.
- Existing atomic JSON plus one transaction ledger replaces the initially proposed SQLite. Separate claim and envelope files are avoided because a crash could commit only half a transition.
- Identity binding, idempotent same-consumer claim and no legacy replay were confirmed. The original critique plus source-based corrections are preserved in the `ticket-7-contract-review` artifact. No new human approval gate is introduced.

## Planned verification

- Failing tests first, real temporary durable store and registry. Two distinct CLI envelopes with different channels/prompts/jobs, two API turns in one channel, duplicate ID versus identical text, immutable fields and FIFO under contention.
- Competing processes/consumers never own two turns for one seat; separate seats can progress. Failed enqueue/claim/ack leaves durable recoverable state. Reopen store after wrapper failure and inspect pending/in-flight receipts without automatic replay.
- Authenticated HTTP/MCP tests reject wrong seat, wrong consumer, stale/replaced identity and invalid payload; rename keeps identity-bound ownership. Ordinary status/chat cannot release a dispatch.
- Real isolated app with fake API provider and real fake CLI console/MCP transport. Verify both distinct turns arrive separately with exact fields and receipts, one owned turn per seat, visible contention and retained work after an owned wrapper failure. No live providers or installed client changes.
- Run full suite and existing frozen-brief/package integrations, JavaScript syntax and whitespace checks. Preserve platform limitations. Same AGY independently tests the frozen implementation and rechecks substantive fixes before merge/push/closure.

## Tasks

- [x] Same AGY pressure-tests and resolves the proposed transport ownership/compatibility contract.
- [x] Test-only helper writes meaningful red regressions against agreed interfaces.
- [x] Implement durable store, scoped endpoints/tools, trigger producer and serial wrappers.
- [x] Show queue state/uncertainty and exercise real fake-client failure windows.
- [x] Freeze, independent same-AGY review/recheck, reviewed publication and closure.

Next owner: same AGY independently verifies the frozen implementation; Codex addresses substantive findings and obtains recheck before reviewed publication.

## Builder evidence

Final suite293 OK (four Unix/tmux skips), all dispatch/store/auth/producer/consumer regressions pass. Normal and serve-mode real mixed-seat integration passed after an observed early cooperative-release race was reproduced and fixed; original receipt-history assertion remains. Exactly2 API fake calls and2 CLI/MCP turns; held release blocks overlap; manager-owned worker stop retains uncertain+queued work, not a SIGKILL test. Frozen-brief, package, API-seat and CLI-seat integrations pass. Queue panel rendered/keyboard checked with desktop/mobile screenshots; scope and inherited UI limits are recorded in STATUS.md. Same AGY independently returned PASS. Published at `98f2722`, issue #7 confirmed closed, post-merge293 tests OK (four skips). Next: #8 explicit completion.
