"""Standard-library bootstrap. --check is passive; --setup permits installation."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from config_loader import apply_cli_overrides, load_config

ROOT = Path(__file__).resolve().parent
PROTOCOL = 1


class LaunchError(Exception):
    pass


def instance_identity(root, config):
    server = config.get('server', {})
    data = (Path(root) / server.get('data_dir', './data')).resolve()
    effective = {'root': os.path.normcase(str(Path(root).resolve())),
                 'data': os.path.normcase(str(data)), 'port': server.get('port', 8300),
                 'host': server.get('host', '127.0.0.1'),
                 'uploads': os.path.normcase(str((Path(root) / config.get('images', {}).get('upload_dir', './uploads')).resolve())),
                 'mcp': config.get('mcp', {})}
    return hashlib.sha256(json.dumps(effective, sort_keys=True).encode()).hexdigest()


def service_url(config):
    server = config.get('server', {})
    host, port = server.get('host', '127.0.0.1'), server.get('port', 8300)
    if host not in ('127.0.0.1', 'localhost', '::1'):
        raise LaunchError('The shortcut supports loopback hosts only; use run.py for explicit network setup.')
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise LaunchError('server.port must be an integer between 1 and 65535.')
    return f'http://{"[::1]" if host == "::1" else host}:{port}'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe_health(url, identity, timeout=2):
    """An HTTP listener is not sufficient: require this installation/config."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(url + '/api/health', timeout=timeout) as response:
            data = json.loads(response.read(8193))
            if (response.status == 200 and isinstance(data, dict)
                    and data.get('app') == 'agentchattr' and data.get('protocol') == PROTOCOL
                    and data.get('identity') == identity and data.get('state') == 'ready'):
                return 'matching'
            return 'foreign'
    except (urllib.error.HTTPError, HTTPException, ValueError, UnicodeError):
        return 'foreign'
    except (urllib.error.URLError, OSError):
        # A listener that stalls or speaks a different protocol is a conflict.
        from urllib.parse import urlsplit
        address = urlsplit(url)
        try:
            with socket.create_connection((address.hostname, address.port), timeout=min(timeout, 0.2)):
                return 'foreign'
        except OSError:
            return 'absent'


