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

The ORIGINAL one-boundary NEW flow was healthy owners/channel -> current producer -> parent/head/pending CAS -> source snapshot/token -> existing prepare_request (packet, reserve, brief, enqueue, queued mark). The first spike rejects it for K6. The reviewed five-phase replacement below preserves packet -> reserve -> brief -> enqueue, but its first prototype STILL FAILS publication timing. The reviewer accepted a further invocation-local evidence extension; its selected-channel prototype now meets the budget including consecutive phases. The exact signature/DTO freeze below is PROPOSED for independent review; no product code or helper brief is authorized by prototype timing alone. In either design, parent <=512KiB is verified by exact id/sequence/hash/length before dispatch; no run_id enters the artifact envelope. An imported lineage revision MUST use its current channel (mismatch => typed409 artifact_channel_mismatch), current head and one-live-slot CAS. Imported unversioned attempts remain imported/read-only, never a pending slot; a well-formed imported head may coexist with them. The lifecycle/import rule forbidding appended imported revisions governs archive import, not a NEW local author request based on an imported head.

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

Types reuse accepted schemas: IDs Hex32, sha256/input_revision Hex64 (input_revision nullable without input); names/text are bounded existing strings; time fields positive finite numbers (source timestamp nullable); sequence positive int; byte/count fields nonnegative ints; nullable labels/reasons as in stored audit/observation. SourceNotice is a CLOSED code in source_absent,source_stopped,source_replaced (no interpolated text). ExistingNotice/ExistingWarning are exactly the accepted service literals, not exception text; final signature freeze lists them before tests. CapabilityReason is the accepted capability enum listed in the wire section. SourcePacket is the exact packet schema above. Preview.lineage_id is always the server-derived/existing Hex32, never null. SourceSummary.message_count=len(scope.message_refs); RequestSummary.created_at=audit.created_at; fields absent on local rows project import_source:null. Historical model observation on imported rows is archive-recorded, never a live verification.

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
|413|artifact_request_too_large|Artifact request body exceeds 262144 bytes.|
|413|artifact_source_too_large|The selected source exceeds the artifact packet limit. Choose a smaller scope; nothing was truncated.|
|503|artifact_storage_unavailable|Saved artifact storage is unavailable. Repair storage and reload.|
|503|artifact_object_unavailable|This saved artifact object is unavailable. Its metadata is retained.|
|503|artifact_operator_unavailable|Artifact management is unavailable. Reload after startup.|

Producer-unavailable may add only reason from the accepted capability enum (artifact_capability_missing/runtime_unverified/producer_unavailable/unmanaged_producer/capability_binding_changed). Source-limit rejection adds exactly limits{packet_bytes:2097152,messages:1000},measured{message_count:int|null,packet_bytes:int|null},measurement_complete:bool,lower_bounds{messages:int|null,packet_bytes:int|null} as defined by the early-exit algorithm; no prefix hash or incomplete data labeled complete. Mid-write failure adds only the guarded durability and staged-orphan projections in the exact freeze below. Cancellation/resume success/partial transport projects the existing internal MutationResult into PublicMutation, without launch authority or a false worker-settlement success. Full final error/projection freeze follows design clearance.

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

### Accepted invocation evidence extension and passing DESIGN prototype

Reviewer accepted invocation-scoped packet evidence for coordinator validate_enqueue. It is private context-local state created during ONE operator create invocation, cleared in finally. It never enters the HTTP body, envelope, ledger or persisted schema, nor another thread/request, claim, poll, admission, recovery or resume. At the pre-ledger hook it is usable only when root, staged-file stat(mtime_ns,size), full scope including digest/length, and frozen audit all match this invocation; ANY absence/mismatch falls back to the existing full packet read. All request/live producer/channel/brief/envelope checks and _persist whole-index validation remain. Claim-time get_brief/get_delivery ALWAYS fully read and validate the packet before generation, even on a plan publication. A same-size/mtime-restored external edit can evade the publication stat check but MUST be caught by that full claim-time hash check; this residual is stated, not treated as a cryptographic stat proof.

Two sequential ignored prototype runs on unchanged productac30259 used the same growing-index100-lineage/10-revision,2MiB/1000-message/id0/UnicodeCRLF/512KiB-parent shape with real fsync. The script uses ContextVars around reserve and the validate_enqueue packet read only; existing checks and final index validation execute. It asserts cleared context after each use and default context in the peer. These assertions are not the full evidence-isolation/fallback/tamper regression suite, which remains root-owned before implementation acceptance. No product API or source/test file changed. The final builder/run-preset/strict HTTP work is still absent: these are selected-channel mechanism measurements, not final K6 or component clearance.

