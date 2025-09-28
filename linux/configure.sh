#!/bin/bash
set -e

if [[ "$EUID" -eq 0 ]]; then

    echo "Error: DO NOT run this script as root or with sudo."
    exit -1

fi

# Detect correct home directory even if running with sudo
if [ "$SUDO_USER" ]; then

    USER_HOME=$(eval echo "~$SUDO_USER")

else

    USER_HOME="$HOME"
    
fi

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PROJECT_ROOT="$(realpath "$SCRIPT_DIR/../..")"
OUT_DIR="$PROJECT_ROOT/SNES-IDE-out"

cd "$SCRIPT_DIR"

echo "Copying pre-built files from $OUT_DIR to $USER_HOME/.local/share/snes-ide..."

TARGET_DIR="$USER_HOME/.local/share/snes-ide"

read -p "Write down the password to allow cleaning the previous configuration: " -r passwd

if [ -d "$TARGET_DIR" ]; then

    echo "Removing previous installation at $TARGET_DIR"
    rm -rf "$TARGET_DIR"

fi

mkdir -p "$TARGET_DIR"

shopt -s dotglob
cp -r "$OUT_DIR"/* "$TARGET_DIR"
shopt -u dotglob

echo "Fixing executable permissions in $TARGET_DIR..."
# Make shell wrappers and obvious emulator binaries executable
find "$TARGET_DIR" -type f \( -name "*.sh" -o -name "bsnes*" -o -name "higan*" -o -name "retroarch" \) -exec chmod a+x {} + || true

# If there's a native installer script, run it. Else, provide guidance.
if [ -f "$TARGET_DIR/INSTALL.sh" ]; then

    echo "Running native installer: INSTALL.sh"
    bash "$TARGET_DIR/INSTALL.sh"

elif [ -f "$TARGET_DIR/INSTALL.bat" ]; then

    echo "Found INSTALL.bat in distribution, but no native installer."
    echo "Please convert the installer to a native script or run the Python entrypoint directly."
    echo "You can start the application with: python3 $TARGET_DIR/src/snes-ide.py"

else

    echo "No installer found. You can start the application with: python3 $TARGET_DIR/src/snes-ide.py"

fi

read -p "Do you want to create a desktop shortcut for start.sh? (y/n): " create_shortcut
if [[ "$create_shortcut" =~ ^[Yy]$ ]]; then

    ICON_PATH="../icons/icon.png"
    START_SH="start.sh"
    DESKTOP_FILE="$USER_HOME/Desktop/SNES-IDE.desktop"
    SYSTEM_DESKTOP_FILE="/usr/share/applications/SNES-IDE.desktop"

    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=SNES-IDE
Exec=$(realpath "$SCRIPT_DIR/src/$START_SH")
Icon=$(realpath "$ICON_PATH")
Terminal=true
EOF

    echo "Shortcut created at $DESKTOP_FILE"

    echo "Write your password to copy to applications: "
    if sudo cp "$DESKTOP_FILE" "$SYSTEM_DESKTOP_FILE"; then

        sudo chmod 644 "$SYSTEM_DESKTOP_FILE"
        echo "Shortcut also installed system-wide at $SYSTEM_DESKTOP_FILE"

    else

        echo "Could not move shortcut to $SYSTEM_DESKTOP_FILE. You may need to run as root."

    fi

fi

read -p "Do you want to start SNES-IDE now? (y/n): " exec_start
if [[ "$exec_start" =~ ^[Yy]$ ]]; then

    bash "$SCRIPT_DIR/src/start.sh"

fi