---
title: "Independent Review: Ticket #4 Configured CLI Seats (Recheck)"
kind: review
comments: none
---

# Independent Implementation Review: Ticket #4 (Configured CLI Seats)

- **Verdict:** **PASS WITH NONBLOCKING NOTES**
- **Recheck Target (Frozen):** `c7ffb3b18e70c71de76df9d85ef218dca9d5b2d2`
- **Initial Frozen Target:** `f933f59ca415bcbd3a2ac5fb0c2da4afe1c9d7e3`
- **Base Commit:** `ca50827307701cde87097a9de984754044b49416` (`origin/main`)
- **Review Date:** 2026-10-18 (Initial review and substantive fix recheck)
- **Reviewer:** Antigravity (`gemini-3.8-flash`, Google DeepMind family; agent `ec1fbcd1-4a02-410e-9029-e498f67918c8`)
- **Builder:** OpenAI Codex (`codex/ticket-4-cli-seat`, different model family)
- **Test Author:** Anthropic Claude Sonnet (`fcc36344-f0ca-4514-9288-74753be75947`)
- **Claimed Role:** `independent-reviewer` over scope `ticket-4-cli-seat`

## 1. Executive Summary & Attestation

This independent review and substantive fix recheck evaluates the implementation of **Ticket #4: Configured CLI Seats** (spec v1.7 PF-2/3/4 and AT-02/03) in the `agentchattr` repository.

Following the initial review of target `f933f59ca415bcbd3a2ac5fb0c2da4afe1c9d7e3`, a substantive fix was implemented by Codex to address the Windows batch argument delimiter finding (rejecting `,`, `;`, and `=` characters before spawning batch shims to prevent `cmd.exe` argument token splitting). This change was frozen at commit `c7ffb3b18e70c71de76df9d85ef218dca9d5b2d2`.

All test suites and integration verifications were independently rerun on Windows in the repository's `.venv-windows` environment without invoking live providers or modifying the working Desktop installation:

- **Full Test Suite:** 229 tests run, OK (4 expected platform skips on Windows), including the new batch delimiter unit test (3 subtests).
- **Fake-CLI Integration (`tools/verify_cli_seat.py`):** **PASS** across all assertions (distinct model argv, isolated private MCP bearer identities, real console keystroke delivery to mentioned seat only, targeted stop with peer preservation, worker stop acknowledgement, configuration mismatch detection requiring restart, and real child exit status 23).
- **Fake-API Regression Integration (`tools/verify_api_seat.py`):** **PASS** (zero provider calls on launch, secret references resolved in memory only, worker stop acknowledgement).
- **Static Syntax & Formatting:** `node --check static/api_seats.js` and `git diff --check` both passed with exit code 0.

Human final completion sign-off from Seth remains pending; no automated merge, push, or ticket closure is performed.

## 2. Independent Test Execution & Verification

The following commands were run from the repository root:

### A. Focused Substantive Regression

```powershell
.venv-windows/Scripts/python.exe -m unittest tests/test_wrapper_windows_exit.py
```

- **Result:** `Ran 6 tests in 0.005s. OK`.
- **Verified:** `test_batch_model_delimiters_fail_before_spawning_client` confirmed that arguments containing `,`, `;`, or `=` raise `ValueError` before spawn when targeting `.cmd` or `.bat` commands.

### B. Full Application Test Suite

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -c "import tempfile,unittest; tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlayground\agentchattr\.audit-tmp'; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not r.wasSuccessful())"
```

- **Result:** **229 tests run, OK (4 skipped)** in 9.380 seconds.
- **Details:** 4 skips are Unix/tmux platform-specific tests as expected on Windows. 1 test added over initial suite (totaling 229).

### C. Real Fake-CLI Console Integration

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_cli_seat.py
```

- **Result:** **PASS**
- **Captured Output:**
    ```json
    {"result": "PASS", "url": "http://127.0.0.1:58034/preflight", "seats": 2, "distinct_models": true, "distinct_mcp_bearer_identities": true, "unmentioned_seat_isolated": true, "targeted_stop_peer_alive": true, "worker_stop_acknowledged": true, "model_edit_requires_restart": true, "stopped_seat_restart_with_new_model": true, "child_exit_code": 23, "final_state_after_exit_23": "failed"}
    ```
- **Key Verified Behaviors:**
  - Real Windows console injection delivered prompts only to the specifically mentioned agent.
  - Two seats using the same fake client received distinct model arguments and separate MCP bearer tokens/config files.
  - Stopping seat one left seat two alive and responsive in `ready` state.
  - Worker explicitly acknowledged the stop request in its receipt.
  - Modifying package model on an active seat returned 409 Conflict, requiring an explicit restart.
  - Child exit code 23 was accurately captured and surfaced as `child_exit_code: 23` with `state: "failed"`.
  - Saved packages (`api_seats.json`) and runtime attempt snapshots exclude browser session tokens and provider credentials. (Note: per-instance MCP bearer tokens are intentionally written to private runtime identity files and verified as isolated).

