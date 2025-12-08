from __future__ import annotations

from typing import List

from rich.segment import Segment
from rich.style import Style
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.geometry import Size
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widgets import Static, Label, Header, Footer

from ..logic.audio import BRRDecoder, BRRBlock, AudioGenerator

class WaveformVisualizer(ScrollView):
    """Visualizes PCM audio data as a waveform."""

    DEFAULT_CSS = """
    WaveformVisualizer {
        width: 1fr;
        height: 100%;
        background: $surface;
        border: solid $primary;
    }
    """

    samples: reactive[List[int]] = reactive([])
    zoom: reactive[int] = reactive(1)  # Samples per column

    def __init__(self, samples: List[int] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.samples = samples or []

    def watch_samples(self, samples: List[int]) -> None:
        self.virtual_size = Size(len(samples) // self.zoom, self.size.height)
        self.refresh()

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        width = self.size.width
        height = self.size.height
        
        # Center line
        center_y = height // 2
        
        segments = []
        
        # We render 'width' columns
        for x in range(width):
            sample_idx = (scroll_x + x) * self.zoom
            
            if sample_idx >= len(self.samples):
                segments.append(Segment(" ", Style()))
                continue
            
            # Get max/min in this zoom range for peak detection
            chunk = self.samples[sample_idx : sample_idx + self.zoom]
            if not chunk:
                val = 0
            else:
                # Simple visualization: just take the first sample or average
                # Better: Max magnitude
                val = max(chunk, key=abs)
            
            # Normalize to -1.0 to 1.0
            norm_val = val / 32768.0
            
            # Calculate height in rows from center
            # Max height is center_y
            bar_height = int(abs(norm_val) * center_y)
            
            # Determine character based on y position
            # y is the current row we are rendering (0 is top)
            
            dist_from_center = center_y - y
            
            char = " "
            style = Style(color="green")
            
            if val > 0:
                # Positive value (Upper half)
                # Bars go UP from center
                if y < center_y and y >= center_y - bar_height:
                    char = "│"
                    style = Style(color="bright_green")
            elif val < 0:
                # Negative value (Lower half)
                # Bars go DOWN from center
                if y > center_y and y <= center_y + bar_height:
                    char = "│"
                    style = Style(color="bright_blue")
            else:
                # Zero crossing
                if y == center_y:
                    char = "─"
                    style = Style(color="gray50")

            segments.append(Segment(char, style))
            
        return Strip(segments)

class BRRHexViewer(Static):
    """Displays BRR blocks in hex format or metadata."""
    
    DEFAULT_CSS = """
    BRRHexViewer {
        width: 30%;
        height: 100%;
        border-left: solid $primary;
        background: $surface;
        overflow-y: auto;
        padding: 0 1;
    }
    """
    
    blocks: reactive[List[BRRBlock]] = reactive([])
    metadata: reactive[str] = reactive("")
    
    def watch_blocks(self, blocks: List[BRRBlock]) -> None:
        self._refresh_content()

    def watch_metadata(self, metadata: str) -> None:
        self._refresh_content()

    def _refresh_content(self) -> None:
        if self.metadata:
            self.update(Text(self.metadata))
            return
            
        if not self.blocks:
            self.update("")
            return

        text = Text()
        for i, block in enumerate(self.blocks):
            # Header analysis
            r = block.range
            f = block.filter
            flags = []
            if block.is_loop: flags.append("L")
            if block.is_end: flags.append("E")
            flag_str = "".join(flags).ljust(2)
            
            # Color code based on filter
            filter_colors = ["white", "cyan", "green", "yellow"]
            color = filter_colors[f]
            
            text.append(f"{i:03X}: ", style="dim")
            text.append(f"[{block.header:02X}] ", style=f"bold {color}")
            text.append(f"{block.data.hex().upper()} ", style="white")
            text.append(f"R:{r} F:{f} {flag_str}\n", style="dim")
            
        self.update(text)

from pathlib import Path
import wave

class AudioEditorPanel(Static):
    """Main panel for the SPC Coherence Engine."""
    
    DEFAULT_CSS = """
    AudioEditorPanel {
        width: 100%;
        height: 100%;
    }
    
    AudioEditorPanel > Horizontal {
        height: 1fr;
    }
    
    AudioEditorPanel > #audio-status {
        dock: bottom;
        height: 1;
        background: $primary 30%;
        padding: 0 1;
    }
    """
    
    file_path: reactive[Path | None] = reactive(None)
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield WaveformVisualizer(id="waveform")
            yield BRRHexViewer(id="brr-hex")
        yield Label("🔊 SPC Coherence Engine - [dim]Fractal Tracker[/dim]", id="audio-status")
            
    def watch_file_path(self, file_path: Path | None) -> None:
        """Load audio file when path changes."""
        status = self.query_one("#audio-status", Label)
        waveform = self.query_one(WaveformVisualizer)
        hex_viewer = self.query_one(BRRHexViewer)
        
        if not file_path:
            status.update("🔊 SPC Coherence Engine - [dim]Select an audio file[/dim]")
            return
            
        if not file_path.exists():
            status.update(f"[red]File not found: {file_path}[/red]")
            return
            
        status.update(f"🔊 SPC Coherence Engine - {file_path.name}")
        
        suffix = file_path.suffix.lower()
        
        if suffix == ".brr":
            # Decode BRR
            try:
                data = file_path.read_bytes()
                decoder = BRRDecoder()
                blocks = decoder.decode_stream(data)
                
                # Collect all samples
                all_samples = []
                for block in blocks:
                    all_samples.extend(block.samples)
                    
                waveform.samples = all_samples
                hex_viewer.metadata = ""
                hex_viewer.blocks = blocks
                status.update(f"🔊 {file_path.name} | BRR | {len(blocks)} blocks | {len(all_samples)} samples")
            except Exception as e:
                status.update(f"[red]Error decoding BRR: {e}[/red]")
                
        elif suffix == ".wav":
            # Read WAV
            try:
                with wave.open(str(file_path), 'rb') as wav_file:
                    n_channels = wav_file.getnchannels()
                    sampwidth = wav_file.getsampwidth()
                    framerate = wav_file.getframerate()
                    n_frames = wav_file.getnframes()
                    
                    raw_data = wav_file.readframes(n_frames)
                    
                    # Convert to 16-bit signed mono for visualization
                    samples = []
                    import struct
                    
                    # Assuming 16-bit PCM for simplicity
                    if sampwidth == 2:
                        fmt = f"<{n_frames * n_channels}h"
                        raw_samples = struct.unpack(fmt, raw_data)
                        
                        # Take only first channel if stereo
                        if n_channels > 1:
                            samples = raw_samples[::n_channels]
                        else:
                            samples = list(raw_samples)
                    elif sampwidth == 1:
                        # 8-bit unsigned to 16-bit signed
                        for b in raw_data:
                            samples.append((b - 128) * 256)
                            
                    waveform.samples = samples
                    hex_viewer.metadata = f"WAV File\nRate: {framerate}Hz\nChannels: {n_channels}\nWidth: {sampwidth*8}bit\nFrames: {n_frames}"
                    hex_viewer.blocks = [] # No BRR blocks for WAV yet
                    status.update(f"🔊 {file_path.name} | WAV | {framerate}Hz | {len(samples)} samples")
            except Exception as e:
                status.update(f"[red]Error reading WAV: {e}[/red]")
                
        elif suffix == ".spc":
            # Parse SPC ID666 Tags
            try:
                data = file_path.read_bytes()
                
                # Check for ID666 text tag at 0x2E
                # 0002E: Song Title (32)
                # 0004E: Game Title (32)
                # 0006E: Dumper (16)
                # 0007E: Comments (32)
                # 0009E: Date (11)
                # 000A9: Song Length (3)
                # 000AC: Fade Length (5)
                # 000B1: Artist (32)
                
                if len(data) > 0xB1 + 32:
                    def get_str(offset, length):
                        try:
                            return data[offset:offset+length].decode('ascii', errors='ignore').strip().replace('\x00', '')
                        except:
                            return "?"

                    song_title = get_str(0x2E, 32)
                    game_title = get_str(0x4E, 32)
                    artist = get_str(0xB1, 32)
                    
                    info_text = (
                        f"SPC Info:\n"
                        f"Song:   {song_title}\n"
                        f"Game:   {game_title}\n"
                        f"Artist: {artist}\n\n"
                        f"[dim]Visualizing SPC700 Memory Dump (64KB)\n"
                        f"This is the raw data state of the audio chip.[/dim]"
                    )
                    
                    # Visualize the RAM dump as a waveform
                    # Skip header (256 bytes)
                    ram_data = data[256:256+65536]
                    # Convert bytes to signed 16-bit scale for visualization
                    # byte (0-255) -> -128 to 127 -> scale to -32768 to 32767
                    ram_samples = [((b - 128) * 256) for b in ram_data]
                    
                    waveform.samples = ram_samples
                    hex_viewer.metadata = info_text
                    hex_viewer.blocks = []
                    
                    status.update(f"🔊 {file_path.name} | SPC | {game_title} - {song_title} | Memory Dump Visualization")
                    
                else:
                    status.update(f"🔊 {file_path.name} | SPC | (No ID666 tags found)")
                    waveform.samples = []
                    hex_viewer.metadata = "No ID666 tags found."
                    hex_viewer.blocks = []
                    
            except Exception as e:
                status.update(f"[red]Error reading SPC: {e}[/red]")
                
        else:
            # Fallback / Demo mode
            self.on_mount()

    def on_mount(self) -> None:
        if self.file_path:
            return
            
        # Generate a test sine wave for now
        gen = AudioGenerator()
        pcm = gen.generate_sine_wave(440.0, 0.1) # 440Hz, 0.1s
        
        # Mock BRR blocks for visualization
        blocks = []
        for i in range(20):
            blocks.append(BRRBlock(
                header=0xB0 if i < 19 else 0xB1, # Range B, Filter 0, Loop/End
                data=b'\x00\x11\x22\x33\x44\x55\x66\x77',
                samples=[0]*16
            ))
            
        self.query_one(WaveformVisualizer).samples = pcm
        self.query_one(BRRHexViewer).metadata = ""
        self.query_one(BRRHexViewer).blocks = blocks
