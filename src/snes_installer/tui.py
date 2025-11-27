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

from snes_installer.installer import ToolInstaller, add_to_path, setup_ides


def parse_selection_input(input_str: str, tools: List[Dict[str, Any]]) -> List[str]:
    """Parse a selection string and return a list of tool names.

    Supported formats:
    - '1' single index (1-based)
    - '1,3' comma-separated
    - '1-3' ranges
    - 'all' or 'install all' or 'i' for all tools
    - 'back' or empty string -> []

    Invalid entries are ignored.
    """
    if not input_str:
        return []
    s = input_str.strip().lower()
    if s in {"back", "", "b"}:
        return []
    if s in {"all", "install all", "i"}:
        return [t["name"] for t in tools]

    selected: List[str] = []
    parts = [p.strip() for p in input_str.split(',') if p.strip()]
    for part in parts:
        # range
        if '-' in part:
            try:
                start_str, end_str = part.split('-', 1)
                start = int(start_str)
                end = int(end_str)
                if start <= 0:
                    continue
                for idx in range(start, min(end, len(tools)) + 1):
                    name = tools[idx - 1]["name"]
                    if name not in selected:
                        selected.append(name)
            except ValueError:
                continue
        else:
            try:
                idx = int(part)
                if 1 <= idx <= len(tools):
                    name = tools[idx - 1]["name"]
                    if name not in selected:
                        selected.append(name)
            except ValueError:
                # ignore invalid entries
                continue
    return selected


def parse_info_input(input_str: str) -> int | None:
    """Parse info commands like 'info 1', 'i 2', 'details 3', returning the index (1-based) or None."""
    if not input_str:
        return None
    s = input_str.strip().lower()
    parts = s.split()
    if not parts:
        return None
    if parts[0] not in {"info", "i", "details", "d"}:
        return None
    if len(parts) < 2:
        return None
    try:
        idx = int(parts[1])
        return idx
    except ValueError:
        return None



