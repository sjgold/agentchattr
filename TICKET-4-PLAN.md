# Ticket #4: configured CLI seats implementation plan

**Goal:** Launch saved interactive CLI seats with honest settings, preserved configuration and isolated identities (spec v1.7 PF-2/3/4, AT-02/03).

**Approved design:** Seth approved extending the existing interactive wrappers through the Traycer design question on 2026-10-18. Reuse saved package controls and app-owned attempt lifecycle from #3. CLI templates declare supported argument mappings; unsupported selections fail before launch. Fixed settings paths receive lifetime locks, so clients without per-instance configuration reject simultaneous launches rather than sharing identities. Preserve existing login mechanisms; do not copy authentication homes.

**Architecture:** Extend the existing package validator/store and SeatManager to support configured CLI templates, retaining API behavior. Add a managed CLI worker that uses existing injection and platform runners. Keep compatibility wrappers and batch entry points on the same configuration/exit helpers.

**Tech stack:** Existing Python standard library, FastAPI, browser JavaScript, Windows console and POSIX tmux. No dependency installation. Use existing platform environment. Branch `codex/ticket-4-cli-seat`, base `ca50827`.

## Constraints

- No live agents/providers, usage-consuming probes, global-login changes, Desktop installation changes or native Omarchy troubleshooting during verification.
- Launch settings snapshots contain configuration and secret references only; saved edits never mutate active attempts.
- Requested and confirmed model remain separate. CLI confirmation/authentication remain unknown absent explicit evidence.
- No automatic push, merge, ticket closure or next-ticket start. Independent different-family review and Seth's final sign-off remain required.

## Work and dependencies

- [x] 1. Red regressions: malformed JSON/shape preservation, exact backups, replacement failure; Windows child exit 23; duplicate identity/configuration isolation and managed CLI validation. Delegate test writing to a fresh Sonnet agent per Traycer selection guide.
- [x] 2. `wrapper.py`: retain writer signatures, add `_replace_config_bytes(path, content)` with lock/backup/atomic replacement; validate project MCP and Gemini trust files; prevent shared-settings collisions. Resolve callers before edits.
- [x] 3. `wrapper_windows.py`, `wrapper_unix.py`: return actual child status, start watcher after spawn, preserve owned-process cleanup; Unix child receipt independent of tmux attach status; never kill unknown existing sessions.
- [x] 4. `cli_seats.py`: validate declared CLI templates, construct explicit model/reasoning argv without a shell, bounded opt-in version probe, determine fixed configuration resource. `api_seats.py`: same saved package schema, adapter `cli`, provider field selects a configured client template, empty secret_ref uses native login. Existing API-only packages remain valid.
- [x] 5. `api_seat_runtime.py`, `cli_worker.py`: immutable effective CLI config, app-owned console/tmux wrapper, heartbeat receipts and targeted restart/stop; expose executable/startup/version/exit independently of unknown auth/model confirmation. Reject config resource conflicts before spawning.
- [x] 6. `app.py`, `static/api_seats.js`, `static/preflight.html`: reuse authenticated endpoints and saved-package editor for mixed API/CLI seats. Show exact configuration effects before Launch. Never turn an executable/probe into authentication evidence.
- [x] 7. Compatibility launchers: bounded shared bootstrap and preserved return status, explicit setup only. Add generic CLI entry points and documented optional configured aliases where applicable.
- [x] 8. Verify full suite, real fake-CLI argv/config/queue/exit integration and API regression integration; JS syntax and diff checks; inspect pre-flight UI. Record platform limits precisely. Freeze implementation and prepare review briefing.

## Review focus

Windows console ownership and command quoting; malformed settings including nested non-maps; two seats sharing a fixed config; failed spawn after registration; exact child exit versus tmux attach status; server loss and stale receipts; API package compatibility; no credentials in public settings/diagnostics; launch with unsupported flags or unknown template.

## Progress

2026-10-18: Issue #4 scope and Stage A plan read, current wrapper callers surveyed. Verified unsafe JSON parse fallback, swallowed Windows child status, shared settings paths and Unix unknown-session kill in source. No implementation or verification success claimed yet.

2026-10-18 verification: Full Windows suite 228 tests OK, 4 Unix/tmux skips. Real Windows fake-CLI integration passed twice (Sonnet pass, then Codex pass with strengthened assertions): separate argv/model/reasoning, private MCP bearer identities, real console mention delivery to only the addressed seat, targeted stop with worker acknowledgement, mismatch rejection, restart and real child exit 23 with failed state. Existing API integration passed. Browser-harness verified package save, CLI launch to mention-injection ready, requested/confirmed distinction, targeted stop, and 390px no-overflow; saved screenshot inspected. Test browser/server stopped. Actual batch shim propagated 23. Native Unix behavior has mocked lifecycle coverage only; native Linux/Omarchy, real clients, native folder trust and live provider acceptance remain unverified.

Ruling: Keep work in a dedicated branch of the existing checkout, reusing the existing ignored Windows environment. No new worktree/setup or dependency changes were needed; preserve the existing Desktop installation and unrelated work.

Ruling: Extend the existing package storage/schema with adapter=cli rather than create a separate CLI package store. Mixed API/CLI packages use one validation and ownership boundary. Existing API package data remains valid.

Ruling: Generic CLI templates enable only explicitly configured model/reasoning argument mappings. No inferred current model catalogs or flags, and no live installed-client probes during routine tests. Version probes are optional declared contracts and run only on explicit Launch. Clients with no supported identity-injection contract are shown as unavailable until configured.

Ruling: Hermes/OMP aliases route configured templates; native adapters and YAML injection are not implicitly enabled or installed. No native Hermes/OMP compatibility pass is claimed.

Fix receipt: A failing worker regression exposed that setting the stop event before classifying an exit could mislabel failure as stopped. Classification now uses the distinct explicit-stop reason. The integration asserts exit 23 has state failed as well as the exact code.

Next gate: freeze code, independent different-family review, resolve substantive findings and recheck, then Seth's final sign-off. No push or merge authorization.
