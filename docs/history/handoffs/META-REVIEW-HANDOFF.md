# Meta review handoff — agentchattr ticket #1

You are the independent different-family reviewer of a baseline audit and bounded Stage A plan. This is a manual handoff from Seth; no API call was made by the builder.

Configured reviewer label found in the existing installation: Meta `muse-spark-1.3-contributor` at `https://api.meta.ai/v1`. Record your actual model identity if exposed; do not assume that this configuration proves the identity of your current session. Seth selected Meta and said its quota is good. Builder runtime identifies itself as Codex / GPT-6; the exact backend ID is not exposed. User requested Luna at Max; the builder did not verify that label against the backend.

## Review target and rules

Review the frozen evidence and plan below. No application implementation is included. Do not write code, contact services, launch agents, or declare live acceptance. Source excerpts preserve local code with line numbers added and trailing whitespace omitted for display; their hashes bind the original reviewed files. You may request missing evidence. Do not approve a claim you cannot verify.

Review these questions:

1. Is the comparison appropriately bounded, with secrets/history excluded and useful local launchers identified? Are retain/adapt decisions supported by the supplied source and diffs?
2. Do E01-E11 follow from the real source and reproducible harnesses? Distinguish source inspection, extracted-function tests, integration tests and historical incident attribution. A passing characterization confirms existing behavior, not a fix.
3. Does the plan keep newer upstream behavior, avoid blind transplantation, and respect #1 -> #2 -> #4 and #3/#4 -> #6 dependencies? Does it avoid duplicating the durable delivery contract?
4. Are JSON/YAML preservation, atomic backup/replacement, exit propagation and cleanup cases concrete enough to implement and review? Flag any incorrect suggested contract or unsafe omission.
5. Do Linux/Omarchy requirements cover equivalent API/CLI aliases, non-destructive platform environments, actual tmux status/ownership and honest Windows-hosted versus native testing?
6. Is the next step truthful and executable? Identify any blocker to treating #1 as technically reviewed, while preserving human final sign-off.

## Required response

Return `PASS`, `PASS WITH NONBLOCKING NOTES`, or `CHANGES REQUIRED`. For each finding give severity (blocking/nonblocking), file/section or evidence ID, the precise unsupported claim or failure, and the smallest correction/reproduction required. List what you could not verify. Record actual reviewer model ID if available and whether you executed anything. Do not use a matched snippet as proof of complete runtime behavior. The builder must address findings; substantive fixes require your recheck. Only Seth supplies final completion sign-off.

If you lack repo access, review the supplied frozen source and captured outputs, but state that the test commands were not independently executed.

## File manifest

Hashes below identify the exact supplied documents/scripts/source. The eventual commit containing this handoff is the review revision; resolve it with `git log -1 --format=%H -- META-REVIEW-HANDOFF.md`.
- `AGENTS.md`: `6162bc2a5b14fe5fb50a5abe98fbc75390bd19194caa567e1c536fdcbd303b15`
- `docs/launcher-baseline-audit.md`: `90e2abc7675e670c1297bc303212c4efdb148ef1b83eb7fb7a52f9f869026471`
- `docs/superpowers/plans/2026-10-12-stage-a.md`: `0e384b6ccb0d6abbbeb1d2c4f86aa98731027e3285a4765dfd97b7706450cb49`
- `launcher-baseline-evidence.json`: `9d9f5b80ef0b16c4fade728ffd9862bd86530da26f9e89852baec2c12fffbb68`
- `tools/audit_launcher_baseline.py`: `7ad1eed43cf508300d8e3e49319a971a0099aea34af4cfc03c351c084879b45e`
- `tools/audit_recipient_baseline.cjs`: `abcab5f713b646fe5d05c0eef56e61693908c3efd9b9c7e334462f9c3a3773a2`
- `wrapper.py`: `0bbbcd89ad5eaf1981b5dd789fec46830f8b7f0e3a0a98b5c6ce9e2666b02d5c`
- `wrapper_windows.py`: `ab6566afa3e3b6f275f1e6ca6c693148ef61786ab273ab5afe551cab46981ee7`
- `wrapper_api.py`: `68536fa16b9a1e9993e55e5c5e1825c59e3ea54270cc331e658260f606695c20`
- `session_engine.py`: `1af08c2168bfc48e2a7460540248615c654e03e4e4ebebc46a9d9ebc553f3d8d`
- `session_store.py`: `b737074d2d287df5b328bfdeb25769041d112bf19c821d6381272d69c94a52b8`
- `static/chat.js`: `19f8c32d1ee7ee81c10563a23c0a5690a23db13c08a9c8ed1ae9c5f6faa902e0`
- `windows/start_api_agent.bat`: `702c61af1623d30b7279577eea92b84effacc088aed1101597cdba55f6ea04f5`
- `macos-linux/start_api_agent.sh`: `f7e2c543c17a0e7ffb498b5dd8ce53cf405db3e09e271e9ec9ae06cf0a82e545`


## Frozen file: AGENTS.md

````markdown
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

````


## Frozen file: docs/launcher-baseline-audit.md

````markdown
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

79 selected paths: **54 equal, 16 different, 2 fork-only, 7 installation-only**. All existing Windows and macOS/Linux launcher counterparts are equal. The machine-readable evidence lists every compared path and both hashes.

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

Review pack: this audit, `launcher-baseline-evidence.json`, the two `tools/audit_*` scripts, the dated Stage A plan, `AGENTS.md`, `STATUS.md`, and the narrow `.gitignore` changes. Review target is the Git commit containing this checkpoint; obtain its hash with `git log -1 --format=%H -- docs/launcher-baseline-audit.md`. Later changes require a new frozen revision and reviewer recheck.

An optional local HTML review surface using agentchattr's existing design tokens was generated under ignored `.lavish/launcher-baseline/`. Lavish's server failed to start; no successful browser review or publication is claimed. The Markdown audit and plan are the durable deliverables.

Builder: Codex / GPT-6 runtime identity; exact provider model ID is not exposed in this session. User requested Luna at Max; no backend identity or reasoning setting is inferred from that label. Independent reviewer: **Meta selected by Seth; manual handoff; review pending**. The installation's configured reviewer model is `muse-spark-1.3-contributor`; this is requested configuration, not response-confirmed identity. Seth confirmed Meta is good for quota and will handle the handoff. No Meta MCP alias is exposed and `META_API_KEY` is absent from this session's environment; no direct model call was made and no secret file was read. `META-REVIEW-HANDOFF.md` contains the self-contained review pack. Do not close #1 or treat this audit as independently approved. Human retains final sign-off.

````

## Frozen file: docs/superpowers/plans/2026-10-12-stage-a.md

````markdown
# Stage A Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Keep coupled changes sequential; independent different-family review is required at each ticket boundary.

**Goal:** Preserve useful launcher behavior, fix verified configuration and Windows exit defects, and carry delivery defects into their existing owning tickets without regressing newer upstream work.

**Architecture:** Keep the Python server/browser frontend and current wrapper boundaries. First establish a reviewed baseline, then implement generic fixes within #4 after its #2 blocker; launch supervision is shared between Windows and Linux entry points. Frozen inputs and durable turns remain #6/#7 responsibilities, avoiding a temporary second delivery protocol.

**Tech Stack:** Python 3.11+, standard-library unittest, existing FastAPI/Uvicorn/MCP server, Windows batch, POSIX shell/tmux, browser JavaScript. PyYAML is needed only if Hermes YAML integration is added.

**Spec:** `docs/agentchattr-fork-spec.md` v1.7, `docs/launcher-baseline-audit.md`, and root `STATUS.md`. User amendment dated 2026-10-12: add Linux/Omarchy launcher equivalents and validate using the user's offered environments.

## Global constraints

- Preserve the working Desktop installation and its data. Do not copy secrets, environments, or histories.
- Keep session creation in chat Ask / Design; pre-flight configures and launches seats.
- Keep existing batch entry points. Shared launch requests select registered adapters and validated arguments, never arbitrary shell strings.
- Preserve valid existing settings; reject malformed input without replacement and back up intentional changes.
- Routine checks use deterministic fake adapters. Real-provider acceptance requires a selected, explicitly authorized package.
- Proposed probe/readiness/cancellation defaults in v1.7 are 15/60/10 seconds respectively; distinguish proposed defaults from already implemented behavior.
- An implementation ticket starts only after its recorded blockers complete. #4 is blocked by #2; #6 is blocked by #3 and #4.
- Different-family technical review and human final sign-off remain mandatory. No eligible quota means review pending.
- The old GLM incident is not attributed to a mechanism merely because that mechanism reproduces offline.

## Review focus

1. Valid JSON with an invalid structure (`[]`, `null`, scalar, non-map `mcpServers` or `security`) must remain byte-for-byte unchanged; Task 2 owns these cases.
2. A write/replace/backup failure must preserve original settings and report failure; Task 2 owns these cases.
3. Failed CLI launch/exit and cleanup failure must not become success or skip deregistration; Task 3 owns these cases.
4. Duplicate launch, an unrelated listener, paths with spaces and incompatible Windows/Linux environments must not cause cross-delivery, process termination or environment deletion; Task 4 assigns the launch acceptance cases to #2/#4.
5. Multiple same-channel turns, stale results and late output after Stop must retain identities and remain distinguishable; Task 5 assigns these cases to #6-#10/#12/#13.

## Task 1 — Freeze and review the baseline (#1)

**Files:** `docs/launcher-baseline-audit.md`, `launcher-baseline-evidence.json`, `tools/audit_launcher_baseline.py`, `tools/audit_recipient_baseline.cjs`, this plan, `STATUS.md`, `AGENTS.md`, `.gitignore`.

**Interfaces:** Consumes pinned source and read-only installed source. Produces a revisioned inventory/evidence pack and retained-launcher decisions. No runtime protocol changes.

1. Reproduce E01-E11 using the commands in the audit. E10 is the separate Node check; E11 requires PyYAML and is explicitly reported if unavailable. Confirm source still matches the pinned commit and review all included paths for secrets.
2. Freeze these documents/scripts in one Git checkpoint when committing is authorized, including `STATUS.md`; record the resulting hash in the review handoff. Do not include runtime files or `.lavish` review assets.
3. Resolve a reviewer from the user-configured quota pool, recording actual provider/model ID and quota eligibility. Send only the frozen evidence pack and necessary source excerpts. Reviewer must distinguish fake-boundary checks from integration acceptance and check the retention decisions.
4. Address findings, freeze a new revision for substantive changes, obtain recheck, then request human final sign-off. Leave issue #1 open until that sign-off. No GitHub comments or assignments are needed to create the local deliverable.

**Exit:** Reviewed inventory and bounded plan; no application fix claimed. After human sign-off, proceed to #2, not directly to dependency-blocked #4 or #6.

## Task 2 — Preserve JSON/YAML configuration (#4, after #2)

**Modify:** `wrapper.py` (`_write_json_mcp_settings`, provider configuration path resolution); `requirements.txt` only if Hermes is enabled.
**Tests:** extend `tests/test_wrapper_mcp_config.py`; create `tests/test_wrapper_config_preservation.py` and, if enabled, `tests/test_wrapper_hermes_config.py`.

**Interfaces:** Preserve `_write_json_mcp_settings(config_file: Path, url: str, transport: str = "http", *, token: str = "", http_key: str = "httpUrl") -> Path`. Add a private `_replace_config_bytes(config_file: Path, content: bytes) -> None` helper shared by settings writers. Invalid syntax/shape raises `ValueError`; filesystem failures propagate `OSError`. Neither path is allowed to overwrite the original on failure.

1. Add failing regressions against the real writer, using only disposable paths. Concrete seed:

```python
def test_malformed_json_is_unchanged(self):
    original = b'{"keep": [broken'
    self.target.write_bytes(original)
    with self.assertRaises(ValueError):
        _write_json_mcp_settings(self.target, "http://example.invalid/mcp")
    self.assertEqual(self.target.read_bytes(), original)
```

Use `subTest` for root `[]`, `null`, `false`, `"text"`, and nested `{"mcpServers": []}`, `{"security": []}`, `{"security":{"folderTrust": []}}`. Each must fail without a byte change. Missing maps are allowed; present non-maps are rejected. Add valid merge cases preserving unrelated top-level/nested values and an absent-file creation case.

2. Run `python -B -m unittest discover -s tests -p test_wrapper_config_preservation.py -v`; record the baseline failures. Configure the test runner's temporary directory inside the checkout if the harness has the same sandbox restriction as this audit.
3. Parse and validate before mutation. Remove the blanket parse-exception fallback. Prepare serialized bytes before creating a backup or replacing the destination. For an existing file, preserve its original bytes in a unique, exclusively created sibling backup; never overwrite earlier backups. Use a same-directory unique temporary file, flush/fsync, then `os.replace`. Clean only the temporary file owned by this attempt. If backup creation or replacement fails, propagate failure; do not continue launch with the wrong identity.
4. Patch backup creation and `os.replace` separately to raise `OSError` in tests; original destination must remain unchanged. Verify backups hold exact original bytes after multiple intentional updates and that an unrelated MCP server survives. Existing writer-shape tests must still pass.
5. If adapting Hermes, keep the upstream executable-default logic and add YAML injection as an explicit optional mode. Reuse the installation's narrow-node merge idea only after rejecting every present non-map, including `mcp_servers: []` (E11). Add tests for valid settings/comments, prior backup, malformed YAML, null/list/scalar shapes, environment-home resolution and missing-section creation. Use the shared atomic-write helper; don't rewrite an active user's global home in a test.
6. Duplicate-instance configuration separation remains an acceptance requirement of #4. Verify two fake seats cannot update the same live identity configuration. For a client whose contract cannot support isolated settings, reject simultaneous seats explicitly rather than claiming isolation or copying authentication into a new home.
7. Run the preservation, existing MCP writer and identity-contract tests. Freeze the #4 change and evidence for independent review; this task alone does not complete all #4 launch requirements.

## Task 3 — Propagate Windows CLI failures (#4, after #2)

**Modify:** `wrapper_windows.py:410`, `wrapper.py:916`, `windows/start_cli_agent.bat` when added, compatibility batch callers as needed.
**Tests:** create `tests/test_wrapper_windows_exit.py`; extend wrapper lifecycle tests with fake registration/cleanup.

**Interfaces:** Windows `run_agent(...) -> int` returns the final child status in `no_restart` mode; launch failure returns nonzero (use 1) and Ctrl+C returns 130. Preserve automatic restart behavior when enabled. `main()` returns a status; module entry calls `raise SystemExit(main())`. Unix currently returns `None`; preserve compatibility with `None -> 0` until Unix exit capture is implemented and verified under #4.

1. Write a failing fake-process test using the actual Windows runner, patching `enable_vt_mode`, `_vt_keepalive_thread`, and `subprocess.Popen`. The fake exposes `pid=123`, `returncode=23`, `wait() -> 23`. With `no_restart=True`, assert the runner returns 23, watcher is started once and PID holder is cleared. Run on Windows; skip the native module import on Linux.
2. Add success (0), `Popen` failure, KeyboardInterrupt and restart-then-exit cases. Check launch errors clear PID state and cannot loop indefinitely in `no_restart` mode.
3. Return the status from the runner, capture it in `main()`, preserve the existing `finally` deregistration/proxy cleanup, and normalize `None` only for compatibility. Ensure cleanup exceptions do not replace a captured failed-child status. Add a wrapper-level test where the runner returns 23 and cleanup executes exactly once.
4. Batch entry points capture `%ERRORLEVEL%` immediately after Python and use `exit /b` with that captured value after any diagnostic/pause. Verify with a fake Python/CLI fixture that exits 23; never invoke a configured live agent for this test.
5. Run Windows lifecycle and configuration tests; freeze evidence with #4. Do not advertise Unix child exit accuracy until Task 4's tmux check is implemented.

## Task 4 — Shared launch path and Omarchy equivalents (#2-#4)

This is a dependency-aware launch handoff, not a complete Stage B design. Implement #2's own approved scope first. The following portability requirements are now part of the intended launch work.

**Files to create/extend in those tickets:** shared `launcher.py`; `windows/start_cli_agent.bat`; `macos-linux/start_cli_agent.sh`; thin platform aliases for `hermes`, `omp`, `glm`, `muse`, `deepseek`; existing `start_api_agent` and `start` entry points; `wrapper_unix.py`; `tests/test_launcher.py`; `tests/test_launcher_shell.py`. Reuse any shared module introduced by #2 rather than adding a competing supervisor.

**Boundary:** The shared Python launcher owns config resolution, bounded probes, app-specific readiness and owned process bookkeeping. Shell/batch files only select a registered adapter and forward arguments/status. Saved seat configuration stores secret references, not values. Match the effective configuration before reusing any instance. Linux uses the upstream tmux transport, retaining its checked delivery and activity handling.

**Required fake acceptance cases:** configured non-default port; unrelated HTTP listener; failed startup; deadline expiry; duplicate launch; missing executable; missing tmux; path containing spaces; failed child; stale session with unknown ownership; and two same-client seats. The first two map to AT-01, duplicate identity to AT-03. Installation/setup must require an explicit setup action; passive `--check` must not install or mutate settings.

**Environment policy:** Use a separate Linux virtual environment when the same checkout is accessible from Windows and Linux. An incompatible existing environment produces a clear setup choice or selects a new platform environment. Never delete `.venv` automatically. Do not require GNOME Terminal or Xterm on Omarchy: use the current terminal for agent/tmux and a supervised background server with local logs. Desktop/browser opening is a thin optional integration; it must not decide server readiness.

**Omarchy validation checklist:**

