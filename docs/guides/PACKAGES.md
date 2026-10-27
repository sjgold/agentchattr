# Saved teams and chat handoff

Choose a saved package in pre-flight, or add seats and **Save package**. A team can include API and interactive CLI seats, each with its own supported model/reasoning choices. The browser remembers the package ID so a new pre-flight tab reopens its saved settings. It stores no credential values in browser storage.

**Launch / reuse selected team** starts missing seats and reuses healthy seats with matching settings. Each seat shows its own result. If one fails, its ready peers keep running. Use that seat's retry/restart controls, then launch/reuse the team again to check the updated selection. Changed running settings always require an explicit restart.

**Leave out of this launch** excludes a seat from the selected team without editing the saved package. It also leaves an already running seat alone; use **Stop this seat** to stop it. Select at least one included seat, then launch/reuse the team to apply those choices.

**Open chat with this team** enables when every included seat is ready and the saved settings still match. The server rechecks the current launch selection when you click it. Unsaved edits, a saved revision change, a stopped/expired attempt or changed client settings prevent that handoff. **Reload saved team** restores the current saved values and discards draft form edits.

Entering chat creates no review session, phases, rounds or model request. Session design stays in chat. The separate **Open chat directly** link remains available for ordinary chat without a package readiness claim.

Readiness keeps the adapter boundaries described in [API-SEATS.md](API-SEATS.md) and [CLI-SEATS.md](CLI-SEATS.md). CLI mention injection does not prove login or MCP tool use. Provider-confirmed models and authentication remain unknown until actual evidence exists.

Launch selections have a frozen package revision, explicit exclusions and bound attempt IDs. Their local receipts contain saved configuration and secret references, not browser session tokens or provider keys. Private MCP identity files still contain the per-instance bearer tokens needed by the adapters. A fresh server requires a new package launch/check; automatic adoption of pre-restart processes belongs to ticket #9.
