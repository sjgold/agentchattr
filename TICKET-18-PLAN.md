# Ticket 18 individual document review implementation plan

> For agentic workers: use superpowers:executing-plans for inline implementation. The existing user-authorized test helper may write only assigned new test files; no additional agents or live acceptance runs without the bounded work order.

**Goal:** Select one UTF-8 document/source file, preview its literal text and identity, then freeze that snapshot for identical CLI/API review without executing or rendering source.

**Architecture:** PROPOSED for Sonnet contract critique, not an implementation freeze. Extend existing immutable input_snapshot/brief source. Prefer stateless bounded byte preview plus revalidated file snapshot at Start, avoiding a second document store or public upload surface.

**Tech stack:** Existing Python/FastAPI, atomic session persistence, plain browser JS/file input. No dependencies.

Base published main: d787f4f79636dbdf8f7f1b9e40c7bc0d34ccc352. Branch codex/ticket-18-document-input. Issue18 open, blocker6 verifiedclosed. Scope authority specv1.7 DA-1/FileAT-04; issue's linkedv1.6 and old human/model gates are historical under Seth's later autonomous/Sonnet direction. Codex ownership56b000d9, Sonnet3b53a0e1 independent reviewer. Baseline1004TOTAL/four expected skips; prior17 receipt retained.

## Context and fit

review_brief.freeze_inputs already preserves exact UTF-8 input_text, rejectsNUL/over512KiB, computes SHA256 input_revision, and stores source in SessionStore. build_brief/brief_messages feed literal source to CLI/API independently of chat history. Both launchSessionWithCast and launchDraftSession currently read the pasted textarea; corrected restart has a separate edited-paste flow. There is no document/file intake module/store/preview yet. Image upload is public and unsuitable for source documents.

Graphify fast-path checked: no localgraph, sharedregistry has no agentchattr entry. Source tracing uses boundedrg/reads; no graph build/install/private-vault mutation.

## Approaches discussed

1. Recommended: stateless server byte preview, then submit and revalidate the canonical snapshot with Start. Existing run persists the text/metadata once. No preview-orphan lifecycle or document lookup authority.
2. Persist each preview in a DocumentStore, Start byID. Useful for future standalone library, but introduces storage/ownership/cleanup and that scope is not requested.
3. Client-only File.text preview/paste. Smallest UI change but cannot enforce authoritative byte/binary validation or preserve source identity robustly. Rejected.

## Proposed pure contract (not frozen until critique)

New document_inputs.py, independently testable and no filesystem/network/runtime operations:

- MAX_DOCUMENT_BYTES uses review_brief.MAX_INPUT_BYTES (512KiB), with no truncation.
- preview_document(filename, content:bytes) -> detached canonical snapshot.
- validate_document_snapshot(snapshot) -> detached canonical snapshot after recomputation.
- Exact snapshot fields: version=1, kind='file', source_id, name, encoding='utf-8', byte_length, content_sha256, text.
- name is the supplied basename/display title, nonempty validUTF-8/noNUL/control/pathseparator/colon, bounded255codepoints/1024UTF8bytes. Never used as a server path. Proposed allowed extensions(case-insensitive): .md/.txt/.py/.mjs/.js/.ts/.tsx/.jsx/.json/.yaml/.yml/.toml/.css/.html.
- Strict bytes.decode('utf-8'), never replacement/guessing. Preserve every decoded codepoint, CRLF/LF, Unicode and a leadingUTF8BOM asU+FEFF; text.encode('utf-8') must equal originalbytes. RejectNUL and binaryC0controls exceptTAB/LF/CR, plusDEL. Emptyvalidfile allowed and explicitlyshownas0bytes. Overlimit/binary/undecodable input fails atomically, without a partial snapshot.
- content_sha256 is SHA256 of exactbytes and equals eventual input_revision. source_id is 'file:'+SHA256 of canonicalJSON{name,content_sha256}; same namedcontent stable, renamed/changedcontent getsnewidentity. It is operator-supplied source identity, not native filesystem provenance or permission.
- Validation requires exactkeys/literalversion/nonstrictbool rejection for numericfields; recomputes textUTF8bytecount/hash/sourceID and rejects any mismatch. It does not trust client hash/size/path claims.

OPEN precision for reviewer: allowlist/empty/BOM/control policy; stateless rather than persistent preview; metadata/sourceID shape. Resolve these before helperTDD.

## Proposed transport and persistence

