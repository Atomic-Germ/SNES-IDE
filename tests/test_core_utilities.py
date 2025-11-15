"""
Consolidated test suite for SNES-IDE core utilities.

This module combines all path_utils, platform_utils, and subprocess_utils tests
into a single comprehensive test suite, eliminating redundancy while maintaining
complete test coverage.
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from typing import List, Dict, Any

# Setup path to import project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from path_utils import PathManager, path_manager
from platform_utils import PlatformManager, platform_manager, Platform
from subprocess_utils import SubprocessManager, subprocess_manager, ProcessResult


class TestCoreUtilities(unittest.TestCase):
    """Comprehensive test suite for all core utilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = None
        
    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


class TestPathUtils(TestCoreUtilities):
    """Test path utilities functionality."""
    
    def test_frozen_detection(self):
        """Test frozen mode detection."""
        with patch("sys.frozen", True, create=True):
            manager = PathManager()
            assert manager.is_frozen is True

    def test_executable_naming(self):
        """Test executable naming logic."""
        manager = PathManager()

        with patch("os.name", "nt"):
            assert manager.executable_name("test") == "test.exe"

        with patch("os.name", "posix"):
            assert manager.executable_name("test") == "test"

    def test_tool_path_resolution(self):
        """Test tool path resolution."""
        manager = PathManager()
        
        # Test basic tool path resolution without mocking properties
        tool_path = manager.get_tool_path("test-tool")
        self.assertIsInstance(tool_path, Path)
        expected_name = "test-tool.exe" if os.name == "nt" else "test-tool"
        self.assertEqual(tool_path.name, expected_name)

    def test_project_root_detection(self):
        """Test project root detection logic."""
        manager = PathManager()
        
        # Should find project root containing build/build.py
        assert manager.project_root.exists()
        assert (manager.project_root / "build" / "build.py").exists()

    def test_ensure_directory_creation(self):
        """Test directory creation utility."""
        manager = PathManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "nested" / "directory"
            manager.ensure_directory_exists(test_dir)
            assert test_dir.exists()
            assert test_dir.is_dir()


class TestPlatformUtils(TestCoreUtilities):
    """Test platform utilities functionality."""
    
    def test_platform_detection(self):
        """Test platform detection logic."""
        manager = PlatformManager()
        
        # Test that platform detection returns a valid Platform enum
        platform = manager.current_platform
        self.assertIn(platform, [Platform.WINDOWS, Platform.MACOS, Platform.LINUX])
        
        # Test platform detection methods using actual platform
        platform_methods = [manager.is_windows(), manager.is_macos(), manager.is_linux()]
        self.assertEqual(sum(platform_methods), 1, "Exactly one platform should be detected")

    def test_platform_properties(self):
        """Test platform property methods."""
        manager = PlatformManager()
        
        # Test that exactly one platform property is True
        platforms = [manager.is_windows(), manager.is_macos(), manager.is_linux()]
        assert sum(platforms) == 1

    def test_executable_naming(self):
        """Test platform-specific executable naming."""
        manager = PlatformManager()
        
        # Test executable naming based on actual platform
        result = manager.get_executable_name("test")
        if manager.is_windows():
            self.assertEqual(result, "test.exe")
        else:
            self.assertEqual(result, "test")

    def test_shell_commands(self):
        """Test shell command generation.""" 
        manager = PlatformManager()
        
        # Test shell command generation based on actual platform
        cmd = manager.get_shell_command("echo test")
        self.assertIsInstance(cmd, list)
        self.assertGreater(len(cmd), 0)
        
        if manager.is_windows():
            self.assertIn(cmd[0], ["cmd", "cmd.exe"])
            self.assertIn("/c", cmd)
        else:
            self.assertIn(cmd[0], ["sh", "/bin/sh"])
            self.assertIn("-c", cmd)

    def test_path_resolution(self):
        """Test platform-specific path resolution."""
        manager = PlatformManager()
        bin_dir = Path("/test/bin")
        
        # Test .NET path resolution
        dotnet_path = manager.get_dotnet_path(bin_dir)
        assert isinstance(dotnet_path, Path)
        
        # Test Java path resolution
        java_path = manager.get_java_path(bin_dir)
        assert isinstance(java_path, Path)
        
        # Test Make path resolution
        make_path = manager.get_make_path(bin_dir)
        assert isinstance(make_path, Path)

    def test_project_utilities(self):
        """Test project creation utilities."""
        manager = PlatformManager()
        
        # Test project name validation
        self.assertTrue(manager.validate_project_name("valid_name"))
        self.assertFalse(manager.validate_project_name("invalid name with spaces"))
        
        # Test Windows reserved names only on Windows
        if manager.is_windows():
            self.assertFalse(manager.validate_project_name("CON"))
        else:
            # On non-Windows, this might be valid
            pass
        
        # Test template path resolution
        template_path = manager.get_template_path("test/template", Path("/base"))
        self.assertIsInstance(template_path, Path)

    def test_singleton_instance(self):
        """Test that platform_manager is a singleton."""
        assert platform_manager is not None
        assert isinstance(platform_manager, PlatformManager)


