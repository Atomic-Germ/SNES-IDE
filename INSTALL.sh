#!/usr/bin/env bash
# Simple installer script for macOS

set -euo pipefail

echo "SNES-IDE macOS installer"

TARGET_DIR="$PWD/sneside-macos-install"

mkdir -p "$TARGET_DIR"

# If running from inside the packaged output this will place files in a sensible location
if [ -d "SNES-IDE-out" ]; then
    echo "Copying packaged files to $TARGET_DIR"
    cp -a SNES-IDE-out/* "$TARGET_DIR/"
    echo "Files copied. You can inspect $TARGET_DIR"
else
    echo "SNES-IDE-out directory not found. If you downloaded the packaged artifact, extract it and re-run this script inside that directory."
fi

echo "Installation step completed (placeholder). Customize INSTALL.sh to perform further setup as needed."
exit 0
