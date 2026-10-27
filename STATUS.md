# STATUS - AGENTCHATTR

**Updated:** 2026-10-27. Documentation cleanup in verification; UAT remains running.

**North Star, Seth's words:** "my initial scope was to remove the need to launch and maintain a ton of batch files that a screen for pre-flight to choose what agents could be used select the configuation and then it went to the chat page".

- Each ticket names the part of that goal it serves and an effort budget. Exceeding the budget, or encountering an untraceable gate, stops work for steering under Needs Seth.
- Acceptance gates cite a spec location or Seth quote; otherwise they are advisory. The unsourced270ms target was withdrawn.
- A milestone is done only after Seth has seen it work end to end. Reviewer/code-path acceptance is recorded separately.

## Now

Documentation cleanup completed and reviewer-accepted on the retained full-run plus focused-correction evidence:110 byte-identical moves, repaired links and the full historical STATUS snapshot. Ticket20 remains reviewer-accepted. Naming correction implemented/tested, awaiting live server refresh. Five UAT seats are running; Antigravity's native login works but its managed launch needs an environment/config check.

## Needs Seth

- [ ] Beyond the raw agent names, what else looked wrong on the main chat screen? Naming is implemented/tested and will appear after the owned server refresh.

- [ ] Decide later whether in-UI provider/template setup, credential entry, live model discovery and launch-and-go-chat belong in scope. They are absent today and are not being built tonight.

## Seats

|Seat|Model|Current check/status|
|---|---|---|
|Claude|claude-opus-5-5|Running; native OAuth hello passed. Earlier Haiku document124B exact; no Opus document loop|
|Codex|gpt-6.1-sol|Running; native OAuth hello passed; isolated MCP launch fixed. No Sol document loop|
|Antigravity|gemini-3.8-flash-medium, effort medium|Native hellos pass; managed document timed out/cancelled. Seat stopped; env/config investigation next, normal login confirmed by Seth|
|DeepSeek|deepseek-flash|Running; Documents create/read/download100B exact.1070 not mapped by provider list|
|GLM|glm-5.3|Running; earlier Documents285B exact, no extra call|
|Muse|muse-spark-1.3-contributor|Running; Documents81B exact. Hello needed512-token probe cap; normal document path worked unchanged|
|Hermes|Not investigated yet|Next after the six; existing-login/config-only investigation first|
|OMP|Not investigated yet|Next after the six; existing-login/config-only investigation first|

## Next

1. Live-check the tested naming correction after the owned server refresh; canonical routing IDs remain unchanged.
2. Exercise real isolated start -> Pre-flight -> saved six-seat package -> launch -> Open chat. Diagnose managed agy environment within that flow; normal login is already confirmed by Seth.
3. UI is part of the handoff and outranks Hermes/OMP: integrate the separate Opus UI branch only after reviewer clearance, then run focused UI checks. That agent owns Pre-flight/help/header-link layout; no overlapping edits here.
4. Hermes/OMP CLI seats afterward if easy; otherwise explicit skip/cause. Existing logins only, time-boxed investigation first.
5. Ticket23 MultiPackets plan only (scope confirmation before code), then authorized Ticket21 and22.24-26 remain uncleared.
6. Final activation-state review and full regression before any publication; push requires Seth's explicit go-ahead.

## UAT

Chat: http://127.0.0.1:49949. Direct Pre-flight: http://127.0.0.1:49949/preflight. Stop only this instance from the active worktree with `.audit-tmp/stop-ticket20-uat.ps1`.

