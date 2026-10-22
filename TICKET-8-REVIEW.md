# Ticket #8 independent review briefing

Builder verification is complete; frozen target will be recorded after the final local commit. Base main: `0029971`. Scope: issue #8, spec v1.7 SD-3 / AT-05 and the autonomous execution amendment. Same Antigravity reviewer independently verifies the implementation and substantive fixes. No routine human completion gate.

## Important behavior and boundaries

- Session chat/status/choice messages and transport release cannot advance a turn. New sessions persist a frozen participant kind and stable identity, plus a bound invocation containing brief, run, turn, attempt, source and dispatch references. Agent disconnect cannot turn the role into a human; an identity-preserving rename still works. Human briefs are operator-only, including later phases after name reuse.
- SessionStore commits accepted text, consumed attempt and phase disposition in one atomic write, with in-memory rollback on failure. A final advances once; a question enters awaiting_input. Compact MCP and scoped HTTP events load immutable IDs and verify every identity plus actual caller provenance. Duplicate/stale submissions cannot consume another attempt.
- Accepted events project through MessageStore.add_once with stable UID and atomic log replacement. Recovery repairs chat-before-backlink failures before successor dispatch. Additive UI metadata does not invalidate the immutable event content check. Operator answers are also durably projected, while retaining their separate continuation provenance.
- API session responses require strict final/question JSON. Only complete optional markdown fences are unwrapped; duplicate keys, unknown fields, plain status text and empty content have no final fallback. Submission retries retain the same event ID and never call the provider again. This is not a durable worker result outbox.
- Operator-only Continue/human-result/Resume/display-repair endpoints have separate authority from agent bearer events. Continue fences the previous attempt and preserves source/design. Resume restores the same held invocation without redispatch. UI retains answer drafts through live updates and validation failure.
- Legacy history is preserved without invented invocation provenance. Stop cancellation, full restart adoption/reconciliation, deadlines, generation retry/recovery and broader capacity remain later scope. Existing typed result admission rejects interrupted sessions, but no provider-cancellation claim is made.

## Reproduction

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -m unittest discover -s tests
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_session_events.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_review_brief.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_dispatch_queue.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_package.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_api_seat.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_cli_seat.py
node --check static/sessions.js
node --check static/chat.js
git diff --check
```

Use `.audit-tmp` as tempfile.tempdir if required by the environment. All integration scripts launch isolated servers with dynamic ports and local fake providers/clients. Do not call live providers or alter the working Desktop installation.

## Builder evidence

- Final full suite: **315 tests OK, four expected Unix/tmux skips**, 13.175s. Core helper captured genuine red evidence before implementation: ordinary status advanced a phase, and explicit admission/protocol interfaces were absent. Root projection and scoped HTTP/MCP regressions were also observed red before implementation.
- Final real mixed-session check: three local provider calls (question, continued final, separate malformed response), three admitted main-run events (question/API final/CLI MCP final), explicit Continue required, fresh attempt fenced, wrong-seat403, duplicate/stale409, malformed API no admission, exact source retained and source unexecuted. Final scratch `session events integration 5qskzrqt`.
- Frozen-brief/MCP, durable-dispatch/failure, package, API-seat and CLI-seat integrations all PASS. Distinct source/context and queue guarantees remain checked; CLI exit23 still propagates. Latest scratch references: `review brief integration iufd2jbx`, `dispatch integration l7dcsai6`, `package integration s0uw0gib`.
- Browser checks used the isolated cached chrome-devtools-axi runtime after the known normal-Chrome approval limitation. Actual form rejected 524289 bytes with400 and retained the complete draft through a status refresh. Native textarea fill plus keyboard Enter submitted a valid Continue with200. A separate human-role run displayed its frozen source/goal/prior result and completed through two actual human-result submissions200/200. Serve-mode cleanup and remaining scripted assertions exited0.
- Inspected initial390px question screenshot; answer panel width390/scroll390, input width350 at14px. Fixed scoped session-strip wrapping after seeing overlap. Confirmation DOM reported no strip overlap and height72. Confirmation screenshots were saved but obscured by the inherited Guide overlay, so final strip visual confirmation is not claimed. Broader header/composer overflow remains inherited; no whole-chat mobile pass.
- Root also observed/fixed regressions for empty event IDs, duplicate discriminator keys, lost output highlighting, human-name source leakage across later phases, disconnected agent-to-human coercion, rename continuation/status, and additive metadata during projection repair. No tests were weakened to keep implicit chat completion.
- `impeccable detect static/sessions.css --json` returned no findings. No new detector suppressions were added for #8. No native Linux/Omarchy, real AI CLI compliance or external-provider acceptance is claimed.

## Review focus

Check the admission transaction and rollback first, then exact ownership/provenance and stale-attempt fences. Examine both sides of the chat projection/backlink crash window, output metadata, continuation projection and successor scheduling. Review the snapshot of human/agent kind and stable identity across disconnect, rename and name reuse. Confirm that agent bearer permission cannot reach operator routes, and that accepted duplicates are distinguished from failed/stale submissions without leaking content.

Finally inspect API error categories, ordinary-chat compatibility, UI draft preservation and explicit Resume/Continue semantics. Atomic full-log replacement for accepted projection trades additional I/O for consistency; large-history performance has not been benchmarked. Full restart reconciliation and pre-submission worker answer recovery remain outside this ticket.

On independent PASS, the parent may merge, push and close under standing authorization, then follow the recorded first-milestone dependency order. Substantive fixes require your recheck.
