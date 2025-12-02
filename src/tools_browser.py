"""SNES-IDE Tool Manager TUI - Textual implementation.

Run with:
    python src/snes-ide.py --tui
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static, Rule


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
                item = ListItem(Label(f"{icon} {tool['name']}"), id=f"tool-{tool['name']}")
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


if __name__ == "__main__":
    ToolBrowser().run()
