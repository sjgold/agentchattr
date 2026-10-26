# Reduced release: tickets 20-22, then multi-file 23

Status: PRODUCT SCOPE APPROVED by Seth2026-10-26 and reviewer atb2b31adb. This E1-E12 revision freezes proposed defaults/routes/errors/new-work boundaries for the one required docs recheck before reds; no production clearance yet. No product code, activation or push is authorized by this document edit. Accepted backend product220f3400 remains unchanged.

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

Existing sessions store frozen design_snapshot.roles and current participant_bindings. NEW pure selection seam: resolve_default_artifact_author(session, registry, seats) returns either a detached eligible {role,name,identity_id,producer} or a typed no_author_available result with cause and optional author_name. Under the existing shared boundary, iterate design_snapshot.roles IN ORDER, skip bindings whose kind is human/family or has no agent identity_id, and resolve each agent binding by identity_id against the LIVE registry. Never select by cast name or by an arbitrary available seat. Require a unique live identity match and current seats.artifact_producer eligibility. Select the first eligible role in that order; current participant_bindings rewrites from replacement are authoritative at save time. Capture the selected role/identity and immutable producer audit. Duplicate identity matches are ambiguous and refuse rather than being guessed.

If no eligible agent resolves: no agent bindings -> no_agent_role; agent bindings but no matching live instance -> no_live_instance; otherwise preserve the first candidate's fixed eligibility cause (capability_off, not_supported, runtime_unverified or binding_changed). When the global capability is empty, cause=capability_off and text is exactly "Artifact authoring is not enabled." No launch/restart, unsupported-client fallback or new producer selection UI. Public card/refusal shows the resolved registry name when known, otherwise author_name=null and a fixed explanation. The name is informational; identity_id is the authority. This is NEW resolver implementation, not an existing seam. Before submit, the UI can say "Author selected from this session"; the resolved author name appears on the saved card or refusal, avoiding a new preview API.
Proposed POST /api/artifacts/requests body is EXACT:

    {request_id: Hex32, channel: ChannelName, session_id: positive bounded int,
     run_id: Hex32, instruction: nonblank UTF8 text <=32768 bytes}

No preview_token, producer claim, message_ids, model, capability, parent or lineage fields. Unknown fields refuse. Channel/session/run must match the real session selected in the UI; the client identifiers grant no authority. Format is server-fixed Markdown. A new independent document has no parent; deterministic request-derived IDs and one-live-slot rules remain. No revision endpoint is part of this release.

Default source: run_accepted_messages from that exact same-channel session/run, including its frozen input snapshot and the admitted-event/operator-continuation projections available when the server saves the request. Exclude unrelated chat, quarantined/unadmitted/abandoned outputs and unlinked human discussion. Existing projection identity/attribution/text checks and source allowlists stay mandatory. No hidden recent-N window, truncation or reconstructed missing message. If no accepted contributions exist, refuse clearly instead of silently making an instruction-only request. Preserve2MiB/1000-message packet and512KiB Markdown bounds; these are existing per-object bounds, not a new installation quota.

The UI says that the source is captured when the request is saved. No preview freshness promise exists because the preview flow is deferred. Under the actual boundary, recheck source/session/channel/producer and freeze one detached snapshot. Before source capture, author resolution or prepare_request, same-ID replay reads the stored request and compares ONLY {request_id, channel, session_id, run_id, instruction, format, requester}, with format=Markdown and requester=operator. Return the stored projection without prepare_request or fresh source/producer work. A producer relaunch changes launch_nonce/fingerprint but must not invalidate an identical replay; prepare_request audit equality is NOT the replay implementation. Different intent with the same request_id is409 request_conflict; imported request IDs remain read-only conflicts. Request body identity is exactly channel/session/run/instruction plus request_id; derived fixed format/empty parent cannot vary. Reject cross-channel IDs and unsupported identity before writes.

Refusal presentation: a fixed readable reason, no private nonce/seal/token/config/path/body echo. Unavailable author: show its name and that a supported managed instance is required, with no automatic launch. Missing/changed source: state that the current session source could not be captured and no new request was saved. Oversize: state the existing per-object bound and no truncation. Partial durability: retain the accepted recorded/not_recorded/unknown distinction and request id, then show the status refresh action; never invite a new-id blind retry when prior durability is unknown. Exact error DTO/status mapping is the next bounded route freeze, reusing cleared families.

