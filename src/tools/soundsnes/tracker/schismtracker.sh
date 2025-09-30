#!/bin/sh
# macOS wrapper that prefers a bundled schismtracker binary or a system-installed one.
# Upstream macOS releases: https://github.com/schismtracker/schismtracker/releases/tag/20250825

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
# check for local bundled executable
if [ -x "$SELF_DIR/schismtracker" ]; then
  exec "$SELF_DIR/schismtracker" "$@"
fi
# check libs location relative to repo
if [ -x "${SELF_DIR}/../../libs/schismtracker/schismtracker" ]; then
  exec "${SELF_DIR}/../../libs/schismtracker/schismtracker" "$@"
fi
# fallback to system PATH
if command -v schismtracker >/dev/null 2>&1; then
  exec schismtracker "$@"
fi

echo "schismtracker: macOS binary not found. Please download the macOS build from https://github.com/schismtracker/schismtracker/releases/tag/20250825 and place it in SNES-IDE-out/tools/soundsnes/tracker/ or in libs/schismtracker/."
exit 1