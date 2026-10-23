# Ticket #16: support the whole selected team

**State:** Proposal for same-AGY contract critique, before implementation or test assignment. Builder Codex; independent reviewer remains agent ec1fbcd1-4a02-410e-9029-e498f67918c8. Base main `ee52c32dfb24b926d84375dbe4a8fb35558f08c5`. #12 is independently passed, published and closed. Seth's standing autonomous authorization replaces routine human gates.

## Scope and observed problem

Specification v1.7 SD-1/AT-20 and approved issue#16 require one configurable policy for coordinator, editor and backend; all six selected seats in one phase; seven-seat package representation; explicit phase/prompt/total-turn bounds; no silent redesign or membership pruning. This is whole-team product capacity, not acceptance above Windows Selector's512-socket limit.

Current `validate_session_template` in session_store.py hardcodes six roles, six phases, four participants and200 prompt characters, with no explicit total-turn ceiling. app.py's coordinator request separately repeats those constants. review_brief.freeze_inputs invokes that validator, so merely changing proposal parsing would still fail Start. SessionStore.save_custom_template does not independently validate. Existing packages accept seven seats without a six-seat ceiling; preserve that behavior. Existing engine walks every phase participant sequentially, which should already schedule six turns once validation permits them. Verify actual scheduling rather than assuming it.

## Proposed design and choices for critique

1. A small `session_capacity.py` defines validated positive-integer settings and canonical public policy/description. Configure through `[session_capacity]`, with no live local settings edited. Proposed defaults: max_roles16, max_participants_per_phase16, max_phases12, max_prompt_chars1000, max_total_turns128. These are builder proposals, not user-selected or ratified values. Reject booleans, non-integers, unknown keys and impossible combinations. Decide whether a policy below six members should be allowed as an explicit configured operator restriction or rejected as incompatible with the milestone.
2. Publish the effective policy at an operator-readable session capacity endpoint. Coordinator instructions derive from it; proposal/cast editor shows the same limits and backend validation messages. Server validation remains authoritative for incoming agent drafts, save and Start. A stale proposal is revalidated against current policy before a new run; never clip lists/prompts or automatically split rounds. Keep the full proposal visible with errors.
3. Pass policy explicitly through SessionStore, validate_session_template and freeze_inputs. Store an immutable capacity_policy snapshot with each accepted run. Later config changes cannot alter an active run, continuation, same-turn Retry or corrected-source child retaining its frozen design. Legacy runs without a snapshot retain existing read-only safety; no process adoption or forced design rewrite.
4. Total turns means sum of participant occurrences across phases in the accepted design, including the output phase. A role repeated in different phases counts each time. Retry generations and question/Continue attempts do not add logical design turns. Do not introduce a separate round format. Preserve existing duplicate/role semantics unless a correctness defect requires a narrowly justified rule.
5. Keep execution sequential with one logical session turn active at a time. Membership and design limits are separate from execution concurrency. No new parallel scheduler, queue batching, role removal or package truncation. Seven-seat package save/list/selection remains representable even when a particular design exceeds its declared run policy; rejection names the actual design limit.

Alternatives: raising scattered constants leaves policy drift and no shared validation; moving validation solely into JavaScript permits invalid machine/API ingress. Prefer the server-owned module plus public snapshot with the existing serial engine.

## Bounded work and proof

1. After critique settles interfaces/defaults, assign existing test helper red tests for six-role phase, seven-seat package, each exact boundary/one-over error, total-turn counting, policy validation/snapshot and direct save/Start validation. Capture actual red before production.
2. Implement policy/config/publication and connect every validation path. Update the older test that explicitly preserves pre-#16 numeric ceilings, retaining meaningful new-limit boundary assertions rather than deleting coverage. Verify invalid designs fail before session persistence, queue enqueue or provider calls.
3. Add shared policy display to existing proposal/cast surfaces and derive coordinator instructions. Preserve current UI style and input drafts. Use exact server error text; no separate browser-only numeric authority. Expose short phase prompt versus full task/source fields clearly.
4. Real isolated fake-client integration saves a seven-seat package and executes a six-member phase through explicit typed finals. Prove six distinct expected identities/briefs/dispatches and exactly six accepted results in order, no skipped members, no extra model calls. Verify bounds via actual coordinator request context, editor/API response and rejected Start with no run/dispatch. A serial schedule is sufficient; do not claim simultaneous execution.
5. Run focused/full suites, all prior integrations appropriate to shared template/brief changes, JS/diff checks and bounded desktop/phone/keyboard verification of the policy/error surface. Freeze for same AGY's independent review/recheck. Publish/close only after PASS, then proceed to #9 under the documented milestone order.

## Open contract questions

- Ratify bounded defaults and explicit low configured capacities versus milestone minimums.
- Ratify turn-count semantics and frozen-policy inheritance for corrected children/legacy packets.
- Settle API/editor policy snapshot shape and stale-policy behavior without silent edits.

No implementation, native AI/provider call, external install, global event-loop change or capacity claim has been made for #16 yet.
