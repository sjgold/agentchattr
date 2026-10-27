# Ticket #11: correct the document and restart cleanly

**State:** Published and closed. Same AGY independently passed frozen implementation78b418d; source publicationf403b59. STATUS.md and REVIEW-GEMINI-TICKET-11.md carry final evidence.

**Authority:** Approved issue #11, spec v1.7 SC-3 and AT-07, October22 autonomous execution amendment. Its only blocker #10 is published/closed. Base main `83aa04a`. Full runtime restart adoption (#9), stalled-turn deadlines/retry (#12), worker outbox recovery in later backlog and file intake (#18) remain separate scope.

## Preimplementation baseline (historical)

- Each run freezes source/hash, design/rules/goal, participant kind and stable identity. New turn briefs are scoped to their own run/attempt. Stop persists ineligibility and quarantines old output, including ordinary untagged output from controlled seats.
- SessionStore has no corrected-restart operation or parent/replacement linkage. Starting a separate session through the ordinary Start endpoint does not record a corrected lineage or establish clean CLI context.
- API `brief_messages` currently appends supplementary recent chat. That can contain the mistaken source and old answers. A new request process alone cannot make that payload clean.
- CLI workers are persistent, with model/reasoning/MCP launch contracts. There is no declared or verified fresh-context/reset contract. Starting a new process does not prove that a native client will avoid auto-resuming history from its existing home or working directory.
- SeatManager retains current app-owned attempts and effective snapshots, but SessionStore participant bindings contain kind/identity rather than a full managed-seat launch provenance snapshot. Saved-package or template edits can diverge from a running seat. Do not infer an old launch from a reused display name.

## Approaches and recommendation

| Approach | Benefit | Cost / boundary |
| --- | --- | --- |
| Linked replacement run with explicit clean-context preparation (recommended) | Preserves old history; rejects old answers; makes API/CLI cleanliness and failures visible | Must establish reliable CLI launch provenance and isolation before dispatch |
| Edit the stopped run and reuse its turn identities | Small code change | Violates immutable source/lineage and risks admitting old-document results; rejected |
| Ordinary Start plus a new input field | Reuses existing UI | Does not establish lineage, prevent chat contamination or prove CLI context isolation; insufficient |

## Proposed product contract

1. Offer **Correct source and restart** on a durably stopped run. Keep the old source, accepted results, quarantine, design and history readable. The replacement source is a new immutable snapshot with a distinct content revision and a new run/turn/attempt identity, linked to the old run. Retain frozen design, goal, rules and role assignments by default. An explicit seat replacement records what changed.
2. Drafting is harmless. Validate exact UTF-8/size/NUL rules and show source/revision/context preparation before dispatch. Invalid, oversized or unchanged replacement text cannot mutate the old run, launch clients or create executable work. Whether an unchanged source should instead be a separate retry is an explicit contract question below.
3. Stop fencing remains permanent. Old briefs/results cannot contribute to the replacement; late old output still quarantines against the old run. Replacement results start empty and do not import old result IDs, questions, continuation answers, summaries or channel chat. Only results accepted within the replacement lineage's current run may enter its later phases/output.
4. API review requests rebuild solely from the replacement packet, retained frozen instructions/rules and that new run's accepted phase results. Exclude supplementary shared-channel history for corrected runs. Keep ordinary non-review chat independent.
5. CLI reuse requires an explicitly supported and verifiable clean-context mechanism. Prefer a fresh app-owned process/context over an unverified in-console reset. Preserve native login, never copy/reset authentication homes or delete native histories. A generic client with no reliable fresh-launch contract stays visibly blocked/unsupported, with no claim that it is clean.
6. Replacing a persistent CLI context has an impact even if the old turn ended. Show and require explicit operator confirmation bound to the exact owned launch. Never restart a seat carrying unrelated active or pending work, silently rebind that work to a new identity, or kill a replacement launch. Existing #10 termination proof and scoped fencing are reusable; a fresh launch must establish new live identity/readiness before its replacement review dispatch.
7. Preserve effective seat/model settings rather than silently adopting edited saved packages/templates. Capture sufficient managed launch provenance for new runs. If an older stopped run lacks enough identity/provenance to establish its original seat settings, surface a repair/explicit replacement choice instead of guessing from names. Human roles remain operator-only.
8. Preparation may involve process side effects, so record a stable operator request ID and visible prepared/blocked/launching state. Repeated requests must not create duplicate replacement runs, duplicate clients or duplicate dispatch. A crash after new-run persistence but before enqueue cannot make the old run eligible. Full arbitrary server-restart adoption/replay remains #9; uncertain preparation must be visible and require explicit recovery.
9. Failures preserve the old run and any successfully prepared owned contexts, while withholding the new review until required roles are ready and clean. Do not report successful restart because one seat launched. Do not auto-loop retries, silently switch models or import worker outbox recovery.

## Questions for independent pressure-test

