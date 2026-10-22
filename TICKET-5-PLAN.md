# Ticket #5: save and relaunch an agent package

**Goal:** Reopen a saved mixed team, launch/reuse its selected seats, resolve failures individually and enter chat with a freshly checked team. Package launch creates no review session or prescribed rounds.

**Authority:** Spec v1.7 PF-3/4, AT-02/03 and issue #5. On 2026-10-22 Seth removed routine human plan/completion gates and authorized autonomous continuation with the same Antigravity tester. This plan uses that authorization; no additional design approval is pending.

**Baseline:** #3/#4 already deliver mixed-package persistence, per-seat launch/reuse/restart/stop, secret-reference validation and model honesty. Missing: whole-team launch, stable saved selection on reopen, explicit exclusion for one launch, and a server-checked chat handoff.

## Design decisions

- Extend `SeatManager` and the existing authenticated preflight routes. Keep package schema/storage compatible; add a canonical package revision hash rather than duplicate package data into a second editable store.
- `launch_package(package_id, revision, restart_seats=None, omitted_seats=None)` freezes a launch selection and attempts each included saved seat using existing ownership checks. Explicit omissions apply only to that launch; saved membership is unchanged. Errors stay per-seat and healthy peers remain running. Do not silently replace clients/models.
- Store a secret-free selection receipt under the existing data directory, with selection ID, frozen package/revision, explicit omissions and bound attempt IDs. It is a package-launch receipt, not a review run. No automatic server-restart process adoption (#9).
- `package_status(package_id)` checks the latest saved revision and live matching attempts on every read. Changed package/template settings, stale/failed/restarted attempts or omitted-all selections cannot claim readiness.
- `continue_package(package_id, selection_id)` rechecks readiness server-side and returns a chat URL only for the current complete selection. It creates no session, messages, phases or model request. Generic chat remains accessible independently.
- Reopen the last selected saved package using a browser-local package ID only. Unsaved form changes/exclusion edits disable team chat handoff. Launch/reuse selected team; offer existing targeted retry/restart plus explicit per-launch exclusions. Keep UI in the existing design system.

## Tasks and interfaces

- [x] 1. Test author: new `tests/test_package_launch.py`, fail-first against real store/manager with fake Popen/receipts. Verify mixed roundtrip, stale revision rejection, reuse, mismatch/restart, partial failure preservation, explicit omission, empty/unknown/duplicate choices, dead/stale attempt and no-session chat handoff.
- [x] 2. `api_seats.py`: add `package_revision(package)` and `SeatStore.package(package_id)`. Resolve callers before changing lookup contracts. Keep malformed storage preservation and API/CLI validation.
- [x] 3. `api_seat_runtime.py`: implement package selection lifecycle, immutable receipts and fresh matching-readiness checks under existing manager/storage locks. Do not turn a batch operation into implicit rollback or automatic restart.
- [x] 4. `app.py`: authenticated package launch/status/chat routes. Strict request schemas and stale-revision errors; no credentials in response or diagnostics.
- [x] 5. `static/api_seats.js`, `static/preflight.html`: remembered selection, launch team/exclude-for-launch controls and checked chat navigation. Preserve draft edits while polling and show actionable per-seat status.
- [x] 6. Verification: full suite, fake mixed-client integration, API/CLI regressions as appropriate, rendered save/reopen/team launch/failure/handoff and 390px layout, JS/diff checks. No live providers or native Omarchy work.
- [ ] 7. Freeze, same Antigravity independent review, fix/recheck as needed, then authorized publication/closure and advance to #6 without human gate.

## Review focus

Store revision versus frozen attempts; concurrency during save/launch; invalid omission/restart IDs; active-template drift; health expiry after ready but before handoff; selection replacement while browser is stale; secret-free receipts; partial failures never stopping healthy seats; no accidental review session creation.

## Builder verification (2026-10-22)

- Full Windows suite: 248 tests OK, four Unix/tmux skips. Package runtime regressions first failed on missing interfaces; endpoint tests first failed on missing revision/interface. Receipt-failure/immutability cases are additional fault-injection checks. One test's repeated mock-process subtests needed independent setup; no production behavior was relaxed.
- Real mixed API/CLI integration `tools/verify_package.py` passed (test author twice and Codex rerun). Three saved seats, partial credential failure, healthy peer reuse, explicit launch-only omission, stale selection/revision rejection, targeted changed-model restart preserving peers, exact CLI argv/MCP isolation and stopped member invalidation. Provider calls zero; no session or message creation. Existing fake-API integration passed, JS syntax and diff checks passed.
- Browser-harness hit the existing Chrome remote-debugging permission prompt; no permission was auto-granted or user profile modified. Used an isolated chrome-devtools-axi session with an already cached MCP binary, without installing dependencies. Verified mixed saved selection, blocked handoff with failed member, explicit exclusion, draft-edit disabling, save/reload, new-tab reopening, fresh ready handoff to actual chat and no visible error. Exact 390px viewport verified via emulation; screenshot PNG dimensions checked and image inspected. Screenshot CLI falsely reported no saved path on later calls; actual files were verified independently. Fixture seats/server and isolated browser session were stopped.
- Native Linux/Omarchy and live provider/client compatibility remain unverified. CLI ready still means mention injection; package receipts do not adopt old processes across server restart. Existing chat remains a separate session-design surface; handoff itself creates no review run.
- Test-author rate-limit failover: existing Sonnet assignment hit Claude quota before completion, so it was reconfigured to Codex gpt-6-sol/medium per the agent-selection guide. AgY was never replaced as independent reviewer. Seth paused to confirm that distinction, then explicitly resumed.

Next baton: same Antigravity independent review of frozen implementation; fix/recheck substantive findings. On PASS, merge/push/close and proceed to #6 under standing authorization.
