# Ticket 18 individual document review implementation plan

> For agentic workers: use superpowers:executing-plans for inline implementation. The existing user-authorized test helper may write only assigned new test files; no additional agents or live acceptance runs without the bounded work order.

**Goal:** Select one UTF-8 document/source file, preview its literal text and identity, then freeze that snapshot for identical CLI/API review without executing or rendering source.

**Architecture:** Contract settlements confirmed by Sonnet atd399cc3; pure-module TDD cleared. Stateless bounded byte preview plus revalidated file snapshot at Start extends existing immutable input_snapshot/brief source. No second document store or public upload surface. The server proves snapshot self-consistency and enforces limits, not native file provenance; kind=file remains an operator assertion like pasted input.

**Tech stack:** Existing Python/FastAPI, atomic session persistence, plain browser JS/file input. No dependencies.

Base published main: d787f4f79636dbdf8f7f1b9e40c7bc0d34ccc352. Branch codex/ticket-18-document-input. Issue18 open, blocker6 verifiedclosed. Scope authority specv1.7 DA-1/FileAT-04; issue's linkedv1.6 and old human/model gates are historical under Seth's later autonomous/Sonnet direction. Codex ownership56b000d9, Sonnet3b53a0e1 independent reviewer. Baseline1004TOTAL/four expected skips; prior17 receipt retained.

## Context and fit

review_brief.freeze_inputs already preserves exact UTF-8 input_text, rejectsNUL/over512KiB, computes SHA256 input_revision, and stores source in SessionStore. build_brief/brief_messages feed literal source to CLI/API independently of chat history. Both launchSessionWithCast and launchDraftSession currently read the pasted textarea; corrected restart has a separate edited-paste flow. There is no document/file intake module/store/preview yet. Image upload is public and unsuitable for source documents.

Graphify fast-path checked: no localgraph, sharedregistry has no agentchattr entry. Source tracing uses boundedrg/reads; no graph build/install/private-vault mutation.

## Approaches discussed

1. Recommended: stateless server byte preview, then submit and revalidate the canonical snapshot with Start. Existing run persists the text/metadata once. No preview-orphan lifecycle or document lookup authority.
2. Persist each preview in a DocumentStore, Start byID. Useful for future standalone library, but introduces storage/ownership/cleanup and that scope is not requested.
3. Client-only File.text preview/paste. Smallest UI change but cannot enforce authoritative byte/binary validation or preserve source identity robustly. Rejected.

## Pure contract (confirmed, pure implementation review pending)

New document_inputs.py, independently testable and no filesystem/network/runtime operations:

- MAX_DOCUMENT_BYTES uses review_brief.MAX_INPUT_BYTES (512KiB), with no truncation.
- preview_document(filename, content:bytes) -> detached canonical snapshot. Only exactbytes accepted, no coercion. DocumentInputError(ValueError) for validation, DocumentTooLarge(DocumentInputError) specifically for the byte cap (route413); no IO or execution.
- validate_document_snapshot(snapshot) -> detached canonical snapshot after recomputation.
- Exact snapshot fields: version=1, kind='file', source_id, name, encoding='utf-8', byte_length, content_sha256, text.
- name is the supplied basename/display title, validUTF8 and bounded255codepoints/1024UTF8bytes. Reject empty/empty-after-trim, . and .., Unicode categoriesCc/Cf(includingbidi/zero-width), U+2028/U+2029, pathseparators/colon, trailingdot/ASCIIspace. Preserve allowed name codepoints/case exactly, never use as a server path. Extension list .md/.txt/.py/.mjs/.js/.ts/.tsx/.jsx/.json/.yaml/.yml/.toml/.css/.html is an ADVISORY filepicker accept hint, not a server gate. Other validUTF8text(.rs/.go/.sql/.log/Makefile/LICENSE etc.) is accepted. Nothing is executed/rendered or rich-format extracted regardless of extension.
- Strict bytes.decode('utf-8'), never replacement/guessing. Preserve every decoded codepoint, CRLF/LF, Unicode and leadingUTF8BOM asU+FEFF; text.encode('utf-8') must equal originalbytes. RejectNUL/C0exceptTAB/LF/CR plusDEL. Control errors identify codepoint(U+XXXX) and zero-basedUTF8BYTEoffset without echoing source; invalidUTF8 likewise reports byteoffset without offendingbytes. Preview visibly says UTF-8 BOM present, preserved when applicable. Emptyfile allowed and prominentlyshown0 bytes (empty source), neverautoStart. Overlimit/binary/undecodable input gives no partialsnapshot or effects.
- content_sha256 is SHA256 of exactbytes and equals eventual input_revision. source_id is 'file:'+SHA256 of canonicalJSON{name,content_sha256}, using sort_keys=True/ensure_ascii=True/separators=(',',':')/allow_nan=False encodedUTF8. Same namedcontent stable, renamed/changedcontent newidentity. It is operator-supplied source identity, never native filesystem provenance or permission. Name metadata appears only in the untrusted source packet, UItextContent.
- Validation requires exactkeys/literalversion/nonstrictbool rejection for numericfields; recomputes textUTF8bytecount/hash/sourceID and rejects any mismatch. It does not trust client hash/size/path claims.

Sonnet settled stateless/self-consistency, advisoryextensions, BOM/empty/control, namehardening, metadata/sourceID, and unchanged-file restart guard below. No production/tests until the amended freeze is confirmed. PureMAX aliases existingMAX_INPUT_BYTES; downstream imports stay local where needed to avoid a new modulecycle.

## Proposed transport and persistence

