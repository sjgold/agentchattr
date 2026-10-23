"""API agent wrapper — bridges the chat room to an OpenAI-compatible endpoint.

Usage:
    python wrapper_api.py qwen
    python wrapper_api.py my-local-model

For local models (Ollama, llama-server, LM Studio, etc.) that expose an
OpenAI-compatible /v1/chat/completions endpoint but have no CLI to inject
keystrokes into.

How it works:
  1. Loads config (config.toml + config.local.toml).
  2. Registers with the chat server via POST /api/register.
  3. Starts a heartbeat thread (same pattern as wrapper.py).
  4. Polls the queue file for @mentions.
  5. On trigger: reads recent chat context, formats into OpenAI messages,
     POSTs to the model's /v1/chat/completions, sends reply via POST /api/send.
  6. On exit: deregisters cleanly.
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent


class _ManagedProviderFailure(Exception):
    """Provider diagnostic already recorded without exposing response bodies."""
    def __init__(self, http_status=None, category='provider_failure'):
        super().__init__('Provider invocation failed.')
        self.http_status = http_status
        self.category = category


def _auth_headers(token: str, *, include_json: bool = False) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if include_json:
        headers["Content-Type"] = "application/json"
    return headers


def _cancellation_requested(queue, dispatch_id, shutdown):
    if shutdown.is_set():
        return True
    try:
        current = queue.claim()
    except (OSError, ValueError):
        # A server restart makes this observation unavailable, not cancelled.
        # The existing heartbeat lease, local Stop and provider deadline still
        # bound execution; the server's durable fence decides publication.
        return shutdown.is_set()
    return bool(current and current['envelope']['dispatch_id'] == dispatch_id
                and current['state'] == 'cancelling')


def main():
    from config_loader import apply_cli_overrides, load_config
    from wrapper import _register_instance

    # Apply AGENTCHATTR_* overrides (from CLI flags or env) BEFORE loading
    # config so the API wrapper connects to the same data_dir/ports as a
    # server launched with matching flags.
    apply_cli_overrides()
    config = load_config(ROOT)
    # Managed seats use an immutable app-owned snapshot, never mutate config.toml.
    preparse = argparse.ArgumentParser(add_help=False)
    preparse.add_argument('--seat-file')
    managed_args, _ = preparse.parse_known_args()
    managed = None
    birth = None
    observed_boot = [None]
    receipt = None
    shutdown = threading.Event()
    if managed_args.seat_file:
        from api_seats import Receipt, validate_seat
        managed = json.loads(Path(managed_args.seat_file).read_text('utf-8'))
        validate_seat(managed['seat'], {managed['seat']['provider']: managed['provider']})
        from runtime_ownership import record_worker_birth
        birth = record_worker_birth(managed_args.seat_file, managed)
        config['server'] = managed['server']
        config['agents'] = {managed['base']: {**managed['provider'], 'type': 'api',
                           'model': managed['seat']['model'], 'label': managed['seat']['name'],
                           'api_key_env': managed['seat']['secret_ref']}}
        receipt = Receipt(Path(managed_args.seat_file).with_name('receipt.json'), managed['attempt'])
        receipt.update()
        receipt.watch_for_stop(on_stop=shutdown.set)
    agent_names = list(config.get("agents", {}).keys())
    api_agents = [n for n in agent_names if config["agents"][n].get("type") == "api"]

    if not api_agents:
        print("  No API agents found in config.\n")
        print("  To add one, copy the example config:")
        print("    cp config.local.toml.example config.local.toml")
        print("  Then uncomment and edit an [agents.NAME] section (set type = \"api\").")
        print("  Finally: python wrapper_api.py <name>")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="API agent wrapper for OpenAI-compatible endpoints")
    parser.add_argument("agent", choices=api_agents,
                        help=f"API agent to run ({', '.join(api_agents)})")
    parser.add_argument("--label", type=str, default=None, help="Custom display label")
    parser.add_argument("--seat-file", help="App-owned immutable managed API-seat snapshot")
    # Per-project isolation flags (consumed by apply_cli_overrides above;
    # listed here so --help shows them and argparse doesn't error on them).
    parser.add_argument("--data-dir",      default=None, help="Override server.data_dir (path)")
    parser.add_argument("--port",          default=None, help="Override server.port (int)")
    parser.add_argument("--mcp-http-port", default=None, help="Override mcp.http_port (int)")
    parser.add_argument("--mcp-sse-port",  default=None, help="Override mcp.sse_port (int)")
    parser.add_argument("--upload-dir",    default=None, help="Override images.upload_dir (path)")
    args = parser.parse_args()

    agent = args.agent
    agent_cfg = config["agents"][agent]
    server_port = config.get("server", {}).get("port", 8300)
    data_dir = ROOT / config.get("server", {}).get("data_dir", "./data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Model API config
    base_url = agent_cfg.get("base_url", "").rstrip("/")
    if not base_url:
        print(f"  Error: [agents.{agent}] must have base_url (e.g. http://localhost:8189/v1)")
        sys.exit(1)
    model = agent_cfg.get("model", "")
    api_key_env = agent_cfg.get("api_key_env", "")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    temperature = agent_cfg.get("temperature")
    if temperature is not None:
        temperature = float(temperature)
        # Clamp: some providers (e.g. MiniMax) require temperature in (0.0, 1.0]
        if temperature <= 0:
            temperature = 0.01
        if temperature > 2.0:
            temperature = 2.0
    context_messages = int(agent_cfg.get("context_messages", 20))
    system_prompt = agent_cfg.get("system_prompt",
        f"You are {agent_cfg.get('label', agent)}, a helpful AI assistant participating "
        "in a developer chat room. Keep responses concise and relevant. "
        "You can see recent messages for context.")

    # Register with server
    try:
        registration = _register_instance(server_port, agent, args.label)
    except Exception as exc:
        if receipt:
            receipt.update(state='failed', error='Registration failed. Check the local server and retry this seat.')
        print(f"  Registration failed ({exc}).")
        print("  Is the server running? Start it with: python run.py")
        sys.exit(1)

    name = registration["name"]
    token = registration["token"]
    if receipt:
        receipt.update(identity_id=registration.get('identity_id'))
    print(f"  Registered as: {name} (slot {registration.get('slot', '?')})")

    # Thread-safe identity state (can change via heartbeat rename)
    _lock = threading.Lock()
    _state = {"name": name, "token": token, "working": False}

    def get_name():
        with _lock:
            return _state["name"]

    def get_token():
        with _lock:
            return _state["token"]

    def set_identity(new_name=None, new_token=None):
        with _lock:
            if new_name:
                _state["name"] = new_name
            if new_token:
                _state["token"] = new_token

    def set_working(val):
        with _lock:
            _state["working"] = val

    def is_working():
        with _lock:
            return _state["working"]

    # Heartbeat thread — same pattern as wrapper.py
    last_heartbeat = [time.monotonic()]
    def _heartbeat():
        while not shutdown.is_set():
            try:
                n = get_name()
                t = get_token()
                heartbeat_body = {"active": is_working()}
                if birth:
                    from runtime_ownership import heartbeat_payload
                    heartbeat_body['runtime_ownership'] = heartbeat_payload(birth, observed_boot[0])
                req = urllib.request.Request(
                    f"http://127.0.0.1:{server_port}/api/heartbeat/{n}",
                    method="POST",
                    data=json.dumps(heartbeat_body).encode(),
                    headers=_auth_headers(t, include_json=True),
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp_data = json.loads(resp.read())
                observed_boot[0] = resp_data.get('runtime_ownership', {}).get('boot_id')
                server_name = resp_data.get("name", n)
                if server_name != n:
                    set_identity(new_name=server_name)
                    print(f"  Identity updated: {n} -> {server_name}")
                if receipt:
                    receipt.update(adapter_connected=True, name=get_name())
                last_heartbeat[0] = time.monotonic()
            except urllib.error.HTTPError as exc:
                if exc.code == 409:
                    try:
                        replacement = _register_instance(server_port, agent, args.label)
                        set_identity(replacement["name"], replacement["token"])
                        if receipt:
                            receipt.update(identity_id=replacement.get('identity_id'))
                        print(f"  Re-registered as: {replacement['name']}")
                    except Exception:
                        pass
            except Exception:
                pass
            if receipt and time.monotonic() - last_heartbeat[0] > 15:
                receipt.update(state='failed', adapter_connected=False,
                               error='Local server connection lost. Restart this seat from pre-flight.')
                # Do not keep a managed child when its server stays unreachable.
                shutdown.set()
            shutdown.wait(5)

    threading.Thread(target=_heartbeat, daemon=True).start()

    # Get this agent's role from server status
    def get_my_role():
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{server_port}/api/status",
                headers=_auth_headers(get_token()),
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = json.loads(resp.read())
            my_name = get_name()
            info = status.get(my_name, {})
            return info.get("role", "") if isinstance(info, dict) else ""
        except Exception:
            return ""

    # Get online agents from server
    def get_online_agents():
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{server_port}/api/status",
                headers=_auth_headers(get_token()),
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = json.loads(resp.read())
            online = [n for n, info in status.items()
                      if isinstance(info, dict) and info.get("available")]
            return online
        except Exception:
            return []

    # Read recent messages from chat server
    def read_messages(channel="general", since_id=0, limit=20, job_id=None):
        params = f"limit={limit}&channel={channel}"
        if job_id is not None:
            params += f"&job_id={job_id}"
        if since_id:
            params = f"since_id={since_id}&{params}"
        req = urllib.request.Request(
            f"http://127.0.0.1:{server_port}/api/messages?{params}",
            headers=_auth_headers(get_token()),
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    # Send message back to chat
    def send_message(text, channel="general", job_id=None, dispatch_id=None):
        payload = {"text": text, "channel": channel}
        if dispatch_id:
            payload['dispatch_id'] = dispatch_id
        if job_id is not None:
            payload["job_id"] = job_id
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{server_port}/api/send",
            method="POST",
            data=body,
            headers=_auth_headers(get_token(), include_json=True),
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    # Call OpenAI-compatible chat completions API
    def call_model(messages, dispatch_id):
        from api_invocation import run_completion, InvocationFailure
        def cancelled():
            return _cancellation_requested(queue, dispatch_id, shutdown)
        if managed:
            try:
                evidence = None
                if managed.get('ownership'):
                    evidence = {'runtime_path': str(Path(managed_args.seat_file).resolve().parent),
                                'launch_attempt': managed['attempt'],
                                'launch_nonce': managed['ownership']['launch_nonce'], 'dispatch_id': dispatch_id}
                result = run_completion(managed['seat'], managed['provider'], messages, cancelled, evidence=evidence)
            except InvocationFailure as exc:
                auth_failure = exc.http_status in (401, 403)
                diagnostic = (f'Provider returned HTTP {exc.http_status}. Check provider settings/limits and retry this seat.'
                              if exc.http_status else
                              'Provider request failed, timed out or returned invalid text. Check provider availability/settings and retry this seat.')
                receipt.update(state='action_required' if auth_failure else 'failed',
                               authentication='failed' if auth_failure else receipt.value['authentication'],
                               error='Provider rejected authentication. Check the credential reference and retry.' if auth_failure else diagnostic)
                raise _ManagedProviderFailure(exc.http_status, exc.category) from None
            receipt.update(confirmed_model=result['confirmed_model'], authentication='verified',
                           state='ready', error=None)
            return result['content']
        seat = {'id': 'compatibility', 'name': get_name(), 'provider': 'compatibility',
                'adapter': 'openai-compatible', 'model': model or None, 'reasoning': None,
                'launch_profile': 'standard', 'secret_ref': api_key_env}
        try:
            result = run_completion(seat, {'base_url': base_url, 'temperature': temperature}, messages, cancelled)
        except InvocationFailure as exc:
            raise _ManagedProviderFailure(exc.http_status, exc.category) from None
        return result['content']

    # Format chat messages into OpenAI format
    def format_messages(chat_msgs):
        my_name = get_name()

        # Build dynamic system prompt with online status, role, and mention instructions
        online = get_online_agents()
        others = [n for n in online if n != my_name]
        parts = [system_prompt]
        # Inject role if set
        my_role = get_my_role()
        if my_role:
            parts.append(f"role: {my_role}")
        if others:
            parts.append(f"Currently online: {', '.join(others)}.")
            parts.append("To mention another agent and trigger them to respond, "
                         "use @name (e.g. " + ", ".join(f"@{n}" for n in others[:3]) + ").")
        parts.append(f"Your name in this chat is {my_name}. Do not prefix your "
                     "messages with your own name.")

        messages = [{"role": "system", "content": " ".join(parts)}]
        for msg in chat_msgs:
            sender = msg.get("sender", "")
            text = msg.get("text", "")
            if sender == "system":
                continue
            role = "assistant" if sender == my_name else "user"
            messages.append({"role": role, "content": f"{sender}: {text}"})
        return messages

    last_failure_category = ['']
    last_failure_http_status = [None]
    last_cancelled = [False]
    unresolved_dispatches = set()

    # Handle a trigger — read context, call model, respond
    def handle_trigger(channel="general", review_brief_id=None, prompt='', frozen=False, job_id=None, dispatch_id=None):
        from turn_events import EventValidationError
        from api_invocation import InvocationCancelled
        last_failure_category[0] = ''
        last_failure_http_status[0] = None
        last_cancelled[0] = False
        saved_result = [False]
        my_name = get_name()
        set_working(True)
        try:
            if receipt:
                receipt.update(result_saved=False, result_id=None, recoverable_result=False)
            chat_msgs = read_messages(channel=channel, limit=context_messages, job_id=job_id)
            if frozen:
                from review_brief import BriefError, brief_messages
                import re
                if not isinstance(review_brief_id, str) or not re.fullmatch(r'[0-9a-f]{32}', review_brief_id):
                    raise BriefError('Invalid frozen review brief reference.')
                req = urllib.request.Request(
                    f'http://127.0.0.1:{server_port}/api/review-briefs/{review_brief_id}',
                    headers=_auth_headers(get_token()))
                with urllib.request.urlopen(req, timeout=10) as resp:
                    envelope = json.loads(resp.read())
                if envelope.get('channel') != channel:
                    raise BriefError('Review brief channel mismatch.')
                messages = brief_messages(envelope, chat_msgs, my_name, system_prompt)
            elif not chat_msgs and not prompt:
                return False
            else:
                messages = format_messages(chat_msgs)
                if prompt:
                    messages.insert(1, {'role': 'system', 'content': prompt})
            def generate():
                print(f"  [{channel}] Calling model with {len(messages)} messages...")
                return call_model(messages, dispatch_id)

            if frozen and managed is not None:
                from result_delivery import complete_review_turn
                def on_saved(result_id):
                    saved_result[0] = True
                    if receipt:
                        # Eligibility belongs to server-side run/attempt fences,
                        # not the existence of a file in this worker.
                        receipt.update(result_saved=True, result_id=result_id, recoverable_result=None)
                def submit(event):
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{server_port}/api/sessions/{envelope['session_id']}/event",
                        data=json.dumps(event).encode('utf-8'),
                        headers=_auth_headers(get_token(), include_json=True))
                    with urllib.request.urlopen(request, timeout=10) as delivered:
                        return json.load(delivered)
                outcome = complete_review_turn(Path(managed_args.seat_file).resolve().parent,
                    envelope, dispatch_id, generate, submit, on_saved=on_saved)
                if outcome['status'] == 'admitted':
                    if receipt:
                        receipt.update(state='ready', error=None, recoverable_result=False)
                    return True
                last_failure_category[0] = 'local_delivery_failure'
                if receipt:
                    receipt.update(state='failed', error='A saved answer is retained. Check its delivery status before generating again.')
                return False

            response = generate()
            response = response.strip()
            if not response:
                last_failure_category[0] = 'empty_completion'
                if receipt:
                    receipt.update(state='failed', error='Provider returned no result. No answer was admitted or saved for recovery.')
                return False

            if frozen:
                from turn_events import parse_session_response
                event = parse_session_response(response)
                event.update(brief_id=review_brief_id, event_id=dispatch_id,
                             **{key: envelope[key] for key in ('run_id', 'turn_id', 'attempt_id', 'input_revision')})
                # Unmanaged compatibility turns retain their prior bounded
                # live-bearer delivery; they make no durable outbox claim.
                for delivery_attempt in range(3):
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{server_port}/api/sessions/{envelope['session_id']}/event",
                        data=json.dumps(event).encode('utf-8'),
                        headers=_auth_headers(get_token(), include_json=True))
                    try:
                        with urllib.request.urlopen(request, timeout=10) as delivered:
                            accepted = json.load(delivered)
                        if accepted.get('status') != 'admitted':
                            raise ValueError('Session event was not admitted.')
                        return True
                    except urllib.error.HTTPError as exc:
                        if exc.code == 409:
                            prior = json.loads(exc.read())
                            if prior.get('accepted_event_id') == dispatch_id:
                                return True
                        if exc.code < 500 or delivery_attempt == 2:
                            raise
                    except OSError:
                        if delivery_attempt == 2:
                            raise
                    time.sleep(.2)

            # Strip self-prefix if the model echoes its own name
            prefixes = [f"{my_name}: ", f"{my_name}:"]
            for prefix in prefixes:
                if response.startswith(prefix):
                    response = response[len(prefix):]
                    break

            send_message(response, channel=channel, job_id=job_id, dispatch_id=dispatch_id)
            print(f"  [{channel}] Responded ({len(response)} chars)")
            return True
        except InvocationCancelled as exc:
            last_cancelled[0] = True
            if not exc.local_ended:
                unresolved_dispatches.add(dispatch_id)
            if not shutdown.is_set():
                current = queue.claim()
                if current and current['state'] == 'cancelling':
                    queue.cancellation_receipt(dispatch_id, 'local_ended' if exc.local_ended else 'unresolved')
                elif not exc.local_ended:
                    queue.uncertain(dispatch_id)
            if receipt:
                receipt.update(state='ready' if exc.local_ended else 'action_required',
                               error=None if exc.local_ended else 'Local invocation termination is unresolved.')
            return False
        except Exception as exc:
            malformed = isinstance(exc, EventValidationError)
            last_failure_category[0] = ('malformed_session_response' if malformed else
                exc.category if isinstance(exc, _ManagedProviderFailure) else 'local_delivery_failure')
            status = getattr(exc, 'http_status', None)
            if isinstance(exc, _ManagedProviderFailure) and type(status) is int and 100 <= status <= 599:
                last_failure_category[0] = 'http_error'
                last_failure_http_status[0] = status
            if receipt:
                if not isinstance(exc, _ManagedProviderFailure):
                    blocked_saved = saved_result[0] and isinstance(exc, urllib.error.HTTPError) and exc.code < 500
                    receipt.update(state='failed', error=(
                        'Session response was not valid final/question JSON; no event was admitted.' if malformed else
                        'Saved answer cannot be delivered for this turn; retained for audit.' if blocked_saved else
                        'Answer saved locally; check delivery status before generating again.' if saved_result[0] else
                        'Local event or chat delivery needs attention. Check the queue and session before retrying.'),
                        recoverable_result=False if blocked_saved or not saved_result[0] else None)
                print('  Managed API turn failed; see pre-flight diagnostics.')
            else:
                print(f'  API turn failed ({last_failure_category[0]}); no successful delivery was claimed.')
            return False
        finally:
            set_working(False)

    # Durable ownership is claimed before a provider call; release is retried
    # independently so an acknowledgement loss never regenerates the answer.
    from queue_client import QueueClient
    queue = QueueClient(server_port, get_token)
    processed_dispatch = None
    processed_ok = False
    if receipt:
        receipt.update(state='ready', adapter_connected=True, name=get_name())

    print(f"\n  === {agent_cfg.get('label', agent)} API Wrapper ===")
    print(f"  Model endpoint: {base_url}/chat/completions")
    if model:
        print(f"  Model: {model}")
    print(f"  @{name} mentions trigger model calls")
    print(f"  Ctrl+C to stop\n")

    try:
        while not shutdown.is_set():
            try:
                record = queue.claim()
                if record:
                    entry = record['envelope']
                    dispatch_id = entry['dispatch_id']
                    if dispatch_id in unresolved_dispatches and record['state'] != 'cancelling':
                        queue.uncertain(dispatch_id)
                        time.sleep(.2)
                        continue
                    if record['state'] == 'cancelling':
                        # Prior unproven cleanup remains unresolved; absence
                        # of a current call does not prove that child ended.
                        queue.cancellation_receipt(dispatch_id, 'unresolved' if dispatch_id in unresolved_dispatches else 'local_ended')
                        time.sleep(.2)
                        continue
                    if dispatch_id != processed_dispatch:
                        queue.acknowledge(dispatch_id)
                        processed_ok = handle_trigger(channel=entry.get('channel', 'general'),
                            review_brief_id=entry.get('review_brief_id'),
                            frozen='review_brief_id' in entry, prompt=entry.get('prompt', ''), job_id=entry.get('job_id') or None, dispatch_id=dispatch_id)
                        processed_dispatch = dispatch_id
                    if not last_cancelled[0]:
                        queue.release(dispatch_id, failed=not processed_ok, error_category=last_failure_category[0],
                                      http_status=last_failure_http_status[0])
            except Exception as exc:
                print(f'  Queue delivery held ({type(exc).__name__}); dispatch retained without model replay.')

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Shutting down...")
    finally:
        shutdown.set()
        if receipt:
            receipt.update(state='stopped', adapter_connected=False)
        try:
            n = get_name()
            t = get_token()
            req = urllib.request.Request(
                f"http://127.0.0.1:{server_port}/api/deregister/{n}",
                method="POST",
                data=b"",
                headers=_auth_headers(t),
            )
            urllib.request.urlopen(req, timeout=5)
            print(f"  Deregistered {n}")
        except Exception:
            pass

    print("  Wrapper stopped.")


if __name__ == "__main__":
    main()
