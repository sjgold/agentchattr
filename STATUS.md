# STATUS - AGENTCHATTR

**Updated:** 2026-10-18 (ticket #3 passed independent Antigravity review with nonblocking notes; human sign-off received; publication in progress)

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
- Independent review received: **PASS WITH NONBLOCKING NOTES** on `3bf7da0484f7dbe308076803efa4e7ff7aff6222`. Reviewer self-identifies as Google / Gemini 3.8 Flash (Antigravity); exact backend ID not independently attested. [Receipt](REVIEW-GEMINI-TICKET-2.md) preserves the supplied report, including independent Windows execution of 173 tests (4 skips), real-server integration and shortcut collision checks. Notes verified against source: retain Windows batch error pause (automation now explicitly documented to use Python directly), product icon deferred to #23, live browser failure/retry remains unverified. No application code changed or substantive recheck required. Seth gave final sign-off and authorized push/merge on 2026-10-12 ("im good with it push merge"). Existing individual agent launchers retain upstream behavior until #3/#4; restart reconciliation remains #9. Web health does not certify agent authentication or MCP adapter readiness.

## Ticket #3 implementation and evidence

- Seth authorized #3 on 2026-10-15. Implemented saved API-seat packages, provider-template/model/reasoning validation, secret references only, immutable launch snapshots, app-owned wrapper attempts, and authenticated pre-flight save/launch/restart/stop controls. Two seats may share one configured provider with different models. Manual IDs remain unverified; Provider default omits model, and unsupported settings fail validation.
- Requested model reaches the actual managed request payload; confirmed model is recorded only from the response. Launch proves chat-adapter connection without provider calls; authentication remains unknown until a successful completion. Missing credentials produce a user-action state. Saved edits do not change active runtime settings; mismatches require explicit restart. Removing a live seat requires targeted stop first.
- Builder verification: **198 tests run, OK, 4 Unix/tmux skips**. Nine configuration/payload/storage tests, fourteen runtime tests, and pre-flight authentication/origin/schema tests cover the new behavior. New tests were observed failing before implementation/fixes. Local fake-HTTP tests verify payload and response model identity separately. JavaScript syntax and diff whitespace checks pass.
- End-to-end fake-provider integration uses two actual wrappers, isolated data and web/MCP ports. It verifies zero provider calls on launch, credential-reference resolution, selected model/reasoning, evidence-based confirmation, matching reuse, mismatch rejection, 401 action-needed state, targeted restart/retry/stop and actual-worker stop acknowledgement. Five final consecutive runs passed. No live external providers or usage-consuming acceptance calls.
- Investigation found a Windows receipt replacement race (WinError 5 while a reader holds the destination). Bounded transient retries fix it; permanent errors preserve the previous file. Actual-worker stop acknowledgement was added rather than relying on supervisor state. A final inventory found no surviving isolated fake-server processes. Earlier failing runs are not counted as acceptance passes.
- Browser verified loading/saving a two-seat package, launching a stopped fake seat to ready, targeted stop leaving its peer ready, controls reenabled and no overflow at 390px. Screenshot tool did not return a saved path, so no visual screenshot inspection is claimed. Last-adapter-check label was added after those interaction checks; its status field is covered in runtime output. Narrow design-hook suppressions are persisted for preflight.html: no glow declarations exist in its page source/CSS; Inter is inherited from the existing product stylesheet (style.css:126), so it is retained for product consistency. The post-freeze font disposition changes detector metadata/documentation only, not application code.
- Runtime currently supports IPv4 loopback only, with explicit rejection of IPv6-only server configuration. Native Linux/Omarchy and real-provider compatibility remain unverified/deferred. Full restart reconciliation (#9), durable turn delivery/outbox and per-turn cancellation remain later scope. Stopping a local wrapper does not guarantee remote-provider cancellation.
- See `API-SEATS.md`, `TICKET-3-PLAN.md` and `TICKET-3-REVIEW.md`. Code frozen at `b4fd3d68b61dbcfd8420f4a3caffc11fc77cfdd6` (base main `8127ea1`). Independent Antigravity review returned PASS WITH NONBLOCKING NOTES on 2026-10-18; Seth gave final completion sign-off and explicitly authorized commit, push, merge and issue closure on 2026-10-18. Publication is in progress; #4 must remain unstarted. Repository review receipt: `REVIEW-GEMINI-TICKET-3.md`.

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

- [26 approved tickets](https://github.com/sjgold/agentchattr/issues) are published with native blocking relationships. [#1: Establish the launcher baseline](https://github.com/sjgold/agentchattr/issues/1) is closed after Meta source/plan review, documentation corrections and Seth's final sign-off. Ticket #2 passed independent review and received Seth's final sign-off; reviewed branch is fast-forward merged and published on origin/main; GitHub issue #2 is confirmed closed as completed.
- First milestone: #1-8, #10-12, and #16. Includes visible stalls/retry and full six-seat capacity. Full restart reconciliation (#9) follows; Stop persistence remains mandatory in #10.
- Reviewer selection follows quota: Meta Muse 1.3, DeepSeek Flash 4.1, Grok 4.7, GLM 5.3 (user-provided labels). Use a different model family from the builder and record actual model IDs. No eligible quota means review pending, not self-approval. Human retains final sign-off.

## Next step

**Action:** Complete the authorized ticket #3 publication: commit review/sign-off status, fast-forward merge into main, verify the merged tree, push and close #3. Leave #4 unstarted. Routine checks use the loopback fake provider; live acceptance requires an explicitly authorized package. Omarchy testing/troubleshooting remains deferred.
**Who:** Codex implemented and verified #3 on `codex/ticket-3-api-seat`; at Seth's explicit request, Traycer Antigravity reviewer `ec1fbcd1-4a02-410e-9029-e498f67918c8` was created with configured model `gemini-3.8-flash`, high reasoning, and local checkout/test access. The reviewer returned PASS WITH NONBLOCKING NOTES and independently reported 198 tests OK (4 platform skips), passing real-wrapper/fake-provider integration, JavaScript syntax and whitespace checks. Reviewer-configured identity: Antigravity / gemini-3.8-flash; exact underlying backend identity not independently attested. Builder backend ID is not exposed by this session; Sol was the requested preference.
**Done when:** Frozen #3 passes independent review, any substantive fixes are rechecked, and Seth gives final completion sign-off. Independent Windows test evidence is now recorded; native Linux/Omarchy and live-provider compatibility remain unverified.

## Now

- **Repository:** https://github.com/sjgold/agentchattr (public fork of bcurts/agentchattr).
- **Checkout:** Documents/CodePlayground/agentchattr (local checkout).
- **Branch:** codex/ticket-3-api-seat (base main `8127ea1`); reviewed ticket #2 fast-forward merged from `codex/ticket-2-preflight` (base `4bc8a3a`). Initial upstream baseline: d775776a30e8af4c85ea16b3caaf9c79d65cb239, "Ignore Codex idle input particles when detecting activity".
- **Remotes:** origin = sjgold/agentchattr; upstream = bcurts/agentchattr.
- **Current build:** reviewed ticket #2 plus independently reviewed ticket #3 API-seat implementation with human sign-off received; publication in progress. Full suite: 198 tests run, OK with 4 Unix/tmux skips. Five final real-wrapper/fake-provider integration runs passed with actual stop acknowledgement; browser package/save/launch/stop and 390px layout checked. Dependencies remain only in ignored `.venv-windows`. Only isolated test wrappers and fake providers were launched; no external model calls. Test servers/browser stopped; native Omarchy unverified. No provider credentials/history copied from the working Desktop installation.
- **Ignore-rule note:** upstream ignores docs contents. Narrow exceptions allow the spec, baseline audit and dated Stage A plan; scratch audit data and local Lavish review surfaces are ignored. Other docs contents remain ignored.
- **Documentation:** spec v1.7, root agent instructions, baseline audit/evidence/scripts, bounded Stage A plan, this status file, and the dated Codex handoff. Application source contains independently reviewed ticket #2 and builder-verified and independently reviewed ticket #3 changes, with human sign-off received; publication in progress.
- **Existing installation:** Desktop/agentchattr-0.5.0 (original installation) remains intact. Runtime history, credentials, environments, and local settings were not copied.
- **In flight:** #1/#2 complete and closed. #3 implemented locally on `codex/ticket-3-api-seat`, code frozen at `b4fd3d68b61dbcfd8420f4a3caffc11fc77cfdd6`, independent review passed with nonblocking notes; human sign-off and publication authorization received; push/merge/closure in progress. #4 not started. Review guide: `TICKET-3-REVIEW.md`; user instructions: `API-SEATS.md`.
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

- Antigravity reviewer `ec1fbcd1-4a02-410e-9029-e498f67918c8` has been assigned #3 through Traycer at Seth's request. Independent review is complete: PASS WITH NONBLOCKING NOTES. Seth gave final completion sign-off and publication authorization on 2026-10-18; no substantive fixes were requested. Implementation, builder checks and independent Windows verification are complete. No live acceptance package selected. Windows-hosted Omarchy testing is deferred due to mounted filesystem problems at Seth's request, with no troubleshooting now; native dual boot is also deferred. #1 received final sign-off.
- Later: select the live-test agent/model package and authorize usage-consuming acceptance when ready.
- No Tribunal code reuse or release-terms decision is needed for the agreed behavioral implementation.

## Not doing

- Editing the working Desktop installation or copying its secrets/history into the fork.
- Starting agents or calling providers during ticket #2 passive checks.
- Treating six example rounds as a mandatory workflow or moving session design into pre-flight.
- Public PR submission, deployment, or old-project retirement during bootstrap.
- Calling a client ready merely because its executable or batch file exists.
