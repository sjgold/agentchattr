"""DRAFT local hidden CLI: genuine MCP calls, fixed controls, no model execution."""
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
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from tools.channel_guard import install_guard
install_guard('client')
from api_seats import atomic_json
from process_identity import capture_birth

CHANNELS = {'lifecycle-run', 'renamed-run', 'peer'}


async def _call(settings, tool, arguments):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    server = settings['mcpServers']['agentchattr']
    address = server.get('url') or server['httpUrl']
    assert urlsplit(address).hostname == '127.0.0.1', 'Fixture MCP must be loopback'
    async with streamablehttp_client(address, headers=server.get('headers'), timeout=15,
                                     sse_read_timeout=15) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
            assert not result.isError, 'MCP protocol refusal'
            return ''.join(item.text for item in result.content if item.type == 'text')


async def call(settings, tool, arguments):
    return await asyncio.wait_for(_call(settings, tool, arguments), timeout=15)


def main():
    birth = capture_birth()  # Capture self before accepting work or reading control.
    root = Path(os.environ['CHANNEL_FIXTURE_ROOT']).resolve()
    records = root / 'records'
    nonce = os.environ['CHANNEL_FIXTURE_NONCE']
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetConsoleWindow.restype = ctypes.c_void_p
    window = kernel.GetConsoleWindow()
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.IsWindowVisible.argtypes = [ctypes.c_void_p]
    record = {'birth': birth, 'console_present': bool(window),
              'console_visible': bool(user.IsWindowVisible(window)) if window else False,
              'turns': [], 'commands': [], 'ended': False}
    journal = records / ('client-' + str(birth['pid']) + '.json')
    atomic_json(journal, record)
    settings_path = Path(os.environ['CHANNEL_SETTINGS']).resolve()
    assert settings_path.is_relative_to(root), 'Only owned MCP settings may be read'
    settings = json.loads(settings_path.read_text(encoding='utf-8'))
    incoming, halt, lock = queue.Queue(), threading.Event(), threading.Lock()
    deadline = time.monotonic() + 350

    def binding():
        value = json.loads((records / 'binding.json').read_text(encoding='utf-8'))
        assert set(value) == {'name', 'identity_id', 'attempt', 'nonce'} and value['nonce'] == nonce
        assert re.fullmatch('[a-f0-9]{32}', value['attempt'])
        with lock:
            record['binding'] = value
            save()
        return value

    def save():
        atomic_json(journal, record)

    def read_stdin():
        for prompt in sys.stdin:
            incoming.put(prompt.rstrip('\r\n'))
        halt.set()

    def work():
        while not halt.is_set():
            try:
                prompt = incoming.get(timeout=.1)
            except queue.Empty:
                continue
            entry = {'prompt': prompt, 'received_at': time.time()}
            with lock:
                record['turns'].append(entry)
                save()
            try:
                dispatch = re.search(r"chat_queue_release\(dispatch_id='([a-f0-9]{32})'\)", prompt).group(1)
                channel = re.search(r'Dispatch channel: #([a-z0-9-]+)\.', prompt).group(1)
                assert channel in CHANNELS
                owner = binding()
                reply = asyncio.run(call(settings, 'chat_read', {'sender': owner['name'], 'channel': channel, 'limit': 50}))
                with lock:
                    entry.update(dispatch_id=dispatch, channel=channel, read_reply=reply,
                                 read_completed_at=time.time())
                    save()
                gate = records / ('release-' + dispatch + '.json')
                while not gate.exists() and not halt.is_set():
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Fixture gate deadline')
                    time.sleep(.05)
                if halt.is_set():
                    return
                value = json.loads(gate.read_text(encoding='utf-8'))
                assert value == {'dispatch_id': dispatch, 'nonce': nonce}
                reply = asyncio.run(call(settings, 'chat_queue_release', {'dispatch_id': dispatch}))
                with lock:
                    entry.update(release_reply=reply, released_at=time.time())
                    save()
            except Exception as error:
                with lock:
                    entry['error_type'] = type(error).__name__
                    save()

    threading.Thread(target=read_stdin, daemon=True).start()
    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    seen = set()
    while not halt.is_set():
        if time.monotonic() >= deadline:
            record['deadline_expired'] = True
            break
        for path in sorted((records / 'commands').glob('*.json')):
            if path.stem in seen:
                continue
            seen.add(path.stem)
            result = {'id': path.stem, 'at': time.time()}
            try:
                command = json.loads(path.read_text(encoding='utf-8'))
                assert set(command) == {'id', 'op', 'channel', 'nonce'}
                assert command['id'] == path.stem and re.fullmatch('[a-f0-9]{32}', path.stem)
                assert command['nonce'] == nonce and command['op'] in {'read', 'send_omitted', 'send_explicit', 'exit'}
                assert command['channel'] in CHANNELS
                result.update(op=command['op'], channel=command['channel'])
                if command['op'] == 'exit':
                    halt.set()
                    result['reply'] = 'cooperative_client_exit'
                else:
                    owner = binding()
                    arguments = {'sender': owner['name']}
                    if command['op'] == 'read':
                        arguments.update(channel=command['channel'], limit=50)
                        tool = 'chat_read'
                    else:
                        tool = 'chat_send'
                        arguments.update(message='CHANNEL_PROBE_' + command['id'], choices=[])
                        if command['op'] == 'send_explicit':
                            arguments['channel'] = command['channel']
                    result['reply'] = asyncio.run(call(settings, tool, arguments))
            except Exception as error:
                result['error_type'] = type(error).__name__
            with lock:
                record['commands'].append(result)
                save()
        halt.wait(.05)
    halt.set()
    worker.join(timeout=22)
    with lock:
        record.update(ended=True, work_thread_ended=not worker.is_alive())
        save()


if __name__ == '__main__':
    main()
