# Agentchattr release candidate

Updated: 2026-11-01. Owner: Codex recovery lead.

Canonical directory: `C:\Users\SJG\Documents\CodePlayground\agentchattr`.
Entry point: `Start Agentchattr.bat`. Python application code lives in `src/`.
Local main contains reviewed RC2 `05a16095`; release-layout changes are in progress.
GitHub publication and removal of external development worktrees remain pending.

## Verification

- Before and after relocation: real provider-free startup, two launcher reuses, authentication enforcement and owned server cleanup passed.
- Configuration overrides: 17 passed. Runtime source manifest closure: 2 passed.
- Launcher tests: all 16 passed with loopback access. The earlier sandbox run failed its loopback health check.
- Release ZIP builds. Extracted-package startup, broader path-dependent tests and independent review remain pending.

## Release blockers

- Sends advance read cursors and limited unread reads discard oldest messages. Both confirmed losses remain for the separately bounded repair assignment.
- Canonical six-seat configuration needs reconciliation. No provider was launched during recovery.
- Claude, Codex, Antigravity, GLM, Muse and DeepSeek must demonstrate a real review, document/task visibility, Stop and corrected restart in an agreed live window.
- Stakeholder acceptance is pending.

## Next

Codex completes the release layout, updates affected tests/tooling, verifies the extracted package, obtains independent review, publishes canonical source and removes superseded development copies after preserving unique evidence. The Desktop installation and its history remain preserved.

Evidence: [RC2 handoff](docs/history/STATUS-RC2-2026-10-27.md), [earlier history](docs/history/STATUS-2026-10-26.md), [specification](docs/agentchattr-fork-spec.md), [cutover plan](docs/superpowers/plans/2026-11-01-canonical-cutover.md).