The isolated run Event-aligns a peer with each phase; the FAIRNESS run has a second thread repeatedly call require_active immediately, with NO wait-for-peer-completion rendezvous, pause or yield between main-thread phases. The peer records every wait, including calls spanning adjacent phases. Total wall is reported independently; no nested phase is relabeled as a whole-create hold.

#### Isolated run, ten samples

| Sample | capture hold s | packet stage wall s (outside) | reserve hold s | brief wall s (outside) | publish hold s | total wall s |
| --- | --- | --- | --- | --- | --- | --- |
|1|0.079236|0.043870|0.131276|0.003421|0.146748|0.406294|
|2|0.078637|0.046132|0.148299|0.003042|0.166895|0.444560|
|3|0.075122|0.043967|0.156665|0.003154|0.177101|0.457624|
|4|0.073768|0.042295|0.172445|0.003068|0.193133|0.486288|
|5|0.073979|0.043017|0.186143|0.003003|0.204222|0.512124|
|6|0.074009|0.041836|0.209214|0.003188|0.222751|0.552710|
|7|0.074363|0.042273|0.224466|0.002911|0.237690|0.583240|
|8|0.074136|0.043275|0.235080|0.003126|0.251758|0.608777|
|9|0.073857|0.042311|0.241458|0.003130|0.286883|0.649086|
|10|0.073549|0.043817|0.267801|0.003076|0.283688|0.673602|

Every recorded peer require_active wait in seconds, in completion order (raw precision, no discarded records):

```json
[0.07973340002354234,0.03163069998845458,0.1317190999398008,0.0007260000566020608,0.1472952999174595,0.07909240003209561,0.021512300008907914,0.14879929996095598,0.0007810000097379088,0.16726809996180236,0.07558990002144128,0.03107969998382032,0.15724730002693832,0.0007409999379888177,0.1774738000240177,0.07424760004505515,0.029817100032232702,0.17290000000502914,0.0009215000318363309,0.19357620005030185,0.07434249995276332,0.030921500059776008,0.18669979996047914,0.0007686000317335129,0.20485490001738071,0.0744942999444902,0.029270999948494136,0.20969639997929335,0.0008001999231055379,0.2232912000035867,0.07483370008412749,0.03056400001514703,0.22494270000606775,0.0007012999849393964,0.23807570000644773,0.07451780000701547,0.03144279995467514,0.23551269993185997,0.0007946999976411462,0.2521372999763116,0.07430570002179593,0.03008830000180751,0.24183020007330924,0.0007535999175161123,0.2873052000068128,0.07399359997361898,0.031136700068600476,0.26830390002578497,0.0007697000401094556,0.2842020000098273]
```

Peer calls=50, maximum hold=0.286882700s, maximum peer wait=0.287305200s.

#### Fairness run, ten samples

| Sample | capture hold s | packet stage wall s (outside) | reserve hold s | brief wall s (outside) | publish hold s | total wall s |
| --- | --- | --- | --- | --- | --- | --- |
|1|0.077561|0.043057|0.126435|0.003447|0.143935|0.397782|
|2|0.076496|0.045251|0.142976|0.003180|0.160783|0.432594|
|3|0.074622|0.043828|0.155609|0.003631|0.176505|0.457789|
|4|0.073316|0.044105|0.170377|0.003692|0.192060|0.487145|
|5|0.077355|0.051296|0.192721|0.003359|0.205808|0.534221|
|6|0.073934|0.042909|0.205719|0.003073|0.218025|0.547319|
|7|0.074096|0.044382|0.214158|0.003536|0.234013|0.573900|
|8|0.075184|0.042656|0.248696|0.003398|0.248400|0.621956|
|9|0.075580|0.043092|0.244847|0.003482|0.287293|0.657900|
|10|0.080319|0.044125|0.260046|0.003214|0.287088|0.678716|

Every recorded peer require_active wait in seconds, in completion order (raw precision, no discarded records):

