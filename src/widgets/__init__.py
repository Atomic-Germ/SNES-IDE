"""Shared widgets for SNES-IDE.

These widgets are used across multiple modules.
"""

from .sidebar import Sidebar
from .project_tree import ProjectTree

__all__ = [
    "Sidebar",
    "ProjectTree",
]
