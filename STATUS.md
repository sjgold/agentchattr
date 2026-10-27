# STATUS - AGENTCHATTR

**Updated:** 2026-10-27 04:34 CDT. RC1 handoff accepted. Corrected adapter cleanup is integration-only,285 focused tests pass; frozen UAT builds stay unchanged.

**START HERE (Seth)**
1. Open RC1: http://127.0.0.1:50010/preflight.
2. Check the six-seat team, then click Launch team and open chat (reuse is fine).
3. In chat, use Documents: pick a completed source session, request a short document, then Read/Download.
4. Try Start a session -> Choose UTF-8 files for the multi-file preview; starting a review uses the selected agents.
5. For Antigravity use RC0: http://127.0.0.1:49949/preflight. RC1 leaves AGY and Hermes out.
6. Decisions: keep Hermes deferred or discuss process61816; review the security rotation note; the app continues to start at Pre-flight.


**UAT RC0:** `99361d1776187571a63ba9feb4af140fb629ff8a`, http://127.0.0.1:49949/preflight. **Frozen: no merges reach this build.**
Stop only RC0: `.audit-tmp/artifact-ui-rc0-_om1o8fc/checkout/.audit-tmp/stop-rc0.ps1` from this integration worktree.
RC0 excludes Hermes adapter, default_model fallback, Ticket23, the seven new UI ideas and daily AGY injection. They remain integration/RC1 work.

**UAT RC1:** `fdc6c275edb8d81f387c782aaeaf27a4e216816a`, http://127.0.0.1:50010/preflight. **Frozen: no merges reach this build.** Adds multi-file packets, effective CLI model defaults and reviewed UI ideas. Six seats ready; Claude is Haiku5.5 for the bounded check, while RC0 keeps Opus.
Stop only RC1: `.audit-tmp/artifact-ui-rc1-euo3av0q/checkout/.audit-tmp/stop-rc1.ps1` from this integration worktree.
**RC1 has no Antigravity seat (RC0 has it); daily Antigravity needs the reviewed distinct-name adapter, in review.** Hermes is excluded. RC1 contains dormant Hermes YAML adapter code with the known stale-backup B2 flaw; no Hermes seat or yaml_settings_file template is present, so that path cannot run. The AGY JSON adapter is absent.

**North Star, Seth's words:** "my initial scope was to remove the need to launch and maintain a ton of batch files that a screen for pre-flight to choose what agents could be used select the configuation and then it went to the chat page".

- Each ticket names the part of that goal it serves and an effort budget. Exceeding the budget, or encountering an untraceable gate, stops work for steering under Needs Seth.
- Acceptance gates cite a spec location or Seth quote; otherwise they are advisory. The unsourced270ms target was withdrawn.
- A milestone is done only after Seth has seen it work end to end. Reviewer/code-path acceptance is recorded separately.

## Now

RC1 is available for comparison with RC0. Its final frozen discovery passed2164 tests with13 skips (9 post-launch transcript,4 existing). Reviewer cleared the exact pin and unchanged artifact-v1 activation. Six included seats are ready. One Claude Haiku document109B and one DeepSeek document73B each passed Read/Download byte equality. The browser picker checked two tiny files,31 raw bytes, with the expected packet revision. No multi-file agent review or screenshot acceptance is claimed.

RC0 is unchanged and retains Antigravity. Hermes stays deferred: the running-path guard is integrated, but the Windows.cmd Stop limitation, pending stale-backup fix and Seth's existing Hermes process still prevent a real-home run. No Hermes home write/call happened.

## Needs Seth

- [ ] Release limit: corrected restart of a multi-file review does not edit the file list; changed files are reselected in a new review.

- [ ] 2026-10-27 02:19 CDT Security note: a test failure on2026-10-27 printed this machine's ambient environment into the Codex agent's tool output (visible to the model provider and stored in the local Traycer transcript). Credential-like variable NAMES visible: RESEND_API_KEY, STITCH_API_KEY, WIKI_LINT_API_KEY, TRAYCER_A2A_MCP_TOKEN (plus STARSHIP_SESSION_KEY). Values are not in any repo file. Consider rotating those that matter. No agent changed or rotated credentials.

- [ ] Beyond the raw agent names, what else looked wrong on the main chat screen? Naming is implemented/tested and is visible on the running instance.

- [ ] Decide later whether in-UI provider/template setup, credential entry, live model discovery belong in scope. These setup features are absent today; launch-and-go-chat is now implemented and exercised.

- [ ] RC0 AGY document path is unverified: one tiny request timed out/cancelled. DeepSeek document and Claude readiness/cooperative Stop verified. No Plan/notices/trust/permission prompt found in the read-only flag check; further retry requires an identified cause. Daily-use sanitized template aliases are still being prepared.

