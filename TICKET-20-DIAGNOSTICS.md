# Ticket 20 R2: independent diagnostic ownership, frozen contract and first reds

Status: EXACT PAYLOAD FREEZE CLEARED at86dad152, with K1-K9 folded below beside the first observed reds. R2 production is NOT cleared. Seth approved R1-R3 scope; R1 is independently CLEARED at bd1f3922 (product 74f4697). First root behavioral/infrastructure reds are now authorized; production and helper work still wait for their review. R3 source-reference compaction remains a separate contract. Production capability stays empty; no authoring quota, public route, activation, deployment or purge is added.

## Outcome and governing choices

Authoring validation must stop paying for quarantine details, overflow summaries and diagnostic attachment links. A corrupt diagnostic JSON file must leave a healthy authoring index usable for prepare/admit/version reads/import/export/cancel/Stop settlement and channel lifecycle metadata. Diagnostic-dependent operations must report their own unavailability rather than fabricate an empty log or successful diagnostic receipt. Shared-root/device failure can naturally affect both files; isolation does not bypass owned-path or storage safety checks.

| Proposed choice | Reason and consequence |
| --- | --- |
| Two owners and two atomic JSON files, inside the existing artifact_store module | Independent locks/validation without introducing a general storage framework, import cycle or new manifest source module. The private shared filesystem base and moved helpers are enumerated below; schema validation and owner state remain independent. |
| Authoring index version 2; independent diagnostic file version 1 | Requests lose persisted quarantine_ids. Index loses diagnostic/overflow containers and their cross-checks. Audit/protocol/seal/version-row formats and portable archive schemas remain unchanged. |
| Explicit request_diagnostics read | No state-machine decision or public transport DTO consumes quarantine_ids/overflow_count. ArtifactService._projection DOES deep-copy the whole row into every private MutationResult, so its private RequestProjection changes with the store row. Keeping them in every request read would reintroduce a diagnostic read/lock into authoring. Their debug projection moves to this separate method; internal row shape changes are explicit below. |
| No implicit multi-file migration of nonempty development v1 data | There is no released artifact data. Hold and preserve a nonempty legacy index rather than risk partially moving diagnostics across two commits. Empty v1 is recognized without data loss. No live installation is inspected or converted by this package. |

The governing request-row compatibility change and development-v1 hold policy are accepted design. Exact payload freeze remains under review before reds; no mechanism here is claimed implemented.

## Source trace

Read artifact_store quarantine_submission/diagnostics/_row/_validate_index/_validate_diagnostics/_validate_summary/_persist/_put_bytes and lifecycle/export/import methods; artifact_service _diagnostic, _packet, admit_saved, reject_response and recover_startup; app factory/store construction; channel RENAME_STEPS/DELETE_STEPS; artifact_archive portable projections. Existing direct production quarantine callers are ArtifactService._diagnostic, the unmatched saved-result branch in admit_saved, and late/unmatched saved results in recover_startup. They call the store facade, not a new public diagnostic API. Existing portable_lineage projects no diagnostic rows, quarantine links or summaries.

## Files, formats and bounds

All locations are relative to the SAME ArtifactStore data root. No caller-supplied path/title is used.

| Data | Location / exact outer shape |
| --- | --- |
| Authoring index | artifacts/index.json: {version:2,lineages:{},requests:{},versions:{}} |
| Diagnostic metadata | artifacts/diagnostics.json: {version:1,diagnostics:{Hex32:Detail},dispatch_overflow:{Hex32:Summary},store_overflow:Summary or null} |
| Diagnostic bodies | Existing artifacts/quarantine/Hex32.txt, binary UTF8 bytes, immutable put-once |
| Locks and temporary files | Existing startup_lock and atomic_json conventions, separate index.json.lock and diagnostics.json.lock; object .txt.lock remains separate. Lock files are neither bodies nor orphans. |

Authoring v2 request fields are EXACTLY audit,channel,state,reason,updated_at,version_id, with import_source added ONLY for imported rows. No quarantine_ids or overflow_count is persisted. Lineage/version metadata and audit key sets remain as in R1. _validate_index checks authoring grammar, immutable references, ordered versions, parents and pending slots only. It never reads, locks, hashes or validates the diagnostics file or quarantine directory. Metadata getters and low-level state setters also have no diagnostic dependency. Imported exception guards remain strict, with no new authority or state/reason enum change; the stored original_reason question remains open as recorded in STATUS.

Detail preserves existing fields id,kind,request_id,attempt_id,dispatch_id,reason,sha256,byte_count,actor_identity_id,received_at,updated_at,not_retained,body_object_id, plus NEW attached_request_id (Hex32 or null). kind is quarantine. attached_request_id may be non-null only when it equals the non-null request_id AND request_ids(attached_request_id)[dispatch_id] equals row.dispatch_id. Validate this derivation without reading authoring. A standalone owner never consults authoring to validate attachment. The facade freezes eligibility as described below. Existing diagnostic UUID derivation is UNCHANGED: canonical request_id/attempt_id/dispatch_id/reason/sha256/byte_count/actor_identity_id only. Attachment is not an ID input, so no diagnostic rekeying.

Summary preserves exactly id,kind,dispatch_id,counter,latest_diagnostic_id,latest_sha256,latest_byte_count,latest_reason,updated_at. Existing summary IDs, dispatch/store kinds, saturating counter <=2**31-1, enum reasons, R1 numeric bounds and last-key-only overflow dedupe remain. Do not invent all-history overflow dedupe or retain more detailed rows.

Preserve ALL current budgets: 8 details per dispatch, 256 dispatch groups, 1024 detailed records; at most 512 KiB per retained body, 8 MiB total body bytes and 1024 body objects INCLUDING orphan bodies. Invalid UTF8/NUL bodies remain hash/count-only. Group overflow versus global overflow precedence, duplicate return behavior, no auto-deletion and first-body bytes remain unchanged.

Proposed diagnostic JSON cap is 1,048,576 actual encoded bytes; bounded read is cap+1, with strict UTF8, duplicate-key/nonfinite/type/depth/key-set refusal. This is a parser/storage safety bound for the fixed diagnostic budgets, not an authoring admission quota. Design sizing reused the existing R1-valid conservative 1024-detail/256-summary/global-summary fixture: old standalone frame 749,770 B; adding attached_request_id yields 810,186 B (60,416 B growth), leaving 238,390 B under 1 MiB with default ensure_ascii=True atomic_json encoding. Proposed empty authoring-v2 frame is 62 B. The old fixture validates under R1; the projected R2 frame has NOT yet passed a new R2 validator. Some simultaneous maxima are structurally valid upper bounds rather than a naturally reachable transaction history. Required red/green tests must build the new maximum row/file and confirm every writer-produced legal shape fits; no budget may be lowered to fit this cap silently.

The diagnostic validator is bounded and self-contained. Validate container/count/scalar shapes before canonical sizing; load no packets, Markdown, channel catalog, runtime registry or authoring rows. Keep a fingerprint-validated in-memory snapshot as the existing store does; formatting-only equivalent edits may refresh the stamp, changed authoritative content holds that diagnostic owner. A missing file is healthy-empty on cold construction, as with the existing store; disappearance after a known snapshot holds the owner. Cold-start body orphans cannot prove whether metadata was lost or the first metadata commit never landed. Report those orphans and preserve body quotas, with no invented historical dedupe or reconstruction journal. Metadata validation is lazy about body bytes as today. A missing/corrupt body is an object matter; it does not hold authoring metadata. No body download API is introduced.

## Owners, facade and read compatibility

Proposed ArtifactDiagnosticStore(data_dir, *, hold_unreadable=False, legacy_held=False) lives in artifact_store.py, with its own path, RLock, fingerprint/held state and independent writer. ArtifactStore constructs diagnostic_store for the same root with hold_unreadable=True, regardless of an ordinary authoring-corruption hold; a nonempty legacy-v1 hold instead passes legacy_held=True and holds BOTH owners. Missing files are otherwise healthy-empty and construction writes nothing. app/run keep constructing ONE ArtifactStore and the same ArtifactService; a factory test proves its diagnostic owner uses that exact root. No standalone model tool or new route exposes the owner.

| Interface | Proposed behavior |
| --- | --- |
| ArtifactStore.quarantine_submission(existing signature) | Facade retained. Validate inputs. For request_id=None, bypass ordinary authoring corruption and call diagnostic_store.record with attached_request_id=None; the legacy-hold marker still refuses every diagnostic write before creating any file. Otherwise copy cached validated attachment eligibility under the authoring RLock, release it, then call record; a known held/uninitialized owner refuses rather than guessing. This snapshot is memory-only as specified in J5; it does not refresh the index from disk. No authoring persistence or request-state mutation. |
| ArtifactDiagnosticStore.record(request_id,attempt_id,dispatch_id,*,reason,content=None,actor_identity_id=None,attached_request_id=None,now=None) | Own-lock transaction; returns existing Detail/Summary shape with attachment field only on Detail. No channel/authoring lookup, provider or callback. |
| ArtifactStore.get_request / get_request_by_dispatch and mutator returns | Detached authoring-v2 row only, no automatic diagnostic enrichment or overflow lookup. Existing metadata/signatures retained; the two debug fields intentionally move. ArtifactService's private mutation projection follows that narrower row. Current agent ACK/QuarantineResult/public transport shapes are unchanged. Future operator DTO allowlists stay unchanged; amend its private ExistingRequestRow definition after R2 is accepted. |
| ArtifactStore.request_diagnostics(request_id) | Explicit detached {available,quarantine_ids,overflow_count,error}. Validate Hex32, then read ONLY diagnostic metadata by attached_request_id, never authoring. Unknown requests and requests without attachments return healthy []/0, not null; this new debug API does not establish request existence. Attached IDs ordered received_at/id ascending, intentionally replacing append order. Attribute the matching deterministic dispatch summary ONLY when at least one stored attached row exists; otherwise overflow_count=0. Imported rows never have attached rows, hence healthy []/0. This avoids guessing imported/local/existence under held authoring; standalone summaries remain globally visible. A held diagnostic owner returns unavailable even for an imported/unknown ID. |
| ArtifactStore.diagnostics(*,limit=100) | Assemble independent authoring object/orphan observations and diagnostic report after separate snapshots. Healthy old fields rows/count/truncated/dispatch_group_count/detailed_count/retained_body_bytes retained, plus owners,partial,errors, with exact per-owner types below. No owner lock is nested. |

Attachment eligibility rule is unchanged: in the cached validated snapshot request exists, is LOCAL (any state except imported), and its immutable deterministic dispatch matches the supplied dispatch. Attempt mismatch is still diagnostic data, not a state transition or attachment authority. Otherwise attached_request_id is null. A repeated diagnostic ID retains its FIRST attachment decision, even if a matching request is reserved later. Never infer attachment later merely because a previously unmatched request_id now exists. Imported requests never gain attachments. Rename/cancel cannot change local eligibility or immutable IDs; imports never replace a local UID, so the detached decision is safe without holding an authoring lock through file IO.

When the diagnostic owner is held, request_diagnostics for ANY valid request ID returns available:false, null IDs/count and the fixed diagnostic error object below. It does not consult authoring or infer imported status. Imported []/0 is a healthy-diagnostic projection only. Authoring rows remain readable and unchanged. For the combined diagnostics report, unavailable totals are null, partial/truncated are true and errors names the unavailable owner; never invent zero. If authoring is healthy, its packet/version orphan and corruption observations can still be shown. If authoring is held, do not guess packet/version references or classify those bodies as orphans. If diagnostic metadata is held, do not classify quarantine bodies as orphans because references are unknown. General inventory observations are read-only snapshots, never deletion/recovery authorization; exact invocation staging receipts retain their existing lock-bound orphan calculation.

