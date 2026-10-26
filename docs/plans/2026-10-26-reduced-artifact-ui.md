# Reduced Ticket 20 UI contract and implementation plan

> Execute inline with superpowers:executing-plans. Product scope is already approved in TICKET-20-22-REDUCED-RELEASE.md. This technical UI contract and ROOT reds require reviewer clearance before production UI edits.

Goal: request a document from a current or completed session, follow its real status, cancel, read verified Markdown literally and download the exact bytes.

Architecture: a small static/artifacts.js module owns the document panel and its timers. Existing static/sessions.js retains review orchestration and gains only the artifact cancellation warning/render-key and init hook. Use the existing app CSS variables and session-control styling. No framework/dependency, producer/source picker, Markdown renderer, revision browser, global library or activation.

## Design brief and chosen integration

- Operate/read inside the incumbent application: a Documents button next to the existing session launcher opens a section below the session bar. It stays reachable when no active session exists. A bounded20-item session select includes completed runs, More pages by20, and source-so-far is explicit for unfinished runs.
- Use one labeled instruction textarea, Request document, a live status/source/author card, Refresh/Cancel, and Read/Download once ready. The verified reader is a wrapping pre block with literal text, never rendered HTML. Empty/loading/refusal text explains the next available action. Closing returns focus to Documents; channel changes close the panel, cancel timers and ignore old replies.
- Reuse existing --bg-header/--bg-input/--text/--border/--accent/--radius-sm and focus-visible treatment. At390px, controls wrap and source/Markdown long lines wrap; no new visual world or typography. One embedded panel is the routine proposed implementation choice. A full modal adds focus machinery; a separate dashboard adds deferred navigation. Neither is needed for the approved flow.

## Files and frozen client seams

|File|Responsibility|
|---|---|
|static/artifacts.js (new)|window.ArtifactDocuments {init,open,close}; event-driven panel, requests/status/read/download, channel lifecycle and timers. No backend authority logic.|
|static/artifacts.css (new)|Scoped .artifact-* form/card/reader styles from existing tokens.|
|static/index.html|Documents button #artifact-documents-open near session-launch-btn, stylesheet/script (artifacts.js after sessions.js and before chat.js).|
|static/sessions.js|init calls ArtifactDocuments.init; renderStopControls uses artifact_cancellation in its cache key and shows its warning through textContent.|
|tests/test_artifact_ui.py (new ROOT)|Actual shipped JavaScript executed with Node vm and a minimal DOM/fetch/clock fixture, matching existing test_restart_ui practice. Unit evidence only.|
|Later browser acceptance harness|Isolated real rendered app and real supported fixture transports under Ticket19 guards; plan below.|

Frozen DOM: #artifact-documents-panel, #artifact-close, #artifact-session-select, #artifact-more-sessions, #artifact-instruction, #artifact-submit, #artifact-status, #artifact-source, #artifact-error, #artifact-refresh, #artifact-cancel, #artifact-read, #artifact-download, #artifact-reader. IDs are behavior-test seams, not a new external API. Controls use onclick/onchange/onsubmit or equivalent real DOM listeners; tests activate actual handlers. Status/errors have live/alert semantics; every input has a visible label.

## Network and state

Use only the accepted /api/artifacts routes with X-Session-Token, cache:no-store, same-origin relative URLs, no query token, no bearer, and JSON POST. Browser supplies POST Origin; do not forge it in client code. Request body EXACT {request_id,channel,session_id,run_id,instruction}. Mint a fresh Hex32 id per NEW submit. Disable double activation while awaiting a result. No automatic create retry. Preserve the request id when a response is lost or effects are unknown; Refresh queries that id, never blindly creates another request. Typed not_recorded refusal permits a new submission with a new id, including packet_exists. A recorded/current request in an error response updates the card; unknown effects remain explicit.

Only the latest known request/session/run IDs per channel may be retained in sessionStorage for same-tab reload status recovery. No token, source body, instruction or result body is stored there. This is not a library/history promise; earlier backend records remain intact. Restore by GET, not POST. Channel mismatch in a late status reply is never rendered in the current channel. Per-channel in-memory drafts can survive close/refusal; channel change clears verified reader text from view. Rename migrates metadata; deletion disposes it.

Status text follows the canonical table: Queued, Writing document, Ready, Cancelled, Stopped, Response rejected, Needs recovery, Imported history and Document could not be completed. Show author and compact source count/bytes/source-so-far. No raw audit/seal/launch identity. A retained verified read that later fails is hidden and marked unavailable. Cancel is offered for prepared/queued/active even when needs_resume, sends {} once, and uses returned current state/durability. Cancel never claims worker exit. Archive disables NEW create while retained status/read/download/Cancel remain subject to server authority.

Poll only a known live request every2s. Failure backs off4/8/16/30s, preserves last-known status with a visible unavailable note, and does not invent a terminal state. Success resets2s. Fulfilled/failed/cancelled/quarantined/imported, close, channel switch/deletion and disposed view stop polling. A sequence/generation guard ignores stale session-list/create/status/read responses. Manual Refresh remains available. A hidden/closed panel makes no background polling request.

Read uses the verified document endpoint then assigns markdown to textContent on pre. Script/img/link/javascript:/data:/entities remain literal. Download uses authenticated fetch, Blob and a temporary object URL with fixed filename document.md, revoking it after activation. It never navigates directly to an authenticated URL or appends a token. Network/verification refusal never downloads a fabricated file.

