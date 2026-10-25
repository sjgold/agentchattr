# Ticket 20 producer capability gate, review draft

Status: contract C1-C8 approved at85179c0; candidate implemented at9ae0842, component verification green and independent review pending. Store correction ef7f896 is independently accepted and full discovery passed1398 tests215.215s (four skips), implementation-owner run590a3db7. This package does not enable artifact generation or create artifact requests.

## Authority and compatibility

A producer is eligible only through an app-owned managed launch with an explicit artifact-v1 declaration, matching worker birth, current authenticated seat identity and existing verified runtime binding. Registration, heartbeat or model text declaring capabilities cannot grant authority. No inference from agent name, role, adapter, model, configured executable or the server's current source version.

An old snapshot without the new declaration stays usable for existing chat and review work, but is unavailable for artifact requests. No retroactive upgrade of its capability, including after server restart or loading newer source files. An unmanaged wrapper is also unavailable for artifact authoring in this package: the operator must start a supported managed seat. This limitation is explicit in the producer picker later.

The new gate defaults closed. The separately reviewed wrapper package will enable artifact-v1 only when both CLI and API purpose branches exist. Until then, ordinary launches declare an empty capability list. Synthetic supported manifests in component tests are labeled fixture-controlled and do not prove runtime artifact support.

## Proposed binding record

Add an optional server-generated `wrapper_protocol` field to the immutable effective launch snapshot:

```text
{version:1, adapter:"cli"|"openai-compatible",
 capabilities:[]|["artifact-v1"],
 sources:{fixed_adapter_source_basename:sha256, ...}}
```

The source set is an explicit per-adapter constant in runtime_protocol.py, containing its own file and the full repo-local static import closure of the adapter entry files. A read-only AST inventory of the current source found12 CLI files and26 API files. These are the initial fixed lists, each also including NEW runtime_protocol.py:

- CLI entries wrapper.py and cli_worker.py: api_seats.py, cli_seats.py, cli_worker.py, config_loader.py, launcher.py, mcp_proxy.py, process_identity.py, queue_client.py, runtime_ownership.py, wrapper.py, wrapper_unix.py, wrapper_windows.py.
- API entries wrapper.py and wrapper_api.py: api_invocation.py, api_seats.py, channel_lifecycle.py, cli_result_recovery.py, cli_seats.py, config_loader.py, document_inputs.py, invocation_evidence.py, launcher.py, mcp_proxy.py, participant_replacement_store.py, process_identity.py, queue_client.py, result_delivery.py, result_outbox.py, review_brief.py, runtime_ownership.py, sealed_result_io.py, session_capacity.py, session_store.py, turn_events.py, turn_recovery.py, wrapper.py, wrapper_api.py, wrapper_unix.py, wrapper_windows.py.

Names are fixed app-owned basenames, never paths from a request. Hash raw file bytes. A missing source or read error omits wrapper_protocol from that new launch, closing artifact eligibility without preventing legacy chat launch; never fabricate a hash. Capability declaration is a source-owned constant initially empty, outside operator package/provider input. The wrapper package must extend these constants for new purpose-branch modules before enabling artifact-v1. An AST test recursively follows all repo-local Import/ImportFrom statements, including conditional imports, and fails if any reachable module is absent from the fixed set. It resolves local modules/packages without executing them. Every repo module containing the artifact branch must belong to this set, including shared delivery/queue/protocol helpers. The larger manifest is copied to birth.json unchanged on a match. This binds the listed repo source bytes, not the interpreter, third-party packages, arbitrary dynamic imports or local-disk tampering.

C1 exact fingerprint edits:

- Add wrapper_protocol to runtime_ownership._EFFECTIVE_FIELDS. Its existing `if key in snapshot` construction preserves legacy absent-field bytes. Capture the current HEAD legacy effective-payload golden fingerprint BEFORE changing source, then assert it unchanged after.
- Include a validated deep copy of wrapper_protocol in ApiSeatManager._provenance_effective's explicit top-level whitelist. Thus launch_provenance's projected fingerprint also reflects protocol changes; it remains distinct from the ownership fingerprint.
- _launch_effective intentionally fingerprints the complete effective dict, including the optional manifest, for same-settings/restart comparison. A changed protocol or source hash requires an explicit new/restarted attempt; an already-running seat is never silently upgraded.
- ArtifactService freezes audit.producer.fingerprint from new_launch_identity's ownership fingerprint, with that same attempt and launch_nonce, NOT the projected launch_provenance fingerprint. Both adapters require all three refs non-null in this ticket; the store's looser CLI shape remains for legacy/import data only.

Reject malformed new manifests, unknown versions, wrong adapter or invalid source sets during snapshot validation; do not drop a malformed declaration before hashing. The server writes the snapshot/launch intent before spawning as today.

C2 deterministic birth rule: record_worker_birth validates the snapshot manifest and compares every fixed source hash to the worker's own checkout. On MATCH it writes the exact wrapper_protocol field into birth.json. On MISMATCH or source read failure it OMITS that field entirely, closing capability while retaining the existing chat birth fields. It does not write a partial or replacement manifest. Existing immutable-birth comparison stays exact: re-running the SAME attempt with an outcome that would change birth.json (match to mismatch or mismatch to match) refuses and never overwrites the record; a new attempt is required. Test both matching repeats plus both conflicting outcome directions. Runtime candidate validation permits an omitted birth manifest as a capability-closed legacy-compatible runtime, but a present declaration must equal the snapshot exactly. Adoption never fills an omitted field from newer source.

Current authenticated heartbeat/native-birth verification remains required; a copied manifest alone is insufficient. No extra claim from /api/register or an unauthenticated capability endpoint is trusted. Existing heartbeat payload fields and legacy responses stay unchanged.

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
 "producer_unavailable"|"unmanaged_producer"|"capability_binding_changed",
 identity_id:32hex|null, adapter:"cli"|"openai-compatible"|null,
 launch_attempt:32hex|null, launch_nonce:32hex|null, fingerprint:64hex|null,
 capabilities:[]|["artifact-v1"]}
