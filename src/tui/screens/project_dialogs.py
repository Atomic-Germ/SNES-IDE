"""
New Project Creation Dialog

Interactive dialog for creating a new SNES project with templates.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Static,
    Button,
    Input,
    Label,
    Select,
    RadioButton,
    RadioSet,
    Checkbox,
    Rule,
)
from textual.screen import ModalScreen

from .sdk_templates import SDK, ROMType, create_project_structure, create_gitignore, create_readme
from .project_config import ProjectConfigManager, ProjectConfig


class NewProjectDialog(ModalScreen):
    """Modal dialog for creating a new SNES project"""
    
    TITLE = "Create New SNES Project"
    
    CSS = """
    NewProjectDialog {
        align: center middle;
    }
    
    #project-dialog {
        width: 80;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    #project-dialog Static {
        width: 100%;
    }
    
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    
    .form-row Label {
        width: 20;
        text-align: right;
        margin-right: 1;
    }
    
    .form-row Input {
        width: 1fr;
    }
    
    .form-group {
        margin-bottom: 2;
        border: solid $accent;
        padding: 1;
    }
    
    .form-group Label {
        width: 100%;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .buttons {
        height: auto;
        text-align: center;
        margin-top: 2;
    }
    
    .buttons Button {
        margin-right: 1;
    }
    
    Select {
        width: 1fr;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.project_data = {
            "name": "",
            "location": str(Path.home()),
            "sdk": SDK.PVSNESLIB.value,
            "rom_type": ROMType.LOROM.value,
            "git": True,
            "readme": True,
        }
    
    def compose(self) -> ComposeResult:
        """Compose the dialog"""
        with Container(id="project-dialog"):
            yield Label("Create New SNES Project")
            yield Rule()
            
            # Project name
            with Horizontal(classes="form-row"):
                yield Label("Project Name:", classes="label")
                yield Input(
                    id="project-name",
                    placeholder="MyGame",
                    classes="input",
                )
            
            # Project location
            with Horizontal(classes="form-row"):
                yield Label("Location:", classes="label")
                yield Input(
                    id="project-location",
                    value=str(Path.home()),
                    classes="input",
                )
            
            # SDK Selection
            with Container(classes="form-group"):
                yield Label("SDK")
                yield Select(
                    options=[
                        (sdk.value.replace("snes", " SNES").title(), sdk.value)
                        for sdk in SDK
                    ],
                    value=SDK.PVSNESLIB.value,
                    id="sdk-select",
                )
            
            # ROM Type Selection
            with Container(classes="form-group"):
                yield Label("ROM Type")
                with RadioSet(id="rom-type-set"):
                    for rom_type in ROMType:
                        yield RadioButton(
                            rom_type.value.upper(),
                            id=f"rom-{rom_type.value}",
                            value=(rom_type.value == ROMType.LOROM.value),
                        )
            
            # Options
            with Container(classes="form-group"):
                yield Label("Options")
                yield Checkbox(
                    "Initialize Git repository",
                    id="git-init",
                    value=True,
                )
                yield Checkbox(
                    "Create README.md",
                    id="create-readme",
                    value=True,
                )
            
            yield Rule()
            
            # Buttons
            with Horizontal(classes="buttons"):
                yield Button("Create", id="create-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "create-btn":
            self.create_project()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle SDK selection"""
        if event.control.id == "sdk-select":
            self.project_data["sdk"] = event.value
    
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle ROM type selection"""
        if event.control.id == "rom-type-set":
            # Get the selected radio button
            selected = event.pressed_button
            if selected:
                rom_value = selected.id.replace("rom-", "")
                self.project_data["rom_type"] = rom_value
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes"""
        if event.control.id == "git-init":
            self.project_data["git"] = event.value
        elif event.control.id == "create-readme":
            self.project_data["readme"] = event.value
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes"""
        if event.control.id == "project-name":
            self.project_data["name"] = event.value
        elif event.control.id == "project-location":
            self.project_data["location"] = event.value
    
    def create_project(self) -> None:
        """Create the project with the configured settings"""
        # Get values from inputs
        name_input = self.query_one("#project-name", Input)
        location_input = self.query_one("#project-location", Input)
        
        project_name = name_input.value.strip()
        location = Path(location_input.value).expanduser()
        
        # Validate
        if not project_name:
            # In production, show error message
            return
        
        try:
            # Create project directory
            project_dir = location / project_name
            if project_dir.exists():
                # Project already exists - show error
                return
            
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Get SDK
            sdk = SDK(self.project_data["sdk"])
            
            # Create project structure
            create_project_structure(project_dir, sdk)
            
            # Create .gitignore if requested
            if self.project_data["git"]:
                create_gitignore(project_dir)
            
            # Create README if requested
            if self.project_data["readme"]:
                create_readme(project_dir, project_name, sdk)
            
            # Create snes-project.yaml
            rom_type = self.project_data["rom_type"]
            config = ProjectConfig(
                project_name=project_name,
                version="0.1.0",
                sdk=sdk,
                rom_type=rom_type,
                output_rom=f"dist/{project_name.lower()}.sfc",
                source_dir="src",
                assets_dir="assets",
                build_dir="build",
                output_dir="dist",
            )
            
            config_path = project_dir / "snes-project.yaml"
            ProjectConfigManager.save(config, config_path)
            
            # Return the project path
            self.dismiss(project_dir)
        
        except Exception as e:
            # In production, show error dialog
            self.dismiss(None)


class LoadProjectDialog(ModalScreen):
    """Modal dialog for loading an existing project"""
    
    TITLE = "Load SNES Project"
    
    CSS = """
    LoadProjectDialog {
        align: center middle;
    }
    
    #load-dialog {
        width: 80;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    #load-dialog Static {
        width: 100%;
    }
    
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    
    .form-row Label {
        width: 20;
        text-align: right;
        margin-right: 1;
    }
    
    .form-row Input {
        width: 1fr;
    }
    
    .buttons {
        height: auto;
        text-align: center;
        margin-top: 2;
    }
    
    .buttons Button {
        margin-right: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose the dialog"""
        with Container(id="load-dialog"):
            yield Label("Load SNES Project")
            yield Rule()
            
            yield Label("Browse for snes-project.yaml:")
            
            with Horizontal(classes="form-row"):
                yield Label("Project File:", classes="label")
                yield Input(
                    id="project-file",
                    placeholder="/path/to/snes-project.yaml",
                    classes="input",
                )
            
            yield Label("Or browse for a directory containing snes-project.yaml:")
            
            with Horizontal(classes="form-row"):
                yield Label("Directory:", classes="label")
                yield Input(
                    id="project-dir",
                    value=str(Path.home()),
                    placeholder="/path/to/project",
                    classes="input",
                )
            
            yield Rule()
            
            with Horizontal(classes="buttons"):
                yield Button("Load File", id="load-file-btn", variant="primary")
                yield Button("Load Directory", id="load-dir-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "load-file-btn":
            self.load_file()
        elif event.button.id == "load-dir-btn":
            self.load_directory()
    
    def load_file(self) -> None:
        """Load project from file path"""
        file_input = self.query_one("#project-file", Input)
        file_path = Path(file_input.value).expanduser()
        
        if file_path.exists() and file_path.suffix == ".yaml":
            self.dismiss(file_path)
        else:
            # Show error
            pass
    
    def load_directory(self) -> None:
        """Load project from directory"""
        dir_input = self.query_one("#project-dir", Input)
        dir_path = Path(dir_input.value).expanduser()
        
        # Look for snes-project.yaml
        config_file = dir_path / "snes-project.yaml"
        if config_file.exists():
            self.dismiss(config_file)
        else:
            # Look for snes-project.yml
            config_file = dir_path / "snes-project.yml"
            if config_file.exists():
                self.dismiss(config_file)
            else:
                # Look for snes-project.json
                config_file = dir_path / "snes-project.json"
                if config_file.exists():
                    self.dismiss(config_file)
                else:
                    # Show error
                    pass
