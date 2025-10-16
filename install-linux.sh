#!/usr/bin/env bash

# SNES-IDE Linux Installer
# This script installs SNES-IDE on Linux systems

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

# Check if running as root (for system-wide installation)
if [[ $EUID -eq 0 ]]; then
    print_warning "Running as root. Installing system-wide."
    INSTALL_DIR="/opt/snes-ide"
    DESKTOP_DIR="/usr/share/applications"
    BIN_DIR="/usr/local/bin"
else
    print_step "Installing for current user."
    INSTALL_DIR="$HOME/.local/share/snes-ide"
    DESKTOP_DIR="$HOME/.local/share/applications"
    BIN_DIR="$HOME/.local/bin"
fi

# Create directories
print_step "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$BIN_DIR"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_step "Copying SNES-IDE files..."
# Copy all files from current directory to install directory
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true

# Make scripts executable
print_step "Setting executable permissions..."
find "$INSTALL_DIR" -name "*.sh" -exec chmod +x {} \;
find "$INSTALL_DIR" -name "*.py" -exec chmod +x {} \;

# Create desktop entries
print_step "Creating desktop shortcuts..."

cat > "$DESKTOP_DIR/snes-ide.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNES-IDE
Comment=SNES Game Development IDE
Exec=$INSTALL_DIR/snes-ide
Icon=$INSTALL_DIR/assets/icons/icon.png
Terminal=false
Categories=Development;IDE;
EOF

cat > "$DESKTOP_DIR/snes-ide-text-editor.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNES-IDE Text Editor
Comment=Launch text editor for SNES development
Exec=$INSTALL_DIR/tools/text-editor.sh
Icon=$INSTALL_DIR/assets/icons/icon.png
Terminal=false
Categories=Development;TextEditor;
EOF

cat > "$DESKTOP_DIR/snes-ide-audio-tools.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNES-IDE Audio Tools
Comment=Audio conversion tools for SNES
Exec=$INSTALL_DIR/tools/audio-tools.py
Icon=$INSTALL_DIR/assets/icons/icon.png
Terminal=false
Categories=Development;Audio;
EOF

cat > "$DESKTOP_DIR/snes-ide-graphics-tools.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNES-IDE Graphics Tools
Comment=Graphics conversion tools for SNES
Exec=$INSTALL_DIR/tools/gfx-tools.py
Icon=$INSTALL_DIR/assets/icons/icon.png
Terminal=false
Categories=Development;Graphics;
EOF

cat > "$DESKTOP_DIR/snes-ide-compiler.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNES-IDE Compiler
Comment=Compile SNES projects
Exec=$INSTALL_DIR/tools/automatizer-batch.sh
Icon=$INSTALL_DIR/assets/icons/icon.png
Terminal=true
Categories=Development;BuildSystem;
EOF

cat > "$DESKTOP_DIR/snes-ide-emulator.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNES-IDE Emulator
Comment=Test SNES games with bsnes
Exec=bsnes
Icon=$INSTALL_DIR/assets/icons/icon.png
Terminal=false
Categories=Game;Emulator;
EOF

# Create wrapper scripts for tools that need special handling
print_step "Creating wrapper scripts..."

# Text editor wrapper that uses configured editor
cat > "$INSTALL_DIR/tools/text-editor.sh" << 'EOF'
#!/bin/bash
# Text editor launcher for SNES-IDE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

# Load configuration
CONFIG_FILE="$INSTALL_DIR/snes-ide-config.json"
if [[ -f "$CONFIG_FILE" ]]; then
    EDITOR_CMD=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE')).get('text_editor', 'code'))")
else
    EDITOR_CMD="code"
fi

# Launch editor
exec $EDITOR_CMD "$@"
EOF

chmod +x "$INSTALL_DIR/tools/text-editor.sh"

# Create main executable symlink/script
print_step "Creating main executable..."
cat > "$BIN_DIR/snes-ide" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/snes-ide.py" "\$@"
EOF
chmod +x "$BIN_DIR/snes-ide"

# Update desktop database if running as root
if [[ $EUID -eq 0 ]]; then
    print_step "Updating desktop database..."
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

print_step "Installation completed successfully!"
echo
echo "SNES-IDE has been installed to: $INSTALL_DIR"
echo
echo "You can now:"
echo "  - Run 'snes-ide' from the command line"
echo "  - Find SNES-IDE applications in your applications menu"
echo "  - Configure your preferred text editor by running snes-ide and selecting option 7"
echo
echo "Make sure you have Python 3 and your preferred text editor installed."
echo "For bsnes emulator, you may need to install it separately:"
echo "  sudo apt install bsnes  # Ubuntu/Debian"
echo "  or download from: https://github.com/bsnes-emu/bsnes"