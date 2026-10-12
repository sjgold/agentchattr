"""Offline characterization of the pinned source, not acceptance of fixes.

Run: python -X utf8 -B tools/audit_launcher_baseline.py --installed <path>
Only reads allowlisted source files in the installed tree. Never imports its
modules, reads local settings/history/environment files, or starts an agent.
Extracted functions run against temporary files and fake transports/processes.
"""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock
import tomllib

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".py", ".toml", ".txt", ".html", ".bat", ".sh", ".js", ".css", ".json"}


def extract(path, name, namespace=None):
    """Compile one real function without executing module startup/imports."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    scope = {} if namespace is None else namespace
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), scope)
    return scope[name]


class EndPoll(BaseException):
    pass


def stop_poll(seconds):
    if seconds == 1:
        raise EndPoll()


def inventory(installed):
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    selected = [p for p in tracked if (
        "/" not in p and (Path(p).suffix in {".py", ".toml", ".txt", ".html"} or p == "VERSION")
        and p not in {"STATUS.md", "AGENTS.md"}
    ) or (p.split("/")[0] in {"windows", "macos-linux", "static", "session_templates"}
          and Path(p).suffix in TEXT_EXTENSIONS)]
    candidates = set(selected)
    for path in installed.iterdir():
        if path.is_file() and path.suffix in {".py", ".html"}:
            candidates.add(path.name)
    for directory in ("windows", "macos-linux", "static", "session_templates"):
        source_dir = installed / directory
        if source_dir.exists():
            for path in source_dir.rglob("*"):
                if path.is_file() and path.suffix in TEXT_EXTENSIONS:
                    candidates.add(path.relative_to(installed).as_posix())
    records = []
    for relative in sorted(candidates):
        current, previous = ROOT / relative, installed / relative
        a = current.read_bytes() if current.is_file() else None
        b = previous.read_bytes() if previous.is_file() else None
        state = "installed_only" if a is None else "fork_only" if b is None else (
            "same" if a.replace(b"\r\n", b"\n") == b.replace(b"\r\n", b"\n") else "different")
        records.append({"path": relative, "state": state,
                        "fork_sha256": hashlib.sha256(a).hexdigest() if a is not None else None,
                        "installed_sha256": hashlib.sha256(b).hexdigest() if b is not None else None})
    return records


def characterize(installed):
    observations = []
    scratch_parent = ROOT / ".audit-tmp"
    scratch_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="baseline-", dir=scratch_parent) as scratch:
        root = Path(scratch)
        # Run the actual JSON writer against disposable malformed input.
        writer = extract(ROOT / "wrapper.py", "_write_json_mcp_settings",
                         {"Path": Path, "json": json, "SERVER_NAME": "agentchattr"})
        target = root / "settings.json"
        original = b'{"keep": [malformed'
        target.write_bytes(original)
        writer(target, "http://example.invalid/mcp")
        assert target.read_bytes() != original
        assert json.loads(target.read_text())["mcpServers"]["agentchattr"]
        observations.append({"id": "E01", "observation": "Malformed JSON overwritten by shared writer"})

        # The Windows runner sees a failed child but returns None.
        fake_process = SimpleNamespace(pid=123, returncode=23, wait=lambda: 23)
        runner = extract(ROOT / "wrapper_windows.py", "run_agent", {
            "enable_vt_mode": lambda: None, "_vt_keepalive_thread": lambda: None,
            "subprocess": SimpleNamespace(Popen=lambda *a, **k: fake_process),
            "inject": lambda *a, **k: None,
        })
        result = runner("fake", [], str(root), {}, root / "unused", "fake", True, lambda fn: None)
        assert result is None
        observations.append({"id": "E02", "child_exit": 23, "runner_return": result})

        # CLI poll: actual watcher, fake role/rules/network-free injection.
        queue = root / "cli_queue.jsonl"
        queue.write_text('\n'.join(json.dumps(x) for x in [
            {"channel": "alpha", "job_id": 41}, {"channel": "beta", "prompt": "SECOND-PROMPT"}
        ]), encoding="utf-8")
        injected = []
        watcher = extract(ROOT / "wrapper.py", "_queue_watcher", {
            "json": json, "time": SimpleNamespace(sleep=stop_poll),
            "_fetch_role": lambda *a: "", "_fetch_active_rules": lambda *a: None,
        })
        try:
            watcher(lambda: ("fake", queue), injected.append)
        except EndPoll:
            pass
        assert injected == ["SECOND-PROMPT"] and queue.read_text() == ""
        observations.append({"id": "E03", "queued": 2, "injected": len(injected), "first_job_lost": True})

        # Compile the exact API polling loop for one iteration; replace only
        # its dependencies. Same-channel prompts collapse before handle_trigger.
        api_tree = ast.parse((ROOT / "wrapper_api.py").read_text(encoding="utf-8"))
        main = next(n for n in api_tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        loop = next(n for n in ast.walk(main) if isinstance(n, ast.While)
                    and any(isinstance(child, ast.Name) and child.id == "channels_triggered"
                            for child in ast.walk(n)))
        api_queue = root / "fake_queue.jsonl"
        api_queue.write_text('\n'.join(json.dumps({"channel": "alpha", "prompt": p}) for p in ("FIRST", "SECOND")), encoding="utf-8")
        handled = []
        namespace = {"data_dir": root, "get_name": lambda: "fake", "json": json,
                     "time": SimpleNamespace(sleep=stop_poll),
                     "handle_trigger": lambda **kw: handled.append(kw)}
        try:
            exec(compile(ast.Module(body=[loop], type_ignores=[]), "wrapper_api.py", "exec"), namespace)
        except EndPoll:
            pass
        assert handled == [{"channel": "alpha"}]
        observations.append({"id": "E04", "queued": 2, "api_calls": len(handled), "prompts_forwarded": False})

        # Capture model payload from real formatting/handling functions.
        payloads, sent, states, limits = [], [], [], []
        api_scope = {
            "get_name": lambda: "fake", "get_online_agents": lambda: [],
            "get_my_role": lambda: "", "system_prompt": "BASE",
            "set_working": states.append, "context_messages": 20,
            "read_messages": lambda **kw: limits.append(kw["limit"]) or [
                {"sender": "system", "text": "SESSION-INSTRUCTION"},
                {"sender": "user", "text": "hello", "attachments": [{"name": "SOURCE-SENTINEL"}]}],
            "call_model": lambda messages: payloads.append(messages) or "result",
            "send_message": lambda *a, **kw: sent.append((a, kw)),
        }
        extract(ROOT / "wrapper_api.py", "format_messages", api_scope)
        handle = extract(ROOT / "wrapper_api.py", "handle_trigger", api_scope)
        with contextlib.redirect_stdout(io.StringIO()):
            handle(channel="alpha")
        payload = json.dumps(payloads)
        assert "SESSION-INSTRUCTION" not in payload and "SOURCE-SENTINEL" not in payload
        assert limits == [20]
        observations.append({"id": "E05", "history_limit": 20, "system_message_included": False,
                             "attachment_included": False})
        sent.clear()
        def fail_model(messages):
            raise RuntimeError("fake provider failure")
        api_scope["call_model"] = fail_model
        with contextlib.redirect_stdout(io.StringIO()) as console:
            handle(channel="alpha")
        assert sent == [] and "Error handling trigger" in console.getvalue() and states[-1] is False
        observations.append({"id": "E06", "failure_posted": False, "failure_printed": True})

        # Real participant handler: plain status schedules advancement and
        # resumes a paused session; fake Timer avoids background execution.
        timers = []
        session = {"id": 1, "cast": {"reviewer": "fake"}, "state": "paused"}
        store = Mock()
        store.get_active.return_value = session
        instance = SimpleNamespace(_store=store, _messages=Mock(), _trigger=Mock(),
                                   _get_expected_agent=lambda s: "fake", _is_agent=lambda n: n == "fake",
                                   _advance=lambda *a: None)
        handler = extract(ROOT / "session_engine.py", "_handle_participant_message", {
            "threading": SimpleNamespace(Timer=lambda *a, **kw: SimpleNamespace(start=lambda: timers.append((a, kw)))),
        })
        handler(instance, {"id": 10, "type": "chat", "text": "Still working"}, "alpha", "fake")
        assert len(timers) == 1 and store.resume.call_count == 1
        observations.append({"id": "E07", "status_schedules_advance": True, "paused_session_resumed": True})
        end_session = extract(ROOT / "session_engine.py", "end_session", {"log": Mock()})
        end_session(instance, 1)
        assert store.interrupt.call_count == 1 and instance._trigger.mock_calls == []
        observations.append({"id": "E08", "end_updates_store": True, "trigger_cancellation_calls": 0})

        validate = extract(ROOT / "session_store.py", "validate_session_template")
        roles = [f"seat{i}" for i in range(6)]
        errors = validate({"name": "Six", "roles": roles, "phases": [
            {"name": "Review", "participants": roles, "prompt": "Review", "is_output": True}]})
        assert any("max 4" in error for error in errors)
        seven_errors = validate({"name": "Seven", "roles": roles + ["seat6"], "phases": [
            {"name": "Review", "participants": ["seat0"], "prompt": "Review", "is_output": True}]})
        assert any("max 6" in error for error in seven_errors)
        observations.append({"id": "E09", "six_seat_errors": errors, "seven_role_errors": seven_errors})

        # A local Hermes writer is a candidate to adapt, not trusted wholesale.
        # Compile just its function; YAML is optional for this diagnostic.
        try:
            import yaml
        except ImportError:
            observations.append({"id": "E11", "hermes_writer_check": "not run: PyYAML unavailable"})
        else:
            yaml_writer = extract(installed / "wrapper.py", "_write_yaml_mcp_settings", {
                "Path": Path, "shutil": shutil, "SERVER_NAME": "agentchattr"})
            yaml_target = root / "hermes.yaml"
            original_yaml = "# Keep\nmodel: example\nmcp_servers:\n  other:\n    url: http://example.invalid\n"
            yaml_target.write_text(original_yaml, encoding="utf-8")
            yaml_writer(yaml_target, "http://example.invalid/mcp", "fake-token")
            saved = yaml.safe_load(yaml_target.read_text(encoding="utf-8"))
            assert saved["model"] == "example" and "other" in saved["mcp_servers"]
            assert yaml_target.with_name("hermes.yaml.agentchattr.bak").read_text(encoding="utf-8") == original_yaml
            yaml_target.write_text("bad: [", encoding="utf-8")
            try:
                yaml_writer(yaml_target, "http://example.invalid/mcp", "fake-token")
            except yaml.YAMLError:
                pass
            else:
                raise AssertionError("Malformed YAML unexpectedly accepted")
            assert yaml_target.read_text(encoding="utf-8") == "bad: ["
            # An empty sequence is invalid as a server map, but the writer's
            # `or {}` accepts and replaces it instead of rejecting its shape.
            yaml_target.write_text("mcp_servers: []\n", encoding="utf-8")
            yaml_writer(yaml_target, "http://example.invalid/mcp", "fake-token")
            assert yaml_target.read_text(encoding="utf-8") != "mcp_servers: []\n"
            observations.append({"id": "E11", "hermes_mapping_and_backup_preserved": True,
                                 "malformed_yaml_preserved": True, "invalid_server_sequence_replaced": True})
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    files = inventory(args.installed)
    installed_cfg = tomllib.loads((args.installed / "config.toml").read_text(encoding="utf-8"))
    fork_cfg = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
    output = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "pinned_upstream": "d775776a30e8af4c85ea16b3caaf9c79d65cb239",
        "method": "allowlisted source comparison; AST-extracted functions with fake dependencies",
        "files": files, "observations": characterize(args.installed),
        "extra_installed_agent_ids": sorted(set(installed_cfg["agents"]) - set(fork_cfg["agents"])),
        "passive_executable_found": {name: shutil.which(name) is not None
                                     for name in ("omp", "hermes", "hermes.cmd", "codebuddy")},
    }
    if args.output:
        args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    counts = {state: sum(f["state"] == state for f in files)
              for state in ("same", "different", "fork_only", "installed_only")}
    print(json.dumps({"inventory": counts, "observations": output["observations"]}, indent=2))


if __name__ == "__main__":
    main()
