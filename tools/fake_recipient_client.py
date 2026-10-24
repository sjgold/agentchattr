"""Local hidden CLI fixture: real MCP early release, gated finals and manual release."""
import asyncio
import ctypes
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api_seats import atomic_json
from process_identity import capture_birth


async def call(settings, name, arguments):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'], headers=server.get('headers'),
                                    timeout=12, sse_read_timeout=12) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            assert not result.isError, 'MCP protocol error'
            return ''.join(item.text for item in result.content if item.type == 'text')


def main():
    directory = Path(os.environ['RECIPIENT_RECORDS'])
    settings = json.loads(Path(os.environ['RECIPIENT_SETTINGS']).read_text(encoding='utf-8'))
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetConsoleWindow.restype = ctypes.c_void_p
    window = kernel.GetConsoleWindow()
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.IsWindowVisible.argtypes = [ctypes.c_void_p]
    record = {'birth': capture_birth(), 'console_present': bool(window),
              'console_visible': bool(user.IsWindowVisible(window)) if window else False, 'turns': []}
    path = directory / ('client-' + str(os.getpid()) + '.json')
    lock, pending = threading.Lock(), queue.Queue()

    def save():
        atomic_json(path, record)

    def gate(index):
        target = directory / ('submit-' + str(os.getpid()) + '-' + str(index))
        deadline = time.monotonic() + 900
        while not target.exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('Bounded fake client gate expired')
            time.sleep(.05)

    def work():
        while True:
            index, prompt = pending.get()
            try:
                dispatch = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                match = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt)
                entry = {'dispatch_id': dispatch, 'kind': 'review' if match else 'manual'}
                if match:
                    brief = match.group(1)
                    envelope = json.loads(asyncio.run(call(settings, 'chat_review_brief', {'brief_id': brief})))
                    entry['envelope'] = envelope
                    # Real early release proves transport delivery, never logical completion.
                    entry['release_reply'] = json.loads(asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch})))
                    entry['release_received_at'] = time.time()
                    peer = os.environ['RECIPIENT_PEER_NAME_FILE']
                    peer_name = Path(peer).read_text(encoding='utf-8')
                    entry['agent_chat_reply'] = asyncio.run(call(settings, 'chat_send', {
                        'sender': Path(os.environ['RECIPIENT_CLI_NAME_FILE']).read_text(encoding='utf-8'),
                        'message': '@' + peer_name + ' Review status only, do not schedule work.',
                        'channel': 'order-run', 'dispatch_id': dispatch, 'choices': []})) if index == 0 else None
                    with lock:
                        record['turns'][index].update(entry)
                        save()
                    gate(index)
                    entry['final_reply'] = json.loads(asyncio.run(call(settings, 'chat_session_event', {
                        'brief_id': brief, 'kind': 'final', 'content': 'ACTUAL_RECIPIENT_FINAL_' + str(index)})))
                    entry['final_received_at'] = time.time()
                else:
                    entry['release_reply'] = json.loads(asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch})))
                with lock:
                    record['turns'][index].update(entry)
                    save()
            except Exception as exc:
                with lock:
                    record['turns'][index]['error_type'] = type(exc).__name__
                    save()

    with lock:
        save()
    threading.Thread(target=work, daemon=True).start()
    for prompt in sys.stdin:
        with lock:
            index = len(record['turns'])
            record['turns'].append({'prompt': prompt.rstrip('\r\n'), 'received_at': time.time()})
            save()
        pending.put((index, prompt))


if __name__ == '__main__':
    main()
