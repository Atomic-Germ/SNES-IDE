#!/bin/bash
#
# SNES-IDE Linux Installer
# Copyright (C) 2025 BrunoRNS
#
# This installer sets up SNES-IDE in a system location to avoid SELinux issues
# and provides a proper Linux installation experience.
#

set -e

# Configuration
INSTALL_DIR="/opt/snes-ide"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/pixmaps"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This installer must be run as root (use sudo)"
        exit 1
    fi
}

# Check prerequisites before installation
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Python 3 is available
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 is required but not installed"
        log_error "Please install Python 3 first"
        exit 1
    fi
    
    # Check if SNES-IDE has been built
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [[ ! -d "$SCRIPT_DIR/dist/SNES-IDE.AppDir/usr/src" ]] && [[ ! -d "$SCRIPT_DIR/../dist/SNES-IDE.AppDir/usr/src" ]]; then
        log_error "SNES-IDE has not been built yet"
        log_error ""
        log_error "Please build the application first:"
        log_error "  cd $(dirname "$SCRIPT_DIR")"
        log_error "  python3 build/build.py"
        log_error ""
        log_error "Then run this installer again."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Detect Linux distribution
detect_distro() {
    if command -v dnf >/dev/null 2>&1; then
        DISTRO="fedora"
        PKG_MANAGER="dnf"
    elif command -v apt >/dev/null 2>&1; then
        DISTRO="debian"
        PKG_MANAGER="apt"
    elif command -v pacman >/dev/null 2>&1; then
        DISTRO="arch"
        PKG_MANAGER="pacman"
    else
        log_warn "Unknown distribution, proceeding with generic installation"
        DISTRO="unknown"
    fi
    
    log_info "Detected distribution: $DISTRO"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    case $DISTRO in
        fedora)
            dnf install -y make gcc python3 python3-tkinter python3-pip
            ;;
        debian)
            apt update
            apt install -y make gcc python3 python3-tk python3-pip
            ;;
        arch)
            pacman -Sy --noconfirm make gcc python python-tkinter python-pip
            ;;
        *)
            log_warn "Please ensure make, gcc, python3, and python3-tkinter are installed"
            ;;
    esac
}

# Create installation directory
create_install_dir() {
    log_info "Creating installation directory at $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    mkdir -p "$DESKTOP_DIR"
    mkdir -p "$ICON_DIR"
}

