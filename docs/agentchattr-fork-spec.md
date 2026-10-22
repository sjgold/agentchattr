# Agentchattr review fork — product and implementation specification

Version: 1.7 · 12 October 2026 · Author: Haalee

Status: implementation specification for review. This document authorizes no deployment, provider purchase, or upstream submission. No application implementation has begun.

## 1. Outcome and scope

Make agentchattr easy to launch and operate for documentation review, adversarial analysis, and other coordinator-designed sessions. Build on its existing chat page, session proposals, roles, and conversation engine.

The entry flow is **open app → pre-flight → select/configure an agent package → setup and launch → existing chat page**. A user-selected coordinator determines teams, roles, and rounds at the beginning of each session. Session creation stays in the existing chat Ask / Design a session feature, after pre-flight hands off. Pre-flight configures and launches the agent package; it does not create the session or decide rounds. The user can modify the coordinator proposal in chat. Neither the six phases in earlier transcripts nor the current manual intake order is a required workflow.

The first usable milestone provides a saved, model-configured team, consistent delivery of review inputs, and reliable Stop/correct/restart. The full scope adds document intake, requested deliverables with an in-app reader, Markdown export, channel archival, and optional independent review with quote checks.

The product direction is one application replacing the separate Warroom and Tribunal user experiences. Flexible coordinator-designed sessions remain the default. Independent review adds fresh API first passes and quotation checks when selected; it shares launch, documents, cancellation, history, and artifacts rather than becoming another product. Do not retire either existing project or migrate/delete its data merely because this spec describes its replacement.

### In scope

- Windows-first bootstrap, environment checks, supervised launch, and saved packages.
- Per-seat client, provider, model, and supported reasoning settings.
- Common input and completion contracts for CLI and API participants.
- Bounded Hermes/OMP diagnosis without blocking the working clients.
- Stop, correction, restart, explicit recipient precedence, and recovery.
- Pasted text and Markdown/plain-text documents retained throughout a run.
- Coordinator-requested artifacts, revisions, preview, and local downloads.
- Discoverable channel management and archive.
- Optional independent API first passes, mechanical quote flags, and synthesis that preserves serious findings.

### Not required for this release

- Rewriting the app in a desktop framework or replacing its chat interface.
- A fixed review methodology, mandatory round count, or mandatory synthesis format for ordinary sessions. Independent review uses the lightweight requirements below.
- Guaranteed compatibility with every model available through Hermes or OMP.
- PDF/DOCX extraction, OCR, interactive HTML artifacts, or public sharing.
- Hosted accounts, multi-user permissions, or remote access.
- Making every API model a general-purpose filesystem agent.
- Mandatory blind-review isolation in ordinary sessions. Independent review builds API requests without peer answers or shared history.

## 2. Baseline and evidence

Start from a recorded commit of https://github.com/bcurts/agentchattr in a proper fork. The inspected Desktop distribution has no Git metadata and contains local additions. Compare it against the selected upstream baseline before carrying over code. Preserve the currently working installation and its data.

The October 9 Combat Paper Walkthrough report records successful use of Claude, Codex, Antigravity, Muse, GLM, and DeepSeek. Classify these as **demonstrated working on October 9**, not as unproven merely because this audit did not relaunch them. This evidence does not establish their filesystem capabilities or every model combination.

OMP and Hermes are installed in the audited environment. Five isolated configuration tests passed; complete interactive review operation remains unverified. CodeBuddy was not resolved on the audit shell's PATH. These observations need timestamps and must not be confused with a live readiness check.

Tribunal runs through OMP with a different execution architecture; the user does not see rounds as live chat turns. Its handoff and August 26 state record completed panel runs. The internal `workflows/lib/hosts/omp.host.ts` file is an implementation detail of that execution path, not an existing agentchattr integration. Use the operational lessons as evidence about prior OMP use, not proof that agentchattr's interactive OMP seat works. No plug-in reuse of Tribunal's runner is assumed. Tribunal's implementation is not a reuse target; its historical behavior informed the product discussion. Its older README does not fully describe the later standalone engine.

Source findings to recheck against the fork baseline:

- API queue processing drops custom session instructions and defaults to 20 recent messages.
- The API adapter exposes no filesystem tools and does not load attachments into model context.
- End Session changes stored state without cancelling active work or queued dispatch.
- Any expected agent chat response can advance a turn; a paused session can resume on that response.
- Selected recipient buttons add mentions even when the user explicitly addresses one agent.
- New API launchers inherit hard-coded port checks and unbounded waits.
- The Windows runner does not propagate a failed CLI exit code.
- OMP's JSON configuration writer can overwrite malformed existing configuration.
- The local history ZIP route requires an absent `archive` module. Upstream contains an `archive.py`; establish whether this is a distribution defect before proposing an upstream fix.

