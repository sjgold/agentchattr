# Ticket 20 operator routes and consistent source snapshots

Status: PROPOSED contract for independent review. Lifecycle slice4 is independently CLEARED ata38c17b (reviewer632 Python tests171.071s and25 actual-source VM cases). Product9b068af full1659/four skips320.363s is implementation-owner evidence; the later assertions changed tests/docs only. Storage, capability, authority, wrappers and lifecycle/backup contracts remain authoritative. This document authorizes no implementation tests, helper briefing, product code or activation until reviewed and the exact helper payload/signature freeze is cleared. The reviewer-requested design timing spike below exercises existing product code only; it is not a new operator implementation or K6 acceptance. Production SUPPORTED_CAPABILITIES stays ().

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
| Lock budget, OPEN mechanism decision | Keep the0.300s per-hold/peer-wait target, but reject the existing one-hold create mechanism: the requested spike measured0.412-0.685s. Proposed staged publication phases are below and require review and a successful prototype before freeze. | Averages or excluding fsync conceal the failure. Staging alone is not asserted to solve repeated index validation; no implementation gate is declared passable until measured. |

These are proposals for this review, not claims that the routes or benchmark exist. Existing standalone component compatibility stays unchanged.

## HTTP surface and authentication

All paths below are operator-only. New namespace is /api/artifacts, distinct from existing agent-only /api/artifact-briefs/... and /api/artifact-results. No path under the operator namespace is added to a bearer allowlist.

Add a NEW strict middleware branch covering every path starting /api/artifacts (including unmatched suffixes), before the existing token fallback. It accepts exactly ONE X-Session-Token header equal to the configured session token and then sets request.state.auth_origin=operator; the binder also requires that state. Reject duplicate operator headers, ANY Authorization header (even with a valid operator header), and ANY query parameter named token (even with a valid header). Cookie-only, query-only and seat-bearer requests fail403. POST requires Content-Type application/json, allowing only an optional charset=utf-8 parameter; another/missing media type is400 artifact_invalid_request. No body field sets the principal. Existing other namespaces and agent transport auth stay unchanged.

Apply the configured loopback Origin allowlist to this branch. Missing Origin is allowed for non-browser clients; a present Origin must be the exact configured http://localhost:<port>, http://127.0.0.1:<port> or http://[::1]:<port>. Reject duplicate Origin or Host headers. Host must be exactly one of localhost:<port>,127.0.0.1:<port>,[::1]:<port> (case-insensitive hostname), with port omitted allowed only when the configured port is80; no suffix matching, arbitrary forwarded host, credentials or wildcard. This new local-only namespace uses both Host and Origin guards against DNS rebinding. The custom authenticated header plus JSON media type provides the browser CSRF defence; no URL/cookie authentication fallback is added. Test clients use an allowed explicit base URL.

An explicit prefix response handler wraps this namespace and emits no-store/nosniff on ALL responses, including middleware denials, unmatched404, method405 and framework422. It replaces framework422 with fixed400 artifact_invalid_request, unmatched404 with artifact_not_found, and405 with fixed artifact_method_not_allowed; no submitted values are echoed. The handler applies even when no binder endpoint matched. Browser downloads in the later reader MUST use authenticated fetch then a blob download, because an anchor cannot supply the custom header; never put the token in a URL.

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
| GET /api/artifacts/requests/{request_id} | PublicMutation with the allowlisted PublicRequest and QueueProjection below; no launch refs or private brief. |
| POST /api/artifacts/requests/{request_id}/cancel | Body exactly {}. Existing cancel_request semantics projected as PublicMutation. Durable cancellation is distinct from worker/transport settlement. |
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

Preview and create share Intent; create adds preview_token:Hex64. request_id is generated once by the operator client and binds deterministic packet/brief/attempt/dispatch ids. Changed submitted intent for a recorded id is409; no implicit new attempt. A new preview may reuse an unrecorded request id; once recorded, edits/reassignment use a NEW request id. requester is always the server literal operator. For a new lineage, lineage_id:null becomes request_ids(request_id).lineage_id; attempt/dispatch/brief/packet ids are derived by that same existing function, never accepted from the body. The entire producer block comes only from seats.artifact_producer and launch_provenance through the existing service producer check: identity/adapter/name, launch refs, requested model and its reason are server observations. Registry/model/body claims cannot supply them.

selected_channel_messages: ids are unique, at most1000, resolve only in the actual requested channel, and normalize to ascending stored id order. No recent-N implicit scope. Picker text_byte_length measures raw UTF8 text only; the successful preview measures the whole canonical packet, including metadata/envelope overhead. Snippets end on a valid UTF8 boundary and declare truncation. The picker exposes a missing legacy uid as legacy:<id>, matching packet construction. session_id may be null; then source_run/input/input_revision are explicitly absent. A nonnull session id includes that same-channel run's exact frozen input and document metadata as context. Empty ids with no run are an explicit instruction-only scope, disclosed as source_absent; never an inferred fallback after a failed lookup.

