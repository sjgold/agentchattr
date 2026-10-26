# D4 admit_saved tail study, harness only

Status: reviewer authorized the larger two-arm DESIGN study after independent remaining gate classes. Product remains4968e47. Gate misses and fixture failures stay unresolved. No acceptance claim.

1. Complete frozen remaining facade/read/import60 then summary20 first. Done:57 successful measured facade/import observations +3 structural peer-setup TypeErrors; summaries20 successful. All rows retained, no replacement. Report these first to reviewer (sent).
2. Add two fixed-order arms,30 fresh max-source samples each: sentinel_only first (no peers, no lock proxy, no nested spans, no per-phase receipt IO), then nested_design10 (nested spans plus passive peer/lock proxy as DESIGN10). Existing setup and diagnostic seed are identical129-request/2MiB/1000-ref/512KiB fixtures in both arms. No warmup discard or resampling.
3. Minimal observer measures acquired outermost A/C and B/whole-call intervals only. Arm2 reuses the actual reviewed observer. All samples retained. Inclusive nested spans aggregate by name; preserve all top-level intervals and counts/totals/maxima for nested labels rather than publishing thousands of repeated JSON-encoding spans.
4. Record setup fsync count/max/last and every>100ms setup fsync, age at A entry, previous measured B end/latency and sample order. Setup fsync wrappers are removed BEFORE measured code; the sentinel uses its captured native primitives. Arm1 has no measured component wrappers. A previous B latency is never mislabeled a native fsync. Predeclared heavy-setup-fsync threshold is>100ms; if none occurs, that correlation is untestable and reported as such.
5. Report arm distributions (median/p90/p95/max), every A>0.216s plus slowest3 per arm, per-label distributions and each tail's component deltas from arm median. Inclusive nested deltas are not additive. Overlay sentinel intervals using the same monotonic clock; no causal or acceptance inference from overlap alone.
6. Synthetic controls before study, then freeze and execute once with no suites alongside. After data, send it for reviewer decision before any product edit or limit/budget change. R3/operator/capacity/activation/push held.

Arm2 varies the instrumentation bundle (spans/passive peer/proxy) together; it can compare that bundle against minimal observation, not isolate each instrument individually. The real sentinel shares GIL/volume in both arms. All setup order and cache-warm conditions remain disclosed.

## Implemented observer and controls

New tools/profile_artifact_admit_tail.py reuses the unchanged setup/diagnostic fixture and writes an independent DESIGN receipt with the sentinel. Sentinel-only arm installs just outermost acquired-boundary and diagnostic B/C phase timers; it creates no thread/proxy/component wrappers and writes no receipt between A/B/C. Nested arm uses the DESIGN10 observer with passive peers/proxy/spans. Both have identical129-request max-source fixtures; no extra mutating peer is prepared. The sentinel runs across both arms.

Setup native-fsync observations are collected ONLY during fixture construction and removed before measuring. Every setup sync>100ms is retained, together with max/last/count, first-after-new-heavy marker, age at A start and previous measured B interval. Previous B is explicitly not a native fsync observation. The study cannot claim a heavy-fsync ordering correlation if no heavy setup sync occurs.

A distributions use nearest-rank p90/p95. Tails include every A>0.216 and the slowest3 in each arm. Nested phase counts/inclusive totals/maxima and all top-level intervals survive aggregation; deltas against each component's arm median are reported for every tail, with no claim that nested deltas add up. Every sample/error remains. Raw A/C/B/whole-call intervals plus sentinel overlays are preserved, no acceptance booleans or class repeats.

Four synthetic controls pass: minimal observer has no peer/proxy/spans and B owns no authority; setup-fsync observer strict threshold/thread isolation; tail/group summaries; CLI rejects N<30. These are not measurement samples. Product files remain unchanged. No other code or budget/limit edits.

## Execute once

```powershell
$env:PYTHONPATH='.'
& 'C:/Users/SJG/Documents/CodePlayground/agentchattr/.venv-windows/Scripts/python.exe' tools/profile_artifact_admit_tail.py --samples 30
```

Run only after the remaining d43 facade/summary commands have exited; no overlapping suites. Report remaining-leg results first (already sent), then this completed study. No product remedy before reviewer ruling on the data.

## Study-file hashes

```json
{
  "tools/profile_artifact_admit_tail.py": "22fc5ae39f0709cc6b7b404b77fdc52a77d4115883e5474999c549a11a00fea0",
  "tools/test_artifact_admit_tail_controls.py": "077ceab6356367109caa96b407ab86f3efc4a3be25e78408450286d02c310e6d"
}
```
