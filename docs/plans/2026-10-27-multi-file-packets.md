# Ticket23: multi-file packets, proposal for Seth

State: planning only. Seth authorized this proposal, not Ticket23 product code. Approval and an effort budget are required before implementation. Tickets24-26 remain outside scope.

## Purpose and budget

North Star contribution: after choosing a team in Pre-flight, select several source files once and give every selected reviewer the same named, frozen input. This extends the existing file picker and review session rather than adding another launcher or review engine.

Planning budget:20 minutes. Proposed first implementation slice:90 minutes of agent time, then stop and report tested results and remaining work. That is a proposed checkpoint, not a promise that all multi-file work fits90 minutes. Work beyond that checkpoint needs steering in STATUS Needs Seth.

Seth's priority: "the 6 > the 2 > MultiPackets > 21-22 >23+". The governing requirement is [Post-initial-build: Multi-file packets](../agentchattr-fork-spec.md#post-initial-build--multi-file-packets), currently lines303-305. It requires file-list preview, per-file ids, individual/aggregate caps, no truncation, one shared revision, file-bound quotes, and a new revision when any file changes. These are the acceptance criteria. Suggested numbers and mechanisms below are proposals.

## Existing seams

|Source|What exists today|Consequence|
|---|---|---|
|document_inputs.py:38,76|One UTF-8 file, basename validation, recomputed bytes/hash and exact fields|Reuse validation for every member; paths never become file access authority|
|review_brief.py:15,45,64|512KiB source limit; file or pasted input; frozen source revision|Keep old single-file/paste records readable; define a versioned packet branch|
|static/document-inputs.js:28|Picker explicitly sets multiple=false|Add file-list preview in this existing control, with names rendered as text|
|app.py:3515|Authenticated single-file preview route|Reuse per-file preview before committing a packet; no filesystem crawl|
|artifact_sources.py and review_brief.py|Source validation propagates frozen document metadata through packets/briefs|Trace and update all consumers before switching schema; test both CLI and API payloads|

A source search found no existing mechanical citation validator in production Python. File-bound quote checking therefore needs a small explicit contract; it cannot be described as merely changing an existing checker. Ticket25's wider findings parsing, reviewer UI and synthesis stay excluded; this proposal adds only the membership helper described below.

## Proposed smallest slice

1. Select several UTF-8 text/source files; preview a list showing each name, byte count and stable-in-packet id. Refuse invalid members or over-limit totals before saving. No silent omission or truncation.
2. Freeze an ordered structured manifest containing each entry's id, name, exact text, byte length and content hash. Give the entire packet a canonical revision. Deliver that same immutable packet to each selected reviewer through the existing brief paths.
3. Bind any mechanical quote check to both the packet revision and explicit file id. Look only inside that file, never another file or a concatenated fallback. An unknown file id or wrong revision refuses. A match verifies literal membership in the named file, not whether a finding is substantively correct.
4. Preserve pasted and version1 single-file input, existing sessions, Stop/retry/stale-result rejection, export/import and document authoring sources. No server-side reads of user filenames.

Proposed ids: f1/f2/... in selection order, scoped by the packet revision. Keep each member's existing content-derived source_id as metadata. This distinguishes two equal-name/equal-content selections, which today's source_id alone cannot distinguish. Default proposal: order is part of the packet, so reordering creates a new revision. This is stricter than the specification and remains a Seth decision. Names are labels, never identity.

Proposed encoding: canonical structured JSON for the immutable payload, with a derived readable file index for agents. Do not parse boundaries by searching raw text delimiters. Validate every declared field against the member text. Avoid storing duplicate full text in indexes or summaries.

Proposed first-slice limits: retain today's512KiB per-file limit and propose512KiB aggregate measured as the sum of raw member bytes. The preview shows that exact total. Count metadata and JSON-escape growth against a separate encoded-envelope safety limit, not the displayed source-byte allowance. Pin that envelope limit and its bounded metadata allowance with the versioned schema before code; size it for worst-case escaping of accepted content. An excessive number of empty/tiny files must still refuse explicitly if metadata exceeds its allowance. No silent truncation or invented timing gate. Seth can choose a larger raw aggregate before code.

## Red-first checks

- Two files with the same quoted text: an explicit file-id/revision mismatch refuses; a matching quote is checked only against the requested member. A quote absent from that member never succeeds because it exists elsewhere.
- Change one byte in one member: packet revision changes, every reviewer gets the new revision, and a late result from the old revision refuses.
- Duplicate basenames and duplicate content retain distinct entry ids; rename/reorder behavior matches the approved contract.
- Invalid UTF-8, control bytes, unsafe basename and edited metadata refuse; Unicode, BOM and CRLF survive exact byte roundtrip.
- Per-file/raw-aggregate exact boundaries pass and one byte beyond refuses, including non-ASCII. JSON-escape growth does not consume the displayed raw-byte allowance; the separate encoded-envelope/metadata boundaries are also tested. No partial packet is saved.
- Preview, participant brief, CLI/API envelope, source builder and import/export agree on the exact manifest; no member is missing or silently normalized.
- Version1/paste fixtures remain valid; old sessions resume safely; Stop/retry/recipient/auth tests stay green.
- Actual-JS picker tests exercise list/removal, refused member, escaped names and stale preview results. Existing UI tests remain the first check, without another browser harness or timing campaign.

## Risks and stop conditions

This is a source-schema change across more than one module, not a picker-only tweak. Changing protocol manifests or historical source validation may affect running seats and retained packets. Before code, list all snapshot/brief/source consumers and pin the compatibility rules. If the first slice cannot preserve old records without a migration, stop and ask rather than rewrite history.

Ticket23 delivers ONLY a membership helper: {packet_revision, file_id, quote} -> verified/not verified plus reason. It parses no reviewer findings, adds no reviewer UI, and produces no synthesis. Author-reported filenames alone are insufficient. The eventual Ticket25 review flow can consume this helper later. The exact wire format remains proposed until the contract is frozen.

## Decisions waiting for Seth

- Approve this bounded shape and90-minute agent-time checkpoint (stop and report), or redirect.
- Keep512KiB raw-member aggregate initially, or name the capacity needed for real use.
- Confirm the helper-only file-id/revision contract. Default: order is part of the packet and reordering creates a new revision; choose otherwise if preferred.

Next owner: Codex records Seth's decisions and sends the frozen contract/observed reds for review. No Ticket23 product implementation until scope confirmation.
