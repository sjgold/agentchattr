# Ticket 20 operator routes and consistent source snapshots

Status: PROPOSED contract for independent review. Lifecycle slice4 is independently CLEARED ata38c17b (reviewer632 Python tests171.071s and25 actual-source VM cases). Product9b068af full1659/four skips320.363s is implementation-owner evidence; the later assertions changed tests/docs only. Storage, capability, authority, wrappers and lifecycle/backup contracts remain authoritative. This document authorizes no tests, helper briefing, code or activation until reviewed and the exact helper payload/signature freeze is cleared. Production SUPPORTED_CAPABILITIES stays ().

## Scope and current source facts

Expose explicit operator preview/create/revise/cancel/resume and read-only library/version/source/download APIs. Freeze a server-built source packet from ONE consistent message snapshot. Preserve exact Unicode/BOM/CRLF, immutable versions, one-live-request CAS, managed producer gates, queue ownership, source Stop fencing and all accepted recovery rules. No synthesis template, transcript assembly (Ticket21), arbitrary agent file writes, model/provider invocation from a route, or renderer in this package.

Verified by source read: ArtifactService.prepare_request already performs packet -> reserve -> private brief -> enqueue -> mark queued under the channel boundary. RequestProjection removes launch_nonce; private seals are not stored in request rows. MessageStore.get_recent/get_since return lists sharing stored row objects; they are NOT a safe source snapshot. get_snapshot copies one row but repeated calls do not provide a batch read. SessionStore freezes input_snapshot.text/revision/document, source run identity and admitted-event/continuation projection links. SessionEngine._project_session_active writes session-event:<event_id> and session-input:<question_event_id> UIDs. Existing projection text may include its missing-contributions footer. ArtifactStore._packet_scope already defines exact message fields, canonical hashes,2MiB/1000 limits and legacy UID collision refusal. No new store schema is proposed.

Use NEW artifact_sources.py for pure source projection/token construction, NEW artifact_routes.py for strict HTTP binding/projections, and a focused operator-service boundary around the existing ArtifactService (proposed NEW artifact_operator.py). Add a narrow generic MessageStore.snapshot_selected(channel,message_ids) batch-copy API; no artifact imports, callbacks or authority decisions inside MessageStore. Existing owners remain shared from app.configure; no second store, queue, catalog or manager.

## Proposed decisions and alternatives

| Decision | Recommendation | Alternatives and reason |
| --- | --- | --- |
| Freshness token | Stateless SHA256 over the complete server-computed immutable audit basis, excluding created_at. It is an opaque freshness/CAS token, never authorization. | A persisted preview adds a new state/crash/retention owner. A boot-key HMAC makes recovery/replay depend on another secret. Both are unnecessary because operator auth and fresh server validation grant authority. |
| Source capture | One detached batch snapshot while engine/catalog boundary is held; derive packet/refs/hashes from those exact copied rows before releasing that boundary. | Independent get_snapshot calls can mix row revisions; shallow get_recent aliases cannot freeze source. An optimistic retry across unrelated store revisions is more complex than the existing outer boundary. |
| Accepted-run preset | Only linked, present, matching admitted-event/operator-continuation projections from the selected run. Refuse edited/mismatched projections; explicit channel selection remains available. | Reconstructing missing rows from journal text would invent chat/projection history. Treating edited projection words as unchanged accepted output would blur provenance. No builder silently repairs either. |
| Imported revisions | An explicit NEW local request may append to an imported lineage's exact current head, in an active channel. Imported request/version rows retain their first origin and remain read-only. | Forbidding every local revision of imported content prevents the normal revision workflow. A fork would need new cross-lineage parent semantics, which the accepted store does not have. This proposal grants no authority to imported producers. |
| Lock budget | K6 maximum0.300s for each measured outer-boundary hold on the stated capped shapes, using real default persistence and a concurrent require_active peer. | Averages conceal long stalls. Raising the cap or excluding encoding/fsync would weaken the already-approved boundary promise. If measurements fail, return for mechanism review before implementation expansion. |

These are proposals for this review, not claims that the routes or benchmark exist. Existing standalone component compatibility stays unchanged.

## HTTP surface and authentication

All paths below are operator-only. New namespace is /api/artifacts, distinct from existing agent-only /api/artifact-briefs/... and /api/artifact-results. No path under the operator namespace is added to a bearer allowlist.

