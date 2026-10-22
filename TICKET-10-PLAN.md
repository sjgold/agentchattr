# Ticket #10: stop an active review reliably

**State:** Implemented and builder verified; same-AGY independent implementation PASS. Reviewed publication in progress.

**Authority:** Approved issue #10, spec v1.7 SC-1/2 and AT-06, autonomous execution amendment. Its only blocker #8 is published and closed. #9 full restart reconciliation remains deferred by first-milestone order. Base main `3bb4357`.

## Verified baseline

- Session End currently persists `interrupted`; typed event admission rejects that run afterward, but queued work and active provider/CLI work are not cancelled. Ordinary message routing can still produce mentions without a run dispatch identity.
- Queue envelopes already carry run/turn/attempt/input identity; one owned transport turn per seat is enforced. Claims, admission and Stop currently lack a shared linearization boundary across their separate stores.
- API generation blocks inside the wrapper's urllib call. Existing SeatManager.stop writes a whole-worker stop control, waits two seconds, then calls stop_owned_child. This is seat termination, not graceful per-invocation cancellation. Reusing it automatically would affect the seat context and unrelated queued work.
- CLI wrappers can inject text and detect activity, but no verified native per-turn interrupt/acknowledgement contract exists. Quietness and process heartbeat are not cancellation evidence. Native client acceptance remains outside routine scope.

## Proposed safety contract

1. Stop first atomically persists `dispatch_eligible=false`, its run-scoped stop ID and state `stopping`. Commit before signalling adapters. It is idempotent, retains accepted results/source/design and blocks new admission/continuation. A crash between this commit and queue cleanup must never make stopped work eligible on restart.
2. Cancel only queued envelopes belonging to that run, including run-tagged descendants. Active claims become `cancelling` and retain ownership until an appropriate receipt. Envelopes for other runs and ordinary work are preserved. Claim/enqueue/admission must consult the persisted run fence under a consistent lock order; a pre-existing queued record cannot bypass Stop after reload.
3. Add scoped cancellation/control receipts, addressed to exact dispatch and consumer plus stable seat identity. Separate `requested`, `delivered`, `local_ended`, `unsupported` and `unresolved` evidence. An idle flag, missing heartbeat, dropped socket or UI dismissal cannot prove computation stopped. New/stale consumers must not acknowledge another invocation or target a replacement process.
4. Return promptly with stopping state and per-invocation progress. Proposed cancellation deadline: ten seconds. At the deadline, expose unresolved work and its last receipt; do not claim stopped while local work is still known to run. Keep dispatch ineligibility and late-output fences durable even if cancellation is unsupported or the server restarts. This is Stop reconciliation only, not general adoption/replay from #9.
5. **Selected and AGY-ratified API mechanism:** isolate each model call in a dedicated owned child process while keeping the seat supervisor alive. Pass request/source/credentials through in-memory IPC, not command-line arguments or persisted secrets. Use communicate to drain pipes; local_ended requires observed child exit and completed IPC cleanup. Cancellation ends only that invocation child using its actual owned process handle. The supervisor can then service unrelated queued turns. Remote provider compute remains unverified.
6. **CLI capability boundary:** deliver the cancellation request to the owning wrapper and use only a declared, verifiable adapter cancellation method. The current generic console adapter may report unsupported/unresolved. Never guess completion from screen quietness, inject a second task as a cancel signal, or terminate the persistent client automatically. Fake acceptance must exercise supported API cancellation and honest unsupported CLI behavior; it cannot certify native CLI cancellation.
7. Offer scoped termination only for a positively owned launch/invocation. For a shared persistent CLI process, show the affected seat/context and queued work before explicit operator confirmation. Bind that action to exact launch attempt plus dispatch ID and recheck ownership under the manager lock. Never kill arbitrary PIDs, a replacement launch, unrelated processes, or a whole channel. Existing whole-seat stop needs this explicit boundary.
8. Preserve late typed output in a bounded quarantine journal after validating its immutable identity and actual seat provenance. It must not enter accepted results, alter phase position, dispatch successors or route mentions. Reject wrong-seat/unknown-provenance submissions normally. Previously accepted event retries remain duplicate receipts rather than newly quarantined results.
9. **Routing provenance proposal:** allow chat_send/API chat replies to carry their dispatch ID, and automatically include it in wrapper-owned API replies/CLI instructions. Propagate authenticated run scope to any resulting triggers. Reject or quarantine stopped-scope output before ordinary routing. After a stop fence, ambiguous unscoped output from that controlled seat must never start work; label ambiguous attribution honestly. Human discussion and unrelated seats remain independent. A fresh legitimate discussion dispatch has its own identity and can proceed when the seat is free.
10. UI Stop replaces End's implied completion with actual stopping/evidence states. Show local adapter outcome separately from remote-provider uncertainty, late-output quarantine and an explicit scoped-termination offer when available. Do not erase channel history or earlier accepted results.

