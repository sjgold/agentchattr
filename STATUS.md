# Agentchattr release candidate

Updated: 2026-11-01. Owner: Codex recovery lead.

Canonical directory: `C:\Users\SJG\Documents\CodePlayground\agentchattr`.
Entry point: `Start Agentchattr.bat`. Python application code lives in `src/`.
Local main contains reviewed RC2 `05a16095` and source-layout commit `567b9a6`.
Canonical Pre-flight is running at http://127.0.0.1:8300/preflight.
Final verification and independent review passed. Canonical main is published to GitHub.
All nine external worktrees and their nested side-builds are retired. Eleven obsolete side-build branch refs were removed. Their recoverable private archives are in data/recovery-evidence.
One empty Orca halibut directory remains locked by another process; it contains no application and is no longer a Git worktree.

## Verification

- Before and after relocation: real provider-free startup, two launcher reuses, authentication enforcement and owned server cleanup passed.
- Configuration overrides: 17 passed. Runtime source manifest closure: 2 passed.
- Launcher tests: all 16 passed with loopback access. The earlier sandbox run failed its loopback health check.
- Extracted release boots with SHA256-identical Python sources and no repository PYTHONPATH fallback.
- Real local fake API and native fake CLI lifecycle checks passed: distinct models/identities, delivery, restart, retry, targeted Stop and CLI exit code 23 surfaced as failed.
- Claude Sonnet 5.5 independently cleared production layout and the frozen verification changes by source review. [Initial review](docs/testing/2026-11-01-release-layout-review.md), [follow-up](docs/testing/2026-11-01-release-layout-final-review.md).
- Final full pass: 2331 tests, 13 skips, no failures, 477.237 seconds. Skips retain the nine deferred transcript checks and four existing platform/optional cases. First pass had eight stale path-fixture failures; the corrected affected 48-test selection passed before the final full run.

## Release blockers

- Sends advance read cursors and limited unread reads discard oldest messages. Both confirmed losses remain for the separately bounded repair assignment.
- The canonical saved team contains exactly the six requested seats, all included. Three CLI executables and three API credential references resolve. Browser and screenshot checks confirm the rendered team. No real chat-provider seat has been launched during recovery.
- Claude, Codex, Antigravity, GLM, Muse and DeepSeek must demonstrate a real review, document/task visibility, Stop and corrected restart in an agreed live window.
- Stakeholder acceptance is pending.

## Next

Next owner: Seth, RC2 end-to-end acceptance. Open Start Agentchattr.bat, launch the saved Six-agent review team, and assess a small review plus document/task visibility, Stop and corrected restart. Record observed failures before expanding scope. The Desktop installation and its history remain preserved. This candidate is not yet stakeholder-accepted; the known unread defects above remain open.

Evidence: [RC2 handoff](docs/history/STATUS-RC2-2026-10-27.md), [earlier history](docs/history/STATUS-2026-10-26.md), [specification](docs/agentchattr-fork-spec.md), [cutover plan](docs/superpowers/plans/2026-11-01-canonical-cutover.md).
