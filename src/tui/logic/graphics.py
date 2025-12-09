from __future__ import annotations

from typing import List, Tuple
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

class SNESPalette:
    """SNES palette management with 15-bit RGB support.
    
    SNES uses 15-bit color: 5 bits per R, G, B channel = 32768 possible colors.
    Format: 0BBBBBGGGGGRRRRR (little-endian in memory)
    
    Palette structure depends on BPP mode:
    - 2bpp: 4 colors per palette, 8 palettes max
    - 4bpp: 16 colors per palette, 8 palettes max  
    - 8bpp: 256 colors, single palette
    
    Color index 0 is transparent for sprites.
    """
    
    def __init__(self, bpp: int = 4, num_palettes: int = 1):
        """Initialize palette.
        
        Args:
            bpp: Bits per pixel (2, 4, or 8)
            num_palettes: Number of palettes (1-8 for 2/4bpp, always 1 for 8bpp)
        """
        self.bpp = bpp
        self.colors_per_palette = 2 ** bpp
        self.num_palettes = num_palettes if bpp < 8 else 1
        # Store as 24-bit RGB tuples for display, convert to 15-bit on export
        self.palettes: List[List[Tuple[int, int, int]]] = [
            [(0, 0, 0)] * self.colors_per_palette 
            for _ in range(self.num_palettes)
        ]
    
    @staticmethod
    def rgb24_to_snes(r: int, g: int, b: int) -> int:
        """Convert 24-bit RGB to 15-bit SNES color.
        
        Args:
            r, g, b: 8-bit color components (0-255)
            
        Returns:
            15-bit SNES color value (0BBBBBGGGGGRRRRR)
        """
        return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
    
    @staticmethod
    def snes_to_rgb24(color: int) -> Tuple[int, int, int]:
        """Convert 15-bit SNES color to 24-bit RGB.
        
        Args:
            color: 15-bit SNES color value
            
        Returns:
            Tuple of (r, g, b) as 8-bit values
        """
        r = (color & 0x1F) << 3
        g = ((color >> 5) & 0x1F) << 3
        b = ((color >> 10) & 0x1F) << 3
        # Replicate top bits into bottom for full range
        r |= r >> 5
        g |= g >> 5
        b |= b >> 5
        return (r, g, b)
    
    def get_color(self, palette_idx: int, color_idx: int) -> Tuple[int, int, int]:
        """Get a color from the palette as 24-bit RGB."""
        if 0 <= palette_idx < self.num_palettes and 0 <= color_idx < self.colors_per_palette:
            return self.palettes[palette_idx][color_idx]
        return (0, 0, 0)
    
    def set_color(self, palette_idx: int, color_idx: int, r: int, g: int, b: int) -> None:
        """Set a color in the palette (stores as SNES-quantized RGB)."""
        if 0 <= palette_idx < self.num_palettes and 0 <= color_idx < self.colors_per_palette:
            # Quantize to 15-bit and back to get SNES-accurate color
            snes = self.rgb24_to_snes(r, g, b)
            self.palettes[palette_idx][color_idx] = self.snes_to_rgb24(snes)
    
    def from_pil_image(self, image: "Image.Image", palette_idx: int = 0) -> None:
        """Extract palette from an indexed PIL image.
        
        Args:
            image: PIL Image in 'P' (palette) mode
            palette_idx: Which palette slot to populate
        """
        if not HAS_PIL:
            return
        if image.mode != 'P':
            return
            
        pal_data = image.getpalette()
        if not pal_data:
            return
            
        # Extract up to colors_per_palette colors
        for i in range(min(self.colors_per_palette, len(pal_data) // 3)):
            r = pal_data[i * 3]
            g = pal_data[i * 3 + 1]
            b = pal_data[i * 3 + 2]
            self.set_color(palette_idx, i, r, g, b)


class SNESTile:
    """SNES tile representation with indexed pixel data.
    
    Tiles are 8x8 or 16x16 pixels, stored as palette indices.
    BPP mode determines max colors: 2bpp=4, 4bpp=16, 8bpp=256.
    
    SNES stores tiles in planar bitplane format for export,
    but we store as simple indexed array for editing.
    """
    
    def __init__(self, width: int = 8, height: int = 8, bpp: int = 4):
        """Initialize a tile.
        
        Args:
            width: Tile width (usually 8 or 16)
            height: Tile height (usually 8 or 16)
            bpp: Bits per pixel (2, 4, or 8)
        """
        self.width = width
        self.height = height
        self.bpp = bpp
        self.max_color_index = (2 ** bpp) - 1
        # 2D array of palette indices
        self.pixels: List[List[int]] = [[0] * width for _ in range(height)]
    
    def get_pixel(self, x: int, y: int) -> int:
        """Get palette index at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pixels[y][x]
        return 0
    
    def set_pixel(self, x: int, y: int, color_index: int) -> None:
        """Set palette index at position, clamping to valid range."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = max(0, min(color_index, self.max_color_index))
    
    def clear(self, color_index: int = 0) -> None:
        """Fill entire tile with a color index."""
        color_index = max(0, min(color_index, self.max_color_index))
        self.pixels = [[color_index] * self.width for _ in range(self.height)]
    
    def from_pil_region(self, image: "Image.Image", x: int, y: int) -> None:
        """Load tile data from a region of an indexed PIL image.
        
        Args:
            image: PIL Image in 'P' (palette) mode
            x, y: Top-left corner of region to extract
        """
        if not HAS_PIL:
            return
        if image.mode != 'P':
            return
            
        for ty in range(self.height):
            for tx in range(self.width):
                px = x + tx
                py = y + ty
                if 0 <= px < image.width and 0 <= py < image.height:
                    idx = image.getpixel((px, py))
                    self.set_pixel(tx, ty, idx)


class SNESTileset:
    """Collection of SNES tiles with shared palette.
    
    Typically loaded from a sprite sheet or tileset image.
    """
    
    def __init__(self, tile_width: int = 8, tile_height: int = 8, bpp: int = 4):
        """Initialize tileset.
        
        Args:
            tile_width: Width of each tile (8 or 16)
            tile_height: Height of each tile (8 or 16)
            bpp: Bits per pixel for tiles
        """
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.bpp = bpp
        self.tiles: List[SNESTile] = []
        self.palette = SNESPalette(bpp=bpp)
        self.image_width = 0  # Original image dimensions
        self.image_height = 0
        self.tiles_per_row = 0
    
    def get_tile(self, index: int) -> SNESTile | None:
        """Get a tile by index."""
        if 0 <= index < len(self.tiles):
            return self.tiles[index]
        return None
    
    @property
    def tile_count(self) -> int:
        """Number of tiles in the tileset."""
        return len(self.tiles)
    
    def from_pil_image(self, image: "Image.Image") -> bool:
        """Load tileset from a PIL image.
        
        Splits image into tiles and extracts palette.
        Image should be indexed (mode 'P') for best results.
        
        Args:
            image: PIL Image to load
            
        Returns:
            True if successful, False otherwise
        """
        if not HAS_PIL:
            return False
        
        # Convert to indexed if not already
        if image.mode != 'P':
            # Quantize to palette matching BPP
            max_colors = 2 ** self.bpp
            image = image.quantize(colors=max_colors)
        
        self.image_width = image.width
        self.image_height = image.height
        
        # Extract palette
        self.palette.from_pil_image(image)
        
        # Split into tiles
        self.tiles = []
        self.tiles_per_row = image.width // self.tile_width
        
        for y in range(0, image.height, self.tile_height):
            for x in range(0, image.width, self.tile_width):
                tile = SNESTile(self.tile_width, self.tile_height, self.bpp)
                tile.from_pil_region(image, x, y)
                self.tiles.append(tile)
        
        return True
    
    def load_from_path(self, path: Path) -> bool:
        """Load tileset from an image file path.
        
        Args:
            path: Path to PNG/BMP file
            
        Returns:
            True if successful, False otherwise
        """
        if not HAS_PIL:
            return False
        
        try:
            image = Image.open(path)
            return self.from_pil_image(image)
        except Exception:
            return False
    
    @classmethod
    def create_new(
        cls,
        width_tiles: int,
        height_tiles: int,
        tile_width: int = 8,
        tile_height: int = 8,
        bpp: int = 4,
    ) -> "SNESTileset":
        """Create a new empty tileset with the specified dimensions.
        
        Args:
            width_tiles: Number of tiles wide
            height_tiles: Number of tiles tall
            tile_width: Width of each tile (8 or 16)
            tile_height: Height of each tile (8 or 16)
            bpp: Bits per pixel (2, 4, or 8)
            
        Returns:
            New SNESTileset with empty tiles and default palette
        """
        tileset = cls(tile_width=tile_width, tile_height=tile_height, bpp=bpp)
        tileset.image_width = width_tiles * tile_width
        tileset.image_height = height_tiles * tile_height
        tileset.tiles_per_row = width_tiles
        
        # Create empty tiles (filled with color index 0)
        total_tiles = width_tiles * height_tiles
        for _ in range(total_tiles):
            tile = SNESTile(tile_width, tile_height, bpp)
            tileset.tiles.append(tile)
        
        # Set up a default SNES-style palette
        tileset.palette = SNESPalette(bpp=bpp)
        max_colors = 2 ** bpp
        
        # Default palette: black, white, and some common colors
        default_colors = [
            (0, 0, 0),       # 0: Black (transparent)
            (255, 255, 255), # 1: White
            (255, 0, 0),     # 2: Red
            (0, 255, 0),     # 3: Green
            (0, 0, 255),     # 4: Blue
            (255, 255, 0),   # 5: Yellow
            (255, 0, 255),   # 6: Magenta
            (0, 255, 255),   # 7: Cyan
            (128, 128, 128), # 8: Gray
            (192, 192, 192), # 9: Light Gray
            (128, 0, 0),     # A: Dark Red
            (0, 128, 0),     # B: Dark Green
            (0, 0, 128),     # C: Dark Blue
            (128, 128, 0),   # D: Olive
            (128, 0, 128),   # E: Purple
            (0, 128, 128),   # F: Teal
        ]
        
        # Fill palette with defaults up to max colors
        for i in range(min(max_colors, len(default_colors))):
            r, g, b = default_colors[i]
            tileset.palette.set_color(0, i, r, g, b)
        
        return tileset