Proposed ArtifactDiagnosticsUnavailable subclasses ArtifactUnavailable, with fixed internal code artifact_diagnostics_unavailable and text 'Artifact diagnostics are unavailable. Repair the diagnostic metadata before retrying.' No exception message/path/body is interpolated. Existing artifact_transport.failure catches this ArtifactUnavailable subclass and projects EXACT HTTP 503 code artifact_storage_unavailable, with no new successful QuarantineResult shape. The new combined diagnostic errors map uses fixed codes/text only. Shared filesystem/root failures may hold both owners normally.

## Atomicity and locking

Ordinary authoring remains engine/catalog boundary -> authoring lock -> index process lock; it never acquires the diagnostic lock. Diagnostic facade takes authoring lock ONLY for metadata/attachment snapshot and releases it before diagnostic lock -> diagnostic process lock -> per-body process lock. The diagnostic owner never calls back into authoring or channel policy. No authoring+diagnostic lock overlap, reverse lock edge or cross-file transaction.

Within a diagnostic transaction, recheck the diagnostic fingerprint under its own process lock, enforce budgets from the real body inventory, construct and validate the complete candidate, and check its actual encoded size UNDER the diagnostic lock BEFORE any body put or JSON replace. Over-cap refuses as ArtifactDiagnosticsUnavailable (internal artifact_diagnostics_unavailable; transport503 artifact_storage_unavailable), creates no body and therefore no new orphan. Then put body first, then existing atomic_json metadata write (exclusive temporary file, flush/fsync, atomic replace). Update memory only on confirmed metadata commit. On IO/lock/uncertain-commit failure, return no diagnostic receipt. Before replacement, prior metadata remains; after an uncertain replacement, preserve whichever complete version landed and hold that diagnostic owner until verified reload, never reset or overwrite the uncertain outcome. Any staged body still counts against the physical quota; call it an orphan only when healthy metadata proves it unreferenced, otherwise report unknown rather than invent zero. Never delete it. A fresh owner can recognize a confirmed landed duplicate; a stale owner fails closed rather than overwriting external changes. Same-owner concurrent writes serialize; separate stale owners cannot silently lose records. Body conflicts remain scoped ArtifactConflict as today.

Existing ArtifactService engine/catalog scopes are NOT silently released or reordered by R2. A service diagnostic call can still run under its existing outer boundary; only authoring/diagnostic owner locks are separated. R2 does not promise a service call bypasses that engine serialization or arbitrary filesystem failure latency. Required Event tests prove low-level authoring settlement does not wait for a diagnostic owner lock/IO. Normal diagnostic service hold/wait timings must pass the gate below; if they require a new authority phase split, return for design review instead of adding a background journal, dropping durability or weakening a timing gate.

## Failure, authority and recovery semantics

Valid prepare/admit/version reads, import/export, metadata counts and cancel/Stop do not require diagnostics. Corrupt diagnostics must not set authored artifacts_held, pause channel creation/reopen/rename/delete, break valid version admission or change the immutable parent/head. Packet/Markdown corruption stays scoped as before.

Diagnostic-required paths are an explicit exception: _diagnostic, invalid-response reject_response, bad packet reporting, unmatched/terminal saved-result recording and their recovery branches must return a real durable diagnostic ID before claiming successful quarantine. If diagnostics cannot persist, propagate the typed unavailable error using the existing 503/held path; no fake ID, ACK, disposition, terminal proof or model retry. Existing preceding activation or subsequent state/fence operations keep their current order. This can leave the current request active until cancel/Stop or the existing empty-delivery settlement; it is not a successful quarantined response. A healthy peer's authoring/recovery still proceeds; per-dispatch diagnostic/storage failures at recover_startup808 reach held/storage_unavailable (832), never abort all startup work. The fulfilled ACK-repair catch799 instead reports operator_recovery_required; preserve that branch distinction. No new outbox, queue operation or generation journal.

The three direct quarantine call sites retain the facade signature; all transitive service entries listed below retain their existing durable-success mapping and propagate diagnostic unavailability honestly. Tests must cover normal diagnostic success and every caller's diagnostic-unavailable path. A diagnostic write never advances a request state itself. In particular, a late/stale submission cannot poison current work, and a standalone diagnostic for an imported request changes neither its audit, lineage nor versions.

## Development v1 handling, lifecycle and backups

Proposed legacy policy: a strictly empty v1 index (all authoring/diagnostic maps empty, store_overflow:null) may normalize to empty v2 IN MEMORY; the first ordinary authoring write emits v2. No startup rewrite. Any nonempty v1 index, including diagnostics-only data, holds authoring with fixed guidance 'Saved development artifacts use schema 1. Conversion is required; no files were reset.' and preserves index/bodies byte-for-byte. Do not create/copy a diagnostics file or present missing diagnostics as empty in this case; combined diagnostics reports the legacy schema unavailable too. Unknown headers, partial field sets or v1 diagnostic keys mixed into a v2 authoring index hold. The intended v2-authoring/v1-diagnostic pair, and a v2 authoring index with absent healthy-empty diagnostics, are valid. No automatic conversion, reset, merge or deletion is part of R2. Development data can be retained for the prior reader; any offline conversion requires a separate explicit reviewed operation. An old reader refuses an emitted v2 authoring index; a new owner holds observed unsupported/data changes. Simultaneous old/new writers or downgrade on the same root are unsupported, and old code cannot understand the new diagnostic file. Do not claim a legacy empty-v1 file itself blocks every old writer before the first v2 authoring write. A nonempty dev-v1 owner sets artifacts_held and pauses the existing held-owner create/reopen/archive/rename/delete operations. Production capability remains empty, so no artifact authoring has been enabled outside tests by this work; no live data inspection is claimed. No offline-converter owner is assigned, and no converter exists in R2. This policy is accepted design, not a migration already performed.

The eighth artifacts rename step remains exactly one existing step: rename authoring lineage/request/version channel fields. Diagnostics have no mutable channel field, so IDs/attachments/path and diagnostic file bytes do not move. Diagnostic corruption must not fail that step. Seven-name intent resume and finished-intent guards remain; DELETE_STEPS unchanged. Archive/delete retain diagnostic metadata/bodies just as current quarantine data, never purge. Catalog/retained counts and preview tokens remain authoring-only; diagnostic JSON corruption alone does not add an artifact blocker or held flag.

Current portable archives already EXCLUDE diagnostics, request quarantine links, overflow summaries, bodies and private briefs. R2 preserves schema1 healthy-empty bytes and schema2 portable shapes: no diagnostics.json member, import never restores diagnostic rows or writes the diagnostic owner. A corrupt diagnostic owner with a healthy authoring index therefore permits authored-content export/import. A held authoring/legacy index still refuses export under the existing configured-owner rule; no silent schema1 fallback. Unknown diagnostic members in ZIP remain structural refusals before mutation. CHANNELS must state that diagnostic logs/bodies are excluded from channel backups and retained on channel delete. No new privacy scrubbing: built diagnostic metadata never copies launch nonce/fingerprint, seal, bearer/config/path or raw content; retained bodies remain private hostile user/model text with existing caps, not new links or tool inputs.

## Red-first work and compatibility movement

Root first behavioral reds: diagnostic-only submission must not create/mutate authoring index bytes; a nonempty authoring index must stay byte-identical across quarantine detail/overflow writes; corrupt diagnostic JSON must refuse a diagnostic write while valid authoring/cancel/Stop/export proceed. Use current real facades for behavior proof; missing owner/helper attributes are labeled infrastructure only. No production before reviewed reds. No helper is assigned by this document; existing helper files stay frozen until named schema-fixture changes are reviewed.

Required coverage includes independent cap/held/no-reset/duplicate/depth/type validation; exact IDs and first-attachment/no-retro-attach; imported standalone behavior; 8/256/1024 and body/orphan budgets with saturating last-key summaries; body-before-metadata fault/uncertain commit; stale owners; Event lock isolation and concurrent same-ID writes; partial diagnostic read availability; v1 empty/nonempty/mixed handling; actual app factory; lifecycle rename/delete/preview with held diagnostics; archive exclusion/strict unknown member and source/Markdown/seal goldens. Real-body hash/count/binary CRLF semantics remain. No existing numerical/assertion budget is weakened.

Named compatibility movement (review before editing): diagnostic methods in tests/test_artifact_store.py; full-group fixtures in test_artifact_store_review.py; both near-counter seeds in test_artifact_store_saturation.py; test_artifact_diagnostic_oversize.py; imported attachment checks in test_artifact_export_store.py and test_artifact_imported_store.py; diagnostic portions of R1 test_artifact_record_bounds.py. Seed diagnostic maps/counters into the diagnostic file/owner, not authoring index. Replace debug-field access with request_diagnostics; preserve the actual expected IDs/counts/body bytes. Authoring-only version2 fixture follow-ups and private ExistingRequestRow docs must be listed separately, never masquerade as assertions passing unchanged. Root uses one NEW test_artifact_diagnostic_owner.py for R2 behavior. Root re-runs all existing authoring/authority/recovery/worker/transport/capability/runtime/lifecycle/archive suites after movement; the R1 991296-byte VERSION-row golden should remain exact because R2 does not compact provenance.

## Timing and completion gates

R1 reference points: builder full1681/four skips315.065 s; affected876 PASS246.414 s; reviewer artifact301 PASS193.5 s. Uninstrumented4MiB import maxima were0.252326 /0.190379 /reviewer0.2057 s under the separate0.300 s import gate. Instrumented timing is never performance acceptance.

After R2, rerun the EXACT4MiB/100-prior-lineage/128-request-version import profile ten samples, real atomic_json/fsync, parse and whole authoring-index validation included, <=0.300 s. Run with a full valid diagnostic ledger present and again held; forbid diagnostic reads/validation from the measured authoring path. Independently test the conservative maximum diagnostic frame fits1MiB and a reachable full public-write profile (1024 details, body objects/bytes at existing limits); do not claim every structural maximum is naturally reachable simultaneously.

Re-measure the CURRENT create path with100 prior lineages,2MiB/1000-message packet,512KiB parent and real persistence, ten samples plus concurrent require_active waits, diagnostics empty/full/held. Report phase/whole holds and wall time. This is a diagnostic comparison, not a new R2 promise of0.270 s: source refs and duplicate packet reads are still present, so the earlier0.41-0.68 s whole-create failure may remain until R3 and the reviewed operator phase split. No quota is chosen here. Final operator maximum-shape0.270 s gate remains held and mandatory in that later package. Report normal diagnostic-service hold/waits against the gate too; do not hide shared-engine serialization.

Completion: reviewed R2 contract/payload freeze -> observed reds -> implementation -> new/changed/frozen affected suites, uninstrumented import/create measurements and one full discovery without overlap -> independent diff/execution review. Then R3 DOCS contract separately. No activation/publication and no claim this alone fixes all authoring growth.


## F1-F10 exact change inventory and accepted refinements

This section refines the proposal only. Governing choices are accepted; payload freeze, new tests and production remain behind independent review.

### Production and document sites