## Settled coordination order

Same AGY accepted this order in its contract critique, Section 7. A coordinator RLock spans Stop, claim, enqueue and admission. Under it, acquire SessionStore only to read/persist eligibility, release that store lock, then acquire QueueStore for its transaction. Neither store lock is held while acquiring the other. QueueStore never calls SessionStore. Every HTTP, MCP and routing producer must use the coordinator; cold startup loads persisted fences before claim loops begin. This closes the live gap between the Stop commit and queue cancellation while retaining the durable fence across crashes.

## Cancellation diagnostic evidence

Test-only helper supplied `tools/probe_http_cancellation.py`, using the exact workspace Python 3.14.6 on Windows. Reproduce the decisive bound with `.venv-windows/Scripts/python.exe tools/probe_http_cancellation.py --long-bound --skip-ipc`. Evidence is local scratch, not portable acceptance evidence for the eventual product implementation.

| Measured case | Result |
| --- | --- |
| HTTP and TLS1.3 body reads, shutdown+close from another thread | Close returned in 0.295/0.330ms; workers still alive at 10002.844/10010.970ms. Both exited only after fixture progress resumed near 12s. Outcome at ten seconds: unresolved. |
| Owned child blocked in an actual urllib body read | terminate+communicate observed exit in 2.346ms before provider progress; parent and fake-provider health remained usable. Remote compute unverified. |
| Short matrix: headers/body, timed/blocking sockets, DNS/connect stalls | Socket closure did not prove worker exit; cancellation guards prevented publication after fixture cleanup. urllib response.close itself could block. |
| 512KiB echo through communicate, three runs | Exact payload/exit0, no observed deadlock. These small-process measurements do not predict full provider-runner overhead. |

Evidence files: `.audit-tmp/http-cancellation-probe-04f8b91f.json` (ten-second bound and owned blocked child), `http-cancellation-probe-df886a9d.json` and `http-cancellation-probe-d1eb4d96.json` (short HTTP/TLS/stall sweeps). All reported workers/closers exited during bounded cleanup. TLS used existing OpenSSL and a scratch certificate, with no installation or live provider calls.