```json
[0.0004611000185832381,0.00038920005317777395,0.0003274999326094985,0.0003823000006377697,0.1080591999925673,0.00044490001164376736,0.00039760000072419643,0.0003988000098615885,0.0003237000200897455,0.0003765999572351575,0.00033199996687471867,0.00032240001019090414,0.0065876999869942665,0.0004328000359237194,0.0006976999575272202,0.00040719995740801096,0.00040520005859434605,0.0003499999875202775,0.0003095000283792615,0.000560399959795177,0.0004905000096186996,0.0004024999216198921,0.00039080006536096334,0.12728980008978397,0.000622799969278276,0.0005193999968469143,0.0005653999978676438,0.00037219992373138666,0.0003192999865859747,0.0003602000651881099,0.0003174000885337591,0.00031409994699060917,0.0003105999203398824,0.14453659998252988,0.000345399952493608,0.0003515999997034669,0.0003942999755963683,0.10815149999689311,0.00045009993482381105,0.000407799961976707,0.0004093999741598964,0.0004088999703526497,0.00036100007127970457,0.00033430010080337524,0.00032190000638365746,0.006978200050070882,0.0006108999950811267,0.0005471999756991863,0.0005058000097051263,0.000519599998369813,0.0004285998875275254,0.00035069999285042286,0.00032650004141032696,0.00042619998566806316,0.0004456000169739127,0.00034330005291849375,0.00034060003235936165,0.00035550002939999104,0.143901800038293,0.0006313999183475971,0.0005209000082686543,0.0003989000106230378,0.00031969998963177204,0.0003295999485999346,0.00048719998449087143,0.00032049999572336674,0.00033059995621442795,0.16132489999290556,0.00034879997838288546,0.00032679992727935314,0.00031999999191612005,0.10610109998378903,0.0004417999880388379,0.0004026999231427908,0.00038790004327893257,0.0004336999263614416,0.00045119994319975376,0.00045000005047768354,0.00656360003631562,0.0004091999726369977,0.00047369999811053276,0.00039249996189028025,0.00035149999894201756,0.00032220000866800547,0.00035880005452781916,0.0003228000132367015,0.0003325999714434147,0.0004056999459862709,0.00034559995401650667,0.00032650004141032696,0.00031949998810887337,0.15641869988758117,0.0004844000795856118,0.0005314000882208347,0.00047229998745024204,0.00034330005291849375,0.00037949997931718826,0.00033799989614635706,0.0004051000578328967,0.0004533999599516392,0.00046749995090067387,0.1770979999564588,0.0004205999430269003,0.00033439998514950275,0.0003250000299885869,0.10496599995531142,0.0005071000196039677,0.0004143000114709139,0.0003931999672204256,0.0004409999819472432,0.0004311000229790807,0.00043649994768202305,0.006922699976712465,0.00048159994184970856,0.0005189999938011169,0.00034439994487911463,0.0003234000178053975,0.00032380002085119486,0.00030890002381056547,0.00031969998963177204,0.00043080002069473267,0.0003198999911546707,0.0003133999416604638,0.0003197999903932214,0.17115489998832345,0.000539399916306138,0.00047109997831285,0.0006046999478712678,0.0004104999825358391,0.00032920006196945906,0.0003347999881953001,0.0004708000924438238,0.0004230000777170062,0.00039599998854100704,0.192695900099352,0.0004205000586807728,0.0004121999954804778,0.11552660004235804,0.00046580005437135696,0.000408399966545403,0.00039770000148564577,0.0003988000098615885,0.0003282000543549657,0.0003261000383645296,0.0067659999476745725,0.0006258999928832054,0.00048559997230768204,0.0004285000031813979,0.0003541000187397003,0.00032049999572336674,0.00032510003075003624,0.0003208999987691641,0.0003306999569758773,0.00031589996069669724,0.00034060003235936165,0.00036239996552467346,0.0003309999592602253,0.00033329997677356005,0.0003432999365031719,0.19354940007906407,0.000555400038138032,0.00045350007712841034,0.0005175000987946987,0.00039240007754415274,0.0004165999125689268,0.00039379997178912163,0.00035880005452781916,0.00032359990291297436,0.0003215000033378601,0.2063695000251755,0.0003402000293135643,0.0003263000398874283,0.0003421000437811017,0.10452749999240041,0.0004827999509871006,0.0003942999755963683,0.00038709992077201605,0.0003829000052064657,0.0003743999404832721,0.00033870001789182425,0.006371999974362552,0.0005945999873802066,0.0006546999793499708,0.00038049998693168163,0.0003421999281272292,0.00039409997407346964,0.0003209999995306134,0.00031160004436969757,0.00032760004978626966,0.0004120999947190285,0.00031839997973293066,0.00031409994699060917,0.0003138999454677105,0.2066542999818921,0.0004627000307664275,0.0003795999800786376,0.0004374999552965164,0.00034769997000694275,0.00041039998177438974,0.00043919996824115515,0.0004062999505549669,0.00039409997407346964,0.21857280004769564,0.0004396000877022743,0.00040460005402565,0.10534829995594919,0.0005193999968469143,0.0004667999455705285,0.0003931999672204256,0.000485299970023334,0.00046170002315193415,0.006605600006878376,0.0008599000284448266,0.000588199938647449,0.0005765999667346478,0.00037260004319250584,0.0003355999942868948,0.0003192999865859747,0.000319099985063076,0.0003573000431060791,0.0004032999277114868,0.0003261000383645296,0.0003209999995306134,0.00031560007482767105,0.0003160000778734684,0.2149904000107199,0.0006164000369608402,0.0005272999405860901,0.00045149994548410177,0.00037260004319250584,0.0003228000132367015,0.0003443000605329871,0.0003421000437811017,0.00031969998963177204,0.0003266999265179038,0.0003256000345572829,0.23459849995560944,0.0003397000255063176,0.00032750004902482033,0.0003231000155210495,0.10588489996735007,0.00036720000207424164,0.00033950002398341894,0.0003298999508842826,0.00032540003303438425,0.0003336999798193574,0.0003369000041857362,0.0003295999485999346,0.00031269993633031845,0.006513700005598366,0.0004588000010699034,0.0005052000051364303,0.0003353999927639961,0.0003124999348074198,0.00030860002152621746,0.0003200999926775694,0.00033249997068196535,0.00032759993337094784,0.0005889000603929162,0.0003589000552892685,0.24958810000680387,0.0005749000702053308,0.0005900000687688589,0.000461899908259511,0.00034360005520284176,0.00035180000122636557,0.00034909998066723347,0.00032540003303438425,0.00031859998125582933,0.0003151999553665519,0.24901360005605966,0.00041390000842511654,0.000394499977119267,0.10616139997728169,0.0004539999645203352,0.00040579994674772024,0.0003532000118866563,0.0003499999875202775,0.0003333999775350094,0.00032279989682137966,0.0003231000155210495,0.006388899986632168,0.0006177999312058091,0.0005849000299349427,0.0004288000054657459,0.0003584000514820218,0.00032490002922713757,0.0003339000977575779,0.00031130004208534956,0.0003256000345572829,0.0003605000674724579,0.000344799947924912,0.00034629995934665203,0.0003229000139981508,0.24574819998815656,0.0006567999953404069,0.0005308000836521387,0.00048530008643865585,0.0004100000951439142,0.0003499999875202775,0.00034200004301965237,0.00034359993878751993,0.00031749997287988663,0.00041259999852627516,0.2878871000139043,0.0003429000498726964,0.00032789993565529585,0.00032600003760308027,0.11134669999592006,0.0005783999804407358,0.0004494000459089875,0.0003953000996261835,0.0004081000806763768,0.0003312000771984458,0.00032439990900456905,0.0068805000046268106,0.0005817000055685639,0.00045489997137337923,0.00044689991045743227,0.00037510006222873926,0.0003375000087544322,0.00033579999580979347,0.0003233000170439482,0.00032430002465844154,0.0003630999708548188,0.00042619998566806316,0.00038320000749081373,0.00033850001636892557,0.0003344999859109521,0.26095889997668564,0.0006422000005841255,0.0006767000304535031,0.00042729999404400587,0.0003394000232219696,0.0003974999999627471,0.00032620003912597895,0.0003247999120503664,0.000354300020262599]
```

