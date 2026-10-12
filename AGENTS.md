# Agent instructions

## Source of truth

- Root `status.md` is the source of truth for the project's current state, status, and next step. Read it before starting work and when resuming a session.
- Read `docs/agentchattr-fork-spec.md` when working on product scope or implementation. Use the specification version identified in `status.md`.
- If code, tickets, or other documents conflict with `status.md`, verify the actual state and reconcile the discrepancy. Do not silently carry stale claims forward.

## Keep status current

- Maintain `status.md` as work progresses: record meaningful changes in scope, decisions, completed work, verification results, blockers, and handoffs.
- Before ending a work session, ensure it accurately describes the current state and the next concrete action, its owner (or unassigned state), and completion criteria.
- Update the `Updated` date and summary when changing status. Preserve relevant context; replace stale current-state statements rather than adding contradictory updates.
- Include the status update in the same commit and push as the project changes it describes whenever committing or pushing is authorized.
- Distinguish planned, implemented, tested, and independently reviewed work. Record what was actually verified and any remaining limitations; never present intended behavior as shipped.
- If the next step has not changed, preserve it explicitly. Documentation maintenance alone does not authorize starting the next implementation task.

## Working practice

- Keep changes bounded to the user's request and preserve unrelated work.
- Follow the current scope, review requirements, and operating constraints recorded in `status.md` and the specification; avoid duplicating volatile project details here.
- Run verification appropriate to the change and record the outcome in `status.md`. Documentation-only changes need a content/diff review, not application tests.
- Keep credentials, runtime history, and local settings out of source control. Changes to another installation or usage-consuming live acceptance require authorization within the requested scope.
- Leave a handoff that another agent can resume from `status.md` and the linked specification.
