#!/usr/bin/env python3
"""
pyinstaller_build_helper.py

Discover Tcl/Tk library locations and invoke PyInstaller with appropriate
--add-data arguments and hidden-imports so tkinter-based features are packaged
correctly on each platform.

Usage: python3 scripts/pyinstaller_build_helper.py --src <path> [--name automatizer] [--onefile]
"""
import argparse
import os
import shlex
import subprocess
import sys


def detect_tcl_tk_dirs():
    """Return a list of (src, dest) pairs to pass to PyInstaller --add-data.
    Dest is relative path inside the bundle where the files will be placed.
    """
    pairs = []

    # First, honor environment variables if the user set them
    tcl_env = os.environ.get('TCL_LIBRARY')
    tk_env = os.environ.get('TK_LIBRARY')
    if tcl_env:
        pairs.append((tcl_env, 'tcl'))
    if tk_env and tk_env != tcl_env:
        pairs.append((tk_env, 'tk'))

    # Try to use tkinter to probe the Tcl 'library' dir without requiring a display
    try:
        import tkinter
        # Use tkinter.Tcl() so we don't create a window
        t = tkinter.Tcl()
        tcl_lib = t.eval('info library')
        if tcl_lib and os.path.exists(tcl_lib):
            if not any(src == tcl_lib for src, _ in pairs):
                pairs.append((tcl_lib, 'tcl'))
    except Exception:
        # If tkinter is not installed or probing failed, continue; we'll log later
        pass

    # On macOS/Homebrew, common installation lives under /opt/homebrew/Cellar/tcl-tk
    if sys.platform == 'darwin':
        homebrew_base = '/opt/homebrew/Cellar/tcl-tk'
        if os.path.isdir(homebrew_base):
            # pick the latest version dir if present
            versions = sorted(os.listdir(homebrew_base), reverse=True)
            if versions:
                candidate = os.path.join(homebrew_base, versions[0], 'lib', 'tcl8')
                if os.path.isdir(candidate):
                    if not any(src == candidate for src, _ in pairs):
                        pairs.append((candidate, 'tcl'))

    # Windows Python installations keep tcl/tk under the Python installation directory
    if sys.platform == 'win32':
        # attempt to locate using sys.prefix
        candidate = os.path.join(sys.prefix, 'tcl')
        if os.path.isdir(candidate):
            if not any(src == candidate for src, _ in pairs):
                pairs.append((candidate, 'tcl'))

    return pairs


def build_pyinstaller_cmd(src, name, onefile=True, debug=False):
    cmd = [sys.executable, '-m', 'PyInstaller']
    if onefile:
        cmd.append('--onefile')
    cmd += ['--name', name]

    # Hidden imports to ensure tkinter modules are discovered
    hidden_imports = [
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ]
    for hi in hidden_imports:
        cmd += ['--hidden-import', hi]

    # Discover tcl/tk library dirs and add them as data
    pairs = detect_tcl_tk_dirs()
    if not pairs and not debug:
        print('Warning: could not detect Tcl/Tk libraries automatically; the packaged binary may fail at runtime if tkinter is used.')

    for src_dir, dest in pairs:
        # PyInstaller expects different separators between SRC and DEST on Windows vs POSIX
        sep = ';' if os.name == 'nt' else ':'
        add_data = f"{src_dir}{sep}{dest}"
        cmd += ['--add-data', add_data]

    # Add manifest-like files or other binaries if needed in future

    # Final target
    cmd.append(src)
    return cmd


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--src', required=True, help='Path to Python entrypoint (automatizer.py)')
    p.add_argument('--name', default='automatizer', help='Name of the output binary')
    p.add_argument('--onefile', action='store_true', help='Create a onefile binary (default)')
    p.add_argument('--debug', action='store_true', help='Add extra logging and do not warn on missing tcl/tk')
    args = p.parse_args(argv)

    src = args.src
    name = args.name

    if not os.path.exists(src):
        print(f'Error: src entrypoint {src} does not exist')
        return 2

    cmd = build_pyinstaller_cmd(src, name, onefile=args.onefile or True, debug=args.debug)
    print('Running PyInstaller with command:')
    print(' '.join(shlex.quote(x) for x in cmd))

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print('PyInstaller build failed with exit code', e.returncode)
        return e.returncode

    print('PyInstaller build finished successfully')
    return 0


if __name__ == '__main__':
    sys.exit(main())
