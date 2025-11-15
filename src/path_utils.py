"""
path_utils.py - Centralized path utilities for SNES-IDE cross-platform compatibility

This module implements the PathManager described in PATH_UTILS.md.
It provides a singleton `path_manager` for global path operations.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Union, Optional


class PathManager:
    """Central path manager for SNES-IDE that handles:
    - PyInstaller frozen vs script execution
    - Cross-platform executable naming
    - Resource path resolution
    - Tool path location
    """

    def __init__(self):
        # Detect if running as a PyInstaller bundle
        self._is_frozen = getattr(sys, "frozen", False)
        self._project_root = self._get_project_root()
        self._executable_dir = self._get_executable_directory()

    def _get_project_root(self) -> Path:
        """Get the project root directory.

        - In frozen mode, return the directory containing sys.executable.
        - Otherwise, walk upwards from this file's directory trying to find
          ``build/build.py`` as an indicator of the repository root.
        """
        if self._is_frozen:
            executable_path = Path(sys.executable).parent
            # If the executable is inside a SNES-IDE-out bundle, use it.
            if executable_path.name == "SNES-IDE-out":
                return executable_path
            return executable_path

        # Development mode: search upwards for build/build.py
        current = Path(__file__).resolve().parent
        # Safety net: avoid infinite loop by comparing to root
        while current != current.parent:
            if (current / "build" / "build.py").exists():
                return current
            current = current.parent
        # Fallback to the script directory
        return Path(__file__).resolve().parent

    def _get_executable_directory(self) -> Path:
        """Get directory containing executable; handles frozen and non-frozen."""
        if self._is_frozen:
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent

    @property
    def is_frozen(self) -> bool:
        """Check if running as PyInstaller frozen executable."""
        return self._is_frozen

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return self._project_root

    @property
    def executable_dir(self) -> Path:
        """Get the executable directory."""
        return self._executable_dir

    def executable_name(self, base_name: str) -> str:
        """Get platform-appropriate executable name.

        Args:
            base_name: Base name without extension (e.g., "get-snes-ide-home")

        Returns:
            Platform-specific executable name
        """
        if os.name == "nt":
            return f"{base_name}.exe"
        return base_name

    def get_tool_path(self, tool_name: str) -> Path:
        """Get full path to a tool executable.

        - Frozen bundles expect tools to be next to the executable.
        - Development mode expects tools to be in `src/scripts`.
        """
        if self._is_frozen:
            return self._executable_dir / self.executable_name(tool_name)
        scripts_dir = self._project_root / "src" / "scripts"
        return scripts_dir / self.executable_name(tool_name)

    def resource_path(self, relative_path: Union[str, Path]) -> Path:
        """Get absolute path to resources; works in dev and PyInstaller mode.

        The `relative_path` is interpreted relative to the project root.
        """
        if isinstance(relative_path, Path):
            rel = relative_path
        else:
            rel = Path(relative_path)
        return self._project_root / rel

    def get_libs_path(self) -> Path:
        """Get path to the libs directory."""
        return self.resource_path("libs")

    def get_bin_path(self) -> Path:
        """Get path to the bin directory."""
        return self.resource_path("bin")

    def get_docs_path(self) -> Path:
        """Get path to the docs directory."""
        return self.resource_path("docs")

    def get_build_output_path(self) -> Path:
        """Get path to the SNES-IDE-out directory (build outputs)."""
        return self._project_root / "SNES-IDE-out"

    def ensure_directory_exists(self, path: Union[str, Path]) -> Path:
        """Ensure directory exists, create if necessary.

        Returns the ensured Path object.
        """
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        return path_obj


# Singleton instance for global use
path_manager = PathManager()

__all__ = ["PathManager", "path_manager"]
