# Ticket13 final independent review pack

State: implementation and builder verification complete; same-AGY final verdict pending. No Ticket13 publication or closure yet.

Published base: `2bdbc777b5ab8e254b36e54cd784a469d02720b4`. Branch: `codex/ticket-13-api-result-outbox`. Frozen implementation hash is recorded in the following documentation-only review pin.

Contract: [TICKET-13-PLAN.md](TICKET-13-PLAN.md), same-AGY contract artifact Sections7.3/7.4 and lifecycle refinements. Usage: [SAVED-API-ANSWERS.md](SAVED-API-ANSWERS.md).

## Review focus

| Area | Required boundary |
| --- | --- |
| Outbox and private brief | Exact schema/canonical HMAC, immutable launch/brief ownership, atomic saved file before post, separate stable ACK; private key never enters model/public output |
| Authority after crash | Original verified saved identity and operator attribution, no revived bearer/fake live principal; exact admitted ACK before later fences, pending Stop/Retry/correction conflict |
| Content versus transport | Durable seat hold before unproven admission; unrelated seat remains usable; exact true worker plus model end proof before internal settlement |
| Hold lifecycle | Original consumer can poll cancellation, ordinary release retains hold; proven released hold settles; cancelled hold clears without rewriting Stop state/ID/receipts |
| Persistence gaps | Admission/projection/ACK/queue failures preserve history and retry idempotently; no second generation, duplicate event or blind successor dispatch |
| Routing | Typed final/question/operator-continuation projections retain literal text and broadcast only, including legacy projections lacking metadata; ordinary chat routing still works |
| UI | Verified readonly preview, explicit delivery, channel isolation, keyboard/history/reload access; no automatic delivery or Retry |

Read `result_outbox.py`, `review_brief.py`, `result_delivery.py`, `result_recovery.py`, `session_store.py`, `dispatch_queue.py`, `runtime_adoption.py` and their thin app/engine/worker wiring. The shared Windows lock correction and immutable post-brief retry authority guard are included in this ticket. Existing hidden CLI startup and Ticket9 native proof rules must remain intact.

## Builder checks

- Full discovery: **734 tests OK,4 expected platform skips**,68.060s after the routing correction. Base630 plus103 new tests across13 modules and1 launcher regression gives734. JavaScript syntax and diff whitespace pass.
- Native/ledger/core recovery boundary tests include real retained Windows worker/model handles, cold algorithm seams labelled explicitly, actual atomic replace failures, concurrent storage and five concurrent engine deliveries.
- Prior unchanged integrations pass: session events12.830s, turn recovery45.008s, corrected restart28.579s, review brief13.763s, dispatch queue12.356s. Logs `.audit-tmp/ticket13-regression-verify_<name>.log`; each script's final result is PASS.
- Same AGY independently bounded-passed5f2ce30,65060b5,f5049cf,67feb33,d75f90f. Those are component verdicts, never final13 acceptance. Frozen versus evolving shared-tree counts are distinguished in `ticket-13-foundations-review`.

## Actual worker evidence

All commands use `.venv-windows/Scripts/python.exe` and fresh isolated data/ports/local fake HTTP providers. Each successful recovery case has exactly2 provider generations, one prior accepted result, one second admission/projection when delivered, and zero regeneration during recovery. Cleanup reports unresolved[] unless explicitly identified below.

| Check | Scratch under `.audit-tmp` | Actual outcome |
| --- | --- | --- |
| Unwired worker baseline | result outbox integration 4p0fj60e | Expected failure:3 posts without a saved file |
| Save-before-post | result outbox integration r7hsjjtw | PASS: signed file before3 failed posts, first ACK/second no ACK, actual MCP/provider/public key redaction |
| Cold final | result outbox integration jtk87m67 | PASS:1810.138ms HTTP restart, original identity, stable ACK and proven settlement |
| Cold question | result outbox integration dvuo315i | PASS:1807.650ms restart, awaiting_input without Continue |
| Lost ACK before routing fix | result outbox integration c82urfgs | FAIL: real admission/projection then503 and duplicate409 succeeded, but quoted @all caused a third peer request |
| Lost ACK after fix | result outbox integration tibjary1 | Unchanged PASS:2 calls/2 posts, one event/projection/ACK, peer never invoked |
| Pending Stop | result outbox integration wgfrj1p2 | PASS:409/no second admission/no ACK, saved bytes retained |
| Actual browser delivery | result outbox integration 8pc_o_1b | PASS:1798.399ms restart, actual UI delivery followed by idempotent script posts,2 calls/one second event/projection/ACK |

Scratch names above have a space between `integration` and the final suffix. Each completed case preserves result.json, posts.json and cleanup.json; cold cases also preserve the final pre-crash snapshot and observed original worker/model exits. The earlier failure remains a failure. Its cleanup initially reported an unproven extra peer model; separate post-cleanup-audit.json preserves that original file/hash while later genuine per-dispatch exit0+IPC journals prove both histories ended. The extra model is not attributed as a parent-retained native wait.

The routing failure was reproduced before its fix with a real callback regression: one typed final changed the real ledger from2 to3 records. Four tests now cover genuine successor versus extra chat dispatch, typed command suppression, projection metadata and unchanged ordinary chat. Content is never stripped or normalized.

## Browser evidence and limits

Builder inspected actual Chrome at1280x900 and390x844 through the available browser extension after Browser Harness lacked a live daemon and the separate CLI driver lacked its local dependency. No installs or user-browser security changes. One batched adjustment prioritizes the pending answer and temporarily hides alternative review panels; Close restores them and Stop remains available.

Computed new panel text14px, padding12px20px, controls44px. Text/primary control contrast9.332:1; secondary control8.714:1. At390px the new panel's scroll width equals client width; the pending delivery control was visible at y514..558 after the adjustment. Keyboard Close/history Enter, reload/history access, actual Deliver acknowledgement and channel-change hiding were observed. The browser connection detached once before the first delivery click; a fresh task tab completed the actual action. Screenshot images were inspected in tool output, not persisted as portable screenshot artifacts.

Inherited whole-page header/composer overflow remains (document width546 at390px); no full-page responsive repair is claimed. Mechanical detector reports16 inherited index findings, none on the new JS/CSS targets; index markup changes only asset versions, global styles remain unchanged. No blanket ignores were added. The two small labels are inherited Channels10px/To9px; padding warnings lack usable selectors.

## Reproduction

```powershell
.\.venv-windows\Scripts\python.exe -m unittest discover -s tests -q
.\.venv-windows\Scripts\python.exe tools/verify_result_outbox.py
.\.venv-windows\Scripts\python.exe tools/verify_saved_result_recovery.py --case cold-final
.\.venv-windows\Scripts\python.exe tools/verify_saved_result_recovery.py --case cold-question
.\.venv-windows\Scripts\python.exe tools/verify_saved_result_recovery.py --case lost-ack
.\.venv-windows\Scripts\python.exe tools/verify_saved_result_recovery.py --case cold-final --stop-before-delivery
node --check static/sessions.js
git diff --check
```

For optional browser reproduction, `--case cold-final --serve` pauses for600s. Browser may Deliver; subsequent script delivery is idempotent. Pulse `.audit-tmp/ticket13-saved-result-browser-stop.txt` to resume cleanup. Query channel is descriptive; choose the outbox-run tab. No other test scenarios are implicitly authorized by that pause.

Recorded limits: Windows/local fake providers only; no live AI, native Omarchy, CLI selected-message recovery, participant replacement, remote compute cancellation or backup/export acceptance.
