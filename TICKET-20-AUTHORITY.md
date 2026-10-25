# Ticket 20 artifact authority and admission, contract draft

Status: review proposal only, no authority tests or implementation. Store ef7f896 and disabled capability package (product0ade4b7, fixtures7a9226e) are independently accepted. Corrected full1415/four skips215.255s is implementation-owner evidence. Production artifact capability remains empty. Existing review-v1 payloads, brief authorization and saved-result behavior remain unchanged.

## Package boundary and interfaces

| Module | Proposed responsibility |
| --- | --- |
| NEW artifact_protocol.py | Exact artifact-v1 brief/result/ACK schemas, content/parser caps, purpose-separated seals using sealed_result_io.canonical_utf8 and payload_mac. No dispatch or model calls. |
| NEW artifact_brief.py | Private put-once authority records referencing the immutable packet; get-public, managed-API delivery and verify-saved-result paths. Independent artifact schema, not review_brief._validate. |
| NEW artifact_delivery.py | Owned per-launch artifact outbox, immutable save-before-submit, admitted ACK and separate terminal quarantine disposition. Shared bounded JSON/immutable IO and delivery mechanics, no review-v1 schema widening. |
| NEW artifact_service.py | Internal prepare, enqueue repair, claimed brief retrieval, admission, cancellation and startup recovery. Uses existing engine/catalog boundary and queue, no SessionEngine run or new phase engine. |
| agents.py / dispatch_queue.py | Explicit artifact envelope fields at trigger/enqueue, authoritative claim eligibility and unknown-purpose refusal at enqueue/consumers. Ledger load tolerates opaque unknown-purpose rows. |

Proposed ArtifactService internal methods: prepare_request(audit,packet,request_id), resume_request(request_id), get_brief(brief_id,instance), get_delivery(brief_id,instance), submit_cli(brief_id,markdown,instance), admit_saved(record,instance), cancel_request(request_id), fence_source_requests(run_id), recover_startup(limit=100). These are trusted application interfaces, not public routes. Operator authentication, preview-token parsing and HTTP/MCP exposure land in the later routes package. Untrusted callers never supply a frozen audit or observation directly.

prepare_request accepts only an app-resolved frozen audit/packet. The later preview/create path must construct them from one message snapshot under the same outer boundary, verify the preview token there, and freeze exact message ids/uids/hashes/order and source-run/input revision. It shows count/bytes before creation and enforces2MiB/1000 messages plus512KiB authored output without truncation. K6 timing at the source cap remains required before public creation is accepted. There is no API that silently re-derives a packet from current chat at dispatch or recovery.

## Frozen dispatch and brief

The existing request_ids(request_id) yields deterministic packet, brief, attempt, dispatch and version ids. The artifact dispatch has purpose="artifact-v1" and its own dispatch/attempt namespace. Its envelope has artifact_request_id, artifact_attempt_id, artifact_brief_id, artifact_scope_sha256 and channel, with target_identity_id supplied by the existing queue. It has NO run_id, session_id, turn_id or review_brief_id; source_run is audit provenance, never queue cancellation authority. No message text or model-generated routing authority is placed in the envelope.

ArtifactBriefStore path: data/artifact_briefs/requests/<brief_id>.json. Its exact frozen internal body is:

```text
{version:1,purpose:"artifact-v1",brief_id,request_id,lineage_id,attempt_id,dispatch_id,
 packet_id,scope_sha256,expected_parent:null|{version_id,sequence,sha256},
 producer:{identity_id,adapter,launch_attempt,launch_nonce,fingerprint},
 instruction,format,input_revision:null|sha256,source_run:null|source_run_metadata}
```

Ids/hashes and source metadata follow the accepted store schema. Instruction/format match the immutable audit byte-for-byte. The brief references the packet already put once; it does not introduce a second mutable source copy. When delivered, validated packet bytes/content are read from that reference and checked against the audit. A missing or corrupt packet has no chat fallback.

Private `_artifact_seal` is exactly {version:1,seal_secret:64hex,owner:{adapter,dispatch_id,seat_identity_id,launch_attempt,launch_nonce,fingerprint}}. Generate the secret only on FIRST private brief put. An exact frozen-body AND owner repeat reuses the same private record; any changed repeat conflicts before write. The shared immutable IO/kernel-lock pattern is reused. No secret enters the index, audit, queue, log, diagnostic, operator route or UI. Operator projections also omit producer.launch_nonce.

