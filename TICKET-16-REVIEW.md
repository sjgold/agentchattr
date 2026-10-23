# Ticket #16 independent review briefing

Base main: `ee52c32dfb24b926d84375dbe4a8fb35558f08c5`. Frozen implementation: `5e6f86ee731ccee0a0e33525d906353cd01f12f8`. Later target pins change documentation only. No independent implementation PASS or publication is claimed yet.

Contract: TICKET-16-PLAN.md plus the same AGY's ticket-16-contract-review artifact. Usage: SESSION-CAPACITY.md. Builder Codex, independent reviewer remains Antigravity agent ec1fbcd1-4a02-410e-9029-e498f67918c8. Routine human gates remain removed; independent review/recheck remains mandatory.

## Reproduction

```powershell
.\.venv-windows\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
.\.venv-windows\Scripts\python.exe tools/verify_team_capacity.py
.\.venv-windows\Scripts\python.exe tools/verify_turn_recovery.py
.\.venv-windows\Scripts\python.exe tools/verify_corrected_restart.py
.\.venv-windows\Scripts\python.exe tools/verify_session_stop.py
.\.venv-windows\Scripts\python.exe tools/verify_session_events.py
.\.venv-windows\Scripts\python.exe tools/verify_review_brief.py
.\.venv-windows\Scripts\python.exe tools/verify_dispatch_queue.py
.\.venv-windows\Scripts\python.exe tools/verify_package.py
.\.venv-windows\Scripts\python.exe tools/verify_api_seat.py
.\.venv-windows\Scripts\python.exe tools/verify_cli_seat.py
node --check static/sessions.js
node --check static/chat.js
git diff --check
```

Optional `verify_team_capacity.py --serve` pauses with a valid proposal before Start. Inspect/open-cancel cast only; the script owns actual Start. Write `.audit-tmp/ticket16-browser-stop.txt` after inspection to resume the unchanged assertions and cleanup. All fixtures use dynamic ports/isolated data and local fake providers.

## Changes and proof

- Final full discovery: **493 tests OK, four expected Unix/tmux skips, 25.909 seconds**. JS syntax and diff whitespace checks pass. Scoped Impeccable detector passes with no new ignores.

- Central strict policy/configuration replaces scattered limits in template validation and coordinator prompts. Backend proposal ingress, direct save, Start and freeze use the same policy. Public response is a plain mapping `{policy, limits_text, execution}`, superseding illustrative flat-JSON/dataclass notation in the critique. No browser-side numeric authority is introduced.
- Accepted runs snapshot policy. Corrected children inherit it; legacy parents remain unchanged and use the ratified legacy fallback. Retry/Continue preserve logical turn count. The engine remains sequential, with no new scheduler or membership pruning.
- Helper20 tests observed the old max4 rejection and unvalidated invalid save red, then passed. Root configuration (2) and route (4) tests cover strict settings, shared public/coordinator text, stale-valid rejection, old-invalid read-only recheck and non-object rejection before cache/persistence. The final malformed-array regression observed AttributeError red before early validation fixed it. Existing frozen-brief numeric tests were moved to the new declared boundaries rather than removed.
- Real normal and --serve team integration PASS. Actual seven saved/launched supervisor identities/models; one coordinator call with exact limits text; six distinct sequential identity/brief/attempt/dispatch contexts; six ordered accepted results and correct own prior context; seventh excluded from review. Five intact over-cap drafts fail Save/Start with exact backend errors and zero extra run/queue/provider work. All seven retained worker process handles signaled exit; server exited. Final browser scratch `.audit-tmp/team capacity integration quhh59wc`.
- Native browser Run opened the six-role cast. Public limits matched exactly,14px functional text. Desktop1280x900 and mobile390x844 screenshots were saved and visually inspected; one scoped flex fix corrected native select overflow. Confirmation showed349px dialog/scroll349 and all six selects inside it. Separate no-client/provider server verified native Check current limits turns an old six-role rejection into a runnable proposal while preserving original metadata. Both test servers/browsers stopped. Inherited whole-page header/composer overflow remains standing, with no whole-app mobile pass/new detector suppression.
- All nine earlier integrations have current-backend passing runs. Preserve the queue fixture failure `equ9v7n8`: ExceptionGroup after call_returned, nested cause uncaptured. One bounded diagnostic rerun `k5shys4z` passed both real MCP replies, with no exception/watchdog output. Full private exception traceback instrumentation is retained; no production fix or assertion weakening is claimed. This is a recurrence of the explicitly nonblocking limitation retained in #12 and requires independent assessment.

Review policy drift at each ingress, invalid template cache/disk mutation, exact upper-bound/one-over behavior, stale draft flags, legacy/corrected inheritance, six distinct scheduled members, package-versus-design separation, actual model-call counts, and failure cleanup ownership. No live external provider, native AI, Linux/Omarchy or capacity above 512 sockets is claimed. Full process adoption remains #9 after the milestone.

## Explicit user amendment after original PASS

Seth requested hidden terminal startup. Managed Windows CLI adds STARTUPINFO STARTF_USESHOWWINDOW/SW_HIDE while retaining CREATE_NEW_CONSOLE/native streams; API worker/model children were already hidden. Unit regression observed missing startupinfo red, then passed. Full494 tests OK/four expected skips25.649s. Actual CLI verifier asserts real console existence and IsWindowVisible=False for initial and restarted clients, plus native input isolation/targeted Stop/peer survival/exact exit23. Turn-recovery and corrected-restart integrations passed unchanged with hidden launches. Compatibility/manual terminals and global settings unchanged. New target requires same-AGY recheck before publication.