| Site | Planned R2 change |
| --- | --- |
| artifact_store._empty; ArtifactStore constructor/load/_check_index/_persist | Authoring version2 exact frame, empty-v1 RAM normalization and nonempty-v1 hold; construct independent owner; no diagnostic validation in authoring persistence. |
| _validate_imported (current lines 315-316); _import_metadata (647/666) | Remove quarantine_ids from exact imported-row keys and constructed rows; preserve imported read-only authority, state/reason and provenance rules. |
| _row (554-559); reserve_request row (892) | Remove computed overflow_count and stored quarantine_ids. Base row is detached authoring metadata only. |
| _validate_index (1238-1275) | Version/key-set/ref checks authoring only; remove diagnostic containers, attachments and summary validation. |
| _validate_diagnostics/_validate_summary (1353-1396) | Move to independent owner; preserve scalar/ID/budget rules, add attached-request derivation, encoded cap and independent load/hold behavior. |
| export_metadata (595-605), lifecycle_scope, imported commit | Detached metadata never enriches with diagnostics. Portable allowlist and lifecycle metadata shapes otherwise unchanged. |
| quarantine_submission, diagnostics; NEW request_diagnostics | Facade snapshots, independent reports and intentional ordering described above. |
| Filesystem mechanics | Extract _safe, _object_path, _put_bytes, _fingerprint and _fingerprint_quiet unchanged into a private _ArtifactOwnedFiles base in SAME module, shared by both owners. No schema/data/held state belongs in this base. Move _body_inventory to diagnostic owner, do not duplicate it. Keep authoring _record_object_error scoped to packet/version; diagnostic object observations remain diagnostic-owned. |
| Diagnostic IDs | Move unchanged _diagnostic_id/_summary_id pure derivations into shared module-private helpers with existing facade delegates if needed by current callers/tests. Do not rekey IDs. |
| Service projection | ArtifactService._projection at lines 102-105 currently deep-copies the whole getter row, then removes launch_nonce. Private MutationResult.request therefore loses quarantine_ids/overflow_count. Public ACK/QuarantineResult shape remains unchanged. |

All diagnostic-producing service entries are in scope for explicit success/unavailable probes: submit_cli at 328/340/344; admit_saved at 401/405/413/428; _repair_fulfilled_ack at 649; resume_request and _resume_recovered via _packet at 262/607/693; get_brief at 275/get_delivery at 286 via _packet; reject_response at 448; recover_startup at 808-812. Line numbers identify the reviewed R1 source, not stable API names. No service state ordering or lock phase split is authorized by this list.

The document amendment map is AUTHORITY at 117/183 (no attachment scan; narrower private RequestProjection), STORE-SCHEMA at 82/103/105/113/116 (request keys, attachment/debug read, diagnostic ownership/budgets), LIFECYCLE-BACKUP at 140/156 (exact imported request keys lose quarantine_ids, not merely an empty value), OPERATOR-ROUTES at 331/377 (private ExistingRequestRow and observation diagnostic owner). Linked R2 proposal notes are added there now; exact authoritative schema text is replaced with the implementation pin, so proposed v2 is never presented as running v1. No public operator DTO field is added.

### Ordering, unavailable paths and fault envelope

request_diagnostics orders retained attachments by (received_at,id), not arrival order. This intentionally makes backdated equal-time reads deterministic without a new sequence field. Existing store.py410/505 single-ID/list membership assertions move to the separate read; they do not prove multi-row insertion ordering. Add a backdated/tied timestamp test pinning the new ordering, retaining every ID and count.

| Condition | Required observable outcome |
| --- | --- |
| Healthy authoring, held diagnostics, unreadable packet | _packet's diagnostic precedes its failed-state write. Propagate typed 503 artifact_storage_unavailable, no fake receipt; request stays LIVE until explicit cancel/Stop settlement. No terminal failure is claimed. |
| CLI invalid Markdown, held diagnostics | Normal retryable 400 invalid_content with a diagnostic ID becomes 503 artifact_storage_unavailable. Correction feedback is unavailable because it could not be saved; never invent the receipt or return 400 as if it had been saved. |
| request_id=None, held authoring but healthy diagnostics | Standalone diagnostic persists through the facade without any authoring snapshot, read or write when held for ordinary corruption. Non-null request IDs still require a healthy attachment snapshot. Nonempty legacy-v1 is the explicit exception: both owners held, no diagnostic file created. |
| Nonempty legacy-v1 authoring hold | Facade stores a private legacy-schema hold marker at load and passes it into the diagnostic owner. Every record, including None, raises typed diagnostic unavailable before any file creation; existing legacy data is never merged. request_diagnostics reports diagnostic unavailable and combined diagnostics reports both owners held with reason legacy_schema, even if the new file is absent. The independent new owner never inspects the old index. |
| Diagnostic process/body lock timeout | Diagnostic owner unavailable, typed 503; diagnostic-dependent state transition remains live, with no fabricated ID. Cancel/Stop remains independently usable. |

Two timing budgets are distinct. NORMAL: every uncontended maximum-graph diagnostic read/write OUTER engine/catalog hold must be <=0.270s including validation, encoded cap check, full body inventory and real fsync; concurrent require_active wait is measured and must also be <=0.270s. FAULT: unchanged startup_lock permits up to 10s diagnostic-process plus 10s body-process waits (<=20s process-lock waiting), PLUS unbounded thread scheduling/OS IO residual. This is not a hard wall-clock bound and is not the normal pass gate. No timeout is shortened to make a benchmark pass.

Existing exposure comparison: current quarantine_submission already executes per-body _put_bytes (10s process-lock wait) and authoring _persist (another 10s index-process wait plus fsync) inside the service engine/catalog boundary. Existing ordinary authoring _persist alone has a 10s index-process wait plus fsync. R2 diagnostic record retains the same two-lock-wait class, now diagnostic-process then body-process; it does not make a previously outside-boundary body wait reachable inside it. Authoring lock is released before this diagnostic IO, so low-level authoring settlement is independent; shared-engine service calls can still wait. A new authority phase split is outside R2.

### Complete compatibility movement

All entries below are PLANNED, no test edits yet. Rewrite means owner/fixture/access changes preserving numerical, ID, hash and state expectations; unchanged means rerun without assertion changes.

| Test / fixture | Rewrite versus unchanged-by-design |
| --- | --- |
| test_artifact_store.py410/505 and diagnostic methods | Rewrite attachment/debug reads to request_diagnostics and seeds to diagnostic owner; preserve detail IDs, limits and counts. Add explicit new ordering test. |
| test_artifact_parent.py67 | Rewrite empty quarantine_ids assertion to request_diagnostics; parent/version assertions unchanged. |
| test_artifact_store_integrity.py53 | Combined orphan report unchanged, rerun against v2. |
| test_artifact_store_integrity.py133 | Rewrite held-owner operation list: non-null diagnostic snapshot refuses; standalone None diagnostic succeeds independently, preserving held index bytes. |
| test_artifact_admission.py277 | Diagnostic reason/ID report assertion unchanged; add held-diagnostic invalid-content503 case separately. |
| test_artifact_recovery.py169/266 | Existing unavailable recovery and conflicting-duplicate report assertions unchanged; add per-dispatch diagnostic-held recovery probes. |
| test_artifact_workers.py336 | Existing invalid-response diagnostic report unchanged; new held-diagnostic path reports unavailable without fake ACK/disposition. |
| test_artifact_staging_receipt.py77; test_artifact_import_stage_review.py219; test_artifact_imported_store.py168 | Combined orphan report assertions unchanged, no staging-receipt changes. |
| test_artifact_export_store.py40 | Rewrite constructed imported row exact keys, remove quarantine_ids. |
| test_artifact_export_store.py142 | Rewrite empty attachment assertion to request_diagnostics; standalone imported detail/budget report assertions unchanged. |
| test_artifact_record_bounds.py322-337/691-706 | Rewrite diagnostic detail/summary seeds and direct validator calls to diagnostic owner; preserve actual R1 scalar bounds/positives and mutation proofs. Authoring/observation tests and 991296B version golden unchanged. |
| test_artifact_diagnostic_oversize.py56-65 | Rewrite full metadata seed into diagnostic file; preserve group/global reason, count and body budget assertions. |
| test_artifact_store_review.py82-92 | Rewrite full-group seed into diagnostic file, preserve 1024-record and 256-group assertions. |
| test_artifact_store_saturation.py45/56 | Rewrite both near-counter seeds into diagnostic file, preserve 2**31-1 saturation and last-key dedupe. |
| tests/fixtures/artifact_portable_projection.json78; artifact_portable_revision_projection.json80/149/214 | KEEP stale quarantine_ids in hand-authored SOURCE rows intentionally as ignored-unknown-key allowlist compatibility/leak inputs, not v2 store rows. Expected portable golden values stay literal/unchanged. Add real v2 export coverage proving actual store source rows omit the field. |

Remaining authoring-only exact-schema/version fixture follow-ups must be named in the reds/implementation receipt after a complete search; no assertion weakening. Root owns one new diagnostic-owner behavioral file; prior helper files remain frozen until explicit reviewed adaptation.

### Design-only maximum-graph measurement, not R2 acceptance

The 810186B graph was rebuilt with 256 real derived dispatch IDs and attached_request_id derivation for all 1024 rows, preserving the size. Existing R1 diagnostic scalar/group validation plus the proposed attachment-derivation check passed in a PRIVATE prototype. It is NOT the complete future R2 validator or a writer-reachable history. The simultaneous max scalar graph and full physical inventory are structural conservative profiles: 1024 independently fsynced 8192-byte body files total 8388608B; their contents are inventory-only and do not match the graph's max-width byte_count/hash metadata. No body integrity/admission claim is made.

Prototype used real service._boundary and concurrent require_active, current default atomic_json fsync/replace and startup_lock, ten read/write pairs. Each sample included 810186B parse, validation and safe-path inventory of 1024 bodies; write included candidate validation and encoded cap check plus real metadata fsync of the complete unchanged frame, not the future record transaction path. Maximum read hold 0.193662100s, write hold 0.267954700s, peer wait 0.268551000s. All measured samples pass 0.270s, with only 0.001449s peer margin. Raw per-sample values are mirrored below. This narrowly passing prototype supports continued design review; it DOES NOT clear the complete R2 implementation timing gate. Full strict parsing, owner fingerprint/transaction behavior, reachable body writes and final validator must be measured after reviewed reds. Any gate failure returns the mechanism/cap to review; no budget reduction, silent cap change or timing relaxation.

