# Delivery file-structure cleanup plan

Status: PROPOSED MOVE MAP, no moves executed. Seth authorized cleanup before delivery on2026-10-26. Technical review precedes execution; any deletion or additional functional restructuring needs explicit discussion. Current plan contains NO deletions. Execute in its own commit after backend/UI functional work settles and before delivery.

## Inventory (frozen163b542 tree)

|Class|Observed count / treatment|
|---|---|
|root_python|67|
|root_markdown|114|
|root_scripts|0|
|root_other|11|
|tests_files|234|
|tools_files|56|
|existing_docs_files|3|
|Historical evidence|Root114 Markdown files include36 Ticket20 documents,33 earlier ticket documents,19 reviews and26 entry/guides/handoffs. Largest retained gate document is7.6MB; historical receipts remain intact.|
|Ignored/private working files|.audit-tmp receipts/fixtures, bytecode caches, local venv/data/settings and worktree metadata are NOT delivery content and are not deleted or moved in this pass.|
|Traycer/worktrees|Leave .git worktree pointer and C:/Users/SJG/.traycer managed worktrees, agent logs and artifact comments untouched. This is repository organization only.|

## Proposed layout

```text
README.md, STATUS.md, AGENTS.md, CHANNELS.md  # stable entry points
*.py                                      # runtime imports unchanged
tests/, tools/, static/, session_templates/ # stable existing paths
docs/README.md                              # documentation navigation
docs/guides/                                # operating guides
docs/project/                               # project execution notes
docs/testing/                               # retained test plans
docs/tickets/01/ ... 19/                     # closed plans and reviews
docs/tickets/20/                            # current reduced scope + production ledger
docs/tickets/20/contracts/                  # accepted component invariants
docs/tickets/20/history/                    # reds, deferred proposals, full receipts
docs/history/handoffs/                      # dated handoffs
docs/history/STATUS-2026-10-26.md            # full pre-cleanup status snapshot
```

Keep67 Python runtime modules at their present import locations. This cleanup removes planning/evidence clutter without a package-layout rewrite. Keep root STATUS short: current state, active worktree, accepted/candidate pins, verification limitations, next owner and release constraints; link its full prior snapshot rather than discard history. Preserve current user decisions verbatim in that compact entry point.

## Move mechanics and preservation

- All110 listed files are tracked rename-only git mv operations, followed by link edits. No delete/recreate, squash, branch removal, reset or force push. Validate every resolved source/destination remains inside the intended worktree/docs tree before moving. All changes form one dedicated cleanup commit after git add -A.
- Preserve every red/gate/variance/failed-attempt ledger, accepted contract and code-fenced receipt. Do not change values, hashes, elapsed times, historical command paths or JSON payloads inside fenced evidence. Record a source/destination manifest and hash fenced receipt contents before/after. Git history preserves the original complete files too.
- Snapshot the complete old STATUS into docs/history before shortening the root; label it historical and point to current STATUS. No old status history is dropped.
- Do not clean ignored .audit-tmp or unknown files. No tracked or untracked deletion is proposed. A later disk-reclamation task would need its own exact targets/authorization.

## Reference and import impact