### D. Fake-API Regression Integration

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_api_seat.py
```

- **Result:** **PASS** (`{"result": "PASS", "seats": 2, ...}`).

### E. Static Syntax and Formatting

```powershell
node --check static/api_seats.js
git diff --check
```

- **Result:** Both passed cleanly with exit code 0.

## 3. Detailed Scope & Adversarial Analysis

| Focus Area | Spec / Contract | Observed & Verified Implementation | Status |
| --- | --- | --- | --- |
| **Mixed API & CLI Packages** | PF-3, AT-02 | `api_seats.py` extends `validate_seat` to support `adapter in ('openai-compatible', 'cli')`. Packages can mix API and CLI seats seamlessly under a single schema and atomic JSON storage. | **PASS** |
| **CLI Argument Contracts** | PF-3, AT-02 | `cli_seats.py` strictly validates `cli_model_args` and `cli_reasoning_args`. Placeholders must match `{model}` and `{reasoning}` exactly. Models with leading dashes (`-flag`) or control characters are rejected upfront. Unsupported settings raise `SeatError` before execution. | **PASS** |
| **Config Preservation & Backups** | PF-4, AT-03 | `wrapper.py` (`_read_config_object`, `_replace_config_bytes`) validates JSON roots and map structures. Malformed files raise `ValueError` and remain byte-for-byte unchanged. Valid updates write exclusive `.bak` backups before atomic replacement with retry logic for Windows locks. | **PASS** |
| **Shared Path Lifetime Locking** | PF-4, AT-03 | `cli_seats.config_resource` resolves canonical settings file paths. In `cli_worker.py`, fixed settings files acquire a `startup_lock` held for the worker's lifetime. In `SeatManager.launch`, attempting to launch a second seat sharing an active resource is rejected upfront. | **PASS** |
| **Process Ownership & Windows Consoles** | PF-4 | On Windows, CLI workers are spawned with `CREATE_NEW_CONSOLE` without redirecting stdio to DEVNULL. Win32 console input injection (`WriteConsoleInputW`) is initialized only after the process is confirmed alive. Queue watcher is started after spawn. | **PASS** |
| **Real Exit Code vs Tmux/Attach Status** | PF-2 | `wrapper_windows.py` surfaces the actual child `returncode` on exit. `wrapper_unix.py` wraps commands with status capture to an attempt receipt file (`code=$?; printf "%s" "$code" > receipt; exit "$code"`), decoupling true child exit code from tmux attach/detach status. | **PASS** |
| **Preservation of Unknown Unix Sessions** | PF-4 | `wrapper_unix.py` checks `_session_exists` and exits with code 73 if a session already exists, refusing to adopt or kill external or pre-existing tmux sessions. | **PASS** |
| **Unexpected Exit vs Cooperative Stop** | PF-2, PF-4 | `cli_worker.py` separates `stop_reason['requested']` from process termination. An unprompted child exit (e.g., code 23) records `state: 'failed'` and `child_exit_code: 23` rather than misclassifying as a voluntary stop. | **PASS** |
| **Registration & Proxy Cleanup** | PF-4 | `cli_worker.py` ensures deregistration from the local chat server and proxy termination in a comprehensive `finally` block, even when spawn or setup fails. `SeatManager._release` sweeps registry entries matching the attempt base. | **PASS** |
| **Windows Batch Injection & Delimiter Defense** | Security | `wrapper_windows.py:423` inspects commands ending in `.cmd` or `.bat` and explicitly rejects arguments containing shell expansion or delimiter characters (`"& | <>^%!,;= |
| `), preventing c`md.exe` command injection and argument token splitting. | **PASS** |  |  |
| **Shared Compatibility Launchers** | PF-1, PF-4 | `launch_agent.py` routes shared startup, enforces `--setup` for environment creation, checks `shutil.which` for executables, and forwards `--` arguments while preserving child exit codes. | **PASS** |
| **Honest UI Reporting** | PF-2 | Preflight UI clearly labels CLI seats as `Mention injection ready`, explicitly stating that login, MCP tool operation, and model confirmation remain unverified. | **PASS** |

## 4. Unverified Platforms & Boundaries

1. **Native Linux / Omarchy Execution:** Not executed natively; testing remains deferred per user instruction. Unix session handling and child receipt logic have unit test coverage (`test_cli_unix_lifecycle.py`), but native tmux interactive behavior was not verified on a Linux host.
2. **Live External Providers & Clients:** Verification utilized loopback fake servers and deterministic fake CLI fixtures (`tools/fake_cli_seat.py`); no live API credits, external networks, or real proprietary agent installations were invoked.
3. **Downstream Tickets (#6–#10):** Durable turn envelopes and queue batching (#6–#8), full server-restart reconciliation (#9), and remote provider cancellation (#10) remain future milestone scope and are not claimed as implemented in Ticket #4.

## 5. Nonblocking Notes & Observations

### Note 1: Unix Exit Receipt Cleanup on SIGKILL

- **File & Line:** `wrapper_unix.py:237, 273`
- **Context:** `receipt = receipt_dir / (uuid.uuid4().hex + '.txt')` is deleted in the `finally` block via `receipt.unlink(missing_ok=True)`.
- **Observation:** If the outer wrapper process is abruptly killed with `SIGKILL` (signal 9) before reaching `finally`, the small text receipt in `data/client-exits/` will persist.
- **Recommendation:** Nonblocking. The directory and file are lightweight, but adding a sweep of stale receipt files on startup in a future ticket would provide clean maintenance.

### Note 2: Frontend Script Scoping (Carried forward from Ticket #3)

- **File & Line:** `static/api_seats.js:147`
- **Context:** `api_seats.js` calls `detail()`, which is defined in `static/preflight.js:5`.
- **Observation:** Script ordering is maintained by `<script defer>` in `static/preflight.html`, but encapsulated namespacing remains recommended for cleaner modularity.

## 6. Conclusion & Recommendation

The Ticket #4 implementation and substantive fix recheck satisfy all requirements of spec v1.7 PF-2/3/4 and AT-02/03. The architecture cleanly bridges interactive CLI clients into the application-owned seat model with rigorous configuration preservation, collision prevention on shared settings, honest readiness states, accurate child exit propagation, and robust batch argument validation.

**Recommendation:** **PASS WITH NONBLOCKING NOTES**. Ready for Seth's human final sign-off.
