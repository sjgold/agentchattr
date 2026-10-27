# Reduced20 guarded browser acceptance design

## Latest scope decision, 2026-10-26

Seth's words, relayed verbatim by the reviewer: "id never needed phone width this is an internal only tool... speed is open as well as long as agents are not taking forever it should be fine".

This supersedes the earlier phone-width, numeric responsiveness-screen and pre-activation visual requirements. Drop the390px/mobile gate, all new numeric speed gates and tools/screen_artifact_release.py (never created). No more browser-harness work or measurement campaign. Existing correctness/security/provenance/idempotency/Stop/durability and regression tests stay. Speed is the stated practical requirement that agents are not taking forever. Browser evidence remains partial and its receipts remain false/incomplete; no visual acceptance is invented. A desktop look by Seth is optional, not a blocker.

Next order: Ticket21 transcript ->22 packaging -> separate activation commit for reviewer -> final approved file cleanup -> publication only with Seth's explicit push authorization. No deletion without his explicit yes. Historical timings, attempt records and superseded proposals remain as history; their old gates no longer apply to this release.

Status: FINAL attempt5 stopped at screenshot host failure after real CLI polling/read/exact Blob proof. Cleanup unresolved=[]; original files/known ports unchanged, one unrelated-to-owned-birth Python baseline addition retained. Full12-case acceptance incomplete. No further adaptation; reviewer disposition pending.

## Final Electron mechanism: fixture-served visibility reads (review pending)

Reviewer classified attempt4 as a harness-mechanism failure and the first clean RAW cleanup. Attempts1-4 remain retained. Chrome/Edge tooling is parked; it requires Seth's request. ONE fifth and LAST Electron attempt is the chosen mechanism, pending executable-delta clearance. A further browser-environment failure ends adaptation and returns the partial evidence/remaining coverage decision to Seth through the reviewer. No automatic rerun.

Observer now only captures native hidden/visibilityState/hasFocus and POSTs them, without redefining document properties. It installs window.__artifactFixtureHidden(), returning false with --simulate-visibility and the native document.hidden otherwise. Only the exact fixture /static/artifacts.js response is substituted: the pinned original SHA25696020b32c44626e5c6fc6c66da7498874640211d19cdb9328e380363b32701ac must match and exactly3 document.hidden byte tokens are replaced with window.__artifactFixtureHidden(). Exact-byte controls prove the replacement is the entire difference. Every other static response and all product files on disk remain unchanged.

The response writes records/served-artifacts.json with original_sha256, served_sha256 and replacement_count=3. Receipt and summary include this proof alongside the native values and visibility_simulated:true. Finish refuses a missing served-route record or differing hashes/count, missing native disclosure or incomplete cases. Required claim: "no native foreground/visibility parity; fixture-served artifacts.js with document.hidden reads replaced". The product hidden-page guard remains proven by the unchanged Node UI tests; the simulated browser run exercises the substituted reads. Native visibility and native saved-file parity remain outside the claim.

The real-page VM now defines NON-configurable own hidden/visibilityState getters. Before the fix, the actual old observer failed with TypeError: Cannot redefine property: hidden; raw .audit-tmp/attempt5-nonconfigurable-observed-red.json. Afterward OFF/ON pass while both native getters remain untouched. Missing substitution, two-of-three substitution and extra bytes each kill the exact-byte test by one assertion, zero errors. OFF forced visible, ON disabled, native capture dropped and observer installed late each fail the actual-page VM. Seven raw reversion results: .audit-tmp/attempt5-served-substitution-reds.json.

Verification:63 harness controls plus39 unchanged UI/restart tests,102 total OK5.555s; compile-only constructs no acceptance resources. No product/capability changes. No fifth listener/profile/browser has started. Next owner reviewer: rerun controls/reds with trusted Python and review this delta before authorizing ONE --run --simulate-visibility. Existing fresh baseline/root/distinct attempt5 output, per-case startup precondition, all12 cases, stop-on-first-failure, disclosure, token scans and birth-based cleanup conditions remain in force. No push; delivery cleanup remains last.

## Scope and deliverables

|File / actor|Responsibility|
|---|---|
|tools/verify_artifact_ui.py|Parent fixture owner, generated server/local fake API responder/bootstrap, manifest, fixed controls, resource inventory/cleanup and receipts. --compile-only constructs no fixture/listener/process.|
|tools/fake_artifact_client.py|Owned hidden fake CLI, genuine MCP client/tool calls and transport release, fixed canned Markdown. No model/LLM execution.|
|tools/test_artifact_ui_harness_controls.py|Synthetic guard, capability, source/port/nonce, cleanup, lost-response and byte-verification controls. No real acceptance listeners/providers.|
|tools/artifact_page_init_control.js|be599be131c894b934d2e63f809dca131faff51373ae298b1172891599d4649f|
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
4. Child env is an owned dictionary. Redirect HOME/USERPROFILE/APPDATA/LOCALAPPDATA/TEMP/TMP/XDG profile paths into the fixture, remove Python startup/user-site overrides, ambient provider credentials and HTTP_PROXY/HTTPS_PROXY/ALL_PROXY; set controlled NO_PROXY, use only fixed fake provider config/dummy key, and set PYTHONNOUSERSITE. Never modify parent/user environment or installed settings. Guard policy lists forbidden real data/profile roots and live ports plus allowed Python roots, with the exact guard hash.
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

## Approved bounded download proof

