from __future__ import annotations

from typing import Dict, Any

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, Label

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
