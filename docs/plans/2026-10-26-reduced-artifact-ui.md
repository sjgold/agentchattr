# Reduced Ticket 20 UI contract and implementation plan

## Latest scope decision, 2026-10-26

Seth's words, relayed verbatim by the reviewer: "id never needed phone width this is an internal only tool... speed is open as well as long as agents are not taking forever it should be fine".

This supersedes the earlier phone-width, numeric responsiveness-screen and pre-activation visual requirements. Drop the390px/mobile gate, all new numeric speed gates and tools/screen_artifact_release.py (never created). No more browser-harness work or measurement campaign. Existing correctness/security/provenance/idempotency/Stop/durability and regression tests stay. Speed is the stated practical requirement that agents are not taking forever. Browser evidence remains partial and its receipts remain false/incomplete; no visual acceptance is invented. A desktop look by Seth is optional, not a blocker.

Next order: Ticket21 transcript ->22 packaging -> separate activation commit for reviewer -> final approved file cleanup -> publication only with Seth's explicit push authorization. No deletion without his explicit yes. Historical timings, attempt records and superseded proposals remain as history; their old gates no longer apply to this release.

> Execute inline with superpowers:executing-plans. Product scope is already approved in TICKET-20-22-REDUCED-RELEASE.md. This technical UI contract and ROOT reds require reviewer clearance before production UI edits.

Goal: request a document from a current or completed session, follow its real status, cancel, read verified Markdown literally and download the exact bytes.

Architecture: a small static/artifacts.js module owns the document panel and its timers. Existing static/sessions.js retains review orchestration and gains only the artifact cancellation warning/render-key and init hook. Use the existing app CSS variables and session-control styling. No framework/dependency, producer/source picker, Markdown renderer, revision browser, global library or activation.

## Design brief and chosen integration

- Operate/read inside the incumbent application: a Documents button next to the existing session launcher opens a section below the session bar. It stays reachable when no active session exists. A bounded20-item session select includes completed runs, More pages by20, and source-so-far is explicit for unfinished runs.
- Use one labeled instruction textarea, Request document, a live status/source/author card, Refresh/Cancel, and Read/Download once ready. The verified reader is a wrapping pre block with literal text, never rendered HTML. Empty/loading/refusal text explains the next available action. Closing returns focus to Documents; channel changes close the panel, cancel timers and ignore old replies.
- Reuse existing --bg-header/--bg-input/--text/--border/--accent/--radius-sm and focus-visible treatment. Controls and long source/Markdown lines wrap; no new visual world or typography. One embedded panel is the routine proposed implementation choice. A full modal adds focus machinery; a separate dashboard adds deferred navigation. Neither is needed for the approved flow.

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

Use a Traycer-isolated rendered Chromium surface under the task's existing browser mechanism, not Seth's personal profile. Prove: completed-session create -> queued/working -> ready -> literal read and exact downloaded bytes; no duplicate POST on double activation; cancellation/Stop warning repaint; global capability-off refusal; 409/503/lost-response handling without duplicate create; reload-known-ID GET; archived/held channel behavior and peer channel unaffected; focus return/keyboard labels and long lines. Historical browser proposal, superseded by the latest scope decision above. Preserve all attempts/errors. Guard records must show no forbidden attempts, and cleanup must enumerate all servers/workers/clients/browsers/model processes with unresolved=[]; no live model usage.

## Ordered execution and proof

- [ ] Freeze contract and one ROOT red file, execute/record infrastructure vs behavioral reds and reachability; reviewer clears production.
- [ ] Implement only artifacts module/style and narrow index/session hooks; ROOT UI tests green with actual JS, mutation-check stale-reply/ID/auth/text/clock guards. Check existing session/restart/channel UI tests.
- [ ] Build/verify the isolated browser harness controls before use. Prior partial browser evidence and raw receipts/cleanup are retained; no new browser runs.
- [ ] Independent UI review/rerun plus affected/full discovery as required for the final source. No open-ended timing campaign; the proposed responsiveness screen is withdrawn.
- [ ] Then transcript21, packaging22, reviewed activation, authorized cleanup last. Push remains gated.


## Observed ROOT red receipt, 2026-10-26

