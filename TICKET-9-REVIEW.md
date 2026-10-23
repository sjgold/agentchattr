# Ticket #9 final review pack

State: builder verification complete; final independent review pending. No publication or issue closure yet.

Base: `139e2dee00b2d803fbe8e31f5bd680d7f16df728` (published main).
Frozen target: `7777f8173ee9109e8c78120b57ec5f9ec55c5237`. Later review-pin changes are documentation only.
Branch: `codex/ticket-9-restart-reconciliation`.
Contract: `TICKET-9-PLAN.md` and same-AGY `ticket-9-contract-review` Sections13-19.

## Review boundaries

Earlier bounded audits passed09f65639,61cc0be,49432621 and328309a. None is final Ticket9 acceptance. Review the complete base-to-target diff, with particular attention to the final changes after328309a:

- Read-only pre-flight inventory distinguishes unverified/legacy/exited launches from not_started without creating owned attempts or granting process control.
- Interrupted session UI survives refresh, exposes explicit saved Retry/repair and retains frozen request IDs. Rendering never submits recovery. Narrow confirmation scroll keeps both choices visible.
- An unavailable cancellation poll cannot cancel the in-flight model. Positive exact cancellation, local shutdown, heartbeat expiry and provider timeout remain bounded. Admission still obeys durable Stop/superseded fences.
- Real API repair and crash fixtures retain true-worker/model/client/server handles independently of Windows venv launchers. Cleanup does not infer exit from timeout or fabricate parent IPC/exit records.

The checkpoint also preserves an unrelated pre-existing working-tree spec typo (`p2arts` in docs/agentchattr-fork-spec.md). It is not an intended product-contract change; flag separately from recovery behavior.

Core ownership and recovery risks:

1. Exact birth/root/data/server/nonce/fingerprint and authenticated current-boot principal before native adoption. Retained handles, not PID-only actuation. File metadata alone grants no control.
2. OpenProcess87 versus query failures5/31/post-open87; creation-time mismatch versus image mismatch. Genuine retained exit259 is not STILL_ACTIVE.
3. Supervisor versus per-dispatch model-child exit, protocol1 empty-history proof, synchronous spawn failure versus pending/spawned intent, and no orphan replacement shortcut.
4. Coordinator lock with sequential non-nested store transactions, permanent run/attempt fences, exact old dispatch settlement after superseding, replay versus explicit preparation repair.
5. Accepted-event projection without blind dispatch, current unfenced late admission, successor readiness by binding kind, stable timing/Wait decisions and normal newly started runs.

## Builder results

Interpreter: repository `.venv-windows/Scripts/python.exe`, Windows, Python3.14.6.

| Check | Observed result |
| --- | --- |
| Full discovery |630 tests OK,4 expected platform skips,52.101s |
| Final visibility endpoint extension |3 focused tests OK,1.016s; exercises actual get_api_seats response |
| Cancellation probe |4 tests OK,0.712s, including actual held child through3 failed polls and one response |
| Invocation regression |8 tests OK,4.835s |
| JavaScript/diff |node --check static/sessions.js and git diff --check pass |
| Browser |Desktop and390px interrupted refresh, enabled recovery, neutral API confirmation Open/Cancel; root never submitted Retry/repair |

Full discovery command:

```powershell
.\.venv-windows\Scripts\python.exe -m unittest discover -s tests -p test_*.py
```

## Actual process and crash evidence

All providers and console clients below are local fixtures. These are actual managed wrappers/native Windows handles and HTTP/MCP flows, not live AI acceptance.

