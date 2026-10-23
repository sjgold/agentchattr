# Ticket #13: recover saved API results without regeneration

State: same-AGY contract Sections7.3/7.4 ratified. Storage, private brief authority, managed issuance and worker save-before-post are implemented and tested. Recovery admission, transport settlement and UI remain pending; final Ticket13 acceptance has not occurred.

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


## Frozen managed-owner metadata interface, tranche3a

SeatManager.result_owner(instance, dispatch_id) returns eitherNone (no current owned API launch) or exactly adapter='openai-compatible', dispatch_id, seat_identity_id, launch_attempt, launch_nonce and fingerprint. The latter nonce/fingerprint come from cached immutable runtime ownership/config, NOT the separate launch-provenance fingerprint. It never returns key/provider settings/credentials or grants new process control.

Validate32hex dispatch_id first (invalid raises SeatError). Require matching live registry identity, same current owned base/attempt, unreleased live process and API adapter as with launch_provenance. Unknown/manual/CLI/replaced/released/dead principals returnNone. Compare current snapshot/launch intent with manager-approved root/data/server/MCP and cached ownership; any changed evidence raises SeatError with no file/process/registry mutation. If an authenticated worker_birth is already retained, changed birth evidence fails closed as in Ticket9. No new native adoption requirement is inferred for same-boot process doubles.

Helper owns only tests/test_result_owner.py for5-7 metadata-boundary cases, captures missing-method red before root implementation. Engine issuance wiring is separate. Same AGY Section7.3 ratified the orphan-brief boundary: after a sealed brief is persisted, owner/key are immutable. Later bind/enqueue/delivery failure is a turn delivery failure; owner change requires explicit fresh Retry IDs. Prepared repair preserves reserved IDs only before sealed authority exists. No rebind/key-rotation mechanism is allowed.

Same AGY independently bounded-passed5f2ce30: dedicated24 tests and full654/four expected skips52.771s, source audit only. No final13 acceptance.


## Managed issuance evidence and next crash-boundary tests

- Helper result_owner initial2 tests produced8 missing-method AttributeError observations0.053s before implementation. Final7 pass0.775s after a test fixture included a real extra server marker to distinguish runtime ownership hash from the filtered provenance hash (simple API fixtures can legitimately have equal hashes). No production hash was changed to force inequality.
- Root normal issuance3 tests captured missing private API key/unsafe unsealed fallback red, then pass with metadata7 (10 total0.525s). API owner scope binds exact dispatch and launch; CLI/manual/human turns stay unsealed; managed owner lookup failure persists interruption/no queue. Initial root TestCase alias accidentally imported15 duplicate tests; corrected to module import before counting. Preparation failure returnsNone per existing Start contract; test reads persisted interruption rather than changing API behavior.
- Full664 first failed3 older manager doubles lacking result_owner. Added explicit metadata-only stubs to those fixtures without weakening readiness/identity/timing assertions; affected26 pass1.091s, full664 tests OK/four expected skips54.278s. No worker persistence, recovery admission or transport settlement acceptance.
- Next helper owns tests/test_result_authority_retry.py (5-7 cases) for actual persisted-brief/bind/enqueue crash gaps. Expected behavior: sealed owner/key never mutate; post-authority failure becomes a recoverable current reserved-turn delivery failure (stalled/local_delivery_failure), pending preparation no longer permits replacement under those IDs; explicit new Retry creates fresh IDs. If exact enqueue was already committed, finalize existing pending bookkeeping without duplicate context/dispatch or deadline reset. Stop remains permanent. No model invocation is inferred from missing queue records. Missing/malformed authority evidence fails closed before process control.


## Post-authority failure evidence

Helper tests/test_result_authority_retry.py captured initial2 FAIL0.183s (bind gap active, enqueue gap retrying), then expanded7 FAIL0.617s including original-request replay re-entering context preparation after committed enqueue. Root implementation now passes unchanged7 in0.657s. A separate atomic SessionStore transaction reconstructs only the already-reserved invocation from its durable sealed brief, exposes stalled/local_delivery_failure when no queue record exists, and removes preparation pending. A new explicit Retry uses fresh IDs. If exact enqueue already committed, finalize bookkeeping without another context/dispatch or deadline reset. Stop wins; no key/owner bytes mutate. Full671 tests OK/four expected skips55.327s; no model invocation is inferred from unpublished work. No worker result persistence/delivery/recovery claim yet.

## Frozen worker delivery component, tranche4

New module result_delivery.py, to be tested before implementation:

```python
def complete_review_turn(runtime_path, envelope, dispatch_id, generate, submit, *, on_saved=None): ...
```

Caller already owns the queue claim; this is not a second scheduler or process-adoption mechanism. envelope is the existing get_delivery response with private seal_secret and exact result_owner. Validate that scope and the managed ResultOutbox snapshot BEFORE generate. Invalid/missing key or changed launch/scope cannot invoke the model. generate() returns the raw provider response text once; strict parse_session_response yields final/question. Provider/cancellation/validation failures propagate with no saved record or submit.

Build the exact tranche1 payload from the trusted envelope/owner, result=dispatch=event ID, and creation time. Atomically ResultOutbox.save before the first submit. Call on_saved(result_id), if supplied, only after a valid sealed result exists. Key never enters payload, submit event, model request or ack.

