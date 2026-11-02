# Dynamic model catalog review

2026-11-01. Backend: Sol. UI: Luna, with xhigh correction pass. Independent reviewer: native Claude Sonnet 5.5. All reviewer claims below are source review, not independently executed tests.

Initial review required corrections for stale effort rejection, unknown capability allowlists, non-exhaustive native picker retirement, partial parsing, select-value preservation, missing-provider preservation and refresh ordering. Red-first regressions were added; backend selection passed 96 tests and UI selection passed 37 tests.

Combined corrected review returned PASS. A subsequent root integration probe found catalog metadata alone changed a running seat's effective fingerprint. The correction retains original catalog evidence only for operational comparison of an unchanged running seat. Commands and operator settings are still compared; new launches and explicit restarts validate current metadata. Snapshot bytes and immutable ownership fingerprints remain intact. The exact regression passed and a narrow Sonnet recheck returned PASS.

Verified metadata sources: Claude native initialization without user turn, Codex app-server model catalog with native cache freshness, Antigravity native models command, and GET models endpoints for DeepSeek, Muse and GLM. Actual metadata-only checks succeeded for all six source types. Native lists are not treated as exhaustive retirement authority. Missing Muse/GLM capability fields do not establish chat compatibility or effort support.

Last-good data and timestamps survive failure. Partial data can add choices without removing prior ones. A watchdog restores UI responsiveness while physical singleflight prevents duplicate outstanding probes. Underlying library calls cannot always be forcibly cancelled. Native login changes lack an independently verified account binding; those catalogs never establish retirement.

Review transcripts are retained privately under data/recovery-evidence after integration. Live rendered selector verification is recorded in root STATUS.md.
