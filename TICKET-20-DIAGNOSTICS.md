# Ticket 20 R2: independent diagnostic ownership, proposed contract

Status: PROPOSED, docs only. Seth approved R1-R3 scope; R1 is independently CLEARED at bd1f3922 (product 74f4697). This proposal needs review before R2 tests, helper work or code. R3 source-reference compaction remains a separate contract. Production capability stays empty; no authoring quota, public route, activation, deployment or purge is added.

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

Proposed ArtifactDiagnosticStore(data_dir, *, hold_unreadable=False) lives in artifact_store.py, with its own path, RLock, fingerprint/held state and independent writer. ArtifactStore constructs diagnostic_store for the same root with hold_unreadable=True, regardless of the authoring owner's hold flag. Missing files are healthy-empty and construction writes nothing. app/run keep constructing ONE ArtifactStore and the same ArtifactService; a factory test proves its diagnostic owner uses that exact root. No standalone model tool or new route exposes the owner.

| Interface | Proposed behavior |
| --- | --- |
| ArtifactStore.quarantine_submission(existing signature) | Facade retained. Validate inputs. For request_id=None, bypass authoring health entirely and call diagnostic_store.record with attached_request_id=None. Otherwise snapshot attachment eligibility under the short authoring lock, release it, then call record; failed authoring snapshot refuses rather than guessing. No authoring persistence or request-state mutation. |
| ArtifactDiagnosticStore.record(request_id,attempt_id,dispatch_id,*,reason,content=None,actor_identity_id=None,attached_request_id=None,now=None) | Own-lock transaction; returns existing Detail/Summary shape with attachment field only on Detail. No channel/authoring lookup, provider or callback. |
| ArtifactStore.get_request / get_request_by_dispatch and mutator returns | Detached authoring-v2 row only, no automatic diagnostic enrichment or overflow lookup. Existing metadata/signatures retained; the two debug fields intentionally move. ArtifactService's private mutation projection follows that narrower row. Current agent ACK/QuarantineResult/public transport shapes are unchanged. Future operator DTO allowlists stay unchanged; amend its private ExistingRequestRow definition after R2 is accepted. |
| ArtifactStore.request_diagnostics(request_id) | Explicit detached {available,quarantine_ids,overflow_count,error}, or null for healthy unknown request. Snapshot authoring row, release its lock, then read the diagnostic owner. Healthy attached IDs ordered received_at/id ascending, an intentional change from stored append order; overflow is the matching dispatch summary as before. Imported rows have exactly []/0 without attachment lookup, since they can never attach; standalone diagnostics can still exist globally. |
| ArtifactStore.diagnostics(*,limit=100) | Assemble independent authoring object/orphan observations and diagnostic report after separate snapshots. Healthy old fields rows/count/truncated/dispatch_group_count/detailed_count/retained_body_bytes retained, plus authoring_available,diagnostics_available,partial,errors. No owner lock is nested. |

Attachment snapshot rule is the existing one: request exists, is LOCAL (any state except imported), and its immutable deterministic dispatch matches the supplied dispatch. Attempt mismatch is still diagnostic data, not a state transition or attachment authority. Otherwise attached_request_id is null. A repeated diagnostic ID retains its FIRST attachment decision, even if a matching request is reserved later. Never infer attachment later merely because a previously unmatched request_id now exists. Imported requests never gain attachments. Rename/cancel cannot change local eligibility or immutable IDs; imports never replace a local UID, so the detached decision is safe without holding an authoring lock through file IO.

When the diagnostic owner is held, request_diagnostics for a LOCAL row returns available:false, null IDs/count and a fixed error. The imported-row []/0 invariant above is knowable without a diagnostic read and remains exact; it does not claim the global diagnostic owner is healthy. Authoring rows remain readable and unchanged. For the combined diagnostics report, unavailable totals are null, partial/truncated are true and errors names the unavailable owner; never invent zero. If authoring is healthy, its packet/version orphan and corruption observations can still be shown. If authoring is held, do not guess packet/version references or classify those bodies as orphans. If diagnostic metadata is held, do not classify quarantine bodies as orphans because references are unknown. General inventory observations are read-only snapshots, never deletion/recovery authorization; exact invocation staging receipts retain their existing lock-bound orphan calculation.

