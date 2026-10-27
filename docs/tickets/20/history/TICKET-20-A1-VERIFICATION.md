# Ticket 20 A1: independent cleared-base verification

Status: A1 CLOSED by reviewer atca47a8bf (producta8862f38), with expiry fix independently confirmed. Reviewed unit74f4697..ca47a8bf recorded locally; no remote publication or activation authorized/performed. Branch codex/ticket-20-a1-isolated is based on CLEARED R1 product74f4697efcc6e66f91f228983a3d6a630ec41fff, which was independently cleared atbd1f3922 with identical product bytes. The original codex/ticket-20-artifacts history stays at67e9e05 WIP checkpoint. R2 diagnostic-v2/D1 inventory/D2 shared atomic_json are EXCLUDED. No D4 phase split, R3, operator or capacity implementation.

Historical full/timing product/tool freeze:8443e1c02868dfbffd0c3074f11b3e70c9dfeccf, reviewed atf769e40. Its first follow-up added only two key/pair tests and receipts. The required expiry correction now changes artifact_store.py ONLY (active flag/cleanup/checks), producta8862f38e0618491e5eb987a75ccbaf30bbab712. The source hashes in the ORIGINAL measurement below belong to8443/f769, not the corrected store. Service/MCP/API-seat/tool bytes remain unchanged. No full or timing rerun was requested for this flag-only correction; new focused/affected/mutation evidence is appended. Do not interpret this as R2 or whole-Ticket20 acceptance.

## Results and attribution

|Check|Result|Scope/limitation|
|---|---|---|
|Fresh cleared baseline, before port|R1 bounds +MCP21PASS2.688s|Executed in the new worktree before source port.|
|Initial isolated focused|A1+MCP+R1 bounds54PASS7.225s|33 A1 methods at that checkpoint; R1 golden unchanged.|
|Affected selection|416PASS224.438870s, no skips|58 modules: artifact*, runtime*, MCP proxy, archive, API-seat users; real import benchmark included. Builder-run, not full discovery.|
|Full discovery ONCE|1714PASS325.416213s, four skips|Builder-run on8443e1c product and33 A1 tests. No overlapping suite. This precedes two final test-only strengthening cases; no product/tool change or full rerun after them.|
|Final focused after test-only additions|56PASS6.963s, no skips|35 A1 +3MCP+18R1 bounds. Includes all extra key/pair checks and earlier unobserved-red bodies.|
|Mutation proofs|20/20 killed|In-memory only, source files unchanged; individual tests/failure sites below. Not production executions.|
|Corrected A design measurement|90/90 meet0.216s target and0.270s hard cap|Ten fresh samples per9 caller classes; real persistence. No concurrent peer/B measurement and NO D4 acceptance. C is prospective guard/effect probe only.|
|Import timing within affected/full|0.201570000s /0.193808200s maxima|Separate ten-sample real4MiB benchmarks; limit0.300s, fsync not mocked. Import is not claimed faster due to A1.|

Tracked commands: affected shell a1c3519c-4068-402e-bf3d-15111c982f59; full9f5d129c-1ee7-4926-85e9-b736e32f2eac; corrected design61f59199-243e-4509-95e7-d5f50afdb2f0. All exited0, with success interpreted at their stated scope only. Existing warnings/intentional fault-output retained; no warning-free claim. All test/prototype fixture roots cleaned, including the90 design fixtures; no provider/native runtime acceptance, no installed user-data inspection, no production capability change.

## Corrected measurements

The SAME committed tools/profile_artifact_authority_phases.py uses the actual combined get_brief_context entry and includes json.dumps/UTF8/size checking INSIDE the original outer boundary. Guard-copy time is separately measured but stays in A_seconds; no subtraction is used for pass. Raw packet reads and content walks are counted; sizes/counts/schema are derived from the actual fixture objects/index/result. Fixed caller order, no warm-up discard or favorable resampling. The earlier aff51101/R2-WIP90 rows are retained in the historical design document and are NOT the gate or an apples-to-apples before/after benchmark: that tool omitted MCP encoding and ran a different persistence base.

Every fresh fixture has128 small prior imported requests plus one local maximum-source revision (129 requests), exact2MiB packet/1000refs,512KiB parent/Markdown, authoring schema1. No diagnostic B or peer is measured. Resume/recovered branches retain the explicit full-read-then-fault seam, not a physically corrupt packet. Startup A is still the existing whole recovery pass. C rows are only existing-primitives feasibility probes, not an implemented D4 settlement.

|Caller|N|A median s|A max s|C probe max s|A target misses|A hard misses|
|---|---:|---:|---:|---:|---:|---:|
|brief_context|10|0.171545900|0.179805600|0.016953600|0|0|
|delivery|10|0.134974450|0.168632100|0.017797800|0|0|
|submit_cli|10|0.133772450|0.149383700|0.015826800|0|0|
|admit_saved|10|0.157717450|0.168952600|0.018602400|0|0|
|reject_response|10|0.136997550|0.145914300|0.083758500|0|0|
|resume|10|0.066791450|0.071564400|0.088732200|0|0|
|retained_recovery|10|0.098831700|0.105399900|0.101925000|0|0|
|ack_repair|10|0.054558100|0.060057400|0.019506100|0|0|
|startup_terminal|10|0.031669350|0.034090400|0.026018400|0|0|

Combined parent/brief:3 raw packet reads and1 full content validation in EACH sample. Maximum observed A includes MCP encoding and prospective guard-copy. At maximum0.179805600s it is0.036194400s below the0.216 target; this is observed machine-load margin, not a general wall-clock guarantee. The old~0.24-0.26s design service-work figures are historical/qualified; the current measured combined maximum is below target. R3 remains a separate next contract, and no finite authoring quota is inferred.

## B1-B6 coverage and mutation evidence

|Review item|Implemented evidence|
|---|---|
|B1 store detachment|Direct store packet mutation check in repeat test, independent of MCP JSON decoding; cached packet/scope detachment test too. store_return_alias_without_skipping_reads mutant killed.|
|B2 foreign-thread immutability|Map equality AND entry identity checked after copied-context thread read; foreign_thread_clears_evidence killed.|
|B3 direct validators on SAME warmed bytes|Per-caller _packet_scope spies (not _canonical(portable)); worker/import/archive valid same-byte calls each count1; direct bypass mutants for each killed. Existing corrupt-input guards remain.|
|B4 failed-audit registration|Valid content with current-audit mismatch leaves entries empty; moving registration before audit loop killed.|
|B4 discard miss/hit|Miss returns packet None with correct scope; hit still rejects changed computed-scope/current-audit. Materializing discard packet and skipping audit comparison mutants killed.|
|B4 observations|Real truncate error creates observation, restored successful hit clears it without a content walk; no-clear mutant killed.|
|B4 differential shapes|Empty/max2MiB/1000refs/Unicode/CRLF packets identical with/without reuse; bad message/source-run/scope and all between-read corruption classifications match. Disabled reuse and raw-binding bypass mutants killed.|
|B4 aggregate/different root|At fixed legal per-packet and2-entry bounds, aggregate>2*MAX is structurally unreachable. Test-only lowering MAX after first capture isolates the aggregate registration check, with the next packet below the lowered individual cap; removal mutant killed. No production/timing cap changes. Different-root and second-owner-same-root guards pass; owner/root bypass killed.|
|B4 selected entries/recovery|Actual admit_saved/reject_response/standalone get_brief reuse, fresh scope per startup public item. Disabling service scopes or reusing one across items killed.|
|B4 service damage/parent order|Actual same-size/mtime valid packet edit at first vs second MCP read preserves queued-before-parent-refusal vs FAILED/source_packet_unavailable; raw-equality and reversed-parent-order mutants killed.|
|B5 name mapping|Explicit proposed-to-actual method table in A1 contract; same-size edit asserts encoded byte lengths equal before setting preserved mtime.|
|B6 assumptions|validate_enqueue remains same invocation/thread (prepare counts2 including build); two owners work on one root; vars(owner) stable; symlink case executed without skip; discard parse check normalizes str to bytes before comparison, so non-bytes cannot make it vacuous.|
|Final key/pair strengthening|Same registered entry remapped to another packet id must revalidate; in-place scope/audit-view field replacement cannot retain issuance. Separate packet-id/scope-pair/view-pair mutants killed. These two methods were added after full run, passed in final56; source/tool bytes unchanged.|

No product semantics were altered to accommodate a fixture. R1 authoring schema1/diagnostic behavior and api_seats.atomic_json remain the cleared versions. The mechanical port is traceable in Git; no R2 fixture migration or known-red exception is carried into the independent unit.

## Complete independent measurement receipt

