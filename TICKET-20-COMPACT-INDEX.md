# Ticket 20 R3: compact source provenance in the authoring index

Status: PROPOSED contract for independent review, DOCS ONLY. No R3 reds, source, fixture migration, timing run or new quota is authorized by this draft. Base is FINAL ACCEPTED R2+D4 product220f340042056b80c09091807690af74f36dafec, closed A1 base2c34bbfb. The accepted unit is publishable on codex/ticket-20-r2-on-a1; push and activation remain held. Older codex/ticket-20-artifacts product WIP67e9e05 is superseded and preserved. Seth approved R1-R3 scope in [the storage decision](TICKET-20-STORE-DECISION.md).

## Outcome and review decisions

Remove full source-ref arrays from BOTH request audit scopes and version provenance scopes in the authoring index. Keep exact source message identity, order and per-message hashes in immutable packet and scope/provenance objects. Index validation and writes must not load those arrays. Ordinary metadata-only cancellation, startup inventory, lifecycle summaries and diagnostic attachment must not acquire a dependency on a healthy packet or scope sidecar.

The following are recommendations for this review, not settled implementation decisions:

|Decision|Recommended contract|Reason / alternative|
|---|---|---|
|Local schema|Authoring index3; diagnostic metadata1 unchanged|Schema2 cannot silently reinterpret the exact scope key set. Portable archive schema2 / artifact section1 remain separate.|
|Ref storage|One immutable full-scope JSON sidecar per packet/request, also referenced by its version|Packet messages already contain the source; current version object is Markdown only. A scope sidecar retains version provenance without rewriting Markdown or requiring a source packet read to inspect a version. Alternative: packet-only reconstruction, which makes historical provenance depend on packet health and repeats content walks.|
|RAM form|Compact authoritative _data; hydrate only explicit full projections|Inflating every scope in RAM would restore the same persist/validation/deepcopy cost. No hidden expanded owner cache.|
|Read compatibility|Existing full getters retain their full scope shape; service/state paths use an explicit compact-record API|Keeping all service calls on the full getter would add a sidecar read to every A/C request lookup and defeat the reduction.|
|Development compatibility|No automatic nonempty schema2 conversion. Explicit offline, validated, non-destructive conversion in the reviewed R3 package|Avoid silent rewrite during constructor or under the shared boundary. Empty valid old frames can upgrade in memory without creating files.|

Review must choose these before reds and freeze exact helper signatures, error strings, conversion command and test patch adaptations in a separate payload table. This proposal authorizes neither a helper to invent them nor production changes while review is pending.

## Current source and why both copies matter

In accepted artifact_store.py, _packet_scope computes ordered message_refs from canonical message bytes. _audit validates all refs; _reserve_new retains the full audit. _commit_new duplicates audit.scope into version.provenance.scope. _validate_index canonicalizes the whole frame and walks requests and versions on every _persist. _validate_version checks full scope equality against its request. A1 removes repeated packet content validation, not those index walks or rewrites.

The independent schema2 diagnostic owner and D4 A/B/C driver are accepted. R3 must preserve them, including the fresh startup warning projection introduced by Q1. DA-2 of specificationv1.7 still requires source message IDs, producing agent/model, run and input provenance, retained versions and exact Markdown downloads. R3 changes storage representation, not that scope.

Current public/local compatibility surfaces: get_request/get_request_by_dispatch return full audits; get_packet returns the packet; get_version returns full metadata+Markdown; list_versions returns full version rows; export_metadata supplies full snapshots to artifact_archive.portable_lineage. Internal metadata-only summaries are already separate: pending, list_lineages, lifecycle_scope and retained_metadata. A full-scope field cannot be removed from one of these existing full projections silently.

## Exact proposed scope shapes

Full scope remains EXACT:

    {kind, packet_id, sha256, byte_length, message_refs, input_revision}

Every ref remains EXACT {id, uid, sha256}, in original order. Existing R1 ref id/UID/digest grammar, uniqueness, zero/1000-ref boundaries and input revision rules remain. Empty refs are valid where valid today. Neither sorting refs nor normalizing strings is allowed.

