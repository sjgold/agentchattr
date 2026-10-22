"""Cooperative transport release for existing isolated fake CLI fixtures."""
import re
import json


async def release_dispatch(settings, prompt):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    match = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt)
    if not match:
        return
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'],
                                    headers=server.get('headers'), timeout=10,
                                    sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool('chat_queue_release', {'dispatch_id': match.group(1)})
            assert not result.isError
            assert any('released' in item.text for item in result.content if item.type == 'text')


async def submit_final(settings, brief_id, content):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    async with streamablehttp_client(server.get('url') or server['httpUrl'],
                                    headers=server.get('headers'), timeout=10,
                                    sse_read_timeout=10) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool('chat_session_event',
                {'brief_id': brief_id, 'kind': 'final', 'content': content})
            value = json.loads(''.join(item.text for item in result.content if item.type == 'text'))
            assert value['status'] == 'admitted'
