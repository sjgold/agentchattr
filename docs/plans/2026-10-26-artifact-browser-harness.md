# Reduced20 guarded browser acceptance design

Status: PROPOSED, reviewer clearance required before implementing/running the new acceptance fixture. No executable artifact browser harness exists yet and no acceptance run is claimed. The accepted Ticket19 tools are patterns, not evidence for these new paths.

## Scope and deliverables

|File / actor|Responsibility|
|---|---|
|tools/verify_artifact_ui.py|Parent fixture owner, generated server/local fake API responder/bootstrap, manifest, fixed controls, resource inventory/cleanup and receipts. --compile-only constructs no fixture/listener/process.|
|tools/fake_artifact_client.py|Owned hidden fake CLI, genuine MCP client/tool calls and transport release, fixed canned Markdown. No model/LLM execution.|
|tools/test_artifact_ui_harness_controls.py|Synthetic guard, capability, source/port/nonce, cleanup, lost-response and byte-verification controls. No real acceptance listeners/providers.|
|Traycer browser controller|Own isolated Chromium session via the existing traycer-browser REPL, actual UI clicks/typing, snapshots, desktop/mobile screenshots and bounded read-only observation.|
|Independent reviewer|Reviews executable tool/control/source hashes before the first run; separately drives/reproduces the bounded UI proof after root results.|

No Python production/backend edit, capability activation, live provider, personal browser/profile, installed-browser/native save-dialog parity, Linux/Omarchy/Desktop or whole-ticket release claim. The later responsiveness screen is separate; no0.270s gate campaign is revived here.

## Established local mechanisms

Read sources: tools/channel_guard.py install_guard(label); tools/verify_channel_lifecycle.py trusted_bootstrap_manifest(), guard_bootstrap(), Fixture ownership/env/port/cleanup pattern; tools/verify_runtime_crash_matrix.py verified process/resource helpers; process_identity.capture_birth/open_verified_process. Reuse audited guard/birth primitives, not the old channel scenario or wholesale fixture constructor.

The actual tools are chat_artifact_brief(brief_id), chat_artifact_submit(brief_id,markdown), then chat_queue_release(dispatch_id). The existing fake_channel_client demonstrates ClientSession + streamablehttp_client(settings URL/headers), initialize, call_tool and bounded timeouts. Artifact worker dispatch injection supplies the frozen brief/dispatch ids. wrapper_api uses the existing OpenAI-compatible /v1/chat/completions path; the fake endpoint implements its required response shape. These names are from current code, not invented endpoints.

## Fixture and isolation boundary

1. Freeze clean product/tool HEAD and SHA256s, including runtime_protocol.py, wrapper entry/worker files, UI sources, guard and new tools. Validate the trusted local .venv-windows interpreter/site-bootstrap manifest before any fixture process. Preserve the known post-site/native/DirEntry/ctypes guard limitations; this is not a Python/OS integrity attestation.
2. Create a unique retained root below .audit-tmp with data, uploads, profiles, records, audit, downloads and generated-code subdirectories. No deletion of existing fixtures/data. Parent owns a nonce and lease deadline (browser at most1200s, cleanup90s, not an ETA). Stop on first harness defect; retain every attempt.
3. Reserve distinct ephemeral127.0.0.1 ports for app, MCP transports and fake API, excluding known live ports8300/8200/8201/8301/8302 and configured repository ports. Config/data roots discovered only from the bounded repository config hash/read exception; never read user provider profiles. Retain config hashes, never config credentials. Close every reservation socket even on failure; before actions confirm the expected nonce/birth/port/source manifest, not just an open port.
4. Child env is an owned dictionary. Redirect HOME/USERPROFILE/APPDATA/LOCALAPPDATA/TEMP/TMP/XDG profile paths into the fixture, remove Python startup/user-site overrides, ambient provider credentials and HTTP_PROXY/HTTPS_PROXY/ALL_PROXY; set controlled NO_PROXY;, use only fixed fake provider config/dummy key, and set PYTHONNOUSERSITE. Never modify parent/user environment or installed settings. Guard policy lists forbidden real data/profile roots and live ports plus allowed Python roots, with the exact guard hash.
A fixture-only socket audit hook additionally restricts connects to the reserved owned-port allowlist. Install it after channel_guard and before product imports in every owned Python process; log readiness and a negative self-test. channel_guard itself remains unchanged. A forbidden connection invalidates the attempt. This covers audited Python connects, with the native-code limitations above.