```json
{
  "kind": "DESIGN ONLY, structural maximum not writer-reachable history; existing R1 validation plus attachment derivation, not complete R2 implementation",
  "metadata_bytes": 810186,
  "body_objects": 1024,
  "body_bytes": 8388608,
  "body_contents": "independent physical inventory, not metadata hash/length matching bodies",
  "fsync_mocked": false,
  "samples": [
    {
      "sample": 1,
      "mode": "read",
      "hold": 0.18157420004718006,
      "peer_wait": 0.18204969994258136
    },
    {
      "sample": 1,
      "mode": "write",
      "hold": 0.2608604000415653,
      "peer_wait": 0.2614603000693023
    },
    {
      "sample": 2,
      "mode": "read",
      "hold": 0.1868682000786066,
      "peer_wait": 0.18749759998172522
    },
    {
      "sample": 2,
      "mode": "write",
      "hold": 0.24528659996576607,
      "peer_wait": 0.2457070000236854
    },
    {
      "sample": 3,
      "mode": "read",
      "hold": 0.17796400003135204,
      "peer_wait": 0.17850770009681582
    },
    {
      "sample": 3,
      "mode": "write",
      "hold": 0.25962929998058826,
      "peer_wait": 0.26018829992972314
    },
    {
      "sample": 4,
      "mode": "read",
      "hold": 0.18059020000509918,
      "peer_wait": 0.18109869991894811
    },
    {
      "sample": 4,
      "mode": "write",
      "hold": 0.26130769995506853,
      "peer_wait": 0.2617501999484375
    },
    {
      "sample": 5,
      "mode": "read",
      "hold": 0.18372299999464303,
      "peer_wait": 0.18426140001975
    },
    {
      "sample": 5,
      "mode": "write",
      "hold": 0.26426440000068396,
      "peer_wait": 0.26483679993543774
    },
    {
      "sample": 6,
      "mode": "read",
      "hold": 0.19299649994354695,
      "peer_wait": 0.19355810002889484
    },
    {
      "sample": 6,
      "mode": "write",
      "hold": 0.2494165999814868,
      "peer_wait": 0.2499124000314623
    },
    {
      "sample": 7,
      "mode": "read",
      "hold": 0.1936621000058949,
      "peer_wait": 0.19416810001712292
    },
    {
      "sample": 7,
      "mode": "write",
      "hold": 0.26079490000847727,
      "peer_wait": 0.2612307999515906
    },
    {
      "sample": 8,
      "mode": "read",
      "hold": 0.1808852000394836,
      "peer_wait": 0.18144650000613183
    },
    {
      "sample": 8,
      "mode": "write",
      "hold": 0.24488959996961057,
      "peer_wait": 0.2455010999692604
    },
    {
      "sample": 9,
      "mode": "read",
      "hold": 0.17724760004784912,
      "peer_wait": 0.1777872999664396
    },
    {
      "sample": 9,
      "mode": "write",
      "hold": 0.2679547000443563,
      "peer_wait": 0.26855100004468113
    },
    {
      "sample": 10,
      "mode": "read",
      "hold": 0.17859839997254312,
      "peer_wait": 0.1791028999723494
    },
    {
      "sample": 10,
      "mode": "write",
      "hold": 0.26004540000576526,
      "peer_wait": 0.26049990009050816
    }
  ],
  "maximum_hold": 0.2679547000443563,
  "maximum_peer_wait": 0.26855100004468113,
  "limit": 0.27,
  "pass": true
}
```

Final R2 gate is maximum structural diagnostic read AND write <=0.270s with real persistence, full inventory/validation, concurrent peer waits, plus separate exact 4MiB import <=0.300s with diagnostics full and held. Record both structural (not writer-reachable) and reachable budget profiles distinctly. Source-ref compaction/create timing remains R3/operator work, not an R2 promised speedup. Capability remains empty, no activation/push.


## H1-H7 final payload refinements

These refinements replace the corresponding proposed statements above. No implementation or red-test clearance is implied.

### Templates, owner mechanics and legacy hold

H1: _empty() becomes the authoring-v2 template only. Its constructor initialization at 369, missing-file default at 420, _import_metadata at 647 staging frame and _validate_index at 1238 key-set template use that v2 frame. _prepared_import785-795 does NOT call _empty or calculate a new template: it parses the metadata already staged from _import_metadata647. The authoring literal version !=1 check1239 becomes version !=2; legacy-empty recognition accepts version1 separately before that validator. Add a SEPARATE _empty_legacy_v1() returning the exact former seven-key frame solely for recognizing a strictly empty v1 input; never use v2 _empty() to decide whether a v1 map is empty. Validate the full v1 empty shape before RAM normalization. Diagnostic owner has its own _empty_diagnostics() v1 frame; these version numbers refer to different files.

H2: both owners supply their OWN .path to shared _fingerprint/_fingerprint_quiet. Shared base contains only filesystem primitives already enumerated, not _load_index/_check_index/_persist. Authoring keeps those methods with the narrowly named v2/legacy-template and legacy-guidance changes; diagnostic owner implements separate _load_diagnostics/_check_diagnostics/_persist_diagnostics with its own cap, validator, held/stamp/known fields and data. Do not share a polymorphic schema transaction framework or copy the authoring validator into diagnostics. Preserve instance dispatch through target._put_bytes so existing fault injection remains effective. Required regression names: test_artifact_archive_driver.py:229, test_artifact_import_stage_review.py:194, test_artifact_staging_receipt.py:65 still patch the authoring instance method and must observe the same failures/receipts. Add an owner-path test checking each fingerprint uses only its own JSON path.

H3: _load_index detects structurally recognized nonempty v1 (defined in J3) with a private legacy marker and fixed guidance. In _check_index's except ArtifactUnavailable branch at 448, preserve that marker/guidance instead of overwriting _held with the generic index-held string; propagate marker to the diagnostic owner when discovered on reload too. This propagation does not take the diagnostic lock while the authoring lock is held: set the facade marker, release authoring, then hold diagnostic owner before the next diagnostic facade entry. All facade diagnostic reads/writes check the marker before entering the independent owner. Initial construction passes legacy_held=True. No diagnostics.json may be created/copied while marked, and no old index diagnostic row is merged. Repair/conversion is a separate future operation; clearing this marker requires a fresh owner after verified external repair, not a successful diagnostic read.

request_diagnostics intentionally has NO authoring dependency, including with an ordinary held index. It filters stored attached_request_id only and cannot distinguish unknown, imported or unattached requests; healthy empty result []/0 is a debug absence, not proof a request exists. Matching dispatch overflow is exposed only with at least one attached detail. This is an explicit change from the prior proposal's authoring snapshot/null-unknown behavior and retains immutable attachment decisions. Under legacy marker the diagnostic source is unavailable. Under an ordinary authoring hold and healthy diagnostics, attached rows remain readable without index access.

### Exact diagnostic errors and report payload

ArtifactDiagnosticsUnavailable(ArtifactUnavailable) has no caller-supplied message: constructor ArtifactDiagnosticsUnavailable(), fixed .code artifact_diagnostics_unavailable and fixed text 'Artifact diagnostics are unavailable. Repair the diagnostic metadata before retrying.'. Invalid diagnostic inputs retain ArtifactValidationError; conflicting immutable body retains ArtifactConflict. Cap, read/parse/validation/lock/uncertain-storage failures use ArtifactDiagnosticsUnavailable. Facade legacy authoring operations retain ArtifactUnavailable with EXACT guidance 'Saved development artifacts use schema 1. Conversion is required; no files were reset.'. No new public HTTP code: artifact_transport.failure maps the unavailable subclass to 503 artifact_storage_unavailable as before.

Fixed report Error = {code:string,error:string}. The ONLY owner error pairs are authoring ordinary: code artifact_storage_unavailable / error 'Saved artifact index is held; repair storage and restart.'; diagnostic ordinary: artifact_diagnostics_unavailable / 'Artifact diagnostics are unavailable. Repair the diagnostic metadata before retrying.'; either owner legacy: artifact_legacy_schema_unavailable / 'Saved development artifacts use schema 1. Conversion is required; no files were reset.'. Codes and messages are literals; no underlying exception text appears.

Combined report keeps rows/count/truncated/dispatch_group_count/detailed_count/retained_body_bytes, adds EXACT owners:{authoring:{available:bool,reason:null|authoring_unavailable|legacy_schema},diagnostics:{available:bool,reason:null|diagnostics_unavailable|legacy_schema}}, partial:bool, errors:{authoring:Error|null,diagnostics:Error|null}. It does NOT also add redundant authoring_available/diagnostics_available booleans. Unknown aggregate totals are null, errors entries for healthy owners null. Known diagnostic-local counts may still be returned when authoring is held; count across unknown authoring object observations is null, partial/truncated true. Request diagnostic read is EXACT {available:bool,quarantine_ids:Hex32[]|null,overflow_count:int|null,error:Error|null}; unavailable result uses the diagnostic or legacy Error above. Healthy result has error:null. No null whole-result/unknown-request branch.

Constructor signature is EXACT ArtifactDiagnosticStore(data_dir, *, hold_unreadable=False, legacy_held=False). Both keyword flags are bool; legacy_held is private facade initialization evidence, never deserialized JSON or external input. Default malformed diagnostic file raises the typed error; hold_unreadable=True retains a held object without resetting bytes. legacy_held=True constructs held without reading/creating the diagnostic file. The facade retains a marker check for later reloads as above.

Depth rule: root dict depth 1, maps depth 2, Detail/Summary dict depth 3. Refuse any dictionary container deeper than 3, any list anywhere, duplicate keys, nonfinite tokens, wrong scalar/field sets and parser RecursionError. Bounded read cap+1 runs before decoding. Apply the self-contained validator after strict parse; no body reads. Depth/shape refusal is diagnostic-owner unavailable on disk, not an authoring hold. Writer input shape errors remain ArtifactValidationError before effects.

Uncertain commit procedure: an exception after metadata replacement may have happened holds that diagnostic instance and returns no receipt. It never retries a write on the assumption replacement failed. Verified reload means a FRESH owner reads bounded bytes between equal before/after fingerprints, strictly validates the whole ledger, then establishes its own known snapshot; a landed row can be recognized by immutable duplicate ID on caller retry. It does not merge with or overwrite stale memory. The old held instance stays held unless its existing previously known snapshot is proven semantically equivalent after a stable bounded strict reread; an uncertain-new snapshot is not adopted silently. Set _invalid_stamp to a new object sentinel after uncertainty so even an unchanged old fingerprint cannot suppress that verification attempt. Production creates a fresh owner only on application restart, never an automatic diagnostic retry/replacement. A legacy marker is never cleared by this procedure. No public repair/reset API is added.

### Remaining normative document and fixture map

R2 implementation must replace STORE-SCHEMA13 healthy-index requirement for quarantine with the None/ordinary-corruption bypass and explicit legacy exception; :101 diagnostic ownership and :132 diagnostic report shape follow this contract. AUTHORITY82/84/126 retryable 400/failed-state/durable-diagnostic statements are conditional on diagnostic persistence: held diagnostics yields storage 503, no fake receipt or failed-state transition; preserve ordinary successful behavior. LIFECYCLE-BACKUP316's historical 'diagnostics map/counters in index.json' becomes diagnostics.json for R2; historical slice2 state invariants remain. Linked proposal amendments in those files now name these sites; exact normative replacement remains with the production pin.

| Additional fixture / test | Planned movement |
| --- | --- |
| test_artifact_record_bounds.py297-299 and 338-347 | Move all diagnostic/summary seeds and validator invocations to diagnostic owner, in addition to 322-337/691-706; preserve R1 bounds and mutation checks. |
| test_artifact_store.py403/444 | Replace removed row debug accesses with request_diagnostics; preserve detail identity/count assertions. |
| test_artifact_export_store.py149-152 | Authoring index unchanged after diagnostic write is now trivially true by design. Keep unchanged as compatibility guard; new independent-owner tests prove diagnostic metadata actually changed/duplicate remained no-write. |
| record_bounds.py503/519/633/640; test_artifact_store.py513 | Explicit authoring-v2 exact-key/version fixture follow-ups, no numerical/assertion weakening. Distinguish v1 legacy-hold tests from current-v2 corruption tests. |
| test_artifact_transport.py87 | Existing generic 503 mapping unchanged; add real diag-held invalid submission transport case asserting 503 artifact_storage_unavailable, fixed redacted body and no false diagnostic receipt. |
| test_artifact_mcp.py55 | Existing generic storage error guard unchanged; add actual diagnostic-held tool path, same fixed storage-unavailable code/text, no fake quarantine ID or success. |

### Reachable timing profile and no resampling escape

