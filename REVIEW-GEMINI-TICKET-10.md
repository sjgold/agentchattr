# Ticket #10 independent review receipt

Received 2026-10-22 from the same Antigravity reviewer, configured gemini-3.8-flash (Google family), agent ec1fbcd1-4a02-410e-9029-e498f67918c8. Exact backend identity is not independently attested. This is the reviewer-supplied report, with its source-accuracy wording corrections confirmed by the reviewer. Verdict PASS; no application changes requested.

# Ticket #10 Independent Implementation Review: Stop, Scoped Invalidation, and Cancellation Evidence

## 1. Executive Summary & Review Verdict

- **Review Verdict:** **PASS**
- **Reviewer:** Antigravity (`gemini-3.8-flash`, agent `ec1fbcd1-4a02-410e-9029-e498f67918c8`)
- **Role:** Claimed role `independent-reviewer` over `subsequent-tickets-review` (claimId: `3b196d4b-c9fc-49f6-b360-8ecc4a48a8f2`)
- **Base Main Commit:** `3bb435713f0a8dae2ffa85171d85ac20923c79a1`
- **Frozen Implementation Target:** `eeb90269e92d89d294550d029e1861617caf07bb`
- **Documentation Pin HEAD:** `06872cfd0aaffa162be5e8f7d906237ff4151dc1` (`git diff` between frozen and HEAD confirms strictly documentation pin files: `AUTONOMOUS-RUN.md`, `STATUS.md`, `TICKET-10-REVIEW.md`)
- **Working Tree State:** Clean (no uncommitted or modified files)

The implementation of Ticket #10 satisfies all specification requirements (spec v1.7 SC-1/2, AT-06, `STOPPING-REVIEWS.md`), passes the full 350-test regression suite, succeeds across all 7 end-to-end integration tools, and fully honors the ratified contract points set forth in `ticket-10-contract-review/index.md` (Sections 7 and 8).

## 2. Independent Verification & Reproduction Evidence

All test and verification commands were independently executed in the workspace environment (`Windows AMD64`, Python `3.14.6`, Node `v22.18.0`):

| Check / Tool | Command Line | Measured Result / Timing | Notes & Status |
| --- | --- | --- | --- |
| **Full Unittest Suite** | `.venv-windows/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"` | **Ran 350 tests in 20.122s. OK (skipped=4)** | 4 expected skips (Unix/tmux-specific tests on Windows). |
| **Stop Verification** | `.venv-windows/Scripts/python.exe tools/verify_session_stop.py` | **PASS (141.498ms API local end)** | `api_prior_results_retained: 1`, `provider_remote_compute: "unverified"`, `cli_unsupported_then_unresolved: true`, `quarantine_no_mention_cascade: true`, `stale_termination_http: 409`, `confirmed_owned_termination: true`, `reloaded_fences: true`. |
| **Session Events** | `.venv-windows/Scripts/python.exe tools/verify_session_events.py` | **PASS** | `api_calls: 3`, `admitted_events: 3`, `fresh_attempt_fenced: true`, `duplicates_stale_http: 409`, `source_executed: false`. |
| **Review Brief** | `.venv-windows/Scripts/python.exe tools/verify_review_brief.py` | **PASS** | `exact_source: true`, `chat_rollover_messages: 30`, `frozen_two_phase_design: true`, `wrong_seat_http: 403`. |
| **Dispatch Queue** | `.venv-windows/Scripts/python.exe tools/verify_dispatch_queue.py` | **PASS** | `cli_injections: 2`, `cli_mcp_releases: 2`, `same_id_deduplicated: true`, `owned_worker_stopped: true`. |
| **Seat Packaging** | `.venv-windows/Scripts/python.exe tools/verify_package.py` | **PASS** | `saved_seats: 3`, `healthy_peers_reused: true`, `stale_handoff_rejected: true`. |
| **API Seat Runtime** | `.venv-windows/Scripts/python.exe tools/verify_api_seat.py` | **PASS** | `seats: 2`, `worker_stop_acknowledged: true`, `secret_values_persisted: false`. |
| **CLI Seat Runtime** | `.venv-windows/Scripts/python.exe tools/verify_cli_seat.py` | **PASS** | `seats: 2`, `distinct_mcp_bearer_identities: true`, `child_exit_code: 23`, `final_state_after_exit_23: "failed"`. |
| **JS Syntax Check** | `node --check static/sessions.js; node --check static/chat.js` | **Exited 0 (Clean)** | No syntax errors or warnings. |
| **Git Diff Whitespace** | `git diff --check` | **Exited 0 (Clean)** | Clean whitespace across all modified and added files. |

## 3. Detailed Architectural Inspection

### 3.1 Lock Ordering & Compound Coordinator Synchronization

- **Strict Monotonic Ordering:** `SessionEngine` instantiates an internal `threading.RLock()` (`self._lock`) and wraps the underlying queue in a `CoordinatedQueue` (`queue_coordinator.py`).
- **Zero Cross-Store Inversion:** `QueueStore` (`dispatch_queue.py`) has no imports, calls, or references to `SessionStore` or `SessionEngine`.
- **Compound Operation Serialization:**
  - **Stop Path:** Acquires `CoordinatorLock` -> `session_store.stop_run()` (writes `dispatch_eligible: False`, `stop_id`, and durable fence under `SessionStore` lock, then releases it) -> `queue.cancel_run()` (cancels queued records and marks active dispatches `cancelling` under `QueueStore` lock, then releases it) -> releases `CoordinatorLock`.
  - **Claim / Enqueue Path:** `CoordinatedQueue` intercepts `claim` and `enqueue` under `CoordinatorLock`:
    - `enqueue()` snapshots run eligibility from `_sessions.list_all()` and rejects enqueues for stopped runs with `QueueConflict`.
    - `claim()` executes `_reconcile()`, ensuring any dead run work is purged before `_queue.claim()` runs.
  - **Start vs Stop Race Closed:** `test_stop_cannot_interleave_start_between_run_creation_and_first_dispatch` proves that `start_session` and `stop_session` acquire `self._lock`, preventing any window where an initial turn is dispatched into a stopping run.

