#!/usr/bin/env zsh

# SNES-IDE macOS Installer
# This script installs SNES-IDE on macOS systems

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

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This installer is for macOS only."
    exit 1
fi

print_step "Installing SNES-IDE for macOS..."

# Set installation directory
INSTALL_DIR="$HOME/Applications/SNES-IDE"

# Create installation directory
print_step "Creating installation directory..."
sudo mkdir -p "$INSTALL_DIR"

# Get the directory where this script is located
# Try multiple methods to handle different shells
if [[ -n "${BASH_SOURCE[0]}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [[ -n "${ZSH_VERSION}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${(%):-%N}")" && pwd)"
else
    # Fallback for other shells
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
print_step "Copying SNES-IDE files..."
# Copy all files to install directory
sudo cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

# Make scripts executable
print_step "Setting executable permissions..."
sudo find "$INSTALL_DIR" -name "*.sh" -exec chmod +x {} \;
sudo find "$INSTALL_DIR" -name "*.py" -exec chmod +x {} \;

# Create wrapper scripts for macOS
print_step "Creating macOS wrapper scripts..."

# Ensure tools directory exists
sudo mkdir -p "$INSTALL_DIR/tools"

# Text editor wrapper
sudo tee "$INSTALL_DIR/tools/text-editor.sh" > /dev/null << 'EOF'
#!/bin/bash
# Text editor launcher for SNES-IDE (macOS)

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

sudo chmod +x "$INSTALL_DIR/tools/text-editor.sh"

# Create Applications folder shortcuts
print_step "Creating Applications shortcuts..."

# Create basic app bundle structure
sudo mkdir -p "/Applications/SNES-IDE.app/Contents/MacOS"
sudo mkdir -p "/Applications/SNES-IDE.app/Contents/Resources"

# Main SNES-IDE app
sudo tee "/Applications/SNES-IDE.app/Contents/MacOS/SNES-IDE" > /dev/null << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/snes-ide.py" "\$@"
EOF
sudo chmod +x "/Applications/SNES-IDE.app/Contents/MacOS/SNES-IDE"

# Create basic app bundle structure if it doesn't exist
if [[ ! -d "/Applications/SNES-IDE.app" ]]; then
    sudo mkdir -p "/Applications/SNES-IDE.app/Contents/MacOS"
    sudo mkdir -p "/Applications/SNES-IDE.app/Contents/Resources"
fi

# Copy icon if available
if [[ -f "$INSTALL_DIR/assets/icons/icon.png" ]]; then
    sudo cp "$INSTALL_DIR/assets/icons/icon.png" "/Applications/SNES-IDE.app/Contents/Resources/"
fi

# Create Info.plist
sudo tee "/Applications/SNES-IDE.app/Contents/Info.plist" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>SNES-IDE</string>
    <key>CFBundleIconFile</key>
    <string>icon.png</string>
    <key>CFBundleIdentifier</key>
    <string>com.snes-ide.main</string>
    <key>CFBundleName</key>
    <string>SNES-IDE</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
</dict>
</plist>
EOF

# Create tool applications
create_tool_app() {
    local app_name="$1"
    local script_name="$2"
    local app_path="/Applications/$app_name.app"

    sudo mkdir -p "$app_path/Contents/MacOS"
    sudo mkdir -p "$app_path/Contents/Resources"

    sudo tee "$app_path/Contents/MacOS/$app_name" > /dev/null << EOF
#!/bin/bash
exec "$INSTALL_DIR/tools/$script_name" "\$@"
EOF
    sudo chmod +x "$app_path/Contents/MacOS/$app_name"

    # Copy icon
    if [[ -f "$INSTALL_DIR/assets/icons/icon.png" ]]; then
        sudo cp "$INSTALL_DIR/assets/icons/icon.png" "$app_path/Contents/Resources/"
    fi

    # Create Info.plist
    sudo tee "$app_path/Contents/Info.plist" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>$app_name</string>
    <key>CFBundleIconFile</key>
    <string>icon.png</string>
    <key>CFBundleIdentifier</key>
    <string>com.snes-ide.$app_name</string>
    <key>CFBundleName</key>
    <string>$app_name</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
</dict>
</plist>
EOF
}

create_tool_app "SNES-IDE Text Editor" "text-editor.sh"
create_tool_app "SNES-IDE Audio Tools" "audio-tools.py"
create_tool_app "SNES-IDE Graphics Tools" "gfx-tools.py"
create_tool_app "SNES-IDE Compiler" "automatizer-batch.sh"

print_step "Installation completed successfully!"
echo
echo "SNES-IDE has been installed to: $INSTALL_DIR"
echo
echo "Applications created in /Applications/:"
echo "  - SNES-IDE.app (main application)"
echo "  - SNES-IDE Text Editor.app"
echo "  - SNES-IDE Audio Tools.app"
echo "  - SNES-IDE Graphics Tools.app"
echo "  - SNES-IDE Compiler.app"
echo
echo "You can now:"
echo "  - Launch SNES-IDE from your Applications folder"
echo "  - Configure your preferred text editor by running SNES-IDE and selecting option 7"
echo
echo "Make sure you have Python 3 installed. You can install it via Homebrew:"
echo "  brew install python3"
echo
echo "For bsnes emulator, you can install it via Homebrew:"
echo "  brew install bsnes"