## Seats

|Seat|Model|Current check/status|
|---|---|---|
|Claude|claude-opus-5-5|Running; native OAuth hello passed. Earlier Haiku document124B exact; no Opus document loop|
|Codex|gpt-6.1-sol|Running; native OAuth hello passed; isolated MCP launch fixed. No Sol document loop|
|Antigravity|gemini-3.8-flash-medium|RC0 ready; document smoke timed out/cancelled. Earlier UAT63B success retained, not claimed forRC0. High/medium/low suggestions editable|
|DeepSeek|deepseek-flash|RC0 ready; fresh Documents99B read/download exact. Earlier100B retained.1070 not mapped|
|GLM|glm-5.3|Running; earlier Documents285B exact, no extra call|
|Muse|muse-spark-1.3-contributor|Running; Documents81B exact. Hello needed512-token probe cap; normal document path worked unchanged|
|Hermes|grok-4.7, existing xai-oauth|Adapter integrated/tested. Real proof deferred: existing bundled Python process; no home write or model call|
|OMP|openai-codex/gpt-6.1-sol|Running; managed Documents90B read/download exact; model unverified in API metadata|

## Next

1. Seth compares the frozen builds through Pre-flight and chat. RC1:50010 has the new UI/packets/defaults; RC0:49949 keeps the earlier build and AGY. Report defects in this handoff before any publication.
2. Reviewer checks the RC1 operational results and export scan. No additional model calls are planned.
3. Hermes and daily AGY injection remain deferred. The Windows owned process-tree Stop design and picker/source-label notes are in the post-launch list. No real YAML/JSON adapter write before its corrected pin is reviewed.
4. [Post-launch scope](C:/Users/SJG/.traycer/epics/6e815a47-c25b-4900-9e83-1be98cead36f/artifacts/post-launch-scope/index.md) holds Tickets21/22/24-26 and later decisions. Keep9 transcript skips and retained history.
5. Publication requires Seth's explicit go-ahead. No push or deletion is authorized.

## UAT

Chat: http://127.0.0.1:49949. Pre-flight: http://127.0.0.1:49949/preflight. It runs from the frozen RC0 clone, not this integration worktree. Stop command is in the top RC0 block; the old .audit-tmp/stop-ticket20-uat.ps1 targets only the retained, stopped old instance.

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

Next owners: Opus prepares the Hermes adapter and fixture tests; reviewer checks the pinned diff; Codex integrates and operates the normal-home seat only after clearance. Ticket21/22 are post-launch by Seth's latest decision;23 follows launch essentials, with Hermes parallel where files do not overlap.

## Verification and limits

- Frozen root discovery:1936 tests,13 disclosed skips (9 pending transcript +4 existing),398.132s, OK. Activation:112 focused builder and112 independent reviewer tests pass.
- UI fixes:40 tests pass,63/63 mutation checks killed. Live Claude/GLM read/download exact; DeepSeek/Muse light document checks exact. No new expensive Opus/Sol document calls.
- Current provider handoff exports:57 files scanned clean against used authorized API credentials and owned tokens/nonces. The owned server is deliberately active, not cleanup-complete.
- Prior R2/D4 timing misses, instrument-invalid attempts, host stalls and final190-observation PASS remain [retained history](docs/tickets/20/history/TICKET-20-D4-FINAL-GATE.md). Full refs remain in the index, historically about293KB per fulfilled max-source request; R3 compaction is deferred. The old128/512KiB quota was withdrawn.
- Browser harness is partial; no phone-width requirement or further harness work. Reviewer visibly exercised both original live paths. Seth's UAT verdict remains open.
- Non-blocking notes: first-use CLI workspace trust; CLI-path actual model confirmation unavailable; raw IDs/old duplicate labels/queue badge/departure lines; earlier cancelled/refused requests retained. The earlier Desktop/agentchatrr spelling was absent; Seth's real Desktop/agentchattr-0.5.0 install was later found and used read-only for CLI template reference.
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

Pure rename commit9fc6a4d contains exactly110 R100 entries. Baseline573 tracked files ->576, with only docs/README.md, historical STATUS snapshot and tools/check_markdown_links.py added. All215 fenced blocks unchanged;397 pre-existing code/tests/tools/static/AGENTS files byte-identical; zero case collisions; longest moved path143 characters; links0 broken before/after. Release build smoke includes README (archive output redirected into scratch). Localhost49949 still listening. Cleanup was reviewer-accepted after88 guide/backend passes and the1939-test full discovery (404.096s,13 skips), which exposed four subtests of one stale pre-activation expectation. Commitsfa1fef0/ea4bdf6 corrected only activated-capability expectations;80 full protocol/capability/worker/admission/operator tests passed. Prior failures remain in the receipt. Reviewer requested no repeat full run now; one final full run follows21/22 before publication.

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

