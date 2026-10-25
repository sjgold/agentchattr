# Ticket 20 artifact-store payload freeze candidate

Status: review draft, not permission for helper tests or store implementation. Task0 at65bcb56 independently PASS (reviewer82/9.855s,3000 seeded MAC comparisons/no mismatch, read/error parity5 cases, private imports intact; full1374/four skips108.397s builder-only). This document covers the STORE only. No queue, adapter, public route, renderer or admission authority is implemented by this package.

## Paths and policy boundary

NEW `artifact_store.py`, `ArtifactStore(data_dir, *, hold_unreadable=False)`. Public `.path` is `data_dir/artifacts/index.json`. Immutable version bytes use `artifacts/objects/<version_id>.md`; exact source packets use `artifact_briefs/packets/<packet_id>.json`. Paths derive only from validated IDs, reject redirected paths and never use a title/path supplied by a producer. Constructor on absent data returns empty in memory without writing files. Default unreadable/malformed storage raises `ArtifactUnavailable`; `hold_unreadable=True` returns a held owner with generic errors and unchanged files.

Error classes: `ArtifactValidationError(ValueError)`, `ArtifactConflict(ChannelConflict)`, `ArtifactUnavailable(ChannelUnavailable)` (the latter two preserve existing409/503 family mappings). Existing ChannelInactive/ChannelUnavailable policy refusals propagate. The initially closed getter raises ArtifactUnavailable before ordinary writes. I/O failures map to unavailable without content/path echo. JSON load rejects duplicates, nonfinite/nonnumeric timestamp/schema/type errors and invalid UTF-8. Formatting-only external edits may revalidate; changed authoritative content holds for repair, never silently replaces memory or overwrites it. Use fingerprint-cached validation as in configured jobs/summaries.

`bind_channel_policy(getter)` stores a callable without entering policy under the store lock. Ordinary writes start closed until bound, then enter the existing engine/catalog boundary before taking the store lock. `put_packet`, `reserve_request`, `commit_version` require the ACTUAL target channel active. Trusted status/quarantine/rename phases below are low-level and bypass the active check so Stop/cancellation/diagnostics remain possible while the catalog is held. They still require healthy artifact storage and their own lock; ArtifactService later owns external authorization and engine serialization. No store method dispatches or calls a provider. Reads stay available for inactive channels.

All returned objects are detached. No method exposes seal material; it is absent from these schemas. Callbacks are out of scope for this store slice; later service events happen after durable commit.

## Primitive types and deterministic IDs

- IDs are exact lowercase32-hex UUIDs; hashes exact64-hex SHA-256. Message ids are int>=0 (bool refused). Legacy message UIDs use explicit `legacy:<id>` when an original UID is absent; otherwise preserve the actual nonempty string UID.
- Channel names use the existing lifecycle grammar. Timestamps are finite positive numbers (bool refused); producer/source strings must be UTF-8-encodable without NUL. No text is trimmed or normalized on persistence.
- `request_ids(request_id) -> {lineage_id, attempt_id, dispatch_id, brief_id, packet_id, version_id}` is a pure public module helper. Each value is UUID5(NAMESPACE_URL, `agentchattr:artifact-v1:<field>:<request_id>`). A retry with the SAME operator request id has the same objects. A new explicit retry/reassignment uses a NEW request id and therefore a new attempt/dispatch. For revisions, the audit's lineage_id references the existing lineage rather than the helper's new-lineage candidate.
- Author cap512*1024 UTF-8 bytes, nonempty/non-whitespace Markdown; validate emptiness without stripping stored text. Packet cap2*1024*1024 canonical UTF-8 JSON bytes and1000 messages. Instruction cap32*1024 UTF-8 bytes; format label cap512 bytes. These fail with no truncation.

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

Audit never changes. A fresh reserve creates a prepared row and reserves the lineage's pending slot. New lineage expected_parent=null; an existing fulfilled lineage requires exact current version id/sequence/hash. An existing failed initial lineage with no head may be retried with parent=null. At most one live prepared/queued/active request per lineage; competing creation409/no index effect. Different lineages can reserve. Same request id + identical audit returns the original row without a write; any changed audit conflicts. Reserve does not create a private brief, dispatch, content version or callback.

Request row keys: `audit`, mutable `channel`, `state`, `reason` (null or safe code), `updated_at`, `version_id` (null until fulfilled), `quarantine_ids` (array). Current channel starts from original_channel and later changes only through staged rename. The lineage metadata includes id/current channel/head version/pending request and version order; its exact on-disk layout is private, but it must validate cross-references before any write.

## Trusted state changes and version commit

`set_attempt_state(request_id, attempt_id, expected_state, change, *, now=None) -> request_row`.

- change accepts exactly `state` and `reason`, never audit/channel/producer/scope/version changes.
- prepared -> queued/active/failed/cancelled/quarantined; queued -> active/failed/cancelled/quarantined; active -> failed/cancelled/quarantined.
- fulfilled is produced only by commit_version; imported is reserved for the later atomic import phase. Terminal -> different state refuses. Same desired state/attempt/reason repeat is no-write. Wrong attempt/current expected state conflicts before effects.
- Terminal failure/quarantine/cancel clears the lineage pending slot, keeps its prior head and audit. Healthy status persistence remains possible on an inactive channel; external calls must never reach this low-level phase directly.

`commit_version(request_id, attempt_id, dispatch_id, markdown, observation, *, now=None) -> version_metadata`.

observation keys exactly `confirmed_model` (text|null) and `confirmation_reason` (`api_response`|`provider_did_not_report_model`|`cli_model_unverified`). CLI requires null/cli_model_unverified. API null requires provider_did_not_report_model; nonnull requires api_response. This observation must come from the later trusted service/adapter, not the submit body. Producer, requested model, source_run/scope/input revision and request instruction come only from audit.

