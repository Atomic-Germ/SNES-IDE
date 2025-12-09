"""Core module for SNES-IDE.

Provides shared state, events, module loading, and base classes.
"""

from .state import AppState
from .events import (
    FileSelected,
    ToolChanged,
    ColorChanged,
    TileNavigated,
    ModuleActivated,
)
from .module_loader import discover_modules, ModuleInfo
from .base_module import Module

__all__ = [
    "AppState",
    "FileSelected",
    "ToolChanged",
    "ColorChanged",
    "TileNavigated",
    "ModuleActivated",
    "discover_modules",
    "ModuleInfo",
    "Module",
]
