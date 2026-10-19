---
kind: review
title: "Independent Review: Ticket #3 Configured API Seats"
comments: none
---

# Independent Implementation Review: Ticket #3 (Configured API Seats)

- **Verdict:** **PASS WITH NONBLOCKING NOTES**
- **Reviewed Target:** `b4fd3d68b61dbcfd8420f4a3caffc11fc77cfdd6`
- **Base Commit:** `8127ea1992e464cbbc56d63df2325742b8382bc9` (`origin/main`)
- **Current HEAD:** `5271ada133b756c416e82dd34e152525ef249638` (`codex/ticket-3-api-seat`)
- **Review Date:** 2026-10-18
- **Reviewer:** Antigravity (`gemini-3.8-flash`, Google DeepMind family; agent `ec1fbcd1-4a02-410e-9029-e498f67918c8`)
- **Builder:** OpenAI Codex (`codex/ticket-3-api-seat`, different model family)
- **Claimed Role:** `independent-reviewer` over scope `ticket-3-api-seat`

---

## 1. Executive Summary & Attestation

This independent review evaluates the implementation of **Ticket #3: Configured API Seats** (spec v1.7 PF-2/3/4 and AT-02) within the `agentchattr` repository.

The application code frozen at commit `b4fd3d68b61dbcfd8420f4a3caffc11fc77cfdd6` has been verified against the base `8127ea1992e464cbbc56d63df2325742b8382bc9`. The current branch HEAD (`5271ada133b756c416e82dd34e152525ef249638`) contains only subsequent freeze-receipt documentation and detector metadata (`.impeccable/config.json` font exception); the underlying application code is identical to the frozen target.

All builder verification claims were tested independently on Windows in the local repository environment without calling external providers or touching live credentials:
- Full test suite: 198 tests run, OK (4 platform skips).
- Real-wrapper loopback integration (`tools/verify_api_seat.py`): Passed with worker stop acknowledgement, clean targeted operations, and zero persisted secrets.
- Static checks: `node --check static/api_seats.js` and `git diff --check` both passed cleanly with exit code 0.

Final completion sign-off remains with the human user (Seth); no automatic merge, push, or ticket closure is performed.

---

## 2. Independent Test Execution & Verification

The following verification commands were executed from the repository root:

