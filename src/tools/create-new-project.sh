#!/usr/bin/env bash

# POSIX wrapper for create-new-project
set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PY="${SCRIPT_DIR}/create-new-project.py"

if [ -f "$PY" ]; then
    exec python3 "$PY" "$@"
else
    echo "Error: create-new-project.py not found in $SCRIPT_DIR"
    exit 1
fi
