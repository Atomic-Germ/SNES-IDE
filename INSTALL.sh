#!/usr/bin/env bash
set -e

if [[ "$EUID" -eq 0 ]]; then
    echo "Error: DO NOT run this script as root or with sudo."
    exit 1
fi

# Detect correct home directory even if running with sudo
if [ "$SUDO_USER" ]; then
    USER_HOME=$(eval echo "~$SUDO_USER")
else
    USER_HOME="$HOME"
fi

TARGET_DIR="$USER_HOME/.local/share/snes-ide"
ROOT_DIR="$(realpath "$(dirname "$0")")"
OUT_DIR="$ROOT_DIR/SNES-IDE-out"

mkdir -p "$TARGET_DIR"

echo "Copying distribution to $TARGET_DIR"
shopt -s dotglob
cp -r "$OUT_DIR"/* "$TARGET_DIR"
shopt -u dotglob

# Ensure executable bits for wrappers and emulator binaries
echo "Setting executable bits for shell wrappers and emulators..."
find "$TARGET_DIR" -type f \( -name "*.sh" -o -name "bsnes*" -o -name "higan*" -o -name "retroarch" \) -exec chmod a+x {} + || true

cat <<EOF
Installation complete.
You can start SNES-IDE with: $TARGET_DIR/src/snes-ide.py or use the top-level snes-ide.sh in the distribution.
EOF
