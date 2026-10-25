# Requested artifacts implementation plan

> For agentic workers: execute the approved plan task by task using the executing-plans skill. Existing bounded helper assignments and independent Sonnet review continue under the standing authorization. No additional agents. This draft requires implementation-plan review before any tests or product edits.

**Goal:** Request, read, revise and download coordinator-authored Markdown through app-owned storage, for CLI and API participants, with exact immutable revisions and trustworthy source/producer provenance.

**Architecture:** A focused ArtifactService owns one-purpose requests over the existing durable queue and seat ownership. Immutable artifact briefs freeze source packets; an atomic metadata store references immutable content objects. Strict artifact-purpose admission shares delivery mechanics with review results while preserving review-v1 schema/semantics. No SessionEngine artifact run or second phase engine.

**Tech stack:** Existing Python/FastAPI/MCP, atomic_json and queue locks; vanilla JavaScript DOM construction, existing marked lexer with a source-only fallback. No new package or provider integration.

**Spec:** Specificationv1.7 DA-2 and artifact portion of AT-12; issue20. `TICKET-20-CONTRACT.md` and Sonnet's accepted P1-P4/A1-A6 rulings govern. Base published main400d6de. Issue21 owns actual-round transcript and combined export.

## Global constraints and ownership

- Do not create an artifact from arbitrary chat, fenced JSON or every session output. A user request is explicit, scoped and durable.
- Exact text, CRLF and UTF-8 bytes are immutable. SHA-256 identifies each version; no 1000-character catch-up limit, silent truncation or universal synthesis format.
- Existing review-v1 validators, HMAC bytes, storage paths, restart behavior and tests remain unchanged. Domain separation for artifact results is inside signed payload bytes.
- Operator-only create/revise/cancel/list/read/download; authenticated producers get only their assigned dispatch brief and one-dispatch submit. Source is untrusted data, never tool authority.
- Engine RLock -> catalog boundary -> one store/file lock. Read other stores under the outer boundary, release their lock before the artifact lock. No await, sleep or whole import under that boundary; sync work is offloaded from async routes.
- Strict held/no-reset stores, fingerprint-cached reads, atomic IO before memory, detached reads, bound before catalog initialization. Owner errors cannot masquerade as empty data.
- Root owns protocol/service/lifecycle/UI/acceptance. Existing helper may own one NEW test file per frozen component, at most12 named methods. Record genuine RED separately from fixture errors. Sonnet reviews each frozen slice.
- No live provider, installed client, Omarchy, Desktop/global changes, external source fetching or environment installs. Native/API/browser scripts get full source/cleanup review before one bounded run.

## Decisions for plan review

| Item | Proposed concrete choice |
| --- | --- |
| Authored cap |512KiB UTF-8 per revision, nonempty/non-NUL valid Unicode; validate without trimming or rewriting stored text |
| Frozen source cap |2MiB canonical UTF-8 JSON, at most1000 selected messages; includes optional run input. This bounds IO and repeated delivery while allowing more source than output. Reject oversize with exact bytes/count before creation; never take only the first rows. It is a storage cap, not a model-context guarantee. |
| Scope options | Server preview offers accepted projected messages of a selected run, or explicitly checked channel-message IDs from a paginated picker. Human discussion is included by explicit selection. Missing projection requires history repair; no reconstructed transcript. Store exact ordered ids/uids/per-message hashes and the full source packet in an immutable brief. |
| IDs | UUID hex for lineage/request/attempt/dispatch/brief/version. Version sequence is positive per-lineage; parent is an exact version ID/hash. No manufactured session id or review turn id. |
| Content placement | `artifacts/index.json` contains validated lineage/request/version metadata and statuses. `artifacts/objects/<version_id>.md` and `artifact_briefs/<brief_id>.json` hold immutable bytes. Object paths derive solely from validated IDs, never title or uploaded paths. |
| CAS | One pending authoring request per lineage; request creation reserves its expected current head under one atomic index transaction. Different lineages may be pending. Idempotent operator request_id + identical body returns the same request; changed body409. |
| Models | Requested model/adapter/identity/name from the immutable launch binding at request creation. API confirmed model comes from that dispatch's actual completion result, bound into its sealed payload by the managed worker; no generic latest receipt or agent-supplied confirmation. CLI confirmed model=null with unverified reason. Missing source run/input revision is explicitly null, with an absent-source label. |
| States | prepared -> queued -> active -> fulfilled, or terminal failed/quarantined/cancelled/imported. Requests retain immutable audit separately from mutable status/channel projection. Retry/reassign is a new request/attempt/dispatch referencing the prior attempt; no spontaneous re-generation. |
| Reader | Node-built Markdown view plus literal source. Block all images initially, including remote/data images. Restrict model links to explicit http/https with noopener/noreferrer; other schemes/relative destinations show as text. Bidi/control warnings do not alter downloaded bytes. |
| Download | Exact stored bytes, `text/markdown; charset=utf-8`, nosniff, attachment filename `artifact-<id>-r<sequence>.md`, content SHA-256 response header. No raw title reflection. |