- **Lineage transaction:** What is the smallest atomic store operation for parent/replacement linkage and idempotent preparation? One SessionStore file can hold both records, but external process launch cannot be atomic with that write. Determine explicit crash boundaries and which states can safely dispatch.
- **Fresh CLI assurance:** What exact evidence qualifies an adapter for clean restart? A declared argv flag and a fresh PID alone may still resume old native context. Require a bounded contract that fake fixtures can verify while keeping unsupported real clients honestly unverified. Do not invent native flags, broadly rewrite client homes or imply a native acceptance pass.
- **Retained settings and identity:** How should managed launch provenance be captured for future runs and handled for older stopped runs, without guessing from names or adopting template drift? Preserve stable API seats where rebuilt requests suffice; map fresh CLI identities only to the new run's roles.
- **Shared seats and impact:** Scope preflight checks across all active/pending envelopes for the old CLI identity. Block preparation that would harm unrelated work. Define exact launch confirmation and race ordering with Stop, normal seat restart and claim.
- **Context contamination:** Which shared-chat reads must be excluded for corrected API/CLI reviews? Filtering only explicit old result messages misses pasted source and untagged summaries. New-run frozen briefs should be sufficient without recent chat; inspect wrappers and MCP read behavior.
- **Same source and terminal parent:** Recommend rejecting identical source for corrected restart and requiring terminal local Stop evidence before execution. Pressure-test whether preparation can be offered while CLI cancellation is unresolved, with execution blocked until explicit owned termination, without confusing it with #12 retry.

## Verification contract

- Observe red tests before implementation. Real stores prove new source/run/revision/attempt identities, retained frozen design/team/rules, atomic old/new linkage and unchanged old history on errors.
- Inject old source, accepted answers, chat summaries and continuation context into the channel; capture actual API request and actual CLI/MCP brief. None may leak into replacement inputs or results, while exact replacement Unicode/CRLF text survives.
- Exercise concurrent/double operator restart, launch failure, persistence failure and a staged crash between preparation/launch/bind/enqueue. At most one replacement executes; no old dispatch is resurrected.
- Real fake CLI verifies a fresh context/identity and exact retained model/reasoning; unsupported fresh-context capability remains visibly blocked. Stale launch confirmation cannot stop a replacement or unrelated work. Native client acceptance remains outside routine scope.
- Real mixed-team fixture preserves old accepted result/history, quarantines late old output, produces new-source-only results and leaves another run/seat available. Operator UI shows replacement source, impact, clean/unsupported/readiness states, lineage and failure recovery.
- Full regression suite, all prior isolated integrations, scoped browser checks, static checks and same-AGY independent frozen review/recheck before publication.

## Work sequence

- [x] Same AGY ratified the core clean-context/provenance/preparation contract; prepared-role repair and pre-activation read amendments are settled in Section8.
- [x] Test-only helper captured real red lineage/launch/repair regressions; current unit checks pass.
- [x] Codex implemented linked preparation, new-run isolation, bounded context preparation and child-only repair.
- [x] Implement operator source preview/impact/blocked/restart controls and real fake-client verification.
- [x] Freeze, same-AGY independent PASS, reviewed publication and issue closure.

Current owner: Codex finishes scoped UI/regression acceptance; test helper executes the isolated corrected integration. Same AGY owns final frozen implementation review. No native/live-provider usage is authorized by these checks. Routine human plan/completion gates remain removed.

## Contract critique and follow-up

Same AGY returned PROCEED WITH AMENDMENTS in `ticket-11-contract-review/index.md`. Root accepted atomic linked preparation, immutable retained launch provenance, same-source400, shared-seat409 and explicit unsupported CLI state. These are pending concrete interface freeze, not implementation evidence.

Rulings and issues sent back for resolution:

- **Accepted:** omit supplementary shared chat for all completion_protocol1 frozen API turns; ordinary API chat stays unchanged. New run phase results remain available through its frozen briefs.
- **Rejected:** a warning acknowledgment cannot turn unverified reused CLI context into clean context. With unresolved old work, drafting/preparation may proceed, but dispatch needs proven old local end or an explicitly selected independently clean replacement identity/context. No native flags are assumed from a generic example.
- **Required distinction:** prepared ineligibility is temporary; a stop_id-bearing fence is permanent. Current #10 code uses dispatch_eligible=False as shorthand for Stop in reconciliation/chat-scope/control paths, so those paths must distinguish preparation before adding prepared records. Stop during preparation must permanently prevent activation.
- **Required provenance:** retain effective allowlisted configuration or immutable launch references plus fingerprint, not only model/reasoning/package IDs. Edited cwd/args/MCP mapping/provider parameters cannot silently enter corrected work. Never persist credential or bearer values. Older missing provenance needs explicit replacement-settings selection/confirmation.
- **Open:** default CLI MCP chat_read/resync/job reads must not silently reintroduce old-channel history. Keep old history readable to the operator; do not imply a filesystem sandbox or forbid unrelated discussion globally. Settle the bounded default-read policy with same AGY.
- **Proposed idempotency:** one prepared child per parent, stable request ID, same-request repair of that child without duplicate launches/runs. Source changes require an explicit replacement lineage rather than mutating an existing source snapshot. AGY is checking exact crash/activation boundaries.