## 3. Product terms

- **Client:** the execution host, such as Claude CLI, Codex CLI, Antigravity, Hermes, OMP, or the direct API adapter.
- **Provider/model:** the service and model used by that client. Do not use a model name as a substitute for client identity.
- **Seat:** a stable member of a package with a display name and launch configuration. Session roles are assigned to seats separately.
- **Package:** a reusable set of seats and an optional preferred coordinator; it does not encode required rounds.
- **Session design:** the coordinator's proposed roles, phases, prompts, and assignments, editable before execution.
- **Run:** one execution of a frozen design and input revision. A corrected restart creates a new run.
- **Turn:** one dispatched unit of work, identified independently of chat messages.
- **Document packet:** immutable source text and metadata supplied to a run.
- **Artifact:** a saved deliverable and its revisions, associated with a session/run. This is an agentchattr feature, not a Clairvoyance Exhibit.

## 4. Pre-flight and launch

### PF-1 — One entry point

Provide one Windows shortcut backed by a small bootstrap. It starts or reconnects to the local server and opens pre-flight. Pre-flight cannot depend on a server the user must first start by hand.

Use the configured port and an app-specific health response, not a generic successful HTTP response or port-listening check. Serialize first-run setup and service startup. Opening the shortcut twice reuses the service. If another application occupies the port, report a conflict without terminating it.

### PF-2 — Honest detection

For each selected seat, distinguish executable found, client startup checked, authentication known/unknown, adapter connected, and ready for the requested capability. Display the resolved executable, client version when available, and last verification time. A successful `--help` is not proof of authentication, file access, or chat operation.

Passive detection must not install packages, invoke a model, or rewrite provider configuration. Setup actions may create dependencies and required client configuration after the user chooses Setup/Launch and sees the required changes. Reuse existing login mechanisms and secret references; never store secrets in saved packages or expose them in diagnostics. Provider calls used for verification must be clearly identified as usage-consuming.

Use bounded checks. Proposed defaults: 15 seconds per passive CLI probe and 60 seconds for server readiness. Login has a distinct user-action state; it must not look like unexplained startup failure. Expose diagnostics and targeted retry.

### PF-3 — Saved packages and models

Each seat stores a stable ID, display name, client adapter, provider if applicable, model or Provider default, supported reasoning effort, and launch profile. A package may contain multiple seats using the same client with different models.

Adapters declare supported settings. Pass the chosen model to the actual CLI invocation or API payload; never silently ignore it. Unsupported combinations produce a specific validation error before execution. Model options come from the client/provider where available; manual model IDs are allowed with unverified status. Do not hard-code this conversation's model catalog.

Keep requested and provider-confirmed model separate. Only show confirmation when a response or client receipt supplies it. A configuration edit is not proof that a running process switched models. Changes affecting an active seat apply to its next launch/run unless that adapter explicitly supports a safe switch.

### PF-4 — Launch ownership

Start missing seats and reuse only healthy seats whose effective configuration matches. A mismatched running seat requires a targeted restart choice. Keep existing batch launchers as compatibility entry points, routing shared behavior through one launcher implementation where feasible.

Track the processes the application owns. Do not kill external processes by executable name. Scope configuration per instance so duplicate seats cannot overwrite each other's MCP identity. Preserve valid existing settings; reject malformed input without replacement and back up intentional changes.

Proceed to chat when the chosen team is ready. If a seat fails, offer retry or explicit removal from the package for this launch. Never silently substitute a provider/model.

## 5. Session design and delivery

### SD-1 — Coordinator authority

The user selects a coordinator and describes the task. The coordinator proposes a session design. Retain the existing editable proposal/casting mechanism; do not require a predefined template. Validate assignments and required capabilities before execution.

Snapshot the accepted design with the run so later template edits cannot alter an active run. Replace the hard-coded four-participant phase and six-role session ceilings with an explicit configurable capacity policy. A phase must support the full selected six-agent team, and a configured package with more than six seats must be representable. Keep concurrency limits separate from membership and turn count. Publish the same effective policy to the coordinator, proposal editor, and backend validator; validate it before launch. Do not silently drop seats or rewrite the intended rounds to satisfy a hidden cap. Phase count, prompt length, and total-turn limits must also be explicit and centrally defined rather than conflicting constants. Long task context and documents belong in the run inputs, not the short phase-prompt field.

