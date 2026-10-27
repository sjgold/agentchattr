# Ticket #3: configured API seats

Approved scope: issue #3, spec v1.7 PF-2/3/4 and AT-02. Seth authorized implementation on 2026-10-15. Use existing FastAPI, stdlib subprocess/JSON and OpenAI-compatible wrapper. No new service dependencies or model catalog. Root STATUS.md tracks progress; this document records implementation decisions.

## Design

Reuse `wrapper_api.py` rather than introduce a second turn runtime. Provider templates come from configured `type=api` agents: configured endpoint, default model, optional model choices and declared supported reasoning efforts. Manual model IDs remain allowed and unverified. An empty model means provider default, omitted from the payload. Default adapter supports model selection; reasoning is rejected unless the provider template explicitly declares supported values. No fallback/substitution.

`api_seats.py` owns strict configuration validation and atomic package storage under configured data directory. Packages have stable IDs/names, and multiple seats can use one provider. Each seat stores stable ID, display name, API adapter, provider template ID, requested model/reasoning, standard launch profile and environment-variable secret reference. Never accept literal secret fields or arbitrary execution commands/URLs. Reject malformed stored JSON and preserve it; backup intentional package replacements.

`api_seat_runtime.py` owns immutable per-attempt snapshots, process handles, launch deadlines and inspection/release. Dynamically seed a distinct registry base per seat. Spawn the existing API wrapper with a snapshot path, preserving effective server/data/upload/MCP configuration. Receipt files contain only safe status/provenance; each attempt has its own path. Reuse requires live owned child, fresh connected receipt and matching effective config. Mismatch requires explicit restart. Retry/stop targets only owned handles; server shutdown releases owned children. Server-restart reconciliation remains #9.

Launch proves connection to the local chat adapter, not successful provider authentication/generation. Passive refresh, save and launch never invoke a model. Missing required secret references produce a user-action state. Authentication/confirmed model stay unknown until a completion response provides evidence. Provider response `model` is recorded independently of requested model; no fabricated confirmation. Generation uses the same validated payload builder tested with a fake endpoint. Existing durable turn/outbox/cancellation work remains later tickets.

Authenticated pre-flight APIs expose provider capabilities, packages and runtime states plus save/launch/retry/stop. UI uses existing product tokens and native form controls; it labels manual models unverified, shows requested versus confirmed values, and offers explicit restart for mismatches. Browser polling and backend startup are bounded. No secret values in forms, persistence, command lines or diagnostics.

## Implementation and verification sequence

1. Tests first: strict package/schema round-trip, capability validation, secret rejection, malformed storage preservation and atomic replacement/backup. Implement storage/provider descriptors.
2. Tests first: real fake-HTTP payload delivery and response provenance; modify API wrapper to use shared payload logic and optional immutable managed launch config/receipt, retaining legacy invocation.
3. Tests first: fake-process launch/reuse/mismatch/retry/timeout/exit/missing-secret/receipt freshness and ownership. Implement manager and authenticated endpoints, then real wrapper registration with a fake provider.
4. Add pre-flight controls; browser verify save/reload, two same-provider seats, validation, launch/reuse/stop/retry and responsive layout. Test providers are loopback-only fakes; never use configured live providers.
5. Run full suite and relevant syntax checks once changes settle. Freeze branch commit and evidence pack. Different-family independent review and human sign-off remain required; do not merge/close automatically.

## Review focus

- Concurrent launch/save, stale attempt receipts, config changes while a seat is active and child cleanup on shutdown.
- Fake authentication failures/timeouts/empty provider responses, model receipt differences and unsupported reasoning without silent dropping.
- Secrets in malicious/unknown fields, URLs/config-derived error strings, disk and browser diagnostics.
- Custom data paths/ports and duplicate seat identities without touching external processes or the working Desktop install.
- Windows verification does not certify Linux/Omarchy. No live provider acceptance without an explicitly authorized package.
