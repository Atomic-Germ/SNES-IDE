import sys
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import pytest
import logging


def _import_subprocess_utils_from_src():
    # Ensure src is on sys.path so imports work consistently when running pytest
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_import_subprocess_utils_from_src()

from subprocess_utils import (
    SubprocessManager, ProcessResult, subprocess_manager,
    run_tool, run_shell_command, run_external_executable
)


class TestProcessResult:
    """Test ProcessResult dataclass"""
    
    def test_process_result_creation(self):
        """Test creating a ProcessResult"""
        result = ProcessResult(
            returncode=0,
            stdout="output",
            stderr="",
            command=["test"],
            success=True
        )
        assert result.returncode == 0
        assert result.stdout == "output"
        assert result.success is True
    
    def test_process_result_failed_property(self):
        """Test failed property"""
        success_result = ProcessResult(0, "", "", [], True)
        assert success_result.failed is False
        
        failure_result = ProcessResult(1, "", "error", [], False)
        assert failure_result.failed is True


class TestSubprocessManagerInit:
    """Test SubprocessManager initialization"""
    
    def test_default_logger(self):
        """Test initialization with default logger"""
        manager = SubprocessManager()
        assert manager.logger is not None
        assert isinstance(manager.logger, logging.Logger)
    
    def test_custom_logger(self):
        """Test initialization with custom logger"""
        custom_logger = logging.getLogger("custom")
        manager = SubprocessManager(logger=custom_logger)
        assert manager.logger is custom_logger


class TestRunTool:
    """Test run_tool method"""
    
    def test_tool_not_found(self):
        """Test handling when tool doesn't exist"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = False
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            result = manager.run_tool("nonexistent-tool")
            
            assert result.failed
            assert result.returncode == -1
            assert "not found" in result.stderr.lower()
    
    def test_tool_execution_success(self):
        """Test successful tool execution"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="success output",
                    stderr=""
                )
                
                result = manager.run_tool("test-tool", ["arg1", "arg2"])
                
                assert result.success
                assert result.stdout == "success output"
                assert result.returncode == 0
                mock_run.assert_called_once()
    
    def test_tool_execution_with_args(self):
        """Test tool execution with arguments"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                result = manager.run_tool("test-tool", ["arg1", "arg2"])
                
                # Check that command includes args
                call_args = mock_run.call_args[0][0]
                assert "/fake/tool" in call_args[0]
                assert "arg1" in call_args
                assert "arg2" in call_args
    
    def test_tool_execution_failure(self):
        """Test tool execution that fails"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=1,
                    stdout="",
                    stderr="error message"
                )
                
                result = manager.run_tool("test-tool")
                
                assert result.failed
                assert result.returncode == 1
                assert result.stderr == "error message"
    
    def test_tool_execution_timeout(self):
        """Test tool execution that times out"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired(
                    cmd="test", timeout=30, output=b"partial", stderr=None
                )
                
                result = manager.run_tool("test-tool", timeout=30)
                
                assert result.failed
                assert result.returncode == -1
                assert "timed out" in result.stderr.lower()
    
    def test_tool_execution_with_check(self):
        """Test tool execution with check=True"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    returncode=1, cmd="test", output="out", stderr="err"
                )
                
                result = manager.run_tool("test-tool", check=True)
                
                assert result.failed
                assert result.returncode == 1


class TestRunShellCommand:
    """Test run_shell_command method"""
    
    def test_shell_command_success(self):
        """Test successful shell command execution"""
        manager = SubprocessManager()
        
        with patch('platform_utils.PlatformManager.get_shell_command') as mock_shell:
            mock_shell.return_value = ["sh", "-c", "echo hello"]
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="hello\n",
                    stderr=""
                )
                
                result = manager.run_shell_command("echo hello")
                
                assert result.success
                assert "hello" in result.stdout
    
    def test_shell_command_failure(self):
        """Test shell command that fails"""
        manager = SubprocessManager()
        
        with patch('platform_utils.PlatformManager.get_shell_command') as mock_shell:
            mock_shell.return_value = ["sh", "-c", "exit 1"]
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=1,
                    stdout="",
                    stderr="command failed"
                )
                
                result = manager.run_shell_command("exit 1")
                
                assert result.failed
                assert result.returncode == 1
    
    def test_shell_command_exception(self):
        """Test shell command that raises exception"""
        manager = SubprocessManager()
        
        with patch('platform_utils.PlatformManager.get_shell_command') as mock_shell:
            mock_shell.return_value = ["sh", "-c", "test"]
            
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = OSError("Permission denied")
                
                result = manager.run_shell_command("test")
                
                assert result.failed
                assert "Permission denied" in result.stderr


