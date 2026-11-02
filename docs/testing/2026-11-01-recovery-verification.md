# Canonical RC2 recovery verification

Date: 2026-11-01. Implementation owner: Codex GPT-6 Astra. Source-layout checkpoint: 567b9a6.

## Observed results

- Canonical main advanced from 400d6de to reviewed RC2 05a16095 without rewriting history.
- All 70 root Python modules moved into src. Startup, subprocess paths, ownership roots and source hashing were updated together.
- Full regression: first run 2331 tests / 3 failures / 5 errors / 13 skips in 493.251s. Each failure was an obsolete path expectation in a fixture. The affected 48 tests passed after correction. Final run: 2331 tests / OK / 13 skips in 477.237s.
- Standalone Pre-flight tests passed after adding scratch-directory creation for fresh checkouts.
- Actual launcher: one server, two separate reuses, matching installation identity, authenticated Pre-flight and owned cleanup passed.
- Fake API lifecycle: two seats, no calls before dispatch, requested/confirmed model distinction, targeted restart/retry/Stop and worker Stop acknowledgement passed. No secret values persisted.
- Native fake CLI lifecycle: distinct models and MCP identities, unmentioned-peer isolation, targeted Stop with peer alive, model-change restart, hidden-console injection and exit code 23 surfaced as failed all passed.
- Both older lifecycle harnesses needed to await message_accepted instead of closing on an initial websocket event. Initial failed attempts were retained in private logs; corrected runs passed.
- Extracted release: all 70 Python source files matched by SHA256; boot and Pre-flight passed with repository PYTHONPATH removed. Build includes short README/STATUS and links detailed evidence to GitHub.
- Browser: canonical port 8300 showed exactly six saved seats, all Use controls checked. Screenshot inspected. Executables and credential references resolved without revealing values.
- Native Claude CLI resolved sonnet to claude-sonnet-5-5 and completed two source reviews with PASS. Reviewers did not independently execute tests. Linked receipts record that limitation.

## Acceptance boundary

Implemented, simulator-tested and reviewer-cleared: canonical source layout, launcher and release packaging. Existing RC2 component reviews remain historical evidence for the unchanged product.

Not yet demonstrated in this recovery: a real six-provider review, document/task visibility through that review, Stop/corrected restart with those providers, and Seth's acceptance. The two known unread-cursor defects remain explicitly open. This checkpoint is a candidate for acceptance, not a certified final release.

The working Desktop installation remains separate and unchanged. Canonical six-seat configuration was reconstructed from non-secret RC2 template fields with new local paths and no stale runtime ownership. Private side-build snapshots are retained under data/recovery-evidence, excluded from Git and release ZIPs.
