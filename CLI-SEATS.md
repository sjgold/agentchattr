# Configured CLI seats

Open pre-flight, create or select a saved package, add an agent seat and choose **Interactive CLI**. Pick a configured client template, save the package, then launch that seat. A package can mix CLI and API seats.

Use **Launch / reuse selected team** to check the saved team together, then enter chat when its included seats are ready. [Saved teams](PACKAGES.md) covers exclusions for one launch and stale-setting checks.

Launch opens an interactive Windows console or an owned tmux session on Unix. It writes the seat's MCP identity settings. Clients with isolated config flags or environment variables get private files; clients with a fixed settings path get a lifetime lock and backups before intentional edits. A second seat using that fixed path is rejected. Existing login files stay in place.

The runtime shows the resolved executable, whether its process started, a version when the template declares a version probe, requested model and child exit code. **Mention injection ready** means the wrapper can deliver console input. Login, actual MCP tool use and provider-confirmed model remain unknown. A CLI can still be waiting for login or folder trust; use its terminal to complete that step. API readiness keeps its existing meaning.

## Declaring supported settings

Only declared argument contracts enable CLI model/reasoning controls. Leave the model blank for the client's default. Manual IDs are unverified, and unsupported overrides fail before execution. Use your installed client's documented arguments; this example demonstrates the schema and does not assert a particular product's flags:

```toml
[agents.myclient]
command = "my-client-executable"
cwd = "."
label = "My CLI"
mcp_inject = "env"
mcp_env_var = "MY_CLIENT_MCP_SETTINGS"
cli_model_args = ["--model", "{model}"]
cli_reasoning_args = ["--reasoning", "{reasoning}"]
reasoning_efforts = ["high"]
# Optional, only when this is a version-only command for your client:
# cli_version_args = ["--version"]
```

Set these in `config.local.toml`. CLI templates are trusted local configuration; do not put credentials in argument mappings or model IDs. CLI seats use the client's native login rather than a saved API credential. Available MCP injection modes are the existing `env`, `flag`, `proxy_flag`, `env_content` and `settings_file` modes. Unknown modes fail validation.

Saved edits apply to the next launch. Reusing a healthy seat requires identical effective settings; an active mismatch requires **Restart**. **Stop** targets the application's owned worker and child, preserving sibling seats. A local stop does not guarantee cancellation at a remote model service. Server-restart adoption and durable turn recovery remain later tickets.

## Compatibility launchers

Named Windows and POSIX launchers route through `launch_agent.py` and the shared bootstrap. They use platform-specific environments and bounded server health checks. They install dependencies only with explicit `--setup`; a normal launch reports setup requirements. Failed child status propagates through the wrapper and launcher. Legacy convenience flags remain on their corresponding named profiles.

Generic entries: `windows/start_cli_agent.bat NAME` and `sh macos-linux/start_cli_agent.sh NAME`. `start_hermes` and `start_omp` are aliases for explicitly configured templates. They do not install clients or invent MCP contracts. A client without a supported identity configuration remains unavailable until configured. Windows batch-based clients reject shell expansion characters and argument delimiters (including commas, semicolons and equals signs); use a native executable or compatible safe profile for complex arguments.

## Verification boundary

Routine verification uses fake clients and isolated loopback servers. Native Linux/Omarchy and compatibility with real provider/client versions require separate authorized acceptance. The working Desktop installation is outside this change.
