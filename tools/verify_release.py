"""Build and boot an extracted release using the existing test interpreter."""
import json
from pathlib import Path
import socket
import sys
import tempfile
import time
import urllib.request
import zipfile
from unittest.mock import patch
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import build_release
import launcher
from config_loader import load_config


def main():
    archive = build_release.build()
    with tempfile.TemporaryDirectory(prefix='release-check-') as temporary:
        with zipfile.ZipFile(archive) as package:
            names = package.namelist()
            assert not any('/data/' in name or '/.launcher/' in name or 'config.local.toml' == name.split('/')[-1] for name in names)
            package.extractall(temporary)
        root = Path(temporary) / build_release.OUT_NAME
        assert not list(root.glob('*.py'))
        assert {p.name for p in (root / 'src').glob('*.py')} == {p.name for p in (ROOT / 'src').glob('*.py')}
        sockets = [socket.socket() for _ in range(3)]
        for item in sockets:
            item.bind(('127.0.0.1', 0))
        ports = [item.getsockname()[1] for item in sockets]
        for item in sockets:
            item.close()
        env = dict(zip(('AGENTCHATTR_PORT', 'AGENTCHATTR_MCP_HTTP_PORT', 'AGENTCHATTR_MCP_SSE_PORT'), map(str, ports)))
        env.update(AGENTCHATTR_DATA_DIR=str(root / 'data'), AGENTCHATTR_UPLOAD_DIR=str(root / 'uploads'))
        with patch.dict(os.environ, env):
            cfg = load_config(root)
            process = launcher.spawn_server(root, sys.executable, cfg)
            try:
                url = launcher.service_url(cfg)
                identity = launcher.instance_identity(root, cfg)
                deadline = time.monotonic() + 30
                while launcher.probe_health(url, identity) != 'matching':
                    assert process.poll() is None, 'Extracted server exited'
                    assert time.monotonic() < deadline, 'Extracted server startup timed out'
                    time.sleep(0.1)
                with urllib.request.urlopen(url + '/preflight', timeout=5) as response:
                    assert response.status == 200
                print(json.dumps({'release': 'PASS', 'source_modules': len(list((root / 'src').glob('*.py'))), 'provider_calls': 0}))
            finally:
                launcher.stop_owned_child(process)


if __name__ == '__main__':
    main()