Peer calls=338, maximum hold=0.287292600s, maximum peer wait=0.287887100s.

The isolated maximum hold/peer wait is0.286882700/0.287305200s. Consecutive-phase fairness maximum is0.287292600/0.287887100s across338 peer calls; every measured hold AND recorded wait is<=0.300s in both runs. The remaining margin is small and is NOT permission to waive the final real-builder benchmark. Total wall isolated0.406294-0.673602s, fairness0.397782-0.678716s. All prior one-hold and first-split failures remain above. The full receipts include acquisitions, per-phase labels, source hash and orphan counts in ignored ticket20_operator_evidence_spike-{isolated,fairness}.json; script adjacent. Tracked isolatedbce8bd2b and fairness148719f1 both exit0; both assert temp root removed and peer joined. Source hash remains1c69d2a89d37aafee3f8ea5dec4f1f892ec60592964d361b4e281556a9f8d2bf. No native/provider/network or final operator acceptance claim.

Reviewer pre-authorized fallback IF the real-builder publish hold or fairness later fails: split publication into enqueue and queued-mark boundaries. The queued mark must then no-op/refresh when a worker has already claimed and activated, never fail active->queued. Before relying on this fallback, root must add Event tests for claim-between-enqueue-and-mark and crash-between-them. This fallback was NOT needed, implemented or measured in the passing prototype; it does not silently change the primary five-phase design.