### A. Full Application Test Suite
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -c "import tempfile,unittest; tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlayground\agentchattr\.audit-tmp'; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not r.wasSuccessful())"
```
- **Result:** **198 tests run, OK (4 skipped)** in 8.851 seconds.
- **Details:** The 4 skips correspond to Unix/tmux-dependent launcher tests as expected on Windows. 23 dedicated Ticket #3 unit and runtime tests passed (9 in `tests/test_api_seats.py`, 14 in `tests/test_api_seat_runtime.py`, and preflight endpoint tests in `tests/test_preflight.py`).

### B. Real-Wrapper Fake-Provider Integration
```powershell
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_api_seat.py
```
- **Result:** **PASS**
- **Captured Output:**
  ```json
  {"result": "PASS", "url": "http://127.0.0.1:59575/preflight", "seats": 2, "provider_calls_before_dispatch": 0, "payload_model": "requested-one", "confirmed_model": "fake-provider-confirmed", "targeted_restart_retry_stop": true, "worker_stop_acknowledged": true, "secret_values_persisted": false}
  ```
- **Verified Behaviors:**
  - Launch generated 0 provider calls before message dispatch.
  - Two distinct seats operated against one configured fake provider.
  - Requested model (`requested-one`) and reasoning effort (`high`) were delivered accurately in the provider request payload.
  - Confirmed model was captured only from provider completion response.
  - Stop control file (`stop.json`) was written and acknowledged by the running worker before supervisor cleanup.
  - Changing package settings on an active seat required an explicit restart choice (409 on plain launch).
  - Provider 401 response transitioned the seat to an `action_required` state without crashing the supervisor or affecting sibling seats.
  - No secret values or session tokens leaked into `api_seats.json` or runtime attempt snapshot/receipt files.

### C. Static Checks
```powershell
node --check static/api_seats.js
git diff --check
```
- **Result:** Both passed with exit code 0 and no warnings or whitespace errors.

---

## 3. Detailed Scope & Behavioral Analysis

| Focus Area | Spec Requirement | Verified Behavior | Status |
| :--- | :--- | :--- | :--- |
| **Strict Schema & Validation** | PF-3, AT-02 | Packages and seats reject unknown fields, literal keys, invalid identifiers, and unconfigured providers. Ports and URLs are strictly checked for valid syntax and loopback HTTP or HTTPS requirements. | **PASS** |
| **Secret Reference Safety** | PF-2, PF-3 | Only environment variable names matching `[A-Za-z_][A-Za-z0-9_]{0,127}` are accepted. Secrets are resolved at runtime in memory; no credential strings appear in packages, snapshots, receipts, or URLs. | **PASS** |
| **Model Honesty** | PF-3, AT-02 | Requested model is forwarded to the payload; null sends Provider default. Confirmed model is recorded solely upon successful completion response. UI explicitly labels requested vs. confirmed models. | **PASS** |
| **Reasoning Effort Validation** | PF-3, AT-02 | Selected reasoning effort must be declared in the provider template's `reasoning_efforts` list. Undeclared values fail upfront validation; no silent fallback or dropping occurs. | **PASS** |
| **Atomic Storage & Windows Locking** | PF-4 | Package storage uses `.lock` serialization and atomic temporary file replacement. `atomic_json` includes bounded exponential backoff retry for transient Windows `PermissionError` (WinError 5). Previous files are preserved on failure; valid replacements produce unique `.bak` files. | **PASS** |
| **Launch Ownership & Targeted Stop** | PF-4 | Server tracks owned `subprocess.Popen` handles. Active seats are assigned unique launch attempt IDs and isolated base names. Stop writes `stop.json` for cooperative worker termination, waits 2s, and invokes `stop_owned_child`. Sibling seats remain undisturbed. | **PASS** |
| **Deregistration Cleanup** | PF-4 | Server deregistrations match attempt base identities even if a child exits abruptly before writing a receipt. No untracked process killing. | **PASS** |
| **Pre-flight Auth & Origin Security** | Security | Pre-flight endpoints (`/api/preflight/seats`, `/api/preflight/packages`, launch, stop) require valid `x-session-token` and enforce strict local origin headers, blocking unauthorized or cross-origin access. | **PASS** |
| **Deadlines & Bounded Operations** | PF-2 | 15s startup and heartbeat deadlines, 10s frontend request abort signal, 20-poll maximum polling loop, 120s provider socket timeout. | **PASS** |

---

## 4. Unverified Platforms & Boundaries

The following areas were not verified and remain bounded:
1. **Linux / Omarchy Execution:** Native Linux and Omarchy launcher testing remains deferred at Seth's request due to mounted filesystem constraints.
2. **Live External Providers:** No external network requests or paid model quotas were consumed; all verification used loopback mock and fake providers.
3. **Downstream Tickets (#6–#10):** Durable API result outbox (#6–#8), full server-restart reconciliation (#9), and remote provider request cancellation (#10) belong to subsequent tickets and are not claimed as implemented in Ticket #3.

---

## 5. Nonblocking Notes & Observations

These findings are nonblocking for Ticket #3 acceptance but should be tracked for ongoing code health:

### Note 1: Implicit Global Scope Dependency in UI Scripts
- **File & Line:** `static/api_seats.js:123`
- **Trigger:** `detail(list, 'State', ...)` calls the `detail` function defined in `static/preflight.js:5`.
- **Impact:** Both scripts are loaded with `defer` in `static/preflight.html` (`preflight.js` then `api_seats.js`), which guarantees execution order in standard browsers. However, depending on an undeclared global function creates a loose coupling if script tags are reordered or `api_seats.js` is reused elsewhere.
- **Recommendation:** Declare `detail` explicitly within `api_seats.js` or attach shared helpers to a lightweight namespace (e.g., `window.PreflightUI`).

### Note 2: Uncapped Backup Retention on Package Edits
- **File & Line:** `api_seats.py:129`
- **Trigger:** `shutil.copy2(self.path, self.path.with_name('api_seats.' + uuid.uuid4().hex + '.bak'))` generates a new backup on every package save.
- **Impact:** In routine desktop use this is safe and provides disaster recovery, but frequent automated saves could accumulate orphaned `.bak` files over time without a retention cap.
- **Recommendation:** Add a bounded pruning routine in a future maintenance pass to retain the N most recent backups.

### Note 3: Provider Template Removal Behavior
- **File & Line:** `api_seats.py:108` and `api_seats.py:61`
- **Trigger:** If a provider template is deleted from `config.toml` while an existing package in `api_seats.json` still references it, `SeatStore.list()` raises `SeatError` during validation.
- **Impact:** The pre-flight UI reports a configuration error and preserves the stored file rather than corrupting it. The user must restore the template or manually edit `api_seats.json`.
- **Recommendation:** In a future UI enhancement, consider surfacing individual orphaned seats with a 'Template Missing' badge rather than failing the entire package listing.

---

## 6. Conclusion & Recommendation

The Ticket #3 implementation meets the requirements of spec v1.7 PF-2/3/4 and AT-02. The code adheres to strict validation, ensures model and confirmation honesty, enforces robust secret protections, and safely manages owned child processes under Windows.

**Recommendation:** **PASS WITH NONBLOCKING NOTES**. Ready for Seth's human final sign-off.
