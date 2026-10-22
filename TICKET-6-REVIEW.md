# Ticket #6 independent review briefing

Frozen target: `e69442dac1da3e464c64e25413037c5ae41219ec`. Base: `75bf639ccb0937ad7b4021e6fda6dd6cab443eb0`. Branch `codex/ticket-6-frozen-brief`. Later commits may record review assignment only; verify runtime/test equality against the frozen target.

Same AGY reviewer/tester remains mandatory. Read `AGENTS.md`, `STATUS.md`, `TICKET-6-PLAN.md`, `FROZEN-REVIEWS.md` and spec v1.7 SD-1/2, AT-04/10. Seth's 2026-10-22 authorization removes routine human approval gates; independent review/recheck is still required. On PASS the parent may merge/push/close and proceed to #7. No live providers/clients, installs, Desktop/global credential changes or native Omarchy testing authorized.

## Code map and critical boundaries

- `review_brief.py`: UTF-8 bounds, exact source snapshot and revisions, frozen design/rules/run identity, per-turn/attempt metadata, atomic immutable brief files, schema/source-revision checks, seat identity scoped retrieval and shared API message formatting. User source is separate untrusted JSON data, not system instructions or execution.
- `session_store.py`, `session_engine.py`: Start freezes template/cast/task/source/rules; getters/callbacks avoid mutable snapshot aliases; every phase/expected-agent/enrichment lookup uses the frozen design. Previous result message IDs provide context. Preserve original dissent instructions. Atomic session persistence rolls back a failed new record. Existing active legacy sessions keep their previous behavior.
- `agents.py`, `wrapper.py`, `wrapper_api.py`: typed brief references in queues. CLI injects a short instruction to retrieve the same brief and does not append live role/rule overrides. API fetches the exact scoped brief, includes explicit role/phase/task/rules/source/prior results, and does not make a provider call on invalid/missing/wrong-seat retrieval. Recent chat is supplementary, not the source. API custom legacy queue coalescing and crash-loss remain for #7; do not claim queue durability or full completion/cancellation guarantees here.
- `app.py`, `run.py`, `mcp_bridge.py`: Start validation and scoped HTTP/MCP `chat_review_brief`. Agent bearer auth allowed only for the new scoped read path; other agent identity cannot obtain the brief. Browser operator read requires session token. Actual MCP context uses authenticated instance, never caller-supplied sender. MCP HTTP transport exercised; SSE/native client behavior unverified.
- `static/sessions.js/css`: pasted source in normal and draft Start dialogs, retained inputs on rejection, successful Start closes dialog. Ask/Design remains in chat. Added scoped hidden-step styling because the inherited dialog step classes had no hide rule; no unrelated global header redesign.

## Builder verification

- Final full Windows suite **266 tests OK, four Unix/tmux skips**. Helper engine interface tests and root missing-route tests were observed failing before implementation; not every helper case was red first because helper/store edits arrived during test writing. Malformed saved-brief tests failed on invalid root/missing source shape before the clean rejection fix. Two different coordinator designs execute their own frozen role/phase order through real engine callbacks after live template changes.
- `tools/verify_review_brief.py` passed by test author and builder (final root rerun after schema hardening). Real isolated app + one local fake-provider request + actual Windows fake CLI console. Configured API model preserved, exact Unicode/CRLF/mentions/code source in separate data message, long goal and frozen rules. After 30 system messages and live template/rule mutation, original second-phase CLI editor receives its scoped ID and retrieves via **actual MCP Streamable HTTP** using installed SDK and injected bearer identity. HTTP/MCP envelopes agree; run/design/input revisions match, prior API result included. Wrong-seat403; missing/malformed brief404; invalid typed API references cause no additional provider calls; oversized Start400 creates no run/model call; source sentinel absent.
- Existing package integration passed, zero provider calls or sessions created by package handoff. JavaScript syntax and whitespace checks pass. Test author fixture initially assumed `url`; it was corrected to support injected `httpUrl` and the run passed. No production failure was counted as a pass.
- Browser: isolated human-only server, no agents/providers. Source field, oversized Start400 retaining 524289 bytes and goal, then valid Start200 with exact Unicode persisted and modal closed. Existing template/cast step visibility issue fixed and checked. Exact 390px viewport: dialog width351 fits without internal overflow; PNG saved/dimensions verified/visually inspected. Existing background chat header overflows to479px, so whole-chat mobile compliance is not claimed. Fixture session ended; isolated browser/server stopped.
- Source file intake/upload belongs to #18; this ticket handles pasted plain text/code as data. Numeric capacity policy stays until #16. Full turn envelope persistence/outbox, explicit final-result admission, restart reconciliation and cancellation remain #7-10. Normal participant chat can still advance a run under the existing engine policy until #8. No live provider/client, native Linux/Omarchy, remote cancellation or perfect model prompt-injection compliance claims.

## Independent commands

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -c "import tempfile,unittest; tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlayground\agentchattr\.audit-tmp'; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not r.wasSuccessful())"
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_review_brief.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_package.py
node --check static/sessions.js
git diff --check
```

Use only existing dependencies and isolated fake fixtures. Clean your owned processes; do not print MCP tokens or source containing secrets. No application/tests/status edits, commits, pushes, issue closures or #7 implementation in reviewer lane.

Review every changed line/caller. Probe immutable snapshots versus later edits, cast/schema failures, stale/replaced/spoofed identities, missing/corrupt brief files, atomic failures, validation before dispatch, input byte limits, source/data separation, prior-result retention beyond recent chat, API error without silent model fallback, and UI draft retention. Validate findings with concrete triggers; distinguish source reasoning from executed evidence.

Write kind: review artifact under this epic at `artifacts/ticket-6-independent-review/index.md`, comments: none. Report PASS / PASS WITH NONBLOCKING NOTES / FAIL, exact hashes from Git, actual exposed identity, commands/results, priority/file/line/trigger/impact/correction and unverified limits. Return artifact path/verdict/findings to parent with the request responseId. Substantive fixes require a new freeze and same-AGY recheck. No routine human completion gate is pending.