run_accepted_messages: session_id required and message_ids must be []. Server derives ids from that run's admitted_events and recorded operator continuation projections, excluding quarantined/unadmitted results, skipped-work notices and unrelated chat. Ordinary human discussion outside those continuations is included only by explicitly checked channel selection (the picker may preselect the run rows; no hidden time-window inference). Input is always that run's input_snapshot.text with its actual revision/document. Stopped/replaced run source is allowed when explicitly selected and labeled by current state/replacement notice; it grants no run/producer authority.

Every linked projection must exist in the channel and match its recorded event/continuation id, stable projection UID and attribution. Validate current projection text against the trusted projector's expected exact text, including its actual missing-contributions footer rule. A missing/mismatched projection refuses the preset; offer explicit channel selection or existing history repair, never construct missing chat from journal content. MessageStore.snapshot_selected and an extracted shared pure expected-projection-text helper ARE in-package implementation work, not assumed APIs: preserve existing projector/footer bytes and run unchanged review/event/projection suites. A selected id that disappeared yields409 artifact_source_unavailable. If create finds the selected rows but edited text changes the candidate audit/token, it yields409 artifact_preview_stale before the preset text-validity refusal; preview itself refuses an edited accepted-run projection as source_unavailable. No missing id is silently dropped.

## Packet snapshot and structural authority allowlist

Add one MessageStore batch-copy read, selecting only requested ids/channel under its lock, with no policy/owner callbacks and no repeated per-id scans. It returns detached rows from one acquisition. Caller already holds engine -> catalog; a detached SessionStore run snapshot is read first and its lock released before MessageStore is locked. Producer manager reads and artifact reads release their locks before touching any other owner. Fixed order stays engine > catalog > manager > store > ledger, never manager+store or two store locks together. Required root test test_session_snapshot_lock_released_before_message_snapshot uses instrumented real locks and two threads/Events to prove SessionStore.get releases before MessageStore.snapshot_selected enters, hooks never enter another owner while holding a store lock, and a concurrent session update/message read completes. Capture remains inside engine/catalog; no owner lock is retained by a detached snapshot.

artifact_sources builds the accepted packet EXACTLY:

```text
{version:1, channel:ChannelName, scope_kind:ScopeKind,
 source_run:null|{session_id,run_id,input_revision,state_at_request},
 input:null|{text,input_revision,source_document:null|DocumentDescriptor},
 messages:[{id,uid,sender,type,timestamp,text,attachments,provenance},...]}
```

Text is the exact captured Unicode string; no newline, BOM, whitespace, bidi or control normalization. A missing legacy uid uses legacy:<id>; an actual equal uid collision is refused, never renamed. Existing required types/UTF8/NUL rules remain. Messages sort ascending id. timestamp is stored value or null, never current time. Missing attachments/provenance become []/{}; no whole-store object is serialized.

BUILT message provenance allowlist: session_id,run_id,event_id,question_event_id,kind,provenance,submitted_by,seat_identity_id,input_revision,session_output, when present and valid. These are source attribution, never a new dispatch binding. Explicitly omit review brief/attempt/dispatch/launch refs, config/provider/settings objects, auth tokens, fingerprint, private seal/owner fields and server paths. Unknown metadata fields are omitted by this fixed projection, not forwarded or promoted to instructions.

BUILT attachment descriptors allow only name,url,type,content_type,mime_type,size,byte_length,sha256,content_sha256,encoding when present with their corresponding bounded JSON primitive types. Do not include path/local_path, tokens, private provider/config fields or nested arbitrary metadata. URLs and names remain untrusted data and are not fetched by the builder or model wrapper. Reader requirement: display attachment url/name as escaped text only; never turn either into a link, image source, navigation, download target or background fetch. DocumentDescriptor reuses document_inputs' validated metadata without text: version,kind,source_id,name,encoding,byte_length,content_sha256. Verify it against input text using the existing validator; no new path locator or guessed revision.

The allowlist is about structure generated by OUR code. Literal user text/names may contain words such as token/path/fingerprint and are preserved; no keyword filter. Previously retained/imported packet bytes remain immutable user data and are not rewritten by this builder. The source-copy sensitivity disclosure continues.

Use sealed_result_io.canonical_utf8 (ensure_ascii=False) and existing _packet_scope for final packet/ref hashes; preserve the separate brief-revision ensure_ascii=True form. Per-message sha256 covers the full allowlisted packet message, not a truncated snippet. Successful preview returns exact canonical packet byte_length, sha256, ordered id/uid/hash refs and input revision from this ONE detached capture, all while the SAME outer boundary remains held. Recheck the supplied preview token against this complete current capture before any create effects. Never compare a token from one read with bytes from a later independent read.

Cap-aware algorithm BEFORE _packet_scope: derive selected ids with an early stop on the1001st unique eligible id; then project rows incrementally in deterministic order. Count the canonical JSON UTF8 bytes of the exact allowlisted envelope/scalars/arrays/objects, including braces, sorted keys, commas and JSON escapes. Encode string characters in bounded chunks with the same escaping as canonical_utf8 (not one full oversized json.dumps/iterencode string allocation); stop once count reaches2097153. Do not hash or present a serialized prefix. Only after this byte/count precheck passes may canonical_utf8 and _packet_scope materialize/validate/hash the complete <=2097152-byte packet. An independent golden must prove counted size equals existing canonical_utf8 for all accepted strings/escapes/non-ASCII/numbers.