The [Python socket documentation](https://docs.python.org/3/library/socket.html#socket.socket.close) describes close/makefile lifetime caveats and recommends shutdown for timely connection closure; it does not promise worker termination. The [subprocess documentation](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.communicate) recommends communicate for pipe handling. Actual worker-exit observations determine this Windows mechanism choice. Earlier spawn-latency/deadlock estimates were withdrawn as unmeasured premises.

## Remaining questions for independent pressure-test

- **Atomic fence and lock order:** What is the smallest reliable coordination boundary between SessionStore Stop, QueueStore claim/cancel and engine dispatch? A proposed engine/coordinator lock around persisted fence plus claim/enqueue must cover every HTTP/MCP/routing entrypoint. Inspect callbacks for lock inversion. On cold restart, reconcile stopped-run queue eligibility without claiming general runtime adoption.
- **API cancellation mechanism:** Is an owned child per model call the smallest robust solution for this blocking wrapper? Compare against cancellable connection/async approaches supported by the actual dependencies. Preserve model/response metadata and ordinary API behavior. No new dependency or provider capability should be assumed. Specify which receipts prove local termination and which remain remote unknown.
- **CLI unsupported and termination:** Define honest state transitions and ownership retention for adapters without verified interrupt support. Can cooperative transport release report local turn-ended evidence without pretending that the provider was cancelled? State what remains unresolved. Confirm that forced shared-context termination is a separate explained operator choice, not the default Stop implementation.
- **Unscoped late messages:** Static bearer identity cannot distinguish an old callback from fresh discussion by itself. Pressure-test dispatch-tagged chat, stopped-scope routing suppression and quarantine against late messages after transport release/new work. Avoid both cascade bypass and blanket channel/global pauses. Clarify the compatibility boundary for native clients that omit dispatch IDs.
- **Race at final admission:** Stop racing final admission, projection, successor enqueue or claim must have one explainable order. Keep results accepted before the fence, suppress work after it, and preserve late output without accepting a second result. Do not import worker answer-outbox recovery or corrected clean restart from later tickets.

## Verification contract

- Red tests with real stores: Stop flag persists before any signal, repeated Stop is idempotent, queued stopped-run work is cancelled, unrelated envelopes remain, and crash/reload between fence and queue cleanup never resurrects work.
- Controlled races: final versus Stop, enqueue/claim versus Stop, callback/mention versus Stop, cancellation acknowledgement versus new attempt, stale targeted-termination confirmation versus replacement launch. Verify exact run/dispatch/identity fields and accepted-result counts, not proxy totals.
- Real isolated delayed fake provider: Stop during generation reaches the actual owned invocation mechanism, local request ends or is reported unresolved by the deadline, no accepted late result/cascade occurs, and another run/seat continues. Remote-provider compute outcome remains unverified unless the adapter has a real acknowledgement contract.
- Real fake CLI/MCP: demonstrate unsupported cancellation honestly, no quietness release or hidden second injection, quarantine late output and suppress its mentions, then exercise explicitly confirmed owned termination without killing peers. Never infer a native client pass.
- Render operator Stop/stopping/unresolved/quarantine/termination controls, including reload of stopped eligibility. Full suite and existing session/brief/queue/package/seat regressions, syntax and whitespace checks. Same AGY independently verifies the frozen implementation and substantive fixes before publication.

## Tasks

- [x] Same AGY pressure-tests and resolves the fence/cancellation/provenance contract (critique Section 8).
- [x] Test-only helper captures red scoped-stop/race/late-output regressions (14 tests, observed red then green).
- [x] Implement durable fence, scoped queue cancellation and ingress quarantine/routing guards.
- [x] Implement adapter evidence and bounded cancellation, plus explicit owned termination/UI.
- [ ] Isolated real fake-client verification, frozen same-AGY review/recheck, reviewed publication/closure.

Next owner: Codex publishes the reviewed merge and closes #10, then begins #11 contract planning. Same AGY independently passed all checks; no application fixes requested. No routine human approval is requested. Live provider usage, Desktop installation changes and native Omarchy remain outside authorization.

## Implementation checkpoint

- Builder reran the decisive probe: evidence `.audit-tmp/http-cancellation-probe-e36c5b05.json`, HTTP/TLS workers still alive at ten seconds; owned request child exited in 1.987ms before provider progress.
- New `api_invocation.py`: four tests observed missing-module red, then all passed with actual loopback HTTP children, exact 512KiB request/result, credential header, safe HTTP401 classification and cancellation preserving provider health. Wrapper now uses the child runner; existing real fake-API integration passes. This is partial integration, not completed Stop acceptance.
- Helper `tests/test_session_stop.py`: 14 tests observed red before implementation, now pass. Durable Stop transaction, queue cancellation/receipt ownership, coordinator facade, reload fence and attributed typed-output quarantine implemented. Root transport tests observed two failures (unwanted CLI injection and missing cancellation endpoint), then both passed.
- Initial full suite: 333 tests, one failure, four skips. Failure is the prior End test asserting interrupted; migrated that assertion to stopping plus persisted dispatch ineligibility. Full rerun remains pending. No independent implementation review or publication yet.

- Routing checkpoint: five tests pass after observed red ingress/callback cases. API/MCP chat preserves authenticated dispatch scope; stopped or ambiguous untagged output is retained without routing, while new tagged independent discussion remains available. Delayed callbacks recheck fences before slash commands/mentions. Test-only helper is drafting real mixed-client Stop acceptance and waits for root readiness. Scoped termination and UI are next.

## Final builder checkpoint

350 tests OK/four skips (17.169s). Root mixed Stop check PASS at `session stop integration b_g7l1hb`, local end175.646ms, real unsupported CLI ten-second unresolved, exact late quarantine/no cascades, retained result1, stale termination409 and confirmed owned cleanup. Helper --serve finished PASS after real UI inspection, markers removed, all3 managed workers stopped. Six earlier integration scripts pass. Browser keyboard Stop/confirm/reload passed for a human-only run, and actual unresolved CLI termination offer opened/cancelled; mobile scoped panel390px/scroll390, text contrast9.33:1, inherited body713px overflow left standing. No new design ignores; shared inherited findings preserved. Final independent review remains pending.

Independent same-AGY PASS received:350 tests/four skips, all seven integrations and static checks independently pass on eeb9026. Receipt REVIEW-GEMINI-TICKET-10.md. Local main fast-forward merge verified350 tests/four skips in17.013s. Publication/closure in progress.
