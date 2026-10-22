"""Fake native CLI: prove fresh boot reads and scoped typed review completion."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import queue
import re
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


def reads(settings, control):
    queries = [('read', 'chat_read', {'sender': '', 'limit': 200, 'channel': control['channel']}),
               ('resync', 'chat_resync', {'sender': '', 'limit': 200, 'channel': control['channel']}),
               ('job', 'chat_read', {'sender': '', 'job_id': control['job_id'], 'limit': 200}),
               ('summary', 'chat_summary', {'action': 'read', 'sender': '', 'channel': control['channel']})]
    result = {}
    for label, name, arguments in queries:
        text = asyncio.run(call(settings, name, arguments))
        # Existing MCP message serialization uses the empty string for an empty
        # list. Only that exact wire value means no messages; errors still fail.
        result[label] = [] if text == '' else json.loads(text)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context-id')
    parser.add_argument('--model')
    parser.add_argument('--reasoning')
    args, _ = parser.parse_known_args()
    root = Path(os.environ['TICKET11_RECORDS'])
    settings = json.loads(Path(os.environ['TICKET11_FAKE_SETTINGS']).read_text('utf-8'))
    control = json.loads((root / 'control.json').read_text('utf-8'))
    path = root / ('client-' + (args.context_id or 'original') + '.json')
    import sys
    record = {'pid': os.getpid(), 'context_id': args.context_id, 'model': args.model,
              'reasoning': args.reasoning, 'argv': sys.argv[1:], 'cwd': str(Path.cwd()),
              'settings_path': os.environ['TICKET11_FAKE_SETTINGS'], 'prompts': []}
    lock, pending = threading.Lock(), queue.Queue()

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')
        temporary.replace(path)

    def marker(name):
        deadline = time.monotonic() + 180
        while not (root / name).exists():
            if time.monotonic() > deadline:
                raise TimeoutError('fixture marker ' + name)
            time.sleep(.05)

    try:
        # These are the fresh client's first MCP data reads, before any stdin
        # instruction or activation. No old context may enter the process.
        if args.context_id:
            record['first_reads'] = reads(settings, control)
        with lock:
            save()
    except Exception as exc:
        record['error'] = type(exc).__name__ + ': ' + str(exc)
        save()
        return

    def worker():
        while True:
            prompt = pending.get()
            try:
                brief_id = re.search(r"chat_review_brief\(brief_id='([a-f0-9]{32})'\)", prompt).group(1)
                dispatch_id = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                envelope = json.loads(asyncio.run(call(settings, 'chat_review_brief', {'brief_id': brief_id})))
                with lock:
                    record.update(envelope=envelope, dispatch_id=dispatch_id)
                    save()
                if not args.context_id:
                    marker('emit-old-late')
                    reply = asyncio.run(call(settings, 'chat_session_event',
                        {'brief_id': brief_id, 'kind': 'final', 'content': 'OLD_CLI_LATE_RESULT must stay abandoned.'}))
                    with lock:
                        record['late_response'] = json.loads(reply)
                        save()
                    # Old native context deliberately never releases; only the
                    # explicitly confirmed owned termination may replace it.
                    continue
                with lock:
                    record['turn_reads'] = reads(settings, control)
                    save()
                marker('submit-new')
                reply = asyncio.run(call(settings, 'chat_session_event',
                    {'brief_id': brief_id, 'kind': 'final', 'content': 'NEW_CLI_RESULT corrected café evidence.'}))
                with lock:
                    record['admission'] = json.loads(reply)
                    save()
                marker('release-new')
                reply = asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch_id}))
                with lock:
                    record['release_response'] = reply
                    save()
            except Exception as exc:
                with lock:
                    record['error'] = type(exc).__name__ + ': ' + str(exc)
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