Require exactly ONE X-Session-Token header authenticated by existing middleware AND request.state.auth_origin==operator. Query-token-only, cookie-only and seat-bearer requests do not authenticate these routes. Reject an Authorization header even alongside a valid operator header, and duplicate operator headers. No model/agent body field can set the principal. Same-origin/DNS-rebinding checks remain. Middleware errors for this namespace use the fixed access-denied/no-store wire; existing other namespaces retain their behavior. Agent transport routes continue rejecting operator credentials.

Every response, including middleware/validation/404 errors and downloads, has Cache-Control:no-store and X-Content-Type-Options:nosniff. Never put credentials in URLs, logs, packet fields or response bodies. Read-only operations do not claim/adopt/start a seat, repair storage, admit results or mutate business records; existing owner lock-file behavior is unchanged. Async handlers offload synchronous owner/JSON/body work with asyncio.to_thread; no await under engine/catalog/store locks.

| Method/path | Purpose and result |
| --- | --- |
| GET /api/artifacts/producers | Page of detached registered-instance choices, name then identity order. Only identity/name/adapter/requested-model labels plus available/reason. Registry tokens and launch refs are excluded. |
| GET /api/artifacts/sources | Paginated channel source picker: id/uid/sender/type/timestamp and a snippet of at most256 UTF8 bytes, text_byte_length/text_truncated. Advisory, not a packet or freshness grant. |
| POST /api/artifacts/preview | Validate Intent, capture source, producer and parent. Return measured source/count/hash/refs, notices and opaque preview token only when authoring is available. No durable writes. |
| POST /api/artifacts/requests | New lineage, Intent.lineage_id and expected_parent must be null. Add preview_token.202 on a new durable request;200 on an identical replay returning current state. |
| POST /api/artifacts/{lineage_id}/revisions | Same create body, with lineage_id equal to the path and exact expected_parent. Fresh request/attempt/dispatch; never edit a prior version. |
| GET /api/artifacts | Page<LineageRow>, optional channel. Metadata only, including archived/deleted/imported lineages. |
| GET /api/artifacts/{lineage_id} | LineageRow plus independent bounded version/request metadata pages. No Markdown/packet body in a list. |
| GET /api/artifacts/requests/{request_id} | Nonce-free current RequestProjection plus the existing QueueProjection/warning when inspected by the service. No private brief. |
| POST /api/artifacts/requests/{request_id}/cancel | Body exactly {}. Existing cancel_request semantics and MutationResult. Durable cancellation is distinct from worker/transport settlement. |
| POST /api/artifacts/requests/{request_id}/resume | Body exactly {recover_saved:bool}; explicit operator recovery only, no regeneration. False repairs enqueue/state; True applies R1/lost-ACK rules exactly. |
| GET /api/artifacts/requests/{request_id}/source | Verified frozen source packet for operator audit, including retained/imported source. JSON only; no execution or attachment fetching. |
| GET /api/artifacts/{lineage_id}/versions/{version_id} | VersionDetail and exact Markdown string; validate membership, body hash/length. |
| GET /api/artifacts/{lineage_id}/versions/{version_id}/download | Exact stored UTF8 bytes with fixed ASCII filename and SHA256 header. No rendering. |

Register ordinary app routes from the binder, as in the accepted artifact transport fix, preserving app.routes entries with .path and both existing enumeration tests. Order static producers/sources/requests before dynamic lineage paths. Actual factory passes shared authorities explicitly; None/held owners refuse, never create an empty substitute. No public fixture switch enables artifact capability.

GET query fields are allowlisted and unique. Single page defaults limit=20,offset=0; limit1..100, offset0..2**53-1, ASCII decimal with no signs/leading zeros. Producers: limit?,offset?. Library: channel?,limit?,offset?. Sources: channel,limit?,offset? and optional session_id. Lineage detail: version_limit/version_offset/request_limit/request_offset (same bounds). Unknown/duplicate fields, query credentials or nonempty GET bodies refuse. Cap raw query bytes8192. IDs are lowercase Hex32, hashes Hex64; message ids are ints0..2**53-1 and session ids positive safe ints, never bool/float. Syntactically invalid ids400; valid unknown resource404.

