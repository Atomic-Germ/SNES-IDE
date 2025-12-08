from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class BRRBlock:
    """Represents a single 9-byte SNES BRR block."""
    header: int
    data: bytes  # 8 bytes
    samples: List[int]  # 16 decoded PCM samples (16-bit signed)

    @property
    def range(self) -> int:
        return (self.header >> 4) & 0x0F

    @property
    def filter(self) -> int:
        return (self.header >> 2) & 0x03

    @property
    def is_loop(self) -> bool:
        return bool(self.header & 0x02)

    @property
    def is_end(self) -> bool:
        return bool(self.header & 0x01)

class BRRDecoder:
    """Decodes SNES BRR audio data to PCM."""

    def __init__(self):
        self.p1 = 0  # Previous sample (t-1)
        self.p2 = 0  # Previous sample (t-2)

    def decode_block(self, block_data: bytes) -> BRRBlock:
        """Decode a 9-byte BRR block."""
        if len(block_data) != 9:
            raise ValueError(f"Invalid BRR block length: {len(block_data)}")

        header = block_data[0]
        data = block_data[1:]
        
        shift = (header >> 4) & 0x0F
        filter_idx = (header >> 2) & 0x03
        
        samples = []
        
        for i in range(8):
            byte = data[i]
            # High nibble first, then low nibble
            nibbles = [(byte >> 4) & 0x0F, byte & 0x0F]
            
            for nibble in nibbles:
                # Sign extension for 4-bit nibble
                if nibble >= 8:
                    nibble -= 16
                
                # Apply shift
                # Note: The shift behavior is complex in hardware, simplified here
                # Standard formula: sample = nibble * 2^shift
                # But SNES limits shift to <= 12 effectively for valid range
                if shift <= 12:
                    sample = (nibble << shift) >> 1
                else:
                    sample = (nibble & ~0x07) << 9 # Invalid/Silence usually
                
                # Apply Filter
                # p1 = previous, p2 = previous-previous
                if filter_idx == 0:
                    # No filter
                    prediction = 0
                elif filter_idx == 1:
                    # p1 * 15/16
                    prediction = self.p1 + ((-self.p1) >> 4)
                elif filter_idx == 2:
                    # p1 * 61/32 - p2 * 15/16
                    part1 = (self.p1 * 2) - (self.p1 >> 5) # ~1.9
                    part2 = self.p2 + ((-self.p2) >> 4)    # ~0.93
                    prediction = part1 - part2
                elif filter_idx == 3:
                    # p1 * 115/64 - p2 * 13/16
                    part1 = (self.p1 * 2) - ((self.p1 * 13) >> 6) # ~1.8
                    part2 = self.p2 + ((-self.p2 * 3) >> 4)       # ~0.8
                    prediction = part1 - part2
                
                final_sample = sample + prediction
                
                # Clamp to 16-bit signed
                final_sample = max(-32768, min(32767, int(final_sample)))
                
                # Wrap for next iteration (hardware behavior involves wrapping)
                # But for visualization, clamping is usually better to see the wave
                
                samples.append(final_sample)
                
                self.p2 = self.p1
                self.p1 = final_sample

        return BRRBlock(header, data, samples)

    def decode_stream(self, brr_data: bytes) -> List[BRRBlock]:
        """Decode a stream of BRR data."""
        blocks = []
        self.p1 = 0
        self.p2 = 0
        
        num_blocks = len(brr_data) // 9
        for i in range(num_blocks):
            chunk = brr_data[i*9 : (i+1)*9]
            blocks.append(self.decode_block(chunk))
            
        return blocks

class AudioGenerator:
    """Generates simple waveforms for testing."""
    
    @staticmethod
    def generate_sine_wave(frequency: float, duration_sec: float, sample_rate: int = 32000) -> List[int]:
        """Generate 16-bit signed PCM sine wave."""
        samples = []
        num_samples = int(duration_sec * sample_rate)
        for i in range(num_samples):
            t = i / sample_rate
            val = int(32767 * math.sin(2 * math.pi * frequency * t))
            samples.append(val)
        return samples