```json
{
  "kind": "A1 on cleared R1 authority-phase DESIGN, no D4 acceptance",
  "samples": [
    {
      "caller": "brief_context",
      "A_seconds": 0.16846189997158945,
      "C_probe_seconds": 0.01573189999908209,
      "A_guard_copy_seconds": 0.00285349995829165,
      "A_mcp_encoding_seconds": 0.006400800077244639,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.17319090000819415,
      "C_probe_seconds": 0.014683000044897199,
      "A_guard_copy_seconds": 0.003826499916613102,
      "A_mcp_encoding_seconds": 0.006825699936598539,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.17234469996765256,
      "C_probe_seconds": 0.016953599988482893,
      "A_guard_copy_seconds": 0.0029872999293729663,
      "A_mcp_encoding_seconds": 0.007173700025305152,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.17131389991845936,
      "C_probe_seconds": 0.01479860011022538,
      "A_guard_copy_seconds": 0.0031032999977469444,
      "A_mcp_encoding_seconds": 0.006867399904876947,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.1701652999036014,
      "C_probe_seconds": 0.015253000077791512,
      "A_guard_copy_seconds": 0.0029005000833421946,
      "A_mcp_encoding_seconds": 0.0073865000158548355,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.17177789995912462,
      "C_probe_seconds": 0.014981699991039932,
      "A_guard_copy_seconds": 0.0035918999928981066,
      "A_mcp_encoding_seconds": 0.006655900040641427,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458390,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.16774479998275638,
      "C_probe_seconds": 0.015261700027622283,
      "A_guard_copy_seconds": 0.0030095999827608466,
      "A_mcp_encoding_seconds": 0.007057500071823597,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.167905000038445,
      "C_probe_seconds": 0.014854799956083298,
      "A_guard_copy_seconds": 0.0031104000518098474,
      "A_mcp_encoding_seconds": 0.006777299917303026,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.1798055999679491,
      "C_probe_seconds": 0.015420599956996739,
      "A_guard_copy_seconds": 0.003374399966560304,
      "A_mcp_encoding_seconds": 0.007459699991159141,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "brief_context",
      "A_seconds": 0.1760092000477016,
      "C_probe_seconds": 0.01623109995853156,
      "A_guard_copy_seconds": 0.0033071000361815095,
      "A_mcp_encoding_seconds": 0.006872300058603287,
      "A_context_response_bytes": 2638593,
      "A_context_within_limit": true,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 2,
      "packet_reads_C": 0,
      "contexts_A": 2,
      "contexts_C": 1,
      "packet_raw_reads_A": 3,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "delivery",
      "A_seconds": 0.156840099953115,
      "C_probe_seconds": 0.016717900056391954,
      "A_guard_copy_seconds": 0.0031108000548556447,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458406,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "delivery",
      "A_seconds": 0.13009549991693348,
      "C_probe_seconds": 0.016582900076173246,
      "A_guard_copy_seconds": 0.0030024999286979437,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458404,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "delivery",
      "A_seconds": 0.12974740006029606,
      "C_probe_seconds": 0.01694029988721013,
      "A_guard_copy_seconds": 0.002946500084362924,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458406,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "delivery",
      "A_seconds": 0.1437302998965606,
      "C_probe_seconds": 0.016175800003111362,
      "A_guard_copy_seconds": 0.0029981000116094947,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458406,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "delivery",
      "A_seconds": 0.13610269990749657,
      "C_probe_seconds": 0.016540899989195168,
      "A_guard_copy_seconds": 0.002899999963119626,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458404,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "delivery",
      "A_seconds": 0.1308010999346152,
      "C_probe_seconds": 0.017361200065352023,
      "A_guard_copy_seconds": 0.002883500070311129,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458406,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "delivery",
      "A_seconds": 0.16863209998700768,
      "C_probe_seconds": 0.017574000055901706,
      "A_guard_copy_seconds": 0.003493799944408238,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458406,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "delivery",
      "A_seconds": 0.134203499997966,
      "C_probe_seconds": 0.017797800013795495,
      "A_guard_copy_seconds": 0.0029155000811442733,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458406,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "delivery",
      "A_seconds": 0.13574539998080581,
      "C_probe_seconds": 0.016448299982585013,
      "A_guard_copy_seconds": 0.0029245999176055193,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458406,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "delivery",
      "A_seconds": 0.1327329999767244,
      "C_probe_seconds": 0.016929300036281347,
      "A_guard_copy_seconds": 0.0032161000417545438,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": null,
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458404,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13285960000939667,
      "C_probe_seconds": 0.014908200013451278,
      "A_guard_copy_seconds": 0.0028658000519499183,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13997849996667355,
      "C_probe_seconds": 0.014498900040052831,
      "A_guard_copy_seconds": 0.0029968000017106533,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458390,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.14938369998708367,
      "C_probe_seconds": 0.014544399920850992,
      "A_guard_copy_seconds": 0.0029436000622808933,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13228340004570782,
      "C_probe_seconds": 0.01475089997984469,
      "A_guard_copy_seconds": 0.003018799936398864,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13589839998167008,
      "C_probe_seconds": 0.014473400078713894,
      "A_guard_copy_seconds": 0.002994599984958768,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13161309994757175,
      "C_probe_seconds": 0.014594600070267916,
      "A_guard_copy_seconds": 0.003005199949257076,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458390,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13130779995117337,
      "C_probe_seconds": 0.014708500006236136,
      "A_guard_copy_seconds": 0.0031766999745741487,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13468530005775392,
      "C_probe_seconds": 0.015311399940401316,
      "A_guard_copy_seconds": 0.0029712000396102667,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458390,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13474640005733818,
      "C_probe_seconds": 0.014645899995230138,
      "A_guard_copy_seconds": 0.002888799994252622,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "submit_cli",
      "A_seconds": 0.13178850000258535,
      "C_probe_seconds": 0.01582680002320558,
      "A_guard_copy_seconds": 0.003243100014515221,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458390,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.15636650007218122,
      "C_probe_seconds": 0.014929399942047894,
      "A_guard_copy_seconds": 0.0036675999872386456,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.159265200025402,
      "C_probe_seconds": 0.013874499942176044,
      "A_guard_copy_seconds": 0.002891200012527406,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.1516972000245005,
      "C_probe_seconds": 0.014733799966052175,
      "A_guard_copy_seconds": 0.002912700059823692,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458390,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.16895260009914637,
      "C_probe_seconds": 0.014202200109139085,
      "A_guard_copy_seconds": 0.0029123000567778945,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.1590684000402689,
      "C_probe_seconds": 0.01455980003811419,
      "A_guard_copy_seconds": 0.0029866000404581428,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458388,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.1563556999899447,
      "C_probe_seconds": 0.014505599974654615,
      "A_guard_copy_seconds": 0.0029134999494999647,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.15522459999192506,
      "C_probe_seconds": 0.018602399970404804,
      "A_guard_copy_seconds": 0.004113900009542704,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.16480170004069805,
      "C_probe_seconds": 0.014533099951222539,
      "A_guard_copy_seconds": 0.0029814000008627772,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.1669341999804601,
      "C_probe_seconds": 0.014683399931527674,
      "A_guard_copy_seconds": 0.0029371000127866864,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458390,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "admit_saved",
      "A_seconds": 0.1536191999912262,
      "C_probe_seconds": 0.014712299918755889,
      "A_guard_copy_seconds": 0.0029371000127866864,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458392,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.1354347999440506,
      "C_probe_seconds": 0.08149860007688403,
      "A_guard_copy_seconds": 0.0030699000926688313,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.13744469999801368,
      "C_probe_seconds": 0.08375850005540997,
      "A_guard_copy_seconds": 0.003164099995046854,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.12994039990007877,
      "C_probe_seconds": 0.07707940007094294,
      "A_guard_copy_seconds": 0.0029229000210762024,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.12807609990704805,
      "C_probe_seconds": 0.07951630000025034,
      "A_guard_copy_seconds": 0.0029831998981535435,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.13655040005687624,
      "C_probe_seconds": 0.08022609993349761,
      "A_guard_copy_seconds": 0.0030061000725254416,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.14591429999563843,
      "C_probe_seconds": 0.07608559995424002,
      "A_guard_copy_seconds": 0.0028522000648081303,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.14322229998651892,
      "C_probe_seconds": 0.07661859993822873,
      "A_guard_copy_seconds": 0.0029572000494226813,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.144974899943918,
      "C_probe_seconds": 0.07888859999366105,
      "A_guard_copy_seconds": 0.002962699974887073,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458395,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.13843679998535663,
      "C_probe_seconds": 0.07687520002946258,
      "A_guard_copy_seconds": 0.002943199942819774,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458393,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "reject_response",
      "A_seconds": 0.13010980002582073,
      "C_probe_seconds": 0.07677879999391735,
      "A_guard_copy_seconds": 0.003540799953043461,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 1,
      "contexts_C": 1,
      "packet_raw_reads_A": 2,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458393,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "resume",
      "A_seconds": 0.06656430009752512,
      "C_probe_seconds": 0.07436779991257936,
      "A_guard_copy_seconds": 0.0029657999984920025,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "resume",
      "A_seconds": 0.06673389999195933,
      "C_probe_seconds": 0.08740640000905842,
      "A_guard_copy_seconds": 0.003488800022751093,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "resume",
      "A_seconds": 0.06717910000588745,
      "C_probe_seconds": 0.07766820001415908,
      "A_guard_copy_seconds": 0.002920400002039969,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458383,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "resume",
      "A_seconds": 0.06684899993706495,
      "C_probe_seconds": 0.08873219997622073,
      "A_guard_copy_seconds": 0.0033628999954089522,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458383,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "resume",
      "A_seconds": 0.07068899995647371,
      "C_probe_seconds": 0.08260590001009405,
      "A_guard_copy_seconds": 0.003001200035214424,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "resume",
      "A_seconds": 0.07156439998652786,
      "C_probe_seconds": 0.0876736999489367,
      "A_guard_copy_seconds": 0.003024199977517128,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458383,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "resume",
      "A_seconds": 0.06781540007796139,
      "C_probe_seconds": 0.08161799993831664,
      "A_guard_copy_seconds": 0.0033870000625029206,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "resume",
      "A_seconds": 0.0653350999346003,
      "C_probe_seconds": 0.0856212000362575,
      "A_guard_copy_seconds": 0.0028894999995827675,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "resume",
      "A_seconds": 0.06510589993558824,
      "C_probe_seconds": 0.0794168000575155,
      "A_guard_copy_seconds": 0.0033897999674081802,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458383,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "resume",
      "A_seconds": 0.06617310002911836,
      "C_probe_seconds": 0.08280770003329962,
      "A_guard_copy_seconds": 0.0029067000141367316,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 1,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458383,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.09914489998482168,
      "C_probe_seconds": 0.0936223000753671,
      "A_guard_copy_seconds": 0.0033362999092787504,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.1011618000920862,
      "C_probe_seconds": 0.10166059993207455,
      "A_guard_copy_seconds": 0.003105200012214482,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.10090740001760423,
      "C_probe_seconds": 0.09484289993997663,
      "A_guard_copy_seconds": 0.003069699974730611,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.09716080001089722,
      "C_probe_seconds": 0.09828639996703714,
      "A_guard_copy_seconds": 0.0030168999219313264,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.09841169998981059,
      "C_probe_seconds": 0.09651169995777309,
      "A_guard_copy_seconds": 0.0030948999337852,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.0975146999116987,
      "C_probe_seconds": 0.08911190007347614,
      "A_guard_copy_seconds": 0.002983099897392094,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.09605359996203333,
      "C_probe_seconds": 0.09097860008478165,
      "A_guard_copy_seconds": 0.0031864000484347343,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.10069099999964237,
      "C_probe_seconds": 0.10192499996628612,
      "A_guard_copy_seconds": 0.0031510000117123127,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.10539989999961108,
      "C_probe_seconds": 0.0979645000770688,
      "A_guard_copy_seconds": 0.003303100005723536,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "retained_recovery",
      "A_seconds": 0.09851849998813123,
      "C_probe_seconds": 0.09523999993689358,
      "A_guard_copy_seconds": 0.002965299994684756,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 1,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 1,
      "packet_raw_reads_C": 0,
      "content_validations_A": 1,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458385,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.05668909999076277,
      "C_probe_seconds": 0.01888470002450049,
      "A_guard_copy_seconds": 0.00312180002219975,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570614,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.05258180003147572,
      "C_probe_seconds": 0.018347900011576712,
      "A_guard_copy_seconds": 0.002938200021162629,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570617,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.06005740002728999,
      "C_probe_seconds": 0.019099800032563508,
      "A_guard_copy_seconds": 0.003023599972948432,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570614,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.05302370002027601,
      "C_probe_seconds": 0.01944890001323074,
      "A_guard_copy_seconds": 0.003130099968984723,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570617,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.05505820002872497,
      "C_probe_seconds": 0.019506099983118474,
      "A_guard_copy_seconds": 0.0032899000216275454,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570617,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.053126799990423024,
      "C_probe_seconds": 0.018009499995969236,
      "A_guard_copy_seconds": 0.0030393999768421054,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570611,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.05651439994107932,
      "C_probe_seconds": 0.01864490006119013,
      "A_guard_copy_seconds": 0.0032646999461576343,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570617,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.053862900007516146,
      "C_probe_seconds": 0.018171099945902824,
      "A_guard_copy_seconds": 0.0033399000531062484,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570617,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.054061500006355345,
      "C_probe_seconds": 0.01824740006122738,
      "A_guard_copy_seconds": 0.003204299951903522,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570617,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "ack_repair",
      "A_seconds": 0.05505470000207424,
      "C_probe_seconds": 0.018965900060720742,
      "A_guard_copy_seconds": 0.0030091999797150493,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 570611,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.031139999977312982,
      "C_probe_seconds": 0.022519499994814396,
      "A_guard_copy_seconds": 0.0028016999131068587,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458377,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 1
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.03380460001062602,
      "C_probe_seconds": 0.023295699968002737,
      "A_guard_copy_seconds": 0.0028762000147253275,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 2
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.031727799912914634,
      "C_probe_seconds": 0.022704900009557605,
      "A_guard_copy_seconds": 0.002818999928422272,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 3
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.03176580008585006,
      "C_probe_seconds": 0.023404399980790913,
      "A_guard_copy_seconds": 0.0028635000344365835,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 4
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.0328148000407964,
      "C_probe_seconds": 0.022408799966797233,
      "A_guard_copy_seconds": 0.0032311000395566225,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 5
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.03120699990540743,
      "C_probe_seconds": 0.022866500075906515,
      "A_guard_copy_seconds": 0.003310499945655465,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 6
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.03409039997495711,
      "C_probe_seconds": 0.026018400094471872,
      "A_guard_copy_seconds": 0.004402200109325349,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 7
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.031246100086718798,
      "C_probe_seconds": 0.022986099938862026,
      "A_guard_copy_seconds": 0.002811599988490343,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458379,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 8
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.031610900070518255,
      "C_probe_seconds": 0.0233557999599725,
      "A_guard_copy_seconds": 0.0030071999644860625,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458379,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 9
    },
    {
      "caller": "startup_terminal",
      "A_seconds": 0.03005160007160157,
      "C_probe_seconds": 0.02333529992029071,
      "A_guard_copy_seconds": 0.0029632000951096416,
      "A_mcp_encoding_seconds": 0.0,
      "A_context_response_bytes": null,
      "A_context_within_limit": null,
      "A_margin_pass": true,
      "C_probe_margin_pass": true,
      "A_hard_pass": true,
      "C_probe_hard_pass": true,
      "A_exit": "DiagnosticStop (expected harness seam)",
      "packet_reads_A": 0,
      "packet_reads_C": 0,
      "contexts_A": 0,
      "contexts_C": 0,
      "packet_raw_reads_A": 0,
      "packet_raw_reads_C": 0,
      "content_validations_A": 0,
      "content_validations_C": 0,
      "authoring_requests": 129,
      "small_prior_requests": 128,
      "packet_bytes": 2097152,
      "message_refs": 1000,
      "parent_bytes": 524288,
      "markdown_bytes": 524288,
      "authoring_schema": 1,
      "authoring_index_bytes": 458381,
      "limitations": "A1 cleared-R1-base DESIGN measurement. A includes actual MCP encoding/size and separately measured guard work; no subtraction for pass. No B/peer gate. C is prospective primitives only, not D4. Fixed caller order, no warmup discard; all sizes derived.",
      "sample": 10
    }
  ],
  "error": null,
  "fsync_mocked": false,
  "harness_edits_product": false,
  "product_pin": "8443e1c02868dfbffd0c3074f11b3e70c9dfeccf",
  "source_sha256": {
    "artifact_store.py": "c5da0dca199d46fcbfad45ce3e6fb0d5055ce1f411aea15ed81c700c0ba149c2",
    "artifact_service.py": "ad9ac57c8928454114bc98631666d6111b59a95f8e0957f045a3fce92e2d92dc",
    "mcp_bridge.py": "b2009a4b24cf8fbdb63c1c140be20162dd17f25e0f87872877f45a0653199ab2",
    "api_seats.py": "c6d3aa257b1bc6199397863f02ccd321982e419f3baf8ff49dd79725cc2a12c4"
  },
  "peer_measured": false,
  "margin_seconds": 0.216,
  "hard_seconds": 0.27,
  "base_product": "74f4697efcc6e66f91f228983a3d6a630ec41fff",
  "authoring_schema": 1,
  "r2_d1_d2_present": false
}
```