Oversize fixed measured shape: {message_count:null|nonnegative_int,packet_bytes:null|nonnegative_int},measurement_complete:bool,lower_bounds:{messages:null|nonnegative_int,packet_bytes:null|nonnegative_int}. Byte early-exit reports packet_bytes:null,measurement_complete:false,lower_bounds.packet_bytes:2097153; lower_bounds.messages may be null if not known. Count early-exit reports message_count:null,packet_bytes:null,measurement_complete:false,lower_bounds.messages:1001,lower_bounds.packet_bytes:null, including a run preset deriving more than1000 ids on the server. If a complete exact measurement exists both measured fields are numeric and lower_bounds values null; no false exact count or incomplete hash. Never truncate a packet. The source picker snippet is labeled text_truncated and never used as packet content. Exact bounded-copy/encoding helper signatures follow the mechanism review; no alternative canonical form is authorized.

REQUIRED NAMED gate: test_locked_packet_snapshot_allowlist_does_not_copy_app_authority. Plant distinct server-owned nonce/seal/token/fingerprint/config/path sentinels in non-allowlisted message/attachment/document metadata, capture through the real builder under the boundary, and assert absent by structural path and sentinel value. Keep literal user text mentioning those field names intact. Verify canonical golden non-ASCII/CRLF bytes and message hashes independently. This gate cannot be deferred past operator-routes/K6 or activation.

## Preview token, replay and durable creation

Token basis is EXACTLY the full server-built immutable audit key set accepted by _audit, with ONLY created_at omitted: version,purpose,request_id,lineage_id,attempt_id,dispatch_id,brief_id,original_channel,requester,producer,source_run,scope,instruction,format,expected_parent. The full producer subobject includes launch_nonce and fingerprint SERVER-SIDE (as well as launch_attempt); these are never projected to the client. Token=SHA256(canonical_utf8(basis)), not a hash of the public DTO or just packet bytes. The unexposed random launch nonce prevents a client constructing a new valid token basis from public labels; SHA256 here remains a freshness guard, not a MAC or authorization mechanism. Relaunch changes the basis. It is optimistic and reusable, not one-time: same request id replays safely through store idempotence; the same token submitted with a NEW request id fails because all derived id fields change. Public preview returns no launch refs/private seal; the token is opaque. No new preview index, expiry timer, boot secret or schema. Requiring a currently active channel and exact current producer is independent of token equality. An archive/reopen with identical source may retain a usable token after the channel is active again; this token binds content/authority, not a catalog revision counter.

The ORIGINAL one-boundary NEW flow was healthy owners/channel -> current producer -> parent/head/pending CAS -> source snapshot/token -> existing prepare_request (packet, reserve, brief, enqueue, queued mark). The first spike rejects it for K6. The reviewed five-phase replacement below preserves packet -> reserve -> brief -> enqueue, but its first prototype STILL FAILS publication timing. A further private evidence-reuse proposal is OPEN; no helper freeze or product code is authorized by these design measurements. In either design, parent <=512KiB is verified by exact id/sequence/hash/length before dispatch; no run_id enters the artifact envelope. An imported lineage revision MUST use its current channel (mismatch => typed409 artifact_channel_mismatch), current head and one-live-slot CAS. Imported unversioned attempts remain imported/read-only, never a pending slot; a well-formed imported head may coexist with them. The lifecycle/import rule forbidding appended imported revisions governs archive import, not a NEW local author request based on an imported head.

EXISTING local id flow comes FIRST after syntax/operator auth (an imported request id is read-only409, never a local-create replay): get_request(request_id), reconstruct the stored token from its immutable audit and compare the normalized Intent/selector with that stored intent. Same token/body returns current row/dispatch view without reading current chat, checking a later producer launch, enqueueing or regenerating. Changed token/intent409. Creation time/current mutable request state are not replay identity. Store one-live/head CAS remains final authority. Normal create replay never invokes R1; explicit resume is separate. HTTP202 is returned only by the invocation that actually reserved a NEW request and completed normal publication as queued; an existing recorded-id replay returns200 regardless of its state, with no repair. A partial new invocation uses the appropriate fixed error HTTP plus durability, never disguises it as202. Replay includes needs_resume:true/resume_reason:transport_missing exactly for a local LIVE prepared/queued/active row whose deterministic queue record is absent; otherwise false/null. It returns the current row without repair; ACTIVE/missing transport may still require operator repair when resume is attempted, not a promise that resume will succeed.

If a write/queue fault occurs after partial durable effects, use a guarded lookup only to report what is known. Error adds request_id, durability:"recorded"|"not_recorded"|"unknown", request:PublicRequest|null; unknown never means empty or rolled back. Prepared recorded requests remain recoverable from frozen data via existing startup/explicit resume. Packet-only orphans remain diagnostics/retained, never deleted. Final error codes and exact helper result shape are review/freeze items before tests; do not invent a second operation journal.