class TestRunExternalExecutable:
    """Test run_external_executable method"""
    
    def test_external_executable_success(self):
        """Test successful external executable execution"""
        manager = SubprocessManager()
        
        with patch('shutil.which') as mock_which:
            mock_which.return_value = "/usr/bin/python3"
            
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True
                
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(
                        returncode=0,
                        stdout="Python 3.x",
                        stderr=""
                    )
                    
                    result = manager.run_external_executable("python3", ["--version"])
                    
                    assert result.success
                    assert "Python" in result.stdout
    
    def test_external_executable_not_found(self):
        """Test external executable not found"""
        manager = SubprocessManager()
        
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None
            
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = False
                
                result = manager.run_external_executable("nonexistent")
                
                assert result.failed
                assert "not found" in result.stderr.lower()
    
    def test_external_executable_with_path_object(self):
        """Test external executable with Path object"""
        manager = SubprocessManager()
        
        exe_path = Path("/usr/bin/test")
        
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                result = manager.run_external_executable(exe_path)
                
                assert result.success
                call_args = mock_run.call_args[0][0]
                assert str(exe_path) in call_args[0]


class TestCompileWithDotnet:
    """Test compile_with_dotnet method"""
    
    def test_dotnet_compilation_success(self):
        """Test successful .NET compilation"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_bin_path') as mock_bin:
            mock_bin.return_value = Path("/test/bin")
            
            with patch('platform_utils.PlatformManager.get_dotnet_path') as mock_dotnet:
                mock_dotnet.return_value = Path("/test/bin/dotnet")
                
                with patch('pathlib.Path.exists') as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout="Build succeeded", stderr="")
                        
                        result = manager.compile_with_dotnet("project.csproj")
                        
                        assert result.success
                        # Check that build command was constructed properly
                        call_args = mock_run.call_args[0][0]
                        assert "build" in call_args
                        assert "project.csproj" in call_args
    
    def test_dotnet_compilation_with_output(self):
        """Test .NET compilation with output path"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_bin_path') as mock_bin:
            mock_bin.return_value = Path("/test/bin")
            
            with patch('platform_utils.PlatformManager.get_dotnet_path') as mock_dotnet:
                mock_dotnet.return_value = Path("/test/bin/dotnet")
                
                with patch('pathlib.Path.exists') as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                        
                        result = manager.compile_with_dotnet(
                            "project.csproj",
                            output_path="build/output",
                            configuration="Debug"
                        )
                        
                        call_args = mock_run.call_args[0][0]
                        assert "--output" in call_args
                        assert "build/output" in call_args
                        assert "--configuration" in call_args
                        assert "Debug" in call_args


