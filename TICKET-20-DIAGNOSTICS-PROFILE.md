# Ticket 20 R2: failed production gate and design phase profile

Status: HISTORICAL DESIGN PROFILE, not R2 acceptance. Latest D1/D2 fresh full-gate result is a retained MISS; see [all 50 samples](TICKET-20-DIAGNOSTICS-D1-D2-GATE.md) and the proposed [D4 contract](TICKET-20-DIAGNOSTIC-PHASES.md). The original measurements below remain unchanged. Original status: DESIGN REVIEW, not R2 acceptance. Product candidate a931275010d7f76154f6478fdc3d386671c803a6 is unchanged. Capability remains empty; no push. Root ran these measurements, the reviewer has not independently reproduced them. Existing40 tests pass4.892s, while N1-N10/additional mutation coverage, old fixture moves, R1/affected/full and structural/import timing remain outstanding.

## Original gate result, retained without rerun substitution

The uninstrumented production gate ran10 reachable heavy +10 summary samples with real fsync, frozen source/tool and no overlapping root suite. Heavy samples2 and7 MISSED0.270s with zero counted replace retries and no exceptions. Maximum heavy hold0.359340200s, peer0.359698900s (margin -0.089698900s). Heavy median0.255782600s. All ten summary-only observed paths passed (max hold0.097756100s, peer0.098154500s); this does not offset the heavy misses. Summary branch does not put/scan body objects, as with the existing summary branch; full structural-read/import gates were not run. The measurement shell909d0781 exited1. No fault exclusion, cap/timeout change, cherry-picked rerun or near-pass acceptance.

|Sample|Path|Hold ms|Peer wait ms|Replace retries|Observed result|
|---|---|---|---|---|---|
|1|heavy|252.171|252.195|0|PASS observed path|
|1|summary|97.756|98.155|0|PASS observed path|
|2|heavy|359.340|359.699|0|MISS|
|2|summary|82.513|83.046|0|PASS observed path|
|3|heavy|265.552|265.308|0|PASS observed path|
|3|summary|67.128|67.683|0|PASS observed path|
|4|heavy|253.496|253.695|0|PASS observed path|
|4|summary|64.993|65.350|0|PASS observed path|
|5|heavy|258.069|258.236|0|PASS observed path|
|5|summary|65.197|65.678|0|PASS observed path|
|6|heavy|249.862|249.837|0|PASS observed path|
|6|summary|66.197|66.542|0|PASS observed path|
|7|heavy|286.323|286.556|0|MISS|
|7|summary|68.054|68.504|0|PASS observed path|
|8|heavy|267.465|267.584|0|PASS observed path|
|8|summary|64.645|65.008|0|PASS observed path|
|9|heavy|253.351|253.335|0|PASS observed path|
|9|summary|65.393|65.760|0|PASS observed path|
|10|heavy|244.042|244.340|0|PASS observed path|
|10|summary|65.585|66.011|0|PASS observed path|

## Profile method and its limits

Reviewer requested a design PROFILE before optimization. tools/profile_artifact_diagnostics.py wraps the existing measurement fixture and call, with NO product edits, skipped writes, replaced fsync or changed locks. Ten new heavy samples used the same128 real reserved source groups,1023 matching prior body files/7.5MiB, then a512KiB body to reach1024 files/8MiB. Inventory INSIDE the heavy hold scans1023 files BEFORE the final put; the post-measure check sees1024. Actual resulting diagnostic metadata668755B.

Wrappers time facade snapshot, each full validation and encoded-size call, full safe-path inventory, body put, and actual metadata atomic_json. Stream proxies forward writes/flushes; wrappers forward os.fsync and Path.replace unchanged. Each sample confirms2 facade snapshots,1 inventory,1 pre-validation/size pair,1 body put,1 persist-validation/size pair,1 atomic_json, and1 body+metadata fsync/replace each. Metadata dump emits61457 stream writes in this fixture.

