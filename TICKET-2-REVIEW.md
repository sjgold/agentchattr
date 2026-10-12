# Ticket #2 implementation review

Status: ready for independent review, not approved or shipped. Frozen code target: `3bf7da0484f7dbe308076803efa4e7ff7aff6222` on `codex/ticket-2-preflight`. Base: `4bc8a3a96f1c26c73e9694a1372c4d469b4b11d9`. The following commit only records this review target in documentation; inspect the frozen target for implementation review.

Reviewer must use a different model family from the Codex builder, record actual provider/model identity, and distinguish source review from independently executed checks. Checkout/test access is needed for meaningful process/HTTP verification; the earlier pasted-only Muse review covered ticket #1, not these changes. Do not call providers, start agent wrappers, edit the working Desktop installation or change user settings.

Scope: issue #2, PF1/PF2 and AT-01 in local specification v1.7, plus Seth's Linux/Omarchy launcher requirement. One bootstrap starts/reuses the correct local service and opens pre-flight; passive executable discovery is honest about unknown authentication/startup/readiness. Package/configuration and actual seat launch controls remain #3/#4.

## Target files

- `launcher.py`: identity, HTTP probe, kernel lock, explicit setup, platform environments, bounded spawn/readiness/browser opening and owned-child cleanup.
- `app.py`, `run.py`: loopback health, authenticated passive discovery, token-injected pre-flight shell and removal of token printing to supervised logs.
- `static/preflight.html`, `static/preflight.css`, `static/preflight.js`: existing product tokens, passive state cards, Refresh and Open chat.
- `windows/start.bat`, `windows/install_shortcut.ps1`, `macos-linux/start.sh`, `macos-linux/install_shortcut.py`: thin entry points and collision-refusing shortcuts.
- `tests/test_launcher.py`, `tests/test_preflight.py`, `tools/verify_preflight.py`: reproducible checks; `.gitignore`, `README.md`, `LAUNCHER.md`, `STATUS.md`: support/limitations.

## Recorded builder evidence

- Python 3.14.6 on Windows; declared requirements installed only in ignored `.venv-windows`. Full unittest suite: **173 tests, OK, 4 Unix/tmux skips**, after identity and malformed-HTTP fixes. Bootstrap tests: 15; pre-flight tests: 4. All initial bootstrap/endpoint tests were red before their implementations. Additional edge-case tests were red before fixes.
- Actual local server: fresh temporary data/upload directories with spaces, three dynamically selected ports, one owned server, two separate launcher processes successfully reused it. Unauthorized pre-flight API request returned 403; authorized snapshot contained ten configured agents with unverified readiness; supervised log did not contain the session token. Owned server was stopped afterwards.
- Kernel lock exclusion across processes and concurrent first-start single-spawn tests passed. Those are separate from the real-server relaunch check; simultaneous real first starts have not been independently exercised.
- Actual Chrome: rendered ten agent cards, Refresh advanced timestamp, Open chat reached `/` with chat input, 390px viewport had no horizontal overflow. Inherited header layout was corrected. Browser/test server stopped. Offline emulation reloaded the page; in-page failure/retry interaction remains unverified.
- Windows shortcut generated and inspected in scratch; `windows/start.bat --check` passed. Shell syntax and Git Bash `start.sh --check` passed (Windows Python). Linux menu content generated in scratch. **No native Omarchy execution or real Desktop/menu installation claimed.**

## Reproduce

Use the platform Python environment after explicitly authorized setup. On Windows, PowerShell from repo root:

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -c "import tempfile,unittest; tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlayground\agentchattr\.audit-tmp'; result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not result.wasSuccessful())"
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_preflight.py
node --check static/preflight.js
git diff --check
```

Create `.audit-tmp` first if absent. Local HTTP tests need loopback permission; a sandboxed run stalled in TestClient and a health probe appeared absent, while permitted runs passed. Do not treat those sandbox results as application acceptance. Substitute a writable local temp path and `.venv-linux/bin/python` on Linux; Python stdlib `unittest` is used.

For browser checks, `tools/verify_preflight.py --serve` prints the local URL and waits for Enter; Enter stops its owned child. Do not print or copy the injected browser session token. Verify Refresh and Open chat; optionally test failure/retry. See `LAUNCHER.md` for explicit setup and shortcut commands. Generate shortcuts into a fresh scratch directory to avoid touching an existing desktop/menu entry.

## Review focus and return contract

Check duplicate launch, lock recovery/bounds, listener identity/malformed responses, foreign-process preservation, child-only cleanup, explicit setup, no model calls during checks, platform environment separation, config override consistency and session-token security. Assess Windows batch quoting/exit propagation and native POSIX/desktop quoting. Web availability must not claim MCP/auth/agent readiness. Respect the ticket boundary; report unrelated baseline defects separately.

Return PASS, PASS WITH NONBLOCKING NOTES, or FAIL with severity, file/line, concrete trigger/impact, recommended correction, exact frozen commit, actual reviewer identity, commands executed/results and unverified platforms. Substantive fixes require a new frozen target and independent recheck. Seth retains final sign-off; do not close #2 or begin dependent tickets automatically.
