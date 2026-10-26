# Ticket 20 artifact-store payload freeze candidate

Status: independently PASS at d94f251 by full document read; final F1-F4 clarifications folded below, helper cleared for the initial two REDs. Store implementation waits for those REDs; expanded helper execution waits for readiness. Task0 at65bcb56 independently PASS (reviewer82/9.855s,3000 seeded MAC comparisons/no mismatch, read/error parity5 cases, private imports intact; full1374/four skips108.397s builder-only). This document covers the STORE only. No queue, adapter, public route, renderer or admission authority is implemented by this package.

R1 compatibility candidate (independent production review pending): primitive bounds below are strengthened without new persisted keys, budgets, dispatch behavior or source/Markdown normalization. Current implementation and verification receipts are in [TICKET-20-STORE-BOUNDS.md](TICKET-20-STORE-BOUNDS.md). Production capability remains empty.

## Paths and policy boundary

NEW `artifact_store.py`, `ArtifactStore(data_dir, *, hold_unreadable=False)`. Public `.path` is `data_dir/artifacts/index.json`. Immutable version bytes use `artifacts/objects/<version_id>.md`; exact source packets use `artifact_briefs/packets/<packet_id>.json`. Paths derive only from validated IDs, reject redirected paths and never use a title/path supplied by a producer. Constructor on absent data returns empty in memory without writing files. Default unreadable/malformed storage raises `ArtifactUnavailable`; `hold_unreadable=True` returns a held owner with generic errors and unchanged files.

Error classes: `ArtifactValidationError(ValueError)`, `ArtifactConflict(ChannelConflict)`, `ArtifactUnavailable(ChannelUnavailable)` (the latter two preserve existing409/503 family mappings). Existing ChannelInactive/ChannelUnavailable policy refusals propagate. The initially closed getter raises ArtifactUnavailable before ordinary writes. I/O failures map to unavailable without content/path echo. JSON load rejects duplicates, nonfinite/nonnumeric timestamp/schema/type errors and invalid UTF-8. Formatting-only external edits may revalidate; changed authoritative content holds for repair, never silently replaces memory or overwrites it. Use fingerprint-cached validation as in configured jobs/summaries.

`bind_channel_policy(getter)` stores a callable without entering policy under the store lock. Ordinary writes start closed until bound, then enter the existing engine/catalog boundary before taking the store lock. `put_packet`, new reserve_request and new commit_version effects require the ACTUAL target channel active. Read-only exact replay of an existing request or fulfilled version may return its stored row on an inactive channel without changing anything. Trusted status/quarantine/rename phases below are low-level and bypass the active check so Stop/cancellation/diagnostics remain possible while the catalog is held. They require a healthy index and their own lock; per-object corruption is scoped below, not a global owner hold; ArtifactService later owns external authorization and engine serialization. No store method dispatches or calls a provider. Reads stay available for inactive channels.

Lock order is explicit: ordinary policy boundary first, then store lock; low-level phases take only the store lock. No method calls the policy getter while holding the store lock. ChannelService must call rename_channel inside its own engine/catalog boundary.

All returned objects are detached. No method exposes seal material; it is absent from these schemas. Callbacks are out of scope for this store slice; later service events happen after durable commit.

## Primitive types and deterministic IDs

- IDs are exact lowercase32-hex UUIDs; hashes exact64-hex SHA-256. Message ids are exact int in 0..2**63-1 (bool refused). Legacy message UIDs use explicit `legacy:<id>` when an original UID is absent; otherwise preserve the actual nonempty string UID, capped at 256 UTF8 bytes and refusing C0/DEL label controls. A real uid such as legacy:5 may collide with the missing-UID fallback for id5; duplicate-UID refusal is intentional, never silently rename either source.
- Channel names use the existing lifecycle grammar. Record timestamps are finite positive exact int/float (bool refused), ints <=2**63-1 and float JSON tokens <=23 characters. Other record integers share the63-bit maximum with existing narrower limits retained. Requester/producer/model/observation/source-run-state/ref-UID labels are <=256 UTF8 bytes, nonblank, refusing C0/DEL. Raw packet body text and arbitrary source metadata retain their prior UTF8/NUL/JSON policy under the packet cap. No text is trimmed or normalized on persistence.
- `request_ids(request_id) -> {lineage_id, attempt_id, dispatch_id, brief_id, packet_id, version_id}` is a pure public module helper. Each value is UUID5(NAMESPACE_URL, `agentchattr:artifact-v1:<field>:<request_id>`). A retry with the SAME operator request id has the same objects. A new explicit retry/reassignment uses a NEW request id and therefore a new attempt/dispatch. For revisions, the audit's lineage_id references the existing lineage rather than the helper's new-lineage candidate.
- Author cap512*1024 UTF-8 bytes, nonempty/non-whitespace Markdown, refusing NUL and lone surrogates; validate emptiness without stripping stored text. Version objects are read/written in binary mode so CRLF survives Windows IO. Packet cap2*1024*1024 canonical UTF-8 JSON bytes and1000 messages. Instruction cap32*1024 UTF-8 bytes; format cap512 bytes. These index free-text fields preserve HT/LF/CR, reject other C0/DEL controls, retain existing strip()-based nonblank checks and allow the other Unicode edges specified in R1. These fail with no truncation.

