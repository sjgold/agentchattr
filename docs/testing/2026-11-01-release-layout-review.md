# Independent review: release layout

Reviewer: Claude Sonnet 5.5 (`claude-sonnet-5-5`), native CLI, read-only tools. Observed successful provider response. Source review only; no independent execution.

**Verdict: PASS for production layout, with caveats.** I found no relocation defects in the production code paths. I did not run anything, and the test migration is unverified.

**What I checked (Read, Glob and Grep only)**
- **Project root:** `src/launcher.py:21`, `src/run.py:13`, `src/config_loader.py:26`, `src/build_release.py:12`, `src/wrapper.py:33`, `src/wrapper_api.py:31` and `src/launch_agent.py:11` all resolve the root as `parent.parent` of `src`. `src/app.py` does the same at lines 374, 627, 641 and 4311, and `src/runtime_ownership.py` at lines 155 and 158.
- **Process spawning:**
  - The launcher starts `src/run.py` (`src/launcher.py:229`).
  - `src/launch_agent.py:34` starts `src/wrapper*.py`.
  - `src/api_seat_runtime.py:230` starts `src/cli_worker.py` or `src/wrapper_api.py`.
  - Each child script gets its own directory (`src`) first on its import path, so the flat imports keep working. `src/run.py:14` also inserts `src` explicitly, which is harmless.
- **Ownership and source hashes:**
  - `src/runtime_protocol.py:44` reads hashes from `<root>/src` but keeps basename keys, so existing manifests stay compatible.
  - The check that each source resolves directly inside `src` (line 48) still holds.
  - `worker_root` is the project root in both `src/runtime_ownership.py:155` and its `sources_match` call at line 158, so the worker and the server compare the same root.
  - `instance_identity` uses the project root (`src/launcher.py:29`, `src/app.py:374`), so the launcher's identity matches the server's `/api/health`.
- **Entry points:**
  - `windows/start.bat` changes to the project root and runs `src\launcher.py`.
  - `windows/start_cli_agent.bat` and the `.sh` equivalents use `src/launcher.py` and `src/launch_agent.py`.
  - `Start Agentchattr.bat` delegates to `windows/start.bat`.
  - `windows/install_shortcut.ps1:11` points at `windows\start.bat`, which still exists.
- **Packaging:**
  - `src/build_release.py:46-50` copies `Start Agentchattr.bat` and `src/*.py`.
  - All the other listed files and directories exist: config, requirements, README, `open_chat.html`, `static`, `windows`, `macos-linux` and `session_templates`.
  - The release excludes `.venv-*`, `data` and `.launcher`.
- **Credentials:**
  - The relocation did not add any new secret handling.
  - The launcher still reads only the named keys from `~/.env`, not from the project directory.
  - Logs go to `.launcher/server.log`, which is gitignored.

**Findings (all minor or already present before this change)**
1. **Minor, relocation-related:** `src/app.py:4325` runs `git remote get-url` with `cwd=src` instead of the project root. Git searches upward, so the result is the same. A release zip has no `.git`, so it reports "unknown" either way. It's cosmetic, but changing it to the root would be tidier.
2. **Minor, doc and message text:** the usage text still says `python wrapper_api.py ...` and `python run.py` (`src/wrapper_api.py:4,102,154`, `src/wrapper.py:4-8`). These are now wrong unless the user adds the `src/` prefix. Several `src` modules also still describe `run.py` by its old location. This is cosmetic.
3. **Baseline, not a relocation defect:** `src/store.py:60` falls back to `data_dir.parent / "uploads"`. This is unrelated to the move, because `data_dir` resolves against the project root.
4. **Test coverage gap:** the 113 test files contain about 376 occurrences of `parent.parent`, `ROOT` or `Path(__file__)` (I only sampled the count output). These likely still need path migration, as you said. Until they pass, I can't say whether the tests catch a layout regression.

**Coverage limitations**
- I did not execute anything, so I did not re-verify your reported server startup, launcher reuse or test passes. I did not open the 70 relocated files individually. The `src/` grep was limited to the path-sensitive modules and the import statements in the worker modules.
- I did not open `src/artifact_*`, `src/mcp_bridge.py` or `src/wrapper_unix.py` beyond a grep for path patterns. I did not do a deep search for hard-coded root-level `.py` names in tests, docs or `tools/`.
- Unmigrated test fixtures and the full regression run are not certified. The existing unread-cursor bugs remain release blockers for final stakeholder acceptance, as you said, and I did not assess them.

**Model identity:** Sonnet 5.5, model ID `claude-sonnet-5-5`.
