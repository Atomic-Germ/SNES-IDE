import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def _import_platform_utils_from_src():
    # Ensure src is on sys.path so imports work consistently when running pytest
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_import_platform_utils_from_src()

from platform_utils import PlatformManager, Platform, platform_manager
from platform_utils import get_platform, is_windows, is_macos, is_linux, is_unix_like


class TestPlatformDetection:
    """Test platform detection logic"""
    
    def test_windows_detection(self):
        """Test Windows platform detection"""
        with patch('platform.system', return_value='Windows'):
            with patch('os.name', 'nt'):
                manager = PlatformManager()
                assert manager.current_platform == Platform.WINDOWS
                assert manager.is_windows()
                assert not manager.is_macos()
                assert not manager.is_linux()
                assert not manager.is_unix_like()
    
    def test_macos_detection(self):
        """Test macOS platform detection"""
        with patch('platform.system', return_value='Darwin'):
            manager = PlatformManager()
            assert manager.current_platform == Platform.MACOS
            assert not manager.is_windows()
            assert manager.is_macos()
            assert not manager.is_linux()
            assert manager.is_unix_like()
    
    def test_linux_detection(self):
        """Test Linux platform detection"""
        with patch('platform.system', return_value='Linux'):
            manager = PlatformManager()
            assert manager.current_platform == Platform.LINUX
            assert not manager.is_windows()
            assert not manager.is_macos()
            assert manager.is_linux()
            assert manager.is_unix_like()
    
    def test_fallback_to_posix(self):
        """Test fallback to Linux for unknown POSIX systems"""
        with patch('platform.system', return_value='FreeBSD'):
            with patch('os.name', 'posix'):
                manager = PlatformManager()
                assert manager.current_platform == Platform.LINUX
    
    def test_fallback_to_windows(self):
        """Test fallback to Windows for unknown systems"""
        with patch('platform.system', return_value='Unknown'):
            with patch('os.name', 'unknown'):
                manager = PlatformManager()
                assert manager.current_platform == Platform.WINDOWS


class TestPlatformProperties:
    """Test platform-specific properties"""
    
    def test_windows_properties(self):
        """Test Windows-specific properties"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            
            assert manager.executable_extension == '.exe'
            assert manager.path_separator == '\\'
            assert manager.line_ending == '\r\n'
            assert manager.case_sensitive == False
    
    def test_macos_properties(self):
        """Test macOS-specific properties"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.MACOS):
            manager._platform_config = manager._get_platform_config()
            
            assert manager.executable_extension == ''
            assert manager.path_separator == '/'
            assert manager.line_ending == '\n'
            assert manager.case_sensitive == True
    
    def test_linux_properties(self):
        """Test Linux-specific properties"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            
            assert manager.executable_extension == ''
            assert manager.path_separator == '/'
            assert manager.line_ending == '\n'
            assert manager.case_sensitive == True


class TestExecutableNaming:
    """Test executable name generation"""
    
    def test_windows_executable_name(self):
        """Test Windows executable naming"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            assert manager.get_executable_name("test") == "test.exe"
            assert manager.get_executable_name("get-snes-ide-home") == "get-snes-ide-home.exe"
    
    def test_unix_executable_name(self):
        """Test Unix executable naming"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            assert manager.get_executable_name("test") == "test"
            assert manager.get_executable_name("get-snes-ide-home") == "get-snes-ide-home"


class TestPathResolution:
    """Test platform-specific path resolution"""
    
    def test_dotnet_path_windows(self):
        """Test .NET path resolution on Windows"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            bin_dir = Path("/test/bin")
            dotnet_path = manager.get_dotnet_path(bin_dir)
            
            assert "dotnet-sdk-8.0.415-win-x64" in str(dotnet_path)
            assert str(dotnet_path).endswith("dotnet.exe")
    
    def test_dotnet_path_macos(self):
        """Test .NET path resolution on macOS"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.MACOS):
            manager._platform_config = manager._get_platform_config()
            bin_dir = Path("/test/bin")
            dotnet_path = manager.get_dotnet_path(bin_dir)
            
            assert "dotnet-sdk-8.0.415-osx-arm64" in str(dotnet_path)
            assert str(dotnet_path).endswith("dotnet")
    
    def test_dotnet_path_linux(self):
        """Test .NET path resolution on Linux"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            bin_dir = Path("/test/bin")
            dotnet_path = manager.get_dotnet_path(bin_dir)
            
            assert "dotnet-sdk-8.0.415-linux-x64" in str(dotnet_path)
            assert str(dotnet_path).endswith("dotnet")
    
    def test_make_path(self):
        """Test make executable path resolution"""
        manager = PlatformManager()
        bin_dir = Path("/test/bin")
        
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            make_path = manager.get_make_path(bin_dir)
            assert str(make_path).endswith("make.exe")
        
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            make_path = manager.get_make_path(bin_dir)
            assert str(make_path).endswith("make")


