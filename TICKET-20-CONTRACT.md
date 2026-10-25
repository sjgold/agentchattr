# Ticket 20 requested artifacts, contract draft

Status: proposal for independent review, not an implementation freeze. No product code or tests changed. Base published main `400d6de808dafbaebe1d378b40099c2fead5edd6`; branch `codex/ticket-20-artifacts`. Owner Codex GPT-6.1; reviewer Claude Sonnet 5.5. Standing autonomous backlog authorization applies; no new agents, live provider, Omarchy, Desktop or global changes.

## Scope and source-grounded baseline

Issue20 and specificationv1.7 DA-2 / artifact portion of AT-12: an operator requests an authored document during or after a session, reads Markdown in the app, requests revisions and downloads an exact `.md` file. Persist requested scope and producer/model/run/input/message provenance. Keep old revisions. No mandatory synthesis or universal document format. Issue21 separately owns actual-round transcript assembly and combined export; it depends on20.

Observed baseline:

- No authored-artifact storage/interface exists. `retained_artifacts.py` stores upload-reference metadata; summaries are a separate 1000-character catch-up feature.
- `wrapper_api.py:handle_trigger` has ordinary chat completion and frozen review completion paths. The current provider call is text completion, not a model tool loop. A REST store alone would leave that API wrapper unable to author an artifact.
- Frozen review delivery already uses `review_brief.py`, `result_delivery.py`, `result_outbox.py`, explicit typed admission and the durable queue. It has exact session/run/turn/attempt and launch ownership fences.
- SessionStore permits one active run per channel. Creating a hidden artifact SessionEngine run would conflict with requests during an existing session.
- Current `ResultOutbox` has a strict review-only v1 field set, positive session id and review turn-id grammar. Artifact work must not manufacture a session or weaken v1 validation.
- `renderMarkdown` changes literal backslash sequences and inserts HTML. An exact, safe artifact reader must be separate.
- No existing graphify graph or registered agentchattr graph was found. Open Brain search returned no matching project/artifact context. Source reads are the current evidence, not a graph or inferred memory.

## Approach settled with the reviewer

Reviewer ruling accepts A: a durable artifact request and immutable revisions, one-purpose dispatch using existing queue/seat ownership, factored brief/result authority, explicit CLI MCP submission and structured API admission. B (storage-only REST) omits the API authoring path. C (treat every output phase as a document) imposes a format and conflicts with concurrent requests. The ruling is based on the specification and root's code description; reviewer code-level verification remains pending.

1. Immutable request audit: requester, original channel, optional source run, producer identity, instruction/format, app-resolved frozen scope containing exact message ids, input revision and expected parent revision. Never recompute the scope from later history.
2. CLI submits through an authenticated explicit tool for one dispatch; API returns a strict structured envelope through owned outbox/admission. Ordinary chat and fenced JSON never create artifacts. Idempotency is by dispatch id; invalid, late, stale and wrong-revision submissions are quarantined and labeled as failed attempts.
3. Revisions are append-only exact UTF-8 text with CRLF, SHA-256 and provenance. Requested/confirmed model values come from actual trusted observations or are null with a reason. A revision is a new request, with parent compare-and-set and one pending request per lineage. Failed retries create a new attempt/dispatch.
4. Queue same-seat work normally, never preempt review work. Different lineages may be pending. Retired/replaced producers need explicit reassignment; no automatic rerouting. Source-run Stop cancels that run's queued artifact work only. Operator queued-only cancel uses the existing queue path.
5. Reader constructs DOM nodes without innerHTML, treats raw HTML literally, restricts links and blocks remote images. Include a source view. Download uses text/markdown;charset=utf-8, nosniff, attachment disposition and a safe filename.
6. Pending artifact work blocks archive/rename/delete with request/dispatch ids. Delete retains completed artifacts read-only with source metadata in the retained view. Rename moves mutable channel projections only; frozen requests, source audit and dispatch envelopes stay unchanged. Display scope counts artifacts and shows owner-held errors.
7. Store uses strict held/no-reset loading, atomic-before-memory writes, fingerprint-cached reads, held-startup mode, shared policy binding before the catalog, and fresh-upgrade coverage when the artifact file is absent.

## Concrete proposals requiring review

