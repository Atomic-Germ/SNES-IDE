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
                'java_subpath': 'jdk8/jdk8/bin',
                'java_executable': 'java.exe',
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
                'java_subpath': 'jdk8/jdk8/zulu-8.jdk/Contents/Home/bin',
                'java_executable': 'java',
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
                'java_subpath': 'jdk8/jdk8/bin',
                'java_executable': 'java',
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
    
    def get_java_path(self, bin_directory: Path) -> Path:
        """
        Get platform-specific Java executable path
        
        Args:
            bin_directory: Base bin directory containing Java
            
        Returns:
            Path to java executable
        """
        java_dir = bin_directory / self._platform_config['java_subpath']
        return java_dir / self._platform_config['java_executable']
    
    def get_java_home(self, bin_directory: Path) -> Path:
        """
        Get platform-specific Java home directory path
        
        Args:
            bin_directory: Base bin directory containing Java
            
        Returns:
            Path to Java home bin directory
        """
        return bin_directory / self._platform_config['java_subpath']
    
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
    
    def get_relative_executable_path(self, base_name: str) -> str:
        """
        Get platform-appropriate relative executable path with correct separators
        
        Args:
            base_name: Base executable name without extension
            
        Returns:
            Relative path to executable (e.g., ".\\tool.exe" on Windows, "./tool" on Unix)
        """
        executable_name = self.get_executable_name(base_name)
        if self.is_windows():
            return f".\\{executable_name}"
        else:
            return f"./{executable_name}"
    
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
    
    def validate_project_name(self, name: str) -> bool:
        """
        Validate project name for cross-platform compatibility
        
        Args:
            name: Project name to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        
        if not name or len(name) == 0:
            return False
            
        # Check for valid characters (alphanumeric, underscore, hyphen)
        # Must start with letter or underscore (common programming convention)
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_-]*$', name):
            return False
        
        # Check platform-specific restrictions
        if self.is_windows():
            # Windows reserved names
            reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                       'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                       'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
            if name.upper() in reserved:
                return False
            
            # Windows doesn't allow paths > 260 chars by default
            # Leave room for template content
            if len(name) > 200:
                return False
                
        # Unix-like systems: avoid names starting with dot (hidden)
        elif name.startswith('.'):
            return False
            
        return True
    
    def get_template_path(self, template_subdir: str, snes_home: Path) -> Path:
        """
        Get platform-specific template path
        
        Args:
            template_subdir: Template subdirectory (e.g., "pvsneslib/template")
            snes_home: SNES-IDE home directory
            
        Returns:
            Path to template directory
        """
        return snes_home / "libs" / template_subdir
    
    def copy_template_safely(self, template_path: Path, target_path: Path, 
                           overwrite: bool = False) -> bool:
        """
        Copy template directory with cross-platform error handling
        
        Args:
            template_path: Source template directory
            target_path: Destination directory
            overwrite: Whether to overwrite existing directory
            
        Returns:
            True if successful, False otherwise
        """
        import shutil
        
        try:
            # Check if template exists
            if not template_path.exists():
                print(f"Template directory {template_path} does not exist")
                return False
                
            if not template_path.is_dir():
                print(f"Template path {template_path} is not a directory")
                return False
            
            # Handle existing target directory
            if target_path.exists():
                if not overwrite:
                    print(f"Target directory {target_path} already exists")
                    return False
                else:
                    # Remove existing directory
                    shutil.rmtree(target_path)
            
            # Create parent directories if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy template
            shutil.copytree(template_path, target_path)
            
            # Set appropriate permissions on Unix-like systems
            if self.is_unix_like():
                self._set_template_permissions(target_path)
                
            return True
            
        except PermissionError as e:
            print(f"Permission error copying template: {e}")
            return False
        except OSError as e:
            print(f"File system error copying template: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error copying template: {e}")
            return False
    
    def _set_template_permissions(self, target_path: Path):
        """Set appropriate permissions on template files for Unix systems"""
        import stat
        
        try:
            # Set directory permissions to 755 (rwxr-xr-x)
            for dir_path in target_path.rglob('*'):
                if dir_path.is_dir():
                    dir_path.chmod(0o755)
            
            # Set file permissions to 644 (rw-r--r--) for most files
            for file_path in target_path.rglob('*'):
                if file_path.is_file():
                    # Make build scripts executable (common extensions)
                    if file_path.suffix in {'.sh', '.py'} or file_path.name in {'Makefile'}:
                        file_path.chmod(0o755)  # rwxr-xr-x
                    else:
                        file_path.chmod(0o644)  # rw-r--r--
        except Exception as e:
            # Don't fail the entire operation for permission issues
            print(f"Warning: Could not set permissions: {e}")


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
