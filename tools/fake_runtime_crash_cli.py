"""Hidden local console fixture: exact MCP brief, gated typed result/release."""
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


async def tool(settings, name, arguments):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    config = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(config.get('url') or config['httpUrl'], headers=config.get('headers'),
                                     timeout=10, sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            assert not result.isError, 'MCP tool protocol failure'
            return ''.join(item.text for item in result.content if item.type == 'text')


def main():
    directory = Path(os.environ['CRASH_MATRIX_RECORDS'])
    settings = json.loads(Path(os.environ['CRASH_MATRIX_SETTINGS']).read_text('utf-8'))
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetConsoleWindow.restype = ctypes.c_void_p
    window = kernel.GetConsoleWindow()
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.IsWindowVisible.argtypes = [ctypes.c_void_p]
    record = {'birth': capture_birth(), 'console_present': bool(window),
              'console_visible': bool(user.IsWindowVisible(window)) if window else False, 'turns': []}
    path = directory / 'client.json'
    lock, pending = threading.Lock(), queue.Queue()

    def save():
        atomic_json(path, record)

    def gate(name):
        deadline = time.monotonic() + 180
        while not (directory / name).exists():
            if time.monotonic() > deadline:
                raise TimeoutError('bounded fixture gate expired')
            time.sleep(.05)

    def work():
        while True:
            index, prompt = pending.get()
            try:
                brief = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt).group(1)
                dispatch = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                envelope = json.loads(asyncio.run(tool(settings, 'chat_review_brief', {'brief_id': brief})))
                with lock:
                    record['turns'][index].update(envelope=envelope, dispatch_id=dispatch)
                    save()
                gate('submit-' + str(index))
                response = json.loads(asyncio.run(tool(settings, 'chat_session_event',
                    {'brief_id': brief, 'kind': 'final', 'content': 'CLI_CRASH_FINAL_' + str(index)})))
                with lock:
                    record['turns'][index]['admission'] = response
                    save()
                # Stop rejection does not imply transport release.
                if response.get('status') == 'admitted':
                    gate('release-' + str(index))
                    response = asyncio.run(tool(settings, 'chat_queue_release', {'dispatch_id': dispatch}))
                    with lock:
                        record['turns'][index]['release'] = response
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
            record['turns'].append({'prompt': prompt.rstrip('\r\n')})
            save()
        pending.put((index, prompt))


if __name__ == '__main__':
    main()