Preparation must not start rounds accidentally. Documents may be supplied before or after design. Start requires the user to have finalized the inputs the session depends on. A document-free task remains valid when explicitly intended.

### SD-2 — Equivalent inputs

Every adapter receives a turn envelope containing run ID, attempt ID, turn ID, design revision, input revision, assigned role, phase instructions, task brief, applicable rules, allowed source references, and relevant prior results.

API participants must receive these instructions directly, rather than reconstruct them from a channel. Required documents remain available independently of the recent-message window. CLI participants receive the same intended source set through scoped retrieval or explicit delivery. If one reviewer introduces additional evidence, record it and make a deliberate inclusion decision for subsequent turns; do not pretend all reviewers saw it. For an independent first pass, changed source material requires a new input revision and affected passes before claiming that reviewers assessed the same text.

Treat document contents as source material, not as operational instructions or permission to launch tools. Reject unsupported or oversized input with a useful explanation. Explicit chunking or a user-approved reduced scope may be offered; silent truncation is prohibited.

### SD-3 — Completion and capacity

Status messages, questions, and ordinary chat must not complete a turn. Require an explicit final-result event carrying the current turn identity. Provide a tool/event path for CLI agents and wrap successful API responses in that contract.

Validate run, input revision, attempt, and expected seat before accepting completion. Accept a turn once; reject duplicate and stale results. A question moves the turn to awaiting input, with explicit continuation. It does not auto-advance.

For the initial implementation, one seat executes one owned turn at a time. Queue contention visibly; do not overlap two sessions in one persistent CLI context. A crash or lost connection becomes a recoverable state, not a successful response.

## 6. Stop, correct, and restart

### SC-1 — State contract

Run states: prepared, running, awaiting_input, stopping, stopped, failed, completed. Turn states: queued, dispatched, acknowledged, awaiting_input, completed, cancelling, cancelled, failed, skipped.

Only running runs dispatch new work. Stop is idempotent and immediately makes the run ineligible for dispatch, before attempting provider cancellation. Persist that decision so refresh or server restart cannot resurrect stopped work.

### SC-2 — Actual cancellation

Stop cancels pending turns owned by the run and signals its active invocations through adapter-specific cancellation. Prevent queued callbacks, late messages, and agent @mentions from starting more work for that stopped run. Keep ordinary discussion and unrelated sessions independent.

Show stopping while cancellation is outstanding. After a bounded cancellation attempt (proposed default: 10 seconds), report any invocation still running and quarantine its output. Do not claim provider computation stopped merely because the UI stopped displaying it. Offer a targeted termination of an owned process when graceful interruption is unavailable; explain the impact before terminating a shared process.

Stopping cannot retract already transmitted document contents or reverse incurred usage. Do not implement Stop as channel deletion or global process termination.

### SC-3 — Corrected restart

Allow replacement of the mistaken documents while stopped. Restart creates a new run ID and input revision, links to the previous attempt, and retains the design and seats unless the user changes them.

Use clean reviewer context. API calls rebuild from the new packet; persistent CLI clients must use a supported reset/new session or a new isolated process/context. If isolation cannot be assured, do not label the restart clean. Old messages remain in the abandoned attempt's history but are excluded from new review context and deliverables by default.

### SC-4 — Recovery

After server restart, reconcile persisted turns with known process/adapter receipts. Never blindly redispatch waiting work. Uncertain ownership becomes a recoverable interruption with explicit retry. Use new attempt IDs on retries to reject a late result from the previous attempt.

### SC-5 — Lost turn or lost participant

A failed seat must not force the user to kill the session. Persist each turn before delivery and distinguish queued, dispatched, acknowledged, and completed receipts. Track delivery acknowledgement and response deadlines separately from process heartbeat: an online process is not proof it received or finished a turn. A slow response is not automatically a crashed agent. Deadlines are configurable by adapter/run and visible to the user.

A missed acknowledgement, failed dispatch, disconnected participant, or exceeded response deadline transitions the affected turn to a visible recoverable failure. Name the seat, phase, last acknowledged event, and reason; retain completed turns. Hold dependent work rather than silently advancing. The user can wait/extend, retry that turn, replace the participant, explicitly skip its contribution, or stop the run. None requires restarting successful earlier turns.

Retry uses a new attempt ID after fencing the old attempt. Recovery must use an identified durable result, not an inferred answer:

