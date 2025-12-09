from __future__ import annotations

import asyncio
import shutil
import subprocess
from typing import Any, Dict

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ProgressBar, RichLog

from ..logic.tools import (
    ToolInstaller,
    check_package_available_cached,
    get_package_manager,
    get_platform,
)


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
                
                # Re-enable appropriate button
                if self.install_mode == "build":
                    try:
                        self.query_one("#build-btn", Button).disabled = False
                        self.query_one("#build-btn", Button).label = "Retry"
                    except:
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
                
                # Re-enable appropriate button
                if self.install_mode == "build":
                    try:
                        self.query_one("#build-btn", Button).disabled = False
                        self.query_one("#build-btn", Button).label = "Retry"
                    except:
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
        self.query_one("#install-btn", Button).label = "Done" if self.install_complete else "Failed"

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
        
        # Update the appropriate button based on mode
        if self.install_mode == "repo":
            self.query_one("#install-btn", Button).label = "Done" if self.install_complete else "Failed"
        elif self.install_mode == "build":
            # Check if we have build-btn (dual mode) or start-btn (single mode)
            try:
                self.query_one("#build-btn", Button).label = "Done" if self.install_complete else "Failed"
            except:
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
