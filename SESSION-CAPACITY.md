# Design limits and the whole team

A phase can include all six selected review members. Packages can contain seven or more seats; the package is an available pool, while a design chooses the roles and turns it needs. The engine executes those turns sequentially and keeps every member of the accepted design.

The coordinator request, proposal and cast editor show the same server-owned limits. Defaults are:

| Limit | Default |
| --- | ---: |
| Roles | 16 |
| Participants in one phase | 16 |
| Phases | 12 |
| Characters in a phase prompt | 1000 |
| Total logical turns | 128 |

Each participant occurrence counts as one logical turn, including output phases and repeated roles. Retry attempts and question/Continue cycles remain within the same logical turn. Full task context and documents belong in the goal/source inputs, separately from the short phase prompt.

An oversized design stays intact with exact validation errors. Start and Save never trim participants, split rounds or shorten prompts. **Read the unchanged proposal** exposes rejected JSON. **Check current limits** revalidates an older rejected draft without rewriting its original message, which is useful after a server policy change.

An accepted run freezes its effective capacity policy. Corrected-source children, continuations and same-turn retries retain it. Old runs lacking a snapshot use the legacy limits of 6 roles, 6 phases, 4 participants, 200 prompt characters and 24 turns fallback when preparing a corrected child; original history is preserved.

## Configuration

Optional partial settings in server configuration:

```toml
[session_capacity]
max_roles = 16
max_participants_per_phase = 16
max_phases = 12
max_prompt_chars = 1000
max_total_turns = 128
```

All values must be positive integers. Explicit limits below six are allowed; the default supports the full team. Total turns must cover the maximum participants in one phase. Safety ceilings are 256 roles, 256 participants, 64 phases, 10000 prompt characters and 1024 turns. Invalid types, booleans, unknown keys and contradictory settings fail configuration validation.

GET `/api/session-capacity` returns the effective `policy`, exact coordinator/editor `limits_text`, and execution information (`mode: sequential`, `active_turns_per_session: 1`). Server validation is authoritative at proposal ingress, Save and Start. Restarting with a smaller policy can reject a new run from an older saved design; existing accepted runs keep their frozen design and policy.

The six-member acceptance uses real app-owned wrappers with a local fake provider. It verifies membership and serial scheduling, not native AI compatibility, external-provider behavior or simultaneous six-way execution. Windows HTTP Selector's 512-socket limit is unchanged.