Compact scope is EXACT:

    {kind, packet_id, sha256, byte_length,
     message_refs_sha256, message_count, input_revision}

- sha256 and byte_length still describe the EXACT canonical packet bytes, not the sidecar.
- message_refs_sha256 is SHA256(canonical_utf8(full_scope.message_refs)). Use the existing sealed_result_io.canonical_utf8 (UTF8, ensure_ascii=False, sorted object keys, compact separators, no NaN). Array order is significant. The empty list has its actual digest, never null or an invented sentinel.
- message_count is exact int, not bool,0..1000. Digest is exactly64 lowercase hex. kind, packet_id, packet hash/length, input_revision retain their existing grammar and identity checks.
- No full array, alternate spelling, optional extension or mixed schema is accepted in a schema3 compact scope. Request and version must have identical compact scope values just as their full scopes match today.
- Local audit version1/purpose artifact-v1, worker packets, queue/brief fields and sealed result payloads do not change. The existing _audit grammar remains a FULL-audit grammar at request construction/import/portable boundaries; a separate compact-audit validator handles schema3 records. Do not make one permissive union validator whose accepted fields depend on guesses.

## Immutable full-scope object and publication order

Recommended local owned path: artifacts/scopes/<packet_id>.json, one per request packet. Its bytes are canonical_utf8(full_scope), with no local channel, mutable state, observation or timestamp added. It is also the immutable version provenance scope object, reached through that version's compact scope.packet_id. Packet IDs remain deterministic request_ids(request_id). This avoids another full ref copy per version while preserving both packet and version ownership of provenance. Markdown stays artifacts/objects/<version_id>.md byte-identical.

Add an explicit scope kind to owned path/read/write/inventory handling; the current _object_path fallback must not accidentally route it to quarantine. Unknown kinds must fail. Reuse immutable no-overwrite put, safe paths, locks and fresh bounded reads; matching existing bytes are idempotent, different bytes conflict. Never repair or delete an existing sidecar automatically.

Proposed independent scope read cap1MiB, with max+1 refusal BEFORE JSON parsing. It is a serialization bound, not a new authoring capacity quota. Pure width arithmetic under R1 yields full canonical scope <=624282 bytes for the conservative1000-ref case with 19-digit IDs and256 quote-byte UIDs; duplicate UIDs in that arithmetic are intentionally invalid, making it an upper bound, not a reachable fixture. A valid unique-UID fixture must prove the cap does not reject accepted inputs. Depth/duplicate JSON key/noncanonical/UTF8/extra-field rules remain fail-closed. Do not introduce a new unbounded parser.

Request preparation validates packet -> computes full scope and compact scope -> immutably stages packet and scope object -> rechecks authority/reserves the compact request. A crash before index commit may leave quota/inventory-visible unreferenced objects, never a request naming unconfirmed bytes. Existing source snapshot validation still happens before reservation; digest/count cannot substitute for it.

Version commit validates its current packet/scope authority at the existing point, ensures the matching scope sidecar is durable, immutably stages exact Markdown, then commits compact version metadata and fulfilled request together in the index. Any staging failure refuses index publication. Same-ID retries must converge on identical objects; no invented receipt or fulfilled state after failed staging. No object lock may be held while acquiring the authoring or engine/catalog boundary lock. R3 does not move filesystem work across authority phases without a separate contract.

## Compact records versus full projections

The index, _persist and schema3 validators operate only on compact records. They validate bounded scalar grammar and cross-record identity/parent/version/lineage relationships without opening a packet or scope sidecar. No diagnostic or scope scan is added to _persist.

Introduce explicitly named compact request/by-dispatch readers for ArtifactService, enqueue validation, recovery, cancellation and D4 guards. Exact names/signatures await payload review. They return detached compact records with no packet/sidecar I/O. All service get_request/get_request_by_dispatch call sites must be audited, including Q1 error-handler reads, source-stop fences, ACK repair and unmatched lookup. Tests patching old public getters must be mapped before changes, not bypassed silently. A source-packet failure must still reach its historical diagnostic/fail/fence branch.