## Independent affected/full receipts

```json
{
  "affected": {
    "kind": "A1 isolated affected selection, builder-run NOT full discovery",
    "modules": [
      "tests.test_api_seat_runtime",
      "tests.test_api_seats",
      "tests.test_archive_feature",
      "tests.test_artifact_admission",
      "tests.test_artifact_api_wiring",
      "tests.test_artifact_archive",
      "tests.test_artifact_archive_codec",
      "tests.test_artifact_archive_codec_review",
      "tests.test_artifact_archive_discrimination",
      "tests.test_artifact_archive_driver",
      "tests.test_artifact_archive_driver_review",
      "tests.test_artifact_authority_review",
      "tests.test_artifact_capability",
      "tests.test_artifact_capability_pending",
      "tests.test_artifact_capability_recovery",
      "tests.test_artifact_cli_wiring",
      "tests.test_artifact_coordination",
      "tests.test_artifact_delivery",
      "tests.test_artifact_delivery_settlement",
      "tests.test_artifact_diagnostic_oversize",
      "tests.test_artifact_export_store",
      "tests.test_artifact_factory",
      "tests.test_artifact_import_benchmark",
      "tests.test_artifact_import_plan",
      "tests.test_artifact_import_stage_review",
      "tests.test_artifact_imported_store",
      "tests.test_artifact_inspect",
      "tests.test_artifact_lifecycle",
      "tests.test_artifact_lifecycle_edges",
      "tests.test_artifact_lifecycle_metadata",
      "tests.test_artifact_lifecycle_review",
      "tests.test_artifact_mcp",
      "tests.test_artifact_packet_reuse",
      "tests.test_artifact_parent",
      "tests.test_artifact_protocol",
      "tests.test_artifact_queue",
      "tests.test_artifact_record_bounds",
      "tests.test_artifact_recovery",
      "tests.test_artifact_service_paths",
      "tests.test_artifact_staging_receipt",
      "tests.test_artifact_store",
      "tests.test_artifact_store_integrity",
      "tests.test_artifact_store_review",
      "tests.test_artifact_store_saturation",
      "tests.test_artifact_transport",
      "tests.test_artifact_worker_http",
      "tests.test_artifact_worker_transport",
      "tests.test_artifact_workers",
      "tests.test_artifact_wrapper_entries",
      "tests.test_artifact_wrapper_review",
      "tests.test_mcp_proxy",
      "tests.test_runtime_adoption",
      "tests.test_runtime_heartbeat",
      "tests.test_runtime_history",
      "tests.test_runtime_ownership",
      "tests.test_runtime_protocol_manifest",
      "tests.test_runtime_protocol_upgrade",
      "tests.test_runtime_visibility"
    ],
    "tests": 416,
    "failures": 0,
    "errors": 0,
    "skipped": 0,
    "seconds": 224.43886999995448,
    "pass": true
  },
  "full": {
    "kind": "A1 isolated full discovery, BUILDER-RUN",
    "tests": 1714,
    "failures": 0,
    "errors": 0,
    "skipped": 4,
    "seconds": 325.4162127999589,
    "pass": true,
    "base_product": "74f4697",
    "candidate_product": "8443e1c"
  },
  "import_affected": {
    "method": "store/catalog real-files Windows default atomic_json",
    "portable_envelope_bytes": 4194304,
    "existing_lineages": 100,
    "existing_versions": 100,
    "requests": 128,
    "versions": 128,
    "packet_objects": 128,
    "zip_member_count": 262,
    "baseline_seconds": [
      0.0004344999324530363,
      0.000394499977119267,
      0.000403400044888258,
      0.000587899936363101,
      0.00040389993228018284,
      0.0004944000393152237,
      0.0005271999398246408,
      0.00038320000749081373,
      0.00040330004412680864,
      0.00039840000681579113
    ],
    "samples_seconds": [
      0.17722469998989254,
      0.1817528000101447,
      0.1808798999991268,
      0.2010353000368923,
      0.1862527000484988,
      0.18244120001327246,
      0.20157000003382564,
      0.18123900005593896,
      0.18171239993534982,
      0.17914899997413158
    ],
    "maximum_seconds": 0.20157000003382564,
    "limit_seconds": 0.3,
    "includes_metadata_parse": true,
    "includes_whole_index_validation": true,
    "fsync_mocked": false
  },
  "import_full": {
    "method": "store/catalog real-files Windows default atomic_json",
    "portable_envelope_bytes": 4194304,
    "existing_lineages": 100,
    "existing_versions": 100,
    "requests": 128,
    "versions": 128,
    "packet_objects": 128,
    "zip_member_count": 262,
    "baseline_seconds": [
      0.00047580001410096884,
      0.00045299995690584183,
      0.0003971999976783991,
      0.00042070006020367146,
      0.00046150002162903547,
      0.0005014999769628048,
      0.0005258000455796719,
      0.0005474000936374068,
      0.00047200010158121586,
      0.000592100084759295
    ],
    "samples_seconds": [
      0.18269830010831356,
      0.18490260001271963,
      0.17831770004704595,
      0.18769689998589456,
      0.18780440010596067,
      0.1919885000679642,
      0.17807060002814978,
      0.19380819995421916,
      0.19054939993657172,
      0.18180899997241795
    ],
    "maximum_seconds": 0.19380819995421916,
    "limit_seconds": 0.3,
    "includes_metadata_parse": true,
    "includes_whole_index_validation": true,
    "fsync_mocked": false
  }
}
```

