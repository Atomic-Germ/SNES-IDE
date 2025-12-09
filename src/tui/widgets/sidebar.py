from __future__ import annotations

from pathlib import Path
from typing import Tuple

from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Label, ListView, DirectoryTree, Collapsible
)

from ..logic.graphics import SNESTileset, SNESTile

class ProjectTree(DirectoryTree):
    """Project file browser with filtering for relevant files."""
    
    DEFAULT_CSS = """
    ProjectTree {
        height: auto;
        max-height: 20;
        background: $panel;
        scrollbar-gutter: stable;
    }
    """

    # File extensions to show
    SHOW_EXTENSIONS = {
        ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
        ".asm", ".s", ".inc",
        ".py", ".java", ".cs",
        ".json", ".yaml", ".yml", ".toml",
        ".md", ".rst", ".txt",
        ".sh", ".bash", ".bat", ".cmd", ".ps1",
        ".xml", ".html", ".css",
        ".lua", ".rb", ".rs", ".go",
        # Graphics files for tile editor
        ".png", ".bmp", ".gif", ".jpg", ".jpeg",
        # SNES-specific formats
        ".pic", ".pal", ".map", ".chr",
        # Audio files
        ".brr", ".wav", ".spc",
        # ROM files
        ".sfc", ".smc",
    }
    
    # Filenames to always show (case-insensitive)
    SHOW_NAMES = {
        "makefile", "gnumakefile", "cmakelists.txt", 
        "readme", "license", "copying", "changelog",
        ".gitignore", ".gitattributes",
    }
    
    # Directories to hide
    HIDE_DIRS = {
        "__pycache__", ".git", ".svn", ".hg", 
        "node_modules", ".venv", "venv", ".env",
        "build", "dist", ".tox", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", "target",
    }

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Filter paths to show only relevant files."""
        filtered = []
        for path in paths:
            name_lower = path.name.lower()
            
            if path.is_dir():
                # Hide certain directories
                if name_lower not in self.HIDE_DIRS:
                    filtered.append(path)
            else:
                # Show files with relevant extensions or special names
                if (path.suffix.lower() in self.SHOW_EXTENSIONS or 
                    name_lower in self.SHOW_NAMES or
                    any(name_lower.startswith(n) for n in self.SHOW_NAMES)):
                    filtered.append(path)
        
        return sorted(filtered, key=lambda p: (not p.is_dir(), p.name.lower()))


class ToolSelector(Widget):
    """Widget for selecting drawing tools.
    
    Displays tool buttons that can be clicked to select the active tool.
    Each tool on its own line for clarity.
    """
    
    DEFAULT_CSS = """
    ToolSelector {
        height: auto;
        padding: 0 1;
        background: $panel;
    }
    """
    
    # Available tools with their display info
    TOOLS = [
        ("pencil", "✏️", "Pencil", "P"),
        ("eyedropper", "💉", "Eyedropper", "Y"),
        ("fill", "🪣", "Fill", "B"),
        ("line", "╱", "Line", "L"),
        ("rect", "▭", "Rectangle", "T"),
        ("ellipse", "◯", "Ellipse", "E"),
    ]
    
    selected_tool: reactive[str] = reactive("pencil")
    
    def render(self) -> Text:
        """Render the tool selector with each tool on its own line."""
        text = Text()
        
        for i, (tool_id, icon, name, key) in enumerate(self.TOOLS):
            if i > 0:
                text.append("\n")
            
            if tool_id == self.selected_tool:
                # Selected tool - highlighted
                text.append(f" {icon} {name} ", style="bold reverse")
                text.append(f" [{key}]", style="dim")
            else:
                text.append(f" {icon} {name} ", style="")
                text.append(f" [{key}]", style="dim")
        
        return text
    
    def on_click(self, event: Click) -> None:
        """Handle click to select a tool."""
        # Each tool is on its own line
        y = event.y
        
        if 0 <= y < len(self.TOOLS):
            tool_id = self.TOOLS[y][0]
            self.selected_tool = tool_id
            self.post_message(self.ToolSelected(tool_id))
            self.refresh()
    
    class ToolSelected(Message):
        """Message sent when a tool is selected."""
        def __init__(self, tool: str):
            super().__init__()
            self.tool = tool


class TilesetPreview(Widget):
    """Widget showing thumbnail previews of tiles in a tileset.
    
    Displays a grid of tile thumbnails that can be clicked to select.
    Uses compact half-block rendering for tile display.
    """
    
    DEFAULT_CSS = """
    TilesetPreview {
        height: auto;
        min-height: 5;
        max-height: 12;
        padding: 0 1;
        background: $panel;
        overflow-y: auto;
    }
    """
    
    selected_tile: reactive[int] = reactive(0)
    
    def __init__(
        self,
        tileset: SNESTileset | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._tileset = tileset
        self._tiles_per_row = 8  # How many tile thumbnails per row
    
    @property
    def tileset(self) -> SNESTileset | None:
        return self._tileset
    
    @tileset.setter
    def tileset(self, value: SNESTileset | None) -> None:
        self._tileset = value
        self.refresh()
    
    def render(self) -> Text:
        """Render tile thumbnails as a grid."""
        if not self._tileset or not self._tileset.tiles:
            return Text("[dim]No tileset loaded[/dim]")
        
        text = Text()
        text.append(f"Tiles: {len(self._tileset.tiles)}\n")
        
        # Render compact tile index display
        # Each tile shown as its index in a colored square
        tiles_per_row = self._tiles_per_row
        for i, tile in enumerate(self._tileset.tiles):
            if i > 0 and i % tiles_per_row == 0:
                text.append("\n")
            
            # Get the dominant/average color of the tile for background
            avg_color = self._get_tile_avg_color(tile)
            r, g, b = avg_color
            
            # Show tile index
            if i == self.selected_tile:
                text.append(f"[{i:02X}]", style=f"bold white on rgb({r},{g},{b})")
            else:
                text.append(f" {i:02X} ", style=f"on rgb({r},{g},{b})")
        
        return text
    
    def _get_tile_avg_color(self, tile: SNESTile) -> Tuple[int, int, int]:
        """Get average color of a tile for preview background.
        
        Averages ALL pixels in the tile for a mosaic-like thumbnail effect.
        This gives a better visual representation of the tile content.
        """
        if not self._tileset:
            return (64, 64, 64)
        
        palette = self._tileset.palette
        r_sum, g_sum, b_sum = 0, 0, 0
        count = 0
        
        # Average ALL pixels for accurate color representation
        for y in range(tile.height):
            for x in range(tile.width):
                idx = tile.get_pixel(x, y)
                r, g, b = palette.get_color(0, idx)
                r_sum += r
                g_sum += g
                b_sum += b
                count += 1
        
        if count == 0:
            return (64, 64, 64)
        
        return (r_sum // count, g_sum // count, b_sum // count)
    
    def on_click(self, event: Click) -> None:
        """Handle click to select a tile."""
        if not self._tileset or not self._tileset.tiles:
            return
        
        # Calculate which tile was clicked
        # First line is "Tiles: N\n"
        y = event.y
        x = event.x
        
        if y == 0:  # Header line
            return
        
        # Each tile is 4 chars wide ([XX] or " XX ")
        tile_row = y - 1  # Account for header
        tile_col = x // 4
        
        tile_idx = tile_row * self._tiles_per_row + tile_col
        
        if 0 <= tile_idx < len(self._tileset.tiles):
            self.selected_tile = tile_idx
            self.post_message(self.TileSelected(tile_idx))
            self.refresh()
    
    class TileSelected(Message):
        """Message sent when a tile is selected."""
        def __init__(self, tile_index: int):
            super().__init__()
            self.tile_index = tile_index


class Sidebar(Widget):
    """Animated sidebar with collapsible sections for Tools and Project."""

    DEFAULT_CSS = """
    Sidebar {
        width: 45;
        layer: sidebar;
        dock: left;
        offset-x: -100%;
        background: $panel;
        border-right: tall $background;
        transition: offset 200ms;
        overflow-y: auto;
        
        &.-visible {
            offset-x: 0;
        }
        
        #sidebar-title {
            dock: top;
            padding: 1 2;
            background: $accent;
            color: $text;
            text-style: bold;
            text-align: center;
        }
        
        Collapsible {
            padding: 0;
            border: none;
            background: $panel;
        }
        
        CollapsibleTitle {
            padding: 0 1;
            background: $primary 30%;
        }
        
        CollapsibleTitle:hover {
            background: $primary 50%;
        }
        
        ListView {
            height: auto;
            max-height: 25;
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
        
        #project-tree-container {
            height: auto;
            max-height: 20;
            background: $panel;
        }
        
        #project-content {
            height: auto;
            max-height: 25;
            background: $panel;
        }
        
        #project-tree {
            height: auto;
            max-height: 24;
        }
        
        #no-project-label {
            padding: 1 2;
            color: $text-muted;
        }
    }
    """
    
    project_path: reactive[Path | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Label("⚡ SNES-IDE", id="sidebar-title")
        with VerticalScroll():
            with Collapsible(title="📁 Project", collapsed=False, id="project-section"):
                with Vertical(id="project-content"):
                    yield Label("[dim]No project open[/dim]", id="no-project-label")
                    # ProjectTree will be added here dynamically
            with Collapsible(title="✏️ Drawing", collapsed=True, id="drawing-section"):
                with Vertical(id="drawing-content"):
                    yield ToolSelector(id="tool-selector")
                    yield TilesetPreview(id="tileset-preview")
            with Collapsible(title="🛠 Tools", collapsed=False, id="tools-section"):
                yield ListView(id="tool-list")
    
    def watch_project_path(self, project_path: Path | None) -> None:
        """Update the project tree when path changes."""
        project_content = self.query_one("#project-content", Vertical)
        no_project_label = self.query_one("#no-project-label", Label)
        
        # Remove existing ProjectTree if any
        for tree in self.query(ProjectTree):
            tree.remove()
        
        if project_path and project_path.exists():
            no_project_label.display = False
            tree = ProjectTree(project_path, id="project-tree")
            project_content.mount(tree)
            # Expand the project section
            self.query_one("#project-section", Collapsible).collapsed = False

    def show_drawing_section(self, tileset: SNESTileset) -> None:
        """Show the drawing section and update tileset preview."""
        drawing_section = self.query_one("#drawing-section", Collapsible)
        drawing_section.collapsed = False
        
        preview = self.query_one("#tileset-preview", TilesetPreview)
        preview.tileset = tileset
        
    def hide_drawing_section(self) -> None:
        """Hide the drawing section."""
        drawing_section = self.query_one("#drawing-section", Collapsible)
        drawing_section.collapsed = True
        
    def update_selected_tool(self, tool: str) -> None:
        """Update the selected tool in the tool selector."""
        selector = self.query_one("#tool-selector", ToolSelector)
        selector.selected_tool = tool