Existing get_request/get_request_by_dispatch full getters resolve their scope through the sidecar, validate it against EVERY compact field, and return fresh detached full audits. They do not require packet content health merely to reconstruct refs. Existing get_version/list_versions and export_metadata similarly hydrate full scopes. Page first, hydrate selected rows only; never inflate the entire index. A missing/corrupt sidecar causes typed object unavailability for that full projection, not healthy-empty, partial success, fabricated refs or an index-wide held latch. Metadata-only state/cancel/list-lineage operations remain possible. That is an explicit new object-health seam to test and disclose.

Full projections cannot silently return compact scopes to artifact_protocol/worker/archive consumers. Worker direct _packet_scope validation continues to compute full scope from exact packet messages; it never accepts a digest-only remote packet or A1 evidence. Brief scope_sha256 remains the packet digest. No HTTP/MCP/worker wire key or enum changes are proposed.

## Authority, A1 and D4 invariants

At a packet read, keep fresh bounded object read, path safety, _check_index and channel/source_run audit checks. Compare the freshly content-validated scope's compact projection against each CURRENT request compact scope that references that packet. Compare all seven fields, not just digest or count. A compact ref digest paired with a different packet hash, count, kind or revision must refuse. Full packet validation still proves per-message uniqueness and hash correctness.

A1 evidence continues to represent ONLY successful pure content validation of exact packet bytes and packet_id, never stored audit/authority. R3 may add immutable compact_scope_bytes to the issued evidence tuple alongside raw/full-scope/audit-view bytes, created together from the same successful validation. A hit can decode that small compact scope for the per-read audit loop, instead of re-hashing all refs on every hit. Any forged/mismatched pair, expired scope, owner/root/path/thread mismatch or different raw bytes triggers full validation. Failed audit comparison never registers evidence. Two entries/aggregate2*MAX_PACKET_BYTES raw limit, active/finally expiry and detachment remain. Extra derived scope bytes must be included in the memory disclosure and mutation proof; no evidence can survive the selected invocation. New helpers belong only at the current _packet content seam; worker/import/archive direct validators must not consume them.

D4 guard audit_bytes becomes canonical bytes of the complete compact audit, preserving every bounded authority field and the ordered-ref commitment. No owner transaction state is added. A/C re-read current compact authority with the same state/reason/channel/queue/outbox/ACK/disposition/producer/brief predicates as accepted. B remains diagnostic I/O without engine/catalog/authoring ownership; no sidecar hydration is allowed in C merely to compare guards. Attachment remains the same cached memory-only predicate. Structural diagnostics/request_diagnostics remain outside the boundary and independent of schema3 source objects.

## Schema and conversion compatibility

|On-disk input|Proposed behavior|
|---|---|
|No index|Healthy empty schema3 in memory; construction creates no files.|
|Exact valid empty schema2|Accept as empty schema3 in memory; first ordinary successful write publishes3.|
|Exact legacy empty schema1|Preserve the accepted harmless-empty compatibility behavior, now returning empty3; no diagnostic migration.|
|Nonempty schema2|Typed authoring hold with explicit offline conversion guidance; no constructor rewrite/reset. Diagnostic owner remains independently usable, subject to its existing sticky schema1 rule.|
|Nonempty schema1|Existing sticky hold in both owners; no expansion of schema1 conversion scope.|
|Schema3|Strict compact validator; object health checked at its read/use sites.|
|Unknown/mixed/malformed/duplicate-key schema|Hold, retain exact bytes. No partial interpretation.|
|Schema3 opened by older schema2 build|Unsupported schema hold, no downgrade/reset.|

Recommended explicit OFFLINE conversion, command/approval mechanics to freeze before reds: stop the app and all writers; copy the old index bytes to a verified backup outside the live index; run the frozen schema2/R1 validator; validate every referenced packet against its FULL old audit and each version against its request/Markdown; create only missing matching immutable scope sidecars; build a compact schema3 candidate; validate full projections against the original full scopes and index relationships; recheck old index exact bytes and object fingerprints; replace ONLY the index atomically last. Write a receipt with old/new hashes and every staged object. Interrupted before replacement leaves the old index authoritative plus possible orphans; interrupted/uncertain replacement requires restart/inspection, never an automatic retry that assumes the old index survived. Preserve backup and immutable objects; conversion does not delete old files, rewrite packets, reset diagnostics or activate capability. Concurrent writer detection aborts before publication. Live hot conversion is out of scope.