## Exact source packet and scope

`put_packet(request_id, packet) -> scope` writes the immutable packet FIRST, before request reserve. An identical repeat is no-write and returns the same scope; changed bytes under that id conflict. Failure leaves any prior packet intact. CAS loss at reserve may leave this one orphan; report it, never auto-delete.

Packet keys:

```text
version: 1
channel: original valid channel
scope_kind: "run_accepted_messages" | "selected_channel_messages"
source_run: null | {session_id:positive int, run_id:32hex, input_revision:64hex, state_at_request:text}
input: null | {text:exact string, input_revision:SHA256(text UTF-8), source_document:null|JSON object}
messages: ordered array of {id:int>=0, uid:text, sender:text, type:text,
                           timestamp:positive finite number|null, text:exact string,
                           attachments:JSON array, provenance:JSON object}
```

Canonical JSON here means sealed_result_io.canonical_utf8: ensure_ascii=False, sort_keys=True, compact separators, allow_nan=False, encoded UTF-8. Never substitute review_brief._revision's ASCII-escaped form. Packet and message_ref hashes get independent non-ASCII/CRLF golden vectors.

JSON metadata is data only; recursively reject nonfinite numbers/unsupported types. The source service later constructs these allowlisted records from one locked snapshot and validates run membership/accepted projections; the store does not infer a source from chat. Preserve the submitted order; duplicate ids/UIDs refuse. Zero messages is allowed for an explicit instruction-only standalone request. When source_run exists, input/input_revision must agree; absent source run is explicitly null, not fabricated.

Returned scope keys:

```text
kind: packet.scope_kind
packet_id: request_ids(request_id).packet_id
sha256: SHA256(canonical_utf8(packet))
byte_length: len(canonical_utf8(packet))
message_refs: ordered [{id, uid, sha256:SHA256(canonical_utf8(message))}]
input_revision: packet.input.input_revision | null
```

The request stores that exact scope. `get_packet(packet_id)` returns the detached packet after exact hash/size validation against its referencing request when present; prepared-orphan inspection is internal/diagnostic only. Public access policy comes from ArtifactService, never arbitrary filesystem routes.

## Reserve request audit

`reserve_request(audit, request_id) -> request_row`. Audit keys are EXACT:

```text
version:1, purpose:"artifact-v1", request_id, lineage_id, attempt_id, dispatch_id, brief_id,
original_channel, requester:text,
producer:{name:text, identity_id:32hex, adapter:"cli"|"openai-compatible",
          launch_attempt:32hex|null, launch_nonce:32hex|null, fingerprint:64hex|null,
          requested_model:text|null, requested_model_reason:text|null,
          capabilities:["artifact-v1"]},
source_run: packet.source_run,
scope: exact returned scope,
instruction:exact text, format:exact text,
expected_parent:null|{version_id:32hex, sequence:positive int, sha256:64hex},
created_at:positive finite timestamp
```

All derived IDs except lineage match request_ids. Launch refs are all present together or all null; an API producer requires them. Requested model null has a nonempty reason; known requested model has reason null. Capability is an already verified binding declaration populated by the service, never an agent body. The store rejects a malformed producer but does not substitute for registration/capability or queue authority checks. Source_run/packet channel/scope must agree with the stored immutable packet. No secret, claim token or free-form filesystem path is accepted.