Timing is WALL TIME, not per-thread CPU accounting. JSON generation minus stream writes retains Python wrapper overhead and scheduling effects; it is not proof of pure CPU time. Instrumentation overhead is NOT subtracted or used to claim a gate pass. Inclusive parents overlap their children; the exclusive top-level partition is facade +pre validation/size +inventory +body-put inclusive +persist validation/size +atomic_json inclusive +other. The profile exit0 means successful data collection, not timing acceptance. All owned roots were cleaned. No unrelated4MiB/structural gates or application suites were run during profiling.

The original two misses had NO per-phase instrumentation. Their cause cannot be reconstructed from these fresh samples. The raw original20 observations are embedded below alongside the new profile, rather than relabeled with invented phase times.

## Per-phase findings

Instrumented heavy median0.292081450s, maximum0.302141400s. These are DESIGN observations, not a replacement uninstrumented gate. Inventory is the largest single phase (median133.735ms). Full validation twice totals about77ms; the combined metadata-validation/encoding/dump work is comparable to inventory, rather than fsync dominating the steady cost. The second validation+size pair is roughly43ms per sample. Body fsync has a real tail: median0.539ms, maximum21.340ms; metadata flush/fsync/replace stays below1.651ms in these ten samples. The slowest profiled sample is not the largest fsync sample: its inventory146.680ms and metadata work both contribute. This does not explain the earlier uninstrumented0.359s event.

|Phase (inclusive/child marked)|Median ms|Maximum ms|
|---|---|---|
|Facade snapshot|0.011|0.015|
|Pre-body full validation|38.292|44.487|
|Pre-body encoded size|3.851|4.605|
|Body inventory|133.735|146.680|
|Body put (inclusive)|2.329|23.229|
|Body fsync (child)|0.539|21.340|
|Persist full validation|38.688|41.645|
|Persist encoded size|4.006|4.563|
|JSON generation + stream writes (child)|53.600|58.009|
|Metadata stream write (child)|13.032|14.145|
|JSON generation minus writes (derived child)|40.619|43.864|
|Metadata flush/fsync/replace (child)|1.106|1.651|
|Metadata atomic_json (inclusive)|55.168|59.663|
|Other hold|7.765|8.843|

|Sample|Hold ms|Peer ms|Facade ms|Pre validate+size ms|Inventory ms|Body put ms|Body fsync child ms|Second validate+size ms|Dump+write child ms|Metadata durable child ms|Other ms|
|---|---|---|---|---|---|---|---|---|---|---|---|
|1|298.520|298.422|0.011|40.884|131.536|22.985|21.162|41.288|52.581|0.995|7.586|
|2|291.599|291.694|0.011|41.832|141.327|2.604|0.617|43.153|53.291|1.103|7.773|
|3|282.496|282.467|0.011|41.734|134.749|2.187|0.499|41.084|53.401|1.109|7.749|
|4|302.141|302.063|0.015|43.217|146.680|2.307|0.646|43.076|56.542|0.995|8.843|
|5|292.809|292.757|0.011|48.211|138.064|2.285|0.549|41.601|53.099|1.172|7.870|
|6|286.104|286.155|0.009|43.555|132.721|2.316|0.502|43.131|54.589|1.651|7.587|
|7|292.564|292.547|0.013|44.990|137.589|2.168|0.478|43.807|54.272|1.179|8.049|
|8|285.751|285.908|0.010|41.696|131.680|2.343|0.529|42.907|58.009|1.116|7.452|
|9|287.291|287.148|0.014|42.377|132.332|2.563|0.529|45.922|53.799|1.000|8.730|
|10|301.148|301.161|0.010|40.841|132.278|23.229|21.340|42.462|53.201|0.933|7.757|

## Recommendation for design review

First consider the bounded invocation-evidence design for redundant validation, with the reviewer-required contract/reds FIRST. It targets repeated validation whose validation+size pair costs roughly43ms in this profile, while retaining once-per-write FULL-graph validation, the same atomic_json/fault seams and all non-evidence validation. Mutation-fingerprint checking may still require encoding work, so43ms is a gross repeated-work budget, NOT a measured saving. This is a diagnostic transaction optimization, not R4/incremental authoring validation. No implementation is authorized by this recommendation; exact evidence identity/mutation/forgery/reuse/fallback rules still need a contract and observed reds.