get_brief returns only projected instructions/source and public ids to the exact authenticated assigned seat, omitting producer.launch_nonce as well as private seal authority. The frozen internal body is not a model-facing/public response. It additionally calls queue.owned(instance,dispatch_id): ownership by seat alone is insufficient. Require a nonempty current consumer_id and state dispatched, acknowledged or uncertain; queued, cancelling and all terminal states refuse. Check purpose, every frozen envelope id/hash and request state/attempt. These checks apply on EVERY brief read and ordinary submit. Both later wrapper-purpose branches must recheck this gate before generation or CLI prompt injection, so a durable cancelled request fences a stale queued envelope even if queue cancellation bookkeeping is pending. Existing chat_review_brief checks identity without this dispatch claim, so it must not be reused as artifact authorization.

get_delivery is a managed-API-worker path only: same claim/capability/launch checks, adapter=openai-compatible, then private seal authority is supplied to that owned wrapper. It is never exposed through the model's tool set or the public artifact reader. CLI MCP receives public source only; submit_cli constructs and seals the result on the server after authentication and claim checks. An agent cannot choose an observation, parent, launch ref or request id through that tool.

## Result schema and model observations

The immutable saved record is exactly {payload,seal}. The signed payload is:

```text
{version:1,purpose:"artifact-v1",result_id:dispatch_id,dispatch_id,request_id,
 attempt_id,brief_id,lineage_id,scope_sha256,expected_parent,
 seat_identity_id,launch_attempt,launch_nonce,fingerprint,
 kind:"artifact",markdown,observation:{confirmed_model,confirmation_reason},created_at}
```

Domain separation is INSIDE the signed bytes (purpose), with the distinct exact field schema. HMAC uses canonical_utf8 (ensure_ascii=False, sorted compact JSON, allow_nan=False), never review_brief._revision's ASCII-escaped form. Both directions of cross-purpose submission refuse. Duplicate JSON keys, unknown fields, malformed ids, nonfinite values and invalid UTF-8 refuse. Save/read cap is6*512KiB+32768 bytes to allow JSON escape expansion; decoded Markdown still has the exact512KiB UTF-8 cap, no NUL or lone surrogates, binary CRLF-preserving objects and SHA-256.

API model output must be exactly one structured {kind:"artifact",markdown:string} object, allowing outer JSON whitespace but no fence/extra field. The worker supplies immutable refs, the result-specific completion observation and seal. The requested model comes from the launch snapshot. Confirmed API model comes only from the trusted per-result run_completion return, carried explicitly through the artifact branch; never from a seat-level shared receipt or model-authored field. CLI observation is {confirmed_model:null,confirmation_reason:"cli_model_unverified"}. Review generation/parsing stays unchanged. Wrapper branches and capability enablement are a separate reviewed package.

Invalid API response text is not published as chat. The actual text is passed to bounded quarantine diagnostics (surrogatepass hash/count; invalid UTF-8/NUL hash-only), and a known exact live attempt may be settled as below. Malformed unsolicited HTTP/agent authorization is a refusal, not authority to terminate someone else's request. Transport bodies are capped before parsing; oversized or non-text protocol failures get a safe failure report without pretending a truncated body is the full response.

## Admission and idempotence

Under engine -> catalog -> owner locks, admission rechecks:

1. For first admission, healthy index and referenced packet; actual current request channel active; no pending channel lifecycle hold. Exact existing ACK replay is read-only and may occur on an inactive channel, with healthy saved authority and the same authenticated binding.
2. Exact request/attempt/dispatch/brief/purpose/scope and frozen expected parent.
3. Authenticated seat and queue.owned, its current consumer/state and envelope fields as above.
4. CURRENT artifact_producer result is available and identity_id, launch_attempt, launch_nonce and OWNERSHIP fingerprint equal the frozen audit. The pre-dispatch gate is evaluated again at enqueue/brief retrieval, and result-time C7 recheck is mandatory. A stale wrapper, released/replaced/exited worker or changed source binding cannot inherit earlier eligibility.
5. Valid saved seal/owner, or CLI server-owned construction; valid exact content and trusted observation. Then ArtifactStore.commit_version performs CAS and atomic immutable-object/index commit.

Successful ACK is {status:"admitted",event_id:dispatch_id,request_id,version_id,sha256}. Shared deliver_saved can validate status/event_id unchanged. Admission never releases transport, advances a review, creates a chat message, or triggers another model. Actual queue settlement still needs its existing evidence.