POST JSON cap256KiB, read at most cap+1 before parsing, empty queries, strict UTF8/duplicate-key/nonfinite/depth/type/extra-field refusal. Exact object key sets; bool is never an int. Instruction1..32768 UTF8 bytes and format1..512, nonblank, no NUL/lone surrogates; preserve bytes rather than trim. Body schemas do not accept client audit/packet/provenance/model observations/launch refs/capabilities/dispatch/attempt/brief ids. Missing/oversize/malformed bodies have no durable effects.

## Intent and source selection

Intent EXACT keys:

```text
{version:1, request_id:Hex32, channel:ChannelName, producer_identity_id:Hex32,
 lineage_id:Hex32|null, expected_parent:null|{version_id:Hex32,sequence:positive_int,sha256:Hex64},
 source:{kind:"run_accepted_messages"|"selected_channel_messages",
         session_id:positive_int|null, message_ids:MessageId[]},
 instruction:exact_string, format:exact_string}
```

Preview and create share Intent; create adds preview_token:Hex64. request_id is generated once by the operator client and binds deterministic packet/brief/attempt/dispatch ids. Changed submitted intent for a recorded id is409; no implicit new attempt. A new preview may reuse an unrecorded request id; once recorded, edits/reassignment use a NEW request id.

selected_channel_messages: ids are unique, at most1000, resolve only in the actual requested channel, and normalize to ascending stored id order. No recent-N implicit scope. Picker text_byte_length measures raw UTF8 text only; the successful preview measures the whole canonical packet, including metadata/envelope overhead. Snippets end on a valid UTF8 boundary and declare truncation. session_id may be null; then source_run/input/input_revision are explicitly absent. A nonnull session id includes that same-channel run's exact frozen input and document metadata as context. Empty ids with no run are an explicit instruction-only scope, disclosed as source_absent; never an inferred fallback after a failed lookup.

run_accepted_messages: session_id required and message_ids must be []. Server derives ids from that run's admitted_events and recorded operator continuation projections, excluding quarantined/unadmitted results, skipped-work notices and unrelated chat. Ordinary human discussion outside those continuations is included only by explicitly checked channel selection (the picker may preselect the run rows; no hidden time-window inference). Input is always that run's input_snapshot.text with its actual revision/document. Stopped/replaced run source is allowed when explicitly selected and labeled by current state/replacement notice; it grants no run/producer authority.

Every linked projection must exist in the channel and match its recorded event/continuation id, stable projection UID and attribution. Validate current projection text against the trusted projector's expected exact text, including its actual missing-contributions footer rule. A missing/edited/mismatched projection refuses the preset; offer explicit channel selection or existing history repair, never construct missing chat from journal content. If an expected-text helper is extracted, preserve existing projection bytes and run unchanged review/event/projection suites. This selection rule and imported-local-revision proposal are explicit review points.

## Packet snapshot and structural authority allowlist

Add one MessageStore batch-copy read, selecting only requested ids/channel under its lock, with no policy/owner callbacks and no repeated per-id scans. It returns detached rows from one acquisition. Caller already holds engine -> catalog; a detached SessionStore run snapshot is read first and its lock released before MessageStore is locked. Producer manager reads and artifact reads release their locks before touching any other owner. Fixed order stays engine > catalog > manager > store > ledger, never manager+store or two store locks together.

artifact_sources builds the accepted packet EXACTLY:

```text
{version:1, channel:ChannelName, scope_kind:ScopeKind,
 source_run:null|{session_id,run_id,input_revision,state_at_request},
 input:null|{text,input_revision,source_document:null|DocumentDescriptor},
 messages:[{id,uid,sender,type,timestamp,text,attachments,provenance},...]}
```

Text is the exact captured Unicode string; no newline, BOM, whitespace, bidi or control normalization. A missing legacy uid uses legacy:<id>; an actual equal uid collision is refused, never renamed. Existing required types/UTF8/NUL rules remain. Messages sort ascending id. timestamp is stored value or null, never current time. Missing attachments/provenance become []/{}; no whole-store object is serialized.

BUILT message provenance allowlist: session_id,run_id,event_id,question_event_id,kind,provenance,submitted_by,seat_identity_id,input_revision,session_output, when present and valid. These are source attribution, never a new dispatch binding. Explicitly omit review brief/attempt/dispatch/launch refs, config/provider/settings objects, auth tokens, fingerprint, private seal/owner fields and server paths. Unknown metadata fields are omitted by this fixed projection, not forwarded or promoted to instructions.

