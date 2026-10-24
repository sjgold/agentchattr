# Ticket15 final review pack

State: accepted after Sonnet5.5 independent PASS WITH NONBLOCKING NOTES on9f40233/executable1cebd9d. Receipt REVIEW-CLAUDE-TICKET-15.md records independent commands, limits and note dispositions. No executable fixes required. Main merge/post-merge verification/publication/closure are next; then continue under Seth's renewed evening authorization.

Base published main: `55bd7cbea6367b299fc4c927f71cf4736480bd40`. Branch: `codex/ticket-15-participant-replacement`. Executable implementation checkpoint: `1cebd9d4244177fdedd7027f22d101bf1c58381e`. Subsequent verifier header and review receipts are documentation only.

Contract: [TICKET-15-PLAN.md](TICKET-15-PLAN.md). Usage: [PARTICIPANT-RECOVERY.md](PARTICIPANT-RECOVERY.md). Artifact receipts: ticket-15-contract-review, ticket-15-foundations-review and ticket-15-browser-qa.

## Source review focus

| Boundary | Required behavior |
| --- | --- |
| Atomic decisions | Exact failed checkpoint, permanent Stop/corrected guards, original accepted content preserved. Store fence and reserved IDs precede queue or Popen effects. |
| Replacement binding | Fresh distinct identity; frozen effective profile, same role/current and unstarted future assignments. Original cast snapshot, source/rules/design and completed events remain intact. |
| Profile-source preservation | Initial clone never terminates, retries, releases or modifies its selected source seat. Verified CLI fresh selector and resource isolation required. |
| Repair | Failed pre-brief clone only, exact confirmation before local control, actual two-ended exit or synchronous no-spawn evidence, no blind cold Popen. Healthy contexts refuse. |
| Brief authority | ANY persisted brief permanently binds ownership. Pre-brief same-owner persistence replay keeps reserved IDs; post-brief publication gaps become bound stalled turns. No owner/key rewrites. |
| Cold recovery | Interrupted pending replacement waits for explicit operator repeat. Exact repair/replacement replies can be repeated without another launch or generation. |
| Retired transport | Old physical identity held even if dispatch never reached ledger. Exact active consumer receives cancellation; peers/new identities remain usable. Dedicated true worker+child/model proof resolves only after durable ledger completion. |
| Skip | Dedicated skipped_turns record, never admitted_events. One cursor advance; future role remains. Missing notice, structured context, synthesis footer and existing ZIP JSONL preserve audit. |
| Successor repair | Deterministic immediate successor IDs repair brief/enqueue gaps. Consumed questions and advanced turns never reuse those IDs or dispatch again. |
| HTTP/UI | Operator-only bounded unique-key metadata, no profile/content override. Sanitized preview and errors; explicit consent and effective model/role preview. |

Read participant_replacement_store.py, replacement_preparation.py, participant_recovery.py and participant_skip.py, then SessionStore/SeatManager/queue/native helpers, thin engine/app wiring, review_brief and sessions UI. Preserve Ticket9/13/14 default exit/HMAC/queue-hold semantics.

## Builder checks

- Final frozen discovery at fc7ef93:918 TOTAL tests,914 passed and four expected platform skips87.210s. Log `.audit-tmp/ticket15-final-frozen-full.log`, tracked shelld9954f50 exit0. Earlier skip/routes run918/four skips88.791s remains `.audit-tmp/ticket15-skip-routes-full.log`. Published base806 plus112 new tests across16 dedicated modules equals918.
- Focused skip/controller/HTTP/brief checks:44 passed4.167s. Later sanitized can_skip/options guard:15 passed2.751s. Python compilation, node syntax and git diff checks pass.
- New tests distinguish real store/ledger/HTTP effects from explicitly supplied algorithm exit-proof dictionaries, process doubles and native-readiness/delegate seams. Native component supervisor/model tests have their own real Windows witnesses; actual end-to-end evidence follows below.
- Same AGY bounded-PASS: skip8834a8d, clone964d3af, transportb9cd507, controller132e598. Last bounded audit independently ran40/6.461s and95/12.605s; builder frozen901/90.284s was reviewer-log-verified. Reviewer shared-tree task3727 was cancelled, not presented as independent frozen discovery. Final review covers later skip/routes/UI/tools and whole-ticket regression.

