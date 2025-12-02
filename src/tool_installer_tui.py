"""Textual TUI for SNES-IDE Tool Installer.

A terminal user interface for managing and viewing SNES development tools.
Mirrors the functionality of ToolInstallerDialog but as a native TUI application.

Usage:
    python tool_installer_tui.py
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.containers import Horizontal
from textual.containers import Vertical
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import Header
from textual.widgets import Label
from textual.widgets import Static
from textual.widgets import Footer

from tool_manager import ToolManager

if TYPE_CHECKING:
    from textual.app import RenderResult


class ToolStatusWidget(Static):
    """Widget displaying a single tool's status and information."""

    DEFAULT_CSS = """
    ToolStatusWidget {
        border: solid $panel;
        padding: 1 2;
        margin: 0 0 1 0;
    }

    ToolStatusWidget > #tool-name {
        color: $text;
        text-style: bold;
    }

    ToolStatusWidget > #tool-description {
        color: $text-muted;
        text-style: italic;
        width: 1fr;
    }

    ToolStatusWidget > Horizontal {
        height: auto;
        margin: 1 0 0 0;
    }

    ToolStatusWidget > Horizontal > Static {
        width: auto;
        margin-right: 2;
    }

    ToolStatusWidget.available > #status-indicator {
        color: $success;
    }

    ToolStatusWidget.missing > #status-indicator {
        color: $error;
    }

    ToolStatusWidget.required {
        border: heavy $primary;
    }
    """

    def __init__(
        self,
        tool_status: dict,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.tool_status = tool_status

    def render(self) -> str:
        """Render the tool status widget."""
        name = self.tool_status["name"]
        description = self.tool_status.get("description", "No description")
        available = self.tool_status.get("available", False)
        path = self.tool_status.get("path")
        priority = self.tool_status.get("priority", "optional")

        status_icon = "✓" if available else "✗"
        status_text = "Available" if available else "Missing"

        # Update CSS class based on availability
        self.set_class(available, "available")
        self.set_class(not available, "missing")
        self.set_class(priority == "required", "required")

        return f"""[bold]{name}[/bold] [{status_icon}] {status_text}
[dim]{description}[/dim]
{f"[dim]Path: {path}[/dim]" if path else "[dim italic]Not found in PATH[/dim italic]"}"""


class CategorySection(Static):
    """Widget displaying a category of tools."""

    DEFAULT_CSS = """
    CategorySection {
        layout: vertical;
        border: round $panel;
        padding: 1 2;
        margin: 0 0 2 0;
    }

    CategorySection > #category-title {
        color: $primary;
        text-style: bold;
        margin: 0 0 1 0;
    }

    CategorySection > #tools-container {
        layout: vertical;
        height: auto;
    }
    """

    def __init__(
        self,
        category: str,
        tools: list[dict],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.category = category
        self.tools = tools

    def compose(self) -> ComposeResult:
        """Create child widgets for this category."""
        yield Label(self.category.upper(), id="category-title")
        with Container(id="tools-container"):
            for tool in self.tools:
                yield ToolStatusWidget(tool)


class ToolInstallerTUI(Screen):
    """Main TUI screen for the tool installer."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    # CSS will be loaded from string since CSS_PATH might not exist during testing
    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }

    Header {
        dock: top;
        height: 1;
        background: $boost;
    }

    Footer {
        dock: bottom;
        height: 1;
        background: $boost;
        border-top: solid $primary;
    }

    #title {
        dock: top;
        height: 3;
        content-align: center middle;
        background: $primary 20%;
        color: $primary;
        text-style: bold;
        border-bottom: heavy $primary;
        margin-bottom: 1;
    }

    #tools-scroll {
        border: solid $panel;
        height: 1fr;
        overflow: auto;
        padding: 1;
    }

    #button-bar {
        dock: bottom;
        height: 3;
        background: $boost;
        border-top: solid $primary;
        padding: 1;
        layout: horizontal;
    }

    #button-bar > Button {
        margin-right: 2;
        width: auto;
    }

    .status-label {
        width: 1fr;
        height: auto;
        margin-bottom: 1;
        text-align: center;
        color: $text-muted;
        text-style: italic;
    }

    CategorySection {
        layout: vertical;
        border: round $accent;
        padding: 1 2;
        margin-bottom: 1;
        background: $panel;
    }

    CategorySection > #category-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }

    CategorySection > #tools-container {
        layout: vertical;
        height: auto;
    }

    ToolStatusWidget {
        border: solid $primary;
        padding: 1 2;
        margin-bottom: 1;
        height: auto;
        background: $surface;
    }

    ToolStatusWidget.available {
        border: solid $success;
        background: $success 5%;
    }

    ToolStatusWidget.missing {
        border: solid $error;
        background: $error 5%;
    }

    ToolStatusWidget.required {
        border: heavy $warning;
        background: $warning 5%;
    }

    ToolStatusWidget:hover {
        background: $primary 10%;
    }

    Button {
        margin-right: 1;
    }

    Button.primary {
        background: $primary;
        border: heavy $primary;
    }

    Button:hover {
        background: $accent;
        border: heavy $accent;
    }

    Button:focus {
        background: $boost;
        border: heavy $accent;
    }
    """

    loading: reactive[bool] = reactive(False)

    def __init__(self, tools_config_path: str | Path | None = None):
        """Initialize the TUI app.

        Args:
            tools_config_path: Path to tools.json configuration file.
                If None, looks for src/tools.json relative to this file.
        """
        super().__init__()
        if tools_config_path is None:
            tools_config_path = Path(__file__).parent / "tools.json"
        self.tool_manager = ToolManager(tools_config_path)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=False)
        with Vertical():
            yield Label("SNES-IDE Tool Installer", id="title")
            with VerticalScroll(id="tools-scroll"):
                yield Label(id="status-label", classes="status-label")
                yield Container(id="tools-container")
        with Horizontal(id="button-bar"):
            yield Button("Refresh", id="btn-refresh", variant="primary")
            yield Button("Quit", id="btn-quit", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        """Load tools data when the app mounts."""
        self.load_tools()

    def load_tools(self) -> None:
        """Load and display tools by category."""
        try:
            self.loading = True
            self.update_status_label("Loading tools...")

            tools_by_category = self.tool_manager.get_tools_by_category()

            # Clear existing tools
            tools_container = self.query_one("#tools-container", Container)
            tools_container.remove_children()

            if not tools_by_category:
                self.update_status_label("No tools configured")
                self.loading = False
                return

            # Add tools by category
            for category, tools in sorted(tools_by_category.items()):
                section = CategorySection(category, tools)
                tools_container.mount(section)

            # Calculate summary
            all_tools = self.tool_manager.get_all_tools_status()
            available = sum(1 for t in all_tools if t.get("available"))
            missing = len(all_tools) - available
            required_missing = len(self.tool_manager.get_missing_required_tools())

            summary = (
                f"Tools: {available} available, {missing} missing"
                f" (⚠ {required_missing} required missing)"
                if required_missing
                else f"Tools: {available} available, {missing} missing"
            )
            self.update_status_label(summary)
            self.loading = False

        except Exception as e:
            self.update_status_label(f"Error loading tools: {e}")
            self.loading = False

    def update_status_label(self, text: str) -> None:
        """Update the status label at the top."""
        try:
            label = self.query_one("#status-label", Label)
            label.update(text)
        except Exception:
            pass

    def action_refresh(self) -> None:
        """Refresh the tool list."""
        self.load_tools()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "btn-refresh":
            self.action_refresh()
        elif button_id == "btn-quit":
            self.app.exit()


if __name__ == "__main__":
    from textual.app import App

    class ToolInstallerApp(App):
        """Tool Installer TUI Application."""

        TITLE = "SNES-IDE Tool Installer"
        SUB_TITLE = "Manage your development tools"

        def on_mount(self) -> None:
            """Initialize the app."""
            tui = ToolInstallerTUI()
            self.push_screen(tui)

    app = ToolInstallerApp()
    app.run()
