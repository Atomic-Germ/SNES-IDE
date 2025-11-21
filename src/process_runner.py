"""
Cross-platform process runner for SNES-IDE

This module provides unified subprocess execution across different platforms.
"""

import subprocess
import sys
import os
import platform
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from . import path_utils


class ProcessRunner:
    """Handles cross-platform process execution."""
    
    @staticmethod
    def run_command(
        cmd: List[str],
        cwd: Optional[str] = None,
        capture_output: bool = True,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """
        Run a command with cross-platform compatibility.
        
        Args:
            cmd: Command as list of strings
            cwd: Working directory
            capture_output: Whether to capture stdout/stderr
            timeout: Timeout in seconds
            env: Environment variables to use
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env=env or os.environ.copy()
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, '', f'Command timed out after {timeout} seconds'
        except Exception as e:
            return -1, '', str(e)
    
    @staticmethod
    def run_executable(
        executable: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        **kwargs
    ) -> Tuple[int, str, str]:
        """
        Run an executable with automatic platform-specific path resolution.
        
        Args:
            executable: Name of executable (with or without .exe)
            args: Arguments to pass to executable
            cwd: Working directory
            **kwargs: Additional arguments to pass to run_command
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        # Add platform-specific extension if needed
        exe_name = executable
        if path_utils.is_windows() and not executable.endswith('.exe'):
            exe_name = executable + '.exe'
        
        cmd = [exe_name]
        if args:
            cmd.extend(args)
        
        return ProcessRunner.run_command(cmd, cwd=cwd, **kwargs)
    
    @staticmethod
    def run_script(
        script_path: str,
        interpreter: str = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        **kwargs
    ) -> Tuple[int, str, str]:
        """
        Run a script with automatic interpreter detection.
        
        Args:
            script_path: Path to script
            interpreter: Interpreter to use (python, bash, etc.) - auto-detect if None
            args: Arguments to pass to script
            cwd: Working directory
            **kwargs: Additional arguments to pass to run_command
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        script_path = path_utils.normalize_path(script_path)
        
        if interpreter is None:
            ext = path_utils.get_file_extension(script_path)
            if ext == '.py':
                interpreter = sys.executable
            elif ext in ['.sh', '.bash']:
                interpreter = 'bash'
            elif ext == '.ps1':
                interpreter = 'powershell'
            else:
                # Try to run directly
                interpreter = None
        
        cmd = [interpreter, script_path] if interpreter else [script_path]
        if args:
            cmd.extend(args)
        
        return ProcessRunner.run_command(cmd, cwd=cwd, **kwargs)
    
    @staticmethod
    def get_env_with_path_addition(additional_path: str) -> Dict[str, str]:
        """
        Get environment variables with an additional path prepended to PATH.
        
        Args:
            additional_path: Path to add to the beginning of PATH
            
        Returns:
            Dict of environment variables
        """
        env = os.environ.copy()
        current_path = env.get('PATH', '')
        
        # Normalize the additional path
        additional_path = path_utils.normalize_path(additional_path)
        
        # Prepend to PATH
        if current_path:
            env['PATH'] = additional_path + os.pathsep + current_path
        else:
            env['PATH'] = additional_path
        
        return env


def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    capture_output: bool = True,
    timeout: Optional[int] = None
) -> Tuple[int, str, str]:
    """
    Convenience function to run a command.
    
    Args:
        cmd: Command as list
        cwd: Working directory
        capture_output: Capture output
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    return ProcessRunner.run_command(cmd, cwd, capture_output, timeout)


def run_executable(
    executable: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None
) -> Tuple[int, str, str]:
    """
    Convenience function to run an executable.
    
    Args:
        executable: Executable name
        args: Arguments
        cwd: Working directory
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    return ProcessRunner.run_executable(executable, args, cwd)


def run_script(
    script_path: str,
    interpreter: Optional[str] = None,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None
) -> Tuple[int, str, str]:
    """
    Convenience function to run a script.
    
    Args:
        script_path: Script path
        interpreter: Interpreter to use
        args: Arguments
        cwd: Working directory
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    return ProcessRunner.run_script(script_path, interpreter, args, cwd)
