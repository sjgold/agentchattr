---
type: session-handoff
project: agentchattr
agent: codex
model: gpt-6
date: 2026-10-12
time: "10:29 AM"
branch: main
session_type: design
active_plan: docs/agentchattr-fork-spec.md
---

# SESSION-HANDOFF — Agentchattr fork and lightweight review scope

**Written by:** codex / gpt-6 · **Project:** agentchattr · **Date:** 2026-10-12

## What happened

The user wants agentchattr to replace the daily Warroom workflow and the useful parts of Tribunal, with one launch/pre-flight entry point and coordinator-designed sessions in chat. A raw upstream fork was created, then the specification gained capacity and lost-turn recovery requirements after a reported GLM freeze. The latest decision explicitly cuts Tribunal's heavyweight machinery: preserve its spirit through independent API first passes, mechanical quote checks, and visible serious findings beside synthesis.

## What's done

- Created the public fork at https://github.com/sjgold/agentchattr with origin pointing there and upstream pointing to bcurts/agentchattr.
- Recorded upstream baseline `d775776a30e8af4c85ea16b3caaf9c79d65cb239` on `main`; application source remains unchanged.
- Updated `docs/agentchattr-fork-spec.md` to v1.6, including simplified section 8A and matching acceptance criteria. AT-17/18 are retired, not renumbered.
- Retained SC-5 durable dispatch, API outbox, selected CLI message recovery, visible deadlines, retry/replace/skip, and AT-21a-d failure cases.
- Added a narrow `.gitignore` exception, deterministic JSON findings parsing with distinct parse flags, and individual source-file plain-text intake.
- Updated `STATUS.md` for the daily-review collector and removed machine-specific absolute paths from published documentation.
- No implementation phase is complete; this is the documentation checkpoint.

## What's NOT done

- Multi-file packets are required after the initial build; individual-file intake is only the initial scope.
- User subsequently authorized pushing as needed; the earlier publication approval blocker is resolved.

- No application fixes, dependency installation, live model calls, or acceptance tests in this fork.
- No full comparison of the original Desktop installation against upstream.
- Historical GLM freeze cause remains unproven; source mechanisms are candidates, not incident evidence.
- No Tribunal code import, automatic repair loops, derived verdicts, voting rules, CLI isolation machinery, or separate Tribunal checkpoint/model-replacement policies.
- No old-project retirement or data migration.

## What's next

1. Read `STATUS.md` and spec v1.6, then compare the original `Desktop/agentchattr-0.5.0` installation with this `Documents/CodePlayground/agentchattr` checkout. Inventory local launchers/adapters and verify Stage A defects against the pinned baseline without launching providers or copying credentials/history.
2. Produce a bounded Stage A implementation plan with reproducible evidence and retained-launcher decisions.
3. Implement verified baseline fixes, then Stage B launch ownership and Stop/correct/restart with fake-adapter tests.
4. Continue C/D daily controls and artifacts, then E lightweight independent review. Request a specific live-test package before usage-consuming acceptance.

**Suggested skills:**
- `diagnosing-bugs` for reproducing adapter failures.
- `writing-plans` for the bounded implementation package.

## Gotchas

- Upstream ignored `docs/`; a narrow exception now tracks the canonical spec. Do not assume ignored runtime files should also be committed.
- The original Desktop tree has no Git metadata and remains the working installation. The new upstream includes `archive.py`; the old missing-module observation is not an established upstream bug.
- API error handling can print `Error handling trigger` without notifying the engine; the engine has no turn timeout. CLI polling collapses batch entries and may mix their fields; API polling also groups by channel. Both need regression tests, but neither proves the historical freeze.
- API independence requires explicit payload construction excluding channel history and peer findings. The existing history-reading API path does not provide it automatically.
- A matched quote proves text attribution, not the validity of a criticism. Serious-finding preservation is a synthesis instruction plus visible source findings, not an enforced verdict.
- Six named seats demonstrably participated in the October 9 report: Claude, Codex, Antigravity, GLM, Muse, DeepSeek. Hermes/OMP interactive agentchattr operation remains unverified despite installed commands and older isolated configuration checks.
- Four-participant phase and six-role caps exist in the new baseline's `session_store.py` validation. Spec requires configurable capacity, all six in one phase, and representable larger packages.
- No root context files or prior handoffs were found in this fork. The session's Clairvoyance context file points at a different project; do not associate agentchattr work with that workspace.
- Old HTML/spec copies may be historical; `docs/agentchattr-fork-spec.md` in this fork is authoritative. Cached upstream activity was misleading; the pinned baseline is September, not July.

### Durable-doc updates needed

None beyond the expressly requested specification/status update. No governing root context files were present. No Open Brain capture is needed: project decisions are recorded here and in the specification.

## Key files

**Modified this session:**
- `.gitignore` — allow only the canonical spec under docs.
- `docs/agentchattr-fork-spec.md` — v1.6 product/implementation requirements and acceptance criteria.
- `STATUS.md` — current state and next step for daily collection.
- `2026-10-12-SESSION-HANDOFF-gpt-6.md` — this resume checkpoint.

**Must read on resume (do not re-read if already loaded):**
- `STATUS.md` and `docs/agentchattr-fork-spec.md` — governing scope; no root CLAUDE/AGENTS/RULES/GEMINI context files found.
- `wrapper_api.py`, `wrapper.py`, `session_engine.py`, `session_store.py` — scoped failure/capacity candidates when performing Stage A.
- `.gitignore` — ignored docs and runtime content.

## Next prompt

```text
Continue agentchattr from STATUS.md and 2026-10-12-SESSION-HANDOFF-gpt-6.md in Documents/CodePlayground/agentchattr. Use docs/agentchattr-fork-spec.md v1.6: Tribunal's spirit, not its engine. Begin Stage A with a read-only comparison against Desktop/agentchattr-0.5.0, inventory local launchers/adapters, and reproduce baseline defect candidates with scoped inspection or fake adapters. Produce a bounded implementation plan; preserve the original installation and do not launch providers or copy secrets/history.
```