The prototype above measures the conservative full metadata frame rewrite, not the reachable heavy record path. Production NORMAL gate must measure BOTH: (1) 1023 detailed records followed by the 1024th valid retained body put (up to 512 KiB) with real body flush/fsync/rename AND diagnostic metadata fsync/replace, with physical inventory initially leaving room under 8 MiB/1024 bodies; (2) full 1024-detail graph followed by a distinct-key summary-only update. Measure separate maximum-graph reads as already required. Use at least 10 independent samples per path, concurrent require_active, full validation/inventory and no mocked fsync. Every hold AND peer wait <=0.270s, report every sample, max and margin, plus actual encoded graph/body counts. Structural maximum fixtures and reachable public-writer histories are labeled separately, never substituted for each other.

A miss is a miss: retain it in the receipt and return mechanism/cap to design review. Only a sample whose harness counted an actual PermissionError replace retry may have a separately attributed fault rerun, retaining the original sample. All other misses return to review; no general environment/load excuse or best-of/cherry-picked pass. atomic_json's eight PermissionError attempts can sleep 0.315s total (0.005+0.010+0.020+0.040+0.080+0.080+0.080); these sleeps are FAULT, not a NORMAL sample to claim passing. No latency guarantee is made for fault IO/scheduling, and neither timeout nor accepted diagnostic budgets are lowered.

Historical H-round status atbc089d1: exact freeze then awaited review; that docs-only pin had no new design spike, tests, helper or source edits. R3/operator/capacity/activation/push remain held.


## J1-J9 final precision pass

This section is docs-only, proposed for exact freeze. It corrects source-trace claims and closes the remaining payload/measurement choices; no new tests or production edits have been made.

### J1/J2: precise template and helper callers, named tests

_prepared_import only parses staged metadata, whose v2 frame was built at _import_metadata647. No direct _empty caller or separate accounting change is claimed there. _validate_index1239 must explicitly require plain-int version2, while the separate empty-v1 recognition runs before it. Keep ArtifactStore inheriting _put_bytes from _ArtifactOwnedFiles: target._put_bytes remains callable/patchable, including direct test_artifact_staging_receipt.py23-24 calls.

Choose facade delegates, not test calls to diagnostic internals: ArtifactStore._diagnostic_id(key) and _summary_id(dispatch_id) remain static delegates to unchanged module-private derivation helpers. Diagnostic class uses the SAME helpers. record_bounds326/337/700/702 and store_review91 keep calling those facade delegates; only their diagnostic seed/validator target moves. No diagnostic ID algorithm or caller argument changes.

Named existing patch-survival regressions are tests.test_artifact_archive_driver.ArtifactArchiveDriverTests.test_history_archive_io_before_writes_and_staging_io_after_history_are_distinct; tests.test_artifact_import_stage_review.ArtifactImportStageReviewTests.test_local_reserve_racing_stage_is_explicit_and_low_level_settlement_progresses; tests.test_artifact_staging_receipt.ArtifactStagingReceiptTests.test_mid_staging_io_is_unknown_with_fixed_reason_and_preserves_leftovers and .test_immutable_put_returns_created_true_only_for_its_own_write.

Required new names in tests.test_artifact_diagnostic_owner.ArtifactDiagnosticOwnerTests: test_diagnostic_only_write_does_not_create_authoring_index; test_diagnostic_detail_and_overflow_do_not_change_authoring_index_bytes; test_diagnostic_corruption_does_not_block_authoring_or_version_admission; test_authoring_validation_and_persistence_never_read_diagnostics; test_authoring_put_bytes_override_still_controls_import_staging; test_owner_fingerprints_use_separate_paths; test_legacy_nonempty_holds_both_owners_without_creating_diagnostics. These establish the authoring owner isolation rather than relying on source inspection alone.

### J3/J4: sticky legacy marker and intentional attachment projection

Initialize self._legacy_held=False before authoring load. _load_index recognizes legacy structurally: strict parseable JSON, plain-int version1 and EXACT seven old keys {version,lineages,requests,versions,diagnostics,dispatch_overflow,store_overflow}. Do NOT retain or invoke a v1 semantic validator for nonempty data. An exact strictly empty v1 template normalizes; any other structurally recognized v1 is legacy-held, even if its old rows would have been invalid. Malformed JSON or a wrong key set is ordinary corruption, not evidence of valid legacy contents. This replaces the ambiguous phrase 'valid nonempty v1'.

On nonempty recognition _load_index sets self._legacy_held=True BEFORE raising ArtifactUnavailable with fixed legacy guidance. Constructor catch380-383 branches on this flag and preserves that text instead of replacing it. _check_index448 does likewise. The success path451 must NEVER clear a legacy marker or its held guidance, even if the file is restored to original/empty bytes; check the sticky flag before normal stamp/equivalence recovery. _persist refuses a known legacy marker before writing and, if _check_index discovers one inside a write, its catch461-462 preserves the fixed legacy guidance instead of wrapping it in 'Artifact index write did not complete.'. Other failures keep the existing generic write mapping.

Both owners' legacy markers stay sticky for their lifetime. Diagnostic owner receives the flag during construction or through the facade when a later AUTHORING operation detects legacy. No authoring/diagnostic locks overlap during propagation. record(None) and request_diagnostics do not call authoring _check_index and therefore do not discover a newly replaced legacy file themselves: they check the marker already set at construction or by an authoring facade operation. External file replacement is not synchronously watched; this is an explicit limit, not a claimed cross-file transaction. On discovery, all subsequent diagnostic facades refuse before IO. Only fresh application construction after verified external repair can clear legacy markers.

Intentional read behavior: request rows no longer have _row's computed overflow_count at all. The separate request_diagnostics overflow_count is0 if all eight retained details for that dispatch were originally UNATTACHED (first attachment wins), even if a matching request is later reserved and a dispatch summary exists. Previously the local getter exposed any matching dispatch summary. This diagnostic-only change avoids retroactive attribution and does not change counters or state; global store_overflow was never counted in a request overflow_count and still is not. Test names: test_unattached_details_and_summary_are_not_retroactively_attributed and test_global_overflow_is_never_attributed_to_a_request.

### J5: exact partial data, uncertainty, parser and snapshot behavior

When diagnostic metadata is unavailable, diagnostic-owned rows contribute[] and retained_body_bytes is null, not a filesystem estimate. Known authoring object-error/orphan rows may still contribute to combined rows when authoring is healthy. count (combined total), dispatch_group_count and detailed_count are null, partial/truncated true, with the diagnostic owner error. If BOTH owners unavailable, rows=[] and every unavailable total/body count is null. When only authoring is unavailable, known diagnostic rows/counts/body bytes remain available, but combined count is null because authoring observations are unknown. No unknown references are called orphans.

An uncertain commit means ANY exception from atomic_json OR the immediate post-write fingerprint/stat. Conservatively set _held and _invalid_stamp=object() (new sentinel, not old fingerprint) before returning typed unavailable; no receipt or optimistic in-memory commit. A later same-instance check can attempt a stable bounded strict read despite an unchanged old stat and clear ordinary uncertainty ONLY if it equals the previously known snapshot. A changed landed ledger is never adopted by that stale owner; application restart creates the fresh diagnostic owner that can validate/adopt it and recognize an immutable duplicate on retry. No production auto-reload/replacement scheduler is added. Legacy-held is a separate sticky case and cannot recover through equivalence.

UTF8 BOM is REFUSED, not stripped; encode/decode uses strict UTF8. The container depth check is an explicit post-parse iterative walk (dict depth1/2/3, no lists); parser RecursionError/decode failure/duplicate key/nonfinite refusal maps to typed diagnostic unavailable on load. R1 numeric bounds remain: plain record int0..2**63-1; summary counter1..2**31-1; positive finite Number plain int<=2**63-1 or float whose shortest json.dumps token is<=23 chars. Booleans are not ints/numbers, zero/negative timestamp refused. The float width guard is defensive/type-consequence as R1 already records.

Exception code artifact_diagnostics_unavailable describes the diagnostic operation failure. Combined/request report Error.code is selected from owner state: legacy marker yields artifact_legacy_schema_unavailable with legacy guidance; ordinary diagnostic hold yields artifact_diagnostics_unavailable with the fixed diagnostic guidance. This is a report projection, not a different exception, and both unavailable cases map through existing transport to artifact_storage_unavailable503.

The facade's 'short authoring lock' is exactly one RLock acquisition for copying its ALREADY VALIDATED in-memory request/held/known flags and immutable dispatch ID, then release, with NO stat/open/parse/body IO. It does not call _check_index. A known held or uninitialized snapshot refuses non-null-request attachment; ordinary None bypass needs no authoring lock. This intentionally changes freshness of the diagnostic-only attachment observation: new external corruption/legacy replacement is discovered by normal authoring operations or restart, not by this snapshot. Service authority/claim/state decisions still perform their existing fresh validation and are never authorized by attachment data. Tests must patch index file IO to fail during the snapshot and assert no authoring IO, plus known-held refusal and sticky legacy cases.

### J6/J7: complete normative map and worker propagation

Single complete map: STORE-SCHEMA13/82/101/103/105/113/116/132; AUTHORITY82/83/84/117/126/183; LIFECYCLE-BACKUP140/156/316; OPERATOR-ROUTES331/377. AUTHORITY83 diagnostic-first-then-quarantined remains conditional on saved diagnostic success; inability to persist stops before that state transition. Earlier request-row, owner, imported-row and partial-report amendments apply at every listed site.

ArtifactDiagnosticsUnavailable inherits ArtifactUnavailable -> ChannelUnavailable -> RuntimeError. Existing artifact_worker broad catches remain unchanged. At229 _redeliver and248 CLI replay catch, it becomes hold/artifact_delivery_unconfirmed; at390 API prior-result replay catch it becomes held/artifact_delivery_unconfirmed; at408 API delivery/context catch it becomes held/artifact_context_unavailable; at428 invalid-response rejection catch it becomes held/artifact_delivery_unconfirmed rather than a successful quarantine; at445 save/redeliver catch it falls through to held/artifact_delivery_unconfirmed. None of these six sites propagates the raw exception. Transport HTTP503 follows the existing HTTPError branches, with no fabricated successful result/disposition. Required new worker-path test test_worker_invalid_response_with_held_diagnostics_returns_hold_without_fake_receipt in the new root file uses the real worker/reject_response seam and checks request remains live, no version/outbox result/false disposition or diagnostic ID.

Additional tests UNCHANGED BY DESIGN, confirm green: store_review110-133 authoring corruption observations; imported_store210-259; export_store36-48/85/99/105/132/188-194 (where any constructed request fixture still contains a removed key, apply only the already named exact-row fixture follow-up, never weaken the asserted authority outcome); store_integrity38-118; admission304-305; recovery229/266; import_benchmark (inherits store setUp). R2 preserves their behavioral assertions; shared setUp/index-version follow-ups are separately attributed. Direct diagnostic facade UUID calls remain mechanical delegates as specified above.

### J8: exact measured setup, retry observation and import isolation

Reachable heavy profile, per independent sample:1023 detailed rows over128 groups (127 groups x8 + final group x7). IDs are lowercase Hex32; request IDs deterministic per group, attempts/dispatch derived by request_ids, actor identity a*32, reason invalid_response, SHA64 computed from actual binary UTF8 bodies. Each body has an equal-length unique eight-ASCII-byte row prefix plus x padding so hashes/IDs are distinct. First1022 bodies are7680B each, last prior body15360B: total7864320B (7.5MiB). The measured new body is524288B with a unique eight-byte prefix; after its fsync/rename + metadata commit, count1024 and body bytes8388608 exactly. Body metadata byte_count/hash match actual files, not max-width placeholders. Use frozen positive23-character timestamp1.2345678901234567e-100 via existing now argument; all IDs/hashes use their exact widths, other counts use actual values. At least the final request is a real reserved local row for facade eligibility; seed prior metadata through the diagnostic owner with valid derived attachments/real matching source requests, not a fake authoring v1 frame. Setup is outside timing and explicitly records fixture seeding versus a naturally reached transaction history.