submit(event) is a callback to the existing authenticated session-event HTTP request. Its exact event fields are brief_id, kind, content, event_id, run_id, turn_id, attempt_id and input_revision. It returns parsed server JSON or raises urllib/OSError. Accept status='admitted' only with exact event_id. Identical accepted_event_id in HTTP409 is idempotent success. HTTP5xx and OSError retry at most3 total attempts with the SAME event and no generate/save repetition; other4xx or malformed/wrong ack fail. On success, persist separate ResultOutbox.acknowledge and return {status:'admitted', result_id}. Ack-write failure propagates after the one admission, retaining the immutable saved record; do not regenerate or claim local ack.

Add ResultOutbox.find(result_id): read-only schema/launch-validated record orNone only on genuine missing result path; malformed/unreadable/symlink cases fail, never mean absent. Existing get semantics unchanged. If complete_review_turn finds an existing record, verify it with the current trusted key, call on_saved and return {status:'saved', result_id}, with ZERO generate or submit calls. This implements explicit cold recovery posture; operator recovery is a later component. A saved record is not by itself a claim that current Stop/Retry fences allow delivery.

Helper owns only tests/test_result_delivery.py, bounded10-12 cases using real isolated structural runtime/outbox and injected generation/HTTP callbacks. No model subprocess/native proof or full wrapper/engine acceptance inferred. Root wires wrapper only after the component's early red and green, and separately tests saved status versus current recoverability/fences.


## Worker delivery component evidence, not wrapper acceptance

Initial helper3 errors0.005s were missing result_delivery before implementation. New component/find now passes12 tests (root1.703s); core storage18 remains unchanged/green. One extended test fault initially patched read_text although storage uses open('rb'); correcting the fixture seam retained unreadable/no-generation assertions and passed. Callback transport verifies bounded3 same-event attempts/one generation, real signed save before submit, failed save/ack replacements, exact409 duplicate, malformed/wrong ack denial and explicit existing-record posture. This is not actual HTTP/session admission proof.

Full683 tests OK/four expected platform skips56.104s. Same AGY bounded650 source PASS remains separate: frozen671 tests; its shared-tree674 execution included first3 evolving delivery tests/refactor and is labelled accordingly in the audit. No final13 review.

New draft tools/verify_result_outbox.py uses actual full app/two API workers/local fake provider. Phase1 accepted, phase2 provider body held until retained true server/workers/model proof; exact phase2 event service returns503 on3 posts. It checks a valid sealed file existed BEFORE each post, first result ACK, second result without ACK, prior/source retained, zero regeneration and key exclusion from actual provider/public/MCP/status/log surfaces. Root reviewed full fault/cleanup and compile-only; ONE baseline run against still-unwired wrapper is authorized. Expected gap is missing outbox before post. No execution result is claimed yet; wrapper wiring waits for the observed baseline.


## Actual worker persistence evidence and shared-lock correction

Unwired baseline4p0fj60e failed before first-post persistence: exactly2 provider calls,1 prior admission and3 same-event503 posts, all without outbox records. After wrapper wiring, the unchanged r7hsjjtw tool passed with a signed scoped record before each post, first result plus separate ACK, second saved result without ACK, exact Unicode/CRLF and no regeneration. Both keys stayed out of actual provider/MCP/public status/log surfaces; idle peer remained ready/unchanged. Native retained-handle cleanup unresolved[]. No cold delivery/UI claim.

First post-wiring full683 run failed at startup_lock initialization flush during concurrent queue writes. Native empty-file contention reproduced PermissionError before the bounded lock loop. Removing the unnecessary initialization write permits direct kernel exclusion on empty files. Launcher/queue/outbox49 tests pass2.865s including independent-process exclusion; full684 tests OK/four expected skips56.313s. Earlier failure retained. Same AGY bounded checkpoint review precedes further recovery implementation.

## Ratified recovery boundary, Section7.4

Operator-only GET /api/sessions/{session_id}/saved-results returns sanitized text preview and metadata, with no key/internal path. Operator-only POST /api/sessions/{session_id}/deliver-saved-result serializes under the engine coordinator RLock. Verify seal/scope first; an exact already-admitted result receives idempotent accepted_event_id even after Stop/Retry. A pending unadmitted result must pass current Stop/superseded fences. SessionStore.admit_verified_saved_event preserves original signed identity, provenance verified_saved_api_result and submitted_by operator, without synthesizing a live principal. Recovery never calls a provider or spawns.

SeatManager.saved_result_exit_proof(payload) verifies trusted exact launch/nonce/fingerprint against cached immutable ownership/birth. Prefer an already retained true-worker handle (worker_process when the launcher is a shim), genuine observed exit and exact model lifecycle evidence; fall back to cold runtime_exit_proof. Query never closes/reopens/terminates handles or extends a lease. Wrapper and model child must both be ended. Content admission remains independent of this process-control proof.

QueueStore.settle_recovered is internal-only. Proven ended transport becomes settled_recovered with source result_recovery and genuine verification basis; preserve old consumer/history and never invent acknowledgements, exit codes or cancellation IDs. Cancelling records remain governed by Stop. Unproven exit keeps only that occupied seat held, allowing unrelated verified successor seats to proceed. Worker receipt result_saved=True/recoverable_result=None is provisional; server current fences determine eligibility. Detailed component interfaces will be frozen before their observed-red tests.
