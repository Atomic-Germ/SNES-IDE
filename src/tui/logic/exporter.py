from __future__ import annotations

from typing import List, Tuple
from .graphics import SNESTile, SNESPalette, SNESTileset

class SNESExporter:
    """Handles conversion of SNES assets to binary and assembly formats."""

    @staticmethod
    def tile_to_bitplanes(tile: SNESTile) -> bytes:
        """Convert a SNESTile to SNES planar format bytes.
        
        Supports 2bpp, 4bpp, and 8bpp.
        """
        # Ensure 8x8 chunks (SNES tiles are always 8x8 in memory, 
        # 16x16 sprites are composed of four 8x8 tiles)
        # For now, let's assume the input tile is 8x8. 
        # If it's 16x16, we'd need to split it.
        
        if tile.width != 8 or tile.height != 8:
            # TODO: Handle 16x16 tiles by splitting them
            return b""

        bpp = tile.bpp
        data = bytearray()
        
        # 2bpp (16 bytes)
        # Plane 0, 1 interleaved by row
        plane0 = []
        plane1 = []
        
        for y in range(8):
            row_p0 = 0
            row_p1 = 0
            for x in range(8):
                pixel = tile.get_pixel(x, y)
                # Bit 0
                if pixel & 0x01:
                    row_p0 |= (1 << (7 - x))
                # Bit 1
                if pixel & 0x02:
                    row_p1 |= (1 << (7 - x))
            plane0.append(row_p0)
            plane1.append(row_p1)
            
            # For 2bpp, we write row by row: P0, P1
            if bpp == 2:
                data.append(row_p0)
                data.append(row_p1)

        if bpp == 2:
            return bytes(data)

        # 4bpp (32 bytes)
        # First 16 bytes: Plane 0, 1 (same as 2bpp)
        # Next 16 bytes: Plane 2, 3
        plane2 = []
        plane3 = []
        
        for y in range(8):
            row_p2 = 0
            row_p3 = 0
            for x in range(8):
                pixel = tile.get_pixel(x, y)
                # Bit 2
                if pixel & 0x04:
                    row_p2 |= (1 << (7 - x))
                # Bit 3
                if pixel & 0x08:
                    row_p3 |= (1 << (7 - x))
            plane2.append(row_p2)
            plane3.append(row_p3)

        # Write Planes 0, 1
        for i in range(8):
            data.append(plane0[i])
            data.append(plane1[i])
            
        # Write Planes 2, 3
        for i in range(8):
            data.append(plane2[i])
            data.append(plane3[i])

        if bpp == 4:
            return bytes(data)

        # 8bpp (64 bytes)
        # First 32 bytes: Plane 0-3 (same as 4bpp)
        # Next 32 bytes: Plane 4-7
        plane4 = []
        plane5 = []
        plane6 = []
        plane7 = []
        
        for y in range(8):
            row_p4 = 0
            row_p5 = 0
            row_p6 = 0
            row_p7 = 0
            for x in range(8):
                pixel = tile.get_pixel(x, y)
                if pixel & 0x10: row_p4 |= (1 << (7 - x))
                if pixel & 0x20: row_p5 |= (1 << (7 - x))
                if pixel & 0x40: row_p6 |= (1 << (7 - x))
                if pixel & 0x80: row_p7 |= (1 << (7 - x))
            plane4.append(row_p4)
            plane5.append(row_p5)
            plane6.append(row_p6)
            plane7.append(row_p7)

        # Write Planes 4, 5
        for i in range(8):
            data.append(plane4[i])
            data.append(plane5[i])
            
        # Write Planes 6, 7
        for i in range(8):
            data.append(plane6[i])
            data.append(plane7[i])

        return bytes(data)

    @staticmethod
    def palette_to_bytes(palette: SNESPalette) -> bytes:
        """Convert SNESPalette to little-endian bytes (BGR555)."""
        data = bytearray()
        # Export all palettes
        for pal_idx in range(palette.num_palettes):
            for col_idx in range(palette.colors_per_palette):
                r, g, b = palette.get_color(pal_idx, col_idx)
                snes_color = SNESPalette.rgb24_to_snes(r, g, b)
                # Little endian: low byte, high byte
                data.append(snes_color & 0xFF)
                data.append((snes_color >> 8) & 0xFF)
        return bytes(data)

    @staticmethod
    def format_asm(data: bytes, label: str, width: int = 16) -> str:
        """Format bytes as WLA-DX compatible assembly (.db)."""
        lines = [f"{label}:"]
        
        for i in range(0, len(data), width):
            chunk = data[i:i+width]
            hex_vals = [f"${b:02X}" for b in chunk]
            lines.append(f"    .db {', '.join(hex_vals)}")
            
        return "\n".join(lines)
