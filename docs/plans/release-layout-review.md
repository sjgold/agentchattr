# Independent release layout review

Review the current canonical checkout read-only. Timebox: 8 minutes. No provider seats, filesystem edits, global settings or Git mutations. Use Read, Glob and Grep only.

The reviewed baseline is RC2 commit 05a16095. All 70 root Python files moved into src. Flat imports stay unchanged. Project-root configuration, static files, templates, runtime data and virtual environment stay in place. launcher/config_loader/run/app/wrapper/wrapper_api/launch_agent/runtime_ownership now resolve project root one level above src. Source hashes keep basename keys but read project/src. Managed subprocess commands now target src. Windows and shell launchers point into src. Start Agentchattr.bat is the user entry. build_release includes src/*.py.

Inspect src/launcher.py, src/run.py, src/config_loader.py, src/api_seat_runtime.py, src/runtime_ownership.py, src/runtime_protocol.py, src/cli_worker.py, src/wrapper.py, src/wrapper_api.py, src/build_release.py, windows/start.bat and Start Agentchattr.bat. Check for remaining wrong paths, ownership mismatch, startup/packaging failures or credential risks introduced by relocation. Inspect relevant tests as useful.

Observed verification: relocated server startup and two separate launcher reuse calls passed with temporary data, no providers; unauthenticated preflight was denied. 16 launcher tests, 17 configuration tests, 2 manifest closure tests passed. Full regression is running; fixture path migration is ongoing. Do not certify that unfinished test migration. Existing unread cursor bugs are explicitly outside this layout change and remain release blockers for final stakeholder acceptance.

Return PASS or REVISE for production layout, concrete file/line findings, coverage limitations and actual model identity if available. Existing baseline defects should be distinguished from relocation defects.
