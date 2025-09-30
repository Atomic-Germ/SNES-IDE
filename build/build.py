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

        # For POSIX builds, ensure shipped Python scripts are executable and
        # contain a proper shebang so users can run them directly.
        if file.suffix == ".py" and platform.system().lower() != "windows":
            dest = SNESIDEOUT / file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Prepend a portable shebang while preserving file contents
            try:
                with open(file, "rb") as srcf, open(dest, "wb") as dstf:
                    dstf.write(b"#!/usr/bin/env python3\n")
                    dstf.write(srcf.read())
                try:
                    dest.chmod(dest.stat().st_mode | 0o111)
                except Exception:
                    pass
                print_step(f"Copied python script with shebang: {file} -> {dest}")
            except Exception:
                # Fallback to plain copy on error
                shutil.copy(file, SNESIDEOUT / file.name)
        else:
            shutil.copy(file, SNESIDEOUT / file.name)
    
    return None


def copy_lib() -> None:
    """
    Copy all files from the lib directory to the SNES-IDE-out directory.
    Also downloads and unpacks the correct pvsneslib release for the platform into libs/pvsneslib/.
    Extracts full directories: lib, devkitsnes/bin, devkitsnes/include, devkitsnes/tools.
    Also copies pvsneslib/pvsneslib_license.txt to libs/pvsneslib/LICENSE.
    Prints debug info for every extracted and copied file.
    Handles double pvsneslib prefix in zip members.
    """
    def strip_prefix(member, prefixes):
        for prefix in prefixes:
            if member.startswith(prefix):
                return Path(member[len(prefix):])
        return None

    sys_platform = platform.system().lower()
    if sys_platform == "darwin":
        url = "https://github.com/alekmaul/pvsneslib/releases/download/4.4.0/pvsneslib_440_64b_darwin.zip"
    elif sys_platform == "linux":
        url = "https://github.com/alekmaul/pvsneslib/releases/download/4.4.0/pvsneslib_440_64b_linux.zip"
    elif sys_platform == "windows":
        url = "https://github.com/alekmaul/pvsneslib/releases/download/4.4.0/pvsneslib_440_64b_windows.zip"
    else:
        print_fail(f"Unsupported platform: {sys_platform}")
        return None

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "pvsneslib.zip"
        print_step(f"Downloading pvsneslib for {sys_platform}...")
        urllib.request.urlretrieve(url, zip_path)
        print_ok(f"Downloaded {url}")
        # Extract full directories and license
        with zipfile.ZipFile(zip_path, 'r') as z:
            for member in z.namelist():
                # Extract lib/
                rel_lib = strip_prefix(member, ["pvsneslib/lib/", "pvsneslib/pvsneslib/lib/"])
                if rel_lib is not None and not member.endswith("/"):
                    dest_path = SNESIDEOUT / "libs" / "pvsneslib" / "lib" / rel_lib
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                    print_step(f"Extracted from zip: {dest_path}")
                    continue
                # Extract devkitsnes/bin
                rel_bin = strip_prefix(member, ["pvsneslib/devkitsnes/bin/", "pvsneslib/pvsneslib/devkitsnes/bin/"])
                if rel_bin is not None and not member.endswith("/"):
                    dest_path = SNESIDEOUT / "libs" / "pvsneslib" / "devkitsnes" / "bin" / rel_bin
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                    print_step(f"Extracted from zip: {dest_path}")
                    continue
                # Extract devkitsnes/include
                rel_inc = strip_prefix(member, ["pvsneslib/devkitsnes/include/", "pvsneslib/pvsneslib/devkitsnes/include/"])
                if rel_inc is not None and not member.endswith("/"):
                    dest_path = SNESIDEOUT / "libs" / "pvsneslib" / "devkitsnes" / "include" / rel_inc
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                    print_step(f"Extracted from zip: {dest_path}")
                    continue
                # Extract devkitsnes/tools
                rel_tools = strip_prefix(member, ["pvsneslib/devkitsnes/tools/", "pvsneslib/pvsneslib/devkitsnes/tools/"])
                if rel_tools is not None and not member.endswith("/"):
                    dest_path = SNESIDEOUT / "libs" / "pvsneslib" / "tools" / rel_tools
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                    print_step(f"Extracted from zip: {dest_path}")
                    continue
                # Extract license
                if member.endswith("pvsneslib_license.txt"):
                    dest_path = SNESIDEOUT / "libs" / "pvsneslib" / "LICENSE"
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                    print_step(f"Extracted from zip: {dest_path}")
        print_ok("Unpacked pvsneslib lib, devkitsnes/bin, devkitsnes/include, devkitsnes/tools, and LICENSE into SNES-IDE-out/libs/pvsneslib/ and SNES-IDE-out/libs/pvsneskit/")

    # Also copy any local files from libs as before
    (SNESIDEOUT / 'libs').mkdir(exist_ok=True)
    for file in (ROOT / 'libs').rglob("*"):
        if file.is_dir():
            continue
        rel_path = file.relative_to(ROOT / 'libs')
        dest_path = SNESIDEOUT / 'libs' / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, dest_path)
        print_step(f"Copied local file: {file} -> {dest_path}")
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

