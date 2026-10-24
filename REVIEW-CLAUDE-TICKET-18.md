# Ticket 18 independent review receipt

Whole-ticket verdict: **PASS WITH NONBLOCKING NOTES** at reviewed HEAD `f893bd2167c02b3df44faf3c768660a39d9c43b8`. Reviewer final artifact: `epics/6e815a47-c25b-4900-9e83-1be98cead36f/artifacts/ticket-18-final-review-claude/index.md`. Pure/backend/UI, native py/mjs and ordinary rendered browser evidence were independently accepted.

Product executable: `c11bdec1c0d39ec5bfd5aba7cf253821c9f551d4`.
Acceptance verifier: `12c9a81d300f9c1613c74cc856146bbb551b07ca`.
Base published main: `d787f4f79636dbdf8f7f1b9e40c7bc0d34ccc352`.
Branch: `codex/ticket-18-document-input`.
Reviewer: Claude, agent `3b53a0e1-7bc3-4807-bf3a-0d08fa9fea86`, configured alias `sonnet`, self-identifies as Sonnet 5.5. Exact provider backend ID is not independently attested. No tracked implementation edits by the reviewer.
Guide: [DOCUMENT-INPUTS.md](DOCUMENT-INPUTS.md). Current status: [STATUS.md](STATUS.md).

## Delivered behavior

Select one UTF-8 document or source file, inspect literal text/name/bytes/hash/source ID, then freeze its canonical snapshot at Start. Source metadata stays inside the untrusted source packet; existing input_revision identity and result-seal gates remain. CLI and API briefs preserve the same bytes after later chat and original-file edits/deletion. Preview is stateless and operator authenticated; canonical echoes are revalidated at every boundary. Validation establishes self-consistency, not OS-file provenance.

Both existing launchers share the file/paste controls and exactly-one-key Start payload. Drafts survive validation/network errors, failed replacement keeps the prior preview visibly blocked, and stale requests cannot change a new modal. File-origin corrected restart validates the parent first, rejects byte-identical and line-ending-only variants before effects, and saves genuine edits as pasted children. No source execution/rendering, additional tool permission, document library, PDF extraction or multi-file scope.

## Executed evidence and pins

| Evidence | Actual result and attribution |
| --- | --- |
| Pure source405b136 |Builder12pure tests, reviewer12/0.257s plus about65 adversarial probes. No route/runtime claim from those. |
| Backend c60f003 |Reviewer document36/1.411s, related67/3.467s and review_brief/corrected_restart/session_events integrations PASS; adversarial real in-process route probes/no-effects. Builder full1040/four skips90.431s. |
| UI f139ffb/c11bdec |Reviewer actual-source documentVM12, prior recipientVM12, syntax/diff and Python36/1.417s PASS. F1/F2 narrow fixes independently rechecked atc11bdec. Builder full1040/four skips93.707s belongs tof139ffb, before JS-only fixes. |
| py at verifier12c9a81 |Builder xya1ix3_ and reviewer _vutl2yq independently PASS:271B BOM/Unicode/CRLF, SHA75e60e2aefbe89fc47a46acb84004b2157dc5b85fd54cdc89a623d1eda32a5bc; each1CLI/1localfakeAPI/2finals/onepreparedchild. |
| mjs at docs-only0cb367f |Builder31xlrj4l and reviewer s_105vhi independently PASS:524288ASCII/CRLF bytes, SHA0ce106ffa2cb6be80c450e6468b74de635617f85f603dd5545202a587e4a1016; each1CLI/1localfakeAPI/2finals/onechild. Provider body701249B, decodedMCPbrief613052B, builder wall26.863s, reviewer27s. |
| Ordinary py rendered browser at docs-only6aef553 |Builder yv4xw7fp and reviewer3pzw1x48 independently PASS with own browsers. Actual File/DataTransfer input preview, one Start, stopped-parent badge/unchanged refusal/one ASCII prepared pasted child. Each1CLI/1localfakeAPI/2finals; cleanup below. |
| Reviewer full at6aef553 |Own full1040TOTAL/1036passed/4platform skips88.771s, `.audit-tmp/reviewer-claude/t18-final-full.log`; both NodeVM scripts12/0, syntax/diff clean. Documentation descendants do not change these executable pins. |

Every accepted native case and rendered serve run ended2workers/1hidden client/1model/1true server, model basis retained_native_model_handle_observed_end, post-close provider_calls1, unresolved[]. No failure.json or serverlog Traceback/Selector/Warning/Error matches. Secondary human-only runs/children add no model calls. Counts come from actual captures/client journals/admitted events, not planned totals.

Native proof includes all source-byte/hash/metadata views, more than20 later messages with no wakes/logical advancement, original-file edit/delete, strict auth refusals, actual chunked MAX+1 reader413/524289bytes, three unchanged restart refusals/equal effects and one prepared pasted child. Early Content-Length413 may close the unread request with a reset; proof then explicitly uses received status and exact server audit, not a readable JSON body.