@contextmanager
def startup_lock(path, deadline):
    """Kernel-held lock; crashes release it without stale-file deletion."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as lock:
        # Byte-range locks may extend beyond EOF on Windows; flock likewise
        # needs no file contents. Writing before locking races other holders.
        while True:
            try:
                lock.seek(0)
                if sys.platform == 'win32':
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise LaunchError('Another startup is busy; retry after it finishes.') from None
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            if sys.platform == 'win32':
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def environment_python(root, platform=None):
    platform = platform or sys.platform
    name = 'windows' if platform == 'win32' else 'macos' if platform == 'darwin' else 'linux'
    environment = Path(root) / f'.venv-{name}'
    return environment / ('Scripts/python.exe' if platform == 'win32' else 'bin/python')


def environment_ready(python):
    if not Path(python).is_file():
        return False
    script = ('import importlib.util,sys; '
              'sys.exit(0 if sys.version_info >= (3,11) and all(importlib.util.find_spec(n) '
              'for n in ("fastapi","uvicorn","mcp","multipart")) else 1)')
    try:
        return subprocess.run([str(python), '-I', '-c', script], timeout=15,
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def ensure_environment(root, setup=False):
    python = environment_python(root)
    if environment_ready(python):
        return python
    if not setup:
        raise LaunchError(f'Setup required. Run launcher.py --setup to create/update {python.parent.parent.name} '
                          'and install requirements.txt. No packages were installed.')
    print(f'Setup: preparing {python.parent.parent.name} and installing requirements.txt.', flush=True)
    try:
        if not python.exists():
            environment = python.parent.parent
            if environment.exists():
                raise LaunchError(f'{environment} is incomplete. Choose another location or repair it; it was not deleted.')
            subprocess.run([sys.executable, '-m', 'venv', str(environment)], check=True, timeout=60)
        subprocess.run([str(python), '-m', 'pip', '--disable-pip-version-check', 'install',
                        '-r', str(Path(root) / 'requirements.txt')], check=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        raise LaunchError(f'Setup failed ({type(exc).__name__}); retry --setup. Existing environments were preserved.') from exc
    if not environment_ready(python):
        raise LaunchError('Setup finished but required modules are still unavailable; inspect setup output and retry --setup.')
    return python


def spawn_server(root, python, config):
    directory = Path(root) / '.launcher'
    directory.mkdir(exist_ok=True)
    with (directory / 'server.log').open('ab') as log:
        kwargs = {'cwd': str(root), 'stdin': subprocess.DEVNULL, 'stdout': log,
                  'stderr': subprocess.STDOUT, 'close_fds': True}
        if sys.platform == 'win32':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs['start_new_session'] = True
        return subprocess.Popen([str(python), str(Path(root) / 'run.py')], **kwargs)


def stop_owned_child(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def ensure_server(root, config, timeout=60, setup=False):
    if not math.isfinite(timeout) or timeout <= 0:
        raise LaunchError('Startup timeout must be finite and greater than zero.')
    root = Path(root)
    url = service_url(config)
    identity = instance_identity(root, config)
    deadline = time.monotonic() + timeout
    # One root-wide lock serializes environment setup as well as service start.
    with startup_lock(root / '.launcher' / 'startup.lock', deadline):
        state = probe_health(url, identity, timeout=min(2, max(0.01, deadline - time.monotonic())))
        if state == 'matching':
            return url + '/preflight'
        if state == 'foreign':
            raise LaunchError(f'Port {config.get("server", {}).get("port", 8300)} is occupied by another service '
                              'or a different agentchattr installation/configuration. It was not stopped. '
                              'Choose another configured port or close the conflicting service yourself.')
        python = ensure_environment(root, setup=setup)
        # Explicit setup has its own bounded installation deadlines. Readiness
        # gets a fresh budget afterwards; a passive launch uses the original one.
        if setup:
            deadline = time.monotonic() + timeout
        if time.monotonic() >= deadline:
            raise LaunchError('Startup deadline reached before service launch; retry.')
        process = spawn_server(root, python, config)
        try:
            while time.monotonic() < deadline:
                code = process.poll()
                if code is not None:
                    raise LaunchError(f'Server exited with code {code}; inspect {root / ".launcher/server.log"} and retry.')
                state = probe_health(url, identity, timeout=min(1, max(0.01, deadline - time.monotonic())))
                if state == 'matching':
                    return url + '/preflight'
                if state == 'foreign':
                    raise LaunchError('Port became occupied by another service during startup; only the new owned child is stopped.')
                time.sleep(min(0.1, max(0, deadline - time.monotonic())))
            raise LaunchError(f'Server readiness deadline reached; inspect {root / ".launcher/server.log"} and retry.')
        except BaseException:
            stop_owned_child(process)
            raise


def preflight_snapshot(config):
    checked = datetime.now(timezone.utc).isoformat()
    agents = []
    for name, cfg in config.get('agents', {}).items():
        api = cfg.get('type') == 'api'
        command = cfg.get('command', '')
        executable = shutil.which(command) if not api and isinstance(command, str) and command else None
        agents.append({'name': name, 'label': cfg.get('label', name), 'client_type': 'api' if api else 'cli',
                       'executable': executable, 'executable_found': bool(executable), 'version': None,
                       'startup_checked': False, 'authentication': 'unknown',
                       'adapter_connected': 'unknown', 'ready': False, 'checked_at': checked})
    return {'checked_at': checked, 'agents': agents}


def open_browser(url):
    # Bound platform browser discovery; do not let an xdg-open helper hang launch.
    kwargs = {'timeout': 10, 'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL,
              'stderr': subprocess.DEVNULL}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.run([sys.executable, '-c',
            'import sys,webbrowser; sys.exit(0 if webbrowser.open(sys.argv[1]) else 1)', url], **kwargs).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(argv=None, *, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only checks; no setup, files, server or model launch.')
    parser.add_argument('--setup', action='store_true', help='Permit platform environment creation and dependency installation.')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--timeout', type=float, default=60, help='Service startup deadline in seconds (default 60).')
    for flag in ('--port', '--data-dir', '--mcp-http-port', '--mcp-sse-port', '--upload-dir'):
        parser.add_argument(flag)
    args = parser.parse_args(argv)
    if args.check and args.setup:
        parser.error('--check and --setup cannot be combined')
    flags = list(argv) if argv is not None else sys.argv[1:]
    try:
        apply_cli_overrides(['launcher.py', *flags])
        config = load_config(Path(root))
        url = service_url(config)
        if args.check:
            result = {'server': probe_health(url, instance_identity(root, config)),
                      'environment_ready': environment_ready(environment_python(root)),
                      **preflight_snapshot(config)}
            print(json.dumps(result, indent=2))
            return 0
        try:
            target = ensure_server(root, config, timeout=args.timeout, setup=args.setup)
        except LaunchError as exc:
            if not args.setup and 'Setup required.' in str(exc) and sys.stdin.isatty():
                print(str(exc))
                if input('Type SETUP to install these app dependencies, or Enter to cancel: ').strip() == 'SETUP':
                    target = ensure_server(root, config, timeout=args.timeout, setup=True)
                else:
                    return 1
            else:
                raise
        print(f'Pre-flight: {target}')
        if not args.no_browser and not open_browser(target):
            print('Browser did not open. Open the URL above; the server remains available.')
        return 0
    except (LaunchError, OSError, ValueError) as exc:
        print(f'Launch failed: {exc}', file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('Launch cancelled.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