Next owner: same AGY resolves the follow-up contract questions; Codex then fixes interfaces for independent red tests. No routine human gate, production changes or implementation-test pass is claimed.

## Agreed execution shape and interface freeze

Same AGY accepted all six follow-up points. Preparation is a distinct temporary state; only a nonempty stop_id marks a permanent Stop fence. Warning acknowledgment cannot certify a reused context. Effective allowlisted launch configuration and its fingerprint must be retained; fresh CLI capability defaults to unsupported.

The operator flow has two actions: prepare the replacement packet/contexts, then start the corrected review after all contexts are ready and clean. Preparing never dispatches. Stop remains available during preparation and permanently prevents activation. Context changes that end a persistent owned launch need exact launch confirmation; selecting an independent replacement remains explicit.

- `SessionStore.prepare_restart(parent_id, input_text, request_id, *, participant_bindings=None)` atomically links one prepared child, with new run/input identities and retained frozen design/goal/rules/cast. Same request and payload returns that child. Different payload or sibling request conflicts. Results/questions/continuations/quarantine/current invocation start empty.
- `SessionStore.activate_restart(child_id, participant_bindings=None)` accepts only an un-stopped prepared child. Eligibility becomes true only after the engine verifies readiness and context assurances.
- `SessionEngine.correct_and_restart(parent_id, input_text, request_id, *, replacements=None, confirmations=None)` prepares the linked replacement and app-owned contexts. `activate_restart(child_id)` validates all roles and dispatches the first new turn.
- New operator routes are `POST /api/sessions/{id}/correct-and-restart` and `POST /api/sessions/{child_id}/activate-restart`, plus a status read. Repeated preparation/status must not cause repeated automatic client launches.
- `cli_fresh_context_args` is a strict argv placeholder contract, with a fresh context nonce. A separate explicit verified-contract capability defaults false; ordinary/native templates are never automatically marked verified. Fake fixtures alone can establish the test adapter's fresh-context behavior. Declaring an arbitrary flag cannot silently create native verification.
- During an activated corrected review, default API/MCP history reads for its bound participants expose only that new run's accepted results/continuation context. `chat_read`, `chat_resync`, job reads and summary defaults must not reintroduce old channel content. Operator history reads and unrelated seats stay unchanged. This is an application context boundary, not a native filesystem sandbox.

Test helper owns `tests/test_corrected_restart.py` for real-store lineage/preparation/fence regressions. Codex owns additional ingress/read-scope and managed launch tests. Each implementation follows observed red evidence; same AGY remains the final independent reviewer.

## Implementation checkpoint

Core suite366 tests OK/four skips at17.822s. Helper14 lineage/preparation tests and root2 read-scope tests pass after observed red. Managed launch10 focused tests pass after identity-replacement provenance failure was fixed. Stop integration PASS155.124ms and migrated brief integration PASS with supplementary chat explicitly excluded (one fake call, actual MCP, exact source/rollover checks preserved). Fresh verified CLI process launch, engine agent-role orchestration, operator endpoints/UI and corrected mixed-team acceptance remain unfinished. No independent implementation review or publication yet.

## Runtime checkpoint and remaining contract follow-up

- Full suite386 tests OK/four skips (17.931s); real normal API-seat and CLI-seat integrations pass after factoring launch-from-effective-settings. No new native/client/provider acceptance.
- Fifteen manager/CLI contract tests and five managed agent tests pass after observed red. Per-run original provenance is captured; managed API correction/activation retains the exact supervisor/model and blocks unrelated queued work. Fresh verified CLI unit tests establish exact confirmation, matching child-exit proof, new nonce/identity/readiness and idempotent prepared attempt. They use process doubles and real receipt files, not live native clients.
- A successive-context regression caught duplicate prior context selectors. Provenance now retains actual effective settings plus a fingerprinted nonce-free context base for later corrected launches; no guessing/removing arbitrary native argv. All launch15 and agent5 tests pass.
- API/human corrected engine paths work in unit tests; CLI engine orchestration remains explicitly gated. No operator corrected-run endpoints/UI or mixed corrected-run integration exists yet.
- Same AGY is pressure-testing a separate child-only, idempotent prepared-context repair action: explicit role changes/retries with audit history, no source/design mutation or sibling runs, original parent request returns current child without reverting changes, final bindings frozen on activation. Do not kill unused owned prepared contexts automatically.
- Same AGY is also checking launch-time child/role metadata so a fresh CLI cannot default-read abandoned chat before activation or after a launch-before-backlink failure. Retained API supervisors must not be globally restricted just because a draft is prepared. This is application read scoping, not a filesystem sandbox.

Next move belongs to same AGY's contract follow-up; its response resumes Codex. The local checkpoint is incomplete and must not be published or called an implementation PASS.

## Current verification checkpoint

401 tests pass with four expected Unix/tmux skips. Operator source/context/activation routes and UI are implemented. Actual corrected integration, seven prior integrations and scoped desktop/mobile/keyboard checks pass. Same AGY Section8 contract is settled. Same AGY independent PASS and publication/closure confirmed. STATUS.md carries the current owner and remaining work.
