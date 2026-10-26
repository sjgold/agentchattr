# Ticket 20: R2 on closed A1, merge plan

Status: PLAN/READ-ONLY PREVIEW, no merge or conflict resolution performed. A1 is CLOSED locally. R2 remains unaccepted. The reviewer requested this conflict report before semantic resolution; no D4/R3/operator source or new measurement is started here.

## A1 closure and publication result

The reviewed independent unit is exactly `74f4697..ca47a8bf`, branch `codex/ticket-20-a1-isolated`, product `a8862f38e0618491e5eb987a75ccbaf30bbab712`. Reviewer closure is at `ca47a8bfcc9cbcd95b8cba284489f85797c07ab3`; local closure-only documentation is now `2c34bbfb159a3334ad4ba66eb7a8fbd4175594ca`. The additional closure commit changes no Python bytes.

Publication result: reviewed unit recorded and committed locally. No push/remote publication or activation was authorized or performed. The reviewer supplies technical acceptance, not Seth's explicit push authorization. Production capability stays empty.

The original `codex/ticket-20-artifacts` branch is preserved. Its unaccepted R2 WIP source remains `67e9e05b26fa9b84101bcdd870b83b85cf3bb74e`; later commits there are documentation pointers. No force-push, reset, rebase or history rewrite is proposed.

## Preview and exact conflicts

Root ran `git merge-tree --write-tree --name-only codex/ticket-20-artifacts codex/ticket-20-a1-isolated`. This writes preview objects only, not an index, branch ref or working file. Both worktrees remained clean. Common ancestor is cleared R1 product `74f4697efcc6e66f91f228983a3d6a630ec41fff`. Preview exit1, tree `ea2c2a50dd2700f4e58f0a888a92f4f30b2dd78f`.

|Conflicted file|Reason|Proposed resolution|
|---|---|---|
|artifact_store.py|Both histories added the A1 helper block, while R2 moved filesystem methods into _ArtifactOwnedFiles and split diagnostics. The marked preview contains TWO _PacketValidationInvocation declarations and a displaced R1 ArtifactStore constructor if blindly accepted.|Retain R2's class hierarchy and schema-v2 constructor. Keep exactly ONE byte/AST-equivalent copy of the CLOSED A1 global evidence/expiry implementation before that hierarchy. Never take an entire ours/theirs store file.|
|artifact_store.py, two helper boundaries|Blank-line conflicts around _remember_validated_packet/_packet only.|Use accepted A1 helper formatting; method ASTs already match.|
|tests/test_artifact_packet_reuse.py|Add/add: original branch has an earlier A1 test stage, independent branch has all accepted coverage including expiry.|Use the complete closed A1 test file; keep R2's separate owner/integration files unchanged. R2 fixture migrations remain a separate reviewed test step.|
|tools/profile_artifact_authority_phases.py|Add/add: old R2 design tool versus corrected A1 tool.|Keep the actual combined call/MCP encoding, measured guard, read/walk counters and derived shapes. Make result labels truthful for the new R2-on-A1 branch (schema2/R2+D1+D2 present), rather than copying hard-coded R1-only provenance. Retain all old receipts unmodified. No new run as part of the merge.|
|STATUS.md|Divergent checkpoint histories.|Current status describes merged R2 candidate on accepted A1, never R2 clearance. Preserve A1 closure and old R2 misses as separately attributed history.|
|TICKET-20-PACKET-VALIDATION-REUSE.md|Add/add proposal/red history versus closed independent unit.|Closed A1 contract and verification are authoritative for A1. Retain R2-specific held dependency notes without reviving superseded A1 instructions.|

## Store/serializer boundary check

Root compared function ASTs in the two worktrees, ignoring line numbers. These methods already match exactly: `_read_validated_packet_content`, `_remember_validated_packet`, `_packet`, `get_packet`, `set_attempt_state`, `_commit_new`. No new algorithm, error mapping, state transition or validation shortcut is required to reconcile them.

