"""
Cross-platform helper utilities for SNES-IDE scripts.
Centralizes common platform-specific behaviors

Functions:
- findExecutable(name) -> Optional[Path]
- runGetSnesIDEHome(cwd) -> Path
- runCmd(args, ...) -> CompletedProcess
- openPath(path, args) -> CompletedProcess | os.startfile fallback
- makeExecutableName(base) -> str

This makes launching scripts consistent across Windows, macOS and Linux.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import os
import platform
from pathlib import Path
from typing import Optional, Sequence, List, Union


def findExecutable(name: str) -> Optional[Path]:
    """Return a Path to an executable if found on PATH or at an explicit path.
    
    If `name` looks like a path (contains a path separator) and exists, it's
    returned resolved. Otherwise `shutil.which` is used. 
    
    On Windows we try name and name.exe.
    """
    if not name:
        return None

    p = Path(name)
    if p.exists() and p.is_file():
        return p.resolve()

    which = shutil.which(name)
    if which:
        return Path(which).resolve()

    if os.name == "nt":
        which = shutil.which(f"{name}.exe")
        if which:
            return Path(which).resolve()

    return None


def runGetSnesIDEHome(cwd: Optional[Path] = None, timeout: Optional[int] = None) -> Path:
    """Get the path from get-snes-ide-home

    Runs `get-snes-ide-home` or `get-snes-ide-home.exe` if either is in
    in the cwd or in the PATH. It calls without a shell andreturns the stdout as a Path.

    Raises FileNotFoundError if the helper wasn't found and subprocess.CalledProcessError
    if the helper ran but returned a non-zero exit code or no output.
    """
    exe_name = "get-snes-ide-home.exe" if os.name == "nt" else "get-snes-ide-home"

    candidates: List[Path] = []
    if cwd:
        candidates.append(Path(cwd) / exe_name)

    found = findExecutable(exe_name)
    if found:
        candidates.append(found)

    # Try each candidate in order and use the first that executes successfully
    checked = set()
    for c in candidates:
        if not c or c in checked:
            continue
        checked.add(c)
        if not c.exists():
            continue

        cmd = [str(c)]
        result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=False, timeout=timeout)
        if result.returncode != 0:
            # try next candidate
            continue

        out = result.stdout.strip()
        if not out:
            # invalid output
            continue

        return Path(out)

    raise FileNotFoundError(f"get-snes-ide-home helper not found (looked for {exe_name} in cwd={cwd} and on PATH)")


def runCmd(args: Sequence[Union[str, Path]], cwd: Optional[Path] = None, check: bool = True,
            capture_output: bool = False, text: bool = True, env: Optional[dict] = None,
            timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Run a command using an argv list with no shell.

    Converts Path objects to strings
    subprocess.CalledProcessError will be raised on non-zero exit.
    """
    argv: List[str] = [str(a) for a in args]
    return subprocess.run(argv, cwd=str(cwd) if cwd else None, check=check,
                          capture_output=capture_output, text=text, env=env,
                          timeout=timeout)


def openPath(path: Union[str, Path], args: Optional[Sequence[str]] = None,
              cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Opens a file or application in a cross-platform way.

    On Windows, when no args are provided prefer os.startfile for a simple
    open. If args are supplied fallback to executing directly.
    On macOS `open <path>`. If there are any arguments use `--args` to forward
    them.
    On Linux try xdg-open, or if args are present and the path is executable 
    execute it directly.
    """
    p = Path(path)
    arguments: List[str] = list(args) if args else []
    system = platform.system().lower()

    if system == "windows":
        if not arguments:
            try:
                os.startfile(str(p))  # type: ignore[attr-defined]
                return subprocess.CompletedProcess(args=[str(p)], returncode=0)
            except Exception:
                # fallthrough to running as a process
                pass

        cmd = [str(p)] + arguments
        return runCmd(cmd, cwd=cwd, check=check)

    if system == "darwin":
        # Use `open` to handle .app bundles. Forward args with --args when present.
        cmd = ["open", str(p)]
        if arguments:
            cmd += ["--args"] + arguments
        return runCmd(cmd, cwd=cwd, check=check)

    # linux / other unix-like
    if not arguments:
        # Prefer xdg-open for general open behavior when no args
        cmd = ["xdg-open", str(p)]
        return runCmd(cmd, cwd=cwd, check=check)

    # If args are present, try to execute the path directly
    cmd = [str(p)] + arguments
    return runCmd(cmd, cwd=cwd, check=check)


def makeExecutableName(base: str) -> str:
    """Return a platform-correct executable filename for a given base name.

    e.g.: makeExecutableName('get-snes-ide-home') -> 'get-snes-ide-home.exe' on Windows
    """
    return f"{base}.exe" if os.name == "nt" else base