- **API seats:** persist a result outbox record atomically before attempting to post the completed response. Include a result ID, seat/instance, run/turn/attempt IDs, input revision, content, and creation time. Deliver with that result ID as an idempotency key and retain acknowledgement state. A post failure, lost acknowledgement, or restart can retry delivery of the same result without calling the model again or advancing twice. If model generation failed or no durable result exists, report that no answer is recoverable; offer a new generation attempt. A local persistence failure must be reported, not mislabeled as successful delivery.
- **CLI seats:** permit the operator to select a specific existing channel message ID from the expected seat, inspect its contents, and explicitly attach it to the failed turn. Verify channel, authenticated seat/instance provenance, input/run association where available, and that it has not already completed another turn. Record the selected message ID and operator recovery decision. Missing legacy turn metadata must be labeled operator-attributed, never machine-verified; reject unknown provenance or a conflicting run/input revision. Independent first-pass input restrictions still apply where relevant. This explicit recovery path is the narrow exception to the prohibition on arbitrary chat completing a turn.

If recovery follows a retry, fence the replacement attempt before attaching the selected result and commit the recovery once under the current turn identity. Preserve original attempt provenance. Late answers from superseded attempts are never automatically accepted; explicit recovery cannot bypass a stopped or superseded run or attach old-document work to a corrected run.

Replacement retains the role and supplies the approved input packet and necessary accepted context to a fresh instance. Record the effective seat/model change and affected future assignments; rerun only work invalidated by the change. If a required coordinator disappears, allow the same explicit replacement path. Skipped work is labeled missing in the transcript and final artifact, never represented as agreement. Show skipped contributions alongside the synthesis; never represent missing input as agreement.

Dispatch processing must retain individual turn envelopes in a durable acknowledged queue. Do not collapse distinct triggers from one poll into a single invocation or combine the channel of one trigger with the prompt/job of another. Schedule distinct turns separately under the seat concurrency rule; deduplicate only identical dispatch IDs. A dequeue is acknowledged only after durable ownership transfer; a read-and-clear file operation is not sufficient.

API generation exceptions, empty responses, and result-post failures must emit structured failure events to the session engine with run/turn/attempt identity and a sanitized error category. Console-only errors are insufficient. Explicit failure should surface immediately; a missed failure event is caught by the acknowledgement/response deadline. Record diagnostic events with timestamps without credentials or full document payloads.

Default to visible user-directed recovery, not endless automatic resubmission or silent model substitution. Any configured automatic retry budget must be finite and must not leave the old invocation able to contribute. Show a recoverable failure within one configured monitoring interval after its deadline. Survive page refresh and server restart with the same checkpoint and recovery choices.

User evidence: Seth reports a session freezing until he asked what was wrong, followed by GLM re-submitting a lost turn. This is a reported incident, not a reproduced root cause; the participant caps are separately verified in source. Preserve this distinction in bug reports.

Source-confirmed candidate mechanisms, not incident conclusions: (1) wrapper_api.py catches generation/post exceptions, prints "Error handling trigger", and sends no failure to the session engine; that engine currently has no turn deadline. A later human mention can start a fresh API response from history, resembling re-submission. Check timestamped GLM console/error evidence around the freeze before attributing the incident. (2) wrapper.py reads and clears a batch of queue entries, then injects once using the last channel and last available prompt/job values; distinct CLI triggers in one poll can be lost or mixed. This is a CLI failure candidate, not an explanation for GLM's API turn. The API queue also groups entries by channel, so its durable replacement must preserve distinct turn IDs too.

## 7. Recipient behavior and channels

### RC-1 — Explicit recipients win

For a human message, explicit agent mentions override selected recipient buttons for that message. Multiple explicit mentions target that set; `@all` targets eligible online agents. Without explicit recipients, use selected buttons. With neither, post without triggering agents. Unknown recipient tokens produce a warning rather than falling back to a wider audience.

Parse addresses in user-authored message text, excluding quoted blocks, fenced code, and attached document bodies. Show the resolved recipients before Send. This controls response triggers, not visibility: directed messages remain in the shared channel. Server-side validation is authoritative.

Keep human addressing distinct from session scheduling. During an active run, a manual request to a participating busy seat must explicitly interrupt the run or wait until its current turn finishes; it must not silently create an overlapping turn. Agent mentions cannot bypass the active run's turn order or stopped state.

### RC-2 — Channel lifecycle

Make rename, archive, and delete discoverable. Archive hides a channel from ordinary active navigation while preserving history and artifacts; it can be reopened. An active review must be stopped or completed before archival/deletion proceeds. Archival must block automatic routing into that channel.

