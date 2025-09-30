#!/bin/sh
# macOS wrapper for gfx-tools
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOL="$SELF_DIR/gfx-tools"

if [ -x "$TOOL" ]; then
  exec "$TOOL" "$@"
fi

echo "gfx-tools: native binary not found. See docs/PORTING_MAC.md for macOS build instructions."
exit 1