The exposed Traycer page API has no isolated download-directory/event control. The reviewer approved this bounded claim: the rendered click performs authenticated fetch -> response.blob() -> object URL, anchor.download=document.md; browser-observed Blob bytes match the expected hash/BOM/CRLF and the URL is revoked after the delay. Hash the Blob inside the browser BEFORE transfer, then hash again at the nonce endpoint and compare both with expected bytes. Intercept only the native anchor save default, log the patch and disclose this observer effect. Filename evidence is product intent, not an OS result. No claim that a file was saved or that a save dialog/destination/other browser works. A guarded browser-native save is a separate optional proposal, unnecessary for reduced acceptance.

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

Expected commands once implemented and reviewed: python -m unittest tools.test_artifact_ui_harness_controls; python tools/verify_artifact_ui.py --compile-only; then the separately cleared browser-case command. These interfaces are implemented; --run remains held pending executable clearance.

Final receipt retains every attempt, pins/hashes, guard coverage/selftests/limitations, fixture-only capability records, actual CLI/API counts, UI assertions/screenshots, browser Blob versus native-save attribution, timing/retry observations and cleanup inventory. Cleanup visits every owned server/wrapper/client/fake endpoint/browser/forward, releases only verified owned resources and writes unresolved=[]. Any missing coverage/failure remains a failure; no silent retries/exclusions or source edits during the run.

## H-1 through H-6 executable requirements

- Child propagation: remove inherited Python overrides first, then set an explicit owned PYTHONPATH containing generated bootstrap and this frozen repository. PYTHONNOUSERSITE does not disable sitecustomize. Product wrapper/fake-client launch must inherit that exact path plus CHANNEL_FIXTURE_ROOT, CHANNEL_GUARD_POLICY, CHANNEL_FIXTURE_NONCE and the artifact guard marker. sitecustomize installs guard and owned-port audit hook before first runtime_protocol import, then applies capability. Every entry validates its current process guard record; a child lacking it exits91 before product/resource work. Synthetic control exercises the missing-marker refusal. Wrapper environment construction will be checked against the actual launcher, not assumed.
- Step budgets: startup90s; ordinary UI calls30s; lost-create observation20s product timeout plus10s margin; status windows permit observed2/4/8/16/30s backoff (a bounded100s observation, reset at2s after success); Blob revocation window1-5s; Cancel/Stop30s each; transport completion90s. Wide windows plus counts, no exact scheduler claims. All stages share the1200s lease; cleanup90s is separate.
- Secrets: never serialize SESSION_TOKEN or nonce into browser evaluations/snapshots/page source. Sanitized DOM-only observations exclude script source. Before accepting any exported transcript/screenshot metadata/evidence/receipt, scan for exact token and nonce; refuse/redact token-bearing strings with a synthetic control. Raw private fixture manifests remain local. Screenshot pixels are checked visually for visible secrets; absent image bytes are recorded as observed in transcript only, with no hash claim.
- Fixed fixture endpoints outside /api/artifacts: GET /__artifact_fixture/state; POST /__artifact_fixture/control; POST /__artifact_fixture/blob; POST /__artifact_fixture/evidence (bounded fixed-case observations, secret-scanned). Every endpoint requires operator token plus fixture nonce, no query authorization, strict bounded payload. Control actions are fixed enums only. Frozen owned ports include app/control/blob listener, MCP HTTP/SSE and local fake API. Generated CSP connect-src names the exact frozen/forwarded app origin and fake API as needed; changing the forwarded port requires refreeze. Controls reject a loopback-but-unowned port, prove capability remains absent if guard fails, scan receipt secrets and reject an unowned CSP origin.
- Scenario allocation: rendered cases additionally cover backoff/reset counts; document-hidden/closed polling pause; RENAME/DELETE metadata migration/disposal; reload retaining id/digest and no POST before re-entry; stale download failure; Refresh versus Cancel; unchanged live-region writes. Existing component tests remain the detailed fault matrix; rendered receipts identify any case that is not reached rather than borrowing a unit pass. A no-author fixture session binds a fixed absent identity instead of an arbitrary live seat. CLI completion gate pauses BEFORE chat_artifact_submit, after the genuine brief read; transport release follows real submit ACK.
- Screenshots: retain returned references/metadata, hash bytes only when supplied. No undocumented save API and no hash-verification claim for transcript-only images.

## Executable review package, 2026-10-26

Implemented tools/verify_artifact_ui.py, tools/fake_artifact_client.py and tools/test_artifact_ui_harness_controls.py. Synthetic28 tests pass; compile-only passes with no fixture/listener/process/profile construction. No real server, managed child, local fake API listener or browser has been started for this package. Native guard reach, source seeding and actual flows remain unobserved until the separately approved run. Controls include structural checks alongside behavioral synthetic checks; they do not prove native timing/transport behavior.

Parent start creates the fixed fixture then launches genuine managed seats and waits for readiness before emitting READY.json. Gate operations use --control ACTION --fixture-root OWNED_ROOT; the tool reads local private credentials itself and prints scanned output, keeping them out of tool arguments. Browser observations go through the injected closure helper __artifactFixtureReport with a fixed case and bounded observations. It scans secrets server-side. Raw token/nonce never appear in public READY/receipt. The WebSocket URL carries the normal product token, so the fixture suppresses server access/INFO logs and browser exports exclude script/network-URL dumps.

The original checkout's data/uploads roots and current worktree data are forbidden. Each generated bootstrap enables capability only after guard success; managed launch inherits the explicit environment, fake CLI strip_env=[] preserves it. A protocol-level JSON refusal with MCP isError=false is still refused: exact assigned brief, admitted ACK/event/hash and released dispatch are checked before proceeding. CLI records only hashes/ids and observed console visibility.

Execution commands proposed for review (the last two remain HELD):

