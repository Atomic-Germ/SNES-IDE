#!/usr/bin/env python3
"""Text User Interface for SNES Installer."""

import sys
from pathlib import Path
from typing import List, Dict, Any
import shutil
import subprocess

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.columns import Columns
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.status import Status

from snes_installer.installer import ToolInstaller


class SNESInstallerTUI:
    """Text User Interface for SNES development tools installer."""

    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.console = Console()
        self.installer = ToolInstaller(config_file)
        self.tools_config = self.installer.load_config()['tools']

    def is_tool_installed(self, tool_name: str) -> bool:
        """Check if a tool is already installed and available in PATH."""
        # Use the same logic as ToolInstaller.is_tool_installed
        return self.installer.is_tool_installed(tool_name)

    def get_installed_tools(self) -> List[str]:
        """Get list of tools that are already installed."""
        installed = []
        for tool in self.tools_config:
            tool_name = tool["name"]
            if self.is_tool_installed(tool_name):
                installed.append(tool_name)
        return installed

    def show_welcome(self) -> None:
        """Show welcome message and current status."""
        welcome_text = Text("SNES Development Tools Installer", style="bold blue")
        subtitle = Text("Cross-platform toolkit for SNES programming", style="dim")

        installed_tools = self.get_installed_tools()
        total_tools = len(self.tools_config)

        status_text = f"Installed: {len(installed_tools)}/{total_tools} tools"

        panel = Panel.fit(
            f"[bold]{welcome_text}[/bold]\n[dim]{subtitle}[/dim]\n\n{status_text}",
            title="🎮 Welcome",
            border_style="blue"
        )
        self.console.print(panel)
        self.console.print()

    def show_tools_table(self) -> Table:
        """Create a table showing all tools with their status."""
        table = Table(title="Available Tools")
        table.add_column("Tool", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Status", justify="center")

        for tool in self.tools_config:
            name = tool["name"]
            description = tool.get("description", "No description")
            installed = self.is_tool_installed(name)

            status = "[green]✓ Installed[/green]" if installed else "[red]✗ Not installed[/red]"
            table.add_row(name, description, status)

        return table

    def select_tools_interactive(self) -> List[str]:
        """Interactive tool selection using checklist."""
        self.console.print("[bold]Select tools to install:[/bold]")
        self.console.print("Use space to toggle selection, enter to confirm")
        self.console.print()

        # Get all tools
        all_tools = [tool["name"] for tool in self.tools_config]
        installed_tools = self.get_installed_tools()

        # Pre-select tools that are not installed
        selected = [tool for tool in all_tools if tool not in installed_tools]

        # For now, we'll use a simple prompt approach since rich doesn't have a built-in checklist
        # In a real implementation, you might want to use a library like questionary or inquirer

        if not selected:
            self.console.print("[green]All tools are already installed![/green]")
            return []

        self.console.print("The following tools will be installed:")
        for tool in selected:
            self.console.print(f"  • [cyan]{tool}[/cyan]")

        if Confirm.ask("\nProceed with installation?", default=True):
            return selected
        else:
            return []

    def install_selected_tools(self, tools_to_install: List[str]) -> None:
        """Install the selected tools with progress display."""
        if not tools_to_install:
            self.console.print("[green]No tools to install.[/green]")
            return

        with self.console.status(f"[bold green]Installing {len(tools_to_install)} tools...") as status:
            for tool_name in tools_to_install:
                status.update(f"[bold green]Installing {tool_name}...")

                try:
                    # Find the tool config
                    tool_config = next((t for t in self.tools_config if t["name"] == tool_name), None)
                    if not tool_config:
                        self.console.print(f"[red]Configuration not found for {tool_name}[/red]")
                        continue

                    # Install the tool
                    self.installer.install_tool(tool_config)

                    self.console.print(f"[green]✓[/green] Successfully installed {tool_name}")

                except Exception as e:
                    self.console.print(f"[red]✗[/red] Failed to install {tool_name}: {str(e)}")

        # Setup PATH and IDEs after installation
        self.console.print("\n[bold]Setting up environment...[/bold]")
        self.installer.add_to_path()
        self.installer.setup_ides()
        self.console.print("[green]✓[/green] Environment setup complete")

    def run(self) -> None:
        """Main TUI loop."""
        self.show_welcome()

        # Show tools table
        table = self.show_tools_table()
        self.console.print(table)
        self.console.print()

        # Select tools to install
        tools_to_install = self.select_tools_interactive()

        if tools_to_install:
            self.install_selected_tools(tools_to_install)
            self.console.print("\n[bold green]Installation complete![/bold]")
            self.console.print("You can now use the installed tools in your terminal.")
        else:
            self.console.print("[yellow]Installation cancelled.[/yellow]")


def main() -> None:
    """Main entry point for TUI."""
    config_file = Path(__file__).parent / "tools_config.json"
    tui = SNESInstallerTUI(config_file)
    tui.run()


if __name__ == "__main__":
    main()