Capability remains empty during this package. Producer choices show the fixed eligibility reason and no automatic restart; preview can return measured source with available=false/token=null. Create always refuses unavailable/legacy/forged-capability producers before new durable effects. Enabled-path fixtures patch runtime_protocol.SUPPORTED_CAPABILITIES in-process ONLY while building the real test managed launch/birth manifest, as earlier component fixtures do, with cleanup restoring(). There is no route, config, environment or production switch. Enabled observations are explicitly labeled fixture controls, not native/provider acceptance; a separate unpatched-default test proves production creation cannot enqueue.

## Read projections, cancellation and download

Every operator response is constructed field-by-field. Never return the internal ArtifactService._projection/MutationResult directly: it removes only launch_nonce and still retains launch_attempt/fingerprint. This proposal LEAVES that accepted internal/agent projection unchanged and adds a public operator projection. Omit launch_attempt,launch_nonce,fingerprint,private brief/seal/owner,consumer_id,capabilities and registry tokens from every BUILT operator DTO, including nested admission, partial-error and list rows. Identity_id is an historical identity label, never launch proof.

The exact proposed DTO key sets (all listed keys required; nullable means explicit null; no additional keys) are:

```text
Page<T>={rows:T[],count:nonnegative_int,truncated:bool}
ProducerLabel={name,identity_id,adapter,requested_model,requested_model_reason}
ProducerChoice={producer:ProducerLabel,available:bool,reason:CapabilityReason|null}
SourceChoice={id,uid,sender,type,timestamp,snippet,text_byte_length,text_truncated:bool}
Parent={version_id,sequence,sha256}
SourceRun={session_id,run_id,input_revision,state_at_request}
MessageRef={id,uid,sha256}
Scope={kind,packet_id,sha256,byte_length,message_refs:MessageRef[],input_revision}
SourceSummary={kind,packet_id,sha256,byte_length,message_count,input_revision}
Observation={confirmed_model,confirmation_reason}
ImportSource={archive_id,original_state,original_reason}
RequestSummary={request_id,lineage_id,dispatch_id,channel,original_channel,state,reason,
 created_at,updated_at,version_id,expected_parent:Parent|null,source_run:SourceRun|null,
 scope:SourceSummary,producer:ProducerLabel,import_source:ImportSource|null}
PublicRequest={request_id,lineage_id,dispatch_id,channel,original_channel,state,reason,
 created_at,updated_at,version_id,expected_parent:Parent|null,source_run:SourceRun|null,
 scope:Scope,producer:ProducerLabel,import_source:ImportSource|null,requester,instruction,format}
VersionSummary={id,lineage_id,channel,sequence,parent_version_id,request_id,sha256,
 byte_length,created_at,source_run:SourceRun|null,scope:SourceSummary,
 producer:ProducerLabel,observation:Observation,import_source:ImportSource|null}
VersionDetail={version:VersionSummary,requester,instruction,format,scope:Scope,markdown}
HeadSummary={id,sequence,sha256,byte_length,created_at}
LineageRow={id,channel,updated_at,head_version_id,head:HeadSummary|null,version_count,
 pending_request_id,pending_request:RequestSummary|null}
LineageDetail={lineage:LineageRow,versions:Page<VersionSummary>,requests:Page<RequestSummary>}
QueueProjection={dispatch_id,state}
PublicAdmission={status:"admitted",event_id,request_id,version_id,sha256}
PublicMutation={request:PublicRequest,dispatch:QueueProjection|null,admission:PublicAdmission|null,
 transport_settled:bool|null,notice:ExistingNotice|null,warning:ExistingWarning|null,
 needs_resume:bool,resume_reason:"transport_missing"|null}
Preview={request_id,lineage_id,channel,producer:ProducerLabel,available:bool,
 reason:CapabilityReason|null,expected_parent:Parent|null,source_run:SourceRun|null,
 scope:Scope,measured:{message_count,packet_bytes},measurement_complete:true,
 notices:SourceNotice[],preview_token:Hex64|null}
SourceResponse={request_id,scope:Scope,packet:SourcePacket}
```

Types reuse accepted schemas: IDs Hex32, sha256/input_revision Hex64 (input_revision nullable without input); names/text are bounded existing strings; time fields nonnegative finite numbers (source timestamp nullable); sequence positive int; byte/count fields nonnegative ints; nullable labels/reasons as in stored audit/observation. SourceNotice is a CLOSED code in source_absent,source_stopped,source_replaced (no interpolated text). ExistingNotice/ExistingWarning are exactly the accepted service literals, not exception text; final signature freeze lists them before tests. CapabilityReason is the accepted capability enum listed in the wire section. SourcePacket is the exact packet schema above. Preview.lineage_id is always the server-derived/existing Hex32, never null. SourceSummary.message_count=len(scope.message_refs); RequestSummary.created_at=audit.created_at; fields absent on local rows project import_source:null. Historical model observation on imported rows is archive-recorded, never a live verification.

