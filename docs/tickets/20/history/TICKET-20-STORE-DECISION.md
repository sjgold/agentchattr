# Ticket 20: choose the storage work before authoring

**Current scope amendment,2026-10-26:** Seth approved reduced20-22 first, multi-file23 next,24-26 later. [Reduced-release contract](../TICKET-20-22-REDUCED-RELEASE.md) is authoritative for this release. R3, advanced operator selection/revision/recovery UI and strict0.270s worst-case acceptance are deferred or replaced as specified there. Safety and accepted backend semantics remain. The 2026-10-25 storage decision below is retained as historical/future scope; its former next-step directions do not authorize work.

Status: SCOPE APPROVED by Seth on2026-10-25 through the structured question: "Approve R1-R3 (recommended)". This authorizes the three additional implementation/review slices. Their detailed schemas and compatibility contracts still need review; no quota, activation or R4 implementation is approved. Production artifact authoring remains disabled.

**Selected direction:** three additional storage/compatibility implementation tickets, then return to operator routes. The independent reviewer recommends R1-R3 below. They reopen the accepted unpublished store schema, so the scope was presented to Seth and explicitly approved.

The index is the JSON metadata catalog of artifact requests, versions and diagnostics. The current implementation validates and rewrites it as one unit.

## What the measurements changed

| Existing accepted shape | Measured result |
| --- | --- |
| Full diagnostic metadata: 1,024 rows, 256 dispatch summaries and one global summary | 749,818 bytes total; 749,688 bytes above an empty index |
| Body-free diagnostic example, with no overflow summaries | 545,920 bytes, already above the proposed 512 KiB ceiling |
| One ordinary max-source CLI request: 2 MiB packet, 1,000 refs, 32 KiB instruction | 293,110 index bytes after fulfilment; two take 586,096 |
| Same source limits with currently accepted escaped fields | 3,647,264 index bytes for one fulfilled request |
| Accepted API confirmed-model label | A 600,000-byte label passes the current validator |

These are temporary-store or pure-schema measurements, with no provider/native acceptance claim. The escaped case uses index-resident U+0001 characters that the proposed grammar correction would reject. The ordinary case shows that escaping is only part of the problem: provenance and source references are copied into request and version rows.

The proposed 512 KiB/128-request quota is **withdrawn**. It cannot reserve even the existing diagnostic budget. Increasing the quota alone also needs new timing evidence: a 2 MiB index pilot held the shared boundary for 0.377s; the final target is 0.270s per hold and peer wait. Earlier small-store prototype passes do not prove growth is safe.

## Proposed implementation tickets

These are planning slices, not new GitHub issues or time estimates.

| Ticket | Work and acceptance |
| --- | --- |
| R1: bound index-resident fields | Bound label-like strings to 256 UTF8 bytes and numeric widths; reject unsafe controls in index text. Keep instruction 32 KiB, format 512 bytes, packet 2 MiB and Markdown 512 KiB. Preserve source/Markdown bytes. Invalid API observations use the existing quarantined/invalid_response path. Separate red-first compatibility pin and review. |
| R2: separate diagnostic ownership | Move quarantine metadata and group/global overflow summaries out of the fully validated authoring index. Preserve 8/group, 256 groups, 1,024 records and body budgets. Design the locking, attachment/recovery seams and backup exclusions before implementation. |
| R3: compact authoring index | Keep full source refs in immutable packet/version records and digest+count in the index. Preserve provenance, claim verification, exact bytes and read projections. Re-review store, authority and archive compatibility, then re-run maximum-shape K6. |
| R4: conditional fallback | If R1-R3 still miss the timing target, design per-request incremental validation. This would be another ticket, not an automatic promise that the first three pass. |

There is no released artifact schema to migrate: Ticket 20 is unpublished and production capability is empty. Tests, goldens and the approved component contracts still need careful updates and independent review. No existing helper assertions will be silently weakened.

## Choices considered

| Choice | Cost and consequence |
| --- | --- |
| **Approve R1-R3, recommended** | Three extra implementation/review tickets before the already-planned operator package. Retest storage, admission, backup and timing. Consider R4 only if measurements still fail. |
| Plan incremental validation first | One architecture-design ticket to compare R4 before choosing R2/R3. Its implementation cost and IO behavior are not yet established. This approves design, not source changes. |
| Defer authoring | No new store implementation now. Keep authoring disabled and continue only independent wire documentation, reader contract and acceptance-harness planning. Ticket 20 remains incomplete. |

With no storage change, creation remains suitable only for small early stores and cannot satisfy the agreed growth/timing acceptance. It cannot be activated under the current contract.

**Product consequence to keep visible:** a finite per-installation quota would apply across all channels, count failed, cancelled and imported attempts, and a successful import could consume it. Exporting or deleting a channel would not free it because Ticket 20 has no purge. That 512 KiB/128-request proposal has been withdrawn; no replacement quota is selected.

The wire work can be reviewed independently in [the operator contract](TICKET-20-OPERATOR-ROUTES.md). Earlier measurements remain in [the experiment log](TICKET-20-OPERATOR-CAPACITY-EXPERIMENTS.md). Next: review the concrete R1 field/numeric/observation contract, capture its behavioral reds and obtain review of that separate compatibility pin. R2/R3 schema contracts follow before their implementation; no repeat scope question is needed.

[Visual decision memo](http://127.0.0.1:4387/session/c99a426ed6cd4630), local review surface using the existing agentchattr theme. The durable decision and numbers are in this file; the HTML adds no product behavior.

## Acceptance order and timing correction, 2026-10-26/27

Seth: "pend 21 to after acceptance" (reviewer relay). Ticket21 and22 are pending until Ticket20 acceptance. Transcript contract/reds are preserved, with9 explicit pending skips; no transcript product code is implemented. Next: one frozen full Ticket20 discovery, separate activation commit for independent review/sign-off, then21/22, final cleanup and publication only after explicit push authorization.

270ms/216ms were docs/reviewer targets without a derived baseline; reviewer withdraws them at Seth's request. Only the existing1.0s basic timing ceiling remains; import300ms is report-only. Standalone tools now use1.0s for timing failures; historical comparative values/misses remain. Safety/error/retry/ownership checks unchanged. No speed-screen tool or new timing campaign.
