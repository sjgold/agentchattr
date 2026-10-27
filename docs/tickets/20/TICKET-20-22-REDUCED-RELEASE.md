# Reduced release: tickets 20-22, then multi-file 23

Status: backend/UI components accepted; partial browser evidence retained. Seth has dropped phone-width checks, new numeric speed screening and further browser-harness work. Ticket21 then22 are next; activation is separately reviewed, desktop look optional, final cleanup required. No push.

## Latest scope decision, 2026-10-26

Seth's words, relayed verbatim by the reviewer: "id never needed phone width this is an internal only tool... speed is open as well as long as agents are not taking forever it should be fine".

This supersedes the earlier phone-width, numeric responsiveness-screen and pre-activation visual requirements. Drop the390px/mobile gate, all new numeric speed gates and tools/screen_artifact_release.py (never created). No more browser-harness work or measurement campaign. Existing correctness/security/provenance/idempotency/Stop/durability and regression tests stay. Speed is the stated practical requirement that agents are not taking forever. Browser evidence remains partial and its receipts remain false/incomplete; no visual acceptance is invented. A desktop look by Seth is optional, not a blocker.

Next order: Ticket21 transcript ->22 packaging -> separate activation commit for reviewer -> final approved file cleanup -> publication only with Seth's explicit push authorization. No deletion without his explicit yes. Historical timings, attempt records and superseded proposals remain as history; their old gates no longer apply to this release.

## Authority and priority

Seth's exact answer on2026-10-26, after the reduced20-22 / separate23 / separate24-26 proposal:

> 20-22 yes 23 separate 24-26 sperate multi file is more impiortant to me than automatic synthisis

He then instructed:

> update status and docs please

This supersedes the earlier instruction to complete R3 before operator routes, the proposed full operator UI and strict worst-case performance acceptance for this first release. Reviewer acknowledged the relay and retained safety requirements. This is a scope change, not evidence that unimplemented work has passed. Original issue bodies remain historical scope; no issues have been closed or edited by this documentation update.

|Milestone|User outcome|Scope|
|---|---|---|
|20, reduced|Request a document from the current session, read it safely and download exact Markdown|Manual request, one default author/source, simple status/result card. Reuse the accepted backend.|
|21, reduced|Download the actual current-session conversation in order|Plain transcript with essential message/seat/time/phase provenance and incomplete markers. Accepted contributions by default; no advanced abandoned-attempt selector or combined synthesis layout.|
|22|Usable everyday release|Integrate20/21, verify supported workflow, package launcher/shortcuts and document recovery/limits. Fix reproduced integration defects. No new feature campaign.|
|23, separate NEXT|Select multiple files for one review packet|Higher priority to Seth than automatic synthesis. Separate scope/review after20-22; retain file identity/limits/revisions.|
|24-26, separate LATER|Independent API first passes, quote checks and findings-aware synthesis|Separate follow-up package, after23 unless Seth changes order. These features do not block22.|

A requested document may be a report, recommendations or any user-requested Markdown. No automatic synthesis phase is added to20/21. The app does not generate documents on every session automatically.

## First usable document flow (20)

1. In the current session, choose Request document, enter the instruction and see the default author name and a concise source statement.
2. Submit once. Save one immutable request through the accepted service/queue authority. Show queued/working/ready/failed or unavailable based on actual state; do not imply worker exit or repair completion.
3. Show the completed document in a safe reader with its author/model honesty, source run and creation time. Download the same UTF8 Markdown bytes, including existing BOM/CRLF behavior. Keep earlier records in storage.
4. Reloading the page can recover the card through a request-status read. A duplicate submit uses the same request id and returns the stored attempt; a changed intent with that id conflicts.

Deferred UI/API work: preview/token roundtrip; selectable source-message and producer pickers; revisions/history browser; imported-head revision creation; advanced resume/repair dashboard; full source inspector; cross-channel document library. Existing accepted revision/recovery/archive/cancel backend code remains intact. None of it is removed to manufacture a smaller test count. An explicit source summary and readable refusal remain required.

### Proposed defaults and exact create intent

Existing sessions store frozen design_snapshot.roles and current participant_bindings. NEW pure selection seam: resolve_default_artifact_author(session, authority) returns ONLY an identity_id string or raises ArtifactOperatorError with code/cause/author_name/examined_roles. The service builds the audit producer block through its existing prepare_request/_producer/launch_provenance path; no duplicate producer derivation. Outside the engine/catalog boundary, iterate design_snapshot.roles IN ORDER, skip bindings whose kind is human/family or has no agent identity_id, and resolve each agent binding by identity_id against the LIVE registry. Never select by cast name or by an arbitrary available seat. Require a unique live identity match and current seats.artifact_producer eligibility. Select the first eligible role in that order; current participant_bindings rewrites from replacement are authoritative at save time. Capture the selected identity; the service derives and freezes its producer audit through the existing path. A candidate with duplicate active identity matches has cause ambiguous and is never selected. Other bound role candidates can still be examined in frozen order.

If no eligible agent resolves: no agent bindings -> no_agent_role; agent bindings but no matching live instance -> no_live_instance; otherwise preserve the first candidate's mapped cause, including unmanaged/binding_changed/ambiguous/runtime_unverified. When the global capability is empty, cause=capability_off and text is exactly "Artifact authoring is not enabled." No launch/restart, unsupported-client fallback or new producer selection UI. Public card/refusal shows the resolved registry name when known, otherwise author_name=null and a fixed explanation. The name is informational; identity_id is the authority. Use a small shared active_artifact_instance(registry, identity_id) helper with the existing ArtifactService._instance rule (exactly one active match); no unique-by-identity registry API currently exists. Check runtime_protocol.SUPPORTED_CAPABILITIES FIRST, before manager I/O. artifact_producer reason mapping is EXACT: artifact_capability_missing->not_supported; unmanaged_producer->unmanaged; producer_unavailable->no_live_instance; capability_binding_changed->binding_changed; runtime_unverified->runtime_unverified. capability_off is the global flag cause, not an artifact_producer reason. The examined_roles count includes every agent candidate inspected, and the FIRST candidate cause is reported if no candidate succeeds. Resolver manager I/O stays outside the engine/catalog boundary. This is NEW resolver implementation, not an existing seam. Before submit, the UI can say "Author selected from this session"; the resolved author name appears on the saved card or refusal, avoiding a new preview API.
Proposed POST /api/artifacts/requests body is EXACT:

    {request_id: Hex32, channel: ChannelName, session_id: positive bounded int,
     run_id: Hex32, instruction: nonblank UTF8 text <=32768 bytes}

