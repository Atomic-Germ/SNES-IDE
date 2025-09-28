"""Platform bridge utilities

Lightweight helpers for locating platform-native external artifacts (bsnes emulator,
preferred editor CLI) and a guarded helper for fetching official release artifacts
in CI (only when explicitly enabled via an environment variable).

This module is intentionally conservative: it will not perform any network fetches
unless the environment variable `SNES_IDE_CI_AUTO_FETCH` is set to a truthy value
and the code is running in a CI environment (detected via `GITHUB_ACTIONS`).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional

REPO_BSNES_API = "https://api.github.com/repos/bsnes-emu/bsnes/releases/latest"


def platform_name() -> str:
    """Return a normalized platform name like 'darwin', 'linux', or 'windows'."""
    return platform.system().lower()


def _is_executable_file(p: Path) -> bool:
    try:
        return p.is_file() and os.access(p, os.X_OK)
    except Exception:
        return False


def find_emulator() -> Optional[Path]:
    """Find a platform-appropriate bsnes emulator binary.

    Search order:
    1. Environment override via `SNES_IDE_BSNES_PATH` (file or directory).
    2. System PATH for an installed `bsnes` binary.
    3. Per-platform library locations under `libs/bsnes/<platform>/`.

    Returns a Path to an executable file if found, otherwise None.
    """
    env_override = os.environ.get("SNES_IDE_BSNES_PATH")
    if env_override:
        p = Path(env_override)
        if p.exists():
            if p.is_dir():
                # look for an executable inside the directory
                for child in p.iterdir():
                    if _is_executable_file(child):
                        return child
            elif _is_executable_file(p):
                return p

    # check PATH
    which_bsnes = shutil.which("bsnes")
    if which_bsnes:
        return Path(which_bsnes)

    sysname = platform.system()
    base = Path("libs") / "bsnes"
    if sysname == "Windows":
        candidate = base / "bsnes.exe"
        if candidate.exists():
            return candidate
    elif sysname == "Darwin":
        macdir = base / "mac"
        # common macOS bundles may be .app directories; also consider single executables
        if macdir.exists():
            # Find .app bundles first
            for p in macdir.glob("*.app"):
                # the typical executable lives in Contents/MacOS/*
                exe = p / "Contents" / "MacOS"
                if exe.exists():
                    for e in exe.iterdir():
                        if _is_executable_file(e):
                            return e
            # Fallback: any executable file inside the macdir
            for p in macdir.rglob("*"):
                if _is_executable_file(p):
                    return p
    else:  # Linux and others
        lndir = base / "linux"
        if lndir.exists():
            for p in lndir.rglob("*"):
                if _is_executable_file(p):
                    return p

    return None


def detect_editor() -> Optional[str]:
    """Detect a preferred editor command on the current platform.

    Preference order:
    - Visual Studio Code 'code'
    - Sublime 'subl'
    - TextMate 'mate'
    - native macOS 'open'
    - fall back to command-line editors 'nano'/ 'vi'

    Returns the CLI command name or None if nothing appropriate found.
    """
    candidates = ["code", "subl", "mate", "open", "nano", "vi"]
    for cmd in candidates:
        if shutil.which(cmd):
            return cmd
    return None


def running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "false").lower() == "true"


def _download_url_to(path: Path, url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as r:
        # simple write; for large files consider streaming
        data = r.read()
    path.write_bytes(data)


def ci_fetch_latest_bsnes_mac(dest_dir: Path) -> Optional[Path]:
    """CI-only helper that attempts to download the latest bsnes macOS release asset.

    This function will only perform network activity when all of the following are true:
    - running_in_github_actions() is True; and
    - environment variable `SNES_IDE_CI_AUTO_FETCH` is set to a truthy value (e.g., '1' or 'true').

    The fetched artifact is saved to `dest_dir` (a directory). The function returns
    the path to the downloaded archive or to the first extracted executable if successful,
    otherwise None.
    """
    if not running_in_github_actions():
        return None
    if os.environ.get("SNES_IDE_CI_AUTO_FETCH", "0").lower() not in ("1", "true", "yes"):
        return None

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(REPO_BSNES_API) as r:
            data = json.load(r)
        assets = data.get("assets", [])
        url = None
        for a in assets:
            name = (a.get("name") or "").lower()
            if "macos" in name or "bsnes-macos" in name:
                url = a.get("browser_download_url")
                break
        if not url:
            # Fallback to the documented nightly URL — best-effort
            url = "https://github.com/bsnes-emu/bsnes/releases/download/nightly/bsnes-macos.zip"

        out_archive = dest_dir / "bsnes-macos.zip"
        _download_url_to(out_archive, url)

        # Try to extract using Python zipfile (avoid shell dependencies)
        try:
            import zipfile

            with zipfile.ZipFile(out_archive, "r") as z:
                z.extractall(dest_dir)
            # locate first executable
            for p in dest_dir.rglob("*"):
                if _is_executable_file(p):
                    return p
        except Exception:
            # If extraction fails, leave the archive in place as the artifact
            return out_archive

    except Exception:
        return None

    return None


if __name__ == "__main__":
    # Quick manual smoke tests when run directly
    print("Platform:", platform_name())
    print("Emulator:", find_emulator())
    print("Editor:", detect_editor())
    # In CI you can enable auto-fetch via: export SNES_IDE_CI_AUTO_FETCH=1
    if os.environ.get("SNES_IDE_CI_AUTO_FETCH"):
        print("Attempting CI fetch of bsnes...")
        p = ci_fetch_latest_bsnes_mac(Path("libs/bsnes/mac"))
        print("Fetched:", p)