This conversion is a proposed R3 deliverable requiring review. No conversion command is executed or implied now. No released schema exists yet, but local development records and portable goldens still get explicit compatibility tests.

## Import, export, codec, lifecycle and backup

|Surface|Required preservation / intentional local adaptation|
|---|---|
|artifact_archive.py codec / archive.py|Portable archive schema2, artifacts/index.json version1 and member names stay unchanged. Portable scopes stay full. No sidecar path, compact digest/count or local schema3 key leaks into the ZIP. Preserve991296-byte golden and exact existing packet/Markdown bytes unless a separately reviewed reason proves a necessary portable change.|
|Export|export_metadata returns a fully validated detached full snapshot; read_archive_object continues accepting packet/version only. Missing/corrupt required sidecar fails the artifact export, no omitted provenance. Cross-check full scope versus packet while copying packet as before.|
|Import preparation|Validate full portable shapes and every exact packet/Markdown first; compute compact scopes and canonical sidecars from VALIDATED full scopes. Stage new sidecars outside metadata commit alongside immutable objects. Extend prepared evidence/root/stamps/collision/orphan accounting to them, and recheck under the existing import commit guard.|
|Import collision/idempotency|A preexisting different sidecar conflicts exactly like another immutable object, without overwriting it. Compact digest equality alone cannot authorize skipping full portable validation. Imported request producer capability/launch fields stay empty, state imported/read-only, diagnostics unattached.|
|Import bounds|4MiB portable metadata cap,50MiB archive cap and existing member/count/ratio limits unchanged. Count full portable refs against those caps; a compact local index does not enlarge allowable imports.|
|Rename/delete/lifecycle|Sidecar has no mutable channel; channel rename changes compact index rows only. Original channel/source/packet bytes stay immutable. Existing retained metadata/count/head/source_bytes summaries remain exact and sidecar-free. No purge added; channel deletion/export still does not free physical authoring history.|
|Backup|Channel ZIP reconstruction regenerates sidecars from its existing full portable scopes on import. Diagnostic metadata/bodies remain excluded as reviewed. For any raw app-state backup mechanism, include the new scope folder with other owned artifact objects; do not confuse raw backup with portable ZIP. No secret/launch file inclusion.|
|Diagnostics/inventory|Track scope objects in authoring object observations and unreferenced-object accounting outside the authoring lock. Missing scope is an object observation, no diagnostic owner failure. Existing cap/legacy/attachment semantics and report mid-scan OSError projection remain.|

## Capacity facts and bounded measurement proposal

Historical source-grounded figure:293110 index bytes for one ordinary fulfilled max-source request (2MiB packet/1000 refs/32KiB instruction),586096 for two, in the pre-R1/R2 storage-decision probe. It is not a current schema3 size or a quota promise. That record includes full refs twice; R2 removed diagnostics and R1 tightened grammar since it was measured. Reproduce the exact fixture on accepted220f340 and R3 separately, with both canonical JSON and actual atomic_json disk bytes.

For one fulfilled request, the canonical-scope reduction is exactly2*(encoded_full_scope_bytes - encoded_compact_scope_bytes), with other fields and serializer fixed; the empty-frame version digit has the same width. Repeated full instruction/producer/source metadata remains and grows with requests/versions. The conservative width arithmetic above gives624282 versus375 scope bytes, not a real valid fixture or a293110-case prediction. Smaller ref lists can cost more scalar metadata than before; report0/1/1000 refs rather than claiming every request shrinks. Sidecar adds a file and full-scope disk bytes; count packet/Markdown/sidecar totals separately from index savings.

Proposed measurement after reviewed reds/source, not run now:

1. Freeze native product/tool/fixture hashes and conversion source base. Validate synthetic controls and run one real SMOKE per class, timing not counted. Retain the accepted stall sentinel, retry counters, fixed-order/fixture disclosures, no overlapping suites and no selective reruns. No change to0.270/0.216/0.300 policies or machine-attribution repeat rules.
2. Size-only table on fresh fixtures:0/1/1000 refs;2MiB packet,512KiB Markdown/parent,32KiB instruction, valid max R1 labels/numbers; prepared/failed/cancelled/fulfilled/imported and multi-version histories. Prior population0/1/100 and the accepted129/130-request authority shapes. Show authoring index bytes/request and version, sidecar count/bytes, total owned bytes, and same-input schema2->3 projection equivalence. Include real valid unique UID shapes, not the duplicate-UID upper-bound arithmetic.
3. Actual service A/C and peer holds,10 fresh samples/class including combined brief/parent, CLI/API admit, reject, reservation/retained resume, ACK/startup and summary-only C. Diagnostic B ownership and mutating-peer/structural-read behavior stay covered. Use accepted harness/sentinel, retaining per-phase/whole call, retries, exceptions and all original rows. Bounds<=0.270 hard and<=0.216 for R3-added/changed holds. Explicitly measure sidecar/full-projection reads as well as compact state paths.
4. Preserve full/held4MiB import full/held/peer<=0.300 gates with sidecar staging included at its real location;10 fresh each, no fsync mocks. Converted schema2 and native schema3 fixtures both included functionally; conversion elapsed time reported separately outside the shared authority boundary.
5. Re-measure CURRENT create path with100 prior lineages, max source/parent, diagnostics empty/full/held and real producer/brief/reserve/enqueue,10 fresh each. This is DESIGN data for the subsequent operator-routes refresh/K6 decision, not operator acceptance. Report EACH boundary hold/peer and whole call. Existing create phase split is reconsidered only with that data; no automatic removal or implementation.
6. Any real miss returns to review, with all attempts retained. No quota or R4 incremental validation is chosen as a side effect. Finite installation capacity remains an explicit open product decision after the measurements; no claim of unbounded growth, no reinstatement of withdrawn128-request/512KiB ceiling.

## Required proof before R3 acceptance

One new root red file (suggested tests/test_artifact_compact_index.py), infrastructure versus behavioral failures labeled, existing equivalence tests adapted in a separately reviewable map. Reviewer reads first red bodies before production. Tests must distinguish:

- Full/compact codec exact fields, order-sensitive digest/count, empty refs, wrong packet/hash/count/kind/revision, bool/overflow and R1 Unicode/control/numeric edges; no full refs in persisted or authoritative RAM index.
- Request/version full projection equivalence, detachment and no sidecar/packet reads in compact metadata/cancel/diagnostic paths; missing/corrupt/noncanonical/oversize/symlink scope objects refuse only the relevant full projection. Source-packet-unavailable diagnostic path remains reachable without a hydrated audit.
- Crash/failure at packet/scope/Markdown/index staging, idempotent retry/collision, no index referencing unstaged objects, no object-lock -> authoring/boundary inversion. Between-read object changes revalidate; no stat-only content trust.
- A1 every existing failure/differential, full/compact evidence pair forgery, fresh current audit comparison, expiry/thread/owner isolation and worker/import/archive no-consumption; D4 all races/receipts/origin/ownership/legacy/startup Q1 controls remain discriminating.
- Schema2 nonempty hold/no-reset; empty compatibility; offline conversion preservation and no writes on malformed/missing/mismatched input, concurrent change/partial staging/uncertain replace; older reader fail-closed. Conversion never resets diagnostics.
- Portable golden/ZIP equivalence and archive exact limits, imported authority absence, sidecar collision/staging/second import; rename/lifecycle/backup exclusions/retention and diagnostic attachment unchanged.
- Focused R1/A1/R2/D4/archive/import/worker/recovery/lifecycle suites, artifact affected selection, one builder full discovery and meaningful digest/count/sidecar/evidence/compact-read mutations. Then measured gates and independent reruns/static audit. No claim of activation or whole-ticket completion.

Open for reviewer: confirm the scope sidecar representation, explicit full-versus-compact API split,1MiB sidecar bound and offline schema2 conversion recommendation; then freeze signatures/errors/fixture migration and measurement matrix before reds. Operator-route refresh follows R3 acceptance; operator implementation, UI, activation and push stay held.
