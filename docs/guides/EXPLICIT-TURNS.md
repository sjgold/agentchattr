# Explicit session turns

A session advances when its expected participant submits an explicit final result. Chat remains available for discussion and progress updates.

## CLI and API participants

CLI instructions identify the frozen turn brief. Retrieve that brief, then submit through MCP:

```python
chat_session_event(brief_id="<ID from this turn's instructions>", kind="final", content="Your result")
```

Use `kind="question"` when the turn needs an operator answer. After finishing the dispatch, separately call `chat_queue_release` with its dispatch ID. Result admission and transport release have separate responsibilities: releasing the transport cannot complete a review turn, and admitting a result cannot bypass held transport ownership.

For session API calls, the model response declares its intent explicitly:

```json
{"kind":"final","content":"Your result"}
```

The alternative is `{"kind":"question","content":"Your question"}`. The wrapper supplies the authenticated run, source and attempt identities. Malformed, empty, ambiguous or status responses fail visibly instead of completing a turn. Plain API chat outside a session retains its text format.

## Operator controls

A typed question appears below the session status strip with **Your answer** and **Continue turn**. Continue keeps the same phase and participant, records the answer and creates a fresh attempt. An old attempt cannot finish the continued turn. The original source and design stay frozen.

Chat answers and choice cards remain discussion. The session Continue button answers the current session question; the existing `/continue` command controls the routing loop guard.

If a human interruption pauses a session, **Resume session** restores its held turn without starting a second invocation. Human participants use **Your turn**, can read the frozen brief/source and earlier accepted results, and finish through **Submit final result**. Their results carry operator provenance rather than agent credentials.

## Saved results and failures

Accepted content and its turn transition are saved together before display. A stable event ID prevents duplicate display during recovery. If display fails after acceptance, **Retry display** repairs it before a successor starts. Retrying an admitted result never advances the turn again.

Event text is bounded to 512 KiB of valid UTF-8 and is never silently truncated. Failed API responses appear in queue/pre-flight diagnostics. Native client cooperation and live provider JSON compliance require separate acceptance; routine checks use local fake clients/providers.

Older runs without explicit invocation identities remain readable, but chat cannot give them machine-verified completion. [Stopping reviews](STOPPING-REVIEWS.md) explains durable Stop, local cancellation evidence and late-output quarantine. Full restart reconciliation, per-turn generation retry and worker result-outbox recovery remain later tickets.
