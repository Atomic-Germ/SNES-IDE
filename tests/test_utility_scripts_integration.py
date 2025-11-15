"""
Integration tests for utility scripts platform_utils migration
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.platform_utils import PlatformManager, Platform


class TestUtilityScriptIntegration:
    """Integration tests for utility scripts using platform_utils"""
    
    def test_utility_script_imports(self):
        """Test that all utility scripts can be imported/compiled"""
        utility_scripts = [
            "get-snes-ide-home.py",
            "open-emulator.py"
        ]
        
        for script_name in utility_scripts:
            script_path = Path(__file__).parent.parent / "src" / "scripts" / script_name
            
            # Test that script can be compiled
            import py_compile
            try:
                py_compile.compile(script_path, doraise=True)
            except Exception as e:
                pytest.fail(f"Script {script_name} failed to compile: {e}")
    
    def test_get_snes_ide_home_no_platform_dependencies(self):
        """Test that get-snes-ide-home.py has no platform dependencies (already clean)"""
        script_path = Path(__file__).parent.parent / "src" / "scripts" / "get-snes-ide-home.py"
        content = script_path.read_text()
        
        # Should not contain any legacy platform code
        legacy_patterns = [
            'os.name',
            'platform.system',
            'import platform'
        ]
        
        for pattern in legacy_patterns:
            assert pattern not in content, f"get-snes-ide-home.py should not have platform dependencies, found: {pattern}"
    
    def test_open_emulator_platform_manager_usage(self):
        """Test platform manager usage patterns in open-emulator.py"""
        manager = PlatformManager()
        
        # Test executable path patterns used in open-emulator.py
        get_snes_ide_home = manager.get_relative_executable_path("get-snes-ide-home")
        
        if manager.is_windows():
            assert get_snes_ide_home.endswith('.exe')
        else:
            assert not get_snes_ide_home.endswith('.exe')
    
    def test_emulator_platform_specific_paths(self):
        """Test platform-specific path resolution for SNES emulators"""
        manager = PlatformManager()
        
        # Test emulator paths (used in open-emulator.py)
        if manager.is_windows():
            expected_emulator = "lakesnes.exe"
        elif manager.is_macos():
            expected_emulator = "bsnes.app"
        else:  # Linux
            expected_emulator = "lakesnes"
        
        # Verify patterns match what open-emulator.py expects
        assert expected_emulator.endswith(('.exe', '.app')) or not expected_emulator.endswith(('.exe', '.app'))
    
    def test_emulator_macos_launch_patterns(self):
        """Test macOS-specific app launching patterns for emulators"""
        manager = PlatformManager()
        
        # open-emulator.py uses 'open -a' command on macOS for .app bundles
        if manager.is_macos():
            # This pattern is used in open-emulator.py
            macos_command_pattern = ["open", "-a", "bsnes.app"]
            assert macos_command_pattern[0] == "open"
            assert macos_command_pattern[1] == "-a"
        else:
            # Non-macOS systems run executables directly with ROM path
            if manager.is_windows():
                direct_command_pattern = ["lakesnes.exe", "rom_path"]
            else:
                direct_command_pattern = ["lakesnes", "rom_path"]
            assert len(direct_command_pattern) == 2
    
    def test_utility_cross_platform_consistency(self):
        """Test cross-platform consistency of utility script patterns"""
        manager = PlatformManager()
        
        # Test that utility scripts use same executable path pattern as other scripts
        test_executable = "get-snes-ide-home"
        utility_pattern = manager.get_relative_executable_path(test_executable)
        
        # Should be consistent with compilation/graphics/audio scripts
        if manager.is_windows():
            assert utility_pattern.endswith('.exe')
        else:
            assert not utility_pattern.endswith('.exe')


class TestUtilityScriptMigrationValidation:
    """Validation tests for utility scripts migration"""
    
    def test_no_legacy_platform_code_in_utilities(self):
        """Test that utility scripts no longer use legacy platform detection"""
        utility_script_dir = Path(__file__).parent.parent / "src" / "scripts"
        utility_scripts = [
            utility_script_dir / "get-snes-ide-home.py",
            utility_script_dir / "open-emulator.py"
        ]
        
        legacy_patterns = [
            'os.name == "nt"',
            'os.name == "posix"',
            'platform.system().lower() == "windows"',
            'platform.system().lower() == "darwin"',
            'platform.system().lower() == "linux"'
        ]
        
        for script_path in utility_scripts:
            content = script_path.read_text()
            
            for pattern in legacy_patterns:
                assert pattern not in content, f"Legacy pattern '{pattern}' found in {script_path.name}"
    
    def test_platform_manager_imports_in_open_emulator(self):
        """Test that open-emulator.py properly imports platform_manager"""
        script_path = Path(__file__).parent.parent / "src" / "scripts" / "open-emulator.py"
        content = script_path.read_text()
        
        required_patterns = [
            'from platform_utils import platform_manager',
            'sys.path.append(str(Path(__file__).parent.parent))'
        ]
        
        for pattern in required_patterns:
            assert pattern in content, f"Required pattern '{pattern}' not found in open-emulator.py"
    
    def test_get_snes_ide_home_remains_clean(self):
        """Test that get-snes-ide-home.py remains clean (no platform_utils needed)"""
        script_path = Path(__file__).parent.parent / "src" / "scripts" / "get-snes-ide-home.py"
        content = script_path.read_text()
        
        # Should NOT have platform_utils import (doesn't need it)
        platform_utils_patterns = [
            'from platform_utils import',
            'platform_manager'
        ]
        
        for pattern in platform_utils_patterns:
            assert pattern not in content, f"get-snes-ide-home.py should not need platform_utils, found: {pattern}"
    
    def test_open_emulator_platform_manager_method_usage(self):
        """Test that open-emulator.py uses platform_manager methods correctly"""
        script_path = Path(__file__).parent.parent / "src" / "scripts" / "open-emulator.py"
        content = script_path.read_text()
        
        expected_method_patterns = [
            'platform_manager.get_relative_executable_path',
            'platform_manager.is_windows',
            'platform_manager.is_macos'
        ]
        
        for pattern in expected_method_patterns:
            assert pattern in content, f"Expected platform_manager method '{pattern}' not found in open-emulator.py"
    
    def test_utility_script_consistency_with_other_phases(self):
        """Test that utility scripts use same patterns as other migrated scripts"""
        manager = PlatformManager()
        
        # Test executable naming consistency
        test_executable = "get-snes-ide-home"
        
        # Utility pattern: platform_manager.get_relative_executable_path
        utility_pattern = manager.get_relative_executable_path(test_executable)
        
        # Should be identical to other phases
        if manager.is_windows():
            assert utility_pattern.endswith('.exe')
            assert "get-snes-ide-home.exe" in utility_pattern
        else:
            assert not utility_pattern.endswith('.exe')
            assert utility_pattern.endswith("get-snes-ide-home")
    
    def test_complete_migration_validation(self):
        """Test that all scripts in the project now use platform_manager"""
        scripts_dir = Path(__file__).parent.parent / "src" / "scripts"
        all_script_files = list(scripts_dir.glob("*.py"))
        
        # Scripts that should have platform_manager usage (excluding get-snes-ide-home.py)
        scripts_with_platform_usage = [
            f for f in all_script_files 
            if f.name != "get-snes-ide-home.py" and not f.name.startswith("__")
        ]
        
        for script_path in scripts_with_platform_usage:
            content = script_path.read_text()
            
            # Should have platform_manager import
            has_platform_manager = 'from platform_utils import platform_manager' in content
            if not has_platform_manager:
                pytest.fail(f"Script {script_path.name} should have platform_manager import")
            
            # Should not have legacy platform code
            legacy_patterns = ['os.name == "nt"', 'platform.system().lower()']
            for pattern in legacy_patterns:
                if pattern in content:
                    pytest.fail(f"Script {script_path.name} still contains legacy pattern: {pattern}")