#!/bin/sh
# macOS wrapper for externTools
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOL="$SELF_DIR/externTools"

if [ -x "$TOOL" ]; then
  exec "$TOOL" "$@"
fi

echo "externTools: native binary not found. Please install or build the macOS version of the tool."
exit 1