```powershell
$env:PYTHONPATH='.'
& 'C:/Users/SJG/Documents/CodePlayground/agentchattr/.venv-windows/Scripts/python.exe' -m unittest tools.test_artifact_ui_harness_controls
& 'C:/Users/SJG/Documents/CodePlayground/agentchattr/.venv-windows/Scripts/python.exe' tools/verify_artifact_ui.py --compile-only
# HELD until executable review clears the pin:
& 'C:/Users/SJG/Documents/CodePlayground/agentchattr/.venv-windows/Scripts/python.exe' tools/verify_artifact_ui.py --run
# Fixed gate/state operation while that owned run is alive, using emitted root:
& 'C:/Users/SJG/Documents/CodePlayground/agentchattr/.venv-windows/Scripts/python.exe' tools/verify_artifact_ui.py --control state --fixture-root '<READY root>'
```

The isolated browser controller supplies the actual cases/screenshots and closes its owned browser/forwards. A finish marker stops the parent lease but is never an acceptance pass; receipt acceptance_claim stays false for reviewer assessment. Parent cleanup visits child/server births even after a mismatch, records unresolved resources, and retains the root. No native-save claim. The screenshot/secret scan and explicit controller cleanup evidence are required before acceptance, not inferred from parent completion.

Frozen executable source SHA256s:

|File|SHA256|
|---|---|
|tools/verify_artifact_ui.py|e3a3afc223c5bedd352cc01c2109112f3b4b894229f9a721a257df66877e1676|
|tools/fake_artifact_client.py|57f8232969d0456827b1f19577bb2a780bda0a6435786917d8c6b100b82f6895|
|tools/test_artifact_ui_harness_controls.py|bc10a2771e0b323dd95b9f6b8c55e3255eef8e93e2aecb0f33080b6dabdb00c1|
|tools/artifact_page_init_control.js|be599be131c894b934d2e63f809dca131faff51373ae298b1172891599d4649f|
|tools/channel_guard.py|76fde78539634a7f1c4ef687f59afcddc82bd12de0aeb4c5e01f73649b23a927|
|runtime_protocol.py|b770452455bcd48b1f50c5f306469aca328e9946292e58b83cd3e9e5cde69b01|

Final synthetic check:28 tests OK0.184s; compile-only OK. Parent/control HTTP explicitly bypasses ambient proxies without editing the host environment. No acceptance resources started.

## dfecc78 review corrections: B-1/B-2 and C-1 through C-8

The reviewer ran28 controls and withheld execution. Read-only probes confirmed Python3.14 uses the pure-Python socketpair fallback and the worktree has no .venv-windows. No acceptance attempt was started. Five new control bodies first errored on four missing harness helpers and the unhandled private.json replace race (5 errors0.008s). Corrected final controls:42 tests OK0.902s, including three real bootstrap-only child processes. Compile-only passes. These real controls were explicitly requested by review; they start no app, MCP/provider listener, managed seat or browser. The only temporary listener is stdlib socketpair itself. All children ended via communicate, with observed codes0 (good),91 (bad guard),92 (expired lease); control roots/results are retained locally.

- B-1: socket.socketpair is wrapped with thread-local state. The audit hook permits loopback bind0 only while that wrapper executes, records that actual listener object, and allows only the subsequent connection to its exact bound port. Forbidden ports remain forbidden. The exception is removed on return/error. A REAL guarded child creates/closes a new event loop, completes asyncio.run and proves a plain unowned-port connection is refused. This replaces the earlier inadequate check_address-only control.
- B-2: trusted_manifest resolves the original checkout from the worktree Git common directory. Only its exact .venv-windows interpreter/prefix is accepted, with the existing fixed site hashes plus executable hash recorded; both original/source-worktree paths are in the receipt. No venv/junction is created. Original and worktree config files receive bounded hash/port/data-root discovery, and both installations' data/uploads/.agentchattr plus discovered data dirs are forbidden.
- C-1/C-3: every guarded Python process gets a parent-birth/1200s lease watchdog. It requests orderly server shutdown through the registered callback, with five-second forced-exit fallback; children independently exit if the parent is gone or lease expires. Parent records its Popen birth immediately, and a bootstrap-installed Popen subclass records product-launched children before relying on their own bootstrap record. Failure to journal a spawn stops only the handle just returned by that Popen. A standalone --control cleanup remains available after lease expiry/source changes and visits signed owned births, preserving mismatches as unresolved. Native venv launcher births are tracked separately from guarded interpreter births; launcher shims need no false guard-coverage claim. Control tests cover parent birth status/handle closure, real expired-lease exit92, missing-bootstrap spawn capture, journal-failure containment and continue-after-mismatch cleanup.
- C-2: atomic JSON replacement retries PermissionError at most10 attempts with20ms spacing; readers tolerate the same bounded Windows race. Writer/reader controls exercise it.
- C-4: a private sibling registry under .audit-tmp/artifact-ui-owners records the exact created root/manifest digest and a per-root signing key. Pre-planted roots without that registration are refused before networking/process control. Manifest ports exclude forbidden/configured ports, private config/nonce/ports bind to the creator manifest, and birth journals are HMAC-checked before PID authority. This protects against target-root tampering/preplanting; it does not defend against the OS user or an attacker who can also alter the sibling registry/process environment. Tests cover preplant refusal, forbidden ports and birth tampering. The registry is local secret state and is never exported.
- C-5/C-6: the controller must NEVER dump page source, scripts, function source, full page.content or network URLs/headers. DOM-only snapshots/assertions are scanned with token/nonce exclusion; screenshot metadata/receipts receive the same check, pixels are visually checked. Do not click outbound Discord/donation/help links. CSP is injected on '/' only; navigate only that owned origin and approved app routes. Never archive/upload the retained root: private.json, MCP configs, registry keys and raw logs may contain secrets. Publish only explicitly scanned observations and permitted screenshots/metadata. This is a controller rule, not a claim of browser sandboxing.
- C-7: mock-guard, MCP-order and capture-gate AST/string checks remain explicitly structural. New real child bootstrap controls exercise the actual sitecustomize/guard/capability ordering; a deliberately wrong guard hash exits91 with no bootstrap record or payload output. No product authoring/transport acceptance is borrowed from these controls.
- C-8: finish refuses409 until all12 EVIDENCE_CASES have an observed report, recording missing names as not_observed. It still does not assert acceptance. After closing the owned browser/forwards, the controller can write its scanned cleanup observation into records/controller-observation.json and submit it via --control report --fixture-root ROOT; this fixed report action validates the same bounded schema and sends it through the authenticated evidence endpoint without secrets in args. Then --control finish. --control cleanup is a separate recovery action, not proof that the browser/controller cleaned itself.