No preview_token, producer claim, message_ids, model, capability, parent or lineage fields. Unknown fields refuse. Channel/session/run must match the real session selected in the UI; the client identifiers grant no authority. Format is server-fixed Markdown. A new independent document has no parent; deterministic request-derived IDs and one-live-slot rules remain. No revision endpoint is part of this release.

Default source: run_accepted_messages from that exact same-channel session/run, including its frozen input snapshot and the admitted-event/operator-continuation projections available when the server saves the request. Exclude unrelated chat, quarantined/unadmitted/abandoned outputs and unlinked human discussion. Existing projection identity/attribution/text checks and source allowlists stay mandatory. No hidden recent-N window, truncation or reconstructed missing message. If no accepted contributions exist, refuse clearly instead of silently making an instruction-only request. Preserve2MiB/1000-message packet and512KiB Markdown bounds; these are existing per-object bounds, not a new installation quota.

The UI says that the source is captured when the request is saved. No preview freshness promise exists because the preview flow is deferred. Capture a detached source and resolve the producer outside engine/catalog, then briefly recheck current session/run/binding before the existing prepare_request boundary. Before source capture, author resolution or prepare_request, same-ID replay reads the stored request and compares ONLY {request_id, channel, session_id, run_id, instruction, format, requester}, with format=Markdown and requester=operator. Return the stored projection without prepare_request or fresh source/producer work. A producer relaunch changes launch_nonce/fingerprint but must not invalidate an identical replay; prepare_request audit equality is NOT the replay implementation. Different intent with the same request_id is409 request_conflict; imported and terminal records remain read-only and replay200 when the immutable reduced intent matches; a changed intent conflicts. Request body identity is exactly channel/session/run/instruction plus request_id; derived fixed format/empty parent cannot vary. Reject cross-channel IDs and unsupported identity before writes.

Refusal presentation: a fixed readable reason, no private nonce/seal/token/config/path/body echo. Unavailable author: show its name and that a supported managed instance is required, with no automatic launch. Missing/changed source: state that the current session source could not be captured and no new request was saved. Oversize: state the existing per-object bound and no truncation. Partial durability: retain the accepted recorded/not_recorded/unknown distinction and request id, then show the status refresh action; never invite a new-id blind retry when prior durability is unknown. Exact error DTO/status mapping is the next bounded route freeze, reusing cleared families.

Minimum operator surface and normative response policy are frozen below. These routes/security/snapshot helpers do not exist yet and are in-scope NEW work. The earlier complete operator contract is historical, so this document restates every retained rule needed for this reduced surface.

### Consistent source capture is in scope (E4)

NEW MessageStore.snapshot_selected(channel, message_ids) validates unique nonnegative IDs, takes its non-reentrant threading.Lock ONCE and calls no other locking MessageStore method and returns detached complete rows for exactly that channel/ID set, or typed MessageSnapshotUnavailable(ValueError) with no partial list; source capture maps it to ArtifactSourceError(source_unavailable). Existing get_recent/get_since return mutable row aliases; repeated get_snapshot reads are not a consistent batch. The store helper has no artifact imports, callbacks or seat authority.

NEW capture_artifact_session_source(session_id, run_id, channel) runs OUTSIDE the engine/catalog boundary: obtain one detached SessionStore.get session; verify exact session/run/channel; derive projection IDs from admitted_events and continuation_context; reject missing/duplicate links; obtain exactly one snapshot_selected batch; validate expected UID (session-event:<event_id> or session-input:<question_event_id>), attribution, metadata identities and exact projected text against the trusted event/continuation, including the footer keyed by that message's own session_output metadata, not the current session state; derive phase/turn from turn_id plus frozen design_snapshot.phases; sort by stored message id. Extract a shared pure expected-projection-text helper from the existing projector so this does not duplicate its formatting rules. Source text is read once from the detached batch, never refetched while encoding. Validate the allowlisted packet with existing _packet_scope and existing2MiB/1000 limits. No projection repair/model call/hidden fallback. Typed source_unavailable or source_too_large refuses before reservation. Keep original frozen input/revision/document. All source allowlists protect config/nonce/seal/fingerprint/token/path fields while retaining literal user text. Snapshot consistency/projector integration is substantive NEW work in the smaller release, not assumed to be a tiny existing API.

### Minimum routes, completion discovery and card actions

|Method/path|Exact purpose|
|---|---|
|POST /api/artifacts/requests|Exact create body above;202 only for new recorded+queued success,200 for identical stored replay.|
|GET /api/artifacts/requests/{request_id}|Global operator read with no channel query; boundary-protected public status/author/source summary, including terminal and needs_resume state; no full audit/seal/launch secrets.|
|POST /api/artifacts/requests/{request_id}/cancel|Body EXACT empty object. Pre-read under boundary, unknown404, validate stored channel ownership then existing cancel_request; current state/transport warning returned.|
|GET /api/artifacts/requests/{request_id}/document|Resolve the known request to completed document, or409 not_ready.|
|GET /api/artifacts/versions/{version_id}|Completed Markdown plus safe metadata; plaintext reader consumes markdown via textContent.|
|GET /api/artifacts/versions/{version_id}/download|Exact saved UTF8 bytes, authenticated download.|
|GET /api/artifacts/sessions?channel=<name>&offset=<int>|Bounded same-channel session summaries from SessionStore.list_all(channel), started_at DESCENDING then id DESCENDING, max20. title is template_name, otherwise goal truncated to256 UTF8 bytes with a truncation indicator; invalid/unknown channel is400 invalid_request. Includes completed sessions; not get_active. Shows session/run/state/title, no bindings/secrets/source text. offset defaults0, nonnegative bounded int; page size fixed20. Response EXACT {sessions:[{session_id,run_id,title,state,started_at,source_so_far,title_truncated}],offset,has_more}. A More control pages20 at a time.|

