"""
platform_utils.py - Cross-platform utilities for SNES-IDE
"""
import os
import platform
from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path


class Platform(Enum):
    """Supported platforms for SNES-IDE"""
    WINDOWS = "windows"
    MACOS = "darwin"
    LINUX = "linux"


class PlatformManager:
    """
    Manages platform-specific functionality and detection
    """
    
    def __init__(self):
        self._platform = self._detect_platform()
        self._platform_config = self._get_platform_config()
    
    def _detect_platform(self) -> Platform:
        """
        Detect the current platform reliably
        
        Returns:
            Platform enum value
        """
        system = platform.system().lower()
        
        # Primary detection method
        if system == "windows" or os.name == "nt":
            return Platform.WINDOWS
        elif system == "darwin":
            return Platform.MACOS
        elif system == "linux":
            return Platform.LINUX
        else:
            # Default fallback for Unix-like systems
            if os.name == "posix":
                return Platform.LINUX
            else:
                # Last resort fallback to Windows
                return Platform.WINDOWS
    
    def _get_platform_config(self) -> Dict[str, Any]:
        """
        Get platform-specific configuration
        
        Returns:
            Dictionary with platform-specific settings
        """
        configs = {
            Platform.WINDOWS: {
                'executable_extension': '.exe',
                'path_separator': '\\',
                'line_ending': '\r\n',
                'case_sensitive': False,
                'dotnet_subpath': 'dotnet-sdk-8.0.415-win-x64',
                'dotnet_executable': 'dotnet.exe',
                'make_executable': 'make.exe',
                'shell_command': 'cmd',
                'shell_args': ['/c'],
                'icon_extension': '.ico',
                'preferred_shell': 'cmd'
            },
            Platform.MACOS: {
                'executable_extension': '',
                'path_separator': '/',
                'line_ending': '\n',
                'case_sensitive': True,
                'dotnet_subpath': 'dotnet-sdk-8.0.415-osx-arm64',
                'dotnet_executable': 'dotnet',
                'make_executable': 'make',
                'shell_command': 'sh',
                'shell_args': ['-c'],
                'icon_extension': '.icns',
                'preferred_shell': 'zsh',
                'app_bundle_extension': '.app'
            },
            Platform.LINUX: {
                'executable_extension': '',
                'path_separator': '/',
                'line_ending': '\n',
                'case_sensitive': True,
                'dotnet_subpath': 'dotnet-sdk-8.0.415-linux-x64',
                'dotnet_executable': 'dotnet',
                'make_executable': 'make',
                'shell_command': 'sh',
                'shell_args': ['-c'],
                'icon_extension': '.png',
                'preferred_shell': 'bash'
            }
        }
        return configs[self._platform]
    
    @property
    def current_platform(self) -> Platform:
        """Get the current platform"""
        return self._platform
    
    @property
    def executable_extension(self) -> str:
        """Get the executable extension for current platform"""
        return self._platform_config['executable_extension']
    
    @property
    def path_separator(self) -> str:
        """Get the path separator for current platform"""
        return self._platform_config['path_separator']
    
    @property
    def line_ending(self) -> str:
        """Get the line ending for current platform"""
        return self._platform_config['line_ending']
    
    @property
    def case_sensitive(self) -> bool:
        """Check if filesystem is case sensitive"""
        return self._platform_config['case_sensitive']
    
    def is_windows(self) -> bool:
        """Check if running on Windows"""
        return self._platform == Platform.WINDOWS
    
    def is_macos(self) -> bool:
        """Check if running on macOS"""
        return self._platform == Platform.MACOS
    
    def is_linux(self) -> bool:
        """Check if running on Linux"""
        return self._platform == Platform.LINUX
    
    def is_unix_like(self) -> bool:
        """Check if running on Unix-like system (macOS or Linux)"""
        return self._platform in (Platform.MACOS, Platform.LINUX)
    
    def get_executable_name(self, base_name: str) -> str:
        """
        Get platform-appropriate executable name
        
        Args:
            base_name: Base executable name without extension
            
        Returns:
            Executable name with appropriate extension
        """
        return f"{base_name}{self.executable_extension}"
    
    def get_dotnet_path(self, bin_directory: Path) -> Path:
        """
        Get platform-specific .NET SDK path
        
        Args:
            bin_directory: Base bin directory containing dotnet
            
        Returns:
            Path to dotnet executable
        """
        dotnet_dir = bin_directory / "dotnet8" / self._platform_config['dotnet_subpath']
        return dotnet_dir / self._platform_config['dotnet_executable']
    
    def get_make_path(self, bin_directory: Path) -> Path:
        """
        Get platform-specific make executable path
        
        Args:
            bin_directory: Base bin directory containing make
            
        Returns:
            Path to make executable
        """
        make_dir = bin_directory / "make"
        return make_dir / self._platform_config['make_executable']
    
    def get_shell_command(self, command: str) -> list[str]:
        """
        Get platform-specific shell command
        
        Args:
            command: Command to execute in shell
            
        Returns:
            List of command components for subprocess
        """
        shell_cmd = self._platform_config['shell_command']
        shell_args = self._platform_config['shell_args']
        return [shell_cmd] + shell_args + [command]
    
    def get_icon_path(self, base_path: Path, icon_name: str = "icon") -> Optional[Path]:
        """
        Get platform-appropriate icon path
        
        Args:
            base_path: Base directory containing icons
            icon_name: Base name of icon file
            
        Returns:
            Path to platform-specific icon file, or None if not found
        """
        icon_extension = self._platform_config['icon_extension']
        icon_path = base_path / f"{icon_name}{icon_extension}"
        
        if icon_path.exists():
            return icon_path
        
        # Fallback to .png for all platforms
        fallback_path = base_path / f"{icon_name}.png"
        return fallback_path if fallback_path.exists() else None
    
    def normalize_path_case(self, path: Path) -> Path:
        """
        Normalize path case based on platform
        
        Args:
            path: Path to normalize
            
        Returns:
            Path with appropriate case normalization
        """
        if not self.case_sensitive:
            # On case-insensitive systems, use lowercase
            return Path(str(path).lower())
        return path
    
    def get_app_data_dir(self, app_name: str = "SNES-IDE") -> Path:
        """
        Get platform-appropriate application data directory
        
        Args:
            app_name: Name of the application
            
        Returns:
            Path to application data directory
        """
        if self.is_windows():
            return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / app_name
        elif self.is_macos():
            return Path.home() / "Library" / "Application Support" / app_name
        else:  # Linux and other Unix-like
            return Path.home() / ".local" / "share" / app_name
    
    def get_config_dir(self, app_name: str = "SNES-IDE") -> Path:
        """
        Get platform-appropriate configuration directory
        
        Args:
            app_name: Name of the application
            
        Returns:
            Path to configuration directory
        """
        if self.is_windows():
            return self.get_app_data_dir(app_name)
        elif self.is_macos():
            return Path.home() / "Library" / "Preferences" / app_name
        else:  # Linux and other Unix-like
            config_home = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
            return Path(config_home) / app_name


# Singleton instance for global use
platform_manager = PlatformManager()

# Convenience functions for backward compatibility
def get_platform() -> Platform:
    """Get the current platform"""
    return platform_manager.current_platform

def is_windows() -> bool:
    """Check if running on Windows"""
    return platform_manager.is_windows()

def is_macos() -> bool:
    """Check if running on macOS"""
    return platform_manager.is_macos()

def is_linux() -> bool:
    """Check if running on Linux"""
    return platform_manager.is_linux()

def is_unix_like() -> bool:
    """Check if running on Unix-like system"""
    return platform_manager.is_unix_like()