### 2026-10-27 01:43 CDT Review and multi-file proposal

Reviewer cleared0251004 after reading the ownership delta and rerunning33 package/pre-flight tests. His approved split assigns Hermes wrapper.py/cli_seats.py/helper/temp-home tests to Opus, while Codex retains integration, STATUS and the Ticket23 plan. No real Hermes file has been written. The multi-file proposal is documentation only: existing512KiB source cap is a starting proposal, not a new settled gate. No23 product code, no new live calls, no push.

### 2026-10-27 01:44 CDT Current handoff refreshed

The morning note and seats artifact now show seven working seats, Hermes delegated, and the active AGY global MCP entry with current backup path/hash and stop removal.57 public exports scanned clean against the three used authorized API credentials and owned tokens/nonces. The UAT server remains running; no new model call, global write or shutdown occurred.

### 2026-10-27 01:46 CDT Multi-file proposal review

Reviewer found the proposal source-grounded and suitable to present as a proposal. Clarifications: raw-member-byte totals in preview, a separate encoded-envelope safety allowance pinned before code, helper-only quote membership (no Ticket25 findings/UI/synthesis), reorder-as-new-revision as an explicit default proposal, and a90-minute agent-time stop/report checkpoint. Seth has not approved23 code. Hermes remains with Opus; no real config write authorized by this docs change.

### 2026-10-27 01:59 CDT Seth release decisions

Seth: "Approve the Ticket 23 shape and the 90-minute checkpoint. Aggregate cap is 512 KiB, and reordering counts as a new packet." Raw member bytes determine the aggregate; encoded-envelope/metadata allowance is pinned before code. The checkpoint is90 minutes of agent time, then stop/report. Contract and observed reds go to reviewer before implementation.

Seth: "24-26 are going to come in post launch" and "to be honest im fine with slipping 21-22 to post launch as well". Release essentials are20, pre-flight/UI, the seven seats plus Hermes, and23. Transcript plan/9 dated skipped reds remain; no21/22/24-26 implementation now. No postponed feature is inherently needed for a source-checkout launch, provided start.bat, configuration/key supply and operator notes work. Final full discovery must disclose the9 transcript skips plus existing skips.

Seth approved daily-use key loading like the old launchers: only referenced api_key_env/secret_ref NAME= lines, first match, existing env wins, quote pair stripped, server-child env only, missing file/name harmless, no value in output/argv/errors. Temp-profile reds precede the fix. No real .env read for this source audit. README legacy-first/stale-ticket guidance and LAUNCHER entry flow were corrected.

Cold-start preparation is approved in one fresh pinned clone under the isolated UAT area, with its own .venv-windows and pip cache/temp paths. requirements.txt installs from PyPI only; no existing environment, global install, junction or interpreter monkeypatch. The directory is retained. Existing UAT49949 remains untouched.

### 2026-10-27 02:00 CDT Final reviewed UI polish

Merged pinned58aedb484763a73ae9ebccaa5cba0b046fa2ab23 (12 reviewed commits after0078e74), preserving the naming/canonical-id changes.149 naming/identity/package/pre-flight/help/Documents/restart/readability/chat-empty/layout tests passed in9.118s. The first command named a nonexistent test_identity_registry and had one loader error; corrected to test_identity_contract and reran the full intended selection. The existing HTTPError404 ResourceWarning remains. No backend or model calls in this merge. Opus can base Hermes on this merged integration pin.

### 2026-10-27 02:12 CDT Launch essentials: cold startup and keys

Cold clone2673954 at .audit-tmp/artifact-ui-cold-kmfwi68g/checkout: real windows/start.bat --setup created its own .venv-windows, installed only requirements.txt through PyPI, and cold-bootstrapped the server in31.435s. The isolated browser picked/saved one configured Codex seat, launched it and automatically reached chat with the Cold Codex pill. No model prompt. --no-browser kept default/personal browser untouched; the controller opened the printed URL. Setup/bootstrap/one-seat readiness pass, not proof of every seat on this fresh environment.

The first supervisor failed to create its audit directory and stopped its own cmd before setup; logs retained, no child/venv/server remained. After fixing the operational directory, the same untouched clone was used. Final cleanup: seat API returned stopped; signed server50372 and verified descendant66148 both ended through retained birth-verified handles. Clone/environment retained. Primary UAT49949 unchanged.

Named-key red-first tests: original run had1 behavioral failure (spawn did not enrich child env) plus7 missing-helper subtest errors across7 tests. Added a malformed saved-provider red (TypeError), then guarded it. Now62 launcher/named-key/package/pre-flight tests pass in4.357s. Temp profiles/fake values only; no real .env read by the new loader. It reads only configured API template/saved-seat reference names, strict first NAME= match, existing env wins (including empty), one quote pair, CRLF; skips invalid bytes/NUL without values in diagnostics; enriches only spawn_server env. Review required before live reliance.

