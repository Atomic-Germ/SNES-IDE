"""Module discovery and loading system.

Scans the modules/ directory for valid modules and registers them.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Type, TYPE_CHECKING

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 fallback

if TYPE_CHECKING:
    from .base_module import Module


@dataclass
class ModuleInfo:
    """Information about a discovered module.
    
    Attributes:
        name: Display name of the module
        icon: Emoji or character icon
        order: Sort order in menus
        key: Keyboard shortcut (if any)
        description: Human-readable description
        extensions: File extensions this module handles
        module_class: The actual Module subclass
        path: Path to the module directory
    """
    name: str
    icon: str
    order: int
    key: str | None
    description: str
    extensions: List[str]
    module_class: Type["Module"]
    path: Path
    config: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def id(self) -> str:
        """Return a unique identifier for this module."""
        return self.path.name


def discover_modules(modules_dir: Path | None = None) -> List[ModuleInfo]:
    """Discover and load all modules from the modules directory.
    
    Modules are discovered by looking for directories containing:
    1. A module.toml configuration file
    2. A screen.py file with a Module subclass
    
    Args:
        modules_dir: Path to the modules directory. 
                     Defaults to src/modules/ relative to this file.
    
    Returns:
        List of ModuleInfo objects, sorted by order.
    """
    if modules_dir is None:
        modules_dir = Path(__file__).parent.parent / "modules"
    
    if not modules_dir.exists():
        return []
    
    discovered: List[ModuleInfo] = []
    
    for module_path in modules_dir.iterdir():
        if not module_path.is_dir():
            continue
        
        config_file = module_path / "module.toml"
        screen_file = module_path / "screen.py"
        
        # Both files must exist
        if not config_file.exists() or not screen_file.exists():
            continue
        
        try:
            # Load configuration
            with open(config_file, "rb") as f:
                config = tomllib.load(f)
            
            module_config = config.get("module", {})
            file_assoc = config.get("file_associations", {})
            
            # Import the screen module
            spec = importlib.util.spec_from_file_location(
                f"snes_ide.modules.{module_path.name}.screen",
                screen_file
            )
            if spec is None or spec.loader is None:
                continue
            
            screen_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(screen_module)
            
            # Find the Module subclass
            module_class = None
            from .base_module import Module
            
            for attr_name in dir(screen_module):
                attr = getattr(screen_module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Module) and 
                    attr is not Module):
                    module_class = attr
                    break
            
            if module_class is None:
                continue
            
            # Create ModuleInfo
            info = ModuleInfo(
                name=module_config.get("name", module_path.name),
                icon=module_config.get("icon", "📦"),
                order=module_config.get("order", 99),
                key=module_config.get("key"),
                description=module_config.get("description", ""),
                extensions=file_assoc.get("extensions", []),
                module_class=module_class,
                path=module_path,
                config=config,
            )
            
            discovered.append(info)
            
        except Exception as e:
            # Log but don't crash on module load errors
            print(f"Warning: Failed to load module {module_path.name}: {e}")
            continue
    
    # Sort by order
    discovered.sort(key=lambda m: (m.order, m.name))
    
    return discovered


def get_module_for_file(modules: List[ModuleInfo], path: Path) -> ModuleInfo | None:
    """Find the best module to handle a given file.
    
    Args:
        modules: List of available modules
        path: Path to the file
        
    Returns:
        ModuleInfo for the handling module, or None if no module can handle it.
    """
    ext = path.suffix.lower()
    
    for module in modules:
        if ext in module.extensions:
            return module
    
    return None