- Operator-session-only POST /api/documents/preview?filename=<percent-encodedbasename>, binarybody application/octet-stream, requiring Ticket17 request.state.auth_origin==operator. Bearer agents andmissingtoken403. No arbitrary server path/URL. Rawquery<=4096bytes, ASCIIpercentencoding with complete%HH escapes, strictUTF8 percentdecode once; reject missing/duplicate/unknownqueryfields, overlong/malformedencoding generically with no filenameecho. Iterate request.stream(), stopatMAX+1/413 before persistent writes; no multipart dependency/arbitrary spool. Return full snapshot+Cache-Control:no-store; decode/format400, size413, no partialsuccess.
- Session Start gains optional source_file canonical snapshot. Mutual exclusion is by KEY PRESENCE: a body containing source_file and any input_text key(includingemptystring) rejects400/noeffects. FileUIomitsinput_text entirely; pastedUIomits source_file. Existingpastedpath unchanged. Bothpaths use purevalidation, no broadJSONparser/refactor. Start re-enforces512KiB and existing4MiBbodycap; test actual512KiBCR/LF-heavy snapshot JSON(<~1MiBplusmetadata) fits4MiB without truncation.
- Proposed keyword-only optional source_file for engine/store/freeze_inputs; existing positional signatures/callers remain compatible. Validate before session/brief/queue/worker effects. Invalid or tampered snapshot gives no successful Start.
- Run input_snapshot retains existing text/revision/encoding and adds document metadata(same snapshot without text) only for file input. Pasted snapshots remain byte/schema compatible. source_id/name/bytes/hash remain frozen even if the original selected file is edited/deleted.
- build_brief adds optional source_document metadata for file inputs. brief_messages puts it beside the literal text in the UNTRUSTED user source packet, never as system authority. CLI gets the same source/text/hash/metadata via existing scoped brief. BriefStore revalidates optional metadata against source before use. No model filesystem tool or permission change.
- Retry/participant replacement reuse immutable file snapshot. Correctedrestart explicitly creates a new PASTEDsnapshot/dropsfileorigin. IMPLEMENT the file-origin unchanged-source guard: validateparentfilemetadata against its frozen text; compare old/new source after CRLF/CR->LF ONLY for equality detection on file-origin parents. Newline-only/editor-normalized unchanged content rejects with existing unchangedsource error BEFORE child/context persistence orprocessactions. Do not normalize parentstoredbytes/hash or genuine editedchildbytes/hash. Pasted-parent guard remains byte/hashexact. RestartUIshowsOriginalfile{name}+lineendingbadge and clearnewpasted-snapshot explanation. TestsCRLF/CR/LFmixed unchanged/realedit, nochild/noPopen/controleffects, immutableoldfilemetadata; genuineeditedchild has no source_document. Filepicker for correctedrestart remains outscope.
- No new document backup/export format, multi-file packet/library, directory crawl, PDF/parser, source-writing capability, execution or Markdown/HTML rendering. Later multi-file/quote features can consume the stablemetadata; no speculative framework.

## Proposed UI

Extend the two existing session source editors with one-filepicker and shared small helper(document_inputs.js/css if warranted), using listedextensions only as anaccept hint. Server validation is authoritative for self-consistency/limits; clientfilesize/type hints are advisory. Show literal source inreadonlytextarea/pre(textContent), filename/title, exactUTF8bytecount, contenthash/sourceID beforeStart; visiblylabelBOMpreserved and0bytesemptysource. No claim of nativefileprovenance. This is source data, never marked/rendered code.

Keep the canonical response object in per-modal state and submit it onStart. Do NOT read the readonly textarea.value for fileStart, because HTMLtextarea normalizesCRLF; preserve the exact serverresponse text. PastedStart keeps existing input_text. Pick/cancel/change/close/failedpreview must not lose the pasted draft or start a run. Use an epoch/AbortController to discard stale responses, disableStart during validation, preserve the last valid draft onfailure, and provide an explicit Use pasted text/Removefile action. No autoretry/autoStart. Useredits require returning to paste or selecting anotherfile; no misleadingfilehash aftereditingpreview.

Both predefined-template and chat-draft Start paths use the samevalidated selection helper. Incumbent Operate styles,>=14px/12pxinset/44pxtargets, narrow layout, accessiblelabels/focus, no new visualworld or unrelatedheaderfix. UI file-object testing via browserDOM/DataTransfer must be labelled separately from a nativeOSfilepicker.

## Planned test/implementation sequence

- [x] Settle governing choices/exactpureinterfaces withSonnet; d399cc3 diffconfirmed beforepureTDD.
- [ ] Existinghelper owns new tests/test_document_inputs.py only: first2actualmissinginterfaceRED, then bounded~12cases UTF8/CRLF/BOM/Unicode/name/hash/size/binary/exactschema/noalias/noexecution. Rootimplements puremodule, focusedcheck, independentboundedreview.
- [ ] Root route/start/brief tests observedRED before wiring: boundedstream/413/auth/invalidsnapshot/noeffects, exactsameCLI/API source/identity beyond20messages, immutableoriginaledits, retries/restarts/failureatomicity. Implement narrow engine/store/brief integration andpreviewroute, preserve pastedfixtures.
- [ ] UIhelper/sharedstate and bothStartpaths withactual-sourceVMRED->green andtargetedbrowserfilepreview/error/norendering/Startchecks. No broadcomposer refactor.
- [ ] ActualisolatedWindows localfake verification .py/.mjs literalroundtrip through realupload/Start/CLIbrief/APIpayload, originaleditsafterselection/Start,>20chatmessages, no source side-effect marker/execution, genuine native resourceend andzero unresolvedcleanup. Draft/counts/cleanup reviewed before any run; no liveprovider/Omarchy/Desktop/globalchanges.
- [ ] Finalfullsuite/syntax/diff, independentwhole-ticketreproduction/recheckPASS, documentation, ffmerge/postmergefull, standingauthorizedpush/closure. Preserve failingattempts and exactsource attribution.

Next owner: Sonnet independently reviews the puremodule/testcheckpoint andprobesadversarialinputs beforewiring. Onlynewdocument_inputs.py andtest_document_inputs.py implemented; app/engine/UI unchanged.


## Settlements S1-S6 and initial test freeze

Source-read review at e774037 APPROVED WITH SETTLEMENTS. S1/S2/S3/S5/S6 incorporated above. S4 selectedimplementation, notdeferral: file-origin newline-normalized unchangedguard + explicitpastedrestartbadge, preservingactualstoredbytes/hashes. Root verifiedcurrentstorehashguard andUItextareaprefill. Noimplementationyet.

