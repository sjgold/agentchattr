# Ticket #7 independent review briefing

**State:** Builder checks pass; preparing frozen implementation handoff. Final suite293 OK (four platform skips).

Base: main `d16780b`. Approved scope: spec v1.7 SD-3 / SC-5 / AT-21b with autonomous execution amendment. Same Antigravity reviewer independently verifies frozen implementation before reviewed publication; no routine human approval gate.

## Changes and review boundaries

- `dispatch_queue.py`: single atomic ledger with cross-process kernel locking, immutable envelopes and receipt events, stable identity binding, FIFO, exact-ID deduplication/conflict detection, one active owner per seat, idempotent same-consumer claim and retained uncertainty. No queue file truncation or automatic legacy replay.
- `agents.py`: both producer entrypoints persist through the same store. Unknown seats cannot assign work to a future replacement identity. Routing and run/turn/attempt/source metadata remain in each envelope.
- `app.py` and `mcp_bridge.py`: bearer-scoped claim/ack/release/uncertain endpoints; operator-only queue status; cooperative transport-only MCP release. Reject result payloads and wrong owner. Job-bound API reads/replies stay in that job.
- `queue_client.py`, CLI/API wrappers: HTTP-only consumption, per-wrapper consumer identity, CLI in-memory injection guard, no quietness/heartbeat release, serial API execution and release retries without model regeneration in that process. Process exits retain uncertain ownership rather than replaying.
- Small chat details view shows pending/held/failed work and legacy files. It uses existing product colors and text-only DOM rendering. No general chat redesign.

Read the `ticket-7-contract-review` artifact including its source-based follow-up. The initial recommendation to infer CLI prompt readiness was withdrawn: existing activity checkers do not prove completion. Missing cooperative release intentionally blocks the seat. This limitation must remain explicit.

## Reproduction commands

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -m unittest discover -s tests
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_dispatch_queue.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_review_brief.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_package.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_api_seat.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_cli_seat.py
node --check static/chat.js
node --check static/sessions.js
git diff --check
```

Use `.audit-tmp` as tempfile.tempdir if the environment needs workspace-local temporary files. All scripts use isolated ports/data and local fake clients/providers. Never invoke live providers or the working Desktop installation.

## Particular scrutiny

Claim-response loss; partial injection before acknowledgement; two processes contending; atomic write failures preserving old bytes; no stale in-memory ledger writes; duplicate IDs versus identical text; identity-preserving rename and replacement isolation; no accidental session advancement through release; source/credential exclusion from status; preserved legacy bytes; API generation versus delivery failure and process restart limitations.

The #6 tests now claim real durable envelopes instead of reading removed JSONL files. Assertions about frozen context and distinct design phase order remain. Existing fake CLI fixtures cooperate with the new release protocol, and invalid-brief integration injections use durable records. Historical baseline audit scripts remain historical, not current queue acceptance checks.

Explicit completion admission remains #8; restart reconciliation #9; cancellation #10; deadlines/operator recovery and API result outbox remain later scope. No native Linux/Omarchy or real client/provider acceptance is claimed.

## Observed failures and fixes

The real integration receipt-history assertion caught an early cooperative MCP release before wrapper inject returned (scratch `dispatch integration hcx5b6o0`). Root deterministic test failed, then passed after acknowledgement+release became atomic and late ack idempotent. Post-fix normal integration `dispatch integration 31jlf7kp` and browser serve `dispatch integration vyucnang` pass unchanged assertions. Source inspection also led to red regressions for identity-preserving rename retries, invalid routing types, session enqueue persistence failure, and full run/turn/attempt/source metadata alongside brief references.

Rendered operator view screenshots are in ignored `.audit-tmp/ticket7-queue-desktop.png` and `ticket7-queue-390.png`, verified PNG dimensions and inspected. Details width390/scroll390, 12px text contrast9.74:1; keyboard Enter toggles. Inherited page width611 at viewport390 remains, so no full-chat mobile pass. Existing contrast/sizing/font/glow detector findings are unchanged baseline styling, with no new ignores. Queue text was checked separately. Optional `--serve` marker/sentinel supports reproduction; cleanup exits0 after targeted owned-worker stop and retained-work assertions.
