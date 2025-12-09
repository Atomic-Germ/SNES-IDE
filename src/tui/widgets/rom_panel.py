from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Label, Header, Footer, Button
from textual.reactive import reactive
from textual.message import Message
from textual.events import MouseMove, Click
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from typing import Optional

from src.tui.logic.rom_analyzer import SNESRomAnalyzer, RomHeader

class RomInfoWidget(Static):
    header: reactive[Optional[RomHeader]] = reactive(None)

    def watch_header(self, header: Optional[RomHeader]):
        self.update(self._make_content(header))

    def _make_content(self, header: Optional[RomHeader]) -> Panel:
        if not header:
            return Panel("No ROM Loaded", title="ROM Info")
        
        info = f"""
[b]Title:[/b] {header.title}
[b]Map Mode:[/b] {header.map_mode}
[b]Type:[/b] {header.rom_type}
[b]ROM Size:[/b] 1 << {header.rom_size_byte} KB
[b]RAM Size:[/b] {header.ram_size_byte} KB
[b]Region:[/b] {header.destination}
[b]Version:[/b] 1.{header.version}
[b]Checksum:[/b] {header.checksum:04X}
[b]Complement:[/b] {header.complement:04X}
[b]Valid:[/b] {"[green]YES[/green]" if header.is_valid else "[red]NO[/red]"}
        """
        return Panel(Align.left(info), title="ROM Header")

class MemoryMapWidget(Static):
    """
    Visualizes the SNES Memory Map (Banks $00-$FF) as a 16x16 grid.
    """
    
    class BankHovered(Message):
        def __init__(self, bank: int, info: list):
            self.bank = bank
            self.info = info
            super().__init__()

    class BankClicked(Message):
        def __init__(self, bank: int):
            self.bank = bank
            super().__init__()

    map_info: reactive[dict] = reactive({})
    hovered_bank: reactive[Optional[int]] = reactive(None)

    def __init__(self, title="Memory Map ($00-$FF)", **kwargs):
        self.title_text = title
        super().__init__(**kwargs)
        self.styles.height = "auto"
        self.styles.width = "auto"

    def watch_map_info(self, info: dict):
        self.refresh()

    def render(self) -> Panel:
        # Create a 16x16 grid of blocks
        # Rows: 0x0_, 0x1_, ... 0xF_
        # Cols: 0x_0, 0x_1, ... 0x_F
        
        grid_text = Text()
        
        for row in range(16):
            for col in range(16):
                bank = (row * 16) + col
                
                # Determine color based on bank type
                # Priority: RAM > SRAM > ROM > System
                bank_data = self.map_info.get(bank, [])
                color = "grey30" # Default/Unmapped
                char = "· "
                
                has_rom = any(d['type'] == 'rom' for d in bank_data)
                has_ram = any(d['type'] == 'ram' for d in bank_data)
                has_sram = any(d['type'] == 'sram' for d in bank_data)
                has_system = any(d['type'] == 'system' for d in bank_data)

                if has_ram:
                    color = "bright_blue"
                    char = "R "
                elif has_sram:
                    color = "bright_red"
                    char = "S "
                elif has_rom:
                    color = "bright_green"
                    char = "■ "
                elif has_system:
                    color = "yellow"
                    char = "sys" # Too wide?
                    char = "s "

                if self.hovered_bank == bank:
                    color = "white on blue"
                
                grid_text.append(char, style=color)
            grid_text.append("\n")
            
        return Panel(grid_text, title=self.title_text, subtitle="Hover for details")

    def on_mouse_move(self, event: MouseMove):
        # Calculate bank from mouse coordinates
        x = event.x - 2 # Adjust for border/padding
        y = event.y - 1
        
        col = x // 2
        row = y
        
        if 0 <= col < 16 and 0 <= row < 16:
            bank = (row * 16) + col
            if bank != self.hovered_bank:
                self.hovered_bank = bank
                self.post_message(self.BankHovered(bank, self.map_info.get(bank, [])))
        else:
            self.hovered_bank = None

    def on_click(self, event: Click):
        x = event.x - 2
        y = event.y - 1
        col = x // 2
        row = y
        
        if 0 <= col < 16 and 0 <= row < 16:
            bank = (row * 16) + col
            self.post_message(self.BankClicked(bank))
        else:
            # Debug click
            # self.notify(f"Click ignored: {x},{y} -> {col},{row}")
            pass

class BankDetailWidget(Static):
    def update_bank(self, bank: int, info: list):
        if bank is None:
            self.update(Panel("Hover over a bank", title="Bank Details"))
            return
            
        content = f"[b]Bank ${bank:02X}[/b]\n\n"
        if not info:
            content += "[dim]Unmapped / Unknown[/dim]"
        else:
            for region in info:
                start, end = region['range']
                rtype = region['type'].upper()
                color = "white"
                if rtype == "ROM": color = "green"
                elif rtype == "RAM": color = "blue"
                elif rtype == "SYSTEM": color = "yellow"
                
                content += f"[{color}]{start:04X}-{end:04X}: {rtype}[/{color}]\n"
                
        self.update(Panel(content, title="Bank Details"))