Next: minimal offline marked fallback, then Ticket23 frozen contract/observed reds. Hermes and the safe daily AGY injection remain with Opus. Sanitized daily aliases/model-editing table are being prepared; no real-install config applied. No postponed audit/refactor work, no push.

### 2026-10-27 02:19 CDT CLI credential boundary and assertion safety

Reviewer found that server API keys could reach native CLI processes through inheritance. Shared referenced_api_key_names now serves both the key loader and CLI effective configuration. CLI-worker spawning and native-client environment construction both remove the referenced names, case-insensitively on Windows; API-worker spawning remains unchanged. No new snapshot field: the names use existing provider.strip_env.73 launcher/key/package/CLI-worker/config/CLI-seat/assertion-guard tests pass in3.699s. Native-client strip bypass mutant failed one assertion with0 errors. Initial safe red confirmed API-key presence in the CLI worker; missing helper was an infrastructure red.

The failed first red accidentally formatted ambient env values; it was corrected to fake-only patch.dict(clear=True) plus boolean assertions and rerun red safely. The new AST assertion guard observed8 unsafe os.environ-container assertion sites (4 in test_config_overrides,4 in the new key tests), now rewritten without changing their predicates. Every future handoff scan includes the five incident variable names' current values in memory, without printing them. Full incident scan result is .audit-tmp/incident-export-scan.json; transcript output remains retained outside exports.

UAT's Claude, Codex, Antigravity and OMP launches inherited ZAI_API_KEY, DEEPSEEK_API_KEY and META_API_KEY by the prior server/worker construction. This is established from the authorized startup env and snapshots, not a process-memory dump. Their restart with stripped environments is pending independent security clearance. No new live model call. Primary server remains available.

### 2026-10-27 02:26 CDT UAT refresh and offline chat

Security fix51a53b6 cleared by reviewer (51 focused reviewer tests). Owned UAT cooperative refresh completed:7/7 ready,0 model prompts. Fresh Claude/Codex/AGY/OMP effective snapshots include all3 referenced API names in strip_env; filtering name-presence probes gives false for all3 on each CLI. Verification is launch construction plus immutable snapshots, not process-memory inspection. Public report cli-api-key-isolation-check.json.

Offline CDN defect: init and renderMarkdown threw ReferenceError when marked was absent. After correcting one Node test argv-fixture error,2 genuine reds were observed and the normal-parser control passed. Added a guard around marked setup and an early escaped-plain-text/line-break fallback, preserving literal paths and code-looking text safely.92 offline/naming/chat-empty/help/Documents/pre-flight/assertion-guard tests pass in8.766s; node --check passes. No vendoring, network call or other audit cleanup.

Daily-model follow-up approved: Opus will add a CLI default_model fallback after Hermes, then the entry-only AGY JSON option. Blank model uses the template default; explicit model wins; no configured default preserves native behavior. AGY daily template will default to gemini-3.8-flash-medium and suggest high/medium/low. PyYAML is already installed transitively; Opus is authorized to declare PyYAML>=6.0 explicitly for the Hermes adapter.

### 2026-10-27 02:37 CDT Ticket23 frozen contract and reds

[Frozen contract](docs/plans/2026-10-27-multi-file-contract.md) pins v2 file_packet fields, f1/f2 ids, canonical UTF-8 manifest/revision,524288 raw aggregate,65536 metadata allowance and1114112 encoded-text allowance, preview/auth, compatibility and every identified consumer. Old v1/paste formats stay unchanged. Existing corrected-paste restart remains explicit; changed files can be reselected in a new review rather than inventing a linked packet-editing workflow. Artifact authoring's2MiB cap stays independent.

Observed22 tests:9FAIL+12ERROR+1PASS (0.571s);8 missing-seam infrastructure errors and4 existing-validator behavioral errors. One actual opaque-packet store/export/import roundtrip already passes. No23 production code;90-minute active implementation/verification clock starts on clearance. No new browser harness or provider call.21/22/24-26 stay post-launch, including9 dated transcript skips. Next owner: reviewer clears contract/reds, Codex implements the bounded slice.

### 2026-10-27 02:45 CDT Ticket23 group1: core

Reviewer cleared production at662558f with deterministic readable delivery shared by CLI/API. Added pure document_packets validation, caps, order-sensitive revisions, file-bound quote membership and render_delivery. The readable projection keeps BOM/CRLF/content verbatim, uses an authoritative ordered index and byte lengths, and warns about fake delimiters. Added a new missing-module red for that projection before code, plus a genuine outer-metadata bool-as-int red found during implementation and fixed with canonical typed comparison.