BUILT attachment descriptors allow only name,url,type,content_type,mime_type,size,byte_length,sha256,content_sha256,encoding when present with their corresponding bounded JSON primitive types. Do not include path/local_path, tokens, private provider/config fields or nested arbitrary metadata. URLs and names remain untrusted data and are not fetched by the builder or model wrapper. DocumentDescriptor reuses document_inputs' validated metadata without text: version,kind,source_id,name,encoding,byte_length,content_sha256. Verify it against input text using the existing validator; no new path locator or guessed revision.

The allowlist is about structure generated by OUR code. Literal user text/names may contain words such as token/path/fingerprint and are preserved; no keyword filter. Previously retained/imported packet bytes remain immutable user data and are not rewritten by this builder. The source-copy sensitivity disclosure continues.

Use sealed_result_io.canonical_utf8 (ensure_ascii=False) and existing _packet_scope for final packet/ref hashes; preserve the separate brief-revision ensure_ascii=True form. Per-message sha256 covers the full allowlisted packet message, not a truncated snippet. Successful preview returns exact canonical packet byte_length, sha256, ordered id/uid/hash refs and input revision from this ONE detached capture, all while the SAME outer boundary remains held. Recheck the supplied preview token against this complete current capture before any create effects. Never compare a token from one read with bytes from a later independent read.

Capture/materialization is cap-aware:2MiB canonical packet and1000 messages, reject before persistence, never truncate a packet or substitute a partial hash. Avoid an unbounded full-history/body serialization to discover an overage. A rejection whose full size was not measured reports packet_bytes:null,measurement_complete:false and a truthful lower bound above the cap; exact accepted sizes are always complete. The source picker snippet is explicitly labeled text_truncated and is never used as packet content. Exact bounded-copy/encoding helper signatures need the later freeze; no alternative canonical form is authorized.

REQUIRED NAMED gate: test_locked_packet_snapshot_allowlist_does_not_copy_app_authority. Plant distinct server-owned nonce/seal/token/fingerprint/config/path sentinels in non-allowlisted message/attachment/document metadata, capture through the real builder under the boundary, and assert absent by structural path and sentinel value. Keep literal user text mentioning those field names intact. Verify canonical golden non-ASCII/CRLF bytes and message hashes independently. This gate cannot be deferred past operator-routes/K6 or activation.

## Preview token, replay and durable creation

Token basis is the full server-built immutable audit except created_at: deterministic ids, actual channel/requester, exact managed producer refs and requested-model labels, source_run, complete scope/ref hashes, instruction/format and expected parent. SHA256(canonical_utf8(basis)). Public preview never returns launch_nonce/private seal; the token is opaque. No new preview index, expiry timer, boot secret or schema. Requiring a currently active channel and exact current producer is independent of token equality. An archive/reopen with identical source may retain a usable token after the channel is active again; this token binds content/authority, not a catalog revision counter.

NEW request flow under ONE outer boundary: healthy configured owners -> actual active channel/no catalog repair -> selected producer's exact verified current binding/model -> lineage pending/head CAS and verified parent bytes if revision -> one source snapshot/packet -> compare token -> trusted audit -> existing prepare_request. The accepted packet/reserve/brief/enqueue/mark ordering and cancellation/Stop serialization do not change. Parent <=512KiB, exact id/sequence/hash/length; corrupt parent refuses before dispatch. Source Stop after this boundary fences the request; Stop before it changes the run-state/token or makes this an explicitly new request after Stop. No run_id is installed on the artifact dispatch envelope.

EXISTING local id flow comes FIRST after syntax/operator auth (an imported request id is read-only409, never a local-create replay): get_request(request_id), reconstruct the stored token from its immutable audit and compare the normalized Intent/selector with that stored intent. Same token/body returns current row/dispatch view without reading current chat, checking a later producer launch, enqueueing or regenerating. Changed token/intent409. Creation time/current mutable request state are not replay identity. Store one-live/head CAS remains final authority. Normal create replay never invokes R1; explicit resume is separate.

If a write/queue fault occurs after partial durable effects, use a guarded lookup only to report what is known. Error adds request_id, durability:"recorded"|"not_recorded"|"unknown", request:RequestProjection|null; unknown never means empty or rolled back. Prepared recorded requests remain recoverable from frozen data via existing startup/explicit resume. Packet-only orphans remain diagnostics/retained, never deleted. Final error codes and exact helper result shape are review/freeze items before tests; do not invent a second operation journal.