```

Only an available result exposes artifact-v1 in capabilities. Missing or stale identity, released/replaced/exited launch, unverified runtime, snapshot/birth disagreement, source disagreement or missing declaration cannot be selected. Generic reason strings contain no paths or exception text. This getter takes the manager lock, performs no policy entry, enqueue, registration or adoption, and returns no secrets or mutable internal records. Later ArtifactService calls it under the engine/catalog boundary before preview and again before request effects, then freezes its exact identity and launch references in the request audit. No artifact routes or picker are added now.

Reason meanings: unmanaged_producer is a live registry identity without an app-owned managed snapshot/birth/nonce binding, requiring a managed launch. artifact_capability_missing is an otherwise verified managed runtime with no artifact-v1 declaration. runtime_unverified is pending/unproven current ownership or heartbeat. producer_unavailable is absent/released/retired/replaced/exited work. capability_binding_changed means a persisted expected snapshot/birth/manifest or identity relationship disagrees during recheck, including after a gate once passed; do not silently downgrade or upgrade it. No mutable capability cache is authoritative.

C5 route projection: launch_nonce is an internal correlation value, not the authentication token, but must never appear in public routes/UI. artifact_producer returns it internally to ArtifactService only; later operator read/list/preview responses project request audits with producer.launch_nonce omitted. Dispatch authority still uses the authenticated seat token plus owned dispatch.

C7 authority dependency: gate output is valid only at that evaluation. Creation rechecks it under the outer boundary, and admission MUST compare current live seat identity/attempt/nonce/ownership fingerprint against the frozen request audit again. Released/replaced/exited or different binding results are quarantined, never admitted from an earlier successful gate. This is a required authority/admission test package dependency.

Current source checks: app.register_agent ignores capability fields and calls registry.register(base,label); managed CLI/API registration shares wrapper._register_instance. Runtime heartbeat binds an authenticated identity to candidate launch/birth/receipt and current boot; result_owner currently only handles API result sealing. This package must reuse those ownership checks without broadening result_owner into CLI sealing or weakening its existing contract.

## Observed-red plan, after review only

NEW tests/test_artifact_capability.py, at most12 methods, real manager/registry/temp launch records with process/birth observations explicitly controlled. Initial two actual REDs: old-style or forged registration declaration cannot produce eligible capability; a matching explicit managed binding can, while changing its identity or birth closes it. A missing module/method RED is recorded as such, not behavioral proof.

Expansion covers CLI and API manifests; the pre-change legacy golden fingerprint; provenance inclusion; static repo import closure; all C2 match/mismatch/repeat/conflicting birth outcomes; malformed/unknown declaration versions rejected at snapshot validation; source hash drift; current-token wrong-seat/replaced identity, released/exited/retired attempts, restart adoption without upgrading an old manifest, detached responses, no enqueue or request/index writes, and the production constant remaining disabled until the wrapper package. Existing runtime ownership/adoption, API-seat, CLI-worker, wrapper queue and review-result suites run unchanged. No native process, model or provider acceptance is claimed.

Freeze this contract with Sonnet before helper briefing or tests. The next package after capability acceptance is authority/admission; enabling capability waits for the later wrapper-purpose review.

## Later import constraint

Store load now requires each imported request to own a version. The whole-lineage import package must preserve that ownership or explicitly revisit the representation of retained failed/pending source requests before implementation. Do not relax the store now or invent shared version ownership during import.


Approved checkpoint85179c0: pre-change legacy golden bce6783ec65b26921583bf847bc9a226f63cbe0289da81a75efe25da91e9155f captured before source changes, baseline151 PASS12.312s. Root2 static checks kept separate (golden PASS, missing-module closure ERROR0.006s). Helper initial2 genuine missing-interface ERROR0.042s follows one disclosed mixed source/fixture attempt0.013s corrected only by seeding the actual registry. Production implementation starts after this evidence; expanded12 remains held.


Candidate checkpoint: initial helper2 and root static2 PASS4/0.299s after implementation. The fixed-set static check now also rejects unreachable listed files except deliberately listed runtime_protocol.py. Expanded behavior12 is frozen compile-only; unchanged151 affected-suite after-run and one focused12 are next. Production SUPPORTED_CAPABILITIES remains empty; no authoring branch enabled.


Frozen9ae0842 verification: helper unchanged12 PASS1.377s, static-finalized SHA25680174baf4da1c41d9df542eb0f2a9938a1e9bcea810a1b65b9cdb192cb3b058f. Unchanged same151 after12.975s PASS (before12.312s), trackedf9c36e92. Full19886263 and independent review running. No capability is enabled in production and no artifact requests/branches exist yet.


P1 correction0ade4b7: live pending launch without recorded birth returns runtime_unverified; after birth but before authenticated heartbeat it remains unverified; the controlled verified binding then becomes available. Root progression RED1FAIL0.069s -> focused15PASS1.577s. Original full1412/222.080s failed7FAIL+9ERROR/4skips. Exact affected15 methods reproduce same7+9 in5.654s, then PASS6.035s after only canonical-field-copy corrections in existing fixtures, assertions unchanged. Real-launch/legacy consumer guards2 PASS1.173s. A new full and independent review remain required; source capability stays empty.


Corrected frozen full7a9226e PASS1415 tests215.255s (four skips), tracked83c09a8b, implementation owner only. Separate P1 source0ade4b7 and fixture/recovery7a9226e await Sonnet recheck; no capability enablement or authority/admission expansion yet.


Independent clearance at265d95f: reviewer106 tests13.578s and6 probes PASS; P1 source and canonical-field fixture diffs read. Full1415 remains implementation-owner evidence. Production capability stays empty until reviewed purpose branches.