Route bodies are EXACTLY: producers => Page<ProducerChoice>; sources => Page<SourceChoice>; preview => Preview; create/revision/request GET/cancel/resume => PublicMutation; library => Page<LineageRow>; lineage GET => LineageDetail; source GET => SourceResponse; version GET => VersionDetail; download => raw bytes/headers only. Errors use only the wire/error/durability key sets below, not a DTO dump. Build compact nested pending_request explicitly instead of returning _lineage_row's current pending payload. Lists order updated_at desc/id asc; versions sequence desc. Versions derive import_source from their request, never mutate stored provenance. Reads are detached.

REQUIRED test test_operator_response_allowlists_exclude_launch_authority exercises EVERY real route success/error/partial body with distinct launch_attempt/nonce/fingerprint/seal/token sentinels in internal stored/service records and verifies the explicit DTO keys and generated values contain none. Cover parent, imported provenance, pending row, admission, list, source, download headers and unexpected failures. Exact Markdown and immutable retained SourcePacket contents are user data, so literal words or historical raw user metadata are preserved, as the accepted backup rule requires; the golden targets authority generated by app code, not keyword-censoring authored/user text. The new source builder must separately pass the named structural leak gate.

Reads work for archived/deleted/imported history and dead/replaced producers without a live gate. Unknown membership404; corrupt body/packet503 per-object, peers readable; corrupt index503/no reseed. No reader auto-repair/quarantine. Cancel on already cancelled/operator_cancelled is idempotent200; cancel of other terminal/imported rows that would mutate them is409/read-only. Resume(recover_saved=true) on fulfilled local work performs the accepted lost-ACK repair and returns200; resume of other local terminal states returns their plain current PublicMutation200. Imported resume(false) is a read-only200 current-row no-op; imported resume(true), which attempts recovery authority, refuses409/read-only. No blanket terminal409 may bypass the fulfilled ACK repair. A NEW local revision of imported content does not change an imported row.

Cancel projects existing request-first cancellation semantics, with transport_settled=false/warning visible, never an exit/remote-cancel claim or chained delete. Explicit resume preserves R1 and bookkeeping-only lost-ACK repair; failed transport with saved content never startup-auto-admits. No client-supplied consumer/owner/exit evidence.

Download verifies membership and stored SHA/length, returns exact UTF8 bytes in binary mode, Content-Type:text/markdown; charset=utf-8, X-Content-SHA256:<lowerhex>, Content-Disposition:attachment; filename="artifact-<lineage_id>-r<sequence>.md", Content-Length and nosniff/no-store. No title/path/header reflection, newline conversion, HTML serving or model call. JSON detail round-trips the same string bytes; source-only rendering/sanitization lives in the reader package.

## Fixed error wire proposal

Flat {code,error}; only the explicit typed count/durability/reason fields below may be added. Add ArtifactOperatorError with a CLOSED reason discriminator (no client string): request_unknown,request_read_only,producer_unavailable,parent_changed,source_unavailable,preview_stale,channel_mismatch,request_conflict,request_pending,channel_unavailable,object_unavailable,storage_unavailable,operator_unavailable. Binder maps the reason table, never parses exception messages. Operator service detects unknown resources from get_* returning None and raises request_unknown (404), including the legacy core unknown-request ArtifactConflict case; scope specific producer/head/source checks and replay comparisons into typed reasons under the boundary. Existing unclassified ArtifactConflict remains409 artifact_request_conflict; it is never guessed404 from free text. Core shared error semantics remain unchanged; any needed additive typed raise-site changes must be frozen and tested across existing callers. Conflict is mapped before ValueError. No exception strings/paths/headers/payload logging; unexpected failures log TYPE only and fixed503. Map ChannelConflict/ArtifactConflict before ValueError, and per-object unavailable before generic validation. No FastAPI422 detail containing submitted values.

| HTTP | code | fixed error |
| --- | --- | --- |
|400|artifact_invalid_request|Invalid artifact request.|
|403|artifact_operator_required|Operator session required.|
|404|artifact_not_found|Saved artifact resource was not found.|
|409|artifact_preview_stale|Artifact source or request context changed. Refresh the preview.|
|409|artifact_request_conflict|That request identifier already records different artifact work.|
|409|artifact_parent_changed|The artifact head changed. Refresh the revision preview.|
|409|artifact_request_pending|This artifact already has pending work. Cancel or settle it before requesting another version.|
|409|artifact_producer_unavailable|The selected author is unavailable for artifact requests.|
|409|artifact_channel_unavailable|Choose an active channel without pending channel repair.|
|409|artifact_source_unavailable|The selected source is unavailable. Select messages explicitly or repair the source.|
|409|artifact_request_read_only|This saved request cannot perform that modifying action.|
|409|artifact_channel_mismatch|The request channel differs from the artifact channel.|
|405|artifact_method_not_allowed|This artifact route does not accept that method.|
|413|artifact_source_too_large|The selected source exceeds the artifact packet limit. Choose a smaller scope; nothing was truncated.|
|503|artifact_storage_unavailable|Saved artifact storage is unavailable. Repair storage and reload.|
|503|artifact_object_unavailable|This saved artifact object is unavailable. Its metadata is retained.|
|503|artifact_operator_unavailable|Artifact management is unavailable. Reload after startup.|

