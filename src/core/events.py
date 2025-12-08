"""Custom Textual messages for cross-module communication.

These messages allow modules to communicate without tight coupling.
Post a message and any parent widget can handle it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from textual.message import Message


class FileSelected(Message):
    """Message sent when a file is selected from any source.
    
    Attributes:
        path: Path to the selected file
        source: Origin of the selection (e.g., "project_tree", "recent_files")
    """
    
    def __init__(self, path: Path, source: str = "unknown") -> None:
        super().__init__()
        self.path = path
        self.source = source


class ToolChanged(Message):
    """Message sent when the active drawing tool changes.
    
    Attributes:
        tool: Tool identifier ("pencil", "fill", "line", etc.)
    """
    
    def __init__(self, tool: str) -> None:
        super().__init__()
        self.tool = tool


class ColorChanged(Message):
    """Message sent when the selected color changes.
    
    Attributes:
        color_index: Palette index of the selected color
        source: Origin ("palette_bar", "eyedropper", etc.)
    """
    
    def __init__(self, color_index: int, source: str = "unknown") -> None:
        super().__init__()
        self.color_index = color_index
        self.source = source


class TileNavigated(Message):
    """Message sent when navigating to a different tile.
    
    Attributes:
        tile_index: Index of the newly selected tile
    """
    
    def __init__(self, tile_index: int) -> None:
        super().__init__()
        self.tile_index = tile_index


class ModuleActivated(Message):
    """Message sent when a module becomes active.
    
    Attributes:
        module_name: Name of the activated module
        previous_module: Name of the previously active module (if any)
    """
    
    def __init__(self, module_name: str, previous_module: str | None = None) -> None:
        super().__init__()
        self.module_name = module_name
        self.previous_module = previous_module


class InstallationStarted(Message):
    """Message sent when a tool installation begins.
    
    Attributes:
        tool_name: Name of the tool being installed
    """
    
    def __init__(self, tool_name: str) -> None:
        super().__init__()
        self.tool_name = tool_name


class InstallationComplete(Message):
    """Message sent when a tool installation completes.
    
    Attributes:
        tool_name: Name of the installed tool
        success: Whether installation succeeded
    """
    
    def __init__(self, tool_name: str, success: bool) -> None:
        super().__init__()
        self.tool_name = tool_name
        self.success = success


class ProjectOpened(Message):
    """Message sent when a project directory is opened.
    
    Attributes:
        path: Path to the project directory
    """
    
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


class TilesetLoaded(Message):
    """Message sent when a tileset is loaded.
    
    Attributes:
        path: Path to the tileset file
        tile_count: Number of tiles in the tileset
    """
    
    def __init__(self, path: Path, tile_count: int) -> None:
        super().__init__()
        self.path = path
        self.tile_count = tile_count
