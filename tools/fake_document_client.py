"""Local hidden CLI: gate BEFORE real MCP brief read, then authenticated final/release."""
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
    # A full 512KiB source plus JSON/MCP framing is intentionally not truncated.
    async with streamablehttp_client(server.get('url') or server['httpUrl'], headers=server.get('headers'),
                                    timeout=75, sse_read_timeout=75) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            assert not result.isError, 'MCP protocol failure'
            return ''.join(item.text for item in result.content if item.type == 'text')


def main():
    directory = Path(os.environ['DOCUMENT_RECORDS'])
    settings = json.loads(Path(os.environ['DOCUMENT_SETTINGS']).read_text(encoding='utf-8'))
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
        deadline = time.monotonic() + 900
        target = directory / ('read-' + str(os.getpid()) + '-' + str(index))
        while not target.exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('Bounded document fixture gate expired')
            time.sleep(.05)

    def work():
        while True:
            index, prompt = pending.get()
            try:
                brief = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt).group(1)
                dispatch = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                with lock:
                    record['turns'][index].update(brief_id=brief, dispatch_id=dispatch, held_before_brief=True)
                    save()
                gate(index)
                envelope = json.loads(asyncio.run(call(settings, 'chat_review_brief', {'brief_id': brief})))
                with lock:
                    record['turns'][index].update(envelope=envelope, brief_received_at=time.time())
                    save()
                response = json.loads(asyncio.run(call(settings, 'chat_session_event', {
                    'brief_id': brief, 'kind': 'final', 'content': 'DOCUMENT_CLI_FINAL'})))
                with lock:
                    record['turns'][index].update(final_response=response, final_received_at=time.time())
                    save()
                assert response.get('status') == 'admitted', 'Real typed CLI final was not admitted'
                released = json.loads(asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch})))
                with lock:
                    record['turns'][index]['release_reply'] = released
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
