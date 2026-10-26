# Reduced20 backend production ledger

Production CLEARED by reviewer at6788311, with F1-F8 green preconditions. R3/UI/transcript/screen/activation/push excluded. Capability stays empty.

Order: fix replay fixture and record ERR-F honestly; implement source snapshot/typed precheck + shared projector text; implement identity resolver/operator services/status; strict route/middleware/app wiring; source-Stop shared cancel wiring; run root reds and fix reachable fixtures; add F1-F8 discriminating cases and mutation checks; affected baseline and one full builder discovery; independent execution/static review before acceptance. No timing campaign here.

First red correction: one error was a fixture defect, not infrastructure: replay reused an immutable packet id with changed bytes. Existing receipt stays unchanged. Correct with a fresh request/derived ids and actually relaunch producer before asserting replay bypasses live resolution.

## Delivery requirement added by Seth

On2026-10-26 Seth requested: "Before delivery please clean up the file stucture its kinda  a mess". Before delivery, group accumulated ticket/review docs under docs/, separate historical measurement receipts from current guidance, and keep a clear root entry point. Preserve history and verification evidence; prepare a concrete move map from the actual tree and check links/imports/tests after the moves. Schedule this after functional changes settle, before delivery. No file deletion or cleanup move has happened yet.

## Implemented backend, functional checkpoint

- artifact_sources: typed bounded canonical byte/count precheck; exact structural allowlists; same-channel one-lock deep snapshot; accepted-event/continuation source validation, own-message footer and shared projector text; immutable packet staging outside authority.
- artifact_operator: current identity resolver/mapping/global capability, source/producer capture outside authority, common service producer derivation, stored and concurrent replay before prepare, bounded public status/cancel/version/download/session projections and honest durability.
- artifact_routes/app: strict prefix-only operator auth/Host/Origin, raw duplicate-header checks, bounded chunked body/strict JSON, method/media/DTO errors, off-thread work, fixed safe downloads and public-header normalization. App uses shared configured owners. Capability unchanged.
- service/coordinator: public status without repair; source Stop shared by Stop/status/reconciliation; durable cancellation precedes fences; actual affected records/partial failures preserved; post-run requests remain independent.

Original27 ROOT tests first reached25 PASS/one imported-status lockfile difference/one CLI-relaunch fixture error. Fixed status to avoid unnecessary queue I/O for terminal/imported rows; replay uses a genuine fake-API managed relaunch with changed identity, nonce AND fingerprint (model change). CLI restart refusal was valid existing safety behavior, not a product bug. Expanded root46 tests OK3.932s, no provider/native/listener claim.

Focused integration222 ran57.422s with TWO findings: a CHANNELS exact contract sentence had been paraphrased by the scope-doc edit, and newly repeated Stop cancellation affected an explicitly later/stopped-source request. Restored the accurate original disclosure sentence and preserved explicit post-run independence without changing the old test. Targeted8 including Stop/recovery/docs then OK1.207s. Full affected/final builder verification follows the frozen source; old222 run is not labeled green.

Mutation proof:25 in-process mutants killed, source files unchanged by harness;24 had assertion failures (two also had follow-on errors), one typed-refusal mutant was ERROR-only and is labeled weaker. It verifies required subclass semantics, not runtime infrastructure. First harness invocation had a SyntaxError before any mutant ran; corrected the harness anchor and retained that fact. Final receipt/hashes are refreshed with the frozen verification run.

F1-F8 coverage is in the same four root areas, including valid create202/replay200, actual API relaunch, deterministic resolver mappings/family/duplicate identity, readonly terminal unconfirmed fence, raw header/body/error matrices, exact DTO/download values, completed session paging/titles, source detach/identity/phase/footer/count/Unicode bounds, Stop partial/retry/no-policy/same-channel-other-run and reconciliation. Fresh fixture scratch directories self-create. Existing frontend and transcript work stays held for later. No responsiveness screening is claimed here.

## Frozen verification window

Product checkpointccf266223cb6d0581978ae647a07ea2a13d70e09. An initial serialized verification command stopped in the mutation step before any artifact/full suite ran: one mutation now matched the newly added404 guard rather than the intended503 guard, so the selected503-only test correctly did not kill it. The failed receipt is retained as reduced20-mutations-wrong-branch.json, shellb6c05ae0. Corrected to two explicit404/503 mutations with their respective existing tests. Final26 mutants all killed,25 assertion-based and one typed-refusal ERROR-only; two assertion-based checks also produce follow-on errors. Product hashes unchanged by these in-process checks. No product fix followed this harness-target correction.

Artifact affected and ONE full builder discovery now follow sequentially, without timing work or overlapping suites. Results pending; no green or acceptance claim yet.