The current .gitignore ignores docs/* except named files. The cleanup commit must add narrow reviewed exceptions for the proposed documentation folders/indexes after checking for unrelated ignored files. This plan itself has an exact named exception; no private ignored content is force-added.

- No Python/test/tool/module/static path moves, so runtime imports, entry scripts, frozen source locations and fixture imports remain stable. Keep CHANNELS at root for existing guide contract checks. The inventory found no operational-guide filename references in Python/JS/HTML/scripts; re-scan immediately before moves.
- Rewrite live relative Markdown links relative to each new parent, including links to unmoved code/spec/guide files. Skip URLs, rootless artifact links and fenced historical commands/receipts. Preserve anchors; route old STATUS historical anchors to the snapshot where needed.
- Update root README/STATUS, current spec, current release contract and relevant script/document pointers. Plain historical filenames in prose/logs remain historical; docs navigation supplies their new locations. Update Traycer entry artifacts to name the new canonical repository paths without moving shared comment threads.
- Build a pre-move link baseline so pre-existing broken historical links are distinguished from NEW broken links. Fix every newly broken live link introduced by the move. No automated rewrite through skills/config/junction directories.

## Verification and delivery boundary

1. Confirm the working tree contains only planned cleanup changes and no active functional edits; capture source/test/tool hashes and the110-file manifest.
2. Perform only the validated moves/link updates; review git diff --stat for expected renames and inspect all non-link content changes. All referenced documents and fenced receipt hashes must survive.
3. Run local link/anchor checks and current-doc navigation checks, compile/import smoke for unchanged runtime modules, and focused guide/root backend tests.
4. Run full discovery on the final combined backend/UI/transcript/cleanup delivery freeze, after cleanup, retaining benchmark target/basic-ceiling facts. This is the final required regression run, not a separate benchmark campaign per Markdown move. Independent review checks the dedicated cleanup diff and final verification before delivery.
5. No activation/push from cleanup. Keep the feature disabled until its separate reviewed activation commit; publication still requires Seth's explicit go-ahead.

## Exact rename map

|Current root file|Target|
|---|---|
|2026-10-12-SESSION-HANDOFF-gpt-6.md|docs/history/handoffs/2026-10-12-SESSION-HANDOFF-gpt-6.md|
|2026-10-18-SESSION-HANDOFF-gpt-6.md|docs/history/handoffs/2026-10-18-SESSION-HANDOFF-gpt-6.md|
|2026-10-23-SESSION-HANDOFF-gpt-6.1-sol.md|docs/history/handoffs/2026-10-23-SESSION-HANDOFF-gpt-6.1-sol.md|
|API-SEATS.md|docs/guides/API-SEATS.md|
|AUTONOMOUS-RUN.md|docs/project/AUTONOMOUS-RUN.md|
|CLI-SEATS.md|docs/guides/CLI-SEATS.md|
|CORRECTING-REVIEWS.md|docs/guides/CORRECTING-REVIEWS.md|
|DOCUMENT-INPUTS.md|docs/guides/DOCUMENT-INPUTS.md|
|EXPLICIT-TURNS.md|docs/guides/EXPLICIT-TURNS.md|
|FROZEN-REVIEWS.md|docs/guides/FROZEN-REVIEWS.md|
|LAUNCHER.md|docs/guides/LAUNCHER.md|
|META-REVIEW-HANDOFF.md|docs/history/handoffs/META-REVIEW-HANDOFF.md|
|OMARCHY-TEST-PLAN.md|docs/testing/OMARCHY-TEST-PLAN.md|
|PACKAGES.md|docs/guides/PACKAGES.md|
|PARTICIPANT-RECOVERY.md|docs/guides/PARTICIPANT-RECOVERY.md|
|QUEUED-TURNS.md|docs/guides/QUEUED-TURNS.md|
|RECOVER-CLI-MESSAGES.md|docs/guides/RECOVER-CLI-MESSAGES.md|
|RESTART-RECOVERY.md|docs/guides/RESTART-RECOVERY.md|
|REVIEW-CLAUDE-TICKET-15.md|docs/tickets/15/REVIEW-CLAUDE-TICKET-15.md|
|REVIEW-CLAUDE-TICKET-17.md|docs/tickets/17/REVIEW-CLAUDE-TICKET-17.md|
|REVIEW-CLAUDE-TICKET-18.md|docs/tickets/18/REVIEW-CLAUDE-TICKET-18.md|
|REVIEW-CLAUDE-TICKET-19.md|docs/tickets/19/REVIEW-CLAUDE-TICKET-19.md|
|REVIEW-GEMINI-TICKET-10.md|docs/tickets/10/REVIEW-GEMINI-TICKET-10.md|
|REVIEW-GEMINI-TICKET-11.md|docs/tickets/11/REVIEW-GEMINI-TICKET-11.md|
|REVIEW-GEMINI-TICKET-12.md|docs/tickets/12/REVIEW-GEMINI-TICKET-12.md|
|REVIEW-GEMINI-TICKET-13.md|docs/tickets/13/REVIEW-GEMINI-TICKET-13.md|
|REVIEW-GEMINI-TICKET-14.md|docs/tickets/14/REVIEW-GEMINI-TICKET-14.md|
|REVIEW-GEMINI-TICKET-16.md|docs/tickets/16/REVIEW-GEMINI-TICKET-16.md|
|REVIEW-GEMINI-TICKET-2.md|docs/tickets/02/REVIEW-GEMINI-TICKET-2.md|
|REVIEW-GEMINI-TICKET-3.md|docs/tickets/03/REVIEW-GEMINI-TICKET-3.md|
|REVIEW-GEMINI-TICKET-4.md|docs/tickets/04/REVIEW-GEMINI-TICKET-4.md|
|REVIEW-GEMINI-TICKET-5.md|docs/tickets/05/REVIEW-GEMINI-TICKET-5.md|
|REVIEW-GEMINI-TICKET-6.md|docs/tickets/06/REVIEW-GEMINI-TICKET-6.md|
|REVIEW-GEMINI-TICKET-7.md|docs/tickets/07/REVIEW-GEMINI-TICKET-7.md|
|REVIEW-GEMINI-TICKET-8.md|docs/tickets/08/REVIEW-GEMINI-TICKET-8.md|
|REVIEW-GEMINI-TICKET-9.md|docs/tickets/09/REVIEW-GEMINI-TICKET-9.md|
|REVIEW-MUSE-TICKET-1.md|docs/tickets/01/REVIEW-MUSE-TICKET-1.md|
|SAVED-API-ANSWERS.md|docs/guides/SAVED-API-ANSWERS.md|
|SESSION-CAPACITY.md|docs/guides/SESSION-CAPACITY.md|
|STALLED-TURNS.md|docs/guides/STALLED-TURNS.md|
|STOPPING-REVIEWS.md|docs/guides/STOPPING-REVIEWS.md|
|TICKET-10-PLAN.md|docs/tickets/10/TICKET-10-PLAN.md|
|TICKET-10-REVIEW.md|docs/tickets/10/TICKET-10-REVIEW.md|
|TICKET-11-PLAN.md|docs/tickets/11/TICKET-11-PLAN.md|
|TICKET-11-REVIEW.md|docs/tickets/11/TICKET-11-REVIEW.md|
|TICKET-12-PLAN.md|docs/tickets/12/TICKET-12-PLAN.md|
|TICKET-12-REVIEW.md|docs/tickets/12/TICKET-12-REVIEW.md|
|TICKET-13-PLAN.md|docs/tickets/13/TICKET-13-PLAN.md|
|TICKET-13-REVIEW.md|docs/tickets/13/TICKET-13-REVIEW.md|
|TICKET-14-PLAN.md|docs/tickets/14/TICKET-14-PLAN.md|
|TICKET-14-REVIEW.md|docs/tickets/14/TICKET-14-REVIEW.md|
|TICKET-15-PLAN.md|docs/tickets/15/TICKET-15-PLAN.md|
|TICKET-15-REVIEW.md|docs/tickets/15/TICKET-15-REVIEW.md|
|TICKET-16-PLAN.md|docs/tickets/16/TICKET-16-PLAN.md|
|TICKET-16-REVIEW.md|docs/tickets/16/TICKET-16-REVIEW.md|
|TICKET-17-PLAN.md|docs/tickets/17/TICKET-17-PLAN.md|
|TICKET-18-PLAN.md|docs/tickets/18/TICKET-18-PLAN.md|
|TICKET-19-ACCEPTANCE.md|docs/tickets/19/TICKET-19-ACCEPTANCE.md|
|TICKET-19-PLAN.md|docs/tickets/19/TICKET-19-PLAN.md|
|TICKET-2-REVIEW.md|docs/tickets/02/TICKET-2-REVIEW.md|
|TICKET-20-22-REDUCED-RELEASE.md|docs/tickets/20/TICKET-20-22-REDUCED-RELEASE.md|
|TICKET-20-A1-VERIFICATION.md|docs/tickets/20/history/TICKET-20-A1-VERIFICATION.md|
|TICKET-20-AUTHORITY.md|docs/tickets/20/contracts/TICKET-20-AUTHORITY.md|
|TICKET-20-CAPABILITY.md|docs/tickets/20/contracts/TICKET-20-CAPABILITY.md|
|TICKET-20-COMPACT-INDEX.md|docs/tickets/20/history/TICKET-20-COMPACT-INDEX.md|
|TICKET-20-CONTRACT.md|docs/tickets/20/contracts/TICKET-20-CONTRACT.md|
|TICKET-20-D4-ADMIT-TAIL.md|docs/tickets/20/history/TICKET-20-D4-ADMIT-TAIL.md|
|TICKET-20-D4-FINAL-FOLLOWUPS.md|docs/tickets/20/history/TICKET-20-D4-FINAL-FOLLOWUPS.md|
|TICKET-20-D4-FINAL-GATE.md|docs/tickets/20/history/TICKET-20-D4-FINAL-GATE.md|
|TICKET-20-D4-LAST-ATTEMPT.md|docs/tickets/20/history/TICKET-20-D4-LAST-ATTEMPT.md|
|TICKET-20-D4-MEASUREMENT-RESULTS.md|docs/tickets/20/history/TICKET-20-D4-MEASUREMENT-RESULTS.md|
|TICKET-20-D4-MEASUREMENT.md|docs/tickets/20/history/TICKET-20-D4-MEASUREMENT.md|
|TICKET-20-D4-PRODUCTION.md|docs/tickets/20/history/TICKET-20-D4-PRODUCTION.md|
|TICKET-20-D4-REDS.md|docs/tickets/20/history/TICKET-20-D4-REDS.md|
|TICKET-20-D4-REMAINING-AND-TAIL.md|docs/tickets/20/history/TICKET-20-D4-REMAINING-AND-TAIL.md|
|TICKET-20-D4-SENTINEL-GATE.md|docs/tickets/20/history/TICKET-20-D4-SENTINEL-GATE.md|
|TICKET-20-DIAGNOSTIC-PHASE-DESIGN.md|docs/tickets/20/history/TICKET-20-DIAGNOSTIC-PHASE-DESIGN.md|
|TICKET-20-DIAGNOSTIC-PHASES.md|docs/tickets/20/contracts/TICKET-20-DIAGNOSTIC-PHASES.md|
|TICKET-20-DIAGNOSTICS-D1-D2-GATE.md|docs/tickets/20/history/TICKET-20-DIAGNOSTICS-D1-D2-GATE.md|
|TICKET-20-DIAGNOSTICS-PROFILE.md|docs/tickets/20/history/TICKET-20-DIAGNOSTICS-PROFILE.md|
|TICKET-20-DIAGNOSTICS.md|docs/tickets/20/contracts/TICKET-20-DIAGNOSTICS.md|
|TICKET-20-LIFECYCLE-BACKUP.md|docs/tickets/20/history/TICKET-20-LIFECYCLE-BACKUP.md|
|TICKET-20-MERGED-DESIGN-CHECKPOINT.md|docs/tickets/20/history/TICKET-20-MERGED-DESIGN-CHECKPOINT.md|
|TICKET-20-OPERATOR-CAPACITY-EXPERIMENTS.md|docs/tickets/20/history/TICKET-20-OPERATOR-CAPACITY-EXPERIMENTS.md|
|TICKET-20-OPERATOR-ROUTES.md|docs/tickets/20/history/TICKET-20-OPERATOR-ROUTES.md|
|TICKET-20-PACKET-VALIDATION-REUSE.md|docs/tickets/20/contracts/TICKET-20-PACKET-VALIDATION-REUSE.md|
|TICKET-20-PLAN.md|docs/tickets/20/history/TICKET-20-PLAN.md|
|TICKET-20-R2-FIXTURE-MIGRATION.md|docs/tickets/20/history/TICKET-20-R2-FIXTURE-MIGRATION.md|
|TICKET-20-R2-N-COVERAGE.md|docs/tickets/20/history/TICKET-20-R2-N-COVERAGE.md|
|TICKET-20-R2-ON-A1-MERGE.md|docs/tickets/20/history/TICKET-20-R2-ON-A1-MERGE.md|
|TICKET-20-REDUCED-BACKEND-REDS.md|docs/tickets/20/history/TICKET-20-REDUCED-BACKEND-REDS.md|
|TICKET-20-REDUCED-PRODUCTION.md|docs/tickets/20/TICKET-20-REDUCED-PRODUCTION.md|
|TICKET-20-STORE-BOUNDS.md|docs/tickets/20/contracts/TICKET-20-STORE-BOUNDS.md|
|TICKET-20-STORE-DECISION.md|docs/tickets/20/history/TICKET-20-STORE-DECISION.md|
|TICKET-20-STORE-SCHEMA.md|docs/tickets/20/history/TICKET-20-STORE-SCHEMA.md|
|TICKET-20-WRAPPERS.md|docs/tickets/20/contracts/TICKET-20-WRAPPERS.md|
|TICKET-3-PLAN.md|docs/tickets/03/TICKET-3-PLAN.md|
|TICKET-3-REVIEW.md|docs/tickets/03/TICKET-3-REVIEW.md|
|TICKET-4-PLAN.md|docs/tickets/04/TICKET-4-PLAN.md|
|TICKET-4-REVIEW.md|docs/tickets/04/TICKET-4-REVIEW.md|
|TICKET-5-PLAN.md|docs/tickets/05/TICKET-5-PLAN.md|
|TICKET-5-REVIEW.md|docs/tickets/05/TICKET-5-REVIEW.md|
|TICKET-6-PLAN.md|docs/tickets/06/TICKET-6-PLAN.md|
|TICKET-6-REVIEW.md|docs/tickets/06/TICKET-6-REVIEW.md|
|TICKET-7-PLAN.md|docs/tickets/07/TICKET-7-PLAN.md|
|TICKET-7-REVIEW.md|docs/tickets/07/TICKET-7-REVIEW.md|
|TICKET-8-PLAN.md|docs/tickets/08/TICKET-8-PLAN.md|
|TICKET-8-REVIEW.md|docs/tickets/08/TICKET-8-REVIEW.md|
|TICKET-9-PLAN.md|docs/tickets/09/TICKET-9-PLAN.md|
|TICKET-9-REVIEW.md|docs/tickets/09/TICKET-9-REVIEW.md|
