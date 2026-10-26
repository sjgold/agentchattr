# D4 measurement revision after the first production MISS

Status: reviewer authorized harness-only revisions; product bytes remain4968e47. The next run is HELD until the tool/doc freeze is reviewed. Original110 samples, the1.166355s A miss, and the earlier1.103s facade miss remain unchanged and unattributed.

## Ordered work

1. Add a shared independent machine-stall sentinel and interval classification helpers. Use a5ms sleep followed by a tiny real fsync/replace outside every fixture. Retain every cycle gap>100ms with monotonic and UTC intervals, stage durations, errors and thread identity. Start before fixture/sample work and persist events incrementally. Sentinel failures invalidate instrumented clearance.
2. Attribute admit_saved A in a separate DESIGN mode using wrappers around actual validation/context/producer/seal/packet/activation/persist/outbox/capture and low-level encode/write/fsync/replace. Main-thread phase filtering prevents sentinel or peer work contaminating the profile. Inclusive nested spans are reported without summing overlapping durations. No product edits or diagnosis assumed.
3. Fix actual production measurement: mutating peer once during B plus repeated same-boundary users across A/B/C, no peer-start handshake in B; service-level heavy and summary C; direct engine-lock holds for startup; A+C sum and whole-call latency. Record operation/phase/peer intervals for sentinel overlap.
4. Add synthetic controls for sentinel thresholds/overlap/error handling, receipt retention, attribution nesting, peer and incidental-lock coverage. These are orchestration checks, not measurement samples. Product/full tests need no repeat because product bytes are unchanged.
5. Freeze code/docs and send the pin and hashes to the independent reviewer. Do not run attribution or acceptance before review. Following clearance: one DESIGN attribution, then one fresh full production gate in service, facade/read/import, supplemental order, all original rows retained. Any repeat policy is explicit below, never automatic.

## Predeclared reviewer policy

Limits stay0.270s hard,0.216s changed-hold/peer margin and0.300s import, with>=10 fresh samples. A miss stays a miss. Only a miss interval overlapping a sentinel cycle gap>0.5s may be labeled machine-attributed under this policy; overlap is temporal evidence, not proof of a specific OS/AV cause. Old runs without a sentinel cannot be retroactively classified.

Clearance despite such a miss requires a COMPLETE fresh repeat of its affected caller/phase class (>=10 new fixtures), zero misses and zero overlapping sentinel stalls, reported together with the original run. No miss is excluded. A miss without that overlap returns to design. The harness reports eligible classes and never silently retries or turns the original pass field true. Independent review decides clearance.

## Disclosure

This machine has shown occasional ~1.1s timing stalls in two different paths; their cause is unverified. New gates use a stall sentinel. Measured source, tool and fixture hashes, sentinel scratch location, classification evidence and every sample travel in the receipt/artifact. R3/operator/capacity/activation/push remain held.

## Implemented freeze, pending delta review

Tools committed9145860730bdea5125a5e943a6738bf0376432d6; the final docs pin follows. Product bytes match all four SHA256 values in the frozen4968e47 service receipt. Git blobs use LF while these worktree files use CRLF, so verification uses the original measured-file hashes, plus normalized Git equality. No attribution or production measurements have run on this revision. Existing1814/four-skips regression and15 mutation results retain their original attribution.

### Shared instrument and incremental evidence

`tools/artifact_measurement_support.py` implements the independent sentinel, receipt, interval classifier, phase profiler and forwarding RLock observer. The sentinel captures native filesystem primitives before measured-thread wrappers. Its unique scratch directory is outside every fixture, under .audit-tmp. Every cycle uses a5ms sleep plus tiny real write/flush/fsync/replace. Gaps>100ms retain monotonic/UTC nanosecond intervals and sleep/fsync/write/replace/between-cycle durations. It runs from before the first fixture until all samples finish. Errors, zero cycles or a still-running monitor invalidate the tool verdict. The disk probe perturbs the measurement environment; no claim of zero overhead or a specific AV/indexer cause is made.

Receipts are an incremental pair during the run: a progress-header .json and its named .events.jsonl journal. Samples, phase observations, sentinel gaps and sentinel errors append immediately under one writer lock. This avoids repeatedly serializing the growing full history during timing. The final .json embeds every row and event. If interrupted, retain BOTH files and embed the journal in the artifact. Sentinel notifications happen without its state lock, preventing a receipt/sentinel lock cycle. Main phase publication happens after the measured locks release. Whole-call latency includes harness publication overhead and is report-only.

### Attribution and active CLI modes

--design-attribution runs10 fresh max-source admit_saved fixtures with a conflicting saved body and real A/B/C. Main-thread A-only wrappers cover validate_payload, context/producer, seal, packet/content, activation, authoring persistence/index validation, atomic_json/JSON encode, stream write/fsync/replace, outbox reads/verification and capture. Inclusive spans retain depth and endpoints; per-label totals are NOT additive across nesting. Top-level attributed time and A residual (including wrapper overhead) are reported. Sentinel/peer work cannot enter these spans. DESIGN strips pass/hard_pass/margin_pass and carries comparators_only=true and acceptance_claim=false.