Minimum operator surface and normative response policy are frozen below. These routes/security/snapshot helpers do not exist yet and are in-scope NEW work. The earlier complete operator contract is historical, so this document restates every retained rule needed for this reduced surface.

### Consistent source capture is in scope (E4)

NEW MessageStore.snapshot_selected(channel, message_ids) validates unique nonnegative IDs, takes its message RLock ONCE and returns detached complete rows for exactly that channel/ID set, or typed unavailable with no partial list. Existing get_recent/get_since return mutable row aliases; repeated get_snapshot reads are not a consistent batch. The store helper has no artifact imports, callbacks or seat authority.

NEW capture_artifact_session_source(session_id, run_id, channel) runs under the engine/catalog boundary: obtain one detached SessionStore.get session; verify exact session/run/channel; derive projection IDs from admitted_events and continuation_context; reject missing/duplicate links; obtain exactly one snapshot_selected batch; validate expected UID (session-event:<event_id> or session-input:<question_event_id>), attribution, metadata identities and exact projected text against the trusted event/continuation, including the existing completion/missing-contribution footer rule; sort by stored message id. Extract a shared pure expected-projection-text helper from the existing projector so this does not duplicate its formatting rules. Source text is read once from the detached batch, never refetched while encoding. Validate the allowlisted packet with existing _packet_scope and existing2MiB/1000 limits. No projection repair/model call/hidden fallback. Typed source_unavailable or source_too_large refuses before reservation. Keep original frozen input/revision/document. All source allowlists protect config/nonce/seal/fingerprint/token/path fields while retaining literal user text. Snapshot consistency/projector integration is substantive NEW work in the smaller release, not assumed to be a tiny existing API.

### Minimum routes, completion discovery and card actions

|Method/path|Exact purpose|
|---|---|
|POST /api/artifacts/requests|Exact create body above;202 only for new recorded+queued success,200 for identical stored replay.|
|GET /api/artifacts/requests/{request_id}|Detached public status/author/source summary, including terminal and needs_resume state; no full audit/seal/launch secrets.|
|POST /api/artifacts/requests/{request_id}/cancel|Body EXACT empty object. Existing cancel_request, same-channel guard; current state/transport warning returned.|
|GET /api/artifacts/versions/{version_id}|Completed Markdown plus safe metadata; plaintext reader consumes markdown via textContent.|
|GET /api/artifacts/versions/{version_id}/download|Exact saved UTF8 bytes, authenticated download.|
|GET /api/artifacts/sessions?channel=<name>&offset=<int>|Bounded same-channel session summaries from SessionStore.list_all(channel), newest started_at then id, max20. Includes completed sessions; not get_active. Shows session/run/state/title, no bindings/secrets/source text. offset defaults0, nonnegative bounded int; page size fixed20. Response EXACT {sessions:[{session_id,run_id,title,state,started_at,source_so_far}],offset,has_more}. A More control pages20 at a time.|

Create permits a matching complete session as well as a current run. UI retains a Request document action on the completed session card and can recover that card from the bounded session summaries after reload. Mid-run cards say "Source so far". The session list chooses the run, not arbitrary source messages/another producer; the deferred source picker stays deferred. Archived/inactive channel new create refuses; retained reads remain available. Poll known request IDs; no global artifact catalog is added.

Minimal Cancel is INCLUDED. It invokes the already accepted authority/fence path; cancellation state is durable before fence effects. Show cancelled with an explicit transport-unconfirmed warning where applicable, never worker-exit proof. Existing source Stop behavior remains. Cancellation of a terminal race returns its typed conflict/current status and refreshes. Cancellation/Stop bypass the new capability gate where the accepted cancellation path does. This prevents a stuck live document from being trapped behind the deferred resume dashboard; unreadable storage can still hold cancellation and channel management honestly.

### NEW strict operator security branch (E3)

Implement a prefix branch for EVERY /api/artifacts path, including unmatched routes, before legacy token fallback. The existing middleware does not supply this security. Order: validate raw headers/auth/Origin/Host, then method, then media/size/JSON/body shape, then route semantics. Require exactly one nonempty X-Session-Token matching configured token, no Authorization header, no query parameter named token (even alongside valid header), no cookie/URL auth fallback; reject duplicate auth/Origin/Host headers. Set request.state.auth_origin=operator, require it at binder. Seat bearer access refuses403.

Origin is REQUIRED for this browser-facing namespace and must equal configured http://localhost:<port>, http://127.0.0.1:<port> or http://[::1]:<port>. Host must be one of the corresponding literal loopback hosts with configured port (case-insensitive hostname, omitted port only at80); no credentials, suffix matching or forwarded-host trust. Fake/non-browser clients send the same explicit allowed Origin. Other existing namespaces retain their compatibility behavior. Reject bad origin/host before route work.