| Command under tools/ | Evidence and limits |
| --- | --- |
|verify_runtime_birth.py |pd93a60x: actual worker PID differs from venv launcher, birth before readiness, current-boot HTTP proof, hidden native console, no provider calls,2 worker exits |
|verify_runtime_reconnect.py |af9h4iv1: fast IDLE reconnect, HTTP1.794s/proof10.052s, original API/CLI identities and hidden console,0 cold spawns/calls,2 worker/2 server exits |
|verify_api_preparation_repair.py |normal_px1s07_ and servebdalkk0m PASS; serve HTTP1849.664ms, provider3/failed-prepared0, cooperative true-worker exit0, reserved source/results/profile, peer retained,4 worker/2 server exits |
|verify_runtime_crash_matrix.py --case projection |412pggbr: real accepted event/add_once before persistent first-boot backlink fault, cold recovery/3 reconciliations, identical one message UID/ID/content, one event/generation;2 server/1 worker/1 model exits |
|verify_runtime_crash_matrix.py --case held-stop |6ubaumx1: held model/hidden CLI survive first crash, exact queue/consumer/timing/prior source, two unfenced finals without regeneration; second crash preserves Stop and quarantines late MCP final, exact termination;3 server/2 worker/model/client exits |
|verify_runtime_crash_matrix.py --case long-down |dnj0w5b0:22005.117ms offline, both workers/model/native client individually observed exited before restart while provider body withheld; interrupted/ineligible, exact old timing/queue/prior result,0 auto spawns,2 provider calls |

Scratch roots are ignored `.audit-tmp/runtime crash <case> <suffix>` and `.audit-tmp/api preparation repair integration <suffix>`. Matrix `result.json` and `cleanup.json` record per-resource observations; unresolved lists were empty. The combined `--case all` mode has not been run; each case passed separately.

## Failures retained and corrections

- Native adoption full623 setup failed once reading birth.json with PermissionError. Only missing/permission reads now retry within the original10s fixture deadline; malformed JSON still fails. Focused15 and subsequent full623/626/630 pass. No production read semantics weakened.
- API repairntd2s7cy expected revoked-bearer409; actual security middleware returns403. Fixture corrected to403; separately controlled superseded-brief admission still requires409/quarantine. No auth middleware change.
- API repair servebt5stwua counted auxiliary Git version probes as managed Popen. Finalbdalkk0m measured2 managed wrapper launches plus2 auxiliary Git commands. The failed run's exact count was not persisted and remains unknown.
- Held-stopf9xwjrf1 exposed the real cancellation-poll exception bug. Root reproduced an actual held-model failure with the extracted unchanged callback, fixed unknown observations and reran unchanged fixture once to PASS6ubaumx1. This is not a retries-until-green claim.
- Earlier queue fixture SDK return/teardown and file-lock incidents remain in prior ticket records. No claim that Ticket9 eliminates every upstream MCP/Windows failure.

## Independent reproduction request

Apply the same independent-review role and record exact target/base, commands, counts and limits. Run full discovery and the four Ticket9 tools above, with all three matrix cases individually. Recheck prior integrations: verify_turn_recovery.py, verify_corrected_restart.py, verify_session_stop.py, verify_session_events.py, verify_review_brief.py, verify_dispatch_queue.py, verify_package.py, verify_api_seat.py, verify_cli_seat.py and verify_team_capacity.py. They use isolated data/ports/fake providers; no live usage is authorized.

Do not weaken assertions or silently rerun a failure into a PASS. Preserve failed scratch evidence, inspect cause and report a concrete finding. A clear fixture defect may be corrected narrowly and rerun with both results retained. Final verdict must distinguish tested Windows behavior from deferred platforms and scenarios.

## Explicit limits

- Native AI-client compatibility and Linux/Omarchy adoption remain unverified/deferred. POSIX ownership fails closed.
- Local process end does not prove remote provider compute stopped; remote_compute remains unverified.
- No generated-answer outbox or recovery of an answer never durably admitted. Those remain later work.
- Browser evidence covers scoped recovery panels; inherited whole-chat mobile header/composer overflow remains standing.
- Actual Windows absence algorithms also have mocked status cases in units. Those are algorithm evidence, not additional native acceptance runs.
