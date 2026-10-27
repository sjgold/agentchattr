# STATUS - AGENTCHATTR

**Updated:** 2026-10-27 01:40 CDT. Pre-flight retry/Leave out fixes tested; reviewer pass requested before relying on ownership refresh.

**North Star, Seth's words:** "my initial scope was to remove the need to launch and maintain a ton of batch files that a screen for pre-flight to choose what agents could be used select the configuation and then it went to the chat page".

- Each ticket names the part of that goal it serves and an effort budget. Exceeding the budget, or encountering an untraceable gate, stops work for steering under Needs Seth.
- Acceptance gates cite a spec location or Seth quote; otherwise they are advisory. The unsourced270ms target was withdrawn.
- A milestone is done only after Seth has seen it work end to end. Reviewer/code-path acceptance is recorded separately.

## Now

Documentation cleanup is accepted. Seven seats are running, including OMP (90B managed document read/download exact). Antigravity's real managed document now passes63B read/download exact after clearing two first-run notices and switching the owned CLI from research-only Plan to Auto mode. Normal Google login was already present; the startup error log was not evidence of missing login.

The real Windows launcher reuse path, Pre-flight package editor/save/launch and Open chat path were exercised. Live sender labels are friendly (zero raw managed ids in sender elements). Reviewed UI commits08b1f0a/a8f624c/c6930b0 and0078e74 are integrated: visible Seats & launch link, clearer pre-flight flow, lighter help and usable menus.The first merge passed119 focused tests; the follow-up passed69. Launch team and open chat was exercised with7/7 ready seats. Seth's own end-to-end acceptance remains open.

## Needs Seth

- [ ] Beyond the raw agent names, what else looked wrong on the main chat screen? Naming is implemented/tested and is visible on the running instance.

- [ ] Decide later whether in-UI provider/template setup, credential entry, live model discovery belong in scope. These setup features are absent today; launch-and-go-chat is now implemented and exercised.

## Seats

|Seat|Model|Current check/status|
|---|---|---|
|Claude|claude-opus-5-5|Running; native OAuth hello passed. Earlier Haiku document124B exact; no Opus document loop|
|Codex|gpt-6.1-sol|Running; native OAuth hello passed; isolated MCP launch fixed. No Sol document loop|
|Antigravity|gemini-3.8-flash-medium, effort medium|Running; managed Documents63B read/download exact. Prior timeout/cancellation retained; CLI model remains unverified in API metadata|
|DeepSeek|deepseek-flash|Running; Documents create/read/download100B exact.1070 not mapped by provider list|
|GLM|glm-5.3|Running; earlier Documents285B exact, no extra call|
|Muse|muse-spark-1.3-contributor|Running; Documents81B exact. Hello needed512-token probe cap; normal document path worked unchanged|
|Hermes|Normal HERMES_HOME authorized|YAML adapter needs temporary-fixture tests and review before any real-home write|
|OMP|openai-codex/gpt-6.1-sol|Running; managed Documents90B read/download exact; model unverified in API metadata|

## Next

1. Fix pre-flight restart dead ends and forgotten Leave out choices, preserving ownership checks.
2. Build/test Hermes YAML support on temporary homes. Reviewer approval before any real-home write, then one tiny request with the existing login.
3. Ticket23 MultiPackets plan only, then authorized Ticket21 and22.24-26 remain uncleared.
4. Final activation review and regression before publication. Push requires Seth's explicit go-ahead.

## UAT

Chat: http://127.0.0.1:49949. Direct Pre-flight: http://127.0.0.1:49949/preflight. Stop only this instance from the active worktree with `.audit-tmp/stop-ticket20-uat.ps1`.