11 methods ran0.151s on accepted backend+c3a0bf3 D8 follow-up:3 FAIL,8 ERROR, no skips, no production UI edits. Real behavioral failures: existing Stop renderer omits the document cancellation warning; artifact-warning-only update leaves dataset.key unchanged at [1,"stopped",[],[],0]. The wiring assertion fails because index/init references do not yet exist (infrastructure integration red). Eight methods raise FileNotFoundError for static/artifacts.js; their subsequent fetch/DOM/state assertions are unobserved until that declared module exists.

Reachability after the module exists: open()/init must create the declared controls and complete the real event handlers; then tests exercise authenticated completed listing/paging, exact id/body submit, double-submit/unknown result, timers/backoff/terminal disposal, status/Cancel, verified literal read/blob download, fixed capability refusal/failed verification, and stale response after channel switch. No test catches a product assertion inside a broad production exception handler; node failures are checked after the script returns. Node absence is a blocking test setup failure.

Raw local receipt: .audit-tmp/reduced20-ui-first-red.txt. This is unit/component evidence, not rendered acceptance. No claim that unexecuted bodies are already valid/complete; a fixture defect found when newly reachable must be labeled, repaired and re-exercised before green acceptance. Reviewer executes/audits this pin before UI source.

Raw receipt SHA256: ae48a1caa6fb48f5df42c336fc2bb602b6fdec52610ee1fd2d162fc86a24ec84


## Production clearance and U1-U9 rulings, 2026-10-26

Reviewer independently confirmed11 reds atc685f9a6 and CLEARED bounded UI production. Browser acceptance is a NEW package deliverable, not an existing executable flow. No browser acceptance is claimed by the unit implementation below.

U1 superseded after a concrete concurrency correction: asyncio.to_thread(create) continues after a client abort; GET404 proves absence only at read time. Unknown/timed-out create retains the SAME id and intent through404, Refresh, reload and retry.404 says Not found yet (the earlier request may still finish). A fresh id requires a definitive not_recorded create refusal, explicit409 packet_exists, or warned Abandon and start new with the literal The earlier request may still finish and could create a second document. This is a deliberate user choice, never an automatic retry. Both200 replay and202 create read the request property identically.

Reload preserves latest id/channel/session/run plus instruction_sha256, unknown and intent_channel metadata. Raw instruction/source/result/token are never stored in sessionStorage. In-memory drafts survive close/channel navigation; reload replay requires re-entering the original instruction and matching its digest. Unknown retry after rename uses intent_channel from the original immutable intent while the card follows the current channel. Mismatched instruction refuses without a POST; Refresh still works. This was disclosed to the reviewer as the way to satisfy same-intent recovery without raw body persistence.

U2: each fetch/body read has a20s AbortController plus raced deadline, so even a transport that ignores abort cannot leave controls busy forever. Create timeout is unknown, poll timeout preserves last status and backs off. U3: fixed fallback copy for all contracted codes/non-JSON proxies; reviewed server literals and author/cause/durability are textContent only. Successful HTML proxy downloads are refused rather than saved as fabricated Markdown. U4: cancellation warning is sticky per current request/view because public status has no transport confirmation; a manual Refresh does not erase it. Only an explicit transport_settled true observation or leaving the view clears it. No dispatch ids are invented when the DTO supplies only a warning.

U5: state+reason derives all labels, with Needs recovery only for live rows. Imported history with/without a version is distinct. U6: latest request only, with the visible earlier-requests-not-listed/may-still-run disclosure. Card source names the actual saved session even if the form selects another source. U7: canWrite AND ownerAvailable(artifacts) disable Create with a literal reason; retained Cancel/read/download keep server authority. U8: session pages dedupe by session_id and show actual state. U9: downloads use response.blob, preserve BOM/CRLF and fixed document.md, and revoke URLs after activation. Reader text is never a download source.

Stop UI includes artifact_cancellation in the render key (no updated_at timestamp), handles null/no-warning without a false line, reports all warning codes/counts and repaints through handleSessionEvent. Escape closes and returns focus; labels, aria-live, role alert and aria-expanded are explicit. Node DOM removes/deregisters descendants and supplies Option/createTextNode so detached ids cannot make tests falsely pass.

## Actual component verification

