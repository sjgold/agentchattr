# Recovery after a server restart

The server preserves review source, frozen settings, accepted results and the current turn. Restarting the server does not send the prompt again.

On Windows, a surviving managed worker becomes ready only after its actual process birth and fresh authenticated connection match its saved launch. The console stays hidden. A PID or old ready receipt alone cannot authorize adoption or termination.

If ownership or readiness cannot be verified, the review remains visible as interrupted. Pre-flight distinguishes these recorded launches from seats that have never started. Unknown ownership blocks a conflicting launch rather than starting another client.

## Operator choices

- **Wait** extends the existing response allowance without another model call.
- **Retry** explicitly supersedes the old attempt while retaining the same turn, source, model settings and prior accepted results. A late old result is rejected and quarantined.
- **Resume saved retry** continues the saved request after another server restart. It does not allocate another reserved generation.
- **Repair failed launch** replaces only the exact failed prepared context after required local exit proof. API cleanup is cooperative; a live context requires exact confirmation. CLI replacement also requires verified client exit.
- **Stop** permanently fences this run across future restarts. It does not stop unrelated work on the physical seat. Unsupported CLI interruption remains unresolved until an explicit owned-seat termination proves local end.

An authenticated result from the current, unfenced attempt can still be accepted after a restart. A managed successor waits for its own verified readiness. Original deadlines and Wait decisions survive; heartbeat and server startup grant no extra response time.

Accepted results are projected into chat once, including a crash after the chat write but before the session backlink. This repairs display bookkeeping. It cannot recover an answer that was never durably accepted.

## Limits

Native Windows ownership is verified with retained process handles. Linux/Omarchy adoption and native AI-client compatibility remain deferred. Legacy runtimes without ownership metadata remain unverified and their files are preserved. Ending a local model process does not establish that remote provider compute stopped.

For isolated fake-client reproduction, see [the review pack](TICKET-9-REVIEW.md). No live provider calls are needed for these checks.
