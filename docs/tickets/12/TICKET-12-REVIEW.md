# Ticket #12 frozen review briefing

Base: `0d247d5a19631dd2b70c20d2861d76af9144da8d` on main. Frozen implementation: `ebc85aedafbef4c53d70ebdaad37f553ddcbe683`. Later pin commits change documentation only. No #12 publication or independent implementation PASS is claimed here.

The contract is TICKET-12-PLAN.md plus the same AGY's ticket-12-contract-review artifact, including explicit preparation repair (Section 7) and scoped Windows HTTP loop selection (Section 8). Usage and configuration are in STALLED-TURNS.md. Seth's standing autonomy removes routine completion sign-off; the same AGY's independent PASS/recheck remains required before publication.

## Reproduce

```powershell
.\.venv-windows\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
.\.venv-windows\Scripts\python.exe tools/verify_turn_recovery.py
.\.venv-windows\Scripts\python.exe tools/verify_session_stop.py
.\.venv-windows\Scripts\python.exe tools/verify_session_events.py
.\.venv-windows\Scripts\python.exe tools/verify_review_brief.py
.\.venv-windows\Scripts\python.exe tools/verify_dispatch_queue.py
.\.venv-windows\Scripts\python.exe tools/verify_package.py
.\.venv-windows\Scripts\python.exe tools/verify_api_seat.py
.\.venv-windows\Scripts\python.exe tools/verify_cli_seat.py
.\.venv-windows\Scripts\python.exe tools/verify_corrected_restart.py
node --check static/sessions.js
node --check static/chat.js
git diff --check
```

All integrations use isolated data, dynamic loopback ports, local fake providers and fake CLI clients. Optional `verify_turn_recovery.py --serve` pauses at the real generic CLI stall. Inspect/open-and-cancel confirmation only; the script owns confirmed Retry. Write `.audit-tmp/ticket12-browser-stop.txt` promptly to resume assertions and cleanup. Fixture gates allow 900 seconds; browser pause is bounded at 600 seconds.

## Evidence and review targets

- Final backend runs passed all nine scripts across the root run and unchanged helper queue reproduction. Retain one transient queue-fixture failure: both ledger dispatches released and server MCP DELETEs completed, but the second asyncio.run call had not returned to append its reply within30s. An unchanged reproduction passed; exact client context/loop cleanup location is unproven. Bounded phase/stack instrumentation then passed both real replies with all14 phase stamps per dispatch through asyncio.run return and an empty watchdog stack file. Scratch d36n5j7i. No assertion weakening or claimed production fix. Diagnostic instrumentation remains in fake_dispatch_cli.py. Review this limitation explicitly.

- Observed initial red tests covered absent policy/monitoring/Retry interfaces, managed launch and engine wiring. New root regressions covered failure categories, route authority, persistence boundaries, repair, adapter limits and listener configuration. Latest builder suite: **467 tests OK, four expected Unix/tmux skips, 24.883 seconds**.
- Real #12 acceptance verifies a blocked HTTP body ends locally before provider progress, Wait makes no new generation, Retry makes exactly two held-call generations, old authenticated ingress gets 409/quarantine, and prior result/source survive. HTTP503 is `http_error` with code503; empty text is `empty_completion`; failed result delivery makes exactly three submissions and one generation, then `local_delivery_failure`. Suppressing retransmissions of one failed receipt yields `response_timeout` despite live heartbeats. Missing ack and disconnected identity remain distinct.
- Actual Windows generic CLI acceptance proves old retained process-handle exit, new PID/identity/readiness, exact frozen argv/model/reasoning/cwd/MCP despite saved/template drift, one new injection, same source/prior result, `clean_context=False`, separate typed final and transport release, request deduplication and a usable API peer. Preparation-repair failure/exit cases use real stores/manager with process doubles, not native client crash acceptance.
- Earlier --serve failures remain recorded failures: fixture gate mismatch, then real Proactor listener shutdown on WinError64. Installed Python source and CPython issue93821 corroborate the listener-close path. The scoped Selector mitigation passed a real HTTP regression with 128 reset-before-request connections and responsive health after all four batches. Subsequent unchanged --serve passed, all eight workers stopped, markers removed, zero accept failures/WinError64 in that server log. Scratch: `.audit-tmp/turn recovery integration nuuoddgs`.
- Native browser actions exercised Wait without changing attempt, Retry with a fresh attempt on the same turn, stable draft/confirmation through polling, and custom Start limits2/4/.2 on a human turn which stayed waiting beyond machine limits. Desktop1280x900 and phone390x844 screenshots were saved and visually inspected. Recovery panel fits390px with14px functional text; inherited header/composer overflow remains standing. Both owned UI server and test browser stopped. Scoped detector, JS syntax and whitespace checks passed; no new detector ignores.

Attack first-writer admission versus Retry/Stop, durable fences after failed queue cleanup, cold claim eligibility, same request after interrupted preparation, failed prepared process replacement proof, exact confirmation/foreign work, role-policy freezing, preserved context/read isolation and diagnostics without raw payload/credential leakage. Check sequential non-nested store transactions under the engine coordinator lock.

Native AI adapters, external providers, Linux/Omarchy, full runtime adoption, durable saved-answer recovery and six-seat capacity are outside this acceptance. Selector's 512-socket bound is documented; no measured concurrent-socket claim is made.