Keep `general` protected. Deletion requires confirmation describing what is removed. Never silently delete saved artifacts with a channel: retain them with their source metadata unless explicitly selected for deletion. No automatic cleanup of old reviews.

## 8. Documents and artifacts

### DA-1 — Intake

Support pasted text, `.md`/`.txt`, and individually selected source files (including `.py`, `.mjs`, `.js`, `.ts`, `.tsx`, `.jsx`, `.json`, `.yaml`, `.yml`, `.toml`, `.css`, and `.html`) as plain UTF-8 text. Reject binary or undecodable input and apply the same size/context limits; never execute or render imported source. Multi-file packets are required after the initial build: allow an explicit selection of files to form one review packet, preserving per-file identity and quote attribution. Initial-build intake may handle individual files first. Automatic directory crawling is not implied. Show extracted text, title, size, and source identity before committing an input revision. Snapshot the text; store content hashes and stable references. Later edits to the original file cannot mutate an in-progress review.

The application loads documents and supplies their content to participants. A direct API participant therefore does not need arbitrary filesystem access. Optional project reading is a separate declared capability, scoped to the selected project; review mode must not grant source-writing permissions by default.

Document access checks must account for both the adapter and effective client permissions. A rule saying read-only is not an enforcement mechanism.

### DA-2 — Requested deliverables

Let the user ask the coordinator for a document during or after a session: synthesis, full rounds, recommendations, or another form. Preserve the request and selected scope. Do not impose a synthesis on every session or require one universal format.

Persist deliverables through an application-owned artifact interface available to both CLI and API adapters. The coordinator supplies authored content; the application owns storage, versions, and downloads. Record producing agent, requested/confirmed model when available, source run, source message IDs, input revision, and creation time.

Read Markdown in-app, request revisions, retain earlier revisions, and download `.md`. Sanitize rendering; source content must not execute scripts. Store stable app-owned copies instead of depending on an agent's Desktop write access.

### DA-3 — Actual rounds

When requested, assemble the transcript from stored messages, not model recollection. Include phase boundaries, seat/agent, timestamp, and message ID. Preserve wording and order; mark superseded, cancelled, and incomplete material. Artifact scope must say whether it contains only accepted run turns or also associated human discussion.

Support one combined Markdown file with authored synthesis followed by the actual rounds, or a transcript alone. Exclude abandoned attempts by default and expose explicit inclusion. No 1,000-character limit applies to artifacts: that limit belongs to the separate agent catch-up summary.

Restore the backup ZIP export if absent/broken in the selected baseline, but keep it distinct from document export.

## 8A. Optional independent review — Tribunal's spirit

### TR-1 — Three useful behaviors

Preserve independent first passes, quotations checked against real source text, and serious findings kept visible in the synthesis. Implement these behaviors directly in agentchattr; do not import Tribunal code or reproduce its engine. The coordinator still proposes the session design in chat. Follow-up discussion and cross-examination are optional, not prescribed stages.

### TR-2 — Independent API first passes

Use at least two fresh API reviewer contexts for the independent first pass. Construct each request from the approved document packet, task brief, and assigned lens only. Exclude channel history, peer answers, prior conversation state, and coordinator-proposed findings. Do not attach retrieval tools to these requests. API seats are independent only because the application controls this payload; the existing API wrapper's history-based path does not qualify unchanged.

Results may remain visible in chat: subsequent first-pass requests must still omit them. No sealed result store or CLI isolation infrastructure is required. CLI seats remain available for coordination, synthesis, discussion, and ordinary reviews. If two API reviewers are unavailable, explain the requirement and allow an ordinary review without claiming independence. Report the actual models; different seat names alone do not imply model diversity.

Use the existing immutable document packet and input-size checks. Use the later shared multi-file packet feature when available; do not add a separate Tribunal ingestion system, checkpoint policy, or replacement-model rules. General run ownership, Stop, retry, and stale-result protection still apply.

### TR-3 — Mechanical quotation checks

Ask reviewers to return one fenced `json` block with this shape: `{"findings":[{"document_id":"doc-1","quote":"exact source text","claim":"the concern","severity":"high"}]}`; `severity` is `critical`, `high`, `medium`, or `low`, and optional `line_start`/`line_end` must be supplied together as integers. Parse JSON and validate this small schema deterministically; an absent/ambiguous block, invalid JSON, or invalid finding shape receives a distinct **could not parse** flag, with the raw response retained. Valid siblings can still be checked when an individual finding is malformed. No repair call is triggered. String-match each quote against that document's stored input revision after newline normalization. Mark quotes as matched, unmatched, or missing/uncheckable; empty quotes and unknown source IDs never count as matched. If a line range is supplied, check that range rather than finding the same text somewhere else. Do not use fuzzy matching to turn a mismatch into a match.

