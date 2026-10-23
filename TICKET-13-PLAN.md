# Ticket #13: recover saved API results without regeneration

State: same-AGY contract and all five source-grounded refinements ratified. Core storage and private-brief interfaces frozen below; bounded storage/private-authority implementation and unit checks pass. Managed launch issuance, worker persistence/delivery, recovery admission and UI remain unwired.

Base: published main2bdbc777b5ab8e254b36e54cd784a469d02720b4. Branch: codex/ticket-13-api-result-outbox. Scope authority: issue13, specificationv1.7 SC-5/AT-21c, standing autonomous execution policy in STATUS.md. Same Antigravity independent reviewer remains assigned.

## Required behavior

Before a completed API review result is posted, save it atomically with stable result, seat/instance, run/turn/attempt/input and brief/dispatch identities, kind/content and creation time. Posting failure, lost acknowledgement and restart must permit delivery of that same result without calling the model again or advancing twice. If generation, strict response validation or durable persistence fails, report that no saved answer is recoverable. Never accept stopped, corrected-source or superseded work as a current result.

Ratified bounded scope is managed frozen API review turns, including typed questions. Ordinary API chat/jobs and unmanaged compatibility wrappers retain existing behavior and make no new outbox claim. CLI selected-message recovery belongs to14, participant replacement/skip to15 and later tickets. Same-AGY critique explicitly ratified this scope.

## Current mechanisms and gaps

- wrapper_api.handle_trigger validates final/question JSON, uses dispatch_id as stable event_id, tries the same post up to3 times, then reports local_delivery_failure. Its processed_dispatch guard prevents a second model call only within that process.
- The HTTP event handler already reports identical accepted_event_id on a duplicate409 after validating original seat identity/content/kind/immutable references. Session admission and projection are durable/idempotent. There is no worker result outbox.
- Queue ownership belongs to the original consumer until its explicit receipt. Starting a different wrapper cannot adopt held work. Result admission remains distinct from transport release.
- A targeted worker restart revokes its bearer. A new identity cannot post an old brief as if it were the original seat. Native process metadata alone does not authenticate result content.
- Ticket9 now provides exact launch/model-child evidence and internal cancellation settlement, but that settlement is bound to a Stop/Retry cancellation ID. It cannot be repurposed as a fictional worker acknowledgement.

## Settled mechanism

The reviewer rejected a separate pre-generation ticket endpoint/store as unnecessary. Reuse the existing authenticated brief fetch instead: generate one random256-bit symmetric seal_secret with the durable managed API brief, retain the key privately on the server, and deliver it to the exact authenticated expected API worker during its existing HTTP GET. No asymmetric signing or extra request/key database is required. Stable result_id == dispatch_id == event_id.

The worker holds the key in memory, validates final/question output, computes HMAC-SHA256 over deterministic UTF-8 payload bytes (sorted keys, compact separators, finite JSON), and atomically writes the sealed outbox before posting. Outbox content includes the seal, never the key, seat bearer or provider credential. Recovery verifies the original saved result without reviving a bearer or fabricating a live principal.

Ratified isolation: BriefStore.get is also used by MCP, operator views and admission. Its default result must redact private keys. Only the existing authenticated HTTP delivery to the exact managed API owner may expose the key. No key in CLI/human briefs, model messages, API model-child packet, outbox, receipts, logs, exports or public provenance. Identical immutable put retries retain the original key; legacy briefs are not silently rewritten. Existing brief_messages allowlists prompt fields, but this gets an explicit leak regression.

HMAC proves payload integrity relative to a trusted server-held key. It does not protect against an actor who can rewrite the trusted brief/key store. Actual runtime path remains data/api_seat_runtime/<launch_attempt>/outbox/<dispatch_id>.json.

## Separate content admission and transport settlement

Ratified: admission alone cannot release transport or prove worker/model exit. A distinct internal settled_recovered operation requires exact original launch/dispatch lifecycle evidence from Ticket9, stores source=result_recovery and a genuine verification basis, and never forges consumer acknowledgement, exit codes or Stop/Retry cancellation IDs.

Ratified: hold only the occupied seat/dispatch. Do not globally disable an unrelated verified successor seat after content is accepted. Existing queue ownership and cold readiness boundaries still prevent execution in the occupied seat. If the original lifecycle remains unproven, preserve transport ownership visibly; its live original worker may send its real release.

