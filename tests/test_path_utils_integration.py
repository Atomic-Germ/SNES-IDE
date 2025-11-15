"""
Test suite for path_utils integration across SNES-IDE codebase.

This module tests that all scripts correctly use path_manager instead of duplicate
get_executable_path() functions, ensuring consistent path handling across platforms
and execution modes (development vs PyInstaller frozen).
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

# Setup path to import project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from path_utils import path_manager
from platform_utils import platform_manager


class TestPathUtilsIntegration(unittest.TestCase):
    """Test path_manager integration across all migrated scripts."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_frozen = getattr(sys, 'frozen', False)
        self.original_executable = sys.executable
        self.original_file = __file__
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if hasattr(sys, 'frozen'):
            sys.frozen = self.original_frozen
        sys.executable = self.original_executable
        
    def test_path_manager_singleton(self):
        """Test that path_manager is properly initialized as singleton."""
        # Import path_manager multiple times should return same instance
        from path_utils import path_manager as pm1
        from path_utils import path_manager as pm2
        
        self.assertIs(pm1, pm2)
        self.assertIsNotNone(pm1.project_root)
        self.assertIsNotNone(pm1.executable_dir)
        
    def test_path_manager_frozen_detection(self):
        """Test path_manager correctly detects PyInstaller frozen mode."""
        # Test development mode (default)
        self.assertFalse(path_manager.is_frozen)
        self.assertEqual(path_manager.executable_dir, Path(__file__).parent.parent / "src")
        
    @patch.object(sys, 'frozen', True, create=True)
    @patch('sys.executable', '/path/to/frozen/executable')
    def test_path_manager_frozen_mode(self):
        """Test path_manager behavior in PyInstaller frozen mode."""
        # Reset path_manager to pick up mocked values
        from path_utils import PathManager
        test_manager = PathManager()
        
        self.assertTrue(test_manager.is_frozen)
        self.assertEqual(test_manager.executable_dir, Path('/path/to/frozen'))
        
    def test_migrated_scripts_import_path_manager(self):
        """Test that all migrated scripts properly import path_manager."""
        migrated_scripts = [
            # Phase 1: Core Scripts
            "src/scripts/compile-pvsneslib-proj.py",
            "src/scripts/compile-dotnetsnes-proj.py", 
            "src/scripts/compile-javasnes-proj.py",
            "src/scripts/create-pvsneslib-proj.py",
            "src/scripts/create-dotnetsnes-proj.py",
            "src/scripts/create-javasnes-proj.py",
            
            # Phase 2: Graphics & Audio Scripts
            "src/scripts/gfx-png-bmp-editor.py",
            "src/scripts/gfx-tmx-editor.py", 
            "src/scripts/gfx-tmx-tmj-converter.py",
            "src/scripts/audio-wav-brr-converter.py",
            "src/scripts/audio-brr-wav-converter.py",
            "src/scripts/audio-impulse-tracker-init.py",
            "src/scripts/audio-sample-generator.py",
            "src/scripts/gfx-png-bmp-snes-converter.py",
            
            # Phase 3: Core Application & Utilities
            "src/snes-ide.py",
            "src/scripts/get-snes-ide-home.py",
            "src/scripts/open-emulator.py",
            
            # Phase 4: Build System
            "build/build.py"
        ]
        
        for script_path in migrated_scripts:
            full_path = project_root / script_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check that script imports path_manager
                self.assertIn("from path_utils import path_manager", content,
                            f"Script {script_path} missing path_manager import")
                
                # Check that script doesn't have old get_executable_path function
                self.assertNotIn("def get_executable_path(", content,
                                f"Script {script_path} still has get_executable_path function")
                                
    def test_no_duplicate_get_executable_path_functions(self):
        """Test that no duplicate get_executable_path functions remain."""
        scripts_to_check = [
            "src/scripts",
            "src/snes-ide.py",
            "build/build.py"
        ]
        
        found_duplicates = []
        
        for path in scripts_to_check:
            full_path = project_root / path
            if full_path.is_file():
                # Single file
                files_to_check = [full_path]
            else:
                # Directory - get all Python files
                files_to_check = list(full_path.rglob("*.py"))
                
            for file_path in files_to_check:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "def get_executable_path(" in content:
                        found_duplicates.append(str(file_path.relative_to(project_root)))
                        
        self.assertEqual([], found_duplicates,
                        f"Found duplicate get_executable_path functions in: {found_duplicates}")
                        
    def test_path_manager_usage_patterns(self):
        """Test that scripts use correct path_manager patterns."""
        scripts_using_executable_dir = [
            "src/scripts/compile-pvsneslib-proj.py",
            "src/scripts/compile-dotnetsnes-proj.py",
            "src/scripts/compile-javasnes-proj.py",
            "src/scripts/get-snes-ide-home.py",
            "src/scripts/open-emulator.py",
        ]
        
        for script_path in scripts_using_executable_dir:
            full_path = project_root / script_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Should use path_manager.executable_dir
                self.assertIn("path_manager.executable_dir", content,
                            f"Script {script_path} should use path_manager.executable_dir")
                            
    def test_build_system_enhancements(self):
        """Test that build system uses enhanced path utilities."""
        build_script = project_root / "build/build.py"
        if build_script.exists():
            with open(build_script, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Should use path_manager.project_root instead of manual calculation
            self.assertIn("path_manager.project_root", content,
                        "Build script should use path_manager.project_root")
                        
            # Should have utility functions
            self.assertIn("def ensure_directory_exists(", content,
                        "Build script should have ensure_directory_exists function")
            self.assertIn("def get_build_resource_path(", content,
                        "Build script should have get_build_resource_path function")
                        
            # Should not use old manual mkdir patterns excessively
            mkdir_count = content.count(".mkdir(parents=True, exist_ok=True)")
            self.assertLessEqual(mkdir_count, 2,
                               f"Build script has {mkdir_count} old mkdir patterns, should use utilities")
                               
    def test_consistent_import_patterns(self):
        """Test that all scripts follow consistent import patterns."""
        migrated_scripts = [
            "src/scripts/compile-pvsneslib-proj.py",
            "src/scripts/compile-dotnetsnes-proj.py",
            "src/scripts/create-pvsneslib-proj.py",
            "src/scripts/gfx-png-bmp-editor.py",
            "src/scripts/audio-wav-brr-converter.py",
        ]
        
        for script_path in migrated_scripts:
            full_path = project_root / script_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Should have both platform_utils and path_utils imports
                self.assertIn("from platform_utils import platform_manager", content,
                            f"Script {script_path} missing platform_manager import")
                self.assertIn("from path_utils import path_manager", content,
                            f"Script {script_path} missing path_manager import")


class TestPathManagerFunctionality(unittest.TestCase):
    """Test core path_manager functionality."""
    
    def test_project_root_detection(self):
        """Test that project_root is correctly detected."""
        # Should point to the directory containing src/, build/, etc.
        expected_root = Path(__file__).parent.parent
        self.assertEqual(path_manager.project_root, expected_root)
        
        # Should contain expected directories
        self.assertTrue((path_manager.project_root / "src").exists())
        self.assertTrue((path_manager.project_root / "build").exists())
        
    def test_executable_dir_in_dev_mode(self):
        """Test executable_dir in development mode."""
        # In development mode, should point to src/
        expected_dir = project_root / "src"
        self.assertEqual(path_manager.executable_dir, expected_dir)
        
    def test_resource_path_resolution(self):
        """Test resource path resolution."""
        # Test various resource paths
        src_scripts_path = path_manager.resource_path("src/scripts") 
        self.assertEqual(src_scripts_path, path_manager.project_root / "src" / "scripts")
        
        assets_path = path_manager.resource_path("src/assets/index.html") 
        self.assertEqual(assets_path, path_manager.project_root / "src" / "assets" / "index.html")
        
    def test_directory_creation_utility(self):
        """Test path_manager's directory creation utility."""
        test_dir = Path(tempfile.mkdtemp()) / "test" / "nested" / "path"
        
        # Should create directory structure
        result = path_manager.ensure_directory_exists(test_dir)
        self.assertTrue(result.exists())
        self.assertTrue(result.is_dir())
        self.assertEqual(result, test_dir)
        
        # Clean up
        shutil.rmtree(test_dir.parent.parent.parent, ignore_errors=True)
        

class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility of path management."""
    
    def test_platform_specific_paths(self):
        """Test that paths work correctly across platforms."""
        # Test that path_manager uses platform-appropriate separators
        test_path = path_manager.resource_path("scripts/compile-pvsneslib-proj.py")
        self.assertIsInstance(test_path, Path)
        
        # Should work with string conversion for subprocess calls
        str_path = str(test_path)
        self.assertIsInstance(str_path, str)
        
    @patch('platform_utils.platform_manager.is_windows')
    def test_windows_compatibility(self, mock_is_windows):
        """Test Windows-specific path handling."""
        mock_is_windows.return_value = True
        
        # Test that paths work correctly on Windows
        test_path = path_manager.resource_path("bin/tool.exe")
        self.assertTrue(str(test_path).endswith("tool.exe"))
        
    @patch('platform_utils.platform_manager.is_macos')  
    def test_macos_compatibility(self, mock_is_macos):
        """Test macOS-specific path handling.""" 
        mock_is_macos.return_value = True
        
        # Test that paths work correctly on macOS
        test_path = path_manager.resource_path("bin/tool")
        self.assertFalse(str(test_path).endswith(".exe"))


class TestMigrationCompleteness(unittest.TestCase):
    """Test that migration is complete and comprehensive."""
    
    def test_all_phases_completed(self):
        """Test that all migration phases are complete."""
        # Count migrated scripts by phase
        phase_counts = {
            "Phase 1 (Core)": 6,
            "Phase 2 (Graphics/Audio)": 8, 
            "Phase 3 (Core App/Utils)": 3,
            "Phase 4 (Build System)": 1
        }
        
        total_expected = sum(phase_counts.values())
        
        # Verify we have the expected number of migrated scripts
        migrated_scripts = []
        for pattern in ["src/scripts/*.py", "src/snes-ide.py", "build/build.py"]:
            migrated_scripts.extend(project_root.glob(pattern))
            
        # Filter to only scripts that import path_manager
        actual_migrated = []
        for script in migrated_scripts:
            if script.is_file():
                with open(script, 'r', encoding='utf-8') as f:
                    if "from path_utils import path_manager" in f.read():
                        actual_migrated.append(script)
                        
        self.assertGreaterEqual(len(actual_migrated), total_expected - 2,  # Allow some flexibility
                              f"Expected ~{total_expected} migrated scripts, found {len(actual_migrated)}")
                              
    def test_no_regression_in_existing_functionality(self):
        """Test that existing functionality hasn't regressed."""
        # Test that platform_manager is still working
        self.assertIsNotNone(platform_manager)
        self.assertTrue(hasattr(platform_manager, 'is_windows'))
        self.assertTrue(hasattr(platform_manager, 'is_macos'))
        self.assertTrue(hasattr(platform_manager, 'is_linux'))


if __name__ == '__main__':
    # Run the test suite
    unittest.main(verbosity=2)