Create permits a matching complete session as well as a current run in active/waiting/paused/awaiting_input/stalled/retrying/interrupted states with actual accepted events and no stop/replacement fence. Prepared/no-events and stopping/stopped/unresolved runs are source_unavailable for new create; no hidden instruction-only fallback. source_so_far is state != complete. UI retains a Request document action on the completed session card and can recover that card from the bounded session summaries after reload. Mid-run cards say "Source so far". The session list chooses the run, not arbitrary source messages/another producer; the deferred source picker stays deferred. Archived/inactive channel new create refuses; retained reads remain available. Poll known request IDs; no global artifact catalog is added.

Minimal Cancel is INCLUDED. It invokes the already accepted authority/fence path; cancellation state is durable before fence effects. Show cancelled with an explicit transport-unconfirmed warning where applicable, never worker-exit proof. Existing source Stop behavior remains. Cancellation of a terminal race returns its typed conflict/current status and refreshes. Cancellation/Stop bypass the new capability gate where the accepted cancellation path does. This prevents a stuck live document from being trapped behind the deferred resume dashboard; unreadable storage can still hold cancellation and channel management honestly.

### NEW strict operator security branch (E3)

Implement the prefix branch for path == '/api/artifacts' or path.startswith('/api/artifacts/'), including unmatched routes, before legacy token fallback. It must not collide with /api/artifact-* agent namespaces. The existing middleware does not supply this security. Order: validate raw headers/auth/Origin/Host, then explicit route+method matching (authenticated404 for unknown path,405 for known path/wrong method), then media/size/JSON/body shape, then route semantics. Scoped prefix422/500 handlers emit the fixed envelope with safety headers; no global handler changes. Require exactly one nonempty X-Session-Token matching configured token, no Authorization header, no query parameter named token (even alongside valid header), no cookie/URL auth fallback; reject duplicate auth/Origin/Host headers. Set request.state.auth_origin=operator, require it at binder. Seat bearer access refuses403.

Origin is REQUIRED for POST. GET/HEAD accept an absent Origin or an allowed exact value; a supplied value must equal configured http://localhost:<port>, http://127.0.0.1:<port> or http://[::1]:<port>. Host must be one of the corresponding literal loopback hosts with configured port (case-insensitive hostname, omitted port only at80); no credentials, suffix matching or forwarded-host trust. Fake/non-browser POST clients send the same explicit allowed Origin. Token comparison is constant-time. Other existing namespaces retain their compatibility behavior. Reject bad origin/host before route work.

Every prefix response, including403/404/405/validation/download, has Cache-Control:no-store and X-Content-Type-Options:nosniff. Unsupported method405, unmatched path404, framework422 mapped to400 invalid_request. POST Content-Type exactly application/json plus optional charset=utf-8, otherwise400. Body <=256KiB, bounded max+1 read before parsing; valid UTF8, reject duplicate JSON fields/nonfinite values/unknown keys/wrong types. Instruction uses existing _index_text with32768 UTF8 byte limit/HT-LF-CR policy; no trimming/normalization. Enforce exact ID/count grammar. Process blocking owner/JSON work through asyncio.to_thread; no await under locks and no model call from HTTP handler.

Download Content-Disposition is fixed ASCII attachment; filename="document.md" (transcript uses "transcript.md"). Use text/markdown; charset=utf-8 plus nosniff, never text/html. Browser uses authenticated fetch with X-Session-Token, then blob/object URL, revoke after use; no credentials in query/filename/log. Read response markdown is JSON text only; client assigns textContent to a wrapping pre-style block (overflow-wrap:anywhere, keyboard-copy and download). No Markdown-to-HTML renderer in first release; rendering is deferred. Script/img/link/javascript:/data:/entity strings display literally; exact original bytes are asserted on download.

### Reduced error and public state contract (E5)

Public error envelope EXACT {code, error, cause, author_name, examined_roles, request_id, durability, request}; nullable fields are null, not omitted. examined_roles is a nonnegative int on no_author_available, null otherwise. Non-author errors have cause=null and author_name=null; their code is the fixed typed discriminator. code/error/cause are fixed reviewed literals, never str(exception). durability is recorded/not_recorded/unknown/null. request is the detached RequestSummary below or null, using an allowlist. Syntax/auth failures do not echo submitted text. Partial-effect lookup failure gives unknown; it never erases the durable request or authorizes a blind new-id retry.

|Code|HTTP|Meaning|
|---|---|---|
|invalid_request|400|Bad header/media/JSON/field/syntax; no new reservation.|
|operator_forbidden|403|Operator token/Origin/Host/duplicate auth failure.|
|method_not_allowed|405|Authenticated valid-prefix request uses unsupported method.|
|request_conflict|409|Same ID changed intent or a cancelled/terminal mutation race. New-lineage create has no independently reachable live-slot/head conflict after stored-ID handling.|
|session_unknown / run_unknown|404|No such stored session, or no matching retained run.|
|channel_mismatch|409|Session/run/request belongs to a different channel.|
|channel_inactive|409|New authoring forbidden in current channel state.|
|no_author_available|409|cause no_agent_role/no_live_instance/not_supported/unmanaged/runtime_unverified/binding_changed/ambiguous.|
|no_author_available|409|cause capability_off; exact text "Artifact authoring is not enabled."|
|source_unavailable|409|Empty accepted source or missing/changed projection, no partial packet.|
|source_too_large|413|Existing2MiB/1000 packet cap, no truncation.|
|request_too_large|413|HTTP256KiB body or instruction32768-byte cap.|
|transcript_too_large|413|Transcript export cap below, no partial download.|
|storage_unavailable|503|Held/malformed/unreadable owner/object, durability reported honestly.|
|boundary_held|503|Typed internal boundary guard refused; fixed public text.|
|not_found|404|Unknown request/version or unmatched prefix path.|
|not_ready|409|GET /api/artifacts/requests/{request_id}/document for a known request with no completed version.|
|unexpected_failure|500|Scoped fixed operation-failed envelope; no exception echo.|

No capacity refusal is invented: no installation quota is enabled. A real existing object/byte cap uses its specific size refusal above. Preserve other accepted agent/service transport errors outside this operator namespace; this table maps only reduced operator operations.

RequestSummary EXACT {request_id,channel,state,reason,label,author_name,created_at,updated_at,version_id,source,needs_resume,warning}. source EXACT {session_id,run_id,message_count,packet_bytes,scope_sha256,input_revision,source_so_far}; no copied refs/body/launch fields. warning is null or an accepted fixed transport/recovery warning. label is exactly queued/working/ready/failed/unavailable. Mutation response EXACT {request:RequestSummary,durability,transport_settled}; no producer credentials or full _projection dump.

