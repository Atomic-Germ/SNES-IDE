"""SNES-IDE Tool Manager TUI - Textual implementation.

Run with:
    python src/snes-ide.py --tui
"""

from __future__ import annotations

import sys
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

from tool_manager import ToolManager


class ToolDetailView(Static):
    """Display detailed information about a selected tool."""

    tool_data: reactive[Dict[str, Any] | None] = reactive(None)

    def render(self) -> str:
        """Render the tool details."""
        if self.tool_data is None:
            return "[dim]Select a tool to view details[/dim]"

        tool = self.tool_data
        lines = []

        # Tool name and status
        status_icon = "✓" if tool.get("available") else "✗"
        status_color = "green" if tool.get("available") else "red"
        status_text = "AVAILABLE" if tool.get("available") else "MISSING"

        lines.append(f"[bold]{tool['name']}[/bold]")
        lines.append(f"[{status_color}][{status_icon}] {status_text}[/{status_color}]")
        lines.append("")

        # Priority
        priority = tool.get("priority", "optional").upper()
        if tool.get("priority") == "required" and not tool.get("available"):
            lines.append(f"[yellow bold]⚠ PRIORITY: {priority}[/yellow bold]")
        else:
            lines.append(f"Priority: {priority}")
        lines.append("")

        # Description
        lines.append(f"[bold]Description:[/bold]")
        lines.append(f"[dim]{tool.get('description', 'No description')}[/dim]")
        lines.append("")

        # Path
        if tool.get("available"):
            lines.append(f"[bold]Path:[/bold]")
            lines.append(f"[blue]{tool.get('path', 'N/A')}[/blue]")
            lines.append("")

        # Category
        lines.append(f"[bold]Category:[/bold] {tool.get('category', 'Unknown')}")
        lines.append("")

        # SDK info if applicable
        if tool.get("is_sdk"):
            lines.append(f"[cyan bold]This is an SDK[/cyan bold]")
            lines.append("")

        # Additional info if missing
        if not tool.get("available"):
            lines.append("[yellow]This tool is not installed or not in PATH[/yellow]")

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
        self.tool_manager = ToolManager(Path(__file__).parent / "tools.json")
        self.tools_by_category = {}
        self.all_tools_map = {}

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
        self.load_tools()
        tree = self.query_one(Tree)
        tree.focus()

    def load_tools(self) -> None:
        """Load tools from manager and populate tree."""
        self.tools_by_category = self.tool_manager.get_tools_by_category()
        all_tools = self.tool_manager.get_all_tools_status()

        # Build map of all tools for quick lookup
        for tool in all_tools:
            self.all_tools_map[tool["name"]] = tool

        # Populate tree
        tree = self.query_one(Tree)
        tree.clear()
        root = tree.root

        for category in sorted(self.tools_by_category.keys()):
            tools = self.tools_by_category[category]

            # Add category node
            cat_label = f"[bold]{category.upper()}[/bold]"
            available_count = sum(1 for t in tools if t.get("available"))
            total_count = len(tools)
            cat_label += f" ({available_count}/{total_count})"

            category_node = root.add(cat_label)

            # Add tools in this category
            for tool in sorted(tools, key=lambda t: (not t.get("available"), t["name"])):
                tool_name = tool["name"]
                status_icon = "✓" if tool.get("available") else "✗"

                tool_label = f"{status_icon} {tool_name}"
                if tool.get("priority") == "required" and not tool.get("available"):
                    tool_label = f"[yellow]{tool_label} ⚠[/yellow]"

                tool_node = category_node.add(tool_label)
                # Store tool name for later lookup
                tool_node.data = tool_name

    def on_tree_select(self, event) -> None:
        """Called when a node is selected in the tree."""
        node = event.node
        if node.data and isinstance(node.data, str):
            # This is a tool node
            tool_name = node.data
            if tool_name in self.all_tools_map:
                self.selected_tool = self.all_tools_map[tool_name]

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
        self.load_tools()
        detail_view = self.query_one("#tool-detail", ToolDetailView)
        detail_view.update(detail_view.render())


if __name__ == "__main__":
    ToolBrowser().run()
