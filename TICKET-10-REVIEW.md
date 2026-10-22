# Ticket #10 independent review briefing

Builder-verified implementation, prepared for frozen same-AGY review. Exact target is supplied in the review request. Base main `3bb435713f0a8dae2ffa85171d85ac20923c79a1`. Scope: issue #10, spec v1.7 SC-1/2 and AT-06. Same Antigravity reviewer owns final independent review and substantive rechecks. Routine human completion gates remain removed under Seth's standing authorization.

## Contract and boundaries

- The coordinator RLock serializes Stop with claim/enqueue/admission. SessionStore commits dispatch ineligibility first, releases its lock, then QueueStore cancels run-owned pending work and marks active claims cancelling. Store locks are never nested; QueueStore never calls SessionStore. HTTP/MCP producers use the coordinated queue facade. Cold claim reconciliation repeats cleanup from persisted fences.
- Cancellation receipts bind actual bearer seat, consumer and dispatch. Requested/delivered/unsupported/unresolved cannot release ownership. Local-ended cancellation requires observed owned local termination. Unsupported CLI work remains held after the ten-second deadline; Stop never automatically kills a persistent CLI.
- API requests execute in owned children with source/request/credential IPC through stdin, bounded output, safe error classification and communicate pipe handling. Persistent supervisors stay alive. Socket-thread interruption was rejected after independently reproduced Windows HTTP/TLS workers remained alive beyond ten seconds. Small echo benchmarks do not predict full request-runner overhead. Remote computation remains unverified.
- Typed late output loads the immutable brief and verifies actual seat identity before quarantine. Accepted attempts remain duplicate conflicts. Ordinary API/MCP chat carries dispatch scope, with run-tagged descendants fenced at enqueue. Delayed callbacks recheck stopped scope before slash commands and routing. Ambiguous untagged output from a stopped seat is visibly unverified and non-routing; human/peer/fresh tagged discussion stays usable.
- Explicit CLI context termination rechecks stable identity and exact launch attempt under manager ownership. The worker owns the client handle; worker exit alone cannot prove that client ended. Missing matching child-exit receipt leaves cancellation unresolved. No arbitrary PID search or room-wide process killing.
- Full runtime adoption/reconciliation, corrected clean restart, result outbox and broad recovery UI remain later scope. No native AI client, external provider, Omarchy or Desktop installation acceptance is claimed.

## Reproduction

```powershell
.venv-windows/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
.venv-windows/Scripts/python.exe tools/verify_session_stop.py
.venv-windows/Scripts/python.exe tools/verify_session_events.py
.venv-windows/Scripts/python.exe tools/verify_review_brief.py
.venv-windows/Scripts/python.exe tools/verify_dispatch_queue.py
.venv-windows/Scripts/python.exe tools/verify_package.py
.venv-windows/Scripts/python.exe tools/verify_api_seat.py
.venv-windows/Scripts/python.exe tools/verify_cli_seat.py
node --check static/sessions.js
node --check static/chat.js
git diff --check
```

Optional mechanism diagnostic: `.venv-windows/Scripts/python.exe tools/probe_http_cancellation.py --long-bound --skip-ipc`. It uses delayed loopback HTTP/TLS, existing OpenSSL when available, scratch data and owned child processes. It is diagnostic evidence, not native/provider acceptance.

## Builder evidence so far

- Helper observed the initial Stop red baseline, then 14 real-store tests pass. Root observed red runner, transport, routing, termination and refresh cases before implementation.
- Final full suite:350 tests OK, four expected Unix/tmux skips (17.169s). Seven runner, five routing, six transport and three termination regressions supplement the helper14. Unproven cleanup remains held, and Start now shares the coordinator with Stop.
- Real mixed-client Stop integration initially failed because security middleware omitted the cancellation receipt route. Root reproduced that failure with real middleware, fixed the exact allowlist entry and passed focused checks. The unchanged integration then passed on helper and root. Root scratch `session stop integration ddiu18g8`: local API end observed194.538ms before provider progress, one accepted prior result retained, CLI unsupported then actual ten-second unresolved, one console injection, quarantine without cascade, fresh tagged discussion, separate peer completion, stale termination409 and confirmed owned termination, durable reload fences.
- Rendered desktop/mobile evidence inspected, panel390/scroll390, text contrast9.33:1. Native keyboard Stop/confirmation on a human-only run and reload preservation pass. Actual CLI termination offer opened/cancelled; HTTP integration performed the confirmed termination. Browser/fixture stopped. Inherited whole-chat width713px remains, with no whole-chat mobile pass. Mechanical detector findings in index.html refer to inherited low contrast, small text, padding and glow. No new suppression was added; the index diff changes only the Stop button label and existing styles remain outside this ticket.

## Review focus

Try Stop versus final/claim/late callback races, cleanup failure followed by cold claim, stale consumer/launch confirmation, interrupted child communication and cancellation after response completion. Inspect every routing producer, including job-scoped MCP chat and direct chat callbacks. Verify that no receipt path claims remote compute termination, and that unresolved local ownership never becomes an automatic retry.

Inspect UI reload visibility, error states, quarantine attribution and exact confirmed termination impact. Check that the published source contains no credentials or runtime histories. Independent PASS/recheck is required before merge, push and issue closure.

Final root Stop rerun after cleanup/Start-race fixes: PASS (`session stop integration b_g7l1hb`), local end175.646ms before provider progress. Final API-seat and session-event regressions PASS; earlier frozen-brief, queue, package and CLI checks PASS. JS syntax, Python compile and whitespace checks PASS. Helper --serve final PASS after browser sentinel, both markers removed and all3 worker receipts stopped.
