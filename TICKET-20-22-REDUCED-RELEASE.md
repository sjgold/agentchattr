# Reduced release: tickets 20-22, then multi-file 23

Status: PRODUCT SCOPE APPROVED by Seth2026-10-26. Implementation defaults, route shapes and numeric responsiveness screening below are PROPOSED for bounded independent review before reds. No product code, activation or push is authorized by this document edit. Accepted backend product220f3400 remains unchanged.

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

Existing sessions store a template/cast, not a special coordinator identity. Proposed default author: the registered instance named by session.cast[first role in the frozen session template's roles order]. Show that participant name before submission. Resolve and verify its current immutable managed identity and artifact-v1 eligibility server-side. Never choose an arbitrary different agent, launch/restart a producer or fall back to an unsupported client. If the role/registration/binding is absent or unavailable, refuse before a new durable reservation. This default must be independently checked against actual session data before source changes; it is not a new user-approved coordinator setting.

Proposed POST /api/artifacts/requests body is EXACT:

    {request_id: Hex32, channel: ChannelName, session_id: positive bounded int,
     run_id: Hex32, instruction: nonblank UTF8 text <=32768 bytes}

No preview_token, producer claim, message_ids, model, capability, parent or lineage fields. Unknown fields refuse. Channel/session/run must match the real session selected in the UI; the client identifiers grant no authority. Format is server-fixed Markdown. A new independent document has no parent; deterministic request-derived IDs and one-live-slot rules remain. No revision endpoint is part of this release.

Default source: run_accepted_messages from that exact same-channel session/run, including its frozen input snapshot and the admitted-event/operator-continuation projections available when the server saves the request. Exclude unrelated chat, quarantined/unadmitted/abandoned outputs and unlinked human discussion. Existing projection identity/attribution/text checks and source allowlists stay mandatory. No hidden recent-N window, truncation or reconstructed missing message. If no accepted contributions exist, refuse clearly instead of silently making an instruction-only request. Preserve2MiB/1000-message packet and512KiB Markdown bounds; these are existing per-object bounds, not a new installation quota.

The UI says that the source is captured when the request is saved. No preview freshness promise exists because the preview flow is deferred. Under the actual boundary, recheck source/session/channel/producer and freeze one detached snapshot. Same-ID replay checks stored intent first; it must not regenerate from changed chat or a later producer. Request body identity is exactly channel/session/run/instruction plus request_id; derived fixed format/empty parent cannot vary. Reject cross-channel IDs and unsupported identity before writes.

Refusal presentation: a fixed readable reason, no private nonce/seal/token/config/path/body echo. Unavailable author: show its name and that a supported managed instance is required, with no automatic launch. Missing/changed source: state that the current session source could not be captured and no new request was saved. Oversize: state the existing per-object bound and no truncation. Partial durability: retain the accepted recorded/not_recorded/unknown distinction and request id, then show the status refresh action; never invite a new-id blind retry when prior durability is unknown. Exact error DTO/status mapping is the next bounded route freeze, reusing cleared families.

Minimum proposed operator surface: create, get request status, get completed document and authenticated Markdown download. Basic current-session document cards can use those responses; no global catalog, producer/source enumeration, preview/revision/source-detail/resume routes are required now. All operator authentication, Host/Origin/no-store/nosniff, strict JSON and secret allowlists from the old operator contract remain. Existing agent endpoints and capability negotiation remain unchanged. Renderer must preserve content while preventing scripts/unsafe HTML/unsafe links; no use of the inherited transforming reader without verification.

## Transcript export (21)

One Download transcript action for the current session. Use actual stored messages in stable order with IDs, author/seat, timestamps, phase markers and incomplete/superseded indicators. Exclude abandoned attempts by default; no selector to include them in this release. Keep the scope disclosure explicit. No model reconstruction or extra synthesis call. A simple separate Markdown transcript is sufficient; combining it with an authored report and elaborate layouts is deferred. Reuse existing backup ZIP behavior and fix only reproduced defects; no backup redesign is authorized.

## Acceptance and what stays protected

Unchanged: authorization and secret protection; no cross-channel scope; exact source/provenance and model honesty; immutable Markdown; request/attempt/dispatch ownership; replay/idempotency; durable ordering and partial-effect honesty; stale-result refusal; cancellation/source Stop fencing; held/corrupt storage behavior; diagnostics privacy; no accidental model calls. Existing accepted R1/A1/R2+D4 code and discriminating tests remain. UI accessibility, keyboard operation and safe rendering remain required. Production artifact capability remains empty until the separately reviewed activation commit.

Changed: first-release acceptance no longer requires every storage/shared-boundary operation at all maximum populations to stay<=0.270s with20percent margin. The withdrawn128-request/512KiB installation quota remains withdrawn. No R3, new schema, migration tool, capacity reservation or R4 is included in20-22. Accepted4MiB import tests and existing limits remain regression checks, not a reason to start a fresh unrelated benchmark campaign for each docs/test edit.

### Proposed numeric responsiveness screen (not a tail guarantee)

Run ONE bounded real-files screening pass on the frozen integrated release, no overlapping suites. Retain tool/product/fixture hashes, actual values, sentinel and retry observations using the existing harness. No new performance framework. Typical fixture:10 prior requests, current session up to50 accepted messages and<=64KiB packet, instruction<=4KiB, result<=64KiB, no parent. Three fresh typical samples: each create service call (excluding model generation) <=2.0s; each shared-boundary hold and concurrent peer wait <=1.0s. Record the actual run; an exceedance is a reported responsiveness finding for review, never a silently repeated sample.

One maximum-source sample:2MiB/1000 refs with32KiB instruction and512KiB result, using the accepted129/130-request fixture. Record call time, holds, peer wait and UI busy/refusal behavior. Maximum shape has no new worst-case latency promise; a captured slow operation is disclosed. It must still finish with a genuine result or typed refusal, without lost data, fabricated success or frozen event-loop work. The request UI shows a pending state rather than hiding work behind a spinner with no status. This is four screening samples, not another190-row timing campaign. Functional race/Stop/auth/durability regressions still run where relevant.

These numeric fixture thresholds are a reviewer-facing proposal chosen to make basic responsiveness testable. Seth approved replacing the strict old guarantee, not these specific numbers. Reviewer must accept or revise this small screen before implementation tests. Any material new work beyond a reproduced integration issue returns to Seth with its user-visible need and smallest alternative, rather than adding another storage redesign automatically.

## Finite capacity and evidence disclosure

Without R3, full source refs remain duplicated in request/version index metadata. The historical sizing probe measured293110 bytes for one fulfilled max-source request; it is not a product quota or a current per-request constant. More requests/versions and larger sources increase validation/write cost. No purge exists; deletion/export retains authored history. No replacement installation quota is chosen or implied.

Accepted evidence remains scoped: final max-source service A phases were roughly0.16-0.18s on this machine; final4MiB import full/held/peer maxima were approximately0.20-0.21s. The complete D4 final190 run passed with a stall sentinel. Earlier real misses, roughly1.1s unattributed stalls and instrument-invalid attempts remain in TICKET-20-D4-FINAL-GATE.md. These facts do not establish unlimited capacity or guarantee future tail latency.

## Current verification boundary and next work

This amendment changes documentation only. R2+D4 is independently FINAL ACCEPTED at220f3400: reviewer170 focused OK47.5s; builder437 artifact and1817 full (4 skips) pass;17 mutants assertion-killed; prior gate190 retained. No reduced operator/UI/transcript code has been implemented or accepted by this edit. Old R3 sidecar proposal196666c and reviewer no-sidecar/no-conversion ruling are preserved as historical/deferred material, not an active red-work instruction.

Next: independent reviewer checks this bounded20-22 contract/defaults/response policy/screen; root freezes the minimum operator signatures/error DTOs against existing code, then writes focused reds, implements the small flow, exercises it in the rendered browser and performs relevant regression plus one final full discovery. Review a frozen integrated release before activation/publication. No new agent creation, provider spend, external issue edit, deploy, activation or push is authorized by this documentation request.
