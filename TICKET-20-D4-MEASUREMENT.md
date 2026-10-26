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