Keep the finding and its check result visible. No automatic repair rounds, finding rejection pipeline, or voting follows a failed check. A matching quotation verifies that the quoted text exists, not that the criticism is valid. Unsupported interpretation remains something the reviewers and user must assess.

### TR-4 — Synthesis and delivery

Give the synthesizer the findings and their quote-check flags. Instruct it: preserve every serious finding or explicitly explain why it is disputed; do not quietly omit or downgrade a finding, and do not present an unmatched quotation as verified evidence. Missing reviewers and disagreements must be acknowledged. This is a prompt convention, not an application-enforced verdict guarantee.

Show and export the original serious findings and quote-check flags alongside the synthesis through the shared artifact feature, so the user can inspect omissions or disagreement. No every-peer-must-dispute rule, derived APPROVED/INCONCLUSIVE/CHANGES NEEDED status, automatic synthesis repair, or separate verdict engine. The coordinator can provide a recommendation in ordinary prose. Actual rounds remain available through the existing planned transcript export.

This replaces the parts of Tribunal the user wants in daily use, not its entire feature set. Existing Tribunal records remain untouched.

## 9. Implementation boundaries

Retain the existing Python server and browser frontend. Add focused modules for launch supervision, adapter capabilities, run/turn ownership, document storage, and artifact storage. Extend existing session and channel code rather than building a second orchestration engine.

Proposed adapter interface: probe, validate_configuration, launch_or_attach, prepare_context, dispatch_turn, cancel_turn, inspect_status, and release. Capabilities declare model selection, reasoning selection, scoped document retrieval, fresh-context support, graceful interruption, and confirmation/provenance support.

Persist these minimal records with versioned schemas:

- Package and seat configuration; secret references only.
- Agent instance with process ownership, effective configuration, capability checks, and status.
- Frozen session design and run with input revision and previous-run linkage.
- Turn/attempt with expected seat, durable dispatch and acknowledgement records, cancellation status, result references, API result outbox/delivery acknowledgements, and operator recovery provenance.
- Document revision with text, hash, and origin metadata.
- Artifact revision with Markdown and source provenance.
- Channel archive state.
- Independent-review selection, original findings, source references, and quotation check flags associated with the input revision.

Use the existing storage approach where sufficient, with atomic writes and serialized state transitions. Do not introduce a database migration solely for this feature set. If implementation establishes that transactional guarantees cannot be met, present a specific storage change separately. No in-place destructive conversion of existing histories.

Keep new endpoints local and authenticated under the existing security model. Launch requests must select registered adapters and validated arguments, never arbitrary shell strings. Preserve legacy data and batch entry points. Keep generic fixes separate from product additions so upstream PRs remain possible.

## 10. Delivery sequence

### A — Baseline and adapter audit

Record upstream commit; compare local files; preserve working installation/data. Repair verified defects in configuration preservation, exit propagation, API turn instructions, and missing baseline files. Inspect Tribunal's OMP-driven execution and recorded live-run lessons before diagnosing OMP here; do not assume the two architectures are interchangeable. Give Hermes and OMP one focused diagnostic pass each, capped initially at one working session; unresolved clients remain clearly unavailable with evidence and next steps.

Exit: adapter matrix distinguishes recorded successful use, current probe results, and live acceptance. No client is called ready solely because a launcher exists.

### B — Reliable launch and run ownership

Implement bootstrap, package persistence, model settings, instance isolation, consistent turn inputs, explicit completion, and Stop/correct/restart. These form the first usable milestone; do not hide unmanaged processes behind pre-flight.

Exit: one shortcut launches a saved team, a six-seat phase works, a stalled or failed turn becomes visible with wait/retry, and a review can be stopped and restarted with corrected pasted text without accepting stale output. The first milestone includes durable per-turn delivery and explicit completion. Full restart reconciliation and recovery of existing answers/replacement/skip follow; persisted Stop must already survive restart.

### C — Documents and daily controls

Add file intake, persistent document packets, recipient precedence, channel archival, and restoration of backup export where needed. Preserve coordinator-designed proposals.

Exit: all selected participant types receive the intended source revision across a multi-round session; directing a message to one agent never wakes the selected group accidentally.

### D — Deliverables and release

Add requested artifacts, Markdown reader, revisions, and exact transcript export. Validate the complete workflow and package the entry point. Document unsupported clients/capabilities and recovery paths. General upstream fixes may be proposed independently; release does not wait on their acceptance.

