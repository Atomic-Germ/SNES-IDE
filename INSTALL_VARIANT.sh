#!/usr/bin/env bash
set -e

# Interactive installer variant for SNES-IDE (POSIX)
# - Lets user choose install location
# - Lets user choose preferred editor (vscode or vim)
# - Offers to copy emulator binaries/cores if present
# - Creates Desktop shortcuts that launch the chosen editor or the snes-ide launcher

if [[ "$EUID" -eq 0 ]]; then
    echo "Error: DO NOT run this script as root or with sudo."
    exit 1
fi

# Determine platform specifics
UNAME=$(uname | tr '[:upper:]' '[:lower:]')
IS_MAC=false
IS_LINUX=false
if [[ "$UNAME" == "darwin" ]]; then IS_MAC=true; fi
if [[ "$UNAME" == "linux" ]]; then IS_LINUX=true; fi

# Detect user home
if [ "$SUDO_USER" ]; then
    USER_HOME=$(eval echo "~$SUDO_USER")
else
    USER_HOME="$HOME"
fi

DEFAULT_TARGET="$USER_HOME/.local/share/snes-ide"
read -p "Install directory (default: $DEFAULT_TARGET): " TARGET_DIR
TARGET_DIR=${TARGET_DIR:-$DEFAULT_TARGET}

mkdir -p "$TARGET_DIR"

ROOT_DIR="$(realpath "$(dirname "$0")")"
OUT_DIR="$ROOT_DIR/SNES-IDE-out"

# Copy distribution
if [ -d "$OUT_DIR" ]; then
    echo "Copying distribution to $TARGET_DIR"
    shopt -s dotglob
    cp -r "$OUT_DIR"/* "$TARGET_DIR"
    shopt -u dotglob
else
    echo "Distribution folder $OUT_DIR not found. Run build first (build/build.py) or place files under SNES-IDE-out/."
fi

# Editor selection
echo "Choose an editor to configure for SNES-IDE integration:" 
echo "  1) Visual Studio Code (code)"
echo "  2) Vim (terminal)"
echo "  3) None / I'll configure manually"
read -p "Enter 1, 2 or 3 (default 1): " editor_choice
editor_choice=${editor_choice:-1}

case "$editor_choice" in
    1)
        EDITOR_CHOICE="vscode"
        ;;
    2)
        EDITOR_CHOICE="vim"
        ;;
    *)
        EDITOR_CHOICE="none"
        ;;
esac

# Optionally copy emulators and libretro cores found in repo
read -p "Copy emulator binaries and libretro cores from repo if present? (y/n, default y): " copy_emu
copy_emu=${copy_emu:-y}

if [[ "$copy_emu" =~ ^[Yy] ]]; then
    if [ -d "$ROOT_DIR/libs/bsnes" ]; then
        echo "Copying libs/bsnes -> $TARGET_DIR/libs/bsnes"
        mkdir -p "$TARGET_DIR/libs/bsnes"
        cp -r "$ROOT_DIR/libs/bsnes"/* "$TARGET_DIR/libs/bsnes/" || true
    fi
    if [ -d "$ROOT_DIR/libs/libretro" ]; then
        echo "Copying libs/libretro -> $TARGET_DIR/libs/libretro"
        mkdir -p "$TARGET_DIR/libs/libretro"
        cp -r "$ROOT_DIR/libs/libretro"/* "$TARGET_DIR/libs/libretro/" || true
    fi
fi

# Ensure executable bits on wrappers and emulators
echo "Setting executable permissions on shell wrappers and native binaries..."
find "$TARGET_DIR" -type f \( -name "*.sh" -o -name "bsnes*" -o -name "higan*" -o -name "retroarch" \) -exec chmod a+x {} + || true

# Create editor launch helper in install dir
BIN_DIR="$TARGET_DIR/bin"
mkdir -p "$BIN_DIR"

if [[ "$EDITOR_CHOICE" == "vscode" ]]; then
    cat > "$BIN_DIR/snes-ide-open-editor" <<EOF
#!/usr/bin/env bash
# Launch VS Code in the current project (or open folder chooser if none provided)
if command -v code &> /dev/null; then
    if [ -n "$1" ]; then
        exec code "$1"
    else
        exec code "$TARGET_DIR"
    fi
else
    echo "VS Code ('code') not found in PATH. Please install or choose another editor."
    exit 1
fi
EOF
    chmod a+x "$BIN_DIR/snes-ide-open-editor"

elif [[ "$EDITOR_CHOICE" == "vim" ]]; then
    cat > "$BIN_DIR/snes-ide-open-editor" <<'EOF'
#!/usr/bin/env bash
# Launch vim in the given file or project folder
if [ -n "$1" ]; then
    exec vim "$1"
else
    exec vim
fi
EOF
    chmod a+x "$BIN_DIR/snes-ide-open-editor"
fi

# Desktop shortcut / launcher
read -p "Create a desktop shortcut to launch SNES-IDE? (y/n, default y): " create_shortcut
create_shortcut=${create_shortcut:-y}

if [[ "$create_shortcut" =~ ^[Yy] ]]; then
    DESKTOP_DIR="$USER_HOME/Desktop"
    mkdir -p "$DESKTOP_DIR"

    if $IS_LINUX; then
        DESKTOP_FILE="$DESKTOP_DIR/SNES-IDE.desktop"
        cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=SNES-IDE
Exec=$TARGET_DIR/snes-ide.sh
Icon=$TARGET_DIR/icons/icon.png
Terminal=true
EOF
        chmod 644 "$DESKTOP_FILE" || true
        echo "Created desktop shortcut: $DESKTOP_FILE"
    elif $IS_MAC; then
        SHORTCUT="$DESKTOP_DIR/SNES-IDE.command"
        cat > "$SHORTCUT" <<EOF
#!/usr/bin/env bash
"$TARGET_DIR/snes-ide.sh" "$@"
EOF
        chmod a+x "$SHORTCUT"
        echo "Created macOS command shortcut: $SHORTCUT"
    else
        # Generic fallback: create a small launcher script on Desktop
        SHORTCUT="$DESKTOP_DIR/launch-snes-ide.sh"
        cat > "$SHORTCUT" <<EOF
#!/usr/bin/env bash
"$TARGET_DIR/snes-ide.sh" "$@"
EOF
        chmod a+x "$SHORTCUT"
        echo "Created desktop launcher: $SHORTCUT"
    fi
fi

# Configure Notepad++ option for Windows users (informational)
if [[ "$IS_LINUX" == "false" && "$IS_MAC" == "false" ]]; then
    echo "On Windows you can run INSTALL_VARIANT.bat to configure Notepad++ shortcuts and Windows-specific options."
fi

cat <<EOF
Installation finished.
- Install directory: $TARGET_DIR
- Editor integration: $EDITOR_CHOICE
- You can launch SNES-IDE using: $TARGET_DIR/snes-ide.sh
- Editor helper created at: $BIN_DIR/snes-ide-open-editor (if selected)
EOF

exit 0
