# Launcher baseline — ticket #1

Date: 2026-10-12. Scope: read-only comparison of the Desktop installation with the fork, offline characterization, retention decisions, and a bounded implementation plan. Application source has not been changed.

## Baseline and authority

- Fork HEAD during audit: `8a51299c195cabc5f309d6e2ea9991b120e4bd36`.
- Pinned upstream: `d775776a30e8af4c85ea16b3caaf9c79d65cb239`.
- `git diff --exit-code d775776a30e8af4c85ea16b3caaf9c79d65cb239 -- '*.py' 'windows/*' 'macos-linux/*' 'static/*' 'config.toml' 'requirements.txt'` returned 0. Existing application source matches that baseline.
- `STATUS.md` and `docs/agentchattr-fork-spec.md` are already tracked. The existing spec ignore exception was not redone; new exceptions cover only this audit and the dated plan.
- [Fork issue #1](https://github.com/sjgold/agentchattr/issues/1) is **Establish the launcher baseline**, open, with no blockers. Always pass `-R sjgold/agentchattr` to GitHub commands: implicit repository selection returned an unrelated upstream issue #1 during this audit.
- Issue #1 still links a v1.6 snapshot. Local `STATUS.md` identifies v1.7 as authoritative; use v1.7 and its expanded recovery requirements. No issue body was edited.
- On this date the user added Linux/Omarchy launchers to the desired scope and offered testing through Windows or dual boot. This is an additive user requirement beyond the Windows-first wording of v1.7.

## Comparison method and coverage

`tools/audit_launcher_baseline.py` compares allowlisted root source files and text files under `windows`, `macos-linux`, `static`, and `session_templates`. It compares CRLF-normalized bytes, with raw SHA-256 hashes recorded in `launcher-baseline-evidence.json`. It reads the two checked-in `config.toml` files only to identify added agent IDs; it never emits their values. This is a source inventory, not a complete installation backup.

Excluded: `.env`, `config.local.toml`, config backups, environments, caches, history/data/uploads, private docs, and binary media. No source/configuration from the installation was copied. Its source functions were inspected/extracted for disposable fake-input checks; its modules and launchers were not executed.

79 selected paths: **54 equal, 16 different, 2 fork-only, 7 installation-only**. `same` means CRLF-normalized content equality, not byte identity; raw hashes are retained for provenance and can differ for a `same` pair. All existing Windows and macOS/Linux launcher counterparts are equal under that normalization. The machine-readable evidence lists every compared path and both hashes.

### Retain/adapt decisions

| File or group | Observed difference | Decision |
| --- | --- | --- |
| `windows/start_cli_agent.bat` | Installation-only shared Hermes/OMP entry; configured port and finite server poll; `--check` can install dependencies; accepts any HTTP success | Retain shared-entry concept. Reimplement setup/probe separation and app-specific readiness under #2/#4; do not transplant unchanged. |
| `windows/start_hermes.bat` | Installation-only `hermes.cmd` preference and `HERMES_HOME` setup | Preserve client distinction as an optional adapter; platform-specific command resolution belongs in #4. |
| `windows/start_omp.bat` | Installation-only Bun path discovery and OMP wrapper entry | Preserve optional OMP entry. Discovery is a hint, not proof of operation. |
| `windows/start_glm.bat`, `start_muse.bat`, `start_deepseek.bat` | Installation-only API aliases; port 8300/wait loops duplicated; two read a user `.env` | Preserve convenient aliases, routing through a shared API launch path under #3. Use secret references/environment; do not copy user files or baked-in model labels. |
| `test_cli_launchers.py` | Installation-only five YAML/OMP configuration tests | Adapt useful cases into `tests/` under #4. Historical pass count does not prove live readiness. |
| `wrapper.py` | Installation adds YAML writer/mode; fork adds exact executable-based provider defaults and Unix activity provider selection | Port only needed YAML behavior after shape/atomicity/isolation checks; retain newer fork logic. |
| `requirements.txt` | Installation adds PyYAML; fork documents MCP v2 incompatibility | Keep MCP constraint. Add PyYAML only when the optional Hermes YAML integration is implemented. |
| `config.toml` | Installation adds `deepseek`, `glm`, `muse`, `omp`, `hermes` definitions | Add sanitized examples/capability configuration under #3/#4; do not bulk-copy configuration or imply model confirmation. |
| `wrapper_unix.py` | Fork has newer tmux delivery checks and activity handling | Keep fork implementation. Extend/test it for Omarchy; no wholesale replacement. |
| `app.py` | Fork adds subtitle, history framing, scheduling validation, rule errors, presence fix, and removes channel cap | Keep fork; these changes do not require restoration from the installation. |
| `mcp_bridge.py` | Fork adds identity/channel fallback maintenance and removes obsolete rule-limit failure | Keep fork. |
| `rules.py` | Fork removes active/total rule ceilings | Keep fork. |
| `schedules.py` | Fork validates explicit timestamps and one-shot state | Keep fork. |
| `session_engine.py`, `session_store.py` | Fork adds choice-card handling, locking and guarded advancement | Keep fork improvements. They still do not supply the explicit completion/cancellation contracts required by the spec. |
| `static/chat.js`, `static/index.html` | Fork has substantial composer/history/voice/scheduling/UI additions | Keep fork. Porting the installation wholesale would regress newer work. |
| `static/channels.js`, `static/rules-panel.js`, `static/sessions.js`, `static/style.css` | Fork adds channel scrolling, error handling, choice state and associated styling | Keep fork. |
| `archive.py`, `build_release.py` | Fork-only files | Keep. Missing `archive.py` is an installation packaging difference, not a missing-file defect in the fork. Export integration remains to be tested later. |

## Reproduced behavior and ownership

These are baseline characterizations. A passing audit assertion confirms that the observed defect exists; it does **not** mean the product acceptance criterion passes. The Python harness executes real AST-extracted function bodies with fake dependencies, avoiding module startup, providers, timers and native console calls. It does not exercise complete running-process integration.

| ID | Evidence | Reproduced observation | Implementation owner |
| --- | --- | --- | --- |
| E01 | `wrapper.py:38` | Malformed JSON is replaced with a fresh MCP settings document. The problem is generic; OMP merely uses this same writer in the installation. | #4; PF-4, AT-03 |
| E02 | `wrapper_windows.py:410`, `wrapper.py:916` | Fake child exits 23; runner returns `None`. Caller discards runner return and module calls `main()` without exit propagation. | #4 |
| E03 | `wrapper.py:473` | Two queue entries produce one injected prompt; the first job is lost. Queue file is cleared before delivery. | #7; AT-21b |
| E04 | `wrapper_api.py:320` | Two same-channel prompts produce one channel-only handler call. Session prompt fields are never forwarded. | #6/#7; AT-04, AT-21b |
| E05 | `wrapper_api.py:96`, `:247`, `:276` | Handler requests 20 recent messages by default; system message text and attachment metadata are omitted from the captured model payload. The source exposes no model filesystem/tool execution path. | #6/#18; AT-04 |
| E06 | `wrapper_api.py:276` | Fake provider failure prints an error, posts no failure event, then marks the wrapper idle. Engine has no per-turn deadline path. | #12; AT-21a |
| E07 | `session_engine.py:143` | Plain expected-agent status text schedules advancement and resumes a paused session. Existing decision-card guards are present and should be preserved. | #8; AT-05 |
| E08 | `session_engine.py:79` | End updates stored state with no adapter/trigger cancellation call. This check is at the engine boundary, not proof of every process-level consequence. | #10; AT-06 |
| E09 | `session_store.py:324` | Six participants in one phase rejected at max 4; seven roles rejected at max 6. | #16; AT-20 |
| E10 | `static/chat.js:2484` | With Claude/Codex/GLM selected, explicit `@claude review this` is sent as `@codex @glm @claude review this`. Actual composer function evaluated using fake DOM/WebSocket. | #17; AT-09 |
| E11 | Installation `wrapper.py:166` | Candidate Hermes writer preserves a valid mapping/backup and rejects malformed YAML, but replaces an invalid empty `mcp_servers` sequence because of `or {}`. | #4; reject invalid shapes when adapting |

Additional **source-confirmed**, not live-executed findings:

- `windows/start_api_agent.bat:34` and the installed API aliases use a hard-coded port check and unbounded wait; no app identity check. Running them would risk setup/provider side effects, so inspection is the evidence.
- Existing `macos-linux/start_api_agent.sh:42` checks port 8300. Its wait is finite (30 half-second polls), but exhaustion still falls through to wrapper launch. Do not describe Linux waits as unbounded.
- Existing shell launchers delete an incompatible `.venv` with `rm -rf`; replace this with a non-destructive platform environment policy before cross-platform use. Nothing was deleted during the audit.
- `wrapper_unix.py:186` kills a named tmux session before creating one and does not establish process ownership/configuration compatibility. Address reuse/isolation under #4; preserve the newer injection code.
- API startup clears an existing queue at `wrapper_api.py:308`. Restart-safe delivery belongs to #7/#9, rather than a one-line poll patch.
- The original GLM freeze remains **unproven**. E03/E04/E06 establish possible mechanisms, without contemporaneous incident receipts or error logs to attribute that event.

## Adapter matrix and bounded optional-client pass

No `--help`, version command, login, model invocation, server or installed launcher was run. Passive PATH lookup on Windows found OMP, Hermes EXE and Hermes CMD; CodeBuddy was not found. Version, authentication, MCP connection and current readiness remain unknown. The old launcher prefers Hermes CMD; EXE discovery must not override that distinction.

| Client/seat | Historical evidence carried from v1.7 | Current audit | Live acceptance |
| --- | --- | --- | --- |
| Claude, Codex, Antigravity | Demonstrated October 9 participation | Source/launcher comparison only | Not rerun |
| GLM, Muse, DeepSeek direct API | Demonstrated October 9 participation | API adapter unchanged; installed aliases/config absent from fork | Not rerun |
| OMP CLI | Prior Tribunal runs through a different architecture; five older isolated config tests cover OMP/Hermes jointly | Executable found; project `.omp/mcp.json` settings path identified; E01 affects shared writer | Agentchattr interactive operation unverified |
| Hermes CLI | Five older isolated config tests, no complete interactive agentchattr acceptance | Commands found; YAML mode absent from fork; candidate writer characterized in E11 | Agentchattr interactive operation unverified |
| CodeBuddy | Not found in prior audit | Not found on this audit's PATH | Unavailable in this audit environment |
| Other built-in clients | No additional historical claim made here | Existing launchers preserved | Not assessed |

OMP/Hermes diagnostic time box for this ticket is complete at **source/configuration and passive discovery**. No repair loop or live run was attempted. Tribunal lessons in spec section 2 establish the architecture distinction; the private Tribunal implementation/records were not re-audited or imported. Optional clients do not block the demonstrated clients.

Follow-up: under #4, validate real installed command/config contracts in disposable homes with bounded passive probes (15 seconds each), then fake MCP/dispatch checks. Only after an explicit live-test package is selected, perform one bounded interactive session per optional client. If unresolved, publish the exact failing check, mark that client unavailable/unverified, and continue with working clients. Never use a successful help command as authentication or review acceptance.

## Reproduce and review

From the fork root, with Python 3.11+ (audit ran on Python 3.14.6) and Node:

```powershell
python -X utf8 -B tools/audit_launcher_baseline.py --installed "$env:USERPROFILE/Desktop/agentchattr-0.5.0" --output launcher-baseline-evidence.json
node tools/audit_recipient_baseline.cjs
```

The optional E11 check additionally uses already-installed PyYAML. Without it, the harness records that check as not run. The harness uses disposable `.audit-tmp` subdirectories inside this workspace because default sandbox temporary-directory writes failed. Test cleanup is performed by Python; no shell deletion is needed.

Eight existing `test_wrapper_mcp_config.py` tests passed with Python's `tempfile.tempdir` redirected to `.audit-tmp`. Their first run failed on sandbox temporary-directory permissions; rerun passed after that environment-only adjustment. They cover existing settings shapes, not E01 rejection. No dependencies were installed. Full application tests were not run: this interpreter lacks FastAPI, Uvicorn and MCP.

Reviewed pack: the audit, evidence, scripts, plan, agent instructions, status and ignore changes frozen at `fc19bc57daad9373ac9593163ff4fdd179c5a3da`. `META-REVIEW-HANDOFF.md` remains the historical packet reviewed at that revision; it is not regenerated after review. Substantive changes require a new frozen revision and reviewer recheck.

An optional local HTML review surface using agentchattr's existing design tokens was generated under ignored `.lavish/launcher-baseline/`. Lavish's server failed to start; no successful browser review or publication is claimed. The Markdown audit and plan are the durable deliverables.

Builder: Codex / GPT-6 runtime identity; exact provider model ID is not exposed in this session. User requested Luna at Max; no backend identity or reasoning setting is inferred from that label. Reviewer self-identifies as **Muse Spark (Muse family, Meta)**; an exact backend ID was not supplied. Its verdict is **PASS WITH NONBLOCKING NOTES**, reviewing the frozen source/excerpts and captured outputs without repo access or test execution. [Review receipt](../REVIEW-MUSE-TICKET-1.md) preserves the supplied response. The two documentation notes are addressed: normalized equality is explicit above, and evidence metadata identifies separate Node E10 output. No substantive change or reviewer recheck was requested. This is independent source/plan review, not independently rerun acceptance. Seth supplied final sign-off ("ship it") on 2026-10-12; issue #1 is closed as completed.