## In-memory mutation receipt

```json
{
  "kind": "A1 in-memory mutations, source untouched",
  "results": [
    {
      "mutant": "store_return_alias_without_skipping_reads",
      "tests": [
        "test_repeat_public_invocations_are_fresh_and_results_detached",
        "test_hit_has_no_new_content_work_and_returns_fresh_packet_and_scope"
      ],
      "run": 2,
      "failures": 2,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_repeat_public_invocations_are_fresh_and_results_detached (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_repeat_public_invocations_are_fresh_and_results_detached)",
          "tail": [
            "                 'uid': 'source-zero'}],",
            "   'scope_kind': 'selected_channel_messages',",
            "   'source_run': None,",
            "   'version': 1}"
          ]
        },
        {
          "test": "test_hit_has_no_new_content_work_and_returns_fresh_packet_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_hit_has_no_new_content_work_and_returns_fresh_packet_and_scope)",
          "tail": [
            "                 'uid': 'source-zero'}],",
            "   'scope_kind': 'selected_channel_messages',",
            "   'source_run': None,",
            "   'version': 1}"
          ]
        }
      ]
    },
    {
      "mutant": "foreign_thread_clears_evidence",
      "tests": [
        "test_copied_context_and_second_thread_cannot_consume_or_mutate_evidence"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_copied_context_and_second_thread_cannot_consume_or_mutate_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_and_second_thread_cannot_consume_or_mutate_evidence)",
          "tail": [
            "    self.assertEqual(self.state().entries, before_entries)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: {} != {'3b0fefdab5e15ec6a94062ce6c0c28f9': _Vali[871 chars]l}')}",
            "Diff is 10207 characters long. Set self.maxDiff to None to see it."
          ]
        }
      ]
    },
    {
      "mutant": "worker_direct_scope_bypass",
      "tests": [
        "test_direct_worker_import_archive_validation_does_not_consume_store_evidence"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_direct_worker_import_archive_validation_does_not_consume_store_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_direct_worker_import_archive_validation_does_not_consume_store_evidence)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 548, in test_direct_worker_import_archive_validation_does_not_consume_store_evidence",
            "    self.assertEqual(walked.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 0 != 1"
          ]
        }
      ]
    },
    {
      "mutant": "import_direct_scope_bypass",
      "tests": [
        "test_direct_worker_import_archive_validation_does_not_consume_store_evidence"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_direct_worker_import_archive_validation_does_not_consume_store_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_direct_worker_import_archive_validation_does_not_consume_store_evidence)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 569, in test_direct_worker_import_archive_validation_does_not_consume_store_evidence",
            "    self.assertEqual(import_walked.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 0 != 1"
          ]
        }
      ]
    },
    {
      "mutant": "archive_direct_scope_bypass",
      "tests": [
        "test_direct_worker_import_archive_validation_does_not_consume_store_evidence"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_direct_worker_import_archive_validation_does_not_consume_store_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_direct_worker_import_archive_validation_does_not_consume_store_evidence)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 573, in test_direct_worker_import_archive_validation_does_not_consume_store_evidence",
            "    self.assertEqual(archive_walked.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 0 != 1"
          ]
        }
      ]
    },
    {
      "mutant": "register_before_audit_check",
      "tests": [
        "test_audit_failure_after_valid_content_registers_no_evidence"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_audit_failure_after_valid_content_registers_no_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_audit_failure_after_valid_content_registers_no_evidence)",
          "tail": [
            "    self.assertEqual(self.state().entries, {})",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: {'3aa5df761b235c77869ea8660c8eb688': _Vali[871 chars]l}')} != {}",
            "Diff is 10207 characters long. Set self.maxDiff to None to see it."
          ]
        }
      ]
    },
    {
      "mutant": "skip_current_audit_comparison",
      "tests": [
        "test_need_packet_false_still_compares_channel_and_source_run",
        "test_need_packet_false_miss_and_scope_mismatch_hit",
        "test_current_audit_scope_mismatches_refuse_identically_after_hit"
      ],
      "run": 3,
      "failures": 8,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_need_packet_false_still_compares_channel_and_source_run (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_still_compares_channel_and_source_run) (field='original_channel')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 219, in test_need_packet_false_still_compares_channel_and_source_run",
            "    self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        },
        {
          "test": "test_need_packet_false_still_compares_channel_and_source_run (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_still_compares_channel_and_source_run) (field='source_run')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 219, in test_need_packet_false_still_compares_channel_and_source_run",
            "    self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        },
        {
          "test": "test_need_packet_false_miss_and_scope_mismatch_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_miss_and_scope_mismatch_hit)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 637, in test_need_packet_false_miss_and_scope_mismatch_hit",
            "    self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        },
        {
          "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='uid')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 504, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
            "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        },
        {
          "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='sha256')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 504, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
            "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        },
        {
          "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='id')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 504, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
            "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        },
        {
          "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='input_revision')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 504, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
            "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        },
        {
          "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='ref_count')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 504, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
            "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
          ]
        }
      ]
    },
    {
      "mutant": "do_not_clear_object_observation",
      "tests": [
        "test_successful_hit_clears_real_prior_object_observation"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_successful_hit_clears_real_prior_object_observation (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_successful_hit_clears_real_prior_object_observation)",
          "tail": [
            "- [{'code': 'object_unavailable',",
            "-   'id': '9160014e8e905013be965fd939240913',",
            "-   'kind': 'object_error',",
            "-   'object_kind': 'packet'}]"
          ]
        }
      ]
    },
    {
      "mutant": "remove_aggregate_raw_bound",
      "tests": [
        "test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 725, in test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count",
            "    self.assertEqual(content.call_count, 2)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 1 != 2"
          ]
        }
      ]
    },
    {
      "mutant": "ignore_owner_and_root",
      "tests": [
        "test_different_root_does_not_share_evidence",
        "test_second_owner_same_root_cannot_reuse_first_owner_evidence"
      ],
      "run": 2,
      "failures": 2,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_different_root_does_not_share_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_different_root_does_not_share_evidence)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 738, in test_different_root_does_not_share_evidence",
            "    self.assertEqual(content.call_count, 2)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 1 != 2"
          ]
        },
        {
          "test": "test_second_owner_same_root_cannot_reuse_first_owner_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_second_owner_same_root_cannot_reuse_first_owner_evidence)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 300, in test_second_owner_same_root_cannot_reuse_first_owner_evidence",
            "    self.assertEqual(content.call_count, 2)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 1 != 2"
          ]
        }
      ]
    },
    {
      "mutant": "disable_service_invocation",
      "tests": [
        "test_admit_reject_and_standalone_brief_selected_entries"
      ],
      "run": 1,
      "failures": 3,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_admit_reject_and_standalone_brief_selected_entries (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_admit_reject_and_standalone_brief_selected_entries) (entry='admit')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 759, in test_admit_reject_and_standalone_brief_selected_entries",
            "    self.assertEqual(content.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 2 != 1"
          ]
        },
        {
          "test": "test_admit_reject_and_standalone_brief_selected_entries (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_admit_reject_and_standalone_brief_selected_entries) (entry='reject')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 759, in test_admit_reject_and_standalone_brief_selected_entries",
            "    self.assertEqual(content.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 2 != 1"
          ]
        },
        {
          "test": "test_admit_reject_and_standalone_brief_selected_entries (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_admit_reject_and_standalone_brief_selected_entries) (entry='brief')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 759, in test_admit_reject_and_standalone_brief_selected_entries",
            "    self.assertEqual(content.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 2 != 1"
          ]
        }
      ]
    },
    {
      "mutant": "disable_all_content_reuse",
      "tests": [
        "test_differential_healthy_empty_unicode_crlf_and_max_packets"
      ],
      "run": 1,
      "failures": 3,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_differential_healthy_empty_unicode_crlf_and_max_packets (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_healthy_empty_unicode_crlf_and_max_packets) (shape='empty')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 677, in test_differential_healthy_empty_unicode_crlf_and_max_packets",
            "    self.assertEqual(content.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 2 != 1"
          ]
        },
        {
          "test": "test_differential_healthy_empty_unicode_crlf_and_max_packets (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_healthy_empty_unicode_crlf_and_max_packets) (shape='unicode_crlf')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 677, in test_differential_healthy_empty_unicode_crlf_and_max_packets",
            "    self.assertEqual(content.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 2 != 1"
          ]
        },
        {
          "test": "test_differential_healthy_empty_unicode_crlf_and_max_packets (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_healthy_empty_unicode_crlf_and_max_packets) (shape='max')",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 677, in test_differential_healthy_empty_unicode_crlf_and_max_packets",
            "    self.assertEqual(content.call_count, 1)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 2 != 1"
          ]
        }
      ]
    },
    {
      "mutant": "ignore_exact_raw_equality",
      "tests": [
        "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics",
        "test_between_read_corruption_matches_uncached_errors_and_observations"
      ],
      "run": 2,
      "failures": 1,
      "errors": 1,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_between_read_corruption_matches_uncached_errors_and_observations (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_between_read_corruption_matches_uncached_errors_and_observations) (variant='same_size_mtime')",
          "tail": [
            "'ok'",
            "<class 'artifact_store.ArtifactUnavailable'>",
            "",
            "Diff is 826 characters long. Set self.maxDiff to None to see it."
          ]
        },
        {
          "test": "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_parent_refusal_and_between_read_packet_damage_keep_service_semantics) (damaged_read=2)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 809, in test_parent_refusal_and_between_read_packet_damage_keep_service_semantics",
            "    self.assertEqual(result['code'], 'artifact_storage_unavailable')",
            "                     ~~~~~~^^^^^^^^",
            "KeyError: 'code'"
          ]
        }
      ]
    },
    {
      "mutant": "reuse_one_scope_across_recovery_items",
      "tests": [
        "test_recovery_public_items_have_fresh_invocation_scopes"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_recovery_public_items_have_fresh_invocation_scopes (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_recovery_public_items_have_fresh_invocation_scopes)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 778, in test_recovery_public_items_have_fresh_invocation_scopes",
            "    self.assertEqual(content.call_count, 2)",
            "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: 0 != 2"
          ]
        }
      ]
    },
    {
      "mutant": "ignore_raw_length_and_equality",
      "tests": [
        "test_differential_bad_message_source_run_and_scope"
      ],
      "run": 1,
      "failures": 3,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_differential_bad_message_source_run_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_bad_message_source_run_and_scope) (field='message')",
          "tail": [
            "'ok'",
            "<class 'artifact_store.ArtifactUnavailable'>",
            "",
            "Diff is 1211 characters long. Set self.maxDiff to None to see it."
          ]
        },
        {
          "test": "test_differential_bad_message_source_run_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_bad_message_source_run_and_scope) (field='source_run')",
          "tail": [
            "'ok'",
            "<class 'artifact_store.ArtifactUnavailable'>",
            "",
            "Diff is 1228 characters long. Set self.maxDiff to None to see it."
          ]
        },
        {
          "test": "test_differential_bad_message_source_run_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_bad_message_source_run_and_scope) (field='scope')",
          "tail": [
            "'ok'",
            "<class 'artifact_store.ArtifactUnavailable'>",
            "",
            "Diff is 1197 characters long. Set self.maxDiff to None to see it."
          ]
        }
      ]
    },
    {
      "mutant": "materialize_discard_packet",
      "tests": [
        "test_need_packet_false_miss_and_scope_mismatch_hit",
        "test_need_packet_false_does_not_parse_full_packet_on_a_hit"
      ],
      "run": 2,
      "failures": 2,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_need_packet_false_miss_and_scope_mismatch_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_miss_and_scope_mismatch_hit)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 632, in test_need_packet_false_miss_and_scope_mismatch_hit",
            "    self.assertIsNone(packet)",
            "    ~~~~~~~~~~~~~~~~~^^^^^^^^",
            "AssertionError: {'channel': 'review', 'input': None, 'messages': [{'attachments': [{'name': 'source.py', 'url': '/uploads/source.py'}], 'id': 0, 'provenance': {'literal': 'Exact source only'}, 'sender': 'operator', 'text': 'Exact caf\u00e9 \u65e5\u672c\u8a9e e\u0301\\r\\n@all is source data.', 'timestamp': 10.5, 'type': 'chat', 'uid': 'source-zero'}], 'scope_kind': 'selected_channel_messages', 'source_run': None, 'version': 1} is not None"
          ]
        },
        {
          "test": "test_need_packet_false_does_not_parse_full_packet_on_a_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_does_not_parse_full_packet_on_a_hit)",
          "tail": [
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 232, in parse",
            "    self.assertNotEqual(compared, raw, 'Discard hit parsed the packet instead of audit-view bytes')",
            "    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
            "AssertionError: b'{\"channel\":\"review\",\"input\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"source_document\":null,\"text\":\"Input\"},\"messages\":[{\"attachments\":[{\"name\":\"source.py\",\"url\":\"/uploads/source.py\"}],\"id\":0,\"provenance\":{\"literal\":\"Exact source only\"},\"sender\":\"operator\",\"text\":\"Exact caf\\xc3\\xa9 \\xe6\\x97\\xa5\\xe6\\x9c\\xac\\xe8\\xaa\\x9e e\\xcc\\x81\\\\r\\\\n@all is source data.\",\"timestamp\":10.5,\"type\":\"chat\",\"uid\":\"source-zero\"}],\"scope_kind\":\"selected_channel_messages\",\"source_run\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"run_id\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"session_id\":1,\"state_at_request\":\"active\"},\"version\":1}' == b'{\"channel\":\"review\",\"input\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"source_document\":null,\"text\":\"Input\"},\"messages\":[{\"attachments\":[{\"name\":\"source.py\",\"url\":\"/uploads/source.py\"}],\"id\":0,\"provenance\":{\"literal\":\"Exact source only\"},\"sender\":\"operator\",\"text\":\"Exact caf\\xc3\\xa9 \\xe6\\x97\\xa5\\xe6\\x9c\\xac\\xe8\\xaa\\x9e e\\xcc\\x81\\\\r\\\\n@all is source data.\",\"timestamp\":10.5,\"type\":\"chat\",\"uid\":\"source-zero\"}],\"scope_kind\":\"selected_channel_messages\",\"source_run\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"run_id\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"session_id\":1,\"state_at_request\":\"active\"},\"version\":1}' : Discard hit parsed the packet instead of audit-view bytes"
          ]
        }
      ]
    },
    {
      "mutant": "ignore_packet_id_binding",
      "tests": [
        "test_registered_evidence_cannot_be_mapped_to_a_different_packet_id"
      ],
      "run": 1,
      "failures": 1,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_registered_evidence_cannot_be_mapped_to_a_different_packet_id (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_registered_evidence_cannot_be_mapped_to_a_different_packet_id)",
          "tail": [
            "AssertionError: 'fe8ea3d7342d533f80f86763036ffd28' != '33d45513e9865b40b1176af2dd7828f9'",
            "- fe8ea3d7342d533f80f86763036ffd28",
            "+ 33d45513e9865b40b1176af2dd7828f9",
            ""
          ]
        }
      ]
    },
    {
      "mutant": "ignore_scope_pair_binding",
      "tests": [
        "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance"
      ],
      "run": 1,
      "failures": 0,
      "errors": 1,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance) (field='scope_bytes')",
          "tail": [
            "           ~~~~~~~~~~~~^^^^^^^^^^^",
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\artifact_store.py\", line 640, in _packet",
            "    raise ArtifactUnavailable('Artifact source packet is unavailable.') from None",
            "artifact_store.ArtifactUnavailable: Artifact source packet is unavailable."
          ]
        }
      ]
    },
    {
      "mutant": "ignore_audit_view_pair_binding",
      "tests": [
        "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance"
      ],
      "run": 1,
      "failures": 0,
      "errors": 1,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance) (field='audit_view_bytes')",
          "tail": [
            "           ~~~~~~~~~~~~^^^^^^^^^^^",
            "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\artifact_store.py\", line 640, in _packet",
            "    raise ArtifactUnavailable('Artifact source packet is unavailable.') from None",
            "artifact_store.ArtifactUnavailable: Artifact source packet is unavailable."
          ]
        }
      ]
    },
    {
      "mutant": "reverse_parent_and_brief",
      "tests": [
        "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics"
      ],
      "run": 1,
      "failures": 2,
      "errors": 0,
      "killed": true,
      "failure_sites": [
        {
          "test": "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_parent_refusal_and_between_read_packet_damage_keep_service_semantics) (damaged_read=1)",
          "tail": [
            "AssertionError: 'failed' != 'queued'",
            "- failed",
            "+ queued",
            ""
          ]
        },
        {
          "test": "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_parent_refusal_and_between_read_packet_damage_keep_service_semantics) (damaged_read=2)",
          "tail": [
            "AssertionError: 'queued' != 'failed'",
            "- queued",
            "+ failed",
            ""
          ]
        }
      ]
    }
  ],
  "all_killed": true
}
```


