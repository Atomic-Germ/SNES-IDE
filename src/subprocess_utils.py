"""
subprocess_utils.py - Safe cross-platform subprocess utilities for SNES-IDE
"""
import subprocess
import shutil
import os
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from dataclasses import dataclass
import logging

# Import our custom utilities
from path_utils import path_manager
from platform_utils import platform_manager


@dataclass
class ProcessResult:
    """
    Container for subprocess execution results
    """
    returncode: int
    stdout: str
    stderr: str
    command: List[str]
    success: bool
    
    @property
    def failed(self) -> bool:
        """Check if process failed"""
        return not self.success


class SubprocessManager:
    """
    Manages safe subprocess execution with cross-platform compatibility
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def run_tool(
        self, 
        tool_name: str, 
        args: Optional[List[str]] = None,
        cwd: Optional[Union[str, Path]] = None,
        capture_output: bool = True,
        text: bool = True,
        timeout: Optional[float] = None,
        check: bool = False,
        env: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ProcessResult:
        """
        Execute a SNES-IDE tool with proper path resolution
        
        Args:
            tool_name: Name of the tool (without extension)
            args: Arguments to pass to the tool
            cwd: Working directory for execution
            capture_output: Whether to capture stdout/stderr
            text: Whether to use text mode
            timeout: Timeout for execution
            check: Whether to raise exception on non-zero return code
            env: Environment variables
            **kwargs: Additional subprocess.run arguments
            
        Returns:
            ProcessResult with execution details
        """
        # Get the full tool path using path manager
        tool_path = path_manager.get_tool_path(tool_name)
        
        if not tool_path.exists():
            self.logger.error(f"Tool not found: {tool_path}")
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=f"Tool not found: {tool_path}",
                command=[str(tool_path)],
                success=False
            )
        
        # Build command
        command = [str(tool_path)]
        if args:
            command.extend(str(arg) for arg in args)
        
        # Set working directory
        if cwd is None:
            cwd = path_manager.executable_dir
        elif isinstance(cwd, str):
            cwd = Path(cwd)
        
        # Execute subprocess
        try:
            self.logger.debug(f"Executing: {' '.join(command)} (cwd: {cwd})")
            
            result = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                check=check,
                env=env,
                **kwargs
            )
            
            success = result.returncode == 0
            
            if success:
                self.logger.debug(f"Tool {tool_name} executed successfully")
            else:
                self.logger.warning(f"Tool {tool_name} failed with return code {result.returncode}")
            
            return ProcessResult(
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                command=command,
                success=success
            )
            
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Tool {tool_name} timed out after {timeout} seconds")
            return ProcessResult(
                returncode=-1,
                stdout=e.stdout.decode() if e.stdout and isinstance(e.stdout, bytes) else (e.stdout or ""),
                stderr=f"Process timed out after {timeout} seconds",
                command=command,
                success=False
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Tool {tool_name} failed: {e}")
            return ProcessResult(
                returncode=e.returncode,
                stdout=e.stdout or "",
                stderr=e.stderr or "",
                command=command,
                success=False
            )
        except Exception as e:
            self.logger.error(f"Unexpected error executing {tool_name}: {e}")
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=str(e),
                command=command,
                success=False
            )
    
    def run_shell_command(
        self,
        command: str,
        cwd: Optional[Union[str, Path]] = None,
        capture_output: bool = True,
        text: bool = True,
        timeout: Optional[float] = None,
        check: bool = False,
        env: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ProcessResult:
        """
        Execute a shell command with platform-appropriate shell
        
        Args:
            command: Shell command to execute
            cwd: Working directory for execution
            capture_output: Whether to capture stdout/stderr
            text: Whether to use text mode
            timeout: Timeout for execution
            check: Whether to raise exception on non-zero return code
            env: Environment variables
            **kwargs: Additional subprocess.run arguments
            
        Returns:
            ProcessResult with execution details
        """
        # Get platform-specific shell command
        shell_cmd = platform_manager.get_shell_command(command)
        
        # Set working directory
        if cwd is None:
            cwd = path_manager.executable_dir
        elif isinstance(cwd, str):
            cwd = Path(cwd)
        
        try:
            self.logger.debug(f"Executing shell command: {command} (cwd: {cwd})")
            
            result = subprocess.run(
                shell_cmd,
                cwd=str(cwd),
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                check=check,
                env=env,
                **kwargs
            )
            
            success = result.returncode == 0
            
            return ProcessResult(
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                command=shell_cmd,
                success=success
            )
            
        except Exception as e:
            self.logger.error(f"Error executing shell command '{command}': {e}")
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=str(e),
                command=shell_cmd,
                success=False
            )
    
    def run_external_executable(
        self,
        executable: Union[str, Path],
        args: Optional[List[str]] = None,
        cwd: Optional[Union[str, Path]] = None,
        capture_output: bool = True,
        text: bool = True,
        timeout: Optional[float] = None,
        check: bool = False,
        env: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> ProcessResult:
        """
        Execute an external executable with path validation
        
        Args:
            executable: Path to executable or executable name
            args: Arguments to pass to the executable
            cwd: Working directory for execution
            capture_output: Whether to capture stdout/stderr
            text: Whether to use text mode
            timeout: Timeout for execution
            check: Whether to raise exception on non-zero return code
            env: Environment variables
            **kwargs: Additional subprocess.run arguments
            
        Returns:
            ProcessResult with execution details
        """
        # Resolve executable path
        if isinstance(executable, str):
            # Try to find the executable in PATH
            resolved_path = shutil.which(executable)
            if resolved_path:
                executable_path = Path(resolved_path)
            else:
                executable_path = Path(executable)
        else:
            executable_path = executable
        
        # Validate executable exists
        if not executable_path.exists():
            self.logger.error(f"Executable not found: {executable_path}")
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=f"Executable not found: {executable_path}",
                command=[str(executable_path)],
                success=False
            )
        
        # Build command
        command = [str(executable_path)]
        if args:
            command.extend(str(arg) for arg in args)
        
        # Set working directory
        if cwd is None:
            cwd = Path.cwd()
        elif isinstance(cwd, str):
            cwd = Path(cwd)
        
        try:
            self.logger.debug(f"Executing external: {' '.join(command)} (cwd: {cwd})")
            
            result = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                check=check,
                env=env,
                **kwargs
            )
            
            success = result.returncode == 0
            
            return ProcessResult(
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                command=command,
                success=success
            )
            
        except Exception as e:
            self.logger.error(f"Error executing {executable_path}: {e}")
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=str(e),
                command=command,
                success=False
            )
    
    def compile_with_dotnet(
        self,
        project_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        configuration: str = "Release",
        additional_args: Optional[List[str]] = None
    ) -> ProcessResult:
        """
        Compile a .NET project using platform-specific .NET SDK
        
        Args:
            project_path: Path to project file or directory
            output_path: Output directory for compiled files
            configuration: Build configuration (Debug/Release)
            additional_args: Additional arguments for dotnet build
            
        Returns:
            ProcessResult with compilation details
        """
        # Get platform-specific .NET SDK path
        bin_dir = path_manager.get_bin_path()
        dotnet_path = platform_manager.get_dotnet_path(bin_dir)
        
        # Build arguments
        args = ["build", str(project_path)]
        args.extend(["--configuration", configuration])
        
        if output_path:
            args.extend(["--output", str(output_path)])
        
        if additional_args:
            args.extend(additional_args)
        
        return self.run_external_executable(
            dotnet_path,
            args,
            cwd=Path(project_path).parent if Path(project_path).is_file() else project_path
        )
    
    def compile_with_make(
        self,
        makefile_dir: Union[str, Path],
        target: Optional[str] = None,
        additional_args: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ProcessResult:
        """
        Compile using make with platform-specific make executable
        
        Args:
            makefile_dir: Directory containing Makefile
            target: Make target to build (default target if None)
            additional_args: Additional arguments for make
            env_vars: Environment variables to set
            
        Returns:
            ProcessResult with compilation details
        """
        # Get platform-specific make path
        bin_dir = path_manager.get_bin_path()
        make_path = platform_manager.get_make_path(bin_dir)
        
        # Build arguments
        args = []
        if target:
            args.append(target)
        
        if additional_args:
            args.extend(additional_args)
        
        # Set up environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        return self.run_external_executable(
            make_path,
            args,
            cwd=makefile_dir,
            env=env
        )


# Singleton instance for global use
subprocess_manager = SubprocessManager()

# Convenience functions for backward compatibility
def run_tool(tool_name: str, args: Optional[List[str]] = None, **kwargs) -> ProcessResult:
    """Run a SNES-IDE tool"""
    return subprocess_manager.run_tool(tool_name, args, **kwargs)

def run_shell_command(command: str, **kwargs) -> ProcessResult:
    """Run a shell command"""
    return subprocess_manager.run_shell_command(command, **kwargs)

def run_external_executable(executable: Union[str, Path], args: Optional[List[str]] = None, **kwargs) -> ProcessResult:
    """Run an external executable"""
    return subprocess_manager.run_external_executable(executable, args, **kwargs)
