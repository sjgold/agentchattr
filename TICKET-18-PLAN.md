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