def copy_bat() -> None:
    """
    Copy the bat files to the SNES-IDE-out directory.
    """

    (SNESIDEOUT / 'tools').mkdir(exist_ok=True)

    for file in (ROOT / 'src' / 'tools' ).rglob("*.bat"):

        if file.is_dir():

            continue

        rel_path = file.relative_to(ROOT / 'src' / 'tools')

        dest_path = SNESIDEOUT / 'tools' / rel_path

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy(file, dest_path)
    
    return None


def copy_sh() -> None:
    """
    Copy POSIX shell wrapper files (.sh) from src/tools to SNES-IDE-out/tools so
    macOS builds include the expected POSIX wrappers.
    """
    (SNESIDEOUT / 'tools').mkdir(exist_ok=True)

    for file in (ROOT / 'src' / 'tools').rglob("*.sh"):

        if file.is_dir():
            continue

        rel_path = file.relative_to(ROOT / 'src' / 'tools')
        dest_path = SNESIDEOUT / 'tools' / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, dest_path)
        try:
            dest_path.chmod(dest_path.stat().st_mode | 0o111)
        except Exception:
            pass
        print_step(f"Copied shell wrapper: {file} -> {dest_path}")
    return None


def copy_dlls() -> None:
    """
    Copy the dlls from tools dir (Windows only). On non-Windows targets this
    operation is skipped to avoid polluting macOS builds with Windows artifacts.
    """
    sys_platform = platform.system().lower()
    if sys_platform != 'windows':
        print_step("Skipping DLL copy: non-Windows target detected")
        return None

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

    src_dir = ROOT / "src"

    # Compile Python files

    import platform
    exe_ext = ".exe" if platform.system().lower() == "windows" else ""
    for file in src_dir.rglob("*.py"):
        rel_path = file.relative_to(src_dir)
        out_path = SNESIDEOUT / rel_path.with_suffix(exe_ext)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if len(sys.argv) > 1 and sys.argv[1] == "linux":
            # On Linux, copy the .py file and create a .bat file to call it with python
            py_out = SNESIDEOUT / rel_path
            py_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, py_out)
            bat_path = out_path.with_suffix(".bat")
            with open(bat_path, "w") as bat_file:
                bat_file.write(f'@echo off\npython "{Path(py_out).resolve().absolute()}" %*\n')
        elif len(sys.argv) > 1 and sys.argv[1] == "mac":
            # On macOS, copy the .py file and create a small executable shell shim that
            # runs the Python script using the system python3. This avoids invoking
            # Windows-specific PyInstaller paths in buildModules.buildPy.
            py_out = SNESIDEOUT / rel_path
            py_out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, py_out)
            # Create shim without extension to behave like an executable
            shim_path = out_path
            shim_path.parent.mkdir(parents=True, exist_ok=True)
            shim_content = (
                "#!/bin/sh\n"
                "SCRIPT_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
                f"exec python3 \"${{SCRIPT_DIR}}/{rel_path.name}\" \"$@\"\n"
            )
            with open(shim_path, "w") as shim_file:
                shim_file.write(shim_content)
            try:
                shim_path.chmod(shim_path.stat().st_mode | 0o111)
            except Exception:
                pass
            print_step(f"Created mac shim: {shim_path} -> {py_out}")
        else:
            from buildModules.buildPy import main as mpy
            out: int = mpy(file, out_path.parent)
            if out != 0:
                raise Exception(f"ERROR while compiling python files: -{abs(out)}")
            # PyInstaller wrapper already moves the executable to SNES-IDE-out
            if out_path.exists():
                print_step(f"PyInstaller output found: {out_path}")
            else:
                print_fail(f"Expected output not found: {out_path}")
                raise Exception(f"Expected output not found: {out_path}")
    sys.stdout.write("Success compiling Python files.\n")
    

