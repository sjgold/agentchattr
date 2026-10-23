"""Dedicated local Windows console fixture for selected CLI message recovery."""
import argparse
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


async def call(settings, tool, arguments):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'], headers=server.get('headers'),
                                     timeout=12, sse_read_timeout=12) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
            assert not result.isError, 'MCP protocol error'
            return ''.join(item.text for item in result.content if item.type == 'text')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model')
    parser.add_argument('--reasoning')
    args, _ = parser.parse_known_args()
    directory = Path(os.environ['CLI_RESULT_RECORDS'])
    settings = json.loads(Path(os.environ['CLI_RESULT_SETTINGS']).read_text('utf-8'))
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetConsoleWindow.restype = ctypes.c_void_p
    window = kernel.GetConsoleWindow()
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.IsWindowVisible.argtypes = [ctypes.c_void_p]
    record = {'birth': capture_birth(), 'console_present': bool(window),
              'console_visible': bool(user.IsWindowVisible(window)) if window else False,
              'argv': sys.argv[1:], 'cwd': str(Path.cwd()), 'model': args.model,
              'reasoning': args.reasoning, 'turns': []}
    path = directory / ('client-' + str(os.getpid()) + '.json')
    lock, pending = threading.Lock(), queue.Queue()

    def save():
        atomic_json(path, record)

    def gate(name):
        deadline = time.monotonic() + 900  # Includes bounded600s browser inspection.
        while not (directory / name).exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('Bounded CLI result fixture gate expired')
            time.sleep(.05)

    def work():
        while True:
            index, prompt = pending.get()
            try:
                brief_id = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt).group(1)
                dispatch_id = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                envelope = json.loads(asyncio.run(call(settings, 'chat_review_brief', {'brief_id': brief_id})))
                with lock:
                    record['turns'][index].update(envelope=envelope, dispatch_id=dispatch_id)
                    save()
                gate('post-' + str(os.getpid()))
                control = json.loads((directory / 'control.json').read_text('utf-8'))
                arguments = {'sender': envelope['expected_agent'], 'message': control['text'],
                             'channel': control['channel'], 'choices': []}
                if control['tagged']:
                    arguments['dispatch_id'] = dispatch_id
                if control.get('emit_chat', True):
                    reply = asyncio.run(call(settings, 'chat_send', arguments))
                    match = re.fullmatch(r'Sent \(id=(\d+)\)', reply)
                    assert match, 'Ordinary MCP chat was not accepted'
                    with lock:
                        record['turns'][index].update(message_id=int(match.group(1)), chat_reply=reply)
                        save()
                else:
                    with lock:
                        record['turns'][index]['chat_skipped'] = True
                        save()
                gate('late-' + str(os.getpid()))
                reply = json.loads(asyncio.run(call(settings, 'chat_session_event',
                    {'brief_id': brief_id, 'kind': 'final', 'content': 'ACTUAL_REPLACEMENT_LATE_FINAL'})))
                with lock:
                    record['turns'][index]['late_result'] = reply
                    save()
                # Rejected content is never interpreted as a transport release.
                gate('release-' + str(os.getpid()))
                reply = asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch_id}))
                with lock:
                    record['turns'][index]['release_reply'] = reply
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