1. Record whether testing is Windows-hosted Linux or native dual boot, Python/tmux versions, shell and terminal. Do not assume the Windows-hosted environment has the same desktop integration as native Omarchy.
2. With fake adapters, run both generic CLI/API entries and all five new aliases; verify selection and exit status without provider calls.
3. Test a checkout path containing spaces, a non-default port and two simultaneous invocations. Confirm one server and no unrelated listener/process termination.
4. Start from a checkout that contains a Windows environment. Confirm Linux selects/prepares a separate environment without modifying it. Missing dependency/probe errors are bounded and actionable.
5. Verify real tmux delivery/acknowledgement and duplicate-seat isolation with fake CLIs, including detach/reattach. A successful tmux attach exit is not a child-process success receipt; capture the owned pane's child status explicitly before claiming exit propagation.
6. When the user selects the usage-consuming live package, test demonstrated clients first, then one bounded Hermes and OMP session each. Verify a mention, the selected role/prompt, a posted result, Stop and process cleanup. Record exact client/model IDs and dates. Unresolved optional clients stay visibly unverified/unavailable.

Windows-hosted tests may establish shell/tmux behavior. Native desktop launch/Wayland/browser claims require a suitable desktop test; dual boot is available if needed. No Omarchy pass is claimed in this checkpoint.

## Task 5 — Carry delivery defects to existing tickets

Do not patch the API prompt in isolation while retaining same-channel coalescing. It would still lose work and create a misleading partial fix.

| Ticket | Source and required verification | Boundary |
| --- | --- | --- |
| #6 | `session_engine.py`, `wrapper_api.py`, `wrapper.py`; deliver explicit frozen role/phase/brief/rules/source revision beyond 20 messages (E04/E05, AT-04/10) | Define the shared turn envelope once; no separate API-only session protocol. |
| #7 | Both queue loops and `agents.py`; distinct turns in one poll retain channel/job/prompt/dispatch identity, same-channel turns survive, exact dispatch replay deduplicates (E03/E04, AT-21b) | Durable serialized consumption/receipts, not only replacing `set()` with a list. |
| #8 | `session_engine.py` and completion endpoints; status, duplicate, wrong-attempt and stale-revision events cannot advance (E07, AT-05) | Preserve choice cards; require explicit current-turn final event. |
| #10 | Engine/router/adapters; persist Stop before cancellation, prevent queued/late cascades, show unresolved cancellation (E08, AT-06) | Do not describe a stored-state change as provider cancellation. |
| #12/#13 | API error/result paths; typed failure plus deadline fallback; persisted result outbox and idempotent recovery (E06, AT-21a/c) | No model regeneration presented as answer recovery. |
| #16 | Coordinator/editor/backend capacity policy (E09, AT-20) | Six seats in a phase and representable seven-seat packages; concurrency is separate. |
| #17/#18 | Composer routing and persistent plain-text documents (E05/E10, AT-09/04) | Explicit recipients win; source documents remain data with revision identity. |

