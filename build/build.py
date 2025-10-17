#!/usr/bin/env python3
# This script is used to build the project.

from pathlib import Path
import traceback
import sys
import shutil as pyshutil
import os
import locale
import platform
import urllib.request
import zipfile
import tarfile
import json
from typing import Dict, List, Optional

# This is just to make the CI prettier
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_OK = Fore.GREEN + Style.BRIGHT
    COLOR_FAIL = Fore.RED + Style.BRIGHT
    COLOR_STEP = Fore.CYAN + Style.BRIGHT
    COLOR_RESET = Style.RESET_ALL
except ImportError:
    COLOR_OK = COLOR_FAIL = COLOR_STEP = COLOR_RESET = ""

def _supports_unicode():
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        encoding = locale.getpreferredencoding(False)
    try:
        "✔".encode(encoding)
        "✖".encode(encoding)
        return True
    except Exception:
        return False

USE_UNICODE = _supports_unicode()

OK_SYMBOL = "✔" if USE_UNICODE else "[OK]"
FAIL_SYMBOL = "✖" if USE_UNICODE else "[FAIL]"
STEP_SYMBOL = "==>"  # Always ASCII

def print_step(msg):
    print(f"{COLOR_STEP}{STEP_SYMBOL} {msg}{COLOR_RESET}")

def print_ok(msg):
    print(f"{COLOR_OK}{OK_SYMBOL} {msg}{COLOR_RESET}")

def print_fail(msg):
    print(f"{COLOR_FAIL}{FAIL_SYMBOL} {msg}{COLOR_RESET}")

def print_summary(success, failed_steps):
    print("\n" + "="*40)
    if success:
        print_ok("BUILD SUCCESSFUL")
    else:
        print_fail("BUILD FAILED")
        print_fail(f"Failed steps: {', '.join(failed_steps)}")
    print("="*40 + "\n")


# Tool manifest for platform-specific downloads
TOOL_MANIFEST = {
    # Note: bsnes currently only provides Windows binaries via GitHub releases
    # For other platforms, users should install bsnes via their package manager
    "bsnes": {
        "description": "SNES emulator for testing games",
        "license": "GPLv3",
        "platforms": {
            "windows": {
                "url": "https://github.com/bsnes-emu/bsnes/releases/download/v115/bsnes_v115-windows.zip",
                "extract_path": "bsnes_v115-windows",
                "files": ["bsnes.exe", "Database/", "Firmware/", "Shaders/"]
            }
            # macOS and Linux users should install bsnes via package manager
        }
    },
    # pvsneslib provides cross-platform binaries
    "pvsneslib-tools": {
        "description": "SNES development tools from pvsneslib",
        "license": "MIT",
        "platforms": {
            "windows": {
                "url": "https://github.com/alekmaul/pvsneslib/releases/download/4.4.0/pvsneslib_440_64b_windows.zip",
                "extract_path": "pvsneslib",
                "files": ["devkitsnes/", "pvsneslib/"]
            },
            "macos": {
                "url": "https://github.com/alekmaul/pvsneslib/releases/download/4.4.0/pvsneslib_440_64b_darwin.zip",
                "extract_path": "pvsneslib",
                "files": ["devkitsnes/", "pvsneslib/"]
            },
            "linux": {
                "url": "https://github.com/alekmaul/pvsneslib/releases/download/4.4.0/pvsneslib_440_64b_linux.zip",
                "extract_path": "pvsneslib",
                "files": ["devkitsnes/", "pvsneslib/"]
            }
        }
    }
}