class TestCompileWithMake:
    """Test compile_with_make method"""
    
    def test_make_compilation_success(self):
        """Test successful make compilation"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_bin_path') as mock_bin:
            mock_bin.return_value = Path("/test/bin")
            
            with patch('platform_utils.PlatformManager.get_make_path') as mock_make:
                mock_make.return_value = Path("/test/bin/make")
                
                with patch('pathlib.Path.exists') as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout="Build complete", stderr="")
                        
                        result = manager.compile_with_make("/project/src")
                        
                        assert result.success
    
    def test_make_compilation_with_target(self):
        """Test make compilation with target"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_bin_path') as mock_bin:
            mock_bin.return_value = Path("/test/bin")
            
            with patch('platform_utils.PlatformManager.get_make_path') as mock_make:
                mock_make.return_value = Path("/test/bin/make")
                
                with patch('pathlib.Path.exists') as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                        
                        result = manager.compile_with_make(
                            "/project/src",
                            target="all",
                            additional_args=["-j4"]
                        )
                        
                        call_args = mock_run.call_args[0][0]
                        assert "all" in call_args
                        assert "-j4" in call_args
    
    def test_make_compilation_with_env_vars(self):
        """Test make compilation with environment variables"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_bin_path') as mock_bin:
            mock_bin.return_value = Path("/test/bin")
            
            with patch('platform_utils.PlatformManager.get_make_path') as mock_make:
                mock_make.return_value = Path("/test/bin/make")
                
                with patch('pathlib.Path.exists') as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch('subprocess.run') as mock_run:
                        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                        
                        env_vars = {"CUSTOM_VAR": "value"}
                        result = manager.compile_with_make(
                            "/project/src",
                            env_vars=env_vars
                        )
                        
                        # Check that environment was passed
                        call_kwargs = mock_run.call_args[1]
                        assert "env" in call_kwargs
                        assert "CUSTOM_VAR" in call_kwargs["env"]


class TestConvenienceFunctions:
    """Test module-level convenience functions"""
    
    def test_run_tool_convenience(self):
        """Test run_tool convenience function"""
        with patch.object(subprocess_manager, 'run_tool') as mock_run:
            mock_run.return_value = ProcessResult(0, "output", "", [], True)
            
            result = run_tool("test-tool", ["arg1"])
            
            assert result.success
            mock_run.assert_called_once_with("test-tool", ["arg1"])
    
    def test_run_shell_command_convenience(self):
        """Test run_shell_command convenience function"""
        with patch.object(subprocess_manager, 'run_shell_command') as mock_run:
            mock_run.return_value = ProcessResult(0, "output", "", [], True)
            
            result = run_shell_command("echo test")
            
            assert result.success
            mock_run.assert_called_once_with("echo test")
    
    def test_run_external_executable_convenience(self):
        """Test run_external_executable convenience function"""
        with patch.object(subprocess_manager, 'run_external_executable') as mock_run:
            mock_run.return_value = ProcessResult(0, "output", "", [], True)
            
            result = run_external_executable("python", ["--version"])
            
            assert result.success
            mock_run.assert_called_once_with("python", ["--version"])


class TestSingletonInstance:
    """Test that subprocess_manager singleton works correctly"""
    
    def test_singleton_exists(self):
        """Test that subprocess_manager singleton is available"""
        assert subprocess_manager is not None
        assert isinstance(subprocess_manager, SubprocessManager)
    
    def test_singleton_has_logger(self):
        """Test that singleton has a logger"""
        assert subprocess_manager.logger is not None


class TestCwdHandling:
    """Test working directory handling"""
    
    def test_run_tool_default_cwd(self):
        """Test run_tool uses executable_dir as default cwd"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                manager.run_tool("test-tool")
                
                # Check that cwd was set
                call_kwargs = mock_run.call_args[1]
                assert "cwd" in call_kwargs
    
    def test_run_tool_custom_cwd(self):
        """Test run_tool with custom cwd"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                custom_cwd = "/custom/dir"
                manager.run_tool("test-tool", cwd=custom_cwd)
                
                call_kwargs = mock_run.call_args[1]
                assert str(custom_cwd) in call_kwargs["cwd"]


class TestErrorScenarios:
    """Test various error scenarios"""
    
    def test_unexpected_exception_in_run_tool(self):
        """Test handling of unexpected exceptions"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock()
            mock_tool_path.exists.return_value = True
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = RuntimeError("Unexpected error")
                
                result = manager.run_tool("test-tool")
                
                assert result.failed
                assert "Unexpected error" in result.stderr
    
    def test_none_stdout_stderr(self):
        """Test handling when stdout/stderr are None"""
        manager = SubprocessManager()
        
        with patch('path_utils.PathManager.get_tool_path') as mock_path:
            mock_tool_path = Mock(spec=Path)
            mock_tool_path.exists.return_value = True
            mock_tool_path.__str__ = Mock(return_value="/fake/tool")
            mock_path.return_value = mock_tool_path
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=None,
                    stderr=None
                )
                
                result = manager.run_tool("test-tool")
                
                assert result.success
                assert result.stdout == ""
                assert result.stderr == ""