|Stored state / condition|Label and card text|
|---|---|
|prepared / queued with a real queue record|queued; "Queued".|
|active|working; "Writing document".|
|fulfilled|ready; "Ready" denotes recorded completion; document reads/downloads still verify bytes and may report storage unavailable.|
|imported with version / without version|ready / failed; "Imported history", never needs_resume or new authoring.|
|failed|failed; "Document could not be completed"; stored closed reason remains available.|
|cancelled, reason operator_cancelled|failed; "Cancelled" plus unconfirmed-fence warning if applicable.|
|cancelled/source_stopped or stopped-source cancellation|failed; "Stopped".|
|quarantined|failed; "Response rejected" (no raw retained body shown).|
|live row with absent queue/needs_resume|unavailable; "Needs recovery" with existing channel-management/repair guidance, not automatic retry.|
|storage/refusal/poll unavailable|unavailable; preserve last known state visibly; no fabricated terminal result.|

operator_cancelled is a reason, not another store state. needs_resume is a projection over a live row, not a persisted state. Poll every2s while known live; after request failure back off to4/8/16/30s maximum, retain last known state and show connection/storage unavailable; successful poll resets2s. Stop automatic polling at fulfilled/failed/cancelled/quarantined. Explicit Refresh remains. If a later document read fails verification, show unavailable instead of displaying unverified text. A queued/active stale card can still offer Cancel; advanced resume is deferred. Cancel/retry outcome never hides a partially durable effect.

## Transcript export (21), explicit NEW route

NEW GET /api/artifacts/sessions/{session_id}/transcript?channel=<name>&run_id=<Hex32> in the SAME strict security prefix, authenticated fetch+blob download. Session/run/channel must match; current or completed sessions allowed. No transcript implementation exists today. Reuse the source snapshot/projection validation, but transcript has its own export byte cap rather than silently applying the2MiB packet cap. It reads actual stored accepted/admitted-event and linked operator-continuation messages, in accepted admission order, preserving the journaled event/continuation sequence. IDs remain displayed provenance, not the ordering authority. Include skipped-turn events as explicit markers without invented message text. No model synthesis or invented text.

UTF8 Markdown output has a fixed session/run/source-scope header, then each message's id, sender/seat, recorded timestamp (explicit unknown when null), phase/turn labels from matching trusted event metadata, and exact text. Attachments get a fixed "Attachment present; content not exported" marker, not local paths/URLs/secret metadata. Incomplete/current/stopped/skipped contribution flags are explicit header/phase markers. Superseded/abandoned/quarantined content is excluded by default with an omission disclosure, no advanced inclusion selector. Missing/edited projections refuse source_unavailable rather than reconstructing them from journal text. Preserve exact message text/Unicode/CRLF within the deterministic Markdown container; HTML is never served.

Proposed export cap8MiB UTF8 output, checked during bounded assembly before returning bytes, no truncation or partial download. This is a per-export safety bound for review, not an installation quota or a1000-character document limit. It does not change backup ZIP schema/budgets: transcript download is a separate convenience export, ZIP backup remains the retained full history/objects path. Only reproduce/fix actual backup integration defects; no backup redesign.

## Acceptance and what stays protected

Unchanged: authorization and secret protection; no cross-channel scope; exact source/provenance and model honesty; immutable Markdown; request/attempt/dispatch ownership; replay/idempotency; durable ordering and partial-effect honesty; stale-result refusal; cancellation/source Stop fencing; held/corrupt storage behavior; diagnostics privacy; no accidental model calls. Existing accepted R1/A1/R2+D4 code and discriminating tests remain. UI accessibility, keyboard operation and safe rendering remain required. Production artifact capability remains empty until the separately reviewed activation commit.

Changed: first-release acceptance no longer requires every storage/shared-boundary operation at all maximum populations to stay<=0.270s with20percent margin. The withdrawn128-request/512KiB installation quota remains withdrawn. No R3, new schema, migration tool, capacity reservation or R4 is included in20-22. Accepted4MiB import tests and existing limits remain regression checks, not a reason to start a fresh unrelated benchmark campaign for each docs/test edit.

### Speed requirement, superseding the proposed numeric screen

Seth accepts practical speed as long as agents are not taking forever. No new numeric screen, screen tool, threshold, retained-row timing campaign or class-repeat campaign will be built. Existing regression tests stay. Earlier measured values remain historical observations, not new acceptance promises.

## Finite capacity and evidence disclosure

Without R3, full source refs remain duplicated in request/version index metadata. The historical sizing probe measured293110 bytes for one fulfilled max-source request; it is not a product quota or a current per-request constant. More requests/versions and larger sources increase validation/write cost. No purge exists; deletion/export retains authored history. No replacement installation quota is chosen or implied.

Accepted evidence remains scoped: final max-source service A phases were roughly0.16-0.18s on this machine; final4MiB import full/held/peer maxima were approximately0.20-0.21s. The complete D4 final190 run passed with a stall sentinel. Earlier real misses, roughly1.1s unattributed stalls and instrument-invalid attempts remain in TICKET-20-D4-FINAL-GATE.md. These facts do not establish unlimited capacity or guarantee future tail latency.

## Current verification boundary and next work

This amendment changes documentation only. R2+D4 is independently FINAL ACCEPTED at220f3400: reviewer170 focused OK47.5s; builder437 artifact and1817 full (4 skips) pass;17 mutants assertion-killed; prior gate190 retained. No reduced operator/UI/transcript code has been implemented or accepted by this edit. Old R3 sidecar proposal196666c and reviewer no-sidecar/no-conversion ruling are preserved as historical/deferred material, not an active red-work instruction.

Next order after independent docs clearance: Ticket20 backend reds (resolver/snapshot/create-replay/status/read/download/cancel/middleware), then UI/plaintext reader, then Ticket21 transcript, then Ticket22 packaging. Relevant safety regressions and one final full discovery on the frozen integrated product, with rendered acceptance, remain required. Stop on a real screen miss and report it; no resampling campaign. Reviewer decides disposition on retained numbers. Review the activation commit last before publication. No new agent creation, provider spend, external issue edit, deploy, activation or push is authorized by this documentation request.

