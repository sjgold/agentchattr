"""End-to-end ticket #4 check: a real isolated app driving a real fake CLI.

Mirrors tools/verify_api_seat.py's isolated-server technique (dynamic ports,
.audit-tmp scratch, a monkeypatched config_loader.load_config, an in-process
`run.main()` child) but exercises the CLI-seat runtime instead of the
API-seat one: a real Windows console, real Win32 keystroke injection, and a
real fake CLI subprocess (tools/fake_cli_seat.py) that records its own argv
and injected MCP identity config, then blocks on real stdin.

No live agent/provider is launched. Windows-only: the managed CLI runtime
this checks (CREATE_NEW_CONSOLE + WriteConsoleInput injection) only exists
on win32; there is no Linux/tmux equivalent to claim here.
"""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from launcher import stop_owned_child


def main():
    if sys.platform != "win32":
        print(json.dumps({"result": "SKIP",
                          "reason": "Managed CLI console runtime is Windows-only."}))
        return

    fixture = str((ROOT / "tools" / "fake_cli_seat.py").resolve())
    scratch = ROOT / ".audit-tmp"
    scratch.mkdir(exist_ok=True)
    child = None
    api = None
    try:
        temporary = tempfile.mkdtemp(prefix="cli seat integration ", dir=scratch)
        records_dir = Path(temporary) / "records"
        records_dir.mkdir()
        sockets = [socket.socket() for _ in range(3)]
        for handle in sockets:
            handle.bind(("127.0.0.1", 0))
        ports = [handle.getsockname()[1] for handle in sockets]
        for handle in sockets:
            handle.close()
        environment = os.environ.copy()
        environment.update(dict(zip(
            ("AGENTCHATTR_PORT", "AGENTCHATTR_MCP_HTTP_PORT", "AGENTCHATTR_MCP_SSE_PORT"),
            map(str, ports))))
        environment.update(AGENTCHATTR_DATA_DIR=str(Path(temporary) / "data"),
                           AGENTCHATTR_UPLOAD_DIR=str(Path(temporary) / "uploads"),
                           TICKET4_SCRATCH_DIR=str(records_dir))

        code = f'''import config_loader
load = config_loader.load_config
def isolated(root=None):
    cfg = load(root)
    cfg['agents'] = {{'fakecli': {{'command': {json.dumps(sys.executable)},
        'cwd': '.', 'cli_args': [{json.dumps(fixture)}],
        'cli_model_args': ['--model', '{{model}}'],
        'cli_reasoning_args': ['--reasoning', '{{reasoning}}'],
        'reasoning_efforts': ['high'],
        'mcp_inject': 'env', 'mcp_env_var': 'TICKET4_FAKE_SETTINGS'}}}}
    return cfg
config_loader.load_config = isolated
import run
run.main()
'''
        with (Path(temporary) / "server.log").open("wb") as output:
            child = subprocess.Popen([sys.executable, "-u", "-c", code], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)

        base = f"http://127.0.0.1:{ports[0]}"

        def wait_for(function, label, timeout=25):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise AssertionError("isolated server exited; inspect its temporary server log")
                try:
                    value = function()
                    if value:
                        return value
                except (OSError, KeyError):
                    pass
                time.sleep(0.1)
            raise AssertionError("deadline waiting for " + label)

        def page():
            with urllib.request.urlopen(base + "/preflight", timeout=2) as response:
                return response.read().decode("utf-8-sig")

        html = wait_for(page, "preflight")
        token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', html).group(1)

        def api(path, body=None):
            request = urllib.request.Request(base + path,
                headers={"x-session-token": token, "Content-Type": "application/json"},
                data=json.dumps(body).encode() if body is not None else None)
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)

        def send_human(text):
            from websockets.sync.client import connect
            with connect(base.replace("http://", "ws://") + "/ws?token=" + token, proxy=None) as connection:
                connection.send(json.dumps({"type": "message", "sender": "test-human",
                                           "text": text, "channel": "general"}))
                connection.recv(timeout=5)

        seat = {"id": "one", "name": "First fake CLI seat", "adapter": "cli", "provider": "fakecli",
                "model": "requested-one", "reasoning": "high", "launch_profile": "standard", "secret_ref": ""}
        package = {"id": "fake-cli-team", "name": "Fake CLI test team",
                   "seats": [seat, {**seat, "id": "two", "name": "Second fake CLI seat", "model": "requested-two"}]}
        api("/api/preflight/packages", package)

        def state(which, allow_failed=False):
            result = api("/api/preflight/seats")["runtime"].get("fake-cli-team/" + which, {})
            if result.get("state") == "failed" and not allow_failed:
                raise AssertionError("Fake CLI seat runtime failed: " + str(result.get("error")) +
                                     "; scratch: " + temporary)
            return result

        def record_path(model_value):
            return records_dir / f"record-{model_value}.json"

        def read_record(model_value):
            return json.loads(record_path(model_value).read_text("utf-8"))

        launch_path = "/api/preflight/seats/fake-cli-team/"
        first_attempt = api(launch_path + "one/launch", {})["attempt"]
        api(launch_path + "two/launch", {})
        wait_for(lambda: state("one").get("state") == "ready" and state("two").get("state") == "ready",
                "both fake CLI consoles ready")
        assert api(launch_path + "one/launch", {})["attempt"] == first_attempt, "idempotent re-launch spawned a new attempt"

        # -- distinct models and MCP bearer identities/config paths ---------
        wait_for(lambda: record_path("requested-one").exists(), "seat one fixture record")
        wait_for(lambda: record_path("requested-two").exists(), "seat two fixture record")
        record_one = read_record("requested-one")
        record_two = read_record("requested-two")
        for record in (record_one, record_two):
            assert record['console_exists'], 'CLI needs a real console for input injection'
            assert record['console_window_visible'] is False, 'Managed CLI console should start hidden'
        assert record_one["model"] == "requested-one"
        assert record_two["model"] == "requested-two"
        assert record_one["reasoning"] == "high" and record_two["reasoning"] == "high"
        assert record_one["mcp_settings_path"] and record_two["mcp_settings_path"]
        assert record_one["mcp_settings_path"] != record_two["mcp_settings_path"], \
            "both seats were handed the same MCP settings file path"
        bearer_one = record_one["mcp_settings"]["mcpServers"]["agentchattr"]["headers"]["Authorization"]
        bearer_two = record_two["mcp_settings"]["mcpServers"]["agentchattr"]["headers"]["Authorization"]
        assert bearer_one and bearer_two and bearer_one != bearer_two, \
            "both seats were handed the same MCP bearer identity"

        # -- only the mentioned seat receives the injected prompt -----------
        # The wrapper's queue watcher injects a fixed trigger phrase on
        # @mention (wrapper.py's "you're mentioned, take appropriate action
        # and respond"), not the raw chat text, so that fixed phrase is the
        # marker to look for.
        first_name = state("one")["name"]
        second_name = state("two")["name"]
        assert first_name != second_name
        trigger = "you're mentioned"
        send_human("@" + first_name + " reply with test text")
        wait_for(lambda: any(trigger in p for p in read_record("requested-one").get("prompts", [])),
                "seat one received the injected prompt")
        time.sleep(1.5)  # give seat two's watcher a full poll cycle too
        assert not any(trigger in p for p in read_record("requested-two").get("prompts", [])), \
            "the unmentioned seat also received the injected prompt"

        # -- targeted stop leaves the peer alive; worker acknowledges -------
        api(launch_path + "one/stop", {})
        stopped_receipt = Path(temporary) / "data" / "api_seat_runtime" / first_attempt / "receipt.json"
        wait_for(lambda: json.loads(stopped_receipt.read_text("utf-8")).get("state") == "stopped",
                "seat one worker acknowledged stop")
        assert state("two")["state"] == "ready", "stopping seat one affected its peer"

        # -- model edit on a still-running seat requires explicit restart ---
        package["seats"][1]["model"] = "changed-two"
        api("/api/preflight/packages", package)
        try:
            api(launch_path + "two/launch", {})
            raise AssertionError("mismatched active seat reused without an explicit restart")
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        api(launch_path + "two/launch", {"restart": True})
        wait_for(lambda: state("two").get("state") == "ready", "seat two targeted restart")
        assert state("two")["requested_model"] == "changed-two"
        wait_for(lambda: record_path("changed-two").exists(), "restarted seat two fixture record")

        # -- a stopped seat can restart with a new requested model ----------
        package["seats"][0]["model"] = "restarted-one"
        api("/api/preflight/packages", package)
        api(launch_path + "one/launch", {"restart": True})
        wait_for(lambda: state("one").get("state") == "ready", "seat one restarted with a new model")
        assert state("one")["requested_model"] == "restarted-one"
        wait_for(lambda: record_path("restarted-one").exists(), "restarted seat one fixture record")
        for model in ('changed-two', 'restarted-one'):
            record = read_record(model)
            assert record['console_exists'] and record['console_window_visible'] is False
        restarted_name = state("one")["name"]

        # -- fixture-driven exit 23 propagates as child_exit_code -----------
        # The fixture exits with status 23 on its SECOND received console
        # line (see tools/fake_cli_seat.py): one harmless mention, then one
        # that kills it, so the test can drive the exit deterministically
        # without needing custom text in the (fixed) injected trigger.
        send_human("@" + restarted_name + " first harmless mention")
        wait_for(lambda: len(read_record("restarted-one").get("prompts", [])) >= 1,
                "restarted seat one received its first prompt")
        send_human("@" + restarted_name + " second mention triggers exit")
        final = wait_for(lambda: state("one", allow_failed=True).get("child_exit_code") == 23
                                  and state("one", allow_failed=True),
                         "fixture exit code 23 observed")
        assert final['state'] == 'failed', 'failed CLI exit was mislabeled as a successful stop'
        assert final['authentication'] == 'unknown'
        assert final['confirmed_model'] is None
        assert token not in (Path(temporary) / 'data' / 'api_seats.json').read_text(encoding='utf-8')

        print(json.dumps({"result": "PASS", "url": base + "/preflight", "seats": 2,
            "distinct_models": True, "distinct_mcp_bearer_identities": True,
            "unmentioned_seat_isolated": True, "targeted_stop_peer_alive": True,
            "worker_stop_acknowledged": True, "model_edit_requires_restart": True,
            "stopped_seat_restart_with_new_model": True,
            "hidden_console_input_verified": True,
            "child_exit_code": final.get("child_exit_code"), "final_state_after_exit_23": final.get("state")}),
            flush=True)

        if "--serve" in sys.argv:
            input("Press Enter to stop the isolated CLI-seat test server: ")
        for which in ("one", "two"):
            try:
                api(launch_path + which + "/stop", {})
            except urllib.error.HTTPError:
                pass
    finally:
        if api is not None and child is not None and child.poll() is None:
            for which in ("one", "two"):
                try:
                    api("/api/preflight/seats/fake-cli-team/" + which + "/stop", {})
                except OSError:
                    pass
        if child is not None:
            stop_owned_child(child)


if __name__ == "__main__":
    main()