Every prefix response, including403/404/405/validation/download, has Cache-Control:no-store and X-Content-Type-Options:nosniff. Unsupported method405, unmatched path404, framework422 mapped to400 invalid_request. POST Content-Type exactly application/json plus optional charset=utf-8, otherwise400. Body <=256KiB, bounded max+1 read before parsing; valid UTF8, reject duplicate JSON fields/nonfinite values/unknown keys/wrong types. Instruction uses existing _index_text with32768 UTF8 byte limit/HT-LF-CR policy; no trimming/normalization. Enforce exact ID/count grammar. Process blocking owner/JSON work through asyncio.to_thread; no await under locks and no model call from HTTP handler.

Download Content-Disposition is fixed ASCII attachment; filename="document.md" (transcript uses "transcript.md"). Use text/markdown; charset=utf-8 plus nosniff, never text/html. Browser uses authenticated fetch with X-Session-Token, then blob/object URL, revoke after use; no credentials in query/filename/log. Read response markdown is JSON text only; client assigns textContent to a wrapping pre-style block (overflow-wrap:anywhere, keyboard-copy and download). No Markdown-to-HTML renderer in first release; rendering is deferred. Script/img/link/javascript:/data:/entity strings display literally; exact original bytes are asserted on download.

### Reduced error and public state contract (E5)

Public error envelope EXACT {code, error, cause, author_name, request_id, durability, request}; nullable fields are null, not omitted. code/error/cause are fixed reviewed literals, never str(exception). durability is recorded/not_recorded/unknown/null. request is the detached RequestSummary below or null, using an allowlist. Syntax/auth failures do not echo submitted text. Partial-effect lookup failure gives unknown; it never erases the durable request or authorizes a blind new-id retry.

|Code|HTTP|Meaning|
|---|---|---|
|invalid_request|400|Bad header/media/JSON/field/syntax; no new reservation.|
|operator_forbidden|403|Operator token/Origin/Host/duplicate auth failure.|
|method_not_allowed|405|Authenticated valid-prefix request uses unsupported method.|
|request_conflict|409|Same ID changed intent, imported ID, live-slot/head conflict, cancelled/terminal race.|
|session_unknown / run_unknown|404|No such stored session, or no matching retained run.|
|channel_mismatch|409|Session/run/request belongs to a different channel.|
|channel_inactive|409|New authoring forbidden in current channel state.|
|no_author_available|409|cause no_agent_role/no_live_instance/not_supported/runtime_unverified/binding_changed/ambiguous.|
|no_author_available|409|cause capability_off; exact text "Artifact authoring is not enabled."|
|source_unavailable|409|Empty accepted source or missing/changed projection, no partial packet.|
|source_too_large|413|Existing2MiB/1000 packet cap, no truncation.|
|request_too_large|413|HTTP256KiB body or instruction32768-byte cap.|
|transcript_too_large|413|Transcript export cap below, no partial download.|
|storage_unavailable|503|Held/malformed/unreadable owner/object, durability reported honestly.|
|boundary_held|503|Typed internal boundary guard refused; fixed public text.|
|not_found|404|Unknown request/version or unmatched prefix path.|
|not_ready|409|Known request has no completed version yet.|

No capacity refusal is invented: no installation quota is enabled. A real existing object/byte cap uses its specific size refusal above. Preserve other accepted agent/service transport errors outside this operator namespace; this table maps only reduced operator operations.

RequestSummary EXACT {request_id,channel,state,reason,label,author_name,created_at,updated_at,version_id,source,needs_resume,warning}. source EXACT {session_id,run_id,message_count,packet_bytes,scope_sha256,input_revision,source_so_far}; no copied refs/body/launch fields. warning is null or an accepted fixed transport/recovery warning. label is exactly queued/working/ready/failed/unavailable. Mutation response EXACT {request:RequestSummary,durability,transport_settled}; no producer credentials or full _projection dump.

