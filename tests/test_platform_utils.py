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
    
    def test_windows_relative_executable_path(self):
        """Test Windows relative executable path generation"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            assert manager.get_relative_executable_path("get-snes-ide-home") == ".\\get-snes-ide-home.exe"
            assert manager.get_relative_executable_path("make") == ".\\make.exe"
    
    def test_unix_relative_executable_path(self):
        """Test Unix relative executable path generation"""
        manager = PlatformManager()
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            assert manager.get_relative_executable_path("get-snes-ide-home") == "./get-snes-ide-home"
            assert manager.get_relative_executable_path("make") == "./make"


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
    
    def test_java_path(self):
        """Test Java executable path resolution"""
        manager = PlatformManager()
        bin_dir = Path("/test/bin")
        
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            java_path = manager.get_java_path(bin_dir)
            assert str(java_path).endswith("java.exe")
            assert "jdk8" in str(java_path)
        
        with patch.object(manager, '_platform', Platform.MACOS):
            manager._platform_config = manager._get_platform_config()
            java_path = manager.get_java_path(bin_dir)
            assert str(java_path).endswith("java")
            assert "zulu-8.jdk/Contents/Home/bin" in str(java_path)
        
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            java_path = manager.get_java_path(bin_dir)
            assert str(java_path).endswith("java")
            assert "jdk8" in str(java_path)


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


class TestProjectCreationUtilities:
    """Test project creation utilities"""
    
    def test_validate_project_name_valid(self):
        """Test valid project names"""
        manager = PlatformManager()
        
        valid_names = [
            "MyProject",
            "my_project", 
            "Project123",
            "_private_project",
            "Project-Name",
            "a",  # Single character
            "A",  # Single uppercase
            "_",  # Single underscore
        ]
        
        for name in valid_names:
            assert manager.validate_project_name(name), f"'{name}' should be valid"
    
    def test_validate_project_name_invalid(self):
        """Test invalid project names"""
        manager = PlatformManager()
        
        invalid_names = [
            "",  # Empty string
            "123project",  # Starts with number
            "-project",  # Starts with hyphen
            "project with spaces",  # Contains spaces
            "project/with/slashes",  # Contains slashes
            "project\\with\\backslashes",  # Contains backslashes
            "project.name",  # Contains dot
            "project@name",  # Contains special char
            ".hidden",  # Starts with dot (Unix hidden)
        ]
        
        for name in invalid_names:
            assert not manager.validate_project_name(name), f"'{name}' should be invalid"
    
    def test_validate_project_name_windows_reserved(self):
        """Test Windows reserved names are rejected"""
        manager = PlatformManager()
        
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            
            reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]
            
            for name in reserved_names:
                assert not manager.validate_project_name(name), f"'{name}' should be invalid on Windows"
                assert not manager.validate_project_name(name.lower()), f"'{name.lower()}' should be invalid on Windows"
    
    def test_get_template_path(self):
        """Test template path generation"""
        manager = PlatformManager()
        snes_home = Path("/test/snes-ide")
        
        # Test different template types
        pvsneslib_path = manager.get_template_path("pvsneslib/template", snes_home)
        expected = snes_home / "libs" / "pvsneslib" / "template"
        assert pvsneslib_path == expected
        
        dotnetsnes_path = manager.get_template_path("DotnetSnesLib/template/DotnetSnes.Example.HelloWorld", snes_home)
        expected = snes_home / "libs" / "DotnetSnesLib" / "template" / "DotnetSnes.Example.HelloWorld"
        assert dotnetsnes_path == expected
    
    def test_copy_template_safely_success(self, tmp_path):
        """Test successful template copying"""
        manager = PlatformManager()
        
        # Create source template
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / "file1.txt").write_text("Template content")
        (template_dir / "subdir").mkdir()
        (template_dir / "subdir" / "file2.txt").write_text("Nested content")
        
        # Copy to target
        target_dir = tmp_path / "target"
        result = manager.copy_template_safely(template_dir, target_dir)
        
        assert result is True
        assert target_dir.exists()
        assert (target_dir / "file1.txt").exists()
        assert (target_dir / "subdir" / "file2.txt").exists()
        assert (target_dir / "file1.txt").read_text() == "Template content"
    
    def test_copy_template_safely_existing_target(self, tmp_path):
        """Test copying when target already exists"""
        manager = PlatformManager()
        
        # Create source template
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / "file.txt").write_text("Template content")
        
        # Create existing target
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "existing.txt").write_text("Existing content")
        
        # Should fail without overwrite
        result = manager.copy_template_safely(template_dir, target_dir, overwrite=False)
        assert result is False
        assert (target_dir / "existing.txt").exists()  # Original content preserved
        
        # Should succeed with overwrite
        result = manager.copy_template_safely(template_dir, target_dir, overwrite=True)
        assert result is True
        assert (target_dir / "file.txt").exists()
        assert not (target_dir / "existing.txt").exists()  # Original content removed
    
    def test_copy_template_safely_nonexistent_source(self, tmp_path):
        """Test copying from non-existent source"""
        manager = PlatformManager()
        
        template_dir = tmp_path / "nonexistent"
        target_dir = tmp_path / "target"
        
        result = manager.copy_template_safely(template_dir, target_dir)
        assert result is False
        assert not target_dir.exists()
    
    def test_copy_template_safely_permissions(self, tmp_path):
        """Test that permissions are set correctly on Unix systems"""
        manager = PlatformManager()
        
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            
            # Create source template with different file types
            template_dir = tmp_path / "template"
            template_dir.mkdir()
            (template_dir / "script.sh").write_text("#!/bin/bash\necho hello")
            (template_dir / "Makefile").write_text("all:\n\techo building")
            (template_dir / "data.txt").write_text("data file")
            
            target_dir = tmp_path / "target"
            
            # Mock the _set_template_permissions method instead of chmod directly
            with patch.object(manager, '_set_template_permissions') as mock_perms:
                result = manager.copy_template_safely(template_dir, target_dir)
                assert result is True
                
                # Verify that _set_template_permissions was called
                mock_perms.assert_called_once_with(target_dir)