27 focused core/v1/protocol tests pass in1.208s. Three in-memory mutants (raw cap off by one, cross-file quote acceptance, ignore file order) each failed one assertion with0 errors. Group2's large encoded-source consumer is still red because the old brief source cap has not been widened for validated v2. Route/picker reds remain pending; no full green claim. API worker closure now declares document_packets; declaring it in the CLI worker set produced an unreachable-module failure, so that set remains accurate. CLI delivery rendering belongs to the server-side MCP handler. No old manifest edited.

Budget tracking uses the662558f red-pin wall clock as a conservative upper bound on active agent time (includes review wait). The90-minute checkpoint remains a stop/report boundary, not a performance gate. Hermes merge/run and consumer integration are next;23 product work stops at the checkpoint if incomplete.

### 2026-10-27 02:49 CDT Hermes adapter integration and managed-path fix

Merged pinnedca2c80b, preserving the security strip changes and both new YAML/API packet source dependencies. PyYAML>=6.0 is declared explicitly. Before a real write, source tracing found the legacy wrapper finally had cleanup but managed cli_worker.run did not. Two temp-HERMES_HOME tests observed genuine failures: cooperative managed Stop and startup failure after apply both left the entry. A YAML-only ExitStack callback now registers before apply and runs while the lifetime settings lock is held; both tests assert exact original bytes and no temporary file.109 YAML/CLI/key/package/protocol/assertion-guard tests pass in4.939s.

Forced worker termination on Windows skips Python finally and can leave the entry/token. No new server-side global-file recovery was added: the supervised real run must verify removal after Stop and explicitly check for leftover entry/tmp files; if proof/cleanup fails, stop and report. The normal-home run is held until reviewer checks this corrected integration pin. No real HERMES_HOME config read/write has happened in these tests.

### 2026-10-27 02:59 CDT UAT freeze RC0 boundary

Reviewer requested immediate UAT isolation from this moving integration tree. RC0 is99361d1 (reviewed UI, pre-flight fixes, key loader/CLI strip and offline Markdown fallback), before23 reds/core and Hermes. A fresh retained clone gets its own environment and one full root discovery; no switch until reviewer checks it. Existing UAT49949 remains up meanwhile. The transition plan is .audit-tmp/rc0-transition-plan.md.

Copy boundary before switching: saved seat packages and non-runtime templates/config/env-var NAMES only. Re-seed synthetic accepted source sessions in the new runtime root. Never copy runtime, queue, process, ownership or other authority catalogs. Old root/data stay untouched. Operational helpers must be frozen with the new checkout, not import moving integration code. After the cooperative switch, further work never changes RC0; later fixes require reviewed RC1. Hermes real-home run will use a separate integration-owned instance or wait for RC1, with its same backup/removal/no-Hermes-running rules.

RC1 trigger: Hermes result or explicit defer, reviewed default_model and the23 checkpoint. Include23 only if all3 groups are green/reviewed; otherwise explicitly exclude it. The7 UI ideas are deferred unless reviewed/pinned by freeze. Daily AGY injection is not an RC prerequisite (reviewed UAT shim remains); disclose it as pending.21/22/24-26 are post-launch. No push/publication.

### 2026-10-27 03:31 CDT RC0 switch, evidence and open risk

Pinned clone99361d1 full discovery:2025 tests in407.218s, OK13 skips (9 post-launch transcript+4 existing). Exact log: C:/Users/SJG/.traycer/worktrees/sjgold__agentchattr/codex-ticket-20-r2-on-a1/.audit-tmp/artifact-ui-rc0-_om1o8fc/full-discovery.log. Reviewer checked the pin and cleared the switch. Copy manifest .audit-tmp/rc0-copy-manifest.json records9 config/control script hashes; product config validation passed7 seats. No runtime/queue/process/ownership/authority catalog copied. Old root/data retained; synthetic sources were re-seeded in the new root.

Cooperative old Stop removed its AGY entry and stopped server/workers. Full signed inventory then found native agy36368 andclaude54236 leftovers. Only their exact current-birth verified handles were terminated/waited. Reviewer's extra ancestor-chain precaution arrived after this action; a retrospective current Traycer/Claude/Codex chain check found0 matches, not a pre-termination proof. The normal RC0 Claude Stop cycle subsequently ended native70724 cooperatively and restarted/rebound the team to7/7,0 model prompts. No broad process kill or port/name authority.