Required additional root gates for evidence: test_packet_evidence_is_invisible_to_other_thread_and_after_invocation; test_publication_evidence_mismatch_falls_back_to_full_packet_read (root/stat/scope/audit/absence each); test_same_size_mtime_packet_tamper_refused_before_generation; test_nonplan_enqueue_resume_and_recovery_keep_full_packet_validation. No evidence reuse on get_brief/get_delivery. Every mismatch preserves today's full-read outcome rather than inventing a new failure/refusal solely from a missing plan.

Required eventual root gate remains test_capped_source_snapshot_and_create_boundary_holds_with_peer_require_active. After mechanism clearance, freeze named phases explicitly: snapshot, reserve recheck+commit, publish+queued mark (and total wall time reported separately, never called one hold). Benchmark selected-channel AND run-projection modes, exact2097152 canonical bytes/1000 messages/id0/UnicodeCRLF, max512KiB parent,100 healthy prior lineages,10 samples per stated shape with normal owners/real fsync. Report all durations/acquisition waits/maxima/source hashes and prior metadata sizes; no discarded samples or IO exclusions. An Event-coordinated require_active peer must progress before/after each phase, with every actual hold AND peer wait <=0.300s, no deadlock. A full create total may exceed0.300s only if it releases the boundary between the documented phases; that is a proposed change to the original one-hold design, not a restated pass.

Separately test1001 messages/2097153 bytes no durable request/brief/enqueue, consistent capture under edit/delete/Stop, stale token/parent CAS races, prepared Stop in the stage-to-publish gap, crash at each phase, stage failure/orphans and stored replay never reading changed chat. Source cap does not promise every model can consume the context; existing wrapper refusals stay visible. These future tests/implementation remain blocked pending mechanism and exact payload review.

Reviewer-required root red-first gates for the split are explicit: test_stop_between_reserve_and_publish_cancels_prepared_without_dispatch (Event-interleaved actual Stop); test_crash_after_packet_stage_before_reserve_reports_orphan (no brief/request/queue); test_crash_after_reserve_before_brief_recovers and test_crash_after_brief_before_enqueue_recovers (existing prepared recovery); test_source_change_before_reserve_refuses_preview_stale; test_split_create_matches_prepare_request_stored_state (same audit, equivalent durable row/packet/brief/queue semantics); test_concurrent_same_request_create_has_one_winner_and_one_replay. Stage receipt created/reused/unknown-I/O accounting, foreign-root/stat tamper and all unchanged recovery/Stop suites remain required. These are planned tests, not executed prototype coverage. The accepted enqueue-evidence extension adds the strict negative authority tests named above before implementation acceptance.

## Exact operator interface freeze, PROPOSED for review before tests

The passing prototype makes the primary five-phase mechanism eligible for a concrete interface review; it does not clear these signatures or authorize tests/code. Names below are new in-package work unless explicitly existing. Public route/DTO key sets above remain exhaustive, with these corrections/completions: ExistingNotice=null|{id:Hex32,code:"admitted_from_recovered_result"}; ExistingWarning=null|"transport_unconfirmed"|"operator_recovery_required". ProducerLabel.adapter is cli|openai-compatible for saved work, and may be null ONLY for an unmanaged/unavailable picker/preview choice; absent verified requested model/reason is null/null on that choice. Timestamps use existing store POSITIVE finite numeric validation (source timestamp may be null); bool is never numeric. SourceRun.state_at_request is the actual stored nonblank UTF8 state string, never a client state. Scope kinds and other record schemas reuse the accepted store grammar.

### Pure source and generic read APIs

```text
MessageStore.snapshot_selected(channel, message_ids) -> {rows:DetachedMessage[],missing_ids:MessageId[]}
session_projection.event_projection(session, event) -> Projection
session_projection.continuation_projection(session, context) -> Projection
artifact_sources.normalize_intent(value) -> NormalizedIntent
artifact_sources.select_run_message_ids(session_snapshot) -> MessageId[]
artifact_sources.project_packet(intent, session_snapshot, message_rows) -> SourceCapture
artifact_sources.measure_packet(packet) -> PacketMeasurement
artifact_sources.preview_token(audit) -> Hex64
```

snapshot_selected is a generic read: validates channel/unique <=1000 safe ids; acquires MessageStore once, returns rows sorted by id and missing_ids sorted, with all mutable values detached; no callback/policy/session/manager/store entry from inside that lock, write or projection repair. Rows in another channel count as missing, never leak their contents. Caller obtains/releases SessionStore.get before this method. select_run_message_ids checks actual admitted/continuation links, duplicates/UID attribution and stops at1001 for a typed source limit; no200-row review helper or recent-N fallback.

