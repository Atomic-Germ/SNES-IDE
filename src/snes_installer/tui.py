#!/usr/bin/env python3
"""Text User Interface for SNES Installer."""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.spinner import Spinner
from rich.status import Status
from rich.table import Table
from rich.text import Text

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
    parts = [p.strip() for p in input_str.split(",") if p.strip()]
    for part in parts:
        # range
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
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

    def __init__(
        self,
        config_file: Path,
        install_dir: Path | None = None,
        min_free_bytes: int | None = None,
        dry_run: bool = False,
    ):
        self.config_file = config_file
        self.console = Console()
        self.installer = ToolInstaller(
            config_file,
            dry_run=dry_run,
            min_free_bytes=(min_free_bytes or 200 * 1024 * 1024),
            install_dir=install_dir,
        )
        self.tools_config = self.installer.load_config()["tools"]
        # Load or initialize user settings storage
        self.user_config_file = Path.home() / ".snes_installer" / "config.json"
        self.user_config_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_user_settings(install_dir, min_free_bytes)

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

    def load_user_settings(
        self,
        install_dir_override: Path | None = None,
        min_free_bytes_override: int | None = None,
    ) -> None:
        """Load user settings from the config file, applying overrides if provided."""
        if self.user_config_file.exists():
            try:
                import json

                with open(self.user_config_file, "r") as f:
                    data = json.load(f)
                install_dir = data.get("install_dir")
                min_space = data.get("min_free_bytes")
                if install_dir and install_dir_override is None:
                    self.installer.install_dir = Path(install_dir)
                if min_space and min_free_bytes_override is None:
                    self.installer.min_free_bytes = int(min_space)
            except Exception:
                # Ignore malformed config files
                pass
        # Apply overrides from constructor
        if install_dir_override is not None:
            self.installer.install_dir = install_dir_override
        if min_free_bytes_override is not None:
            self.installer.min_free_bytes = min_free_bytes_override

    def save_user_settings(self) -> None:
        """Save current installer settings to the user config file."""
        import json

        data = {
            "install_dir": str(self.installer.install_dir),
            "min_free_bytes": int(self.installer.min_free_bytes),
        }
        with open(self.user_config_file, "w") as f:
            json.dump(data, f)

    def show_settings_menu(self) -> None:
        """Show a settings menu to edit installation directory and min-space threshold."""
        self.console.print("[bold cyan]Settings[/bold cyan]")
        cur_dir = str(self.installer.install_dir)
        cur_space = self.installer.min_free_bytes // (1024 * 1024)
        self.console.print(f"Current install directory: {cur_dir}")
        self.console.print(f"Current minimum free space: {cur_space} MB")
        new_dir = Prompt.ask(
            "Enter new install directory (leave blank to keep current)", default=""
        )
        if new_dir:
            self.installer.install_dir = Path(new_dir)
        new_space_str = Prompt.ask(
            "Enter minimum free space in MB (leave blank to keep current)", default=""
        )
        if new_space_str:
            try:
                self.installer.min_free_bytes = int(new_space_str) * 1024 * 1024
            except ValueError:
                self.console.print(
                    "[red]Invalid number for space; keeping the current value.[/red]"
                )
        if Confirm.ask("Save settings?", default=True):
            self.save_user_settings()
            self.console.print("[green]Settings saved.[/green]")

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

        status_text = (
            f"Installed: {len(installed_tools)}/{total_tools} tools | "
            + ", ".join(category_summaries)
        )

        panel = Panel.fit(
            f"[bold]{welcome_text}[/bold]\n[dim]{subtitle}[/dim]\n\n{status_text}",
            title="🎮 Welcome",
            border_style="blue",
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
            panels.append(
                Panel(
                    "\n".join(lines),
                    title=f"{cat}",
                    expand=True,
                    border_style="dark_blue",
                )
            )
        if panels:
            self.console.print(Columns(panels))
            self.console.print()

    def show_main_menu(self) -> str:
        """Show main menu and return selected option."""
        self.console.print("[bold cyan]Main Menu:[/bold cyan]")
        menu_items = [
            ("Install all missing tools", "install_all"),
            ("Install tools by category", "category"),
            ("Install specific tool", "specific"),
            ("Reinstall tool", "reinstall"),
            ("Uninstall tool", "uninstall"),
            ("Show tool status", "status"),
            ("Settings", "settings"),
            ("Exit", "exit"),
        ]
        # Use questionary.select for better UX if available
        try:
            import questionary

            selected = questionary.select(
                "Select an option", choices=[m[0] for m in menu_items]
            ).ask()
            # Map back to value
            for title, value in menu_items:
                if title == selected:
                    return value
            return "exit"
        except Exception:
            # Fallback to numbered Prompt
            for i, (title, _) in enumerate(menu_items, 1):
                self.console.print(f"{i}. {title}")
            self.console.print()
            while True:
                choice = Prompt.ask(
                    "Select an option",
                    choices=[str(i) for i in range(1, len(menu_items) + 1)],
                )
                idx = int(choice) - 1
                return menu_items[idx][1]

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
            self.console.print(
                "[yellow]No tools available for this operation.[/yellow]"
            )
            return ""

        self.console.print(f"[bold]{prompt}[/bold]")
        for i, tool in enumerate(tools_list, 1):
            tool_config = next(
                (t for t in self.tools_config if t["name"] == tool), None
            )
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

        if self.show_preview_panel(missing_tools):
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
            status = (
                "[green]✓ Installed[/green]"
                if installed
                else "[red]✗ Not installed[/red]"
            )
            self.console.print(f"{i}. {tool['name']} - {description} - {status}")
        self.console.print(f"{len(tools)+1}. Install all")
        self.console.print(f"{len(tools)+2}. Back to categories")

        # If questionary is available, use its checkbox prompt for better UX
        try:
            import questionary

            # Build choices
            choices = []
            for tool in tools:
                name = tool["name"]
                desc = tool.get("description", "")
                installed = self.is_tool_installed(name)
                status = "✓" if installed else "✗"
                choices.append(
                    questionary.Choice(title=f"[{status}] {name} - {desc}", value=name)
                )

            selected = questionary.checkbox(
                "Select tools to install", choices=choices
            ).ask()
            if selected:
                return selected
            # If user cancelled or selected nothing, return empty list
            return []
        except Exception:
            # Fallback to textual input parsing
            while True:
                choice = Prompt.ask(
                    "Enter tool numbers to install (comma-separated), or choose Install all/Back",
                    default="",
                )
                if not choice:
                    return []
                choice = choice.strip()
                # Support 'info N' to show details about a tool
                info_idx = parse_info_input(choice)
                if info_idx is not None:
                    if 1 <= info_idx <= len(tools):
                        detail_tool = tools[info_idx - 1]
                        url = detail_tool.get("url", "")
                        instructions = detail_tool.get(
                            "install_instructions", "No instructions provided."
                        )
                        build_cmds = detail_tool.get("build_commands", {})
                        build_text = (
                            "" if not build_cmds else f"\nBuild commands: {build_cmds}"
                        )
                        content = f"{detail_tool.get('description', '')}\n\nURL: {url}\n{instructions}{build_text}"
                        self.console.print(
                            Panel(
                                content,
                                title=f"Details: {detail_tool['name']}",
                                border_style="green",
                            )
                        )
                        continue
                    else:
                        self.console.print(
                            "[red]Invalid tool index for info command.[/red]"
                        )
                        continue
                if choice.lower() in ["install all", "all", "i"] or choice == str(
                    len(tools) + 1
                ):
                    return [t["name"] for t in tools]
                if choice == str(len(tools) + 2):
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
        self.console.print(
            f"Installing {len(tool_names)} tools in category '{category}'"
        )
        if Confirm.ask("Proceed with installation?", default=True):
            self.install_selected_tools(tool_names)

    def generate_preview_info(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """Generate a preview info list for the provided tool names.

        Each dict contains: name, description, url, build_commands, requires_cargo, binary_path, installed
        """
        preview = []
        for name in tool_names:
            tool = next((t for t in self.tools_config if t["name"] == name), None)
            if not tool:
                continue
            build_cmds = tool.get("build_commands", {})
            # Normalize to platform-specific list
            platform_cmds = (
                build_cmds.get(sys.platform, [])
                if isinstance(build_cmds, dict)
                else build_cmds
            )
            requires_cargo = (
                any("cargo" in c for c in platform_cmds)
                or tool.get("name") == "terrific_audio_driver"
            )
            preview.append(
                {
                    "name": name,
                    "description": tool.get("description", ""),
                    "url": tool.get("url", ""),
                    "build_commands": platform_cmds,
                    "requires_cargo": requires_cargo,
                    "binary_path": tool.get("binary_path", ""),
                    "installed": self.is_tool_installed(name),
                }
            )
        return preview

    def show_preview_panel(self, tool_names: List[str]) -> bool:
        """Show a preview panel summarizing planned actions for provided tool names.

        Returns True if user confirms to proceed, False otherwise.
        """
        if not tool_names:
            self.console.print("[yellow]No tools selected for preview.[/yellow]")
            return False

        preview = self.generate_preview_info(tool_names)
        lines = []
        warnings = []
        for entry in preview:
            name = entry["name"]
            desc = entry["description"]
            url = entry["url"]
            cmds = entry["build_commands"] or []
            installed = entry["installed"]
            lines.append(f"[bold]{name}[/bold] - {desc}")
            lines.append(f"  URL: {url}")
            if cmds:
                lines.append(f"  Build: {'; '.join(cmds)}")
            else:
                lines.append("  Build: (no build commands specified)")
            if entry["requires_cargo"]:
                warnings.append(
                    f"{name} requires Rust/Cargo. Ensure cargo is installed."
                )
            if installed:
                lines.append("  [green]Already installed[/green]")
            lines.append("")

        # Add disk space info
        import shutil

        try:
            usage = shutil.disk_usage(str(self.installer.install_dir))
            free_mb = usage.free // (1024 * 1024)
            lines.append(f"Disk free at install location: {free_mb} MB")
            if (
                getattr(self.installer, "min_free_bytes", 0)
                and usage.free < self.installer.min_free_bytes
            ):
                warnings.append(
                    f"Available disk space ({free_mb} MB) is below the minimum configured ({self.installer.min_free_bytes // (1024*1024)} MB)."
                )
        except Exception:
            # ignore disk usage failures in preview
            pass

        if warnings:
            lines.append("\n[red]Warnings:[/red]")
            for w in warnings:
                lines.append(f" - {w}")

        content = "\n".join(lines)
        self.console.print(
            Panel(content, title="Preview: Planned Actions", border_style="cyan")
        )
        return Confirm.ask("Proceed with installation for these tools?", default=False)

    def install_specific_tool(self) -> None:
        """Install a specific tool selected by the user."""
        all_tools = [tool["name"] for tool in self.tools_config]
        tool_name = self.select_tool("Select a tool to install:", all_tools)
        if tool_name:
            if self.show_preview_panel([tool_name]):
                self.install_selected_tools([tool_name])

    def reinstall_tool(self) -> None:
        """Reinstall a tool that is already installed."""
        installed_tools = self.get_installed_tools()
        if not installed_tools:
            self.console.print("[yellow]No tools are currently installed.[/yellow]")
            return

        tool_name = self.select_tool("Select a tool to reinstall:", installed_tools)
        if tool_name:
            if Confirm.ask(
                f"[yellow]This will uninstall and reinstall {tool_name}. Continue?",
                default=False,
            ):
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
            if Confirm.ask(
                f"[red]This will permanently remove {tool_name}. Continue?",
                default=False,
            ):
                self.console.print(f"Uninstalling {tool_name}...")
                if self.installer.uninstall_tool(tool_name):
                    self.console.print(
                        f"[green]✓[/green] Successfully uninstalled {tool_name}"
                    )
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
                status = (
                    "[green]✓ Installed[/green]"
                    if installed
                    else "[red]✗ Not installed[/red]"
                )
                lines.append(f"{status} {name} - {desc}")
            content = "\n".join(lines)
            panels.append(
                Panel(
                    content,
                    title=f"{cat} ({len(tools)})",
                    expand=False,
                    border_style="blue",
                )
            )

        if panels:
            self.console.print(Columns(panels))
        else:
            self.console.print("[yellow]No tools configured.[/yellow]")

        installed = self.get_installed_tools()
        missing = self.get_missing_tools()

        self.console.print()
        self.console.print(
            f"[green]Installed tools ({len(installed)}):[/green] {', '.join(installed) if installed else 'None'}"
        )
        if missing:
            self.console.print(
                f"[red]Missing tools ({len(missing)}):[/red] {', '.join(missing)}"
            )

    def install_selected_tools(self, tools_to_install: List[str]) -> None:
        """Install the selected tools with progress display."""
        if not tools_to_install:
            self.console.print("[green]No tools to install.[/green]")
            return

        with self.console.status(
            f"[bold green]Installing {len(tools_to_install)} tools..."
        ) as status:
            for tool_name in tools_to_install:
                status.update(f"[bold green]Installing {tool_name}...")

                try:
                    # Find the tool config
                    tool_config = next(
                        (t for t in self.tools_config if t["name"] == tool_name), None
                    )
                    if not tool_config:
                        self.console.print(
                            f"[red]Configuration not found for {tool_name}[/red]"
                        )
                        continue

                    # Install the tool
                    self.installer.install_selected_tools([tool_name])

                    self.console.print(
                        f"[green]✓[/green] Successfully installed {tool_name}"
                    )

                except Exception as e:
                    self.console.print(
                        f"[red]✗[/red] Failed to install {tool_name}: {str(e)}"
                    )

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

                # Support both numeric and action string choices (questionary returns action values)
                if choice in {"1", "install_all"}:
                    self.install_missing_tools()
                elif choice in {"2", "category"}:
                    category = self.show_categories_menu()
                    if category:
                        selections = self.show_category_tools_menu(category)
                        if selections:
                            # Show preview and confirm before installing
                            if self.show_preview_panel(selections):
                                self.install_selected_tools(selections)
                elif choice in {"3", "specific"}:
                    self.install_specific_tool()
                elif choice in {"4", "reinstall"}:
                    self.reinstall_tool()
                elif choice in {"5", "uninstall"}:
                    self.uninstall_tool()
                elif choice in {"6", "status"}:
                    self.show_status()
                elif choice in {"7", "settings"}:
                    self.show_settings_menu()
                elif choice in {"8", "exit"}:
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