--production-gate on the authority tool runs110 samples: nine diagnostic and two healthy classes,10 new fixtures each. The facade tool's production mode runs40 heavy/summary/request/structural observations and20 full/held4MiB imports. --summary-gate on the authority tool adds20 service summary-only C samples,10 CLI and10 API rejection. Each summary fixture fills1024 bodies/8MiB and prerecords exactly one distinct summary key; actual overflow counter2 is checked after C. Source-failure diagnostics with no body still report1023/7.5MiB. No body write is fabricated.

Historical unsentinelled CLI modes now refuse execution, including the old D2-incompatible diagnostic profiler. Their code/functions remain for historical receipts and synthetic orchestration controls. --check-plan remains pure arithmetic. All active measurement CLI modes use the sentinel and incremental receipt.

### Concurrent peer and real boundary holds

A real independent peer continuously uses the same engine/catalog boundary across A/B/C. Once B begins it performs one independent cancellation, source Stop/fence repair, or claimed-request brief activation, rotated across samples, then continues boundary activity. Healthy calls mutate during A. No phase waits for a peer-start or peer-completion handshake. Real interval overlap with B is required for diagnostic writes; missing overlap is an instrument error. Very short read observations likewise cannot clear without a peer interval overlapping the call. Outcomes/errors are retained.

The peer adds a small request to the original129-request fixture, so service samples honestly report130 requests while preserving128 imported priors plus the2MiB/1000-ref candidate and512KiB parent/Markdown. Each facade phase prepares a fresh peer and reports its resulting count. Stop fixture construction uses a NEW packet identity for changed source bytes; its initial tiny packet may remain an orphan and contributes to report scan costs.

Actual acquired A/C holds and acquisition waits are recorded separately. The forwarding observer replaces BOTH engine._lock and CoordinatedQueue's cached alias with the SAME proxy after checking original identity, then restores both. It records outermost engine holds in main/peer threads, including startup's engine-only inventory holds outside a channel boundary, with incidental labels. No nested hold is summed into a fictional continuous hold. A+C sums and whole-call latency are explicit fields. Imported authoring holds/peer waits retain their0.300 limit; replacement PermissionErrors include object paths throughout the import fixture.

Candidate states, warning/result outcomes and summary counts are checked in addition to timing. Functional failures, ownership violations, unexpected errors, retries and missing overlap cannot become repeat-eligible merely through a coincident sentinel gap. Overlap classification adds evidence to each exceeded interval, never changes original pass fields or schedules a repeat. Mixed attributed/unattributed misses are ineligible. Strict>0.5s and strict interval overlap apply. A single tool pass never claims D4 acceptance.

### Verification

13 controls OK1.427s: threshold/overlap policy; independent monitor error lifecycle; incremental journal/final embedding; inclusive nested A-only/thread-only spans; real tiny sentinel fsync/replace/cleanup; real independent cancel/Stop/request builders; forwarding cached engine-lock alias; old CLI rejection; and actual attribution hook signatures with a SYNTHETIC clock and small fixture. These are controls, not gate samples. They exposed and corrected a zero-work fake peer-overlap assumption and a summary-local variable shadowing the operation result before freeze. Product remained unchanged; no full suite was repeated.

## Run order AFTER reviewer clearance

With the main .venv-windows interpreter, PYTHONPATH=. and this worktree as cwd, run sequentially without suites:

```powershell
python tools/profile_artifact_authority_phases.py --design-attribution --samples 10
python tools/profile_artifact_authority_phases.py --production-gate --samples 10
python tools/measure_artifact_diagnostics.py --production-gate --samples 10
python tools/profile_artifact_authority_phases.py --summary-gate --samples 10
```

That is10 DESIGN attribution samples followed by190 fresh production observations. Every original sample is retained. An unattributed miss returns to design. Any complete affected-class repeat under the predeclared sentinel policy must retain both runs and receive reviewer direction; no automatic retry exists. Attribution indicating a code issue requires a new ruling before product changes. Remaining R3/operator/capacity/activation/push stay held.

## Frozen-file hashes

```json
{
  "tools/artifact_measurement_support.py": "f1cddc7b16109e803248ae69ef9e6dcf15fe8cfe6711d5a10e4c9a78c0c362e8",
  "tools/profile_artifact_authority_phases.py": "fcdbe022fb9ebf4765b1203dbfa0f5348326eb157e6f1a94ffaef7b46aa86222",
  "tools/measure_artifact_diagnostics.py": "8e1955ef993380d4cd78dc148a648ea446c858660de85adade4f52e91418d4ab",
  "tools/profile_artifact_diagnostics.py": "2f4f3a47ff9cfbd41fd21aecdd07ed1f10cb7aa3780c1deb9f3ab4e7e34d0ce2",
  "tools/test_artifact_checkpoint_controls.py": "7f5baac4a5a56d44208a4a149c36247e054212dff5b3620776a51a871ab66301",
  "artifact_store.py": "6c92e79837400e79444353d1a10c6679ac6761db07bb8a2f48062fd75a212f1d",
  "artifact_service.py": "2a13f084071e6e12db61fcb6fdbeccfde030d5ffe1bd9add33422b297fd6e6d7",
  "api_seats.py": "a638aa9711b3b25e522654cee68fb91000e1349040cc2bd62fef034ed665c13d",
  "mcp_bridge.py": "265dd38d36be915b8df6040222cac4de878ef9f8d498127cf99c1b0c253141b8"
}
```
