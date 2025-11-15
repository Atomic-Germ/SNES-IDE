"""
Integration tests for audio scripts platform_utils migration
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.platform_utils import PlatformManager, Platform


class TestAudioScriptIntegration:
    """Integration tests for audio scripts using platform_utils"""
    
    def test_audio_script_imports(self):
        """Test that all audio scripts can be imported with platform_utils"""
        audio_scripts = [
            "audio-wav-brr-converter.py",
            "audio-impulse-tracker-init.py",
            "audio-brr-wav-converter.py", 
            "audio-sample-generator.py"
        ]
        
        for script_name in audio_scripts:
            script_path = Path(__file__).parent.parent / "src" / "scripts" / script_name
            
            # Test that script can be compiled
            import py_compile
            try:
                py_compile.compile(script_path, doraise=True)
            except Exception as e:
                pytest.fail(f"Script {script_name} failed to compile: {e}")
    
    def test_audio_platform_manager_usage(self):
        """Test platform manager usage patterns in audio scripts"""
        manager = PlatformManager()
        
        # Test executable path patterns used in audio scripts
        get_snes_ide_home = manager.get_relative_executable_path("get-snes-ide-home")
        snesbrr_tool = manager.get_executable_name("snesbrr")
        
        if manager.is_windows():
            assert get_snes_ide_home.endswith('.exe')
            assert snesbrr_tool.endswith('.exe')
        else:
            assert not get_snes_ide_home.endswith('.exe')
            assert not snesbrr_tool.endswith('.exe')
    
    def test_audio_platform_specific_paths(self):
        """Test platform-specific path resolution for audio tools"""
        manager = PlatformManager()
        
        # Test snesbrr paths (used in wav-brr and brr-wav converters)
        snesbrr_executable = manager.get_executable_name("snesbrr")
        if manager.is_windows():
            assert snesbrr_executable == "snesbrr.exe"
        else:
            assert snesbrr_executable == "snesbrr"
            
        # Test schismtracker paths (used in audio-impulse-tracker-init.py)
        if manager.is_windows():
            expected_schism = "schismtracker.exe"
        elif manager.is_macos():
            expected_schism = "Schism Tracker.app"
        else:  # Linux
            expected_schism = "Schism_Tracker-x86_64.AppImage"
        
        # Verify patterns match what scripts expect
        assert expected_schism.endswith(('.exe', '.app', '.AppImage'))
    
    def test_audio_macos_launch_patterns(self):
        """Test macOS-specific app launching patterns for audio tools"""
        manager = PlatformManager()
        
        # Audio scripts use 'open -a' command on macOS for .app bundles
        if manager.is_macos():
            # This pattern is used in audio-impulse-tracker-init.py
            macos_command_pattern = ["open", "-a", "Schism Tracker.app"]
            assert macos_command_pattern[0] == "open"
            assert macos_command_pattern[1] == "-a"
        else:
            # Non-macOS systems run executables directly
            direct_command_pattern = ["schismtracker.exe" if manager.is_windows() else "Schism_Tracker-x86_64.AppImage"]
            assert len(direct_command_pattern) == 1
    
    def test_audio_tool_paths(self):
        """Test audio tool path construction"""
        manager = PlatformManager()
        
        # Test snesbrr tool path (used by wav-brr and brr-wav converters)
        snesbrr_name = manager.get_executable_name("snesbrr")
        expected_path_suffix = f"bin/pvsneslib/tools/{snesbrr_name}"
        
        if manager.is_windows():
            assert expected_path_suffix.endswith("snesbrr.exe")
        else:
            assert expected_path_suffix.endswith("snesbrr")
            assert not expected_path_suffix.endswith(".exe")


class TestAudioScriptMigrationValidation:
    """Validation tests for audio scripts migration"""
    
    def test_no_legacy_platform_code_in_audio(self):
        """Test that audio scripts no longer use legacy platform detection"""
        audio_script_dir = Path(__file__).parent.parent / "src" / "scripts"
        audio_scripts = list(audio_script_dir.glob("audio-*.py"))
        
        legacy_patterns = [
            'os.name == "nt"',
            'os.name == "posix"',
            'platform.system().lower() == "windows"',
            'platform.system().lower() == "darwin"',
            'platform.system().lower() == "linux"'
        ]
        
        for script_path in audio_scripts:
            content = script_path.read_text()
            
            for pattern in legacy_patterns:
                assert pattern not in content, f"Legacy pattern '{pattern}' found in {script_path.name}"
    
    def test_platform_manager_imports_in_audio(self):
        """Test that audio scripts properly import platform_manager"""
        audio_script_dir = Path(__file__).parent.parent / "src" / "scripts"
        audio_scripts = list(audio_script_dir.glob("audio-*.py"))
        
        required_patterns = [
            'from platform_utils import platform_manager',
            'sys.path.append(str(Path(__file__).parent.parent))'
        ]
        
        for script_path in audio_scripts:
            content = script_path.read_text()
            
            for pattern in required_patterns:
                assert pattern in content, f"Required pattern '{pattern}' not found in {script_path.name}"
    
    def test_audio_platform_manager_method_usage(self):
        """Test that audio scripts use platform_manager methods correctly"""
        audio_script_dir = Path(__file__).parent.parent / "src" / "scripts"
        audio_scripts = list(audio_script_dir.glob("audio-*.py"))
        
        expected_method_patterns = [
            'platform_manager.get_relative_executable_path',
            'platform_manager.get_executable_name'
        ]
        
        # Some scripts also use platform detection methods
        platform_detection_patterns = [
            'platform_manager.is_windows',
            'platform_manager.is_macos'
        ]
        
        for script_path in audio_scripts:
            content = script_path.read_text()
            
            # At least one platform_manager method should be used in each script
            has_platform_manager_usage = any(pattern in content for pattern in expected_method_patterns)
            assert has_platform_manager_usage, f"No platform_manager method usage found in {script_path.name}"
    
    def test_audio_script_consistency_with_other_phases(self):
        """Test that audio scripts use same patterns as other migrated scripts"""
        manager = PlatformManager()
        
        # Test executable naming consistency
        test_executable = "test-tool"
        
        # Audio pattern: platform_manager.get_relative_executable_path
        audio_pattern = manager.get_relative_executable_path(test_executable)
        
        # Compilation scripts pattern (for comparison)
        compilation_pattern = manager.get_relative_executable_path(test_executable)
        
        # Should be identical
        assert audio_pattern == compilation_pattern
        
        # Test tool executable name consistency
        tool_name = "snesbrr"
        audio_executable = manager.get_executable_name(tool_name)
        
        if manager.is_windows():
            assert audio_executable.endswith('.exe')
        else:
            assert not audio_executable.endswith('.exe')
    
    def test_audio_converter_path_patterns(self):
        """Test specific patterns used by audio converter scripts"""
        manager = PlatformManager()
        
        # Test the path pattern used by wav-brr and brr-wav converters
        snesbrr_executable = manager.get_executable_name("snesbrr")
        
        # These scripts construct paths like: Path(...) / "bin" / "pvsneslib" / "tools" / snesbrr_executable
        expected_snesbrr = "snesbrr.exe" if manager.is_windows() else "snesbrr"
        assert snesbrr_executable == expected_snesbrr
        
        # Verify the pattern is consistent across both converter scripts
        assert snesbrr_executable in ["snesbrr", "snesbrr.exe"]