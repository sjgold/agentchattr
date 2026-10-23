# Ticket #13: recover saved API results without regeneration

State: proposed contract for same-AGY critique. No implementation or red tests yet. Open choices below are not settled.

Base: published main2bdbc777b5ab8e254b36e54cd784a469d02720b4. Branch: codex/ticket-13-api-result-outbox. Scope authority: issue13, specificationv1.7 SC-5/AT-21c, standing autonomous execution policy in STATUS.md. Same Antigravity independent reviewer remains assigned.

## Required behavior

Before a completed API review result is posted, save it atomically with stable result, seat/instance, run/turn/attempt/input and brief/dispatch identities, kind/content and creation time. Posting failure, lost acknowledgement and restart must permit delivery of that same result without calling the model again or advancing twice. If generation, strict response validation or durable persistence fails, report that no saved answer is recoverable. Never accept stopped, corrected-source or superseded work as a current result.

Proposed bounded scope is managed frozen API review turns, including typed questions. Ordinary API chat/jobs and unmanaged compatibility wrappers retain existing behavior and make no new outbox claim. CLI selected-message recovery belongs to14, participant replacement/skip to15 and later tickets. Ask the reviewer to challenge this scope if issue13 requires broader delivery.

## Current mechanisms and gaps

- wrapper_api.handle_trigger validates final/question JSON, uses dispatch_id as stable event_id, tries the same post up to3 times, then reports local_delivery_failure. Its processed_dispatch guard prevents a second model call only within that process.
- The HTTP event handler already reports identical accepted_event_id on a duplicate409 after validating original seat identity/content/kind/immutable references. Session admission and projection are durable/idempotent. There is no worker result outbox.
- Queue ownership belongs to the original consumer until its explicit receipt. Starting a different wrapper cannot adopt held work. Result admission remains distinct from transport release.
- A targeted worker restart revokes its bearer. A new identity cannot post an old brief as if it were the original seat. Native process metadata alone does not authenticate result content.
- Ticket9 now provides exact launch/model-child evidence and internal cancellation settlement, but that settlement is bound to a Stop/Retry cancellation ID. It cannot be repurposed as a fictional worker acknowledgement.

## Candidate approaches

| Approach | Benefit | Cost or risk |
| --- | --- | --- |
| Worker outbox plus current original bearer only | Smallest change; preserves existing admission API | Cannot recover after explicit worker replacement revokes that bearer; incomplete restart acceptance |
| Treat local outbox files as trusted original-seat assertions | Simple operator-driven recovery | Cannot distinguish edited content/seat metadata from the original worker output; weaker provenance boundary |
| Scoped pre-generation result ticket plus authenticated/sealed worker outbox (proposed) | Preserves original result authority across worker exit without reviving a bearer or granting process control | Adds a narrow durable ticket/key record and recovery ingress; needs explicit review |

## Choice1, OPEN: durable result authority after worker death

Propose a server-issued, per-dispatch result ticket obtained over the existing authenticated connection before generation. Server resolves the actual queue owner and immutable active invocation, assigns one stable result_id and a scoped signing key, and persists that binding atomically. Identical ticket requests return the same binding; changed scope conflicts.

The worker keeps the signing key in memory only, validates the provider result, signs a canonical exact record and writes it atomically under that launch's outbox before attempting delivery. The outbox contains the signature, never the signing key, seat bearer or provider credentials. A private app-data ticket store retains the verifier key; it is not a public endpoint or launch-provenance export. No global/native credential changes.

After the original identity is gone, an operator-only recovery endpoint can verify the stored ticket/signature and exact immutable references. It records explicit saved-API-result provenance with original identity and operator recovery attribution. It never calls the live-bearer admission path using a fabricated principal and never reactivates an old bearer.

Critique request: is this ticket boundary necessary, or does an existing narrower authenticated durable capability suffice? If using a signature, settle canonical bytes, key storage/issuance, ticket lifetime and the exact relationship between result_id and event_id before tests. No cryptographic claims should be made for unhashed local-file metadata alone.

## Choice2, OPEN: result admission versus old transport ownership

Admission and release must remain separate operations. A saved result can be valid while transport is still held. Recovering content must not automatically assert that a live or unproven worker/model ended.

Propose a distinct internal exact-dispatch transport settlement after recovery only when existing Ticket9 runtime_exit_proof proves the original supervisor/model lifecycle ended, bound to the original launch/dispatch. Record source=result_recovery and the genuine verification basis. Never forge consumer/bearer acknowledgement, invent an exit code or reuse Stop/Retry cancellation IDs.

If local end remains unproven, the result may be accepted under normal unfenced authority but the old transport stays held and visible; a dependent turn cannot execute in that occupied seat. The live original wrapper may still send its normal release. Critique the minimal safe settlement interface and whether additional dispatch readiness gating is needed.