Projection EXACT keys={uid,sender,type,text,metadata}, where metadata is the CURRENT projector's full constructed metadata, preserving existing chat bytes/behavior. The source builder compares the expected projection's required attribution/UID/type/sender/text to the captured row, then builds its narrower packet allowlist; it never copies full projector metadata. Extract pure helpers into NEW session_projection.py and call them from the existing SessionEngine projector as well as source validation, with unchanged-output goldens/tests. Helpers read no owners/files, emit no messages, and do not mutate session/event/context. Event projection includes the current exact footer rule; continuation uses the stored answer. Scope source selection and projection text validation stay separate from packet metadata projection.

NormalizedIntent has exactly the Intent keys above, with selected ids sorted and a detached parent; null/new lineage stays null until server audit derivation. No trimming of source/instruction/format. SourceCapture is PRIVATE {packet,scope,notices}; packet/scope are detached full accepted records, notices use the closed SourceNotice codes above. project_packet calls cap-aware measure_packet BEFORE existing full _packet_scope; its accepted output has exact complete canonical bytes/hash. PacketMeasurement EXACT keys={message_count,packet_bytes,measurement_complete,lower_bounds:{messages,packet_bytes}} with the nullable/exact/early-exit rules already specified. Over-limit paths raise ArtifactSourceLimit (an ArtifactOperatorError with reason source_too_large), carrying only this measurement and fixed limits, never a packet prefix.

Optional message provenance types: session_id positive safe int; run_id,event_id,question_event_id,seat_identity_id Hex32; input_revision Hex64; session_output bool; kind,provenance,submitted_by UTF8 strings. Attachment name,url,type,content_type,mime_type,encoding are UTF8 strings; size/byte_length nonnegative safe ints; sha256/content_sha256 Hex64. Optional invalid values and unknown keys are omitted, not coerced or recursively copied. Strings are NUL/surrogate-free and bounded by the total packet budget; optional empty strings remain data. No nested arbitrary value is accepted for these fields. Required message identity/text/type/timestamp must satisfy the accepted packet schema or source_unavailable is raised. Build the document candidate from its exact allowlisted keys plus the actual frozen input text before existing validate_document_snapshot; unknown authority keys are not copied even temporarily into the packet. Document errors refuse source_unavailable; no metadata guessed from a pathname.

### Store stage/reserve and publication evidence

```text
ArtifactStore.stage_packet(request_id, packet) -> _PreparedPacket
ArtifactStore.reserve_staged_request(audit, request_id, prepared) -> ExistingRequestRow
ArtifactStore._staged_packet_matches(prepared, audit) -> bool
ArtifactStore._staged_packet_orphans(prepared_or_error) -> {objects:int,bytes:int}|null
ArtifactService._operator_packet_evidence(audit, prepared) -> private contextmanager
ArtifactService._publish_operator_prepared(request_id, prepared) -> ExistingMutationResult
```

_PreparedPacket is an opaque frozen root-bound object constructed ONLY by stage_packet; private data includes canonical packet bytes/scope, deterministic packet/request id, root, observed file stamp and created_objects tuple as in import staging. No caller-controlled paths/callables or mutable dictionary is a plan. It is not serializable through a route, envelope or ledger. stage_packet validates/detaches/classifies under a short metadata lock first; an indexed id with conflicting scope/channel/source cannot be staged or overwritten. Release that lock before _put_bytes, fsync and stat. Unknown staging progress carries created_objects:null/reason staging_io_unconfirmed; reused/duplicate has empty receipt. Count only this call's currently unreferenced objects, with no body read/deletion. Existing same-id request detection is a replay/conflict before staging, not permission to attach a new packet. The already-accepted residual same-UUID reserve race is handled by final recheck, clean conflict and orphan reporting.

reserve_staged_request has the existing channel_write guard and runs inside the operator's reserve boundary after recapture/token comparison. It validates the full audit and staged scope/root/stat, current index, immutable replay identity, same-channel lineage, one-live slot and parent CAS; it may reuse staged packet data instead of _packet IO only for the validated plan. Whole _persist validation/default atomic_json remain. Foreign root/invalid plan => ArtifactValidationError; changed plan/file => full packet validation or ArtifactUnavailable, never unchecked reservation. Existing reserve_request, put_packet and prepare_request stay unchanged for all existing callers.

_operator_packet_evidence sets a PRIVATE ContextVar only around this invocation's pre-ledger publication validation and resets its token in finally. Evidence additionally binds the actual invocation/thread and full frozen audit; no child task/thread is spawned while set. _staged_packet_matches verifies root, stat, exact scope digest/length/all fields and audit agreement without a body read. In validate_enqueue only, a positive match replaces the final store.get_packet read; absence, mismatch, invalid stat or lookup failure takes the existing full packet read. Evidence lookup itself never converts failure into success. All live state/producer/channel/brief/envelope checks before this final read remain. Claim/admission/recovery/resume paths never consult the ContextVar, even on the originating thread; raw enqueue still refuses. Fallback must have byte-for-byte current full-read effects/results. Full-index validation remains mandatory.

