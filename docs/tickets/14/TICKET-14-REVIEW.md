# Ticket14 final review pack

State: COMPLETE. Accepted after same-AGY source-grounded recheck and final FULL PASS. Initial report inaccuracies prompted a publication HOLD; source reread, focused72-test re-execution and corrected command/scratch attribution resolved it. Published origin/main4999c39342b85cfafc44bb373ad39cb6e0b57377 and issue14 closure verified. Post-merge806 total tests OK/four expected skips71.794s and syntax/diff pass. Receipt REVIEW-GEMINI-TICKET-14.md.

Base: `9de60a2e9c413dad789a3f06e91682684d74e46f`. Branch: `codex/ticket-14-selected-cli-result`. Frozen implementation: `fc921ca884ba3b63303d8a8489320bf668729bcc`. This receipt pin changes documentation only; evaluate executable source at the frozen target.

Contract: [TICKET-14-PLAN.md](TICKET-14-PLAN.md). Usage: [RECOVER-CLI-MESSAGES.md](RECOVER-CLI-MESSAGES.md). Contract rulings and bounded reviews are in `ticket-14-contract-review` and `ticket-14-foundations-review` under the epic artifacts.

## Review order and boundaries

| Area | Required behavior |
| --- | --- |
| Snapshot and import | Copied read-only snapshots, literal ID0, canonical full-snapshot hash; imported records lose execution claims and always carry imported=True |
| Candidate attribution | Immutable authenticated seat identity, current or retained same-turn source lineage; explicit confirmation for incomplete legacy tags, conflicting tags reject |
| Store transaction | Current checkpoint and global UID single-use; one atomic selected admission plus replacement fence, original source identity retained separately |
| Replay | Exact intent ACK precedes source lookup and later fences; changed intent rejects; projection repair never dispatches another successor |
| Queue lifecycle | Hold before cancellation, identity-scoped unpublished-dispatch audit, existing owner cancellation polling, unaffected peers; truthful settlement only after exact proof and durable writes |
| Native proof | True worker handle versus venv shim, matching CLI child receipt, precise cold absence rules; query performs no process control or lease extension |
| HTTP and UI | Operator-only bounded metadata, no content override, readonly preview, explicit final/question and legacy consent, stable request replay and channel isolation |
| Late output | A selected copy using replacement attempt IDs does not suppress quarantine of that replacement's actual late typed output; true typed duplicates keep existing behavior |

Read `cli_result_recovery.py`, `session_store.py`, `queue_coordinator.py`, `dispatch_queue.py`, `runtime_adoption.py`, then thin engine/app wiring and the UI. Existing API outbox default holds, HMAC authority, hidden console behavior and permanent Stop fences must remain intact.

## Builder verification

- Full discovery: **806 tests, OK with 4 expected platform skips**,73.299s. Published base734 plus72 new tests across10 modules equals806. New modules cover storage10, candidate12, admission12, hold8, CLI proof7, unpublished dispatch3, attachment12, HTTP4, same-boot native handles2 and replacement quarantine2.
- Prior unchanged integrations: turn recovery44.799s, corrected restart30.112s, session Stop21.930s, each exit0. Logs are `.audit-tmp/ticket14-regression-verify_<name>.log`.
- Existing API saved-result lost-ACK integration also PASS: scratch `result outbox integration isfhwjra`, exactly2 provider calls/2 second posts/one admission/projection/ACK, idle peer unused and cleanup unresolved[]. Log `.audit-tmp/ticket14-regression-api-lost-ack.log`.
- Same AGY independently bounded-passed storageb9763b2, candidate8fe4e10, admission2340a90, transport2e10812, engine/HTTPc48b18a and the same-boot handle correction2887184. The last review explicitly excluded UI/tools and the subsequent quarantine correction. Final review must cover those remaining areas.
- Native component tests distinguish actual retained worker handles from supplied child-receipt protocol fixtures and patched cold-probe algorithm inputs. Actual CLI/MCP lifecycle evidence comes from the tool cases below.

## Actual isolated Windows cases

Commands use `.venv-windows/Scripts/python.exe tools/verify_cli_result_recovery.py` with the case arguments below. Every pass uses one local API generation for an earlier accepted result. Attachment makes no provider call or process-control request. Explicit fixture termination is a separate action using existing exact owned lifecycle controls, followed by actual retained worker/client waits and matching integer child receipts.

