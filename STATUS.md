# STATUS - AGENTCHATTR

**Updated:** 2026-10-22 (autonomous continuation authorized; autonomous run; #5 published/closed; #6 implemented and builder-verified, preparing AGY review)

- Maintain this file in the same push as project changes: Seth's daily-review agent collects root status documents.
- This file plus [the specification](docs/agentchattr-fork-spec.md) should be enough to resume.
- Update actual results and next steps, not intended features presented as shipped.
- Root `AGENTS.md` requires agents to read this file before work and maintain current status, verification, blockers, and the next action before handing off.
- Latest resume note: [2026-10-18 handoff](2026-10-18-SESSION-HANDOFF-gpt-6.md). The October 12 handoff describes an earlier checkpoint; use this status and the latest handoff on resume.

## Autonomous execution policy (2026-10-22)

- Seth instructed: "remove my gate and continue autonomiously same setup with the agy tester". This supersedes the October 18 instruction to leave #5 unstarted and the routine per-ticket human approval/sign-off waits in older handoffs, plans and issue snapshots.
- Continue the remaining approved backlog in dependency order, preserving the first-milestone ordering already recorded below. Codex builds; the same Antigravity reviewer/tester `ec1fbcd1-4a02-410e-9029-e498f67918c8` independently reviews frozen changes and rechecks substantive fixes. The existing test-writing agent may write tests as before; after a Claude quota failure it switched to Codex gpt-6-sol/medium. AgY remains the independent reviewer. No self-approval or lowered verification bar.
- Seth grants standing authorization within this agreed project scope to commit, merge, push and close tickets after checks and Antigravity review/recheck pass. Continue to the next eligible ticket without asking for a routine plan or completion gate. Escalate real scope decisions, destructive operations outside that authorization, live provider usage, unavailable independent verification or unresolved correctness disputes. Desktop/global credentials and deferred native Omarchy work remain outside scope.
- Durable run tracking: `AUTONOMOUS-RUN.md`. Active implementation: #5, `TICKET-5-PLAN.md`. Historical receipts keep their original approval language as dated evidence.

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
- See `API-SEATS.md`, `TICKET-3-PLAN.md` and `TICKET-3-REVIEW.md`. Code frozen at `b4fd3d68b61dbcfd8420f4a3caffc11fc77cfdd6` (base main `8127ea1`). Independent Antigravity review returned PASS WITH NONBLOCKING NOTES on 2026-10-18; Seth gave final completion sign-off and explicitly authorized commit, push, merge and issue closure on 2026-10-18. The reviewed branch was fast-forward merged and published on origin/main at `c06c0a9`; GitHub issue #3 is confirmed closed as completed. At that publication checkpoint #4 was unstarted; Seth subsequently authorized it. Post-merge verification on 2026-10-18: 198 tests OK (4 skips), real-wrapper/fake-provider integration PASS including worker stop acknowledgement and no persisted secret values, JavaScript syntax and whitespace checks PASS. Repository review receipt: `REVIEW-GEMINI-TICKET-3.md`.

## Ticket #4 implementation and verification

- Seth authorized work ("begin") and approved extending the interactive wrappers through a Traycer design question on 2026-10-18. `TICKET-4-PLAN.md` records the approach and rulings. Codex implemented; fresh Sonnet agent `fcc36344-f0ca-4514-9288-74753be75947` (configured `claude-sonnet-5`, medium) wrote config/exit regressions and the fake-CLI integration. Actual backend IDs are not independently attested.
- Saved packages now accept mixed API/CLI seats; CLI model/reasoning choices require explicit template argument contracts. Managed workers use existing Windows console or Unix tmux injection, immutable snapshots and owned targeted lifecycle controls. Native login is reused. Readiness is explicitly mention injection, with authentication/MCP tool operation/model confirmation unknown.
- JSON settings/trust writes validate shape before mutation, preserve exact-byte backups and replace atomically. Fixed settings paths have lifetime locks across managed/compatibility launches; unsafe simultaneous seats are rejected. Windows failed child status propagates; Unix uses a separate child-exit receipt and preserves unknown sessions. Shared compatibility launchers use bounded bootstrap and explicit setup. Hermes/OMP aliases require configured supported templates; no native client/YAML integration or compatibility pass is claimed.
- Full Windows suite: **228 tests, OK, 4 Unix/tmux skips**. New config/Windows exit, CLI schema/runtime, Unix ownership/child-exit and failed-worker regressions were observed failing before fixes. Sonnet ran real fake-CLI integration once successfully after correcting a test assumption about raw mention text; Codex reran with stronger failed-state/auth/model assertions and passed. Actual console keystroke injection, two distinct model/reasoning argv and MCP identities, no cross-delivery, matching reuse, changed-settings rejection, targeted restart/stop with worker acknowledgement and child exit **23** were verified. Existing real-wrapper/fake-API integration also passed. Actual Windows compatibility batch shim preserved **23**. JS syntax and whitespace checks pass.
- Browser-harness on an isolated fake-client server verified selecting CLI, saving model/reasoning, launch to ready, honest unknown auth/confirmation, targeted stop and no horizontal overflow at 390px. Screenshot `.audit-tmp/ticket4-preflight-390.png` was saved and visually inspected. Test tab/server stopped. No live provider/client calls, native Linux/Omarchy run, credential copies or Desktop changes. Full turn recovery, server-restart adoption and remote cancellation remain later scope.
- Implementation is frozen at `f933f59ca415bcbd3a2ac5fb0c2da4afe1c9d7e3`. At Seth's explicit preference, the same Antigravity reviewer used for #3 (`ec1fbcd1-4a02-410e-9029-e498f67918c8`, configured `gemini-3.8-flash`, high) received the complete #4 briefing. The Opus assignment was stopped and archived before delivery; it supplied no review. Initial review and substantive recheck both passed with nonblocking notes; Seth gave final completion sign-off and explicitly authorized push, merge and issue closure on 2026-10-18. Fast-forward merged and published on origin/main at `612c9f6`; GitHub issue #4 is confirmed closed as completed. #5 remains unstarted. Post-merge verification: 229 tests OK (4 skips), real fake-CLI and fake-API integrations PASS, JS syntax and whitespace checks PASS.

- Independent Antigravity review of `f933f59` returned **PASS WITH NONBLOCKING NOTES**, independently reporting 228 tests OK (4 skips), real fake-CLI and fake-API integrations PASS, JS/diff checks PASS. Notes: Windows batch delimiters, orphaned Unix exit receipts after SIGKILL, and existing deferred `detail()` helper coupling. Native Linux/live-client limits remain.
- Codex reproduced the delimiter note using a disposable `.cmd`: each of `alpha,beta`, `alpha;beta`, `alpha=beta` arrived as two batch parameters. A new regression failed for all three before extending the existing batch-only rejection guard. Now these fail before client spawn; native executables are unaffected. Full suite **229 tests OK (4 skips)**, real fake-CLI integration PASS (including exact exit 23 / failed), JS/diff checks PASS. The same reviewer independently passed substantive recheck of `c7ffb3b18e70c71de76df9d85ef218dca9d5b2d2`: focused regression (6 tests), full suite 229 OK (4 skips), fake-CLI and fake-API integrations, JS and whitespace checks. Final receipt: `REVIEW-GEMINI-TICKET-4.md`. Remaining nonblocking notes concern Unix receipt files after SIGKILL and existing deferred UI helper coupling. Report hash/persistence wording was corrected. MCP bearer tokens intentionally reside in private identity files; package/snapshot secret boundaries remain distinct.

## Ticket #5 implementation and verification

- Reuses #3/#4 mixed-package schema and owned seat runtime. Adds canonical saved revisions, frozen team selection receipts, whole-team launch/reuse with per-seat failures and explicit launch-only omissions, freshly checked chat handoff, remembered package ID and draft/stale-setting guards. No session, rounds or model requests are created by the handoff.
- Builder full Windows suite: **248 tests OK, 4 Unix/tmux skips**. Test-author runtime regressions and root endpoint regressions were observed failing before implementation; receipt fault/immutability checks also pass. Codex reran actual mixed fake-API/CLI integration: 3 saved seats, matching reuse, partial credential failure without stopping peers, omission-only selection ready, stale selection/revision rejection and targeted restart. **Provider calls: 0; sessions created: 0**, message/session snapshots unchanged. Existing real-wrapper/fake-API integration, JS syntax and whitespace checks pass.
- Isolated browser verified save/reload, new-tab remembered selection, missing-credential block, explicit exclusion to 2-of-2 ready, draft-edit disabling and actual checked chat navigation. 390px DOM check has no overflow; saved 390x844 PNG independently confirmed and inspected. Browser-harness required a user Chrome permission prompt, so verification used an isolated cached chrome-devtools-axi runtime without installs. Test fixtures/browser/server stopped. No live models or native Linux/Omarchy pass claimed.
- Same AgY reviewer remains mandatory; no human per-ticket approval gate. Test author failed over from rate-limited Sonnet to Codex gpt-6-sol/medium; it did not act as final reviewer. Plan: `TICKET-5-PLAN.md`; user guide: `PACKAGES.md`. Frozen implementation: `8474bb25690cc8e43d40e8b1a4ad605e4933e04e`; review guide: `TICKET-5-REVIEW.md`. Same Antigravity reviewer independently returned PASS on `8474bb25690cc8e43d40e8b1a4ad605e4933e04e`, with 248 tests OK (4 skips), actual package/fake-API integrations and static checks. Receipt: `REVIEW-GEMINI-TICKET-5.md`. No findings requiring fixes. Published on origin/main at `7575c68` and GitHub issue #5 confirmed closed as completed under standing authorization. Post-merge full suite: 248 tests OK (4 skips), JS/diff checks PASS. No human completion gate is pending.

## Ticket #6 implementation and verification

- Start freezes accepted design/cast, exact pasted source, full bounded task brief and active rules with run/input/design/rules identities. Engine phase/expected-seat/enrichment paths use frozen design. Scoped atomic per-turn brief records survive recent-chat rollover; existing prior-result IDs are included without changing completion admission (#8).
- New authenticated HTTP/MCP `chat_review_brief` retrieval is bound to the intended stable seat identity. API adapter fetches exact context before provider requests, with frozen instructions and separate untrusted source JSON; malformed/missing/wrong-seat lookup has no chat-only provider fallback. CLI receives short scoped retrieval instructions rather than pasted source or live role/rule overrides. Native client compliance remains unverified.
- Chat normal/draft Start dialogs accept pasted text and retain drafts on validation error. UTF-8 limits: task32KiB/source512KiB/rules32KiB/prior-results256KiB; reject without slicing. Existing role/phase count limits remain until #16. Source is data, never evaluated or routed as mentions by Start. Legacy sessions are not automatically migrated.
- Builder full suite **266 tests OK, 4 Unix/tmux skips**. Real isolated fake-API/actual fake-CLI integration passed: one local provider request, matching exact Unicode/CRLF/code/mentions source and revisions across distinct frozen phases after30messages/live template/rule edits; CLI retrieves via actual MCP HTTP transport; wrong-seat403, invalid brief404/no extra API call, oversized Start400/no run, source sentinel absent. Existing package regression integration and static checks pass.
- Rendered human-only Start verified source field, rejected oversized input retained in modal, successful source persisted, corrected scoped step visibility, and inspected390px dialog screenshot. Dialog width351 fits; inherited background chat header overflows to479px, so no whole-chat mobile pass is claimed. Fixture session/browser/server stopped. No live clients/providers or native Linux/Omarchy checks.
- Same AGY reviewer receives frozen implementation; review/publication not yet claimed. Test author remained test-only on configured Codex after Sonnet quota failover. Plan `TICKET-6-PLAN.md`, usage `FROZEN-REVIEWS.md`. Queue durability/outbox, completion admission, server-restart reconciliation and cancellation remain #7-10.

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
- Reviewer selection requires a different family, available quota and recorded identity. Seth explicitly preferred keeping the same Antigravity reviewer from #3 for #4; use that project preference over the generic Traycer guide's Opus default. The attempted Opus assignment was stopped/archived before delivery and supplied no review. No eligible quota means review pending, not self-approval. Human retains final sign-off.

## Next step

**Action:** Freeze and obtain same AGY independent review/recheck of #6 frozen source/design delivery using `TICKET-6-REVIEW.md`. On PASS merge/push/close under standing authorization and continue #7. No human completion gate; unapproved live usage/native Omarchy remain deferred.
**Who:** Codex builder/coordinator. Same Antigravity reviewer `ec1fbcd1-4a02-410e-9029-e498f67918c8`; test author `fcc36344-f0ca-4514-9288-74753be75947` completed tests after configured Codex gpt-6-sol/medium failover from rate-limited Sonnet.
**Done when:** Each ticket satisfies its documented criteria, tests and independent Antigravity review/recheck; it is published and closed, with status and next action recorded. Continue autonomously within the approved backlog.

## Now

- **Repository:** https://github.com/sjgold/agentchattr (public fork of bcurts/agentchattr).
- **Checkout:** Documents/CodePlayground/agentchattr (local checkout).
- **Branch:** codex/ticket-6-frozen-brief, base main `75bf639`. #1-5 published and closed; #6 is local and review pending.
- **Remotes:** origin = sjgold/agentchattr; upstream = bcurts/agentchattr.
- **Current build:** published #1-5 plus local #6 frozen review context implementation, builder-verified with 266 tests OK (4 platform skips), real fake-API-to-fake-CLI/MCP delivery and package regression integration. Exact source survives30messages/live template-rule edits; wrong-seat/invalid context rejected and source not executed. Rendered input/error/Start dialog verified; inherited background chat header remains a mobile limitation. Same AGY review pending. No live providers/native Omarchy or Desktop changes.
- **Ignore-rule note:** upstream ignores docs contents. Narrow exceptions allow the spec, baseline audit and dated Stage A plan; scratch audit data and local Lavish review surfaces are ignored. Other docs contents remain ignored.
- **Documentation:** spec v1.7, prior baseline/Stage A evidence and review receipts; #4 plan `TICKET-4-PLAN.md`, user guide `CLI-SEATS.md` and review briefing `TICKET-4-REVIEW.md`. Reviewed/rechecked #4 application implementation is approved and published on origin/main; final review receipt: `REVIEW-GEMINI-TICKET-4.md`.
- **Existing installation:** Desktop/agentchattr-0.5.0 (original installation) remains intact. Runtime history, credentials, environments, and local settings were not copied.
- **In flight:** #6 frozen brief delivery implemented and builder-verified; independent same-AGY review pending. #1-5 completed/published/closed. Autonomous pipeline remains active; no human sign-off gate.
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

- Routine ticket approval gates removed by Seth on 2026-10-22. Only unresolved scope/authorization or independent-verification blockers need user input. Live acceptance and native Omarchy testing remain deferred.
- Later: select the live-test agent/model package and authorize usage-consuming acceptance when ready.
- No Tribunal code reuse or release-terms decision is needed for the agreed behavioral implementation.

## Not doing

- Editing the working Desktop installation or copying its secrets/history into the fork.
- Starting agents or calling providers during ticket #2 passive checks.
- Treating six example rounds as a mandatory workflow or moving session design into pre-flight.
- Public PR submission, deployment, or old-project retirement during bootstrap.
- Calling a client ready merely because its executable or batch file exists.