Run invocation after review clearance: change directory to this active worktree, set PYTHONPATH to its absolute path, invoke the ORIGINAL checkout Python with tools/verify_artifact_ui.py --run in a tracked detached shell with output redirected/retained. No tool timeout around the live parent. No acceptance resource starts before the reviewer's exact command clearance. Cleanup remains last; no push.

## First-run clearance and final R fixes

Reviewer cleared30fc9bf for the FIRST --run after R-1/R-2/R-3, no further review round. Two controls first errored (missing shutdown helper and actual non-ASCII compare_digest TypeError); final44 controls OK0.912s and compile-only pass. Watchdog evidence/callback failures now always reach the own-process exit92 in finally. Control auth compares encoded bytes and refuses malformed/non-ASCII values rather than raising500. The frozen SHA table below is refreshed from final working bytes and checked after commit.

Known accepted limitations: native _overlapped connects may lack audit events, so fixed literal destinations supplement guard evidence; base interpreter/stdlib/native DLLs remain a trusted un-hashed boundary except the recorded executable/site pins. Already-exited launcher probes can falsely leave unresolved; the expired-lease control can race slow fsync. Creator/HMAC trust is NOT defended against code running inside the fixture (guarded children can read the key), nor the OS user or registry/environment tampering. Inline token/nonce require DOM-only controller observations and scanned exports. No page/script/function source dumps, outbound-link clicks or retained-root archive/export. Each real control root intentionally records one unowned-port refusal; those control files do not belong to the acceptance root.

Before first start: retain known-live-port listener baseline, name/size/mtime manifests of the original data/uploads/.agentchattr roots and Python PIDs/start times; verify no other owned acceptance fixture is running. Control sanity check found14 ended control results (codes0/91/92), no live owned control births; PIDs19936/28248 were absent from control records and were not touched. After the run compare baseline, signed births, per-process guards, no run-root violation/watchdog/missing-case files, all12 observed cases, browser/forward closure and secret scan. Keep acceptance_claim=false for review. Exact approved invocation uses original checkout Python, absolute worktree PYTHONPATH, hidden detached process with stdout/stderr redirected, no tool timeout. No push.

## First attempt e4a601f: retained startup fixture defect

Tracked shell7278f314 launched the exact cleared hidden detached parent. Root .audit-tmp/artifact-ui-i2wyom3g never emitted READY and no browser/document request ran. Real validate_package refused the fake API seat because its secret_ref was empty while the literal provider declares ARTIFACT_FIXTURE_DUMMY_KEY. This is an instrument-invalid fixture startup, not a product/UI failure or acceptance pass. Original artifact-run.out/err, private server.log, receipt.json and cleanup.json remain unchanged.

Initial cleanup retained URLError (server already offline) and a transient exited-launcher probe ValueError. Subsequent independent probes show both signed recorded PIDs41408/3972 absent; standalone signed cleanup visited2 with unresolved=[]. All four owned ports have zero listeners. Guard records show zero real attempts, no unowned-port or watchdog files. The original known ports/data manifest/Python baseline is unchanged. The first PowerShell object comparison falsely reported data/PID differences because ConvertFrom-Json automatically parsed timestamp strings; its false projection is retained in recovery-baseline.json. Raw JSON comparison and -DateKind String confirm exact equality in recovery-baseline-verified.json. No source changed while the failed run was alive.

The fixture package is now a shared literal helper called by the actual server. A new control using real provider_templates/cli_templates/validate_package reproduced the SeatError first (1 ERROR0.026s), then passes after the API seat's secret_ref points to the owned dummy environment variable. No real credential, provider, capability or product edit. Final45 controls OK1.027s and compile-only pass; source table refreshed. Corrected run is held for reviewer confirmation; preserve first attempt outputs and use distinct attempt2 output paths/baseline on retry. Never overwrite the first receipt. Cleanup of tracked docs remains last.

## Attempt 2 and combined startup-defect audit (before any third try)

Reviewer cleared5bc86df for attempt2. Fresh raw-string baseline:25 Python PIDs, original data1 file, no known-port listeners. Distinct artifact-run-attempt2.out/err retained. Root .audit-tmp/artifact-ui-99j19hmh reached READY, launched both actual managed authors and produced4 guarded interpreter records. Owned isolated session0a2a9e09 / tab4f9356f6 opened on the same host, no forwarding. The page remained at Loading messages with0 channel tabs: DOM observation proved marked exists but setOptions is undefined; actual chat.js init calls marked.setOptions before WebSocket/channel initialization. The console-output API returned no matching console entries; it does not establish absence of uncaught page errors. A new Node control independently reproduced the missing-method assertion.

