# Ticket #11: correct the document and restart cleanly

**State:** Proposed contract for same-AGY pressure-test. No #11 production changes or implementation tests yet.

**Authority:** Approved issue #11, spec v1.7 SC-3 and AT-07, October22 autonomous execution amendment. Its only blocker #10 is published/closed. Base main `83aa04a`. Full runtime restart adoption (#9), failure/retry/outbox recovery (#12) and file intake (#18) remain separate scope.

## Verified baseline

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

- [ ] Same AGY pressure-tests and resolves the clean-context/provenance/preparation contract.
- [ ] Test-only helper captures real red lineage/isolation/race regressions against agreed interfaces.
- [ ] Codex implements linked preparation, new-run input isolation and bounded context preparation.
- [ ] Implement operator source preview/impact/blocked/restart controls and real fake-client verification.
- [ ] Freeze, same-AGY independent review/recheck, reviewed publication and issue closure.

Next owner: same AGY returns a contract critique. Codex settles bounded choices, records rulings and begins red tests. No #11 implementation or native/live-provider usage is claimed. Routine human plan/completion gates remain removed by the standing authorization.
