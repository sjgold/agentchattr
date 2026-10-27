# Ticket23 implementation contract and red-first plan

**State:** frozen for reviewer evaluation before product implementation. Seth approved the a441a2d shape, raw512KiB aggregate and order-sensitive revision; reviewer may clear contract/reds while Seth is away. No24-26 or21/22 work. This contract narrows implementation details without changing the approved user flow.

**Goal:** choose multiple UTF-8 files in the existing source editor, preview their names/ids/raw sizes, freeze one packet for all selected reviewers, and check literal quotes against an explicit file id/revision.

**Budget:**90 minutes of active implementation/verification agent time after production clearance, then stop and report remaining work. Contract preparation and separately requested launch/security fixes are recorded separately. No rescoping or migration without steering. Spec: [multi-file requirement](../agentchattr-fork-spec.md#post-initial-build--multi-file-packets), lines303-305; approved shape: [proposal](2026-10-27-multi-file-packets.md).

## Exact format

Keep every version1 file and pasted snapshot byte-compatible. New packet snapshots have exactly these keys:

|Field|Value|
|---|---|
|version|integer2|
|kind|file_packet|
|encoding|utf-8|
|source_id|packet: followed by content_sha256|
|byte_length|sum of member raw UTF-8 bytes, not encoded JSON size|
|content_sha256|lowercase SHA-256 of text.encode('utf-8')|
|files|ordered list of member metadata described below|
|text|the canonical manifest JSON string described below|

Canonical manifest: exactly {version:2,kind:"file_packet",files:[members...]}. Each member has exactly the existing version1 file snapshot fields plus file_id. IDs are f1,f2,... in selection order, with no gaps. The existing file metadata fields are version,kind,source_id,name,encoding,byte_length,content_sha256,text. The outer files list contains those same member fields plus file_id, omitting text only. Duplicate names/content are accepted and retain distinct file_ids.

Canonical encoding uses sealed_result_io.canonical_utf8: sorted keys, compact separators, ensure_ascii=False, allow_nan=False. It is not a text delimiter format. Freeze this canonical string in input_snapshot.text; freeze outer metadata (snapshot minus text) in input_snapshot.document. input_revision and input_snapshot.revision equal content_sha256. This retains the existing revision=SHA256(source bytes) rule rather than creating an alternate authority path.

Changing any member name, bytes or order changes the canonical revision. Changing line endings/BOM is a byte change. Validators rebuild each member with preview_document and recompute the complete packet; edited fields, unknown keys/versions/ids and noncanonical text refuse, never repair on read. Packet validation returns a detached value.

## Caps and refusal

- Per member: existing MAX_DOCUMENT_BYTES=524288 raw bytes, strict UTF-8/control/name rules unchanged.
- Aggregate:524288 raw member bytes, inclusive. The UI displays the raw sum against512KiB. No silent drop or truncation.
- Metadata allowance:65536 canonical bytes for the manifest with each member text replaced by an empty string. This bounds large lists of empty/tiny files without inventing a separate file-count number. Refusal explicitly says packet metadata is too large.
- Canonical packet text allowance:2*524288+65536=1114112 bytes. Under ensure_ascii=False, valid text's quote/backslash/HT/LF/CR escaping expands by at most2; metadata includes the empty quote pairs. Test encoded growth separately from raw totals.
- Existing4MiB session-start body cap stays. Packet-preview body has the same4MiB cap. Test worst-case valid quoted/control/non-ASCII payloads under the actual HTTP serializer; if an approved input cannot fit, report before changing this contract.
- Existing authoring source2MiB/1000-message and archive limits remain. An accepted review packet can still receive an honest source_too_large refusal when combined with accepted responses for document authoring. No larger authoring cap is implied.

Use existing DocumentInputError / DocumentTooLarge and BriefError boundaries. No new error logging containing source or keys. Refuse the whole operation before allocating a session, source object or dispatch.

## Public seams and preview

New pure module document_packets.py exports preview_packet(files), validate_packet(snapshot), and check_quote(snapshot,citation). preview_packet accepts a nonempty list of existing validated version1 snapshots and returns the version2 snapshot. validate_document_snapshot remains the public version-dispatch seam and delegates version2 to validate_packet; old callers stay compatible.

POST /api/documents/packet-preview accepts exactly {files:[version1 snapshots...]}, returns the packet snapshot (200), rejects malformed/unknown body or query fields (400), overflow (413), and agent/unauthenticated access (403) using the existing operator middleware rules. It performs no filesystem input read or persistence. Single-file preview keeps its route, auth and response unchanged.

Existing DocumentInput.attach editor: multiple picker enabled; preview each file through existing single-file endpoint, then assemble through packet-preview. One selected file keeps the old version1 path; multiple files use version2. Show file ids/names/raw byte counts and aggregate. Removing a member recomputes the preview and ids; a stale response cannot replace a newer selection. Failures keep Start disabled until corrected or switched to pasted text. Readonly source text is literal, names via textContent. No file text in browser storage. Source submission still uses source_file, never a second input field or a chat attachment.

check_quote(snapshot,citation) accepts exactly {packet_revision,file_id,quote}. Return exactly {verified:bool,reason:null|string}. Invalid citation shape/type/empty quote -> invalid_citation; wrong revision -> packet_revision_mismatch; unknown file id -> unknown_file; literal text absent from that member -> quote_not_found; success -> true/null. Invalid packet itself raises DocumentInputError. Look only inside that member. Identical quotes in two files can each prove membership; the helper cannot infer author intent. An unknown/wrong id never falls back to searching another file. No findings parsing, reviewer UI or synthesis.

## Consumer/compatibility map

|Consumer|Required change/proof|
|---|---|
|document_inputs.py + new document_packets.py|Version dispatch, exact validation and caps; version1 unchanged|
|review_brief.py freeze_inputs/_validated_document/BriefStore/build_brief/brief_messages|Packet-aware source allowance only for validated v2; one canonical source/revision; same packet for CLI delivery and API messages|
|session_store.py create + session_engine.py start|Existing source_file plumbing accepts v2; snapshot persists/reloads without rewrite|
|Same-turn retry/participant replacement/turn_events.py|Existing input_revision gates and frozen briefs retain the same packet; stale results still refuse|
|Corrected restart + sessions.js|Existing explicit corrected-paste behavior remains (a child is pasted input with its usual cap; original packet stays frozen). Do not interpret arbitrary pasted JSON as authority. To review changed files as a packet, reselect them in a new review. No new linked multi-file correction editor in this slice|
|artifact_sources.py|Validate/reuse v2 metadata and canonical source; keep existing source cap/refusals|
|artifact_store.py/_packet_scope + artifact_archive.py|Opaque source_document dictionaries and canonical packet bytes already travel together; real store/export/import fixtures must roundtrip v2 without granting authority or rewriting old packets|
|archive.py|Channel history does not currently add full SessionStore export;23 does not add session backup. Existing artifact packet export/import is the compatibility proof|
|app.py packet-preview + session-start|Operator-only preview,4MiB body bounds; actual start passes canonical v2 through existing source_file seam|
|static/document-inputs.js + sessions.js consumers|List/aggregate/removal, stale/abort/dispose safe; source labels understand v2 rather than showing undefined filename|
|runtime_protocol.py SOURCE_FILES|Declare new pure module in both adapter closures; old source hashes are not rewritten. Existing live seats need a deliberate refresh before relying on new manifests|
|wrapper_api.py + MCP brief delivery + managed seats|Consume the existing frozen envelope unchanged; tests compare exact packet/revision on both paths; no live provider generation required|

No store migration, source repair or current-record rewriting. If that proves impossible, stop for steering rather than reinterpret old records.

## Tasks and checks

- [ ] Observe core schema/cap/quote, actual freeze/brief/store/source, route and actual-JS picker reds. Label missing seams as infrastructure, genuine rejections as behavioral; unexecuted bodies stay unobserved.
- [ ] Send this contract and red pin to reviewer; wait for production clearance.
- [ ] Implement pure packet validator/helper and v1/v2 dispatch, then exact-cap/tamper/quote tests green.
- [ ] Thread validated packet through brief/source/session consumers; use real persistent stores and prior source fixtures. Keep auth/recipient/Stop/retry/seal suites green.
- [ ] Wire operator preview and existing picker/list, with actual-JS controls and typed failures. No new browser harness.
- [ ] Run affected document/brief/session/source/archive/UI/protocol tests; report at90-minute agent-time checkpoint. Final full discovery belongs to frozen release gate, disclosing9 post-launch transcript skips plus existing skips.

No new features outside this contract, no push, no publication, no deletion.

## Observed red checkpoint

Before implementation:22 tests,9 FAIL +12 ERROR +1 PASS in0.571s. The12 errors split into8 missing-seam infrastructure errors (6 missing document_packets module,2 missing preview_document_packet route function) and4 behavioral rejections by existing file/brief validation.9 failures are missing route/start acceptance plus the actual-JS picker refusing multiple files (including its distinct wrong-reason aggregate refusal). Bodies beyond an earlier missing seam/first assertion remain unobserved until implementation.

The one PASS is a real artifact-store export/import roundtrip of the independently constructed canonical v2 source packet. This is existing opaque-packet compatibility evidence, not proof that new file validation/delivery works. No product file changed in this checkpoint.

Root files: tests/test_document_packets.py (11), tests/test_document_packet_routes.py (4), tests/test_document_packet_ui.py (7). Run: python -m unittest tests.test_document_packets tests.test_document_packet_routes tests.test_document_packet_ui. The first route run also discovered9 imported legacy tests; the import was corrected to a module fixture before the final22-test run. Initial UI controls use actual shipped document-inputs.js and fake-only responses/DOM; they prove no rendered layout.

Retained red log: .audit-tmp/ticket23-reds-errors.log; SHA-256 c048facc2d6a54ad82f038c7ac78860b50f3fb713d0229cd75add393cbb72316. No production implementation has begun;90-minute active implementation/verification checkpoint starts only after reviewer clearance.
