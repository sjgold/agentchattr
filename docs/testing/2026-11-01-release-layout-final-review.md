# Frozen layout follow-up review

Claude Sonnet 5.5 reviewed commit 567b9a6 using read-only source tools. This is source clearance, not independently executed acceptance.

**Verdict: PASS**, with four non-blocking findings. This is a source review only. I ran nothing, so I did not re-verify the reported runs or the full regression.

**Test path expectations: correct, assertions not weakened**
- `test_runtime_ownership.py:14` and `:197` expect `worker_root` to be the project root. That matches `src/runtime_ownership.py:155`, and the assertion is still an exact equality.
- `test_preflight.py:35` computes the identity from `app.__file__`'s grandparent, which is the project root that `src/app.py:374` uses. That is a real equality check against `/api/health`.
- `test_artifact_capability.py` hashes `fixture.ROOT/'src'/name` against the manifest (`:148`) and still asserts `runtime_protocol.py` is a key (`:145`). The traversal-key negative case (`:161`) is retained.
- I only grepped `test_artifact_workers.py`. Its `.parent` hits are snapshot paths and artifact parent packets, not layout paths, and I saw no layout edits there.

**Websocket acknowledgements: correct**
- Both seat scripts wait for `message_accepted` and raise on `message_error`. Both event types are emitted by `src/app.py:2116` and `:2119-2130`.
- `recv(timeout=5)` raises if no acknowledgement arrives, so a missing ack fails loudly instead of passing silently.

**Release smoke: it does exercise the extracted sources, with a limited guarantee**
- `spawn_server` runs `<extracted>/src/run.py` with `cwd` set to the extracted root (`src/launcher.py:229`).
- The health probe requires an identity hash that includes the root path. A server that started from the repo would not match the extracted root, so a `matching` result is real evidence. The `/preflight` request adds a little more.
- The scripts and the launcher, config loader and builder come from the repo, not the extracted copy. That is acceptable, because only the server child needs to be the extracted code.

**Findings**
1. **Low:** `tools/verify_release.py:29` compares only the `.py` filenames in `src/`. Because it builds fresh from the same tree, content drift is unlikely. A hash comparison of the extracted files against `ROOT/src` would be a cheap, stronger check.
2. **Low:** the child inherits the environment, and `tools/test.ps1:6` sets `PYTHONPATH` to the repo's `src` and the repo root. The extracted script's own directory comes first on the import path, so the extracted modules win. Any import that is not in the extracted `src` would silently fall back to the repo copy. The name-equality check blocks that for `.py` modules, but the smoke doesn't guard it directly. Dropping `PYTHONPATH` from the child's environment in `verify_release.py` would make the check airtight.
3. **Low:** `tests/test_preflight.py:68` uses `root/'.audit-tmp'` without creating it. `test_runtime_ownership.py:21` does create it, and the directory is gitignored. A fresh clone running `test_preflight` on its own would fail with `FileNotFoundError`. Add `mkdir(exist_ok=True)` there.
4. **Info:** `tools/test.ps1` is correct. It restores `PYTHONPATH`, propagates the exit code, and hard-codes `.venv-windows`, so it is Windows-only.

The final full regression result is still outstanding. The 48 affected tests passing is consistent with what I read.

Lead disposition: strengthened extracted source checks to compare SHA256 bytes and clear inherited PYTHONPATH; extracted-release boot passed again. Added the missing scratch-directory creation. The review's statement that it saw no layout edit in test_artifact_workers.py is a coverage limitation: its drift fixture was explicitly updated to project/src. The behavioral negative assertion remains intact and passed in the 48-test recheck.