The strongest objection is the tail: even a uniform43ms saving would leave the old0.359s observation around0.316s. That is a counterfactual, NOT a forecast or retrospective attribution. The profile shows a material avoidable repeated pass, but does NOT establish that removing it yields sufficient max latency or margin. A fresh full uninstrumented gate must prove the changed design, with the original misses retained.

If the reviewer considers that remaining margin risk insufficient for an evidence experiment, or the fresh gate misses, use a separately reviewed service diagnostic phase split. That means actual diagnostic persistence outside the engine/catalog boundary, with authentication capture, rechecks, Stop races and crash-window semantics specified per caller. The harness must then measure actual service capture/settlement holds and real outside-boundary fsync, not merely remove the artificial benchmark boundary while leaving product service calls locked. Reducing detail/body budgets remains a separate Seth scope decision and is not selected. The0.270s gate stays fixed.

Next owner reviewer: assess this profile/recommendation and choose the next technical design review. Root makes no optimization, N/fixture edits or further gate run until that ruling. R3/operator/capacity/activation/push remain held.

## Portable raw receipt

The complete original20 and profiled10 samples follow; only these numbers support the claims above. Local receipt r2-diagnostic-profile-1e80e9de90ae421d80a6fb43b755fa91.json embeds the original failed set r2-diagnostic-measure-ef1a3a5d53d448db9591615c4cf67ffa.json.