Ratified: an exact already-admitted result remains idempotently acknowledgeable after a later Stop/Retry because no new admission occurs. An unadmitted pending result for stopped/superseded/corrected work rejects409. Recovery must validate the original stable identity and immutable fields before either disposition.

## Proposed data and failure boundaries

One immutable outbox record per result_id under a validated managed runtime path. Use current kernel-lock/atomic-replace patterns; reject path traversal, schema drift, duplicate IDs with changed content and malformed/tampered records without rewriting them. Preserve exact Unicode/newlines and enforce existing event byte limits without truncation.

Immutable payload: version, result_id, dispatch_id, session_id, brief_id, run_id, turn_id, attempt_id, input_revision, seat_identity_id, launch_attempt/nonce/fingerprint, kind, content, created_at and HMAC seal. No whole prompt/source snapshot, credentials, raw provider errors or unrelated context. Exact core allowlist is frozen below.

Delivery acknowledgement is separate mutable bookkeeping. A crash after server admission but before local ack persistence leaves a pending record; retry must identify the exact already-accepted result and mark acknowledged without another admission or model call. Changing content/kind/scope under the same ID must conflict. Local acknowledgement-write failure must remain truthful even when the server already accepted.

Generation error, invalid/empty discriminator or outbox write failure means recoverable_result=false. Failed persistence must prevent the first post. A completed response that was not saved cannot be advertised as recoverable. Reuse local_delivery_failure with a distinct safe diagnostic unless the reviewer finds a separate typed category necessary.

Do not delete pending or rejected saved content as cleanup. Preserve blocked stale results for audit, with no automatic old-result attachment after Retry/Stop/correction. Retention policy is outside this ticket unless bounded storage requires an explicit choice.

## Proposed operator and restart behavior

After3 bounded normal delivery attempts fail, show Saved answer available and Deliver saved answer, distinct from Generate again. An explicit delivery action never calls the provider. Repeated actions are idempotent. During normal operation, duplicate successful-post acknowledgements may resolve automatically under the current existing retry budget.

Cold discovery validates existing outbox records without spawning a worker or re-invoking the model. Ratified default is visible operator-directed delivery after cold discovery, preserving the spec's user-directed recovery posture. No automatic cold conversation advancement. Old outboxes must remain discoverable after explicit wrapper replacement, even if the old bearer is revoked.

UI shows pending/saved/delivered/blocked state and safe reason, original seat/turn and exact result preview. Content is rendered as text. Stopped or superseded attempts have no enabled delivery action; a new generation remains a separate explicit Retry with fresh IDs. Wrong-seat/cross-run/corrected-source substitutions are rejected.

## Concurrency and ordering

Use the existing coordinator RLock for recovery versus Stop/Retry/Continue/admission. Store locks remain sequential and non-nested; no cross-store calls under another store's lock. Avoid a distributed transaction:

1. Persist private per-brief key/binding and fetch through the existing authenticated brief route before generation.
2. Generate once, parse/validate, atomically save signed immutable outbox.
3. Attempt exact typed result delivery with stable result_id.
4. Server durably admits once, projects via existing journal/add_once and returns acknowledgement.
5. Persist local acknowledgement. Duplicate exact admission resolves the lost-ack gap.
6. Settle transport separately only with real ownership/end proof.

If Stop or Retry wins the coordinator lock first, saved-result delivery cannot bypass its fence. If result admission wins first, it remains accepted; Stop cancels successors. Recovery must retain prior accepted work and all frozen policies.

## Observed-red and acceptance plan after settlement

Tests must precede production implementation. Existing helper authors bounded outbox/delivery cases against frozen interfaces, root covers authority/routes/concurrency; same AGY supplies final independent review.