| Arguments | Scratch under `.audit-tmp` | Outcome |
| --- | --- | --- |
| --case tagged-final | cli selected tagged-final 7bfj2rgf | PASS:1 CLI injection, machine-verified source,1 selected admission/projection, exact replay settles after observed end |
| --case legacy-question | cli selected legacy-question 4pe29lrq | PASS:false confirmation409, literal consent admits operator-attributed question, awaiting_input without Continue |
| --case after-retry | cli selected after-retry ajo5d4hu | PASS:2 injections, real A-to-B Retry, original source A retained, actual B late typed final rejected and quarantined, frozen argv/cwd/profile retained |
| --case tagged-final --stop-before-attach | cli selected tagged-final 50l46tq4 | PASS:Stop then409, source preserved and no selected admission |
| --case tagged-final --serve | cli selected tagged-final za6r12aj | PASS:actual UI final attachment, original stored UI request replayed, native release and cleanup complete |
| --case legacy-question --serve | cli selected legacy-question 6eb9bnjj | PASS:actual UI checkbox/question attachment, original literal-confirmation request replayed, no automatic Continue |

All pass cleanup files report unresolved[]. Normal cases observe3 true workers,1 native client,1 true server and1 retained model end. After-Retry observes4 workers and2 clients. Launcher handles are waited separately, not treated as worker identity. The idle API peer remains ready and unused; both revoked CLI and valid peer bearers receive403 on operator recovery ingress.

Preserved failures, each with clean unresolved[] teardown:

- `cli selected tagged-final 2ua_bi5_`: fixture searched literal Unicode in escaped JSON before ordinary chat/attachment. Exact parsed-text equality replaced that assertion.
- `cli selected tagged-final 7sop0n1_`: content admitted but transport remained unproven after actual exit. Native CLI/API regressions reproduced discarded true-worker handles behind Windows venv shims. Heartbeat now retains the verified worker separately while preserving launcher Popen.
- `cli selected after-retry io6ppxny`: replacement typed output was rejected but not quarantined because selected content shared its attempt ID. A focused red regression preceded the narrow duplicate-suppression correction. The unchanged after-Retry case then passed.

## Browser evidence

Builder artifact: `epics/6e815a47-c25b-4900-9e83-1be98cead36f/artifacts/ticket-14-browser-qa/index.md`.

Actual desktop1280x900 and mobile390x844 inspection verified literal preview, machine/legacy attribution, disabled actions before legacy consent, actual final/question attachment, history/reload replay, Close/Escape and channel hiding. Question Close now focuses the empty answer field. No Continue was submitted. New panel text14px, controls44px, computed primary contrast9.332:1 and no internal horizontal overflow at390px.

Browser Harness had no daemon; the existing Chrome extension supplied the bounded QA session. Screenshot images were visually inspected in tool output without saved portable image paths. Legacy pointer navigation twice opened the existing Guide; keyboard navigation and closing Guide completed the actual tested flow. Inherited whole-page header overflow remains717px at390px for this fixture. Index detector warnings are inherited page findings; index changes only asset versions. No ignores or general page redesign.

## Reproduction

```powershell
.\.venv-windows\Scripts\python.exe -m unittest discover -s tests -q
.\.venv-windows\Scripts\python.exe tools/verify_cli_result_recovery.py --case tagged-final
.\.venv-windows\Scripts\python.exe tools/verify_cli_result_recovery.py --case legacy-question
.\.venv-windows\Scripts\python.exe tools/verify_cli_result_recovery.py --case after-retry
.\.venv-windows\Scripts\python.exe tools/verify_cli_result_recovery.py --case tagged-final --stop-before-attach
node --check static/sessions.js
git diff --check
```

Optional --serve supports tagged-final or legacy-question, with a600s inspection pause. Actual UI attachment is allowed; the script adopts and replays its exact stored request. Pulse `.audit-tmp/ticket14-cli-result-browser-stop.txt` to resume. --compile-only starts no processes.

Limits: actual Windows/local fake API and CLI only. No live provider/native AI-client, remote cancellation, Linux/Omarchy, participant replacement or general imported-message authenticity claim. Selected content admission itself never proves process exit.
