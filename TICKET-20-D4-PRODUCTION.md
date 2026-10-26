# Ticket 20 D4 production ledger

Status: production CLEARED by reviewer after945ea482 red audit (own30tests33FAIL/28ERROR24.8s). Implementation not yet accepted. No R3/operator/capacity/activation/push. Capability stays empty.

## Ordered work and verification

1. Correct P1 deterministic startup/no-spurious-held/queued-positive test, P2 masked hooks, P3 genuine fence evolution, P4 weak peers/ownership variants; retain observed-red baseline. Freeze all private seams in one PHASES table (P6).
2. Implement shared legacy Event before authoring load, capture/snapshot pure predicate and outside-authoring observational scan. Run owner/integration + phase tests for actual store behavior.
3. Implement frozen diagnostic intents/guards/receipts and a per-invocation A/B/C driver with no owner transaction state. Explicit per-caller locked cores preserve ordinary behavior; every B failure propagates before C, private signal caught only by driver.
4. Refactor startup into outside-boundary inventory and fresh per-item operations/counts/marks; adapt MCP to combined service without caller boundary. Run D4 and A1/R1/R2 support green.
5. Add all P5 missing contract coverage (red-before-source where possible, else mutation-checked green), ownership/receipt/guard mutations, artifact affected selection and ONE full discovery on frozen source. Do not run suites in a timing window.
6. Add explicit production gate mode on same tools:10+ fresh samples per caller A/C/peer during heavy B, structural reads outside boundary, full/held4MiB import gates. Retain every sample/retry, no threshold changes. Miss returns to review. Independent reviewer runs/static audit required before acceptance.

## Mechanism decisions

- Ruling: diagnostic context is passed explicitly through private locked cores (origin/mode), never placed on an owner or in a new ContextVar. The existing A1 packet invocation scope may span A/B/C.
- Ruling: guards store immutable canonical request/audit, normalized queue claim and retained result/ACK/disposition snapshots. C rereads fresh authority and compares; it never rereads or writes diagnostics. Result-based seal checks stay for admission/recovery/ACK, while terminal/unmatched startup retains existing launch-bound/no-added-seal behavior.
- Ruling: _DiagnosticRequired inherits directly from Exception and is never intercepted by existing ValueError/RuntimeError storage catches. Only the driver catches it after releasing A; B errors propagate with no fabricated receipt.
- Ruling: startup selection is deterministic by sorted channels and original per-channel request order. Tests explicitly seed selection order; a fresh row check before omitted marks prevents spurious storage-unavailable warnings as well as stale writes.

Each step's actual edits/checks and any changed decision will be recorded below. Existing failed gates and raw DESIGN receipts retain their original attribution.

## Step1/2 checkpoint

P1-P4 test corrections observed red before source:30methods45FAIL/28ERROR27.851s, tracked14dc5da0. Hooks now collect writer/marker observations and assert after production returns; deterministic same-channel task selection tests both still-queued positive and changed-active/no-spurious-held negative. Ownership unsupported cases cover all3locks and noncallable/raising/None/nonbool results. Startup terminal peer actually cancels another request; structural reads progress while a separate thread holds the boundary. Real fence evolution precedes release. No unused pause argument remains.

Store implementation adds one shared Event before authoring load and uses it for sticky legacy refusal in both owners. Capture/snapshot share a memory-only predicate, including imported/no-attachment and non-null authoring errors. Diagnostic transactions check the marker before and after metadata replacement; landed bytes are retained and C never gets a successful receipt after legacy discovery. Filesystem orphan scans now execute outside the authoring lock. A1 packet helpers unchanged.

Executed56tests8.663s PASS (owner/integration plus marker-before-load/capture-no-diagnostic-lock/orphan-scan release). This is partial implementation evidence, NOT complete D4 green or a timing gate. Service driver/startup/MCP and P5 coverage remain.