Capability remains empty during this package. Producer choices show the fixed eligibility reason and no automatic restart; preview can return measured source with available=false/token=null. Create always refuses unavailable/legacy/forged-capability producers before new durable effects. Fixture-controlled supported managed bindings exercise the enabled paths; they are labeled component controls, not native/provider acceptance.

## Read projections, cancellation and download

Page<T> = {rows:T[],count:nonnegative_int,truncated:bool}; list order updated_at desc/id asc, versions newest sequence first. No bodies in pages. LineageRow reuses existing _lineage_row; RequestSummary contains request/lineage/dispatch ids, state/reason/times/version/expected_parent, compact source counts and public producer/model labels. VersionSummary contains id,lineage_id,channel,sequence,parent_version_id,request_id,sha256,byte_length,created_at, compact source_run/input/scope counts, producer labels/observation and derived import_source. VersionDetail adds requester/instruction/format/full ordered message refs. Exact projection key sets will be frozen before helper briefing, never deep-copy then delete secrets.

Producer labels are historical name,identity_id,adapter,requested_model/requested_model_reason plus the version's trusted observation. CLI confirmation remains null/cli_model_unverified; API confirmation comes from that result, not a shared receipt. RequestProjection/MutationResult retain the accepted authority contract (launch_nonce omitted; no seals); compact library rows omit all launch refs. Version import_source is derived from its request at read time, never added to stored version provenance. Imported labels/text are hostile and must be escaped later; imported ownership is not live/verified.

Reads work for archived/deleted/imported history and dead/replaced producers without a live gate. Unknown membership404; corrupt body/packet503 per-object, metadata peers stay readable; corrupt index503/no reseed. No reader auto-repair or quarantine. Imported request cancel/resume is409/read-only; an explicit local revision is a NEW request, never a state change to an imported row.

Cancel returns the existing MutationResult after request-first cancellation. transport_settled=false/warning is visible, not an exit or remote-cancel claim; no chained archive/delete. Resume uses existing exact semantics, recover_saved=true only from this authenticated operator action. Failed transport with saved content is never startup-auto-admitted; lost-ACK repair remains bookkeeping only. No client-supplied consumer/owner/exit evidence.

Download verifies membership and stored SHA/length, returns exact UTF8 bytes in binary mode, Content-Type:text/markdown; charset=utf-8, X-Content-SHA256:<lowerhex>, Content-Disposition:attachment; filename="artifact-<lineage_id>-r<sequence>.md", Content-Length and nosniff/no-store. No title/path/header reflection, newline conversion, HTML serving or model call. JSON detail round-trips the same string bytes; source-only rendering/sanitization lives in the reader package.

## Fixed error wire proposal

Flat {code,error}; only the explicit typed count/durability/reason fields below may be added. No exception strings/paths/headers/payload logging; unexpected failures log TYPE only and fixed503. Map ChannelConflict/ArtifactConflict before ValueError, and per-object unavailable before generic validation. No FastAPI422 detail containing submitted values.

| HTTP | code | fixed error |
| --- | --- | --- |
|400|artifact_invalid_request|Invalid artifact request.|
|403|artifact_operator_required|Operator session required.|
|404|artifact_not_found|Saved artifact resource was not found.|
|409|artifact_preview_changed|Artifact source or request context changed. Refresh the preview.|
|409|artifact_request_conflict|That request identifier already records different artifact work.|
|409|artifact_parent_changed|The artifact head changed. Refresh the revision preview.|
|409|artifact_request_pending|This artifact already has pending work. Cancel or settle it before requesting another version.|
|409|artifact_producer_unavailable|The selected author is unavailable for artifact requests.|
|409|artifact_channel_unavailable|Choose an active channel without pending channel repair.|
|409|artifact_source_unavailable|The selected source is unavailable or its projection changed. Select messages explicitly or repair the source.|
|409|artifact_request_read_only|This saved request is terminal or imported and cannot perform that action.|
|413|artifact_source_too_large|The selected source exceeds the artifact packet limit. Choose a smaller scope; nothing was truncated.|
|503|artifact_storage_unavailable|Saved artifact storage is unavailable. Repair storage and reload.|
|503|artifact_object_unavailable|This saved artifact object is unavailable. Its metadata is retained.|
|503|artifact_operator_unavailable|Artifact management is unavailable. Reload after startup.|