def download_and_extract_tool(tool_name: str, platform_name: str) -> bool:
    """
    Download and extract a tool for the specified platform.
    
    Args:
        tool_name: Name of the tool to download
        platform_name: Target platform ('windows', 'macos', 'linux')
        
    Returns:
        True if successful, False otherwise
    """
    if tool_name not in TOOL_MANIFEST:
        print_fail(f"Unknown tool: {tool_name}")
        return False
        
    tool_info = TOOL_MANIFEST[tool_name]
    if platform_name not in tool_info["platforms"]:
        print_fail(f"Tool {tool_name} not available for platform {platform_name}")
        return False
        
    platform_info = tool_info["platforms"][platform_name]
    url = platform_info["url"]
    extract_path = platform_info["extract_path"]
    
    print_step(f"Downloading {tool_name} for {platform_name}...")
    
    try:
        # Create temp directory for download
        temp_dir = Path("temp_download")
        temp_dir.mkdir(exist_ok=True)
        
        # Download the file
        filename = url.split("/")[-1]
        download_path = temp_dir / filename
        
        print(f"Downloading from: {url}")
        urllib.request.urlretrieve(url, download_path)
        
        # Extract the archive
        print(f"Extracting {filename}...")
        if filename.endswith(".zip"):
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        elif filename.endswith((".tar.gz", ".tgz")):
            with tarfile.open(download_path, 'r:gz') as tar_ref:
                tar_ref.extractall(temp_dir)
        else:
            print_fail(f"Unsupported archive format: {filename}")
            return False
            
        # Copy files to libs directory
        source_dir = temp_dir / extract_path
        if not source_dir.exists():
            print_fail(f"Expected extract path not found: {extract_path}")
            return False
            
        libs_dir = ROOT / 'libs'
        for file_pattern in platform_info["files"]:
            source_files = list(source_dir.glob(file_pattern))
            if not source_files:
                # Try as direct path
                direct_path = source_dir / file_pattern
                if direct_path.exists():
                    source_files = [direct_path]
                    
            for source_file in source_files:
                if source_file.is_file():
                    # Copy file
                    rel_path = source_file.relative_to(source_dir)
                    dest_path = libs_dir / extract_path / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    pyshutil.copy2(source_file, dest_path)
                elif source_file.is_dir():
                    # Copy directory
                    rel_path = source_file.relative_to(source_dir)
                    dest_dir = libs_dir / extract_path / rel_path
                    if dest_dir.exists():
                        pyshutil.rmtree(dest_dir)
                    pyshutil.copytree(source_file, dest_dir)
        
        # Cleanup
        # pyshutil.rmtree(temp_dir)  # Commented out for debugging
        
        print_ok(f"Successfully installed {tool_name} for {platform_name}")
        return True
        
    except Exception as e:
        print_fail(f"Failed to download/extract {tool_name}: {e}")
        return False


def get_current_platform() -> str:
    """
    Get the current platform name for tool downloads.
    
    Returns:
        Platform name ('windows', 'macos', 'linux')
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    else:
        return "linux"


class shutil:
    """Reimplementation of class shutil to avoid errors in Wine"""

    @staticmethod
    def copy(src: str|Path, dst: str|Path) -> None:
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        pyshutil.copy2(src, dst)

    @staticmethod
    def copytree(src: str|Path, dst: str|Path) -> None:
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        pyshutil.copytree(src, dst, dirs_exist_ok=True)

    @staticmethod
    def rmtree(path: str|Path) -> None:
        path = Path(path).resolve()
        pyshutil.rmtree(path)

    @staticmethod
    def move(src: str|Path, dst: str|Path) -> None:
        src, dst = map(lambda x: Path(x).resolve(), (src, dst))
        pyshutil.move(src, dst)

# Copy all files from root to the SNES-IDE-out directory

ROOT = Path(__file__).parent.parent.resolve().absolute()

SNESIDEOUT = ROOT / "SNES-IDE-out"

def clean_all() -> None:
    """
    Clean the SNES-IDE-out directory.
    """

    if SNESIDEOUT.exists():
        shutil.rmtree(SNESIDEOUT)

    return None


def copy_root() -> None:
    """
    Copy all files from the root directory to the SNES-IDE-out directory.
    """
    SNESIDEOUT.mkdir(exist_ok=True)

    for file in ROOT.glob("*"):

        if file.is_dir():

            continue

        shutil.copy(file, SNESIDEOUT / file.name)
    
    return None


def copy_lib() -> None:
    """
    Copy cross-platform libs and download platform-specific tools.
    """

    (SNESIDEOUT / 'libs').mkdir(exist_ok=True)
    
    current_platform = get_current_platform()
    print_step(f"Building for platform: {current_platform}")

    # Copy cross-platform files (headers, templates, etc.)
    cross_platform_dirs = ['include', 'libs', 'font', 'template', 'pvsneslib']
    
    for dir_name in cross_platform_dirs:
        src_dir = ROOT / 'libs' / dir_name
        if src_dir.exists():
            dest_dir = SNESIDEOUT / 'libs' / dir_name
            if dest_dir.exists():
                pyshutil.rmtree(dest_dir)
            pyshutil.copytree(src_dir, dest_dir)
    
    # Download platform-specific tools
    tools_to_download = ['pvsneslib-tools']  # bsnes only available for Windows
    
    for tool in tools_to_download:
        if not download_and_extract_tool(tool, current_platform):
            print_fail(f"Failed to download {tool}, falling back to bundled version if available")
            # Try to copy from existing libs if download failed
            src_dir = ROOT / 'libs' / tool.split('-')[0]  # Remove '-tools' suffix
            if src_dir.exists():
                dest_dir = SNESIDEOUT / 'libs' / tool.split('-')[0]
                if dest_dir.exists():
                    pyshutil.rmtree(dest_dir)
                pyshutil.copytree(src_dir, dest_dir)
                print_ok(f"Using bundled version of {tool}")
    
    # Handle bsnes separately (only Windows binaries available)
    if current_platform == "windows":
        if not download_and_extract_tool("bsnes", current_platform):
            # Fallback to bundled version
            src_dir = ROOT / 'libs' / 'bsnes'
            if src_dir.exists():
                dest_dir = SNESIDEOUT / 'libs' / 'bsnes'
                if dest_dir.exists():
                    pyshutil.rmtree(dest_dir)
                pyshutil.copytree(src_dir, dest_dir)
                print_ok("Using bundled version of bsnes")
    else:
        # For non-Windows platforms, copy the existing bsnes if available (for compatibility)
        # but document that it's Windows-only
        src_dir = ROOT / 'libs' / 'bsnes'
        if src_dir.exists():
            dest_dir = SNESIDEOUT / 'libs' / 'bsnes'
            if dest_dir.exists():
                pyshutil.rmtree(dest_dir)
            pyshutil.copytree(src_dir, dest_dir)
            print_step("Note: bsnes binaries are Windows-only. Install bsnes via your package manager on other platforms.")
    
    # Handle platform-specific tools that don't have automated downloads
    if current_platform == "windows":
        # Include Windows-specific tools
        windows_only_dirs = ['notepad++', 'M8TE']
        for dir_name in windows_only_dirs:
            src_dir = ROOT / 'libs' / dir_name
            if src_dir.exists():
                dest_dir = SNESIDEOUT / 'libs' / dir_name
                if dest_dir.exists():
                    pyshutil.rmtree(dest_dir)
                pyshutil.copytree(src_dir, dest_dir)
                print_ok(f"Included Windows tool: {dir_name}")
    else:
        # For non-Windows platforms, create placeholder files or skip
        print_step("Note: Notepad++ and M8TE are Windows-only tools and are not included in this build")
        print_step("Users should install these tools separately on their system")
        
        # Create a README file explaining the situation
        readme_content = """# Platform-Specific Tools

