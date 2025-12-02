"""SNES-IDE Tool Manager TUI - Textual implementation.

Run with:
    python src/snes-ide.py --tui
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive, var
from textual.widgets import (
    DirectoryTree, Footer, Header, Static, Tree
)
from textual.widgets.tree import TreeNode


class ToolDetailView(Static):
    """Display detailed information about a selected tool."""

    tool_data: reactive[Dict[str, Any] | None] = reactive(None)

    def render(self) -> str:
        """Render the tool details."""
        if self.tool_data is None:
            return "[dim]Select a tool to view details[/dim]"

        # Safeguard: ensure tool_data is a dict
        if not isinstance(self.tool_data, dict):
            return "[dim]Invalid tool data. Select a tool to view details[/dim]"

        tool = self.tool_data
        lines = []

        # Tool name and status
        available = tool.get("available", False)
        status_icon = "✓" if available else "✗"
        status_color = "green" if available else "red"
        status_text = "AVAILABLE" if available else "NOT INSTALLED"

        lines.append(f"[bold]{tool['name']}[/bold]")
        lines.append(f"[{status_color}][{status_icon}] {status_text}[/{status_color}]")
        lines.append("")

        # Description
        if tool.get("description"):
            lines.append(f"[bold]Description:[/bold]")
            lines.append(f"[dim]{tool['description']}[/dim]")
            lines.append("")

        # Category
        if tool.get("category"):
            lines.append(f"[bold]Category:[/bold] {tool['category']}")
            lines.append("")

        # Path
        if available and tool.get("path"):
            lines.append(f"[bold]Path:[/bold]")
            lines.append(f"[blue]{tool['path']}[/blue]")
            lines.append("")

        # Binary path (relative to installation)
        if tool.get("binary_path"):
            lines.append(f"[bold]Binary Path:[/bold]")
            lines.append(f"[dim]{tool['binary_path']}[/dim]")
            lines.append("")

        # URL
        if tool.get("url"):
            url = tool["url"]
            if isinstance(url, dict):
                url = url.get("linux") or url.get("darwin") or url.get("win32") or "Multiple URLs"
            lines.append(f"[bold]Download:[/bold]")
            lines.append(f"[cyan]{url}[/cyan]")
            lines.append("")

        # Build commands
        if tool.get("build_commands"):
            build_cmds = tool["build_commands"]
            if isinstance(build_cmds, dict) and any(build_cmds.values()):
                lines.append(f"[bold]Build Commands:[/bold]")
                for platform, cmds in build_cmds.items():
                    if cmds:
                        lines.append(f"[dim]{platform}:[/dim] {'; '.join(cmds)}")
                lines.append("")

        # Install instructions
        if tool.get("install_instructions"):
            lines.append(f"[bold]Installation Notes:[/bold]")
            lines.append(f"[yellow]{tool['install_instructions']}[/yellow]")
            lines.append("")

        # If not available
        if not available:
            lines.append("[yellow]This tool is not installed or not in PATH[/yellow]")
            if tool.get("url"):
                lines.append("[dim]See URL above to download and build[/dim]")

        return "\n".join(lines)

    def watch_tool_data(self, tool_data: Dict[str, Any] | None) -> None:
        """Called when tool data is updated."""
        self.update(self.render())


class ToolBrowser(App):
    """Textual tool manager browser app."""

    CSS_PATH = "tools_browser.tcss"
    BINDINGS = [
        ("t", "toggle_tree", "Toggle Tree"),
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    show_tree = var(True)
    selected_tool: reactive[Dict[str, Any] | None] = reactive(None)

    def __init__(self):
        """Initialize the app."""
        super().__init__()
        self.tools_by_category: Dict[str, list] = {}
        self.all_tools_map: Dict[str, Dict[str, Any]] = {}
        self.load_tools_from_json()

    def load_tools_from_json(self) -> None:
        """Load tools from tools.json and check availability."""
        tools_json_path = Path(__file__).parent / "tools.json"
        
        if not tools_json_path.exists():
            # Fallback to tools_.json if it exists
            tools_json_path = Path(__file__).parent / "tools_.json"
        
        if not tools_json_path.exists():
            print(f"Error: Could not find tools.json at {tools_json_path}")
            sys.exit(1)
        
        try:
            with open(tools_json_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error parsing {tools_json_path}: {e}")
            sys.exit(1)
        
        # Process tools
        tools = data.get("tools", [])
        
        for tool_def in tools:
            tool_name = tool_def.get("name")
            if not tool_name:
                continue
            
            # Check if tool is available in PATH
            available = self._check_tool_available(tool_def)
            
            # Create tool record
            tool_record = {
                **tool_def,
                "available": available,
                "path": self._find_tool_path(tool_def) if available else None,
            }
            
            self.all_tools_map[tool_name] = tool_record
            
            # Organize by category
            category = tool_def.get("category", "Other")
            if category not in self.tools_by_category:
                self.tools_by_category[category] = []
            self.tools_by_category[category].append(tool_record)

    def _check_tool_available(self, tool_def: Dict[str, Any]) -> bool:
        """Check if a tool is available in PATH."""
        import shutil
        
        # Try to find the tool by name
        tool_name = tool_def.get("name")
        if tool_name and isinstance(tool_name, str) and shutil.which(tool_name):
            return True
        
        # Try binary_name field (if it's a string)
        binary_name = tool_def.get("binary_name")
        if binary_name and isinstance(binary_name, str) and shutil.which(binary_name):
            return True
        
        # For tools with complex binary_path, just check by name
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
        if binary_name and isinstance(binary_name, str):
            path = shutil.which(binary_name)
            if path:
                return path
        
        return None

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header(show_clock=False)
        with Container():
            yield Tree("Tools", id="tree-view")
            with VerticalScroll(id="detail-view"):
                yield ToolDetailView(id="tool-detail", expand=True)
        yield Footer()

    def on_mount(self) -> None:
        """Initialize when app mounts."""
        self.populate_tree()
        tree = self.query_one(Tree)
        tree.focus()

    def populate_tree(self) -> None:
        """Populate the tree with tools from tools.json."""
        tree = self.query_one(Tree)
        tree.clear()
        root = tree.root

        for category in sorted(self.tools_by_category.keys()):
            tools = self.tools_by_category[category]

            # Add category node with counts
            available_count = sum(1 for t in tools if t.get("available"))
            total_count = len(tools)
            cat_label = f"[bold]{category}[/bold] ({available_count}/{total_count})"

            category_node = root.add(cat_label)

            # Add tools in this category, sorted by availability then name
            for tool in sorted(
                tools,
                key=lambda t: (not t.get("available"), t["name"])
            ):
                tool_name = tool["name"]
                status_icon = "✓" if tool.get("available") else "✗"
                tool_label = f"{status_icon} {tool_name}"

                tool_node = category_node.add(tool_label)
                # Store tool name for later lookup
                tool_node.data = tool_name

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when a node is selected in the tree."""
        node = event.node
        if node.data and isinstance(node.data, str):
            # This is a tool node
            tool_name = node.data
            if tool_name in self.all_tools_map:
                self.selected_tool = self.all_tools_map[tool_name]
        else:
            # Category or root node selected
            self.selected_tool = None

    def watch_selected_tool(self, tool_data: Dict[str, Any] | None) -> None:
        """Called when selected tool changes."""
        detail_view = self.query_one("#tool-detail", ToolDetailView)
        detail_view.tool_data = tool_data
        self.query_one("#detail-view", VerticalScroll).scroll_home(animate=False)

    def action_toggle_tree(self) -> None:
        """Toggle tree visibility."""
        self.show_tree = not self.show_tree

    def action_refresh(self) -> None:
        """Refresh the tool list."""
        self.load_tools_from_json()
        self.populate_tree()
        detail_view = self.query_one("#tool-detail", ToolDetailView)
        detail_view.update(detail_view.render())


if __name__ == "__main__":
    ToolBrowser().run()
