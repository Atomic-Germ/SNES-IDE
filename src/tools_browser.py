"""SNES-IDE - Integrated Development Environment for SNES.

A Textual-based TUI providing:
- Tool management (install, update, verify, uninstall)
- Code browsing with syntax highlighting
- Project file navigation

Run with:
    python src/snes-ide.py --tui
"""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import sys
import json
import tempfile
import time
import urllib.request
import tarfile
from pathlib import Path
from typing import Dict, Any, Callable

from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.traceback import Traceback

from textual.app import App, ComposeResult
from textual.command import Hit, Hits, Provider
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive, var
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Footer, Header, Label, ListItem, ListView, Static, Rule, 
    Button, RichLog, ProgressBar, DirectoryTree, Collapsible, Tree
)
from textual.widgets.tree import TreeNode
import webbrowser

# Note: textual-terminal was considered for embedded terminal support, but it uses
# pty.fork() which only works on Linux with a real terminal - not in web/browser mode.
# We use app.suspend() for terminal mode and show manual instructions for browser mode.
#
# FUTURE ENHANCEMENT: Find or create a browser-compatible terminal widget that can:
# - Display output from subprocess commands in real-time
# - Accept password input for sudo (securely)
# - Work in both terminal and Textual web/browser modes
# Options to explore: WebSocket-based PTY proxy, or a Textual-native terminal emulator


def get_platform() -> str:
    """Get the current platform identifier."""
    system = platform.system()
    if system == "Darwin":
        return "darwin"
    elif system == "Windows":
        return "win32"
    return "linux"


def get_package_manager() -> str | None:
    """Detect the available package manager on the system."""
    plat = get_platform()
    if plat == "darwin":
        if shutil.which("brew"):
            return "brew"
    elif plat == "linux":
        if shutil.which("apt-get"):
            return "apt"
        elif shutil.which("dnf"):
            return "dnf"
    elif plat == "win32":
        if shutil.which("pacman"):  # MSYS2
            return "msys2"
    return None


