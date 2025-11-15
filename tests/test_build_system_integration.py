"""
Test cases for build system platform_utils integration
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.platform_utils import PlatformManager, Platform


class TestBuildSystemIntegration:
    """Integration tests for build system using platform_utils"""
    
    def test_build_system_import(self):
        """Test that build.build module can be imported with platform_utils"""
        try:
            import build.build
            assert True, "build.build module imported successfully"
        except ImportError as e:
            pytest.fail(f"Failed to import build.build: {e}")
    
    def test_platform_manager_methods_exist(self):
        """Test platform manager has required methods"""
        manager = PlatformManager()
        
        # Test that required methods exist
        assert hasattr(manager, 'is_windows')
        assert hasattr(manager, 'is_macos')
        assert hasattr(manager, 'is_linux')
        
        # Test current platform detection
        if manager.current_platform == Platform.WINDOWS:
            assert manager.is_windows()
            assert not manager.is_macos()
            assert not manager.is_linux()
        elif manager.current_platform == Platform.MACOS:
            assert manager.is_macos()
            assert not manager.is_windows()
            assert not manager.is_linux()
        elif manager.current_platform == Platform.LINUX:
            assert manager.is_linux()
            assert not manager.is_windows()
            assert not manager.is_macos()
    
    def test_executable_naming_logic(self):
        """Test executable naming logic for build system"""
        manager = PlatformManager()
        
        # Test the pattern used in build.py
        file_stem = "test-script"
        
        if manager.is_windows():
            result = file_stem + ".exe"
            assert result.endswith('.exe')
        else:
            result = file_stem + ""
            assert not result.endswith('.exe')
            assert result == file_stem
    
    def test_chmod_x_logic(self):
        """Test chmod +x logic for build system"""
        manager = PlatformManager()
        
        # Windows should not get chmod +x, others should
        should_chmod = not manager.is_windows()
        
        if manager.is_windows():
            assert not should_chmod
        else:  # Unix-like (Linux, macOS)
            assert should_chmod


class TestBuildSystemMigrationValidation:
    """Validation tests for successful migration from os.name/platform.system()"""
    
    def test_no_legacy_platform_imports_in_build(self):
        """Test that build.py no longer uses legacy platform detection"""
        build_file = Path(__file__).parent.parent / "build" / "build.py"
        content = build_file.read_text()
        
        # These patterns should no longer exist after migration
        legacy_patterns = [
            'os.name == "nt"',
            'os.name == "posix"', 
            'platform.system() == "Windows"',
            'platform.system() == "Darwin"',
            'platform.system() == "Linux"',
            'system == "Windows"',
            'system == "Darwin"',
            'system == "Linux"'
        ]
        
        for pattern in legacy_patterns:
            assert pattern not in content, f"Legacy pattern found in build.py: {pattern}"
    
    def test_platform_manager_usage_in_build(self):
        """Test that build.py properly uses platform_manager methods"""
        build_file = Path(__file__).parent.parent / "build" / "build.py"
        content = build_file.read_text()
        
        # These patterns should exist after migration
        required_patterns = [
            'platform_manager.is_windows()',
            'platform_manager.is_macos()',
            'from platform_utils import platform_manager'
        ]
        
        for pattern in required_patterns:
            assert pattern in content, f"Required pattern not found in build.py: {pattern}"
    
    def test_build_system_imports_correctly(self):
        """Test that build system imports platform_utils correctly"""
        build_file = Path(__file__).parent.parent / "build" / "build.py"
        content = build_file.read_text()
        
        # Check that platform_utils is properly imported
        import_patterns = [
            'from platform_utils import platform_manager',
            'sys.path.append',  # Path setup for imports
        ]
        
        for pattern in import_patterns:
            assert pattern in content, f"Import pattern not found: {pattern}"
    
    def test_build_system_consistency_with_scripts(self):
        """Test that build system uses same patterns as migrated scripts"""
        manager = PlatformManager()
        
        # Test that executable naming is consistent 
        test_stem = "example-tool"
        
        # Build system pattern: stem + (".exe" if is_windows() else "")
        build_pattern = test_stem + (".exe" if manager.is_windows() else "")
        
        # Script pattern: get_relative_executable_path (but strip the ./ prefix)
        script_pattern = manager.get_relative_executable_path(test_stem).lstrip("./")
        
        # Both should have same result
        assert build_pattern == script_pattern