RC0 Pre-flight loads with7 editable model fields and saved choices retained on reload. AGY suggestions are high/medium/low and saved model is explicitlymedium; blank-default fallback is absent inRC0. Fresh smoke: DeepSeek99B exact; AGY1 request accepted202 but timed out180s and was cancelled, with no automatic retry. Native console flags: Medium, no Plan/notice/trust/permission prompt, no artifact tool text visible. The durable queue has a cancelling transport record; no conclusion about cause. Earlier original-UAT CLI passes stay historical.

Next: group2 packet consumers within the checkpoint; Hermes proof uses a separate integration-owned instance or RC1, never editsRC0. The currently running AGY shim/merge and server bootstrap are frozen ignored control files insideRC0. All later UI/product merges remain integration-only. No push/publication.

### 2026-10-27 03:39 CDT Ticket23 group2: consumers

Validated v2 source uses its encoded allowance through freeze and BriefStore; v1/paste keep the old cap and exact message bytes. Stored/internal HTTP source remains canonical and validated. Both actual agent boundaries use render_delivery: API source message directly; CLI MCP gets one JSON context prefix, exact --- packet --- boundary, then the same verbatim body. No duplicated canonical source/model content; IDs/revision/seal authority are unchanged. Five boundary tests observed1 genuine failure+1 missing source_follows behavioral error before code; old byte controls passed. Pre-change v1/paste API payload digests remain pinned.

All ten fake CLI tools and verify_result_outbox use one test-only framing decoder (4 initial tests/9 missing-helper subtest errors observed). Product imports no test codec. Native wrappers do not parse tool output.100 core/delivery/codec/real-session-HTTP/v1/brief/seal/source/import/protocol/assertion tests passed in7.145s. Real HTTP serializer accepts raw512KiB worst-case quoted/backslash input under4MiB; unauthenticated/agent starts remain403. No route/picker green claim yet.

Group1 asks included: whitespace-only quote red then refusal, versionTrue/2.0/string dispatch guards, inner manifest id gap/reorder tamper, hand-crafted raw/metadata excess through validation, non-dict/str-subclass citation guards, and forged markers using real byte_length/sha fields. check_quote still validates the whole packet on each call; optimization is post-launch only. No migration, no live model generation or UAT checkout edit in this group.

### 2026-10-27 03:55 CDT Ticket23 group3 verification

Operator-only packet-preview POST enforces a4MiB streamed-body limit and strict JSON shape. The existing source picker accepts multiple UTF-8 files, lists ordered ids/names/raw sizes, freezes the validated packet and supports removal. Single-file selection still uses v1; pasted text stays unchanged. Stale selection, disposal and timeout cannot restore late results or enable Start. Text remains literal; source bodies are not put in browser storage.

175 focused document/brief/delivery/route/source/seal/outbox/protocol/naming/artifact-UI/environment-guard tests pass in9.949s. Node syntax and diff checks pass. Three in-memory mutants (aggregate guard, packet validation, stale selection) each fail one assertion with zero errors. An explicit untrusted-data preamble test was observed red before its wording fix. CLI guide records v2 JSON-prefix/fixed-boundary framing. No browser/live-provider check or RC0 change.

Commit1d0ed71 landed before this STATUS update because the timestamp script failed on missing Windows tzdata; this follow-up uses Windows TimeZoneInfo. Hermes operations stopped before any real-home write: bundled Python61816 was present under HERMES_HOME although image checks missed it. Config unchanged and agentchattr-uat absent. Reviewer requested path detection and a signed fake.cmd Stop reproduction before RC1.

### 2026-10-27 04:01 CDT Ticket23 review follow-ups and checkpoint report

Reviewer cleared groups1/2/3. Four added regression tests observed3 assertion failures and1 disconnect error before the small fixes: normalize zero-padded Content-Length, return400 for disconnected request streams, identify the failing file by index/name, and reset the8-second deadline for each preview request. Duplicate fields, tampered members,415 and no-Content-Length chunked overflow are also covered.179 focused tests pass in13.431s; Node syntax is valid. No rendered multi-file or live multi-file provider claim.

Remaining before RC1: review this follow-up delta; integrate reviewed default_model4af9bc2 plus managed-runtime snapshot/effective-model tests; optionally integrate reviewed UI10ff7d0 and AGY JSON adapter only after clearance; then freeze and run final full discovery/activation-state review. Ticket23 is included only after that verification. Early client-side file-count/metadata refusal remains a note; the authoritative server64KiB metadata cap already refuses oversized lists. No add-to-selection feature or source-view redesign added.

Windows Stop reproduction is a confirmed limitation, not fixed: a directly owned fake.cmd parent ended while its signed/birth-verified Python child survived. Both test handles exited during proof cleanup. Evidence: .audit-tmp/owned-cmd-stop-proof/result.json and .audit-tmp/reproduce_owned_cmd_stop.py. Reviewer ruled race-free Job Object ownership is post-launch work. Current UAT uses claude.exe, codex.exe, omp.exe and Python-shim-to-agy.exe, none.cmd/.bat. Hermes.cmd is explicitly deferred with the running-path guard and existing Hermes process decision. Spot leftovers through signed birth inventories and retained handles; never kill by name or port.