Proposed ArtifactDiagnosticsUnavailable subclasses ArtifactUnavailable, with fixed internal code artifact_diagnostics_unavailable and text 'Artifact diagnostics are unavailable. Repair the diagnostic metadata before retrying.' No exception message/path/body is interpolated. Existing artifact_transport.failure catches this ArtifactUnavailable subclass and projects EXACT HTTP 503 code artifact_storage_unavailable, with no new successful QuarantineResult shape. The new combined diagnostic errors map uses fixed codes/text only. Shared filesystem/root failures may hold both owners normally.

## Atomicity and locking

Ordinary authoring remains engine/catalog boundary -> authoring lock -> index process lock; it never acquires the diagnostic lock. Diagnostic facade takes authoring lock ONLY for metadata/attachment snapshot and releases it before diagnostic lock -> diagnostic process lock -> per-body process lock. The diagnostic owner never calls back into authoring or channel policy. No authoring+diagnostic lock overlap, reverse lock edge or cross-file transaction.

Within a diagnostic transaction, recheck the diagnostic fingerprint under its own process lock, enforce budgets from the real body inventory, construct and validate the complete candidate, and check its actual encoded size UNDER the diagnostic lock BEFORE any body put or JSON replace. Over-cap refuses as ArtifactDiagnosticsUnavailable (internal artifact_diagnostics_unavailable; transport503 artifact_storage_unavailable), creates no body and therefore no new orphan. Then put body first, then existing atomic_json metadata write (exclusive temporary file, flush/fsync, atomic replace). Update memory only on confirmed metadata commit. On IO/lock/uncertain-commit failure, return no diagnostic receipt. Before replacement, prior metadata remains; after an uncertain replacement, preserve whichever complete version landed and hold that diagnostic owner until verified reload, never reset or overwrite the uncertain outcome. Any staged body still counts against the physical quota; call it an orphan only when healthy metadata proves it unreferenced, otherwise report unknown rather than invent zero. Never delete it. A fresh owner can recognize a confirmed landed duplicate; a stale owner fails closed rather than overwriting external changes. Same-owner concurrent writes serialize; separate stale owners cannot silently lose records. Body conflicts remain scoped ArtifactConflict as today.

Existing ArtifactService engine/catalog scopes are NOT silently released or reordered by R2. A service diagnostic call can still run under its existing outer boundary; only authoring/diagnostic owner locks are separated. R2 does not promise a service call bypasses that engine serialization or arbitrary filesystem failure latency. Required Event tests prove low-level authoring settlement does not wait for a diagnostic owner lock/IO. Normal diagnostic service hold/wait timings must pass the gate below; if they require a new authority phase split, return for design review instead of adding a background journal, dropping durability or weakening a timing gate.

## Failure, authority and recovery semantics

Valid prepare/admit/version reads, import/export, metadata counts and cancel/Stop do not require diagnostics. Corrupt diagnostics must not set authored artifacts_held, pause channel creation/reopen/rename/delete, break valid version admission or change the immutable parent/head. Packet/Markdown corruption stays scoped as before.

Diagnostic-required paths are an explicit exception: _diagnostic, invalid-response reject_response, bad packet reporting, unmatched/terminal saved-result recording and their recovery branches must return a real durable diagnostic ID before claiming successful quarantine. If diagnostics cannot persist, propagate the typed unavailable error using the existing 503/held path; no fake ID, ACK, disposition, terminal proof or model retry. Existing preceding activation or subsequent state/fence operations keep their current order. This can leave the current request active until cancel/Stop or the existing empty-delivery settlement; it is not a successful quarantined response. A healthy peer's authoring/recovery still proceeds; per-dispatch recovery failures stay reported held/operator_recovery_required, never abort all startup work. No new outbox, queue operation or generation journal.

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
| request_id=None, held authoring but healthy diagnostics | Standalone diagnostic persists through the facade without any authoring snapshot, read or write. Non-null request IDs still require a healthy attachment snapshot. |
| Nonempty legacy-v1 authoring hold | Facade stores a private legacy-schema hold marker at load. request_diagnostics and combined diagnostics report that unavailable legacy diagnostic source even if the new file is absent; they must not return healthy-empty. The independent new owner does not inspect the old index. This does not block unrelated standalone record(None) into a healthy new diagnostic owner. |
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