Full restart reconciliation (#9), participant recovery (#14/#15), documents/artifacts/export (#18-#23) and independent review product features (#24-#26) remain outside this Stage A patch scope. The presence of `archive.py` removes the missing-file task; actual export behavior still belongs to later acceptance. All requirements in v1.7 not addressed by Tasks 2/3 are deliberately assigned to the existing launch/delivery/product tickets, not claimed complete here.

## Verification and handoff

The current checkpoint has a passing offline audit (10 Python observations including optional Hermes E11, plus Node E10) and eight existing MCP configuration tests passing. It has no application implementation, complete application-suite pass, independent approval, live-provider acceptance or Omarchy run.

Freeze/review #1 first. Then execute #2; implement Tasks 2/3 with #4 after its blocker, and apply Task 4's Linux requirements across #2-#4. Update root `STATUS.md` with actual results and the next dependency-ready action at every handoff. Keep this document an implementation reference; current progress belongs in `STATUS.md`.

````


## Frozen file: launcher-baseline-evidence.json

```json
{
  "head": "8a51299c195cabc5f309d6e2ea9991b120e4bd36",
  "pinned_upstream": "d775776a30e8af4c85ea16b3caaf9c79d65cb239",
  "method": "allowlisted source comparison; AST-extracted functions with fake dependencies",
  "files": [
    {
      "path": "VERSION",
      "state": "same",
      "fork_sha256": "c2f2fc398169dfaf4b6a16077a5938b7361aefac1143f532b17ea18c3229cf3a",
      "installed_sha256": "a0ad50640139a524f86591157145bf1d4674ea9c065bfea21558f0f7b04430c8"
    },
    {
      "path": "agents.py",
      "state": "same",
      "fork_sha256": "2c7b55355ddfb6c2aaacb17ec0180fcd0dc60a20cf1373c09e7d74c2fc4eac7e",
      "installed_sha256": "2c7b55355ddfb6c2aaacb17ec0180fcd0dc60a20cf1373c09e7d74c2fc4eac7e"
    },
    {
      "path": "app.py",
      "state": "different",
      "fork_sha256": "24128606beb07ac3185f149ba6c400f1c96c534747babfbffce308943779e158",
      "installed_sha256": "9e78ef0af85ed077ec31d6f9e650bad28a1b006688f562d3761065c70c72cdf0"
    },
    {
      "path": "archive.py",
      "state": "fork_only",
      "fork_sha256": "b17e8bca0170f40b685bbbcd5b0108368633b89b5a6eaf82633e4008dcaca82e",
      "installed_sha256": null
    },
    {
      "path": "build_release.py",
      "state": "fork_only",
      "fork_sha256": "f647f2b7e82ec91a31f0e4cd4438018590ed11eba5659edd5c7ab1b7e19a0268",
      "installed_sha256": null
    },
    {
      "path": "config.toml",
      "state": "different",
      "fork_sha256": "607c6dbd6522c6da99beed5c9ffd3f620151fbe8e67115acb5539283e70c8599",
      "installed_sha256": "203f981054105ba0337eed08aff53e59d0ce8b39758af53b55da0b96d37de693"
    },
    {
      "path": "config_loader.py",
      "state": "same",
      "fork_sha256": "853aa1dbec7dc6fe1dcc301d4be61f8c542b77e40f1ce925cc712f33ce6b0b7d",
      "installed_sha256": "853aa1dbec7dc6fe1dcc301d4be61f8c542b77e40f1ce925cc712f33ce6b0b7d"
    },
    {
      "path": "jobs.py",
      "state": "same",
      "fork_sha256": "031466f02775c3da9541356b2cbca967c2768ee20413805c4614a4729f2197e6",
      "installed_sha256": "031466f02775c3da9541356b2cbca967c2768ee20413805c4614a4729f2197e6"
    },
    {
      "path": "macos-linux/start.sh",
      "state": "same",
      "fork_sha256": "dc8afad4c2b4ae2aaea79e97201017eccc917a3479974ad026cefaef9a75f37d",
      "installed_sha256": "dc8afad4c2b4ae2aaea79e97201017eccc917a3479974ad026cefaef9a75f37d"
    },
    {
      "path": "macos-linux/start_antigravity.sh",
      "state": "same",
      "fork_sha256": "3de63332314ea11e150e78a4504f0399006673b06594110a1927e1baa3ff2783",
      "installed_sha256": "3de63332314ea11e150e78a4504f0399006673b06594110a1927e1baa3ff2783"
    },
    {
      "path": "macos-linux/start_api_agent.sh",
      "state": "same",
      "fork_sha256": "f7e2c543c17a0e7ffb498b5dd8ce53cf405db3e09e271e9ec9ae06cf0a82e545",
      "installed_sha256": "701690d0abf15c383b39432a5a5b22f82bea6a4364e30409e1ca524c204100a9"
    },
    {
      "path": "macos-linux/start_claude.sh",
      "state": "same",
      "fork_sha256": "563e86c9247e02dc97e7e2391d0c685e88b4670ad0a91f69d1aea1cec7caf8eb",
      "installed_sha256": "563e86c9247e02dc97e7e2391d0c685e88b4670ad0a91f69d1aea1cec7caf8eb"
    },
    {
      "path": "macos-linux/start_claude_skip-permissions.sh",
      "state": "same",
      "fork_sha256": "e945cb69c696178d4fe0a0309c5229205c2ebf4cc53238bbaed433923176e280",
      "installed_sha256": "e945cb69c696178d4fe0a0309c5229205c2ebf4cc53238bbaed433923176e280"
    },
    {
      "path": "macos-linux/start_codebuddy.sh",
      "state": "same",
      "fork_sha256": "bb1c1f5cc2a7019c703831818238574cb18bd00a6c44f0ee2dc76beca51045fe",
      "installed_sha256": "bb1c1f5cc2a7019c703831818238574cb18bd00a6c44f0ee2dc76beca51045fe"
    },
    {
      "path": "macos-linux/start_codex.sh",
      "state": "same",
      "fork_sha256": "4944a49250a13bed1651fba04c91f89910c143d3abdbaf75b2337982c148c7ae",
      "installed_sha256": "4944a49250a13bed1651fba04c91f89910c143d3abdbaf75b2337982c148c7ae"
    },
    {
      "path": "macos-linux/start_codex_bypass.sh",
      "state": "same",
      "fork_sha256": "9ea1fef6e1654d34e86cb5cde02e17829e0f55ca643c01a4af5c3afcc6f1b48d",
      "installed_sha256": "9ea1fef6e1654d34e86cb5cde02e17829e0f55ca643c01a4af5c3afcc6f1b48d"
    },
    {
      "path": "macos-linux/start_copilot.sh",
      "state": "same",
      "fork_sha256": "040828de7137816edd3fe432c9c96f3ba97267709f8a13ecb2dbc96bc7f4df37",
      "installed_sha256": "040828de7137816edd3fe432c9c96f3ba97267709f8a13ecb2dbc96bc7f4df37"
    },
    {
      "path": "macos-linux/start_gemini.sh",
      "state": "same",
      "fork_sha256": "0563215f624d195f91781997ff98ba48d27dfb5c134a450e27fef4a3356ad2a2",
      "installed_sha256": "0563215f624d195f91781997ff98ba48d27dfb5c134a450e27fef4a3356ad2a2"
    },
    {
      "path": "macos-linux/start_gemini_yolo.sh",
      "state": "same",
      "fork_sha256": "c44ff6e35ddc3bb03302e3dbed809d08c0c69a1efd5fc524affb6a766e1deb26",
      "installed_sha256": "c44ff6e35ddc3bb03302e3dbed809d08c0c69a1efd5fc524affb6a766e1deb26"
    },
    {
      "path": "macos-linux/start_kilo.sh",
      "state": "same",
      "fork_sha256": "04bacb4d4b5909326f67a4cd6d21379f0e63f514b4fc89e203aaaad439f3a307",
      "installed_sha256": "04bacb4d4b5909326f67a4cd6d21379f0e63f514b4fc89e203aaaad439f3a307"
    },
    {
      "path": "macos-linux/start_kimi.sh",
      "state": "same",
      "fork_sha256": "32f0b95787459c014018f2206237d433b0b5d5e3adf5c51238e6dc73874ce11d",
      "installed_sha256": "32f0b95787459c014018f2206237d433b0b5d5e3adf5c51238e6dc73874ce11d"
    },
    {
      "path": "macos-linux/start_minimax.sh",
      "state": "same",
      "fork_sha256": "b52b9f0ed603cec0730eefae5935f0adb060ff6b615ce31d970c16d9fde965da",
      "installed_sha256": "b52b9f0ed603cec0730eefae5935f0adb060ff6b615ce31d970c16d9fde965da"
    },
    {
      "path": "macos-linux/start_qwen.sh",
      "state": "same",
      "fork_sha256": "8bc952d988b6a77e92cc686913660fb2e14363c743e3d43a181d1a1dc9b62024",
      "installed_sha256": "8bc952d988b6a77e92cc686913660fb2e14363c743e3d43a181d1a1dc9b62024"
    },
    {
      "path": "macos-linux/start_qwen_yolo.sh",
      "state": "same",
      "fork_sha256": "0631b3d671423967ae21c9c6c4a79e3e8bc62c402fd8bde7d19b7ce92e67f56a",
      "installed_sha256": "0631b3d671423967ae21c9c6c4a79e3e8bc62c402fd8bde7d19b7ce92e67f56a"
    },
    {
      "path": "mcp_bridge.py",
      "state": "different",
      "fork_sha256": "46684dbe60b1862d7eb392c929257d9c6bd7462717651359292d5ec2f07565b0",
      "installed_sha256": "d6a627eeb6a401145969a7a9b7b718a9440e30b0ed1ae1eef6895ecee505c103"
    },
    {
      "path": "mcp_proxy.py",
      "state": "same",
      "fork_sha256": "02f67941a6e98932aeee1f12d727c8a35ee97e026b07a6e5a21c44b0b34bc32f",
      "installed_sha256": "02f67941a6e98932aeee1f12d727c8a35ee97e026b07a6e5a21c44b0b34bc32f"
    },
    {
      "path": "open_chat.html",
      "state": "same",
      "fork_sha256": "f707e304f78bd0c0ef5d8d2f69b188dcda981f6197014b69db0393906c10b97c",
      "installed_sha256": "1eafd18eae325b1735b164e70a0516db3be906be1ad94d79fa08781a423c3604"
    },
    {
      "path": "registry.py",
      "state": "same",
      "fork_sha256": "660eb28ee79435304e2779c30f03bd9435d15ea66f6652a258843bdb72f5c22f",
      "installed_sha256": "660eb28ee79435304e2779c30f03bd9435d15ea66f6652a258843bdb72f5c22f"
    },
    {
      "path": "requirements.txt",
      "state": "different",
      "fork_sha256": "3ab722855a78c318d6695563f9817b45ca7f3aa46838c4e0e4bfb292ab8e3928",
      "installed_sha256": "9658a5ef30e6479463bfdc1d3876830af88ef88cb8a328229da6977de890999f"
    },
    {
      "path": "router.py",
      "state": "same",
      "fork_sha256": "66db4df09cc78307d79b79fd2c334a1bab7c7430fdb3f262d12d08ff07ccadbd",
      "installed_sha256": "5a70f3adc156eed2b7163f40a2f75898ed088a6345c120c47d9190253c5dc3a2"
    },
    {
      "path": "rules.py",
      "state": "different",
      "fork_sha256": "c68e3b792cfb44f08d6bdb9465f0f7ec4f5e7a8d2d3d313dac41a03797b54006",
      "installed_sha256": "320eea4f7ed50c601c393e65ef7b3914f428208698aaab6230e11a431bd2332a"
    },
    {
      "path": "run.py",
      "state": "same",
      "fork_sha256": "ad42c38340b1f617cdfea788b01b78b1dfe719d51cb0573b8888e74a5f1e4cbc",
      "installed_sha256": "ad42c38340b1f617cdfea788b01b78b1dfe719d51cb0573b8888e74a5f1e4cbc"
    },
    {
      "path": "schedules.py",
      "state": "different",
      "fork_sha256": "52384133bd7161d40e99daa06a18250bc968233634add50eb85b1ac858a483c3",
      "installed_sha256": "82f61784e0ffadc55949c6f4818fb056b2d68c8041d61f7b3b4562c99fbd9947"
    },
    {
      "path": "session_engine.py",
      "state": "different",
      "fork_sha256": "1af08c2168bfc48e2a7460540248615c654e03e4e4ebebc46a9d9ebc553f3d8d",
      "installed_sha256": "b67b098c32675a415009e41df56ac1531ad0184f98bc2aeaa6a18812bbfb2c57"
    },
    {
      "path": "session_store.py",
      "state": "different",
      "fork_sha256": "b737074d2d287df5b328bfdeb25769041d112bf19c821d6381272d69c94a52b8",
      "installed_sha256": "ceb6accb696ae53a9fc9f421e5cafc1504faec86dbd2002df53a69e0e334bd8f"
    },
    {
      "path": "session_templates/code-review.json",
      "state": "same",
      "fork_sha256": "983a5e9fabc832708e4b1465b275ec4403315e79bece3b9ba94914f175c82c90",
      "installed_sha256": "d64c024cffa5cad15d38ff2c69be44d146fa132e08df8f0c973b6200df90f6a1"
    },
    {
      "path": "session_templates/debate.json",
      "state": "same",
      "fork_sha256": "43850230a198fce922c0994afc6e449ff93a1e8173899414feae09a42548ea94",
      "installed_sha256": "f20f4fce014f277295da2b55c5318c78cff789d945ebbda257c5d89dbc6a3a1a"
    },
    {
      "path": "session_templates/design-critique.json",
      "state": "same",
      "fork_sha256": "f09e83ef68b0028f83c0a56b4ae1f6c91d1d548c9b2b216bd125c297e756d300",
      "installed_sha256": "ba80336243ab3b06b5592d37cd0bbb3c70d4c7e5a0f89ae6d8e579fbb5a48246"
    },
    {
      "path": "session_templates/planning.json",
      "state": "same",
      "fork_sha256": "5433ceec3d95cba81013c74ece9287e55289d3b4a4ad1c9ca009c2e5869d331b",
      "installed_sha256": "f1e44b7e1ba5331c75c402d6f886aa82de162a30dc96a9f0e44d67e1869b8e7a"
    },
    {
      "path": "static/channels.js",
      "state": "different",
      "fork_sha256": "a823675fa1a4e44eb7d63a8cf6bcdaeb27ae42255973b2eb8f4c57af38617c17",
      "installed_sha256": "a4900323ddaf607fe4a2de02eb34d7ba56afd053f600890c8b0473acb7950334"
    },
    {
      "path": "static/chat.js",
      "state": "different",
      "fork_sha256": "19f8c32d1ee7ee81c10563a23c0a5690a23db13c08a9c8ed1ae9c5f6faa902e0",
      "installed_sha256": "8ee336a2d3fb1348d2dc47676b92dcb02980d735195b8f545dc279ee49ba6844"
    },
    {
      "path": "static/core.js",
      "state": "same",
      "fork_sha256": "f9107290e3566901546817d91654d4d106d4b9910ff89043052be72a6da88cd8",
      "installed_sha256": "f9107290e3566901546817d91654d4d106d4b9910ff89043052be72a6da88cd8"
    },
    {
      "path": "static/index.html",
      "state": "different",
      "fork_sha256": "0ae68addf9225f3efec67ea044a9167cbc33f1baf9b7cbcada00daaa9a367929",
      "installed_sha256": "47a0ad27ad943bebeccb90d14ee9fcaf4467036e4b8cf015b8a4497ad79035ff"
    },
    {
      "path": "static/jobs.css",
      "state": "same",
      "fork_sha256": "a40480704d2b31c96bed2b62a20754d90f4d53fb9e98301d4ad2e1daab057f8b",
      "installed_sha256": "a40480704d2b31c96bed2b62a20754d90f4d53fb9e98301d4ad2e1daab057f8b"
    },
    {
      "path": "static/jobs.js",
      "state": "same",
      "fork_sha256": "eeef8c4340cf5a3bdfe4de51fdc5a675a039d6f9a5cb1bb0531b4d7913f5058a",
      "installed_sha256": "eeef8c4340cf5a3bdfe4de51fdc5a675a039d6f9a5cb1bb0531b4d7913f5058a"
    },
    {
      "path": "static/rules-panel.js",
      "state": "different",
      "fork_sha256": "e7142fa01ba60b84218310d22b97a82500797ba5e59701d40d919d168e4efc0d",
      "installed_sha256": "1b4e1c86fa41afe11a01a12c4830876b09417fa26b0c4a1f03d6878326fc9755"
    },
    {
      "path": "static/sessions.css",
      "state": "same",
      "fork_sha256": "e11750a72cbc42ac8f37aec4d3dc48429df2bd4865bbf880fa1d85b5cc4cc04c",
      "installed_sha256": "e11750a72cbc42ac8f37aec4d3dc48429df2bd4865bbf880fa1d85b5cc4cc04c"
    },
    {
      "path": "static/sessions.js",
      "state": "different",
      "fork_sha256": "b76237a4cae84f4dc3d85065b9ec777195cb25739e03c99af13a37545dd09c04",
      "installed_sha256": "4776af58e1985482fce663ebdd6ceeb8b7e76e7e1d54b314ea1b8d24866db8cc"
    },
    {
      "path": "static/store.js",
      "state": "same",
      "fork_sha256": "3ef05b6111e9dc03fb805084e8bcb09dec3591f4277d35cdf113d673e605bbf6",
      "installed_sha256": "3ef05b6111e9dc03fb805084e8bcb09dec3591f4277d35cdf113d673e605bbf6"
    },
    {
      "path": "static/style.css",
      "state": "different",
      "fork_sha256": "6a3dd55e6f609eb08f4ae85160fedba47adee3b5c4ed3429b1ca65e6188f130b",
      "installed_sha256": "cb91276eb1342d1bff06219c54e4da774fe655b9344316feb61e9c6ef5e7e432"
    },
    {
      "path": "store.py",
      "state": "same",
      "fork_sha256": "9d17d519e80ae1e412a424452810b15a331827ef8a058d6912a566d05144ad1d",
      "installed_sha256": "9d17d519e80ae1e412a424452810b15a331827ef8a058d6912a566d05144ad1d"
    },
    {
      "path": "summaries.py",
      "state": "same",
      "fork_sha256": "7627b2dfff9412208a9b5fd8117252e8381a74f0b257dbf3fc5d08336e062038",
      "installed_sha256": "7627b2dfff9412208a9b5fd8117252e8381a74f0b257dbf3fc5d08336e062038"
    },
    {
      "path": "test_cli_launchers.py",
      "state": "installed_only",
      "fork_sha256": null,
      "installed_sha256": "6d9a78b56aac05ff6a7b0934669fdf245d7a110a123f578be21aeb233de87c65"
    },
    {
      "path": "windows/start.bat",
      "state": "same",
      "fork_sha256": "20b2c7a76336d3751303756cf5f2186bd03291ffb358b8beb37a3b09e125c266",
      "installed_sha256": "20b2c7a76336d3751303756cf5f2186bd03291ffb358b8beb37a3b09e125c266"
    },
    {
      "path": "windows/start_antigravity.bat",
      "state": "same",
      "fork_sha256": "dff43e2c1e848c3e3734c7466ef982edebe6abe3e697a9a5f47600efc9fbeb12",
      "installed_sha256": "9dd9245b4b0f4efb5f83444ad9bee3859779970cf51cf8e8a3b968e50ec44462"
    },
    {
      "path": "windows/start_api_agent.bat",
      "state": "same",
      "fork_sha256": "702c61af1623d30b7279577eea92b84effacc088aed1101597cdba55f6ea04f5",
      "installed_sha256": "702c61af1623d30b7279577eea92b84effacc088aed1101597cdba55f6ea04f5"
    },
    {
      "path": "windows/start_claude.bat",
      "state": "same",
      "fork_sha256": "2545bf41cd88bda5b181977084710640c9dac98dd0c4ffe59f90915c527a04bb",
      "installed_sha256": "2545bf41cd88bda5b181977084710640c9dac98dd0c4ffe59f90915c527a04bb"
    },
    {
      "path": "windows/start_claude_skip-permissions.bat",
      "state": "same",
      "fork_sha256": "7b4337d6a36ec0fb7d56bba7cf887e5420122b1ea77f16986c09be63c1289662",
      "installed_sha256": "7b4337d6a36ec0fb7d56bba7cf887e5420122b1ea77f16986c09be63c1289662"
    },
    {
      "path": "windows/start_cli_agent.bat",
      "state": "installed_only",
      "fork_sha256": null,
      "installed_sha256": "0f34b67ae5ccddb725f262db828b5056febe647ed0cdc3b5f51c135524e9fd85"
    },
    {
      "path": "windows/start_codebuddy.bat",
      "state": "same",
      "fork_sha256": "cead0a29698492bd91e12df6d64edaa967621959907b8a5199d3077e1f4406e8",
      "installed_sha256": "b6e783a77689a15d1e99b65b80e05d28ca24deb9aca105cd945e9e580fad871f"
    },
    {
      "path": "windows/start_codex.bat",
      "state": "same",
      "fork_sha256": "d2607b48600c8d17ea565cd319b9198e6a1fecf2c75ecf6f8a7da2c218480877",
      "installed_sha256": "d2607b48600c8d17ea565cd319b9198e6a1fecf2c75ecf6f8a7da2c218480877"
    },
    {
      "path": "windows/start_codex_bypass.bat",
      "state": "same",
      "fork_sha256": "a79d682b438b1982f7abe0a14183f42e02c658ad7711737295a7e2df19ac84b9",
      "installed_sha256": "a79d682b438b1982f7abe0a14183f42e02c658ad7711737295a7e2df19ac84b9"
    },
    {
      "path": "windows/start_copilot.bat",
      "state": "same",
      "fork_sha256": "28ddcd8d2a25b817d66312f7b2d3a2c4e72c943f11c4c3b8a67b170bc4bffcc3",
      "installed_sha256": "f59b0ed7aaffc272f12c7dbfd32d1f1b2e0024bcde8ec022a31e35b7c612e790"
    },
    {
      "path": "windows/start_deepseek.bat",
      "state": "installed_only",
      "fork_sha256": null,
      "installed_sha256": "d1941a1a425ddb5e0b25739a3866b2cba0cf108b9885d91016416b9ea2bb4169"
    },
    {
      "path": "windows/start_gemini.bat",
      "state": "same",
      "fork_sha256": "3972c6621a45815f23a59125afae061facd1912b6328168befba4fcf53444d95",
      "installed_sha256": "3972c6621a45815f23a59125afae061facd1912b6328168befba4fcf53444d95"
    },
    {
      "path": "windows/start_gemini_yolo.bat",
      "state": "same",
      "fork_sha256": "e7c3a37fbf95b12b96c99483840fd4ed198460efd5474d3e54447c75b34ec069",
      "installed_sha256": "e7c3a37fbf95b12b96c99483840fd4ed198460efd5474d3e54447c75b34ec069"
    },
    {
      "path": "windows/start_glm.bat",
      "state": "installed_only",
      "fork_sha256": null,
      "installed_sha256": "363505136146705500382511d2b3145413396e255db5bfe9f827717e061bbc39"
    },
    {
      "path": "windows/start_hermes.bat",
      "state": "installed_only",
      "fork_sha256": null,
      "installed_sha256": "052348581bc047296e93298d679af0ed60f7ab0834d50ffeb0ca3585f0650dec"
    },
    {
      "path": "windows/start_kilo.bat",
      "state": "same",
      "fork_sha256": "512dc5755ca8a0bab54e829cd1be6d110501b5ba9ac963311a10bf8feb96dab2",
      "installed_sha256": "512dc5755ca8a0bab54e829cd1be6d110501b5ba9ac963311a10bf8feb96dab2"
    },
    {
      "path": "windows/start_kimi.bat",
      "state": "same",
      "fork_sha256": "e47ea8520ec7205a7280b77a375560bb602ce27bd13eb5b25bf59ab8d822b713",
      "installed_sha256": "e47ea8520ec7205a7280b77a375560bb602ce27bd13eb5b25bf59ab8d822b713"
    },
    {
      "path": "windows/start_minimax.bat",
      "state": "same",
      "fork_sha256": "6bf273d87ee0167b46c465604739eed1fde801e5ecd5cd1555f7f6807208fc42",
      "installed_sha256": "6bf273d87ee0167b46c465604739eed1fde801e5ecd5cd1555f7f6807208fc42"
    },
    {
      "path": "windows/start_muse.bat",
      "state": "installed_only",
      "fork_sha256": null,
      "installed_sha256": "2f07432e66b6b92b4e11096a9aca970c883081048bc6adc14dcdaa9fa0f53593"
    },
    {
      "path": "windows/start_omp.bat",
      "state": "installed_only",
      "fork_sha256": null,
      "installed_sha256": "16964cc0b50d8eceb14b3712a0163de7b49b8681883e081cf421eafc278cf964"
    },
    {
      "path": "windows/start_qwen.bat",
      "state": "same",
      "fork_sha256": "f676bf5e74da9a50a3f012697564f4577cdf1df699e9b71fd99d03bd5e9bfdf7",
      "installed_sha256": "f676bf5e74da9a50a3f012697564f4577cdf1df699e9b71fd99d03bd5e9bfdf7"
    },
    {
      "path": "windows/start_qwen_yolo.bat",
      "state": "same",
      "fork_sha256": "8f62dd261f07d25a170bb7359b9073911d7ddb66bcb6bb000ed9fb6bad6d7425",
      "installed_sha256": "8f62dd261f07d25a170bb7359b9073911d7ddb66bcb6bb000ed9fb6bad6d7425"
    },
    {
      "path": "wrapper.py",
      "state": "different",
      "fork_sha256": "0bbbcd89ad5eaf1981b5dd789fec46830f8b7f0e3a0a98b5c6ce9e2666b02d5c",
      "installed_sha256": "55b4d9d04be86442b15bd83c3df91c848d849bdf48e757bf55fb34bddb951754"
    },
    {
      "path": "wrapper_api.py",
      "state": "same",
      "fork_sha256": "68536fa16b9a1e9993e55e5c5e1825c59e3ea54270cc331e658260f606695c20",
      "installed_sha256": "68536fa16b9a1e9993e55e5c5e1825c59e3ea54270cc331e658260f606695c20"
    },
    {
      "path": "wrapper_unix.py",
      "state": "different",
      "fork_sha256": "71d9cdd7609e586e296ed4a7a35cd7dc83b6eda964cd085ffe942e2eaef724a1",
      "installed_sha256": "db434a8f66dbe7ee834c2eba3c33839349651094551b35c62ae9a8c335d806ac"
    },
    {
      "path": "wrapper_windows.py",
      "state": "same",
      "fork_sha256": "ab6566afa3e3b6f275f1e6ca6c693148ef61786ab273ab5afe551cab46981ee7",
      "installed_sha256": "ab6566afa3e3b6f275f1e6ca6c693148ef61786ab273ab5afe551cab46981ee7"
    }
  ],
  "observations": [
    {
      "id": "E01",
      "observation": "Malformed JSON overwritten by shared writer"
    },
    {
      "id": "E02",
      "child_exit": 23,
      "runner_return": null
    },
    {
      "id": "E03",
      "queued": 2,
      "injected": 1,
      "first_job_lost": true
    },
    {
      "id": "E04",
      "queued": 2,
      "api_calls": 1,
      "prompts_forwarded": false
    },
    {
      "id": "E05",
      "history_limit": 20,
      "system_message_included": false,
      "attachment_included": false
    },
    {
      "id": "E06",
      "failure_posted": false,
      "failure_printed": true
    },
    {
      "id": "E07",
      "status_schedules_advance": true,
      "paused_session_resumed": true
    },
    {
      "id": "E08",
      "end_updates_store": true,
      "trigger_cancellation_calls": 0
    },
    {
      "id": "E09",
      "six_seat_errors": [
        "Phase 1: too many participants (6, max 4)"
      ],
      "seven_role_errors": [
        "Too many roles (7, max 6)"
      ]
    },
    {
      "id": "E11",
      "hermes_mapping_and_backup_preserved": true,
      "malformed_yaml_preserved": true,
      "invalid_server_sequence_replaced": true
    }
  ],
  "extra_installed_agent_ids": [
    "deepseek",
    "glm",
    "hermes",
    "muse",
    "omp"
  ],
  "passive_executable_found": {
    "omp": true,
    "hermes": true,
    "hermes.cmd": true,
    "codebuddy": false
  }
}

```


## Frozen file: tools/audit_launcher_baseline.py

```python
"""Offline characterization of the pinned source, not acceptance of fixes.

Run: python -X utf8 -B tools/audit_launcher_baseline.py --installed <path>
Only reads allowlisted source files in the installed tree. Never imports its
modules, reads local settings/history/environment files, or starts an agent.
Extracted functions run against temporary files and fake transports/processes.
"""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock
import tomllib

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".py", ".toml", ".txt", ".html", ".bat", ".sh", ".js", ".css", ".json"}


def extract(path, name, namespace=None):
    """Compile one real function without executing module startup/imports."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    scope = {} if namespace is None else namespace
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), scope)
    return scope[name]


class EndPoll(BaseException):
    pass


def stop_poll(seconds):
    if seconds == 1:
        raise EndPoll()


def inventory(installed):
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    selected = [p for p in tracked if (
        "/" not in p and (Path(p).suffix in {".py", ".toml", ".txt", ".html"} or p == "VERSION")
        and p not in {"STATUS.md", "AGENTS.md"}
    ) or (p.split("/")[0] in {"windows", "macos-linux", "static", "session_templates"}
          and Path(p).suffix in TEXT_EXTENSIONS)]
    candidates = set(selected)
    for path in installed.iterdir():
        if path.is_file() and path.suffix in {".py", ".html"}:
            candidates.add(path.name)
    for directory in ("windows", "macos-linux", "static", "session_templates"):
        source_dir = installed / directory
        if source_dir.exists():
            for path in source_dir.rglob("*"):
                if path.is_file() and path.suffix in TEXT_EXTENSIONS:
                    candidates.add(path.relative_to(installed).as_posix())
    records = []
    for relative in sorted(candidates):
        current, previous = ROOT / relative, installed / relative
        a = current.read_bytes() if current.is_file() else None
        b = previous.read_bytes() if previous.is_file() else None
        state = "installed_only" if a is None else "fork_only" if b is None else (
            "same" if a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n") else "different")
        records.append({"path": relative, "state": state,
                        "fork_sha256": hashlib.sha256(a).hexdigest() if a is not None else None,
                        "installed_sha256": hashlib.sha256(b).hexdigest() if b is not None else None})
    return records


def characterize(installed):
    observations = []
    scratch_parent = ROOT / ".audit-tmp"
    scratch_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="baseline-", dir=scratch_parent) as scratch:
        root = Path(scratch)
        # Run the actual JSON writer against disposable malformed input.
        writer = extract(ROOT / "wrapper.py", "_write_json_mcp_settings",
                         {"Path": Path, "json": json, "SERVER_NAME": "agentchattr"})
        target = root / "settings.json"
        original = b'{"keep": [malformed'
        target.write_bytes(original)
        writer(target, "http://example.invalid/mcp")
        assert target.read_bytes() != original
        assert json.loads(target.read_text())["mcpServers"]["agentchattr"]
        observations.append({"id": "E01", "observation": "Malformed JSON overwritten by shared writer"})

        # The Windows runner sees a failed child but returns None.
        fake_process = SimpleNamespace(pid=123, returncode=23, wait=lambda: 23)
        runner = extract(ROOT / "wrapper_windows.py", "run_agent", {
            "enable_vt_mode": lambda: None, "_vt_keepalive_thread": lambda: None,
            "subprocess": SimpleNamespace(Popen=lambda *a, **k: fake_process),
            "inject": lambda *a, **k: None,
        })
        result = runner("fake", [], str(root), {}, root / "unused", "fake", True, lambda fn: None)
        assert result is None
        observations.append({"id": "E02", "child_exit": 23, "runner_return": result})

        # CLI poll: actual watcher, fake role/rules/network-free injection.
        queue = root / "cli_queue.jsonl"
        queue.write_text('\n'.join(json.dumps(x) for x in [
            {"channel": "alpha", "job_id": 41}, {"channel": "beta", "prompt": "SECOND-PROMPT"}
        ]), encoding="utf-8")
        injected = []
        watcher = extract(ROOT / "wrapper.py", "_queue_watcher", {
            "json": json, "time": SimpleNamespace(sleep=stop_poll),
            "_fetch_role": lambda *a: "", "_fetch_active_rules": lambda *a: None,
        })
        try:
            watcher(lambda: ("fake", queue), injected.append)
        except EndPoll:
            pass
        assert injected == ["SECOND-PROMPT"] and queue.read_text() == ""
        observations.append({"id": "E03", "queued": 2, "injected": len(injected), "first_job_lost": True})

        # Compile the exact API polling loop for one iteration; replace only
        # its dependencies. Same-channel prompts collapse before handle_trigger.
        api_tree = ast.parse((ROOT / "wrapper_api.py").read_text(encoding="utf-8"))
        main = next(n for n in api_tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        loop = next(n for n in ast.walk(main) if isinstance(n, ast.While)
                    and any(isinstance(child, ast.Name) and child.id == "channels_triggered"
                            for child in ast.walk(n)))
        api_queue = root / "fake_queue.jsonl"
        api_queue.write_text('\n'.join(json.dumps({"channel": "alpha", "prompt": p}) for p in ("FIRST", "SECOND")), encoding="utf-8")
        handled = []
        namespace = {"data_dir": root, "get_name": lambda: "fake", "json": json,
                     "time": SimpleNamespace(sleep=stop_poll),
                     "handle_trigger": lambda **kw: handled.append(kw)}
        try:
            exec(compile(ast.Module(body=[loop], type_ignores=[]), "wrapper_api.py", "exec"), namespace)
        except EndPoll:
            pass
        assert handled == [{"channel": "alpha"}]
        observations.append({"id": "E04", "queued": 2, "api_calls": len(handled), "prompts_forwarded": False})

        # Capture model payload from real formatting/handling functions.
        payloads, sent, states, limits = [], [], [], []
        api_scope = {
            "get_name": lambda: "fake", "get_online_agents": lambda: [],
            "get_my_role": lambda: "", "system_prompt": "BASE",
            "set_working": states.append, "context_messages": 20,
            "read_messages": lambda **kw: limits.append(kw["limit"]) or [
                {"sender": "system", "text": "SESSION-INSTRUCTION"},
                {"sender": "user", "text": "hello", "attachments": [{"name": "SOURCE-SENTINEL"}]}],
            "call_model": lambda messages: payloads.append(messages) or "result",
            "send_message": lambda *a, **kw: sent.append((a, kw)),
        }
        extract(ROOT / "wrapper_api.py", "format_messages", api_scope)
        handle = extract(ROOT / "wrapper_api.py", "handle_trigger", api_scope)
        with contextlib.redirect_stdout(io.StringIO()):
            handle(channel="alpha")
        payload = json.dumps(payloads)
        assert "SESSION-INSTRUCTION" not in payload and "SOURCE-SENTINEL" not in payload
        assert limits == [20]
        observations.append({"id": "E05", "history_limit": 20, "system_message_included": False,
                             "attachment_included": False})
        sent.clear()
        def fail_model(messages):
            raise RuntimeError("fake provider failure")
        api_scope["call_model"] = fail_model
        with contextlib.redirect_stdout(io.StringIO()) as console:
            handle(channel="alpha")
        assert sent == [] and "Error handling trigger" in console.getvalue() and states[-1] is False
        observations.append({"id": "E06", "failure_posted": False, "failure_printed": True})

        # Real participant handler: plain status schedules advancement and
        # resumes a paused session; fake Timer avoids background execution.
        timers = []
        session = {"id": 1, "cast": {"reviewer": "fake"}, "state": "paused"}
        store = Mock()
        store.get_active.return_value = session
        instance = SimpleNamespace(_store=store, _messages=Mock(), _trigger=Mock(),
                                   _get_expected_agent=lambda s: "fake", _is_agent=lambda n: n == "fake",
                                   _advance=lambda *a: None)
        handler = extract(ROOT / "session_engine.py", "_handle_participant_message", {
            "threading": SimpleNamespace(Timer=lambda *a, **kw: SimpleNamespace(start=lambda: timers.append((a, kw)))),
        })
        handler(instance, {"id": 10, "type": "chat", "text": "Still working"}, "alpha", "fake")
        assert len(timers) == 1 and store.resume.call_count == 1
        observations.append({"id": "E07", "status_schedules_advance": True, "paused_session_resumed": True})
        end_session = extract(ROOT / "session_engine.py", "end_session", {"log": Mock()})
        end_session(instance, 1)
        assert store.interrupt.call_count == 1 and instance._trigger.mock_calls == []
        observations.append({"id": "E08", "end_updates_store": True, "trigger_cancellation_calls": 0})

        validate = extract(ROOT / "session_store.py", "validate_session_template")
        roles = [f"seat{i}" for i in range(6)]
        errors = validate({"name": "Six", "roles": roles, "phases": [
            {"name": "Review", "participants": roles, "prompt": "Review", "is_output": True}]})
        assert any("max 4" in error for error in errors)
        seven_errors = validate({"name": "Seven", "roles": roles + ["seat6"], "phases": [
            {"name": "Review", "participants": ["seat0"], "prompt": "Review", "is_output": True}]})
        assert any("max 6" in error for error in seven_errors)
        observations.append({"id": "E09", "six_seat_errors": errors, "seven_role_errors": seven_errors})

        # A local Hermes writer is a candidate to adapt, not trusted wholesale.
        # Compile just its function; YAML is optional for this diagnostic.
        try:
            import yaml
        except ImportError:
            observations.append({"id": "E11", "hermes_writer_check": "not run: PyYAML unavailable"})
        else:
            yaml_writer = extract(installed / "wrapper.py", "_write_yaml_mcp_settings", {
                "Path": Path, "shutil": shutil, "SERVER_NAME": "agentchattr"})
            yaml_target = root / "hermes.yaml"
            original_yaml = "# Keep\nmodel: example\nmcp_servers:\n  other:\n    url: http://example.invalid\n"
            yaml_target.write_text(original_yaml, encoding="utf-8")
            yaml_writer(yaml_target, "http://example.invalid/mcp", "fake-token")
            saved = yaml.safe_load(yaml_target.read_text(encoding="utf-8"))
            assert saved["model"] == "example" and "other" in saved["mcp_servers"]
            assert yaml_target.with_name("hermes.yaml.agentchattr.bak").read_text(encoding="utf-8") == original_yaml
            yaml_target.write_text("bad: [", encoding="utf-8")
            try:
                yaml_writer(yaml_target, "http://example.invalid/mcp", "fake-token")
            except yaml.YAMLError:
                pass
            else:
                raise AssertionError("Malformed YAML unexpectedly accepted")
            assert yaml_target.read_text(encoding="utf-8") == "bad: ["
            # An empty sequence is invalid as a server map, but the writer's
            # `or {}` accepts and replaces it instead of rejecting its shape.
            yaml_target.write_text("mcp_servers: []\n", encoding="utf-8")
            yaml_writer(yaml_target, "http://example.invalid/mcp", "fake-token")
            assert yaml_target.read_text(encoding="utf-8") != "mcp_servers: []\n"
            observations.append({"id": "E11", "hermes_mapping_and_backup_preserved": True,
                                 "malformed_yaml_preserved": True, "invalid_server_sequence_replaced": True})
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    files = inventory(args.installed)
    installed_cfg = tomllib.loads((args.installed / "config.toml").read_text(encoding="utf-8"))
    fork_cfg = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
    output = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "pinned_upstream": "d775776a30e8af4c85ea16b3caaf9c79d65cb239",
        "method": "allowlisted source comparison; AST-extracted functions with fake dependencies",
        "files": files, "observations": characterize(args.installed),
        "extra_installed_agent_ids": sorted(set(installed_cfg["agents"]) - set(fork_cfg["agents"])),
        "passive_executable_found": {name: shutil.which(name) is not None
                                     for name in ("omp", "hermes", "hermes.cmd", "codebuddy")},
    }
    if args.output:
        args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    counts = {state: sum(f["state"] == state for f in files)
              for state in ("same", "different", "fork_only", "installed_only")}
    print(json.dumps({"inventory": counts, "observations": output["observations"]}, indent=2))


if __name__ == "__main__":
    main()

```


## Frozen file: tools/audit_recipient_baseline.cjs

```javascript
// Characterize the real composer function with a fake DOM and WebSocket.
// No browser/server/provider is started. Expected baseline behavior is a defect.
const fs = require('fs');
const source = fs.readFileSync(require('path').join(__dirname, '../static/chat.js'), 'utf8');
const start = source.indexOf('function sendMessage() {');
const end = source.indexOf('// --- Image paste/drop ---', start);
if (start < 0 || end < start) throw new Error('Composer boundaries changed; inspect before updating audit');
const input = {value: '@claude review this', style: {}, focus() {}};
const document = {getElementById() { return input; }};
const activeMentions = new Set(['claude', 'codex', 'glm']);
const pendingAttachments = [];
const username = 'test', activeChannel = 'general', replyingTo = null;
const WebSocket = {OPEN: 1};
let captured;
const ws = {readyState: 1, send(payload) { captured = JSON.parse(payload); }};
const restartVoiceAfterEdit = () => {}, clearAttachments = () => {};
const cancelReply = () => {}, updateSendButton = () => {};
eval(source.slice(start, end) + '\nsendMessage();');
if (captured.text !== '@codex @glm @claude review this') throw new Error('Baseline behavior changed');
console.log(JSON.stringify({id: 'E10', input: '@claude review this',
  selected: ['claude', 'codex', 'glm'], actual: captured.text}));

```

## Source excerpts

Line numbers refer to the fork source at the audit baseline. These are evidence, not operational instructions.

### wrapper.py:38

```text
38: def _write_json_mcp_settings(config_file: Path, url: str, transport: str = "http",
39:                               *, token: str = "", http_key: str = "httpUrl") -> Path:
40:     """Write/merge a settings-style JSON file with nested mcpServers config.
41:
42:     Preserves existing servers in the file — only updates the agentchattr entry.
43:
44:     Gemini CLI 0.32+ expects:
45:       - "httpUrl" key (not "url") for streamable-http transport
46:       - "url" key for SSE transport
47:       - "trust": true to skip per-call approval prompts
48:
49:     `http_key` controls which JSON key names the HTTP transport URL. Defaults
50:     to "httpUrl" (Gemini/Qwen). Providers like CodeBuddy that follow the
51:     standard MCP shape should set `mcp_http_key = "url"` in their config.
52:     Only affects settings_file / env injector modes (not the Claude flag
53:     writer or Kilo env_content writer).
54:     """
55:     config_file.parent.mkdir(parents=True, exist_ok=True)
56:     existing: dict = {}
57:     if config_file.exists():
58:         try:
59:             existing = json.loads(config_file.read_text("utf-8"))
60:         except Exception:
61:             pass
62:     servers = existing.get("mcpServers", {})
63:     # Default: Gemini-style "httpUrl" for HTTP. Override with http_key="url"
64:     # for providers that follow the standard MCP shape (e.g. CodeBuddy).
65:     if transport in ("http", "streamable-http"):
66:         entry: dict = {"type": "http", http_key: url, "trust": True}
67:     else:
68:         entry = {"type": transport, "url": url, "trust": True}
69:     if token:
70:         entry["headers"] = {"Authorization": f"Bearer {token}"}
71:     servers[SERVER_NAME] = entry
72:     existing["mcpServers"] = servers
73:
74:     # Enable folder trust so ~/.gemini/trustedFolders.json is respected
75:     security = existing.get("security", {})
76:     folder_trust = security.get("folderTrust", {})
77:     folder_trust["enabled"] = True
78:     security["folderTrust"] = folder_trust
79:     existing["security"] = security
80:
81:     config_file.write_text(json.dumps(existing, indent=2) + "\n", "utf-8")
82:     return config_file
```

### wrapper.py:163

```text
163: _VALID_INJECT_MODES = {"settings_file", "env", "flag", "proxy_flag", "env_content"}
164:
165:
166: def _provider_from_command(command: object) -> str:
167:     """Return a built-in provider for an exact configured executable name.
168:
169:     Named agent identities (for example ``claude2``) are independent of
170:     the CLI they launch.  Resolve only exact known executable basenames; do
171:     not guess from prefixes or arbitrary command text.
172:     """
173:     if not isinstance(command, str):
174:         return ""
175:     executable = command.strip().replace("\\", "/").rsplit("/", 1)[-1].lower()
176:     for suffix in (".exe", ".cmd", ".bat"):
177:         if executable.endswith(suffix):
178:             executable = executable[:-len(suffix)]
179:             break
180:     return executable if executable in _BUILTIN_DEFAULTS else ""
181:
182:
183: def _resolve_mcp_inject(agent: str, agent_cfg: dict) -> dict:
184:     """Resolve MCP injection config: explicit config > provider defaults > none."""
185:     if agent_cfg.get("mcp_inject"):
186:         return dict(agent_cfg)
187:     provider = agent
188:     if provider not in _BUILTIN_DEFAULTS:
189:         provider = _provider_from_command(agent_cfg.get("command", ""))
190:     if provider:
191:         merged = dict(_BUILTIN_DEFAULTS[provider])
192:         merged.update({k: v for k, v in agent_cfg.items() if k.startswith("mcp_")})
193:         return merged
194:     return {}
195:
196:
197: def _get_server_url(mcp_cfg: dict, transport: str) -> str:
198:     """Build the MCP server URL for the given transport."""
199:     if transport == "sse":
200:         port = mcp_cfg.get("sse_port", 8201)
201:         return f"http://127.0.0.1:{port}/sse"
202:     port = mcp_cfg.get("http_port", 8200)
203:     return f"http://127.0.0.1:{port}/mcp"
204:
```

### wrapper.py:206

```text
206: def _apply_mcp_inject(
207:     inject_cfg: dict,
208:     instance_name: str,
209:     data_dir: Path,
210:     proxy_url: str | None,
211:     *,
212:     token: str = "",
213:     mcp_cfg: dict | None = None,
214:     project_dir: Path | None = None,
215: ) -> tuple[list[str], dict[str, str], Path | None]:
216:     """Apply MCP config injection based on the resolved inject config.
217:
218:     Returns (extra_launch_args, inject_env, settings_path_or_None).
219:     settings_path is stored so re-registration can rewrite it.
220:     """
221:     mode = inject_cfg.get("mcp_inject")
222:     if not mode:
223:         return [], {}, None
224:
225:     launch_args: list[str] = []
226:     inject_env: dict[str, str] = {}
227:     settings_path: Path | None = None
228:     config_dir = data_dir / "provider-config"
229:     transport = inject_cfg.get("mcp_transport", "http")
230:     server_url = _get_server_url(mcp_cfg or {}, transport)
231:
232:     http_key = inject_cfg.get("mcp_http_key", "httpUrl")
233:
234:     if mode == "settings_file":
235:         # Write a settings JSON file at a user-specified path (e.g. .qwen/settings.json,
236:         # or ~/.codebuddy/.mcp.json for user-scope configs).
237:         raw_path = inject_cfg.get("mcp_settings_path", "")
238:         if not raw_path:
239:             raise ValueError(f"mcp_inject = 'settings_file' requires mcp_settings_path")
240:         # Expand ~ to user home (e.g. ~/.codebuddy/.mcp.json), then resolve
241:         # relative paths against project_dir/CWD as before.
242:         target = Path(raw_path).expanduser()
243:         if not target.is_absolute():
244:             base = Path(project_dir) if project_dir else Path.cwd()
245:             target = base / target
246:         settings_path = _write_json_mcp_settings(target, server_url,
247:                                                   transport=transport, token=token,
248:                                                   http_key=http_key)
249:         # Optionally set an env var pointing to the settings file
250:         env_var = inject_cfg.get("mcp_env_var")
251:         if env_var:
252:             inject_env[env_var] = str(settings_path)
```

### wrapper.py:356

```text
356: def _build_provider_launch(
357:     agent: str,
358:     agent_cfg: dict,
359:     instance_name: str,
360:     data_dir: Path,
361:     proxy_url: str | None,
362:     extra_args: list[str],
363:     env: dict[str, str],
364:     *,
365:     token: str = "",
366:     mcp_cfg: dict | None = None,
367:     project_dir: Path | None = None,
368: ) -> tuple[list[str], dict[str, str], dict[str, str], Path | None]:
369:     """Return provider-specific launch args/env/inject_env/settings_path.
370:
371:     inject_env: env vars that must propagate INTO the agent process.  On
372:     Mac/Linux these are prefixed onto the tmux command via ``env VAR=val``
373:     because subprocess.run(env=...) only affects the tmux client binary.
374:     On Windows they are simply merged into the Popen env dict.
375:     """
376:     inject_cfg = _resolve_mcp_inject(agent, agent_cfg)
377:     mcp_args, inject_env, settings_path = _apply_mcp_inject(
378:         inject_cfg, instance_name, data_dir, proxy_url,
379:         token=token, mcp_cfg=mcp_cfg, project_dir=project_dir,
380:     )
381:
382:     launch_args = [*mcp_args, *extra_args]
383:     launch_env = dict(env)
384:
385:     return launch_args, launch_env, inject_env, settings_path
```

### wrapper.py:473

```text
473: def _queue_watcher(get_identity_fn, inject_fn, *, is_multi_instance: bool = False, trigger_flag=None,
474:                    server_port: int = 8300, agent_name: str = "", get_token_fn=None,
475:                    refresh_interval: int = 10):
476:     """Poll queue file and inject an MCP read task when triggered."""
477:     first_mention = True
478:     last_rules_epoch = 0  # 0 = unknown/cold start — will inject on first trigger
479:     trigger_count = 0
480:     while True:
481:         try:
482:             _, queue_file = get_identity_fn()
483:             if queue_file.exists() and queue_file.stat().st_size > 0:
484:                 with open(queue_file, "r", encoding="utf-8") as f:
485:                     lines = f.readlines()
486:                 queue_file.write_text("", "utf-8")
487:
488:                 has_trigger = False
489:                 channel = "general"
490:                 for line in lines:
491:                     line = line.strip()
492:                     if not line:
493:                         continue
494:                     try:
495:                         data = json.loads(line)
496:                     except json.JSONDecodeError:
497:                         continue
498:                     has_trigger = True
499:                     if isinstance(data, dict) and "channel" in data:
500:                         channel = data["channel"]
501:
502:                 if has_trigger:
503:                     # Signal activity BEFORE injecting — covers the thinking phase
504:                     if trigger_flag is not None:
505:                         trigger_flag[0] = True
506:                     time.sleep(0.5)
507:
508:                     # Check if this is a job/activity-scoped trigger
509:                     job_id = None
510:                     custom_prompt = ""
511:                     for line in lines:
512:                         line = line.strip()
513:                         if not line:
514:                             continue
515:                         try:
516:                             data = json.loads(line)
517:                             if isinstance(data, dict) and "job_id" in data:
518:                                 job_id = data["job_id"]
519:                             if isinstance(data, dict):
520:                                 raw_prompt = data.get("prompt", "")
521:                                 if isinstance(raw_prompt, str) and raw_prompt.strip():
522:                                     custom_prompt = raw_prompt.strip()
523:                         except json.JSONDecodeError:
524:                             pass
525:
526:                     if custom_prompt:
527:                         prompt = custom_prompt
528:                     elif job_id:
529:                         prompt = f"use mcp to read job_id={job_id} - you're mentioned in a job thread, take appropriate action and respond"
530:                     else:
531:                         prompt = f"use mcp to read #{channel} - you're mentioned, take appropriate action and respond"
532:
533:                     # Use current identity (may have changed via rename)
534:                     current_name, _ = get_identity_fn()
535:                     # Append role if set — check both current name and base name
536:                     role = _fetch_role(server_port, current_name)
537:                     if not role and current_name != agent_name:
538:                         role = _fetch_role(server_port, agent_name)
539:                     if role:
540:                         prompt += f"\n\nROLE: {role}"
541:
542:                     # Smart rules injection: first trigger, epoch change, or periodic refresh
543:                     _token = get_token_fn() if get_token_fn else ""
544:                     rules_data = _fetch_active_rules(server_port, _token)
545:                     trigger_count += 1
546:                     if rules_data:
547:                         # Use server-side refresh_interval (live from settings UI)
548:                         ri = rules_data.get("refresh_interval", refresh_interval)
549:                         need_inject = (
550:                             last_rules_epoch == 0
551:                             or rules_data["epoch"] != last_rules_epoch
552:                             or (ri > 0 and trigger_count % ri == 0)
553:                         )
554:                         if need_inject:
555:                             if rules_data["rules"]:
556:                                 rules_text = "; ".join(rules_data["rules"])
557:                                 prompt += f"\n\nRULES:\n{rules_text}"
558:                             last_rules_epoch = rules_data["epoch"]
559:                             _report_rule_sync(server_port, current_name, rules_data["epoch"], _token)
560:
561:                     if first_mention and is_multi_instance:
562:                         prompt += _IDENTITY_HINT
563:                         first_mention = False
564:                     # Flatten to single line — multi-line text triggers paste
565:                     # detection in CLIs (Claude Code shows "[Pasted text +N]")
566:                     # which can break injection of long session prompts
567:                     inject_fn(prompt.replace("\n", " "))
568:         except Exception:
569:             pass
570:
571:         time.sleep(1)
```

### wrapper.py:630

```text
630:     # Resolve MCP injection mode to determine if a proxy is needed.
631:     # Direct-connect modes (settings_file, env, flag) don't need a proxy.
632:     # proxy_flag mode needs a proxy. No mcp_inject = proxy fallback.
633:     inject_cfg = _resolve_mcp_inject(agent, agent_cfg)
634:     inject_mode = inject_cfg.get("mcp_inject", "")
635:     if inject_mode and inject_mode not in _VALID_INJECT_MODES:
636:         print(f"  Error: unknown mcp_inject mode '{inject_mode}' for agent '{agent}'.")
637:         print(f"  Valid modes: {', '.join(sorted(_VALID_INJECT_MODES))}")
638:         sys.exit(1)
639:     needs_proxy = inject_mode in ("proxy_flag", "") or not inject_mode
```

### wrapper.py:916

```text
916:     try:
917:         run_agent(**run_kwargs)
918:     finally:
919:         try:
920:             current_name, _ = get_identity()
921:             current_token = get_token()
922:             dereg_req = urllib.request.Request(
923:                 f"http://127.0.0.1:{server_port}/api/deregister/{current_name}",
924:                 method="POST",
925:                 data=b"",
926:                 headers=_auth_headers(current_token),
927:             )
928:             urllib.request.urlopen(dereg_req, timeout=5)
929:             print(f"  Deregistered {current_name}")
930:         except Exception:
931:             pass
932:
933:         if proxy is not None:
934:             proxy.stop()
935:
936:     print("  Wrapper stopped.")
937:
938:
939: if __name__ == "__main__":
940:     main()
```

### wrapper_windows.py:410

```text
410: def run_agent(command, extra_args, cwd, env, queue_file, agent, no_restart, start_watcher, strip_env=None, pid_holder=None, session_name=None, inject_env=None, inject_delay: float = 0.3, enter_backend: str = "console_input"):
411:     """Run agent as a direct subprocess, inject via Win32 console."""
412:     # Newer codex/claude/etc TUIs require VT processing on the parent console;
413:     # without this, ANSI escape sequences leak as text into the terminal.
414:     # One-shot at startup (with diagnostic print) then a keepalive thread.
415:     enable_vt_mode()
416:     _vt_keepalive_thread()
417:
418:     if inject_env:
419:         env = {**env, **inject_env}
420:     start_watcher(lambda text: inject(text, delay=inject_delay, enter_backend=enter_backend))
421:
422:     while True:
423:         try:
424:             proc = subprocess.Popen([command] + extra_args, cwd=cwd, env=env)
425:             if pid_holder is not None:
426:                 pid_holder[0] = proc.pid
427:             proc.wait()
428:             if pid_holder is not None:
429:                 pid_holder[0] = None
430:
431:             if no_restart:
432:                 break
433:
434:             print(f"\n  {agent.capitalize()} exited (code {proc.returncode}).")
435:             print(f"  Restarting in 3s... (Ctrl+C to quit)")
436:             time.sleep(3)
437:         except KeyboardInterrupt:
438:             break
```

### wrapper_api.py:80

```text
80:     # Model API config
81:     base_url = agent_cfg.get("base_url", "").rstrip("/")
82:     if not base_url:
83:         print(f"  Error: [agents.{agent}] must have base_url (e.g. http://localhost:8189/v1)")
84:         sys.exit(1)
85:     model = agent_cfg.get("model", "")
86:     api_key_env = agent_cfg.get("api_key_env", "")
87:     api_key = os.environ.get(api_key_env, "") if api_key_env else ""
88:     temperature = agent_cfg.get("temperature")
89:     if temperature is not None:
90:         temperature = float(temperature)
91:         # Clamp: some providers (e.g. MiniMax) require temperature in (0.0, 1.0]
92:         if temperature <= 0:
93:             temperature = 0.01
94:         if temperature > 2.0:
95:             temperature = 2.0
96:     context_messages = int(agent_cfg.get("context_messages", 20))
97:     system_prompt = agent_cfg.get("system_prompt",
98:         f"You are {agent_cfg.get('label', agent)}, a helpful AI assistant participating "
99:         "in a developer chat room. Keep responses concise and relevant. "
100:         "You can see recent messages for context.")
```

### wrapper_api.py:204

```text
204:     def read_messages(channel="general", since_id=0, limit=20):
205:         params = f"limit={limit}&channel={channel}"
206:         if since_id:
207:             params = f"since_id={since_id}&{params}"
208:         req = urllib.request.Request(
209:             f"http://127.0.0.1:{server_port}/api/messages?{params}",
210:             headers=_auth_headers(get_token()),
211:         )
212:         with urllib.request.urlopen(req, timeout=10) as resp:
213:             return json.loads(resp.read())
214:
215:     # Send message back to chat
216:     def send_message(text, channel="general"):
217:         body = json.dumps({"text": text, "channel": channel}).encode()
218:         req = urllib.request.Request(
219:             f"http://127.0.0.1:{server_port}/api/send",
220:             method="POST",
221:             data=body,
222:             headers=_auth_headers(get_token(), include_json=True),
223:         )
224:         with urllib.request.urlopen(req, timeout=10) as resp:
225:             return json.loads(resp.read())
226:
227:     # Call OpenAI-compatible chat completions API
228:     def call_model(messages):
229:         url = f"{base_url}/chat/completions"
230:         payload = {"messages": messages}
231:         if model:
232:             payload["model"] = model
233:         if temperature is not None:
234:             payload["temperature"] = temperature
235:         body = json.dumps(payload).encode()
236:
237:         headers = {"Content-Type": "application/json"}
238:         if api_key:
239:             headers["Authorization"] = f"Bearer {api_key}"
240:
241:         req = urllib.request.Request(url, method="POST", data=body, headers=headers)
242:         with urllib.request.urlopen(req, timeout=120) as resp:
243:             data = json.loads(resp.read())
244:         return data["choices"][0]["message"]["content"]
```

### wrapper_api.py:247

```text
247:     def format_messages(chat_msgs):
248:         my_name = get_name()
249:
250:         # Build dynamic system prompt with online status, role, and mention instructions
251:         online = get_online_agents()
252:         others = [n for n in online if n != my_name]
253:         parts = [system_prompt]
254:         # Inject role if set
255:         my_role = get_my_role()
256:         if my_role:
257:             parts.append(f"role: {my_role}")
258:         if others:
259:             parts.append(f"Currently online: {', '.join(others)}.")
260:             parts.append("To mention another agent and trigger them to respond, "
261:                          "use @name (e.g. " + ", ".join(f"@{n}" for n in others[:3]) + ").")
262:         parts.append(f"Your name in this chat is {my_name}. Do not prefix your "
263:                      "messages with your own name.")
264:
265:         messages = [{"role": "system", "content": " ".join(parts)}]
266:         for msg in chat_msgs:
267:             sender = msg.get("sender", "")
268:             text = msg.get("text", "")
269:             if sender == "system":
270:                 continue
271:             role = "assistant" if sender == my_name else "user"
272:             messages.append({"role": role, "content": f"{sender}: {text}"})
273:         return messages
274:
275:     # Handle a trigger — read context, call model, respond
276:     def handle_trigger(channel="general"):
277:         my_name = get_name()
278:         set_working(True)
279:         try:
280:             chat_msgs = read_messages(channel=channel, limit=context_messages)
281:             if not chat_msgs:
282:                 return
283:
284:             messages = format_messages(chat_msgs)
285:             print(f"  [{channel}] Calling model with {len(messages)} messages...")
286:
287:             response = call_model(messages)
288:             response = response.strip()
289:             if not response:
290:                 return
291:
292:             # Strip self-prefix if the model echoes its own name
293:             prefixes = [f"{my_name}: ", f"{my_name}:"]
294:             for prefix in prefixes:
295:                 if response.startswith(prefix):
296:                     response = response[len(prefix):]
297:                     break
298:
299:             send_message(response, channel=channel)
300:             print(f"  [{channel}] Responded ({len(response)} chars)")
301:         except Exception as exc:
302:             print(f"  Error handling trigger: {exc}")
303:         finally:
```

### wrapper_api.py:306

```text
306:     # Queue watcher — polls queue file for @mentions
307:     queue_file = data_dir / f"{name}_queue.jsonl"
308:     if queue_file.exists():
309:         queue_file.write_text("", "utf-8")
310:
311:     print(f"\n  === {agent_cfg.get('label', agent)} API Wrapper ===")
312:     print(f"  Model endpoint: {base_url}/chat/completions")
313:     if model:
314:         print(f"  Model: {model}")
315:     print(f"  @{name} mentions trigger model calls")
316:     print(f"  Ctrl+C to stop\n")
317:
318:     try:
319:         while True:
320:             try:
321:                 # Update queue file path in case of rename
322:                 current_name = get_name()
323:                 qf = data_dir / f"{current_name}_queue.jsonl"
324:
325:                 if qf.exists() and qf.stat().st_size > 0:
326:                     with open(qf, "r", encoding="utf-8") as f:
327:                         lines = f.readlines()
328:                     qf.write_text("", "utf-8")
329:
330:                     channels_triggered = set()
331:                     for line in lines:
332:                         line = line.strip()
333:                         if not line:
334:                             continue
335:                         try:
336:                             data = json.loads(line)
337:                             ch = data.get("channel", "general") if isinstance(data, dict) else "general"
338:                             channels_triggered.add(ch)
339:                         except json.JSONDecodeError:
340:                             channels_triggered.add("general")
341:
342:                     for ch in channels_triggered:
343:                         handle_trigger(channel=ch)
344:             except Exception:
345:                 pass
346:
347:             time.sleep(1)
```

### session_engine.py:79

```text
79:     def end_session(self, session_id: int, reason: str = "ended by user") -> dict | None:
80:         """End a session early."""
81:         session = self._store.interrupt(session_id, reason)
82:         if session:
83:             log.info("Session %d interrupted: %s", session_id, reason)
84:         return session
85:
86:     def get_active(self, channel: str) -> dict | None:
87:         """Get the active session for a channel, enriched with phase info."""
88:         session = self._store.get_active(channel)
89:         if not session:
90:             return None
91:         return self._enrich(session)
92:
93:     def get_allowed_agent(self, channel: str) -> str | None:
94:         """If a session is active on this channel, return the agent whose turn it is.
95:         Returns None if no session is active (meaning all agents are allowed)."""
96:         session = self._store.get_active(channel)
97:         if not session or session.get("state") not in ("active", "waiting"):
98:             return None
99:         return self._get_expected_agent(session)
```

### session_engine.py:131

```text
131:     def _on_message(self, msg: dict):
132:         """Called on every new chat message. Checks if it advances a session."""
133:         channel = msg.get("channel", "general")
134:         sender = msg.get("sender", "")
135:
136:         # Ignore system-generated messages (banners, phase markers, etc.)
137:         if sender == "system" or msg.get("type", "chat") not in ("chat", "decision"):
138:             return
139:
140:         with self._lock:
141:             self._handle_participant_message(msg, channel, sender)
142:
143:     def _handle_participant_message(self, msg: dict, channel: str, sender: str):
144:         session = self._store.get_active(channel)
145:         if not session:
146:             return
147:
148:         expected_agent = self._get_expected_agent(session)
149:         if not expected_agent:
150:             return
151:
152:         cast_agents = set(session.get("cast", {}).values())
153:         sender_is_agent = self._is_agent(sender)
154:
155:         # Agent not in this session's cast — ignore
156:         if sender_is_agent and sender not in cast_agents:
157:             return
158:
159:         # A choice card asks for input; it is not the participant's completed turn.
160:         if msg.get("type") == "decision":
161:             if sender == expected_agent:
162:                 self._store.set_choice(session["id"], msg["id"])
163:             return
164:
165:         choice_id = session.get("choice_message_id")
166:         if choice_id is not None and not sender_is_agent and msg.get("reply_to") is not None:
167:             choice = self._messages.get_by_id(msg["reply_to"])
168:             if (choice and choice.get("type") == "decision"
169:                     and (choice.get("metadata") or {}).get("resolved")):
170:                 if msg["reply_to"] == choice_id:
171:                     self._store.set_choice(session["id"], None)
172:                 # Normal @mention routing wakes the participant with the answer.
173:                 # An older card must not release the current question.
174:                 return
175:
176:         # Human spoke but it's not their turn — pause if an agent is expected
177:         if not sender_is_agent and sender != expected_agent and self._is_agent(expected_agent):
178:             if choice_id is not None:
179:                 self._store.set_choice(session["id"], None)
180:             self._store.pause(session["id"])
181:             log.info("Session %d paused: human interruption by %s", session["id"], sender)
182:             return
183:
184:         if sender == expected_agent:
185:             if choice_id is not None:
186:                 return
187:             # Auto-resume if paused
188:             if session["state"] == "paused":
189:                 self._store.resume(session["id"])
190:             # Defer advance slightly so the triggering message broadcasts
191:             # before phase/completion banners are added
192:             threading.Timer(0.3, self._advance, args=(session, msg["id"])).start()
193:             return
194:
195:         # Wrong agent spoke - ignore
196:         return
197:
198:     # --- Engine core ---
199:
200:     def _advance(self, session: dict, message_id: int):
201:         """Advance once, only if this response still belongs to the current turn."""
202:         with self._lock:
203:             current = self._store.get(session["id"])
204:             if (not current or current["state"] not in ("active", "waiting")
205:                     or current.get("choice_message_id") is not None
206:                     or message_id <= current.get("last_choice_message_id", -1)
207:                     or (current["current_phase"], current["current_turn"])
208:                     != (session["current_phase"], session["current_turn"])):
209:                 return
210:             self._advance_current(current, message_id)
```

### session_engine.py:258

```text
258:
259:     def _trigger_current(self, session: dict):
260:         """Trigger the agent whose turn it is."""
261:         tmpl = self._store.get_template(session["template_id"])
262:         if not tmpl:
263:             return
264:
265:         phases = tmpl.get("phases", [])
266:         phase_idx = session["current_phase"]
267:         turn_idx = session["current_turn"]
268:
269:         if phase_idx >= len(phases):
270:             return
271:
272:         phase = phases[phase_idx]
273:         participants = phase.get("participants", [])
274:
275:         if turn_idx >= len(participants):
276:             return
277:
278:         role = participants[turn_idx]
279:         cast = session.get("cast", {})
280:         agent = cast.get(role)
281:
282:         if not agent:
283:             log.warning("Session %d: no agent cast for role '%s'", session["id"], role)
284:             self._store.interrupt(session["id"], f"no agent for role '{role}'")
285:             return
286:
287:         if not self._is_agent(agent):
288:             # Human's turn - just mark as waiting, don't trigger
289:             self._store.set_waiting(session["id"], agent)
290:             return
291:
292:         # Mark waiting
293:         self._store.set_waiting(session["id"], agent)
294:
295:         # Assemble the prompt
296:         prompt = self._assemble_prompt(session, tmpl, phase, role)
297:
298:         # Trigger the agent
299:         channel = session.get("channel", "general")
300:         log.info("Session %d: triggering %s (%s) for phase '%s'",
301:                  session["id"], agent, role, phase["name"])
302:
303:         try:
304:             self._trigger.trigger_sync(agent, channel=channel, prompt=prompt)
305:         except Exception as exc:
306:             log.error("Session %d: failed to trigger %s: %s",
307:                       session["id"], agent, exc)
308:
309:     def _assemble_prompt(self, session: dict, tmpl: dict, phase: dict,
310:                          role: str) -> str:
311:         """Build the session-aware prompt for an agent."""
312:         phases = tmpl.get("phases", [])
313:         phase_idx = session["current_phase"]
314:         total_phases = len(phases)
315:
316:         channel = session.get("channel", "general")
317:         lines = [
318:             f"SESSION: {tmpl.get('name', '?')}",
319:         ]
320:         if session.get("goal"):
321:             lines.append(f"GOAL: {session['goal']}")
322:         lines.append(f"PHASE: {phase['name']} ({phase_idx + 1}/{total_phases})")
323:         lines.append(f"YOUR ROLE: {role}")
324:         lines.append(f"INSTRUCTION: {phase.get('prompt', '')}")
325:
326:         # Dissent mandate for review/critique roles
327:         if role.lower() in _DISSENT_ROLES:
328:             lines.append(f"\n{_DISSENT_LINE}")
329:
330:         lines.append("")
331:         lines.append(f"IMPORTANT: You MUST respond using the 'chat_send' tool in the #{channel} channel. "
332:                       "The session flow is blocked until your message appears in the chat. "
333:                       "Do NOT respond only in your terminal.")
334:         lines.append("Read recent messages in the channel for context (use 'chat_read' or 'mcp read'), "
335:                       "then post your response. Stay focused on the session goal.")
336:
337:         # Use double newlines to ensure separation in TUIs that might collapse single newlines
338:         return "\n\n".join(lines)
```

### session_store.py:324

```text
324: def validate_session_template(tmpl: dict) -> list[str]:
325:     """Validate a session template dict. Returns list of errors (empty = valid)."""
326:     errors = []
327:
328:     if not isinstance(tmpl, dict):
329:         return ["Template must be a JSON object"]
330:
331:     if not tmpl.get("name") or not isinstance(tmpl.get("name"), str):
332:         errors.append("Missing or invalid 'name' (string required)")
333:
334:     roles = tmpl.get("roles", [])
335:     if not isinstance(roles, list) or len(roles) == 0:
336:         errors.append("'roles' must be a non-empty array")
337:     elif len(roles) > 6:
338:         errors.append(f"Too many roles ({len(roles)}, max 6)")
339:
340:     phases = tmpl.get("phases", [])
341:     if not isinstance(phases, list) or len(phases) == 0:
342:         errors.append("'phases' must be a non-empty array")
343:     elif len(phases) > 6:
344:         errors.append(f"Too many phases ({len(phases)}, max 6)")
345:
346:     roles_set = set(roles) if isinstance(roles, list) else set()
347:     output_count = 0
348:
349:     for i, phase in enumerate(phases if isinstance(phases, list) else []):
350:         if not isinstance(phase, dict):
351:             errors.append(f"Phase {i + 1}: must be an object")
352:             continue
353:         if not phase.get("name"):
354:             errors.append(f"Phase {i + 1}: missing 'name'")
355:         participants = phase.get("participants", [])
356:         if not isinstance(participants, list) or len(participants) == 0:
357:             errors.append(f"Phase {i + 1}: 'participants' must be a non-empty array")
358:         elif len(participants) > 4:
359:             errors.append(f"Phase {i + 1}: too many participants ({len(participants)}, max 4)")
360:         for p in (participants if isinstance(participants, list) else []):
361:             if p not in roles_set:
362:                 errors.append(f"Phase {i + 1}: participant '{p}' not in roles list")
363:         prompt = phase.get("prompt", "")
364:         if isinstance(prompt, str) and len(prompt) > 200:
365:             errors.append(f"Phase {i + 1}: prompt too long ({len(prompt)} chars, max 200)")
366:         if phase.get("is_output"):
367:             output_count += 1
368:
369:     if output_count == 0 and isinstance(phases, list) and len(phases) > 0:
370:         errors.append("No phase marked as 'is_output: true'")
371:     elif output_count > 1:
372:         errors.append(f"Multiple phases marked as output ({output_count}, expected 1)")
373:
374:     return errors
```

### static/chat.js:2484

```text
2484: function sendMessage() {
2485:     const input = document.getElementById('input');
2486:     let text = input.value.trim();
2487:
2488:     if (!text && pendingAttachments.length === 0) return;
2489:
2490:     // Prepend active mention toggles if the message doesn't already mention them
2491:     // Skip for non-broadcast slash commands (e.g. /clear, /continue)
2492:     let skipMentions = false;
2493:     if (text.startsWith('/')) {
2494:         const cmdWord = text.split(/\s/)[0].toLowerCase();
2495:         const matchedCmd = SLASH_COMMANDS.find(c => c.cmd.startsWith(cmdWord) || cmdWord.startsWith(c.cmd.split(/\s/)[0]));
2496:         if (matchedCmd && !matchedCmd.broadcast) {
2497:             skipMentions = true;
2498:         }
2499:         // Commands that need an @mention — show hint and keep command in input
2500:         if (matchedCmd && matchedCmd.needsMention && !/@\w[\w-]*/.test(text)) {
2501:             const canonical = matchedCmd.cmd.split(/\s/)[0];  // e.g. '/summary'
2502:             input.value = canonical + ' @';
2503:             input.focus();
2504:             input.setSelectionRange(input.value.length, input.value.length);
2505:             showSlashHint(`Tag an agent: ${canonical} @claude`);
2506:             // Trigger mention autocomplete for the '@'
2507:             input.dispatchEvent(new Event('input', { bubbles: true }));
2508:             return;
2509:         }
2510:     }
2511:     if (activeMentions.size > 0 && text && !skipMentions) {
2512:         const prefix = [...activeMentions].map(n => `@${n}`).join(' ');
2513:         // Only prepend if user didn't already @mention these agents
2514:         const lower = text.toLowerCase();
2515:         const missing = [...activeMentions].filter(n => !lower.includes(`@${n}`));
2516:         if (missing.length > 0) {
2517:             text = missing.map(n => `@${n}`).join(' ') + ' ' + text;
2518:         }
2519:     }
2520:
2521:     const payload = {
2522:         type: 'message',
2523:         text: text,
2524:         sender: username,
2525:         channel: activeChannel,
2526:         attachments: pendingAttachments.map(a => ({
2527:             path: a.path,
2528:             name: a.name,
2529:             url: a.url,
2530:         })),
2531:     };
2532:     if (replyingTo) {
2533:         payload.reply_to = replyingTo.id;
2534:     }
2535:
2536:     if (ws && ws.readyState === WebSocket.OPEN) {
2537:         ws.send(JSON.stringify(payload));
2538:     }
2539:
2540:     input.value = '';
2541:     restartVoiceAfterEdit();
2542:     input.style.height = 'auto';
2543:     clearAttachments();
2544:     cancelReply();
2545:     updateSendButton();
2546:     input.focus();
2547: }
2548:
2549: // --- Image paste/drop ---
```

### windows/start_api_agent.bat:1

```text
1: @echo off
2: REM agentchattr — starts server (if not running) + API agent wrapper
3: REM Usage: start_api_agent.bat <agent_name>
4: REM Example: start_api_agent.bat qwen
5: cd /d "%~dp0.."
6:
7: set AGENT_NAME=%~1
8: if "%AGENT_NAME%"=="" (
9:     echo.
10:     echo   agentchattr — API Agent Launcher
11:     echo   ---------------------------------
12:     echo   Enter the agent name from your config.local.toml
13:     echo   Example: qwen, mistral, llama, deepseek
14:     echo.
15:     set /p AGENT_NAME="  Agent name: "
16: )
17: if "%AGENT_NAME%"=="" (
18:     echo   Error: No agent name provided.
19:     pause
20:     exit /b 1
21: )
22:
23: REM Auto-create venv and install deps on first run
24: if not exist ".venv" (
25:     python -m venv .venv
26:     .venv\Scripts\pip install -q -r requirements.txt >nul 2>nul
27: )
28: call .venv\Scripts\activate.bat
29:
30: REM Start server if not already running, then wait for it
31: netstat -ano | findstr :8300 | findstr LISTENING >nul 2>&1
32: if %errorlevel% neq 0 (
33:     start "agentchattr server" cmd /c "python run.py"
34: )
35: :wait_server
36: netstat -ano | findstr :8300 | findstr LISTENING >nul 2>&1
37: if %errorlevel% neq 0 (
38:     timeout /t 1 /nobreak >nul
39:     goto :wait_server
40: )
41:
42: python wrapper_api.py %AGENT_NAME%
43: pause
```

### macos-linux/start_api_agent.sh:1

```text
1: #!/usr/bin/env sh
2: # agentchattr — starts server (if not running) + API agent wrapper
3: # Usage: sh start_api_agent.sh <agent_name>
4: # Example: sh start_api_agent.sh qwen
5: cd "$(dirname "$0")/.."
6:
7: if [ -z "$1" ]; then
8:     echo "Usage: start_api_agent.sh <agent_name>"
9:     echo "Example: start_api_agent.sh qwen"
10:     exit 1
11: fi
12:
13: PYTHON_BIN=""
14: if command -v python3 >/dev/null 2>&1; then
15:     PYTHON_BIN="python3"
16: elif command -v python >/dev/null 2>&1; then
17:     PYTHON_BIN="python"
18: else
19:     echo "Python 3 is required but was not found on PATH."
20:     exit 1
21: fi
22:
23: ensure_venv() {
24:     if [ -d ".venv" ] && [ ! -x ".venv/bin/python" ]; then
25:         echo "Recreating .venv for this platform..."
26:         rm -rf .venv
27:     fi
28:
29:     if [ ! -x ".venv/bin/python" ]; then
30:         echo "Creating virtual environment..."
31:         "$PYTHON_BIN" -m venv .venv || {
32:             echo "Error: failed to create .venv with $PYTHON_BIN."
33:             exit 1
34:         }
35:         .venv/bin/python -m pip install -q -r requirements.txt || {
36:             echo "Error: failed to install Python dependencies."
37:             exit 1
38:         }
39:     fi
40: }
41:
42: is_server_running() {
43:     lsof -i :8300 -sTCP:LISTEN >/dev/null 2>&1 || \
44:     ss -tlnp 2>/dev/null | grep -q ':8300 '
45: }
46:
47: ensure_venv
48:
49: if ! is_server_running; then
50:     if [ "$(uname -s)" = "Darwin" ]; then
51:         osascript -e "tell app \"Terminal\" to do script \"cd '$(pwd)' && .venv/bin/python run.py\"" > /dev/null 2>&1
52:     else
53:         if command -v gnome-terminal >/dev/null 2>&1; then
54:             gnome-terminal -- sh -c "cd '$(pwd)' && .venv/bin/python run.py; printf 'Press Enter to close... '; read _"
55:         elif command -v xterm >/dev/null 2>&1; then
56:             xterm -e sh -c "cd '$(pwd)' && .venv/bin/python run.py" &
57:         else
58:             .venv/bin/python run.py > data/server.log 2>&1 &
59:         fi
60:     fi
61:
62:     i=0
63:     while [ "$i" -lt 30 ]; do
64:         if is_server_running; then
65:             break
66:         fi
67:         sleep 0.5
68:         i=$((i + 1))
69:     done
70: fi
71:
72: .venv/bin/python wrapper_api.py "$1"
```

## Captured verification output

- Pinned application source diff: exit 0; no source changes against d775776a30e8af4c85ea16b3caaf9c79d65cb239.
- Inventory: 79 selected paths, 54 same / 16 different / 2 fork-only / 7 installation-only.
- Python harness: all 10 characterization observations returned successfully, including optional E11 using existing PyYAML. Full structured observations are in the embedded JSON above.
- Node harness: {"id":"E10","input":"@claude review this","selected":["claude","codex","glm"],"actual":"@codex @glm @claude review this"}.
- Existing MCP writer tests: Ran 8 tests; OK. Default sandbox temporary paths first failed with PermissionError; rerun redirected Python tempfile.tempdir into workspace .audit-tmp and passed. No source test changes were needed.
- Git diff whitespace check: exit 0. Python AST, JSON parsing and Markdown fence checks passed.
- No full application-suite, provider, native console, complete process lifecycle, current client authentication, or Linux run was performed.

## Ticket facts verified through GitHub

Explicit repository sjgold/agentchattr: #1 Establish the launcher baseline is open and has no blockers. #4 Launch a configured CLI seat is blocked by #2. #6 Deliver a frozen review brief to every seat is blocked by #3 and #4. The 26 approved tickets remain open. Bodies link spec v1.6; local STATUS.md selects v1.7. No issue state/body/comment was changed.

The audit/plan pack is the requested deliverable. Application fixes, independent review approval and human completion are separate states.

## Complete authoritative specification

SHA-256: `845ce4a28220d6ddb6f9c452c256d55a835a34f4015a0070d7ef1a32eda1f614`

````markdown
# Agentchattr review fork — product and implementation specification

Version: 1.7 · 12 October 2026 · Author: Haalee

Status: implementation specification for review. This document authorizes no deployment, provider purchase, or upstream submission. No application implementation has begun.

## 1. Outcome and scope

Make agentchattr easy to launch and operate for documentation review, adversarial analysis, and other coordinator-designed sessions. Build on its existing chat page, session proposals, roles, and conversation engine.

The entry flow is **open app → pre-flight → select/configure an agent package → setup and launch → existing chat page**. A user-selected coordinator determines teams, roles, and rounds at the beginning of each session. Session creation stays in the existing chat Ask / Design a session feature, after pre-flight hands off. Pre-flight configures and launches the agent package; it does not create the session or decide rounds. The user can modify the coordinator proposal in chat. Neither the six phases in earlier transcripts nor the current manual intake order is a required workflow.

The first usable milestone provides a saved, model-configured team, consistent delivery of review inputs, and reliable Stop/correct/restart. The full scope adds document intake, requested deliverables with an in-app reader, Markdown export, channel archival, and optional independent review with quote checks.

The product direction is one application replacing the separate Warroom and Tribunal user experiences. Flexible coordinator-designed sessions remain the default. Independent review adds fresh API first passes and quotation checks when selected; it shares launch, documents, cancellation, history, and artifacts rather than becoming another product. Do not retire either existing project or migrate/delete its data merely because this spec describes its replacement.

### In scope

- Windows-first bootstrap, environment checks, supervised launch, and saved packages.
- Per-seat client, provider, model, and supported reasoning settings.
- Common input and completion contracts for CLI and API participants.
- Bounded Hermes/OMP diagnosis without blocking the working clients.
- Stop, correction, restart, explicit recipient precedence, and recovery.
- Pasted text and Markdown/plain-text documents retained throughout a run.
- Coordinator-requested artifacts, revisions, preview, and local downloads.
- Discoverable channel management and archive.
- Optional independent API first passes, mechanical quote flags, and synthesis that preserves serious findings.

### Not required for this release

- Rewriting the app in a desktop framework or replacing its chat interface.
- A fixed review methodology, mandatory round count, or mandatory synthesis format for ordinary sessions. Independent review uses the lightweight requirements below.
- Guaranteed compatibility with every model available through Hermes or OMP.
- PDF/DOCX extraction, OCR, interactive HTML artifacts, or public sharing.
- Hosted accounts, multi-user permissions, or remote access.
- Making every API model a general-purpose filesystem agent.
- Mandatory blind-review isolation in ordinary sessions. Independent review builds API requests without peer answers or shared history.

## 2. Baseline and evidence

Start from a recorded commit of https://github.com/bcurts/agentchattr in a proper fork. The inspected Desktop distribution has no Git metadata and contains local additions. Compare it against the selected upstream baseline before carrying over code. Preserve the currently working installation and its data.

The October 9 Combat Paper Walkthrough report records successful use of Claude, Codex, Antigravity, Muse, GLM, and DeepSeek. Classify these as **demonstrated working on October 9**, not as unproven merely because this audit did not relaunch them. This evidence does not establish their filesystem capabilities or every model combination.

OMP and Hermes are installed in the audited environment. Five isolated configuration tests passed; complete interactive review operation remains unverified. CodeBuddy was not resolved on the audit shell's PATH. These observations need timestamps and must not be confused with a live readiness check.

Tribunal runs through OMP with a different execution architecture; the user does not see rounds as live chat turns. Its handoff and August 26 state record completed panel runs. The internal `workflows/lib/hosts/omp.host.ts` file is an implementation detail of that execution path, not an existing agentchattr integration. Use the operational lessons as evidence about prior OMP use, not proof that agentchattr's interactive OMP seat works. No plug-in reuse of Tribunal's runner is assumed. Tribunal's implementation is not a reuse target; its historical behavior informed the product discussion. Its older README does not fully describe the later standalone engine.

Source findings to recheck against the fork baseline:

- API queue processing drops custom session instructions and defaults to 20 recent messages.
- The API adapter exposes no filesystem tools and does not load attachments into model context.
- End Session changes stored state without cancelling active work or queued dispatch.
- Any expected agent chat response can advance a turn; a paused session can resume on that response.
- Selected recipient buttons add mentions even when the user explicitly addresses one agent.
- New API launchers inherit hard-coded port checks and unbounded waits.
- The Windows runner does not propagate a failed CLI exit code.
- OMP's JSON configuration writer can overwrite malformed existing configuration.
- The local history ZIP route requires an absent `archive` module. Upstream contains an `archive.py`; establish whether this is a distribution defect before proposing an upstream fix.

## 3. Product terms

- **Client:** the execution host, such as Claude CLI, Codex CLI, Antigravity, Hermes, OMP, or the direct API adapter.
- **Provider/model:** the service and model used by that client. Do not use a model name as a substitute for client identity.
- **Seat:** a stable member of a package with a display name and launch configuration. Session roles are assigned to seats separately.
- **Package:** a reusable set of seats and an optional preferred coordinator; it does not encode required rounds.
- **Session design:** the coordinator's proposed roles, phases, prompts, and assignments, editable before execution.
- **Run:** one execution of a frozen design and input revision. A corrected restart creates a new run.
- **Turn:** one dispatched unit of work, identified independently of chat messages.
- **Document packet:** immutable source text and metadata supplied to a run.
- **Artifact:** a saved deliverable and its revisions, associated with a session/run. This is an agentchattr feature, not a Clairvoyance Exhibit.

## 4. Pre-flight and launch

### PF-1 — One entry point

Provide one Windows shortcut backed by a small bootstrap. It starts or reconnects to the local server and opens pre-flight. Pre-flight cannot depend on a server the user must first start by hand.

Use the configured port and an app-specific health response, not a generic successful HTTP response or port-listening check. Serialize first-run setup and service startup. Opening the shortcut twice reuses the service. If another application occupies the port, report a conflict without terminating it.

### PF-2 — Honest detection

For each selected seat, distinguish executable found, client startup checked, authentication known/unknown, adapter connected, and ready for the requested capability. Display the resolved executable, client version when available, and last verification time. A successful `--help` is not proof of authentication, file access, or chat operation.

Passive detection must not install packages, invoke a model, or rewrite provider configuration. Setup actions may create dependencies and required client configuration after the user chooses Setup/Launch and sees the required changes. Reuse existing login mechanisms and secret references; never store secrets in saved packages or expose them in diagnostics. Provider calls used for verification must be clearly identified as usage-consuming.

Use bounded checks. Proposed defaults: 15 seconds per passive CLI probe and 60 seconds for server readiness. Login has a distinct user-action state; it must not look like unexplained startup failure. Expose diagnostics and targeted retry.

### PF-3 — Saved packages and models

Each seat stores a stable ID, display name, client adapter, provider if applicable, model or Provider default, supported reasoning effort, and launch profile. A package may contain multiple seats using the same client with different models.

Adapters declare supported settings. Pass the chosen model to the actual CLI invocation or API payload; never silently ignore it. Unsupported combinations produce a specific validation error before execution. Model options come from the client/provider where available; manual model IDs are allowed with unverified status. Do not hard-code this conversation's model catalog.

Keep requested and provider-confirmed model separate. Only show confirmation when a response or client receipt supplies it. A configuration edit is not proof that a running process switched models. Changes affecting an active seat apply to its next launch/run unless that adapter explicitly supports a safe switch.

### PF-4 — Launch ownership

Start missing seats and reuse only healthy seats whose effective configuration matches. A mismatched running seat requires a targeted restart choice. Keep existing batch launchers as compatibility entry points, routing shared behavior through one launcher implementation where feasible.

Track the processes the application owns. Do not kill external processes by executable name. Scope configuration per instance so duplicate seats cannot overwrite each other's MCP identity. Preserve valid existing settings; reject malformed input without replacement and back up intentional changes.

Proceed to chat when the chosen team is ready. If a seat fails, offer retry or explicit removal from the package for this launch. Never silently substitute a provider/model.

## 5. Session design and delivery

### SD-1 — Coordinator authority

The user selects a coordinator and describes the task. The coordinator proposes a session design. Retain the existing editable proposal/casting mechanism; do not require a predefined template. Validate assignments and required capabilities before execution.

Snapshot the accepted design with the run so later template edits cannot alter an active run. Replace the hard-coded four-participant phase and six-role session ceilings with an explicit configurable capacity policy. A phase must support the full selected six-agent team, and a configured package with more than six seats must be representable. Keep concurrency limits separate from membership and turn count. Publish the same effective policy to the coordinator, proposal editor, and backend validator; validate it before launch. Do not silently drop seats or rewrite the intended rounds to satisfy a hidden cap. Phase count, prompt length, and total-turn limits must also be explicit and centrally defined rather than conflicting constants. Long task context and documents belong in the run inputs, not the short phase-prompt field.

Preparation must not start rounds accidentally. Documents may be supplied before or after design. Start requires the user to have finalized the inputs the session depends on. A document-free task remains valid when explicitly intended.

### SD-2 — Equivalent inputs

Every adapter receives a turn envelope containing run ID, attempt ID, turn ID, design revision, input revision, assigned role, phase instructions, task brief, applicable rules, allowed source references, and relevant prior results.

API participants must receive these instructions directly, rather than reconstruct them from a channel. Required documents remain available independently of the recent-message window. CLI participants receive the same intended source set through scoped retrieval or explicit delivery. If one reviewer introduces additional evidence, record it and make a deliberate inclusion decision for subsequent turns; do not pretend all reviewers saw it. For an independent first pass, changed source material requires a new input revision and affected passes before claiming that reviewers assessed the same text.

Treat document contents as source material, not as operational instructions or permission to launch tools. Reject unsupported or oversized input with a useful explanation. Explicit chunking or a user-approved reduced scope may be offered; silent truncation is prohibited.

### SD-3 — Completion and capacity

Status messages, questions, and ordinary chat must not complete a turn. Require an explicit final-result event carrying the current turn identity. Provide a tool/event path for CLI agents and wrap successful API responses in that contract.

Validate run, input revision, attempt, and expected seat before accepting completion. Accept a turn once; reject duplicate and stale results. A question moves the turn to awaiting input, with explicit continuation. It does not auto-advance.

For the initial implementation, one seat executes one owned turn at a time. Queue contention visibly; do not overlap two sessions in one persistent CLI context. A crash or lost connection becomes a recoverable state, not a successful response.

## 6. Stop, correct, and restart

### SC-1 — State contract

Run states: prepared, running, awaiting_input, stopping, stopped, failed, completed. Turn states: queued, dispatched, acknowledged, awaiting_input, completed, cancelling, cancelled, failed, skipped.

Only running runs dispatch new work. Stop is idempotent and immediately makes the run ineligible for dispatch, before attempting provider cancellation. Persist that decision so refresh or server restart cannot resurrect stopped work.

### SC-2 — Actual cancellation

Stop cancels pending turns owned by the run and signals its active invocations through adapter-specific cancellation. Prevent queued callbacks, late messages, and agent @mentions from starting more work for that stopped run. Keep ordinary discussion and unrelated sessions independent.

Show stopping while cancellation is outstanding. After a bounded cancellation attempt (proposed default: 10 seconds), report any invocation still running and quarantine its output. Do not claim provider computation stopped merely because the UI stopped displaying it. Offer a targeted termination of an owned process when graceful interruption is unavailable; explain the impact before terminating a shared process.

Stopping cannot retract already transmitted document contents or reverse incurred usage. Do not implement Stop as channel deletion or global process termination.

### SC-3 — Corrected restart

Allow replacement of the mistaken documents while stopped. Restart creates a new run ID and input revision, links to the previous attempt, and retains the design and seats unless the user changes them.

Use clean reviewer context. API calls rebuild from the new packet; persistent CLI clients must use a supported reset/new session or a new isolated process/context. If isolation cannot be assured, do not label the restart clean. Old messages remain in the abandoned attempt's history but are excluded from new review context and deliverables by default.

### SC-4 — Recovery

After server restart, reconcile persisted turns with known process/adapter receipts. Never blindly redispatch waiting work. Uncertain ownership becomes a recoverable interruption with explicit retry. Use new attempt IDs on retries to reject a late result from the previous attempt.

### SC-5 — Lost turn or lost participant

A failed seat must not force the user to kill the session. Persist each turn before delivery and distinguish queued, dispatched, acknowledged, and completed receipts. Track delivery acknowledgement and response deadlines separately from process heartbeat: an online process is not proof it received or finished a turn. A slow response is not automatically a crashed agent. Deadlines are configurable by adapter/run and visible to the user.

A missed acknowledgement, failed dispatch, disconnected participant, or exceeded response deadline transitions the affected turn to a visible recoverable failure. Name the seat, phase, last acknowledged event, and reason; retain completed turns. Hold dependent work rather than silently advancing. The user can wait/extend, retry that turn, replace the participant, explicitly skip its contribution, or stop the run. None requires restarting successful earlier turns.

Retry uses a new attempt ID after fencing the old attempt. Recovery must use an identified durable result, not an inferred answer:

- **API seats:** persist a result outbox record atomically before attempting to post the completed response. Include a result ID, seat/instance, run/turn/attempt IDs, input revision, content, and creation time. Deliver with that result ID as an idempotency key and retain acknowledgement state. A post failure, lost acknowledgement, or restart can retry delivery of the same result without calling the model again or advancing twice. If model generation failed or no durable result exists, report that no answer is recoverable; offer a new generation attempt. A local persistence failure must be reported, not mislabeled as successful delivery.
- **CLI seats:** permit the operator to select a specific existing channel message ID from the expected seat, inspect its contents, and explicitly attach it to the failed turn. Verify channel, authenticated seat/instance provenance, input/run association where available, and that it has not already completed another turn. Record the selected message ID and operator recovery decision. Missing legacy turn metadata must be labeled operator-attributed, never machine-verified; reject unknown provenance or a conflicting run/input revision. Independent first-pass input restrictions still apply where relevant. This explicit recovery path is the narrow exception to the prohibition on arbitrary chat completing a turn.

If recovery follows a retry, fence the replacement attempt before attaching the selected result and commit the recovery once under the current turn identity. Preserve original attempt provenance. Late answers from superseded attempts are never automatically accepted; explicit recovery cannot bypass a stopped or superseded run or attach old-document work to a corrected run.

Replacement retains the role and supplies the approved input packet and necessary accepted context to a fresh instance. Record the effective seat/model change and affected future assignments; rerun only work invalidated by the change. If a required coordinator disappears, allow the same explicit replacement path. Skipped work is labeled missing in the transcript and final artifact, never represented as agreement. Show skipped contributions alongside the synthesis; never represent missing input as agreement.

Dispatch processing must retain individual turn envelopes in a durable acknowledged queue. Do not collapse distinct triggers from one poll into a single invocation or combine the channel of one trigger with the prompt/job of another. Schedule distinct turns separately under the seat concurrency rule; deduplicate only identical dispatch IDs. A dequeue is acknowledged only after durable ownership transfer; a read-and-clear file operation is not sufficient.

API generation exceptions, empty responses, and result-post failures must emit structured failure events to the session engine with run/turn/attempt identity and a sanitized error category. Console-only errors are insufficient. Explicit failure should surface immediately; a missed failure event is caught by the acknowledgement/response deadline. Record diagnostic events with timestamps without credentials or full document payloads.

Default to visible user-directed recovery, not endless automatic resubmission or silent model substitution. Any configured automatic retry budget must be finite and must not leave the old invocation able to contribute. Show a recoverable failure within one configured monitoring interval after its deadline. Survive page refresh and server restart with the same checkpoint and recovery choices.

User evidence: Seth reports a session freezing until he asked what was wrong, followed by GLM re-submitting a lost turn. This is a reported incident, not a reproduced root cause; the participant caps are separately verified in source. Preserve this distinction in bug reports.

Source-confirmed candidate mechanisms, not incident conclusions: (1) wrapper_api.py catches generation/post exceptions, prints "Error handling trigger", and sends no failure to the session engine; that engine currently has no turn deadline. A later human mention can start a fresh API response from history, resembling re-submission. Check timestamped GLM console/error evidence around the freeze before attributing the incident. (2) wrapper.py reads and clears a batch of queue entries, then injects once using the last channel and last available prompt/job values; distinct CLI triggers in one poll can be lost or mixed. This is a CLI failure candidate, not an explanation for GLM's API turn. The API queue also groups entries by channel, so its durable replacement must preserve distinct turn IDs too.

## 7. Recipient behavior and channels

### RC-1 — Explicit recipients win

For a human message, explicit agent mentions override selected recipient buttons for that message. Multiple explicit mentions target that set; `@all` targets eligible online agents. Without explicit recipients, use selected buttons. With neither, post without triggering agents. Unknown recipient tokens produce a warning rather than falling back to a wider audience.

Parse addresses in user-authored message text, excluding quoted blocks, fenced code, and attached document bodies. Show the resolved recipients before Send. This controls response triggers, not visibility: directed messages remain in the shared channel. Server-side validation is authoritative.

Keep human addressing distinct from session scheduling. During an active run, a manual request to a participating busy seat must explicitly interrupt the run or wait until its current turn finishes; it must not silently create an overlapping turn. Agent mentions cannot bypass the active run's turn order or stopped state.

### RC-2 — Channel lifecycle

Make rename, archive, and delete discoverable. Archive hides a channel from ordinary active navigation while preserving history and artifacts; it can be reopened. An active review must be stopped or completed before archival/deletion proceeds. Archival must block automatic routing into that channel.

Keep `general` protected. Deletion requires confirmation describing what is removed. Never silently delete saved artifacts with a channel: retain them with their source metadata unless explicitly selected for deletion. No automatic cleanup of old reviews.

## 8. Documents and artifacts

### DA-1 — Intake

Support pasted text, `.md`/`.txt`, and individually selected source files (including `.py`, `.mjs`, `.js`, `.ts`, `.tsx`, `.jsx`, `.json`, `.yaml`, `.yml`, `.toml`, `.css`, and `.html`) as plain UTF-8 text. Reject binary or undecodable input and apply the same size/context limits; never execute or render imported source. Multi-file packets are required after the initial build: allow an explicit selection of files to form one review packet, preserving per-file identity and quote attribution. Initial-build intake may handle individual files first. Automatic directory crawling is not implied. Show extracted text, title, size, and source identity before committing an input revision. Snapshot the text; store content hashes and stable references. Later edits to the original file cannot mutate an in-progress review.

The application loads documents and supplies their content to participants. A direct API participant therefore does not need arbitrary filesystem access. Optional project reading is a separate declared capability, scoped to the selected project; review mode must not grant source-writing permissions by default.

Document access checks must account for both the adapter and effective client permissions. A rule saying read-only is not an enforcement mechanism.

### DA-2 — Requested deliverables

Let the user ask the coordinator for a document during or after a session: synthesis, full rounds, recommendations, or another form. Preserve the request and selected scope. Do not impose a synthesis on every session or require one universal format.

Persist deliverables through an application-owned artifact interface available to both CLI and API adapters. The coordinator supplies authored content; the application owns storage, versions, and downloads. Record producing agent, requested/confirmed model when available, source run, source message IDs, input revision, and creation time.

Read Markdown in-app, request revisions, retain earlier revisions, and download `.md`. Sanitize rendering; source content must not execute scripts. Store stable app-owned copies instead of depending on an agent's Desktop write access.

### DA-3 — Actual rounds

When requested, assemble the transcript from stored messages, not model recollection. Include phase boundaries, seat/agent, timestamp, and message ID. Preserve wording and order; mark superseded, cancelled, and incomplete material. Artifact scope must say whether it contains only accepted run turns or also associated human discussion.

Support one combined Markdown file with authored synthesis followed by the actual rounds, or a transcript alone. Exclude abandoned attempts by default and expose explicit inclusion. No 1,000-character limit applies to artifacts: that limit belongs to the separate agent catch-up summary.

Restore the backup ZIP export if absent/broken in the selected baseline, but keep it distinct from document export.

## 8A. Optional independent review — Tribunal's spirit

### TR-1 — Three useful behaviors

Preserve independent first passes, quotations checked against real source text, and serious findings kept visible in the synthesis. Implement these behaviors directly in agentchattr; do not import Tribunal code or reproduce its engine. The coordinator still proposes the session design in chat. Follow-up discussion and cross-examination are optional, not prescribed stages.

### TR-2 — Independent API first passes

Use at least two fresh API reviewer contexts for the independent first pass. Construct each request from the approved document packet, task brief, and assigned lens only. Exclude channel history, peer answers, prior conversation state, and coordinator-proposed findings. Do not attach retrieval tools to these requests. API seats are independent only because the application controls this payload; the existing API wrapper's history-based path does not qualify unchanged.

Results may remain visible in chat: subsequent first-pass requests must still omit them. No sealed result store or CLI isolation infrastructure is required. CLI seats remain available for coordination, synthesis, discussion, and ordinary reviews. If two API reviewers are unavailable, explain the requirement and allow an ordinary review without claiming independence. Report the actual models; different seat names alone do not imply model diversity.

Use the existing immutable document packet and input-size checks. Use the later shared multi-file packet feature when available; do not add a separate Tribunal ingestion system, checkpoint policy, or replacement-model rules. General run ownership, Stop, retry, and stale-result protection still apply.

### TR-3 — Mechanical quotation checks

Ask reviewers to return one fenced `json` block with this shape: `{"findings":[{"document_id":"doc-1","quote":"exact source text","claim":"the concern","severity":"high"}]}`; `severity` is `critical`, `high`, `medium`, or `low`, and optional `line_start`/`line_end` must be supplied together as integers. Parse JSON and validate this small schema deterministically; an absent/ambiguous block, invalid JSON, or invalid finding shape receives a distinct **could not parse** flag, with the raw response retained. Valid siblings can still be checked when an individual finding is malformed. No repair call is triggered. String-match each quote against that document's stored input revision after newline normalization. Mark quotes as matched, unmatched, or missing/uncheckable; empty quotes and unknown source IDs never count as matched. If a line range is supplied, check that range rather than finding the same text somewhere else. Do not use fuzzy matching to turn a mismatch into a match.

Keep the finding and its check result visible. No automatic repair rounds, finding rejection pipeline, or voting follows a failed check. A matching quotation verifies that the quoted text exists, not that the criticism is valid. Unsupported interpretation remains something the reviewers and user must assess.

### TR-4 — Synthesis and delivery

Give the synthesizer the findings and their quote-check flags. Instruct it: preserve every serious finding or explicitly explain why it is disputed; do not quietly omit or downgrade a finding, and do not present an unmatched quotation as verified evidence. Missing reviewers and disagreements must be acknowledged. This is a prompt convention, not an application-enforced verdict guarantee.

Show and export the original serious findings and quote-check flags alongside the synthesis through the shared artifact feature, so the user can inspect omissions or disagreement. No every-peer-must-dispute rule, derived APPROVED/INCONCLUSIVE/CHANGES NEEDED status, automatic synthesis repair, or separate verdict engine. The coordinator can provide a recommendation in ordinary prose. Actual rounds remain available through the existing planned transcript export.

This replaces the parts of Tribunal the user wants in daily use, not its entire feature set. Existing Tribunal records remain untouched.

## 9. Implementation boundaries

Retain the existing Python server and browser frontend. Add focused modules for launch supervision, adapter capabilities, run/turn ownership, document storage, and artifact storage. Extend existing session and channel code rather than building a second orchestration engine.

Proposed adapter interface: probe, validate_configuration, launch_or_attach, prepare_context, dispatch_turn, cancel_turn, inspect_status, and release. Capabilities declare model selection, reasoning selection, scoped document retrieval, fresh-context support, graceful interruption, and confirmation/provenance support.

Persist these minimal records with versioned schemas:

- Package and seat configuration; secret references only.
- Agent instance with process ownership, effective configuration, capability checks, and status.
- Frozen session design and run with input revision and previous-run linkage.
- Turn/attempt with expected seat, durable dispatch and acknowledgement records, cancellation status, result references, API result outbox/delivery acknowledgements, and operator recovery provenance.
- Document revision with text, hash, and origin metadata.
- Artifact revision with Markdown and source provenance.
- Channel archive state.
- Independent-review selection, original findings, source references, and quotation check flags associated with the input revision.

Use the existing storage approach where sufficient, with atomic writes and serialized state transitions. Do not introduce a database migration solely for this feature set. If implementation establishes that transactional guarantees cannot be met, present a specific storage change separately. No in-place destructive conversion of existing histories.

Keep new endpoints local and authenticated under the existing security model. Launch requests must select registered adapters and validated arguments, never arbitrary shell strings. Preserve legacy data and batch entry points. Keep generic fixes separate from product additions so upstream PRs remain possible.

## 10. Delivery sequence

### A — Baseline and adapter audit

Record upstream commit; compare local files; preserve working installation/data. Repair verified defects in configuration preservation, exit propagation, API turn instructions, and missing baseline files. Inspect Tribunal's OMP-driven execution and recorded live-run lessons before diagnosing OMP here; do not assume the two architectures are interchangeable. Give Hermes and OMP one focused diagnostic pass each, capped initially at one working session; unresolved clients remain clearly unavailable with evidence and next steps.

Exit: adapter matrix distinguishes recorded successful use, current probe results, and live acceptance. No client is called ready solely because a launcher exists.

### B — Reliable launch and run ownership

Implement bootstrap, package persistence, model settings, instance isolation, consistent turn inputs, explicit completion, and Stop/correct/restart. These form the first usable milestone; do not hide unmanaged processes behind pre-flight.

Exit: one shortcut launches a saved team, a six-seat phase works, a stalled or failed turn becomes visible with wait/retry, and a review can be stopped and restarted with corrected pasted text without accepting stale output. The first milestone includes durable per-turn delivery and explicit completion. Full restart reconciliation and recovery of existing answers/replacement/skip follow; persisted Stop must already survive restart.

### C — Documents and daily controls

Add file intake, persistent document packets, recipient precedence, channel archival, and restoration of backup export where needed. Preserve coordinator-designed proposals.

Exit: all selected participant types receive the intended source revision across a multi-round session; directing a message to one agent never wakes the selected group accidentally.

### D — Deliverables and release

Add requested artifacts, Markdown reader, revisions, and exact transcript export. Validate the complete workflow and package the entry point. Document unsupported clients/capabilities and recovery paths. General upstream fixes may be proposed independently; release does not wait on their acceptance.

### Post-initial-build — Multi-file packets

Support selecting multiple text/source files into one immutable review packet, with a preview of the file list, per-file IDs, individual and aggregate limits, and no silent truncation. Deliver the same packet revision to the selected reviewers and bind quote checks to the named file. Verify two files with identical quoted text cannot validate a citation against the wrong file, and that changing one file creates a new packet revision. This is required follow-on scope, not a blocker for the initial launch/Stop milestone.

### E — Lightweight independent review

Add fresh API first-pass payloads, mechanical quotation checks, and synthesis instructions with original serious findings and check flags retained alongside the output. Use the shared document, run, and artifact infrastructure. No Tribunal code import or separate review engine. This follows the everyday-use release and does not delay launch/Stop.

Exit: the lightweight acceptance checks pass and one real review demonstrates independent inputs, useful quote flags, and readable synthesis. Describe this as replacing the user's chosen Tribunal workflow, not full Tribunal feature parity. Retirement or migration remains a separate explicit choice.

Implementation model preference: Sol for the next build steps. Astra is an optional escalation, not a prerequisite: on tickets #7-14 and #24, ask the user to bring it in if builder/reviewer disagreement or a reproduced correctness failure remains unresolved. Supply a frozen change and compact reproduction/evidence pack. Do not automatically launch Astra or replace the independent different-family reviewer with it. This is a build preference, not a hard-coded product model list. Every implementation ticket requires independent review by a different model family against a frozen change and reproducible evidence. Reviewer choice is driven by available quota from the user-configured pool: Meta Muse 1.3, DeepSeek Flash 4.1, Grok 4.7, and GLM 5.3 (user-provided labels; resolve actual provider/model IDs at execution time). Do not require Claude/Opus. Record builder and reviewer model identities, findings, and recheck outcome. If no eligible reviewer has quota, leave review pending rather than self-approving. The human retains final completion sign-off. Cancellation, routing, and storage changes must receive particular scrutiny.

## 11. Acceptance and verification

Use deterministic fake adapters for routine tests. They must simulate slow startup, failed login, a crashed turn, partial output, duplicate completion, delayed completion after Stop, and unsupported cancellation. Real-provider acceptance is separate and consumes actual usage; schedule it explicitly with the user.

- **AT-01:** Opening the shortcut twice creates one server. Occupied ports and startup failure produce actionable errors within the configured timeout.
- **AT-02:** A saved package round-trips client/provider/model/reasoning values. Unsupported values are rejected. Requested models reach the actual launch arguments/payloads. Confirmation is never fabricated.
- **AT-03:** Two seats on one client cannot overwrite configuration or cross-deliver messages. Malformed existing config remains byte-for-byte unchanged on failure.
- **AT-04:** CLI and API turns receive the selected phase prompt, rules, and identical intended document revision. The document remains available after more than 20 messages. Individually selected `.py` and `.mjs` inputs round-trip as plain text without execution; binary/undecodable inputs are rejected.
- **AT-05:** Status text cannot complete a turn. Duplicate or old-attempt completion cannot advance another turn. Questions await explicit continuation.
- **AT-06:** Stop during queued, active, and completing work blocks further dispatch and cascading mentions. Late output is quarantined. Unsupported cancellation remains visibly unresolved.
- **AT-07:** Run document A, Stop, replace with B, restart. Every new reviewer context uses B; no A completion enters the B transcript or synthesis. Other runs continue.
- **AT-08:** A server restart during a waiting turn does not blindly duplicate work. Stopped runs remain stopped across refresh and restart.
- **AT-09:** With all seats selected, `@claude` triggers only Claude. Multiple explicit recipients, `@all`, no selections, unknown names, and mentions inside documents behave as specified.
- **AT-10:** A coordinator proposes two different session structures for two tasks; the application validates and executes either without forcing six fixed phases.
- **AT-11:** Archive/reopen preserves messages and artifacts. Active work blocks channel removal until stopped. Delete confirms consequences and protects general.
- **AT-12:** A requested document is readable, revisable, and downloadable. Combined export contains actual ordered messages and provenance, not a reconstructed transcript or catch-up summary.
- **AT-13:** A complete live review succeeds with the selected release-supported clients. Record configuration and date; Hermes/OMP are optional until they pass the same end-to-end check.
- **AT-14:** Capture the API first-pass request payloads with fake adapters. Each contains the approved packet, brief, and lens, with no channel history, peer response, coordinator findings, prior conversation state, or retrieval tools. Publish one response before constructing the next request and verify it is still excluded. Ordinary CLI reviews remain available.
- **AT-15:** A valid JSON findings block yields extracted findings; absent/multiple blocks, malformed JSON, and invalid fields produce distinct parse flags with raw text retained. Correct quotes match their selected document revision; fabricated, empty, wrong-document, and missing quotes receive visible flags. Supplied invalid line ranges cannot pass. No automatic repair call is made. A matched quote is not labeled a validated claim.
- **AT-16:** The synthesis request includes original findings, quote-check flags, and instructions to preserve or explicitly address serious findings. The artifact and export retain original serious findings and flags even if fake synthesizer output omits them. No application-derived verdict or voting rule is required.
- **AT-17:** Retired in v1.4: Tribunal-specific replacement/checkpoint rules removed. General attempt identity, model honesty, and stale-result protection remain covered by AT-02, AT-05, AT-07, AT-08, and AT-22.
- **AT-18:** Retired in v1.4: automatic repair exhaustion and derived-verdict enforcement removed. Missing participants remain visible under SC-5; synthesis guidance and flags are covered by AT-16.
- **AT-19:** One real independent API review produces readable synthesis with original serious findings and quote flags. Stop/correct/restart works during first passes and synthesis. Ordinary session behavior and existing Tribunal data remain unchanged.

- **AT-20:** A phase containing all six selected agents validates and schedules all six; a configured seven-seat package is representable. Exceeding the declared policy fails before launch with the same explanation in coordinator context, editor, and backend. Concurrency limits do not remove members.
- **AT-21a — API freeze path:** Make a fake API model raise before producing output. The session receives a typed failure and retains completed turns, rather than waiting indefinitely for an answer. No recoverable result is offered. Drop that failure event separately and verify the deadline fallback. Exercise explicit retry and replacement.
- **AT-21b — CLI batching path:** Queue two distinct turn envelopes within one polling interval, including different channels/prompts/jobs. Both retain their identities, are scheduled separately, and receive receipts; no field mixing or last-trigger-wins loss. Repeat for two API turns in one channel and replay an identical dispatch ID to verify deduplication.
- **AT-21c — Result recovery:** Persist an API result, fail the post, restart the wrapper, and recover from the outbox without another model call. Separately lose the successful post acknowledgement and verify one accepted result. Recover an operator-selected CLI message from the expected seat; reject wrong-seat, conflicting-input, duplicate-use, and unknown-provenance messages. Label operator attribution where legacy metadata is absent. Persistence failure never claims a recoverable saved answer.
- **AT-21d — Participant loss:** Drop a dispatch acknowledgement, disconnect GLM, and simulate a live-but-stalled process as distinct cases. Each shows the correct recoverable state and preserves earlier accepted turns. Wait/extend, replacement, skip, and coordinator replacement produce attributable outcomes without killing the run.
- **AT-22:** Deliver an old GLM attempt after retry or replacement and refresh/restart during recovery. No duplicate advancement occurs; the failed-turn checkpoint survives. A skip remains visible alongside the synthesis and in export.

Completion means the acceptance evidence is recorded, the app starts through the packaged entry point, existing data remains accessible, and unresolved adapter limitations are visible. The spec itself is not evidence that any of these features have been implemented.

## 12. Source references

- Local audit: `windows/*.bat`, `wrapper.py`, `wrapper_windows.py`, `wrapper_api.py`, `config_loader.py`, `session_engine.py`, `session_store.py`, `agents.py`, `router.py`, `store.py`, `summaries.py`, `mcp_bridge.py`, `app.py`, and `static/{index.html,chat.js,channels.js,sessions.js}`.
- October 9 evidence: local Combat Paper Walkthrough report (2026-10-09), Appendix A; private reference, not bundled.
- September 28 example: local snake roguelite design-review transcript; private reference, not bundled.
- Tribunal comparison: local project context and August 26 state/handoff records; historical evidence only. No source-code import planned.
- Upstream: https://github.com/bcurts/agentchattr. Its current commit and installed CLI contracts must be verified during implementation; cached web pages are not a pinned build baseline.

````

## Candidate local Hermes writer (not ported)

```python
def _write_yaml_mcp_settings(config_file: Path, url: str, token: str) -> Path:
    """Merge Hermes' MCP entry, preserving other settings and an original backup.

    Refuse malformed configuration rather than silently replacing it. Only
    rewrite the mcp_servers YAML node so unrelated formatting stays intact.
    """
    import yaml

    original = config_file.read_text("utf-8-sig") if config_file.exists() else ""
    existing = yaml.safe_load(original) or {}
    if not isinstance(existing, dict):
        raise ValueError(f"Expected a YAML mapping in {config_file}")
    servers = existing.get("mcp_servers") or {}
    if not isinstance(servers, dict):
        raise ValueError(f"Expected mcp_servers to be a mapping in {config_file}")
    entry = {"url": url}
    if token:
        entry["headers"] = {"Authorization": f"Bearer {token}"}
    servers[SERVER_NAME] = entry
    block = yaml.safe_dump({"mcp_servers": servers}, sort_keys=False, allow_unicode=True)
    node = yaml.compose(original)
    result = None
    if node is not None:
        for key, value in node.value:
            if key.value == "mcp_servers":
                result = original[:key.start_mark.index] + block + original[value.end_mark.index:]
                break
    if result is None:
        result = original.rstrip() + "\n\n" + block
    # Verify that replacing the node did not change any other config value.
    existing["mcp_servers"] = servers
    if yaml.safe_load(result) != existing:
        raise ValueError("Cannot safely update Hermes YAML; configuration left unchanged")
    config_file.parent.mkdir(parents=True, exist_ok=True)
    backup = config_file.with_name(config_file.name + ".agentchattr.bak")
    if config_file.exists() and not backup.exists():
        shutil.copy2(config_file, backup)
    config_file.write_text(result, "utf-8")
    return config_file
```

## Candidate local shared Windows launcher (not ported)

```bat
@echo off
setlocal
cd /d "%~dp0.."
set "CHAT_AGENT=%~1"
set "CHAT_COMMAND=%~2"
if not defined CHAT_COMMAND exit /b 2
REM --check probes the real CLI and wrapper config without starting a session.
where "%CHAT_COMMAND%" >nul 2>&1
if errorlevel 1 (
    echo Error: %CHAT_COMMAND% was not found on PATH.
    goto :failed
)
call %CHAT_COMMAND% --help >nul
if errorlevel 1 (
    echo Error: %CHAT_COMMAND% cannot start. Run it with --help to see details.
    goto :failed
)
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto :failed
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto :failed
)
.venv\Scripts\python.exe -c "import fastapi, uvicorn, mcp, yaml" >nul 2>&1
if errorlevel 1 (
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto :failed
)
.venv\Scripts\python.exe -c "from config_loader import load_config; import sys; assert sys.argv[1] in load_config()['agents'], 'Agent missing from config'" "%CHAT_AGENT%"
if errorlevel 1 goto :failed
if /i "%~3"=="--check" (
    echo %CHAT_AGENT% CLI and wrapper preflight passed. No agent session started.
    exit /b 0
)
REM Use the same configured port as the wrapper, including environment overrides.
for /f "delims=" %%P in ('.venv\Scripts\python.exe -c "from config_loader import load_config; print(load_config()['server']['port'])"') do set "CHAT_PORT=%%P"
if not defined CHAT_PORT goto :failed
powershell -NoProfile -Command "try { $null = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 ('http://127.0.0.1:' + $env:CHAT_PORT + '/'); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    REM The server is a background helper; keep its window hidden.
    powershell -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath '.venv\Scripts\python.exe' -ArgumentList 'run.py' -WorkingDirectory (Get-Location).Path"
    if errorlevel 1 goto :failed
)
set /a CHAT_WAIT=0
:wait_server
powershell -NoProfile -Command "try { $null = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 ('http://127.0.0.1:' + $env:CHAT_PORT + '/'); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :launch
set /a CHAT_WAIT+=1
if %CHAT_WAIT% geq 15 (
    echo Error: agentchattr did not become ready on port %CHAT_PORT%.
    goto :failed
)
powershell -NoProfile -Command "Start-Sleep -Seconds 1"
goto :wait_server
:launch
if /i "%CHAT_AGENT%"=="hermes" (
    .venv\Scripts\python.exe wrapper.py hermes --no-restart --cli
) else (
    .venv\Scripts\python.exe wrapper.py "%CHAT_AGENT%" --no-restart
)
if errorlevel 1 goto :failed
exit /b 0
:failed
echo Launcher stopped. Review the error above.
if /i not "%~3"=="--check" pause
exit /b 1

```
