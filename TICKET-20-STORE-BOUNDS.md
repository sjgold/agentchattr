# Ticket 20 R1: bounded artifact records, proposed compatibility contract

Status: PROPOSED for independent review. Seth selected R1-R3 on2026-10-25 through the structured question. That approves this work's scope, not an unreviewed implementation. No source or new tests in this pin. R2 diagnostic ownership and R3 compact index still require their own schema contracts. Authoring remains disabled; no replacement quota or R4 implementation is approved.

## Outcome and boundaries

Every variable field copied into an artifact request/version has an explicit byte or numeric bound. API observation rejection uses the existing terminal path before result persistence. Raw Markdown/source text retains exact UTF8/BOM/CRLF; no truncation, normalization or invented observation. This is semantic validation with unchanged record key sets, not the diagnostic/index layout change.

There is no released artifact schema to migrate. Existing artifacts produced only by local tests/development are not silently rewritten: malformed local metadata holds according to the existing owner rules; imported lineages exceeding the new semantic bounds skip as invalid_lineage. Existing readable peers/body-byte behavior remains. Fixture/golden compatibility must be audited before edits, not assumed from the empty production capability tuple.

## Exact field policy

| Field / owner | Proposed bound |
| --- | --- |
| audit.requester | Label,256 UTF8 bytes |
| audit.producer.name, requested_model, requested_model_reason | Label,256 UTF8 bytes each; existing nullable/model-reason relationship unchanged |
| audit.source_run.state_at_request | Label,256 UTF8 bytes; existing source-run identity/revision checks unchanged |
| audit.scope.message_refs[].uid and packet.messages[].uid | Label,256 UTF8 bytes; both validators use the SAME rule, no generated replacement for a bad existing UID |
| observation.confirmed_model | null under existing adapter/reason rules, otherwise Label,256 UTF8 bytes |
| audit/brief instruction | Index free text,32768 UTF8 bytes; nonblank and NUL/surrogate-free as before |
| audit/brief format | Index free text,512 UTF8 bytes; nonblank as before |
| UUID/hash/channel/enum fields | Existing fixed grammars:32/64 lowercase hex, channel<=20 ASCII, closed states/reasons/adapter/capability literals. No wider text fallback. |
| Version Markdown and raw packet bodies | Existing524288-byte Markdown and2097152-byte/1000-message packet caps unchanged. Generic source/provenance/document text is not relabeled as an index Label. |
| Record integer fields | Exact int (not bool), existing minimum and narrower maximum, plus<=2**63-1. Includes persisted sequence/ref ids/session ids/counts/diagnostic byte counts and protocol parent sequences. |
| Record timestamp fields | Exact int/float, positive and finite as before; int<=2**63-1; float JSON token length<=23 ASCII bytes using the actual json serializer. Do not coerce int to float or change seal bytes. |

Label: existing _text validation plus byte cap, reject U+0000..U+001F and U+007F. No trimming/NFC/case conversion. Free text: same byte/nonblank checks, reject those controls EXCEPT HT(U+0009), LF(U+000A), CR(U+000D). **CR allowance is a review proposal:** it preserves Windows CRLF instructions and has a two-byte JSON escape, not the six-byte U+0001 amplification. The reviewer previously suggested HT/LF only; accept or reject this precise refinement before code. Raw packet message text, input text and Markdown retain their existing control policy (including current NUL refusal), not this index free-text filter.

Do not globally restrict _text or generic _json: they also validate immutable raw user/source data. Add narrow _label_text and _index_text helpers and apply them to the listed fields. Generic _integer remains available for ZIP header/pagination structural values; use a new _record_integer for index/protocol semantic fields. _number is the artifact record timestamp validator and gains the stated width rule. Floats remain finite/positive;23 is the maximum JSON token width for positive finite binary64 shortest representation (17 significant digits, decimal point, exponent marker/sign and up to3 exponent digits). A direct serializer check enforces the promised profile rather than assuming it.

## Source trace and implementation surface

Already read: artifact_store._text/_number/_integer/_packet_scope/_audit/_audit_imported/_observation/_validate_version/_validate_diagnostics/_validate_summary, artifact_protocol.validate_brief/validate_payload, artifact_worker.run_api_artifact, codec request/version/scope shape validators and archive driver's per-lineage exception catch. Callers were enumerated across store/protocol/worker/service/codec before this proposal.

Planned bounded changes:

