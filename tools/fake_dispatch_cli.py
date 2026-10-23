"""Fake CLI records real console input and cooperatively releases via MCP."""
import asyncio
import faulthandler
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api_seats import atomic_json


async def release(settings, dispatch_id, phase):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    phase('transport_entering')
    async with streamablehttp_client(server.get('url') or server['httpUrl'],
                                     headers=server.get('headers'), timeout=10,
                                     sse_read_timeout=10) as (read, write, _):
        phase('transport_entered')
        phase('session_entering')
        async with ClientSession(read, write) as session:
            phase('session_entered')
            phase('initialize_entering')
            await session.initialize()
            phase('initialize_returned')
            phase('call_entering')
            result = await session.call_tool('chat_queue_release', {'dispatch_id': dispatch_id})
            phase('call_returned')
            assert not result.isError, 'MCP release returned a tool error'
            reply = ''.join(item.text for item in result.content if item.type == 'text')
            phase('session_exiting')
        phase('session_exited')
        phase('transport_exiting')
    phase('transport_exited')
    return reply


def main():
    directory = Path(os.environ['TICKET7_RECORDS'])
    settings = json.loads(Path(os.environ['TICKET7_FAKE_SETTINGS']).read_text('utf-8'))
    record = {'prompts': [], 'released': [], 'phases': [],
              'settings_path': os.environ['TICKET7_FAKE_SETTINGS']}
    path = directory / 'cli-record.json'
    lock = threading.Lock()
    work = queue.Queue()
    # Earlier evidence showed a released ledger record without the client
    # returning. Capture every thread before the unchanged verifier deadline.
    stack_output = (directory / 'cli-thread-stacks.log').open('a', encoding='utf-8')

    def save():
        atomic_json(path, record)

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
                dispatch_id = match.group(1)
                def phase(name):
                    with lock:
                        record['phases'].append({'dispatch_id': dispatch_id,
                            'phase': name, 'at': time.time(), 'thread_id': threading.get_ident()})
                        save()
                phase('asyncio_run_entering')
                faulthandler.dump_traceback_later(20, file=stack_output)
                try:
                    reply = asyncio.run(release(settings, dispatch_id, phase))
                    phase('asyncio_run_returned')
                finally:
                    faulthandler.cancel_dump_traceback_later()
                with lock:
                    record['released'].append({'dispatch_id': match.group(1), 'reply': reply})
                    save()
            except Exception as exc:
                with (directory / 'cli-exceptions.log').open('a', encoding='utf-8') as diagnostic:
                    diagnostic.write(''.join(traceback.format_exception(exc)))
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