|Area|Resolution invariant|
|---|---|
|Global packet evidence|Use accepted A1 owner/root/thread/token + exact raw/scope/audit-view issuance, per-read audit checks, entry/byte bounds and active/clearing finally. Remove stale duplicate helper definitions.|
|Authoring _persist / constructor / _validate_index / _row|These differ intentionally because R2 removes diagnostic containers/request debug fields and uses version2/legacy hold. Retain R2's proposed implementation and held status. Do not copy A1's R1/schema1 constructor or persistence over it.|
|Diagnostic owner / filesystem base|Retain R2 candidate's ArtifactDiagnosticStore and _ArtifactOwnedFiles. A1 content validation helpers stay on the authoring ArtifactStore; diagnostic bodies cannot consume packet evidence.|
|set_attempt_state and _commit_new|Retain accepted A1 `_need_packet=False` reads, fresh current-audit comparisons and R2's surrounding index/state persistence. Their function ASTs already match.|
|artifact_service.py / mcp_bridge.py|Byte-identical across current branches; retain the accepted selected-entry scopes and parent-first combined MCP entry. No D4 boundary split is introduced by merge.|
|api_seats.atomic_json|A1 leaves this file at R1. R2 carries D2's previously reviewed byte-identical dumps+single-write candidate; Git reports no conflict here. Retain it ONLY on the new R2 candidate branch, not on the closed A1 unit. Keep its independent shared-writer/differential evidence and unaccepted R2 status.|
|D1 inventory|Retain the R2 candidate's measured scandir change WITH its per-path guards. No new guard shortcut, caching or diagnostic optimization.|

The only proposed product resolution is structural reconciliation of already separate changes: accepted A1 behavior plus existing R2 candidate behavior. If a conflict requires altering either algorithm, exception/wire, owner binding, lock order or lifecycle semantics, stop and obtain the reviewer's ruling before implementing that change.

## Merge mechanics and verification plan

1. Create a NEW native worktree/branch `codex/ticket-20-r2-on-a1` starting at closed A1 documentation tip `2c34bbf`. Leave both existing branches intact. This gives the R2 integration branch the reviewed A1 unit as its first-parent base.
2. Merge the original R2 branch into that new R2 branch with no automatic commit, resolve only the invariants above, then inspect the staged diff/ASTs. Do not merge R2 into the CLOSED A1 branch, do not rebase/rewrite either old history and do not push.
3. Before committing, assert one evidence-state class/helper set; accepted A1 helper/selected-service AST parity; R2 schema2 and diagnostic owner retained; D1 guards/D2 serializer retained; capabilities empty. Verify the authoring `_persist`, diagnostic `_persist_diagnostics` and lifecycle/state paths were not replaced by R1 versions.
4. Run the A1 module/MCP and the existing R2 diagnostic owner/integration selection on the merged candidate. Keep known pre-existing R2 fixture migration failures explicitly attributed if encountered; they are R2 work, not exceptions to the already-green independent A1 unit. Do not silently migrate or weaken those tests during merge resolution. Report exact outcomes; no merged-R2 acceptance is inferred from a clean Git merge.
5. Record merge parents, resolved hunks and check results. Refresh D4 contract against that actual candidate next. R3 still gets its own contract before operator create. No queued package is started by this plan.

## D4 decision inputs after reconciliation

The accepted A1 baseline now has combined parent/brief A maximum0.1832s in the independent reviewer run (root maximum0.179806s), with3 raw reads and1 content walk per sample. Other recorded A maxima are<=0.169s. The measured authority phase at the specified max-source fixture is no longer the capacity-margin blocker. These observations are from the accepted R1/A1 base, not new timing on R2's shared writer/index.

Design inference: D4 is still needed for the diagnostic IO boundary problem. The retained R2+D1+D2 gate already measured heavy diagnostic writes and structural reports directly through the store facade under the boundary, not through repeated service packet validation. A1 does not change quarantine_submission, diagnostic validation/inventory/body IO/persist/report, and those calls do not invoke store._packet or the selected-service packet scope. Thus A1 supplies no mechanism that removes the observed diagnostic heavy misses (including0.359340/0.286323 and later0.386682/0.284912s) or structural-read0.270486s miss. This is a call-path inference, not a claim of a fresh post-merge latency measurement.

No fresh profile is needed just to decide whether the untouched diagnostic IO still needs separation; the old profile and misses remain in the record. After actual reconciliation, the proposed D4 refresh should use A1's now-passing authority baseline and narrow the remaining question to diagnostic capture/IO/settlement and report reads. Its real production peer/boundary gates remain mandatory after reviewed contract, observed reds and implementation. Neither limits nor retention budgets change. If the merge reveals a new diagnostic path dependency on A1, reassess this inference before choosing a new experiment.
