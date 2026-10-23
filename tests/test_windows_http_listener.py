"""Windows HTTP listener survives peers resetting before sending a request."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

from launcher import stop_owned_child
import run


@unittest.skipUnless(sys.platform == 'win32', 'Windows accept-loop regression')
class WindowsHTTPListenerTests(unittest.TestCase):
    def test_main_http_loop_survives_aborted_connections_and_remains_responsive(self):
        run.http_event_loop()  # Exercise the production selector configuration.
        scratch = Path('.audit-tmp')
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            code = f'''import asyncio,uvicorn,run
from fastapi import FastAPI
app=FastAPI()
@app.get('/health')
async def health():
    return {{'selector':isinstance(asyncio.get_running_loop(),asyncio.SelectorEventLoop)}}
@app.get('/shutdown')
async def shutdown():
    server.should_exit=True
    return {{'stopping':True}}
server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port={port},loop=run.http_event_loop(),log_level='warning'))
server.run()
'''
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def health():
                with opener.open(f'http://127.0.0.1:{port}/health', timeout=2) as response:
                    return json.load(response)
            log = Path(temporary) / 'server.log'
            with log.open('wb') as output:
                process = subprocess.Popen([sys.executable, '-u', '-c', code],
                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                ready = None
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        ready = health()
                        break
                    except OSError:
                        time.sleep(.02)
                self.assertEqual(ready, {'selector': True}, log.read_text(encoding='utf-8'))
                def reset(_):
                    with socket.create_connection(('127.0.0.1', port), timeout=2) as connection:
                        connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('HH', 1, 0))
                    return 1
                total = 0
                with ThreadPoolExecutor(max_workers=8) as clients:
                    for _ in range(4):
                        total += sum(clients.map(reset, range(32)))
                        self.assertEqual(health(), {'selector': True})
                self.assertEqual(total, 128)
                self.assertIsNone(process.poll())
                self.assertNotIn('Accept failed on a socket', log.read_text(encoding='utf-8'))
            finally:
                try:
                    with opener.open(f'http://127.0.0.1:{port}/shutdown', timeout=2):
                        pass
                    process.wait(timeout=5)
                finally:
                    stop_owned_child(process)
            self.assertIsNotNone(process.poll())
