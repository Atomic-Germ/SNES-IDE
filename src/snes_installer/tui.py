#!/usr/bin/env python3
"""Text User Interface for SNES Installer."""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Tuple

from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
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

        # Initialize operation history
        self.operation_history: List[str] = []
        self.layout = self.create_layout()

    def create_layout(self) -> Layout:
        """Create the main layout for the TUI."""
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )
        layout["main"].split_row(
            Layout(name="menu", ratio=1),
            Layout(name="content", ratio=3),
        )
        return layout

    def render_header(self) -> None:
        """Render the header section."""
        self.layout["header"].update(
            Panel("[bold blue]SNES Installer — DEV BUILD[/bold blue]", expand=True)
        )

    def render_footer(self) -> None:
        """Render the footer section."""
        self.layout["footer"].update(
            Panel("[bold green]Press Ctrl+C to exit[/bold green]", expand=True)
        )

    def render_menu(self) -> None:
        """Render the menu section."""
        menu = Panel(
            "[bold yellow]Menu Options[/bold yellow]\n1. Install Tools\n2. Settings\n3. Exit",
            expand=True,
        )
        self.layout["menu"].update(menu)

    def render_content(self, content: str) -> None:
        """Render the content section."""
        self.layout["content"].update(Panel(content, expand=True))

    def get_menu_choice(
        self, title: str, options: List[str], allow_back: bool = False
    ) -> int | None:
        """Get a menu choice from the user with consistent formatting.

        Returns the 1-based index of the choice, or None if cancelled/back.
        """
        self.console.print(f"[bold cyan]{title}[/bold cyan]")
        for i, option in enumerate(options, 1):
            self.console.print(f"{i}. {option}")
        if allow_back:
            self.console.print(f"{len(options) + 1}. Back")

        while True:
            try:
                choice = int(Prompt.ask("Select an option (number)"))
                if allow_back and choice == len(options) + 1:
                    return None
                if 1 <= choice <= len(options):
                    return choice
                self.console.print("[red]Invalid choice. Please try again.[/red]")
            except ValueError:
                self.console.print("[red]Please enter a number.[/red]")

    def _read_key(self) -> str:
        """Read a single keypress from stdin and return a string representing it.

        Supports arrow keys by returning their escape sequences (e.g. '\x1b[A' for UP).
        """
        try:
            import termios
            import tty
        except Exception:
            # Fallback to normal input if termios/tty not available
            return sys.stdin.read(1)

        try:
            fd = sys.stdin.fileno()
        except Exception:
            # stdin has no fileno (e.g. redirected in tests); fall back to a simple read
            try:
                return sys.stdin.read(1)
            except Exception:
                return ""

        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch1 = sys.stdin.read(1)
            if ch1 == "\x1b":
                # possible escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    return "\x1b[" + ch3
                return ch1 + ch2
            return ch1
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _interactive_select(
        self, title: str, options: List[str], allow_back: bool = True
    ) -> Tuple[int | None, str | None]:
        """Render a navigable selection list and return (index, value) when selected.

        Navigation: Up/Down arrows or 'k'/'j', numbers to jump, Enter to select, 'q' or Back to cancel.
        Returns (None, None) on cancel/back.
        """
        if not options:
            return None, None

        selected = 0
        while True:
            # build display
            lines = [f"[bold cyan]{title}[/bold cyan]\n"]
            for i, opt in enumerate(options):
                prefix = ">" if i == selected else " "
                style = "reverse" if i == selected else ""
                lines.append(f"{prefix} {i+1}. {opt}")

            if allow_back:
                lines.append(
                    "\nPress Enter to select, arrows/j/k to move, 'q' to go back"
                )
            else:
                lines.append("\nPress Enter to select, arrows/j/k to move")

            content = "\n".join(lines)
            self.layout["content"].update(
                Panel(content, title=title, border_style="blue")
            )

            key = self._read_key()
            # handle arrow up / 'k'
            if key in ("\x1b[A", "k"):
                selected = (selected - 1) % len(options)
                continue
            # arrow down / 'j'
            if key in ("\x1b[B", "j"):
                selected = (selected + 1) % len(options)
                continue
            # numbers (single digit or more)
            if key.isdigit():
                # accept multi-digit numbers by reading the rest if any
                num = int(key)
                if 1 <= num <= len(options):
                    return num - 1, options[num - 1]
                continue
            # Enter
            if key in ("\r", "\n"):
                return selected, options[selected]
            # Back / cancel
            if allow_back and key in ("q", "b", "\x03"):
                return None, None
            # ignore other keys
            continue

    def get_text_input(self, prompt: str, default: str = "") -> str:
        """Get text input from the user with consistent formatting."""
        return Prompt.ask(prompt, default=default).strip()

    def get_confirmation(self, message: str, default: bool = False) -> bool:
        """Get a yes/no confirmation from the user."""
        return Confirm.ask(message, default=default)

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
        self.console.clear()
        self.console.print("[bold cyan]Settings[/bold cyan]")
        cur_dir = str(self.installer.install_dir)
        cur_space = self.installer.min_free_bytes // (1024 * 1024)
        self.console.print(f"Current install directory: {cur_dir}")
        self.console.print(f"Current minimum free space: {cur_space} MB")

        new_dir = self.get_text_input(
            "Enter new install directory (leave blank to keep current)", default=""
        )
        if new_dir:
            self.installer.install_dir = Path(new_dir)

        new_space_str = self.get_text_input(
            "Enter minimum free space in MB (leave blank to keep current)", default=""
        )
        if new_space_str:
            try:
                self.installer.min_free_bytes = int(new_space_str) * 1024 * 1024
            except ValueError:
                self.console.print(
                    "[red]Invalid number for space; keeping the current value.[/red]"
                )

        if self.get_confirmation("Save settings?", default=True):
            self.save_user_settings()
            self.console.print("[green]Settings saved.[/green]")

    def show_operation_history(self) -> None:
        """Show recent operations performed in this session."""
        self.console.clear()
        if not self.operation_history:
            self.console.print(
                "[yellow]No operations performed in this session yet.[/yellow]"
            )
            return

        self.console.print("[bold cyan]Recent Operations:[/bold cyan]")
        for i, operation in enumerate(
            reversed(self.operation_history[-10:]), 1
        ):  # Show last 10
            self.console.print(f"{i}. {operation}")
        self.console.print()

    def show_welcome(self) -> None:
        """Show welcome message and current status."""
        self.console.clear()
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
        menu_options = [
            "Install all missing tools",
            "Install tools by category",
            "Search and install tools",
            "Install specific tool",
            "Reinstall tool",
            "Uninstall tool",
            "Show tool status",
            "Show operation history",
            "Settings",
            "Exit",
        ]

        menu_values = [
            "install_all",
            "category",
            "search",
            "specific",
            "reinstall",
            "uninstall",
            "status",
            "history",
            "settings",
            "exit",
        ]

        # Try questionary first for better UX (as before)
        try:
            import questionary

            choices = [f"{opt}" for opt in menu_options]
            selected = questionary.select("Select an option", choices=choices).ask()
            for i, choice in enumerate(choices):
                if choice == selected:
                    return menu_values[i]
            return "exit"
        except Exception:
            # Try simple Prompt.ask numeric fallback (used by tests)
            try:
                resp = Prompt.ask("Select an option (number or letter)")
                if resp:
                    choice = resp.strip()
                    # numeric
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(menu_values):
                            return menu_values[idx]
                    except ValueError:
                        pass
                    # letter shortcuts mapping
                    shortcuts = {
                        "a": "install_all",
                        "c": "category",
                        "s": "search",
                        "i": "specific",
                        "r": "reinstall",
                        "u": "uninstall",
                        "t": "status",
                        "h": "history",
                        "e": "settings",
                        "x": "exit",
                        "1": "install_all",
                        "2": "category",
                        "3": "search",
                        "4": "specific",
                        "5": "reinstall",
                        "6": "uninstall",
                        "7": "status",
                        "8": "history",
                        "9": "settings",
                        "0": "exit",
                    }
                    out = shortcuts.get(choice.lower())
                    if out:
                        return out
            except Exception:
                pass

            # If running in a real terminal, use interactive keyboard UI
            try:
                isatty = False
                try:
                    isatty = sys.stdin.isatty()
                except Exception:
                    isatty = False

                if isatty:
                    idx, _ = self._interactive_select(
                        "Main Menu", menu_options, allow_back=False
                    )
                    if idx is None:
                        return "exit"
                    return menu_values[idx]
            except Exception:
                pass

            # Default fallback
            return "exit"

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

    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search for tools by name or description."""
        query_lower = query.lower()
        results = []
        for tool in self.tools_config:
            name = tool["name"].lower()
            description = tool.get("description", "").lower()
            category = tool.get("category", "").lower()
            if (
                query_lower in name
                or query_lower in description
                or query_lower in category
            ):
                results.append(tool)
        return results

    def show_search_menu(self) -> List[str]:
        """Show search interface and return selected tool names."""
        self.console.clear()
        self.console.print("[bold cyan]Search Tools[/bold cyan]")

        while True:
            query = self.get_text_input(
                "Enter search terms (name, description, or category)"
            )
            if not query:
                return []

            results = self.search_tools(query)
            if not results:
                self.console.print(
                    f"[yellow]No tools found matching '{query}'[/yellow]"
                )
                if not self.get_confirmation("Try a different search?", default=True):
                    return []
                continue

            self.console.print(f"\n[green]Found {len(results)} tool(s):[/green]")
            result_names = []
            for i, tool in enumerate(results, 1):
                name = tool["name"]
                desc = tool.get("description", "")
                category = tool.get("category", "")
                installed = self.is_tool_installed(name)
                status = "[green]✓[/green]" if installed else "[red]✗[/red]"
                self.console.print(f"{i}. {status} {name} - {desc} ({category})")
                result_names.append(name)

            self.console.print(f"{len(results)+1}. Search again")
            self.console.print(f"{len(results)+2}. Back to main menu")

            while True:
                choice_input = self.get_text_input(
                    "Select tools to install (comma-separated) or choose option"
                )
                if not choice_input:
                    continue

                # Handle special options
                try:
                    choice = int(choice_input)
                    if choice == len(results) + 1:
                        break  # Search again
                    elif choice == len(results) + 2:
                        return []  # Back to main menu
                    elif 1 <= choice <= len(results):
                        # Single tool selection
                        tool_name = results[choice - 1]["name"]
                        if self.show_preview_panel([tool_name]):
                            return [tool_name]
                        return []
                    else:
                        self.console.print("[red]Invalid choice.[/red]")
                        continue
                except ValueError:
                    pass

                # Try parsing as comma-separated selections
                selections = parse_selection_input(choice_input, results)
                if selections:
                    if self.show_preview_panel(selections):
                        return selections
                    return []

                self.console.print(
                    "[red]Invalid input. Please enter numbers or 'back'.[/red]"
                )

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

        idx, val = self._interactive_select("Categories", categories, allow_back=True)
        if idx is None:
            return ""
        return val

    def show_category_tools_menu(self, category: str) -> List[str]:
        """Show tools in a category and let user select tools to install.

        Returns a list of selected tool names (could be empty if none selected).
        """
        self.console.clear()
        tools = self.get_tools_in_category(category)
        if not tools:
            self.console.print(f"[yellow]No tools in category {category}[/yellow]")
            return []

        self.console.print(f"[bold cyan]{category} Tools:[/bold cyan]")
        tool_options = []
        for i, tool in enumerate(tools, 1):
            description = tool.get("description", "")
            installed = self.is_tool_installed(tool["name"])
            status = (
                "[green]✓ Installed[/green]"
                if installed
                else "[red]✗ Not installed[/red]"
            )
            option = f"{tool['name']} - {description} - {status}"
            tool_options.append(option)
            self.console.print(f"{i}. {option}")

        self.console.print(f"{len(tools)+1}. Install all")
        self.console.print(f"{len(tools)+2}. Show details for a tool")
        self.console.print(f"{len(tools)+3}. Back to categories")

        # Present a navigable multi-select: space toggles selection, Enter confirms
        names = [t["name"] for t in tools]
        selected = []

        # Use multiselect UI
        def _multiselect(title: str, options: List[str]) -> List[str]:
            if not options:
                return []
            cur = 0
            chosen = set()
            while True:
                lines = [f"[bold cyan]{title}[/bold cyan]\n"]
                for i, opt in enumerate(options):
                    mark = "[x]" if opt in chosen else "[ ]"
                    pointer = ">" if i == cur else " "
                    lines.append(f"{pointer} {i+1}. {mark} {opt}")
                lines.append(
                    "\nSpace: toggle, Enter: confirm, d: details, a: toggle all, q: back"
                )
                content = "\n".join(lines)
                self.layout["content"].update(
                    Panel(content, title=title, border_style="blue")
                )
                key = self._read_key()
                if key in ("\x1b[A", "k"):
                    cur = (cur - 1) % len(options)
                    continue
                if key in ("\x1b[B", "j"):
                    cur = (cur + 1) % len(options)
                    continue
                if key == " ":
                    opt = options[cur]
                    if opt in chosen:
                        chosen.remove(opt)
                    else:
                        chosen.add(opt)
                    continue
                if key in ("\r", "\n"):
                    return [o for o in options if o in chosen]
                if key == "a":
                    # toggle all
                    if len(chosen) == len(options):
                        chosen.clear()
                    else:
                        chosen = set(options)
                    continue
                if key == "d":
                    # show details for current
                    self.show_tool_details(options[cur])
                    continue
                if key in ("q", "b", "\x03"):
                    return []
                # numbers quick toggle
                if key.isdigit():
                    n = int(key)
                    if 1 <= n <= len(options):
                        opt = options[n - 1]
                        if opt in chosen:
                            chosen.remove(opt)
                        else:
                            chosen.add(opt)
                    continue

        return _multiselect(category + " Tools", names)

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
        if self.get_confirmation("Proceed with installation?", default=True):
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

    def show_tool_details(self, tool_name: str) -> None:
        """Show detailed information about a specific tool."""
        self.console.clear()
        tool = next((t for t in self.tools_config if t["name"] == tool_name), None)
        if not tool:
            self.console.print(f"[red]Tool '{tool_name}' not found.[/red]")
            return

        installed = self.is_tool_installed(tool_name)
        status = "[green]Installed[/green]" if installed else "[red]Not Installed[/red]"

        content = f"""[bold]Name:[/bold] {tool['name']}
