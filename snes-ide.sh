#!/usr/bin/env bash

# Top-level wrapper to run the Python entrypoint
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PY="$SCRIPT_DIR/src/snes-ide.py"

if [ -f "$PY" ]; then
    exec python3 "$PY" "$@"
else
    echo "Could not find $PY. Run the application with: python3 src/snes-ide.py"
    exit 1
fi