CLI submission and retry first look up the stored dispatch record; an identical repeat reuses its original timestamp/observation/seal instead of constructing a timestamp-changed result. An authenticated identical direct retry of an already admitted dispatch returns its existing ACK without mutation after verifying the same immutable record/content and bound seat. It may read a released queue record for this ACK-only replay; it cannot create a version or revive a terminal request. Different content for that dispatch is a conflicting_duplicate diagnostic, never a version overwrite. An existing admitted version/ACK remains immutable even if later diagnostics arrive. Terminal startup redelivery is DIFFERENT: K4 never admits it or recreates an ACK by guessing, as stated below.

| Submission condition | Diagnostic / request effect |
| --- | --- |
| Unknown request/dispatch | Request-less unmatched_saved_result; no row state or pending-slot effect. |
| Wrong seat/attempt/dispatch/brief/scope/parent, or superseded launch | Corresponding safe diagnostic code (wrong_identity, wrong_attempt, wrong_dispatch, wrong_brief, wrong_scope, wrong_parent, superseded). Diagnostic-only; cannot poison a matching live request. |
| Already cancelled or superseded terminal request | cancelled/superseded diagnostic; terminal state unchanged; no regeneration. |
| Exact trusted live attempt with invalid response/content | Diagnostic first, then set_attempt_state to quarantined/reason invalid_response, freeing its pending slot; fence that exact dispatch. |
| Exact live request with unreadable packet | source_packet_unavailable diagnostic and terminal failed/reason source_packet_unavailable; cannot rebuild/advance that packet. Unrelated requests stay usable. |
| Storage/policy unavailable or durable commit failure | Generic unavailable/503, preserve live state and saved record; no false ACK or quarantine-as-success. |

quarantine_submission itself NEVER changes state. Its matching request+dispatch attachment rule still applies regardless of claimed attempt; service settlement is a separate trusted action and is forbidden for forged/wrong-scope submissions. State changes use expected_state and exact attempt, with terminal reason immutability preserved. A disposition {status:"quarantined",diagnostic_id,reason} is distinct from admitted ACK; the outbox stores that terminal disposition separately and never calls acknowledge for it. Invalid-content records that cannot fit the valid-result schema remain diagnostics, not fabricated signed successful results.

## Preparation, enqueue and recovery

Order: immutable packet -> reserve prepared -> private brief put-once -> enqueue deterministic dispatch -> mark queued/active from the actual queue record. Request replay first calls get_request and uses the existing immutable audit/packet, never refreshed launch settings or current chat. CAS loss may leave one deterministic orphan, reported and never auto-deleted. Fault after reserve/before brief, after brief/before enqueue, and after enqueue/before mark must resume from durable data after a fresh reload.

The enqueue/cancel race is serialized under the same engine/catalog boundary, rechecking live request and capability IMMEDIATELY before enqueue. Queue lock nests inside. No duplicate model work after a claimed/finished dispatch. Recovery uses queue state as authority:

| Existing queue record | Request repair action |
| --- | --- |
| None, live prepared/queued request | Validate same frozen binding/capability and private brief, then enqueue exactly once. |
| queued | Mark queued/reason queued or queued_behind_review, no second enqueue. |
| dispatched / acknowledged / uncertain | Mark active; never enqueue or generate again. |
| cancelling / cancelled | Set request cancelled if still live; never re-enqueue. |
| released / failed / settled_recovered with saved result | Repair a live prepared/queued row to active only after exact frozen queue/brief/result matching, without enqueue; defer saved admission to a separate explicit resume. An already-active row may use the separate recovered-seal path below. |
| released / failed / settled_recovered without saved result | Set live request failed/delivery_unconfirmed; require a NEW explicit request attempt. |
| Any terminal request | No enqueue or generation. Retain readable state; matching admitted direct ACK replay is not startup admission. |

Artifact outbox path is api_seat_runtime/<launch_attempt>/artifact_results/<dispatch_id>.json for either managed adapter. ACKs/dispositions use separate owned subdirectories. Validate the owned snapshot/attempt/nonce/fingerprint before any path use. Artifact and review-v1 files are never scanned as each other's purpose. CLI server-side submission persists its sealed record there before commit; API worker persists before transport. Reuse immutable put/bounded-read mechanics and preserve conflicting objects. No automatic deletion of orphan objects or result files.

