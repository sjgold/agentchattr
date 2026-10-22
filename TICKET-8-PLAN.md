# Ticket #8: accept explicit turn completion exactly once

**State:** Same-AGY contract critique complete; core implementation and focused tests pass. Adapter/UI integration in progress, final independent implementation review pending.

**Authority:** Approved issue #8, spec v1.7 SD-3 / AT-05 and the autonomous execution amendment. #7 is independently reviewed, published and closed. Base main `0029971`. Codex implements; same Antigravity independently reviews the frozen implementation and substantive fixes.

## Verified baseline

`SessionEngine._on_message` currently treats an ordinary chat message from the expected participant as a candidate completion and schedules `_advance` on a timer. Turn/phase comparisons prevent some duplicate timers, but there is no authenticated result event with run/input/attempt identity. A decision card sets a choice marker; arbitrary agent chat can auto-resume a paused run. SessionStore advances phases, stores message IDs and completes runs in separate writes. Its in-memory mutation precedes save, so admission needs explicit rollback on failed persistence.

Ticket #7 provides immutable dispatch metadata, scoped brief retrieval, one active owner per seat and transport-only release. That release must continue to have zero result-admission or phase-advance behavior.

## Settled behavior

1. Ordinary chat, status, typing, heartbeat and `chat_queue_release` never complete an agent turn. Remove ordinary-message timer advancement for new and existing sessions. Preserve chat as discussion. Legacy sessions lacking a bound invocation must not acquire invented identities or silently accept legacy chat as completion; surface that they need explicit restart/migration rather than guessing ownership.
2. Before enqueue, persist a bound invocation containing brief/dispatch reference, run ID, turn ID, attempt ID, input revision and expected stable seat identity. The current immutable brief and queued envelope must agree. Each turn or continued attempt gets fresh attempt/brief identity. Frozen design/source/rules remain authoritative.
3. Both adapters submit one canonical event: `event_id`, `kind` (`final` or `question`), `brief_id`, `run_id`, `turn_id`, `attempt_id`, `input_revision`, content and authenticated seat provenance. Validate every identity against the current persisted invocation before admitting content. Wrong seat403; unknown/stale/stopped/completed identity409 or404 without leaking source; invalid/oversized content400 before mutation. Status is not a final event.
4. Persist event acceptance and the turn's disposition under one SessionStore transaction. Final admission moves the expected phase/turn pointer once, or completes the run, and records the accepted result identity. Question admission retains that phase/turn, records its question identity and enters visible awaiting-input state. Duplicate event IDs, a second result ID for the same consumed attempt, stale attempts and wrong input revisions never advance again. Restore the previous in-memory state if atomic persistence fails.
5. Represent accepted server events durably enough to project result/question messages without accepting them twice. A failure between SessionStore admission and chat rendering cannot create a second accepted result or silently discard the accepted content. This is server-side acceptance bookkeeping, not the deferred API worker result outbox: a worker crash before submitting its generated answer remains outside #8's recovery guarantee. The exact projection/phase-dispatch ordering is an open point below.
6. CLI gets an authenticated MCP event tool in its frozen instructions. Prefer a compact immutable brief reference from which the tool can load the full canonical IDs, then validate all of them against the current invocation; never infer identity from recent chat. Return explicit accepted/duplicate/stale/error information. A successful result does not imply the provider process stopped. Existing explicit queue-release semantics remain separate; a held transport claim can block the next queued turn without causing duplicate admission.
7. For session API turns, require a small explicit response discriminator, such as JSON `{"kind":"final","content":"..."}` or `{"kind":"question","content":"..."}`. The wrapper supplies the immutable identity envelope and stable event ID. A plain status-like response or malformed discriminator must not fall back to a final result. Ordinary API chat outside a session keeps its current text-response behavior. Questions need a deliberate typed path rather than punctuation or text heuristics.
8. Show awaiting-input, the exact question and an operator **Continue** action. Freeform chat or an answer to an unrelated/old choice does not continue the turn. Continue checks the current question/attempt and operator authority, persists the supplied answer as authenticated continuation context and creates a new attempt for the same phase/participant. Old-attempt results are fenced. Preserve original source/design/input revision; answers become separately identified context, not a replacement source packet. Do not discard earlier accepted results.
9. Human participants need an explicit operator-authenticated result action rather than implicit chat completion. Preserve the existing ability to design casts with human roles. Never allow the operator event endpoint to impersonate an expected agent identity merely by providing its name. Use a distinct human-principal contract when the expected cast member is human.

## Contract resolutions

- Accepted events, exact content, consumed attempt and phase disposition share one SessionStore atomic transaction. Each event carries projected_message_id=None until chat projection is back-linked. Projection uses stable UID and an atomic idempotent MessageStore path, including recovery after chat saved but backlink failed. Pending accepted projections are repaired before successor dispatch. This does not recover an API answer lost before server admission; worker outbox remains later scope.
- CLI tool takes brief_id/kind/content, loads immutable canonical IDs server-side and validates every field against persisted invocation and actual bearer identity. API uses the same contract with strict typed JSON and no plain-text final fallback.
- Awaiting-input ignores background chat. Operator Continue validates the current question and creates a fresh attempt; paused runs require explicit operator Resume first. Resume restores the held invocation without dispatching a second one. Human roles use a distinct operator result endpoint; agents cannot use it. Legacy runs remain readable without auto-completion or invented provenance.

## Verification contract

- Red regressions: ordinary expected-seat status/chat/decision cannot advance; explicit final advances once; two concurrent valid submissions consume one attempt; duplicate same ID and second-ID retry cannot advance again; wrong run/input/turn/attempt/seat is rejected without effects; persistence failure preserves prior bytes and in-memory position.
- Real stores and registry, immutable briefs and actual queue. A released transport alone does not complete a turn, and admitted final alone does not bypass a held transport claim. Two coordinator designs execute their own orders through actual typed events.
- Question moves to awaiting input without phase advancement or hidden auto-retry. Old/unrelated chat/choice cannot resume. Valid operator continuation preserves source/design and earlier results while issuing a fresh attempt. Late old-attempt completion fails. Human explicit submission is distinct from agent bearer authority.
- Mixed local fake API and real fake CLI/MCP integration: actual typed final and question events, source identity retained after chat rollover, visible continuation, duplicate/stale admission rejection, and exactly one transition per valid final. No live providers or installed client changes.
- Full suite plus dispatch/frozen-brief/package/seat regressions, JS syntax and whitespace checks. Existing fixtures must adopt explicit completion rather than weakening progression assertions. Same AGY independently verifies the frozen implementation and substantive fixes before publication/closure.

## Tasks

- [x] Same AGY pressure-tests and resolves the admission/projection/question contract.
- [x] Test-only helper captures red identity/idempotence/question regressions.
- [ ] Implement store transaction, engine admission and scoped HTTP/MCP events.
- [ ] Wire typed API result and CLI instructions; operator question/Continue and human result UI.
- [ ] Real isolated verification, frozen same-AGY review/recheck, reviewed publication and closure.

Next owner: Codex finishes adapter/UI wiring and isolated verification; same AGY independently reviews the frozen implementation. No routine human approval is requested. Restart reconciliation, actual cancellation, provider result outbox/recovery and broader capacity remain their later tickets.