|Stored state / condition|Label and card text|
|---|---|
|prepared / queued|queued; "Queued".|
|active|working; "Writing document".|
|fulfilled|ready; "Ready" denotes recorded completion; document reads/downloads still verify bytes and may report storage unavailable.|
|failed|failed; "Document could not be completed"; stored closed reason remains available.|
|cancelled, reason operator_cancelled|failed; "Cancelled" plus unconfirmed-fence warning if applicable.|
|cancelled/source_stopped or stopped-source cancellation|failed; "Stopped".|
|quarantined|failed; "Response rejected" (no raw retained body shown).|
|live row with absent queue/needs_resume|unavailable; "Needs recovery" with existing channel-management/repair guidance, not automatic retry.|
|storage/refusal/poll unavailable|unavailable; preserve last known state visibly; no fabricated terminal result.|

operator_cancelled is a reason, not another store state. needs_resume is a projection over a live row, not a persisted state. Poll every2s while known live; after request failure back off to4/8/16/30s maximum, retain last known state and show connection/storage unavailable; successful poll resets2s. Stop automatic polling at fulfilled/failed/cancelled/quarantined. Explicit Refresh remains. If a later document read fails verification, show unavailable instead of displaying unverified text. A queued/active stale card can still offer Cancel; advanced resume is deferred. Cancel/retry outcome never hides a partially durable effect.

## Transcript export (21), explicit NEW route

NEW GET /api/artifacts/sessions/{session_id}/transcript?channel=<name>&run_id=<Hex32> in the SAME strict security prefix, authenticated fetch+blob download. Session/run/channel must match; current or completed sessions allowed. No transcript implementation exists today. Reuse the source snapshot/projection validation, but transcript has its own export byte cap rather than silently applying the2MiB packet cap. It reads actual stored accepted/admitted-event and linked operator-continuation messages, stable by ascending stored message id. No model synthesis or invented text.

UTF8 Markdown output has a fixed session/run/source-scope header, then each message's id, sender/seat, recorded timestamp (explicit unknown when null), phase/turn labels from matching trusted event metadata, and exact text. Attachments get a fixed "Attachment present; content not exported" marker, not local paths/URLs/secret metadata. Incomplete/current/stopped/skipped contribution flags are explicit header/phase markers. Superseded/abandoned/quarantined content is excluded by default with an omission disclosure, no advanced inclusion selector. Missing/edited projections refuse source_unavailable rather than reconstructing them from journal text. Preserve exact message text/Unicode/CRLF within the deterministic Markdown container; HTML is never served.

Proposed export cap8MiB UTF8 output, checked during bounded assembly before returning bytes, no truncation or partial download. This is a per-export safety bound for review, not an installation quota or a1000-character document limit. It does not change backup ZIP schema/budgets: transcript download is a separate convenience export, ZIP backup remains the retained full history/objects path. Only reproduce/fix actual backup integration defects; no backup redesign.

## Acceptance and what stays protected

Unchanged: authorization and secret protection; no cross-channel scope; exact source/provenance and model honesty; immutable Markdown; request/attempt/dispatch ownership; replay/idempotency; durable ordering and partial-effect honesty; stale-result refusal; cancellation/source Stop fencing; held/corrupt storage behavior; diagnostics privacy; no accidental model calls. Existing accepted R1/A1/R2+D4 code and discriminating tests remain. UI accessibility, keyboard operation and safe rendering remain required. Production artifact capability remains empty until the separately reviewed activation commit.

Changed: first-release acceptance no longer requires every storage/shared-boundary operation at all maximum populations to stay<=0.270s with20percent margin. The withdrawn128-request/512KiB installation quota remains withdrawn. No R3, new schema, migration tool, capacity reservation or R4 is included in20-22. Accepted4MiB import tests and existing limits remain regression checks, not a reason to start a fresh unrelated benchmark campaign for each docs/test edit.

### Proposed numeric responsiveness screen (not a tail guarantee)

Run ONE bounded real-files screening pass on the frozen integrated release, no overlapping suites. Retain tool/product/fixture hashes, actual values, sentinel and retry observations using the existing harness. The existing tools cannot run this screen directly: they have no typical create fixture, enforce10 samples and the old limits. NEW thin tools/screen_artifact_release.py is in scope, reusing shared sentinel/retry/receipt mechanics but using ONLY these four observations. Include fixture/tool hashes, actual create/hold/peer timing and all errors; no new framework. Typical fixture:10 prior requests, current session up to50 accepted messages and<=64KiB packet, instruction<=4KiB, result<=64KiB, no parent. Three fresh typical samples: each create service call (excluding model generation) <=2.0s; each shared-boundary hold and concurrent peer wait <=1.0s. Record the actual run; an exceedance is a reported responsiveness finding for review, never a silently repeated sample.

