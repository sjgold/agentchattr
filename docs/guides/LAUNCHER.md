# Open pre-flight

Python 3.11 or newer is required. These launchers open `/preflight`. Use its seat editor to choose/configure a saved team, choose Launch team and open chat. If a seat needs attention, retry it or leave it out before continuing. Chat has a Seats & launch link back to pre-flight. Opening the page alone does not launch agents.

Windows: run `windows\start.bat`. To add a desktop shortcut, run `powershell -NoProfile -ExecutionPolicy Bypass -File windows\install_shortcut.ps1` from this checkout. The installer refuses an existing `Agentchattr.lnk`.

Linux/Omarchy: run `sh macos-linux/start.sh`. To add an application-menu entry, run `python3 macos-linux/install_shortcut.py`. It uses `$XDG_DATA_HOME/applications` or `~/.local/share/applications`, refuses an existing `agentchattr.desktop`, and opens a terminal for first-run setup and errors. Native Omarchy testing is pending. macOS can use the same shell entry point; the menu installer is for Linux.

On first launch, review the setup message and type `SETUP` to create the platform environment and install `requirements.txt`. Canceling installs nothing. For an explicit noninteractive setup, run `python src/launcher.py --setup` (Linux: `python3`). Existing environments are preserved; Windows, Linux and macOS use separate `.venv-windows`, `.venv-linux`, `.venv-macos` directories. These are separate from any old `.venv`.

`python src/launcher.py --check` prints passive checks without writing files, installing packages or starting the server. `--no-browser` starts/reuses the server and prints the pre-flight URL. `--timeout 60` controls lock/startup readiness; dependency inspection is bounded at 15 seconds, explicit environment creation at 60 seconds, installation at 300 seconds, browser opening at 10 seconds, and owned-child cleanup at 6 seconds.

The bootstrap serializes setup/startup, checks an app/installation/configuration identity, and reuses a matching service on the configured port. A different listener is reported as a conflict and remains running. Failed startup stops only the child created by that invocation and points to `.launcher/server.log`. A successful server keeps running after the bootstrap exits. Closing a browser tab does not stop it.

The server reads `config.toml` and the existing supported local overrides. `--port`, `--data-dir`, `--mcp-http-port`, `--mcp-sse-port` and `--upload-dir` retain the existing configuration-loader behavior. Use distinct web **and MCP** ports when running multiple installations. The shortcut supports loopback binding only. Existing `src/run.py` remains available for explicit server operation. Windows `start.bat` pauses after errors so desktop users can read them; automated callers should invoke `python src/launcher.py` directly to avoid that pause.

Pre-flight finds CLI paths without executing the commands. Unknown version, unchecked startup, unknown authentication/connection and unverified readiness are shown explicitly. Refresh repeats these passive checks; it never authenticates or installs anything.

## Verification

Run the existing unittest suite in the platform environment. On restricted hosts, loopback tests require local network permission and a writable temporary directory. `tools/verify_preflight.py` starts an isolated local app using temporary data and three dynamically chosen ports, exercises two separate relaunches and token enforcement, then stops its owned server. `--serve` keeps that test page available until Enter for browser verification. It does not call providers.

## Provider keys and daily configuration

Pre-flight selects saved seats and model settings from configured templates. Add distinct template names in the installation's gitignored config.local.toml under [agents.NAME]; existing names in config.toml cannot be overridden by that local file. Store only environment-variable names in api_key_env/secret_ref, never key values. The launcher preserves keys already set in the starting terminal. When starting a new server, it also reads exact NAME= lines from your home .env for configured API templates and saved API seats, loading them only into that server child. First match wins; one surrounding quote pair is removed. Missing/unreadable file or missing names leave credentials unavailable for pre-flight to report. Values are never written to configuration, logs or command arguments. Changing .env requires restarting your owned server; reconnecting to an existing server does not reload keys. This change has focused fake-profile tests and is awaiting the independent security review before live use.

A fresh installation needs its own platform environment; the one-time explicit --setup path creates it and installs requirements.txt. An environment belonging to a different checkout is not silently reused.