### 3.2 API Invocation: Owned Child Process & Cancellation

- **Mechanism:** Implemented in `api_invocation.py` via `subprocess.Popen([sys.executable, ..., '--child'])`.
- **Supervisor Persistence:** The seat supervisor (`wrapper_api.py`) remains long-lived and does not restart or exit when cancelling a turn.
- **Empirical Justification:** In Windows/Python 3.14.6, thread-based socket closure leaves read threads hung for >10 seconds (`http-cancellation-probe-04f8b91f.json`), whereas owned child termination exits cleanly in ~2.35ms.
- **Credential Handling & Secret Containment:**
  - Credentials and request payloads are transmitted strictly via `stdin` (`child.communicate(input=packet)`), never in `argv`.
  - The parent supervisor pops the selected credential reference from the child's inherited environment (`environment.pop(reference, None)`).
  - The child process reads the packet over `stdin` and restores that selected credential into its own `os.environ` solely for `request_completion`. General process environment variables are not globally stripped.
  - `stderr` is redirected to `subprocess.DEVNULL`, and failure exceptions report status codes without leaking auth headers or raw provider bodies into logs or consoles.
- **Receipt Truthfulness:** `cancellation_receipt` enforces `remote_compute == 'unverified'`. Calling `cancellation_receipt` with any other status or value raises `ValueError`.

### 3.3 Truthful CLI Capability & Controlled Termination

- **Turn-Level Non-Interruption:** The Windows CLI adapter uses console input (`WriteConsoleInput` / console handles), rather than a verified per-turn ConPTY programmatic interrupt. When a turn is active, Stop causes `CliConsumer` to report `cancellation_receipt(..., 'unsupported')` without injecting cancel keystrokes into the terminal.
- **Deadline Behavior:** The turn remains held in `cancelling` until the 10-second deadline elapses, transitioning to `unresolved` in `session_engine.reconcile_stops()`. The persistent CLI process is **never killed automatically**.
- **Explicit Operator Termination:**
  - Available strictly via `POST /api/sessions/{session_id}/terminate-seat`.
  - Requires operator authorization (`x-session-token`), explicit `confirm: true`, and matching `(dispatch_id, launch_attempt)`.
  - Stale launch tokens reject with `409 Conflict`.
  - Termination requires the worker process to exit AND record a matching exit receipt with an integer `child_exit_code`. If the worker exits without recording child exit proof, it remains `unresolved`.

### 3.4 Durable Scoped Fencing & Chat Routing

- **Fencing Scope:** Fences are permanently keyed to `(session_id, run_id, attempt_id)`.
- **Tagged Ingress Quarantine:** In `send_chat` (`session_engine.py`), messages tagged with a stopped `dispatch_id` are quarantined into `SessionStore` (`quarantined_events`). The original text (including any literal `@mention` strings) is faithfully preserved, while `routing_suppressed: True` ensures no agent routing or mention triggers execute.
- **Suppression of Delayed Callbacks:** In `app.py` (`_handle_new_message`), delayed message callbacks check routing scope against `session_engine.chat_scope()` and suppress triggers if `routing_suppressed` is set.
- **Untagged Messages from Stopped Seats:** If an untagged chat arrives from a seat that had an active stopped turn, `chat_scope` marks it `unverified_scope` and prepends `[quarantine-warning] Unscoped output from a stopped seat: `. Mentions are suppressed from triggering agents, preventing cascading turns.
- **Quarantine Bounds:** Bounded to 64 records and 8 MiB per run in `session_store.py`.
- **Unblocked Channels:** Human chat, unrelated peer seats, and subsequent freshly tagged runs remain completely unblocked and fully functional.

### 3.5 Security Middleware & API Allowlist

- In `app.py` (`_install_security_middleware`), the Bearer token check allows registered agents to access `/api/queue/cancel`.
- Stale session tokens or unauthorized peers trying to cancel dispatches owned by another seat receive `403 Forbidden`.

## 4. Boundaries & Limitations

1. **Remote Compute Cancellation:** Ending the local process does not retract data transmitted over the wire or guarantee that remote LLM providers stopped charging or processing tokens. This is truthfully documented as `remote_compute: "unverified"`.
2. **Generic CLI Process Lifecycle:** The generic Windows console adapter lacks per-turn interrupt primitives. Work remains `unresolved` unless the operator explicitly triggers `terminate-seat`.
3. **Outbox Recovery & Full Restart Reconciliation:** Durable worker answer-outbox persistence and full runtime adoption after server restarts remain deferred to subsequent tickets (full restart reconciliation is tracked under issue #9; milestone progression continues with #11 next).
4. **Inherited UI Styles:** Inherited chat container styling (such as 713px container overflow on mobile) remains outside the scope of Ticket #10. The Ticket #10 diff touches only the Stop review button, stop status panel, and termination inline confirmation dialogs.

## 5. Review Conclusion

The Ticket #10 implementation is robust, adheres strictly to reporting integrity and concurrency invariants, and is backed by comprehensive automated test coverage and empirical probe verification.

**Verdict: PASS.** Ready for merge and issue closure.
