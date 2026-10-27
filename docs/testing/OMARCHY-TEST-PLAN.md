# Ticket #2: Windows-hosted Omarchy test

Target: `3bf7da0484f7dbe308076803efa4e7ff7aff6222`. Independent code review remains pending. This is a platform smoke test; no dual boot or agent/model calls are needed. Allow about 15–20 minutes plus dependency download time.

Use the supplied `ticket-2-omarchy-3bf7da0.zip`, which contains tracked source at that commit, without Windows environments, local settings or runtime history. Copy it into your Omarchy install. Run everything below in an **Omarchy terminal**, not PowerShell/Git Bash. Stop at a failed step and report its output.

## Running directly from the repo

You can use the existing checkout instead of extracting the ZIP. Confirm it contains the implementation:

```sh
git merge-base --is-ancestor 3bf7da0484f7dbe308076803efa4e7ff7aff6222 HEAD
```

Exit code 0 means the target is included. The feature branch has not been pushed; a separate clone may not have it yet. Stop if the check fails.

From the repo root in Omarchy, set these overrides in the test terminal:

```sh
TEST_DATA=$(mktemp -d "$HOME/agentchattr-ticket2-data.XXXXXX")
export AGENTCHATTR_PORT=19300
export AGENTCHATTR_MCP_HTTP_PORT=19200
export AGENTCHATTR_MCP_SSE_PORT=19201
export AGENTCHATTR_DATA_DIR="$TEST_DATA/data"
export AGENTCHATTR_UPLOAD_DIR="$TEST_DATA/uploads"
python3 --version
python3 launcher.py --check
```

Then run steps 3, 4 and 6 below in that same terminal. **Skip steps 1 and 2:** do not edit shared `config.toml`. Existing `.venv-linux` may already be ready; if so, setup/cancellation is not exercised and should be marked skipped. The Windows environment remains separate.

**Skip step 5 for this route.** A menu launch does not inherit these terminal overrides and could open the default instance. Record menu testing as pending; use the disposable-copy route when testing the actual menu shortcut. These exports last only for this terminal, so close it after the test. Keep test data until its server is stopped.

## Disposable-copy route

1. **Prepare a fresh copy.** Substitute the actual location of the copied zip. Keep this terminal open through the tests.

   ```sh
   python3 --version
   TEST_ROOT=$(mktemp -d "$HOME/agentchattr-ticket2-test.XXXXXX")
   python3 -m zipfile -e /path/to/ticket-2-omarchy-3bf7da0.zip "$TEST_ROOT"
   cd "$TEST_ROOT"
   ```

   Expected: Python 3.11 or newer. The new directory contains `launcher.py`. This copy has no existing sessions or credentials. Its environment will be `.venv-linux`.

2. **Choose isolated ports in this disposable copy.** The menu shortcut must use the same configuration as terminal launches. This edits only the extracted test copy, not your working checkout.

   ```sh
   python3 - <<'PY'
   from pathlib import Path
   p = Path('config.toml')
   text = p.read_text()
   text = text.replace('port = 8300', 'port = 19300', 1)
   text = text.replace('http_port = 8200', 'http_port = 19200', 1)
   text = text.replace('sse_port = 8201', 'sse_port = 19201', 1)
   p.write_text(text)
   PY
   python3 launcher.py --check
   ```

   Expected: server `absent`, environment `false`, unknown authentication and readiness `false`. No `.venv-linux` or `.launcher` should be created. If a port is occupied, stop; do not stop another service. Record any inherited `AGENTCHATTR_*` overrides by name, without sharing their values, because they can override this config.

3. **Cancel setup, then accept it.** Run `sh macos-linux/start.sh`. At the setup prompt, press Enter. Expected: exits without installation. Run it again and type `SETUP` after reading the message. Expected: creates `.venv-linux`, installs the declared dependencies, starts the server and opens `http://127.0.0.1:19300/preflight` in the Omarchy browser. If no browser opens, record the message and try the printed URL manually in Omarchy. A working manual URL alone does not pass automatic browser opening.

4. **Check the page and repeated launch.** Confirm executable paths/missing commands are plausible, authentication remains unknown, and agents are not called ready merely because a command exists. Refresh checks should update the time. Open chat should reach the existing chat page. Run `sh macos-linux/start.sh` twice more: both should promptly reopen pre-flight without setup, duplicate-server errors or another server process.

   ```sh
   pgrep -af '[p]ython.*run.py'
   ```

   Expected: one process for this test copy. Other installations may appear; compare the full path and do not stop them.

5. **Test the Omarchy menu entry.** Install into the normal application-menu directory only if no entry named `agentchattr.desktop` already exists:

   ```sh
   python3 macos-linux/install_shortcut.py
   ```

   Expected: prints the new path. Find **Agentchattr** in the Omarchy application menu and open it. It should reuse the test server and open pre-flight. Opening it again should still leave one server for this copy. A second installer run must refuse the existing entry, rather than overwrite it. If an entry already exists before this test, leave it alone and report this step as skipped.

6. **Run the isolated integration check.** This uses additional temporary data and dynamically chosen ports, then stops only its own child:

   ```sh
   .venv-linux/bin/python tools/verify_preflight.py
   ```

   Expected: JSON with `result: PASS`, `owned_servers: 1`, `separate_relaunches: 2`, `authentication_enforced: true`, and `session_token_logged: false`.

## Send back

```text
Omarchy runs inside Windows using: [WSL / VM / other]
Python version:
Passive check / setup cancellation:
Accepted setup + automatic browser opening:
Refresh + Open chat:
Repeated launch + one server:
Menu entry + repeated open + overwrite refusal:
Integration PASS:
First error/output, if any:
```

Do not paste credentials or browser session tokens. Keep the extracted folder while its menu entry exists. Closing the browser does not stop the server. To stop the smoke-test server, identify its exact path/PID above and terminate only that PID with `kill PID`; do not use a blanket Python kill. We can handle removal of the test folder/menu entry after results. Record this as **Windows-hosted Omarchy**, with native dual-boot testing deferred.
