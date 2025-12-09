"""Central application state for cross-module communication.

Uses Textual's reactive system to provide observable state that
modules can subscribe to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

from textual.reactive import reactive

if TYPE_CHECKING:
    from ..modules.graphics.models import SNESTileset


class AppState:
    """Central reactive state container for the application.
    
    This class holds shared state that multiple modules need access to.
    Changes to reactive properties will trigger updates in subscribers.
    
    Usage:
        # In app.py
        self.state = AppState()
        
        # In any module/widget
        state = self.app.state
        current_file = state.current_file
    """
    
    # Current view: "installers", "browser", "graphics", or module name
    current_view: str = "installers"
    
    # Currently selected file path
    current_file: Path | None = None
    
    # Project root directory
    project_path: Path | None = None
    
    # Graphics editor state
    current_color_index: int = 1  # 0 is usually transparent
    current_tool: str = "pencil"
    current_tile_index: int = 0
    zoom_level: int = 4
    show_grid: bool = True
    edit_mode: bool = True  # True = full-block editing, False = half-block display
    
    # Currently loaded tileset (shared between modules)
    _tileset: "SNESTileset | None" = None
    
    # Sidebar visibility
    show_sidebar: bool = True
    
    # Installed tools cache (tool_name -> tool_data dict)
    tools_cache: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self) -> None:
        """Initialize the application state."""
        self.tools_cache = {}
        self._tileset = None
    
    @property
    def tileset(self) -> "SNESTileset | None":
        """Get the currently loaded tileset."""
        return self._tileset
    
    @tileset.setter
    def tileset(self, value: "SNESTileset | None") -> None:
        """Set the current tileset."""
        self._tileset = value
    
    def reset_graphics_state(self) -> None:
        """Reset graphics editor state to defaults."""
        self.current_color_index = 1
        self.current_tool = "pencil"
        self.current_tile_index = 0
        self.zoom_level = 4
        self.show_grid = True
        self.edit_mode = True
        self._tileset = None