This SNES-IDE build does not include the following Windows-only tools:

## bsnes (SNES Emulator)
Used for testing SNES games. On non-Windows platforms:
- Install bsnes via your package manager:
  - macOS: `brew install bsnes`
  - Ubuntu/Debian: `sudo apt install bsnes`
  - Other Linux: Check your distribution's repositories
- Or use alternative emulators like Snes9x, Mesen-S

## Notepad++
A text editor used for SNES development. On non-Windows platforms:
- Install a local text editor (VS Code, Vim, Emacs, etc.)
- Configure it in SNES-IDE settings
- Or install Notepad++ via Wine/CrossOver if needed

## M8TE (Mode 3/7 Tile Editor)
A specialized tile editor for SNES graphics. On non-Windows platforms:
- Use alternative tile editors
- Run M8TE via Wine/CrossOver
- Or use web-based alternatives

These tools are included in Windows builds of SNES-IDE.
"""
        readme_path = SNESIDEOUT / 'libs' / 'PLATFORM_TOOLS_README.md'
        with open(readme_path, 'w') as f:
            f.write(readme_content)
    
    # Copy license files
    license_files = ['README.md']
    for license_file in license_files:
        src_file = ROOT / 'libs' / license_file
        if src_file.exists():
            pyshutil.copy2(src_file, SNESIDEOUT / 'libs' / license_file)
    
    return None


def copy_docs() -> None:
    """
    Copy the docs directory to the SNES-IDE-out directory.
    """

    (SNESIDEOUT / 'docs').mkdir(exist_ok=True)

    for file in (ROOT / 'docs').rglob("*"):

        if file.is_dir():
            continue

        rel_path = file.relative_to(ROOT / 'docs')
        dest_path = SNESIDEOUT / 'docs' / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, dest_path)
    
    return None


def copy_gh_pages() -> None:
    """
    Copy the gh-pages directory to the SNES-IDE-out directory.
    """

    (SNESIDEOUT / 'gh-pages').mkdir(exist_ok=True)

    for file in (ROOT / 'gh-pages').rglob("*"):

        if file.is_dir():
            continue

        rel_path = file.relative_to(ROOT / 'gh-pages')
        dest_path = SNESIDEOUT / 'gh-pages' / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, dest_path)
    
    return None


def copy_scripts() -> None:
    """
    Copy the script files (.bat or .sh) to the SNES-IDE-out directory.
    """

    (SNESIDEOUT / 'tools').mkdir(exist_ok=True)

    # Copy .scripts
    for pattern in ["*.bat", "*.sh"]:
        for file in (ROOT / 'src' / 'tools' ).rglob(pattern):

            if file.is_dir():
                continue

            rel_path = file.relative_to(ROOT / 'src' / 'tools')

            dest_path = SNESIDEOUT / 'tools' / rel_path

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy(file, dest_path)
    
    return None

def copy_dlls() -> None:
    """
    Copy the dlls from tools dir
    """

    (SNESIDEOUT / 'tools').mkdir(exist_ok=True)

    for file in (ROOT / 'tools').rglob("*.dll"):

        if file.is_dir():

            continue

        rel_path = file.relative_to(ROOT / 'tools')

        dest_path = SNESIDEOUT / 'tools' / rel_path

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy(file, dest_path)
    
    return None

def compile() -> None:
    """
    Compile the project.
    """

    import platform as pf

    src_dir = ROOT / "src"
    target_platform = sys.argv[1] if len(sys.argv) > 1 else "windows"
    host_platform = pf.system().lower()

    # Check for cross-compilation limitations
    if target_platform == "windows" and host_platform != "windows":
        print("Warning: Building Windows executables on non-Windows platform.")
        print("Windows executables should be built on Windows for best compatibility.")
        print("Falling back to copying Python files instead.")

    # Compile Python files
    for file in src_dir.rglob("*.py"):

        rel_path = file.relative_to(src_dir)
        py_out = SNESIDEOUT / rel_path
        py_out.parent.mkdir(parents=True, exist_ok=True)

        if target_platform in ["linux", "macos"]:
            # On Unix-like systems, copy the .py file and make it executable
            shutil.copy(file, py_out)
            # Make Python files executable on Unix systems
            import os
            os.chmod(py_out, 0o755)

        elif target_platform == "windows" and host_platform == "windows":
            # On Windows building for Windows, compile to .exe using PyInstaller
            out_path = SNESIDEOUT / rel_path.with_suffix(".exe")
            out_path.parent.mkdir(parents=True, exist_ok=True)

            from buildModules.buildPy import main as mpy

            out: int = mpy(file, out_path.parent)

            if out != 0:
                raise Exception(f"ERROR while compiling python files: -{abs(out)}")
        else:
            # Cross-platform or fallback: just copy Python files
            shutil.copy(file, py_out)
            if target_platform in ["linux", "macos"]:
                import os
                os.chmod(py_out, 0o755)

    # Copy installer scripts for the target platform
    if target_platform == "linux":
        installer_src = ROOT / "install-linux.sh"
        installer_dst = SNESIDEOUT / "install.sh"
        if installer_src.exists():
            shutil.copy(installer_src, installer_dst)
            import os
            os.chmod(installer_dst, 0o755)

    elif target_platform == "macos":
        installer_src = ROOT / "install-macos.sh"
        installer_dst = SNESIDEOUT / "install.sh"
        if installer_src.exists():
            shutil.copy(installer_src, installer_dst)
            import os
            os.chmod(installer_dst, 0o755)

    sys.stdout.write("Success compiling Python files.\n")
    
def copyTracker() -> None:
    
    src_dir = ROOT / "src" / "tools" / "soundsnes" / "tracker"
    dest_dir = ROOT / "SNES-IDE-out" / "tools" / "soundsnes" / "tracker"
    
    shutil.copytree(src_dir, dest_dir)

# Pretty formatting for CI logs
def run_step(step_name, func):
    print_step(f"{step_name}...")
    try:
        func()
        print_ok(f"{step_name} completed.")
        return True
    except Exception as e:
        print_fail(f"{step_name} failed: {e}")
        traceback.print_exception(e)
        return False

def main() -> int:
    """
    Main function to run the build process.
    """
    steps = [
        ("Cleaning SNES-IDE-out", clean_all),
        ("Copying root files", copy_root),
        ("Copying libs", copy_lib),
        ("Copying docs", copy_docs),
        ("Copying gh-pages", copy_gh_pages),
        ("Copying script files", copy_scripts),
        ("Copying dlls", copy_dlls),
        ("Copying tracker", copyTracker),
        ("Compiling python files", compile),
    ]
    failed_steps = []
    for name, func in steps:
        if not run_step(name, func):
            failed_steps.append(name)
    print_summary(len(failed_steps) == 0, failed_steps)
    return 0 if not failed_steps else -1

if __name__ == "__main__":
    """
    Run the main function.
    """
    sys.exit(main())