Initialhelper scope afterdiffconfirmation: NEW tests/test_document_inputs.py only, first2actualmissingmodule/interfaces RED, then bounded12methods covering exactUTF8/CRLFmix/BOM/astral/combining/noalias; malformed/overlong/surrogateUTF8; NUL/ESC/DEL/FF codepoint+BYTEoffset;512KiB/+1;empty; nameCc/Cf/bidi/separators/colon/dot/trailing/UTF8/length; advisoryextensions/case/extensionless; exactkeys/literalversion/no boolnumeric/coercion; recomputedhash/size/sourceID/text tamper. .py/.mjs literals containing@all,$(...),<script>,fences,__import__ remain inert. Do not import/run sourcefiles or claim HTTP/engine/native proof. Root later testsinput_revision==contenthash,CRLF-heavyJSONbodybound,routeauth/rawquery/stream/noeffects, bothStartpaths, correctedrestartguard, >20messages/CLI+API payload/sourcefileedit/delete, DataTransferbrowserseam. Source identityself-consistency neverprovenanceauthority.


## Final precision P1/P2, pure TDD cleared

Sonnet confirmed e774037..d399cc3 docs-only settlement; no implementation/test run by reviewer. P1 limitation: a line-ending-only intended change(CRLF/CR->LF) is treated asUNCHANGED by correctedrestart for file-origin parents; use a genuinelyeditedsource or a separatelyselectedfile/newreview rather than using correctedrestart as a line-ending converter. P2 symmetry: normalize CRLF andbareCR->LF on BOTH frozenparenttext and proposedcorrectedtext, ONLY after revalidating parentdocumentmetadata against its frozen text; invalidparentmetadata fails closed, never falls back to exact-hash guard. Storedbytes/hashes remain unnormalized. Purepreview input type is exactbytes only, bytearray/memoryview/str rejected. These precisions do not affectpurehelpertestscope.

Next owner existinghelper: firsttwoactualmissingmoduleRED innewtests/test_document_inputs.py, thenbounded12puremethods; rootimplementsnewmoduleonlyaftertheRED. Reviewer independently reruns/probes puremodulebeforewiring. NoHTTP/engine/nativeclaimfrompuretests.


## Pure implementation checkpoint (unwired)

First2actualmissingmoduleRED0.005s, thenrootnewmodule/first2PASS0.063s. Helper12puremethodsPASS0.277s androotindependent12PASS0.261s;pycompile/diffclean, nofixturecorrections/assertionweakening. Purechecks cover allsettledinput/identity/schema/name/binary/size cases; no route/session/native/full18acceptance proof. Sourcefieldsunchangedelsewhere. Sonnet frozen-source/adversarial review next; no callerwiringbeforeboundedclearance.


## Pure checkpoint independently cleared

Sonnet atdocs-onlyade99d3/source405b136:12testsPASS0.257s and~65ownadversarialprobes,512KiBpreview0.039s/validate0.038s. BoundedPUREPASS only, noHTTP/engine/UI/nativeproof. Nits retainedaspolicy: contentC1(U+0080..U+009F) accepted becausegateisC0+DEL, notallUnicodecontrols; name trailingUnicodeZs/NBSP permitted becausetrailing-space ruleisASCIIspace/dot; filenamesstillrejectallCc/Cf andU2028/29. No purechangesrequired.

## Wiring tranche interface freeze proposal (before tests/code)

### Operator preview

- New helpersinapp.py: `_document_filename(request) -> str` and `async _document_bytes(request) -> bytes`; `async preview_document_input(request:Request)` registeredPOST`/api/documents/preview`.
- Require request.state.auth_origin=='operator' before readingquery/body; agentbearer/notoken403. Require Content-Type media type application/octet-stream(case-insensitive, optionalparameters allowed), otherwise415. No newpublic/static/uploadroute.
- Parse request.scope['query_string'] directly, exactbytes<=4096; ASCIIwire, complete%HHescapes, strictUTF8percentdecodeONCE(via parse_qsl encodingutf8/errorsstrict, rejectmalformedpercentfirst), exactlyonefilenamepair withnonemptyvalue, noextrakeys/duplicates. Generic400/no filenameecho; purevalidator appliesnamepolicy. Do not rely on Starlette replacement decoding.
- Streamchunkswithoutrequest.body/multipart. Retainedbuffer neverexceedsMAX_DOCUMENT_BYTES+1, includinga singleoversizedASGIchunk(sliceonlyremainingbudget); onoverflow raiseDocumentTooLarge anddoNOTiteratefurtherchunks. This boundsretainedpayload, nottheASGIserver'sownnetworkbuffer. Emptybodyvalid. Incomplete/disconnectrequest returnsgeneric400 ifpossible, no snapshot/state effects. Finaljoin<=MAX thenpurepreview_document; outputJSONsnapshot/no-store. Size413, validation400, unsupportedmedia415. No writes/callbacks/router/queue/Popen/nativeaction.

### Start and snapshot threading

- `SessionEngine.start_session(..., recovery_policy=None, *, source_file=None)` and `_start_session(..., recovery_policy=None, *, source_file=None)`; preserveallpreviouspositionalargs. Validate source_file/canonicalself-consistency beforebindings/managerinspection inengine, beforeanydispatch/persistence.
- `SessionStore.create(..., recovery_policy=None, *, source_file=None)`; `freeze_inputs(template,goal='',input_text='',rules=None,capacity_policy=None,*,source_file=None)`. Store/freezeboundaryrevalidates, so internalcallerscannotbypasslimits.
- HTTPStart: immediatelyafterexisting4MiBJSONobjectparse, ifsource_fileKEYpresent requireoperatororiginand reject ANYinput_textKEY(includingempty/None); validatecanonicalfilebefore drafttemplate registration/autocast/engineeffects. Null/invalidsource_file isfailure, neverpastedfallback. Pastedrequest unchanged. FileUIomitsinput_text, sendsfullcanonicalsource_file. DocumentTooLarge413/DocumentInputError400 atHTTP, wrappedBriefError atinternalfreeze boundary forcompatibility.
- Internalfunctions allow defaultinput_text='' withsource_file(neededforsignaturecompatibility), reject nonempty/non-stringpastedargumentalongsidefile. Source_fileNone remainsordinarypastedmode internally; HTTPpresenceNone rejected.
- File frozenrun exactshape: input_revision==content_sha256==SHA256originalbytes; input_snapshot existing{text,revision,encoding} plus `document` = canonicalfullsnapshot WITHOUTtext (7exactmetadatafields:version,kind,source_id,name,encoding,byte_length,content_sha256). No path, nativefileprovenance or executionauthority. Pastedinput_snapshot retainsold3fieldshape andhashsemantics.