Producer-unavailable may add only reason from the accepted capability enum (artifact_capability_missing/runtime_unverified/producer_unavailable/unmanaged_producer/capability_binding_changed). Source-limit rejection adds limits{packet_bytes:2097152,messages:1000}, measured{message_count,packet_bytes:int|null},measurement_complete:bool and optional lower_bound_bytes; no prefix hash or incomplete data labeled complete. Mid-write failure adds only the guarded durability projection above. Cancellation/resume success/partial transport is the existing MutationResult, without a false worker-settlement success. Full final error/projection freeze follows design clearance.

## K6 benchmark and concurrency proof, required before activation

Named root gate test_capped_source_snapshot_and_create_boundary_holds_with_peer_require_active. Exact2097152 canonical bytes and1000 messages (not a mocked lower cap), including non-ASCII/CRLF and actual id0. Measure selected-channel and run-projection modes, and a revision with a512KiB verified parent. Source setup is outside timing, using real normal owners/validated persisted fixtures; timing uses real MessageStore/SessionStore/ArtifactStore/queue/private brief/default atomic_json/fsync. Managed binding/native birth observations may be controlled and labeled; no provider/process claim.

Ten samples per stated shape on this Windows host, each with100 existing healthy artifact lineages and the exact capped source; default writer/fsync is not patched. Report raw outermost engine/catalog hold durations and lock acquisition waits separately, maximum and all samples, packet bytes/count, prior metadata shape and source hashes. Include copying, allowlist projection, encoding/hashes/token comparison, parent verification, producer checks and durable prepare steps in the relevant hold; no exclusion of nested phases or caching eligibility across calls. A concurrent loop thread repeatedly require_active('peer') with Events records attempt/return times and progress before/after. No sleep-based race assertions, fake clock or artificial timing exclusions. The established import benchmark's fixture/worker approach is the baseline; deterministic barrier mutation races are separate from the timing samples.

PASS: every measured outermost source-capture AND create hold <=0.300s, peer require_active contention <=0.300s on the stated shapes, no deadlock, correct source/queued bytes. If this fails, preserve measurements and return for mechanism review; do not weaken the limit or omit IO. Also test1001 messages and2097153 bytes refuse with no durable request/brief/enqueue, one consistent batch under concurrent edit/delete/Stop with exact token mismatch or exact frozen source, parent-CAS concurrency, and no packet construction from changed chat on replay. Source cap is not a promise that every model can consume the context; existing wrapper context refusals remain visible.

## Execution/acceptance split

After contract review, freeze exact builder/operator service/helper signatures, all public DTO key sets, error/body bounds and idempotent intent reconstruction rules. Only then brief the existing helper (one NEW tests/test_artifact_routes.py, <=12 methods). Root owns snapshot consistency/allowlist/golden/K6/concurrency/replay/crash tests and actual middleware/factory enumeration. Initial infrastructure reds are labeled; observe actual behavioral auth/creation refusals before fixing.

Required checks: every route's real operator middleware denial for bearer/query/duplicate/ambiguous auth, no-store fixed errors; unsupported producer and production-empty no-enqueue; malformed/extra/duplicate/oversize JSON/query/path cases; exact preview bytes/refs/replay; source channel/run/parent edits and Stop boundary; imported/dead-producer reads and new-local revision; partial-write durability with fresh reload; library detached pages; source object corruption scope; binary download Unicode/CRLF/SHA/header/filename; both shared app bindings; unchanged artifact/lifecycle/runtime/queue/review/Stop suites. Full configured discovery and independent source review are separate evidence. No tests/code exist for this draft yet.

Deferred ONLY to reader package: request/revision modal and source picker UX, Markdown node rendering/hostile HTML/link/image policies, visible imported/model/source labels, source tab/bidi warnings, download UI/hash check and rendered layout. This package supplies authenticated data/bytes, not an unsafe interim HTML preview. Deferred acceptance harnesses: native CLI fake client/real MCP, API local fake responder and rendered browser under Ticket19 isolation/nonce/cleanup guards, then the SEPARATE activation commit and final whole-ticket review. No ordinary chat or model-produced declaration can enable authoring.