Producer-unavailable may add only reason from the accepted capability enum (artifact_capability_missing/runtime_unverified/producer_unavailable/unmanaged_producer/capability_binding_changed). Source-limit rejection adds exactly limits{packet_bytes:2097152,messages:1000},measured{message_count:int|null,packet_bytes:int|null},measurement_complete:bool,lower_bounds{messages:int|null,packet_bytes:int|null} as defined by the early-exit algorithm; no prefix hash or incomplete data labeled complete. Mid-write failure adds only the guarded durability projection above. Cancellation/resume success/partial transport projects the existing internal MutationResult into PublicMutation, without launch authority or a false worker-settlement success. Full final error/projection freeze follows design clearance.

## K6 benchmark and concurrency proof, required before activation

The two original holds are explicitly (a) snapshot+allowlist projection+canonical scope/hash/token while engine/catalog remain held, (b) WHOLE create, including that capture plus parent/producer checks and ALL existing prepare_request packet/reserve/brief/enqueue/queued persistence. Timing only put_packet or splitting nested reentrant spans does not measure (b). Peer require_active wait is a separate latency measurement. Both were proposed <=0.300s.

### Observed baseline, existing path FAILS the proposed budget

Reviewer-requested spike executed2026-10-25 from an ignored .audit-tmp script against unchanged product3f40912. Real MessageStore/ArtifactStore/catalog/queue/private-brief IO, real fsync/default atomic_json, fixture-supported managed binding with controlled process/native observations only.100 existing imported lineages,10 of them with exact524288-byte heads;10 distinct revisions, so lineage count stays100 while requests/index grow. Each packet has1000 real stored messages starting id0, exact2097152 canonical bytes, Unicode/CRLF, scope sha2561c69d2a89d37aafee3f8ea5dec4f1f892ec60592964d361b4e281556a9f8d2bf. Source acquisition is a prototype detached copy of already allowlisted rows, not the not-yet-built snapshot/allowlist or run-projection helper. No API/provider/network/native execution. Thus these are design measurements, not K6 acceptance or a bound for the unimplemented builder.

| Sample | snapshot hold s | whole-create hold s |
| --- | --- | --- |
|1|0.041512|0.411677|
|2|0.041037|0.440929|
|3|0.039318|0.470061|
|4|0.039396|0.503954|
|5|0.040400|0.552584|
|6|0.039841|0.561640|
|7|0.040310|0.604775|
|8|0.040493|0.653826|
|9|0.040108|0.684326|
|10|0.040841|0.684864|

Peer maximum require_active wait0.677207s. Outermost acquisition waits0.000005-0.000709s were recorded separately. All ten whole-create samples exceed0.300s; snapshot-only does not. The snapshot prototype measures copy/projection/scope hashing, not producer/token/run-helper validation, so it is not acceptance of full hold(a). Whole-create includes current producer/parent/audit token work and existing durable prepare steps. Receipt and script retained locally in .audit-tmp/ticket20_operator_spike.{json,py}, shellc11e87d9 exit0. Exit0 means measurement completed, NOT a passing timing gate. Cleanup joined peer and invoked fixture shutdown/temp cleanup; the shell is stopped. The accepted source/count/parent caps remain unchanged. **The one-hold mechanism is rejected; the timing contract is NOT cleared.**

### Reviewed phase split, prototype still FAILS publication budget

Reviewer ACCEPTED the split with M1-M4, preserving packet -> reserve -> brief -> enqueue. The accepted structural phases replace the earlier proposal that staged a secret-bearing brief before a request:

1. Capture/project/validate under engine/catalog. SessionStore lock is released before MessageStore. Build exact packet/audit/token and verify parent/current producer/head; no durable write.
2. Stage ONLY the immutable packet OUTSIDE engine/catalog. Add a separate unguarded root-bound store staging API; guarded put_packet and existing prepare_request stay unchanged. Use the same private created-object receipt semantics as import: created vs reused, uncertain I/O receipt null, count only this invocation's objects still unreferenced under the store metadata lock. Orphans are reported, never deleted and never counted as created requests/versions. Stage after replay/classification check, never overwrite.
3. Short reserve boundary: re-capture/recompute source/token and recheck Stop/run state, channel, producer, parent/pending CAS. Fresh scope.sha256 AND byte_length must equal the staged scope (and full scope fields must agree); difference =>409 artifact_preview_stale with staged orphan report. A private same-invocation plan may skip reading the2MiB packet during reserve ONLY after verifying its root-bound file fingerprint (mtime_ns,size), as accepted for import plans. Full _persist index validation/real fsync remain. Persist PREPARED then release boundary: this is creation's durable linearization point.
4. Private brief put-once OUTSIDE the boundary, AFTER reservation. No brief with a seal secret is created without a durable request. Stop may cancel the prepared request during this phase; a brief then grants nothing because publication rechecks state. Existing after-reserve/before-brief and after-brief/before-enqueue recovery seams remain.
5. Separate publication boundary: re-read exact request, require still prepared/uncancelled, recheck current producer/channel/head, existing coordinator-authorized enqueue and queued mark. Stop between reserve/publish sees PREPARED and cancels without enqueue. No ledger callback into owners, raw paths closed, no cross-invocation eligibility cache. Incomplete publication reports actual durability/current row, never blind retry. The existing prepare_request and guarded put_packet stay byte-for-byte unchanged; recovery/resume retain their existing path.

