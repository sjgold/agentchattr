# Durable dispatches

Each mention or review trigger is saved as a separate envelope before a wrapper receives it. Channel, prompt, job and frozen-brief reference stay together. Two turns in the same channel remain two turns. Repeating the same dispatch ID is safe only when its contents and intended seat identity match.

Open **Dispatch queue** below the chat header to see pending work, held ownership and failed dispatches. A busy seat keeps later work queued. Other seats can continue independently. The view contains receipt summaries rather than source text or credentials.

## CLI ownership

The injected instruction includes `chat_queue_release(dispatch_id='...')`. After finishing that dispatch's work, the CLI agent calls this authenticated MCP tool. The wrapper observes the resulting receipt before injecting another turn. The tool changes transport ownership only; it does not submit a review result or advance a session.

Console quietness, typing status, heartbeat and ordinary chat never release the seat. A client that omits the release stays visibly awaiting release. Native client compliance has not been established by fake-client acceptance tests. If injection fails or the wrapper exits with work in flight, ownership is retained as uncertain and the pending envelope is preserved. A replacement consumer cannot silently replay that work.

## API ownership

API wrappers process one claimed envelope at a time, with its own prompt and channel or job context. Delivery acknowledgement retries do not call the model again in that wrapper process. Provider and local delivery errors produce failed dispatch receipts. This ticket does not add the durable API result outbox or automatic answer recovery.

## Existing queues and restart boundaries

Older `*_queue.jsonl` files remain untouched and appear as legacy files in the operator view. Updated wrappers ignore them. Their triggers are not automatically imported or executed.

Queue envelopes, ownership and event receipts share one atomic transaction ledger under the configured data directory, `queue/ledger.json`. Wrappers access authenticated HTTP endpoints, not the ledger file. Restarted wrappers use new consumer identities and cannot automatically adopt an in-flight dispatch. Full restart reconciliation, explicit result admission, retry controls and cancellation follow in their designated tickets.
