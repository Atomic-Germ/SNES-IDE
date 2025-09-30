"""
Utility to resolve platform-specific binary names.

Functions:
- platform_bin_name(name): Map a Windows-style filename (ending with .exe)
  to the appropriate platform-specific filename. On Windows, returns the
  original name. On POSIX (macOS/Linux) strips the .exe suffix.

This small module centralizes platform-aware filename logic so the rest
of the codebase can remain platform-agnostic while preserving Windows
defaults for repo-wide compatibility.
"""
from __future__ import annotations

import platform
from pathlib import Path


def platform_bin_name(name: str) -> str:
    """Return the platform-appropriate filename for `name`.

    - Windows: return name unchanged.
    - POSIX: strip a trailing .exe (if present).
    """
    sys_platform = platform.system().lower()
    if sys_platform == "windows":
        return name
    # Strip .exe for POSIX platforms
    if name.lower().endswith(".exe"):
        return name[:-4]
    return name


def platform_bin_path(base: Path, name: str) -> Path:
    """Resolve a platform-aware Path under `base` for `name`.

    Example: platform_bin_path(devkit_dir / 'bin', '816-tcc.exe')
    will yield devkit_dir/bin/816-tcc.exe on Windows and devkit_dir/bin/816-tcc
    on macOS/Linux.
    """
    return base / platform_bin_name(name)