Refusals: preserve reviewed server error text/code. Capability-off says Artifact authoring is not enabled; no_author_available presents cause/author/examined roles without exposing bindings; packet_exists instructs a new request id; Needs recovery explains advanced recovery is outside this release. Use textContent for all server strings and author/session labels.

## Stop warnings

Existing review Stop status stays independent of artifact work. renderStopControls must include artifact_cancellation in its cache key and add a live textContent line for storage_unavailable, artifact_fence_failed, transport_unconfirmed and unconfirmed_overflow, plus known unconfirmed count. Warn that document cancellation is unconfirmed; never say the review is still running because an artifact is held. Immediate Stop reply and stop-status polling both use this renderer. Overflow is deliberately sticky until process restart; empty process-local reports do not prove remote termination. D8 preserves known IDs across re-Stop until terminal receipts.

## ROOT reds and reachability

One new ROOT file exercises the actual JS with a small DOM, deterministic fake fetch and clock, no listeners/providers. Two behavior reds are reachable today: Stop warning absent and render cache key ignores warning-only changes. The new artifact module and its UI behavior are infrastructure reds until static/artifacts.js exists; follow-on assertions are explicitly unobserved until then. Planned bodies cover completed list/pagination, exact fresh-id submit and double activation, typed/unknown effects, status/Cancel/terminal states, poll backoff/disposal, literal reader/download and refused read, channel/late-reply isolation, safe Stop warning repaint, module load/init wiring. Do not count a missing file as behavioral proof. Node unavailable is a blocking test environment finding, not a silent acceptance skip.

Rendered acceptance remains required even after vm green; no accessibility/layout/browser claim is made by the minimal DOM.

## Browser acceptance, Ticket19 isolation rules

Extend/reuse tools/channel_guard.py and the reviewed verify_channel_lifecycle bootstrap controls, with a new task-local fixture/nonce and source/tool hashes. Validate the trusted interpreter manifest first. Initialize real catalog/session/message/queue/artifact owners in a disposable root; no production paths/settings/history, real credentials or provider egress. Fixture-only capability patch, no runtime_protocol flag edit. Use a local fake API responder and fake CLI client with the REAL MCP artifact calls, genuine service/worker completion, retained receipts and counted cleanup. These are synthetic transports, not live-provider/Omarchy/Desktop evidence.

Use a Traycer-isolated rendered Chromium surface under the task's existing browser mechanism, not Seth's personal profile. Prove: completed-session create -> queued/working -> ready -> literal read and exact downloaded bytes; no duplicate POST on double activation; cancellation/Stop warning repaint; global capability-off refusal; 409/503/lost-response handling without duplicate create; reload-known-ID GET; archived/held channel behavior and peer channel unaffected; focus return/keyboard labels and390px fit/long lines. Screenshot desktop+mobile in one batched inspection, one correction pass if needed. Preserve all attempts/errors. Guard records must show no forbidden attempts, and cleanup must enumerate all servers/workers/clients/browsers/model processes with unresolved=[]; no live model usage.

## Ordered execution and proof

- [ ] Freeze contract and one ROOT red file, execute/record infrastructure vs behavioral reds and reachability; reviewer clears production.
- [ ] Implement only artifacts module/style and narrow index/session hooks; ROOT UI tests green with actual JS, mutation-check stale-reply/ID/auth/text/clock guards. Check existing session/restart/channel UI tests.
- [ ] Build/verify the isolated browser harness controls before use. Execute real desktop/mobile flow and both fixture transport paths under guard, retain raw receipts and cleanup.
- [ ] Independent UI review/rerun plus affected/full discovery as required for the final source. No open-ended timing campaign; the separately scoped responsiveness screen follows.
- [ ] Then transcript21, packaging22, reviewed activation, authorized cleanup last. Push remains gated.


## Observed ROOT red receipt, 2026-10-26

11 methods ran0.151s on accepted backend+c3a0bf3 D8 follow-up:3 FAIL,8 ERROR, no skips, no production UI edits. Real behavioral failures: existing Stop renderer omits the document cancellation warning; artifact-warning-only update leaves dataset.key unchanged at [1,"stopped",[],[],0]. The wiring assertion fails because index/init references do not yet exist (infrastructure integration red). Eight methods raise FileNotFoundError for static/artifacts.js; their subsequent fetch/DOM/state assertions are unobserved until that declared module exists.

Reachability after the module exists: open()/init must create the declared controls and complete the real event handlers; then tests exercise authenticated completed listing/paging, exact id/body submit, double-submit/unknown result, timers/backoff/terminal disposal, status/Cancel, verified literal read/blob download, fixed capability refusal/failed verification, and stale response after channel switch. No test catches a product assertion inside a broad production exception handler; node failures are checked after the script returns. Node absence is a blocking test setup failure.

Raw local receipt: .audit-tmp/reduced20-ui-first-red.txt. This is unit/component evidence, not rendered acceptance. No claim that unexecuted bodies are already valid/complete; a fixture defect found when newly reachable must be labeled, repaired and re-exercised before green acceptance. Reviewer executes/audits this pin before UI source.

Raw receipt SHA256: ae48a1caa6fb48f5df42c336fc2bb602b6fdec52610ee1fd2d162fc86a24ec84