Commit requires matching current queued/active request+attempt+dispatch, lineage pending ownership and exact expected parent. It writes immutable object bytes first, then atomically appends metadata, advances head, clears pending and marks request fulfilled. Object/index fault never advances authoritative memory or head; any orphan is diagnostic only. Same fulfilled dispatch + identical Markdown returns the original metadata/no write, ignoring a later delivery timestamp; different Markdown or wrong attempt conflicts and never alters the admitted version. No implicit quarantine from a failed commit: the admission service records it explicitly, so a malicious wrong-seat attempt cannot terminate legitimate work.

Version metadata keys: `id`, `lineage_id`, `sequence`, mutable `channel`, `parent_version_id`, `request_id`, `attempt_id`, `dispatch_id`, `sha256`, `byte_length`, `created_at`, immutable `provenance`. Provenance copies requester, producer name/identity/adapter/requested model, result observation, source_run, scope and input revision from validated records. Old revisions remain untouched. get_version below includes exact Markdown only when specifically requested.

`quarantine_submission(request_id, attempt_id, dispatch_id, *, reason, content=None, actor_identity_id=None, now=None) -> diagnostic` is a trusted, bounded diagnostic append. Reason is a safe enumerated code supplied by admission, not exception text. Store hash/UTF-8 byte count, supplied actor/attempt/dispatch and received time; body at or below512KiB may be an immutable inert diagnostic object at artifacts/quarantine/<diagnostic_id>.txt, larger body is hash/count only with an explicit not-retained flag. No truncation presented as full content. Identical diagnostic input is idempotent; it does not change request state, pending slot or admitted versions. Invalid programmer inputs/unknown request refuse. Admission explicitly marks the CURRENT owner attempt terminal only when appropriate; a wrong/stale attempt must not poison a newer request.

Safe state reason codes are null or one of: resume_pending, queued, queued_behind_review, source_stopped, operator_cancelled, producer_unavailable, generation_failed, delivery_unconfirmed, invalid_response, quarantined, imported. Quarantine reason codes: wrong_identity, wrong_attempt, wrong_dispatch, wrong_brief, wrong_scope, wrong_parent, cancelled, superseded, conflicting_duplicate, invalid_content, invalid_response, unmatched_saved_result. The store never persists an arbitrary exception string as a reason. Newly reserved rows have reason resume_pending.

## Detached reads and lifecycle phases

- `get_request(request_id) -> request_row|None`.
- `get_version(version_id) -> {metadata:version_metadata, markdown:exact string}|None`; validate exact bytes/hash and hold on discovered corruption. Lists/metadata readers do not copy Markdown or packet bodies.
- `list_lineages(channel=None, *, limit=100, offset=0) -> {rows:[metadata], count:int, truncated:bool}`. Row contains id/channel/head metadata/version_count/pending request metadata, not bodies. Count includes a requested lineage with no completed version, visibly pending/failed.
- `pending(channel) -> [{request_id,lineage_id,attempt_id,dispatch_id,state,reason,source_run_id}]` for prepared/queued/active rows only. Prepared reason is resume_pending. Store does no queue interpretation or recovery; later service applies K2 mapping.
- `channel_names() -> set[str]` from mutable lineage/request/version channels.
- `lifecycle_scope(channel) -> {lineages:[{id,updated_at}], pending:[same pending metadata], version_count:int}`, metadata only.
- `retained_metadata(channel, *, limit=100) -> {rows:[lineage metadata], count:int, truncated:bool}`, metadata only and read-only for inactive channels.
- `diagnostics(*, limit=100) -> bounded metadata report` includes quarantines and orphan object/packet IDs with count/truncation, no auto-deletion or dispatch.
- `rename_channel(old,new)` is an unguarded low-level phase. Validate names and healthy storage, then stage changes ONLY to mutable lineage/request/version channel fields. Old absent => no-write retry; old+destination coexist => conflict before effects. Atomic commit before memory, no timestamps/provenance/audit/packet/body/private brief changes and no callbacks.

Missing IDs return None only for a healthy owner; held storage raises even on unknown-id reads. Malformed ID types are validation errors. No read normalizes or saves. Missing artifact index is the first-run upgrade, not corruption. Referenced body/packet corruption is reported/held when inspected; catalog metadata reads do not scan/copy every body on every call.

## Write seams and bounded helper tests

Store index uses module alias `artifact_store.atomic_json` (from api_seats); helper may inject an OSError there. Immutable byte objects use temp+fsync+replace with cleanup, preserving originals on failure; test through pathlib.Path.replace/real owned paths. No invented private helper anchors. Clock is explicit `now` or actual time; packet identity is request_ids, not a duplicated UUID implementation inside tests.

Helper owns ONLY NEW tests/test_artifact_store.py, <=12 named methods. Fixture uses real temporary stores/catalog and a real ChannelService boundary, no app.configure or workers/providers. Initial EXACT2 genuine RED before production: immutable reserve/CAS and atomic version commit failure. Then extend within12 while holding execution until production readiness. Cover exact Unicode/CRLF/caps/no normalization, deterministic packet replay/conflict, concurrent same-lineage CAS and peer lineages, all trusted state transitions/terminal no restart, identical/different version replay, quarantine not poisoning current work, strict/held/no-reset/read-detached behavior, active-channel ordinary writes versus low-level settlement, staged rename and metadata-only reads, object/index faults and orphan reporting/fresh reload. Root adds targeted cases beyond that cap only where genuinely needed. Preserve source and fixture failure attribution separately.

Implementation of brief seals, queue-state recovery, capability/claim checks, actual admission/quarantine decisions, backup import and UI is deferred to later reviewed packages. This store contract supplies no external authorization by itself.
