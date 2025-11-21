"""
Cross-platform path utilities for SNES-IDE

This module provides platform-agnostic path handling to ensure consistent behavior
across Windows, macOS, and Linux.
"""

import os
import sys
from pathlib import Path, PureWindowsPath, PurePosixPath
import platform


def get_platform() -> str:
    """Get the current platform name.
    
    Returns:
        str: 'windows', 'macos', or 'linux'
    """
    system = platform.system()
    if system == 'Windows':
        return 'windows'
    elif system == 'Darwin':
        return 'macos'
    else:
        return 'linux'


def normalize_path(path) -> str:
    """Convert any path format to the current platform's native format.
    
    Args:
        path: Path as string or Path object
        
    Returns:
        str: Path in platform-native format
    """
    if path is None:
        return None
    
    path_str = str(path)
    
    # Convert to Path object for normalization
    path_obj = Path(path_str)
    
    # Return as string using platform-native separators
    return str(path_obj)


def join_paths(*parts) -> str:
    """Join path components in a platform-safe way.
    
    Args:
        *parts: Path components
        
    Returns:
        str: Joined path with platform-native separators
    """
    if not parts:
        return ''
    
    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part
    
    return str(result)


def to_absolute_path(path) -> str:
    """Convert a path to absolute, resolving symlinks.
    
    Args:
        path: Path as string or Path object
        
    Returns:
        str: Absolute path
    """
    return str(Path(path).resolve())


def get_home_directory() -> str:
    """Get the user's home directory in a cross-platform way.
    
    Returns:
        str: Home directory path
    """
    return str(Path.home())


def get_executable_extension() -> str:
    """Get the executable extension for the current platform.
    
    Returns:
        str: '.exe' on Windows, '' on others
    """
    return '.exe' if get_platform() == 'windows' else ''


def is_windows() -> bool:
    """Check if running on Windows.
    
    Returns:
        bool: True if on Windows
    """
    return get_platform() == 'windows'


def is_macos() -> bool:
    """Check if running on macOS.
    
    Returns:
        bool: True if on macOS
    """
    return get_platform() == 'macos'


def is_linux() -> bool:
    """Check if running on Linux.
    
    Returns:
        bool: True if on Linux
    """
    return get_platform() == 'linux'


def get_snes_ide_home() -> str:
    """Get the SNES-IDE home directory (where the application is installed).
    
    Returns:
        str: SNES-IDE home directory path
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        base_path = Path(sys.executable).resolve().parent
    else:
        # Running as script
        base_path = Path(__file__).resolve().parent
    
    return str(base_path)


def get_snes_ide_resources() -> str:
    """Get the SNES-IDE resources directory.
    
    Returns:
        str: Path to resources directory
    """
    home = Path(get_snes_ide_home())
    
    if getattr(sys, 'frozen', False):
        # In frozen executable, resources are typically one level up
        resources = home.parent / 'resources'
    else:
        # In development, go up from src/
        resources = home.parent / 'resources'
    
    return str(resources)


def get_snes_ide_scripts() -> str:
    """Get the SNES-IDE scripts directory.
    
    Returns:
        str: Path to scripts directory
    """
    home = get_snes_ide_home()
    return join_paths(home, 'scripts')


def create_directory(path, exist_ok=True) -> str:
    """Create a directory with cross-platform support.
    
    Args:
        path: Directory path to create
        exist_ok: If True, don't raise error if directory exists
        
    Returns:
        str: Normalized path
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=exist_ok)
    return str(path_obj)


def ensure_path_exists(path) -> bool:
    """Ensure a path exists, creating it if necessary.
    
    Args:
        path: File or directory path
        
    Returns:
        bool: True if path exists or was created
    """
    path_obj = Path(path)
    if path_obj.is_file():
        return True
    
    if path_obj.is_dir():
        return True
    
    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def path_exists(path) -> bool:
    """Check if a path exists.
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if path exists
    """
    return Path(path).exists()


def is_file(path) -> bool:
    """Check if path points to a file.
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if path is a file
    """
    return Path(path).is_file()


def is_directory(path) -> bool:
    """Check if path points to a directory.
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if path is a directory
    """
    return Path(path).is_dir()


def get_filename(path) -> str:
    """Get just the filename from a path.
    
    Args:
        path: Full path
        
    Returns:
        str: Filename
    """
    return Path(path).name


def get_file_extension(path) -> str:
    """Get file extension.
    
    Args:
        path: File path
        
    Returns:
        str: Extension including dot (e.g., '.txt')
    """
    return Path(path).suffix


def get_parent_directory(path) -> str:
    """Get parent directory of a path.
    
    Args:
        path: Path
        
    Returns:
        str: Parent directory path
    """
    return str(Path(path).parent)