class TestSubprocessUtils(TestCoreUtilities):
    """Test subprocess utilities functionality."""
    
    def test_process_result_creation(self):
        """Test ProcessResult creation and properties."""
        result = ProcessResult(
            returncode=0,
            stdout="test output",
            stderr="",
            command=["test", "command"],
            success=True
        )
        
        assert result.returncode == 0
        assert result.stdout == "test output"
        assert result.success == True
        assert result.failed == False

    def test_subprocess_manager_initialization(self):
        """Test SubprocessManager initialization."""
        manager = SubprocessManager()
        assert manager.logger is not None
        
        # Test with custom logger
        import logging
        custom_logger = logging.getLogger("test")
        manager = SubprocessManager(custom_logger)
        assert manager.logger == custom_logger

    @patch('subprocess.run')
    def test_tool_execution(self, mock_run):
        """Test tool execution functionality."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="success",
            stderr=""
        )
        
        manager = SubprocessManager()
        
        # Mock path_manager.get_tool_path to return an existing path
        with patch.object(path_manager, 'get_tool_path') as mock_get_tool:
            mock_get_tool.return_value = Path(__file__)  # Use this file as existing path
            
            result = manager.run_tool("test-tool", args=["arg1", "arg2"])
            
            self.assertTrue(result.success)
            self.assertEqual(result.stdout, "success")
            mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_external_executable(self, mock_run):
        """Test external executable execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="output",
            stderr=""
        )
        
        manager = SubprocessManager()
        
        with patch('shutil.which', return_value="/usr/bin/test"):
            result = manager.run_external_executable("test", args=["arg"])
            
            assert result.success
            mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_shell_command_execution(self, mock_run):
        """Test shell command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="output",
            stderr=""
        )
        
        manager = SubprocessManager()
        
        with patch.object(platform_manager, 'get_shell_command') as mock_shell:
            mock_shell.return_value = ["sh", "-c", "echo test"]
            
            result = manager.run_shell_command("echo test")
            
            assert result.success
            mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_make_compilation(self, mock_run):
        """Test make compilation functionality."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="build success",
            stderr=""
        )
        
        manager = SubprocessManager()
        
        with patch.object(platform_manager, 'get_make_path') as mock_make:
            mock_make.return_value = Path("/usr/bin/make")
            
            result = manager.compile_with_make(
                makefile_dir=Path("/test/project"),
                env_vars={"TEST_VAR": "value"}
            )
            
            assert result.success
            mock_run.assert_called_once()

    def test_convenience_functions(self):
        """Test convenience functions."""
        from subprocess_utils import run_tool, run_shell_command, run_external_executable
        
        # Test that convenience functions exist and are callable
        assert callable(run_tool)
        assert callable(run_shell_command)
        assert callable(run_external_executable)

    def test_singleton_instance(self):
        """Test that subprocess_manager is a singleton."""
        assert subprocess_manager is not None
        assert isinstance(subprocess_manager, SubprocessManager)


class TestScriptIntegration(TestCoreUtilities):
    """Test integration across all migrated scripts."""
    
    def test_script_compilation(self):
        """Test that all scripts can be compiled without syntax errors."""
        scripts_dir = project_root / "src" / "scripts"
        
        if not scripts_dir.exists():
            self.skipTest("Scripts directory not found")
            
        import py_compile
        
        for script_path in scripts_dir.glob("*.py"):
            with self.subTest(script=script_path.name):
                try:
                    py_compile.compile(script_path, doraise=True)
                except Exception as e:
                    self.fail(f"Script {script_path.name} failed to compile: {e}")

    def test_utility_imports(self):
        """Test that all utilities can be imported correctly."""
        try:
            from path_utils import path_manager
            from platform_utils import platform_manager
            from subprocess_utils import subprocess_manager
            
            # Verify instances exist and are properly initialized
            self.assertIsNotNone(path_manager)
            self.assertIsNotNone(platform_manager)
            self.assertIsNotNone(subprocess_manager)
            
        except ImportError as e:
            self.fail(f"Failed to import utilities: {e}")

    def test_cross_platform_consistency(self):
        """Test that utilities work consistently across platforms."""
        # Test path resolution consistency
        tool_path = path_manager.get_tool_path("test-tool")
        self.assertIsInstance(tool_path, Path)
        
        # Test platform detection consistency
        platform_count = sum([
            platform_manager.is_windows(),
            platform_manager.is_macos(),
            platform_manager.is_linux()
        ])
        self.assertEqual(platform_count, 1, "Exactly one platform should be detected")


if __name__ == '__main__':
    unittest.main()