5. Generated sitecustomize installs the same fail-closed guard before product/resource imports, exits91 on failure, and THEN patches runtime_protocol.SUPPORTED_CAPABILITIES=('artifact-v1',) only inside explicitly owned fixture Python processes. This includes the served app AND owned wrapper/worker children before manifest validation. Record pid/role/nonce/capability tuple and unchanged source hashes; the repository flag remains empty. A controlled capability-off phase changes only the fixture server gate, then restores it.
6. All generated controls exist only in this fixture server, outside /api/artifacts, require BOTH fixture nonce and operator token, and accept fixed operation enums/fixture-owned ids. No arbitrary path/port/config/expression payload. Logs sanitize tokens/headers; raw nonce/token stay in private fixture manifests, not portable report prose.
7. Own every process handle plus birth tuple before driving it; verify birth before cleanup/termination. No global kill-by-name/port or reused-pid action. Retain every guard record and self-test result. Any unexpected real attempt, wrong source hash, absent guard/capability record or unresolved child invalidates acceptance.

## Real app/source setup

Generated server loads a literal fixture configuration rather than production config/provider discovery and calls the actual app.configure and shared owners. Seed real catalogs for document-cli/document-api/peer, a frozen source template, real accepted-event messages/projection links and complete session rows through the actual stores. Seed one active source with accepted messages for Stop coverage, without a normal review model turn. These are synthetic source fixtures, not evidence of real multi-agent review generation.

Create an actual supported managed CLI seat and an actual API seat bound by the frozen session participant identity. API provider base_url points only to the owned local fake server; use a dummy fixture key, no ambient fallback. Producer manifest, launch fingerprint/nonce, queue ownership, packet/brief, outbox sealing, ACK and version persistence all follow existing production paths. No direct commit_version/seal fabrication in the acceptance flow.

The canned Markdown is deterministic and includes UTF8 BOM, CRLF, non-ASCII and literal script/img/javascript-link text. Record expected raw bytes/hash. Fake API completion count and CLI tool/injection records prove actual transport was exercised once. The receipt must prove zero fixture-owned model processes and provider-spend calls; it makes no machine-global process claim.

## Transport paths

- CLI: real managed wrapper/consumer receives artifact-v1 dispatch; fake client parses only assigned fixture brief/dispatch ids, reads its owned snapshot MCP settings, calls real MCP chat_artifact_brief and chat_artifact_submit, validates the ACK, then real chat_queue_release. It never calls chat_send or uses mutable chat as document input. Record exact tool names, ids, result hash, consumer and process births without secrets.
- API: real wrapper_api/ArtifactHTTP/complete_api_artifact fetches the accepted delivery, generates against the owned /v1/chat/completions responder, seals/persists/adopts its real outbox and settles transport. Record one fake generation and the admitted version hash/observation. A fixture gate can hold/release completion for queued/working/Cancel/Stop screenshots.
- Lost response: a fixture-only gate pauses capture after the genuine detached source read and outside engine/catalog, so the first authorized create worker can survive the browser's20s timeout. GET404 occurs before reserve; retry uses the same id/intent. Releasing the gate lets the real idempotent service choose one stored winner; prove one version/dispatch/generation for that id, not just matching canned JSON.

## Browser controller and visual proof

The available task browser API is tools.mcp__traycer_browser__repl with page.openSession({profile:'isolated',initialUrl:<observed READY URL>}), getByRole/getByLabel/locators, evaluate, snapshot, setViewportSize and screenshot. No guessed locator ids/URLs: use the emitted manifest and observed app DOM. Never attach primary/personal tabs. Close only the owned isolated session.

If browser and server hosts differ, use one tracked loopback forward using the browser-reported host id. Its port must remain the frozen app port so Host/Origin checks stay exact; if forwarding changes it, stop and refreeze rather than weakening auth. Keep all task forward ids in cleanup.

Browser network containment is distinct from Python channel_guard. Serve the actual product UI JS/CSS unchanged, add fixture-only CSP limiting resources/connect to owned loopback, block remote assets and replace the unrelated CDN marked script in fixture HTML with a disclosed local escape-to-text shim. The document reader never uses marked. Record that one HTML substitution and do not claim rich-chat renderer parity. No browser navigation to outside sites or personal origins; any needed browser capability must be confirmed before a run, never assumed.

