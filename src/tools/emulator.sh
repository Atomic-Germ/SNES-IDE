#!/usr/bin/env bash

# POSIX wrapper to launch emulator
set -e

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
EMULATOR_DIR="$(realpath "$SCRIPT_DIR/../libs/bsnes")"

# Look for commonly named native emulator binaries
for candidate in "bsnes" "higan" "bsnes-snes9x" "bsnes-gtk"; do
    if [ -x "$EMULATOR_DIR/$candidate" ]; then
        exec "$EMULATOR_DIR/$candidate" "$@"
    fi
done

# If only Windows executable exists, inform user
if [ -f "$EMULATOR_DIR/bsnes.exe" ] || [ -f "$EMULATOR_DIR/bsnes.exe" ]; then
    echo "A Windows-only bsnes binary is present in the distribution. Please install a native emulator for your platform or provide a native binary in libs/bsnes/."
    exit 1
fi

# Try RetroArch if installed
if command -v retroarch &> /dev/null; then
    echo "RetroArch found. Launching RetroArch (you need to configure a SNES core separately)."
    exec retroarch "$@"
fi

echo "No emulator found. Install a native bsnes/higan or RetroArch, or place a native emulator binary in libs/bsnes/."
exit 1