[bold]Description:[/bold] {tool.get('description', 'No description')}
[bold]Category:[/bold] {tool.get('category', 'Uncategorized')}
[bold]Status:[/bold] {status}
[bold]URL:[/bold] {tool.get('url', 'N/A')}

[bold]Installation Details:[/bold]
• Binary Path: {tool.get('binary_path', 'N/A')}
• Requires Cargo: {'Yes' if tool.get('name') == 'terrific_audio_driver' else 'No'}
"""

        build_cmds = tool.get("build_commands", {})
        if build_cmds:
            platform_cmds = (
                build_cmds.get(sys.platform, [])
                if isinstance(build_cmds, dict)
                else build_cmds
            )
            if platform_cmds:
                content += f"\n[bold]Build Commands:[/bold]\n"
                for cmd in platform_cmds:
                    content += f"  • {cmd}\n"

        instructions = tool.get("install_instructions", "")
        if instructions:
            content += f"\n[bold]Install Instructions:[/bold]\n{instructions}"

        panel = Panel(
            content,
            title=f"Tool Details: {tool_name}",
            border_style="blue",
            expand=False,
        )
        self.console.print(panel)

    def show_preview_panel(self, tool_names: List[str]) -> bool:
        """Show a preview panel summarizing planned actions for provided tool names.

        Returns True if user confirms to proceed, False otherwise.
        """
        self.console.clear()
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
        return self.get_confirmation(
            "Proceed with installation for these tools?", default=False
        )

    def select_tool(self, prompt: str, tool_list: List[str]) -> str | None:
        """Select a tool from the provided list using interactive prompt."""
        self.console.clear()
        if not tool_list:
            return None
        idx, val = self._interactive_select(prompt, tool_list, allow_back=True)
        if idx is None:
            return None
        return val

    def install_specific_tool(self) -> None:
        """Install a specific tool selected by the user."""
        all_tools = [t["name"] for t in self.tools_config]
        if not all_tools:
            self.console.print("[yellow]No tools configured.[/yellow]")
            return

        tool_name = self.select_tool("Select a tool to install:", all_tools)
        if tool_name:
            installed = self.is_tool_installed(tool_name)
            if installed:
                if not self.get_confirmation(
                    f"{tool_name} is already installed. Reinstall?", default=False
                ):
                    return
                # Uninstall first
                self.console.print(f"Uninstalling {tool_name}...")
                if self.installer.uninstall_tool(tool_name):
                    self.console.print(f"[green]✓[/green] Uninstalled {tool_name}")
                else:
                    self.console.print(f"[red]✗[/red] Failed to uninstall {tool_name}")
                    return

            # Install
            self.install_selected_tools([tool_name])

    def reinstall_tool(self) -> None:
        """Reinstall a tool that is already installed."""
        installed_tools = self.get_installed_tools()
        if not installed_tools:
            self.console.print("[yellow]No tools are currently installed.[/yellow]")
            return

        tool_name = self.select_tool("Select a tool to reinstall:", installed_tools)
        if tool_name:
            if self.get_confirmation(
                f"[yellow]This will uninstall and reinstall {tool_name}. Continue?",
                default=False,
            ):
                # First uninstall
                self.console.print(f"Uninstalling {tool_name}...")
                if self.installer.uninstall_tool(tool_name):
                    self.console.print(f"[green]✓[/green] Uninstalled {tool_name}")
                    self.operation_history.append(
                        f"Uninstalled {tool_name} for reinstall"
                    )
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
            if self.get_confirmation(
                f"[red]This will permanently remove {tool_name}. Continue?",
                default=False,
            ):
                self.console.print(f"Uninstalling {tool_name}...")
                if self.installer.uninstall_tool(tool_name):
                    self.console.print(
                        f"[green]✓[/green] Successfully uninstalled {tool_name}"
                    )
                    self.operation_history.append(f"Uninstalled {tool_name}")
                else:
                    self.console.print(f"[red]✗[/red] Failed to uninstall {tool_name}")
                    self.operation_history.append(f"Failed to uninstall {tool_name}")

    def show_status(self) -> None:
        """Show detailed status of all tools using categorized panels."""
        self.console.clear()
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

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            overall_task = progress.add_task(
                "Installing tools...", total=len(tools_to_install)
            )

            for tool_name in tools_to_install:
                tool_task = progress.add_task(f"Installing {tool_name}...", total=1)

                try:
                    # Find the tool config
                    tool_config = next(
                        (t for t in self.tools_config if t["name"] == tool_name), None
                    )
                    if not tool_config:
                        progress.update(
                            tool_task,
                            description=f"[red]Configuration not found for {tool_name}[/red]",
                        )
                        progress.update(overall_task, advance=1)
                        continue

                    # Install the tool
                    self.installer.install_selected_tools([tool_name])

                    progress.update(
                        tool_task,
                        description=f"[green]✓[/green] Successfully installed {tool_name}",
                        completed=1,
                    )
                    progress.update(overall_task, advance=1)
                    self.operation_history.append(f"Installed {tool_name}")

                except Exception as e:
                    progress.update(
                        tool_task,
                        description=f"[red]✗[/red] Failed to install {tool_name}: {str(e)}",
                        completed=1,
                    )
                    progress.update(overall_task, advance=1)
                    self.operation_history.append(
                        f"Failed to install {tool_name}: {str(e)}"
                    )

        # Setup PATH and IDEs after installation
        self.console.print("\n[bold]Setting up environment...[/bold]")
        add_to_path()
        setup_ides()
        self.console.print("[green]✓[/green] Environment setup complete")

    def run(self) -> None:
        """Run the TUI."""
        # Prefer Textual-based TUI when available and running in a TTY
        try:
            use_textual = False
            try:
                import importlib

                textual_spec = importlib.util.find_spec("textual")
                if textual_spec and sys.stdin.isatty():
                    use_textual = True
            except Exception:
                use_textual = False

            if use_textual:
                # Run the Textual app which provides a richer TUI experience
                try:
                    from snes_installer.tui_textual import run_textual_tui

                    run_textual_tui(self)
                    return
                except Exception:
                    # If textual app fails to start, fall back to existing Rich-based TUI
                    pass
        except Exception:
            # If any of the checks fail, fall back to the existing implementation
            pass

        console = Console()
        self.render_header()
        self.render_footer()
        self.render_menu()
        self.render_content("[bold white]Welcome to the SNES Installer![/bold white]")
        with Live(self.layout, refresh_per_second=10, console=console):
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
                    elif choice in {"3", "search"}:
                        selections = self.show_search_menu()
                        if selections:
                            self.install_selected_tools(selections)
                    elif choice in {"4", "specific"}:
                        self.install_specific_tool()
                    elif choice in {"5", "reinstall"}:
                        self.reinstall_tool()
                    elif choice in {"6", "uninstall"}:
                        self.uninstall_tool()
                    elif choice in {"7", "status"}:
                        self.show_status()
                    elif choice in {"8", "history"}:
                        self.show_operation_history()
                    elif choice in {"9", "settings"}:
                        self.show_settings_menu()
                    elif choice in {"0", "exit"}:
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
