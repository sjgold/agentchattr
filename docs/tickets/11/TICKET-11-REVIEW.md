# Ticket #11 independent review briefing

Builder verification complete; same AGY independent verdict PASS received. Receipt REVIEW-GEMINI-TICKET-11.md; publication follows corrected receipt metadata and merged verification. Base main: `83aa04a8883ec48728b1e8fffbe53a623ab439d1`. Frozen implementation target: `78b418df887596c5f173c0126a3e52d6d144670b`. Subsequent receipt-pin commits change documentation only. Scope is issue #11, spec v1.7 SC-3/AT-07 and the same AGY contract amendments in Sections7/8. Standing authorization removes routine human completion gates. Same AGY remains the final independent reviewer.

## Contract and implementation

- SessionStore atomically links one immutable prepared child with its parent/root. It retains frozen source-independent design/goal/rules and launch provenance, starts empty result/question/continuation context, reserves the channel, and deduplicates raw operator intent. Same-source input is rejected. A truthy stop_id permanently fences a run; prepared ineligibility alone remains temporary.
- Child-only prepare-contexts stages request/binding intent before process effects. It records reassignment history and keeps source, hash and lineage immutable. Retrying the original parent request returns the current edited child. Current-request recovery repairs a missing context backlink without a second launch. Activation freezes final actual launch provenance and identity, rechecks readiness/foreign work, and dispatches once.
- Managed launch provenance freezes allowlisted effective settings and their fingerprint, excluding credential and bearer values. API supervisors reuse matching actual identity/attempt settings. CLI fresh launch requires a strict explicitly verified argument contract, a new nonce/owned process and new readiness identity. A fingerprinted nonce-free launch base prevents later corrections from accumulating old context selectors.
- Live CLI replacement uses exact launch confirmation and the existing worker-owned child termination proof. Missing client-exit evidence stays blocked. Unsupported native adapters remain blocked, regardless of an operator warning acknowledgment. Unresolved old work can execute a correction only through proven termination or an explicit independently clean replacement; unrelated held work prevents reuse.
- Fresh CLI launch metadata binds child run, role and context key before Popen. API/MCP review reads resolve it before readiness/backlink and return current-run-only context, including empty context. Read-only cold metadata fencing does not adopt runtime ownership or certify readiness after a server restart.
- All completion_protocol1 API packets omit supplementary channel chat. Corrected packets retain their own accepted phase results. Operator history remains available; ordinary unrelated discussion remains independent. The existing brief integration's old supplementary-chat assertion was changed to require exclusion.
- Operator-only routes expose correction, child context repair, status/options and activation. The UI retains source drafts during polling, separates prepared from Stop, shows frozen source and original audit history, requires exact CLI confirmation, withholds Start for unsaved role choices, and keeps Stop available during preparation. Delayed parent updates cannot replace a newer child in the channel cache.

## Reproduce

```powershell
.venv-windows/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
.venv-windows/Scripts/python.exe tools/verify_corrected_restart.py
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

Optional `verify_corrected_restart.py --serve` pauses after contexts are ready and before activation. It writes `.audit-tmp/ticket11-browser-url.txt`; write `.audit-tmp/ticket11-browser-stop.txt` after inspection. Browser activation is allowed, and the script verifies idempotent subsequent activation. Fake CLI completion remains gated until the script resumes. No native AI client or external provider is involved.

## Builder evidence

- Full suite: **401 tests OK, four expected Unix/tmux skips, 20.679s**. Test author observed initial missing lineage/launch/repair interfaces and old-context leakage red before implementation. Root fixes addressed same-base identity provenance, repeated context selectors, missing backlink recovery, actual activated launch provenance and monotonic unresolved state. Unit process doubles are distinguished from actual console acceptance.
- Normal corrected integration and two --serve runs pass. It creates a real old API question, operator continuation and accepted answer, then holds the old Windows CLI. After actual ten-second unresolved cancellation it confirms the exact original launch, injects a backlink503 after fresh spawn, retrieves empty real MCP read/resync/job/summary before that backlink, and repairs the same request without a second launch. Original client handle exit, fresh PID/nonce/bearer identity, frozen launch settings despite live drift, exact new Unicode/CRLF source, absence of old context, two accepted new results, independent peer completion and unchanged old audit are verified. Final builder scratch: `.audit-tmp/corrected restart integration ys4sg5te`. All owned worker receipts stopped; markers removed.
- All seven prior integrations pass on the current backend. Stop local end observed98.747ms before provider progress, with remote compute unverified; prior typed result, frozen brief, queue serialization, package reuse and API/CLI identity/lifecycle checks remain passing.
- Actual browser native keyboard activation advanced the mixed correction to its new CLI phase. A separate human-only server verified unchanged-source rejection/draft preservation, edited-source preparation and permanent Stop during preparation after reload, with no invocation/results. Final native role selection disabled Start, explicit preparation reenabled it, and preserved original source/result/continuation were readable. No assertions were weakened for browser QA.
- Desktop1280x900 and mobile390x844 screenshots were saved and inspected. Scoped panel width390/scroll390, functional text14px, text/background contrast about9.3:1. Start moved above collapsible role details. The inherited whole-page header/composer overflow and older shared-page design findings remain standing; no whole-chat mobile pass or new detector suppression is claimed. Scoped detector invocation, JS syntax and whitespace checks pass.

## Review focus and boundaries

Attack raw-intent idempotency after role edits and interrupted bookkeeping; Stop during preparation; stale identities/confirmations; unrelated seat work; activation racing launch changes; and pre-backlink MCP reads. Verify exact new-source context in actual API payload and CLI tool results, including exclusion of old questions/answers, job content and summary. Check second-generation context selection and final actual launch provenance.

Full server restart ownership adoption is #9, stalled turn retry is #12, and file intake is #18. Native adapter verification, external provider usage, login-home changes and Desktop/Omarchy acceptance remain outside scope. Frozen implementation requires the same AGY's independent PASS and substantive recheck before push/merge/closure.
