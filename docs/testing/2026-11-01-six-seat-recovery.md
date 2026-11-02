# Six-seat send/reply recovery

2026-11-01. Runtime implementation: Sol. History/UI regression: Luna. Integration and live UI check: Codex recovery lead. Independent review: Claude Sonnet 5.5, source inspection only.

## Failures reproduced

- The older Desktop app and canonical app used the same origin and core.js?v=223 URL for different code. Loading old core with new chat history reproduced a missing agentDisplayName exception, an uncleared loading state and no rendered messages. Firefox's actual cache was not directly inspected. The asset URL now changes and static responses use no-store.
- Inherited Windows stdin could not deliver to the owned Antigravity console. A real targeted probe failed before opening CONIN$ explicitly, then succeeded. Text and both Enter writes now require confirmed write counts.
- Managed CLI workers omitted activity reporting. Explicit CONOUT$ observations and injection signals now feed activity heartbeats; unreadable consoles report unknown rather than refreshing a false busy state forever.
- Codex inherited TERM=dumb and stopped at an interactive confirmation. Child-scoped normalization avoids that prompt.
- Codex chat MCP calls required approval while the client forbade prompts. Approval is now scoped to the injected local agentchattr connection; filesystem read-only/never settings remain intact.
- A network-blocked heartbeat could prevent local Stop from being read, leaving a child orphaned. Local Stop polling is now independent of network heartbeats. Real native Stop produced a worker-emitted stopped receipt and exit code.
- Verified ordinary CLI child exit now fails its outstanding ordinary dispatch. Review/artifact, cancelling and unproven ownership remain conservative. Old failed attempts were preserved and individually reconciled with native-exit evidence.

## Real-provider proof

One normal-UI operator message, ID 32, marker RECOVERY-SIX-1101-B, addressed exactly the saved six seats. It appeared immediately in the browser. Exactly one authenticated chat reply per dispatch was observed:

| Seat | Reply ID | Final dispatch |
| --- | --- | --- |
| DeepSeek | 33 | released |
| Claude | 34 | released |
| Muse | 35 | released |
| Codex | 36 | released |
| GLM | 38 | released |
| Antigravity | 39 | released |

Message 37 was a join announcement. All six seats ended available and idle. Queue: zero queued, zero active; two historical failures remain separate. The browser loading spinner was absent. Activity transitions were captured in runtime logs; DeepSeek's brief working interval was captured in the earlier attempt, while the final attempt captured the other five. No timing guarantee is claimed.

Private exact receipts: data/recovery-evidence/six-seat-recovery-six-1101-b-final.json and matching runtime JSONL. Original failed proof and orphan-exit evidence are retained there. This is a real six-provider send/reply proof, not full document-review/Stop/corrected-restart stakeholder acceptance.

Runtime focused verification: 64 passing tests and independent Sonnet recheck PASS. Model-catalog work is separately tracked; styling remains unchanged.