One maximum-source sample:2MiB/1000 refs with32KiB instruction and512KiB result, using the accepted129/130-request fixture. Record call time, holds, peer wait and UI busy/refusal behavior. Maximum shape has no new worst-case latency promise; a captured slow operation is disclosed. It must still finish with a genuine result or typed refusal, without lost data, fabricated success or frozen event-loop work. The request UI shows a pending state rather than hiding work behind a spinner with no status. This is four screening samples, not another190-row timing campaign. Functional race/Stop/auth/durability regressions still run where relevant.

These numeric fixture thresholds are a reviewer-facing proposal chosen to make basic responsiveness testable. Seth approved replacing the strict old guarantee, not these specific numbers. Reviewer must accept or revise this small screen before implementation tests. Any material new work beyond a reproduced integration issue returns to Seth with its user-visible need and smallest alternative, rather than adding another storage redesign automatically.

## Finite capacity and evidence disclosure

Without R3, full source refs remain duplicated in request/version index metadata. The historical sizing probe measured293110 bytes for one fulfilled max-source request; it is not a product quota or a current per-request constant. More requests/versions and larger sources increase validation/write cost. No purge exists; deletion/export retains authored history. No replacement installation quota is chosen or implied.

Accepted evidence remains scoped: final max-source service A phases were roughly0.16-0.18s on this machine; final4MiB import full/held/peer maxima were approximately0.20-0.21s. The complete D4 final190 run passed with a stall sentinel. Earlier real misses, roughly1.1s unattributed stalls and instrument-invalid attempts remain in TICKET-20-D4-FINAL-GATE.md. These facts do not establish unlimited capacity or guarantee future tail latency.

## Current verification boundary and next work

This amendment changes documentation only. R2+D4 is independently FINAL ACCEPTED at220f3400: reviewer170 focused OK47.5s; builder437 artifact and1817 full (4 skips) pass;17 mutants assertion-killed; prior gate190 retained. No reduced operator/UI/transcript code has been implemented or accepted by this edit. Old R3 sidecar proposal196666c and reviewer no-sidecar/no-conversion ruling are preserved as historical/deferred material, not an active red-work instruction.

Next order after independent docs clearance: Ticket20 backend reds (resolver/snapshot/create-replay/status/read/download/cancel/middleware), then UI/plaintext reader, then the thin four-observation responsiveness script, then Ticket21 transcript, then Ticket22 packaging. Relevant safety regressions and one final full discovery on the frozen integrated product, with rendered acceptance, remain required. Stop on a real screen miss and report it; no resampling campaign. Reviewer decides disposition on retained numbers. Review the activation commit last before publication. No new agent creation, provider spend, external issue edit, deploy, activation or push is authorized by this documentation request.

## Activation and the release22 finish line (E9)

With SUPPORTED_CAPABILITIES empty, EVERY new production create is refused with no_author_available/capability_off. Other accepted read/cancel/replay safety semantics remain. Development acceptance uses the existing in-process fixture-patched capability only: managed local fake CLI with the real MCP artifact tool, API local fake responder/outbox/admission, and rendered browser in Ticket19-style isolated sessions. Label these honestly; no live provider/model spend, installed-client compatibility, Omarchy or Desktop mutation is inferred.

Release22 is not called usable while the capability is disabled. After the frozen20/21 flow and packaging pass, prepare a separate ACTIVATION commit containing the reviewed capability allowlist and actual wrapper support/wiring, with explicit fail-closed unsupported-client checks. Independent reviewer must clear that commit and its end-to-end fake acceptance before shipping. No activation is done by these docs; git push remains held until Seth explicitly authorizes it.

## Reduced specification acceptance (E12)

DA-2 / artifact AT-12 for20-22: explicitly request current/completed session document with default bound author, preserve provenance/attempt safety and immutable records, read escaped Markdown text, download exact .md, expose status and minimal Cancel. Revision browser, producer/source picker and advanced resume UI are deferred.

DA-3 / transcript AT-12 for20-22: download accepted stored messages in actual ID order with phase/seat/time/message provenance and incomplete/omission markers. Explicit abandoned-attempt inclusion, combined synthesis layout and automatic synthesis are deferred. Backup ZIP preservation remains. Transcript and first document together are exercised through the real operator HTTP/browser flow with fake managed adapters.

R3, new schema/sidecar/converter/capacity policy, multi-file23 and automatic24-26 remain outside this implementation package.23 is the next milestone and outranks24-26 per Seth. This E1-E12 freeze clarifies NEW work honestly; it does not claim those helpers or security checks already exist.