Stop-on-first-defect honored: no document action, durable index absent/request count0, CLI tool count0 and invocation record files0. One viewport case reported not_observed. Transcript screenshot image-1, returned1280x850 metadata, visibly no secrets; no image-byte hash/native file claim. Owned browser/tab closed, no forwards. Authenticated shutdown ended the parent; original receipt acceptance_claim=false and original cleanup URLError/two transient exited-launcher ValueErrors retained. Recovery signed cleanup visited8/unresolved=[], all8 births independently absent;4 guards have real_attempts=[], no unowned-port/watchdog files. Root metadata/data and known ports unchanged. Full-machine Python baseline is NOT identical: PID58092 disappeared, no additions. It belongs to neither the8 run birth records nor retained control births; its cause is unknown. Keep this baseline deviation, never relabel it unchanged. attempt-summary.json and recovery-baseline-verified.json retain the facts; no third run has started.

|Startup stage|Combined static audit and actual evidence|Change / remaining boundary|
|---|---|---|
|Interpreter/guard/child env|Original venv/Git common-dir, guarded child0/91/92 controls and attempt2 managed readiness reached|Existing coverage retained; native/pre-site limitations remain.|
|Literal provider/package|Attempt1 real validator refused empty API secret_ref; shared fixture_package + actual validator now pass|Owned dummy reference only; no real credential.|
|Full app configuration before first bind|Earlier controls validated isolated helpers only|NEW dry_startup mode follows the SAME runtime_server route setup, run.main/configure, real app stores/catalog/package validation and HTML construction; stops deliberately before the first fake API/MCP/web bind. Audit hook refuses any service-port bind. Actual guarded child passes. It does not execute ASGI lifespan, managed launch or a browser.|
|Fixture CDN substitution / page host|Attempt2 shim supplied parse but real chat.js also requires setOptions|Shared marked_shim/fixture_html now supply setOptions (no-op) and escape-only parse. Node enumerates EVERY actual marked method used by chat.js, asserts functions, calls setOptions and verifies escaping. Rich-chat rendering remains excluded.|
|Primary host/source freeze|Original manifest lacked direct hashes for app.py/run.py/chat.js and package/config validators|Added those6 host/validator sources to PIN_FILES; Git HEAD/clean checks and existing artifact/wrapper hashes retained. Product bytes unchanged.|
|Source/author seeding and monitor|Attempt2 READY + completed/absent/active synthetic source rows reached; monitor_turns only advances waiting/stalled invocation work|No document transport/admission exercised, no inherited unit acceptance used for that claim.|
|API/MCP endpoints and UI actions|Only readiness and safe DOM probes reached|All12 rendered cases remain unaccepted; fresh run still needs reviewer clearance.|
|Cleanup / baseline / secrecy|Signed recovery8 absent, originals/ports unchanged, one un-attributed baseline PID departure|Original failures/deviation retained. No root/private/registry archive; DOM-only exports and screenshot visual check.|

Control sequence: shared shim extraction kept old behavior, then actual Node method test failed and dry seam errored (1 FAIL +1 ERROR0.043s). Added setOptions and listener-free full runtime prebind mode. Final47 controls OK2.266s, including real guarded dry app startup and existing bootstrap children; compile-only OK. Console output retained in .audit-tmp/browser-harness-controls-after-attempt2-final.txt. No acceptance listener opened by these controls (stdlib internal socketpair allowance remains). No product/capability edit and no automatic third run. Reviewer receives this combined audit/pin before deciding another run.

## Third-run hold: first-visit tour and real-page init backstop

Reviewer withheld b14ff1a: a fresh isolated profile has no help_seen flag, so successful chat init schedules the help overlay after2500ms. This would block later clicks despite a healthy server. The fixture head now seeds localStorage.help_seen=1 before any product script. This is fixture-only origin state, never a personal profile or product-source change.

NEW tools/artifact_page_init_control.js executes fixture_html('T','N') in one Node vm context. Python HTMLParser extracts every script tag in exact document order, inline token/observer/shim then all11 local static scripts. The DOM tree/strict id map comes from the actual HTML; unknown ids return null (no auto-created controls). Map-backed storage, recorded fetch/WebSocket, a schema-valid general-channel catalog and bounded microtask/history-task queue replace browser APIs. The real DOMContentLoaded callback runs, then settings/agents/history/history_complete enter the real ws.onmessage. It asserts: every script/async task completed without a throw or error log, marked.setOptions ran, the WebSocket is ws://127.0.0.1:1/ws?token=T (DUMMY test token), required channels/active-all/capacity fetches occurred, the real catalog validator accepts general, channel tabs exist, history hides loading-indicator, Documents.onclick is a function, help seed exists and help-guide is absent. Observer code is compiled using new vm.Script before execution. Loaded static source hashes and the new VM tool are frozen too.

This is a globals/shim/order/init-throw backstop. The DOM parser/selectors/geometry and network are minimal doubles; no layout, CSP, focus, timing, real transport or browser acceptance claim. VM scaffolding initially lacked Event/insertAdjacentElement and used an incorrect active-all DTO; those control defects were corrected, and the real catalog acceptance assertion prevents a silently held catalog from passing. One in-memory debug probe logged the swallowed lifecycle exception to locate the stub gap; final green executes unmodified product scripts. No file under static/ was edited.

Observed-red mutation results retained in .audit-tmp/artifact-page-init-vm-results.json:

|In-process reversion|Observed failure|File/stage|
|---|---|---|
|Remove help seed from generated HTML|AssertionError: fixture must suppress first-visit help overlay|DOMContentLoaded/static/chat.js|
|Remove setOptions from generated shim|TypeError: marked.setOptions is not a function|DOMContentLoaded/static/chat.js|
|Break observer source syntax|SyntaxError from new vm.Script|inline-1 observer|

Baseline VM PASS:14 scripts, optionsCalls1, exact dummy-token WebSocket, all required fetches, catalogAccepted=true, channelTabs1, loadingHidden=true, documentsClick=true, observerSyntax=true, helpSeed=true, uncaughtErrors0/errorLogs0. All3 reversions exit1 and are checked for their specific failure text. Final harness controls49 OK2.987s; compile-only and node --check pass. Raw console receipt .audit-tmp/browser-harness-controls-page-init-final.txt. No acceptance app/browser started after attempt2.

Controller precondition BEFORE EVERY evidence case, after waiting for legitimate page/history loading: loading-indicator is hidden (hidden property, CSS hidden class or no visible layout), channel-tabs has children, and help-guide is absent. If this fails, stop as startup-invalid, not a case failure; never click through a backdrop or manufacture readiness. A DOM-only probe is permitted:

```javascript
await page.evaluate(() => {
  const loader = document.getElementById('loading-indicator');
  const loadingHidden = !!loader && (loader.hidden || loader.classList.contains('hidden') || getComputedStyle(loader).display === 'none');
  const tabs = document.getElementById('channel-tabs')?.childElementCount || 0;
  const helpAbsent = !document.getElementById('help-guide');
  if (!loadingHidden || !tabs || !helpAbsent) throw new Error('Fixture startup invalid before evidence case');
  return {loadingHidden, tabs, helpAbsent};
});
```

Keep host127.0.0.1 for CSP. No source/script/function/page dumps or outbound Discord/donation clicks. The escape-only shim can double-escape angle brackets in ordinary chat (cosmetic; rich-chat parity excluded). Alert/naming-lightbox paths remain outside this bounded document flow. PID58092 baseline miss and both instrument-invalid attempts remain recorded. New pin goes to reviewer with the real-page VM red results; third run remains held until explicit clearance.

## Attempt3 at120f491: real CLI admission, foreground runtime limitation

Reviewer authorized ONE attempt3. Fresh baseline24 Python PIDs/start strings, no known-port listeners, original files1/0/0; distinct artifact-run-attempt3.out/err. Root .audit-tmp/artifact-ui-_i8od3z3 reached READY with both managed authors. Fresh isolated Electron session5e2e4847/tab744a1515 passed the exact startup precondition: loader hidden,6 channel tabs, help absent. No fourth run or source edit during the run.

An actual completed-session document request was submitted via the rendered form. Real fake CLI called chat_artifact_brief, then chat_artifact_submit, then chat_queue_release, all validated successfully. Durable request00501cd97424429cb615761b32630e61 is fulfilled, version72f14aba39575950be14a8ef197b1010;99-byte Markdown SHA256c0422b95ed2987c2af066dee02169cd73f4773939684a9f9985d18e32f84e744 equals the canned BOM/CRLF fixture. This is real transport/admission evidence, not complete UI acceptance.

The offscreen isolated browser reports document.hidden=true/visibilityState=hidden even with hasFocus=true. Supported attachTab and native window.focus calls did not change it. UI status polling (including Refresh) deliberately stops while hidden; the card remained Queued after backend admission. No visibility getter override, synthetic visibility event or product change was applied. Browser foreground polling, Read and Download were not reached. CLI/polling reports explicitly say not_observed with partial evidence; all12 cases remain incomplete and acceptance_claim=false. This is a runtime/harness coverage limit, not a product failure verdict. A visible surface or an explicitly reviewed visibility-simulation disclosure is an OPEN next-mechanism decision.

Controller deviations retained: one exact channel-name role selector failed (fresh snapshot/ref succeeded); a15s wait targeted Read while the real button is Read document, so that wait is not a valid product timeout. The subsequent DOM visibility probe established the independent hidden-tab limitation. No blanket timing claim is made.

Stopped and closed only the owned isolated session/tab, no forwards. Original receipt and cleanup warnings (offline cooperative shutdown + exited-handle probe errors) remain unchanged. Signed recovery visits8;7 primary birth probes show absent and PID44120 remains uncertain/process_probe_failed. Independent Win32_Process enumeration shows NONE of the8 recorded PIDs present, owned listeners0. Do not rewrite that uncertainty or declare cleanup.json clean: raw standalone cleanup retains the44120 unresolved row. All4 guard records have real_attempts=[], no unowned-port/watchdog/missing-case files. Original data, known listeners and full Python baseline are exactly unchanged for attempt3. Prior attempt2 PID58092 deviation remains historical. Receipt/summary token+nonce scan clean; browser tool observations were DOM-only and no source/outbound links were read/clicked. No retained-root export/deletion.

Next owner reviewer: classify partial evidence/cleanup uncertainty and choose a supported visible browser route or authorize a bounded fixture-only visibility simulation before any fourth attempt. No automatic rerun. UI/backend component acceptance unchanged; rendered whole-flow acceptance still pending.

## Visibility-simulation ruling and cleanup repairs (fourth run NOT yet cleared)

Reviewer accepts attempt3 only as partial real CLI admission, not UI acceptance or product failure. Approved next mechanism: explicit --simulate-visibility flag, fixture observer only, product code untouched. Before any static product script, observer records native_hidden/native_visibilityState/native_hasFocus, then defines hidden=false and visibilityState=visible on the DOCUMENT INSTANCE when the flag is on. No prototype modification and no synthetic visibility events. Off leaves the instance untouched. Claim is exactly: no native foreground/visibility parity. The product hidden-guard proof stays in the existing Node UI tests, not a browser case under simulation. Closing the actual document panel and ordinary polling/backoff can still be exercised, with the simulation disclosed.