Audit never changes. A fresh reserve creates a prepared row and reserves the lineage's pending slot. New lineage expected_parent=null; an existing fulfilled lineage requires exact current version id/sequence/hash. An existing failed initial lineage with no head may be retried with parent=null. At most one live prepared/queued/active request per lineage; competing creation409/no index effect. Different lineages can reserve. The service first looks up get_request(request_id) and, after checking the same operator intent, returns the stored progressed row without re-resolving current launch refs or source. In reserve_request, compare audit identity fields excluding created_at only; changed launch refs/producer/instruction/scope/parent still conflict. Same request id with matching identity returns the CURRENT prepared/queued/active/fulfilled/terminal row without a write and never resets it. Preserve the original created_at. Read-only replay can return an existing row for an inactive channel; only new reserve requires active policy. Input shape/types remain validated before replay. Reserve does not create a private brief, dispatch, content version or callback.

Request row keys: `audit`, mutable `channel`, `state`, `reason` (null or safe code), `updated_at`, `version_id` (null until fulfilled), `quarantine_ids` (retained detailed diagnostic ids, at most8), and a detached computed `overflow_count` (per-dispatch summary counter, otherwise0). The global overflow counter is reported separately and never attributed to a particular request. Current channel starts from original_channel and later changes only through staged rename. The lineage metadata includes id/current channel/head version/pending request and version order; its exact on-disk layout is private, but it must validate cross-references before any write.

## Trusted state changes and version commit

`set_attempt_state(request_id, attempt_id, expected_state, change, *, now=None) -> request_row`.

- change accepts exactly `state` and `reason`, never audit/channel/producer/scope/version changes.
- prepared -> queued/active/failed/cancelled/quarantined; queued -> active/failed/cancelled/quarantined; active -> failed/cancelled/quarantined.
- fulfilled is produced only by commit_version; imported is reserved for the later atomic import phase. Terminal -> different state refuses. Same-state reason changes are allowed ONLY for prepared/queued/active, when attempt AND expected_state match, changing reason/updated_at only. A terminal fulfilled/failed/cancelled/quarantined/imported row refuses a different reason; an identical repeat is no-write. An identical desired state/attempt/reason repeat is no-write, including after progress; wrong attempt or an unmatched expected state for a real change conflicts before effects. Fresh reserve reason is null; startup repair explicitly sets resume_pending.
- Terminal failure/quarantine/cancel clears the lineage pending slot, keeps its prior head and audit. Healthy status persistence remains possible on an inactive channel; external calls must never reach this low-level phase directly.

`commit_version(request_id, attempt_id, dispatch_id, markdown, observation, *, now=None) -> version_metadata`.

observation keys exactly `confirmed_model` (text|null) and `confirmation_reason` (`api_response`|`provider_did_not_report_model`|`cli_model_unverified`). CLI requires null/cli_model_unverified. API null requires provider_did_not_report_model; nonnull requires api_response. This observation must come from the later trusted service/adapter, not the submit body. Producer, requested model, source_run/scope/input revision and request instruction come only from audit.

Commit requires matching current queued/active request+attempt+dispatch, lineage pending ownership and exact expected parent. It writes immutable object bytes first, then atomically appends metadata, advances head, clears pending and marks request fulfilled. Object/index fault never advances authoritative memory or head; any orphan is diagnostic only. Same fulfilled dispatch + identical Markdown returns the original metadata/no write, ignoring a later delivery timestamp; different Markdown or wrong attempt conflicts and never alters the admitted version. No implicit quarantine from a failed commit: the admission service records it explicitly, so a malicious wrong-seat attempt cannot terminate legitimate work.

Version metadata keys: `id`, `lineage_id`, `sequence`, mutable `channel`, `parent_version_id`, `request_id`, `attempt_id`, `dispatch_id`, `sha256`, `byte_length`, `created_at`, immutable `provenance`. Provenance copies requester, producer name/identity/adapter/requested model, result observation, source_run, scope and input revision from validated records. Old revisions remain untouched. get_version below includes exact Markdown only when specifically requested.

`quarantine_submission(request_id, attempt_id, dispatch_id, *, reason, content=None, actor_identity_id=None, now=None) -> diagnostic` is a trusted diagnostic append. request_id may be null or a valid but unknown id, so unmatched saved results can stand alone. attempt/dispatch and optional actor ids still validate. Reason is a safe enum, never exception text. Content is any string or null. Diagnostic hash/byte count uses UTF-8 with errors=surrogatepass, preserving valid UTF-8 bytes and encoding lone surrogates losslessly. NUL or invalid UTF-8 content is hash/count-only, never retained as a body. Record received time and retained/not-retained status. No truncation presented as full content. This method never changes request state, pending slot or admitted versions.

