# Ticket14: recover an operator-selected CLI message

State: proposed contract for same-AGY critique. The choices marked OPEN are not settled. No production implementation or new tests yet.

Base: published main `9de60a2e9c413dad789a3f06e91682684d74e46f`. Branch: `codex/ticket-14-selected-cli-result`. Scope: issue14, specificationv1.7 SC-5 and CLI AT-21c, standing autonomous policy in STATUS.md. Ticket12 blocker is confirmed closed; Ticket13 is published and closed. Same AGY remains independent reviewer.

## Required outcome

An operator selects a specific existing channel message ID, inspects exact text and attribution, then explicitly attaches it to the failed CLI turn. Ordinary chat still cannot complete turns automatically. The server verifies expected seat/instance, channel, available run/turn/input association and duplicate use. Missing legacy turn association is operator-attributed, never machine-verified. Unknown authorship and any known conflicting association are rejected.

If recovery follows Retry, permanently fence the replacement attempt before attaching the selected answer, preserve original source-attempt provenance and commit once under the current logical turn. Stop and corrected/superseded runs remain protected. No model invocation, implicit seat replacement, native termination or source/message rewrite is part of content recovery.

## Source-grounded baseline

- MessageStore.add creates nonnegative numeric IDs starting at0, UUID-string uid, timestamp, sender, text, type and channel. Legacy load can lack uid; get_by_id currently returns an in-memory alias after releasing its lock. Need a copied snapshot for inspect/attach, not a borrowed mutable mapping.
- SessionEngine.send_chat/chat_scope stamps authenticated stable seat_identity_id. Tagged chat additionally has authenticated_dispatch provenance and dispatch/run/turn/attempt/input metadata. Untagged authenticated chat can have known seat identity while missing turn association. Name equality alone cannot prove authorship after identity replacement/rename.
- Tagged stopped/superseded output is quarantined with routing_suppressed. It must not become a recovery bypass. Typed results/questions/operator inputs already have their own protocol and are display-only after Ticket13; candidate selection concerns ordinary CLI chat text.
- SessionStore persists current invocation, frozen participant binding/launch provenance, superseded attempt identity/dispatch/run/turn/input, retry intent and accepted events. BriefStore retains old immutable packets. These are the authority for association, not the live seat name or current provider template.
- Ticket13 provides separate operator admission/projection patterns, exact idempotent ACK, per-seat recovery_hold and native end proof. Its HMAC outbox and API-only result_owner do not authenticate selected CLI chat and must not be relabelled as such.
- Archive import currently forwards supplied metadata to store.add; archive fingerprints are deduplication aids, not authentication. Demotion can replace metadata. Before claiming message provenance, audit import/edit paths and prevent imported or rewritten claims from masquerading as live authenticated ingress. Do not add a general signing/key system without demonstrating necessity.

## Approaches

| Approach | Assessment |
| --- | --- |
| Explicit message snapshot plus dedicated operator recovery ingress | Recommended. Fits durable message IDs, existing atomic admission and coordinator locking; preserves attribution and original text |
| Guess the latest answer or allow normal chat/status to advance | Rejected by SC-5. Cannot distinguish status, wrong input, late output or duplicate use |
| Rewrite selected chat as a normal machine final or relax live-bearer validation | Rejected. Forges protocol/identity and risks routing old text again |

## Proposed operator flow

1. Current failed CLI review offers Recover a message, distinct from Wait, Retry and API saved-answer delivery.
2. Operator selects a nonnegative message ID (including0), receives readonly exact text, source identity/channel, available scope and verification/legacy explanation. No auto-selection of latest message.
3. Server returns a source snapshot key/hash plus current turn/checkpoint identity. Known contradictory fields block attachment. If turn association is missing but authenticated seat is known, require explicit operator-attributed association, never a machine-verified label.
4. Operator explicitly attaches it as a final answer (OPEN: also allow explicit question kind through the existing event model). Request supplies IDs/hash/intent only; content comes from the server snapshot.
5. Under engine RLock, recheck source hash/UID, expected participant lineage, current turn, Stop/Retry fences and global duplicate source use. Persist recovery decision, accepted content and required replacement fence atomically. Cancel/hold exact affected transport separately; peers remain untouched.
6. Project once with routing suppressed, preserve copied text and source metadata. Repeating exact admitted intent resolves an ACK without another turn advance or model call. Transport end remains a separate proof/clear action.

## Decisions for critique

### OPEN1: legacy provenance boundary

Recommended: known authenticated stable seat identity is mandatory. Missing run/turn/input fields may be attached only with explicit operator attribution; all present fields must agree with the selected failed logical turn. Unknown identity, name-only, forged/imported provenance, other channels/jobs, human/API/other seats, typed events and quarantine entries are ineligible.