### Brief metadata and fail-closed reads

- Add private review_brief._validated_document(metadata,text) -> detached canonicalmetadata. Reject non-dict/embeddedtext/unknown/missingmetafields; reconstructfullsnapshotwithauthoritativetext andcallvalidate_document_snapshot. WrapDocumentInputError inBriefError withoutsourceecho. No fieldmaskingofextra`text`.
- freeze_inputs storesfilemetadata onlyafterpurefullvalidation. build_brief readsfilemetadata onlywhen `document` KEYpresent ininput_snapshot, calls_validated_document andadds `source_document` (same7metadatafields); absentkeypreservespasted/legacyenvelopeunchanged. PresentNone/malformed failsclosed, notfallback.
- brief_messages puts source_document beside text/input_revision inUNTRUSTED user sourcepacket only, notsysteminstructions; no new tools or permission. CLIscopedbriefreturnssameoptionalmetadata/source. BriefStore._validate, when source_documentKEYpresent, revalidatesmetadataagainstsource (alsoexistinginput_revisioncheck) beforeuse/seal/return; no on-diskrepair/mutation.
- Retry/replacement useexistinginput_snapshot/revision; newbriefs retainmetadata throughbuild_brief. Noidentity/seal/Stop/outboxchanges. Snapshot/briefreturns detached; mutationdoesnotchangefrozenrun.

### Corrected restart P1/P2

- SessionStore.prepare_restart: ifparentinput_snapshot hasdocumentKEY, revalidateitagainstparenttext FIRST; invalidfailsclosed. Forfileoriginonly compare `_newlines(parenttext)==_newlines(input_text)` withCRLF->LF thenbareCR->LF onBOTHsides. Equal raisesexistingunchanged-sourceBriefError beforechild/contextwrites/callbacks/Popen. Keepoldhash-equalityguardforpastedparents.
- Genuinelyeditedinputstillfreezes exactsubmittedbytesasNEWPASTEDsnapshot, nofiledocument/source_document; doNOTnormalizetheparentorchildtext/hash. ExistingrequestID/replay/binding/Stopguardsremain. Explicitlineending-onlycorrectionunsupportedforfileparents; selectanotherfile/newrevieworactuallyedittext.
- ExistingrestarteditoraddsplaintextbadgeOriginalfile{name}/lineendings andsays thisrestartcreatesapasted snapshot; nofilepickerinrestart, noalterationoftheoldsourcepreview.

### UI helper API proposal for later UI tranche

- New static/document-inputs.js exports `DocumentInput.attach(editorElement) -> facade` with `.requestFields()` (returnsdetached{input_text} or{source_file}; throwswhilevalidation/error), `.setSubmitting(bool)` (disablesownsourcecontrols whileexplicitStartinflight), `.dispose()` (abort/staleinvalidate), readonly `.state` paste|reading|file|error. Emits `document-input-state` onmeaningfulchange. Per-modalstate, no globalsnapshotsharedbetweenlaunchers.
- Bothsessionlauncher/draftmodalsattachtotheexisting.session-source-editor; bothStartfunctionscollectfacade.requestFields BEFOREHTTP, setSubmittingtrue, restoreonfailure,disposeonclose/success/replacement. Startbuttonsdisabledreading/error/submitting; noStartfromstalesnapshotorfailednewselection. Existingpastedtextcached/restoredonexplicitUsepastedtext. Filepickercancelkeepspreviousstate, invalidnewselectionkeepsoldpreviewbutclearlyblocksStartuntilnewfileorUsepastedtext. Noautoretry/start.
- BinaryfetchusesURLfilenameencodeURIComponent, rawFilebody withoctetstream/sessiontoken;8sdeadline/AbortController/epoch/connectededitorcheck discardsstale. Display servercanonicaltextreadonlyandsubmitthatobject, nevertextarea.valueforfile. Basicresponseschemafailclosed; serverStartrevalidates. Hash/size/sourceID/BOMnote/emptywarning viaDOMtextContent. Acceptlistisadvisory; noextJSgate. Incumbent14px/12px/44px, narrowlayout/keyboardlabels, fileDataTransfertestlabelnoOSpickerclaim.
- Loadsharedhelper before sessions.js, scopedCSS onlyifneeded. ThisAPI getsitsownshortbehaviorconfirmationbefore UItests/code; backendtranchedoesnotimplementit.

### Proposed test ownership and next action

AfterSonnetinterfaceconfirmation, existinghelper ONLYnewtests/test_document_briefs.py bounded12methods, first2actualmissingkeyword/interfaceRED beforewiring. Realstore/engine/brief fixtures withnon-nativequeue/registryseams, clearlylabelled; noHTTP/nativeclaim. Cover exactfilefreeze/metadata/CLI+APIpacket/>20messages/edits-delete/noalias/pastedcompatibility/tamper/failatomicity/retryreuse and P1/P2storeguard asfits12; rootownsnewroute/restarttestsseparately. Rootnewtest_document_routes.py coversstream/query/auth/contenttype/4MiBJSONbodybounds andbothHTTPStartfields/noeffects. Rootimplementsbackendwiring onlyafteractualRED. No UI/nativeactions beforelaterworkorder/cleanupreview. Fullrepo regression afterbackendchanges, notclaimedfrompure12.


## Wiring confirmation W1-W4 (before integration TDD)

Sonnet confirmed the interfaces at e047e33 with these four precisions. No backend wiring or integration tests have been implemented at this checkpoint.