Detailed diagnostic id = UUID5(NAMESPACE_URL, canonical_utf8({request_id,attempt_id,dispatch_id,reason,sha256,byte_count,actor_identity_id}).decode('utf-8')). Time is not in the key; retain the first received_at and return identical retained keys without rewriting. Null content hashes empty bytes, with byte_count0 and body not-retained. A request_id is a claimed reference, not a required foreign key. Append a retained detailed id to request.quarantine_ids whenever request_id AND dispatch_id both match that stored request, REGARDLESS of the claimed attempt_id. A stale request's matching dispatch attaches to that stale row; a wrong-attempt claim using the matching request/dispatch appends an attached diagnostic with reason wrong_attempt and never changes state. Unknown/null request or mismatched dispatch attaches nowhere. No diagnostics can terminate a newer legitimate request.

Detailed return keys are id, kind=quarantine, request_id, attempt_id, dispatch_id, reason, sha256, byte_count, actor_identity_id, received_at, updated_at (same first timestamp), not_retained, and body_object_id (id or null). No body is returned by diagnostics(). Overflow return rows have id, kind=dispatch_overflow|store_overflow, fixed dispatch_id (null for store scope), counter, latest_diagnostic_id, latest_sha256, latest_byte_count, latest_reason and updated_at. The request row's overflow_count is computed from its dispatch summary, not persisted as attempt state.

### Diagnostic bounds, overflow and dedupe

Public constants: MAX_DIAGNOSTICS_PER_DISPATCH=8, MAX_DIAGNOSTIC_DISPATCH_GROUPS=256, MAX_DIAGNOSTIC_RECORDS=1024, MAX_QUARANTINE_BODY_BYTES=8*1024*1024, MAX_QUARANTINE_OBJECTS=1024, MAX_DIAGNOSTIC_COUNTER=2**31-1. Tests verify the actual default limits; no smaller patched cap is counted as proof of these numbers.

- At most8 detailed records per dispatch, at most256 distinct retained dispatch groups, at most1024 detailed records total. Hash-only records count toward these limits. No automatic deletion of detailed records or objects.
- After a group's8 detailed slots, further new keys use ONE fixed per-dispatch overflow summary, with no body and no new individual row. When a new group would exceed256, or a detailed record would exceed1024 globally, use ONE fixed store-level overflow summary instead, with no new group. IDs of summary records derive only from their fixed scope (dispatch or store), distinct from detailed diagnostic ids.
- Summary fields may update only counter, latest_diagnostic_id, latest_sha256, latest_byte_count, latest_reason, updated_at. Counter is a plain int saturated at2**31-1. It never changes request state, pending slot, quarantine_ids or a version. get_request's computed overflow_count reads its per-dispatch summary; global overflow remains an unattributed store diagnostic.
- A repeat of any retained detailed id is always no-write. A repeat of the latest overflow key is no-write; an older overflow key may increment again. **overflow dedupe is last-key only; counters are an upper bound on distinct submissions**.
- Retain a body only if <=512KiB and the total retained quarantine-body bytes remain <=8MiB. Otherwise store hash/count only with not_retained=true; the id does not change. Budget includes orphan quarantine-body objects left by failed metadata commits, so retries cannot bypass it. Before any body write, count existing quarantine body objects including orphans against an additional1024-object storage bound; beyond it retain hash/count only. Those orphans are reported, not deleted. Bodies use artifacts/quarantine/<diagnostic_id>.txt in binary mode.
- diagnostics() returns detailed records, group/total counts, body-byte total, per-dispatch/store summaries and truncated flag. Request quarantine_ids lists only retained detailed ids (max8); never append overflow keys. Admission explicitly changes CURRENT-owner attempt state when appropriate, separately from diagnostics.


