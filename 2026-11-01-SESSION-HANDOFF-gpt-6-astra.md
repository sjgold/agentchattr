---
type: session-handoff
project: agentchattr
agent: codex
model: gpt-6-astra
date: 2026-11-01
time: "8:46 PM"
branch: main
session_type: debugging
active_plan: docs/agentchattr-fork-spec.md
---

# Session handoff: canonical app, six-seat recovery and dynamic model catalogs

**Written by:** codex / gpt-6-astra. **Project:** agentchattr. **Date:** 2026-11-01.

## What happened

Seth requested one current application in the normal project directory and removal of the accumulated side-builds. Initial acceptance exposed blocked typing, missing rendered messages, stalled dispatches, misleading activity and incomplete model controls. Sol and Luna handled bounded implementation and verification assignments, with Sonnet reviewing the changes; the lead coordinated integration and exercised the normal chat UI. A six-provider send/reply proof passed, and Pre-flight now discovers model choices and effort metadata dynamically.

## What's done

- Canonical application is `C:\Users\SJG\Documents\CodePlayground\agentchattr` on `main`. Entry: `Start Agentchattr.bat`; URL: `http://127.0.0.1:8300/preflight`. Python modules live in `src/`.
- RC2 source was integrated without rewriting history. Nine external worktrees and their nested frozen builds were retired; private recovery ZIPs are in `data/recovery-evidence/`. Only canonical remains registered. The separate Desktop installation was preserved.
- Fixed the mixed-generation asset collision, explicit Windows console input/output access, injection receipt checks, CLI activity reporting, network-independent local Stop, Codex TERM and local MCP approval, and ordinary exited-worker queue settlement. See `docs/testing/2026-11-01-six-seat-recovery.md`.
- Real-provider proof: normal-UI message **32** produced exactly six authenticated replies: DeepSeek **33**, Claude **34**, Muse **35**, Codex **36**, GLM **38**, Antigravity **39**. All six dispatches released and seats returned idle/available. Zero queued/active work; two historical failures were retained separately.
- Implemented dynamic metadata probes for Claude, Codex, Antigravity, DeepSeek, Muse and GLM. The UI shows a real model dropdown, per-model effort choices, background refresh and explicit Refresh models. Saved selections survive refresh failures; metadata changes do not demand a running-seat restart. See `docs/plans/2026-11-01-dynamic-model-catalog.md` and its review receipt.
- Live selector checks observed 17 Claude alias/resolved entries, 8 Codex, 6 Antigravity, 11 GLM, 9 Muse and 2 DeepSeek choices. These are observed counts, not fixed future expectations. Claude/Codex effort controls worked; selecting Codex Luna removed ultra; an unsaved effort survived refresh.
- Verification: 135 tests in the combined focused selection passed. Runtime selection passed 64; catalog backend passed 96; final UI selection passed 38. The earlier layout-only full run passed 2331 with 13 skips; it is not a full-suite claim for every later change. Corrective independent Sonnet source reviews passed. Extracted release booted with source-byte equality and no repository import fallback.
- Raised the confirmed Channels sidebar label from 10px to 12px. Actual browser measurement and screenshot showed it visible without horizontal overflow. Sonnet source review passed. Other styling was unchanged; no detector ignores were added.
- Product changes were published through `f6f71bc` before this handoff. This handoff commit includes the final label change and status update. At 8:46 PM Central, all six current seats reported ready; saved models and default efforts were unchanged. Leave them running unless a later scoped task requires an owned restart.

## What's NOT done

- Full stakeholder acceptance, a substantive six-agent document review, document/task visibility and corrected-restart acceptance remain pending. A successful roll call does not prove those workflows.
- Two confirmed unread losses remain in `src/mcp_bridge.py`: sends advance the sender's read cursor, and limited unread reads take the newest slice. The browser rendering repair did not fix these separate mechanisms.
- Browser local storage still shares the localhost origin with the old installation. Selecting Back to general fixed Seth's stale radar-review channel for this session; permanent instance scoping remains pending.
- The inherited operator name `must not change` still needs tracing and cleanup. Preserve old message authorship while addressing the setting.
- Two generic padding warnings lack reliable element attribution. Other contrast and hover findings remain in `docs/testing/2026-11-01-ui-warning-audit.md`. One empty Orca `halibut` directory remains held by another process, with no application contents or Git registration.
- Native catalog lists are not exhaustive retirement authority. Muse/GLM basic metadata does not establish every model's chat compatibility or effort support. No generation-based compatibility sweep was performed.

## What's next

1. Morning reporting agent: read `STATUS.md` and this handoff, then report the proven basic flow and the open acceptance boundaries. No provider calls or code changes are needed for that report.
2. Seth chooses the next bounded assignment. Recommend fixing the two unread-cursor losses first; implementation owner is currently unassigned. Require red-first tests proving send does not consume unread messages and limited reads drain oldest-first without gaps.
3. After that repair, agree a live window for one small document review, task/source visibility, Stop and corrected restart. Preserve the existing failed attempts and original review evidence.
4. Keep browser-state isolation, operator-name cleanup and the remaining mapped readability issues as explicit follow-ups. Do not turn this list into automatic backlog execution.

