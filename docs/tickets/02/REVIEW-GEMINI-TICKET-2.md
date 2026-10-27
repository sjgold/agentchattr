# Ticket #2 independent review receipt

Received from Seth on 2026-10-12. Verdict: **PASS WITH NONBLOCKING NOTES**.

- Frozen implementation: `3bf7da0484f7dbe308076803efa4e7ff7aff6222`; base: `4bc8a3a96f1c26c73e9694a1372c4d469b4b11d9`.
- Reviewer self-identifies as **Google / Gemini 3.8 Flash (Antigravity)**, distinct from the OpenAI Codex builder. This is the supplied reviewer identity; a backend API ID is not independently attested by this receipt.
- Reviewer reports independent Windows 11 execution of the 173-test suite (4 skips), real-server integration, JavaScript/diff checks, Windows/Git Bash passive entry points, and both shortcut installers including collision refusal. The supplied report below is the evidence; Codex did not rerun these checks while recording this documentation-only receipt.
- Nonblocking disposition: retain the Windows error pause and document direct Python invocation for automation; leave the generic terminal icon until release packaging (#23); preserve in-page network failure/retry as an unverified browser interaction. No application code revisions requested or made, so the reviewed code target is unchanged.
- Linux/Omarchy remains unverified. Seth deferred Windows-hosted testing because of mounted filesystem issues and explicitly does not want troubleshooting now. Dual boot is deferred while four lanes are active.
- Seth gave final sign-off and explicitly authorized push/merge on 2026-10-12 ("im good with it push merge"). The implementation is merged/published on origin/main, and GitHub issue #2 is confirmed closed. `STATUS.md` records the next action; this does not authorize dependent implementation.

## Supplied review

The text below is preserved as supplied, including its wrapped command table. The wrapped suite command appears to omit a path separator before `.audit-tmp`; its exact runnable form is in `TICKET-2-REVIEW.md`. Do not silently reconstruct this as a raw execution log.

   Ticket #2 Implementation Review

  Verdict: PASS WITH NONBLOCKING NOTES
  Frozen Target: 3bf7da0484f7dbe308076803efa4e7ff7aff6222 on codex/ticket-2-preflight
  Base Target: 4bc8a3a96f1c26c73e9694a1372c4d469b4b11d9
  Reviewer Identity: Google / Gemini 3.8 Flash (Antigravity) — distinct model family from the OpenAI Codex builder.
  ──────
  ## 1. Independently Executed Verification

  All checks were executed independently on Windows 11 (C:\Users\SJG\Documents\CodePlayground\agentchattr):

   Check / Command                                         │ Exi… │ Result Summary
  ─────────────────────────────────────────────────────────┼──────┼────────────────────────────────────────────────────
   .venv-windows/Scripts/python.exe -X utf8 -B -c "import  │ 0    │ 173 tests run, OK (4 platform skips) in 7.787s.
   tempfile,unittest;                                      │      │
   tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlaygroun │     │
   d\agentchattr.audit-tmp';                               │    │
   result=unittest.TextTestRunner(verbosity=1).run(unittes │    │
   t.defaultTestLoader.discover('tests')); raise           │    │
   SystemExit(not result.wasSuccessful())"                 │    │
   .venv-windows/Scripts/python.exe -X utf8 -B             │ 0  │ {"result": "PASS", "url":
   tools/verify_preflight.py                               │    │ "http://127.0.0.1:49313/preflight", "owned_servers":
                                                           │    │ 1, "separate_relaunches": 2, "agents_checked": 10,
                                                           │    │ "authentication_enforced": true,
                                                           │    │ "session_token_logged": false}
   node --check static/preflight.js                        │ 0  │ Syntax check clean.
   git diff --check                                        │ 0  │ No whitespace errors, clean diff.
   4bc8a3a96f1c26c73e9694a1372c4d469b4b11d9                │    │
   3bf7da0484f7dbe308076803efa4e7ff7aff6222                │    │
   cmd.exe /c "windows\start.bat --check"                  │ 0  │ Passive JSON snapshot emitted: 10 agents, server
                                                           │    │ absent, environment ready.
   bash -c "sh macos-linux/start.sh --check"               │ 0  │ Passive JSON snapshot emitted matching Windows
   windows/install_shortcut.ps1 (in isolated .audit-tmp) │ 0  │ Created Agentchattr.lnk; second invocation refused
                                                         │ (i │ existing .lnk collision with exit code 1.
                                                         │ ni │
                                                         │ t) │
                                                         │ /  │
                                                         │ 1  │
                                                         │ (c │
                                                         │ ol │
                                                         │ li │
                                                         │ si │
                                                         │ on │
                                                         │ )  │
   macos-linux/install_shortcut.py (in isolated .audit-  │ 0  │ Created agentchattr.desktop; second invocation refused
   tmp)                                                  │ (i │ existing .desktop collision with exit code 1.
                                                         │ ni │
                                                         │ t) │
                                                         │ /  │
                                                         │ 1  │
                                                         │ (c │
                                                         │ ol │
                                                         │ li │
                                                         │ si │
                                                         │ on │
                                                         │ )  │
  ──────
  ## 2. Source Review & Contract Verification

  ### A. Duplicate Launch & Lock Bounds

  • launcher.py:79-110: startup_lock uses OS kernel locks (msvcrt.locking on Windows, fcntl.flock on Unix) on .
  launcher/startup.lock. Crashing or SIGKILL releases the lock automatically via the OS file table without leaving
  dangling state or needing file deletion. Acquisition retries are bounded by deadline (time.monotonic() + timeout).
  • launcher.py:181-220: ensure_server checks probe_health under the lock before doing anything else. If an existing
  matching server is running (e.g., started by an earlier concurrent launch), it returns immediately with url +
  '/preflight' without spawning or modifying dependencies.

  ### B. Listener Identity & Malformed Responses

  • launcher.py:29-37 & app.py:267-272: instance_identity hashes normalized root, data directory, upload directory,
  host, port, and MCP configuration. /api/health returns this identity along with app protocol and readiness state.
  • launcher.py:55-77: probe_health uses ProxyHandler({}) (bypassing corporate/system HTTP proxies) and NoRedirect().
  Responses with non-200 status, invalid JSON, or non-matching identity return 'foreign'. Non-HTTP listeners or stalls
  return 'foreign' via socket connect fallback, while closed ports return 'absent'.

  ### C. Foreign-Process Preservation & Child Cleanup

  • launcher.py:193-196: If state == 'foreign', ensure_server raises LaunchError with actionable messaging and never
  touches the foreign process.
  • launcher.py:170-179: stop_owned_child only acts on the specific subprocess.Popen handle created by spawn_server. If
  startup fails or readiness times out, only the child spawned by that launcher process is terminated/killed.

  ### D. Explicit Setup & Environment Isolation

  • launcher.py:112-155: Platform environments are strictly partitioned into .venv-windows, .venv-linux, and .venv-
  macos. The existing .venv is never modified or deleted.
  • Passive --check does not create directories or install packages. Environment setup requires --setup or typing SETUP
  in an interactive TTY.
  • In ensure_server, when setup=True, the readiness deadline is reset (deadline = time.monotonic() + timeout) so
  package installation time does not consume the server startup timeout budget.

  ### E. Session-Token Security & Log Sanitation

  • run.py:160-167: print(f"\n Session token: {session_token}\n") was removed. The token is never written to .
  launcher/server.log.
  • run.py:101-113: The token is injected into /preflight HTML with Cache-Control: no-store. Same-origin isolation
  prevents cross-origin exfiltration.
  • app.py:275-278: /api/preflight requires the x-session-token header via security middleware, returning 403 when
  unauthenticated.

  ### F. Honest Detection (PF-2)

  • launcher.py:222-234: Resolves CLI executables via shutil.which. No commands or models are executed. Reports
  version: null, startup_checked: false, authentication: "unknown", adapter_connected: "unknown", ready: false.
  • preflight.html & preflight.js: States clearly that checks only find executables, without implying readiness or
  authentication.

  ### G. Shell Scripting & Quoting

  • start.bat: Uses cd /d "%~dp0..", forwards %*, captures %ERRORLEVEL%, and propagates exit /b %launch_code%.
  • install_shortcut.ps1: Arguments formatted as cmd /d /c "" for paths with spaces. Refuses collision with existing .
  lnk.
  • start.sh: Uses POSIX CDPATH= cd -- ..., detects python3/python, and execs launcher.py with "$@".
  • install_shortcut.py: desktop_quote escapes %, \, ", `, and $ per XDG Desktop Entry specifications, uses exclusive
  mode 'x', and sets Terminal=true.
  ──────
  ## 3. Nonblocking Notes

  1. Windows Batch Error Pause:
  start.bat:17-20: On non-zero exit, start.bat executes pause. This is helpful for users double-clicking a shortcut
  from Explorer so the window doesn't disappear before they read the error. For automated callers, launcher.py should
  be invoked directly (as documented in LAUNCHER.md).
  2. Desktop Entry Icon Reference:
  install_shortcut.py:31: Uses generic standard icon Icon=utilities-terminal. A product icon (e.g. static/logo.png) can
  be wired in Ticket #23 (release packaging).
  3. In-Page Fetch Disconnection UI:
  preflight.js:43-47: Network errors correctly display failure messages, clear the card grid, and re-enable the refresh
  button. While offline emulation was tested by the builder, interactive mid-flight retry was not exercised in a live
  browser session.
  ──────
  ## 4. Unverified Platforms

  • Native Linux / Omarchy Execution:
  Shell syntax, .desktop file generation, and launcher --check were validated on Windows (using native PowerShell/CMD
  and Git Bash). Native Omarchy execution (including Wayland, system terminal spawning from .desktop, and Linux-native
  browser launch) remains unverified until executed on an Omarchy host per OMARCHY-TEST-PLAN.md.
  ──────
  ## 5. Review Conclusion

  The changes on 3bf7da0484f7dbe308076803efa4e7ff7aff6222 satisfy the requirements of Ticket #2 (PF-1, PF-2, AT-01). No
  defects require blocking or code revision.

  Per the return contract, ticket #2 remains open pending Seth's final sign-off; dependent tickets (#3/#4) should not
  be automatically started.`