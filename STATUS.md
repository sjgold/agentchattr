# STATUS - AGENTCHATTR

**Updated:** 2026-10-27 02:37 CDT. Ticket23 contract and22 observed reds ready for reviewer; no23 product implementation yet.

**North Star, Seth's words:** "my initial scope was to remove the need to launch and maintain a ton of batch files that a screen for pre-flight to choose what agents could be used select the configuation and then it went to the chat page".

- Each ticket names the part of that goal it serves and an effort budget. Exceeding the budget, or encountering an untraceable gate, stops work for steering under Needs Seth.
- Acceptance gates cite a spec location or Seth quote; otherwise they are advisory. The unsourced270ms target was withdrawn.
- A milestone is done only after Seth has seen it work end to end. Reviewer/code-path acceptance is recorded separately.

## Now

Documentation cleanup is accepted. Seven seats are running, including OMP (90B managed document read/download exact). Antigravity's real managed document now passes63B read/download exact after clearing two first-run notices and switching the owned CLI from research-only Plan to Auto mode. Normal Google login was already present; the startup error log was not evidence of missing login.

The real Windows launcher reuse path, Pre-flight package editor/save/launch and Open chat path were exercised. Live sender labels are friendly (zero raw managed ids in sender elements). Reviewed UI commits08b1f0a/a8f624c/c6930b0 and0078e74 are integrated: visible Seats & launch link, clearer pre-flight flow, lighter help and usable menus.The first merge passed119 focused tests; the follow-up passed69. Launch team and open chat was exercised with7/7 ready seats. Seth's own end-to-end acceptance remains open.

## Needs Seth

- [ ] 2026-10-27 02:19 CDT Security note: a test failure on2026-10-27 printed this machine's ambient environment into the Codex agent's tool output (visible to the model provider and stored in the local Traycer transcript). Credential-like variable NAMES visible: RESEND_API_KEY, STITCH_API_KEY, WIKI_LINT_API_KEY, TRAYCER_A2A_MCP_TOKEN (plus STARSHIP_SESSION_KEY). Values are not in any repo file. Consider rotating those that matter. No agent changed or rotated credentials.

- [ ] Beyond the raw agent names, what else looked wrong on the main chat screen? Naming is implemented/tested and is visible on the running instance.

- [ ] Decide later whether in-UI provider/template setup, credential entry, live model discovery belong in scope. These setup features are absent today; launch-and-go-chat is now implemented and exercised.

- [ ] Launch handoff: cold startup verification is in progress; daily-use sanitized template aliases will be prepared for approval. No further scope decision is needed for23 shape.

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

1. Pre-flight retry/Leave out fixes0251004 are reviewer-cleared; keep the running UAT instance available.
2. Opus implements Hermes YAML support on temporary homes in its own worktree. Codex integrates its reviewed pin; explicit reviewer approval before any real-home write, then one tiny request with the existing login.
3. Cold-start verification and the approved named-key child-environment fix; then freeze Ticket23 contract/observed reds, review, implement within its90-minute agent-time checkpoint.
4. [Post-launch scope](C:/Users/SJG/.traycer/epics/6e815a47-c25b-4900-9e83-1be98cead36f/artifacts/post-launch-scope/index.md) is the shared next-scoping list. Tickets21/22/24-26 are post-launch; preserve transcript plan and9 dated skipped reds. Final full discovery, activation review and file-state check precede any publication.
5. Push/publication requires Seth's explicit go-ahead.

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
