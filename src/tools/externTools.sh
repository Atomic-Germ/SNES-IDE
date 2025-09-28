#!/usr/bin/env bash

# POSIX wrapper for externTools
set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PY="$SCRIPT_DIR/externTools.py"

if [ -f "$PY" ]; then
    exec python3 "$PY" "$@"
else
    echo "Error: externTools.py not found in $SCRIPT_DIR"
    exit 1
fi