For the separate summary path, start from that full1024-detail/128-group result; a distinct9th key in the last now8-row group produces/updates its dispatch summary without a body. Each independent sample starts with a valid counter1 summary and measures the next distinct key/counter2 update; maximal-width counter/value cases belong to separately labeled structural graph reads/rewrites, never falsely called reachable max-field histories. Body files and hashes remain valid. Run at least10 independent heavy and10 independent summary samples, plus10 structural maximum-graph reads; measure service outer-boundary hold and concurrent require_active wait, full candidate validation/encoded cap/inventory, all actual body and metadata persistence. Every normal hold/wait<=0.270s. Report actual metadata bytes, all samples, max and margin. Heavy-path miss returns to design, not an adjustment or a summary-path substitution.

Identify retry faults with a HARNESS-ONLY Path.replace wrapper that calls the real method unchanged, counts only PermissionError raised for replacement into that sample's diagnostic JSON path, and re-raises so the real atomic_json retries/sleeps. No fsync, clock, replace result or wait is mocked. A sample may be labeled retry-fault/rerun ONLY if this counter>0; retain original elapsed result/counter and rerun attribution. Misses with retry_count0 remain normal misses even under system load. No generic 'diagnosed environment' resampling exception. The existing total0.315s retry sleep is FAULT, not removed from elapsed original samples.

Separate authoring import gate: exact4MiB/100-prior-lineage/128-request-version profile,10 samples with diagnostics FULL and10 with diagnostics HELD, default real atomic_json/fsync/parse/whole authoring validation, every hold<=0.300s. Construct owners/fixtures before measuring. Harness guards Path.open against any read of that root's diagnostics.json and patches diagnostic validation/read entry points to raise if invoked inside the measured authoring path; no diagnostic read or validation may pass unnoticed through a cached owner. Restore guards after each sample, no parallel diagnostic benchmark on that root. These guards verify isolation, not a production bypass.

### J9: closed independent diagnostic validation rules

1. Outer value is a dict with EXACT {version,diagnostics,dispatch_overflow,store_overflow}; version is plain int1; diagnostics and dispatch_overflow dicts; store_overflow dict or null. Encoded/read bound<=1048576B. Strict UTF8/no BOM, duplicate keys/nonfinite parse tokens refused; explicit post-parse depth walk as above. No arbitrary extra keys or lists.
2. At most1024 detailed entries, at most256 DISTINCT dispatch groups, at most8 detailed entries/group. Detail EXACT keys {id,kind,request_id,attempt_id,dispatch_id,reason,sha256,byte_count,actor_identity_id,received_at,updated_at,not_retained,body_object_id,attached_request_id}. kind literal quarantine, map key==row.id, both Hex32. request_id/actor_identity_id/attached_request_id are null or Hex32; attempt_id/dispatch_id Hex32; sha256 Hex64. Hex means exact lowercase [0-9a-f] width, no normalization.
3. byte_count plain int0..2**63-1; received_at positive bounded Number; updated_at EXACTLY equals received_at (with ordinary equality as current validator). not_retained is plain bool. body_object_id is null iff not_retained true, otherwise exactly row.id. No disk body read during validation; body corruption is a scoped object matter. Physical body quota/retainability is checked by record using inventory, not guessed from metadata hashes.
4. Reason is EXACT one of wrong_identity, wrong_attempt, wrong_dispatch, wrong_brief, wrong_scope, wrong_parent, cancelled, superseded, conflicting_duplicate, invalid_content, invalid_response, unmatched_saved_result, source_packet_unavailable, response_too_large. No free text exception/reason.
5. Detail ID is uuid5(NAMESPACE_URL, canonical_utf8(key).decode('utf-8')).hex where key EXACT {request_id,attempt_id,dispatch_id,reason,sha256,byte_count,actor_identity_id}; canonical_utf8 uses existing sorted compact JSON UTF8. attached_request_id is NOT in key. When non-null it equals row.request_id AND request_ids(attached_request_id)['dispatch_id']==row.dispatch_id. Null permits standalone/mismatched request evidence without attachment. Validate derivation without authoring reads.
6. Each dispatch_overflow key Hex32 names a group already present among detailed rows. Summary EXACT keys {id,kind,dispatch_id,counter,latest_diagnostic_id,latest_sha256,latest_byte_count,latest_reason,updated_at}. dispatch summary kind dispatch_overflow and dispatch_id==map key. Global summary kind store_overflow and dispatch_id null. Summary ID uuid5(NAMESPACE_URL,'agentchattr:artifact-v1:overflow:'+(dispatch_id or 'store')).hex. Row.id must match it. counter plain int1..2**31-1, latest_diagnostic_id Hex32, latest_sha256 Hex64, latest_byte_count plain int0..2**63-1, latest_reason closed quarantine reason above, updated_at positive bounded Number. At most one global summary. No reference from latest_diagnostic_id to a retained detail is required: overflow keys are intentionally not retained details.
7. Writer semantics stay8/256/1024,512KiB retained-body/8MiB physical-body/1024objects including orphans; invalidUTF8/NUL or absent content is hash/count-only. Detailed duplicate ID no-write/first attachment retained; only latest overflow key dedupes, older keys may increment to saturated counter. Store-level overflow remains unattributed. Full encoded candidate cap check is under diagnostic lock BEFORE any body put; no writer budget reduction is authorized.

The 810186B figure is VERIFIED ONLY for the stated rebuilt structural profile and its measured serialization. It is NOT yet verified as the escape/encoding maximum over every accepted diagnostic graph. The future maximum-row/file golden must independently enumerate closed reason/field/token widths and real accepted values, including ensure_ascii escaping effects, before claiming an upper bound. If that proof or actual timing fails, return to design, never silently change budgets/cap/normal gate.

J1-J9 exact freeze is now CLEARED at86dad152. Root owns one NEW behavioral test file, no helper yet. No R3/operator/capacity/activation/push.


## K1-K9 folded with first root reds

Reviewer exact payload freeze86dad152 is CLEARED at design scope. This section names the final mechanics and observed test evidence; it authorizes no production before independent red-body review. Existing production remains74f4697.

### K1/K2/K8: exact private interfaces and marker locking

| Method / attribute | Frozen responsibility |
| --- | --- |
| ArtifactStore.diagnostic_store | Independent owner on the same root. ArtifactStore still inherits _put_bytes, with per-instance patches preserved. |
| ArtifactStore._legacy_held; ArtifactDiagnosticStore._legacy_held | Sticky bool markers set at construction/recognized legacy authoring access; never cleared in-place. Ordinary corruption holds are distinct. |
| ArtifactStore._check_diagnostic_legacy() | Under AUTHORING RLock copy ONLY _legacy_held, release it, then call diagnostic_store._set_legacy_hold() if true. No file IO, no diagnostic lock while authoring lock held. record(None), request_diagnostics and combined report use this check before diagnostic entry. It does not call authoring _check_index. |
| ArtifactStore._snapshot_diagnostic_attachment(request_id,dispatch_id) | Under authoring RLock check cached known/held/legacy flags and copy eligible immutable request/dispatch only, no IO. After releasing, propagate any legacy marker. Known held/uninitialized AUTHORING raises existing ArtifactUnavailable with fixed authoring guidance, NOT ArtifactDiagnosticsUnavailable; legacy uses fixed legacy guidance. Healthy unknown/mismatched/imported request returns null attachment. |
| ArtifactDiagnosticStore._set_legacy_hold() | Under diagnostic RLock set sticky marker/held guidance only, no IO. Every record/request_diagnostics/report/_check_diagnostics checks that marker first. |
| ArtifactDiagnosticStore._attached_rows(request_id) | Under its own lock select detached rows by exact attached_request_id, order received_at/id ascending. No authoring lookup. |
| ArtifactDiagnosticStore.request_diagnostics(request_id) | Validate Hex32, own lock/check, use _attached_rows and matching dispatch summary only if at least one attached row. Return healthy four-field RequestDiagnostic projection; a held diagnostic owner RAISES ArtifactDiagnosticsUnavailable. |
| ArtifactDiagnosticStore.report() | Own lock/check, detached full diagnostic rows/summaries plus own orphan observations/inventory. Private unpaged snapshot EXACT {rows,dispatch_group_count,detailed_count,retained_body_bytes}. No authoring callback. Unavailable raises typed diagnostic error; facade projects per-owner status. |
| ArtifactDiagnosticStore._body_inventory() | Existing safe-path physical file count/byte inventory moved unchanged here; includes orphans. |
| ArtifactStore.request_diagnostics(request_id) | Validate Hex32 first; _check_diagnostic_legacy then delegate diagnostic owner and map a diagnostic hold to exact available:false/null fields/fixed Error. Invalid ID raises ArtifactValidationError, never unknown/empty or503. |
| ArtifactStore.diagnostics(*,limit=100) | Read authoring observations under its existing lock, release; propagate any discovered legacy marker before calling independent report. Merge detached known rows, sort/page/project owner errors as below. |

Only DIAGNOSTIC-owner or diagnostic IO failure raises ArtifactDiagnosticsUnavailable. A non-null request with known held/uninitialized authoring fails at the attachment snapshot with ArtifactUnavailable and authoring text. record(None) ALWAYS acquires the authoring RLock for the marker read only, even when ordinary authoring corruption is bypassed. It never takes that lock across diagnostic IO. No facade can reinterpret a known legacy marker as healthy-empty.

J8 isolation harness exact patch targets, active ONLY during the measured authoring path after fixture construction: Path.open read access for that root's diagnostics.json; ArtifactDiagnosticStore._load_diagnostics, _check_diagnostics, _validate_diagnostics, request_diagnostics, report and record all raise on call. Patch _persist_diagnostics too to catch an accidental write. Do not patch shared _put_bytes or clocks/fsync; restore all guards afterward. Owner construction/full or held fixture setup occurs BEFORE these guards. The public full/held4MiB authoring import gate remains mandatory.

### K3/K4/K5/K9: failure, paging, encoding and recovery

A body _put_bytes OSError/ArtifactUnavailable BEFORE entering atomic_json/post-write-stat is NOT a metadata uncertainty and does NOT hold the diagnostic owner. Return ArtifactDiagnosticsUnavailable without a receipt, leave the last known diagnostic metadata/stamp healthy, count any body left behind against physical quota, and report it as an orphan only when known metadata proves it unreferenced. Body lock timeout has the same no-metadata-uncertainty rule. An immutable body ArtifactConflict stays a conflict. A later valid diagnostic may succeed on the same owner. Only ANY atomic_json or immediate post-write fingerprint/stat exception invokes conservative commit uncertainty and its hold rule.

Combined diagnostics merges known owner rows by (-updated_at,id), the existing deterministic ordering. limit is a plain int1..100, validated even when held; no offset parameter is introduced. rows is ALWAYS a detached list of at most limit known rows. Healthy count is the full merged total BEFORE slicing; truncated reflects omitted known rows. If any owner makes the aggregate total unknown, count:null and partial:true/truncated:true even if known rows fit or rows=[]; known rows are still paged normally. Diagnostic-unavailable contributes no diagnostic rows and retained_body_bytes:null, while healthy authoring observations may remain. Invalid request_diagnostics id raises ArtifactValidationError before owner-health projection.

