"""Install a Linux/Omarchy application-menu entry; never replace an existing one."""
import argparse
import os
from pathlib import Path
import sys


def desktop_quote(value):
    # Desktop Entry Exec quoting differs from shell quoting; % is a field code.
    value = value.replace('%', '%%')
    for character in ('\\', '"', '`', '$'):
        value = value.replace(character, '\\' + character)
    # The desktop-entry string parser consumes one escaping layer before Exec.
    value = value.replace('\\', '\\\\')
    return '"' + value + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path,
                        default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'applications')
    args = parser.parse_args()
    script = Path(__file__).resolve().parent / 'start.sh'
    if any(c in str(script) for c in ('\n', '\r')):
        parser.error('checkout path cannot contain a newline')
    args.destination.mkdir(parents=True, exist_ok=True)
    target = args.destination / 'agentchattr.desktop'
    content = ('[Desktop Entry]\nType=Application\nName=Agentchattr\n'
               'Comment=Open agentchattr pre-flight\n'
               f'Exec=sh {desktop_quote(str(script))}\n'
               'Terminal=true\nIcon=utilities-terminal\nCategories=Development;\n')
    try:
        with target.open('x', encoding='utf-8', newline='\n') as output:
            output.write(content)
    except FileExistsError:
        print(f'Shortcut already exists: {target}. Move it before installing this checkout\'s shortcut.', file=sys.stderr)
        return 1
    print(f'Created {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