## Task 0: Pure shared-mechanics extraction, no artifact code

Files: NEW `sealed_result_io.py`; modify `result_outbox.py`, `result_delivery.py`, `review_brief.py` only where mechanics are delegated. Read every caller of the touched functions first. Keep existing public/private wrapper signatures and exception types, monkeypatch seams and exact canonical review-v1 bytes.

Proposed shared interfaces:

- `canonical_utf8(payload) -> bytes` and `payload_mac(payload, secret) -> str`, matching current sorted-key compact JSON/HMAC exactly. Review-v1 has no new field; artifact schemas later require purpose=`artifact-v1` inside payload.
- `read_bounded_json(path, maximum, error_factory) -> object` with duplicate/nonfinite refusal and unchanged caller error mapping.
- `put_immutable_json(path, value, *, lock_path, load_existing, error_factory) -> dict`, atomic write / exact-repeat / conflicting-repeat mechanics, caller-owned schema and launch/path checks retained.
- `deliver_saved(event, submit, *, expected_id, acknowledge, error_factory, sleep) -> acknowledgement`, factored bounded transport delivery and matching ACK logic. No generation, scanning, ownership adoption or policy inside this helper.
- Small explicit-identity/public-private brief helpers only if they remove identical logic; do not generalize review role/phase/run authorization into an artifact validator.

- [ ] Run existing result suites GREEN before refactoring: `python -m unittest tests.test_result_outbox tests.test_result_delivery tests.test_saved_result_recovery tests.test_result_brief_seal tests.test_session_events tests.test_restart_startup tests.test_corrected_restart`.
- [ ] Apply the pure refactor, then rerun the SAME unchanged suites and configured full discovery. No artifact module, schema, method or test exists yet. Inspect the diff for exact review-v1 preservation.
- [ ] Freeze/commit and obtain Sonnet review of extraction before Task1. This is the explicit green-only refactor exception, not a fabricated RED.

## Task 1: Artifact metadata and immutable-object store

Create `artifact_store.py` with `ArtifactStore(data_dir, *, hold_unreadable=False)`. Bind policy through `bind_channel_policy(getter)`. Guard ordinary request/version mutations; expose unguarded staged rename/import phases solely to their services.

Interfaces to freeze with the helper: `reserve_request(audit, request_id)`, `set_attempt_state(request_id, attempt_id, expected_state, change)`, `commit_version(request_id, attempt_id, dispatch_id, markdown, provenance)`, `quarantine_submission(...)`, detached `get_request`, `get_version`, metadata-only `list_lineages`, `pending(channel)`, `channel_names`, `lifecycle_scope`, `retained_metadata`, and staged `rename_channel(old,new)`. Error classes distinguish validation, CAS conflict and held storage. Exact signatures/payload keys are locked before helper writes.