class SNESInstallerTUI:
    """Text User Interface for SNES development tools installer.

    Can optionally accept an install_dir and min_free_bytes to pass into the underlying ToolInstaller.
    """

    def __init__(self, config_file: Path, install_dir: Path | None = None, min_free_bytes: int | None = None, dry_run: bool = False):
        self.config_file = config_file
        self.console = Console()
        self.installer = ToolInstaller(config_file, dry_run=dry_run, min_free_bytes=(min_free_bytes or 200 * 1024 * 1024), install_dir=install_dir)
        self.tools_config = self.installer.load_config()['tools']

    def is_tool_installed(self, tool_name: str) -> bool:
        """Check if a tool is already installed and available in PATH."""
        return self.installer.is_tool_installed(tool_name)

    def get_installed_tools(self) -> List[str]:
        """Get list of tools that are already installed."""
        installed = []
        for tool in self.tools_config:
            tool_name = tool["name"]
            if self.is_tool_installed(tool_name):
                installed.append(tool_name)
        return installed

    def get_missing_tools(self) -> List[str]:
        """Get list of tools that are not installed."""
        missing = []
        for tool in self.tools_config:
            tool_name = tool["name"]
            if not self.is_tool_installed(tool_name):
                missing.append(tool_name)
        return missing

    def get_tools_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group tools by their category."""
        categorized: Dict[str, List[Dict[str, Any]]] = {}
        for tool in self.tools_config:
            category = tool.get("category", "Other")
            categorized.setdefault(category, []).append(tool)
        return categorized

    def get_tools_in_category(self, category: str) -> List[Dict[str, Any]]:
        """Return tools in the given category."""
        return self.get_tools_by_category().get(category, [])

    def show_welcome(self) -> None:
        """Show welcome message and current status."""
        welcome_text = Text("SNES Development Tools Installer", style="bold blue")
        subtitle = Text("Cross-platform toolkit for SNES programming", style="dim")

        installed_tools = self.get_installed_tools()
        total_tools = len(self.tools_config)
        categorized = self.get_tools_by_category()

        # Build a summary per category
        category_summaries = []
        for cat, tools in categorized.items():
            installed_count = sum(1 for t in tools if self.is_tool_installed(t["name"]))
            category_summaries.append(f"{cat}: {installed_count}/{len(tools)}")

        status_text = f"Installed: {len(installed_tools)}/{total_tools} tools | " + ", ".join(category_summaries)

        panel = Panel.fit(
            f"[bold]{welcome_text}[/bold]\n[dim]{subtitle}[/dim]\n\n{status_text}",
            title="🎮 Welcome",
            border_style="blue"
        )
        self.console.print(panel)
        self.console.print()
        # Show a small dashboard with category panels
        categorized = self.get_tools_by_category()
        panels = []
        for cat, tools in categorized.items():
            lines = []
            for t in tools[:4]:
                name = t["name"]
                installed = self.is_tool_installed(name)
                status = "[green]✓[/green]" if installed else "[red]✗[/red]"
                lines.append(f"{status} {name}")
            panels.append(Panel("\n".join(lines), title=f"{cat}", expand=True, border_style="dark_blue"))
        if panels:
            self.console.print(Columns(panels))
            self.console.print()

    def show_main_menu(self) -> str:
        """Show main menu and return selected option."""
        self.console.print("[bold cyan]Main Menu:[/bold cyan]")
        self.console.print("1. Install all missing tools")
        self.console.print("2. Install tools by category")
        self.console.print("3. Install specific tool")
        self.console.print("4. Reinstall tool")
        self.console.print("5. Uninstall tool")
        self.console.print("6. Show tool status")
        self.console.print("7. Exit")
        self.console.print()

        while True:
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6", "7"])
            return choice

    def show_tools_table(self, highlight_tools: List[str] = None) -> Table:
        """Create a table showing all tools with their status split by category."""
        categorized = self.get_tools_by_category()
        main_table = Table(title="Available Tools (Grouped)")
        main_table.add_column("Category", style="magenta")
        main_table.add_column("Tools", style="cyan")

        for cat, tools in categorized.items():
            tool_display = []
            for tool in tools:
                name = tool["name"]
                description = tool.get("description", "No description")
                installed = self.is_tool_installed(name)
                status = "[green]✓[/green]" if installed else "[red]✗[/red]"
                display = f"{status} {name} - {description}"
                if highlight_tools and name in highlight_tools:
                    display = f"[bold yellow]{display}[/bold yellow]"
                tool_display.append(display)

            main_table.add_row(cat, "\n".join(tool_display))

        return main_table

    def select_tool(self, prompt: str, tools_list: List[str]) -> str:
        """Let user select a tool from a list."""
        if not tools_list:
            self.console.print("[yellow]No tools available for this operation.[/yellow]")
            return ""

        self.console.print(f"[bold]{prompt}[/bold]")
        for i, tool in enumerate(tools_list, 1):
            tool_config = next((t for t in self.tools_config if t["name"] == tool), None)
            description = tool_config.get("description", "") if tool_config else ""
            self.console.print(f"{i}. {tool} - {description}")

        while True:
            try:
                choice = int(Prompt.ask("Enter tool number"))
                if 1 <= choice <= len(tools_list):
                    return tools_list[choice - 1]
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
            except ValueError:
                self.console.print("[red]Please enter a number.[/red]")

    def install_missing_tools(self) -> None:
        """Install all tools that are not currently installed."""
        missing_tools = self.get_missing_tools()
        if not missing_tools:
            self.console.print("[green]All tools are already installed![/green]")
            return

        self.console.print(f"Installing {len(missing_tools)} missing tools:")
        for tool in missing_tools:
            self.console.print(f"  • [cyan]{tool}[/cyan]")

        if Confirm.ask("\nProceed with installation?", default=True):
            self.install_selected_tools(missing_tools)

    def show_categories_menu(self) -> str:
        """Show categories to the user and return the selected category."""
        categories = list(self.get_tools_by_category().keys())
        if not categories:
            self.console.print("[yellow]No categories available.[/yellow]")
            return ""

        self.console.print("[bold cyan]Categories:[/bold cyan]")
        for i, cat in enumerate(categories, 1):
            self.console.print(f"{i}. {cat}")
        self.console.print(f"{len(categories)+1}. Back to main menu")

        while True:
            try:
                choice = int(Prompt.ask("Select a category"))
                if 1 <= choice <= len(categories):
                    return categories[choice - 1]
                elif choice == len(categories) + 1:
                    return ""
                else:
                    self.console.print("[red]Invalid choice. Please try again.[/red]")
            except ValueError:
                self.console.print("[red]Please enter a number.[/red]")

    def show_category_tools_menu(self, category: str) -> List[str]:
        """Show tools in a category and let user select tools to install.

        Returns a list of selected tool names (could be empty if none selected).
        """
        tools = self.get_tools_in_category(category)
        if not tools:
            self.console.print(f"[yellow]No tools in category {category}[/yellow]")
            return []

        self.console.print(f"[bold cyan]{category} Tools:[/bold cyan]")
        for i, tool in enumerate(tools, 1):
            description = tool.get("description", "")
            installed = self.is_tool_installed(tool["name"])
            status = "[green]✓ Installed[/green]" if installed else "[red]✗ Not installed[/red]"
            self.console.print(f"{i}. {tool['name']} - {description} - {status}")
        self.console.print(f"{len(tools)+1}. Install all")
        self.console.print(f"{len(tools)+2}. Back to categories")

        # If questionary is available, use its checkbox prompt for better UX
        try:
            import questionary
            # Build choices
            choices = []
            for tool in tools:
                name = tool['name']
                desc = tool.get('description', '')
                installed = self.is_tool_installed(name)
                status = '✓' if installed else '✗'
                choices.append(questionary.Choice(title=f"[{status}] {name} - {desc}", value=name))

            selected = questionary.checkbox("Select tools to install", choices=choices).ask()
            if selected:
                return selected
            # If user cancelled or selected nothing, return empty list
            return []
        except Exception:
            # Fallback to textual input parsing
            while True:
                choice = Prompt.ask("Enter tool numbers to install (comma-separated), or choose Install all/Back", default="")
                if not choice:
                    return []
                choice = choice.strip()
                # Support 'info N' to show details about a tool
                info_idx = parse_info_input(choice)
                if info_idx is not None:
                    if 1 <= info_idx <= len(tools):
                        detail_tool = tools[info_idx - 1]
                        url = detail_tool.get("url", "")
                        instructions = detail_tool.get("install_instructions", "No instructions provided.")
                        build_cmds = detail_tool.get("build_commands", {})
                        build_text = "" if not build_cmds else f"\nBuild commands: {build_cmds}"
                        content = f"{detail_tool.get('description', '')}\n\nURL: {url}\n{instructions}{build_text}"
                        self.console.print(Panel(content, title=f"Details: {detail_tool['name']}", border_style="green"))
                        continue
                    else:
                        self.console.print("[red]Invalid tool index for info command.[/red]")
                        continue
                if choice.lower() in ["install all", "all", "i"] or choice == str(len(tools)+1):
                    return [t["name"] for t in tools]
                if choice == str(len(tools)+2):
                    return []
                # Use parsing helper
                selections = parse_selection_input(choice, tools)
                if selections:
                    return selections
                else:
                    # If parse returned nothing but the input wasn't empty and wasn't handled above, it's invalid
                    self.console.print("[red]Invalid selection. Try again.[/red]")

    def install_tools_in_category(self, category: str) -> None:
        """Install all tools in a given category."""
        tools = self.get_tools_in_category(category)
        if not tools:
            self.console.print(f"[yellow]No tools found in {category}[/yellow]")
            return

        tool_names = [t["name"] for t in tools]
        self.console.print(f"Installing {len(tool_names)} tools in category '{category}'")
        if Confirm.ask("Proceed with installation?", default=True):
            self.install_selected_tools(tool_names)

    def install_specific_tool(self) -> None:
        """Install a specific tool selected by the user."""
        all_tools = [tool["name"] for tool in self.tools_config]
        tool_name = self.select_tool("Select a tool to install:", all_tools)
        if tool_name:
            if self.is_tool_installed(tool_name):
                if not Confirm.ask(f"[yellow]{tool_name} is already installed. Reinstall?", default=False):
                    return
            self.install_selected_tools([tool_name])

    def reinstall_tool(self) -> None:
        """Reinstall a tool that is already installed."""
        installed_tools = self.get_installed_tools()
        if not installed_tools:
            self.console.print("[yellow]No tools are currently installed.[/yellow]")
            return

        tool_name = self.select_tool("Select a tool to reinstall:", installed_tools)
        if tool_name:
            if Confirm.ask(f"[yellow]This will uninstall and reinstall {tool_name}. Continue?", default=False):
                # First uninstall
                self.console.print(f"Uninstalling {tool_name}...")
                if self.installer.uninstall_tool(tool_name):
                    self.console.print(f"[green]✓[/green] Uninstalled {tool_name}")
                else:
                    self.console.print(f"[red]✗[/red] Failed to uninstall {tool_name}")
                    return
                
                # Then reinstall
                self.install_selected_tools([tool_name])

    def uninstall_tool(self) -> None:
        """Uninstall a tool selected by the user."""
        installed_tools = self.get_installed_tools()
        if not installed_tools:
            self.console.print("[yellow]No tools are currently installed.[/yellow]")
            return

        tool_name = self.select_tool("Select a tool to uninstall:", installed_tools)
        if tool_name:
            if Confirm.ask(f"[red]This will permanently remove {tool_name}. Continue?", default=False):
                self.console.print(f"Uninstalling {tool_name}...")
                if self.installer.uninstall_tool(tool_name):
                    self.console.print(f"[green]✓[/green] Successfully uninstalled {tool_name}")
                else:
                    self.console.print(f"[red]✗[/red] Failed to uninstall {tool_name}")

    def show_status(self) -> None:
        """Show detailed status of all tools using categorized panels."""
        categorized = self.get_tools_by_category()
        panels = []
        for cat, tools in categorized.items():
            lines = []
            for tool in tools:
                name = tool["name"]
                desc = tool.get("description", "")
                installed = self.is_tool_installed(name)
                status = "[green]✓ Installed[/green]" if installed else "[red]✗ Not installed[/red]"
                lines.append(f"{status} {name} - {desc}")
            content = "\n".join(lines)
            panels.append(Panel(content, title=f"{cat} ({len(tools)})", expand=False, border_style="blue"))

        if panels:
            self.console.print(Columns(panels))
        else:
            self.console.print("[yellow]No tools configured.[/yellow]")

        installed = self.get_installed_tools()
        missing = self.get_missing_tools()
        
        self.console.print()
        self.console.print(f"[green]Installed tools ({len(installed)}):[/green] {', '.join(installed) if installed else 'None'}")
        if missing:
            self.console.print(f"[red]Missing tools ({len(missing)}):[/red] {', '.join(missing)}")

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
                    self.installer.install_selected_tools([tool_name])

                    self.console.print(f"[green]✓[/green] Successfully installed {tool_name}")

                except Exception as e:
                    self.console.print(f"[red]✗[/red] Failed to install {tool_name}: {str(e)}")

        # Setup PATH and IDEs after installation
        self.console.print("\n[bold]Setting up environment...[/bold]")
        add_to_path()
        setup_ides()
        self.console.print("[green]✓[/green] Environment setup complete")

    def run(self) -> None:
        """Main TUI loop."""
        self.show_welcome()
        try:
            while True:
                choice = self.show_main_menu()

                if choice == "1":
                    self.install_missing_tools()
                elif choice == "2":
                    category = self.show_categories_menu()
                    if category:
                        selections = self.show_category_tools_menu(category)
                        if selections:
                            self.install_selected_tools(selections)
                elif choice == "3":
                    self.install_specific_tool()
                elif choice == "4":
                    self.reinstall_tool()
                elif choice == "5":
                    self.uninstall_tool()
                elif choice == "6":
                    self.show_status()
                elif choice == "7":
                    self.console.print("[green]Goodbye![/green]")
                    break

                self.console.print()  # Add spacing between operations
        except (KeyboardInterrupt, EOFError):
            # Graceful exit on Ctrl-C or EOF
            self.console.print("\n[green]Goodbye![/green]")


def main() -> None:
    """Main entry point for TUI."""
    config_file = Path(__file__).parent / "tools_config.json"
    tui = SNESInstallerTUI(config_file)
    tui.run()


if __name__ == "__main__":
    main()