The browser controller drives completed-session selection, instruction, Submit/double activation, Refresh, Cancel/Stop, Read, Download, archive/held selection, close/reload, keyboard focus and channel changes. Parent automation seeds fixed data, operates nonce-gated fake transport/fault gates, captures server/client/guard/count evidence and cleans resources. It does not inject UI actions or forge success DOM.

Capture one batched desktop1280x850 and mobile390x844 round, including real form/status/warning/reader content, bounding-box/overflow/focus/label checks. One bounded correction/confirmation round if defects arise; retain failed screenshots/source pins. Retain screenshot references and metadata from the browser tool transcript, plus hashes when image bytes are available; no undocumented screenshot save-path API is assumed. DOM live-region write observation may count unchanged poll writes; this is not a screen-reader/assistive-technology claim.

## Download capability boundary requiring review

The exposed Traycer page API documents no download-directory/event control. Do not invent Playwright download APIs or allow an uncontrolled write to Seth's Downloads directory.

Proposed bounded proof: install an explicitly recorded browser observer for createObjectURL and document.md activation, preserve the product's actual authenticated response.blob, hash its bytes in the browser, and intercept only the native save default to prevent an uncontrolled OS write. Transfer those exact observed Blob bytes to an owned nonce endpoint and save a comparison copy under fixture/downloads; verify BOM/CRLF/hash/filename and delayed URL revoke. This proves the rendered click/Blob path, not the OS save dialog/native download destination. Unit byte tests plus actual browser Blob observation are the proposed reduced acceptance evidence, consistent with Ticket19's native-dialog exclusions. If the reviewer requires an actual browser-native saved file, the run stays held until a supported isolated download-directory capability is supplied. This is an open review decision, not a claimed completed test.

## Fixed acceptance cases

|Case|Driven UI / real effect|Required evidence|
|---|---|---|
|CLI completed source|Request -> queued/working -> Ready -> literal Read and Download activation|Real MCP2 artifact tools/release, one version, byte/hash equality, no script/img execution.|
|API completed source|Same flow with bound API default author|One local fake API completion, real worker/outbox/ACK, matching exact Markdown.|
|Lost create / duplicate|Timeout, GET404, same-id retry, late save/reload adoption|Two POSTs same id, one request/dispatch/version/generation; no blind fresh id.|
|Definite refusal|Capability off, no-author/source/size/session/channel errors plus proxy error|Literal safe copy, draft editable, no false unknown on definitive4xx, no body/token storage.|
|Cancel and source Stop|Held fake completion, Cancel/Stop, status refresh and warning-only update|Durable cancellation; separate artifact warning/count/overflow; review state not made unresolved by artifact work.|
|Archived/held and peer|Archive through owned lifecycle; read retained document; switch to peer|Create disabled with reason; retained server-authorized actions; no old-channel response applied.|
|Read/download failure|One-shot verification503/proxy200 HTML, then refresh|No unverified text/file; exact authenticated Blob when successful.|
|Viewport/keyboard|Desktop+390px, labels, Escape/focus return, focus while list loading|Actual screenshots/boxes; no focus theft, clipped controls or false aria repeats.|

## Controls and execution gate

Design approval authorizes writing the new tools and running compile-only/synthetic controls. Before ANY acceptance process/listener/profile run, send the executable tools/control pin, source/tool/guard hashes and exact command for review. Controls must cover no fixture/resource construction, listener/process/network/profile work on import/compile (trusted module/source/hash reads remain allowed), guard bootstrap refusal/missing child guard, foreign root/port/nonce, real source flag unchanged, capability absent, safe config/env, malformed MCP binding, fake API egress refusal, timeout/lost response, mismatched byte/hash, partial construction/cleanup/birth mismatch and forbidden native-save destination. Tests must not count fixture errors as behavioral acceptance.

Expected commands once implemented and reviewed: python -m unittest tools.test_artifact_ui_harness_controls; python tools/verify_artifact_ui.py --compile-only; then the separately cleared browser-case command. Names are proposed interfaces, not existing executables.

Final receipt retains every attempt, pins/hashes, guard coverage/selftests/limitations, fixture-only capability records, actual CLI/API counts, UI assertions/screenshots, browser Blob versus native-save attribution, timing/retry observations and cleanup inventory. Cleanup visits every owned server/wrapper/client/fake endpoint/browser/forward, releases only verified owned resources and writes unresolved=[]. Any missing coverage/failure remains a failure; no silent retries/exclusions or source edits during the run.