- Atomic initial save and ack failures preserve disk/memory, no first post on save failure, no fake recoverable flag.
- Exact Unicode result, strict schema/path limits, seal/key-exposure and payload tamper, wrong seat/run/brief/input and changed same-ID content.
- Post outage leaves one saved answer and one generation. Actual wrapper restart/server crash recovery delivers it without another call.
- Successful admission followed by lost HTTP acknowledgement and failed local ack persistence produces one result/phase advancement/chat projection across reload.
- Stop, Retry, corrected source and concurrent delivery retain durable fencing; no implicit old-result recovery or peer interference.
- Original bearer revoked and new worker identity differs; recovery preserves authentic saved-result provenance without pretending the new worker owns the old brief.
- Exact transport remains held when end is unproven; proven old lifecycle permits explicit internal settlement with no fake receipt.
- Real isolated local provider/Windows workers, retained native handles, bounded fault seams and complete cleanup. No live providers/native AI/Omarchy. Browser refresh and explicit Deliver saved answer distinct from Retry; full suite/prior relevant integrations.

Implementation begins only after the consequential choices are settled with the same reviewer under the standing autonomous policy. Unresolved reproduced correctness disputes use the recorded Astra escalation procedure, never automatic extra model spawning.


## Frozen core storage interface, tranche1

New module result_outbox.py (not implemented at freeze):

```python
class OutboxError(ValueError): ...
class OutboxConflict(OutboxError): ...

def seal_result(payload, seal_secret): ...  # -> {"payload": deep copy, "seal": hex SHA256 MAC}
def verify_result(record, seal_secret): ...  # -> verified deep-copy payload; mismatch raises OutboxError

class ResultOutbox:
    def __init__(self, runtime_path): ...
    def save(self, payload, seal_secret): ...  # immutable, idempotent -> sealed record
    def get(self, result_id): ...  # schema-validated record, not an authentication claim
    def list_records(self): ...  # sorted immutable records, malformed final JSON fails closed
    def acknowledge(self, result_id, accepted_event_id): ...  # -> durable ack, exact matching IDs
    def get_ack(self, result_id): ...  # -> ack dict or None
```

Exact payload fields: version, result_id, dispatch_id, event_id, session_id, brief_id, run_id, turn_id, attempt_id, input_revision, seat_identity_id, launch_attempt, launch_nonce, fingerprint, kind, content, created_at. No optional unknown fields. version is literal int1; IDs are32 lowercase hex except positive-int session_id,64hex input_revision/fingerprint, and turn_id equal to run_id + ':' + nonnegative phase + ':' + nonnegative turn. result_id == dispatch_id == event_id. created_at is positive finite int/float, booleans rejected. kind/content obey turn_events.validate_content and its512KiB UTF-8 bound. No Unicode/newline normalization.

seal_secret is64 lowercase hex encoding32 random bytes. HMAC key is bytes.fromhex(seal_secret). MAC covers only payload JSON with ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False encoded UTF-8. Use compare_digest. Record exactly {payload, seal}; mutable acknowledgement never changes sealed bytes.

ResultOutbox validates existing runtime config through runtime_ownership._validate and accepts only managed openai-compatible snapshots. save additionally binds launch_attempt/nonce/fingerprint to that snapshot. This is structural storage validation, never runtime adoption or result authenticity by itself. get/list perform schema and launch checks; authentication is explicit verify_result with the trusted brief key. Legacy/unmanaged/CLI paths fail closed without mutation.

Result file is runtime_path/outbox/<result_id>.json. Separate acknowledgement at runtime_path/outbox_ack/<result_id>.json contains exactly version, result_id, accepted_event_id and acknowledged_at (finite positive timestamp). Acknowledgement writes require an existing valid result; repeat ack retains the original ack bytes/time. Read-only get_ack(validID) returnsNone when both result and ack are absent; orphan/malformed ack fails closed. One shared per-result kernel lock serializes save/ack. Use existing atomic_json; failed writes preserve prior immutable result/ack and do not leak a failed record into a later save. Identical saves return original bytes; changed payload under the same ID raises OutboxConflict. Read/list do not create files. Reject invalid IDs/path escape/symlink targets; temporary/lock files are not recoverable results and remain ignored/preserved.

No arbitrary directory scan or native process is needed for tranche1. Use structurally valid isolated ownership snapshots; no fake OS ownership claim. Test helper owns only tests/test_result_outbox.py. Root writes private brief delivery and later engine/HTTP tests separately after their own frozen interface tranche.

## Implementation sequence