## Activation and the release22 finish line (E9)

With SUPPORTED_CAPABILITIES empty, EVERY new production create is refused with no_author_available/capability_off. Other accepted read/cancel/replay safety semantics remain. Development acceptance uses the existing in-process fixture-patched capability only: managed local fake CLI with the real MCP artifact tool, API local fake responder/outbox/admission, and rendered browser in Ticket19-style isolated sessions. Label these honestly; no live provider/model spend, installed-client compatibility, Omarchy or Desktop mutation is inferred.

Release22 is not called usable while the capability is disabled. After the frozen20/21 flow and packaging pass, prepare a separate ACTIVATION commit containing the reviewed capability allowlist and actual wrapper support/wiring, with explicit fail-closed unsupported-client checks. Independent reviewer must clear that commit and its end-to-end fake acceptance before shipping. No activation is done by these docs; git push remains held until Seth explicitly authorizes it.

## Reduced specification acceptance (E12)

DA-2 / artifact AT-12 for20-22: explicitly request current/completed session document with default bound author, preserve provenance/attempt safety and immutable records, read escaped Markdown text, download exact .md, expose status and minimal Cancel. Revision browser, producer/source picker and advanced resume UI are deferred.

DA-3 / transcript AT-12 for20-22: download accepted stored messages in actual admission order with phase/seat/time/message provenance and incomplete/omission markers. Explicit abandoned-attempt inclusion, combined synthesis layout and automatic synthesis are deferred. Backup ZIP preservation remains. Transcript and first document together are exercised through the real operator HTTP/browser flow with fake managed adapters.

R3, new schema/sidecar/converter/capacity policy, multi-file23 and automatic24-26 remain outside this implementation package.23 is the next milestone and outranks24-26 per Seth. This E1-E12 freeze clarifies NEW work honestly; it does not claim those helpers or security checks already exist.

## C1-C11 corrections and backend red interfaces

Stored status/replay and immutable intent comparison occur inside the shared boundary. NEW ArtifactService.request_status(request_id) returns None for unknown, otherwise EXACT {request:detached existing _projection(row),needs_resume:bool} using the real queue record; prepared with NO record is Needs recovery, not Queued. Terminal/imported never need resume. ArtifactOperator maps this internal read to RequestSummary by a closed allowlist; it never forwards the private row. Cancel pre-read and service action are serialized; a post-durable fence exception returns durability=recorded and current summary/warning. Unknown cancel ID is404; conflicts include current summary where readable. The operator is global, so request-id reads/cancel have no supplied channel to trust; validate the stored request/lineage channel relationship through existing owner checks, never infer a caller channel. Unreadable versions are503, not404/not_ready.

Version response EXACT {version,markdown}; version is an allowlist of id,lineage_id,sequence,channel,request_id,sha256,byte_length,created_at,author_name,requested_model,confirmed_model,confirmation_reason,source_run. All nested source_run keys are only session_id,run_id,input_revision,state_at_request. Null model fields retain existing honest reasons. No launch_nonce/fingerprint/launch_attempt/seal/private producer object is returned. Download remains exact bytes and fixed headers.

Capture (session/message snapshot, packet projection/validation and put_packet) and resolver I/O stay OUTSIDE engine/catalog. Only the existing prepare_request authority/persistence path runs inside. The2.0s screen is total create wall time excluding model generation;1.0s applies to prepare_request holds/peers. If the harness cannot split them, BOTH limits are1.0s. Before prepare, re-read current session/run/binding under the boundary; if Stop/replacement won during capture, refuse before reservation. A staged immutable packet may remain orphaned after a later typed refusal; it is retained and reported, never deleted or falsely referenced. This is the accepted packet-orphan seam, not rollback atomicity.

Packet envelope EXACT {version:1,channel,scope_kind,source_run,input,messages}. source_run is null or exact {session_id,run_id,input_revision,state_at_request}; input is null or {text,input_revision,source_document}. Messages exact {id,uid,sender,type,timestamp,text,attachments,provenance}. Use exact captured text and R1 numeric/UID/source-run validation. Missing legacy UID becomes legacy:<id>, with real collision refused, never renamed. Timestamp is stored value or null. Message provenance allowlist: session_id,run_id,event_id,question_event_id,kind,provenance,submitted_by,seat_identity_id,input_revision,session_output. Attachment allowlist: name,url,type,content_type,mime_type,size,byte_length,sha256,content_sha256,encoding with valid primitive types; never paths/tokens/config/nested server metadata. URLs remain unfetched source text. DocumentDescriptor reuses document_inputs validated version,kind,source_id,name,encoding,byte_length,content_sha256 metadata and verifies it against frozen input, no locator guessing.

NEW check_packet_bounds(packet) performs count-aware<=1000 and cap-aware canonical UTF8 size<=2097152 precheck (stop at1001 /2097153, including JSON escaping) BEFORE full _packet_scope walk. It raises ArtifactSourceError with typed code source_too_large or source_unavailable; no parsing validation exception text. NEW project_artifact_message(row) produces the exact allowlisted message above. Use canonical_utf8 and store._packet_scope for final validated hashes. Literal source text containing token/path words is retained. The bounded encoder must be equivalent on valid strings/escapes/numbers; no partial source prefix or silent truncation is returned.

Production Stop wiring: engine.stop_session durably stops the run, then explicitly requests artifact source fencing once. Historical run reconciliation cancels ordinary review transport only. A separate bounded, rotating retained-artifact pass examines at most100 requests per reconciliation (not per historical run), cancels live-source requests whose exact source run is stopped, and repairs their fences. Post-run snapshots remain independent. ArtifactUnavailable/OSError from the artifact owner is contained: ordinary review claims and other session Stop outcomes continue. Artifact cancellation is reported separately through artifact_cancellation {warning,unconfirmed_dispatch_ids} on Stop/status; artifact records do not enter review cancellation_receipts, stopping/unresolved state or termination offers. The report is observational process-local state, not proof of worker exit; storage_unavailable without known IDs means effects unknown. Persisted request/transport state remains recovery authority. Ordinary no-policy runs remain compatible.