```json
{
  "kind": "DESIGN PROFILE ONLY, original uninstrumented gate remains failed",
  "original_measurement": {
    "kind": "R2 reachable heavy/summary measurement, not unit reds",
    "samples": [
      {
        "phase": "heavy",
        "hold": 0.2521714000031352,
        "peer_wait": 0.2521954000694677,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 1
      },
      {
        "phase": "summary",
        "hold": 0.09775610000360757,
        "peer_wait": 0.09815450001042336,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 1
      },
      {
        "phase": "heavy",
        "hold": 0.3593402000842616,
        "peer_wait": 0.35969890002161264,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": false,
        "sample": 2
      },
      {
        "phase": "summary",
        "hold": 0.08251310000196099,
        "peer_wait": 0.08304649998899549,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 2
      },
      {
        "phase": "heavy",
        "hold": 0.2655517999082804,
        "peer_wait": 0.26530799991451204,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 3
      },
      {
        "phase": "summary",
        "hold": 0.0671279999660328,
        "peer_wait": 0.06768330000340939,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 3
      },
      {
        "phase": "heavy",
        "hold": 0.25349629996344447,
        "peer_wait": 0.25369480007793754,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 4
      },
      {
        "phase": "summary",
        "hold": 0.06499260000418872,
        "peer_wait": 0.06535030005034059,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 4
      },
      {
        "phase": "heavy",
        "hold": 0.25806889997329563,
        "peer_wait": 0.2582360999658704,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 5
      },
      {
        "phase": "summary",
        "hold": 0.06519659992773086,
        "peer_wait": 0.06567839998751879,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 5
      },
      {
        "phase": "heavy",
        "hold": 0.2498621999984607,
        "peer_wait": 0.249836599919945,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 6
      },
      {
        "phase": "summary",
        "hold": 0.06619689997751266,
        "peer_wait": 0.06654159992467612,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 6
      },
      {
        "phase": "heavy",
        "hold": 0.28632309997919947,
        "peer_wait": 0.2865557000041008,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": false,
        "sample": 7
      },
      {
        "phase": "summary",
        "hold": 0.06805370002985,
        "peer_wait": 0.06850439996924251,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 7
      },
      {
        "phase": "heavy",
        "hold": 0.2674648000393063,
        "peer_wait": 0.2675840000156313,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 8
      },
      {
        "phase": "summary",
        "hold": 0.06464540003798902,
        "peer_wait": 0.06500810000579804,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 8
      },
      {
        "phase": "heavy",
        "hold": 0.2533505999017507,
        "peer_wait": 0.25333520001731813,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 9
      },
      {
        "phase": "summary",
        "hold": 0.0653926000231877,
        "peer_wait": 0.06576029991265386,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 9
      },
      {
        "phase": "heavy",
        "hold": 0.244042000034824,
        "peer_wait": 0.2443401999771595,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 668755,
        "normal_pass": true,
        "sample": 10
      },
      {
        "phase": "summary",
        "hold": 0.06558490009047091,
        "peer_wait": 0.06601130007766187,
        "replace_retries": 0,
        "exception_type": null,
        "peer_errors": [],
        "body_objects": 1024,
        "body_bytes": 8388608,
        "metadata_bytes": 669173,
        "normal_pass": true,
        "sample": 10
      }
    ],
    "fsync_mocked": false,
    "limit_seconds": 0.27,
    "max_hold": 0.3593402000842616,
    "max_peer_wait": 0.35969890002161264,
    "pass": false,
    "resampling": "None automatic; retain counted-retry faults and every normal miss.",
    "margin": -0.08969890002161263
  },
  "profile_samples": [
    {
      "phase": "heavy",
      "hold": 0.29852019995450974,
      "peer_wait": 0.29842209990601987,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.070008147507906e-05,
        "inventory": 0.13153579994104803,
        "pre_validate": 0.03716559999156743,
        "pre_size": 0.003718600026331842,
        "body_stream_write": 0.0001697000116109848,
        "body_flush": 9.00006853044033e-07,
        "body_fsync": 0.021162399905733764,
        "body_replace": 0.0002701999619603157,
        "body_put_inclusive": 0.022984700044617057,
        "persist_validate": 0.037565300008282065,
        "persist_size": 0.003722399938851595,
        "metadata_stream_write": 0.012581703253090382,
        "metadata_dump_inclusive": 0.05258060002233833,
        "metadata_flush": 1.680001150816679e-05,
        "metadata_fsync": 0.0006338999373838305,
        "metadata_replace": 0.0003440999425947666,
        "atomic_json_inclusive": 0.05423120001796633,
        "persist_inclusive": 0.0960890999995172,
        "metadata_serialize_excluding_stream_write": 0.03999889676924795,
        "metadata_flush_fsync_replace": 0.000994799891486764,
        "other_hold": 0.007585899904370308
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 1
    },
    {
      "phase": "heavy",
      "hold": 0.291598999989219,
      "peer_wait": 0.2916941000148654,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.0999967344105244e-05,
        "inventory": 0.14132719999179244,
        "pre_validate": 0.037987800082191825,
        "pre_size": 0.0038438000483438373,
        "body_stream_write": 0.00018530001398175955,
        "body_flush": 9.00006853044033e-07,
        "body_fsync": 0.0006169000407680869,
        "body_replace": 0.00048500008415430784,
        "body_put_inclusive": 0.002603899920359254,
        "persist_validate": 0.03898269997444004,
        "persist_size": 0.004169899970293045,
        "metadata_stream_write": 0.012713299947790802,
        "metadata_dump_inclusive": 0.05329149996396154,
        "metadata_flush": 1.8600025214254856e-05,
        "metadata_fsync": 0.0005963000003248453,
        "metadata_replace": 0.0004879999905824661,
        "atomic_json_inclusive": 0.05489980010315776,
        "persist_inclusive": 0.09875660005491227,
        "metadata_serialize_excluding_stream_write": 0.04057820001617074,
        "metadata_flush_fsync_replace": 0.0011029000161215663,
        "other_hold": 0.007772899931296706
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 2
    },
    {
      "phase": "heavy",
      "hold": 0.282496300060302,
      "peer_wait": 0.2824668000685051,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.0599964298307896e-05,
        "inventory": 0.134749099961482,
        "pre_validate": 0.03783419996034354,
        "pre_size": 0.0039000000106170774,
        "body_stream_write": 0.0001631999621167779,
        "body_flush": 9.00006853044033e-07,
        "body_fsync": 0.0004988000728189945,
        "body_replace": 0.00025839998852461576,
        "body_put_inclusive": 0.0021871000062674284,
        "persist_validate": 0.03710000007413328,
        "persist_size": 0.003983499947935343,
        "metadata_stream_write": 0.012923099915497005,
        "metadata_dump_inclusive": 0.05340139998588711,
        "metadata_flush": 2.5000073947012424e-05,
        "metadata_fsync": 0.0006321999244391918,
        "metadata_replace": 0.00045160006266087294,
        "atomic_json_inclusive": 0.05498280003666878,
        "persist_inclusive": 0.09662730002310127,
        "metadata_serialize_excluding_stream_write": 0.040478300070390105,
        "metadata_flush_fsync_replace": 0.0011088000610470772,
        "other_hold": 0.00774900009855628
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 3
    },
    {
      "phase": "heavy",
      "hold": 0.3021414000540972,
      "peer_wait": 0.3020626000361517,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.4999997802078724e-05,
        "inventory": 0.14667990000452846,
        "pre_validate": 0.039107799995690584,
        "pre_size": 0.004109199973754585,
        "body_stream_write": 0.00015790003817528486,
        "body_flush": 1.00000761449337e-06,
        "body_fsync": 0.000645900028757751,
        "body_replace": 0.0002607000060379505,
        "body_put_inclusive": 0.0023066001012921333,
        "persist_validate": 0.03851300000678748,
        "persist_size": 0.004563499940559268,
        "metadata_stream_write": 0.013808195595629513,
        "metadata_dump_inclusive": 0.056541699916124344,
        "metadata_flush": 3.1400006264448166e-05,
        "metadata_fsync": 0.0005173999816179276,
        "metadata_replace": 0.00044570001773536205,
        "atomic_json_inclusive": 0.05800299998372793,
        "persist_inclusive": 0.10177609999664128,
        "metadata_serialize_excluding_stream_write": 0.04273350432049483,
        "metadata_flush_fsync_replace": 0.0009945000056177378,
        "other_hold": 0.008843400049954653
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 4
    },
    {
      "phase": "heavy",
      "hold": 0.29280860000289977,
      "peer_wait": 0.2927570999599993,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.1199968867003918e-05,
        "inventory": 0.13806409994140267,
        "pre_validate": 0.044487499981187284,
        "pre_size": 0.0037237999495118856,
        "body_stream_write": 0.0001713000237941742,
        "body_flush": 1.300009898841381e-06,
        "body_fsync": 0.0005486999871209264,
        "body_replace": 0.0002584999892860651,
        "body_put_inclusive": 0.002285399939864874,
        "persist_validate": 0.03767620003782213,
        "persist_size": 0.003924399963580072,
        "metadata_stream_write": 0.012778105097822845,
        "metadata_dump_inclusive": 0.053098500007763505,
        "metadata_flush": 1.6300007700920105e-05,
        "metadata_fsync": 0.0005952999927103519,
        "metadata_replace": 0.0005607999628409743,
        "atomic_json_inclusive": 0.05476570001337677,
        "persist_inclusive": 0.09704509994480759,
        "metadata_serialize_excluding_stream_write": 0.04032039490994066,
        "metadata_flush_fsync_replace": 0.0011723999632522464,
        "other_hold": 0.007870300207287073
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 5
    },
    {
      "phase": "heavy",
      "hold": 0.28610430005937815,
      "peer_wait": 0.286155299982056,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 9.499955922365189e-06,
        "inventory": 0.1327208000002429,
        "pre_validate": 0.038950600079260767,
        "pre_size": 0.004604700021445751,
        "body_stream_write": 0.00018370000179857016,
        "body_flush": 1.100008375942707e-06,
        "body_fsync": 0.0005022999830543995,
        "body_replace": 0.0002767000114545226,
        "body_put_inclusive": 0.002315700054168701,
        "persist_validate": 0.038691400084644556,
        "persist_size": 0.004439900047145784,
        "metadata_stream_write": 0.013315100106410682,
        "metadata_dump_inclusive": 0.054588699946179986,
        "metadata_flush": 3.4100026823580265e-05,
        "metadata_fsync": 0.001243000035174191,
        "metadata_replace": 0.00037429993972182274,
        "atomic_json_inclusive": 0.05678430001717061,
        "persist_inclusive": 0.10053749999497086,
        "metadata_serialize_excluding_stream_write": 0.041273599839769304,
        "metadata_flush_fsync_replace": 0.001651400001719594,
        "other_hold": 0.007587399799376726
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 6
    },
    {
      "phase": "heavy",
      "hold": 0.2925639000022784,
      "peer_wait": 0.2925468999892473,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.3399985618889332e-05,
        "inventory": 0.13758920005057007,
        "pre_validate": 0.04093009990174323,
        "pre_size": 0.004060399951413274,
        "body_stream_write": 0.00016140006482601166,
        "body_flush": 1.00000761449337e-06,
        "body_fsync": 0.0004779000300914049,
        "body_replace": 0.0002543999580666423,
        "body_put_inclusive": 0.002167999977245927,
        "persist_validate": 0.03977919998578727,
        "persist_size": 0.004027799936011434,
        "metadata_stream_write": 0.013219904503785074,
        "metadata_dump_inclusive": 0.054271699977107346,
        "metadata_flush": 4.910002462565899e-05,
        "metadata_fsync": 0.0007678000256419182,
        "metadata_replace": 0.0003616999601945281,
        "atomic_json_inclusive": 0.05594700004439801,
        "persist_inclusive": 0.10038439999334514,
        "metadata_serialize_excluding_stream_write": 0.04105179547332227,
        "metadata_flush_fsync_replace": 0.0011786000104621053,
        "other_hold": 0.008048800169490278
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 7
    },
    {
      "phase": "heavy",
      "hold": 0.2857509000459686,
      "peer_wait": 0.28590839996468276,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 9.500072337687016e-06,
        "inventory": 0.13167979998979717,
        "pre_validate": 0.03806499997153878,
        "pre_size": 0.003631100058555603,
        "body_stream_write": 0.00020000000949949026,
        "body_flush": 1.00000761449337e-06,
        "body_fsync": 0.0005286000669002533,
        "body_replace": 0.0003288000589236617,
        "body_put_inclusive": 0.002342900028452277,
        "persist_validate": 0.03949630004353821,
        "persist_size": 0.003411000012420118,
        "metadata_stream_write": 0.014144900720566511,
        "metadata_dump_inclusive": 0.05800930003169924,
        "metadata_flush": 2.3000058718025684e-05,
        "metadata_fsync": 0.0005362000083550811,
        "metadata_replace": 0.0005570999346673489,
        "atomic_json_inclusive": 0.0596628999337554,
        "persist_inclusive": 0.10325500008184463,
        "metadata_serialize_excluding_stream_write": 0.04386439931113273,
        "metadata_flush_fsync_replace": 0.0011163000017404556,
        "other_hold": 0.0074523999355733395
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 8
    },
    {
      "phase": "heavy",
      "hold": 0.2872912000166252,
      "peer_wait": 0.28714810009114444,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.4099990949034691e-05,
        "inventory": 0.132331500062719,
        "pre_validate": 0.03851920005399734,
        "pre_size": 0.003857300034724176,
        "body_stream_write": 0.0001772999530658126,
        "body_flush": 1.100008375942707e-06,
        "body_fsync": 0.0005294999573379755,
        "body_replace": 0.0002604000037536025,
        "body_put_inclusive": 0.002562900073826313,
        "persist_validate": 0.04164489998947829,
        "persist_size": 0.004277199972420931,
        "metadata_stream_write": 0.01314039807766676,
        "metadata_dump_inclusive": 0.053799299988895655,
        "metadata_flush": 2.629996743053198e-05,
        "metadata_fsync": 0.0005537000251933932,
        "metadata_replace": 0.00042019993998110294,
        "atomic_json_inclusive": 0.055353700066916645,
        "persist_inclusive": 0.10207450005691499,
        "metadata_serialize_excluding_stream_write": 0.040658901911228895,
        "metadata_flush_fsync_replace": 0.0010001999326050282,
        "other_hold": 0.008730399771593511
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 9
    },
    {
      "phase": "heavy",
      "hold": 0.3011484000599012,
      "peer_wait": 0.3011608000379056,
      "replace_retries": 0,
      "exception_type": null,
      "peer_errors": [],
      "body_objects": 1024,
      "body_bytes": 8388608,
      "metadata_bytes": 668755,
      "normal_pass": false,
      "seconds": {
        "facade_snapshot": 1.0299962013959885e-05,
        "inventory": 0.13227840000763535,
        "pre_validate": 0.03715589991770685,
        "pre_size": 0.003685200004838407,
        "body_stream_write": 0.00018550001550465822,
        "body_flush": 1.00000761449337e-06,
        "body_fsync": 0.02133960009086877,
        "body_replace": 0.0003831000067293644,
        "body_put_inclusive": 0.02322870003990829,
        "persist_validate": 0.038685500039719045,
        "persist_size": 0.0037764000007882714,
        "metadata_stream_write": 0.0128331029554829,
        "metadata_dump_inclusive": 0.053200599970296025,
        "metadata_flush": 1.9000028260052204e-05,
        "metadata_fsync": 0.0005736000603064895,
        "metadata_replace": 0.00034010002855211496,
        "atomic_json_inclusive": 0.054571100044995546,
        "persist_inclusive": 0.09769490000326186,
        "metadata_serialize_excluding_stream_write": 0.040367497014813125,
        "metadata_flush_fsync_replace": 0.0009327001171186566,
        "other_hold": 0.007756900042295456
      },
      "calls": {
        "facade_snapshot": 2,
        "inventory": 1,
        "pre_validate": 1,
        "pre_size": 1,
        "body_stream_write": 1,
        "body_flush": 1,
        "body_fsync": 1,
        "body_replace": 1,
        "body_put_inclusive": 1,
        "persist_validate": 1,
        "persist_size": 1,
        "metadata_stream_write": 61457,
        "metadata_dump_inclusive": 1,
        "metadata_flush": 1,
        "metadata_fsync": 1,
        "metadata_replace": 1,
        "atomic_json_inclusive": 1,
        "persist_inclusive": 1
      },
      "inside_hold_inventory": [
        {
          "objects": 1023,
          "bytes": 7864320
        }
      ],
      "interpretation": "Inclusive parents overlap children; exclusive top-level phases partition hold. Instrumented design profile, not acceptance.",
      "sample": 10
    }
  ],
  "fsync_mocked": false,
  "product_change": false,
  "median_instrumented_hold": 0.2920814499957487,
  "max_instrumented_hold": 0.3021414000540972,
  "limits": "Instrumentation overhead retained; no retrospective phase attribution for original misses. Serialization-minus-write is wall time, not CPU accounting."
}
```


