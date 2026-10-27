---
title: "Independent Review: Ticket #7 Durable Queue Envelopes & Single-Seat Ownership"
kind: review
comments: none
---

# Independent Implementation Review: Ticket #7 (Durable Queue Envelopes & Single-Seat Ownership)

- **Verdict:** **PASS**
- **Frozen Implementation Target:** `3b3a80f4b4d2660ec68e5e5bed55887b8bae3c5a`
- **Current Branch HEAD:** `1cc717e6297d6c618e4b9b057ad9b80a07c68b5f` on `codex/ticket-7-durable-queue`
- **Base Commit:** `d16780bd1d8554d1f197e9800e689850adfd8a8e` (`origin/main`)
- **Review Date:** 2026-10-22
- **Reviewer:** Antigravity (`gemini-3.8-flash`, Google DeepMind family; agent `ec1fbcd1-4a02-410e-9029-e498f67918c8`)
- **Builder:** OpenAI Codex (`codex/ticket-7-durable-queue`, OpenAI family)
- **Helper:** `fcc36344-f0ca-4514-9288-74753be75947` (configured Codex gpt-6-sol; helper/test author only, not independent reviewer)
- **Claimed Role:** `independent-reviewer` over scope `subsequent-tickets-review` (`claimId: 3b196d4b-c9fc-49f6-b360-8ecc4a48a8f2`)

---

## 1. Executive Summary & Attestation

This independent review and verification evaluates the implementation of **Ticket #7: Preserve Every Queued Turn** (spec v1.7 SD-3 / SC-5 / AT-21b with autonomous execution amendment) in the `agentchattr` repository.

### Source Equality Verification
- `git diff --stat 3b3a80f4b4d2660ec68e5e5bed55887b8bae3c5a HEAD` confirmed that HEAD (`1cc717e6297d6c618e4b9b057ad9b80a07c68b5f`) differs from the frozen implementation target **only** in documentation (`AUTONOMOUS-RUN.md`, `STATUS.md`, `TICKET-7-REVIEW.md`) and design detector metadata (`.impeccable/config.json`).
- All runtime Python application modules (`dispatch_queue.py`, `queue_client.py`, `agents.py`, `app.py`, `mcp_bridge.py`, `wrapper.py`, `wrapper_api.py`, `session_engine.py`), frontend assets (`static/chat.js`, `static/style.css`, `static/index.html`), and test suites are bit-for-bit identical to the frozen implementation target `3b3a80f4b4d2660ec68e5e5bed55887b8bae3c5a`.
- Working tree is clean.

### Governance & Gate Authority
- Seth explicitly removed routine human completion sign-off on 2026-10-22.
- Independent technical review and substantive verification remain strictly required.
- On this independent **PASS**, parent builder (Codex) is authorized to merge, push, close Ticket #7, and advance autonomously to Ticket #8 without further user sign-off.

---

## 2. Independent Test Execution & Verification

All test suites and integration verification scripts were independently executed on Windows in the repository's `.venv-windows` environment with dynamic ports and isolated scratch directories (`.audit-tmp`):

### A. Full Application Test Suite
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -c "import tempfile,unittest; tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlayground\agentchattr\.audit-tmp'; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not r.wasSuccessful())"
```
- **Result:** `Ran 293 tests in 11.511s. OK (skipped=4)`.
- The 4 skipped tests are expected platform-specific skips (Unix/tmux tests skipped on Windows).

### B. Durable Dispatch Queue Integration (`tools/verify_dispatch_queue.py`)
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_dispatch_queue.py
```
- **Result:** **PASS**
- **Output:**
  ```json
  {
    "result": "PASS",
    "successful_cli_injections": 2,
    "cli_mcp_releases": 2,
    "api_calls": 2,
    "release_withheld_blocks_next": true,
    "replacement_consumer_http": 409,
    "same_id_deduplicated": true,
    "legacy_bytes_preserved": true,
    "owned_worker_stopped": true,
    "retained_active_state": "uncertain",
    "retained_queued": 1,
    "fresh_consumer_blocked_after_failure": true,
    "scratch": "C:\\Users\\SJG\\Documents\\CodePlayground\\agentchattr\\.audit-tmp\\dispatch integration 2rfou9ev"
  }
  ```
- **Verified Specifics:**
  - 2 distinct CLI envelopes injected serially with distinct IDs, channel/prompt/job fields, and cooperative MCP releases.
  - Withheld release correctly blocks injection of the next turn (contention preserved).
  - Claim by a competing consumer returns HTTP 409 Conflict.
  - Enqueue with identical `dispatch_id` and payload is deduplicated; conflicting payload with same ID is rejected with 409.
  - Legacy `{agent}_queue.jsonl` files are left untouched with exact byte preservation.
  - Owned worker termination marks active dispatch as `uncertain`, retains queued work, and blocks fresh consumers from hijacking in-flight work.