Object-before-index: create immutable source/content objects before committing their references. An object-write fault changes no authoritative metadata; an index-write fault leaves harmless unreferenced objects. Startup never treats an orphan as an artifact. A committed index must reference exact existing bytes/hash; missing/corrupt objects hold that owner, never rebuild guessed text. No callbacks before durability or under the store lock. Index reads copy metadata only; read one requested version body separately.

- [ ] NEW `tests/test_artifact_store.py`, initial2 genuine RED for missing store/CAS and durable fault rollback, then <=12 bounded cases.
- [ ] Verify exact Unicode/CRLF/hash,512KiB edges, one CAS winner for simultaneous same-lineage requests, two different lineages allowed, detached reads, held malformed/duplicate/nonfinite/schema/IO cases, immutable-repeat/conflicting-repeat, object/index crash seams and fresh reload.
- [ ] Target `python -m unittest tests.test_artifact_store`; root integration cases use actual stores and policies. Freeze/store review before authoring.

## Task 2: Frozen artifact purpose, outbox and admission

Create `artifact_protocol.py` (strict schemas/content/result parsing), `artifact_brief.py` (immutable packet and trusted delivery authority), `artifact_delivery.py` (purpose-specific owned outbox using shared mechanics), and `artifact_service.py` (request, dispatch, admission/recovery). Keep modules small; do not duplicate a session engine.

Brief schema contains purpose, request/attempt/dispatch/brief IDs, expected producer identity and immutable launch refs, lineage/parent version, source scope hash and exact frozen packet. Request metadata keeps message IDs/UIDs/hash and a private source-brief reference. Public/operator responses never expose seal secrets. Producer brief retrieval authenticates exact seat + assigned claimed dispatch + current request attempt. Unknown purpose fails closed.

API response is exactly `{"kind":"artifact","markdown":"..."}` with JSON outer whitespace allowed, no fence or additional fields. Markdown bytes inside the string are preserved. Model content never supplies a lineage, identity, model confirmation or parent. The owned worker adds result-specific model observation and signs the strict artifact payload; native CLI uses an explicit submit tool. Artifact outbox/ACK files live in separate owned directories, never scanned as review-v1 records.

Admission checks live request/attempt, frozen-scope hash, expected parent, authenticated identity/current dispatch and managed launch ownership where applicable. An identical dispatch/content returns the same version/admission; conflicting content is quarantined without changing the existing version. Invalid/stale/cancelled/superseded results are visible as failed/quarantined attempts, never ordinary chat. Oversize output records a clear error/hash/byte count rather than silently truncating a published version.

Request persistence and queue enqueue are separate atomic files: reserve request with deterministic dispatch id -> persist frozen brief -> enqueue that exact dispatch -> mark queued. Crash recovery may complete only the matching live prepared/queued request, idempotently. Terminal requests never requeue. If a saved API result exists after restart, redeliver only after verifying the exact pending request + dispatch + purpose/ownership/seal; unmatched records are quarantined/reported. No generation on recovery and no transport release merely because admission succeeded. Reuse genuine settlement evidence for an uncertain old owner.

- [ ] NEW `tests/test_artifact_admission.py`, observed RED before new interfaces, then strict cross-purpose rejection both directions, wrong-attempt/scope/parent/identity, exact duplicate and conflicting duplicate, superseded retry and source Stop fences.
- [ ] NEW `tests/test_artifact_delivery.py`: save-before-send, failed ACK, crash after result save, restart matching-live-only redelivery without generation, unknown/unmatched/quarantined records, private-secret non-disclosure. Existing review tests remain unchanged.
- [ ] Freeze the common authority/admission pack for Sonnet before adapters.

## Task 3: Operator routes, adapter dispatch and cancellation