## D1 behavior-preserving inventory change

Reviewer D1-D4 orders cheap wins before one fresh full gate and requires heavy maximum hold/peer<=0.216s (20 percent margin under0.270); old misses remain. D1 now uses os.scandir/DirEntry.stat in one enumeration, retaining EVERY per-entry _safe full-path guard, matching case behavior, matching .txt directories as before, ignoring temp/lock/nonmatching suffixes, preserving glob enumeration-error suppression and entry-stat errors. No cross-pass cache or new file classification. Differential test passes on old1.111s and new1.039s across absent/empty/orphan/referenced/nonfile/temp/1024/unreadable cases; all41 current R2 tests PASS5.807s. These are equivalence checks, not new gate acceptance.

Inventory-only DESIGN comparison on the same1024objects/8MiB fixture,10 old/new pairs: old median144.402ms/max150.949ms; new median122.058ms/max131.763ms, about22.344ms median reduction. Both perform1025 _safe calls/pass. Guard time remains dominant (old median112.522ms, new114.339ms). No guard was removed to produce a larger saving; result/error/report equivalence is required. No fresh full gate has run. D2 shared writer inspection/byte identity is next; N additions and broader acceptance still pending.

`json
{
  "kind": "D1 inventory-only DESIGN comparison, not a full timing gate",
  "rows": [
    {
      "sample": 1,
      "method": "previous_path_glob_stat",
      "seconds": 0.15094850002788007,
      "safe_seconds": 0.11791449890006334,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 1,
      "method": "scandir_direntry_stat",
      "seconds": 0.13176310004200786,
      "safe_seconds": 0.12406409892719239,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 2,
      "method": "previous_path_glob_stat",
      "seconds": 0.14571549999527633,
      "safe_seconds": 0.11369939940050244,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 2,
      "method": "scandir_direntry_stat",
      "seconds": 0.12897720001637936,
      "safe_seconds": 0.12113959901034832,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 3,
      "method": "previous_path_glob_stat",
      "seconds": 0.14562139997724444,
      "safe_seconds": 0.11354769847821444,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 3,
      "method": "scandir_direntry_stat",
      "seconds": 0.12385839992202818,
      "safe_seconds": 0.1163457992952317,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 4,
      "method": "previous_path_glob_stat",
      "seconds": 0.14797599997837096,
      "safe_seconds": 0.1154109031194821,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 4,
      "method": "scandir_direntry_stat",
      "seconds": 0.12134169996716082,
      "safe_seconds": 0.11376789852511138,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 5,
      "method": "previous_path_glob_stat",
      "seconds": 0.14579340000636876,
      "safe_seconds": 0.11393369862344116,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 5,
      "method": "scandir_direntry_stat",
      "seconds": 0.120457399985753,
      "safe_seconds": 0.11290590313728899,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 6,
      "method": "previous_path_glob_stat",
      "seconds": 0.14274139993358403,
      "safe_seconds": 0.11127290257718414,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 6,
      "method": "scandir_direntry_stat",
      "seconds": 0.12793079996481538,
      "safe_seconds": 0.11997269897256047,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 7,
      "method": "previous_path_glob_stat",
      "seconds": 0.13869440008420497,
      "safe_seconds": 0.10811080154962838,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 7,
      "method": "scandir_direntry_stat",
      "seconds": 0.11795149999670684,
      "safe_seconds": 0.11077270261012018,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 8,
      "method": "previous_path_glob_stat",
      "seconds": 0.14318270003423095,
      "safe_seconds": 0.11149599985219538,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 8,
      "method": "scandir_direntry_stat",
      "seconds": 0.12152540008537471,
      "safe_seconds": 0.11411810165736824,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 9,
      "method": "previous_path_glob_stat",
      "seconds": 0.14266010001301765,
      "safe_seconds": 0.1104098993819207,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 9,
      "method": "scandir_direntry_stat",
      "seconds": 0.11876109999138862,
      "safe_seconds": 0.11108839802909642,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 10,
      "method": "previous_path_glob_stat",
      "seconds": 0.13854910002555698,
      "safe_seconds": 0.10794830089434981,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    },
    {
      "sample": 10,
      "method": "scandir_direntry_stat",
      "seconds": 0.12259109993465245,
      "safe_seconds": 0.11455929966177791,
      "safe_calls": 1025,
      "objects": 1024,
      "bytes": 8388608
    }
  ],
  "summary": {
    "previous_path_glob_stat": {
      "median": 0.1444020500057377,
      "max": 0.15094850002788007,
      "median_safe": 0.11252184916520491
    },
    "scandir_direntry_stat": {
      "median": 0.12205825001001358,
      "max": 0.13176310004200786,
      "median_safe": 0.11433870065957308
    }
  },
  "per_entry_path_guard": "retained,1025 safe checks per pass; no cache across passes"
}
`
