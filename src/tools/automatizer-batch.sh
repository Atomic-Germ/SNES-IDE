#!/usr/bin/env bash
# Cross-platform automatizer script for SNES-IDE

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$(dirname "$SCRIPT_DIR")"

# Function to read user input with default
read_with_default() {
    local prompt="$1"
    local default="$2"
    local input

    read -p "$prompt [$default]: " input
    echo "${input:-$default}"
}

# Get user input
echo "SNES Project Compiler"
echo "===================="
userDirectory=$(read_with_default "Enter the desired directory (e.g., /home/user/Desktop/game_folder)" "$(pwd)")
MemoryMap=$(read_with_default "HIROM or LOROM (if you don't know, choose LOROM)" "LOROM")
Speed=$(read_with_default "Speed: use all SNES speed (FAST) or use the recommended one (SLOW)" "SLOW")

# Convert to uppercase
MemoryMap=$(echo "$MemoryMap" | tr '[:lower:]' '[:upper:]')
Speed=$(echo "$Speed" | tr '[:lower:]' '[:upper:]')

# Set the path to automatizer executable
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    automatizerPath="$TOOLS_DIR/libs/pvsneslib/devkitsnes/automatizer"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    automatizerPath="$TOOLS_DIR/libs/pvsneslib/devkitsnes/automatizer"
else
    # Assume Windows/WSL
    automatizerPath="$TOOLS_DIR/libs/pvsneslib/devkitsnes/automatizer.exe"
fi

# Check if automatizer exists
if [[ -f "$automatizerPath" ]]; then
    echo "Compiling project in: $userDirectory"
    echo "Memory Map: $MemoryMap"
    echo "Speed: $Speed"
    echo

    # Change to the user-specified directory
    cd "$userDirectory" || {
        echo "Error: Cannot change to directory $userDirectory"
        exit 1
    }

    # Execute automatizer with the parameters
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        "$automatizerPath" "$userDirectory" "$MemoryMap" "$Speed"
    else
        # Unix-like systems
        "$automatizerPath" "$userDirectory" "$MemoryMap" "$Speed"
    fi

    if [[ $? -eq 0 ]]; then
        echo "Execution successful!"
    else
        echo "Error: Compilation failed!"
        exit 1
    fi

else
    echo "Error: automatizer not found at $automatizerPath"
    echo "Expected location: $TOOLS_DIR/libs/pvsneslib/devkitsnes/"
    exit 1
fi

echo
read -p "Press Enter to continue..."