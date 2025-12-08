import struct
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class RomHeader:
    title: str
    map_mode: str  # "LoROM", "HiROM", "ExHiROM"
    rom_type: str
    rom_size_byte: int
    ram_size_byte: int
    destination: str
    version: int
    checksum: int
    complement: int
    is_valid: bool
    header_location: int  # Offset in file

class SNESRomAnalyzer:
    # Map Modes
    MAP_MODES = {
        0x20: "LoROM",
        0x21: "HiROM",
        0x22: "ExLoROM",
        0x23: "SA-1",
        0x25: "ExHiROM",
        0x30: "LoROM (Fast)",
        0x31: "HiROM (Fast)",
        0x32: "ExLoROM (Fast)",
        0x35: "ExHiROM (Fast)",
    }

    # Cartridge Types
    CART_TYPES = {
        0x00: "ROM",
        0x01: "ROM + RAM",
        0x02: "ROM + RAM + Battery",
        0x03: "ROM + Coprocessor",
        0x04: "ROM + Coprocessor + RAM",
        0x05: "ROM + Coprocessor + RAM + Battery",
        0x13: "ROM + Super FX",
    }

    # Destination Codes
    DESTINATIONS = {
        0x00: "Japan (NTSC)",
        0x01: "USA (NTSC)",
        0x02: "Europe (PAL)",
        0x03: "Sweden/Scandinavia (PAL)",
        0x04: "Finland (PAL)",
        0x05: "Denmark (PAL)",
        0x06: "France (PAL)",
        0x07: "Netherlands (PAL)",
        0x08: "Spain (PAL)",
        0x09: "Germany (PAL)",
        0x0A: "Italy (PAL)",
        0x0B: "China (PAL)",
        0x0C: "Indonesia (PAL)",
        0x0D: "Korea (NTSC)",
    }

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = b""
        self.header: Optional[RomHeader] = None
        self.data_offset = 0
        self.load()

    def load(self):
        if not self.file_path:
            return
            
        try:
            with open(self.file_path, "rb") as f:
                self.data = f.read()
            
            # Check for SMC header (512 bytes)
            # Standard ROM sizes are multiples of 1024.
            # If size % 1024 == 512, it likely has a header.
            if len(self.data) % 1024 == 512:
                self.data_offset = 512
            else:
                self.data_offset = 0
                
            self.header = self._find_header()
        except Exception as e:
            print(f"Error loading ROM: {e}")

    def _find_header(self) -> Optional[RomHeader]:
        # Check LoROM location ($7FC0) + data_offset
        header_lo = self._parse_header_at(0x7FC0 + self.data_offset)
        if header_lo and header_lo.is_valid:
            return header_lo

        # Check HiROM location ($FFC0) + data_offset
        header_hi = self._parse_header_at(0xFFC0 + self.data_offset)
        if header_hi and header_hi.is_valid:
            return header_hi
            
        # If neither is perfectly valid, return the one that looks most promising (or None)
        # For now, return None if no valid checksum found
        return None

    def _parse_header_at(self, offset: int) -> Optional[RomHeader]:
        if offset + 32 > len(self.data):
            return None

        # Read 32 bytes starting at offset
        # Title is 21 bytes at offset
        title_bytes = self.data[offset:offset+21]
        title = title_bytes.decode("ascii", errors="replace").strip()

        map_mode_byte = self.data[offset+21]
        rom_type_byte = self.data[offset+22]
        rom_size_byte = self.data[offset+23]
        ram_size_byte = self.data[offset+24]
        dest_byte = self.data[offset+25]
        fixed_byte = self.data[offset+26] # Should be 0x33
        version_byte = self.data[offset+27]
        complement = struct.unpack("<H", self.data[offset+28:offset+30])[0]
        checksum = struct.unpack("<H", self.data[offset+30:offset+32])[0]

        # Validate
        is_valid = (checksum + complement) == 0xFFFF
        
        # Map values
        map_mode = self.MAP_MODES.get(map_mode_byte & ~0x10, f"Unknown ({map_mode_byte:02X})") # Mask out speed bit
        rom_type = self.CART_TYPES.get(rom_type_byte, f"Unknown ({rom_type_byte:02X})")
        destination = self.DESTINATIONS.get(dest_byte, f"Unknown ({dest_byte:02X})")

        return RomHeader(
            title=title,
            map_mode=map_mode,
            rom_type=rom_type,
            rom_size_byte=rom_size_byte,
            ram_size_byte=ram_size_byte,
            destination=destination,
            version=version_byte,
            checksum=checksum,
            complement=complement,
            is_valid=is_valid,
            header_location=offset
        )

    def get_bank_data(self, bank: int) -> bytes:
        """
        Returns the raw ROM data associated with a specific bank.
        Returns empty bytes if the bank is not mapped to ROM or out of bounds.
        """
        if not self.header or not self.data:
            return b""

        mode = self.header.map_mode
        
        # LoROM Mapping
        if "LoROM" in mode:
            # LoROM maps 32KB chunks to the upper half ($8000-$FFFF) of banks.
            # Banks $00-$7D and $80-$FD use this mapping.
            # File Offset = (Bank & 0x7F) * 32KB
            
            # Calculate logical ROM offset
            rom_offset = ((bank & 0x7F) * 0x8000) + self.data_offset
            
            if rom_offset < len(self.data):
                # Return 32KB chunk
                return self.data[rom_offset : rom_offset + 0x8000]
                
        # HiROM Mapping
        elif "HiROM" in mode:
            # HiROM maps 64KB chunks linearly in banks $C0-$FF (and $40-$7D).
            # Banks $00-$3F and $80-$BF are mirrors of the upper half of these chunks.
            
            rom_offset = -1
            
            if 0xC0 <= bank <= 0xFF:
                rom_offset = ((bank - 0xC0) * 0x10000) + self.data_offset
            elif 0x40 <= bank <= 0x7D:
                rom_offset = ((bank - 0x40) * 0x10000) + self.data_offset
            elif 0x00 <= bank <= 0x3F:
                # Mirror of upper half of (Bank + $C0)
                base_bank = bank + 0xC0
                rom_offset = ((base_bank - 0xC0) * 0x10000 + 0x8000) + self.data_offset
                if rom_offset < len(self.data):
                    return self.data[rom_offset : rom_offset + 0x8000]
                return b""
            elif 0x80 <= bank <= 0xBF:
                # Mirror of upper half of (Bank + $40) -> which is (Bank - $80 + $C0)
                base_bank = bank - 0x80 + 0xC0
                rom_offset = ((base_bank - 0xC0) * 0x10000 + 0x8000) + self.data_offset
                if rom_offset < len(self.data):
                    return self.data[rom_offset : rom_offset + 0x8000]
                return b""

            if rom_offset >= 0 and rom_offset < len(self.data):
                return self.data[rom_offset : rom_offset + 0x10000]

        return b""

    def get_memory_map_info(self) -> dict:
        """
        Returns a dictionary describing the memory map for visualization.
        Keys are bank numbers (0-255), values are types ('rom', 'ram', 'system', 'sram').
        """
        if not self.header:
            return {}

        banks = {}
        mode = self.header.map_mode

        # Basic LoROM mapping
        if "LoROM" in mode:
            for bank in range(0x100): # 00-FF
                banks[bank] = []
                # LoROM: 
                # Banks 00-3F and 80-BF:
                #   0000-1FFF: System (RAM mirror)
                #   2000-5FFF: System (IO)
                #   6000-7FFF: SRAM (if enabled)
                #   8000-FFFF: ROM (32k chunks)
                # Banks 40-7D and C0-FD:
                #   0000-FFFF: ROM (64k chunks) - wait, LoROM usually maps 32k chunks in lower banks
                
                # Simplified visualization for now:
                if 0x00 <= bank <= 0x3F or 0x80 <= bank <= 0xBF:
                    banks[bank].append({"range": (0x0000, 0x7FFF), "type": "system"}) # System/SRAM
                    banks[bank].append({"range": (0x8000, 0xFFFF), "type": "rom"})    # ROM Window
                elif 0x40 <= bank <= 0x7D or 0xC0 <= bank <= 0xFD:
                    banks[bank].append({"range": (0x0000, 0xFFFF), "type": "rom"})    # Full ROM
                elif 0x7E <= bank <= 0x7F:
                    banks[bank].append({"range": (0x0000, 0xFFFF), "type": "ram"})    # WRAM
        
        # Basic HiROM mapping
        elif "HiROM" in mode:
            for bank in range(0x100):
                banks[bank] = []
                # HiROM:
                # Banks 00-3F and 80-BF:
                #   0000-5FFF: System
                #   6000-7FFF: SRAM
                #   8000-FFFF: ROM (Mirror of upper banks)
                # Banks 40-7D and C0-FD:
                #   0000-FFFF: ROM
                
                if 0x00 <= bank <= 0x3F or 0x80 <= bank <= 0xBF:
                    banks[bank].append({"range": (0x0000, 0x7FFF), "type": "system"})
                    banks[bank].append({"range": (0x8000, 0xFFFF), "type": "rom"})
                elif 0x40 <= bank <= 0x7D:
                    banks[bank].append({"range": (0x0000, 0xFFFF), "type": "rom"})
                elif 0xC0 <= bank <= 0xFF: # HiROM maps ROM linearly here
                    banks[bank].append({"range": (0x0000, 0xFFFF), "type": "rom"})
                elif 0x7E <= bank <= 0x7F:
                    banks[bank].append({"range": (0x0000, 0xFFFF), "type": "ram"})

        return banks