- W1: `_document_bytes` checks Content-Length before iterating the stream. An absent header uses the bounded stream path. A present header must occur once and contain only ASCII decimal digits representing a nonnegative length; malformed, negative or duplicate headers return generic 400. A valid length above MAX_DOCUMENT_BYTES returns 413 without reading a chunk. Streaming still retains at most MAX+1 bytes, slices oversized chunks to that remaining budget, and stops on overflow. This bounds application-retained memory, not the socket buffer. Test early refusal with a stream that must never be read, and absent/chunked MAX and MAX+1 bodies.
- W2: reject a raw `+` in the raw filename query with generic 400 before parse_qsl. Encoded `%2B` is decoded once and preserved, so `c%2B%2B.md` previews as `c++.md`. The client uses encodeURIComponent. Keep missing, duplicate, unknown, malformed-percent and invalid-UTF8 query tests.
- W3: source_document is optional source metadata, never a new authority or identity field. Source inspection: turn_events.IDENTITY_FIELDS remains brief_id/run_id/turn_id/attempt_id/input_revision; BriefStore.verify_saved_result also matches session_id and the existing owner dispatch_id/seat_identity_id/launch_attempt/launch_nonce/fingerprint. Preserve the current seal algorithm and owner schema. Tests must exercise a file-origin typed final admission, Retry and replacement briefs with the same frozen source/revision, private API result authority validation, and a legacy stored brief without source_document. These are unit/component seams, not native worker proof.
- W4: reload session_runs.json and verify exact CRLF text plus document metadata. A legacy session without document must reload and build the unchanged brief shape. Invalid source_file at create must consume no session id and leave persistence/brief/queue bytes unchanged (or absent). Internal source_file plus nonempty pasted input_text must fail before effects. Root additionally owns the P1/P2 restart validation and no-child/no-context tests.

Both existing `.session-source-editor` wrappers were verified in static/sessions.js (the ordinary launcher and draft launcher). No wrapper invention is needed; UI implementation remains a later tranche.

Next owner: existing helper writes ONLY new tests/test_document_briefs.py, at most 12 methods, capturing the first two actual failing tests before production wiring. Root writes new tests/test_document_routes.py and restart tests. After observed RED, root implements backend wiring, runs focused/full regression, then requests Sonnet's independent frozen-source review. No UI, native scenario or provider execution is authorized by this test assignment.


## Backend execution checkpoint (review pending)

Observed RED before wiring: helper2 missing source_file keyword errors0.006s; root missing preview error and incorrect newline-only restart failure0.053s. Implemented the agreed backend interfaces, optional document/source_document validation and file-parent restart guard. Existing identity/seal field sets and algorithms were not changed. Root route/restart tests cover both existing Start paths, 512KiB CRLF-heavy JSON, preview auth/query/media/stream bounds, no-effects refusal, and no context/Popen/callback on unchanged restart. Related98 tests passed7.455s; root12 plus existing engine2 passed14/0.995s. Helper brief12 finalization, frozen full regression and independent Sonnet backend review remain required. No UI/native acceptance is claimed.

Helper brief12 finalized PASS0.502s; root document36 PASS1.350s (pure12, brief12, route/restart12). Static syntax and whitespace checks clean. Frozen full discovery and Sonnet independent backend review are next; no UI/native work.


## Frozen backend full regression (builder evidence)

At clean source c60f003, full discovery ran1040 tests in90.431s, OK with4platformskips (1036passed), tracked def71596, retained `.audit-tmp/ticket18-backend-frozen-full.log`. Count cross-check1004+12+12+12=1040. Sonnet independently reviewing frozen backend; no review verdict yet. Next: address findings or obtain bounded backend clearance before the UI tranche. No UI/native acceptance from this run.


## Backend independently cleared

Sonnet bounded PASS at source c60f003 (docs-only d0f440e): own document36 PASS1.411s; related67 PASS3.467s; verify_review_brief, verify_corrected_restart and verify_session_events PASS. Own route probes confirmed size/chunk/media/query/Unicode/auth/Start-tamper refusal with unchanged file effects. Reviewer read builder full1040/4skips90.431s log summary, did not rerun full discovery. Revalidation cost at512KiB is acceptable; no cache is planned. This clears backend only, not UI or native file intake.

## UI behavior freeze proposal (before UI tests/code)

### Facade and source state

Use the existing `.session-source-editor` wrappers in BOTH ordinary and draft launchers. Preserve the current task/cast/recovery controls and product colors, spacing and typography. New static/document-inputs.js loads before sessions.js. No dependencies, new upload store or source rendering.

`DocumentInput.attach(editorElement)` returns one facade per live editor (repeat attach returns the same facade): readonly `.state` in paste|reading|file|error; `.requestFields()` returns a fresh detached object with EXACTLY input_text or source_file; `.setSubmitting(boolean)` disables its source controls; `.dispose()` aborts pending work, invalidates epochs and removes its listeners. requestFields throws when reading, error, submitting or disposed. File mode returns the stored canonical snapshot, never textarea.value. Paste mode returns the exact textarea.value. Dispatch bubbling `document-input-state` CustomEvent with detail `{state, canSubmit}` on meaningful changes so the modal updates Start. The facade owns no run/turn/queue operation.

Initial paste state preserves the current textarea/draft. Add native single-file input and a labelled 'Choose UTF-8 file' action, a 'Use pasted text' action and a plain-text status/metadata region. Accept hint lists the agreed extensions; other extensions remain valid. File picker cancel leaves all state untouched. File selection clears the native input value after capturing the File so the same file can be selected again. More than one supplied file is refused, never silently merged.

On selection cache the current pasted draft, enter reading, abort the previous preview, increment the epoch and disable Start. A valid latest preview enters file, stores its canonical object and shows read-only literal text, basename/title, exact byte size, full content SHA-256 and source_id. The text area may visually normalize newlines; payload still comes from the canonical object. Display the actual line-ending label from that object's text (CRLF, LF, CR or mixed) and a short note that original bytes are preserved. Do not execute, syntax-render, parse Markdown or use innerHTML for file content/name/errors.

A failed NEW selection enters error and keeps any previous preview visible, labelled 'Previous preview, not ready to start'. Start remains blocked; no fallback to the previous file or selected buttons. Show the server's safe validation error (or a bounded generic network/timeout message) plus 'Choose another file or use pasted text. Nothing was started.' Choosing a valid file clears the error. 'Use pasted text' aborts/increments epoch, clears file authority/error, restores the cached paste and focuses its textarea. Picker cancel alone never clears a prior error. A zero-byte file is valid but prominently labelled '0 bytes (empty source)'; a leading BOM shows 'UTF-8 BOM present, preserved'. Both still require explicit Start.

### Fetch, validation and lifetime

