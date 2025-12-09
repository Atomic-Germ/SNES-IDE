from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from rich.segment import Segment
from rich.style import Style
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import Click
from textual.geometry import Size
from textual.message import Message
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static, Label

from ..logic.graphics import SNESTileset, SNESTile, SNESPalette, HAS_PIL
from .preview_panel import AssemblyPreviewPanel

class PixelCanvas(ScrollView):
    """Terminal-based pixel canvas for SNES graphics display and editing.
    
    Extends ScrollView to provide scrollable content with render_line().
    
    EDIT MODE (zoom >= 4):
    - Each pixel = 2 full block chars wide × 1 row tall (square)
    - Easy mouse targeting, full precision
    
    DISPLAY MODE:
    - Half-block rendering for compact view
    - Read-only overview
    
    Press 'd' to toggle between modes.
    """
    
    DEFAULT_CSS = """
    PixelCanvas {
        width: 100%;
        height: 100%;
        overflow: auto;
        background: $surface;
    }
    """
    
    BINDINGS = [
        ("p", "set_tool('pencil')", "Pencil"),
        ("i", "set_tool('eyedropper')", "Eyedropper"),
        ("d", "toggle_edit_mode", "Edit/Display Mode"),
        ("tab", "next_tile", "Next Tile"),
        ("shift+tab", "prev_tile", "Previous Tile"),
    ]
    
    # Reactive properties
    zoom: reactive[int] = reactive(4)  # Minimum 4 for editing (full blocks)
    current_tile_index: reactive[int] = reactive(0)
    show_grid: reactive[bool] = reactive(True)
    current_color_index: reactive[int] = reactive(1)  # Default to color 1 (0 is usually transparent)
    current_tool: reactive[str] = reactive("pencil")  # "pencil", "eyedropper", "fill", "line", "rect", "ellipse"
    is_modified: reactive[bool] = reactive(False)
    edit_mode: reactive[bool] = reactive(True)  # True = full-block editing, False = half-block display
    
    # Shape tool state (for preview and drawing)
    _shape_start: tuple[int, int] | None = None  # Starting point for shape tools
    _shape_preview: set[tuple[int, int]] = set()  # Pixels to preview (as set for O(1) lookup)
    
    # Minimum zoom for editing (each pixel = 2 chars wide x 1 row tall = square)
    MIN_EDIT_ZOOM = 4
    
    # Maximum undo stack size
    MAX_UNDO_STEPS = 50
    
    def __init__(
        self, 
        tileset: SNESTileset | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        """Initialize the canvas.
        
        Args:
            tileset: Tileset to display
            name, id, classes: Standard Textual widget parameters
        """
        super().__init__(name=name, id=id, classes=classes)
        self._tileset = tileset
        self._is_drawing = False
        self._last_draw_pos: Tuple[int, int] | None = None
        # Undo/redo stacks store snapshots of tile pixel data
        self._undo_stack: List[List[List[List[int]]]] = []
        self._redo_stack: List[List[List[List[int]]]] = []
    
    @property
    def tileset(self) -> SNESTileset | None:
        return self._tileset
    
    @tileset.setter
    def tileset(self, value: SNESTileset | None) -> None:
        self._tileset = value
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.is_modified = False
        self._update_virtual_size()
        self.refresh()
    
    def _update_virtual_size(self) -> None:
        """Update virtual_size based on tileset dimensions and zoom."""
        if not self._tileset or not self._tileset.tiles:
            self.virtual_size = Size(1, 1)
            return
        
        tiles_per_row = self._tileset.tiles_per_row or 1
        tile_w = self._tileset.tile_width
        tile_h = self._tileset.tile_height
        total_tile_rows = (len(self._tileset.tiles) + tiles_per_row - 1) // tiles_per_row
        pixel_width = tiles_per_row * tile_w
        pixel_height = total_tile_rows * tile_h
        
        zoom = self.zoom
        if self.edit_mode and zoom >= self.MIN_EDIT_ZOOM:
            # Edit mode: 2 chars per pixel, 1 row per pixel (at zoom=4)
            chars_per_pixel = zoom // 2
            rows_per_pixel = max(1, zoom // 4)
            grid_chars = (tiles_per_row - 1) if self.show_grid else 0
            # Add horizontal grid line rows (one between each tile row)
            h_grid_rows = (total_tile_rows - 1) if self.show_grid else 0
            width = pixel_width * chars_per_pixel + grid_chars
            height = pixel_height * rows_per_pixel + h_grid_rows
        else:
            # Display mode: 1 char per pixel, 2 pixels per row
            grid_chars = (tiles_per_row - 1) if self.show_grid else 0
            # Horizontal grid adds rows between tile rows
            h_grid_rows = (total_tile_rows - 1) if self.show_grid else 0
            width = pixel_width + grid_chars
            height = (pixel_height + 1) // 2 + h_grid_rows
        
        self.virtual_size = Size(width, height)
    
    def watch_zoom(self, zoom: int) -> None:
        """Update virtual size when zoom changes."""
        self._update_virtual_size()
        self.refresh()
    
    def watch_edit_mode(self, edit_mode: bool) -> None:
        """Update virtual size when edit mode changes."""
        self._update_virtual_size()
        self.refresh()
    
    def watch_show_grid(self, show_grid: bool) -> None:
        """Update virtual size when grid visibility changes."""
        self._update_virtual_size()
        self.refresh()
    
    def render_line(self, y: int) -> Strip:
        """Render a single line of the canvas.
        
        Two rendering modes:
        
        EDIT MODE (zoom >= 4, edit_mode=True):
        - Each pixel = 2 full blocks wide (██) × 1 row tall
        - At zoom=4: 2 chars per pixel, 1 row per pixel
        - At zoom=8: 4 chars per pixel, 2 rows per pixel
        - Square pixels, easy mouse targeting
        
        DISPLAY MODE (edit_mode=False):
        - Half-block rendering for compact view
        - Use ▄ with fg=bottom, bg=top
        - 2 pixel rows per terminal row
        - Read-only (for overview)
        """
        if not self._tileset or not self._tileset.tiles:
            if y == 0:
                return Strip([Segment("[dim]No image loaded[/dim]")])
            return Strip([])
        
        # Get scroll offset - y is the viewport line, we need to add scroll offset
        scroll_x, scroll_y = self.scroll_offset
        content_y = scroll_y + y
        
        zoom = self.zoom
        tiles_per_row = self._tileset.tiles_per_row or 1
        tile_w = self._tileset.tile_width
        tile_h = self._tileset.tile_height
        
        # Total pixel dimensions
        total_tile_rows = (len(self._tileset.tiles) + tiles_per_row - 1) // tiles_per_row
        pixel_height = total_tile_rows * tile_h
        pixel_width = tiles_per_row * tile_w
        
        # Calculate current tile row/col for highlighting
        current_tile_row = self.current_tile_index // tiles_per_row
        current_tile_col = self.current_tile_index % tiles_per_row
        
        if self.edit_mode and zoom >= self.MIN_EDIT_ZOOM:
            # EDIT MODE: Full blocks, 1 pixel per row (at base zoom)
            # chars_per_pixel = zoom // 2 (so zoom=4 -> 2 chars, zoom=8 -> 4 chars)
            # rows_per_pixel = zoom // 4 (so zoom=4 -> 1 row, zoom=8 -> 2 rows)
            chars_per_pixel = zoom // 2
            rows_per_pixel = max(1, zoom // 4)
            
            pixel_y = content_y // rows_per_pixel
            
            # Check if this is a horizontal grid line row (between tiles)
            if self.show_grid and pixel_y > 0 and pixel_y % tile_h == 0 and pixel_y < pixel_height:
                # This is a grid line row - render horizontal separator
                tile_row_above = (pixel_y - 1) // tile_h
                segments = []
                for px in range(pixel_width):
                    tile_col = px // tile_w
                    tile_x = px % tile_w
                    
                    # Highlight if adjacent to current tile
                    is_current_grid = (tile_row_above == current_tile_row or tile_row_above + 1 == current_tile_row) and tile_col == current_tile_col
                    grid_color = "bright_cyan" if is_current_grid else "gray50"
                    
                    if tile_x == tile_w - 1 and tile_col < tiles_per_row - 1:
                        # Intersection with vertical grid
                        segments.append(Segment("─" * chars_per_pixel + "┼", Style(color=grid_color)))
                    else:
                        segments.append(Segment("─" * chars_per_pixel, Style(color=grid_color)))
                
                strip = Strip(segments)
                return strip.crop(scroll_x, scroll_x + self.size.width)
            
            if pixel_y >= pixel_height:
                return Strip([])
            
            # Check if this row is part of the current tile
            current_pixel_row_in_tile = pixel_y // tile_h
            is_current_tile_row = current_pixel_row_in_tile == current_tile_row
            is_tile_top_edge = (pixel_y % tile_h == 0) and is_current_tile_row
            is_tile_bottom_edge = (pixel_y % tile_h == tile_h - 1) and is_current_tile_row
            
            segments = []
            for px in range(pixel_width):
                tile_col = px // tile_w
                tile_x = px % tile_w
                
                # Check if this pixel is in the current tile (for border highlighting)
                is_current_tile = (tile_col == current_tile_col and is_current_tile_row)
                is_left_edge = (tile_x == 0) and is_current_tile
                is_right_edge = (tile_x == tile_w - 1) and is_current_tile
                is_edge = is_tile_top_edge or is_tile_bottom_edge or is_left_edge or is_right_edge
                
                color = self._get_pixel_color(tile_col, pixel_y, tile_x, pixel_y % tile_h)
                
                # For selected tile edges, use a bright visible border
                if is_current_tile and is_edge:
                    # Use bright cyan border for selected tile
                    style = Style(
                        bgcolor=f"rgb({color[0]},{color[1]},{color[2]})",
                        color="bright_cyan",
                        bold=True,
                        underline=is_tile_bottom_edge,
                        overline=is_tile_top_edge
                    )
                    # Use box-drawing chars for left/right edges
                    if is_left_edge and is_right_edge:
                        char = "║" + " " * (chars_per_pixel - 2) + "║" if chars_per_pixel > 2 else "█" * chars_per_pixel
                    elif is_left_edge:
                        char = "▌" + " " * (chars_per_pixel - 1)
                    elif is_right_edge:
                        char = " " * (chars_per_pixel - 1) + "▐"
                    else:
                        char = " " * chars_per_pixel
                    segments.append(Segment(char, style))
                else:
                    style = Style(bgcolor=f"rgb({color[0]},{color[1]},{color[2]})")
                    segments.append(Segment(" " * chars_per_pixel, style))
                
                # Grid line between tiles - highlight if adjacent to current tile
                if self.show_grid and tile_x == tile_w - 1 and tile_col < tiles_per_row - 1:
                    is_current_grid = (tile_col == current_tile_col or tile_col + 1 == current_tile_col) and is_current_tile_row
                    grid_color = "bright_cyan" if is_current_grid else "gray50"
                    segments.append(Segment("│", Style(color=grid_color)))
            
            # Crop horizontally to viewport
            strip = Strip(segments)
            return strip.crop(scroll_x, scroll_x + self.size.width)
        
        else:
            # DISPLAY MODE: Half-block rendering (compact, read-only)
            # Each terminal row shows 2 pixel rows
            pixel_y_top = content_y * 2
            pixel_y_bot = pixel_y_top + 1
            
            # Check if this is a horizontal grid line row
            if self.show_grid and pixel_y_top > 0 and pixel_y_top % tile_h == 0 and pixel_y_top < pixel_height:
                tile_row_above = (pixel_y_top - 1) // tile_h
                segments = []
                for px in range(pixel_width):
                    tile_col = px // tile_w
                    tile_x = px % tile_w
                    
                    is_current_grid = (tile_row_above == current_tile_row or tile_row_above + 1 == current_tile_row) and tile_col == current_tile_col
                    grid_color = "bright_cyan" if is_current_grid else "gray50"
                    
                    if tile_x == tile_w - 1 and tile_col < tiles_per_row - 1:
                        segments.append(Segment("┼", Style(color=grid_color)))
                    else:
                        segments.append(Segment("─", Style(color=grid_color)))
                
                strip = Strip(segments)
                return strip.crop(scroll_x, scroll_x + self.size.width)
            
            if pixel_y_top >= pixel_height:
                return Strip([])
            
            segments = []
            for px in range(pixel_width):
                tile_col = px // tile_w
                tile_x = px % tile_w
                
                # Check if this pixel column is part of the current tile
                tile_row_at_top = pixel_y_top // tile_h
                is_current_tile = (tile_col == current_tile_col and tile_row_at_top == current_tile_row)
                
                top_color = self._get_pixel_color(tile_col, pixel_y_top, tile_x, pixel_y_top % tile_h)
                
                if pixel_y_bot < pixel_height:
                    bot_color = self._get_pixel_color(tile_col, pixel_y_bot, tile_x, pixel_y_bot % tile_h)
                else:
                    bot_color = (0, 0, 0)
                
                # Highlight selected tile with brighter colors
                if is_current_tile:
                    # Boost brightness for selected tile
                    top_color = tuple(min(255, c + 40) for c in top_color)
                    bot_color = tuple(min(255, c + 40) for c in bot_color)
                
                # ▄ with fg=bottom, bg=top
                style = Style(
                    color=f"rgb({bot_color[0]},{bot_color[1]},{bot_color[2]})",
                    bgcolor=f"rgb({top_color[0]},{top_color[1]},{top_color[2]})"
                )
                segments.append(Segment("▄", style))
                
                # Grid line between tiles - highlight if adjacent to current tile
                if self.show_grid and tile_x == tile_w - 1 and tile_col < tiles_per_row - 1:
                    is_current_row = tile_row_at_top == current_tile_row
                    is_current_grid = (tile_col == current_tile_col or tile_col + 1 == current_tile_col) and is_current_row
                    grid_color = "bright_cyan" if is_current_grid else "gray50"
                    segments.append(Segment("│", Style(color=grid_color)))
            
            # Crop horizontally to viewport
            strip = Strip(segments)
            return strip.crop(scroll_x, scroll_x + self.size.width)
    
    def _get_pixel_color(
        self, tile_col: int, pixel_y: int, tile_x: int, tile_y_in_tile: int
    ) -> Tuple[int, int, int]:
        """Get the RGB color for a pixel position.
        
        Args:
            tile_col: Which tile column (0-based)
            pixel_y: Global Y pixel coordinate
            tile_x: X position within the tile
            tile_y_in_tile: Y position within the tile
            
        Returns:
            RGB tuple
        """
        if not self._tileset:
            return (0, 0, 0)
        
        tile_h = self._tileset.tile_height
        tile_w = self._tileset.tile_width
        tiles_per_row = self._tileset.tiles_per_row or 1
        
        tile_row = pixel_y // tile_h
        tile_idx = tile_row * tiles_per_row + tile_col
        
        # Calculate global pixel x
        global_pixel_x = tile_col * tile_w + tile_x
        
        # Check if this pixel is in the shape preview
        if self._shape_preview and (global_pixel_x, pixel_y) in self._shape_preview:
            # Return the preview color (the current selected color)
            return self._tileset.palette.get_color(0, self.current_color_index)
        
        tile = self._tileset.get_tile(tile_idx)
        if not tile:
            return (0, 0, 0)
        
        color_idx = tile.get_pixel(tile_x, tile_y_in_tile)
        return self._tileset.palette.get_color(0, color_idx)
    
    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        """Calculate content height for scrolling."""
        if not self._tileset or not self._tileset.tiles:
            return 1
        
        tiles_per_row = self._tileset.tiles_per_row or 1
        tile_h = self._tileset.tile_height
        total_tile_rows = (len(self._tileset.tiles) + tiles_per_row - 1) // tiles_per_row
        pixel_height = total_tile_rows * tile_h
        
        zoom = self.zoom
        if self.edit_mode and zoom >= self.MIN_EDIT_ZOOM:
            # Edit mode: 1 row per pixel (at zoom=4), more at higher zoom
            rows_per_pixel = max(1, zoom // 4)
            return pixel_height * rows_per_pixel
        else:
            # Display mode: 2 pixels per row (half-blocks)
            return (pixel_height + 1) // 2
    
    def get_content_width(self, container: Size, viewport: Size, height: int) -> int:
        """Calculate content width for horizontal scrolling."""
        if not self._tileset or not self._tileset.tiles:
            return 1
        
        tiles_per_row = self._tileset.tiles_per_row or 1
        tile_w = self._tileset.tile_width
        pixel_width = tiles_per_row * tile_w
        
        zoom = self.zoom
        if self.edit_mode and zoom >= self.MIN_EDIT_ZOOM:
            # Edit mode: 2 chars per pixel (at zoom=4), more at higher zoom
            chars_per_pixel = zoom // 2
            # Add grid lines between tiles
            grid_chars = (tiles_per_row - 1) if self.show_grid else 0
            return pixel_width * chars_per_pixel + grid_chars
        else:
            # Display mode: 1 char per pixel
            grid_chars = (tiles_per_row - 1) if self.show_grid else 0
            return pixel_width + grid_chars
    
    def action_zoom_in(self) -> None:
        """Increase zoom level."""
        if self.zoom < 16:
            self.zoom = min(16, self.zoom * 2)
            self.refresh()
    
    def action_zoom_out(self) -> None:
        """Decrease zoom level."""
        # In edit mode, don't go below MIN_EDIT_ZOOM
        min_zoom = self.MIN_EDIT_ZOOM if self.edit_mode else 1
        if self.zoom > min_zoom:
            self.zoom = max(min_zoom, self.zoom // 2)
            self.refresh()
    
    def action_toggle_grid(self) -> None:
        """Toggle grid display."""
        self.show_grid = not self.show_grid
        self.refresh()
    
    def action_toggle_edit_mode(self) -> None:
        """Toggle between edit mode (full blocks) and display mode (half blocks)."""
        self.edit_mode = not self.edit_mode
        if self.edit_mode and self.zoom < self.MIN_EDIT_ZOOM:
            self.zoom = self.MIN_EDIT_ZOOM
        mode_name = "Edit" if self.edit_mode else "Display"
        self.app.notify(f"{mode_name} mode", severity="information")
        self.refresh()

    def action_set_tool(self, tool: str) -> None:
        """Set the current drawing tool."""
        valid_tools = ("pencil", "eyedropper", "fill", "line", "rect", "ellipse")
        if tool in valid_tools:
            self.current_tool = tool
            self.app.notify(f"Tool: {tool.capitalize()}", severity="information")
    
    def action_next_tile(self) -> None:
        """Navigate to the next tile."""
        if not self._tileset or not self._tileset.tiles:
            return
        max_idx = len(self._tileset.tiles) - 1
        if self.current_tile_index < max_idx:
            self.current_tile_index += 1
            self.scroll_to_tile(self.current_tile_index)
    
    def action_prev_tile(self) -> None:
        """Navigate to the previous tile."""
        if not self._tileset or not self._tileset.tiles:
            return
        if self.current_tile_index > 0:
            self.current_tile_index -= 1
            self.scroll_to_tile(self.current_tile_index)
    
    def scroll_to_tile(self, tile_index: int) -> None:
        """Scroll the canvas to center a specific tile on screen.
        
        Args:
            tile_index: Index of the tile to scroll to
        """
        if not self._tileset or not self._tileset.tiles:
            return
        
        if tile_index < 0 or tile_index >= len(self._tileset.tiles):
            return
        
        tiles_per_row = self._tileset.tiles_per_row or 1
        tile_w = self._tileset.tile_width
        tile_h = self._tileset.tile_height
        
        # Calculate tile position
        tile_row = tile_index // tiles_per_row
        tile_col = tile_index % tiles_per_row
        
        # Calculate pixel position of tile center
        pixel_x = tile_col * tile_w + tile_w // 2
        pixel_y = tile_row * tile_h + tile_h // 2
        
        # Convert to terminal coordinates based on mode
        zoom = self.zoom
        if self.edit_mode and zoom >= self.MIN_EDIT_ZOOM:
            chars_per_pixel = zoom // 2
            rows_per_pixel = max(1, zoom // 4)
            grid_offset = tile_col if self.show_grid else 0
            h_grid_offset = tile_row if self.show_grid else 0  # Horizontal grid lines
            target_x = pixel_x * chars_per_pixel + grid_offset
            target_y = pixel_y * rows_per_pixel + h_grid_offset
            
            # Calculate tile dimensions in terminal chars
            tile_width_chars = tile_w * chars_per_pixel
            tile_height_rows = tile_h * rows_per_pixel
        else:
            grid_offset = tile_col if self.show_grid else 0
            h_grid_offset = tile_row if self.show_grid else 0
            target_x = pixel_x + grid_offset
            target_y = pixel_y // 2 + h_grid_offset
            
            tile_width_chars = tile_w
            tile_height_rows = tile_h // 2
        
        # Center the tile on screen by offsetting by half the viewport
        viewport_w = self.size.width
        viewport_h = self.size.height
        
        # Calculate scroll position to center the tile
        scroll_x = max(0, target_x - viewport_w // 2)
        scroll_y = max(0, target_y - viewport_h // 2)
        
        # Scroll to position
        self.scroll_to(scroll_x, scroll_y, animate=True)
        
        # Update the current tile index
        self.current_tile_index = tile_index
        
        # Post message for other widgets to sync
        self.post_message(self.TileNavigated(tile_index))
    
    def watch_current_tile_index(self, tile_index: int) -> None:
        """React to tile index changes."""
        self.refresh()
    
    class TileNavigated(Message):
        """Message sent when navigating to a tile."""
        def __init__(self, tile_index: int):
            super().__init__()
            self.tile_index = tile_index

    # =========================================================================
    # Mouse handling for drawing
    # =========================================================================
    
    def _terminal_to_pixel(self, x: int, y: int) -> Tuple[int, int] | None:
        """Convert terminal coordinates to pixel coordinates.
        
        In EDIT MODE (full blocks):
        - chars_per_pixel = zoom // 2 (zoom=4 -> 2 chars, zoom=8 -> 4 chars)
        - rows_per_pixel = zoom // 4 (zoom=4 -> 1 row, zoom=8 -> 2 rows)
        - Simple integer division gives exact pixel
        
        In DISPLAY MODE (half blocks):
        - 1 char per pixel horizontally
        - 2 pixels per row vertically (can't distinguish, returns top pixel)
        
        Args:
            x: Terminal column (0-based, viewport-relative)
            y: Terminal row (0-based, viewport-relative)
            
        Returns:
            (pixel_x, pixel_y) or None if outside image bounds
        """
        if not self._tileset or not self._tileset.tiles:
            return None
        
        # Add scroll offset to convert viewport coords to content coords
        scroll_x, scroll_y = self.scroll_offset
        content_x = x + scroll_x
        content_y = y + scroll_y
        
        zoom = self.zoom
        tiles_per_row = self._tileset.tiles_per_row or 1
        tile_w = self._tileset.tile_width
        tile_h = self._tileset.tile_height
        
        # Total pixel dimensions for bounds checking
        total_tile_rows = (len(self._tileset.tiles) + tiles_per_row - 1) // tiles_per_row
        pixel_height = total_tile_rows * tile_h
        pixel_width = tiles_per_row * tile_w
        
        if self.edit_mode and zoom >= self.MIN_EDIT_ZOOM:
            # EDIT MODE: Full blocks
            chars_per_pixel = zoom // 2
            rows_per_pixel = max(1, zoom // 4)
            
            # Handle grid lines in X
            if self.show_grid:
                chars_per_tile_col = tile_w * chars_per_pixel + 1
                tile_col = content_x // chars_per_tile_col
                x_in_tile_area = content_x % chars_per_tile_col
                
                # Clicking on grid line?
                if x_in_tile_area >= tile_w * chars_per_pixel:
                    return None
                
                pixel_x = tile_col * tile_w + x_in_tile_area // chars_per_pixel
            else:
                pixel_x = content_x // chars_per_pixel
            
            pixel_y = content_y // rows_per_pixel
        
        else:
            # DISPLAY MODE: Half blocks (read-only, but still need coordinate conversion)
            # 1 char per pixel X, 2 pixels per row Y
            if self.show_grid:
                chars_per_tile_col = tile_w + 1
                tile_col = content_x // chars_per_tile_col
                x_in_tile_area = content_x % chars_per_tile_col
                
                if x_in_tile_area >= tile_w:
                    return None
                
                pixel_x = tile_col * tile_w + x_in_tile_area
            else:
                pixel_x = content_x
            
            # Can only target top pixel of each pair in display mode
            pixel_y = content_y * 2
        
        # Bounds check
        if 0 <= pixel_x < pixel_width and 0 <= pixel_y < pixel_height:
            return (pixel_x, pixel_y)
        return None
    
    def _save_undo_state(self) -> None:
        """Save current tile state for undo."""
        if not self._tileset:
            return
        
        # Deep copy all tile pixel data
        state = []
        for tile in self._tileset.tiles:
            tile_data = [row[:] for row in tile.pixels]
            state.append(tile_data)
        
        self._undo_stack.append(state)
        
        # Limit stack size
        if len(self._undo_stack) > self.MAX_UNDO_STEPS:
            self._undo_stack.pop(0)
        
        # Clear redo stack on new edit
        self._redo_stack.clear()
    
    def _restore_state(self, state: List[List[List[int]]]) -> None:
        """Restore tile state from a snapshot."""
        if not self._tileset:
            return
        
        for tile_idx, tile_data in enumerate(state):
            if tile_idx < len(self._tileset.tiles):
                tile = self._tileset.tiles[tile_idx]
                tile.pixels = [row[:] for row in tile_data]
        
        self.refresh()
    
    def action_undo(self) -> None:
        """Undo the last edit."""
        if not self._undo_stack or not self._tileset:
            return
        
        # Save current state to redo stack
        current_state = []
        for tile in self._tileset.tiles:
            current_state.append([row[:] for row in tile.pixels])
        self._redo_stack.append(current_state)
        
        # Restore from undo stack
        state = self._undo_stack.pop()
        self._restore_state(state)
        
        if not self._undo_stack:
            self.is_modified = False
            
        self.post_message(self.PixelModified(self.current_tile_index))
    
    def action_redo(self) -> None:
        """Redo the last undone edit."""
        if not self._redo_stack or not self._tileset:
            return
        
        # Save current state to undo stack
        current_state = []
        for tile in self._tileset.tiles:
            current_state.append([row[:] for row in tile.pixels])
        self._undo_stack.append(current_state)
        
        # Restore from redo stack
        state = self._redo_stack.pop()
        self._restore_state(state)
        self.is_modified = True
        self.post_message(self.PixelModified(self.current_tile_index))
    
    def _set_pixel(self, pixel_x: int, pixel_y: int, color_index: int) -> None:
        """Set a pixel to the given color index."""
        if not self._tileset:
            return
        
        tile_w = self._tileset.tile_width
        tile_h = self._tileset.tile_height
        tiles_per_row = self._tileset.tiles_per_row or 1
        
        tile_col = pixel_x // tile_w
        tile_row = pixel_y // tile_h
        tile_idx = tile_row * tiles_per_row + tile_col
        
        tile = self._tileset.get_tile(tile_idx)
        if tile:
            tile_x = pixel_x % tile_w
            tile_y = pixel_y % tile_h
            tile.set_pixel(tile_x, tile_y, color_index)
    
    def _get_pixel_index(self, pixel_x: int, pixel_y: int) -> int:
        """Get the color index at a pixel position."""
        if not self._tileset:
            return 0
        
        tile_w = self._tileset.tile_width
        tile_h = self._tileset.tile_height
        tiles_per_row = self._tileset.tiles_per_row or 1
        
        tile_col = pixel_x // tile_w
        tile_row = pixel_y // tile_h
        tile_idx = tile_row * tiles_per_row + tile_col
        
        tile = self._tileset.get_tile(tile_idx)
        if tile:
            tile_x = pixel_x % tile_w
            tile_y = pixel_y % tile_h
            return tile.get_pixel(tile_x, tile_y)
        return 0
    
    def _get_image_bounds(self) -> tuple[int, int]:
        """Get the image dimensions in pixels."""
        if not self._tileset:
            return (0, 0)
        return (self._tileset.image_width, self._tileset.image_height)
    
    def _is_in_bounds(self, x: int, y: int) -> bool:
        """Check if pixel coordinates are within image bounds."""
        w, h = self._get_image_bounds()
        return 0 <= x < w and 0 <= y < h
    
    def _flood_fill(self, start_x: int, start_y: int, fill_color: int) -> None:
        """Flood fill from a starting point with the given color.
        
        Uses iterative approach to avoid recursion limit issues.
        """
        if not self._tileset:
            return
        
        w, h = self._get_image_bounds()
        if not self._is_in_bounds(start_x, start_y):
            return
        
        target_color = self._get_pixel_index(start_x, start_y)
        if target_color == fill_color:
            return  # Nothing to fill
        
        # Use a stack for flood fill (iterative)
        stack = [(start_x, start_y)]
        visited = set()
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited:
                continue
            if not self._is_in_bounds(x, y):
                continue
            if self._get_pixel_index(x, y) != target_color:
                continue
            
            visited.add((x, y))
            self._set_pixel(x, y, fill_color)
            
            # Add adjacent pixels
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))
    
    def _get_line_pixels(self, x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
        """Get pixels on a line using Bresenham's algorithm."""
        pixels = []
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        while True:
            if self._is_in_bounds(x, y):
                pixels.append((x, y))
            
            if x == x1 and y == y1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return pixels
    
    def _get_rect_pixels(self, x0: int, y0: int, x1: int, y1: int, filled: bool = False) -> list[tuple[int, int]]:
        """Get pixels for a rectangle (outline or filled)."""
        pixels = []
        
        # Normalize coordinates
        left = min(x0, x1)
        right = max(x0, x1)
        top = min(y0, y1)
        bottom = max(y0, y1)
        
        if filled:
            for y in range(top, bottom + 1):
                for x in range(left, right + 1):
                    if self._is_in_bounds(x, y):
                        pixels.append((x, y))
        else:
            # Top and bottom edges
            for x in range(left, right + 1):
                if self._is_in_bounds(x, top):
                    pixels.append((x, top))
                if self._is_in_bounds(x, bottom) and top != bottom:
                    pixels.append((x, bottom))
            # Left and right edges (excluding corners already added)
            for y in range(top + 1, bottom):
                if self._is_in_bounds(left, y):
                    pixels.append((left, y))
                if self._is_in_bounds(right, y) and left != right:
                    pixels.append((right, y))
        
        return pixels
    
    def _get_ellipse_pixels(self, x0: int, y0: int, x1: int, y1: int, filled: bool = False) -> list[tuple[int, int]]:
        """Get pixels for an ellipse (outline or filled) using midpoint algorithm."""
        pixels = []
        
        # Calculate center and radii
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        rx = abs(x1 - x0) // 2
        ry = abs(y1 - y0) // 2
        
        if rx == 0 or ry == 0:
            # Degenerate case: draw a line
            return self._get_line_pixels(x0, y0, x1, y1)
        
        # Use a set to track pixels (ellipse algorithm may add duplicates)
        pixel_set = set()
        
        # Midpoint ellipse algorithm
        rx2 = rx * rx
        ry2 = ry * ry
        
        # Region 1
        x = 0
        y = ry
        d1 = ry2 - rx2 * ry + 0.25 * rx2
        
        while ry2 * x < rx2 * y:
            if filled:
                # Fill horizontal line from -x to x
                for px in range(cx - x, cx + x + 1):
                    if self._is_in_bounds(px, cy + y):
                        pixel_set.add((px, cy + y))
                    if self._is_in_bounds(px, cy - y):
                        pixel_set.add((px, cy - y))
            else:
                # Add outline points
                for px, py in [(cx + x, cy + y), (cx - x, cy + y), 
                               (cx + x, cy - y), (cx - x, cy - y)]:
                    if self._is_in_bounds(px, py):
                        pixel_set.add((px, py))
            
            if d1 < 0:
                x += 1
                d1 += 2 * ry2 * x + ry2
            else:
                x += 1
                y -= 1
                d1 += 2 * ry2 * x - 2 * rx2 * y + ry2
        
        # Region 2
        d2 = ry2 * (x + 0.5) ** 2 + rx2 * (y - 1) ** 2 - rx2 * ry2
        
        while y >= 0:
            if filled:
                for px in range(cx - x, cx + x + 1):
                    if self._is_in_bounds(px, cy + y):
                        pixel_set.add((px, cy + y))
                    if self._is_in_bounds(px, cy - y):
                        pixel_set.add((px, cy - y))
            else:
                for px, py in [(cx + x, cy + y), (cx - x, cy + y),
                               (cx + x, cy - y), (cx - x, cy - y)]:
                    if self._is_in_bounds(px, py):
                        pixel_set.add((px, py))
            
            if d2 > 0:
                y -= 1
                d2 -= 2 * rx2 * y + rx2
            else:
                x += 1
                y -= 1
                d2 += 2 * ry2 * x - 2 * rx2 * y + rx2
        
        pixels = list(pixel_set)
        return pixels
    
    def _draw_shape(self, pixels: list[tuple[int, int]], color_index: int) -> None:
        """Draw a list of pixels with the given color."""
        for x, y in pixels:
            self._set_pixel(x, y, color_index)

    def on_mouse_down(self, event) -> None:
        """Handle mouse button press."""
        if not self._tileset:
            return
        
        # Convert terminal coordinates to pixel coordinates
        pixel_pos = self._terminal_to_pixel(event.x, event.y)
        if not pixel_pos:
            return
        
        pixel_x, pixel_y = pixel_pos
        
        # Ctrl+Click to select tile
        if event.ctrl:
            tile_w = self._tileset.tile_width
            tile_h = self._tileset.tile_height
            tiles_per_row = self._tileset.tiles_per_row or 1
            tile_col = pixel_x // tile_w
            tile_row = pixel_y // tile_h
            tile_idx = tile_row * tiles_per_row + tile_col
            if 0 <= tile_idx < len(self._tileset.tiles):
                self.scroll_to_tile(tile_idx)
                self.app.notify(f"Selected tile {tile_idx:02X}", severity="information")
            event.stop()
            return
        
        if self.current_tool == "eyedropper":
            # Sample color from canvas
            color_idx = self._get_pixel_index(pixel_x, pixel_y)
            self.current_color_index = color_idx
            self.app.notify(f"Picked color {color_idx}", severity="information")
            # Notify parent to update palette display
            self.post_message(self.ColorPicked(color_idx))
        
        elif self.current_tool == "pencil":
            # Only allow drawing in edit mode
            if not self.edit_mode:
                self.app.notify("Press 'd' to enter Edit mode for drawing", severity="warning")
                return
            
            # Start drawing
            self._is_drawing = True
            self._save_undo_state()
            self._set_pixel(pixel_x, pixel_y, self.current_color_index)
            self._last_draw_pos = (pixel_x, pixel_y)
            self.is_modified = True
            self.refresh()
        
        elif self.current_tool == "fill":
            # Flood fill
            if not self.edit_mode:
                self.app.notify("Press 'd' to enter Edit mode for drawing", severity="warning")
                return
            
            self._save_undo_state()
            self._flood_fill(pixel_x, pixel_y, self.current_color_index)
            self.is_modified = True
            self.refresh()
            self.app.notify("Fill complete", severity="information")
        
        elif self.current_tool in ("line", "rect", "ellipse"):
            # Start shape drawing
            if not self.edit_mode:
                self.app.notify("Press 'd' to enter Edit mode for drawing", severity="warning")
                return
            
            self._shape_start = (pixel_x, pixel_y)
            self._shape_preview = {(pixel_x, pixel_y)}
            self._is_drawing = True
            self.refresh()
        
        event.stop()
    
    def on_mouse_move(self, event) -> None:
        """Handle mouse movement (for drag drawing and shape preview)."""
        if not self._is_drawing or not self._tileset:
            return
        
        pixel_pos = self._terminal_to_pixel(event.x, event.y)
        if not pixel_pos:
            return
        
        pixel_x, pixel_y = pixel_pos
        
        if self.current_tool == "pencil":
            # Only draw if position changed
            if (pixel_x, pixel_y) != self._last_draw_pos:
                self._set_pixel(pixel_x, pixel_y, self.current_color_index)
                self._last_draw_pos = (pixel_x, pixel_y)
                self.refresh()
        
        elif self.current_tool in ("line", "rect", "ellipse") and self._shape_start:
            # Update shape preview
            x0, y0 = self._shape_start
            if self.current_tool == "line":
                self._shape_preview = set(self._get_line_pixels(x0, y0, pixel_x, pixel_y))
            elif self.current_tool == "rect":
                self._shape_preview = set(self._get_rect_pixels(x0, y0, pixel_x, pixel_y, filled=False))
            elif self.current_tool == "ellipse":
                self._shape_preview = set(self._get_ellipse_pixels(x0, y0, pixel_x, pixel_y, filled=False))
            self.refresh()
    
    def on_mouse_up(self, event) -> None:
        """Handle mouse button release."""
        if self.current_tool in ("line", "rect", "ellipse") and self._shape_start and self._shape_preview:
            # Draw the final shape
            pixel_pos = self._terminal_to_pixel(event.x, event.y)
            if pixel_pos:
                x0, y0 = self._shape_start
                pixel_x, pixel_y = pixel_pos
                
                self._save_undo_state()
                
                if self.current_tool == "line":
                    pixels = self._get_line_pixels(x0, y0, pixel_x, pixel_y)
                elif self.current_tool == "rect":
                    pixels = self._get_rect_pixels(x0, y0, pixel_x, pixel_y, filled=False)
                elif self.current_tool == "ellipse":
                    pixels = self._get_ellipse_pixels(x0, y0, pixel_x, pixel_y, filled=False)
                else:
                    pixels = []
                
                self._draw_shape(pixels, self.current_color_index)
                self.is_modified = True
                self.refresh()
        
        if self._is_drawing:
            self.post_message(self.PixelModified(self.current_tile_index))

        self._is_drawing = False
        self._last_draw_pos = None
        self._shape_start = None
        self._shape_preview = set()
    
    # Custom message for color picking
    class ColorPicked(Message):
        """Message sent when a color is picked from the canvas."""
        def __init__(self, color_index: int):
            super().__init__()
            self.color_index = color_index

    class PixelModified(Message):
        """Message sent when pixels are modified."""
        def __init__(self, tile_index: int):
            super().__init__()
            self.tile_index = tile_index


class PaletteBar(Widget):
    """Interactive palette bar for selecting colors.
    
    Displays palette colors as clickable swatches.
    Click to select a color for drawing.
    """
    
    DEFAULT_CSS = """
    PaletteBar {
        height: 3;
        background: $panel;
        padding: 0 1;
    }
    """
    
    selected_index: reactive[int] = reactive(1)
    
    def __init__(
        self,
        palette: SNESPalette | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._palette = palette
        self._swatch_width = 2  # Chars per color swatch
    
    @property
    def palette(self) -> SNESPalette | None:
        return self._palette
    
    @palette.setter
    def palette(self, value: SNESPalette | None) -> None:
        self._palette = value
        self.refresh()
    
    def render(self) -> Text:
        """Render the palette as colored swatches."""
        if not self._palette:
            return Text("[dim]No palette[/dim]")
        
        text = Text()
        text.append("Palette: ")
        
        num_colors = min(16, self._palette.colors_per_palette)
        for i in range(num_colors):
            r, g, b = self._palette.get_color(0, i)
            
            if i == self.selected_index:
                # Highlight selected with brackets and bold
                text.append("[", style="bold white")
                text.append(f"{i:X}", style=f"bold white on rgb({r},{g},{b})")
                text.append("]", style="bold white")
            else:
                # Regular swatch - 2 chars wide
                text.append("  ", style=f"on rgb({r},{g},{b})")
        
        return text
    
    def on_click(self, event: Click) -> None:
        """Handle click to select a color."""
        if not self._palette:
            return
        
        # Calculate which swatch was clicked
        # "Palette: " is 9 chars, then 2 chars per swatch (or 3 for selected with brackets)
        x = event.x
        prefix_len = 9  # "Palette: "
        
        if x < prefix_len:
            return
        
        # Account for the variable width of selected swatch
        click_pos = x - prefix_len
        
        # Calculate swatch index based on position
        # Each swatch is 2 chars wide, except selected which is 3 (brackets + hex)
        num_colors = min(16, self._palette.colors_per_palette)
        
        current_pos = 0
        for i in range(num_colors):
            if i == self.selected_index:
                swatch_width = 3  # [X]
            else:
                swatch_width = 2  # "  "
            
            if current_pos <= click_pos < current_pos + swatch_width:
                # Clicked on this swatch
                self.selected_index = i
                self.post_message(self.ColorSelected(i))
                return
            
            current_pos += swatch_width
    
    class ColorSelected(Message):
        """Message sent when a color is selected from the palette."""
        def __init__(self, color_index: int):
            super().__init__()
            self.color_index = color_index


class TileEditorPanel(Static):
    """Panel for displaying and editing SNES tile graphics.
    
    Contains the pixel canvas, palette display, and status information.
    Similar structure to CodeViewer but for graphics.
    """
    
    DEFAULT_CSS = """
    TileEditorPanel {
        width: 100%;
        height: 100%;
        background: $surface;
    }
    
    TileEditorPanel > Horizontal {
        height: 1fr;
        width: 100%;
    }
    
    TileEditorPanel #pixel-canvas {
        width: 70%;
        height: 100%;
    }
    
    TileEditorPanel #assembly-preview {
        width: 30%;
        height: 100%;
    }
    
    TileEditorPanel > #tile-palette-bar {
        dock: bottom;
        height: 1;
        background: $panel;
    }
    
    TileEditorPanel > #tile-status-bar {
        dock: bottom;
        height: 1;
        background: $primary 30%;
        padding: 0 1;
    }
    """
    
    file_path: reactive[Path | None] = reactive(None)
    
    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._tileset: SNESTileset | None = None
    
    def compose(self) -> ComposeResult:
        yield Label("", id="tile-status-bar")
        with Horizontal():
            yield PixelCanvas(id="pixel-canvas")
            yield AssemblyPreviewPanel(id="assembly-preview")
        yield PaletteBar(id="tile-palette-bar")
    
    def watch_file_path(self, file_path: Path | None) -> None:
        """Load and display image when path changes."""
        status = self.query_one("#tile-status-bar", Label)
        palette_bar = self.query_one("#tile-palette-bar", PaletteBar)
        canvas = self.query_one("#pixel-canvas", PixelCanvas)
        
        if file_path is None:
            status.update("[dim]Select an image file to edit[/dim]")
            palette_bar.palette = None
            canvas.tileset = None
            return
        
        if not HAS_PIL:
            status.update("[red]PIL/Pillow not installed - cannot load images[/red]")
            return
        
        if not file_path.exists():
            status.update(f"[red]File not found: {file_path}[/red]")
            return
        
        # Load the image as a tileset
        self._tileset = SNESTileset(tile_width=8, tile_height=8, bpp=4)
        if self._tileset.load_from_path(file_path):
            canvas.tileset = self._tileset
            palette_bar.palette = self._tileset.palette
            palette_bar.selected_index = canvas.current_color_index
            
            # Update status
            tile_count = self._tileset.tile_count
            w, h = self._tileset.image_width, self._tileset.image_height
            status.update(
                f"📄 {file_path.name} | {w}×{h}px | {tile_count} tiles | "
                f"Zoom: {canvas.zoom}x | [dim]G=grid, +/-=zoom[/dim]"
            )
            self._update_preview()
        else:
            status.update(f"[red]Failed to load: {file_path}[/red]")
            canvas.tileset = None
            palette_bar.palette = None
    
    def on_palette_bar_color_selected(self, event: PaletteBar.ColorSelected) -> None:
        """Handle color selection from palette bar."""
        canvas = self.query_one("#pixel-canvas", PixelCanvas)
        canvas.current_color_index = event.color_index
        self._update_status()
    
    def on_pixel_canvas_color_picked(self, event: PixelCanvas.ColorPicked) -> None:
        """Update palette bar when color is picked from canvas (eyedropper)."""
        palette_bar = self.query_one("#tile-palette-bar", PaletteBar)
        palette_bar.selected_index = event.color_index
        self._update_status()

    def on_pixel_canvas_pixel_modified(self, message: PixelCanvas.PixelModified) -> None:
        self._update_preview()
        
    def on_pixel_canvas_tile_navigated(self, message: PixelCanvas.TileNavigated) -> None:
        self._update_preview()
        
    def _update_preview(self) -> None:
        canvas = self.query_one("#pixel-canvas", PixelCanvas)
        preview = self.query_one("#assembly-preview", AssemblyPreviewPanel)
        if canvas.tileset:
             tile = canvas.tileset.get_tile(canvas.current_tile_index)
             preview.update_preview(tile, canvas.tileset.palette, canvas.current_tile_index)
    
    def on_pixel_canvas_tile_navigated(self, event: PixelCanvas.TileNavigated) -> None:
        """Update status bar when tile navigation occurs."""
        self._update_status()
    
    def _update_status(self) -> None:
        """Refresh the status bar display."""
        canvas = self.query_one("#pixel-canvas", PixelCanvas)
        status = self.query_one("#tile-status-bar", Label)
        
        if not self._tileset:
            return
        
        tile_count = self._tileset.tile_count
        w, h = self._tileset.image_width, self._tileset.image_height
        modified = " [yellow]●[/yellow]" if canvas.is_modified else ""
        
        # Handle unsaved new tilesets
        filename = self.file_path.name if self.file_path else "[New Tileset]"
        
        status.update(
            f"📄 {filename}{modified} | {w}×{h}px | {tile_count} tiles | "
            f"Zoom: {canvas.zoom}x | Tile: {canvas.current_tile_index:02X} | "
            f"[dim]G=grid, Tab=next tile[/dim]"
        )
    
    def save_image(self) -> bool:
        """Save the current image back to disk.
        
        Returns:
            True if save succeeded, False otherwise
        """
        if not HAS_PIL or not self._tileset or not self.file_path:
            return False
        
        canvas = self.query_one("#pixel-canvas", PixelCanvas)
        
        # Reconstruct PIL Image from tiles
        from PIL import Image
        
        w = self._tileset.image_width
        h = self._tileset.image_height
        tile_w = self._tileset.tile_width
        tile_h = self._tileset.tile_height
        tiles_per_row = self._tileset.tiles_per_row or 1
        
        # Create RGB image
        img = Image.new("RGB", (w, h))
        
        for tile_idx, tile in enumerate(self._tileset.tiles):
            tile_row = tile_idx // tiles_per_row
            tile_col = tile_idx % tiles_per_row
            
            base_x = tile_col * tile_w
            base_y = tile_row * tile_h
            
            for y in range(tile_h):
                for x in range(tile_w):
                    color_idx = tile.get_pixel(x, y)
                    r, g, b = self._tileset.palette.get_color(0, color_idx)
                    px_x = base_x + x
                    px_y = base_y + y
                    if px_x < w and px_y < h:
                        img.putpixel((px_x, px_y), (r, g, b))
        
        # Save with same format as original
        try:
            img.save(self.file_path)
            canvas.is_modified = False
            self._update_status()
            return True
        except Exception as e:
            self.app.notify(f"Save failed: {e}", severity="error")
            return False
