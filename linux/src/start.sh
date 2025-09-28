#!/bin/bash

set -e

if [ "$SUDO_USER" ]; then

    USER_HOME=$(eval echo "~$SUDO_USER")

else

    USER_HOME="$HOME"
    
fi

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PROJECT_ROOT="$(realpath "$SCRIPT_DIR/../..")"

# Prefer a native executable or shell wrapper in the installed location
INSTALL_DIR="$USER_HOME/.local/share/snes-ide"

if [ -f "$INSTALL_DIR/snes-ide.sh" ]; then

    echo "Starting SNES-IDE via native shell wrapper..."
    bash "$INSTALL_DIR/snes-ide.sh"
    exit 0

fi

if [ -f "$INSTALL_DIR/src/snes-ide.py" ]; then

    echo "Starting SNES-IDE via Python script..."
    python3 "$INSTALL_DIR/src/snes-ide.py"
    exit 0

fi

# As a fallback, look for installed binaries in the current project layout
if [ -f "$PROJECT_ROOT/SNES-IDE-out/src/snes-ide.py" ]; then

    echo "Starting local SNES-IDE development copy via Python script..."
    python3 "$PROJECT_ROOT/SNES-IDE-out/src/snes-ide.py"
    exit 0

fi

echo "SNES IDE not found! Please run ./linux/configure.sh to install or run the Python entrypoint directly."
exit 1