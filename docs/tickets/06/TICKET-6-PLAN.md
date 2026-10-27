# Ticket #6: frozen review brief delivery

**Authority:** Issue #6, spec v1.7 SD-1/2 and AT-04/10, plus the 2026-10-22 autonomous execution amendment. No routine human gate. Same Antigravity independently tests/reviews and rechecks substantive fixes before publication.

**Baseline:** Ask/Design and editable draft/cast UI already exist. SessionStore retains only a template ID and truncates goal to 500 characters. The engine rereads mutable templates. API wrappers discard custom turn prompts and depend on 20 recent messages; CLI prompts lack durable scoped source retrieval. Those are the bounded defects here.

## Contract

- Preserve Ask/Design in chat. At Start freeze the accepted template, cast, task brief, pasted source and active rules. Record run ID and canonical design/input/rules revisions. Source text is untrusted plain data and is never executed or routed as chat mentions.
- Default bounds: task brief 32 KiB UTF-8, pasted source 512 KiB, frozen rules 32 KiB, prior results 256 KiB. Reject invalid/oversized input with explicit errors before Start; never slice/truncate. Keep existing role/phase capacity policy unchanged until #16.
- `review_brief.py`: shared freeze/build/format helpers and atomic `BriefStore`. Each dispatched turn has a stable run/phase/turn identity, new attempt ID, intended seat identity, frozen instructions/role/rules/source revisions and relevant prior results.
- Save the scoped brief before enqueue. Queue entries carry only a `review_brief_id` plus concise retrieval instructions. New authenticated HTTP and MCP `chat_review_brief` retrieval accepts only the bound agent identity (browser operator may inspect through authenticated HTTP). Durable source remains available beyond the recent-message window.
- API wrapper fetches the exact brief and builds explicit model messages with frozen task instructions plus a separate untrusted-source JSON message and prior results; recent chat is supplementary. No fallback to chat-only context if scoped retrieval fails. CLI injected instructions request the same scoped brief and treat source as data; do not append live role/rules that override the frozen brief.
- Add pasted source fields to both normal and draft Start dialogs. Preserve entered data if server rejects input. Multiple coordinator-designed structures remain supported; no fixed six-phase flow is introduced.
- #7 will replace lossy queue persistence/batching, #8 completion admission, #9 restart reconciliation and #10 cancellation. This ticket adds immutable brief identity/context and handles typed brief triggers without mixing them, but does not claim durable turn delivery/outbox or cancellation.

## Tasks

- [x] 1. Independent test author writes failing freeze/scope/context tests using real stores and fake agents/providers.
- [x] 2. Implement bounded UTF-8 input validation, frozen snapshots/revisions and atomic brief storage; retain backward-compatible legacy session reads.
- [x] 3. Wire engine, queue and scoped retrieval; freeze template lookups for every phase/expected-agent/enrichment path. Record prior result IDs without changing completion policy (#8).
- [x] 4. Wire API/CLI delivery to the same brief; test beyond 20 messages, wrong identity, malformed/missing brief and no silent fallback.
- [x] 5. Chat Start input/error handling plus strict request validation; preserve Ask/Design and editable drafts.
- [x] 6. Full tests, fake API/CLI delivery integration, rendered Start/rejection checks and static checks. No live providers or native Omarchy.
- [x] 7. Freeze and same AGY independent review/recheck; publish/close on PASS, continue #7.

## Review focus

Mutable template/cast/rule changes after Start; exact Unicode source preservation; unsupported/malformed text and atomic persistence failure; agent identity spoof/re-registration; context retrieval after chat rollover; equivalent API/CLI role/phase/brief/rules/revision; source containing code, mentions and fake operational instructions remains data; no claiming #7/#8/#10 guarantees early.

## Builder evidence (2026-10-22)

- Full Windows suite: 266 tests OK, four Unix/tmux skips. Test author observed missing engine input_text/rules_store interfaces before implementation; helper/store code arrived during its baseline run, so no claim that every helper case was independently red first. Root scoped endpoint test first failed on absent module/route. Malformed/oversized Start, full source/long goal and scope checks pass.
- Real API-to-CLI integration passed by test author and builder. Exactly one local fake-provider request with configured model, frozen rules/goal/role/phase and separate untrusted-source JSON. After 30 system messages plus live design/rule mutation, actual console instructions led a fake CLI through real MCP Streamable HTTP `chat_review_brief`; HTTP and MCP envelopes match. Input/design revisions match both phases; prior API result supplied. Wrong identity403, missing/malformed brief404, API invalid-brief triggers cause no further provider call, oversized Start rejects without persisted run/dispatch, source sentinel absent. First test fixture needed httpUrl/url compatibility correction; no production issue was hidden.
- Existing package integration passed (zero provider calls/session creation). JS syntax and whitespace checks pass.
- Isolated human-only chat browser verified pasted-source field, Ask/Design retained, source rejection400 with 524289 bytes retained in modal, then valid source200 and exact Unicode persisted; no agents/providers configured. Scoped hidden styling fixed inherited template/cast step visibility. At viewport390 dialog width351 fits with no internal overflow; screenshot saved/inspected. Existing background chat header extends document width479, outside this dialog change; no whole-chat mobile pass claimed. Test session ended, browser/server stopped.
- New UI source is plain text; no source code execution or mention routing occurs merely by Start. Legacy sessions retain old behavior, and #7-10 durability/completion/cancellation guarantees remain explicitly deferred.

Published on main at `53a1b9b`; issue #6 confirmed closed after AGY PASS and post-merge 266-test suite (4 skips). Next baton: #7 durable queue, without routine human gate.

Final follow-up checks: two different coordinator designs execute their frozen phase/role orders through actual engine message/timer callbacks. A malformed saved-brief regression failed on list/missing/invalid source shapes; brief reads now validate schema and source revision before returning context. Final suite 266 OK (four skips), real API-to-CLI/MCP integration PASS again, static checks PASS.
