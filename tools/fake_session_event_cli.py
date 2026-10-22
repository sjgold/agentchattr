"""Fake CLI retrieves frozen context and submits a typed event through real MCP."""
import asyncio
import json
import os
from pathlib import Path
import re
import time


async def call(settings, name, arguments):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'],
                                     headers=server.get('headers'), timeout=10,
                                     sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            assert not result.isError, 'MCP protocol returned a tool error'
            return ''.join(item.text for item in result.content if item.type == 'text')


def main():
    root = Path(os.environ['TICKET8_RECORDS'])
    settings = json.loads(Path(os.environ['TICKET8_FAKE_SETTINGS']).read_text('utf-8'))
    path = root / 'cli-event.json'
    record = {'prompts': []}

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')
        temporary.replace(path)

    def wait_for_marker(name):
        deadline = time.monotonic() + 120
        while not (root / name).exists():
            if time.monotonic() > deadline:
                raise TimeoutError('fixture marker ' + name)
            time.sleep(.05)

    save()
    while True:
        try:
            prompt = input()
        except EOFError:
            return
        record['prompts'].append(prompt)
        try:
            brief_id = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt).group(1)
            dispatch_id = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
            assert 'chat_session_event' in prompt, 'CLI was not instructed to use typed completion'
            record['dispatch_id'] = dispatch_id
            record['envelope'] = json.loads(asyncio.run(call(settings, 'chat_review_brief', {'brief_id': brief_id})))
            save()
            wait_for_marker('submit-cli')
            arguments = {'brief_id': brief_id, 'kind': 'final', 'content': 'CLI accepted final, exact café.'}
            record['admission'] = json.loads(asyncio.run(call(settings, 'chat_session_event', arguments)))
            record['duplicate_response'] = asyncio.run(call(settings, 'chat_session_event', arguments))
            save()
            wait_for_marker('release-cli')
            record['release_response'] = asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch_id}))
            save()
        except Exception as exc:
            record['error'] = type(exc).__name__ + ': ' + str(exc)
            save()


if __name__ == '__main__':
    main()
