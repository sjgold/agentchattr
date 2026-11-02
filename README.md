# Agentchattr

A local shared chat for Claude, Codex, Antigravity, GLM, Muse and DeepSeek.

## Open the app

On Windows, double-click **Start Agentchattr.bat**. It starts or reconnects to this installation and opens Pre-flight. Choose the saved six-agent team, check models, then select **Launch team and open chat**.

On a fresh installation, Python 3.11 or newer is required. The launcher asks before installing application dependencies. Existing installations reuse their environment.

Linux/macOS entry: `sh macos-linux/start.sh`. Native Linux/macOS release acceptance is pending.

## Release status

This is the RC2 recovery candidate. [STATUS.md](STATUS.md) records verification, open defects and the next acceptance step. The six-provider review and stakeholder verdict remain pending.

The canonical checkout is `C:\Users\SJG\Documents\CodePlayground\agentchattr`. GitHub main tracks the shareable source. Local credentials, saved teams and chat history stay private.

## Where things live

| Folder | Contents |
| --- | --- |
| `src/` | Python application and release builder |
| `static/` | Chat and Pre-flight interface |
| `session_templates/` | Review session templates |
| `data/` | Private local history, team configuration and runtime records |
| `tests/`, `tools/` | Developer tests and verification tools |
| `docs/` | Operator guides, specifications and historical evidence |
| `windows/`, `macos-linux/` | Platform and compatibility launchers |

`config.toml` supplies defaults. `config.local.toml` adds private installation-specific templates using distinct names. API templates reference environment-variable names; saved teams contain no credential values.

## Developer checks

Windows tests: `powershell -NoProfile -File tools/test.ps1`.
Passive launch check: `python src/launcher.py --check`.
Build release: `python src/build_release.py`.
Extracted-release smoke test: `.venv-windows\Scripts\python.exe tools/verify_release.py`.

See [launcher guidance](docs/guides/LAUNCHER.md), [documents](docs/guides/DOCUMENT-INPUTS.md), [Stop](docs/guides/STOPPING-REVIEWS.md), and [corrected restart](docs/guides/CORRECTING-REVIEWS.md).
