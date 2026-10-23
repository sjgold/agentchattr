# Ticket #9: reconcile interrupted runs after server restart

**State:** Proposal for same-AGY contract critique, before tests or implementation. Base main `139e2dee00b2d803fbe8e31f5bd680d7f16df728`. First milestone (#1-8, #10-12, #16) is published and closed. Builder Codex; independent reviewer remains Antigravity agent ec1fbcd1-4a02-410e-9029-e498f67918c8. Seth's standing autonomous authorization removes routine human gates. Preserve the requested hidden managed terminal startup.

## Required outcome and current evidence

Approved issue#9/specification v1.7 SC-4/AT-08 require honest restart reconciliation, no blind duplicate dispatch, explicit new-attempt Retry and permanent Stop protection. Completed results/source/design/policy and recovery choices survive. Do not automatically regenerate or claim a recoverable saved answer before #13.

Current SeatManager starts with an empty attempts map; it cannot own an old worker merely because config.json/receipt.json exists. Registry restores old identities as reclaimable, and a valid token may reactivate them, but token recovery alone proves neither an OS process handle nor safe termination authority. Receipts currently bind attempt/state/readiness but lack durable worker process birth identity. Engine.resume_active_sessions only reconciles Stop and accepted-event projection. Queue claims already retain consumer identity and permanent run/attempt fences. Graceful shutdown intentionally stops owned workers; a crash can leave them alive until their existing heartbeat deadline.

## Approaches

| Approach | Consequence |
| --- | --- |
| Mark every cold run uncertain and never inspect live owners | Safe fallback, but cannot restore verified surviving workers or usable lifecycle control |
| Adopt by PID, registry name, or a recent ready receipt | Unsafe under PID/name reuse or stale/copied state; rejected |
| Reconcile immutable launch metadata, OS birth identity and fresh authenticated adapter evidence (recommended) | Restores provable owners while preserving visible interruption for everything uncertain |

No global process-name search, taskkill tree, external client control, new storage backend or mandatory dependency install is proposed.

## Contract choices requiring critique

### 1. Startup fence and reconciliation transaction

Introduce a fresh server boot/incarnation ID and durable per-run restart-recovery evidence. Initialize eligibility before HTTP/MCP dispatcher loops can claim work. Engine coordinator RLock still spans sequential non-nested SessionStore then QueueStore operations. Persisted Stop/superseded fences win immediately, regardless of receipts or heartbeat.

Never re-enqueue an existing waiting attempt simply because the server started. Preserve exact queue envelope/consumer and accepted-result journal. An uncertain owner becomes visible interruption with a reason and retained checkpoint; proposed state is `interrupted`, with explicit eligibility separate from permanent stop_id. Settle compatibility with #12's recovery routes and existing channel reservation. Duplicate startup/reconciliation calls must not allocate another attempt, enqueue work or renew deadlines.

### 2. Distinct identity, process ownership and completion authority

Persist launch ownership metadata under the existing runtime attempt directory: immutable launch key/attempt/nonce, root+data server identity, frozen effective configuration fingerprint and OS process birth identity. Establish the worker's actual PID/birth/executable independently of a Windows venv launcher shim PID. Worker receipts bind their own identity and, where relevant, owned child PID/birth/exit evidence. No credentials in ownership records/argv/logs.

Before controlling an old worker, validate its exact birth identity through an OS handle plus matching launch metadata and fresh authenticated adapter report bound to the new boot. A stale receipt, changed PID birth, replaced registry identity or foreign root/data/config fails closed. Keep a retained verified process handle so PID reuse cannot redirect a later stop. No automatic process kill during reconciliation.

Separate completion admission from OS termination authority. Open question: retain #12's current unfenced typed-final authority when the same authenticated immutable brief/attempt returns after restart, even if process adoption remains unverified, or hold admission pending fresh adapter proof? Prefer preserving existing first-writer admission semantics without inventing a hidden operator-held result store, while blocking any successor dispatch that lacks proven readiness. The reviewer must settle this boundary explicitly.

### 3. Bounded process adapter and platform honesty

Recommend a small owned-process handle interface for adopted processes, with poll/wait/close and explicitly authorized termination, rather than faking Popen or inferring exit from receipt age. Windows can use OpenProcess/GetProcessTimes/QueryFullProcessImageName and retained handles; verify actual worker versus venv shim identity. POSIX support must use equally stable process identity/handles where available and fail visibly closed otherwise. Native Linux/Omarchy acceptance remains deferred; do not claim it from Windows mocks.

Settle whether a worker authenticated reconciliation handshake suffices for dispatch continuity while process control stays unavailable, and how existing runtimes lacking new ownership metadata are displayed. Legacy runtime files must remain intact and readable. Unprovable old processes must never be adopted or killed by guesswork.

### 4. Explicit Retry, Stop and pending preparation after a crash

Reuse #12's durable same-turn Retry request/reserved generation and exact-dispatch cancellation. Preserve frozen source, model/launch provenance, capacity/timing policy and prior results. Retry first fences the old attempt; late results lose authority. API local-end acknowledgement and CLI exact confirmed termination still require genuine proof, never an expired lease.

Interrupted preparation must repair/reuse the same request/context reservation when provable. Starting/failed contexts may not silently respawn on startup. Exact explicit repair remains required for failed prepared contexts. Persisted Stop during waiting/preparation/retry remains permanently ineligible across repeated crashes. Unknown/dead-without-child-proof ownership stays visibly blocked; no broad cleanup.

### 5. Deadlines, projection and operator surface

Keep original acknowledgement/response deadlines and Wait decisions; startup and heartbeat cannot grant fresh time. Human turns, questions, explicit pauses, prepared corrected children and completed runs retain their distinct semantics. Project accepted content idempotently before any eligible successor work, with no duplicate message/admission. A lost result delivery without a durable outbox remains unrecoverable in #9.

Expose restored/verified, interrupted/unverified, exited and blocked states with exact seat/phase/last receipt and restart reason. Reuse Wait/Retry/Stop where safe, with explicit ownership confirmation for CLI control. A surviving hidden console must remain hidden; restarting the server must not spawn another console or model call.

## Bounded proof plan after contract settlement

1. Existing helper authors observed-red store/coordinator tests for startup gating, all run states, immutable checkpoints/deadlines, Stop/superseded precedence, replay prohibition, projection idempotence and new-attempt Retry.
2. Root and helper separately test process birth/identity validation, PID reuse/foreign root/stale receipts, missing metadata, exact confirmation, wrapper-shim distinction, interrupted preparation and failed atomic bookkeeping. Faults retain last durable state and never control an unrelated process.
3. Actual isolated fake-provider/Windows CLI integration retains handles to exact server/workers, crashes only the owned server (not its process tree), restarts the same port/data, and observes genuine reconnect/ownership receipts. Verify no new provider call/injection during reconciliation, no duplicate accepted result/phase advancement, explicit Retry with new IDs/old409, preserved accepted work, repeated-crash idempotence and permanent Stop after cold restart. Parent fixture provider survives server death independently.
4. Cover both surviving and genuinely exited workers; never fabricate local-exit proof. Use bounded crash/restart windows relative to current15s heartbeat expiry and report which case was exercised. Cleanup only retained owned handles/verified attempts. No live provider/native AI calls.
5. Verify UI/refresh, full suite, affected integrations, JS/diff and same-AGY frozen independent review/recheck. No implementation begins until these consequential ownership/authority choices are settled. Escalate a reproduced unresolved correctness dispute with the specified Astra evidence pack rather than silently weakening proof.
