"""Isolated local integration check. No agents/providers; --serve keeps the page open until Enter."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import launcher
from config_loader import load_config


def main():
    scratch = ROOT / '.audit-tmp'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='preflight integration ', dir=scratch) as temporary:
        holders = [socket.socket() for _ in range(3)]
        for holder in holders:
            holder.bind(('127.0.0.1', 0))
        ports = [holder.getsockname()[1] for holder in holders]
        for holder in holders:
            holder.close()
        overrides = dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports)))
        overrides.update(AGENTCHATTR_DATA_DIR=str(Path(temporary) / 'data'),
                         AGENTCHATTR_UPLOAD_DIR=str(Path(temporary) / 'uploads'))
        children = []
        original_spawn = launcher.spawn_server
        def record_child(*args):
            child = original_spawn(*args)
            children.append(child)
            return child
        try:
            with patch.dict(os.environ, overrides), patch.object(launcher, 'spawn_server', side_effect=record_child):
                cfg = load_config(ROOT)
                target = launcher.ensure_server(ROOT, cfg, timeout=30)
                assert len(children) == 1, 'expected one owned server'
                # Real separate bootstrap processes contend/reuse through the kernel lock.
                command = [sys.executable, str(ROOT / 'launcher.py'), '--no-browser', '--timeout', '10']
                launches = [subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
                for process in launches:
                    out, err = process.communicate(timeout=15)
                    assert process.returncode == 0, err.decode(errors='replace')
                    assert target.encode() in out
                assert children[0].poll() is None
                with urllib.request.urlopen(target, timeout=3) as response:
                    html = response.read().decode('utf-8-sig')
                token = re.search(r'window.__SESSION_TOKEN__="([a-f0-9]+)"', html).group(1)
                api = target.removesuffix('/preflight') + '/api/preflight'
                try:
                    urllib.request.urlopen(api, timeout=3)
                    raise AssertionError('unauthenticated request accepted')
                except urllib.error.HTTPError as exc:
                    assert exc.code == 403
                request = urllib.request.Request(api, headers={'x-session-token': token})
                with urllib.request.urlopen(request, timeout=3) as response:
                    snapshot = json.load(response)
                assert snapshot['agents'] and all(not a['ready'] for a in snapshot['agents'])
                assert all(a['authentication'] == 'unknown' for a in snapshot['agents'])
                log = (ROOT / '.launcher/server.log').read_text(errors='replace')
                assert token not in log, 'session token leaked to supervised log'
                print(json.dumps({'result': 'PASS', 'url': target, 'owned_servers': len(children),
                                  'separate_relaunches': 2, 'agents_checked': len(snapshot['agents']),
                                  'authentication_enforced': True, 'session_token_logged': False}), flush=True)
                if '--serve' in sys.argv:
                    input('Press Enter to stop the isolated test server: ')
        finally:
            for child in children:
                launcher.stop_owned_child(child)


if __name__ == '__main__':
    main()
