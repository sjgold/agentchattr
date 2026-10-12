# STATUS - AGENTCHATTR

**Updated:** 2026-10-12 (ticket #1 baseline audit and Stage A plan written; independent review pending; no application implementation)

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
- Seth selected Meta as the quota-eligible different-family reviewer and will handle the handoff. [Self-contained Meta review pack](META-REVIEW-HANDOFF.md) is prepared. Installed configuration names `muse-spark-1.3-contributor`; actual reviewer response identity remains to be recorded. No Meta MCP alias is exposed and `META_API_KEY` is absent from this session's environment, so no direct model call was made and no secret file was read. Review target is the Git commit containing this checkpoint (resolve with `git log -1 --format=%H -- META-REVIEW-HANDOFF.md`). Review pending; issue #1 remains open; human retains final completion sign-off.
- Optional Lavish review surface was generated using the product's design tokens, but its local server failed to start. Durable audit/plan Markdown files remain available; no browser review is claimed.
- Always specify `-R sjgold/agentchattr` for GitHub reads. Implicit selection returned an unrelated upstream issue; explicit fork reads verified #1 and the 26-ticket backlog. Issue bodies still link a v1.6 snapshot; v1.7 remains the local scope authority, with the user's additive Omarchy request recorded here and in the plan.

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

- [26 approved tickets](https://github.com/sjgold/agentchattr/issues) are published with native blocking relationships. [#1: Establish the launcher baseline](https://github.com/sjgold/agentchattr/issues/1) has a local audit/plan checkpoint awaiting freeze and independent review. No application builder or independent reviewer has been launched.
- First milestone: #1-8, #10-12, and #16. Includes visible stalls/retry and full six-seat capacity. Full restart reconciliation (#9) follows; Stop persistence remains mandatory in #10.
- Reviewer selection follows quota: Meta Muse 1.3, DeepSeek Flash 4.1, Grok 4.7, GLM 5.3 (user-provided labels). Use a different model family from the builder and record actual model IDs. No eligible quota means review pending, not self-approval. Human retains final sign-off.

## Next step

**Action:** Seth sends `META-REVIEW-HANDOFF.md` to Meta and brings back its review. Address/recheck substantive findings against the frozen ticket #1 checkpoint, then obtain human sign-off. Afterward start issue #2 (Open pre-flight from one shortcut). Configuration/exit fixes belong to #4 after #2; frozen-input delivery belongs to #6 after #3/#4. Include the user's Omarchy requirements in #2-#4.
**Who:** Current Codex session produced the audit/plan; Seth owns the Meta handoff. User requested Luna at Max for this work; exact backend model ID/settings are not exposed and were not inferred. Meta is selected for independent review; actual reviewer identity/outcome awaits its response. Sol remains the recorded preference for subsequent implementation.
**Done when:** The frozen baseline pack has an independent review outcome, substantive fixes are rechecked, human signs off #1, and #2 is ready to start with its bounded scope.

## Now

- **Repository:** https://github.com/sjgold/agentchattr (public fork of bcurts/agentchattr).
- **Checkout:** Documents/CodePlayground/agentchattr (local checkout).
- **Branch:** main. Initial upstream baseline: d775776a30e8af4c85ea16b3caaf9c79d65cb239, "Ignore Codex idle input particles when detecting activity".
- **Remotes:** origin = sjgold/agentchattr; upstream = bcurts/agentchattr.
- **Current build:** unchanged upstream application source, verified against the pinned baseline. No dependencies installed or agents launched. Offline audit and eight existing MCP config tests passed; no complete application or live acceptance pass.
- **Ignore-rule note:** upstream ignores docs contents. Narrow exceptions allow the spec, baseline audit and dated Stage A plan; scratch audit data and local Lavish review surfaces are ignored. Other docs contents remain ignored.
- **Documentation:** spec v1.7, root agent instructions, baseline audit/evidence/scripts, bounded Stage A plan, this status file, and the dated Codex handoff. Application source remains at the raw upstream baseline.
- **Existing installation:** Desktop/agentchattr-0.5.0 (original installation) remains intact. Runtime history, credentials, environments, and local settings were not copied.
- **In flight:** Ticket #1 audit/plan checkpoint, independent review pending. No application implementation PR.
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

- Send the prepared Meta handoff and return its review/model identity. Human final sign-off remains required after substantive findings are addressed and rechecked.
- Later: select the live-test agent/model package and authorize usage-consuming acceptance when ready.
- No Tribunal code reuse or release-terms decision is needed for the agreed behavioral implementation.

## Not doing

- Editing the working Desktop installation or copying its secrets/history into the fork.
- Installing dependencies or starting agents as part of repository creation.
- Treating six example rounds as a mandatory workflow or moving session design into pre-flight.
- Public PR submission, deployment, or old-project retirement during bootstrap.
- Calling a client ready merely because its executable or batch file exists.
