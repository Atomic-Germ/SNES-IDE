"""
Build System Panel for SNES-IDE TUI

Provides interactive build system interface:
  • Load/manage project configurations
  • Execute builds with visual feedback
  • View build status and errors
  • Track incremental build progress
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import (
    Static,
    Button,
    Label,
    Select,
    Input,
)
from textual.reactive import reactive
import json

from ..logic.project_builder import ProjectBuilder, BuildConfig, SDK, ROMType
from ..screens.project_config import ProjectConfigManager, ProjectConfig


class BuildStatusDisplay(Static):
    """Display current build status and progress"""
    
    status = reactive("Ready")
    progress = reactive("")
    
    def render(self) -> str:
        """Render build status"""
        output = f"Status: {self.status}\n"
        if self.progress:
            output += f"\n{self.progress}"
        return output


class BuildOutputPanel(Static):
    """Display build output and logs"""
    
    DEFAULT_CSS = """
    BuildOutputPanel {
        border: solid $primary;
        height: 12;
        width: 100%;
    }
    
    BuildOutputPanel > Static {
        width: 100%;
        height: 100%;
        overflow-y: auto;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.output_lines = []
    
    def add_output(self, line: str) -> None:
        """Add a line to build output"""
        self.output_lines.append(line)
        # Keep last 100 lines
        if len(self.output_lines) > 100:
            self.output_lines = self.output_lines[-100:]
        self.update_display()
    
    def clear(self) -> None:
        """Clear build output"""
        self.output_lines = []
        self.update_display()
    
    def update_display(self) -> None:
        """Update the displayed output"""
        output = "\n".join(self.output_lines)
        if self.children:
            self.children[0].update(output)
        else:
            self.mount(Static(output))


class BuildPanel(Static):
    """
    Main build system panel for SNES-IDE.
    
    Features:
      • Project configuration loading
      • Build execution with progress
      • Build output display
      • Incremental build status
    """
    
    DEFAULT_CSS = """
    BuildPanel {
        width: 100%;
        height: 100%;
        border: solid $accent;
        padding: 1;
    }
    
    BuildPanel > Vertical {
        width: 100%;
        height: 100%;
    }
    
    #build-controls {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    #build-controls Button {
        margin-right: 1;
    }
    
    #project-mgmt {
        height: auto;
        border: solid $success;
        padding: 1;
        margin-bottom: 1;
    }
    
    #project-mgmt Button {
        margin-right: 1;
    }
    
    #config-controls {
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    #build-status {
        height: 3;
        border: solid $primary;
        margin-top: 1;
    }
    
    #build-output {
        height: 1fr;
        margin-top: 1;
    }
    
    .config-row {
        height: auto;
        border: solid $primary;
        margin-bottom: 1;
        padding: 1;
    }
    
    .config-row Label {
        width: 20;
    }
    """
    
    def __init__(self):
        super().__init__(id="build-panel")
        self.project_config: ProjectConfig | None = None
        self.builder: ProjectBuilder | None = None
        self.current_project_path: Path | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the build panel UI"""
        with Vertical():
            # Header
            yield Label("🔨 Build System")
            
            # Project management buttons
            with Container(id="project-mgmt"):
                yield Label("Project Management:")
                with Horizontal():
                    yield Button("New Project", id="new-project-btn", variant="success")
                    yield Button("Load Project", id="load-project-btn", variant="primary")
            
            # Configuration loading
            with Container(id="config-controls"):
                yield Label("Project Configuration:")
                with Horizontal():
                    yield Input(
                        id="project-path",
                        placeholder="snes-project.yaml path",
                    )
                    yield Button("Load Config", id="load-config-btn", variant="primary")
            
            # Project info display
            with Container(id="config-row", classes="config-row"):
                yield Label("Project: (none loaded)")
                yield Label("SDK: (none)")
                yield Label("ROM Type: (none)")
            
            # Build controls
            with Container(id="build-controls"):
                yield Label("Build Options:")
                with Horizontal():
                    yield Button("Build", id="build-btn", variant="primary")
                    yield Button("Clean Build", id="clean-build-btn", variant="warning")
                    yield Button("Rebuild All", id="rebuild-all-btn", variant="warning")
            
            # Build status
            yield BuildStatusDisplay(id="build-status")
            
            # Build output
            yield BuildOutputPanel(id="build-output")
    
    def on_mount(self) -> None:
        """Initialize build panel"""
        self.output_panel = self.query_one(BuildOutputPanel)
        self.status_display = self.query_one(BuildStatusDisplay)
        self.add_output("Build system ready.\nLoad a snes-project.yaml to begin.")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "new-project-btn":
            self.new_project()
        elif event.button.id == "load-project-btn":
            self.load_project()
        elif event.button.id == "load-config-btn":
            self.load_configuration()
        elif event.button.id == "build-btn":
            self.execute_build(clean=False)
        elif event.button.id == "clean-build-btn":
            self.execute_build(clean=True)
        elif event.button.id == "rebuild-all-btn":
            self.execute_build(clean=True)
    
    def load_configuration(self) -> None:
        """Load project configuration"""
        try:
            # Get path from input
            path_input = self.query_one("#project-path", Input)
            config_path = Path(path_input.value)
            
            if not config_path.exists():
                # Try to find it in current directory
                config_path = ProjectConfigManager.find_project_file()
                if not config_path:
                    self.add_output("❌ Error: No snes-project.yaml found")
                    self.status_display.status = "Failed"
                    return
            
            # Load configuration
            self.add_output(f"📖 Loading {config_path}...")
            self.project_config = ProjectConfigManager.load(config_path)
            self.current_project_path = config_path.parent
            
            # Create builder
            build_config = self.project_config.to_build_config()
            self.builder = ProjectBuilder(build_config)
            
            # Update UI
            self.add_output(f"✅ Loaded: {self.project_config.project_name}")
            self.add_output(f"   SDK: {self.project_config.sdk.value}")
            self.add_output(f"   ROM Type: {self.project_config.rom_type.name}")
            self.add_output(f"   Assets: {len(self.project_config.assets)}")
            self.add_output(f"   Compilation Targets: {len(self.project_config.compilation_targets)}")
            
            self.status_display.status = "Ready to build"
            
            # Update config display
            try:
                config_display = self.query_one("#config-row")
                # Update labels in config display
                labels = config_display.query(Label)
                if len(labels) >= 3:
                    labels[0].update(f"Project: {self.project_config.project_name}")
                    labels[1].update(f"SDK: {self.project_config.sdk.value}")
                    labels[2].update(f"ROM Type: {self.project_config.rom_type.name}")
            except:
                pass
            
        except Exception as e:
            self.add_output(f"❌ Error loading config: {e}")
            self.status_display.status = "Failed"
    
    def execute_build(self, clean: bool = False) -> None:
        """Execute the build"""
        if not self.builder:
            self.add_output("❌ Error: No project loaded. Load a configuration first.")
            self.status_display.status = "Failed"
            return
        
        try:
            self.add_output("")
            if clean:
                self.add_output("🗑️  Cleaning build directory...")
            
            self.add_output("Building...")
            self.status_display.status = "Building..."
            
            # Run build (output is to console/file, not captured)
            # For TUI, we'll show a simplified status
            success = self.builder.build(clean=clean)
            
            if success:
                self.add_output("✅ Build successful!")
                self.add_output(f"📀 ROM: {self.builder.config.output_rom}")
                self.status_display.status = "Build complete ✓"
            else:
                self.add_output("❌ Build failed!")
                self.status_display.status = "Build failed"
        
        except Exception as e:
            self.add_output(f"❌ Build error: {e}")
            self.status_display.status = "Error"
    
    def new_project(self) -> None:
        """Open new project dialog"""
        from ..screens.project_dialogs import NewProjectDialog
        
        def handle_new_project(project_path: Path | None) -> None:
            if project_path:
                self.add_output(f"✅ Project created: {project_path}")
                self.add_output(f"Project: {project_path.name}")
                # Auto-load the config
                config_file = project_path / "snes-project.yaml"
                if config_file.exists():
                    self.current_project_path = project_path
                    path_input = self.query_one("#project-path", Input)
                    path_input.value = str(config_file)
                    self.load_configuration()
        
        dialog = NewProjectDialog()
        self.app.push_screen(dialog, handle_new_project)
    
    def load_project(self) -> None:
        """Open load project dialog"""
        from ..screens.project_dialogs import LoadProjectDialog
        
        def handle_load_project(config_path: Path | None) -> None:
            if config_path:
                self.add_output(f"✅ Loading project: {config_path.parent.name}")
                self.current_project_path = config_path.parent
                path_input = self.query_one("#project-path", Input)
                path_input.value = str(config_path)
                self.load_configuration()
        
        dialog = LoadProjectDialog()
        self.app.push_screen(dialog, handle_load_project)
    
    def add_output(self, line: str) -> None:
        """Add output to the build panel"""
        try:
            self.output_panel.add_output(line)
        except:
            pass


# Shorthand for easy access
def get_build_panel(widget) -> BuildPanel | None:
    """Get build panel from any widget"""
    try:
        return widget.app.query_one(BuildPanel)
    except:
        return None