Dedicated modules: test_participant_skip_storage, test_prepare_replacement_context, test_participant_transport_hold, test_participant_transport_settlement, test_participant_exit_proof, test_participant_replacement_store, test_replacement_preparation_supersede, test_replacement_preparation_repair, test_missing_participant_checkpoint, test_participant_recovery_engine, test_participant_recovery_faults, test_participant_recovery_options, test_replacement_repair_replay, test_participant_skip_projection, test_skip_successor_question, test_participant_recovery_routes.

## Actual isolated Windows cases

Command prefix: `.venv-windows/Scripts/python.exe tools/verify_participant_recovery.py`.

| Arguments | Scratch in .audit-tmp | Measured result |
| --- | --- | --- |
| --case replace-api | participant replace-api 6rmzxi21 |3 API generations,1 old CLI injection,3 accepted results; distinct clone/current+future roles;4 workers/1 client/3 models/1 true server observed ended. |
| --case replace-cli | participant replace-cli bq9wq49w |1 API generation,3 CLI injections (old1/fresh2),3 results; exactly one fresh selector;4 workers/2 clients/1 model/1 true server observed ended. |
| --case skip | participant skip zwilykuq |2 API generations,1 CLI injection,2 authentic results; missing context/notice/footer/authenticated ZIP export;3 workers/1 client/2 models/1 true server observed ended. |
| --case repair-cold | participant repair-cold cui8g8b_ |Exact synchronous clone Popen fault before OS creation and real failed manifest/no birth; actual server crash/restart1785.788ms, zero cold auto-launch/call before explicit repeat/repair, same reserved IDs;3 API generations/1 injection/3 results;4 workers/1 client/3 models/2 true servers observed ended. |
| --case replace-api --serve | participant replace-api ove1rbs8 |Actual builder UI Replace, original stored request adopted; same counts and native invariants as warm API case. |
| --case skip --serve | participant skip i0noa6tp |Actual builder UI consent/reason/Skip; original stored request adopted, same counts/audit/native invariants as skip case. |

Every case measured zero recovery terminate_owned calls, retained the original source and idle peer, admitted actual typed events, rejected/quarantined actual old CLI MCP late output and ended with cleanup unresolved `[]`. Launchers are accounted separately from true worker/server handles. API models and native clients are never parent-forced; fresh complete child inventory gates any worker fallback. Unknown ownership remains unresolved instead of guessed.

The fake provider response bodies are deliberately gated until native handles are retained. repair-cold uses one exact subprocess audit-hook failure before OS child creation; it is a deterministic local fault seam, not an external provider outage. The cold case proves one fast restart, not every outage duration. No live AI provider/client or Omarchy acceptance is claimed.

## Prior affected integrations and retained failure

- verify_turn_recovery: PASS44.510s, log `.audit-tmp/ticket15-regression-verify_turn_recovery.log`.
- verify_corrected_restart: initial unchanged run failed waiting for a fresh CLI brief, scratch `corrected restart integration k4mzwnry`, log `.audit-tmp/ticket15-regression-verify_corrected_restart.log`. Its current invocation was acknowledged and source packet retained; the fake client's first reads were empty and its prompt was recorded, but no brief/turn-read record appeared before deadline. Cause is unestablished. No production code, fixture or assertion was changed to obtain a pass.
- Independent unchanged reproduction by builder: verify_corrected_restart PASS in `corrected restart integration 5g3zflf5`, log `.audit-tmp/ticket15-regression-corrected-repro.log`, shell93077347 exit0. Final reviewer must reproduce this prior integration and hold acceptance if the timeout repeats or a source defect emerges.
- verify_session_stop: PASS `session stop integration xbcx2yup`, actual API local end142.796ms, quarantine, stale termination409 and confirmed owned CLI termination/peer completion.
- verify_saved_result_recovery --case lost-ack: PASS `result outbox integration v8ktfnqt`,2 calls/2 posts/one admission/projection/ACK; idle peer unused, cleanup unresolved[].

