# Ticket #3 independent review handoff

Status: implemented and builder-verified, independent review and human sign-off pending. Frozen target will be recorded after the local implementation commit. Base: `8127ea1992e464cbbc56d63df2325742b8382bc9`. Branch: `codex/ticket-3-api-seat`.

Scope: issue #3, spec v1.7 PF-2/3/4 and AT-02; see `TICKET-3-PLAN.md` and `API-SEATS.md`. Review must come from a different family than OpenAI Codex. Builder backend ID is not exposed by this session; Sol was the requested build preference. Record actual reviewer identity, frozen hash, verdict, substantive findings, exact commands/results and platforms not verified. Do not self-approve, call live providers, use real credentials, touch the working Desktop installation or begin dependent tickets.

## Changes

- `api_seats.py`: strict package/seat/provider validation, atomic package storage and backups, provider capabilities, payload/response handling and atomic per-attempt receipts. Unknown secret fields rejected; saved credentials are references only.
- `api_seat_runtime.py`: serialized saves/launches, immutable settings snapshots, unique per-attempt registry bases, owned Popen handles, readiness/liveness deadlines, reuse only with matching settings, explicit targeted restart/stop and registry cleanup even if a child dies before receipt creation.
- `wrapper_api.py`: optional app-managed snapshot path; legacy invocation retained. Managed generation uses the tested payload helper, records evidence-based model/authentication results and safe failure diagnostics. Heartbeats maintain adapter liveness; prolonged local-server loss exits the managed child.
- `app.py`: authenticated provider/package/runtime APIs and save/launch/stop actions; shutdown releases owned children. `static/api_seats.js` and pre-flight markup/style provide package editing and bounded action polling using existing product tokens.
- Tests: package round-trip/schema/secrets/storage, real fake-HTTP payloads, process ownership/deadline/concurrency/staleness and authenticated endpoint validation. `tools/verify_api_seat.py` tests real server/wrappers against a fake provider and can keep the page open for browser checks.
- `.impeccable/config.json`: narrow `dark-glow` suppression for `static/preflight.html`; neither that HTML nor its page CSS contains a shadow declaration. The scanner matched imported legacy styling. No global rule/file suppression.

## Builder evidence

- Full suite: **198 tests run, OK, 4 Unix/tmux skips** on Windows, Python 3.14.6, dependencies already in `.venv-windows`. New configuration/runtime/endpoint assertions were observed failing before their implementations/fixes. No live-provider calls.
- Windows regression investigation reproduced a receipt replacement failure: a concurrent reader can block `os.replace` with WinError 5. The captured fake-wrapper traceback identified the failure; transient replacement now has bounded retries, and persistent failure preserves the old file. Dedicated tests failed before the fix. A stronger stop check also required actual-worker acknowledgement; a per-attempt control file and worker watcher now provide that acknowledgement before forced cleanup. Configuration/runtime regression counts: 9 and 14 tests respectively.
- Five final real-wrapper integration runs all passed, including `worker_stop_acknowledged: true`, after the fixes. Earlier failed runs are investigation evidence, not acceptance passes. Fake-only child debug logs remain under ignored scratch for diagnosis. A final process inventory found no surviving isolated fake-server processes.
- Real isolated app plus two real wrappers and a loopback fake provider: zero provider calls at launch; distinct seat identities; chosen model/reasoning delivered in the actual request; returned model remains distinct; authenticated fake endpoint requires the referenced fake credential; same-config reuse, mismatch rejection, targeted restart, 401 action-needed state, targeted retry and stopping one while the other remains ready. Disk inspection found no fake credential values/session token in saved package/snapshot/receipt JSON.
- Browser on isolated fake-provider app: selected the saved two-seat package and read the complete values back; form submit saved it; launch transitioned the stopped first seat to ready; stop affected only that seat while second remained ready; controls reenabled. At 390px there was no horizontal overflow. Screenshot tool failed to report a saved path, so visual screenshot inspection is not claimed. A later last-adapter-check label uses the same status payload; browser checks predated that final label addition.
- JavaScript syntax and diff whitespace checks passed. The test servers and isolated browser were stopped. Native Linux/Omarchy, real provider compatibility/quotas/model access, and mid-flight browser disconnection remain unverified.

## Reproduce

From the repo root in PowerShell, with existing platform dependencies:

```powershell
.venv-windows/Scripts/python.exe -X utf8 -B -c "import tempfile,unittest; tempfile.tempdir=r'C:\Users\SJG\Documents\CodePlayground\agentchattr\.audit-tmp'; r=unittest.TextTestRunner().run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not r.wasSuccessful())"
.venv-windows/Scripts/python.exe -X utf8 -B tools/verify_api_seat.py
node --check static/api_seats.js
git diff --check
```

Create `.audit-tmp` first if absent. Restricted hosts need loopback permission; use local writable temporary data. Substitute the Linux environment/path when testing there. For browser checks add `--serve` to the integration tool; Enter stops the isolated app's owned seats/server. Do not print/copy browser tokens or actual secret values.

## Adversarial review focus

Validate secrets across all persisted/public fields; malicious schema/types/URLs; manual model/default behavior; no silent reasoning/model substitution; response provenance; concurrent save/launch and active-seat removal; stale/missing/invalid receipts and child exits; cleanup of only owned processes/registrations; subprocess quoting and configured data paths/ports; provider failures versus local chat delivery failures; bounded polling and authentication/origin enforcement.

Readiness certifies chat dispatch only until a successful response supplies provider evidence. Declared reasoning capabilities come from provider configuration, not a hard-coded catalog or implicit live discovery. Full restart adoption/stale-result reconciliation (#9), durable turn delivery/outbox (#6–#8) and per-turn cancellation (#10) remain later scope. Review those boundaries for unsafe claims or interactions; do not treat them as implemented here.

Return PASS, PASS WITH NONBLOCKING NOTES or FAIL with file/line, concrete trigger/impact, correction and reproducible evidence. Substantive fixes require a newly frozen target and independent recheck. Human retains final completion sign-off; no merge, push or ticket closure authorized by this handoff.