The distinct Antigravity `agentchattr-uat` global MCP entry was backed up, added alone, then removed; remaining structure equals backup. Global trustedFolders was untouched. Exact backup hash/path and restore/removal instructions are in the [historical handoff](docs/history/STATUS-2026-10-26.md#requested-seats-final-nightly-verification) and private `.audit-tmp/ticket20-seat-morning.md`. MiMo parked; MiniMax not used.

## Seth's decisions and execution order

- "code is not frozen features are.. ;)": small existing-feature defects may be fixed; new scope stays bounded.
- "id never needed phone width this is an internal only tool... speed is open as well as long as agents are not taking forever it should be fine": phone-width and numeric screen work were dropped. Historical270/216ms gates are withdrawn; existing1s basic ceiling remains. Safety/auth/idempotency/provenance are unchanged.
- "what we should have available is Claude, Codex, Antigravity, Deepseek, GLM, Muse": these six are the morning target.
- "so priority is the 6 > the 2 > MultiPackets > 21-22 >23+ how ever you want to run that is fine as long as the 6+2 happen before morning": finish or explicitly skip the six and Hermes/OMP with a cause. Then source-grounded Ticket23 multi-file plan only; no23 code before scope confirmation. Ticket21/22 are authorized afterward.24-26 remain uncleared.
- "i do need doc cleanup tonight": execute the approved110-doc map, preserve everything, no deletions. It takes priority while in progress.
- "Yes to 21 and 22 after Hermes/OMP. Keep 23 and 24-26 as separate decisions.": authorization is recorded; later priority moves MultiPackets planning ahead of21/22. Transcript has not been implemented.
- MiMo: "leave out mimo this has some investigation i need to do and i cant do it right now". No MiMo credential search or setup.
- No push/publication without Seth's explicit go-ahead. No deletions. No Fable/helper calls. No new keys. Global writes require the approved backup/distinct-entry/structural-diff/removal protocol and Seth's permission.

Next owner: Codex finishes cleanup checks and sends the cleanup pins to the reviewer. Then read-only managed-agy environment comparison, followed by time-boxed Hermes/OMP investigation. Small launch/config fixes only; otherwise record exact skips. Send status before starting21.23 implementation and24-26 remain held.

## Verification and limits

- Frozen root discovery:1936 tests,13 disclosed skips (9 pending transcript +4 existing),398.132s, OK. Activation:112 focused builder and112 independent reviewer tests pass.
- UI fixes:40 tests pass,63/63 mutation checks killed. Live Claude/GLM read/download exact; DeepSeek/Muse light document checks exact. No new expensive Opus/Sol document calls.
- Final provider handoff exports:44 files scanned clean against used authorized API credentials and owned tokens/nonces. The owned server is deliberately active, not cleanup-complete.
- Prior R2/D4 timing misses, instrument-invalid attempts, host stalls and final190-observation PASS remain [retained history](docs/tickets/20/history/TICKET-20-D4-FINAL-GATE.md). Full refs remain in the index, historically about293KB per fulfilled max-source request; R3 compaction is deferred. The old128/512KiB quota was withdrawn.
- Browser harness is partial; no phone-width requirement or further harness work. Reviewer visibly exercised both original live paths. Seth's UAT verdict remains open.
- Non-blocking notes: first-use CLI workspace trust; CLI-path actual model confirmation unavailable; raw IDs/old duplicate labels/queue badge/departure lines; earlier cancelled/refused requests retained. The Desktop/agentchatrr reference path was absent on this host.
- Cleanup checks/results are recorded below as they finish. Tests and live UAT must remain intact.

## Where things live

- [Documentation index](docs/README.md)
- [Current specification](docs/agentchattr-fork-spec.md), with [reduced release contract](docs/tickets/20/TICKET-20-22-REDUCED-RELEASE.md)
- [Cleanup plan and exact move map](docs/plans/2026-10-26-delivery-file-cleanup.md)
- [Complete pre-cleanup STATUS snapshot](docs/history/STATUS-2026-10-26.md), historical guidance preserved verbatim apart from live link destinations
- [Ticket20 contracts](docs/tickets/20/contracts/TICKET-20-CONTRACT.md) and [accepted production record](docs/tickets/20/TICKET-20-REDUCED-PRODUCTION.md)

Active branch: `codex/ticket-20-r2-on-a1`, worktree `C:/Users/SJG/.traycer/worktrees/sjgold__agentchattr/codex-ticket-20-r2-on-a1`. The main-checkout `codex/ticket-20-artifacts` WIP is superseded for product work. Other branches are preserved and must rebase/resolve moved documentation before integration.

Accepted R2+D4 unit:2c34bbfb..220f3400. Those review pins refer to historical root paths, preserved in Git and the moved receipts. No history rewrite or branch deletion.

AGENTS.md names `status.md`, while the tracked entry is `STATUS.md`; casing remains unchanged. AGENTS.md is untouched. External Traycer artifact paths/comments stay in place; repository links are refreshed separately.

## Cleanup verification

Pure rename commit9fc6a4d contains exactly110 R100 entries. Baseline573 tracked files ->576, with only docs/README.md, historical STATUS snapshot and tools/check_markdown_links.py added. All215 fenced blocks unchanged;397 pre-existing code/tests/tools/static/AGENTS files byte-identical; zero case collisions; longest moved path143 characters; links0 broken before/after. Release build smoke includes README (archive output redirected into scratch). Localhost49949 still listening. Focused guide/backend, artifact selection and one full discovery are next on this frozen cleanup source; no result claimed yet.

Cleanup regression update:88 focused tests pass. Artifact selection559 ran with9 explicit pending-transcript skips and one stale pre-activation expectation in test_artifact_capability_recovery (expected empty capabilities, actual reviewed artifact-v1). Product unchanged. Corrected that one test expectation in a separate test-only activation follow-up; retained all recovery/legacy assertions. Full discovery had not started, so the single full run follows this correction.

Cleanup acceptance: full1939 ran404.096s with13 disclosed skips and4 subtest failures from one remaining pre-activation fresh-launch assertion. Corrected only that literal/comment; entire protocol-upgrade/capability/capability-recovery/workers/admission/operator core+routes80 PASS20.843s. Reviewer accepts combined evidence, no repeat full run now; final full run remains required before publication. Both failed runs remain recorded. Static sweep26 hits across10 files: remaining expectations are explicit disabled/denied/old/imported fixtures, plus historical browser harness source guards retained at their original pre-activation pin. Those tools are not current acceptance and were not weakened. No product code changed in the activation-test follow-ups.

Naming fix: durable retained-identity labels plus saved-package family aliases are exposed as display-only WebSocket metadata. Chat/join/leave, session cast/design/owner/proposer and Documents author text use the label; role/action values retain canonical IDs. Three new tests first showed missing-seam/Node reds, then passed; the raw-render mutation produces a genuine assertion failure. Focused naming/UI/restart/identity/operator-route86 PASS5.968s; UI mutation63/63 killed; Node syntax checks pass. One existing HTTPError404 ResourceWarning appeared in the identity suite and is retained, not silently fixed. Product change is display-only; no authority/queue/store invariant change.

Naming review correction: reviewer found3 Request Changes onclick arguments had received display labels. A new Node test executes Request Changes -> Send for both draft-card variants; observed red sent @Agy Friendly instead of the canonical id. Restored canonical proposedBy in all3 action sites while keeping visible labels and card.dataset.proposedBy. Naming/UI/restart45 PASS2.918s; Node syntax passes. The initial regression is retained here rather than described as unchanged routing throughout. Live server refresh still pending the isolated launch flow.
