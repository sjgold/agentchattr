"""Check repository-relative Markdown links and heading anchors, excluding fences.

Reports existing defects without rewriting documents. Exit 1 means broken links.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit


def prose_lines(text):
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
            continue
        if fence is None:
            yield number, line


def anchors(text):
    found = set()
    counts = {}
    for _, line in prose_lines(text):
        heading = re.match(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$', line)
        if heading:
            label = heading.group(1).lower()
            label = re.sub(r'<[^>]*>', '', label)
            label = re.sub(r'[^\w\- ]', '', label, flags=re.UNICODE).replace(' ', '-')
            count = counts.get(label, 0)
            counts[label] = count + 1
            found.add(label + (f'-{count}' if count else ''))
        found.update(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', line))
    return found


def check_links(root, files):
    root = Path(root).resolve()
    problems = []
    cache = {}
    for source in files:
        path = root / source
        for line_number, line in prose_lines(path.read_text(encoding='utf-8-sig')):
            targets = re.findall(r'!?\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+["\'][^)]*)?\)', line)
            targets += re.findall(r'^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)', line)
            for target in targets:
                raw = target.strip('<>')
                parsed = urlsplit(raw)
                if parsed.scheme or parsed.netloc or raw.startswith(('/', 'epics/')):
                    continue
                resolved = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
                try:
                    relative = resolved.relative_to(root).as_posix()
                except ValueError:
                    continue
                reason = None
                if not resolved.exists():
                    reason = 'missing_file'
                elif parsed.fragment and resolved.is_file() and resolved.suffix.lower() == '.md':
                    if resolved not in cache:
                        cache[resolved] = anchors(resolved.read_text(encoding='utf-8-sig'))
                    if unquote(parsed.fragment) not in cache[resolved]:
                        reason = 'missing_anchor'
                if reason:
                    problems.append({'source': str(source), 'line': line_number,
                                     'target': relative, 'anchor': unquote(parsed.fragment),
                                     'reason': reason})
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=args.root).decode('utf-8').split('\0')
    files = [name for name in tracked if name.lower().endswith('.md') and (args.root / name).is_file()]
    problems = check_links(args.root, files)
    report = {'files': len(files), 'broken': len(problems), 'problems': problems}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(files), 'broken': len(problems)}))
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
