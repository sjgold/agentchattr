# Open pre-flight

Python 3.11 or newer is required. These launchers open `/preflight`; Open chat goes to the existing chat page. They do not start agents or call providers. Agent/package launch controls are later tickets.

Windows: run `windows\start.bat`. To add a desktop shortcut, run `powershell -NoProfile -ExecutionPolicy Bypass -File windows\install_shortcut.ps1` from this checkout. The installer refuses an existing `Agentchattr.lnk`.

Linux/Omarchy: run `sh macos-linux/start.sh`. To add an application-menu entry, run `python3 macos-linux/install_shortcut.py`. It uses `$XDG_DATA_HOME/applications` or `~/.local/share/applications`, refuses an existing `agentchattr.desktop`, and opens a terminal for first-run setup and errors. Native Omarchy testing is pending. macOS can use the same shell entry point; the menu installer is for Linux.

On first launch, review the setup message and type `SETUP` to create the platform environment and install `requirements.txt`. Canceling installs nothing. For an explicit noninteractive setup, run `python launcher.py --setup` (Linux: `python3`). Existing environments are preserved; Windows, Linux and macOS use separate `.venv-windows`, `.venv-linux`, `.venv-macos` directories. These are separate from any old `.venv`.

`python launcher.py --check` prints passive checks without writing files, installing packages or starting the server. `--no-browser` starts/reuses the server and prints the pre-flight URL. `--timeout 60` controls lock/startup readiness; dependency inspection is bounded at 15 seconds, explicit environment creation at 60 seconds, installation at 300 seconds, browser opening at 10 seconds, and owned-child cleanup at 6 seconds.

The bootstrap serializes setup/startup, checks an app/installation/configuration identity, and reuses a matching service on the configured port. A different listener is reported as a conflict and remains running. Failed startup stops only the child created by that invocation and points to `.launcher/server.log`. A successful server keeps running after the bootstrap exits. Closing a browser tab does not stop it.

The server reads `config.toml` and the existing supported local overrides. `--port`, `--data-dir`, `--mcp-http-port`, `--mcp-sse-port` and `--upload-dir` retain the existing configuration-loader behavior. Use distinct web **and MCP** ports when running multiple installations. The shortcut supports loopback binding only. Existing `run.py` remains available for explicit server operation.

Pre-flight finds CLI paths without executing the commands. Unknown version, unchecked startup, unknown authentication/connection and unverified readiness are shown explicitly. Refresh repeats these passive checks; it never authenticates or installs anything.

## Verification

Run the existing unittest suite in the platform environment. On restricted hosts, loopback tests require local network permission and a writable temporary directory. `tools/verify_preflight.py` starts an isolated local app using temporary data and three dynamically chosen ports, exercises two separate relaunches and token enforcement, then stops its owned server. `--serve` keeps that test page available until Enter for browser verification. It does not call providers.
