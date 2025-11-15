"""
Consolidated script integration tests for SNES-IDE.

This module provides comprehensive integration testing for all script categories:
- Audio scripts
- Graphics scripts  
- Build system scripts
- Utility scripts
- Project creation scripts
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# Setup path to import project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from path_utils import path_manager
from platform_utils import platform_manager
from subprocess_utils import subprocess_manager


class TestScriptIntegration(unittest.TestCase):
    """Integration tests for all SNES-IDE scripts."""
    
    def setUp(self):
        """Set up test environment."""
        self.scripts_dir = project_root / "src" / "scripts"
        self.temp_dir = None
        
    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_all_scripts_compilation(self):
        """Test that all scripts compile without syntax errors."""
        if not self.scripts_dir.exists():
            self.skipTest("Scripts directory not found")
            
        import py_compile
        
        script_files = list(self.scripts_dir.glob("*.py"))
        self.assertGreater(len(script_files), 0, "No script files found")
        
        for script_path in script_files:
            with self.subTest(script=script_path.name):
                try:
                    py_compile.compile(script_path, doraise=True)
                except Exception as e:
                    self.fail(f"Script {script_path.name} compilation failed: {e}")

    def test_audio_scripts_interface(self):
        """Test audio script interfaces and dependencies."""
        audio_scripts = [
            "audio-brr-wav-converter.py",
            "audio-impulse-tracker-init.py", 
            "audio-sample-generator.py",
            "audio-wav-brr-converter.py"
        ]
        
        for script_name in audio_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                with self.subTest(script=script_name):
                    # Test that script can be imported
                    self._test_script_import(script_path, script_name)

    def test_graphics_scripts_interface(self):
        """Test graphics script interfaces and dependencies."""
        graphics_scripts = [
            "gfx-png-bmp-editor.py",
            "gfx-png-bmp-snes-converter.py",
            "gfx-tmx-editor.py",
            "gfx-tmx-tmj-converter.py"
        ]
        
        for script_name in graphics_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                with self.subTest(script=script_name):
                    self._test_script_import(script_path, script_name)

    def test_build_scripts_interface(self):
        """Test build system script interfaces."""
        build_scripts = [
            "compile-dotnetsnes-proj.py",
            "compile-javasnes-proj.py", 
            "compile-pvsneslib-proj.py"
        ]
        
        for script_name in build_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                with self.subTest(script=script_name):
                    self._test_script_import(script_path, script_name)

    def test_project_creation_scripts(self):
        """Test project creation script interfaces."""
        creation_scripts = [
            "create-dotnetsnes-proj.py",
            "create-javasnes-proj.py",
            "create-pvsneslib-proj.py"
        ]
        
        for script_name in creation_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                with self.subTest(script=script_name):
                    self._test_script_import(script_path, script_name)

    def test_utility_scripts_interface(self):
        """Test utility script interfaces."""
        utility_scripts = [
            "get-snes-ide-home.py",
            "open-emulator.py"
        ]
        
        for script_name in utility_scripts:
            script_path = self.scripts_dir / script_name
            if script_path.exists():
                with self.subTest(script=script_name):
                    self._test_script_import(script_path, script_name)

    def _test_script_import(self, script_path: Path, script_name: str):
        """Test that a script can be imported and analyzed for dependencies."""
        try:
            # Read script content to check for utility imports
            content = script_path.read_text()
            lines = content.splitlines()
            
            # Check that migrated scripts use new utilities correctly
            has_subprocess_utils = "from subprocess_utils import" in content
            has_path_utils = "from path_utils import" in content
            has_platform_utils = "from platform_utils import" in content
            
            # Check for direct subprocess imports that haven't been migrated
            deprecated_imports = []
            for line in lines:
                line = line.strip()
                # Check for direct subprocess imports (not subprocess_utils)
                if line.startswith("from subprocess import") or line == "import subprocess":
                    deprecated_imports.append(f"Line: {line}")
            
            # Allow certain scripts to not be fully migrated yet
            exempted_scripts = [
                "open-emulator.py",  # May use subprocess for platform-specific operations
                "get-snes-ide-home.py"  # Simple utility script
            ]
            
            if deprecated_imports and script_name not in exempted_scripts:
                self.fail(f"{script_name} has unmigrated subprocess usage:\n" + 
                         "\n".join(deprecated_imports))
                         
            # If script uses subprocess_utils, verify it's used properly
            if has_subprocess_utils:
                self.assertIn("subprocess_manager", content,
                            f"{script_name} imports subprocess_utils but doesn't use subprocess_manager")
                    
        except Exception as e:
            self.fail(f"Failed to analyze script {script_name}: {e}")

    def test_script_utility_integration(self):
        """Test integration between scripts and utility modules."""
        # Test that utilities are properly accessible
        self.assertIsNotNone(path_manager)
        self.assertIsNotNone(platform_manager) 
        self.assertIsNotNone(subprocess_manager)
        
        # Test that utilities can be used together
        try:
            # Test path resolution
            tool_path = path_manager.get_tool_path("test")
            self.assertIsInstance(tool_path, Path)
            
            # Test platform detection
            platform_detected = any([
                platform_manager.is_windows(),
                platform_manager.is_macos(),
                platform_manager.is_linux()
            ])
            self.assertTrue(platform_detected, "No platform detected")
            
            # Test subprocess manager initialization
            self.assertIsNotNone(subprocess_manager.logger)
            
        except Exception as e:
            self.fail(f"Utility integration failed: {e}")

    def test_migration_completeness(self):
        """Test that migration is complete across all scripts."""
        if not self.scripts_dir.exists():
            self.skipTest("Scripts directory not found")
            
        migration_issues = []
        
        # Scripts that are allowed to use subprocess directly for specific purposes
        subprocess_exempt_scripts = {"open-emulator.py"}
        
        for script_path in self.scripts_dir.glob("*.py"):
            content = script_path.read_text()
            lines = content.splitlines()
            
            # Check for unmigrated subprocess usage
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                # Check for direct subprocess imports (not subprocess_utils)
                if (line.startswith("from subprocess import") or line == "import subprocess") and \
                   script_path.name not in subprocess_exempt_scripts:
                    migration_issues.append(
                        f"{script_path.name}:{line_num}: Direct subprocess import not migrated"
                    )
        
        if migration_issues:
            self.fail("Migration incomplete:\n" + "\n".join(migration_issues))

    @patch('subprocess_utils.subprocess_manager')
    def test_script_execution_patterns(self, mock_subprocess_manager):
        """Test common script execution patterns."""
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_subprocess_manager.run_tool.return_value = mock_result
        mock_subprocess_manager.run_external_executable.return_value = mock_result
        
        # Test that scripts would use subprocess_manager correctly
        result = subprocess_manager.run_tool("test-tool")
        self.assertIsNotNone(result)


class TestBuildSystemIntegration(unittest.TestCase):
    """Test build system integration across all project types."""
    
    def test_build_system_scripts_exist(self):
        """Test that all build system scripts exist."""
        scripts_dir = project_root / "src" / "scripts"
        
        expected_scripts = [
            "compile-dotnetsnes-proj.py",
            "compile-javasnes-proj.py", 
            "compile-pvsneslib-proj.py",
            "create-dotnetsnes-proj.py",
            "create-javasnes-proj.py",
            "create-pvsneslib-proj.py"
        ]
        
        for script_name in expected_scripts:
            script_path = scripts_dir / script_name
            with self.subTest(script=script_name):
                self.assertTrue(script_path.exists(), f"Missing script: {script_name}")

    def test_build_script_dependencies(self):
        """Test that build scripts have proper utility dependencies."""
        scripts_dir = project_root / "src" / "scripts"
        
        build_scripts = [
            "compile-dotnetsnes-proj.py",
            "compile-javasnes-proj.py",
            "compile-pvsneslib-proj.py"
        ]
        
        for script_name in build_scripts:
            script_path = scripts_dir / script_name
            if script_path.exists():
                with self.subTest(script=script_name):
                    content = script_path.read_text()
                    
                    # Build scripts should use subprocess_manager for compilation
                    self.assertIn("subprocess_manager", content,
                                f"{script_name} should use subprocess_manager")


if __name__ == '__main__':
    unittest.main()