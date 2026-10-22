"""Fake CLI records real console input and cooperatively releases via MCP."""
import asyncio
import json
import os
from pathlib import Path
import queue
import re
import threading
import time


async def release(settings, dispatch_id):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'],
                                     headers=server.get('headers'), timeout=10,
                                     sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool('chat_queue_release', {'dispatch_id': dispatch_id})
            assert not result.isError, 'MCP release returned a tool error'
            return ''.join(item.text for item in result.content if item.type == 'text')


def main():
    directory = Path(os.environ['TICKET7_RECORDS'])
    settings = json.loads(Path(os.environ['TICKET7_FAKE_SETTINGS']).read_text('utf-8'))
    record = {'prompts': [], 'released': [], 'settings_path': os.environ['TICKET7_FAKE_SETTINGS']}
    path = directory / 'cli-record.json'
    lock = threading.Lock()
    work = queue.Queue()

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')
        temporary.replace(path)

    def worker():
        while True:
            prompt = work.get()
            try:
                match = re.search(r"chat_queue_release\(dispatch_id=['\"]([a-f0-9]{32})['\"]\)", prompt)
                if not match:
                    raise AssertionError('Injected prompt lacks explicit dispatch release ID')
                if 'CLI-HOLD-UNTIL-FAILURE' in prompt:
                    # Deliberately noncompliant work for the owned-worker failure
                    # scenario. The input reader stays live to expose overlap.
                    while not (directory / 'release-failure').exists():
                        time.sleep(.05)
                if not record['released']:
                    deadline = time.monotonic() + 45
                    while not (directory / 'release-first').exists():
                        if time.monotonic() > deadline:
                            raise TimeoutError('fixture release sentinel deadline')
                        time.sleep(.05)
                reply = asyncio.run(release(settings, match.group(1)))
                with lock:
                    record['released'].append({'dispatch_id': match.group(1), 'reply': reply})
                    save()
            except Exception as exc:
                with lock:
                    record['error'] = type(exc).__name__ + ': ' + str(exc)
                    save()

    with lock:
        save()
    threading.Thread(target=worker, daemon=True).start()
    while True:
        try:
            prompt = input()
        except EOFError:
            return
        with lock:
            record['prompts'].append(prompt)
            save()
        work.put(prompt)


if __name__ == '__main__':
    main()