class HexViewer(Static):
    """
    Displays raw hex data for a selected bank.
    """
    data: reactive[bytes] = reactive(b"")
    bank: reactive[Optional[int]] = reactive(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.styles.height = "1fr"
        self.styles.overflow_y = "scroll"

    def watch_data(self, data: bytes):
        self.update(self._make_content(data))
        self.scroll_to(0, 0)

    def _make_content(self, data: bytes) -> Panel:
        if data is None:
            return Panel("Data is None (Initial State)", title="Hex View")
        if len(data) == 0:
            return Panel("Data is Empty (Not Mapped to ROM)", title="Hex View")
        
        # Format hex dump
        # Address  Hex...            Chars
        # 0000     00 01 02 ... 0F   ....
        
        lines = []
        # Limit to first 4KB for performance if needed, or paginate
        # For now, show first 1KB to be safe with TUI performance
        limit = 1024 
        display_data = data[:limit]
        
        text = Text()
        for i in range(0, len(display_data), 16):
            chunk = display_data[i:i+16]
            
            # Address (Relative to bank start)
            text.append(f"{i:04X}  ", style="dim cyan")
            
            # Hex
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            text.append(f"{hex_part:<48}  ", style="green")
            
            # Chars
            chars = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            text.append(f"{chars}\n", style="yellow")
            
        if len(data) > limit:
            text.append(f"\n... {len(data) - limit} bytes omitted ...", style="dim")

        return Panel(text, title=f"Bank ${self.bank:02X} Data" if self.bank is not None else "Hex View")

class RomAnalyzerPanel(Container):
    DEFAULT_CSS = """
    RomAnalyzerPanel {
        layout: horizontal;
        height: 100%;
    }
    #left-col {
        width: 1fr;
        height: 100%;
    }
    #right-col {
        width: 40;
        height: 100%;
    }
    #maps-container {
        height: auto;
        width: 100%;
    }
    MemoryMapWidget {
        width: 50%;
    }
    #hex-view {
        height: 1fr;
    }
    """

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.analyzer = SNESRomAnalyzer(file_path)

    def compose(self) -> ComposeResult:
        with Vertical(id="left-col"):
            with Horizontal(id="maps-container"):
                yield MemoryMapWidget(title="ROM Chip ($00-$FF)", id="map-rom")
                yield MemoryMapWidget(title="RAM/System ($00-$FF)", id="map-ram")
            yield HexViewer(id="hex-view")
            yield Button("Disassemble Bank", id="btn-disasm", disabled=True)
        with Vertical(id="right-col"):
            yield RomInfoWidget(id="rom-info")
            yield BankDetailWidget(id="bank-detail")

    def on_mount(self):
        if self.file_path:
            self.load_file(self.file_path)

    def load_file(self, file_path: str):
        self.file_path = file_path
        self.analyzer = SNESRomAnalyzer(file_path)
        self.query_one(RomInfoWidget).header = self.analyzer.header
        
        full_map = self.analyzer.get_memory_map_info()
        
        # Split map info
        rom_map = {}
        ram_map = {}
        
        for bank, regions in full_map.items():
            rom_regions = [r for r in regions if r['type'] == 'rom']
            ram_regions = [r for r in regions if r['type'] in ('ram', 'sram', 'system')]
            
            if rom_regions:
                rom_map[bank] = rom_regions
            if ram_regions:
                ram_map[bank] = ram_regions
        
        self.query_one("#map-rom", MemoryMapWidget).map_info = rom_map
        self.query_one("#map-ram", MemoryMapWidget).map_info = ram_map
        
        self.query_one(HexViewer).data = b""
        self.query_one(HexViewer).bank = None

    def on_memory_map_widget_bank_hovered(self, event: MemoryMapWidget.BankHovered):
        self.query_one(BankDetailWidget).update_bank(event.bank, event.info)
        
    def on_click(self, event: Click):
        # Handle click on MemoryMapWidget manually if needed, 
        # but MemoryMapWidget is a Static, so it gets clicks.
        # We need to know WHICH bank was clicked.
        # The MemoryMapWidget needs to emit a BankClicked event.
        pass
        
    def on_memory_map_widget_bank_hovered(self, event: MemoryMapWidget.BankHovered):
        self.query_one(BankDetailWidget).update_bank(event.bank, event.info)
        
    def on_click(self, event: Click):
        # Handle click on MemoryMapWidget manually if needed, 
        # but MemoryMapWidget is a Static, so it gets clicks.
        # We need to know WHICH bank was clicked.
        # The MemoryMapWidget needs to emit a BankClicked event.
        pass
        
    def on_memory_map_widget_bank_clicked(self, event: "MemoryMapWidget.BankClicked"):
        # We need to add this event to MemoryMapWidget first
        data = self.analyzer.get_bank_data(event.bank)
        
        # Detailed Debug
        header_ok = self.analyzer.header is not None
        data_len = len(self.analyzer.data)
        map_mode = self.analyzer.header.map_mode if header_ok else "None"
        
        msg = f"Bank ${event.bank:02X} | Header: {header_ok} | Data: {data_len} | Mode: {map_mode} | Result: {len(data)}"
        
        hex_view = self.query_one(HexViewer)
        hex_view.bank = event.bank
        hex_view.data = data
        
        self.query_one("#btn-disasm", Button).disabled = not bool(data)
        
        # Only notify if we have data, or if it's a ROM bank click that failed
        # If clicking RAM map on a RAM-only bank, data will be empty, which is expected.
        if data:
            self.notify(msg, severity="information")
        else:
            # Check if it was supposed to have ROM
            # We can check the event.control (the widget that sent it)
            # But event doesn't carry that easily in this handler signature?
            # Actually event.control is the widget.
            if event.control and event.control.id == "map-rom":
                 self.notify(msg, severity="warning")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-disasm":
            hex_view = self.query_one(HexViewer)
            if hex_view.data and hex_view.bank is not None:
                # Import here to avoid circular dependency
                from .disassembler_panel import DisassemblerPanel
                
                try:
                    disasm_panel = self.app.query_one(DisassemblerPanel)
                    start_addr = hex_view.bank << 16
                    disasm_panel.load_data(hex_view.data, start_addr)
                    
                    # Switch view
                    if hasattr(self.app, "action_show_disassembler"):
                        self.app.action_show_disassembler()
                except Exception as e:
                    self.notify(f"Failed to open disassembler: {e}", severity="error")
