from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Collapsible,
    DirectoryTree,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
)

from .logic.commands import ToolCommandProvider
from .logic.graphics import HAS_PIL
from .screens.graphics_screens import NewTilesetScreen, SliceImageScreen
from .screens.install_screens import InstallScreen, UninstallScreen, VerifyScreen
from .widgets.code_panel import CodeViewer
from .widgets.graphics_panel import PaletteBar, PixelCanvas, TileEditorPanel
from .widgets.audio_panel import AudioEditorPanel
from .widgets.rom_panel import RomAnalyzerPanel
from .widgets.profiler_panel import ProfilerPanel
from .widgets.disassembler_panel import DisassemblerPanel
from .widgets.sidebar import Sidebar, TilesetPreview, ToolSelector
from .widgets.tool_panel import ToolDetailPanel


class SNESIDEApp(App):
    """SNES-IDE - Integrated Development Environment for SNES."""

    TITLE = "SNES-IDE"
    COMMANDS = {ToolCommandProvider}
    
    DEFAULT_CSS = """
    Screen {
        layers: sidebar;
        background: $surface;
    }
    
    #main-content {
        width: 100%;
        height: 100%;
    }
    
    #content-switcher {
        width: 100%;
        height: 100%;
    }
    
    #tool-panel {
        width: 100%;
        height: 100%;
    }
    
    #code-panel {
        width: 100%;
        height: 100%;
    }
    
    #graphics-panel {
        width: 100%;
        height: 100%;
    }

    #audio-panel {
        width: 100%;
        height: 100%;
    }

    #rom-panel {
        width: 100%;
        height: 100%;
    }

    #profiler-panel {
        width: 100%;
        height: 100%;
    }

    #disassembler-panel {
        width: 100%;
        height: 100%;
    }
    
    #file-path-bar {
        dock: top;
        height: 1;
        padding: 0 1;
        background: $primary 30%;
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("s", "toggle_sidebar", "Sidebar"),
        ("f", "toggle_files", "Files"),
        ("d", "toggle_graphics_mode", "Display/Edit Mode"),
        ("g", "toggle_grid", "Grid"),
        ("i", "install", "Install"),
        ("n", "new_tileset", "New Tileset"),
        ("c", "slice_image", "Slice Image"),
        ("o", "open_project", "Open Project"),
        ("shift+p", "show_profiler", "Profiler"),
        ("shift+d", "show_disassembler", "Disassembler"),
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("escape", "show_tools", "Tools View"),
        ("+", "zoom_in", "Zoom In"),
        ("=", "zoom_in", "Zoom In"),
        ("-", "zoom_out", "Zoom Out"),
        # Graphics editor bindings
        ("p", "set_pencil_tool", "Pencil"),
        ("y", "set_eyedropper_tool", "Eyedropper"),
        ("b", "set_fill_tool", "Fill"),
        ("l", "set_line_tool", "Line"),
        ("t", "set_rect_tool", "Rectangle"),
        ("e", "set_ellipse_tool", "Ellipse"),
        ("ctrl+s", "save_graphics", "Save"),
        ("ctrl+z", "undo_graphics", "Undo"),
        ("ctrl+y", "redo_graphics", "Redo"),
    ]

    show_sidebar = reactive(False)
    current_view = reactive("tools")  # "tools", "code", or "graphics"
    current_file: reactive[Path | None] = reactive(None)
    project_path: reactive[Path | None] = reactive(None)

    # Image file extensions to route to graphics editor
    IMAGE_EXTENSIONS = {".png", ".bmp", ".gif", ".jpg", ".jpeg"}
    # Audio file extensions to route to audio editor
    AUDIO_EXTENSIONS = {".brr", ".wav", ".spc"}
    # ROM file extensions to route to ROM analyzer
    ROM_EXTENSIONS = {".sfc", ".smc"}

    def __init__(self, project_path: Path | None = None):
        super().__init__()
        self.tools_by_category: Dict[str, list] = {}
        self.all_tools_map: Dict[str, Dict[str, Any]] = {}
        self._initial_project_path = project_path
        self.load_tools_from_json()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Sidebar()
        with Container(id="main-content"):
            # Tool detail view
            with VerticalScroll(id="tool-panel"):
                yield ToolDetailPanel()
            # Code viewer
            with Vertical(id="code-panel"):
                yield Label("", id="file-path-bar")
                yield CodeViewer()
            # Graphics editor
            with Vertical(id="graphics-panel"):
                yield TileEditorPanel()
            # Audio editor
            with Vertical(id="audio-panel"):
                yield AudioEditorPanel()
            # ROM Analyzer
            with Vertical(id="rom-panel"):
                yield RomAnalyzerPanel("")
            # Profiler
            with Vertical(id="profiler-panel"):
                yield ProfilerPanel()
            # Disassembler
            with Vertical(id="disassembler-panel"):
                yield DisassemblerPanel()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the UI on mount."""
        self.populate_tool_list()
        # Start with sidebar visible
        self.show_sidebar = True
        # Set initial project if provided
        if self._initial_project_path:
            self.project_path = self._initial_project_path
        else:
            # Default to current working directory
            self.project_path = Path.cwd()
        # Show tools panel by default
        self.current_view = "tools"
    
    def watch_current_view(self, view: str) -> None:
        """Switch between tool, code, graphics, and audio views."""
        tool_panel = self.query_one("#tool-panel")
        code_panel = self.query_one("#code-panel")
        graphics_panel = self.query_one("#graphics-panel")
        audio_panel = self.query_one("#audio-panel")
        rom_panel = self.query_one("#rom-panel")
        profiler_panel = self.query_one("#profiler-panel")
        disassembler_panel = self.query_one("#disassembler-panel")
        
        # Hide all panels first
        tool_panel.display = False
        code_panel.display = False
        graphics_panel.display = False
        audio_panel.display = False
        rom_panel.display = False
        profiler_panel.display = False
        disassembler_panel.display = False
        
        if view == "tools":
            tool_panel.display = True
            self.sub_title = "Tools"
        elif view == "code":
            code_panel.display = True
            if self.current_file:
                self.sub_title = str(self.current_file.name)
        elif view == "graphics":
            graphics_panel.display = True
            if self.current_file:
                self.sub_title = f"🎨 {self.current_file.name}"
        elif view == "audio":
            audio_panel.display = True
            if self.current_file:
                self.sub_title = f"🔊 {self.current_file.name}"
        elif view == "rom":
            rom_panel.display = True
            if self.current_file:
                self.sub_title = f"🗺️ {self.current_file.name}"
        elif view == "profiler":
            profiler_panel.display = True
            self.sub_title = "⏱️ Silicon Turtleneck"
        elif view == "disassembler":
            disassembler_panel.display = True
            self.sub_title = "🔍 Disassembler"
    
    def watch_current_file(self, file_path: Path | None) -> None:
        """Update the appropriate viewer when a file is selected."""
        if not file_path:
            return

        suffix = file_path.suffix.lower()
        is_image = suffix in self.IMAGE_EXTENSIONS
        is_audio = suffix in self.AUDIO_EXTENSIONS
        is_rom = suffix in self.ROM_EXTENSIONS
        
        if is_image:
            # Route to graphics editor
            tile_editor = self.query_one(TileEditorPanel)
            tile_editor.file_path = file_path
            
            # Update sidebar drawing section with tileset
            sidebar = self.query_one(Sidebar)
            if tile_editor._tileset:
                sidebar.show_drawing_section(tile_editor._tileset)
        elif is_audio:
            # Route to audio editor
            audio_panel = self.query_one(AudioEditorPanel)
            audio_panel.file_path = file_path
            
            # Hide drawing section
            sidebar = self.query_one(Sidebar)
            sidebar.hide_drawing_section()
        elif is_rom:
            # Route to ROM analyzer
            # We need to recreate the panel or update it
            # Since RomAnalyzerPanel takes path in init, we might need to update it
            # But wait, RomAnalyzerPanel is yielded in compose with empty string.
            # We should add a file_path setter or method to update it.
            # Let's assume we can replace the widget or update it.
            # Actually, let's check RomAnalyzerPanel implementation again.
            # It has self.analyzer = SNESRomAnalyzer(file_path) in __init__.
            # We need a method to load a new file.
            
            # For now, let's just try to update it if we can, or rebuild it.
            # Better: Add a load_file method to RomAnalyzerPanel.
            
            rom_panel = self.query_one(RomAnalyzerPanel)
            # We need to implement load_file in RomAnalyzerPanel first!
            # But I can't edit it right now in this tool call.
            # I'll assume I'll add it.
            if hasattr(rom_panel, 'load_file'):
                rom_panel.load_file(str(file_path))
            else:
                # Fallback: Re-mount (hacky)
                pass
                
            sidebar = self.query_one(Sidebar)
            sidebar.hide_drawing_section()
        else:
            # Route to code viewer
            code_viewer = self.query_one(CodeViewer)
            code_viewer.file_path = file_path
            
            # Hide drawing section when not viewing graphics
            sidebar = self.query_one(Sidebar)
            sidebar.hide_drawing_section()
        
        path_bar = self.query_one("#file-path-bar", Label)
        if file_path:
            # Show relative path if within project
            if self.project_path and file_path.is_relative_to(self.project_path):
                rel_path = file_path.relative_to(self.project_path)
                path_bar.update(f"📄 {rel_path}")
            else:
                path_bar.update(f"📄 {file_path}")
            self.sub_title = file_path.name
        else:
            path_bar.update("")
    
    def watch_project_path(self, project_path: Path | None) -> None:
        """Update sidebar when project path changes."""
        sidebar = self.query_one(Sidebar)
        sidebar.project_path = project_path
        if project_path:
            self.notify(f"Opened project: {project_path.name}", severity="information")
    
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection from the project tree."""
        event.stop()
        self.current_file = event.path
        
        # Route to appropriate view based on file type
        suffix = event.path.suffix.lower()
        if suffix in self.IMAGE_EXTENSIONS:
            self.current_view = "graphics"
        elif suffix in self.AUDIO_EXTENSIONS:
            self.current_view = "audio"
        elif suffix in self.ROM_EXTENSIONS:
            self.current_view = "rom"
        else:
            self.current_view = "code"
        
        # Auto-hide sidebar after selection
        self.show_sidebar = False
    
    def action_toggle_files(self) -> None:
        """Toggle between tools and file views (code, graphics, or audio)."""
        if self.current_view == "tools":
            if self.current_file:
                # Return to whichever file view was appropriate
                suffix = self.current_file.suffix.lower()
                if suffix in self.IMAGE_EXTENSIONS:
                    self.current_view = "graphics"
                elif suffix in self.AUDIO_EXTENSIONS:
                    self.current_view = "audio"
                else:
                    self.current_view = "code"
            elif self.project_path:
                self.notify("Select a file from the Project tree", severity="information")
                self.show_sidebar = True
        else:
            self.current_view = "tools"
    
    def action_show_tools(self) -> None:
        """Show the tools panel."""
        self.current_view = "tools"
    
    def action_zoom_in(self) -> None:
        """Zoom in on the graphics canvas."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.action_zoom_in()
                # Update status bar
                tile_editor = self.query_one(TileEditorPanel)
                if tile_editor.file_path:
                    tile_editor.file_path = tile_editor.file_path  # Trigger refresh
            except Exception:
                pass
    
    def action_zoom_out(self) -> None:
        """Zoom out on the graphics canvas."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.action_zoom_out()
                tile_editor = self.query_one(TileEditorPanel)
                if tile_editor.file_path:
                    tile_editor.file_path = tile_editor.file_path  # Trigger refresh
            except Exception:
                pass
    
    def action_toggle_grid(self) -> None:
        """Toggle grid display on the graphics canvas."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.action_toggle_grid()
            except Exception:
                pass
    
    def action_new_tileset(self) -> None:
        """Open the New Tileset dialog."""
        # Use project path or home directory as default
        default_dir = self.project_path or Path.home()
        
        def on_new_tileset_result(result: dict | None) -> None:
            if result is None:
                return
            
            # Got a new tileset
            tileset = result["tileset"]
            file_path = result["file_path"]
            
            # Save the new tileset as a PNG file
            if HAS_PIL:
                try:
                    from PIL import Image
                    w = tileset.image_width
                    h = tileset.image_height
                    tile_w = tileset.tile_width
                    tile_h = tileset.tile_height
                    tiles_per_row = tileset.tiles_per_row
                    
                    img = Image.new("RGB", (w, h))
                    for tile_idx, tile in enumerate(tileset.tiles):
                        tile_row = tile_idx // tiles_per_row
                        tile_col = tile_idx % tiles_per_row
                        base_x = tile_col * tile_w
                        base_y = tile_row * tile_h
                        
                        for y in range(tile_h):
                            for x in range(tile_w):
                                color_idx = tile.get_pixel(x, y)
                                r, g, b = tileset.palette.get_color(0, color_idx)
                                img.putpixel((base_x + x, base_y + y), (r, g, b))
                    
                    img.save(file_path)
                except Exception as e:
                    self.notify(f"Failed to save: {e}", severity="error")
                    return
            
            # Update the graphics editor
            try:
                tile_editor = self.query_one(TileEditorPanel)
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                palette_bar = self.query_one("#tile-palette-bar", PaletteBar)
                
                # Set up the new tileset
                tile_editor._tileset = tileset
                tile_editor.file_path = file_path
                canvas.tileset = tileset
                palette_bar.palette = tileset.palette
                
                # Switch to graphics view
                self.current_view = "graphics"
                
                # Update sidebar with new tileset
                sidebar = self.query_one(Sidebar)
                tileset_preview = sidebar.query_one(TilesetPreview)
                tileset_preview.tileset = tileset
                sidebar.show_drawing_section(tileset)
                
                self.notify(
                    f"Created {file_path.name} ({result['width_tiles']}×{result['height_tiles']} tiles)",
                    severity="information"
                )
            except Exception as e:
                self.notify(f"Error creating tileset: {e}", severity="error")
        
        self.push_screen(NewTilesetScreen(default_dir), on_new_tileset_result)
    
    def action_slice_image(self) -> None:
        """Open the Slice Image dialog for the current image."""
        # Only works when viewing an image in graphics mode
        if self.current_view != "graphics":
            self.notify("Open an image first (click a PNG/BMP file)", severity="warning")
            return
        
        try:
            tile_editor = self.query_one(TileEditorPanel)
            if not tile_editor.file_path:
                self.notify("No image file loaded", severity="warning")
                return
            
            image_path = tile_editor.file_path
            
            def on_slice_result(result: dict | None) -> None:
                if result is None:
                    return
                
                tileset = result["tileset"]
                file_path = result["file_path"]
                
                try:
                    canvas = self.query_one("#pixel-canvas", PixelCanvas)
                    palette_bar = self.query_one("#tile-palette-bar", PaletteBar)
                    
                    tile_editor._tileset = tileset
                    tile_editor.file_path = file_path
                    canvas.tileset = tileset
                    canvas.current_tile_index = 0
                    palette_bar.palette = tileset.palette
                    
                    # Update sidebar
                    sidebar = self.query_one(Sidebar)
                    tileset_preview = sidebar.query_one(TilesetPreview)
                    tileset_preview.tileset = tileset
                    sidebar.show_drawing_section(tileset)
                    
                    tile_editor._update_status()
                    
                    self.notify(
                        f"Sliced into {result['tiles_x']}×{result['tiles_y']} tiles "
                        f"({result['tile_size']}×{result['tile_size']}px, {2**result['bpp']} colors)",
                        severity="information"
                    )
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")
            
            self.push_screen(SliceImageScreen(image_path), on_slice_result)
            
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
    
    def action_toggle_graphics_mode(self) -> None:
        """Toggle between edit and display mode for graphics canvas."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.action_toggle_edit_mode()
            except Exception:
                pass
        else:
            # For code view, open in external editor
            self.action_open_in_editor()
    
    def action_show_profiler(self) -> None:
        """Switch to the profiler view."""
        self.notify("Switching to Silicon Turtleneck Profiler...", severity="information")
        self.current_view = "profiler"
        sidebar = self.query_one(Sidebar)
        sidebar.hide_drawing_section()

    def action_show_disassembler(self) -> None:
        """Switch to the disassembler view."""
        self.current_view = "disassembler"
        sidebar = self.query_one(Sidebar)
        sidebar.hide_drawing_section()

    def action_set_pencil_tool(self) -> None:
        """Set the pencil drawing tool."""
        self._set_graphics_tool("pencil")
    
    def action_set_eyedropper_tool(self) -> None:
        """Set the eyedropper (color picker) tool."""
        self._set_graphics_tool("eyedropper")
    
    def on_tool_selector_tool_selected(self, event: ToolSelector.ToolSelected) -> None:
        """Handle tool selection from sidebar tool selector."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.current_tool = event.tool
            except Exception:
                pass
    
    def on_tileset_preview_tile_selected(self, event: TilesetPreview.TileSelected) -> None:
        """Handle tile selection from sidebar tileset preview."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.scroll_to_tile(event.tile_index)
                self.notify(f"Tile {event.tile_index:02X} selected", severity="information")
            except Exception:
                self.notify(f"Tile {event.tile_index:02X} selected", severity="information")
    
    def on_pixel_canvas_tile_navigated(self, event: PixelCanvas.TileNavigated) -> None:
        """Handle tile navigation from canvas (Tab/Shift+Tab)."""
        try:
            sidebar = self.query_one(Sidebar)
            tileset_preview = sidebar.query_one(TilesetPreview)
            tileset_preview.selected_tile = event.tile_index
        except Exception:
            pass
    
    def _set_graphics_tool(self, tool: str) -> None:
        """Helper to set a graphics tool and update sidebar."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.current_tool = tool
                sidebar = self.query_one(Sidebar)
                sidebar.update_selected_tool(tool)
            except Exception:
                pass
    
    def action_set_fill_tool(self) -> None:
        """Set the fill (flood fill) tool."""
        self._set_graphics_tool("fill")
    
    def action_set_line_tool(self) -> None:
        """Set the line drawing tool."""
        self._set_graphics_tool("line")
    
    def action_set_rect_tool(self) -> None:
        """Set the rectangle drawing tool."""
        self._set_graphics_tool("rect")
    
    def action_set_ellipse_tool(self) -> None:
        """Set the ellipse drawing tool."""
        self._set_graphics_tool("ellipse")
    
    def action_save_graphics(self) -> None:
        """Save the current graphics file."""
        if self.current_view == "graphics":
            try:
                tile_editor = self.query_one(TileEditorPanel)
                if tile_editor.save_image():
                    self.notify("Image saved", severity="information")
                else:
                    self.notify("Nothing to save or save failed", severity="warning")
            except Exception as e:
                self.notify(f"Save failed: {e}", severity="error")
    
    def action_undo_graphics(self) -> None:
        """Undo the last graphics edit."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.action_undo()
                tile_editor = self.query_one(TileEditorPanel)
                tile_editor._update_status()
            except Exception:
                pass
    
    def action_redo_graphics(self) -> None:
        """Redo the last undone graphics edit."""
        if self.current_view == "graphics":
            try:
                canvas = self.query_one("#pixel-canvas", PixelCanvas)
                canvas.action_redo()
                tile_editor = self.query_one(TileEditorPanel)
                tile_editor._update_status()
            except Exception:
                pass
    
    def action_open_in_editor(self) -> None:
        """Open current file in external editor."""
        if not self.current_file:
            self.notify("No file selected", severity="warning")
            return
        
        if not self.current_file.exists():
            self.notify(f"File not found: {self.current_file}", severity="error")
            return
        
        # Get editor from environment or fallback to common editors
        editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
        if not editor:
            # Try common editors
            for fallback in ["nano", "vim", "vi", "code", "gedit", "kate"]:
                if shutil.which(fallback):
                    editor = fallback
                    break
        
        if not editor:
            self.notify("No editor found. Set $EDITOR environment variable.", severity="error")
            return
        
        file_path = self.current_file
        
        # Suspend the TUI, run editor, then resume
        with self.suspend():
            try:
                subprocess.run([editor, str(file_path)])
            except Exception as e:
                # Will show after resume
                pass
        
        # Refresh the file view after editor closes
        code_viewer = self.query_one(CodeViewer)
        # Force a refresh by toggling the path
        code_viewer.file_path = None
        code_viewer.file_path = file_path
        self.notify(f"Returned from {editor}", severity="information")
    
    def action_open_project(self) -> None:
        """Open a project directory (placeholder - could show a dialog)."""
        # For now, just use current directory
        # In future, could integrate with a file picker
        self.project_path = Path.cwd()
        self.show_sidebar = True
        # Expand project section
        try:
            project_section = self.query_one("#project-section", Collapsible)
            project_section.collapsed = False
        except Exception:
            pass

    def load_tools_from_json(self) -> None:
        """Load tools from tools.json."""
        # Try tools.json first, then tools_.json as fallback
        # Look in parent directory of this package (src/)
        tools_json_path = Path(__file__).parent.parent / "tools.json"
        if not tools_json_path.exists():
            tools_json_path = Path(__file__).parent.parent / "tools_.json"

        if not tools_json_path.exists():
            return

        try:
            with open(tools_json_path) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return

        tools = data.get("tools", [])

        for tool_def in tools:
            tool_name = tool_def.get("name")
            if not tool_name:
                continue

            available = self._check_tool_available(tool_def)
            tool_record = {
                **tool_def,
                "available": available,
                "path": self._find_tool_path(tool_def) if available else None,
            }

            self.all_tools_map[tool_name] = tool_record

            category = tool_def.get("category", "other")
            if category not in self.tools_by_category:
                self.tools_by_category[category] = []
            self.tools_by_category[category].append(tool_record)

    def _check_tool_available(self, tool_def: Dict[str, Any]) -> bool:
        """Check if a tool is available in PATH."""
        import shutil

        # Check by tool name
        tool_name = tool_def.get("name")
        if tool_name and isinstance(tool_name, str) and shutil.which(tool_name):
            return True

        # Check binary_name
        binary_name = tool_def.get("binary_name")
        if binary_name:
            if isinstance(binary_name, dict):
                import platform
                plat = "darwin" if platform.system() == "Darwin" else "linux" if platform.system() == "Linux" else "win32"
                binary_name = binary_name.get(plat)
            if binary_name and isinstance(binary_name, str) and shutil.which(binary_name):
                return True

        return False

    def _find_tool_path(self, tool_def: Dict[str, Any]) -> str | None:
        """Find the full path to a tool."""
        import shutil

        tool_name = tool_def.get("name")
        if tool_name and isinstance(tool_name, str):
            path = shutil.which(tool_name)
            if path:
                return path

        binary_name = tool_def.get("binary_name")
        if binary_name:
            if isinstance(binary_name, dict):
                import platform
                plat = "darwin" if platform.system() == "Darwin" else "linux" if platform.system() == "Linux" else "win32"
                binary_name = binary_name.get(plat)
            if binary_name and isinstance(binary_name, str):
                path = shutil.which(binary_name)
                if path:
                    return path

        return None

    def populate_tool_list(self) -> None:
        """Populate the sidebar with tools."""
        list_view = self.query_one("#tool-list", ListView)
        list_view.clear()

        for category in sorted(self.tools_by_category.keys()):
            tools = self.tools_by_category[category]
            
            # Category header
            available_count = sum(1 for t in tools if t.get("available"))
            total_count = len(tools)
            cat_label = f"━━ {category.upper()} ({available_count}/{total_count}) ━━"
            list_view.append(ListItem(Label(f"[bold]{cat_label}[/bold]"), disabled=True))

            # Tools in category
            for tool in sorted(tools, key=lambda t: (not t.get("available"), t["name"])):
                icon = "[green]●[/green]" if tool.get("available") else "[red]○[/red]"
                item = ListItem(Label(f"{icon} {tool['name']}"))
                item.data = tool["name"]  # Store tool name for lookup
                list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle tool selection from list."""
        item = event.item
        if hasattr(item, "data") and item.data:
            tool_name = item.data
            if tool_name in self.all_tools_map:
                detail_panel = self.query_one(ToolDetailPanel)
                detail_panel.tool_data = self.all_tools_map[tool_name]
                # Auto-hide sidebar after selection
                self.show_sidebar = False

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        self.show_sidebar = not self.show_sidebar

    def watch_show_sidebar(self, show_sidebar: bool) -> None:
        """Update sidebar visibility class."""
        self.query_one(Sidebar).set_class(show_sidebar, "-visible")

    def action_refresh(self) -> None:
        """Refresh the tool list."""
        self.tools_by_category.clear()
        self.all_tools_map.clear()
        self.load_tools_from_json()
        self.populate_tool_list()

    def action_install(self) -> None:
        """Install the currently selected tool."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected. Press 's' to open sidebar and select a tool.", severity="warning")
            return
        
        if tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is already installed.", severity="information")
            return
        
        # Push the install screen
        self.push_screen(InstallScreen(tool_data), self._on_install_complete)

    def action_update(self) -> None:
        """Update (re-install) the currently selected tool."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected.", severity="warning")
            return
        
        if not tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is not installed. Use Install instead.", severity="warning")
            return
        
        # Push the install screen (update = re-install)
        self.push_screen(InstallScreen(tool_data, title_prefix="Updating"), self._on_install_complete)

    def action_verify(self) -> None:
        """Verify the currently selected tool's installation."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected.", severity="warning")
            return
        
        if not tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is not installed.", severity="warning")
            return
        
        verify_cmd = tool_data.get("verify_command", [])
        if not verify_cmd:
            self.notify(f"No verify command for {tool_data.get('name')}", severity="information")
            return
        
        # Run verify command and show result
        self.push_screen(VerifyScreen(tool_data), self._on_verify_complete)

    def action_uninstall(self) -> None:
        """Uninstall the currently selected tool."""
        detail_panel = self.query_one(ToolDetailPanel)
        tool_data = detail_panel.tool_data
        
        if tool_data is None:
            self.notify("No tool selected.", severity="warning")
            return
        
        if not tool_data.get("available"):
            self.notify(f"{tool_data.get('name')} is not installed.", severity="information")
            return
        
        # Push the uninstall screen
        self.push_screen(UninstallScreen(tool_data), self._on_uninstall_complete)

    def _on_install_complete(self, success: bool) -> None:
        """Handle install completion."""
        if success:
            self.notify("Installation complete! Refreshing...", severity="information")
            self.action_refresh()
        else:
            self.notify("Installation did not complete successfully.", severity="warning")

    def _on_verify_complete(self, success: bool) -> None:
        """Handle verify completion."""
        if success:
            self.notify("Verification passed!", severity="information")
        else:
            self.notify("Verification failed.", severity="warning")

    def _on_uninstall_complete(self, success: bool) -> None:
        """Handle uninstall completion."""
        if success:
            self.notify("Uninstall complete! Refreshing...", severity="information")
            self.action_refresh()
        else:
            self.notify("Uninstall had errors.", severity="warning")


if __name__ == "__main__":
    # Accept optional project path as argument
    project = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    SNESIDEApp(project_path=project).run()