The distinct Antigravity `agentchattr-uat` global MCP entry is currently active for the running seat. It was backed up and structurally verified as the only new entry; the stop hook removes it and checks the remaining structure against the backup. Earlier removal was exercised successfully. Global trustedFolders was untouched. Exact backup hash/path and restore/removal instructions are in the [historical handoff](docs/history/STATUS-2026-10-26.md#requested-seats-final-nightly-verification) and private `.audit-tmp/ticket20-seat-morning.md`. MiMo parked; MiniMax not used.

## Seth's decisions and execution order

- "code is not frozen features are.. ;)": small existing-feature defects may be fixed; new scope stays bounded.
- "id never needed phone width this is an internal only tool... speed is open as well as long as agents are not taking forever it should be fine": phone-width and numeric screen work were dropped. Historical270/216ms gates are withdrawn; existing1s basic ceiling remains. Safety/auth/idempotency/provenance are unchanged.
- "what we should have available is Claude, Codex, Antigravity, Deepseek, GLM, Muse": these six are the morning target.
- "so priority is the 6 > the 2 > MultiPackets > 21-22 >23+ how ever you want to run that is fine as long as the 6+2 happen before morning": finish or explicitly skip the six and Hermes/OMP with a cause. Then source-grounded Ticket23 multi-file plan only; no23 code before scope confirmation. Ticket21/22 are authorized afterward.24-26 remain uncleared.
- "i do need doc cleanup tonight": execute the approved110-doc map, preserve everything, no deletions. It takes priority while in progress.
- "Yes to 21 and 22 after Hermes/OMP. Keep 23 and 24-26 as separate decisions.": authorization is recorded; later priority moves MultiPackets planning ahead of21/22. Transcript has not been implemented.
- MiMo: "leave out mimo this has some investigation i need to do and i cant do it right now". No MiMo credential search or setup.
- 2026-10-27 01:37 CDT: Seth: "so we dont split brain hermes use my normal home". Normal HERMES_HOME is authorized with a distinct agentchattr-uat YAML entry, backup, structural diff and exact-entry removal at stop. Adapter review precedes the first real write.
- No push/publication without Seth's explicit go-ahead. No deletions. No Fable/helper calls. No new keys. Global writes require the approved backup/distinct-entry/structural-diff/removal protocol and Seth's permission.

Next owner: Codex handles pre-flight restart defects, then the reviewed Hermes adapter. Focused regressions and reviewed real-home config changes are the completion criteria.

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

Live handoff details: actual windows/start.bat with isolated data/uploads/MCP flags exited0 and returned /preflight by reusing the matching owned instance (not a new cold-server bootstrap). In the actual editor, selected the six-seat package, changed AGY display name, saved, included all six, launched/reused them and opened chat. MiniMax removed from isolated config and saved package; initial stale unused row caused one startup refusal and was backed up/repaired, not a product-data migration. Current native AGY console shows Google AI Pro, Gemini3.8 Flash(Medium); two onboarding notices were dismissed, current mode is Auto. One new document request fulfilled,63B exact, SHAea55a480c1dfc31ff396d8b5a82752935bc1002821dab72c88444fec973f1b3a; API correctly reports cli_model_unverified. No new Opus/Sol call.

UI merge verification: exact reviewed tipc6930b0 (08b1f0a,a8f624c,c6930b0), auto-merged while preserving canonical-label fixes. Naming/preflight/help/artifact UI/restart/source-builder/identity/operator-route119 PASS7.430s. One previously noted HTTPError404 ResourceWarning remains. The separate UI worktree instance is http://127.0.0.1:49960/preflight; primary integrated handoff is49949/preflight. Later moving-branch commits are not included. No push.

### 2026-10-27 01:37 CDT UI follow-up and dashboard correction

Reviewed UI pin0078e74 is merged at0e985ad;69 focused tests passed in6.330s. The merge committed before its STATUS update because Python timezone data was unavailable. This follow-up records the result using the Windows Central timezone. No runtime/backend changes in the UI merge. No push.

### 2026-10-27 01:40 CDT Pre-flight restart defects

Observed reds: a cold manager forgot the saved CLI omission, and Retry rejected a CLI whose worker/client exit had become provable after startup. Explicit Launch/Retry now refreshes existing runtime reconciliation before applying the unchanged launch guard. Uncertain/live/missing evidence still blocks. This cannot make a truly unproven child exit safe; that case remains blocked for ownership recovery.

Cold package status restores only saved omitted-seat checkbox choices for the exact current package revision. It restores no selection id, readiness, process handle or launch authority. Changed packages ignore old choices.61 package-launch/receipt/runtime-adoption/ownership/pre-flight UI tests pass in7.112s. No live seats restarted; ownership-related delta goes to reviewer before live use. Next: reviewed Hermes YAML adapter on temporary homes, real write only after explicit reviewer clearance.