RC0 still serves49949 from99361d1. This check scanned17 current exports clean against authorized credentials/owned tokens and the five incident-variable current values;27 old-root report paths were absent and excluded, not claimed scanned. No push or publication.

### 2026-10-27 04:04 CDT RC1 default-model integration

Merged reviewed4af9bc2. A blank CLI model now uses its template default, with an explicit seat model winning. Added default_model to managed client snapshots and provenance fingerprints; requested_model reports the effective value both before and after launch. Two managed-runtime tests observed real failures before the integration fix; they now verify frozen worker arguments and changed-default fingerprints without launching a client.85 CLI/default/runtime/worker/pre-flight/package/protocol/security-guard tests pass in6.208s. One test initially changed the original template instead of SeatStore's detached copy; corrected the fixture, then reran the full focused set.

The daily Antigravity model proposal is in docs/guides/DAILY-SEAT-TEMPLATES.md. Injection remains pending corrected adapter review; no daily/global config applied. RC1 will run beside RC0 on its own free port block, not replace it. Hermes remains excluded; its real-home proof is deferred. Next: reviewed UI10ff7d0 and path guard48c6d36, then the corrected AGY adapter only if cleared, final frozen discovery and reviewer activation-state check.

### 2026-10-27 04:05 CDT Reviewed UI ideas integrated for RC1

Merged pinned10ff7d0: clearer text-field edges, side-by-side seat toggles, wider Documents reading space, compact channel actions, template-first session choices and a smaller idle addressed-agents line. Idea6 was intentionally skipped on the reviewed branch. Resolved cache-version conflicts using the new packet picker and newest UI assets; kept both default-model and toggle-layout tests. Canonical routing ids and display labels remain intact.151 readability/pre-flight/help/artifact/restart/naming/packet/default/CLI/package tests pass in8.161s. RC0 checkout and its served bytes were untouched. Next: path guard48c6d36, corrected AGY adapter only if cleared, then frozen RC1 verification.

### 2026-10-27 04:06 CDT Reviewed path guard integrated

Merged pinned48c6d36 without conflict. Hermes detection now checks executable paths beneath the resolved home as well as image names; unknown probes stay unknown.102 YAML/temp-home/CLI/default/protocol/environment-guard tests pass in3.310s. No real home, live process or global config was changed. Hermes stays excluded from RC1. The separate stale-backup receipt correction is still under Opus/reviewer review; no real YAML/JSON adapter write is permitted before that corrected pin.

RC1 freeze proposal includes cleared multi-file work, model defaults, UI10ff7d0 and path guard48c6d36. The AGY JSON adapter remains excluded unless cleared with managed cleanup tests first. A sibling instance must not replace RC0's distinct global AGY MCP entry; concurrent AGY launch needs an explicit safe plan or omission. Final full discovery has not yet run on these merged bytes.

## Pre-flight model editing, release check

The seven RC0 model fields were editable and retained their saved values after reload. Defaults are suggestions, not live model discovery. Hermes has not been launched.

|Seat|Editable|Suggestions in tested config|How launch uses it|Effort|
|---|---|---|---|---|
|Claude|Yes|claude-opus-5-5|--model value|No declared effort override|
|Codex|Yes|gpt-6.1-sol|--model value|No declared effort override|
|Antigravity|Yes, RC0|gemini-3.8-flash-high/medium/low|--model value; explicit medium saved in RC0|RC0 also declares --effort medium; daily proposal uses model variant|
|OMP|Yes|openai-codex/gpt-6.1-sol|--model value|--thinking minimal|
|Hermes|Not live-verified|Not wired for RC1|Deferred, no model/launch claim|Existing normal-home setup stays untouched|
|DeepSeek|Yes|deepseek-flash|API request model field|No configured effort choices|
|GLM|Yes|glm-5.3, glm-5.3-flash, glm-5.3-flashx|API request model field|No configured effort choices|
|Muse|Yes|muse-spark-1.3-contributor|API request model field|No configured effort choices|

RC1 tests verify a blank CLI seat uses the template default in the frozen worker arguments; an explicit value wins. The daily agy default is medium, and the proposal carries all three variants. No global/default login setting was changed.

### 2026-10-27 04:09 CDT Frozen RC1 discovery started

