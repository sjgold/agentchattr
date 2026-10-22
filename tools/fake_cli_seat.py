"""Fake interactive CLI used only by tools/verify_cli_seat.py.

Spawned by the real cli_worker.py/wrapper_windows.py runtime inside an
app-owned Windows console, exactly like a real agent CLI would be. Records
its own argv and the private MCP identity config the wrapper injected for it
to a uniquely-named scratch file (keyed by its requested --model), then
blocks on real console stdin to capture the keystrokes the wrapper injects
on an @mention. Never calls any external tool, model or network endpoint.

A wrapper mention injects a fixed generic trigger phrase, never the raw
chat text, so this fixture can't match on custom marker text. Instead its
SECOND received console line makes it exit with status 23, so the test can
drive that deterministically (one harmless mention, then one that kills it)
and observe child_exit_code propagate end to end.
"""
import json
import os
import sys
from pathlib import Path

_SETTINGS_ENV_VAR = "TICKET4_FAKE_SETTINGS"


def _argval(args, flag):
    return args[args.index(flag) + 1] if flag in args else None


def main():
    args = sys.argv[1:]
    model = _argval(args, "--model")
    reasoning = _argval(args, "--reasoning")

    scratch = Path(os.environ["TICKET4_SCRATCH_DIR"])
    scratch.mkdir(parents=True, exist_ok=True)
    record_path = scratch / f"record-{model or 'unknown'}.json"

    settings_path = os.environ.get(_SETTINGS_ENV_VAR, "")
    settings = None
    if settings_path:
        try:
            settings = json.loads(Path(settings_path).read_text("utf-8"))
        except (OSError, ValueError):
            settings = None

    record = {"argv": args, "model": model, "reasoning": reasoning,
              "mcp_settings_path": settings_path, "mcp_settings": settings,
              "prompts": []}

    def save():
        record_path.write_text(json.dumps(record), encoding="utf-8")

    save()

    while True:
        try:
            line = input()
        except EOFError:
            break
        record["prompts"].append(line)
        save()
        if len(record["prompts"]) >= 2:
            sys.exit(23)
        if settings:
            import asyncio
            from queue_fixture import release_dispatch
            asyncio.run(release_dispatch(settings, line))


if __name__ == "__main__":
    main()
