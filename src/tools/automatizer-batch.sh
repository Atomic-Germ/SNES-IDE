#!/usr/bin/env bash

set -e

read -p "Enter the desired directory (e.g., /home/user/Desktop/game_folder): " userDirectory
read -p "Memory map (HIROM or LOROM): " MemoryMap
read -p "Speed (FAST or SLOW): " Speed

TOOLS_DIR="$(dirname "$(realpath "$0")")/.."
AUTOMATIZER_PATH="$TOOLS_DIR/libs/pvsneslib/devkitsnes/automatizer"

if [ -x "$AUTOMATIZER_PATH" ]; then
    "$AUTOMATIZER_PATH" "$userDirectory" "$MemoryMap" "$Speed"
    echo "Execution successful!"
else
    # Fallback to Python implementation if binary not present
    PY_AUTOMATIZER="$TOOLS_DIR/../src/libs/pvsneslib/devkitsnes/automatizer.py"
    if [ -f "$PY_AUTOMATIZER" ]; then
        python3 "$PY_AUTOMATIZER" "$userDirectory" "$MemoryMap" "$Speed"
    else
        echo "Error: automatizer binary or Python script not found."
        exit 1
    fi
fi

read -p "Press Enter to continue..." -r