Create `artifact_routes.py` with an explicit router/service binder; `app.py` owns configure/startup/Stop wiring. Proposed operator routes: `POST /api/artifacts/preview`, `POST /api/artifacts/requests`, `POST /api/artifacts/{id}/revisions`, `POST /api/artifacts/requests/{id}/cancel`, paginated `GET /api/artifacts`, `GET /api/artifacts/{id}`, `GET /api/artifacts/{id}/versions/{version}`, and its `/download`. These are new proposals, not existing endpoints. Exact JSON schemas reject duplicates/unknown fields/nonfinite/bad UTF-8 and cap input before mutation. Preview returns source bytes/count/hash, exact IDs and producer/parent scope token; create rechecks token under the boundary before effects. Routes are operator-only/no-store, ordinary 400/403/404/409/503 with generic IO errors.

Agent-only purpose routes retrieve the assigned artifact brief and submit one dispatch result. MCP adds `chat_artifact_brief(brief_id, ctx)` and `chat_artifact_submit(brief_id, markdown, ctx)`, authenticated by seat token; neither lists/reads the operator library. `wrapper.py` injects explicit artifact tool instructions. `wrapper_api.py` branches on purpose, reads the frozen packet and generates the strict artifact envelope through existing invocation/cancellation. Extend `agents.py` envelope whitelist and `dispatch_queue.py` validation with purpose-specific fields; absent purpose remains legacy review/chat behavior, unknown purpose refuses. Do not set artifact envelope run_id to its source session run_id.

Factory binds artifact owner to the same closed channel getter before catalog init and wires ArtifactService before inventory/recovery/threads. Recovery scans only owned runtime paths after source of truth is available. Source Stop atomically fences requests created before that stop: queued dispatches cancelled; active attempts enter existing cancelling transport path and request cancelled, late content quarantined. New explicit requests created after Stop record the stopped source state and remain eligible. Producer replacement/retirement terminally fails unfulfilled ownership for explicit reassignment; no automatic redirect.

Session reconciliation must not adopt artifact work. Same-seat review has existing transport precedence; artifact work waits. Artifact pending work remains unrelated work for restart context preparation; preserve that refusal and make its UI explanation actionable. Source Stop and artifact cancellation never cancel a peer/other lineage by accidental namespace reuse.

- [ ] NEW `tests/test_artifact_routes.py` exercises actual middleware: every operator route refuses agent tokens, schema/no-store/download headers and exact bytes/hash; producer only gets its assigned brief/submit.
- [ ] NEW `tests/test_artifact_dispatch.py` uses real queue/coordinator and engine: active review then artifact FIFO, pending unrelated work restart refusal, source Stop before/after request, active cancellation/late result, replacement and startup idempotency. Observed RED first.
- [ ] Run artifact modules plus existing channel ingress/agent paths, restart, result-outbox/delivery and Stop suites. Freeze review before lifecycle/UI.

## Task 4: Lifecycle, retained view and backup

Modify `channel_lifecycle.py`, `channel_service.py`, `archive.py`, artifact store/service and shared app binder. Add artifact counts/errors to catalog and retained API/validators. Pending artifact request/dispatch blocks archive, rename and delete with exact IDs. Completed artifacts stay read-only after deletion. Delete preview and guide disclose copied source text retained in immutable artifact audit, even when its original chat message is deleted. Backup export discloses the same inclusion.

Append `artifacts` AFTER the current seven rename steps, using the same single intent. Existing old seven-step prefixes remain valid; a fully marked old intent runs only artifacts before finish. Stage changes only mutable outer channel fields/index projections, not frozen request/source/dispatch audit. Delete steps remain todos/messages/settings.

Backup imports a lineage as one atomic metadata transaction with all referenced versions/source objects staged first. Any existing UID collision skips the entire lineage with a report; never merge/fork/overwrite chains. Imported requests are terminal read-only imported, dispatch/seal material stripped, provenance explicitly imported. Resolve the lineage channel under a short policy boundary; inactive/reserved names remap with the established reason. Enforce content/source caps before effects; report exact whole-lineage landed/skipped counts. No callbacks/dispatch/model work on import.