class TestShellCommands:
    """Test shell command generation"""
    
    def test_windows_shell_command(self):
        """Test Windows shell command generation"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            cmd = manager.get_shell_command("echo Hello")
            assert cmd == ["cmd", "/c", "echo Hello"]
    
    def test_unix_shell_command(self):
        """Test Unix shell command generation"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            cmd = manager.get_shell_command("echo Hello")
            assert cmd == ["sh", "-c", "echo Hello"]


class TestIconResolution:
    """Test icon path resolution"""
    
    def test_icon_path_exists(self, tmp_path):
        """Test icon resolution when platform-specific icon exists"""
        manager = PlatformManager()
        
        # Create a test icon file
        icon_dir = tmp_path / "icons"
        icon_dir.mkdir()
        (icon_dir / "icon.png").touch()
        
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            icon_path = manager.get_icon_path(icon_dir)
            assert icon_path == icon_dir / "icon.png"
    
    def test_icon_path_fallback(self, tmp_path):
        """Test icon fallback to PNG when platform-specific doesn't exist"""
        manager = PlatformManager()
        
        icon_dir = tmp_path / "icons"
        icon_dir.mkdir()
        (icon_dir / "icon.png").touch()
        
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            # Windows looks for .ico, but only .png exists
            icon_path = manager.get_icon_path(icon_dir)
            assert icon_path == icon_dir / "icon.png"
    
    def test_icon_path_not_found(self, tmp_path):
        """Test icon resolution returns None when no icon exists"""
        manager = PlatformManager()
        
        icon_dir = tmp_path / "icons"
        icon_dir.mkdir()
        
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            icon_path = manager.get_icon_path(icon_dir)
            assert icon_path is None


class TestPathNormalization:
    """Test path case normalization"""
    
    def test_case_sensitive_normalization(self):
        """Test path normalization on case-sensitive systems"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            path = Path("/Test/Path")
            normalized = manager.normalize_path_case(path)
            assert normalized == path  # Should remain unchanged
    
    def test_case_insensitive_normalization(self):
        """Test path normalization on case-insensitive systems"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            path = Path("/Test/Path")
            normalized = manager.normalize_path_case(path)
            assert str(normalized).lower() == str(path).lower()


class TestDirectoryResolution:
    """Test application directory resolution"""
    
    def test_windows_app_data_dir(self):
        """Test Windows app data directory"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            with patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
                app_dir = manager.get_app_data_dir()
                # Path normalizes to forward slashes on non-Windows systems
                assert "AppData" in str(app_dir) and "SNES-IDE" in str(app_dir)
    
    def test_macos_app_data_dir(self):
        """Test macOS app data directory"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.MACOS):
            manager._platform_config = manager._get_platform_config()
            with patch('pathlib.Path.home', return_value=Path('/Users/test')):
                app_dir = manager.get_app_data_dir()
                assert str(app_dir) == "/Users/test/Library/Application Support/SNES-IDE"
    
    def test_linux_app_data_dir(self):
        """Test Linux app data directory"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            with patch('pathlib.Path.home', return_value=Path('/home/test')):
                app_dir = manager.get_app_data_dir()
                assert str(app_dir) == "/home/test/.local/share/SNES-IDE"
    
    def test_linux_config_dir_xdg(self):
        """Test Linux config directory with XDG_CONFIG_HOME"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': '/custom/config'}):
                config_dir = manager.get_config_dir()
                assert str(config_dir) == "/custom/config/SNES-IDE"
    
    def test_linux_config_dir_default(self):
        """Test Linux config directory without XDG_CONFIG_HOME"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            with patch('pathlib.Path.home', return_value=Path('/home/test')):
                with patch.dict(os.environ, {}, clear=True):
                    config_dir = manager.get_config_dir()
                    assert str(config_dir) == "/home/test/.config/SNES-IDE"


class TestConvenienceFunctions:
    """Test module-level convenience functions"""
    
    def test_get_platform(self):
        """Test get_platform convenience function"""
        platform_type = get_platform()
        assert isinstance(platform_type, Platform)
    
    def test_is_functions(self):
        """Test is_* convenience functions"""
        # At least one should be True
        platforms = [is_windows(), is_macos(), is_linux()]
        assert any(platforms)
        
        # Exactly one should be True
        assert sum(platforms) == 1
        
        # is_unix_like should match macos or linux
        assert is_unix_like() == (is_macos() or is_linux())


class TestSingletonInstance:
    """Test that platform_manager singleton works correctly"""
    
    def test_singleton_exists(self):
        """Test that platform_manager singleton is available"""
        assert platform_manager is not None
        assert isinstance(platform_manager, PlatformManager)
    
    def test_singleton_consistency(self):
        """Test that singleton maintains consistent state"""
        platform1 = platform_manager.current_platform
        platform2 = platform_manager.current_platform
        assert platform1 == platform2