Private staged-plan stat checking shares import's limitation: mtime_ns+size is not a cryptographic proof against an out-of-process writer deliberately restoring both; put-once internal writes plus final metadata/CAS checks remain the accepted protection. No new persisted schema, operation journal or public capability flag. Exact plan/receipt/error signatures await review/freeze. On failed stage/reserve, the eventual error projection must include counted orphan metadata (objects/bytes, or null with staging_io_unconfirmed); it may never claim a new request from staging alone.

### Phased prototype result, retained failure

Ran the reviewed phases against unchanged product6da23f7 in an ignored script, with the same100-lineage/10-revision,2097152-byte/1000-message,524288-byte-parent shape as the first spike. Real fsync/default writer, same source hash; controlled supported managed observations only. Prototype uses the existing reserve_request with a PRIVATE instance-local _packet reuse patch ONLY during reserve, verifying exact staged stat first; _persist/full-index validation are unmodified. Publication uses the REAL coordinator validate_enqueue and full packet re-read (no authorization bypass). The unguarded packet stage is a script-local call to existing _put_bytes plus private receipt/stat construction, not a product API. Capture still uses a prototype batch copy of known allowlisted selected-channel rows; no final operator builder/run helper/auth/race/crash acceptance exists yet.

An Event-controlled peer attempts require_active inside each measured hold and concurrently during the two outside phases. Hold timing includes peer-attempt synchronization and every nested operation; peer completion is awaited outside the boundary before the next phase, and total wall includes that scheduling. This isolates per-phase waits; it does not prove fairness for an implementation that immediately re-acquires without giving a waiting peer progress. The final real benchmark must also exercise consecutive phases without this rendezvous and retain the every-wait bound.

| Sample | capture hold s | packet stage wall s (outside) | reserve hold s | brief wall s (outside) | publish hold s | total wall s |
| --- | --- | --- | --- | --- | --- | --- |
|1|0.082033|0.042633|0.122113|0.003345|0.184881|0.436507|
|2|0.074288|0.042224|0.135028|0.002840|0.205187|0.461302|
|3|0.075719|0.042860|0.147657|0.002655|0.220363|0.490816|
|4|0.078272|0.043473|0.166095|0.002846|0.244147|0.536391|
|5|0.075144|0.042295|0.176339|0.002758|0.250716|0.548811|
|6|0.079496|0.043690|0.195944|0.002845|0.261608|0.584967|
|7|0.073763|0.043661|0.217611|0.002957|0.275277|0.615032|
|8|0.074319|0.042258|0.219318|0.003146|0.295678|0.636390|
|9|0.076586|0.043340|0.236379|0.002971|0.327580|0.688397|
|10|0.075008|0.042861|0.272222|0.003280|0.319327|0.714254|

| Sample | peer wait capture s | peer wait packet stage s | peer wait reserve s | peer wait brief s | peer wait publish s |
| --- | --- | --- | --- | --- | --- |
|1|0.082491|0.030331|0.122492|0.000686|0.185335|
|2|0.074880|0.030546|0.135484|0.000776|0.205682|
|3|0.076183|0.030414|0.148113|0.000748|0.220806|
|4|0.078762|0.031306|0.166520|0.000836|0.244578|
|5|0.075592|0.030534|0.176725|0.000713|0.251231|
|6|0.079903|0.019966|0.196326|0.000900|0.262006|
|7|0.074229|0.031135|0.218087|0.000685|0.275757|
|8|0.074783|0.030025|0.219783|0.000741|0.296216|
|9|0.077064|0.031274|0.236840|0.000886|0.327973|
|10|0.075458|0.030654|0.272690|0.000838|0.319730|

**FAIL:** publication samples9/10 hold0.327580/0.319327s, peer waits0.327973/0.319730s exceed0.300s. Maximum capture0.082033s, reserve0.272222s; total create wall0.436507-0.714254s. Do not round0.327580 down to the threshold, discard the late samples, reset index between samples or call this a K6 pass. Receipt retains every phase/acquisition duration, all50 peer waits, total wall, source hash, fsync_mocked:false and persist_validation_bypassed:false in .audit-tmp/ticket20_operator_phased_spike.json; script adjacent. Tracked shella1bcfec2 exit0 means measurement completed only. Script asserts successful fixture cleanup, absent temp root and joined peer; no shell/native/provider resources remain.

### Next mechanism question, OPEN and not prototyped