New Python modules contain36methods above the1004baseline: document_inputs12, document_briefs12, document_routes12. NodeVM12 is separate from Python discovery. No runtime credentials or scratch histories are committed.

## Rendered scope and explicit limits

Builder desktop1280 and390px screenshots inspected; DOM measurements14px text/12px inset/44px new file-action controls. At390px the modal outer351px/client342px/scroll342px and metadata302px/client=scroll fit internally. Whole-page669px width was measured separately with no pre-ticket baseline attribution. Reviewer measured desktop1280 only; **reviewer390px reproduction was not done**. The existing Start Session button is32px high by source/inherited styling; it was outside the new file-action CSS.

Builder alone checked rendered empty/BOM/advisory-extension cases, failed replacement retention, Use pasted text focus/draft restoration, controlled fetch failure and8037ms timeout. Both browsers used the actual stopped-file parent and live preview/Start chain. Screenshots are output-only low-resolution attachments; geometry is DOM-derived. Hidden picker activation/cancel and IME checks are labelled controlled DOM seams. Native OS picker, native Tab traversal, OS IME and screen-reader behavior are unverified.

**mjs draft-launcher real-browser serve was not run by either builder or reviewer.** It was optional; both launcher functions are exercised in actual-source VM tests, and the draft HTTP Start path is route-tested. The512KiB mjs CLI/API path is independently native-tested. No extrapolated browser claim.

Windows/local-fake only. No live external AI provider/client, native Linux/Omarchy, arbitrary source filesystem authority, remote-cancellation guarantee or sandbox attestation. C1 content controls and trailing Unicode spaces in names follow the explicitly recorded policy. Line-ending-only corrected restart is deliberately unsupported for file-origin parents; start a separate file review for that conversion.

## Resolved findings and failed fixtures retained

Before UI acceptance: new-button inset10px->12px, generic unknown preview-error copy, cast-step selector restored. API seal/identity fields stayed unchanged.

Preflight verifier fixes covered constructor resources, all-run cleanup, known Data startup-line allowlist, stream/reset evidence, pinned policy, compact effect maps, measured counts and browser preview adoption. Draft review attribution: Sonnet ran compile-only and verified specific findings; its read-only analyst audited a full checklist. Do not present that initial method as personally re-derived whole-script review. Subsequent changed diffs were read by the reviewer.

| Failed builder scratch | Actual failure and cleanup |
| --- | --- |
|mwq99nfh at2474c3f |Early413 body reset inside HTTPError handler, before Start;0provider/clientturns;2workers/1client/0models/1server ended/unresolved[]. |
|pgmsqycg at8797d48 |Early auth403 response body reset from unread5byte probe, before Start;0provider/clientturns; same complete cleanup. Empty valid UTF8 auth probes fixed it without relaxing403 checks. |
|7pms_r4i at0118e27 |Final Windows path-key lookup failed after1CLI/1API/2finals and child checks;2workers/1client/1model/1server ended/unresolved[]. Portable map keys fixed it; remains failed fixture, not retroactive acceptance. |

No accepted native cases were rerun on every later docs-only descendant. Final whole-ticket PASS was received and the reviewer verified empty product/tool diffs atf893bd2. Local main was fast-forward merged and post-merge verified. Publication and issue closure were completed under the recorded standing authorization; exact details follow below.

## Final nonblocking notes N1-N7

1. mjs draft-launcher browser serve was not run by anyone; VM and draft HTTP tests cover that path.
2. Reviewer measured1280px only;390px figures remain builder evidence.
3. No OS picker, native Tab, OS IME or screen-reader verification.
4. Existing Start Session button32px, inherited styling outside new44px file actions.
5. mjs observations about8.9MB embed source copies; acceptable, do not grow them.
6. File-parent line-ending-only corrected restart is deliberately refused and documented.
7. Initial acceptance script review combined analyst checklist with the reviewer's verified findings/compile-only; later changed diffs were read personally.


## Post-merge verification

Main fast-forwarded to docs-only `9d874a8e95a6baaca50fbc8bc75fe533cf6e5b74`, source branch retained. Builder full discovery1040TOTAL/1036passed/4platform skips89.765s, exit0; `.audit-tmp/ticket18-postmerge-full.log`, tracked a10ad6a9-5be7-4fb7-a81e-b7220b31c914. Actual-source documentVM12/0 and recipientVM12/0, syntax and full-diff whitespace checks passed. Product/tool diffs fromc11bdec/12c9a81 empty. No native cases repeated for the docs-only merge; their accepted pins remain above. Publication and issue closure are recorded below.


## Publication and closure

Published main `5cac753a9339ed70a26064ee3d561261f7dd66b7`, verified by git ls-remote. GitHub issue18 independently reread via the issue wrapper and precise API: state=closed, state_reason=completed, closed_at=`2026-10-24T10:45:05Z`. Verification comment links the published guide/receipt and preserves the exact limitations and failed fixture history. Closure tracking is docs-only; productc11bdec/verifier12c9a81 remain unchanged. No new native rerun is claimed for this metadata descendant.