Flag freezes into private/creator manifests and binding checks. READY/state expose the mode. Authenticated bounded POST /__artifact_fixture/visibility validates all native fields/mode/claim, saves the latest plus an append-only-per-document capture history. Receipt.json AND summary.json always include visibility, visibility_records and the claim. Before a browser observation exists, explicit null native fields/native_values_missing=true mark missing coverage; finish refuses missing/invalid disclosure. Reload captures fresh native values again before overriding. Token/nonce export scanning and native-save interception boundaries remain unchanged.

Native/override controls execute the ACTUAL observer in the full-page VM, starting from hidden/hidden/no-focus native stubs. Off and on both pass; four specific in-process reversions fail:

|Reversion|Observed red|
|---|---|
|Force override while flag off|document.hidden flag-control assertion|
|Remove override while flag on|document.hidden flag-control assertion|
|Omit native capture fields|native hidden must be recorded|
|Move observer after first product script|visibility must be installed before first product script|

Raw baseline/red results: .audit-tmp/artifact-visibility-control-results.json. This proves observer logic/order in VM, not native foreground parity.

Cleanup diagnosis: PID44120 was the TRUE OWNED SERVER INTERPRETER birth, not a launcher. It is the initial/earliest signed bootstrap selected by Fixture.start before seed launches any worker; no signed spawn-44120 launcher file or worker/client birth maps to it. The parent retained its verified kernel handle but cleanup re-opened it by PID after exit, hitting image-query failure. Original attempt3 cleanup and uncertain/probe_failed records remain unchanged; a later primary check returned absent/error87. No retrospective clean/pass claim.

Repairs are HARNESS ONLY (process_identity.py unchanged): server cleanup uses the retained verified handle with a full matching birth pair. A mismatched pair never gets authority. For other uncertain image probes, a separate query-only+synchronize handle reads terminal state; it NEVER requests terminate rights or returns an unverified handle. Only exited/absent becomes terminal; still-live unverified or mismatched remains unresolved, never killed. Every cleanup probe records its status/proof/exit code. Cooperative shutdown skips HTTP when its owned process is already exited, and clears a connection-refusal race only if a second owned-handle poll proves exit. A live failure remains unresolved. A failed query AFTER opening a handle does not become absence just from error87.

Observed red: three cleanup controls first failed (3FAIL0.028s), then passed. In-process legacy probe/shutdown reversions also produce3 assertion failures/0 errors in .audit-tmp/artifact-cleanup-regression-reds.json. An earlier mutation wrapper captured an import before the test patch and produced1FAIL/2ERROR; retained as instrument-invalid in the separate -invalid.json, not counted as useful kills. A real guarded child exits normally and its read-only terminal query is exited/absent. No malformed/live/mismatched PID is controlled.

Final61 harness controls OK3.442s; compile-only and Node syntax pass. Console .audit-tmp/browser-harness-controls-visibility-cleanup-final.txt. No fourth acceptance server/browser started. Old roots remain retained, no deletion/export. New pin and red proof go to reviewer for ONE-attempt authorization, using trusted Python/absolute PYTHONPATH plus --run --simulate-visibility, fresh baseline/root/distinct attempt4 logs. All12 cases still required; include the visibility disclosure in EVERY report. No native hidden/foreground parity or native-save claim, no activation/push.

## Attempt4: browser runtime refused visibility simulation

Reviewer authorized ONE run at40fe872 with --simulate-visibility. Root .audit-tmp/artifact-ui-pt13sdra reached READY. The isolated browser exposes document.hidden and document.visibilityState as non-configurable own getter properties. The approved instance override failed before the observer installed its evidence/report functions. DOM-only checks showed hidden=true, visibilityState=hidden, hasFocus=false, loader hidden,6 tabs and no help overlay. No document request was made. Root stopped the attempt without changing product code or trying another override.

All12 cases remain incomplete; acceptance_claim=false. Native values were captured only in observer memory before the failed override, so no visibility record reached the server. Receipt/summary honestly retain null native fields, native_values_missing=true, visibility_simulated=true and the claim "no native foreground/visibility parity". The independent DOM probe supplies the observed native values separately. This is a browser-runtime/harness incompatibility, not a product failure or rendered acceptance. VM controls did not model non-configurable own properties.

Raw cleanup.json: unresolved=[], births_visited=8, cooperative_shutdown=already_exited; six probes absent, PID4552 exited by query-only terminal check, PID19468 exited through its retained verified kernel handle. Later primary probes and independent Win32_Process enumeration show all8 absent; all4 owned ports have no listeners. Four guards have real_attempts=[], no unowned-port/watchdog/missing-case files. Original files, known listeners and the full raw-string Python baseline are unchanged. Owned browser/session closed, no forwards. Receipt, summary and postcheck exports passed the token/nonce scan. Earlier attempt histories and the PID58092 baseline deviation remain retained separately.

Evidence stays local under the root, including recovery-baseline-verified.json and independent-postcheck.json; private root is not exported or deleted. No fifth attempt is authorized. Next owner reviewer: settle a supported browser mechanism; root implements only the reviewed delta and reruns only after explicit clearance. Accepted backend/UI components are unchanged. Screen/transcript/packaging/activation and final file cleanup remain pending. No push.

## Attempt5 FINAL: CLI polling/read/Blob evidence, screenshot runtime failure

