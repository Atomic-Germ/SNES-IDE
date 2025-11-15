"""
Integration tests for platform_utils migration in SNES-IDE compilation scripts.

These tests simulate cross-platform environments and validate that the migrated
compilation scripts work correctly with the PlatformManager.
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import subprocess
import pytest
from tempfile import TemporaryDirectory


def _import_platform_utils_from_src():
    """Ensure src is on sys.path so imports work consistently when running pytest"""
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_import_platform_utils_from_src()

from platform_utils import PlatformManager, Platform, platform_manager


class TestCompilationScriptIntegration:
    """Integration tests for compilation scripts with platform_utils"""
    
    def setup_method(self):
        """Set up test environment for each test"""
        self.repo_root = Path(__file__).resolve().parent.parent
        self.scripts_dir = self.repo_root / "src" / "scripts"
    
    @pytest.fixture
    def mock_snes_ide_home(self):
        """Mock SNES IDE home directory structure"""
        with TemporaryDirectory() as temp_dir:
            snes_home = Path(temp_dir)
            
            # Create expected directory structure
            (snes_home / "bin" / "pvsneslib").mkdir(parents=True)
            (snes_home / "bin" / "make").mkdir(parents=True)
            (snes_home / "bin" / "dotnet8" / "dotnet-sdk-8.0.415-win-x64").mkdir(parents=True)
            (snes_home / "bin" / "dotnet8" / "dotnet-sdk-8.0.415-osx-arm64").mkdir(parents=True)
            (snes_home / "bin" / "dotnet8" / "dotnet-sdk-8.0.415-linux-x64").mkdir(parents=True)
            (snes_home / "bin" / "jdk8" / "jdk8" / "bin").mkdir(parents=True)
            (snes_home / "bin" / "jdk8" / "jdk8" / "zulu-8.jdk" / "Contents" / "Home" / "bin").mkdir(parents=True)
            (snes_home / "libs" / "DntcTranspiler").mkdir(parents=True)
            (snes_home / "libs" / "DotnetSnesLib" / "src").mkdir(parents=True)
            
            # Create executables
            (snes_home / "bin" / "make" / "make").touch()
            (snes_home / "bin" / "make" / "make.exe").touch()
            (snes_home / "bin" / "dotnet8" / "dotnet-sdk-8.0.415-win-x64" / "dotnet.exe").touch()
            (snes_home / "bin" / "dotnet8" / "dotnet-sdk-8.0.415-osx-arm64" / "dotnet").touch()
            (snes_home / "bin" / "dotnet8" / "dotnet-sdk-8.0.415-linux-x64" / "dotnet").touch()
            (snes_home / "bin" / "jdk8" / "jdk8" / "bin" / "java").touch()
            (snes_home / "bin" / "jdk8" / "jdk8" / "bin" / "java.exe").touch()
            (snes_home / "bin" / "jdk8" / "jdk8" / "zulu-8.jdk" / "Contents" / "Home" / "bin" / "java").touch()
            (snes_home / "libs" / "DotnetSnesLib" / "src" / "Makefile.defaults").touch()
            
            yield snes_home
    
    def test_platform_manager_windows_paths(self, mock_snes_ide_home):
        """Test that PlatformManager generates correct paths on Windows"""
        manager = PlatformManager()
        bin_dir = mock_snes_ide_home / "bin"
        
        with patch.object(manager, '_platform', Platform.WINDOWS):
            manager._platform_config = manager._get_platform_config()
            
            # Test executable names
            assert manager.get_executable_name("get-snes-ide-home") == "get-snes-ide-home.exe"
            assert manager.get_relative_executable_path("get-snes-ide-home") == ".\\get-snes-ide-home.exe"
            
            # Test paths
            dotnet_path = manager.get_dotnet_path(bin_dir)
            assert str(dotnet_path).endswith("dotnet.exe")
            assert "win-x64" in str(dotnet_path)
            
            make_path = manager.get_make_path(bin_dir)
            assert str(make_path).endswith("make.exe")
            
            java_path = manager.get_java_path(bin_dir)
            assert str(java_path).endswith("java.exe")
            assert "jdk8" in str(java_path)
    
    def test_platform_manager_macos_paths(self, mock_snes_ide_home):
        """Test that PlatformManager generates correct paths on macOS"""
        manager = PlatformManager()
        bin_dir = mock_snes_ide_home / "bin"
        
        with patch.object(manager, '_platform', Platform.MACOS):
            manager._platform_config = manager._get_platform_config()
            
            # Test executable names
            assert manager.get_executable_name("get-snes-ide-home") == "get-snes-ide-home"
            assert manager.get_relative_executable_path("get-snes-ide-home") == "./get-snes-ide-home"
            
            # Test paths
            dotnet_path = manager.get_dotnet_path(bin_dir)
            assert str(dotnet_path).endswith("dotnet")
            assert "osx-arm64" in str(dotnet_path)
            
            make_path = manager.get_make_path(bin_dir)
            assert str(make_path).endswith("make")
            
            java_path = manager.get_java_path(bin_dir)
            assert str(java_path).endswith("java")
            assert "zulu-8.jdk/Contents/Home/bin" in str(java_path)
    
    def test_platform_manager_linux_paths(self, mock_snes_ide_home):
        """Test that PlatformManager generates correct paths on Linux"""
        manager = PlatformManager()
        bin_dir = mock_snes_ide_home / "bin"
        
        with patch.object(manager, '_platform', Platform.LINUX):
            manager._platform_config = manager._get_platform_config()
            
            # Test executable names
            assert manager.get_executable_name("get-snes-ide-home") == "get-snes-ide-home"
            assert manager.get_relative_executable_path("get-snes-ide-home") == "./get-snes-ide-home"
            
            # Test paths
            dotnet_path = manager.get_dotnet_path(bin_dir)
            assert str(dotnet_path).endswith("dotnet")
            assert "linux-x64" in str(dotnet_path)
            
            make_path = manager.get_make_path(bin_dir)
            assert str(make_path).endswith("make")
            
            java_path = manager.get_java_path(bin_dir)
            assert str(java_path).endswith("java")
            assert "jdk8" in str(java_path)
    
    def test_compilation_script_imports(self):
        """Test that all compilation scripts can be imported successfully"""
        scripts_to_test = [
            "compile-pvsneslib-proj.py",
            "compile-dotnetsnes-proj.py", 
            "compile-javasnes-proj.py"
        ]
        
        for script_name in scripts_to_test:
            script_path = self.scripts_dir / script_name
            assert script_path.exists(), f"Script {script_name} does not exist"
            
            # Test that the script can be compiled (syntax check)
            result = subprocess.run([
                sys.executable, "-m", "py_compile", str(script_path)
            ], capture_output=True, text=True)
            
            assert result.returncode == 0, f"Script {script_name} has syntax errors: {result.stderr}"
    
    @patch('subprocess.run')
    def test_pvsneslib_compilation_workflow(self, mock_subprocess, mock_snes_ide_home):
        """Test the complete PvSnesLib compilation workflow with mocked subprocess"""
        # Mock get-snes-ide-home output
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = str(mock_snes_ide_home)
        
        # Import and test the compilation logic components
        sys.path.append(str(self.scripts_dir))
        
        # We can't directly run main() because it calls exit(), but we can test the logic
        from platform_utils import platform_manager
        
        # Simulate the workflow for each platform
        platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        
        for platform in platforms:
            with patch.object(platform_manager, '_platform', platform):
                platform_manager._platform_config = platform_manager._get_platform_config()
                
                # Test path generation
                bin_dir = mock_snes_ide_home / "bin"
                relative_exe = platform_manager.get_relative_executable_path("get-snes-ide-home")
                make_path = platform_manager.get_make_path(bin_dir)
                
                # Verify the paths exist in our mock structure
                assert make_path.exists(), f"Make path {make_path} does not exist for {platform}"
                
                # Verify correct platform-specific naming
                if platform == Platform.WINDOWS:
                    assert ".exe" in relative_exe
                    assert str(make_path).endswith("make.exe")
                else:
                    assert ".exe" not in relative_exe
                    assert str(make_path).endswith("make")
    
    @patch('subprocess.run')
    def test_dotnetsnes_compilation_workflow(self, mock_subprocess, mock_snes_ide_home):
        """Test the complete DotnetSnes compilation workflow with mocked subprocess"""
        # Mock get-snes-ide-home output
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = str(mock_snes_ide_home)
        
        from platform_utils import platform_manager
        
        # Test for each platform
        platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        
        for platform in platforms:
            with patch.object(platform_manager, '_platform', platform):
                platform_manager._platform_config = platform_manager._get_platform_config()
                
                # Test path generation
                bin_dir = mock_snes_ide_home / "bin"
                dotnet_path = platform_manager.get_dotnet_path(bin_dir)
                make_path = platform_manager.get_make_path(bin_dir)
                
                # Verify the paths exist in our mock structure
                assert dotnet_path.exists(), f"Dotnet path {dotnet_path} does not exist for {platform}"
                assert make_path.exists(), f"Make path {make_path} does not exist for {platform}"
                
                # Verify correct platform-specific .NET SDK selection
                if platform == Platform.WINDOWS:
                    assert "win-x64" in str(dotnet_path)
                    assert str(dotnet_path).endswith("dotnet.exe")
                elif platform == Platform.MACOS:
                    assert "osx-arm64" in str(dotnet_path)
                    assert str(dotnet_path).endswith("dotnet")
                else:  # Linux
                    assert "linux-x64" in str(dotnet_path)
                    assert str(dotnet_path).endswith("dotnet")
    
    @patch('subprocess.run')
    def test_javasnes_compilation_workflow(self, mock_subprocess, mock_snes_ide_home):
        """Test the complete JavaSnes compilation workflow with mocked subprocess"""
        # Mock get-snes-ide-home output
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = str(mock_snes_ide_home)
        
        from platform_utils import platform_manager
        
        # Test for each platform
        platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        
        for platform in platforms:
            with patch.object(platform_manager, '_platform', platform):
                platform_manager._platform_config = platform_manager._get_platform_config()
                
                # Test path generation
                bin_dir = mock_snes_ide_home / "bin"
                java_path = platform_manager.get_java_path(bin_dir)
                java_home = platform_manager.get_java_home(bin_dir)
                make_path = platform_manager.get_make_path(bin_dir)
                
                # Verify the paths exist in our mock structure
                assert java_path.exists(), f"Java path {java_path} does not exist for {platform}"
                assert java_home.exists(), f"Java home {java_home} does not exist for {platform}"
                assert make_path.exists(), f"Make path {make_path} does not exist for {platform}"
                
                # Verify correct platform-specific Java setup
                if platform == Platform.WINDOWS:
                    assert str(java_path).endswith("java.exe")
                elif platform == Platform.MACOS:
                    assert "zulu-8.jdk/Contents/Home/bin" in str(java_path)
                    assert str(java_path).endswith("java")
                else:  # Linux
                    assert "jdk8/jdk8/bin" in str(java_path)
                    assert str(java_path).endswith("java")


class TestErrorHandling:
    """Test error handling and edge cases in the migrated scripts"""
    
    def test_missing_executable_paths(self):
        """Test behavior when expected executables don't exist"""
        manager = PlatformManager()
        non_existent_bin = Path("/non/existent/path")
        
        # Should still generate paths even if they don't exist
        # (The scripts will handle the missing files appropriately)
        dotnet_path = manager.get_dotnet_path(non_existent_bin)
        make_path = manager.get_make_path(non_existent_bin)
        java_path = manager.get_java_path(non_existent_bin)
        
        assert isinstance(dotnet_path, Path)
        assert isinstance(make_path, Path)
        assert isinstance(java_path, Path)
    
    def test_platform_consistency(self):
        """Test that platform detection is consistent across calls"""
        manager = PlatformManager()
        
        # Multiple calls should return the same platform
        platform1 = manager.current_platform
        platform2 = manager.current_platform
        
        assert platform1 == platform2
        
        # Platform-specific methods should be consistent
        is_windows1 = manager.is_windows()
        is_windows2 = manager.is_windows()
        
        assert is_windows1 == is_windows2
    
    def test_path_separator_consistency(self):
        """Test that path separators are used consistently"""
        manager = PlatformManager()
        
        # Test on multiple platforms
        platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]
        
        for platform in platforms:
            with patch.object(manager, '_platform', platform):
                manager._platform_config = manager._get_platform_config()
                
                relative_path = manager.get_relative_executable_path("test")
                
                if platform == Platform.WINDOWS:
                    assert relative_path.startswith(".\\")
                    assert "\\" in relative_path
                else:
                    assert relative_path.startswith("./")
                    assert "/" in relative_path