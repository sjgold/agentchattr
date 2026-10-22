# Stop a review

Choose **Stop review**, then confirm. The run becomes ineligible for new work before cancellation is attempted. Accepted results, the original source and the frozen design remain available. Pending work for that run is cancelled; other runs and ordinary discussion remain independent.

The status panel distinguishes the saved Stop decision from evidence about local work:

| Evidence | Meaning |
| --- | --- |
| Cancellation requested/delivered | Cancellation is outstanding. |
| Local invocation ended | The owned local request process exited and its IPC cleanup completed. |
| CLI interrupt unsupported | The generic native CLI adapter has no verified per-turn interrupt method. Its process stays running. |
| Unresolved | The cancellation deadline elapsed without proof that local work ended. Ownership stays held. |

API requests run in individual owned child processes. Cancelling one request preserves its persistent seat supervisor. Ending the local connection/process does not establish that a remote provider stopped computing or charging. Remote compute is explicitly unverified.

## CLI termination

For a positively identified app-owned CLI launch, **Terminate context** offers a separate inline confirmation. It explains that the persistent CLI context ends and other queued work for that seat may need recovery. Confirmation binds the exact launch attempt and held dispatch. A replaced or stale launch returns a conflict before any stop control is written.

The owning worker terminates its own client handle. The server requires both worker exit and a matching receipt with the client's exit code before reporting local end. A worker disappearing without that evidence remains unresolved. Unknown processes and unrelated seats are never termination targets.

## Late output and discussion

Typed results from stopped attempts are retained in a bounded quarantine journal and rejected from result admission. They cannot advance the review or start mention cascades. Retries of already accepted results remain duplicate conflicts.

CLI replies should include the dispatch ID supplied in their instructions:

```python
chat_send(sender="your confirmed name", message="Progress or discussion", dispatch_id="the dispatch ID")
```

The server derives run scope from the authenticated seat and owned dispatch. Callers cannot supply an arbitrary run identity. Wrapper API replies supply their dispatch ID automatically.

After Stop, untagged output from that controlled seat has ambiguous old/new scope. It is shown with a quarantine warning and cannot trigger agents. Human discussion and unrelated seats remain available. Fresh independent work has a new dispatch ID and can proceed once the seat's held ownership is resolved.

Quarantine retains at most 64 entries and 8 MiB of content per run, recording evictions. The UI keeps quarantined output separate from accepted results. Full runtime adoption after server restart, corrected clean restart and worker answer-outbox recovery remain later tickets; the persisted Stop fence already prevents stopped work from becoming eligible again.