Metadata atomic_json encoding is EXACT json.dump(...,ensure_ascii=True,allow_nan=False), default separators (', ', ': '), sort_keys=False (insertion order), indent=None, UTF8 file, no added trailing newline. Canonical UUID input remains separately compact/sorted UTF8 as specified in J9. The23-char finite float token is asserted by test_r1_numeric_token_guard_and_atomic_json_encoding_match, not inferred from prose; that compatibility guard also pins insertion order, escaped Unicode and actual metadata bytes.

One recovery rule: sticky LEGACY holds never clear on the same instance. An ordinary uncertain diagnostic hold may clear on that instance ONLY after a stable strict reread equals its previously known snapshot (the sentinel forces a verification attempt). If a different ledger actually landed, that stale instance remains held; only application restart constructs the fresh owner that may adopt it. Thus 'fresh restart only' refers to adoption of a DIFFERENT landed snapshot, not recovery to the SAME known snapshot. No runtime reconstruction/auto retry is added.

### K6: single enumerated root test inventory and observed labels

The following is the INITIAL first-pin inventory; the expanded Z receipt below supersedes its pending status and locations (worker integration moved to the explicitly authorized second root file). B = behavioral red against the existing facade/schema; I = missing owner/read API infrastructure, not proof the later assertions fail behaviorally; G = existing compatibility guard, not a new red. PENDING bodies remain required before green acceptance; they are not counted as executed evidence.

| # | Test name | First-pin status |
| --- | --- | --- |
|1|test_diagnostic_only_write_does_not_create_authoring_index|B: actual old writer creates index.|
|2|test_diagnostic_detail_and_overflow_do_not_change_authoring_index_bytes|B: nine actual detail/summary index rewrites, plus missing independent file assertion.|
|3|test_diagnostic_corruption_does_not_block_authoring_or_version_admission|B: corrupt diagnostic file ignored, submission does not refuse. Post-refusal valid admission is UNOBSERVED-RED until green.|
|4|test_cap_depth_bom_duplicate_and_invalid_ledgers_refuse_before_body_put|B: seven malformed-file cases ignored. Does not isolate each parser mechanism yet; early directory ignorance is the behavioral failure. Cap uses otherwise valid JSON with leading whitespace.|
|5|test_request_diagnostics_is_detached_ordered_and_independent_of_authoring_health|I: missing request_diagnostics after real source/diagnostics setup.|
|6|test_standalone_diagnostic_bypasses_ordinary_held_authoring|B ERROR: actual old ArtifactUnavailable from authoring blocks legitimate standalone persistence, not a fixture/import error.|
|7|test_legacy_nonempty_holds_both_owners_without_creating_diagnostics|B: old reader accepts v1 and records more diagnostics; two missing refusals and changed legacy bytes.|
|8|test_body_put_error_does_not_hold_diagnostic_owner_or_invent_commit_uncertainty|I: missing diagnostic_store; no fault semantics claimed yet.|
|9|test_uncertain_metadata_commit_holds_stale_instance_and_restart_recognizes_landed_row|I: missing owner; later real atomic_json-after-replace fault unobserved until green.|
|10|test_stale_diagnostic_owner_cannot_overwrite_another_owner|I: missing owner, no stale-diagnostic proof yet.|
|11|test_existing_8_256_1024_budgets_move_without_lowering_or_widening|I: missing owner; seeded legal graph + real overflow checks must run green.|
|12|test_event_blocked_diagnostic_io_does_not_block_low_level_authoring_settlement|I: missing owner; no Event concurrency claim yet.|
|13|test_request_diagnostics_invalid_id_is_validation_error_not_unknown_request|I: missing API; invalid-ID subtests unobserved until green.|
|14|test_authoring_validation_and_persistence_never_read_diagnostics|B: authoring index still includes three diagnostic keys; subsequent guarded authoring mutation unobserved until green.|
|15|test_r1_numeric_token_guard_and_atomic_json_encoding_match|G: actual writer encoding and23-char positive Number pass unchanged.|
|16|test_authoring_put_bytes_override_still_controls_import_staging|PENDING G/behavioral companion to named existing patch-survival tests.|
|17|test_owner_fingerprints_use_separate_paths|PENDING I then independent-path behavior.|
|18|test_unattached_details_and_summary_are_not_retroactively_attributed|PENDING I then first-attachment/overflow semantics.|
|19|test_global_overflow_is_never_attributed_to_a_request|PENDING I plus existing summary compatibility guard.|
|20|test_legacy_markers_preserve_guidance_across_constructor_check_and_persist|PENDING B/I, sticky restore-original-bytes and no diagnostic file.|
|21|test_same_instance_uncertainty_recovers_only_the_previous_known_snapshot|PENDING I, complement different-landed-ledger restart test.|
|22|test_combined_report_partial_rows_limits_and_owner_errors_are_exact|PENDING I, include ordinary held authoring plus healthy diagnostic read, invalid limit and null counts.|
|23|test_snapshot_and_none_marker_read_do_no_authoring_io_or_nested_owner_lock|PENDING B/I; cached snapshot flag behavior and no-overlap guard.|
|24|test_worker_cli_saved_redelivery_diag_failure_holds|PENDING real-worker229 path.|
|25|test_worker_api_saved_redelivery_diag_failure_holds|PENDING real-worker229 API replay path.|
|26|test_worker_delivery_with_held_diagnostics_is_context_unavailable|PENDING real-worker408 path.|
|27|test_worker_invalid_response_with_held_diagnostics_returns_hold_without_fake_receipt|PENDING real-worker428 path.|
|28|test_worker_postsave_redelivery_diag_failure_holds_without_disposition|PENDING held outcome through229 after save; no fake terminal disposition.|

The six catch sites are not six independent natural diagnostic-failure sites. Real submit_saved diagnostic failures are caught INSIDE _redeliver at229. They cannot escape that helper to248 or390;387-389 already handles its returned decision. The post-save helper at445 likewise normally receives a hold decision after229, rather than a raw new diagnostic exception. No artificial rethrow is counted as real coverage of those outer catches. Existing replay guards keep them unchanged; named CLI/API/post-save tests exercise their observable held outcomes. Delivery408 and reject-response428 have distinct real diagnostic failure seams. Any additional source-trace discovery is reported rather than invented coverage.

Executed first root run (unchanged source):14 tests22FAIL+9ERROR0.383s. One diagnostic-file FileNotFoundError was a secondary missing-file observation after subtest failures, not fixture corruption. It was replaced with an explicit missing-file assertion for a clearer receipt. Final observed run:15 tests23FAIL+8ERROR0.388s, ONE existing guard passes. Failures are23 behavioral assertions; errors are7 missing-API infrastructure and1 genuine standalone-authoring behavioral refusal. No errors are import/setup/cleanup failures. All owned fixture roots cleaned. New expected-refusal follow-on body/index/admission invariants and infrastructure-gated bodies remain UNOBSERVED-RED, required green checks, not counted as proven behavior.

### K6/K7: measurement and fixture scope

tools/measure_artifact_diagnostics.py is a separate root-owned MEASUREMENT harness, never a unittest red. It seeds ALL128 groups with actual reserved authoring requests and derived attempt/dispatch IDs. Bodies for all1023 prior records match their declared hashes/counts; fixture seeding is explicit, not a natural transaction-history claim. Its heavy and summary profiles follow J8 exactly. Actual timing requires R2 owner implementation and is NOT RUN on this pin. Only --check-plan arithmetic and py_compile ran; those are not performance evidence. The structural-profile read and guarded4MiB full/held import gates remain separately required; this initial tool implements reachable heavy/summary profiles only. No pass based on the earlier narrow prototype can replace them.

Fixture label resolution: export_store36-48/132 contains the imported construction/attachment cases already named for rewriting at40/142; these EXACT fixture/debug-key adaptations are REWRITE, their other authority/immutability assertions UNCHANGED BY DESIGN. export_store85/99/105/188-194 stay unchanged. No claim that removed request keys load unchanged. Factory test_artifact_factory.py20/64/67 gains checks that an absent diagnostics.json is not created during healthy/broken-index construction/recovery, and that a pre-existing diagnostic file is never reset when authoring is broken; existing root/authority/order assertions remain. Factory binding uses independent ordinary-corruption semantics, not a fabricated legacy marker.

Production stays behind independent first-red-body review. No helper has been assigned; no R3/operator/capacity/activation/push. Hard timing gate remains unchanged and unmeasured heavy profile is not called passing.


## Z1-Z8 expanded root reds, production still held

Reviewer personally reran3192f1e:15 tests23FAIL+8ERROR0.43s, counts confirmed; source unchanged and analyst bodies traced. Production was NOT cleared. This addition round uses TWO ROOT-owned test files, as expressly allowed in Z7: test_artifact_diagnostic_owner.py (30 methods) and test_artifact_diagnostic_integration.py (10 methods). No helper is assigned; no existing helper, fixture or production source was edited.

### Exact additions and frozen private seams

- Z1 retains stale-file behavioral cases and adds cold diagnostic owner construction with BOTH hold_unreadable=False and True after malformed bytes exist. Missing ArtifactDiagnosticStore is INFRASTRUCTURE until implementation; no cold-parser behavior is claimed from those errors.
- Z2 writer overflow now isolates1024 records with128 groups x8 and a new129th group, below256. Direct cold-load refusal cases isolate ninth detail in one group,257 groups x1, and1025 records over129 groups with max8/group. Body tests isolate512KiB/512KiB+1,8MiB using16 large bodies (far below1024objects), and1024objects using zero-byte orphan bodies (far below byte cap). These tests are API-gated and must run in green; no budget coverage claimed merely from AttributeError.
- Z3 diagnostic refusal helper asserts BOTH ArtifactUnavailable parent family and the required ArtifactDiagnosticsUnavailable subclass, .code and exact fixed text after the refusal occurs. Authoring-only legacy/non-null-held guards assert exact base ArtifactUnavailable class and authoring text. Old missing refusal remains behavioral; subtype follow-on checks are unobserved-red until that refusal exists.
- Z4 retain and freeze private diagnostic attributes _stamp:(mtime_ns,size)|None, _invalid_stamp:tuple|fresh object sentinel, _held:str|None, _legacy_held:bool. These are per-instance RAM only, never serialized. _persist_diagnostics(self,value)->None accepts the complete diagnostic-v1 frame and owns/re-enters its RLock, validates cap/schema then does the process-lock/atomic metadata write as frozen. _validate_diagnostics(self,value)->None is the pure full diagnostic-frame validator. Tests may seed through the single-value private persist seam; this is a fixture API, not an exposed tool/route or a new bypass.
- Z5 attachment ordering includes equal timestamps and compares the tied IDs in lexical order, then the later row. Detached result mutation must not change the next read.
- Z6 real diagnostic metadata is created BEFORE the authoring guard. Path.open and all J8/K8 owner read/validation/persistence targets raise on any access during authoring validation/state write. The old seven-key schema assertion currently blocks this body: the guarded path is explicitly unobserved-red, not claimed exercised.
- Z7 all formerly pending K6 items have bodies; new factory, transport/MCP, archive/export, imported standalone, same-ID concurrency, empty/mixed-v1 and structural profile tests are included. Factory uses the real configure fixture with existing process/thread doubles, asserts absent diagnostic file stays absent and pre-existing diagnostic bytes stay unchanged, while also checking same-root owner binding. Its owner lookup is currently infrastructure-gated.
- Z8 per-test reached/unobserved conditions are in the table below. Future green acceptance MUST execute those bodies, not merely replace their old failure with a new unrelated exception.

