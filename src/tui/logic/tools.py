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
from typing import Dict, Any, Callable, List, Tuple

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
            return result.returncode == 0
            
    except Exception:
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
        # Build phase is 75% of total progress (25%-100%), so scale total by 4/3
        # and start at 25% to reflect download/extract/deps already done
        progress_total = int(total_source_files * 4 / 3)
        progress_offset = progress_total // 4  # 25% starting point
        self.update_progress(progress_offset, progress_total, None)

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
                                
                                # Update progress with ETA (offset by 25% for pre-build phases)
                                self.update_progress(progress_offset + len(files_compiled), progress_total, eta_seconds)
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
        self.update_progress(progress_total, progress_total, 0)
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
        
        return success
