#!/usr/bin/env python3
"""Build a clean release zip for agentchattr.

Packages only user-facing files — no .git, no dev files, no logs, no caches.
Output: dist/agentchattr-{version}.zip.
"""

import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text().strip()
OUT_NAME = f"agentchattr-{VERSION}"

# Files and dirs to include (relative to repo root)
INCLUDE_FILES = [
    "open_chat.html",
    "config.toml",
    "config.local.toml.example",
    "requirements.txt",
    "README.md",
    "STATUS.md",
    "LICENSE",
    "VERSION",
    "screenshot.png",
    "gang.gif",
]

INCLUDE_DIRS = [
    "static",
    "windows",
    "macos-linux",
    "session_templates",
]


def build():
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / OUT_NAME
        dest.mkdir()

        for f in INCLUDE_FILES:
            src = ROOT / f
            shutil.copy2(src, dest / f)
        # Keep release guidance small; detailed evidence lives with the source.
        for name in ('README.md', 'STATUS.md'):
            page = dest / name
            page.write_text(page.read_text(encoding='utf-8').replace(
                '](docs/', '](https://github.com/sjgold/agentchattr/blob/main/docs/'), encoding='utf-8')

        shutil.copy2(ROOT / 'Start Agentchattr.bat', dest / 'Start Agentchattr.bat')
        source_dir = dest / 'src'
        source_dir.mkdir()
        for source in sorted((ROOT / 'src').glob('*.py')):
            shutil.copy2(source, source_dir / source.name)

        for d in INCLUDE_DIRS:
            src = ROOT / d
            shutil.copytree(src, dest / d)

        (ROOT / 'dist').mkdir(exist_ok=True)
        out_path = ROOT / 'dist' / OUT_NAME
        shutil.make_archive(str(out_path), "zip", tmp, OUT_NAME)

    print(f"Built {out_path}.zip")
    return f"{out_path}.zip"


if __name__ == "__main__":
    build()