Earlier component failures and fixture corrections remain recorded in TICKET-15-PLAN.md. No new participant verifier case failed or had its assertions weakened.

## Browser scope

Builder artifact `epics/6e815a47-c25b-4900-9e83-1be98cead36f/artifacts/ticket-15-browser-qa/index.md` records actual actions, desktop/mobile dimensions, measured14px/44px controls, contrast9.332:1 panel and8.714:1 buttons, explicit consent gates, channel hiding, Escape handler/focus return and output notice/footer. Screenshots were inspected in tool output, without portable files. Inherited whole-page header overflow710px at390 remains; new panel is contained382/382px. Browser session and both fixture servers are closed.

## Reproduction and final gate

```powershell
.\.venv-windows\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
.\.venv-windows\Scripts\python.exe tools/verify_participant_recovery.py --case replace-api
.\.venv-windows\Scripts\python.exe tools/verify_participant_recovery.py --case replace-cli
.\.venv-windows\Scripts\python.exe tools/verify_participant_recovery.py --case skip
.\.venv-windows\Scripts\python.exe tools/verify_participant_recovery.py --case repair-cold
.\.venv-windows\Scripts\python.exe tools/verify_corrected_restart.py
node --check static/sessions.js
git diff --check 55bd7cb..HEAD
```

Review only the frozen target's source. Record reviewer identity, exact commands/logs/scratch paths, source findings and platform limits. Recheck substantive fixes. Final FULL PASS authorizes the already-approved fast-forward main merge, post-merge checks, push, verified issue closure and status receipt. Then continue the next dependency-eligible ticket under the renewed authorization, with independent review before each publication.

## Final reviewer handoff update

Current reviewer:3b53a0e1-7bc3-4807-bf3a-0d08fa9fea86, Claude/Sonnet5.5 as selected by Seth (harness alias sonnet). Source1cebd9d unchanged;9f40233 and later handoff updates are documentation only. Sonnet independently passed918 total/four skips87.682s, .audit-tmp/reviewer-claude/full-suite.log; source/native/corrected-restart checks remain in progress.

Gemini's completed recent native reproductions:ecsio2tn API, c_59qbq8 CLI,1a1xkjis skip, eachPASS/cleanup[]. Interrupted repair-cold5xphgpv8 has no result orcleanup; nevercountPASS. Root separatepost-stop-audit.json accounts all5launchintents:4spawned workers+nativeclient+2servers verified absent(error87), allactual modelhistories ended/IPC,1syncfailedmanifest/no birth/noinvocations. Original artifacts remain untouched. Sonnet will perform a fresh cold case and prior corrected restart; any findings require recheck beforeacceptance.

## Accepted final review and scope note

Sonnet5.5 agent3b53a0e1 independently ran918 total tests/four skips87.682s and all4 actual native cases plus prior corrected restart/Retry/Stop/APIlostACK, allPASS. Report ticket-15-final-review-claude; receipt REVIEW-CLAUDE-TICKET-15.md. Browser serves/measurements remain builder-only evidence. Full source target9f40233/executable1cebd9d unchanged afterPASS.

Prior-context scope: _trigger_current now takes prior text from immutable admitted_events for all explicit-completion frozen review turns, not just replacement. projected_message_id can be null before projection repair; content remains the durable accepted event. Legacy runs are not redispatched. User guide clarifies future turns on a skipped liveidentity remain held until exit evidence or explicit replacement. Name shadowing and unreproduced malformed-session KeyError hardening are nonblocking deferred notes, not source fixes.
