#!/usr/bin/env bash
# libs/pvsneslib/devkitsnes/bin/automatizer
# Small POSIX wrapper to run the Python automatizer shipped with the repo
set -e
# Resolve the script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
# The python script is expected to be one directory up: ../automatizer.py
PY_AUTOMATIZER="$SCRIPT_DIR/../automatizer.py"
if [ -f "$PY_AUTOMATIZER" ]; then
  exec python3 "$PY_AUTOMATIZER" "$@"
else
  echo "automatizer Python script not found at $PY_AUTOMATIZER" >&2
  exit 1
fi
