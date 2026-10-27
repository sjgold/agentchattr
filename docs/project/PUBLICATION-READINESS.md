# Publication readiness, reviewer-cleared note

**No push is authorized.** This note describes the proposed source publication. It does not approve deployment, a release ZIP, copying local configuration, stopping either UAT build or changing the working Desktop installation.

## Proposed branch and code

- Integration branch: `codex/ticket-20-r2-on-a1`.
- Proposed code pin: `c662722cca14e10a4e64d04212a473eddc4d375b`, plus the reviewed documentation commit containing this note.
- Local comparison base: `main` at `400d6de808dafbaebe1d378b40099c2fead5edd6` (Ticket19 closure). This is a local ref, not a fresh check of the remote target.
- Current frozen UAT: RC0 `99361d1` on49949; RC1 `fdc6c27` on50010. Neither checkout changes when integration advances.

RC1 contains the accepted Documents flow, multi-file review packets, pre-flight/label/restart fixes, CLI model defaults and reviewed UI changes. Integration adds the reviewed JSON entry-only adapter and corrected YAML/JSON receipt handling at `5d89816`, then the entry-name provenance fix at `c662722`. Reviewer cleared these later integration changes at c662722 and the note at433f3e0. A full run on the final publication tip remains required. They are absent from the running RC1.

## Size and tracked files

At the code pin, `git diff --stat main..c662722` covers316 changed files. The repository has605 tracked files. The diff is585564 added and1631 removed lines, mostly preserved historical receipts rather than runtime code.

|Area|Changed files|Added lines|Removed lines|
|---|---:|---:|---:|
|Runtime and other source/config|46|9187|168|
|UI|17|1627|733|
|Tests|99|21244|19|
|Tools|29|5068|10|
|Guides, plans and other Markdown|98|5143|701|
|Historical docs/receipts|27|543295|0|

The note and its STATUS update add documentation after this measurement. No historical receipts were deleted to shrink the change. The approved cleanup preserved110 tracked document renames; source/test/tool/static paths were not moved by that cleanup.

Tracked content includes product code, UI assets, tests, tools, plans, guides, the shortened STATUS and retained historical evidence. Seven private/local categories were checked as ignored: `.env`, `config.local.toml`, `.audit-tmp/`, `.launcher/`, `.venv-windows/`, `data/`, `uploads/`. None appears in tracked paths. The ignored roots contain live UAT environments, credentials/settings, logs, signing records and history; they are not publication material. No ignored-file census or bulk copy is proposed.

## What is excluded

- Hermes as a usable daily seat: real-home YAML write/MCP connection/exact restore passed twice, but its hello exited2. Windows batch-launched grandchildren can survive a direct Stop. The hello investigation is post-launch; the gateway processes were ended under Seth's grant and memory DB was untouched.
- Antigravity from the existing frozen RC1: it has no AGY seat. The corrected adapter/provenance and authorized real-file proof are now reviewer-accepted, including one34B document and exact restore. RC0 is intentionally stopped after that window. No local global-MCP settings or tokens ship, and integrating daily seat templates remains an explicit deployment/config choice.
- Unreviewed adapter changes. If the final integration pin is not cleared, do not publish that tip or silently substitute the older RC1, which contains the dormant stale-backup flaw.
- Tickets21/22/24-26 as implemented features. Their existing plans and9 dated skipped transcript tests remain tracked post-launch material.
- Multi-file additions beyond the bounded slice: adding to an existing selection, readable packet labels in frozen/restart views and early client file-count refusal. The server metadata cap remains enforced.
- Release ZIP packaging. The existing packager's module list was reported incomplete by the read-only assessment; no ZIP is proposed. Source launch uses the tested Windows start.bat -> Pre-flight route.

## Evidence and remaining limits

RC1's exact frozen pin passed245 modules/2164 tests in413.123s, with13 skips (9 post-launch transcript and4 existing). The reviewer checked its clean clone, log, activation tuple and endpoints. Builder live checks: one Haiku document109B and one DeepSeek document73B, Read/Download exact; two-file browser preview31B with independently matching revision. CLI actual model is not provider-confirmed. A live multi-file review and screenshot/visual acceptance were not performed; Seth's own end-to-end verdict is still open.

Post-RC1 adapter cleanup passed285 focused tests. The provenance sweep found one missing consumed key, mcp_entry_name;298 focused tests pass after binding it. All tests used temporary homes and fake processes. **There is no full-discovery result for the later integration pin yet.** Do not present the RC1 full result as coverage of those later bytes.

RC1 stays running. RC0 was explicitly stopped by Seth for the adapter proof and remains stopped; their roots/ports/registries remain separate. A fresh CLI workspace can require a one-time trust choice through its console. The source publication does not install the UAT's local seat package or API keys into a daily installation. The daily alias/template proposal still needs final approval and completion; secrets stay outside git. STATUS records the names-only credential exposure; Seth has rotations scheduled later this week. No agent rotates those credentials.

## Exact approval path

1. Seth tries RC1 through Pre-flight -> launch/reuse team -> chat -> Documents and multi-file preview, requesting a separate AGY restart/build when he wants it; RC0 is currently stopped. Record his verdict and any bounded defect fixes.
2. Integration adapter/provenance was reviewer-cleared at c662722 and this note at433f3e0. After Seth's UAT verdict, freeze the exact publication tip. If it differs from the tested RC1, run one final full discovery on that frozen tip, disclose skips and obtain the activation-state review. Repeat only relevant checks if a real fix changes it.
3. Confirm the intended remote target and compare it with the local main base without rewriting history. Review the final source diff, tracked/private-file boundary, secret scan, Markdown links and STATUS together. Resolve an advanced/divergent target explicitly.
4. Prepare the ordinary integration into the named publication branch, keeping STATUS in that same change. Do not force-push, delete branches/history, copy ignored roots or use build_release.py for a ZIP.
5. Seth explicitly approves the exact branch/tip and says to push. A push triggers his deployment, so this is the deployment approval step. Until then, only local commits are permitted.
6. After that explicit go, push normally to the agreed target, verify the resulting deployment/checks and record the actual result. Keep RC1 running until Seth asks to stop it. RC0 remains stopped under his instruction; any later restart uses its reviewed start path in an owned runtime. Cleanup uses only the relevant stop script and verified handles.
