#!/usr/bin/env sh
# Shared pre-flight bootstrap; safe for a checkout also used from Windows.
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
else
    echo "Python 3.11 or newer is required. Install Python and retry." >&2
    exit 1
fi
exec "$PYTHON_BIN" "$ROOT/launcher.py" "$@"
