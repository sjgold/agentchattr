# Ticket 20: merged-base DESIGN checkpoint

Status: tools frozen for the ONE reviewer-authorized run after G1-G5 edits. No D4/R2 acceptance, source implementation or activation follows. Merge baseline356a26d, previous tool freeze7d756bde. This document records the builder-run results separately from all previous failed gates and isolated A1 evidence.

## Final harness-only delta from 7d756bde

* G1: facade measures request_diagnostics for attached local and unattached imported ids as one observation row, after heavy/summary and before structural metadata replacement. Validate eight attached ids/overflow2 versus empty/0. Fixed per-fixture order is heavy, summary, request_diagnostics, structural_read.
* G2: untimed provenance verifies unpatched pathlib.Path.replace and builtin os.fsync, detects diagnostic owner, D1 scandir and D2's actual byte-identical single-write behavior using a real disposable file. Record detected schema, dirty flag/git status, source hashes, all loaded test fixture module hashes, sealed_result_io/worker hashes, tool self-hash and both ancestor labels in each receipt. Before timing the only permitted replace patch is the harness retry counter; fsync is untouched.
* G3: facade retry counter covers diagnostic metadata AND quarantine body-object replacement. Authority counts all replace PermissionErrors in A/C. Real retry behavior is preserved.
* G4: tools/test_artifact_checkpoint_controls.py retains runnable synthetic orchestration/import trap/no-verdict/provenance checks and cleanup-result preservation. Current shape adds request read, so the original synthetic90authority/28facade check becomes90authority/37facade with retained phase observations after injected first-sample failure. Three tests pass0.639s; no real timing in this test. A cleanup error is a separate row/observation alongside a completed result, never a replacement result.
* G5: caches are warm after setup. Only structural_read forces metadata reread; cold-restart tails are not measured. Untimed distinct summary key one is recorded before the summary hold. Heavy body(...).decode(ascii) runs inside the hold; its cost is retained (historical ~0.1ms estimate, not separately measured). Peer require_active contends on the same engine+catalog RLocks: channel_service.py:105-110 boundary, :149-151 require_active; channel_lifecycle.py:182 checks active under catalog lock.

Authority raw A includes measured guard_copy plus actual MCP encode/size; comparator subtracts guard_copy only, raw retained. Prospective C is outside A1 scope, cold validation, not future D4 C. Both tools use fresh fixture per sample, fixed order, no warm-up discard/overlap/selective rerun; every phase/error row is written incrementally. Numeric0.270 comparisons only; no acceptance fields or0.216 gate on unchanged source. No imports in facade DESIGN mode. Benchmark output in the earlier fixture-module check is separate, not a checkpoint.

## Planned execution

Same frozen pin, main .venv-windows interpreter and PYTHONPATH=., CWD new R2-on-A1 worktree. Sequentially run authority --samples10 and facade --design-checkpoint --samples10. No suites during timing.90 authority samples and40 facade phase samples expected if no error; all errors/not-run/retries retained. Old R2 gate heavy median0.2286/max0.3867, structural max0.2705 and isolated A1 combined median0.1711/max0.1832 stay attributed to their old pins. Compare medians/maxima without acceptance relabel. Both raw JSON receipts will be embedded here and mirrored as an artifact.

## Frozen tool hashes

- `tools/profile_artifact_authority_phases.py` SHA256 `f930adfdfe3fcb5174af7785157c229f1618dd1b38bca146e9e5e5f945c1c329`.
- `tools/measure_artifact_diagnostics.py` SHA256 `bbdebd70a986139579c058993081362ec425f1bcc41f8a1e56d940d794ed148f`.
- `tools/test_artifact_checkpoint_controls.py` SHA256 `2b2969f9cfe58b6fa1f3ca7475cf3da4197a77b8e78d6a742f60b290649611f0`.
