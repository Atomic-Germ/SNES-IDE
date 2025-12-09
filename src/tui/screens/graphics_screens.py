from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from ..logic.graphics import HAS_PIL, SNESTileset


class NewTilesetScreen(ModalScreen):
    """Modal dialog for creating a new tileset with SNES-appropriate options."""
    
    DEFAULT_CSS = """
    NewTilesetScreen {
        align: center middle;
    }
    
    #new-tileset-dialog {
        width: 65;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #new-tileset-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        background: $accent;
        margin-bottom: 1;
    }
    
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    
    .form-row Label {
        width: 18;
        text-align: right;
        margin-right: 1;
    }
    
    .form-row Input {
        width: 1fr;
    }
    
    .form-row Select {
        width: 1fr;
    }
    
    #form-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    #form-buttons Button {
        margin: 0 2;
    }
    
    #bpp-help {
        color: $text-muted;
        text-align: center;
        padding: 0 1;
        margin-top: 1;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, default_dir: Path | None = None):
        super().__init__()
        self.default_dir = default_dir or Path.home()
    
    def compose(self) -> ComposeResult:
        with Vertical(id="new-tileset-dialog"):
            yield Label("📐 New Tileset", id="new-tileset-title")
            
            with Horizontal(classes="form-row"):
                yield Label("Filename:")
                yield Input(value="tileset.png", id="filename-input")
            
            with Horizontal(classes="form-row"):
                yield Label("Width (tiles):")
                yield Input(value="16", type="integer", id="width-input")
            
            with Horizontal(classes="form-row"):
                yield Label("Height (tiles):")
                yield Input(value="16", type="integer", id="height-input")
            
            with Horizontal(classes="form-row"):
                yield Label("Tile Size:")
                yield Select(
                    [("8×8 (standard)", "8"), ("16×16 (large)", "16")],
                    value="8",
                    id="tile-size-select"
                )
            
            with Horizontal(classes="form-row"):
                yield Label("Colors (BPP):")
                yield Select(
                    [
                        ("4 colors (2bpp) - Mode 0 BGs", "2"),
                        ("16 colors (4bpp) - Mode 1 BGs, sprites", "4"),
                        ("256 colors (8bpp) - Mode 3/7", "8"),
                    ],
                    value="4",
                    id="bpp-select"
                )
            
            yield Label(
                "[dim]Mode 0: 4×2bpp BGs | Mode 1: 4bpp+4bpp+2bpp | Mode 3: 8bpp[/dim]",
                id="bpp-help"
            )
            
            with Horizontal(id="form-buttons"):
                yield Button("Create", id="create-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create-btn":
            self._create_tileset()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
    
    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(None)
    
    def _create_tileset(self) -> None:
        """Validate inputs and create the tileset."""
        try:
            filename_input = self.query_one("#filename-input", Input)
            width_input = self.query_one("#width-input", Input)
            height_input = self.query_one("#height-input", Input)
            tile_size_select = self.query_one("#tile-size-select", Select)
            bpp_select = self.query_one("#bpp-select", Select)
            
            # Get values
            filename = filename_input.value.strip() or "tileset.png"
            if not filename.endswith(".png"):
                filename += ".png"
            
            width_tiles = int(width_input.value or "16")
            height_tiles = int(height_input.value or "16")
            tile_size = int(tile_size_select.value or "8")
            bpp = int(bpp_select.value or "4")
            
            # Validate ranges
            if width_tiles < 1 or width_tiles > 64:
                self.notify("Width must be 1-64 tiles", severity="error")
                return
            if height_tiles < 1 or height_tiles > 64:
                self.notify("Height must be 1-64 tiles", severity="error")
                return
            if tile_size not in (8, 16):
                self.notify("Tile size must be 8 or 16", severity="error")
                return
            if bpp not in (2, 4, 8):
                self.notify("BPP must be 2, 4, or 8", severity="error")
                return
            
            # Create the tileset
            tileset = SNESTileset.create_new(
                width_tiles=width_tiles,
                height_tiles=height_tiles,
                tile_width=tile_size,
                tile_height=tile_size,
                bpp=bpp
            )
            
            # Determine file path
            file_path = self.default_dir / filename
            
            # Return the config as a dict for the caller
            result = {
                "tileset": tileset,
                "file_path": file_path,
                "width_tiles": width_tiles,
                "height_tiles": height_tiles,
                "tile_size": tile_size,
                "bpp": bpp
            }
            self.dismiss(result)
            
        except ValueError as e:
            self.notify(f"Invalid input: {e}", severity="error")


class SliceImageScreen(ModalScreen):
    """Modal dialog for slicing an existing image into a tileset."""
    
    DEFAULT_CSS = """
    SliceImageScreen {
        align: center middle;
    }
    
    #slice-dialog {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #slice-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        background: $accent;
        margin-bottom: 1;
    }
    
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    
    .form-row Label {
        width: 18;
        text-align: right;
        margin-right: 1;
    }
    
    .form-row Input, .form-row Select {
        width: 1fr;
    }
    
    #form-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    #form-buttons Button {
        margin: 0 2;
    }
    
    #image-info {
        color: $text-muted;
        text-align: center;
        padding: 0 1;
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, image_path: Path):
        super().__init__()
        self.image_path = image_path
        self.image_width = 0
        self.image_height = 0
        
        # Try to get image dimensions
        if HAS_PIL:
            try:
                from PIL import Image
                img = Image.open(image_path)
                self.image_width, self.image_height = img.size
            except Exception:
                pass
    
    def compose(self) -> ComposeResult:
        with Vertical(id="slice-dialog"):
            yield Label("✂️ Slice Image into Tileset", id="slice-title")
            
            yield Label(
                f"[dim]{self.image_path.name} ({self.image_width}×{self.image_height}px)[/dim]",
                id="image-info"
            )
            
            with Horizontal(classes="form-row"):
                yield Label("Tile Size:")
                yield Select(
                    [("8×8 (standard)", "8"), ("16×16 (large)", "16")],
                    value="8",
                    id="tile-size-select"
                )
            
            with Horizontal(classes="form-row"):
                yield Label("Colors (BPP):")
                yield Select(
                    [
                        ("4 colors (2bpp) - Mode 0 BGs", "2"),
                        ("16 colors (4bpp) - Mode 1 BGs, sprites", "4"),
                        ("256 colors (8bpp) - Mode 3/7", "8"),
                    ],
                    value="4",
                    id="bpp-select"
                )
            
            with Horizontal(id="form-buttons"):
                yield Button("Slice", id="slice-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "slice-btn":
            self._slice_image()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)
    
    def _slice_image(self) -> None:
        """Slice the image into a tileset."""
        try:
            tile_size_select = self.query_one("#tile-size-select", Select)
            bpp_select = self.query_one("#bpp-select", Select)
            
            tile_size = int(tile_size_select.value or "8")
            bpp = int(bpp_select.value or "4")
            
            # Create tileset with specified parameters
            tileset = SNESTileset(tile_width=tile_size, tile_height=tile_size, bpp=bpp)
            
            if tileset.load_from_path(self.image_path):
                tiles_x = self.image_width // tile_size
                tiles_y = self.image_height // tile_size
                
                result = {
                    "tileset": tileset,
                    "file_path": self.image_path,
                    "tile_size": tile_size,
                    "bpp": bpp,
                    "tiles_x": tiles_x,
                    "tiles_y": tiles_y
                }
                self.dismiss(result)
            else:
                self.notify("Failed to load image", severity="error")
                
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