Safe state reason codes are null or one of: resume_pending, queued, queued_behind_review, source_stopped, operator_cancelled, producer_unavailable, generation_failed, delivery_unconfirmed, invalid_response, quarantined, imported, source_packet_unavailable. Quarantine reason codes: wrong_identity, wrong_attempt, wrong_dispatch, wrong_brief, wrong_scope, wrong_parent, cancelled, superseded, conflicting_duplicate, invalid_content, invalid_response, unmatched_saved_result, source_packet_unavailable, response_too_large. The store never persists an arbitrary exception string as a reason. Newly reserved rows have reason null; startup repair sets resume_pending explicitly.

## Detached reads and lifecycle phases

- `get_request(request_id) -> request_row|None`.
- `get_request_by_dispatch(dispatch_id) -> request_row|None`, detached metadata/audit lookup for admission; dispatch ids uniquely identify requests. No packet/Markdown body is copied.
- `list_versions(lineage_id, *, limit=100, offset=0) -> {rows:[version_metadata],count,truncated}`, newest sequence first, metadata only. Healthy missing lineage gives an empty result; bad index still raises. This supports the reader and expected-parent inspection without reading bodies.
- `get_version(version_id) -> {metadata:version_metadata, markdown:exact string}|None`; validate exact bytes/hash and fail that object read on discovered corruption, without holding unrelated lineages or low-level settlement. Lists/metadata readers do not copy Markdown or packet bodies.
- `list_lineages(channel=None, *, limit=100, offset=0) -> {rows:[metadata], count:int, truncated:bool}`. Row contains id/channel/head metadata/version_count/pending request metadata, not bodies. Count includes a requested lineage with no completed version, visibly pending/failed. Ordering is updated_at descending, then lineage id ascending; apply limit/offset after sorting.
- `pending(channel) -> [{request_id,lineage_id,attempt_id,dispatch_id,state,reason,source_run_id}]` for prepared/queued/active rows only. Fresh prepared reason is null; resume_pending means startup has explicitly identified resume work. Store does no queue interpretation or recovery; later service applies K2 mapping.
- `channel_names() -> set[str]` from mutable lineage/request/version channels.
- `lifecycle_scope(channel) -> {lineages:[{id,updated_at}], pending:[same pending metadata], version_count:int}`, metadata only.
- `retained_metadata(channel, *, limit=100) -> {rows:[lineage metadata], count:int, truncated:bool}`, metadata only and read-only for inactive channels. Ordering is updated_at descending, then lineage id ascending.
- `diagnostics(*, limit=100) -> {rows,count,truncated,dispatch_group_count,detailed_count,retained_body_bytes}` includes quarantines, overflow summaries, object-corruption observations and orphan object/packet IDs with counts/truncation, no auto-deletion or dispatch. Order by updated_at descending, then id ascending; immutable detailed records use first received_at and file-only orphan observations use owned file mtime. Reading diagnostics does not persist a new report.
- `rename_channel(old,new)` is an unguarded low-level phase. Validate names and healthy storage, then stage changes ONLY to mutable lineage/request/version channel fields. Old absent => no-write retry; old+destination coexist => conflict before effects. Atomic commit before memory, no timestamps/provenance/audit/packet/body/private brief changes and no callbacks.

Missing IDs return None only for a healthy owner; held storage raises even on unknown-id reads. Malformed ID types are validation errors. No read normalizes or saves. Missing artifact index is the first-run upgrade, not corruption. Corrupt index.json holds ALL operations. Corrupt/missing version bodies or packets fail only that object read with a generic object-unavailable code and appear in diagnostics; they do not block state/quarantine/reserve for healthy unrelated requests. A pending request with an unreadable packet cannot be rebuilt or advanced to queued/active/fulfilled; it can only be settled terminal. Metadata-only readers do not scan/copy every body on every call. Later lifecycle integration must validate the relevant channel objects before destructive effects, with per-object errors rather than a whole-store hold.

Future HTTP mapping must catch ArtifactConflict/ChannelConflict BEFORE ValueError (409 versus400), and ArtifactUnavailable/ChannelUnavailable as503. Add a real route mapping regression in that package.

## Write seams and bounded helper tests

Store index uses module alias `artifact_store.atomic_json` (from api_seats); helper may inject an OSError there. Immutable byte objects use temp+fsync+replace with cleanup, preserving originals on failure; test through pathlib.Path.replace/real owned paths. No invented private helper anchors. Clock is explicit `now` or actual time; packet identity is request_ids, not a duplicated UUID implementation inside tests.

