# Ticket #4 independent review handoff

Status: implemented and builder-verified; independent review and human completion sign-off pending. Frozen implementation: `f933f59` (resolve with `git rev-parse f933f59`); base `ca50827`. Branch: `codex/ticket-4-cli-seat`. Later documentation-only commits may record review assignment; verify application code equality before executing checks.

## Scope and identity

Issue #4, spec v1.7 PF-2/3/4, AT-02/03, approved `TICKET-4-PLAN.md`. Builder OpenAI Codex (actual backend ID unavailable); test author Traycer Claude Sonnet configured `claude-sonnet-5`, medium (backend identity not independently attested). Independent final reviewer must be a different family from OpenAI and work from the local checkout, not approve builder claims alone. Use `traycer-review` inline and write a kind: review artifact. Record actual exposed reviewer identity, reviewed hash, platform, exact commands/results, findings and remaining limits. Human retains completion sign-off.

## Review map

- `cli_seats.py`, `api_seats.py`: explicit CLI argument contracts and model/reasoning validation; mixed saved packages; native login and no saved credential values; provider-template descriptions and unknown/incompatible modes.
- `api_seat_runtime.py`, `cli_worker.py`: resolved executable/CWD, immutable snapshot, owned console/tmux worker, matching reuse versus explicit restart, missing command and config conflicts, receipt deadlines, exact failed exit, cooperative targeted stop, cleanup after setup/registration failures and server loss.
- `wrapper.py`: validated read/merge, exact-byte backups, atomic replacement, malformed project/trust/settings input, lifetime shared-file locks in compatibility launches. Much of its diff is indentation to protect the entire post-registration lifetime with cleanup, rather than only the final runner call.
- `wrapper_windows.py`, `wrapper_unix.py`: actual child status, watcher after spawn, child cleanup, batch argument restrictions; Unix child-exit receipt independent of attach status and refusal to kill an unknown existing session. Native Unix execution has not been tested.
- `launch_agent.py` and Windows/POSIX compatibility scripts: shared bounded bootstrap, explicit setup, propagated failures and preserved convenience flags. Hermes/OMP aliases require configured supported templates; no new native adapters/YAML installation is claimed.
- Existing preflight endpoints/UI: API/CLI packages, conditional setting support, configuration effects before launch, requested/confirmed distinction, CLI mention-injection readiness without authentication or MCP tool-operation claims.

## Builder evidence and limits

- Final Windows suite **228 tests OK, 4 Unix/tmux skips**. Sonnet's 13 config/Windows regressions and Codex CLI validation/runtime/Unix/failed-worker tests were observed failing before fixes; new tests do not establish native Unix behavior.
- Real Windows integration passed twice: Sonnet final run and Codex rerun strengthened to assert final state failed for child exit 23, unknown authentication and unconfirmed model. Two real Python fake clients in app-owned consoles receive distinct model/reasoning argv and MCP settings/bearer identities. Real console injection reaches only the mentioned seat. Targeted stop keeps peer ready and worker acknowledges; changed settings require restart. No live provider calls.
- An early integration draft wrongly expected literal chat text in the CLI prompt. Existing queue delivery emits a generic retrieval instruction. Test corrected to assert that actual contract; earlier failed run is not acceptance evidence. Queue batching/durable envelopes remain later scope.
- A worker regression exposed failure classification after setting the stop event; fixed using a separate explicit-stop reason. Do not assume unexpected server loss is a successful stop.
- Existing real-wrapper/fake-provider API integration passed. Actual Windows compatibility batch shim with a fake Python command returned exactly **23**. Browser-harness verified save/launch/stop, honest unknown auth/model, and 390px no-overflow; saved screenshot inspected. Test tab/server stopped.
- No native Linux/Omarchy, real CLI/provider compatibility, real login/folder-trust, remote cancellation or full server-restart reconciliation pass is claimed. Stop is local. Optional clients remain unavailable until configured with supported contracts. CLI readiness is console mention injection; actual authenticated MCP operation remains unverified.

## Reproduce

Use existing dependencies; do not install or touch the working Desktop installation. Use isolated scratch and fake clients only. Never print session tokens, MCP bearer config content or real credentials.

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -c "import tempfile,unittest; tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlayground\agentchattr\.audit-tmp'; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not r.wasSuccessful())"
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_cli_seat.py
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_api_seat.py
node --check static/api_seats.js
git diff --check
```

The CLI integration is Windows-only and uses actual console windows/keystrokes; it never starts a live agent. `--serve` keeps an isolated fixture server open for manual browser checks; stop its owned workers and server afterwards. Preserve user browser tabs. No application changes, commits, push, merge, ticket closure or #5 start by the reviewer. Validate each finding against code and a concrete trigger; report PASS, PASS WITH NONBLOCKING NOTES or FAIL with file/line, impact and reproducible evidence. Substantive fixes need a new frozen target and independent recheck.