def copyTracker() -> None:
    
    src_dir = ROOT / "src" / "tools" / "soundsnes" / "tracker"
    dest_dir = ROOT / "SNES-IDE-out" / "tools" / "soundsnes" / "tracker"
    
    shutil.copytree(src_dir, dest_dir)

def fetch_schismtracker() -> None:
    """
    Attempt to download a macOS SchismTracker release asset for tag 20250825 and
    install it into SNES-IDE-out. If no binary release asset is found, fetch the
    source archive for the tag and copy the source into SNES-IDE-out/libs/schismtracker/source
    so developers can build it manually.
    """
    sys_platform = platform.system().lower()
    if sys_platform != 'darwin':
        print_step("Skipping SchismTracker fetch: not running on macOS")
        return None

    candidates = [
        # Common asset name patterns used by releases
        "schismtracker-macos.zip",
        "schismtracker_mac.zip",
        "schismtracker-darwin.zip",
        "schismtracker-20250825-mac.zip",
        "schismtracker-20250825-macos.zip",
        # Fall back to the tag archive (source)
        "archive/refs/tags/20250825.zip",
    ]

    base_url = "https://github.com/schismtracker/schismtracker/releases/download/20250825/"
    got_binary = False

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in candidates:
            url = base_url + name if not name.startswith('archive') else f"https://github.com/schismtracker/schismtracker/{name}"
            try:
                zip_path = Path(tmpdir) / name.split('/')[-1]
                print_step(f"Attempting to download SchismTracker asset: {url}")
                urllib.request.urlretrieve(url, zip_path)
                print_ok(f"Downloaded {url}")
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(tmpdir)
                # Look for a macOS executable or .app inside extracted content
                extracted = Path(tmpdir)
                # prefer an executable named 'schismtracker' or an .app bundle
                found = False
                for p in extracted.rglob('*'):
                    if p.is_file() and (p.name.lower() == 'schismtracker' or p.suffix == '' and os.access(p, os.X_OK)):
                        dest = SNESIDEOUT / 'tools' / 'soundsnes' / 'tracker' / p.name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(p, dest)
                        try:
                            dest.chmod(dest.stat().st_mode | 0o111)
                        except Exception:
                            pass
                        print_step(f"Copied schismtracker binary: {dest}")
                        found = True
                        got_binary = True
                # also copy .app bundles if any
                for app in extracted.rglob('*.app'):
                    dest = SNESIDEOUT / 'tools' / 'soundsnes' / 'tracker' / app.name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(app, dest)
                    print_step(f"Copied schismtracker .app bundle: {dest}")
                    found = True
                    got_binary = True

                if found:
                    print_ok("SchismTracker binary found and installed.")
                    break
                else:
                    print_step(f"No obvious SchismTracker binary found in {url}; continuing to next candidate.")
            except Exception as e:
                print_step(f"Failed to download/extract {url}: {e}")
                continue

        if not got_binary:
            # As a fallback, copy the source archive for developers to build locally
            src_url = "https://github.com/schismtracker/schismtracker/archive/refs/tags/20250825.zip"
            try:
                zip_path = Path(tmpdir) / 'schismtracker-source.zip'
                print_step(f"Downloading SchismTracker source archive: {src_url}")
                urllib.request.urlretrieve(src_url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(tmpdir)
                # copy the top-level extracted folder into libs
                possible_dirs = [d for d in Path(tmpdir).iterdir() if d.is_dir()]
                if possible_dirs:
                    srcdir = possible_dirs[0]
                    dest = SNESIDEOUT / 'libs' / 'schismtracker' / 'source'
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(srcdir, dest)
                    print_ok(f"Copied SchismTracker source to {dest}")
                else:
                    print_fail("Unable to locate extracted SchismTracker source directory after download.")
            except Exception as e:
                print_fail(f"Failed to fetch SchismTracker release or source: {e}")
    return None

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
        ("Fetching SchismTracker release", fetch_schismtracker),
        ("Copying docs", copy_docs),
        ("Copying bat files", copy_bat),
        ("Copying sh files", copy_sh),
        ("Copying dlls", copy_dlls),
        ("Copying tracker", copyTracker),
        ("Compiling python files", compile),
    ]
    success = True
    failed_steps = []

    for step_name, step_func in steps:
        if not run_step(step_name, step_func):
            success = False
            failed_steps.append(step_name)

    print_summary(success, failed_steps)

    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())