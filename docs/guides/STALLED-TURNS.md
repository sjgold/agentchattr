# When a review turn needs attention

The review panel shows a missing delivery acknowledgement, disconnected seat, explicit generation/delivery failure, or overdue response. It retains the source and accepted results. Agent heartbeats show connectivity and never extend a response deadline.

Choose **Wait longer** to extend the current attempt without another model call. A valid late final or question remains authoritative until Retry or Stop wins the coordinator lock. Human turns, questions awaiting an answer, and explicitly paused time do not consume machine response timeouts.

Choose **Retry this turn** to reserve a fresh attempt for the same turn. Completed phases stay completed; source, rules, model and launch settings stay frozen. The old attempt permanently loses admission and mention-routing authority. Request retries reuse the same reserved attempt rather than making duplicate calls.

For a live owned CLI, the panel asks for confirmation before ending that exact persistent context. Other work on the seat blocks replacement. A fresh process must become ready before receiving the retry. Generic CLI relaunch is labeled `same_turn_retry_relaunch`; it does not certify a clean native history. Native login and history files are preserved. Remote provider computation remains unverified after local API cancellation.

If preparation fails, **Repair retry preparation** is explicit. A live prepared context requires its own exact termination confirmation. An exited worker requires a matching receipt with an integer child exit code; an unverified orphan remains blocked. Repair preserves the reserved generation and frozen settings while recording replacement preparation references. Refreshing or monitoring never silently replaces a failed prepared process.

No durable saved answer is offered for a failed delivery in this ticket. Answer outbox/recovery is #13; inspected native CLI answer recovery is #14; changing a participant/model or skipping a turn is #15. Full server-restart process adoption remains #9.

## Timing configuration

Defaults are delivery acknowledgement 30 seconds, response 900 seconds, and monitoring 1 second. The Start dialog can override limits for one run. Server configuration can set partial defaults:

```toml
[session_recovery]
ack_timeout = 30
response_timeout = 900
monitor_interval = 1

[session_recovery_by_adapter.cli]
response_timeout = 1200

[session_recovery_by_adapter.openai-compatible]
ack_timeout = 20
```

Precedence is global defaults, managed adapter defaults, then explicit run settings. Effective role policies are frozen at Start and copied into invocation monitoring. Unmanaged identities use global/run limits. Limits must be positive finite numbers, with booleans rejected. Changing configuration does not rewrite a current turn's allowance.

Windows HTTP uses Uvicorn's app-scoped `asyncio:SelectorEventLoop` factory to avoid CPython's Proactor listener-close failure after WinError 64. Other platforms keep `auto`; MCP thread loops and global event-loop policy are unchanged. Windows select() has a 512-socket limit per loop. Six-seat capacity is verified separately in #16.