Original production attempt reached all11 existing bodies:9 passed,2 failed. One real defensive label issue was terminal Cancelled retaining a stale needs_resume flag; text derivation now restricts Needs recovery to live rows. The load/init substring assertion was a fixture weakness: optional chaining correctly called init but failed the substring. Replaced it with parsed HTML script/CSS/order/button checks and an actual sessions init spy, preserving the original wiring intent.

Strengthened17-case run exposed the missing Escape action and the defensive Cancel label; after fixes20 cases passed. Additional observed red:200 HTML download proxy must not create a file (1FAIL0.057s), fixed with media verification. Additional observed red: closing the panel must retain an in-memory draft (1FAIL0.055s), fixed without body persistence. Final UI+existing restart UI result and mutation receipt are recorded in the final component handoff; no rendered/viewport/assistive-technology claim.

The first mutation attempt was INSTRUMENT-INVALID for long-source cases: passing source overrides in node -e exceeded Windows CreateProcess length (WinError206). Retained as artifact-ui-mutations-instrument-invalid.json; those ERROR records are not valid kills. Harness now sends the script through stdin to node -, source rewrites stay in vm only, and ERROR-only results do not count as kills. All final mutations must have assertion failures and unchanged source hashes.

Impeccable context used the incumbent code/tokens (no PRODUCT/DESIGN rewrite or new interview; product scope already approved). The mechanical detector ran once across the edited page and found15 aggregate warnings (contrast/padding/glow/text size). No clean-page claim: old shared page styles are outside this feature, and rendered contrast/layout still need the guarded desktop/mobile pass. New document notes/placeholder use foreground contrast instead of dim text. No dependencies installed, no provider/browser/profile used by the component tests.


## Frozen unit component handoff

22 actual-JS artifact UI tests plus the existing restart UI case:23 tests OK1.249s.20 valid vm-source mutations killed, all by assertions, zero ERROR-only; source hashes unchanged. Node --check passed for artifacts.js and sessions.js; git diff --check clean. No Python production/backend bytes changed from the accepted D8 pin. Browser, full-project final source verification and UI acceptance remain pending.

The new browser package files are explicitly planned as tools/verify_artifact_ui.py (guarded fixture/bootstrap/manifest/cleanup and compile-only mode), tools/fake_artifact_client.py (local fake CLI using the REAL MCP tool), and tools/test_artifact_ui_harness_controls.py (synthetic guard/fixture/cleanup controls before any run). A local fake API responder is generated inside the fixture by the verifier. All new executable harness source, its guard/manifest/tool hashes and exact run commands must be reviewed before running any acceptance fixture. The existing verify_channel_lifecycle is a pattern, not proof that these new flows already exist. Runtime capability stays fixture-patched only. The responsiveness script is a separate later deliverable.

Final component verification receipt (summary; raw local outputs retained):

```json
{
  "kind": "actual UI source mutated only in Node vm",
  "source_hashes": {
    "static/artifacts.js": "bc536c2a57a4afc01481d62ce79306c1911ed73a17d6e0427fa67bbb73bdf26a",
    "static/sessions.js": "3e342750daf29d18f3830699e1a16d4adaef06a44587eee11ae4759c7f9cbe10",
    "static/artifacts.css": "08909e7d0ed4d145948b31b7ba025cac1fb1b0c79c40ac2b00465b5356e8df2d",
    "static/index.html": "8e4198618e55f4c9762cefe1ddc0b314d83ec0e2aec89b24fe21df078685b558",
    "tests/test_artifact_ui.py": "efb4366fc11f3625d85a7bc4731fd3719e2ce5c7ff9eeb69fe6f3746bed16567"
  },
  "checks": [
    {
      "label": "operator auth header",
      "test": "test_completed_session_list_and_more_are_authenticated",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "lazy rotated token",
      "test": "test_unknown_reload_retry_requires_original_instruction_and_lazy_token",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "double submit",
      "test": "test_double_activation_and_unknown_effect_keep_same_request_id",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "unknown same intent",
      "test": "test_double_activation_and_unknown_effect_keep_same_request_id",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "unknown404 retains id",
      "test": "test_double_activation_and_unknown_effect_keep_same_request_id",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "reentered instruction proof",
      "test": "test_unknown_reload_retry_requires_original_instruction_and_lazy_token",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "twenty second deadline",
      "test": "test_deadline_get404_late_save_and_reload_keep_unknown_identity",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "terminal poll stops",
      "test": "test_poll_backoff_terminal_and_close_dispose_timers",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "backoff cap",
      "test": "test_poll_backoff_terminal_and_close_dispose_timers",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "close cancels timer",
      "test": "test_poll_backoff_terminal_and_close_dispose_timers",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "cancel warning sticky",
      "test": "test_all_status_texts_and_cancel_warning_survive_manual_refresh",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "literal reader",
      "test": "test_verified_reader_is_literal_and_download_is_exact_blob",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "binary download bytes",
      "test": "test_verified_reader_is_literal_and_download_is_exact_blob",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "no body persistence",
      "test": "test_verified_reader_is_literal_and_download_is_exact_blob",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "download response integrity",
      "test": "test_download_rejects_proxy_html_without_creating_a_file",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "in-memory draft survives close",
      "test": "test_draft_survives_close_in_memory_without_browser_body_storage",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "channel disposal",
      "test": "test_channel_change_and_late_response_do_not_leak_other_channel",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "owner availability",
      "test": "test_archived_held_policy_labels_keyboard_and_latest_only_disclosure",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "Stop warning display",
      "test": "test_stop_warning_is_literal_and_distinct_from_review_outcome",
      "killed": true,
      "failures": 1,
      "errors": 0
    },
    {
      "label": "Stop warning render key",
      "test": "test_stop_warning_only_update_invalidates_render_cache",
      "killed": true,
      "failures": 1,
      "errors": 0
    }
  ],
  "source_unchanged": true,
  "pass": true
}
```