## Required expiry correction after independent review

The reviewer executed56 focused tests OK7.19s, all artifact modules336OK205.5s, five evidence-key mutants (all killed), and the corrected ten-per-class design tool on f769e40. Reviewer combined A median~0.1711/max~0.1832s,3 reads/1 content walk every sample, all A rows<=0.216. Its91 output rows comprise90 samples plus the final receipt line. These are reviewer-reported independent results, not root reruns. The reviewer did not rerun builder full1714 or read every builder raw receipt. Analyst static audit passed soundness/isolation/detachment/site/MCP/error checks.

The one required fix was a retained same-thread copy_context outliving ContextVar reset. Root added test_copied_context_after_exit_is_expired_and_releases_evidence: normal and exceptional exits both observed0 full content walks vs1 expected, one method/two behavioral failures0.047s before product edit. After fixing, invocation.active is setFalse in finally, entries AND issued are cleared, both eligibility and evidence lookup reject inactive states, and stale copied contexts full-validate without re-registering evidence. This is a lifetime/retention contract correction, not a finding that exact-byte validation admitted unsafe content.

Product change is limited to8 added/changed source lines in artifact_store.py. No optional root-key optimization, D4 phase split, R2 diagnostic migration, schema/enum/wire or capability change. Corrected producta8862f3: focused57PASS7.354s; affected58modules/419PASS220.412112s, no skips; in-suite import max0.188553900s, limit0.300, real fsync.24 in-memory mutants killed, including leave-active, retain-entries, retain-issuance and bypass-closed-guard, each discriminated by the new normal/exceptional-exit test. All temp cleanup assertions pass. Tracked affected shell916fc412-0706-4417-9a9b-e40058823b15 exited0, no suite overlap. No full/authority-timing rerun per reviewer instruction; old results keep old product attribution. Independent final fix check and publication authorization remain outstanding.