Reviewer authorized ONE final Electron run at1ab0589 with --simulate-visibility. Root .audit-tmp/artifact-ui-cc5qedbl reached READY. Served-route proof was checked first: original SHA25696020b32c44626e5c6fc6c66da7498874640211d19cdb9328e380363b32701ac, served SHA256ec02a269d4eb65a7ee3c2b65fedb3b3c3d7c02c66dc3876945455da417ac17a3, replacement_count=3. Native hidden=true, visibilityState=hidden, hasFocus=false were POSTed and retained with simulation=true and the full substituted-read claim. Loader hidden,6 tabs,help absent passed before the cases.

Positive bounded browser evidence: completed-session CLI form -> Queued -> real MCP brief/submit/release -> automatic Ready; manual Refresh retained Ready. Request999000fc25fc4cd190b22a7a7be717d3. Read document showed the canned HTML/script/javascript-link content literally in PRE and window.BAD remained absent. Download Markdown produced a99-byte Blob, browser/server SHA256c0422b95ed2987c2af066dee02169cd73f4773939684a9f9985d18e32f84e744, fixed filename document.md, native default intercepted, native_save_claim=false; object URL revocation observed about1.017s later. Observer errors empty. CLI and read-download observations were recorded; no native-save or foreground parity claim.

Desktop screenshot at1280x850 then timed out after15000ms: browser tool reports reachable DOM but no frame. Root STOPPED at that first browser-environment failure, without a screenshot retry or more scenarios. Mobile/keyboard, API generation, lost-create, refusal, cancellation/Stop, lifecycle, backoff/reload/stale-response and complete12-case acceptance remain unproven in this run. Screenshot bytes do not exist; no hash/visual-layout claim. Receipt acceptance_claim=false, controller_finished=false; viewport-keyboard explicitly not_observed. No sixth run or Chrome/Edge tooling is authorized. Adaptation ends per reviewer ruling; the reviewer must now advise Seth on accepting bounded partial harness evidence plus existing component/Node tests, or seeking a separately requested browser follow-up.

Controller deviation retained: first waitFor used40000ms, rejected locally because the browser tool caps it at30000ms; corrected to30000ms before any actual wait, which found Read document immediately. This is not a product timeout or hidden extra attempt. Initial postcheck used PowerShell JSON property order and null-array count, falsely flagging tree changes/one guard attempt; its raw result is preserved as postcheck-first-property-order-invalid.json. Independent structural JSON comparison corrects those two fields.

Raw cleanup.json unresolved=[], births_visited=8, cooperative_shutdown=already_exited. Six probes absent; PID48040 exited/query-only proof exit0; PID6308 exited/retained verified kernel handle exit0. Independent Win32_Process query lists none of the8 PIDs; all4 owned listeners0. Four guards real_attempts=[], no unowned-port/watchdog/missing-case files. Owned isolated browser/session closed, no forwards. Original data/uploads/.agentchattr manifests and known listeners unchanged. FULL Python baseline is NOT unchanged: one added pythonw.exe PID56240 start2026-10-27T01:00:01.2962040Z, no removals; it is outside all8 owned births, cause unassigned, untouched. Prior PID58092 deviation remains separate. Receipt/summary/postcheck exports pass token/nonce scan; retained root is not exported or deleted.

Next owner reviewer: assess this final partial evidence and recommend the remaining-coverage decision to Seth. Root does not restart or adapt the browser. Backend/UI component acceptance remains unchanged. Screen/transcript21/packaging22/activation and final file-structure cleanup remain pending. No push.

## Reviewer disposition after final browser attempt, 2026-10-26

Reviewer classifies attempt5's screenshot timeout as the host's inability to render frames, not a product failure. No sixth attempt or unprompted Chrome/Edge work. Positive real-browser DOM evidence is accepted for startup, create/Queued, real MCP brief/submit/release, automatic Ready, manual Refresh, literal PRE reading and byte-exact99B Blob/download intent/revocation, served script proof and raw cleanup. This is PARTIAL browser evidence, never UI acceptance. The12-case gate remains incomplete and acceptance_claim=false. Viewport/keyboard/mobile/API/lost-create/refusal/cancel/lifecycle/backoff/reload/stale and every visual/layout check rely on existing component, Node-vm UI and mutation tests; they are not browser-proven.

Baseline correction from reviewer's read-only Win32_Process query: added PID56240 pythonw.exe start2026-10-27T01:00:01.296Z is a Task Scheduler child of svchost.exe running C:/Users/SJG/miniconda3/pythonw.exe -m hotin refresh --quiet. Timestamp matches root's baseline addition. Record as added unrelated scheduled process, identified, outside all owned births; no fixture-caused baseline violation is established. Original baseline and raw deviation remain retained; PID58092 stays a separate historical miss. No unrelated process was changed.

Recommendation relayed to Seth, decision pending:

- Accept PARTIAL browser harness for20-22 and proceed to responsiveness screen,21 and22, because capability remains off until a separate activation commit.
- Add a pre-ACTIVATION real visual check of the Documents panel at desktop and390px, by Seth looking at it, or an optional separately owned Chrome/Edge follow-up if he requests automation. This precedes activation, not21/22 work.
- Alternatives: accept partial with no visual gate, or build Chrome/Edge harness first. Ask Seth once. If he does not answer, follow the first recommendation; activation remains blocked until visual checking is done. This default is the reviewer recommendation, not a fabricated user decision.

Next owner root: prepare the thin responsiveness screen under the existing reduced contract, then21/22. Retain all roots; no deletion, activation or push. No additional browser adaptation.
