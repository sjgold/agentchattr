# Daily-use seat template proposal

These settings are a proposal for `config.local.toml` in the intended daily installation. They have not been applied there. Keep the existing installation and its templates unchanged until Seth approves the final blocks.

Use distinct aliases: `claude_daily`, `codex_daily`, `agy_daily`, `omp_daily`, `hermes_daily`, `deepseek_daily`, `glm_daily`, `muse_daily`. API keys stay in the user's `.env`; templates name their variables only. The launcher reads referenced names into the server child, and managed CLI children strip those API names.

## Antigravity model settings

```toml
[agents.agy_daily]
command = "agy"
cwd = "."
label = "Antigravity"
cli_model_args = ["--model", "{model}"]
models = ["gemini-3.8-flash-high", "gemini-3.8-flash-medium", "gemini-3.8-flash-low"]
default_model = "gemini-3.8-flash-medium"
# MCP identity injection: pending corrected json_entry_file adapter review.
# Do not launch this incomplete template yet.
```

The Pre-flight model field accepts an explicit model and offers the three variants. Medium is the template fallback for a blank seat model. Effort is encoded in the high/medium/low model variant here. Saved explicit choices survive reload; launch passes the selected model through `--model`. Frozen RC0 uses an explicit saved medium value and its reviewed operational shim, rather than this pending daily injection.

The remaining alias blocks will be prepared from the tested seats before any daily-install change. Hermes is deferred from RC1 because its existing process and Windows batch-child Stop limitation need a separate decision.