```json
{
  "product_pin": "a8862f38e0618491e5eb987a75ccbaf30bbab712",
  "base": "74f4697efcc6e66f91f228983a3d6a630ec41fff",
  "red": {
    "tests": 1,
    "failures": 2,
    "errors": 0,
    "seconds": 0.047,
    "conditions": [
      "normal_exit",
      "exceptional_exit"
    ],
    "assertion": "full content validation calls 0 != 1",
    "log_sha256": "7ab2e3c59f2eee15291b1f90ff2305c735807ed896e0db9d8503fe667f2825a1"
  },
  "focused": {
    "tests": 57,
    "failures": 0,
    "errors": 0,
    "skips": 0,
    "seconds": 7.354
  },
  "affected": {
    "kind": "A1 expiry fix affected selection, builder-run NOT full discovery",
    "modules": [
      "tests.test_api_seat_runtime",
      "tests.test_api_seats",
      "tests.test_archive_feature",
      "tests.test_artifact_admission",
      "tests.test_artifact_api_wiring",
      "tests.test_artifact_archive",
      "tests.test_artifact_archive_codec",
      "tests.test_artifact_archive_codec_review",
      "tests.test_artifact_archive_discrimination",
      "tests.test_artifact_archive_driver",
      "tests.test_artifact_archive_driver_review",
      "tests.test_artifact_authority_review",
      "tests.test_artifact_capability",
      "tests.test_artifact_capability_pending",
      "tests.test_artifact_capability_recovery",
      "tests.test_artifact_cli_wiring",
      "tests.test_artifact_coordination",
      "tests.test_artifact_delivery",
      "tests.test_artifact_delivery_settlement",
      "tests.test_artifact_diagnostic_oversize",
      "tests.test_artifact_export_store",
      "tests.test_artifact_factory",
      "tests.test_artifact_import_benchmark",
      "tests.test_artifact_import_plan",
      "tests.test_artifact_import_stage_review",
      "tests.test_artifact_imported_store",
      "tests.test_artifact_inspect",
      "tests.test_artifact_lifecycle",
      "tests.test_artifact_lifecycle_edges",
      "tests.test_artifact_lifecycle_metadata",
      "tests.test_artifact_lifecycle_review",
      "tests.test_artifact_mcp",
      "tests.test_artifact_packet_reuse",
      "tests.test_artifact_parent",
      "tests.test_artifact_protocol",
      "tests.test_artifact_queue",
      "tests.test_artifact_record_bounds",
      "tests.test_artifact_recovery",
      "tests.test_artifact_service_paths",
      "tests.test_artifact_staging_receipt",
      "tests.test_artifact_store",
      "tests.test_artifact_store_integrity",
      "tests.test_artifact_store_review",
      "tests.test_artifact_store_saturation",
      "tests.test_artifact_transport",
      "tests.test_artifact_worker_http",
      "tests.test_artifact_worker_transport",
      "tests.test_artifact_workers",
      "tests.test_artifact_wrapper_entries",
      "tests.test_artifact_wrapper_review",
      "tests.test_mcp_proxy",
      "tests.test_runtime_adoption",
      "tests.test_runtime_heartbeat",
      "tests.test_runtime_history",
      "tests.test_runtime_ownership",
      "tests.test_runtime_protocol_manifest",
      "tests.test_runtime_protocol_upgrade",
      "tests.test_runtime_visibility"
    ],
    "tests": 419,
    "failures": 0,
    "errors": 0,
    "skipped": 0,
    "seconds": 220.41211160004605,
    "pass": true
  },
  "import_benchmark": {
    "method": "store/catalog real-files Windows default atomic_json",
    "portable_envelope_bytes": 4194304,
    "existing_lineages": 100,
    "existing_versions": 100,
    "requests": 128,
    "versions": 128,
    "packet_objects": 128,
    "zip_member_count": 262,
    "baseline_seconds": [
      0.0003992000129073858,
      0.0003888999344781041,
      0.0004988000728189945,
      0.00040040002204477787,
      0.00041930004954338074,
      0.0006157000316306949,
      0.0003757000667974353,
      0.00044029997661709785,
      0.00039489998016506433,
      0.000480900052934885
    ],
    "samples_seconds": [
      0.18365209992043674,
      0.1837198999710381,
      0.18534359999466687,
      0.17832119995728135,
      0.18578810000326484,
      0.18373039993457496,
      0.17829599999822676,
      0.18855389999225736,
      0.18262760003563017,
      0.17987260001245886
    ],
    "maximum_seconds": 0.18855389999225736,
    "limit_seconds": 0.3,
    "includes_metadata_parse": true,
    "includes_whole_index_validation": true,
    "fsync_mocked": false
  },
  "mutations": {
    "kind": "A1 in-memory mutations, source untouched",
    "results": [
      {
        "mutant": "store_return_alias_without_skipping_reads",
        "tests": [
          "test_repeat_public_invocations_are_fresh_and_results_detached",
          "test_hit_has_no_new_content_work_and_returns_fresh_packet_and_scope"
        ],
        "run": 2,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_repeat_public_invocations_are_fresh_and_results_detached (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_repeat_public_invocations_are_fresh_and_results_detached)",
            "tail": [
              "                 'uid': 'source-zero'}],",
              "   'scope_kind': 'selected_channel_messages',",
              "   'source_run': None,",
              "   'version': 1}"
            ]
          },
          {
            "test": "test_hit_has_no_new_content_work_and_returns_fresh_packet_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_hit_has_no_new_content_work_and_returns_fresh_packet_and_scope)",
            "tail": [
              "                 'uid': 'source-zero'}],",
              "   'scope_kind': 'selected_channel_messages',",
              "   'source_run': None,",
              "   'version': 1}"
            ]
          }
        ]
      },
      {
        "mutant": "foreign_thread_clears_evidence",
        "tests": [
          "test_copied_context_and_second_thread_cannot_consume_or_mutate_evidence"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_copied_context_and_second_thread_cannot_consume_or_mutate_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_and_second_thread_cannot_consume_or_mutate_evidence)",
            "tail": [
              "    self.assertEqual(self.state().entries, before_entries)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: {} != {'2feebf6040255ae5b6c8cabc8fbfc765': _Vali[871 chars]l}')}",
              "Diff is 10207 characters long. Set self.maxDiff to None to see it."
            ]
          }
        ]
      },
      {
        "mutant": "worker_direct_scope_bypass",
        "tests": [
          "test_direct_worker_import_archive_validation_does_not_consume_store_evidence"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_direct_worker_import_archive_validation_does_not_consume_store_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_direct_worker_import_archive_validation_does_not_consume_store_evidence)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 573, in test_direct_worker_import_archive_validation_does_not_consume_store_evidence",
              "    self.assertEqual(walked.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 0 != 1"
            ]
          }
        ]
      },
      {
        "mutant": "import_direct_scope_bypass",
        "tests": [
          "test_direct_worker_import_archive_validation_does_not_consume_store_evidence"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_direct_worker_import_archive_validation_does_not_consume_store_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_direct_worker_import_archive_validation_does_not_consume_store_evidence)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 594, in test_direct_worker_import_archive_validation_does_not_consume_store_evidence",
              "    self.assertEqual(import_walked.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 0 != 1"
            ]
          }
        ]
      },
      {
        "mutant": "archive_direct_scope_bypass",
        "tests": [
          "test_direct_worker_import_archive_validation_does_not_consume_store_evidence"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_direct_worker_import_archive_validation_does_not_consume_store_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_direct_worker_import_archive_validation_does_not_consume_store_evidence)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 598, in test_direct_worker_import_archive_validation_does_not_consume_store_evidence",
              "    self.assertEqual(archive_walked.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 0 != 1"
            ]
          }
        ]
      },
      {
        "mutant": "register_before_audit_check",
        "tests": [
          "test_audit_failure_after_valid_content_registers_no_evidence"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_audit_failure_after_valid_content_registers_no_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_audit_failure_after_valid_content_registers_no_evidence)",
            "tail": [
              "    self.assertEqual(self.state().entries, {})",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: {'c8cb0af992b156169f245dcda4bfb9f2': _Vali[871 chars]l}')} != {}",
              "Diff is 10207 characters long. Set self.maxDiff to None to see it."
            ]
          }
        ]
      },
      {
        "mutant": "skip_current_audit_comparison",
        "tests": [
          "test_need_packet_false_still_compares_channel_and_source_run",
          "test_need_packet_false_miss_and_scope_mismatch_hit",
          "test_current_audit_scope_mismatches_refuse_identically_after_hit"
        ],
        "run": 3,
        "failures": 8,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_need_packet_false_still_compares_channel_and_source_run (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_still_compares_channel_and_source_run) (field='original_channel')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 219, in test_need_packet_false_still_compares_channel_and_source_run",
              "    self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          },
          {
            "test": "test_need_packet_false_still_compares_channel_and_source_run (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_still_compares_channel_and_source_run) (field='source_run')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 219, in test_need_packet_false_still_compares_channel_and_source_run",
              "    self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          },
          {
            "test": "test_need_packet_false_miss_and_scope_mismatch_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_miss_and_scope_mismatch_hit)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 662, in test_need_packet_false_miss_and_scope_mismatch_hit",
              "    self.assertEqual(self.outcome(owner, key, need_packet=False)[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          },
          {
            "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='uid')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 529, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
              "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          },
          {
            "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='sha256')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 529, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
              "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          },
          {
            "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='id')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 529, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
              "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          },
          {
            "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='input_revision')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 529, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
              "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          },
          {
            "test": "test_current_audit_scope_mismatches_refuse_identically_after_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_current_audit_scope_mismatches_refuse_identically_after_hit) (field='ref_count')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 529, in test_current_audit_scope_mismatches_refuse_identically_after_hit",
              "    self.assertEqual(baseline[0], storage.ArtifactUnavailable)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 'ok' != <class 'artifact_store.ArtifactUnavailable'>"
            ]
          }
        ]
      },
      {
        "mutant": "do_not_clear_object_observation",
        "tests": [
          "test_successful_hit_clears_real_prior_object_observation"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_successful_hit_clears_real_prior_object_observation (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_successful_hit_clears_real_prior_object_observation)",
            "tail": [
              "- [{'code': 'object_unavailable',",
              "-   'id': 'ca970eed1e78515cb88a7366e7ec7784',",
              "-   'kind': 'object_error',",
              "-   'object_kind': 'packet'}]"
            ]
          }
        ]
      },
      {
        "mutant": "remove_aggregate_raw_bound",
        "tests": [
          "test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 750, in test_aggregate_raw_budget_bypasses_registration_independently_of_entry_count",
              "    self.assertEqual(content.call_count, 2)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 1 != 2"
            ]
          }
        ]
      },
      {
        "mutant": "ignore_owner_and_root",
        "tests": [
          "test_different_root_does_not_share_evidence",
          "test_second_owner_same_root_cannot_reuse_first_owner_evidence"
        ],
        "run": 2,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_different_root_does_not_share_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_different_root_does_not_share_evidence)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 763, in test_different_root_does_not_share_evidence",
              "    self.assertEqual(content.call_count, 2)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 1 != 2"
            ]
          },
          {
            "test": "test_second_owner_same_root_cannot_reuse_first_owner_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_second_owner_same_root_cannot_reuse_first_owner_evidence)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 300, in test_second_owner_same_root_cannot_reuse_first_owner_evidence",
              "    self.assertEqual(content.call_count, 2)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 1 != 2"
            ]
          }
        ]
      },
      {
        "mutant": "disable_service_invocation",
        "tests": [
          "test_admit_reject_and_standalone_brief_selected_entries"
        ],
        "run": 1,
        "failures": 3,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_admit_reject_and_standalone_brief_selected_entries (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_admit_reject_and_standalone_brief_selected_entries) (entry='admit')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 784, in test_admit_reject_and_standalone_brief_selected_entries",
              "    self.assertEqual(content.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 2 != 1"
            ]
          },
          {
            "test": "test_admit_reject_and_standalone_brief_selected_entries (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_admit_reject_and_standalone_brief_selected_entries) (entry='reject')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 784, in test_admit_reject_and_standalone_brief_selected_entries",
              "    self.assertEqual(content.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 2 != 1"
            ]
          },
          {
            "test": "test_admit_reject_and_standalone_brief_selected_entries (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_admit_reject_and_standalone_brief_selected_entries) (entry='brief')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 784, in test_admit_reject_and_standalone_brief_selected_entries",
              "    self.assertEqual(content.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 2 != 1"
            ]
          }
        ]
      },
      {
        "mutant": "disable_all_content_reuse",
        "tests": [
          "test_differential_healthy_empty_unicode_crlf_and_max_packets"
        ],
        "run": 1,
        "failures": 3,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_differential_healthy_empty_unicode_crlf_and_max_packets (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_healthy_empty_unicode_crlf_and_max_packets) (shape='empty')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 702, in test_differential_healthy_empty_unicode_crlf_and_max_packets",
              "    self.assertEqual(content.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 2 != 1"
            ]
          },
          {
            "test": "test_differential_healthy_empty_unicode_crlf_and_max_packets (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_healthy_empty_unicode_crlf_and_max_packets) (shape='unicode_crlf')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 702, in test_differential_healthy_empty_unicode_crlf_and_max_packets",
              "    self.assertEqual(content.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 2 != 1"
            ]
          },
          {
            "test": "test_differential_healthy_empty_unicode_crlf_and_max_packets (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_healthy_empty_unicode_crlf_and_max_packets) (shape='max')",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 702, in test_differential_healthy_empty_unicode_crlf_and_max_packets",
              "    self.assertEqual(content.call_count, 1)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 2 != 1"
            ]
          }
        ]
      },
      {
        "mutant": "ignore_exact_raw_equality",
        "tests": [
          "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics",
          "test_between_read_corruption_matches_uncached_errors_and_observations"
        ],
        "run": 2,
        "failures": 1,
        "errors": 1,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_between_read_corruption_matches_uncached_errors_and_observations (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_between_read_corruption_matches_uncached_errors_and_observations) (variant='same_size_mtime')",
            "tail": [
              "'ok'",
              "<class 'artifact_store.ArtifactUnavailable'>",
              "",
              "Diff is 826 characters long. Set self.maxDiff to None to see it."
            ]
          },
          {
            "test": "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_parent_refusal_and_between_read_packet_damage_keep_service_semantics) (damaged_read=2)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 834, in test_parent_refusal_and_between_read_packet_damage_keep_service_semantics",
              "    self.assertEqual(result['code'], 'artifact_storage_unavailable')",
              "                     ~~~~~~^^^^^^^^",
              "KeyError: 'code'"
            ]
          }
        ]
      },
      {
        "mutant": "reuse_one_scope_across_recovery_items",
        "tests": [
          "test_recovery_public_items_have_fresh_invocation_scopes"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_recovery_public_items_have_fresh_invocation_scopes (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_recovery_public_items_have_fresh_invocation_scopes)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 803, in test_recovery_public_items_have_fresh_invocation_scopes",
              "    self.assertEqual(content.call_count, 2)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: 0 != 2"
            ]
          }
        ]
      },
      {
        "mutant": "ignore_raw_length_and_equality",
        "tests": [
          "test_differential_bad_message_source_run_and_scope"
        ],
        "run": 1,
        "failures": 3,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_differential_bad_message_source_run_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_bad_message_source_run_and_scope) (field='message')",
            "tail": [
              "'ok'",
              "<class 'artifact_store.ArtifactUnavailable'>",
              "",
              "Diff is 1211 characters long. Set self.maxDiff to None to see it."
            ]
          },
          {
            "test": "test_differential_bad_message_source_run_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_bad_message_source_run_and_scope) (field='source_run')",
            "tail": [
              "'ok'",
              "<class 'artifact_store.ArtifactUnavailable'>",
              "",
              "Diff is 1228 characters long. Set self.maxDiff to None to see it."
            ]
          },
          {
            "test": "test_differential_bad_message_source_run_and_scope (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_differential_bad_message_source_run_and_scope) (field='scope')",
            "tail": [
              "'ok'",
              "<class 'artifact_store.ArtifactUnavailable'>",
              "",
              "Diff is 1197 characters long. Set self.maxDiff to None to see it."
            ]
          }
        ]
      },
      {
        "mutant": "materialize_discard_packet",
        "tests": [
          "test_need_packet_false_miss_and_scope_mismatch_hit",
          "test_need_packet_false_does_not_parse_full_packet_on_a_hit"
        ],
        "run": 2,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_need_packet_false_miss_and_scope_mismatch_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_miss_and_scope_mismatch_hit)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 657, in test_need_packet_false_miss_and_scope_mismatch_hit",
              "    self.assertIsNone(packet)",
              "    ~~~~~~~~~~~~~~~~~^^^^^^^^",
              "AssertionError: {'channel': 'review', 'input': None, 'messages': [{'attachments': [{'name': 'source.py', 'url': '/uploads/source.py'}], 'id': 0, 'provenance': {'literal': 'Exact source only'}, 'sender': 'operator', 'text': 'Exact caf\u00e9 \u65e5\u672c\u8a9e e\u0301\\r\\n@all is source data.', 'timestamp': 10.5, 'type': 'chat', 'uid': 'source-zero'}], 'scope_kind': 'selected_channel_messages', 'source_run': None, 'version': 1} is not None"
            ]
          },
          {
            "test": "test_need_packet_false_does_not_parse_full_packet_on_a_hit (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_need_packet_false_does_not_parse_full_packet_on_a_hit)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 232, in parse",
              "    self.assertNotEqual(compared, raw, 'Discard hit parsed the packet instead of audit-view bytes')",
              "    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
              "AssertionError: b'{\"channel\":\"review\",\"input\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"source_document\":null,\"text\":\"Input\"},\"messages\":[{\"attachments\":[{\"name\":\"source.py\",\"url\":\"/uploads/source.py\"}],\"id\":0,\"provenance\":{\"literal\":\"Exact source only\"},\"sender\":\"operator\",\"text\":\"Exact caf\\xc3\\xa9 \\xe6\\x97\\xa5\\xe6\\x9c\\xac\\xe8\\xaa\\x9e e\\xcc\\x81\\\\r\\\\n@all is source data.\",\"timestamp\":10.5,\"type\":\"chat\",\"uid\":\"source-zero\"}],\"scope_kind\":\"selected_channel_messages\",\"source_run\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"run_id\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"session_id\":1,\"state_at_request\":\"active\"},\"version\":1}' == b'{\"channel\":\"review\",\"input\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"source_document\":null,\"text\":\"Input\"},\"messages\":[{\"attachments\":[{\"name\":\"source.py\",\"url\":\"/uploads/source.py\"}],\"id\":0,\"provenance\":{\"literal\":\"Exact source only\"},\"sender\":\"operator\",\"text\":\"Exact caf\\xc3\\xa9 \\xe6\\x97\\xa5\\xe6\\x9c\\xac\\xe8\\xaa\\x9e e\\xcc\\x81\\\\r\\\\n@all is source data.\",\"timestamp\":10.5,\"type\":\"chat\",\"uid\":\"source-zero\"}],\"scope_kind\":\"selected_channel_messages\",\"source_run\":{\"input_revision\":\"36ecb4f8669133ce744c21982ba4abe2ecd7086e1dc2226ccd6f266f3a5005f8\",\"run_id\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"session_id\":1,\"state_at_request\":\"active\"},\"version\":1}' : Discard hit parsed the packet instead of audit-view bytes"
            ]
          }
        ]
      },
      {
        "mutant": "ignore_packet_id_binding",
        "tests": [
          "test_registered_evidence_cannot_be_mapped_to_a_different_packet_id"
        ],
        "run": 1,
        "failures": 1,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_registered_evidence_cannot_be_mapped_to_a_different_packet_id (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_registered_evidence_cannot_be_mapped_to_a_different_packet_id)",
            "tail": [
              "AssertionError: 'eaa87df0470958b79dfb774c1e4672fa' != '503e75b6e7f65a99abf28a716db6acdf'",
              "- eaa87df0470958b79dfb774c1e4672fa",
              "+ 503e75b6e7f65a99abf28a716db6acdf",
              ""
            ]
          }
        ]
      },
      {
        "mutant": "ignore_scope_pair_binding",
        "tests": [
          "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance"
        ],
        "run": 1,
        "failures": 0,
        "errors": 1,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance) (field='scope_bytes')",
            "tail": [
              "           ~~~~~~~~~~~~^^^^^^^^^^^",
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\artifact_store.py\", line 644, in _packet",
              "    raise ArtifactUnavailable('Artifact source packet is unavailable.') from None",
              "artifact_store.ArtifactUnavailable: Artifact source packet is unavailable."
            ]
          }
        ]
      },
      {
        "mutant": "ignore_audit_view_pair_binding",
        "tests": [
          "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance"
        ],
        "run": 1,
        "failures": 0,
        "errors": 1,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_in_place_scope_and_audit_view_forgery_cannot_reuse_issuance) (field='audit_view_bytes')",
            "tail": [
              "           ~~~~~~~~~~~~^^^^^^^^^^^",
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\artifact_store.py\", line 644, in _packet",
              "    raise ArtifactUnavailable('Artifact source packet is unavailable.') from None",
              "artifact_store.ArtifactUnavailable: Artifact source packet is unavailable."
            ]
          }
        ]
      },
      {
        "mutant": "reverse_parent_and_brief",
        "tests": [
          "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics"
        ],
        "run": 1,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_parent_refusal_and_between_read_packet_damage_keep_service_semantics) (damaged_read=1)",
            "tail": [
              "AssertionError: 'failed' != 'queued'",
              "- failed",
              "+ queued",
              ""
            ]
          },
          {
            "test": "test_parent_refusal_and_between_read_packet_damage_keep_service_semantics (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_parent_refusal_and_between_read_packet_damage_keep_service_semantics) (damaged_read=2)",
            "tail": [
              "AssertionError: 'queued' != 'failed'",
              "- queued",
              "+ failed",
              ""
            ]
          }
        ]
      },
      {
        "mutant": "leave_invocation_active",
        "tests": [
          "test_copied_context_after_exit_is_expired_and_releases_evidence"
        ],
        "run": 1,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=False)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 322, in test_copied_context_after_exit_is_expired_and_releases_evidence",
              "    self.assertFalse(state.active)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^",
              "AssertionError: True is not false"
            ]
          },
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=True)",
            "tail": [
              "  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-a1-isolated\\tests\\test_artifact_packet_reuse.py\", line 322, in test_copied_context_after_exit_is_expired_and_releases_evidence",
              "    self.assertFalse(state.active)",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^",
              "AssertionError: True is not false"
            ]
          }
        ]
      },
      {
        "mutant": "retain_expired_entries",
        "tests": [
          "test_copied_context_after_exit_is_expired_and_releases_evidence"
        ],
        "run": 1,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=False)",
            "tail": [
              "    self.assertEqual(state.entries, {})",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^",
              "AssertionError: {'cbbf90b6c2995342b2ec9a83f94f47a9': _Vali[871 chars]l}')} != {}",
              "Diff is 10207 characters long. Set self.maxDiff to None to see it."
            ]
          },
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=True)",
            "tail": [
              "    self.assertEqual(state.entries, {})",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^",
              "AssertionError: {'80e9cf7d795559fbac5faba6378d9e01': _Vali[871 chars]l}')} != {}",
              "Diff is 10207 characters long. Set self.maxDiff to None to see it."
            ]
          }
        ]
      },
      {
        "mutant": "retain_expired_issuance",
        "tests": [
          "test_copied_context_after_exit_is_expired_and_releases_evidence"
        ],
        "run": 1,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=False)",
            "tail": [
              "    self.assertEqual(state.issued, {})",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^",
              "AssertionError: {2223017457968: (_ValidatedPacketBytes(pac[1671 chars]70>)} != {}",
              "Diff is 3569 characters long. Set self.maxDiff to None to see it."
            ]
          },
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=True)",
            "tail": [
              "    self.assertEqual(state.issued, {})",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^",
              "AssertionError: {2223017456848: (_ValidatedPacketBytes(pac[1671 chars]90>)} != {}",
              "Diff is 3569 characters long. Set self.maxDiff to None to see it."
            ]
          }
        ]
      },
      {
        "mutant": "ignore_closed_invocation_guard",
        "tests": [
          "test_copied_context_after_exit_is_expired_and_releases_evidence"
        ],
        "run": 1,
        "failures": 2,
        "errors": 0,
        "killed": true,
        "failure_sites": [
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=False)",
            "tail": [
              "    self.assertEqual(state.entries, {})",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^",
              "AssertionError: {'4acedf13d791592a94838f028b6be22c': _Vali[871 chars]l}')} != {}",
              "Diff is 10207 characters long. Set self.maxDiff to None to see it."
            ]
          },
          {
            "test": "test_copied_context_after_exit_is_expired_and_releases_evidence (tests.test_artifact_packet_reuse.ArtifactPacketReuseTests.test_copied_context_after_exit_is_expired_and_releases_evidence) (exceptional=True)",
            "tail": [
              "    self.assertEqual(state.entries, {})",
              "    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^",
              "AssertionError: {'533840bf3f9657b0a29dadb29f775a6a': _Vali[871 chars]l}')} != {}",
              "Diff is 10207 characters long. Set self.maxDiff to None to see it."
            ]
          }
        ]
      }
    ],
    "all_killed": true
  },
  "full_rerun": false,
  "authority_timing_rerun": false,
  "reason": "reviewer explicitly requested focused+affected once for flag-only expiry correction; prior full/timing remain original-pin evidence",
  "source_sha256": {
    "artifact_store.py": "2d3ea01aacb07dc900da9c937be546a3aebbbedab97a88999eee661fde5ac2c8",
    "artifact_service.py": "ad9ac57c8928454114bc98631666d6111b59a95f8e0957f045a3fce92e2d92dc",
    "mcp_bridge.py": "b2009a4b24cf8fbdb63c1c140be20162dd17f25e0f87872877f45a0653199ab2",
    "api_seats.py": "c6d3aa257b1bc6199397863f02ccd321982e419f3baf8ff49dd79725cc2a12c4"
  }
}
```


## Final independent closure and publication result

Reviewer CLOSED A1 atca47a8bfcc9cbcd95b8cba284489f85797c07ab3, producta8862f38e0618491e5eb987a75ccbaf30bbab712, base74f4697efcc6e66f91f228983a3d6a630ec41fff. Exact reviewed commit range:74f4697..ca47a8bf, on codex/ticket-20-a1-isolated. Reviewer executed57 focused tests OK7.07s from the isolated worktree and killed raw-equality, packet-id and thread-binding mutants; verified active flag/finally/guards. Its earlier static audit stands, no affected/full rerun claimed by reviewer. Prior own affected419 and full1714 remain separately attributed builder evidence.

Publication result: local reviewed unit recorded, no git push or remote publication. Reviewer clearance is technical acceptance; the session has no explicit Seth authorization to push. Capability stays empty and nothing activates. Main codex/ticket-20-artifacts still carries unaccepted R2 WIP source at67e9e05; later commits there only point to this independent unit. Merge R2 on top of A1, never replace the reviewed A1 unit with R2; preserve history and review any semantic conflict. No R2/D4/R3/operator/reader/acceptance/activation work is implied by this closure.
