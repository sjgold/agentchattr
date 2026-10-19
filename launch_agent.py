"""Shared compatibility entry point. Explicit setup only; preserve child status."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from config_loader import CLI_OVERRIDE_FLAGS, apply_cli_overrides, load_config
from launcher import LaunchError, ensure_environment, ensure_server

ROOT = Path(__file__).resolve().parent


def main(argv=None, *, root=ROOT):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('agent', help='Configured agent template name')
    parser.add_argument('--setup', action='store_true', help='Explicitly permit platform environment setup')
    for flag, _ in CLI_OVERRIDE_FLAGS:
        parser.add_argument(flag)
    args, extra = parser.parse_known_args(argv)
    apply_cli_overrides(['launch_agent.py', *argv])
    try:
        config = load_config(root)
        client = config.get('agents', {}).get(args.agent)
        if not client:
            raise LaunchError('Agent template is not configured. Add it to config.local.toml before launching.')
        api = client.get('type') == 'api'
        if not api and not shutil.which(client.get('command', args.agent)):
            raise LaunchError('Configured CLI executable was not found. Install or configure it before retrying.')
        ensure_server(root, config, setup=args.setup)
        python = ensure_environment(root, setup=False)
        script = 'wrapper_api.py' if api else 'wrapper.py'
        command = [str(python), str(root / script), args.agent]
        if not api:
            command.append('--no-restart')
        if extra and extra[0] == '--':
            extra = extra[1:]
        if extra:
            command.extend(['--', *extra] if not api else extra)
        return subprocess.run(command, cwd=root).returncode
    except (LaunchError, OSError, ValueError) as exc:
        # Configuration/executable failures are local, no provider responses.
        print(f'Launch could not complete: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