```text
.......................
----------------------------------------------------------------------
Ran 23 tests in 1.249s

OK

```

## Y-1 through Y-7 follow-up, 2026-10-26

Reviewer accepted component ae4ab08f pending these bounded changes. Definitive first-attempt JSON 4xx pre-effect refusals clear the unknown state and leave the draft editable; client validation checks blank/control text and the 32768-byte UTF-8 limit. A previously unknown attempt retains its original identity when a later refusal cannot settle the earlier worker. GET 404 still never permits an automatic new id.

Request/version paths encode ids; versions require hex validation. Stored instruction digests include request_id. Live text updates only on change; delayed session loading preserves user focus. Polling pauses while the document is hidden. Refresh cannot race Cancel. Cancel not_found does not fabricate a worker warning. Session-list retry clears its prior error. Stop warning copy handles zero and one dispatch. Blob URLs revoke after one second or on close. A stale download failure cannot overwrite a newer request card. Script versions are sessions233/artifacts2.

Observed follow-up reds included eight failures in the 29-case run and a separate stale-download failure (0.060s). Final UI/restart selection: 39 tests OK in 2.453s. JS syntax and git diff checks pass. Final mutation receipt: 61/61 assertion-killed, zero errors, source unchanged. Raw receipt: .audit-tmp/artifact-ui-mutations.json; console: .audit-tmp/reduced20-ui-y-mutations-output.txt. Earlier survivors and the incorrect mutation anchor are retained; controls were strengthened/retargeted, product safeguards were preserved.

Harness honesty: each Node case must emit exactly one completion marker, so an unresolved fake promise cannot count as success. Conditional stale read/list/create defenses use explicit in-VM removal of the single-flight entry guard to reach their independent guards; these are fault-injection cases, not claims that normal UI actions allow parallel reads. All other UI tests execute the actual source with fake DOM/network/clock. None is rendered-browser acceptance.

Next owner: root implements the browser harness only after review of docs/plans/2026-10-26-artifact-browser-harness.md. That DESIGN proposes real MCP fake-CLI and local fake-API flows with fixture-only capability, owned guards/resources and desktop/mobile proof. The browser API exposes no isolated download-directory control: actual Blob/click observation with native save intercepted is an explicit open review decision. No browser acceptance process, listener, profile or harness execution has started. Executable tools and controls require a second pin review before acceptance runs. Screen, transcript21, packaging22, activation and cleanup remain later; no push.


Follow-up review: UI7d962b07 independently ACCEPTED (reviewer39 tests OK2.5s,61 mutants killed). Browser DESIGN approved for tools/synthetic controls with H-1..H-6 folded; bounded native-default-intercepted Blob proof accepted, no saved-file claim. Tools are now implemented with28 synthetic controls/compile green, awaiting executable review before any acceptance resources. Current action and hashes are in the browser harness design.