_publish_operator_prepared re-reads the row under the boundary, verifies still prepared plus current binding/channel/head, establishes the private evidence context, invokes normal agents.trigger_identity_sync/coordinator authorization, and marks queued exactly as prepare_request does (including queued_behind_review). It does not regenerate a private brief, stage a packet or change a terminal request. Another invocation that already won publication is returned as a replay after immutable equality, never a second enqueue. The pre-authorized two-boundary enqueue/mark fallback remains dormant until a measured real gate failure and its additional red-first races; the primary interface here publishes/marks in one boundary.

### Operator service, HTTP binding and error payloads

```text
ArtifactOperator(*, authority, messages, sessions)
ArtifactOperator.producers(*, limit=20, offset=0) -> Page<ProducerChoice>
ArtifactOperator.sources(channel, *, session_id=None, limit=20, offset=0) -> Page<SourceChoice>
ArtifactOperator.preview(intent) -> Preview
ArtifactOperator.create(intent, *, preview_token, revision_lineage_id=None) -> Created
ArtifactOperator.library(*, channel=None, limit=20, offset=0) -> Page<LineageRow>
ArtifactOperator.lineage(lineage_id, *, version_limit=20, version_offset=0,
                         request_limit=20, request_offset=0) -> LineageDetail
ArtifactOperator.request(request_id) -> PublicMutation
ArtifactOperator.cancel(request_id) -> PublicMutation
ArtifactOperator.resume(request_id, *, recover_saved) -> PublicMutation
ArtifactOperator.source(request_id) -> SourceResponse
ArtifactOperator.version(lineage_id, version_id) -> VersionDetail
ArtifactOperator.download(lineage_id, version_id) -> Download
artifact_routes.create_router(get_operator_service) -> APIRouter
artifact_routes.error_body(reason, *, measurement=None, durability=None, staging=None) -> dict
```

Constructor verifies shared authority root/MessageStore/SessionStore/engine references, no cloned store/manager/registry. Actual app.configure constructs one artifact_operator_service from existing artifact_authority plus messages/sessions; None at startup maps operator_unavailable503. Configure binds it before serving; no new recovery worker or monitor. Both route registration and factory tests use this actual shared instance. Existing history/agent routes keep their auth and output shapes. Register the returned ordinary routes preserving .path enumeration; strict new prefix middleware is app code, not a router-only assumption.

Created is PRIVATE EXACT {mutation:PublicMutation,created:bool}; created:true means this call won NEW reservation and completed queued publication (HTTP202), false means immutable replay (HTTP200). On any incomplete new publication raise typed failure with guarded durability and staging, not created:true. Download is PRIVATE EXACT {content:bytes,sha256:Hex64,byte_length:int,filename:ASCIIString}; no filesystem path. Binder sets the fixed binary headers above after verifying len(content)/sha256 agree. All other successful endpoints return200 and exactly their earlier DTO. Requests are parsed manually with strict key/type checks, not Pydantic422 echo; empty queries on POST; GET body byte cap0, POST cap262144, query8192, JSON nesting depth32 (root depth1), duplicate/nonfinite/lone-surrogate refusal. Non-JSON POST media type400, POST raw body over262144 bytes413 artifact_request_too_large without source measurement fields, malformed query/path400, unknown valid id404. Header names/media-type tokens are case-insensitive; no extra Content-Type parameters except charset=utf-8. Root wire tests assert tokens/seals/launch refs/source sentinels never appear in logs or exception bodies. No async await while any owner lock is held; handlers use to_thread for complete synchronous operations.

Replay derives the normalized source selector from STORED audit only: kind, sorted message_ref ids for selected mode (run mode requires submitted message_ids=[]), session_id from source_run or null; checks request/producer identity, original channel, instruction/format, expected_parent and endpoint lineage semantics against the audit and reconstructs its token without created_at. It never reads current chat/seat/parent objects or repairs a missing queue. New-route lineage:null matches only the derived lineage id with null parent; revision path/body must match the stored lineage. Imported request ids cannot be reused to create. Request read/normal replay may inspect only queue metadata for needs_resume. A queue lookup failure is storage_unavailable, not assumed absent.

