"""Animated sidebar with collapsible sections."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Collapsible, Label, ListView

from .project_tree import ProjectTree

if TYPE_CHECKING:
    from ..core.state import AppState


class Sidebar(Widget):
    """Animated sidebar with collapsible sections for Project and Modules.
    
    The sidebar slides in from the left and contains:
    - Project file browser
    - Module-specific sections (dynamically added)
    - Tool installers list (when installer module active)
    """

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
        
        #module-sections {
            height: auto;
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
                    # ProjectTree will be added dynamically when project is opened
            
            # Container for module-specific sections
            yield Vertical(id="module-sections")
    
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
        else:
            no_project_label.display = True
            no_project_label.update("[dim]No project open[/dim]")
    
    def add_module_section(
        self, 
        section_id: str, 
        title: str, 
        widgets: list[Widget],
        collapsed: bool = True
    ) -> None:
        """Add a module-specific section to the sidebar.
        
        Args:
            section_id: Unique identifier for this section
            title: Display title with icon (e.g., "✏️ Drawing")
            widgets: Widgets to include in the section
            collapsed: Whether section starts collapsed
        """
        module_sections = self.query_one("#module-sections", Vertical)
        
        # Remove existing section with same ID if present
        for existing in self.query(f"#{section_id}"):
            existing.remove()
        
        # Create new collapsible section
        with module_sections.batch():
            collapsible = Collapsible(title=title, collapsed=collapsed, id=section_id)
            module_sections.mount(collapsible)
            
            content = Vertical(id=f"{section_id}-content")
            collapsible.mount(content)
            
            for widget in widgets:
                content.mount(widget)
    
    def remove_module_section(self, section_id: str) -> None:
        """Remove a module-specific section.
        
        Args:
            section_id: ID of the section to remove
        """
        for section in self.query(f"#{section_id}"):
            section.remove()
    
    def show_section(self, section_id: str) -> None:
        """Expand a specific section.
        
        Args:
            section_id: ID of the section to expand
        """
        try:
            section = self.query_one(f"#{section_id}", Collapsible)
            section.collapsed = False
        except Exception:
            pass
    
    def hide_section(self, section_id: str) -> None:
        """Collapse a specific section.
        
        Args:
            section_id: ID of the section to collapse
        """
        try:
            section = self.query_one(f"#{section_id}", Collapsible)
            section.collapsed = True
        except Exception:
            pass