Verify the source identity against the frozen CLI binding or documented same-turn retry lineage, not the current registry alone. A disconnected original identity can remain a valid source; recovery must not revive its bearer. Determine the smallest ingress/import marking needed so raw imported metadata cannot manufacture authenticated provenance. Existing trusted server data versus untrusted history import must be explicit.

Native UID is preferred for duplicate detection. For legacy records missing UID but with known authenticated identity, settle whether a full canonical snapshot digest can identify the selected source without rewriting history, or whether another explicit migration boundary is required. Existing16hex archive fingerprints alone are not an authentication primitive.

### OPEN2: recovery after Retry and replacement fences

The spec explicitly permits deliberate recovery following Retry, while prohibiting automatic acceptance of superseded work. A source already associated with the same logical turn/run/input and original expected identity may be eligible through explicit recovery, rather than weakening normal event admission.

Recommended minimal direction: validate the current replacement is still current/unconsumed, then atomically fence that replacement and record the operator-selected answer under the current logical turn identity, retaining source attempt/identity separately. Ordinary machine admission must never bypass the new fence. Settle whether consuming/fencing the current attempt in the same operator transaction is sufficient, or a distinct operator recovery attempt is necessary. Do not silently rotate an immutable brief/owner or launch a process.

Also settle preparation-in-progress: pending_retry may reserve IDs before a new brief/identity is ready. Prefer a clear fail-closed state boundary over inventing a new scheduler. Bound replacement attempts already in waiting/stalled/interrupted states must be handled consistently. A normal final versus operator recovery races under the same first-writer engine lock.

### OPEN3: admission audit, duplicate use and source edits

Proposed accepted record includes selected message ID, UID or stable source key, full SHA256 snapshot hash, copied exact content, available source scope/identity/attempt, current target identities, operator request/decision and attribution strength. Scan retained accepted recovery records under SessionStore lock to prevent reusing one source message across turns/runs. Preserve the original message and earlier accepted results.

Inspect returns a copied snapshot; attach binds the reviewed hash and rejects a changed candidate. Freeze copied text at admission so later edits cannot alter the result. Settle message-edit/import provenance and snapshot ordering without nested MessageStore/SessionStore locks. Idempotent replay of an already committed exact decision must not be defeated by a later Stop, Retry or source display edit. Avoid a separate recovery database when one session transaction can record the decision.

### OPEN4: physical seat lifetime

Content recovery must not declare the CLI process or its current replacement ended. Reuse conservative per-seat holds/cancellation under exact dispatch, with explicit original/current attempt attribution. No force kill during inspect/attach. Peers or unrelated verified successor seats remain eligible.

Settle a minimal adapter-neutral extension of Ticket13 hold/settlement for genuine CLI worker plus child receipt/native end proof. API-only HMAC ownership and proof basis cannot be fabricated for a CLI. Confirmed termination remains a separate exact-owned operator action. A fenced replacement transport stays held until genuine release/end semantics settle; never cancel unrelated same-seat jobs.

## Planned interfaces after settlement

Operator-only inspect and attach routes; engine coordination; copied MessageStore snapshot; dedicated SessionStore operator-selected ingress/audit. Exact signatures and field allowlists will be frozen only after critique. Wrong/malformed/stale requests use strict errors, sanitized diagnostics and no provider/control side effects.

UI uses the existing review panel and message IDs with readonly preview, clear attribution and explicit attachment. Do not add participant replacement/skip (#15), general message editing, file intake, source correction or broader channel redesign.

## Observed-red and acceptance plan

- Capture missing inspect/attach interface and ordinary-chat noncompletion baselines before implementation. Separate helper tests from final same-AGY review.
- Exact Unicode/CRLF text and message0; correct tagged source and explicit legacy association; wrong seat/channel/input/run/turn, unknown/imported provenance and duplicate source use reject.
- Source snapshot changed between inspect/attach, concurrent decisions, storage rollback, projection gap, lost ACK and restart preserve one result and audit. No source mutation or fake principal.
- After Retry, old selected answer can be attached only through settled same-turn lineage; replacement late output is fenced, Stop/corrected/superseded runs never bypassed, unrelated envelopes stay intact.
- Real local fake CLI/MCP and isolated app; source message selected through actual UI; exact process/model/injection/dispatch counts, no regeneration from recovery. Native retained handles and complete cleanup; no live clients/providers/Omarchy.
- Same AGY final frozen review/reproduction and post-merge checks before standing-authorized publication/closure.