POST `/api/documents/preview?filename=${encodeURIComponent(file.name)}` with raw File body, Content-Type application/octet-stream and current X-Session-Token. Client file-size refusal above512KiB is an early convenience; server limits remain authoritative. No client extension gate or text decoding. Eight-second AbortController deadline, monotonically increasing request epoch, disposed and editor.isConnected checks discard stale responses without touching state or Start. Closing/replacing the modal aborts/disposes. No auto retry or Start.

Before accepting a response require exactly the canonical8keys; version integer1, kind file, encoding utf-8, name matches the selected File.name, byte_length integer0..524288 and equals File.size and UTF-8 length of returned text, content_sha256 lowercase64hex, source_id file:lowercase64hex, text string. Invalid shape fails closed; the browser does not duplicate server hashing/provenance validation. Store a detached snapshot and return detached snapshots from requestFields. Timer/abort state must be cleaned on success/failure/dispose; a stale old request cannot remove the newest request's timer/status.

### Both Start paths and draft retention

Both launchSessionWithCast and launchDraftSession read the same attached facade. File payload spreads `{source_file: canonical}` and OMITS input_text; paste payload spreads `{input_text: rawValue}` and OMITS source_file. Preserve goal/cast/recovery/draft/template/channel fields. One Start in flight per captured modal; guard it synchronously before awaiting fetch and disable its Start/source controls. Use a shared small submission/lifetime helper if this avoids duplicating the ownership checks, not a new generic form framework.

On rejection/network failure keep the entire modal, source mode/object, pasted draft, goal/cast/recovery settings and error feedback, unlock controls and permit explicit retry. Never auto retry. Success disposes and removes only the captured modal; a stale response must not close a replacement modal. Closing/replacing the modal calls a single disposal-aware close function; inspect and replace ALL existing remove paths (backdrop, close button, reopening, successful Start). If closed during a Start, the pending request can still have started a run: no automatic resend and no success claim based on a closed modal. Start is explicit, textarea Enter remains a newline, IME never invokes Start, and native button Enter/Space retain native behavior.

### Corrected restart and copy

For file-origin stopped parents add a textContent-only badge 'Original file: {name} ({line endings})'. Keep the full original frozen source readable. Say: 'This restart creates a pasted snapshot. Edit the source itself; changing only line endings is treated as unchanged.' The corrected textarea remains the existing paste editor, no new file picker there. Prepared pasted children have no file badge/source_document. Backend validation remains the authority if stored metadata is malformed; the UI must not invent missing metadata or imply a native file link.

### Layout and accessibility

Operate mode, incumbent app styling. Scope new CSS to the document input component: minimum14px text,12px control inset,44px minimum action targets, min-width0 and anywhere wrapping for filenames/hashes/IDs. Preview stays within the modal at390px with bounded vertical scrolling, preserves literal whitespace and never grows the page horizontally. Empty/BOM/error/reading labels remain visible without opening a secondary dialog. Use associated labels, readonly (not disabled) file preview so it can be selected/copied, polite live status for meaningful state changes, alert for validation failures, and visible focus. Do not move focus when an async response arrives; Use pasted text restores focus to its editor. No decorative animation or unrelated inherited-overflow repair.

### Test ownership and acceptance boundary

After Sonnet confirms this behavior freeze, existing helper owns ONLY NEW tools/verify_document_ui.cjs, bounded12 named Node VM cases. First2 actual RED before frontend edits: missing module/facade and actual ordinary/draft Start payload still reading pasted textarea instead of canonical file fields. Test the actual shared module and extracted real launcher/restart functions at explicit source markers (minimal VM/fake DOM/clock/fetch only); no mirror implementation. Cover exact source/payload key exclusion/noalias, both Start paths, single flight/draft retention, cancel/same-file/replacement error, size/BOM/empty/extension advisory, stale/out-of-order/dispose/8s abort, all close paths, schema refusal, restart badge and script order/accessibility. Root implements UI only after RED. Node results are VM component evidence, not rendered browser or OS picker proof.

Then syntax/diff, existing document/Python regressions and independent frozen UI source/VM review. Native/live-server acceptance requires its own reviewed draft with exact CLI/API invocations and retained-handle cleanup; no process runs under this UI freeze. Browser File/DataTransfer injection must be labelled DOM file-object evidence, distinct from an actual native OS picker. Final browser checks desktop/390px/keyboard/focus/empty/BOM/error/draft retention and both launcher paths. Existing Windows/local-fake/Omarchy/live-provider limits remain.


## UI freeze precisions confirmed before TDD

Sonnet confirmed 11f09bb with five additions. No frontend implementation exists yet.

1. Cache bust new document-inputs.js and bump sessions.js/sessions.css versions in index.html; assert document-inputs.js loads before sessions.js. Existing cached launchers must not keep the old pasted-only payload.
2. BOTH Start functions catch requestFields failures before any POST or submitting transition. Show visible inline feedback: reading -> 'Wait for the file check to finish.'; error -> 'Choose another file or use pasted text.' Keep modal/source/draft and current disabled state unchanged; no uncaught rejection, no fallback payload.
3. Keep the advisory file accept hint, and add 'Other plain-text files: choose All files in the dialog.' A valid .rs/.sql/extensionless File remains acceptable. The hint is not a server or JavaScript extension gate.
4. Source trace confirmed SessionEngine._enrich adds fields to the detached whole session and returns it without filtering input_snapshot.document; get_active and restart_status both use it. Add an actual response/enrichment assertion retaining a stopped file parent's exact metadata, plus VM restart rendering assertions: file parent badge present with literal name/line endings, pasted parent none. Prepared pasted children have none. No nested-key whitelist stripping is needed.
5. Later browser verification uses File/DataTransfer into the real input, labelled DOM file-object evidence, not native OS picker. Include names with spaces/Unicode and literal plus encoded by encodeURIComponent, and an exact512KiB CRLF file. Node VM remains component-only evidence.

All close paths include sendDesignRequest's current modal removal as well as backdrop/header/reopen/success. Disposing an old modal must not affect a newer one or its pending preview. Existing helper may now write only NEW tools/verify_document_ui.cjs12: first2 actual RED (absent facade and real launcher pasted-only payload), then bounded cases. Root starts frontend code after that RED; Sonnet reviews the frozen actual-source/VM package before any separately reviewed live/native acceptance.


## UI implementation checkpoint (VM-only, independent review pending)

