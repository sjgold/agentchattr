# Configure and launch API seats

Open pre-flight through the shared launcher. The **API seats** section saves named packages containing multiple seats, including multiple models using one provider. Enter stable lowercase IDs, display names, provider template, requested model/reasoning and a credential **environment-variable name**. Never enter a key value. Save package before launching.

Provider templates come from configured `[agents.NAME]` entries with `type = "api"`. Existing `config.local.toml` merge rules still apply: use a new name rather than overriding a built-in agent. Example template structure:

```toml
[agents.my_api]
type = "api"
label = "My provider"
base_url = "https://your-provider.example/v1"
api_key_env = "MY_PROVIDER_KEY"
model = "your-model-id"
# Optional suggestions supplied by your configuration; not provider confirmation:
models = ["your-model-id", "another-model-id"]
# Omit unless this endpoint supports the reasoning_effort payload field/values:
reasoning_efforts = ["high"]
```

This is a schema example, not a working service or a claim about any model's capabilities. HTTPS is required except for loopback HTTP endpoints. URL credentials, query strings and fragments are rejected. The adapter is OpenAI-compatible chat completions; other API protocols are not supported by this ticket.

Model suggestions come from template configuration. Manual IDs are allowed and remain unverified. Blank model means **Provider default**: the request omits `model`; it does not silently substitute the template's suggested model. Reasoning is omitted unless selected from the provider template's declared capabilities. Unsupported settings fail validation. An endpoint that requires a model will report failure if Provider default is selected.

Secrets must already exist in the server environment. A missing reference produces an action-needed state without spawning a wrapper. Set credentials through your existing environment/secret mechanism and restart the server so it inherits them. Credential values are not entered in the browser, saved in packages, put on command lines or emitted in managed diagnostics.

**Launch / reuse** starts a missing API wrapper or reuses a live matching owned attempt. It does not call the provider. Ready means connected for **chat dispatch**, not successful authentication/generation. Sending an ordinary chat message mentioning the displayed chat name can consume provider usage. Only a successful completion proves access to that provider; only a response's `model` value supplies provider-confirmed model identity. Requested and confirmed values remain separate, including when they differ. The UI labels confirmation as the last successful response, not proof of a future request.

Saving edits leaves running settings unchanged. Use **Restart / retry this seat** to explicitly replace that owned attempt; other seats keep running. **Stop this seat** stops its owned wrapper. Stop a live seat before removing it from the package. Stopping a local wrapper cannot guarantee cancellation of a request already executing at a remote provider; per-turn cancellation/outbox/recovery are later tickets.

Startup/heartbeat inspection uses a 15-second deadline, owned-process cleanup allows two seconds for a worker stop acknowledgement, then at most six seconds for forced cleanup, and provider requests use a 120-second socket timeout. Browser requests time out after ten seconds; action polling runs for at most twenty subsequent checks. Refresh checks reinspects without calling models. Child exit, expired/missing receipts, provider HTTP errors and local delivery failures are surfaced separately where evidence allows. Managed wrappers exit when their local server stays unreachable; full server-restart reconciliation remains ticket #9 and is not claimed here.

Packages live in `api_seats.json` under the configured data directory. Updates are atomic; intentional replacements back up valid previous contents. Malformed storage is preserved and blocks saving until repaired/restored. Per-attempt settings and safe status receipts live under `api_seat_runtime/` in the same data directory. Each attempt has a unique chat identity and keeps secret references only. The server tracks its own Popen handles; it never searches for or kills external processes by executable name.

This runtime currently requires IPv4 loopback (`127.0.0.1`/`localhost`); an IPv6-only server gets an explicit validation error. Windows behavior is tested. Linux/Omarchy execution remains deferred because of the user's mounted filesystem issue.

## Reproduce without live providers

Run the full unittest suite in the platform environment, using a writable temporary directory and loopback permission on restricted hosts. `tools/verify_api_seat.py` starts an isolated app, two actual API wrappers and a loopback fake provider; it tests chosen payload settings, response provenance, secret-reference resolution, zero provider calls on launch, reuse/mismatch, targeted restart/retry/stop and authentication failure. It keeps scratch evidence under ignored `.audit-tmp`; it stops its owned wrappers/server afterwards. `--serve` holds the fake-provider page until Enter for browser checks. No configured external providers are contacted.