def check_package_available(package_name: str, pkg_manager: str | None = None) -> bool:
    """Check if a package is available in the system package manager.
    
    Args:
        package_name: Name of the package to check
        pkg_manager: Package manager to use (auto-detected if None)
    
    Returns:
        True if package is available for installation
    """
    if pkg_manager is None:
        pkg_manager = get_package_manager()
    
    if not pkg_manager:
        return False
    
    try:
        if pkg_manager == "apt":
            # Use apt-cache to check if package exists
            result = subprocess.run(
                ["apt-cache", "show", package_name],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        
        elif pkg_manager == "dnf":
            # Use dnf info to check if package exists
            result = subprocess.run(
                ["dnf", "info", "--available", package_name],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        
        elif pkg_manager == "brew":
            # Use brew info to check if formula/cask exists
            result = subprocess.run(
                ["brew", "info", package_name],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        
        elif pkg_manager == "msys2":
            # Use pacman to check if package exists
            result = subprocess.run(
                ["pacman", "-Ss", f"^{package_name}$"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0 and package_name in result.stdout.decode()
        
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False
    
    return False


def check_package_available_cached(package_name: str, pkg_manager: str | None = None) -> bool:
    """Cached version of check_package_available.
    
    Results are cached for the lifetime of the process to avoid
    repeated slow lookups.
    """
    if not hasattr(check_package_available_cached, '_cache'):
        check_package_available_cached._cache = {}
    
    if pkg_manager is None:
        pkg_manager = get_package_manager()
    
    cache_key = (package_name, pkg_manager)
    if cache_key not in check_package_available_cached._cache:
        check_package_available_cached._cache[cache_key] = check_package_available(package_name, pkg_manager)
    
    return check_package_available_cached._cache[cache_key]


class ToolInstaller:
    """Handles downloading, building, and installing tools."""

    def __init__(
        self, 
        tools_dir: Path | None = None, 
        log_callback: Callable[[str], None] | None = None,
        progress_callback: Callable[[float, float, float | None], None] | None = None,
        sudo_callback: Callable[[list[str]], bool] | None = None
    ):
        """Initialize the installer.
        
        Args:
            tools_dir: Directory to install tools to. Defaults to ~/.snes-ide/tools
            log_callback: Function to call with log messages
            progress_callback: Function to call with (current, total, eta_seconds)
            sudo_callback: Function to call when sudo command needs to run in terminal.
                          Takes command list, returns True if successful.
        """
        if tools_dir is None:
            tools_dir = Path.home() / ".snes-ide" / "tools"
        self.tools_dir = tools_dir
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.log = log_callback or print
        self.progress_callback = progress_callback
        self.sudo_callback = sudo_callback
        self.platform = get_platform()
        self.pkg_manager = get_package_manager()

    def update_progress(self, current: float, total: float, eta_seconds: float | None = None) -> None:
        """Update the progress bar."""
        if self.progress_callback:
            self.progress_callback(current, total, eta_seconds)

    def log_info(self, msg: str) -> None:
        """Log an info message."""
        self.log(f"[cyan]INFO:[/cyan] {msg}")

    def log_error(self, msg: str) -> None:
        """Log an error message."""
        self.log(f"[red]ERROR:[/red] {msg}")

    def log_success(self, msg: str) -> None:
        """Log a success message."""
        self.log(f"[green]SUCCESS:[/green] {msg}")

    def log_cmd(self, msg: str) -> None:
        """Log a command being run."""
        self.log(f"[yellow]RUN:[/yellow] {msg}")

    async def install_dependencies(self, tool_config: Dict[str, Any]) -> bool:
        """Install system dependencies for a tool.
        
        Returns True if successful, False otherwise.
        """
        deps = tool_config.get("dependencies", {})
        plat_deps = deps.get(self.platform, {})
        
        if not plat_deps:
            self.log_info("No dependencies to install")
            return True

        if not self.pkg_manager:
            self.log_error(f"No package manager detected for {self.platform}")
            return False

        packages = plat_deps.get(self.pkg_manager, [])
        if not packages:
            self.log_info(f"No {self.pkg_manager} packages required")
            return True

        # Handle dict-style dependency specs with custom commands (e.g., dnf builddep)
        if isinstance(packages, dict):
            custom_cmd = packages.get("command", "install")
            custom_args = packages.get("args", [])
            self.log_info(f"Using custom command: {self.pkg_manager} {custom_cmd} {' '.join(custom_args)}")
            # For builddep and similar, we can't easily check if deps are installed
            # So we just run the command
            missing_packages = custom_args  # Treat args as "packages" for command building
        else:
            # Standard package list - check which are already available in PATH
            missing_packages = []
            for pkg in packages:
                # Map package names to binary names for common packages
                binary_name = self._package_to_binary(pkg)
                if binary_name and shutil.which(binary_name):
                    self.log_info(f"✓ {pkg} already available ({binary_name})")
            else:
                missing_packages.append(pkg)

        if not missing_packages:
            self.log_success("All dependencies already available!")
            return True

        self.log_info(f"Missing dependencies: {', '.join(missing_packages)}")

        # Check if we need sudo
        needs_sudo = self.pkg_manager in ("apt", "dnf")

        # Build the install command
        if self.pkg_manager == "apt":
            # Check if packages is a dict with custom command
            if isinstance(packages, dict):
                apt_cmd = packages.get("command", "install")
                apt_args = packages.get("args", [])
                cmd = ["sudo", "apt-get", apt_cmd, "-y"] + apt_args
            else:
                cmd = ["sudo", "apt-get", "install", "-y"] + missing_packages
        elif self.pkg_manager == "dnf":
            # Check if packages is a dict with custom command (e.g., builddep)
            if isinstance(packages, dict):
                dnf_cmd = packages.get("command", "install")
                dnf_args = packages.get("args", [])
                cmd = ["sudo", "dnf", dnf_cmd, "-y"] + dnf_args
            else:
                cmd = ["sudo", "dnf", "install", "-y"] + missing_packages
        elif self.pkg_manager == "brew":
            cmd = ["brew", "install"] + missing_packages
        elif self.pkg_manager == "msys2":
            cmd = ["pacman", "-S", "--noconfirm"] + missing_packages
        else:
            self.log_error(f"Unknown package manager: {self.pkg_manager}")
            return False

        self.log_cmd(" ".join(cmd))
        
        # If we need sudo and have a sudo callback, use it to run in terminal
        if needs_sudo and self.sudo_callback:
            self.log_info("[yellow]Root privileges required - switching to terminal...[/yellow]")
            self.log_info("[dim]The TUI will pause while you enter your password[/dim]")
            
            # Run synchronously via the callback (which suspends TUI)
            success = self.sudo_callback(cmd)
            
            if success:
                self.log_success("Dependencies installed")
            else:
                self.log_error("Dependency installation failed or was cancelled")
            return success
        
        # Non-sudo path (brew, msys2) or no callback - run async with streaming
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Stream output line by line in real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                self.log(f"  {line.decode().rstrip()}")
            
            await process.wait()
            
            if process.returncode != 0:
                self.log_error(f"Dependency installation failed with code {process.returncode}")
                return False
            
            self.log_success("Dependencies installed")
            return True
        except Exception as e:
            self.log_error(f"Failed to install dependencies: {e}")
            return False

    def _package_to_binary(self, package: str) -> str | None:
        """Map a package name to its primary binary name for PATH checking."""
        # Common mappings for build dependencies
        mappings = {
            # Build essentials
            "build-essential": "gcc",
            "gcc": "gcc",
            "g++": "g++",
            "gcc-c++": "g++",
            "make": "make",
            "cmake": "cmake",
            "git": "git",
            "mingw-w64-x86_64-gcc": "gcc",
            "mingw-w64-x86_64-cmake": "cmake",
            # Libraries - these don't have binaries, return None
            "libpng-dev": None,
            "libpng-devel": None,
            "libpng": None,
            "mingw-w64-x86_64-libpng": None,
            "zlib1g-dev": None,
            "zlib-devel": None,
            "zlib": None,
        }
        return mappings.get(package, package)  # Default: try package name as binary
        return False

    async def download_source(self, tool_config: Dict[str, Any]) -> Path | None:
        """Download the source code for a tool.
        
        Returns the path to the source directory, or None on failure.
        """
        source = tool_config.get("source", {})
        source_type = source.get("type")
        tool_name = tool_config.get("name", "unknown")
        
        tool_dir = self.tools_dir / tool_name
        
        if source_type == "git":
            return await self._clone_git(source, tool_dir)
        elif source_type == "tarball":
            return await self._download_tarball(source, tool_dir)
        else:
            self.log_error(f"Unknown source type: {source_type}")
            return None

    async def _clone_git(self, source: Dict[str, Any], tool_dir: Path) -> Path | None:
        """Clone a git repository."""
        url = source.get("url")
        if not url:
            self.log_error("No git URL specified")
            return None

        branch = source.get("branch", "master")
        tag = source.get("tag")

        # Remove existing directory if it exists
        if tool_dir.exists():
            self.log_info(f"Removing existing directory: {tool_dir}")
            shutil.rmtree(tool_dir)

        self.log_info(f"Cloning {url}")
        
        cmd = ["git", "clone", "--depth", "1"]
        if tag:
            cmd.extend(["--branch", tag])
        elif branch:
            cmd.extend(["--branch", branch])
        cmd.extend([url, str(tool_dir)])

        self.log_cmd(" ".join(cmd))
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            # Stream output line by line in real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                self.log(f"  {line.decode().rstrip()}")
            
            await process.wait()

            if process.returncode != 0:
                self.log_error(f"Git clone failed with code {process.returncode}")
                return None

            self.log_success(f"Cloned to {tool_dir}")
            return tool_dir
        except Exception as e:
            self.log_error(f"Git clone failed: {e}")
            return None

    async def _download_tarball(self, source: Dict[str, Any], tool_dir: Path) -> Path | None:
        """Download and extract a tarball."""
        url = source.get("url")
        if not url:
            self.log_error("No tarball URL specified")
            return None

        strip_components = source.get("strip_components", 0)

        # Remove existing directory if it exists
        if tool_dir.exists():
            self.log_info(f"Removing existing directory: {tool_dir}")
            shutil.rmtree(tool_dir)

        tool_dir.mkdir(parents=True, exist_ok=True)

        self.log_info(f"Downloading {url}")

        try:
            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            # Use curl or wget for download (more reliable than urllib)
            if shutil.which("curl"):
                cmd = ["curl", "-L", "-o", str(tmp_path), url]
            elif shutil.which("wget"):
                cmd = ["wget", "-O", str(tmp_path), url]
            else:
                # Fallback to urllib
                self.log_info("Downloading with urllib...")
                urllib.request.urlretrieve(url, tmp_path)
                cmd = None

            if cmd:
                self.log_cmd(" ".join(cmd))
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                stdout, _ = await process.communicate()
                if process.returncode != 0:
                    self.log_error(f"Download failed with code {process.returncode}")
                    return None

            self.log_info(f"Extracting to {tool_dir}")

            # Extract tarball
            with tarfile.open(tmp_path, "r:*") as tar:
                if strip_components > 0:
                    # Extract with strip components
                    for member in tar.getmembers():
                        parts = Path(member.name).parts
                        if len(parts) > strip_components:
                            member.name = str(Path(*parts[strip_components:]))
                            tar.extract(member, tool_dir)
                else:
                    tar.extractall(tool_dir)

            tmp_path.unlink()
            self.log_success(f"Extracted to {tool_dir}")
            return tool_dir
        except Exception as e:
            self.log_error(f"Download/extract failed: {e}")
            return None

    async def build_tool(
        self, 
        tool_config: Dict[str, Any], 
        source_dir: Path
    ) -> bool:
        """Build a tool from source.
        
        Returns True if successful, False otherwise.
        """
        build = tool_config.get("build", {})
        plat_build = build.get(self.platform, {})
        commands = plat_build.get("commands", [])
        env_vars = plat_build.get("env", {})

        if not commands:
            self.log_info("No build commands specified")
            return True

        self.log_info(f"Building in {source_dir}")

        # Count source files to estimate build progress
        source_extensions = {'.c', '.cpp', '.cc', '.cxx', '.s', '.asm'}
        source_files = set()
        for ext in source_extensions:
            for f in source_dir.rglob(f'*{ext}'):
                # Store just the filename for matching
                source_files.add(f.name)
        
        total_source_files = max(len(source_files), 1)  # At least 1 to avoid division issues
        self.log_info(f"Found {len(source_files)} source files to track")
        
        # Set progress bar total to the number of source files for granular tracking
        self.update_progress(0, total_source_files, None)

        # Set up environment
        env = os.environ.copy()
        for key, value in env_vars.items():
            # Replace ${TOOL_DIR} with actual path
            value = value.replace("${TOOL_DIR}", str(source_dir))
            env[key] = value
            self.log_info(f"Setting {key}={value}")

        # Track files compiled across all commands and timing for ETA
        files_compiled = set()
        compile_times: list[float] = []  # Time taken to compile each file (excluding outliers)
        last_compile_time = time.monotonic()
        build_start_time = last_compile_time
        MIN_COMPILE_TIME = 0.5  # Ignore files that compile in under 0.5s (likely cached/trivial)
        
        for i, cmd_str in enumerate(commands, 1):
            self.log(f"[bold cyan]Command {i}/{len(commands)}:[/bold cyan]")
            self.log_cmd(cmd_str)
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd_str,
                    cwd=source_dir,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                
                # Stream output line by line in real-time
                line_count = 0
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    line_count += 1
                    decoded = line.decode().rstrip()
                    
                    # Check if this line mentions any of our source files
                    for src_file in source_files:
                        if src_file in decoded:
                            if src_file not in files_compiled:
                                # New file compiled - track timing
                                now = time.monotonic()
                                elapsed = now - last_compile_time
                                last_compile_time = now
                                files_compiled.add(src_file)
                                
                                # Only include substantial compile times (filter outliers)
                                if elapsed >= MIN_COMPILE_TIME:
                                    compile_times.append(elapsed)
                                
                                # Calculate ETA based on average compile time
                                eta_seconds = None
                                if compile_times:
                                    avg_time = sum(compile_times) / len(compile_times)
                                    remaining_files = total_source_files - len(files_compiled)
                                    eta_seconds = avg_time * remaining_files
                                
                                # Update progress with ETA
                                self.update_progress(len(files_compiled), total_source_files, eta_seconds)
                            break  # Only count once per line
                    
                    # Show all lines but dim the verbose compiler output
                    if any(x in decoded.lower() for x in ['warning:', 'error:', 'undefined']):
                        self.log(f"  [yellow]{decoded}[/yellow]")
                    elif decoded.startswith('cc ') or decoded.startswith('gcc ') or decoded.startswith('g++ '):
                        # Shorten long compile commands
                        if len(decoded) > 80:
                            self.log(f"  [dim]{decoded[:77]}...[/dim]")
                        else:
                            self.log(f"  [dim]{decoded}[/dim]")
                    else:
                        self.log(f"  {decoded}")

                await process.wait()
                
                if process.returncode != 0:
                    self.log_error(f"Build command failed with code {process.returncode}")
                    return False
                    
                self.log_info(f"Command completed ({line_count} lines, {len(files_compiled)}/{total_source_files} files)")
            except Exception as e:
                self.log_error(f"Build failed: {e}")
                return False

        # Ensure we show 100% at end of build with 0 ETA
        total_build_time = time.monotonic() - build_start_time
        self.update_progress(total_source_files, total_source_files, 0)
        self.log_success(f"Build completed ({len(files_compiled)} files in {total_build_time:.1f}s)")
        return True

    async def install_binary(self, tool_config: Dict[str, Any], source_dir: Path) -> bool:
        """Install the built binary to PATH.
        
        Returns True if successful, False otherwise.
        """
        binary_path = tool_config.get("binary_path", "")
        binary_name = tool_config.get("binary_name", {})
        
        if isinstance(binary_name, dict):
            binary_name = binary_name.get(self.platform)
        
        if not binary_name:
            binary_name = tool_config.get("name")

        if tool_config.get("is_sdk"):
            # For SDKs, we just add to shell config
            self.log_info(f"SDK detected - adding {source_dir} to environment")
            return await self._setup_sdk_env(tool_config, source_dir)

        # Find the binary
        if binary_path:
            binary_file = source_dir / binary_path
        else:
            binary_file = source_dir / binary_name

        if not binary_file.exists():
            # Search for it
            for pattern in [binary_name, f"**/{binary_name}"]:
                matches = list(source_dir.glob(pattern))
                if matches:
                    binary_file = matches[0]
                    break

        if not binary_file.exists():
            self.log_error(f"Binary not found: {binary_file}")
            return False

        # Install to ~/.local/bin
        install_dir = Path.home() / ".local" / "bin"
        install_dir.mkdir(parents=True, exist_ok=True)
        
        dest = install_dir / binary_name
        self.log_info(f"Installing {binary_file} -> {dest}")

        try:
            shutil.copy2(binary_file, dest)
            dest.chmod(0o755)
            self.log_success(f"Installed to {dest}")
            
            # Check if ~/.local/bin is in PATH
            if str(install_dir) not in os.environ.get("PATH", ""):
                self.log_info(f"Note: Add {install_dir} to your PATH")
            
            return True
        except Exception as e:
            self.log_error(f"Install failed: {e}")
            return False

    async def _setup_sdk_env(self, tool_config: Dict[str, Any], source_dir: Path) -> bool:
        """Set up environment variables for an SDK."""
        tool_name = tool_config.get("name", "").upper().replace("-", "_")
        env_var = f"{tool_name}_HOME"
        
        self.log_info(f"SDK installed at: {source_dir}")
        self.log_info(f"Add to your shell config:")
        self.log(f"  export {env_var}={source_dir}")
        self.log(f"  export PATH=$PATH:${env_var}/devkitsnes/tools")
        return True

    async def verify_installation(self, tool_config: Dict[str, Any]) -> bool:
        """Verify that a tool is properly installed.
        
        Returns True if verification passes, False otherwise.
        """
        verify_cmd = tool_config.get("verify_command", [])
        if not verify_cmd:
            self.log_info("No verify command specified")
            return True

        self.log_info(f"Verifying installation: {' '.join(verify_cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *verify_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await process.communicate()
            if stdout:
                for line in stdout.decode().splitlines()[:3]:  # First 3 lines
                    self.log(f"  {line}")

            if process.returncode == 0:
                self.log_success("Verification passed!")
                return True
            else:
                self.log_error(f"Verification failed with code {process.returncode}")
                return False
        except FileNotFoundError:
            self.log_error(f"Command not found: {verify_cmd[0]}")
            return False
        except Exception as e:
            self.log_error(f"Verification failed: {e}")
            return False

    async def install(self, tool_config: Dict[str, Any]) -> bool:
        """Perform a full installation of a tool.
        
        Returns True if successful, False otherwise.
        """
        tool_name = tool_config.get("name", "unknown")
        
        # Use a simple 4-step progress for non-build phases
        # Build phase will dynamically set its own total based on source file count
        
        self.update_progress(0, 4)
        
        self.log(f"[bold]{'='*50}[/bold]")
        self.log(f"[bold]Installing: {tool_name}[/bold]")
        self.log(f"[bold]{'='*50}[/bold]")
        self.log("")

        # Step 1: Install dependencies
        self.log("[bold cyan]Step 1/4: Installing dependencies...[/bold cyan]")
        if not await self.install_dependencies(tool_config):
            return False
        self.update_progress(1, 4)
        self.log("")

        # Step 2: Download source
        self.log("[bold cyan]Step 2/4: Downloading source...[/bold cyan]")
        source_dir = await self.download_source(tool_config)
        if not source_dir:
            return False
        self.update_progress(2, 4)
        self.log("")

        # Step 3: Build (progress bar will be dynamically set to source file count)
        self.log("[bold cyan]Step 3/4: Building...[/bold cyan]")
        if not await self.build_tool(tool_config, source_dir):
            return False
        # Build sets its own progress, now reset to step-based for remaining phases
        self.update_progress(3, 4)
        self.log("")

        # Step 4: Install binary
        self.log("[bold cyan]Step 4/4: Installing binary...[/bold cyan]")
        if not await self.install_binary(tool_config, source_dir):
            return False
        self.log("")

        # Verify
        self.log("[bold cyan]Verifying installation...[/bold cyan]")
        await self.verify_installation(tool_config)
        self.update_progress(4, 4)
        self.log("")

        self.log(f"[bold green]{'='*50}[/bold green]")
        self.log(f"[bold green]Installation of {tool_name} complete![/bold green]")
        self.log(f"[bold green]{'='*50}[/bold green]")
        return True

    async def uninstall(self, tool_config: Dict[str, Any]) -> bool:
        """Uninstall a tool by removing its binary and source.
        
        Returns True if successful, False otherwise.
        """
        tool_name = tool_config.get("name", "unknown")
        
        self.log(f"[bold]{'='*50}[/bold]")
        self.log(f"[bold]Uninstalling: {tool_name}[/bold]")
        self.log(f"[bold]{'='*50}[/bold]")
        self.log("")

        success = True

        # Remove binary from ~/.local/bin
        binary_name = tool_config.get("binary_name", {})
        if isinstance(binary_name, dict):
            binary_name = binary_name.get(self.platform)
        if not binary_name:
            binary_name = tool_name

        binary_path = Path.home() / ".local" / "bin" / binary_name
        if binary_path.exists():
            self.log_info(f"Removing binary: {binary_path}")
            try:
                binary_path.unlink()
                self.log_success(f"Removed {binary_path}")
            except Exception as e:
                self.log_error(f"Failed to remove binary: {e}")
                success = False
        else:
            self.log_info(f"Binary not found: {binary_path}")

        # Remove source directory
        source_dir = self.tools_dir / tool_name
        if source_dir.exists():
            self.log_info(f"Removing source: {source_dir}")
            try:
                shutil.rmtree(source_dir)
                self.log_success(f"Removed {source_dir}")
            except Exception as e:
                self.log_error(f"Failed to remove source: {e}")
                success = False
        else:
            self.log_info(f"Source directory not found: {source_dir}")

        if success:
            self.log(f"[bold green]{'='*50}[/bold green]")
            self.log(f"[bold green]Uninstall of {tool_name} complete![/bold green]")
            self.log(f"[bold green]{'='*50}[/bold green]")
        else:
            self.log(f"[bold yellow]{'='*50}[/bold yellow]")
            self.log(f"[bold yellow]Uninstall of {tool_name} had errors[/bold yellow]")
            self.log(f"[bold yellow]{'='*50}[/bold yellow]")
        
        return success


# Category to scripts mapping
CATEGORY_SCRIPTS: Dict[str, list[Dict[str, str]]] = {
    "audio": [
        {"label": "Convert WAV to BRR", "script": "audio-wav-brr-converter.py"},
        {"label": "Convert BRR to WAV", "script": "audio-brr-wav-converter.py"},
        {"label": "Generate Audio Sample", "script": "audio-sample-generator.py"},
        {"label": "Initialize Impulse Tracker", "script": "audio-impulse-tracker-init.py"},
    ],
    "graphics": [
        {"label": "Convert PNG to SNES", "script": "gfx-png-bmp-snes-converter.py"},
        {"label": "Edit PNG/BMP", "script": "gfx-png-bmp-editor.py"},
        {"label": "Edit TMX Map", "script": "gfx-tmx-editor.py"},
        {"label": "Convert TMX to TMJ", "script": "gfx-tmx-tmj-converter.py"},
    ],
    "emulators": [
        {"label": "Open in Emulator", "script": "open-emulator.py"},
    ],
    "sdk": [
        {"label": "Create PVSnesLib Project", "script": "create-pvsneslib-proj.py"},
        {"label": "Compile PVSnesLib Project", "script": "compile-pvsneslib-proj.py"},
        {"label": "Create DotnetSnes Project", "script": "create-dotnetsnes-proj.py"},
        {"label": "Compile DotnetSnes Project", "script": "compile-dotnetsnes-proj.py"},
        {"label": "Create JavaSnes Project", "script": "create-javasnes-proj.py"},
        {"label": "Compile JavaSnes Project", "script": "compile-javasnes-proj.py"},
    ],
}


class ToolCommandProvider(Provider):
    """Provides contextual commands for the selected tool."""

    @property
    def _app(self) -> "ToolBrowser":
        return self.app  # type: ignore

    async def search(self, query: str) -> Hits:
        """Yield command hits based on current context."""
        matcher = self.matcher(query)
        scripts_dir = Path(__file__).parent / "scripts"

        # Get currently selected tool
        detail_panel = self._app.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        tool_name = tool_data.get("name", "tool") if tool_data else None
        is_installed = tool_data.get("available", False) if tool_data else False
        category = tool_data.get("category") if tool_data else None

        # === Always-available commands ===
        
        # Refresh
        command = "Refresh Tools"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_refresh, help="Reload tool list")

        # Toggle sidebar
        command = "Toggle Sidebar"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_toggle_sidebar, help="Show/hide sidebar")

        # Open project
        command = "Open Project"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_open_project, help="Open project directory")

        # Toggle files/tools view
        command = "Toggle Code/Tools View"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_toggle_files, help="Switch between code and tools view")

        # Show tools view
        command = "Show Tools"
        score = matcher.match(command)
        if score > 0:
            yield Hit(score, command, self._app.action_show_tools, help="Show tools panel")

        # Open in Editor (only when viewing a file)
        current_file = self._app.current_file
        if current_file:
            command = f"Open in Editor: {current_file.name}"
            score = matcher.match(command)
            if score > 0:
                yield Hit(score, command, self._app.action_open_in_editor, help="Edit file in external editor")

        # === Tool-specific commands (require a selected tool) ===
        if tool_data:
            # Install (only if not installed)
            if not is_installed:
                command = f"Install {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_install, help=f"Download and build {tool_name}")

            # Update (re-run install, only if installed)
            if is_installed:
                command = f"Update {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_update, help=f"Re-download and rebuild {tool_name}")

            # Verify (only if installed)
            if is_installed:
                command = f"Verify {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_verify, help=f"Check {tool_name} installation")

            # Uninstall (only if installed)
            if is_installed:
                command = f"Uninstall {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, self._app.action_uninstall, help=f"Remove {tool_name} binary and source")

            # Documentation (if docs_url exists)
            docs_url = tool_data.get("docs_url")
            if docs_url:
                command = f"Documentation: {tool_name}"
                score = matcher.match(command)
                if score > 0:
                    yield Hit(score, command, lambda: webbrowser.open(docs_url), help=f"Open {tool_name} docs in browser")

            # Per-tool custom commands from tools.json
            tool_commands = tool_data.get("commands", [])
            for cmd in tool_commands:
                label = cmd.get("label", "")
                script = cmd.get("script", "")
                args = cmd.get("args", [])
                if label:
                    command = f"{tool_name}: {label}"
                    score = matcher.match(command)
                    if score > 0:
                        script_path = scripts_dir / script if script else None
                        yield Hit(
                            score, 
                            command, 
                            lambda s=script_path, a=args: self._run_script(s, a),
                            help=f"Run {script}" if script else label
                        )

            # Category-based commands
            if category and category in CATEGORY_SCRIPTS:
                for cat_cmd in CATEGORY_SCRIPTS[category]:
                    label = cat_cmd.get("label", "")
                    script = cat_cmd.get("script", "")
                    command = label
                    score = matcher.match(command)
                    if score > 0:
                        script_path = scripts_dir / script
                        yield Hit(
                            score,
                            command,
                            lambda s=script_path: self._run_script(s, []),
                            help=f"Run {script}"
                        )

    def _run_script(self, script_path: Path | None, args: list[str]) -> None:
        """Run a script with arguments."""
        if script_path and script_path.exists():
            self._app.notify(f"Running {script_path.name}...", severity="information")
            # For now, just notify - full implementation would run the script
            # subprocess.Popen([sys.executable, str(script_path)] + args)
        else:
            self._app.notify(f"Script not found: {script_path}", severity="error")


class InstallScreen(ModalScreen):
    """Modal screen for tool installation with progress log."""

    DEFAULT_CSS = """
    InstallScreen {
        align: center middle;
    }
    
    #install-dialog {
        width: 80%;
        height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #install-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        background: $accent;
        margin-bottom: 1;
    }
    
    #install-log {
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    #progress-container {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }
    
    #install-progress {
        width: 1fr;
    }
    
    #eta-label {
        width: auto;
        margin-left: 1;
        color: $text-muted;
    }
    
    #install-buttons {
        height: auto;
        align: center middle;
    }
    
    #install-buttons Button {
        margin: 0 2;
    }
    
    #mode-description {
        text-align: center;
        color: $text-muted;
        padding: 0 2;
        margin-bottom: 1;
        height: auto;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, tool_config: Dict[str, Any], title_prefix: str = "Installing"):
        super().__init__()
        self.tool_config = tool_config
        self.title_prefix = title_prefix
        self.installing = False
        self.install_complete = False
        self.install_mode = None  # "repo" or "build"
        self.repo_package_name = None  # Name of package in repo (if available)
        
        # Check if this tool supports repo install (either explicit or dynamic)
        self.has_repo_install, self.repo_package_name = self._check_repo_install()
    
    def _check_repo_install(self) -> tuple[bool, str | None]:
        """Check if this tool can be installed from package manager.
        
        First checks for explicit repo_install config, then tries dynamic
        detection using the tool's binary name (unless skip_repo_check is set).
        
        Returns:
            Tuple of (is_available, package_name)
        """
        tool_name = self.tool_config.get("name", "")
        plat = get_platform()
        pkg_manager = get_package_manager()
        
        # Check if dynamic repo checking is disabled for this tool
        if self.tool_config.get("skip_repo_check", False):
            return False, None
        
        # SDKs typically aren't in package managers in the right form
        if self.tool_config.get("is_sdk", False):
            return False, None
        
        # First check for explicit repo_install configuration
        repo_install = self.tool_config.get("repo_install", {})
        if repo_install:
            plat_config = repo_install.get(plat, {})
            
            # Check for a note (e.g., Windows manual install)
            if "note" in plat_config:
                return False, None
            
            if pkg_manager and pkg_manager in plat_config:
                packages = plat_config.get(pkg_manager, [])
                if packages:
                    return True, packages[0]
        
        # Dynamic detection: try the tool name as a package name
        if pkg_manager:
            # Try common package name patterns
            candidates = []
            
            # First priority: explicit package_name from config
            explicit_pkg = self.tool_config.get("package_name")
            if explicit_pkg:
                candidates.append(explicit_pkg)
            
            # Then try the tool name variations
            candidates.extend([
                tool_name,  # e.g., "tiled"
                tool_name.lower(),  # e.g., "Tiled" -> "tiled"
                tool_name.replace("-", ""),  # e.g., "wla-dx" -> "wladx"
                tool_name.replace("_", "-"),  # e.g., "some_tool" -> "some-tool"
            ])
            
            # Add binary name as candidate
            binary_name = self.tool_config.get("binary_name", {})
            if isinstance(binary_name, dict):
                bin_name = binary_name.get(plat, "")
                if bin_name and bin_name not in candidates:
                    candidates.append(bin_name.lower().replace(".exe", "").replace(".app", ""))
            
            # Check each candidate
            for candidate in candidates:
                if candidate and check_package_available_cached(candidate, pkg_manager):
                    return True, candidate
        
        return False, None
    
    def _get_repo_description(self) -> str:
        """Get the description for repo install option."""
        repo_install = self.tool_config.get("repo_install", {})
        if repo_install.get("description"):
            return repo_install["description"]
        if self.repo_package_name:
            return f"Install '{self.repo_package_name}' from package manager"
        return "Install from system package manager"

    def compose(self) -> ComposeResult:
        tool_name = self.tool_config.get("name", "Unknown")
        with Vertical(id="install-dialog"):
            yield Label(f"{self.title_prefix}: {tool_name}", id="install-title")
            yield Label("", id="mode-description")
            yield RichLog(id="install-log", highlight=True, markup=True)
            with Horizontal(id="progress-container"):
                yield ProgressBar(id="install-progress", total=100, show_eta=False)
                yield Label("", id="eta-label")
            with Horizontal(id="install-buttons"):
                if self.has_repo_install:
                    yield Button("Install", id="install-btn", variant="success")
                    yield Button("Build", id="build-btn", variant="primary")
                else:
                    yield Button("Start", id="start-btn", variant="primary")
                yield Button("Close", id="close-btn", variant="default")

    def on_mount(self) -> None:
        """Set up the dialog when mounted."""
        self.query_one("#close-btn", Button).disabled = True
        
        # Show description based on available options
        desc_label = self.query_one("#mode-description", Label)
        if self.has_repo_install:
            desc_label.update("[cyan]Install[/cyan] from package manager (fast) or [cyan]Build[/cyan] from source")
        else:
            desc_label.update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "start-btn":
            # Legacy single-button mode
            if not self.installing:
                self.installing = True
                self.install_mode = "build"
                event.button.disabled = True
                self._check_and_install()
        elif event.button.id == "install-btn":
            # Repo install mode
            if not self.installing:
                self.installing = True
                self.install_mode = "repo"
                event.button.disabled = True
                self.query_one("#build-btn", Button).disabled = True
                self.query_one("#mode-description", Label).update("[green]Installing from package manager...[/green]")
                self._run_repo_install()
        elif event.button.id == "build-btn":
            # Build from source mode
            if not self.installing:
                self.installing = True
                self.install_mode = "build"
                event.button.disabled = True
                self.query_one("#install-btn", Button).disabled = True
                self.query_one("#mode-description", Label).update("[blue]Building from source...[/blue]")
                self._check_and_install()
        elif event.button.id == "close-btn":
            self.dismiss(self.install_complete)

    def _run_repo_install(self) -> None:
        """Install from system package manager."""
        plat = get_platform()
        pkg_manager = get_package_manager()
        
        # Determine package name - either from explicit config or dynamic detection
        packages = []
        repo_install = self.tool_config.get("repo_install", {})
        plat_config = repo_install.get(plat, {})
        
        # Check for note (e.g., Windows manual install)
        if "note" in plat_config:
            self.log_message(f"[yellow]Note: {plat_config['note']}[/yellow]")
            self.installing = False
            self.query_one("#close-btn", Button).disabled = False
            return
        
        # Use explicit packages if defined, otherwise use dynamically detected name
        if pkg_manager and pkg_manager in plat_config:
            packages = plat_config.get(pkg_manager, [])
        
        if not packages and self.repo_package_name:
            packages = [self.repo_package_name]
        
        if not packages:
            self.log_message(f"[red]No packages found for {pkg_manager}[/red]")
            self.installing = False
            self.query_one("#close-btn", Button).disabled = False
            return
        
        # Build the install command
        if pkg_manager == "apt":
            cmd = ["sudo", "apt-get", "install", "-y"] + packages
            cmd_str = f"sudo apt-get install -y {' '.join(packages)}"
        elif pkg_manager == "dnf":
            cmd = ["sudo", "dnf", "install", "-y"] + packages
            cmd_str = f"sudo dnf install -y {' '.join(packages)}"
        elif pkg_manager == "pacman":
            cmd = ["sudo", "pacman", "-S", "--noconfirm"] + packages
            cmd_str = f"sudo pacman -S --noconfirm {' '.join(packages)}"
        elif pkg_manager == "brew":
            cmd = ["brew", "install"] + packages
            cmd_str = f"brew install {' '.join(packages)}"
        elif pkg_manager == "msys2":
            cmd = ["pacman", "-S", "--noconfirm"] + packages
            cmd_str = f"pacman -S --noconfirm {' '.join(packages)}"
        else:
            self.log_message(f"[red]Unknown package manager: {pkg_manager}[/red]")
            self.installing = False
            self.query_one("#close-btn", Button).disabled = False
            return
        
        self.log_message(f"[cyan]Installing: {' '.join(packages)}[/cyan]")
        
        # Check if we need sudo
        needs_sudo = pkg_manager in ("apt", "dnf", "pacman")
        
        if needs_sudo:
            # Check if we're in web/browser mode
            if self.app.is_web:
                self.log_message("[red]━━━ Manual Installation Required ━━━[/red]")
                self.log_message("[yellow]Running in browser mode - cannot run sudo commands.[/yellow]")
                self.log_message("")
                self.log_message("[cyan]Please install manually in a terminal:[/cyan]")
                self.log_message(f"[white bold]  {cmd_str}[/white bold]")
                self.log_message("")
                self.installing = False
                self.query_one("#close-btn", Button).disabled = False
                return
            
            # Run with sudo in terminal
            self.log_message("[dim]Switching to terminal for password entry...[/dim]")
            success = self._run_sudo_in_terminal(cmd)
            
            if success:
                self.log_message("[green]✓ Package installed successfully![/green]")
                self.install_complete = True
            else:
                self.log_message("[red]Installation failed or was cancelled[/red]")
            
            self.installing = False
            self.query_one("#close-btn", Button).disabled = False
        else:
            # No sudo needed (e.g., brew)
            self.run_worker(self._run_repo_install_async(cmd))

    def _check_and_install(self) -> None:
        """Check for sudo requirements and start installation."""
        # Check if dependencies need sudo
        deps = self.tool_config.get("dependencies", {})
        plat = get_platform()
        pkg_manager = get_package_manager()
        plat_deps = deps.get(plat, {})
        
        needs_sudo = False
        missing_packages = []
        
        if plat_deps and pkg_manager in ("apt", "dnf"):
            packages = plat_deps.get(pkg_manager, [])
            
            # Handle dict-style dependency specs with custom commands (e.g., dnf builddep)
            if isinstance(packages, dict):
                custom_cmd = packages.get("command", "install")
                custom_args = packages.get("args", [])
                # For builddep and similar, we can't easily check if deps are installed
                # So we always need to run the command
                needs_sudo = True
                missing_packages = custom_args
                is_custom_command = True
            else:
                is_custom_command = False
                # Check which packages are missing
                installer = ToolInstaller()
                for pkg in packages:
                    binary_name = installer._package_to_binary(pkg)
                    if not (binary_name and shutil.which(binary_name)):
                        missing_packages.append(pkg)
                
                if missing_packages:
                    needs_sudo = True
        else:
            is_custom_command = False
        
        if needs_sudo:
            self.log_message("[yellow]━━━ System Dependencies ━━━[/yellow]")
            
            # Build the command based on whether it's custom or standard
            if pkg_manager == "apt":
                if is_custom_command:
                    apt_cmd = packages.get("command", "install")
                    cmd = ["sudo", "apt-get", apt_cmd, "-y"] + missing_packages
                    cmd_str = f"sudo apt-get {apt_cmd} -y {' '.join(missing_packages)}"
                    self.log_message(f"[yellow]Running: {cmd_str}[/yellow]")
                else:
                    cmd = ["sudo", "apt-get", "install", "-y"] + missing_packages
                    cmd_str = f"sudo apt-get install -y {' '.join(missing_packages)}"
                    self.log_message(f"[yellow]Missing packages: {', '.join(missing_packages)}[/yellow]")
            else:  # dnf
                if is_custom_command:
                    dnf_cmd = packages.get("command", "install")
                    cmd = ["sudo", "dnf", dnf_cmd, "-y"] + missing_packages
                    cmd_str = f"sudo dnf {dnf_cmd} -y {' '.join(missing_packages)}"
                    self.log_message(f"[yellow]Running: {cmd_str}[/yellow]")
                else:
                    cmd = ["sudo", "dnf", "install", "-y"] + missing_packages
                    cmd_str = f"sudo dnf install -y {' '.join(missing_packages)}"
                    self.log_message(f"[yellow]Missing packages: {', '.join(missing_packages)}[/yellow]")
            
            # Check if we're in web/browser mode - can't do sudo there
            if self.app.is_web:
                self.log_message("[red]━━━ Manual Installation Required ━━━[/red]")
                self.log_message("[yellow]Running in browser mode - cannot run sudo commands.[/yellow]")
                self.log_message("")
                self.log_message("[cyan]Please install the dependencies manually in a terminal:[/cyan]")
                self.log_message(f"[white bold]  {cmd_str}[/white bold]")
                self.log_message("")
                self.log_message("[dim]After installing, close this dialog and try again.[/dim]")
                self.installing = False
                self.query_one("#start-btn", Button).disabled = False
                self.query_one("#start-btn", Button).label = "Retry"
                self.query_one("#close-btn", Button).disabled = False
                return
            
            # Use suspend() to run sudo in the terminal
            # Note: textual-terminal uses PTY which doesn't work in all environments
            self.log_message("[dim]Switching to terminal for password entry...[/dim]")
            success = self._run_sudo_in_terminal(cmd)
            
            if not success:
                self.log_message("[red]Dependency installation failed or was cancelled[/red]")
                self.log_message("[dim]You can try installing manually and retry[/dim]")
                self.installing = False
                self.query_one("#start-btn", Button).disabled = False
                self.query_one("#start-btn", Button).label = "Retry"
                self.query_one("#close-btn", Button).disabled = False
                return
            
            self.log_message("[green]✓ Dependencies installed[/green]")
        
        # Continue with the rest of the installation
        self.run_worker(self._run_install())

    def _run_sudo_in_terminal(self, cmd: list[str]) -> bool:
        """Run a sudo command by suspending the TUI.
        
        This allows the user to enter their password in the terminal.
        Returns True if the command succeeded.
        """
        success = False
        
        with self.app.suspend():
            print("\n" + "="*60)
            print("SNES-IDE: Installing system dependencies")
            print("="*60)
            print(f"\nRunning: {' '.join(cmd)}\n")
            
            try:
                result = subprocess.run(cmd)
                success = (result.returncode == 0)
                
                if success:
                    print("\n✓ Dependencies installed successfully!")
                else:
                    print(f"\n✗ Command failed with exit code {result.returncode}")
                
                print("\nPress Enter to return to SNES-IDE...")
                input()
            except KeyboardInterrupt:
                print("\n\nCancelled by user.")
                print("\nPress Enter to return to SNES-IDE...")
                try:
                    input()
                except:
                    pass
                success = False
            except Exception as e:
                print(f"\n✗ Error: {e}")
                print("\nPress Enter to return to SNES-IDE...")
                try:
                    input()
                except:
                    pass
                success = False
        
        return success

    async def _run_repo_install_async(self, cmd: list[str]) -> None:
        """Run repo install for package managers that don't need sudo (e.g., brew)."""
        self.log_message(f"[yellow]Running:[/yellow] {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            async for line in process.stdout:
                self.log_message(line.decode().rstrip())
            
            await process.wait()
            
            if process.returncode == 0:
                self.log_message("[green]✓ Package installed successfully![/green]")
                self.install_complete = True
            else:
                self.log_message(f"[red]Installation failed with exit code {process.returncode}[/red]")
        except Exception as e:
            self.log_message(f"[red]Error: {e}[/red]")
        
        self.installing = False
        self.query_one("#close-btn", Button).disabled = False

    def action_close(self) -> None:
        """Close the screen."""
        if not self.installing:
            self.dismiss(False)

    def log_message(self, msg: str) -> None:
        """Add a message to the log."""
        log = self.query_one("#install-log", RichLog)
        log.write(msg)

    def update_progress(self, current: float, total: float, eta_seconds: float | None = None) -> None:
        """Update the progress bar and ETA display."""
        progress_bar = self.query_one("#install-progress", ProgressBar)
        eta_label = self.query_one("#eta-label", Label)
        
        if total > 0:
            progress_bar.update(total=total, progress=current)
        
        # Format and display ETA
        if eta_seconds is not None:
            if eta_seconds <= 0:
                eta_label.update("")
            elif eta_seconds < 60:
                eta_label.update(f" ~{int(eta_seconds)}s remaining")
            elif eta_seconds < 3600:
                mins = int(eta_seconds // 60)
                secs = int(eta_seconds % 60)
                eta_label.update(f" ~{mins}m {secs}s remaining")
            else:
                hours = int(eta_seconds // 3600)
                mins = int((eta_seconds % 3600) // 60)
                eta_label.update(f" ~{hours}h {mins}m remaining")
        else:
            eta_label.update("")

    async def _run_install(self) -> None:
        """Run the installation process."""
        installer = ToolInstaller(
            log_callback=self.log_message,
            progress_callback=self.update_progress
            # No sudo_callback needed - we handle sudo deps upfront in _check_and_install
        )
        
        try:
            self.install_complete = await installer.install(self.tool_config)
        except Exception as e:
            self.log_message(f"[red]Installation failed: {e}[/red]")
            self.install_complete = False
        
        # Re-enable close button
        self.query_one("#close-btn", Button).disabled = False
        self.query_one("#start-btn", Button).label = "Done" if self.install_complete else "Failed"


class VerifyScreen(ModalScreen):
    """Modal screen for verifying a tool installation."""

    DEFAULT_CSS = """
    VerifyScreen {
        align: center middle;
    }
    
    #verify-dialog {
        width: 60%;
        height: auto;
        max-height: 50%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #verify-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        background: $accent;
        margin-bottom: 1;
    }
    
    #verify-log {
        height: auto;
        max-height: 10;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    #verify-buttons {
        height: auto;
        align: center middle;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__()
        self.tool_config = tool_config
        self.verify_success = False

    def compose(self) -> ComposeResult:
        tool_name = self.tool_config.get("name", "Unknown")
        with Vertical(id="verify-dialog"):
            yield Label(f"Verifying: {tool_name}", id="verify-title")
            yield RichLog(id="verify-log", highlight=True, markup=True)
            with Horizontal(id="verify-buttons"):
                yield Button("Close", id="close-btn", variant="default")

    def on_mount(self) -> None:
        """Start verification when mounted."""
        self.run_worker(self._run_verify())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss(self.verify_success)

    def action_close(self) -> None:
        """Close the screen."""
        self.dismiss(self.verify_success)

    async def _run_verify(self) -> None:
        """Run the verification."""
        log = self.query_one("#verify-log", RichLog)
        verify_cmd = self.tool_config.get("verify_command", [])
        
        if not verify_cmd:
            log.write("[yellow]No verify command specified[/yellow]")
            self.verify_success = True
            return

        log.write(f"[cyan]Running:[/cyan] {' '.join(verify_cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *verify_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await process.communicate()
            if stdout:
                for line in stdout.decode().splitlines()[:5]:
                    log.write(f"  {line}")

            if process.returncode == 0:
                log.write("[green bold]✓ Verification passed![/green bold]")
                self.verify_success = True
            else:
                log.write(f"[red bold]✗ Verification failed (code {process.returncode})[/red bold]")
                self.verify_success = False
        except FileNotFoundError:
            log.write(f"[red]Command not found: {verify_cmd[0]}[/red]")
            self.verify_success = False
        except Exception as e:
            log.write(f"[red]Error: {e}[/red]")
            self.verify_success = False


class UninstallScreen(ModalScreen):
    """Modal screen for uninstalling a tool."""

    DEFAULT_CSS = """
    UninstallScreen {
        align: center middle;
    }
    
    #uninstall-dialog {
        width: 60%;
        height: auto;
        max-height: 60%;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    
    #uninstall-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        background: $error;
        margin-bottom: 1;
    }
    
    #uninstall-log {
        height: auto;
        max-height: 15;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    #uninstall-buttons {
        height: auto;
        align: center middle;
    }
    
    #uninstall-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__()
        self.tool_config = tool_config
        self.uninstalling = False
        self.uninstall_complete = False

    def compose(self) -> ComposeResult:
        tool_name = self.tool_config.get("name", "Unknown")
        with Vertical(id="uninstall-dialog"):
            yield Label(f"⚠ Uninstall: {tool_name}", id="uninstall-title")
            yield RichLog(id="uninstall-log", highlight=True, markup=True)
            with Horizontal(id="uninstall-buttons"):
                yield Button("Confirm Uninstall", id="confirm-btn", variant="error")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_mount(self) -> None:
        """Show warning when mounted."""
        log = self.query_one("#uninstall-log", RichLog)
        tool_name = self.tool_config.get("name", "Unknown")
        log.write(f"[yellow]This will remove {tool_name}:[/yellow]")
        log.write(f"  • Binary from ~/.local/bin")
        log.write(f"  • Source from ~/.snes-ide/tools/{tool_name}")
        log.write("")
        log.write("[dim]Press 'Confirm Uninstall' to proceed or 'Cancel' to abort.[/dim]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm-btn":
            if not self.uninstalling:
                self.uninstalling = True
                event.button.disabled = True
                self.query_one("#cancel-btn", Button).disabled = True
                self.run_worker(self._run_uninstall())
        elif event.button.id == "cancel-btn":
            self.dismiss(False)

    def action_close(self) -> None:
        """Close the screen."""
        if not self.uninstalling:
            self.dismiss(False)

    async def _run_uninstall(self) -> None:
        """Run the uninstall process."""
        log = self.query_one("#uninstall-log", RichLog)
        log.write("")
        log.write("[bold]Starting uninstall...[/bold]")
        
        installer = ToolInstaller(
            log_callback=lambda msg: log.write(msg)
        )
        
        try:
            self.uninstall_complete = await installer.uninstall(self.tool_config)
        except Exception as e:
            log.write(f"[red]Uninstall failed: {e}[/red]")
            self.uninstall_complete = False
        
        # Update buttons
        self.query_one("#confirm-btn", Button).label = "Done" if self.uninstall_complete else "Failed"
        self.query_one("#cancel-btn", Button).label = "Close"
        self.query_one("#cancel-btn", Button).disabled = False


class CodeViewer(Static):
    """Syntax-highlighted code viewer panel."""

    DEFAULT_CSS = """
    CodeViewer {
        width: 100%;
        height: 100%;
        overflow: auto scroll;
        padding: 0 1;
        background: $surface;
    }
    
    CodeViewer > Static {
        width: auto;
    }
    """

    file_path: reactive[Path | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static(id="code-content")

    def watch_file_path(self, file_path: Path | None) -> None:
        """Load and display the file when path changes."""
        content = self.query_one("#code-content", Static)
        
        if file_path is None:
            content.update("[dim italic]Select a file from the project tree to view its contents[/dim italic]")
            return
        
        if not file_path.exists():
            content.update(f"[red]File not found: {file_path}[/red]")
            return
        
        if not file_path.is_file():
            content.update(f"[dim]{file_path} is a directory[/dim]")
            return
        
        try:
            # Check file size - don't try to load huge files
            file_size = file_path.stat().st_size
            if file_size > 1_000_000:  # 1MB limit
                content.update(f"[yellow]File too large to display ({file_size:,} bytes)[/yellow]")
                return
            
            code = file_path.read_text(encoding="utf-8", errors="replace")
            
            # Determine lexer from file extension
            ext = file_path.suffix.lower()
            lexer_map = {
                ".py": "python",
                ".c": "c",
                ".h": "c",
                ".cpp": "cpp",
                ".hpp": "cpp",
                ".cc": "cpp",
                ".cxx": "cpp",
                ".asm": "nasm",
                ".s": "gas",
                ".inc": "nasm",
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".toml": "toml",
                ".md": "markdown",
                ".rst": "rst",
                ".sh": "bash",
                ".bash": "bash",
                ".zsh": "zsh",
                ".fish": "fish",
                ".ps1": "powershell",
                ".bat": "batch",
                ".cmd": "batch",
                ".js": "javascript",
                ".ts": "typescript",
                ".html": "html",
                ".htm": "html",
                ".css": "css",
                ".tcss": "css",
                ".xml": "xml",
                ".java": "java",
                ".cs": "csharp",
                ".rs": "rust",
                ".go": "go",
                ".rb": "ruby",
                ".lua": "lua",
                ".make": "make",
                ".mk": "make",
            }
            # Handle Makefile specially
            if file_path.name.lower() in ("makefile", "gnumakefile"):
                lexer = "make"
            else:
                lexer = lexer_map.get(ext, "text")
            
            # Render Markdown files specially
            if ext in (".md", ".markdown"):
                md = Markdown(code)
                content.update(md)
            else:
                syntax = Syntax(
                    code, 
                    lexer, 
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=False,
                )
                content.update(syntax)
            
        except UnicodeDecodeError:
            content.update("[yellow]Binary file - cannot display[/yellow]")
        except Exception as e:
            content.update(Traceback(theme="monokai", width=None))


class ProjectTree(DirectoryTree):
    """Project file browser with filtering for relevant files."""
    
    DEFAULT_CSS = """
    ProjectTree {
        height: auto;
        max-height: 20;
        background: $panel;
        scrollbar-gutter: stable;
    }
    """

    # File extensions to show
    SHOW_EXTENSIONS = {
        ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
        ".asm", ".s", ".inc",
        ".py", ".java", ".cs",
        ".json", ".yaml", ".yml", ".toml",
        ".md", ".rst", ".txt",
        ".sh", ".bash", ".bat", ".cmd", ".ps1",
        ".xml", ".html", ".css",
        ".lua", ".rb", ".rs", ".go",
    }
    
    # Filenames to always show (case-insensitive)
    SHOW_NAMES = {
        "makefile", "gnumakefile", "cmakelists.txt", 
        "readme", "license", "copying", "changelog",
        ".gitignore", ".gitattributes",
    }
    
    # Directories to hide
    HIDE_DIRS = {
        "__pycache__", ".git", ".svn", ".hg", 
        "node_modules", ".venv", "venv", ".env",
        "build", "dist", ".tox", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", "target",
    }

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Filter paths to show only relevant files."""
        filtered = []
        for path in paths:
            name_lower = path.name.lower()
            
            if path.is_dir():
                # Hide certain directories
                if name_lower not in self.HIDE_DIRS:
                    filtered.append(path)
            else:
                # Show files with relevant extensions or special names
                if (path.suffix.lower() in self.SHOW_EXTENSIONS or 
                    name_lower in self.SHOW_NAMES or
                    any(name_lower.startswith(n) for n in self.SHOW_NAMES)):
                    filtered.append(path)
        
        return sorted(filtered, key=lambda p: (not p.is_dir(), p.name.lower()))


class Sidebar(Widget):
    """Animated sidebar with collapsible sections for Tools and Project."""

    DEFAULT_CSS = """
    Sidebar {
        width: 45;
        layer: sidebar;
        dock: left;
        offset-x: -100%;
        background: $panel;
        border-right: tall $background;
        transition: offset 200ms;
        overflow-y: auto;
        
        &.-visible {
            offset-x: 0;
        }
        
        #sidebar-title {
            dock: top;
            padding: 1 2;
            background: $accent;
            color: $text;
            text-style: bold;
            text-align: center;
        }
        
        Collapsible {
            padding: 0;
            border: none;
            background: $panel;
        }
        
        CollapsibleTitle {
            padding: 0 1;
            background: $primary 30%;
        }
        
        CollapsibleTitle:hover {
            background: $primary 50%;
        }
        
        ListView {
            height: auto;
            max-height: 25;
            background: $panel;
        }
        
        ListItem {
            padding: 0 2;
        }
        
        ListItem:hover {
            background: $boost;
        }
        
        ListItem.-selected {
            background: $accent 30%;
        }
        
        #project-tree-container {
            height: auto;
            max-height: 20;
            background: $panel;
        }
        
        #project-content {
            height: auto;
            max-height: 25;
            background: $panel;
        }
        
        #project-tree {
            height: auto;
            max-height: 24;
        }
        
        #no-project-label {
            padding: 1 2;
            color: $text-muted;
        }
    }
    """
    
    project_path: reactive[Path | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Label("⚡ SNES-IDE", id="sidebar-title")
        with VerticalScroll():
            with Collapsible(title="📁 Project", collapsed=False, id="project-section"):
                with Vertical(id="project-content"):
                    yield Label("[dim]No project open[/dim]", id="no-project-label")
                    # ProjectTree will be added here dynamically
            with Collapsible(title="🛠 Tools", collapsed=True, id="tools-section"):
                yield ListView(id="tool-list")
    
    def watch_project_path(self, project_path: Path | None) -> None:
        """Update the project tree when path changes."""
        project_content = self.query_one("#project-content", Vertical)
        no_project_label = self.query_one("#no-project-label", Label)
        
        # Remove existing ProjectTree if any
        for tree in self.query(ProjectTree):
            tree.remove()
        
        if project_path and project_path.exists():
            no_project_label.display = False
            tree = ProjectTree(project_path, id="project-tree")
            project_content.mount(tree)
            # Expand the project section
            self.query_one("#project-section", Collapsible).collapsed = False
        else:
            no_project_label.display = True
            no_project_label.update("[dim]No project open[/dim]")


class ToolDetailPanel(Static):
    """Panel showing details for the selected tool."""

    DEFAULT_CSS = """
    ToolDetailPanel {
        padding: 2 4;
        background: $surface;
        height: 100%;
        
        .tool-title {
            text-style: bold;
            text-align: center;
            padding: 1;
            background: $primary;
            margin-bottom: 1;
        }
        
        .status-available {
            color: $success;
            text-style: bold;
        }
        
        .status-missing {
            color: $error;
            text-style: bold;
        }
        
        .section-title {
            text-style: bold;
            margin-top: 1;
            color: $accent;
        }
        
        .section-content {
            margin-left: 2;
            color: $text-muted;
        }
    }
    """

    tool_data: reactive[Dict[str, Any] | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Label("Select a tool from the sidebar", id="detail-content")

    def watch_tool_data(self, tool_data: Dict[str, Any] | None) -> None:
        """Update the display when tool data changes."""
        self.query_one("#detail-content", Label).update(self._render_tool())

    def _render_tool(self) -> str:
        """Render the tool details as rich text."""
        if self.tool_data is None:
            return "[dim italic]← Press [b]s[/b] to toggle sidebar, then select a tool[/dim italic]"

        if not isinstance(self.tool_data, dict):
            return "[dim]Invalid tool data[/dim]"

        tool = self.tool_data
        lines = []

        # Tool name header
        name = tool.get("name", "Unknown")
        lines.append(f"[bold reverse] {name.upper()} [/bold reverse]")
        lines.append("")

        # Status
        available = tool.get("available", False)
        if available:
            lines.append("[green bold]✓ INSTALLED[/green bold]")
            if tool.get("path"):
                lines.append(f"  [dim]{tool['path']}[/dim]")
        else:
            lines.append("[red bold]✗ NOT INSTALLED[/red bold]")
        lines.append("")

        # Description
        if tool.get("description"):
            lines.append("[cyan bold]Description[/cyan bold]")
            lines.append(f"  {tool['description']}")
            lines.append("")

        # Category
        if tool.get("category"):
            lines.append("[cyan bold]Category[/cyan bold]")
            lines.append(f"  {tool['category']}")
            lines.append("")

        # Priority
        if tool.get("priority"):
            priority = tool["priority"]
            color = "yellow" if priority == "required" else "dim"
            lines.append("[cyan bold]Priority[/cyan bold]")
            lines.append(f"  [{color}]{priority.upper()}[/{color}]")
            lines.append("")

        # Source info
        if tool.get("source"):
            source = tool["source"]
            if isinstance(source, dict):
                lines.append("[cyan bold]Source[/cyan bold]")
                source_type = source.get("type", "unknown")
                lines.append(f"  Type: {source_type}")
                if source.get("url"):
                    url = source["url"]
                    if isinstance(url, str):
                        lines.append(f"  URL: [blue]{url}[/blue]")
                lines.append("")

        # Build commands (simplified)
        if tool.get("build"):
            build = tool["build"]
            if isinstance(build, dict):
                lines.append("[cyan bold]Build[/cyan bold]")
                for platform in ["linux", "darwin", "win32"]:
                    if platform in build:
                        cmds = build[platform].get("commands", [])
                        if cmds:
                            lines.append(f"  [dim]{platform}:[/dim] {len(cmds)} step(s)")
                lines.append("")

        return "\n".join(lines)


class ToolBrowser(App):
    """SNES-IDE - Integrated Development Environment for SNES."""

    TITLE = "SNES-IDE"
    COMMANDS = {ToolCommandProvider}
    
    DEFAULT_CSS = """
    Screen {
        layers: sidebar;
        background: $surface;
    }
    
    #main-content {
        width: 100%;
        height: 100%;
    }
    
    #content-switcher {
        width: 100%;
        height: 100%;
    }
    
    #tool-panel {
        width: 100%;
        height: 100%;
    }
    
    #code-panel {
        width: 100%;
        height: 100%;
    }
    
    #file-path-bar {
        dock: top;
        height: 1;
        padding: 0 1;
        background: $primary 30%;
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("s", "toggle_sidebar", "Sidebar"),
        ("f", "toggle_files", "Files"),
        ("e", "open_in_editor", "Edit"),
        ("i", "install", "Install"),
        ("o", "open_project", "Open Project"),
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "show_tools", "Tools View"),
    ]

    show_sidebar = reactive(False)
    current_view = reactive("tools")  # "tools" or "code"
    current_file: reactive[Path | None] = reactive(None)
    project_path: reactive[Path | None] = reactive(None)

    def __init__(self, project_path: Path | None = None):
        super().__init__()
        self.tools_by_category: Dict[str, list] = {}
        self.all_tools_map: Dict[str, Dict[str, Any]] = {}
        self._initial_project_path = project_path
        self.load_tools_from_json()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Sidebar()
        with Container(id="main-content"):
            # Tool detail view
            with VerticalScroll(id="tool-panel"):
                yield ToolDetailPanel()
            # Code viewer
            with Vertical(id="code-panel"):
                yield Label("", id="file-path-bar")
                yield CodeViewer()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the UI on mount."""
        self.populate_tool_list()
        # Start with sidebar visible
        self.show_sidebar = True
        # Set initial project if provided
        if self._initial_project_path:
            self.project_path = self._initial_project_path
        else:
            # Default to current working directory
            self.project_path = Path.cwd()
        # Show tools panel by default
        self.current_view = "tools"
    
    def watch_current_view(self, view: str) -> None:
        """Switch between tool and code views."""
        tool_panel = self.query_one("#tool-panel")
        code_panel = self.query_one("#code-panel")
        
        if view == "tools":
            tool_panel.display = True
            code_panel.display = False
            self.sub_title = "Tools"
        else:
            tool_panel.display = False
            code_panel.display = True
            if self.current_file:
                self.sub_title = str(self.current_file.name)
    
    def watch_current_file(self, file_path: Path | None) -> None:
        """Update the code viewer when a file is selected."""
        code_viewer = self.query_one(CodeViewer)
        code_viewer.file_path = file_path
        
        path_bar = self.query_one("#file-path-bar", Label)
        if file_path:
            # Show relative path if within project
            if self.project_path and file_path.is_relative_to(self.project_path):
                rel_path = file_path.relative_to(self.project_path)
                path_bar.update(f"📄 {rel_path}")
            else:
                path_bar.update(f"📄 {file_path}")
            self.sub_title = file_path.name
        else:
            path_bar.update("")
    
    def watch_project_path(self, project_path: Path | None) -> None:
        """Update sidebar when project path changes."""
        sidebar = self.query_one(Sidebar)
        sidebar.project_path = project_path
        if project_path:
            self.notify(f"Opened project: {project_path.name}", severity="information")
    
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection from the project tree."""
        event.stop()
        self.current_file = event.path
        self.current_view = "code"
        # Auto-hide sidebar after selection
        self.show_sidebar = False
    
    def action_toggle_files(self) -> None:
        """Toggle between tools and code view."""
        if self.current_view == "tools":
            if self.current_file:
                self.current_view = "code"
            elif self.project_path:
                self.notify("Select a file from the Project tree", severity="information")
                self.show_sidebar = True
        else:
            self.current_view = "tools"
    
    def action_show_tools(self) -> None:
        """Show the tools panel."""
        self.current_view = "tools"
    
    def action_open_in_editor(self) -> None:
        """Open current file in external editor."""
        if not self.current_file:
            self.notify("No file selected", severity="warning")
            return
        
        if not self.current_file.exists():
            self.notify(f"File not found: {self.current_file}", severity="error")
            return
        
        # Get editor from environment or fallback to common editors
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
        if not editor:
            # Try common editors
            for fallback in ["nano", "vim", "vi", "code", "gedit", "kate"]:
                if shutil.which(fallback):
                    editor = fallback
                    break
        
        if not editor:
            self.notify("No editor found. Set $EDITOR environment variable.", severity="error")
            return
        
        file_path = self.current_file
        
        # Suspend the TUI, run editor, then resume
        with self.suspend():
            try:
                subprocess.run([editor, str(file_path)])
            except Exception as e:
                # Will show after resume
                pass
        
        # Refresh the file view after editor closes
        code_viewer = self.query_one(CodeViewer)
        # Force a refresh by toggling the path
        code_viewer.file_path = None
        code_viewer.file_path = file_path
        self.notify(f"Returned from {editor}", severity="information")
    
    def action_open_project(self) -> None:
        """Open a project directory (placeholder - could show a dialog)."""
        # For now, just use current directory
        # In future, could integrate with a file picker
        self.project_path = Path.cwd()
        self.show_sidebar = True
        # Expand project section
        try:
            project_section = self.query_one("#project-section", Collapsible)
            project_section.collapsed = False
        except Exception:
            pass

    def load_tools_from_json(self) -> None:
        """Load tools from tools.json."""
        # Try tools.json first, then tools_.json as fallback
        tools_json_path = Path(__file__).parent / "tools.json"
        if not tools_json_path.exists():
            tools_json_path = Path(__file__).parent / "tools_.json"

        if not tools_json_path.exists():
            return

        try:
            with open(tools_json_path) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return

        tools = data.get("tools", [])

        for tool_def in tools:
            tool_name = tool_def.get("name")
            if not tool_name:
                continue

            available = self._check_tool_available(tool_def)
            tool_record = {
                **tool_def,
                "available": available,
                "path": self._find_tool_path(tool_def) if available else None,
            }

            self.all_tools_map[tool_name] = tool_record

            category = tool_def.get("category", "other")
            if category not in self.tools_by_category:
                self.tools_by_category[category] = []
            self.tools_by_category[category].append(tool_record)

    def _check_tool_available(self, tool_def: Dict[str, Any]) -> bool:
        """Check if a tool is available in PATH."""
        import shutil

        # Check by tool name
        tool_name = tool_def.get("name")
        if tool_name and isinstance(tool_name, str) and shutil.which(tool_name):
            return True

        # Check binary_name
        binary_name = tool_def.get("binary_name")
        if binary_name:
            if isinstance(binary_name, dict):
                import platform
                plat = "darwin" if platform.system() == "Darwin" else "linux" if platform.system() == "Linux" else "win32"
                binary_name = binary_name.get(plat)
            if binary_name and isinstance(binary_name, str) and shutil.which(binary_name):
                return True

        return False

    def _find_tool_path(self, tool_def: Dict[str, Any]) -> str | None:
        """Find the full path to a tool."""
        import shutil

        tool_name = tool_def.get("name")
        if tool_name and isinstance(tool_name, str):
            path = shutil.which(tool_name)
            if path:
                return path

        binary_name = tool_def.get("binary_name")
        if binary_name:
            if isinstance(binary_name, dict):
                import platform
                plat = "darwin" if platform.system() == "Darwin" else "linux" if platform.system() == "Linux" else "win32"
                binary_name = binary_name.get(plat)
            if binary_name and isinstance(binary_name, str):
                path = shutil.which(binary_name)
                if path:
                    return path

        return None

    def populate_tool_list(self) -> None:
        """Populate the sidebar with tools."""
        list_view = self.query_one("#tool-list", ListView)
        list_view.clear()

        for category in sorted(self.tools_by_category.keys()):
            tools = self.tools_by_category[category]
            
            # Category header
            available_count = sum(1 for t in tools if t.get("available"))
            total_count = len(tools)
            cat_label = f"━━ {category.upper()} ({available_count}/{total_count}) ━━"
            list_view.append(ListItem(Label(f"[bold]{cat_label}[/bold]"), disabled=True))

            # Tools in category
            for tool in sorted(tools, key=lambda t: (not t.get("available"), t["name"])):
                icon = "[green]●[/green]" if tool.get("available") else "[red]○[/red]"
                item = ListItem(Label(f"{icon} {tool['name']}"))
                item.data = tool["name"]  # Store tool name for lookup
                list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle tool selection from list."""
        item = event.item
        if hasattr(item, "data") and item.data:
            tool_name = item.data
            if tool_name in self.all_tools_map:
                detail_panel = self.query_one(ToolDetailPanel)
                detail_panel.tool_data = self.all_tools_map[tool_name]
                # Auto-hide sidebar after selection
                self.show_sidebar = False

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        self.show_sidebar = not self.show_sidebar

    def watch_show_sidebar(self, show_sidebar: bool) -> None:
        """Update sidebar visibility class."""
        self.query_one(Sidebar).set_class(show_sidebar, "-visible")

    def action_refresh(self) -> None:
        """Refresh the tool list."""
        self.tools_by_category.clear()
        self.all_tools_map.clear()
        self.load_tools_from_json()
        self.populate_tool_list()

    def action_install(self) -> None:
        """Install the currently selected tool."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected. Press 's' to open sidebar and select a tool.", severity="warning")
            return
        
        if tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is already installed.", severity="information")
            return
        
        # Push the install screen
        self.push_screen(InstallScreen(tool_data), self._on_install_complete)

    def action_update(self) -> None:
        """Update (re-install) the currently selected tool."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected.", severity="warning")
            return
        
        if not tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is not installed. Use Install instead.", severity="warning")
            return
        
        # Push the install screen (update = re-install)
        self.push_screen(InstallScreen(tool_data, title_prefix="Updating"), self._on_install_complete)

    def action_verify(self) -> None:
        """Verify the currently selected tool's installation."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected.", severity="warning")
            return
        
        if not tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is not installed.", severity="warning")
            return
        
        verify_cmd = tool_data.get("verify_command", [])
        if not verify_cmd:
            self.notify(f"No verify command for {tool_data.get('name')}", severity="information")
            return
        
        # Run verify command and show result
        self.push_screen(VerifyScreen(tool_data), self._on_verify_complete)

    def action_uninstall(self) -> None:
        """Uninstall the currently selected tool."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected.", severity="warning")
            return
        
        if not tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is not installed.", severity="information")
            return
        
        # Push the uninstall screen
        self.push_screen(UninstallScreen(tool_data), self._on_uninstall_complete)

    def _on_install_complete(self, success: bool) -> None:
        """Handle install completion."""
        if success:
            self.notify("Installation complete! Refreshing...", severity="information")
            self.action_refresh()
        else:
            self.notify("Installation did not complete successfully.", severity="warning")

    def _on_verify_complete(self, success: bool) -> None:
        """Handle verify completion."""
        if success:
            self.notify("Verification passed!", severity="information")
        else:
            self.notify("Verification failed.", severity="warning")

    def _on_uninstall_complete(self, success: bool) -> None:
        """Handle uninstall completion."""
        if success:
            self.notify("Uninstall complete! Refreshing...", severity="information")
            self.action_refresh()
        else:
            self.notify("Uninstall had errors.", severity="warning")


if __name__ == "__main__":
    # Accept optional project path as argument
    project = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    ToolBrowser(project_path=project).run()
