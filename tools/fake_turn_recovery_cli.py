"""Actual generic console fixture for same-source retry, no clean-context claim."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time

async def call(settings, name, arguments):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'], headers=server.get('headers'),
                                     timeout=10, sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            assert not result.isError, 'MCP protocol error'
            return ''.join(item.text for item in result.content if item.type == 'text')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model')
    parser.add_argument('--reasoning')
    args, _ = parser.parse_known_args()
    root = Path(os.environ['TICKET12_RECORDS'])
    settings = json.loads(Path(os.environ['TICKET12_FAKE_SETTINGS']).read_text('utf-8'))
    record = {'pid': os.getpid(), 'model': args.model, 'reasoning': args.reasoning,
              'argv': sys.argv[1:], 'cwd': str(Path.cwd()), 'prompts': []}
    path = root / ('client-' + str(os.getpid()) + '.json')
    lock, pending = threading.Lock(), queue.Queue()

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')
        temporary.replace(path)

    def marker(name):
        deadline = time.monotonic() + 900
        while not (root / name).exists():
            if time.monotonic() > deadline:
                raise TimeoutError('fixture gate ' + name)
            time.sleep(.05)

    def worker():
        while True:
            prompt = pending.get()
            try:
                brief_id = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt).group(1)
                dispatch_id = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                envelope = json.loads(asyncio.run(call(settings, 'chat_review_brief', {'brief_id': brief_id})))
                control = json.loads((root / 'control.json').read_text('utf-8'))
                with lock:
                    record.update(envelope=envelope, dispatch_id=dispatch_id)
                    save()
                if os.getpid() == control['old_pid']:
                    marker('old-may-submit')
                else:
                    marker('new-may-submit')
                response = asyncio.run(call(settings, 'chat_session_event',
                    {'brief_id': brief_id, 'kind': 'final', 'content': 'CLI_RETRY_FINAL exact same-source result.'}))
                with lock:
                    record['admission'] = json.loads(response)
                    save()
                marker('new-may-release')
                response = asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch_id}))
                with lock:
                    record['release'] = response
                    save()
            except Exception as exc:
                with lock:
                    record['error'] = type(exc).__name__ + ': ' + str(exc)
                    save()

    with lock:
        save()
    threading.Thread(target=worker, daemon=True).start()
    for prompt in sys.stdin:
        with lock:
            record['prompts'].append(prompt.rstrip('\r\n'))
            save()
        pending.put(prompt)


if __name__ == '__main__':
    main()