Publication still performs a full staged-packet read/parse/canonicalization inside validate_enqueue; the accepted stat-plan shortcut above is reserve-only. Propose extending that same PRIVATE invocation's exact staged-packet evidence to the coordinator's validate_enqueue call, with root/stat/scope/audit equality checked immediately before ledger entry. All current request-state/producer/channel/brief/envelope checks still execute, and the raw queue API remains closed. No envelope/body boolean grants a bypass; no plan survives to another request, claim, poll, admission, recovery or resume. Non-plan callers keep full existing packet validation. This changes neither queue event shape nor _persist whole-index validation. This is a proposal to measure, not a claim that packet I/O is the sole bottleneck or that it will meet0.300s. Do not implement/prototype this extension until the reviewer accepts its authority boundary; then rerun all phases/waits at the same growing-index shape. If it still fails, preserve that failure and return for mechanism review. DTO/signature freeze and helper briefing remain blocked.

Required eventual root gate remains test_capped_source_snapshot_and_create_boundary_holds_with_peer_require_active. After mechanism clearance, freeze named phases explicitly: snapshot, reserve recheck+commit, publish+queued mark (and total wall time reported separately, never called one hold). Benchmark selected-channel AND run-projection modes, exact2097152 canonical bytes/1000 messages/id0/UnicodeCRLF, max512KiB parent,100 healthy prior lineages,10 samples per stated shape with normal owners/real fsync. Report all durations/acquisition waits/maxima/source hashes and prior metadata sizes; no discarded samples or IO exclusions. An Event-coordinated require_active peer must progress before/after each phase, with every actual hold AND peer wait <=0.300s, no deadlock. A full create total may exceed0.300s only if it releases the boundary between the documented phases; that is a proposed change to the original one-hold design, not a restated pass.

Separately test1001 messages/2097153 bytes no durable request/brief/enqueue, consistent capture under edit/delete/Stop, stale token/parent CAS races, prepared Stop in the stage-to-publish gap, crash at each phase, stage failure/orphans and stored replay never reading changed chat. Source cap does not promise every model can consume the context; existing wrapper refusals stay visible. These future tests/implementation remain blocked pending mechanism and exact payload review.

Reviewer-required root red-first gates for the split are explicit: test_stop_between_reserve_and_publish_cancels_prepared_without_dispatch (Event-interleaved actual Stop); test_crash_after_packet_stage_before_reserve_reports_orphan (no brief/request/queue); test_crash_after_reserve_before_brief_recovers and test_crash_after_brief_before_enqueue_recovers (existing prepared recovery); test_source_change_before_reserve_refuses_preview_stale; test_split_create_matches_prepare_request_stored_state (same audit, equivalent durable row/packet/brief/queue semantics); test_concurrent_same_request_create_has_one_winner_and_one_replay. Stage receipt created/reused/unknown-I/O accounting, foreign-root/stat tamper and all unchanged recovery/Stop suites remain required. These are planned tests, not executed prototype coverage. Any proposed enqueue-evidence extension adds its own strict negative authority tests before implementation.

## Execution/acceptance split

After contract AND staged-mechanism review plus a passable timing prototype, freeze exact builder/operator service/helper signatures, the remaining nested type/literal bounds, error/body bounds and idempotent intent reconstruction rules. Public DTO key sets above are proposed for this review and cannot widen silently. Only then brief the existing helper (one NEW tests/test_artifact_routes.py, <=12 methods). Root owns snapshot consistency/allowlist/golden/K6/concurrency/replay/crash tests and actual middleware/factory enumeration. Initial infrastructure reds are labeled; observe actual behavioral auth/creation refusals before fixing.

Required checks: every route's real operator middleware denial for bearer/query/duplicate/ambiguous auth, no-store fixed errors; unsupported producer and production-empty no-enqueue; malformed/extra/duplicate/oversize JSON/query/path cases; exact preview bytes/refs/replay; source channel/run/parent edits and Stop boundary; imported/dead-producer reads and new-local revision; partial-write durability with fresh reload; library detached pages; source object corruption scope; binary download Unicode/CRLF/SHA/header/filename; both shared app bindings; unchanged artifact/lifecycle/runtime/queue/review/Stop suites. Full configured discovery and independent source review are separate evidence. No product operator-route tests/code exist for this draft yet; the explicitly requested ignored design spikes measured existing components and a private script-local phase/plan prototype; production source is unchanged.

Deferred ONLY to reader package: request/revision modal and source picker UX, Markdown node rendering/hostile HTML/link/image policies, visible imported/model/source labels, source tab/bidi warnings, authenticated fetch-to-blob download UI/hash check (no credential URLs), attachment URL/name text-only rendering and rendered layout. This package supplies authenticated data/bytes, not an unsafe interim HTML preview. Deferred acceptance harnesses: native CLI fake client/real MCP, API local fake responder and rendered browser under Ticket19 isolation/nonce/cleanup guards, then the SEPARATE activation commit and final whole-ticket review. No ordinary chat or model-produced declaration can enable authoring.
