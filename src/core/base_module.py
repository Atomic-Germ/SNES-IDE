"""Base class for SNES-IDE modules.

Each module is a self-contained feature area (graphics editor, installers, etc.)
that can be dropped into the modules/ directory and automatically discovered.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 fallback

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget

if TYPE_CHECKING:
    from .state import AppState


class Module(Screen, ABC):
    """Base class for all SNES-IDE modules.
    
    A module is a Screen that provides a complete feature area.
    Modules are discovered automatically from the modules/ directory
    if they contain a module.toml configuration file.
    
    Example module.toml:
        [module]
        name = "Graphics Editor"
        icon = "🎨"
        order = 1
        key = "g"
        description = "Edit SNES tiles and sprites"
        
        [sidebar]
        enabled = true
        sections = ["drawing_tools", "tileset_preview"]
        
        [file_associations]
        extensions = [".png", ".bmp", ".pic"]
    
    Subclasses must implement:
        - compose(): Return the module's widget tree
        - get_config_path(): Return path to module.toml
    
    Optionally override:
        - sidebar_widgets(): Return widgets to show in sidebar
        - on_activate(): Called when module becomes active
        - on_deactivate(): Called when module becomes inactive
        - handles_file(): Return True if module can open a file type
    """
    
    # Module configuration (loaded from module.toml)
    _config: Dict[str, Any] | None = None
    
    @classmethod
    def get_config_path(cls) -> Path:
        """Return the path to this module's module.toml file.
        
        Override in subclasses to point to the correct location.
        Default implementation looks in the same directory as the class file.
        """
        import inspect
        module_file = inspect.getfile(cls)
        return Path(module_file).parent / "module.toml"
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Load and return the module configuration.
        
        Configuration is cached after first load.
        """
        if cls._config is not None:
            return cls._config
        
        config_path = cls.get_config_path()
        if config_path.exists():
            with open(config_path, "rb") as f:
                cls._config = tomllib.load(f)
        else:
            # Default config if no module.toml exists
            cls._config = {
                "module": {
                    "name": cls.__name__,
                    "icon": "📦",
                    "order": 99,
                    "description": "",
                }
            }
        
        return cls._config
    
    @classmethod
    def get_module_name(cls) -> str:
        """Return the display name for this module."""
        config = cls.get_config()
        return config.get("module", {}).get("name", cls.__name__)
    
    @classmethod
    def get_module_icon(cls) -> str:
        """Return the icon for this module."""
        config = cls.get_config()
        return config.get("module", {}).get("icon", "📦")
    
    @classmethod
    def get_module_order(cls) -> int:
        """Return the sort order for this module in menus."""
        config = cls.get_config()
        return config.get("module", {}).get("order", 99)
    
    @classmethod
    def get_module_key(cls) -> str | None:
        """Return the keyboard shortcut for this module."""
        config = cls.get_config()
        return config.get("module", {}).get("key")
    
    @classmethod
    def get_file_extensions(cls) -> List[str]:
        """Return file extensions this module handles."""
        config = cls.get_config()
        return config.get("file_associations", {}).get("extensions", [])
    
    @property
    def state(self) -> "AppState":
        """Access the shared application state."""
        return self.app.state
    
    @abstractmethod
    def compose(self) -> ComposeResult:
        """Define the widget tree for this module.
        
        Must be implemented by subclasses.
        """
        raise NotImplementedError
    
    def sidebar_widgets(self) -> List[Widget]:
        """Return widgets to display in the sidebar when this module is active.
        
        Override to provide module-specific sidebar content.
        Default returns empty list.
        """
        return []
    
    def on_activate(self) -> None:
        """Called when this module becomes the active view.
        
        Override to perform setup when module gains focus.
        """
        pass
    
    def on_deactivate(self) -> None:
        """Called when this module loses focus to another module.
        
        Override to perform cleanup or save state.
        """
        pass
    
    def handles_file(self, path: Path) -> bool:
        """Check if this module can handle a specific file.
        
        Default implementation checks against file_associations in config.
        Override for more complex logic.
        
        Args:
            path: Path to the file to check
            
        Returns:
            True if this module can open the file
        """
        extensions = self.get_file_extensions()
        if not extensions:
            return False
        return path.suffix.lower() in extensions
    
    def open_file(self, path: Path) -> bool:
        """Open a file in this module.
        
        Override to implement file opening logic.
        
        Args:
            path: Path to the file to open
            
        Returns:
            True if file was opened successfully
        """
        return False
