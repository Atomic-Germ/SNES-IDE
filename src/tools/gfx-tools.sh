#!/usr/bin/env bash

# POSIX wrapper for gfx-tools
set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PY="$SCRIPT_DIR/gfx-tools.py"

if [ -f "$PY" ]; then
    exec python3 "$PY" "$@"
else
    echo "Error: gfx-tools.py not found in $SCRIPT_DIR"
    exit 1
fi
