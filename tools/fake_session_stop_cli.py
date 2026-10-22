"""Record real console input continuously; emit controlled late MCP output."""
import asyncio
import json
import os
from pathlib import Path
import queue
import re
import threading
import time


async def tool(settings, name, arguments):
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
    root = Path(os.environ['TICKET10_RECORDS'])
    settings = json.loads(Path(os.environ['TICKET10_FAKE_SETTINGS']).read_text('utf-8'))
    record = {'prompts': [], 'settings_path': os.environ['TICKET10_FAKE_SETTINGS']}
    path = root / 'cli-stop.json'
    lock = threading.Lock()
    pending = queue.Queue()

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')
        temporary.replace(path)

    def worker():
        while True:
            prompt = pending.get()
            try:
                brief_id = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt).group(1)
                dispatch_id = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                envelope = json.loads(asyncio.run(tool(settings, 'chat_review_brief', {'brief_id': brief_id})))
                with lock:
                    record.update(envelope=envelope, dispatch_id=dispatch_id)
                    save()
                deadline = time.monotonic() + 120
                while not (root / 'emit-late').exists():
                    if time.monotonic() > deadline:
                        raise TimeoutError('late-output fixture gate')
                    time.sleep(.05)
                control = json.loads((root / 'control.json').read_text('utf-8'))
                mention = '@' + control['peer_name']
                typed = 'CLI-LATE-TYPED café ' + mention
                tagged = 'CLI-LATE-TAGGED café ' + mention
                untagged = 'CLI-LATE-UNTAGGED café ' + mention
                responses = {'typed': asyncio.run(tool(settings, 'chat_session_event',
                    {'brief_id': brief_id, 'kind': 'final', 'content': typed})),
                    'tagged': asyncio.run(tool(settings, 'chat_send', {'sender': envelope['expected_agent'],
                        'message': tagged, 'choices': [], 'channel': envelope['channel'], 'dispatch_id': dispatch_id})),
                    'untagged': asyncio.run(tool(settings, 'chat_send', {'sender': envelope['expected_agent'],
                        'message': untagged, 'choices': [], 'channel': envelope['channel']}))}
                with lock:
                    record.update(late_content={'typed': typed, 'tagged': tagged, 'untagged': untagged}, responses=responses)
                    save()
                # No cooperative release or fictitious cancellation support.
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
        pending.put(prompt)


if __name__ == '__main__':
    main()