ArtifactOperatorError has a CLOSED service reason enum: request_unknown,request_read_only,producer_unavailable,parent_changed,source_unavailable,preview_stale,channel_mismatch,request_conflict,request_pending,channel_unavailable,source_too_large,object_unavailable,storage_unavailable,operator_unavailable. It exposes no free-text message as a wire. error_body maps the fixed earlier status/code/text table; request_unknown maps artifact_not_found. Binder-only invalid_request/operator_required/method_not_allowed/request_too_large are fixed entries in the same table. No matching exception strings, field-name guessing or arbitrary status. SourceLimit is the one subtype carrying the bounded measurement DTO.

Base error EXACT {code,error}. Allowed additions by circumstance ONLY: producer refusal adds reason:CapabilityReason; source_too_large adds limits/measurement fields as specified; a post-stage/write failure adds request_id:Hex32,durability:"recorded"|"not_recorded"|"unknown",request:PublicRequest|null and staging:{orphans:{objects:int,bytes:int}|null,reason:null|"staging_io_unconfirmed"|"inventory_unavailable"}. Guarded lookup returns recorded only on an observed matching row, not_recorded only on a healthy observed absence; any failed lookup returns unknown/request:null. Never drop an already known durable effect, call an orphan a created request or report zero when staging/inventory is uncertain. No private receipt ids/paths/launch refs enter staging. Pre-effect syntax/auth errors carry none of these additions. Cancel/resume transport partials remain PublicMutation200 as the accepted core returns, without claiming transport_settled:true.

### Helper boundary after review

Existing helper may own ONLY NEW tests/test_artifact_routes.py, at most12 methods. Root owns builder/packet golden/leak, lock/Stop/Event/concurrent-create/crash/evidence-fallback/races, exact middleware prefix/Host/Origin/body limits/factory enumeration, staged store negative tests and final real K6 benchmark. Helper uses real temp shared owners and the earlier labeled in-process supported managed fixture; no live process/provider, app-global seam outside scoped cleanup, renderer or benchmark claim. First helper2: actual operator route bearer refusal with no source/index/queue effects; exact preview->create/replay/download Unicode/CRLF bytes through real service and middleware. Capture infrastructure missing-method reds separately and observe behavioral red before implementation.

The remaining <=10 helper groups may cover typed unknown-vs-conflict; source selection/edit staleness; production-empty create refusal; parent/pending/imported revision/channel CAS; stored replay after producer/source change and missing transport needs_resume; terminal cancel/resume/lost-ACK semantics; library/provenance projection detachment; count/byte caps and exact download headers; read-only corrupt-object isolation; and every public DTO authority sentinel. Freeze the final named12 with the reviewer before briefing, do not edit frozen prior helper files. All later browser/native/API-fake/reader/activation gates remain separate. No operator tests or production implementation yet.


## Execution/acceptance split

After contract AND staged-mechanism review plus a passable timing prototype, freeze exact builder/operator service/helper signatures, the remaining nested type/literal bounds, error/body bounds and idempotent intent reconstruction rules. Public DTO key sets above are proposed for this review and cannot widen silently. Only then brief the existing helper (one NEW tests/test_artifact_routes.py, <=12 methods). Root owns snapshot consistency/allowlist/golden/K6/concurrency/replay/crash tests and actual middleware/factory enumeration. Initial infrastructure reds are labeled; observe actual behavioral auth/creation refusals before fixing.

Required checks: every route's real operator middleware denial for bearer/query/duplicate/ambiguous auth, no-store fixed errors; unsupported producer and production-empty no-enqueue; malformed/extra/duplicate/oversize JSON/query/path cases; exact preview bytes/refs/replay; source channel/run/parent edits and Stop boundary; imported/dead-producer reads and new-local revision; partial-write durability with fresh reload; library detached pages; source object corruption scope; binary download Unicode/CRLF/SHA/header/filename; both shared app bindings; unchanged artifact/lifecycle/runtime/queue/review/Stop suites. Full configured discovery and independent source review are separate evidence. No product operator-route tests/code exist for this draft yet; the explicitly requested ignored design spikes measured existing components and a private script-local phase/plan prototype; production source is unchanged.

Deferred ONLY to reader package: request/revision modal and source picker UX, Markdown node rendering/hostile HTML/link/image policies, visible imported/model/source labels, source tab/bidi warnings, authenticated fetch-to-blob download UI/hash check (no credential URLs), attachment URL/name text-only rendering and rendered layout. This package supplies authenticated data/bytes, not an unsafe interim HTML preview. Deferred acceptance harnesses: native CLI fake client/real MCP, API local fake responder and rendered browser under Ticket19 isolation/nonce/cleanup guards, then the SEPARATE activation commit and final whole-ticket review. No ordinary chat or model-produced declaration can enable authoring.