### C. Scoped Review Brief Integration Regression (`tools/verify_review_brief.py`)
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_review_brief.py
```
- **Result:** **PASS** (`provider_calls: 1`, `cli_transport: "mcp-streamable-http"`, `exact_source: true`, `chat_rollover_messages: 30`, `frozen_two_phase_design: true`, `wrong_seat_http: 403`, `invalid_brief_no_provider_fallback: true`, `oversized_start_rejected: true`, `source_executed: false`).

### D. Whole-Package Launch Regression (`tools/verify_package.py`)
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_package.py
```
- **Result:** **PASS** (`saved_seats: 3`, `healthy_peers_reused: true`, `partial_failure_isolated: true`, `omitted_selection_ready: true`, `stale_handoff_rejected: true`, `provider_calls: 0`, `sessions_created: 0`).

### E. Configured API Seat Regression (`tools/verify_api_seat.py`)
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_api_seat.py
```
- **Result:** **PASS** (`seats: 2`, `provider_calls_before_dispatch: 0`, `targeted_restart_retry_stop: true`, `worker_stop_acknowledged: true`, `secret_values_persisted: false`).

### F. Configured CLI Seat Regression (`tools/verify_cli_seat.py`)
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_cli_seat.py
```
- **Result:** **PASS** (`seats: 2`, `distinct_models: true`, `distinct_mcp_bearer_identities: true`, `targeted_stop_peer_alive: true`, `child_exit_code: 23`, `final_state_after_exit_23`: "failed").

### G. Static Syntax & Formatting Checks
```powershell
node --check static/chat.js
node --check static/sessions.js
git diff --check
```
- **Result:** Clean exit 0, no syntax errors, no whitespace check violations.

---

## 3. Scope & Code Inspection Analysis

### A. Single Unified Transaction Ledger (`dispatch_queue.py`)
- Standardizes on a single transaction snapshot ledger (`data/queue/ledger.json`) guarded by cross-process kernel locking via `startup_lock` (`data/queue/ledger.json.lock`) and atomic replacement (`atomic_json`).
- Prevents split-brain crash states between separate claim and envelope files, and eliminates multi-process SQLite lock contention under Windows.
- Ledger schema validates record states (`queued`, `dispatched`, `acknowledged`, `uncertain`, `released`, `failed`) and enforces single-active-dispatch constraint per `target_identity_id`.

### B. Identity Binding & Fencing
- `agents.py` resolves `agent_name` against `RuntimeRegistry` at enqueue time and persists `target_identity_id`.
- Unregistered names are rejected immediately, preventing dispatches from being claimed by future replacement instances.
- Bearer-authenticated endpoints (`/api/queue/claim`, `/api/queue/ack`, `/api/queue/release`, `/api/queue/uncertain`) verify caller identity against `target_identity_id`, returning 403 on seat mismatch.

### C. CLI Transport Release vs. Session Advancement
- `mcp_bridge.py` exposes `chat_queue_release(dispatch_id=...)`, which delegates directly to `queue.release(...)`.
- The release endpoint accepts only `{consumer_id, dispatch_id}` and rejects any payload containing session output or engine advance commands.
- `wrapper.py` implements an in-memory `last_injected_dispatch_id` guard to prevent repeated terminal injections while polling for the release receipt.
- If a client fails to emit `chat_queue_release`, the seat remains visibly held in contention (`awaiting_release: true`), preventing turn overlapping or silent advance.

### D. API Serial Execution & Idempotent Release
- `wrapper_api.py` claims envelopes serially via `QueueClient`, calls the model, posts the chat message, and releases ownership.
- A failed HTTP release call is retried without regenerating the model answer.
- Dispatches are processed in FIFO order; two turns in the same channel remain separate envelopes and are executed sequentially.

### E. Legacy Preservation & Clean Status
- Pre-existing `{agent}_queue.jsonl` files are preserved untouched on disk.
- `/api/queue/status` reports their presence under `legacy_unmigrated_files: [...]`.
- Queue summaries exclude prompt text, source text, and credentials, exposing only state, count, contention, and dispatch IDs.

---

## 4. Scope Boundaries & Non-Blocking Notes

No blocking issues identified.

### Scope Boundaries Confirmed for Downstream Tickets
1. **Explicit Completion Admission (#8):** Ticket #7 provides transport-level release only. Full turn completion validation, output message admission, and run advancement contracts are deferred to Ticket #8.
2. **Server Restart Reconciliation (#9):** Uncertain in-flight dispatches remain retained on disk. Automated crash reconciliation and operator retry/fencing controls are deferred to Ticket #9.
3. **Interactive Cancellation (#10):** Cancelling active or queued turns remains scoped to Ticket #10.
4. **Outbox Durability (#11):** Idempotent API answer recovery from a dedicated result outbox remains scheduled for Ticket #11.

---

## 5. Limits of Verification

- **Live Provider Testing:** Live AI provider endpoints were not invoked; all verification ran against isolated fake providers and dynamic mock servers.
- **Native Client Execution:** Tests were performed in Windows fake CLI environments; native Linux/Omarchy tmux execution was not evaluated on this Windows host.

---

## 6. Final Verdict & Next Steps

- **Verdict:** **PASS**
- **Authority:** Seth's 2026-10-22 standing authorization applies.
- **Recommendation:** Parent agent Codex may proceed immediately to merge `codex/ticket-7-durable-queue` into `main`, push upstream, close Ticket #7, and commence Ticket #8.
