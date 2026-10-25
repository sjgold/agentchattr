# Verdict: PASS WITH NONBLOCKING NOTES

Reviewer: Claude Sonnet 5.5 (agent 3b53a0e1). I edited no tracked product file, changed no assertion or timeout, and touched no live provider, Omarchy, Desktop or global setting. My probes, scripts and scratch runs live under `.audit-tmp/reviewer-claude/` and the scratchpad.

Frozen: product `90078e1eb4ab8b876e0e5a75d0c609187a573bca` on `codex/ticket-19-channel-lifecycle`. Acceptance tools `tools/verify_channel_lifecycle.py` SHA-256 `7427750E...7674B`, `tools/fake_channel_client.py` `9577AF8B...944AF`, `tools/channel_guard.py` `C08872FA...8F34`. Python production files are unchanged since `02ff956` (and the only change after that is static UI, see below).

## What I executed myself

| Check | Result |
| --- | --- |
| Pure catalog `ChannelStore` | 12 focused tests plus about 70 adversarial probes (probe19, probe19b) |
| Queue hold, atomic rewrite, rename/delete store phases | focused suites plus probe19c, probe21, probe23; independent timing copies probe25 (import), probe30 (rename) reproduced the builder's numbers |
| ChannelService, routes, ingress, agent paths, message and job mutations, sessions, schedules, shared binding | affected suites at each pin (see the per-slice messages), plus probes 20, 22, 26, 27, 28, 29, 31 |
| Rename orchestration | 86 tests; large-shape hold probe: worst single step 0.267 to 0.286 s, loop-thread stall 0.264 s |
| Retained API and upload metadata | 89 tests; probe31 end to end (no message text retained, upload bytes intact, one safe link) |
| UI | Node actual-source VM verifiers: channel_ui 12/0, channel_policy 4/0, document_ui 12/0, recipient_ui 12/0, job_storage_ui 2/0; independent red/green runs of the new focus and hover tests against the prior static files |
| Native acceptance (one unchanged run at `1034fbc`) | PASS from my own shell, scratch `channel lifecycle native 87_fig46`, 11.2 s: 2 injections/dispatches, 25 archived WS refusals, quiet 3.08 s with before == after, cleanup 1 server/1 worker/1 client/0 models, unresolved [], three guard records with 23 self-tests each and zero attempts |
| Browser acceptance (one unchanged run at `90078e1`) | PASS from my own isolated session, scratch `channel lifecycle browser zaucfc23`: pending hold and UI retry, Reload focus, typed confirmations, exactly one rename 200 on double activation, archive/reopen/delete retained view, tab-icon hover and focus reveal, detached-trigger focus return, synthetic DragEvents with the request body excluding the inactive job, 390 px dialog fit; cleanup 2 servers/0 workers/clients/models, unresolved [], guards clean |

## What was read, not executed

Large builder diffs and test modules were read in part and then run (named per slice in my messages to the owner). Two read-only analyst subagent scans (caller-lock scan for guarded writes; static Manage UI scan) supplied line leads that I spot-checked and did not re-verify one by one. Builder full discovery runs (the last: 1374 tests, 104.844s, OK with 4 skips, tracked 748f8265) are recorded as builder-only; I did not run full discovery myself.

## Findings raised and fixed during review

Contract and design (C1-C5, N1-N5, J1-J4, SF1-SF2, S1-S4, FR1-FR5, R1-R3, AC1-AC9, G1-G3, B-1..B-5, BC1-BC7, FB1-FB5, RT1-RT5, DND1, CSS1, FOCUS1) all settled in the thread. Defects found by running or reading and fixed before acceptance:

- Store/queue: catalog delete order (todos first), notice-drop and projection repair path (R1), startup recovery regression that skipped a lost terminal banner (F1).
- Services and routes: held jobs file turning the catalog view into a 503 (display scope amendment); per-row jobs/schedules/summaries read cost (R-J1); startup crash on an unreadable jobs or summaries file (R-J2, SF1); legacy-valid summaries held by over-strict validation (SF2); QueueConflict mapped to 400; broadcast failure reported as failure after a committed change.
- Acceptance harness: the isolation guard did not observe existence probes on Python 3.14 Windows (R1 in the harness review); guard in a heavy import chain (R2); volatile-file hashing (R3); version-check egress seam in the generated server; shutdown listener selection; pending-delete control exception type; nonce on private routes.
- Product defects only the rendered browser could find: focus lost to BODY on re-render of the Manage dialog, and wrapper hover/focus/editing regression hiding sidebar and tab action icons, plus the close-focus fallback to a hidden control. Fixed with new pins (`294364d`, `90078e1`); non-acceptance runs 1 and 2 retained untouched.

## Nonblocking notes

1. Whole-page overflow at 390 px (476 px) is inherited from the base app; only dialog fit is claimed. The coarse-pointer reveal rule is verified statically, not rendered.
2. Rendered claims are from the Traycer-managed isolated Electron Chromium; no installed browser, OS file picker, drag from the OS, assistive technology or Omarchy claim. Drag was synthetic DOM DragEvents on the real handlers.
3. The native case proves one live CLI seat with a fake client; busy classes beyond live dispatch, crash seams, due-schedule firing and typed-repair recovery are component evidence only. Crash and restart behavior is process-proven only for the clean-restart pending DELETE in the browser case.
4. Hover reveal takes about one second to settle in this runtime; unsettled samples read opacity 0.
5. The guard's unobserved list (DirEntry.stat, direct ctypes/pywin32, non-Python children, pre-hook site initialization, plus realpath/resolve and several path write events) is documented, not closed.
6. Per-step hold at the large rename shape is about 0.27 to 0.29 s (33.9 MB messages, 11.6 MB jobs); the user docs should state the measured sizes, not a general guarantee.
7. The retained-artifacts metadata file is not part of the archive export or import; artifact purge is not supported.
8. Held-store closures are intentionally broad: an unreadable retained-artifacts file pauses create, reopen, archive, rename and delete while healthy chat continues.
9. The browser reproduction did not repeat the injected 409/503/timeout faults, held-owner alerts, draft preservation, peer post, sidebar-layout hover/focus or retained expansions beyond the summary view; those rest on the owner's run and are attributed as such.

## Not covered

Native Linux/Omarchy, live AI providers or clients, remote cancellation, assistive technology, installed-browser behavior, whole-page 390 px layout, any case run after `90078e1`, and a reviewer re-execution of full discovery.