Frozen new seams for root reds: artifact_operator.resolve_default_artifact_author(session,authority)->identity_id; ArtifactOperator(authority=...,sessions=...,messages=...) with create(intent), request_status(request_id), cancel(request_id), version(version_id), download(version_id); ArtifactOperatorError with code/http_status/cause/author_name/examined_roles. artifact_routes.create_router(operator_getter) binds only reduced routes. artifact_sources.project_artifact_message,check_packet_bounds and ArtifactSourceError; MessageStore.snapshot_selected(channel,message_ids); ArtifactService.request_status(request_id). Shared active_artifact_instance uses the current service rule. Tests patch only these declared seams or existing owner methods.

Backend red areas: ONE root file each for operator core/resolver/service reads; middleware/routes; source builder/snapshot; source Stop wiring. UI, screen script, transcript (including skip markers/admission-order export), packaging and activation remain later, in that order. Root records infrastructure versus behavioral reds and unobserved follow-on assertions, then reviewer executes/audits BEFORE product edits.

## Backend implementation decisions and evidence, pre-acceptance

NEW service request_producer(identity) derives audit producer fields and uses the SAME _producer/launch_provenance validation as prepare_request; operator resolver returns only identity and runs outside the boundary. Source capture returns (detached_session,packet). Shared exact event text helper is session_engine.event_projection_text, called by the actual projector and source validation. MessageSnapshotUnavailable is the generic typed MessageStore refusal; ArtifactSourceError and ArtifactOperatorError are the fixed source/operator types.

HTTP created202 versus stored replay200 is carried as an internal _Creation.created attribute, not an extra wire key. A final boundary read handles identical concurrent create as replay; input revision/current binding/Stop are rechecked. All error-time durability lookups are guarded reads; boundary-held refusal performs no owner lookup and reports unknown. Typed404/503 envelopes are preserved by a request-local marker when prefix framework responses are normalized; non-prefix handlers stay unchanged.

Stop cancels/fences requests captured while their source run was live; explicitly post-run snapshots remain independent. Durable cancelled/source_stopped precedes transport effects. Failed artifact fencing returns a separate transport_unconfirmed warning, rather than aborting session Stop. Retained-record repair retries without scanning all authoring channels for every historical run. After restart, retained records and startup recovery remain authoritative; in-memory reports are rebuilt as retained requests are inspected.

The backend source is implemented with48 ROOT tests passing; functional verification and independent acceptance are recorded in TICKET-20-REDUCED-PRODUCTION.md. UI/transcript/screen/activation are still not implemented by this backend slice. No R3 or performance campaign was started. Delivery cleanup requested by Seth is a separate required final stage before delivery, preserving history and references.

## Dated import-variance rule, reviewed2026-10-26

Under Seth's reduced basic-responsiveness scope, reviewer Sonnet5.5 ruled that the in-suite4MiB import benchmark always records the0.300s target and target_met, but fails the first release only above1.0s. This is a dated policy change, not a silent waiver: affected-suite sample0.3100635 was a REAL old300ms miss and remains in the receipt. Import/_persist/atomic_json AST is unchanged from accepted220f3400, whose sentinel gate full0.2045/held0.1972 remains authoritative for that path.

Before applying the new ceiling, the existing ten-sample method ran ONCE in isolation with MachineSentinel: all10 actual imports0.15999-0.17627s, median0.16460s, max0.1762739s, no target misses, zero replace retries; four sentinel gaps over100ms, max0.1077206s, none over500ms. The old assertion passed. Full discovery also passed1863/four skips on the pre-concurrency-fix product, import max0.188733s. No attribution/exclusion, resampling or tuning replaced the0.310s record. The test method is renamed to meet_basic_responsiveness, reports both target and basic limit, and its exact changed assertion was exercised at0.3100635/1.0 (accept) and1.000001 (refuse). That assertion check is not another hardware benchmark.

A subsequent duplicate-submit counterexample exposed an exception-path race: another same-intent creator can save a different captured packet before our staging. One observed red requires returning that stored identical winner instead of409. The fix rechecks saved intent inside the boundary on immutable conflict through the same replay helper; lookup failures remain typed and changed intents still409. Final root48 passes; final full verification follows that source fix. No import path or other performance budget changed.


## Backend review corrections G1-G4 / R1-R5, 2026-10-26

The original backend candidate is not accepted: the reviewer found held-artifact storage leaked into ordinary claims through historical Stop reconciliation. The corrected Stop model above replaces that behavior. Security parsing uses ASCII decimal Content-Length, rejects repeated channel/offset query fields, and sends empty HEAD bodies for successes and every refusal, including middleware/framework errors.

A packet staged before a later refusal remains immutable. If the same unsaved request_id later captures different source bytes, return409 request_conflict with cause packet_exists, durability not_recorded and text directing a new request_id. A concurrently saved identical winner still replays200 first. UI must mint a fresh request_id for each new submission; retrying an already saved identical intent retains idempotency. Producer drift/access loss after resolution maps to409 no_author_available/cause producer_unavailable, not request_conflict.

The source-so-far caption describes the accepted projection at capture time. Newly admitted events between capture and prepare do not invalidate that snapshot; run, binding, input revision and Stop are rechecked. Sessions paging currently detaches all session rows before slicing; this is accepted simple first-release behavior. The later responsiveness script must time the whole create wall call and the actual prepare boundary (including packet re-read, reservation, brief write, trigger and state writes); a >1.0s typical hold is reported without resampling.


## Final Stop isolation amendment A1-A3 / B1-B4, 2026-10-26

A bound artifact-policy getter returning None means no artifact policy. All Exception subclasses from artifact policy resolution/fencing/repair are contained, logged by class and reported as artifact_fence_failed (storage_unavailable for storage/OSError). They never abort ordinary queue claim or review Stop/reconciliation. Global channel holds still refuse claims; optional artifact startup repair stays idle under that hold.

Claim eligibility receives a set of stopped source run IDs from the coordinator's existing session snapshot. A request captured from a live source in that set is ineligible even if cancellation/repair failed. Explicit post-run captures remain independent. The bounded retained pass includes queued requests as well as ACTIVE ones and rotates across changing candidates. Prepared requests with no transport are also excluded by the eligibility guard and remain available to the existing recovery path; no whole-index scan is added for each historical run.

