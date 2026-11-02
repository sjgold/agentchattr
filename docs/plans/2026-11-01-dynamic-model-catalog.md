# Dynamic Pre-flight model catalogs

Requested by Seth during RC2 acceptance, 2026-11-01. Owner: recovery lead; backend Sol, UI Luna. Budgets: backend 25 minutes, UI 20 minutes, then report any unresolved capability.

## Outcome

Choose client, model and supported effort from populated selectors. New and retired models come from a metadata probe, without hand-editing model IDs. Show last-known results immediately, refresh in the background on Pre-flight entry, and expose Refresh models. Opening a dropdown should not repeatedly start network/client probes.

## Boundaries

- Probes enumerate metadata only. No user turn, model generation or team launch.
- Claude native initialize control response is verified locally to return 13 choices and per-model efforts without a user prompt.
- Codex native app-server catalog and model-cache timestamp require explicit freshness provenance; successful RPC alone does not prove network refresh.
- Antigravity models command can fail when native authentication access is unavailable. Empty output from a failed probe is not retirement.
- DeepSeek and Muse have documented metadata endpoints. A metadata-only live check also verified the configured GLM coding endpoint returns a model list. Muse/GLM basic lists omit per-model effort and chat-compatibility details; keep those capabilities unknown.
- A failed or partial refresh preserves the last good catalog and its timestamp. Only fresh, complete sources with explicit retirement authority can mark a missing saved model unavailable. Native picker lists are not exhaustive and never establish retirement.
- Preserve saved model/effort selections in readable history and open forms. Never silently substitute another model. Validate at launch against authoritative supported settings and freeze the effective settings for that worker.
- API keys stay in the existing server-child environment. Catalogs and probe diagnostics must never contain credentials, auth headers or raw private client output.
- Current six-seat team stays running during implementation. Root coordinates one reviewed reload after focused verification.

## Ownership and proof

Sol: model_catalog.py, API/backend validation boundaries and focused tests. Luna: api_seats.js, preflight.html and UI tests. Root: integration, independent review, live rendered verification and status. No new worktrees.

Tests cover appearance/retirement, partial or failed refresh retention, model-specific efforts, preserved historical selections, exact argv/payload, single-flight bounded probes, authentication and proof that probe adapters never submit generation requests.
