# Ticket 20 producer capability gate, review draft

Status: proposed next package after the standalone store's full regression. No capability tests or code yet. Store correction ef7f896 is independently accepted; full discovery is running in tracked shell590a3db7. This package does not enable artifact generation or create artifact requests.

## Authority and compatibility

A producer is eligible only through an app-owned managed launch with an explicit artifact-v1 declaration, matching worker birth, current authenticated seat identity and existing verified runtime binding. Registration, heartbeat or model text declaring capabilities cannot grant authority. No inference from agent name, role, adapter, model, configured executable or the server's current source version.

An old snapshot without the new declaration stays usable for existing chat and review work, but is unavailable for artifact requests. No retroactive upgrade of its capability, including after server restart or loading newer source files. An unmanaged wrapper is also unavailable for artifact authoring in this package: the operator must start a supported managed seat. This limitation is explicit in the producer picker later.

The new gate defaults closed. The separately reviewed wrapper package will enable artifact-v1 only when both CLI and API purpose branches exist. Until then, ordinary launches declare an empty capability list. Synthetic supported manifests in component tests are labeled fixture-controlled and do not prove runtime artifact support.

## Proposed binding record

Add an optional server-generated `wrapper_protocol` field to the immutable effective launch snapshot:

```text
{version:1, adapter:"cli"|"openai-compatible",
 capabilities:[]|["artifact-v1"],
 sources:{"wrapper.py":sha256, "cli_worker.py":sha256, "wrapper_api.py":sha256}}
```

The exact source set is adapter-specific: CLI uses wrapper.py plus cli_worker.py; API uses wrapper.py plus wrapper_api.py. Names are fixed app-owned basenames, never paths from a request. Hash raw file bytes. A missing source or read error closes capability eligibility without preventing legacy chat launch; never fabricate a hash. Capability declaration is a source-owned constant initially empty, outside operator package/provider input. Source hashes bind the declaration to the implementation selected for that launch, rather than purporting to attest the Python interpreter or arbitrary local-disk tampering.

Include this optional field in the ownership fingerprint when present. Existing snapshots without it retain their original fingerprint bytes and validation behavior. Reject malformed new records; do not silently drop a declaration before hashing. The server writes the snapshot/launch intent before spawning as today.

`record_worker_birth` validates the manifest and compares its fixed source hashes to the worker's own checkout before adding the exact manifest to birth.json. A mismatch must not advertise artifact capability. The immutable birth record is checked against the snapshot during runtime candidate validation. The current authenticated heartbeat and native-birth verification remain required; a copied manifest by itself is insufficient. No extra claim from `/api/register` or an unauthenticated capability endpoint is trusted. Existing heartbeat payload fields and legacy responses stay unchanged.

## Interfaces and files

| Module | Proposed bounded change |
| --- | --- |
| NEW runtime_protocol.py | Build and validate the fixed source manifest, expose an initially empty supported-purpose constant, compare worker source bytes. No registry, network, launch or provider effects. |
| api_seat_runtime.py | Add optional manifest to server-owned effective snapshots; expose `artifact_producer(instance)` as a detached, metadata-only gate. |
| runtime_ownership.py | Include optional wrapper_protocol in effective fingerprint validation; copy verified declaration into new worker births, preserving absent-field legacy behavior. |
| runtime_adoption.py | Validate declared birth/snapshot agreement and reuse current runtime ownership/identity/freshness checks; never manufacture a declaration on adoption. |
| cli_worker.py / wrapper_api.py | Only the birth/binding plumbing needed by the manifest, if not already covered by the shared birth function. No prompt/result branches here. |

`artifact_producer(instance)` returns an exact shape:

```text
{available:bool, reason:null|"artifact_capability_missing"|"runtime_unverified"|
 "producer_unavailable"|"capability_binding_changed",
 identity_id:32hex|null, adapter:"cli"|"openai-compatible"|null,
 launch_attempt:32hex|null, launch_nonce:32hex|null, fingerprint:64hex|null,
 capabilities:[]|["artifact-v1"]}
```

Only an available result exposes artifact-v1 in capabilities. Missing or stale identity, released/replaced/exited launch, unverified runtime, snapshot/birth disagreement, source disagreement or missing declaration cannot be selected. Generic reason strings contain no paths or exception text. This getter takes the manager lock, performs no policy entry, enqueue, registration or adoption, and returns no secrets or mutable internal records. Later ArtifactService calls it under the engine/catalog boundary before preview and again before request effects, then freezes its exact identity and launch references in the request audit. No artifact routes or picker are added now.

Current source checks: app.register_agent ignores capability fields and calls registry.register(base,label); managed CLI/API registration shares wrapper._register_instance. Runtime heartbeat binds an authenticated identity to candidate launch/birth/receipt and current boot; result_owner currently only handles API result sealing. This package must reuse those ownership checks without broadening result_owner into CLI sealing or weakening its existing contract.

## Observed-red plan, after review only

NEW tests/test_artifact_capability.py, at most12 methods, real manager/registry/temp launch records with process/birth observations explicitly controlled. Initial two actual REDs: old-style or forged registration declaration cannot produce eligible capability; a matching explicit managed binding can, while changing its identity or birth closes it. A missing module/method RED is recorded as such, not behavioral proof.

Expansion covers CLI and API manifests, absent-field legacy fingerprints, malformed/unknown declaration versions, source hash drift, current-token wrong-seat/replaced identity, released/exited/retired attempts, restart adoption without upgrading an old manifest, detached responses, no enqueue or request/index writes, and the production constant remaining disabled until the wrapper package. Existing runtime ownership/adoption, API-seat, CLI-worker, wrapper queue and review-result suites run unchanged. No native process, model or provider acceptance is claimed.

Freeze this contract with Sonnet before helper briefing or tests. The next package after capability acceptance is authority/admission; enabling capability waits for the later wrapper-purpose review.

## Later import constraint

Store load now requires each imported request to own a version. The whole-lineage import package must preserve that ownership or explicitly revisit the representation of retained failed/pending source requests before implementation. Do not relax the store now or invent shared version ownership during import.
