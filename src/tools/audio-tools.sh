#!/bin/sh
# macOS wrapper for audio-tools
# Prefer a native macOS binary named "audio-tools" in the same folder; if not
# present, instruct the user how to install the tool.

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOL="$SELF_DIR/audio-tools"

if [ -x "$TOOL" ]; then
  exec "$TOOL" "$@"
fi

# Try in the current working directory's libs path
if [ -x "./libs/audio-tools" ]; then
  exec "./libs/audio-tools" "$@"
fi

echo "audio-tools: macOS native binary not bundled. See docs/PORTING_MAC.md for installation instructions."
exit 1