# Recovery cleanup receipt

2026-11-01. Canonical application: Documents/CodePlayground/agentchattr, branch main.

Nine external Git worktrees retired:

- Traycer: codex-ticket-20-a1-isolated, codex-ticket-20-d4-timing-d43, codex-ticket-20-r2-on-a1, hermes-proof, hermes-yaml-adapter, ui-preflight-usable-ui.
- Previously staged: agy-json-adapter, hermes-running-path.
- Orca: halibut.

The integration directory's nested RC0, RC1, RC2 and other frozen checkouts were removed with it. Windows Git hit its long-path limit there; native PowerShell removed the exact verified directory. The Orca checkout contents and registration were removed, but another process holds its empty directory open. No unrelated process was stopped.

Before removal, each tree was archived under ignored data/recovery-evidence. Git metadata, virtual environments, dependency directories and bytecode caches were excluded. Every archive entry was read back; SHA256 was checked again before removal. Original chat records, private configuration, logs and unique source/evidence remain recoverable locally. These archives are excluded from GitHub and release packages.

Eleven obsolete branch refs were retired: the eight merged adapter/UI/Ticket20/Orca refs and three documentation-only tips. Unique status and UI handoff text was preserved under docs/history before deleting those tips. Older merged ticket branches remain historical Git references without checkouts.

Final Git worktree inventory contains only the canonical application. The separate working Desktop installation was preserved.