The process-local Stop observation cache is bounded to128 reports; it is not an authoring quota. Clean/confirmed warning-free reports are evicted first. If every slot is unconfirmed, keeping the newest report sets global unconfirmed_overflow instead of silently reading clean. Reports are lost on restart; explicit failure observations otherwise stay until successful re-Stop or the disclosed overflow condition. Empty cached reports are not proof of worker termination. Persisted requests and queue fences remain authoritative. UI scope includes a visible artifact cancellation warning/unconfirmed line in the Stop result/status, including artifact_fence_failed and storage_unavailable, separate from review outcome. No UI is implemented by this backend amendment.

Responsiveness script scope includes claim polling with100+ retained artifact rows, because the repair pass reads queue records and processes at most100 request IDs under the engine boundary. Source fencing and fence repair are separate authority passes over those IDs, each reading request rows;100 IDs is not a promise of only100 storage reads. Record this cost rather than claiming constant-time polling. Private _ArtifactCapabilityUnavailable remains an ArtifactConflict subclass with code artifact_capability_off; the operator maps it to no_author_available/capability_off if support changes at prepare time. The optional stopped_source_runs keyword on eligible_dispatch_ids uses a fresh source-run set when omitted; test hooks forward it.


## Backend closure follow-ups D1-D7, 2026-10-26

A missing artifact policy at enqueue is a typed QueueConflict, matching eligibility's closed behavior. Optional retained repair and artifact status inspection contain failures from their ledger snapshot too; underlying review transport still applies its own durable safety checks. The cache evicts clean/confirmed warning-free observations first. If all128 slots are unconfirmed, it retains the newest and sets global unconfirmed_overflow; this warning remains visible so eviction never looks like confirmed cancellation. A new unconfirmed dispatch invalidates a prior confirmed observation.

Prepared requests with no queue record use the explicit Stop retry path: after storage recovers, repeating Stop with the existing stable stop_id cancels pending prepared requests as cancelled/source_stopped. This also works after recreating the coordinator. Until retry, source-Stop eligibility refuses them, and the request card can cancel them through the existing minimal Cancel route. A prepared request never becomes claimable merely because no retained record exists. No full-index prepared scan is added to every historical-run claim.

UI release requirement: show artifact_cancellation warning and unconfirmed dispatch status with textContent in both immediate Stop results and polled status. Include artifact_cancellation in the sessions render-cache key so warning changes repaint. This is pending UI work, not a backend acceptance claim. The screen must retain the100+ retained-row claim-poll observation including eligibility channel_names/pending index work, report-only under the reduced scope.


UI lost-response clarification2026-10-26: GET404 after an aborted create is not proof that the worker will never save it. Keep the same id/intent through404 and replay; only definitive create refusal, packet_exists or explicit warned abandonment allows a new id. This supersedes the reviewer's initial U1 proposal. SessionStorage retains identity/digest metadata only; original instruction re-entry is required to replay after reload. See the approved UI technical contract for deadline/backoff, sticky cancellation warning, safe reader/download and stale-response rules. Browser acceptance remains pending; capability is empty.

## Reviewer disposition after final browser attempt, 2026-10-26

Reviewer classifies attempt5's screenshot timeout as the host's inability to render frames, not a product failure. No sixth attempt or unprompted Chrome/Edge work. Positive real-browser DOM evidence is accepted for startup, create/Queued, real MCP brief/submit/release, automatic Ready, manual Refresh, literal PRE reading and byte-exact99B Blob/download intent/revocation, served script proof and raw cleanup. This is PARTIAL browser evidence, never UI acceptance. The12-case gate remains incomplete and acceptance_claim=false. Viewport/keyboard/mobile/API/lost-create/refusal/cancel/lifecycle/backoff/reload/stale and every visual/layout check rely on existing component, Node-vm UI and mutation tests; they are not browser-proven.

Baseline correction from reviewer's read-only Win32_Process query: added PID56240 pythonw.exe start2026-10-27T01:00:01.296Z is a Task Scheduler child of svchost.exe running C:/Users/SJG/miniconda3/pythonw.exe -m hotin refresh --quiet. Timestamp matches root's baseline addition. Record as added unrelated scheduled process, identified, outside all owned births; no fixture-caused baseline violation is established. Original baseline and raw deviation remain retained; PID58092 stays a separate historical miss. No unrelated process was changed.

Recommendation relayed to Seth, decision pending:

- Accept PARTIAL browser harness for20-22 and proceed to responsiveness screen,21 and22, because capability remains off until a separate activation commit.
- Add a pre-ACTIVATION real visual check of the Documents panel at desktop and390px, by Seth looking at it, or an optional separately owned Chrome/Edge follow-up if he requests automation. This precedes activation, not21/22 work.
- Alternatives: accept partial with no visual gate, or build Chrome/Edge harness first. Ask Seth once. If he does not answer, follow the first recommendation; activation remains blocked until visual checking is done. This default is the reviewer recommendation, not a fabricated user decision.

Next owner root: prepare the thin responsiveness screen under the existing reduced contract, then21/22. Retain all roots; no deletion, activation or push. No additional browser adaptation.

## Acceptance order and timing correction, 2026-10-26/27

Seth: "pend 21 to after acceptance" (reviewer relay). Ticket21 and22 are pending until Ticket20 acceptance. Transcript contract/reds are preserved, with9 explicit pending skips; no transcript product code is implemented. Next: one frozen full Ticket20 discovery, separate activation commit for independent review/sign-off, then21/22, final cleanup and publication only after explicit push authorization.

270ms/216ms were docs/reviewer targets without a derived baseline; reviewer withdraws them at Seth's request. Only the existing1.0s basic timing ceiling remains; import300ms is report-only. Standalone tools now use1.0s for timing failures; historical comparative values/misses remain. Safety/error/retry/ownership checks unchanged. No speed-screen tool or new timing campaign.

## Ticket20 frozen regression and activation candidate, 2026-10-26/27

Seth's freeze: "unless there is a blocking feature everything is frozen" (reviewer relay). No new features/hardening/harness/timing/refactor work. Only an evidenced blocking document-flow or safety/auth/data-loss defect may receive a minimal observed-red fix after reviewer notification. Ticket21/22 remain pending until20 acceptance.

Frozen product0a009ca full root discovery:1936 tests across227 modules, OK398.132s,13 explicit skips (9 pending Ticket21 transcript +4 existing). Shell6384cb77-6ab5-42d7-8980-05aa28c91753 exit0; no product/test edits during the run. No timing campaign. Historical tool controls are not part of root discovery; their frozen4968 guard remains unchanged.