Observed first2 actual RED before frontend work: shared module absent; both real extracted Start functions posted pasted textarea fields instead of canonical source_file. Implemented static/document-inputs.js, exact canonical-object file mode, stale/abort/8s preview lifecycle, cached paste/error retention, both launcher Start guards/single-flight/lifetime, all disposal-aware close paths, original-file restart badge, scoped14px/44px controls and12px inset, asset versions/order. Both Start paths omit the other source key. Actual stopped-session route assertion retains exact input_snapshot.document and CRLF.

Helper first expanded12:5PASS/7 fixture failures (standard insertBefore absent, restart fixture missing kind=file). Correcting only those fixtures reached11PASS/1 genuine new-button inset failure; changed only new buttons from10px12px padding to12px all sides. Unchanged actual-source document VM12 then PASS. Existing recipient VM12 also PASS; document Python36 PASS1.426s; syntax/diff clean. VM uses actual shared script and extracted actual launcher/restart helpers with fake DOM/clock/fetch. No browser/DataTransfer/OS-picker/native/provider acceptance is claimed. Full regression and independent Sonnet UI review are next; native/live-server acceptance needs a separately reviewed script/cleanup draft.


## UI review fixes and frozen full result

Sonnet reviewed f139ffb: own documentVM12 and prior recipientVM12 PASS, five JS syntax checks clean, Python document36 PASS1.417s, diff clean. Bounded PASS with two fixes before acceptance, no rendered/native evidence. Builder full at f139ffb completed1040 tests93.707s, OK/four skips (1036passed), `.audit-tmp/ticket18-ui-frozen-full.log`, tracked9c095ea5. Reviewer did not rerun or claim this full result.

F1/F2 actual VM RED:10PASS/2FAIL, arbitrary network TypeError text was displayed and an outside-cast-step select overwrote the assigned role. Added an internal FileCheckError only for explicit server/own validation messages; unknown transport/non-JSON errors now show the generic checked-file failure. Restored `#session-step-cast .session-cast-select` query scope. Asset cache versions updated. Unchanged expanded VM12 PASS, including later JSON SyntaxError/server400/own-schema checks and BOTH actual launcher stray-select checks. No fixture correction/assertion weakening in this fix round. Sonnet short recheck is next.

## Live/native acceptance proposal (design only, no execution)

New verifier tools/verify_document_review.py and a dedicated tools/fake_document_client.py, existing lifecycle/resource utilities reused READ-ONLY (no inherited scenario constructor). Two selectable cases, each isolated data/config/web+MCP/provider ports and retained true server birth handle:

| Case | Input | Primary flow | Exact actual counts |
| --- | --- | --- | --- |
| py | BOM/Unicode/CRLF source, basename with spaces/Unicode/literal plus and .py | CLI reader -> API editor | 1 CLI injection, 1 local fake provider generation, 2 authenticated admitted finals |
| mjs | Exactly512KiB CRLF-heavy UTF-8 .mjs | CLI reader -> API editor | 1 CLI injection, 1 local fake provider generation, 2 authenticated admitted finals |

Both sources contain literal @all, shell-substitution text, script tags and fenced text as source data. Include a valid language statement that would write ONE owned scratch marker if the source were executed; never invoke/import/evaluate it. Assert that marker remains absent throughout. This proves absence of that observed execution side effect, not arbitrary sandbox enforcement. The original source path is fixture-owned and never provided as a server path.

Non-serve path uses actual authenticated raw-byte `/api/documents/preview`, then the same echoed canonical `source_file` Start route (no input_text key). Capture exact original bytes/hash/name/source_id and session/brief references before effects. Add at least25 authenticated no-recipient human chat messages after Start, while the actual hidden CLI holds its turn before fetching the scoped brief. Original selected file is then changed and deleted. Release the exact client gate: actual MCP chat_review_brief returns frozen source/document, authenticated typed final advances to the API seat. Capture the real API request's untrusted source packet and verify source UTF-8 bytes, input_revision and source_document equal the CLI envelope and original bytes/metadata. No parent admission callback, forged boot or invented worker evidence.

Retain true CLI worker/client births and handles before any gate release/control. API response body is gated until true API worker/model births and handles are retained; wait genuine exact model end and existing protocol classification before progression/cleanup. Record genuine typed admission events, exact2 accepted finals and exact1 provider request/CLI journal injection, no hidden extra call. Settings/source/rules frozen; source edits/deletion never re-read by the product.

Each case also creates a separate zero-model HUMAN-only file-origin run on a dedicated channel, Stops it, then exercises the real corrected-restart routes: line-ending-only change refused with no new child/id/queue/process effects; actual content edit creates a prepared pasted child with exact submitted text/hash and no document/source_document. Do not activate that child. This adds zero CLI injections/provider generations and zero accepted results. Record the primary and all secondary run IDs for cooperative cleanup. Pasted legacy behavior stays covered by existing regression; no duplicate native case.

Cheap real HTTP checks before primary Start: agent bearer and no-token preview403; binary/invalidUTF8 and MAX+1 rejected without new session/queue/brief/callback effects; preview self-consistency/tamper Start refusal. Do not add a broad unrelated acceptance matrix. Compile-only compiles every generated server/client variant and starts no processes. Script asserts Windows/local-fake prerequisites and labels platform/provider limits.

### Optional browser modes (separately authorized runs)

Each case may support `--serve` for ONE actual UI Start: py through the ordinary launcher, mjs through the draft launcher. Root explicitly selects the correct channel tab (URL query alone is insufficient). The isolated fixture may expose one operator-authenticated fixed-input endpoint to deliver owned bytes for a browser File object, without arbitrary path access. Browser creates File/DataTransfer into the REAL native input element and dispatches change; this is DOM file-object evidence, NOT a native OS picker claim. Real module must issue the preview request and the operator explicitly clicks Start. Adopt exactly one new session with exact canonical original bytes/hash/name/source_id/cast/channel, not a helper-generated Start. Assert no extra primary run.