Candidate pin: fdc6c275edb8d81f387c782aaeaf27a4e216816a. Fresh clone: C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\.audit-tmp\artifact-ui-rc1-euo3av0q\checkout. Exact full-discovery log: C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\.audit-tmp\artifact-ui-rc1-euo3av0q\full-discovery.log. Own environment setup succeeded; the single full root discovery is running. No server or model calls in this window. RC1 has separate future runtime/ownership/ports and leaves AGY out; no RC0 shim/global entry is copied. Expected skip disclosure is9 post-launch transcript plus existing skips; actual counts/result will replace this pending note.

### 2026-10-27 04:28 CDT Frozen RC1 launch and bounded checks

Exact pinfdc6c275edb8d81f387c782aaeaf27a4e216816a, clean clone,245 modules/2164 tests/413.123s, OK13skips. Exact log: .audit-tmp/artifact-ui-rc1-euo3av0q/full-discovery.log. Reviewer verified pin/clean tree/log and SUPPORTED_CAPABILITIES=('artifact-v1',), then cleared sibling launch. Runtime is .audit-tmp/artifact-ui-rc1-euo3av0q/checkout/.audit-tmp/artifact-ui-uat-rc1 on ports50010-50013. RC0/its registries remain separate and unchanged. Only config/templates/package/bootstrap/owned controls were copied;0 authority catalogs. Seven copied-file names/hashes and six-seat validation are in .audit-tmp/rc1-copy-manifest.json. AGY shim and global cleanup imports were removed; no Hermes/AGY provider or YAML/JSON entry mode exists in RC1.

First supervisor invocation lacked PYTHONPATH and failed at import before creating any child. Explicit pinned PYTHONPATH fixed that operational invocation without a code change. Claude's new-workspace trust menu defaulted to No: numeric1+Enter did not select Yes and the client exited before generation. Explicit Restart followed by Up+Enter accepted only the owned empty workspace; the trust prompt disappeared and Haiku was visible. Package rebind restored6/6 readiness. This is one-time console trust, not a global-settings edit by our scripts.

Exactly2 new document requests: Claude Haiku requested,109B SHA256dc827c229d465be2d131c50c54d2a72c61b1575dcf000af643039fa214f23692; DeepSeekFlash confirmed,73B SHA256302deedc1446b146473f2de01eef5bbc4dc2b7384c81d70aec69e629567abc23. Both fulfilled, Read/Download200 and byte-equal. CLI actual model remains unverified by metadata; no Opus/Sol document loop. Reports: runtime/rc1-document-smoke.json and rc1-claude-trust.json.

Real browser Pre-flight showed6/6 ready and the polished cards; chat had Seats&launch -> /preflight and0 raw managed ids in visible text. Dismissed the one-time Welcome through its control. Two browser File objects (native file dialog not used) passed the real picker/HTTP route: f1 one.txt17B including BOM/CRLF, f2 two.txt14B;31 raw bytes; revision4748b2758fdbdbd0c73f6d7ed3296e5be2941ce1ae90e9379fd22bd60029a11e independently matches preview_packet. Start was not clicked: a multi-agent live packet review was skipped to keep calls bounded. Report: runtime/rc1-ui-packet-check.json.

Signed inventory:17 live,0 uncertain, intentionally active and not cleanup-complete. Original checkout data manifest unchanged (1 file); both Pre-flight URLs return200. CLI frozen configs strip all3 referenced API names; proof is configuration plus tested native env construction, not process-memory inspection. Both pinned checkouts have0 tracked changes. No global config write, push, publication or deletion from RC1.

### 2026-10-27 04:34 CDT Corrected JSON adapter and managed cleanup, integration only

Merged reviewer-clearedff32cb6, preserving the reviewed executable-path guard. It fixes stale-backup receipt composition in both YAML/JSON adapters and adds the distinct-name JSON option. Two actual managed-worker tests observed original-byte failures before B1: cooperative Stop and startup failure after apply left the JSON entry. cli_worker now registers the JSON cleanup callback before apply, inside the lifetime settings lock, matching YAML. Both modes are exercised on temporary homes, including lock-before-cleanup assertions and exact-byte/no-tmp checks.285 focused adapter/guard/managed-worker/CLI/default/runtime/protocol/key/assertion tests pass in8.297s.

RC0 and RC1 still serve their original clean pins; this merge does not reach them. No real YAML/JSON write, agent launch or model call occurred in these tests. Further real-home use still needs reviewer clearance, Seth's go and the running-client conditions; Hermes.cmd Stop limitation remains. Next: reviewer checks this integration pin; prepare a docs-only publication-readiness note for reviewer review, no push.

RC1 handoff was independently accepted: reviewer checked both HTTP endpoints, listeners,7 copy hashes, pin/clean tree, full-run log and STATUS. Live smoke/preview/trust observations and28-export scan remain builder evidence. Final file-state check:126 tracked Markdown files,0 broken links;0 tracked deletions RC0..RC1; both frozen trees clean.