Activation CANDIDATE, awaiting independent review: runtime_protocol.SUPPORTED_CAPABILITIES advertises only artifact-v1. This is the sole product edit. Three existing test defaults now expect the activated capability; all disabled-policy/legacy/source/birth/ownership refusal bodies remain, with an additional explicit empty-manifest policy test. Before the flag change,3 activation expectations failed by assertion (0.029s); after,112 capability/admission/worker/operator/routes/UI tests OK18.599s. Full1936 predates the flag;112 focused tests cover the candidate. No live runtime/seat/model launched from the candidate, no push. Existing managed launches must be relaunched to receive the new source-bound manifest; old retained launches are never retroactively granted support.

Post-review UAT, fixed providers: real Claude CLI with claude-haiku-5-5, Sonnet/lower fallback only if needed; no Fable/Opus, no helper agents. API author z.ai only, exact model/base URL must come from Seth/config, never guessed. Both paths: one small create -> author -> submit -> read -> exact download, stop at first problem; live-path evidence only, no UI/visual acceptance. Authorization is after full discovery and activation review only. Isolated fixture roots, owned signed process cleanup/baseline comparison, credential/token scans, no global/Omarchy/Desktop changes. No keys in chat/logs/receipts; existing API-seat secret_ref path or Seth's one-process masked input. CLI executable is installed; login has not been exercised. No z.ai provider exists in either project config/batch tree; local config absent. Need base URL/model slug/environment reference and masked key setup before API live testing. No live calls made.

Next owner reviewer: review the activation candidate and sign-off for launch/UAT. Root then performs bounded Claude and z.ai checks when configuration is available. Ticket21/22 stay pending; final file cleanup/publication later, explicit push authorization still required. Optional desktop look only; phone-width/speed-screen/browser-harness work is withdrawn.

## For Seth: Ticket20 UAT is running

Open http://127.0.0.1:49949. Separate test data; normal installation data and known ports are unchanged. Both seats are ready. The instance stays running until you request stop.

Worked: real Claude CLI, requested Haiku5.5, created/read/downloaded a124-byte document with identical bytes. Live z.ai glm-5.3 did the same with285 bytes; API response confirmed glm-5.3. CLI model confirmation remains honestly unverified. Rough live usage: one API generation, one Claude print probe and one Claude document generation; no Fable/Opus/helpers.

Setup note: Claude's initial workspace-trust menu defaulted to No, causing the first CLI request to stall/exit. Only the empty owned UAT workspace was approved; a fresh source-bound seat/session then passed. The old request was durably cancelled, and a stale-source retry was refused without a new document. No product fix was needed. One owned setup restart loaded the authorized z.ai environment; a later refresh rebound the test sessions. Previous API data survived the restart. Historical failures are retained.

Features are frozen, code is not: Seth's correction permits minimal fixes to defects in existing features with focused checks, without new features/refactors/harness/timing work. Ticket21/22 remain pending until20 acceptance. Activation cfcbdf1 was independently signed off with112 reviewer tests; prior full1936/13 skips remains retained.

Stop in PowerShell: `& 'C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\.audit-tmp\stop-ticket20-uat.ps1'`. This requests cooperative shutdown of this instance and its seats only. Signed births remain for verification; the active inventory has7 owned live processes, so no cleanup-complete claim is made while it is running. No browser/profile was created for live UAT. No push/publication/deletion.

The12 short UAT steps are in the shared Ticket20 UAT artifact and .audit-tmp/ticket20-uat-handoff.md. Choose Documents in #general, then Claude UAT source or z.ai UAT source. Those are declared synthetic accepted fixture sessions. Live checks cover the API/CLI paths, not visual UI acceptance. Optional desktop look only; no phone/speed/browser gate.

Credential handling: only the authorized ZAI_API_KEY line from the user's .env was read into child environment memory; no key value in config, arguments, logs, receipts or summaries. Provider block is confined to the owned root's config.local.toml. No other .env key was parsed; no normal-install config was copied. Exact Desktop/agentchatrr reference was absent, so no broad search or launch/write there occurred. Native Claude login was reused without copying an authentication home.

Next owner reviewer: final Ticket20 sign-off on these live results. Root keeps the instance up for Seth;21/22 stay pending until acceptance. All non-blocking findings remain notes, not new work.

## Ticket20 reviewer acceptance

Reviewer signed off atfaab83599a71890976dac70bce78b683d3039b29. Accepted product activation iscfcbdf1; subsequent changes are documentation only. Both live code paths passed. This is code-path acceptance, not visual/browser acceptance, Seth's UAT verdict, publication or cleanup.

UAT stays running at http://127.0.0.1:49949 until Seth requests stop. Ticket21/22, final file cleanup and publication stay pending Seth's call. Fix reported defects in existing features with focused checks; add no features, harnesses, timing work or refactors. No push.

Non-blocking notes:
- A fresh Claude workspace needs one-time Yes at the native trust menu, whose default is No, exit.
- The CLI path cannot verify the actual model; requested Haiku5.5 is labeled honestly.
- Exact Desktop/agentchatrr reference path was absent on this host and was not used.
- The cancelled first CLI request and refused stale-source retry remain retained history.

Full1936/13 explicit skips and focused112/independent112 checks stand. Live CLI124B and API285B read/download matches stand.15 public-export/server-log files passed credential/session-token scans; no secret values exported. Signed active inventory remains7 live, deliberately not a cleanup-complete claim. Short UAT checklist and stop script are linked above.

## Final nightly requested-seat handoff

Five seats remain running: Claude Opus5.5, Codex Sol6.1, DeepSeek Flash, GLM5.3 and Muse1.3 contributor. DeepSeek100B and Muse81B real document read/download match; GLM prior285B match reused. Claude/Codex readiness and native hellos only, no new expensive document loops.

Antigravity gemini-3.8-flash-medium native hellos pass, but its managed document timed out and was durably cancelled; startup reports not logged in. Seat stopped, needs Seth's login check. The authorized distinct global MCP entry was backed up, added alone, then removed; remaining structure equals backup. No global trust-file change occurred.

MiMo parked, MiniMax not used. Next after Seth UAT/decisions: Hermes/OMP CLI seats before Ticket21, then22, cleanup, publication. None started tonight; no push. Full six-row report, exact backup hash/path, removal and stop instructions are in STATUS and the shared seat artifact.