### Post-initial-build — Multi-file packets

Support selecting multiple text/source files into one immutable review packet, with a preview of the file list, per-file IDs, individual and aggregate limits, and no silent truncation. Deliver the same packet revision to the selected reviewers and bind quote checks to the named file. Verify two files with identical quoted text cannot validate a citation against the wrong file, and that changing one file creates a new packet revision. This is required follow-on scope, not a blocker for the initial launch/Stop milestone.

### E — Lightweight independent review

Add fresh API first-pass payloads, mechanical quotation checks, and synthesis instructions with original serious findings and check flags retained alongside the output. Use the shared document, run, and artifact infrastructure. No Tribunal code import or separate review engine. This follows the everyday-use release and does not delay launch/Stop.

Exit: the lightweight acceptance checks pass and one real review demonstrates independent inputs, useful quote flags, and readable synthesis. Describe this as replacing the user's chosen Tribunal workflow, not full Tribunal feature parity. Retirement or migration remains a separate explicit choice.

Implementation model preference: Sol for the next build steps. Astra is an optional escalation, not a prerequisite: on tickets #7-14 and #24, ask the user to bring it in if builder/reviewer disagreement or a reproduced correctness failure remains unresolved. Supply a frozen change and compact reproduction/evidence pack. Do not automatically launch Astra or replace the independent different-family reviewer with it. This is a build preference, not a hard-coded product model list. Every implementation ticket requires independent review by a different model family against a frozen change and reproducible evidence. Reviewer choice is driven by available quota from the user-configured pool: Meta Muse 1.3, DeepSeek Flash 4.1, Grok 4.7, and GLM 5.3 (user-provided labels; resolve actual provider/model IDs at execution time). Do not require Claude/Opus. Record builder and reviewer model identities, findings, and recheck outcome. If no eligible reviewer has quota, leave review pending rather than self-approving. Execution-policy amendment, 2026-10-22: Seth removed routine human approval/sign-off gates and authorized autonomous implementation, reviewed merge/push and ticket closure within this approved scope. Use the same Antigravity reviewer/tester from tickets #3/#4, including independent recheck of substantive fixes. This direct instruction supersedes the older suggested reviewer pool and human completion gate; independent verification remains mandatory. Escalate material scope decisions or live usage outside existing authorization. Cancellation, routing, and storage changes must receive particular scrutiny.

## 11. Acceptance and verification

Use deterministic fake adapters for routine tests. They must simulate slow startup, failed login, a crashed turn, partial output, duplicate completion, delayed completion after Stop, and unsupported cancellation. Real-provider acceptance is separate and consumes actual usage; schedule it explicitly with the user.

- **AT-01:** Opening the shortcut twice creates one server. Occupied ports and startup failure produce actionable errors within the configured timeout.
- **AT-02:** A saved package round-trips client/provider/model/reasoning values. Unsupported values are rejected. Requested models reach the actual launch arguments/payloads. Confirmation is never fabricated.
- **AT-03:** Two seats on one client cannot overwrite configuration or cross-deliver messages. Malformed existing config remains byte-for-byte unchanged on failure.
- **AT-04:** CLI and API turns receive the selected phase prompt, rules, and identical intended document revision. The document remains available after more than 20 messages. Individually selected `.py` and `.mjs` inputs round-trip as plain text without execution; binary/undecodable inputs are rejected.
- **AT-05:** Status text cannot complete a turn. Duplicate or old-attempt completion cannot advance another turn. Questions await explicit continuation.
- **AT-06:** Stop during queued, active, and completing work blocks further dispatch and cascading mentions. Late output is quarantined. Unsupported cancellation remains visibly unresolved.
- **AT-07:** Run document A, Stop, replace with B, restart. Every new reviewer context uses B; no A completion enters the B transcript or synthesis. Other runs continue.
- **AT-08:** A server restart during a waiting turn does not blindly duplicate work. Stopped runs remain stopped across refresh and restart.
- **AT-09:** With all seats selected, `@claude` triggers only Claude. Multiple explicit recipients, `@all`, no selections, unknown names, and mentions inside documents behave as specified.
- **AT-10:** A coordinator proposes two different session structures for two tasks; the application validates and executes either without forcing six fixed phases.
- **AT-11:** Archive/reopen preserves messages and artifacts. Active work blocks channel removal until stopped. Delete confirms consequences and protects general.
- **AT-12:** A requested document is readable, revisable, and downloadable. Combined export contains actual ordered messages and provenance, not a reconstructed transcript or catch-up summary.
- **AT-13:** A complete live review succeeds with the selected release-supported clients. Record configuration and date; Hermes/OMP are optional until they pass the same end-to-end check.
- **AT-14:** Capture the API first-pass request payloads with fake adapters. Each contains the approved packet, brief, and lens, with no channel history, peer response, coordinator findings, prior conversation state, or retrieval tools. Publish one response before constructing the next request and verify it is still excluded. Ordinary CLI reviews remain available.
- **AT-15:** A valid JSON findings block yields extracted findings; absent/multiple blocks, malformed JSON, and invalid fields produce distinct parse flags with raw text retained. Correct quotes match their selected document revision; fabricated, empty, wrong-document, and missing quotes receive visible flags. Supplied invalid line ranges cannot pass. No automatic repair call is made. A matched quote is not labeled a validated claim.
- **AT-16:** The synthesis request includes original findings, quote-check flags, and instructions to preserve or explicitly address serious findings. The artifact and export retain original serious findings and flags even if fake synthesizer output omits them. No application-derived verdict or voting rule is required.
- **AT-17:** Retired in v1.4: Tribunal-specific replacement/checkpoint rules removed. General attempt identity, model honesty, and stale-result protection remain covered by AT-02, AT-05, AT-07, AT-08, and AT-22.
- **AT-18:** Retired in v1.4: automatic repair exhaustion and derived-verdict enforcement removed. Missing participants remain visible under SC-5; synthesis guidance and flags are covered by AT-16.
- **AT-19:** One real independent API review produces readable synthesis with original serious findings and quote flags. Stop/correct/restart works during first passes and synthesis. Ordinary session behavior and existing Tribunal data remain unchanged.