The structural frame is built from independent literal rows/closed maxima and fixed derived IDs:1024 details,256 groups/summaries and global summary, attached-request derivation, max19-digit byte counts/10-digit counters/23-char positive floats. Literal size810186B and SHA256 ca2cead533284a9c9165be1f5912e57f994a1a6cec9d4645e21beed290db34c1 are pinned. These serialization/count guards ran on old code before the missing R2 class lookup. Full R2 validator/persistence is UNOBSERVED-RED; this is still a stated structural profile, not a naturally reached history or independent all-encoding-max acceptance.

Replay correction: two initial worker tests passed old code's held outcome because a nonterminal saved diagnostic already produces a hold without terminal disposition. That outcome alone was insufficient. Both now assert the real submit callback runs exactly once AND authoring bytes remain unchanged. They now fail behaviorally on the old diagnostic index write. No artificial worker exception or false branch-coverage claim. The HTTP error literal was corrected before the final pin to the existing wire text 'Artifact storage is unavailable. Work is retained.'; the old200 fails before that wire assertion, so its green text remains unobserved-red.

Intermediate receipts retained: store-only28 tests27FAIL+18ERROR0.651s; initial integration10 tests6FAIL+2ERROR3.455s (two insufficient replay guards passed); strengthened39 tests35FAIL+21ERROR3.238s. FINAL unchanged-source combined run40 tests35FAIL+21ERROR3.374s. Errors are18 missing-API AttributeErrors +1 missing owners-projection KeyError (19 INFRASTRUCTURE), and2 genuine authoring-held ArtifactUnavailable errors (standalone None and combined report).35 assertion failures are behavioral, not setup/import errors. Three existing guards PASS: encoding/float token, authoring _put_bytes override on actual import staging, and held-authoring non-null request's exact authoring exception/no diagnostic write. All fixture roots cleaned; retained deprecation warnings from current app/TestClient imports are not claimed clean. No timing or full discovery was run.

|#|Test|Observed classification|Unobserved-red condition / reached guard|
|---|---|---|---|
|1|test_artifact_diagnostic_owner.py::test_diagnostic_only_write_does_not_create_authoring_index|B FAIL|Authoring index must remain absent; then independent metadata/attachment/body byte assertions run.|
|2|test_artifact_diagnostic_owner.py::test_diagnostic_detail_and_overflow_do_not_change_authoring_index_bytes|B FAIL|Each of nine saved writes must preserve authoring bytes and row; independent file/8 detail/summary counter checks then run.|
|3|test_artifact_diagnostic_owner.py::test_diagnostic_corruption_does_not_block_authoring_or_version_admission|B FAIL|Typed diagnostic refusal must occur; then unchanged index, healthy commit_version and per-owner report assertions run.|
|4|test_artifact_diagnostic_owner.py::test_cap_depth_bom_duplicate_and_invalid_ledgers_refuse_before_body_put|B FAIL|Each malformed file must refuse before body; preserving bytes/no bodies/no index follows. Separate cold-owner test eliminates changed-file-only false positives.|
|5|test_artifact_diagnostic_owner.py::test_request_diagnostics_is_detached_ordered_and_independent_of_authoring_health|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'request_diagnostics'. Remaining behavior assertions are unobserved until that lookup succeeds.|
|6|test_artifact_diagnostic_owner.py::test_standalone_diagnostic_bypasses_ordinary_held_authoring|B ERROR|Standalone None write must succeed despite authoring hold; new diagnostic file and unchanged authoring bytes checks then run.|
|7|test_artifact_diagnostic_owner.py::test_legacy_nonempty_holds_both_owners_without_creating_diagnostics|B FAIL|Both missing refusal subtests and byte-preservation assertion must pass before absent new-file proof.|
|8|test_artifact_diagnostic_owner.py::test_body_put_error_does_not_hold_diagnostic_owner_or_invent_commit_uncertainty|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|9|test_artifact_diagnostic_owner.py::test_uncertain_metadata_commit_holds_stale_instance_and_restart_recognizes_landed_row|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|10|test_artifact_diagnostic_owner.py::test_stale_diagnostic_owner_cannot_overwrite_another_owner|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|11|test_artifact_diagnostic_owner.py::test_existing_8_256_1024_budgets_move_without_lowering_or_widening|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|12|test_artifact_diagnostic_owner.py::test_event_blocked_diagnostic_io_does_not_block_low_level_authoring_settlement|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|13|test_artifact_diagnostic_owner.py::test_request_diagnostics_invalid_id_is_validation_error_not_unknown_request|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'request_diagnostics'. Remaining behavior assertions are unobserved until that lookup succeeds.|
|14|test_artifact_diagnostic_owner.py::test_authoring_validation_and_persistence_never_read_diagnostics|B FAIL|Four-key v2 authoring frame must pass first; then existing diagnostic file + Path.open + all named owner-method guards exercise actual state persistence.|
|15|test_artifact_diagnostic_owner.py::test_r1_numeric_token_guard_and_atomic_json_encoding_match|G PASS|All current guard assertions reached and passed; no new behavior proof claimed.|
|16|test_artifact_diagnostic_owner.py::test_cold_and_stale_diagnostic_parsers_reject_cap_depth_bom_duplicate|I ERROR|Required API/schema must exist: module 'artifact_store' has no attribute 'ArtifactDiagnosticStore'. Remaining behavior assertions are unobserved until that lookup succeeds.|
|17|test_artifact_diagnostic_owner.py::test_record_group_and_global_limits_are_individually_validated_on_cold_load|I ERROR|Required API/schema must exist: module 'artifact_store' has no attribute 'ArtifactDiagnosticStore'. Remaining behavior assertions are unobserved until that lookup succeeds.|
|18|test_artifact_diagnostic_owner.py::test_body_object_total_bytes_and_object_count_limits_are_isolated|I ERROR|Required API/schema must exist: module 'artifact_store' has no attribute 'ArtifactDiagnosticStore'. Remaining behavior assertions are unobserved until that lookup succeeds.|
|19|test_artifact_diagnostic_owner.py::test_authoring_put_bytes_override_still_controls_import_staging|G PASS|All current guard assertions reached and passed; no new behavior proof claimed.|
|20|test_artifact_diagnostic_owner.py::test_owner_fingerprints_use_separate_paths|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|21|test_artifact_diagnostic_owner.py::test_unattached_details_and_summary_are_not_retroactively_attributed|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'request_diagnostics'. Remaining behavior assertions are unobserved until that lookup succeeds.|
|22|test_artifact_diagnostic_owner.py::test_global_overflow_is_never_attributed_to_a_request|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|23|test_artifact_diagnostic_owner.py::test_legacy_markers_preserve_guidance_across_constructor_check_and_persist|B FAIL|Legacy refusal/guidance must pass; then restoring old bytes must not clear marker and diagnostic None must refuse with no new file.|
|24|test_artifact_diagnostic_owner.py::test_empty_v1_normalizes_in_memory_but_mixed_v2_is_held_without_reset|B FAIL|Empty-v1 RAM frame must become v2; then unchanged old file/absent diagnostics postconditions run. Mixed-v2 refusal is an existing guard reached separately.|
|25|test_artifact_diagnostic_owner.py::test_same_instance_uncertainty_recovers_only_the_previous_known_snapshot|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|26|test_artifact_diagnostic_owner.py::test_combined_report_partial_rows_limits_and_owner_errors_are_exact|B ERROR|diagnostics() must return a partial report despite held authoring; owner map/null totals/known rows/limits/both-held assertions then run.|
|27|test_artifact_diagnostic_owner.py::test_snapshot_and_none_marker_read_do_no_authoring_io_or_nested_owner_lock|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|28|test_artifact_diagnostic_owner.py::test_concurrent_same_diagnostic_id_has_one_body_row_and_stable_receipt|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|29|test_artifact_diagnostic_owner.py::test_structural_maximum_frame_golden_validates_attached_derivation_and_encoding|I ERROR|Required API/schema must exist: module 'artifact_store' has no attribute 'ArtifactDiagnosticStore'. Remaining behavior assertions are unobserved until that lookup succeeds. The literal810186B/profile SHA/count/23-char guards before lookup DID pass.|
|30|test_artifact_diagnostic_owner.py::test_nonnull_request_held_authoring_is_authoring_error_without_diagnostic_write|G PASS|All current guard assertions reached and passed; no new behavior proof claimed.|
|31|test_artifact_diagnostic_integration.py::test_worker_cli_saved_redelivery_diag_failure_holds|B FAIL|Real submit count1 and held outcome already pass; unchanged authoring bytes must pass before ACK/disposition/state/version checks.|
|32|test_artifact_diagnostic_integration.py::test_worker_api_saved_redelivery_diag_failure_holds|B FAIL|Real submit count1 and held outcome already pass; unchanged authoring bytes must pass before ACK/disposition/state/version checks.|
|33|test_artifact_diagnostic_integration.py::test_worker_delivery_with_held_diagnostics_is_context_unavailable|B FAIL|Held context outcome already passes; request must stay active rather than old failed before no-result assertion.|
|34|test_artifact_diagnostic_integration.py::test_worker_invalid_response_with_held_diagnostics_returns_hold_without_fake_receipt|B FAIL|Worker must return held instead of old quarantined; then live request/no result/disposition/ID assertions run.|
|35|test_artifact_diagnostic_integration.py::test_worker_postsave_redelivery_diag_failure_holds_without_disposition|B FAIL|Saved outbox/held/no ACK/disposition checks reached; request must remain active rather than failed before zero versions check.|
|36|test_artifact_diagnostic_integration.py::test_actual_agent_transport_projects_held_diagnostic_503_without_receipt|B FAIL|HTTP503 must replace old200; exact fixed error body/no-store/live-state checks follow.|
|37|test_artifact_diagnostic_integration.py::test_actual_mcp_submit_projects_held_diagnostic_503_without_receipt|B FAIL|artifact_storage_unavailable must replace invalid_content; fixed status/no ID/live-state checks follow.|
|38|test_artifact_diagnostic_integration.py::test_real_factory_does_not_create_or_reset_diagnostics_when_authoring_is_broken|I ERROR|Required API/schema must exist: 'ArtifactStore' object has no attribute 'diagnostic_store'. Did you mean: 'diagnostics'?. Remaining behavior assertions are unobserved until that lookup succeeds.|
|39|test_artifact_diagnostic_integration.py::test_export_and_import_ignore_corrupt_diagnostics_without_resetting_them|I ERROR|Required API/schema must exist: 'owners'. Remaining behavior assertions are unobserved until that lookup succeeds. Real export/import, object comparison and corrupt-file byte preservation DID pass before owners projection lookup.|
|40|test_artifact_diagnostic_integration.py::test_imported_standalone_diagnostic_changes_no_authoring_bytes_or_imported_rows|B FAIL|Authoring bytes must remain unchanged; then same imported row, empty request diagnostic projection and null attachment checks run.|


Static verification: both files compile, strictUTF8/AST30+10 methods/no BOM, git diff --check; tracked production files unchanged vs74f4697. Measurement harness remains separate and unchanged, with no new timing run. Review this expanded red pin BEFORE R2 production. Thin prototype margin does not waive the real heavy/summary/structural/read/import gates. R3/operator/capacity/activation/push remain held.
