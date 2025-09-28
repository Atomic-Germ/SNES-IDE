#!/usr/bin/env bash

# POSIX wrapper for audio-tools
set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PY="$SCRIPT_DIR/audio-tools.py"

if [ -f "$PY" ]; then
    exec python3 "$PY" "$@"
else
    echo "Error: audio-tools.py not found in $SCRIPT_DIR"
    exit 1
fi
