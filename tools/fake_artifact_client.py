"""Owned fixture CLI, real MCP artifact tools. Importing constructs no resources."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit


def binding(settings, ports):
    server = settings['mcpServers']['agentchattr']
    address = server.get('url') or server.get('httpUrl')
    parsed = urlsplit(address)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.port not in ports
            or parsed.path != '/mcp' or parsed.query or parsed.fragment or parsed.username):
        raise ValueError('Fixture MCP binding refused')
    headers = server.get('headers', {})
    if not isinstance(headers, dict) or not headers:
        raise ValueError('Fixture MCP identity headers absent')
    return address, headers


def prompt_ids(prompt):
    brief = re.search(r"chat_artifact_brief\(brief_id='([a-f0-9]{32})'\)", prompt)
    dispatch = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt)
    if not brief or not dispatch:
        raise ValueError('Assigned artifact prompt required')
    return brief.group(1), dispatch.group(1)


async def call(settings, ports, tool, arguments):
    if tool not in ('chat_artifact_brief', 'chat_artifact_submit', 'chat_queue_release'):
        raise ValueError('Only artifact fixture tools allowed')
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    address, headers = binding(settings, ports)
    async with streamablehttp_client(address, headers=headers, timeout=15, sse_read_timeout=15) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await asyncio.wait_for(session.call_tool(tool, arguments), 20)
            if result.isError:
                raise ValueError('Real MCP tool refused fixture operation')
            # Persist hashes only. Brief results can contain launch credentials.
            text = ''.join(item.text for item in result.content if item.type == 'text')
            return text


def validate_reply(tool, text, brief_id, dispatch_id, markdown):
    value = json.loads(text)
    if not isinstance(value, dict) or 'error' in value:
        raise ValueError('Real MCP artifact operation refused')
    if tool == 'chat_artifact_brief':
        if (set(value) != {'brief', 'packet', 'parent'} or value['brief'].get('brief_id') != brief_id
                or value['brief'].get('dispatch_id') != dispatch_id):
            raise ValueError('Assigned brief mismatch')
    elif tool == 'chat_artifact_submit':
        if (value.get('status') != 'admitted' or value.get('event_id') != dispatch_id
                or value.get('sha256') != hashlib.sha256(markdown.encode('utf-8')).hexdigest()
                or any(not re.fullmatch('[a-f0-9]{32}', value.get(key, '')) for key in ('request_id', 'version_id'))):
            raise ValueError('Admitted ACK required before transport release')
    elif tool == 'chat_queue_release':
        if value != {'dispatch_id': dispatch_id, 'status': 'released'}:
            raise ValueError('Transport release not confirmed')
    else:
        raise ValueError('Unknown fixture tool')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.verify_artifact_ui import require_guard, CANNED, read_json, write_json
    try: root = require_guard()
    except RuntimeError: raise SystemExit(91) from None
    from process_identity import capture_birth
    birth = capture_birth()
    record = {'birth': birth, 'tools': [], 'ended': False}
    if sys.platform == 'win32':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetConsoleWindow.restype = ctypes.c_void_p
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.IsWindowVisible.argtypes = [ctypes.c_void_p]
        window = kernel.GetConsoleWindow()
        record.update(console_present=bool(window),
            console_visible=bool(user.IsWindowVisible(window)) if window else False)
    path = root / 'records' / ('client-' + str(os.getpid()) + '.json')
    write_json(path, record)
    settings_path = Path(os.environ['ARTIFACT_FIXTURE_MCP']).resolve()
    if not settings_path.is_relative_to(root):
        raise ValueError('Only owned MCP settings allowed')
    settings = read_json(settings_path)
    ports = read_json(root / 'private.json')['ports']
    binding(settings, ports)
    try:
        for prompt in sys.stdin:
            brief, dispatch = prompt_ids(prompt)
            for tool, args in [('chat_artifact_brief', {'brief_id': brief}),
                               ('chat_artifact_submit', {'brief_id': brief, 'markdown': CANNED}),
                               ('chat_queue_release', {'dispatch_id': dispatch})]:
                if tool == 'chat_artifact_submit':
                    deadline = time.monotonic() + 100
                    while not (root / 'records' / 'cli-release').exists():
                        if time.monotonic() > deadline:
                            raise TimeoutError('CLI before-submit gate')
                        time.sleep(.05)
                reply = asyncio.run(call(settings, ports, tool, args))
                digest = validate_reply(tool, reply, brief, dispatch, CANNED)
                record['tools'].append({'tool': tool, 'brief_id': brief, 'dispatch_id': dispatch, 'reply_sha256': digest})
                write_json(path, record)
    except Exception as error:
        record['error'] = type(error).__name__
        raise
    finally:
        record['ended'] = True
        write_json(path, record)


if __name__ == '__main__':
    main()