1. artifact_store.py: constants MAX_ARTIFACT_LABEL_BYTES=256,MAX_ARTIFACT_RECORD_INTEGER=2**63-1,MAX_ARTIFACT_NUMBER_TOKEN_BYTES=23; narrow helpers; listed field calls and load/index/import semantic validation. Original import reason must exclude the string imported as already specified in the operator wire contract. Keep CLI legacy all-null launch refs with capabilities[artifact-v1] storage-valid; API null refs/local empty capabilities remain invalid. No new state/reason/member schema.
2. artifact_protocol.py: reuse these helpers for brief instruction/format, parent sequence, observation and result timestamp, so runtime and load agree. Existing sealing canonical forms and every valid vector byte remain unchanged.
3. artifact_worker.py: validate the generated observation inside the same pre-save invalid-response try/dispatch path as content parsing; keep owner/persistence faults separate from bad provider output. Do not turn a storage fault into invalid_response. No provider invocation, adapter, queue event, tool list, cancellation proof or legacy chat/review change.
4. artifact_archive.py: structure checks stay STRUCTURE-only for the new semantic bounds. Its current shared _number import would otherwise turn an overwide but syntactically numeric timestamp into a section400; add a codec-local shape-number validator with the old finite-positive/type rules for structural preflight, and let store semantic validation enforce the new width. Generic header _integer remains unchanged. Overlong labels, new disallowed label controls and out-of-range record numbers must become per-lineage invalid_lineage skips, while malformed types/keys/section hazards retain their accepted section errors/precedence. Body/packet semantic errors remain per-lineage as before.
5. Documentation: update store schema/protocol/wrapper contracts and the declared bounds table. The accepted import performance gate remains its separate0.300s profile; foreground operator/commit/cancel/Stop/recovery maximum-shape target is0.270s. R1 does not claim final R2/R3/K6 or enable capability.

## Exact invalid-observation outcome

The API generate return stays {content,confirmed_model}. Build observation={confirmed_model,confirmation_reason:api_response or provider_did_not_report_model}, validate it BEFORE payload/outbox save, and route its ValueError/type/Unicode failure through existing reject_response(_report(generated.content)). Do not send the overlong model label in that report, log or error. It is provider metadata, not a new source packet or model argument to fix.

Successful trusted rejection keeps the current result: API worker outcome quarantined / artifact_invalid_response; request state quarantined, reason invalid_response; bounded diagnostic under current caps; no saved artifact result and no version. Existing generation-intent receipts may exist, as they do for invalid content. It is NOT state failed, does NOT leave the whole index byte-identical (diagnostic/state metadata changes), and adds no new OperatorReason/agent-route/body field. If rejection delivery fails, existing held/delivery_unconfirmed/cancellation handling remains. CLI Markdown validation remains retryable ACTIVE as already accepted; forged/direct malformed agent records retain their existing no-poison refusal semantics.

## Observed-red and compatibility proof plan

Root owns ONE new tests/test_artifact_record_bounds.py; no previous helper files or fixture assertions change without a separately authorized correction. First two actual behavior reds against unchanged product: accepted API label257 UTF8 bytes must refuse, and generated valid Markdown plus overlong observation must take the terminal rejection path with no saved result/version. Label-size failure alone is not proof of the whole API path; record both. No ImportError-only substitute.

Expand root coverage after the first reds are frozen:

- All listed labels at byte256/257, including multibyte Unicode and combined/decomposed forms; no normalization. Free text instruction32768/32769 and format512/513 bytes; CRLF acceptance according to the reviewed decision; C0/DEL refusal only in the index fields; raw Markdown/source bytes and their Unicode/CRLF goldens unchanged.
- Integers2**63-1/2**63, bool/negative/zero according to each existing minimum; NaN/Infinity/zero timestamps, representative23-character positive floats, preserved int/float serialization and protocol/load/import parity.
- Local/legacy CLI and imported exception guards unchanged; a bad imported lineage next to a healthy lineage skips only the bad one with no source/index partial write. Pure section schema/bounds errors remain separate, including large ZIP header precedence.
- A per-record maximum serialized version golden: actual256-byte permitted Unicode labels,1000 unique maximum-width UIDs,32KiB instruction/512-byte format, max observation and numeric widths. Validate through the relevant record validators; record serialized bytes under actual atomic_json encoding. Use a conservative projected width for numeric sequences that cannot be physically populated to2**63 rows. Do not pretend the row fits512KiB or compute a final escrow before R3 fixes its physical layout.
- Audit current fixtures/goldens for static/dynamic positive label/numeric outliers BEFORE source edits; classify negative tests separately. Report any real fixture correction; do not silently rewrite assertions or claim a scan already ran.

After source changes: compile/strict UTF8/diff check, focused new bounds tests, unchanged store helper12/store_review/integrity/saturation, protocol/delivery/recovery, API/CLI worker/wiring, imported-store helper12/plan/codec/archive/import suites, runtime source-closure/capability gates. Run an appropriate frozen full regression once the focused checks pass, with no overlapping reviewer heavy suite. Send the small compatibility pin for independent review before R2/R3 or operator escrow relies on it. API fake/model/native/browser acceptance remains later work.