Startup runs after stores/policy/service binding and before background workers. It repairs only live prepared/queued requests for enqueue/state repair. Saved-outbox redelivery handles only a LIVE ACTIVE request matching dispatch/request/attempt/brief/scope, private seal, same seat claim record and current verified launch binding. For dispatched/acknowledged/uncertain require the current consumer. Proposed recovery-only exception for released/failed/settled_recovered: require the retained nonempty consumer_id and claim event history, exact sealed record, same LIVE verified producer launch and a still-active request. This is not brief retrieval or permission to claim again. Queue cancellation, request cancellation or a replaced/exited producer still refuses; transport state is never rewritten by admission. It never enqueues, regenerates, guesses a seat or adopts a worker. If current-boot proof/claim is not ready, leave resume pending for an explicit operator resume; no timer retries. One pass assigns each dispatch either enqueue repair or saved-result admission, never both. Work beyond limit100 is reported with count/remaining and resume_pending, not silently dropped.

Unmatched, terminal or cancelled saved records are quarantined/reported without admission. A malformed record with no usable authority ids uses a deterministic diagnostic-only UUID5 derived from its raw-record hash for diagnostic grouping, never a dispatch/enqueue identity; preserve the original file. Diagnostic budgets remain the store's8/group,256groups,1024details,8MiB bodies plus bounded observations. A persisted quarantine disposition prevents startup loops while remaining visible. If diagnostics cannot persist, report unavailable and leave the original record untouched.

## Cancellation and source Stop

cancel_request first persists the exact live request as cancelled/operator_cancelled under the shared boundary, then calls queue.cancel_dispatch using its deterministic cancellation id. Prepared cancellation never enqueues. Queued work is cancelled; active work enters existing cancelling transport settlement. The durable cancelled row is the result/dispatch admission fence even if queue bookkeeping fails. Report cancelled-with-transport-unconfirmed on that partial failure, and retry ONLY that fence, never request creation or generation. Startup may repair these terminal cancellation transport fences in a separate cancellation-only pass; that exception does not permit terminal enqueue or saved-result admission.

The later Stop integration calls fence_source_requests for requests already present with that exact source run, BEFORE recording the source Stop, inside the same outer boundary. Persist their cancelled/source_stopped fences, then stop the engine run and request each exact queue cancellation. A failed Stop can leave those explicit artifact requests cancelled; it must report its actual partial effects. Requests created after the source was stopped record stopped provenance and are normal new requests, unaffected by the earlier Stop. No cancel_run shortcut: current cancel_run only matches envelope.run_id, intentionally absent on artifacts. Late results after a durable fence are quarantined. Session reconcile/restart never adopts artifact work; artifact cancellation never cancels a review or peer lineage.

Cancellation/transport repair and typed release/Stop remain possible while a channel/catalog is held; new prepare/enqueue/first admission require an active channel. Pending artifacts/dispatches become lifecycle blockers with ids in the later integration package. This intermediate component is not enabled or published as a complete artifact feature.

## Evidence packages, after review only

First freeze exact protocol/service helper payloads with Sonnet, then assign at most12 NEW admission methods to the existing helper. Initial observed RED: assigned but unclaimed submit refuses without any version/state effect; exact claimed, sealed artifact result admits once. Root owns protocol/outbox and crash/recovery tests separately. No helper tests before this contract and payload review.

Required coverage: cross-purpose rejection both ways and legacy review golden vectors; wrong/stale/cancelled/superseded binding; claim ownership and cancelling refusal; identical/direct conflicting duplicates; terminal startup quarantine; all queue-state recovery rows and no dual enqueue/redelivery; cancel-before/after-enqueue interleavings with Events; every write/mark crash seam fresh reload; diagnostic-versus-state separation; packet corruption versus unrelated progress; non-disclosure of seal/nonce; parent CAS and independent lineages; exact Unicode/CRLF/size bounds; source Stop selection including a new request after Stop; and unchanged review/runtime/wrapper suites. K6 source snapshot hold measurement is required before public creation.

Native managed CLI, fake API responder and rendered reader/download cases remain later source-reviewed acceptance harnesses under the Ticket19 isolation/cleanup contract. This draft creates no route, MCP tool, worker branch, enabled capability or model invocation.


Review decision requested: approve the narrow recovery-only retained-claim exception above for a sealed saved result whose transport is already released/failed/settled_recovered while its request and exact producer launch remain live. The ordinary brief/submit path remains current-claim-only. If the exception is rejected, these saved results must be quarantined/reported instead; no queue state is revived and no model runs. This is an open contract decision, not implemented behavior.