- [x] Helper captured missing-module/core-storage red, then18 bounded atomicity/HMAC/schema/identity/path/concurrency tests pass. Root waits for early red before creating result_outbox.py.
- [x] Root implements minimal storage/sealing:18 tests pass, including actual6 threads/3 subprocesses and native symlink refusal. No delivery/recovery claim yet.
- [ ] Root freezes BriefStore key issuance/redaction/HTTP-only delivery interface, captures red leak/identity/immutable retry tests, implements and checks prompt/child/outbox exclusion.
- [ ] Freeze engine recovery/discovery and operator routes: exact sealed result provenance, duplicate acknowledgement versus pending stale409, transport settlement only with original supervisor+exact model end proof. Helper authors bounded red cases; root owns authority/race tests.
- [ ] Wire worker save-before-first-post and durable ack, bounded3 delivery attempts and explicit cold recovery; generation/persistence failures never claim a saved answer. No automatic cold model invocation or result admission.
- [ ] Actual isolated fake-provider/worker integration exercises post outage, lost ack, explicit wrapper/server restart with revoked original bearer, real end proof/held transport, Stop/Retry/corrected source and peer isolation. Complete retained-handle cleanup on failure. Browser explicit saved-answer delivery/preview/refresh distinct from Retry.
- [ ] Freeze final target, full suite/appropriate prior tools/static checks and same-AGY independent reproduction/recheck. Publish/close only after PASS under standing authorization.


## Frozen private-brief interface, root tranche2

BriefStore.put(envelope, *, result_owner=None) may seal only when the internal result_owner exactly contains adapter='openai-compatible', dispatch_id, seat_identity_id, launch_attempt, launch_nonce and fingerprint. IDs/fingerprint follow tranche1 format; seat_identity_id must equal expected_identity_id, and completion_protocol must be literal int1. The engine derives this internal owner from the actual managed launch's runtime ownership, not from request-provided IDs or the distinct launch-provenance fingerprint. Generic plain/legacy/CLI/human briefs get no private key. Incoming public envelopes cannot set reserved seal fields.

Persist private _result_seal={version:1, seal_secret:64hex, owner:result_owner} once, under the existing brief lock. Identical put preserves exact file bytes and key; changed owner/public context conflicts. Never add a key to an existing unsealed legacy brief by replay. Default get (including operator=True) strips private metadata. A public-envelope replay with no result_owner cannot downgrade an already sealed record.

BriefStore.get_delivery(brief_id, instance) authorizes the exact expected identity and returns the normal envelope plus seal_secret/result_owner only when the private managed API metadata exists. This is used only by the existing authenticated HTTP handler for an actual resolved bearer; operator-only reads and MCP keep calling default get. The key is not copied into model messages or child invocation packets.

BriefStore.verify_saved_result(record) is an internal server method: validate strict sealed record, read its private brief key, verify HMAC, compare session/brief/run/turn/attempt/input identities plus exact owner dispatch/seat/launch/nonce/fingerprint, and return only a verified payload. It does not admit, check live principal, settle transport or return the key. Missing/private malformed/legacy records fail closed. Recovery engine later checks current authority/fences under its lock. These methods alone do not grant process control.


## Foundation evidence, not Ticket13 acceptance

- Helper initial3/3 errors0.005s were missing result_outbox before implementation. Extended18 initially16 pass/2 errors: true concurrent peer-locked Windows resolve returned equivalent extended path spelling and triggered a false redirect guard; get_ack absent-result query semantics needed clarification. Root reproduced the exact extended-prefix mismatch, normalized equivalent Windows/UNC path spellings without accepting symlink escapes, and kept absence read-only while requiring existing results for ack writes. Unchanged18 PASS1.144s. All owned child processes bounded/waited; no provider/native ownership claim.
- Root private-brief initial3 and expanded4 errors before implementation (missing put keyword/get_delivery). Private key/stable immutable retries, exact matching identity, legacy non-upgrade, sealed saved-result scope verification pass. Actual authenticated HTTP test then failed because handler used redacted get; after exact-owner get_delivery wiring,6 private tests plus2 prior endpoint tests PASS0.450s. MCP and operator reads stay redacted; brief_messages excludes the key. Production engine does not issue result_owner yet, so no current managed turn is advertised as saved/recoverable.
- Full654 tests OK/four expected platform skips53.118s; diff whitespace clean. No actual outbox save-before-post/restart delivery, provenance admission, transport settlement or browser recovery pass claimed. Those remain next tranches.