## Proposed data and failure boundaries

One immutable outbox record per result_id under a validated managed runtime path. Use current kernel-lock/atomic-replace patterns; reject path traversal, schema drift, duplicate IDs with changed content and malformed/tampered records without rewriting them. Preserve exact Unicode/newlines and enforce existing event byte limits without truncation.

Immutable payload: version, result_id, dispatch_id, session_id, brief_id, run_id, turn_id, attempt_id, input_revision, seat_identity_id, launch_attempt/nonce/fingerprint, kind, content, created_at and ticket reference/signature. No whole prompt/source snapshot, credentials, raw provider errors or unrelated context. Precise allowlist is proposed, not frozen yet.

Delivery acknowledgement is separate mutable bookkeeping. A crash after server admission but before local ack persistence leaves a pending record; retry must identify the exact already-accepted result and mark acknowledged without another admission or model call. Changing content/kind/scope under the same ID must conflict. Local acknowledgement-write failure must remain truthful even when the server already accepted.

Generation error, invalid/empty discriminator or outbox write failure means recoverable_result=false. Failed persistence must prevent the first post. A completed response that was not saved cannot be advertised as recoverable. Reuse local_delivery_failure with a distinct safe diagnostic unless the reviewer finds a separate typed category necessary.

Do not delete pending or rejected saved content as cleanup. Preserve blocked stale results for audit, with no automatic old-result attachment after Retry/Stop/correction. Retention policy is outside this ticket unless bounded storage requires an explicit choice.

## Proposed operator and restart behavior

After3 bounded normal delivery attempts fail, show Saved answer available and Deliver saved answer, distinct from Generate again. An explicit delivery action never calls the provider. Repeated actions are idempotent. During normal operation, duplicate successful-post acknowledgements may resolve automatically under the current existing retry budget.

Cold discovery validates existing outbox records without spawning a worker or re-invoking the model. Proposed default is visible operator-directed delivery after cold discovery, preserving the spec's user-directed recovery posture. Critique whether the acceptance contract requires additional automatic bounded delivery on wrapper startup. Old outboxes must remain discoverable after explicit wrapper replacement, even if the old bearer is revoked.

UI shows pending/saved/delivered/blocked state and safe reason, original seat/turn and exact result preview. Content is rendered as text. Stopped or superseded attempts have no enabled delivery action; a new generation remains a separate explicit Retry with fresh IDs. Wrong-seat/cross-run/corrected-source substitutions are rejected.

## Concurrency and ordering

Use the existing coordinator RLock for recovery versus Stop/Retry/Continue/admission. Store locks remain sequential and non-nested; no cross-store calls under another store's lock. Avoid a distributed transaction:

1. Persist ticket/binding before generation.
2. Generate once, parse/validate, atomically save signed immutable outbox.
3. Attempt exact typed result delivery with stable result_id.
4. Server durably admits once, projects via existing journal/add_once and returns acknowledgement.
5. Persist local acknowledgement. Duplicate exact admission resolves the lost-ack gap.
6. Settle transport separately only with real ownership/end proof.

If Stop or Retry wins the coordinator lock first, saved-result delivery cannot bypass its fence. If result admission wins first, it remains accepted; Stop cancels successors. Recovery must retain prior accepted work and all frozen policies.

## Observed-red and acceptance plan after settlement

Tests must precede production implementation. Existing helper authors bounded outbox/delivery cases against frozen interfaces, root covers authority/routes/concurrency; same AGY supplies final independent review.

- Atomic initial save and ack failures preserve disk/memory, no first post on save failure, no fake recoverable flag.
- Exact Unicode result, strict schema/path limits, signing/ticket tamper, wrong seat/run/brief/input and changed same-ID content.
- Post outage leaves one saved answer and one generation. Actual wrapper restart/server crash recovery delivers it without another call.
- Successful admission followed by lost HTTP acknowledgement and failed local ack persistence produces one result/phase advancement/chat projection across reload.
- Stop, Retry, corrected source and concurrent delivery retain durable fencing; no implicit old-result recovery or peer interference.
- Original bearer revoked and new worker identity differs; recovery preserves authentic saved-result provenance without pretending the new worker owns the old brief.
- Exact transport remains held when end is unproven; proven old lifecycle permits explicit internal settlement with no fake receipt.
- Real isolated local provider/Windows workers, retained native handles, bounded fault seams and complete cleanup. No live providers/native AI/Omarchy. Browser refresh and explicit Deliver saved answer distinct from Retry; full suite/prior relevant integrations.

Implementation begins only after the consequential choices are settled with the same reviewer under the standing autonomous policy. Unresolved reproduced correctness disputes use the recorded Astra escalation procedure, never automatic extra model spawning.
