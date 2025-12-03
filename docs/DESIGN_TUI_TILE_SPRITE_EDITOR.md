# SNES-IDE TUI Tile and Sprite Editor - Design Document

**Version:** 1.0  
**Date:** December 3, 2025  
**Status:** Proposal  

---

## Executive Summary

This document proposes building an SNES tile and sprite editor directly into the SNES-IDE TUI (Textual-based terminal interface). The editor would provide a terminal-native way to create, edit, and export SNES graphics assets without requiring external GUI applications. This builds on existing Qt-based functionality in the IDE while offering the benefits of terminal accessibility, SSH compatibility, and integration with the TUI's project browser and command palette.

---

## Table of Contents

1. [Motivation](#1-motivation)
2. [Technical Foundation](#2-technical-foundation)
3. [SNES Graphics Constraints](#3-snes-graphics-constraints)
4. [Architecture Overview](#4-architecture-overview)
5. [Core Components](#5-core-components)
6. [User Interface Design](#6-user-interface-design)
7. [Data Flow and Pipelines](#7-data-flow-and-pipelines)
8. [Integration Points](#8-integration-points)
9. [Technical Challenges and Mitigations](#9-technical-challenges-and-mitigations)
10. [Implementation Phases](#10-implementation-phases)
11. [Dependencies](#11-dependencies)
12. [Feasibility Assessment](#12-feasibility-assessment)
13. [References](#13-references)

---

## 1. Motivation

### 1.1 Why Build This?

1. **Terminal-First Development**: Many SNES developers prefer terminal workflows. A TUI editor enables graphics work over SSH, in screen/tmux sessions, and on headless servers.

2. **Unified Workflow**: The TUI already provides code browsing, tool installation, and project management. Adding graphics editing creates a complete development environment.

3. **Learning from textual-paint**: The textual-paint project (1.1k stars, MIT licensed) has proven that full-featured image editing is possible in a terminal, with undo/redo, tool palettes, color pickers, and file format support.

4. **SNES-Specific Features**: Unlike generic editors, a purpose-built tool can enforce SNES constraints (palette limits, tile sizes, BPP modes) at edit-time rather than conversion-time.

### 1.2 Similar Existing Functionality

The Qt-based interface already provides:
- `gfx-png-bmp-snes-converter.py`: Converts images to SNES tile format via superfamiconv
- `gfx-tmx-tmj-converter.py`: Converts Tiled TMX maps to JSON
- `gfx-png-bmp-editor.py`: Launches LibreSprite for sprite editing
- `gfx-tmx-editor.py`: Launches Tiled for map editing

---

## 2. Technical Foundation

### 2.1 Key Libraries and Inspiration

| Library | Purpose | Key Features to Leverage |
|---------|---------|--------------------------|
| **textual-paint** | Full paint program in terminal | Canvas with undo/redo, tool palette, color picker, zoom, file dialogs |
| **rich-pixels** | Render images as terminal "pixels" | `Pixels.from_image()`, ASCII art mapping, Textual integration |
| **textual-imageview** | View images in terminal | `ImageView` renderable, pan/zoom, mouse interaction |
| **pytmx** | Parse Tiled TMX files | Load tilesets, layers, objects, properties, animations |
| **Pillow (PIL)** | Image manipulation | Indexed color, palette operations, resize, crop, pixel access |

### 2.2 Terminal Pixel Rendering

Terminal "pixels" use half-block characters (▀, ▄) or full blocks (█) with 24-bit color. Each character cell represents 2 vertical pixels. This means:
- 8x8 SNES tiles → 8x4 terminal characters
- 16x16 sprites → 16x8 terminal characters
- At zoom level 1, each SNES pixel = 1 half-block (very small)
- At zoom level 8, each SNES pixel = 8x4 character blocks (very readable)

### 2.3 Textual Framework Capabilities

Textual provides:
- **Widgets**: Custom drawing with `render()` or Rich renderables
- **Mouse events**: Click, drag, scroll, hover with cell coordinates
- **Keyboard bindings**: Shortcuts and command palette integration
- **CSS styling**: Consistent theming
- **Workers**: Async file I/O and conversion tasks
- **Screens**: Modal dialogs for color pickers, file dialogs, etc.

---

## 3. SNES Graphics Constraints

### 3.1 Color Palette Restrictions

| Mode | Palettes | Colors/Palette | Total Colors |
|------|----------|----------------|--------------|
| BG Mode 0 | 8 | 4 | 32 |
| BG Mode 1 | 8 | 16 | 128 |
| BG Mode 3 | 1 | 256 | 256 |
| Sprites | 8 | 16 | 128 |

- All colors are 15-bit RGB (5 bits per channel, 32768 possible colors)
- Color index 0 is always transparent for sprites

### 3.2 Tile Constraints

- **Tile sizes**: 8x8 (standard), 16x16 (large sprites), Mode 7 tiles
- **BPP modes**: 2bpp (4 colors), 4bpp (16 colors), 8bpp (256 colors)
- **Maximum tiles**: Limited by VRAM (typically 512-1024 unique tiles per layer)
- **Tile flipping**: Hardware supports horizontal/vertical flip

### 3.3 Tilemap Constraints

- Maximum tilemap size: 32x32, 64x32, 32x64, or 64x64 tiles
- Each tilemap entry: tile index + palette + flip flags + priority

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     SNES-IDE TUI (tools_browser.py)             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│  │ Project Tree │  │  Code Viewer  │  │  Graphics Editor    │  │
│  │              │  │               │  │  ┌───────────────┐  │  │
│  │              │  │               │  │  │ Canvas Widget │  │  │
│  │              │  │               │  │  │ (PixelCanvas) │  │  │
│  │              │  │               │  │  └───────────────┘  │  │
│  │              │  │               │  │  ┌───────────────┐  │  │
│  │              │  │               │  │  │ Tool Palette  │  │  │
│  │              │  │               │  │  └───────────────┘  │  │
│  │              │  │               │  │  ┌───────────────┐  │  │
│  │              │  │               │  │  │ Color Palette │  │  │
│  │              │  │               │  │  └───────────────┘  │  │
│  └──────────────┘  └───────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                        Core Libraries                            │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌───────────┐ │
│  │ SNESPalette │ │  SNESTile    │ │ SNESTilemap│ │ SNESSprite│ │
│  └─────────────┘ └──────────────┘ └────────────┘ └───────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     File I/O & Conversion                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────────┐ │
│  │ Pillow (images) │ │ pytmx (tilemaps)│ │ superfamiconv CLI │ │
│  └─────────────────┘ └─────────────────┘ └───────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Core Components

### 5.1 SNESPalette Class

Manages SNES 15-bit RGB palettes with conversion to/from 24-bit RGB for display.

```python
class SNESPalette:
    """SNES palette management with 15-bit RGB support."""
    
    def __init__(self, bpp: int = 4, num_palettes: int = 8):
        self.bpp = bpp  # 2, 4, or 8
        self.colors_per_palette = 2 ** bpp
        self.num_palettes = num_palettes
        self.palettes: list[list[tuple[int, int, int]]] = []
    
    def rgb24_to_snes(self, r: int, g: int, b: int) -> int:
        """Convert 24-bit RGB to 15-bit SNES color."""
        return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
    
    def snes_to_rgb24(self, color: int) -> tuple[int, int, int]:
        """Convert 15-bit SNES color to 24-bit RGB."""
        r = (color & 0x1F) << 3
        g = ((color >> 5) & 0x1F) << 3
        b = ((color >> 10) & 0x1F) << 3
        return (r, g, b)
    
    def from_image(self, image: Image.Image) -> None:
        """Extract palette from indexed PNG."""
        pass
    
    def to_snes_data(self) -> bytes:
        """Export as raw SNES palette data."""
        pass
```

### 5.2 SNESTile Class

Represents a single tile with pixel data in indexed color format.

```python
class SNESTile:
    """SNES tile representation with BPP support."""
    
    def __init__(self, width: int = 8, height: int = 8, bpp: int = 4):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.pixels: list[list[int]] = [[0] * width for _ in range(height)]
    
    def get_pixel(self, x: int, y: int) -> int:
        """Get palette index at position."""
        return self.pixels[y][x]
    
    def set_pixel(self, x: int, y: int, color_index: int) -> None:
        """Set palette index at position, enforcing BPP limit."""
        max_index = (2 ** self.bpp) - 1
        self.pixels[y][x] = min(color_index, max_index)
    
    def flip_horizontal(self) -> 'SNESTile':
        """Return horizontally flipped copy."""
        pass
    
    def flip_vertical(self) -> 'SNESTile':
        """Return vertically flipped copy."""
        pass
    
    def to_snes_data(self) -> bytes:
        """Export as raw SNES tile data (planar format)."""
        pass
    
    def from_snes_data(self, data: bytes) -> None:
        """Import from raw SNES tile data."""
        pass
```

### 5.3 SNESTileset Class

Collection of tiles with shared palette, typically loaded from an image.

```python
class SNESTileset:
    """Collection of SNES tiles from a tileset image."""
    
    def __init__(self, tile_width: int = 8, tile_height: int = 8):
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.tiles: list[SNESTile] = []
        self.palette: SNESPalette = SNESPalette()
    
    def from_image(self, image: Image.Image) -> None:
        """Split image into tiles, extracting palette."""
        pass
    
    def get_tile(self, index: int) -> SNESTile:
        """Get tile by index."""
        return self.tiles[index]
    
    def find_duplicate_tiles(self) -> dict[int, int]:
        """Find tiles that are duplicates (including flipped)."""
        pass
    
    def optimize(self) -> 'SNESTileset':
        """Remove duplicate tiles, returning mapping."""
        pass
```

### 5.4 SNESTilemap Class

Grid of tile references with metadata (palette, flip, priority).

```python
class SNESTilemap:
    """SNES tilemap (background layer)."""
    
    def __init__(self, width: int = 32, height: int = 32):
        self.width = width
        self.height = height
        self.entries: list[list[TilemapEntry]] = []
    
    @dataclass
    class TilemapEntry:
        tile_index: int = 0
        palette: int = 0
        flip_h: bool = False
        flip_v: bool = False
        priority: bool = False
    
    def from_tmx(self, tmx_path: str) -> None:
        """Load from Tiled TMX file using pytmx."""
        pass
    
    def to_snes_data(self) -> bytes:
        """Export as raw SNES tilemap data."""
        pass
```

### 5.5 PixelCanvas Widget

The main editing widget, inspired by textual-paint's canvas.

```python
class PixelCanvas(Widget):
    """Terminal-based pixel canvas for SNES graphics editing."""
    
    BINDINGS = [
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+y", "redo", "Redo"),
        Binding("ctrl+shift+z", "redo", "Redo"),
    ]
    
    def __init__(self, width: int, height: int, zoom: int = 4):
        super().__init__()
        self.canvas_width = width
        self.canvas_height = height
        self.zoom = zoom  # Terminal chars per pixel
        self.tileset: SNESTileset | None = None
        self.current_tile: int = 0
        self.current_palette: int = 0
        self.current_tool: str = "pencil"
        self.undo_stack: list[CanvasState] = []
        self.redo_stack: list[CanvasState] = []
    
    def render(self) -> RenderResult:
        """Render canvas using rich-pixels or custom half-blocks."""
        # Use half-block characters (▀▄█) with foreground/background colors
        # to render 2 vertical pixels per character cell
        pass
    
    def on_mouse_down(self, event: MouseDown) -> None:
        """Handle drawing start."""
        pass
    
    def on_mouse_move(self, event: MouseMove) -> None:
        """Handle drawing while mouse held."""
        pass
    
    def action_undo(self) -> None:
        """Restore previous canvas state."""
        if self.undo_stack:
            self.redo_stack.append(self._capture_state())
            state = self.undo_stack.pop()
            self._restore_state(state)
            self.refresh()
    
    def action_redo(self) -> None:
        """Restore next canvas state."""
        if self.redo_stack:
            self.undo_stack.append(self._capture_state())
            state = self.redo_stack.pop()
            self._restore_state(state)
            self.refresh()
    
    def _capture_state(self) -> CanvasState:
        """Capture current canvas state for undo."""
        pass
    
    def _restore_state(self, state: CanvasState) -> None:
        """Restore canvas from captured state."""
        pass
```

### 5.6 Rendering Pipeline

```python
def render_tile_to_segments(
    tile: SNESTile, 
    palette: SNESPalette, 
    palette_index: int,
    zoom: int = 1
) -> list[Segment]:
    """Convert a tile to Rich Segments for terminal display.
    
    Uses half-block characters to display 2 vertical pixels per cell.
    At zoom=1, an 8x8 tile becomes 8 chars wide x 4 chars tall.
    At zoom=4, an 8x8 tile becomes 32 chars wide x 16 chars tall.
    """
    segments = []
    colors = palette.palettes[palette_index]
    
    for y in range(0, tile.height, 2):
        row_segments = []
        for x in range(tile.width):
            for z in range(zoom):
                # Top pixel = foreground, bottom pixel = background
                top_idx = tile.get_pixel(x, y)
                bot_idx = tile.get_pixel(x, y + 1) if y + 1 < tile.height else 0
                
                top_color = colors[top_idx]
                bot_color = colors[bot_idx]
                
                # Half-block: foreground is top, background is bottom
                style = Style(
                    color=Color.from_rgb(*top_color),
                    bgcolor=Color.from_rgb(*bot_color)
                )
                row_segments.append(Segment("▀", style))
        
        # Repeat row for vertical zoom
        for _ in range(zoom // 2 or 1):
            segments.extend(row_segments)
            segments.append(Segment.line())
    
    return segments
```

---

## 6. User Interface Design

### 6.1 Main Editor Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ SNES Tile Editor - project/assets/player.png                    [×] │
├────────────┬─────────────────────────────────────────────────────────┤
│ Tools      │                                                         │
│ ┌────────┐ │                    Canvas Area                          │
│ │ ✏ Pen  │ │                                                         │
│ │ 🪣 Fill │ │    ████████████████████████████████████                │
│ │ ▭ Select│ │    ██  ████████████  ██████████████                    │
│ │ ◯ Ellip│ │    ████████████████████████████████                    │
│ │ ▭ Rect │ │    ██████████  ████████  ██████████                    │
│ │ ╱ Line │ │    ████████████████████████████████████                │
│ │ 🔍 Zoom │ │    ██████████████████████████████████                  │
│ │ 🎨 Pick │ │                                                        │
│ └────────┘ │                                                         │
│            │                                                         │
│ Tileset    │─────────────────────────────────────────────────────────│
│ ┌────────┐ │ Palette: [1▼]  BPP: [4▼]  Tile: 3/64  Grid: [✓]        │
│ │▓▓░░▓▓░░│ ├─────────────────────────────────────────────────────────│
│ │░░▓▓░░▓▓│ │ ▓ ▓ ░ ░ ▓ ░ ▓ ▓ ░ ░ ▓ ░ ▓ ▓ ░ ░  Current Colors       │
│ │▓▓░░▓▓░░│ │ [0][1][2][3][4][5][6][7][8][9][A][B][C][D][E][F]       │
│ │░░▓▓░░▓▓│ └─────────────────────────────────────────────────────────│
│ └────────┘ │ Status: Ready | Zoom: 4x | Position: (12, 8)           │
└────────────┴─────────────────────────────────────────────────────────┘
```

### 6.2 Component Breakdown

#### 6.2.1 Tool Palette (Left Sidebar)
- **Pencil**: Single pixel drawing
- **Fill**: Flood fill with tolerance
- **Rectangle Select**: Marquee selection
- **Ellipse**: Draw ellipses/circles
- **Rectangle**: Draw rectangles
- **Line**: Draw straight lines
- **Zoom**: Magnify canvas regions
- **Color Picker**: Sample colors from canvas

#### 6.2.2 Canvas Area (Center)
- Main editing surface using half-block rendering
- Grid overlay toggle for tile boundaries
- Selection highlight with dashed border
- Cursor showing current brush/tool

#### 6.2.3 Tileset View (Left, Below Tools)
- Thumbnail grid of all tiles in tileset
- Click to select tile for editing
- Scroll for large tilesets
- Highlight for currently selected tile

#### 6.2.4 Palette Bar (Bottom)
- 16 colors (for 4bpp) or 4 colors (for 2bpp)
- Left-click = foreground, Right-click = background
- Double-click opens color editor dialog
- Palette selector dropdown (0-7)

#### 6.2.5 Status Bar
- Current mode and tool
- Zoom level
- Cursor position in tile/pixel coordinates
- Modified indicator

### 6.3 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `P` | Pencil tool |
| `B` | Brush tool |
| `F` | Fill tool |
| `S` | Select tool |
| `L` | Line tool |
| `R` | Rectangle tool |
| `E` | Ellipse tool |
| `I` | Color picker (eyedropper) |
| `G` | Toggle grid |
| `+` / `=` | Zoom in |
| `-` / `_` | Zoom out |
| `0` | Reset zoom to 100% |
| `1`-`8` | Select palette 1-8 |
| `Arrow Keys` | Move canvas/selection |
| `Shift+Arrow` | Pan canvas (when zoomed) |
| `Space+Drag` | Pan canvas |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+E` | Export to SNES format |
| `Ctrl+O` | Open file |
| `Ctrl+N` | New tileset |
| `Ctrl+P` | Command palette |
| `Tab` | Next tile in tileset |
| `Shift+Tab` | Previous tile in tileset |
| `Escape` | Return to TUI main view |

### 6.4 Dialogs and Modals

#### 6.4.1 Color Editor Dialog
- HSV/RGB sliders
- SNES 15-bit color preview (shows quantization)
- 32768 color grid picker
- Hex input with SNES format support

#### 6.4.2 New Tile/Tileset Dialog
- Tile size: 8x8, 16x16, 32x32
- BPP mode: 2, 4, 8
- Tileset dimensions (tiles wide × tiles tall)
- Initial palette choice

#### 6.4.3 Export Dialog
- Output format: Raw, ASM include, C header
- Tile data filename
- Palette data filename  
- Tilemap data filename (if applicable)
- superfamiconv options pass-through

---

## 7. Data Flow and Pipelines

### 7.1 Image Import Pipeline

```
PNG/BMP File
     │
     ▼
┌─────────────┐
│ Pillow Load │ ◄── Validate dimensions, color mode
└─────────────┘
     │
     ▼
┌──────────────────┐
│ Extract Palette  │ ◄── If indexed: use existing
│                  │ ◄── If RGB: quantize to palette
└──────────────────┘
     │
     ▼
┌────────────────┐
│ Split to Tiles │ ◄── 8x8 or 16x16 grid
└────────────────┘
     │
     ▼
┌────────────────────┐
│ Create SNESTileset │
└────────────────────┘
     │
     ▼
   Editor
```

### 7.2 TMX Import Pipeline

```
TMX File (Tiled Map)
     │
     ▼
┌─────────────┐
│ pytmx Load  │ ◄── Parse XML, load tilesets, layers
└─────────────┘
     │
     ├──── Tileset Images ────┐
     │                        ▼
     │              ┌─────────────────┐
     │              │ Create Tileset  │
     │              └─────────────────┘
     │                        │
     ▼                        ▼
┌─────────────────┐   ┌───────────────┐
│ Parse Tile      │   │ SNESTileset   │
│ Layers          │   └───────────────┘
└─────────────────┘           │
     │                        │
     ▼                        │
┌─────────────────┐           │
│ Create Tilemap  │◄──────────┘
│ (SNESTilemap)   │
└─────────────────┘
     │
     ▼
   Editor
```

### 7.3 Export Pipeline

```
Editor State
     │
     ├─── Tiles ─────┬─── Palette ────┬─── Tilemap ───┐
     ▼               ▼                ▼                │
┌──────────┐  ┌───────────┐  ┌─────────────────┐     │
│ SNESTile │  │ SNESPalete│  │ SNESTilemap     │     │
│ to bytes │  │ to bytes  │  │ (optional)      │     │
└──────────┘  └───────────┘  └─────────────────┘     │
     │               │                │               │
     ▼               ▼                ▼               │
┌────────────────────────────────────────────────────┐
│              superfamiconv CLI                      │
│  (or native Python export if simpler)              │
└────────────────────────────────────────────────────┘
     │
     ├─── tiles.chr (raw tile data)
     ├─── palette.pal (raw palette)
     ├─── tilemap.bin (raw map data)
     ├─── tiles.asm (optional assembly include)
     └─── tiles.h (optional C header)
```

---

## 8. Integration Points

### 8.1 TUI Project Browser Integration

- **Open from file tree**: Click `.png`, `.bmp`, `.tmx` files to open in editor
- **Context menu**: "Edit with Tile Editor" option for graphics files
- **Auto-refresh**: Reload tileset when file changes externally

### 8.2 Command Palette Integration

Commands added to the TUI command palette:

| Command | Description |
|---------|-------------|
| `New Tile` | Create new blank tile |
| `New Tileset` | Create new tileset from dimensions |
| `Open Image` | Open PNG/BMP as tileset |
| `Open TMX` | Open Tiled map |
| `Save` | Save current work |
| `Export SNES` | Export to SNES-native formats |
| `Import Palette` | Load palette from file |
| `Export Palette` | Save palette to file |
| `Optimize Tiles` | Remove duplicate tiles |
| `Convert BPP` | Change color depth |

### 8.3 Existing Script Integration

The editor can call existing conversion scripts:
- Use `superfamiconv` for validated SNES format export
- Fall back to Python-native export for simpler cases
- Integrate with `gfx-tmx-tmj-converter` for Tiled interop
- Leverage existing tool installation system from tools_browser.py
- Share palette and tileset data structures with Qt-based converters for consistency

### 8.4 Editor State Management

The editor should integrate with the TUI's existing patterns:
- Use Textual's `Screen` class for the editor as a modal/full-screen view
- Return to project browser when pressing Escape
- Store recently opened files in TUI session state
- Support opening multiple files in tabs (future enhancement)
- Broadcast file change events for auto-refresh in project tree

---

## 9. Technical Challenges and Mitigations

### 9.1 Terminal Color Limitations

**Challenge**: Some terminals only support 256 colors, not true color (24-bit).

**Mitigations**:
- Detect terminal capabilities using `$COLORTERM` environment variable
- For 256-color terminals, snap SNES colors to nearest terminal color
- For true color terminals, display exact SNES colors (upscaled from 15-bit)
- Show warning when terminal colors don't match SNES colors accurately

### 9.2 Canvas Size vs Terminal Size

**Challenge**: Large tilesets (256x256 pixels) may not fit on screen.

**Mitigations**:
- Scrollable canvas with mouse drag and keyboard navigation
- Zoom levels from 1x (tiny) to 8x (large)
- Minimap showing viewport position in large images
- "Fit to window" zoom option

### 9.3 Mouse Precision

**Challenge**: Each terminal character = 2 pixels vertically. Sub-cell precision is hard.

**Mitigations**:
- textual-paint solves this by tracking sub-character positions
- Use half-block rendering (▀▄) which naturally maps to 2 vertical pixels
- At high zoom, precision becomes a non-issue
- Keyboard arrow keys for fine positioning

### 9.4 Performance with Large Tilesets

**Challenge**: Rendering hundreds of tiles with color conversion may be slow.

**Mitigations**:
- Cache rendered tiles as Rich Segments
- Only re-render dirty regions (tiles that changed)
- Use `@lru_cache` for color conversion functions
- Lazy-load tiles outside the viewport

### 9.5 Undo/Redo Memory

**Challenge**: Storing full canvas state for each action uses memory.

**Mitigations**:
- Store diffs (changed pixels only) rather than full states
- Limit undo stack size (e.g., 100 steps)
- Compress undo states using run-length encoding
- Consider per-tile undo for tileset editing

### 9.6 Browser/Web Mode Compatibility

**Challenge**: Textual web mode has some limitations with mouse precision and color rendering.

**Mitigations**:
- Test rendering in both terminal and web modes
- Use standard Textual widgets where possible
- Provide fallback for any browser-incompatible features
- Note: Based on existing SNES-IDE TUI experience, avoid PTY-based interactions (like textual-terminal)
- All editing operations must work with keyboard-only input for full web compatibility

### 9.7 Data Loss Prevention

**Challenge**: User might accidentally close editor or crash without saving.

**Mitigations**:
- Auto-save to temporary file every N operations
- Warn on exit if unsaved changes exist
- Implement crash recovery with session restoration
- Save undo history to enable session recovery
- Modified indicator in status bar and title

---

## 10. Implementation Phases

### Phase 1: Core Rendering (2-3 weeks)

**Deliverables**:
1. `SNESPalette` class with 15-bit ↔ 24-bit conversion
2. `SNESTile` class with pixel get/set
3. Basic `PixelCanvas` widget with read-only display
4. Half-block rendering pipeline
5. Load PNG/BMP and display as tiles

**Validation**:
- Can display an indexed PNG with correct colors
- Zoom works (1x, 2x, 4x, 8x)
- Grid overlay toggle works

### Phase 2: Basic Editing (2-3 weeks)

**Deliverables**:
1. Pencil tool with click and drag
2. Color picker (click palette, sample from canvas)
3. Undo/redo (full canvas state)
4. Save/load PNG (preserving palette)

**Validation**:
- Can draw pixels on canvas
- Can undo/redo 10+ operations
- Can save and reload work

### Phase 3: Tileset Management (2 weeks)

**Deliverables**:
1. `SNESTileset` class
2. Tileset view panel with tile selection
3. Navigate between tiles
4. Split image into tiles on load
5. New tileset dialog

**Validation**:
- Can load a sprite sheet and edit individual tiles
- Can create new tileset with specified dimensions

### Phase 4: Additional Tools (2 weeks)

**Deliverables**:
1. Fill tool (flood fill)
2. Rectangle and ellipse tools (outline and filled)
3. Line tool
4. Selection tool (cut/copy/paste)
5. Flip and rotate operations

**Validation**:
- All tools work with undo/redo
- Selection can be moved and pasted

### Phase 5: SNES Export (1-2 weeks)

**Deliverables**:
1. Export to raw tile data (planar format)
2. Export palette data
3. superfamiconv integration for validated export
4. ASM and C header generation options

**Validation**:
- Exported data can be assembled into working SNES ROM
- Round-trip: export → import in SNES emulator → looks correct

### Phase 6: Tilemap Support (2-3 weeks)

**Deliverables**:
1. `SNESTilemap` class
2. pytmx integration for TMX loading
3. Tilemap editor mode (place tiles on grid)
4. Export tilemap data
5. Layer management (future)

**Validation**:
- Can load Tiled TMX and display correctly
- Can place tiles and export working tilemap

### Phase 7: Polish and Integration (1-2 weeks)

**Deliverables**:
1. Command palette integration
2. File browser integration (open files in editor)
3. Keyboard shortcut refinement
4. Status bar and help
5. Documentation
6. Auto-save and crash recovery
7. Web mode testing and compatibility fixes
8. Performance optimization and profiling

**Validation**:
- Smooth workflow for common tasks
- No crashes or data loss bugs
- Works in both terminal and web modes
- Can recover from unexpected exit

---

## 11. Dependencies

### 11.1 Required (Already in Project)

| Package | Version | Purpose |
|---------|---------|---------|
| `textual` | >=0.40.0 | TUI framework |
| `rich` | >=13.0.0 | Terminal rendering |
| `Pillow` | >=10.0.0 | Image loading/manipulation |

### 11.2 To Add

| Package | Version | Purpose |
|---------|---------|---------|
| `rich-pixels` | >=3.0.1 | Image-to-terminal rendering |
| `pytmx` | >=3.32 | Tiled TMX parsing |
| `textual-canvas` | >=0.2.0 | Optional: Higher-level canvas widget (if available) |

### 11.3 Optional (External Tools)

| Tool | Purpose |
|------|---------|
| `superfamiconv` | SNES format validation and export |

---

## 12. Feasibility Assessment

### 12.1 Proven Concepts

| Feature | Precedent | Confidence |
|---------|-----------|------------|
| Pixel editing in terminal | textual-paint | **High** - 1.1k stars, full feature parity with MS Paint |
| Image display in terminal | rich-pixels, textual-imageview | **High** - Well-maintained, Textual-compatible |
| Tile/palette constraints | Existing Qt converter GUI | **High** - Logic already exists |
| TMX parsing | pytmx | **High** - Used by 1.1k projects |
| Undo/redo | textual-paint | **High** - Robust implementation exists |

### 12.2 Novel Requirements

| Feature | Challenge Level | Notes |
|---------|-----------------|-------|
| SNES planar format export | **Medium** | Well-documented format, superfamiconv fallback |
| 15-bit color enforcement | **Low** | Simple bit manipulation |
| Tilemap editing | **Medium** | Based on well-understood concepts |
| Integration with TUI | **Low** | Same framework, similar patterns |

### 12.3 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance issues with large files | Medium | Medium | Viewport rendering, caching |
| Terminal compatibility issues | Low | Medium | Test on major terminals, fallbacks |
| User adoption resistance | Low | Low | Parallel to existing Qt tools |
| Scope creep | Medium | High | Strict phase boundaries |

### 12.4 Overall Feasibility

**Verdict: Highly Feasible**

The existence of textual-paint proves that full-featured image editing is possible in a terminal. All the SNES-specific features (palettes, tiles, formats) are straightforward data transformations. The integration with the existing TUI is natural since they share the same framework.

**Estimated Total Effort**: 12-18 weeks for full implementation by a single developer, or 6-9 weeks with two developers.

**Quick Win Option**: A minimal viable product (MVP) focusing on Phase 1-2 only (basic rendering + pencil tool) could be completed in 3-4 weeks, providing immediate value while validating the approach before committing to full development.

---

## 13. References

### 13.1 Inspiration Projects

1. **textual-paint**: https://github.com/1j01/textual-paint (MIT license)
   - Source for canvas editing patterns, undo/redo, tool implementation
   
2. **rich-pixels**: https://github.com/darrenburns/rich-pixels (MIT license)
   - Image-to-terminal rendering

3. **textual-imageview**: https://github.com/adamviola/textual-imageview (MIT license)
   - Image viewing widget

4. **pytmx**: https://github.com/bitcraft/pytmx (LGPL-3.0 license)
   - TMX parsing

### 13.2 SNES Technical References

1. **SuperFamiconv**: https://github.com/Optiroc/SuperFamiconv
2. **SNES Dev Manual**: https://www.romhacking.net/documents/226/
3. **Anomie's SNES Docs**: https://www.romhacking.net/documents/197/
4. **PVSnesLib Documentation**: https://github.com/alekmaul/pvsneslib

### 13.3 Textual Framework

1. **Textual Documentation**: https://textual.textualize.io/
2. **Rich Documentation**: https://rich.readthedocs.io/
3. **Textual Widget Guide**: https://textual.textualize.io/guide/widgets/

---

## Appendix A: Half-Block Rendering Technical Details

Terminal half-block characters work as follows:

| Character | Description | Use Case |
|-----------|-------------|----------|
| `▀` (U+2580) | Upper half block | FG=top pixel, BG=bottom pixel |
| `▄` (U+2584) | Lower half block | FG=bottom pixel, BG=top pixel |
| `█` (U+2588) | Full block | When both pixels same color |
| ` ` (space) | Empty | When both pixels transparent/BG |

For a pixel at position (x, y) with y being the row:
- If y is even: This is the "top" pixel of the terminal character at row y/2
- If y is odd: This is the "bottom" pixel of the terminal character at row (y-1)/2

Using `▀` with foreground=top_color and background=bottom_color renders both pixels correctly.

---

## Appendix B: SNES Planar Tile Format

SNES tiles use a planar bitplane format. For 4bpp tiles:

```
Tile (8x8, 4bpp) = 32 bytes
  Bytes 0-15: Bitplanes 0 and 1 interleaved (rows 0-7)
  Bytes 16-31: Bitplanes 2 and 3 interleaved (rows 0-7)

For each row (rows 0-7):
  Byte 0: Bitplane 0 (LSB of color index for each pixel)
  Byte 1: Bitplane 1
  [next row...]
  
Then for rows 0-7 again:
  Byte 16: Bitplane 2
  Byte 17: Bitplane 3
  [next row...]
```

For 2bpp tiles (4 colors):
- Only 16 bytes total
- Only bitplanes 0 and 1 are used

For 8bpp tiles (256 colors):
- 64 bytes total
- All 8 bitplanes used, grouped in pairs

Example encoding function:

```python
def encode_tile_4bpp(tile: SNESTile) -> bytes:
    """Encode 8x8 4bpp tile to SNES format (32 bytes)."""
    data = bytearray(32)
    
    for y in range(8):
        bp0 = bp1 = bp2 = bp3 = 0
        for x in range(8):
            color = tile.get_pixel(x, y)
            bit = 7 - x
            bp0 |= ((color >> 0) & 1) << bit
            bp1 |= ((color >> 1) & 1) << bit
            bp2 |= ((color >> 2) & 1) << bit
            bp3 |= ((color >> 3) & 1) << bit
        
        data[y * 2] = bp0
        data[y * 2 + 1] = bp1
        data[16 + y * 2] = bp2
        data[16 + y * 2 + 1] = bp3
    
    return bytes(data)
```

---

## Appendix C: File Format Support Matrix

| Format | Input | Output | Notes |
|--------|-------|--------|-------|
| PNG (indexed) | ✓ | ✓ | Preserves palette |
| PNG (RGB) | ✓ | ✓ | Auto-quantize to palette |
| BMP | ✓ | ✓ | Same as PNG |
| TMX (Tiled) | ✓ | ✓ | Via pytmx |
| TMJ (Tiled JSON) | Future | Future | Newer Tiled format |
| CHR (raw tiles) | ✓ | ✓ | SNES native format |
| PAL (raw palette) | ✓ | ✓ | SNES native format |
| BIN (raw tilemap) | ✓ | ✓ | SNES native format |
| ASM (includes) | - | ✓ | For WLA-DX, CA65, etc |
| H/INC (C headers) | - | ✓ | For C projects |

---

## Appendix D: Testing Strategy

### Unit Tests
- Color conversion (24-bit ↔ 15-bit)
- Tile encoding/decoding (2bpp, 4bpp, 8bpp)
- Palette extraction and optimization
- Flip/rotate operations
- Undo/redo stack operations

### Integration Tests
- Load PNG → Edit → Save → Verify unchanged
- Load PNG → Export SNES → Import → Compare pixels
- Load TMX → Display → Export → Load in Tiled
- Large tileset performance (1000+ tiles)

### Manual Testing
- Terminal compatibility (xterm, kitty, iTerm2, Windows Terminal, etc.)
- Web mode functionality
- Mouse precision at different zoom levels
- Color accuracy on different displays
- Keyboard-only navigation
- Crash recovery after forced exit

### Performance Benchmarks
- Render time for 256x256 pixel canvas
- Undo/redo operation latency
- File load time for large tilesets
- Memory usage with large undo stack

---

*End of Design Document*