- [ ] NEW `tests/test_artifact_lifecycle.py`: old seven-mark upgrade, new-step write-before-mark crash/fresh reload, exact audit preservation, delete retention/source disclosure, all owner-held/count/error paths, missing-artifact-file configure upgrade and binding order.
- [ ] NEW `tests/test_artifact_archive.py`: whole-lineage collision/dedupe/authority stripping, immutable content/provenance, mid-import lifecycle change, exact partial reports and no wake. Existing channel/archive assertions remain.
- [ ] Measure hold and loop-thread require_active on a bounded many-version/source shape before freezing. No whole-file body copies in catalog/retained lists.

## Task 5: Request, revision and safe reader UI

Create `static/artifacts.js` and scoped `static/artifacts.css`; integrate `index.html`, existing session/selected channel controls, retained view and actual typed settings events. Add an Artifacts entry, scope picker and selected-author request form; requested format remains user text, not an imposed template. A reader lists versions, provenance, pending/failed attempts, literal source and exact download. Revision requires the current parent and instruction; keep drafts on409/503/timeout, synchronous single-flight and no optimistic new version. Refetch after reconnect/events. Inactive channels permit reading, not request/revision; Stop remains available.

Use marked.lexer tokens only as untrusted data and construct an allowlisted DOM tree. No innerHTML, event attributes, source-derived CSS, HTML interpretation, remote images or mutation of original Markdown. If lexer unavailable/unknown tokens, show literal source with an explanation. Download via authenticated fetch of exact bytes and a page-owned Blob URL; model content cannot supply the download URL/filename. Safely render bidi/control warnings while retaining exact source bytes.

- [ ] NEW `tools/verify_artifact_ui.cjs`, <=12 named actual-source VM cases, initial missing facade/unsafe rendering RED; model DOM detach/focus and async timing accurately.
- [ ] Hostile corpus: raw HTML/scripts/event attributes, javascript/data links, nested links/images, bidi and control chars, code blocks containing markup, CRLF and literal backslashes. Assert no unauthorized element/attribute/network request and exact source/download identity.
- [ ] Keyboard/focus/Escape,44px controls/14px text and390/1280 dialog fit; preserve known inherited whole-page overflow as a limitation. Keep task scope separate from global chat Markdown cleanup.

## Task 6: Frozen acceptance, final review and publication

- [ ] Draft one owned managed-CLI/fake-client case using real MCP artifact submission and release; one actual API-wrapper/local fake responder case using strict purpose/outbox/admission; one isolated rendered case for request/revision/hostile Markdown/download/lifecycle/retained access. No code-generated scenario substitutes for actual public admissions without a fixture label.
- [ ] Full source/hashes/cleanup/guard review before any resource launches. One unchanged run per case; failed cases retained and classified before a rerun. Reuse accepted child-aware cleanup, record true births, end every owned resource; no parent force of clients/models, no provider calls.
- [ ] API saved-result restart and duplicate do not regenerate; native real MCP submits exact dispatch; headers/download bytes/hash are actual network observations, not screenshot inferences. Record every observer/method separately.
- [ ] Full configured discovery, prior Node verifiers and source syntax/diff. Sonnet frozen different-family review and bounded independent reproduction. Update guide, status, contract/acceptance artifacts and accurate limits.
- [ ] Only after final PASS: ff-merge, postmerge checks, authorized push, exact remote hash and explicit-repo issue20 closure/reread. No claim that Ticket21 transcript export is built.

## Review focus before tests/code

1. Confirm the shared extraction is narrow enough to prove review-v1 unchanged, including saved-result recovery and monkeypatch seams.
2. Confirm prepared-request/outbox restart rules cannot either lose a saved answer or silently regenerate/adopt unmatched work.
3. Confirm source Stop and identity replacement fence active artifact admission without colliding with review namespaces or cancelling unrelated work.
4. Confirm the appended lifecycle step handles a seven-mark pending intent and retained copied-source disclosure is explicit.
5. Confirm scope/cap/default metadata semantics, version CAS, imported authority stripping and the no-HTML reader meet DA-2 without implementing DA-3.