READY includes stage/channel/url/case/filename/file-byte endpoint/expected roles/scratch/unique sentinel and bounded600s pre-Start. CLI gates remain held until the browser observes Start success and pulses; no provider body exists yet. After that pulse execute the same25-message/edit/delete/MCP/API assertions and exact counts. Before the one Start, root can inspect desktop/390px, literal source/title/size/hash/identity, BOM and empty warnings, spaces/Unicode/plus encoding, error/failed-replacement/paste restoration, cancel/reselect, hidden picker activation, keyboard/focus and controlled preview failures, all without starting extra runs. Label synthetic DOM key/IME events separately from OS input.

After primary completion, a second READY stage may pause on the stopped HUMAN-only parent (300s, distinct fresh sentinel) for the restart badge and the two actual UI corrected-source actions (unchanged refusal, real edit prepared). Stage2 adopts the single prepared child and validates its exact pasted source/metadata absence; no activation/calls. Keep the non-serve route checks unchanged. No browser actions during gates that require a live model deadline; every model/client remains owned and accounted.

### Cleanup and run discipline

Constructor and main use try/finally; failure writing observations/result must NEVER bypass close. On success/failure Stop EVERY recorded run, release only owned fake-provider response gates, inventory every private launch/config/model intent/client receipt before and after cleanup. Retain exact server/worker/model/client birth handles, distinguish true server from launcher shims. Cooperatively request exact worker stops and genuinely wait all models/clients; NEVER parent-force models or clients. Worker fallback permitted only after fresh complete exact-launch/nonce/dispatch child-end evidence immediately before actuation, else preserve/report unresolved and continue other resources. No PID guessing/process scans/tree kills/global profiles. Every resource count and observed end basis is persisted; unresolved makes the case fail.

Before any process: helper draft -> root and Sonnet source/cleanup review -> compile-only -> frozen hash -> authorize ONE case. Any failure stops the sequence; keep failed scratch/failure.json and report, no automatic rerun or next case. Reviewer reproduces py and mjs independently after builder results; browser modes separately reviewed/adopted. Local fake generation is real local process activity, not live AI/provider/native external-client/Omarchy/remote-cancellation proof. A draft/count promise is not acceptance evidence.


## UI recheck cleared; acceptance draft settlements A1-A6

Sonnet confirmed F1/F2 at c11bdec: own documentVM12PASS, syntax/diff clean. UI is bounded PASS (component/VM/unit), rendered/live/native proof still pending. Reviewer accepts builder f139ffb full1040/4skips93.707s attribution; no rerun after the narrow JS fixes.

Acceptance DESIGN is approved to DRAFT ONLY with these settled requirements, before any script/process execution:

- A1: compare identical original bytes and SHA-256 at every hop: raw preview snapshot, exact Start request echo, run input_snapshot.text/revision/document, actual CLI MCP brief source/input_revision/source_document, decoded actual API untrusted_review_source packet text/input_revision/source_document. Include exact filename, BOM U+FEFF/CRLF/Unicode for py. Persist comparisons before assertions and fail loudly on truncation.
- A2 corrected and confirmed by Sonnet: existing SYSTEM input_revision is trusted turn identity and must remain; content_sha256 equals it. Require exactly one system input_revision equal to original SHA-256. File basename/source_id/source_document/source content and absolute fixture path must be absent from SYSTEM, with file name/metadata/text inside the untrusted user source packet only. Hash is allowed in the existing identity/revision fields. Source execution-marker statements use a relative __file__ sibling (py) / import.meta.url sibling (mjs), with no absolute scratch path literal in the source. Absolute fixture path must not leak into API payloads/public scoped briefs/ledger or captured server/client output logs; private native birth/config evidence naturally retains its ownership paths and is not a public payload. Marker absence is a bounded observed source-side-effect check, not sandbox proof.
- A3: mjs exact512KiB is ASCII+CRLF, so construction cannot split multibyte characters. Budget full preview/StartJSON/MCPbrief/provider request bodies; client MCP read timeout must be well above12s. Do not truncate or silently shorten assertions to fit a transport.
- A4: the25 no-recipient human messages must cause zero recipient wakes and leave the logical run state/turn/invocation identity unchanged; exactly one held CLI injection remains. Monitoring fields may legitimately converge from the real queue events, as in Ticket17, and must not be mistaken for logical advancement. Use exact stable-field comparison and actual ledger-derived monitoring if needed, never ignore unrelated mutation.
- A5: secondary HUMAN-only stopped parent refuses byte-identical text, LF-only normalization and bare-CR variant. Compare file-tree/ledger/id snapshots to prove no child/brief/queue/worker effects on refusal. Genuine content edit creates exactly one prepared pasted child, one consumed id, exact submitted UTF-8 hash, document/source_document absent; no activation or model calls.
- A6: mjs draft-launcher browser mode requires a real draft-message fixture and remains OPTIONAL, with separate authorization only after py ordinary-launcher browser PASS. VM covers draft behavior meanwhile. No implication that a raw URL query selects the channel; click its tab explicitly.

Existing helper next drafts ONLY tools/verify_document_review.py + tools/fake_document_client.py, no changes to old verifiers/source/status, no integration run. Compile-only must start no processes. Root and Sonnet review the complete new script, fake client, imported cleanup shape and hashes before authorizing ONE case; failures stop the sequence and remain recorded. No claim of accepted counts or cleaned resources exists until actual runs.


## Corrected acceptance draft frozen for independent source review (unrun)

Root read the complete initial verifier/client and reused lifecycle close, then requested B1-B4 preflight corrections. Corrected draft: provider/socket construction has its own exception cleanup and starts the provider thread only after other initialization; serve-only secondary edited text/READY/adoption use exact LF while primary canonical and non-serve CRLF remain unchanged; actual pre-primary refusal matrix now checks agent/no-token403, binary/invalidUTF8/MAX+1 and tampered Start with authoritative no-effects/id/runtime snapshots; nested run/child revision+encoding checks are explicit. No product source or prior verifier was changed.

Root verified the corrected source and ran compile-only (2generatedservers/1client/processes_started0); helper syntax/compile-only also clean. Verifier SHA256 fccaf8ca6a37236bebce301f2d2016740d6738c1e3bc88b06c1dd700fb6e1524; fake client f5893f5f94abb6684df0543266676639fd9dc6a7e5898d60b8522f73b28c5eae. No actual case has run. Next Sonnet independently reads full script/client/cleanup before ONE-case readiness authorization. Planned1CLI/1localAPI/2final counts remain assertions to be tested, not evidence.
