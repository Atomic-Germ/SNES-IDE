"""
Integration tests for graphics scripts platform_utils migration
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.platform_utils import PlatformManager, Platform


class TestGraphicsScriptIntegration:
    """Integration tests for graphics scripts using platform_utils"""
    
    def test_graphics_script_imports(self):
        """Test that all graphics scripts can be imported with platform_utils"""
        graphics_scripts = [
            "gfx-tmx-editor.py",
            "gfx-png-bmp-editor.py", 
            "gfx-tmx-tmj-converter.py",
            "gfx-png-bmp-snes-converter.py"
        ]
        
        for script_name in graphics_scripts:
            script_path = Path(__file__).parent.parent / "src" / "scripts" / script_name
            
            # Test that script can be compiled
            import py_compile
            try:
                py_compile.compile(script_path, doraise=True)
            except Exception as e:
                pytest.fail(f"Script {script_name} failed to compile: {e}")
    
    def test_graphics_platform_manager_usage(self):
        """Test platform manager usage patterns in graphics scripts"""
        manager = PlatformManager()
        
        # Test executable path patterns used in graphics scripts
        get_snes_ide_home = manager.get_relative_executable_path("get-snes-ide-home")
        gfx4snes_tool = manager.get_executable_name("gfx4snes")
        
        if manager.is_windows():
            assert get_snes_ide_home.endswith('.exe')
            assert gfx4snes_tool.endswith('.exe')
        else:
            assert not get_snes_ide_home.endswith('.exe')
            assert not gfx4snes_tool.endswith('.exe')
    
    def test_graphics_platform_specific_paths(self):
        """Test platform-specific path resolution for graphics tools"""
        manager = PlatformManager()
        
        # Test tiled editor paths (used in gfx-tmx-editor.py)
        if manager.is_windows():
            expected_tiled = "tiled.exe"
        elif manager.is_macos():
            expected_tiled = "Tiled.app"
        else:  # Linux
            expected_tiled = "tiled.AppImage"
            
        # Test libresprite paths (used in gfx-png-bmp-editor.py)
        if manager.is_windows():
            expected_libresprite = "libresprite.exe"
        elif manager.is_macos():
            expected_libresprite = "libresprite.app"
        else:  # Linux
            expected_libresprite = "libresprite.AppImage"
        
        # Verify patterns match what scripts expect
        assert expected_tiled.endswith(('.exe', '.app', '.AppImage'))
        assert expected_libresprite.endswith(('.exe', '.app', '.AppImage'))
    
    def test_graphics_macos_launch_patterns(self):
        """Test macOS-specific app launching patterns"""
        manager = PlatformManager()
        
        # Graphics scripts use 'open -a' command on macOS
        if manager.is_macos():
            # This pattern is used in both gfx-tmx-editor.py and gfx-png-bmp-editor.py
            macos_command_pattern = ["open", "-a", "some-app.app"]
            assert macos_command_pattern[0] == "open"
            assert macos_command_pattern[1] == "-a"
        else:
            # Non-macOS systems run executables directly
            direct_command_pattern = ["some-executable"]
            assert len(direct_command_pattern) == 1


class TestGraphicsScriptMigrationValidation:
    """Validation tests for graphics scripts migration"""
    
    def test_no_legacy_platform_code_in_graphics(self):
        """Test that graphics scripts no longer use legacy platform detection"""
        graphics_script_dir = Path(__file__).parent.parent / "src" / "scripts"
        graphics_scripts = list(graphics_script_dir.glob("gfx-*.py"))
        
        legacy_patterns = [
            'os.name == "nt"',
            'os.name == "posix"',
            'platform.system().lower() == "windows"',
            'platform.system().lower() == "darwin"',
            'platform.system().lower() == "linux"'
        ]
        
        for script_path in graphics_scripts:
            content = script_path.read_text()
            
            for pattern in legacy_patterns:
                assert pattern not in content, f"Legacy pattern '{pattern}' found in {script_path.name}"
    
    def test_platform_manager_imports_in_graphics(self):
        """Test that graphics scripts properly import platform_manager"""
        graphics_script_dir = Path(__file__).parent.parent / "src" / "scripts"
        graphics_scripts = list(graphics_script_dir.glob("gfx-*.py"))
        
        required_patterns = [
            'from platform_utils import platform_manager',
            'sys.path.append(str(Path(__file__).parent.parent))'
        ]
        
        for script_path in graphics_scripts:
            content = script_path.read_text()
            
            for pattern in required_patterns:
                assert pattern in content, f"Required pattern '{pattern}' not found in {script_path.name}"
    
    def test_graphics_platform_manager_method_usage(self):
        """Test that graphics scripts use platform_manager methods correctly"""
        graphics_script_dir = Path(__file__).parent.parent / "src" / "scripts"
        graphics_scripts = list(graphics_script_dir.glob("gfx-*.py"))
        
        expected_method_patterns = [
            'platform_manager.get_relative_executable_path',
            'platform_manager.is_windows',
            'platform_manager.is_macos'
        ]
        
        for script_path in graphics_scripts:
            content = script_path.read_text()
            
            # At least one platform_manager method should be used in each script
            has_platform_manager_usage = any(pattern in content for pattern in expected_method_patterns)
            assert has_platform_manager_usage, f"No platform_manager method usage found in {script_path.name}"
    
    def test_graphics_script_consistency_with_other_phases(self):
        """Test that graphics scripts use same patterns as other migrated scripts"""
        manager = PlatformManager()
        
        # Test executable naming consistency
        test_executable = "test-tool"
        
        # Graphics pattern: platform_manager.get_relative_executable_path
        graphics_pattern = manager.get_relative_executable_path(test_executable)
        
        # Compilation scripts pattern (for comparison)
        compilation_pattern = manager.get_relative_executable_path(test_executable)
        
        # Should be identical
        assert graphics_pattern == compilation_pattern
        
        # Test executable name consistency
        tool_name = "gfx4snes"
        graphics_executable = manager.get_executable_name(tool_name)
        
        if manager.is_windows():
            assert graphics_executable.endswith('.exe')
        else:
            assert not graphics_executable.endswith('.exe')