Helper owns ONLY NEW tests/test_artifact_store.py, <=12 named methods. Fixture uses real temporary stores/catalog and a real ChannelService boundary, no app.configure or workers/providers. Initial EXACT2 genuine RED before production: immutable reserve/CAS and atomic version commit failure. Then extend within12 while holding execution until production readiness. Use Barrier/Event for deterministic concurrency, never sleeps. Include a two-thread ordinary-write waiting on policy versus low-level cancellation test, proving no policy entry under the store lock. Cover exact Unicode/CRLF/raw .md bytes/caps/no normalization, packet/message golden hash vectors, deterministic packet replay/conflict, concurrent same-lineage CAS and peer lineages, all trusted state transitions/terminal no restart, identical/different version replay, unmatched/request-less quarantine, matching-only diagnostic attachment, all M2 cap/overflow/body-budget subtests in one method, same-state reason changes, progressed request replay with changed created_at, per-object corruption not holding unrelated work, quarantine not poisoning current work, strict/held/no-reset/read-detached behavior, active-channel ordinary writes versus low-level settlement, staged rename and metadata-only reads, object/index faults and orphan reporting/fresh reload. Root adds targeted cases beyond that cap only where genuinely needed. Preserve source and fixture failure attribution separately.

Implementation of brief seals, queue-state recovery, capability/claim checks, actual admission/quarantine decisions, backup import and UI is deferred to later reviewed packages. This store contract supplies no external authorization by itself.


Reviewer M1-M5 and S1-S6 amendments are folded in. M2 bounded overflow ruling:8/group,256groups,1024details,8MiBbody budget, saturating last-key-only overflow counters and explicit loss of all-history overflow dedupe. No helper briefing/tests or store code before changed-section recheck.


Final F1-F4: terminal reason changes conflict; metadata-only list_versions/get_request_by_dispatch added; matching request+dispatch attaches a detailed diagnostic regardless of claimed attempt without state effects; source_packet_unavailable is a quarantine reason. Reviewer explicitly cleared the <=12 helper after this tiny docs-only commit, no additional re-review needed for these same semantics. Initial exact2 observed RED first, no production source before evidence.


Integrity clarification: known enum values forbidden by the operation or current state raise ArtifactConflict; malformed values, unknown enums and extra fields raise ArtifactValidationError. Audit immutability protects against API mutation, not hand edits of index.json. Disk tampering is outside this contract; metadata cross-reference validation and the later sealed brief provide the stated checks. Index load validates expected-parent id, sequence and hash against the ordered version chain and live pending head without reading object bodies. Packet access and queued/active advancement verify channel, source_run, input revision and ordered message references against the frozen audit; a mismatch affects only that packet and leaves terminal settlement available.


Store review clarifications: every fulfilled/imported request must name its own existing version, and version metadata must point back to that request. Pagination truncated means offset plus returned length is less than total count. A full dispatch group always updates its own overflow summary, even at the global detailed-record cap; the store-level summary handles other groups/records. Object-error observations are in-memory, referenced-only and bounded to the256 most recently observed objects; unknown/unreserved packet ids produce no corruption report, and evicted observations can be rediscovered by reading their object. This cache never deletes stored objects. Persistent startup-lock files are not artifact bodies, are outside body quotas and orphan reports, and remain on disk to preserve lock identity. Queued/active reason-only changes still verify the source packet, so corruption blocks those updates while terminal cancellation/failure remains available.


Authority C1 enum amendment: response_too_large separates an omitted oversize body from an earlier retained empty-string diagnostic through the existing reason key. Only this fixed quarantine enum member is added; request state reasons, diagnostic UUID key, schemas, caps and row shapes stay unchanged. Nothing shipped, so no migration or rekeying is needed. Root regression observed the missing-enum refusal before the change, then distinct ids/no-body and unchanged real-limit overflow validation passed.


## Proposed R2 document amendment, not implemented

R2 replaces the request-row/debug and diagnostic paragraphs (82/103/105/113/116): authoring-v2 rows have audit/channel/state/reason/updated_at/version_id (+import_source only for imported); no stored quarantine_ids or computed overflow_count. Independent diagnostics.json owns attachments/summaries, separate request_diagnostics supplies debug reads. All8/256/1024 and body budgets remain. See [R2 diagnostic ownership](TICKET-20-DIAGNOSTICS.md) for the governing proposed delta; existing descriptions above remain the R1 implementation until its reviewed production pin.
