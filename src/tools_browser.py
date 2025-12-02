"""SNES-IDE Tool Manager TUI - Textual implementation.

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
import urllib.request
import tarfile
from pathlib import Path
from typing import Dict, Any, Callable

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static, Rule, Button, RichLog


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


class ToolInstaller:
    """Handles downloading, building, and installing tools."""

    def __init__(self, tools_dir: Path | None = None, log_callback: Callable[[str], None] | None = None):
        """Initialize the installer.
        
        Args:
            tools_dir: Directory to install tools to. Defaults to ~/.snes-ide/tools
            log_callback: Function to call with log messages
        """
        if tools_dir is None:
            tools_dir = Path.home() / ".snes-ide" / "tools"
        self.tools_dir = tools_dir
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.log = log_callback or print
        self.platform = get_platform()
        self.pkg_manager = get_package_manager()

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

        # Check which dependencies are already available in PATH
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
        
        if needs_sudo:
            self.log_info("[yellow]Root privileges required to install system packages[/yellow]")
            self.log_info("You may be prompted for your password...")

        # Build the install command
        if self.pkg_manager == "apt":
            cmd = ["sudo", "apt-get", "install", "-y"] + missing_packages
        elif self.pkg_manager == "dnf":
            cmd = ["sudo", "dnf", "install", "-y"] + missing_packages
        elif self.pkg_manager == "brew":
            cmd = ["brew", "install"] + missing_packages
        elif self.pkg_manager == "msys2":
            cmd = ["pacman", "-S", "--noconfirm"] + missing_packages
        else:
            self.log_error(f"Unknown package manager: {self.pkg_manager}")
            return False

        self.log_cmd(" ".join(cmd))
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            stdout, _ = await process.communicate()
            if stdout:
                for line in stdout.decode().splitlines():
                    self.log(f"  {line}")
            
            if process.returncode != 0:
                self.log_error(f"Dependency installation failed with code {process.returncode}")
                if needs_sudo:
                    self.log_info("[dim]Tip: You may need to run with proper sudo access[/dim]")
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
            stdout, _ = await process.communicate()
            if stdout:
                for line in stdout.decode().splitlines():
                    self.log(f"  {line}")

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

    async def build_tool(self, tool_config: Dict[str, Any], source_dir: Path) -> bool:
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

        # Set up environment
        env = os.environ.copy()
        for key, value in env_vars.items():
            # Replace ${TOOL_DIR} with actual path
            value = value.replace("${TOOL_DIR}", str(source_dir))
            env[key] = value
            self.log_info(f"Setting {key}={value}")

        for cmd_str in commands:
            self.log_cmd(cmd_str)
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd_str,
                    cwd=source_dir,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                stdout, _ = await process.communicate()
                if stdout:
                    for line in stdout.decode().splitlines():
                        self.log(f"  {line}")

                if process.returncode != 0:
                    self.log_error(f"Build command failed with code {process.returncode}")
                    return False
            except Exception as e:
                self.log_error(f"Build failed: {e}")
                return False

        self.log_success("Build completed")
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
        self.log(f"[bold]{'='*50}[/bold]")
        self.log(f"[bold]Installing: {tool_name}[/bold]")
        self.log(f"[bold]{'='*50}[/bold]")
        self.log("")

        # Step 1: Install dependencies
        self.log("[bold cyan]Step 1/4: Installing dependencies...[/bold cyan]")
        if not await self.install_dependencies(tool_config):
            return False
        self.log("")

        # Step 2: Download source
        self.log("[bold cyan]Step 2/4: Downloading source...[/bold cyan]")
        source_dir = await self.download_source(tool_config)
        if not source_dir:
            return False
        self.log("")

        # Step 3: Build
        self.log("[bold cyan]Step 3/4: Building...[/bold cyan]")
        if not await self.build_tool(tool_config, source_dir):
            return False
        self.log("")

        # Step 4: Install binary
        self.log("[bold cyan]Step 4/4: Installing binary...[/bold cyan]")
        if not await self.install_binary(tool_config, source_dir):
            return False
        self.log("")

        # Verify
        self.log("[bold cyan]Verifying installation...[/bold cyan]")
        await self.verify_installation(tool_config)
        self.log("")

        self.log(f"[bold green]{'='*50}[/bold green]")
        self.log(f"[bold green]Installation of {tool_name} complete![/bold green]")
        self.log(f"[bold green]{'='*50}[/bold green]")
        return True


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
    
    #install-buttons {
        height: auto;
        align: center middle;
    }
    
    #install-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__()
        self.tool_config = tool_config
        self.installing = False
        self.install_complete = False

    def compose(self) -> ComposeResult:
        tool_name = self.tool_config.get("name", "Unknown")
        with Vertical(id="install-dialog"):
            yield Label(f"Installing: {tool_name}", id="install-title")
            yield RichLog(id="install-log", highlight=True, markup=True)
            with Horizontal(id="install-buttons"):
                yield Button("Start Install", id="start-btn", variant="primary", flat=True, compact=True)
                yield Button("Close", id="close-btn", variant="default", flat=True, compact=True)

    def on_mount(self) -> None:
        """Start installation when mounted."""
        self.query_one("#close-btn", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "start-btn":
            if not self.installing:
                self.installing = True
                event.button.disabled = True
                self.run_worker(self._run_install())
        elif event.button.id == "close-btn":
            self.dismiss(self.install_complete)

    def action_close(self) -> None:
        """Close the screen."""
        if not self.installing:
            self.dismiss(False)

    def log_message(self, msg: str) -> None:
        """Add a message to the log."""
        log = self.query_one("#install-log", RichLog)
        log.write(msg)

    async def _run_install(self) -> None:
        """Run the installation process."""
        installer = ToolInstaller(log_callback=self.log_message)
        
        try:
            self.install_complete = await installer.install(self.tool_config)
        except Exception as e:
            self.log_message(f"[red]Installation failed: {e}[/red]")
            self.install_complete = False
        
        # Re-enable close button
        self.query_one("#close-btn", Button).disabled = False
        self.query_one("#start-btn", Button).label = "Done" if self.install_complete else "Failed"


class Sidebar(Widget):
    """Animated sidebar containing the tool list."""

    DEFAULT_CSS = """
    Sidebar {
        width: 40;
        layer: sidebar;
        dock: left;
        offset-x: -100%;
        background: $panel;
        border-right: tall $background;
        transition: offset 200ms;
        
        &.-visible {
            offset-x: 0;
        }
        
        & > Vertical {
            height: 100%;
        }
        
        #sidebar-title {
            dock: top;
            padding: 1 2;
            background: $accent;
            color: $text;
            text-style: bold;
            text-align: center;
        }
        
        ListView {
            height: 1fr;
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
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("🛠 SNES-IDE Tools", id="sidebar-title")
            yield ListView(id="tool-list")


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
    """SNES-IDE Tool Browser TUI."""

    TITLE = "SNES-IDE Tool Manager"
    
    DEFAULT_CSS = """
    Screen {
        layers: sidebar;
        background: $surface;
    }
    
    #main-content {
        width: 100%;
        height: 100%;
    }
    
    #welcome {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    
    #welcome Label {
        text-align: center;
    }
    """

    BINDINGS = [
        ("s", "toggle_sidebar", "Sidebar"),
        ("i", "install", "Install"),
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    show_sidebar = reactive(False)

    def __init__(self):
        super().__init__()
        self.tools_by_category: Dict[str, list] = {}
        self.all_tools_map: Dict[str, Dict[str, Any]] = {}
        self.load_tools_from_json()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Sidebar()
        with VerticalScroll(id="main-content"):
            yield ToolDetailPanel()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the UI on mount."""
        self.populate_tool_list()
        # Start with sidebar visible
        self.show_sidebar = True

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

    def _on_install_complete(self, success: bool) -> None:
        """Handle install completion."""
        if success:
            self.notify("Installation complete! Refreshing...", severity="information")
            self.action_refresh()
        else:
            self.notify("Installation did not complete successfully.", severity="warning")


if __name__ == "__main__":
    ToolBrowser().run()
