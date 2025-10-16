#!/usr/bin/env python3
# This script is used to build the project.

from pathlib import Path
import traceback
import sys
import shutil as pyshutil
import os
import locale

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
    Copy all files from the lib directory to the SNES-IDE-out directory.
    """

    (SNESIDEOUT / 'libs').mkdir(exist_ok=True)

    for file in (ROOT / 'libs').rglob("*"):

        if file.is_dir():
            continue

        rel_path = file.relative_to(ROOT / 'libs')
        dest_path = SNESIDEOUT / 'libs' / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, dest_path)
    
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