# Copy SNES-IDE files
install_files() {
    log_info "Installing SNES-IDE files..."
    
    # Determine source directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [[ -d "$SCRIPT_DIR/dist/SNES-IDE.AppDir/usr/src" ]]; then
        SOURCE_DIR="$SCRIPT_DIR/dist/SNES-IDE.AppDir/usr/src"
    elif [[ -d "$SCRIPT_DIR/../dist/SNES-IDE.AppDir/usr/src" ]]; then
        SOURCE_DIR="$SCRIPT_DIR/../dist/SNES-IDE.AppDir/usr/src"
    else
        log_error "Could not find built SNES-IDE distribution"
        log_error "Please run 'python build/build.py' first to build the application"
        exit 1
    fi
    
    # Verify the build contains essential files
    if [[ ! -f "$SOURCE_DIR/snes-ide.py" ]]; then
        log_error "Build appears incomplete - missing main application file"
        log_error "Please run 'python build/build.py' to rebuild the application"
        exit 1
    fi
    
    if [[ ! -d "$SOURCE_DIR/bin" ]] || [[ ! -d "$SOURCE_DIR/scripts" ]]; then
        log_error "Build appears incomplete - missing essential directories"
        log_error "Please run 'python build/build.py' to rebuild the application"
        exit 1
    fi
    
    log_info "Source directory: $SOURCE_DIR"
    
    # Copy all files
    cp -r "$SOURCE_DIR"/* "$INSTALL_DIR/"
    
    # Set proper ownership
    chown -R root:root "$INSTALL_DIR"
    
    # Set execute permissions for binaries
    find "$INSTALL_DIR/bin" -type f -exec chmod +x {} \;
    find "$INSTALL_DIR/scripts" -type f -name "*.py" -exec chmod +x {} \;
    
    log_success "Files installed successfully"
}

# Fix SELinux contexts
fix_selinux() {
    if command -v getenforce >/dev/null 2>&1 && [[ "$(getenforce)" == "Enforcing" ]]; then
        log_info "SELinux detected - setting proper security contexts..."
        
        # Set proper contexts for executable files
        find "$INSTALL_DIR/bin" -type f -exec chcon -t bin_t {} \; 2>/dev/null || true
        restorecon -R "$INSTALL_DIR" 2>/dev/null || true
        
        log_success "SELinux contexts configured"
    fi
}

# Create launcher script
create_launcher() {
    log_info "Creating launcher script..."
    
    cat > "$BIN_DIR/snes-ide" << 'EOF'
#!/bin/bash
#
# SNES-IDE Launcher
#

INSTALL_DIR="/opt/snes-ide"

# Check if installation exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Error: SNES-IDE not found at $INSTALL_DIR"
    echo "Please reinstall SNES-IDE"
    exit 1
fi

# Launch SNES-IDE
cd "$INSTALL_DIR"
exec python3 snes-ide.py "$@"
EOF

    chmod +x "$BIN_DIR/snes-ide"
    log_success "Launcher created at $BIN_DIR/snes-ide"
}

# Create desktop entry
create_desktop_entry() {
    log_info "Creating desktop entry..."
    
    # Copy icon if it exists
    if [[ -f "$INSTALL_DIR/icon.png" ]]; then
        cp "$INSTALL_DIR/icon.png" "$ICON_DIR/snes-ide.png"
    fi
    
    cat > "$DESKTOP_DIR/snes-ide.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNES-IDE
Comment=Integrated Development Environment for SNES Game Development
Exec=snes-ide
Icon=snes-ide
Terminal=false
Categories=Development;IDE;
MimeType=text/plain;
Keywords=SNES;game;development;IDE;programming;
EOF

    chmod 644 "$DESKTOP_DIR/snes-ide.desktop"
    log_success "Desktop entry created"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    if [[ -f "$INSTALL_DIR/requirements.txt" ]]; then
        python3 -m pip install -r "$INSTALL_DIR/requirements.txt"
        log_success "Python dependencies installed"
    else
        log_warn "No requirements.txt found, skipping Python dependencies"
    fi
}

# Create uninstaller
create_uninstaller() {
    log_info "Creating uninstaller..."
    
    cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/bin/bash
#
# SNES-IDE Uninstaller
#

if [[ $EUID -ne 0 ]]; then
    echo "Error: Uninstaller must be run as root (use sudo)"
    exit 1
fi

echo "Uninstalling SNES-IDE..."

# Remove files
rm -rf "/opt/snes-ide"
rm -f "/usr/local/bin/snes-ide"
rm -f "/usr/share/applications/snes-ide.desktop"
rm -f "/usr/share/pixmaps/snes-ide.png"

echo "SNES-IDE has been uninstalled successfully"
EOF

    chmod +x "$INSTALL_DIR/uninstall.sh"
    log_success "Uninstaller created at $INSTALL_DIR/uninstall.sh"
}

# Main installation function
main() {
    echo "============================================"
    echo "           SNES-IDE Linux Installer        "
    echo "============================================"
    echo
    
    check_root
    check_prerequisites
    detect_distro
    install_dependencies
    create_install_dir
    install_files
    fix_selinux
    create_launcher
    create_desktop_entry
    install_python_deps
    create_uninstaller
    
    echo
    log_success "SNES-IDE has been installed successfully!"
    echo
    echo "You can now run SNES-IDE by:"
    echo "  1. Running 'snes-ide' from the terminal"
    echo "  2. Finding it in your applications menu"
    echo
    echo "To uninstall, run: sudo $INSTALL_DIR/uninstall.sh"
    echo
    echo "============================================"
}

# Run main function
main "$@"