- Operator-session-only POST /api/documents/preview?filename=<percent-encodedbasename>, binarybody application/octet-stream. No arbitrary server filesystem path/URL. Reject missing/duplicate/unknownqueryfields, bearer-only andmissingtoken403. Iterate request.stream(), stopatMAX+1/413 before persistent writes; no multipart dependency or eager arbitrary upload spool. Return full canonical snapshot, Cache-Control:no-store. Decode/format400, oversized413, no partialsuccess.
- Session Start gains optional source_file canonical snapshot, mutually exclusive with an explicitly supplied input_text at HTTP boundary. Existing pasted path unchanged. Both routes share the pure validator; no new broad JSON parser/refactor.
- Proposed keyword-only optional source_file for engine/store/freeze_inputs; existing positional signatures/callers remain compatible. Validate before session/brief/queue/worker effects. Invalid or tampered snapshot gives no successful Start.
- Run input_snapshot retains existing text/revision/encoding and adds document metadata(same snapshot without text) only for file input. Pasted snapshots remain byte/schema compatible. source_id/name/bytes/hash remain frozen even if the original selected file is edited/deleted.
- build_brief adds optional source_document metadata for file inputs. brief_messages puts it beside the literal text in the UNTRUSTED user source packet, never as system authority. CLI gets the same source/text/hash/metadata via existing scoped brief. BriefStore revalidates optional metadata against source before use. No model filesystem tool or permission change.
- Retry/participant replacement reuse immutable file snapshot. Explicit corrected restart using edited pasted input produces a new pasted snapshot and drops fileorigin; no false originalfilename attribution. File selection in the corrected-restart UI is deferred unless needed to preserve existing behavior.
- No new document backup/export format, multi-file packet/library, directory crawl, PDF/parser, source-writing capability, execution or Markdown/HTML rendering. Later multi-file/quote features can consume the stablemetadata; no speculative framework.

## Proposed UI

Extend the two existing session source editors with one-filepicker and a shared small helper(document_inputs.js/css if warranted), accepting the listed extensions. Server preview is authoritative; client filesize/type hints are advisory only. Show literal source in a readonly textarea/pre(textContent), filename/title, exactUTF8bytecount, contenthash andstable sourceID beforeStart. This is source data, never marked/rendered code.

Keep the canonical response object in per-modal state and submit it onStart. Do NOT read the readonly textarea.value for fileStart, because HTMLtextarea normalizesCRLF; preserve the exact serverresponse text. PastedStart keeps existing input_text. Pick/cancel/change/close/failedpreview must not lose the pasted draft or start a run. Use an epoch/AbortController to discard stale responses, disableStart during validation, preserve the last valid draft onfailure, and provide an explicit Use pasted text/Removefile action. No autoretry/autoStart. Useredits require returning to paste or selecting anotherfile; no misleadingfilehash aftereditingpreview.

Both predefined-template and chat-draft Start paths use the samevalidated selection helper. Incumbent Operate styles,>=14px/12pxinset/44pxtargets, narrow layout, accessiblelabels/focus, no new visualworld or unrelatedheaderfix. UI file-object testing via browserDOM/DataTransfer must be labelled separately from a nativeOSfilepicker.

## Planned test/implementation sequence

- [ ] Settle governing choices/exactpureinterfaces withSonnet; update thisproposal tofreeze.
- [ ] Existinghelper owns new tests/test_document_inputs.py only: first2actualmissinginterfaceRED, then bounded~12cases UTF8/CRLF/BOM/Unicode/name/hash/size/binary/exactschema/noalias/noexecution. Rootimplements puremodule, focusedcheck, independentboundedreview.
- [ ] Root route/start/brief tests observedRED before wiring: boundedstream/413/auth/invalidsnapshot/noeffects, exactsameCLI/API source/identity beyond20messages, immutableoriginaledits, retries/restarts/failureatomicity. Implement narrow engine/store/brief integration andpreviewroute, preserve pastedfixtures.
- [ ] UIhelper/sharedstate and bothStartpaths withactual-sourceVMRED->green andtargetedbrowserfilepreview/error/norendering/Startchecks. No broadcomposer refactor.
- [ ] ActualisolatedWindows localfake verification .py/.mjs literalroundtrip through realupload/Start/CLIbrief/APIpayload, originaleditsafterselection/Start,>20chatmessages, no source side-effect marker/execution, genuine native resourceend andzero unresolvedcleanup. Draft/counts/cleanup reviewed before any run; no liveprovider/Omarchy/Desktop/globalchanges.
- [ ] Finalfullsuite/syntax/diff, independentwhole-ticketreproduction/recheckPASS, documentation, ffmerge/postmergefull, standingauthorizedpush/closure. Preserve failingattempts and exactsource attribution.

Next owner: Sonnet critiques thisproposal against DA-1/FileAT-04 andactualcallers, especially the threeOPENchoices. No production/test/helper source work yet.