- **AT-20:** A phase containing all six selected agents validates and schedules all six; a configured seven-seat package is representable. Exceeding the declared policy fails before launch with the same explanation in coordinator context, editor, and backend. Concurrency limits do not remove members.
- **AT-21a — API freeze path:** Make a fake API model raise before producing output. The session receives a typed failure and retains completed turns, rather than waiting indefinitely for an answer. No recoverable result is offered. Drop that failure event separately and verify the deadline fallback. Exercise explicit retry and replacement.
- **AT-21b — CLI batching path:** Queue two distinct turn envelopes within one polling interval, including different channels/prompts/jobs. Both retain their identities, are scheduled separately, and receive receipts; no field mixing or last-trigger-wins loss. Repeat for two API turns in one channel and replay an identical dispatch ID to verify deduplication.
- **AT-21c — Result recovery:** Persist an API result, fail the post, restart the wrapper, and recover from the outbox without another model call. Separately lose the successful post acknowledgement and verify one accepted result. Recover an operator-selected CLI message from the expected seat; reject wrong-seat, conflicting-input, duplicate-use, and unknown-provenance messages. Label operator attribution where legacy metadata is absent. Persistence failure never claims a recoverable saved answer.
- **AT-21d — Participant loss:** Drop a dispatch acknowledgement, disconnect GLM, and simulate a live-but-stalled process as distinct cases. Each shows the correct recoverable state and preserves earlier accepted turns. Wait/extend, replacement, skip, and coordinator replacement produce attributable outcomes without killing the run.
- **AT-22:** Deliver an old GLM attempt after retry or replacement and refresh/restart during recovery. No duplicate advancement occurs; the failed-turn checkpoint survives. A skip remains visible alongside the synthesis and in export.

Completion means the acceptance evidence is recorded, the app starts through the packaged entry point, existing data remains accessible, and unresolved adapter limitations are visible. The spec itself is not evidence that any of these features have been implemented.

## 12. Source references

- Local audit: `windows/*.bat`, `wrapper.py`, `wrapper_windows.py`, `wrapper_api.py`, `config_loader.py`, `session_engine.py`, `session_store.py`, `agents.py`, `router.py`, `store.py`, `summaries.py`, `mcp_bridge.py`, `app.py`, and `static/{index.html,chat.js,channels.js,sessions.js}`.
- October 9 evidence: local Combat Paper Walkthrough report (2026-10-09), Appendix A; private reference, not bundled.
- September 28 example: local snake roguelite design-review transcript; private reference, not bundled.
- Tribunal comparison: local project context and August 26 state/handoff records; historical evidence only. No source-code import planned.
- Upstream: https://github.com/bcurts/agentchattr. Its current commit and installed CLI contracts must be verified during implementation; cached web pages are not a pinned build baseline.