These are open choices, not implemented promises.

### P1. Purpose-specific authority without review-schema drift

Use a distinct artifact-purpose brief/result schema and domain-separated seal. Factor canonical signing, atomic result persistence and bounded delivery mechanics; keep the exact existing review-v1 validator and recovery unchanged. Artifact payloads include request/attempt/dispatch/producer ids, frozen-scope hash and expected parent revision, rather than fake session/turn ids. Store artifact outbox records in a distinct owned subdirectory so legacy review recovery cannot mistake them for session results. Extend the existing worker's frozen-dispatch branch explicitly by purpose, with no ordinary-chat inference or startup automatic admission.

Review question: accept this strict schema separation and the narrow shared-mechanics extraction before adding authoring, or prefer another reuse boundary? New code must preserve all existing result-outbox and restart tests unchanged.

### P2. Bounded exact content and operator scope

Propose512KiB UTF-8 per authored revision, matching the existing result-content cap, with an explicit oversized error and no truncation. Source-packet size is separately bounded and rejects oversized selected scopes, never silently shortens them. Operator picks server-computed options: accepted results for a source run, accepted results plus associated human discussion, or explicitly checked source messages from that channel. Freeze exact ids, full selected bytes and hashes at request creation; retain run input identity when present. Standalone channel requests may have no source run/input revision and must label that absence. Final exact source-packet cap and option schema need review.

The producer is explicitly selected by authenticated seat identity; arbitrary role names in user-designed sessions cannot be treated as a hardcoded coordinator role. UI calls it the selected author/coordinator. Requested model is captured from its immutable launch configuration; API confirmed model needs a result-specific trusted observation. CLI confirmed model remains null/unverified rather than copied from a model name the agent supplies.

### P3. Stop, cancellation and failed pending requests

Propose terminal failed/quarantined/cancelled requests remain readable and do not silently restart. A retry/reassignment creates a new attempt with a fresh dispatch; version CAS still applies. Active or uncertain queue ownership remains a lifecycle blocker until genuinely settled. Need a precise ruling for an active artifact attempt when its optional source run is stopped: queued records are cancelled as ruled; should active admission be fenced while transport settlement remains separate, or may explicitly requested partial-source authoring finish? Do not reuse the source run_id as the artifact dispatch run_id, which could accidentally cancel/adopt it through session reconciliation.

### P4. Rename upgrade and backups

Propose append an `artifacts` step after the existing seven rename steps in the SAME catalog intent. This preserves the prefix of an old pending rename, including one with all seven prior marks; it can then perform the new idempotent artifact phase before finish. Insertions in the middle would invalidate old persisted step prefixes. Keep the delete step list unchanged; deletion never removes artifact versions.

Propose include authored artifact requests/versions in backup export/import with UID dedupe, stripped imported dispatch/authoring authority and explicit preserved provenance labels. Existing import must remain chunked and resolve each row's channel through catalog policy. No import may start model work or overwrite a local lineage; exact collision and partial-import reporting need review. This is separate from retained-upload-reference metadata, which Ticket19 explicitly excludes from backup export/import.

## Planned bounded packages after contract freeze

| Package | Deliverable and proof |
| --- | --- |
| Store | Request/version/CAS persistence and exact reads; observed RED first, strict upgrade/corruption/atomic fault cases |
| Shared authority | Purpose separation and shared mechanics with existing v1 schemas unchanged; reject cross-purpose, stale, mismatched, duplicate and superseded results |
| Authoring | Real request/dispatch, CLI explicit submit, API structured output and durable delivery; fake-only native/API cases after source/cleanup review |
| Lifecycle and backup | Busy/count/retained integration, append-step pending-intent upgrade, quiescent rename and chunked authority-stripped import/export |
| Reader and revision UI | Request/source selection, revision history, safe node-built Markdown/source/download, retained access and draft-preserving errors; source VM then rendered hostile-content/revision checks |
| Final acceptance | Configured full, different-family review, separately attributed native/API/browser evidence, clean cleanup and exact publication gates |

No helper tests are assigned until the relevant interface is frozen. No generated native/API/browser resource may launch until its source and cleanup are reviewed. The implementation plan will name exact modules/interfaces and observed-red commands after P1-P4 settle.
