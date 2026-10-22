"""Local fake CLI: receive actual console instructions and retrieve an MCP brief."""
import asyncio
import json
import os
from pathlib import Path
import re
import sys
import urllib.request


async def fetch_brief(settings, brief_id):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'], headers=server.get('headers'),
                                     timeout=10, sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool('chat_review_brief', {'brief_id': brief_id})
            assert not result.isError, 'MCP brief tool returned an error'
            return json.loads(''.join(item.text for item in result.content if item.type == 'text'))


def main():
    directory = Path(os.environ['TICKET6_RECORDS'])
    settings = json.loads(Path(os.environ['TICKET6_FAKE_SETTINGS']).read_text('utf-8'))
    record = {'argv': sys.argv[1:], 'prompts': [], 'transport': 'mcp-streamable-http',
              'settings_path': os.environ['TICKET6_FAKE_SETTINGS']}
    path = directory / 'cli-receipt.json'

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')
        temporary.replace(path)

    save()
    while True:
        try:
            prompt = input()
        except EOFError:
            return
        record['prompts'].append(prompt)
        match = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt)
        if match:
            try:
                envelope = asyncio.run(fetch_brief(settings, match.group(1)))
                record['envelope'] = envelope
                request = urllib.request.Request(
                    os.environ['TICKET6_APP_URL'] + '/api/review-briefs/' + match.group(1),
                    headers=settings['mcpServers']['agentchattr']['headers'])
                with urllib.request.urlopen(request, timeout=10) as response:
                    record['http_envelope'] = json.load(response)
                from queue_fixture import release_dispatch
                asyncio.run(release_dispatch(settings, prompt))
            except Exception as exc:
                record['error'] = type(exc).__name__ + ': ' + str(exc)
        save()


if __name__ == '__main__':
    main()
