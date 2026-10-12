# STATUS - AGENTCHATTR

**Updated:** 2026-10-12 (ticket #2 independently reviewed: PASS WITH NONBLOCKING NOTES; human sign-off pending; Omarchy testing deferred)

- Maintain this file in the same push as project changes: Seth's daily-review agent collects root status documents.
- This file plus [the specification](docs/agentchattr-fork-spec.md) should be enough to resume.
- Update actual results and next steps, not intended features presented as shipped.
- Root `AGENTS.md` requires agents to read this file before work and maintain current status, verification, blockers, and the next action before handing off.

## Ticket #1 checkpoint

- [Baseline audit](docs/launcher-baseline-audit.md) and [bounded Stage A plan](docs/superpowers/plans/2026-10-12-stage-a.md) are written. Source comparison covers 79 selected paths: 54 equal, 16 different, 2 fork-only, 7 installation-only. Raw hashes and observations are in `launcher-baseline-evidence.json`.
- Ten Python offline observations and a separate Node composer reproduction confirm configuration overwrite, swallowed Windows child status, CLI/API queue coalescing, missing API instructions/attachments, console-only API errors, status-triggered advancement, absent engine cancellation, capacity ceilings and additive recipients. The candidate Hermes writer also accepts an invalid empty server sequence. These checks establish baseline behavior, not the historical GLM incident's cause or fixed product acceptance.
- Eight existing MCP configuration tests passed using workspace-local temporary files after the sandbox's default temporary path failed. No dependencies installed, application started, provider called or installed launcher executed. Full application suite not run; this interpreter lacks FastAPI/Uvicorn/MCP.
- Retain newer fork source. Adapt the installation's shared-launch concept and optional API/Hermes/OMP aliases; do not bulk-copy source/configuration. Fork `archive.py` exists, so no missing-file fix is planned.
- User added Linux/Omarchy launcher equivalents to the launch scope and offered Windows-hosted or dual-boot testing. Plan includes shared launch behavior, separate platform environments, tmux/ownership tests and later native desktop validation. No Omarchy execution yet.
- Passive Windows discovery found OMP and Hermes EXE/CMD; CodeBuddy was not found. Authentication, versions, connection and current readiness are unverified. Optional-client source/configuration diagnostic pass is bounded and complete; live diagnosis is deferred to an authorized package.
- Meta returned **PASS WITH NONBLOCKING NOTES** on the pack frozen at `fc19bc57daad9373ac9593163ff4fdd179c5a3da`. Reviewer self-identifies as Muse Spark (Muse family, Meta); exact backend ID unavailable. [Review receipt](REVIEW-MUSE-TICKET-1.md) records its source/plan review without repo access or independently executed tests. Both documentation notes are addressed: explicit normalized equality versus raw hashes, and separate Node E10 provenance in JSON metadata. No substantive fixes/recheck requested. Historical handoff remains unchanged. Seth gave final sign-off ("ship it") on 2026-10-12; GitHub issue #1 is closed as completed.
- Optional Lavish review surface was generated using the product's design tokens, but its local server failed to start. Durable audit/plan Markdown files remain available; no browser review is claimed.
- Always specify `-R sjgold/agentchattr` for GitHub reads. Implicit selection returned an unrelated upstream issue; explicit fork reads verified #1 and the 26-ticket backlog. Issue bodies still link a v1.6 snapshot; v1.7 remains the local scope authority, with the user's additive Omarchy request recorded here and in the plan.

## Ticket #2 verification and limits

- Windows-hosted Omarchy test plan supplied in `OMARCHY-TEST-PLAN.md`, with a source-only archive frozen at `3bf7da0` under ignored `.audit-tmp`. The plan uses a disposable Linux copy, distinct web/MCP ports and no agents/providers; no successful Omarchy test results received; testing is now deferred at Seth's request because of mounted filesystem issues. Seth prefers testing directly from the repo; the plan now provides terminal-only port/data overrides without editing shared config, with menu testing deferred for that route.

- Platform environments are separate; no deletion or migration of existing `.venv`/working installation. Passive checks never install packages or execute agent commands. Setup requires `SETUP` in a terminal or explicit `--setup`.
- App-specific loopback health binds checkout, host, port, data/upload paths and MCP configuration. Kernel locking serializes startup; foreign listeners are preserved; failure/timeout cleanup targets only the invocation's child. Server logs omit the browser session token.
- New tests were observed failing before implementation; additional identity/malformed-HTTP tests failed then passed after fixes. Current full suite is 173 tests, 4 platform skips. Loopback checks need permission outside this sandbox; repo-local temporary data avoids its default-temp restriction. Logs/scratch/environments are ignored.
- Real integration uses fresh data, dynamically selected web/MCP ports and no agents/providers. Two separate launcher processes reuse the owned server. Cross-process lock exclusion and concurrent first-start single-spawn behavior also pass focused tests.
- Windows `.lnk` generation/target inspection passed in ignored scratch; installer not run against the real Desktop. Linux `.desktop` content generation passed on Windows; native menu launch/setup/browser behavior is pending. Git Bash is only a shell-entry smoke test, not Linux verification.
- Browser-harness could not connect to normal Chrome. A separate `chrome-devtools-axi` test session verified rendered pre-flight, refresh and chat navigation. Screenshot inspection found inherited header styling, which was corrected; DOM check at 390px confirmed block header/no overflow. Offline emulation reloaded the browser instead of testing the in-page error state; that interaction is not claimed as verified.
- Independent review received: **PASS WITH NONBLOCKING NOTES** on `3bf7da0484f7dbe308076803efa4e7ff7aff6222`. Reviewer self-identifies as Google / Gemini 3.8 Flash (Antigravity); exact backend ID not independently attested. [Receipt](REVIEW-GEMINI-TICKET-2.md) preserves the supplied report, including independent Windows execution of 173 tests (4 skips), real-server integration and shortcut collision checks. Notes verified against source: retain Windows batch error pause (automation now explicitly documented to use Python directly), product icon deferred to #23, live browser failure/retry remains unverified. No application code changed or substantive recheck required. Seth's final sign-off is pending. Existing individual agent launchers retain upstream behavior until #3/#4; restart reconciliation remains #9. Web health does not certify agent authentication or MCP adapter readiness.

## Latest reviewer additions

- v1.7 adds a small JSON findings contract with separate parse-failure flags, individual source-file intake as plain text, and a narrow Git exception for the spec.
- User authorized pushing documentation as needed; the earlier public-push approval blocker is resolved.
- Multi-file review packets are required follow-on scope after the initial build; preserve file identity and shared packet revisions.

- Opus identified two candidate freeze paths: console-only API errors with no session timeout, and distinct CLI triggers collapsed in one poll. Source paths verified; the historical GLM incident is not proven without contemporaneous console/error evidence.
- Spec v1.7 requires a durable API result outbox, idempotent delivery, operator-selected CLI message-ID recovery, and a durable queue preserving each turn envelope. AT-21a through AT-21d exercise both freeze mechanisms and recovery provenance. No application fixes yet.

## Latest scope clarification

- v1.7 supersedes the heavyweight Tribunal requirements. AT-14 through AT-16 and AT-19 cover the lighter behavior; AT-17/18 are explicitly retired to preserve numbering. General recovery safeguards remain.

- Spec v1.7 adds explicit configurable participant capacity and per-turn recovery. Six participants must fit in one phase; configured packages larger than six must be representable.
- A lost GLM turn/participant must expose retry, recover delivered answer, replace, skip, or stop without losing completed work. Deadlines and receipt states must be visible.
- Seth reported a freeze and GLM re-submission; its root cause has not been reproduced. The source caps are verified separately. Acceptance IDs AT-01 through AT-22 remain; AT-21 now has four explicit subcases covering API failure, poll batching, result recovery, and participant loss. No implementation changes.

## Ticket execution and review

- [26 approved tickets](https://github.com/sjgold/agentchattr/issues) are published with native blocking relationships. [#1: Establish the launcher baseline](https://github.com/sjgold/agentchattr/issues/1) is closed after Meta source/plan review, documentation corrections and Seth's final sign-off. Ticket #2 passed independent review and awaits Seth's final sign-off on `codex/ticket-2-preflight`.
- First milestone: #1-8, #10-12, and #16. Includes visible stalls/retry and full six-seat capacity. Full restart reconciliation (#9) follows; Stop persistence remains mandatory in #10.
- Reviewer selection follows quota: Meta Muse 1.3, DeepSeek Flash 4.1, Grok 4.7, GLM 5.3 (user-provided labels). Use a different model family from the builder and record actual model IDs. No eligible quota means review pending, not self-approval. Human retains final sign-off.

## Next step

**Action:** Obtain Seth's final sign-off for reviewed ticket #2. On explicit shipping approval, publish/merge the reviewed branch and close #2 with its review/evidence references; do not automatically begin #3/#4. Windows-hosted Omarchy testing is deferred because its mounted filesystem is not picking up files correctly; Seth does not want troubleshooting now. Dual boot remains deferred while four lanes are active. Configuration/exit fixes belong to #4 after #2; frozen-input delivery belongs to #6 after #3/#4.
**Who:** Codex implemented and locally verified #2; Google / Gemini 3.8 Flash (Antigravity, supplied identity) independently reviewed the frozen implementation and reports executing Windows checks. Seth owns final sign-off. No Omarchy troubleshooting assigned.
**Done when:** #2 provides one supervised entry point with app-specific readiness, bounded startup, duplicate-launch reuse and actionable conflict/failure reporting, with Windows and Omarchy requirements covered by its implementation plan and verification evidence.

## Now

- **Repository:** https://github.com/sjgold/agentchattr (public fork of bcurts/agentchattr).
- **Checkout:** Documents/CodePlayground/agentchattr (local checkout).
- **Branch:** codex/ticket-2-preflight (base main `4bc8a3a`). Initial upstream baseline: d775776a30e8af4c85ea16b3caaf9c79d65cb239, "Ignore Codex idle input particles when detecting activity".
- **Remotes:** origin = sjgold/agentchattr; upstream = bcurts/agentchattr.
- **Current build:** shared bootstrap, pre-flight API/page, Windows shortcut installer and Linux/Omarchy menu installer implemented. Dependencies installed only in ignored `.venv-windows`; no agents/providers launched. Full suite: 173 tests run, OK with 4 Unix/tmux skips. Real isolated startup, two separate relaunches, token enforcement and token-free supervised logging passed. Browser: ten agent cards, Refresh, Open chat and 390px no-overflow checks passed using an isolated Chrome session; test server/session stopped. Shell syntax and Git Bash passive entry point passed; native Linux/Omarchy runtime remains unverified.
- **Ignore-rule note:** upstream ignores docs contents. Narrow exceptions allow the spec, baseline audit and dated Stage A plan; scratch audit data and local Lavish review surfaces are ignored. Other docs contents remain ignored.
- **Documentation:** spec v1.7, root agent instructions, baseline audit/evidence/scripts, bounded Stage A plan, this status file, and the dated Codex handoff. Application source contains independently reviewed ticket #2 changes; later changes are documentation only.
- **Existing installation:** Desktop/agentchattr-0.5.0 (original installation) remains intact. Runtime history, credentials, environments, and local settings were not copied.
- **In flight:** Ticket #1 complete and closed; ticket #2 independently reviewed with nonblocking notes, not signed off or closed. Local feature branch only; code frozen at `3bf7da0484f7dbe308076803efa4e7ff7aff6222`; no push or implementation PR. Seat/package launch controls remain in #3/#4; #2 performs passive executable discovery only. Review guide: `TICKET-2-REVIEW.md`; user launch instructions: `LAUNCHER.md`.
- **Verified creation:** fork exists; origin/upstream configured; source checkout was clean before these documentation additions. Current upstream includes archive.py; the old installation's missing export dependency must not be filed as an upstream defect without reproduction.
- **Upstream activity correction:** earlier web pages were cached. The new checkout is ahead of the July release commit previously shown; do not describe upstream as abandoned based on that earlier lookup.

### Agreed product direction

- One app replacing the separate everyday Warroom and Tribunal experiences, without deleting or migrating either project's records implicitly.
- Pre-flight detects environment, selects/saves agent packages and client/provider/model/reasoning settings, launches agents, and opens the existing chat page.
- Session creation remains in chat through Ask / Design a session. A selected coordinator defines teams, roles, and rounds; the user can edit its proposal. No fixed example flow.
- Reliable Stop/correct/restart, stable document delivery, explicit mentions overriding selected recipient buttons, and channel archive.
- Coordinator-requested artifacts, in-app Markdown reading/revisions, and optional actual-round transcript export.
- Optional independent review preserves Tribunal's spirit: fresh API first passes without history/peer answers, string-matched quote flags, and serious findings visible alongside synthesis. No Tribunal code import, repair loops, voting rules, derived verdicts, CLI isolation machinery, or separate checkpoint policy.

### Evidence carried forward

- Claude, Codex, Antigravity, GLM, Muse, and DeepSeek demonstrably participated in the October 9 review. Do not reclassify them as entirely unproven.
- OMP/Hermes commands were found in the old installation's environment; five isolated configuration tests passed. Full agentchattr round operation remains unverified. Tribunal records prior OMP-driven runs through a different path.
- Old-source audit found API session prompts discarded, limited recent-message context, no actual cancellation on End Session, premature turn advancement, additive recipient mentions, fragile launcher startup, swallowed CLI exit codes, and unsafe malformed JSON replacement. Recheck against this baseline before fixing.
- No live provider acceptance was performed in this project. Configuration tests and mocked checks are not an end-to-end pass.

## After that

1. **Stage A:** baseline comparison, bounded adapter diagnosis, and verified generic fixes.
2. **Stage B:** bootstrap/pre-flight, saved model-configured packages, explicit turn ownership, Stop/correct/restart. First usable milestone.
3. **Stage C:** file intake/document packets, recipient behavior, channel archive, backup export verification.
4. **Stage D:** requested artifacts, viewer/revisions, exact transcript exports, everyday-use release.
5. **Stage E:** lightweight independent review and quote checks; replace the chosen daily workflow without claiming full Tribunal feature parity.

Build preference: Sol for the next steps. Tickets #7-14 and #24 flag optional Astra escalation for unresolved correctness disagreement or reproduced failures; ask the user to bring Astra in with an evidence pack. Astra is not required upfront and does not replace cross-model final review.

## Waiting on Seth

- Final sign-off for #2; implementation review is complete with no blocking findings. Windows-hosted Omarchy testing is deferred due to mounted filesystem problems at Seth's request, with no troubleshooting now; native dual boot is also deferred. #1 received final sign-off.
- Later: select the live-test agent/model package and authorize usage-consuming acceptance when ready.
- No Tribunal code reuse or release-terms decision is needed for the agreed behavioral implementation.

## Not doing

- Editing the working Desktop installation or copying its secrets/history into the fork.
- Starting agents or calling providers during ticket #2 passive checks.
- Treating six example rounds as a mandatory workflow or moving session design into pre-flight.
- Public PR submission, deployment, or old-project retirement during bootstrap.
- Calling a client ready merely because its executable or batch file exists.