Suggested skills for the next approved defect: `diagnosing-bugs` for a precise reproduction and the appropriate focused verification workflow. Morning reporting needs neither implementation nor a new review fleet.

## Gotchas

- The old and new apps had used identical `core.js?v=223` URLs despite different contents. Replaying old core with current history code reproduced the missing display helper, spinner and absent messages. Actual Firefox cache contents were not captured; supported Chromium/IAB checks and the deterministic mixed-generation replay supplied the evidence.
- A ready console is not proof a turn can run. Codex was waiting at a TERM=dumb confirmation, then separately refused MCP calls under never-approve policy. Both were repaired within the owned child configuration. Do not remove filesystem restrictions or edit global client settings to work around failures.
- Two orphan Codex children were verified individually and retired. Their parent PIDs had been reused; those unrelated processes were left alone. Original receipts and explicitly labelled operator-observed exit evidence are retained privately.
- Windows sandbox networking caused TestClient/socketpair hangs. Unsandboxed focused tests passed. Do not treat that harness failure as an application regression or keep retrying the same blocked test setup.
- Operational logs can contain local browser session tokens. Use sanitized summaries; do not dump raw server logs, identity files or credentials into tool output or handoff documents.
- CLI model catalog caches and picker lists can be partial. Failed refreshes must not retire saved choices. Current runtime comparison intentionally retains frozen catalog evidence for unchanged running seats; new launches/restarts validate current metadata.
- Loop guard counts agent messages that mention other agents, per channel. The default 4 is sufficient for six direct replies to a human roll call. Human messages or `/continue` reset it. It is unrelated to the repaired transport failures.
- Seth wants a lead coordinating cheaper bounded workers rather than Astra implementing everything. Luna handled UI/tests, with xhigh used for the stateful UI correction; Sol handled runtime and catalog backend. Different-family review remained separate.
- Earlier handoffs under `docs/history/handoffs/` describe deleted worktrees and former next steps. They are historical evidence; root `STATUS.md` and `AGENTS.md` govern current work.

### Durable-doc updates needed

None required for this wrap-up beyond the requested `STATUS.md`, style audit and handoff updates. `AGENTS.md` already records canonical delivery, `src/`, and explicit authorization for future worktrees. No other agent's global configuration or historical handoff was changed. Open Brain capture was skipped because the durable project decisions and evidence are now in these accessible project files.

## Key files

**Modified this session:**

- `src/launcher.py`, `src/cli_worker.py`, `src/wrapper_windows.py`, `src/wrapper.py`, `src/queue_client.py`: launch, transport, Stop, activity and exited-worker recovery.
- `src/model_catalog.py`, `src/api_seats.py`, `src/cli_seats.py`, `src/api_seat_runtime.py`, `src/package_launch.py`, `src/app.py`, `src/runtime_protocol.py`: catalog discovery, validation, frozen settings and endpoints.
- `static/api_seats.js`, `static/preflight.html`, `static/index.html`, `static/recipients.js`: model/effort controls, cache separation and friendly audience labels.
- `static/style.css`: the final 12px Channels label.
- `tests/test_model_catalog.py`, `tests/test_preflight_ui.py`, `tests/test_history_asset_generation.py`, `tests/test_asset_cache_isolation.py`, `tests/test_cli_exit_queue.py`, `tests/test_managed_cli_activity.py`, `tests/test_windows_injection_receipts.py`: focused regressions. Related existing tests were updated for the `src/` move.
- `README.md`, `AGENTS.md`, `STATUS.md`, `docs/plans/2026-11-01-dynamic-model-catalog.md`, `docs/testing/2026-11-01-*.md`: delivery entry, instructions, verification and review evidence.

**Must read on resume (do not re-read if already loaded):**

- `AGENTS.md`, `STATUS.md`, this handoff.
- `docs/agentchattr-fork-spec.md`: governing v1.7 scope, especially equivalent inputs and acceptance.
- `docs/testing/2026-11-01-six-seat-recovery.md` and `docs/testing/2026-11-01-model-catalog-review.md`: exact proof boundaries and reviewed decisions.
- `src/mcp_bridge.py`: before the next approved unread-loss repair; inspect actual callers before editing.

## Next prompt

```text
Prepare the agentchattr morning status from AGENTS.md, STATUS.md and 2026-11-01-SESSION-HANDOFF-gpt-6-astra.md in the canonical project folder. Report the proven six-agent send/reply flow and dynamic model controls separately from pending stakeholder/document/restart acceptance. Recommend the bounded unread-cursor repair as the next decision for Seth, with implementation unassigned. Do not launch providers, rerun acceptance or start backlog work just to produce the report.
```
